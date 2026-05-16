"""
Stabilization Survival Replay v1 -- offline replay tool.

Measures whether a detected stabilization/compression state survives until
close or breaks into volatility resurgence or late reversal, and identifies
realtime-feasible predictor features at the stabilization moment.

Background (Convergence Regime Classification Replay v1, 2026-05-15):
  59 / 70 epochs showed initial stabilization.
  46 / 59 stabilized epochs later experienced volatility resurgence.
  Volatility resurgence + late reversal = 75.7% of all epochs.
  Stabilization is often temporary compression, not final convergence.
  REAL vs PSEUDO separation is trivially clear by bid level:
    REAL stabilization bid ≈ 0.887  |  PSEUDO ≈ 0.059
  Main open question: which realtime features predict survival?

Four survival states (per-epoch, single label, priority order):
  NO_STABILIZATION      No stabilization event detected in post-entry timeline.
  FAILED_RESURGENCE     Stabilization detected, then rolling vol > 0.04 before close.
  FAILED_LATE_REVERSAL  Stabilization detected, no resurgence, but yes_bid moves
                        >10pp against prior direction in SR < 90s.
  SURVIVED              Stabilization detected; no resurgence and no late reversal.

Two-view contract:
  diagnostic_survival_truth           Uses future post-stab timeline data.
  realtime_feasible_predictor_features Uses only data at or before stabilization_sr.

Two added metrics:
  stabilization_lifetime_seconds
    Duration from stabilization detection until the first failure event
    (resurgence_sr or reversal_sr), or until the final close snapshot if
    survival.  Diagnostic — uses post-stab data, labeled accordingly.

  survival_after_sr120_rate
    Survival rate for epochs where stabilization was detected with
    SR > 120s remaining.  Tests whether early-window stabilization is
    less durable than late-window stabilization.  None if < 3 events.

Predictor features extracted at/before stabilization moment only:
  stabilization_sr, stabilization_bid_level, rolling_vol_at_stabilization,
  bid_stability_score (vol/bid CV), stable_streak_length,
  pre_stabilization_volatility, pre_stabilization_slope,
  bid_distance_from_0_5, n_pre_stab_snaps

Data sources (local JSONL only -- no live API calls):
  runtime/quant_data/system_health/YYYY-MM-DD.jsonl    (zero_size_probe_v1)
  runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl  (timelines + settlement)

Usage:
  python -m tools.stabilization_survival_replay --date 2026-05-15
  python -m tools.stabilization_survival_replay --date 2026-05-15 --write-report
  python -m tools.stabilization_survival_replay --date 2026-05-15 --asset BTC

Output:
  Console summary + optional runtime/reports/stab_survival_YYYY-MM-DD_HHMM.json

This tool is OFFLINE-ONLY.  It does NOT change runtime, strategy, risk,
execution, position_sizing.py, order_manager.py, paper/live separation, or
any trading behavior.  No runtime modules are imported.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
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
DEFAULT_REPORT_DIR     = Path("runtime/reports")

# Shadow formula constants (not imported from runtime)
_GOOD_EV    = 0.08
_CONF_FLOOR = 0.54
_CONF_SPAN  = 0.21
_EV_Q_FLOOR = 0.5

# Settlement proxy thresholds (identical to prior replay tools)
_YES_THRESHOLD    = 0.70
_NO_THRESHOLD     = 0.30
_MAX_SR_FOR_PROXY = 120.0

# Stabilization / resurgence / reversal thresholds
_STAB_VOL_THRESHOLD  = 0.02    # rolling vol < this → stabilizing
_STAB_PERSIST_N      = 3       # consecutive stable snapshots to confirm
_CONV_VOL_WINDOW     = 5       # rolling vol window size
_RESURGENCE_THRESHOLD = 0.04   # vol re-expands above this → resurgence
_LATE_WINDOW_SR      = 90.0    # late window = SR < 90s
_REVERSAL_THRESHOLD  = 0.10    # >10pp = late reversal
_PRIOR_LEVEL_WINDOW  = 5

# Policy B reference
_DERISK_SR = 60.0

# Verdict thresholds
_SURVIVAL_GUARD_THRESHOLD = 0.40   # survival_rate >= this → guard candidate
_FIXED_BEST_THRESHOLD     = 0.30   # survival_rate < this → fixed SR60 best
_MIN_STAB_FOR_VERDICT     = 10     # minimum stabilization events for verdict

# SR bucket boundaries for early vs late stabilization
_SR_ABOVE_120 = 120.0   # survival_after_sr120_rate threshold
_MIN_SR120_COUNT = 3    # minimum events for sr120 rate to be valid

# Bucket definitions
_BID_BUCKETS: list[tuple[float, float]] = [
    (0.0, 0.1), (0.1, 0.3), (0.3, 0.5),
    (0.5, 0.7), (0.7, 0.9), (0.9, 1.01),
]
_SR_BUCKETS: list[tuple[float, float]] = [
    (180.0, 300.0), (120.0, 180.0), (90.0, 120.0), (60.0, 90.0), (0.0, 60.0),
]

# Survival state labels
SURVIVED             = "SURVIVED"
FAILED_RESURGENCE    = "FAILED_RESURGENCE"
FAILED_LATE_REVERSAL = "FAILED_LATE_REVERSAL"
NO_STABILIZATION     = "NO_STABILIZATION"

ALL_SURVIVAL_STATES = [SURVIVED, FAILED_RESURGENCE, FAILED_LATE_REVERSAL, NO_STABILIZATION]

# Verdict labels
GUARD_CANDIDATE = "stabilization_survival_guard_candidate"
FIXED_BEST      = "fixed_SR60_remains_best"
MORE_DATA       = "more_data_needed"


# ---------------------------------------------------------------------------
# Shadow formula (not imported from runtime)
# ---------------------------------------------------------------------------

def _compute_shadow(p: dict[str, Any]) -> dict[str, Any]:
    if "semantic_c_multiplier_shadow" in p:
        return {
            "c_size":       float(p.get("semantic_c_size_usd_shadow") or 0.0),
            "nonzero":      bool(p.get("semantic_c_would_produce_nonzero_size")),
            "pct_bankroll": float(p.get("semantic_c_size_pct_bankroll") or 0.0),
        }
    ev_f     = float(p.get("ev") or 0.0)
    conf     = float(p.get("confidence") or 0.0)
    raw_size = float(p.get("raw_size_usd") or 0.0)
    bankroll = float(p.get("bankroll") or 1.0)
    ev_q   = max(_EV_Q_FLOOR, min(1.0, ev_f / max(_GOOD_EV, 1e-9)))
    c_in   = conf * ev_q
    c_mult = max(0.0, min(1.0, 0.25 + 0.75 * (c_in - _CONF_FLOOR) / _CONF_SPAN))
    c_size = raw_size * c_mult
    pct    = round(c_size / max(bankroll, 1e-9) * 100, 4)
    return {"c_size": round(c_size, 6), "nonzero": c_size > 0.0, "pct_bankroll": pct}


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

def load_probe_events(
    date_str: str,
    quant_data_dir: Path = DEFAULT_QUANT_DATA_DIR,
    run_id: str | None = None,
    asset_filter: str | None = None,
) -> list[dict[str, Any]]:
    path = quant_data_dir / "system_health" / f"{date_str}.jsonl"
    raw  = _read_jsonl(path)
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
            if str(p.get("ticker") or "").upper() != asset_filter.upper():
                continue
        events.append(p)
    return events


def build_settlement_map(
    date_str: str,
    quant_data_dir: Path,
    probe_epoch_keys: set[tuple[Any, str]],
) -> dict[tuple[Any, str], dict[str, Any]]:
    path = quant_data_dir / "market_snapshots" / f"{date_str}.jsonl"
    raw  = _read_jsonl(path)
    best: dict[tuple[Any, str], dict[str, Any]] = {}
    for ev in raw:
        p  = _payload(ev) if "payload" in ev else ev
        ep = p.get("epoch_start_ts") or p.get("epoch_start")
        mk = p.get("market_key")
        sr = p.get("seconds_remaining")
        yb = p.get("yes_bid")
        if None in (ep, mk, sr, yb):
            continue
        key  = (ep, mk)
        sr_f = float(sr)
        if key not in probe_epoch_keys or sr_f >= _MAX_SR_FOR_PROXY:
            continue
        if key not in best or sr_f < float(best[key]["seconds_remaining"]):
            best[key] = {"seconds_remaining": sr_f, "yes_bid": float(yb)}
    result: dict[tuple[Any, str], dict[str, Any]] = {}
    for key, rec in best.items():
        yb = rec["yes_bid"]
        if yb >= _YES_THRESHOLD:
            inferred, price, conf = "YES", 1.0, "HIGH"
        elif yb <= _NO_THRESHOLD:
            inferred, price, conf = "NO", 0.0, "HIGH"
        else:
            inferred, price, conf = "AMBIGUOUS", None, "AMBIGUOUS"
        result[key] = {
            "inferred_settlement":        inferred,
            "settlement_price":           price,
            "yes_bid_at_match":           round(yb, 4),
            "seconds_remaining_at_match": rec["seconds_remaining"],
            "confidence":                 conf,
        }
    return result


def load_epoch_timelines(
    date_str: str,
    quant_data_dir: Path,
    probe_epoch_keys: set[tuple[Any, str]],
) -> dict[tuple[Any, str], list[tuple[float, float]]]:
    path = quant_data_dir / "market_snapshots" / f"{date_str}.jsonl"
    raw  = _read_jsonl(path)
    result: dict[tuple[Any, str], list[tuple[float, float]]] = defaultdict(list)
    for ev in raw:
        p  = _payload(ev) if "payload" in ev else ev
        ep = p.get("epoch_start_ts") or p.get("epoch_start")
        mk = p.get("market_key")
        sr = p.get("seconds_remaining")
        yb = p.get("yes_bid")
        if None in (ep, mk, sr, yb):
            continue
        key = (ep, mk)
        if key not in probe_epoch_keys:
            continue
        yb_f = float(yb)
        sr_f = float(sr)
        if 0.0 <= yb_f <= 1.0:
            result[key].append((sr_f, yb_f))
    return dict(result)


# ---------------------------------------------------------------------------
# PnL / drawdown / stats helpers
# ---------------------------------------------------------------------------

def _max_drawdown(pnl_series: list[float]) -> float:
    if not pnl_series:
        return 0.0
    cum = peak = max_dd = 0.0
    for pnl in pnl_series:
        cum += pnl
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 8)


def _pct(n: int | float, d: int | float) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": 0.0, "p50": 0.0, "p90": 0.0, "min": 0.0, "max": 0.0}
    p90 = quantiles(values, n=10)[8] if len(values) >= 10 else max(values)
    return {
        "count": len(values),
        "mean":  round(mean(values), 6),
        "p50":   round(median(values), 6),
        "p90":   round(p90, 6),
        "min":   round(min(values), 6),
        "max":   round(max(values), 6),
    }


def _asset_from_event(p: dict[str, Any]) -> str:
    tk = str(p.get("ticker") or "").upper()
    if tk in ("BTC", "ETH"):
        return tk
    mk = str(p.get("market_key") or "").lower()
    return "BTC" if "btc" in mk else ("ETH" if "eth" in mk else "UNKNOWN")


# ---------------------------------------------------------------------------
# Rolling volatility
# ---------------------------------------------------------------------------

def _stdev_safe(values: list[float]) -> float | None:
    """Sample stdev. Returns None if fewer than 2 values."""
    n = len(values)
    if n < 2:
        return None
    m = sum(values) / n
    return (sum((x - m) ** 2 for x in values) / (n - 1)) ** 0.5


def _rolling_vol(bids: list[float], window: int = _CONV_VOL_WINDOW) -> float:
    """Rolling std of last `window` yes_bid values. Returns inf if < 2."""
    sample = bids[-window:]
    result = _stdev_safe(sample)
    return result if result is not None else float("inf")


# ---------------------------------------------------------------------------
# Stabilization, resurgence, reversal detectors (identical to classification replay)
# ---------------------------------------------------------------------------

def _detect_stabilization(
    timeline: list[tuple[float, float]],
    vol_threshold: float = _STAB_VOL_THRESHOLD,
    persist_n: int = _STAB_PERSIST_N,
) -> dict[str, Any] | None:
    """Detect first stabilization window. Timeline must be SR-descending."""
    bids:   list[float] = []
    streak: int         = 0
    for sr, yb in timeline:
        bids.append(yb)
        vol = _rolling_vol(bids)
        if vol < vol_threshold:
            streak += 1
            if streak >= persist_n:
                stab_bids = bids[-persist_n:]
                mean_bid  = sum(stab_bids) / len(stab_bids)
                return {
                    "stabilization_sr":        sr,
                    "stabilization_bid_level": round(mean_bid, 6),
                    "vol_at_stabilization":    round(vol, 6),
                    "n_stable_snaps":          streak,
                }
        else:
            streak = 0
    return None


def _detect_vol_resurgence(
    timeline:      list[tuple[float, float]],
    stab_info:     dict[str, Any] | None,
    res_threshold: float = _RESURGENCE_THRESHOLD,
) -> dict[str, Any] | None:
    """Detect vol re-expansion after stabilization. Requires >= 2 post-stab snaps."""
    if stab_info is None:
        return None
    stab_sr   = stab_info["stabilization_sr"]
    post_stab = [(sr, yb) for sr, yb in timeline if sr < stab_sr]
    if len(post_stab) < 2:
        return None
    bids_running: list[float] = []
    for sr, yb in post_stab:
        bids_running.append(yb)
        if len(bids_running) < 2:
            continue
        vol = _rolling_vol(bids_running)
        if vol > res_threshold:
            return {"resurgence_sr": sr, "vol_at_resurgence": round(vol, 6)}
    return None


def _detect_late_reversal(
    timeline:           list[tuple[float, float]],
    late_window_sr:     float = _LATE_WINDOW_SR,
    reversal_threshold: float = _REVERSAL_THRESHOLD,
    prior_level_window: int   = _PRIOR_LEVEL_WINDOW,
) -> dict[str, Any] | None:
    """Detect >reversal_threshold movement against prior direction in SR < late_window_sr."""
    early_bids = [yb for sr, yb in timeline if sr >= late_window_sr]
    late_snaps = [(sr, yb) for sr, yb in timeline if sr  < late_window_sr]
    if not late_snaps:
        return None
    if len(early_bids) >= prior_level_window:
        prior_sample = early_bids[-prior_level_window:]
    elif early_bids:
        prior_sample = early_bids
    else:
        prior_sample = [yb for _, yb in timeline[:3]]
    if not prior_sample:
        return None
    prior_level = sum(prior_sample) / len(prior_sample)
    max_magnitude = 0.0
    reversal_sr:  float | None = None
    if prior_level >= 0.50:
        for sr, yb in late_snaps:
            drop = prior_level - yb
            if drop > reversal_threshold and drop > max_magnitude:
                max_magnitude = drop
                reversal_sr   = sr
    else:
        for sr, yb in late_snaps:
            rise = yb - prior_level
            if rise > reversal_threshold and rise > max_magnitude:
                max_magnitude = rise
                reversal_sr   = sr
    if reversal_sr is not None:
        return {
            "reversal_sr":        reversal_sr,
            "reversal_magnitude": round(max_magnitude, 6),
            "prior_level":        round(prior_level, 6),
        }
    return None


# ---------------------------------------------------------------------------
# Policy B PnL helper
# ---------------------------------------------------------------------------

def _policy_b_pnl(
    timeline:         list[tuple[float, float]],
    entry_price:      float,
    shadow_size:      float,
    settlement_price: float | None,
    derisk_sr:        float = _DERISK_SR,
) -> float | None:
    tokens = shadow_size / max(entry_price, 1e-9)
    for sr, yb in timeline:
        if sr < derisk_sr:
            return round((yb - entry_price) * tokens, 8)
    if settlement_price is not None:
        return round((settlement_price - entry_price) * tokens, 8)
    return None


# ---------------------------------------------------------------------------
# Pre-stabilization slope (OLS on SR-descending segment)
# ---------------------------------------------------------------------------

def _compute_slope(timeline_segment: list[tuple[float, float]]) -> float | None:
    """
    Linear slope of yes_bid over time.  Positive = bid RISING as time passes
    (as SR decreases).  Returns None if < 2 points or degenerate X variance.
    """
    if len(timeline_segment) < 2:
        return None
    srs  = [sr for sr, _  in timeline_segment]
    bids = [yb for _,  yb in timeline_segment]
    n          = len(srs)
    sum_sr     = sum(srs)
    sum_bid    = sum(bids)
    sum_sr2    = sum(s * s for s in srs)
    sum_srbid  = sum(s * b for s, b in zip(srs, bids))
    denom = n * sum_sr2 - sum_sr * sum_sr
    if abs(denom) < 1e-9:
        return None
    # bid change per SR unit.  Negate: positive = rising over time.
    raw_slope = (n * sum_srbid - sum_sr * sum_bid) / denom
    return round(-raw_slope, 8)


# ---------------------------------------------------------------------------
# Survival classification (DIAGNOSTIC TRUTH — uses future post-stab data)
# ---------------------------------------------------------------------------

def _classify_survival(
    timeline:  list[tuple[float, float]],
    stab_info: dict[str, Any],
) -> dict[str, Any]:
    """
    Classify survival of a confirmed stabilization.

    Uses post-stabilization timeline data (DIAGNOSTIC TRUTH — future relative
    to the stabilization detection moment).

    stabilization_lifetime_seconds is also diagnostic: it measures duration
    from stabilization detection to the first failure event or final snapshot.
    """
    stab_sr   = stab_info["stabilization_sr"]
    post_stab = [(sr, yb) for sr, yb in timeline if sr < stab_sr]

    resurgence    = _detect_vol_resurgence(timeline, stab_info)
    has_resurgence = resurgence is not None
    resurgence_sr  = resurgence["resurgence_sr"] if resurgence else None

    reversal      = _detect_late_reversal(timeline)
    has_reversal   = reversal is not None
    reversal_sr    = reversal["reversal_sr"] if reversal else None

    if has_resurgence:
        survival   = FAILED_RESURGENCE
        failure_sr = resurgence_sr
    elif has_reversal:
        survival   = FAILED_LATE_REVERSAL
        failure_sr = reversal_sr
    else:
        survival   = SURVIVED
        failure_sr = None

    # Stabilization lifetime (diagnostic — uses post-stab data)
    if survival == SURVIVED:
        if post_stab:
            end_sr   = min(sr for sr, _ in post_stab)
            lifetime = round(stab_sr - end_sr, 2)
        else:
            lifetime = 0.0
    elif failure_sr is not None:
        lifetime = round(stab_sr - failure_sr, 2)
    else:
        lifetime = None

    return {
        "survival":                         survival,
        "has_post_stab_resurgence":         has_resurgence,
        "resurgence_sr":                    resurgence_sr,
        "has_late_reversal":                has_reversal,
        "reversal_sr":                      reversal_sr,
        "post_stab_snapshot_count":         len(post_stab),
        "stabilization_lifetime_seconds":   lifetime,   # diagnostic: uses post-stab
    }


# ---------------------------------------------------------------------------
# Feature extraction at stabilization moment (realtime-feasible predictor)
# ---------------------------------------------------------------------------

def _extract_stab_features(
    timeline:  list[tuple[float, float]],
    stab_info: dict[str, Any],
) -> dict[str, Any]:
    """
    Extract predictor features AT OR BEFORE the stabilization moment.

    No post-stabilization data is used here.  All features use only timeline
    entries with SR >= stabilization_sr (at or before detection).
    """
    stab_sr  = stab_info["stabilization_sr"]
    stab_bid = stab_info["stabilization_bid_level"]
    stab_vol = stab_info["vol_at_stabilization"]
    n_stable = stab_info["n_stable_snaps"]

    # Bids at and before stabilization (SR-descending, chronological)
    pre_and_stab = [(sr, yb) for sr, yb in timeline if sr >= stab_sr]

    # Partition: pre-stab vs stabilization window
    if len(pre_and_stab) >= n_stable:
        pre_stab    = pre_and_stab[:-n_stable]
    else:
        pre_stab    = []

    # Pre-stabilization volatility (std of all pre-stab bids)
    pre_bids = [yb for _, yb in pre_stab]
    pre_stab_vol: float | None = None
    if len(pre_bids) >= 2:
        s = _stdev_safe(pre_bids)
        pre_stab_vol = round(s, 6) if s is not None else None

    # Pre-stabilization slope (positive = bid rising over time)
    pre_stab_slope = _compute_slope(pre_stab) if len(pre_stab) >= 2 else None

    # Bid stability score: coefficient of variation at stab (lower = more stable)
    bid_stability_score: float | None = None
    if stab_bid > 1e-9:
        bid_stability_score = round(stab_vol / stab_bid, 6)

    # Distance from midpoint 0.5
    bid_distance_from_0_5 = round(abs(stab_bid - 0.5), 6)

    return {
        "stabilization_sr":              stab_sr,
        "stabilization_bid_level":       stab_bid,
        "rolling_vol_at_stabilization":  stab_vol,
        "bid_stability_score":           bid_stability_score,
        "stable_streak_length":          n_stable,
        "pre_stabilization_volatility":  pre_stab_vol,
        "pre_stabilization_slope":       pre_stab_slope,
        "bid_distance_from_0_5":         bid_distance_from_0_5,
        "n_pre_stab_snaps":              len(pre_stab),
    }


# ---------------------------------------------------------------------------
# Position classification (inventory continuity: max 1 per asset per epoch)
# ---------------------------------------------------------------------------

def classify_positions(
    events:          list[dict[str, Any]],
    settlement_map:  dict[tuple[Any, str], dict[str, Any]],
    epoch_timelines: dict[tuple[Any, str], list[tuple[float, float]]],
) -> list[dict[str, Any]]:
    """
    Classify stabilization survival for each simulated entry epoch.
    Applies max-1-position-per-asset inventory continuity.
    """
    epoch_groups: dict[tuple[Any, str], list[dict[str, Any]]] = defaultdict(list)
    for p in events:
        ep = p.get("epoch_start_ts")
        mk = p.get("market_key")
        if ep is None or mk is None:
            continue
        epoch_groups[(ep, mk)].append(p)
    for key in epoch_groups:
        epoch_groups[key].sort(key=lambda p: -float(p.get("seconds_remaining") or 0))

    sorted_keys = sorted(
        epoch_groups.keys(),
        key=lambda k: (k[0] if k[0] is not None else 0, k[1] or ""),
    )

    asset_entered: dict[str, bool] = {}
    records:       list[dict[str, Any]] = []
    prev_epoch_ts  = None

    for epoch_key in sorted_keys:
        ep_ts, mk = epoch_key
        epoch_events = epoch_groups[epoch_key]
        asset = _asset_from_event(epoch_events[0])

        if ep_ts != prev_epoch_ts:
            asset_entered = {}
            prev_epoch_ts = ep_ts

        if asset_entered.get(asset):
            continue

        entry_event = None
        for p in epoch_events:
            shadow = _compute_shadow(p)
            if shadow["nonzero"]:
                entry_event = p
                break
        if entry_event is None:
            continue

        asset_entered[asset] = True

        shadow          = _compute_shadow(entry_event)
        entry_price     = float(entry_event.get("entry_price") or 0.0)
        entry_sr        = float(entry_event.get("seconds_remaining") or 0.0)
        lifecycle_phase = str(entry_event.get("lifecycle_phase") or "")

        sett = settlement_map.get(epoch_key)
        settlement_price:  float | None = None
        settlement_label                = "NO_SNAPSHOT"
        unresolved                      = True

        if sett and sett["confidence"] == "HIGH":
            settlement_price = sett["settlement_price"]
            settlement_label = sett["inferred_settlement"]
            unresolved       = False
        elif sett and sett["confidence"] == "AMBIGUOUS":
            settlement_label = "AMBIGUOUS"

        all_snaps = epoch_timelines.get(epoch_key) or []
        timeline  = sorted(
            [(sr, yb) for sr, yb in all_snaps if sr < entry_sr],
            key=lambda s: -s[0],
        )

        stab_info = _detect_stabilization(timeline)
        stab_found = stab_info is not None

        if stab_found:
            survival_data = _classify_survival(timeline, stab_info)
            feat_data     = _extract_stab_features(timeline, stab_info)
        else:
            survival_data = {
                "survival":                       NO_STABILIZATION,
                "has_post_stab_resurgence":        False,
                "resurgence_sr":                  None,
                "has_late_reversal":              False,
                "reversal_sr":                    None,
                "post_stab_snapshot_count":       0,
                "stabilization_lifetime_seconds": None,
            }
            feat_data = {
                "stabilization_sr":              None,
                "stabilization_bid_level":       None,
                "rolling_vol_at_stabilization":  None,
                "bid_stability_score":           None,
                "stable_streak_length":          None,
                "pre_stabilization_volatility":  None,
                "pre_stabilization_slope":       None,
                "bid_distance_from_0_5":         None,
                "n_pre_stab_snaps":              None,
            }

        # PnL references
        tokens = shadow["c_size"] / max(entry_price, 1e-9)
        pnl_a  = (
            round((settlement_price - entry_price) * tokens, 8)
            if settlement_price is not None else None
        )
        pnl_b = _policy_b_pnl(timeline, entry_price, shadow["c_size"], settlement_price)

        records.append({
            "asset":               asset,
            "market_key":          mk,
            "epoch_start_ts":      ep_ts,
            "entry_price":         entry_price,
            "entry_sr":            entry_sr,
            "shadow_size_usd":     shadow["c_size"],
            "shadow_pct_bankroll": shadow["pct_bankroll"],
            "lifecycle_phase":     lifecycle_phase,
            "settlement":          settlement_label,
            "settlement_price":    settlement_price,
            "unresolved":          unresolved,
            "stabilization_found": stab_found,
            "pnl_policy_a":        pnl_a,
            "pnl_policy_b":        pnl_b,
            **survival_data,
            **feat_data,
        })

    return records


# ---------------------------------------------------------------------------
# Aggregate helpers
# ---------------------------------------------------------------------------

def _dominant_failure(group: list[dict[str, Any]]) -> str | None:
    r = sum(1 for p in group if p.get("survival") == FAILED_RESURGENCE)
    l = sum(1 for p in group if p.get("survival") == FAILED_LATE_REVERSAL)
    if r == 0 and l == 0:
        return None
    return FAILED_RESURGENCE if r >= l else FAILED_LATE_REVERSAL


def _asset_survival(positions: list[dict[str, Any]]) -> dict[str, Any]:
    stab = [p for p in positions if p.get("stabilization_found")]
    if not stab:
        return {"count": len(positions), "stabilization_count": 0, "survival_rate": None}
    surv = [p for p in stab if p.get("survival") == SURVIVED]
    fr   = [p for p in stab if p.get("survival") == FAILED_RESURGENCE]
    flr  = [p for p in stab if p.get("survival") == FAILED_LATE_REVERSAL]
    lifetimes = [p["stabilization_lifetime_seconds"] for p in stab
                 if p.get("stabilization_lifetime_seconds") is not None]
    return {
        "count":                      len(positions),
        "stabilization_count":        len(stab),
        "survival_count":             len(surv),
        "survival_rate":              _pct(len(surv), len(stab)),
        "failure_resurgence_count":   len(fr),
        "failure_late_reversal_count": len(flr),
        "mean_lifetime_seconds":      round(mean(lifetimes), 1) if lifetimes else None,
    }


def _bid_bucket_report(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stabilized = [p for p in positions if p.get("stabilization_found")]
    rows: list[dict[str, Any]] = []
    for lo, hi in _BID_BUCKETS:
        group = [
            p for p in stabilized
            if p.get("stabilization_bid_level") is not None
            and lo <= p["stabilization_bid_level"] < hi
        ]
        lbl = f"[{lo:.1f}-{hi:.2f})"
        if not group:
            rows.append({"bucket": lbl, "count": 0, "survival_rate": None, "dominant_failure": None})
            continue
        surv = sum(1 for p in group if p.get("survival") == SURVIVED)
        rows.append({
            "bucket":           lbl,
            "count":            len(group),
            "survival_rate":    _pct(surv, len(group)),
            "dominant_failure": _dominant_failure(group),
        })
    return rows


def _sr_bucket_report(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stabilized = [p for p in positions if p.get("stabilization_found")]
    rows: list[dict[str, Any]] = []
    for lo, hi in _SR_BUCKETS:
        group = [
            p for p in stabilized
            if p.get("stabilization_sr") is not None
            and lo <= p["stabilization_sr"] < hi
        ]
        lbl = f"[{lo:.0f}-{hi:.0f})"
        if not group:
            rows.append({"bucket": lbl, "count": 0, "survival_rate": None})
            continue
        surv = sum(1 for p in group if p.get("survival") == SURVIVED)
        lifetimes = [p["stabilization_lifetime_seconds"] for p in group
                     if p.get("stabilization_lifetime_seconds") is not None]
        rows.append({
            "bucket":           lbl,
            "count":            len(group),
            "survival_rate":    _pct(surv, len(group)),
            "dominant_failure": _dominant_failure(group),
            "mean_lifetime":    round(mean(lifetimes), 1) if lifetimes else None,
        })
    return rows


def _pnl_by_outcome(positions: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {s: [] for s in ALL_SURVIVAL_STATES}
    for p in positions:
        state = p.get("survival") or NO_STABILIZATION
        grouped.setdefault(state, []).append(p)
    result: dict[str, Any] = {}
    for state, group in grouped.items():
        settled_a = [p for p in group if p.get("pnl_policy_a") is not None]
        settled_b = [p for p in group if p.get("pnl_policy_b") is not None]
        pnl_a     = [p["pnl_policy_a"] for p in settled_a]
        pnl_b     = [p["pnl_policy_b"] for p in settled_b]
        sorted_a  = sorted(settled_a, key=lambda p: p.get("epoch_start_ts") or 0)
        dd_a      = _max_drawdown([p["pnl_policy_a"] for p in sorted_a])
        result[state] = {
            "count":                  len(group),
            "settled_count":          len(settled_a),
            "total_pnl_policy_a":     round(sum(pnl_a), 6) if pnl_a else 0.0,
            "mean_pnl_policy_a":      round(mean(pnl_a), 6) if pnl_a else None,
            "total_pnl_policy_b":     round(sum(pnl_b), 6) if pnl_b else 0.0,
            "mean_pnl_policy_b":      round(mean(pnl_b), 6) if pnl_b else None,
            "max_drawdown_policy_a":  dd_a,
        }
    return result


# ---------------------------------------------------------------------------
# Predictor separation: SURVIVED vs FAILED_RESURGENCE
# ---------------------------------------------------------------------------

def _predictor_separation(positions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compare realtime-feasible predictor features between SURVIVED and
    FAILED_RESURGENCE stabilized epochs.
    """
    survived  = [p for p in positions if p.get("survival") == SURVIVED]
    failed_r  = [p for p in positions if p.get("survival") == FAILED_RESURGENCE]

    feat_keys = [
        "stabilization_sr",
        "stabilization_bid_level",
        "rolling_vol_at_stabilization",
        "bid_stability_score",
        "pre_stabilization_volatility",
        "pre_stabilization_slope",
        "bid_distance_from_0_5",
    ]

    def _group_means(group: list[dict]) -> dict[str, Any] | None:
        if not group:
            return None
        out: dict[str, Any] = {"count": len(group)}
        for k in feat_keys:
            vals = [
                p[k] for p in group
                if p.get(k) is not None and p.get(k) != float("inf")
            ]
            out[f"mean_{k}"] = round(mean(vals), 6) if vals else None
        return out

    surv_means = _group_means(survived)
    fail_means = _group_means(failed_r)

    separating:    list[str]       = []
    best_predictor: str | None     = None
    best_diff_pct: float           = 0.0

    if surv_means and fail_means:
        for k in feat_keys:
            rk = f"mean_{k}"
            sv = surv_means.get(rk)
            fv = fail_means.get(rk)
            if sv is None or fv is None:
                continue
            denom    = max(abs(sv), abs(fv), 1e-9)
            diff_pct = abs(sv - fv) / denom * 100
            if diff_pct > 20:
                direction = "SURVIVED_higher" if sv > fv else "FAILED_higher"
                separating.append(
                    f"{k}: SURVIVED={sv:.4f}, FAILED_RESURGENCE={fv:.4f}, "
                    f"diff={diff_pct:.1f}% ({direction})"
                )
                if diff_pct > best_diff_pct:
                    best_diff_pct  = diff_pct
                    best_predictor = k

    return {
        "survived":                          surv_means,
        "failed_resurgence":                 fail_means,
        "separating_features":               separating,
        "best_realtime_predictor_candidate": best_predictor,
        "best_predictor_diff_pct":           round(best_diff_pct, 1) if best_predictor else None,
    }


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

def _verdict(
    stabilization_count: int,
    survival_rate_frac:  float,
    separating_features: list[str],
) -> dict[str, str]:
    if stabilization_count < _MIN_STAB_FOR_VERDICT:
        v    = MORE_DATA
        note = (
            f"Only {stabilization_count} stabilization events "
            f"(need >= {_MIN_STAB_FOR_VERDICT}). "
            "Insufficient sample for survival verdict."
        )
    elif survival_rate_frac >= _SURVIVAL_GUARD_THRESHOLD and separating_features:
        v    = GUARD_CANDIDATE
        note = (
            f"Survival rate {survival_rate_frac:.0%} with "
            f"{len(separating_features)} separating feature(s) found. "
            "Consider a stabilization survival gate: exit only when stabilization "
            "is predicted to survive; fall back to fixed SR<60 otherwise. "
            "Validate over multiple dates before any runtime consideration. "
            "Do NOT promote to runtime without a separately scoped Phase 3 implementation."
        )
    elif survival_rate_frac < _FIXED_BEST_THRESHOLD:
        v    = FIXED_BEST
        note = (
            f"Survival rate {survival_rate_frac:.0%} < "
            f"{_FIXED_BEST_THRESHOLD:.0%} threshold. "
            "Stabilization is too often transient compression. "
            "Fixed SR<60 derisk (Policy B) remains the best deployable option."
        )
    else:
        v    = MORE_DATA
        note = (
            f"Survival rate {survival_rate_frac:.0%} is inconclusive "
            f"(no clear feature separation or borderline rate). "
            "Run replay over multiple dates before designing a survival guard."
        )
    return {"verdict": v, "verdict_note": note}


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyse(
    events:          list[dict[str, Any]],
    settlement_map:  dict[tuple[Any, str], dict[str, Any]],
    epoch_timelines: dict[tuple[Any, str], list[tuple[float, float]]],
) -> dict[str, Any]:
    if not events:
        return {
            "event_count": 0,
            "error":       "no_zero_size_probe_v1_events_found",
            "guardrail":   "offline-only; no runtime changes",
        }

    bankroll_ref = 20.0
    for p in events:
        b = p.get("bankroll")
        if b:
            bankroll_ref = float(b)
            break

    positions = classify_positions(events, settlement_map, epoch_timelines)

    stabilized = [p for p in positions if p.get("stabilization_found")]
    no_stab    = [p for p in positions if not p.get("stabilization_found")]
    survived   = [p for p in stabilized if p.get("survival") == SURVIVED]
    failed_r   = [p for p in stabilized if p.get("survival") == FAILED_RESURGENCE]
    failed_lr  = [p for p in stabilized if p.get("survival") == FAILED_LATE_REVERSAL]

    stab_count = len(stabilized)
    surv_count = len(survived)
    surv_rate  = surv_count / max(stab_count, 1)

    # survival_after_sr120_rate
    stab_above_120 = [
        p for p in stabilized
        if (p.get("stabilization_sr") or 0.0) > _SR_ABOVE_120
    ]
    surv_above_120 = [p for p in stab_above_120 if p.get("survival") == SURVIVED]
    survival_after_sr120_rate: float | None = (
        round(len(surv_above_120) / len(stab_above_120), 4)
        if len(stab_above_120) >= _MIN_SR120_COUNT else None
    )

    # Stabilization lifetime stats (diagnostic)
    lifetimes = [
        p["stabilization_lifetime_seconds"]
        for p in stabilized
        if p.get("stabilization_lifetime_seconds") is not None
    ]
    surv_lifetimes  = [p["stabilization_lifetime_seconds"] for p in survived
                       if p.get("stabilization_lifetime_seconds") is not None]
    fail_lifetimes  = [p["stabilization_lifetime_seconds"] for p in failed_r
                       if p.get("stabilization_lifetime_seconds") is not None]

    pred_sep   = _predictor_separation(positions)
    bid_bkts   = _bid_bucket_report(positions)
    sr_bkts    = _sr_bucket_report(positions)
    pnl_out    = _pnl_by_outcome(positions)
    btc_pos    = [p for p in positions if p.get("asset") == "BTC"]
    eth_pos    = [p for p in positions if p.get("asset") == "ETH"]
    verd       = _verdict(stab_count, surv_rate, pred_sep.get("separating_features", []))

    return {
        "event_count":                   len(events),
        "position_count":                len(positions),
        "bankroll_ref":                  bankroll_ref,
        # Global survival
        "stabilization_count":           stab_count,
        "no_stabilization_count":        len(no_stab),
        "survival_count":                surv_count,
        "failure_resurgence_count":      len(failed_r),
        "failure_late_reversal_count":   len(failed_lr),
        "survival_rate":                 round(surv_rate, 4),
        "survival_rate_pct":             _pct(surv_count, stab_count),
        # Two added metrics
        "survival_after_sr120_rate":     survival_after_sr120_rate,
        "stabilization_lifetime_stats": {
            "all":       _stats(lifetimes),
            "survived":  _stats(surv_lifetimes),
            "failed_r":  _stats(fail_lifetimes),
        },
        # Per-asset
        "survival_by_asset": {
            "btc": _asset_survival(btc_pos),
            "eth": _asset_survival(eth_pos),
        },
        # Bucket breakdowns
        "survival_by_bid_bucket": bid_bkts,
        "survival_by_sr_bucket":  sr_bkts,
        # Feature separation
        "predictor_separation":   pred_sep,
        # PnL by outcome
        "pnl_by_outcome":         pnl_out,
        # Verdict
        "verdict":                verd,
        "simulation_rules": [
            "Max 1 position per asset per epoch (no reloads).",
            "Timeline filtered to post-entry snapshots (SR < entry_SR), sorted SR-descending.",
            f"Stabilization: rolling vol < {_STAB_VOL_THRESHOLD} for >= {_STAB_PERSIST_N} consecutive snapshots.",
            f"FAILED_RESURGENCE: rolling vol > {_RESURGENCE_THRESHOLD} after stabilization (>= 2 post-stab snaps required).",
            f"FAILED_LATE_REVERSAL: yes_bid moves > {_REVERSAL_THRESHOLD} against prior direction in SR < {_LATE_WINDOW_SR}s.",
            "FAILED_RESURGENCE has priority over FAILED_LATE_REVERSAL when both detected.",
            "diagnostic_survival_truth uses future post-stabilization timeline data.",
            "realtime_feasible_predictor_features use only data at or before stabilization_sr.",
            "stabilization_lifetime_seconds is diagnostic: duration from stab detection to failure or close.",
            f"survival_after_sr120_rate: survival rate for epochs with stabilization_sr > {_SR_ABOVE_120}s. "
            f"None if < {_MIN_SR120_COUNT} such events.",
            "Settlement inferred from market_snapshots yes_bid near close (proxy, not confirmed).",
        ],
        "guardrail": (
            "offline-only; does not change strategy, risk, execution, "
            "position_sizing.py, order_manager.py, paper/live separation, "
            "or any runtime behavior; survival labels use future post-stabilization "
            "data for diagnostic truth only — never a realtime trigger claim"
        ),
    }


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------

SEP  = "=" * 76
SEP2 = "-" * 76


def print_report(result: dict[str, Any], date_str: str) -> None:
    if "error" in result:
        print(f"\n{SEP}")
        print(f"  Stabilization Survival Replay v1  |  {date_str}")
        print(f"{SEP}")
        print(f"  ERROR: {result['error']}")
        print(f"{SEP}\n")
        return

    print(f"\n{SEP}")
    print(f"  Stabilization Survival Replay v1  |  {date_str}")
    print(f"{SEP}")
    print(f"  Positions        : {result['position_count']}")
    print(f"  Stabilized       : {result['stabilization_count']}")
    print(f"  No stabilization : {result['no_stabilization_count']}")
    print(f"  Survived         : {result['survival_count']}  ({result['survival_rate_pct']:.1f}%)")
    print(f"  Failed resurgence: {result['failure_resurgence_count']}")
    print(f"  Failed late rev  : {result['failure_late_reversal_count']}")
    sr120 = result.get("survival_after_sr120_rate")
    print(f"  Surv SR>120 rate : {sr120:.1%}" if sr120 is not None else "  Surv SR>120 rate : N/A (< 3 events)")

    # Lifetime stats
    lt = result.get("stabilization_lifetime_stats") or {}
    all_lt = lt.get("all") or {}
    surv_lt = lt.get("survived") or {}
    fail_lt = lt.get("failed_r") or {}
    print(f"\n  [Stabilization Lifetime (diagnostic — uses post-stab data)]")
    print(f"  All   : mean={all_lt.get('mean', 0):.1f}s  p50={all_lt.get('p50', 0):.1f}s  "
          f"min={all_lt.get('min', 0):.1f}s  max={all_lt.get('max', 0):.1f}s  n={all_lt.get('count', 0)}")
    print(f"  SURV  : mean={surv_lt.get('mean', 0):.1f}s  n={surv_lt.get('count', 0)}")
    print(f"  FAIL_R: mean={fail_lt.get('mean', 0):.1f}s  n={fail_lt.get('count', 0)}")

    # BTC/ETH
    print(f"\n{SEP2}")
    print(f"  SURVIVAL BY ASSET")
    print(f"{SEP2}")
    for label, key in [("BTC", "btc"), ("ETH", "eth")]:
        a = (result.get("survival_by_asset") or {}).get(key) or {}
        sc = a.get("stabilization_count", 0)
        if sc == 0:
            print(f"  {label}: no stabilized epochs")
            continue
        print(f"  {label}: n={a['count']}  stab={sc}  surv={a['survival_count']}  "
              f"surv_rate={a['survival_rate']:.1f}%  "
              f"failed_R={a['failure_resurgence_count']}  "
              f"failed_LR={a['failure_late_reversal_count']}  "
              f"mean_lifetime={a.get('mean_lifetime_seconds') or 0:.1f}s")

    # SR bucket
    print(f"\n{SEP2}")
    print(f"  SURVIVAL BY STABILIZATION SR BUCKET")
    print(f"{SEP2}")
    print(f"  {'Bucket':<16}  {'n':>4}  {'Surv%':>6}  {'DomFail':<22}  mean_lifetime")
    for row in result.get("survival_by_sr_bucket") or []:
        if row["count"] == 0:
            continue
        dom = row.get("dominant_failure") or "SURVIVED"
        lt_mean = row.get("mean_lifetime")
        lt_s    = f"{lt_mean:.1f}s" if lt_mean is not None else "N/A"
        sr_pct  = row.get("survival_rate")
        sr_s    = f"{sr_pct:.1f}%" if sr_pct is not None else "N/A"
        print(f"  {row['bucket']:<16}  {row['count']:>4}  {sr_s:>6}  {dom:<22}  {lt_s}")

    # Bid bucket
    print(f"\n{SEP2}")
    print(f"  SURVIVAL BY STABILIZATION BID BUCKET")
    print(f"{SEP2}")
    print(f"  {'Bucket':<16}  {'n':>4}  {'Surv%':>6}  DomFail")
    for row in result.get("survival_by_bid_bucket") or []:
        if row["count"] == 0:
            continue
        dom  = row.get("dominant_failure") or "SURVIVED"
        sr_p = row.get("survival_rate")
        sr_s = f"{sr_p:.1f}%" if sr_p is not None else "N/A"
        print(f"  {row['bucket']:<16}  {row['count']:>4}  {sr_s:>6}  {dom}")

    # Predictor separation
    print(f"\n{SEP2}")
    print(f"  PREDICTOR SEPARATION: SURVIVED vs FAILED_RESURGENCE")
    print(f"{SEP2}")
    ps   = result.get("predictor_separation") or {}
    sm   = ps.get("survived")  or {}
    fm   = ps.get("failed_resurgence") or {}
    n_s  = sm.get("count", 0)
    n_f  = fm.get("count", 0)
    print(f"  SURVIVED={n_s}  FAILED_RESURGENCE={n_f}")

    feat_display = [
        ("stabilization_sr",             "stab_sr          "),
        ("stabilization_bid_level",       "stab_bid         "),
        ("rolling_vol_at_stabilization",  "vol_at_stab      "),
        ("bid_stability_score",           "bid_stab_score   "),
        ("pre_stabilization_volatility",  "pre_stab_vol     "),
        ("pre_stabilization_slope",       "pre_stab_slope   "),
        ("bid_distance_from_0_5",         "bid_dist_0.5     "),
    ]
    print(f"  {'Feature':<22}  {'SURVIVED':>12}  {'FAILED_R':>12}")
    print(f"  {'-'*22}  {'-'*12}  {'-'*12}")
    for fk, disp in feat_display:
        rk = f"mean_{fk}"
        sv = sm.get(rk)
        fv = fm.get(rk)
        ss = f"{sv:.6f}" if sv is not None else "N/A"
        fs = f"{fv:.6f}" if fv is not None else "N/A"
        print(f"  {disp:<22}  {ss:>12}  {fs:>12}")

    seps = ps.get("separating_features") or []
    best = ps.get("best_realtime_predictor_candidate")
    if seps:
        print(f"\n  Separating features (>20% diff):")
        for s in seps:
            print(f"    - {s}")
    else:
        print(f"\n  No features show >20% relative difference.")
    if best:
        print(f"  Best predictor candidate: {best}  (diff={ps.get('best_predictor_diff_pct')}%)")

    # PnL by outcome
    print(f"\n{SEP2}")
    print(f"  PNL BY SURVIVAL OUTCOME")
    print(f"{SEP2}")
    po = result.get("pnl_by_outcome") or {}
    print(f"  {'Outcome':<24}  {'n':>4}  {'PnL(A)':>9}  {'PnL(B)':>9}  {'MaxDD(A)':>9}")
    for state in ALL_SURVIVAL_STATES:
        row = po.get(state) or {}
        if row.get("count", 0) == 0:
            continue
        print(f"  {state:<24}  {row['count']:>4}  "
              f"${row.get('total_pnl_policy_a', 0):>8.2f}  "
              f"${row.get('total_pnl_policy_b', 0):>8.2f}  "
              f"${row.get('max_drawdown_policy_a', 0):>8.4f}")

    # Verdict
    print(f"\n{SEP2}")
    print(f"  VERDICT")
    print(f"{SEP2}")
    vd = result.get("verdict") or {}
    print(f"  {vd.get('verdict', '?')}")
    note = vd.get("verdict_note", "")
    words = note.split()
    line  = "  "
    for word in words:
        if len(line) + len(word) + 1 > 78:
            print(line)
            line = "  " + word + " "
        else:
            line += word + " "
    if line.strip():
        print(line)

    print(f"\n  guardrail: {result.get('guardrail', '')}")
    print(f"{SEP}\n")


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(result: dict[str, Any], date_str: str, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now(tz=timezone.utc).strftime("%H%M")
    path = report_dir / f"stab_survival_{date_str}_{ts}.json"
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
        description="Stabilization Survival Replay v1 -- offline-only"
    )
    parser.add_argument("--date",           required=True)
    parser.add_argument("--write-report",   action="store_true")
    parser.add_argument("--asset",          default=None)
    parser.add_argument("--run-id",         default=None)
    parser.add_argument("--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--report-dir",     default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    qd     = Path(args.quant_data_dir)
    events = load_probe_events(
        args.date,
        quant_data_dir=qd,
        run_id=args.run_id,
        asset_filter=args.asset,
    )

    probe_epoch_keys: set[tuple[Any, str]] = set()
    for p in events:
        ep = p.get("epoch_start_ts")
        mk = p.get("market_key")
        if ep is not None and mk is not None:
            probe_epoch_keys.add((ep, mk))

    settlement_map  = build_settlement_map(args.date, qd, probe_epoch_keys)
    epoch_timelines = load_epoch_timelines(args.date, qd, probe_epoch_keys)

    result = analyse(events, settlement_map, epoch_timelines)
    print_report(result, args.date)

    if args.write_report:
        write_report(result, args.date, Path(args.report_dir))


if __name__ == "__main__":
    main()
