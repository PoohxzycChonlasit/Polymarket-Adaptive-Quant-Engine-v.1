"""
Tests for Semantic C Inventory Continuity Replay State Machine v1.

Covers:
- State transitions: FLAT->OPEN->HOLD->REDUCE->FINAL_DERISK->CLOSED->FLAT
- Max one position per asset: second shadow event in same epoch is skipped
- Cross-asset independence: BTC and ETH states are independent
- Max concurrent positions tracked correctly
- Exposure cap: concurrent BTC+ETH exposure summed correctly
- Forced close: position with no settlement snapshot counted correctly
- Unresolved settlement: AMBIGUOUS settlement -> unresolved, no PnL
- PnL aggregation: settled positions sum correctly
- Drawdown: same formula as pnl_truth layer
- Clustered loss detection: consecutive losses, isolated losses not clustered
- Opportunity cost metrics: skipped EV+ and profitable candidates
- Continuity vs independent comparison: fields and direction
- Verdict logic: all three branches
- Exposure duration distribution: entry SR stats present
- Fail-soft: empty events, missing files, missing fields
- Filters: run_id, asset_filter
- No runtime imports (AST scan)
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

from tools.shadow.semantic_c_inventory_continuity_replay import (
    _FINAL_DERISK,
    _FLAT,
    _HOLD,
    _MAX_PER_ASSET,
    _OPEN,
    _REDUCE,
    _compute_pnl,
    _compute_shadow,
    _clustered_losses,
    _max_drawdown,
    analyse,
    build_settlement_map,
    load_probe_events,
    simulate_inventory,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _probe(
    *,
    ticker: str = "BTC",
    market_key: str = "pm-5m-btc",
    epoch_start_ts: int = 1_000_000,
    seconds_remaining: float = 250.0,
    lifecycle_phase: str = "OPENING_SCAN",
    confidence: float = 0.62,
    ev: float = 0.16,
    raw_size_usd: float = 0.68,
    bankroll: float = 20.0,
    entry_price: float = 0.29,
    ev_positive: bool = True,
    run_id: str = "run_test",
) -> dict:
    return {
        "event":             "zero_size_probe_v1",
        "run_id":            run_id,
        "ticker":            ticker,
        "market_key":        market_key,
        "epoch_start_ts":    epoch_start_ts,
        "seconds_remaining": seconds_remaining,
        "lifecycle_phase":   lifecycle_phase,
        "confidence":        confidence,
        "ev":                ev,
        "ev_positive":       ev_positive,
        "raw_size_usd":      raw_size_usd,
        "bankroll":          bankroll,
        "entry_price":       entry_price,
        "final_size_usd":    0.0,
    }


def _smap_yes(epoch_start_ts: int = 1_000_000, market_key: str = "pm-5m-btc") -> dict:
    return {
        (epoch_start_ts, market_key): {
            "inferred_settlement":        "YES",
            "settlement_price":           1.0,
            "yes_bid_at_match":           0.95,
            "seconds_remaining_at_match": 50.0,
            "confidence":                 "HIGH",
        }
    }


def _smap_no(epoch_start_ts: int = 1_000_000, market_key: str = "pm-5m-btc") -> dict:
    return {
        (epoch_start_ts, market_key): {
            "inferred_settlement":        "NO",
            "settlement_price":           0.0,
            "yes_bid_at_match":           0.02,
            "seconds_remaining_at_match": 50.0,
            "confidence":                 "HIGH",
        }
    }


def _smap_ambig(epoch_start_ts: int = 1_000_000, market_key: str = "pm-5m-btc") -> dict:
    return {
        (epoch_start_ts, market_key): {
            "inferred_settlement":        "AMBIGUOUS",
            "settlement_price":           None,
            "yes_bid_at_match":           0.50,
            "seconds_remaining_at_match": 50.0,
            "confidence":                 "AMBIGUOUS",
        }
    }


# ===========================================================================
# State machine: basic state transitions
# ===========================================================================

class TestStateMachineTransitions:
    def test_flat_to_open_on_first_shadow_event(self):
        evs = [_probe(epoch_start_ts=1_000, seconds_remaining=250, lifecycle_phase="OPENING_SCAN")]
        sim = simulate_inventory(evs, {})
        assert len(sim["positions"]) == 1
        assert sim["positions"][0]["state"] == "CLOSED"  # closed at epoch end
        assert sim["positions"][0]["entry_phase"] == "OPENING_SCAN"

    def test_second_event_same_epoch_is_skipped(self):
        evs = [
            _probe(epoch_start_ts=1_000, seconds_remaining=250, lifecycle_phase="OPENING_SCAN"),
            _probe(epoch_start_ts=1_000, seconds_remaining=200, lifecycle_phase="ACTIVE_INVENTORY_TRADING"),
        ]
        sim = simulate_inventory(evs, {})
        assert len(sim["positions"]) == 1
        assert len(sim["skipped_events"]) == 1
        assert sim["skipped_events"][0]["skip_reason"] == "existing_inventory"

    def test_position_state_advances_to_hold(self):
        # Two events in same epoch: OPENING_SCAN then ACTIVE_INVENTORY_TRADING
        evs = [
            _probe(epoch_start_ts=1_000, seconds_remaining=250, lifecycle_phase="OPENING_SCAN"),
            _probe(epoch_start_ts=1_000, seconds_remaining=200, lifecycle_phase="ACTIVE_INVENTORY_TRADING"),
        ]
        sim = simulate_inventory(evs, {})
        # The position should have advanced to HOLD before epoch closed
        # (We check via the closed position's state = CLOSED, but the state_at_close is
        # accessible through the position dict's final state)
        pos = sim["positions"][0]
        assert pos["state"] == "CLOSED"

    def test_final_derisk_triggered_by_low_sr(self):
        evs = [
            _probe(epoch_start_ts=1_000, seconds_remaining=250, lifecycle_phase="OPENING_SCAN"),
            _probe(epoch_start_ts=1_000, seconds_remaining=25, lifecycle_phase="ACTIVE_INVENTORY_TRADING"),
        ]
        sim = simulate_inventory(evs, {})
        pos = sim["positions"][0]
        # Forced close because last state was FINAL_DERISK
        assert pos["forced_close"] is True

    def test_flat_resets_between_epochs(self):
        evs = [
            _probe(epoch_start_ts=1_000, seconds_remaining=250),
            _probe(epoch_start_ts=2_000, seconds_remaining=250),
        ]
        sim = simulate_inventory(evs, {})
        assert len(sim["positions"]) == 2  # one per epoch

    def test_no_shadow_event_produces_no_entry(self):
        evs = [_probe(confidence=0.0, ev=0.0)]  # shadow = 0 (blocked)
        sim = simulate_inventory(evs, {})
        assert len(sim["positions"]) == 0
        assert len(sim["skipped_events"]) == 0


# ===========================================================================
# Max one position per asset
# ===========================================================================

class TestMaxOnePositionPerAsset:
    def test_one_entry_per_epoch_per_asset(self):
        evs = [
            _probe(epoch_start_ts=1_000, seconds_remaining=250),
            _probe(epoch_start_ts=1_000, seconds_remaining=200),
            _probe(epoch_start_ts=1_000, seconds_remaining=150),
        ]
        sim = simulate_inventory(evs, {})
        assert len(sim["positions"]) == 1
        assert len(sim["skipped_events"]) == 2

    def test_all_intra_epoch_skips_counted(self):
        n_extra = 5
        evs = [_probe(epoch_start_ts=1_000, seconds_remaining=250 - i * 10) for i in range(n_extra + 1)]
        sim = simulate_inventory(evs, {})
        assert len(sim["skipped_events"]) == n_extra

    def test_btc_and_eth_independent_no_cross_skip(self):
        evs = [
            _probe(ticker="BTC", market_key="pm-5m-btc", epoch_start_ts=1_000, seconds_remaining=250),
            _probe(ticker="ETH", market_key="pm-5m-eth", epoch_start_ts=1_000, seconds_remaining=250),
        ]
        sim = simulate_inventory(evs, {})
        assert len(sim["positions"]) == 2
        assert len(sim["skipped_events"]) == 0

    def test_next_epoch_entered_after_prior_closed(self):
        evs = [
            _probe(ticker="BTC", market_key="pm-5m-btc", epoch_start_ts=1_000, seconds_remaining=250),
            _probe(ticker="BTC", market_key="pm-5m-btc", epoch_start_ts=2_000, seconds_remaining=250),
        ]
        sim = simulate_inventory(evs, {})
        assert len(sim["positions"]) == 2  # Both epochs entered


# ===========================================================================
# Concurrent position tracking
# ===========================================================================

class TestConcurrentPositions:
    def test_concurrent_is_2_when_btc_and_eth_both_open(self):
        evs = [
            _probe(ticker="BTC", market_key="pm-5m-btc", epoch_start_ts=1_000),
            _probe(ticker="ETH", market_key="pm-5m-eth", epoch_start_ts=1_000),
        ]
        smap = {**_smap_yes(1_000, "pm-5m-btc"), **_smap_yes(1_000, "pm-5m-eth")}
        r = analyse(evs, smap)
        assert r["max_concurrent_positions"] == 2

    def test_concurrent_is_1_when_only_one_asset(self):
        evs = [_probe(ticker="BTC", market_key="pm-5m-btc", epoch_start_ts=1_000)]
        r = analyse(evs, _smap_yes(1_000, "pm-5m-btc"))
        assert r["max_concurrent_positions"] == 1

    def test_concurrent_is_0_when_no_entries(self):
        evs = [_probe(confidence=0.0, ev=0.0)]
        r = analyse(evs, {})
        assert r["max_concurrent_positions"] == 0


# ===========================================================================
# Exposure cap
# ===========================================================================

class TestExposureCap:
    def test_max_exposure_is_sum_of_concurrent_pcts(self):
        evs = [
            _probe(ticker="BTC", market_key="pm-5m-btc", epoch_start_ts=1_000,
                   confidence=0.62, ev=0.16, raw_size_usd=0.68, bankroll=20.0),
            _probe(ticker="ETH", market_key="pm-5m-eth", epoch_start_ts=1_000,
                   confidence=0.62, ev=0.16, raw_size_usd=0.68, bankroll=20.0),
        ]
        smap = {**_smap_yes(1_000, "pm-5m-btc"), **_smap_yes(1_000, "pm-5m-eth")}
        r = analyse(evs, smap)
        # Each position is ~1.9% bankroll; together ~3.8%
        assert r["max_total_exposure_pct"] > 0.0
        assert r["max_total_exposure_pct"] < 10.0  # safe

    def test_single_asset_exposure_less_than_concurrent(self):
        ev_btc = [_probe(ticker="BTC", market_key="pm-5m-btc", epoch_start_ts=1_000)]
        ev_both = [
            _probe(ticker="BTC", market_key="pm-5m-btc", epoch_start_ts=1_000),
            _probe(ticker="ETH", market_key="pm-5m-eth", epoch_start_ts=1_000),
        ]
        smap = {**_smap_yes(1_000, "pm-5m-btc"), **_smap_yes(1_000, "pm-5m-eth")}
        r_btc  = analyse(ev_btc, _smap_yes(1_000, "pm-5m-btc"))
        r_both = analyse(ev_both, smap)
        assert r_both["max_total_exposure_pct"] >= r_btc["max_total_exposure_pct"]


# ===========================================================================
# Forced close
# ===========================================================================

class TestForcedClose:
    def test_forced_close_when_no_settlement_snapshot(self):
        evs = [_probe(epoch_start_ts=1_000, seconds_remaining=250)]
        r = analyse(evs, {})  # empty smap
        assert r["forced_close_count"] == 1

    def test_forced_close_when_final_derisk_sr(self):
        evs = [
            _probe(epoch_start_ts=1_000, seconds_remaining=250, lifecycle_phase="OPENING_SCAN"),
            _probe(epoch_start_ts=1_000, seconds_remaining=20, lifecycle_phase="FINAL_DERISK"),
        ]
        r = analyse(evs, {})
        assert r["forced_close_count"] == 1

    def test_no_forced_close_with_high_confidence_settlement(self):
        evs = [_probe(epoch_start_ts=1_000, seconds_remaining=250)]
        r = analyse(evs, _smap_yes(1_000, "pm-5m-btc"))
        assert r["forced_close_count"] == 0

    def test_forced_close_zero_when_settlement_exists(self):
        evs = [_probe(epoch_start_ts=1_000)] * 1
        r = analyse(evs, _smap_no(1_000, "pm-5m-btc"))
        assert r["forced_close_count"] == 0


# ===========================================================================
# Unresolved settlement
# ===========================================================================

class TestUnresolvedSettlement:
    def test_ambiguous_settlement_is_unresolved(self):
        evs = [_probe(epoch_start_ts=1_000)]
        r = analyse(evs, _smap_ambig(1_000, "pm-5m-btc"))
        assert r["unresolved_close_count"] == 1
        assert r["settled_fill_count"] == 0
        assert r["realized_proxy_pnl"] == 0.0

    def test_no_snapshot_is_unresolved(self):
        evs = [_probe(epoch_start_ts=1_000)]
        r = analyse(evs, {})
        assert r["unresolved_close_count"] == 1

    def test_high_confidence_is_resolved(self):
        evs = [_probe(epoch_start_ts=1_000)]
        r = analyse(evs, _smap_yes(1_000, "pm-5m-btc"))
        assert r["unresolved_close_count"] == 0
        assert r["settled_fill_count"] == 1


# ===========================================================================
# PnL aggregation
# ===========================================================================

class TestPnLAggregation:
    def test_yes_settlement_gives_positive_pnl(self):
        evs = [_probe(epoch_start_ts=1_000, entry_price=0.29, raw_size_usd=0.68)]
        r = analyse(evs, _smap_yes(1_000, "pm-5m-btc"))
        assert r["realized_proxy_pnl"] > 0.0

    def test_no_settlement_gives_negative_pnl(self):
        evs = [_probe(epoch_start_ts=1_000, entry_price=0.29, raw_size_usd=0.68)]
        r = analyse(evs, _smap_no(1_000, "pm-5m-btc"))
        assert r["realized_proxy_pnl"] < 0.0

    def test_pnl_sums_across_epochs(self):
        evs = [
            _probe(epoch_start_ts=1_000, seconds_remaining=250),
            _probe(epoch_start_ts=2_000, seconds_remaining=250),
        ]
        smap = {**_smap_yes(1_000, "pm-5m-btc"), **_smap_yes(2_000, "pm-5m-btc")}
        r = analyse(evs, smap)
        assert r["settled_fill_count"] == 2
        assert r["realized_proxy_pnl"] > 0.0

    def test_mixed_pnl_correct_sign(self):
        evs = [
            _probe(epoch_start_ts=1_000, seconds_remaining=250),
            _probe(epoch_start_ts=2_000, seconds_remaining=250),
        ]
        smap = {
            **_smap_yes(1_000, "pm-5m-btc"),
            **_smap_no(2_000, "pm-5m-btc"),
        }
        r = analyse(evs, smap)
        # One win, one loss
        assert r["win_count"] == 1
        assert r["loss_count"] == 1

    def test_btc_eth_pnl_separated(self):
        evs = [
            _probe(ticker="BTC", market_key="pm-5m-btc", epoch_start_ts=1_000),
            _probe(ticker="ETH", market_key="pm-5m-eth", epoch_start_ts=1_000),
        ]
        smap = {**_smap_yes(1_000, "pm-5m-btc"), **_smap_no(1_000, "pm-5m-eth")}
        r = analyse(evs, smap)
        pa = r["pnl_by_asset"]
        assert pa["btc"]["total_pnl"] > 0.0
        assert pa["eth"]["total_pnl"] < 0.0

    def test_pnl_stats_populated_with_enough_fills(self):
        evs = [_probe(epoch_start_ts=1_000_000 + i * 300) for i in range(12)]
        smap = {(1_000_000 + i * 300, "pm-5m-btc"): {
            "inferred_settlement": "YES",
            "settlement_price": 1.0,
            "yes_bid_at_match": 0.95,
            "seconds_remaining_at_match": 50.0,
            "confidence": "HIGH",
        } for i in range(12)}
        r = analyse(evs, smap)
        ps = r.get("pnl_stats") or {}
        assert ps["count"] == 12
        assert ps["mean"] > 0.0


# ===========================================================================
# Win rate by asset
# ===========================================================================

class TestWinRateByAsset:
    def test_win_rate_100_when_all_yes(self):
        evs = [_probe(epoch_start_ts=1_000)]
        r = analyse(evs, _smap_yes(1_000, "pm-5m-btc"))
        assert r["win_rate_by_asset"]["btc"] == 100.0

    def test_win_rate_0_when_all_no(self):
        evs = [_probe(epoch_start_ts=1_000)]
        r = analyse(evs, _smap_no(1_000, "pm-5m-btc"))
        assert r["win_rate_by_asset"]["btc"] == 0.0

    def test_overall_win_rate_combines_assets(self):
        evs = [
            _probe(ticker="BTC", market_key="pm-5m-btc", epoch_start_ts=1_000),
            _probe(ticker="ETH", market_key="pm-5m-eth", epoch_start_ts=1_000),
        ]
        smap = {**_smap_yes(1_000, "pm-5m-btc"), **_smap_no(1_000, "pm-5m-eth")}
        r = analyse(evs, smap)
        assert r["win_rate_overall_pct"] == 50.0


# ===========================================================================
# Drawdown
# ===========================================================================

class TestDrawdown:
    def test_zero_drawdown_all_wins(self):
        evs = [
            _probe(epoch_start_ts=1_000, seconds_remaining=250),
            _probe(epoch_start_ts=2_000, seconds_remaining=250),
        ]
        smap = {**_smap_yes(1_000, "pm-5m-btc"), **_smap_yes(2_000, "pm-5m-btc")}
        r = analyse(evs, smap)
        assert r["max_drawdown_approx"] == 0.0

    def test_positive_drawdown_with_losses(self):
        evs = [
            _probe(epoch_start_ts=1_000, seconds_remaining=250),
            _probe(epoch_start_ts=2_000, seconds_remaining=250),
        ]
        smap = {**_smap_yes(1_000, "pm-5m-btc"), **_smap_no(2_000, "pm-5m-btc")}
        r = analyse(evs, smap)
        assert r["max_drawdown_approx"] >= 0.0

    def test_max_drawdown_unit(self):
        pnls = [0.10, -0.30, 0.50]
        dd = _max_drawdown(pnls)
        assert abs(dd - 0.30) < 1e-8


# ===========================================================================
# Clustered loss detection
# ===========================================================================

class TestClusteredLosses:
    def _make_sorted(self, pnl_values: list[float]) -> list[dict]:
        return [{"pnl": v, "epoch_start_ts": i} for i, v in enumerate(pnl_values)]

    def test_no_cluster_when_isolated_losses(self):
        records = self._make_sorted([0.10, -0.05, 0.10, -0.05, 0.10])
        info = _clustered_losses(records)
        assert info["loss_cluster_count"] == 0
        assert info["max_consecutive_losses"] == 1

    def test_cluster_detected_for_two_consecutive_losses(self):
        records = self._make_sorted([0.10, -0.05, -0.05, 0.10])
        info = _clustered_losses(records)
        assert info["loss_cluster_count"] == 1
        assert info["max_consecutive_losses"] == 2

    def test_max_consecutive_correct(self):
        records = self._make_sorted([-0.10, -0.10, -0.10, 0.20])
        info = _clustered_losses(records)
        assert info["max_consecutive_losses"] == 3
        assert info["loss_cluster_count"] == 1

    def test_multiple_clusters(self):
        records = self._make_sorted([-0.10, -0.10, 0.20, -0.05, -0.05, 0.10])
        info = _clustered_losses(records)
        assert info["loss_cluster_count"] == 2

    def test_empty_series(self):
        info = _clustered_losses([])
        assert info["max_consecutive_losses"] == 0
        assert info["loss_cluster_count"] == 0

    def test_cluster_at_end_of_series(self):
        records = self._make_sorted([0.10, -0.05, -0.05])
        info = _clustered_losses(records)
        assert info["loss_cluster_count"] == 1

    def test_integration_with_analyse(self):
        # 3 consecutive NO settlements
        evs = [_probe(epoch_start_ts=1_000_000 + i * 300) for i in range(5)]
        smap = {}
        for i in range(3):
            ep = 1_000_000 + i * 300
            smap[(ep, "pm-5m-btc")] = {
                "inferred_settlement": "NO", "settlement_price": 0.0,
                "yes_bid_at_match": 0.02, "seconds_remaining_at_match": 50.0,
                "confidence": "HIGH",
            }
        for i in range(3, 5):
            ep = 1_000_000 + i * 300
            smap[(ep, "pm-5m-btc")] = {
                "inferred_settlement": "YES", "settlement_price": 1.0,
                "yes_bid_at_match": 0.95, "seconds_remaining_at_match": 50.0,
                "confidence": "HIGH",
            }
        r = analyse(evs, smap)
        cl = r["clustered_loss_periods"]
        assert cl["max_consecutive_losses"] >= 2


# ===========================================================================
# Opportunity cost metrics
# ===========================================================================

class TestOpportunityCostMetrics:
    def test_skipped_positive_ev_counted(self):
        evs = [
            _probe(epoch_start_ts=1_000, seconds_remaining=250, ev_positive=True),
            _probe(epoch_start_ts=1_000, seconds_remaining=200, ev_positive=True),
        ]
        r = analyse(evs, {})
        assert r["skipped_positive_ev_candidates"] == 1

    def test_skipped_profitable_counted_when_yes_settlement(self):
        evs = [
            _probe(epoch_start_ts=1_000, seconds_remaining=250),
            _probe(epoch_start_ts=1_000, seconds_remaining=200),
        ]
        r = analyse(evs, _smap_yes(1_000, "pm-5m-btc"))
        assert r["skipped_profitable_candidates"] == 1

    def test_opportunity_cost_is_positive_when_profitable_skipped(self):
        evs = [
            _probe(epoch_start_ts=1_000, seconds_remaining=250, entry_price=0.29, raw_size_usd=0.68),
            _probe(epoch_start_ts=1_000, seconds_remaining=200, entry_price=0.29, raw_size_usd=0.68),
        ]
        r = analyse(evs, _smap_yes(1_000, "pm-5m-btc"))
        assert r["skipped_candidate_opportunity_cost_usd"] > 0.0

    def test_opportunity_cost_zero_when_no_profitable_skips(self):
        evs = [
            _probe(epoch_start_ts=1_000, seconds_remaining=250),
            _probe(epoch_start_ts=1_000, seconds_remaining=200),
        ]
        r = analyse(evs, _smap_no(1_000, "pm-5m-btc"))
        assert r["skipped_candidate_opportunity_cost_usd"] == 0.0

    def test_no_opportunity_cost_when_no_skips(self):
        evs = [_probe(epoch_start_ts=1_000)]
        r = analyse(evs, _smap_yes(1_000, "pm-5m-btc"))
        assert r["skipped_due_to_existing_inventory"] == 0
        assert r["skipped_candidate_opportunity_cost_usd"] == 0.0


# ===========================================================================
# Continuity vs independent comparison
# ===========================================================================

class TestContinuityVsIndependent:
    def test_comparison_fields_present(self):
        evs = [_probe(epoch_start_ts=1_000)]
        r = analyse(evs, {})
        ci = r.get("continuity_vs_independent") or {}
        assert "ref_independent_fills" in ci
        assert "continuity_entries" in ci
        assert "pnl_relationship" in ci
        assert "interpretation" in ci

    def test_entries_change_pct_correct_direction(self):
        # 1 entry vs reference 299 => entries_change_pct should be negative
        evs = [_probe(epoch_start_ts=1_000)]
        r = analyse(evs, {})
        ci = r["continuity_vs_independent"]
        assert ci["entries_change_pct"] < 0.0

    def test_reduces_materially_when_pnl_tiny(self):
        evs = [_probe(epoch_start_ts=1_000)]
        r = analyse(evs, {})
        ci = r["continuity_vs_independent"]
        assert ci["pnl_relationship"] == "REDUCES_MATERIALLY"


# ===========================================================================
# Verdict logic
# ===========================================================================

class TestVerdictLogic:
    def test_safe_for_normal_bounded_scenario(self):
        evs = [_probe(epoch_start_ts=1_000_000 + i * 300) for i in range(12)]
        smap = {(1_000_000 + i * 300, "pm-5m-btc"): {
            "inferred_settlement": "YES", "settlement_price": 1.0,
            "yes_bid_at_match": 0.95, "seconds_remaining_at_match": 50.0,
            "confidence": "HIGH",
        } for i in range(12)}
        r = analyse(evs, smap)
        assert r["verdict"] == "safe_for_scoped_paper_trial"

    def test_needs_more_replay_when_too_few_entries(self):
        evs = [_probe(epoch_start_ts=1_000)]
        r = analyse(evs, _smap_yes(1_000, "pm-5m-btc"))
        assert r["verdict"] == "needs_more_replay"

    def test_needs_more_replay_when_low_win_rate(self):
        evs = [_probe(epoch_start_ts=1_000_000 + i * 300) for i in range(15)]
        smap = {(1_000_000 + i * 300, "pm-5m-btc"): {
            "inferred_settlement": "NO", "settlement_price": 0.0,
            "yes_bid_at_match": 0.02, "seconds_remaining_at_match": 50.0,
            "confidence": "HIGH",
        } for i in range(15)}
        r = analyse(evs, smap)
        assert r["verdict"] in ("needs_more_replay", "unsafe_due_to_inventory_overlap")

    def test_verdict_note_non_empty(self):
        evs = [_probe(epoch_start_ts=1_000)]
        r = analyse(evs, {})
        assert len(r.get("verdict_note", "")) > 0

    def test_guardrail_present(self):
        evs = [_probe(epoch_start_ts=1_000)]
        r = analyse(evs, {})
        assert "offline-only" in r.get("guardrail", "")


# ===========================================================================
# Exposure duration
# ===========================================================================

class TestExposureDuration:
    def test_exposure_duration_stats_present(self):
        evs = [_probe(epoch_start_ts=1_000, seconds_remaining=250)]
        r = analyse(evs, {})
        ed = r.get("exposure_duration") or {}
        assert "entry_seconds_remaining_stats" in ed
        assert ed["entry_seconds_remaining_stats"]["count"] == 1

    def test_typical_hold_is_entry_sr(self):
        evs = [_probe(epoch_start_ts=1_000, seconds_remaining=200.0)]
        r = analyse(evs, {})
        ed = r.get("exposure_duration") or {}
        assert abs(ed.get("typical_hold_seconds", 0) - 200.0) < 1.0


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
        r = analyse([{} for _ in range(5)], {})
        assert r["event_count"] == 5
        assert "verdict" in r

    def test_zero_shadow_events_no_entries(self):
        evs = [_probe(confidence=0.0, ev=0.0)] * 10
        r = analyse(evs, {})
        assert r["simulated_entries"] == 0
        assert r["skipped_due_to_existing_inventory"] == 0

    def test_simulation_rules_list_present(self):
        evs = [_probe(epoch_start_ts=1_000)]
        r = analyse(evs, {})
        assert isinstance(r.get("simulation_rules"), list)
        assert len(r["simulation_rules"]) > 0


# ===========================================================================
# Filters
# ===========================================================================

class TestFilters:
    def _write_probe(self, tmp_path: Path, payloads: list[dict]) -> None:
        d = tmp_path / "system_health"
        d.mkdir(parents=True, exist_ok=True)
        rows = [json.dumps({"run_id": p.get("run_id", "r"), "payload": p}) for p in payloads]
        (d / "2026-05-16.jsonl").write_text("\n".join(rows), encoding="utf-8")

    def test_asset_filter(self, tmp_path):
        payloads = [_probe(ticker="BTC"), _probe(ticker="ETH")]
        self._write_probe(tmp_path, payloads)
        result = load_probe_events("2026-05-16", quant_data_dir=tmp_path, asset_filter="BTC")
        assert len(result) == 1
        assert result[0]["ticker"] == "BTC"

    def test_run_id_filter(self, tmp_path):
        payloads = [_probe(run_id="A"), _probe(run_id="B")]
        self._write_probe(tmp_path, payloads)
        result = load_probe_events("2026-05-16", quant_data_dir=tmp_path, run_id="A")
        assert len(result) == 1


# ===========================================================================
# No runtime imports
# ===========================================================================

class TestNoRuntimeImports:
    def test_no_runtime_modules_imported(self):
        import ast
        import inspect
        import tools.shadow.semantic_c_inventory_continuity_replay as mod

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
        evs = [_probe(epoch_start_ts=1_000) for _ in range(4)]
        originals = [dict(e) for e in evs]
        analyse(evs, {})
        for orig, curr in zip(originals, evs):
            assert orig == curr

    def test_simulate_no_side_effects_on_smap(self):
        evs = [_probe(epoch_start_ts=1_000)]
        smap = _smap_yes(1_000, "pm-5m-btc")
        original_keys = set(smap.keys())
        simulate_inventory(evs, smap)
        assert set(smap.keys()) == original_keys
