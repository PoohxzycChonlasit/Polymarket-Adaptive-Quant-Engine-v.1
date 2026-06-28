"""tests/test_identity_continuity_diagnostics.py

Targeted unit tests for the _identity_continuity_diagnostics function
added to tools/compact_run_summary.py.

Scope: offline observability only.  No runtime, strategy, risk, or
execution logic is tested or altered here.
"""
from __future__ import annotations

import pytest

from tools.runtime.compact_run_summary import _identity_continuity_diagnostics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event(category: str, payload: dict) -> dict:
    """Build a minimal inline event in the format expected by compact_run_summary helpers."""
    return {"_category": category, "payload": payload}


def _decision(trace_id: str, confidence: str = "STRONG") -> dict:
    return _event(
        "decision_log",
        {
            "candidate_trace_id": trace_id,
            "lineage_confidence": confidence,
            "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
        },
    )


def _risk(trace_id: str | None, confidence: str = "STRONG") -> dict:
    payload: dict = {"lifecycle_phase": "ACTIVE_INVENTORY_TRADING"}
    if trace_id:
        payload["candidate_trace_id"] = trace_id
        payload["lineage_confidence"] = confidence
    return _event("risk_log", payload)


def _execution(trace_id: str | None, confidence: str = "STRONG") -> dict:
    payload: dict = {"lifecycle_phase": "ACTIVE_INVENTORY_TRADING"}
    if trace_id:
        payload["candidate_trace_id"] = trace_id
        payload["lineage_confidence"] = confidence
    return _event("execution_log", payload)


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------

def test_identity_continuity_returns_required_keys() -> None:
    result = _identity_continuity_diagnostics([])
    required = {
        "scope",
        "total_events_scanned",
        "total_traced_candidates",
        "identity_continuity_score",
        "deterministic_chain_rate",
        "deterministic_chain_count",
        "direct_chain_count",
        "strong_chain_count",
        "weak_chain_count",
        "proxy_or_unknown_chain_count",
        "orphan_risk_count",
        "orphan_execution_count",
        "orphan_counts_by_producer",
        "decision_to_risk_identity_gap_count",
        "risk_to_execution_identity_gap_count",
        "replay_lineage_gap_rate",
        "producer_trace_coverage",
        "guardrail",
        "interpretation",
    }
    assert required.issubset(result.keys()), f"Missing keys: {required - result.keys()}"


def test_empty_events_produces_zero_metrics() -> None:
    result = _identity_continuity_diagnostics([])
    assert result["total_events_scanned"] == 0
    assert result["total_traced_candidates"] == 0
    assert result["identity_continuity_score"] == 0.0
    assert result["deterministic_chain_rate"] == 0.0
    assert result["orphan_risk_count"] == 0
    assert result["orphan_execution_count"] == 0
    assert result["decision_to_risk_identity_gap_count"] == 0
    assert result["risk_to_execution_identity_gap_count"] == 0
    assert result["replay_lineage_gap_rate"] == 0.0


# ---------------------------------------------------------------------------
# deterministic_chain_rate
# ---------------------------------------------------------------------------

def test_deterministic_chain_rate_perfect_when_all_traces_cross_decision_and_risk() -> None:
    """All traces appear in both decision_log and risk_log => deterministic_chain_rate = 1.0."""
    events = [
        _decision("trace-a"),
        _risk("trace-a"),
        _decision("trace-b"),
        _risk("trace-b"),
    ]
    result = _identity_continuity_diagnostics(events)
    assert result["deterministic_chain_rate"] == 1.0
    assert result["deterministic_chain_count"] == 2
    assert result["total_traced_candidates"] == 2


def test_deterministic_chain_rate_zero_when_decision_traces_never_reach_risk() -> None:
    """Decision traces that never appear in risk_log => deterministic_chain_rate = 0.0."""
    events = [
        _decision("trace-a"),
        _decision("trace-b"),
        _risk(None),   # orphan risk event
    ]
    result = _identity_continuity_diagnostics(events)
    assert result["deterministic_chain_rate"] == 0.0
    assert result["deterministic_chain_count"] == 0


def test_deterministic_chain_rate_partial_when_some_traces_missing_from_risk() -> None:
    events = [
        _decision("trace-a"),
        _risk("trace-a"),    # linked
        _decision("trace-b"),
        # trace-b never reaches risk
    ]
    result = _identity_continuity_diagnostics(events)
    assert result["deterministic_chain_count"] == 1
    assert result["total_traced_candidates"] == 2
    assert result["deterministic_chain_rate"] == 0.5


# ---------------------------------------------------------------------------
# identity_continuity_score
# ---------------------------------------------------------------------------

def test_identity_continuity_score_counts_direct_and_strong() -> None:
    events = [
        _decision("trace-direct", "DIRECT"),
        _decision("trace-strong", "STRONG"),
        _decision("trace-weak", "WEAK"),
        _decision("trace-proxy", "PROXY"),
        _decision("trace-unknown"),  # no lineage_confidence field
    ]
    result = _identity_continuity_diagnostics(events)
    assert result["direct_chain_count"] == 1
    assert result["strong_chain_count"] == 1
    assert result["weak_chain_count"] == 1
    assert result["total_traced_candidates"] == 5
    # DIRECT + STRONG = 2 / 5 = 0.4
    assert result["identity_continuity_score"] == pytest.approx(0.4, abs=1e-4)


# ---------------------------------------------------------------------------
# Orphan counts
# ---------------------------------------------------------------------------

def test_orphan_risk_count_for_events_without_trace_id() -> None:
    events = [
        _risk(None),   # no candidate_trace_id
        _risk(None),   # no candidate_trace_id
        _risk("trace-a"),  # has trace_id — not an orphan
    ]
    result = _identity_continuity_diagnostics(events)
    assert result["orphan_risk_count"] == 2


def test_orphan_execution_count_for_events_without_trace_id() -> None:
    events = [
        _execution(None),
        _execution("trace-a"),  # has trace_id
    ]
    result = _identity_continuity_diagnostics(events)
    assert result["orphan_execution_count"] == 1


def test_orphan_counts_by_producer_includes_all_producers() -> None:
    events = [
        _risk(None),
        _risk(None),
        _execution(None),
        _event("system_health", {"event": "heartbeat"}),  # no trace_id
    ]
    result = _identity_continuity_diagnostics(events)
    counts = result["orphan_counts_by_producer"]
    assert counts.get("risk_log") == 2
    assert counts.get("execution_log") == 1
    assert counts.get("system_health") == 1


# ---------------------------------------------------------------------------
# decision_to_risk_identity_gap_count
# ---------------------------------------------------------------------------

def test_decision_to_risk_gap_zero_when_all_decisions_reach_risk() -> None:
    events = [
        _decision("trace-a"),
        _risk("trace-a"),
        _decision("trace-b"),
        _risk("trace-b"),
    ]
    result = _identity_continuity_diagnostics(events)
    assert result["decision_to_risk_identity_gap_count"] == 0


def test_decision_to_risk_gap_counts_traces_that_never_reach_risk() -> None:
    events = [
        _decision("trace-a"),
        _risk("trace-a"),       # linked
        _decision("trace-b"),   # gap — never seen in risk
        _decision("trace-c"),   # gap — never seen in risk
    ]
    result = _identity_continuity_diagnostics(events)
    assert result["decision_to_risk_identity_gap_count"] == 2


# ---------------------------------------------------------------------------
# risk_to_execution_identity_gap_count
# ---------------------------------------------------------------------------

def test_risk_to_execution_gap_zero_when_all_risk_traces_reach_execution() -> None:
    events = [
        _risk("trace-a"),
        _execution("trace-a"),
    ]
    result = _identity_continuity_diagnostics(events)
    assert result["risk_to_execution_identity_gap_count"] == 0


def test_risk_to_execution_gap_counts_traces_that_never_reach_execution() -> None:
    events = [
        _risk("trace-a"),
        _execution("trace-a"),   # linked
        _risk("trace-b"),        # gap — never seen in execution
    ]
    result = _identity_continuity_diagnostics(events)
    assert result["risk_to_execution_identity_gap_count"] == 1


# ---------------------------------------------------------------------------
# replay_lineage_gap_rate
# ---------------------------------------------------------------------------

def test_replay_lineage_gap_rate_zero_on_perfect_chain() -> None:
    events = [
        _decision("trace-a"),
        _risk("trace-a"),
        _execution("trace-a"),
    ]
    result = _identity_continuity_diagnostics(events)
    assert result["replay_lineage_gap_rate"] == 0.0


def test_replay_lineage_gap_rate_positive_on_broken_chain() -> None:
    events = [
        _decision("trace-a"),   # seen in decision only
        _decision("trace-b"),
        _risk("trace-b"),
        # no execution events
    ]
    result = _identity_continuity_diagnostics(events)
    # decision->risk gap: trace-a not in risk (1)
    # risk->execution gap: trace-b not in execution (1)
    # total_traced = 2
    assert result["replay_lineage_gap_rate"] > 0.0
    assert result["decision_to_risk_identity_gap_count"] == 1


# ---------------------------------------------------------------------------
# producer_trace_coverage
# ---------------------------------------------------------------------------

def test_producer_trace_coverage_counts_unique_traces_per_producer() -> None:
    events = [
        _decision("trace-a"),
        _decision("trace-b"),
        _risk("trace-a"),
        _execution("trace-a"),
    ]
    result = _identity_continuity_diagnostics(events)
    coverage = result["producer_trace_coverage"]
    assert coverage["decision_log"] == 2
    assert coverage["risk_log"] == 1
    assert coverage["execution_log"] == 1


# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------

def test_guardrail_field_present() -> None:
    result = _identity_continuity_diagnostics([])
    assert "guardrail" in result
    assert "Offline observability only" in result["guardrail"]


def test_scope_is_correct() -> None:
    result = _identity_continuity_diagnostics([])
    assert result["scope"] == "offline_identity_continuity_diagnostics_v1"
