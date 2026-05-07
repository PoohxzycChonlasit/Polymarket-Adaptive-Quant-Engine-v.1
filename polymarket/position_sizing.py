from __future__ import annotations

from dataclasses import dataclass, field

from polymarket.bankroll_tiers import (
    BankrollTier,
    BankrollTierConfig,
    calculate_base_risk_pct,
    get_bankroll_tier,
    get_tier_config,
)
from polymarket.delta_engine import delta_multiplier_for_score
from polymarket.trade_frequency import frequency_multiplier_for_tier


@dataclass(frozen=True, slots=True)
class PositionSizingInput:
    bankroll: float
    confidence: float
    ev: float
    entry_price: float = 0.50
    drawdown_pct: float = 0.0
    spread: float = 0.0
    liquidity_usd: float = 1_000.0
    delta: float = 1.0
    delta_multiplier: float | None = None
    time_remaining_seconds: int = 300
    trades_last_hour: int = 0
    min_position_size_usd: float = 1.0
    daily_loss_limit_reached: bool = False
    hard_drawdown_reached: bool = False
    confidence_floor: float = 0.54
    max_spread: float = 0.10
    min_liquidity_usd: float = 10.0
    daily_loss_limit_pct: float = 0.08
    hard_drawdown_pct: float = 0.15
    good_liquidity_usd: float = 1_000.0
    good_ev: float = 0.08
    good_delta: float = 1.0
    good_time_remaining_seconds: int = 240


@dataclass(frozen=True, slots=True)
class PositionSizingResult:
    approved: bool
    final_size_usd: float
    shares: float
    bankroll: float
    tier: BankrollTier
    tier_config: BankrollTierConfig
    tier_base_risk_pct: float
    confidence_multiplier: float
    ev_multiplier: float
    drawdown_multiplier: float
    liquidity_multiplier: float
    spread_multiplier: float
    time_to_settlement_multiplier: float
    delta_multiplier: float
    frequency_multiplier: float
    blocked_reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def risk_pct_after_multipliers(self) -> float:
        if self.bankroll <= 0:
            return 0.0
        return self.final_size_usd / self.bankroll

    def log_line(self) -> str:
        status = "APPROVED" if self.approved else "BLOCKED"
        reasons = ",".join(self.blocked_reasons) if self.blocked_reasons else "none"
        return (
            "[BANKROLL_RANK] "
            f"{status} tier={self.tier.value} bankroll=${self.bankroll:.2f} "
            f"base_risk={self.tier_base_risk_pct * 100:.2f}% "
            f"final=${self.final_size_usd:.2f} "
            f"risk={self.risk_pct_after_multipliers * 100:.2f}% "
            f"reasons={reasons}"
        )


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _zero_result(
    sizing_input: PositionSizingInput,
    blocked_reasons: list[str],
    *,
    confidence_multiplier: float = 0.0,
    ev_multiplier: float = 0.0,
    drawdown_multiplier: float = 0.0,
    liquidity_multiplier: float = 0.0,
    spread_multiplier: float = 0.0,
    time_to_settlement_multiplier: float = 0.0,
    delta_multiplier: float = 0.0,
    frequency_multiplier: float = 0.0,
) -> PositionSizingResult:
    tier = get_bankroll_tier(sizing_input.bankroll)
    config = get_tier_config(tier)
    return PositionSizingResult(
        approved=False,
        final_size_usd=0.0,
        shares=0.0,
        bankroll=sizing_input.bankroll,
        tier=tier,
        tier_config=config,
        tier_base_risk_pct=calculate_base_risk_pct(sizing_input.bankroll),
        confidence_multiplier=confidence_multiplier,
        ev_multiplier=ev_multiplier,
        drawdown_multiplier=drawdown_multiplier,
        liquidity_multiplier=liquidity_multiplier,
        spread_multiplier=spread_multiplier,
        time_to_settlement_multiplier=time_to_settlement_multiplier,
        delta_multiplier=delta_multiplier,
        frequency_multiplier=frequency_multiplier,
        blocked_reasons=tuple(blocked_reasons),
    )


def _build_multipliers(sizing_input: PositionSizingInput, config: BankrollTierConfig) -> dict[str, float]:
    confidence_span = max(0.75 - sizing_input.confidence_floor, 1e-9)
    confidence_multiplier = _clamp(
        0.25 + 0.75 * ((sizing_input.confidence - sizing_input.confidence_floor) / confidence_span),
        0.0,
        1.0,
    )

    ev_multiplier = _clamp(sizing_input.ev / max(sizing_input.good_ev, 1e-9), 0.20, 1.0)

    soft_drawdown = max(sizing_input.daily_loss_limit_pct, 1e-9)
    drawdown_multiplier = _clamp(1.0 - 0.75 * (sizing_input.drawdown_pct / soft_drawdown), 0.10, 1.0)

    liquidity_multiplier = _clamp(
        sizing_input.liquidity_usd / max(sizing_input.good_liquidity_usd, 1e-9),
        0.25,
        1.0,
    )

    spread_multiplier = _clamp(1.0 - 0.80 * (sizing_input.spread / max(sizing_input.max_spread, 1e-9)), 0.20, 1.0)

    time_window = max(sizing_input.good_time_remaining_seconds - 90, 1)
    time_to_settlement_multiplier = _clamp(
        0.35 + 0.65 * ((sizing_input.time_remaining_seconds - 90) / time_window),
        0.0,
        1.0,
    )

    if sizing_input.delta_multiplier is None:
        delta_multiplier = delta_multiplier_for_score(abs(sizing_input.delta))
    else:
        delta_multiplier = _clamp(float(sizing_input.delta_multiplier), 0.0, 1.0)

    frequency_multiplier = frequency_multiplier_for_tier(
        config,
        sizing_input.trades_last_hour,
        liquidity=sizing_input.liquidity_usd,
    )

    return {
        "confidence_multiplier": confidence_multiplier,
        "ev_multiplier": ev_multiplier,
        "drawdown_multiplier": drawdown_multiplier,
        "liquidity_multiplier": liquidity_multiplier,
        "spread_multiplier": spread_multiplier,
        "time_to_settlement_multiplier": time_to_settlement_multiplier,
        "delta_multiplier": delta_multiplier,
        "frequency_multiplier": frequency_multiplier,
    }


def calculate_position_size(sizing_input: PositionSizingInput) -> PositionSizingResult:
    tier = get_bankroll_tier(sizing_input.bankroll)
    config = get_tier_config(tier)
    base_risk_pct = calculate_base_risk_pct(sizing_input.bankroll)
    multipliers = _build_multipliers(sizing_input, config)

    blocked: list[str] = []
    if sizing_input.bankroll <= 0:
        blocked.append("invalid_bankroll")
    if sizing_input.daily_loss_limit_reached or sizing_input.drawdown_pct >= sizing_input.daily_loss_limit_pct:
        blocked.append("daily_loss_limit_reached")
    if sizing_input.hard_drawdown_reached or sizing_input.drawdown_pct >= sizing_input.hard_drawdown_pct:
        blocked.append("hard_drawdown_reached")
    if sizing_input.time_remaining_seconds <= 90:
        blocked.append("time_remaining_le_90s")
    if sizing_input.confidence < sizing_input.confidence_floor:
        blocked.append("confidence_too_low")
    if sizing_input.ev <= 0:
        blocked.append("ev_not_positive")
    if sizing_input.spread > sizing_input.max_spread:
        blocked.append("spread_too_wide")
    if sizing_input.liquidity_usd < sizing_input.min_liquidity_usd:
        blocked.append("liquidity_too_low")
    if sizing_input.trades_last_hour >= config.max_trades_per_hour:
        blocked.append("max_trades_per_hour_reached")

    if blocked:
        return _zero_result(sizing_input, blocked, **multipliers)

    final_size = sizing_input.bankroll * base_risk_pct
    for multiplier in multipliers.values():
        final_size *= multiplier

    final_size = round(max(final_size, 0.0), 6)
    shares = round(final_size / max(sizing_input.entry_price, 1e-9), 6)

    requested_min_size = max(float(sizing_input.min_position_size_usd), 0.0)
    effective_min_size = min(requested_min_size, max(sizing_input.bankroll * base_risk_pct * 0.10, 0.01))
    if final_size < effective_min_size:
        return PositionSizingResult(
            approved=False,
            final_size_usd=final_size,
            shares=shares,
            bankroll=sizing_input.bankroll,
            tier=tier,
            tier_config=config,
            tier_base_risk_pct=base_risk_pct,
            blocked_reasons=("below_min_position_size",),
            **multipliers,
        )

    return PositionSizingResult(
        approved=True,
        final_size_usd=final_size,
        shares=shares,
        bankroll=sizing_input.bankroll,
        tier=tier,
        tier_config=config,
        tier_base_risk_pct=base_risk_pct,
        blocked_reasons=(),
        **multipliers,
    )
