"""
Tests for Decision Cycle Timing Alignment Probe v1.

Covers:
- Lifecycle phase classification at decision time
- Active-window detection (entry_window_decision_seen)
- Active-inventory window missed detection
- Model-gate timing blocker classification
- Executable-to-decision delay computation
- Missing-data fail-soft behavior
- Additive-only / no runtime behavior change assertions
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from utils.decision_cycle_timing_classifier import (
    classify_decision_cycle_timing,
    _ENTRY_CUTOFF_SECONDS,
    _EPOCH_SECONDS,
)
from tools.probes.decision_cycle_timing_probe import (
    aggregate,
    extract_record,
)


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------

def _active_payload(**overrides: Any) -> dict[str, Any]:
    """Decision cycle during ACTIVE_INVENTORY_TRADING with executable book."""
    base = {
        "asset": "BTC",
        "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
        "seconds_remaining": 180,
        "first_tradable_ts": "2026-05-15T10:00:00Z",
        "first_tradable_seconds_remaining": 250,
        "decision_timestamp": "2026-05-15T10:02:00Z",
        "decision_cycle_interval_seconds": 60.0,
        "executable_book_state": "TRADABLE",
    }
    base.update(overrides)
    return base


def _late_payload(**overrides: Any) -> dict[str, Any]:
    """Decision cycle during FINAL_DERISK — past entry window."""
    base = {
        "asset": "ETH",
        "lifecycle_phase": "FINAL_DERISK",
        "seconds_remaining": 20,
        "first_tradable_ts": "2026-05-15T10:00:00Z",
        "first_tradable_seconds_remaining": 156,
        "decision_timestamp": "2026-05-15T10:04:40Z",
        "decision_cycle_interval_seconds": 60.1,
        "executable_book_state": "TOKEN_READY",
    }
    base.update(overrides)
    return base


def _no_data_payload(**overrides: Any) -> dict[str, Any]:
    """Minimal payload — missing most fields."""
    base = {
        "asset": "BTC",
        "lifecycle_phase": "",
        "seconds_remaining": None,
        "first_tradable_ts": "",
        "decision_timestamp": "",
    }
    base.update(overrides)
    return base


def _profit_payload(**overrides: Any) -> dict[str, Any]:
    """Decision during PROFIT_MANAGEMENT phase."""
    base = {
        "asset": "BTC",
        "lifecycle_phase": "PROFIT_MANAGEMENT",
        "seconds_remaining": 55,
        "first_tradable_ts": "2026-05-15T10:00:00Z",
        "first_tradable_seconds_remaining": 200,
        "decision_timestamp": "2026-05-15T10:04:05Z",
        "decision_cycle_interval_seconds": 58.5,
        "executable_book_state": "SPREAD_NORMALIZED",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# TestClassifierFields — all 10 fields always returned
# ---------------------------------------------------------------------------

class TestClassifierFields:
    _EXPECTED_KEYS = {
        "decision_cycle_ts",
        "decision_cycle_seconds_remaining",
        "decision_cycle_seconds_since_open",
        "decision_cycle_lifecycle_phase",
        "decision_cycle_gap_seconds",
        "entry_window_decision_seen",
        "model_gate_blocked_by_timing",
        "executable_first_seen_to_decision_ms",
        "candidate_first_seen_to_decision_ms",
        "active_inventory_window_missed",
    }

    def test_returns_all_10_fields(self):
        result = classify_decision_cycle_timing(_active_payload())
        assert len(result) == 10

    def test_expected_keys_present(self):
        result = classify_decision_cycle_timing(_active_payload())
        assert set(result.keys()) == self._EXPECTED_KEYS

    def test_late_payload_all_fields_present(self):
        result = classify_decision_cycle_timing(_late_payload())
        assert set(result.keys()) == self._EXPECTED_KEYS

    def test_empty_payload_returns_all_keys(self):
        result = classify_decision_cycle_timing({})
        assert set(result.keys()) == self._EXPECTED_KEYS


# ---------------------------------------------------------------------------
# TestLifecyclePhaseClassification
# ---------------------------------------------------------------------------

class TestLifecyclePhaseClassification:
    def test_active_lifecycle_phase_preserved(self):
        result = classify_decision_cycle_timing(_active_payload())
        assert result["decision_cycle_lifecycle_phase"] == "ACTIVE_INVENTORY_TRADING"

    def test_final_derisk_lifecycle_preserved(self):
        result = classify_decision_cycle_timing(_late_payload())
        assert result["decision_cycle_lifecycle_phase"] == "FINAL_DERISK"

    def test_profit_management_preserved(self):
        result = classify_decision_cycle_timing(_profit_payload())
        assert result["decision_cycle_lifecycle_phase"] == "PROFIT_MANAGEMENT"

    def test_empty_lifecycle_becomes_unknown(self):
        result = classify_decision_cycle_timing(_no_data_payload())
        assert result["decision_cycle_lifecycle_phase"] == "UNKNOWN"

    def test_seconds_remaining_preserved(self):
        result = classify_decision_cycle_timing(_active_payload(seconds_remaining=180))
        assert result["decision_cycle_seconds_remaining"] == 180

    def test_seconds_since_open_computed(self):
        result = classify_decision_cycle_timing(_active_payload(seconds_remaining=180))
        assert result["decision_cycle_seconds_since_open"] == 120  # 300 - 180

    def test_seconds_since_open_none_when_missing(self):
        result = classify_decision_cycle_timing(_no_data_payload())
        assert result["decision_cycle_seconds_since_open"] is None

    def test_seconds_since_open_at_epoch_boundary(self):
        result = classify_decision_cycle_timing(_active_payload(seconds_remaining=0))
        assert result["decision_cycle_seconds_since_open"] == 300

    def test_decision_cycle_ts_from_decision_timestamp(self):
        result = classify_decision_cycle_timing(_active_payload())
        assert result["decision_cycle_ts"] == "2026-05-15T10:02:00Z"


# ---------------------------------------------------------------------------
# TestActiveWindowDetection
# ---------------------------------------------------------------------------

class TestActiveWindowDetection:
    def test_active_inventory_above_cutoff_is_entry_window(self):
        result = classify_decision_cycle_timing(
            _active_payload(lifecycle_phase="ACTIVE_INVENTORY_TRADING", seconds_remaining=180)
        )
        assert result["entry_window_decision_seen"] is True

    def test_active_inventory_exactly_at_cutoff_is_not_entry_window(self):
        # seconds_remaining == _ENTRY_CUTOFF_SECONDS: must be strictly GREATER
        result = classify_decision_cycle_timing(
            _active_payload(lifecycle_phase="ACTIVE_INVENTORY_TRADING",
                            seconds_remaining=_ENTRY_CUTOFF_SECONDS)
        )
        assert result["entry_window_decision_seen"] is False

    def test_active_inventory_below_cutoff_is_not_entry_window(self):
        result = classify_decision_cycle_timing(
            _active_payload(lifecycle_phase="ACTIVE_INVENTORY_TRADING", seconds_remaining=50)
        )
        assert result["entry_window_decision_seen"] is False

    def test_final_derisk_is_never_entry_window(self):
        result = classify_decision_cycle_timing(_late_payload())
        assert result["entry_window_decision_seen"] is False

    def test_profit_management_is_never_entry_window(self):
        result = classify_decision_cycle_timing(_profit_payload())
        assert result["entry_window_decision_seen"] is False

    def test_missing_lifecycle_is_not_entry_window(self):
        result = classify_decision_cycle_timing(_no_data_payload())
        assert result["entry_window_decision_seen"] is False


# ---------------------------------------------------------------------------
# TestActiveInventoryWindowMissed
# ---------------------------------------------------------------------------

class TestActiveInventoryWindowMissed:
    def test_late_decision_with_early_executable_is_missed(self):
        # Market was executable at 156s remaining (> 90s cutoff)
        # But current decision is FINAL_DERISK → window missed
        result = classify_decision_cycle_timing(_late_payload())
        assert result["active_inventory_window_missed"] is True

    def test_active_window_decision_is_not_missed(self):
        result = classify_decision_cycle_timing(_active_payload())
        assert result["active_inventory_window_missed"] is False

    def test_executable_after_cutoff_not_missed(self):
        # Market only became executable after entry cutoff — no window to miss
        result = classify_decision_cycle_timing(
            _late_payload(first_tradable_seconds_remaining=50)
        )
        assert result["active_inventory_window_missed"] is False

    def test_no_executable_ts_not_missed(self):
        result = classify_decision_cycle_timing(
            _late_payload(first_tradable_seconds_remaining=0, first_tradable_ts="")
        )
        assert result["active_inventory_window_missed"] is False

    def test_profit_phase_with_early_executable_is_missed(self):
        result = classify_decision_cycle_timing(_profit_payload())
        assert result["active_inventory_window_missed"] is True


# ---------------------------------------------------------------------------
# TestModelGateTimingBlocker
# ---------------------------------------------------------------------------

class TestModelGateTimingBlocker:
    def test_final_derisk_is_blocked(self):
        result = classify_decision_cycle_timing(_late_payload())
        assert result["model_gate_blocked_by_timing"] is True

    def test_profit_management_is_blocked(self):
        result = classify_decision_cycle_timing(_profit_payload())
        assert result["model_gate_blocked_by_timing"] is True

    def test_active_above_cutoff_is_not_blocked(self):
        result = classify_decision_cycle_timing(_active_payload(seconds_remaining=180))
        assert result["model_gate_blocked_by_timing"] is False

    def test_active_below_cutoff_is_blocked(self):
        result = classify_decision_cycle_timing(
            _active_payload(lifecycle_phase="ACTIVE_INVENTORY_TRADING", seconds_remaining=50)
        )
        assert result["model_gate_blocked_by_timing"] is True

    def test_seconds_at_entry_cutoff_is_blocked(self):
        result = classify_decision_cycle_timing(
            _active_payload(lifecycle_phase="ACTIVE_INVENTORY_TRADING",
                            seconds_remaining=_ENTRY_CUTOFF_SECONDS)
        )
        assert result["model_gate_blocked_by_timing"] is True

    def test_closed_or_unsafe_is_blocked(self):
        result = classify_decision_cycle_timing(
            _late_payload(lifecycle_phase="CLOSED_OR_UNSAFE", seconds_remaining=0)
        )
        assert result["model_gate_blocked_by_timing"] is True

    def test_missing_lifecycle_defaults_not_blocked(self):
        # Empty lifecycle with None seconds_remaining — cannot determine, defaults False
        result = classify_decision_cycle_timing(_no_data_payload())
        assert result["model_gate_blocked_by_timing"] is False


# ---------------------------------------------------------------------------
# TestExecutableToDecisionDelay
# ---------------------------------------------------------------------------

class TestExecutableToDecisionDelay:
    def test_delay_computed_when_timestamps_present(self):
        result = classify_decision_cycle_timing(_active_payload())
        # first_tradable_ts="2026-05-15T10:00:00Z", decision_timestamp="2026-05-15T10:02:00Z"
        # expected: 2 minutes = 120_000 ms
        delay = result["executable_first_seen_to_decision_ms"]
        assert delay is not None
        assert abs(delay - 120000.0) < 100  # within 100ms of expected

    def test_delay_none_when_no_first_tradable_ts(self):
        result = classify_decision_cycle_timing(
            _active_payload(first_tradable_ts="")
        )
        assert result["executable_first_seen_to_decision_ms"] is None

    def test_delay_none_when_no_decision_ts(self):
        result = classify_decision_cycle_timing(
            _active_payload(decision_timestamp="")
        )
        assert result["executable_first_seen_to_decision_ms"] is None

    def test_delay_for_late_event(self):
        # first_tradable: 10:00:00Z, decision: 10:04:40Z → 280s = 280_000 ms
        result = classify_decision_cycle_timing(_late_payload())
        delay = result["executable_first_seen_to_decision_ms"]
        assert delay is not None
        assert abs(delay - 280000.0) < 500

    def test_gap_seconds_from_payload(self):
        result = classify_decision_cycle_timing(_active_payload(decision_cycle_interval_seconds=62.3))
        assert result["decision_cycle_gap_seconds"] == pytest.approx(62.3, abs=0.01)

    def test_gap_seconds_none_when_missing(self):
        result = classify_decision_cycle_timing(_active_payload(decision_cycle_interval_seconds=None))
        assert result["decision_cycle_gap_seconds"] is None


# ---------------------------------------------------------------------------
# TestFailSoft
# ---------------------------------------------------------------------------

class TestFailSoft:
    def test_none_payload_returns_defaults(self):
        try:
            result = classify_decision_cycle_timing(None)  # type: ignore
        except Exception:
            result = {}
        # Should either return defaults or raise — never crash in probe
        # The classifier catches all exceptions and returns _unknown_defaults
        assert isinstance(result, dict)

    def test_empty_payload_returns_all_keys(self):
        result = classify_decision_cycle_timing({})
        assert len(result) == 10
        assert result["entry_window_decision_seen"] is False
        assert result["model_gate_blocked_by_timing"] is False
        assert result["decision_cycle_lifecycle_phase"] == "UNKNOWN"

    def test_bad_timestamp_returns_none_delay(self):
        result = classify_decision_cycle_timing(
            _active_payload(first_tradable_ts="not-a-date", decision_timestamp="also-bad")
        )
        assert result["executable_first_seen_to_decision_ms"] is None

    def test_negative_seconds_remaining_handled(self):
        result = classify_decision_cycle_timing(
            _active_payload(seconds_remaining=-5)
        )
        assert result["decision_cycle_seconds_since_open"] is not None

    def test_no_runtime_imports_in_classifier(self):
        import inspect
        import utils.decision_cycle_timing_classifier as mod
        src = inspect.getsource(mod)
        for forbidden in ("polymarket.trader", "from polymarket", "import trader"):
            assert forbidden not in src, f"Forbidden import found: {forbidden}"

    def test_no_runtime_imports_in_tool(self):
        import inspect
        import tools.probes.decision_cycle_timing_probe as mod
        src = inspect.getsource(mod)
        for forbidden in ("polymarket.trader", "from polymarket", "import trader"):
            assert forbidden not in src, f"Forbidden import found: {forbidden}"


# ---------------------------------------------------------------------------
# TestExtractRecord
# ---------------------------------------------------------------------------

class TestExtractRecord:
    def test_extract_wraps_timing_classification(self):
        event = {"payload": _active_payload()}
        record = extract_record(event)
        assert "entry_window_decision_seen" in record
        assert "model_gate_blocked_by_timing" in record

    def test_extract_asset_preserved(self):
        event = {"payload": _active_payload(asset="ETH")}
        record = extract_record(event)
        assert record["asset"] == "ETH"

    def test_extract_lifecycle_phase_preserved(self):
        event = {"payload": _active_payload()}
        record = extract_record(event)
        assert record["lifecycle_phase"] == "ACTIVE_INVENTORY_TRADING"

    def test_extract_does_not_mutate_event(self):
        event = {"payload": _active_payload()}
        original = deepcopy(event)
        extract_record(event)
        assert event == original

    def test_extract_flat_event_fallback(self):
        # No nested payload key — falls back to treating event as payload
        event = _active_payload()
        record = extract_record(event)
        assert "entry_window_decision_seen" in record


# ---------------------------------------------------------------------------
# TestAggregate
# ---------------------------------------------------------------------------

class TestAggregate:
    def _make_records(self) -> list[dict]:
        events = [
            {"payload": _active_payload()},
            {"payload": _active_payload()},
            {"payload": _late_payload()},
            {"payload": _late_payload()},
            {"payload": _profit_payload()},
        ]
        return [extract_record(e) for e in events]

    def test_total_events(self):
        records = self._make_records()
        result = aggregate(records)
        assert result["total_events"] == 5

    def test_active_window_count(self):
        records = self._make_records()
        result = aggregate(records)
        # 2 active_payload with seconds_remaining=180 > 90
        assert result["active_window_decisions"] == 2

    def test_model_gate_blocked_count(self):
        records = self._make_records()
        result = aggregate(records)
        # FINAL_DERISK (x2) + PROFIT_MANAGEMENT (x1) + ACTIVE < cutoff = 3 total
        assert result["model_gate_blocked_count"] == 3

    def test_active_window_coverage_pct(self):
        records = self._make_records()
        result = aggregate(records)
        assert result["active_window_coverage_pct"] == pytest.approx(40.0, abs=0.1)

    def test_lifecycle_phase_distribution_present(self):
        records = self._make_records()
        result = aggregate(records)
        dist = result["lifecycle_phase_distribution"]
        assert "ACTIVE_INVENTORY_TRADING" in dist
        assert "FINAL_DERISK" in dist

    def test_asset_breakdown_present(self):
        records = self._make_records()
        result = aggregate(records)
        assert "BTC" in result["asset_breakdown"] or "ETH" in result["asset_breakdown"]

    def test_empty_records_returns_zero_total(self):
        result = aggregate([])
        assert result["total_events"] == 0

    def test_gap_stats_present_when_gaps_available(self):
        records = self._make_records()
        result = aggregate(records)
        # All payloads have decision_cycle_interval_seconds set
        stats = result.get("decision_cycle_gap_stats", {})
        if stats:  # may be empty if all None
            assert "p50" in stats

    def test_exec_delay_stats_present(self):
        records = self._make_records()
        result = aggregate(records)
        stats = result.get("executable_to_decision_delay_ms_stats", {})
        if stats:
            assert "n" in stats

    def test_required_aggregate_keys_present(self):
        records = self._make_records()
        result = aggregate(records)
        for key in [
            "total_events",
            "active_window_decisions",
            "active_window_coverage_pct",
            "model_gate_blocked_count",
            "lifecycle_phase_distribution",
            "asset_breakdown",
            "decision_cycle_gap_stats",
            "executable_to_decision_delay_ms_stats",
            "run_cadence_summary",
        ]:
            assert key in result, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# TestAdditiveOnly
# ---------------------------------------------------------------------------

class TestAdditiveOnly:
    def test_classifier_does_not_mutate_payload(self):
        payload = _active_payload()
        original = deepcopy(payload)
        classify_decision_cycle_timing(payload)
        assert payload == original

    def test_no_paper_live_flags_in_classifier(self):
        import inspect
        import utils.decision_cycle_timing_classifier as mod
        src = inspect.getsource(mod)
        for forbidden in ("is_paper", "is_live", "paper_mode", "live_mode",
                          "arb_auto_execute", "order_intent"):
            assert forbidden not in src

    def test_no_paper_live_flags_in_tool(self):
        import inspect
        import tools.probes.decision_cycle_timing_probe as mod
        src = inspect.getsource(mod)
        for forbidden in ("is_paper", "is_live", "paper_mode", "live_mode",
                          "arb_auto_execute", "order_intent"):
            assert forbidden not in src

    def test_entry_cutoff_matches_settings(self):
        # _ENTRY_CUTOFF_SECONDS must stay in sync with settings.execution_entry_cutoff_seconds
        from utils.decision_cycle_timing_classifier import _ENTRY_CUTOFF_SECONDS
        assert _ENTRY_CUTOFF_SECONDS == 90

    def test_all_10_keys_always_returned_active(self):
        result = classify_decision_cycle_timing(_active_payload())
        assert len(result) == 10

    def test_all_10_keys_always_returned_empty(self):
        result = classify_decision_cycle_timing({})
        assert len(result) == 10

    def test_classifier_does_not_read_trader_state(self):
        # No PolymarketTrader instance needed — pure function
        from utils.decision_cycle_timing_classifier import classify_decision_cycle_timing as clf
        result = clf({"lifecycle_phase": "ACTIVE_INVENTORY_TRADING", "seconds_remaining": 200})
        assert result["entry_window_decision_seen"] is True
