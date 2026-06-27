from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SCHEMA_VERSION = "size_sharp_v1"


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class SizeSharpInput:
    probability: float | None = None
    fair_value: float | None = None
    ev: float | None = None
    ev_after_spread: float | None = None
    confidence: float | None = None
    spread: float | None = None
    depth_usd: float | None = None
    quote_age_ms: int | None = None
    fill_probability: float | None = None
    slippage_risk: float | None = None
    regime: str | None = None
    volatility: float | None = None
    lifecycle_phase: str | None = None
    seconds_remaining: int | None = None
    current_exposure: float | None = None
    market_exposure: float | None = None
    open_position_count: int | None = None
    bankroll_rank: float | None = None
    capital_score: float | None = None
    capital_state: str | None = None
    risk_mode: str | None = None
    alternative_candidate_count: int | None = None
    best_alternative_ev_after_spread: float | None = None
    recent_rejected_opportunity_count: int | None = None
    recent_rejected_best_ev_after_spread: float | None = None
    candidate_rank_in_cycle: int | None = None


@dataclass(frozen=True)
class SizeSharpResult:
    size_sharp: float
    size_sharp_bucket: str
    deployment_state: str
    limiting_factor: str
    penalties: dict[str, float] = field(default_factory=dict)
    boosts: dict[str, float] = field(default_factory=dict)
    confidence_grade: str = "F"
    component_scores: dict[str, float] = field(default_factory=dict)
    hard_caps: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "size_sharp": self.size_sharp,
            "size_sharp_bucket": self.size_sharp_bucket,
            "deployment_state": self.deployment_state,
            "limiting_factor": self.limiting_factor,
            "penalties": dict(self.penalties),
            "boosts": dict(self.boosts),
            "confidence_grade": self.confidence_grade,
            "component_scores": dict(self.component_scores),
            "hard_caps": list(self.hard_caps),
            "missing_inputs": list(self.missing_inputs),
            "schema_version": self.schema_version,
        }


class SizeSharpEngine:
    """Pure, deterministic deployment-quality scorer for observability only."""

    STALE_QUOTE_MS = 3_000
    MAX_SPREAD = 0.10
    MIN_DEPTH_USD = 1.00
    MARKET_EXPOSURE_CONCENTRATION_USD = 10.0
    OPEN_POSITION_CONCENTRATION_COUNT = 5

    WEIGHTS = {
        "signal_edge": 0.30,
        "execution_quality": 0.20,
        "market_state": 0.15,
        "inventory_room": 0.15,
        "capital_alignment": 0.15,
        "opportunity_cost": 0.05,
    }

    def evaluate(self, size_input: SizeSharpInput) -> SizeSharpResult:
        missing = self._missing_inputs(size_input)
        hard_caps = self._hard_caps(size_input, missing)
        component_scores = {
            "signal_edge": self._signal_edge_score(size_input),
            "execution_quality": self._execution_quality_score(size_input),
            "market_state": self._market_state_score(size_input),
            "inventory_room": self._inventory_room_score(size_input),
            "capital_alignment": self._capital_alignment_score(size_input),
            "opportunity_cost": self._opportunity_cost_score(size_input),
        }
        penalties = self._penalties(size_input, missing)
        boosts = self._boosts(size_input)
        base_score = sum(component_scores[name] * weight for name, weight in self.WEIGHTS.items())
        boost_total = min(sum(boosts.values()), 0.10)
        penalty_total = sum(penalties.values())
        cap_limit = self._cap_limit(hard_caps)
        raw_score = base_score + boost_total - penalty_total
        size_sharp = round(_clamp(min(raw_score, cap_limit)), 4)
        bucket = self.bucket_for_score(size_sharp)
        return SizeSharpResult(
            size_sharp=size_sharp,
            size_sharp_bucket=bucket,
            deployment_state=f"OBSERVE_{bucket}",
            limiting_factor=self._limiting_factor(component_scores, penalties, hard_caps, missing),
            penalties={key: round(value, 4) for key, value in penalties.items()},
            boosts={key: round(value, 4) for key, value in boosts.items()},
            confidence_grade=self.confidence_grade_for(missing_count=len(missing), hard_caps=hard_caps),
            component_scores={key: round(value, 4) for key, value in component_scores.items()},
            hard_caps=hard_caps,
            missing_inputs=missing,
        )

    def bucket_for_score(self, score: float) -> str:
        score = _clamp(float(score))
        if score < 0.15:
            return "BLOCKED"
        if score < 0.35:
            return "WEAK"
        if score < 0.55:
            return "WATCH"
        if score < 0.70:
            return "GOOD"
        if score < 0.85:
            return "STRONG"
        return "ELITE"

    def confidence_grade_for(self, *, missing_count: int, hard_caps: list[str]) -> str:
        caps = set(hard_caps)
        if "risk_mode_lockdown" in caps or "closed_or_unsafe" in caps:
            return "F"
        if missing_count >= 7:
            return "F"
        if caps.intersection({"stale_quote", "excessive_spread", "low_depth", "inventory_concentration"}):
            return "D" if missing_count >= 3 else "C"
        if missing_count >= 5:
            return "D"
        if missing_count >= 2:
            return "B"
        if missing_count == 1:
            return "B"
        return "A"

    def _missing_inputs(self, size_input: SizeSharpInput) -> list[str]:
        required = (
            "probability",
            "fair_value",
            "ev_after_spread",
            "spread",
            "depth_usd",
            "quote_age_ms",
            "lifecycle_phase",
            "seconds_remaining",
            "current_exposure",
            "market_exposure",
            "open_position_count",
            "capital_score",
            "capital_state",
            "risk_mode",
        )
        return [name for name in required if getattr(size_input, name) in {None, ""}]

    def _hard_caps(self, size_input: SizeSharpInput, missing: list[str]) -> list[str]:
        caps: list[str] = []
        risk_mode = str(size_input.risk_mode or "").upper()
        capital_state = str(size_input.capital_state or "").upper()
        lifecycle = str(size_input.lifecycle_phase or "").upper()
        spread = _to_float(size_input.spread)
        depth = _to_float(size_input.depth_usd)
        quote_age = _to_float(size_input.quote_age_ms)
        market_exposure = _to_float(size_input.market_exposure) or 0.0
        open_count = int(_to_float(size_input.open_position_count) or 0)

        if risk_mode == "LOCKDOWN":
            caps.append("risk_mode_lockdown")
        if lifecycle == "CLOSED_OR_UNSAFE":
            caps.append("closed_or_unsafe")
        if lifecycle == "FINAL_DERISK":
            caps.append("final_derisk_timing")
        if capital_state == "CRITICAL":
            caps.append("capital_critical")
        if quote_age is not None and quote_age > self.STALE_QUOTE_MS:
            caps.append("stale_quote")
        if spread is not None and spread > self.MAX_SPREAD:
            caps.append("excessive_spread")
        if depth is not None and depth < self.MIN_DEPTH_USD:
            caps.append("low_depth")
        if "ev_after_spread" in missing and size_input.ev is None:
            caps.append("missing_ev")
        if market_exposure >= self.MARKET_EXPOSURE_CONCENTRATION_USD or open_count >= self.OPEN_POSITION_CONCENTRATION_COUNT:
            caps.append("inventory_concentration")
        return caps

    def _cap_limit(self, hard_caps: list[str]) -> float:
        limits = {
            "risk_mode_lockdown": 0.00,
            "closed_or_unsafe": 0.00,
            "final_derisk_timing": 0.20,
            "capital_critical": 0.30,
            "stale_quote": 0.25,
            "excessive_spread": 0.35,
            "low_depth": 0.40,
            "missing_ev": 0.45,
            "inventory_concentration": 0.20,
        }
        if not hard_caps:
            return 1.0
        return min(limits.get(cap, 1.0) for cap in hard_caps)

    def _signal_edge_score(self, size_input: SizeSharpInput) -> float:
        ev = _to_float(size_input.ev_after_spread)
        if ev is None:
            ev = _to_float(size_input.ev)
        ev_score = 0.25 if ev is None else _clamp((ev + 0.02) / 0.14)
        probability = _to_float(size_input.probability)
        fair_value = _to_float(size_input.fair_value)
        confidence = _to_float(size_input.confidence)
        probability_score = 0.50 if probability is None else _clamp(abs(probability - 0.50) / 0.20)
        fair_value_score = 0.50 if fair_value is None else _clamp(abs(fair_value - 0.50) / 0.20)
        confidence_score = 0.50 if confidence is None else _clamp(confidence)
        return _clamp(0.45 * ev_score + 0.20 * probability_score + 0.15 * fair_value_score + 0.20 * confidence_score)

    def _execution_quality_score(self, size_input: SizeSharpInput) -> float:
        spread = _to_float(size_input.spread)
        depth = _to_float(size_input.depth_usd)
        quote_age = _to_float(size_input.quote_age_ms)
        fill_probability = _to_float(size_input.fill_probability)
        slippage_risk = _to_float(size_input.slippage_risk)
        spread_score = 0.50 if spread is None else _clamp(1.0 - (spread / self.MAX_SPREAD))
        depth_score = 0.50 if depth is None else _clamp(depth / 25.0)
        quote_score = 0.50 if quote_age is None else _clamp(1.0 - (quote_age / self.STALE_QUOTE_MS))
        fill_score = 0.50 if fill_probability is None else _clamp(fill_probability)
        slip_score = 0.50 if slippage_risk is None else _clamp(1.0 - slippage_risk)
        return _clamp(0.25 * spread_score + 0.25 * depth_score + 0.20 * quote_score + 0.20 * fill_score + 0.10 * slip_score)

    def _market_state_score(self, size_input: SizeSharpInput) -> float:
        lifecycle = str(size_input.lifecycle_phase or "").upper()
        seconds = _to_float(size_input.seconds_remaining)
        volatility = _to_float(size_input.volatility)
        lifecycle_score = {
            "OPENING_SCAN": 0.70,
            "ACTIVE_INVENTORY_TRADING": 0.90,
            "PROFIT_MANAGEMENT": 0.60,
            "FINAL_DERISK": 0.20,
            "CLOSED_OR_UNSAFE": 0.00,
        }.get(lifecycle, 0.45)
        if seconds is None:
            time_score = 0.50
        elif seconds <= 20:
            time_score = 0.10
        elif seconds <= 45:
            time_score = 0.35
        elif seconds <= 210:
            time_score = 0.85
        else:
            time_score = 0.65
        volatility_score = 0.60 if volatility is None else _clamp(1.0 - volatility)
        return _clamp(0.45 * lifecycle_score + 0.35 * time_score + 0.20 * volatility_score)

    def _inventory_room_score(self, size_input: SizeSharpInput) -> float:
        current = _to_float(size_input.current_exposure) or 0.0
        market = _to_float(size_input.market_exposure) or 0.0
        open_count = _to_float(size_input.open_position_count) or 0.0
        current_score = _clamp(1.0 - current / 50.0)
        market_score = _clamp(1.0 - market / self.MARKET_EXPOSURE_CONCENTRATION_USD)
        count_score = _clamp(1.0 - open_count / self.OPEN_POSITION_CONCENTRATION_COUNT)
        return _clamp(0.35 * current_score + 0.45 * market_score + 0.20 * count_score)

    def _capital_alignment_score(self, size_input: SizeSharpInput) -> float:
        capital_score = _to_float(size_input.capital_score)
        bankroll_rank = _to_float(size_input.bankroll_rank)
        capital_state = str(size_input.capital_state or "").upper()
        risk_mode = str(size_input.risk_mode or "").upper()
        state_score = {"HEALTHY": 1.0, "DEGRADED": 0.55, "CRITICAL": 0.10}.get(capital_state, 0.50)
        mode_score = {"NORMAL": 1.0, "DEFENSIVE": 0.65, "MICRO_RECOVERY": 0.45, "LOCKDOWN": 0.0}.get(risk_mode, 0.50)
        return _clamp(
            0.40 * (capital_score if capital_score is not None else 0.50)
            + 0.20 * (bankroll_rank if bankroll_rank is not None else 0.50)
            + 0.20 * state_score
            + 0.20 * mode_score
        )

    def _opportunity_cost_score(self, size_input: SizeSharpInput) -> float:
        alternatives = _to_float(size_input.alternative_candidate_count) or 0.0
        best_alt_ev = _to_float(size_input.best_alternative_ev_after_spread)
        recent_rejects = _to_float(size_input.recent_rejected_opportunity_count) or 0.0
        rank = _to_float(size_input.candidate_rank_in_cycle)
        score = 1.0
        if alternatives > 0 and best_alt_ev is not None:
            own_ev = _to_float(size_input.ev_after_spread) or _to_float(size_input.ev) or 0.0
            if best_alt_ev > own_ev:
                score -= min(best_alt_ev - own_ev, 0.10) * 3.0
        score -= min(recent_rejects, 5.0) * 0.03
        if rank is not None and rank > 1:
            score -= min(rank - 1.0, 4.0) * 0.06
        return _clamp(score)

    def _penalties(self, size_input: SizeSharpInput, missing: list[str]) -> dict[str, float]:
        spread = _to_float(size_input.spread) or 0.0
        quote_age = _to_float(size_input.quote_age_ms) or 0.0
        depth = _to_float(size_input.depth_usd)
        seconds = _to_float(size_input.seconds_remaining)
        market_exposure = _to_float(size_input.market_exposure) or 0.0
        capital_state = str(size_input.capital_state or "").upper()
        risk_mode = str(size_input.risk_mode or "").upper()
        recent_rejects = _to_float(size_input.recent_rejected_opportunity_count) or 0.0
        return {
            "execution": _clamp(spread / 2.0 + max(quote_age - 1_000, 0.0) / 20_000.0 + (0.08 if depth is not None and depth < self.MIN_DEPTH_USD else 0.0), 0.0, 0.30),
            "market_state": 0.08 if seconds is not None and seconds < 45 else 0.0,
            "inventory": _clamp(market_exposure / 100.0, 0.0, 0.20),
            "capital": 0.12 if capital_state == "CRITICAL" else (0.08 if risk_mode in {"DEFENSIVE", "MICRO_RECOVERY"} else 0.0),
            "opportunity_cost": _clamp(recent_rejects * 0.01, 0.0, 0.08),
            "missing_inputs": _clamp(len(missing) * 0.025, 0.0, 0.20),
        }

    def _boosts(self, size_input: SizeSharpInput) -> dict[str, float]:
        ev = _to_float(size_input.ev_after_spread)
        quote_age = _to_float(size_input.quote_age_ms)
        market_exposure = _to_float(size_input.market_exposure) or 0.0
        open_count = _to_float(size_input.open_position_count) or 0.0
        capital_state = str(size_input.capital_state or "").upper()
        risk_mode = str(size_input.risk_mode or "").upper()
        return {
            "clean_edge": 0.04 if ev is not None and ev >= 0.08 else 0.0,
            "fresh_quote": 0.02 if quote_age is not None and quote_age <= 1_000 else 0.0,
            "healthy_capital": 0.03 if capital_state == "HEALTHY" and risk_mode == "NORMAL" else 0.0,
            "low_inventory": 0.01 if market_exposure <= 0 and open_count <= 1 else 0.0,
        }

    def _limiting_factor(
        self,
        component_scores: dict[str, float],
        penalties: dict[str, float],
        hard_caps: list[str],
        missing: list[str],
    ) -> str:
        if "risk_mode_lockdown" in hard_caps:
            return "risk_mode_lockdown"
        if "closed_or_unsafe" in hard_caps:
            return "closed_or_unsafe"
        if "missing_ev" in hard_caps or missing:
            return "missing_inputs"
        if "stale_quote" in hard_caps:
            return "stale_quote"
        if "excessive_spread" in hard_caps:
            return "execution_spread"
        if "low_depth" in hard_caps:
            return "low_liquidity"
        if "inventory_concentration" in hard_caps:
            return "inventory_concentration"
        if "capital_critical" in hard_caps:
            return "capital_degraded"
        lowest_component = min(component_scores.items(), key=lambda item: item[1])[0]
        highest_penalty = max(penalties.items(), key=lambda item: item[1])[0]
        if penalties[highest_penalty] > 0.05:
            return highest_penalty
        if component_scores[lowest_component] < 0.45:
            return lowest_component
        return "none"

