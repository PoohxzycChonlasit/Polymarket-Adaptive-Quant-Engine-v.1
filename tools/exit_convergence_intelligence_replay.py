"""
Exit Convergence Intelligence Replay v1 -- offline replay tool.

Studies whether prediction-market YES books exhibit measurable convergence
toward final settlement before expiry, and whether dynamic convergence-aware
exits outperform the fixed SR<60 derisking from Lifecycle Policy D.

Research questions:
  1. At what SR does yes_bid statistically converge near final settlement?
  2. Is convergence timing stable across BTC vs ETH?
  3. Is there a detectable "uncertainty collapse" window?
  4. Can dynamic convergence exits improve Policy D (fixed SR<60 derisk)?
  5. Does convergence reduce tail drawdown?
  6. Are late-window reversals common after convergence?

Background:
  Lifecycle Profit Management Replay v1 (2026-05-15) established:
    Policy D (derisk-before-close, SR<60):  best policy
    proxy pnl = $67.67,  uplift = +$5.22 vs baseline
    drawdown = $1.11,  exposure = 5.01%
  Policy E (decay heuristic) produced 21 false triggers and is unreliable.
  This replay studies convergence-aware exits as an alternative to static SR<60.

Five policies simulated:
  A  baseline_hold_to_settlement
     Hold 100% to settlement.

  B  fixed_derisk_sr60
     Full close at first snapshot with SR < 60s.
     Mirrors Lifecycle Profit Management Replay Policy D (current best).

  C  dynamic_convergence_exit_95
     Full close when yes_bid is within 5 percentage points of settlement proxy
     for >= 3 consecutive post-entry snapshots.
     RESEARCH ASSUMPTION: uses settlement proxy (near-close yes_bid) as target.
     This constitutes future knowledge and is labeled research_proxy_used=True.

  D  dynamic_convergence_exit_volatility
     Full close when rolling 5-snapshot vol collapses below 0.02 for >=3
     consecutive snapshots AND SR < 150s.
     Purely backward-looking; no future leakage.

  E  hybrid_convergence_derisk
     Full close when SR < 60s AND (rolling_vol < 0.025 OR yes_bid within 5pp
     of settlement proxy).
     RESEARCH ASSUMPTION: uses settlement proxy for proximity check.
     Labels research_proxy_used=True.

Inventory continuity constraints (same as prior replay tools):
  max 1 position per asset per epoch
  no reloads

No future leakage:
  All decisions use only snapshots with SR < entry_SR, processed
  chronologically (SR descending = earlier-in-window first).
  Settlement proxy is a known constant for each epoch used in
  Policies C and E only; explicitly labeled as future knowledge.

Convergence signals (all backward-looking except settlement proxy):
  rolling_vol        std of last 5 yes_bid readings
  bid_stabilization  coefficient of variation of last 5 yes_bid readings
  persistence_count  consecutive readings within 5pp band of target

Additional metrics (beyond standard per-policy report):
  convergence_false_positive_cost_usd
    Sum of max(0, premature_reduce_regret) for positions flagged as
    false_convergence_exit.  Measures the USD cost of wrong convergence exits.

  late_uncertainty_expansion_count
    Count of simulated positions where rolling vol in the late window
    (SR < 90s) was HIGHER than vol in the early window (SR >= 90s).
    Counter-evidence for the convergence hypothesis.

Data sources (local JSONL only -- no live API calls):
  runtime/quant_data/system_health/YYYY-MM-DD.jsonl    (zero_size_probe_v1)
  runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl  (settlement proxy + timeline)

Settlement inference (identical to prior replay tools):
  yes_bid >= 0.70  ->  YES  (settlement_price=1.0, HIGH)
  yes_bid <= 0.30  ->  NO   (settlement_price=0.0, HIGH)
  otherwise        ->  AMBIGUOUS (excluded from realized PnL)

Usage:
  python -m tools.exit_convergence_intelligence_replay --date 2026-05-15
  python -m tools.exit_convergence_intelligence_replay --date 2026-05-15 --write-report
  python -m tools.exit_convergence_intelligence_replay --date 2026-05-15 --asset BTC
  python -m tools.exit_convergence_intelligence_replay --date 2026-05-15 --run-id <id>

Output:
  Console summary + optional runtime/reports/exit_convergence_YYYY-MM-DD_HHMM.json

Per-policy report (13 core outputs + convergence diagnostics):
   1.  realized_proxy_pnl
   2.  pnl_uplift_vs_baseline (vs A) + pnl_uplift_vs_fixed_derisk_sr60 (vs B)
   3.  max_drawdown
   4.  convergence_exit_count
   5.  avg_exit_sr
   6.  convergence_stability_score
   7.  false_convergence_exits
   8.  late_reversal_count
   9.  btc + eth convergence behavior
  10.  volatility_at_exit_mean / early_epoch_vol_mean
  11.  clustered_loss_periods
  12.  max_exposure_pct
  13.  verdict (safe_candidate | convergence_unstable | no_material_improvement
               | needs_more_replay)

Additional diagnostics:
  convergence_timing_distribution
  average_snapshots_to_convergence
  reversal_after_convergence_rate
  eth_vs_btc_convergence_gap
  uncertainty_collapse_window_estimate
  convergence_false_positive_cost_usd
  late_uncertainty_expansion_count

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

# Shadow formula constants (read-only reference; not imported from runtime)
_GOOD_EV    = 0.08
_CONF_FLOOR = 0.54
_CONF_SPAN  = 0.21
_EV_Q_FLOOR = 0.5

# Settlement proxy thresholds (identical to prior replay tools)
_YES_THRESHOLD    = 0.70
_NO_THRESHOLD     = 0.30
_MAX_SR_FOR_PROXY = 120.0

# Safety verdict thresholds
_UNSAFE_DRAWDOWN_PCT       = 10.0
_NO_IMPROVEMENT_USD        = 2.0
_NEEDS_MORE_ENTRIES        = 10
_NEEDS_MORE_WIN_RATE       = 40.0
_CONVERGENCE_UNSTABLE_RATE = 0.30   # >30% false convergence exits → unstable

# Convergence parameters
_CONV_VOL_WINDOW         = 5      # rolling vol window (snapshots)
_CONV_VOL_THRESHOLD      = 0.02   # rolling std below this → vol collapsed
_CONV_STAB_THRESHOLD     = 0.04   # bid CV below this → bid stable
_CONV_PERSIST_N          = 3      # consecutive readings required to confirm convergence
_CONV_PROXY_BAND         = 0.05   # absolute: within 5 pct-points of settlement proxy
_CONV_MAX_SR             = 150.0  # only check vol-collapse convergence when SR < this
_CONV_REVERSAL_THRESHOLD = 0.10   # post-exit abs bid movement > this → late reversal
_LATE_VOL_SR_BOUNDARY    = 90.0   # late window = SR < 90s; early window = SR >= 90s

# Policy B: fixed derisk SR threshold (mirrors Lifecycle PM Policy D)
_DERISK_SR = 60.0

POLICIES: list[dict[str, Any]] = [
    {
        "name":  "A_baseline_hold_to_settlement",
        "label": "A  baseline (hold-to-settlement)",
    },
    {
        "name":      "B_fixed_derisk_sr60",
        "label":     "B  fixed-derisk-SR<60 (Lifecycle Policy D best)",
        "derisk_sr": _DERISK_SR,
    },
    {
        "name":           "C_dynamic_convergence_exit_95",
        "label":          "C  convergence-exit-95 (proxy proximity, research)",
        "proxy_band":     _CONV_PROXY_BAND,
        "persist_n":      _CONV_PERSIST_N,
        "research_proxy": True,
    },
    {
        "name":          "D_dynamic_convergence_exit_volatility",
        "label":         "D  convergence-exit-vol (vol collapse)",
        "vol_threshold": _CONV_VOL_THRESHOLD,
        "persist_n":     _CONV_PERSIST_N,
        "max_sr":        _CONV_MAX_SR,
    },
    {
        "name":           "E_hybrid_convergence_derisk",
        "label":          "E  hybrid-convergence-derisk (SR guard + convergence)",
        "sr_guard":       _DERISK_SR,
        "vol_threshold":  0.025,
        "proxy_band":     _CONV_PROXY_BAND,
        "research_proxy": True,
    },
]


# ---------------------------------------------------------------------------
# Shadow formula (identical to other replay tools; not imported from runtime)
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
# Data loading (identical to lifecycle_profit_management_replay)
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
# PnL / drawdown / clustered losses / stats (identical to prior replay tools)
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


def _clustered_losses(sorted_records: list[dict[str, Any]]) -> dict[str, Any]:
    max_run = cur = n_clusters = total_eps = 0
    for rec in sorted_records:
        pnl = rec.get("total_pnl")
        if pnl is not None and pnl < 0:
            cur += 1
            if cur > max_run:
                max_run = cur
        else:
            if cur >= 2:
                n_clusters += 1
                total_eps  += cur
            cur = 0
    if cur >= 2:
        n_clusters += 1
        total_eps  += cur
    return {
        "max_consecutive_losses":    max_run,
        "loss_cluster_count":        n_clusters,
        "total_loss_cluster_epochs": total_eps,
    }


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
# Convergence detectors (pure functions; no future leakage; no runtime imports)
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


def _bid_stabilization(bids: list[float], window: int = _CONV_VOL_WINDOW) -> float:
    """Coefficient of variation (std/mean) of last `window` yes_bids. Lower = more stable."""
    sample = bids[-window:]
    std = _stdev_safe(sample)
    if std is None:
        return float("inf")
    m = sum(sample) / len(sample)
    if m < 1e-9:
        return float("inf")
    return std / m


def _persistence_count(bids: list[float], target: float, band: float = _CONV_PROXY_BAND) -> int:
    """
    Count of consecutive readings from the END of bids within `band` (absolute) of target.
    Returns 0 if bids is empty.
    """
    count = 0
    for bid in reversed(bids):
        if abs(bid - target) <= band:
            count += 1
        else:
            break
    return count


# ---------------------------------------------------------------------------
# Per-position convergence lifecycle simulation
# ---------------------------------------------------------------------------

def _simulate_convergence(
    entry_price:          float,
    shadow_size:          float,
    entry_sr:             float,
    all_snaps:            list[tuple[float, float]],  # (sr, yes_bid) full epoch
    settlement_price:     float | None,
    settlement_proxy_bid: float | None,               # near-close yes_bid; research only
    policy:               dict[str, Any],
) -> dict[str, Any]:
    """
    Simulate one convergence policy for a single position.

    No future leakage: only snapshots with SR < entry_sr are processed.
    Processed SR-descending (= chronological; earlier SR = later in time).

    settlement_proxy_bid is the near-close yes_bid used as convergence target in
    Policies C and E.  This constitutes future knowledge; its use is labeled
    research_proxy_used=True in the returned dict and in the tool guardrail.
    """
    # Filter to post-entry snapshots only
    timeline = sorted(
        [(sr, yb) for sr, yb in all_snaps if sr < entry_sr],
        key=lambda s: -s[0],   # SR descending = chronological
    )

    tokens_total = shadow_size / max(entry_price, 1e-9)

    convergence_exit = False
    exit_sr:  float | None = None
    exit_bid: float | None = None

    policy_name = policy["name"]
    bids_so_far: list[float] = []

    # ------------------------------------------------------------------
    # Policy A: baseline — hold 100% to settlement
    # ------------------------------------------------------------------
    if policy_name == "A_baseline_hold_to_settlement":
        for _, yb in timeline:
            bids_so_far.append(yb)

    # ------------------------------------------------------------------
    # Policy B: full close at first snapshot with SR < 60s
    # ------------------------------------------------------------------
    elif policy_name == "B_fixed_derisk_sr60":
        sr_guard = float(policy["derisk_sr"])
        for sr, yb in timeline:
            bids_so_far.append(yb)
            if sr < sr_guard:
                convergence_exit = True
                exit_sr  = sr
                exit_bid = yb
                break

    # ------------------------------------------------------------------
    # Policy C: convergence to settlement proxy (research assumption)
    # Exit when yes_bid within CONV_PROXY_BAND of settlement proxy
    # for >= persist_n consecutive snapshots.
    # ------------------------------------------------------------------
    elif policy_name == "C_dynamic_convergence_exit_95":
        proxy_band = float(policy["proxy_band"])
        persist_n  = int(policy["persist_n"])
        for sr, yb in timeline:
            bids_so_far.append(yb)
            if settlement_proxy_bid is None:
                continue
            if _persistence_count(bids_so_far, settlement_proxy_bid, proxy_band) >= persist_n:
                convergence_exit = True
                exit_sr  = sr
                exit_bid = yb
                break

    # ------------------------------------------------------------------
    # Policy D: vol-collapse convergence — purely backward-looking
    # Exit when rolling vol < vol_threshold for >= persist_n consecutive
    # snapshots AND SR < max_sr.
    # ------------------------------------------------------------------
    elif policy_name == "D_dynamic_convergence_exit_volatility":
        vol_thr   = float(policy["vol_threshold"])
        persist_n = int(policy["persist_n"])
        max_sr    = float(policy["max_sr"])
        collapsed_streak = 0
        for sr, yb in timeline:
            bids_so_far.append(yb)
            if sr >= max_sr:
                collapsed_streak = 0   # reset outside the late window
                continue
            vol = _rolling_vol(bids_so_far)
            if vol < vol_thr:
                collapsed_streak += 1
                if collapsed_streak >= persist_n:
                    convergence_exit = True
                    exit_sr  = sr
                    exit_bid = yb
                    break
            else:
                collapsed_streak = 0

    # ------------------------------------------------------------------
    # Policy E: hybrid — SR guard + convergence confirmation
    # Exit when SR < sr_guard AND (vol_collapsed OR within proxy band).
    # Uses settlement proxy for proximity check (research assumption).
    # ------------------------------------------------------------------
    elif policy_name == "E_hybrid_convergence_derisk":
        sr_guard   = float(policy["sr_guard"])
        vol_thr    = float(policy["vol_threshold"])
        proxy_band = float(policy.get("proxy_band", _CONV_PROXY_BAND))
        for sr, yb in timeline:
            bids_so_far.append(yb)
            if sr >= sr_guard:
                continue
            vol_ok   = _rolling_vol(bids_so_far) < vol_thr
            proxy_ok = (
                settlement_proxy_bid is not None and
                abs(yb - settlement_proxy_bid) <= proxy_band
            )
            if vol_ok or proxy_ok:
                convergence_exit = True
                exit_sr  = sr
                exit_bid = yb
                break

    # If no exit action, accumulate remaining bids for diagnostic completeness
    if not convergence_exit and policy_name not in ("A_baseline_hold_to_settlement",):
        pass  # bids_so_far already accumulated up to first non-triggering scan

    # ------------------------------------------------------------------
    # PnL (identical formula to lifecycle_profit_management_replay)
    # All convergence exits are full closes (reduce_fraction = 1.0)
    # ------------------------------------------------------------------
    reduce_fraction = 1.0 if convergence_exit else 0.0
    reduce_price    = exit_bid if convergence_exit else None
    reduce_sr_val   = exit_sr  if convergence_exit else None

    tokens_reduced = round(tokens_total * reduce_fraction, 8)
    tokens_runner  = round(tokens_total * (1.0 - reduce_fraction), 8)

    reduce_pnl = 0.0
    if reduce_price is not None and tokens_reduced > 0:
        reduce_pnl = round((reduce_price - entry_price) * tokens_reduced, 8)

    runner_pnl: float | None = None
    if tokens_runner == 0.0:
        runner_pnl = 0.0
    elif settlement_price is not None:
        runner_pnl = round((settlement_price - entry_price) * tokens_runner, 8)

    total_pnl: float | None = None
    if runner_pnl is not None:
        total_pnl = round(reduce_pnl + runner_pnl, 8)

    # Premature reduce regret: (settlement - reduce_price) * tokens_reduced
    # positive = left money on table; negative = avoided a loss
    premature_regret: float | None = None
    if reduce_price is not None and settlement_price is not None and tokens_reduced > 0:
        premature_regret = round((settlement_price - reduce_price) * tokens_reduced, 8)

    # ------------------------------------------------------------------
    # Late reversal detection (research diagnostic; uses post-exit data)
    # True when any post-exit yes_bid deviates > CONV_REVERSAL_THRESHOLD
    # from exit_bid in absolute terms.
    # ------------------------------------------------------------------
    late_reversal = False
    if convergence_exit and exit_bid is not None and exit_sr is not None:
        for sr, post_yb in all_snaps:
            if sr < exit_sr and abs(post_yb - exit_bid) > _CONV_REVERSAL_THRESHOLD:
                late_reversal = True
                break

    # ------------------------------------------------------------------
    # False convergence exit classification
    # Fires when: settlement direction contradicts exit_bid, OR late reversal.
    # ------------------------------------------------------------------
    false_convergence_exit = False
    if convergence_exit and settlement_price is not None and exit_bid is not None:
        direction_mismatch = (
            (exit_bid > 0.5 and settlement_price < 0.5) or
            (exit_bid < 0.5 and settlement_price > 0.5)
        )
        false_convergence_exit = direction_mismatch or late_reversal

    # ------------------------------------------------------------------
    # convergence_false_positive_cost_usd (per-position component)
    # Cost = max(0, premature_regret) for false-convergence-exit positions.
    # Captures USD left on table when a false convergence exit fired.
    # ------------------------------------------------------------------
    fp_cost: float | None = None
    if false_convergence_exit and premature_regret is not None:
        fp_cost = round(max(0.0, premature_regret), 8)

    # ------------------------------------------------------------------
    # Late uncertainty expansion (per position)
    # True when volatility in the late window (SR < 90s) exceeds
    # volatility in the early window (SR >= 90s).
    # Uses post-entry timeline only (no future leakage for the diagnostic).
    # ------------------------------------------------------------------
    early_bids = [yb for sr, yb in timeline if sr >= _LATE_VOL_SR_BOUNDARY]
    late_bids  = [yb for sr, yb in timeline if sr <  _LATE_VOL_SR_BOUNDARY]
    early_vol  = _stdev_safe(early_bids)
    late_vol   = _stdev_safe(late_bids)
    late_uncertainty_expansion = (
        early_vol is not None and late_vol is not None and
        late_vol > early_vol
    )

    # ------------------------------------------------------------------
    # Exit-point convergence diagnostics
    # ------------------------------------------------------------------
    exit_vol      = _rolling_vol(bids_so_far)
    exit_bid_stab = _bid_stabilization(bids_so_far)
    early_epoch_vol = early_vol  # stdev of early-window bids (may be None)

    snapshots_to_convergence = len(bids_so_far) if convergence_exit else None

    return {
        "total_pnl":                  total_pnl,
        "reduce_pnl":                 round(reduce_pnl, 8),
        "runner_pnl":                 runner_pnl,
        "reduce_price":               reduce_price,
        "reduce_sr":                  reduce_sr_val,
        "reduce_fraction":            reduce_fraction,
        "tokens_total":               round(tokens_total, 6),
        "tokens_reduced":             round(tokens_reduced, 6),
        "tokens_runner":              round(tokens_runner, 6),
        "convergence_exit":           convergence_exit,
        "late_reversal":              late_reversal,
        "false_convergence_exit":     false_convergence_exit,
        "premature_reduce_regret":    premature_regret,
        "fp_cost":                    fp_cost,
        "exit_vol":                   exit_vol,
        "exit_bid_stab":              exit_bid_stab,
        "early_epoch_vol":            early_epoch_vol,
        "snapshots_to_convergence":   snapshots_to_convergence,
        "late_uncertainty_expansion": late_uncertainty_expansion,
        "research_proxy_used":        policy.get("research_proxy", False),
    }


# ---------------------------------------------------------------------------
# Policy simulation (inventory continuity: max 1 position per asset per epoch)
# ---------------------------------------------------------------------------

def simulate_convergence_policy(
    events:          list[dict[str, Any]],
    settlement_map:  dict[tuple[Any, str], dict[str, Any]],
    epoch_timelines: dict[tuple[Any, str], list[tuple[float, float]]],
    policy:          dict[str, Any],
    bankroll_ref:    float = 20.0,
) -> list[dict[str, Any]]:
    """
    Run one convergence policy with max-1-position-per-asset inventory constraint.
    Returns a list of position records (one per simulated entry).
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

    asset_entered_this_epoch: dict[str, bool] = {}
    positions: list[dict[str, Any]] = []
    prev_epoch_ts = None

    for epoch_key in sorted_keys:
        ep_ts, mk = epoch_key
        epoch_events = epoch_groups[epoch_key]
        asset = _asset_from_event(epoch_events[0])

        if ep_ts != prev_epoch_ts:
            asset_entered_this_epoch = {}
            prev_epoch_ts = ep_ts

        if asset_entered_this_epoch.get(asset):
            continue

        entry_event = None
        for p in epoch_events:
            shadow = _compute_shadow(p)
            if shadow["nonzero"]:
                entry_event = p
                break
        if entry_event is None:
            continue

        asset_entered_this_epoch[asset] = True

        shadow      = _compute_shadow(entry_event)
        entry_price = float(entry_event.get("entry_price") or 0.0)
        entry_sr    = float(entry_event.get("seconds_remaining") or 0.0)

        sett = settlement_map.get(epoch_key)
        settlement_price:     float | None = None
        settlement_label                   = "NO_SNAPSHOT"
        settlement_proxy_bid: float | None = None
        unresolved                         = True

        if sett and sett["confidence"] == "HIGH":
            settlement_price     = sett["settlement_price"]
            settlement_label     = sett["inferred_settlement"]
            settlement_proxy_bid = sett.get("yes_bid_at_match")
            unresolved           = False
        elif sett and sett["confidence"] == "AMBIGUOUS":
            settlement_label = "AMBIGUOUS"

        all_snaps = epoch_timelines.get(epoch_key) or []

        lc = _simulate_convergence(
            entry_price=entry_price,
            shadow_size=shadow["c_size"],
            entry_sr=entry_sr,
            all_snaps=all_snaps,
            settlement_price=settlement_price,
            settlement_proxy_bid=settlement_proxy_bid,
            policy=policy,
        )

        positions.append({
            "asset":               asset,
            "market_key":          mk,
            "epoch_start_ts":      ep_ts,
            "entry_price":         entry_price,
            "shadow_size_usd":     shadow["c_size"],
            "shadow_pct_bankroll": shadow["pct_bankroll"],
            "entry_sr":            entry_sr,
            "settlement":          settlement_label,
            "settlement_price":    settlement_price,
            "unresolved":          unresolved,
            **lc,
        })

    return positions


# ---------------------------------------------------------------------------
# Per-policy report
# ---------------------------------------------------------------------------

def _policy_report(
    positions:        list[dict[str, Any]],
    policy:           dict[str, Any],
    bankroll_ref:     float,
    baseline_pnl:     float,
    fixed_derisk_pnl: float,
) -> dict[str, Any]:
    total_entries = len(positions)
    settled       = [p for p in positions if p.get("total_pnl") is not None]
    pnl_vals      = [p["total_pnl"] for p in settled]
    realized_pnl  = round(sum(pnl_vals), 8) if pnl_vals else 0.0

    pnl_uplift_vs_baseline     = round(realized_pnl - baseline_pnl, 8)
    pnl_uplift_vs_fixed_derisk = round(realized_pnl - fixed_derisk_pnl, 8)

    # --- Convergence metrics ---
    conv_exits      = [p for p in positions if p.get("convergence_exit")]
    conv_exit_count = len(conv_exits)
    exit_srs        = [p["reduce_sr"] for p in conv_exits if p.get("reduce_sr") is not None]
    avg_exit_sr     = round(mean(exit_srs), 1) if exit_srs else 0.0

    late_reversal_count      = sum(1 for p in positions if p.get("late_reversal"))
    false_conv_exit_count    = sum(1 for p in positions if p.get("false_convergence_exit"))
    late_unc_expansion_count = sum(1 for p in positions if p.get("late_uncertainty_expansion"))

    stability_score = (
        round(1.0 - false_conv_exit_count / conv_exit_count, 4)
        if conv_exit_count > 0 else None
    )
    reversal_rate = (
        round(late_reversal_count / conv_exit_count, 4)
        if conv_exit_count > 0 else 0.0
    )

    # convergence_false_positive_cost_usd
    fp_costs = [p["fp_cost"] for p in positions if p.get("fp_cost") is not None]
    conv_fp_cost_usd = round(sum(fp_costs), 8) if fp_costs else 0.0

    # Premature reduce regret
    regret_vals = [
        p["premature_reduce_regret"] for p in settled
        if p.get("premature_reduce_regret") is not None
    ]
    premature_regret_total = round(sum(regret_vals), 8) if regret_vals else 0.0

    # --- Exposure ---
    epoch_exp: dict[Any, float] = defaultdict(float)
    for p in positions:
        epoch_exp[p["epoch_start_ts"]] += p["shadow_pct_bankroll"]
    max_exp_pct = round(max(epoch_exp.values(), default=0.0), 4)

    # --- Drawdown ---
    sorted_settled = sorted(
        settled,
        key=lambda p: (p.get("epoch_start_ts") or 0, p.get("market_key") or ""),
    )
    max_dd  = _max_drawdown([p["total_pnl"] for p in sorted_settled])
    dd_pct  = round(max_dd / bankroll_ref * 100, 2) if bankroll_ref > 0 else 0.0

    # --- Win rate ---
    wins   = sum(1 for v in pnl_vals if v > 0)
    losses = sum(1 for v in pnl_vals if v < 0)
    wr     = _pct(wins, len(settled))
    avg_win  = round(mean([v for v in pnl_vals if v > 0]), 6) if wins   else None
    avg_loss = round(mean([v for v in pnl_vals if v < 0]), 6) if losses else None

    # --- Clustered losses ---
    cluster_info = _clustered_losses(sorted_settled)

    # --- BTC / ETH ---
    def _asset_report(asset: str) -> dict[str, Any]:
        sub     = [p for p in settled if p["asset"] == asset]
        vals    = [p["total_pnl"] for p in sub]
        wins_a  = [v for v in vals if v > 0]
        a_exits = [p for p in positions if p["asset"] == asset and p.get("convergence_exit")]
        a_srs   = [p["reduce_sr"] for p in a_exits if p.get("reduce_sr") is not None]
        return {
            "entries":           len([p for p in positions if p["asset"] == asset]),
            "settled_fills":     len(sub),
            "total_pnl":         round(sum(vals), 8) if vals else 0.0,
            "win_rate_pct":      _pct(len(wins_a), len(sub)),
            "pnl_stats":         _stats(vals),
            "convergence_exits": len(a_exits),
            "avg_exit_sr":       round(mean(a_srs), 1) if a_srs else 0.0,
        }

    # --- Convergence timing distribution ---
    sr_buckets: dict[str, int] = {
        "300-150": 0, "150-90": 0, "90-60": 0, "60-30": 0, "30-0": 0,
    }
    for sr in exit_srs:
        if sr >= 150:
            sr_buckets["300-150"] += 1
        elif sr >= 90:
            sr_buckets["150-90"] += 1
        elif sr >= 60:
            sr_buckets["90-60"] += 1
        elif sr >= 30:
            sr_buckets["60-30"] += 1
        else:
            sr_buckets["30-0"] += 1

    # --- Snapshots to convergence ---
    snap_counts = [
        p["snapshots_to_convergence"]
        for p in positions
        if p.get("snapshots_to_convergence") is not None
    ]
    avg_snaps = round(mean(snap_counts), 1) if snap_counts else None

    # --- Uncertainty collapse window (P10–P90 of exit SRs) ---
    collapse_window: dict[str, Any] = {}
    if len(exit_srs) >= 10:
        q = quantiles(exit_srs, n=10)
        collapse_window = {"p10_sr": round(q[0], 1), "p90_sr": round(q[8], 1)}
    elif exit_srs:
        collapse_window = {
            "p10_sr": round(min(exit_srs), 1),
            "p90_sr": round(max(exit_srs), 1),
        }

    # --- Volatility before / after convergence ---
    exit_vols = [
        p["exit_vol"] for p in conv_exits
        if p.get("exit_vol") is not None and p["exit_vol"] != float("inf")
    ]
    early_vols = [
        p["early_epoch_vol"] for p in positions
        if p.get("early_epoch_vol") is not None
    ]
    volatility_at_exit_mean  = round(mean(exit_vols),  6) if exit_vols  else None
    early_epoch_vol_mean     = round(mean(early_vols), 6) if early_vols else None

    # --- BTC / ETH convergence gap ---
    btc_srs = [p["reduce_sr"] for p in conv_exits if p.get("asset") == "BTC" and p.get("reduce_sr") is not None]
    eth_srs = [p["reduce_sr"] for p in conv_exits if p.get("asset") == "ETH" and p.get("reduce_sr") is not None]
    eth_vs_btc_gap: float | None = None
    if btc_srs and eth_srs:
        eth_vs_btc_gap = round(mean(eth_srs) - mean(btc_srs), 1)

    # --- Avg entry SR ---
    entry_srs    = [p["entry_sr"] for p in positions]
    avg_entry_sr = round(mean(entry_srs), 1) if entry_srs else 0.0

    # --- Verdict ---
    false_rate = false_conv_exit_count / conv_exit_count if conv_exit_count > 0 else 0.0

    if conv_exit_count > 0 and false_rate > _CONVERGENCE_UNSTABLE_RATE:
        verdict = "convergence_unstable"
        verdict_note = (
            f"False convergence exit rate {false_rate:.0%} exceeds "
            f"{_CONVERGENCE_UNSTABLE_RATE:.0%} stability threshold "
            f"({false_conv_exit_count}/{conv_exit_count} exits)."
        )
    elif dd_pct > _UNSAFE_DRAWDOWN_PCT:
        verdict = "unsafe_due_to_drawdown"
        verdict_note = (
            f"Max drawdown ${max_dd:.4f} = {dd_pct:.1f}% of bankroll "
            f"(>{_UNSAFE_DRAWDOWN_PCT}% threshold)."
        )
    elif total_entries < _NEEDS_MORE_ENTRIES or wr < _NEEDS_MORE_WIN_RATE:
        verdict = "needs_more_replay"
        verdict_note = (
            f"Entries={total_entries} or win_rate={wr:.1f}% below threshold."
        )
    elif abs(pnl_uplift_vs_baseline) < _NO_IMPROVEMENT_USD:
        verdict = "no_material_improvement"
        verdict_note = (
            f"PnL uplift ${pnl_uplift_vs_baseline:+.4f} is within the "
            f"${_NO_IMPROVEMENT_USD} no-material-improvement band."
        )
    else:
        verdict = "safe_candidate"
        verdict_note = (
            f"Uplift vs baseline ${pnl_uplift_vs_baseline:+.4f} "
            f"(vs fixed-derisk ${pnl_uplift_vs_fixed_derisk:+.4f}), "
            f"drawdown ${max_dd:.4f} ({dd_pct:.1f}%), "
            f"win_rate {wr:.1f}%, entries {total_entries}."
        )

    return {
        "policy_name":  policy["name"],
        "policy_label": policy["label"],
        # 1
        "realized_proxy_pnl":            realized_pnl,
        "settled_fill_count":            len(settled),
        "pnl_stats":                     _stats(pnl_vals),
        # 2
        "pnl_uplift_vs_baseline":        pnl_uplift_vs_baseline,
        "pnl_uplift_vs_fixed_derisk_sr60": pnl_uplift_vs_fixed_derisk,
        # 3
        "max_drawdown":                  max_dd,
        "max_drawdown_pct_bankroll":     dd_pct,
        # 4
        "convergence_exit_count":        conv_exit_count,
        # 5
        "avg_exit_sr":                   avg_exit_sr,
        # 6
        "convergence_stability_score":   stability_score,
        # 7
        "false_convergence_exits":       false_conv_exit_count,
        # 8
        "late_reversal_count":           late_reversal_count,
        # 9
        "btc": _asset_report("BTC"),
        "eth": _asset_report("ETH"),
        # 10
        "volatility_at_exit_mean":       volatility_at_exit_mean,
        "early_epoch_vol_mean":          early_epoch_vol_mean,
        # 11
        "clustered_loss_periods":        cluster_info,
        # 12
        "max_exposure_pct":              max_exp_pct,
        # 13
        "verdict":      verdict,
        "verdict_note": verdict_note,
        # Win / loss
        "win_rate_pct": wr,
        "win_count":    wins,
        "loss_count":   losses,
        "avg_win":      avg_win,
        "avg_loss":     avg_loss,
        "avg_entry_sr": avg_entry_sr,
        # Convergence diagnostics
        "convergence_timing_distribution":       sr_buckets,
        "average_snapshots_to_convergence":      avg_snaps,
        "reversal_after_convergence_rate":       reversal_rate,
        "eth_vs_btc_convergence_gap":            eth_vs_btc_gap,
        "uncertainty_collapse_window_estimate":  collapse_window,
        "convergence_false_positive_cost_usd":   conv_fp_cost_usd,
        "late_uncertainty_expansion_count":      late_unc_expansion_count,
        "premature_reduce_regret_usd":           premature_regret_total,
        "unresolved_count":                      sum(1 for p in positions if p.get("unresolved")),
        "research_proxy_used":                   policy.get("research_proxy", False),
    }


# ---------------------------------------------------------------------------
# Core analysis: run all 5 policies
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

    unsafe_dd_usd = round(bankroll_ref * _UNSAFE_DRAWDOWN_PCT / 100.0, 4)

    # Policy A: baseline (establishes baseline_pnl reference)
    pos_a    = simulate_convergence_policy(events, settlement_map, epoch_timelines, POLICIES[0], bankroll_ref)
    report_a = _policy_report(pos_a, POLICIES[0], bankroll_ref, baseline_pnl=0.0, fixed_derisk_pnl=0.0)
    baseline_pnl = report_a["realized_proxy_pnl"]

    # Policy B: fixed derisk SR60 (establishes fixed_derisk_pnl reference)
    pos_b    = simulate_convergence_policy(events, settlement_map, epoch_timelines, POLICIES[1], bankroll_ref)
    report_b = _policy_report(pos_b, POLICIES[1], bankroll_ref, baseline_pnl=baseline_pnl, fixed_derisk_pnl=baseline_pnl)
    fixed_derisk_pnl = report_b["realized_proxy_pnl"]
    report_b["pnl_uplift_vs_fixed_derisk_sr60"] = 0.0   # B vs itself

    # Policies C, D, E: compared against both baseline and fixed-derisk
    policy_reports: list[dict[str, Any]] = [report_a, report_b]
    for policy in POLICIES[2:]:
        pos    = simulate_convergence_policy(events, settlement_map, epoch_timelines, policy, bankroll_ref)
        report = _policy_report(pos, policy, bankroll_ref, baseline_pnl=baseline_pnl, fixed_derisk_pnl=fixed_derisk_pnl)
        policy_reports.append(report)

    # Comparison
    safe      = [r for r in policy_reports if r["verdict"] == "safe_candidate"]
    best_pnl  = max(policy_reports, key=lambda r: r["realized_proxy_pnl"])
    best_safe = max(safe, key=lambda r: r["realized_proxy_pnl"]) if safe else None

    comparison_rows = [
        {
            "policy":          r["policy_label"],
            "entries":         r["settled_fill_count"],
            "realized_pnl":    r["realized_proxy_pnl"],
            "uplift_vs_A":     r["pnl_uplift_vs_baseline"],
            "uplift_vs_B":     r["pnl_uplift_vs_fixed_derisk_sr60"],
            "max_dd":          r["max_drawdown"],
            "win_rate":        r["win_rate_pct"],
            "conv_exits":      r["convergence_exit_count"],
            "false_conv":      r["false_convergence_exits"],
            "late_rev":        r["late_reversal_count"],
            "fp_cost_usd":     r["convergence_false_positive_cost_usd"],
            "late_unc_expand": r["late_uncertainty_expansion_count"],
            "verdict":         r["verdict"],
        }
        for r in policy_reports
    ]

    if best_safe:
        recommended = best_safe["policy_label"]
        rec_note = (
            f"'{recommended}' is the safe convergence policy with the best proxy PnL. "
            "Validate over more sessions before any runtime consideration. "
            "Do NOT promote to runtime without a separately scoped Phase 3 implementation."
        )
    else:
        recommended = "A_baseline or B_fixed_derisk_sr60 (no convergence policy reached safe_candidate)"
        rec_note = (
            "No convergence policy safely improved on baseline. "
            "Continue using Lifecycle Policy D (fixed SR<60 derisk)."
        )

    return {
        "event_count":  total_events,
        "bankroll_ref": bankroll_ref,
        "unsafe_dd_usd": unsafe_dd_usd,
        "policy_A": policy_reports[0],
        "policy_B": policy_reports[1],
        "policy_C": policy_reports[2],
        "policy_D": policy_reports[3],
        "policy_E": policy_reports[4],
        "policy_comparison": {
            "rows":             comparison_rows,
            "best_pnl_policy":  best_pnl["policy_label"],
            "best_safe_policy": best_safe["policy_label"] if best_safe else "none",
            "recommended":      recommended,
            "recommended_note": rec_note,
        },
        "simulation_rules": [
            "Max 1 position per asset per epoch (no reloads).",
            "No future leakage: decisions use only snapshots with SR < entry_SR.",
            f"Policy B: full close at first snapshot with SR < {_DERISK_SR}s.",
            (
                f"Policy C: full close when yes_bid within {_CONV_PROXY_BAND} (abs) "
                f"of settlement proxy for >= {_CONV_PERSIST_N} consecutive snapshots "
                "(RESEARCH ASSUMPTION: uses settlement proxy = future knowledge)."
            ),
            (
                f"Policy D: full close when rolling-{_CONV_VOL_WINDOW}-snapshot vol "
                f"< {_CONV_VOL_THRESHOLD} for >= {_CONV_PERSIST_N} consecutive "
                f"snapshots AND SR < {_CONV_MAX_SR}s. Backward-looking only."
            ),
            (
                f"Policy E: full close when SR < {_DERISK_SR}s AND "
                "(vol_collapsed OR yes_bid within proxy band) "
                "(RESEARCH ASSUMPTION: uses settlement proxy for proximity)."
            ),
            (
                "convergence_false_positive_cost_usd = sum of max(0, premature_reduce_regret) "
                "for positions flagged as false_convergence_exit."
            ),
            (
                f"late_uncertainty_expansion = late-window vol (SR < {_LATE_VOL_SR_BOUNDARY}s) "
                f"> early-window vol (SR >= {_LATE_VOL_SR_BOUNDARY}s)."
            ),
            "Settlement inferred from market_snapshots yes_bid near close (proxy, not confirmed).",
        ],
        "guardrail": (
            "offline-only; does not change strategy, risk, execution, "
            "position_sizing.py, order_manager.py, paper/live separation, "
            "or any runtime behavior; Policies C and E use settlement proxy "
            "(future knowledge) for convergence proximity — labeled research_proxy_used=True"
        ),
    }


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------

SEP  = "=" * 76
SEP2 = "-" * 76


def _print_policy_section(r: dict[str, Any]) -> None:
    print(f"\n{SEP2}")
    print(f"  {r['policy_label']}")
    if r.get("research_proxy_used"):
        print(f"  [RESEARCH] Uses settlement proxy (future knowledge) for proximity check.")
    print(f"{SEP2}")
    print(f"  Settled fills            : {r['settled_fill_count']}")

    print(f"\n  [PnL]")
    print(f"  Realized proxy PnL       : ${r['realized_proxy_pnl']:.4f}")
    print(f"  Uplift vs baseline (A)   : ${r['pnl_uplift_vs_baseline']:+.4f}")
    print(f"  Uplift vs fixed-derisk (B): ${r['pnl_uplift_vs_fixed_derisk_sr60']:+.4f}")
    print(f"  Win rate                 : {r['win_rate_pct']:.1f}%  ({r['win_count']}W / {r['loss_count']}L)")
    aw = r.get("avg_win"); al = r.get("avg_loss")
    print(f"  Avg win / loss           : {'$%.4f' % aw if aw is not None else 'N/A'} / "
          f"{'$%.4f' % al if al is not None else 'N/A'}")

    print(f"\n  [Convergence]")
    print(f"  Convergence exits        : {r['convergence_exit_count']}")
    print(f"  Avg exit SR              : {r['avg_exit_sr']:.1f}s")
    stab = r.get("convergence_stability_score")
    print(f"  Stability score          : {stab:.4f}" if stab is not None else "  Stability score          : N/A")
    print(f"  False convergence exits  : {r['false_convergence_exits']}")
    print(f"  Late reversal count      : {r['late_reversal_count']}")
    print(f"  FP cost (USD)            : ${r['convergence_false_positive_cost_usd']:.4f}")
    print(f"  Late uncertainty expand  : {r['late_uncertainty_expansion_count']}")
    rev = r.get("reversal_after_convergence_rate") or 0.0
    print(f"  Reversal rate            : {rev:.1%}")
    pre = r.get("premature_reduce_regret_usd") or 0.0
    print(f"  Premature regret         : ${pre:+.4f}  (+ve=left on table, -ve=avoided loss)")

    tbd = r.get("convergence_timing_distribution") or {}
    if any(v for v in tbd.values()):
        print(f"  Exit SR distribution     : " + "  ".join(f"{k}:{v}" for k, v in tbd.items()))

    avg_s = r.get("average_snapshots_to_convergence")
    if avg_s is not None:
        print(f"  Avg snapshots to conv.   : {avg_s:.1f}")

    cw = r.get("uncertainty_collapse_window_estimate") or {}
    if cw:
        print(f"  Collapse window (P10-P90): SR {cw.get('p90_sr','?')}s – {cw.get('p10_sr','?')}s")

    gap = r.get("eth_vs_btc_convergence_gap")
    if gap is not None:
        print(f"  ETH vs BTC conv gap      : {gap:+.1f}s (positive = ETH exits later)")

    ev_exit = r.get("volatility_at_exit_mean")
    ev_early = r.get("early_epoch_vol_mean")
    if ev_exit is not None or ev_early is not None:
        print(f"  Vol at exit (mean)       : {ev_exit:.6f}" if ev_exit is not None else "  Vol at exit (mean)       : N/A")
        print(f"  Early window vol (mean)  : {ev_early:.6f}" if ev_early is not None else "  Early window vol (mean)  : N/A")

    print(f"\n  [Risk]")
    print(f"  Max exposure             : {r['max_exposure_pct']:.2f}%")
    print(f"  Max drawdown             : ${r['max_drawdown']:.4f} ({r['max_drawdown_pct_bankroll']:.1f}% bankroll)")
    cl = r.get("clustered_loss_periods") or {}
    print(f"  Max consec losses        : {cl.get('max_consecutive_losses',0)}  "
          f"(clusters: {cl.get('loss_cluster_count',0)})")
    print(f"  Avg entry SR             : {r['avg_entry_sr']:.0f}s remaining")

    print(f"\n  [BTC / ETH]")
    for label, key in [("BTC", "btc"), ("ETH", "eth")]:
        a  = r.get(key) or {}
        p2 = a.get("pnl_stats") or {}
        if a.get("entries", 0) == 0:
            print(f"  {label}: no entries")
            continue
        print(f"  {label}: entries={a['entries']}  settled={a.get('settled_fills',0)}  "
              f"pnl=${a.get('total_pnl',0):.4f}  wr={a.get('win_rate_pct',0):.1f}%  "
              f"conv_exits={a.get('convergence_exits',0)}  "
              f"avg_exit_sr={a.get('avg_exit_sr',0):.0f}s")

    print(f"\n  [Verdict]  {r['verdict']}")
    print(f"  {r['verdict_note']}")


def print_report(result: dict[str, Any], date_str: str) -> None:
    if "error" in result:
        print(f"\n{SEP}")
        print(f"  Exit Convergence Intelligence Replay v1  |  {date_str}")
        print(f"{SEP}")
        print(f"  ERROR: {result['error']}")
        print(f"{SEP}\n")
        return

    print(f"\n{SEP}")
    print(f"  Exit Convergence Intelligence Replay v1  |  {date_str}")
    print(f"{SEP}")
    print(f"  Total events    : {result['event_count']}")
    print(f"  Bankroll ref    : ${result['bankroll_ref']:.2f}")
    print(f"  Unsafe DD (USD) : ${result['unsafe_dd_usd']:.2f} (={_UNSAFE_DRAWDOWN_PCT}% bankroll)")

    for key in ("policy_A", "policy_B", "policy_C", "policy_D", "policy_E"):
        r = result.get(key)
        if r:
            _print_policy_section(r)

    print(f"\n{SEP}")
    print(f"  POLICY COMPARISON SUMMARY")
    print(f"{SEP}")
    hdr = (f"  {'Policy':<40} {'Fills':>5} {'PnL':>9} {'vs A':>8} {'vs B':>8} "
           f"{'MaxDD':>7} {'WR%':>5} {'CExit':>6} {'FalseC':>7} "
           f"{'FPcost':>8} {'LateUE':>7}  Verdict")
    print(hdr)
    print(f"  {'-'*40} {'-'*5} {'-'*9} {'-'*8} {'-'*8} {'-'*7} {'-'*5} "
          f"{'-'*6} {'-'*7} {'-'*8} {'-'*7}  {'-'*22}")
    for row in result.get("policy_comparison", {}).get("rows", []):
        print(
            f"  {row['policy']:<40} {row['entries']:>5} "
            f"${row['realized_pnl']:>8.2f} ${row['uplift_vs_A']:>+7.2f} ${row['uplift_vs_B']:>+7.2f} "
            f"${row['max_dd']:>6.2f} {row['win_rate']:>4.1f}% "
            f"{row['conv_exits']:>6} {row['false_conv']:>7} "
            f"${row['fp_cost_usd']:>7.2f} {row['late_unc_expand']:>7}  {row['verdict']}"
        )
    pc = result.get("policy_comparison") or {}
    print(f"\n  Best PnL policy : {pc.get('best_pnl_policy','?')}")
    print(f"  Best safe policy: {pc.get('best_safe_policy','?')}")
    print(f"  Recommended     : {pc.get('recommended','?')}")
    print(f"  {pc.get('recommended_note','')}")
    print(f"\n  guardrail: {result.get('guardrail','')}")
    print(f"{SEP}\n")


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(result: dict[str, Any], date_str: str, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now(tz=timezone.utc).strftime("%H%M")
    path = report_dir / f"exit_convergence_{date_str}_{ts}.json"
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
        description="Exit Convergence Intelligence Replay v1 -- offline-only"
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
