"""
Convergence Regime Classification Replay v1 -- offline replay tool.

Classifies the late-window YES-book behavior of each intra-epoch timeline
into one of five mutually exclusive regimes, and measures how well realtime-
feasible features can identify each regime without settlement knowledge.

Background:
  Exit Convergence Intelligence Replay v1 (2026-05-15) established:
    Policy B (fixed SR<60 derisk): best deployable policy
      PnL=$67.67, max DD=$1.11, WR=57.4%
    Policy D (vol-collapse): high WR (61.2%) but underperformed B by -$1.10
      reversal rate=34.1% → vol collapse fires too early
    Policy E (hybrid + settlement proxy): lowest reversal (8%) but research-only
    Main bottleneck: false/pseudo-convergence detection

Five regime labels (applied via priority hierarchy):
  Priority 1  LATE_REVERSAL
    After SR < 90s, yes_bid moves > 10pp against prior direction.
    Prior direction = mean of last 5 early-window (SR >= 90s) bids.
    Realtime-feasible.

  Priority 2  VOLATILITY_RESURGENCE
    Requires prior stabilization. After vol collapses below threshold,
    rolling vol re-expands above resurgence threshold.
    Realtime-feasible.

  Priority 3  REAL_CONVERGENCE
    yes_bid stabilized (vol collapsed) AND settlement confirms YES.
    DIAGNOSTIC ONLY: requires settlement outcome.

  Priority 4  PSEUDO_CONVERGENCE
    yes_bid stabilized (vol collapsed) AND settlement is NO.
    DIAGNOSTIC ONLY: requires settlement outcome.

  Priority 5  NO_CONVERGENCE
    No durable stabilization, or AMBIGUOUS settlement.
    Realtime-feasible (default label).

Two-view classification per epoch:
  diagnostic_regime  Uses settlement outcome — ground truth label.
  realtime_regime    Uses only backward-looking timeline features.
                     PSEUDO_CONVERGENCE never appears here: it is
                     indistinguishable from REAL in realtime view.

Two added metrics:
  pseudo_after_high_confidence_count
    Count of PSEUDO_CONVERGENCE epochs where the stabilization signal
    was "high confidence": stabilization_bid_level >= 0.70 AND
    vol_at_stabilization <= 0.01.  Captures how many pseudo epochs
    "fooled" the system with a convincing YES-territory stabilization.

  regime_transition_matrix
    Counts of within-epoch state transitions across all positions:
    entry_to_stabilized, stabilized_to_resurgent, etc.
    Describes the convergence trajectory landscape.

No future leakage:
  Classification features use only post-entry market_snapshot timelines.
  Settlement outcome is used ONLY for diagnostic_regime; never for
  realtime_regime or any realtime-feasible feature computation.

Data sources (local JSONL only -- no live API calls):
  runtime/quant_data/system_health/YYYY-MM-DD.jsonl    (zero_size_probe_v1)
  runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl  (timelines + settlement proxy)

Usage:
  python -m tools.convergence_regime_classification_replay --date 2026-05-15
  python -m tools.convergence_regime_classification_replay --date 2026-05-15 --write-report
  python -m tools.convergence_regime_classification_replay --date 2026-05-15 --asset BTC

Output:
  Console summary + optional runtime/reports/conv_regime_YYYY-MM-DD_HHMM.json

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

# Stabilization detection
_STAB_VOL_THRESHOLD = 0.02   # rolling vol < this → stabilizing
_STAB_PERSIST_N     = 3      # consecutive stable snapshots to confirm
_CONV_VOL_WINDOW    = 5      # rolling vol window size

# Volatility resurgence
_RESURGENCE_THRESHOLD = 0.04  # vol re-expands above this after stabilization

# Late reversal
_LATE_WINDOW_SR    = 90.0    # late window = SR < 90s
_REVERSAL_THRESHOLD = 0.10   # >10pp movement against prior direction = reversal
_PRIOR_LEVEL_WINDOW = 5      # last N early-window bids for prior level
_FINAL_WINDOW_N     = 3      # last N timeline bids for final_bid_level

# High-confidence stabilization (for pseudo_after_high_confidence_count)
_HIGH_CONF_BID_LEVEL     = 0.70   # bid in YES territory
_HIGH_CONF_VOL_THRESHOLD = 0.01   # stricter than stabilization threshold

# Policy B reference
_DERISK_SR = 60.0

# Verdict thresholds
_UNSAFE_DRAWDOWN_PCT = 10.0

# Regime labels (canonical)
REAL_CONVERGENCE      = "REAL_CONVERGENCE"
PSEUDO_CONVERGENCE    = "PSEUDO_CONVERGENCE"
VOLATILITY_RESURGENCE = "VOLATILITY_RESURGENCE"
LATE_REVERSAL         = "LATE_REVERSAL"
NO_CONVERGENCE        = "NO_CONVERGENCE"

ALL_REGIMES = [
    REAL_CONVERGENCE,
    PSEUDO_CONVERGENCE,
    VOLATILITY_RESURGENCE,
    LATE_REVERSAL,
    NO_CONVERGENCE,
]


# ---------------------------------------------------------------------------
# Shadow formula (identical to prior replay tools; not imported from runtime)
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
# Data loading (identical to prior replay tools)
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
# PnL / drawdown / stats helpers (identical to prior replay tools)
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
# Rolling volatility (identical to exit_convergence_intelligence_replay)
# ---------------------------------------------------------------------------

def _stdev_safe(values: list[float]) -> float | None:
    """Sample stdev. Returns None if fewer than 2 values."""
    n = len(values)
    if n < 2:
        return None
    m = sum(values) / n
    return (sum((x - m) ** 2 for x in values) / (n - 1)) ** 0.5


def _rolling_vol(bids: list[float], window: int = _CONV_VOL_WINDOW) -> float:
    """Rolling std of last `window` yes_bid values. Returns inf if < 2 values."""
    sample = bids[-window:]
    result = _stdev_safe(sample)
    return result if result is not None else float("inf")


# ---------------------------------------------------------------------------
# Convergence pattern detectors
# (all backward-looking; none accept settlement as input)
# ---------------------------------------------------------------------------

def _detect_stabilization(
    timeline: list[tuple[float, float]],
    vol_threshold: float = _STAB_VOL_THRESHOLD,
    persist_n: int = _STAB_PERSIST_N,
) -> dict[str, Any] | None:
    """
    Detect the first stabilization window in the post-entry timeline.

    Timeline must be sorted SR-descending (chronological: high SR → low SR).
    Returns {stabilization_sr, stabilization_bid_level, vol_at_stabilization,
             n_stable_snaps} at the moment PERSIST_N consecutive stable
    snapshots are confirmed.  Returns None if no stabilization found.
    """
    bids:   list[float] = []
    streak: int         = 0

    for sr, yb in timeline:
        bids.append(yb)
        vol = _rolling_vol(bids)
        if vol < vol_threshold:
            streak += 1
            if streak >= persist_n:
                stab_bids  = bids[-persist_n:]
                mean_bid   = sum(stab_bids) / len(stab_bids)
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
    timeline:       list[tuple[float, float]],
    stab_info:      dict[str, Any] | None,
    res_threshold:  float = _RESURGENCE_THRESHOLD,
) -> dict[str, Any] | None:
    """
    Detect if rolling vol re-expands after stabilization.

    Only checks snapshots after stabilization_sr (lower SR values).
    Requires at least 2 post-stabilization bids before evaluating vol.
    Returns {resurgence_sr, vol_at_resurgence} or None.
    """
    if stab_info is None:
        return None
    stab_sr   = stab_info["stabilization_sr"]
    post_stab = [(sr, yb) for sr, yb in timeline if sr < stab_sr]
    if len(post_stab) < 2:
        return None
    bids_running: list[float] = []
    for sr, yb in post_stab:   # already SR-descending = chronological
        bids_running.append(yb)
        if len(bids_running) < 2:
            continue            # need at least 2 to compute vol
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
    """
    Detect if yes_bid moves > reversal_threshold against prior direction
    in the late window (SR < late_window_sr).

    prior_level = mean of the last PRIOR_LEVEL_WINDOW early-window bids
    (SR >= late_window_sr). Falls back to first 3 timeline bids for late entries.

    Direction check:
      prior_level >= 0.50 → YES-direction; reversal = bid drops below
                             prior_level - reversal_threshold
      prior_level <  0.50 → NO-direction;  reversal = bid rises above
                             prior_level + reversal_threshold

    Returns {reversal_sr, reversal_magnitude, prior_level} or None.
    """
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
# Epoch classification (core)
# ---------------------------------------------------------------------------

def _classify_epoch(
    timeline:          list[tuple[float, float]],
    settlement_label:  str,
    settlement_price:  float | None,
) -> dict[str, Any]:
    """
    Classify one epoch trajectory into diagnostic and realtime regimes.

    timeline: sorted SR-descending (chronological).
    settlement_label: "YES" | "NO" | "AMBIGUOUS" | "NO_SNAPSHOT"
    settlement_price: 1.0 | 0.0 | None

    diagnostic_regime uses settlement_label and settlement_price.
    realtime_regime uses ONLY backward-looking features — no settlement info.

    Settlement is never used for realtime_regime or any realtime feature.
    """
    stab      = _detect_stabilization(timeline)
    resurgence = _detect_vol_resurgence(timeline, stab)
    reversal  = _detect_late_reversal(timeline)

    has_stabilization  = stab      is not None
    has_vol_resurgence = resurgence is not None
    has_late_reversal  = reversal  is not None

    # Final bid level: mean of last FINAL_WINDOW_N bids (realtime-feasible)
    recent_bids = [yb for _, yb in timeline[-_FINAL_WINDOW_N:]] if timeline else []
    final_bid_level: float | None = (
        round(sum(recent_bids) / len(recent_bids), 6) if recent_bids else None
    )
    final_vol = _rolling_vol([yb for _, yb in timeline]) if len(timeline) >= 2 else float("inf")

    # High-confidence stabilization (realtime-feasible — no settlement used)
    is_high_confidence_stab = (
        has_stabilization and
        stab["stabilization_bid_level"] >= _HIGH_CONF_BID_LEVEL and
        stab["vol_at_stabilization"]    <= _HIGH_CONF_VOL_THRESHOLD
    )

    # ------------------------------------------------------------------
    # Diagnostic regime (uses settlement — ground truth, research label)
    # ------------------------------------------------------------------
    if has_late_reversal:
        diagnostic_regime = LATE_REVERSAL
    elif has_vol_resurgence:
        diagnostic_regime = VOLATILITY_RESURGENCE
    elif has_stabilization:
        if settlement_label == "YES":
            diagnostic_regime = REAL_CONVERGENCE
        elif settlement_label == "NO":
            diagnostic_regime = PSEUDO_CONVERGENCE
        else:
            diagnostic_regime = NO_CONVERGENCE     # AMBIGUOUS / NO_SNAPSHOT
    else:
        diagnostic_regime = NO_CONVERGENCE

    # ------------------------------------------------------------------
    # Realtime regime (no settlement — realtime-feasible prediction)
    # PSEUDO_CONVERGENCE never appears here.
    # ------------------------------------------------------------------
    if has_late_reversal:
        realtime_regime = LATE_REVERSAL
    elif has_vol_resurgence:
        realtime_regime = VOLATILITY_RESURGENCE
    elif has_stabilization and final_bid_level is not None and final_bid_level >= _YES_THRESHOLD:
        realtime_regime = REAL_CONVERGENCE         # predicted, not confirmed
    else:
        realtime_regime = NO_CONVERGENCE

    # realtime_correct: None when settlement unknown (AMBIGUOUS/NO_SNAPSHOT)
    realtime_correct: bool | None = None
    if settlement_label in ("YES", "NO"):
        realtime_correct = realtime_regime == diagnostic_regime

    return {
        # Detection results (realtime-feasible)
        "has_stabilization":       has_stabilization,
        "stabilization_sr":        stab["stabilization_sr"]        if stab else None,
        "stabilization_bid_level": stab["stabilization_bid_level"] if stab else None,
        "vol_at_stabilization":    stab["vol_at_stabilization"]    if stab else None,
        "n_stable_snaps":          stab["n_stable_snaps"]          if stab else None,
        "has_vol_resurgence":      has_vol_resurgence,
        "resurgence_sr":           resurgence["resurgence_sr"]     if resurgence else None,
        "vol_at_resurgence":       resurgence["vol_at_resurgence"] if resurgence else None,
        "has_late_reversal":       has_late_reversal,
        "reversal_sr":             reversal["reversal_sr"]         if reversal else None,
        "reversal_magnitude":      reversal["reversal_magnitude"]  if reversal else None,
        "prior_level":             reversal["prior_level"]         if reversal else None,
        "final_bid_level":         final_bid_level,
        "final_vol":               final_vol,
        "is_high_confidence_stab": is_high_confidence_stab,
        # Regime labels
        "diagnostic_regime":       diagnostic_regime,
        "realtime_regime":         realtime_regime,
        "realtime_correct":        realtime_correct,
    }


# ---------------------------------------------------------------------------
# Policy B PnL helper (realtime-feasible; no settlement needed for exit)
# ---------------------------------------------------------------------------

def _policy_b_pnl(
    timeline:        list[tuple[float, float]],
    entry_price:     float,
    shadow_size:     float,
    settlement_price: float | None,
    derisk_sr:       float = _DERISK_SR,
) -> float | None:
    """
    Compute Policy B PnL: exit at first SR < derisk_sr, else hold to settlement.
    Timeline is SR-descending (chronological).
    """
    tokens = shadow_size / max(entry_price, 1e-9)
    for sr, yb in timeline:
        if sr < derisk_sr:
            return round((yb - entry_price) * tokens, 8)
    if settlement_price is not None:
        return round((settlement_price - entry_price) * tokens, 8)
    return None


# ---------------------------------------------------------------------------
# Position classification (inventory continuity: max 1 per asset per epoch)
# ---------------------------------------------------------------------------

def classify_positions(
    events:          list[dict[str, Any]],
    settlement_map:  dict[tuple[Any, str], dict[str, Any]],
    epoch_timelines: dict[tuple[Any, str], list[tuple[float, float]]],
) -> list[dict[str, Any]]:
    """
    Classify each simulated entry epoch into a convergence regime.

    Applies max-1-position-per-asset inventory continuity (same as prior tools).
    Returns one record per simulated entry.
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

        shadow      = _compute_shadow(entry_event)
        entry_price = float(entry_event.get("entry_price") or 0.0)
        entry_sr    = float(entry_event.get("seconds_remaining") or 0.0)

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
            key=lambda s: -s[0],   # SR-descending = chronological
        )

        classification = _classify_epoch(timeline, settlement_label, settlement_price)

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
            "settlement":          settlement_label,
            "settlement_price":    settlement_price,
            "unresolved":          unresolved,
            "pnl_policy_a":        pnl_a,
            "pnl_policy_b":        pnl_b,
            **classification,
        })

    return records


# ---------------------------------------------------------------------------
# Regime aggregate report
# ---------------------------------------------------------------------------

def _regime_aggregate(
    positions:    list[dict[str, Any]],
    regime_field: str,
    bankroll_ref: float,
) -> dict[str, Any]:
    """Compute per-regime metrics, grouped by the specified regime field."""
    total  = len(positions)
    result = {}

    for label in ALL_REGIMES:
        group = [p for p in positions if p.get(regime_field) == label]
        count = len(group)
        if count == 0:
            result[label] = {"count": 0, "pct": 0.0}
            continue

        settled_a = [p for p in group if p.get("pnl_policy_a") is not None]
        settled_b = [p for p in group if p.get("pnl_policy_b") is not None]
        pnl_a_vals = [p["pnl_policy_a"] for p in settled_a]
        pnl_b_vals = [p["pnl_policy_b"] for p in settled_b]

        # Drawdown (by epoch_start_ts order)
        sorted_a = sorted(settled_a, key=lambda p: (p.get("epoch_start_ts") or 0))
        dd_a = _max_drawdown([p["pnl_policy_a"] for p in sorted_a])
        dd_a_pct = round(dd_a / bankroll_ref * 100, 2) if bankroll_ref > 0 else 0.0

        # Realtime accuracy (meaningful for diagnostic field comparison)
        correct_labeled = [p for p in group if p.get("realtime_correct") is not None]
        rt_acc = (
            round(sum(1 for p in correct_labeled if p["realtime_correct"]) / len(correct_labeled), 4)
            if correct_labeled else None
        )

        # BTC / ETH
        btc = [p for p in group if p.get("asset") == "BTC"]
        eth = [p for p in group if p.get("asset") == "ETH"]

        # Feature means (realtime-feasible)
        stab_srs   = [p["stabilization_sr"]        for p in group if p.get("stabilization_sr") is not None]
        vol_stab   = [p["vol_at_stabilization"]     for p in group if p.get("vol_at_stabilization") is not None]
        final_bids = [p["final_bid_level"]          for p in group if p.get("final_bid_level") is not None]
        final_vols = [p["final_vol"]                for p in group
                      if p.get("final_vol") is not None and p["final_vol"] != float("inf")]
        rev_mags   = [p["reversal_magnitude"]       for p in group if p.get("reversal_magnitude") is not None]

        # Win rate (Policy A)
        wins_a = sum(1 for v in pnl_a_vals if v > 0)
        wr_a   = _pct(wins_a, len(settled_a))

        result[label] = {
            "count":                  count,
            "pct":                    _pct(count, total),
            "btc_count":              len(btc),
            "eth_count":              len(eth),
            "settled_count":          len(settled_a),
            # PnL
            "total_pnl_policy_a":     round(sum(pnl_a_vals), 6) if pnl_a_vals else 0.0,
            "mean_pnl_policy_a":      round(mean(pnl_a_vals), 6) if pnl_a_vals else None,
            "total_pnl_policy_b":     round(sum(pnl_b_vals), 6) if pnl_b_vals else 0.0,
            "mean_pnl_policy_b":      round(mean(pnl_b_vals), 6) if pnl_b_vals else None,
            "win_rate_policy_a":      wr_a,
            "pnl_a_stats":            _stats(pnl_a_vals),
            # Drawdown
            "max_drawdown_policy_a":  dd_a,
            "max_dd_pct_bankroll":    dd_a_pct,
            # Realtime accuracy
            "realtime_prediction_accuracy": rt_acc,
            # Convergence timing
            "mean_convergence_sr":    round(mean(stab_srs), 1) if stab_srs else None,
            # Late reversal within regime
            "late_reversal_rate":     _pct(sum(1 for p in group if p.get("has_late_reversal")), count),
            # Vol / bid metrics
            "mean_vol_at_stabilization": round(mean(vol_stab), 6) if vol_stab else None,
            "mean_final_bid_level":      round(mean(final_bids), 6) if final_bids else None,
            "mean_final_vol":            round(mean(final_vols), 6) if final_vols else None,
            "mean_reversal_magnitude":   round(mean(rev_mags), 6) if rev_mags else None,
        }

    return result


# ---------------------------------------------------------------------------
# Feature separation: REAL_CONVERGENCE vs PSEUDO_CONVERGENCE
# ---------------------------------------------------------------------------

def _feature_separation(positions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compare backward-looking features between diagnostic REAL and PSEUDO epochs.
    Identifies which features may predict pseudo-convergence without settlement.
    """
    real   = [p for p in positions if p.get("diagnostic_regime") == REAL_CONVERGENCE]
    pseudo = [p for p in positions if p.get("diagnostic_regime") == PSEUDO_CONVERGENCE]

    feat_keys = [
        "stabilization_sr",
        "stabilization_bid_level",
        "vol_at_stabilization",
        "n_stable_snaps",
        "final_bid_level",
        "final_vol",
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
        out["has_vol_resurgence_rate"] = _pct(
            sum(1 for p in group if p.get("has_vol_resurgence")), len(group))
        out["has_late_reversal_rate"] = _pct(
            sum(1 for p in group if p.get("has_late_reversal")), len(group))
        out["is_high_confidence_stab_rate"] = _pct(
            sum(1 for p in group if p.get("is_high_confidence_stab")), len(group))
        return out

    real_means   = _group_means(real)
    pseudo_means = _group_means(pseudo)

    # Identify separating features (>20% relative difference between means)
    separating: list[str] = []
    if real_means and pseudo_means:
        for k in feat_keys:
            rk = f"mean_{k}"
            rv = real_means.get(rk)
            pv = pseudo_means.get(rk)
            if rv is None or pv is None:
                continue
            denom = max(abs(rv), abs(pv), 1e-9)
            diff_pct = abs(rv - pv) / denom * 100
            if diff_pct > 20:
                direction = "REAL higher" if rv > pv else "PSEUDO higher"
                separating.append(
                    f"{k}: REAL={rv:.4f}, PSEUDO={pv:.4f}, "
                    f"diff={diff_pct:.1f}% ({direction})"
                )

    # How many PSEUDO epochs were misclassified as REAL by realtime view
    pseudo_confused = sum(
        1 for p in pseudo if p.get("realtime_regime") == REAL_CONVERGENCE
    )
    pseudo_confusion_rate = _pct(pseudo_confused, len(pseudo)) if pseudo else 0.0

    # Any realtime feature that could help predict pseudo (qualitative)
    realtime_pseudo_signal: str
    if "vol_at_stabilization" in " ".join(separating):
        realtime_pseudo_signal = (
            "vol_at_stabilization differs between REAL and PSEUDO — "
            "a stricter vol floor may help filter pseudo epochs."
        )
    elif "stabilization_bid_level" in " ".join(separating):
        realtime_pseudo_signal = (
            "stabilization_bid_level differs — "
            "bid level at convergence may weakly predict pseudo-convergence."
        )
    elif "final_bid_level" in " ".join(separating):
        realtime_pseudo_signal = (
            "final_bid_level differs — "
            "late-window bid level provides some pseudo-convergence signal."
        )
    elif separating:
        realtime_pseudo_signal = (
            f"Some separation found in: {separating[0].split(':')[0]}. "
            "Consider using this feature as an additional exit gate."
        )
    else:
        realtime_pseudo_signal = (
            "No single realtime feature reliably separates REAL from PSEUDO. "
            "More sessions required before composite scoring is warranted."
        )

    return {
        "real_convergence":             real_means,
        "pseudo_convergence":           pseudo_means,
        "separating_features":          separating,
        "realtime_pseudo_confusion_count": pseudo_confused,
        "realtime_pseudo_confusion_rate":  pseudo_confusion_rate,
        "realtime_pseudo_signal":          realtime_pseudo_signal,
    }


# ---------------------------------------------------------------------------
# Regime transition matrix
# ---------------------------------------------------------------------------

def _build_transition_matrix(positions: list[dict[str, Any]]) -> dict[str, int]:
    """
    Count within-epoch state transitions across all classified positions.

    Each position contributes exactly one path through the state space:
      entry → [stabilized | no_stabilization]
        stabilized → [resurgent | reversed | held_stable]
          resurgent → [reversed | then_settled]
        no_stabilization → [reversed | no_event]
    """
    matrix: dict[str, int] = {
        "entry_to_stabilized":       0,
        "entry_to_no_stabilization": 0,
        "stabilized_to_resurgent":   0,
        "stabilized_to_reversed":    0,
        "stabilized_to_held_stable": 0,
        "resurgent_to_reversed":     0,
        "resurgent_then_settled":    0,
        "no_stab_to_reversed":       0,
        "no_stab_no_event":          0,
    }

    for p in positions:
        has_stab   = p.get("has_stabilization",  False)
        has_resurg = p.get("has_vol_resurgence", False)
        has_rev    = p.get("has_late_reversal",  False)

        if has_stab:
            matrix["entry_to_stabilized"] += 1
            if has_resurg:
                matrix["stabilized_to_resurgent"] += 1
                if has_rev:
                    matrix["resurgent_to_reversed"] += 1
                else:
                    matrix["resurgent_then_settled"] += 1
            elif has_rev:
                matrix["stabilized_to_reversed"] += 1
            else:
                matrix["stabilized_to_held_stable"] += 1
        else:
            matrix["entry_to_no_stabilization"] += 1
            if has_rev:
                matrix["no_stab_to_reversed"] += 1
            else:
                matrix["no_stab_no_event"] += 1

    return matrix


# ---------------------------------------------------------------------------
# Next-policy recommendation
# ---------------------------------------------------------------------------

def _recommend_next_policy(
    positions:        list[dict[str, Any]],
    feature_sep:      dict[str, Any],
    trans_matrix:     dict[str, int],
) -> dict[str, str]:
    n = max(len(positions), 1)
    resurg_total  = (trans_matrix.get("stabilized_to_resurgent", 0) +
                     trans_matrix.get("resurgent_to_reversed", 0))
    late_rev_count = sum(1 for p in positions if p.get("diagnostic_regime") == LATE_REVERSAL)
    pseudo_count   = sum(1 for p in positions if p.get("diagnostic_regime") == PSEUDO_CONVERGENCE)
    pseudo_confused = feature_sep.get("realtime_pseudo_confusion_count", 0)
    sep_features    = feature_sep.get("separating_features", [])

    if resurg_total / n > 0.15:
        policy = "VOLATILITY_RESURGENCE_GUARD"
        note   = (
            f"Vol resurgence present in {resurg_total}/{n} epoch paths ({resurg_total/n:.0%}). "
            "Add post-stabilization resurgence check: if vol re-expands after collapse, "
            "defer convergence exit and fall back to fixed SR<60 derisk."
        )
    elif late_rev_count / n > 0.20:
        policy = "LATE_WINDOW_SR_GUARD_TIGHTEN"
        note   = (
            f"LATE_REVERSAL in {late_rev_count}/{n} epochs ({late_rev_count/n:.0%}). "
            "Tighten SR guard to <45s or add directional persistence confirmation "
            "before any convergence exit trigger."
        )
    elif pseudo_confused > 0 and sep_features:
        policy = "HIGH_CONFIDENCE_STAB_COMPOSITE_FILTER"
        note   = (
            f"{pseudo_confused} PSEUDO epochs misclassified as REAL in realtime view. "
            f"Separating signal found: {sep_features[0].split(':')[0]}. "
            "Research a composite score (bid level × stable duration × vol floor) "
            "to add a PSEUDO_GUARD gate before promoting convergence exits."
        )
    elif pseudo_count > 0 and not sep_features:
        policy = "MORE_DATA_NEEDED"
        note   = (
            f"{pseudo_count} PSEUDO epochs found but no realtime feature separates "
            "REAL from PSEUDO. Run replay over multiple dates before designing "
            "a convergence-aware exit filter."
        )
    else:
        policy = "CONTINUE_FIXED_DERISK_SR60"
        note   = (
            "No strong evidence for a better convergence policy. "
            "Fixed SR<60 derisk (Policy B) remains the best deployable option. "
            "Collect more sessions before revisiting."
        )

    return {"recommended_policy": policy, "recommendation_note": note}


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

    total_events = len(events)
    bankroll_ref = 20.0
    for p in events:
        b = p.get("bankroll")
        if b:
            bankroll_ref = float(b)
            break

    positions = classify_positions(events, settlement_map, epoch_timelines)

    # Per-regime aggregates
    diag_report = _regime_aggregate(positions, "diagnostic_regime", bankroll_ref)
    rt_report   = _regime_aggregate(positions, "realtime_regime",   bankroll_ref)

    # Feature separation
    feat_sep = _feature_separation(positions)

    # Transition matrix
    trans_matrix = _build_transition_matrix(positions)

    # pseudo_after_high_confidence_count
    pseudo_high_conf = sum(
        1 for p in positions
        if p.get("diagnostic_regime") == PSEUDO_CONVERGENCE
        and p.get("is_high_confidence_stab", False)
    )

    # Realtime accuracy (across all positions with known settlement)
    labeled = [p for p in positions if p.get("realtime_correct") is not None]
    realtime_accuracy = (
        round(sum(1 for p in labeled if p["realtime_correct"]) / len(labeled), 4)
        if labeled else None
    )

    # Recommendation
    recommendation = _recommend_next_policy(positions, feat_sep, trans_matrix)

    return {
        "event_count":                    total_events,
        "position_count":                 len(positions),
        "bankroll_ref":                   bankroll_ref,
        "diagnostic_regimes":             diag_report,
        "realtime_regimes":               rt_report,
        "feature_separation":             feat_sep,
        "regime_transition_matrix":       trans_matrix,
        "pseudo_after_high_confidence_count": pseudo_high_conf,
        "realtime_accuracy":              realtime_accuracy,
        "recommendation":                 recommendation,
        "simulation_rules": [
            "Max 1 position per asset per epoch (no reloads; same as prior replay tools).",
            "Timeline filtered to post-entry snapshots (SR < entry_SR), sorted SR-descending.",
            f"Stabilization: rolling vol < {_STAB_VOL_THRESHOLD} for >= {_STAB_PERSIST_N} "
            "consecutive snapshots.",
            f"Vol resurgence: rolling vol > {_RESURGENCE_THRESHOLD} after stabilization "
            "(requires >= 2 post-stabilization snapshots to evaluate).",
            f"Late reversal: yes_bid moves > {_REVERSAL_THRESHOLD} against prior direction "
            f"in SR < {_LATE_WINDOW_SR}s window.",
            "diagnostic_regime uses settlement outcome (REAL/PSEUDO require YES/NO settlement).",
            "realtime_regime uses ONLY backward-looking timeline features — no settlement.",
            "PSEUDO_CONVERGENCE never appears in realtime_regime: it is indistinguishable "
            "from REAL_CONVERGENCE without settlement outcome.",
            "pseudo_after_high_confidence_count = PSEUDO epochs where "
            f"bid >= {_HIGH_CONF_BID_LEVEL} AND vol <= {_HIGH_CONF_VOL_THRESHOLD} at stabilization.",
            "regime_transition_matrix counts within-epoch state-transition paths.",
            "Settlement inferred from market_snapshots yes_bid near close (proxy, not confirmed).",
        ],
        "guardrail": (
            "offline-only; does not change strategy, risk, execution, "
            "position_sizing.py, order_manager.py, paper/live separation, "
            "or any runtime behavior; diagnostic_regime uses settlement outcome "
            "for REAL/PSEUDO labeling — never used as a realtime trigger claim"
        ),
    }


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------

SEP  = "=" * 76
SEP2 = "-" * 76


def _print_regime_row(label: str, r: dict[str, Any]) -> None:
    if r.get("count", 0) == 0:
        print(f"  {label:<26}: 0 epochs")
        return
    pnl_a  = r.get("total_pnl_policy_a") or 0.0
    pnl_b  = r.get("total_pnl_policy_b") or 0.0
    dd_a   = r.get("max_drawdown_policy_a") or 0.0
    rt_acc = r.get("realtime_prediction_accuracy")
    acc_s  = f"{rt_acc:.1%}" if rt_acc is not None else "N/A"
    print(
        f"  {label:<26}: n={r['count']:>3} ({r['pct']:.1f}%)  "
        f"BTC={r.get('btc_count',0)}  ETH={r.get('eth_count',0)}  "
        f"PnL(A)=${pnl_a:>7.2f}  PnL(B)=${pnl_b:>7.2f}  "
        f"DD=${dd_a:.3f}  RT-acc={acc_s}"
    )


def print_report(result: dict[str, Any], date_str: str) -> None:
    if "error" in result:
        print(f"\n{SEP}")
        print(f"  Convergence Regime Classification Replay v1  |  {date_str}")
        print(f"{SEP}")
        print(f"  ERROR: {result['error']}")
        print(f"{SEP}\n")
        return

    print(f"\n{SEP}")
    print(f"  Convergence Regime Classification Replay v1  |  {date_str}")
    print(f"{SEP}")
    print(f"  Events          : {result['event_count']}")
    print(f"  Positions       : {result['position_count']}")
    print(f"  Bankroll ref    : ${result['bankroll_ref']:.2f}")
    rt_acc = result.get("realtime_accuracy")
    print(f"  Realtime acc.   : {rt_acc:.1%}" if rt_acc is not None else "  Realtime acc.   : N/A")
    print(f"  PseudoHighConf  : {result.get('pseudo_after_high_confidence_count', 0)}")

    # Diagnostic regime table
    print(f"\n{SEP2}")
    print(f"  DIAGNOSTIC REGIME DISTRIBUTION  (uses settlement -- ground truth)")
    print(f"{SEP2}")
    dr = result.get("diagnostic_regimes") or {}
    for label in ALL_REGIMES:
        _print_regime_row(label, dr.get(label) or {})

    # Realtime regime table
    print(f"\n{SEP2}")
    print(f"  REALTIME REGIME DISTRIBUTION  (no settlement -- deployable features only)")
    print(f"{SEP2}")
    rr = result.get("realtime_regimes") or {}
    for label in ALL_REGIMES:
        _print_regime_row(label, rr.get(label) or {})

    # Feature separation
    print(f"\n{SEP2}")
    print(f"  FEATURE SEPARATION: REAL vs PSEUDO (diagnostic epochs only)")
    print(f"{SEP2}")
    fs = result.get("feature_separation") or {}
    rm = fs.get("real_convergence")  or {}
    pm = fs.get("pseudo_convergence") or {}
    print(f"  REAL  epochs : {rm.get('count', 0)}")
    print(f"  PSEUDO epochs: {pm.get('count', 0)}")
    print(f"  Realtime confusion (PSEUDO labeled as REAL): "
          f"{fs.get('realtime_pseudo_confusion_count', 0)}  "
          f"({fs.get('realtime_pseudo_confusion_rate', 0):.1f}% of PSEUDO epochs)")

    feat_keys_display = [
        ("stabilization_sr",        "mean_stab_sr      "),
        ("stabilization_bid_level",  "mean_stab_bid     "),
        ("vol_at_stabilization",     "mean_vol_at_stab  "),
        ("n_stable_snaps",           "mean_n_stable_snaps"),
        ("final_bid_level",          "mean_final_bid    "),
        ("final_vol",                "mean_final_vol    "),
    ]
    print(f"\n  {'Feature':<26}  {'REAL':>10}  {'PSEUDO':>10}")
    print(f"  {'-'*26}  {'-'*10}  {'-'*10}")
    for feat_key, display in feat_keys_display:
        rk = f"mean_{feat_key}"
        rv = rm.get(rk)
        pv = pm.get(rk)
        rs = f"{rv:.6f}" if rv is not None else "N/A"
        ps = f"{pv:.6f}" if pv is not None else "N/A"
        print(f"  {display:<26}  {rs:>10}  {ps:>10}")
    print(f"  {'resurgence_rate':<26}  "
          f"{rm.get('has_vol_resurgence_rate', 0.0):>9.1f}%  "
          f"{pm.get('has_vol_resurgence_rate', 0.0):>9.1f}%")
    print(f"  {'reversal_rate':<26}  "
          f"{rm.get('has_late_reversal_rate', 0.0):>9.1f}%  "
          f"{pm.get('has_late_reversal_rate', 0.0):>9.1f}%")
    print(f"  {'high_conf_stab_rate':<26}  "
          f"{rm.get('is_high_confidence_stab_rate', 0.0):>9.1f}%  "
          f"{pm.get('is_high_confidence_stab_rate', 0.0):>9.1f}%")

    seps = fs.get("separating_features") or []
    if seps:
        print(f"\n  Separating features (>20% relative diff):")
        for s in seps:
            print(f"    - {s}")
    else:
        print(f"\n  No features show >20% relative difference between REAL and PSEUDO.")

    sig = fs.get("realtime_pseudo_signal", "")
    if sig:
        print(f"\n  Signal: {sig}")

    # Transition matrix
    print(f"\n{SEP2}")
    print(f"  REGIME TRANSITION MATRIX")
    print(f"{SEP2}")
    tm = result.get("regime_transition_matrix") or {}
    for key, val in tm.items():
        print(f"  {key:<35}: {val:>4}")

    # Recommendation
    print(f"\n{SEP2}")
    print(f"  RECOMMENDATION")
    print(f"{SEP2}")
    rec = result.get("recommendation") or {}
    print(f"  Policy  : {rec.get('recommended_policy', '?')}")
    note = rec.get('recommendation_note', '')
    # Wrap note at ~70 chars
    words = note.split()
    line = "  Note    : "
    for word in words:
        if len(line) + len(word) + 1 > 78:
            print(line)
            line = "            " + word + " "
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
    path = report_dir / f"conv_regime_{date_str}_{ts}.json"
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
        description="Convergence Regime Classification Replay v1 -- offline-only"
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
