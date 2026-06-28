"""
EV Field Coverage Audit v1.

Offline-only audit of EV/probability/fair-value field completeness and
reliability in runtime decision snapshots.

Reads decision_log/ and research_log/ JSONL.
Computes field coverage %, null/missing rates, missing_reason frequency,
and correlation breakdowns by lifecycle_phase, skip_reason_category,
dominant_latency_stage, and asset.

Usage:
    python -m tools.unknown.ev_field_coverage_audit --date 2026-05-15
    python -m tools.unknown.ev_field_coverage_audit --date 2026-05-15 --write-report
    python -m tools.unknown.ev_field_coverage_audit --date 2026-05-15 --run-id <id>
    python -m tools.unknown.ev_field_coverage_audit --date 2026-05-15 --asset BTC

Output:
    Console summary + optional runtime/reports/ev_field_coverage_YYYY-MM-DD.json

This tool is offline-only. It does not change runtime, strategy, risk,
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

DEFAULT_QUANT_DATA_DIR = Path("runtime/quant_data")
DEFAULT_REPORT_DIR = Path("runtime/reports")

# ---------------------------------------------------------------------------
# Canonical audit field definitions
# Each entry: (canonical_name, (alias, ...), null_reason_field | None)
# "Present" = any alias exists in payload AND value is not None/""
# ---------------------------------------------------------------------------

AUDIT_FIELDS: list[tuple[str, tuple[str, ...], str | None]] = [
    (
        "probability_yes",
        ("true_probability", "model_probability_yes", "p_yes", "model_p_yes",
         "fair_value_yes", "probability_yes"),
        "true_probability_null_reason",
    ),
    (
        "probability_confidence",
        ("true_probability_available", "fair_value_available",
         "probability_model_output_visible", "model_output_visible",
         "probability_confidence"),
        "model_output_missing_reason",
    ),
    (
        "fair_value",
        ("fair_value", "fair_value_yes", "fair_value_no", "model_fair_value"),
        "fair_value_null_reason",
    ),
    (
        "edge_bps",
        ("edge", "ev", "ev_after_spread", "edge_bps", "executable_ev"),
        "ev_after_spread_null_reason",
    ),
    (
        "spread_bps",
        ("spread", "spread_normalized", "spread_bps", "spread_gap_to_limit"),
        None,
    ),
    (
        "bid",
        ("yes_bid", "no_bid", "orderbook_bid", "bid", "best_bid"),
        None,
    ),
    (
        "ask",
        ("yes_ask", "no_ask", "orderbook_ask", "ask", "best_ask"),
        None,
    ),
    (
        "mid_price",
        ("yes_mid", "no_mid", "mid_price", "mid"),
        None,
    ),
    (
        "book_imbalance",
        ("orderbook_imbalance", "book_imbalance", "imbalance"),
        None,
    ),
    (
        "top_depth_yes",
        ("yes_bid_size", "yes_ask_size", "top_depth_yes"),
        None,
    ),
    (
        "top_depth_no",
        ("no_bid_size", "no_ask_size", "top_depth_no"),
        None,
    ),
    (
        "ev_per_dollar",
        ("ev_per_dollar", "ev_after_spread", "ev", "edge"),
        "ev_after_spread_null_reason",
    ),
    (
        "planned_size",
        ("planned_size", "risk_plan_size", "position_size", "size"),
        None,
    ),
    (
        "data_quality_score",
        ("data_quality_score", "quality_score", "data_quality"),
        None,
    ),
]

# Aliases for quick lookup by canonical name
_FIELD_ALIASES: dict[str, tuple[str, ...]] = {name: aliases for name, aliases, _ in AUDIT_FIELDS}
_FIELD_NULL_REASON: dict[str, str | None] = {name: nr for name, _, nr in AUDIT_FIELDS}
CANONICAL_NAMES: tuple[str, ...] = tuple(name for name, _, _ in AUDIT_FIELDS)


# ---------------------------------------------------------------------------
# JSONL reading
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
    return p if isinstance(p, dict) else {}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_decision_events(
    date_str: str,
    quant_data_dir: Path = DEFAULT_QUANT_DATA_DIR,
    run_id: str | None = None,
    asset_filter: str | None = None,
) -> list[dict[str, Any]]:
    path = quant_data_dir / "decision_log" / f"{date_str}.jsonl"
    events = _read_jsonl(path)
    if run_id:
        events = [e for e in events if e.get("run_id") == run_id]
    if asset_filter:
        af = asset_filter.upper()
        filtered = []
        for e in events:
            p = _payload(e)
            asset = str(p.get("asset") or p.get("ticker") or "").upper()
            if asset == af:
                filtered.append(e)
        events = filtered
    return events


def load_research_events(
    date_str: str,
    quant_data_dir: Path = DEFAULT_QUANT_DATA_DIR,
    run_id: str | None = None,
) -> list[dict[str, Any]]:
    path = quant_data_dir / "research_log" / f"{date_str}.jsonl"
    events = _read_jsonl(path)
    if run_id:
        events = [e for e in events if e.get("run_id") == run_id]
    return events


# ---------------------------------------------------------------------------
# Field presence check
# ---------------------------------------------------------------------------

def _field_present(payload: dict[str, Any], canonical: str) -> bool:
    """True if any alias exists in payload with a non-null, non-empty value."""
    for alias in _FIELD_ALIASES[canonical]:
        v = payload.get(alias)
        if v is not None and v != "" and v is not False:
            return True
    return False


def _field_value(payload: dict[str, Any], canonical: str) -> Any:
    """Return first non-null value found across aliases, or None."""
    for alias in _FIELD_ALIASES[canonical]:
        v = payload.get(alias)
        if v is not None and v != "":
            return v
    return None


def _null_reason(payload: dict[str, Any], canonical: str) -> str:
    nr_field = _FIELD_NULL_REASON.get(canonical)
    if not nr_field:
        return ""
    v = payload.get(nr_field)
    return str(v).strip() if v else ""


# ---------------------------------------------------------------------------
# Per-event record extraction
# ---------------------------------------------------------------------------

def extract_record(event: dict[str, Any]) -> dict[str, Any]:
    """
    Extract audit-relevant fields from a single decision_log event.
    Returns a flat record dict — does not mutate the original event.
    """
    p = _payload(event)
    asset = str(p.get("asset") or p.get("ticker") or "UNKNOWN").upper()
    lifecycle_phase = str(p.get("lifecycle_phase") or "UNKNOWN")
    skip_reason_cat = str(p.get("skip_reason_category") or "")
    dominant_latency = str(p.get("dominant_latency_stage") or
                           p.get("dominant_latency_stage_so_far") or "")
    skipped = bool(p.get("skipped", True))

    coverage: dict[str, bool] = {}
    null_reasons: dict[str, str] = {}
    for canonical in CANONICAL_NAMES:
        coverage[canonical] = _field_present(p, canonical)
        nr = _null_reason(p, canonical)
        if nr:
            null_reasons[canonical] = nr

    return {
        "asset": asset,
        "lifecycle_phase": lifecycle_phase,
        "skip_reason_category": skip_reason_cat,
        "dominant_latency_stage": dominant_latency,
        "skipped": skipped,
        "coverage": coverage,
        "null_reasons": null_reasons,
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute coverage statistics from extracted records.
    Returns structured summary dict — does not mutate records.
    """
    if not records:
        return {
            "total_events": 0,
            "guardrail": "no data",
        }

    total = len(records)

    # --- Per-field coverage counts ---
    present_counts: dict[str, int] = {c: 0 for c in CANONICAL_NAMES}
    null_reason_counts: dict[str, Counter[str]] = {c: Counter() for c in CANONICAL_NAMES}

    for r in records:
        for canonical in CANONICAL_NAMES:
            if r["coverage"][canonical]:
                present_counts[canonical] += 1
            nr = r["null_reasons"].get(canonical, "")
            if nr:
                null_reason_counts[canonical][nr] += 1

    field_coverage: dict[str, dict[str, Any]] = {}
    for canonical in CANONICAL_NAMES:
        present = present_counts[canonical]
        missing = total - present
        field_coverage[canonical] = {
            "present": present,
            "missing": missing,
            "coverage_pct": round(present / total * 100, 1) if total else 0.0,
            "missing_pct": round(missing / total * 100, 1) if total else 0.0,
            "top_null_reasons": dict(null_reason_counts[canonical].most_common(5)),
        }

    # --- Overall coverage tier ---
    coverage_pcts = [field_coverage[c]["coverage_pct"] for c in CANONICAL_NAMES]
    mean_coverage = round(sum(coverage_pcts) / len(coverage_pcts), 1) if coverage_pcts else 0.0
    fully_covered = sum(1 for p in coverage_pcts if p >= 99.0)
    well_covered = sum(1 for p in coverage_pcts if 70.0 <= p < 99.0)
    partial = sum(1 for p in coverage_pcts if 10.0 <= p < 70.0)
    absent = sum(1 for p in coverage_pcts if p < 10.0)

    # --- Asset breakdown ---
    asset_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        asset_records[r["asset"]].append(r)

    asset_coverage: dict[str, dict[str, float]] = {}
    for asset, arecs in sorted(asset_records.items()):
        n = len(arecs)
        asset_coverage[asset] = {
            c: round(sum(1 for r in arecs if r["coverage"][c]) / n * 100, 1)
            for c in CANONICAL_NAMES
        }
        asset_coverage[asset]["_total_events"] = n  # type: ignore[assignment]

    # --- Lifecycle phase correlation: coverage by phase ---
    phase_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        phase_records[r["lifecycle_phase"]].append(r)

    phase_coverage: dict[str, dict[str, Any]] = {}
    for phase, precs in sorted(phase_records.items()):
        n = len(precs)
        # Report mean coverage pct per phase (not per-field, to keep output compact)
        field_pcts = {}
        for c in CANONICAL_NAMES:
            field_pcts[c] = round(sum(1 for r in precs if r["coverage"][c]) / n * 100, 1)
        mean = round(sum(field_pcts.values()) / len(field_pcts), 1) if field_pcts else 0.0
        phase_coverage[phase] = {
            "event_count": n,
            "mean_field_coverage_pct": mean,
            "per_field": field_pcts,
        }

    # --- Skip reason category correlation ---
    cat_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        cat = r["skip_reason_category"] or "unknown"
        cat_records[cat].append(r)

    category_coverage: dict[str, dict[str, Any]] = {}
    for cat, crecs in sorted(cat_records.items()):
        n = len(crecs)
        field_pcts = {}
        for c in CANONICAL_NAMES:
            field_pcts[c] = round(sum(1 for r in crecs if r["coverage"][c]) / n * 100, 1)
        mean = round(sum(field_pcts.values()) / len(field_pcts), 1) if field_pcts else 0.0
        category_coverage[cat] = {
            "event_count": n,
            "mean_field_coverage_pct": mean,
            "per_field": field_pcts,
        }

    # --- Dominant latency stage correlation ---
    latency_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        stage = r["dominant_latency_stage"] or "UNKNOWN"
        latency_records[stage].append(r)

    latency_stage_coverage: dict[str, dict[str, Any]] = {}
    for stage, lrecs in sorted(latency_records.items()):
        n = len(lrecs)
        field_pcts = {}
        for c in CANONICAL_NAMES:
            field_pcts[c] = round(sum(1 for r in lrecs if r["coverage"][c]) / n * 100, 1)
        mean = round(sum(field_pcts.values()) / len(field_pcts), 1) if field_pcts else 0.0
        latency_stage_coverage[stage] = {
            "event_count": n,
            "mean_field_coverage_pct": mean,
            "per_field": field_pcts,
        }

    # --- Missing rate by field (sorted worst-first) ---
    missing_ranked = sorted(
        CANONICAL_NAMES,
        key=lambda c: field_coverage[c]["missing_pct"],
        reverse=True,
    )

    return {
        "total_events": total,
        "mean_field_coverage_pct": mean_coverage,
        "coverage_tier_summary": {
            "fully_covered_99pct+": fully_covered,
            "well_covered_70-99pct": well_covered,
            "partial_10-69pct": partial,
            "absent_lt10pct": absent,
        },
        "field_coverage": field_coverage,
        "missing_rank": missing_ranked,
        "asset_coverage": asset_coverage,
        "lifecycle_phase_coverage": phase_coverage,
        "skip_reason_category_coverage": category_coverage,
        "dominant_latency_stage_coverage": latency_stage_coverage,
    }


# ---------------------------------------------------------------------------
# Console rendering
# ---------------------------------------------------------------------------

def render_console(summary: dict[str, Any], date_str: str) -> None:
    total = summary.get("total_events", 0)
    if not total:
        print(f"\nNo decision events found for {date_str}. "
              "Verify decision_log JSONL exists.")
        return

    print(f"\n{'='*68}")
    print(f"  EV Field Coverage Audit v1  |  {date_str}")
    print(f"{'='*68}")
    print(f"  Total events    : {total}")
    print(f"  Mean coverage   : {summary['mean_field_coverage_pct']:.1f}%")
    tiers = summary["coverage_tier_summary"]
    print(f"  Fully covered   : {tiers['fully_covered_99pct+']} fields (>=99%)")
    print(f"  Well covered    : {tiers['well_covered_70-99pct']} fields (70-99%)")
    print(f"  Partial         : {tiers['partial_10-69pct']} fields (10-69%)")
    print(f"  Absent          : {tiers['absent_lt10pct']} fields (<10%)")
    print()

    print(f"  {'Field':<26} {'Present':>8} {'Missing':>8} {'Coverage':>10} {'Top Null Reason'}")
    print(f"  {'-'*26} {'-'*8} {'-'*8} {'-'*10} {'-'*28}")
    fc = summary["field_coverage"]
    for canonical in summary["missing_rank"]:
        s = fc[canonical]
        top_nr = next(iter(s["top_null_reasons"]), "") if s["top_null_reasons"] else ""
        cov_str = f"{s['coverage_pct']:>5.1f}%"
        miss_str = f"{s['missing_pct']:>5.1f}%"
        print(f"  {canonical:<26} {s['present']:>8} {s['missing']:>8} "
              f"  {cov_str}   {top_nr[:30]}")

    print()
    print("  -- BTC vs ETH Coverage (mean %) --")
    for asset, ac in summary["asset_coverage"].items():
        n = ac.get("_total_events", 0)
        mean = round(
            sum(v for k, v in ac.items() if k != "_total_events") / len(CANONICAL_NAMES),
            1,
        )
        print(f"    {asset:<6}: mean={mean:.1f}%  N={n}")

    print()
    print("  -- Coverage by Lifecycle Phase (mean %) --")
    for phase, ps in sorted(summary["lifecycle_phase_coverage"].items(),
                             key=lambda x: -x[1]["mean_field_coverage_pct"]):
        print(f"    {phase:<30} mean={ps['mean_field_coverage_pct']:>5.1f}%  "
              f"N={ps['event_count']}")

    print()
    print("  -- Coverage by Skip Reason Category --")
    for cat, cs in sorted(summary["skip_reason_category_coverage"].items(),
                           key=lambda x: -x[1]["mean_field_coverage_pct"]):
        print(f"    {cat:<28} mean={cs['mean_field_coverage_pct']:>5.1f}%  "
              f"N={cs['event_count']}")

    print()
    print("  -- Coverage by Dominant Latency Stage --")
    for stage, ls in sorted(summary["dominant_latency_stage_coverage"].items(),
                             key=lambda x: -x[1]["mean_field_coverage_pct"]):
        print(f"    {stage:<25} mean={ls['mean_field_coverage_pct']:>5.1f}%  "
              f"N={ls['event_count']}")

    print()

    print("  -- Worst Coverage Fields (bottom 5) --")
    for canonical in summary["missing_rank"][:5]:
        s = fc[canonical]
        print(f"    {canonical:<26} {s['coverage_pct']:>5.1f}%  "
              f"missing_reasons={s['top_null_reasons']}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="EV Field Coverage Audit v1")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument("--run-id", default=None, help="Filter to a specific run_id")
    parser.add_argument("--asset", default=None, help="Filter to BTC or ETH")
    parser.add_argument(
        "--write-report", action="store_true",
        help="Write JSON report to runtime/reports/",
    )
    parser.add_argument(
        "--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR),
    )
    parser.add_argument(
        "--report-dir", default=str(DEFAULT_REPORT_DIR),
    )
    args = parser.parse_args(argv)

    date_str = args.date
    quant_data_dir = Path(args.quant_data_dir)
    report_dir = Path(args.report_dir)

    print(f"Loading decision_log for {date_str} ...")
    decision_events = load_decision_events(
        date_str, quant_data_dir, run_id=args.run_id, asset_filter=args.asset,
    )
    print(f"  decision events loaded: {len(decision_events)}")

    if not decision_events:
        print("No decision events found. Nothing to audit.")
        return

    records = [extract_record(e) for e in decision_events]
    summary = aggregate(records)
    summary["date"] = date_str
    summary["asset_filter"] = args.asset or "all"
    summary["run_id_filter"] = args.run_id or "all"
    summary["generated_at"] = datetime.now(timezone.utc).isoformat()
    summary["source"] = "ev_field_coverage_audit_v1"
    summary["guardrail"] = (
        "Offline observability only. Does not change runtime, strategy, "
        "risk, execution, or paper/live separation."
    )

    render_console(summary, date_str)

    if args.write_report:
        report_dir.mkdir(parents=True, exist_ok=True)
        out_path = report_dir / f"ev_field_coverage_{date_str}.json"
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2, default=str)
        print(f"  Report written to: {out_path}")


if __name__ == "__main__":
    main()
