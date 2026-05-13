from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REPORT_DIR = Path("runtime/reports")
DEFAULT_MEMORY_INDEX_DIR = Path("docs/research_memory/index")
DEFAULT_OUTPUT_DIR = Path("runtime/research_state")
COMPACT_SIZE_TARGET_BYTES = 10_000


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool) or value is None:
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool) or value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_list(value: Any, *, limit: int = 5) -> list[Any]:
    return list(value[:limit]) if isinstance(value, list) else []


def _run_id(payload: dict[str, Any]) -> str:
    run_id = str(payload.get("run_id") or "").strip()
    if run_id:
        return run_id
    time_filter = payload.get("time_filter")
    if isinstance(time_filter, dict):
        return str(time_filter.get("run_id") or "").strip()
    return ""


def _date_from_payload(payload: dict[str, Any]) -> str:
    for key in ("date_from", "date", "session_date"):
        value = str(payload.get(key) or "").strip()
        if len(value) >= 10:
            return value[:10]
    return ""


def _match_filters(path: Path, payload: dict[str, Any], *, date: str | None, run_id: str | None) -> bool:
    if date and date not in path.name and _date_from_payload(payload) != date:
        return False
    if run_id and _run_id(payload) != run_id:
        return False
    return True


def _latest_report(
    *,
    report_dir: str | Path,
    prefix: str,
    date: str | None = None,
    run_id: str | None = None,
) -> tuple[Path, dict[str, Any]] | None:
    root = Path(report_dir)
    if not root.exists():
        return None
    matches: list[tuple[float, Path, dict[str, Any]]] = []
    for path in root.glob(f"{prefix}*.json"):
        payload = _load_json(path)
        if payload is None or not _match_filters(path, payload, date=date, run_id=run_id):
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        matches.append((mtime, path, payload))
    if not matches:
        return None
    _mtime, path, payload = sorted(matches, key=lambda item: (item[0], item[1].name))[-1]
    return path, payload


def _latest_memory_indexes(
    *,
    memory_index_dir: str | Path,
    date: str | None = None,
    run_id: str | None = None,
    limit: int = 3,
) -> list[Path]:
    root = Path(memory_index_dir)
    if not root.exists():
        return []
    matches: list[tuple[float, Path]] = []
    for path in root.glob("*.md"):
        if date and date not in path.name:
            continue
        if run_id and run_id not in path.name:
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        matches.append((mtime, path))
    return [path for _mtime, path in sorted(matches, key=lambda item: (item[0], item[1].name), reverse=True)[:limit]]


def _counter_from_pairs(value: Any, *, limit: int = 5) -> dict[str, int]:
    counter: Counter[str] = Counter()
    if isinstance(value, dict):
        for key, count in value.items():
            counter[str(key)] += _as_int(count)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                counter[str(item[0])] += _as_int(item[1], default=1)
            elif isinstance(item, dict):
                label = str(item.get("cause") or item.get("section") or item.get("reason") or "").strip()
                if label:
                    counter[label] += _as_int(item.get("count"), default=1)
    return {key: int(count) for key, count in counter.most_common(limit)}


def _table_counts(payload: dict[str, Any]) -> dict[str, int]:
    tables = payload.get("tables")
    if not isinstance(tables, dict):
        return {}
    names = (
        "missed_starter_candidates",
        "candidate_blocked_before_ev",
        "candidate_blocked_after_ev",
        "time_unsafe_candidates",
        "liquidity_or_orderbook_blocked_candidates",
    )
    counts: dict[str, int] = {}
    for name in names:
        value = tables.get(name)
        counts[name] = len(value) if isinstance(value, list) else _as_int(value)
    return counts


def _distribution(payload: dict[str, Any], name: str) -> dict[str, int]:
    tables = payload.get("tables")
    if not isinstance(tables, dict):
        return {}
    value = tables.get(name)
    if isinstance(value, dict) and isinstance(value.get("counts"), dict):
        return {str(key): _as_int(count) for key, count in value["counts"].items()}
    return {}


def _unknown_lifecycle_rate(truth: dict[str, Any]) -> float:
    precision = truth.get("unknown_lifecycle_precision_metrics")
    if isinstance(precision, dict) and precision.get("refined_unknown_lifecycle_rate") is not None:
        return round(_as_float(precision.get("refined_unknown_lifecycle_rate")), 4)
    distribution = _distribution(truth, "lifecycle_phase_distribution")
    candidate_events = _as_int(truth.get("candidate_events"))
    if not candidate_events:
        return 0.0
    return round(_as_int(distribution.get("UNKNOWN")) / candidate_events, 4)


def _coverage_gaps(*reports: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    for report in reports:
        phase2 = report.get("phase2_coverage")
        if isinstance(phase2, dict):
            gaps.extend(str(item) for item in phase2.get("coverage_gaps", []) if item)
        evidence = report.get("evidence_completeness")
        if isinstance(evidence, dict):
            gaps.extend(str(item) for item in evidence.get("coverage_gaps", []) if item)
        partial = report.get("partial_lifecycle_replay")
        if isinstance(partial, dict):
            for item in partial.get("replay_unsupported_sections", []):
                if isinstance(item, dict) and item.get("section"):
                    gaps.append(str(item["section"]))
    return list(dict.fromkeys(gaps))[:8]


def _recommended_next_step(blind_spots: list[str], truth: dict[str, Any], cross: dict[str, Any]) -> str:
    unknown_rate = _unknown_lifecycle_rate(truth)
    if unknown_rate > 0:
        return "tighten lifecycle ownership or add direct lifecycle fields for remaining UNKNOWN candidate rows"
    if "mfe_mae_support" in blind_spots:
        return "add offline MFE/MAE candidate path evidence before full lifecycle replay claims"
    if "reload_unload_truth" in blind_spots:
        return "add direct reload/unload observability labels before inventory replay conclusions"
    maturity = str(cross.get("replay_truth_maturity") or "")
    if maturity and "PROXY" in maturity:
        return "rerun refined truth-table backfill to reduce proxy-heavy cross-run maturity"
    return "continue run-isolated paper evidence collection and keep reports compact"


def _read_memory_index_summary(paths: list[Path]) -> dict[str, Any]:
    sources: list[str] = []
    notes: list[str] = []
    for path in paths:
        sources.append(path.as_posix())
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            text = line.strip()
            if text.startswith("- ") and any(token in text.lower() for token in ("next", "gap", "hypothesis", "coverage")):
                notes.append(text[:220])
            if len(notes) >= 5:
                break
    return {"source_indexes": sources, "compact_notes": notes[:5]}


def build_research_state(
    *,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    memory_index_dir: str | Path = DEFAULT_MEMORY_INDEX_DIR,
    date: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    replay_item = _latest_report(report_dir=report_dir, prefix="replay_report_", date=date, run_id=run_id)
    truth_item = _latest_report(report_dir=report_dir, prefix="lifecycle_truth_tables_", date=date, run_id=run_id)
    cross_item = _latest_report(report_dir=report_dir, prefix="cross_run_lifecycle_truth_", date=date, run_id=None)
    memory_paths = _latest_memory_indexes(memory_index_dir=memory_index_dir, date=date, run_id=run_id)

    replay_path, replay = replay_item if replay_item else (None, {})
    truth_path, truth = truth_item if truth_item else (None, {})
    cross_path, cross = cross_item if cross_item else (None, {})
    source_reports = [path.as_posix() for path in (replay_path, truth_path, cross_path) if path is not None]

    phase2 = replay.get("phase2_coverage") if isinstance(replay.get("phase2_coverage"), dict) else {}
    aggregate = cross.get("aggregate") if isinstance(cross.get("aggregate"), dict) else {}
    direct_proxy = aggregate.get("direct_vs_proxy_evidence_trend") if isinstance(aggregate.get("direct_vs_proxy_evidence_trend"), dict) else {}
    blind_spots = _coverage_gaps(replay, truth)

    top_candidate_loss = _table_counts(truth)
    if not top_candidate_loss and isinstance(aggregate.get("repeated_candidate_loss_patterns"), dict):
        top_candidate_loss = _counter_from_pairs(aggregate.get("repeated_candidate_loss_patterns"))

    lifecycle_bottlenecks = _distribution(truth, "lifecycle_phase_distribution")
    if not lifecycle_bottlenecks:
        lifecycle_bottlenecks = _counter_from_pairs(cross.get("lifecycle_phase_failure_ranking"))

    ev_null = _distribution(truth, "ev_null_reason_distribution")
    if not ev_null and isinstance(aggregate.get("repeated_ev_null_reasons"), dict):
        ev_null = _counter_from_pairs(aggregate.get("repeated_ev_null_reasons"))

    direct_field_rate = _as_float(truth.get("direct_field_rate"), default=_as_float(direct_proxy.get("direct_field_rate_avg")))
    proxy_field_rate = _as_float(truth.get("proxy_field_rate"), default=_as_float(direct_proxy.get("proxy_field_rate_avg")))
    latest_run_id = _run_id(truth) or _run_id(replay) or str(cross.get("run_id_filter") or "")

    truth_state = {
        "generated_at_utc": _utc_now(),
        "scope": "offline_compact_research_state",
        "source_reports": source_reports,
        "latest_run_id": latest_run_id,
        "replay_truth_maturity": str(cross.get("replay_truth_maturity") or truth.get("replay_truth_quality") or "unknown"),
        "direct_field_maturity": str(cross.get("direct_field_maturity") or "unknown"),
        "latest_replay_confidence": str(truth.get("replay_truth_confidence") or replay.get("lifecycle_replay_confidence") or "unknown"),
        "direct_field_rate": round(direct_field_rate, 4),
        "proxy_field_rate": round(proxy_field_rate, 4),
        "unknown_lifecycle_rate": _unknown_lifecycle_rate(truth),
        "top_candidate_loss_reasons": _counter_from_pairs(top_candidate_loss),
        "top_lifecycle_bottlenecks": _counter_from_pairs(lifecycle_bottlenecks),
        "top_ev_null_reasons": _counter_from_pairs(ev_null),
        "current_blind_spots": blind_spots,
    }
    truth_state["current_recommended_next_step"] = _recommended_next_step(blind_spots, truth, cross)

    runtime_state = {
        "generated_at_utc": truth_state["generated_at_utc"],
        "scope": "offline_compact_runtime_research_state",
        "source_reports": source_reports[:2],
        "latest_run_id": latest_run_id,
        "phase2_status": str(phase2.get("status") or "unknown"),
        "latest_replay_confidence": truth_state["latest_replay_confidence"],
        "events_loaded": {
            "replay_report": _as_int(replay.get("events_loaded")),
            "truth_table": _as_int(truth.get("events_loaded")),
            "candidate_events": _as_int(truth.get("candidate_events")),
        },
        "top_candidate_loss_reasons": truth_state["top_candidate_loss_reasons"],
        "top_ev_null_reasons": truth_state["top_ev_null_reasons"],
        "current_blind_spots": blind_spots,
        "does_not_claim_profitability": True,
        "does_not_authorize_runtime_decisions": True,
    }

    return {
        "runtime_state": runtime_state,
        "truth_state": truth_state,
        "memory_index_summary": _read_memory_index_summary(memory_paths),
    }


def render_research_state_markdown(state: dict[str, Any]) -> str:
    truth = state["truth_state"]
    runtime = state["runtime_state"]
    memory = state["memory_index_summary"]

    def bullets(mapping: dict[str, int]) -> list[str]:
        if not mapping:
            return ["- none_observed"]
        return [f"- {key}: {value}" for key, value in list(mapping.items())[:5]]

    blind_spots = [f"- {item}" for item in truth.get("current_blind_spots", [])[:8]] or ["- none_reported"]
    source_reports = [f"- {path}" for path in truth.get("source_reports", [])[:6]] or ["- none"]
    memory_notes = [f"- {note.lstrip('- ')}" for note in memory.get("compact_notes", [])[:5]] or ["- none"]

    lines = [
        "# Latest Research State",
        "",
        f"generated_at: {truth['generated_at_utc']}",
        "scope: offline compact research memory",
        f"latest_run_id: {truth.get('latest_run_id') or 'unknown'}",
        f"replay_truth_maturity: {truth.get('replay_truth_maturity')}",
        f"direct_field_maturity: {truth.get('direct_field_maturity')}",
        f"latest_replay_confidence: {truth.get('latest_replay_confidence')}",
        f"direct_field_rate: {truth.get('direct_field_rate')}",
        f"proxy_field_rate: {truth.get('proxy_field_rate')}",
        f"unknown_lifecycle_rate: {truth.get('unknown_lifecycle_rate')}",
        "",
        "## Top Candidate Loss Reasons",
        *bullets(truth.get("top_candidate_loss_reasons", {})),
        "",
        "## Top Lifecycle Bottlenecks",
        *bullets(truth.get("top_lifecycle_bottlenecks", {})),
        "",
        "## Top EV Null Reasons",
        *bullets(truth.get("top_ev_null_reasons", {})),
        "",
        "## Current Blind Spots",
        *blind_spots,
        "",
        "## Recommended Next Step",
        f"- {truth.get('current_recommended_next_step')}",
        "",
        "## Runtime Evidence",
        f"- phase2_status: {runtime.get('phase2_status')}",
        f"- replay_events_loaded: {runtime.get('events_loaded', {}).get('replay_report')}",
        f"- truth_candidate_events: {runtime.get('events_loaded', {}).get('candidate_events')}",
        "- no profitability claim",
        "- no live readiness claim",
        "- no runtime decision authority",
        "",
        "## Source Reports",
        *source_reports,
        "",
        "## Research Memory Index Notes",
        *memory_notes,
        "",
        "Future Codex tasks should read this file before large reports unless raw evidence is explicitly required.",
        "",
    ]
    return "\n".join(lines)


def write_research_state(
    state: dict[str, Any],
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "runtime": output / "latest_runtime_state.json",
        "truth": output / "latest_truth_state.json",
        "markdown": output / "latest_research_state.md",
    }
    paths["runtime"].write_text(json.dumps(state["runtime_state"], indent=2, sort_keys=True), encoding="utf-8")
    paths["truth"].write_text(json.dumps(state["truth_state"], indent=2, sort_keys=True), encoding="utf-8")
    paths["markdown"].write_text(render_research_state_markdown(state), encoding="utf-8")
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write compact offline research state summaries.")
    parser.add_argument("--date", default=None, help="Optional YYYY-MM-DD report filter.")
    parser.add_argument("--run-id", default=None, help="Optional exact run_id filter for latest run state.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Source report directory.")
    parser.add_argument("--memory-index-dir", default=str(DEFAULT_MEMORY_INDEX_DIR), help="Research memory index directory.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Compact research-state output directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    state = build_research_state(
        report_dir=args.report_dir,
        memory_index_dir=args.memory_index_dir,
        date=args.date,
        run_id=args.run_id,
    )
    paths = write_research_state(state, output_dir=args.output_dir)
    print("Research State Writer")
    for name, path in paths.items():
        size = path.stat().st_size
        status = "ok" if size < COMPACT_SIZE_TARGET_BYTES else "over_target"
        print(f"{name}={path} bytes={size} size_target={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
