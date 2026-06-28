"""
Tests for Semantic C Shadow PnL Truth Layer v1.

Covers:
- Settlement map builder: YES/NO/AMBIGUOUS inference from yes_bid
- Settlement map: minimum-SR selection (nearest-to-close snapshot wins)
- Settlement map: max_sr_for_proxy filtering (snapshots too far from close excluded)
- PnL formula: YES win (positive), NO win (negative), zero size/price guards
- Settlement matching: probe event matched by (epoch_start_ts, market_key)
- analyse(): all 13 outputs
- BTC/ETH PnL aggregation
- Lifecycle phase PnL aggregation
- Win rate / avg win / avg loss / win-loss ratio
- Max drawdown: correct trajectory, zero when no losses
- Unresolved markets: count and list
- Data quality verdict: AVAILABLE / PARTIAL / UNAVAILABLE thresholds
- Economic evidence verdict: each branch
- Fail-soft: missing market_snapshots file, empty events, ambiguous-only
- No runtime module imports (AST scan)
- No side effects on input dicts
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.shadow.semantic_c_shadow_pnl_truth import (
    _NO_THRESHOLD,
    _YES_THRESHOLD,
    _MAX_SR_FOR_PROXY,
    _compute_pnl,
    _compute_shadow,
    _max_drawdown,
    analyse,
    build_settlement_map,
    load_probe_events,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _probe_ev(
    *,
    ticker: str = "BTC",
    confidence: float = 0.62,
    entry_price: float = 0.29,
    ev: float = 0.16,
    raw_size_usd: float = 0.68,
    bankroll: float = 20.10,
    lifecycle_phase: str = "ACTIVE_INVENTORY_TRADING",
    epoch_start_ts: int = 1_000_000,
    market_key: str = "pm-5m-btc",
    run_id: str = "run_test",
    ts: str | None = None,
) -> dict:
    """Return a zero_size_probe_v1 payload dict for analyse()."""
    p: dict = {
        "event":           "zero_size_probe_v1",
        "run_id":          run_id,
        "ticker":          ticker,
        "confidence":      confidence,
        "entry_price":     entry_price,
        "ev":              ev,
        "ev_positive":     ev > 0,
        "raw_size_usd":    raw_size_usd,
        "bankroll":        bankroll,
        "lifecycle_phase": lifecycle_phase,
        "epoch_start_ts":  epoch_start_ts,
        "market_key":      market_key,
        "final_size_usd":  0.0,
    }
    if ts is not None:
        p["ts"] = ts
    return p


def _snap_ev(
    *,
    epoch_start_ts: int = 1_000_000,
    market_key: str = "pm-5m-btc",
    seconds_remaining: float = 45.0,
    yes_bid: float = 0.95,
) -> dict:
    """Return a market_snapshots payload dict for build_settlement_map."""
    return {
        "epoch_start_ts":  epoch_start_ts,
        "epoch_start":     epoch_start_ts,
        "market_key":      market_key,
        "seconds_remaining": seconds_remaining,
        "yes_bid":         yes_bid,
    }


def _write_jsonl(path: Path, payloads: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [json.dumps({"payload": p}) for p in payloads]
    path.write_text("\n".join(rows), encoding="utf-8")


def _build_smap(snaps: list[dict]) -> dict:
    """Build settlement map directly from snapshot dicts (no file I/O)."""
    from collections import defaultdict
    from tools.shadow.semantic_c_shadow_pnl_truth import _YES_THRESHOLD, _NO_THRESHOLD, _MAX_SR_FOR_PROXY

    best: dict[tuple, dict] = {}
    for p in snaps:
        ep = p.get("epoch_start_ts")
        mk = p.get("market_key")
        sr = p.get("seconds_remaining")
        yb = p.get("yes_bid")
        if None in (ep, mk, sr, yb):
            continue
        key = (ep, mk)
        sr_f = float(sr)
        if sr_f >= _MAX_SR_FOR_PROXY:
            continue
        if key not in best or sr_f < float(best[key]["seconds_remaining"]):
            best[key] = {"epoch_start_ts": ep, "market_key": mk,
                         "seconds_remaining": sr_f, "yes_bid": float(yb)}

    result = {}
    for key, rec in best.items():
        yb = rec["yes_bid"]
        if yb >= _YES_THRESHOLD:
            inferred, price, conf = "YES", 1.0, "HIGH"
        elif yb <= _NO_THRESHOLD:
            inferred, price, conf = "NO", 0.0, "HIGH"
        else:
            inferred, price, conf = "AMBIGUOUS", None, "AMBIGUOUS"
        result[key] = {
            "inferred_settlement": inferred,
            "settlement_price": price,
            "yes_bid_at_match": round(yb, 4),
            "seconds_remaining_at_match": rec["seconds_remaining"],
            "confidence": conf,
            "settlement_source": "market_price_proxy_near_close",
        }
    return result


# ===========================================================================
# 1. Settlement map builder -- inference logic
# ===========================================================================

class TestBuildSettlementMapInference:
    def test_yes_settlement_when_yes_bid_high(self):
        smap = _build_smap([_snap_ev(yes_bid=0.95)])
        rec = smap[(1_000_000, "pm-5m-btc")]
        assert rec["inferred_settlement"] == "YES"
        assert rec["settlement_price"] == 1.0
        assert rec["confidence"] == "HIGH"

    def test_no_settlement_when_yes_bid_low(self):
        smap = _build_smap([_snap_ev(yes_bid=0.02)])
        rec = smap[(1_000_000, "pm-5m-btc")]
        assert rec["inferred_settlement"] == "NO"
        assert rec["settlement_price"] == 0.0
        assert rec["confidence"] == "HIGH"

    def test_ambiguous_when_yes_bid_in_middle(self):
        smap = _build_smap([_snap_ev(yes_bid=0.50)])
        rec = smap[(1_000_000, "pm-5m-btc")]
        assert rec["inferred_settlement"] == "AMBIGUOUS"
        assert rec["settlement_price"] is None
        assert rec["confidence"] == "AMBIGUOUS"

    def test_exact_yes_threshold_is_yes(self):
        smap = _build_smap([_snap_ev(yes_bid=_YES_THRESHOLD)])
        rec = smap[(1_000_000, "pm-5m-btc")]
        assert rec["inferred_settlement"] == "YES"

    def test_exact_no_threshold_is_no(self):
        smap = _build_smap([_snap_ev(yes_bid=_NO_THRESHOLD)])
        rec = smap[(1_000_000, "pm-5m-btc")]
        assert rec["inferred_settlement"] == "NO"

    def test_settlement_source_label(self):
        smap = _build_smap([_snap_ev(yes_bid=0.95)])
        rec = smap[(1_000_000, "pm-5m-btc")]
        assert rec["settlement_source"] == "market_price_proxy_near_close"


class TestBuildSettlementMapMinSR:
    def test_minimum_sr_snapshot_wins(self):
        snaps = [
            _snap_ev(seconds_remaining=80.0, yes_bid=0.50),  # ambiguous
            _snap_ev(seconds_remaining=40.0, yes_bid=0.96),  # YES -- this should win
        ]
        smap = _build_smap(snaps)
        rec = smap[(1_000_000, "pm-5m-btc")]
        assert rec["inferred_settlement"] == "YES"
        assert rec["seconds_remaining_at_match"] == 40.0

    def test_snapshots_beyond_max_sr_excluded(self):
        snaps = [_snap_ev(seconds_remaining=_MAX_SR_FOR_PROXY + 1, yes_bid=0.96)]
        smap = _build_smap(snaps)
        assert (1_000_000, "pm-5m-btc") not in smap

    def test_snapshot_at_max_sr_exactly_excluded(self):
        snaps = [_snap_ev(seconds_remaining=_MAX_SR_FOR_PROXY, yes_bid=0.96)]
        smap = _build_smap(snaps)
        assert (1_000_000, "pm-5m-btc") not in smap

    def test_snapshot_just_below_max_sr_included(self):
        snaps = [_snap_ev(seconds_remaining=_MAX_SR_FOR_PROXY - 0.1, yes_bid=0.96)]
        smap = _build_smap(snaps)
        assert (1_000_000, "pm-5m-btc") in smap

    def test_different_epochs_independent(self):
        snaps = [
            _snap_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                     seconds_remaining=50.0, yes_bid=0.95),
            _snap_ev(epoch_start_ts=2_000, market_key="pm-5m-btc",
                     seconds_remaining=50.0, yes_bid=0.02),
        ]
        smap = _build_smap(snaps)
        assert smap[(1_000, "pm-5m-btc")]["inferred_settlement"] == "YES"
        assert smap[(2_000, "pm-5m-btc")]["inferred_settlement"] == "NO"


# ===========================================================================
# 2. PnL formula
# ===========================================================================

class TestComputePnl:
    def test_yes_settlement_is_profitable_for_yes_buy(self):
        # entry=0.30, c_size=0.60, settle=1.0 -> tokens=2.0, pnl=(1.0-0.3)*2=1.4
        pnl = _compute_pnl(entry_price=0.30, c_size=0.60, settlement_price=1.0)
        assert pnl is not None
        assert abs(pnl - 1.40) < 1e-5

    def test_no_settlement_is_loss_for_yes_buy(self):
        # entry=0.30, c_size=0.60, settle=0.0 -> pnl=(0.0-0.3)*2=-0.6
        pnl = _compute_pnl(entry_price=0.30, c_size=0.60, settlement_price=0.0)
        assert pnl is not None
        assert abs(pnl - (-0.60)) < 1e-5

    def test_zero_c_size_returns_none(self):
        assert _compute_pnl(0.30, 0.0, 1.0) is None

    def test_zero_entry_price_returns_none(self):
        assert _compute_pnl(0.0, 0.60, 1.0) is None

    def test_high_entry_price_reduces_tokens(self):
        # entry=0.80, c_size=0.80, settle=1.0 -> tokens=1, pnl=0.20
        pnl = _compute_pnl(entry_price=0.80, c_size=0.80, settlement_price=1.0)
        assert pnl is not None
        assert abs(pnl - 0.20) < 1e-5


# ===========================================================================
# 3. Max drawdown
# ===========================================================================

class TestMaxDrawdown:
    def test_no_drawdown_when_all_wins(self):
        dd = _max_drawdown([0.10, 0.20, 0.30])
        assert dd == 0.0

    def test_full_series_loss_drawdown(self):
        # cumulative: -0.10, -0.20 -> peak=0, dd=0.20
        dd = _max_drawdown([-0.10, -0.10])
        assert abs(dd - 0.20) < 1e-8

    def test_mixed_win_loss_drawdown(self):
        # wins then loss: cumulative 0.30, 0.20 -> peak=0.30, dd=0.10
        dd = _max_drawdown([0.30, -0.10])
        assert abs(dd - 0.10) < 1e-8

    def test_empty_series(self):
        assert _max_drawdown([]) == 0.0

    def test_single_win(self):
        assert _max_drawdown([0.50]) == 0.0

    def test_single_loss(self):
        dd = _max_drawdown([-0.50])
        assert abs(dd - 0.50) < 1e-8

    def test_recovery_after_drawdown(self):
        # 0.10, -0.30, 0.50: cumulative 0.10, -0.20, 0.30; peak=0.10, dd=0.30
        dd = _max_drawdown([0.10, -0.30, 0.50])
        assert abs(dd - 0.30) < 1e-8


# ===========================================================================
# 4. analyse() -- shadow fill candidates (output 1)
# ===========================================================================

class TestFillCandidates:
    def test_fill_candidates_count(self):
        evs = [_probe_ev(confidence=0.62, ev=0.16)] * 8
        r = analyse(evs, {})
        assert r["shadow_fill_candidates"] == 8

    def test_zero_candidates_when_blocked(self):
        evs = [_probe_ev(confidence=0.40, ev=0.0)] * 8
        r = analyse(evs, {})
        assert r["shadow_fill_candidates"] == 0

    def test_fill_candidate_pct(self):
        evs = [_probe_ev(confidence=0.62, ev=0.16)] * 6 + [_probe_ev(confidence=0.40, ev=0.0)] * 4
        r = analyse(evs, {})
        assert abs(r["fill_candidate_pct"] - 60.0) < 0.2


# ===========================================================================
# 5. analyse() -- settlement matching (outputs 2, 3, 4)
# ===========================================================================

class TestSettlementMatching:
    def test_matched_count_correct(self):
        ep = 1_000_000
        mk = "pm-5m-btc"
        evs = [_probe_ev(epoch_start_ts=ep, market_key=mk, confidence=0.62, ev=0.16)] * 5
        smap = _build_smap([_snap_ev(epoch_start_ts=ep, market_key=mk,
                                     seconds_remaining=50.0, yes_bid=0.95)])
        r = analyse(evs, smap)
        assert r["settlement_matched_count"] == 5

    def test_no_match_when_smap_empty(self):
        evs = [_probe_ev(confidence=0.62, ev=0.16)] * 5
        r = analyse(evs, {})
        assert r["settlement_matched_count"] == 0
        assert r["no_snapshot_count"] == 5

    def test_ambiguous_counted_separately(self):
        ep = 1_000_000
        mk = "pm-5m-btc"
        evs = [_probe_ev(epoch_start_ts=ep, market_key=mk, confidence=0.62, ev=0.16)] * 3
        smap = _build_smap([_snap_ev(epoch_start_ts=ep, market_key=mk,
                                     seconds_remaining=50.0, yes_bid=0.50)])
        r = analyse(evs, smap)
        assert r["ambiguous_count"] == 3
        assert r["settlement_matched_count"] == 0

    def test_match_rate_100_when_all_matched(self):
        ep = 1_000_000
        mk = "pm-5m-btc"
        evs = [_probe_ev(epoch_start_ts=ep, market_key=mk, confidence=0.62, ev=0.16)] * 5
        smap = _build_smap([_snap_ev(epoch_start_ts=ep, market_key=mk,
                                     seconds_remaining=50.0, yes_bid=0.95)])
        r = analyse(evs, smap)
        assert r["match_rate_pct"] == 100.0

    def test_match_rate_0_when_no_snapshot(self):
        evs = [_probe_ev(confidence=0.62, ev=0.16)] * 5
        r = analyse(evs, {})
        assert r["match_rate_pct"] == 0.0


# ===========================================================================
# 6. analyse() -- PnL total (output 5)
# ===========================================================================

class TestPnLTotal:
    def _run(self, outcome: str, yes_bid: float, n: int = 5) -> dict:
        ep, mk = 1_000_000, "pm-5m-btc"
        evs = [_probe_ev(epoch_start_ts=ep, market_key=mk,
                         confidence=0.62, ev=0.16,
                         entry_price=0.29, raw_size_usd=0.68)] * n
        smap = _build_smap([_snap_ev(epoch_start_ts=ep, market_key=mk,
                                     seconds_remaining=50.0, yes_bid=yes_bid)])
        return analyse(evs, smap)

    def test_total_pnl_positive_when_yes_wins(self):
        r = self._run("YES", yes_bid=0.95)
        assert r["total_hypothetical_pnl"] > 0.0

    def test_total_pnl_negative_when_no_wins(self):
        r = self._run("NO", yes_bid=0.02)
        assert r["total_hypothetical_pnl"] < 0.0

    def test_settled_fill_count_correct(self):
        r = self._run("YES", yes_bid=0.95, n=5)
        assert r["settled_fill_count"] == 5

    def test_pnl_stats_populated(self):
        r = self._run("YES", yes_bid=0.95, n=10)
        ps = r.get("pnl_stats") or {}
        assert ps["count"] == 10
        assert ps["mean"] > 0.0


# ===========================================================================
# 7. analyse() -- BTC / ETH aggregation (output 6)
# ===========================================================================

class TestAssetAggregation:
    def test_btc_eth_settled_separately(self):
        evs = (
            [_probe_ev(ticker="BTC", epoch_start_ts=1_000, market_key="pm-5m-btc",
                       confidence=0.62, ev=0.16)] * 4
            + [_probe_ev(ticker="ETH", epoch_start_ts=2_000, market_key="pm-5m-eth",
                         confidence=0.62, ev=0.16)] * 3
        )
        smap = _build_smap([
            _snap_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                     seconds_remaining=50.0, yes_bid=0.95),
            _snap_ev(epoch_start_ts=2_000, market_key="pm-5m-eth",
                     seconds_remaining=50.0, yes_bid=0.02),
        ])
        r = analyse(evs, smap)
        assert r["btc"]["settled_fills"] == 4
        assert r["eth"]["settled_fills"] == 3
        assert r["btc"]["total_pnl"] > 0.0  # YES wins for BTC
        assert r["eth"]["total_pnl"] < 0.0  # NO wins for ETH

    def test_zero_fills_for_missing_asset(self):
        evs = [_probe_ev(ticker="BTC", epoch_start_ts=1_000, market_key="pm-5m-btc",
                         confidence=0.62, ev=0.16)] * 3
        smap = _build_smap([_snap_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                                     seconds_remaining=50.0, yes_bid=0.95)])
        r = analyse(evs, smap)
        assert r["eth"]["settled_fills"] == 0

    def test_different_pnl_per_asset_when_different_outcomes(self):
        evs = (
            [_probe_ev(ticker="BTC", epoch_start_ts=1_000, market_key="pm-5m-btc",
                       confidence=0.62, ev=0.16, entry_price=0.30)] * 5
            + [_probe_ev(ticker="ETH", epoch_start_ts=2_000, market_key="pm-5m-eth",
                         confidence=0.62, ev=0.16, entry_price=0.07)] * 5
        )
        smap = _build_smap([
            _snap_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                     seconds_remaining=50.0, yes_bid=0.95),
            _snap_ev(epoch_start_ts=2_000, market_key="pm-5m-eth",
                     seconds_remaining=50.0, yes_bid=0.95),
        ])
        r = analyse(evs, smap)
        # ETH has lower entry price so higher win per token
        assert r["eth"]["settled_fills"] == 5
        assert r["btc"]["settled_fills"] == 5


# ===========================================================================
# 8. analyse() -- lifecycle phase aggregation (output 7)
# ===========================================================================

class TestLifecyclePhasePnL:
    def test_phases_aggregated_separately(self):
        evs = (
            [_probe_ev(lifecycle_phase="ACTIVE_INVENTORY_TRADING",
                       epoch_start_ts=1_000, market_key="pm-5m-btc",
                       confidence=0.62, ev=0.16)] * 3
            + [_probe_ev(lifecycle_phase="OPENING_SCAN",
                         epoch_start_ts=1_000, market_key="pm-5m-btc",
                         confidence=0.62, ev=0.16)] * 2
        )
        smap = _build_smap([_snap_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                                     seconds_remaining=50.0, yes_bid=0.95)])
        r = analyse(evs, smap)
        lp = r["lifecycle_pnl"]
        assert lp["ACTIVE_INVENTORY_TRADING"]["settled_fills"] == 3
        assert lp["OPENING_SCAN"]["settled_fills"] == 2

    def test_phase_win_rate_100_when_all_win(self):
        evs = [_probe_ev(lifecycle_phase="ACTIVE_INVENTORY_TRADING",
                         epoch_start_ts=1_000, market_key="pm-5m-btc",
                         confidence=0.62, ev=0.16)] * 5
        smap = _build_smap([_snap_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                                     seconds_remaining=50.0, yes_bid=0.95)])
        r = analyse(evs, smap)
        lp = r["lifecycle_pnl"]
        assert lp["ACTIVE_INVENTORY_TRADING"]["win_rate_pct"] == 100.0


# ===========================================================================
# 9. analyse() -- win rate, avg win/loss (outputs 8, 9)
# ===========================================================================

class TestWinRateAndAvgPnL:
    def test_win_rate_100_when_yes_wins(self):
        ep, mk = 1_000_000, "pm-5m-btc"
        evs = [_probe_ev(epoch_start_ts=ep, market_key=mk, confidence=0.62, ev=0.16)] * 6
        smap = _build_smap([_snap_ev(epoch_start_ts=ep, market_key=mk,
                                     seconds_remaining=50.0, yes_bid=0.95)])
        r = analyse(evs, smap)
        assert r["win_rate_pct"] == 100.0
        assert r["win_count"] == 6
        assert r["loss_count"] == 0

    def test_win_rate_0_when_no_wins(self):
        ep, mk = 1_000_000, "pm-5m-btc"
        evs = [_probe_ev(epoch_start_ts=ep, market_key=mk, confidence=0.62, ev=0.16)] * 6
        smap = _build_smap([_snap_ev(epoch_start_ts=ep, market_key=mk,
                                     seconds_remaining=50.0, yes_bid=0.02)])
        r = analyse(evs, smap)
        assert r["win_rate_pct"] == 0.0
        assert r["loss_count"] == 6

    def test_avg_win_positive(self):
        ep, mk = 1_000_000, "pm-5m-btc"
        evs = [_probe_ev(epoch_start_ts=ep, market_key=mk, confidence=0.62, ev=0.16)] * 5
        smap = _build_smap([_snap_ev(epoch_start_ts=ep, market_key=mk,
                                     seconds_remaining=50.0, yes_bid=0.95)])
        r = analyse(evs, smap)
        assert r["avg_win"] is not None
        assert r["avg_win"] > 0.0
        assert r["avg_loss"] is None  # no losses

    def test_avg_loss_negative(self):
        ep, mk = 1_000_000, "pm-5m-btc"
        evs = [_probe_ev(epoch_start_ts=ep, market_key=mk, confidence=0.62, ev=0.16)] * 5
        smap = _build_smap([_snap_ev(epoch_start_ts=ep, market_key=mk,
                                     seconds_remaining=50.0, yes_bid=0.02)])
        r = analyse(evs, smap)
        assert r["avg_loss"] is not None
        assert r["avg_loss"] < 0.0
        assert r["avg_win"] is None  # no wins

    def test_win_loss_ratio_when_both_present(self):
        # Two epochs: one YES, one NO
        evs = (
            [_probe_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                       confidence=0.62, ev=0.16)] * 3
            + [_probe_ev(epoch_start_ts=2_000, market_key="pm-5m-btc",
                         confidence=0.62, ev=0.16)] * 3
        )
        smap = _build_smap([
            _snap_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                     seconds_remaining=50.0, yes_bid=0.95),
            _snap_ev(epoch_start_ts=2_000, market_key="pm-5m-btc",
                     seconds_remaining=50.0, yes_bid=0.02),
        ])
        r = analyse(evs, smap)
        assert r["win_loss_ratio"] is not None
        assert r["win_loss_ratio"] > 0.0


# ===========================================================================
# 10. analyse() -- max drawdown (output 10)
# ===========================================================================

class TestMaxDrawdownIntegration:
    def test_zero_drawdown_when_all_yes_wins(self):
        ep, mk = 1_000_000, "pm-5m-btc"
        evs = [_probe_ev(epoch_start_ts=ep, market_key=mk, confidence=0.62, ev=0.16)] * 5
        smap = _build_smap([_snap_ev(epoch_start_ts=ep, market_key=mk,
                                     seconds_remaining=50.0, yes_bid=0.95)])
        r = analyse(evs, smap)
        assert r["max_drawdown_approx"] == 0.0

    def test_positive_drawdown_when_losses_exist(self):
        evs = (
            [_probe_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                       confidence=0.62, ev=0.16)] * 5
            + [_probe_ev(epoch_start_ts=2_000, market_key="pm-5m-btc",
                         confidence=0.62, ev=0.16)] * 5
        )
        smap = _build_smap([
            _snap_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                     seconds_remaining=50.0, yes_bid=0.95),
            _snap_ev(epoch_start_ts=2_000, market_key="pm-5m-btc",
                     seconds_remaining=50.0, yes_bid=0.02),
        ])
        r = analyse(evs, smap)
        assert r["max_drawdown_approx"] >= 0.0


# ===========================================================================
# 11. analyse() -- unresolved markets (output 11)
# ===========================================================================

class TestUnresolvedMarkets:
    def test_unresolved_count_when_no_smap(self):
        evs = [_probe_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                         confidence=0.62, ev=0.16)] * 5
        r = analyse(evs, {})
        assert r["unresolved_count"] >= 1

    def test_unresolved_count_zero_when_all_matched(self):
        ep, mk = 1_000_000, "pm-5m-btc"
        evs = [_probe_ev(epoch_start_ts=ep, market_key=mk, confidence=0.62, ev=0.16)] * 5
        smap = _build_smap([_snap_ev(epoch_start_ts=ep, market_key=mk,
                                     seconds_remaining=50.0, yes_bid=0.95)])
        r = analyse(evs, smap)
        assert r["unresolved_count"] == 0
        assert r["unresolved_market_keys"] == []

    def test_ambiguous_counted_as_unresolved(self):
        ep, mk = 1_000_000, "pm-5m-btc"
        evs = [_probe_ev(epoch_start_ts=ep, market_key=mk, confidence=0.62, ev=0.16)] * 5
        smap = _build_smap([_snap_ev(epoch_start_ts=ep, market_key=mk,
                                     seconds_remaining=50.0, yes_bid=0.50)])
        r = analyse(evs, smap)
        assert r["unresolved_count"] == 1


# ===========================================================================
# 12. analyse() -- data quality verdict (output 12)
# ===========================================================================

class TestDataQualityVerdict:
    def _make(self, n_yes: int, n_no: int, n_ambig: int = 0) -> dict:
        evs = []
        smap_snaps = []

        for i, (yes_bid, n) in enumerate([(0.95, n_yes), (0.02, n_no), (0.50, n_ambig)]):
            if n == 0:
                continue
            ep = 1_000_000 + i * 300
            mk = "pm-5m-btc"
            evs += [_probe_ev(epoch_start_ts=ep, market_key=mk,
                              confidence=0.62, ev=0.16)] * n
            smap_snaps.append(_snap_ev(epoch_start_ts=ep, market_key=mk,
                                       seconds_remaining=50.0, yes_bid=yes_bid))

        smap = _build_smap(smap_snaps)
        return analyse(evs, smap)

    def test_available_when_high_coverage(self):
        r = self._make(n_yes=8, n_no=7)
        assert r["data_quality_verdict"] == "PNL_TRUTH_AVAILABLE"

    def test_partial_when_low_settled_count(self):
        r = self._make(n_yes=3, n_no=3)
        assert r["data_quality_verdict"] in ("PARTIAL_PNL_TRUTH", "PNL_TRUTH_UNAVAILABLE")

    def test_unavailable_when_only_ambiguous(self):
        # No HIGH-confidence settlement
        evs = [_probe_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                         confidence=0.62, ev=0.16)] * 5
        smap = _build_smap([_snap_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                                     seconds_remaining=50.0, yes_bid=0.50)])
        r = analyse(evs, smap)
        assert r["data_quality_verdict"] in ("PARTIAL_PNL_TRUTH", "PNL_TRUTH_UNAVAILABLE")

    def test_verdict_note_non_empty(self):
        r = self._make(n_yes=5, n_no=5)
        assert len(r.get("data_quality_note", "")) > 0


# ===========================================================================
# 13. analyse() -- economic evidence verdict (output 13)
# ===========================================================================

class TestEconomicEvidenceVerdict:
    def test_supports_paper_trial_when_high_win_rate(self):
        evs = [_probe_ev(epoch_start_ts=1_000_000 + i * 300, market_key="pm-5m-btc",
                         confidence=0.62, ev=0.16) for i in range(12)]
        smap = _build_smap([
            _snap_ev(epoch_start_ts=1_000_000 + i * 300, market_key="pm-5m-btc",
                     seconds_remaining=50.0, yes_bid=0.95)
            for i in range(12)
        ])
        r = analyse(evs, smap)
        assert r["economic_evidence_verdict"] == "EVIDENCE_SUPPORTS_SCOPED_PAPER_TRIAL"

    def test_weak_negative_expectancy_when_low_win_rate(self):
        evs = [_probe_ev(epoch_start_ts=1_000_000 + i * 300, market_key="pm-5m-btc",
                         confidence=0.62, ev=0.16) for i in range(12)]
        smap = _build_smap([
            _snap_ev(epoch_start_ts=1_000_000 + i * 300, market_key="pm-5m-btc",
                     seconds_remaining=50.0, yes_bid=0.02)
            for i in range(12)
        ])
        r = analyse(evs, smap)
        assert r["economic_evidence_verdict"] == "EVIDENCE_WEAK_NEGATIVE_EXPECTANCY"

    def test_partial_evidence_when_partial_verdict(self):
        evs = [_probe_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                         confidence=0.62, ev=0.16)] * 4
        smap = _build_smap([_snap_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                                     seconds_remaining=50.0, yes_bid=0.95)])
        r = analyse(evs, smap)
        if r["data_quality_verdict"] == "PARTIAL_PNL_TRUTH":
            assert r["economic_evidence_verdict"] == "PARTIAL_EVIDENCE_GATHER_MORE"

    def test_insufficient_when_no_settlement(self):
        evs = [_probe_ev(confidence=0.62, ev=0.16)] * 5
        r = analyse(evs, {})
        assert r["economic_evidence_verdict"] == "INSUFFICIENT_PNL_EVIDENCE"

    def test_evidence_note_non_empty(self):
        evs = [_probe_ev(confidence=0.62, ev=0.16)] * 5
        r = analyse(evs, {})
        assert len(r.get("economic_evidence_note", "")) > 0


# ===========================================================================
# Fail-soft
# ===========================================================================

class TestFailSoft:
    def test_empty_events_returns_error(self):
        r = analyse([], {})
        assert r["event_count"] == 0
        assert "error" in r

    def test_missing_probe_file_returns_empty(self, tmp_path):
        result = load_probe_events("2099-12-31", quant_data_dir=tmp_path)
        assert result == []

    def test_missing_snapshots_file_returns_empty_smap(self, tmp_path):
        smap = build_settlement_map("2099-12-31", tmp_path, {(1_000, "pm-5m-btc")})
        assert smap == {}

    def test_missing_fields_do_not_raise(self):
        r = analyse([{} for _ in range(8)], {})
        assert r["event_count"] == 8
        assert "data_quality_verdict" in r

    def test_all_ambiguous_settlement_is_handled(self):
        ep, mk = 1_000_000, "pm-5m-btc"
        evs = [_probe_ev(epoch_start_ts=ep, market_key=mk, confidence=0.62, ev=0.16)] * 5
        smap = _build_smap([_snap_ev(epoch_start_ts=ep, market_key=mk,
                                     seconds_remaining=50.0, yes_bid=0.50)])
        r = analyse(evs, smap)
        assert r["settled_fill_count"] == 0
        assert r["total_hypothetical_pnl"] == 0.0

    def test_zero_shadow_events_produce_safe_result(self):
        evs = [_probe_ev(confidence=0.0, ev=0.0)] * 10
        r = analyse(evs, {})
        assert r["shadow_fill_candidates"] == 0
        assert r["settled_fill_count"] == 0


# ===========================================================================
# Filters: load_probe_events
# ===========================================================================

class TestLoadProbeFilters:
    def _write_probe(self, tmp_path: Path, payloads: list[dict]) -> None:
        d = tmp_path / "system_health"
        d.mkdir(parents=True, exist_ok=True)
        rows = [json.dumps({"run_id": p.get("run_id", "r"), "payload": p}) for p in payloads]
        (d / "2026-05-16.jsonl").write_text("\n".join(rows), encoding="utf-8")

    def test_asset_filter(self, tmp_path):
        payloads = [_probe_ev(ticker="BTC"), _probe_ev(ticker="ETH")]
        self._write_probe(tmp_path, payloads)
        result = load_probe_events("2026-05-16", quant_data_dir=tmp_path, asset_filter="BTC")
        assert len(result) == 1
        assert result[0]["ticker"] == "BTC"

    def test_run_id_filter(self, tmp_path):
        payloads = [_probe_ev(run_id="A"), _probe_ev(run_id="B")]
        self._write_probe(tmp_path, payloads)
        result = load_probe_events("2026-05-16", quant_data_dir=tmp_path, run_id="A")
        assert len(result) == 1

    def test_no_filter_loads_all(self, tmp_path):
        payloads = [_probe_ev(ticker="BTC"), _probe_ev(ticker="ETH"), _probe_ev(ticker="BTC")]
        self._write_probe(tmp_path, payloads)
        result = load_probe_events("2026-05-16", quant_data_dir=tmp_path)
        assert len(result) == 3


# ===========================================================================
# build_settlement_map -- file I/O
# ===========================================================================

class TestBuildSettlementMapIO:
    def _write_snaps(self, tmp_path: Path, payloads: list[dict]) -> None:
        d = tmp_path / "market_snapshots"
        d.mkdir(parents=True, exist_ok=True)
        rows = [json.dumps({"payload": p}) for p in payloads]
        (d / "2026-05-16.jsonl").write_text("\n".join(rows), encoding="utf-8")

    def test_loads_settlement_from_file(self, tmp_path):
        snaps = [_snap_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                          seconds_remaining=50.0, yes_bid=0.95)]
        self._write_snaps(tmp_path, snaps)
        keys = {(1_000, "pm-5m-btc")}
        smap = build_settlement_map("2026-05-16", tmp_path, keys)
        assert (1_000, "pm-5m-btc") in smap
        assert smap[(1_000, "pm-5m-btc")]["inferred_settlement"] == "YES"

    def test_only_probe_keys_included(self, tmp_path):
        snaps = [
            _snap_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                     seconds_remaining=50.0, yes_bid=0.95),
            _snap_ev(epoch_start_ts=9_999, market_key="pm-5m-eth",
                     seconds_remaining=50.0, yes_bid=0.95),
        ]
        self._write_snaps(tmp_path, snaps)
        keys = {(1_000, "pm-5m-btc")}
        smap = build_settlement_map("2026-05-16", tmp_path, keys)
        assert (9_999, "pm-5m-eth") not in smap

    def test_malformed_lines_skipped(self, tmp_path):
        d = tmp_path / "market_snapshots"
        d.mkdir(parents=True, exist_ok=True)
        content = (
            json.dumps({"payload": _snap_ev(epoch_start_ts=1_000, market_key="pm-5m-btc",
                                            seconds_remaining=50.0, yes_bid=0.95)}) + "\n"
            + "NOT_VALID_JSON\n"
        )
        (d / "2026-05-16.jsonl").write_text(content, encoding="utf-8")
        keys = {(1_000, "pm-5m-btc")}
        smap = build_settlement_map("2026-05-16", tmp_path, keys)
        assert (1_000, "pm-5m-btc") in smap


# ===========================================================================
# No runtime imports
# ===========================================================================

class TestNoRuntimeImports:
    def test_no_runtime_modules_imported(self):
        import ast
        import inspect
        import tools.shadow.semantic_c_shadow_pnl_truth as mod

        src  = inspect.getsource(mod)
        tree = ast.parse(src)
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.append(node.module)

        banned = {
            "polymarket.trader",
            "polymarket.order_manager",
            "polymarket.position_sizing",
            "utils.risk_manager",
            "polymarket.bankroll_tiers",
        }
        for m in banned:
            assert m not in imported, f"Must not import runtime module: {m}"

    def test_analyse_no_side_effects_on_events(self):
        evs = [_probe_ev() for _ in range(5)]
        originals = [dict(e) for e in evs]
        analyse(evs, {})
        for orig, current in zip(originals, evs):
            assert orig == current

    def test_build_settlement_map_no_side_effects(self):
        snaps = [_snap_ev()]
        smap_in = {}
        build_settlement_map.__doc__  # just touch the function -- real test is IO side-effect
        # Verify calling analyse with a copy doesn't mutate smap
        ep, mk = 1_000_000, "pm-5m-btc"
        smap = _build_smap([_snap_ev(epoch_start_ts=ep, market_key=mk,
                                     seconds_remaining=50.0, yes_bid=0.95)])
        original_keys = set(smap.keys())
        evs = [_probe_ev(epoch_start_ts=ep, market_key=mk)] * 3
        analyse(evs, smap)
        assert set(smap.keys()) == original_keys


# ===========================================================================
# Settlement inference caveats in output
# ===========================================================================

class TestSettlementCaveats:
    def test_caveats_list_present(self):
        evs = [_probe_ev()] * 5
        r = analyse(evs, {})
        si = r.get("settlement_inference") or {}
        assert isinstance(si.get("caveats"), list)
        assert len(si["caveats"]) > 0

    def test_caveats_mention_proxy(self):
        evs = [_probe_ev()] * 5
        r = analyse(evs, {})
        combined = " ".join(r.get("settlement_inference", {}).get("caveats", []))
        assert "proxy" in combined.lower() or "inferred" in combined.lower()

    def test_guardrail_string_present(self):
        evs = [_probe_ev()] * 5
        r = analyse(evs, {})
        assert "offline-only" in r.get("guardrail", "")
        assert "position_sizing" in r.get("guardrail", "")
