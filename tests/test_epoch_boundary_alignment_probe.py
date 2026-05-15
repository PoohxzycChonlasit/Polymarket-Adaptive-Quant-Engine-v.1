"""
Tests for Epoch Boundary Alignment Probe v1.

Coverage:
- seconds_since_open conversion
- classify_window correctness
- _int_field / _bool_field / _epoch_start extraction
- extract_epoch_record: canonical timing record from event group
- extract_epoch_record: missing-data fail-soft
- build_epoch_records: grouping by (asset, epoch_start_ts)
- build_epoch_records: filters fake/test epoch timestamps
- aggregate: structure, key metrics, window percentages
- aggregate: empty-input safe
- aggregate: BTC vs ETH split
- aggregate: preload correlation keys present
- extract_cycle_gaps: happy path and missing-data fail-soft
- load_snapshot_events: missing file returns empty
- render_console: no crash on empty or normal stats
- no runtime imports
- no mutation of input data
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from tools.epoch_boundary_alignment_probe import (
    EPOCH_DURATION_SECONDS,
    MIN_REAL_EPOCH_TS,
    _bool_field,
    _epoch_start,
    _int_field,
    _milestone_completeness,
    aggregate,
    build_epoch_records,
    classify_window,
    extract_cycle_gaps,
    extract_epoch_record,
    load_snapshot_events,
    render_console,
    seconds_since_open,
    write_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REAL_EPOCH = 1_778_810_700  # a real epoch timestamp well above the threshold

def _event(payload: dict, run_id: str = "r1") -> dict:
    return {"payload": payload, "run_id": run_id}


def _snap(
    asset: str = "BTC",
    epoch_ts: int = _REAL_EPOCH,
    first_disc_sr: int | None = 200,
    first_tok_sr:  int | None = 200,
    first_ob_sr:   int | None = 198,
    first_trad_sr: int | None = 190,
    preload_success: bool | None = True,
    preload_cache_hit: bool | None = False,
    preload_latency_ms: int | None = 350,
    entry_cutoff: int = 90,
    **extra,
) -> dict:
    p = {
        "asset": asset,
        "epoch_start_ts": epoch_ts,
        "first_discovered_seconds_remaining": first_disc_sr,
        "first_token_ready_seconds_remaining": first_tok_sr,
        "first_orderbook_seen_seconds_remaining": first_ob_sr,
        "first_tradable_seconds_remaining": first_trad_sr,
        "first_spread_normalized_seconds_remaining": first_trad_sr,
        "first_nonzero_bidask_seconds_remaining": first_ob_sr,
        "entry_cutoff_seconds": entry_cutoff,
        "preload_success": preload_success,
        "preload_cache_hit": preload_cache_hit,
        "preload_latency_ms": preload_latency_ms,
    }
    p.update(extra)
    return _event(p)


def _research_event(
    interval_s: float = 11.5,
    asset: str = "BTC",
) -> dict:
    return _event({
        "asset": asset,
        "decision_cycle_interval_seconds": interval_s,
    })


# ---------------------------------------------------------------------------
# seconds_since_open
# ---------------------------------------------------------------------------

class TestSecondsSinceOpen:
    def test_basic_conversion(self):
        assert seconds_since_open(200) == 100    # 300 - 200 = 100
        assert seconds_since_open(300) == 0      # epoch just opened
        assert seconds_since_open(1)   == 299    # nearly closed

    def test_zero_returns_none(self):
        assert seconds_since_open(0) is None

    def test_none_input_returns_none(self):
        assert seconds_since_open(None) is None

    def test_negative_returns_none(self):
        assert seconds_since_open(-5) is None

    def test_above_epoch_duration_returns_none(self):
        assert seconds_since_open(301) is None

    def test_float_input(self):
        result = seconds_since_open(200.0)
        assert result == 100

    def test_string_float_invalid(self):
        assert seconds_since_open("bad") is None  # type: ignore[arg-type]

    def test_epoch_duration_boundary(self):
        # 300 remaining → sso = 0 → valid
        assert seconds_since_open(300) == 0

    def test_one_remaining(self):
        assert seconds_since_open(1) == 299


# ---------------------------------------------------------------------------
# classify_window
# ---------------------------------------------------------------------------

class TestClassifyWindow:
    def test_opening_scan_boundaries(self):
        assert classify_window(0)  == "OPENING_SCAN"
        assert classify_window(34) == "OPENING_SCAN"

    def test_active_inventory_trading_boundaries(self):
        assert classify_window(35)  == "ACTIVE_INVENTORY_TRADING"
        assert classify_window(100) == "ACTIVE_INVENTORY_TRADING"
        assert classify_window(239) == "ACTIVE_INVENTORY_TRADING"

    def test_profit_management_boundaries(self):
        assert classify_window(240) == "PROFIT_MANAGEMENT"
        assert classify_window(269) == "PROFIT_MANAGEMENT"

    def test_final_derisk_boundaries(self):
        assert classify_window(270) == "FINAL_DERISK"
        assert classify_window(299) == "FINAL_DERISK"

    def test_closed_or_unsafe(self):
        assert classify_window(300) == "CLOSED_OR_UNSAFE"
        assert classify_window(999) == "CLOSED_OR_UNSAFE"

    def test_none_returns_unknown(self):
        assert classify_window(None) == "UNKNOWN"

    def test_negative_returns_unknown(self):
        assert classify_window(-1) == "UNKNOWN"


# ---------------------------------------------------------------------------
# Field extraction helpers
# ---------------------------------------------------------------------------

class TestIntField:
    def test_normal_value(self):
        assert _int_field({"x": 150}, "x") == 150

    def test_zero_returns_none(self):
        assert _int_field({"x": 0}, "x") is None

    def test_negative_returns_none(self):
        assert _int_field({"x": -5}, "x") is None

    def test_missing_key_returns_none(self):
        assert _int_field({}, "x") is None

    def test_none_value_returns_none(self):
        assert _int_field({"x": None}, "x") is None

    def test_float_string_truncated(self):
        assert _int_field({"x": "200.7"}, "x") == 200

    def test_invalid_string_returns_none(self):
        assert _int_field({"x": "bad"}, "x") is None


class TestBoolField:
    def test_true(self):
        assert _bool_field({"x": True}, "x") is True

    def test_false(self):
        assert _bool_field({"x": False}, "x") is False

    def test_string_true(self):
        assert _bool_field({"x": "true"}, "x") is True

    def test_string_false(self):
        assert _bool_field({"x": "false"}, "x") is False

    def test_missing_returns_none(self):
        assert _bool_field({}, "x") is None

    def test_none_returns_none(self):
        assert _bool_field({"x": None}, "x") is None


class TestEpochStart:
    def test_epoch_start_ts(self):
        assert _epoch_start({"epoch_start_ts": _REAL_EPOCH}) == _REAL_EPOCH

    def test_epoch_start_fallback(self):
        assert _epoch_start({"epoch_start": _REAL_EPOCH}) == _REAL_EPOCH

    def test_market_epoch_start_fallback(self):
        assert _epoch_start({"market_epoch_start": _REAL_EPOCH}) == _REAL_EPOCH

    def test_fake_epoch_rejected(self):
        assert _epoch_start({"epoch_start_ts": 123}) is None

    def test_zero_rejected(self):
        assert _epoch_start({"epoch_start_ts": 0}) is None

    def test_missing_returns_none(self):
        assert _epoch_start({}) is None

    def test_invalid_string_returns_none(self):
        assert _epoch_start({"epoch_start_ts": "bad"}) is None


# ---------------------------------------------------------------------------
# extract_epoch_record
# ---------------------------------------------------------------------------

class TestExtractEpochRecord:
    def test_basic_extraction(self):
        events = [_snap()]
        rec = extract_epoch_record(events)
        assert rec["asset"] == "BTC"
        assert rec["epoch_start_ts"] == _REAL_EPOCH

    def test_sso_conversion(self):
        events = [_snap(first_disc_sr=200, first_tok_sr=200, first_ob_sr=198, first_trad_sr=190)]
        rec = extract_epoch_record(events)
        assert rec["first_discovered_sso"]  == 100   # 300 - 200
        assert rec["first_token_ready_sso"] == 100   # 300 - 200
        assert rec["first_orderbook_sso"]   == 102   # 300 - 198
        assert rec["first_tradable_sso"]    == 110   # 300 - 190

    def test_delay_computation(self):
        events = [_snap(first_disc_sr=200, first_tok_sr=200, first_ob_sr=198, first_trad_sr=190)]
        rec = extract_epoch_record(events)
        assert rec["token_publication_delay_seconds"] == 100   # sso when token ready
        assert rec["orderbook_ready_delay_seconds"]   == 102
        assert rec["tradable_delay_seconds"]           == 110

    def test_window_classification(self):
        # first_tok_sr=200 → sso=100 → ACTIVE_INVENTORY_TRADING
        events = [_snap(first_tok_sr=200)]
        rec = extract_epoch_record(events)
        assert rec["tok_window"] == "ACTIVE_INVENTORY_TRADING"

    def test_tradable_before_cutoff_true(self):
        # first_trad_sr=190 > entry_cutoff=90 → before cutoff
        events = [_snap(first_trad_sr=190, entry_cutoff=90)]
        rec = extract_epoch_record(events)
        assert rec["tradable_before_cutoff"] is True

    def test_tradable_before_cutoff_false(self):
        # first_trad_sr=50 < entry_cutoff=90 → after cutoff
        events = [_snap(first_trad_sr=50, entry_cutoff=90)]
        rec = extract_epoch_record(events)
        assert rec["tradable_before_cutoff"] is False

    def test_missing_token_ids_gives_none(self):
        events = [_snap(first_tok_sr=0)]
        rec = extract_epoch_record(events)
        assert rec["first_token_ready_sso"] is None
        assert rec["has_token_ready"] is False

    def test_missing_tradable_gives_none(self):
        events = [_snap(first_trad_sr=0)]
        rec = extract_epoch_record(events)
        assert rec["first_tradable_sso"] is None
        assert rec["has_tradable"] is False

    def test_multi_event_best_completeness_wins(self):
        # Event 1: all milestones present
        e1 = _snap(first_disc_sr=200, first_tok_sr=200, first_ob_sr=198, first_trad_sr=190)
        # Event 2: only discovery
        e2 = _snap(first_disc_sr=200, first_tok_sr=0, first_ob_sr=0, first_trad_sr=0)
        rec = extract_epoch_record([e2, e1])
        assert rec["has_tradable"] is True

    def test_multi_event_fallback_fills_gaps(self):
        # Event 1: has tradable only
        e1 = _snap(first_disc_sr=0, first_tok_sr=0, first_ob_sr=0, first_trad_sr=180)
        # Event 2: has disc + tok only
        e2 = _snap(first_disc_sr=200, first_tok_sr=200, first_ob_sr=0, first_trad_sr=0)
        rec = extract_epoch_record([e1, e2])
        # Best (most complete) gets tok from e2, tradable from e1
        assert rec["has_tradable"] is True or rec["has_token_ready"] is True

    def test_empty_events_returns_empty_dict(self):
        rec = extract_epoch_record([])
        assert rec == {}

    def test_preload_fields_extracted(self):
        events = [_snap(preload_success=True, preload_cache_hit=True, preload_latency_ms=250)]
        rec = extract_epoch_record(events)
        assert rec["preload_success"] is True
        assert rec["preload_cache_hit"] is True
        assert rec["preload_latency_ms"] == 250

    def test_input_not_mutated(self):
        events = [_snap()]
        original_payload = dict(events[0]["payload"])
        extract_epoch_record(events)
        assert events[0]["payload"] == original_payload

    def test_tok_window_opening_scan(self):
        # first_tok_sr=295 → sso=5 → OPENING_SCAN
        events = [_snap(first_tok_sr=295)]
        rec = extract_epoch_record(events)
        assert rec["tok_window"] == "OPENING_SCAN"

    def test_eth_asset(self):
        events = [_snap(asset="ETH")]
        rec = extract_epoch_record(events)
        assert rec["asset"] == "ETH"


# ---------------------------------------------------------------------------
# build_epoch_records
# ---------------------------------------------------------------------------

class TestBuildEpochRecords:
    def test_groups_by_asset_and_epoch(self):
        epoch_a = _REAL_EPOCH
        epoch_b = _REAL_EPOCH + 300
        events = [
            _snap(asset="BTC", epoch_ts=epoch_a),
            _snap(asset="BTC", epoch_ts=epoch_b),
            _snap(asset="ETH", epoch_ts=epoch_a),
        ]
        records = build_epoch_records(events)
        assert len(records) == 3

    def test_same_epoch_merged_into_one_record(self):
        events = [
            _snap(asset="BTC", epoch_ts=_REAL_EPOCH),
            _snap(asset="BTC", epoch_ts=_REAL_EPOCH, first_tok_sr=195),
        ]
        records = build_epoch_records(events)
        assert len(records) == 1

    def test_fake_epoch_timestamps_filtered(self):
        events = [
            _snap(asset="BTC", epoch_ts=123),   # fake
            _snap(asset="BTC", epoch_ts=_REAL_EPOCH),  # real
        ]
        records = build_epoch_records(events)
        # Only the real epoch produces a record
        assert len(records) == 1
        assert records[0]["epoch_start_ts"] == _REAL_EPOCH

    def test_empty_events_returns_empty_list(self):
        assert build_epoch_records([]) == []

    def test_missing_epoch_ts_excluded(self):
        e = _event({"asset": "BTC"})  # no epoch_start_ts
        records = build_epoch_records([e])
        assert records == []

    def test_result_has_expected_keys(self):
        events = [_snap()]
        rec = build_epoch_records(events)[0]
        required = {
            "asset", "epoch_start_ts", "first_discovered_sso", "first_token_ready_sso",
            "first_orderbook_sso", "first_tradable_sso", "tok_window", "trad_window",
            "tradable_before_cutoff", "has_token_ready", "has_tradable",
            "token_publication_delay_seconds", "tradable_delay_seconds",
        }
        assert required.issubset(rec.keys())


# ---------------------------------------------------------------------------
# aggregate
# ---------------------------------------------------------------------------

class TestAggregate:
    def _make_records(self, n_btc: int = 3, n_eth: int = 2, **kwargs) -> list[dict]:
        recs = []
        epoch = _REAL_EPOCH
        for i in range(n_btc):
            evs = [_snap(asset="BTC", epoch_ts=epoch + i * 300, **kwargs)]
            recs.append(extract_epoch_record(evs))
        for i in range(n_eth):
            evs = [_snap(asset="ETH", epoch_ts=epoch + i * 300, **kwargs)]
            recs.append(extract_epoch_record(evs))
        return recs

    def test_empty_records_safe(self):
        result = aggregate([])
        assert result["total_epochs"] == 0
        assert "guardrail" in result

    def test_total_epochs_correct(self):
        recs = self._make_records(n_btc=3, n_eth=2)
        r = aggregate(recs)
        assert r["total_epochs"] == 5

    def test_required_keys_present(self):
        recs = self._make_records()
        r = aggregate(recs)
        required = {
            "total_epochs",
            "first_discovered_sso_stats",
            "first_token_ready_sso_stats",
            "first_orderbook_sso_stats",
            "first_executable_sso_stats",
            "token_publication_delay_stats",
            "orderbook_ready_delay_stats",
            "tradable_delay_stats",
            "epochs_with_token_ready_count",
            "epochs_with_token_ready_pct",
            "epochs_with_tradable_count",
            "epochs_with_tradable_pct",
            "epochs_token_never_reached_count",
            "tok_window_distribution",
            "trad_window_distribution",
            "pct_token_ready_in_opening_scan",
            "pct_token_ready_in_active_window",
            "pct_tradable_before_entry_cutoff",
            "asset_breakdown",
            "preload_tradable_delay_correlation",
            "cycle_gap_correlation",
            "guardrail",
        }
        assert required.issubset(r.keys())

    def test_asset_breakdown_has_btc_and_eth(self):
        recs = self._make_records(n_btc=2, n_eth=1)
        r = aggregate(recs)
        assert "BTC" in r["asset_breakdown"]
        assert "ETH" in r["asset_breakdown"]
        assert r["asset_breakdown"]["BTC"]["total_epochs"] == 2
        assert r["asset_breakdown"]["ETH"]["total_epochs"] == 1

    def test_pct_tradable_before_cutoff(self):
        # All records have first_trad_sr=190 > entry_cutoff=90
        recs = self._make_records(first_trad_sr=190, entry_cutoff=90)
        r = aggregate(recs)
        assert r["pct_tradable_before_entry_cutoff"] == 100.0

    def test_pct_tradable_before_cutoff_none_qualify(self):
        # first_trad_sr=50 < entry_cutoff=90 → none qualify
        recs = self._make_records(first_trad_sr=50, entry_cutoff=90)
        r = aggregate(recs)
        assert r["pct_tradable_before_entry_cutoff"] == 0.0

    def test_tok_window_distribution(self):
        # first_tok_sr=200 → sso=100 → ACTIVE_INVENTORY_TRADING
        recs = self._make_records(first_tok_sr=200)
        r = aggregate(recs)
        assert r["tok_window_distribution"].get("ACTIVE_INVENTORY_TRADING", 0) > 0

    def test_tok_window_opening_scan_counted(self):
        # first_tok_sr=295 → sso=5 → OPENING_SCAN
        recs = self._make_records(first_tok_sr=295)
        r = aggregate(recs)
        assert r["tok_window_distribution"].get("OPENING_SCAN", 0) > 0

    def test_epochs_token_never_reached_when_missing(self):
        # first_tok_sr=0 → has_token_ready=False
        recs = self._make_records(first_tok_sr=0)
        r = aggregate(recs)
        assert r["epochs_token_never_reached_count"] == r["total_epochs"]
        assert r["epochs_token_never_reached_pct"] == 100.0

    def test_cycle_gap_correlation_with_data(self):
        recs = self._make_records()
        gaps = [11.5, 12.0, 11.3, 277.0, 302.0]
        r = aggregate(recs, gaps)
        cg = r["cycle_gap_correlation"]
        assert cg["available"] is True
        assert cg["cycle_gap_stats"]["n"] == 5
        assert cg["bimodal_short_n"] == 3
        assert cg["bimodal_long_n"] == 2

    def test_cycle_gap_correlation_no_data(self):
        recs = self._make_records()
        r = aggregate(recs, [])
        assert r["cycle_gap_correlation"]["available"] is False

    def test_preload_correlation_keys_present(self):
        recs = self._make_records()
        r = aggregate(recs)
        pc = r["preload_tradable_delay_correlation"]
        assert "preload_cache_hit_p50" in pc
        assert "preload_cache_miss_p50" in pc
        assert "cache_hit_n" in pc

    def test_stats_fields_present(self):
        recs = self._make_records()
        r = aggregate(recs)
        s = r["first_token_ready_sso_stats"]
        assert set(s.keys()) == {"n", "min", "p25", "p50", "p75", "p90", "max", "mean"}

    def test_guardrail_always_present(self):
        r = aggregate([])
        assert "offline" in r["guardrail"].lower()
        r2 = aggregate(self._make_records())
        assert "offline" in r2["guardrail"].lower()


# ---------------------------------------------------------------------------
# extract_cycle_gaps
# ---------------------------------------------------------------------------

class TestExtractCycleGaps:
    def test_extracts_from_decision_cycle_interval(self):
        events = [_research_event(11.5), _research_event(12.0)]
        gaps = extract_cycle_gaps(events)
        assert len(gaps) == 2
        assert 11.5 in gaps

    def test_fallback_to_effective_outer_loop(self):
        e = _event({"effective_outer_loop_interval_seconds": 14.2})
        gaps = extract_cycle_gaps([e])
        assert 14.2 in gaps

    def test_zero_interval_excluded(self):
        e = _event({"decision_cycle_interval_seconds": 0})
        gaps = extract_cycle_gaps([e])
        assert gaps == []

    def test_missing_fields_skipped_gracefully(self):
        e = _event({"asset": "BTC"})
        gaps = extract_cycle_gaps([e])
        assert gaps == []

    def test_empty_events_returns_empty(self):
        assert extract_cycle_gaps([]) == []

    def test_negative_excluded(self):
        e = _event({"decision_cycle_interval_seconds": -5.0})
        gaps = extract_cycle_gaps([e])
        assert gaps == []


# ---------------------------------------------------------------------------
# load_snapshot_events — file-not-found fail-soft
# ---------------------------------------------------------------------------

class TestLoadSnapshotEvents:
    def test_missing_file_returns_empty(self, tmp_path):
        result = load_snapshot_events("2099-01-01", quant_data_dir=tmp_path)
        assert result == []

    def test_empty_directory_returns_empty(self, tmp_path):
        (tmp_path / "market_snapshots").mkdir()
        result = load_snapshot_events("2099-01-01", quant_data_dir=tmp_path)
        assert result == []

    def test_malformed_jsonl_skipped(self, tmp_path):
        d = tmp_path / "market_snapshots"
        d.mkdir()
        f = d / "2026-01-01.jsonl"
        f.write_text('{"payload": {"asset": "BTC", "epoch_start_ts": 1778810700}}\nBAD_LINE\n')
        result = load_snapshot_events("2026-01-01", quant_data_dir=tmp_path)
        assert len(result) == 1

    def test_asset_filter(self, tmp_path):
        d = tmp_path / "market_snapshots"
        d.mkdir()
        f = d / "2026-01-01.jsonl"
        lines = [
            json.dumps({"payload": {"asset": "BTC", "epoch_start_ts": _REAL_EPOCH}}),
            json.dumps({"payload": {"asset": "ETH", "epoch_start_ts": _REAL_EPOCH}}),
        ]
        f.write_text("\n".join(lines))
        result = load_snapshot_events("2026-01-01", quant_data_dir=tmp_path, asset_filter="BTC")
        assert len(result) == 1
        assert result[0]["payload"]["asset"] == "BTC"

    def test_run_id_filter(self, tmp_path):
        d = tmp_path / "market_snapshots"
        d.mkdir()
        f = d / "2026-01-01.jsonl"
        lines = [
            json.dumps({"run_id": "r1", "payload": {"asset": "BTC", "epoch_start_ts": _REAL_EPOCH}}),
            json.dumps({"run_id": "r2", "payload": {"asset": "BTC", "epoch_start_ts": _REAL_EPOCH + 300}}),
        ]
        f.write_text("\n".join(lines))
        result = load_snapshot_events("2026-01-01", quant_data_dir=tmp_path, run_id="r1")
        assert len(result) == 1
        assert result[0]["run_id"] == "r1"


# ---------------------------------------------------------------------------
# render_console — no crash contract
# ---------------------------------------------------------------------------

class TestRenderConsole:
    def test_empty_stats_no_crash(self, capsys):
        render_console({"total_epochs": 0, "guardrail": "test"}, "2026-05-15")
        captured = capsys.readouterr()
        assert "No epoch records" in captured.out

    def test_normal_stats_no_crash(self, capsys):
        recs = [
            extract_epoch_record([_snap(asset="BTC")]),
            extract_epoch_record([_snap(asset="ETH")]),
        ]
        stats = aggregate(recs, [11.5, 12.0])
        render_console(stats, "2026-05-15")
        captured = capsys.readouterr()
        assert "Epoch Boundary Alignment Probe" in captured.out
        assert "BTC" in captured.out or "ETH" in captured.out

    def test_all_unknown_milestones_no_crash(self, capsys):
        # All milestone fields zero → everything UNKNOWN
        recs = [extract_epoch_record([_snap(
            first_disc_sr=0, first_tok_sr=0, first_ob_sr=0, first_trad_sr=0
        )])]
        stats = aggregate(recs)
        render_console(stats, "2026-05-15")
        captured = capsys.readouterr()
        assert "Epoch Boundary Alignment Probe" in captured.out


# ---------------------------------------------------------------------------
# write_report
# ---------------------------------------------------------------------------

class TestWriteReport:
    def test_writes_json_file(self, tmp_path):
        recs = [extract_epoch_record([_snap()])]
        stats = aggregate(recs)
        out = write_report(stats, "2026-05-15", report_dir=tmp_path)
        assert out.exists()
        content = json.loads(out.read_text())
        assert content["date"] == "2026-05-15"
        assert content["source"] == "epoch_boundary_alignment_probe_v1"
        assert "guardrail" in content

    def test_creates_report_dir(self, tmp_path):
        recs = [extract_epoch_record([_snap()])]
        stats = aggregate(recs)
        report_dir = tmp_path / "sub" / "reports"
        write_report(stats, "2026-05-15", report_dir=report_dir)
        assert report_dir.exists()

    def test_asset_filter_in_filename(self, tmp_path):
        recs = [extract_epoch_record([_snap()])]
        stats = aggregate(recs)
        out = write_report(stats, "2026-05-15", report_dir=tmp_path, asset_filter="BTC")
        assert "BTC" in out.name

    def test_generated_at_present(self, tmp_path):
        recs = [extract_epoch_record([_snap()])]
        stats = aggregate(recs)
        out = write_report(stats, "2026-05-15", report_dir=tmp_path)
        content = json.loads(out.read_text())
        assert "generated_at" in content


# ---------------------------------------------------------------------------
# No runtime imports guard
# ---------------------------------------------------------------------------

class TestNoRuntimeImports:
    def test_no_polymarket_import(self):
        import tools.epoch_boundary_alignment_probe as m
        src = Path(m.__file__).read_text()
        assert "from polymarket" not in src
        assert "import polymarket" not in src

    def test_no_config_settings_import(self):
        import tools.epoch_boundary_alignment_probe as m
        src = Path(m.__file__).read_text()
        assert "from config" not in src
        assert "import config" not in src

    def test_no_utils_risk_manager_import(self):
        import tools.epoch_boundary_alignment_probe as m
        src = Path(m.__file__).read_text()
        assert "risk_manager" not in src

    def test_no_live_execution_import(self):
        import tools.epoch_boundary_alignment_probe as m
        src = Path(m.__file__).read_text()
        assert "order_manager" not in src
        assert "order_intent" not in src


# ---------------------------------------------------------------------------
# Seconds_since_open <-> classify_window integration
# ---------------------------------------------------------------------------

class TestSecondsSinceOpenAndWindowIntegration:
    @pytest.mark.parametrize("sr,expected_window", [
        (295, "OPENING_SCAN"),              # sso=5
        (266, "OPENING_SCAN"),              # sso=34 — last second of OPENING_SCAN
        (265, "ACTIVE_INVENTORY_TRADING"),  # sso=35 — first second of ACTIVE (lo inclusive)
        (264, "ACTIVE_INVENTORY_TRADING"),  # sso=36
        (61,  "ACTIVE_INVENTORY_TRADING"),  # sso=239
        (60,  "PROFIT_MANAGEMENT"),      # sso=240
        (31,  "PROFIT_MANAGEMENT"),      # sso=269
        (30,  "FINAL_DERISK"),           # sso=270
        (1,   "FINAL_DERISK"),           # sso=299
    ])
    def test_sr_to_window(self, sr: int, expected_window: str):
        sso = seconds_since_open(sr)
        assert classify_window(sso) == expected_window

    def test_zero_sr_gives_none_sso(self):
        assert seconds_since_open(0) is None
        assert classify_window(None) == "UNKNOWN"

    def test_boundary_opening_scan_active(self):
        # sso=35 is first second of ACTIVE_INVENTORY_TRADING (lo=35)
        assert classify_window(35) == "ACTIVE_INVENTORY_TRADING"
        # sso=34 is last of OPENING_SCAN (hi=35, exclusive)
        assert classify_window(34) == "OPENING_SCAN"
