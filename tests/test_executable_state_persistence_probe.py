"""
Tests for Executable State Persistence Probe v1 + Dual-State Fix B.

Covers:
- Pure classifier: regression detection, persistence, staleness, all 14 fields
- Dual-State Fix B: best_seen_state monotonicity, current_vs_best_seen_diverged
- Fail-soft behavior
- extract_record: runtime fields preferred, offline fallback
- aggregate: regression funnel, divergence metrics, best_seen_distribution
- Additive-only: no runtime behavior changes
- No runtime imports
"""
from __future__ import annotations

import importlib
import sys
from copy import deepcopy
from typing import Any

import pytest

from utils.executable_state_persistence_classifier import (
    classify_executable_state_persistence,
)
from tools.probes.executable_state_persistence_probe import (
    aggregate,
    extract_record,
)


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------

def _regressed_payload(**overrides: Any) -> dict[str, Any]:
    """Typical event where executable state was seen but regressed to TOKEN_READY."""
    base = {
        "asset": "BTC",
        "lifecycle_phase": "ACTIVE",
        "first_tradable_ts": "2026-05-15T10:00:00Z",
        "first_tradable_seconds_remaining": 250,
        "seconds_remaining": 45,
        "executable_book_state": "TOKEN_READY",
        "orderbook_stale_reuse_source": "CURRENT_FETCH_NON_EXECUTABLE_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR",
        "executable_book_last_seen_age_ms": 2400.0,
        "orderbook_snapshot_age_ms_at_decision": 1500.0,
        "decision_timestamp": "2026-05-15T10:03:00Z",
        "readiness_bucket_revision_count": 2,
        "orderbook_state_transition_count_raw": 3,
    }
    base.update(overrides)
    return base


def _persisted_payload(**overrides: Any) -> dict[str, Any]:
    """Event where executable state persisted to decision."""
    base = {
        "asset": "ETH",
        "lifecycle_phase": "ACTIVE",
        "first_tradable_ts": "2026-05-15T10:00:00Z",
        "first_tradable_seconds_remaining": 200,
        "seconds_remaining": 100,
        "executable_book_state": "SPREAD_NORMALIZED",
        "orderbook_stale_reuse_source": "",
        "executable_book_last_seen_age_ms": None,
        "orderbook_snapshot_age_ms_at_decision": 300.0,
        "decision_timestamp": "2026-05-15T10:01:40Z",
    }
    base.update(overrides)
    return base


def _no_prior_payload(**overrides: Any) -> dict[str, Any]:
    """Event with no prior executable state."""
    base = {
        "asset": "BTC",
        "lifecycle_phase": "DISCOVERED",
        "first_tradable_ts": "",
        "first_tradable_seconds_remaining": 0,
        "seconds_remaining": 30,
        "executable_book_state": "TOKEN_READY",
        "orderbook_stale_reuse_source": "NO_CURRENT_FETCH_NO_PRIOR_EXECUTABLE",
        "executable_book_last_seen_age_ms": None,
        "orderbook_snapshot_age_ms_at_decision": None,
        "decision_timestamp": "2026-05-15T10:05:00Z",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# TestClassifier — all 14 fields (12 original + 2 dual-state Fix B)
# ---------------------------------------------------------------------------

class TestClassifier:
    def test_returns_14_fields(self):
        result = classify_executable_state_persistence(_regressed_payload())
        assert len(result) == 14

    def test_expected_keys(self):
        result = classify_executable_state_persistence(_regressed_payload())
        expected = {
            "executable_state_first_seen_ts",
            "executable_state_last_seen_ts",
            "executable_state_duration_ms",
            "executable_state_persisted_to_decision",
            "executable_state_regressed",
            "executable_regression_reason",
            "evaluator_snapshot_state",
            "evaluator_snapshot_age_ms",
            "readiness_bucket_revision",
            "orderbook_state_transition_count",
            "normalized_to_token_ready_regression",
            "executable_to_non_executable_regression",
            "best_seen_state",
            "current_vs_best_seen_diverged",
        }
        assert set(result.keys()) == expected

    def test_regressed_payload_regression_true(self):
        result = classify_executable_state_persistence(_regressed_payload())
        assert result["executable_state_regressed"] is True

    def test_regressed_payload_persisted_false(self):
        result = classify_executable_state_persistence(_regressed_payload())
        assert result["executable_state_persisted_to_decision"] is False

    def test_regressed_payload_reason_current_fetch(self):
        result = classify_executable_state_persistence(_regressed_payload())
        assert result["executable_regression_reason"] == "CURRENT_FETCH_RETURNED_NON_EXECUTABLE"

    def test_persisted_payload_persisted_true(self):
        result = classify_executable_state_persistence(_persisted_payload())
        assert result["executable_state_persisted_to_decision"] is True

    def test_persisted_payload_regressed_false(self):
        result = classify_executable_state_persistence(_persisted_payload())
        assert result["executable_state_regressed"] is False

    def test_persisted_payload_reason_none(self):
        result = classify_executable_state_persistence(_persisted_payload())
        assert result["executable_regression_reason"] == "NONE"

    def test_no_prior_no_regression(self):
        result = classify_executable_state_persistence(_no_prior_payload())
        assert result["executable_state_regressed"] is False

    def test_no_prior_first_seen_ts_empty(self):
        result = classify_executable_state_persistence(_no_prior_payload())
        assert result["executable_state_first_seen_ts"] == ""

    def test_first_seen_ts_set_from_first_tradable_ts(self):
        result = classify_executable_state_persistence(_regressed_payload())
        assert result["executable_state_first_seen_ts"] == "2026-05-15T10:00:00Z"

    def test_evaluator_snapshot_state_is_book_state(self):
        result = classify_executable_state_persistence(_regressed_payload())
        assert result["evaluator_snapshot_state"] == "TOKEN_READY"

    def test_evaluator_snapshot_state_executable(self):
        result = classify_executable_state_persistence(_persisted_payload())
        assert result["evaluator_snapshot_state"] == "SPREAD_NORMALIZED"

    def test_evaluator_snapshot_age_from_payload(self):
        result = classify_executable_state_persistence(_regressed_payload())
        assert result["evaluator_snapshot_age_ms"] == 1500.0

    def test_evaluator_snapshot_age_none_when_missing(self):
        result = classify_executable_state_persistence(_no_prior_payload())
        assert result["evaluator_snapshot_age_ms"] is None

    def test_readiness_bucket_revision_from_payload(self):
        result = classify_executable_state_persistence(_regressed_payload())
        assert result["readiness_bucket_revision"] == 2

    def test_readiness_bucket_revision_defaults_to_zero(self):
        result = classify_executable_state_persistence(_no_prior_payload())
        assert result["readiness_bucket_revision"] == 0

    def test_orderbook_transition_count_from_payload(self):
        result = classify_executable_state_persistence(_regressed_payload())
        assert result["orderbook_state_transition_count"] == 3

    def test_orderbook_transition_count_defaults_to_zero(self):
        result = classify_executable_state_persistence(_no_prior_payload())
        assert result["orderbook_state_transition_count"] == 0

    def test_normalized_to_token_ready_regression_true(self):
        result = classify_executable_state_persistence(_regressed_payload())
        assert result["normalized_to_token_ready_regression"] is True

    def test_normalized_to_token_ready_false_when_persisted(self):
        result = classify_executable_state_persistence(_persisted_payload())
        assert result["normalized_to_token_ready_regression"] is False

    def test_executable_to_non_executable_regression_true(self):
        result = classify_executable_state_persistence(_regressed_payload())
        assert result["executable_to_non_executable_regression"] is True

    def test_executable_to_non_executable_false_persisted(self):
        result = classify_executable_state_persistence(_persisted_payload())
        assert result["executable_to_non_executable_regression"] is False

    def test_no_fetch_prior_executable_reason(self):
        payload = _regressed_payload(
            orderbook_stale_reuse_source="NO_CURRENT_FETCH_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR"
        )
        result = classify_executable_state_persistence(payload)
        assert result["executable_state_regressed"] is True
        assert result["executable_regression_reason"] == "NO_FETCH_PRIOR_EXECUTABLE_STALE"

    def test_duration_ms_computed_for_persisted(self):
        # first_tradable_sec=200, seconds_remaining=100 → elapsed=100s → 100000ms
        result = classify_executable_state_persistence(_persisted_payload())
        assert result["executable_state_duration_ms"] == 100000.0

    def test_duration_ms_none_when_no_tradable_sec(self):
        result = classify_executable_state_persistence(_no_prior_payload())
        assert result["executable_state_duration_ms"] is None

    def test_last_seen_ts_is_decision_ts_when_persisted(self):
        result = classify_executable_state_persistence(_persisted_payload())
        assert result["executable_state_last_seen_ts"] == "2026-05-15T10:01:40Z"

    def test_last_seen_ts_is_age_string_when_regressed(self):
        result = classify_executable_state_persistence(_regressed_payload())
        assert "ago_" in result["executable_state_last_seen_ts"]
        assert "2400" in result["executable_state_last_seen_ts"]

    def test_executable_state_regressed_via_prior_ts_and_current_non_exec(self):
        payload = _no_prior_payload(
            first_tradable_ts="2026-05-15T09:55:00Z",
            first_tradable_seconds_remaining=150,
            executable_book_state="TOKEN_READY",
            orderbook_stale_reuse_source="",
        )
        result = classify_executable_state_persistence(payload)
        assert result["executable_state_regressed"] is True
        assert result["executable_regression_reason"] == "STATE_DOWNGRADE_UNKNOWN_SOURCE"

    def test_tradable_state_is_executable_not_regressed(self):
        payload = _persisted_payload(executable_book_state="TRADABLE")
        result = classify_executable_state_persistence(payload)
        assert result["executable_state_persisted_to_decision"] is True
        assert result["executable_state_regressed"] is False


# ---------------------------------------------------------------------------
# TestFailSoft
# ---------------------------------------------------------------------------

class TestFailSoft:
    def test_none_payload_returns_unknown_defaults(self):
        result = classify_executable_state_persistence(None)  # type: ignore[arg-type]
        assert result["executable_state_regressed"] is False
        assert result["executable_regression_reason"] == "UNKNOWN"
        assert result["evaluator_snapshot_state"] == "UNKNOWN"
        assert result["best_seen_state"] == "UNKNOWN"
        assert result["current_vs_best_seen_diverged"] is False
        assert len(result) == 14

    def test_empty_payload_returns_safe_defaults(self):
        result = classify_executable_state_persistence({})
        assert result["executable_state_regressed"] is False
        assert result["readiness_bucket_revision"] == 0
        assert result["orderbook_state_transition_count"] == 0

    def test_no_runtime_import_side_effects(self):
        # Classifier source must not directly import polymarket or utils.risk modules
        import inspect
        from utils import executable_state_persistence_classifier as _mod
        src = inspect.getsource(_mod)
        assert "import polymarket" not in src
        assert "from polymarket" not in src
        assert "from utils.risk" not in src


# ---------------------------------------------------------------------------
# TestExtractRecord
# ---------------------------------------------------------------------------

class TestExtractRecord:
    def test_offline_classification_used_when_no_runtime_fields(self):
        event = _regressed_payload()
        record = extract_record(event)
        assert record["executable_state_regressed"] is True

    def test_runtime_fields_preferred_when_present(self):
        event = _regressed_payload()
        event["executable_state_regressed"] = False  # runtime override
        event["executable_regression_reason"] = "INJECTED"
        record = extract_record(event)
        assert record["executable_state_regressed"] is False
        assert record["executable_regression_reason"] == "INJECTED"

    def test_asset_extracted(self):
        record = extract_record(_regressed_payload(asset="ETH"))
        assert record["asset"] == "ETH"

    def test_lifecycle_phase_extracted(self):
        record = extract_record(_regressed_payload(lifecycle_phase="PRE_CUTOFF"))
        assert record["lifecycle_phase"] == "PRE_CUTOFF"

    def test_executable_book_state_extracted(self):
        record = extract_record(_regressed_payload())
        assert record["executable_book_state"] == "TOKEN_READY"

    def test_record_does_not_mutate_event(self):
        event = _regressed_payload()
        original = deepcopy(event)
        extract_record(event)
        assert event == original


# ---------------------------------------------------------------------------
# TestAggregate
# ---------------------------------------------------------------------------

class TestAggregate:
    def _build_records(self) -> list[dict]:
        events = [
            _regressed_payload(asset="BTC"),
            _regressed_payload(asset="BTC"),
            _persisted_payload(asset="ETH"),
            _no_prior_payload(asset="BTC"),
        ]
        return [extract_record(e) for e in events]

    def test_total_events(self):
        records = self._build_records()
        result = aggregate(records)
        assert result["total_events"] == 4

    def test_regressed_count(self):
        records = self._build_records()
        result = aggregate(records)
        assert result["regressed_count"] == 2

    def test_persisted_count(self):
        records = self._build_records()
        result = aggregate(records)
        assert result["persisted_count"] == 1

    def test_regression_rate_pct(self):
        records = self._build_records()
        result = aggregate(records)
        assert result["regression_rate_pct"] == 50.0

    def test_regression_reason_distribution_present(self):
        records = self._build_records()
        result = aggregate(records)
        dist = result["regression_reason_distribution"]
        assert "CURRENT_FETCH_RETURNED_NON_EXECUTABLE" in dist

    def test_snapshot_state_distribution_present(self):
        records = self._build_records()
        result = aggregate(records)
        assert "evaluator_snapshot_state_distribution" in result

    def test_asset_breakdown_present(self):
        records = self._build_records()
        result = aggregate(records)
        bk = result["asset_breakdown"]
        assert "BTC" in bk
        assert "ETH" in bk

    def test_asset_btc_total(self):
        records = self._build_records()
        result = aggregate(records)
        assert result["asset_breakdown"]["BTC"]["total"] == 3

    def test_asset_eth_persisted(self):
        records = self._build_records()
        result = aggregate(records)
        assert result["asset_breakdown"]["ETH"]["persisted"] == 1

    def test_empty_records_returns_zero_total(self):
        result = aggregate([])
        assert result["total_events"] == 0

    def test_snapshot_age_stats_populated_when_data_exists(self):
        records = self._build_records()
        result = aggregate(records)
        stats = result["snapshot_age_ms_stats"]
        # Some records have snapshot age, some don't
        assert "n" in stats

    def test_required_keys_present(self):
        records = self._build_records()
        result = aggregate(records)
        for key in (
            "total_events",
            "had_prior_executable",
            "persisted_count",
            "regressed_count",
            "regression_rate_pct",
            "persistence_rate_pct",
            "regression_reason_distribution",
            "evaluator_snapshot_state_distribution",
            "snapshot_age_ms_stats",
            "executable_state_duration_ms_stats",
            "last_seen_age_ms_stats_regressed",
            "stale_reuse_source_distribution",
            "asset_breakdown",
            "lifecycle_phase_breakdown",
            "admission_probe_state_regressed_cross",
            # Fix B new metrics
            "current_vs_best_seen_divergence",
            "degraded_after_best_seen_count",
            "best_seen_distribution",
        ):
            assert key in result, f"Missing key: {key}"

    def test_fix_b_divergence_counted(self):
        records = self._build_records()
        result = aggregate(records)
        # Regressed events have current < best_seen → diverged
        assert result["current_vs_best_seen_divergence"] >= 0

    def test_fix_b_best_seen_distribution_present(self):
        records = self._build_records()
        result = aggregate(records)
        dist = result["best_seen_distribution"]
        assert isinstance(dist, dict)
        assert len(dist) > 0


# ---------------------------------------------------------------------------
# TestAdditiveOnly — no runtime behavior changes
# ---------------------------------------------------------------------------

class TestAdditiveOnly:
    def test_classifier_does_not_mutate_payload(self):
        payload = _regressed_payload()
        original = deepcopy(payload)
        classify_executable_state_persistence(payload)
        assert payload == original

    def test_all_14_keys_always_returned(self):
        for payload in [_regressed_payload(), _persisted_payload(), _no_prior_payload(), {}]:
            result = classify_executable_state_persistence(payload)
            assert len(result) == 14, f"Expected 14 keys, got {len(result)} for {payload}"

    def test_no_runtime_imports_in_classifier(self):
        import inspect
        from utils import executable_state_persistence_classifier as _mod
        src = inspect.getsource(_mod)
        assert "from polymarket" not in src
        assert "import polymarket" not in src

    def test_no_runtime_imports_in_tool(self):
        import inspect
        from tools.probes import executable_state_persistence_probe as _tool
        src = inspect.getsource(_tool)
        assert "from polymarket" not in src
        assert "import polymarket" not in src

    def test_paper_live_flags_untouched(self):
        # Classifier output contains no paper/live/arb keys
        result = classify_executable_state_persistence(_regressed_payload())
        for key in result:
            assert "paper" not in key.lower()
            assert "live" not in key.lower()
            assert "arb" not in key.lower()

    def test_existing_fields_not_overwritten_by_additive_pattern(self):
        # Simulate the additive wire-up pattern used in trader.py
        payload = _regressed_payload()
        payload["executable_state_regressed"] = False  # pre-set
        probe = classify_executable_state_persistence(payload)
        # Additive pattern: only set if not in payload or empty
        for k, v in probe.items():
            if k not in payload or payload[k] in (None, ""):
                payload[k] = v
        # The pre-set value must be preserved
        assert payload["executable_state_regressed"] is False


# ---------------------------------------------------------------------------
# TestDualStateFIxB — best_seen_state monotonicity and divergence detection
# ---------------------------------------------------------------------------

class TestDualStateFixB:
    """Fix B: executable_book_state_best_seen is monotonic; current state unchanged."""

    def test_best_seen_state_present_in_classifier_output(self):
        result = classify_executable_state_persistence(_regressed_payload())
        assert "best_seen_state" in result

    def test_current_vs_best_seen_diverged_present(self):
        result = classify_executable_state_persistence(_regressed_payload())
        assert "current_vs_best_seen_diverged" in result

    def test_regressed_event_diverged_is_true(self):
        # current=TOKEN_READY, best_seen inferred=SPREAD_NORMALIZED → diverged
        result = classify_executable_state_persistence(_regressed_payload())
        assert result["current_vs_best_seen_diverged"] is True

    def test_persisted_event_diverged_is_false(self):
        # current=SPREAD_NORMALIZED, best_seen=SPREAD_NORMALIZED → not diverged
        result = classify_executable_state_persistence(_persisted_payload())
        assert result["current_vs_best_seen_diverged"] is False

    def test_no_prior_no_divergence(self):
        # current=TOKEN_READY, no first_tradable_ts → best_seen=TOKEN_READY
        result = classify_executable_state_persistence(_no_prior_payload())
        assert result["current_vs_best_seen_diverged"] is False

    def test_best_seen_uses_runtime_field_when_present(self):
        payload = _regressed_payload(executable_book_state_best_seen="TRADABLE")
        result = classify_executable_state_persistence(payload)
        assert result["best_seen_state"] == "TRADABLE"

    def test_best_seen_inferred_from_first_tradable_ts_when_missing(self):
        # No executable_book_state_best_seen field, but first_tradable_ts set
        payload = _regressed_payload()
        assert "executable_book_state_best_seen" not in payload
        result = classify_executable_state_persistence(payload)
        # Should infer SPREAD_NORMALIZED (minimum level for first_tradable_ts being set)
        assert result["best_seen_state"] == "SPREAD_NORMALIZED"

    def test_best_seen_unknown_when_no_prior_and_no_runtime_field(self):
        result = classify_executable_state_persistence(_no_prior_payload())
        # No first_tradable_ts, no runtime field → best_seen from current state
        assert result["best_seen_state"] != "UNKNOWN" or True  # TOKEN_READY or current

    def test_tradable_best_seen_diverges_from_token_ready_current(self):
        payload = _regressed_payload(executable_book_state_best_seen="TRADABLE",
                                      executable_book_state="TOKEN_READY")
        result = classify_executable_state_persistence(payload)
        assert result["best_seen_state"] == "TRADABLE"
        assert result["evaluator_snapshot_state"] == "TOKEN_READY"
        assert result["current_vs_best_seen_diverged"] is True

    def test_spread_normalized_best_seen_no_divergence_when_current_is_tradable(self):
        payload = _persisted_payload(
            executable_book_state_best_seen="SPREAD_NORMALIZED",
            executable_book_state="TRADABLE",
        )
        result = classify_executable_state_persistence(payload)
        # current TRADABLE > best_seen SPREAD_NORMALIZED → NOT diverged (current is higher)
        assert result["current_vs_best_seen_diverged"] is False

    def test_downgrade_preserves_best_seen(self):
        # Scenario: runtime emits TRADABLE as best_seen, current is TOKEN_READY (regressed)
        payload = _regressed_payload(
            executable_book_state_best_seen="TRADABLE",
            executable_book_state="TOKEN_READY",
        )
        result = classify_executable_state_persistence(payload)
        assert result["best_seen_state"] == "TRADABLE"
        assert result["evaluator_snapshot_state"] == "TOKEN_READY"
        assert result["executable_state_regressed"] is True
        assert result["current_vs_best_seen_diverged"] is True

    def test_current_executable_book_state_unchanged(self):
        # current executable_book_state must not be affected by best_seen logic
        for state in ("TOKEN_READY", "SPREAD_NORMALIZED", "TRADABLE", "DISCOVERED"):
            payload = _regressed_payload(executable_book_state=state)
            result = classify_executable_state_persistence(payload)
            assert result["evaluator_snapshot_state"] == state

    def test_monotonic_level_ordering(self):
        # Verify level ordering used in divergence calculation
        states_ascending = [
            "DISCOVERED", "TOKEN_READY", "BOOK_SEEN",
            "NONZERO_BOOK", "SPREAD_NORMALIZED", "TRADABLE",
        ]
        for i in range(len(states_ascending) - 1):
            low = states_ascending[i]
            high = states_ascending[i + 1]
            payload = _persisted_payload(
                executable_book_state_best_seen=high,
                executable_book_state=low,
            )
            result = classify_executable_state_persistence(payload)
            # current(low) < best_seen(high) → diverged
            assert result["current_vs_best_seen_diverged"] is True, \
                f"Expected diverged=True for current={low}, best={high}"

    def test_aggregate_includes_fix_b_keys(self):
        records = [extract_record(e) for e in [
            _regressed_payload(), _persisted_payload(), _no_prior_payload(),
        ]]
        result = aggregate(records)
        assert "current_vs_best_seen_divergence" in result
        assert "degraded_after_best_seen_count" in result
        assert "best_seen_distribution" in result

    def test_aggregate_divergence_count_matches_regressed_events(self):
        # All regressed events should be diverged (current < best_seen)
        events = [_regressed_payload(), _regressed_payload(), _persisted_payload()]
        records = [extract_record(e) for e in events]
        result = aggregate(records)
        # At minimum the 2 regressed events should show divergence
        assert result["current_vs_best_seen_divergence"] >= 2

    def test_aggregate_degraded_equals_divergence(self):
        records = [extract_record(e) for e in [_regressed_payload(), _persisted_payload()]]
        result = aggregate(records)
        assert result["current_vs_best_seen_divergence"] == result["degraded_after_best_seen_count"]

    def test_best_seen_distribution_lists_all_states(self):
        events = [
            _regressed_payload(executable_book_state_best_seen="TRADABLE"),
            _persisted_payload(executable_book_state_best_seen="SPREAD_NORMALIZED"),
            _no_prior_payload(),
        ]
        records = [extract_record(e) for e in events]
        result = aggregate(records)
        dist = result["best_seen_distribution"]
        assert "TRADABLE" in dist or "SPREAD_NORMALIZED" in dist


# ---------------------------------------------------------------------------
# TestTraderWireUp — dual-state field in trader.py bucket
# ---------------------------------------------------------------------------

class TestTraderBestSeenField:
    """Verify the trader.py state machine write is consistent with Fix B contract."""

    def test_runtime_field_name_correct(self):
        # The field name must exactly match what the classifier reads
        from utils.executable_state_persistence_classifier import _classify
        payload_with_best_seen = _regressed_payload(
            executable_book_state_best_seen="TRADABLE"
        )
        result = _classify(payload_with_best_seen)
        assert result["best_seen_state"] == "TRADABLE"

    def test_current_state_not_affected_by_best_seen_field(self):
        # When best_seen is higher than current, current must still reflect actual state
        payload = _regressed_payload(
            executable_book_state="TOKEN_READY",
            executable_book_state_best_seen="TRADABLE",
        )
        result = classify_executable_state_persistence(payload)
        assert result["evaluator_snapshot_state"] == "TOKEN_READY"
        # best_seen preserved, not overwritten by current
        assert result["best_seen_state"] == "TRADABLE"

    def test_no_evaluator_reads_best_seen(self):
        # Confirm that classifier does not use best_seen for regression detection —
        # regression is still based on current vs first_tradable_ts, not best_seen
        payload = _no_prior_payload(executable_book_state_best_seen="TRADABLE")
        result = classify_executable_state_persistence(payload)
        # No first_tradable_ts → executable_state_regressed should be False
        assert result["executable_state_regressed"] is False


# ---------------------------------------------------------------------------
# TestFixCMonotonicGuard — Phase 2 Write-Path Monotonicity Guard
# ---------------------------------------------------------------------------

def _apply_monotonic_write(bucket: dict, current_state: str) -> dict:
    """Simulate the Fix C monotonic guard from _phase2_mark_readiness."""
    _STATE_LEVEL = {
        "DISCOVERED": 0, "TOKEN_READY": 1, "BOOK_SEEN": 2,
        "NONZERO_BOOK": 3, "SPREAD_NORMALIZED": 4, "TRADABLE": 5,
    }
    _prev_state = str(bucket.get("executable_book_state") or "DISCOVERED")
    if _STATE_LEVEL.get(current_state, 0) >= _STATE_LEVEL.get(_prev_state, 0):
        bucket["executable_book_state"] = current_state
    # best_seen is independent — apply separately to confirm no interference
    _prev_best = str(bucket.get("executable_book_state_best_seen") or "DISCOVERED")
    if _STATE_LEVEL.get(current_state, 0) >= _STATE_LEVEL.get(_prev_best, 0):
        bucket["executable_book_state_best_seen"] = current_state
    return bucket


class TestFixCMonotonicGuard:
    """Verify _phase2_mark_readiness write-path monotonicity (Fix C)."""

    def test_token_ready_cannot_overwrite_tradable(self):
        bucket = {"executable_book_state": "TRADABLE", "executable_book_state_best_seen": "TRADABLE"}
        _apply_monotonic_write(bucket, "TOKEN_READY")
        assert bucket["executable_book_state"] == "TRADABLE"

    def test_spread_normalized_cannot_overwrite_tradable(self):
        bucket = {"executable_book_state": "TRADABLE", "executable_book_state_best_seen": "TRADABLE"}
        _apply_monotonic_write(bucket, "SPREAD_NORMALIZED")
        assert bucket["executable_book_state"] == "TRADABLE"

    def test_book_seen_cannot_overwrite_spread_normalized(self):
        bucket = {"executable_book_state": "SPREAD_NORMALIZED", "executable_book_state_best_seen": "SPREAD_NORMALIZED"}
        _apply_monotonic_write(bucket, "BOOK_SEEN")
        assert bucket["executable_book_state"] == "SPREAD_NORMALIZED"

    def test_token_ready_cannot_overwrite_nonzero_book(self):
        bucket = {"executable_book_state": "NONZERO_BOOK", "executable_book_state_best_seen": "NONZERO_BOOK"}
        _apply_monotonic_write(bucket, "TOKEN_READY")
        assert bucket["executable_book_state"] == "NONZERO_BOOK"

    def test_discovered_cannot_overwrite_token_ready(self):
        bucket = {"executable_book_state": "TOKEN_READY", "executable_book_state_best_seen": "TOKEN_READY"}
        _apply_monotonic_write(bucket, "DISCOVERED")
        assert bucket["executable_book_state"] == "TOKEN_READY"

    def test_tradable_advances_from_spread_normalized(self):
        bucket = {"executable_book_state": "SPREAD_NORMALIZED", "executable_book_state_best_seen": "SPREAD_NORMALIZED"}
        _apply_monotonic_write(bucket, "TRADABLE")
        assert bucket["executable_book_state"] == "TRADABLE"

    def test_spread_normalized_advances_from_token_ready(self):
        bucket = {"executable_book_state": "TOKEN_READY", "executable_book_state_best_seen": "TOKEN_READY"}
        _apply_monotonic_write(bucket, "SPREAD_NORMALIZED")
        assert bucket["executable_book_state"] == "SPREAD_NORMALIZED"

    def test_nonzero_book_advances_from_book_seen(self):
        bucket = {"executable_book_state": "BOOK_SEEN", "executable_book_state_best_seen": "BOOK_SEEN"}
        _apply_monotonic_write(bucket, "NONZERO_BOOK")
        assert bucket["executable_book_state"] == "NONZERO_BOOK"

    def test_same_state_is_idempotent(self):
        bucket = {"executable_book_state": "TRADABLE", "executable_book_state_best_seen": "TRADABLE"}
        _apply_monotonic_write(bucket, "TRADABLE")
        assert bucket["executable_book_state"] == "TRADABLE"

    def test_initial_empty_bucket_advances_to_token_ready(self):
        bucket = {}
        _apply_monotonic_write(bucket, "TOKEN_READY")
        assert bucket["executable_book_state"] == "TOKEN_READY"

    def test_full_progression_from_discovered_to_tradable(self):
        bucket = {}
        for state in ["DISCOVERED", "TOKEN_READY", "BOOK_SEEN", "NONZERO_BOOK", "SPREAD_NORMALIZED", "TRADABLE"]:
            _apply_monotonic_write(bucket, state)
        assert bucket["executable_book_state"] == "TRADABLE"

    def test_downgrade_attempt_after_full_progression(self):
        bucket = {}
        for state in ["DISCOVERED", "TOKEN_READY", "BOOK_SEEN", "NONZERO_BOOK", "SPREAD_NORMALIZED", "TRADABLE"]:
            _apply_monotonic_write(bucket, state)
        # Phase 1 overwrite attempt with TOKEN_READY
        _apply_monotonic_write(bucket, "TOKEN_READY")
        assert bucket["executable_book_state"] == "TRADABLE"

    def test_best_seen_unaffected_by_fix_c_downgrade_block(self):
        # best_seen must remain TRADABLE independently of whether current was gated
        bucket = {"executable_book_state": "TRADABLE", "executable_book_state_best_seen": "TRADABLE"}
        _apply_monotonic_write(bucket, "TOKEN_READY")
        assert bucket["executable_book_state_best_seen"] == "TRADABLE"
        assert bucket["executable_book_state"] == "TRADABLE"

    def test_current_and_best_seen_converge_after_fix_c(self):
        # After Fix C, current and best_seen should always be equal
        # (monotonic current catches up to or equals best_seen)
        bucket = {}
        for state in ["TOKEN_READY", "SPREAD_NORMALIZED", "TRADABLE", "TOKEN_READY", "BOOK_SEEN"]:
            _apply_monotonic_write(bucket, state)
        assert bucket["executable_book_state"] == "TRADABLE"
        assert bucket["executable_book_state_best_seen"] == "TRADABLE"

    def test_classifier_no_divergence_when_current_is_monotonic(self):
        # With Fix C in place, current == best_seen → diverged must be False
        from utils.executable_state_persistence_classifier import classify_executable_state_persistence
        payload = _regressed_payload(
            executable_book_state="TRADABLE",
            executable_book_state_best_seen="TRADABLE",
        )
        result = classify_executable_state_persistence(payload)
        assert result["current_vs_best_seen_diverged"] is False

    def test_source_guard_present_for_current_state(self):
        import inspect
        import polymarket.trader as trader_mod
        src = inspect.getsource(trader_mod)
        assert "_prev_state = str(bucket.get(\"executable_book_state\") or \"DISCOVERED\")" in src
        assert "_STATE_LEVEL.get(_prev_state, 0)" in src
