"""
No-Entry Root Cause Report v1.

Offline aggregation tool that reads decision_log JSONL and optional research_log
lifecycle milestone events to produce structured no-entry diagnostics.

Usage:
    python -m tools.no_entry_root_cause_report --date 2026-05-14
    python -m tools.no_entry_root_cause_report --date 2026-05-14 --write-report
    python -m tools.no_entry_root_cause_report --date 2026-05-14 --run-id <run_id>

Output:
    Console summary + optional runtime/reports/no_entry_root_cause_YYYY-MM-DD.json

This tool is offline-only. It does not change runtime behavior, strategy, risk,
execution, or paper/live separation.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    _repo_root = Path(__file__).resolve().parents[1]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

from utils.no_entry_root_cause_classifier import classify_no_entry_root_cause

DEFAULT_QUANT_DATA_DIR = Path("runtime/quant_data")
DEFAULT_REPORT_DIR = Path("runtime/reports")


# ---------------------------------------------------------------------------
# JSONL reader
# ---------------------------------------------------------------------------

def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass
    return events


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    p = event.get("payload") or {}
    if not isinstance(p, dict):
        p = {}
    return p


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_decision_events(
    date_str: str,
    quant_data_dir: Path = DEFAULT_QUANT_DATA_DIR,
    run_id: str | None = None,
) -> list[dict[str, Any]]:
    path = quant_data_dir / "decision_log" / f"{date_str}.jsonl"
    events = _read_jsonl(path)
    if run_id:
        events = [e for e in events if e.get("run_id") == run_id]
    return events


def load_milestone_events(
    date_str: str,
    quant_data_dir: Path = DEFAULT_QUANT_DATA_DIR,
    run_id: str | None = None,
) -> dict[tuple[str, int], list[str]]:
    """
    Returns mapping of (ticker, epoch_start) -> [milestone_names reached].
    """
    path = quant_data_dir / "research_log" / f"{date_str}.jsonl"
    events = _read_jsonl(path)
    if run_id:
        events = [e for e in events if e.get("run_id") == run_id]
    index: dict[tuple[str, int], list[str]] = defaultdict(list)
    for event in events:
        p = _payload(event)
        if p.get("event_subtype") != "lifecycle_milestone":
            continue
        ticker = str(p.get("ticker") or "").upper()
        epoch = int(p.get("market_epoch_start") or 0)
        milestone = str(p.get("lifecycle_phase") or "")
        if ticker and epoch and milestone:
            key = (ticker, epoch)
            if milestone not in index[key]:
                index[key].append(milestone)
    return dict(index)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

_ORDERED_MILESTONES = [
    "market_discovered",
    "token_ready",
    "first_orderbook_seen",
    "first_nonzero_book",
    "first_normalized_book",
    "first_executable_book",
    "first_decision_evaluable",
]


def _highest_milestone_reached(milestone_list: list[str]) -> str:
    reached = set(milestone_list)
    for m in reversed(_ORDERED_MILESTONES):
        if m in reached:
            return m
    return ""


def build_records(
    decision_events: list[dict[str, Any]],
    milestone_index: dict[tuple[str, int], list[str]],
) -> list[dict[str, Any]]:
    """
    Enrich each skipped decision event with root-cause classification + milestone context.
    Returns one record per skipped event.
    """
    records: list[dict[str, Any]] = []
    for event in decision_events:
        p = _payload(event)
        if not p.get("skipped", True) and p.get("decision") not in {None, "", "skip"}:
            continue  # keep only skipped events

        ticker = str(p.get("asset") or p.get("ticker") or "").upper()
        epoch = int(p.get("market_epoch_start") or p.get("epoch_start") or 0)
        milestones = milestone_index.get((ticker, epoch), [])
        highest = _highest_milestone_reached(milestones)

        enriched = dict(p)
        enriched["_milestones_reached"] = milestones
        enriched["_highest_milestone"] = highest
        enriched["run_id"] = event.get("run_id", "")
        enriched["timestamp_utc"] = event.get("timestamp_utc", "")

        # If root-cause fields already present (emitted at runtime), use them.
        # Otherwise classify offline from payload.
        if not enriched.get("skip_reason_category"):
            classification = classify_no_entry_root_cause(enriched)
            for k, v in classification.items():
                if k not in enriched or enriched[k] in (None, ""):
                    enriched[k] = v

        records.append(enriched)
    return records


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    category_counts: Counter[str] = Counter()
    primary_counts: Counter[str] = Counter()
    asset_counts: dict[str, Counter[str]] = defaultdict(Counter)
    lifecycle_phase_counts: Counter[str] = Counter()
    highest_milestone_counts: Counter[str] = Counter()
    confidence_buckets: Counter[str] = Counter()
    unknown_count = 0
    timing_stage_corr: Counter[str] = Counter()

    for r in records:
        cat = str(r.get("skip_reason_category") or "system_or_unknown")
        primary = str(r.get("skip_reason_primary") or "unclassified")
        asset = str(r.get("asset") or r.get("ticker") or "UNKNOWN").upper()
        lc_phase = str(r.get("lifecycle_phase") or "UNKNOWN")
        highest = str(r.get("_highest_milestone") or "none_reached")
        conf = float(r.get("no_entry_root_cause_confidence") or 0.1)

        category_counts[cat] += 1
        primary_counts[primary] += 1
        asset_counts[asset][cat] += 1
        lifecycle_phase_counts[lc_phase] += 1
        highest_milestone_counts[highest] += 1

        if cat == "system_or_unknown":
            unknown_count += 1

        # Confidence bucket
        if conf >= 0.85:
            confidence_buckets["high_0.85+"] += 1
        elif conf >= 0.6:
            confidence_buckets["medium_0.60-0.84"] += 1
        elif conf >= 0.3:
            confidence_buckets["low_0.30-0.59"] += 1
        else:
            confidence_buckets["very_low_<0.30"] += 1

        # Timing-stage correlation: when timing was the block, which milestone was highest?
        if cat == "timing":
            timing_stage_corr[highest] += 1

    return {
        "total_skipped_events": total,
        "unknown_unclassified_count": unknown_count,
        "unknown_rate": round(unknown_count / total, 3) if total else 0.0,
        "category_counts": dict(category_counts.most_common()),
        "primary_reason_counts": dict(primary_counts.most_common(20)),
        "confidence_distribution": dict(confidence_buckets),
        "asset_category_breakdown": {k: dict(v) for k, v in sorted(asset_counts.items())},
        "lifecycle_phase_distribution": dict(lifecycle_phase_counts.most_common()),
        "highest_milestone_at_skip": dict(highest_milestone_counts.most_common()),
        "timing_block_stage_correlation": dict(timing_stage_corr.most_common()),
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_console(summary: dict[str, Any], date_str: str) -> None:
    total = summary["total_skipped_events"]
    unknown = summary["unknown_unclassified_count"]
    print(f"\n{'='*60}")
    print(f"  No-Entry Root Cause Report v1  |  {date_str}")
    print(f"{'='*60}")
    print(f"  Total skipped events  : {total}")
    print(f"  Unclassified / unknown: {unknown} ({summary['unknown_rate']*100:.1f}%)")
    print()

    print("  -- By Category --")
    for cat, count in summary["category_counts"].items():
        pct = count / total * 100 if total else 0
        print(f"    {cat:<25} {count:>5}  ({pct:.1f}%)")

    print()
    print("  -- Top Primary Reasons --")
    for reason, count in list(summary["primary_reason_counts"].items())[:10]:
        pct = count / total * 100 if total else 0
        print(f"    {reason:<35} {count:>5}  ({pct:.1f}%)")

    print()
    print("  -- Asset Breakdown --")
    for asset, cats in summary["asset_category_breakdown"].items():
        asset_total = sum(cats.values())
        print(f"    {asset}: {asset_total} events — {cats}")

    print()
    print("  -- Highest Lifecycle Milestone at Skip --")
    for milestone, count in summary["highest_milestone_at_skip"].items():
        pct = count / total * 100 if total else 0
        print(f"    {milestone:<35} {count:>5}  ({pct:.1f}%)")

    print()
    print("  -- Timing Block Stage Correlation --")
    timing_corr = summary["timing_block_stage_correlation"]
    if timing_corr:
        for stage, count in timing_corr.items():
            print(f"    stopped_at={stage:<30} {count:>5}")
    else:
        print("    (no timing-category events)")

    print()
    print("  -- Confidence Distribution --")
    for bucket, count in summary["confidence_distribution"].items():
        pct = count / total * 100 if total else 0
        print(f"    {bucket:<30} {count:>5}  ({pct:.1f}%)")
    print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="No-Entry Root Cause Report v1")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument("--run-id", default=None, help="Filter to a specific run_id")
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write JSON report to runtime/reports/",
    )
    parser.add_argument(
        "--quant-data-dir",
        default=str(DEFAULT_QUANT_DATA_DIR),
        help="Base quant data directory",
    )
    parser.add_argument(
        "--report-dir",
        default=str(DEFAULT_REPORT_DIR),
        help="Output report directory",
    )
    args = parser.parse_args(argv)

    date_str = args.date
    quant_data_dir = Path(args.quant_data_dir)
    report_dir = Path(args.report_dir)

    print(f"Loading decision events for {date_str} ...")
    decisions = load_decision_events(date_str, quant_data_dir, run_id=args.run_id)
    print(f"  decision_log events loaded: {len(decisions)}")

    print(f"Loading lifecycle milestone events for {date_str} ...")
    milestones = load_milestone_events(date_str, quant_data_dir, run_id=args.run_id)
    print(f"  milestone index entries: {len(milestones)}")

    records = build_records(decisions, milestones)
    print(f"  skipped records to classify: {len(records)}")

    if not records:
        print("No skipped decision events found. Nothing to report.")
        return

    summary = aggregate(records)
    summary["date"] = date_str
    summary["generated_at"] = datetime.now(timezone.utc).isoformat()
    summary["run_id_filter"] = args.run_id or "all"
    summary["source"] = "no_entry_root_cause_report_v1"
    summary["guardrail"] = (
        "Offline observability only. Does not change runtime, strategy, risk, execution, or live flags."
    )

    render_console(summary, date_str)

    if args.write_report:
        report_dir.mkdir(parents=True, exist_ok=True)
        out_path = report_dir / f"no_entry_root_cause_{date_str}.json"
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2, default=str)
        print(f"  Report written to: {out_path}")


if __name__ == "__main__":
    main()
