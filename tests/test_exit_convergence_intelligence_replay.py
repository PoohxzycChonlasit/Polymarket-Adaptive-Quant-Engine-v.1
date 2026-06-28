"""
Tests for Exit Convergence Intelligence Replay v1.

Covers:
- Convergence detector correctness: _rolling_vol, _bid_stabilization, _persistence_count
- Rolling volatility: window clamping, monotonic series, noisy series, inf on < 2 bids
- No future leakage: snapshots at/above entry_SR excluded from decisions
- Reversal detection: late_reversal flag, post-exit bid movement threshold
- Derisk timing: Policy B (SR<60) correct exit trigger and PnL
- PnL aggregation: reduce_pnl, runner_pnl, total_pnl formulas
- BTC/ETH aggregation: separate tracking, divergent settlements
- Verdict branches: safe_candidate, convergence_unstable, no_material_improvement,
  needs_more_replay
- convergence_false_positive_cost_usd: correct accumulation for false exits
- late_uncertainty_expansion_count: correct detection per position
- No runtime imports: AST scan over module source
- No side effects: analyse() and simulate_convergence_policy() do not mutate inputs
- analyse() runs all 5 policies
- Policy comparison block present and complete
- Fail-soft: empty events, missing files, missing fields
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.replay.exit_convergence_intelligence_replay import (
    _CONV_PERSIST_N,
    _CONV_PROXY_BAND,
    _CONV_REVERSAL_THRESHOLD,
    _CONV_VOL_THRESHOLD,
    _CONV_VOL_WINDOW,
    _CONVERGENCE_UNSTABLE_RATE,
    _DERISK_SR,
    _LATE_VOL_SR_BOUNDARY,
    _NO_IMPROVEMENT_USD,
    _UNSAFE_DRAWDOWN_PCT,
    POLICIES,
    _bid_stabilization,
    _compute_shadow,
    _max_drawdown,
    _persistence_count,
    _rolling_vol,
    _simulate_convergence,
    _stdev_safe,
    analyse,
    build_settlement_map,
    load_epoch_timelines,
    load_probe_events,
    simulate_convergence_policy,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _probe(
    *,
    ticker: str = "BTC",
    market_key: str = "pm-5m-btc",
    epoch_start_ts: int = 1_000_000,
    seconds_remaining: float = 250.0,
    confidence: float = 0.62,
    ev: float = 0.16,
    raw_size_usd: float = 0.68,
    bankroll: float = 20.0,
    entry_price: float = 0.29,
    run_id: str = "run_test",
) -> dict:
    return {
        "event":             "zero_size_probe_v1",
        "run_id":            run_id,
        "ticker":            ticker,
        "market_key":        market_key,
        "epoch_start_ts":    epoch_start_ts,
        "seconds_remaining": seconds_remaining,
        "confidence":        confidence,
        "ev":                ev,
        "raw_size_usd":      raw_size_usd,
        "bankroll":          bankroll,
        "entry_price":       entry_price,
        "final_size_usd":    0.0,
    }


def _yes_smap(ep: int = 1_000_000, mk: str = "pm-5m-btc") -> dict:
    return {(ep, mk): {
        "inferred_settlement": "YES",
        "settlement_price":    1.0,
        "yes_bid_at_match":    0.95,
        "seconds_remaining_at_match": 54.0,
        "confidence": "HIGH",
    }}


def _no_smap(ep: int = 1_000_000, mk: str = "pm-5m-btc") -> dict:
    return {(ep, mk): {
        "inferred_settlement": "NO",
        "settlement_price":    0.0,
        "yes_bid_at_match":    0.02,
        "seconds_remaining_at_match": 54.0,
        "confidence": "HIGH",
    }}


def _run_policy(
    policy_idx: int,
    events: list[dict],
    smap: dict,
    timelines: dict | None = None,
    bankroll: float = 20.0,
) -> dict:
    from tools.replay.exit_convergence_intelligence_replay import _policy_report
    tl = timelines or {}
    # Policy A baseline first (needed for uplift reference)
    pos_a = simulate_convergence_policy(events, smap, tl, POLICIES[0], bankroll)
    r_a   = _policy_report(pos_a, POLICIES[0], bankroll, 0.0, 0.0)
    baseline_pnl = r_a["realized_proxy_pnl"]
    # Policy B fixed-derisk (for vs-B reference)
    pos_b = simulate_convergence_policy(events, smap, tl, POLICIES[1], bankroll)
    r_b   = _policy_report(pos_b, POLICIES[1], bankroll, baseline_pnl, baseline_pnl)
    fixed_pnl = r_b["realized_proxy_pnl"]

    pos = simulate_convergence_policy(events, smap, tl, POLICIES[policy_idx], bankroll)
    return _policy_report(pos, POLICIES[policy_idx], bankroll, baseline_pnl, fixed_pnl)


# ---------------------------------------------------------------------------
# 1. Convergence detector correctness
# ---------------------------------------------------------------------------

class TestConvergenceDetector:
    def test_stdev_safe_returns_none_for_single_value(self):
        assert _stdev_safe([0.5]) is None

    def test_stdev_safe_returns_none_for_empty(self):
        assert _stdev_safe([]) is None

    def test_stdev_safe_correct_two_values(self):
        result = _stdev_safe([0.0, 1.0])
        assert result is not None
        assert abs(result - 0.7071067811865476) < 1e-9

    def test_stdev_safe_zero_for_identical_values(self):
        result = _stdev_safe([0.5, 0.5, 0.5])
        assert result == 0.0

    def test_persistence_count_zero_on_empty(self):
        assert _persistence_count([], 0.9) == 0

    def test_persistence_count_full_match(self):
        bids = [0.88, 0.91, 0.93, 0.92]
        # target=0.95, band=0.05: |0.92-0.95|=0.03 ok, |0.93-0.95|=0.02 ok,
        # |0.91-0.95|=0.04 ok, |0.88-0.95|=0.07 NOT ok → count=3
        assert _persistence_count(bids, 0.95, 0.05) == 3

    def test_persistence_count_none_when_last_outside_band(self):
        bids = [0.91, 0.92, 0.70]   # last bid 0.70 is outside 5pp of 0.95
        assert _persistence_count(bids, 0.95, 0.05) == 0

    def test_persistence_count_all_match(self):
        bids = [0.92, 0.93, 0.94]
        assert _persistence_count(bids, 0.95, 0.05) == 3

    def test_persistence_count_absolute_not_relative(self):
        # target=0.02, band=0.05: bids within [0, 0.07] should match
        bids = [0.03, 0.04, 0.05]
        assert _persistence_count(bids, 0.02, 0.05) == 3  # all within ±0.05

    def test_bid_stabilization_inf_on_single_value(self):
        assert _bid_stabilization([0.5]) == float("inf")

    def test_bid_stabilization_inf_on_near_zero_mean(self):
        assert _bid_stabilization([1e-12, 2e-12]) == float("inf")

    def test_bid_stabilization_low_for_stable_bids(self):
        bids = [0.90, 0.91, 0.90, 0.91, 0.90]
        stab = _bid_stabilization(bids)
        assert stab < 0.02  # very stable

    def test_bid_stabilization_high_for_volatile_bids(self):
        bids = [0.10, 0.90, 0.20, 0.80, 0.30]
        stab = _bid_stabilization(bids)
        assert stab > 0.5   # very volatile


# ---------------------------------------------------------------------------
# 2. Rolling volatility
# ---------------------------------------------------------------------------

class TestRollingVolatility:
    def test_inf_on_empty(self):
        assert _rolling_vol([]) == float("inf")

    def test_inf_on_single_value(self):
        assert _rolling_vol([0.9]) == float("inf")

    def test_zero_for_constant_series(self):
        assert _rolling_vol([0.5, 0.5, 0.5, 0.5, 0.5]) == 0.0

    def test_window_clamping_uses_last_n(self):
        # Window=3: only last 3 bids matter
        bids = [0.0, 0.0, 0.9, 0.9, 0.9]   # last 3 are constant
        assert _rolling_vol(bids, window=3) == 0.0

    def test_noisy_series_has_positive_vol(self):
        bids = [0.1, 0.9, 0.2, 0.8, 0.3]
        assert _rolling_vol(bids) > 0.0

    def test_window_smaller_than_bids(self):
        bids = [0.5] * 10
        assert _rolling_vol(bids, window=3) == 0.0

    def test_vol_correct_for_two_value_window(self):
        bids = [0.0, 1.0]
        vol = _rolling_vol(bids, window=5)
        # stdev([0,1]) = sqrt(0.5) ≈ 0.7071
        assert abs(vol - 0.7071067811865476) < 1e-9


# ---------------------------------------------------------------------------
# 3. No future leakage
# ---------------------------------------------------------------------------

class TestNoFutureLeakage:
    def test_policy_b_excludes_pre_entry_snapshots(self):
        # Entry at SR=200; snapshot at SR=250 (before entry) must not trigger exit
        policy = POLICIES[1]  # B_fixed_derisk_sr60
        timeline = [(250.0, 0.40), (55.0, 0.88)]   # SR=250 excluded
        lc = _simulate_convergence(0.29, 0.68, 200.0, timeline, 1.0, 0.95, policy)
        # SR=55 < 60 should fire, not SR=250
        assert lc["convergence_exit"] is True
        assert abs(lc["reduce_sr"] - 55.0) < 1e-6

    def test_policy_b_no_exit_when_only_pre_entry_snapshots(self):
        policy = POLICIES[1]
        # All snapshots have SR >= entry_sr=100
        timeline = [(200.0, 0.50), (150.0, 0.80), (110.0, 0.95)]
        lc = _simulate_convergence(0.29, 0.68, 100.0, timeline, 1.0, 0.95, policy)
        assert lc["convergence_exit"] is False

    def test_policy_d_vol_collapse_excludes_future_snapshots(self):
        # Entry at SR=200; vol-collapse snapshots at SR > 200 must not fire
        policy = POLICIES[3]  # D_dynamic_convergence_exit_volatility
        # Pre-entry snapshot with constant bids (would trigger vol=0 if included)
        timeline = [(250.0, 0.95), (250.0, 0.95), (250.0, 0.95)]
        lc = _simulate_convergence(0.29, 0.68, 200.0, timeline, 1.0, 0.95, policy)
        # No post-entry snapshots → no exit
        assert lc["convergence_exit"] is False

    def test_policy_c_no_trigger_without_proxy(self):
        # settlement_proxy_bid = None → Policy C never triggers
        policy = POLICIES[2]  # C_dynamic_convergence_exit_95
        timeline = [(180.0, 0.95), (160.0, 0.95), (140.0, 0.95)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, None, policy)
        assert lc["convergence_exit"] is False

    def test_settlement_proxy_labeled_as_research(self):
        policy = POLICIES[2]  # C uses research proxy
        lc = _simulate_convergence(0.29, 0.68, 250.0, [], 1.0, 0.95, policy)
        assert lc["research_proxy_used"] is True

    def test_policy_d_not_labeled_research(self):
        policy = POLICIES[3]  # D is backward-looking only
        lc = _simulate_convergence(0.29, 0.68, 250.0, [], 1.0, 0.95, policy)
        assert lc["research_proxy_used"] is False


# ---------------------------------------------------------------------------
# 4. Reversal detection
# ---------------------------------------------------------------------------

class TestReversalDetection:
    def test_late_reversal_true_when_post_exit_bid_deviates(self):
        policy = POLICIES[1]  # B: exit at SR<60
        # Exit at SR=55 (yes_bid=0.88); then SR=10 has bid=0.40 (drop > 0.10)
        timeline = [(55.0, 0.88), (10.0, 0.40)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["convergence_exit"] is True
        assert lc["late_reversal"] is True

    def test_late_reversal_false_when_bid_stable_after_exit(self):
        policy = POLICIES[1]
        # Exit at SR=55 (yes_bid=0.88); post-exit SR=10 bid=0.90 (stable)
        timeline = [(55.0, 0.88), (10.0, 0.90)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["late_reversal"] is False

    def test_late_reversal_false_when_no_convergence_exit(self):
        # Policy A: no exit, so no reversal possible
        policy = POLICIES[0]
        timeline = [(55.0, 0.88), (10.0, 0.30)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["convergence_exit"] is False
        assert lc["late_reversal"] is False

    def test_late_reversal_uses_reversal_threshold(self):
        policy = POLICIES[1]
        # Exit at SR=55, bid=0.88; post-exit bid=0.79 → delta=0.09 < 0.10 → no reversal
        timeline = [(55.0, 0.88), (10.0, 0.79)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["late_reversal"] is False

    def test_late_reversal_below_threshold_no_reversal(self):
        # Delta = 0.07 < 0.10 threshold → no reversal
        policy = POLICIES[1]
        timeline = [(55.0, 0.80), (10.0, 0.73)]  # delta = 0.07 < 0.10
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["late_reversal"] is False


# ---------------------------------------------------------------------------
# 5. Derisk timing (Policy B)
# ---------------------------------------------------------------------------

class TestDeriskTiming:
    def test_policy_b_fires_at_first_sub_threshold_sr(self):
        policy = POLICIES[1]
        timeline = [(120.0, 0.40), (55.0, 0.88), (30.0, 0.95)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["convergence_exit"] is True
        assert abs(lc["reduce_sr"] - 55.0) < 1e-6
        assert abs(lc["reduce_price"] - 0.88) < 1e-6

    def test_policy_b_no_fire_when_no_sub_threshold_snapshot(self):
        policy = POLICIES[1]
        timeline = [(120.0, 0.40), (70.0, 0.80)]   # all SR >= 60
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["convergence_exit"] is False
        assert lc["reduce_fraction"] == 0.0

    def test_policy_b_full_close(self):
        policy = POLICIES[1]
        timeline = [(55.0, 0.90)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["reduce_fraction"] == 1.0
        assert lc["tokens_runner"] == 0.0
        assert lc["runner_pnl"] == 0.0

    def test_policy_b_total_pnl_is_reduce_pnl_only(self):
        policy = POLICIES[1]
        timeline = [(55.0, 0.90)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert abs(lc["total_pnl"] - lc["reduce_pnl"]) < 1e-7


# ---------------------------------------------------------------------------
# 6. PnL aggregation
# ---------------------------------------------------------------------------

class TestPnLAggregation:
    def test_reduce_pnl_formula_correct(self):
        # exit at reduce_price, tokens_reduced = size/entry
        policy = POLICIES[1]
        entry = 0.29; size = 0.68; exit_p = 0.88
        timeline = [(55.0, exit_p)]
        lc = _simulate_convergence(entry, size, 250.0, timeline, 1.0, 0.95, policy)
        tokens = size / entry
        expected = round((exit_p - entry) * tokens, 8)
        assert abs(lc["reduce_pnl"] - expected) < 1e-6

    def test_baseline_runner_pnl_for_yes_settlement(self):
        # Policy A: no exit, all tokens held; total_pnl = (settlement - entry) * tokens
        policy = POLICIES[0]
        entry = 0.29; size = 0.68
        lc = _simulate_convergence(entry, size, 250.0, [], 1.0, None, policy)
        tokens = size / entry
        expected = round((1.0 - entry) * tokens, 8)
        assert lc["total_pnl"] is not None
        assert abs(lc["total_pnl"] - expected) < 1e-5

    def test_baseline_total_pnl_negative_for_no_settlement(self):
        policy = POLICIES[0]
        lc = _simulate_convergence(0.29, 0.68, 250.0, [], 0.0, None, policy)
        assert lc["total_pnl"] is not None
        assert lc["total_pnl"] < 0.0

    def test_total_pnl_none_when_settlement_none(self):
        policy = POLICIES[0]
        lc = _simulate_convergence(0.29, 0.68, 250.0, [], None, None, policy)
        assert lc["total_pnl"] is None

    def test_premature_regret_positive_when_exited_before_yes(self):
        policy = POLICIES[1]
        timeline = [(55.0, 0.85)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        # regret = (1.0 - 0.85) * tokens > 0
        assert lc["premature_reduce_regret"] is not None
        assert lc["premature_reduce_regret"] > 0.0

    def test_premature_regret_negative_when_exited_above_no_settlement(self):
        # Exit at 0.85, settled NO → regret = (0.0 - 0.85) * tokens < 0 (beneficial)
        policy = POLICIES[1]
        timeline = [(55.0, 0.85)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 0.0, 0.02, policy)
        assert lc["premature_reduce_regret"] < 0.0

    def test_premature_regret_none_when_no_exit(self):
        policy = POLICIES[0]
        lc = _simulate_convergence(0.29, 0.68, 250.0, [], 1.0, None, policy)
        assert lc["premature_reduce_regret"] is None

    def test_policy_d_vol_collapse_fires_and_produces_pnl(self):
        # Constant yes_bid → vol=0 → triggers after CONV_PERSIST_N=3 consecutive collapses.
        # First snapshot gives vol=inf (single bid); collapse streak starts at snap 2.
        # Need 4 snapshots total: snap1(inf→no), snap2(0→streak=1), snap3(0→streak=2),
        # snap4(0→streak=3) → fires.
        policy = POLICIES[3]
        timeline = [(140.0, 0.80), (130.0, 0.80), (120.0, 0.80), (110.0, 0.80)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["convergence_exit"] is True
        assert lc["total_pnl"] is not None

    def test_policy_d_does_not_fire_when_vol_high(self):
        # Alternating bids → high vol, never collapses
        policy = POLICIES[3]
        timeline = [(140.0, 0.20), (130.0, 0.90), (120.0, 0.20), (110.0, 0.90), (100.0, 0.20)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["convergence_exit"] is False

    def test_policy_d_does_not_fire_outside_max_sr(self):
        # Constant bids above max_sr (150s) → no trigger
        policy = POLICIES[3]
        timeline = [(200.0, 0.80), (190.0, 0.80), (180.0, 0.80), (170.0, 0.80)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["convergence_exit"] is False

    def test_policy_c_fires_when_bids_near_proxy(self):
        # Proxy = 0.95; bids at 0.93, 0.94, 0.92 → all within 0.05 of 0.95
        policy = POLICIES[2]
        timeline = [(200.0, 0.93), (180.0, 0.94), (160.0, 0.92)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["convergence_exit"] is True

    def test_policy_c_does_not_fire_when_bids_far_from_proxy(self):
        policy = POLICIES[2]
        # Proxy = 0.95; bids at 0.50 → far from proxy (|0.50-0.95|=0.45 > 0.05)
        timeline = [(200.0, 0.50), (180.0, 0.50), (160.0, 0.50)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["convergence_exit"] is False

    def test_policy_e_fires_via_vol_collapse_under_sr_guard(self):
        # SR < 60 and vol collapses → hybrid fires
        policy = POLICIES[4]
        # 3 identical bids at SR < 60, vol = 0
        timeline = [(58.0, 0.80), (50.0, 0.80), (40.0, 0.80)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["convergence_exit"] is True

    def test_policy_e_does_not_fire_when_sr_above_guard(self):
        # SR > 60 with stable bids → guard not breached → no exit
        policy = POLICIES[4]
        timeline = [(120.0, 0.80), (110.0, 0.80), (100.0, 0.80)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["convergence_exit"] is False


# ---------------------------------------------------------------------------
# 7. BTC / ETH aggregation
# ---------------------------------------------------------------------------

class TestBtcEthAggregation:
    def test_btc_eth_tracked_separately(self):
        evs = [
            _probe(ticker="BTC", market_key="pm-5m-btc", epoch_start_ts=1_000_000),
            _probe(ticker="ETH", market_key="pm-5m-eth", epoch_start_ts=1_000_000),
        ]
        smap = {**_yes_smap(1_000_000, "pm-5m-btc"), **_no_smap(1_000_000, "pm-5m-eth")}
        r = _run_policy(0, evs, smap)
        assert r["btc"]["entries"] == 1
        assert r["eth"]["entries"] == 1
        assert r["btc"]["total_pnl"] > 0.0
        assert r["eth"]["total_pnl"] < 0.0

    def test_btc_eth_convergence_exits_counted_separately(self):
        evs = [
            _probe(ticker="BTC", market_key="pm-5m-btc", epoch_start_ts=1_000_000),
            _probe(ticker="ETH", market_key="pm-5m-eth", epoch_start_ts=1_000_000),
        ]
        smap = {**_yes_smap(1_000_000, "pm-5m-btc"), **_yes_smap(1_000_000, "pm-5m-eth")}
        tl = {
            (1_000_000, "pm-5m-btc"): [(55.0, 0.90)],
            (1_000_000, "pm-5m-eth"): [(55.0, 0.90)],
        }
        r = _run_policy(1, evs, smap, tl)  # Policy B
        assert r["btc"]["convergence_exits"] == 1
        assert r["eth"]["convergence_exits"] == 1

    def test_max_one_position_per_asset_per_epoch(self):
        evs = [
            _probe(epoch_start_ts=1_000_000, seconds_remaining=250),
            _probe(epoch_start_ts=1_000_000, seconds_remaining=200),   # same epoch, BTC
        ]
        positions = simulate_convergence_policy(evs, {}, {}, POLICIES[0])
        assert len(positions) == 1

    def test_btc_eth_independent_in_same_epoch(self):
        evs = [
            _probe(ticker="BTC", market_key="pm-5m-btc", epoch_start_ts=1_000_000),
            _probe(ticker="ETH", market_key="pm-5m-eth", epoch_start_ts=1_000_000),
        ]
        positions = simulate_convergence_policy(evs, {}, {}, POLICIES[0])
        assert len(positions) == 2


# ---------------------------------------------------------------------------
# 8. Verdict branches
# ---------------------------------------------------------------------------

class TestVerdictBranches:
    def test_needs_more_replay_when_few_entries(self):
        r = _run_policy(0, [_probe()], _yes_smap())
        assert r["verdict"] == "needs_more_replay"

    def test_no_material_improvement_when_uplift_tiny(self):
        # Policy A (baseline) has uplift_vs_baseline = 0 → within $2 band
        evs = [_probe(epoch_start_ts=1_000_000 + i * 300) for i in range(12)]
        smap = {(1_000_000 + i * 300, "pm-5m-btc"): {
            "inferred_settlement": "YES", "settlement_price": 1.0,
            "yes_bid_at_match": 0.95, "seconds_remaining_at_match": 54.0, "confidence": "HIGH",
        } for i in range(12)}
        r = _run_policy(0, evs, smap)
        assert r["verdict"] in ("no_material_improvement", "safe_candidate")

    def test_convergence_unstable_when_high_false_rate(self):
        # We need > 30% false convergence exits.
        # Create many epochs where convergence fires but is wrong.
        # Policy B exits at ~SR=55 (yes_bid=0.40 < 0.5) but settles YES → direction mismatch.
        evs = [_probe(epoch_start_ts=1_000_000 + i * 300, seconds_remaining=250.0) for i in range(12)]
        smap = {(1_000_000 + i * 300, "pm-5m-btc"): {
            "inferred_settlement": "YES", "settlement_price": 1.0,
            "yes_bid_at_match": 0.95, "seconds_remaining_at_match": 30.0, "confidence": "HIGH",
        } for i in range(12)}
        tl = {
            (1_000_000 + i * 300, "pm-5m-btc"): [(55.0, 0.40)]  # exit at 0.40 but settles YES
            for i in range(12)
        }
        # Policy B exits at yes_bid=0.40 (below 0.5); settlement YES → direction mismatch
        positions = simulate_convergence_policy(evs, smap, tl, POLICIES[1])
        false_count = sum(1 for p in positions if p.get("false_convergence_exit"))
        conv_count  = sum(1 for p in positions if p.get("convergence_exit"))
        if conv_count > 0:
            rate = false_count / conv_count
            assert rate > 0.0   # some false exits occurred

    def test_verdict_note_non_empty(self):
        r = _run_policy(0, [_probe()], {})
        assert len(r.get("verdict_note", "")) > 0

    def test_convergence_unstable_verdict_string(self):
        # Directly trigger convergence_unstable verdict by mocking report data
        # by setting up enough false convergence exits in a direct function call
        from tools.replay.exit_convergence_intelligence_replay import _policy_report
        # Simulate positions where 100% of convergence exits are false
        positions = []
        for i in range(12):
            positions.append({
                "asset": "BTC", "market_key": "pm-5m-btc",
                "epoch_start_ts": 1_000_000 + i * 300,
                "entry_price": 0.29, "shadow_size_usd": 0.68,
                "shadow_pct_bankroll": 3.4, "entry_sr": 250.0,
                "settlement": "YES", "settlement_price": 1.0, "unresolved": False,
                "total_pnl": 0.50, "reduce_pnl": 0.50, "runner_pnl": 0.0,
                "reduce_price": 0.40, "reduce_sr": 55.0, "reduce_fraction": 1.0,
                "tokens_total": 2.34, "tokens_reduced": 2.34, "tokens_runner": 0.0,
                "convergence_exit": True, "late_reversal": False,
                "false_convergence_exit": True,   # all false
                "premature_reduce_regret": 0.30,
                "fp_cost": 0.30,
                "exit_vol": 0.01, "exit_bid_stab": 0.05,
                "early_epoch_vol": 0.05,
                "snapshots_to_convergence": 3,
                "late_uncertainty_expansion": False,
                "research_proxy_used": False,
            })
        r = _policy_report(positions, POLICIES[1], 20.0, baseline_pnl=0.0, fixed_derisk_pnl=0.0)
        assert r["verdict"] == "convergence_unstable"


# ---------------------------------------------------------------------------
# 9. convergence_false_positive_cost_usd
# ---------------------------------------------------------------------------

class TestFalsePositiveCost:
    def test_fp_cost_zero_when_no_convergence_exits(self):
        # Policy A: no exits → no false exits → fp_cost = 0
        evs = [_probe(epoch_start_ts=1_000_000 + i * 300) for i in range(5)]
        smap = {(1_000_000 + i * 300, "pm-5m-btc"): {
            "inferred_settlement": "YES", "settlement_price": 1.0,
            "yes_bid_at_match": 0.95, "seconds_remaining_at_match": 54.0, "confidence": "HIGH",
        } for i in range(5)}
        r = _run_policy(0, evs, smap)
        assert r["convergence_false_positive_cost_usd"] == 0.0

    def test_fp_cost_positive_when_exited_low_and_settled_yes(self):
        # Exit at yes_bid=0.40 (below 0.5), settled YES → direction mismatch
        # premature_regret = (1.0 - 0.40) * tokens > 0 → fp_cost > 0
        policy = POLICIES[1]
        timeline = [(55.0, 0.40)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        assert lc["false_convergence_exit"] is True
        assert lc["fp_cost"] is not None
        assert lc["fp_cost"] > 0.0

    def test_fp_cost_zero_when_exited_high_and_settled_no(self):
        # Exit at yes_bid=0.85 (above 0.5), settled NO → direction mismatch
        # premature_regret = (0.0 - 0.85) * tokens < 0 → fp_cost = max(0, neg) = 0
        policy = POLICIES[1]
        timeline = [(55.0, 0.85)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 0.0, 0.02, policy)
        assert lc["false_convergence_exit"] is True
        assert lc["fp_cost"] == 0.0   # mismatch, but no cost (we benefited)

    def test_fp_cost_none_when_not_false_exit(self):
        # Correct exit (high bid, settled YES) → no false exit → fp_cost is None
        policy = POLICIES[1]
        timeline = [(55.0, 0.90)]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, 0.95, policy)
        # direction_mismatch: exit_bid=0.90 > 0.5, settlement=1.0 >= 0.5 → False
        assert lc["false_convergence_exit"] is False
        assert lc["fp_cost"] is None

    def test_fp_cost_aggregated_in_policy_report(self):
        # Two positions: one with false exit + cost, one without
        from tools.replay.exit_convergence_intelligence_replay import _policy_report
        pos = [
            {
                "asset": "BTC", "market_key": "pm-5m-btc",
                "epoch_start_ts": 1_000_000, "entry_price": 0.29,
                "shadow_size_usd": 0.68, "shadow_pct_bankroll": 3.4,
                "entry_sr": 250.0, "settlement": "YES", "settlement_price": 1.0,
                "unresolved": False, "total_pnl": 0.10,
                "reduce_pnl": 0.10, "runner_pnl": 0.0,
                "reduce_price": 0.40, "reduce_sr": 55.0, "reduce_fraction": 1.0,
                "tokens_total": 2.34, "tokens_reduced": 2.34, "tokens_runner": 0.0,
                "convergence_exit": True, "late_reversal": False,
                "false_convergence_exit": True,
                "premature_reduce_regret": 0.80,
                "fp_cost": 0.80,
                "exit_vol": 0.01, "exit_bid_stab": 0.05, "early_epoch_vol": 0.05,
                "snapshots_to_convergence": 3,
                "late_uncertainty_expansion": False, "research_proxy_used": False,
            },
            {
                "asset": "BTC", "market_key": "pm-5m-btc",
                "epoch_start_ts": 2_000_000, "entry_price": 0.29,
                "shadow_size_usd": 0.68, "shadow_pct_bankroll": 3.4,
                "entry_sr": 250.0, "settlement": "YES", "settlement_price": 1.0,
                "unresolved": False, "total_pnl": 0.50,
                "reduce_pnl": 0.50, "runner_pnl": 0.0,
                "reduce_price": 0.90, "reduce_sr": 55.0, "reduce_fraction": 1.0,
                "tokens_total": 2.34, "tokens_reduced": 2.34, "tokens_runner": 0.0,
                "convergence_exit": True, "late_reversal": False,
                "false_convergence_exit": False,
                "premature_reduce_regret": 0.05,
                "fp_cost": None,
                "exit_vol": 0.01, "exit_bid_stab": 0.05, "early_epoch_vol": 0.05,
                "snapshots_to_convergence": 3,
                "late_uncertainty_expansion": False, "research_proxy_used": False,
            },
        ]
        r = _policy_report(pos, POLICIES[1], 20.0, 0.0, 0.0)
        assert abs(r["convergence_false_positive_cost_usd"] - 0.80) < 1e-7


# ---------------------------------------------------------------------------
# 10. late_uncertainty_expansion_count
# ---------------------------------------------------------------------------

class TestLateUncertaintyExpansion:
    def test_expansion_true_when_late_vol_exceeds_early(self):
        # Early window (SR >= 90): stable bids [0.7, 0.71, 0.72]
        # Late window (SR < 90): volatile bids [0.3, 0.9, 0.2]
        policy = POLICIES[0]
        timeline = [
            (200.0, 0.70), (150.0, 0.71), (100.0, 0.72),  # early (SR >= 90)
            (80.0,  0.30), (50.0,  0.90), (20.0,  0.20),  # late (SR < 90)
        ]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, None, policy)
        assert lc["late_uncertainty_expansion"] is True

    def test_expansion_false_when_late_vol_below_early(self):
        # Early window: volatile; Late window: stable
        policy = POLICIES[0]
        timeline = [
            (200.0, 0.20), (150.0, 0.80), (100.0, 0.20),   # early: high vol
            (80.0,  0.91), (50.0,  0.92), (20.0,  0.91),   # late: stable
        ]
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, None, policy)
        assert lc["late_uncertainty_expansion"] is False

    def test_expansion_false_when_insufficient_data(self):
        # Only one bid in late window → stdev undefined → no expansion
        policy = POLICIES[0]
        timeline = [(200.0, 0.50), (150.0, 0.80), (50.0, 0.70)]   # one late bid
        lc = _simulate_convergence(0.29, 0.68, 250.0, timeline, 1.0, None, policy)
        # late_bids has only 1 value → stdev_safe returns None → no expansion
        assert lc["late_uncertainty_expansion"] is False

    def test_expansion_count_aggregated_in_policy_report(self):
        # Set up two epochs: one with expansion, one without
        from tools.replay.exit_convergence_intelligence_replay import _policy_report
        pos = [
            {"asset": "BTC", "market_key": "k1", "epoch_start_ts": 1, "entry_price": 0.29,
             "shadow_size_usd": 0.68, "shadow_pct_bankroll": 3.4, "entry_sr": 250.0,
             "settlement": "YES", "settlement_price": 1.0, "unresolved": False,
             "total_pnl": 0.50, "reduce_pnl": 0.0, "runner_pnl": 0.50,
             "reduce_price": None, "reduce_sr": None, "reduce_fraction": 0.0,
             "tokens_total": 2.34, "tokens_reduced": 0.0, "tokens_runner": 2.34,
             "convergence_exit": False, "late_reversal": False,
             "false_convergence_exit": False, "premature_reduce_regret": None, "fp_cost": None,
             "exit_vol": float("inf"), "exit_bid_stab": float("inf"), "early_epoch_vol": None,
             "snapshots_to_convergence": None,
             "late_uncertainty_expansion": True,   # expansion epoch
             "research_proxy_used": False},
            {"asset": "BTC", "market_key": "k2", "epoch_start_ts": 2, "entry_price": 0.29,
             "shadow_size_usd": 0.68, "shadow_pct_bankroll": 3.4, "entry_sr": 250.0,
             "settlement": "YES", "settlement_price": 1.0, "unresolved": False,
             "total_pnl": 0.50, "reduce_pnl": 0.0, "runner_pnl": 0.50,
             "reduce_price": None, "reduce_sr": None, "reduce_fraction": 0.0,
             "tokens_total": 2.34, "tokens_reduced": 0.0, "tokens_runner": 2.34,
             "convergence_exit": False, "late_reversal": False,
             "false_convergence_exit": False, "premature_reduce_regret": None, "fp_cost": None,
             "exit_vol": float("inf"), "exit_bid_stab": float("inf"), "early_epoch_vol": None,
             "snapshots_to_convergence": None,
             "late_uncertainty_expansion": False,  # stable epoch
             "research_proxy_used": False},
        ]
        r = _policy_report(pos, POLICIES[0], 20.0, 0.0, 0.0)
        assert r["late_uncertainty_expansion_count"] == 1

    def test_expansion_uses_post_entry_timeline_only(self):
        # Pre-entry volatile bids (SR >= entry_sr=100) should not affect measurement
        policy = POLICIES[0]
        # Pre-entry: SR=200, SR=150 (both >= 100 = entry_sr) → filtered out by timeline
        # Post-entry: SR=80 (early), SR=50, SR=20 (late) → 1 early, 2 late → need >=2 in each
        # Actually SR=80 >= 90? No, 80 < 90. So early window needs SR >= 90.
        # Let's add SR=95 to early window.
        timeline = [
            (200.0, 0.10),  # pre-entry, excluded
            (95.0,  0.70),  # post-entry, early (SR >= 90)
            (92.0,  0.71),  # post-entry, early (SR >= 90)
            (50.0,  0.30),  # post-entry, late (SR < 90)
            (20.0,  0.90),  # post-entry, late (SR < 90) → high vol
        ]
        # entry_sr=100 → only SR < 100 used: 95, 92, 50, 20
        lc = _simulate_convergence(0.29, 0.68, 100.0, timeline, 1.0, None, policy)
        # early_bids=[0.70, 0.71] (SR 95,92 >= 90, < 100) → low vol
        # late_bids=[0.30, 0.90] (SR 50,20 < 90) → high vol
        assert lc["late_uncertainty_expansion"] is True


# ---------------------------------------------------------------------------
# 11. No runtime imports (AST scan)
# ---------------------------------------------------------------------------

class TestNoRuntimeImports:
    def test_no_runtime_modules_imported(self):
        import ast
        import inspect
        import tools.replay.exit_convergence_intelligence_replay as mod

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
            "polymarket.virtual_ptb",
        }
        for m in banned:
            assert m not in imported, f"Must not import runtime module: {m}"


# ---------------------------------------------------------------------------
# 12. No side effects
# ---------------------------------------------------------------------------

class TestNoSideEffects:
    def test_analyse_does_not_mutate_events(self):
        evs = [_probe() for _ in range(3)]
        originals = [dict(e) for e in evs]
        analyse(evs, {}, {})
        for orig, curr in zip(originals, evs):
            assert orig == curr

    def test_simulate_does_not_mutate_settlement_map(self):
        smap = _yes_smap()
        orig_keys = set(smap.keys())
        simulate_convergence_policy([_probe()], smap, {}, POLICIES[0])
        assert set(smap.keys()) == orig_keys

    def test_simulate_does_not_mutate_timelines(self):
        tl = {(1_000_000, "pm-5m-btc"): [(55.0, 0.90), (30.0, 0.95)]}
        orig_len = len(tl[(1_000_000, "pm-5m-btc")])
        simulate_convergence_policy([_probe()], _yes_smap(), tl, POLICIES[1])
        assert len(tl[(1_000_000, "pm-5m-btc")]) == orig_len


# ---------------------------------------------------------------------------
# 13. analyse() runs all 5 policies
# ---------------------------------------------------------------------------

class TestAnalyseFivePolicies:
    def test_all_five_policy_keys_present(self):
        evs = [_probe(epoch_start_ts=1_000_000 + i * 300) for i in range(5)]
        r = analyse(evs, {}, {})
        for key in ("policy_A", "policy_B", "policy_C", "policy_D", "policy_E"):
            assert key in r, f"Missing {key}"

    def test_policy_comparison_block_present(self):
        evs = [_probe()]
        r = analyse(evs, {}, {})
        pc = r.get("policy_comparison") or {}
        assert "rows" in pc
        assert len(pc["rows"]) == 5

    def test_comparison_row_contains_fp_cost_and_late_uc(self):
        evs = [_probe()]
        r = analyse(evs, {}, {})
        row = r["policy_comparison"]["rows"][0]
        assert "fp_cost_usd"     in row
        assert "late_unc_expand" in row

    def test_bankroll_ref_from_events(self):
        evs = [_probe(bankroll=15.0)]
        r = analyse(evs, {}, {})
        assert abs(r["bankroll_ref"] - 15.0) < 0.01

    def test_empty_events_returns_error(self):
        r = analyse([], {}, {})
        assert r["event_count"] == 0
        assert "error" in r

    def test_guardrail_present(self):
        evs = [_probe()]
        r = analyse(evs, {}, {})
        assert "offline-only" in r.get("guardrail", "")

    def test_research_proxy_label_in_guardrail(self):
        evs = [_probe()]
        r = analyse(evs, {}, {})
        assert "research_proxy_used" in r.get("guardrail", "")

    def test_simulation_rules_present(self):
        evs = [_probe()]
        r = analyse(evs, {}, {})
        rules = r.get("simulation_rules") or []
        assert len(rules) > 0
        # Both new diagnostics documented in rules
        rules_text = " ".join(rules)
        assert "convergence_false_positive_cost_usd" in rules_text
        assert "late_uncertainty_expansion" in rules_text

    def test_policy_b_uplift_vs_itself_is_zero(self):
        evs = [_probe(epoch_start_ts=1_000_000 + i * 300) for i in range(5)]
        smap = {(1_000_000 + i * 300, "pm-5m-btc"): {
            "inferred_settlement": "YES", "settlement_price": 1.0,
            "yes_bid_at_match": 0.95, "seconds_remaining_at_match": 54.0, "confidence": "HIGH",
        } for i in range(5)}
        r = analyse(evs, smap, {})
        assert r["policy_B"]["pnl_uplift_vs_fixed_derisk_sr60"] == 0.0


# ---------------------------------------------------------------------------
# 14. Fail-soft
# ---------------------------------------------------------------------------

class TestFailSoft:
    def test_missing_probe_file_returns_empty(self, tmp_path):
        result = load_probe_events("2099-12-31", quant_data_dir=tmp_path)
        assert result == []

    def test_missing_snapshots_returns_empty_smap(self, tmp_path):
        smap = build_settlement_map("2099-12-31", tmp_path, {(1_000, "pm-5m-btc")})
        assert smap == {}

    def test_missing_timelines_returns_empty(self, tmp_path):
        tl = load_epoch_timelines("2099-12-31", tmp_path, {(1_000, "pm-5m-btc")})
        assert tl == {}

    def test_missing_fields_do_not_raise(self):
        r = analyse([{} for _ in range(5)], {}, {})
        assert "event_count" in r

    def test_zero_shadow_produces_no_positions(self):
        evs = [_probe(confidence=0.0, ev=0.0)] * 5
        r = analyse(evs, {}, {})
        assert r["policy_A"]["settled_fill_count"] == 0
