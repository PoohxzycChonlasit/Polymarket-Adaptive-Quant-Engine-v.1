from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_REPORT_DIR = Path("runtime/reports")
DEFAULT_MEMORY_INDEX_DIR = Path("docs/research_memory/index")

TRUTH_TABLE_NAMES = (
    "starter_candidates",
    "missed_starter_candidates",
    "candidate_blocked_before_ev",
    "candidate_blocked_after_ev",
    "time_unsafe_candidates",
    "liquidity_or_orderbook_blocked_candidates",
)

TIMING_TOKENS = ("time", "cutoff", "hard_close", "too_late")
LIQUIDITY_TOKENS = ("orderbook", "empty_book", "liquidity", "spread", "warmup", "stale", "clob", "token")
PRE_MODEL_TOKENS = ("no_probability_model_output", "pre_model", "candidate_blocked_before_ev")
POST_MODEL_TOKENS = ("risk_blocked_after_ev", "candidate_blocked_after_ev", "after_ev")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"date must be YYYY-MM-DD; got {value!r}") from exc


def _date_strings(date_from: str, date_to: str) -> list[str]:
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
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _safe_filename_token(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return ("".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in text)[:80]) or "run"


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


def _counter_dict(counter: Counter[str], *, limit: int | None = None) -> dict[str, int]:
    items = counter.most_common(limit)
    return {str(key): int(value) for key, value in items}


def _counts_from_table(value: Any) -> dict[str, int]:
    if isinstance(value, dict) and isinstance(value.get("counts"), dict):
        return {str(key): _as_int(count) for key, count in value["counts"].items()}
    if isinstance(value, dict):
        return {str(key): _as_int(count) for key, count in value.items() if isinstance(count, (int, float))}
    return {}


def _table_counts(payload: dict[str, Any]) -> dict[str, int]:
    tables = payload.get("tables")
    if not isinstance(tables, dict):
        return {name: 0 for name in TRUTH_TABLE_NAMES}
    counts: dict[str, int] = {}
    for name in TRUTH_TABLE_NAMES:
        value = tables.get(name)
        counts[name] = len(value) if isinstance(value, list) else _as_int(value)
    return counts


def _table_rows(payload: dict[str, Any], table_name: str) -> list[dict[str, Any]]:
    tables = payload.get("tables")
    if not isinstance(tables, dict):
        return []
    value = tables.get(table_name)
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _distribution(payload: dict[str, Any], table_name: str) -> dict[str, int]:
    tables = payload.get("tables")
    if not isinstance(tables, dict):
        return {}
    return _counts_from_table(tables.get(table_name))


def _run_id(payload: dict[str, Any]) -> str:
    run_id = payload.get("run_id")
    if run_id:
        return str(run_id)
    time_filter = payload.get("time_filter")
    if isinstance(time_filter, dict) and time_filter.get("run_id"):
        return str(time_filter["run_id"])
    return ""


def _date_from_payload_or_path(payload: dict[str, Any], path: Path) -> str:
    for key in ("date_from", "date", "session_date"):
        value = str(payload.get(key) or "").strip()
        if len(value) >= 10:
            return value[:10]
    for part in path.name.split("_"):
        if len(part) == 10 and part[4] == "-" and part[7] == "-":
            return part
    return ""


def _is_truth_report(payload: dict[str, Any], path: Path) -> bool:
    return path.name.startswith("lifecycle_truth_tables_") or "replay_truth_confidence" in payload


def _is_replay_report(payload: dict[str, Any], path: Path) -> bool:
    return path.name.startswith("replay_report_") or ("phase2_coverage" in payload and "events_loaded" in payload)


def discover_lifecycle_truth_reports(
    *,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    date_from: str,
    date_to: str,
    run_id: str | None = None,
) -> list[tuple[Path, dict[str, Any]]]:
    dates = set(_date_strings(date_from, date_to))
    reports: list[tuple[Path, dict[str, Any]]] = []
    root = Path(report_dir)
    if not root.exists():
        return reports
    for date in sorted(dates):
        for path in sorted(root.glob(f"lifecycle_truth_tables_*{date}*.json")):
            payload = _load_json(path)
            if payload is None or not _is_truth_report(payload, path):
                continue
            if run_id and _run_id(payload) != run_id:
                continue
            reports.append((path, payload))
    return reports


def discover_replay_reports(
    *,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    date_from: str,
    date_to: str,
    run_id: str | None = None,
) -> list[tuple[Path, dict[str, Any]]]:
    dates = set(_date_strings(date_from, date_to))
    reports: list[tuple[Path, dict[str, Any]]] = []
    root = Path(report_dir)
    if not root.exists():
        return reports
    for date in sorted(dates):
        for path in sorted(root.glob(f"replay_report_*{date}*.json")):
            payload = _load_json(path)
            if payload is None or not _is_replay_report(payload, path):
                continue
            if run_id and _run_id(payload) != run_id:
                continue
            reports.append((path, payload))
    return reports


def discover_research_memory_indexes(
    *,
    memory_index_dir: str | Path = DEFAULT_MEMORY_INDEX_DIR,
    date_from: str,
    date_to: str,
    run_id: str | None = None,
) -> list[Path]:
    dates = set(_date_strings(date_from, date_to))
    root = Path(memory_index_dir)
    if not root.exists():
        return []
    paths: list[Path] = []
    safe_run_id = _safe_filename_token(run_id)
    for date in sorted(dates):
        for path in sorted(root.glob(f"*{date}*.md")):
            if run_id and safe_run_id not in path.name:
                continue
            paths.append(path)
    return paths


def _top_label(counter: Counter[str]) -> str:
    return counter.most_common(1)[0][0] if counter else "Not reported"


def _top_from_dict(value: dict[str, int]) -> str:
    if not value:
        return "Not reported"
    return sorted(value.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _asset_counts_from_truth(payload: dict[str, Any]) -> dict[str, dict[str, int]]:
    rq = payload.get("research_questions")
    if isinstance(rq, dict):
        split = rq.get("are_btc_and_eth_failing_differently")
        if isinstance(split, dict) and isinstance(split.get("asset_failure_counts"), dict):
            return {
                str(asset): {str(key): _as_int(value) for key, value in counts.items()}
                for asset, counts in split["asset_failure_counts"].items()
                if isinstance(counts, dict)
            }

    asset_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for table_name in (
        "missed_starter_candidates",
        "candidate_blocked_before_ev",
        "candidate_blocked_after_ev",
        "time_unsafe_candidates",
        "liquidity_or_orderbook_blocked_candidates",
    ):
        for row in _table_rows(payload, table_name):
            asset = str(row.get("asset") or "UNKNOWN")
            asset_counts[asset][table_name] += 1
    return {asset: dict(counter) for asset, counter in asset_counts.items()}


def _classify_truth_run(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    counts = _table_counts(payload)
    lifecycle_distribution = _distribution(payload, "lifecycle_phase_distribution")
    ev_null_distribution = _distribution(payload, "ev_null_reason_distribution")
    unknown_precision = payload.get("unknown_lifecycle_precision_metrics")
    unknown_precision = unknown_precision if isinstance(unknown_precision, dict) else {}
    excluded_telemetry = payload.get("excluded_telemetry_counts")
    excluded_telemetry = excluded_telemetry if isinstance(excluded_telemetry, dict) else {}
    evidence = payload.get("evidence_completeness")
    evidence = evidence if isinstance(evidence, dict) else {}
    timing_count = counts["time_unsafe_candidates"] + sum(
        count for label, count in ev_null_distribution.items() if any(token in label.lower() for token in TIMING_TOKENS)
    )
    liquidity_count = counts["liquidity_or_orderbook_blocked_candidates"] + sum(
        count for label, count in ev_null_distribution.items() if any(token in label.lower() for token in LIQUIDITY_TOKENS)
    )
    pre_model_count = counts["candidate_blocked_before_ev"] + sum(
        count for label, count in ev_null_distribution.items() if any(token in label.lower() for token in PRE_MODEL_TOKENS)
    )
    post_model_count = counts["candidate_blocked_after_ev"] + sum(
        count for label, count in ev_null_distribution.items() if any(token in label.lower() for token in POST_MODEL_TOKENS)
    )
    quality = str(payload.get("replay_truth_quality") or "")
    confidence = str(payload.get("replay_truth_confidence") or "")
    direct_rate = _as_float(payload.get("direct_field_rate"))
    proxy_rate = _as_float(payload.get("proxy_field_rate"))
    proxy_heavy = "PROXY" in quality or "PROXY" in confidence or proxy_rate > direct_rate
    return {
        "source_report": path.as_posix(),
        "date": _date_from_payload_or_path(payload, path),
        "run_id": _run_id(payload) or "missing_run_id",
        "utc_window": payload.get("time_filter", {}).get("range") if isinstance(payload.get("time_filter"), dict) else "",
        "events_loaded": _as_int(payload.get("events_loaded")),
        "candidate_events": _as_int(payload.get("candidate_events")),
        "replay_truth_confidence": confidence or "Not reported",
        "replay_truth_quality": quality or "Not reported",
        "truth_label": "proxy_heavy_truth" if proxy_heavy else "direct_or_partial_truth",
        "direct_field_rate": direct_rate,
        "proxy_field_rate": proxy_rate,
        "table_counts": counts,
        "lifecycle_phase_distribution": lifecycle_distribution,
        "ev_null_reason_distribution": ev_null_distribution,
        "candidate_classification": {
            "version": str(payload.get("candidate_classification_version") or "legacy_or_unreported"),
            "candidate_classification_reasons": evidence.get("candidate_classification_reasons", {}),
            "candidate_classification_confidence": evidence.get("candidate_classification_confidence", {}),
            "excluded_telemetry_counts": excluded_telemetry,
            "unknown_lifecycle_precision_metrics": unknown_precision,
        },
        "asset_failure_counts": _asset_counts_from_truth(payload),
        "derived_counts": {
            "timing_cutoff_failures": timing_count,
            "liquidity_orderbook_failures": liquidity_count,
            "pre_model_ev_failures": pre_model_count,
            "post_model_or_risk_failures": post_model_count,
            "structural_failures": timing_count + liquidity_count,
            "model_related_failures": pre_model_count + post_model_count,
        },
        "does_not_claim_profitability": bool(payload.get("does_not_claim_profitability", True)),
        "does_not_authorize_runtime_decisions": bool(payload.get("does_not_authorize_runtime_decisions", True)),
    }


def _replay_evidence_summary(replay_reports: list[tuple[Path, dict[str, Any]]]) -> dict[str, Any]:
    skip_reasons: Counter[str] = Counter()
    phase2_statuses: Counter[str] = Counter()
    total_events = 0
    for _path, payload in replay_reports:
        total_events += _as_int(payload.get("events_loaded"))
        for item in payload.get("top_skip_reasons") or []:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                skip_reasons[str(item[0])] += _as_int(item[1], default=1)
        phase2 = payload.get("phase2_coverage")
        if isinstance(phase2, dict):
            phase2_statuses[str(phase2.get("status") or "Not reported")] += 1
    return {
        "reports_loaded": len(replay_reports),
        "events_loaded": total_events,
        "top_skip_reasons": _counter_dict(skip_reasons, limit=10),
        "phase2_statuses": _counter_dict(phase2_statuses),
    }


def _memory_index_summary(index_paths: list[Path]) -> dict[str, Any]:
    hypotheses: Counter[str] = Counter()
    notebook_sections: Counter[str] = Counter()
    for path in index_paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            text = line.strip()
            if text.startswith("- hypothesis:"):
                hypotheses[text.split(":", 1)[1].strip()] += 1
            if text.startswith("## "):
                notebook_sections[text[3:].strip()] += 1
    return {
        "indexes_loaded": len(index_paths),
        "source_indexes": [path.as_posix() for path in index_paths],
        "reported_hypotheses": _counter_dict(hypotheses, limit=8),
        "sections_seen": _counter_dict(notebook_sections, limit=8),
    }


def _trend_value(first: float, last: float, *, epsilon: float = 0.005) -> str:
    if last > first + epsilon:
        return "increasing"
    if last < first - epsilon:
        return "decreasing"
    return "flat"


def _maturity_from_runs(runs: list[dict[str, Any]]) -> tuple[str, str]:
    if not runs:
        return "NO_TRUTH_REPORTS", "NO_DIRECT_FIELD_EVIDENCE"
    avg_direct = sum(run["direct_field_rate"] for run in runs) / len(runs)
    avg_proxy = sum(run["proxy_field_rate"] for run in runs) / len(runs)
    high_or_medium = sum(
        1 for run in runs if str(run["replay_truth_confidence"]).startswith(("HIGH", "MEDIUM"))
    )
    if high_or_medium == len(runs) and avg_direct >= 0.35:
        replay_maturity = "DIRECT_TRUTH_MATURE"
    elif high_or_medium:
        replay_maturity = "PARTIAL_DIRECT_TRUTH"
    elif avg_proxy > avg_direct:
        replay_maturity = "PROXY_HEAVY_TRUTH"
    else:
        replay_maturity = "LOW_EVIDENCE_TRUTH"

    if avg_direct >= 0.35:
        direct_maturity = "READY_DIRECT_FIELD_COVERAGE"
    elif avg_direct >= 0.20:
        direct_maturity = "PARTIAL_DIRECT_FIELD_COVERAGE"
    elif avg_direct > 0:
        direct_maturity = "LOW_DIRECT_FIELD_COVERAGE"
    else:
        direct_maturity = "NO_DIRECT_FIELD_COVERAGE"
    return replay_maturity, direct_maturity


def _recurring_causes(
    *,
    candidate_loss: Counter[str],
    ev_null_reasons: Counter[str],
    lifecycle_phase_failures: Counter[str],
    timing_cutoff_failures: int,
    liquidity_orderbook_failures: int,
    runs_count: int,
) -> list[dict[str, Any]]:
    causes: list[dict[str, Any]] = []
    if runs_count <= 0:
        return causes
    for label, count in candidate_loss.most_common():
        if count:
            causes.append({
                "cause": f"candidate_loss:{label}",
                "count": count,
                "runs_observed": min(runs_count, count),
                "evidence_label": "direct_or_proxy_truth_table_count",
            })
    for label, count in ev_null_reasons.most_common():
        if count:
            causes.append({
                "cause": f"ev_null_reason:{label}",
                "count": count,
                "runs_observed": min(runs_count, count),
                "evidence_label": "direct_null_reason_count",
            })
    if timing_cutoff_failures:
        causes.append({
            "cause": "structural:timing_cutoff",
            "count": timing_cutoff_failures,
            "runs_observed": runs_count,
            "evidence_label": "direct_or_proxy_timing_count",
        })
    if liquidity_orderbook_failures:
        causes.append({
            "cause": "structural:liquidity_orderbook",
            "count": liquidity_orderbook_failures,
            "runs_observed": runs_count,
            "evidence_label": "direct_or_proxy_liquidity_count",
        })
    if lifecycle_phase_failures:
        phase, count = lifecycle_phase_failures.most_common(1)[0]
        causes.append({
            "cause": f"lifecycle_phase:{phase}",
            "count": count,
            "runs_observed": runs_count,
            "evidence_label": "phase_distribution_count",
        })
    return sorted(causes, key=lambda item: (-_as_int(item["count"]), str(item["cause"])))[:12]


def _repeated_failure_confidence(runs: list[dict[str, Any]], recurring_causes: list[dict[str, Any]]) -> str:
    if not runs or not recurring_causes:
        return "INSUFFICIENT_EVIDENCE"
    top = recurring_causes[0]
    avg_direct = sum(run["direct_field_rate"] for run in runs) / len(runs)
    proxy_heavy = sum(1 for run in runs if run["truth_label"] == "proxy_heavy_truth")
    if _as_int(top.get("runs_observed")) >= 3 and avg_direct >= 0.20:
        return "MEDIUM_REPEATED_DIRECT_EVIDENCE"
    if _as_int(top.get("runs_observed")) >= 2:
        return "LOW_REPEATED_PROXY_HEAVY_EVIDENCE" if proxy_heavy else "MEDIUM_REPEATED_EVIDENCE"
    return "LOW_SINGLE_RUN_OR_WEAK_REPEAT_EVIDENCE"


def _run_to_run_drift(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    drift: list[dict[str, Any]] = []
    ordered = sorted(runs, key=lambda run: (run.get("date") or "", run.get("run_id") or "", run.get("source_report") or ""))
    previous: dict[str, Any] | None = None
    for run in ordered:
        if previous is None:
            previous = run
            continue
        drift.append({
            "from_run_id": previous["run_id"],
            "to_run_id": run["run_id"],
            "from_date": previous["date"],
            "to_date": run["date"],
            "candidate_events_delta": run["candidate_events"] - previous["candidate_events"],
            "direct_field_rate_delta": round(run["direct_field_rate"] - previous["direct_field_rate"], 4),
            "proxy_field_rate_delta": round(run["proxy_field_rate"] - previous["proxy_field_rate"], 4),
            "top_lifecycle_phase_from": _top_from_dict(previous["lifecycle_phase_distribution"]),
            "top_lifecycle_phase_to": _top_from_dict(run["lifecycle_phase_distribution"]),
            "top_ev_null_reason_from": _top_from_dict(previous["ev_null_reason_distribution"]),
            "top_ev_null_reason_to": _top_from_dict(run["ev_null_reason_distribution"]),
            "truth_quality_from": previous["replay_truth_quality"],
            "truth_quality_to": run["replay_truth_quality"],
        })
        previous = run
    return drift


def build_cross_run_lifecycle_truth(
    *,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    memory_index_dir: str | Path = DEFAULT_MEMORY_INDEX_DIR,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    if date:
        date_from = date_to = date
    if not date_from:
        date_from = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not date_to:
        date_to = date_from

    truth_reports = discover_lifecycle_truth_reports(
        report_dir=report_dir,
        date_from=date_from,
        date_to=date_to,
        run_id=run_id,
    )
    replay_reports = discover_replay_reports(
        report_dir=report_dir,
        date_from=date_from,
        date_to=date_to,
        run_id=run_id,
    )
    memory_indexes = discover_research_memory_indexes(
        memory_index_dir=memory_index_dir,
        date_from=date_from,
        date_to=date_to,
        run_id=run_id,
    )

    runs = [_classify_truth_run(path, payload) for path, payload in truth_reports]
    candidate_loss: Counter[str] = Counter()
    ev_null_reasons: Counter[str] = Counter()
    lifecycle_phase_failures: Counter[str] = Counter()
    truth_confidence: Counter[str] = Counter()
    truth_quality: Counter[str] = Counter()
    asset_loss: defaultdict[str, Counter[str]] = defaultdict(Counter)
    timing_cutoff_failures = 0
    liquidity_orderbook_failures = 0
    pre_model_failures = 0
    post_model_failures = 0
    excluded_telemetry_total = 0
    excluded_legacy_candidate_like_total = 0
    legacy_candidate_like_events = 0
    legacy_unknown_lifecycle_events = 0
    refined_unknown_lifecycle_events = 0
    unknown_lifecycle_removed_by_filter = 0
    classification_reasons: Counter[str] = Counter()
    classification_confidence: Counter[str] = Counter()
    excluded_telemetry_categories: Counter[str] = Counter()
    excluded_telemetry_reasons: Counter[str] = Counter()

    for run in runs:
        for label, count in run["table_counts"].items():
            if label != "starter_candidates":
                candidate_loss[label] += count
        for label, count in run["ev_null_reason_distribution"].items():
            ev_null_reasons[label] += count
        for label, count in run["lifecycle_phase_distribution"].items():
            lifecycle_phase_failures[label] += count
        truth_confidence[run["replay_truth_confidence"]] += 1
        truth_quality[run["replay_truth_quality"]] += 1
        timing_cutoff_failures += run["derived_counts"]["timing_cutoff_failures"]
        liquidity_orderbook_failures += run["derived_counts"]["liquidity_orderbook_failures"]
        pre_model_failures += run["derived_counts"]["pre_model_ev_failures"]
        post_model_failures += run["derived_counts"]["post_model_or_risk_failures"]
        classification = run.get("candidate_classification", {})
        unknown_precision = classification.get("unknown_lifecycle_precision_metrics", {}) if isinstance(classification, dict) else {}
        excluded = classification.get("excluded_telemetry_counts", {}) if isinstance(classification, dict) else {}
        excluded_telemetry_total += _as_int(excluded.get("excluded_total"))
        excluded_legacy_candidate_like_total += _as_int(excluded.get("excluded_legacy_candidate_like_events"))
        legacy_candidate_like_events += _as_int(unknown_precision.get("legacy_candidate_like_events"))
        legacy_unknown_lifecycle_events += _as_int(unknown_precision.get("legacy_unknown_lifecycle_events"))
        refined_unknown_lifecycle_events += _as_int(unknown_precision.get("refined_unknown_lifecycle_events"))
        unknown_lifecycle_removed_by_filter += _as_int(unknown_precision.get("unknown_lifecycle_events_removed_by_filter"))
        for label, count in dict(classification.get("candidate_classification_reasons", {})).items():
            classification_reasons[str(label)] += _as_int(count)
        for label, count in dict(classification.get("candidate_classification_confidence", {})).items():
            classification_confidence[str(label)] += _as_int(count)
        for label, count in dict(excluded.get("by_category", {})).items():
            excluded_telemetry_categories[str(label)] += _as_int(count)
        for label, count in dict(excluded.get("by_reason", {})).items():
            excluded_telemetry_reasons[str(label)] += _as_int(count)
        for asset, counts in run["asset_failure_counts"].items():
            for label, count in counts.items():
                asset_loss[asset][label] += count

    replay_maturity, direct_maturity = _maturity_from_runs(runs)
    recurring_causes = _recurring_causes(
        candidate_loss=candidate_loss,
        ev_null_reasons=ev_null_reasons,
        lifecycle_phase_failures=lifecycle_phase_failures,
        timing_cutoff_failures=timing_cutoff_failures,
        liquidity_orderbook_failures=liquidity_orderbook_failures,
        runs_count=len(runs),
    )
    direct_rates = [run["direct_field_rate"] for run in runs]
    proxy_rates = [run["proxy_field_rate"] for run in runs]
    direct_trend = _trend_value(direct_rates[0], direct_rates[-1]) if len(direct_rates) >= 2 else "insufficient_runs"
    proxy_trend = _trend_value(proxy_rates[0], proxy_rates[-1]) if len(proxy_rates) >= 2 else "insufficient_runs"
    structural = timing_cutoff_failures + liquidity_orderbook_failures
    model_related = pre_model_failures + post_model_failures
    top_phase = _top_label(lifecycle_phase_failures)
    max_phase_count = max(lifecycle_phase_failures.values(), default=0)
    opening_scan_is_dominant = bool(max_phase_count and lifecycle_phase_failures.get("OPENING_SCAN", 0) == max_phase_count)

    report = {
        "generated_at_utc": _utc_now(),
        "date_from": date_from,
        "date_to": date_to,
        "run_id_filter": run_id or "",
        "scope": "offline_research_replay_only",
        "does_not_claim_profitability": True,
        "does_not_authorize_runtime_decisions": True,
        "does_not_implement_inventory_execution": True,
        "source_inputs": {
            "lifecycle_truth_tables": [path.as_posix() for path, _payload in truth_reports],
            "replay_reports": [path.as_posix() for path, _payload in replay_reports],
            "research_memory_indexes": [path.as_posix() for path in memory_indexes],
            "counts": {
                "lifecycle_truth_tables": len(truth_reports),
                "replay_reports": len(replay_reports),
                "research_memory_indexes": len(memory_indexes),
            },
        },
        "runs_analyzed": runs,
        "aggregate": {
            "runs_analyzed": len(runs),
            "candidate_events": sum(run["candidate_events"] for run in runs),
            "repeated_candidate_loss_patterns": _counter_dict(candidate_loss),
            "repeated_ev_null_reasons": _counter_dict(ev_null_reasons),
            "repeated_lifecycle_phase_failures": _counter_dict(lifecycle_phase_failures),
            "repeated_timing_cutoff_failures": timing_cutoff_failures,
            "repeated_liquidity_orderbook_failures": liquidity_orderbook_failures,
            "direct_vs_proxy_evidence_trend": {
                "direct_field_rate_avg": round(sum(direct_rates) / len(direct_rates), 4) if direct_rates else None,
                "proxy_field_rate_avg": round(sum(proxy_rates) / len(proxy_rates), 4) if proxy_rates else None,
                "direct_field_rate_trend": direct_trend,
                "proxy_field_rate_trend": proxy_trend,
                "truth_confidence_distribution": _counter_dict(truth_confidence),
                "truth_quality_distribution": _counter_dict(truth_quality),
                "proxy_heavy_run_count": sum(1 for run in runs if run["truth_label"] == "proxy_heavy_truth"),
            },
            "candidate_classification_trend": {
                "classification_reasons": _counter_dict(classification_reasons),
                "classification_confidence": _counter_dict(classification_confidence),
                "excluded_telemetry_total": excluded_telemetry_total,
                "excluded_legacy_candidate_like_events": excluded_legacy_candidate_like_total,
                "excluded_telemetry_by_category": _counter_dict(excluded_telemetry_categories),
                "excluded_telemetry_by_reason": _counter_dict(excluded_telemetry_reasons),
            },
            "unknown_lifecycle_precision_metrics": {
                "legacy_candidate_like_events": legacy_candidate_like_events,
                "refined_candidate_events": sum(run["candidate_events"] for run in runs),
                "legacy_unknown_lifecycle_events": legacy_unknown_lifecycle_events,
                "refined_unknown_lifecycle_events": refined_unknown_lifecycle_events,
                "unknown_lifecycle_events_removed_by_filter": unknown_lifecycle_removed_by_filter,
                "legacy_unknown_lifecycle_rate": round(legacy_unknown_lifecycle_events / legacy_candidate_like_events, 4) if legacy_candidate_like_events else 0.0,
                "refined_unknown_lifecycle_rate": round(refined_unknown_lifecycle_events / sum(run["candidate_events"] for run in runs), 4) if sum(run["candidate_events"] for run in runs) else 0.0,
                "unknown_inflation_removed_rate": round(unknown_lifecycle_removed_by_filter / legacy_unknown_lifecycle_events, 4) if legacy_unknown_lifecycle_events else 0.0,
            },
            "run_to_run_drift": _run_to_run_drift(runs),
            "btc_vs_eth_candidate_loss_differences": {
                asset: dict(counter.most_common())
                for asset, counter in sorted(asset_loss.items())
            },
        },
        "recurring_root_causes": recurring_causes,
        "repeated_failure_confidence": _repeated_failure_confidence(runs, recurring_causes),
        "replay_truth_maturity": replay_maturity,
        "direct_field_maturity": direct_maturity,
        "lifecycle_phase_failure_ranking": _counter_dict(lifecycle_phase_failures),
        "replay_report_evidence": _replay_evidence_summary(replay_reports),
        "research_memory_index_evidence": _memory_index_summary(memory_indexes),
        "research_questions": {
            "is_timing_decay_consistently_killing_executable_edge": {
                "answer": "evidence_present" if timing_cutoff_failures else "not_observed",
                "timing_cutoff_failures": timing_cutoff_failures,
                "confidence": "proxy_heavy_if_truth_quality_is_proxy_heavy",
            },
            "are_failures_structural_or_model_related": {
                "answer": "structural" if structural > model_related else "model_related" if model_related > structural else "mixed_or_insufficient",
                "structural_count": structural,
                "model_related_count": model_related,
                "uncertainty": "candidate-loss counts are evidence summaries and do not authorize runtime changes",
            },
            "is_opening_scan_still_dominant": {
                "answer": opening_scan_is_dominant,
                "top_lifecycle_phase": top_phase,
                "phase_distribution": _counter_dict(lifecycle_phase_failures),
                "interpretation": "true means OPENING_SCAN is tied for or holds the highest observed phase count",
            },
            "are_ev_failures_mostly_pre_model_or_post_model": {
                "answer": "pre_model" if pre_model_failures > post_model_failures else "post_model_or_risk" if post_model_failures > pre_model_failures else "mixed_or_insufficient",
                "pre_model_ev_failures": pre_model_failures,
                "post_model_or_risk_failures": post_model_failures,
            },
            "is_replay_truth_improving_across_runs": {
                "answer": "improving" if direct_trend == "increasing" and proxy_trend != "increasing" else "not_observed_or_mixed",
                "direct_field_rate_trend": direct_trend,
                "proxy_field_rate_trend": proxy_trend,
                "replay_truth_maturity": replay_maturity,
            },
            "how_much_unknown_inflation_comes_from_telemetry_pollution": {
                "answer": "evidence_present" if unknown_lifecycle_removed_by_filter else "not_observed_or_unreported",
                "unknown_lifecycle_events_removed_by_filter": unknown_lifecycle_removed_by_filter,
                "excluded_legacy_candidate_like_events": excluded_legacy_candidate_like_total,
                "unknown_inflation_removed_rate": round(unknown_lifecycle_removed_by_filter / legacy_unknown_lifecycle_events, 4) if legacy_unknown_lifecycle_events else 0.0,
            },
            "does_direct_field_maturity_improve_after_filtering": {
                "answer": direct_maturity,
                "direct_field_rate_avg_after_filtering": round(sum(direct_rates) / len(direct_rates), 4) if direct_rates else None,
                "proxy_field_rate_avg_after_filtering": round(sum(proxy_rates) / len(proxy_rates), 4) if proxy_rates else None,
            },
            "are_pre_ev_blocks_still_dominant_after_cleanup": {
                "answer": pre_model_failures > post_model_failures,
                "pre_model_ev_failures": pre_model_failures,
                "post_model_or_risk_failures": post_model_failures,
            },
            "does_lifecycle_phase_ranking_stabilize": {
                "answer": top_phase,
                "phase_distribution": _counter_dict(lifecycle_phase_failures),
                "uncertainty": "ranking is filtered but still depends on compatible truth-table coverage",
            },
        },
    }
    return report


def _output_date_part(report: dict[str, Any]) -> str:
    date_from = str(report.get("date_from") or "")
    date_to = str(report.get("date_to") or date_from)
    text = date_from if date_from == date_to else f"{date_from}_to_{date_to}"
    run_id = _safe_filename_token(report.get("run_id_filter"))
    if run_id:
        text = f"{text}_run_{run_id}"
    return text


def write_cross_run_lifecycle_truth(
    report: dict[str, Any],
    *,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"cross_run_lifecycle_truth_{_output_date_part(report)}.json"
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return output_path


def print_summary(report: dict[str, Any]) -> None:
    aggregate = report.get("aggregate", {})
    print("Cross-Run Lifecycle Truth Analysis")
    print(
        "range={start}..{end} run_id_filter={run_id} truth_reports={truth_reports} runs={runs} maturity={maturity} direct_maturity={direct_maturity}".format(
            start=report.get("date_from"),
            end=report.get("date_to"),
            run_id=report.get("run_id_filter") or "",
            truth_reports=report.get("source_inputs", {}).get("counts", {}).get("lifecycle_truth_tables", 0),
            runs=aggregate.get("runs_analyzed", 0),
            maturity=report.get("replay_truth_maturity"),
            direct_maturity=report.get("direct_field_maturity"),
        )
    )
    print(
        "candidate_events={candidate_events} timing_cutoff={timing} liquidity_orderbook={liquidity} repeated_failure_confidence={confidence}".format(
            candidate_events=aggregate.get("candidate_events", 0),
            timing=aggregate.get("repeated_timing_cutoff_failures", 0),
            liquidity=aggregate.get("repeated_liquidity_orderbook_failures", 0),
            confidence=report.get("repeated_failure_confidence"),
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze cross-run lifecycle truth-table drift from offline reports.")
    parser.add_argument("--date", default=None, help="Single date in YYYY-MM-DD format.")
    parser.add_argument("--from", dest="date_from", default=None, help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--to", dest="date_to", default=None, help="End date in YYYY-MM-DD format.")
    parser.add_argument("--run-id", default=None, help="Optional exact run_id filter.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Input/output report directory.")
    parser.add_argument("--memory-index-dir", default=str(DEFAULT_MEMORY_INDEX_DIR), help="Research memory index directory.")
    parser.add_argument("--no-write", action="store_true", help="Do not write cross-run JSON report.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.date and (args.date_from or args.date_to):
        raise SystemExit("--date cannot be combined with --from/--to")
    if (args.date_from or args.date_to) and not (args.date_from and args.date_to):
        raise SystemExit("--from and --to must be provided together")
    report = build_cross_run_lifecycle_truth(
        report_dir=args.report_dir,
        memory_index_dir=args.memory_index_dir,
        date=args.date,
        date_from=args.date_from,
        date_to=args.date_to,
        run_id=args.run_id,
    )
    print_summary(report)
    if not args.no_write:
        path = write_cross_run_lifecycle_truth(report, report_dir=args.report_dir)
        print(f"wrote_report={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
