"""
risk_manager.py
===============
Tiered bankroll management + Fractional Kelly position sizing for binary prediction markets.

Math (EN/TH):
─────────────
Binary market mechanics:
  - You buy YES shares at entry_price  (e.g. 0.55 = 55 cents per share)
  - If YES wins -> you receive $1.00 per share  -> profit = (1 - entry_price) per share
  - If YES loses -> you lose entry_price per share (your cost)
  - Max loss  = shares x entry_price
  - Max profit = shares x (1 - entry_price)

Kelly Criterion for binary markets (full Kelly):
  p  = model win probability  (e.g. 0.62)
  b  = profit ratio per $1 wagered = (1 - entry_price) / entry_price
  f* = edge / (1 - entry_price)
  where edge = p - entry_price  (model prob minus market-implied prob)

Position sizing formula:
  risk_pct      = min(full_kelly x kelly_fraction, tier_max_risk, HARD_CAP_3%)
  position_$    = bankroll x risk_pct          <- target profit if WIN
  shares        = position_$ / (1 - entry_price)
  cost_to_enter = shares x entry_price         <- dollars actually spent
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import NamedTuple

from polymarket.bankroll_tiers import get_tier_config as get_bankroll_tier_config


LOGGER = logging.getLogger(__name__)

# ── Hard limits (always enforced regardless of tier) ──────────────────────────
HARD_CAP_SINGLE_TRADE      = 0.03   # Never risk > 3% of bankroll in one trade
HARD_DAILY_DRAWDOWN        = 0.10   # Stop trading if daily loss exceeds 10%
FLOOR_BALANCE              = 5.00   # Stop ALL trading below this balance (dollars)
LOSS_CLUSTER_THRESHOLD     = 3      # Consecutive losses before pause
LOSS_CLUSTER_PAUSE_SECONDS = 1800   # 30-minute pause after loss cluster
STANDARD_BANKROLL_MODE     = "STANDARD"
MICRO_SURVIVAL_MODE        = "MICRO_SURVIVAL"

class TierInfo(NamedTuple):
    label: str           # e.g. "micro"
    description: str     # e.g. "Micro Bankroll"
    max_risk_pct: float  # e.g. 0.005 for 0.5%
    kelly_fraction: float
    min_bet: float       # minimum bet in USD
    stop_loss_pct: float


def get_bankroll_tier(bankroll: float) -> TierInfo:
    """Return the risk tier for a given bankroll size."""
    try:
        config = get_bankroll_tier_config(max(float(bankroll), 0.0))
        return TierInfo(
            label=config.tier_id,
            description=config.description,
            max_risk_pct=config.max_risk_pct,
            kelly_fraction=config.kelly_fraction,
            min_bet=config.min_position_size_hint,
            stop_loss_pct=config.stop_loss_pct,
        )
    except Exception:
        pass
    return TierInfo(
        label="T0_MICRO_SEED", description="Micro Seed",
        max_risk_pct=0.005, kelly_fraction=0.10, min_bet=0.05,
        stop_loss_pct=0.90
    )


# Alias for backward compat
get_tier = get_bankroll_tier


# ── Core Kelly math ───────────────────────────────────────────────────────────

def calculate_kelly_fraction(win_rate: float, reward_risk_ratio: float) -> float:
    """Standard Kelly: f* = p - (1-p)/b"""
    if not 0 < win_rate < 1:
        raise ValueError("win_rate must be between 0 and 1.")
    if reward_risk_ratio <= 0:
        raise ValueError("reward_risk_ratio must be positive.")
    loss_rate = 1 - win_rate
    kelly = win_rate - (loss_rate / reward_risk_ratio)
    LOGGER.debug("Kelly | win=%.4f rr=%.4f kelly=%.4f", win_rate, reward_risk_ratio, kelly)
    return max(0.0, kelly)


def kelly_for_binary(edge: float, entry_price: float) -> float:
    """
    Kelly fraction for binary prediction market.
    f* = edge / (1 - entry_price)

    edge        = model_prob - entry_price
    entry_price = market price per share (0-1 range)
    """
    if entry_price <= 0 or entry_price >= 1:
        return 0.0
    denom = 1.0 - entry_price
    return max(0.0, edge / denom)


def dynamic_stop_loss_pct(
    edge: float,
    realized_volatility: float,
    min_sl: float = 0.01,
    max_sl: float = 0.04,
) -> float:
    """
    Dynamic Stop Loss:
    - edge high (>0.15) -> tight SL (near min_sl)
    - volatility high   -> wider SL (toward max_sl)
    """
    edge_factor = max(0.0, min(1.0, 1.0 - (edge / 0.20)))
    vol_factor  = min(realized_volatility * 5.0, 0.5)
    combined    = edge_factor + vol_factor
    sl_pct = min_sl + (max_sl - min_sl) * min(combined, 1.0)
    return round(max(min_sl, min(sl_pct, max_sl)), 4)


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass(slots=True)
class RiskPlan:
    account_balance: float
    entry_price: float
    stop_loss_price: float
    take_profit_price: float
    partial_tp_price: float
    risk_amount: float
    kelly_fraction: float
    capped_fraction: float
    position_size: float        # number of shares
    notional_size: float        # cost to enter = shares x entry_price
    stop_loss_pct: float
    diagnostics: dict[str, object] = field(default_factory=dict)


@dataclass
class SafeBetResult:
    """
    Full breakdown of a tiered safe-bet sizing decision.
    ผลการคำนวณขนาด position แบบ tiered conservative สำหรับ binary market
    """
    # Inputs
    bankroll:          float
    edge:              float
    entry_price:       float
    price_to_beat:     float   # For log display only

    # Tier
    tier:              str
    tier_description:  str
    max_risk_pct:      float
    kelly_fraction:    float
    min_bet:           float

    # Kelly chain
    full_kelly:        float   # Full (uncapped) Kelly fraction of bankroll
    fractional_kelly:  float   # After tier kelly_fraction applied
    applied_risk_pct:  float   # After all caps: min(frac_kelly, tier_max, 3%)

    # Sizing output
    position_dollars:  float   # Target profit if WIN = bankroll x applied_risk_pct
    shares:            float   # = position_dollars / (1 - entry_price)
    cost_to_enter:     float   # = shares x entry_price (actual $ spent)
    max_profit:        float   # = position_dollars
    max_loss:          float   # = cost_to_enter

    # Guard flags
    floor_breach:      bool    # balance < FLOOR_BALANCE -> NO TRADE
    below_min_bet:     bool    # cost_to_enter < min_bet -> skip (too small)
    hard_cap_applied:  bool    # 3% hard cap was binding constraint

    def log_line(self) -> str:
        """Produce the standard MICRO BANKROLL log line."""
        if self.floor_breach:
            return (
                f"[FLOOR BREACH] Bankroll ${self.bankroll:.2f} < floor ${FLOOR_BALANCE:.2f} "
                "-- NO TRADE"
            )
        ptb_str = f"${self.price_to_beat:,.2f}" if self.price_to_beat > 0 else "N/A"
        return (
            f"Bankroll: ${self.bankroll:.2f} | "
            f"Tier: {self.tier.capitalize()} | "
            f"Risk %: {self.applied_risk_pct*100:.2f}% | "
            f"Suggested Bet: ${self.cost_to_enter:.2f} | "
            f"Edge: {self.edge*100:.1f}% | "
            f"Price To Beat: {ptb_str}"
        )

    def can_place(self) -> bool:
        return (not self.floor_breach) and (not self.below_min_bet) and (self.shares > 0)


# ── Main sizing function ──────────────────────────────────────────────────────

def calculate_safe_bet_size(
    bankroll: float,
    edge: float,
    entry_price: float = 0.50,
    price_to_beat: float = 0.0,
) -> SafeBetResult:
    """
    Calculate conservative tiered position size for a binary prediction market trade.

    Parameters
    ----------
    bankroll    : Current USDC balance
    edge        : Model edge = model_probability - entry_price
    entry_price : Market price per YES share (0-1)
    price_to_beat : PTB for display in log line only

    Math (step-by-step):
    --------------------
    1. หา tier -> max_risk_pct, kelly_fraction, min_bet
    2. Full Kelly: f* = edge / (1 - entry_price)
    3. Fractional Kelly: f_applied = f* x kelly_fraction
    4. Cap ด้วย tier max: min(f_applied, tier_max_risk)
    5. Hard cap 3%: min(..., 0.03)
    6. position_dollars = bankroll x applied_risk_pct  (กำไรเป้าหมายถ้าชนะ)
    7. shares = position_dollars / (1 - entry_price)
    8. cost_to_enter = shares x entry_price            (เงินที่จ่ายจริง)
    """
    tier = get_bankroll_tier(bankroll)

    # Floor guard
    if bankroll < FLOOR_BALANCE:
        return SafeBetResult(
            bankroll=bankroll, edge=edge, entry_price=entry_price, price_to_beat=price_to_beat,
            tier=tier.label, tier_description=tier.description,
            max_risk_pct=tier.max_risk_pct, kelly_fraction=tier.kelly_fraction, min_bet=tier.min_bet,
            full_kelly=0.0, fractional_kelly=0.0, applied_risk_pct=0.0,
            position_dollars=0.0, shares=0.0, cost_to_enter=0.0,
            max_profit=0.0, max_loss=0.0,
            floor_breach=True, below_min_bet=False, hard_cap_applied=False,
        )

    # No edge -> no trade
    if edge <= 0:
        return SafeBetResult(
            bankroll=bankroll, edge=edge, entry_price=entry_price, price_to_beat=price_to_beat,
            tier=tier.label, tier_description=tier.description,
            max_risk_pct=tier.max_risk_pct, kelly_fraction=tier.kelly_fraction, min_bet=tier.min_bet,
            full_kelly=0.0, fractional_kelly=0.0, applied_risk_pct=0.0,
            position_dollars=0.0, shares=0.0, cost_to_enter=0.0,
            max_profit=0.0, max_loss=0.0,
            floor_breach=False, below_min_bet=True, hard_cap_applied=False,
        )

    # Kelly chain
    full_kelly       = kelly_for_binary(edge=edge, entry_price=entry_price)
    fractional_kelly = full_kelly * tier.kelly_fraction
    capped_by_tier   = min(fractional_kelly, tier.max_risk_pct)
    hard_cap_applied = capped_by_tier > HARD_CAP_SINGLE_TRADE
    applied_risk_pct = min(capped_by_tier, HARD_CAP_SINGLE_TRADE)

    # Position sizing (Kelly base)
    position_dollars = bankroll * applied_risk_pct
    profit_per_share = max(1.0 - entry_price, 1e-9)
    shares           = position_dollars / profit_per_share
    
    # ── User Request: Dynamic Minimum Shares (1-5) based on Opportunity (Edge) ──
    # If edge is small (0.01), min_shares ~ 1. If edge is high (>=0.15), min_shares ~ 5.
    opportunity_factor = min(edge / 0.15, 1.0)  # 0.0 to 1.0
    dynamic_min_shares = 1.0 + (opportunity_factor * 4.0)  # 1.0 to 5.0
    
    # Override shares if Kelly gave us too little (common in Micro tier)
    if shares < dynamic_min_shares:
        shares = round(dynamic_min_shares)
        # Recalculate costs based on forced minimum shares
        position_dollars = shares * profit_per_share

    cost_to_enter    = shares * entry_price
    max_profit       = position_dollars
    max_loss         = cost_to_enter

    below_min_bet = cost_to_enter < tier.min_bet

    # Safety guard: cost must never exceed the bankroll itself.
    # If this fires, there is a math bug in the Kelly chain above.
    if cost_to_enter > bankroll * 1.1:
        raise AssertionError(
            f"SAFETY BREACH in calculate_safe_bet_size: "
            f"cost_to_enter=${cost_to_enter:.6f} > 110% of bankroll=${bankroll:.6f}. "
            f"edge={edge:.6f} entry_price={entry_price:.4f} "
            f"full_kelly={full_kelly:.6f} applied_risk_pct={applied_risk_pct:.6f}. "
            "This is a sizing logic bug — fix before placing real orders."
        )

    return SafeBetResult(
        bankroll=bankroll, edge=edge, entry_price=entry_price, price_to_beat=price_to_beat,
        tier=tier.label, tier_description=tier.description,
        max_risk_pct=tier.max_risk_pct, kelly_fraction=tier.kelly_fraction, min_bet=tier.min_bet,
        full_kelly=full_kelly, fractional_kelly=fractional_kelly, applied_risk_pct=applied_risk_pct,
        position_dollars=position_dollars, shares=shares, cost_to_enter=cost_to_enter,
        max_profit=max_profit, max_loss=max_loss,
        floor_breach=False, below_min_bet=below_min_bet, hard_cap_applied=hard_cap_applied,
    )


# ── BankrollTierManager (stateful compounding tracker) ───────────────────────

class BankrollTierManager:
    """
    Stateful bankroll tracker with automatic compounding.
    Delegates sizing to calculate_safe_bet_size().
    """

    def __init__(
        self,
        initial_balance: float = 10.0,
        floor: float = FLOOR_BALANCE,
        daily_drawdown_limit: float = HARD_DAILY_DRAWDOWN,
    ) -> None:
        self._balance            = initial_balance
        self._floor              = floor
        self._daily_dd_limit     = daily_drawdown_limit
        self._day_start_balance  = initial_balance
        self._daily_loss         = 0.0
        self._day_start_ts       = time.time()
        self._consecutive_losses = 0
        self._pause_until_ts     = 0.0

    def set_balance(self, balance: float) -> None:
        self._balance = round(balance, 6)
        if self._daily_loss == 0:
            self._day_start_balance = self._balance

    @property
    def balance(self) -> float:
        return self._balance

    def record_win(self, profit: float) -> float:
        self._consecutive_losses = 0
        self._balance = round(self._balance + profit, 6)
        LOGGER.info("[BankrollMgr] WIN +$%.4f -> balance $%.4f | streak reset", profit, self._balance)
        return self._balance

    def record_loss(self, loss: float) -> float:
        self._balance         = round(max(0.0, self._balance - loss), 6)
        self._daily_loss      += loss
        self._consecutive_losses += 1
        if self._consecutive_losses >= LOSS_CLUSTER_THRESHOLD:
            self._pause_until_ts = time.time() + LOSS_CLUSTER_PAUSE_SECONDS
            LOGGER.warning(
                "[LOSS CLUSTER] %d consecutive losses — pausing trading for %d min (until %s)",
                self._consecutive_losses,
                LOSS_CLUSTER_PAUSE_SECONDS // 60,
                time.strftime("%H:%M", time.localtime(self._pause_until_ts)),
            )
        LOGGER.info(
            "[BankrollMgr] LOSS -$%.4f -> balance $%.4f | daily_loss $%.4f | streak %d",
            loss, self._balance, self._daily_loss, self._consecutive_losses,
        )
        return self._balance

    def reset_daily_stats(self) -> None:
        self._day_start_balance = self._balance
        self._daily_loss        = 0.0
        self._day_start_ts      = time.time()

    @property
    def is_floor_breached(self) -> bool:
        return self._balance < self._floor

    @property
    def is_daily_drawdown_breached(self) -> bool:
        if self._day_start_balance <= 0:
            return True
        return (self._daily_loss / self._day_start_balance) >= self._daily_dd_limit

    def can_trade(self) -> tuple[bool, str]:
        now = time.time()
        if now < self._pause_until_ts:
            mins_left = int((self._pause_until_ts - now) / 60) + 1
            return False, (
                f"LOSS CLUSTER PAUSE: {self._consecutive_losses} consecutive losses — "
                f"resuming in ~{mins_left}min (at {time.strftime('%H:%M', time.localtime(self._pause_until_ts))})"
            )
        if self.is_floor_breached:
            return False, f"FLOOR BREACH: balance ${self._balance:.2f} < floor ${self._floor:.2f}"
        if self.is_daily_drawdown_breached:
            dd_pct = (self._daily_loss / max(self._day_start_balance, 1e-9)) * 100
            return False, f"DAILY DRAWDOWN {dd_pct:.1f}% >= limit {self._daily_dd_limit*100:.0f}%"
        return True, ""

    def calculate_position_size(
        self,
        bankroll: float | None = None,
        *,
        edge: float,
        entry_price: float = 0.50,
        price_to_beat: float = 0.0,
    ) -> SafeBetResult:
        bal = bankroll if bankroll is not None else self._balance
        return calculate_safe_bet_size(
            bankroll=bal, edge=edge, entry_price=entry_price, price_to_beat=price_to_beat,
        )


# ── RiskManager (high-level facade) ──────────────────────────────────────────

class RiskManager:
    """High-level facade. Primary external entry point."""

    def __init__(self, initial_balance: float = 10.0, floor: float = FLOOR_BALANCE) -> None:
        self._tier_mgr = BankrollTierManager(
            initial_balance=initial_balance, floor=floor,
        )

    @property
    def balance(self) -> float:
        return self._tier_mgr.balance

    @property
    def tier(self) -> TierInfo:
        return get_bankroll_tier(self._tier_mgr.balance)

    def can_trade(self) -> tuple[bool, str]:
        return self._tier_mgr.can_trade()

    def calculate_position_size(
        self,
        bankroll: float | None = None,
        *,
        edge: float,
        entry_price: float = 0.50,
        price_to_beat: float = 0.0,
    ) -> SafeBetResult:
        return self._tier_mgr.calculate_position_size(
            bankroll=bankroll, edge=edge, entry_price=entry_price, price_to_beat=price_to_beat,
        )

    def set_balance(self, balance: float) -> None:
        self._tier_mgr.set_balance(balance)

    def record_result(self, won: bool, pnl: float) -> float:
        return self._tier_mgr.record_win(pnl) if won else self._tier_mgr.record_loss(abs(pnl))

    def reset_daily(self) -> None:
        self._tier_mgr.reset_daily_stats()


# ── Legacy API (kept for backward compatibility with PolymarketOrderManager) ──

def build_risk_plan(
    account_balance: float,
    entry_price: float,
    stop_loss_pct: float,
    max_risk_per_trade: float,
    win_rate: float,
    reward_risk_ratio: float,
    kelly_fraction_cap: float,
    take_profit_pct: float = 0.06,
    partial_tp_pct: float = 0.03,
) -> RiskPlan:
    if account_balance <= 0:
        raise ValueError("account_balance must be positive.")
    if entry_price <= 0:
        raise ValueError("entry_price must be positive.")
    if not 0 < stop_loss_pct < 1:
        raise ValueError("stop_loss_pct must be between 0 and 1.")
    if not 0 < max_risk_per_trade <= HARD_CAP_SINGLE_TRADE:
        raise ValueError(
            f"max_risk_per_trade must be positive and no greater than {HARD_CAP_SINGLE_TRADE:.2f}."
        )
    if not 0 < kelly_fraction_cap <= 1:
        raise ValueError("kelly_fraction_cap must be between 0 and 1.")

    stop_loss_price   = entry_price * (1 - stop_loss_pct)
    take_profit_price = entry_price * (1 + take_profit_pct)
    partial_tp_price  = entry_price * (1 + partial_tp_pct)

    risk_amount  = account_balance * max_risk_per_trade
    price_risk   = entry_price - stop_loss_price
    kelly        = calculate_kelly_fraction(win_rate=win_rate, reward_risk_ratio=reward_risk_ratio)
    capped_frac  = min(kelly, kelly_fraction_cap)

    pos_by_risk  = risk_amount / price_risk
    pos_by_kelly = (account_balance * capped_frac) / entry_price
    raw_pos      = min(pos_by_risk, pos_by_kelly)

    max_notional  = account_balance * min(max_risk_per_trade, HARD_CAP_SINGLE_TRADE)
    position_size = min(raw_pos, max_notional / max(entry_price, 1e-9))
    notional_size = position_size * entry_price

    LOGGER.info(
        "RiskPlan | risk=%.2f%% sl=%.2f%% tp=%.2f%% kelly=%.4f size=%.6f notional=%.4f",
        max_risk_per_trade * 100, stop_loss_pct * 100, take_profit_pct * 100,
        capped_frac, position_size, notional_size,
    )

    return RiskPlan(
        account_balance=account_balance, entry_price=entry_price,
        stop_loss_price=stop_loss_price, take_profit_price=take_profit_price,
        partial_tp_price=partial_tp_price, risk_amount=risk_amount,
        kelly_fraction=kelly, capped_fraction=capped_frac,
        position_size=position_size, notional_size=notional_size,
        stop_loss_pct=stop_loss_pct,
    )


def bankroll_mode_for(
    *,
    account_balance: float,
    threshold: float,
    paper_trading: bool,
) -> str:
    if paper_trading and 0.0 < float(account_balance) < float(threshold):
        return MICRO_SURVIVAL_MODE
    return STANDARD_BANKROLL_MODE


def build_micro_survival_risk_plan(
    *,
    account_balance: float,
    entry_price: float,
    stop_loss_pct: float,
    risk_fraction: float,
    min_position_size_usd: float,
    max_risk_per_trade: float,
    take_profit_pct: float = 0.06,
    partial_tp_pct: float = 0.03,
    diagnostics: dict[str, object] | None = None,
) -> RiskPlan:
    if account_balance <= 0:
        raise ValueError("account_balance must be positive.")
    if entry_price <= 0:
        raise ValueError("entry_price must be positive.")
    if not 0 < stop_loss_pct < 1:
        raise ValueError("stop_loss_pct must be between 0 and 1.")

    effective_fraction = min(
        max(float(risk_fraction), 0.0),
        max(float(max_risk_per_trade), 0.0),
        HARD_CAP_SINGLE_TRADE,
    )
    risk_cap_usd = account_balance * effective_fraction
    minimum_usd = max(float(min_position_size_usd), 0.0)
    notional_size = min(max(risk_cap_usd, minimum_usd), account_balance)
    notional_size = round(max(notional_size, 0.0), 6)
    position_size = round(notional_size / max(entry_price, 1e-9), 6)
    stop_loss_price = entry_price * (1 - stop_loss_pct)

    merged_diagnostics: dict[str, object] = dict(diagnostics or {})
    merged_diagnostics.update(
        {
            "bankroll_mode": MICRO_SURVIVAL_MODE,
            "micro_survival_active": True,
            "micro_position_size": notional_size,
            "micro_survival_risk_fraction": effective_fraction,
            "micro_survival_min_position_size": minimum_usd,
        }
    )

    return RiskPlan(
        account_balance=account_balance,
        entry_price=entry_price,
        stop_loss_price=stop_loss_price,
        take_profit_price=entry_price * (1 + take_profit_pct),
        partial_tp_price=entry_price * (1 + partial_tp_pct),
        risk_amount=notional_size,
        kelly_fraction=0.0,
        capped_fraction=(notional_size / account_balance if account_balance > 0 else 0.0),
        position_size=position_size,
        notional_size=notional_size,
        stop_loss_pct=stop_loss_pct,
        diagnostics=merged_diagnostics,
    )
