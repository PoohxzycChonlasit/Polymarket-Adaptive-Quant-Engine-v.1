from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import inf


class BankrollTier(str, Enum):
    SEED_TEST = "SEED_TEST"
    MICRO = "MICRO"
    MICRO_PLUS = "MICRO_PLUS"
    SMALL = "SMALL"
    SMALL_PLUS = "SMALL_PLUS"
    BUILDER = "BUILDER"
    GROWTH = "GROWTH"
    GROWTH_PLUS = "GROWTH_PLUS"
    SERIOUS = "SERIOUS"
    CAPITAL_BASE = "CAPITAL_BASE"
    CAPITAL_PLUS = "CAPITAL_PLUS"
    ADVANCED = "ADVANCED"
    PROFESSIONAL = "PROFESSIONAL"


@dataclass(frozen=True, slots=True)
class BankrollTierConfig:
    tier: BankrollTier
    min_bankroll_usd: float
    max_bankroll_usd: float
    min_risk_pct: float
    max_risk_pct: float
    min_trades_per_hour: int
    max_trades_per_hour: int
    max_market_exposure_pct: float

    @property
    def label(self) -> str:
        return self.tier.value

    @property
    def description(self) -> str:
        return self.tier.value.replace("_", " ").title()


@dataclass(frozen=True, slots=True)
class BankrollRankLockResult:
    active_tier: BankrollTier
    raw_tier: BankrollTier
    balance: float
    reason: str
    changed: bool


_TIER_CONFIGS: tuple[BankrollTierConfig, ...] = (
    BankrollTierConfig(BankrollTier.SEED_TEST, 0.0, 25.0, 0.03, 0.05, 2, 4, 0.10),
    BankrollTierConfig(BankrollTier.MICRO, 25.0, 50.0, 0.04, 0.06, 3, 5, 0.10),
    BankrollTierConfig(BankrollTier.MICRO_PLUS, 50.0, 100.0, 0.04, 0.05, 4, 6, 0.09),
    BankrollTierConfig(BankrollTier.SMALL, 100.0, 250.0, 0.03, 0.04, 5, 8, 0.08),
    BankrollTierConfig(BankrollTier.SMALL_PLUS, 250.0, 500.0, 0.025, 0.035, 6, 8, 0.07),
    BankrollTierConfig(BankrollTier.BUILDER, 500.0, 1_000.0, 0.02, 0.03, 6, 10, 0.06),
    BankrollTierConfig(BankrollTier.GROWTH, 1_000.0, 2_500.0, 0.015, 0.025, 6, 10, 0.05),
    BankrollTierConfig(BankrollTier.GROWTH_PLUS, 2_500.0, 5_000.0, 0.01, 0.02, 5, 8, 0.04),
    BankrollTierConfig(BankrollTier.SERIOUS, 5_000.0, 10_000.0, 0.0075, 0.015, 4, 7, 0.035),
    BankrollTierConfig(BankrollTier.CAPITAL_BASE, 10_000.0, 25_000.0, 0.005, 0.0125, 3, 6, 0.03),
    BankrollTierConfig(BankrollTier.CAPITAL_PLUS, 25_000.0, 50_000.0, 0.004, 0.01, 3, 5, 0.025),
    BankrollTierConfig(BankrollTier.ADVANCED, 50_000.0, 100_000.0, 0.0025, 0.0075, 2, 4, 0.02),
    BankrollTierConfig(BankrollTier.PROFESSIONAL, 100_000.0, inf, 0.001, 0.005, 1, 3, 0.015),
)

_TIER_INDEX: dict[BankrollTier, int] = {
    config.tier: index for index, config in enumerate(_TIER_CONFIGS)
}


def get_bankroll_tier(bankroll: float) -> BankrollTier:
    """Return the bankroll rank for the current account balance."""
    bankroll = max(float(bankroll), 0.0)
    for config in _TIER_CONFIGS:
        if config.min_bankroll_usd <= bankroll < config.max_bankroll_usd:
            return config.tier
    return BankrollTier.PROFESSIONAL


def get_tier_config(tier_or_bankroll: BankrollTier | str | float | int) -> BankrollTierConfig:
    """Return config by tier, tier name, or bankroll amount."""
    if isinstance(tier_or_bankroll, (float, int)):
        tier = get_bankroll_tier(float(tier_or_bankroll))
    elif isinstance(tier_or_bankroll, BankrollTier):
        tier = tier_or_bankroll
    else:
        tier = BankrollTier[str(tier_or_bankroll).upper()]

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
    return BankrollTier[str(tier_or_bankroll).upper()]


class BankrollRankLock:
    """Stateful session tier lock with threshold hysteresis."""

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
        active_tier = previous_tier
        active_index = _TIER_INDEX[active_tier]
        raw_index = _TIER_INDEX[raw_tier]
        reason = "raw_match"

        if raw_index > active_index:
            reason = "inside_hysteresis"
            while _TIER_INDEX[active_tier] < raw_index:
                next_config = _TIER_CONFIGS[_TIER_INDEX[active_tier] + 1]
                upgrade_balance = next_config.min_bankroll_usd * (1.0 + self.buffer_pct)
                if balance > upgrade_balance:
                    active_tier = next_config.tier
                    reason = "upgraded"
                    continue
                break
        elif raw_index < active_index:
            active_config = get_tier_config(active_tier)
            downgrade_balance = active_config.min_bankroll_usd * (1.0 - self.buffer_pct)
            if balance < downgrade_balance:
                active_tier = raw_tier
                reason = "downgraded"
            else:
                reason = "inside_hysteresis"

        self._active_tier = active_tier
        return BankrollRankLockResult(
            active_tier=active_tier,
            raw_tier=raw_tier,
            balance=balance,
            reason=reason,
            changed=active_tier != previous_tier,
        )


def iter_tier_configs() -> tuple[BankrollTierConfig, ...]:
    return _TIER_CONFIGS


def calculate_base_risk_pct(bankroll: float) -> float:
    """
    Smoothly interpolate risk inside a bankroll tier.

    The configured max risk applies at the lower edge of a tier and the min
    risk applies near the upper edge. Professional accounts taper from 0.5%
    toward 0.1% over the first additional $400k above $100k.
    """
    bankroll = max(float(bankroll), 0.0)
    config = get_tier_config(bankroll)

    if config.max_bankroll_usd == inf:
        span = 400_000.0
        progress = min(max((bankroll - config.min_bankroll_usd) / span, 0.0), 1.0)
    else:
        span = max(config.max_bankroll_usd - config.min_bankroll_usd, 1e-9)
        progress = min(max((bankroll - config.min_bankroll_usd) / span, 0.0), 1.0)

    return config.max_risk_pct - (config.max_risk_pct - config.min_risk_pct) * progress
