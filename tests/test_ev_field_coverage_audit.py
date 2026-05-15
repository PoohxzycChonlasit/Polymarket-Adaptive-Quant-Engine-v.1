"""
Tests for tools/ev_field_coverage_audit.py — EV Field Coverage Audit v1.

Coverage:
- Field presence detection (canonical + aliases)
- Null/missing value handling
- Missing-reason extraction
- aggregate() structure and coverage metrics
- Asset, lifecycle-phase, skip-reason-category, dominant-latency-stage
  correlation tables
- BTC vs ETH comparison
- Missing/empty input fail-soft
- Additive-only: no runtime imports, no mutation
- load_decision_events filtering (run_id, asset)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from tools.ev_field_coverage_audit import (
    AUDIT_FIELDS,
    CANONICAL_NAMES,
    aggregate,
    extract_record,
    load_decision_events,
    render_console,
    _field_present,
    _field_value,
    _null_reason,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event(payload: dict, *, run_id: str = "r1", asset: str = "BTC") -> dict:
    payload["asset"] = asset  # always override so asset kwarg controls the field
    return {"payload": payload, "run_id": run_id}


def _full_payload(**overrides) -> dict:
    """Payload with all 14 canonical fields present via their primary aliases."""
    base = {
        "asset": "BTC",
        "lifecycle_phase": "OPENING_SCAN",
        "skip_reason_category": "timing",
        "dominant_latency_stage": "CUTOFF",
        "skipped": True,
        # probability_yes
        "true_probability": 0.62,
        # probability_confidence
        "true_probability_available": True,
        # fair_value
        "fair_value": 0.61,
        # edge_bps
        "edge": 0.03,
        # spread_bps
        "spread": 0.04,
        # bid
        "yes_bid": 0.59,
        # ask
        "yes_ask": 0.63,
        # mid_price
        "yes_mid": 0.61,
        # book_imbalance
        "orderbook_imbalance": 0.1,
        # top_depth_yes
        "yes_bid_size": 500.0,
        # top_depth_no
        "no_bid_size": 300.0,
        # ev_per_dollar
        "ev_per_dollar": 0.02,
        # planned_size
        "planned_size": 25.0,
        # data_quality_score
        "data_quality_score": 0.95,
    }
    base.update(overrides)
    return base


def _empty_payload(**extras) -> dict:
    p: dict = {"asset": "BTC", "lifecycle_phase": "UNKNOWN"}
    p.update(extras)
    return p


# ---------------------------------------------------------------------------
# _field_present
# ---------------------------------------------------------------------------

class TestFieldPresent:
    def test_primary_alias_detected(self):
        p = {"true_probability": 0.55}
        assert _field_present(p, "probability_yes") is True

    def test_secondary_alias_detected(self):
        p = {"model_probability_yes": 0.55}
        assert _field_present(p, "probability_yes") is True

    def test_none_value_not_present(self):
        p = {"true_probability": None}
        assert _field_present(p, "probability_yes") is False

    def test_empty_string_not_present(self):
        p = {"true_probability": ""}
        assert _field_present(p, "probability_yes") is False

    def test_false_value_not_present(self):
        # False boolean should not count as coverage
        p = {"true_probability_available": False}
        assert _field_present(p, "probability_confidence") is False

    def test_zero_float_is_present(self):
        # 0.0 is a valid numeric value
        p = {"spread": 0.0}
        assert _field_present(p, "spread_bps") is True

    def test_absent_key_not_present(self):
        p = {}
        assert _field_present(p, "fair_value") is False

    def test_fair_value_alias_chain(self):
        # fair_value_yes is a valid alias
        p = {"fair_value_yes": 0.58}
        assert _field_present(p, "fair_value") is True

    def test_all_canonical_names_defined(self):
        assert len(CANONICAL_NAMES) == 14

    def test_all_audit_fields_have_aliases(self):
        for name, aliases, _ in AUDIT_FIELDS:
            assert len(aliases) >= 1, f"{name} must have at least one alias"


# ---------------------------------------------------------------------------
# _field_value and _null_reason
# ---------------------------------------------------------------------------

class TestFieldValueAndNullReason:
    def test_field_value_returns_first_match(self):
        p = {"true_probability": 0.7, "model_probability_yes": 0.6}
        v = _field_value(p, "probability_yes")
        assert v == 0.7

    def test_field_value_returns_none_when_absent(self):
        assert _field_value({}, "probability_yes") is None

    def test_null_reason_extracted(self):
        p = {"true_probability_null_reason": "model_not_attempted"}
        nr = _null_reason(p, "probability_yes")
        assert nr == "model_not_attempted"

    def test_null_reason_empty_when_no_field(self):
        assert _null_reason({}, "probability_yes") == ""

    def test_null_reason_empty_for_field_without_reason_field(self):
        # spread_bps has no null_reason field
        p = {"spread_null_reason": "something"}
        assert _null_reason(p, "spread_bps") == ""


# ---------------------------------------------------------------------------
# extract_record
# ---------------------------------------------------------------------------

class TestExtractRecord:
    def test_full_payload_all_covered(self):
        event = _event(_full_payload())
        record = extract_record(event)
        assert all(record["coverage"][c] for c in CANONICAL_NAMES)

    def test_empty_payload_nothing_covered(self):
        event = _event(_empty_payload())
        record = extract_record(event)
        assert not any(record["coverage"][c] for c in CANONICAL_NAMES)

    def test_asset_extracted(self):
        event = _event(_full_payload(), asset="ETH")
        record = extract_record(event)
        assert record["asset"] == "ETH"

    def test_lifecycle_phase_extracted(self):
        event = _event(_full_payload(lifecycle_phase="ACTIVE_INVENTORY_TRADING"))
        record = extract_record(event)
        assert record["lifecycle_phase"] == "ACTIVE_INVENTORY_TRADING"

    def test_skip_reason_category_extracted(self):
        event = _event(_full_payload(skip_reason_category="evidence"))
        record = extract_record(event)
        assert record["skip_reason_category"] == "evidence"

    def test_dominant_latency_stage_extracted(self):
        event = _event(_full_payload(dominant_latency_stage="DISCOVERY"))
        record = extract_record(event)
        assert record["dominant_latency_stage"] == "DISCOVERY"

    def test_null_reasons_captured(self):
        p = _empty_payload(
            true_probability_null_reason="model_not_attempted",
            fair_value_null_reason="upstream_missing",
        )
        event = _event(p)
        record = extract_record(event)
        assert record["null_reasons"].get("probability_yes") == "model_not_attempted"
        assert record["null_reasons"].get("fair_value") == "upstream_missing"

    def test_does_not_mutate_event(self):
        import copy
        event = _event(_full_payload())
        original = copy.deepcopy(event)
        extract_record(event)
        assert event == original

    def test_partial_coverage(self):
        p = {"true_probability": 0.5, "fair_value": 0.5}
        event = _event(p)
        record = extract_record(event)
        assert record["coverage"]["probability_yes"] is True
        assert record["coverage"]["fair_value"] is True
        assert record["coverage"]["spread_bps"] is False

    def test_alias_probability_confidence_true_value(self):
        # true_probability_available = True should count
        p = {"true_probability_available": True}
        event = _event(p)
        record = extract_record(event)
        assert record["coverage"]["probability_confidence"] is True


# ---------------------------------------------------------------------------
# aggregate
# ---------------------------------------------------------------------------

class TestAggregate:
    def _records(self, n_full=2, n_empty=0, asset="BTC", phase="OPENING_SCAN",
                 cat="timing", stage="CUTOFF") -> list[dict]:
        recs = []
        for i in range(n_full):
            e = _event(_full_payload(
                lifecycle_phase=phase,
                skip_reason_category=cat,
                dominant_latency_stage=stage,
            ), asset=asset)
            recs.append(extract_record(e))
        for i in range(n_empty):
            e = _event(_empty_payload(
                lifecycle_phase=phase,
                skip_reason_category=cat,
                dominant_latency_stage=stage,
            ), asset=asset)
            recs.append(extract_record(e))
        return recs

    def test_empty_returns_no_data(self):
        result = aggregate([])
        assert result["total_events"] == 0

    def test_total_events(self):
        records = self._records(n_full=5)
        result = aggregate(records)
        assert result["total_events"] == 5

    def test_required_keys_present(self):
        records = self._records(n_full=1)
        result = aggregate(records)
        required = {
            "total_events", "mean_field_coverage_pct", "coverage_tier_summary",
            "field_coverage", "missing_rank", "asset_coverage",
            "lifecycle_phase_coverage", "skip_reason_category_coverage",
            "dominant_latency_stage_coverage",
        }
        assert required.issubset(result.keys())

    def test_full_coverage_all_fields(self):
        records = self._records(n_full=4)
        result = aggregate(records)
        fc = result["field_coverage"]
        for canonical in CANONICAL_NAMES:
            assert fc[canonical]["coverage_pct"] == 100.0

    def test_zero_coverage_empty_payloads(self):
        records = self._records(n_full=0, n_empty=3)
        result = aggregate(records)
        fc = result["field_coverage"]
        for canonical in CANONICAL_NAMES:
            assert fc[canonical]["coverage_pct"] == 0.0

    def test_partial_coverage_mixed(self):
        full_recs = self._records(n_full=2)
        empty_recs = self._records(n_full=0, n_empty=2)
        result = aggregate(full_recs + empty_recs)
        fc = result["field_coverage"]
        for canonical in CANONICAL_NAMES:
            assert fc[canonical]["coverage_pct"] == 50.0

    def test_missing_rank_sorted_worst_first(self):
        # All full except fair_value missing
        recs = []
        for _ in range(4):
            p = _full_payload()
            del p["fair_value"]
            recs.append(extract_record(_event(p)))
        result = aggregate(recs)
        # fair_value should appear near top of missing_rank
        rank = result["missing_rank"]
        assert "fair_value" in rank
        # Confirm rank is sorted descending by missing_pct
        fc = result["field_coverage"]
        pcts = [fc[c]["missing_pct"] for c in rank]
        assert pcts == sorted(pcts, reverse=True)

    def test_asset_coverage_btc_vs_eth(self):
        btc_recs = self._records(n_full=3, asset="BTC")
        eth_recs = self._records(n_full=0, n_empty=3, asset="ETH")
        result = aggregate(btc_recs + eth_recs)
        ac = result["asset_coverage"]
        assert "BTC" in ac
        assert "ETH" in ac
        # BTC should have 100% coverage; ETH should have 0%
        btc_mean = sum(
            v for k, v in ac["BTC"].items() if k != "_total_events"
        ) / len(CANONICAL_NAMES)
        eth_mean = sum(
            v for k, v in ac["ETH"].items() if k != "_total_events"
        ) / len(CANONICAL_NAMES)
        assert btc_mean == 100.0
        assert eth_mean == 0.0

    def test_lifecycle_phase_correlation(self):
        scan_recs = self._records(n_full=2, phase="OPENING_SCAN")
        active_recs = self._records(n_full=0, n_empty=2, phase="ACTIVE_INVENTORY_TRADING")
        result = aggregate(scan_recs + active_recs)
        lc = result["lifecycle_phase_coverage"]
        assert "OPENING_SCAN" in lc
        assert "ACTIVE_INVENTORY_TRADING" in lc
        assert lc["OPENING_SCAN"]["mean_field_coverage_pct"] == 100.0
        assert lc["ACTIVE_INVENTORY_TRADING"]["mean_field_coverage_pct"] == 0.0

    def test_skip_reason_category_correlation(self):
        timing_recs = self._records(n_full=2, cat="timing")
        evidence_recs = self._records(n_full=0, n_empty=2, cat="evidence")
        result = aggregate(timing_recs + evidence_recs)
        cc = result["skip_reason_category_coverage"]
        assert "timing" in cc
        assert "evidence" in cc

    def test_dominant_latency_stage_correlation(self):
        cutoff_recs = self._records(n_full=3, stage="CUTOFF")
        disc_recs = self._records(n_full=0, n_empty=2, stage="DISCOVERY")
        result = aggregate(cutoff_recs + disc_recs)
        lc = result["dominant_latency_stage_coverage"]
        assert "CUTOFF" in lc
        assert "DISCOVERY" in lc

    def test_coverage_tier_summary_counts(self):
        records = self._records(n_full=1)
        result = aggregate(records)
        tiers = result["coverage_tier_summary"]
        total_fields = sum(tiers.values())
        assert total_fields == len(CANONICAL_NAMES)

    def test_null_reason_counts_in_field_coverage(self):
        recs = []
        for _ in range(3):
            p = _empty_payload(true_probability_null_reason="model_not_attempted")
            recs.append(extract_record(_event(p)))
        result = aggregate(recs)
        top_nr = result["field_coverage"]["probability_yes"]["top_null_reasons"]
        assert top_nr.get("model_not_attempted", 0) == 3

    def test_does_not_mutate_records(self):
        import copy
        records = self._records(n_full=2)
        original = copy.deepcopy(records)
        aggregate(records)
        assert records == original

    def test_per_field_counts_add_up(self):
        records = self._records(n_full=3, n_empty=2)
        result = aggregate(records)
        fc = result["field_coverage"]
        for canonical in CANONICAL_NAMES:
            s = fc[canonical]
            assert s["present"] + s["missing"] == result["total_events"]


# ---------------------------------------------------------------------------
# load_decision_events filtering
# ---------------------------------------------------------------------------

class TestLoadDecisionEvents:
    def _write_events(self, path: Path, events: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(json.dumps(e) for e in events), encoding="utf-8"
        )

    def test_nonexistent_file_returns_empty(self, tmp_path):
        result = load_decision_events("2099-01-01", tmp_path / "qd")
        assert result == []

    def test_run_id_filter(self, tmp_path):
        qd = tmp_path / "qd"
        self._write_events(
            qd / "decision_log" / "2026-05-15.jsonl",
            [
                {"run_id": "r1", "payload": {"asset": "BTC"}},
                {"run_id": "r2", "payload": {"asset": "BTC"}},
            ],
        )
        events = load_decision_events("2026-05-15", qd, run_id="r1")
        assert len(events) == 1
        assert events[0]["run_id"] == "r1"

    def test_asset_filter(self, tmp_path):
        qd = tmp_path / "qd"
        self._write_events(
            qd / "decision_log" / "2026-05-15.jsonl",
            [
                {"run_id": "r1", "payload": {"asset": "BTC"}},
                {"run_id": "r1", "payload": {"asset": "ETH"}},
            ],
        )
        events = load_decision_events("2026-05-15", qd, asset_filter="BTC")
        assert len(events) == 1
        assert events[0]["payload"]["asset"] == "BTC"

    def test_asset_filter_case_insensitive(self, tmp_path):
        qd = tmp_path / "qd"
        self._write_events(
            qd / "decision_log" / "2026-05-15.jsonl",
            [{"run_id": "r1", "payload": {"asset": "BTC"}}],
        )
        events = load_decision_events("2026-05-15", qd, asset_filter="btc")
        assert len(events) == 1

    def test_malformed_json_lines_skipped(self, tmp_path):
        qd = tmp_path / "qd"
        path = qd / "decision_log" / "2026-05-15.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '{"run_id":"r1","payload":{"asset":"BTC"}}\n'
            'NOT_JSON\n'
            '{"run_id":"r1","payload":{"asset":"ETH"}}\n',
            encoding="utf-8",
        )
        events = load_decision_events("2026-05-15", qd)
        assert len(events) == 2


# ---------------------------------------------------------------------------
# render_console smoke tests
# ---------------------------------------------------------------------------

class TestRenderConsole:
    def test_no_data(self, capsys):
        render_console({"total_events": 0}, "2026-05-15")
        out = capsys.readouterr().out
        assert "No decision events" in out

    def test_full_summary_renders(self, capsys):
        records = [extract_record(_event(_full_payload(
            lifecycle_phase="OPENING_SCAN",
            skip_reason_category="timing",
            dominant_latency_stage="CUTOFF",
        )))]
        summary = aggregate(records)
        summary["date"] = "2026-05-15"
        render_console(summary, "2026-05-15")
        out = capsys.readouterr().out
        assert "EV Field Coverage Audit" in out
        assert "fair_value" in out
        assert "probability_yes" in out

    def test_renders_btc_vs_eth(self, capsys):
        recs = [
            extract_record(_event(_full_payload(), asset="BTC")),
            extract_record(_event(_empty_payload(), asset="ETH")),
        ]
        summary = aggregate(recs)
        render_console(summary, "2026-05-15")
        out = capsys.readouterr().out
        assert "BTC" in out
        assert "ETH" in out


# ---------------------------------------------------------------------------
# Additive-only / no runtime modification
# ---------------------------------------------------------------------------

class TestAdditiveOnly:
    def test_no_runtime_imports(self):
        import tools.ev_field_coverage_audit as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        forbidden = [
            "polymarket.trader", "utils.risk_manager", "order_manager",
            "virtual_ptb", "live_order", "execute_order", "sign_order",
        ]
        for token in forbidden:
            assert token not in source, f"Audit tool must not import runtime: {token}"

    def test_canonical_names_count(self):
        assert len(CANONICAL_NAMES) == 14

    def test_canonical_names_match_spec(self):
        expected = {
            "probability_yes", "probability_confidence", "fair_value",
            "edge_bps", "spread_bps", "bid", "ask", "mid_price",
            "book_imbalance", "top_depth_yes", "top_depth_no",
            "ev_per_dollar", "planned_size", "data_quality_score",
        }
        assert set(CANONICAL_NAMES) == expected

    def test_aggregate_no_side_effects_on_input(self):
        import copy
        records = [extract_record(_event(_full_payload()))]
        original = copy.deepcopy(records)
        aggregate(records)
        assert records == original
