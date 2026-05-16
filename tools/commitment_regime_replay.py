"""
Commitment Regime Replay v1 -- offline replay tool.

Measures whether directional commitment features can predict stabilization
survival better than raw stabilization/volatility signals, by constructing
and evaluating five offline commitment score candidates.

Background (Stabilization Survival Replay v1, 2026-05-15):
  Stabilized: 59 / 70 epochs
  Survived:   13 / 59 = 22.0%
  Failed resurgence: 46 / 59 = 78.0%
  BTC survival: 15.9%  |  ETH survival: 40.0%
  Top separating features (realtime-feasible):
    pre_stabilization_slope    (66.8% separation)
    bid_stability_score        (51.7%)
    bid_distance_from_0_5      (31.4%)
    pre_stabilization_volatility (33.4%)
    stabilization_bid_level    (23.1%)
  Hypothesis: market directional commitment predicts survival.

Five commitment score candidates (all realtime-feasible at stab moment):
  A  distance_only_score
     = bid_distance_from_0_5
  B  slope_distance_score
     = bid_distance_from_0_5 + abs(pre_stab_slope) * 200
  C  distance_minus_vol_score
     = bid_distance_from_0_5 - pre_stab_vol * 1.5
  D  asset_adjusted_commitment_score
     = bid_distance_from_0_5 + (0.15 if ETH else 0.0)
  E  conservative_commitment_score
     = max(0, distance + abs(slope)*200 - max(0, vol-0.05)*2.0)

Two added diagnostics:
  commitment_decay_after_stabilization
    How much does bid_distance_from_0_5 drop in the post-stab window?
    = stab_bid_distance - min(abs(yb-0.5) for post-stab bids)
    Positive = bid moved toward midpoint (commitment decayed).
    Diagnostic: uses future post-stab data, clearly labeled.

  high_commitment_false_positive_count
    Count of positions where commitment_score >= best_threshold (predicted
    SURVIVED) but actual outcome was FAILED.  Equals FP at best-F1 threshold.
    Reported per score and globally (score with lowest FP count).

No future leakage:
  Score inputs use only features available at or before stabilization_sr.
  Survival labels are used only for diagnostic evaluation (never as score inputs).
  commitment_decay_after_stabilization is explicitly labeled as diagnostic.

Verdict per score:
  candidate_guard    accuracy >= 60%, precision >= 45%, PnL uplift vs B > 0
  overfit_risk       accuracy >= 60% but recall < 30%
  weak_signal        accuracy < 55%
  needs_more_data    insufficient epochs or borderline signal

Data sources (local JSONL only -- no live API calls):
  runtime/quant_data/system_health/YYYY-MM-DD.jsonl    (zero_size_probe_v1)
  runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl  (timelines + settlement)

Usage:
  python -m tools.commitment_regime_replay --date 2026-05-15
  python -m tools.commitment_regime_replay --date 2026-05-15 --write-report
  python -m tools.commitment_regime_replay --date 2026-05-15 --asset BTC

Output:
  Console summary + optional runtime/reports/commitment_regime_YYYY-MM-DD_HHMM.json

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

# Settlement proxy thresholds
_YES_THRESHOLD    = 0.70
_NO_THRESHOLD     = 0.30
_MAX_SR_FOR_PROXY = 120.0

# Stabilization / resurgence / reversal thresholds
_STAB_VOL_THRESHOLD   = 0.02
_STAB_PERSIST_N       = 3
_CONV_VOL_WINDOW      = 5
_RESURGENCE_THRESHOLD = 0.04
_LATE_WINDOW_SR       = 90.0
_REVERSAL_THRESHOLD   = 0.10
_PRIOR_LEVEL_WINDOW   = 5
_DERISK_SR            = 60.0

# Commitment score parameters
SLOPE_SCALE                = 200.0   # abs(slope) multiplier in score formulas
VOL_PENALTY_SCALE          = 1.5     # pre_stab_vol multiplier in score C
ETH_ASSET_BONUS            = 0.15    # ETH bonus in score D
CONSERVATIVE_VOL_THRESHOLD = 0.05    # vol floor for penalty in score E
CONSERVATIVE_VOL_SCALE     = 2.0     # excess-vol penalty multiplier in score E

# Threshold sweep
N_THRESHOLD_STEPS = 20

# Verdict thresholds
MIN_STABILIZED_FOR_VERDICT    = 10
CANDIDATE_GUARD_ACCURACY_THR  = 0.60
CANDIDATE_GUARD_PRECISION_THR = 0.45
WEAK_SIGNAL_ACCURACY_THR      = 0.55

# Survival state labels
SURVIVED             = "SURVIVED"
FAILED_RESURGENCE    = "FAILED_RESURGENCE"
FAILED_LATE_REVERSAL = "FAILED_LATE_REVERSAL"
NO_STABILIZATION     = "NO_STABILIZATION"

# Score keys (canonical order)
SCORE_KEYS = [
    "distance_only_score",
    "slope_distance_score",
    "distance_minus_vol_score",
    "asset_adjusted_commitment_score",
    "conservative_commitment_score",
]

SCORE_META: dict[str, dict[str, str]] = {
    "distance_only_score": {
        "label": "A  distance_only",
        "formula": "bid_distance_from_0_5",
    },
    "slope_distance_score": {
        "label": "B  slope_distance",
        "formula": f"bid_distance_from_0_5 + abs(pre_stab_slope) × {SLOPE_SCALE:.0f}",
    },
    "distance_minus_vol_score": {
        "label": "C  distance_minus_vol",
        "formula": f"bid_distance_from_0_5 - pre_stab_vol × {VOL_PENALTY_SCALE}",
    },
    "asset_adjusted_commitment_score": {
        "label": "D  asset_adjusted",
        "formula": f"bid_distance_from_0_5 + (ETH? +{ETH_ASSET_BONUS} : 0)",
    },
    "conservative_commitment_score": {
        "label": "E  conservative",
        "formula": (
            f"max(0, distance + abs(slope)×{SLOPE_SCALE:.0f} "
            f"- max(0, vol-{CONSERVATIVE_VOL_THRESHOLD})×{CONSERVATIVE_VOL_SCALE:.0f})"
        ),
    },
}


# ---------------------------------------------------------------------------
# Shadow formula
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
    n = len(values)
    if n < 2:
        return None
    m = sum(values) / n
    return (sum((x - m) ** 2 for x in values) / (n - 1)) ** 0.5


def _rolling_vol(bids: list[float], window: int = _CONV_VOL_WINDOW) -> float:
    sample = bids[-window:]
    result = _stdev_safe(sample)
    return result if result is not None else float("inf")


# ---------------------------------------------------------------------------
# Detection helpers (identical to stabilization_survival_replay)
# ---------------------------------------------------------------------------

def _detect_stabilization(
    timeline: list[tuple[float, float]],
    vol_threshold: float = _STAB_VOL_THRESHOLD,
    persist_n: int = _STAB_PERSIST_N,
) -> dict[str, Any] | None:
    bids: list[float] = []
    streak: int = 0
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


def _compute_slope(timeline_segment: list[tuple[float, float]]) -> float | None:
    if len(timeline_segment) < 2:
        return None
    srs  = [sr for sr, _  in timeline_segment]
    bids = [yb for _,  yb in timeline_segment]
    n         = len(srs)
    sum_sr    = sum(srs)
    sum_bid   = sum(bids)
    sum_sr2   = sum(s * s for s in srs)
    sum_srbid = sum(s * b for s, b in zip(srs, bids))
    denom = n * sum_sr2 - sum_sr * sum_sr
    if abs(denom) < 1e-9:
        return None
    raw_slope = (n * sum_srbid - sum_sr * sum_bid) / denom
    return round(-raw_slope, 8)


def _extract_stab_features(
    timeline:  list[tuple[float, float]],
    stab_info: dict[str, Any],
) -> dict[str, Any]:
    stab_sr  = stab_info["stabilization_sr"]
    stab_bid = stab_info["stabilization_bid_level"]
    stab_vol = stab_info["vol_at_stabilization"]
    n_stable = stab_info["n_stable_snaps"]
    pre_and_stab = [(sr, yb) for sr, yb in timeline if sr >= stab_sr]
    if len(pre_and_stab) >= n_stable:
        pre_stab = pre_and_stab[:-n_stable]
    else:
        pre_stab = []
    pre_bids = [yb for _, yb in pre_stab]
    pre_stab_vol: float | None = None
    if len(pre_bids) >= 2:
        s = _stdev_safe(pre_bids)
        pre_stab_vol = round(s, 6) if s is not None else None
    pre_stab_slope = _compute_slope(pre_stab) if len(pre_stab) >= 2 else None
    bid_stability_score: float | None = None
    if stab_bid > 1e-9:
        bid_stability_score = round(stab_vol / stab_bid, 6)
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
# Survival classification (includes commitment_decay_after_stabilization)
# ---------------------------------------------------------------------------

def _classify_survival(
    timeline:  list[tuple[float, float]],
    stab_info: dict[str, Any],
) -> dict[str, Any]:
    """
    Classify survival and compute commitment_decay_after_stabilization.

    commitment_decay_after_stabilization is DIAGNOSTIC — uses future post-stab
    data.  Positive = bid moved toward midpoint (commitment decayed).
    """
    stab_sr   = stab_info["stabilization_sr"]
    stab_bid  = stab_info["stabilization_bid_level"]
    stab_dist = abs(stab_bid - 0.5)
    post_stab = [(sr, yb) for sr, yb in timeline if sr < stab_sr]

    resurgence = _detect_vol_resurgence(timeline, stab_info)
    has_resurgence = resurgence is not None
    resurgence_sr  = resurgence["resurgence_sr"] if resurgence else None

    reversal = _detect_late_reversal(timeline)
    has_reversal = reversal is not None
    reversal_sr  = reversal["reversal_sr"] if reversal else None

    if has_resurgence:
        survival   = FAILED_RESURGENCE
        failure_sr = resurgence_sr
    elif has_reversal:
        survival   = FAILED_LATE_REVERSAL
        failure_sr = reversal_sr
    else:
        survival   = SURVIVED
        failure_sr = None

    # Stabilization lifetime (diagnostic)
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

    # commitment_decay_after_stabilization (diagnostic: uses post-stab bids)
    if post_stab:
        min_post_dist   = min(abs(yb - 0.5) for _, yb in post_stab)
        commitment_decay = round(stab_dist - min_post_dist, 6)
    else:
        commitment_decay = None

    return {
        "survival":                              survival,
        "has_post_stab_resurgence":              has_resurgence,
        "resurgence_sr":                         resurgence_sr,
        "has_late_reversal":                     has_reversal,
        "reversal_sr":                           reversal_sr,
        "post_stab_snapshot_count":              len(post_stab),
        "stabilization_lifetime_seconds":        lifetime,
        "commitment_decay_after_stabilization":  commitment_decay,  # diagnostic
    }


# ---------------------------------------------------------------------------
# Commitment score computation (realtime-feasible at stabilization moment)
# ---------------------------------------------------------------------------

def _compute_commitment_scores(p: dict[str, Any]) -> dict[str, float | None]:
    """
    Compute 5 commitment score candidates from realtime-feasible predictor features.
    All inputs use only data available at or before stabilization_sr.
    Survival label is NOT used.  Returns None for all scores if no stabilization.
    """
    if not p.get("stabilization_found"):
        return {k: None for k in SCORE_KEYS}

    dist  = p.get("bid_distance_from_0_5")
    if dist is None:
        return {k: None for k in SCORE_KEYS}

    slope = p.get("pre_stabilization_slope") or 0.0   # None → 0.0
    vol   = p.get("pre_stabilization_volatility") or 0.0
    asset = p.get("asset", "BTC")

    # A: distance only
    score_a = dist

    # B: slope + distance
    score_b = dist + abs(slope) * SLOPE_SCALE

    # C: distance minus vol
    score_c = dist - vol * VOL_PENALTY_SCALE

    # D: asset-adjusted
    score_d = dist + (ETH_ASSET_BONUS if asset == "ETH" else 0.0)

    # E: conservative
    slope_contrib = abs(slope) * SLOPE_SCALE
    excess_vol    = max(0.0, vol - CONSERVATIVE_VOL_THRESHOLD) * CONSERVATIVE_VOL_SCALE
    score_e       = max(0.0, dist + slope_contrib - excess_vol)

    return {
        "distance_only_score":             round(score_a, 6),
        "slope_distance_score":            round(score_b, 6),
        "distance_minus_vol_score":        round(score_c, 6),
        "asset_adjusted_commitment_score": round(score_d, 6),
        "conservative_commitment_score":   round(score_e, 6),
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
    Classify stabilization survival and compute commitment scores for each entry.
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
    records: list[dict[str, Any]]  = []
    prev_epoch_ts = None

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
        settlement_price: float | None = None
        settlement_label               = "NO_SNAPSHOT"
        unresolved                     = True

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

        stab_info  = _detect_stabilization(timeline)
        stab_found = stab_info is not None

        if stab_found:
            survival_data = _classify_survival(timeline, stab_info)
            feat_data     = _extract_stab_features(timeline, stab_info)
        else:
            survival_data = {
                "survival":                             NO_STABILIZATION,
                "has_post_stab_resurgence":             False,
                "resurgence_sr":                        None,
                "has_late_reversal":                    False,
                "reversal_sr":                          None,
                "post_stab_snapshot_count":             0,
                "stabilization_lifetime_seconds":       None,
                "commitment_decay_after_stabilization": None,
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

        tokens = shadow["c_size"] / max(entry_price, 1e-9)
        pnl_a  = (
            round((settlement_price - entry_price) * tokens, 8)
            if settlement_price is not None else None
        )
        pnl_b  = _policy_b_pnl(timeline, entry_price, shadow["c_size"], settlement_price)

        rec = {
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
        }

        # Compute commitment scores (realtime-feasible; no survival label used)
        rec.update(_compute_commitment_scores(rec))
        records.append(rec)

    return records


# ---------------------------------------------------------------------------
# Threshold sweep and guard simulation
# ---------------------------------------------------------------------------

def _threshold_sweep(
    positions: list[dict[str, Any]],
    score_key: str,
    n_steps:   int = N_THRESHOLD_STEPS,
) -> list[dict[str, Any]]:
    """
    Sweep thresholds from min to max of score_key for stabilized positions.
    At each threshold: predict SURVIVED if score >= threshold.
    """
    valid = [
        (p[score_key], p.get("survival"))
        for p in positions
        if p.get(score_key) is not None and p.get("stabilization_found")
    ]
    if len(valid) < 2:
        return []
    scores = [s for s, _ in valid]
    lo, hi = min(scores), max(scores)
    if hi - lo < 1e-9:
        return []
    step = (hi - lo) / n_steps
    rows: list[dict[str, Any]] = []
    for i in range(n_steps + 1):
        thr = round(lo + i * step, 6)
        tp = sum(1 for s, sv in valid if s >= thr and sv == SURVIVED)
        fp = sum(1 for s, sv in valid if s >= thr and sv != SURVIVED)
        fn = sum(1 for s, sv in valid if s <  thr and sv == SURVIVED)
        tn = sum(1 for s, sv in valid if s <  thr and sv != SURVIVED)
        total = tp + fp + fn + tn
        acc  = (tp + tn) / total if total > 0 else 0.0
        prec = tp / (tp + fp)   if (tp + fp) > 0 else 0.0
        rec  = tp / (tp + fn)   if (tp + fn) > 0 else 0.0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        fpr  = fp / (fp + tn)   if (fp + tn) > 0 else 0.0
        fnr  = fn / (fn + tp)   if (fn + tp) > 0 else 0.0
        rows.append({
            "threshold":           thr,
            "tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "accuracy":            round(acc,  4),
            "precision":           round(prec, 4),
            "recall":              round(rec,  4),
            "f1":                  round(f1,   4),
            "false_positive_rate": round(fpr,  4),
            "false_negative_rate": round(fnr,  4),
        })
    return rows


def _best_threshold_row(sweep: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Select threshold row with highest F1; break ties by accuracy."""
    if not sweep:
        return None
    return max(sweep, key=lambda r: (r["f1"], r["accuracy"]))


def _simulate_guard_pnl(
    positions:  list[dict[str, Any]],
    score_key:  str,
    threshold:  float,
) -> float:
    """
    Guarded PnL: HOLD (Policy A) when score >= threshold; EXIT (Policy B) otherwise.
    Non-stabilized or None-score positions always use Policy B fallback.
    """
    total = 0.0
    for p in positions:
        score = p.get(score_key)
        if score is not None and score >= threshold:
            # Predict SURVIVED → hold to settlement
            pnl = p.get("pnl_policy_a") if p.get("pnl_policy_a") is not None else p.get("pnl_policy_b")
        else:
            # Predict FAILED or no stab → derisk at SR<60
            pnl = p.get("pnl_policy_b") if p.get("pnl_policy_b") is not None else p.get("pnl_policy_a")
        if pnl is not None:
            total += pnl
    return round(total, 6)


# ---------------------------------------------------------------------------
# Per-score reporting helpers
# ---------------------------------------------------------------------------

def _asset_score_stats(
    positions: list[dict[str, Any]],
    score_key: str,
) -> dict[str, Any] | None:
    valid = [p for p in positions if p.get(score_key) is not None]
    if not valid:
        return None
    scores      = [p[score_key] for p in valid]
    surv_scores = [p[score_key] for p in valid if p.get("survival") == SURVIVED]
    fail_scores = [p[score_key] for p in valid if p.get("survival") in (FAILED_RESURGENCE, FAILED_LATE_REVERSAL)]
    return {
        "count":         len(valid),
        "mean_score":    round(mean(scores),      4),
        "mean_survived": round(mean(surv_scores), 4) if surv_scores else None,
        "mean_failed":   round(mean(fail_scores), 4) if fail_scores else None,
    }


def _score_verdict(
    best_row:    dict[str, Any],
    uplift_vs_b: float,
    n_stab:      int,
) -> tuple[str, str]:
    acc  = best_row["accuracy"]
    prec = best_row["precision"]
    rec  = best_row["recall"]
    if n_stab < MIN_STABILIZED_FOR_VERDICT:
        return "needs_more_data", f"Only {n_stab} stabilized epochs (need >= {MIN_STABILIZED_FOR_VERDICT})."
    if acc >= CANDIDATE_GUARD_ACCURACY_THR and prec >= CANDIDATE_GUARD_PRECISION_THR and uplift_vs_b > 0:
        return "candidate_guard", (
            f"Accuracy={acc:.1%}, precision={prec:.1%}, "
            f"PnL uplift vs fixed-derisk=${uplift_vs_b:+.2f}. "
            "Validate over multiple sessions before runtime consideration."
        )
    if acc >= CANDIDATE_GUARD_ACCURACY_THR and rec < 0.30:
        return "overfit_risk", (
            f"Accuracy={acc:.1%} but recall={rec:.1%} — misses most SURVIVED epochs."
        )
    if acc < WEAK_SIGNAL_ACCURACY_THR:
        return "weak_signal", f"Best accuracy={acc:.1%} below {WEAK_SIGNAL_ACCURACY_THR:.0%} threshold."
    return "needs_more_data", (
        f"Accuracy={acc:.1%}, precision={prec:.1%}. "
        "Borderline signal; multi-session validation required."
    )


def _score_report(
    positions:   list[dict[str, Any]],
    score_key:   str,
    baseline_a:  float,
    baseline_b:  float,
) -> dict[str, Any]:
    meta      = SCORE_META[score_key]
    sweep     = _threshold_sweep(positions, score_key)
    n_stab    = sum(1 for p in positions if p.get("stabilization_found"))

    if not sweep:
        return {
            "score_key":   score_key,
            "score_label": meta["label"],
            "formula":     meta["formula"],
            "verdict":     "needs_more_data",
            "error":       "no_valid_score_range",
        }

    best_row    = _best_threshold_row(sweep)
    best_acc_row = max(sweep, key=lambda r: (r["accuracy"], r["f1"]))

    thr          = best_row["threshold"]
    pnl_guarded  = _simulate_guard_pnl(positions, score_key, thr)
    uplift_b     = round(pnl_guarded - baseline_b, 6)
    uplift_a     = round(pnl_guarded - baseline_a, 6)

    btc = [p for p in positions if p.get("asset") == "BTC" and p.get("stabilization_found")]
    eth = [p for p in positions if p.get("asset") == "ETH" and p.get("stabilization_found")]

    verdict, note = _score_verdict(best_row, uplift_b, n_stab)

    # Threshold sensitivity: top 8 rows by F1
    sensitivity = sorted(sweep, key=lambda r: (-r["f1"], -r["accuracy"]))[:8]

    return {
        "score_key":   score_key,
        "score_label": meta["label"],
        "formula":     meta["formula"],
        "best_threshold_by_f1":       thr,
        "best_threshold_by_accuracy": best_acc_row["threshold"],
        # Confusion metrics at best-F1 threshold
        **{k: best_row[k] for k in [
            "accuracy", "precision", "recall", "f1",
            "false_positive_rate", "false_negative_rate",
            "tp", "tn", "fp", "fn",
        ]},
        # Explicit FP count at best threshold (added diagnostic)
        "high_commitment_false_positive_count": best_row["fp"],
        # PnL
        "pnl_guarded":                pnl_guarded,
        "pnl_uplift_vs_fixed_derisk": uplift_b,
        "pnl_uplift_vs_always_hold":  uplift_a,
        # Asset stats
        "btc_stats": _asset_score_stats(btc, score_key),
        "eth_stats": _asset_score_stats(eth, score_key),
        # Threshold sensitivity
        "threshold_sensitivity": sensitivity,
        # Verdict
        "verdict":      verdict,
        "verdict_note": note,
    }


# ---------------------------------------------------------------------------
# Feature importance ranking (realtime-feasible features only)
# ---------------------------------------------------------------------------

def _feature_importance_ranking(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Rank realtime-feasible features by separation power between SURVIVED and
    FAILED_RESURGENCE.  commitment_decay_after_stabilization (diagnostic) is
    excluded from this ranking to avoid mixing future-data features.
    """
    survived = [p for p in positions if p.get("survival") == SURVIVED]
    failed   = [p for p in positions if p.get("survival") == FAILED_RESURGENCE]

    feat_keys = [
        "bid_distance_from_0_5",
        "pre_stabilization_slope",
        "pre_stabilization_volatility",
        "stabilization_bid_level",
        "bid_stability_score",
        "stable_streak_length",
        "stabilization_sr",
        "shadow_pct_bankroll",
        "entry_price",
    ]

    rankings: list[dict[str, Any]] = []
    for feat in feat_keys:
        s_vals = [p[feat] for p in survived if p.get(feat) is not None and p.get(feat) != float("inf")]
        f_vals = [p[feat] for p in failed   if p.get(feat) is not None and p.get(feat) != float("inf")]
        if not s_vals or not f_vals:
            continue
        s_mean = mean(s_vals)
        f_mean = mean(f_vals)
        denom  = max(abs(s_mean), abs(f_mean), 1e-9)
        sep    = abs(s_mean - f_mean) / denom * 100
        rankings.append({
            "feature":        feat,
            "survived_mean":  round(s_mean, 6),
            "failed_mean":    round(f_mean, 6),
            "separation_pct": round(sep, 1),
            "direction":      "SURVIVED_higher" if s_mean > f_mean else "FAILED_higher",
        })

    return sorted(rankings, key=lambda r: -r["separation_pct"])


# ---------------------------------------------------------------------------
# Commitment decay diagnostic aggregate
# ---------------------------------------------------------------------------

def _commitment_decay_summary(positions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Aggregate commitment_decay_after_stabilization by survival outcome.
    Diagnostic only: uses post-stab data.
    """
    def _decay_stats(group: list[dict]) -> dict[str, Any]:
        vals = [p["commitment_decay_after_stabilization"] for p in group
                if p.get("commitment_decay_after_stabilization") is not None]
        return _stats(vals)

    survived  = [p for p in positions if p.get("survival") == SURVIVED]
    failed_r  = [p for p in positions if p.get("survival") == FAILED_RESURGENCE]
    all_stab  = [p for p in positions if p.get("stabilization_found")]

    return {
        "all_stabilized": _decay_stats(all_stab),
        "survived":       _decay_stats(survived),
        "failed_resurgence": _decay_stats(failed_r),
        "diagnostic_note": (
            "commitment_decay_after_stabilization uses future post-stab data. "
            "Values are diagnostic truth only, not realtime-feasible features."
        ),
    }


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

    # Baselines
    baseline_a = sum(p["pnl_policy_a"] for p in positions if p.get("pnl_policy_a") is not None)
    baseline_b = sum(p["pnl_policy_b"] for p in positions if p.get("pnl_policy_b") is not None)
    n_stab     = sum(1 for p in positions if p.get("stabilization_found"))
    n_surv     = sum(1 for p in positions if p.get("survival") == SURVIVED)

    # Per-score reports
    score_reports: dict[str, Any] = {}
    for key in SCORE_KEYS:
        score_reports[key] = _score_report(positions, key, baseline_a, baseline_b)

    valid_rpts = [r for r in score_reports.values() if "accuracy" in r]

    # Best by accuracy and PnL
    best_acc_key = (
        max(valid_rpts, key=lambda r: r.get("accuracy", 0))["score_key"]
        if valid_rpts else None
    )
    best_pnl_key = (
        max(valid_rpts, key=lambda r: r.get("pnl_uplift_vs_fixed_derisk", -999))["score_key"]
        if valid_rpts else None
    )

    # Feature importance (realtime-feasible only)
    feat_rank = _feature_importance_ranking(positions)

    # Commitment decay diagnostic
    decay_summary = _commitment_decay_summary(positions)

    # Global high_commitment_false_positive_count (score with lowest FP)
    fp_by_score = {
        key: r.get("high_commitment_false_positive_count", 999)
        for key, r in score_reports.items()
        if "high_commitment_false_positive_count" in r
    }
    lowest_fp_score = min(fp_by_score, key=fp_by_score.get) if fp_by_score else None

    # Recommended candidate
    candidates = [r for r in valid_rpts if r.get("verdict") == "candidate_guard"]
    if candidates:
        rec_candidate = max(candidates, key=lambda r: r.get("pnl_uplift_vs_fixed_derisk", -999))
        multi_session_ready = True
    else:
        rec_candidate = max(valid_rpts, key=lambda r: r.get("pnl_uplift_vs_fixed_derisk", -999)) if valid_rpts else None
        multi_session_ready = False

    fixed_sr60_still_best = all(
        r.get("pnl_uplift_vs_fixed_derisk", -999) <= 0
        for r in valid_rpts
    )

    if multi_session_ready:
        next_step = (
            "Validate the recommended commitment score candidate over >= 5 sessions. "
            "Track whether separating features remain stable across dates before "
            "designing a runtime survival guard."
        )
    elif not fixed_sr60_still_best:
        next_step = (
            "Marginal PnL improvement found for one or more scores. "
            "Collect >= 3 more sessions before designing a runtime guard. "
            "Do NOT promote to runtime without a separately scoped Phase 3."
        )
    else:
        next_step = (
            "Fixed SR<60 derisk remains best. Commitment scores do not improve "
            "PnL over the current policy. Continue collecting sessions and "
            "re-run over >= 5 dates before revisiting."
        )

    return {
        "event_count":                        len(events),
        "position_count":                     len(positions),
        "stabilized_count":                   n_stab,
        "survived_count":                     n_surv,
        "baseline_pnl_policy_a":              round(baseline_a, 4),
        "baseline_pnl_policy_b":              round(baseline_b, 4),
        "score_reports":                      score_reports,
        "best_score_by_accuracy":             best_acc_key,
        "best_score_by_pnl":                  best_pnl_key,
        "lowest_false_positive_score":        lowest_fp_score,
        "feature_importance_ranking":         feat_rank,
        "commitment_decay_diagnostic":        decay_summary,
        "recommended_candidate_guard":        rec_candidate["score_key"] if rec_candidate else None,
        "fixed_sr60_remains_best":            fixed_sr60_still_best,
        "multi_session_validation_ready":     multi_session_ready,
        "next_research_step":                 next_step,
        "simulation_rules": [
            "Max 1 position per asset per epoch (no reloads).",
            "Commitment scores use only features at or before stabilization_sr.",
            "Survival labels used only for diagnostic evaluation; never as score inputs.",
            f"Score A: bid_distance_from_0_5.",
            f"Score B: distance + abs(slope)×{SLOPE_SCALE:.0f}.",
            f"Score C: distance - pre_stab_vol×{VOL_PENALTY_SCALE}.",
            f"Score D: distance + ETH_bonus({ETH_ASSET_BONUS}).",
            f"Score E: max(0, distance + abs(slope)×{SLOPE_SCALE:.0f} - max(0,vol-{CONSERVATIVE_VOL_THRESHOLD})×{CONSERVATIVE_VOL_SCALE:.0f}).",
            "Guard simulation: score >= threshold → HOLD (Policy A); else EXIT (Policy B).",
            "Non-stabilized or None-score positions always fall back to Policy B in guard.",
            "commitment_decay_after_stabilization is DIAGNOSTIC: uses future post-stab bids.",
            "high_commitment_false_positive_count = FP count at best-F1 threshold per score.",
            "Settlement inferred from market_snapshots yes_bid near close (proxy, not confirmed).",
        ],
        "guardrail": (
            "offline-only; does not change strategy, risk, execution, "
            "position_sizing.py, order_manager.py, paper/live separation, "
            "or any runtime behavior; commitment scores are research candidates only "
            "and must not be promoted to runtime without a separately scoped Phase 3"
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
        print(f"  Commitment Regime Replay v1  |  {date_str}")
        print(f"{SEP}")
        print(f"  ERROR: {result['error']}")
        print(f"{SEP}\n")
        return

    print(f"\n{SEP}")
    print(f"  Commitment Regime Replay v1  |  {date_str}")
    print(f"{SEP}")
    print(f"  Positions   : {result['position_count']}")
    print(f"  Stabilized  : {result['stabilized_count']}")
    print(f"  Survived    : {result['survived_count']}")
    print(f"  Baseline A  : ${result['baseline_pnl_policy_a']:.2f}")
    print(f"  Baseline B  : ${result['baseline_pnl_policy_b']:.2f}")

    # Commitment decay diagnostic
    cd = result.get("commitment_decay_diagnostic") or {}
    surv_d  = (cd.get("survived") or {}).get("mean")
    fail_d  = (cd.get("failed_resurgence") or {}).get("mean")
    print(f"\n  [Commitment Decay Diagnostic -- post-stab data]")
    print(f"  mean decay SURVIVED        : {surv_d:.4f}" if surv_d is not None else "  mean decay SURVIVED        : N/A")
    print(f"  mean decay FAILED_RESURGENCE: {fail_d:.4f}" if fail_d is not None else "  mean decay FAILED_RESURGENCE: N/A")

    # Score comparison table
    print(f"\n{SEP2}")
    print(f"  COMMITMENT SCORE COMPARISON  (threshold = best F1)")
    print(f"{SEP2}")
    print(f"  {'Score':<28}  {'Acc':>6}  {'Prec':>6}  {'Rec':>6}  {'F1':>6}  "
          f"{'FPcnt':>6}  {'GuardPnL':>9}  {'vs B':>7}  Verdict")
    print(f"  {'-'*28}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*6}  "
          f"{'-'*6}  {'-'*9}  {'-'*7}  {'-'*20}")

    srs = result.get("score_reports") or {}
    for key in SCORE_KEYS:
        r = srs.get(key) or {}
        if "error" in r:
            print(f"  {r.get('score_label', key):<28}  (no valid score range)")
            continue
        lbl   = r.get("score_label", key)[:28]
        acc   = r.get("accuracy", 0)
        prec  = r.get("precision", 0)
        rec   = r.get("recall", 0)
        f1    = r.get("f1", 0)
        fp_c  = r.get("high_commitment_false_positive_count", 0)
        gpnl  = r.get("pnl_guarded", 0)
        uplft = r.get("pnl_uplift_vs_fixed_derisk", 0)
        verd  = r.get("verdict", "?")[:20]
        print(f"  {lbl:<28}  {acc:>5.1%}  {prec:>5.1%}  {rec:>5.1%}  {f1:>5.3f}  "
              f"{fp_c:>6}  ${gpnl:>8.2f}  ${uplft:>+6.2f}  {verd}")

    # Best / lowest FP
    print(f"\n  Best by accuracy : {result.get('best_score_by_accuracy', '?')}")
    print(f"  Best by PnL      : {result.get('best_score_by_pnl', '?')}")
    print(f"  Lowest FP score  : {result.get('lowest_false_positive_score', '?')}")

    # Feature importance
    print(f"\n{SEP2}")
    print(f"  FEATURE IMPORTANCE  (realtime-feasible; SURVIVED vs FAILED_RESURGENCE)")
    print(f"{SEP2}")
    print(f"  {'Feature':<36}  {'SURV mean':>10}  {'FAIL mean':>10}  {'Sep%':>6}  Direction")
    for row in (result.get("feature_importance_ranking") or [])[:9]:
        print(f"  {row['feature']:<36}  {row['survived_mean']:>10.4f}  "
              f"{row['failed_mean']:>10.4f}  {row['separation_pct']:>5.1f}%  {row['direction']}")

    # Threshold sensitivity for best score
    best_k = result.get("best_score_by_pnl") or (SCORE_KEYS[0] if SCORE_KEYS else None)
    if best_k and best_k in srs:
        br = srs[best_k]
        sens = br.get("threshold_sensitivity") or []
        if sens:
            print(f"\n{SEP2}")
            print(f"  THRESHOLD SENSITIVITY  ({br.get('score_label','?')})")
            print(f"{SEP2}")
            print(f"  {'Thr':>8}  {'Acc':>6}  {'Prec':>6}  {'Rec':>6}  {'F1':>6}  {'FPR':>6}  FP")
            for row in sens[:6]:
                print(f"  {row['threshold']:>8.4f}  {row['accuracy']:>5.1%}  "
                      f"{row['precision']:>5.1%}  {row['recall']:>5.1%}  "
                      f"{row['f1']:>5.3f}  {row['false_positive_rate']:>5.1%}  {row['fp']}")

    # Verdict
    print(f"\n{SEP2}")
    print(f"  VERDICT")
    print(f"{SEP2}")
    print(f"  fixed_SR60_remains_best         : {result.get('fixed_sr60_remains_best')}")
    print(f"  multi_session_validation_ready  : {result.get('multi_session_validation_ready')}")
    print(f"  recommended_candidate_guard     : {result.get('recommended_candidate_guard', 'none')}")
    note = result.get("next_research_step", "")
    words = note.split()
    line  = "  Next step : "
    for word in words:
        if len(line) + len(word) + 1 > 78:
            print(line)
            line = "              " + word + " "
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
    path = report_dir / f"commitment_regime_{date_str}_{ts}.json"
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
        description="Commitment Regime Replay v1 -- offline-only"
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
        args.date, quant_data_dir=qd,
        run_id=args.run_id, asset_filter=args.asset,
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
