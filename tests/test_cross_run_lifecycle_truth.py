import json
from pathlib import Path

from tools.shadow.cross_run_lifecycle_truth import (
    build_cross_run_lifecycle_truth,
    main,
    write_cross_run_lifecycle_truth,
)


DATE = "2026-05-08"
NEXT_DATE = "2026-05-09"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _truth_payload(
    *,
    date: str,
    run_id: str,
    confidence: str = "LOW_PROXY",
    quality: str = "PROXY_HEAVY_TRUTH_TABLES",
    direct_rate: float = 0.10,
    proxy_rate: float = 0.20,
    candidate_events: int = 5,
    asset: str = "BTC",
    no_probability_model_output: int = 3,
    no_orderbook: int = 0,
    time_unsafe: int = 2,
) -> dict:
    return {
        "date_from": date,
        "date_to": date,
        "run_id": run_id,
        "time_filter": {
            "applied": True,
            "since": "01:00",
            "until": "01:05",
            "since_utc": f"{date}T01:00:00Z",
            "until_utc": f"{date}T01:05:00Z",
            "run_id": run_id,
        },
        "scope": "offline_research_replay_only",
        "does_not_claim_profitability": True,
        "does_not_authorize_runtime_decisions": True,
        "events_loaded": 20,
        "candidate_events": candidate_events,
        "replay_truth_confidence": confidence,
        "replay_truth_quality": quality,
        "direct_field_rate": direct_rate,
        "proxy_field_rate": proxy_rate,
        "candidate_classification_version": "truth_table_candidate_classification_v1",
        "excluded_telemetry_counts": {
            "excluded_total": 3,
            "excluded_legacy_candidate_like_events": 2,
            "by_category": {"execution_log": 2, "risk_log": 1},
            "by_reason": {"excluded_telemetry_without_lifecycle_ownership": 3},
        },
        "unknown_lifecycle_precision_metrics": {
            "legacy_candidate_like_events": candidate_events + 2,
            "refined_candidate_events": candidate_events,
            "legacy_unknown_lifecycle_events": 2,
            "refined_unknown_lifecycle_events": 0,
            "unknown_lifecycle_events_removed_by_filter": 2,
            "legacy_unknown_lifecycle_rate": 0.2,
            "refined_unknown_lifecycle_rate": 0.0,
            "unknown_inflation_removed_rate": 1.0,
        },
        "evidence_completeness": {
            "coverage_gaps": ["mfe_mae_support"],
            "candidate_classification_reasons": {"direct_candidate_identity": candidate_events},
            "candidate_classification_confidence": {"high": candidate_events},
        },
        "tables": {
            "starter_candidates": [{"candidate_id": f"{run_id}-starter", "asset": asset}],
            "missed_starter_candidates": [{"candidate_id": f"{run_id}-missed", "asset": asset}],
            "candidate_blocked_before_ev": [{"candidate_id": f"{run_id}-before", "asset": asset}],
            "candidate_blocked_after_ev": [{"candidate_id": f"{run_id}-after", "asset": asset}],
            "time_unsafe_candidates": [{"candidate_id": f"{run_id}-time", "asset": asset}] if time_unsafe else [],
            "liquidity_or_orderbook_blocked_candidates": [{"candidate_id": f"{run_id}-liq", "asset": asset}] if no_orderbook else [],
            "lifecycle_phase_distribution": {
                "counts": {
                    "OPENING_SCAN": 4 if asset == "BTC" else 1,
                    "ACTIVE_INVENTORY_TRADING": 1 if asset == "BTC" else 4,
                },
            },
            "ev_null_reason_distribution": {
                "counts": {
                    "no_probability_model_output": no_probability_model_output,
                    "time_unsafe": time_unsafe,
                    "no_orderbook": no_orderbook,
                },
            },
        },
        "research_questions": {
            "are_btc_and_eth_failing_differently": {
                "asset_failure_counts": {
                    asset: {
                        "blocked_before_ev": 1,
                        "blocked_after_ev": 1,
                        "time_unsafe": 1 if time_unsafe else 0,
                        "liquidity_or_orderbook": 1 if no_orderbook else 0,
                    }
                }
            }
        },
    }


def _write_report_set(report_dir: Path, memory_index_dir: Path) -> None:
    _write_json(
        report_dir / f"lifecycle_truth_tables_{DATE}_0100_to_0105_run_run-alpha.json",
        _truth_payload(date=DATE, run_id="run-alpha", asset="BTC"),
    )
    _write_json(
        report_dir / f"lifecycle_truth_tables_{NEXT_DATE}_0100_to_0105_run_run-beta.json",
        _truth_payload(
            date=NEXT_DATE,
            run_id="run-beta",
            confidence="MEDIUM_DIRECT",
            quality="PARTIAL_DIRECT_TRUTH_TABLES",
            direct_rate=0.26,
            proxy_rate=0.12,
            candidate_events=7,
            asset="ETH",
            no_probability_model_output=1,
            no_orderbook=4,
            time_unsafe=1,
        ),
    )
    _write_json(
        report_dir / f"replay_report_{DATE}_0100_to_0105_run_run-alpha.json",
        {
            "date_from": DATE,
            "date_to": DATE,
            "run_id": "run-alpha",
            "events_loaded": 10,
            "top_skip_reasons": [["time_unsafe", 2], ["ev_below_threshold", 1]],
            "phase2_coverage": {"status": "PARTIAL_PHASE2_COVERAGE"},
        },
    )
    _write_json(
        report_dir / f"replay_report_{NEXT_DATE}_0100_to_0105_run_run-beta.json",
        {
            "date_from": NEXT_DATE,
            "date_to": NEXT_DATE,
            "run_id": "run-beta",
            "events_loaded": 12,
            "top_skip_reasons": [["orderbook_unavailable", 4], ["warmup_pending", 1]],
            "phase2_coverage": {"status": "READY_FOR_PHASE2_REPLAY_RESEARCH"},
        },
    )
    memory_index_dir.mkdir(parents=True, exist_ok=True)
    (memory_index_dir / f"{DATE}_run_comparison.md").write_text(
        "# Same-Day Run Comparison Index\n\n## Recurring Root-Cause Hypothesis\n- hypothesis: repeated_timing_liquidity_or_orderbook_bottleneck\n",
        encoding="utf-8",
    )
    (memory_index_dir / f"{NEXT_DATE}.md").write_text(
        "# Daily Research Memory Index\n\n## Lifecycle Truth Table Trend\n- hypothesis: repeated_ev_null_reason:no_orderbook\n",
        encoding="utf-8",
    )


def test_build_cross_run_lifecycle_truth_summarizes_drift(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    memory_index_dir = tmp_path / "memory" / "index"
    _write_report_set(report_dir, memory_index_dir)

    report = build_cross_run_lifecycle_truth(
        report_dir=report_dir,
        memory_index_dir=memory_index_dir,
        date_from=DATE,
        date_to=NEXT_DATE,
    )

    assert report["scope"] == "offline_research_replay_only"
    assert report["does_not_claim_profitability"] is True
    assert report["does_not_authorize_runtime_decisions"] is True
    assert report["does_not_implement_inventory_execution"] is True
    assert report["source_inputs"]["counts"]["lifecycle_truth_tables"] == 2
    assert report["source_inputs"]["counts"]["replay_reports"] == 2
    assert report["source_inputs"]["counts"]["research_memory_indexes"] == 2
    assert report["aggregate"]["runs_analyzed"] == 2
    assert report["aggregate"]["candidate_events"] == 12
    assert report["aggregate"]["repeated_candidate_loss_patterns"]["candidate_blocked_before_ev"] == 2
    assert report["aggregate"]["repeated_ev_null_reasons"]["no_probability_model_output"] == 4
    assert report["aggregate"]["repeated_ev_null_reasons"]["no_orderbook"] == 4
    assert report["aggregate"]["repeated_lifecycle_phase_failures"]["OPENING_SCAN"] == 5
    assert report["aggregate"]["repeated_timing_cutoff_failures"] > 0
    assert report["aggregate"]["repeated_liquidity_orderbook_failures"] > 0
    assert report["aggregate"]["direct_vs_proxy_evidence_trend"]["direct_field_rate_trend"] == "increasing"
    assert report["aggregate"]["direct_vs_proxy_evidence_trend"]["proxy_field_rate_trend"] == "decreasing"
    assert report["aggregate"]["candidate_classification_trend"]["excluded_telemetry_total"] == 6
    assert report["aggregate"]["candidate_classification_trend"]["excluded_legacy_candidate_like_events"] == 4
    assert report["aggregate"]["candidate_classification_trend"]["excluded_telemetry_by_category"]["execution_log"] == 4
    assert report["aggregate"]["unknown_lifecycle_precision_metrics"]["unknown_lifecycle_events_removed_by_filter"] == 4
    assert report["aggregate"]["unknown_lifecycle_precision_metrics"]["refined_unknown_lifecycle_events"] == 0
    assert len(report["aggregate"]["run_to_run_drift"]) == 1
    assert report["aggregate"]["btc_vs_eth_candidate_loss_differences"]["BTC"]["blocked_before_ev"] == 1
    assert report["aggregate"]["btc_vs_eth_candidate_loss_differences"]["ETH"]["liquidity_or_orderbook"] == 1
    assert report["recurring_root_causes"]
    assert report["repeated_failure_confidence"] in {
        "LOW_REPEATED_PROXY_HEAVY_EVIDENCE",
        "MEDIUM_REPEATED_EVIDENCE",
        "MEDIUM_REPEATED_DIRECT_EVIDENCE",
    }
    assert report["replay_truth_maturity"] == "PARTIAL_DIRECT_TRUTH"
    assert report["direct_field_maturity"] == "LOW_DIRECT_FIELD_COVERAGE"
    assert report["lifecycle_phase_failure_ranking"]["OPENING_SCAN"] == 5
    assert report["replay_report_evidence"]["top_skip_reasons"]["orderbook_unavailable"] == 4
    assert report["research_memory_index_evidence"]["reported_hypotheses"]["repeated_ev_null_reason:no_orderbook"] == 1
    assert report["research_questions"]["is_opening_scan_still_dominant"]["answer"] is True
    assert report["research_questions"]["is_replay_truth_improving_across_runs"]["answer"] == "improving"
    assert report["research_questions"]["how_much_unknown_inflation_comes_from_telemetry_pollution"]["answer"] == "evidence_present"
    assert report["research_questions"]["are_pre_ev_blocks_still_dominant_after_cleanup"]["answer"] is True


def test_write_cross_run_lifecycle_truth_uses_date_range_and_run_filter(tmp_path: Path) -> None:
    report = {
        "date_from": DATE,
        "date_to": NEXT_DATE,
        "run_id_filter": "run/id",
    }

    path = write_cross_run_lifecycle_truth(report, report_dir=tmp_path / "reports")

    assert path.name == f"cross_run_lifecycle_truth_{DATE}_to_{NEXT_DATE}_run_run_id.json"
    assert json.loads(path.read_text(encoding="utf-8"))["run_id_filter"] == "run/id"


def test_cross_run_lifecycle_truth_cli_writes_report(tmp_path: Path, capsys) -> None:
    report_dir = tmp_path / "reports"
    memory_index_dir = tmp_path / "memory" / "index"
    _write_report_set(report_dir, memory_index_dir)

    assert main([
        "--from",
        DATE,
        "--to",
        NEXT_DATE,
        "--report-dir",
        str(report_dir),
        "--memory-index-dir",
        str(memory_index_dir),
    ]) == 0

    output = capsys.readouterr().out
    assert "Cross-Run Lifecycle Truth Analysis" in output
    assert "truth_reports=2" in output
    assert (report_dir / f"cross_run_lifecycle_truth_{DATE}_to_{NEXT_DATE}.json").exists()
