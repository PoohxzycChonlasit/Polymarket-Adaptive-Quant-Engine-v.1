"""
Semantic C Bounded Reload Opportunity Replay v1 -- offline replay tool.

Measures whether a strictly capped reload policy can recover part of the
$323.33 skipped opportunity cost from the inventory continuity replay without
creating unsafe exposure or drawdown.

Inventory continuity baseline (2026-05-15):
  simulated_entries            :  70
  skipped_due_to_inventory     : 251
  skipped_profitable_candidates: 148
  skipped_opportunity_cost_usd : $323.33
  realized_proxy_pnl           : $62.45  (Policy A / no reload)
  max_concurrent_positions     :   2
  max_total_exposure_pct       :   5.01%
  max_drawdown                 :   $1.93

Four reload policies are simulated and compared:
  A  baseline_one_position   max 1 per asset per epoch (matches continuity replay)
  B  reload_2_per_asset      max 2 per asset per epoch
  C  reload_3_per_asset      max 3 per asset per epoch
  D  exposure_capped_reload  unlimited reloads while total exposure <= 7.5% bankroll

CRITICAL CAVEAT:
  All reload positions within the same epoch share the SAME settlement outcome.
  Reloads in a single epoch are concentrated exposure, NOT diversification.
  If the epoch settles NO, every reload position loses.  Max drawdown scales
  with position count per epoch, not just entry count.

Data sources (local JSONL only -- no live API calls):
  runtime/quant_data/system_health/YYYY-MM-DD.jsonl    (zero_size_probe_v1)
  runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl  (settlement proxy)

Settlement inference:
  yes_bid >= 0.70  ->  YES  (settlement_price=1.0, HIGH confidence)
  yes_bid <= 0.30  ->  NO   (settlement_price=0.0, HIGH confidence)
  otherwise        ->  AMBIGUOUS (excluded from PnL)

PnL formula:
  tokens = shadow_size_usd / entry_price
  pnl    = (settlement_price - entry_price) * tokens

Usage:
  python -m tools.semantic_c_bounded_reload_replay --date 2026-05-15
  python -m tools.semantic_c_bounded_reload_replay --date 2026-05-15 --write-report
  python -m tools.semantic_c_bounded_reload_replay --date 2026-05-15 --run-id <id>
  python -m tools.semantic_c_bounded_reload_replay --date 2026-05-15 --asset BTC

Output:
  Console summary + optional runtime/reports/sem_c_reload_YYYY-MM-DD_HHMM.json

Per-policy report (13 outputs per policy):
   1.  entries
   2.  skipped_candidates
   3.  captured_opportunity_cost_usd  (PnL from reload positions only)
   4.  realized_proxy_pnl
   5.  pnl_uplift_vs_baseline_usd
   6.  max_exposure_pct
   7.  max_concurrent_positions
   8.  max_drawdown
   9.  win_rate_pct
  10.  clustered_loss_periods
  11.  btc_eth_contribution
  12.  cutoff_collision_rate_pct
  13.  verdict

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
_UNSAFE_EXPOSURE_PCT  = 10.0   # max_total_exposure_pct >= this -> unsafe_exposure
_UNSAFE_DRAWDOWN_PCT  = 10.0   # max_drawdown > this% of bankroll_ref -> unsafe_drawdown
_CAUTION_LOSS_CLUSTER = 6      # max_consecutive_losses > this -> caution
_CAUTION_CUTOFF_PCT   = 10.0   # cutoff_collision_rate_pct > this -> caution
_NEEDS_MORE_ENTRIES   = 10
_NEEDS_MORE_WIN_RATE  = 40.0

# Exposure cap for Policy D
_POLICY_D_EXPOSURE_CAP = 7.5   # %

# Cutoff threshold: entries with seconds_remaining < this are "near close"
_CUTOFF_SR = 90.0

# Reload policies
POLICIES: list[dict[str, Any]] = [
    {"name": "A_baseline_one_position",  "label": "A  baseline (1/asset/epoch)",
     "max_per_asset": 1,    "exposure_cap_pct": None},
    {"name": "B_reload_2_per_asset",     "label": "B  reload-2 (2/asset/epoch)",
     "max_per_asset": 2,    "exposure_cap_pct": None},
    {"name": "C_reload_3_per_asset",     "label": "C  reload-3 (3/asset/epoch)",
     "max_per_asset": 3,    "exposure_cap_pct": None},
    {"name": "D_exposure_capped_reload", "label": "D  exp-capped (<=7.5% total)",
     "max_per_asset": None, "exposure_cap_pct": _POLICY_D_EXPOSURE_CAP},
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


# ---------------------------------------------------------------------------
# Settlement map
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# PnL / drawdown / clustered losses (identical formulas to other tools)
# ---------------------------------------------------------------------------

def _compute_pnl(entry_price: float, c_size: float, settlement_price: float) -> float | None:
    if c_size <= 0.0 or entry_price <= 0.0:
        return None
    return round((settlement_price - entry_price) * (c_size / entry_price), 8)


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
    max_run = cur = n_clusters = total_cluster_eps = 0
    for rec in sorted_records:
        pnl = rec.get("pnl")
        if pnl is not None and pnl < 0:
            cur += 1
            if cur > max_run:
                max_run = cur
        else:
            if cur >= 2:
                n_clusters += 1
                total_cluster_eps += cur
            cur = 0
    if cur >= 2:
        n_clusters += 1
        total_cluster_eps += cur
    return {
        "max_consecutive_losses":    max_run,
        "loss_cluster_count":        n_clusters,
        "total_loss_cluster_epochs": total_cluster_eps,
    }


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
# Core reload simulation
# ---------------------------------------------------------------------------

def simulate_reload_policy(
    events: list[dict[str, Any]],
    settlement_map: dict[tuple[Any, str], dict[str, Any]],
    policy: dict[str, Any],
    bankroll_ref: float = 20.0,
) -> dict[str, Any]:
    """
    Simulate one reload policy over sorted probe events.

    policy keys:
      max_per_asset      int or None  (None = no count cap, rely on exposure_cap)
      exposure_cap_pct   float or None (None = no exposure cap)

    Returns:
      positions    list of position dicts (one per fill taken)
      skipped      list of skipped event dicts
      concurrent_log list of {epoch_start_ts, concurrent_count}
    """
    max_cap  = policy["max_per_asset"]
    exp_cap  = policy["exposure_cap_pct"]

    # Group events by (epoch_ts, market_key), sort within each epoch by SR desc
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

    positions: list[dict[str, Any]]    = []
    skipped:   list[dict[str, Any]]    = []

    # Running exposure per epoch_ts (sum of all positions at that timestamp)
    epoch_ts_exposure: dict[Any, float] = defaultdict(float)

    for epoch_key in sorted_keys:
        ep_ts, mk = epoch_key
        epoch_events = epoch_groups[epoch_key]
        asset = _asset_from_event(epoch_events[0])
        sett  = settlement_map.get(epoch_key)

        # Count positions already taken for this (epoch_ts, asset) in this pass
        taken_this_epoch_asset: list[dict[str, Any]] = []

        for p in epoch_events:
            shadow = _compute_shadow(p)
            if not shadow["nonzero"]:
                continue

            sr = float(p.get("seconds_remaining") or 0)
            candidate_pct = shadow["pct_bankroll"]

            # --- Count cap check ---
            if max_cap is not None and len(taken_this_epoch_asset) >= max_cap:
                skipped.append(_skip_record(p, asset, ep_ts, mk, shadow, sett, "count_cap"))
                continue

            # --- Exposure cap check ---
            if exp_cap is not None:
                current_ep_exposure = epoch_ts_exposure[ep_ts]
                if current_ep_exposure + candidate_pct > exp_cap:
                    skipped.append(_skip_record(p, asset, ep_ts, mk, shadow, sett, "exposure_cap"))
                    continue

            # --- Enter this position ---
            is_reload = len(taken_this_epoch_asset) > 0  # not the first position this epoch/asset
            entry_price = float(p.get("entry_price") or 0.0)

            # Compute PnL now if settlement is known (same settlement for all positions in epoch)
            pnl: float | None = None
            unresolved = False
            forced     = False
            settlement_label = "NO_SNAPSHOT"

            if sett and sett["confidence"] == "HIGH":
                pnl = _compute_pnl(entry_price, shadow["c_size"], sett["settlement_price"])
                settlement_label = sett["inferred_settlement"]
            elif sett and sett["confidence"] == "AMBIGUOUS":
                settlement_label = "AMBIGUOUS"
                unresolved = True
            else:
                forced     = True
                unresolved = True

            pos = {
                "asset":               asset,
                "market_key":          mk,
                "epoch_start_ts":      ep_ts,
                "entry_price":         entry_price,
                "shadow_size_usd":     shadow["c_size"],
                "shadow_pct_bankroll": candidate_pct,
                "entry_phase":         str(p.get("lifecycle_phase") or "UNKNOWN").upper(),
                "entry_sr":            sr,
                "is_reload":           is_reload,
                "settlement":          settlement_label,
                "pnl":                 pnl,
                "forced_close":        forced,
                "unresolved_close":    unresolved,
                "ev_positive":         bool(p.get("ev_positive")),
                "cutoff_collision":    sr < _CUTOFF_SR,
            }
            positions.append(pos)
            taken_this_epoch_asset.append(pos)
            epoch_ts_exposure[ep_ts] += candidate_pct

    # Build concurrent log: for each epoch_ts, count distinct assets with positions
    epoch_ts_assets: dict[Any, set[str]] = defaultdict(set)
    for pos in positions:
        epoch_ts_assets[pos["epoch_start_ts"]].add(pos["asset"])
    concurrent_log = [
        {"epoch_start_ts": ts, "concurrent_count": len(assets)}
        for ts, assets in epoch_ts_assets.items()
    ]

    return {"positions": positions, "skipped": skipped, "concurrent_log": concurrent_log}


def _skip_record(
    p: dict[str, Any],
    asset: str,
    ep_ts: Any,
    mk: str,
    shadow: dict[str, Any],
    sett: dict[str, Any] | None,
    reason: str,
) -> dict[str, Any]:
    return {
        "asset":             asset,
        "epoch_start_ts":   ep_ts,
        "market_key":       mk,
        "shadow_size_usd":  shadow["c_size"],
        "entry_price":      float(p.get("entry_price") or 0.0),
        "shadow_pct":       shadow["pct_bankroll"],
        "sr":               float(p.get("seconds_remaining") or 0),
        "ev_positive":      bool(p.get("ev_positive")),
        "skip_reason":      reason,
        "settlement":       sett["inferred_settlement"] if sett else None,
        "settlement_conf":  sett["confidence"] if sett else None,
        "settlement_price": sett["settlement_price"] if sett else None,
    }


# ---------------------------------------------------------------------------
# Per-policy report builder
# ---------------------------------------------------------------------------

def _policy_report(
    sim: dict[str, Any],
    policy: dict[str, Any],
    bankroll_ref: float,
    baseline_pnl: float,
) -> dict[str, Any]:
    positions      = sim["positions"]
    skipped        = sim["skipped"]
    concurrent_log = sim["concurrent_log"]

    total_entries  = len(positions)
    total_skipped  = len(skipped)

    # --- Settled / unresolved split ---
    settled = [p for p in positions if p["pnl"] is not None]
    settled_pnls   = [p["pnl"] for p in settled]
    realized_pnl   = round(sum(settled_pnls), 8) if settled_pnls else 0.0

    # --- Reload-specific PnL (captured opportunity cost) ---
    reload_settled = [p for p in settled if p["is_reload"]]
    reload_pnls    = [p["pnl"] for p in reload_settled]
    captured_opp   = round(sum(reload_pnls), 8) if reload_pnls else 0.0

    # --- Uplift vs baseline ---
    pnl_uplift = round(realized_pnl - baseline_pnl, 8)

    # --- Per-(epoch_ts, asset) grouping for correlated-exposure metrics ---
    epoch_asset_pos: dict[tuple[Any, str], list[dict[str, Any]]] = defaultdict(list)
    for pos in positions:
        epoch_asset_pos[(pos["epoch_start_ts"], pos["asset"])].append(pos)

    # Correlated exposure: all reloads in one epoch share the same settlement outcome.
    # If YES -> all win; if NO -> all lose.  NOT diversification.

    # same_epoch_reload_count: epochs where more than one position was taken per asset
    same_epoch_reload_count = sum(
        1 for poss in epoch_asset_pos.values() if len(poss) > 1
    )

    # max_reload_count_per_epoch: deepest concentration in any single (epoch, asset)
    max_reload_count_per_epoch = max(
        (len(poss) for poss in epoch_asset_pos.values()), default=0
    )

    # worst_losing_epoch_pnl: single-epoch total loss (most negative sum of positions)
    epoch_total_pnls = {
        key: sum(p["pnl"] for p in poss if p["pnl"] is not None)
        for key, poss in epoch_asset_pos.items()
    }
    worst_losing_epoch_pnl = min(epoch_total_pnls.values(), default=0.0)

    # exposure_concentration_by_epoch: distribution of per-(epoch,asset) exposure
    ep_exposure_vals = [
        sum(p["shadow_pct_bankroll"] for p in poss)
        for poss in epoch_asset_pos.values()
    ]
    exposure_concentration = _stats(ep_exposure_vals)

    # reload_loss_cluster_count: epochs that have reload positions AND net loss
    reload_loss_epochs = [
        key for key, poss in epoch_asset_pos.items()
        if any(p["is_reload"] for p in poss)
        and epoch_total_pnls.get(key, 0.0) < 0
    ]
    reload_loss_cluster_count = len(reload_loss_epochs)

    # --- Exposure ---
    epoch_ts_exp: dict[Any, float] = defaultdict(float)
    for pos in positions:
        epoch_ts_exp[pos["epoch_start_ts"]] += pos["shadow_pct_bankroll"]
    max_exposure_pct = round(max(epoch_ts_exp.values(), default=0.0), 4)

    # --- Max concurrent ---
    max_concurrent = max((c["concurrent_count"] for c in concurrent_log), default=0)

    # --- Max drawdown ---
    sorted_settled = sorted(settled, key=lambda p: (p.get("epoch_start_ts") or 0, p.get("market_key") or ""))
    max_dd = _max_drawdown([p["pnl"] for p in sorted_settled])

    # --- Win rate ---
    wins   = sum(1 for v in settled_pnls if v > 0)
    losses = sum(1 for v in settled_pnls if v < 0)
    win_rate = _pct(wins, len(settled))
    avg_win  = round(mean([v for v in settled_pnls if v > 0]), 6) if wins  else None
    avg_loss = round(mean([v for v in settled_pnls if v < 0]), 6) if losses else None

    # --- Clustered losses ---
    cluster_info = _clustered_losses(sorted_settled)

    # --- BTC / ETH contribution ---
    def _asset_contribution(asset: str) -> dict[str, Any]:
        sub  = [p for p in settled if p["asset"] == asset]
        vals = [p["pnl"] for p in sub]
        w    = [v for v in vals if v > 0]
        return {
            "entries":       len([p for p in positions if p["asset"] == asset]),
            "settled_fills": len(sub),
            "total_pnl":     round(sum(vals), 8) if vals else 0.0,
            "win_rate_pct":  _pct(len(w), len(sub)),
            "pnl_stats":     _stats(vals),
        }

    # --- Cutoff collision rate ---
    cutoff_entries = sum(1 for p in positions if p.get("cutoff_collision"))
    cutoff_rate    = _pct(cutoff_entries, total_entries)

    # --- Forced / unresolved ---
    forced_count     = sum(1 for p in positions if p.get("forced_close"))
    unresolved_count = sum(1 for p in positions if p.get("unresolved_close"))

    # --- Verdict ---
    unsafe_exp  = max_exposure_pct >= _UNSAFE_EXPOSURE_PCT
    drawdown_pct = (max_dd / bankroll_ref * 100) if bankroll_ref > 0 else 0.0
    unsafe_dd   = drawdown_pct > _UNSAFE_DRAWDOWN_PCT
    too_few     = total_entries < _NEEDS_MORE_ENTRIES
    low_wr      = win_rate < _NEEDS_MORE_WIN_RATE

    if unsafe_exp:
        verdict = "unsafe_exposure"
        verdict_note = (
            f"Max total exposure {max_exposure_pct:.2f}% >= {_UNSAFE_EXPOSURE_PCT}% threshold. "
            "Reload depth exceeds safe exposure limit."
        )
    elif unsafe_dd:
        verdict = "unsafe_drawdown"
        verdict_note = (
            f"Max drawdown ${max_dd:.4f} = {drawdown_pct:.1f}% of bankroll "
            f"(>{_UNSAFE_DRAWDOWN_PCT}% threshold). Reload depth creates unsafe loss trajectory."
        )
    elif too_few or low_wr:
        verdict = "needs_more_replay"
        verdict_note = (
            f"Entries={total_entries} (threshold >={_NEEDS_MORE_ENTRIES}) or "
            f"win_rate={win_rate:.1f}% (threshold >={_NEEDS_MORE_WIN_RATE}%). "
            "Collect more evidence before assessing this reload depth."
        )
    else:
        cautions = []
        if cluster_info["max_consecutive_losses"] > _CAUTION_LOSS_CLUSTER:
            cautions.append(f"max_consecutive_losses={cluster_info['max_consecutive_losses']}")
        if cutoff_rate > _CAUTION_CUTOFF_PCT:
            cautions.append(f"cutoff_rate={cutoff_rate:.1f}%")
        verdict = "safe_candidate"
        verdict_note = (
            f"Exposure {max_exposure_pct:.2f}%, drawdown ${max_dd:.4f} ({drawdown_pct:.1f}%), "
            f"win rate {win_rate:.1f}%, entries {total_entries}. "
            + (f"Caution: {'; '.join(cautions)}. " if cautions else "")
            + "Evidence is compatible with a scoped bounded reload paper trial. "
            "Do NOT promote to live without a separately scoped Phase 3 implementation."
        )

    return {
        "policy_name":              policy["name"],
        "policy_label":             policy["label"],
        "max_per_asset":            policy["max_per_asset"],
        "exposure_cap_pct":         policy["exposure_cap_pct"],
        # 1
        "entries":                  total_entries,
        # 2
        "skipped_candidates":       total_skipped,
        # 3
        "captured_opportunity_cost_usd":   captured_opp,
        "reload_entries":           len(reload_settled),
        # 4
        "realized_proxy_pnl":       realized_pnl,
        "settled_fill_count":       len(settled),
        "pnl_stats":                _stats(settled_pnls),
        # 5
        "pnl_uplift_vs_baseline_usd": pnl_uplift,
        # 6
        "max_exposure_pct":         max_exposure_pct,
        # 7
        "max_concurrent_positions": max_concurrent,
        # 8
        "max_drawdown":             max_dd,
        "max_drawdown_pct_bankroll": round(drawdown_pct, 2),
        # 9
        "win_rate_pct":             win_rate,
        "win_count":                wins,
        "loss_count":               losses,
        "avg_win":                  avg_win,
        "avg_loss":                 avg_loss,
        # 10
        "clustered_loss_periods":   cluster_info,
        # 11
        "btc":                      _asset_contribution("BTC"),
        "eth":                      _asset_contribution("ETH"),
        # 12
        "cutoff_collision_rate_pct": cutoff_rate,
        "cutoff_entry_count":       cutoff_entries,
        # 13
        "verdict":                  verdict,
        "verdict_note":             verdict_note,
        # Correlated exposure (reload concentration risk -- NOT diversification)
        "correlated_exposure": {
            "same_epoch_reload_count":         same_epoch_reload_count,
            "max_reload_count_per_epoch":      max_reload_count_per_epoch,
            "worst_losing_epoch_pnl":          round(worst_losing_epoch_pnl, 6),
            "exposure_concentration_by_epoch": exposure_concentration,
            "reload_loss_cluster_count":       reload_loss_cluster_count,
            "warning": (
                "Reloads in the same epoch share the same settlement outcome. "
                "These are correlated positions, not independent diversification. "
                "worst_losing_epoch_pnl is the single worst-epoch concentrated loss."
            ),
        },
        # Diagnostics
        "forced_close_count":       forced_count,
        "unresolved_close_count":   unresolved_count,
    }


# ---------------------------------------------------------------------------
# Core analysis: run all policies and compare
# ---------------------------------------------------------------------------

def analyse(
    events: list[dict[str, Any]],
    settlement_map: dict[tuple[Any, str], dict[str, Any]],
) -> dict[str, Any]:
    """
    Run all four reload policies and produce a comparative report.

    No runtime imports; no side effects on inputs.
    """
    if not events:
        return {
            "event_count": 0,
            "error": "no_zero_size_probe_v1_events_found",
            "guardrail": "offline-only; no runtime changes",
        }

    total_events = len(events)

    # Derive bankroll reference from first event
    bankroll_ref = 20.0
    for p in events:
        b = p.get("bankroll")
        if b:
            bankroll_ref = float(b)
            break

    unsafe_drawdown_usd = round(bankroll_ref * _UNSAFE_DRAWDOWN_PCT / 100.0, 4)

    # Run Policy A first to get baseline PnL
    sim_a = simulate_reload_policy(events, settlement_map, POLICIES[0], bankroll_ref)
    report_a = _policy_report(sim_a, POLICIES[0], bankroll_ref, baseline_pnl=0.0)
    baseline_pnl = report_a["realized_proxy_pnl"]

    # Run remaining policies with baseline_pnl reference
    policy_reports: list[dict[str, Any]] = [report_a]
    for policy in POLICIES[1:]:
        sim    = simulate_reload_policy(events, settlement_map, policy, bankroll_ref)
        report = _policy_report(sim, policy, bankroll_ref, baseline_pnl)
        policy_reports.append(report)

    # --- Policy comparison block ---
    safe_policies   = [r for r in policy_reports if r["verdict"] == "safe_candidate"]
    best_pnl_policy = max(policy_reports, key=lambda r: r["realized_proxy_pnl"])
    best_safe_pnl   = max(safe_policies, key=lambda r: r["realized_proxy_pnl"]) if safe_policies else None

    comparison_rows = []
    for r in policy_reports:
        comparison_rows.append({
            "policy":         r["policy_label"],
            "entries":        r["entries"],
            "realized_pnl":   r["realized_proxy_pnl"],
            "uplift_usd":     r["pnl_uplift_vs_baseline_usd"],
            "max_exp_pct":    r["max_exposure_pct"],
            "max_dd":         r["max_drawdown"],
            "win_rate":       r["win_rate_pct"],
            "verdict":        r["verdict"],
        })

    # Recommendation: safest policy with best PnL
    if best_safe_pnl:
        recommended = best_safe_pnl["policy_label"]
        recommended_note = (
            f"'{recommended}' is the highest-PnL safe_candidate policy. "
            "It may be suitable for a bounded paper experiment. "
            "Do NOT wire into runtime without a Phase 3 implementation."
        )
    else:
        recommended = "A_baseline_one_position (all reload policies need more data or are unsafe)"
        recommended_note = "No reload policy reached safe_candidate status. Keep Policy A (baseline)."

    return {
        "event_count":             total_events,
        "bankroll_ref":            bankroll_ref,
        "unsafe_drawdown_usd":     unsafe_drawdown_usd,
        # Individual policy reports
        "policy_A": policy_reports[0],
        "policy_B": policy_reports[1],
        "policy_C": policy_reports[2],
        "policy_D": policy_reports[3],
        # Comparison
        "policy_comparison": {
            "rows":              comparison_rows,
            "best_pnl_policy":   best_pnl_policy["policy_label"],
            "best_safe_policy":  best_safe_pnl["policy_label"] if best_safe_pnl else "none",
            "recommended":       recommended,
            "recommended_note":  recommended_note,
        },
        # Reload caveats (must be prominently stated)
        "reload_caveats": [
            "All reload positions within the same epoch share the SAME settlement outcome.",
            "Reloads are concentrated exposure, NOT diversification.",
            "If an epoch settles NO, every reload position in that epoch loses.",
            "PnL formula: tokens = shadow_size / entry_price; pnl = (settle - entry) * tokens.",
            "Settlement is INFERRED from yes_bid near close, NOT confirmed API settlement.",
            "No slippage, fees, or spread modelled.",
            "Proxy evidence only -- does not prove live profitability.",
        ],
        "simulation_rules": [
            f"Max positions per asset: A={POLICIES[0]['max_per_asset']}, "
            f"B={POLICIES[1]['max_per_asset']}, C={POLICIES[2]['max_per_asset']}, "
            f"D=unlimited (exposure-capped).",
            f"Policy D: reload allowed while total epoch exposure <= {_POLICY_D_EXPOSURE_CAP}% bankroll.",
            "Events within each epoch sorted by seconds_remaining descending (earliest first).",
            f"Cutoff collision: seconds_remaining < {_CUTOFF_SR}s.",
            f"Unsafe exposure threshold: >= {_UNSAFE_EXPOSURE_PCT}% bankroll.",
            f"Unsafe drawdown threshold: > {_UNSAFE_DRAWDOWN_PCT}% bankroll = ~${unsafe_drawdown_usd:.2f}.",
            f"Loss cluster caution: max consecutive losses > {_CAUTION_LOSS_CLUSTER}.",
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
    print(f"\n{'─'*72}")
    print(f"  {r['policy_label']}")
    print(f"{'─'*72}")
    print(f"  Entries             : {r['entries']}  (settled: {r['settled_fill_count']})")
    print(f"  Skipped candidates  : {r['skipped_candidates']}")
    print(f"  Reload entries      : {r['reload_entries']}")

    print(f"\n  [PnL]")
    print(f"  Realized proxy PnL  : ${r['realized_proxy_pnl']:.4f}")
    print(f"  Reload PnL captured : ${r['captured_opportunity_cost_usd']:.4f}")
    print(f"  PnL uplift vs A     : ${r['pnl_uplift_vs_baseline_usd']:+.4f}")
    print(f"  Win rate            : {r['win_rate_pct']:.1f}%  "
          f"({r['win_count']}W / {r['loss_count']}L)")
    aw = r.get("avg_win")
    al = r.get("avg_loss")
    print(f"  Avg win / loss      : "
          f"{'$%.4f' % aw if aw is not None else 'N/A'} / "
          f"{'$%.4f' % al if al is not None else 'N/A'}")

    print(f"\n  [Risk]")
    print(f"  Max exposure        : {r['max_exposure_pct']:.2f}%")
    print(f"  Max concurrent      : {r['max_concurrent_positions']}")
    print(f"  Max drawdown        : ${r['max_drawdown']:.4f} ({r['max_drawdown_pct_bankroll']:.1f}% bankroll)")
    cl = r.get("clustered_loss_periods") or {}
    print(f"  Max consec losses   : {cl.get('max_consecutive_losses', 0)}  "
          f"(clusters: {cl.get('loss_cluster_count', 0)}, "
          f"epochs: {cl.get('total_loss_cluster_epochs', 0)})")
    print(f"  Cutoff collision    : {r['cutoff_collision_rate_pct']:.1f}%")

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

    print(f"\n  [Correlated Exposure  -- reloads are NOT diversification]")
    ce = r.get("correlated_exposure") or {}
    print(f"  Epochs with reloads     : {ce.get('same_epoch_reload_count', 0)}")
    print(f"  Max positions/epoch     : {ce.get('max_reload_count_per_epoch', 0)}")
    print(f"  Worst losing epoch PnL  : ${ce.get('worst_losing_epoch_pnl', 0):.4f}")
    print(f"  Reload loss epochs      : {ce.get('reload_loss_cluster_count', 0)}")
    ep_exp = ce.get("exposure_concentration_by_epoch") or {}
    print(f"  Epoch exposure mean     : {ep_exp.get('mean', 0):.2f}%  "
          f"max={ep_exp.get('max', 0):.2f}%")

    print(f"\n  [Verdict]  {r['verdict']}")
    print(f"  {r['verdict_note']}")


def print_report(result: dict[str, Any], date_str: str) -> None:
    if "error" in result:
        print(f"\n{SEP}")
        print(f"  Semantic C Bounded Reload Replay v1  |  {date_str}")
        print(f"{SEP}")
        print(f"  ERROR: {result['error']}")
        print(f"{SEP}\n")
        return

    print(f"\n{SEP}")
    print(f"  Semantic C Bounded Reload Opportunity Replay v1  |  {date_str}")
    print(f"{SEP}")
    print(f"  Total events        : {result['event_count']}")
    print(f"  Bankroll ref        : ${result['bankroll_ref']:.2f}")
    print(f"  Unsafe drawdown USD : ${result['unsafe_drawdown_usd']:.2f} "
          f"(={_UNSAFE_DRAWDOWN_PCT}% bankroll)")

    print(f"\n{'═'*72}")
    print(f"  CRITICAL CAVEATS")
    print(f"{'═'*72}")
    for c in result.get("reload_caveats", []):
        print(f"  ! {c}")

    for key in ("policy_A", "policy_B", "policy_C", "policy_D"):
        r = result.get(key)
        if r:
            _print_policy_section(r, result["bankroll_ref"])

    print(f"\n{SEP}")
    print(f"  POLICY COMPARISON SUMMARY")
    print(f"{SEP}")
    print(f"  {'Policy':<34} {'Entries':>7} {'PnL':>9} {'Uplift':>9} "
          f"{'MaxExp%':>8} {'MaxDD':>7} {'WR%':>5}  Verdict")
    print(f"  {'-'*34} {'-'*7} {'-'*9} {'-'*9} {'-'*8} {'-'*7} {'-'*5}  {'─'*16}")
    for row in result.get("policy_comparison", {}).get("rows", []):
        print(f"  {row['policy']:<34} {row['entries']:>7} "
              f"${row['realized_pnl']:>8.2f} ${row['uplift_usd']:>+8.2f} "
              f"{row['max_exp_pct']:>7.2f}% "
              f"${row['max_dd']:>6.2f} {row['win_rate']:>4.1f}%  {row['verdict']}")

    pc = result.get("policy_comparison") or {}
    print(f"\n  Best PnL policy     : {pc.get('best_pnl_policy', '?')}")
    print(f"  Best safe policy    : {pc.get('best_safe_policy', '?')}")
    print(f"  Recommended         : {pc.get('recommended', '?')}")
    print(f"  {pc.get('recommended_note', '')}")

    print(f"\n  guardrail: {result.get('guardrail', '')}")
    print(f"{SEP}\n")


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(result: dict[str, Any], date_str: str, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now(tz=timezone.utc).strftime("%H%M")
    path = report_dir / f"sem_c_reload_{date_str}_{ts}.json"
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
        description="Semantic C Bounded Reload Opportunity Replay v1 -- offline-only"
    )
    parser.add_argument("--date", required=True, help="Date to replay (YYYY-MM-DD)")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--asset", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    qd = Path(args.quant_data_dir)

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

    settlement_map = build_settlement_map(args.date, qd, probe_epoch_keys)

    result = analyse(events, settlement_map)
    print_report(result, args.date)

    if args.write_report:
        write_report(result, args.date, Path(args.report_dir))


if __name__ == "__main__":
    main()
