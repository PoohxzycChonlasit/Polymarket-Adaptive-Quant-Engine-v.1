"""
Tests for tools/lifecycle_latency_report.py — Lifecycle Latency Report Tool v1.

Coverage:
- _percentile / _pct_stats accuracy
- load_research_snapshots split logic
- build_latency_records merge and highest-total-wins logic
- asset_filter behaviour
- aggregate structure and metric correctness
- no-entry correlation table population
- missing-data / empty-input fail-soft
- additive-only / no runtime modification assertions
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from tools.lifecycle_latency_report import (
    STAGE_FIELDS,
    _percentile,
    _pct_stats,
    _payload,
    _safe_float,
    _safe_int,
    aggregate,
    build_latency_records,
    load_research_snapshots,
    render_console,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snap_event(ticker: str, epoch: int, total_ms: float, **extra) -> dict:
    payload = {
        "ticker": ticker,
        "market_epoch_start": epoch,
        "total_discovery_to_decision_ms": total_ms,
        **extra,
    }
    return {"payload": payload, "run_id": "r1"}


def _milestone_event(ticker: str, epoch: int, phase: str, sso: int = 10) -> dict:
    return {
        "payload": {
            "ticker": ticker,
            "market_epoch_start": epoch,
            "event_subtype": "lifecycle_milestone",
            "lifecycle_phase": phase,
            "seconds_since_market_open": sso,
        },
        "run_id": "r1",
    }


def _decision_event(ticker: str, epoch: int, skipped: bool = True,
                    cat: str = "timing", pri: str = "book_warming",
                    conf: float = 0.9) -> dict:
    return {
        "payload": {
            "asset": ticker,
            "market_epoch_start": epoch,
            "skipped": skipped,
            "skip_reason_category": cat,
            "skip_reason_primary": pri,
            "no_entry_root_cause_confidence": conf,
            "seconds_remaining": 120,
            "lifecycle_phase": "READY",
        },
        "run_id": "r1",
    }


# ---------------------------------------------------------------------------
# _percentile
# ---------------------------------------------------------------------------

class TestPercentile:
    def test_empty_returns_zero(self):
        assert _percentile([], 50) == 0.0

    def test_single_value(self):
        assert _percentile([42.0], 50) == 42.0
        assert _percentile([42.0], 99) == 42.0

    def test_known_median(self):
        # [1,2,3,4,5] → median = 3
        assert _percentile([1.0, 2.0, 3.0, 4.0, 5.0], 50) == 3.0

    def test_p90_of_ten(self):
        # [1..10] → p90 idx = 0.9*9 = 8.1 → 9 + 0.1*(10-9) = 9.1
        vals = [float(i) for i in range(1, 11)]
        result = _percentile(vals, 90)
        assert 9.0 <= result <= 10.0

    def test_p99_large_list(self):
        vals = [float(i) for i in range(1, 101)]
        result = _percentile(vals, 99)
        assert result >= 98.0

    def test_unsorted_input(self):
        assert _percentile([5.0, 1.0, 3.0], 50) == 3.0


class TestPctStats:
    def test_empty_returns_zeros(self):
        result = _pct_stats([])
        assert result == {"p50": 0.0, "p90": 0.0, "p99": 0.0, "mean": 0.0, "count": 0}

    def test_known_values(self):
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = _pct_stats(vals)
        assert result["count"] == 5
        assert result["p50"] == 30.0
        assert result["mean"] == 30.0
        assert result["p90"] >= 40.0

    def test_keys_present(self):
        result = _pct_stats([100.0])
        assert set(result.keys()) == {"p50", "p90", "p99", "mean", "count"}


# ---------------------------------------------------------------------------
# load_research_snapshots — split logic
# ---------------------------------------------------------------------------

class TestLoadResearchSnapshots:
    def test_nonexistent_file_returns_empty(self, tmp_path):
        snaps, milestones = load_research_snapshots("2099-01-01", tmp_path / "qd")
        assert snaps == []
        assert milestones == []

    def test_splits_milestone_vs_latency(self, tmp_path):
        qd = tmp_path / "qd" / "research_log"
        qd.mkdir(parents=True)
        import json
        lines = [
            json.dumps({"payload": {"event_subtype": "lifecycle_milestone", "ticker": "BTC",
                                    "market_epoch_start": 1000, "lifecycle_phase": "token_ready",
                                    "seconds_since_market_open": 5}}),
            json.dumps({"payload": {"ticker": "BTC", "market_epoch_start": 1000,
                                    "total_discovery_to_decision_ms": 12000.0,
                                    "discovery_to_token_ready_ms": 3000.0}}),
            json.dumps({"payload": {"ticker": "ETH", "market_epoch_start": 2000,
                                    "total_discovery_to_decision_ms": 8000.0}}),
        ]
        (qd / "2026-05-14.jsonl").write_text("\n".join(lines), encoding="utf-8")

        snaps, milestones = load_research_snapshots("2026-05-14", tmp_path / "qd")
        assert len(snaps) == 2
        assert len(milestones) == 1
        assert _payload(milestones[0])["lifecycle_phase"] == "token_ready"

    def test_run_id_filter(self, tmp_path):
        qd = tmp_path / "qd" / "research_log"
        qd.mkdir(parents=True)
        import json
        lines = [
            json.dumps({"run_id": "r1", "payload": {"ticker": "BTC", "market_epoch_start": 1,
                                                     "total_discovery_to_decision_ms": 100.0}}),
            json.dumps({"run_id": "r2", "payload": {"ticker": "BTC", "market_epoch_start": 2,
                                                     "total_discovery_to_decision_ms": 200.0}}),
        ]
        (qd / "2026-05-14.jsonl").write_text("\n".join(lines), encoding="utf-8")

        snaps, _ = load_research_snapshots("2026-05-14", tmp_path / "qd", run_id="r1")
        assert len(snaps) == 1
        assert _payload(snaps[0])["market_epoch_start"] == 1

    def test_ignores_events_without_latency_fields(self, tmp_path):
        qd = tmp_path / "qd" / "research_log"
        qd.mkdir(parents=True)
        import json
        lines = [
            json.dumps({"payload": {"ticker": "BTC", "market_epoch_start": 1, "some_other": "field"}}),
        ]
        (qd / "2026-05-14.jsonl").write_text("\n".join(lines), encoding="utf-8")
        snaps, milestones = load_research_snapshots("2026-05-14", tmp_path / "qd")
        assert snaps == []
        assert milestones == []


# ---------------------------------------------------------------------------
# build_latency_records
# ---------------------------------------------------------------------------

class TestBuildLatencyRecords:
    def _make_records(self, latency=None, milestones=None, decisions=None, asset=None):
        return build_latency_records(
            latency or [],
            milestones or [],
            decisions or [],
            asset_filter=asset,
        )

    def test_empty_inputs_returns_empty(self):
        assert self._make_records() == []

    def test_basic_record_built(self):
        snaps = [_snap_event("BTC", 1000, 15000.0)]
        records = self._make_records(latency=snaps)
        assert len(records) == 1
        r = records[0]
        assert r["ticker"] == "BTC"
        assert r["epoch"] == 1000
        assert r["stage_ms"]["TOTAL"] == 15000.0

    def test_highest_total_ms_wins(self):
        # Two snapshots for same (ticker, epoch) — higher total should win
        snaps = [
            _snap_event("BTC", 1000, 5000.0),
            _snap_event("BTC", 1000, 20000.0),  # should win
        ]
        records = self._make_records(latency=snaps)
        assert len(records) == 1
        assert records[0]["stage_ms"]["TOTAL"] == 20000.0

    def test_asset_filter_excludes_other_assets(self):
        snaps = [
            _snap_event("BTC", 1000, 10000.0),
            _snap_event("ETH", 2000, 8000.0),
        ]
        records = self._make_records(latency=snaps, asset="BTC")
        assert len(records) == 1
        assert records[0]["ticker"] == "BTC"

    def test_asset_filter_case_insensitive(self):
        snaps = [_snap_event("BTC", 1000, 10000.0)]
        records = self._make_records(latency=snaps, asset="btc")
        assert len(records) == 1

    def test_decision_metadata_merged(self):
        snaps = [_snap_event("BTC", 1000, 12000.0)]
        decs = [_decision_event("BTC", 1000, skipped=True, cat="timing", pri="book_warming", conf=0.85)]
        records = self._make_records(latency=snaps, decisions=decs)
        r = records[0]
        assert r["skip_reason_category"] == "timing"
        assert r["skip_reason_primary"] == "book_warming"
        assert r["root_cause_confidence"] == 0.85
        assert r["skipped"] is True

    def test_milestone_data_merged(self):
        snaps = [_snap_event("BTC", 1000, 10000.0)]
        ms = [
            _milestone_event("BTC", 1000, "token_ready", sso=5),
            _milestone_event("BTC", 1000, "first_executable_book", sso=60),
        ]
        records = self._make_records(latency=snaps, milestones=ms)
        r = records[0]
        assert r["executable_reached"] is True
        assert r["executable_seconds_since_open"] == 60
        assert r["highest_milestone"] == "first_executable_book"

    def test_missing_milestone_executable_not_reached(self):
        snaps = [_snap_event("BTC", 1000, 10000.0)]
        ms = [_milestone_event("BTC", 1000, "token_ready", sso=5)]
        records = self._make_records(latency=snaps, milestones=ms)
        assert records[0]["executable_reached"] is False

    def test_multiple_assets_separate_records(self):
        snaps = [
            _snap_event("BTC", 1000, 10000.0),
            _snap_event("ETH", 2000, 9000.0),
        ]
        records = self._make_records(latency=snaps)
        tickers = {r["ticker"] for r in records}
        assert tickers == {"BTC", "ETH"}

    def test_stage_ms_only_nonnegative(self):
        snaps = [_snap_event("BTC", 1000, 10000.0,
                             discovery_to_token_ready_ms=2000.0,
                             token_ready_to_book_ms=-1.0)]  # negative should be excluded
        records = self._make_records(latency=snaps)
        stage_ms = records[0]["stage_ms"]
        assert "DISCOVERY" in stage_ms
        assert "TOKEN_READY" not in stage_ms  # negative filtered by _safe_float


# ---------------------------------------------------------------------------
# aggregate
# ---------------------------------------------------------------------------

class TestAggregate:
    def _make_full_record(self, ticker="BTC", epoch=1000, total_ms=12000.0,
                          skipped=True, cat="timing", pri="book_warming",
                          dominant="CUTOFF", lc_class="LATE", conf=0.85,
                          exec_reached=True, exec_sso=60) -> dict:
        return {
            "ticker": ticker,
            "epoch": epoch,
            "stage_ms": {"TOTAL": total_ms, "CUTOFF": 5000.0, "DISCOVERY": 2000.0},
            "dominant_latency_stage": dominant,
            "lifecycle_latency_classification": lc_class,
            "actual_decision": "skip",
            "skipped": skipped,
            "skip_reason_category": cat,
            "skip_reason_primary": pri,
            "root_cause_confidence": conf,
            "lifecycle_phase": "READY",
            "seconds_remaining": 120,
            "highest_milestone": "first_executable_book",
            "executable_reached": exec_reached,
            "executable_seconds_since_open": exec_sso,
            "milestones": {},
        }

    def test_empty_records_returns_no_data(self):
        result = aggregate([])
        assert result["total_records"] == 0

    def test_total_records_count(self):
        records = [self._make_full_record(epoch=i) for i in range(5)]
        result = aggregate(records)
        assert result["total_records"] == 5

    def test_required_keys_present(self):
        records = [self._make_full_record()]
        result = aggregate(records)
        expected_keys = {
            "total_records",
            "stage_latency_percentiles",
            "dominant_stage_distribution",
            "latency_classification_distribution",
            "entry_vs_no_entry_latency",
            "asset_latency_breakdown",
            "lifecycle_phase_distribution",
            "executable_before_cutoff_rate",
            "executable_reached_count",
            "first_executable_book_timing",
            "highest_milestone_at_decision",
            "latency_stage_vs_skip_reason_category",
            "latency_stage_avg_root_cause_confidence",
        }
        assert expected_keys.issubset(result.keys())

    def test_stage_latency_percentiles_all_stages(self):
        records = [self._make_full_record()]
        result = aggregate(records)
        for stage in STAGE_FIELDS:
            assert stage in result["stage_latency_percentiles"]

    def test_executable_rate_calculation(self):
        records = [
            self._make_full_record(epoch=1, exec_reached=True),
            self._make_full_record(epoch=2, exec_reached=True),
            self._make_full_record(epoch=3, exec_reached=False),
            self._make_full_record(epoch=4, exec_reached=False),
        ]
        result = aggregate(records)
        assert result["executable_before_cutoff_rate"] == 0.5
        assert result["executable_reached_count"] == 2

    def test_entry_vs_no_entry_split(self):
        records = [
            self._make_full_record(epoch=1, skipped=True, total_ms=15000.0),
            self._make_full_record(epoch=2, skipped=False, total_ms=5000.0),
        ]
        result = aggregate(records)
        no_entry_total = result["entry_vs_no_entry_latency"]["no_entry"]["TOTAL"]
        entry_total = result["entry_vs_no_entry_latency"]["entry"]["TOTAL"]
        assert no_entry_total["count"] == 1
        assert entry_total["count"] == 1
        assert no_entry_total["p50"] == 15000.0
        assert entry_total["p50"] == 5000.0

    def test_no_entry_correlation_table_populated(self):
        records = [
            self._make_full_record(epoch=1, dominant="CUTOFF", cat="timing"),
            self._make_full_record(epoch=2, dominant="CUTOFF", cat="evidence"),
            self._make_full_record(epoch=3, dominant="DISCOVERY", cat="timing"),
        ]
        result = aggregate(records)
        corr = result["latency_stage_vs_skip_reason_category"]
        assert "CUTOFF" in corr
        assert corr["CUTOFF"].get("timing", 0) == 1
        assert corr["CUTOFF"].get("evidence", 0) == 1
        assert "DISCOVERY" in corr
        assert corr["DISCOVERY"].get("timing", 0) == 1

    def test_avg_confidence_per_stage(self):
        records = [
            self._make_full_record(epoch=1, dominant="CUTOFF", conf=0.8),
            self._make_full_record(epoch=2, dominant="CUTOFF", conf=0.6),
        ]
        result = aggregate(records)
        avg = result["latency_stage_avg_root_cause_confidence"]
        assert "CUTOFF" in avg
        assert abs(avg["CUTOFF"] - 0.7) < 0.01

    def test_asset_breakdown_contains_asset(self):
        records = [
            self._make_full_record(ticker="BTC", epoch=1),
            self._make_full_record(ticker="ETH", epoch=2),
        ]
        result = aggregate(records)
        assert "BTC" in result["asset_latency_breakdown"]
        assert "ETH" in result["asset_latency_breakdown"]

    def test_highest_milestone_counts(self):
        records = [
            self._make_full_record(epoch=1),   # highest_milestone = "first_executable_book"
            self._make_full_record(epoch=2),
        ]
        result = aggregate(records)
        hm = result["highest_milestone_at_decision"]
        assert hm.get("first_executable_book", 0) == 2


# ---------------------------------------------------------------------------
# Missing data / fail-soft
# ---------------------------------------------------------------------------

class TestMissingDataFailSoft:
    def test_record_with_no_stage_ms(self):
        record = {
            "ticker": "BTC",
            "epoch": 1000,
            "stage_ms": {},
            "dominant_latency_stage": "",
            "lifecycle_latency_classification": "",
            "actual_decision": "",
            "skipped": True,
            "skip_reason_category": "",
            "skip_reason_primary": "",
            "root_cause_confidence": None,
            "lifecycle_phase": "UNKNOWN",
            "seconds_remaining": None,
            "highest_milestone": "",
            "executable_reached": False,
            "executable_seconds_since_open": None,
            "milestones": {},
        }
        result = aggregate([record])
        assert result["total_records"] == 1
        assert result["stage_latency_percentiles"]["TOTAL"]["count"] == 0

    def test_build_records_no_ticker_skipped(self):
        snaps = [{"payload": {"market_epoch_start": 1000,
                              "total_discovery_to_decision_ms": 5000.0},
                  "run_id": "r1"}]  # no ticker
        records = build_latency_records(snaps, [], [])
        assert records == []

    def test_build_records_no_epoch_skipped(self):
        snaps = [{"payload": {"ticker": "BTC", "total_discovery_to_decision_ms": 5000.0},
                  "run_id": "r1"}]  # no epoch
        records = build_latency_records(snaps, [], [])
        assert records == []

    def test_pct_stats_single_value(self):
        result = _pct_stats([999.0])
        assert result["count"] == 1
        assert result["p50"] == 999.0
        assert result["p99"] == 999.0
        assert result["mean"] == 999.0


# ---------------------------------------------------------------------------
# render_console — smoke test (no exceptions)
# ---------------------------------------------------------------------------

class TestRenderConsole:
    def test_render_no_data(self, capsys):
        render_console({"total_records": 0}, "2026-05-14")
        out = capsys.readouterr().out
        assert "No lifecycle latency records" in out

    def test_render_with_data(self, capsys):
        records = [{
            "ticker": "BTC",
            "epoch": 1000,
            "stage_ms": {"TOTAL": 12000.0, "CUTOFF": 5000.0},
            "dominant_latency_stage": "CUTOFF",
            "lifecycle_latency_classification": "LATE",
            "actual_decision": "skip",
            "skipped": True,
            "skip_reason_category": "timing",
            "skip_reason_primary": "book_warming",
            "root_cause_confidence": 0.9,
            "lifecycle_phase": "READY",
            "seconds_remaining": 120,
            "highest_milestone": "first_executable_book",
            "executable_reached": True,
            "executable_seconds_since_open": 60,
            "milestones": {},
        }]
        summary = aggregate(records)
        summary["date"] = "2026-05-14"
        render_console(summary, "2026-05-14")
        out = capsys.readouterr().out
        assert "Lifecycle Latency Report" in out
        assert "CUTOFF" in out


# ---------------------------------------------------------------------------
# Additive-only / no runtime modification
# ---------------------------------------------------------------------------

class TestAdditiveOnly:
    def test_stage_fields_is_read_only_dict(self):
        original_keys = set(STAGE_FIELDS.keys())
        assert original_keys == {
            "DISCOVERY", "TOKEN_READY", "ORDERBOOK",
            "SPREAD_NORMALIZATION", "DECISION", "CUTOFF", "TOTAL",
        }

    def test_tool_has_no_runtime_imports(self):
        import tools.lifecycle_latency_report as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        forbidden = ["polymarket.trader", "utils.risk_manager", "order_manager",
                     "virtual_ptb", "execute", "live_order"]
        for token in forbidden:
            assert token not in source, f"Tool should not import runtime: {token}"

    def test_aggregate_does_not_mutate_records(self):
        records = [{
            "ticker": "BTC",
            "epoch": 1000,
            "stage_ms": {"TOTAL": 10000.0},
            "dominant_latency_stage": "CUTOFF",
            "lifecycle_latency_classification": "LATE",
            "actual_decision": "skip",
            "skipped": True,
            "skip_reason_category": "timing",
            "skip_reason_primary": "book_warming",
            "root_cause_confidence": 0.9,
            "lifecycle_phase": "READY",
            "seconds_remaining": 120,
            "highest_milestone": "first_executable_book",
            "executable_reached": True,
            "executable_seconds_since_open": 60,
            "milestones": {},
        }]
        import copy
        original = copy.deepcopy(records)
        aggregate(records)
        assert records == original

    def test_build_latency_records_does_not_mutate_inputs(self):
        import copy
        snaps = [_snap_event("BTC", 1000, 10000.0)]
        original_snaps = copy.deepcopy(snaps)
        build_latency_records(snaps, [], [])
        assert snaps == original_snaps
