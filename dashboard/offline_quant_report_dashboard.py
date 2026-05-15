from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = REPO_ROOT / "runtime" / "reports"
HTML_PATH = Path(__file__).with_name("offline_quant_report_dashboard.html")

REPORT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("quant_data_quality", re.compile(r"^quant_data_quality_(?P<date>\d{4}-\d{2}-\d{2})(?:_run_(?P<run>.+))?\.json$")),
    ("no_entry", re.compile(r"^no_entry_report_(?P<date>\d{4}-\d{2}-\d{2})(?:_run_(?P<run>.+))?\.json$")),
    ("session_runtime", re.compile(r"^session_runtime_evaluation_(?P<date>\d{4}-\d{2}-\d{2})(?:_run_(?P<run>.+))?\.json$")),
    ("replay", re.compile(r"^replay_report_(?P<date>\d{4}-\d{2}-\d{2})(?:_run_(?P<run>.+))?\.json$")),
    ("compact_run_summary", re.compile(r"^compact_run_summary_(?P<date>\d{4}-\d{2}-\d{2})\.json$")),
    ("market_readiness_probe", re.compile(r"^market_readiness_admission_probe_(?P<date>\d{4}-\d{2}-\d{2})\.json$")),
    ("silent_zone_probe", re.compile(r"^silent_zone_selection_probe_(?P<date>\d{4}-\d{2}-\d{2})(?:_.+)?\.json$")),
    ("no_entry_root_cause", re.compile(r"^no_entry_root_cause_(?P<date>\d{4}-\d{2}-\d{2})\.json$")),
    ("decision_cycle_timing_probe", re.compile(r"^decision_cycle_timing_probe_(?P<date>\d{4}-\d{2}-\d{2})\.json$")),
    ("candidate_continuity", re.compile(r"^candidate_continuity_(?P<date>\d{4}-\d{2}-\d{2})(?:_run_(?P<run>.+))?\.json$")),
    ("candidate_path_observability", re.compile(r"^candidate_path_observability_(?P<date>\d{4}-\d{2}-\d{2})(?:_run_(?P<run>.+))?\.json$")),
)


def detect_report(path: Path) -> tuple[str, str | None, str | None] | None:
    for kind, pattern in REPORT_PATTERNS:
        match = pattern.match(path.name)
        if match:
            return kind, match.groupdict().get("date"), match.groupdict().get("run")
    return None


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _get(data: dict[str, Any] | None, path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = data or {}
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _first(values: list[Any], default: Any = None) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return default


def _number(value: Any, default: int | float = 0) -> int | float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return value
    return default


def _first_number(values: list[Any], default: int | float = 0) -> int | float:
    for value in values:
        number = _number(value, default=None)  # type: ignore[arg-type]
        if number is not None:
            return number
    return default


def _as_count_dict(value: Any) -> dict[str, int | float]:
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    if isinstance(value, list):
        output: dict[str, int | float] = {}
        for row in value:
            if isinstance(row, (list, tuple)) and len(row) >= 2 and isinstance(row[1], (int, float)):
                output[str(row[0])] = row[1]
        return output
    return {}


def _dominant_count_key(value: Any) -> str | None:
    counts = _as_count_dict(value)
    if not counts:
        return None
    return max(counts.items(), key=lambda item: item[1])[0]


def _root_probe_label(root_probe: dict[str, Any] | None) -> str | None:
    if not root_probe:
        return None
    category = _dominant_count_key(root_probe.get("category_counts"))
    reason = _dominant_count_key(root_probe.get("primary_reason_counts"))
    if category and reason:
        return f"{category}/{reason}"
    return category or reason


def _iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat().replace("+00:00", "Z")


def _report_run_id(data: dict[str, Any], filename_run: str | None) -> str | None:
    return _first(
        [
            data.get("run_id"),
            data.get("run_id_filter"),
            data.get("run_id_scope"),
            _get(data, ("replay_continuity", "run_id_scope")),
            filename_run,
        ]
    )


def _report_sort_timestamp(reports: dict[str, dict[str, Any]], newest_file_utc: str) -> str:
    candidates = [
        _get(reports.get("quant_data_quality"), ("run_id_summary", "run_ids"), []),
        _get(reports.get("compact_run_summary"), ("time_range", "last_timestamp_utc")),
        _get(reports.get("session_runtime"), ("generated_at_utc",)),
        _get(reports.get("replay"), ("generated_at_utc",)),
    ]
    run_rows = candidates[0]
    if isinstance(run_rows, list) and run_rows:
        last_ts = _get(run_rows[0], ("last_timestamp_utc",))
        if last_ts:
            return str(last_ts)
    for value in candidates[1:]:
        if value:
            return str(value)
    return newest_file_utc


def _continuity_summary(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    quality = reports.get("quant_data_quality")
    continuity = _get(quality, ("replay_continuity",), {})
    ordering = _get(quality, ("timestamp_ordering",), {})
    return {
        "status": _first([continuity.get("status"), ordering.get("status"), "UNKNOWN"]),
        "trustworthy_for_replay": bool(continuity.get("trustworthy_for_replay")),
        "events_checked": _number(continuity.get("events_checked")),
        "run_chain_gap_count": _number(continuity.get("run_chain_gap_count")),
        "timestamp_ordering": _first([ordering.get("status"), "UNKNOWN"]),
        "research_log_integrity": _first([_get(quality, ("research_log_integrity", "status")), "UNKNOWN"]),
    }


def _bad_json_summary(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    quality = reports.get("quant_data_quality")
    no_entry = reports.get("no_entry")
    replay = reports.get("replay")
    impact = _get(quality, ("malformed_json_impact",), {})
    count = _first_number(
        [
            _get(impact, ("matching_run_id_malformed_json_lines",)),
            quality.get("bad_json_lines") if quality else None,
            no_entry.get("bad_json_lines") if no_entry else None,
            replay.get("bad_json_lines") if replay else None,
        ]
    )
    total_scanned = _first_number(
        [
            _get(impact, ("total_malformed_json_lines_in_scanned_files",)),
            quality.get("bad_lines_count") if quality else None,
        ]
    )
    return {
        "warning": bool(count or impact.get("affects_selected_run")),
        "selected_run_bad_lines": count,
        "total_scanned_bad_lines": total_scanned,
        "affects_selected_run": bool(impact.get("affects_selected_run")),
        "status": _first([impact.get("status"), "UNKNOWN"]),
    }


def _root_cause_summary(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    no_entry = reports.get("no_entry")
    session = reports.get("session_runtime")
    root_probe = reports.get("no_entry_root_cause")
    root = _first(
        [
            no_entry.get("root_cause_category") if no_entry else None,
            session.get("primary_bottleneck") if session else None,
            _root_probe_label(root_probe),
            "UNKNOWN",
        ]
    )
    return {
        "primary": root,
        "secondary": _first([session.get("secondary_bottleneck") if session else None, "UNKNOWN"]),
        "counts": _first(
            [
                no_entry.get("root_cause_counts") if no_entry else None,
                root_probe.get("category_counts") if root_probe else None,
                {},
            ],
            {},
        ),
        "details": _first([no_entry.get("root_cause_details") if no_entry else None, []], []),
        "execution_stage_attempts": _first_number(
            [
                no_entry.get("execution_stage_attempt_count") if no_entry else None,
                _get(session, ("execution_summary", "order_submit_attempt_count")),
            ]
        ),
    }


def _lifecycle_distribution(reports: dict[str, dict[str, Any]]) -> dict[str, int | float]:
    compact = reports.get("compact_run_summary")
    session = reports.get("session_runtime")
    no_entry_root = reports.get("no_entry_root_cause")
    admission = reports.get("market_readiness_probe")
    timing = reports.get("decision_cycle_timing_probe")
    return _first(
        [
            _as_count_dict(_get(no_entry_root, ("lifecycle_phase_distribution",))),
            _as_count_dict(_get(admission, ("lifecycle_phase_probe_distribution",))),
            _as_count_dict(_get(timing, ("lifecycle_phase_distribution",))),
            _as_count_dict(_get(compact, ("candidate_timing_diagnostics", "lifecycle_phase_counts"))),
            _as_count_dict(_get(session, ("scanner_lifecycle", "lifecycle_phase_counts"))),
            {},
        ],
        {},
    )


def _ev_visibility(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    compact = reports.get("compact_run_summary")
    coverage = _first(
        [
            _get(reports.get("no_entry"), ("phase2_coverage",)),
            _get(reports.get("session_runtime"), ("phase2_coverage",)),
            _get(reports.get("replay"), ("phase2_coverage",)),
            _get(reports.get("quant_data_quality"), ("phase2_coverage",)),
            {},
        ],
        {},
    )
    ev_field = _get(coverage, ("ev_null_reason_coverage", "fields", "ev_after_spread"), {})
    compact_ev = _get(compact, ("ev_visibility",), {})
    return {
        "status": _first([compact_ev.get("ev_visibility_status"), "UNKNOWN"]),
        "value_events": _number(ev_field.get("value_events")),
        "null_events": _number(ev_field.get("null_events")),
        "null_reason_coverage_rate": _number(ev_field.get("null_reason_coverage_rate")),
        "top_null_reasons": _as_count_dict(ev_field.get("null_reasons")),
        "does_not_claim_ev_available": bool(_get(coverage, ("ev_null_reason_coverage", "does_not_claim_ev_available"), True)),
    }


def _liquidity_orderbook(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    session = reports.get("session_runtime")
    no_entry = reports.get("no_entry")
    replay = reports.get("replay")
    market = _get(session, ("market_readiness",), {})
    orderbook = _get(session, ("orderbook_readiness",), {})
    spread = _first(
        [
            _get(session, ("spread_liquidity_readiness_summary",)),
            _get(no_entry, ("spread_liquidity_readiness_summary",)),
            _get(replay, ("spread_liquidity_readiness_summary",)),
            {},
        ],
        {},
    )
    blockers = _first_number(
        [
            market.get("empty_book_count"),
            orderbook.get("orderbook_unavailable_count"),
            orderbook.get("stale_book_count"),
        ]
    )
    return {
        "status": "READY" if not blockers else "ATTENTION",
        "market_readiness": market,
        "orderbook_unavailable_count": _number(orderbook.get("orderbook_unavailable_count")),
        "empty_book_count": _number(market.get("empty_book_count")),
        "stale_book_count": _number(market.get("stale_book_count")),
        "liquidity_states": _as_count_dict(spread.get("liquidity_states")),
        "spread_normalization_rate": _number(spread.get("spread_normalization_rate")),
        "readiness_status": _first([spread.get("status"), "UNKNOWN"]),
    }


def _timeline_cards(reports: dict[str, dict[str, Any]], source_files: list[str]) -> list[dict[str, Any]]:
    replay = reports.get("replay")
    session = reports.get("session_runtime")
    no_entry = reports.get("no_entry")
    quality = reports.get("quant_data_quality")
    return [
        {
            "title": "Report Coverage",
            "items": {
                "source_files": len(source_files),
                "report_types": ", ".join(sorted(reports.keys())),
            },
        },
        {
            "title": "Continuity Gate",
            "items": {
                "events_checked": _get(quality, ("replay_continuity", "events_checked"), 0),
                "chain_gaps": _get(quality, ("replay_continuity", "run_chain_gap_count"), 0),
                "timestamp_ordering": _get(quality, ("timestamp_ordering", "status"), "UNKNOWN"),
            },
        },
        {
            "title": "Replay Summary",
            "items": {
                "events_loaded": _get(replay, ("events_loaded",), 0),
                "approved_decisions": _first_number([_get(replay, ("approved_decisions",)), _get(session, ("execution_summary", "approved_decisions"))]),
                "rejected_decisions": _get(session, ("execution_summary", "rejected_decisions"), 0),
                "cutoff_blocks": _first_number([_get(replay, ("cutoff_block_count",)), _get(session, ("cutoff_behavior", "cutoff_block_count"))]),
            },
        },
        {
            "title": "Execution Evidence",
            "items": {
                "execution_events_loaded": _first_number([_get(no_entry, ("execution_events_loaded",)), _get(session, ("execution_summary", "execution_events_loaded"))]),
                "submit_attempts": _first_number([_get(no_entry, ("order_submit_attempt_count",)), _get(session, ("execution_summary", "order_submit_attempt_count"))]),
                "failures": _first_number([_get(no_entry, ("execution_failure_count",)), _get(session, ("execution_summary", "execution_failure_count"))]),
                "paper_fills": _first_number([_get(no_entry, ("paper_fill_count",)), _get(session, ("execution_summary", "paper_fill_count"))]),
            },
        },
    ]


def _build_record(date: str, run_id: str, reports: dict[str, dict[str, Any]], source_files: list[str], newest_file_utc: str) -> dict[str, Any]:
    session = reports.get("session_runtime")
    no_entry = reports.get("no_entry")
    time_unsafe = _first_number(
        [
            no_entry.get("count_time_unsafe") if no_entry else None,
            _get(session, ("skip_summary", "skip_reason_counts", "time_unsafe")),
            _get(session, ("cutoff_behavior", "time_unsafe_count")),
            _get(reports.get("no_entry_root_cause"), ("primary_reason_counts", "cutoff_passed")),
            _get(reports.get("no_entry_root_cause"), ("category_counts", "timing")),
        ]
    )
    risk_zero = _first_number(
        [
            no_entry.get("count_risk_plan_zero") if no_entry else None,
            _get(session, ("skip_summary", "skip_reason_counts", "risk_plan_zero")),
            _get(session, ("risk_blocks", "risk_plan_zero_count")),
            _get(reports.get("no_entry_root_cause"), ("primary_reason_counts", "zero_size_plan")),
            _get(reports.get("no_entry_root_cause"), ("category_counts", "risk")),
        ]
    )
    return {
        "date": date,
        "run_id": run_id,
        "has_run_id": run_id not in {"unscoped", "unknown"},
        "sort_timestamp_utc": _report_sort_timestamp(reports, newest_file_utc),
        "latest_report_file_utc": newest_file_utc,
        "continuity": _continuity_summary(reports),
        "root_cause": _root_cause_summary(reports),
        "time_unsafe_count": time_unsafe,
        "risk_plan_zero_count": risk_zero,
        "lifecycle_distribution": _lifecycle_distribution(reports),
        "ev_visibility": _ev_visibility(reports),
        "liquidity_orderbook": _liquidity_orderbook(reports),
        "bad_json": _bad_json_summary(reports),
        "timeline_cards": _timeline_cards(reports, source_files),
        "source_files": sorted(source_files),
    }


def build_dashboard_payload(report_dir: Path = DEFAULT_REPORT_DIR) -> dict[str, Any]:
    report_dir = report_dir.resolve()
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    ignored_files: list[str] = []

    for path in sorted(report_dir.glob("*.json")):
        detected = detect_report(path)
        if not detected:
            ignored_files.append(path.name)
            continue
        kind, date, filename_run = detected
        data = _read_json(path)
        if data is None:
            ignored_files.append(path.name)
            continue
        run_id = _report_run_id(data, filename_run) or "unscoped"
        group_key = (date or str(data.get("date") or "unknown"), str(run_id))
        group = groups.setdefault(group_key, {"reports": {}, "source_files": [], "newest_file_utc": ""})
        group["reports"][kind] = data
        group["source_files"].append(path.name)
        newest = _iso_mtime(path)
        if newest > group["newest_file_utc"]:
            group["newest_file_utc"] = newest

    records = [
        _build_record(date, run_id, group["reports"], group["source_files"], group["newest_file_utc"])
        for (date, run_id), group in groups.items()
    ]
    records.sort(key=lambda item: (item["has_run_id"], item["sort_timestamp_utc"], item["latest_report_file_utc"]), reverse=True)
    latest = next((record for record in records if record["has_run_id"]), records[0] if records else None)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "report_dir": str(report_dir),
        "record_count": len(records),
        "latest_run_id": latest["run_id"] if latest else None,
        "latest_record": latest,
        "records": records,
        "ignored_files": sorted(ignored_files),
        "guardrail": "Read-only dashboard; parses runtime/reports/*.json only and does not write runtime data.",
    }


class OfflineDashboardHandler(BaseHTTPRequestHandler):
    report_dir = DEFAULT_REPORT_DIR

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler name
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._send_bytes(HTML_PATH.read_bytes(), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/reports":
            payload = json.dumps(build_dashboard_payload(self.report_dir), indent=2, sort_keys=True).encode("utf-8")
            self._send_bytes(payload, "application/json; charset=utf-8")
            return
        self.send_error(HTTPStatus.NOT_FOUND, "not found")

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_bytes(self, payload: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only dashboard for offline quant report JSON files.")
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--once", action="store_true", help="Print a compact summary and exit.")
    args = parser.parse_args()

    if args.once:
        payload = build_dashboard_payload(args.reports_dir)
        latest = payload.get("latest_record") or {}
        print(
            "records={records} latest_run_id={run_id} continuity={continuity} root_cause={root}".format(
                records=payload.get("record_count", 0),
                run_id=payload.get("latest_run_id"),
                continuity=_get(latest, ("continuity", "status"), "UNKNOWN"),
                root=_get(latest, ("root_cause", "primary"), "UNKNOWN"),
            )
        )
        return

    OfflineDashboardHandler.report_dir = args.reports_dir
    server = ThreadingHTTPServer((args.host, args.port), OfflineDashboardHandler)
    print(f"Offline Quant Report Dashboard: http://{args.host}:{args.port}")
    print(f"Reading reports from: {args.reports_dir.resolve()}")
    server.serve_forever()


if __name__ == "__main__":
    main()
