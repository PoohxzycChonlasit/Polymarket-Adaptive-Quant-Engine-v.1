"""
Entry Budget Consumption Probe v1 — offline aggregation tool.

Reads system_health JSONL and aggregates entry_budget_probe_v1 events to answer
exactly when and why the per-epoch entry-budget slot is consumed or gate-fired,
and whether slot-burn semantics match intended duplicate-entry protection.

Usage:
    python -m tools.entry_budget_consumption_probe --date 2026-05-15
    python -m tools.entry_budget_consumption_probe --date 2026-05-15 --write-report
    python -m tools.entry_budget_consumption_probe --date 2026-05-15 --run-id <id>
    python -m tools.entry_budget_consumption_probe --date 2026-05-15 --asset BTC

Output:
    Console summary + optional runtime/reports/entry_budget_consumption_probe_YYYY-MM-DD.json

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
from statistics import mean, median
from typing import Any

if __package__ in {None, ""}:
    _repo_root = Path(__file__).resolve().parents[1]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

DEFAULT_QUANT_DATA_DIR = Path("runtime/quant_data")
DEFAULT_REPORT_DIR = Path("runtime/reports")


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

def load_budget_events(
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
        if p.get("event") != "entry_budget_probe_v1":
            if ev.get("event") != "entry_budget_probe_v1":
                continue
            p = ev
        if run_id:
            ev_run = ev.get("run_id") or p.get("run_id") or ""
            if ev_run and ev_run != run_id:
                continue
        if asset_filter:
            af = asset_filter.upper()
            if str(p.get("ticker") or "").upper() != af:
                continue
        events.append(p)
    return events


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyse(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {
            "event_count": 0,
            "error": "no_entry_budget_probe_v1_events_found",
            "guardrail": "offline-only; no runtime changes",
        }

    total = len(events)
    gate_events = [e for e in events if e.get("event_subtype") == "gate_fired"]
    consume_events = [e for e in events if e.get("event_subtype") == "slot_consumed"]

    # --- Gate site distribution ---
    gate_sites = Counter(e.get("site", "unknown") for e in gate_events)

    # Gate fired: model reached breakdown
    gate_model_reached = sum(1 for e in gate_events if e.get("model_gate_reached"))
    gate_pre_model = sum(1 for e in gate_events if not e.get("model_gate_reached"))

    # --- Slot consumed breakdown ---
    with_fill = sum(1 for e in consume_events if e.get("paper_fill_occurred"))
    with_order = sum(1 for e in consume_events if e.get("real_order_attempted"))
    without_order = sum(1 for e in consume_events if e.get("entry_budget_consumed_without_order"))
    without_fill = sum(1 for e in consume_events if e.get("entry_budget_consumed_without_fill"))
    after_zero_size = sum(1 for e in consume_events if e.get("entry_budget_consumed_after_zero_size"))
    after_opening_scan = sum(1 for e in consume_events if e.get("entry_budget_consumed_after_opening_scan"))
    after_model_eval = sum(1 for e in consume_events if e.get("entry_budget_consumed_after_model_eval"))

    # --- Consumed reason distribution ---
    consumed_reasons = Counter(e.get("entry_budget_consumed_reason", "unknown") for e in consume_events)

    # --- Lifecycle phase at gate fire ---
    gate_phases = Counter(str(e.get("lifecycle_phase", "UNKNOWN")).upper() for e in gate_events)
    consume_phases = Counter(str(e.get("lifecycle_phase", "UNKNOWN")).upper() for e in consume_events)

    # --- BTC vs ETH ---
    def asset_stats(asset: str) -> dict[str, Any]:
        a_gate = [e for e in gate_events if str(e.get("ticker", "")).upper() == asset]
        a_consume = [e for e in consume_events if str(e.get("ticker", "")).upper() == asset]
        return {
            "gate_fired": len(a_gate),
            "slot_consumed": len(a_consume),
            "gate_post_model": sum(1 for e in a_gate if e.get("model_gate_reached")),
            "consume_with_fill": sum(1 for e in a_consume if e.get("paper_fill_occurred")),
        }

    # --- Seconds_remaining at gate fire ---
    gate_sr = sorted(float(e.get("seconds_remaining", 0) or 0) for e in gate_events)
    consume_sr = sorted(float(e.get("seconds_remaining", 0) or 0) for e in consume_events)

    def _pct(n: int, d: int) -> float:
        return round(100.0 * n / d, 1) if d else 0.0

    # --- Root cause ranking ---
    root_causes: list[str] = []
    n_gate = len(gate_events)
    n_consume = len(consume_events)

    if n_gate > 0:
        dominant_site = gate_sites.most_common(1)[0]
        root_causes.append(
            f"1. gate_fired dominant site: {dominant_site[0]} "
            f"({dominant_site[1]}/{n_gate} = {_pct(dominant_site[1], n_gate):.1f}%)"
        )
    if n_gate > 0 and gate_model_reached > 0:
        root_causes.append(
            f"2. gate fired AFTER model ({gate_model_reached}/{n_gate} = "
            f"{_pct(gate_model_reached, n_gate):.1f}%): active window evaluated but locked"
        )
    if n_consume > 0 and with_fill > 0:
        root_causes.append(
            f"3. slot consumed by fill ({with_fill}/{n_consume}): "
            "intended duplicate-entry protection working correctly"
        )
    if n_gate > n_consume:
        ratio = round(n_gate / max(n_consume, 1), 1)
        root_causes.append(
            f"4. gate/consume ratio={ratio}: {ratio} blocked revisits per successful fill"
        )

    semantics_verdict = "CORRECT" if (
        without_order == 0 and without_fill == 0 and with_fill == n_consume
    ) else "REVIEW_NEEDED"

    return {
        "event_count": total,
        "gate_fired_count": n_gate,
        "slot_consumed_count": n_consume,
        "gate_site_distribution": dict(gate_sites),
        "gate_pre_model_count": gate_pre_model,
        "gate_post_model_count": gate_model_reached,
        "gate_post_model_pct": _pct(gate_model_reached, n_gate),
        "consume_with_fill_count": with_fill,
        "consume_with_fill_pct": _pct(with_fill, n_consume),
        "consume_without_order_count": without_order,
        "consume_without_fill_count": without_fill,
        "consume_after_zero_size_count": after_zero_size,
        "consume_after_opening_scan_count": after_opening_scan,
        "consume_after_model_eval_count": after_model_eval,
        "consumed_reason_distribution": dict(consumed_reasons),
        "gate_phase_distribution": dict(gate_phases),
        "consume_phase_distribution": dict(consume_phases),
        "btc": asset_stats("BTC"),
        "eth": asset_stats("ETH"),
        "gate_seconds_remaining_p50": round(median(gate_sr), 1) if gate_sr else None,
        "gate_seconds_remaining_min": round(min(gate_sr), 1) if gate_sr else None,
        "gate_seconds_remaining_max": round(max(gate_sr), 1) if gate_sr else None,
        "consume_seconds_remaining_p50": round(median(consume_sr), 1) if consume_sr else None,
        "semantics_verdict": semantics_verdict,
        "root_cause_ranking": root_causes,
        "guardrail": (
            "offline-only; does not change strategy, risk, execution, "
            "paper/live separation, or any runtime behavior"
        ),
    }


# ---------------------------------------------------------------------------
# Console report
# ---------------------------------------------------------------------------

def print_report(result: dict[str, Any], date_str: str) -> None:
    SEP = "=" * 70
    print(f"\n{SEP}")
    print(f"  Entry Budget Consumption Probe v1  |  {date_str}")
    print(SEP)

    if "error" in result:
        print(f"  ERROR: {result['error']}")
        print("  No entry_budget_probe_v1 events found.")
        print("  Run a paper session with the Entry Budget probe instrumentation first.")
        print(f"{SEP}\n")
        return

    n = result["event_count"]
    n_gate = result["gate_fired_count"]
    n_consume = result["slot_consumed_count"]

    print(f"\n  Total probe events    : {n}")
    print(f"  gate_fired events     : {n_gate}")
    print(f"  slot_consumed events  : {n_consume}")

    print(f"\n--- Gate-Fired Distribution ---")
    print(f"  Site breakdown:")
    for site, cnt in sorted(result.get("gate_site_distribution", {}).items(), key=lambda x: -x[1]):
        pct = round(cnt / n_gate * 100, 1) if n_gate else 0
        print(f"    {site:<15} {cnt:>4}  ({pct:.1f}%)")
    print(f"  Pre-model gate fires  : {result['gate_pre_model_count']}")
    print(f"  Post-model gate fires : {result['gate_post_model_count']} ({result['gate_post_model_pct']:.1f}%)")
    if result.get("gate_seconds_remaining_p50") is not None:
        print(f"  SR at gate fire:  p50={result['gate_seconds_remaining_p50']}s  "
              f"min={result['gate_seconds_remaining_min']}s  max={result['gate_seconds_remaining_max']}s")

    print(f"\n--- Slot-Consumed Breakdown ---")
    print(f"  With real paper fill  : {result['consume_with_fill_count']} ({result['consume_with_fill_pct']:.1f}%)")
    print(f"  Without order         : {result['consume_without_order_count']}")
    print(f"  Without fill          : {result['consume_without_fill_count']}")
    print(f"  After zero_size_plan  : {result['consume_after_zero_size_count']}")
    print(f"  After OPENING_SCAN    : {result['consume_after_opening_scan_count']}")
    print(f"  After model eval      : {result['consume_after_model_eval_count']}")
    if result.get("consume_seconds_remaining_p50") is not None:
        print(f"  SR at slot burn: p50={result['consume_seconds_remaining_p50']}s")
    for reason, cnt in result.get("consumed_reason_distribution", {}).items():
        pct = round(cnt / n_consume * 100, 1) if n_consume else 0
        print(f"  reason={reason:<20} {cnt:>3}  ({pct:.1f}%)")

    print(f"\n--- Lifecycle Phase at Event ---")
    print(f"  gate_fired phases:")
    for ph, cnt in sorted(result.get("gate_phase_distribution", {}).items(), key=lambda x: -x[1]):
        pct = round(cnt / n_gate * 100, 1) if n_gate else 0
        print(f"    {ph:<30} {cnt:>4}  ({pct:.1f}%)")
    print(f"  slot_consumed phases:")
    for ph, cnt in sorted(result.get("consume_phase_distribution", {}).items(), key=lambda x: -x[1]):
        pct = round(cnt / n_consume * 100, 1) if n_consume else 0
        print(f"    {ph:<30} {cnt:>4}  ({pct:.1f}%)")

    print(f"\n--- BTC vs ETH ---")
    for asset in ("BTC", "ETH"):
        s = result.get(asset, {})
        print(f"  {asset}: gate={s.get('gate_fired',0)}  consumed={s.get('slot_consumed',0)}  "
              f"post_model_gate={s.get('gate_post_model',0)}  with_fill={s.get('consume_with_fill',0)}")

    print(f"\n--- Slot-Burn Semantics Verdict ---")
    print(f"  {result.get('semantics_verdict', 'UNKNOWN')}")

    print(f"\n--- Root Cause Ranking ---")
    for line in result.get("root_cause_ranking", []):
        print(f"  {line}")

    print(f"\n  guardrail: {result.get('guardrail', '')}")
    print(f"{SEP}\n")


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(result: dict[str, Any], date_str: str, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%H%M")
    path = report_dir / f"entry_budget_consumption_probe_{date_str}_{ts}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, default=str)
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Entry Budget Consumption Probe v1 — offline analysis."
    )
    parser.add_argument("--date", required=True, help="Date to analyse (YYYY-MM-DD)")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--asset", default=None, help="Filter by asset (BTC or ETH)")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    events = load_budget_events(
        args.date,
        quant_data_dir=Path(args.quant_data_dir),
        run_id=args.run_id,
        asset_filter=args.asset,
    )
    result = analyse(events)
    print_report(result, args.date)

    if args.write_report:
        path = write_report(result, args.date, Path(args.report_dir))
        print(f"  Report written: {path}\n")


if __name__ == "__main__":
    main()
