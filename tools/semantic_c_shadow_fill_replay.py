"""
Semantic C Shadow Fill Replay Simulator v1 -- offline replay tool.

Replays zero_size_probe_v1 + semantic_c_shadow fields and simulates what
would have happened if Semantic C confidence-input sizing had been active,
without changing any runtime sizing or execution.

Based on confirmed evidence:
  - Semantic mismatch confirmed 31/31
  - Semantic C shadow sizing stable across 178 events
  - mean shadow size ~$0.299, mean exposure ~1.49% bankroll, max ~3.39%
  - verdict: safe_for_more_paper_evidence

This tool simulates hypothetical fills and reports ten outputs:
  1. hypothetical fill count
  2. hypothetical order size distribution
  3. BTC vs ETH split
  4. lifecycle phase split
  5. estimated exposure curve
  6. cutoff collision rate
  7. hypothetical PnL if settlement/outcome fields exist
  8. if settlement unavailable, report honestly
  9. shadow opportunity count
  10. whether Semantic C is safe for a scoped paper-only runtime trial

Usage:
    python -m tools.semantic_c_shadow_fill_replay --date 2026-05-15
    python -m tools.semantic_c_shadow_fill_replay --date 2026-05-15 --write-report
    python -m tools.semantic_c_shadow_fill_replay --date 2026-05-15 --run-id <id>
    python -m tools.semantic_c_shadow_fill_replay --date 2026-05-15 --asset BTC

Output:
    Console summary + optional runtime/reports/sem_c_fill_replay_YYYY-MM-DD_HHMM.json

Replay assumptions:
    - A "hypothetical fill" occurs when Semantic C shadow produces nonzero size.
    - Fill price = entry_price from the probe event (no slippage modelled).
    - Each fill is independent; no inventory accumulation modelled.
    - Exposure at each event = shadow_size_usd / bankroll (point-in-time).
    - Cumulative exposure curve sorts events by timestamp ascending (by
      original index when ts is absent).
    - Cutoff collision = seconds_remaining < 90s at probe time.
    - PnL requires settlement_outcome and resolution_price fields in event.

This tool is OFFLINE-ONLY.  It does NOT change runtime, strategy, risk,
execution, position_sizing.py, order_manager.py, paper/live separation, or
any trading behavior.  No runtime modules are imported.
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

# ---------------------------------------------------------------------------
# Guard: this module must NEVER import runtime trading code.
# ---------------------------------------------------------------------------

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

# Cutoff collision threshold
_CUTOFF_COLLISION_SECONDS = 90.0

# Paper trial verdict thresholds
_MIN_FILLS_FOR_VERDICT  = 5
_SAFE_MEAN_EXPOSURE_PCT = 5.0
_SAFE_MAX_EXPOSURE_PCT  = 10.0
_DANGER_CUTOFF_RATE_PCT = 80.0

# Settlement field names to scan (ordered by preference)
_OUTCOME_KEYS       = ("settlement_outcome", "market_outcome", "final_outcome", "resolved_outcome")
_SETTLE_PRICE_KEYS  = ("resolution_price", "settlement_price", "final_price", "resolved_price")


# ---------------------------------------------------------------------------
# Shadow formula -- identical to semantic_c_shadow_observability_report.py
# ---------------------------------------------------------------------------

def _compute_shadow(p: dict[str, Any]) -> dict[str, Any]:
    """
    Derive Semantic C shadow fields from a zero_size_probe_v1 payload.

    Pre-populated live shadow fields are returned directly.  Historical events
    (emitted before shadow fields existed) are computed from the formula.
    """
    if "semantic_c_multiplier_shadow" in p:
        return {
            "ev_quality":      float(p.get("semantic_c_ev_quality_shadow") or 0.0),
            "c_input":         float(p.get("semantic_c_input_shadow") or 0.0),
            "c_mult":          float(p.get("semantic_c_multiplier_shadow") or 0.0),
            "c_size":          float(p.get("semantic_c_size_usd_shadow") or 0.0),
            "would_pass":      bool(p.get("semantic_c_would_pass_confidence_gate")),
            "nonzero":         bool(p.get("semantic_c_would_produce_nonzero_size")),
            "pct_bankroll":    float(p.get("semantic_c_size_pct_bankroll") or 0.0),
            "from_live_event": True,
        }

    ev_f     = float(p.get("ev") or 0.0)
    conf     = float(p.get("confidence") or 0.0)
    raw_size = float(p.get("raw_size_usd") or 0.0)
    bankroll = float(p.get("bankroll") or 1.0)

    ev_quality = max(_EV_Q_FLOOR, min(1.0, ev_f / max(_GOOD_EV, 1e-9)))
    c_input    = conf * ev_quality
    c_mult     = max(0.0, min(1.0, 0.25 + 0.75 * (c_input - _CONF_FLOOR) / _CONF_SPAN))
    c_size     = raw_size * c_mult
    pct        = round(c_size / max(bankroll, 1e-9) * 100, 4)

    return {
        "ev_quality":      round(ev_quality, 6),
        "c_input":         round(c_input, 6),
        "c_mult":          round(c_mult, 6),
        "c_size":          round(c_size, 6),
        "would_pass":      c_input >= _CONF_FLOOR,
        "nonzero":         c_size > 0.0,
        "pct_bankroll":    pct,
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

def load_replay_events(
    date_str: str,
    quant_data_dir: Path = DEFAULT_QUANT_DATA_DIR,
    run_id: str | None = None,
    asset_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Load zero_size_probe_v1 payloads for fill replay."""
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
        # Carry envelope-level ts into payload dict for sort ordering
        if "ts" not in p and "ts" in ev:
            p = dict(p)
            p["_envelope_ts"] = ev["ts"]
        events.append(p)
    return events


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def _pct(n: int | float, d: int | float) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": 0.0, "p50": 0.0, "p90": 0.0, "min": 0.0, "max": 0.0}
    p90 = quantiles(values, n=10)[8] if len(values) >= 10 else max(values)
    return {
        "count": len(values),
        "mean":  round(mean(values), 4),
        "p50":   round(median(values), 4),
        "p90":   round(p90, 4),
        "min":   round(min(values), 4),
        "max":   round(max(values), 4),
    }


# ---------------------------------------------------------------------------
# Settlement detection
# ---------------------------------------------------------------------------

def _get_settlement(p: dict[str, Any]) -> tuple[str | None, float | None]:
    """Return (outcome, price) if settlement fields are present, else (None, None)."""
    outcome: str | None = None
    for k in _OUTCOME_KEYS:
        v = p.get(k)
        if v is not None and str(v).strip() not in ("", "None", "null"):
            outcome = str(v).strip().upper()
            break

    price: float | None = None
    for k in _SETTLE_PRICE_KEYS:
        v = p.get(k)
        if v is not None:
            try:
                price = float(v)
                break
            except (ValueError, TypeError):
                pass

    return outcome, price


def _compute_hypothetical_pnl(
    entry_price: float,
    c_size: float,
    settlement_price: float,
) -> float | None:
    """
    PnL = (settlement_price - entry_price) * tokens_bought
    where tokens_bought = c_size / entry_price.
    """
    if c_size <= 0.0 or entry_price <= 0.0:
        return None
    tokens = c_size / entry_price
    return round((settlement_price - entry_price) * tokens, 6)


# ---------------------------------------------------------------------------
# Per-event fill simulation
# ---------------------------------------------------------------------------

def _simulate_fill(p: dict[str, Any]) -> dict[str, Any]:
    """Produce a hypothetical fill record for one zero_size_probe_v1 payload."""
    shadow = _compute_shadow(p)
    outcome, settlement_price = _get_settlement(p)
    sr = float(p.get("seconds_remaining") or 0.0)
    entry_price = float(p.get("entry_price") or 0.0)

    pnl: float | None = None
    pnl_available = False
    if shadow["nonzero"] and outcome is not None and settlement_price is not None:
        pnl_available = True
        pnl = _compute_hypothetical_pnl(entry_price, shadow["c_size"], settlement_price)

    # Stable sort key: prefer explicit ts, fall back to envelope ts injected by loader
    ts = p.get("ts") or p.get("_envelope_ts") or None

    return {
        "asset":               str(p.get("ticker") or "UNKNOWN").upper(),
        "lifecycle_phase":     str(p.get("lifecycle_phase") or "UNKNOWN").upper(),
        "entry_price":         entry_price,
        "shadow_size_usd":     shadow["c_size"],
        "shadow_pct_bankroll": shadow["pct_bankroll"],
        "shadow_mult":         shadow["c_mult"],
        "would_fill":          shadow["nonzero"],
        "seconds_remaining":   sr,
        "cutoff_collision":    sr < _CUTOFF_COLLISION_SECONDS,
        "settlement_outcome":  outcome,
        "settlement_price":    settlement_price,
        "pnl_available":       pnl_available,
        "hypothetical_pnl":    pnl,
        "ts":                  ts,
    }


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyse(events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Replay zero_size_probe_v1 payloads with Semantic C shadow sizing.

    Returns a result dict answering all ten report outputs.
    No runtime imports; no side effects on inputs.
    """
    if not events:
        return {
            "event_count": 0,
            "error": "no_zero_size_probe_v1_events_found",
            "guardrail": "offline-only; no runtime changes",
        }

    total = len(events)
    fills = [_simulate_fill(p) for p in events]

    # --- 9. Shadow opportunity count ---
    opportunity_count = sum(1 for f in fills if f["would_fill"])

    # --- 1. Hypothetical fill count ---
    fill_count = opportunity_count

    # --- 2. Order size distribution (fills only) ---
    fill_sizes = [f["shadow_size_usd"] for f in fills if f["would_fill"]]
    size_distribution = _stats(fill_sizes)

    # --- 3. BTC vs ETH split ---
    def _asset_split(asset: str) -> dict[str, Any]:
        sub      = [f for f in fills if f["asset"] == asset]
        sub_fill = [f for f in sub if f["would_fill"]]
        sizes    = [f["shadow_size_usd"] for f in sub_fill]
        pcts     = [f["shadow_pct_bankroll"] for f in sub_fill]
        return {
            "total_events":   len(sub),
            "fill_count":     len(sub_fill),
            "fill_pct":       _pct(len(sub_fill), len(sub)),
            "size_stats":     _stats(sizes),
            "exposure_stats": _stats(pcts),
        }

    btc_split = _asset_split("BTC")
    eth_split = _asset_split("ETH")

    # --- 4. Lifecycle phase split ---
    phase_total: Counter[str] = Counter()
    phase_fills: Counter[str] = Counter()
    for f in fills:
        ph = f["lifecycle_phase"]
        phase_total[ph] += 1
        if f["would_fill"]:
            phase_fills[ph] += 1

    lifecycle_phase_split = {
        ph: {
            "total":    phase_total[ph],
            "fills":    phase_fills[ph],
            "fill_pct": _pct(phase_fills[ph], phase_total[ph]),
        }
        for ph in phase_total
    }

    # --- 5. Estimated exposure curve ---
    # Sort by ts string then original index for stable tiebreaking when ts absent.
    indexed = list(enumerate(fills))
    indexed.sort(key=lambda x: (str(x[1]["ts"]) if x[1]["ts"] else "", x[0]))
    ordered_fills = [f for _, f in indexed]

    running_sum = 0.0
    cumulative_pts: list[float] = []
    for f in ordered_fills:
        if f["would_fill"]:
            running_sum += f["shadow_size_usd"]
        cumulative_pts.append(running_sum)

    pct_exposures = [f["shadow_pct_bankroll"] for f in fills if f["would_fill"]]
    exposure_curve = {
        "peak_cumulative_usd":     round(running_sum, 4),
        "curve_final_usd":         round(cumulative_pts[-1], 4) if cumulative_pts else 0.0,
        "curve_length":            len(cumulative_pts),
        "fill_pct_bankroll_stats": _stats(pct_exposures),
    }

    # --- 6. Cutoff collision rate ---
    fills_only    = [f for f in fills if f["would_fill"]]
    cc_in_fills   = sum(1 for f in fills_only if f["cutoff_collision"])
    cc_rate       = cc_in_fills / fill_count if fill_count else 0.0
    cc_rate_pct   = round(cc_rate * 100.0, 1)
    all_cc        = sum(1 for f in fills if f["cutoff_collision"])

    # --- 7 & 8. Hypothetical PnL ---
    pnl_fills     = [f for f in fills_only if f["pnl_available"] and f["hypothetical_pnl"] is not None]
    pnl_available = len(pnl_fills) > 0

    if pnl_available:
        pnl_vals = [f["hypothetical_pnl"] for f in pnl_fills]
        wins     = [v for v in pnl_vals if v > 0]
        pnl_summary: dict[str, Any] = {
            "pnl_fill_count": len(pnl_fills),
            "total_pnl":      round(sum(pnl_vals), 6),
            "mean_pnl":       round(mean(pnl_vals), 6),
            "win_rate_pct":   _pct(len(wins), len(pnl_vals)),
            "pnl_stats":      _stats(pnl_vals),
        }
    else:
        pnl_summary = {
            "pnl_available": False,
            "message": (
                "PnL unavailable: zero_size_probe_v1 events do not carry "
                "settlement_outcome or resolution_price fields. "
                "Settlement data requires a separate market resolution lookup "
                "after market close. This is expected for live paper sessions."
            ),
        }

    # --- 10. Paper trial verdict ---
    mean_exp = mean(pct_exposures) if pct_exposures else 0.0
    max_exp  = max(pct_exposures) if pct_exposures else 0.0

    if fill_count < _MIN_FILLS_FOR_VERDICT:
        verdict = "insufficient_data"
        verdict_note = (
            f"Only {fill_count} hypothetical fills; need >={_MIN_FILLS_FOR_VERDICT} "
            "for a confident paper-trial verdict."
        )
    elif mean_exp > _SAFE_MEAN_EXPOSURE_PCT or max_exp > _SAFE_MAX_EXPOSURE_PCT:
        verdict = "not_ready"
        verdict_note = (
            f"Shadow exposure exceeds safe thresholds: "
            f"mean={mean_exp:.2f}% (limit {_SAFE_MEAN_EXPOSURE_PCT}%), "
            f"max={max_exp:.2f}% (limit {_SAFE_MAX_EXPOSURE_PCT}%). "
            "Semantic C parameters need further dampening before runtime promotion."
        )
    elif cc_rate_pct >= _DANGER_CUTOFF_RATE_PCT:
        verdict = "not_ready"
        verdict_note = (
            f"Cutoff collision rate is too high ({cc_rate_pct:.1f}% of fills near "
            f"window close, threshold <{_DANGER_CUTOFF_RATE_PCT:.0f}%). "
            "A scoped paper trial would concentrate fills in low-quality near-expiry "
            "windows. Investigate entry timing before runtime promotion."
        )
    else:
        verdict = "safe_for_scoped_paper_trial"
        verdict_note = (
            f"Shadow produces {fill_count} hypothetical fills with mean exposure "
            f"{mean_exp:.2f}% and max {max_exp:.2f}% of bankroll. "
            f"Cutoff collision rate {cc_rate_pct:.1f}% (threshold <{_DANGER_CUTOFF_RATE_PCT:.0f}%). "
            "Semantic C sizing is bounded and consistent with MICRO_SEED risk geometry. "
            "Evidence supports a scoped paper-only runtime trial. "
            "Do NOT promote to live without a separately scoped implementation phase."
        )

    return {
        # Metadata
        "event_count":                  total,
        # 1. Fill count
        "hypothetical_fill_count":      fill_count,
        "hypothetical_fill_pct":        _pct(fill_count, total),
        # 2. Size distribution
        "shadow_size_distribution":     size_distribution,
        # 3. BTC vs ETH split
        "btc":                          btc_split,
        "eth":                          eth_split,
        # 4. Lifecycle phase split
        "lifecycle_phase_split":        lifecycle_phase_split,
        # 5. Exposure curve
        "exposure_curve":               exposure_curve,
        # 6. Cutoff collision
        "cutoff_collision_count":       cc_in_fills,
        "cutoff_collision_rate":        round(cc_rate, 4),
        "cutoff_collision_rate_pct":    cc_rate_pct,
        "all_events_cutoff_count":      all_cc,
        "all_events_cutoff_pct":        _pct(all_cc, total),
        # 7 & 8. PnL
        "pnl_available":                pnl_available,
        "hypothetical_pnl_summary":     pnl_summary,
        # 9. Shadow opportunity count
        "shadow_opportunity_count":     opportunity_count,
        # 10. Verdict
        "paper_trial_verdict":          verdict,
        "paper_trial_note":             verdict_note,
        # Replay context
        "replay_assumptions": [
            "Hypothetical fill = shadow produces nonzero size (semantic_c_would_produce_nonzero_size).",
            "Fill price = entry_price from probe event; no slippage modelled.",
            "Each fill is independent; no inventory accumulation modelled.",
            "Exposure = shadow_size_usd / bankroll at each probe event (point-in-time).",
            "Cumulative curve sorts events by timestamp; original index used as tiebreaker.",
            f"Cutoff collision = seconds_remaining < {_CUTOFF_COLLISION_SECONDS}s at probe time.",
            "PnL requires settlement_outcome and resolution_price fields in the event.",
        ],
        "guardrail": (
            "offline-only; does not change strategy, risk, execution, "
            "position_sizing.py, order_manager.py, paper/live separation, "
            "or any runtime behavior"
        ),
    }


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------

SEP = "=" * 70


def print_report(result: dict[str, Any], date_str: str) -> None:
    if "error" in result:
        print(f"\n{SEP}")
        print(f"  Semantic C Shadow Fill Replay Simulator v1  |  {date_str}")
        print(f"{SEP}")
        print(f"  ERROR: {result['error']}")
        print(f"  Run a paper session with zero_size_probe_v1 instrumentation first.")
        print(f"{SEP}\n")
        return

    total      = result["event_count"]
    fill_count = result["hypothetical_fill_count"]

    print(f"\n{SEP}")
    print(f"  Semantic C Shadow Fill Replay Simulator v1  |  {date_str}")
    print(f"{SEP}")
    print(f"  Total zero_size_probe_v1 events : {total}")
    print(f"  Shadow opportunity count        : {result['shadow_opportunity_count']}")

    print(f"\n--- 1. Hypothetical Fill Count ---")
    print(f"  Fills : {fill_count} ({result['hypothetical_fill_pct']:.1f}% of all events)")

    print(f"\n--- 2. Shadow Order Size Distribution (fills only) ---")
    s = result.get("shadow_size_distribution") or {}
    print(f"  count : {s.get('count', 0)}")
    print(f"  mean  : ${s.get('mean', 0):.4f}")
    print(f"  p50   : ${s.get('p50', 0):.4f}")
    print(f"  p90   : ${s.get('p90', 0):.4f}")
    print(f"  max   : ${s.get('max', 0):.4f}")
    print(f"  min   : ${s.get('min', 0):.4f}")

    print(f"\n--- 3. BTC vs ETH Replay Participation ---")
    for label, key in [("BTC", "btc"), ("ETH", "eth")]:
        a  = result.get(key) or {}
        ss = a.get("size_stats") or {}
        es = a.get("exposure_stats") or {}
        if a.get("total_events", 0) == 0:
            print(f"  {label}: no events")
            continue
        print(f"  {label}: events={a['total_events']}  fills={a['fill_count']}  "
              f"fill_pct={a['fill_pct']:.1f}%  "
              f"size_mean=${ss.get('mean', 0):.4f}  "
              f"exp_mean={es.get('mean', 0):.2f}%")

    print(f"\n--- 4. Lifecycle Phase Split ---")
    lps = result.get("lifecycle_phase_split") or {}
    for ph, d in sorted(lps.items(), key=lambda x: -x[1].get("fills", 0)):
        print(f"  {ph:<40} total={d['total']:>4}  fills={d['fills']:>4}  "
              f"fill_pct={d['fill_pct']:.1f}%")

    print(f"\n--- 5. Estimated Exposure Curve ---")
    ec  = result.get("exposure_curve") or {}
    fps = ec.get("fill_pct_bankroll_stats") or {}
    print(f"  Peak cumulative shadow (USD)    : ${ec.get('peak_cumulative_usd', 0):.4f}")
    print(f"  Fill exposure mean (% bankroll) : {fps.get('mean', 0):.2f}%")
    print(f"  Fill exposure max  (% bankroll) : {fps.get('max', 0):.2f}%")
    print(f"  Fill exposure p90  (% bankroll) : {fps.get('p90', 0):.2f}%")
    print(f"  Curve length (events)           : {ec.get('curve_length', 0)}")

    print(f"\n--- 6. Cutoff Collision Rate ---")
    print(f"  Fills near window close (<90s)  : {result['cutoff_collision_count']} "
          f"({result['cutoff_collision_rate_pct']:.1f}% of fills)")
    print(f"  All events near close           : {result['all_events_cutoff_count']} "
          f"({result['all_events_cutoff_pct']:.1f}% of all events)")

    print(f"\n--- 7 & 8. Hypothetical PnL ---")
    if result.get("pnl_available"):
        ps = result.get("hypothetical_pnl_summary") or {}
        print(f"  PnL-eligible fills              : {ps.get('pnl_fill_count', 0)}")
        print(f"  Total hypothetical PnL          : ${ps.get('total_pnl', 0):.6f}")
        print(f"  Mean PnL per fill               : ${ps.get('mean_pnl', 0):.6f}")
        print(f"  Win rate (pnl > 0)              : {ps.get('win_rate_pct', 0):.1f}%")
    else:
        ps = result.get("hypothetical_pnl_summary") or {}
        print(f"  PnL unavailable")
        print(f"  {ps.get('message', '')}")

    print(f"\n--- 9. Shadow Opportunity Count ---")
    print(f"  {result['shadow_opportunity_count']} events where Semantic C would produce nonzero shadow size")

    print(f"\n--- 10. Paper Trial Verdict ---")
    print(f"  {result.get('paper_trial_verdict', 'UNKNOWN')}")
    print(f"  {result.get('paper_trial_note', '')}")

    print(f"\n--- Replay Assumptions ---")
    for a in result.get("replay_assumptions", []):
        print(f"  - {a}")

    print(f"\n  guardrail: {result.get('guardrail', '')}")
    print(f"{SEP}\n")


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(result: dict[str, Any], date_str: str, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now(tz=timezone.utc).strftime("%H%M")
    path = report_dir / f"sem_c_fill_replay_{date_str}_{ts}.json"
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
        description="Semantic C Shadow Fill Replay Simulator v1 -- offline-only"
    )
    parser.add_argument("--date", required=True, help="Date to replay (YYYY-MM-DD)")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--asset", default=None, help="Filter by asset (BTC or ETH)")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    events = load_replay_events(
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
