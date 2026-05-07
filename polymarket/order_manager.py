from __future__ import annotations

import logging
from dataclasses import dataclass

from polymarket.bankroll_tiers import get_bankroll_tier, get_tier_config
from polymarket.position_sizing import PositionSizingInput, calculate_position_size
from utils.risk_manager import (
    FLOOR_BALANCE,
    RiskPlan,
)


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class OrderRequest:
    market_id: str
    side: str
    entry_price: float
    win_rate: float
    reward_risk_ratio: float
    edge: float = 0.0          # model_prob - entry_price (used for tiered sizing)
    price_to_beat: float = 0.0 # for log display
    spread: float = 0.0
    liquidity_usd: float = 1_000.0
    delta: float = 1.0
    delta_multiplier: float | None = None
    time_remaining_seconds: int = 300
    trades_last_hour: int = 0
    drawdown_pct: float = 0.0
    min_position_size_usd: float = 1.0
    daily_loss_limit_reached: bool = False
    hard_drawdown_reached: bool = False


class PolymarketOrderManager:
    def __init__(
        self,
        account_balance: float,
        max_risk_per_trade: float,
        stop_loss_pct: float,
        kelly_fraction_cap: float,
    ) -> None:
        self.account_balance   = account_balance
        self.max_risk_per_trade = max_risk_per_trade
        self.stop_loss_pct     = stop_loss_pct
        self.kelly_fraction_cap = kelly_fraction_cap

    def _zero_plan(self, request: OrderRequest) -> RiskPlan:
        return RiskPlan(
            account_balance=self.account_balance,
            entry_price=request.entry_price,
            stop_loss_price=request.entry_price,
            take_profit_price=request.entry_price,
            partial_tp_price=request.entry_price,
            risk_amount=0.0,
            kelly_fraction=0.0,
            capped_fraction=0.0,
            position_size=0.0,
            notional_size=0.0,
            stop_loss_pct=self.stop_loss_pct,
        )

    def build_order_plan(self, request: OrderRequest) -> RiskPlan:
        """
        Build a RiskPlan using the Bankroll Rank Engine.

        The active path is quant-style rank sizing, not fixed percentage risk
        and not legacy 20% bankroll exposure.
        """
        balance = self.account_balance
        tier = get_bankroll_tier(balance)
        tier_config = get_tier_config(tier)

        LOGGER.info(
            "Building order plan | market=%s side=%s | balance=$%.2f tier=%s",
            request.market_id, request.side, balance, tier_config.description,
        )

        if balance < FLOOR_BALANCE:
            LOGGER.warning(
                "[FLOOR BREACH] Balance $%.2f < floor $%.2f -- order plan returns zero size",
                balance, FLOOR_BALANCE,
            )
            return self._zero_plan(request)

        ev = request.edge if request.edge != 0 else request.win_rate - request.entry_price
        sizing = calculate_position_size(PositionSizingInput(
            bankroll=balance,
            confidence=request.win_rate,
            ev=ev,
            entry_price=request.entry_price,
            drawdown_pct=request.drawdown_pct,
            spread=request.spread,
            liquidity_usd=request.liquidity_usd,
            delta=request.delta,
            delta_multiplier=request.delta_multiplier,
            time_remaining_seconds=request.time_remaining_seconds,
            trades_last_hour=request.trades_last_hour,
            min_position_size_usd=request.min_position_size_usd,
            daily_loss_limit_reached=request.daily_loss_limit_reached,
            hard_drawdown_reached=request.hard_drawdown_reached,
        ))

        LOGGER.info(sizing.log_line())
        if not sizing.approved:
            LOGGER.warning(
                "[SKIP] sizing blocked | market=%s reasons=%s size=$%.4f",
                request.market_id, ",".join(sizing.blocked_reasons), sizing.final_size_usd,
            )
            return self._zero_plan(request)

        stop_loss_price   = request.entry_price * (1 - self.stop_loss_pct)
        take_profit_price = request.entry_price * (1 + 0.06)
        partial_tp_price  = request.entry_price * (1 + 0.03)

        return RiskPlan(
            account_balance  = balance,
            entry_price      = request.entry_price,
            stop_loss_price  = stop_loss_price,
            take_profit_price= take_profit_price,
            partial_tp_price = partial_tp_price,
            risk_amount      = sizing.final_size_usd,
            kelly_fraction   = 0.0,
            capped_fraction  = sizing.risk_pct_after_multipliers,
            position_size    = sizing.shares,
            notional_size    = sizing.final_size_usd,
            stop_loss_pct    = self.stop_loss_pct,
        )
