"""
Epoch Boundary Alignment Probe v1 - offline analysis tool.

Measures how quickly each 5-minute market becomes discoverable, token-ready,
orderbook-ready, and tradable after epoch open, and classifies which lifecycle
window each milestone lands in.

Answers the question: is the ACTIVE_INVENTORY_TRADING window being lost because
token IDs / orderbooks aren't available at epoch open?

Reads:
  runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl   (primary)
  runtime/quant_data/research_log/YYYY-MM-DD.jsonl       (cycle-gap supplement)

Usage:
    python -m tools.epoch_boundary_alignment_probe --date 2026-05-15
    python -m tools.epoch_boundary_alignment_probe --date 2026-05-15 --write-report
    python -m tools.epoch_boundary_alignment_probe --date 2026-05-15 --asset BTC
    python -m tools.epoch_boundary_alignment_probe --date 2026-05-15 --run-id <id>

Output:
    Console summary + optional runtime/reports/epoch_boundary_alignment_probe_YYYY-MM-DD.json

Guardrail: offline-only. Does not change runtime, strategy, risk, execution, or
paper/live separation. No runtime imports.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

if __package__ in {None, ""}:
    _repo_root = Path(__file__).resolve().parents[1]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

EPOCH_DURATION_SECONDS = 300
MIN_REAL_EPOCH_TS = 1_000_000_000  # Filter out fake/test epoch timestamps

# Lifecycle window boundaries (seconds since epoch open)
_WINDOWS = [
    ("OPENING_SCAN",           0,   35),
    ("ACTIVE_INVENTORY_TRADING", 35, 240),
    ("PROFIT_MANAGEMENT",      240, 270),
    ("FINAL_DERISK",           270, 300),
]

DEFAULT_QUANT_DATA_DIR = Path("runtime/quant_data")
DEFAULT_REPORT_DIR = Path("runtime/reports")


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

def load_snapshot_events(
    date_str: str,
    quant_data_dir: Path = DEFAULT_QUANT_DATA_DIR,
    run_id: str | None = None,
    asset_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Load market_snapshots events for the given date."""
    path = quant_data_dir / "market_snapshots" / f"{date_str}.jsonl"
    events = _read_jsonl(path)
    if run_id:
        events = [e for e in events if e.get("run_id") == run_id]
    if asset_filter:
        af = asset_filter.upper()
        events = [
            e for e in events
            if str(_payload(e).get("asset") or _payload(e).get("ticker") or "").upper() == af
        ]
    return events


def load_research_events(
    date_str: str,
    quant_data_dir: Path = DEFAULT_QUANT_DATA_DIR,
    run_id: str | None = None,
    asset_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Load research_log events for the given date (cycle-gap supplement)."""
    path = quant_data_dir / "research_log" / f"{date_str}.jsonl"
    events = _read_jsonl(path)
    if run_id:
        events = [e for e in events if e.get("run_id") == run_id]
    if asset_filter:
        af = asset_filter.upper()
        events = [
            e for e in events
            if str(_payload(e).get("asset") or _payload(e).get("ticker") or "").upper() == af
        ]
    return events


# ---------------------------------------------------------------------------
# Core timing conversions
# ---------------------------------------------------------------------------

def seconds_since_open(seconds_remaining: int | float | None) -> int | None:
    """Convert seconds_remaining to seconds_since_open within a 300s epoch.

    Returns None if input is missing, zero (meaning milestone not reached), or invalid.
    """
    if seconds_remaining is None:
        return None
    try:
        sr = float(seconds_remaining)
    except (TypeError, ValueError):
        return None
    if sr <= 0:
        return None
    sso = int(EPOCH_DURATION_SECONDS - sr)
    if sso < 0 or sso > EPOCH_DURATION_SECONDS:
        return None
    return sso


def classify_window(sso: int | None) -> str:
    """Return lifecycle window name for a seconds_since_open value."""
    if sso is None:
        return "UNKNOWN"
    for name, lo, hi in _WINDOWS:
        if lo <= sso < hi:
            return name
    if sso >= EPOCH_DURATION_SECONDS:
        return "CLOSED_OR_UNSAFE"
    return "UNKNOWN"


def _int_field(payload: dict[str, Any], key: str) -> int | None:
    v = payload.get(key)
    if v is None:
        return None
    try:
        iv = int(float(v))
        return iv if iv > 0 else None
    except (TypeError, ValueError):
        return None


def _bool_field(payload: dict[str, Any], key: str) -> bool | None:
    v = payload.get(key)
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() == "true"
    return bool(v)


def _epoch_start(payload: dict[str, Any]) -> int | None:
    for key in ("epoch_start_ts", "epoch_start", "market_epoch_start"):
        v = payload.get(key)
        if v is not None:
            try:
                iv = int(float(v))
                if iv >= MIN_REAL_EPOCH_TS:
                    return iv
            except (TypeError, ValueError):
                pass
    return None


def _milestone_completeness(payload: dict[str, Any]) -> int:
    """Count how many first_* milestone fields are non-zero (more = more complete)."""
    keys = (
        "first_discovered_seconds_remaining",
        "first_token_ready_seconds_remaining",
        "first_orderbook_seen_seconds_remaining",
        "first_tradable_seconds_remaining",
    )
    return sum(1 for k in keys if _int_field(payload, k) is not None)


# ---------------------------------------------------------------------------
# Per-epoch record extraction
# ---------------------------------------------------------------------------

def extract_epoch_record(events: list[dict[str, Any]]) -> dict[str, Any]:
    """From all market_snapshot events for one (asset, epoch_start_ts) group,
    build a single canonical timing record.

    Uses the event with the highest milestone completeness as primary, then
    fills any remaining gaps from other events in the group.
    """
    if not events:
        return {}

    payloads = [_payload(e) for e in events]
    payloads.sort(key=_milestone_completeness, reverse=True)
    best = payloads[0]

    asset = str(best.get("asset") or best.get("ticker") or "").upper()
    epoch_ts = _epoch_start(best)

    # Timing milestone seconds_remaining values
    first_disc_sr   = _int_field(best, "first_discovered_seconds_remaining")
    first_tok_sr    = _int_field(best, "first_token_ready_seconds_remaining")
    first_ob_sr     = _int_field(best, "first_orderbook_seen_seconds_remaining")
    first_trad_sr   = _int_field(best, "first_tradable_seconds_remaining")
    first_norm_sr   = _int_field(best, "first_spread_normalized_seconds_remaining")
    first_nonz_sr   = _int_field(best, "first_nonzero_bidask_seconds_remaining")
    entry_cutoff    = _int_field(best, "entry_cutoff_seconds") or _int_field(best, "effective_cutoff_seconds") or 90

    # Fallback: fill missing from other payloads in same epoch group
    for p in payloads[1:]:
        if first_disc_sr is None:
            first_disc_sr = _int_field(p, "first_discovered_seconds_remaining")
        if first_tok_sr is None:
            first_tok_sr = _int_field(p, "first_token_ready_seconds_remaining")
        if first_ob_sr is None:
            first_ob_sr = _int_field(p, "first_orderbook_seen_seconds_remaining")
        if first_trad_sr is None:
            first_trad_sr = _int_field(p, "first_tradable_seconds_remaining")
        if first_norm_sr is None:
            first_norm_sr = _int_field(p, "first_spread_normalized_seconds_remaining")
        if first_nonz_sr is None:
            first_nonz_sr = _int_field(p, "first_nonzero_bidask_seconds_remaining")

    # Convert to seconds_since_open
    first_disc_sso  = seconds_since_open(first_disc_sr)
    first_tok_sso   = seconds_since_open(first_tok_sr)
    first_ob_sso    = seconds_since_open(first_ob_sr)
    first_trad_sso  = seconds_since_open(first_trad_sr)
    first_norm_sso  = seconds_since_open(first_norm_sr)
    first_nonz_sso  = seconds_since_open(first_nonz_sr)

    # Derived delays (seconds from epoch open to milestone)
    token_pub_delay = first_tok_sso  # seconds from open to first token IDs
    ob_delay        = first_ob_sso   # seconds from open to first orderbook
    tradable_delay  = first_trad_sso # seconds from open to first TRADABLE

    # Relative delays: from one milestone to next
    tok_after_disc  = (first_tok_sso  - first_disc_sso) if (first_tok_sso  is not None and first_disc_sso  is not None) else None
    ob_after_tok    = (first_ob_sso   - first_tok_sso)  if (first_ob_sso   is not None and first_tok_sso   is not None) else None
    trad_after_ob   = (first_trad_sso - first_ob_sso)   if (first_trad_sso is not None and first_ob_sso    is not None) else None

    # Window classifications
    disc_window  = classify_window(first_disc_sso)
    tok_window   = classify_window(first_tok_sso)
    ob_window    = classify_window(first_ob_sso)
    trad_window  = classify_window(first_trad_sso)

    # Before-cutoff check: did TRADABLE arrive before the entry cutoff window?
    # tradable is before cutoff if first_trad_sr > entry_cutoff
    tradable_before_cutoff = (
        first_trad_sr is not None and first_trad_sr > entry_cutoff
    )

    # Preload fields from best payload
    preload_success   = _bool_field(best, "preload_success")
    preload_cache_hit = _bool_field(best, "preload_cache_hit")
    preload_lat_ms    = _int_field(best, "preload_latency_ms")

    # Total events in this epoch group
    event_count = len(events)

    return {
        "asset": asset,
        "epoch_start_ts": epoch_ts,
        "event_count": event_count,
        "entry_cutoff_seconds": entry_cutoff,
        # Seconds-remaining fields (raw)
        "first_discovered_sr":  first_disc_sr,
        "first_token_ready_sr": first_tok_sr,
        "first_orderbook_sr":   first_ob_sr,
        "first_tradable_sr":    first_trad_sr,
        # Seconds-since-open fields (derived)
        "first_discovered_sso":  first_disc_sso,
        "first_token_ready_sso": first_tok_sso,
        "first_orderbook_sso":   first_ob_sso,
        "first_tradable_sso":    first_trad_sso,
        "first_spread_norm_sso": first_norm_sso,
        "first_nonzero_book_sso": first_nonz_sso,
        # Lifecycle window classifications
        "disc_window":  disc_window,
        "tok_window":   tok_window,
        "ob_window":    ob_window,
        "trad_window":  trad_window,
        # Derived delays
        "token_publication_delay_seconds": token_pub_delay,
        "orderbook_ready_delay_seconds":   ob_delay,
        "tradable_delay_seconds":          tradable_delay,
        "tok_after_disc_seconds":   tok_after_disc,
        "ob_after_tok_seconds":     ob_after_tok,
        "trad_after_ob_seconds":    trad_after_ob,
        # Flags
        "tradable_before_cutoff":    tradable_before_cutoff,
        "has_token_ready":           first_tok_sso is not None,
        "has_orderbook":             first_ob_sso is not None,
        "has_tradable":              first_trad_sso is not None,
        # Preload correlation
        "preload_success":    preload_success,
        "preload_cache_hit":  preload_cache_hit,
        "preload_latency_ms": preload_lat_ms,
    }


def build_epoch_records(
    snapshot_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Group snapshot events by (asset, epoch_start_ts) and extract one record per epoch."""
    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for event in snapshot_events:
        p = _payload(event)
        asset = str(p.get("asset") or p.get("ticker") or "").upper()
        epoch_ts = _epoch_start(p)
        if asset and epoch_ts is not None:
            groups[(asset, epoch_ts)].append(event)
    return [extract_epoch_record(evs) for evs in groups.values() if evs]


# ---------------------------------------------------------------------------
# Cycle-gap supplement from research_log
# ---------------------------------------------------------------------------

def extract_cycle_gaps(research_events: list[dict[str, Any]]) -> list[float]:
    """Extract observed cycle gap values from research_log events."""
    gaps: list[float] = []
    for event in research_events:
        p = _payload(event)
        for key in ("decision_cycle_interval_seconds", "effective_outer_loop_interval_seconds"):
            v = p.get(key)
            if v is not None:
                try:
                    fv = float(v)
                    if fv > 0:
                        gaps.append(fv)
                        break
                except (TypeError, ValueError):
                    pass
    return gaps


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _pct(n: int, total: int) -> float:
    return round(100.0 * n / total, 1) if total else 0.0


def _stats(values: list[float | int]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "min": None, "p25": None, "p50": None, "p75": None, "p90": None, "max": None, "mean": None}
    sv = sorted(values)
    n = len(sv)

    def _p(pct: float) -> float:
        idx = (pct / 100.0) * (n - 1)
        lo, hi = int(idx), min(int(idx) + 1, n - 1)
        return round(sv[lo] + (sv[hi] - sv[lo]) * (idx - lo), 1)

    return {
        "n":   n,
        "min": round(sv[0], 1),
        "p25": _p(25),
        "p50": _p(50),
        "p75": _p(75),
        "p90": _p(90),
        "max": round(sv[-1], 1),
        "mean": round(mean(sv), 1),
    }


def _window_dist(records: list[dict[str, Any]], field: str) -> dict[str, int]:
    c: dict[str, int] = defaultdict(int)
    for r in records:
        c[str(r.get(field) or "UNKNOWN")] += 1
    return dict(c)


def _preload_correlation(records: list[dict[str, Any]], metric_key: str) -> dict[str, Any]:
    """Compare a sso metric split by preload_success and preload_cache_hit."""
    with_hit:    list[float] = []
    without_hit: list[float] = []
    with_success:    list[float] = []
    without_success: list[float] = []
    for r in records:
        v = r.get(metric_key)
        if v is None:
            continue
        fv = float(v)
        if r.get("preload_cache_hit") is True:
            with_hit.append(fv)
        elif r.get("preload_cache_hit") is False:
            without_hit.append(fv)
        if r.get("preload_success") is True:
            with_success.append(fv)
        elif r.get("preload_success") is False:
            without_success.append(fv)
    return {
        "preload_cache_hit_p50":    _stats(with_hit).get("p50"),
        "preload_cache_miss_p50":   _stats(without_hit).get("p50"),
        "preload_success_p50":      _stats(with_success).get("p50"),
        "preload_no_success_p50":   _stats(without_success).get("p50"),
        "cache_hit_n":    len(with_hit),
        "cache_miss_n":   len(without_hit),
        "success_n":      len(with_success),
        "no_success_n":   len(without_success),
    }


def _cycle_gap_correlation(
    records: list[dict[str, Any]],
    cycle_gaps: list[float],
) -> dict[str, Any]:
    """Summarise overall cycle gap distribution (supplement data, not per-epoch joined)."""
    if not cycle_gaps:
        return {"available": False}
    return {
        "available":          True,
        "cycle_gap_stats":    _stats(cycle_gaps),
        "bimodal_short_n":    sum(1 for g in cycle_gaps if g < 30),
        "bimodal_long_n":     sum(1 for g in cycle_gaps if g >= 200),
        "bimodal_short_pct":  _pct(sum(1 for g in cycle_gaps if g < 30), len(cycle_gaps)),
        "bimodal_long_pct":   _pct(sum(1 for g in cycle_gaps if g >= 200), len(cycle_gaps)),
    }


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------

def aggregate(
    records: list[dict[str, Any]],
    cycle_gaps: list[float] | None = None,
) -> dict[str, Any]:
    """Compute all probe statistics from epoch records."""
    if not records:
        return {
            "total_epochs": 0,
            "guardrail": (
                "Offline observability only. Does not change runtime, strategy, "
                "risk, execution, or paper/live separation."
            ),
        }

    total = len(records)

    # Overall timing stats (seconds_since_open)
    disc_ssos  = [r["first_discovered_sso"]  for r in records if r.get("first_discovered_sso")  is not None]
    tok_ssos   = [r["first_token_ready_sso"] for r in records if r.get("first_token_ready_sso") is not None]
    ob_ssos    = [r["first_orderbook_sso"]   for r in records if r.get("first_orderbook_sso")   is not None]
    trad_ssos  = [r["first_tradable_sso"]    for r in records if r.get("first_tradable_sso")    is not None]

    # Derived delays
    tok_delays  = [r["token_publication_delay_seconds"] for r in records if r.get("token_publication_delay_seconds") is not None]
    ob_delays   = [r["orderbook_ready_delay_seconds"]   for r in records if r.get("orderbook_ready_delay_seconds")   is not None]
    trad_delays = [r["tradable_delay_seconds"]          for r in records if r.get("tradable_delay_seconds")          is not None]

    # Milestone attainment counts
    n_has_tok   = sum(1 for r in records if r.get("has_token_ready"))
    n_has_ob    = sum(1 for r in records if r.get("has_orderbook"))
    n_has_trad  = sum(1 for r in records if r.get("has_tradable"))

    # Window distribution
    tok_window_dist  = _window_dist(records, "tok_window")
    ob_window_dist   = _window_dist(records, "ob_window")
    trad_window_dist = _window_dist(records, "trad_window")

    # % TOKEN_READY inside specific windows
    tok_in_opening = tok_window_dist.get("OPENING_SCAN", 0)
    tok_in_active  = tok_window_dist.get("ACTIVE_INVENTORY_TRADING", 0)

    # % TRADABLE before entry cutoff
    n_trad_before_cutoff = sum(1 for r in records if r.get("tradable_before_cutoff"))

    # BTC vs ETH split
    btc_recs = [r for r in records if r.get("asset") == "BTC"]
    eth_recs = [r for r in records if r.get("asset") == "ETH"]

    # Preload correlation on tradable_delay
    preload_corr = _preload_correlation(records, "tradable_delay_seconds")

    # Cycle gap correlation
    cycle_corr = _cycle_gap_correlation(records, cycle_gaps or [])

    # Epochs where TOKEN_READY was NOT achieved before FINAL_DERISK
    n_tok_missed_active = sum(
        1 for r in records
        if r.get("has_token_ready")
        and r.get("tok_window") not in {"OPENING_SCAN", "ACTIVE_INVENTORY_TRADING"}
    )
    n_tok_never = sum(1 for r in records if not r.get("has_token_ready"))
    n_trad_after_active = sum(
        1 for r in records
        if r.get("has_tradable")
        and r.get("trad_window") not in {"OPENING_SCAN", "ACTIVE_INVENTORY_TRADING"}
    )

    def _asset_stats(recs: list[dict[str, Any]]) -> dict[str, Any]:
        asset_total = len(recs)
        at_ssos = [r["first_token_ready_sso"] for r in recs if r.get("first_token_ready_sso") is not None]
        ao_ssos = [r["first_orderbook_sso"] for r in recs if r.get("first_orderbook_sso") is not None]
        atr_ssos = [r["first_tradable_sso"] for r in recs if r.get("first_tradable_sso") is not None]
        return {
            "total_epochs":                     asset_total,
            "has_token_ready_count":            sum(1 for r in recs if r.get("has_token_ready")),
            "has_token_ready_pct":              _pct(sum(1 for r in recs if r.get("has_token_ready")), asset_total),
            "has_tradable_count":               sum(1 for r in recs if r.get("has_tradable")),
            "has_tradable_pct":                 _pct(sum(1 for r in recs if r.get("has_tradable")), asset_total),
            "tradable_before_cutoff_count":     sum(1 for r in recs if r.get("tradable_before_cutoff")),
            "tradable_before_cutoff_pct":       _pct(sum(1 for r in recs if r.get("tradable_before_cutoff")), asset_total),
            "tok_window_dist":                  _window_dist(recs, "tok_window"),
            "trad_window_dist":                 _window_dist(recs, "trad_window"),
            "first_token_ready_sso_stats":      _stats([float(v) for v in at_ssos]),
            "first_orderbook_sso_stats":        _stats([float(v) for v in ao_ssos]),
            "first_tradable_sso_stats":         _stats([float(v) for v in atr_ssos]),
        }

    return {
        "total_epochs": total,
        # ---- Milestone timing stats (seconds_since_open) ----
        "first_discovered_sso_stats":       _stats([float(v) for v in disc_ssos]),
        "first_token_ready_sso_stats":      _stats([float(v) for v in tok_ssos]),
        "first_orderbook_sso_stats":        _stats([float(v) for v in ob_ssos]),
        "first_executable_sso_stats":       _stats([float(v) for v in trad_ssos]),
        # ---- Derived delay stats ----
        "token_publication_delay_stats":    _stats([float(v) for v in tok_delays]),
        "orderbook_ready_delay_stats":      _stats([float(v) for v in ob_delays]),
        "tradable_delay_stats":             _stats([float(v) for v in trad_delays]),
        # ---- Milestone attainment ----
        "epochs_with_token_ready_count":    n_has_tok,
        "epochs_with_token_ready_pct":      _pct(n_has_tok, total),
        "epochs_with_orderbook_count":      n_has_ob,
        "epochs_with_orderbook_pct":        _pct(n_has_ob, total),
        "epochs_with_tradable_count":       n_has_trad,
        "epochs_with_tradable_pct":         _pct(n_has_trad, total),
        "epochs_token_never_reached_count": n_tok_never,
        "epochs_token_never_reached_pct":   _pct(n_tok_never, total),
        # ---- Window distribution ----
        "tok_window_distribution":          tok_window_dist,
        "ob_window_distribution":           ob_window_dist,
        "trad_window_distribution":         trad_window_dist,
        # ---- Key percentages ----
        "pct_token_ready_in_opening_scan":       _pct(tok_in_opening, total),
        "pct_token_ready_in_active_window":      _pct(tok_in_active, total),
        "pct_token_missed_active_window":        _pct(tok_in_opening + tok_in_active, total),  # reached during active periods
        "pct_tradable_before_entry_cutoff":      _pct(n_trad_before_cutoff, total),
        "pct_token_ready_missed_active_window":  _pct(n_tok_missed_active, total),  # had token but outside active window
        "pct_tradable_missed_active_window":     _pct(n_trad_after_active, total),
        # ---- Per-asset breakdown ----
        "asset_breakdown": {
            "BTC": _asset_stats(btc_recs),
            "ETH": _asset_stats(eth_recs),
        },
        # ---- Preload correlation ----
        "preload_tradable_delay_correlation": preload_corr,
        # ---- Cycle gap correlation ----
        "cycle_gap_correlation": cycle_corr,
        # Guardrail
        "guardrail": (
            "Offline observability only. Does not change runtime, strategy, "
            "risk, execution, or paper/live separation."
        ),
    }


# ---------------------------------------------------------------------------
# Console rendering
# ---------------------------------------------------------------------------

def render_console(stats: dict[str, Any], date_str: str = "") -> None:
    total = stats.get("total_epochs", 0)
    hdr = f"Epoch Boundary Alignment Probe v1  |  date={date_str}  |  epochs={total}"
    print()
    print("=" * len(hdr))
    print(hdr)
    print("=" * len(hdr))

    if total == 0:
        print("  No epoch records found - nothing to report.")
        print()
        return

    def _row(label: str, val: Any) -> None:
        print(f"  {label:<52} {val}")

    def _stat_row(label: str, s: dict[str, Any]) -> None:
        if s.get("n", 0) == 0:
            _row(label, "n=0  (no data)")
            return
        _row(label, f"n={s['n']}  p50={s['p50']}s  p90={s['p90']}s  mean={s['mean']}s  max={s['max']}s")

    print()
    print("  -- Milestone Timing (seconds since epoch open) -----------------")
    _stat_row("first_discovered_sso:", stats.get("first_discovered_sso_stats", {}))
    _stat_row("first_token_ready_sso:", stats.get("first_token_ready_sso_stats", {}))
    _stat_row("first_orderbook_sso:", stats.get("first_orderbook_sso_stats", {}))
    _stat_row("first_executable/TRADABLE_sso:", stats.get("first_executable_sso_stats", {}))

    print()
    print("  -- Epoch-Open to Milestone Delays ------------------------------")
    _stat_row("token_publication_delay:", stats.get("token_publication_delay_stats", {}))
    _stat_row("orderbook_ready_delay:", stats.get("orderbook_ready_delay_stats", {}))
    _stat_row("tradable_delay:", stats.get("tradable_delay_stats", {}))

    print()
    print("  -- Milestone Attainment -----------------------------------------")
    _row("epochs with TOKEN_READY:",
         f"{stats.get('epochs_with_token_ready_count', 0)} / {total}  ({stats.get('epochs_with_token_ready_pct', 0)}%)")
    _row("epochs with orderbook:",
         f"{stats.get('epochs_with_orderbook_count', 0)} / {total}  ({stats.get('epochs_with_orderbook_pct', 0)}%)")
    _row("epochs with TRADABLE:",
         f"{stats.get('epochs_with_tradable_count', 0)} / {total}  ({stats.get('epochs_with_tradable_pct', 0)}%)")
    _row("epochs TOKEN never reached:",
         f"{stats.get('epochs_token_never_reached_count', 0)} / {total}  ({stats.get('epochs_token_never_reached_pct', 0)}%)")

    print()
    print("  -- Window Distribution ------------------------------------------")
    tok_wd  = stats.get("tok_window_distribution", {})
    trad_wd = stats.get("trad_window_distribution", {})
    _row("TOKEN_READY in OPENING_SCAN:",
         f"{tok_wd.get('OPENING_SCAN', 0)} epochs  ({stats.get('pct_token_ready_in_opening_scan', 0)}%)")
    _row("TOKEN_READY in ACTIVE_INVENTORY_TRADING:",
         f"{tok_wd.get('ACTIVE_INVENTORY_TRADING', 0)} epochs  ({stats.get('pct_token_ready_in_active_window', 0)}%)")
    _row("TOKEN_READY in PROFIT_MANAGEMENT:",
         f"{tok_wd.get('PROFIT_MANAGEMENT', 0)} epochs")
    _row("TOKEN_READY in FINAL_DERISK:",
         f"{tok_wd.get('FINAL_DERISK', 0)} epochs")
    _row("TOKEN_READY UNKNOWN (never reached):",
         f"{tok_wd.get('UNKNOWN', 0)} epochs")
    _row("TRADABLE before entry cutoff:",
         f"{stats.get('epochs_with_tradable_count', 0)} with tradable  |  before-cutoff: {stats.get('pct_tradable_before_entry_cutoff', 0)}% of epochs")
    _row("TRADABLE missed ACTIVE window:",
         f"{stats.get('pct_tradable_missed_active_window', 0)}% of epochs")

    print()
    print("  -- BTC vs ETH ---------------------------------------------------")
    for asset in ("BTC", "ETH"):
        ab = stats.get("asset_breakdown", {}).get(asset, {})
        at = ab.get("total_epochs", 0)
        if at == 0:
            print(f"  {asset}: no data")
            continue
        ts = ab.get("first_token_ready_sso_stats", {})
        trs = ab.get("first_tradable_sso_stats", {})
        print(f"  {asset}: epochs={at}  "
              f"tok_ready={ab.get('has_token_ready_pct', 0)}%  "
              f"tradable={ab.get('has_tradable_pct', 0)}%  "
              f"tok_p50={ts.get('p50')}s  "
              f"trad_p50={trs.get('p50')}s  "
              f"before_cutoff={ab.get('tradable_before_cutoff_pct', 0)}%")
        tok_wd_a = ab.get("tok_window_dist", {})
        print(f"         tok windows: OPEN={tok_wd_a.get('OPENING_SCAN', 0)} "
              f"ACTIVE={tok_wd_a.get('ACTIVE_INVENTORY_TRADING', 0)} "
              f"PROFIT={tok_wd_a.get('PROFIT_MANAGEMENT', 0)} "
              f"FINAL={tok_wd_a.get('FINAL_DERISK', 0)} "
              f"UNKNOWN={tok_wd_a.get('UNKNOWN', 0)}")

    print()
    print("  -- Preload Correlation (tradable_delay) -------------------------")
    pc = stats.get("preload_tradable_delay_correlation", {})
    if pc.get("cache_hit_n", 0) > 0 or pc.get("cache_miss_n", 0) > 0:
        _row("preload cache HIT  - tradable_delay p50:",
             f"{pc.get('preload_cache_hit_p50')}s  (n={pc.get('cache_hit_n', 0)})")
        _row("preload cache MISS - tradable_delay p50:",
             f"{pc.get('preload_cache_miss_p50')}s  (n={pc.get('cache_miss_n', 0)})")
    else:
        print("  (preload correlation data not available)")

    print()
    print("  -- Cycle Gap (from research_log) --------------------------------")
    cg = stats.get("cycle_gap_correlation", {})
    if cg.get("available"):
        gs = cg.get("cycle_gap_stats", {})
        _row("cycle gap:", f"n={gs.get('n')}  p50={gs.get('p50')}s  p75={gs.get('p75')}s  p90={gs.get('p90')}s")
        _row("cycles < 30s (short cluster):",
             f"{cg.get('bimodal_short_n', 0)}  ({cg.get('bimodal_short_pct', 0)}%)")
        _row("cycles >= 200s (long/blocking):",
             f"{cg.get('bimodal_long_n', 0)}  ({cg.get('bimodal_long_pct', 0)}%)")
    else:
        print("  (cycle gap data not available from research_log)")

    print()
    print(f"  Guardrail: {stats.get('guardrail', '')}")
    print()


# ---------------------------------------------------------------------------
# Report writing
# ---------------------------------------------------------------------------

def write_report(
    stats: dict[str, Any],
    date_str: str,
    report_dir: Path = DEFAULT_REPORT_DIR,
    run_id: str | None = None,
    asset_filter: str | None = None,
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    suffix = ""
    if asset_filter:
        suffix += f"_{asset_filter.upper()}"
    fname = f"epoch_boundary_alignment_probe_{date_str}{suffix}.json"
    out_path = report_dir / fname
    payload = {
        **stats,
        "date": date_str,
        "run_id_filter": run_id or "all",
        "asset_filter": asset_filter or "all",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "epoch_boundary_alignment_probe_v1",
    }
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return out_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Epoch Boundary Alignment Probe v1 - offline analysis only."
    )
    parser.add_argument("--date", required=True, help="Date to analyse (YYYY-MM-DD)")
    parser.add_argument("--write-report", action="store_true", help="Write JSON report to runtime/reports/")
    parser.add_argument("--run-id", default=None, help="Filter to a single run_id")
    parser.add_argument("--asset", default=None, choices=["BTC", "ETH"], help="Filter to a single asset")
    parser.add_argument(
        "--quant-data-dir",
        default=None,
        help="Override runtime/quant_data directory",
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        help="Override runtime/reports directory",
    )
    args = parser.parse_args(argv)

    quant_data_dir = Path(args.quant_data_dir) if args.quant_data_dir else DEFAULT_QUANT_DATA_DIR
    report_dir = Path(args.report_dir) if args.report_dir else DEFAULT_REPORT_DIR

    snap_events    = load_snapshot_events(args.date, quant_data_dir, args.run_id, args.asset)
    research_events = load_research_events(args.date, quant_data_dir, args.run_id, args.asset)

    records    = build_epoch_records(snap_events)
    cycle_gaps = extract_cycle_gaps(research_events)
    stats      = aggregate(records, cycle_gaps)

    render_console(stats, args.date)

    if args.write_report:
        out = write_report(stats, args.date, report_dir, args.run_id, args.asset)
        print(f"  Report written: {out}")
        print()


if __name__ == "__main__":
    main()
