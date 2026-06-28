import json
from pathlib import Path

from dashboard.offline_quant_report_dashboard import build_dashboard_payload


RUN_ID = "20260515T143223Z_22760_1b6c0b35"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_dashboard_payload_groups_run_scoped_reports(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    _write_json(
        report_dir / f"quant_data_quality_2026-05-15_run_{RUN_ID}.json",
        {
            "date": "2026-05-15",
            "run_id": RUN_ID,
            "bad_json_lines": 0,
            "replay_continuity": {
                "status": "PASS",
                "trustworthy_for_replay": True,
                "events_checked": 494,
                "run_chain_gap_count": 0,
                "run_id_scope": RUN_ID,
            },
            "timestamp_ordering": {"status": "PASS"},
            "research_log_integrity": {"status": "PASS"},
            "malformed_json_impact": {
                "affects_selected_run": False,
                "matching_run_id_malformed_json_lines": 0,
                "total_malformed_json_lines_in_scanned_files": 2,
                "status": "NO_DIRECT_RUN_ID_MATCH",
            },
            "run_id_summary": {
                "run_ids": [
                    {
                        "run_id": RUN_ID,
                        "last_timestamp_utc": "2026-05-15T14:48:02Z",
                    }
                ]
            },
        },
    )
    _write_json(
        report_dir / f"no_entry_report_2026-05-15_run_{RUN_ID}.json",
        {
            "date": "2026-05-15",
            "run_id": RUN_ID,
            "root_cause_category": "cutoff",
            "root_cause_counts": {"cutoff": 23, "risk": 9, "execution": 0},
            "count_time_unsafe": 23,
            "count_risk_plan_zero": 9,
            "execution_stage_attempt_count": 0,
            "order_submit_attempt_count": 0,
            "execution_failure_count": 0,
            "phase2_coverage": {
                "ev_null_reason_coverage": {
                    "does_not_claim_ev_available": True,
                    "fields": {
                        "ev_after_spread": {
                            "value_events": 9,
                            "null_events": 160,
                            "null_reason_coverage_rate": 1.0,
                            "null_reasons": [["no_probability_model_output", 131]],
                        }
                    },
                }
            },
            "spread_liquidity_readiness_summary": {
                "status": "proxy_inferred",
                "liquidity_states": [["HEALTHY", 169]],
                "spread_normalization_rate": 0.9349,
            },
        },
    )
    _write_json(
        report_dir / f"session_runtime_evaluation_2026-05-15_run_{RUN_ID}.json",
        {
            "date": "2026-05-15",
            "run_id": RUN_ID,
            "primary_bottleneck": "cutoff",
            "secondary_bottleneck": "risk_plan_zero",
            "execution_summary": {
                "execution_events_loaded": 107,
                "order_submit_attempt_count": 0,
                "execution_failure_count": 0,
                "paper_fill_count": 0,
            },
            "market_readiness": {
                "empty_book_count": 0,
                "stale_book_count": 0,
                "orderbook_ready_count": 128,
            },
            "orderbook_readiness": {"orderbook_unavailable_count": 0},
        },
    )
    _write_json(
        report_dir / "no_entry_root_cause_2026-05-15.json",
        {
            "date": "2026-05-15",
            "run_id_filter": RUN_ID,
            "lifecycle_phase_distribution": {
                "FINAL_DERISK": 16,
                "ACTIVE_INVENTORY_TRADING": 16,
                "PROFIT_MANAGEMENT": 6,
            },
        },
    )

    payload = build_dashboard_payload(report_dir)

    assert payload["latest_run_id"] == RUN_ID
    assert payload["record_count"] == 1
    record = payload["latest_record"]
    assert record["continuity"]["status"] == "PASS"
    assert record["root_cause"]["primary"] == "cutoff"
    assert record["root_cause"]["execution_stage_attempts"] == 0
    assert record["time_unsafe_count"] == 23
    assert record["risk_plan_zero_count"] == 9
    assert record["lifecycle_distribution"]["FINAL_DERISK"] == 16
    assert record["liquidity_orderbook"]["status"] == "READY"
    assert record["bad_json"]["affects_selected_run"] is False


def test_dashboard_keeps_unscoped_probe_separate_from_latest_run(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    _write_json(
        report_dir / f"quant_data_quality_2026-05-15_run_{RUN_ID}.json",
        {
            "date": "2026-05-15",
            "run_id": RUN_ID,
            "replay_continuity": {"status": "PASS", "run_id_scope": RUN_ID},
            "timestamp_ordering": {"status": "PASS"},
        },
    )
    _write_json(
        report_dir / "market_readiness_admission_probe_2026-05-15.json",
        {
            "date": "2026-05-15",
            "run_id_filter": None,
            "lifecycle_phase_probe_distribution": {"FINAL_DERISK": 4},
        },
    )

    payload = build_dashboard_payload(report_dir)

    assert payload["latest_run_id"] == RUN_ID
    assert {record["run_id"] for record in payload["records"]} == {RUN_ID, "unscoped"}
