from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_REPORT_DIR = Path("runtime/reports")
DEFAULT_OUTPUT_DIR = Path("docs/research_memory")

RESEARCH_MEMORY_FOLDERS = (
    "replay_findings",
    "execution_microstructure",
    "index",
    "lifecycle_replay",
    "scanner_timing",
    "ev_null_reasons",
    "known_failures",
    "session_summaries",
)

NOTE_FOLDERS = tuple(folder for folder in RESEARCH_MEMORY_FOLDERS if folder != "index")

KNOWN_REPORT_TYPES = {
    "lifecycle_truth_tables": "lifecycle_truth",
    "replay_report": "replay",
    "no_entry_report": "no_entry",
    "session_runtime_evaluation": "session_runtime",
    "quant_data_quality": "quant_data_quality",
    "paper_evaluation": "paper_evaluation",
}


@dataclass
class SourceReport:
    path: Path
    report_type: str
    payload: dict[str, Any]


@dataclass
class ResearchMemoryBundle:
    date: str
    slug: str
    utc_window: str
    source_reports: list[SourceReport] = field(default_factory=list)

    def by_type(self) -> dict[str, dict[str, Any]]:
        return {report.report_type: report.payload for report in self.source_reports}

    def source_report_names(self) -> list[str]:
        return [report.path.as_posix() for report in self.source_reports]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"date must be YYYY-MM-DD; got {value!r}") from exc


def iter_date_strings(date_from: str, date_to: str) -> list[str]:
    start = _parse_date(date_from)
    end = _parse_date(date_to)
    if start > end:
        raise ValueError("--from must be earlier than or equal to --to")
    dates: list[str] = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _safe_filename_token(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    sanitized = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in text)
    return sanitized[:80] or "run"


def _report_run_id(payload: dict[str, Any]) -> str:
    run_id = payload.get("run_id")
    if run_id:
        return str(run_id)
    time_filter = payload.get("time_filter")
    if isinstance(time_filter, dict) and time_filter.get("run_id"):
        return str(time_filter.get("run_id"))
    return ""


def discover_report_run_ids(report_dir: str | Path, date: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for report in discover_source_reports(report_dir, date):
        run_id = _report_run_id(report.payload) or "missing_run_id"
        item = grouped.setdefault(
            run_id,
            {
                "run_id": run_id,
                "event_count": 0,
                "first_timestamp_utc": "",
                "last_timestamp_utc": "",
                "event_categories": set(),
                "modes": set(),
                "missing_run_id": run_id == "missing_run_id",
            },
        )
        count = (
            _as_int(report.payload.get("events_loaded"))
            or _as_int(report.payload.get("total_scanned"))
            or _as_int(report.payload.get("health_summary", {}).get("scanned") if isinstance(report.payload.get("health_summary"), dict) else 0)
            or 1
        )
        item["event_count"] += count
        item["event_categories"].add(report.report_type)
        mode = str(report.payload.get("mode") or "").strip()
        if mode:
            item["modes"].add(mode)
        time_filter = report.payload.get("time_filter")
        if isinstance(time_filter, dict):
            since_utc = str(time_filter.get("since_utc") or "").strip()
            until_utc = str(time_filter.get("until_utc") or "").strip()
            if since_utc and (not item["first_timestamp_utc"] or since_utc < item["first_timestamp_utc"]):
                item["first_timestamp_utc"] = since_utc
            if until_utc and until_utc > item["last_timestamp_utc"]:
                item["last_timestamp_utc"] = until_utc

    summaries: list[dict[str, Any]] = []
    for item in grouped.values():
        summaries.append({
            **item,
            "event_categories": sorted(item["event_categories"]),
            "modes": sorted(item["modes"]),
        })
    return sorted(summaries, key=lambda item: (item["missing_run_id"], item["first_timestamp_utc"], item["run_id"]))


def print_report_run_id_summary(summaries: list[dict[str, Any]]) -> None:
    print("Available report run IDs")
    if not summaries:
        print("(none)")
        return
    for summary in summaries:
        marker = " missing_run_id=true" if summary.get("missing_run_id") else ""
        categories = ",".join(summary.get("event_categories") or []) or "-"
        modes = ",".join(summary.get("modes") or []) or "-"
        print(
            "run_id={run_id}{marker} event_count={count} first={first} last={last} categories={categories} mode={modes}".format(
                run_id=summary.get("run_id"),
                marker=marker,
                count=summary.get("event_count", 0),
                first=summary.get("first_timestamp_utc") or "-",
                last=summary.get("last_timestamp_utc") or "-",
                categories=categories,
                modes=modes,
            )
        )


def _report_type(path: Path, payload: dict[str, Any]) -> str:
    name = path.name
    for prefix, report_type in KNOWN_REPORT_TYPES.items():
        if name.startswith(prefix):
            return report_type
    if "phase2_coverage" in payload and "events_loaded" in payload:
        return "replay"
    if "root_cause_category" in payload and "skip_reason_counts" in payload:
        return "no_entry"
    if "primary_bottleneck" in payload and "session_status" in payload:
        return "session_runtime"
    return "unknown"


def discover_source_reports(report_dir: str | Path, date: str, *, run_id: str | None = None) -> list[SourceReport]:
    reports: list[SourceReport] = []
    root = Path(report_dir)
    if not root.exists():
        return reports
    for path in sorted(root.glob(f"*{date}*.json")):
        if not path.is_file():
            continue
        payload = _load_json(path)
        if payload is None:
            continue
        report_type = _report_type(path, payload)
        if report_type == "unknown":
            continue
        if run_id and _report_run_id(payload) != run_id:
            continue
        reports.append(SourceReport(path=path, report_type=report_type, payload=payload))
    return reports


def _time_slug(value: Any, fallback: str) -> str:
    if value is None or str(value).strip() == "":
        return fallback
    return str(value).strip().replace(":", "")


def _filename_window(path: Path) -> tuple[str | None, str | None]:
    match = re.search(r"_(\d{4}|start)_to_(\d{4}|end)\.json$", path.name)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def _group_slug(date: str, report: SourceReport) -> str:
    time_filter = report.payload.get("time_filter")
    if isinstance(time_filter, dict) and time_filter.get("applied"):
        since = _time_slug(time_filter.get("since"), "start")
        until = _time_slug(time_filter.get("until"), "end")
        slug = f"{date}_{since}_to_{until}"
    else:
        since, until = _filename_window(report.path)
        if since or until:
            slug = f"{date}_{since or 'start'}_to_{until or 'end'}"
        else:
            slug = date
    safe_run_id = _safe_filename_token(_report_run_id(report.payload))
    if safe_run_id:
        slug = f"{slug}_run_{safe_run_id}"
    return slug


def _utc_window(date: str, reports: list[SourceReport]) -> str:
    for report in reports:
        time_filter = report.payload.get("time_filter")
        if not isinstance(time_filter, dict):
            continue
        display_range = time_filter.get("range")
        if display_range:
            return str(display_range)
        since_utc = time_filter.get("since_utc")
        until_utc = time_filter.get("until_utc")
        if since_utc or until_utc:
            return f"{since_utc or f'{date}T00:00:00Z'}..{until_utc or f'{date}T23:59:59Z'}"
    return f"{date}T00:00:00Z..{date}T23:59:59Z"


def group_reports_by_window(reports: list[SourceReport], date: str) -> list[ResearchMemoryBundle]:
    grouped: dict[str, dict[str, SourceReport]] = {}
    for report in reports:
        slug = _group_slug(date, report)
        grouped.setdefault(slug, {})
        current = grouped[slug].get(report.report_type)
        if current is None or report.path.stat().st_mtime >= current.path.stat().st_mtime:
            grouped[slug][report.report_type] = report

    bundles: list[ResearchMemoryBundle] = []
    for slug in sorted(grouped):
        source_reports = sorted(grouped[slug].values(), key=lambda item: item.path.name)
        bundles.append(
            ResearchMemoryBundle(
                date=date,
                slug=slug,
                utc_window=_utc_window(date, source_reports),
                source_reports=source_reports,
            )
        )
    return bundles


def _first_dict(reports: dict[str, dict[str, Any]], *paths: str) -> dict[str, Any]:
    for path in paths:
        report_name, _, key = path.partition(".")
        payload = reports.get(report_name)
        if not payload:
            continue
        value = payload.get(key) if key else payload
        if isinstance(value, dict):
            return value
    return {}


def _first_value(reports: dict[str, dict[str, Any]], *paths: str, default: Any = "") -> Any:
    for path in paths:
        current: Any = reports
        found = True
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                found = False
                break
        if found and current not in (None, ""):
            return current
    return default


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


def _pairs(value: Any, *, limit: int = 5) -> list[tuple[str, int | float | str]]:
    items: list[tuple[str, int | float | str]] = []
    if isinstance(value, dict):
        iterator = value.items()
    else:
        iterator = value or []
    for item in iterator:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            key, count = item[0], item[1]
        else:
            continue
        label = str(key or "UNKNOWN").strip() or "UNKNOWN"
        items.append((label, count))
    return items[:limit]


def _format_pairs(value: Any, *, limit: int = 5, empty: str = "Not reported in source evidence.") -> list[str]:
    pairs = _pairs(value, limit=limit)
    if not pairs:
        return [f"- {empty}"]
    return [f"- {label}: {count}" for label, count in pairs]


def _format_mapping(value: Any, *, limit: int = 5, empty: str = "Not reported in source evidence.") -> list[str]:
    if not isinstance(value, dict) or not value:
        return [f"- {empty}"]
    lines: list[str] = []
    for key, item in list(value.items())[:limit]:
        lines.append(f"- {key}: {item}")
    return lines or [f"- {empty}"]


def _coverage_lists(phase2: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    requirements = phase2.get("requirements")
    direct: list[str] = []
    proxy: list[str] = []
    gaps: list[str] = []
    if isinstance(requirements, dict):
        for key, payload in requirements.items():
            if not isinstance(payload, dict):
                continue
            status = str(payload.get("status") or "")
            inference = str(payload.get("inference") or "")
            if status == "coverage_gap":
                gaps.append(str(key))
            elif status == "proxy_inferred" or inference == "proxy_inferred":
                proxy.append(str(key))
            elif status == "available" or inference == "direct_observed":
                direct.append(str(key))
    else:
        proxy = [str(item) for item in phase2.get("proxy_inferred_items", [])]
        gaps = [str(item) for item in phase2.get("coverage_gaps", [])]
    return direct, proxy, gaps


def _best_phase2(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return _first_dict(
        reports,
        "session_runtime.phase2_coverage",
        "session_runtime.inventory_replay_readiness",
        "replay.phase2_coverage",
        "no_entry.phase2_coverage",
    )


def _best_partial_replay(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return _first_dict(
        reports,
        "session_runtime.partial_lifecycle_replay",
        "replay.partial_lifecycle_replay",
        "no_entry.partial_lifecycle_replay",
    )


def _best_lifecycle_truth(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    truth = reports.get("lifecycle_truth")
    return truth if isinstance(truth, dict) else {}


def _truth_table_counts(truth: dict[str, Any]) -> dict[str, int]:
    tables = truth.get("tables")
    if not isinstance(tables, dict):
        return {}
    names = (
        "starter_candidates",
        "missed_starter_candidates",
        "candidate_blocked_before_ev",
        "candidate_blocked_after_ev",
        "time_unsafe_candidates",
        "liquidity_or_orderbook_blocked_candidates",
    )
    counts: dict[str, int] = {}
    for name in names:
        value = tables.get(name)
        counts[name] = len(value) if isinstance(value, list) else 0
    return counts


def _truth_distribution(truth: dict[str, Any], table_name: str) -> dict[str, int]:
    tables = truth.get("tables")
    if not isinstance(tables, dict):
        return {}
    table = tables.get(table_name)
    if isinstance(table, dict) and isinstance(table.get("counts"), dict):
        return {str(key): _as_int(value) for key, value in table["counts"].items()}
    if isinstance(table, dict):
        return {str(key): _as_int(value) for key, value in table.items() if isinstance(value, (int, float))}
    return {}


def _lifecycle_truth_blind_spots(truth: dict[str, Any]) -> list[str]:
    if not truth:
        return ["lifecycle_truth_tables_report_missing"]
    blind_spots: list[str] = []
    quality = str(truth.get("replay_truth_quality") or "")
    confidence = str(truth.get("replay_truth_confidence") or "")
    direct_rate = _as_float(truth.get("direct_field_rate"), default=0.0)
    proxy_rate = _as_float(truth.get("proxy_field_rate"), default=0.0)
    counts = _truth_table_counts(truth)
    completeness = truth.get("evidence_completeness")
    gaps = completeness.get("coverage_gaps") if isinstance(completeness, dict) else []

    if "PROXY" in quality or "PROXY" in confidence or proxy_rate > direct_rate:
        blind_spots.append("proxy_heavy_truth_tables")
    if direct_rate <= 0:
        blind_spots.append("no_direct_truth_fields_observed")
    if counts.get("starter_candidates", 0) == 0:
        blind_spots.append("no_starter_candidate_truth_rows")
    if counts.get("missed_starter_candidates", 0) == 0:
        blind_spots.append("no_missed_starter_truth_rows")
    if isinstance(gaps, list):
        blind_spots.extend(str(item) for item in gaps[:6])
    return list(dict.fromkeys(blind_spots)) or ["None reported in source evidence."]


def _lifecycle_truth_summary_lines(reports: dict[str, dict[str, Any]], *, indent: str = "- ") -> list[str]:
    truth = _best_lifecycle_truth(reports)
    if not truth:
        return [f"{indent}lifecycle_truth_tables: Not reported in source evidence."]

    sub_indent = "  - " if indent == "- " else "    - "
    counts = _truth_table_counts(truth)
    lines = [
        f"{indent}replay_truth_confidence: {truth.get('replay_truth_confidence', 'Not reported')}",
        f"{indent}replay_truth_quality: {truth.get('replay_truth_quality', 'Not reported')}",
        f"{indent}truth_label: {'proxy_heavy_truth' if 'PROXY' in str(truth.get('replay_truth_quality') or truth.get('replay_truth_confidence') or '') else 'direct_or_partial_truth'}",
        f"{indent}direct_field_rate: {truth.get('direct_field_rate', 'Not reported')}",
        f"{indent}proxy_field_rate: {truth.get('proxy_field_rate', 'Not reported')}",
        f"{indent}candidate_events: {truth.get('candidate_events', 'Not reported')}",
    ]
    for name in (
        "starter_candidates",
        "missed_starter_candidates",
        "candidate_blocked_before_ev",
        "candidate_blocked_after_ev",
        "time_unsafe_candidates",
        "liquidity_or_orderbook_blocked_candidates",
    ):
        lines.append(f"{indent}{name}: {counts.get(name, 0)}")

    lines.append(f"{indent}lifecycle_phase_distribution:")
    phase_counts = _truth_distribution(truth, "lifecycle_phase_distribution")
    lines.extend(_sorted_counter_lines(phase_counts, limit=6, indent=sub_indent))
    lines.append(f"{indent}ev_null_reason_distribution:")
    ev_counts = _truth_distribution(truth, "ev_null_reason_distribution")
    lines.extend(_sorted_counter_lines(ev_counts, limit=6, indent=sub_indent))
    lines.append(f"{indent}remaining_blind_spots:")
    lines.extend(f"{sub_indent}{item}" for item in _lifecycle_truth_blind_spots(truth)[:8])
    return lines


def _evidence_quality(reports: dict[str, dict[str, Any]]) -> str:
    phase2 = _best_phase2(reports)
    status = str(phase2.get("status") or "")
    gaps = phase2.get("coverage_gaps", [])
    gap_count = _as_int(phase2.get("coverage_gap_count"), default=len(gaps) if isinstance(gaps, list) else 0)
    events = (
        _as_int(_first_value(reports, "replay.events_loaded", default=0))
        + _as_int(_first_value(reports, "no_entry.total_scanned", default=0))
        + _as_int(_first_value(reports, "session_runtime.health_summary.scanned", default=0))
    )
    if not reports or events == 0:
        return "INSUFFICIENT_EVIDENCE"
    if status == "READY_FOR_PHASE2_REPLAY_RESEARCH" and gap_count == 0:
        return "READY_RESEARCH_EVIDENCE"
    if status or gap_count:
        return "PARTIAL_OR_PROXY_EVIDENCE"
    return "REPORTS_PRESENT_WITH_LIMITED_PHASE2_EVIDENCE"


def _metadata_lines(bundle: ResearchMemoryBundle, generated_at: str, reports: dict[str, dict[str, Any]]) -> list[str]:
    replay_confidence = _first_value(
        reports,
        "session_runtime.lifecycle_replay_confidence",
        "replay.lifecycle_replay_confidence",
        "no_entry.lifecycle_replay_confidence",
        default="Not reported",
    )
    lines = [
        "## Metadata",
        f"- generated_at: {generated_at}",
        f"- session_date: {bundle.date}",
        f"- utc_window: {bundle.utc_window}",
        f"- replay_confidence: {replay_confidence}",
        f"- evidence_quality: {_evidence_quality(reports)}",
        "- source_reports:",
    ]
    lines.extend(f"  - {name}" for name in bundle.source_report_names())
    return lines


def _phase2_lines(reports: dict[str, dict[str, Any]]) -> list[str]:
    phase2 = _best_phase2(reports)
    direct, proxy, gaps = _coverage_lists(phase2)
    lines = [
        f"- phase2_status: {phase2.get('status', 'Not reported') if phase2 else 'Not reported'}",
        f"- coverage_gap_count: {_as_int(phase2.get('coverage_gap_count'), default=len(gaps)) if phase2 else 'Not reported'}",
        "- direct_observed:",
    ]
    lines.extend([f"  - {item}" for item in direct[:8]] or ["  - Not reported in source evidence."])
    lines.append("- proxy_inferred:")
    lines.extend([f"  - {item}" for item in proxy[:8]] or ["  - None reported."])
    lines.append("- coverage_gap:")
    lines.extend([f"  - {item}" for item in gaps[:8]] or ["  - None reported."])
    return lines


def _ev_null_lines(reports: dict[str, dict[str, Any]]) -> list[str]:
    phase2 = _best_phase2(reports)
    nulls = phase2.get("ev_null_reason_coverage") if isinstance(phase2, dict) else None
    if not isinstance(nulls, dict):
        return ["- EV/fair-value null reason coverage was not reported in source evidence."]
    lines = [
        f"- status: {nulls.get('status', 'Not reported')}",
        f"- events_checked: {nulls.get('events_checked', 'Not reported')}",
        f"- null_reason_coverage_rate: {nulls.get('null_reason_coverage_rate', 'Not reported')}",
        "- top_null_reasons:",
    ]
    lines.extend(f"  - {label}: {count}" for label, count in _pairs(nulls.get("null_reasons"), limit=6))
    if len(lines) == 4:
        lines.append("  - Not reported in source evidence.")
    lines.append("- probability_model_stages:")
    lines.extend(f"  - {label}: {count}" for label, count in _pairs(nulls.get("probability_model_stages"), limit=4))
    lines.append("- ev_calculation_stages:")
    lines.extend(f"  - {label}: {count}" for label, count in _pairs(nulls.get("ev_calculation_stages"), limit=4))
    return lines


def _missed_starter_lines(reports: dict[str, dict[str, Any]], *, limit: int = 5) -> list[str]:
    candidates = _first_value(
        reports,
        "session_runtime.missed_starter_candidates",
        "replay.missed_starter_candidates",
        "no_entry.missed_starter_candidates",
        default=[],
    )
    if not isinstance(candidates, list) or not candidates:
        return ["- No missed starter candidates reported in source evidence."]
    lines: list[str] = []
    for candidate in candidates[:limit]:
        if not isinstance(candidate, dict):
            continue
        label = candidate.get("candidate_key") or candidate.get("candidate_id") or "unknown_candidate"
        market = candidate.get("market_key") or candidate.get("market_id") or candidate.get("asset") or "UNKNOWN"
        seconds = candidate.get("seconds_remaining", "unknown")
        reason = candidate.get("skip_reason", "unknown")
        inference = candidate.get("starter_replay_inference", "unknown")
        phase = candidate.get("lifecycle_phase", "unknown")
        lines.append(
            f"- {label}: market={market}, seconds_remaining={seconds}, phase={phase}, "
            f"skip_reason={reason}, inference={inference}"
        )
    return lines or ["- No missed starter candidates reported in source evidence."]


def _quant_interpretation_lines(reports: dict[str, dict[str, Any]]) -> list[str]:
    primary = _first_value(reports, "session_runtime.primary_bottleneck", default="")
    evidence_quality = _evidence_quality(reports)
    phase2_status = _best_phase2(reports).get("status", "Not reported") if _best_phase2(reports) else "Not reported"
    lines = [
        f"- Evidence quality: {evidence_quality}.",
        f"- Phase 2 status from reports: {phase2_status}.",
        "- This note is research memory only and does not claim profitability, live readiness, or runtime permission.",
    ]
    if primary:
        lines.insert(1, f"- Dominant reported bottleneck: {primary}.")
    return lines


def _future_investigation_lines(reports: dict[str, dict[str, Any]]) -> list[str]:
    recommendations = _first_value(reports, "session_runtime.recommendations", "no_entry.recommendations", default=[])
    if isinstance(recommendations, list) and recommendations:
        return [f"- {item}" for item in recommendations[:3]]
    return ["- Collect additional paper-session reports before drawing stronger lifecycle replay conclusions."]


def _missed_starter_count(reports: dict[str, dict[str, Any]]) -> int:
    candidates = _first_value(
        reports,
        "session_runtime.missed_starter_candidates",
        "replay.missed_starter_candidates",
        "no_entry.missed_starter_candidates",
        default=[],
    )
    return len(candidates) if isinstance(candidates, list) else 0


def _top_ev_null_reason_lines(reports: dict[str, dict[str, Any]], *, limit: int = 3) -> list[str]:
    phase2 = _best_phase2(reports)
    nulls = phase2.get("ev_null_reason_coverage") if isinstance(phase2, dict) else None
    if not isinstance(nulls, dict):
        return ["  - Not reported in source evidence."]
    pairs = _pairs(nulls.get("null_reasons"), limit=limit)
    return [f"  - {label}: {count}" for label, count in pairs] or ["  - None reported."]


def _timing_liquidity_bottleneck_lines(reports: dict[str, dict[str, Any]], *, limit: int = 5) -> list[str]:
    lines: list[str] = []
    session = reports.get("session_runtime", {})
    no_entry = reports.get("no_entry", {})
    partial = _best_partial_replay(reports)
    spread_liquidity = partial.get("spread_liquidity_readiness_summary") if isinstance(partial, dict) else {}

    primary = session.get("primary_bottleneck")
    secondary = session.get("secondary_bottleneck")
    if primary:
        lines.append(f"  - primary_bottleneck: {primary}")
    if secondary and secondary != primary:
        lines.append(f"  - secondary_bottleneck: {secondary}")

    score_map = session.get("bottleneck_scores")
    if isinstance(score_map, dict):
        selected = {
            key: value
            for key, value in score_map.items()
            if key in {"cutoff", "latency", "market_readiness", "stale_data"} and _as_int(value) > 0
        }
        for key, value in sorted(selected.items(), key=lambda item: _as_int(item[1]), reverse=True):
            lines.append(f"  - {key}: {value}")

    timing_or_liquidity_reasons = []
    for reason, count in _pairs(no_entry.get("top_skip_reasons"), limit=10):
        text = reason.lower()
        if any(token in text for token in ("time", "cutoff", "warmup", "orderbook", "empty_book", "liquidity", "spread", "stale", "latency")):
            timing_or_liquidity_reasons.append((reason, count))
    for reason, count in timing_or_liquidity_reasons[:limit]:
        lines.append(f"  - skip_reason:{reason}: {count}")

    if isinstance(spread_liquidity, dict):
        for state, count in _pairs(spread_liquidity.get("liquidity_states"), limit=3):
            if str(state).upper() not in {"HEALTHY", "READY"}:
                lines.append(f"  - liquidity_state:{state}: {count}")
        for reason, count in _pairs(spread_liquidity.get("orderbook_readiness_reasons"), limit=3):
            lines.append(f"  - orderbook_readiness:{reason}: {count}")

    return list(dict.fromkeys(lines))[:limit] or ["  - Not reported in source evidence."]


def _note_link_lines(slug: str) -> list[str]:
    return [
        f"- [Session Summary](../session_summaries/{slug}.md)",
        f"- [Replay Findings](../replay_findings/{slug}.md)",
        f"- [Execution Microstructure](../execution_microstructure/{slug}.md)",
        f"- [Lifecycle Replay](../lifecycle_replay/{slug}.md)",
        f"- [Scanner Timing](../scanner_timing/{slug}.md)",
        f"- [EV Null Reasons](../ev_null_reasons/{slug}.md)",
        f"- [Known Failures](../known_failures/{slug}.md)",
    ]


def _command_run_id_arg(run_id: str | None) -> str:
    return f" --run-id {run_id}" if run_id else ""


def _daily_reproduce_lines(date: str, run_id: str | None = None) -> list[str]:
    run_arg = _command_run_id_arg(run_id)
    return [
        f"- replay: `python -m tools.replay_analyzer --date {date}{run_arg}`",
        f"- no_entry: `python -m tools.research.no_entry_analyzer --date {date}{run_arg} --write-report`",
        f"- session_eval: `python -m tools.runtime.session_runtime_evaluator --date {date}{run_arg} --write-report --verbose`",
        f"- memory: `python -m tools.research.research_memory_writer --date {date}{run_arg} --write-index`",
    ]


def _range_reproduce_lines(date_from: str, date_to: str, run_id: str | None = None) -> list[str]:
    run_arg = _command_run_id_arg(run_id)
    return [
        f"- replay: `python -m tools.replay_analyzer --from {date_from} --to {date_to}{run_arg}`",
        f"- no_entry: run per date with `python -m tools.research.no_entry_analyzer --date YYYY-MM-DD{run_arg} --write-report`",
        f"- session_eval: run per date with `python -m tools.runtime.session_runtime_evaluator --date YYYY-MM-DD{run_arg} --write-report --verbose`",
        f"- memory: `python -m tools.research.research_memory_writer --from {date_from} --to {date_to}{run_arg} --write-index`",
    ]


def _notebooklm_note_lines() -> list[str]:
    return [
        "- Upload this index plus the linked topic notes for NotebookLM ingestion.",
        "- Treat this file as evidence navigation only; source report JSON paths below are the audit trail.",
        "- Do not use the index as a profitability, live-readiness, strategy, risk, or execution approval.",
    ]


def _source_report_lines(bundle: ResearchMemoryBundle) -> list[str]:
    names = bundle.source_report_names()
    return [f"  - {name}" for name in names] or ["  - Not reported in source evidence."]


def _index_markdown(date: str, bundles: list[ResearchMemoryBundle], generated_at: str, *, run_id: str | None = None) -> str:
    lines = [
        f"# Daily Research Memory Index - {date}",
        "",
        "## Metadata",
        f"- generated_at: {generated_at}",
        f"- session_date: {date}",
        f"- run_id: {run_id or 'not_filtered'}",
        f"- windows_indexed: {len(bundles)}",
        "- scope: offline research memory only",
        "- guardrail: no profitability, live-readiness, strategy, risk, or execution claims",
        "",
        "## Reproduce",
    ]
    lines.extend(_daily_reproduce_lines(date, run_id))
    lines.extend([
        "",
        "## NotebookLM Ingestion Note",
    ])
    lines.extend(_notebooklm_note_lines())
    lines.extend([
        "",
    ]
    )
    if not bundles:
        lines.extend([
            "## Windows",
            "- No matching report JSON found for this date.",
            "",
        ])
        return "\n".join(lines)

    for bundle in bundles:
        reports = bundle.by_type()
        phase2 = _best_phase2(reports)
        direct, proxy, gaps = _coverage_lists(phase2)
        replay_confidence = _first_value(
            reports,
            "session_runtime.lifecycle_replay_confidence",
            "replay.lifecycle_replay_confidence",
            "no_entry.lifecycle_replay_confidence",
            default="Not reported",
        )
        lines.extend([
            f"## Window {bundle.slug}",
            f"- utc_window: {bundle.utc_window}",
            f"- phase2_status: {phase2.get('status', 'Not reported') if phase2 else 'Not reported'}",
            f"- replay_confidence: {replay_confidence}",
            f"- evidence_quality: {_evidence_quality(reports)}",
            f"- missed_starter_count: {_missed_starter_count(reports)}",
            "- generated_notes:",
        ])
        lines.extend(f"  {line}" for line in _note_link_lines(bundle.slug))
        lines.append("- source_reports:")
        lines.extend(_source_report_lines(bundle))
        lines.append("- top_ev_null_reasons:")
        lines.extend(_top_ev_null_reason_lines(reports))
        lines.append("- top_timing_liquidity_bottlenecks:")
        lines.extend(_timing_liquidity_bottleneck_lines(reports))
        lines.append("- lifecycle_truth_table_summary:")
        lines.extend(_lifecycle_truth_summary_lines(reports, indent="  - "))
        lines.extend([
            "- direct_observed:",
        ])
        lines.extend([f"  - {item}" for item in direct[:6]] or ["  - Not reported in source evidence."])
        lines.append("- proxy_inferred:")
        lines.extend([f"  - {item}" for item in proxy[:6]] or ["  - None reported."])
        lines.append("- coverage_gap:")
        lines.extend([f"  - {item}" for item in gaps[:6]] or ["  - None reported."])
        lines.append("- recommended_next_investigation:")
        recommendations = _future_investigation_lines(reports)
        lines.extend(f"  {item}" for item in recommendations[:2])
        lines.append("")
    return "\n".join(lines)


def _add_pairs(counter: dict[str, int], value: Any, *, limit: int = 20) -> None:
    for label, count in _pairs(value, limit=limit):
        counter[label] = counter.get(label, 0) + _as_int(count, default=1)


def _sorted_counter_lines(counter: dict[str, int], *, limit: int = 8, indent: str = "- ") -> list[str]:
    if not counter:
        return [f"{indent}None reported."]
    items = sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return [f"{indent}{label}: {count}" for label, count in items]


def _bundle_timing_liquidity_counter(reports: dict[str, dict[str, Any]]) -> dict[str, int]:
    counter: dict[str, int] = {}
    for line in _timing_liquidity_bottleneck_lines(reports, limit=10):
        text = line.strip()
        if not text.startswith("- "):
            continue
        text = text[2:]
        label, _, count_text = text.rpartition(": ")
        label = label or text
        count = _as_int(count_text, default=0)
        if count == 0:
            label = text
            count = 1
        counter[label] = counter.get(label, 0) + count
    return counter


def _recurring_root_cause_hypothesis(
    *,
    ev_null_reasons: dict[str, int],
    timing_liquidity: dict[str, int],
    coverage_gaps: dict[str, int],
    root_causes: dict[str, int],
) -> str:
    if not any((ev_null_reasons, timing_liquidity, coverage_gaps, root_causes)):
        return "insufficient_repeated_evidence"

    top_root = max(root_causes.items(), key=lambda item: item[1])[0] if root_causes else ""
    if top_root and root_causes.get(top_root, 0) >= 2:
        return f"repeated_reported_root_cause:{top_root}"

    timing_score = sum(
        count
        for label, count in timing_liquidity.items()
        if any(token in label.lower() for token in ("cutoff", "time", "latency", "orderbook", "liquidity", "spread", "stale"))
    )
    if timing_score >= 2:
        return "repeated_timing_liquidity_or_orderbook_bottleneck"

    top_ev = max(ev_null_reasons.items(), key=lambda item: item[1])[0] if ev_null_reasons else ""
    if top_ev:
        return f"repeated_ev_null_reason:{top_ev}"

    if coverage_gaps:
        top_gap = max(coverage_gaps.items(), key=lambda item: item[1])[0]
        return f"repeated_coverage_gap:{top_gap}"

    return "mixed_or_insufficient_repeated_pattern"


def _multi_day_index_markdown(
    *,
    date_from: str,
    date_to: str,
    bundles_by_date: dict[str, list[ResearchMemoryBundle]],
    generated_at: str,
    run_id: str | None = None,
) -> str:
    all_bundles = [bundle for bundles in bundles_by_date.values() for bundle in bundles]
    ev_null_reasons: dict[str, int] = {}
    timing_liquidity: dict[str, int] = {}
    direct_counter: dict[str, int] = {}
    proxy_counter: dict[str, int] = {}
    gap_counter: dict[str, int] = {}
    phase2_status_counter: dict[str, int] = {}
    root_cause_counter: dict[str, int] = {}
    truth_confidence_counter: dict[str, int] = {}
    truth_quality_counter: dict[str, int] = {}
    truth_table_totals: dict[str, int] = {}
    truth_phase_distribution: dict[str, int] = {}
    truth_ev_null_distribution: dict[str, int] = {}
    truth_blind_spots: dict[str, int] = {}
    truth_direct_rates: list[float] = []
    truth_proxy_rates: list[float] = []
    truth_candidate_events = 0
    missed_starter_total = 0

    for bundle in all_bundles:
        reports = bundle.by_type()
        phase2 = _best_phase2(reports)
        status = str(phase2.get("status") or "Not reported")
        phase2_status_counter[status] = phase2_status_counter.get(status, 0) + 1
        direct, proxy, gaps = _coverage_lists(phase2)
        for item in direct:
            direct_counter[item] = direct_counter.get(item, 0) + 1
        for item in proxy:
            proxy_counter[item] = proxy_counter.get(item, 0) + 1
        for item in gaps:
            gap_counter[item] = gap_counter.get(item, 0) + 1
        nulls = phase2.get("ev_null_reason_coverage") if isinstance(phase2, dict) else {}
        if isinstance(nulls, dict):
            _add_pairs(ev_null_reasons, nulls.get("null_reasons"), limit=20)
        for label, count in _bundle_timing_liquidity_counter(reports).items():
            timing_liquidity[label] = timing_liquidity.get(label, 0) + count
        no_entry = reports.get("no_entry", {})
        root = str(no_entry.get("root_cause_category") or "")
        if root:
            root_cause_counter[root] = root_cause_counter.get(root, 0) + 1
        missed_starter_total += _missed_starter_count(reports)
        truth = _best_lifecycle_truth(reports)
        if truth:
            confidence = str(truth.get("replay_truth_confidence") or "Not reported")
            quality = str(truth.get("replay_truth_quality") or "Not reported")
            truth_confidence_counter[confidence] = truth_confidence_counter.get(confidence, 0) + 1
            truth_quality_counter[quality] = truth_quality_counter.get(quality, 0) + 1
            truth_candidate_events += _as_int(truth.get("candidate_events"))
            truth_direct_rates.append(_as_float(truth.get("direct_field_rate")))
            truth_proxy_rates.append(_as_float(truth.get("proxy_field_rate")))
            for label, count in _truth_table_counts(truth).items():
                truth_table_totals[label] = truth_table_totals.get(label, 0) + count
            for label, count in _truth_distribution(truth, "lifecycle_phase_distribution").items():
                truth_phase_distribution[label] = truth_phase_distribution.get(label, 0) + count
            for label, count in _truth_distribution(truth, "ev_null_reason_distribution").items():
                truth_ev_null_distribution[label] = truth_ev_null_distribution.get(label, 0) + count
            for label in _lifecycle_truth_blind_spots(truth):
                truth_blind_spots[label] = truth_blind_spots.get(label, 0) + 1

    hypothesis = _recurring_root_cause_hypothesis(
        ev_null_reasons=ev_null_reasons,
        timing_liquidity=timing_liquidity,
        coverage_gaps=gap_counter,
        root_causes=root_cause_counter,
    )

    lines = [
        f"# Multi-Day Research Memory Index - {date_from}_to_{date_to}",
        "",
        "## Metadata",
        f"- generated_at: {generated_at}",
        f"- date_range: {date_from}..{date_to}",
        f"- run_id: {run_id or 'not_filtered'}",
        f"- dates_included: {len(bundles_by_date)}",
        f"- windows_included: {len(all_bundles)}",
        "- scope: offline research memory only",
        "- guardrail: no profitability, live-readiness, strategy, risk, or execution claims",
        "",
        "## Reproduce",
    ]
    lines.extend(_range_reproduce_lines(date_from, date_to, run_id))
    lines.extend([
        "",
        "## NotebookLM Ingestion Note",
    ])
    lines.extend(_notebooklm_note_lines())
    lines.extend([
        "",
        "## Dates And Windows Included",
    ]
    )
    if not all_bundles:
        lines.append("- No matching report JSON found for this date range.")
    else:
        for date in sorted(bundles_by_date):
            bundles = bundles_by_date[date]
            if not bundles:
                lines.append(f"- {date}: no matching report JSON")
                continue
            lines.append(f"- {date}: {len(bundles)} window(s)")
            for bundle in bundles:
                lines.append(f"  - {bundle.slug}: {bundle.utc_window}")
                lines.append("    source_reports:")
                lines.extend(f"      - {name}" for name in bundle.source_report_names())

    lines.extend([
        "",
        "## Repeated EV-Null Reasons",
    ])
    lines.extend(_sorted_counter_lines(ev_null_reasons))
    lines.extend([
        "",
        "## Repeated Timing/Liquidity Bottlenecks",
    ])
    lines.extend(_sorted_counter_lines(timing_liquidity))
    lines.extend([
        "",
        "## Missed Starter Totals",
        f"- missed_starter_total: {missed_starter_total}",
        "",
        "## Phase2 Readiness Trend",
    ])
    lines.extend(_sorted_counter_lines(phase2_status_counter))
    lines.extend([
        "",
        "## Direct vs Proxy Evidence Trend",
        "- direct_observed:",
    ])
    lines.extend(_sorted_counter_lines(direct_counter, indent="  - "))
    lines.append("- proxy_inferred:")
    lines.extend(_sorted_counter_lines(proxy_counter, indent="  - "))
    lines.extend([
        "",
        "## Lifecycle Truth Table Trend",
        f"- truth_reports_included: {sum(truth_confidence_counter.values())}",
        f"- candidate_events: {truth_candidate_events}",
        f"- direct_field_rate_avg: {round(sum(truth_direct_rates) / len(truth_direct_rates), 4) if truth_direct_rates else 'Not reported'}",
        f"- proxy_field_rate_avg: {round(sum(truth_proxy_rates) / len(truth_proxy_rates), 4) if truth_proxy_rates else 'Not reported'}",
        "- replay_truth_confidence:",
    ])
    lines.extend(_sorted_counter_lines(truth_confidence_counter, indent="  - "))
    lines.append("- replay_truth_quality:")
    lines.extend(_sorted_counter_lines(truth_quality_counter, indent="  - "))
    lines.append("- truth_table_counts:")
    lines.extend(_sorted_counter_lines(truth_table_totals, indent="  - "))
    lines.append("- lifecycle_phase_distribution:")
    lines.extend(_sorted_counter_lines(truth_phase_distribution, indent="  - "))
    lines.append("- ev_null_reason_distribution:")
    lines.extend(_sorted_counter_lines(truth_ev_null_distribution, indent="  - "))
    lines.append("- remaining_blind_spots:")
    lines.extend(_sorted_counter_lines(truth_blind_spots, indent="  - "))
    lines.extend([
        "",
        "## Coverage Gaps Across Days",
    ])
    lines.extend(_sorted_counter_lines(gap_counter))
    lines.extend([
        "",
        "## Recurring Root-Cause Hypothesis",
        f"- hypothesis: {hypothesis}",
        "- confidence: evidence_index_only",
        "- guardrail: hypothesis summarizes repeated report fields and does not authorize runtime changes.",
        "",
        "## Recommended Next Investigation",
    ])
    if gap_counter:
        top_gap = sorted(gap_counter.items(), key=lambda item: (-item[1], item[0]))[0][0]
        lines.append(f"- Review repeated coverage gap `{top_gap}` before using the range for stronger lifecycle replay conclusions.")
    elif timing_liquidity:
        top_bottleneck = sorted(timing_liquidity.items(), key=lambda item: (-item[1], item[0]))[0][0]
        lines.append(f"- Compare repeated timing/liquidity bottleneck `{top_bottleneck}` by date/window before changing runtime policy.")
    elif ev_null_reasons:
        top_reason = sorted(ev_null_reasons.items(), key=lambda item: (-item[1], item[0]))[0][0]
        lines.append(f"- Review repeated EV-null reason `{top_reason}` against source reports before drawing model conclusions.")
    else:
        lines.append("- Collect additional dated report JSON before drawing cross-session conclusions.")
    lines.append("")
    return "\n".join(lines)


def _bundle_event_count(bundle: ResearchMemoryBundle) -> int:
    reports = bundle.by_type()
    return max(
        _as_int(reports.get("replay", {}).get("events_loaded")),
        _as_int(reports.get("no_entry", {}).get("total_scanned")),
        _as_int(reports.get("session_runtime", {}).get("health_summary", {}).get("scanned") if isinstance(reports.get("session_runtime", {}).get("health_summary"), dict) else 0),
        0,
    )


def _run_summary(run_id: str, bundles: list[ResearchMemoryBundle]) -> dict[str, Any]:
    ev_null_reasons: dict[str, int] = {}
    timing_liquidity: dict[str, int] = {}
    direct_counter: dict[str, int] = {}
    proxy_counter: dict[str, int] = {}
    gap_counter: dict[str, int] = {}
    phase2_status_counter: dict[str, int] = {}
    root_cause_counter: dict[str, int] = {}
    truth_confidence_counter: dict[str, int] = {}
    truth_quality_counter: dict[str, int] = {}
    truth_table_totals: dict[str, int] = {}
    truth_phase_distribution: dict[str, int] = {}
    truth_ev_null_distribution: dict[str, int] = {}
    truth_blind_spots: dict[str, int] = {}
    truth_direct_rates: list[float] = []
    truth_proxy_rates: list[float] = []
    truth_candidate_events = 0
    source_reports: list[str] = []
    utc_windows: list[str] = []
    event_count = 0
    missed_starter_count = 0

    for bundle in bundles:
        reports = bundle.by_type()
        event_count += _bundle_event_count(bundle)
        missed_starter_count += _missed_starter_count(reports)
        utc_windows.append(bundle.utc_window)
        source_reports.extend(bundle.source_report_names())
        phase2 = _best_phase2(reports)
        phase2_status = str(phase2.get("status") or "Not reported")
        phase2_status_counter[phase2_status] = phase2_status_counter.get(phase2_status, 0) + 1
        direct, proxy, gaps = _coverage_lists(phase2)
        for item in direct:
            direct_counter[item] = direct_counter.get(item, 0) + 1
        for item in proxy:
            proxy_counter[item] = proxy_counter.get(item, 0) + 1
        for item in gaps:
            gap_counter[item] = gap_counter.get(item, 0) + 1
        nulls = phase2.get("ev_null_reason_coverage") if isinstance(phase2, dict) else {}
        if isinstance(nulls, dict):
            _add_pairs(ev_null_reasons, nulls.get("null_reasons"), limit=20)
        for label, count in _bundle_timing_liquidity_counter(reports).items():
            timing_liquidity[label] = timing_liquidity.get(label, 0) + count
        no_entry = reports.get("no_entry", {})
        root = str(no_entry.get("root_cause_category") or "")
        if root:
            root_cause_counter[root] = root_cause_counter.get(root, 0) + 1
        truth = _best_lifecycle_truth(reports)
        if truth:
            confidence = str(truth.get("replay_truth_confidence") or "Not reported")
            quality = str(truth.get("replay_truth_quality") or "Not reported")
            truth_confidence_counter[confidence] = truth_confidence_counter.get(confidence, 0) + 1
            truth_quality_counter[quality] = truth_quality_counter.get(quality, 0) + 1
            truth_candidate_events += _as_int(truth.get("candidate_events"))
            truth_direct_rates.append(_as_float(truth.get("direct_field_rate")))
            truth_proxy_rates.append(_as_float(truth.get("proxy_field_rate")))
            for label, count in _truth_table_counts(truth).items():
                truth_table_totals[label] = truth_table_totals.get(label, 0) + count
            for label, count in _truth_distribution(truth, "lifecycle_phase_distribution").items():
                truth_phase_distribution[label] = truth_phase_distribution.get(label, 0) + count
            for label, count in _truth_distribution(truth, "ev_null_reason_distribution").items():
                truth_ev_null_distribution[label] = truth_ev_null_distribution.get(label, 0) + count
            for label in _lifecycle_truth_blind_spots(truth):
                truth_blind_spots[label] = truth_blind_spots.get(label, 0) + 1

    return {
        "run_id": run_id,
        "missing_run_id": run_id == "missing_run_id",
        "bundles": bundles,
        "utc_windows": utc_windows,
        "event_count": event_count,
        "missed_starter_count": missed_starter_count,
        "ev_null_reasons": ev_null_reasons,
        "timing_liquidity": timing_liquidity,
        "direct": direct_counter,
        "proxy": proxy_counter,
        "gaps": gap_counter,
        "phase2_status": phase2_status_counter,
        "root_causes": root_cause_counter,
        "truth_report_count": sum(truth_confidence_counter.values()),
        "truth_candidate_events": truth_candidate_events,
        "truth_direct_field_rate_avg": round(sum(truth_direct_rates) / len(truth_direct_rates), 4) if truth_direct_rates else None,
        "truth_proxy_field_rate_avg": round(sum(truth_proxy_rates) / len(truth_proxy_rates), 4) if truth_proxy_rates else None,
        "truth_confidence": truth_confidence_counter,
        "truth_quality": truth_quality_counter,
        "truth_tables": truth_table_totals,
        "truth_lifecycle_phase_distribution": truth_phase_distribution,
        "truth_ev_null_reason_distribution": truth_ev_null_distribution,
        "truth_blind_spots": truth_blind_spots,
        "source_reports": sorted(dict.fromkeys(source_reports)),
    }


def _compare_runs_markdown(date: str, summaries: list[dict[str, Any]], generated_at: str) -> str:
    all_ev: dict[str, int] = {}
    all_timing: dict[str, int] = {}
    all_gaps: dict[str, int] = {}
    all_roots: dict[str, int] = {}
    for summary in summaries:
        for label, count in summary["ev_null_reasons"].items():
            all_ev[label] = all_ev.get(label, 0) + count
        for label, count in summary["timing_liquidity"].items():
            all_timing[label] = all_timing.get(label, 0) + count
        for label, count in summary["gaps"].items():
            all_gaps[label] = all_gaps.get(label, 0) + count
        for label, count in summary["root_causes"].items():
            all_roots[label] = all_roots.get(label, 0) + count

    hypothesis = _recurring_root_cause_hypothesis(
        ev_null_reasons=all_ev,
        timing_liquidity=all_timing,
        coverage_gaps=all_gaps,
        root_causes=all_roots,
    )
    lines = [
        f"# Same-Day Run Comparison Index - {date}",
        "",
        "## Metadata",
        f"- generated_at: {generated_at}",
        f"- session_date: {date}",
        f"- runs_compared: {len(summaries)}",
        "- scope: offline research memory only",
        "- guardrail: no profitability, live-readiness, strategy, risk, or execution claims",
        "",
        "## Reproduce",
        f"- list_run_ids: `python -m tools.research.research_memory_writer --date {date} --list-run-ids`",
        f"- compare_runs: `python -m tools.research.research_memory_writer --date {date} --compare-runs --write-index`",
        f"- per_run_memory: `python -m tools.research.research_memory_writer --date {date} --run-id RUN_ID --write-index`",
        "",
        "## NotebookLM Ingestion Note",
    ]
    lines.extend(_notebooklm_note_lines())
    lines.extend([
        "",
        "## Run IDs Compared",
    ])
    if not summaries:
        lines.append("- No run_id-bearing report JSON found for this date.")
    for summary in summaries:
        marker = " missing_run_id=true" if summary["missing_run_id"] else ""
        lines.append(
            f"- run_id: {summary['run_id']}{marker}; event_count: {summary['event_count']}; "
            f"windows: {len(summary['utc_windows'])}; missed_starters: {summary['missed_starter_count']}"
        )
        for window in summary["utc_windows"][:3]:
            lines.append(f"  - utc_window: {window}")

    for summary in summaries:
        lines.extend([
            "",
            f"## Run {summary['run_id']}",
            f"- missing_run_id: {str(summary['missing_run_id']).lower()}",
            f"- event_count: {summary['event_count']}",
            f"- missed_starter_count: {summary['missed_starter_count']}",
            "- phase2_status:",
        ])
        lines.extend(_sorted_counter_lines(summary["phase2_status"], indent="  - "))
        lines.append("- ev_null_reasons:")
        lines.extend(_sorted_counter_lines(summary["ev_null_reasons"], indent="  - "))
        lines.append("- timing_liquidity_bottlenecks:")
        lines.extend(_sorted_counter_lines(summary["timing_liquidity"], indent="  - "))
        lines.append("- direct_observed:")
        lines.extend(_sorted_counter_lines(summary["direct"], indent="  - "))
        lines.append("- proxy_inferred:")
        lines.extend(_sorted_counter_lines(summary["proxy"], indent="  - "))
        lines.append("- coverage_gap:")
        lines.extend(_sorted_counter_lines(summary["gaps"], indent="  - "))
        lines.append("- lifecycle_truth_table_summary:")
        lines.append(f"  - truth_reports_included: {summary['truth_report_count']}")
        lines.append(f"  - candidate_events: {summary['truth_candidate_events']}")
        lines.append(f"  - direct_field_rate_avg: {summary['truth_direct_field_rate_avg'] if summary['truth_direct_field_rate_avg'] is not None else 'Not reported'}")
        lines.append(f"  - proxy_field_rate_avg: {summary['truth_proxy_field_rate_avg'] if summary['truth_proxy_field_rate_avg'] is not None else 'Not reported'}")
        lines.append("  - replay_truth_confidence:")
        lines.extend(_sorted_counter_lines(summary["truth_confidence"], indent="    - "))
        lines.append("  - replay_truth_quality:")
        lines.extend(_sorted_counter_lines(summary["truth_quality"], indent="    - "))
        lines.append("  - truth_table_counts:")
        lines.extend(_sorted_counter_lines(summary["truth_tables"], indent="    - "))
        lines.append("  - lifecycle_phase_distribution:")
        lines.extend(_sorted_counter_lines(summary["truth_lifecycle_phase_distribution"], indent="    - "))
        lines.append("  - ev_null_reason_distribution:")
        lines.extend(_sorted_counter_lines(summary["truth_ev_null_reason_distribution"], indent="    - "))
        lines.append("  - remaining_blind_spots:")
        lines.extend(_sorted_counter_lines(summary["truth_blind_spots"], indent="    - "))
        lines.append("- source_reports:")
        lines.extend([f"  - {path}" for path in summary["source_reports"][:8]] or ["  - Not reported in source evidence."])

    lines.extend([
        "",
        "## EV-Null Reason Drift",
    ])
    for summary in summaries:
        top = ", ".join(f"{label}={count}" for label, count in sorted(summary["ev_null_reasons"].items(), key=lambda item: (-item[1], item[0]))[:4]) or "None reported."
        lines.append(f"- {summary['run_id']}: {top}")
    lines.extend([
        "",
        "## Timing/Liquidity Bottleneck Drift",
    ])
    for summary in summaries:
        top = ", ".join(f"{label}={count}" for label, count in sorted(summary["timing_liquidity"].items(), key=lambda item: (-item[1], item[0]))[:4]) or "None reported."
        lines.append(f"- {summary['run_id']}: {top}")
    lines.extend([
        "",
        "## Recurring Root-Cause Hypothesis",
        f"- hypothesis: {hypothesis}",
        "- confidence: evidence_index_only",
        "- guardrail: hypothesis summarizes repeated report fields and does not authorize runtime changes.",
        "",
        "## Recommended Next Investigation",
    ])
    if all_gaps:
        top_gap = sorted(all_gaps.items(), key=lambda item: (-item[1], item[0]))[0][0]
        lines.append(f"- Compare run-level coverage gap `{top_gap}` before using same-day evidence for stronger replay conclusions.")
    elif all_timing:
        top_bottleneck = sorted(all_timing.items(), key=lambda item: (-item[1], item[0]))[0][0]
        lines.append(f"- Compare run-level timing/liquidity bottleneck `{top_bottleneck}` against source reports before changing runtime policy.")
    elif all_ev:
        top_reason = sorted(all_ev.items(), key=lambda item: (-item[1], item[0]))[0][0]
        lines.append(f"- Compare EV-null reason `{top_reason}` across run IDs before drawing model conclusions.")
    else:
        lines.append("- Generate run-id filtered analyzer reports before drawing run-to-run conclusions.")
    lines.append("")
    return "\n".join(lines)


def write_same_day_run_comparison_index(
    *,
    date: str,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    reports = discover_source_reports(report_dir, date)
    reports_by_run: dict[str, list[SourceReport]] = {}
    for report in reports:
        run_id = _report_run_id(report.payload) or "missing_run_id"
        reports_by_run.setdefault(run_id, []).append(report)

    summaries = [
        _run_summary(run_id, group_reports_by_window(run_reports, date))
        for run_id, run_reports in sorted(reports_by_run.items())
    ]
    root = Path(output_dir)
    index_dir = root / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    path = index_dir / f"{date}_run_comparison.md"
    path.write_text(
        _compare_runs_markdown(date, summaries, _utc_now()),
        encoding="utf-8",
        newline="\n",
    )
    return path


def write_research_memory_index(
    *,
    date: str,
    bundles: list[ResearchMemoryBundle],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    generated_at: str | None = None,
    run_id: str | None = None,
) -> Path:
    root = Path(output_dir)
    index_dir = root / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    safe_run_id = _safe_filename_token(run_id)
    suffix = f"_run_{safe_run_id}" if safe_run_id else ""
    path = index_dir / f"{date}{suffix}.md"
    path.write_text(_index_markdown(date, bundles, generated_at or _utc_now(), run_id=run_id), encoding="utf-8", newline="\n")
    return path


def write_research_memory_multi_day_index(
    *,
    date_from: str,
    date_to: str,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    run_id: str | None = None,
) -> Path:
    dates = iter_date_strings(date_from, date_to)
    bundles_by_date: dict[str, list[ResearchMemoryBundle]] = {}
    for date in dates:
        reports = discover_source_reports(report_dir, date, run_id=run_id)
        bundles_by_date[date] = group_reports_by_window(reports, date)
    root = Path(output_dir)
    index_dir = root / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    safe_run_id = _safe_filename_token(run_id)
    suffix = f"_run_{safe_run_id}" if safe_run_id else ""
    path = index_dir / f"{date_from}_to_{date_to}{suffix}.md"
    path.write_text(
        _multi_day_index_markdown(
            date_from=date_from,
            date_to=date_to,
            bundles_by_date=bundles_by_date,
            generated_at=_utc_now(),
            run_id=run_id,
        ),
        encoding="utf-8",
        newline="\n",
    )
    return path


def _session_summary_markdown(bundle: ResearchMemoryBundle, generated_at: str) -> str:
    reports = bundle.by_type()
    replay = reports.get("replay", {})
    no_entry = reports.get("no_entry", {})
    session = reports.get("session_runtime", {})
    partial = _best_partial_replay(reports)
    timing = partial.get("timing_decay_summary") if isinstance(partial, dict) else {}
    spread_liquidity = partial.get("spread_liquidity_readiness_summary") if isinstance(partial, dict) else {}

    lines = [f"# Quant Research Memory - {bundle.slug}", ""]
    lines.extend(_metadata_lines(bundle, generated_at, reports))
    lines.extend([
        "",
        "## Replay Status",
        f"- session_status: {session.get('session_status', 'Not reported')}",
        f"- primary_bottleneck: {session.get('primary_bottleneck', 'Not reported')}",
        f"- replay_events_loaded: {replay.get('events_loaded', 'Not reported')}",
        f"- no_entry_total_scanned: {no_entry.get('total_scanned', 'Not reported')}",
        f"- lifecycle_replay_confidence: {_first_value(reports, 'session_runtime.lifecycle_replay_confidence', 'replay.lifecycle_replay_confidence', 'no_entry.lifecycle_replay_confidence', default='Not reported')}",
        "",
        "## Phase2 Coverage",
    ])
    lines.extend(_phase2_lines(reports))
    lines.extend([
        "",
        "## Top Bottlenecks",
        f"- session_primary_bottleneck: {session.get('primary_bottleneck', 'Not reported')}",
        f"- session_secondary_bottleneck: {session.get('secondary_bottleneck', 'Not reported')}",
        "- bottleneck_scores:",
    ])
    lines.extend(_format_mapping(session.get("bottleneck_scores"), limit=8))
    lines.extend(["- no_entry_root_cause_counts:"])
    lines.extend(_format_mapping(no_entry.get("root_cause_counts"), limit=8))
    lines.extend([
        "",
        "## Missed Starter Summary",
    ])
    lines.extend(_missed_starter_lines(reports))
    lines.extend([
        "",
        "## Liquidity Findings",
    ])
    lines.extend(_format_pairs(spread_liquidity.get("liquidity_states") if isinstance(spread_liquidity, dict) else []))
    lines.extend([
        "",
        "## Spread Findings",
        f"- spread_summary_status: {spread_liquidity.get('status', 'Not reported') if isinstance(spread_liquidity, dict) else 'Not reported'}",
        f"- spread_events: {spread_liquidity.get('spread_events', 'Not reported') if isinstance(spread_liquidity, dict) else 'Not reported'}",
        f"- spread_normalization_rate: {spread_liquidity.get('spread_normalization_rate', 'Not reported') if isinstance(spread_liquidity, dict) else 'Not reported'}",
        "",
        "## EV-Null Findings",
    ])
    lines.extend(_ev_null_lines(reports))
    lines.extend([
        "",
        "## Lifecycle Observations",
        f"- partial_lifecycle_replay_status: {partial.get('status', 'Not reported') if isinstance(partial, dict) else 'Not reported'}",
        f"- timing_decay_status: {timing.get('status', 'Not reported') if isinstance(timing, dict) else 'Not reported'}",
        f"- first_seen_seconds_remaining: {timing.get('first_seen_seconds_remaining', 'Not reported') if isinstance(timing, dict) else 'Not reported'}",
        f"- first_evaluable_seconds_remaining: {timing.get('first_evaluable_seconds_remaining', 'Not reported') if isinstance(timing, dict) else 'Not reported'}",
        "",
        "## Repeated Failure Patterns",
    ])
    lines.extend(_format_pairs(no_entry.get("top_skip_reasons") or replay.get("top_skip_reasons"), limit=6))
    lines.extend([
        "",
        "## Direct vs Proxy Evidence",
    ])
    lines.extend(_phase2_lines(reports))
    lines.extend([
        "",
        "## Coverage Gaps",
    ])
    gaps = _coverage_lists(_best_phase2(reports))[2]
    lines.extend([f"- {item}" for item in gaps] or ["- None reported."])
    lines.extend([
        "",
        "## Quant Interpretation",
    ])
    lines.extend(_quant_interpretation_lines(reports))
    lines.extend([
        "",
        "## Recommended Future Investigation",
    ])
    lines.extend(_future_investigation_lines(reports))
    lines.append("")
    return "\n".join(lines)


def _topic_markdown(bundle: ResearchMemoryBundle, generated_at: str, topic: str) -> str:
    reports = bundle.by_type()
    replay = reports.get("replay", {})
    no_entry = reports.get("no_entry", {})
    session = reports.get("session_runtime", {})
    partial = _best_partial_replay(reports)
    spread_liquidity = partial.get("spread_liquidity_readiness_summary") if isinstance(partial, dict) else {}
    timing = partial.get("timing_decay_summary") if isinstance(partial, dict) else {}

    title_by_topic = {
        "replay_findings": "Replay Findings",
        "execution_microstructure": "Execution Microstructure",
        "lifecycle_replay": "Lifecycle Replay",
        "scanner_timing": "Scanner Timing",
        "ev_null_reasons": "EV Null Reasons",
        "known_failures": "Known Failures",
    }
    title = title_by_topic[topic]
    lines = [f"# {title} - {bundle.slug}", ""]
    lines.extend(_metadata_lines(bundle, generated_at, reports))
    lines.append("")

    if topic == "replay_findings":
        lines.extend([
            "## Replay Status",
            f"- replay_events_loaded: {replay.get('events_loaded', 'Not reported')}",
            f"- total_trades: {replay.get('total_trades', 'Not reported')}",
            f"- skipped_decisions: {replay.get('skipped_decisions', 'Not reported')}",
            f"- lifecycle_replay_confidence: {_first_value(reports, 'session_runtime.lifecycle_replay_confidence', 'replay.lifecycle_replay_confidence', default='Not reported')}",
            "",
            "## Top Skip Reasons",
        ])
        lines.extend(_format_pairs(replay.get("top_skip_reasons"), limit=6))
        lines.extend(["", "## Missed Starter Summary"])
        lines.extend(_missed_starter_lines(reports))
    elif topic == "execution_microstructure":
        lines.extend([
            "## Liquidity Findings",
        ])
        lines.extend(_format_pairs(spread_liquidity.get("liquidity_states") if isinstance(spread_liquidity, dict) else []))
        lines.extend([
            "",
            "## Spread Findings",
            f"- spread_events: {spread_liquidity.get('spread_events', 'Not reported') if isinstance(spread_liquidity, dict) else 'Not reported'}",
            f"- spread_normalized_events: {spread_liquidity.get('spread_normalized_events', 'Not reported') if isinstance(spread_liquidity, dict) else 'Not reported'}",
            f"- spread_normalization_rate: {spread_liquidity.get('spread_normalization_rate', 'Not reported') if isinstance(spread_liquidity, dict) else 'Not reported'}",
            "",
            "## Orderbook Readiness Reasons",
        ])
        lines.extend(_format_pairs(spread_liquidity.get("orderbook_readiness_reasons") if isinstance(spread_liquidity, dict) else []))
    elif topic == "lifecycle_replay":
        lines.extend([
            "## Phase2 Coverage",
        ])
        lines.extend(_phase2_lines(reports))
        lines.extend(["", "## Partial Lifecycle Replay"])
        if isinstance(partial, dict) and partial:
            lines.extend([
                f"- status: {partial.get('status', 'Not reported')}",
                f"- lifecycle_replay_confidence: {partial.get('lifecycle_replay_confidence', 'Not reported')}",
                f"- replay_supported_sections: {len(partial.get('replay_supported_sections', []))}",
                f"- replay_unsupported_sections: {len(partial.get('replay_unsupported_sections', []))}",
            ])
        else:
            lines.append("- Not reported in source evidence.")
        lines.extend(["", "## Missed Starter Summary"])
        lines.extend(_missed_starter_lines(reports))
    elif topic == "scanner_timing":
        lines.extend([
            "## Timing Decay",
            f"- status: {timing.get('status', 'Not reported') if isinstance(timing, dict) else 'Not reported'}",
            f"- first_seen_seconds_remaining: {timing.get('first_seen_seconds_remaining', 'Not reported') if isinstance(timing, dict) else 'Not reported'}",
            f"- first_evaluable_seconds_remaining: {timing.get('first_evaluable_seconds_remaining', 'Not reported') if isinstance(timing, dict) else 'Not reported'}",
            f"- avg_seconds_remaining: {timing.get('avg_seconds_remaining', 'Not reported') if isinstance(timing, dict) else 'Not reported'}",
            f"- min_seconds_remaining: {timing.get('min_seconds_remaining', 'Not reported') if isinstance(timing, dict) else 'Not reported'}",
            "",
            "## Candidate Timing",
        ])
        lines.extend(_format_mapping(session.get("candidate_timing"), limit=8))
    elif topic == "ev_null_reasons":
        lines.extend(["## EV-Null Findings"])
        lines.extend(_ev_null_lines(reports))
        lines.extend(["", "## Interpretation Guardrail"])
        lines.append("- Null reasons explain missing EV/fair-value evidence; they do not create a trade signal.")
    elif topic == "known_failures":
        lines.extend([
            "## Repeated Failure Patterns",
            f"- root_cause_category: {no_entry.get('root_cause_category', 'Not reported')}",
            f"- primary_bottleneck: {session.get('primary_bottleneck', 'Not reported')}",
            "",
            "## Skip Reasons",
        ])
        lines.extend(_format_pairs(no_entry.get("top_skip_reasons") or replay.get("top_skip_reasons"), limit=8))
        lines.extend(["", "## Recommendations From Reports"])
        lines.extend(_future_investigation_lines(reports))

    lines.extend(["", "## Quant Interpretation"])
    lines.extend(_quant_interpretation_lines(reports))
    lines.append("")
    return "\n".join(lines)


def write_research_memory(
    *,
    date: str,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    write_index: bool = False,
    run_id: str | None = None,
) -> list[Path]:
    reports = discover_source_reports(report_dir, date, run_id=run_id)
    bundles = group_reports_by_window(reports, date)
    root = Path(output_dir)
    for folder in NOTE_FOLDERS:
        (root / folder).mkdir(parents=True, exist_ok=True)

    generated_at = _utc_now()
    written: list[Path] = []
    for bundle in bundles:
        topic_payloads = {
            "session_summaries": _session_summary_markdown(bundle, generated_at),
            "replay_findings": _topic_markdown(bundle, generated_at, "replay_findings"),
            "execution_microstructure": _topic_markdown(bundle, generated_at, "execution_microstructure"),
            "lifecycle_replay": _topic_markdown(bundle, generated_at, "lifecycle_replay"),
            "scanner_timing": _topic_markdown(bundle, generated_at, "scanner_timing"),
            "ev_null_reasons": _topic_markdown(bundle, generated_at, "ev_null_reasons"),
            "known_failures": _topic_markdown(bundle, generated_at, "known_failures"),
        }
        for folder, markdown in topic_payloads.items():
            path = root / folder / f"{bundle.slug}.md"
            path.write_text(markdown, encoding="utf-8", newline="\n")
            written.append(path)
    if write_index:
        written.append(write_research_memory_index(
            date=date,
            bundles=bundles,
            output_dir=root,
            generated_at=generated_at,
            run_id=run_id,
        ))
    return written


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write offline quant research memory markdown from existing runtime/reports JSON."
    )
    parser.add_argument("--date", default=None, help="Report date in YYYY-MM-DD format.")
    parser.add_argument("--from", dest="date_from", default=None, help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--to", dest="date_to", default=None, help="End date in YYYY-MM-DD format.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Input report directory.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output research memory directory.")
    parser.add_argument("--write-index", action="store_true", help="Write compact daily index markdown.")
    parser.add_argument("--run-id", default=None, help="Exact run_id to isolate from existing report JSON.")
    parser.add_argument("--list-run-ids", action="store_true", help="List available run_id values from existing report JSON for --date.")
    parser.add_argument("--compare-runs", action="store_true", help="Write same-day run comparison index for report JSON grouped by run_id.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.date and (args.date_from or args.date_to):
        raise SystemExit("--date cannot be combined with --from/--to")
    if (args.date_from or args.date_to) and not (args.date_from and args.date_to):
        raise SystemExit("--from and --to must be provided together")
    if args.compare_runs and (args.date_from or args.date_to):
        raise SystemExit("--compare-runs supports --date only")
    if args.date_from and args.date_to:
        if args.list_run_ids:
            raise SystemExit("--list-run-ids currently supports --date only")
        if not args.write_index:
            raise SystemExit("--from/--to currently require --write-index")
        path = write_research_memory_multi_day_index(
            date_from=args.date_from,
            date_to=args.date_to,
            report_dir=args.report_dir,
            output_dir=args.output_dir,
            run_id=args.run_id,
        )
        print("Research Memory Writer")
        print(f"range={args.date_from}..{args.date_to} generated_files=1")
        print(f"wrote={path}")
        return 0
    if not args.date:
        raise SystemExit("--date or --from/--to is required")
    if args.list_run_ids:
        print_report_run_id_summary(discover_report_run_ids(args.report_dir, args.date))
        return 0
    if args.compare_runs:
        if args.run_id:
            raise SystemExit("--compare-runs cannot be combined with --run-id")
        if not args.write_index:
            raise SystemExit("--compare-runs requires --write-index")
        path = write_same_day_run_comparison_index(
            date=args.date,
            report_dir=args.report_dir,
            output_dir=args.output_dir,
        )
        print("Research Memory Writer")
        print(f"date={args.date} run_comparison=true generated_files=1")
        print(f"wrote={path}")
        return 0
    paths = write_research_memory(
        date=args.date,
        report_dir=args.report_dir,
        output_dir=args.output_dir,
        write_index=args.write_index,
        run_id=args.run_id,
    )
    print("Research Memory Writer")
    print(f"date={args.date} generated_files={len(paths)}")
    for path in paths:
        print(f"wrote={path}")
    if not paths:
        print("no matching report JSON found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
