"""
Semantic C Inventory Continuity Replay State Machine v1 -- offline replay tool.

Replays Semantic C shadow fill candidates with realistic inventory continuity:
per-asset open/close state, max-one-position-per-asset gate, lifecycle-aware
state transitions, and settlement-based closing.  Measures how inventory
gating changes fill count, PnL, and exposure vs the independent-fill baseline.

Independent-fill baseline (from prior tools, 2026-05-15):
  shadow_fill_replay  : 321 hypothetical fills, 342 events
  pnl_truth_layer     : 299 settled fills, total proxy PnL $352.02, WR 60.9%
  BTC                 : 249 settled, WR 65.1%, mean PnL $0.84/fill
  ETH                 :  50 settled, WR 40.0%, mean PnL $2.84/fill

Data sources (local JSONL only -- no live API calls):
  runtime/quant_data/system_health/YYYY-MM-DD.jsonl     (zero_size_probe_v1)
  runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl   (settlement proxy)

State machine (per asset):
  FLAT         -> OPEN          first shadow-nonzero event in epoch (any phase)
  OPEN         -> HOLD          subsequent event in same epoch with ACTIVE_INVENTORY_TRADING
  OPEN/HOLD    -> REDUCE        subsequent event with PROFIT_MANAGEMENT
  any          -> FINAL_DERISK  event where seconds_remaining < FINAL_DERISK_SR
  any          -> CLOSED        epoch ends; settlement applied, state reset to FLAT

While OPEN/HOLD/REDUCE/FINAL_DERISK: subsequent shadow-nonzero events are
SKIPPED (counted as skipped_due_to_existing_inventory).

Settlement inference (from market_snapshots near close):
  yes_bid >= 0.70  ->  YES settlement, settlement_price = 1.0  (HIGH)
  yes_bid <= 0.30  ->  NO settlement,  settlement_price = 0.0  (HIGH)
  otherwise        ->  AMBIGUOUS  (unresolved, excluded from PnL)

PnL formula:
  tokens = shadow_size_usd / entry_price
  pnl    = (settlement_price - entry_price) * tokens

Additional opportunity-cost metrics:
  skipped_positive_ev_candidates      events skipped where ev_positive is True
  skipped_profitable_candidates       events skipped with proxy YES settlement
  skipped_candidate_opportunity_cost  sum of proxy PnL foregone from skipped profitable candidates

Usage:
  python -m tools.semantic_c_inventory_continuity_replay --date 2026-05-15
  python -m tools.semantic_c_inventory_continuity_replay --date 2026-05-15 --write-report
  python -m tools.semantic_c_inventory_continuity_replay --date 2026-05-15 --run-id <id>
  python -m tools.semantic_c_inventory_continuity_replay --date 2026-05-15 --asset BTC

Output:
  Console summary + optional runtime/reports/sem_c_inv_continuity_YYYY-MM-DD_HHMM.json

Report answers (14 outputs):
   1. simulated_entries
   2. skipped_due_to_existing_inventory
   3. max_concurrent_positions
   4. max_total_exposure_pct
   5. exposure_duration_distribution
   6. realized_proxy_pnl
   7. pnl_by_asset
   8. win_rate_by_asset
   9. max_drawdown
  10. clustered_loss_periods
  11. forced_close_count
  12. unresolved_close_count
  13. continuity_vs_independent_comparison
  14. verdict

This tool is OFFLINE-ONLY.  It does NOT change runtime, strategy, risk,
execution, position_sizing.py, order_manager.py, paper/live separation, or
any trading behavior.  No runtime modules are imported.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
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

# Shadow formula constants (mirrors position_sizing.py -- read-only reference)
_GOOD_EV    = 0.08
_CONF_FLOOR = 0.54
_CONF_SPAN  = 0.21
_EV_Q_FLOOR = 0.5

# Settlement proxy thresholds (same as pnl_truth layer)
_YES_THRESHOLD   = 0.70
_NO_THRESHOLD    = 0.30
_MAX_SR_FOR_PROXY = 120.0

# State machine thresholds
_FINAL_DERISK_SR  = 30.0   # seconds_remaining below this triggers FINAL_DERISK state
_MAX_PER_ASSET    = 1      # max open positions per asset (default, no reload)

# Reference values from prior independent-fill replay tools (2026-05-15)
_REF_INDEPENDENT_FILLS = 299
_REF_INDEPENDENT_PNL   = 352.015609
_REF_WIN_RATE_PCT      = 60.9

# Verdict thresholds
_UNSAFE_CONCURRENT    = 3     # max_concurrent >= this -> unsafe
_UNSAFE_EXPOSURE_PCT  = 10.0  # max_total_exposure_pct >= this -> unsafe
_NEEDS_MORE_MIN_FILLS = 10    # simulated_entries < this -> needs_more_replay
_NEEDS_MORE_WIN_RATE  = 40.0  # overall win rate < this -> needs_more_replay

# State labels
_FLAT         = "FLAT"
_OPEN         = "OPEN"
_HOLD         = "HOLD"
_REDUCE       = "REDUCE"
_FINAL_DERISK = "FINAL_DERISK"
_CLOSED       = "CLOSED"

# Lifecycle phase -> state mapping
_PHASE_TO_STATE: dict[str, str] = {
    "OPENING_SCAN":              _OPEN,
    "ACTIVE_INVENTORY_TRADING":  _HOLD,
    "PROFIT_MANAGEMENT":         _REDUCE,
    "FINAL_DERISK":              _FINAL_DERISK,
    "CLOSED_OR_UNSAFE":          _FINAL_DERISK,
}


# ---------------------------------------------------------------------------
# Shadow formula (identical to other shadow tools)
# ---------------------------------------------------------------------------

def _compute_shadow(p: dict[str, Any]) -> dict[str, Any]:
    """Derive Semantic C shadow from a zero_size_probe_v1 payload."""
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
    """Load zero_size_probe_v1 payloads from system_health JSONL."""
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
        if "ts" not in p and "ts" in ev:
            p = dict(p)
            p["_envelope_ts"] = ev["ts"]
        events.append(p)
    return events


# ---------------------------------------------------------------------------
# Settlement map (same algorithm as pnl_truth layer)
# ---------------------------------------------------------------------------

def build_settlement_map(
    date_str: str,
    quant_data_dir: Path,
    probe_epoch_keys: set[tuple[Any, str]],
) -> dict[tuple[Any, str], dict[str, Any]]:
    """Build settlement map from market_snapshots near-close yes_bid."""
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
# PnL formula
# ---------------------------------------------------------------------------

def _compute_pnl(entry_price: float, c_size: float, settlement_price: float) -> float | None:
    if c_size <= 0.0 or entry_price <= 0.0:
        return None
    tokens = c_size / entry_price
    return round((settlement_price - entry_price) * tokens, 8)


# ---------------------------------------------------------------------------
# Max drawdown
# ---------------------------------------------------------------------------

def _max_drawdown(pnl_series: list[float]) -> float:
    if not pnl_series:
        return 0.0
    cumulative = 0.0
    peak       = 0.0
    max_dd     = 0.0
    for pnl in pnl_series:
        cumulative += pnl
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 8)


# ---------------------------------------------------------------------------
# Clustered loss detection
# ---------------------------------------------------------------------------

def _clustered_losses(sorted_pnl_records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Detect consecutive loss runs from epoch-sorted settled positions.

    sorted_pnl_records must be sorted by epoch_start_ts ascending.
    Returns: max_consecutive_losses, loss_cluster_count, total_loss_cluster_epochs.
    """
    max_run   = 0
    n_clusters = 0
    total_epochs_in_clusters = 0
    current_run = 0
    for rec in sorted_pnl_records:
        pnl = rec.get("pnl")
        if pnl is not None and pnl < 0:
            current_run += 1
            if current_run > max_run:
                max_run = current_run
        else:
            if current_run >= 2:
                n_clusters += 1
                total_epochs_in_clusters += current_run
            current_run = 0
    if current_run >= 2:
        n_clusters += 1
        total_epochs_in_clusters += current_run
    return {
        "max_consecutive_losses":    max_run,
        "loss_cluster_count":        n_clusters,
        "total_loss_cluster_epochs": total_epochs_in_clusters,
    }


# ---------------------------------------------------------------------------
# Asset helper
# ---------------------------------------------------------------------------

def _asset_from_event(p: dict[str, Any]) -> str:
    tk = str(p.get("ticker") or "").upper()
    if tk in ("BTC", "ETH"):
        return tk
    mk = str(p.get("market_key") or "").lower()
    if "btc" in mk:
        return "BTC"
    if "eth" in mk:
        return "ETH"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# State machine simulation
# ---------------------------------------------------------------------------

def simulate_inventory(
    events: list[dict[str, Any]],
    settlement_map: dict[tuple[Any, str], dict[str, Any]],
    max_per_asset: int = _MAX_PER_ASSET,
) -> dict[str, Any]:
    """
    Run the inventory continuity state machine over sorted probe events.

    Events are grouped by (epoch_start_ts, market_key).  Within each epoch
    they are sorted by seconds_remaining descending (highest SR first = earliest
    in window = best entry timing).  Epochs are processed in chronological order.

    Returns a dict with:
      positions           - list of PositionRecord dicts (one per entry taken)
      skipped_events      - list of skipped shadow-nonzero event dicts
      concurrent_log      - list of {epoch_start_ts, concurrent_count, total_exposure_pct}
    """
    # --- Group and sort ---
    epoch_groups: dict[tuple[Any, str], list[dict[str, Any]]] = defaultdict(list)
    for p in events:
        ep = p.get("epoch_start_ts")
        mk = p.get("market_key")
        if ep is None or mk is None:
            continue
        epoch_groups[(ep, mk)].append(p)

    # Within each epoch: sort by SR descending (earliest in window first)
    for key in epoch_groups:
        epoch_groups[key].sort(
            key=lambda p: -float(p.get("seconds_remaining") or 0)
        )

    # Sort epochs chronologically
    sorted_keys = sorted(epoch_groups.keys(), key=lambda k: (k[0] if k[0] is not None else 0, k[1] or ""))

    # Per-asset state
    asset_state:    dict[str, str]                    = defaultdict(lambda: _FLAT)
    asset_position: dict[str, dict[str, Any] | None]  = defaultdict(lambda: None)

    positions: list[dict[str, Any]]    = []
    skipped:   list[dict[str, Any]]    = []
    concurrent_log: list[dict[str, Any]] = []

    # Group epochs by epoch_ts for concurrent tracking
    # We want to know, for each epoch_ts, how many assets have open positions
    epoch_ts_open: dict[Any, set[str]] = defaultdict(set)

    for epoch_key in sorted_keys:
        ep_ts, mk = epoch_key
        epoch_events = epoch_groups[epoch_key]
        asset = _asset_from_event(epoch_events[0])

        current_state = asset_state[asset]
        entry_taken   = False

        for p in epoch_events:
            shadow = _compute_shadow(p)
            sr     = float(p.get("seconds_remaining") or 0)
            phase  = str(p.get("lifecycle_phase") or "").upper()

            if not shadow["nonzero"]:
                continue  # no shadow for this event -- not a fill candidate

            if current_state == _FLAT and not entry_taken:
                # --- ENTER ---
                entry_price = float(p.get("entry_price") or 0.0)
                asset_position[asset] = {
                    "asset":               asset,
                    "market_key":          mk,
                    "epoch_start_ts":      ep_ts,
                    "entry_price":         entry_price,
                    "shadow_size_usd":     shadow["c_size"],
                    "shadow_pct_bankroll": shadow["pct_bankroll"],
                    "entry_phase":         phase,
                    "entry_sr":            sr,
                    "state":               _OPEN,
                    "ev_positive":         bool(p.get("ev_positive")),
                    "confidence":          float(p.get("confidence") or 0.0),
                }
                current_state = _OPEN
                entry_taken   = True
                epoch_ts_open[ep_ts].add(asset)

            else:
                # --- SKIP ---
                sett = settlement_map.get((ep_ts, mk))
                skipped.append({
                    "asset":          asset,
                    "epoch_start_ts": ep_ts,
                    "market_key":     mk,
                    "shadow_size_usd":shadow["c_size"],
                    "entry_price":    float(p.get("entry_price") or 0.0),
                    "phase":          phase,
                    "sr":             sr,
                    "ev_positive":    bool(p.get("ev_positive")),
                    "skip_reason":    "existing_inventory",
                    # Settlement of this epoch (for opportunity cost)
                    "settlement":     sett["inferred_settlement"] if sett else None,
                    "settlement_confidence": sett["confidence"] if sett else None,
                    "settlement_price": sett["settlement_price"] if sett else None,
                })

            # Update open position state based on phase / SR progression
            if entry_taken and asset_position[asset] is not None:
                pos = asset_position[asset]
                if sr < _FINAL_DERISK_SR:
                    pos["state"] = _FINAL_DERISK
                    current_state = _FINAL_DERISK
                elif phase in _PHASE_TO_STATE:
                    new_state = _PHASE_TO_STATE[phase]
                    # Only advance (never retreat) in state progression
                    state_order = [_OPEN, _HOLD, _REDUCE, _FINAL_DERISK]
                    curr_idx = state_order.index(current_state) if current_state in state_order else 0
                    new_idx  = state_order.index(new_state) if new_state in state_order else 0
                    if new_idx > curr_idx:
                        pos["state"] = new_state
                        current_state = new_state

        # --- EPOCH END: settle the open position ---
        if asset_position[asset] is not None:
            pos  = asset_position[asset]
            sett = settlement_map.get((ep_ts, mk))

            forced_by_derisk = (current_state == _FINAL_DERISK)

            if sett and sett["confidence"] == "HIGH":
                pnl = _compute_pnl(pos["entry_price"], pos["shadow_size_usd"], sett["settlement_price"])
                pos.update({
                    "state":            _CLOSED,
                    "settlement":       sett["inferred_settlement"],
                    "settlement_price": sett["settlement_price"],
                    "pnl":              pnl,
                    "close_reason":     "final_derisk_settled" if forced_by_derisk else "settlement",
                    "forced_close":     forced_by_derisk,
                    "unresolved_close": False,
                })
            elif sett and sett["confidence"] == "AMBIGUOUS":
                pos.update({
                    "state":            _CLOSED,
                    "settlement":       "AMBIGUOUS",
                    "settlement_price": None,
                    "pnl":              None,
                    "close_reason":     "unresolved_ambiguous",
                    "forced_close":     forced_by_derisk,
                    "unresolved_close": True,
                })
            else:
                pos.update({
                    "state":            _CLOSED,
                    "settlement":       None,
                    "settlement_price": None,
                    "pnl":              None,
                    "close_reason":     "no_snapshot",
                    "forced_close":     True,
                    "unresolved_close": True,
                })

            positions.append(pos)
            asset_position[asset] = None

        # Reset state for next epoch
        asset_state[asset] = _FLAT

    # Build concurrent exposure log
    for ep_ts, open_assets in epoch_ts_open.items():
        concurrent_log.append({
            "epoch_start_ts":  ep_ts,
            "concurrent_count": len(open_assets),
            "open_assets":      sorted(open_assets),
        })

    return {
        "positions":      positions,
        "skipped_events": skipped,
        "concurrent_log": concurrent_log,
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


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyse(
    events: list[dict[str, Any]],
    settlement_map: dict[tuple[Any, str], dict[str, Any]],
) -> dict[str, Any]:
    """
    Run the inventory continuity state machine and produce the 14-output report.

    No runtime imports; no side effects on inputs.
    """
    if not events:
        return {
            "event_count": 0,
            "error": "no_zero_size_probe_v1_events_found",
            "guardrail": "offline-only; no runtime changes",
        }

    sim = simulate_inventory(events, settlement_map)
    positions      = sim["positions"]
    skipped_events = sim["skipped_events"]
    concurrent_log = sim["concurrent_log"]

    total_events = len(events)

    # --- 1. Simulated entries ---
    simulated_entries = len(positions)

    # --- 2. Skipped due to existing inventory ---
    skipped_count = len(skipped_events)

    # Additional opportunity-cost metrics for skipped events
    skipped_ev_positive = sum(1 for s in skipped_events if s.get("ev_positive"))
    skipped_profitable  = sum(
        1 for s in skipped_events
        if s.get("settlement") == "YES" and s.get("settlement_confidence") == "HIGH"
    )
    # Opportunity cost: proxy PnL foregone from profitable skipped candidates
    opp_cost_total = 0.0
    for s in skipped_events:
        if s.get("settlement") == "YES" and s.get("settlement_confidence") == "HIGH":
            pnl = _compute_pnl(s["entry_price"], s["shadow_size_usd"], 1.0)
            if pnl is not None:
                opp_cost_total += pnl
    opp_cost_total = round(opp_cost_total, 6)

    # --- 3. Max concurrent positions ---
    max_concurrent = max((c["concurrent_count"] for c in concurrent_log), default=0)

    # --- 4. Max total exposure % ---
    # Build per-epoch total exposure from completed positions
    epoch_exposure: dict[Any, float] = defaultdict(float)
    for pos in positions:
        epoch_exposure[pos["epoch_start_ts"]] += pos.get("shadow_pct_bankroll", 0.0)
    max_total_exposure_pct = round(max(epoch_exposure.values(), default=0.0), 4)

    # --- 5. Exposure duration distribution ---
    # In Polymarket 5-minute binary markets, each position spans exactly one epoch.
    # The "duration" is the time from entry to epoch close, approximated as entry SR.
    entry_srs = [pos.get("entry_sr", 0.0) for pos in positions]
    exposure_duration = {
        "note": "Each position spans one 5-minute epoch (Polymarket atomic market).",
        "entry_seconds_remaining_stats": _stats(entry_srs),
        "typical_hold_seconds": round(mean(entry_srs), 1) if entry_srs else 0.0,
    }

    # --- 6. Realized proxy PnL ---
    settled_positions = [p for p in positions if p.get("pnl") is not None]
    settled_pnls      = [p["pnl"] for p in settled_positions]
    realized_pnl      = round(sum(settled_pnls), 8) if settled_pnls else 0.0

    # --- 7 & 8. PnL by asset and win rate by asset ---
    def _asset_stats(asset: str) -> dict[str, Any]:
        sub  = [p for p in settled_positions if p.get("asset") == asset]
        vals = [p["pnl"] for p in sub]
        wins = [v for v in vals if v > 0]
        return {
            "entries":         len([p for p in positions if p.get("asset") == asset]),
            "settled_fills":   len(sub),
            "total_pnl":       round(sum(vals), 8) if vals else 0.0,
            "win_rate_pct":    _pct(len(wins), len(sub)),
            "pnl_stats":       _stats(vals),
        }

    btc_stats = _asset_stats("BTC")
    eth_stats = _asset_stats("ETH")

    # --- 9. Max drawdown ---
    sorted_settled = sorted(settled_positions, key=lambda p: (p.get("epoch_start_ts") or 0, p.get("market_key") or ""))
    sorted_pnls    = [p["pnl"] for p in sorted_settled]
    max_dd         = _max_drawdown(sorted_pnls)

    # --- 10. Clustered loss periods ---
    cluster_info = _clustered_losses(sorted_settled)

    # --- 11. Forced close count ---
    forced_close_count = sum(1 for p in positions if p.get("forced_close"))

    # --- 12. Unresolved close count ---
    unresolved_close_count = sum(1 for p in positions if p.get("unresolved_close"))

    # --- Win rate overall ---
    wins_total  = sum(1 for v in settled_pnls if v > 0)
    losses_total = sum(1 for v in settled_pnls if v < 0)
    win_rate_overall = _pct(wins_total, len(settled_positions))
    avg_win  = round(mean([v for v in settled_pnls if v > 0]),  6) if any(v > 0 for v in settled_pnls)  else None
    avg_loss = round(mean([v for v in settled_pnls if v < 0]),  6) if any(v < 0 for v in settled_pnls) else None

    # --- 13. Continuity vs independent comparison ---
    pnl_change_pct = round(
        (realized_pnl - _REF_INDEPENDENT_PNL) / max(abs(_REF_INDEPENDENT_PNL), 1e-9) * 100, 2
    )
    entries_change_pct = round(
        (simulated_entries - _REF_INDEPENDENT_FILLS) / max(_REF_INDEPENDENT_FILLS, 1) * 100, 2
    )
    if realized_pnl >= _REF_INDEPENDENT_PNL * 0.80:
        pnl_relationship = "PRESERVES"
    elif realized_pnl >= _REF_INDEPENDENT_PNL * 0.50:
        pnl_relationship = "REDUCES_MODERATELY"
    else:
        pnl_relationship = "REDUCES_MATERIALLY"

    continuity_vs_independent = {
        "ref_independent_fills":    _REF_INDEPENDENT_FILLS,
        "ref_independent_pnl":      _REF_INDEPENDENT_PNL,
        "ref_win_rate_pct":         _REF_WIN_RATE_PCT,
        "continuity_entries":       simulated_entries,
        "continuity_pnl":           realized_pnl,
        "continuity_win_rate_pct":  win_rate_overall,
        "entries_change_pct":       entries_change_pct,
        "pnl_change_pct":           pnl_change_pct,
        "pnl_relationship":         pnl_relationship,
        "interpretation": (
            f"Inventory gating reduced entries from {_REF_INDEPENDENT_FILLS} to "
            f"{simulated_entries} ({entries_change_pct:+.1f}%). "
            f"Realized proxy PnL ${realized_pnl:.4f} vs ${_REF_INDEPENDENT_PNL:.4f} "
            f"independent ({pnl_change_pct:+.1f}%). "
            f"Win rate {win_rate_overall:.1f}% vs {_REF_WIN_RATE_PCT:.1f}% independent."
        ),
    }

    # --- 14. Verdict ---
    if max_concurrent >= _UNSAFE_CONCURRENT or max_total_exposure_pct >= _UNSAFE_EXPOSURE_PCT:
        verdict = "unsafe_due_to_inventory_overlap"
        verdict_note = (
            f"Max concurrent positions {max_concurrent} (threshold <{_UNSAFE_CONCURRENT}) "
            f"or max total exposure {max_total_exposure_pct:.2f}% "
            f"(threshold <{_UNSAFE_EXPOSURE_PCT}%) exceeds safe bounds."
        )
    elif simulated_entries < _NEEDS_MORE_MIN_FILLS or win_rate_overall < _NEEDS_MORE_WIN_RATE:
        verdict = "needs_more_replay"
        verdict_note = (
            f"Entries {simulated_entries} (threshold >={_NEEDS_MORE_MIN_FILLS}) "
            f"or win rate {win_rate_overall:.1f}% (threshold >={_NEEDS_MORE_WIN_RATE}%) "
            "insufficient for confident evidence. Collect longer paper sessions."
        )
    else:
        verdict = "safe_for_scoped_paper_trial"
        verdict_note = (
            f"Max concurrent {max_concurrent}, max exposure {max_total_exposure_pct:.2f}%, "
            f"win rate {win_rate_overall:.1f}%, entries {simulated_entries}. "
            "Inventory continuity constraints are bounded and safe. "
            "Evidence supports a scoped paper-only runtime trial with max-one-per-asset gate. "
            "Do NOT promote to live without a separately scoped implementation phase."
        )

    return {
        "event_count":               total_events,
        # 1
        "simulated_entries":         simulated_entries,
        "simulated_entries_pct":     _pct(simulated_entries, total_events),
        # 2
        "skipped_due_to_existing_inventory": skipped_count,
        "skipped_positive_ev_candidates":    skipped_ev_positive,
        "skipped_profitable_candidates":     skipped_profitable,
        "skipped_candidate_opportunity_cost_usd": opp_cost_total,
        # 3
        "max_concurrent_positions":  max_concurrent,
        # 4
        "max_total_exposure_pct":    max_total_exposure_pct,
        # 5
        "exposure_duration":         exposure_duration,
        # 6
        "settled_fill_count":        len(settled_positions),
        "realized_proxy_pnl":        realized_pnl,
        "pnl_stats":                 _stats(settled_pnls),
        # 7
        "pnl_by_asset": {"btc": btc_stats, "eth": eth_stats},
        # 8
        "win_rate_by_asset": {
            "btc": btc_stats["win_rate_pct"],
            "eth": eth_stats["win_rate_pct"],
        },
        "win_rate_overall_pct":  win_rate_overall,
        "win_count":             wins_total,
        "loss_count":            losses_total,
        "avg_win":               avg_win,
        "avg_loss":              avg_loss,
        # 9
        "max_drawdown_approx":   max_dd,
        # 10
        "clustered_loss_periods": cluster_info,
        # 11
        "forced_close_count":    forced_close_count,
        # 12
        "unresolved_close_count": unresolved_close_count,
        # 13
        "continuity_vs_independent": continuity_vs_independent,
        # 14
        "verdict":      verdict,
        "verdict_note": verdict_note,
        # Simulation context
        "simulation_rules": [
            "Inventory state machine runs per asset (BTC and ETH independent).",
            f"Max {_MAX_PER_ASSET} open position per asset (no reload/martingale).",
            "Events within each epoch sorted by seconds_remaining descending (earliest first).",
            "First shadow-nonzero event in epoch is the entry candidate.",
            "Subsequent shadow-nonzero events in same epoch are skipped.",
            f"FINAL_DERISK state triggered when seconds_remaining < {_FINAL_DERISK_SR}s.",
            "Position settled at epoch end using market_snapshots yes_bid proxy.",
            "AMBIGUOUS settlement (0.30 < yes_bid < 0.70) -> unresolved, no PnL.",
            "No slippage, no fees, no spread modelled in proxy PnL.",
            f"Reference independent-fill baseline: {_REF_INDEPENDENT_FILLS} fills, "
            f"${_REF_INDEPENDENT_PNL:.2f} proxy PnL, {_REF_WIN_RATE_PCT}% WR.",
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

SEP = "=" * 72


def print_report(result: dict[str, Any], date_str: str) -> None:
    if "error" in result:
        print(f"\n{SEP}")
        print(f"  Semantic C Inventory Continuity Replay v1  |  {date_str}")
        print(f"{SEP}")
        print(f"  ERROR: {result['error']}")
        print(f"{SEP}\n")
        return

    print(f"\n{SEP}")
    print(f"  Semantic C Inventory Continuity Replay v1  |  {date_str}")
    print(f"{SEP}")
    print(f"  Total probe events      : {result['event_count']}")

    print(f"\n--- 1. Simulated Entries ---")
    print(f"  Entries taken           : {result['simulated_entries']} "
          f"({result['simulated_entries_pct']:.1f}% of all events)")

    print(f"\n--- 2. Skipped Due to Existing Inventory ---")
    print(f"  Skipped total           : {result['skipped_due_to_existing_inventory']}")
    print(f"  Skipped with +EV        : {result['skipped_positive_ev_candidates']}")
    print(f"  Skipped profitable (YES): {result['skipped_profitable_candidates']}")
    print(f"  Opportunity cost (USD)  : ${result['skipped_candidate_opportunity_cost_usd']:.4f}")

    print(f"\n--- 3. Max Concurrent Positions ---")
    print(f"  {result['max_concurrent_positions']} (max across all epochs)")

    print(f"\n--- 4. Max Total Exposure % ---")
    print(f"  {result['max_total_exposure_pct']:.2f}% bankroll (sum of concurrent shadow sizes)")

    print(f"\n--- 5. Exposure Duration ---")
    ed = result.get("exposure_duration") or {}
    sr_s = ed.get("entry_seconds_remaining_stats") or {}
    print(f"  {ed.get('note', '')}")
    print(f"  Typical hold at entry SR: {ed.get('typical_hold_seconds', 0):.0f}s remaining")
    print(f"  Entry SR range: min={sr_s.get('min',0):.0f}s  max={sr_s.get('max',0):.0f}s")

    print(f"\n--- 6. Realized Proxy PnL ---")
    print(f"  Settled fill count      : {result['settled_fill_count']}")
    print(f"  Total proxy PnL         : ${result['realized_proxy_pnl']:.6f}")
    ps = result.get("pnl_stats") or {}
    print(f"  PnL mean                : ${ps.get('mean',0):.6f}")
    print(f"  PnL p50                 : ${ps.get('p50',0):.6f}")
    print(f"  PnL min                 : ${ps.get('min',0):.6f}")
    print(f"  PnL max                 : ${ps.get('max',0):.6f}")

    print(f"\n--- 7. PnL by Asset ---")
    for label, key in [("BTC", "btc"), ("ETH", "eth")]:
        a  = (result.get("pnl_by_asset") or {}).get(key) or {}
        p2 = a.get("pnl_stats") or {}
        if a.get("settled_fills", 0) == 0:
            print(f"  {label}: no settled fills")
            continue
        print(f"  {label}: entries={a['entries']}  settled={a['settled_fills']}  "
              f"total_pnl=${a['total_pnl']:.6f}  "
              f"pnl_mean=${p2.get('mean',0):.6f}")

    print(f"\n--- 8. Win Rate by Asset ---")
    wr = result.get("win_rate_by_asset") or {}
    print(f"  BTC        : {wr.get('btc', 0):.1f}%")
    print(f"  ETH        : {wr.get('eth', 0):.1f}%")
    print(f"  Overall    : {result['win_rate_overall_pct']:.1f}%  "
          f"({result['win_count']} wins / {result['loss_count']} losses)")
    aw = result.get("avg_win")
    al = result.get("avg_loss")
    print(f"  Avg win    : {'$%.6f' % aw if aw is not None else 'N/A'}")
    print(f"  Avg loss   : {'$%.6f' % al if al is not None else 'N/A'}")

    print(f"\n--- 9. Max Drawdown ---")
    print(f"  ${result['max_drawdown_approx']:.6f}  (epoch-sorted cumulative proxy PnL)")

    print(f"\n--- 10. Clustered Loss Periods ---")
    cl = result.get("clustered_loss_periods") or {}
    print(f"  Max consecutive losses  : {cl.get('max_consecutive_losses', 0)}")
    print(f"  Loss cluster count      : {cl.get('loss_cluster_count', 0)}")
    print(f"  Total epochs in clusters: {cl.get('total_loss_cluster_epochs', 0)}")

    print(f"\n--- 11. Forced Close Count ---")
    print(f"  {result['forced_close_count']} (closed at epoch end without settlement snapshot)")

    print(f"\n--- 12. Unresolved Close Count ---")
    print(f"  {result['unresolved_close_count']} (closed with AMBIGUOUS or missing settlement)")

    print(f"\n--- 13. Continuity vs Independent Comparison ---")
    ci = result.get("continuity_vs_independent") or {}
    print(f"  {ci.get('interpretation', '')}")
    print(f"  PnL relationship        : {ci.get('pnl_relationship', '')}")

    print(f"\n--- 14. Verdict ---")
    print(f"  {result.get('verdict', 'UNKNOWN')}")
    print(f"  {result.get('verdict_note', '')}")

    print(f"\n--- Simulation Rules ---")
    for rule in result.get("simulation_rules", []):
        print(f"  - {rule}")

    print(f"\n  guardrail: {result.get('guardrail', '')}")
    print(f"{SEP}\n")


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(result: dict[str, Any], date_str: str, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now(tz=timezone.utc).strftime("%H%M")
    path = report_dir / f"sem_c_inv_continuity_{date_str}_{ts}.json"
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
        description="Semantic C Inventory Continuity Replay v1 -- offline-only"
    )
    parser.add_argument("--date", required=True, help="Date to replay (YYYY-MM-DD)")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--asset", default=None, help="Filter by asset (BTC or ETH)")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--quant-data-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = parser.parse_args()

    qd = Path(args.quant_data_dir)

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

    settlement_map = build_settlement_map(args.date, qd, probe_epoch_keys)

    result = analyse(events, settlement_map)
    print_report(result, args.date)

    if args.write_report:
        write_report(result, args.date, Path(args.report_dir))


if __name__ == "__main__":
    main()
