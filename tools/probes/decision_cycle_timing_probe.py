"""
Decision Cycle Timing Alignment Probe v1 — offline aggregation tool.

Reads decision_log JSONL and classifies whether decision cycles are occurring
during the usable market entry window, or too late (FINAL_DERISK / PROFIT_MANAGEMENT).

Usage:
    python -m tools.decision_cycle_timing_probe --date 2026-05-15
    python -m tools.decision_cycle_timing_probe --date 2026-05-15 --write-report
    python -m tools.decision_cycle_timing_probe --date 2026-05-15 --asset BTC
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

from utils.decision_cycle_timing_classifier import (
    classify_decision_cycle_timing,
    _ENTRY_CUTOFF_SECONDS,
)


# ---------------------------------------------------------------------------
# JSONL loader
# ---------------------------------------------------------------------------

def _default_quant_data_dir() -> Path:
    base = Path(__file__).resolve().parent.parent
    return base / "runtime" / "quant_data"


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    p = event.get("payload")
    if isinstance(p, dict):
        return p
    return event


def load_decision_events(
    date_str: str,
    quant_data_dir: Path | None = None,
    asset_filter: str | None = None,
    run_id: str | None = None,
) -> list[dict[str, Any]]:
    qd = quant_data_dir or _default_quant_data_dir()
    log_path = qd / "decision_log" / f"{date_str}.jsonl"
    if not log_path.exists():
        return []
    events: list[dict[str, Any]] = []
    with open(log_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if run_id and event.get("run_id") != run_id:
                continue
            if asset_filter:
                p = _payload(event)
                val = str(p.get("asset") or p.get("ticker") or "").upper()
                if val != asset_filter.upper():
                    continue
            events.append(event)
    return events


# ---------------------------------------------------------------------------
# Per-event record extraction
# ---------------------------------------------------------------------------

def extract_record(event: dict[str, Any]) -> dict[str, Any]:
    p = _payload(event)
    timing = classify_decision_cycle_timing(p)
    return {
        **timing,
        "asset": str(p.get("asset") or p.get("ticker") or "").upper(),
        "run_id": str(event.get("run_id") or p.get("run_id") or ""),
        "lifecycle_phase": str(p.get("lifecycle_phase") or ""),
        "seconds_remaining": p.get("seconds_remaining"),
        "first_tradable_seconds_remaining": p.get("first_tradable_seconds_remaining"),
        "first_tradable_ts": str(p.get("first_tradable_ts") or ""),
        "executable_book_state": str(p.get("executable_book_state") or "").upper(),
        "admission_probe_state": str(p.get("admission_probe_state") or ""),
    }


# ---------------------------------------------------------------------------
# Percentile helper
# ---------------------------------------------------------------------------

def _percentiles(values: list[float]) -> dict[str, Any]:
    if not values:
        return {}
    s = sorted(values)
    n = len(s)
    def p(pct: float) -> float:
        idx = max(0, min(n - 1, int(pct / 100 * n)))
        return round(s[idx], 1)
    return {
        "n": n,
        "min": round(s[0], 1),
        "p25": p(25),
        "p50": p(50),
        "p75": p(75),
        "p90": p(90),
        "p95": p(95),
        "max": round(s[-1], 1),
        "mean": round(mean(values), 1),
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    if total == 0:
        return {"total_events": 0}

    # --- Phase distribution ---
    phase_dist: Counter[str] = Counter()
    for r in records:
        phase_dist[str(r.get("decision_cycle_lifecycle_phase") or "UNKNOWN")] += 1

    # --- Active window coverage ---
    active_window_decisions = sum(1 for r in records if r.get("entry_window_decision_seen"))
    model_gate_blocked = sum(1 for r in records if r.get("model_gate_blocked_by_timing"))
    active_window_missed_events = sum(1 for r in records if r.get("active_inventory_window_missed"))

    # --- Seconds-remaining distribution for ALL events ---
    secs_all = [
        float(r["seconds_remaining"])
        for r in records
        if r.get("seconds_remaining") is not None
    ]
    secs_stats_all = _percentiles(secs_all)

    # --- Seconds-remaining at decision for active-window events ---
    secs_active = [
        float(r["seconds_remaining"])
        for r in records
        if r.get("entry_window_decision_seen") and r.get("seconds_remaining") is not None
    ]
    secs_stats_active = _percentiles(secs_active)

    # --- Decision cycle gap distribution ---
    gaps = [
        float(r["decision_cycle_gap_seconds"])
        for r in records
        if r.get("decision_cycle_gap_seconds") is not None
    ]
    gap_stats = _percentiles(gaps)

    # --- Cadence inference ---
    # P50 gap is the best estimate of the poll interval
    inferred_interval_p50 = gap_stats.get("p50")
    inferred_interval_median = round(median(gaps), 1) if gaps else None

    # --- Executable-to-decision delay ---
    exec_delays = [
        float(r["executable_first_seen_to_decision_ms"])
        for r in records
        if r.get("executable_first_seen_to_decision_ms") is not None
        and float(r["executable_first_seen_to_decision_ms"]) >= 0
    ]
    exec_delay_stats = _percentiles(exec_delays)

    # --- Discovery-to-decision delay ---
    disc_delays = [
        float(r["candidate_first_seen_to_decision_ms"])
        for r in records
        if r.get("candidate_first_seen_to_decision_ms") is not None
        and float(r["candidate_first_seen_to_decision_ms"]) >= 0
    ]
    disc_delay_stats = _percentiles(disc_delays)

    # --- Per-asset breakdown ---
    asset_breakdown: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "total": 0, "active_window": 0, "model_gate_blocked": 0, "window_missed": 0,
    })
    for r in records:
        asset = r.get("asset") or "UNKNOWN"
        asset_breakdown[asset]["total"] += 1
        if r.get("entry_window_decision_seen"):
            asset_breakdown[asset]["active_window"] += 1
        if r.get("model_gate_blocked_by_timing"):
            asset_breakdown[asset]["model_gate_blocked"] += 1
        if r.get("active_inventory_window_missed"):
            asset_breakdown[asset]["window_missed"] += 1

    # --- Run-level cadence summary ---
    run_gaps: dict[str, list[float]] = defaultdict(list)
    for r in records:
        rid = r.get("run_id") or "unknown"
        g = r.get("decision_cycle_gap_seconds")
        if g is not None:
            run_gaps[rid].append(float(g))
    run_cadence: dict[str, Any] = {}
    for rid, gs in run_gaps.items():
        if gs:
            run_cadence[rid] = {
                "n": len(gs),
                "p50_gap": round(median(gs), 1),
                "mean_gap": round(mean(gs), 1),
            }

    # --- Active-window coverage rate ---
    active_window_coverage_pct = (
        round(100.0 * active_window_decisions / total, 1) if total > 0 else 0.0
    )
    model_gate_blocked_pct = (
        round(100.0 * model_gate_blocked / total, 1) if total > 0 else 0.0
    )

    # --- Executable state at decision (active window only) ---
    exec_state_active: Counter[str] = Counter()
    for r in records:
        if r.get("entry_window_decision_seen"):
            exec_state_active[str(r.get("executable_book_state") or "UNKNOWN")] += 1

    return {
        "total_events": total,
        "active_window_decisions": active_window_decisions,
        "active_window_coverage_pct": active_window_coverage_pct,
        "model_gate_blocked_count": model_gate_blocked,
        "model_gate_blocked_pct": model_gate_blocked_pct,
        "active_inventory_window_missed_count": active_window_missed_events,
        "lifecycle_phase_distribution": dict(phase_dist.most_common()),
        "seconds_remaining_stats_all": secs_stats_all,
        "seconds_remaining_stats_active_window": secs_stats_active,
        "decision_cycle_gap_stats": gap_stats,
        "inferred_interval_p50_seconds": inferred_interval_p50,
        "inferred_interval_median_seconds": inferred_interval_median,
        "executable_to_decision_delay_ms_stats": exec_delay_stats,
        "candidate_to_decision_delay_ms_stats": disc_delay_stats,
        "asset_breakdown": {k: dict(v) for k, v in asset_breakdown.items()},
        "run_cadence_summary": run_cadence,
        "executable_state_at_active_window_decision": dict(exec_state_active.most_common()),
    }


# ---------------------------------------------------------------------------
# Console rendering
# ---------------------------------------------------------------------------

def render_console(result: dict[str, Any], date_str: str) -> None:
    total = result.get("total_events", 0)
    active = result.get("active_window_decisions", 0)
    active_pct = result.get("active_window_coverage_pct", 0.0)
    blocked = result.get("model_gate_blocked_count", 0)
    blocked_pct = result.get("model_gate_blocked_pct", 0.0)
    missed = result.get("active_inventory_window_missed_count", 0)

    print("=" * 72)
    print(f"  Decision Cycle Timing Probe v1  |  {date_str}")
    print("=" * 72)
    print(f"  Total decision events     : {total}")
    print(f"  Active-window decisions   : {active}  ({active_pct}%)")
    print(f"  Model-gate blocked        : {blocked}  ({blocked_pct}%)")
    print(f"  Active window missed      : {missed} events had exec before cutoff but missed window")

    # Phase distribution
    phase_dist = result.get("lifecycle_phase_distribution", {})
    if phase_dist:
        print()
        print("  Decision Phase Distribution")
        print("  " + "-" * 50)
        for phase, cnt in sorted(phase_dist.items(), key=lambda x: -x[1]):
            bar = "#" * min(40, int(40 * cnt / max(total, 1)))
            pct = round(100.0 * cnt / max(total, 1), 1)
            print(f"  {phase:<35} {cnt:>4}  ({pct:>5}%)  {bar}")

    # Seconds remaining distribution
    secs_all = result.get("seconds_remaining_stats_all", {})
    if secs_all:
        print()
        print(f"  Seconds Remaining at Decision (all events, n={secs_all.get('n',0)})")
        print(f"    min={secs_all.get('min')}s  P25={secs_all.get('p25')}s  P50={secs_all.get('p50')}s  "
              f"P75={secs_all.get('p75')}s  P90={secs_all.get('p90')}s  max={secs_all.get('max')}s")

    secs_active = result.get("seconds_remaining_stats_active_window", {})
    if secs_active:
        print()
        print(f"  Seconds Remaining (active-window events only, n={secs_active.get('n',0)})")
        print(f"    min={secs_active.get('min')}s  P50={secs_active.get('p50')}s  "
              f"max={secs_active.get('max')}s")

    # Cadence inference
    gap_stats = result.get("decision_cycle_gap_stats", {})
    inferred = result.get("inferred_interval_p50_seconds")
    if gap_stats:
        print()
        print(f"  Decision Cycle Gap (inter-cycle interval, n={gap_stats.get('n',0)})")
        print(f"    P50={gap_stats.get('p50')}s  P90={gap_stats.get('p90')}s  "
              f"max={gap_stats.get('max')}s  mean={gap_stats.get('mean')}s")
        if inferred is not None:
            print(f"    Inferred poll interval (P50): {inferred}s")
            note = ""
            if inferred is not None and float(inferred) >= 55:
                note = "  [!] ~60s interval — may miss short active windows"
            elif inferred is not None and float(inferred) <= 20:
                note = "  [OK] Fast cadence — low miss risk"
            print(f"    {note}" if note else "")

    # Executable-to-decision delay
    exec_d = result.get("executable_to_decision_delay_ms_stats", {})
    if exec_d:
        print()
        print(f"  Executable-to-Decision Delay (n={exec_d.get('n',0)})")
        print(f"    P50={exec_d.get('p50')}ms  P90={exec_d.get('p90')}ms  max={exec_d.get('max')}ms")

    # Asset breakdown
    asset_bd = result.get("asset_breakdown", {})
    if asset_bd:
        print()
        print("  Asset Breakdown")
        print("  " + "-" * 50)
        for asset, bd in sorted(asset_bd.items()):
            t = bd.get("total", 0)
            aw = bd.get("active_window", 0)
            mb = bd.get("model_gate_blocked", 0)
            aw_pct = round(100.0 * aw / max(t, 1), 1)
            mb_pct = round(100.0 * mb / max(t, 1), 1)
            print(f"  {asset}  total={t}  active_window={aw} ({aw_pct}%)  "
                  f"model_blocked={mb} ({mb_pct}%)")

    # Run cadence
    run_cad = result.get("run_cadence_summary", {})
    if run_cad:
        print()
        print("  Run Cadence Summary")
        print("  " + "-" * 50)
        for rid, cad in run_cad.items():
            short_id = rid[-16:] if len(rid) > 16 else rid
            print(f"  {short_id}  n={cad.get('n')}  P50_gap={cad.get('p50_gap')}s  "
                  f"mean_gap={cad.get('mean_gap')}s")

    # Exec state at active window
    exec_state_active = result.get("executable_state_at_active_window_decision", {})
    if exec_state_active:
        print()
        print("  Executable State at Active-Window Decisions")
        print("  " + "-" * 50)
        for state, cnt in exec_state_active.items():
            pct = round(100.0 * cnt / max(active, 1), 1)
            print(f"  {state:<30} {cnt:>4}  ({pct}%)")

    # Summary verdict
    print()
    if active == 0:
        print("  [!] ZERO active-window decisions — decision cycles are not reaching")
        print(f"      ACTIVE_INVENTORY_TRADING phase with >{_ENTRY_CUTOFF_SECONDS}s remaining.")
        if inferred is not None and float(inferred) >= 55:
            print(f"      Inferred poll interval {inferred}s is likely too sparse for 5-min markets.")
    elif active_pct < 10.0:
        print(f"  [!] LOW active-window coverage: {active_pct}% — most decisions arrive too late.")
    else:
        print(f"  [OK] {active_pct}% of decisions are in the active entry window.")
    print("=" * 72)


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(result: dict[str, Any], date_str: str, reports_dir: Path | None = None) -> Path:
    if reports_dir is None:
        reports_dir = Path(__file__).resolve().parent.parent / "runtime" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"decision_cycle_timing_probe_{date_str}.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    return path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Decision Cycle Timing Probe v1")
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--asset", default=None)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    events = load_decision_events(
        args.date, asset_filter=args.asset, run_id=args.run_id
    )
    if not events:
        print(f"No decision events found for {args.date}", file=sys.stderr)
        return 1

    records = [extract_record(e) for e in events]
    result = aggregate(records)
    render_console(result, args.date)

    if args.write_report:
        path = write_report(result, args.date)
        print(f"\nReport written: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
