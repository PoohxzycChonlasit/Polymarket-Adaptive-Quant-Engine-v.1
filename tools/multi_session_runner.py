"""Docs-safe multi-session replay orchestration.

Offline-only; no runtime changes. This tool records and optionally executes the
Phase 2 multi-session validation chain. It never imports trading runtime
modules, never mutates existing replay reports, never tunes thresholds, and
never promotes verdicts automatically.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


DEFAULT_OUTPUT_DIR = Path("runtime/reports/multi_session_validation")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class ReplayStep:
    step_id: int
    name: str
    module: str | None
    script: str | None
    report_prefix: str


REPLAY_STEPS: tuple[ReplayStep, ...] = (
    ReplayStep(0, "data_quality_gate", None, "tools/quant_data_quality.py", "quant_data_quality"),
    ReplayStep(1, "semantic_c_shadow_fill_replay", "tools.semantic_c_shadow_fill_replay", None, "sem_c_fill_replay"),
    ReplayStep(2, "semantic_c_shadow_pnl_truth", "tools.semantic_c_shadow_pnl_truth", None, "sem_c_pnl_truth"),
    ReplayStep(3, "semantic_c_inventory_continuity_replay", "tools.semantic_c_inventory_continuity_replay", None, "sem_c_inv_continuity"),
    ReplayStep(4, "lifecycle_profit_management_replay", "tools.lifecycle_profit_management_replay", None, "lifecycle_pm"),
    ReplayStep(5, "commitment_regime_replay", "tools.commitment_regime_replay", None, "commitment_regime"),
)


CommandRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


def validate_date(date_str: str) -> str:
    if not DATE_RE.match(date_str):
        raise ValueError(f"Invalid date '{date_str}'. Expected YYYY-MM-DD.")
    parsed = datetime.strptime(date_str, "%Y-%m-%d")
    if parsed.strftime("%Y-%m-%d") != date_str:
        raise ValueError(f"Invalid date '{date_str}'. Expected a real YYYY-MM-DD date.")
    return date_str


def parse_run_id_map(values: Sequence[str] | None) -> dict[str, str]:
    run_ids: dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError("--run-id must use DATE=RUN_ID format.")
        date_str, run_id = value.split("=", 1)
        date_str = validate_date(date_str.strip())
        run_id = run_id.strip()
        if not run_id:
            raise ValueError(f"Missing run id for {date_str}.")
        run_ids[date_str] = run_id
    return run_ids


def build_command(
    step: ReplayStep,
    *,
    date_str: str,
    report_dir: Path,
    python_executable: str,
    run_id: str | None = None,
) -> list[str]:
    if step.script:
        command = [python_executable, step.script]
    else:
        command = [python_executable, "-m", step.module or ""]
    command.extend(["--date", date_str, "--write-report", "--report-dir", str(report_dir)])
    if run_id:
        command.extend(["--run-id", run_id])
    return command


def _default_runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "run"


def make_run_label(now: datetime | None = None, *, dry_run: bool = True) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    prefix = "dry_run" if dry_run else "executed"
    return f"{prefix}_{stamp}"


def _list_reports(report_dir: Path, step: ReplayStep, date_str: str) -> list[Path]:
    if not report_dir.exists():
        return []
    return sorted(report_dir.glob(f"{step.report_prefix}_{date_str}*.json"))


def _read_json(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _first_number(payload: dict[str, Any], keys: Sequence[str]) -> float | int | None:
    for key in keys:
        value: Any = payload
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                value = None
                break
            value = value[part]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
    return None


def _policy_b_rank(report: dict[str, Any]) -> int | None:
    policies: list[tuple[str, float]] = []
    for key in ("policy_A", "policy_B", "policy_C", "policy_D", "policy_E"):
        payload = report.get(key)
        if not isinstance(payload, dict):
            continue
        pnl = payload.get("realized_proxy_pnl")
        if isinstance(pnl, (int, float)) and not isinstance(pnl, bool):
            policies.append((key, float(pnl)))
    if not policies:
        return None
    ranked = sorted(policies, key=lambda item: item[1], reverse=True)
    for idx, (key, _) in enumerate(ranked, start=1):
        if key == "policy_B":
            return idx
    return None


def extract_step_metrics(step_name: str, report: dict[str, Any]) -> dict[str, Any]:
    if not report:
        return {}
    if step_name == "data_quality_gate":
        malformed = _first_number(report, ("bad_json_lines", "bad_lines_count"))
        lines = _first_number(report, ("lines_scanned",))
        malformed_rate = None
        if isinstance(malformed, (int, float)) and isinstance(lines, (int, float)) and lines:
            malformed_rate = float(malformed) / float(lines)
        return {
            "ok": report.get("ok"),
            "bad_json_lines": malformed,
            "malformed_json_rate": malformed_rate,
            "valid_events": _first_number(report, ("valid_events",)),
            "replay_continuity_status": (report.get("replay_continuity") or {}).get("status")
            if isinstance(report.get("replay_continuity"), dict)
            else None,
        }
    if step_name == "semantic_c_shadow_fill_replay":
        return {
            "candidate_count": _first_number(report, ("candidate_count", "total_candidates", "input_candidate_count")),
            "hypothetical_fill_count": _first_number(report, ("hypothetical_fill_count", "fill_count", "fills")),
            "paper_trial_verdict": report.get("paper_trial_verdict") or report.get("verdict"),
        }
    if step_name == "semantic_c_shadow_pnl_truth":
        return {
            "settlement_coverage_rate": _first_number(report, ("settlement_coverage_rate", "settlement_coverage")),
            "hypothetical_pnl": _first_number(report, ("hypothetical_pnl", "realized_proxy_pnl", "total_pnl")),
            "economic_evidence_verdict": report.get("economic_evidence_verdict") or report.get("verdict"),
        }
    if step_name == "semantic_c_inventory_continuity_replay":
        return {
            "entries": _first_number(report, ("entries", "entry_count", "positions_opened")),
            "skipped_candidates": _first_number(report, ("skipped_candidates", "skip_count")),
            "max_concurrent_exposure": _first_number(report, ("max_concurrent_exposure", "max_exposure_usd")),
            "scoped_paper_trial_verdict": report.get("scoped_paper_trial_verdict") or report.get("verdict"),
        }
    if step_name == "lifecycle_profit_management_replay":
        return {
            "n_positions": _first_number(report, ("n_positions", "position_count", "policy_B.n_positions")),
            "policy_b_pnl": _first_number(report, ("policy_B.realized_proxy_pnl",)),
            "policy_a_pnl": _first_number(report, ("policy_A.realized_proxy_pnl",)),
            "policy_b_rank": _policy_b_rank(report),
            "policy_b_max_drawdown": _first_number(report, ("policy_B.max_drawdown", "policy_B.max_drawdown_usd")),
            "policy_b_win_rate": _first_number(report, ("policy_B.win_rate",)),
        }
    if step_name == "commitment_regime_replay":
        score_c = {}
        score_reports = report.get("score_reports")
        if isinstance(score_reports, dict):
            score_c = score_reports.get("distance_minus_vol_score") or score_reports.get("score_C") or {}
            if not isinstance(score_c, dict):
                score_c = {}
        return {
            "stabilized_count": _first_number(report, ("stabilized_count", "n_stabilized")),
            "survived_count": _first_number(report, ("survived_count", "n_survived")),
            "score_c_accuracy": _first_number(score_c, ("accuracy", "oos_accuracy")),
            "score_c_precision": _first_number(score_c, ("precision", "oos_precision")),
            "score_c_recall": _first_number(score_c, ("recall", "oos_recall")),
            "score_c_f1": _first_number(score_c, ("f1", "oos_f1")),
            "score_c_verdict": score_c.get("verdict"),
        }
    return {}


def _command_record(
    *,
    step: ReplayStep,
    command: list[str],
    executed: bool,
    result: subprocess.CompletedProcess[str] | None,
    started_at: str | None,
    finished_at: str | None,
    duration_seconds: float | None,
) -> dict[str, Any]:
    stdout = result.stdout if result and isinstance(result.stdout, str) else ""
    stderr = result.stderr if result and isinstance(result.stderr, str) else ""
    return {
        "step_id": step.step_id,
        "step_name": step.name,
        "command": command,
        "command_text": subprocess.list2cmdline(command),
        "executed": executed,
        "return_code": result.returncode if result else None,
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "duration_seconds": duration_seconds,
        "stdout_chars": len(stdout),
        "stderr_chars": len(stderr),
        "stdout_preview": stdout[:1000],
        "stderr_preview": stderr[:1000],
    }


def _run_step(
    *,
    step: ReplayStep,
    date_str: str,
    report_dir: Path,
    python_executable: str,
    run_id: str | None,
    execute: bool,
    cwd: Path,
    runner: CommandRunner,
) -> dict[str, Any]:
    command = build_command(
        step,
        date_str=date_str,
        report_dir=report_dir,
        python_executable=python_executable,
        run_id=run_id,
    )
    started_at = finished_at = None
    duration = None
    result: subprocess.CompletedProcess[str] | None = None
    before = set(_list_reports(report_dir, step, date_str))
    if execute:
        started_at = _utc_now()
        t0 = time.monotonic()
        result = runner(command, cwd)
        duration = round(time.monotonic() - t0, 6)
        finished_at = _utc_now()
    after = set(_list_reports(report_dir, step, date_str))
    created = sorted(after - before) or sorted(after)
    report_path = created[-1] if created else None
    report = _read_json(report_path)
    missing_report = report_path is None
    command_failed = bool(execute and result and result.returncode != 0)
    status = "complete"
    if command_failed:
        status = "command_failed"
    elif missing_report:
        status = "missing_report"
    return {
        "step_id": step.step_id,
        "step_name": step.name,
        "status": status,
        "command_failed": command_failed,
        "missing_report": missing_report,
        "report_path": str(report_path) if report_path else None,
        "metrics": extract_step_metrics(step.name, report),
        "command_record": _command_record(
            step=step,
            command=command,
            executed=execute,
            result=result,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration,
        ),
    }


def aggregate_sessions(sessions: Sequence[dict[str, Any]]) -> dict[str, Any]:
    complete_sessions = [s for s in sessions if s.get("status") == "complete"]
    incomplete_sessions = [s for s in sessions if s.get("status") != "complete"]
    policy_b_ranks: list[int] = []
    policy_b_pnls: list[float] = []
    total_positions = 0
    total_stabilized = 0
    total_survived = 0

    for session in sessions:
        by_name = {
            step.get("step_name"): step.get("metrics") or {}
            for step in session.get("steps", [])
        }
        lifecycle = by_name.get("lifecycle_profit_management_replay", {})
        commitment = by_name.get("commitment_regime_replay", {})
        rank = lifecycle.get("policy_b_rank")
        pnl = lifecycle.get("policy_b_pnl")
        n_positions = lifecycle.get("n_positions")
        stabilized = commitment.get("stabilized_count")
        survived = commitment.get("survived_count")
        if isinstance(rank, int):
            policy_b_ranks.append(rank)
        if isinstance(pnl, (int, float)) and not isinstance(pnl, bool):
            policy_b_pnls.append(float(pnl))
        if isinstance(n_positions, (int, float)) and not isinstance(n_positions, bool):
            total_positions += int(n_positions)
        if isinstance(stabilized, (int, float)) and not isinstance(stabilized, bool):
            total_stabilized += int(stabilized)
        if isinstance(survived, (int, float)) and not isinstance(survived, bool):
            total_survived += int(survived)

    survival_rate = None
    if total_stabilized:
        survival_rate = total_survived / total_stabilized
    return {
        "session_count": len(sessions),
        "complete_session_count": len(complete_sessions),
        "incomplete_session_count": len(incomplete_sessions),
        "incomplete_dates": [s.get("date") for s in incomplete_sessions],
        "policy_b_rank_1_count": sum(1 for rank in policy_b_ranks if rank == 1),
        "policy_b_rank_values": policy_b_ranks,
        "policy_b_pnl_sum": round(sum(policy_b_pnls), 8) if policy_b_pnls else None,
        "total_positions": total_positions,
        "total_stabilized": total_stabilized,
        "total_survived": total_survived,
        "pooled_survival_rate": survival_rate,
        "automatic_verdict_promotion": False,
        "threshold_optimization_performed": False,
    }


def render_markdown_summary(manifest: dict[str, Any]) -> str:
    aggregate = manifest.get("aggregate", {})
    lines = [
        "# Multi-Session Validation Summary",
        "",
        "**validation output, not runtime approval.**",
        "",
        "This summary is generated by an offline orchestration tool. It does not update verdicts, tune thresholds, approve live trading, or modify runtime behavior.",
        "",
        f"- Run label: `{manifest.get('run_label')}`",
        f"- Mode: `{'execute' if manifest.get('execute') else 'dry-run command recording'}`",
        f"- Fixed replay order: `{', '.join(step.name for step in REPLAY_STEPS)}`",
        f"- Sessions requested: `{aggregate.get('session_count')}`",
        f"- Complete sessions: `{aggregate.get('complete_session_count')}`",
        f"- Incomplete sessions: `{aggregate.get('incomplete_session_count')}`",
        f"- Threshold optimization performed: `{aggregate.get('threshold_optimization_performed')}`",
        f"- Automatic verdict promotion: `{aggregate.get('automatic_verdict_promotion')}`",
        "",
        "## Session Status",
        "",
        "| Date | Status | Missing Reports | Commands Executed |",
        "|---|---:|---:|---:|",
    ]
    for session in manifest.get("sessions", []):
        missing = sum(1 for step in session.get("steps", []) if step.get("missing_report"))
        executed = sum(1 for step in session.get("steps", []) if (step.get("command_record") or {}).get("executed"))
        lines.append(f"| {session.get('date')} | {session.get('status')} | {missing} | {executed} |")
    lines.extend([
        "",
        "## Aggregate Metrics",
        "",
        f"- Policy B rank #1 count: `{aggregate.get('policy_b_rank_1_count')}`",
        f"- Policy B rank values: `{aggregate.get('policy_b_rank_values')}`",
        f"- Total positions: `{aggregate.get('total_positions')}`",
        f"- Total stabilized: `{aggregate.get('total_stabilized')}`",
        f"- Total survived: `{aggregate.get('total_survived')}`",
        f"- Pooled survival rate: `{aggregate.get('pooled_survival_rate')}`",
        "",
        "## Integrity Notes",
        "",
        "- The user-task fixed replay order was used, even if external validation docs list a different chain.",
        "- Existing replay report files are not modified; tools write only into per-session validation output folders when execution is explicit.",
        "- Missing tools or reports mark a date incomplete and do not stop later dates from being recorded.",
        "- Per-session and pooled thresholds are not optimized by this runner.",
    ])
    return "\n".join(lines) + "\n"


def write_outputs(manifest: dict[str, Any], *, run_dir: Path, obsidian_dir: Path | None = None) -> dict[str, str]:
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "manifest.json"
    aggregate_path = run_dir / "aggregate_metrics.json"
    markdown_path = run_dir / "validation_summary.md"
    paths = {
        "manifest": str(manifest_path),
        "aggregate": str(aggregate_path),
        "markdown": str(markdown_path),
    }
    markdown = render_markdown_summary(manifest)
    if obsidian_dir:
        obsidian_dir.mkdir(parents=True, exist_ok=True)
        obsidian_path = obsidian_dir / f"multi_session_validation_{manifest['run_label']}.md"
        obsidian_path.write_text(markdown, encoding="utf-8")
        paths["obsidian_markdown"] = str(obsidian_path)
    manifest["output_paths"] = paths
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    aggregate_path.write_text(json.dumps(manifest["aggregate"], indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")
    return paths


def run_multi_session_validation(
    *,
    dates: Sequence[str],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    execute: bool = False,
    run_ids: dict[str, str] | None = None,
    run_label: str | None = None,
    python_executable: str | None = None,
    cwd: Path | None = None,
    runner: CommandRunner | None = None,
    obsidian_dir: Path | None = None,
) -> dict[str, Any]:
    valid_dates = [validate_date(date_str) for date_str in dates]
    if not valid_dates:
        raise ValueError("At least one --date is required.")
    root = Path(output_dir)
    label = _safe_token(run_label or make_run_label(dry_run=not execute))
    run_dir = root / label
    sessions_dir = run_dir / "sessions"
    py = python_executable or sys.executable
    workdir = cwd or Path.cwd()
    command_runner = runner or _default_runner
    run_id_map = run_ids or {}

    sessions: list[dict[str, Any]] = []
    for date_str in valid_dates:
        session_dir = sessions_dir / date_str
        report_dir = session_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        steps: list[dict[str, Any]] = []
        for step in REPLAY_STEPS:
            steps.append(
                _run_step(
                    step=step,
                    date_str=date_str,
                    report_dir=report_dir,
                    python_executable=py,
                    run_id=run_id_map.get(date_str),
                    execute=execute,
                    cwd=workdir,
                    runner=command_runner,
                )
            )
        missing_reports = [step["step_name"] for step in steps if step["missing_report"]]
        incomplete_steps = [step["step_name"] for step in steps if step["status"] != "complete"]
        sessions.append(
            {
                "date": date_str,
                "run_id": run_id_map.get(date_str),
                "session_dir": str(session_dir),
                "report_dir": str(report_dir),
                "status": "incomplete" if incomplete_steps else "complete",
                "missing_reports": missing_reports,
                "incomplete_steps": incomplete_steps,
                "steps": steps,
            }
        )

    manifest: dict[str, Any] = {
        "schema_version": "multi_session_validation_v1",
        "generated_at_utc": _utc_now(),
        "run_label": label,
        "execute": execute,
        "output_dir": str(root),
        "run_dir": str(run_dir),
        "fixed_replay_order": [step.name for step in REPLAY_STEPS],
        "oos_integrity": {
            "fixed_order_from_user_task": True,
            "no_threshold_retuning": True,
            "no_pooled_threshold_optimization": True,
            "no_automatic_verdict_promotion": True,
            "existing_replay_reports_modified": False,
        },
        "sessions": sessions,
    }
    manifest["aggregate"] = aggregate_sessions(sessions)
    manifest["output_paths"] = write_outputs(manifest, run_dir=run_dir, obsidian_dir=obsidian_dir)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline multi-session replay validation orchestrator.")
    parser.add_argument("--date", dest="single_dates", action="append", default=[], help="Session date in YYYY-MM-DD format. Repeatable.")
    parser.add_argument("--dates", dest="date_list", nargs="+", default=[], help="Session dates in deterministic order.")
    parser.add_argument("--run-id", action="append", default=[], help="Optional DATE=RUN_ID filter. Repeatable.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Validation output root.")
    parser.add_argument("--obsidian-dir", default=None, help="Optional directory for Obsidian-ready markdown copy.")
    parser.add_argument("--run-label", default=None, help="Optional deterministic output run label.")
    parser.add_argument("--python", default=sys.executable, help="Python executable used for replay commands.")
    parser.add_argument("--dry-run", action="store_true", help="Record commands only. This is the default.")
    parser.add_argument("--execute", action="store_true", help="Actually run replay commands. Default records commands only.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.dry_run and args.execute:
        parser.error("--dry-run cannot be combined with --execute.")
    dates = list(args.single_dates or []) + list(args.date_list or [])
    try:
        manifest = run_multi_session_validation(
            dates=dates,
            output_dir=Path(args.output_dir),
            execute=args.execute,
            run_ids=parse_run_id_map(args.run_id),
            run_label=args.run_label,
            python_executable=args.python,
            obsidian_dir=Path(args.obsidian_dir) if args.obsidian_dir else None,
        )
    except ValueError as exc:
        parser.error(str(exc))
        return 2
    print(f"multi-session validation manifest: {manifest['output_paths']['manifest']}")
    print(f"mode: {'execute' if args.execute else 'dry-run command recording'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
