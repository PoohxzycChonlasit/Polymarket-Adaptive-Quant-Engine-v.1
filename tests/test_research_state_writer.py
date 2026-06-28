import json
from pathlib import Path

from tools.research.research_state_writer import (
    COMPACT_SIZE_TARGET_BYTES,
    build_research_state,
    main,
    render_research_state_markdown,
    write_research_state,
)


DATE = "2026-05-11"
RUN_ID = "run-compact"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_sources(report_dir: Path, memory_dir: Path) -> None:
    time_filter = {
        "applied": True,
        "since": "04:21",
        "until": "04:23",
        "since_utc": f"{DATE}T04:21:00Z",
        "until_utc": f"{DATE}T04:23:00Z",
        "run_id": RUN_ID,
    }
    _write_json(
        report_dir / f"replay_report_{DATE}_0421_to_0423_run_{RUN_ID}.json",
        {
            "date_from": DATE,
            "date_to": DATE,
            "run_id": RUN_ID,
            "time_filter": time_filter,
            "events_loaded": 17,
            "lifecycle_replay_confidence": "MEDIUM_PROXY",
            "top_skip_reasons": [["ev_below_threshold", 2]],
            "phase2_coverage": {
                "status": "PARTIAL_PHASE2_COVERAGE",
                "coverage_gaps": ["mfe_mae_support"],
            },
            "partial_lifecycle_replay": {
                "replay_unsupported_sections": [
                    {"section": "reload_unload_truth", "status": "coverage_gap"},
                ]
            },
        },
    )
    _write_json(
        report_dir / f"lifecycle_truth_tables_{DATE}_0421_to_0423_run_{RUN_ID}.json",
        {
            "date_from": DATE,
            "date_to": DATE,
            "run_id": RUN_ID,
            "events_loaded": 17,
            "candidate_events": 3,
            "replay_truth_confidence": "MEDIUM_DIRECT",
            "replay_truth_quality": "PARTIAL_DIRECT_TRUTH_TABLES",
            "direct_field_rate": 0.6176,
            "proxy_field_rate": 0.5,
            "unknown_lifecycle_precision_metrics": {
                "refined_unknown_lifecycle_rate": 0.0,
            },
            "evidence_completeness": {
                "coverage_gaps": ["mfe_mae_support"],
            },
            "tables": {
                "missed_starter_candidates": [],
                "candidate_blocked_before_ev": [{"candidate_id": "candidate-before"}],
                "candidate_blocked_after_ev": [],
                "time_unsafe_candidates": [],
                "liquidity_or_orderbook_blocked_candidates": [],
                "lifecycle_phase_distribution": {
                    "counts": {"ACTIVE_INVENTORY_TRADING": 3},
                },
                "ev_null_reason_distribution": {
                    "counts": {"no_probability_model_output": 3},
                },
            },
        },
    )
    _write_json(
        report_dir / f"cross_run_lifecycle_truth_{DATE}.json",
        {
            "date_from": DATE,
            "date_to": DATE,
            "replay_truth_maturity": "PARTIAL_DIRECT_TRUTH",
            "direct_field_maturity": "LOW_DIRECT_FIELD_COVERAGE",
            "lifecycle_phase_failure_ranking": {"ACTIVE_INVENTORY_TRADING": 3},
            "aggregate": {
                "repeated_candidate_loss_patterns": {"candidate_blocked_before_ev": 1},
                "repeated_ev_null_reasons": {"no_probability_model_output": 3},
                "direct_vs_proxy_evidence_trend": {
                    "direct_field_rate_avg": 0.1,
                    "proxy_field_rate_avg": 0.2,
                },
            },
        },
    )
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / f"{DATE}_run_{RUN_ID}.md").write_text(
        "# Daily Index\n\n- coverage gap: mfe_mae_support\n- recommended next investigation: MFE path evidence\n",
        encoding="utf-8",
    )


def test_research_state_writer_builds_compact_outputs(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    memory_dir = tmp_path / "memory" / "index"
    output_dir = tmp_path / "research_state"
    _write_sources(report_dir, memory_dir)

    state = build_research_state(
        report_dir=report_dir,
        memory_index_dir=memory_dir,
        date=DATE,
        run_id=RUN_ID,
    )
    paths = write_research_state(state, output_dir=output_dir)

    assert state["truth_state"]["latest_run_id"] == RUN_ID
    assert state["truth_state"]["replay_truth_maturity"] == "PARTIAL_DIRECT_TRUTH"
    assert state["truth_state"]["direct_field_rate"] == 0.6176
    assert state["truth_state"]["unknown_lifecycle_rate"] == 0.0
    assert state["truth_state"]["top_candidate_loss_reasons"]["candidate_blocked_before_ev"] == 1
    assert state["truth_state"]["top_ev_null_reasons"]["no_probability_model_output"] == 3
    assert "mfe_mae_support" in state["truth_state"]["current_blind_spots"]
    markdown = render_research_state_markdown(state).lower()
    assert "jsonl" not in markdown
    assert "orderbook dump" not in markdown

    for path in paths.values():
        assert path.exists()
        assert path.stat().st_size < COMPACT_SIZE_TARGET_BYTES


def test_research_state_writer_cli(tmp_path: Path, capsys) -> None:
    report_dir = tmp_path / "reports"
    memory_dir = tmp_path / "memory" / "index"
    output_dir = tmp_path / "research_state"
    _write_sources(report_dir, memory_dir)

    assert main([
        "--date",
        DATE,
        "--run-id",
        RUN_ID,
        "--report-dir",
        str(report_dir),
        "--memory-index-dir",
        str(memory_dir),
        "--output-dir",
        str(output_dir),
    ]) == 0

    output = capsys.readouterr().out
    assert "Research State Writer" in output
    assert (output_dir / "latest_runtime_state.json").exists()
    assert (output_dir / "latest_truth_state.json").exists()
    assert (output_dir / "latest_research_state.md").exists()
