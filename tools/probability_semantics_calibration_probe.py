"""
Probability Semantics Calibration Probe v1 -- offline analysis tool.

Reads zero_size_probe_v1 events from system_health JSONL and computes what
would happen under four alternative confidence-input semantics, answering
whether the current p_yes-as-win_rate logic is mathematically appropriate
for low-priced binary prediction market contracts.

Background:
  The current sizing path passes probability.p_yes (outcome probability) as
  win_rate into calculate_position_size(), which checks it against
  confidence_floor=0.54.  For a YES leg priced at ~0.28-0.29 cents, p_yes is
  roughly entry_price+ev (~0.44-0.45), which sits below the 0.54 floor, so
  confidence_too_low fires even when the model has positive EV and a high
  composite confidence_score (~0.60).

  This tool simulates four alternative semantics -- offline only -- to
  identify which input would be mathematically appropriate without changing
  any runtime behavior.

Semantics simulated:
  A  Current:   win_rate = p_yes_implied = entry_price + ev
  B  Conf-score: win_rate = confidence_score
  C  Edge-aware: win_rate = confidence_score * ev_quality  (ev_quality in 0.5-1.0)
  D  Price-rel:  win_rate = conf_floor + edge_yield * conf_span

Usage:
    python -m tools.probability_semantics_calibration_probe --date 2026-05-15
    python -m tools.probability_semantics_calibration_probe --date 2026-05-15 --write-report
    python -m tools.probability_semantics_calibration_probe --date 2026-05-15 --run-id <id>
    python -m tools.probability_semantics_calibration_probe --date 2026-05-15 --asset BTC

Output:
    Console summary + optional runtime/reports/prob_semantics_calibration_YYYY-MM-DD_HHMM.json

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
from statistics import mean, median
from typing import Any

# ---------------------------------------------------------------------------
# Guard: this module must never import runtime trading code.
# ---------------------------------------------------------------------------

if __package__ in {None, ""}:
    _repo_root = Path(__file__).resolve().parents[1]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

DEFAULT_QUANT_DATA_DIR = Path("runtime/quant_data")
DEFAULT_REPORT_DIR = Path("runtime/reports")

# Sizing constants (mirrors position_sizing.py defaults -- read-only reference)
CONFIDENCE_FLOOR = 0.54
CONFIDENCE_CEILING = 0.75
CONFIDENCE_SPAN = CONFIDENCE_CEILING - CONFIDENCE_FLOOR   # 0.21
GOOD_EV = 0.08       # PositionSizingInput.good_ev default
EV_QUALITY_FLOOR = 0.5   # minimum ev_quality in semantic C


# ---------------------------------------------------------------------------
# Multiplier formula (mirrors _build_multipliers in position_sizing.py)
# ---------------------------------------------------------------------------

def _multiplier_formula(win_rate: float) -> float:
    """Reproduce the confidence_multiplier curve from position_sizing._build_multipliers."""
    raw = 0.25 + 0.75 * (win_rate - CONFIDENCE_FLOOR) / max(CONFIDENCE_SPAN, 1e-9)
    return max(0.0, min(1.0, raw))


# ---------------------------------------------------------------------------
# Four semantic alternatives
# ---------------------------------------------------------------------------

def _semantic_a(p: dict[str, Any]) -> dict[str, float]:
    """Current: win_rate = p_yes_implied = entry_price + ev."""
    entry = float(p.get("entry_price") or 0.0)
    ev = float(p.get("ev") or 0.0)
    win_rate = max(0.0, min(1.0, entry + ev))
    return {"win_rate": win_rate, "multiplier": _multiplier_formula(win_rate)}


def _semantic_b(p: dict[str, Any]) -> dict[str, float]:
    """Confidence-score: win_rate = confidence_score."""
    confidence = float(p.get("confidence") or 0.0)
    win_rate = max(0.0, min(1.0, confidence))
    return {"win_rate": win_rate, "multiplier": _multiplier_formula(win_rate)}


def _semantic_c(p: dict[str, Any]) -> dict[str, float]:
    """Edge-aware: win_rate = confidence_score * ev_quality, ev_quality in [0.5, 1.0]."""
    confidence = float(p.get("confidence") or 0.0)
    ev = float(p.get("ev") or 0.0)
    ev_quality = max(EV_QUALITY_FLOOR, min(1.0, ev / max(GOOD_EV, 1e-9)))
    win_rate = max(0.0, min(1.0, confidence * ev_quality))
    return {
        "win_rate": win_rate,
        "multiplier": _multiplier_formula(win_rate),
        "ev_quality": ev_quality,
    }


def _semantic_d(p: dict[str, Any]) -> dict[str, float]:
    """Price-relative: win_rate = conf_floor + edge_yield * conf_span.
    edge_yield = ev / entry_price (normalised edge as fraction of price paid).
    """
    entry = float(p.get("entry_price") or 0.0)
    ev = float(p.get("ev") or 0.0)
    edge_yield = ev / max(entry, 0.01)
    # Map edge_yield into [conf_floor, conf_ceiling] -- capped at 1.0
    win_rate = max(0.0, min(1.0, CONFIDENCE_FLOOR + edge_yield * CONFIDENCE_SPAN))
    return {"win_rate": win_rate, "multiplier": _multiplier_formula(win_rate)}


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

def load_calibration_events(
    date_str: str,
    quant_data_dir: Path = DEFAULT_QUANT_DATA_DIR,
    run_id: str | None = None,
    asset_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Load zero_size_probe_v1 payloads for the calibration analysis."""
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


def _dist_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "p50": 0.0, "min": 0.0, "max": 0.0}
    return {
        "mean": round(mean(values), 4),
        "p50": round(median(values), 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyse(events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Analyse zero_size_probe_v1 events under four alternative semantics.

    Returns a result dict.  Does not import or call any runtime module.
    No side effects.
    """
    if not events:
        return {
            "event_count": 0,
            "error": "no_zero_size_probe_v1_events_found",
            "guardrail": "offline-only; no runtime changes",
        }

    total = len(events)

    # --- Input distributions ---
    confidence_vals = [float(e.get("confidence") or 0.0) for e in events]
    entry_vals = [float(e.get("entry_price") or 0.0) for e in events]
    ev_vals = [float(e.get("ev") or 0.0) for e in events]
    win_rate_implied = [
        max(0.0, min(1.0, ep + ev))
        for ep, ev in zip(entry_vals, ev_vals)
    ]

    # --- EV / confidence mismatch ---
    ev_positive_count = sum(1 for e in events if e.get("ev_positive"))
    conf_score_passes = sum(1 for c in confidence_vals if c >= CONFIDENCE_FLOOR)
    win_rate_fails = sum(1 for w in win_rate_implied if w < CONFIDENCE_FLOOR)
    mismatch_count = sum(
        1 for e, w in zip(events, win_rate_implied)
        if e.get("confidence_passed") and w < CONFIDENCE_FLOOR
    )
    ev_pos_zero_mult = sum(
        1 for e in events
        if e.get("ev_positive") and float(e.get("confidence_multiplier") or 0.0) == 0.0
    )

    # --- Per-event semantic simulation ---
    sem_a = [_semantic_a(e) for e in events]
    sem_b = [_semantic_b(e) for e in events]
    sem_c = [_semantic_c(e) for e in events]
    sem_d = [_semantic_d(e) for e in events]

    def _sem_stats(sem_results: list[dict], label: str) -> dict[str, Any]:
        mults = [s["multiplier"] for s in sem_results]
        raw_sizes = [float(e.get("raw_size_usd") or 0.0) for e in events]
        hyp_sizes = [r * m for r, m in zip(raw_sizes, mults)]
        passes = sum(1 for m in mults if m > 0.0)
        return {
            "label": label,
            "passes": passes,
            "passes_pct": _pct(passes, total),
            "blocks": total - passes,
            "blocks_pct": _pct(total - passes, total),
            "multiplier_stats": _dist_stats(mults),
            "hyp_size_usd_stats": _dist_stats(hyp_sizes),
            "win_rate_stats": _dist_stats([s["win_rate"] for s in sem_results]),
        }

    sem_a_stats = _sem_stats(sem_a, "A_current_p_yes_implied")
    sem_b_stats = _sem_stats(sem_b, "B_confidence_score")
    sem_c_stats = _sem_stats(sem_c, "C_edge_aware")
    sem_d_stats = _sem_stats(sem_d, "D_price_relative")

    # --- Asset breakdown ---
    def _asset_sem_stats(asset: str) -> dict[str, Any]:
        sub_idx = [i for i, e in enumerate(events) if str(e.get("ticker") or "").upper() == asset]
        if not sub_idx:
            return {"count": 0}
        sub_events = [events[i] for i in sub_idx]
        sub_conf = [confidence_vals[i] for i in sub_idx]
        sub_wri = [win_rate_implied[i] for i in sub_idx]
        return {
            "count": len(sub_idx),
            "conf_score_passes": sum(1 for c in sub_conf if c >= CONFIDENCE_FLOOR),
            "win_rate_fails": sum(1 for w in sub_wri if w < CONFIDENCE_FLOOR),
            "sem_b_passes": sum(1 for i in sub_idx if sem_b[i]["multiplier"] > 0),
            "sem_c_passes": sum(1 for i in sub_idx if sem_c[i]["multiplier"] > 0),
            "sem_d_passes": sum(1 for i in sub_idx if sem_d[i]["multiplier"] > 0),
            "ev_positive": sum(1 for e in sub_events if e.get("ev_positive")),
            "mean_entry_price": round(mean(float(e.get("entry_price") or 0) for e in sub_events), 4),
            "mean_ev": round(mean(float(e.get("ev") or 0) for e in sub_events), 5),
            "mean_confidence": round(mean(sub_conf), 4),
        }

    btc_stats = _asset_sem_stats("BTC")
    eth_stats = _asset_sem_stats("ETH")

    # --- Lifecycle phase breakdown ---
    phase_counts: Counter[str] = Counter(
        str(e.get("lifecycle_phase") or "UNKNOWN").upper() for e in events
    )

    # --- Tier distribution ---
    tier_counts: Counter[str] = Counter(
        str(e.get("tier_id") or "unknown") for e in events
    )

    # --- Verdict ---
    #  semantic_mismatch_confirmed: conf_score passes but win_rate fails on majority of events
    #                               AND sem_b would unlock trades
    #  correct_conservative: win_rate also passes (no mismatch)
    #  insufficient_evidence: too few events or unclear pattern
    mismatch_pct = _pct(mismatch_count, total)
    sem_b_unlock_pct = _pct(sem_b_stats["passes"], total)

    if total < 5:
        verdict = "insufficient_evidence"
        verdict_note = f"Only {total} events; need >=5 for confident verdict."
        safest_candidate = "none -- collect more data"
    elif mismatch_pct >= 50 and sem_b_unlock_pct >= 50:
        verdict = "semantic_mismatch_confirmed"
        verdict_note = (
            f"{mismatch_pct:.0f}% of events have confidence_score passing but win_rate "
            f"failing the 0.54 floor. Semantic B (confidence_score) would unlock "
            f"{sem_b_unlock_pct:.0f}% of blocked trades. "
            "p_yes-as-win_rate is structurally inappropriate for low-priced binary markets."
        )
        # Safest candidate: smallest size step-up with most principled semantics
        # B unlocks most cleanly; C adds ev_quality dampening (safer on low-EV)
        b_mean_size = sem_b_stats["hyp_size_usd_stats"]["mean"]
        c_mean_size = sem_c_stats["hyp_size_usd_stats"]["mean"]
        if c_mean_size <= b_mean_size and sem_c_stats["passes"] >= sem_b_stats["passes"] * 0.7:
            safest_candidate = "C_edge_aware (confidence_score * ev_quality)"
        else:
            safest_candidate = "B_confidence_score (direct replacement)"
    elif mismatch_pct < 20:
        verdict = "correct_conservative"
        verdict_note = (
            f"Only {mismatch_pct:.0f}% mismatch. "
            "win_rate and confidence_score are broadly aligned; "
            "current sizing logic may be appropriate for this data."
        )
        safest_candidate = "no change needed -- insufficient mismatch evidence"
    else:
        verdict = "semantic_mismatch_confirmed"
        verdict_note = (
            f"{mismatch_pct:.0f}% mismatch detected. Semantic B would unlock "
            f"{sem_b_unlock_pct:.0f}% of blocked trades."
        )
        safest_candidate = "C_edge_aware (confidence_score * ev_quality)"

    return {
        "event_count": total,
        "confidence_floor": CONFIDENCE_FLOOR,
        "confidence_ceiling": CONFIDENCE_CEILING,
        "good_ev_reference": GOOD_EV,
        # Input distributions
        "confidence_stats": _dist_stats(confidence_vals),
        "entry_price_stats": _dist_stats(entry_vals),
        "ev_stats": _dist_stats(ev_vals),
        "win_rate_implied_stats": _dist_stats(win_rate_implied),
        # Mismatch counts
        "ev_positive_count": ev_positive_count,
        "ev_positive_pct": _pct(ev_positive_count, total),
        "conf_score_passes_count": conf_score_passes,
        "conf_score_passes_pct": _pct(conf_score_passes, total),
        "win_rate_fails_count": win_rate_fails,
        "win_rate_fails_pct": _pct(win_rate_fails, total),
        "mismatch_count": mismatch_count,
        "mismatch_pct": mismatch_pct,
        "ev_pos_zero_multiplier_count": ev_pos_zero_mult,
        "ev_pos_zero_multiplier_pct": _pct(ev_pos_zero_mult, total),
        # Semantic simulation
        "semantic_a": sem_a_stats,
        "semantic_b": sem_b_stats,
        "semantic_c": sem_c_stats,
        "semantic_d": sem_d_stats,
        # Asset breakdown
        "btc": btc_stats,
        "eth": eth_stats,
        # Phase / tier
        "lifecycle_phase_distribution": dict(phase_counts),
        "tier_distribution": dict(tier_counts),
        # Verdict
        "verdict": verdict,
        "verdict_note": verdict_note,
        "safest_candidate": safest_candidate,
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
        print(f"  Probability Semantics Calibration Probe v1  |  {date_str}")
        print(f"{SEP}")
        print(f"  ERROR: {result['error']}")
        print(f"{SEP}\n")
        return

    print(f"{SEP}")
    print(f"  Probability Semantics Calibration Probe v1  |  {date_str}")
    print(f"{SEP}")
    print(f"  Total zero_size_probe_v1 events : {result['event_count']}")
    print(f"  Confidence floor (sizing)       : {result['confidence_floor']}")
    print(f"  Good EV reference               : {result['good_ev_reference']}")

    print(f"\n--- Input Distributions ---")
    for label, key in [
        ("confidence_score  ", "confidence_stats"),
        ("entry_price       ", "entry_price_stats"),
        ("ev                ", "ev_stats"),
        ("win_rate_implied  ", "win_rate_implied_stats"),
    ]:
        s = result.get(key) or {}
        print(f"  {label}: mean={s.get('mean',0):.4f}  "
              f"p50={s.get('p50',0):.4f}  "
              f"min={s.get('min',0):.4f}  "
              f"max={s.get('max',0):.4f}")

    print(f"\n--- Semantic Mismatch Evidence ---")
    print(f"  EV positive                     : {result['ev_positive_count']} ({result['ev_positive_pct']:.1f}%)")
    print(f"  conf_score passes (>=0.54)      : {result['conf_score_passes_count']} ({result['conf_score_passes_pct']:.1f}%)")
    print(f"  win_rate_implied fails (<0.54)  : {result['win_rate_fails_count']} ({result['win_rate_fails_pct']:.1f}%)")
    print(f"  Mismatch (conf_pass+wrate_fail) : {result['mismatch_count']} ({result['mismatch_pct']:.1f}%)")
    print(f"  EV+ but conf_multiplier=0       : {result['ev_pos_zero_multiplier_count']} ({result['ev_pos_zero_multiplier_pct']:.1f}%)")

    print(f"\n--- Semantic Simulation Results ---")
    print(f"  {'Semantic':<32} {'passes':>7} {'%':>6} {'mult_mean':>10} {'size_mean':>10}")
    print(f"  {'-'*32} {'-'*7} {'-'*6} {'-'*10} {'-'*10}")
    for key, label in [
        ("semantic_a", "A  current (p_yes_implied)"),
        ("semantic_b", "B  confidence_score"),
        ("semantic_c", "C  edge_aware"),
        ("semantic_d", "D  price_relative"),
    ]:
        s = result.get(key) or {}
        ms = s.get("multiplier_stats") or {}
        hs = s.get("hyp_size_usd_stats") or {}
        print(f"  {label:<32} {s.get('passes',0):>7} {s.get('passes_pct',0):>5.1f}% "
              f"{ms.get('mean',0):>10.4f} {hs.get('mean',0):>10.4f}")

    print(f"\n--- Hypothetical Size Under Each Semantic (mean USD) ---")
    for key, label in [
        ("semantic_a", "A  current"),
        ("semantic_b", "B  confidence_score"),
        ("semantic_c", "C  edge_aware"),
        ("semantic_d", "D  price_relative"),
    ]:
        s = result.get(key) or {}
        hs = s.get("hyp_size_usd_stats") or {}
        ws = s.get("win_rate_stats") or {}
        print(f"  {label:<26} win_rate_mean={ws.get('mean',0):.4f}  "
              f"size_mean=${hs.get('mean',0):.4f}  "
              f"size_p50=${hs.get('p50',0):.4f}")

    print(f"\n--- Asset Breakdown ---")
    for asset in ("BTC", "ETH"):
        s = result.get(asset.lower()) or {}
        if s.get("count", 0) == 0:
            print(f"  {asset}: no events")
            continue
        print(f"  {asset}: n={s['count']}  "
              f"conf_pass={s.get('conf_score_passes',0)}  "
              f"wrate_fail={s.get('win_rate_fails',0)}  "
              f"sem_b_pass={s.get('sem_b_passes',0)}  "
              f"sem_c_pass={s.get('sem_c_passes',0)}  "
              f"ev+={s.get('ev_positive',0)}  "
              f"entry={s.get('mean_entry_price',0):.3f}  "
              f"ev={s.get('mean_ev',0):.4f}  "
              f"conf={s.get('mean_confidence',0):.4f}")

    print(f"\n--- Lifecycle Phase Distribution ---")
    for phase, cnt in sorted(result.get("lifecycle_phase_distribution", {}).items(),
                              key=lambda x: -x[1]):
        print(f"  {phase:<36} {cnt:>5}")

    print(f"\n--- Tier Distribution ---")
    for tier, cnt in sorted(result.get("tier_distribution", {}).items(),
                             key=lambda x: -x[1]):
        print(f"  {tier:<36} {cnt:>5}")

    print(f"\n--- Verdict ---")
    print(f"  {result.get('verdict', 'UNKNOWN')}")
    print(f"  {result.get('verdict_note', '')}")
    print(f"\n  Safest next candidate: {result.get('safest_candidate', '?')}")
    print(f"\n  guardrail: {result.get('guardrail', '')}")
    print(f"{SEP}\n")


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(result: dict[str, Any], date_str: str, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%H%M")
    path = report_dir / f"prob_semantics_calibration_{date_str}_{ts}.json"
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
        description="Probability Semantics Calibration Probe v1 -- offline-only"
    )
    parser.add_argument("--date", required=True, help="Date to analyse (YYYY-MM-DD)")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--asset", default=None, help="Filter by asset (BTC or ETH)")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    events = load_calibration_events(
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
