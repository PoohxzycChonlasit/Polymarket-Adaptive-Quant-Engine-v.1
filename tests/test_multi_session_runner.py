from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.multi_session_runner import (
    REPLAY_STEPS,
    aggregate_sessions,
    render_markdown_summary,
    run_multi_session_validation,
    validate_date,
)


DATE_1 = "2026-05-13"
DATE_2 = "2026-05-12"


REPORT_FIXTURES = {
    "quant_data_quality": {
        "ok": True,
        "bad_json_lines": 0,
        "lines_scanned": 100,
        "valid_events": 90,
        "replay_continuity": {"status": "PASS"},
    },
    "sem_c_fill_replay": {
        "candidate_count": 40,
        "hypothetical_fill_count": 30,
        "paper_trial_verdict": "paper_only_candidate",
    },
    "sem_c_pnl_truth": {
        "settlement_coverage_rate": 0.8,
        "hypothetical_pnl": 12.5,
        "economic_evidence_verdict": "needs_more_data",
    },
    "sem_c_inv_continuity": {
        "entries": 12,
        "skipped_candidates": 4,
        "max_concurrent_exposure": 2.5,
        "scoped_paper_trial_verdict": "scoped_candidate",
    },
    "lifecycle_pm": {
        "n_positions": 50,
        "policy_A": {"realized_proxy_pnl": 8.0},
        "policy_B": {"realized_proxy_pnl": 14.0, "max_drawdown": 1.2, "win_rate": 0.6},
        "policy_C": {"realized_proxy_pnl": 10.0},
        "policy_D": {"realized_proxy_pnl": 9.0},
        "policy_E": {"realized_proxy_pnl": 7.0},
    },
    "commitment_regime": {
        "stabilized_count": 30,
        "survived_count": 9,
        "score_reports": {
            "distance_minus_vol_score": {
                "accuracy": 0.61,
                "precision": 0.46,
                "recall": 0.7,
                "f1": 0.55,
                "verdict": "diagnostic_only",
            }
        },
    },
}


TOOL_TO_PREFIX = {
    "tools/quant_data_quality.py": "quant_data_quality",
    "tools.semantic_c_shadow_fill_replay": "sem_c_fill_replay",
    "tools.semantic_c_shadow_pnl_truth": "sem_c_pnl_truth",
    "tools.semantic_c_inventory_continuity_replay": "sem_c_inv_continuity",
    "tools.lifecycle_profit_management_replay": "lifecycle_pm",
    "tools.commitment_regime_replay": "commitment_regime",
}


def _tool_key(command: Sequence[str]) -> str:
    if len(command) > 2 and command[1] == "-m":
        return command[2]
    return command[1]


def _arg_after(command: Sequence[str], flag: str) -> str:
    return command[command.index(flag) + 1]


def _runner(
    *,
    missing_prefixes: set[str] | None = None,
    failing_prefixes: set[str] | None = None,
    calls: list[list[str]] | None = None,
):
    missing = missing_prefixes or set()
    failing = failing_prefixes or set()

    def fake_runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        command_list = list(command)
        if calls is not None:
            calls.append(command_list)
        prefix = TOOL_TO_PREFIX[_tool_key(command)]
        date_str = _arg_after(command, "--date")
        report_dir = Path(_arg_after(command, "--report-dir"))
        report_dir.mkdir(parents=True, exist_ok=True)
        if prefix not in missing and prefix not in failing:
            payload = dict(REPORT_FIXTURES[prefix])
            (report_dir / f"{prefix}_{date_str}_fake.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(
            args=command_list,
            returncode=2 if prefix in failing else 0,
            stdout=f"{prefix} stdout",
            stderr=f"{prefix} stderr" if prefix in failing else "",
        )

    return fake_runner


def test_deterministic_order_in_manifest_and_commands(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    manifest = run_multi_session_validation(
        dates=[DATE_1],
        output_dir=tmp_path,
        execute=True,
        run_label="order",
        python_executable="python",
        runner=_runner(calls=calls),
        cwd=_REPO,
    )

    assert manifest["fixed_replay_order"] == [step.name for step in REPLAY_STEPS]
    command_names = [_tool_key(call) for call in calls]
    assert command_names == [
        "tools/quant_data_quality.py",
        "tools.semantic_c_shadow_fill_replay",
        "tools.semantic_c_shadow_pnl_truth",
        "tools.semantic_c_inventory_continuity_replay",
        "tools.lifecycle_profit_management_replay",
        "tools.commitment_regime_replay",
    ]


def test_default_is_dry_run_command_recording(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    manifest = run_multi_session_validation(
        dates=[DATE_1],
        output_dir=tmp_path,
        run_label="dry",
        python_executable="python",
        runner=_runner(calls=calls),
    )

    assert manifest["execute"] is False
    assert calls == []
    assert all(
        not step["command_record"]["executed"]
        for step in manifest["sessions"][0]["steps"]
    )
    assert manifest["sessions"][0]["status"] == "incomplete"


def test_missing_report_handling_marks_date_incomplete_and_continues(tmp_path: Path) -> None:
    manifest = run_multi_session_validation(
        dates=[DATE_1, DATE_2],
        output_dir=tmp_path,
        execute=True,
        run_label="missing",
        python_executable="python",
        runner=_runner(missing_prefixes={"sem_c_pnl_truth"}),
        cwd=_REPO,
    )

    assert manifest["aggregate"]["incomplete_session_count"] == 2
    assert manifest["aggregate"]["incomplete_dates"] == [DATE_1, DATE_2]
    for session in manifest["sessions"]:
        assert "semantic_c_shadow_pnl_truth" in session["missing_reports"]
        assert session["steps"][-1]["step_name"] == "commitment_regime_replay"
        assert session["steps"][-1]["missing_report"] is False


def test_aggregation_correctness_from_session_metrics(tmp_path: Path) -> None:
    manifest = run_multi_session_validation(
        dates=[DATE_1, DATE_2],
        output_dir=tmp_path,
        execute=True,
        run_label="aggregate",
        python_executable="python",
        runner=_runner(),
        cwd=_REPO,
    )

    aggregate = manifest["aggregate"]
    assert aggregate["complete_session_count"] == 2
    assert aggregate["policy_b_rank_values"] == [1, 1]
    assert aggregate["policy_b_rank_1_count"] == 2
    assert aggregate["policy_b_pnl_sum"] == 28.0
    assert aggregate["total_positions"] == 100
    assert aggregate["total_stabilized"] == 60
    assert aggregate["total_survived"] == 18
    assert aggregate["pooled_survival_rate"] == pytest.approx(0.3)
    assert aggregate["automatic_verdict_promotion"] is False
    assert aggregate["threshold_optimization_performed"] is False


def test_session_isolation_uses_distinct_report_directories(tmp_path: Path) -> None:
    calls: list[list[str]] = []
    manifest = run_multi_session_validation(
        dates=[DATE_1, DATE_2],
        output_dir=tmp_path,
        execute=True,
        run_label="isolation",
        python_executable="python",
        runner=_runner(calls=calls),
        cwd=_REPO,
    )

    report_dirs = {session["report_dir"] for session in manifest["sessions"]}
    assert len(report_dirs) == 2
    assert all(str(tmp_path / "isolation" / "sessions") in report_dir for report_dir in report_dirs)
    command_report_dirs = {_arg_after(call, "--report-dir") for call in calls}
    assert command_report_dirs == report_dirs


def test_no_runtime_import_ast_scan() -> None:
    source = (_REPO / "tools" / "multi_session_runner.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = ("polymarket", "utils", "config", "main")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(forbidden), f"Forbidden runtime import: {alias.name}"
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith(forbidden), f"Forbidden runtime import: {node.module}"


def test_markdown_summary_generation_contains_required_safety_phrase(tmp_path: Path) -> None:
    manifest = run_multi_session_validation(
        dates=[DATE_1],
        output_dir=tmp_path,
        execute=True,
        run_label="markdown",
        python_executable="python",
        runner=_runner(),
        cwd=_REPO,
    )

    markdown = Path(manifest["output_paths"]["markdown"]).read_text(encoding="utf-8")
    assert "validation output, not runtime approval." in markdown
    assert "Automatic verdict promotion: `False`" in markdown
    assert "Threshold optimization performed: `False`" in markdown
    assert render_markdown_summary(manifest).startswith("# Multi-Session Validation Summary")


def test_output_path_correctness_and_optional_obsidian_copy(tmp_path: Path) -> None:
    obsidian_dir = tmp_path / "vault"
    manifest = run_multi_session_validation(
        dates=[DATE_1],
        output_dir=tmp_path / "runtime" / "reports" / "multi_session_validation",
        execute=True,
        run_label="paths",
        python_executable="python",
        runner=_runner(),
        cwd=_REPO,
        obsidian_dir=obsidian_dir,
    )

    run_dir = tmp_path / "runtime" / "reports" / "multi_session_validation" / "paths"
    assert Path(manifest["output_paths"]["manifest"]) == run_dir / "manifest.json"
    assert Path(manifest["output_paths"]["aggregate"]) == run_dir / "aggregate_metrics.json"
    assert Path(manifest["output_paths"]["markdown"]) == run_dir / "validation_summary.md"
    assert Path(manifest["output_paths"]["obsidian_markdown"]).parent == obsidian_dir


def test_fail_soft_behavior_records_command_failure_and_keeps_later_steps(tmp_path: Path) -> None:
    manifest = run_multi_session_validation(
        dates=[DATE_1],
        output_dir=tmp_path,
        execute=True,
        run_label="failsoft",
        python_executable="python",
        runner=_runner(failing_prefixes={"sem_c_fill_replay"}),
        cwd=_REPO,
    )

    steps = manifest["sessions"][0]["steps"]
    failed = next(step for step in steps if step["step_name"] == "semantic_c_shadow_fill_replay")
    assert failed["command_record"]["return_code"] == 2
    assert failed["command_failed"] is True
    assert failed["status"] == "command_failed"
    assert failed["missing_report"] is True
    assert steps[-1]["step_name"] == "commitment_regime_replay"
    assert steps[-1]["missing_report"] is False
    assert manifest["sessions"][0]["status"] == "incomplete"


def test_replay_command_recording_includes_run_id_and_report_dir(tmp_path: Path) -> None:
    manifest = run_multi_session_validation(
        dates=[DATE_1],
        output_dir=tmp_path,
        execute=True,
        run_ids={DATE_1: "run-selected"},
        run_label="commands",
        python_executable="python",
        runner=_runner(),
        cwd=_REPO,
    )

    command = manifest["sessions"][0]["steps"][0]["command_record"]["command"]
    assert command[:2] == ["python", "tools/quant_data_quality.py"]
    assert "--date" in command
    assert _arg_after(command, "--date") == DATE_1
    assert "--write-report" in command
    assert "--report-dir" in command
    assert "--run-id" in command
    assert _arg_after(command, "--run-id") == "run-selected"
    assert "tools/quant_data_quality.py" in manifest["sessions"][0]["steps"][0]["command_record"]["command_text"]


def test_invalid_date_handling() -> None:
    with pytest.raises(ValueError):
        validate_date("2026-02-30")
    with pytest.raises(ValueError):
        run_multi_session_validation(dates=["20260513"], output_dir=Path("unused"))


def test_aggregate_sessions_handles_empty_or_missing_metrics() -> None:
    aggregate = aggregate_sessions([
        {"date": DATE_1, "status": "incomplete", "steps": [{"step_name": "missing", "metrics": {}}]},
    ])

    assert aggregate["session_count"] == 1
    assert aggregate["complete_session_count"] == 0
    assert aggregate["incomplete_dates"] == [DATE_1]
    assert aggregate["policy_b_pnl_sum"] is None
