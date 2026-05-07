from __future__ import annotations

from dataclasses import dataclass

from polymarket.bankroll_tiers import BankrollTier, BankrollTierConfig, get_tier_config


COOLDOWN_AFTER_LOSS_SECONDS = 120
COOLDOWN_AFTER_WIN_SECONDS = 30
MIN_SECONDS_BETWEEN_ENTRIES = 30


@dataclass(frozen=True, slots=True)
class TradeFrequencyConfig:
    tier: BankrollTier | str
    cooldown_after_loss: float = COOLDOWN_AFTER_LOSS_SECONDS
    cooldown_after_win: float = COOLDOWN_AFTER_WIN_SECONDS
    min_seconds_between_entries: float = MIN_SECONDS_BETWEEN_ENTRIES
    max_trades_per_market: int = 1
    max_trades_per_hour: int | None = None
    liquidity: float = 1_000.0
    reconciliation_safe: bool = True


@dataclass(frozen=True, slots=True)
class TradeFrequencyState:
    trades_last_hour: int = 0
    trades_for_market: int = 0
    seconds_since_last_entry: float | None = None
    last_trade_result: str = ""
    risk_off: bool = False


@dataclass(frozen=True, slots=True)
class TradeFrequencyInput:
    tier: BankrollTier | str
    trades_last_hour: int = 0
    trades_for_market: int = 0
    seconds_since_last_entry: float | None = None
    last_trade_result: str = ""
    risk_off: bool = False
    reconciliation_safe: bool = True
    max_trades_per_market: int = 1
    liquidity: float = 1_000.0


@dataclass(frozen=True, slots=True)
class TradeFrequencyResult:
    approved: bool
    frequency_multiplier: float
    min_trades_per_hour: int
    max_trades_per_hour: int
    blocked_reasons: tuple[str, ...] = ()


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _tier(tier: BankrollTier | str) -> BankrollTier:
    if isinstance(tier, BankrollTier):
        return tier
    return BankrollTier[str(tier).upper()]


def frequency_multiplier_for_tier(
    config: BankrollTierConfig,
    trades_last_hour: int,
    *,
    liquidity: float = 1_000.0,
) -> float:
    max_trades = max(int(config.max_trades_per_hour), 0)
    if max_trades <= 0:
        return 0.0

    used_ratio = _clamp(trades_last_hour / max_trades, 0.0, 1.0)
    if used_ratio < 0.25:
        multiplier = 1.0
    elif used_ratio < 0.50:
        multiplier = 0.75
    elif used_ratio < 0.75:
        multiplier = 0.50
    else:
        multiplier = 0.25

    if config.tier in {
        BankrollTier.GROWTH,
        BankrollTier.GROWTH_PLUS,
        BankrollTier.SERIOUS,
        BankrollTier.CAPITAL_BASE,
        BankrollTier.CAPITAL_PLUS,
        BankrollTier.ADVANCED,
        BankrollTier.PROFESSIONAL,
    }:
        liquidity_multiplier = _clamp(float(liquidity) / 1_000.0, 0.50, 1.0)
        multiplier *= liquidity_multiplier

    return _clamp(multiplier, 0.20, 1.0)


def calculate_frequency_multiplier(
    state: TradeFrequencyState,
    config: TradeFrequencyConfig,
) -> float:
    tier_config = get_tier_config(_tier(config.tier))
    max_trades = config.max_trades_per_hour if config.max_trades_per_hour is not None else tier_config.max_trades_per_hour
    effective_config = BankrollTierConfig(
        tier=tier_config.tier,
        min_bankroll_usd=tier_config.min_bankroll_usd,
        max_bankroll_usd=tier_config.max_bankroll_usd,
        min_risk_pct=tier_config.min_risk_pct,
        max_risk_pct=tier_config.max_risk_pct,
        min_trades_per_hour=tier_config.min_trades_per_hour,
        max_trades_per_hour=max_trades,
        max_market_exposure_pct=tier_config.max_market_exposure_pct,
    )
    return frequency_multiplier_for_tier(
        effective_config,
        state.trades_last_hour,
        liquidity=config.liquidity,
    )


def can_trade_now(
    state: TradeFrequencyState,
    config: TradeFrequencyConfig,
) -> TradeFrequencyResult:
    return _evaluate_trade_frequency(
        TradeFrequencyInput(
            tier=config.tier,
            trades_last_hour=state.trades_last_hour,
            trades_for_market=state.trades_for_market,
            seconds_since_last_entry=state.seconds_since_last_entry,
            last_trade_result=state.last_trade_result,
            risk_off=state.risk_off,
            reconciliation_safe=config.reconciliation_safe,
            max_trades_per_market=config.max_trades_per_market,
            liquidity=config.liquidity,
        ),
        max_trades_per_hour=config.max_trades_per_hour,
        cooldown_after_loss=config.cooldown_after_loss,
        cooldown_after_win=config.cooldown_after_win,
        min_seconds_between_entries=config.min_seconds_between_entries,
    )


def evaluate_trade_frequency(freq_input: TradeFrequencyInput) -> TradeFrequencyResult:
    return _evaluate_trade_frequency(freq_input)


def _evaluate_trade_frequency(
    freq_input: TradeFrequencyInput,
    *,
    max_trades_per_hour: int | None = None,
    cooldown_after_loss: float = COOLDOWN_AFTER_LOSS_SECONDS,
    cooldown_after_win: float = COOLDOWN_AFTER_WIN_SECONDS,
    min_seconds_between_entries: float = MIN_SECONDS_BETWEEN_ENTRIES,
) -> TradeFrequencyResult:
    config = get_tier_config(_tier(freq_input.tier))
    max_trades = max_trades_per_hour if max_trades_per_hour is not None else config.max_trades_per_hour
    blocked: list[str] = []

    if freq_input.risk_off:
        blocked.append("risk_off")
    if not freq_input.reconciliation_safe:
        blocked.append("reconciliation_unsafe")
    if freq_input.trades_for_market >= freq_input.max_trades_per_market:
        blocked.append("max_trades_per_market_reached")
    if freq_input.trades_last_hour >= max_trades:
        blocked.append("max_trades_per_hour_reached")

    if freq_input.seconds_since_last_entry is not None:
        if freq_input.seconds_since_last_entry < min_seconds_between_entries:
            blocked.append("min_seconds_between_entries")

        result = freq_input.last_trade_result.strip().lower()
        if result == "loss" and freq_input.seconds_since_last_entry < cooldown_after_loss:
            blocked.append("cooldown_after_loss")
        if result == "win" and freq_input.seconds_since_last_entry < cooldown_after_win:
            blocked.append("cooldown_after_win")

    effective_config = BankrollTierConfig(
        tier=config.tier,
        min_bankroll_usd=config.min_bankroll_usd,
        max_bankroll_usd=config.max_bankroll_usd,
        min_risk_pct=config.min_risk_pct,
        max_risk_pct=config.max_risk_pct,
        min_trades_per_hour=config.min_trades_per_hour,
        max_trades_per_hour=max_trades,
        max_market_exposure_pct=config.max_market_exposure_pct,
    )

    return TradeFrequencyResult(
        approved=not blocked,
        frequency_multiplier=frequency_multiplier_for_tier(
            effective_config,
            freq_input.trades_last_hour,
            liquidity=freq_input.liquidity,
        ),
        min_trades_per_hour=config.min_trades_per_hour,
        max_trades_per_hour=max_trades,
        blocked_reasons=tuple(blocked),
    )
