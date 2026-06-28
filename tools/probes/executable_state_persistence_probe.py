"""
Executable State Persistence Probe — offline aggregation tool.

Reads decision_log JSONL, detects whether executable orderbook state is being
lost, overwritten, or evaluated against stale state before model admission.

Usage:
    python -m tools.executable_state_persistence_probe --date 2026-05-15
    python -m tools.executable_state_persistence_probe --date 2026-05-15 --write-report
    python -m tools.executable_state_persistence_probe --date 2026-05-15 --run-id RUN123 --asset BTC
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# Offline-only: no runtime imports
from utils.executable_state_persistence_classifier import (
    classify_executable_state_persistence,
)


# ---------------------------------------------------------------------------
# JSONL loader
# ---------------------------------------------------------------------------

def _default_quant_data_dir() -> Path:
    base = Path(__file__).resolve().parent.parent
    return base / "runtime" / "quant_data"


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    """Unwrap nested payload; fall back to flat event for test fixtures."""
    p = event.get("payload")
    if isinstance(p, dict):
        return p
    return event


def load_decision_events(
    date_str: str,
    quant_data_dir: Path | None = None,
    run_id: str | None = None,
    asset_filter: str | None = None,
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
                asset_val = str(p.get("asset") or p.get("ticker") or "").upper()
                if asset_val != asset_filter.upper():
                    continue
            events.append(event)
    return events


# ---------------------------------------------------------------------------
# Per-event record extraction
# ---------------------------------------------------------------------------

def extract_record(event: dict[str, Any]) -> dict[str, Any]:
    """
    Build a flat record for aggregation. Unwraps nested payload if present.
    Uses runtime-emitted probe fields if present; otherwise classifies offline.
    """
    p = _payload(event)

    has_runtime_fields = (
        p.get("executable_state_regressed") is not None
        and p.get("executable_regression_reason") is not None
    )
    if has_runtime_fields:
        probe = {k: p[k] for k in (
            "executable_state_first_seen_ts",
            "executable_state_last_seen_ts",
            "executable_state_duration_ms",
            "executable_state_persisted_to_decision",
            "executable_state_regressed",
            "executable_regression_reason",
            "evaluator_snapshot_state",
            "evaluator_snapshot_age_ms",
            "readiness_bucket_revision",
            "orderbook_state_transition_count",
            "normalized_to_token_ready_regression",
            "executable_to_non_executable_regression",
            "best_seen_state",
            "current_vs_best_seen_diverged",
        ) if k in p}
        # Backfill any missing keys (including new dual-state fields) via offline classifier
        offline = classify_executable_state_persistence(p)
        for k, v in offline.items():
            probe.setdefault(k, v)
    else:
        probe = classify_executable_state_persistence(p)

    return {
        **probe,
        "asset": str(p.get("asset") or p.get("ticker") or "").upper(),
        "lifecycle_phase": str(p.get("lifecycle_phase") or ""),
        "executable_book_state": str(p.get("executable_book_state") or "").upper(),
        "orderbook_stale_reuse_source": str(p.get("orderbook_stale_reuse_source") or ""),
        "executable_book_last_seen_age_ms": p.get("executable_book_last_seen_age_ms"),
        "first_tradable_seconds_remaining": p.get("first_tradable_seconds_remaining"),
        "seconds_remaining": p.get("seconds_remaining"),
        "admission_probe_state": str(p.get("admission_probe_state") or ""),
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    if total == 0:
        return {"total_events": 0}

    # Regression funnel
    had_prior_executable = sum(
        1 for r in records if r.get("executable_state_first_seen_ts")
    )
    persisted = sum(1 for r in records if r.get("executable_state_persisted_to_decision"))
    regressed = sum(1 for r in records if r.get("executable_state_regressed"))
    normalized_regression = sum(1 for r in records if r.get("normalized_to_token_ready_regression"))

    # Regression reason distribution
    regression_reason_dist: Counter[str] = Counter()
    for r in records:
        if r.get("executable_state_regressed"):
            regression_reason_dist[str(r.get("executable_regression_reason") or "UNKNOWN")] += 1

    # Evaluator snapshot state distribution
    snapshot_state_dist: Counter[str] = Counter()
    for r in records:
        snapshot_state_dist[str(r.get("evaluator_snapshot_state") or "UNKNOWN")] += 1

    # Snapshot age distribution (among events with age data)
    snapshot_ages = [
        float(r["evaluator_snapshot_age_ms"])
        for r in records
        if r.get("evaluator_snapshot_age_ms") is not None
    ]
    snapshot_age_stats = _percentiles(snapshot_ages)

    # Executable state duration distribution (among events with duration)
    durations = [
        float(r["executable_state_duration_ms"])
        for r in records
        if r.get("executable_state_duration_ms") is not None
    ]
    duration_stats = _percentiles(durations)

    # Last-seen age distribution (among regressed events with age)
    last_seen_ages = [
        float(r["executable_book_last_seen_age_ms"])
        for r in records
        if r.get("executable_state_regressed")
        and r.get("executable_book_last_seen_age_ms") is not None
    ]
    last_seen_age_stats = _percentiles(last_seen_ages)

    # Stale reuse source distribution
    stale_source_dist: Counter[str] = Counter()
    for r in records:
        src = str(r.get("orderbook_stale_reuse_source") or "NONE")
        stale_source_dist[src] += 1

    # Asset breakdown
    asset_breakdown: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "regressed": 0, "persisted": 0})
    for r in records:
        asset = r.get("asset") or "UNKNOWN"
        asset_breakdown[asset]["total"] += 1
        if r.get("executable_state_regressed"):
            asset_breakdown[asset]["regressed"] += 1
        if r.get("executable_state_persisted_to_decision"):
            asset_breakdown[asset]["persisted"] += 1

    # Lifecycle phase breakdown
    phase_breakdown: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "regressed": 0})
    for r in records:
        phase = r.get("lifecycle_phase") or "UNKNOWN"
        phase_breakdown[phase]["total"] += 1
        if r.get("executable_state_regressed"):
            phase_breakdown[phase]["regressed"] += 1

    # Admission probe state cross-tab
    probe_cross: Counter[str] = Counter()
    for r in records:
        probe_state = r.get("admission_probe_state") or "UNKNOWN"
        if r.get("executable_state_regressed"):
            probe_cross[probe_state] += 1

    # Dual-State Fix B metrics
    # current_vs_best_seen_divergence: events where current < best_seen
    current_vs_best_seen_divergence = sum(
        1 for r in records if r.get("current_vs_best_seen_diverged")
    )
    # degraded_after_best_seen_count: same as divergence (current below historical best)
    degraded_after_best_seen_count = current_vs_best_seen_divergence
    # best_seen_distribution: frequency of each best_seen_state value
    best_seen_dist: Counter[str] = Counter()
    for r in records:
        best_seen_dist[str(r.get("best_seen_state") or "UNKNOWN")] += 1

    return {
        "total_events": total,
        "had_prior_executable": had_prior_executable,
        "persisted_count": persisted,
        "regressed_count": regressed,
        "normalized_to_token_ready_regression_count": normalized_regression,
        "regression_rate_pct": round(regressed / total * 100, 1) if total else 0.0,
        "persistence_rate_pct": round(persisted / total * 100, 1) if total else 0.0,
        "regression_reason_distribution": dict(regression_reason_dist.most_common()),
        "evaluator_snapshot_state_distribution": dict(snapshot_state_dist.most_common()),
        "snapshot_age_ms_stats": snapshot_age_stats,
        "executable_state_duration_ms_stats": duration_stats,
        "last_seen_age_ms_stats_regressed": last_seen_age_stats,
        "stale_reuse_source_distribution": dict(stale_source_dist.most_common()),
        "asset_breakdown": dict(asset_breakdown),
        "lifecycle_phase_breakdown": dict(phase_breakdown),
        "admission_probe_state_regressed_cross": dict(probe_cross.most_common()),
        # Dual-State Fix B metrics
        "current_vs_best_seen_divergence": current_vs_best_seen_divergence,
        "degraded_after_best_seen_count": degraded_after_best_seen_count,
        "best_seen_distribution": dict(best_seen_dist.most_common()),
    }


def _percentiles(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    s = sorted(values)
    n = len(s)

    def pct(p: float) -> float:
        idx = int(p / 100 * n)
        return round(s[min(idx, n - 1)], 1)

    return {
        "n": n,
        "min": round(s[0], 1),
        "p25": pct(25),
        "p50": pct(50),
        "p75": pct(75),
        "p90": pct(90),
        "p95": pct(95),
        "max": round(s[-1], 1),
    }


# ---------------------------------------------------------------------------
# Console renderer
# ---------------------------------------------------------------------------

def render_console(summary: dict[str, Any], date_str: str) -> None:
    total = summary.get("total_events", 0)
    if total == 0:
        print(f"[executable-state-persistence-probe] No decision events found for {date_str}.")
        return

    regressed = summary.get("regressed_count", 0)
    persisted = summary.get("persisted_count", 0)
    had_prior = summary.get("had_prior_executable", 0)
    regression_rate = summary.get("regression_rate_pct", 0.0)
    persistence_rate = summary.get("persistence_rate_pct", 0.0)
    norm_regression = summary.get("normalized_to_token_ready_regression_count", 0)

    print()
    print("=" * 72)
    print(f"  Executable State Persistence Probe  |  {date_str}")
    print("=" * 72)
    print(f"  Total decision events : {total}")
    print(f"  Had prior executable  : {had_prior}  ({had_prior / total * 100:.1f}%)")
    print(f"  Persisted to decision : {persisted}  ({persistence_rate:.1f}%)")
    print(f"  Regressed             : {regressed}  ({regression_rate:.1f}%)")
    print(f"  Norm->TokenReady      : {norm_regression}  ({norm_regression / total * 100:.1f}%)")
    print()

    # Regression funnel bar chart
    print("  Regression Funnel")
    print("  " + "-" * 50)
    _bar("had_prior_executable", had_prior, total)
    _bar("persisted_to_decision", persisted, total)
    _bar("regressed", regressed, total)
    _bar("norm_to_token_ready", norm_regression, total)
    print()

    # Regression reason breakdown
    reason_dist = summary.get("regression_reason_distribution", {})
    if reason_dist:
        print("  Regression Reasons (regressed events only)")
        print("  " + "-" * 50)
        for reason, count in reason_dist.items():
            pct = count / total * 100
            print(f"  {reason:<45} {count:>4}  ({pct:.1f}%)")
        print()

    # Evaluator snapshot state
    snap_dist = summary.get("evaluator_snapshot_state_distribution", {})
    if snap_dist:
        print("  Evaluator Snapshot State at Decision Time")
        print("  " + "-" * 50)
        for state, count in snap_dist.items():
            pct = count / total * 100
            bar = "#" * int(pct / 2)
            print(f"  {state:<22} {count:>4}  ({pct:5.1f}%)  {bar}")
        print()

    # Snapshot age stats
    age_stats = summary.get("snapshot_age_ms_stats", {})
    if age_stats.get("n", 0) > 0:
        print(f"  Snapshot Age at Decision (n={age_stats['n']})")
        print(f"    min={age_stats['min']}ms  P50={age_stats['p50']}ms  "
              f"P90={age_stats['p90']}ms  max={age_stats['max']}ms")
        print()

    # Last-seen age for regressed events
    ls_stats = summary.get("last_seen_age_ms_stats_regressed", {})
    if ls_stats.get("n", 0) > 0:
        print(f"  Last-Seen Age (regressed events, n={ls_stats['n']})")
        print(f"    min={ls_stats['min']}ms  P50={ls_stats['p50']}ms  "
              f"P90={ls_stats['p90']}ms  max={ls_stats['max']}ms")
        print()

    # Duration stats
    dur_stats = summary.get("executable_state_duration_ms_stats", {})
    if dur_stats.get("n", 0) > 0:
        print(f"  Executable State Duration (n={dur_stats['n']})")
        print(f"    min={dur_stats['min']}ms  P50={dur_stats['p50']}ms  "
              f"P90={dur_stats['p90']}ms  max={dur_stats['max']}ms")
        print()

    # Asset breakdown
    asset_bk = summary.get("asset_breakdown", {})
    if asset_bk:
        print("  Asset Breakdown")
        print("  " + "-" * 50)
        for asset, counts in sorted(asset_bk.items()):
            t = counts["total"]
            r = counts["regressed"]
            p = counts["persisted"]
            print(f"  {asset:<8}  total={t}  regressed={r}  persisted={p}")
        print()

    # Dual-State Fix B metrics
    divergence = summary.get("current_vs_best_seen_divergence", 0)
    degraded = summary.get("degraded_after_best_seen_count", 0)
    best_dist = summary.get("best_seen_distribution", {})
    if divergence > 0 or best_dist:
        print("  Dual-State: Current vs Best-Seen (Fix B)")
        print("  " + "-" * 50)
        print(f"  current_vs_best_seen_divergence : {divergence}  ({divergence / total * 100:.1f}%)")
        print(f"  degraded_after_best_seen_count  : {degraded}  ({degraded / total * 100:.1f}%)")
        if best_dist:
            print("  Best-Seen State Distribution:")
            for state, count in best_dist.items():
                pct = count / total * 100
                bar = "#" * int(pct / 2)
                print(f"    {state:<22} {count:>4}  ({pct:5.1f}%)  {bar}")
        print()

    # Key finding callout
    if regression_rate >= 50.0:
        print(f"  [!] HIGH REGRESSION RATE: {regression_rate:.1f}% of events show")
        print(f"      executable state lost before model admission.")
    elif regression_rate >= 20.0:
        print(f"  [~] MODERATE REGRESSION: {regression_rate:.1f}% regression rate.")
    else:
        print(f"  [ok] Low regression rate: {regression_rate:.1f}%.")
    print("=" * 72)
    print()


def _bar(label: str, count: int, total: int) -> None:
    pct = count / total * 100 if total else 0
    bar = "#" * int(pct / 2)
    print(f"  {label:<28} {count:>4}  ({pct:5.1f}%)  {bar}")


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def _default_report_dir() -> Path:
    base = Path(__file__).resolve().parent.parent
    return base / "runtime" / "reports"


def write_report(summary: dict[str, Any], date_str: str, report_dir: Path | None = None) -> Path:
    rd = report_dir or _default_report_dir()
    rd.mkdir(parents=True, exist_ok=True)
    out = rd / f"executable_state_persistence_probe_{date_str}.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)
    return out


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executable State Persistence Probe — offline analysis"
    )
    parser.add_argument("--date", required=True, help="Date string YYYY-MM-DD")
    parser.add_argument("--run-id", default=None, help="Filter by run_id")
    parser.add_argument("--asset", default=None, help="Filter by asset (BTC/ETH)")
    parser.add_argument("--write-report", action="store_true", help="Write JSON report")
    parser.add_argument("--quant-data-dir", default=None, help="Override quant_data directory")
    parser.add_argument("--report-dir", default=None, help="Override report output directory")
    args = parser.parse_args()

    qd = Path(args.quant_data_dir) if args.quant_data_dir else None
    rd = Path(args.report_dir) if args.report_dir else None

    events = load_decision_events(args.date, qd, args.run_id, args.asset)
    records = [extract_record(e) for e in events]
    summary = aggregate(records)

    render_console(summary, args.date)

    if args.write_report:
        out = write_report(summary, args.date, rd)
        print(f"Report written: {out}")


if __name__ == "__main__":
    main()
