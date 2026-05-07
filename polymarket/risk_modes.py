from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RiskMode(str, Enum):
    NORMAL = "NORMAL"
    DEFENSIVE = "DEFENSIVE"
    MICRO_RECOVERY = "MICRO_RECOVERY"
    LOCKDOWN = "LOCKDOWN"


@dataclass(frozen=True, slots=True)
class RiskModeDecision:
    mode: RiskMode
    previous_mode: RiskMode
    reason: str
    size_multiplier: float
    allow_new_entries: bool
    changed: bool
    consecutive_losses: int
    drawdown_pct: float
    lockdown_reasons: tuple[str, ...] = ()


@dataclass(slots=True)
class RiskModeState:
    current_mode: RiskMode = RiskMode.NORMAL
    lockdown_reasons: set[str] = field(default_factory=set)

    def trigger_lockdown(self, reason: str) -> None:
        clean = str(reason or "unknown_lockdown").strip() or "unknown_lockdown"
        self.lockdown_reasons.add(clean)

    def update(
        self,
        *,
        consecutive_losses: int,
        drawdown_pct: float,
        hard_drawdown_reached: bool = False,
    ) -> RiskModeDecision:
        previous = self.current_mode
        decision = evaluate_risk_mode(
            consecutive_losses=consecutive_losses,
            drawdown_pct=drawdown_pct,
            lockdown_reasons=tuple(sorted(self.lockdown_reasons)),
            hard_drawdown_reached=hard_drawdown_reached,
            previous_mode=previous,
        )
        self.current_mode = decision.mode
        return decision


def evaluate_risk_mode(
    *,
    consecutive_losses: int,
    drawdown_pct: float,
    lockdown_reasons: tuple[str, ...] = (),
    hard_drawdown_reached: bool = False,
    previous_mode: RiskMode = RiskMode.NORMAL,
) -> RiskModeDecision:
    losses = max(int(consecutive_losses), 0)
    drawdown = max(float(drawdown_pct), 0.0)
    reasons = tuple(str(reason) for reason in lockdown_reasons if str(reason))

    if hard_drawdown_reached or reasons:
        reason = "hard_drawdown" if hard_drawdown_reached else reasons[0]
        return _decision(
            RiskMode.LOCKDOWN,
            previous_mode,
            reason,
            losses,
            drawdown,
            reasons,
        )
    if drawdown >= 0.04:
        return _decision(RiskMode.MICRO_RECOVERY, previous_mode, "drawdown_ge_4pct", losses, drawdown, reasons)
    if losses >= 3:
        return _decision(RiskMode.MICRO_RECOVERY, previous_mode, "losses_ge_3", losses, drawdown, reasons)
    if drawdown >= 0.02:
        return _decision(RiskMode.DEFENSIVE, previous_mode, "drawdown_ge_2pct", losses, drawdown, reasons)
    if losses >= 2:
        return _decision(RiskMode.DEFENSIVE, previous_mode, "losses_ge_2", losses, drawdown, reasons)
    return _decision(RiskMode.NORMAL, previous_mode, "normal", losses, drawdown, reasons)


def trade_quality_allowed(
    mode: RiskMode,
    *,
    confidence: float | None = None,
    grade: str | None = None,
) -> tuple[bool, str]:
    if mode == RiskMode.NORMAL:
        return True, "normal"
    if mode == RiskMode.LOCKDOWN:
        return False, "risk_mode_lockdown"

    clean_grade = str(grade or "").upper().replace(" ", "_")
    if mode == RiskMode.DEFENSIVE:
        if clean_grade in {"A+", "A", "STRONG", "HOT", "BEST"}:
            return True, "grade_ok"
        if confidence is None:
            return False, "risk_mode_missing_quality"
        return (float(confidence) >= 0.65, "confidence_ok" if float(confidence) >= 0.65 else "confidence_below_defensive")

    if clean_grade in {"A+", "STRONGEST", "ELITE", "BEST"}:
        return True, "grade_ok"
    if confidence is None:
        return False, "risk_mode_missing_quality"
    return (float(confidence) >= 0.75, "confidence_ok" if float(confidence) >= 0.75 else "confidence_below_micro_recovery")


def _decision(
    mode: RiskMode,
    previous: RiskMode,
    reason: str,
    consecutive_losses: int,
    drawdown_pct: float,
    lockdown_reasons: tuple[str, ...],
) -> RiskModeDecision:
    return RiskModeDecision(
        mode=mode,
        previous_mode=previous,
        reason=reason,
        size_multiplier=_size_multiplier(mode),
        allow_new_entries=mode != RiskMode.LOCKDOWN,
        changed=mode != previous,
        consecutive_losses=consecutive_losses,
        drawdown_pct=drawdown_pct,
        lockdown_reasons=lockdown_reasons,
    )


def _size_multiplier(mode: RiskMode) -> float:
    if mode == RiskMode.DEFENSIVE:
        return 0.50
    if mode == RiskMode.MICRO_RECOVERY:
        return 0.25
    if mode == RiskMode.LOCKDOWN:
        return 0.0
    return 1.0
