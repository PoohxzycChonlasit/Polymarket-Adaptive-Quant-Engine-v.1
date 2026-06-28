"""
Lifecycle Latency Report Tool v1.

Offline-only aggregation of lifecycle timing stages from research_log and
decision_log JSONL. Correlates latency with no-entry root cause classifications.

Usage:
    python -m tools.lifecycle_latency_report --date 2026-05-14
    python -m tools.lifecycle_latency_report --date 2026-05-14 --write-report
    python -m tools.lifecycle_latency_report --date 2026-05-14 --run-id <run_id>
    python -m tools.lifecycle_latency_report --date 2026-05-14 --asset BTC

Output:
    Console summary + optional runtime/reports/lifecycle_latency_YYYY-MM-DD.json

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

# Stage name → JSONL ms-duration field
STAGE_FIELDS: dict[str, str] = {
    "DISCOVERY":           "discovery_to_token_ready_ms",
    "TOKEN_READY":         "token_ready_to_book_ms",
    "ORDERBOOK":           "book_to_nonzero_ms",
    "SPREAD_NORMALIZATION":"nonzero_to_normalized_ms",
    "DECISION":            "normalized_to_executable_ms",
    "CUTOFF":              "executable_to_decision_ms",
    "TOTAL":               "total_discovery_to_decision_ms",
}

# Ordered milestone names from Lifecycle Early Snapshot Emission v1
ORDERED_MILESTONES = [
    "market_discovered",
    "token_ready",
    "first_orderbook_seen",
    "first_nonzero_book",
    "first_normalized_book",
    "first_executable_book",
    "first_decision_evaluable",
]


# ---------------------------------------------------------------------------
# Pure utilities
# ---------------------------------------------------------------------------

def _percentile(values: list[float], p: int) -> float:
    """Compute p-th percentile from a list. No numpy required."""
    if not values:
        return 0.0
    s = sorted(values)
    idx = (p / 100.0) * (len(s) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(s) - 1)
    frac = idx - lo
    return round(s[lo] + frac * (s[hi] - s[lo]), 1)


def _pct_stats(values: list[float]) -> dict[str, float]:
    """Return P50/P90/P99/mean/count for a value list."""
    if not values:
        return {"p50": 0.0, "p90": 0.0, "p99": 0.0, "mean": 0.0, "count": 0}
    return {
        "p50":   _percentile(values, 50),
        "p90":   _percentile(values, 90),
        "p99":   _percentile(values, 99),
        "mean":  round(sum(values) / len(values), 1),
        "count": len(values),
    }


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


def _safe_float(v: Any) -> float | None:
    try:
        f = float(v)
        return f if f >= 0 else None
    except (TypeError, ValueError):
        return None


def _safe_int(v: Any) -> int | None:
    try:
        return int(v) if v is not None and str(v).strip() != "" else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_research_snapshots(
    date_str: str,
    quant_data_dir: Path = DEFAULT_QUANT_DATA_DIR,
    run_id: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Load research_log JSONL and split into:
      - latency_snapshots: events with latency ms fields (from _emit_hybrid_v1_snapshot)
      - milestone_events: events with event_subtype=lifecycle_milestone
    Returns (latency_snapshots, milestone_events).
    """
    path = quant_data_dir / "research_log" / f"{date_str}.jsonl"
    events = _read_jsonl(path)
    if run_id:
        events = [e for e in events if e.get("run_id") == run_id]
    latency: list[dict[str, Any]] = []
    milestones: list[dict[str, Any]] = []
    for event in events:
        p = _payload(event)
        if p.get("event_subtype") == "lifecycle_milestone":
            milestones.append(event)
        elif "discovery_to_token_ready_ms" in p or "total_discovery_to_decision_ms" in p:
            latency.append(event)
    return latency, milestones


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


# ---------------------------------------------------------------------------
# Record building — merge per-(ticker, epoch) across sources
# ---------------------------------------------------------------------------

def build_latency_records(
    latency_snapshots: list[dict[str, Any]],
    milestone_events: list[dict[str, Any]],
    decision_events: list[dict[str, Any]],
    asset_filter: str | None = None,
) -> list[dict[str, Any]]:
    """
    Merge latency snapshots, milestone events, and decision events into
    per-(ticker, epoch) records containing all available latency and
    classification fields.
    """
    # Index decision events by (ticker, epoch)
    decision_index: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for ev in decision_events:
        p = _payload(ev)
        ticker = str(p.get("asset") or p.get("ticker") or "").upper()
        epoch = _safe_int(p.get("market_epoch_start") or p.get("epoch_start")) or 0
        if ticker and epoch:
            decision_index[(ticker, epoch)].append(p)

    # Index milestone events by (ticker, epoch) → {milestone_name: seconds_since_open}
    milestone_index: dict[tuple[str, int], dict[str, int]] = defaultdict(dict)
    for ev in milestone_events:
        p = _payload(ev)
        ticker = str(p.get("ticker") or "").upper()
        epoch = _safe_int(p.get("market_epoch_start")) or 0
        milestone = str(p.get("lifecycle_phase") or "")
        sso = _safe_int(p.get("seconds_since_market_open"))
        if ticker and epoch and milestone:
            milestone_index[(ticker, epoch)][milestone] = sso if sso is not None else 0

    # Build one record per unique (ticker, epoch) from latency snapshots.
    # If multiple snapshots exist for the same key, use the one with the highest total_ms.
    snap_index: dict[tuple[str, int], dict[str, Any]] = {}
    for ev in latency_snapshots:
        p = _payload(ev)
        ticker = str(p.get("ticker") or "").upper()
        epoch = _safe_int(p.get("market_epoch_start") or p.get("epoch_start")) or 0
        if not ticker or not epoch:
            continue
        total = _safe_float(p.get("total_discovery_to_decision_ms")) or 0.0
        key = (ticker, epoch)
        existing_total = _safe_float(snap_index.get(key, {}).get("total_discovery_to_decision_ms")) or 0.0
        if total >= existing_total:
            snap_index[key] = p

    records: list[dict[str, Any]] = []
    for (ticker, epoch), snap in snap_index.items():
        if asset_filter and ticker != asset_filter.upper():
            continue

        # Pull latency stage ms values
        stage_ms: dict[str, float] = {}
        for stage, field in STAGE_FIELDS.items():
            v = _safe_float(snap.get(field))
            if v is not None:
                stage_ms[stage] = v

        # Merge decision metadata (last decision for this epoch wins)
        decisions = decision_index.get((ticker, epoch), [])
        last_dec = decisions[-1] if decisions else {}
        skip_reason_cat = str(last_dec.get("skip_reason_category") or "")
        skip_reason_pri = str(last_dec.get("skip_reason_primary") or "")
        root_cause_conf = _safe_float(last_dec.get("no_entry_root_cause_confidence"))
        skipped = bool(last_dec.get("skipped", True))
        seconds_rem = _safe_int(last_dec.get("seconds_remaining"))
        lc_phase = str(last_dec.get("lifecycle_phase") or snap.get("lifecycle_phase") or "UNKNOWN")

        # Milestone data for this epoch
        ms_map = milestone_index.get((ticker, epoch), {})
        highest_milestone = ""
        for m in reversed(ORDERED_MILESTONES):
            if m in ms_map:
                highest_milestone = m
                break
        executable_reached = "first_executable_book" in ms_map
        executable_sso = ms_map.get("first_executable_book")  # seconds since open

        records.append({
            "ticker": ticker,
            "epoch": epoch,
            "stage_ms": stage_ms,
            "dominant_latency_stage": str(snap.get("dominant_latency_stage") or ""),
            "lifecycle_latency_classification": str(snap.get("lifecycle_latency_classification") or ""),
            "actual_decision": str(snap.get("actual_decision") or last_dec.get("decision") or ""),
            "skipped": skipped,
            "skip_reason_category": skip_reason_cat,
            "skip_reason_primary": skip_reason_pri,
            "root_cause_confidence": root_cause_conf,
            "lifecycle_phase": lc_phase,
            "seconds_remaining": seconds_rem,
            "highest_milestone": highest_milestone,
            "executable_reached": executable_reached,
            "executable_seconds_since_open": executable_sso,
            "milestones": ms_map,
        })

    return records


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"total_records": 0, "guardrail": "no data"}

    total = len(records)

    # --- Per-stage latency collections ---
    stage_values: dict[str, list[float]] = defaultdict(list)
    for r in records:
        for stage, ms in r["stage_ms"].items():
            if ms > 0:
                stage_values[stage].append(ms)

    stage_percentiles: dict[str, dict[str, float]] = {}
    for stage in STAGE_FIELDS:
        vals = stage_values.get(stage, [])
        stage_percentiles[stage] = _pct_stats(vals)

    # --- Dominant stage distribution ---
    dominant_counts: Counter[str] = Counter()
    for r in records:
        d = r["dominant_latency_stage"]
        if d:
            dominant_counts[d] += 1

    # --- Latency classification distribution ---
    classification_counts: Counter[str] = Counter()
    for r in records:
        c = r["lifecycle_latency_classification"]
        if c:
            classification_counts[c] += 1
        else:
            classification_counts["UNKNOWN"] += 1

    # --- Entry vs no-entry latency ---
    entry_vals: dict[str, list[float]] = defaultdict(list)
    no_entry_vals: dict[str, list[float]] = defaultdict(list)
    for r in records:
        bucket = no_entry_vals if r["skipped"] else entry_vals
        for stage, ms in r["stage_ms"].items():
            if ms > 0:
                bucket[stage].append(ms)

    entry_latency = {s: _pct_stats(entry_vals.get(s, [])) for s in STAGE_FIELDS}
    no_entry_latency = {s: _pct_stats(no_entry_vals.get(s, [])) for s in STAGE_FIELDS}

    # --- Asset breakdown ---
    asset_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        asset_records[r["ticker"]].append(r)

    asset_latency: dict[str, dict[str, Any]] = {}
    for asset, asset_recs in sorted(asset_records.items()):
        av: dict[str, list[float]] = defaultdict(list)
        for r in asset_recs:
            for stage, ms in r["stage_ms"].items():
                if ms > 0:
                    av[stage].append(ms)
        asset_latency[asset] = {
            "total_records": len(asset_recs),
            "TOTAL": _pct_stats(av.get("TOTAL", [])),
            "CUTOFF": _pct_stats(av.get("CUTOFF", [])),
            "DISCOVERY": _pct_stats(av.get("DISCOVERY", [])),
        }

    # --- Lifecycle phase distribution ---
    lc_phase_counts: Counter[str] = Counter()
    for r in records:
        lc_phase_counts[r["lifecycle_phase"]] += 1

    # --- Executable before cutoff rate ---
    exec_reached_count = sum(1 for r in records if r["executable_reached"])
    exec_rate = round(exec_reached_count / total, 3) if total else 0.0

    # --- first_executable_book timing distribution (seconds since open) ---
    exec_sso_values = [
        r["executable_seconds_since_open"]
        for r in records
        if r["executable_reached"] and r["executable_seconds_since_open"] is not None
    ]
    exec_timing = _pct_stats([float(v) for v in exec_sso_values])

    # --- Highest milestone at skip ---
    highest_milestone_counts: Counter[str] = Counter()
    for r in records:
        highest_milestone_counts[r["highest_milestone"] or "none_reached"] += 1

    # --- Latency stage vs skip_reason_category correlation ---
    stage_vs_category: dict[str, Counter[str]] = defaultdict(Counter)
    for r in records:
        dominant = r["dominant_latency_stage"]
        cat = r["skip_reason_category"] or "unknown"
        if dominant:
            stage_vs_category[dominant][cat] += 1

    # --- Latency stage vs root_cause_confidence ---
    stage_confidence: dict[str, list[float]] = defaultdict(list)
    for r in records:
        dominant = r["dominant_latency_stage"]
        conf = r["root_cause_confidence"]
        if dominant and conf is not None:
            stage_confidence[dominant].append(conf)

    stage_avg_confidence: dict[str, float] = {
        stage: round(sum(vals) / len(vals), 3)
        for stage, vals in stage_confidence.items()
        if vals
    }

    return {
        "total_records": total,
        "stage_latency_percentiles": stage_percentiles,
        "dominant_stage_distribution": dict(dominant_counts.most_common()),
        "latency_classification_distribution": dict(classification_counts.most_common()),
        "entry_vs_no_entry_latency": {
            "entry": entry_latency,
            "no_entry": no_entry_latency,
        },
        "asset_latency_breakdown": asset_latency,
        "lifecycle_phase_distribution": dict(lc_phase_counts.most_common()),
        "executable_before_cutoff_rate": exec_rate,
        "executable_reached_count": exec_reached_count,
        "first_executable_book_timing": exec_timing,
        "highest_milestone_at_decision": dict(highest_milestone_counts.most_common()),
        "latency_stage_vs_skip_reason_category": {
            stage: dict(cat_counts.most_common())
            for stage, cat_counts in sorted(stage_vs_category.items())
        },
        "latency_stage_avg_root_cause_confidence": stage_avg_confidence,
    }


# ---------------------------------------------------------------------------
# Console rendering
# ---------------------------------------------------------------------------

def render_console(summary: dict[str, Any], date_str: str) -> None:
    total = summary.get("total_records", 0)
    if not total:
        print(f"\nNo lifecycle latency records found for {date_str}.")
        return

    print(f"\n{'='*65}")
    print(f"  Lifecycle Latency Report v1  |  {date_str}")
    print(f"{'='*65}")
    print(f"  Total records: {total}")
    print(f"  Executable-before-cutoff rate: {summary['executable_before_cutoff_rate']*100:.1f}%"
          f"  ({summary['executable_reached_count']}/{total})")
    print()

    print("  -- Per-Stage Latency (ms) --")
    print(f"  {'Stage':<22} {'P50':>8} {'P90':>8} {'P99':>8} {'Mean':>8} {'N':>6}")
    print(f"  {'-'*22} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*6}")
    for stage in STAGE_FIELDS:
        st = summary["stage_latency_percentiles"].get(stage, {})
        if not st.get("count"):
            continue
        print(f"  {stage:<22} {st['p50']:>8.0f} {st['p90']:>8.0f} {st['p99']:>8.0f} "
              f"{st['mean']:>8.0f} {st['count']:>6}")

    print()
    print("  -- Dominant Latency Stage --")
    for stage, count in summary["dominant_stage_distribution"].items():
        pct = count / total * 100
        print(f"    {stage:<25} {count:>5}  ({pct:.1f}%)")

    print()
    print("  -- Latency Classification --")
    for cls, count in summary["latency_classification_distribution"].items():
        pct = count / total * 100
        print(f"    {cls:<20} {count:>5}  ({pct:.1f}%)")

    print()
    print("  -- Entry vs No-Entry (TOTAL stage P50/P90 ms) --")
    ep = summary["entry_vs_no_entry_latency"]
    for outcome_key in ("entry", "no_entry"):
        t = ep.get(outcome_key, {}).get("TOTAL", {})
        if t.get("count"):
            print(f"    {outcome_key:<12}: P50={t['p50']:.0f}ms  P90={t['p90']:.0f}ms  N={t['count']}")

    print()
    print("  -- Asset Comparison (TOTAL stage P50/P90 ms) --")
    for asset, stats in summary["asset_latency_breakdown"].items():
        t = stats.get("TOTAL", {})
        if t.get("count"):
            print(f"    {asset:<6}: P50={t['p50']:.0f}ms  P90={t['p90']:.0f}ms  N={t['count']}")

    print()
    print("  -- first_executable_book Timing (seconds since open) --")
    et = summary["first_executable_book_timing"]
    if et.get("count"):
        print(f"    P50={et['p50']:.0f}s  P90={et['p90']:.0f}s  mean={et['mean']:.0f}s  N={et['count']}")
    else:
        print("    (no milestone data)")

    print()
    print("  -- Lifecycle Phase at Decision --")
    for phase, count in list(summary["lifecycle_phase_distribution"].items())[:8]:
        pct = count / total * 100
        print(f"    {phase:<35} {count:>5}  ({pct:.1f}%)")

    print()
    print("  -- Dominant Stage vs Skip Reason Category --")
    for stage, cat_map in summary["latency_stage_vs_skip_reason_category"].items():
        conf = summary["latency_stage_avg_root_cause_confidence"].get(stage, 0.0)
        print(f"    {stage} (avg_conf={conf:.2f}): {cat_map}")

    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Lifecycle Latency Report Tool v1")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument("--run-id", default=None, help="Filter to a specific run_id")
    parser.add_argument("--asset", default=None, help="Filter to a specific asset (BTC or ETH)")
    parser.add_argument("--write-report", action="store_true",
                        help="Write JSON report to runtime/reports/")
    parser.add_argument("--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args(argv)

    date_str = args.date
    quant_data_dir = Path(args.quant_data_dir)
    report_dir = Path(args.report_dir)

    print(f"Loading research_log for {date_str} ...")
    latency_snaps, milestone_evs = load_research_snapshots(date_str, quant_data_dir, args.run_id)
    print(f"  latency snapshots: {len(latency_snaps)}  |  milestone events: {len(milestone_evs)}")

    print(f"Loading decision_log for {date_str} ...")
    decisions = load_decision_events(date_str, quant_data_dir, args.run_id)
    print(f"  decision events: {len(decisions)}")

    records = build_latency_records(latency_snaps, milestone_evs, decisions, args.asset)
    print(f"  merged records: {len(records)}")

    if not records:
        print("No latency records found. Verify research_log JSONL exists and contains snapshots.")
        return

    summary = aggregate(records)
    summary["date"] = date_str
    summary["asset_filter"] = args.asset or "all"
    summary["run_id_filter"] = args.run_id or "all"
    summary["generated_at"] = datetime.now(timezone.utc).isoformat()
    summary["source"] = "lifecycle_latency_report_v1"
    summary["guardrail"] = (
        "Offline observability only. Does not change runtime, strategy, risk, "
        "execution, or paper/live separation."
    )

    render_console(summary, date_str)

    if args.write_report:
        report_dir.mkdir(parents=True, exist_ok=True)
        out_path = report_dir / f"lifecycle_latency_{date_str}.json"
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2, default=str)
        print(f"  Report written to: {out_path}")


if __name__ == "__main__":
    main()
