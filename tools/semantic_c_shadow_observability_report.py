"""
Semantic C Shadow Observability Report v1 -- offline analysis tool.

Reads zero_size_probe_v1 events from system_health JSONL and aggregates the
Semantic C shadow fields added to each event.  Answers whether shadow sizing
is stable, bounded, and safe for deeper paper validation without changing any
runtime behavior.

Semantic C formula (observability-only shadow):
    GOOD_EV    = 0.08
    ev_quality = clamp(ev / GOOD_EV, 0.5, 1.0)
    c_input    = confidence_score * ev_quality
    c_mult     = clamp(0.25 + 0.75 * (c_input - 0.54) / 0.21, 0.0, 1.0)
    c_size_usd = raw_size_usd * c_mult

Shadow fields emitted per event (written by trader._emit_zero_size_probe_event):
    semantic_c_ev_quality_shadow
    semantic_c_input_shadow
    semantic_c_multiplier_shadow
    semantic_c_size_usd_shadow
    semantic_c_would_pass_confidence_gate
    semantic_c_would_produce_nonzero_size
    semantic_c_size_pct_bankroll
    semantic_c_shadow_reason

For events emitted before the shadow fields were added (backward-compat),
this tool derives the shadow values from the existing confidence/ev/raw_size_usd
fields using the same formula.

Usage:
    python -m tools.semantic_c_shadow_observability_report --date 2026-05-16
    python -m tools.semantic_c_shadow_observability_report --date 2026-05-16 --write-report
    python -m tools.semantic_c_shadow_observability_report --date 2026-05-16 --run-id <id>
    python -m tools.semantic_c_shadow_observability_report --date 2026-05-16 --asset BTC

Output:
    Console summary + optional runtime/reports/sem_c_shadow_YYYY-MM-DD_HHMM.json

This tool is OFFLINE-ONLY.  It does NOT change runtime, strategy, risk,
execution, position_sizing.py, paper/live separation, or any trading behavior.
No runtime modules are imported.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, quantiles
from typing import Any

if __package__ in {None, ""}:
    _repo_root = Path(__file__).resolve().parents[1]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

DEFAULT_QUANT_DATA_DIR = Path("runtime/quant_data")
DEFAULT_REPORT_DIR = Path("runtime/reports")

# Mirror of sizing constants -- read-only reference, not imported from runtime
_GOOD_EV    = 0.08
_CONF_FLOOR = 0.54
_CONF_SPAN  = 0.21   # 0.75 - 0.54
_EV_Q_FLOOR = 0.5

# Threshold for "too aggressive" verdict
_AGGRESSIVE_MEAN_PCT  = 5.0    # mean shadow size as % bankroll
_AGGRESSIVE_MAX_PCT   = 10.0   # max shadow size as % bankroll


# ---------------------------------------------------------------------------
# Shadow formula -- backward-compat derivation
# ---------------------------------------------------------------------------

def _compute_shadow(p: dict[str, Any]) -> dict[str, Any]:
    """
    Derive Semantic C shadow fields from a zero_size_probe_v1 payload.

    If the event already carries pre-computed shadow fields (written by the
    enriched trader code), those values are returned directly.  Otherwise the
    formula is applied to confidence / ev / raw_size_usd so that historical
    events (emitted before the shadow fields existed) remain analysable.
    """
    # If shadow already present, return as-is
    if "semantic_c_multiplier_shadow" in p:
        return {
            "ev_quality":    float(p.get("semantic_c_ev_quality_shadow") or 0.0),
            "c_input":       float(p.get("semantic_c_input_shadow") or 0.0),
            "c_mult":        float(p.get("semantic_c_multiplier_shadow") or 0.0),
            "c_size":        float(p.get("semantic_c_size_usd_shadow") or 0.0),
            "would_pass":    bool(p.get("semantic_c_would_pass_confidence_gate")),
            "nonzero":       bool(p.get("semantic_c_would_produce_nonzero_size")),
            "pct_bankroll":  float(p.get("semantic_c_size_pct_bankroll") or 0.0),
            "from_live_event": True,
        }

    # Backward-compat: derive from existing fields
    ev_f       = float(p.get("ev") or 0.0)
    conf       = float(p.get("confidence") or 0.0)
    raw_size   = float(p.get("raw_size_usd") or 0.0)
    bankroll   = float(p.get("bankroll") or 1.0)

    ev_quality = max(_EV_Q_FLOOR, min(1.0, ev_f / max(_GOOD_EV, 1e-9)))
    c_input    = conf * ev_quality
    c_mult     = max(0.0, min(1.0, 0.25 + 0.75 * (c_input - _CONF_FLOOR) / _CONF_SPAN))
    c_size     = raw_size * c_mult
    pct        = round(c_size / max(bankroll, 1e-9) * 100, 4)

    return {
        "ev_quality":    round(ev_quality, 6),
        "c_input":       round(c_input, 6),
        "c_mult":        round(c_mult, 6),
        "c_size":        round(c_size, 6),
        "would_pass":    c_input >= _CONF_FLOOR,
        "nonzero":       c_size > 0.0,
        "pct_bankroll":  pct,
        "from_live_event": False,
    }


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

def load_shadow_events(
    date_str: str,
    quant_data_dir: Path = DEFAULT_QUANT_DATA_DIR,
    run_id: str | None = None,
    asset_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Load zero_size_probe_v1 payloads for shadow analysis."""
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
# Statistics helpers
# ---------------------------------------------------------------------------

def _pct(n: int | float, d: int | float) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def _stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "p50": 0.0, "p90": 0.0, "min": 0.0, "max": 0.0}
    p90 = quantiles(values, n=10)[8] if len(values) >= 10 else max(values)
    return {
        "mean": round(mean(values), 4),
        "p50":  round(median(values), 4),
        "p90":  round(p90, 4),
        "min":  round(min(values), 4),
        "max":  round(max(values), 4),
    }


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyse(events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Aggregate Semantic C shadow fields from zero_size_probe_v1 events.

    Returns a result dict.  No runtime imports; no side effects.
    """
    if not events:
        return {
            "event_count": 0,
            "error": "no_zero_size_probe_v1_events_found",
            "guardrail": "offline-only; no runtime changes",
        }

    total = len(events)
    shadows = [_compute_shadow(p) for p in events]

    # --- Core shadow metrics ---
    pass_count    = sum(1 for s in shadows if s["would_pass"])
    nonzero_count = sum(1 for s in shadows if s["nonzero"])
    live_event_count = sum(1 for s in shadows if s["from_live_event"])

    # Current-zero but shadow-nonzero (main diagnostic)
    current_zero_shadow_nonzero = sum(
        1 for p, s in zip(events, shadows)
        if float(p.get("final_size_usd") or 0.0) == 0.0 and s["nonzero"]
    )

    # Shadow size and pct distributions
    shadow_sizes  = [s["c_size"] for s in shadows]
    shadow_pcts   = [s["pct_bankroll"] for s in shadows]
    ev_quals      = [s["ev_quality"] for s in shadows]
    c_inputs      = [s["c_input"] for s in shadows]
    c_mults       = [s["c_mult"] for s in shadows]

    # Aggressiveness check
    pct_max = max(shadow_pcts) if shadow_pcts else 0.0
    pct_mean = mean(shadow_pcts) if shadow_pcts else 0.0
    too_aggressive_count = sum(1 for pct in shadow_pcts if pct > _AGGRESSIVE_MEAN_PCT)

    # --- Asset breakdown ---
    def _asset_stats(asset: str) -> dict[str, Any]:
        idx = [i for i, p in enumerate(events) if str(p.get("ticker") or "").upper() == asset]
        if not idx:
            return {"count": 0}
        sub_sh = [shadows[i] for i in idx]
        sub_ev = [events[i] for i in idx]
        sz = [s["c_size"] for s in sub_sh]
        pcts = [s["pct_bankroll"] for s in sub_sh]
        return {
            "count":            len(idx),
            "shadow_passes":    sum(1 for s in sub_sh if s["would_pass"]),
            "shadow_nonzero":   sum(1 for s in sub_sh if s["nonzero"]),
            "ev_positive":      sum(1 for p in sub_ev if p.get("ev_positive")),
            "mean_entry_price": round(mean(float(p.get("entry_price") or 0) for p in sub_ev), 4),
            "mean_ev":          round(mean(float(p.get("ev") or 0) for p in sub_ev), 5),
            "mean_confidence":  round(mean(float(p.get("confidence") or 0) for p in sub_ev), 4),
            "shadow_size_stats": _stats(sz),
            "shadow_pct_stats":  _stats(pcts),
        }

    btc_stats = _asset_stats("BTC")
    eth_stats = _asset_stats("ETH")

    # --- Lifecycle breakdown ---
    phase_counts: Counter[str] = Counter(
        str(p.get("lifecycle_phase") or "UNKNOWN").upper() for p in events
    )

    # --- Verdict ---
    if total < 10:
        verdict = "insufficient_data"
        verdict_note = f"Only {total} events; need >=10 for confident verdict."
    elif pct_mean > _AGGRESSIVE_MEAN_PCT or pct_max > _AGGRESSIVE_MAX_PCT:
        verdict = "too_aggressive"
        verdict_note = (
            f"Shadow mean size is {pct_mean:.2f}% of bankroll (threshold {_AGGRESSIVE_MEAN_PCT}%) "
            f"or max is {pct_max:.2f}% (threshold {_AGGRESSIVE_MAX_PCT}%). "
            "Semantic C parameters may need further dampening before paper validation."
        )
    else:
        verdict = "safe_for_more_paper_evidence"
        verdict_note = (
            f"Shadow mean size {pct_mean:.2f}% of bankroll, max {pct_max:.2f}%. "
            f"Shadow passes {_pct(pass_count, total):.0f}% of zero-size events. "
            "Semantic C shadow produces controlled sizing consistent with MICRO_SEED risk geometry. "
            "Suitable for continued paper evidence collection."
        )

    return {
        "event_count":                  total,
        "live_event_count":             live_event_count,
        "confidence_floor":             _CONF_FLOOR,
        "good_ev_reference":            _GOOD_EV,
        # Shadow pass/fail
        "shadow_pass_count":            pass_count,
        "shadow_pass_pct":              _pct(pass_count, total),
        "shadow_nonzero_count":         nonzero_count,
        "shadow_nonzero_pct":           _pct(nonzero_count, total),
        "current_zero_shadow_nonzero":  current_zero_shadow_nonzero,
        "current_zero_shadow_nonzero_pct": _pct(current_zero_shadow_nonzero, total),
        # Shadow size distributions
        "shadow_size_usd_stats":        _stats(shadow_sizes),
        "shadow_pct_bankroll_stats":    _stats(shadow_pcts),
        "ev_quality_stats":             _stats(ev_quals),
        "shadow_c_input_stats":         _stats(c_inputs),
        "shadow_c_mult_stats":          _stats(c_mults),
        # Aggressiveness
        "too_aggressive_count":         too_aggressive_count,
        "too_aggressive_pct":           _pct(too_aggressive_count, total),
        # Asset breakdown
        "btc":                          btc_stats,
        "eth":                          eth_stats,
        # Lifecycle
        "lifecycle_phase_distribution": dict(phase_counts),
        # Verdict
        "verdict":                      verdict,
        "verdict_note":                 verdict_note,
        "guardrail": (
            "offline-only; does not change strategy, risk, execution, "
            "position_sizing.py, paper/live separation, or any runtime behavior"
        ),
    }


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------

SEP = "=" * 70


def print_report(result: dict[str, Any], date_str: str) -> None:
    if "error" in result:
        print(f"{SEP}")
        print(f"  Semantic C Shadow Observability Report v1  |  {date_str}")
        print(f"{SEP}")
        print(f"  ERROR: {result['error']}")
        print(f"{SEP}\n")
        return

    total = result["event_count"]
    print(f"{SEP}")
    print(f"  Semantic C Shadow Observability Report v1  |  {date_str}")
    print(f"{SEP}")
    print(f"  Total zero_size_probe_v1 events : {total}")
    print(f"  Events with live shadow fields  : {result.get('live_event_count', 0)}")
    print(f"  Confidence floor (sizing)       : {result['confidence_floor']}")
    print(f"  Good EV reference               : {result['good_ev_reference']}")

    print(f"\n--- Shadow Pass / Fail ---")
    print(f"  Shadow passes confidence gate   : {result['shadow_pass_count']} ({result['shadow_pass_pct']:.1f}%)")
    print(f"  Shadow nonzero size             : {result['shadow_nonzero_count']} ({result['shadow_nonzero_pct']:.1f}%)")
    print(f"  Current=0 but shadow>0          : {result['current_zero_shadow_nonzero']} ({result['current_zero_shadow_nonzero_pct']:.1f}%)")

    print(f"\n--- Shadow Size Distribution ---")
    for label, key in [
        ("shadow size usd  ", "shadow_size_usd_stats"),
        ("shadow % bankroll", "shadow_pct_bankroll_stats"),
        ("ev_quality        ", "ev_quality_stats"),
        ("c_input (sem C)   ", "shadow_c_input_stats"),
        ("c_mult (sem C)    ", "shadow_c_mult_stats"),
    ]:
        s = result.get(key) or {}
        print(f"  {label}: mean={s.get('mean',0):.4f}  "
              f"p50={s.get('p50',0):.4f}  "
              f"p90={s.get('p90',0):.4f}  "
              f"max={s.get('max',0):.4f}")

    print(f"\n--- Aggressiveness Check ---")
    print(f"  Events where shadow pct > 5%   : {result['too_aggressive_count']} ({result['too_aggressive_pct']:.1f}%)")
    pct_s = result.get("shadow_pct_bankroll_stats") or {}
    print(f"  Mean shadow size % bankroll     : {pct_s.get('mean',0):.2f}%")
    print(f"  Max  shadow size % bankroll     : {pct_s.get('max',0):.2f}%")

    print(f"\n--- Asset Breakdown ---")
    for asset in ("BTC", "ETH"):
        s = result.get(asset.lower()) or {}
        if s.get("count", 0) == 0:
            print(f"  {asset}: no events")
            continue
        sz = s.get("shadow_size_stats") or {}
        pct = s.get("shadow_pct_stats") or {}
        print(f"  {asset}: n={s['count']}  "
              f"shadow_pass={s.get('shadow_passes',0)}  "
              f"shadow_nonzero={s.get('shadow_nonzero',0)}  "
              f"ev+={s.get('ev_positive',0)}  "
              f"entry={s.get('mean_entry_price',0):.3f}  "
              f"ev={s.get('mean_ev',0):.4f}  "
              f"conf={s.get('mean_confidence',0):.4f}  "
              f"size_mean=${sz.get('mean',0):.4f}  "
              f"size_pct={pct.get('mean',0):.2f}%")

    print(f"\n--- Lifecycle Phase Distribution ---")
    for phase, cnt in sorted(result.get("lifecycle_phase_distribution", {}).items(),
                              key=lambda x: -x[1]):
        print(f"  {phase:<38} {cnt:>5}")

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
    ts = datetime.now(tz=timezone.utc).strftime("%H%M")
    path = report_dir / f"sem_c_shadow_{date_str}_{ts}.json"
    try:
        with path.open("w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, default=str)
        print(f"  Report written: {path}")
    except OSError as exc:
        print(f"  [WARN] Could not write report: {exc}")
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Semantic C Shadow Observability Report v1 -- offline-only"
    )
    parser.add_argument("--date", required=True, help="Date to analyse (YYYY-MM-DD)")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--asset", default=None, help="Filter by asset (BTC or ETH)")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    events = load_shadow_events(
        args.date,
        quant_data_dir=Path(args.quant_data_dir),
        run_id=args.run_id,
        asset_filter=args.asset,
    )
    result = analyse(events)
    print_report(result, args.date)

    if args.write_report:
        write_report(result, args.date, Path(args.report_dir))


if __name__ == "__main__":
    main()
