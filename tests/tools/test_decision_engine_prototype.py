import ast
import json
from pathlib import Path

import pytest

from tools.decision.decision_engine_prototype import (
    PASS_CONTEXT,
    REJECT_BAD_EV,
    REJECT_BAD_PROBABILITY,
    REJECT_LOW_EVIDENCE,
    REJECT_MISSING_CONTEXT,
    REVIEW_REQUIRED,
    validate_trade_context,
)


def _good_context_row(**overrides):
    row = {
        "schema_version": "canonical_trade_context.v1",
        "trade_id": "trade-001",
        "asset": "BTC",
        "condition_id": "condition-001",
        "outcome": "YES",
        "intended_price": 0.45,
        "intended_size": 10.0,
        "intended_notional": 4.5,
        "true_probability": 0.62,
        "probability": 0.62,
        "fair_value": 0.62,
        "ev": 0.17,
        "ev_after_spread": 0.14,
        "quote_age_ms": 250,
        "slippage": 0.0,
        "data_quality_grade": "A",
        "join_confidence": "HIGH",
        "source_streams": ["trade_journal", "decision_log", "execution_log"],
        "missing_fields": [],
        "counterfactual_available": True,
    }
    row.update(overrides)
    return row


def test_good_canonical_row_passes_context_validation():
    diagnostic = validate_trade_context(_good_context_row())

    assert diagnostic["schema_version"] == "decision_engine_prototype.v1"
    assert diagnostic["decision_state"] == PASS_CONTEXT
    assert diagnostic["confidence"] == "HIGH"
    assert diagnostic["missing_fields"] == []
    assert diagnostic["reject_reasons"] == []
    assert diagnostic["probability_quality"]["status"] == "PASS"
    assert diagnostic["ev_quality"]["status"] == "PASS"
    assert diagnostic["liquidity_quality"]["status"] == "PASS"
    assert diagnostic["availability_quality"]["status"] == "PASS"


def test_missing_intended_price_rejects_missing_context():
    row = _good_context_row(intended_price=None)

    diagnostic = validate_trade_context(row)

    assert diagnostic["decision_state"] == REJECT_MISSING_CONTEXT
    assert "intended_price" in diagnostic["missing_fields"]
    assert "missing_required_context" in diagnostic["reject_reasons"]
    assert diagnostic["availability_quality"]["status"] == "FAIL"


def test_missing_true_probability_rejects_missing_context():
    row = _good_context_row(true_probability=None, probability=None)

    diagnostic = validate_trade_context(row)

    assert diagnostic["decision_state"] == REJECT_MISSING_CONTEXT
    assert "true_probability" in diagnostic["missing_fields"]
    assert diagnostic["probability_quality"]["status"] == "MISSING"
    assert "missing_required_context" in diagnostic["reject_reasons"]


def test_invalid_probability_rejects_bad_probability():
    row = _good_context_row(true_probability=1.4, probability=1.4)

    diagnostic = validate_trade_context(row)

    assert diagnostic["decision_state"] == REJECT_BAD_PROBABILITY
    assert diagnostic["probability_quality"]["status"] == "FAIL"
    assert "invalid_probability" in diagnostic["reject_reasons"]


def test_nonpositive_ev_after_spread_rejects_bad_ev():
    row = _good_context_row(ev_after_spread=0.0)

    diagnostic = validate_trade_context(row)

    assert diagnostic["decision_state"] == REJECT_BAD_EV
    assert diagnostic["ev_quality"]["status"] == "FAIL"
    assert "invalid_ev_after_spread" in diagnostic["reject_reasons"]


def test_missing_ev_after_spread_rejects_missing_context():
    row = _good_context_row(ev_after_spread=None)

    diagnostic = validate_trade_context(row)

    assert diagnostic["decision_state"] == REJECT_MISSING_CONTEXT
    assert "ev_after_spread" in diagnostic["missing_fields"]
    assert diagnostic["ev_quality"]["status"] == "MISSING"


def test_missing_severity_buckets_are_empty_for_complete_context():
    diagnostic = validate_trade_context(_good_context_row())

    assert diagnostic["missing_critical_fields"] == []
    assert diagnostic["missing_high_fields"] == []
    assert diagnostic["missing_medium_fields"] == []
    assert diagnostic["missing_low_fields"] == []
    assert diagnostic["missing_info_fields"] == []


def test_missing_critical_fields_still_reject():
    diagnostic = validate_trade_context(_good_context_row(ev_after_spread=None, missing_fields=["bankroll_rank"]))

    assert diagnostic["decision_state"] == REJECT_MISSING_CONTEXT
    assert diagnostic["missing_critical_fields"] == ["ev_after_spread"]
    assert diagnostic["missing_info_fields"] == ["bankroll_rank"]
    assert "missing_required_context" in diagnostic["reject_reasons"]


def test_missing_high_fields_require_review():
    diagnostic = validate_trade_context(_good_context_row(missing_fields=["quote_age_ms", "risk_mode"]))

    assert diagnostic["decision_state"] == REVIEW_REQUIRED
    assert diagnostic["missing_high_fields"] == ["quote_age_ms", "risk_mode"]
    assert diagnostic["availability_quality"]["status"] == "REVIEW"
    assert "noncritical_context_missing" in diagnostic["notes"]


def test_missing_medium_fields_require_review_in_strict_v1():
    diagnostic = validate_trade_context(_good_context_row(missing_fields=["signal_name"]))

    assert diagnostic["decision_state"] == REVIEW_REQUIRED
    assert diagnostic["missing_medium_fields"] == ["signal_name"]
    assert diagnostic["availability_quality"]["status"] == "REVIEW"


def test_missing_low_fields_pass_with_ignored_note():
    diagnostic = validate_trade_context(_good_context_row(missing_fields=["blockers", "exit_reason"]))

    assert diagnostic["decision_state"] == PASS_CONTEXT
    assert diagnostic["missing_low_fields"] == ["blockers", "exit_reason"]
    assert diagnostic["availability_quality"]["status"] == "PASS"
    assert "ignored_missing_fields_present" in diagnostic["notes"]
    assert "noncritical_context_missing" not in diagnostic["notes"]


def test_missing_info_fields_pass_with_ignored_note():
    diagnostic = validate_trade_context(_good_context_row(missing_fields=["bankroll_rank", "capital_score", "size_sharp_at_entry"]))

    assert diagnostic["decision_state"] == PASS_CONTEXT
    assert diagnostic["missing_info_fields"] == ["bankroll_rank", "capital_score", "size_sharp_at_entry"]
    assert diagnostic["availability_quality"]["status"] == "PASS"
    assert "ignored_missing_fields_present" in diagnostic["notes"]


def test_mixed_high_and_ignored_fields_review():
    diagnostic = validate_trade_context(_good_context_row(missing_fields=["risk_mode", "bankroll_rank", "blockers"]))

    assert diagnostic["decision_state"] == REVIEW_REQUIRED
    assert diagnostic["missing_high_fields"] == ["risk_mode"]
    assert diagnostic["missing_low_fields"] == ["blockers"]
    assert diagnostic["missing_info_fields"] == ["bankroll_rank"]


def test_unknown_missing_field_defaults_to_review():
    diagnostic = validate_trade_context(_good_context_row(missing_fields=["new_schema_field_x"]))

    assert diagnostic["decision_state"] == REVIEW_REQUIRED
    assert diagnostic["missing_medium_fields"] == ["new_schema_field_x"]
    assert diagnostic["availability_quality"]["status"] == "REVIEW"


def test_missing_severity_buckets_preserve_raw_missing_fields():
    diagnostic = validate_trade_context(_good_context_row(missing_fields=["risk_mode", "blockers", "size_sharp_at_entry"]))

    assert diagnostic["missing_fields"] == ["risk_mode", "blockers", "size_sharp_at_entry"]
    assert diagnostic["missing_high_fields"] == ["risk_mode"]
    assert diagnostic["missing_low_fields"] == ["blockers"]
    assert diagnostic["missing_info_fields"] == ["size_sharp_at_entry"]


def test_weak_evidence_grade_rejects_low_evidence():
    row = _good_context_row(data_quality_grade="D", join_confidence="LOW")

    diagnostic = validate_trade_context(row)

    assert diagnostic["decision_state"] == REJECT_LOW_EVIDENCE
    assert diagnostic["evidence_quality"]["status"] == "FAIL"
    assert "low_evidence_quality" in diagnostic["reject_reasons"]


def test_missing_liquidity_context_requires_review_without_rejecting_core_context():
    row = _good_context_row(quote_age_ms=None, slippage=None, source_streams=["trade_journal", "decision_log"])

    diagnostic = validate_trade_context(row)

    assert diagnostic["decision_state"] == REVIEW_REQUIRED
    assert diagnostic["liquidity_quality"]["status"] == "REVIEW"
    assert diagnostic["reject_reasons"] == []
    assert "liquidity_context_missing" in diagnostic["notes"]


@pytest.mark.parametrize(
    ("case_name", "overrides", "expected_state"),
    [
        ("complete_context", {}, PASS_CONTEXT),
        ("missing_core_context", {"intended_price": None}, REJECT_MISSING_CONTEXT),
        ("bad_probability", {"true_probability": -0.1, "probability": -0.1}, REJECT_BAD_PROBABILITY),
        ("bad_ev", {"ev_after_spread": -0.01}, REJECT_BAD_EV),
        ("low_evidence", {"data_quality_grade": "D", "join_confidence": "LOW"}, REJECT_LOW_EVIDENCE),
        ("liquidity_review", {"quote_age_ms": None, "slippage": None, "source_streams": ["trade_journal", "decision_log"]}, REVIEW_REQUIRED),
    ],
)
def test_fixture_matrix_covers_all_decision_states(case_name, overrides, expected_state):
    diagnostic = validate_trade_context(_good_context_row(trade_id=f"fixture-{case_name}", **overrides))

    assert diagnostic["decision_state"] == expected_state


def test_diagnostic_is_json_serializable():
    diagnostic = validate_trade_context(_good_context_row())

    encoded = json.dumps(diagnostic, sort_keys=True)

    assert "decision_engine_prototype.v1" in encoded


def test_decision_engine_prototype_has_no_runtime_imports():
    source_path = Path("tools/decision/decision_engine_prototype.py")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    forbidden_roots = {"polymarket", "config", "utils"}
    assert imported_roots.isdisjoint(forbidden_roots)
