from __future__ import annotations

import json
from pathlib import Path

from tools.runtime.offline_telegram_summary import build_offline_telegram_summary_message


DATE = "2026-05-15"
RUN_ID = "run/target<&>"


def _safe_run_id() -> str:
    return "run_target___"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_offline_telegram_summary_formats_required_fields_and_escapes_html(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    _write_json(
        reports / f"quant_data_quality_{DATE}_run_{_safe_run_id()}.json",
        {
            "bad_json_lines": 0,
            "replay_continuity": {"status": "PASS"},
            "malformed_json_impact": {
                "affects_selected_run": False,
                "total_malformed_json_lines_in_scanned_files": 2,
            },
        },
    )
    _write_json(
        reports / f"no_entry_report_{DATE}_run_{_safe_run_id()}.json",
        {
            "root_cause_category": "cutoff",
            "root_cause_counts": {"cutoff": 23, "risk": 9, "execution": 0},
            "count_time_unsafe": 23,
            "count_risk_plan_zero": 9,
            "bad_json_lines": 1,
            "market_data_quality": {
                "orderbook_unavailable_count": 0,
                "stale_data_count": 0,
            },
            "spread_liquidity_readiness_summary": {
                "liquidity_states": [["HEALTHY", 169]],
                "spread_normalization_rate": 0.9349,
            },
        },
    )
    _write_json(
        reports / f"session_runtime_evaluation_{DATE}_run_{_safe_run_id()}.json",
        {"market_readiness": {"orderbook_ready_count": 128}},
    )
    _write_json(
        reports / f"market_readiness_admission_probe_{DATE}.json",
        {
            "run_id_filter": RUN_ID,
            "gate_funnel": {"total": 32, "model_gate_reached": 32, "ev_gate_reached": 32},
            "lifecycle_phase_probe_distribution": {
                "ACTIVE_INVENTORY_TRADING": {"EXECUTABLE_EVALUATED": 10},
                "FINAL_DERISK": {"EXECUTABLE_EVALUATED": 18},
            },
        },
    )

    message = build_offline_telegram_summary_message(date=DATE, run_id=RUN_ID, report_dir=reports)

    assert "Run: <code>run/target&lt;&amp;&gt;</code>" in message
    assert "Continuity: <b>PASS</b>" in message
    assert "Root cause: <b>cutoff</b>" in message
    assert "time_unsafe=23" in message
    assert "risk_plan_zero=9" in message
    assert "ACTIVE_INVENTORY_TRADING=10" in message
    assert "FINAL_DERISK=18" in message
    assert "orderbook_ready=128" in message
    assert "liquidity=HEALTHY=169" in message
    assert "model_gate=32/32, ev_gate=32/32" in message
    assert "day warning only" in message
    assert "runtime, strategy, risk, execution, wallet, or live config" in message


def test_offline_telegram_summary_marks_scoped_bad_json_warning(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    _write_json(
        reports / f"quant_data_quality_{DATE}_run_{_safe_run_id()}.json",
        {
            "bad_json_lines": 1,
            "replay_continuity": {"status": "FAIL"},
            "malformed_json_impact": {
                "affects_selected_run": True,
                "total_malformed_json_lines_in_scanned_files": 3,
            },
        },
    )
    _write_json(
        reports / f"no_entry_report_{DATE}_run_{_safe_run_id()}.json",
        {"root_cause_category": "data", "count_time_unsafe": 0, "count_risk_plan_zero": 0},
    )

    message = build_offline_telegram_summary_message(date=DATE, run_id=RUN_ID, report_dir=reports)

    assert "Continuity: <b>FAIL</b>" in message
    assert "SCOPED WARNING" in message
    assert "scoped_bad_json=1" in message
