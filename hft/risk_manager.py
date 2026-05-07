"""
hft/risk_manager.py
===================
Dynamic Tiered Bankroll & Risk Manager

Tier detection is automatic based on current balance:

  Tier 1  < $100    : Fixed micro-sizing $1-$2, Kelly 0.25, cap 20%/window
  Tier 2  $100-$999 : Fractional Kelly 0.20, cap 15%/window
  Tier 3  $1K-$10K  : Fractional Kelly 0.15, cap 10%/window, multi-coin enabled
  Tier 4  $10K+     : Fractional Kelly 0.10, cap 8%/window, prefer maker orders

Kelly sizing math:
  full_kelly = (p - price) / (1 - price)
  bet_size   = bankroll * tier_kelly_frac * full_kelly
  capped at  min(tier_max_bet, window_exposure_remaining)

Brier score bonus: rolling avg Brier < 0.18 → size += 10% (model well-calibrated).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple

LOGGER = logging.getLogger(__name__)

FLOOR_BALANCE_USD    = 5.0
DAILY_DRAWDOWN_LIMIT = 0.08


# ── Tier profiles ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TierProfile:
    name:           str
    kelly_fraction: float
    window_cap_pct: float   # max bankroll fraction exposed per window
    min_bet_usd:    float
    max_bet_usd:    float
    max_entries:    int
    prefer_maker:   bool    # True → limit orders preferred over FOK
    multi_coin:     bool    # True → BTC + ETH concurrently allowed


TIERS: Dict[int, TierProfile] = {
    1: TierProfile("micro",         0.25, 0.20,  1.00,  2.00, 3, False, False),
    2: TierProfile("small",         0.20, 0.15,  1.50,  5.00, 3, False, False),
    3: TierProfile("growth",        0.15, 0.10,  2.00, 15.00, 4, True,  True),
    4: TierProfile("institutional", 0.10, 0.08,  5.00, 50.00, 5, True,  True),
}


def _detect_tier(balance: float) -> int:
    if balance >= 10_000: return 4
    if balance >= 1_000:  return 3
    if balance >= 100:    return 2
    return 1


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class SizeResult:
    allowed:      bool
    shares:       float = 0.0
    cost_usd:     float = 0.0
    block_reason: str   = ""
    tier:         int   = 1
    use_maker:    bool  = False


@dataclass
class WindowState:
    epoch:    int
    entries:  int   = 0
    exposure: float = 0.0


# ── Main class ─────────────────────────────────────────────────────────────────

class HFTRiskManager:
    """
    Usage:
        rm = HFTRiskManager(initial_bankroll=100.0)
        ok, reason = rm.can_trade()
        size = rm.compute_size(p_model=0.62, entry_price=0.48, window_epoch=epoch)
        rm.register_entry(epoch, size.cost_usd)
        rm.register_exit(pnl_usd=+1.20, p_model=0.62, outcome=1.0)
    """

    def __init__(self, initial_bankroll: float) -> None:
        self.bankroll        = initial_bankroll
        self._day_start_bal  = initial_bankroll
        self._day_start_ts   = time.time()
        self._daily_pnl      = 0.0
        self._windows: Dict[int, WindowState] = {}
        self._brier_scores: List[float] = []
        self._paused_until   = 0.0

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def tier(self) -> int:
        return _detect_tier(self.bankroll)

    @property
    def profile(self) -> TierProfile:
        return TIERS[self.tier]

    @property
    def daily_pnl(self) -> float:
        return self._daily_pnl

    @property
    def avg_brier(self) -> float:
        recent = self._brier_scores[-20:]
        return sum(recent) / len(recent) if recent else 0.25

    # ── Gate ──────────────────────────────────────────────────────────────────

    def can_trade(self) -> Tuple[bool, str]:
        if time.time() < self._paused_until:
            return False, f"circuit_breaker:{int(self._paused_until - time.time())}s"
        if self.bankroll <= FLOOR_BALANCE_USD:
            return False, f"floor:${self.bankroll:.2f}"
        if self._daily_pnl < -(self._day_start_bal * DAILY_DRAWDOWN_LIMIT):
            return False, f"daily_dd:{self._daily_pnl:+.2f}"
        self._check_day_reset()
        return True, ""

    # ── Sizing ────────────────────────────────────────────────────────────────

    def compute_size(
        self,
        p_model:      float,
        entry_price:  float,
        window_epoch: int,
    ) -> SizeResult:
        """
        Fractional Kelly bet sizing with tier caps.

        Math:
          full_kelly = (p_model - entry_price) / (1 - entry_price)
          raw_bet    = bankroll * tier_kelly_fraction * full_kelly
          final_bet  = clamp(raw_bet, min_bet, min(max_bet, window_remaining_cap))
        """
        prof = self.profile
        ws   = self._get_window(window_epoch)

        if ws.entries >= prof.max_entries:
            return SizeResult(False, block_reason=f"max_entries:{prof.max_entries}")
        if not (0.0 < entry_price < 1.0):
            return SizeResult(False, block_reason="invalid_price")

        full_kelly = max(0.0, (p_model - entry_price) / (1.0 - entry_price))
        if full_kelly <= 0:
            return SizeResult(False, block_reason="no_edge")

        # Apply fractional kelly + Brier calibration bonus
        frac = prof.kelly_fraction
        if self.avg_brier < 0.18 and len(self._brier_scores) >= 5:
            frac = min(frac * 1.10, 0.30)   # cap bonus at 30%

        raw_bet  = self.bankroll * frac * full_kelly
        raw_bet  = max(prof.min_bet_usd, min(prof.max_bet_usd, raw_bet))

        # Window exposure cap
        max_exp   = self.bankroll * prof.window_cap_pct
        remaining = max(0.0, max_exp - ws.exposure)
        cost_usd  = min(raw_bet, remaining)

        if cost_usd < prof.min_bet_usd:
            return SizeResult(
                False,
                block_reason=f"window_cap:exp={ws.exposure:.2f}/max={max_exp:.2f}",
            )

        # Floor guard
        if self.bankroll - cost_usd < FLOOR_BALANCE_USD:
            cost_usd = self.bankroll - FLOOR_BALANCE_USD
            if cost_usd < prof.min_bet_usd:
                return SizeResult(False, block_reason="floor_guard")

        shares = cost_usd / entry_price

        return SizeResult(
            allowed=True,
            shares=round(shares, 4),
            cost_usd=round(cost_usd, 4),
            tier=self.tier,
            use_maker=prof.prefer_maker,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def register_entry(self, window_epoch: int, cost_usd: float) -> None:
        ws = self._get_window(window_epoch)
        ws.entries  += 1
        ws.exposure += cost_usd
        self.bankroll -= cost_usd

    def register_exit(self, pnl_usd: float, p_model: float, outcome: float) -> None:
        """outcome: 1.0 = win, 0.0 = loss"""
        self.bankroll   += pnl_usd
        self._daily_pnl += pnl_usd
        self._brier_scores.append((p_model - outcome) ** 2)

        if self.bankroll < FLOOR_BALANCE_USD * 1.5:
            self._paused_until = time.time() + 300
            LOGGER.warning("[RiskMgr] Near floor — pausing 5 min")

    def window_info(self, epoch: int) -> dict:
        ws = self._get_window(epoch)
        return {
            "entries":  ws.entries,
            "exposure": ws.exposure,
            "max_exp":  round(self.bankroll * self.profile.window_cap_pct, 2),
            "tier":     self.tier,
            "tier_name": self.profile.name,
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_window(self, epoch: int) -> WindowState:
        if epoch not in self._windows:
            self._windows = {k: v for k, v in self._windows.items() if k >= epoch - 600}
            self._windows[epoch] = WindowState(epoch=epoch)
        return self._windows[epoch]

    def _check_day_reset(self) -> None:
        if time.time() - self._day_start_ts >= 86400:
            self._daily_pnl    = 0.0
            self._day_start_bal = self.bankroll
            self._day_start_ts  = time.time()
            LOGGER.info("[RiskMgr] Day reset. Balance: $%.2f", self.bankroll)
