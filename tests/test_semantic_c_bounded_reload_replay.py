"""
Tests for Semantic C Bounded Reload Opportunity Replay v1.

Covers:
- Policy cap tests: A takes 1, B takes 2, C takes 3 per epoch per asset
- Exposure cap tests: Policy D blocks when running exposure would exceed cap
- Reload skip tests: events beyond cap are skipped with correct reason
- PnL uplift tests: more positions = more PnL when YES wins; more loss when NO
- Drawdown tests: reload depth increases drawdown under consecutive losses
- Loss cluster tests: clustered loss detection across reload positions
- Correlated exposure: same_epoch_reload_count, max_reload_count_per_epoch,
  worst_losing_epoch_pnl, exposure_concentration, reload_loss_cluster_count
- BTC/ETH aggregation tests
- Verdict branch tests: unsafe_exposure, unsafe_drawdown, needs_more_replay, safe_candidate
- All four policies run in analyse()
- Policy comparison block present
- No runtime imports (AST scan)
- No side effects on inputs
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.semantic_c_bounded_reload_replay import (
    _POLICY_D_EXPOSURE_CAP,
    _UNSAFE_EXPOSURE_PCT,
    _compute_pnl,
    _compute_shadow,
    _max_drawdown,
    _clustered_losses,
    analyse,
    build_settlement_map,
    load_probe_events,
    simulate_reload_policy,
    POLICIES,
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


def _yes_smap(epoch_start_ts: int = 1_000_000, market_key: str = "pm-5m-btc") -> dict:
    return {(epoch_start_ts, market_key): {
        "inferred_settlement": "YES", "settlement_price": 1.0,
        "yes_bid_at_match": 0.95, "seconds_remaining_at_match": 50.0, "confidence": "HIGH",
    }}


def _no_smap(epoch_start_ts: int = 1_000_000, market_key: str = "pm-5m-btc") -> dict:
    return {(epoch_start_ts, market_key): {
        "inferred_settlement": "NO", "settlement_price": 0.0,
        "yes_bid_at_match": 0.02, "seconds_remaining_at_match": 50.0, "confidence": "HIGH",
    }}


def _ambig_smap(epoch_start_ts: int = 1_000_000, market_key: str = "pm-5m-btc") -> dict:
    return {(epoch_start_ts, market_key): {
        "inferred_settlement": "AMBIGUOUS", "settlement_price": None,
        "yes_bid_at_match": 0.50, "seconds_remaining_at_match": 50.0, "confidence": "AMBIGUOUS",
    }}


def _multi_ev(n: int, epoch_start_ts: int = 1_000_000, **kw) -> list[dict]:
    """n events in the same epoch at decreasing SR."""
    return [_probe(epoch_start_ts=epoch_start_ts,
                   seconds_remaining=250.0 - i * 20, **kw)
            for i in range(n)]


def _run_policy(policy_idx: int, events: list[dict], smap: dict,
                bankroll_ref: float = 20.0) -> dict:
    sim = simulate_reload_policy(events, smap, POLICIES[policy_idx], bankroll_ref)
    from tools.semantic_c_bounded_reload_replay import _policy_report
    baseline_pnl = 0.0
    if policy_idx > 0:
        sim_a = simulate_reload_policy(events, smap, POLICIES[0], bankroll_ref)
        r_a = _policy_report(sim_a, POLICIES[0], bankroll_ref, 0.0)
        baseline_pnl = r_a["realized_proxy_pnl"]
    return _policy_report(sim, POLICIES[policy_idx], bankroll_ref, baseline_pnl)


# ===========================================================================
# 1. Policy cap tests
# ===========================================================================

class TestPolicyCaps:
    def test_policy_a_takes_one_per_epoch(self):
        evs = _multi_ev(5)
        sim = simulate_reload_policy(evs, {}, POLICIES[0])
        assert len(sim["positions"]) == 1

    def test_policy_b_takes_two_per_epoch(self):
        evs = _multi_ev(5)
        sim = simulate_reload_policy(evs, {}, POLICIES[1])
        assert len(sim["positions"]) == 2

    def test_policy_c_takes_three_per_epoch(self):
        evs = _multi_ev(5)
        sim = simulate_reload_policy(evs, {}, POLICIES[2])
        assert len(sim["positions"]) == 3

    def test_policy_b_skips_when_only_one_event(self):
        evs = [_probe()]
        sim = simulate_reload_policy(evs, {}, POLICIES[1])
        assert len(sim["positions"]) == 1
        assert len(sim["skipped"]) == 0

    def test_policies_independent_across_epochs(self):
        evs = (
            _multi_ev(3, epoch_start_ts=1_000_000)
            + _multi_ev(3, epoch_start_ts=2_000_000)
        )
        sim = simulate_reload_policy(evs, {}, POLICIES[1])
        assert len(sim["positions"]) == 4  # 2 per epoch × 2 epochs

    def test_is_reload_flag_on_second_position(self):
        evs = _multi_ev(3)
        sim = simulate_reload_policy(evs, {}, POLICIES[1])
        assert sim["positions"][0]["is_reload"] is False
        assert sim["positions"][1]["is_reload"] is True

    def test_policy_a_no_reload_flags(self):
        evs = _multi_ev(3)
        sim = simulate_reload_policy(evs, {}, POLICIES[0])
        assert all(not p["is_reload"] for p in sim["positions"])


# ===========================================================================
# 2. Exposure cap tests (Policy D)
# ===========================================================================

class TestExposureCap:
    def test_policy_d_blocks_when_cap_exceeded(self):
        # Large raw_size creates high pct_bankroll; cap at 7.5%
        # One event might already hit the cap depending on shadow
        evs = [
            _probe(epoch_start_ts=1_000_000, seconds_remaining=250,
                   confidence=0.75, ev=0.20, raw_size_usd=2.0, bankroll=5.0),
        ] * 10
        sim = simulate_reload_policy(evs, {}, POLICIES[3])
        total_pct = sum(p["shadow_pct_bankroll"] for p in sim["positions"])
        assert total_pct <= _POLICY_D_EXPOSURE_CAP + 0.1  # small tolerance for floating point

    def test_policy_d_allows_when_under_cap(self):
        # Small positions: ~1.9% each; 3 fit under 7.5%
        evs = _multi_ev(5, raw_size_usd=0.68, bankroll=20.0)
        sim = simulate_reload_policy(evs, {}, POLICIES[3])
        assert len(sim["positions"]) >= 2  # at least some reloads allowed

    def test_policy_d_skip_reason_is_exposure_cap(self):
        evs = [
            _probe(epoch_start_ts=1_000_000, seconds_remaining=250 - i * 10,
                   confidence=0.75, ev=0.20, raw_size_usd=2.0, bankroll=5.0)
            for i in range(5)
        ]
        sim = simulate_reload_policy(evs, {}, POLICIES[3])
        skip_reasons = [s["skip_reason"] for s in sim["skipped"]]
        assert "exposure_cap" in skip_reasons

    def test_policy_d_exposure_tracked_across_assets(self):
        # BTC and ETH at same epoch_ts; their exposure sums toward the cap
        evs = [
            _probe(ticker="BTC", market_key="pm-5m-btc", epoch_start_ts=1_000_000,
                   seconds_remaining=250, confidence=0.75, ev=0.20,
                   raw_size_usd=1.5, bankroll=5.0),
            _probe(ticker="ETH", market_key="pm-5m-eth", epoch_start_ts=1_000_000,
                   seconds_remaining=250, confidence=0.75, ev=0.20,
                   raw_size_usd=1.5, bankroll=5.0),
        ]
        sim = simulate_reload_policy(evs, {}, POLICIES[3])
        total_pct = sum(p["shadow_pct_bankroll"] for p in sim["positions"])
        assert total_pct <= _POLICY_D_EXPOSURE_CAP + 0.1


# ===========================================================================
# 3. Reload skip tests
# ===========================================================================

class TestReloadSkips:
    def test_skipped_count_correct_for_policy_a(self):
        evs = _multi_ev(4)
        sim = simulate_reload_policy(evs, {}, POLICIES[0])
        assert len(sim["skipped"]) == 3

    def test_skipped_count_correct_for_policy_b(self):
        evs = _multi_ev(4)
        sim = simulate_reload_policy(evs, {}, POLICIES[1])
        assert len(sim["skipped"]) == 2

    def test_skip_reason_count_cap(self):
        evs = _multi_ev(4)
        sim = simulate_reload_policy(evs, {}, POLICIES[0])
        assert all(s["skip_reason"] == "count_cap" for s in sim["skipped"])

    def test_skip_records_settlement_when_available(self):
        evs = _multi_ev(3)
        smap = _yes_smap()
        sim = simulate_reload_policy(evs, smap, POLICIES[0])
        for s in sim["skipped"]:
            assert s["settlement"] == "YES"

    def test_zero_skips_when_all_events_fit(self):
        evs = _multi_ev(2)
        sim = simulate_reload_policy(evs, {}, POLICIES[2])  # cap=3; 2 events -> 0 skipped
        assert len(sim["skipped"]) == 0

    def test_zero_shadow_events_produce_no_skips(self):
        evs = [_probe(confidence=0.0, ev=0.0)] * 5
        sim = simulate_reload_policy(evs, {}, POLICIES[1])
        assert len(sim["positions"]) == 0
        assert len(sim["skipped"]) == 0


# ===========================================================================
# 4. PnL uplift tests
# ===========================================================================

class TestPnLUplift:
    def test_more_positions_more_pnl_when_yes_wins(self):
        evs = _multi_ev(4)
        smap = _yes_smap()
        r_a = _run_policy(0, evs, smap)
        r_b = _run_policy(1, evs, smap)
        assert r_b["realized_proxy_pnl"] > r_a["realized_proxy_pnl"]
        assert r_b["pnl_uplift_vs_baseline_usd"] > 0.0

    def test_more_positions_more_loss_when_no_wins(self):
        evs = _multi_ev(4)
        smap = _no_smap()
        r_a = _run_policy(0, evs, smap)
        r_b = _run_policy(1, evs, smap)
        assert r_b["realized_proxy_pnl"] < r_a["realized_proxy_pnl"]
        assert r_b["pnl_uplift_vs_baseline_usd"] < 0.0

    def test_captured_opportunity_cost_positive_when_reloads_win(self):
        evs = _multi_ev(3)
        smap = _yes_smap()
        r_b = _run_policy(1, evs, smap)
        assert r_b["captured_opportunity_cost_usd"] > 0.0

    def test_captured_opportunity_cost_zero_for_policy_a(self):
        evs = _multi_ev(3)
        smap = _yes_smap()
        r_a = _run_policy(0, evs, smap)
        assert r_a["captured_opportunity_cost_usd"] == 0.0

    def test_captured_opportunity_cost_negative_when_reloads_lose(self):
        evs = _multi_ev(3)
        smap = _no_smap()
        r_b = _run_policy(1, evs, smap)
        assert r_b["captured_opportunity_cost_usd"] < 0.0


# ===========================================================================
# 5. Drawdown tests
# ===========================================================================

class TestDrawdown:
    def test_drawdown_increases_with_reloads_under_losses(self):
        # Two epochs: one YES, one NO -- more reloads in NO epoch = larger drawdown
        evs = (
            _multi_ev(3, epoch_start_ts=1_000_000)
            + _multi_ev(3, epoch_start_ts=2_000_000)
        )
        smap = {**_yes_smap(1_000_000), **_no_smap(2_000_000)}
        r_a = _run_policy(0, evs, smap)
        r_b = _run_policy(1, evs, smap)
        assert r_b["max_drawdown"] >= r_a["max_drawdown"]

    def test_zero_drawdown_when_all_yes(self):
        evs = _multi_ev(3)
        smap = _yes_smap()
        r = _run_policy(1, evs, smap)
        assert r["max_drawdown"] == 0.0

    def test_drawdown_pct_bankroll_computed(self):
        evs = _multi_ev(3)
        smap = _no_smap()
        r = _run_policy(1, evs, smap)
        assert r["max_drawdown_pct_bankroll"] >= 0.0


# ===========================================================================
# 6. Correlated exposure tests
# ===========================================================================

class TestCorrelatedExposure:
    def test_same_epoch_reload_count_zero_for_policy_a(self):
        evs = _multi_ev(3)
        r = _run_policy(0, evs, {})
        ce = r["correlated_exposure"]
        assert ce["same_epoch_reload_count"] == 0

    def test_same_epoch_reload_count_nonzero_for_policy_b(self):
        evs = _multi_ev(3)
        r = _run_policy(1, evs, {})
        ce = r["correlated_exposure"]
        assert ce["same_epoch_reload_count"] == 1

    def test_max_reload_count_per_epoch_matches_cap(self):
        evs = _multi_ev(5)
        r_b = _run_policy(1, evs, {})
        r_c = _run_policy(2, evs, {})
        assert r_b["correlated_exposure"]["max_reload_count_per_epoch"] == 2
        assert r_c["correlated_exposure"]["max_reload_count_per_epoch"] == 3

    def test_worst_losing_epoch_pnl_negative_when_loss(self):
        evs = _multi_ev(3)
        smap = _no_smap()
        r = _run_policy(1, evs, smap)
        ce = r["correlated_exposure"]
        assert ce["worst_losing_epoch_pnl"] < 0.0

    def test_worst_losing_epoch_pnl_zero_when_no_settled(self):
        evs = _multi_ev(3)
        r = _run_policy(1, evs, {})  # no settlement = no PnL
        ce = r["correlated_exposure"]
        assert ce["worst_losing_epoch_pnl"] == 0.0

    def test_exposure_concentration_stats_populated(self):
        evs = _multi_ev(3)
        smap = _yes_smap()
        r = _run_policy(1, evs, smap)
        ec = r["correlated_exposure"]["exposure_concentration_by_epoch"]
        assert ec["count"] >= 1
        assert ec["max"] >= ec["mean"]

    def test_reload_loss_cluster_count_positive_when_reloads_lose(self):
        evs = _multi_ev(3)
        smap = _no_smap()
        r = _run_policy(1, evs, smap)
        ce = r["correlated_exposure"]
        assert ce["reload_loss_cluster_count"] >= 1

    def test_reload_loss_cluster_count_zero_when_no_reloads(self):
        evs = _multi_ev(1)
        smap = _no_smap()
        r = _run_policy(0, evs, smap)
        ce = r["correlated_exposure"]
        assert ce["reload_loss_cluster_count"] == 0

    def test_correlated_exposure_warning_present(self):
        evs = _multi_ev(3)
        r = _run_policy(1, evs, {})
        ce = r["correlated_exposure"]
        assert "warning" in ce
        assert "correlated" in ce["warning"].lower() or "same settlement" in ce["warning"].lower()


# ===========================================================================
# 7. Loss cluster tests
# ===========================================================================

class TestLossCluster:
    def test_no_cluster_when_isolated_losses(self):
        evs = [
            _probe(epoch_start_ts=1_000_000),
            _probe(epoch_start_ts=2_000_000),
            _probe(epoch_start_ts=3_000_000),
        ]
        smap = {
            **_no_smap(1_000_000),
            **_yes_smap(2_000_000),
            **_no_smap(3_000_000),
        }
        r = _run_policy(0, evs, smap)
        cl = r["clustered_loss_periods"]
        assert cl["loss_cluster_count"] == 0
        assert cl["max_consecutive_losses"] == 1

    def test_cluster_detected_consecutive_losses(self):
        evs = [
            _probe(epoch_start_ts=1_000_000),
            _probe(epoch_start_ts=2_000_000),
            _probe(epoch_start_ts=3_000_000),
        ]
        smap = {
            **_no_smap(1_000_000),
            **_no_smap(2_000_000),
            **_yes_smap(3_000_000),
        }
        r = _run_policy(0, evs, smap)
        cl = r["clustered_loss_periods"]
        assert cl["max_consecutive_losses"] == 2
        assert cl["loss_cluster_count"] == 1

    def test_max_drawdown_unit(self):
        assert abs(_max_drawdown([0.10, -0.30, 0.50]) - 0.30) < 1e-8


# ===========================================================================
# 8. BTC / ETH aggregation tests
# ===========================================================================

class TestAssetAggregation:
    def test_btc_eth_separated(self):
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

    def test_reload_adds_to_asset_entry_count(self):
        evs = _multi_ev(3)
        smap = _yes_smap()
        r_a = _run_policy(0, evs, smap)
        r_b = _run_policy(1, evs, smap)
        assert r_b["btc"]["entries"] > r_a["btc"]["entries"]


# ===========================================================================
# 9. Verdict branch tests
# ===========================================================================

class TestVerdictBranches:
    def test_unsafe_exposure_verdict(self):
        # Force exposure > 10%: raw_size=2.0, bankroll=5.0, 5 events in same epoch
        evs = [
            _probe(epoch_start_ts=1_000_000, seconds_remaining=250 - i * 10,
                   confidence=0.75, ev=0.20, raw_size_usd=2.0, bankroll=5.0)
            for i in range(5)
        ]
        smap = {(1_000_000, "pm-5m-btc"): {
            "inferred_settlement": "YES", "settlement_price": 1.0,
            "yes_bid_at_match": 0.95, "seconds_remaining_at_match": 50.0,
            "confidence": "HIGH",
        }}
        r = _run_policy(2, evs, smap)  # policy C = 3 positions = ~120% exposure
        assert r["verdict"] == "unsafe_exposure"

    def test_needs_more_replay_when_too_few_entries(self):
        evs = [_probe()]
        smap = _yes_smap()
        r = _run_policy(0, evs, smap)
        assert r["verdict"] == "needs_more_replay"

    def test_safe_candidate_for_bounded_normal_sizing(self):
        evs = [_probe(epoch_start_ts=1_000_000 + i * 300) for i in range(12)]
        smap = {(1_000_000 + i * 300, "pm-5m-btc"): {
            "inferred_settlement": "YES", "settlement_price": 1.0,
            "yes_bid_at_match": 0.95, "seconds_remaining_at_match": 50.0,
            "confidence": "HIGH",
        } for i in range(12)}
        r = _run_policy(0, evs, smap)
        assert r["verdict"] == "safe_candidate"

    def test_verdict_note_non_empty(self):
        evs = [_probe()]
        r = _run_policy(0, evs, {})
        assert len(r.get("verdict_note", "")) > 0


# ===========================================================================
# 10. analyse() runs all four policies
# ===========================================================================

class TestAnalyseFourPolicies:
    def test_all_four_policies_present(self):
        evs = [_probe(epoch_start_ts=1_000_000 + i * 300) for i in range(5)]
        r = analyse(evs, {})
        assert "policy_A" in r
        assert "policy_B" in r
        assert "policy_C" in r
        assert "policy_D" in r

    def test_policy_comparison_block_present(self):
        evs = [_probe()]
        r = analyse(evs, {})
        pc = r.get("policy_comparison") or {}
        assert "rows" in pc
        assert "recommended" in pc
        assert len(pc["rows"]) == 4

    def test_reload_caveats_present(self):
        evs = [_probe()]
        r = analyse(evs, {})
        caveats = r.get("reload_caveats") or []
        assert len(caveats) > 0
        combined = " ".join(caveats).lower()
        assert "correlated" in combined or "same settlement" in combined or "diversification" in combined

    def test_empty_events_returns_error(self):
        r = analyse([], {})
        assert r["event_count"] == 0
        assert "error" in r

    def test_bankroll_ref_derived_from_events(self):
        evs = [_probe(bankroll=15.0)]
        r = analyse(evs, {})
        assert abs(r["bankroll_ref"] - 15.0) < 0.01

    def test_unsafe_drawdown_usd_is_10pct_of_bankroll(self):
        evs = [_probe(bankroll=20.0)]
        r = analyse(evs, {})
        assert abs(r["unsafe_drawdown_usd"] - 2.0) < 0.01

    def test_policies_entries_non_decreasing_a_to_c(self):
        # More positions allowed -> entries >= prior policy
        evs = _multi_ev(4)
        r = analyse(evs, {})
        ea = r["policy_A"]["entries"]
        eb = r["policy_B"]["entries"]
        ec = r["policy_C"]["entries"]
        assert eb >= ea
        assert ec >= eb


# ===========================================================================
# 11. Cutoff collision rate
# ===========================================================================

class TestCutoffCollisionRate:
    def test_zero_collision_when_sr_high(self):
        evs = [_probe(seconds_remaining=200.0)]
        r = _run_policy(0, evs, {})
        assert r["cutoff_collision_rate_pct"] == 0.0

    def test_100_collision_when_sr_low(self):
        evs = [_probe(seconds_remaining=45.0)]
        r = _run_policy(0, evs, {})
        assert r["cutoff_collision_rate_pct"] == 100.0


# ===========================================================================
# 12. Fail-soft
# ===========================================================================

class TestFailSoft:
    def test_missing_probe_file_returns_empty(self, tmp_path):
        result = load_probe_events("2099-12-31", quant_data_dir=tmp_path)
        assert result == []

    def test_missing_snapshots_file_returns_empty_smap(self, tmp_path):
        smap = build_settlement_map("2099-12-31", tmp_path, {(1_000, "pm-5m-btc")})
        assert smap == {}

    def test_missing_fields_do_not_raise(self):
        evs = [{} for _ in range(5)]
        r = analyse(evs, {})
        assert "event_count" in r

    def test_zero_shadow_events_safe(self):
        evs = [_probe(confidence=0.0, ev=0.0)] * 5
        r = analyse(evs, {})
        assert r["policy_A"]["entries"] == 0


# ===========================================================================
# 13. No runtime imports
# ===========================================================================

class TestNoRuntimeImports:
    def test_no_runtime_modules_imported(self):
        import ast
        import inspect
        import tools.semantic_c_bounded_reload_replay as mod

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
            "polymarket.trader", "polymarket.order_manager",
            "polymarket.position_sizing", "utils.risk_manager",
            "polymarket.bankroll_tiers",
        }
        for m in banned:
            assert m not in imported, f"Must not import runtime module: {m}"

    def test_analyse_no_side_effects_on_events(self):
        evs = [_probe() for _ in range(3)]
        originals = [dict(e) for e in evs]
        analyse(evs, {})
        for orig, curr in zip(originals, evs):
            assert orig == curr

    def test_simulate_no_side_effects_on_smap(self):
        smap = _yes_smap()
        original_keys = set(smap.keys())
        simulate_reload_policy([_probe()], smap, POLICIES[0])
        assert set(smap.keys()) == original_keys
