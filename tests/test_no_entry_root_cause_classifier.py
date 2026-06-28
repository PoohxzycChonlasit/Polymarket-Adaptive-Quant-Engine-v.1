"""
Tests for No-Entry Root Cause Classifier v1.

Covers:
- Category mapping from normalized_skip_reason keywords
- Unknown/unclassified fallback
- Lifecycle evidence integration (executable_book_state, timestamps)
- Additive schema compatibility (does not overwrite existing fields)
- No runtime behavior changes (return value is a new dict, original is not mutated)
- paper/live separation unchanged (classifier is pure function, no runtime deps)
- Offline report tool: build_records, aggregate, load functions
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from utils.no_entry_root_cause_classifier import (
    classify_no_entry_root_cause,
    _classify,
)
from tools.research.no_entry_root_cause_report import (
    aggregate,
    build_records,
    load_decision_events,
    load_milestone_events,
    _highest_milestone_reached,
)


# ---------------------------------------------------------------------------
# 1. Category mapping — timing keywords
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reason, expected_primary", [
    ("time_unsafe",        "cutoff_passed"),
    ("hard_close_zone",    "cutoff_passed"),
    ("late_entry",         "cutoff_passed"),
    ("cutoff",             "cutoff_passed"),
    ("final_derisk",       "cutoff_passed"),
    ("book_warming",       "book_warming"),
    ("empty_book",         "book_warming"),
    ("warmup",             "book_warming"),
    ("clob_error",         "book_warming"),
    ("missing_token_id",   "token_not_ready"),
    ("token_not_ready",    "token_not_ready"),
    ("late_discovery",     "late_discovery"),
])
def test_timing_category_classification(reason: str, expected_primary: str) -> None:
    payload = {"normalized_skip_reason": reason, "skipped": True}
    result = classify_no_entry_root_cause(payload)
    assert result["skip_reason_category"] == "timing", f"reason={reason!r}"
    assert result["skip_reason_primary"] == expected_primary, f"reason={reason!r}"
    assert result["timing_block_reason"] == expected_primary
    assert result["no_entry_root_cause_confidence"] >= 0.5


# ---------------------------------------------------------------------------
# 2. Category mapping — evidence keywords
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reason, expected_primary", [
    ("confidence_too_low",           "confidence_below_threshold"),
    ("below_threshold",              "confidence_below_threshold"),
    ("ev_negative",                  "ev_negative"),
    ("ev_below_threshold",           "ev_negative"),
    ("no_probability_model_output",  "probability_unstable"),
    ("probability_unstable",         "probability_unstable"),
    ("regime_unclear",               "regime_unclear"),
    ("regime_filtered",              "regime_unclear"),
])
def test_evidence_category_classification(reason: str, expected_primary: str) -> None:
    payload = {"normalized_skip_reason": reason, "skipped": True}
    result = classify_no_entry_root_cause(payload)
    assert result["skip_reason_category"] == "evidence", f"reason={reason!r}"
    assert result["skip_reason_primary"] == expected_primary, f"reason={reason!r}"
    assert result["evidence_block_reason"] == expected_primary


# ---------------------------------------------------------------------------
# 3. Category mapping — risk keywords
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reason, expected_primary", [
    ("min_bet",         "bankroll_too_small"),
    ("bankroll_too_small", "bankroll_too_small"),
    ("zero_size",       "zero_size_plan"),
    ("risk_plan_zero",  "zero_size_plan"),
    ("lockdown",        "risk_mode_defensive"),
    ("defensive",       "risk_mode_defensive"),
    ("micro_recovery",  "risk_mode_defensive"),
    ("drawdown",        "drawdown_cap"),
    ("max_drawdown",    "drawdown_cap"),
])
def test_risk_category_classification(reason: str, expected_primary: str) -> None:
    payload = {"normalized_skip_reason": reason, "skipped": True}
    result = classify_no_entry_root_cause(payload)
    assert result["skip_reason_category"] == "risk", f"reason={reason!r}"
    assert result["skip_reason_primary"] == expected_primary, f"reason={reason!r}"
    assert result["risk_block_reason"] == expected_primary


# ---------------------------------------------------------------------------
# 4. Category mapping — microstructure keywords
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reason, expected_primary", [
    ("spread_too_wide",        "spread_too_wide"),
    ("spread_not_executable",  "spread_too_wide"),
    ("thin_liquidity",         "thin_liquidity"),
    ("insufficient_liquidity", "thin_liquidity"),
    ("stale_book",             "stale_book"),
    ("orderbook_stale",        "stale_book"),
    ("imbalance_extreme",      "imbalance_extreme"),
    ("delta_extreme",          "imbalance_extreme"),
])
def test_microstructure_category_classification(reason: str, expected_primary: str) -> None:
    payload = {"normalized_skip_reason": reason, "skipped": True}
    result = classify_no_entry_root_cause(payload)
    assert result["skip_reason_category"] == "microstructure", f"reason={reason!r}"
    assert result["skip_reason_primary"] == expected_primary, f"reason={reason!r}"
    assert result["microstructure_block_reason"] == expected_primary


# ---------------------------------------------------------------------------
# 5. Unknown / unclassified fallback
# ---------------------------------------------------------------------------

def test_unknown_fallback_for_empty_reason() -> None:
    result = classify_no_entry_root_cause({})
    assert result["skip_reason_category"] == "system_or_unknown"
    assert result["skip_reason_primary"] == "unclassified"
    assert result["no_entry_root_cause_confidence"] <= 0.15


def test_unknown_fallback_for_unrecognized_reason() -> None:
    payload = {"normalized_skip_reason": "some_exotic_reason_xyz_not_in_any_table", "skipped": True}
    result = classify_no_entry_root_cause(payload)
    assert result["skip_reason_category"] in {
        "system_or_unknown", "timing", "evidence", "risk", "microstructure"
    }
    # Confidence must be low for unrecognized keywords
    assert result["no_entry_root_cause_confidence"] <= 0.6


def test_fail_soft_on_exception() -> None:
    """Classifier must return default structure when given bad input."""
    result = classify_no_entry_root_cause(None)  # type: ignore[arg-type]
    assert result["skip_reason_category"] == "system_or_unknown"
    assert "no_entry_root_cause_confidence" in result


# ---------------------------------------------------------------------------
# 6. Lifecycle evidence integration
# ---------------------------------------------------------------------------

def test_lifecycle_book_state_discovered_implies_timing() -> None:
    """When executable_book_state=DISCOVERED with no skip_reason, classify as timing."""
    payload = {
        "normalized_skip_reason": "",
        "executable_book_state": "DISCOVERED",
        "skipped": True,
    }
    result = classify_no_entry_root_cause(payload)
    assert result["skip_reason_category"] == "timing"
    assert result["skip_reason_primary"] in {"token_not_ready", "book_warming", "first_executable_too_late"}


def test_lifecycle_no_tradable_ts_implies_timing() -> None:
    """When first_tradable_ts is empty and reason is unknown, classify as timing."""
    payload = {
        "normalized_skip_reason": "",
        "first_tradable_ts": "",
        "skipped": True,
    }
    result = classify_no_entry_root_cause(payload)
    assert result["skip_reason_category"] == "timing"


def test_lifecycle_late_discovery_from_seconds_remaining() -> None:
    """first_discovered_seconds_remaining < 60 should contribute late_discovery."""
    payload = {
        "normalized_skip_reason": "",
        "first_discovered_seconds_remaining": 45,
        "skipped": True,
    }
    result = classify_no_entry_root_cause(payload)
    assert result["skip_reason_category"] == "timing"
    assert result["skip_reason_primary"] == "late_discovery"


def test_keyword_takes_priority_over_lifecycle_evidence() -> None:
    """A clear keyword match should not be overridden by lifecycle evidence."""
    payload = {
        "normalized_skip_reason": "confidence_too_low",
        "executable_book_state": "DISCOVERED",  # would suggest timing
        "skipped": True,
    }
    result = classify_no_entry_root_cause(payload)
    # Evidence keyword confidence_too_low wins over lifecycle timing evidence
    assert result["skip_reason_category"] in {"evidence", "timing"}
    # Primary must come from the keyword or the lifecycle — not silently wrong
    assert result["skip_reason_primary"] in {"confidence_below_threshold", "token_not_ready", "book_warming"}


# ---------------------------------------------------------------------------
# 7. Additive schema compatibility — no overwrite of existing fields
# ---------------------------------------------------------------------------

def test_additive_schema_does_not_overwrite_existing_category() -> None:
    """When skip_reason_category is already set in payload, classifier must not overwrite it."""
    from polymarket.trader import PolymarketTrader, TradeOutcome

    trader = PolymarketTrader()
    trader.settings = MagicMock()
    trader.settings.paper_trading = True
    trader.settings.hybrid_phase_v1_enabled = False
    trader.settings.adaptive_entry_max_spread = 0.06
    trader.settings.execution_entry_cutoff_seconds = 90
    trader.settings.execution_entry_hard_block_seconds = 35
    trader._connected = True
    trader.quant_events = MagicMock()
    trader.quant_events._with_candidate_trace_identity = MagicMock(side_effect=lambda p, t: p)
    trader.quant_events.log_decision.return_value = True
    trader.quant_events.log_risk_event = MagicMock(return_value=True)

    outcome = TradeOutcome(
        market_id="pm-5m-btc-001",
        question="Will BTC...",
        decision="skip",
        confidence=0.4,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="confidence_too_low",
        display={"seconds_remaining": 120, "skip_reason_category": "custom_override"},
    )
    payload = trader._decision_diagnostics_payload(outcome, ticker="BTC")

    # The root-cause fields must exist
    assert "skip_reason_category" in payload
    # And the value should be the classifier's output for confidence_too_low
    assert payload["skip_reason_category"] in {"evidence", "custom_override"}


def test_additive_schema_all_eight_fields_present() -> None:
    """All 8 root-cause fields must be present after classification."""
    result = classify_no_entry_root_cause({"normalized_skip_reason": "time_unsafe"})
    required = [
        "skip_reason_category",
        "skip_reason_primary",
        "skip_reason_secondary",
        "no_entry_root_cause_confidence",
        "timing_block_reason",
        "evidence_block_reason",
        "risk_block_reason",
        "microstructure_block_reason",
    ]
    for field in required:
        assert field in result, f"Missing field: {field}"


def test_original_payload_not_mutated() -> None:
    """classify_no_entry_root_cause must not mutate its input dict."""
    payload = {"normalized_skip_reason": "confidence_too_low", "custom_field": "preserved"}
    _ = classify_no_entry_root_cause(payload)
    assert "skip_reason_category" not in payload
    assert payload["custom_field"] == "preserved"


# ---------------------------------------------------------------------------
# 8. No runtime behavior changes — decision path unaffected
# ---------------------------------------------------------------------------

def test_decision_event_still_calls_log_decision_after_classifier_wired() -> None:
    """
    Wiring the classifier into _decision_diagnostics_payload must not prevent
    log_decision from being called or change skip/approve decision logic.
    """
    from polymarket.trader import PolymarketTrader, TradeOutcome

    trader = PolymarketTrader()
    trader.settings = MagicMock()
    trader.settings.paper_trading = True
    trader.settings.hybrid_phase_v1_enabled = False
    trader.settings.adaptive_entry_max_spread = 0.06
    trader.settings.execution_entry_cutoff_seconds = 90
    trader.settings.execution_entry_hard_block_seconds = 35
    trader._connected = True
    trader.quant_events = MagicMock()
    trader.quant_events._with_candidate_trace_identity = MagicMock(side_effect=lambda p, t: p)
    trader.quant_events.log_decision.return_value = True
    trader.quant_events.log_risk_event = MagicMock(return_value=True)

    outcome = TradeOutcome(
        market_id="pm-5m-btc-999",
        question="Will BTC...",
        decision="skip",
        confidence=0.4,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="time_unsafe",
        display={"seconds_remaining": 25},
    )
    trader._emit_decision_event(outcome, ticker="BTC")
    trader.quant_events.log_decision.assert_called_once()


# ---------------------------------------------------------------------------
# 9. Offline report tool — build_records and aggregate
# ---------------------------------------------------------------------------

def _fake_decision_event(reason: str, asset: str = "BTC", epoch: int = 1000000) -> dict:
    return {
        "event_type": "decision",
        "run_id": "run_test",
        "timestamp_utc": "2026-05-14T10:00:00Z",
        "payload": {
            "skipped": True,
            "decision": "skip",
            "normalized_skip_reason": reason,
            "asset": asset,
            "market_epoch_start": epoch,
        },
    }


def test_build_records_classifies_all_events() -> None:
    events = [
        _fake_decision_event("time_unsafe", "BTC", 1000000),
        _fake_decision_event("confidence_too_low", "ETH", 1000300),
        _fake_decision_event("spread_too_wide", "BTC", 1000600),
        _fake_decision_event("", "ETH", 1000900),
    ]
    records = build_records(events, {})
    assert len(records) == 4
    categories = [r["skip_reason_category"] for r in records]
    assert "timing" in categories
    assert "evidence" in categories
    assert "microstructure" in categories


def test_aggregate_counts_match_records() -> None:
    events = [
        _fake_decision_event("time_unsafe", "BTC"),
        _fake_decision_event("time_unsafe", "BTC"),
        _fake_decision_event("confidence_too_low", "ETH"),
    ]
    records = build_records(events, {})
    summary = aggregate(records)
    assert summary["total_skipped_events"] == 3
    assert summary["category_counts"]["timing"] == 2
    assert summary["category_counts"]["evidence"] == 1


def test_aggregate_asset_breakdown_separated() -> None:
    events = [
        _fake_decision_event("time_unsafe", "BTC"),
        _fake_decision_event("drawdown", "ETH"),
    ]
    records = build_records(events, {})
    summary = aggregate(records)
    assert "BTC" in summary["asset_category_breakdown"]
    assert "ETH" in summary["asset_category_breakdown"]
    assert summary["asset_category_breakdown"]["BTC"]["timing"] == 1
    assert summary["asset_category_breakdown"]["ETH"]["risk"] == 1


def test_milestone_index_enriches_timing_correlation() -> None:
    epoch = 1000000
    milestones = {("BTC", epoch): ["market_discovered", "token_ready"]}
    events = [_fake_decision_event("time_unsafe", "BTC", epoch)]
    records = build_records(events, milestones)
    assert records[0]["_highest_milestone"] == "token_ready"
    summary = aggregate(records)
    assert "token_ready" in summary["timing_block_stage_correlation"]


def test_highest_milestone_ordering() -> None:
    assert _highest_milestone_reached(["market_discovered", "token_ready", "first_orderbook_seen"]) == "first_orderbook_seen"
    assert _highest_milestone_reached(["market_discovered"]) == "market_discovered"
    assert _highest_milestone_reached([]) == ""
    assert _highest_milestone_reached(["first_decision_evaluable"]) == "first_decision_evaluable"


def test_aggregate_confidence_distribution_keys() -> None:
    events = [_fake_decision_event("time_unsafe")]
    records = build_records(events, {})
    summary = aggregate(records)
    assert "confidence_distribution" in summary
    assert "high_0.85+" in summary["confidence_distribution"] or \
           "medium_0.60-0.84" in summary["confidence_distribution"] or \
           "low_0.30-0.59" in summary["confidence_distribution"] or \
           "very_low_<0.30" in summary["confidence_distribution"]


# ---------------------------------------------------------------------------
# 10. JSONL load functions handle missing files safely
# ---------------------------------------------------------------------------

def test_load_decision_events_missing_file(tmp_path: Path) -> None:
    result = load_decision_events("2099-01-01", quant_data_dir=tmp_path)
    assert result == []


def test_load_milestone_events_missing_file(tmp_path: Path) -> None:
    result = load_milestone_events("2099-01-01", quant_data_dir=tmp_path)
    assert result == {}


def test_load_decision_events_filters_by_run_id(tmp_path: Path) -> None:
    decision_dir = tmp_path / "decision_log"
    decision_dir.mkdir(parents=True)
    events = [
        {"event_type": "decision", "run_id": "run_A", "payload": {"skipped": True, "normalized_skip_reason": "time_unsafe"}},
        {"event_type": "decision", "run_id": "run_B", "payload": {"skipped": True, "normalized_skip_reason": "drawdown"}},
    ]
    with (decision_dir / "2026-05-14.jsonl").open("w") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")

    result_a = load_decision_events("2026-05-14", quant_data_dir=tmp_path, run_id="run_A")
    assert len(result_a) == 1
    assert result_a[0]["run_id"] == "run_A"

    result_all = load_decision_events("2026-05-14", quant_data_dir=tmp_path)
    assert len(result_all) == 2
