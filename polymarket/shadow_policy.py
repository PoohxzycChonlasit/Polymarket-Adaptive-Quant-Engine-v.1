"""Shadow Policy Evaluator — passive offline candidate validation.

Evaluates each decision candidate against the offline-identified policy candidate
(min_ev=0.12, min_probability=0.65, risk_mode=NORMAL) and emits structured
telemetry WITHOUT gating, altering, or influencing any execution path.

OBSERVABILITY-ONLY GUARANTEE:
    shadow_policy_decision does NOT gate entry.
    shadow_policy_decision does NOT change the risk plan.
    shadow_policy_decision does NOT affect position sizing.
    shadow_policy_decision does NOT alter order intent.
    shadow_policy_decision does NOT affect execution.

All downstream code that reads this field must be telemetry/logging only.
Source: BACKTEST_ENGINE_V2_POLICY_GRID_EXPANSION_001
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Policy identity constants ─────────────────────────────────────────────

SHADOW_POLICY_ID = "EV012_PROB065_NORMAL_V1"
SHADOW_POLICY_VERSION = "shadow_policy_v1"
SHADOW_POLICY_SOURCE = "BACKTEST_ENGINE_V2_POLICY_GRID_EXPANSION_001"
SHADOW_POLICY_CONFIDENCE = "LOW_STATISTICAL_CONFIDENCE"

SHADOW_MIN_EV: float = 0.12
SHADOW_MIN_PROBABILITY: float = 0.65
SHADOW_ALLOWED_RISK_MODES: tuple[str, ...] = ("NORMAL",)

# ── Reject reason codes ────────────────────────────────────────────────────

REASON_EV_BELOW_THRESHOLD = "EV_BELOW_THRESHOLD"
REASON_PROBABILITY_BELOW_THRESHOLD = "PROBABILITY_BELOW_THRESHOLD"
REASON_RISK_MODE_BLOCKED = "RISK_MODE_BLOCKED"
REASON_MISSING_EV = "MISSING_EV"
REASON_MISSING_PROBABILITY = "MISSING_PROBABILITY"
REASON_MISSING_RISK_MODE = "MISSING_RISK_MODE"

DECISION_ACCEPT = "ACCEPT"
DECISION_REJECT = "REJECT"


@dataclass
class ShadowPolicyResult:
    decision: str
    reasons: list[str] = field(default_factory=list)
    observed_ev: float | None = None
    observed_probability: float | None = None
    observed_risk_mode: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "shadow_policy_id": SHADOW_POLICY_ID,
            "shadow_policy_version": SHADOW_POLICY_VERSION,
            "shadow_policy_decision": self.decision,
            "shadow_policy_reasons": list(self.reasons),
            "shadow_policy_min_ev": SHADOW_MIN_EV,
            "shadow_policy_min_probability": SHADOW_MIN_PROBABILITY,
            "shadow_policy_allowed_risk_modes": list(SHADOW_ALLOWED_RISK_MODES),
            "shadow_policy_observed_ev": self.observed_ev,
            "shadow_policy_observed_probability": self.observed_probability,
            "shadow_policy_observed_risk_mode": self.observed_risk_mode,
            "shadow_policy_confidence": SHADOW_POLICY_CONFIDENCE,
            "shadow_policy_source": SHADOW_POLICY_SOURCE,
        }


class ShadowPolicyEvaluator:
    """Evaluate the offline-identified policy candidate without gating execution.

    Usage::

        evaluator = ShadowPolicyEvaluator()
        result = evaluator.evaluate(ev=0.15, probability=0.68, risk_mode="NORMAL")
        quant_detail.update(result.to_dict())
        # result.decision is logged, never consumed by execution paths
    """

    def evaluate(
        self,
        ev: float | None,
        probability: float | None,
        risk_mode: str | None,
    ) -> ShadowPolicyResult:
        reasons: list[str] = []

        # Normalise risk mode
        rm = str(risk_mode or "").strip().upper()

        # Check for missing inputs first
        if ev is None:
            reasons.append(REASON_MISSING_EV)
        if probability is None:
            reasons.append(REASON_MISSING_PROBABILITY)
        if not rm:
            reasons.append(REASON_MISSING_RISK_MODE)

        # Threshold checks (only when values present)
        if ev is not None and ev < SHADOW_MIN_EV:
            reasons.append(REASON_EV_BELOW_THRESHOLD)
        if probability is not None and probability < SHADOW_MIN_PROBABILITY:
            reasons.append(REASON_PROBABILITY_BELOW_THRESHOLD)
        if rm and rm not in SHADOW_ALLOWED_RISK_MODES:
            reasons.append(REASON_RISK_MODE_BLOCKED)

        decision = DECISION_ACCEPT if not reasons else DECISION_REJECT

        return ShadowPolicyResult(
            decision=decision,
            reasons=reasons,
            observed_ev=float(ev) if ev is not None else None,
            observed_probability=float(probability) if probability is not None else None,
            observed_risk_mode=str(risk_mode or "").strip() or None,
        )
