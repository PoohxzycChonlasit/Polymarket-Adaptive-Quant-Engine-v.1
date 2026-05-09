from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import inf


class BankrollTier(str, Enum):
    T0_MICRO_SEED = "T0_MICRO_SEED"
    T1_MICRO_BUILD = "T1_MICRO_BUILD"
    T2_MICRO_SURVIVAL = "T2_MICRO_SURVIVAL"
    T3_BASE_BUILD = "T3_BASE_BUILD"
    T4_BASE_STABLE = "T4_BASE_STABLE"
    T5_SMALL_GROWTH = "T5_SMALL_GROWTH"
    T6_GROWTH_1 = "T6_GROWTH_1"
    T7_GROWTH_2 = "T7_GROWTH_2"
    T8_GROWTH_3 = "T8_GROWTH_3"
    T9_CAPITAL_1 = "T9_CAPITAL_1"
    T10_CAPITAL_2 = "T10_CAPITAL_2"
    T11_CAPITAL_3 = "T11_CAPITAL_3"
    T12_CAPITAL_PRESERVE = "T12_CAPITAL_PRESERVE"

    # Backward-compatible aliases for older tests/callers.
    SEED_TEST = "T0_MICRO_SEED"
    MICRO = "T1_MICRO_BUILD"
    MICRO_PLUS = "T2_MICRO_SURVIVAL"
    SMALL = "T3_BASE_BUILD"
    SMALL_PLUS = "T4_BASE_STABLE"
    BUILDER = "T5_SMALL_GROWTH"
    GROWTH = "T6_GROWTH_1"
    GROWTH_PLUS = "T7_GROWTH_2"
    SERIOUS = "T8_GROWTH_3"
    CAPITAL_BASE = "T9_CAPITAL_1"
    CAPITAL_PLUS = "T10_CAPITAL_2"
    ADVANCED = "T11_CAPITAL_3"
    PROFESSIONAL = "T12_CAPITAL_PRESERVE"


@dataclass(frozen=True, slots=True)
class BankrollTierConfig:
    tier: BankrollTier
    tier_id: str
    tier_name: str
    lower_bound: float
    upper_bound: float
    family: str
    risk_profile: str
    recommended_max_risk_fraction: float
    min_position_size_hint: float
    max_position_size_hint: float
    runner_allowed_hint: bool
    description: str
    min_risk_pct: float
    max_risk_pct: float
    min_trades_per_hour: int
    max_trades_per_hour: int
    max_market_exposure_pct: float
    kelly_fraction: float = 0.20
    stop_loss_pct: float = 0.80

    @property
    def min_bankroll_usd(self) -> float:
        return self.lower_bound

    @property
    def max_bankroll_usd(self) -> float:
        return self.upper_bound

    @property
    def label(self) -> str:
        return self.tier_id

    @property
    def min_bet(self) -> float:
        return self.min_position_size_hint

    def to_metadata(self) -> dict[str, object]:
        return {
            "tier_id": self.tier_id,
            "tier_name": self.tier_name,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "family": self.family,
            "risk_profile": self.risk_profile,
            "recommended_max_risk_fraction": self.recommended_max_risk_fraction,
            "min_position_size_hint": self.min_position_size_hint,
            "max_position_size_hint": self.max_position_size_hint,
            "runner_allowed_hint": self.runner_allowed_hint,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class BankrollRankLockResult:
    active_tier: BankrollTier
    raw_tier: BankrollTier
    balance: float
    reason: str
    changed: bool
    tier_locked: bool = False
    hysteresis_active: bool = False


def _tier(
    tier: BankrollTier,
    tier_name: str,
    lower: float,
    upper: float,
    family: str,
    risk_profile: str,
    min_risk: float,
    max_risk: float,
    min_trades: int,
    max_trades: int,
    max_market_exposure: float,
    min_position_hint: float,
    max_position_hint: float,
    runner_allowed: bool,
    description: str,
    *,
    kelly_fraction: float,
    stop_loss_pct: float,
) -> BankrollTierConfig:
    return BankrollTierConfig(
        tier=tier,
        tier_id=tier.value,
        tier_name=tier_name,
        lower_bound=lower,
        upper_bound=upper,
        family=family,
        risk_profile=risk_profile,
        recommended_max_risk_fraction=max_risk,
        min_position_size_hint=min_position_hint,
        max_position_size_hint=max_position_hint,
        runner_allowed_hint=runner_allowed,
        description=description,
        min_risk_pct=min_risk,
        max_risk_pct=max_risk,
        min_trades_per_hour=min_trades,
        max_trades_per_hour=max_trades,
        max_market_exposure_pct=max_market_exposure,
        kelly_fraction=kelly_fraction,
        stop_loss_pct=stop_loss_pct,
    )


_TIER_CONFIGS: tuple[BankrollTierConfig, ...] = (
    _tier(BankrollTier.T0_MICRO_SEED, "Micro Seed", 0.0, 25.0, "MICRO", "seed_protection", 0.03, 0.05, 2, 4, 0.10, 0.01, 1.25, False, "Paper validation tier for tiny seed bankrolls.", kelly_fraction=0.10, stop_loss_pct=0.90),
    _tier(BankrollTier.T1_MICRO_BUILD, "Micro Build", 25.0, 50.0, "MICRO", "micro_build", 0.04, 0.06, 3, 5, 0.10, 0.02, 3.00, False, "Micro bankroll building tier with tight exposure limits.", kelly_fraction=0.12, stop_loss_pct=0.88),
    _tier(BankrollTier.T2_MICRO_SURVIVAL, "Micro Survival", 50.0, 100.0, "MICRO", "micro_survival", 0.04, 0.05, 4, 6, 0.09, 0.05, 5.00, False, "Upper micro tier; paper micro-survival remains isolated from standard sizing.", kelly_fraction=0.15, stop_loss_pct=0.85),
    _tier(BankrollTier.T3_BASE_BUILD, "Base Build", 100.0, 250.0, "BASE", "base_build", 0.03, 0.04, 5, 8, 0.08, 0.50, 10.00, False, "First standard bankroll tier; no paper micro-survival behavior.", kelly_fraction=0.20, stop_loss_pct=0.80),
    _tier(BankrollTier.T4_BASE_STABLE, "Base Stable", 250.0, 500.0, "BASE", "base_stable", 0.025, 0.035, 6, 8, 0.07, 0.75, 17.50, True, "Stable base tier with lower per-trade risk than build tiers.", kelly_fraction=0.20, stop_loss_pct=0.78),
    _tier(BankrollTier.T5_SMALL_GROWTH, "Small Growth", 500.0, 1_000.0, "GROWTH", "small_growth", 0.02, 0.03, 6, 10, 0.06, 1.00, 30.00, True, "Small growth tier; sizing remains capped by rank and market exposure.", kelly_fraction=0.22, stop_loss_pct=0.76),
    _tier(BankrollTier.T6_GROWTH_1, "Growth 1", 1_000.0, 2_500.0, "GROWTH", "growth_1", 0.015, 0.025, 6, 10, 0.05, 2.00, 62.50, True, "Growth tier with reduced risk fraction as capital increases.", kelly_fraction=0.25, stop_loss_pct=0.75),
    _tier(BankrollTier.T7_GROWTH_2, "Growth 2", 2_500.0, 5_000.0, "GROWTH", "growth_2", 0.01, 0.02, 5, 8, 0.04, 2.50, 100.00, True, "Mid-growth tier focused on reducing variance.", kelly_fraction=0.25, stop_loss_pct=0.74),
    _tier(BankrollTier.T8_GROWTH_3, "Growth 3", 5_000.0, 10_000.0, "GROWTH", "growth_3", 0.0075, 0.015, 4, 7, 0.035, 5.00, 150.00, True, "Late-growth tier with lower exposure and trade frequency.", kelly_fraction=0.25, stop_loss_pct=0.72),
    _tier(BankrollTier.T9_CAPITAL_1, "Capital 1", 10_000.0, 25_000.0, "CAPITAL", "capital_1", 0.005, 0.0125, 3, 6, 0.03, 10.00, 312.50, True, "Capital tier prioritizing preservation over frequency.", kelly_fraction=0.22, stop_loss_pct=0.70),
    _tier(BankrollTier.T10_CAPITAL_2, "Capital 2", 25_000.0, 50_000.0, "CAPITAL", "capital_2", 0.004, 0.01, 3, 5, 0.025, 15.00, 500.00, True, "Capital tier with tighter max market exposure.", kelly_fraction=0.20, stop_loss_pct=0.70),
    _tier(BankrollTier.T11_CAPITAL_3, "Capital 3", 50_000.0, 100_000.0, "CAPITAL", "capital_3", 0.0025, 0.0075, 2, 4, 0.02, 20.00, 750.00, True, "Large capital tier with conservative risk tapering.", kelly_fraction=0.18, stop_loss_pct=0.70),
    _tier(BankrollTier.T12_CAPITAL_PRESERVE, "Capital Preserve", 100_000.0, inf, "CAPITAL", "capital_preserve", 0.001, 0.005, 1, 3, 0.015, 25.00, 1_000.00, True, "Capital preservation tier; risk tapers toward the minimum as bankroll grows.", kelly_fraction=0.15, stop_loss_pct=0.70),
)

_TIER_INDEX: dict[BankrollTier, int] = {
    config.tier: index for index, config in enumerate(_TIER_CONFIGS)
}


def _tier_from_name(value: str) -> BankrollTier:
    normalized = str(value).strip().upper()
    if normalized in BankrollTier.__members__:
        return BankrollTier.__members__[normalized]
    for tier in BankrollTier:
        if tier.value.upper() == normalized:
            return tier
    raise ValueError(f"Unknown bankroll tier: {value!r}")


def get_bankroll_tier(bankroll: float) -> BankrollTier:
    """Return the raw bankroll tier for the current account balance."""
    bankroll = max(float(bankroll), 0.0)
    for config in _TIER_CONFIGS:
        if config.lower_bound <= bankroll < config.upper_bound:
            return config.tier
    return BankrollTier.T12_CAPITAL_PRESERVE


def get_tier_config(tier_or_bankroll: BankrollTier | str | float | int) -> BankrollTierConfig:
    """Return config by tier, tier name, legacy tier alias, or bankroll amount."""
    if isinstance(tier_or_bankroll, (float, int)):
        tier = get_bankroll_tier(float(tier_or_bankroll))
    elif isinstance(tier_or_bankroll, BankrollTier):
        tier = tier_or_bankroll
    else:
        tier = _tier_from_name(str(tier_or_bankroll))

    for config in _TIER_CONFIGS:
        if config.tier == tier:
            return config
    raise ValueError(f"Unknown bankroll tier: {tier_or_bankroll!r}")


def _coerce_tier(tier_or_bankroll: BankrollTier | str | float | int | None) -> BankrollTier | None:
    if tier_or_bankroll is None:
        return None
    if isinstance(tier_or_bankroll, (float, int)):
        return get_bankroll_tier(float(tier_or_bankroll))
    if isinstance(tier_or_bankroll, BankrollTier):
        return tier_or_bankroll
    return _tier_from_name(str(tier_or_bankroll))


def get_bankroll_tier_with_hysteresis(
    balance: float,
    previous_tier: BankrollTier | str | float | int | None,
    *,
    buffer_pct: float = 0.05,
) -> BankrollTier:
    """Return a tier that upgrades at boundaries and downgrades only after a buffer break."""
    balance = max(float(balance), 0.0)
    raw_tier = get_bankroll_tier(balance)
    previous = _coerce_tier(previous_tier)
    if previous is None:
        return raw_tier

    raw_index = _TIER_INDEX[raw_tier]
    previous_index = _TIER_INDEX[previous]
    if raw_index >= previous_index:
        return raw_tier

    previous_config = get_tier_config(previous)
    downgrade_balance = previous_config.lower_bound * (1.0 - max(float(buffer_pct), 0.0))
    return raw_tier if balance < downgrade_balance else previous


class BankrollRankLock:
    """Stateful session tier lock with downgrade hysteresis."""

    def __init__(
        self,
        initial_tier: BankrollTier | str | float | int | None = None,
        *,
        buffer_pct: float = 0.05,
    ) -> None:
        self.buffer_pct = max(float(buffer_pct), 0.0)
        self._active_tier = _coerce_tier(initial_tier)

    @property
    def active_tier(self) -> BankrollTier | None:
        return self._active_tier

    def reset(self, initial_tier: BankrollTier | str | float | int | None = None) -> None:
        self._active_tier = _coerce_tier(initial_tier)

    def update(self, balance: float) -> BankrollRankLockResult:
        balance = max(float(balance), 0.0)
        raw_tier = get_bankroll_tier(balance)

        if self._active_tier is None:
            self._active_tier = raw_tier
            return BankrollRankLockResult(
                active_tier=raw_tier,
                raw_tier=raw_tier,
                balance=balance,
                reason="initialized",
                changed=True,
            )

        previous_tier = self._active_tier
        active_tier = get_bankroll_tier_with_hysteresis(
            balance,
            previous_tier,
            buffer_pct=self.buffer_pct,
        )
        raw_index = _TIER_INDEX[raw_tier]
        previous_index = _TIER_INDEX[previous_tier]
        active_index = _TIER_INDEX[active_tier]

        if active_tier == previous_tier and raw_tier != active_tier:
            reason = "inside_hysteresis"
        elif active_index > previous_index:
            reason = "upgraded"
        elif active_index < previous_index:
            reason = "downgraded"
        else:
            reason = "raw_match"

        self._active_tier = active_tier
        hysteresis_active = reason == "inside_hysteresis"
        return BankrollRankLockResult(
            active_tier=active_tier,
            raw_tier=raw_tier,
            balance=balance,
            reason=reason,
            changed=active_tier != previous_tier,
            tier_locked=hysteresis_active,
            hysteresis_active=hysteresis_active,
        )


def iter_tier_configs() -> tuple[BankrollTierConfig, ...]:
    return _TIER_CONFIGS


def calculate_base_risk_pct(bankroll: float) -> float:
    """
    Smoothly interpolate risk inside a bankroll tier.

    The configured max risk applies at the lower edge of a tier and the min
    risk applies near the upper edge. Capital preserve accounts taper from
    0.5% toward 0.1% over the first additional $400k above $100k.
    """
    bankroll = max(float(bankroll), 0.0)
    config = get_tier_config(bankroll)

    if config.upper_bound == inf:
        span = 400_000.0
        progress = min(max((bankroll - config.lower_bound) / span, 0.0), 1.0)
    else:
        span = max(config.upper_bound - config.lower_bound, 1e-9)
        progress = min(max((bankroll - config.lower_bound) / span, 0.0), 1.0)

    return config.max_risk_pct - (config.max_risk_pct - config.min_risk_pct) * progress
