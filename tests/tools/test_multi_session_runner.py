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

from tools.replay.multi_session_runner import (
    CANONICAL_SR60_POLICY_ID,
    CAUTION_STATUS,
    FULL_COVERAGE_STATUS,
    PARTIAL_COVERAGE_STATUS,
    REPLAY_STEPS,
    REQUIRED_BUT_NOT_RUN,
    SCORE_C_ACCURACY_NOTE,
    SEMANTIC_C_STEP_NAMES,
    WARNING_BANNER,
    _resolve_canonical_lifecycle_metrics,
    aggregate_sessions,
    load_policy_registry,
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
    "exit_convergence": {
        "policy_B": {"realized_proxy_pnl": 67.67, "verdict": "safe_candidate"},
        "policy_comparison": {
            "best_pnl_policy": "B  fixed-derisk-SR<60",
            "recommended": "B  fixed-derisk-SR<60",
        },
    },
    "conv_regime": {
        "realtime_accuracy": 0.8906,
        "pseudo_after_high_confidence_count": 0,
        "diagnostic_regimes": {"VOLATILITY_RESURGENCE": {"count": 28}},
        "recommendation": {"recommended_policy": "VOLATILITY_RESURGENCE_GUARD"},
    },
    "stab_survival": {
        "stabilization_count": 59,
        "survival_count": 13,
        "survival_rate": 0.2203,
        "verdict": {"verdict": "fixed_SR60_remains_best"},
    },
}


TOOL_TO_PREFIX = {
    "tools.research.quant_data_quality": "quant_data_quality",
    "tools.shadow.semantic_c_shadow_fill_replay": "sem_c_fill_replay",
    "tools.shadow.semantic_c_shadow_pnl_truth": "sem_c_pnl_truth",
    "tools.shadow.semantic_c_inventory_continuity_replay": "sem_c_inv_continuity",
    "tools.replay.lifecycle_profit_management_replay": "lifecycle_pm",
    "tools.replay.commitment_regime_replay": "commitment_regime",
    "tools.replay.exit_convergence_intelligence_replay": "exit_convergence",
    "tools.replay.convergence_regime_classification_replay": "conv_regime",
    "tools.replay.stabilization_survival_replay": "stab_survival",
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
    failing_with_report_prefixes: set[str] | None = None,
    calls: list[list[str]] | None = None,
):
    """
    missing_prefixes: step returns success exit code but writes no report file.
    failing_prefixes: step returns non-zero exit code AND writes no report.
    failing_with_report_prefixes: step returns non-zero exit code BUT writes report
        (models the real data_quality_gate behaviour: finds hygiene issues,
        returns non-zero, but still produces its JSON report).
    """
    missing = missing_prefixes or set()
    failing = failing_prefixes or set()
    failing_with_report = failing_with_report_prefixes or set()

    def fake_runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        command_list = list(command)
        if calls is not None:
            calls.append(command_list)
        prefix = TOOL_TO_PREFIX[_tool_key(command)]
        date_str = _arg_after(command, "--date")
        report_dir = Path(_arg_after(command, "--report-dir"))
        report_dir.mkdir(parents=True, exist_ok=True)
        # Write report unless explicitly suppressed by missing or failing (no-report) sets.
        if prefix not in missing and prefix not in failing:
            payload = dict(REPORT_FIXTURES[prefix])
            (report_dir / f"{prefix}_{date_str}_fake.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
        failed = prefix in failing or prefix in failing_with_report
        return subprocess.CompletedProcess(
            args=command_list,
            returncode=2 if failed else 0,
            stdout=f"{prefix} stdout",
            stderr=f"{prefix} stderr" if failed else "",
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
        "tools.research.quant_data_quality",
        "tools.shadow.semantic_c_shadow_fill_replay",
        "tools.shadow.semantic_c_shadow_pnl_truth",
        "tools.shadow.semantic_c_inventory_continuity_replay",
        "tools.replay.lifecycle_profit_management_replay",
        "tools.replay.commitment_regime_replay",
        "tools.replay.exit_convergence_intelligence_replay",
        "tools.replay.convergence_regime_classification_replay",
        "tools.replay.stabilization_survival_replay",
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
        assert session["steps"][-1]["step_name"] == "stabilization_survival_replay"
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
    import tools.replay.multi_session_runner as target_module
    source = Path(target_module.__file__).read_text(encoding="utf-8")
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
    assert WARNING_BANNER in markdown
    assert "Automatic verdict promotion: `False`" in markdown
    assert "Threshold optimization performed: `False`" in markdown
    assert render_markdown_summary(manifest).startswith("# Multi-Session Validation Summary")


def test_missing_validation_tools_present_in_manifest_and_markdown(tmp_path: Path) -> None:
    manifest = run_multi_session_validation(
        dates=[DATE_1],
        output_dir=tmp_path,
        execute=True,
        run_label="coverage_missing",
        python_executable="python",
        runner=_runner(),
        cwd=_REPO,
    )

    assert manifest["required_but_not_run"] == list(REQUIRED_BUT_NOT_RUN)
    assert manifest["validation_coverage"]["missing_validation_tools"] == list(REQUIRED_BUT_NOT_RUN)

    persisted = json.loads(Path(manifest["output_paths"]["manifest"]).read_text(encoding="utf-8"))
    assert persisted["required_but_not_run"] == list(REQUIRED_BUT_NOT_RUN)
    assert persisted["validation_coverage"]["missing_validation_tools"] == list(REQUIRED_BUT_NOT_RUN)

    markdown = Path(manifest["output_paths"]["markdown"]).read_text(encoding="utf-8")
    for missing_tool in REQUIRED_BUT_NOT_RUN:
        assert missing_tool in markdown


def test_partial_coverage_flag_correctness(tmp_path: Path) -> None:
    manifest = run_multi_session_validation(
        dates=[DATE_1],
        output_dir=tmp_path,
        execute=True,
        run_label="coverage_partial",
        python_executable="python",
        runner=_runner(),
        cwd=_REPO,
    )

    coverage = manifest["validation_coverage"]
    assert coverage["coverage_status"] == FULL_COVERAGE_STATUS
    assert coverage["executed_tools"] == [step.name for step in REPLAY_STEPS]
    assert coverage["runner_tool_chain"] == [step.name for step in REPLAY_STEPS]
    assert coverage["dry_run_command_recording"] is False

    dry_manifest = run_multi_session_validation(
        dates=[DATE_1],
        output_dir=tmp_path,
        run_label="coverage_dry",
        python_executable="python",
        runner=_runner(),
    )
    assert dry_manifest["validation_coverage"]["coverage_status"] == FULL_COVERAGE_STATUS
    assert dry_manifest["validation_coverage"]["executed_tools"] == []
    assert dry_manifest["validation_coverage"]["dry_run_command_recording"] is True


def test_oos_warning_persistence(tmp_path: Path) -> None:
    manifest = run_multi_session_validation(
        dates=[DATE_1],
        output_dir=tmp_path,
        execute=True,
        run_label="oos_warning",
        python_executable="python",
        runner=_runner(),
        cwd=_REPO,
    )

    assert manifest["oos_score_c_not_validated"] is True
    assert manifest["score_c_accuracy_note"] == SCORE_C_ACCURACY_NOTE
    assert manifest["oos_integrity"]["oos_score_c_not_validated"] is True
    assert manifest["oos_integrity"]["score_c_accuracy_note"] == SCORE_C_ACCURACY_NOTE

    persisted = json.loads(Path(manifest["output_paths"]["manifest"]).read_text(encoding="utf-8"))
    assert persisted["oos_score_c_not_validated"] is True
    assert persisted["score_c_accuracy_note"] == SCORE_C_ACCURACY_NOTE

    markdown = Path(manifest["output_paths"]["markdown"]).read_text(encoding="utf-8")
    assert "oos_score_c_not_validated: true" in markdown
    assert SCORE_C_ACCURACY_NOTE in markdown


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
    assert steps[-1]["step_name"] == "stabilization_survival_replay"
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
    assert command[:3] == ["python", "-m", "tools.research.quant_data_quality"]
    assert "--date" in command
    assert _arg_after(command, "--date") == DATE_1
    assert "--write-report" in command
    assert "--report-dir" in command
    assert "--run-id" in command
    assert _arg_after(command, "--run-id") == "run-selected"
    assert "tools.research.quant_data_quality" in manifest["sessions"][0]["steps"][0]["command_record"]["command_text"]
    assert "tools/quant_data_quality.py" not in manifest["sessions"][0]["steps"][0]["command_record"]["command_text"]


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


def test_data_quality_caution_with_complete_semantic_c(tmp_path: Path) -> None:
    """
    data_quality_gate fails (non-zero, e.g. bad_json found) but writes its report
    and all Semantic C steps complete normally.
    Session must be classified as CAUTION, not incomplete.
    Semantic C evidence is usable; aggregate counts it as complete.
    """
    manifest = run_multi_session_validation(
        dates=[DATE_1],
        output_dir=tmp_path,
        execute=True,
        run_label="dq_caution",
        python_executable="python",
        runner=_runner(failing_with_report_prefixes={"quant_data_quality"}),
        cwd=_REPO,
    )

    session = manifest["sessions"][0]
    assert session["status"] == CAUTION_STATUS
    assert session["data_quality_caution"] is True

    # Raw step data preserved: quality gate is still recorded as command_failed.
    dqg_step = next(s for s in session["steps"] if s["step_name"] == "data_quality_gate")
    assert dqg_step["command_failed"] is True
    assert dqg_step["missing_report"] is False   # report WAS written

    # Semantic C steps are all complete.
    for step in session["steps"]:
        if step["step_name"] in SEMANTIC_C_STEP_NAMES:
            assert step["status"] == "complete", step["step_name"]

    aggregate = manifest["aggregate"]
    assert aggregate["complete_session_count"] == 1   # caution counts as usable
    assert aggregate["caution_session_count"] == 1
    assert aggregate["incomplete_session_count"] == 0
    assert aggregate["caution_dates"] == [DATE_1]
    assert aggregate["incomplete_dates"] == []


def test_canonical_registry_loads_and_contains_sr60_derisk() -> None:
    """Registry file exists, parses cleanly, and contains the canonical SR<60 policy."""
    registry = load_policy_registry()
    assert registry is not None, "research/replay_policy_registry.json must exist"
    assert registry.get("schema_version") == "replay_policy_registry_v1"
    ids = [p["canonical_policy_id"] for p in registry.get("policies", [])]
    assert CANONICAL_SR60_POLICY_ID in ids


def test_policy_d_maps_to_canonical_sr60_with_naming_drift_flag() -> None:
    """lifecycle_profit_management_replay's policy_D is the SR<60 derisk, with drift flagged."""
    registry = load_policy_registry()
    assert registry is not None
    entry = next(
        (p for p in registry["policies"] if p["canonical_policy_id"] == CANONICAL_SR60_POLICY_ID),
        None,
    )
    assert entry is not None, f"{CANONICAL_SR60_POLICY_ID} must be in registry"
    lpm = next(
        (m for m in entry["tool_mappings"] if m["replay_tool"] == "lifecycle_profit_management_replay"),
        None,
    )
    assert lpm is not None, "lifecycle_profit_management_replay must have a mapping"
    assert lpm["tool_key"] == "policy_D"
    assert lpm["naming_drift"] is True


def test_canonical_rank_is_1_when_policy_d_is_best() -> None:
    """Canonical resolution returns rank=1 when policy_D has the highest PnL (real 2026-05-15 profile)."""
    registry = load_policy_registry()
    assert registry is not None
    # Matches real 2026-05-15 lifecycle_pm output where policy_D ($67.67) is best.
    synthetic_report = {
        "policy_A": {"realized_proxy_pnl": 62.45},
        "policy_B": {"realized_proxy_pnl": 62.25},
        "policy_C": {"realized_proxy_pnl": 66.09},
        "policy_D": {"realized_proxy_pnl": 67.67},
        "policy_E": {"realized_proxy_pnl": 63.04},
    }
    metrics = _resolve_canonical_lifecycle_metrics(synthetic_report, registry)
    assert metrics["canonical_sr60_derisk_rank"] == 1
    assert metrics["canonical_sr60_derisk_pnl"] == pytest.approx(67.67)
    assert metrics["canonical_policy_id"] == CANONICAL_SR60_POLICY_ID
    assert metrics["canonical_naming_drift_resolved"] is True


def test_backward_compat_policy_b_fields_alongside_canonical(tmp_path: Path) -> None:
    """Old policy_b_* fields survive unchanged; new canonical_sr60_* fields co-exist."""
    manifest = run_multi_session_validation(
        dates=[DATE_1],
        output_dir=tmp_path,
        execute=True,
        run_label="compat_canonical",
        python_executable="python",
        runner=_runner(),
        cwd=_REPO,
    )
    lifecycle_metrics = next(
        step["metrics"]
        for step in manifest["sessions"][0]["steps"]
        if step["step_name"] == "lifecycle_profit_management_replay"
    )
    # Backward-compat fields still present.
    assert "policy_b_rank" in lifecycle_metrics
    assert "policy_b_pnl" in lifecycle_metrics
    assert "policy_a_pnl" in lifecycle_metrics
    # New canonical fields present (registry loaded from research/replay_policy_registry.json).
    assert "canonical_sr60_derisk_rank" in lifecycle_metrics
    assert "canonical_sr60_derisk_pnl" in lifecycle_metrics
    assert "canonical_policy_id" in lifecycle_metrics
    assert lifecycle_metrics["canonical_policy_id"] == CANONICAL_SR60_POLICY_ID
    # Aggregate has canonical fields.
    aggregate = manifest["aggregate"]
    assert "canonical_sr60_rank_1_count" in aggregate
    assert "canonical_sr60_rank_values" in aggregate
    assert "canonical_sr60_pnl_sum" in aggregate
    # In fixture: policy_D.realized_proxy_pnl = 9.0 (3rd after B=14, C=10).
    assert lifecycle_metrics["canonical_sr60_derisk_rank"] == 3
    assert lifecycle_metrics["canonical_sr60_derisk_pnl"] == pytest.approx(9.0)
    # Manifest top-level registry fields.
    assert manifest["canonical_policy_registry_loaded"] is True
    assert manifest["canonical_sr60_policy_id"] == CANONICAL_SR60_POLICY_ID


def test_data_quality_caution_missing_semantic_c_is_incomplete(tmp_path: Path) -> None:
    """
    data_quality_gate fails with report AND a Semantic C step is missing.
    Session must be classified as incomplete (not caution) because the
    Semantic C evidence itself is incomplete.
    """
    manifest = run_multi_session_validation(
        dates=[DATE_1],
        output_dir=tmp_path,
        execute=True,
        run_label="dq_caution_sem_miss",
        python_executable="python",
        runner=_runner(
            failing_with_report_prefixes={"quant_data_quality"},
            missing_prefixes={"sem_c_fill_replay"},
        ),
        cwd=_REPO,
    )

    session = manifest["sessions"][0]
    assert session["status"] == "incomplete"
    assert session["data_quality_caution"] is False

    aggregate = manifest["aggregate"]
    assert aggregate["incomplete_session_count"] == 1
    assert aggregate["caution_session_count"] == 0
    assert aggregate["incomplete_dates"] == [DATE_1]
    assert aggregate["caution_dates"] == []
