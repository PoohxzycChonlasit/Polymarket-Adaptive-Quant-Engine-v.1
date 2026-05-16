"""
Lifecycle Profit Management Replay v1 -- offline replay tool.

Measures whether lifecycle-aware HOLD / REDUCE / FINAL_DERISK management can
safely improve realized proxy PnL versus the current atomic hold-to-settlement
baseline, WITHOUT adding reloads or increasing inventory concentration risk.

Baseline inventory constraints (same as Policy A, continuity replay):
  max 1 position per asset per epoch
  no reloads

Intra-epoch yes_bid calibration (2026-05-15):
  35 YES epochs (final yes_bid >= 0.70)
  33 NO epochs  (final yes_bid <= 0.30)
  mean entry_price: $0.276/token
  YES: yes_bid crosses 0.60 at mean SR=262s (early in window)
  YES: yes_bid crosses 0.70 at mean SR=220s
  YES: yes_bid crosses 0.80 at mean SR=185s
  NO:  9/33 NO epochs briefly touch 0.60 (decoy peaks)

Five policies simulated:
  A  baseline_hold_to_settlement      hold 100% to settlement
  B  partial_reduce_50pct_at_2x       reduce 50% when yes_bid >= 2x entry_price
  C  partial_reduce_50pct_at_3x       reduce 50% when yes_bid >= 3x entry_price
  D  dynamic_derisk_before_close      close 100% at first snapshot with SR < 60s
  E  hold_winners_cut_late_decay      reduce 50% on 15% decay from peak after SR<120

No future leakage: decisions use only snapshots with SR < entry_SR, processed
chronologically (SR descending = earlier in window first).

Additional diagnostic metrics:
  premature_reduce_regret_usd  (settlement - reduce_price) * tokens_reduced
                                positive = left money on table (reduced too early)
                                negative = avoided a loss (benefited from early exit)
  false_decay_trigger_count    (Policy E) decay cut fired but epoch settled YES

Data sources (local JSONL only -- no live API calls):
  runtime/quant_data/system_health/YYYY-MM-DD.jsonl    (zero_size_probe_v1)
  runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl  (settlement proxy + timeline)

Settlement inference:
  yes_bid >= 0.70  ->  YES  (settlement_price=1.0, HIGH)
  yes_bid <= 0.30  ->  NO   (settlement_price=0.0, HIGH)
  otherwise        ->  AMBIGUOUS (excluded from PnL)

Usage:
  python -m tools.lifecycle_profit_management_replay --date 2026-05-15
  python -m tools.lifecycle_profit_management_replay --date 2026-05-15 --write-report
  python -m tools.lifecycle_profit_management_replay --date 2026-05-15 --run-id <id>
  python -m tools.lifecycle_profit_management_replay --date 2026-05-15 --asset BTC

Output:
  Console summary + optional runtime/reports/lifecycle_pm_YYYY-MM-DD_HHMM.json

Per-policy report (13 outputs per policy):
   1.  realized_proxy_pnl
   2.  pnl_uplift_vs_baseline_usd
   3.  max_drawdown
   4.  win_rate_pct
   5.  avg_win / avg_loss
   6.  realized_runner_contribution_usd
   7.  forced_derisk_count
   8.  late_window_decay_avoided_count
   9.  btc_eth_contribution
  10.  max_exposure_pct
  11.  clustered_loss_periods
  12.  avg_entry_sr
  13.  verdict

Additional diagnostics:
  premature_reduce_regret_usd    (see above)
  false_decay_trigger_count      (Policy E only)

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

# Settlement proxy thresholds
_YES_THRESHOLD    = 0.70
_NO_THRESHOLD     = 0.30
_MAX_SR_FOR_PROXY = 120.0

# Safety verdict thresholds
_UNSAFE_DRAWDOWN_PCT   = 10.0   # max_drawdown > 10% bankroll
_NO_IMPROVEMENT_USD    = 2.0    # |pnl_uplift| < $2 = no material improvement
_NEEDS_MORE_ENTRIES    = 10
_NEEDS_MORE_WIN_RATE   = 40.0

# Policy D: derisk SR threshold
_DERISK_SR = 60.0

# Policy E: late decay parameters
_DECAY_THRESHOLD    = 0.15   # 15% drop from peak
_DECAY_SR_WINDOW    = 120.0  # only check when SR < 120s
_DECAY_PEAK_MIN     = 0.40   # peak must have been >= 0.40 to be a "winner"
_DECAY_REDUCE_FRAC  = 0.50   # reduce 50% on detected decay

POLICIES: list[dict[str, Any]] = [
    {
        "name":  "A_baseline_hold_to_settlement",
        "label": "A  baseline (hold-to-settlement)",
    },
    {
        "name":           "B_partial_reduce_50pct_at_2x",
        "label":          "B  reduce-50% at 2x entry price",
        "threshold_mult": 2.0,
        "reduce_fraction": 0.50,
    },
    {
        "name":           "C_partial_reduce_50pct_at_3x",
        "label":          "C  reduce-50% at 3x entry price",
        "threshold_mult": 3.0,
        "reduce_fraction": 0.50,
    },
    {
        "name":              "D_dynamic_derisk_before_close",
        "label":             "D  derisk-before-close (SR<60s)",
        "derisk_sr_threshold": _DERISK_SR,
    },
    {
        "name":             "E_hold_winners_cut_late_decay",
        "label":            "E  hold-winners / cut-late-decay",
        "decay_threshold":  _DECAY_THRESHOLD,
        "decay_sr_window":  _DECAY_SR_WINDOW,
        "peak_min":         _DECAY_PEAK_MIN,
        "reduce_fraction":  _DECAY_REDUCE_FRAC,
    },
]


# ---------------------------------------------------------------------------
# Shadow formula (identical to other shadow tools)
# ---------------------------------------------------------------------------

def _compute_shadow(p: dict[str, Any]) -> dict[str, Any]:
    if "semantic_c_multiplier_shadow" in p:
        return {
            "c_size":    float(p.get("semantic_c_size_usd_shadow") or 0.0),
            "nonzero":   bool(p.get("semantic_c_would_produce_nonzero_size")),
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
    """
    Load market_snapshots yes_bid timelines for probe epochs.

    Returns {(epoch_ts, market_key): [(sr, yes_bid), ...]} where yes_bid values
    are filtered to [0.0, 1.0] and the list is NOT yet sorted (caller sorts after
    filtering to entry_sr).  Only epochs in probe_epoch_keys are included.
    """
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
        key  = (ep, mk)
        if key not in probe_epoch_keys:
            continue
        yb_f = float(yb)
        sr_f = float(sr)
        if 0.0 <= yb_f <= 1.0:  # filter out bad data
            result[key].append((sr_f, yb_f))
    return dict(result)


# ---------------------------------------------------------------------------
# PnL / drawdown / clustered losses / stats (identical formulas)
# ---------------------------------------------------------------------------

def _compute_pnl_usd(entry_price: float, c_size: float, price: float) -> float | None:
    if c_size <= 0.0 or entry_price <= 0.0:
        return None
    return round((price - entry_price) * (c_size / entry_price), 8)


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
# Per-position lifecycle simulation
# ---------------------------------------------------------------------------

def _simulate_lifecycle(
    entry_price:     float,
    shadow_size:     float,
    entry_sr:        float,
    all_snaps:       list[tuple[float, float]],  # (sr, yes_bid) full epoch
    settlement_price: float | None,              # None = unresolved
    policy:          dict[str, Any],
) -> dict[str, Any]:
    """
    Simulate one lifecycle policy for a single position.

    No future leakage: only snapshots with SR < entry_sr are used (after entry).
    Snapshots are processed SR-descending = chronological (earlier SR = later time).

    Returns a dict with PnL components, diagnostic flags, and regret metrics.
    """
    # Filter to post-entry snapshots only (no future leakage)
    timeline = sorted(
        [(sr, yb) for sr, yb in all_snaps if sr < entry_sr],
        key=lambda s: -s[0],   # SR descending = chronological order
    )

    tokens_total = shadow_size / max(entry_price, 1e-9)

    reduce_fraction  = 0.0
    reduce_price:    float | None = None
    reduce_sr:       float | None = None
    forced_derisk    = False
    late_decay_avoided = False

    policy_name = policy["name"]

    # ------------------------------------------------------------------
    # Policy A: no action
    # ------------------------------------------------------------------
    if policy_name == "A_baseline_hold_to_settlement":
        pass  # all defaults

    # ------------------------------------------------------------------
    # Policy B & C: partial reduce at N × entry_price
    # ------------------------------------------------------------------
    elif policy_name in ("B_partial_reduce_50pct_at_2x", "C_partial_reduce_50pct_at_3x"):
        threshold_price  = entry_price * policy["threshold_mult"]
        reduce_frac_cfg  = policy["reduce_fraction"]
        for sr, yes_bid in timeline:
            if yes_bid >= threshold_price:
                reduce_fraction = reduce_frac_cfg
                reduce_price    = yes_bid
                reduce_sr       = sr
                break

    # ------------------------------------------------------------------
    # Policy D: close all at first snapshot with SR < derisk threshold
    # ------------------------------------------------------------------
    elif policy_name == "D_dynamic_derisk_before_close":
        sr_thr = policy["derisk_sr_threshold"]
        for sr, yes_bid in timeline:
            if sr < sr_thr:
                reduce_fraction = 1.0
                reduce_price    = yes_bid
                reduce_sr       = sr
                forced_derisk   = True
                break

    # ------------------------------------------------------------------
    # Policy E: hold winners, cut late decay
    # ------------------------------------------------------------------
    elif policy_name == "E_hold_winners_cut_late_decay":
        decay_thr  = policy["decay_threshold"]
        decay_sr_w = policy["decay_sr_window"]
        peak_min   = policy["peak_min"]
        red_frac   = policy["reduce_fraction"]
        max_yb     = 0.0
        for sr, yes_bid in timeline:
            max_yb = max(max_yb, yes_bid)
            if (not late_decay_avoided
                    and sr < decay_sr_w
                    and max_yb >= peak_min
                    and max_yb > 1e-9
                    and (max_yb - yes_bid) / max_yb > decay_thr):
                reduce_fraction    = red_frac
                reduce_price       = yes_bid
                reduce_sr          = sr
                late_decay_avoided = True
                break

    # ------------------------------------------------------------------
    # Compute PnL components
    # ------------------------------------------------------------------
    tokens_reduced = round(tokens_total * reduce_fraction, 8)
    tokens_runner  = round(tokens_total * (1.0 - reduce_fraction), 8)

    # Partial / full reduce PnL
    reduce_pnl = 0.0
    if reduce_price is not None and tokens_reduced > 0:
        reduce_pnl = round((reduce_price - entry_price) * tokens_reduced, 8)

    # Runner PnL (held fraction, settled at settlement_price)
    runner_pnl: float | None = None
    if tokens_runner == 0.0:
        runner_pnl = 0.0
    elif settlement_price is not None:
        runner_pnl = round((settlement_price - entry_price) * tokens_runner, 8)

    # Total
    total_pnl: float | None = None
    if runner_pnl is not None:
        total_pnl = round(reduce_pnl + runner_pnl, 8)

    # Premature reduce regret:
    # (settlement - reduce_price) × tokens_reduced
    # positive  = left money on table (reduced before a YES settlement)
    # negative  = benefited from early exit (avoided a NO loss)
    premature_regret: float | None = None
    if reduce_price is not None and settlement_price is not None and tokens_reduced > 0:
        premature_regret = round(
            (settlement_price - reduce_price) * tokens_reduced, 8
        )

    # False decay trigger: Policy E fired but epoch settled YES
    false_decay_trigger = (
        late_decay_avoided
        and settlement_price is not None
        and settlement_price >= _YES_THRESHOLD
    )

    return {
        "total_pnl":               total_pnl,
        "reduce_pnl":              round(reduce_pnl, 8),
        "runner_pnl":              runner_pnl,
        "reduce_price":            reduce_price,
        "reduce_sr":               reduce_sr,
        "reduce_fraction":         reduce_fraction,
        "tokens_total":            round(tokens_total, 6),
        "tokens_reduced":          round(tokens_reduced, 6),
        "tokens_runner":           round(tokens_runner, 6),
        "forced_derisk":           forced_derisk,
        "late_decay_avoided":      late_decay_avoided,
        "premature_reduce_regret": premature_regret,
        "false_decay_trigger":     false_decay_trigger,
    }


# ---------------------------------------------------------------------------
# Policy simulation (inventory continuity: max 1/asset/epoch)
# ---------------------------------------------------------------------------

def simulate_lifecycle_policy(
    events:          list[dict[str, Any]],
    settlement_map:  dict[tuple[Any, str], dict[str, Any]],
    epoch_timelines: dict[tuple[Any, str], list[tuple[float, float]]],
    policy:          dict[str, Any],
    bankroll_ref:    float = 20.0,
) -> list[dict[str, Any]]:
    """
    Run one lifecycle policy with max-1-position-per-asset inventory constraint.

    Returns a list of position records (one per simulated entry).
    """
    # Group events by (epoch_ts, market_key); sort within epoch by SR descending
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

    asset_entered_this_epoch: dict[str, Any] = {}   # asset -> True/False per epoch
    positions: list[dict[str, Any]] = []

    # Track which epoch_ts we're currently processing to reset per-epoch state
    prev_epoch_ts = None

    for epoch_key in sorted_keys:
        ep_ts, mk = epoch_key
        epoch_events = epoch_groups[epoch_key]
        asset = _asset_from_event(epoch_events[0])

        # New epoch_ts: reset per-epoch asset tracking
        if ep_ts != prev_epoch_ts:
            asset_entered_this_epoch = {}
            prev_epoch_ts = ep_ts

        # Max 1 position per asset per epoch: skip if already entered
        if asset_entered_this_epoch.get(asset):
            continue

        # Find first shadow-nonzero event in this epoch
        entry_event = None
        for p in epoch_events:
            shadow = _compute_shadow(p)
            if shadow["nonzero"]:
                entry_event = p
                break
        if entry_event is None:
            continue

        # Mark entered
        asset_entered_this_epoch[asset] = True

        shadow = _compute_shadow(entry_event)
        entry_price = float(entry_event.get("entry_price") or 0.0)
        entry_sr    = float(entry_event.get("seconds_remaining") or 0.0)

        # Get settlement
        sett = settlement_map.get(epoch_key)
        settlement_price: float | None = None
        settlement_label = "NO_SNAPSHOT"
        unresolved = True
        if sett and sett["confidence"] == "HIGH":
            settlement_price  = sett["settlement_price"]
            settlement_label  = sett["inferred_settlement"]
            unresolved        = False
        elif sett and sett["confidence"] == "AMBIGUOUS":
            settlement_label = "AMBIGUOUS"

        # Get epoch timeline for lifecycle decisions
        all_snaps = epoch_timelines.get(epoch_key) or []

        # Run lifecycle simulation
        lc = _simulate_lifecycle(
            entry_price=entry_price,
            shadow_size=shadow["c_size"],
            entry_sr=entry_sr,
            all_snaps=all_snaps,
            settlement_price=settlement_price,
            policy=policy,
        )

        positions.append({
            "asset":                    asset,
            "market_key":               mk,
            "epoch_start_ts":           ep_ts,
            "entry_price":              entry_price,
            "shadow_size_usd":          shadow["c_size"],
            "shadow_pct_bankroll":      shadow["pct_bankroll"],
            "entry_sr":                 entry_sr,
            "settlement":               settlement_label,
            "settlement_price":         settlement_price,
            "unresolved":               unresolved,
            **lc,
        })

    return positions


# ---------------------------------------------------------------------------
# Per-policy report
# ---------------------------------------------------------------------------

def _policy_report(
    positions:    list[dict[str, Any]],
    policy:       dict[str, Any],
    bankroll_ref: float,
    baseline_pnl: float,
) -> dict[str, Any]:
    total_entries = len(positions)
    settled       = [p for p in positions if p.get("total_pnl") is not None]
    pnl_vals      = [p["total_pnl"] for p in settled]
    realized_pnl  = round(sum(pnl_vals), 8) if pnl_vals else 0.0
    pnl_uplift    = round(realized_pnl - baseline_pnl, 8)

    # Runner contribution (sum of runner_pnl from positions that had a reduce)
    runner_vals = [
        p["runner_pnl"] for p in settled
        if p.get("reduce_fraction", 0) > 0 and p.get("runner_pnl") is not None
    ]
    runner_contrib = round(sum(runner_vals), 8) if runner_vals else 0.0

    # Premature reduce regret
    regret_vals = [
        p["premature_reduce_regret"] for p in settled
        if p.get("premature_reduce_regret") is not None
    ]
    premature_regret_total = round(sum(regret_vals), 8) if regret_vals else 0.0

    # False decay triggers (Policy E only)
    false_decay_count = sum(1 for p in positions if p.get("false_decay_trigger"))

    # Forced derisk / late decay avoided
    forced_derisk_count      = sum(1 for p in positions if p.get("forced_derisk"))
    late_decay_avoided_count = sum(1 for p in positions if p.get("late_decay_avoided"))

    # Exposure
    epoch_ts_exp: dict[Any, float] = defaultdict(float)
    for p in positions:
        epoch_ts_exp[p["epoch_start_ts"]] += p["shadow_pct_bankroll"]
    max_exp_pct = round(max(epoch_ts_exp.values(), default=0.0), 4)

    # Max concurrent
    epoch_ts_assets: dict[Any, set[str]] = defaultdict(set)
    for p in positions:
        epoch_ts_assets[p["epoch_start_ts"]].add(p["asset"])
    max_concurrent = max((len(a) for a in epoch_ts_assets.values()), default=0)

    # Drawdown (sort by epoch_ts)
    sorted_settled = sorted(settled, key=lambda p: (p.get("epoch_start_ts") or 0, p.get("market_key") or ""))
    max_dd = _max_drawdown([p["total_pnl"] for p in sorted_settled])
    dd_pct = round(max_dd / bankroll_ref * 100, 2) if bankroll_ref > 0 else 0.0

    # Win rate
    wins   = sum(1 for v in pnl_vals if v > 0)
    losses = sum(1 for v in pnl_vals if v < 0)
    wr     = _pct(wins, len(settled))
    avg_win  = round(mean([v for v in pnl_vals if v > 0]), 6) if wins   else None
    avg_loss = round(mean([v for v in pnl_vals if v < 0]), 6) if losses else None

    # Clustered losses
    cluster_info = _clustered_losses(sorted_settled)

    # BTC / ETH
    def _asset_report(asset: str) -> dict[str, Any]:
        sub  = [p for p in settled if p["asset"] == asset]
        vals = [p["total_pnl"] for p in sub]
        w    = [v for v in vals if v > 0]
        return {
            "entries":       len([p for p in positions if p["asset"] == asset]),
            "settled_fills": len(sub),
            "total_pnl":     round(sum(vals), 8) if vals else 0.0,
            "win_rate_pct":  _pct(len(w), len(sub)),
            "pnl_stats":     _stats(vals),
        }

    # Avg entry SR
    entry_srs = [p["entry_sr"] for p in positions]
    avg_entry_sr = round(mean(entry_srs), 1) if entry_srs else 0.0

    # Verdict
    if dd_pct > _UNSAFE_DRAWDOWN_PCT:
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
    elif abs(pnl_uplift) < _NO_IMPROVEMENT_USD:
        verdict = "no_material_improvement"
        verdict_note = (
            f"PnL uplift ${pnl_uplift:+.4f} is within the ${_NO_IMPROVEMENT_USD} "
            "no-material-improvement band."
        )
    else:
        verdict = "safe_candidate"
        verdict_note = (
            f"Uplift ${pnl_uplift:+.4f}, drawdown ${max_dd:.4f} ({dd_pct:.1f}%), "
            f"win rate {wr:.1f}%, entries {total_entries}. "
            "Policy is safe-bounded and shows material improvement over baseline."
        )

    return {
        "policy_name":               policy["name"],
        "policy_label":              policy["label"],
        # 1
        "realized_proxy_pnl":        realized_pnl,
        "settled_fill_count":        len(settled),
        "pnl_stats":                 _stats(pnl_vals),
        # 2
        "pnl_uplift_vs_baseline_usd": pnl_uplift,
        # 3
        "max_drawdown":              max_dd,
        "max_drawdown_pct_bankroll": dd_pct,
        # 4
        "win_rate_pct":              wr,
        "win_count":                 wins,
        "loss_count":                losses,
        # 5
        "avg_win":                   avg_win,
        "avg_loss":                  avg_loss,
        # 6
        "realized_runner_contribution_usd": runner_contrib,
        # 7
        "forced_derisk_count":       forced_derisk_count,
        # 8
        "late_window_decay_avoided_count": late_decay_avoided_count,
        # 9
        "btc":                       _asset_report("BTC"),
        "eth":                       _asset_report("ETH"),
        # 10
        "max_exposure_pct":          max_exp_pct,
        "max_concurrent_positions":  max_concurrent,
        # 11
        "clustered_loss_periods":    cluster_info,
        # 12
        "avg_entry_sr":              avg_entry_sr,
        # 13
        "verdict":                   verdict,
        "verdict_note":              verdict_note,
        # Additional diagnostics
        "premature_reduce_regret_usd": premature_regret_total,
        "false_decay_trigger_count":   false_decay_count,
        "unresolved_count":            sum(1 for p in positions if p.get("unresolved")),
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
            "error": "no_zero_size_probe_v1_events_found",
            "guardrail": "offline-only; no runtime changes",
        }

    total_events = len(events)
    bankroll_ref = 20.0
    for p in events:
        b = p.get("bankroll")
        if b:
            bankroll_ref = float(b)
            break

    unsafe_dd_usd = round(bankroll_ref * _UNSAFE_DRAWDOWN_PCT / 100.0, 4)

    # Run Policy A first to establish baseline PnL
    pos_a    = simulate_lifecycle_policy(events, settlement_map, epoch_timelines, POLICIES[0], bankroll_ref)
    report_a = _policy_report(pos_a, POLICIES[0], bankroll_ref, baseline_pnl=0.0)
    baseline_pnl = report_a["realized_proxy_pnl"]

    # Run remaining policies
    policy_reports: list[dict[str, Any]] = [report_a]
    for policy in POLICIES[1:]:
        pos    = simulate_lifecycle_policy(events, settlement_map, epoch_timelines, policy, bankroll_ref)
        report = _policy_report(pos, policy, bankroll_ref, baseline_pnl)
        policy_reports.append(report)

    # Comparison
    safe     = [r for r in policy_reports if r["verdict"] == "safe_candidate"]
    best_pnl = max(policy_reports, key=lambda r: r["realized_proxy_pnl"])
    best_safe_pnl = max(safe, key=lambda r: r["realized_proxy_pnl"]) if safe else None

    comparison_rows = [
        {
            "policy":         r["policy_label"],
            "entries":        r["settled_fill_count"],
            "realized_pnl":   r["realized_proxy_pnl"],
            "uplift_usd":     r["pnl_uplift_vs_baseline_usd"],
            "max_dd":         r["max_drawdown"],
            "win_rate":       r["win_rate_pct"],
            "regret_usd":     r["premature_reduce_regret_usd"],
            "false_decay":    r["false_decay_trigger_count"],
            "verdict":        r["verdict"],
        }
        for r in policy_reports
    ]

    if best_safe_pnl:
        recommended = best_safe_pnl["policy_label"]
        rec_note = (
            f"'{recommended}' is the safe policy with the best proxy PnL. "
            "Validate over more sessions before any runtime consideration. "
            "Do NOT promote to runtime without a separately scoped Phase 3 implementation."
        )
    else:
        recommended = "A_baseline_hold_to_settlement (no lifecycle policy reached safe_candidate)"
        rec_note = "No lifecycle policy improved on baseline safely. Keep Policy A."

    return {
        "event_count":         total_events,
        "bankroll_ref":        bankroll_ref,
        "unsafe_dd_usd":       unsafe_dd_usd,
        "policy_A":            policy_reports[0],
        "policy_B":            policy_reports[1],
        "policy_C":            policy_reports[2],
        "policy_D":            policy_reports[3],
        "policy_E":            policy_reports[4],
        "policy_comparison": {
            "rows":             comparison_rows,
            "best_pnl_policy":  best_pnl["policy_label"],
            "best_safe_policy": best_safe_pnl["policy_label"] if best_safe_pnl else "none",
            "recommended":      recommended,
            "recommended_note": rec_note,
        },
        "simulation_rules": [
            "Max 1 position per asset per epoch (no reloads).",
            "No future leakage: decisions use only snapshots with SR < entry_SR.",
            "Policy B: reduce 50% at first yes_bid >= 2x entry_price.",
            "Policy C: reduce 50% at first yes_bid >= 3x entry_price.",
            f"Policy D: close 100% at first snapshot with SR < {_DERISK_SR}s.",
            f"Policy E: reduce 50% when yes_bid drops >{_DECAY_THRESHOLD*100:.0f}% from peak "
            f"AND SR < {_DECAY_SR_WINDOW}s AND peak was >= {_DECAY_PEAK_MIN}.",
            "premature_reduce_regret = (settlement - reduce_price) * tokens_reduced.",
            "false_decay_trigger = Policy E fired AND epoch settled YES.",
            "Settlement inferred from market_snapshots yes_bid near close (proxy, not confirmed).",
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

SEP  = "=" * 72
SEP2 = "-" * 72


def _print_policy_section(r: dict[str, Any], bankroll_ref: float) -> None:
    print(f"\n{SEP2}")
    print(f"  {r['policy_label']}")
    print(f"{SEP2}")
    print(f"  Settled fills       : {r['settled_fill_count']}")
    print(f"\n  [PnL]")
    print(f"  Realized proxy PnL  : ${r['realized_proxy_pnl']:.4f}")
    print(f"  Uplift vs baseline  : ${r['pnl_uplift_vs_baseline_usd']:+.4f}")
    print(f"  Runner contribution : ${r['realized_runner_contribution_usd']:.4f}")
    print(f"  Win rate            : {r['win_rate_pct']:.1f}%  ({r['win_count']}W / {r['loss_count']}L)")
    aw = r.get("avg_win"); al = r.get("avg_loss")
    print(f"  Avg win / loss      : {'$%.4f' % aw if aw is not None else 'N/A'} / "
          f"{'$%.4f' % al if al is not None else 'N/A'}")

    print(f"\n  [Regret & Decay Diagnostics]")
    print(f"  Premature regret    : ${r['premature_reduce_regret_usd']:.4f}  "
          f"(+ve=left on table, -ve=avoided loss)")
    print(f"  False decay triggers: {r['false_decay_trigger_count']}  (E only: YES won but cut)")
    print(f"  Forced derisks      : {r['forced_derisk_count']}")
    print(f"  Late decay avoided  : {r['late_window_decay_avoided_count']}")

    print(f"\n  [Risk]")
    print(f"  Max exposure        : {r['max_exposure_pct']:.2f}%")
    print(f"  Max drawdown        : ${r['max_drawdown']:.4f} ({r['max_drawdown_pct_bankroll']:.1f}% bankroll)")
    cl = r.get("clustered_loss_periods") or {}
    print(f"  Max consec losses   : {cl.get('max_consecutive_losses',0)}  "
          f"(clusters: {cl.get('loss_cluster_count',0)})")
    print(f"  Avg entry SR        : {r['avg_entry_sr']:.0f}s remaining")

    print(f"\n  [BTC / ETH]")
    for label, key in [("BTC", "btc"), ("ETH", "eth")]:
        a  = r.get(key) or {}
        p2 = a.get("pnl_stats") or {}
        if a.get("entries", 0) == 0:
            print(f"  {label}: no entries")
            continue
        print(f"  {label}: entries={a['entries']}  settled={a['settled_fills']}  "
              f"pnl=${a['total_pnl']:.4f}  wr={a['win_rate_pct']:.1f}%  "
              f"mean=${p2.get('mean',0):.4f}")

    print(f"\n  [Verdict]  {r['verdict']}")
    print(f"  {r['verdict_note']}")


def print_report(result: dict[str, Any], date_str: str) -> None:
    if "error" in result:
        print(f"\n{SEP}")
        print(f"  Lifecycle Profit Management Replay v1  |  {date_str}")
        print(f"{SEP}")
        print(f"  ERROR: {result['error']}")
        print(f"{SEP}\n")
        return

    print(f"\n{SEP}")
    print(f"  Lifecycle Profit Management Replay v1  |  {date_str}")
    print(f"{SEP}")
    print(f"  Total events        : {result['event_count']}")
    print(f"  Bankroll ref        : ${result['bankroll_ref']:.2f}")
    print(f"  Unsafe drawdown USD : ${result['unsafe_dd_usd']:.2f} (={_UNSAFE_DRAWDOWN_PCT}% bankroll)")

    for key in ("policy_A", "policy_B", "policy_C", "policy_D", "policy_E"):
        r = result.get(key)
        if r:
            _print_policy_section(r, result["bankroll_ref"])

    print(f"\n{SEP}")
    print(f"  POLICY COMPARISON SUMMARY")
    print(f"{SEP}")
    print(f"  {'Policy':<35} {'Settled':>7} {'PnL':>9} {'Uplift':>8} "
          f"{'MaxDD':>7} {'WR%':>5} {'Regret':>8} {'FalseDcy':>8}  Verdict")
    print(f"  {'-'*35} {'-'*7} {'-'*9} {'-'*8} {'-'*7} {'-'*5} {'-'*8} {'-'*8}  {'-'*20}")
    for row in result.get("policy_comparison", {}).get("rows", []):
        print(
            f"  {row['policy']:<35} {row['entries']:>7} "
            f"${row['realized_pnl']:>8.2f} ${row['uplift_usd']:>+7.2f} "
            f"${row['max_dd']:>6.2f} {row['win_rate']:>4.1f}% "
            f"${row['regret_usd']:>+7.2f} {row['false_decay']:>8}  {row['verdict']}"
        )
    pc = result.get("policy_comparison") or {}
    print(f"\n  Best PnL policy     : {pc.get('best_pnl_policy','?')}")
    print(f"  Best safe policy    : {pc.get('best_safe_policy','?')}")
    print(f"  Recommended         : {pc.get('recommended','?')}")
    print(f"  {pc.get('recommended_note','')}")

    print(f"\n  guardrail: {result.get('guardrail','')}")
    print(f"{SEP}\n")


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(result: dict[str, Any], date_str: str, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now(tz=timezone.utc).strftime("%H%M")
    path = report_dir / f"lifecycle_pm_{date_str}_{ts}.json"
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
        description="Lifecycle Profit Management Replay v1 -- offline-only"
    )
    parser.add_argument("--date", required=True)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--asset", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    qd = Path(args.quant_data_dir)
    events = load_probe_events(args.date, quant_data_dir=qd,
                                run_id=args.run_id, asset_filter=args.asset)

    probe_epoch_keys: set[tuple[Any, str]] = set()
    for p in events:
        ep = p.get("epoch_start_ts"); mk = p.get("market_key")
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
