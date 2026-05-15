"""
Zero-Size Risk Floor Probe v1 — offline aggregation tool.

Reads system_health JSONL and aggregates zero_size_probe_v1 events to answer
why risk sizing returns zero during active-window opportunities, and whether the
current no-trade behavior is correct MICRO_SURVIVAL survival or an overly
conservative sizing bug.

Usage:
    python -m tools.zero_size_risk_floor_probe --date 2026-05-15
    python -m tools.zero_size_risk_floor_probe --date 2026-05-15 --write-report
    python -m tools.zero_size_risk_floor_probe --date 2026-05-15 --run-id <id>
    python -m tools.zero_size_risk_floor_probe --date 2026-05-15 --asset BTC

Output:
    Console summary + optional runtime/reports/zero_size_risk_floor_probe_YYYY-MM-DD.json

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
CONFIDENCE_FLOOR = 0.54


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

def load_zero_size_events(
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
        if p.get("event") != "zero_size_probe_v1":
            if ev.get("event") != "zero_size_probe_v1":
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

def _pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def analyse(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {
            "event_count": 0,
            "error": "no_zero_size_probe_v1_events_found",
            "guardrail": "offline-only; no runtime changes",
        }

    total = len(events)

    # --- Constraint distribution ---
    constraint_counts: Counter[str] = Counter(
        str(e.get("zero_size_primary_constraint") or "unknown") for e in events
    )
    reason_counts: Counter[str] = Counter(
        str(e.get("zero_size_reason") or "unknown") for e in events
    )

    # --- EV / confidence ---
    ev_positive = sum(1 for e in events if e.get("ev_positive"))
    confidence_passed = sum(1 for e in events if e.get("confidence_passed"))
    ev_positive_conf_passed = sum(
        1 for e in events if e.get("ev_positive") and e.get("confidence_passed")
    )

    # --- Active-window rate (sr > 90) ---
    active_window = [e for e in events if float(e.get("seconds_remaining") or 0) > 90]
    active_count = len(active_window)

    # --- Bankroll / floor / min-order collision ---
    floor_usd = float(events[0].get("bankroll_floor_usd") or 5.0) if events else 5.0
    bankroll_values = [float(e.get("bankroll") or 0) for e in events]
    at_or_near_floor = sum(1 for b in bankroll_values if b < floor_usd * 2)
    below_min_order = sum(
        1 for e in events
        if "below_min_position_size" in (e.get("blocked_reasons") or [])
    )

    # --- MICRO_SURVIVAL ---
    micro_active_count = sum(1 for e in events if e.get("micro_survival_active"))

    # --- Multiplier stats for constraint groups ---
    def _mstats(key: str, subset: list[dict]) -> dict[str, float] | None:
        vals = [float(e.get(key) or 0) for e in subset if e.get(key) is not None]
        if not vals:
            return None
        return {"mean": round(mean(vals), 3), "min": round(min(vals), 3), "max": round(max(vals), 3)}

    multiplier_keys = [
        "confidence_multiplier", "ev_multiplier", "drawdown_multiplier",
        "liquidity_multiplier", "spread_multiplier", "time_to_settlement_multiplier",
        "delta_multiplier", "frequency_multiplier",
    ]
    multiplier_stats = {k: _mstats(k, events) for k in multiplier_keys}

    # --- Raw vs final size ---
    raw_sizes = [float(e.get("raw_size_usd") or 0) for e in events if e.get("raw_size_usd")]
    final_sizes = [float(e.get("final_size_usd") or 0) for e in events if e.get("final_size_usd") is not None]
    min_order_vals = [float(e.get("min_order_usd") or 0) for e in events if e.get("min_order_usd")]

    raw_stats = {"mean": round(mean(raw_sizes), 4), "p50": round(median(raw_sizes), 4)} if raw_sizes else None
    final_stats = {"mean": round(mean(final_sizes), 4), "p50": round(median(final_sizes), 4)} if final_sizes else None
    min_order_stats = {"mean": round(mean(min_order_vals), 4)} if min_order_vals else None

    # --- BTC vs ETH ---
    def _asset_stats(asset: str) -> dict[str, Any]:
        sub = [e for e in events if str(e.get("ticker") or "").upper() == asset]
        if not sub:
            return {"count": 0}
        c_counts = Counter(str(e.get("zero_size_primary_constraint") or "unknown") for e in sub)
        return {
            "count": len(sub),
            "ev_positive": sum(1 for e in sub if e.get("ev_positive")),
            "confidence_passed": sum(1 for e in sub if e.get("confidence_passed")),
            "active_window": sum(1 for e in sub if float(e.get("seconds_remaining") or 0) > 90),
            "micro_active": sum(1 for e in sub if e.get("micro_survival_active")),
            "top_constraint": c_counts.most_common(1)[0][0] if c_counts else "unknown",
        }

    # --- Tier / risk mode ---
    tier_counts = Counter(str(e.get("tier_id") or "unknown") for e in events)
    risk_mode_counts = Counter(str(e.get("risk_mode") or "unknown") for e in events)

    # --- Lifecycle phase ---
    phase_counts = Counter(str(e.get("lifecycle_phase") or "UNKNOWN").upper() for e in events)

    # --- Verdict ---
    dominant = constraint_counts.most_common(1)[0][0] if constraint_counts else "unknown"
    dominant_pct = _pct(constraint_counts[dominant], total)
    time_or_confidence_dominant = dominant in (
        "time_remaining_too_short", "confidence_too_low", "ev_not_positive",
    )
    micro_dominant = micro_active_count > total * 0.8
    ev_pos_suppressed = ev_positive > total * 0.3
    below_min_significant = below_min_order > total * 0.2

    if ev_pos_suppressed and dominant not in ("time_remaining_too_short",):
        verdict = "REVIEW_NEEDED"
        verdict_note = (
            f"{_pct(ev_positive, total):.0f}% of zero-size events had positive EV. "
            f"Dominant constraint is '{dominant}'. If this is not time-related, "
            "investigate whether sizing multipliers are collapsing unnecessarily."
        )
    elif below_min_significant and micro_dominant:
        verdict = "REVIEW_NEEDED"
        verdict_note = (
            f"below_min_order is a significant constraint ({_pct(below_min_order, total):.0f}%). "
            "MICRO_SURVIVAL should rescue below_min_position_size blocks. "
            "If they persist, the micro_survival rescue path may not be firing correctly."
        )
    elif time_or_confidence_dominant and micro_dominant and not below_min_significant:
        verdict = "MICRO_SURVIVAL_CORRECT"
        verdict_note = (
            f"Dominant constraint '{dominant}' ({dominant_pct:.0f}%) is a legitimate "
            "market-timing or model-quality gate, not a sizing bug. "
            "MICRO_SURVIVAL is active and correctly deferring risk."
        )
    else:
        verdict = "MICRO_SURVIVAL_CORRECT"
        verdict_note = (
            f"Dominant constraint '{dominant}' ({dominant_pct:.0f}%) is consistent with "
            "conservative MICRO_SURVIVAL behavior for a small bankroll."
        )

    return {
        "event_count": total,
        "constraint_distribution": dict(constraint_counts),
        "reason_distribution": dict(reason_counts),
        "ev_positive_count": ev_positive,
        "ev_positive_pct": _pct(ev_positive, total),
        "confidence_passed_count": confidence_passed,
        "confidence_passed_pct": _pct(confidence_passed, total),
        "ev_positive_and_confidence_passed_count": ev_positive_conf_passed,
        "ev_positive_and_confidence_passed_pct": _pct(ev_positive_conf_passed, total),
        "active_window_count": active_count,
        "active_window_pct": _pct(active_count, total),
        "micro_survival_active_count": micro_active_count,
        "micro_survival_active_pct": _pct(micro_active_count, total),
        "at_or_near_floor_count": at_or_near_floor,
        "below_min_order_count": below_min_order,
        "below_min_order_pct": _pct(below_min_order, total),
        "bankroll_floor_usd": floor_usd,
        "bankroll_stats": {
            "mean": round(mean(bankroll_values), 2) if bankroll_values else None,
            "min": round(min(bankroll_values), 2) if bankroll_values else None,
            "max": round(max(bankroll_values), 2) if bankroll_values else None,
        },
        "raw_size_stats": raw_stats,
        "final_size_stats": final_stats,
        "min_order_stats": min_order_stats,
        "multiplier_stats": multiplier_stats,
        "tier_distribution": dict(tier_counts),
        "risk_mode_distribution": dict(risk_mode_counts),
        "lifecycle_phase_distribution": dict(phase_counts),
        "btc": _asset_stats("BTC"),
        "eth": _asset_stats("ETH"),
        "dominant_constraint": dominant,
        "dominant_constraint_pct": dominant_pct,
        "verdict": verdict,
        "verdict_note": verdict_note,
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
    print(f"  Zero-Size Risk Floor Probe v1  |  {date_str}")
    print(SEP)

    if "error" in result:
        print(f"  ERROR: {result['error']}")
        print("  No zero_size_probe_v1 events found in system_health JSONL.")
        print("  Run a paper session with the Zero-Size probe instrumentation first.")
        print(f"{SEP}\n")
        return

    n = result["event_count"]
    print(f"\n  Total zero-size events : {n}")
    print(f"  Active window (sr>90s) : {result['active_window_count']} ({result['active_window_pct']:.1f}%)")
    print(f"  MICRO_SURVIVAL active  : {result['micro_survival_active_count']} ({result['micro_survival_active_pct']:.1f}%)")

    print(f"\n--- Dominant Constraint Distribution ---")
    for constraint, cnt in sorted(result.get("constraint_distribution", {}).items(), key=lambda x: -x[1]):
        pct = _pct(cnt, n)
        print(f"  {constraint:<30} {cnt:>5}  ({pct:.1f}%)")

    print(f"\n--- EV / Confidence ---")
    print(f"  EV positive              : {result['ev_positive_count']} ({result['ev_positive_pct']:.1f}%)")
    print(f"  Confidence passed (≥0.54): {result['confidence_passed_count']} ({result['confidence_passed_pct']:.1f}%)")
    print(f"  Both EV+ AND conf passed : {result['ev_positive_and_confidence_passed_count']} ({result['ev_positive_and_confidence_passed_pct']:.1f}%)")

    print(f"\n--- Bankroll / Floor / Min-Order ---")
    bs = result.get("bankroll_stats") or {}
    print(f"  Bankroll: mean=${bs.get('mean','?')}  min=${bs.get('min','?')}  max=${bs.get('max','?')}")
    print(f"  Floor threshold          : ${result['bankroll_floor_usd']:.2f}")
    print(f"  At/near floor (<2x)      : {result['at_or_near_floor_count']}")
    print(f"  below_min_order blocks   : {result['below_min_order_count']} ({result['below_min_order_pct']:.1f}%)")
    if result.get("raw_size_stats"):
        print(f"  Raw size (pre-mult) p50  : ${result['raw_size_stats'].get('p50','?')}")
    if result.get("final_size_stats"):
        print(f"  Final size (post-mult)p50: ${result['final_size_stats'].get('p50','?')}")
    if result.get("min_order_stats"):
        print(f"  Min order mean           : ${result['min_order_stats'].get('mean','?')}")

    print(f"\n--- Multiplier Stats (mean across all events) ---")
    for k, v in (result.get("multiplier_stats") or {}).items():
        if v:
            print(f"  {k:<35} mean={v['mean']:.3f}  min={v['min']:.3f}  max={v['max']:.3f}")

    print(f"\n--- Lifecycle Phase ---")
    for ph, cnt in sorted(result.get("lifecycle_phase_distribution", {}).items(), key=lambda x: -x[1]):
        print(f"  {ph:<30} {cnt:>5}  ({_pct(cnt, n):.1f}%)")

    print(f"\n--- Tier / Risk Mode ---")
    for tier, cnt in sorted(result.get("tier_distribution", {}).items(), key=lambda x: -x[1]):
        print(f"  tier={tier:<20} {cnt:>5}")
    for mode, cnt in sorted(result.get("risk_mode_distribution", {}).items(), key=lambda x: -x[1]):
        print(f"  mode={mode:<20} {cnt:>5}")

    print(f"\n--- BTC vs ETH ---")
    for asset in ("BTC", "ETH"):
        s = result.get(asset, {})
        print(f"  {asset}: n={s.get('count',0)}  ev+={s.get('ev_positive',0)}  "
              f"conf_pass={s.get('confidence_passed',0)}  active={s.get('active_window',0)}  "
              f"micro={s.get('micro_active',0)}  top={s.get('top_constraint','?')}")

    print(f"\n--- Verdict ---")
    print(f"  {result.get('verdict', 'UNKNOWN')}")
    print(f"  {result.get('verdict_note', '')}")

    print(f"\n  guardrail: {result.get('guardrail', '')}")
    print(f"{SEP}\n")


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(result: dict[str, Any], date_str: str, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%H%M")
    path = report_dir / f"zero_size_risk_floor_probe_{date_str}_{ts}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, default=str)
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Zero-Size Risk Floor Probe v1 — offline analysis."
    )
    parser.add_argument("--date", required=True, help="Date to analyse (YYYY-MM-DD)")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--asset", default=None, help="Filter by asset (BTC or ETH)")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    events = load_zero_size_events(
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
