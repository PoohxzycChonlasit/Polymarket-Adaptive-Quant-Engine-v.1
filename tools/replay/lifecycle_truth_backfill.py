from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.shadow.cross_run_lifecycle_truth import (
    DEFAULT_MEMORY_INDEX_DIR,
    build_cross_run_lifecycle_truth,
    write_cross_run_lifecycle_truth,
)
from tools.unknown.lifecycle_truth_tables import build_lifecycle_truth_tables, write_lifecycle_truth_tables
from tools.replay_analyzer import DEFAULT_QUANT_DATA_DIR, DEFAULT_REPORT_DIR, RunIdSummary, discover_run_ids


MANIFEST_NAME = "lifecycle_truth_backfill_manifest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"date must be YYYY-MM-DD; got {value!r}") from exc


def _date_in_range(date: str, date_from: str | None, date_to: str | None) -> bool:
    if date_from and date < date_from:
        return False
    if date_to and date > date_to:
        return False
    return True


def _discover_available_dates(base_dir: str | Path, *, date_from: str | None = None, date_to: str | None = None) -> list[str]:
    root = Path(base_dir)
    dates: set[str] = set()
    if not root.exists():
        return []
    for category_dir in root.iterdir():
        if not category_dir.is_dir():
            continue
        for path in category_dir.glob("*.jsonl"):
            date = path.stem[:10]
            if len(date) == 10 and date[4] == "-" and date[7] == "-" and _date_in_range(date, date_from, date_to):
                dates.add(date)
    return sorted(dates)


def _safe_summary_dict(summary: RunIdSummary) -> dict[str, Any]:
    return summary.to_dict() if hasattr(summary, "to_dict") else dict(summary)


def _is_live_mode(summary: RunIdSummary) -> bool:
    return any(str(mode).strip().lower() == "live" for mode in summary.modes)


def _compatibility_from_truth(summary: RunIdSummary, truth: dict[str, Any] | None) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if summary.missing_run_id or summary.run_id == "missing_run_id":
        return "incompatible_legacy", ["missing_run_id_cannot_isolate"]
    if _is_live_mode(summary):
        return "incompatible_legacy", ["live_mode_evidence_skipped"]
    if not truth:
        return "incompatible_legacy", ["truth_table_generation_failed"]

    events_loaded = int(truth.get("events_loaded") or 0)
    candidate_events = int(truth.get("candidate_events") or 0)
    direct_rate = float(truth.get("direct_field_rate") or 0.0)
    proxy_rate = float(truth.get("proxy_field_rate") or 0.0)
    if events_loaded <= 0:
        return "incompatible_legacy", ["no_run_events_loaded"]
    if candidate_events > 0 and direct_rate > 0:
        if proxy_rate > direct_rate:
            reasons.append("proxy_heavy_but_direct_candidate_evidence_present")
        return "compatible", reasons or ["direct_candidate_evidence_present"]
    if candidate_events > 0:
        return "partial_legacy", ["candidate_events_without_direct_field_coverage"]
    return "partial_legacy", ["events_present_but_no_candidate_truth_rows"]


def _entry_from_summary(
    *,
    date: str,
    summary: RunIdSummary,
    compatibility_level: str,
    compatibility_reasons: list[str],
    truth: dict[str, Any] | None = None,
    truth_path: Path | None = None,
) -> dict[str, Any]:
    return {
        "run_id": summary.run_id,
        "date": date,
        "utc_window": {
            "first_timestamp_utc": summary.first_timestamp_utc,
            "last_timestamp_utc": summary.last_timestamp_utc,
        },
        "event_count": summary.event_count,
        "event_categories": list(summary.event_categories),
        "modes": list(summary.modes),
        "compatibility_level": compatibility_level,
        "compatibility_reasons": compatibility_reasons,
        "truth_table_path": truth_path.as_posix() if truth_path else "",
        "replay_truth_confidence": truth.get("replay_truth_confidence", "") if truth else "",
        "replay_truth_quality": truth.get("replay_truth_quality", "") if truth else "",
        "direct_field_rate": truth.get("direct_field_rate") if truth else None,
        "proxy_field_rate": truth.get("proxy_field_rate") if truth else None,
        "events_loaded": truth.get("events_loaded") if truth else 0,
        "candidate_events": truth.get("candidate_events") if truth else 0,
        "bad_json_lines": truth.get("bad_json_lines") if truth else 0,
    }


def build_lifecycle_truth_backfill(
    *,
    base_dir: str | Path = DEFAULT_QUANT_DATA_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    memory_index_dir: str | Path = DEFAULT_MEMORY_INDEX_DIR,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    if date_from:
        _parse_date(date_from)
    if date_to:
        _parse_date(date_to)
    if date_from and date_to and date_from > date_to:
        raise ValueError("--from must be earlier than or equal to --to")

    dates = _discover_available_dates(base_dir, date_from=date_from, date_to=date_to)
    entries: list[dict[str, Any]] = []
    discovered_run_count = 0
    generated_truth_count = 0

    for date in dates:
        summaries = discover_run_ids(base_dir=base_dir, date=date)
        discovered_run_count += len(summaries)
        for summary in summaries:
            if summary.missing_run_id or summary.run_id == "missing_run_id" or _is_live_mode(summary):
                level, reasons = _compatibility_from_truth(summary, None)
                entries.append(
                    _entry_from_summary(
                        date=date,
                        summary=summary,
                        compatibility_level=level,
                        compatibility_reasons=reasons,
                    )
                )
                continue

            truth: dict[str, Any] | None = None
            truth_path: Path | None = None
            try:
                truth = build_lifecycle_truth_tables(base_dir=base_dir, date=date, run_id=summary.run_id)
                level, reasons = _compatibility_from_truth(summary, truth)
                if level in {"compatible", "partial_legacy"}:
                    truth_path = write_lifecycle_truth_tables(truth, report_dir=report_dir)
                    generated_truth_count += 1
            except Exception as exc:  # noqa: BLE001 - manifest should preserve failures without aborting backfill.
                level = "incompatible_legacy"
                reasons = [f"truth_table_generation_error:{type(exc).__name__}"]
                truth = None
                truth_path = None

            entries.append(
                _entry_from_summary(
                    date=date,
                    summary=summary,
                    compatibility_level=level,
                    compatibility_reasons=reasons,
                    truth=truth,
                    truth_path=truth_path,
                )
            )

    compatibility_counts = Counter(entry["compatibility_level"] for entry in entries)
    cross_run_report: dict[str, Any] | None = None
    cross_run_path: Path | None = None
    if dates:
        cross_run_report = build_cross_run_lifecycle_truth(
            report_dir=report_dir,
            memory_index_dir=memory_index_dir,
            date_from=dates[0],
            date_to=dates[-1],
        )
        cross_run_path = write_cross_run_lifecycle_truth(cross_run_report, report_dir=report_dir)

    return {
        "generated_at_utc": _utc_now(),
        "scope": "offline_research_replay_only",
        "does_not_claim_profitability": True,
        "does_not_authorize_runtime_decisions": True,
        "does_not_implement_inventory_execution": True,
        "base_dir": str(base_dir),
        "report_dir": str(report_dir),
        "date_from": dates[0] if dates else (date_from or ""),
        "date_to": dates[-1] if dates else (date_to or date_from or ""),
        "dates_discovered": dates,
        "historical_run_counts": {
            "dates": len(dates),
            "run_ids_discovered": discovered_run_count,
            "truth_tables_generated": generated_truth_count,
        },
        "compatibility_counts": dict(compatibility_counts),
        "runs": entries,
        "cross_run_lifecycle_truth": {
            "path": cross_run_path.as_posix() if cross_run_path else "",
            "repeated_failure_confidence": cross_run_report.get("repeated_failure_confidence") if cross_run_report else "",
            "replay_truth_maturity": cross_run_report.get("replay_truth_maturity") if cross_run_report else "",
            "direct_field_maturity": cross_run_report.get("direct_field_maturity") if cross_run_report else "",
            "runs_analyzed": cross_run_report.get("aggregate", {}).get("runs_analyzed") if cross_run_report else 0,
            "candidate_events": cross_run_report.get("aggregate", {}).get("candidate_events") if cross_run_report else 0,
            "recurring_root_causes": cross_run_report.get("recurring_root_causes", [])[:8] if cross_run_report else [],
        },
    }


def write_lifecycle_truth_backfill_manifest(
    manifest: dict[str, Any],
    *,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / MANIFEST_NAME
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return path


def print_summary(manifest: dict[str, Any]) -> None:
    counts = manifest.get("historical_run_counts", {})
    compat = manifest.get("compatibility_counts", {})
    cross = manifest.get("cross_run_lifecycle_truth", {})
    print("Lifecycle Truth Backfill")
    print(
        "dates={dates} run_ids={runs} generated_truth_tables={truth_tables} compatible={compatible} partial_legacy={partial} incompatible_legacy={incompatible}".format(
            dates=counts.get("dates", 0),
            runs=counts.get("run_ids_discovered", 0),
            truth_tables=counts.get("truth_tables_generated", 0),
            compatible=compat.get("compatible", 0),
            partial=compat.get("partial_legacy", 0),
            incompatible=compat.get("incompatible_legacy", 0),
        )
    )
    print(
        "cross_run_runs={runs} repeated_failure_confidence={confidence} replay_truth_maturity={maturity}".format(
            runs=cross.get("runs_analyzed", 0),
            confidence=cross.get("repeated_failure_confidence", ""),
            maturity=cross.get("replay_truth_maturity", ""),
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill offline lifecycle truth tables for historical paper run IDs.")
    parser.add_argument("--from", dest="date_from", default=None, help="Optional start date in YYYY-MM-DD format.")
    parser.add_argument("--to", dest="date_to", default=None, help="Optional end date in YYYY-MM-DD format.")
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR), help="Quant JSONL data root.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Report output directory.")
    parser.add_argument("--memory-index-dir", default=str(DEFAULT_MEMORY_INDEX_DIR), help="Research memory index directory for cross-run rerun.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = build_lifecycle_truth_backfill(
        base_dir=args.base_dir,
        report_dir=args.report_dir,
        memory_index_dir=args.memory_index_dir,
        date_from=args.date_from,
        date_to=args.date_to,
    )
    path = write_lifecycle_truth_backfill_manifest(manifest, report_dir=args.report_dir)
    print_summary(manifest)
    print(f"wrote_manifest={path}")
    cross_path = manifest.get("cross_run_lifecycle_truth", {}).get("path")
    if cross_path:
        print(f"wrote_cross_run_report={cross_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
