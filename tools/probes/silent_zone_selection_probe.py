"""
Silent-Zone Selection Probe v1 — offline aggregation tool.

Reads system_health JSONL and aggregates cycle_selection_probe_v1 events
to answer why a ~210s silent-zone exists after each epoch open:
  - Which early-return branch dominates?
  - Were executable markets present during the silent zone?
  - Does _select_markets() return empty during ACTIVE window?
  - Does preload orchestration cause selection drift?
  - Do BTC/ETH token IDs arrive late, suppressing evaluation?
  - What is the epoch-second distribution of successful vs early-return cycles?

Usage:
    python -m tools.probes.silent_zone_selection_probe --date 2026-05-15
    python -m tools.probes.silent_zone_selection_probe --date 2026-05-15 --write-report
    python -m tools.probes.silent_zone_selection_probe --date 2026-05-15 --asset BTC
    python -m tools.probes.silent_zone_selection_probe --date 2026-05-15 --run-id <id>

Output:
    Console summary + optional runtime/reports/silent_zone_selection_probe_YYYY-MM-DD.json

This tool is offline-only. It does not change runtime, strategy, risk,
execution, paper/live separation, or any trading behavior.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

if __package__ in {None, ""}:
    _repo_root = Path(__file__).resolve().parents[1]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

DEFAULT_QUANT_DATA_DIR = Path("runtime/quant_data")
DEFAULT_REPORT_DIR = Path("runtime/reports")

EPOCH_BUCKET_SECONDS = 30  # histogram bucket width
SILENT_ZONE_THRESHOLD_SECONDS = 210  # confirmed silent-zone upper bound


# ---------------------------------------------------------------------------
# JSONL helpers
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

def load_selection_probe_events(
    date_str: str,
    quant_data_dir: Path = DEFAULT_QUANT_DATA_DIR,
    run_id: str | None = None,
    asset_filter: str | None = None,
) -> list[dict[str, Any]]:
    path = quant_data_dir / "system_health" / f"{date_str}.jsonl"
    raw = _read_jsonl(path)
    events: list[dict[str, Any]] = []
    for ev in raw:
        p = _payload(ev)
        if p.get("event") != "cycle_selection_probe_v1":
            if ev.get("event") != "cycle_selection_probe_v1":
                continue
            p = ev
        if run_id:
            ev_run = ev.get("run_id") or p.get("run_id") or ""
            if ev_run and ev_run != run_id:
                continue
        if asset_filter:
            af = asset_filter.upper()
            order = p.get("selection_order") or []
            if af not in [str(x).upper() for x in order]:
                if not (af == "BTC" and p.get("btc_token_ids_present") is not None):
                    if not (af == "ETH" and p.get("eth_token_ids_present") is not None):
                        continue
        events.append(p)
    return events


# ---------------------------------------------------------------------------
# Bucket helpers
# ---------------------------------------------------------------------------

def _epoch_bucket(seconds_since_open: float | None) -> str:
    if seconds_since_open is None:
        return "unknown"
    s = float(seconds_since_open)
    lo = int(s // EPOCH_BUCKET_SECONDS) * EPOCH_BUCKET_SECONDS
    hi = lo + EPOCH_BUCKET_SECONDS
    return f"{lo:03d}-{hi:03d}s"


def _bucket_sort_key(label: str) -> int:
    try:
        return int(label.split("-")[0])
    except (ValueError, IndexError):
        return 9999


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyse(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {"event_count": 0, "error": "no_cycle_selection_probe_events_found"}

    total = len(events)

    # --- Early-return distribution ---
    early_return_counts: Counter[str] = Counter()
    reached_analysis = 0
    for ev in events:
        reason = ev.get("early_return_reason")
        if reason:
            early_return_counts[str(reason)] += 1
        else:
            reached_analysis += 1

    # --- Epoch-second distribution: buckets ---
    bucket_total: Counter[str] = Counter()
    bucket_early: Counter[str] = Counter()
    bucket_reached: Counter[str] = Counter()
    bucket_btc_token: Counter[str] = Counter()
    bucket_eth_token: Counter[str] = Counter()
    bucket_btc_executable: defaultdict[str, Counter] = defaultdict(Counter)
    bucket_eth_executable: defaultdict[str, Counter] = defaultdict(Counter)

    seconds_list: list[float] = []
    silent_zone_cycles: list[dict[str, Any]] = []

    for ev in events:
        seo = ev.get("seconds_since_epoch_open")
        try:
            seo_f = float(seo) if seo is not None else None
        except (TypeError, ValueError):
            seo_f = None

        bkt = _epoch_bucket(seo_f)
        bucket_total[bkt] += 1

        if ev.get("early_return_reason"):
            bucket_early[bkt] += 1
        else:
            bucket_reached[bkt] += 1

        if ev.get("btc_token_ids_present"):
            bucket_btc_token[bkt] += 1
        if ev.get("eth_token_ids_present"):
            bucket_eth_token[bkt] += 1

        btc_state = str(ev.get("btc_executable_state") or "UNKNOWN")
        eth_state = str(ev.get("eth_executable_state") or "UNKNOWN")
        bucket_btc_executable[bkt][btc_state] += 1
        bucket_eth_executable[bkt][eth_state] += 1

        if seo_f is not None:
            seconds_list.append(seo_f)
            if seo_f < SILENT_ZONE_THRESHOLD_SECONDS and ev.get("early_return_reason"):
                silent_zone_cycles.append(ev)

    # --- Executable-but-early-return (smoking gun) ---
    executable_states_non_discovered = {
        "TOKEN_READY", "BOOK_SEEN", "TRADABLE", "EXECUTABLE",
        "BOOK_READY", "READY",
    }
    executable_but_early: list[dict[str, Any]] = []
    for ev in events:
        if not ev.get("early_return_reason"):
            continue
        btc_st = str(ev.get("btc_executable_state") or "").upper()
        eth_st = str(ev.get("eth_executable_state") or "").upper()
        if btc_st in executable_states_non_discovered or eth_st in executable_states_non_discovered:
            executable_but_early.append(ev)

    # --- Selection order: BTC vs ETH leading ---
    order_counts: Counter[str] = Counter()
    for ev in events:
        order = ev.get("selection_order") or []
        if len(order) >= 2:
            order_counts[f"{order[0]}_first"] += 1
        elif len(order) == 1:
            order_counts[f"{order[0]}_only"] += 1
        elif not ev.get("early_return_reason"):
            order_counts["empty_selection"] += 1

    # --- Preload coverage ---
    preload_btc_present = sum(1 for ev in events if ev.get("preload_btc_present"))
    preload_eth_present = sum(1 for ev in events if ev.get("preload_eth_present"))

    # --- Token ID arrival timing (first cycle with token present per epoch) ---
    btc_token_arrival: list[float] = []
    eth_token_arrival: list[float] = []
    # group by epoch_ts
    by_epoch: defaultdict[int, list[dict]] = defaultdict(list)
    for ev in events:
        try:
            ep = int(ev.get("epoch_ts") or 0)
        except (TypeError, ValueError):
            ep = 0
        if ep > 0:
            by_epoch[ep].append(ev)
    for ep_evs in by_epoch.values():
        ep_evs_sorted = sorted(
            ep_evs,
            key=lambda e: float(e.get("seconds_since_epoch_open") or 0),
        )
        for e in ep_evs_sorted:
            seo = e.get("seconds_since_epoch_open")
            if e.get("btc_token_ids_present") and not btc_token_arrival:
                try:
                    btc_token_arrival.append(float(seo))
                except (TypeError, ValueError):
                    pass
            if e.get("eth_token_ids_present") and not eth_token_arrival:
                try:
                    eth_token_arrival.append(float(seo))
                except (TypeError, ValueError):
                    pass
    # collect first-token-present per epoch
    btc_first_token_per_epoch: list[float] = []
    eth_first_token_per_epoch: list[float] = []
    for ep_evs in by_epoch.values():
        ep_evs_sorted = sorted(
            ep_evs,
            key=lambda e: float(e.get("seconds_since_epoch_open") or 999),
        )
        first_btc = next(
            (float(e.get("seconds_since_epoch_open") or 0) for e in ep_evs_sorted
             if e.get("btc_token_ids_present")),
            None,
        )
        first_eth = next(
            (float(e.get("seconds_since_epoch_open") or 0) for e in ep_evs_sorted
             if e.get("eth_token_ids_present")),
            None,
        )
        if first_btc is not None:
            btc_first_token_per_epoch.append(first_btc)
        if first_eth is not None:
            eth_first_token_per_epoch.append(first_eth)

    # --- Build per-bucket summary ---
    all_buckets = sorted(set(bucket_total.keys()), key=_bucket_sort_key)
    bucket_summary: list[dict[str, Any]] = []
    for bkt in all_buckets:
        n = bucket_total[bkt]
        early = bucket_early[bkt]
        reached = bucket_reached[bkt]
        btc_tok = bucket_btc_token[bkt]
        eth_tok = bucket_eth_token[bkt]
        btc_exe = dict(bucket_btc_executable[bkt])
        eth_exe = dict(bucket_eth_executable[bkt])
        bucket_summary.append({
            "bucket": bkt,
            "total_cycles": n,
            "early_return_count": early,
            "reached_analysis_count": reached,
            "early_return_rate": round(early / n, 3) if n else 0.0,
            "btc_token_present_count": btc_tok,
            "eth_token_present_count": eth_tok,
            "btc_token_rate": round(btc_tok / n, 3) if n else 0.0,
            "eth_token_rate": round(eth_tok / n, 3) if n else 0.0,
            "btc_executable_state_distribution": btc_exe,
            "eth_executable_state_distribution": eth_exe,
        })

    # --- Dominant root cause ranking ---
    root_cause_rank: list[str] = []
    if early_return_counts:
        dominant = early_return_counts.most_common(1)[0]
        dominant_reason, dominant_count = dominant
        dominant_pct = round(dominant_count / total * 100, 1)
        root_cause_rank.append(
            f"1. early_return={dominant_reason} ({dominant_count}/{total} = {dominant_pct}%)"
        )
    if executable_but_early:
        root_cause_rank.append(
            f"2. executable_markets_ignored_during_early_return: {len(executable_but_early)} cycles"
        )
    sz_count = len(silent_zone_cycles)
    if sz_count:
        sz_early_reasons = Counter(
            ev.get("early_return_reason") or "none" for ev in silent_zone_cycles
        )
        root_cause_rank.append(
            f"3. silent_zone_cycles (<{SILENT_ZONE_THRESHOLD_SECONDS}s, early return): "
            f"{sz_count} | reasons={dict(sz_early_reasons)}"
        )

    # --- Stats ---
    stats: dict[str, Any] = {}
    if seconds_list:
        stats["seconds_since_epoch_open_p5"] = round(sorted(seconds_list)[int(len(seconds_list) * 0.05)], 1)
        stats["seconds_since_epoch_open_p50"] = round(median(seconds_list), 1)
        stats["seconds_since_epoch_open_p95"] = round(sorted(seconds_list)[int(len(seconds_list) * 0.95)], 1)
        stats["seconds_since_epoch_open_mean"] = round(mean(seconds_list), 1)
    if btc_first_token_per_epoch:
        stats["btc_first_token_arrival_p50"] = round(median(btc_first_token_per_epoch), 1)
        stats["btc_first_token_arrival_p95"] = round(sorted(btc_first_token_per_epoch)[int(len(btc_first_token_per_epoch) * 0.95)], 1)
    if eth_first_token_per_epoch:
        stats["eth_first_token_arrival_p50"] = round(median(eth_first_token_per_epoch), 1)
        stats["eth_first_token_arrival_p95"] = round(sorted(eth_first_token_per_epoch)[int(len(eth_first_token_per_epoch) * 0.95)], 1)

    return {
        "event_count": total,
        "epochs_observed": len(by_epoch),
        "reached_analysis_count": reached_analysis,
        "early_return_count": total - reached_analysis,
        "early_return_rate": round((total - reached_analysis) / total, 3) if total else 0.0,
        "early_return_reasons": dict(early_return_counts),
        "silent_zone_early_return_count": sz_count,
        "executable_but_early_return_count": len(executable_but_early),
        "selection_order_distribution": dict(order_counts),
        "preload_btc_present_count": preload_btc_present,
        "preload_eth_present_count": preload_eth_present,
        "preload_btc_coverage_rate": round(preload_btc_present / total, 3) if total else 0.0,
        "preload_eth_coverage_rate": round(preload_eth_present / total, 3) if total else 0.0,
        "bucket_summary": bucket_summary,
        "root_cause_rank": root_cause_rank,
        "stats": stats,
        "guardrail": (
            "offline-only; does not change strategy, risk, execution, "
            "paper/live separation, or any runtime behavior"
        ),
    }


# ---------------------------------------------------------------------------
# Console report
# ---------------------------------------------------------------------------

def print_report(result: dict[str, Any], date_str: str) -> None:
    print(f"\n{'='*70}")
    print(f"  Silent-Zone Selection Probe v1  |  {date_str}")
    print(f"{'='*70}")

    if "error" in result:
        print(f"  ERROR: {result['error']}")
        print(f"  No cycle_selection_probe_v1 events found in system_health JSONL.")
        print(f"  This probe requires a paper run with Silent-Zone instrumentation.")
        print(f"{'='*70}\n")
        return

    n = result["event_count"]
    epochs = result.get("epochs_observed", "?")
    reached = result["reached_analysis_count"]
    early_total = result["early_return_count"]
    early_rate = result["early_return_rate"]

    print(f"\n  Total probe events    : {n}")
    print(f"  Epochs observed       : {epochs}")
    print(f"  Reached analysis      : {reached} ({100-round(early_rate*100,1):.1f}%)")
    print(f"  Early returns         : {early_total} ({round(early_rate*100,1):.1f}%)")

    print(f"\n--- Early-Return Breakdown ---")
    er = result.get("early_return_reasons", {})
    for reason, cnt in sorted(er.items(), key=lambda x: -x[1]):
        pct = round(cnt / n * 100, 1) if n else 0
        print(f"  {reason:<30} {cnt:>5}  ({pct:.1f}%)")

    sz = result.get("silent_zone_early_return_count", 0)
    exe_early = result.get("executable_but_early_return_count", 0)
    print(f"\n  Silent-zone cycles (<{SILENT_ZONE_THRESHOLD_SECONDS}s, early return): {sz}")
    print(f"  Executable-but-early-return (smoking gun) : {exe_early}")

    print(f"\n--- Selection Order Distribution ---")
    for order, cnt in sorted(result.get("selection_order_distribution", {}).items(), key=lambda x: -x[1]):
        pct = round(cnt / n * 100, 1) if n else 0
        print(f"  {order:<25} {cnt:>5}  ({pct:.1f}%)")

    print(f"\n--- Preload Coverage ---")
    print(f"  BTC preload present: {result.get('preload_btc_present_count', 0)}/{n} ({round(result.get('preload_btc_coverage_rate',0)*100,1):.1f}%)")
    print(f"  ETH preload present: {result.get('preload_eth_present_count', 0)}/{n} ({round(result.get('preload_eth_coverage_rate',0)*100,1):.1f}%)")

    stats = result.get("stats", {})
    if stats:
        print(f"\n--- Epoch-Second Distribution ---")
        for k, v in stats.items():
            print(f"  {k:<45} : {v}")

    print(f"\n--- Per-Bucket Summary (every {EPOCH_BUCKET_SECONDS}s) ---")
    print(f"  {'Bucket':<12} {'Total':>6} {'Reached':>8} {'EarlyRet':>9} {'BTCTok':>7} {'ETHTok':>7}  BTC-ExeState(top)")
    for row in result.get("bucket_summary", []):
        bkt = row["bucket"]
        n_b = row["total_cycles"]
        reached_b = row["reached_analysis_count"]
        early_b = row["early_return_count"]
        btc_tok = row["btc_token_rate"]
        eth_tok = row["eth_token_rate"]
        btc_exe = row.get("btc_executable_state_distribution", {})
        top_btc = max(btc_exe, key=btc_exe.get, default="?") if btc_exe else "?"
        print(
            f"  {bkt:<12} {n_b:>6} {reached_b:>8} {early_b:>9} "
            f"{btc_tok:>7.1%} {eth_tok:>7.1%}  {top_btc}"
        )

    print(f"\n--- Root Cause Ranking ---")
    for line in result.get("root_cause_rank", []):
        print(f"  {line}")
    if not result.get("root_cause_rank"):
        print("  (no early returns detected — all cycles reached analysis)")

    print(f"\n  guardrail: {result.get('guardrail', '')}")
    print(f"{'='*70}\n")


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(result: dict[str, Any], date_str: str, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%H%M")
    filename = f"silent_zone_selection_probe_{date_str}_{ts}.json"
    path = report_dir / filename
    with path.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, default=str)
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Silent-Zone Selection Probe v1 — offline analysis of cycle selection events."
    )
    parser.add_argument("--date", required=True, help="Date to analyse (YYYY-MM-DD)")
    parser.add_argument("--write-report", action="store_true", help="Write JSON report to runtime/reports/")
    parser.add_argument("--asset", default=None, help="Filter by asset (BTC or ETH)")
    parser.add_argument("--run-id", default=None, help="Filter by run_id")
    parser.add_argument(
        "--quant-data-dir",
        default=str(DEFAULT_QUANT_DATA_DIR),
        help="Override runtime/quant_data directory",
    )
    parser.add_argument(
        "--report-dir",
        default=str(DEFAULT_REPORT_DIR),
        help="Override runtime/reports directory",
    )
    args = parser.parse_args()

    qd = Path(args.quant_data_dir)
    rd = Path(args.report_dir)

    events = load_selection_probe_events(
        args.date,
        quant_data_dir=qd,
        run_id=args.run_id,
        asset_filter=args.asset,
    )
    result = analyse(events)
    print_report(result, args.date)

    if args.write_report:
        path = write_report(result, args.date, rd)
        print(f"  Report written: {path}\n")


if __name__ == "__main__":
    main()
