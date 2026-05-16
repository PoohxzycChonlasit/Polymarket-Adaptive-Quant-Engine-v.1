"""
Semantic C Shadow PnL Truth Layer v1 -- offline replay tool.

Attaches settlement/resolution truth to Semantic C shadow fill opportunities
from zero_size_probe_v1 events, then computes hypothetical PnL honestly.

Settlement is INFERRED from the near-close yes_bid in market_snapshots JSONL,
not from a confirmed authoritative settlement API.  The tool states this clearly
in every output and treats ambiguous epochs conservatively (excluded from PnL).

Data sources (local JSONL only -- no live API calls):
  runtime/quant_data/system_health/YYYY-MM-DD.jsonl    (zero_size_probe_v1)
  runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl  (settlement proxy)

Settlement inference algorithm:
  For each unique (epoch_start_ts, market_key), take the market_snapshots entry
  with the minimum seconds_remaining (nearest to close).
    yes_bid >= 0.70  ->  YES settlement  (settlement_price = 1.0, confidence HIGH)
    yes_bid <= 0.30  ->  NO settlement   (settlement_price = 0.0, confidence HIGH)
    otherwise        ->  AMBIGUOUS       (excluded from PnL, reported honestly)

PnL formula (per fill):
    tokens = shadow_size_usd / entry_price
    pnl    = (settlement_price - entry_price) * tokens

Max drawdown approximation:
    Sort settled fills by epoch_start_ts ascending.
    Track running cumulative PnL.
    max_drawdown = max over series of (peak_so_far - current_cumulative_pnl).

Usage:
    python -m tools.semantic_c_shadow_pnl_truth --date 2026-05-15
    python -m tools.semantic_c_shadow_pnl_truth --date 2026-05-15 --write-report
    python -m tools.semantic_c_shadow_pnl_truth --date 2026-05-15 --run-id <id>
    python -m tools.semantic_c_shadow_pnl_truth --date 2026-05-15 --asset BTC

Output:
    Console summary + optional runtime/reports/sem_c_pnl_truth_YYYY-MM-DD_HHMM.json

Report answers (13 outputs):
    1.  Shadow fill candidates loaded
    2.  Settlement matched count
    3.  Settlement missing / ambiguous count
    4.  Match rate %
    5.  Hypothetical PnL total
    6.  PnL by BTC / ETH
    7.  PnL by lifecycle phase
    8.  Win rate (% fills with positive PnL)
    9.  Average win / average loss
    10. Max drawdown approximation
    11. Unresolved markets list / count
    12. Data quality verdict (PNL_TRUTH_AVAILABLE / PARTIAL_PNL_TRUTH / PNL_TRUTH_UNAVAILABLE)
    13. Semantic C economic evidence verdict for future scoped paper-only runtime trial

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

# Settlement proxy thresholds
_YES_THRESHOLD = 0.70   # yes_bid >= this -> YES settlement
_NO_THRESHOLD  = 0.30   # yes_bid <= this -> NO settlement
_MAX_SR_FOR_PROXY = 120.0  # only use snapshots with seconds_remaining < this

# Verdict thresholds
_MIN_SETTLED_FILLS_AVAILABLE = 10
_MIN_SETTLED_FILLS_PARTIAL   = 5
_MATCH_RATE_AVAILABLE        = 0.80
_MATCH_RATE_PARTIAL          = 0.30


# ---------------------------------------------------------------------------
# Shadow formula -- identical to other shadow tools
# ---------------------------------------------------------------------------

def _compute_shadow(p: dict[str, Any]) -> dict[str, Any]:
    """Derive Semantic C shadow fields from a zero_size_probe_v1 payload."""
    if "semantic_c_multiplier_shadow" in p:
        return {
            "c_size":        float(p.get("semantic_c_size_usd_shadow") or 0.0),
            "nonzero":       bool(p.get("semantic_c_would_produce_nonzero_size")),
            "pct_bankroll":  float(p.get("semantic_c_size_pct_bankroll") or 0.0),
            "from_live":     True,
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
    return {
        "c_size":       round(c_size, 6),
        "nonzero":      c_size > 0.0,
        "pct_bankroll": pct,
        "from_live":    False,
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

def load_probe_events(
    date_str: str,
    quant_data_dir: Path = DEFAULT_QUANT_DATA_DIR,
    run_id: str | None = None,
    asset_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Load zero_size_probe_v1 payloads from system_health JSONL."""
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
            if str(p.get("ticker") or "").upper() != asset_filter.upper():
                continue
        # Carry envelope ts into payload
        if "ts" not in p and "ts" in ev:
            p = dict(p)
            p["_envelope_ts"] = ev["ts"]
        events.append(p)
    return events


# ---------------------------------------------------------------------------
# Settlement map builder
# ---------------------------------------------------------------------------

_SettlementRecord = dict[str, Any]  # type alias

def build_settlement_map(
    date_str: str,
    quant_data_dir: Path,
    probe_epoch_keys: set[tuple[int | str, str]],
) -> dict[tuple[Any, str], _SettlementRecord]:
    """
    Build a settlement map keyed by (epoch_start_ts, market_key).

    Reads market_snapshots JSONL.  For each probe epoch key, finds the snapshot
    with the minimum seconds_remaining (nearest to close) that also satisfies
    seconds_remaining < _MAX_SR_FOR_PROXY, then infers settlement from yes_bid.

    Returns:
        {(epoch_start_ts, market_key): settlement_record}
    """
    path = quant_data_dir / "market_snapshots" / f"{date_str}.jsonl"
    raw  = _read_jsonl(path)

    # epoch_key -> best (lowest SR) record
    best: dict[tuple[Any, str], dict[str, Any]] = {}

    for ev in raw:
        p = _payload(ev) if "payload" in ev else ev
        ep  = p.get("epoch_start_ts") or p.get("epoch_start")
        mk  = p.get("market_key")
        sr  = p.get("seconds_remaining")
        yb  = p.get("yes_bid")

        if ep is None or mk is None or sr is None or yb is None:
            continue
        key = (ep, mk)
        if key not in probe_epoch_keys:
            continue
        sr_f = float(sr)
        if sr_f >= _MAX_SR_FOR_PROXY:
            continue
        if key not in best or sr_f < float(best[key]["seconds_remaining"]):
            best[key] = {"epoch_start_ts": ep, "market_key": mk,
                         "seconds_remaining": sr_f, "yes_bid": float(yb)}

    result: dict[tuple[Any, str], _SettlementRecord] = {}
    for key, rec in best.items():
        yb = rec["yes_bid"]
        if yb >= _YES_THRESHOLD:
            inferred = "YES"
            price    = 1.0
            conf     = "HIGH"
        elif yb <= _NO_THRESHOLD:
            inferred = "NO"
            price    = 0.0
            conf     = "HIGH"
        else:
            inferred = "AMBIGUOUS"
            price    = None
            conf     = "AMBIGUOUS"

        result[key] = {
            "inferred_settlement":       inferred,
            "settlement_price":          price,
            "yes_bid_at_match":          round(yb, 4),
            "seconds_remaining_at_match": rec["seconds_remaining"],
            "confidence":                conf,
            "settlement_source":         "market_price_proxy_near_close",
        }

    return result


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
# PnL formula
# ---------------------------------------------------------------------------

def _compute_pnl(entry_price: float, c_size: float, settlement_price: float) -> float | None:
    """
    Hypothetical PnL for one fill.

    tokens = c_size / entry_price
    pnl    = (settlement_price - entry_price) * tokens

    Returns None when inputs are insufficient.
    """
    if c_size <= 0.0 or entry_price <= 0.0:
        return None
    tokens = c_size / entry_price
    return round((settlement_price - entry_price) * tokens, 8)


# ---------------------------------------------------------------------------
# Max drawdown from a sorted PnL series
# ---------------------------------------------------------------------------

def _max_drawdown(pnl_series: list[float]) -> float:
    """
    Compute max drawdown over a cumulative PnL trajectory.

    Returns the maximum drop from any peak to any subsequent trough.
    """
    if not pnl_series:
        return 0.0
    cumulative   = 0.0
    peak         = 0.0
    max_dd       = 0.0
    for pnl in pnl_series:
        cumulative += pnl
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 8)


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyse(
    events: list[dict[str, Any]],
    settlement_map: dict[tuple[Any, str], _SettlementRecord],
) -> dict[str, Any]:
    """
    Attach settlement truth to shadow fill candidates and compute PnL.

    events         -- zero_size_probe_v1 payloads (from load_probe_events)
    settlement_map -- keyed by (epoch_start_ts, market_key)

    Returns a result dict answering all 13 outputs.
    No runtime imports; no side effects on inputs.
    """
    if not events:
        return {
            "event_count": 0,
            "error": "no_zero_size_probe_v1_events_found",
            "guardrail": "offline-only; no runtime changes",
        }

    total = len(events)

    # Build per-event records
    records: list[dict[str, Any]] = []
    for p in events:
        shadow = _compute_shadow(p)
        ep  = p.get("epoch_start_ts")
        mk  = p.get("market_key")
        key = (ep, mk) if ep is not None and mk is not None else None

        sett: _SettlementRecord | None = settlement_map.get(key) if key else None

        asset   = str(p.get("ticker") or "UNKNOWN").upper()
        phase   = str(p.get("lifecycle_phase") or "UNKNOWN").upper()
        ep_val  = p.get("epoch_start_ts")
        ts_sort = p.get("ts") or p.get("_envelope_ts") or (ep_val if ep_val else None)

        pnl: float | None = None
        pnl_eligible = False
        settlement_label = "NO_SNAPSHOT"

        if sett is None:
            settlement_label = "NO_SNAPSHOT"
        elif sett["confidence"] == "AMBIGUOUS":
            settlement_label = "AMBIGUOUS"
        elif shadow["nonzero"] and sett["settlement_price"] is not None:
            pnl_eligible = True
            settlement_label = sett["inferred_settlement"]
            entry_price = float(p.get("entry_price") or 0.0)
            pnl = _compute_pnl(entry_price, shadow["c_size"], sett["settlement_price"])
        else:
            settlement_label = sett["inferred_settlement"]

        records.append({
            "asset":              asset,
            "phase":              phase,
            "epoch_start_ts":     ep_val,
            "market_key":         mk,
            "ts_sort":            ts_sort,
            "shadow_size_usd":    shadow["c_size"],
            "shadow_pct_bankroll":shadow["pct_bankroll"],
            "would_fill":         shadow["nonzero"],
            "settlement_label":   settlement_label,
            "settlement_matched": sett is not None and sett["confidence"] == "HIGH",
            "pnl_eligible":       pnl_eligible,
            "pnl":                pnl,
            "yes_bid_proxy":      sett["yes_bid_at_match"] if sett else None,
            "sr_at_match":        sett["seconds_remaining_at_match"] if sett else None,
        })

    # --- 1. Shadow fill candidates ---
    fill_candidates = [r for r in records if r["would_fill"]]
    fill_count      = len(fill_candidates)

    # --- 2. Settlement matched ---
    matched_fills   = [r for r in fill_candidates if r["settlement_matched"]]
    matched_count   = len(matched_fills)

    # --- 3. Settlement missing / ambiguous ---
    ambig_fills     = [r for r in fill_candidates if r["settlement_label"] == "AMBIGUOUS"]
    no_snap_fills   = [r for r in fill_candidates if r["settlement_label"] == "NO_SNAPSHOT"]
    unresolved_count = len(ambig_fills) + len(no_snap_fills)

    # --- 4. Match rate ---
    match_rate = matched_count / fill_count if fill_count else 0.0

    # --- 5. PnL total ---
    pnl_records  = [r for r in fill_candidates if r["pnl_eligible"] and r["pnl"] is not None]
    settled_count = len(pnl_records)
    pnl_values   = [r["pnl"] for r in pnl_records]
    total_pnl    = round(sum(pnl_values), 8) if pnl_values else 0.0

    # --- 8. Win rate ---
    wins   = [v for v in pnl_values if v > 0.0]
    losses = [v for v in pnl_values if v < 0.0]
    win_rate = _pct(len(wins), settled_count)

    # --- 9. Avg win / avg loss ---
    avg_win  = round(mean(wins),   6) if wins   else None
    avg_loss = round(mean(losses), 6) if losses else None

    # --- 6. PnL by asset ---
    def _asset_pnl(asset: str) -> dict[str, Any]:
        sub    = [r for r in pnl_records if r["asset"] == asset]
        vals   = [r["pnl"] for r in sub]
        w_sub  = [v for v in vals if v > 0]
        return {
            "settled_fills":  len(sub),
            "total_pnl":      round(sum(vals), 8) if vals else 0.0,
            "win_rate_pct":   _pct(len(w_sub), len(sub)),
            "pnl_stats":      _stats(vals),
        }

    # --- 7. PnL by lifecycle phase ---
    phase_pnl: dict[str, list[float]] = defaultdict(list)
    for r in pnl_records:
        phase_pnl[r["phase"]].append(r["pnl"])

    lifecycle_pnl = {
        ph: {
            "settled_fills": len(vs),
            "total_pnl":     round(sum(vs), 8),
            "win_rate_pct":  _pct(sum(1 for v in vs if v > 0), len(vs)),
            "pnl_stats":     _stats(vs),
        }
        for ph, vs in phase_pnl.items()
    }

    # --- 10. Max drawdown ---
    # Sort pnl_records by epoch_start_ts then ts_sort
    def _sort_key(r: dict) -> tuple[int | float, str]:
        ep = r["epoch_start_ts"]
        return (ep if ep is not None else 0, str(r["ts_sort"] or ""))

    sorted_pnl = [r["pnl"] for r in sorted(pnl_records, key=_sort_key)]
    max_dd = _max_drawdown(sorted_pnl)

    # --- 11. Unresolved markets ---
    all_epoch_keys = set()
    for r in records:
        ep = r["epoch_start_ts"]
        mk = r["market_key"]
        if ep is not None and mk is not None:
            all_epoch_keys.add((ep, mk))

    unresolved_keys = [
        k for k in all_epoch_keys
        if k not in settlement_map or settlement_map[k]["confidence"] == "AMBIGUOUS"
    ]
    unresolved_market_keys = [str(k) for k in sorted(unresolved_keys, key=lambda x: (x[0], x[1]))]

    # --- 12. Data quality verdict ---
    if settled_count >= _MIN_SETTLED_FILLS_AVAILABLE and match_rate >= _MATCH_RATE_AVAILABLE:
        dq_verdict = "PNL_TRUTH_AVAILABLE"
        dq_note    = (
            f"Settlement inferred for {settled_count} fills ({_pct(settled_count, fill_count):.0f}% "
            f"of fill candidates). Match rate {match_rate:.0%} meets the "
            f"{_MATCH_RATE_AVAILABLE:.0%} threshold. PnL results are usable as "
            "offline replay evidence. Settlement is still proxy-inferred, not confirmed API truth."
        )
    elif settled_count >= _MIN_SETTLED_FILLS_PARTIAL and match_rate >= _MATCH_RATE_PARTIAL:
        dq_verdict = "PARTIAL_PNL_TRUTH"
        dq_note    = (
            f"Settlement inferred for {settled_count} fills ({_pct(settled_count, fill_count):.0f}% "
            f"of fill candidates). Match rate {match_rate:.0%} is below the "
            f"{_MATCH_RATE_AVAILABLE:.0%} threshold for full truth. Treat PnL estimates as "
            "indicative only. Collect more data or investigate ambiguous epochs."
        )
    else:
        dq_verdict = "PNL_TRUTH_UNAVAILABLE"
        dq_note    = (
            f"Only {settled_count} fills with settlement data. "
            "Insufficient coverage for reliable PnL truth. "
            "Run more paper sessions or investigate missing near-close snapshots."
        )

    # --- 13. Economic evidence verdict ---
    if dq_verdict == "PNL_TRUTH_AVAILABLE" and win_rate >= 40.0:
        econ_verdict = "EVIDENCE_SUPPORTS_SCOPED_PAPER_TRIAL"
        econ_note    = (
            f"Win rate {win_rate:.1f}% across {settled_count} proxy-settled fills. "
            f"Total proxy PnL ${total_pnl:.4f}. "
            "Geometric exposure is bounded (from fill replay). "
            "Settlement proxy evidence supports a scoped paper-only runtime trial. "
            "Do NOT promote to live without a separately scoped implementation phase, "
            "real settlement confirmation, and a longer paper evidence window."
        )
    elif dq_verdict == "PNL_TRUTH_AVAILABLE" and win_rate < 40.0:
        econ_verdict = "EVIDENCE_WEAK_NEGATIVE_EXPECTANCY"
        econ_note    = (
            f"Win rate {win_rate:.1f}% is below 40%. "
            f"Total proxy PnL ${total_pnl:.4f}. "
            "Settlement proxy evidence suggests negative or near-zero expectancy. "
            "Do not promote to paper runtime without investigating why Semantic C "
            "entries lose under this session's market conditions."
        )
    elif dq_verdict == "PARTIAL_PNL_TRUTH":
        econ_verdict = "PARTIAL_EVIDENCE_GATHER_MORE"
        econ_note    = (
            f"Partial settlement coverage ({settled_count} fills settled). "
            "Cannot confidently claim positive or negative expectancy. "
            "Collect longer paper sessions before drawing economic conclusions."
        )
    else:
        econ_verdict = "INSUFFICIENT_PNL_EVIDENCE"
        econ_note    = (
            "Settlement coverage is too low for any economic evidence claim. "
            "Geometric safety from fill replay remains valid, but profitability "
            "is completely unknown from current data."
        )

    return {
        # Metadata
        "event_count":            total,
        # 1
        "shadow_fill_candidates": fill_count,
        "fill_candidate_pct":     _pct(fill_count, total),
        # 2
        "settlement_matched_count":  matched_count,
        # 3
        "settlement_missing_ambiguous_count": unresolved_count,
        "ambiguous_count":          len(ambig_fills),
        "no_snapshot_count":        len(no_snap_fills),
        # 4
        "match_rate":             round(match_rate, 4),
        "match_rate_pct":         _pct(matched_count, fill_count),
        # 5
        "settled_fill_count":     settled_count,
        "total_hypothetical_pnl": total_pnl,
        "pnl_stats":              _stats(pnl_values),
        # 6
        "btc":                    _asset_pnl("BTC"),
        "eth":                    _asset_pnl("ETH"),
        # 7
        "lifecycle_pnl":          lifecycle_pnl,
        # 8
        "win_rate_pct":           win_rate,
        "win_count":              len(wins),
        "loss_count":             len(losses),
        # 9
        "avg_win":                avg_win,
        "avg_loss":               avg_loss,
        "win_loss_ratio":         round(abs(avg_win / avg_loss), 4) if avg_win and avg_loss else None,
        # 10
        "max_drawdown_approx":    max_dd,
        # 11
        "unresolved_market_keys": unresolved_market_keys,
        "unresolved_count":       len(unresolved_market_keys),
        # 12
        "data_quality_verdict":   dq_verdict,
        "data_quality_note":      dq_note,
        # 13
        "economic_evidence_verdict": econ_verdict,
        "economic_evidence_note":    econ_note,
        # Settlement metadata
        "settlement_inference": {
            "source":              "market_price_proxy_near_close",
            "yes_threshold":       _YES_THRESHOLD,
            "no_threshold":        _NO_THRESHOLD,
            "max_sr_for_proxy":    _MAX_SR_FOR_PROXY,
            "caveats": [
                "Settlement is INFERRED from yes_bid near close, NOT confirmed API settlement.",
                "Ambiguous epochs (0.30 < yes_bid < 0.70) are excluded from PnL.",
                "PnL assumes fill at entry_price with zero slippage.",
                "This is proxy evidence only; does not prove live profitability.",
            ],
        },
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
        print(f"  Semantic C Shadow PnL Truth Layer v1  |  {date_str}")
        print(f"{SEP}")
        print(f"  ERROR: {result['error']}")
        print(f"{SEP}\n")
        return

    print(f"\n{SEP}")
    print(f"  Semantic C Shadow PnL Truth Layer v1  |  {date_str}")
    print(f"{SEP}")
    si = result.get("settlement_inference") or {}
    print(f"  Settlement source  : {si.get('settlement_source','market_price_proxy_near_close')}")
    print(f"  YES threshold      : yes_bid >= {si.get('yes_threshold', _YES_THRESHOLD)}")
    print(f"  NO threshold       : yes_bid <= {si.get('no_threshold', _NO_THRESHOLD)}")
    print(f"  Max SR for proxy   : < {si.get('max_sr_for_proxy', _MAX_SR_FOR_PROXY)}s")
    print(f"  Total events       : {result['event_count']}")

    print(f"\n--- 1. Shadow Fill Candidates ---")
    print(f"  Fill candidates    : {result['shadow_fill_candidates']} "
          f"({result['fill_candidate_pct']:.1f}% of all events)")

    print(f"\n--- 2 & 3. Settlement Coverage ---")
    print(f"  Matched (HIGH conf): {result['settlement_matched_count']}")
    print(f"  Ambiguous          : {result['ambiguous_count']}")
    print(f"  No snapshot        : {result['no_snapshot_count']}")

    print(f"\n--- 4. Match Rate ---")
    print(f"  {result['match_rate_pct']:.1f}% of fill candidates have HIGH-confidence settlement")

    print(f"\n--- 5. Hypothetical PnL Total ---")
    print(f"  Settled fills      : {result['settled_fill_count']}")
    print(f"  Total PnL          : ${result['total_hypothetical_pnl']:.6f}")
    ps = result.get("pnl_stats") or {}
    print(f"  PnL mean           : ${ps.get('mean', 0):.6f}")
    print(f"  PnL p50            : ${ps.get('p50', 0):.6f}")
    print(f"  PnL min            : ${ps.get('min', 0):.6f}")
    print(f"  PnL max            : ${ps.get('max', 0):.6f}")

    print(f"\n--- 6. PnL by Asset ---")
    for label, key in [("BTC", "btc"), ("ETH", "eth")]:
        a = result.get(key) or {}
        if a.get("settled_fills", 0) == 0:
            print(f"  {label}: no settled fills")
            continue
        ps2 = a.get("pnl_stats") or {}
        print(f"  {label}: settled={a['settled_fills']}  total_pnl=${a['total_pnl']:.6f}  "
              f"win_rate={a['win_rate_pct']:.1f}%  pnl_mean=${ps2.get('mean',0):.6f}")

    print(f"\n--- 7. PnL by Lifecycle Phase ---")
    for ph, d in sorted(result.get("lifecycle_pnl", {}).items(), key=lambda x: -abs(x[1].get("total_pnl", 0))):
        ps3 = d.get("pnl_stats") or {}
        print(f"  {ph:<40} n={d['settled_fills']:>4}  total=${d['total_pnl']:.6f}  "
              f"win%={d['win_rate_pct']:.1f}  mean=${ps3.get('mean',0):.6f}")

    print(f"\n--- 8. Win Rate ---")
    print(f"  {result['win_rate_pct']:.1f}%  ({result['win_count']} wins / "
          f"{result['loss_count']} losses / {result['settled_fill_count']} total)")

    print(f"\n--- 9. Average Win / Average Loss ---")
    aw = result.get("avg_win")
    al = result.get("avg_loss")
    wlr = result.get("win_loss_ratio")
    print(f"  Avg win            : {'$%.6f' % aw if aw is not None else 'N/A'}")
    print(f"  Avg loss           : {'$%.6f' % al if al is not None else 'N/A'}")
    print(f"  Win/loss ratio     : {'%.4f' % wlr if wlr is not None else 'N/A'}")

    print(f"\n--- 10. Max Drawdown Approximation ---")
    print(f"  ${result['max_drawdown_approx']:.6f}  "
          f"(epoch-sorted cumulative PnL; proxy-only, not confirmed live drawdown)")

    print(f"\n--- 11. Unresolved Markets ---")
    ur = result.get("unresolved_count", 0)
    print(f"  {ur} market epochs without HIGH-confidence settlement")
    for mk_str in (result.get("unresolved_market_keys") or [])[:5]:
        print(f"    {mk_str}")
    if ur > 5:
        print(f"    ... and {ur - 5} more")

    print(f"\n--- 12. Data Quality Verdict ---")
    print(f"  {result.get('data_quality_verdict', 'UNKNOWN')}")
    print(f"  {result.get('data_quality_note', '')}")

    print(f"\n--- 13. Economic Evidence Verdict ---")
    print(f"  {result.get('economic_evidence_verdict', 'UNKNOWN')}")
    print(f"  {result.get('economic_evidence_note', '')}")

    print(f"\n--- Settlement Inference Caveats ---")
    for c in (si.get("caveats") or []):
        print(f"  - {c}")

    print(f"\n  guardrail: {result.get('guardrail', '')}")
    print(f"{SEP}\n")


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(result: dict[str, Any], date_str: str, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now(tz=timezone.utc).strftime("%H%M")
    path = report_dir / f"sem_c_pnl_truth_{date_str}_{ts}.json"
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
        description="Semantic C Shadow PnL Truth Layer v1 -- offline-only"
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

    # Collect unique epoch keys from loaded events
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
