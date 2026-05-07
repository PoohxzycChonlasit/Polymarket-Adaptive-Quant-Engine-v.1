from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ExpectedValueTier:
    name: str = "default"
    min_ev: float = 0.02


@dataclass(frozen=True, slots=True)
class ExpectedValueInput:
    p_yes: float
    p_no: float
    yes_ask: float
    no_ask: float
    confidence_score: float
    spread: float
    liquidity: float
    delta: float
    tier: ExpectedValueTier = field(default_factory=ExpectedValueTier)
    confidence_floor: float = 0.54


@dataclass(frozen=True, slots=True)
class ExpectedValueResult:
    approved: bool
    side: str
    ev_yes: float
    ev_no: float
    min_ev: float
    skip_reason: str = ""


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def calculate_binary_ev(p_win: float, ask_price: float) -> float:
    return float(p_win) - float(ask_price)


def calculate_ev(p_win: float, ask_price: float) -> float:
    return calculate_binary_ev(p_win, ask_price)


def dynamic_min_ev(
    *,
    tier: ExpectedValueTier,
    delta: float,
    spread: float,
    liquidity: float,
    confidence_score: float,
) -> float:
    min_ev = float(tier.min_ev)
    abs_delta = abs(float(delta))
    spread = max(float(spread), 0.0)
    liquidity = max(float(liquidity), 0.0)

    if abs_delta < 0.20 and spread <= 0.02 and liquidity >= 1_000.0:
        min_ev -= 0.005

    if abs_delta >= 2.0:
        min_ev += 0.015
    elif abs_delta >= 1.0:
        min_ev += 0.005

    if spread >= 0.08:
        min_ev += 0.020
    elif spread >= 0.04:
        min_ev += 0.010

    if liquidity < 100.0:
        min_ev += 0.015
    elif liquidity < 500.0:
        min_ev += 0.005

    if confidence_score < 0.60:
        min_ev += 0.020
    elif confidence_score < 0.65:
        min_ev += 0.010

    return _clamp(min_ev, 0.005, 0.150)


def evaluate_entry(ev_input: ExpectedValueInput) -> ExpectedValueResult:
    ev_yes = calculate_ev(ev_input.p_yes, ev_input.yes_ask)
    ev_no = calculate_ev(ev_input.p_no, ev_input.no_ask)
    min_ev = dynamic_min_ev(
        tier=ev_input.tier,
        delta=ev_input.delta,
        spread=ev_input.spread,
        liquidity=ev_input.liquidity,
        confidence_score=ev_input.confidence_score,
    )

    if ev_input.confidence_score < ev_input.confidence_floor:
        return ExpectedValueResult(
            approved=False,
            side="SKIP",
            ev_yes=ev_yes,
            ev_no=ev_no,
            min_ev=min_ev,
            skip_reason="confidence_too_low",
        )

    if ev_input.yes_ask <= 0 or ev_input.yes_ask >= 1 or ev_input.no_ask <= 0 or ev_input.no_ask >= 1:
        return ExpectedValueResult(
            approved=False,
            side="SKIP",
            ev_yes=ev_yes,
            ev_no=ev_no,
            min_ev=min_ev,
            skip_reason="invalid_ask_price",
        )

    yes_ok = ev_yes >= min_ev
    no_ok = ev_no >= min_ev

    if yes_ok and ev_yes > ev_no:
        return ExpectedValueResult(True, "YES", ev_yes, ev_no, min_ev)

    if no_ok and ev_no > ev_yes:
        return ExpectedValueResult(True, "NO", ev_yes, ev_no, min_ev)

    return ExpectedValueResult(
        approved=False,
        side="SKIP",
        ev_yes=ev_yes,
        ev_no=ev_no,
        min_ev=min_ev,
        skip_reason="ev_below_threshold",
    )


def choose_best_ev_trade(
    *,
    p_yes: float,
    p_no: float,
    yes_ask: float,
    no_ask: float,
    confidence: float,
    min_ev: float,
    min_confidence: float,
) -> ExpectedValueResult:
    return evaluate_entry(
        ExpectedValueInput(
            p_yes=p_yes,
            p_no=p_no,
            yes_ask=yes_ask,
            no_ask=no_ask,
            confidence_score=confidence,
            spread=0.0,
            liquidity=1_000.0,
            delta=0.0,
            tier=ExpectedValueTier(name="custom", min_ev=min_ev),
            confidence_floor=min_confidence,
        )
    )
