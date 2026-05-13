from __future__ import annotations

import json
from pathlib import Path

from tools.research_memory_writer import NOTE_FOLDERS, RESEARCH_MEMORY_FOLDERS, main, write_research_memory


DATE = "2026-05-08"
NEXT_DATE = "2026-05-09"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _phase2_payload() -> dict:
    return {
        "status": "PARTIAL_PHASE2_COVERAGE",
        "coverage_gap_count": 1,
        "coverage_gaps": ["mfe_mae_support"],
        "proxy_inferred_items": ["fair_value_ev_decay"],
        "ev_null_reason_coverage": {
            "status": "available",
            "events_checked": 4,
            "null_reason_coverage_rate": 1.0,
            "null_reasons": [["no_orderbook", 3], ["time_unsafe", 1]],
            "probability_model_stages": [["pre_model_skip", 4]],
            "ev_calculation_stages": [["pre_model_skip", 4]],
        },
        "requirements": {
            "lifecycle_phase_evidence": {
                "status": "available",
                "inference": "direct_observed",
            },
            "fair_value_ev_decay": {
                "status": "proxy_inferred",
                "inference": "proxy_inferred",
            },
            "mfe_mae_support": {
                "status": "coverage_gap",
                "inference": "missing",
            },
        },
    }


def _partial_replay_payload() -> dict:
    return {
        "status": "PARTIAL_PROXY_REPLAY",
        "lifecycle_replay_confidence": "LOW_PROXY",
        "replay_supported_sections": [{"section": "timing_decay"}],
        "replay_unsupported_sections": [{"section": "mfe_mae_support", "status": "coverage_gap"}],
        "missed_starter_candidates": [
            {
                "candidate_key": "candidate-1",
                "market_key": "pm-5m-btc",
                "seconds_remaining": 180,
                "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                "skip_reason": "ev_below_threshold",
                "starter_replay_inference": "proxy_inferred",
            }
        ],
        "timing_decay_summary": {
            "status": "proxy_inferred",
            "first_seen_seconds_remaining": 250,
            "first_evaluable_seconds_remaining": 220,
            "avg_seconds_remaining": 180,
            "min_seconds_remaining": 80,
        },
        "spread_liquidity_readiness_summary": {
            "status": "proxy_inferred",
            "spread_events": 4,
            "spread_normalized_events": 2,
            "spread_normalization_rate": 0.5,
            "liquidity_states": [["HEALTHY", 3], ["EMPTY", 1]],
            "orderbook_readiness_reasons": [["empty_book", 1]],
        },
    }


def _lifecycle_truth_payload(*, run_id: str | None = None, candidate_events: int = 7) -> dict:
    return {
        "date_from": DATE,
        "date_to": DATE,
        "run_id": run_id or "",
        "scope": "offline_research_replay_only",
        "does_not_claim_profitability": True,
        "does_not_authorize_runtime_decisions": True,
        "events_loaded": 28,
        "candidate_events": candidate_events,
        "replay_truth_confidence": "LOW_PROXY",
        "replay_truth_quality": "PROXY_HEAVY_TRUTH_TABLES",
        "direct_field_rate": 0.1185,
        "proxy_field_rate": 0.1731,
        "evidence_completeness": {
            "coverage_gaps": ["mfe_mae_support"],
        },
        "tables": {
            "starter_candidates": [],
            "missed_starter_candidates": [{"candidate_id": "candidate-1"}],
            "candidate_blocked_before_ev": [{"candidate_id": "candidate-before"}],
            "candidate_blocked_after_ev": [{"candidate_id": "candidate-after"}],
            "time_unsafe_candidates": [{"candidate_id": "candidate-time"}],
            "liquidity_or_orderbook_blocked_candidates": [{"candidate_id": "candidate-liq"}],
            "lifecycle_phase_distribution": {
                "counts": {
                    "OPENING_SCAN": 2,
                    "ACTIVE_INVENTORY_TRADING": 3,
                    "PROFIT_MANAGEMENT": 2,
                },
            },
            "ev_null_reason_distribution": {
                "counts": {
                    "no_probability_model_output": 5,
                    "time_unsafe": 2,
                },
            },
        },
    }


def _write_synthetic_reports_for_date(
    report_dir: Path,
    *,
    date: str,
    since: str = "01:00",
    until: str = "01:05",
    primary_bottleneck: str = "strategy_thresholds",
    secondary_bottleneck: str = "market_readiness",
    root_cause: str = "strategy",
    top_skip_reasons: list[list] | None = None,
    null_reasons: list[list] | None = None,
    run_id: str | None = None,
    include_lifecycle_truth: bool = False,
    lifecycle_candidate_events: int = 7,
) -> None:
    since_slug = since.replace(":", "")
    until_slug = until.replace(":", "")
    top_skip_reasons = top_skip_reasons or [["ev_below_threshold", 2], ["time_unsafe", 1]]
    phase2 = _phase2_payload()
    if null_reasons is not None:
        phase2["ev_null_reason_coverage"]["null_reasons"] = null_reasons
    time_filter = {
        "applied": True,
        "since": since,
        "until": until,
        "since_utc": f"{date}T{since}:00Z",
        "until_utc": f"{date}T{until}:00Z",
        "run_id": run_id,
        "run_id_applied": bool(run_id),
        "semantics": "half_open_since_inclusive_until_exclusive",
    }
    run_suffix = f"_run_{str(run_id).replace('/', '_')}" if run_id else ""
    _write_json(
        report_dir / f"replay_report_{date}_{since_slug}_to_{until_slug}{run_suffix}.json",
        {
            "date_from": date,
            "date_to": date,
            "run_id": run_id or "",
            "time_filter": time_filter,
            "events_loaded": 9,
            "total_trades": 0,
            "skipped_decisions": 3,
            "top_skip_reasons": top_skip_reasons,
            "phase2_coverage": phase2,
            "partial_lifecycle_replay": _partial_replay_payload(),
            "lifecycle_replay_confidence": "LOW_PROXY",
            "missed_starter_candidates": _partial_replay_payload()["missed_starter_candidates"],
        },
    )
    _write_json(
        report_dir / f"no_entry_report_{date}_{since_slug}_to_{until_slug}{run_suffix}.json",
        {
            "date": date,
            "run_id": run_id or "",
            "time_filter": time_filter,
            "total_scanned": 3,
            "total_skipped": 3,
            "root_cause_category": root_cause,
            "root_cause_counts": {
                "data": 1,
                "strategy": 2,
                "risk": 0,
                "cutoff": 1,
                "execution": 0,
            },
            "top_skip_reasons": top_skip_reasons,
            "phase2_coverage": phase2,
            "partial_lifecycle_replay": _partial_replay_payload(),
            "lifecycle_replay_confidence": "LOW_PROXY",
            "recommendations": ["Review EV distribution offline before changing thresholds."],
        },
    )
    _write_json(
        report_dir / f"session_runtime_evaluation_{date}_{since_slug}_to_{until_slug}{run_suffix}.json",
        {
            "date": date,
            "run_id": run_id or "",
            "time_filter": {
                **time_filter,
                "timezone": "UTC",
                "range": f"{date}T{since}:00Z..{date}T{until}:00Z",
            },
            "session_status": "CAUTION",
            "primary_bottleneck": primary_bottleneck,
            "secondary_bottleneck": secondary_bottleneck,
            "bottleneck_scores": {
                primary_bottleneck: 3,
                secondary_bottleneck: 1,
            },
            "health_summary": {"scanned": 3, "entered": 0, "skipped": 3},
            "phase2_coverage": phase2,
            "partial_lifecycle_replay": _partial_replay_payload(),
            "lifecycle_replay_confidence": "LOW_PROXY",
            "missed_starter_candidates": _partial_replay_payload()["missed_starter_candidates"],
            "candidate_timing": {
                "candidates_seen": 3,
                "pre_cutoff_candidates": 2,
            },
            "recommendations": ["Collect more paper evidence before considering strategy changes."],
        },
    )
    if include_lifecycle_truth:
        truth = _lifecycle_truth_payload(run_id=run_id, candidate_events=lifecycle_candidate_events)
        truth["date_from"] = date
        truth["date_to"] = date
        truth["time_filter"] = time_filter
        _write_json(
            report_dir / f"lifecycle_truth_tables_{date}_{since_slug}_to_{until_slug}{run_suffix}.json",
            truth,
        )


def _write_synthetic_reports(report_dir: Path) -> None:
    _write_synthetic_reports_for_date(report_dir, date=DATE, include_lifecycle_truth=True)


def test_research_memory_writer_creates_topic_markdown_from_synthetic_reports(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    output_dir = tmp_path / "research_memory"
    _write_synthetic_reports(report_dir)

    written = write_research_memory(date=DATE, report_dir=report_dir, output_dir=output_dir)

    assert len(written) == len(NOTE_FOLDERS)
    for folder in NOTE_FOLDERS:
        assert (output_dir / folder / f"{DATE}_0100_to_0105.md").exists()
    assert not (output_dir / "index" / f"{DATE}.md").exists()

    summary = (output_dir / "session_summaries" / f"{DATE}_0100_to_0105.md").read_text(encoding="utf-8")
    assert "source_reports:" in summary
    assert "phase2_status: PARTIAL_PHASE2_COVERAGE" in summary
    assert "fair_value_ev_decay" in summary
    assert "mfe_mae_support" in summary
    assert "candidate-1" in summary
    assert "proxy_inferred" in summary
    assert "no_orderbook: 3" in summary
    assert "does not claim profitability" in summary


def test_research_memory_cli_reports_generated_files(tmp_path: Path, capsys) -> None:
    report_dir = tmp_path / "reports"
    output_dir = tmp_path / "research_memory"
    _write_synthetic_reports(report_dir)

    assert main([
        "--date",
        DATE,
        "--report-dir",
        str(report_dir),
        "--output-dir",
        str(output_dir),
    ]) == 0

    output = capsys.readouterr().out
    assert "Research Memory Writer" in output
    assert "generated_files=7" in output
    assert str(output_dir / "session_summaries" / f"{DATE}_0100_to_0105.md") in output


def test_research_memory_writer_can_create_compact_daily_index(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    output_dir = tmp_path / "research_memory"
    _write_synthetic_reports_for_date(report_dir, date=DATE, include_lifecycle_truth=True)

    written = write_research_memory(
        date=DATE,
        report_dir=report_dir,
        output_dir=output_dir,
        write_index=True,
    )

    index_path = output_dir / "index" / f"{DATE}.md"
    assert len(written) == len(RESEARCH_MEMORY_FOLDERS)
    assert index_path.exists()

    index = index_path.read_text(encoding="utf-8")
    assert f"# Daily Research Memory Index - {DATE}" in index
    assert "run_id: not_filtered" in index
    assert f"replay: `python -m tools.replay_analyzer --date {DATE}`" in index
    assert f"no_entry: `python -m tools.no_entry_analyzer --date {DATE} --write-report`" in index
    assert f"session_eval: `python -m tools.session_runtime_evaluator --date {DATE} --write-report --verbose`" in index
    assert f"memory: `python -m tools.research_memory_writer --date {DATE} --write-index`" in index
    assert "## NotebookLM Ingestion Note" in index
    assert "Upload this index plus the linked topic notes for NotebookLM ingestion." in index
    assert f"## Window {DATE}_0100_to_0105" in index
    assert "source_reports:" in index
    assert f"runtime/reports/replay_report_{DATE}_0100_to_0105.json" not in index
    assert f"reports/replay_report_{DATE}_0100_to_0105.json" in index
    assert "phase2_status: PARTIAL_PHASE2_COVERAGE" in index
    assert "replay_confidence: LOW_PROXY" in index
    assert "evidence_quality: PARTIAL_OR_PROXY_EVIDENCE" in index
    assert "no_orderbook: 3" in index
    assert "primary_bottleneck: strategy_thresholds" in index
    assert "missed_starter_count: 1" in index
    assert "lifecycle_truth_table_summary:" in index
    assert "replay_truth_confidence: LOW_PROXY" in index
    assert "replay_truth_quality: PROXY_HEAVY_TRUTH_TABLES" in index
    assert "truth_label: proxy_heavy_truth" in index
    assert "direct_field_rate: 0.1185" in index
    assert "proxy_field_rate: 0.1731" in index
    assert "candidate_events: 7" in index
    assert "starter_candidates: 0" in index
    assert "missed_starter_candidates: 1" in index
    assert "candidate_blocked_before_ev: 1" in index
    assert "candidate_blocked_after_ev: 1" in index
    assert "time_unsafe_candidates: 1" in index
    assert "liquidity_or_orderbook_blocked_candidates: 1" in index
    assert "ACTIVE_INVENTORY_TRADING: 3" in index
    assert "no_probability_model_output: 5" in index
    assert "proxy_heavy_truth_tables" in index
    assert "fair_value_ev_decay" in index
    assert "mfe_mae_support" in index
    assert "../session_summaries/2026-05-08_0100_to_0105.md" in index
    assert "no profitability, live-readiness, strategy, risk, or execution claims" in index


def test_research_memory_cli_write_index_flag(tmp_path: Path, capsys) -> None:
    report_dir = tmp_path / "reports"
    output_dir = tmp_path / "research_memory"
    _write_synthetic_reports(report_dir)

    assert main([
        "--date",
        DATE,
        "--report-dir",
        str(report_dir),
        "--output-dir",
        str(output_dir),
        "--write-index",
    ]) == 0

    output = capsys.readouterr().out
    assert "generated_files=8" in output
    assert str(output_dir / "index" / f"{DATE}.md") in output


def test_research_memory_writer_filters_reports_by_run_id(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    output_dir = tmp_path / "research_memory"
    _write_synthetic_reports_for_date(report_dir, date=DATE, run_id="run/target", include_lifecycle_truth=True)
    _write_synthetic_reports_for_date(
        report_dir,
        date=DATE,
        since="02:00",
        until="02:05",
        run_id="run-other",
        top_skip_reasons=[["other_run", 4]],
        null_reasons=[["other_null", 4]],
    )

    written = write_research_memory(
        date=DATE,
        report_dir=report_dir,
        output_dir=output_dir,
        write_index=True,
        run_id="run/target",
    )

    assert len(written) == len(RESEARCH_MEMORY_FOLDERS)
    target_summary = output_dir / "session_summaries" / f"{DATE}_0100_to_0105_run_run_target.md"
    other_summary = output_dir / "session_summaries" / f"{DATE}_0200_to_0205_run_run-other.md"
    index_path = output_dir / "index" / f"{DATE}_run_run_target.md"
    assert target_summary.exists()
    assert not other_summary.exists()
    assert index_path.exists()
    index = index_path.read_text(encoding="utf-8")
    assert "run_id: run/target" in index
    assert f"python -m tools.replay_analyzer --date {DATE} --run-id run/target" in index
    assert f"python -m tools.no_entry_analyzer --date {DATE} --run-id run/target --write-report" in index
    assert f"python -m tools.session_runtime_evaluator --date {DATE} --run-id run/target --write-report --verbose" in index
    assert f"python -m tools.research_memory_writer --date {DATE} --run-id run/target --write-index" in index
    assert f"## Window {DATE}_0100_to_0105_run_run_target" in index
    assert "source_reports:" in index
    assert f"reports/replay_report_{DATE}_0100_to_0105_run_run_target.json" in index
    assert f"reports/lifecycle_truth_tables_{DATE}_0100_to_0105_run_run_target.json" in index
    assert "replay_truth_quality: PROXY_HEAVY_TRUTH_TABLES" in index
    assert "other_run" not in index
    assert "other_null" not in index


def test_research_memory_cli_lists_report_run_ids(tmp_path: Path, capsys) -> None:
    report_dir = tmp_path / "reports"
    output_dir = tmp_path / "research_memory"
    _write_synthetic_reports_for_date(report_dir, date=DATE, run_id="run/target")
    _write_synthetic_reports_for_date(report_dir, date=DATE, since="02:00", until="02:05", run_id="run-other")

    assert main([
        "--date",
        DATE,
        "--report-dir",
        str(report_dir),
        "--output-dir",
        str(output_dir),
        "--list-run-ids",
    ]) == 0

    output = capsys.readouterr().out
    assert "Available report run IDs" in output
    assert "run_id=run/target" in output
    assert "run_id=run-other" in output
    assert "categories=no_entry,replay,session_runtime" in output


def test_research_memory_cli_writes_multi_day_index(tmp_path: Path, capsys) -> None:
    report_dir = tmp_path / "reports"
    output_dir = tmp_path / "research_memory"
    _write_synthetic_reports_for_date(report_dir, date=DATE, include_lifecycle_truth=True)
    _write_synthetic_reports_for_date(
        report_dir,
        date=NEXT_DATE,
        since="02:00",
        until="02:05",
        primary_bottleneck="market_readiness",
        secondary_bottleneck="cutoff",
        root_cause="data",
        top_skip_reasons=[["orderbook_unavailable", 2], ["warmup_pending", 1]],
        null_reasons=[["no_orderbook", 2], ["warmup_pending", 1]],
        include_lifecycle_truth=True,
        lifecycle_candidate_events=4,
    )

    assert main([
        "--from",
        DATE,
        "--to",
        NEXT_DATE,
        "--report-dir",
        str(report_dir),
        "--output-dir",
        str(output_dir),
        "--write-index",
    ]) == 0

    index_path = output_dir / "index" / f"{DATE}_to_{NEXT_DATE}.md"
    output = capsys.readouterr().out
    assert "generated_files=1" in output
    assert str(index_path) in output
    index = index_path.read_text(encoding="utf-8")
    assert f"# Multi-Day Research Memory Index - {DATE}_to_{NEXT_DATE}" in index
    assert "run_id: not_filtered" in index
    assert f"memory: `python -m tools.research_memory_writer --from {DATE} --to {NEXT_DATE} --write-index`" in index
    assert "## NotebookLM Ingestion Note" in index
    assert "source_reports:" in index
    assert "dates_included: 2" in index
    assert "windows_included: 2" in index
    assert f"{DATE}_0100_to_0105" in index
    assert f"{NEXT_DATE}_0200_to_0205" in index
    assert "no_orderbook: 5" in index
    assert "time_unsafe: 1" in index
    assert "orderbook_unavailable" in index
    assert "missed_starter_total: 2" in index
    assert "PARTIAL_PHASE2_COVERAGE: 2" in index
    assert "## Lifecycle Truth Table Trend" in index
    assert "truth_reports_included: 2" in index
    assert "candidate_events: 11" in index
    assert "direct_field_rate_avg: 0.1185" in index
    assert "proxy_field_rate_avg: 0.1731" in index
    assert "LOW_PROXY: 2" in index
    assert "PROXY_HEAVY_TRUTH_TABLES: 2" in index
    assert "missed_starter_candidates: 2" in index
    assert "ACTIVE_INVENTORY_TRADING: 6" in index
    assert "no_probability_model_output: 10" in index
    assert "proxy_heavy_truth_tables: 2" in index
    assert "fair_value_ev_decay: 2" in index
    assert "mfe_mae_support: 2" in index
    assert "repeated_timing_liquidity_or_orderbook_bottleneck" in index
    assert "no profitability, live-readiness, strategy, risk, or execution claims" in index


def test_research_memory_cli_writes_same_day_run_comparison_index(tmp_path: Path, capsys) -> None:
    report_dir = tmp_path / "reports"
    output_dir = tmp_path / "research_memory"
    _write_synthetic_reports_for_date(
        report_dir,
        date=DATE,
        run_id="run-alpha",
        primary_bottleneck="cutoff",
        secondary_bottleneck="latency",
        top_skip_reasons=[["time_unsafe", 3], ["ev_below_threshold", 1]],
        null_reasons=[["time_unsafe", 3], ["no_market_price", 1]],
        include_lifecycle_truth=True,
    )
    _write_synthetic_reports_for_date(
        report_dir,
        date=DATE,
        since="02:00",
        until="02:05",
        run_id="run-beta",
        primary_bottleneck="market_readiness",
        secondary_bottleneck="cutoff",
        root_cause="data",
        top_skip_reasons=[["orderbook_unavailable", 4], ["warmup_pending", 2]],
        null_reasons=[["no_orderbook", 4], ["warmup_pending", 2]],
        include_lifecycle_truth=True,
        lifecycle_candidate_events=4,
    )

    assert main([
        "--date",
        DATE,
        "--report-dir",
        str(report_dir),
        "--output-dir",
        str(output_dir),
        "--compare-runs",
        "--write-index",
    ]) == 0

    output = capsys.readouterr().out
    index_path = output_dir / "index" / f"{DATE}_run_comparison.md"
    assert "run_comparison=true generated_files=1" in output
    assert str(index_path) in output

    index = index_path.read_text(encoding="utf-8")
    assert f"# Same-Day Run Comparison Index - {DATE}" in index
    assert "runs_compared: 2" in index
    assert "run_id: run-alpha" in index
    assert "run_id: run-beta" in index
    assert "event_count:" in index
    assert "utc_window:" in index
    assert "PARTIAL_PHASE2_COVERAGE" in index
    assert "time_unsafe=3" in index
    assert "no_orderbook=4" in index
    assert "primary_bottleneck: market_readiness" in index
    assert "missed_starter_count: 1" in index
    assert "direct_observed:" in index
    assert "proxy_inferred:" in index
    assert "coverage_gap:" in index
    assert "lifecycle_truth_table_summary:" in index
    assert "truth_reports_included: 1" in index
    assert "candidate_events: 7" in index
    assert "candidate_events: 4" in index
    assert "direct_field_rate_avg: 0.1185" in index
    assert "proxy_field_rate_avg: 0.1731" in index
    assert "PROXY_HEAVY_TRUTH_TABLES" in index
    assert "no_probability_model_output: 5" in index
    assert "proxy_heavy_truth_tables: 1" in index
    assert "mfe_mae_support" in index
    assert "## EV-Null Reason Drift" in index
    assert "## Timing/Liquidity Bottleneck Drift" in index
    assert "## Recurring Root-Cause Hypothesis" in index
    assert "no profitability, live-readiness, strategy, risk, or execution claims" in index
