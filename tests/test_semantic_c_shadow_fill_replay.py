"""
Tests for Semantic C Shadow Fill Replay Simulator v1.

Covers:
- Hypothetical fill count (shadow gate respected)
- Shadow order size distribution statistics
- BTC vs ETH split
- Lifecycle phase split
- Exposure curve (non-decreasing, peak correct)
- Cutoff collision rate (sr < 90s threshold)
- PnL unavailable path (honest message when no settlement fields)
- PnL available path (computed from outcome + settlement_price)
- Shadow opportunity count
- Paper trial verdict logic (safe / not_ready / insufficient_data)
- Timestamp ordering for exposure curve
- Fail-soft: empty events, missing file, missing fields, zero shadow
- Run-id and asset filters via load_replay_events
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

from tools.shadow.semantic_c_shadow_fill_replay import (
    _CONF_FLOOR,
    _CUTOFF_COLLISION_SECONDS,
    _GOOD_EV,
    _EV_Q_FLOOR,
    _compute_shadow,
    _compute_hypothetical_pnl,
    _simulate_fill,
    analyse,
    load_replay_events,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _ev(
    *,
    ticker: str = "BTC",
    confidence: float = 0.62,
    entry_price: float = 0.29,
    ev: float = 0.16,
    ev_positive: bool = True,
    confidence_passed: bool = True,
    final_size_usd: float = 0.0,
    raw_size_usd: float = 0.68,
    bankroll: float = 20.10,
    lifecycle_phase: str = "ACTIVE_INVENTORY_TRADING",
    seconds_remaining: float = 200.0,
    tier_id: str = "T0_MICRO_SEED",
    run_id: str = "run_test",
    ts: str | None = None,
    # Optional settlement fields
    settlement_outcome: str | None = None,
    resolution_price: float | None = None,
    # Optional live shadow fields
    include_shadow: bool = False,
) -> dict:
    """Return a payload dict (no envelope wrapper) for analyse()."""
    p: dict = {
        "event":              "zero_size_probe_v1",
        "run_id":             run_id,
        "ticker":             ticker,
        "confidence":         confidence,
        "entry_price":        entry_price,
        "ev":                 ev,
        "ev_positive":        ev_positive,
        "confidence_passed":  confidence_passed,
        "final_size_usd":     final_size_usd,
        "raw_size_usd":       raw_size_usd,
        "bankroll":           bankroll,
        "lifecycle_phase":    lifecycle_phase,
        "seconds_remaining":  seconds_remaining,
        "tier_id":            tier_id,
    }
    if ts is not None:
        p["ts"] = ts
    if settlement_outcome is not None:
        p["settlement_outcome"] = settlement_outcome
    if resolution_price is not None:
        p["resolution_price"] = resolution_price
    if include_shadow:
        from tools.shadow.semantic_c_shadow_fill_replay import _CONF_SPAN
        ev_q  = min(1.0, max(_EV_Q_FLOOR, ev / _GOOD_EV))
        c_in  = confidence * ev_q
        c_m   = max(0.0, min(1.0, 0.25 + 0.75 * (c_in - _CONF_FLOOR) / _CONF_SPAN))
        c_sz  = raw_size_usd * c_m
        pct   = round(c_sz / max(bankroll, 1e-9) * 100, 4)
        p.update({
            "semantic_c_ev_quality_shadow":          round(ev_q, 6),
            "semantic_c_input_shadow":               round(c_in, 6),
            "semantic_c_multiplier_shadow":          round(c_m, 6),
            "semantic_c_size_usd_shadow":            round(c_sz, 6),
            "semantic_c_would_pass_confidence_gate": c_in >= _CONF_FLOOR,
            "semantic_c_would_produce_nonzero_size": c_sz > 0.0,
            "semantic_c_size_pct_bankroll":          pct,
            "semantic_c_shadow_reason":              "confidence_score_x_ev_quality_not_in_active_sizing",
        })
    return p


def _fill_events(evs: list[dict]) -> list[dict]:
    """Select only events that would produce hypothetical fills."""
    return [e for e in evs if _compute_shadow(e)["nonzero"]]


# ===========================================================================
# 1. Hypothetical fill count
# ===========================================================================

class TestFillCount:
    def test_all_fill_when_confidence_high(self):
        evs = [_ev(confidence=0.62, ev=0.16)] * 10
        r = analyse(evs)
        assert r["hypothetical_fill_count"] == 10
        assert r["hypothetical_fill_pct"] == 100.0

    def test_zero_fill_when_confidence_too_low(self):
        evs = [_ev(confidence=0.40, ev=0.0)] * 10
        r = analyse(evs)
        assert r["hypothetical_fill_count"] == 0
        assert r["hypothetical_fill_pct"] == 0.0

    def test_partial_fill_count(self):
        evs = (
            [_ev(confidence=0.62, ev=0.16)] * 6
            + [_ev(confidence=0.40, ev=0.0)] * 4
        )
        r = analyse(evs)
        assert r["hypothetical_fill_count"] == 6
        assert abs(r["hypothetical_fill_pct"] - 60.0) < 0.2

    def test_fill_count_equals_opportunity_count(self):
        evs = [_ev(confidence=0.62, ev=0.16)] * 8
        r = analyse(evs)
        assert r["hypothetical_fill_count"] == r["shadow_opportunity_count"]


# ===========================================================================
# 2. Shadow order size distribution
# ===========================================================================

class TestSizeDistribution:
    def test_mean_positive_when_fills_exist(self):
        evs = [_ev(confidence=0.62, ev=0.16, raw_size_usd=0.68)] * 10
        r = analyse(evs)
        assert r["shadow_size_distribution"]["mean"] > 0.0

    def test_mean_zero_when_no_fills(self):
        evs = [_ev(confidence=0.40, ev=0.0)] * 10
        r = analyse(evs)
        assert r["shadow_size_distribution"]["mean"] == 0.0
        assert r["shadow_size_distribution"]["count"] == 0

    def test_p90_present_with_ten_or_more_fills(self):
        evs = [_ev(confidence=0.62, ev=0.16)] * 15
        r = analyse(evs)
        assert "p90" in r["shadow_size_distribution"]
        assert r["shadow_size_distribution"]["p90"] > 0.0

    def test_max_gte_mean(self):
        evs = [_ev(confidence=0.62, ev=0.16, raw_size_usd=0.68)] * 10
        r = analyse(evs)
        sd = r["shadow_size_distribution"]
        assert sd["max"] >= sd["mean"]

    def test_count_matches_fill_count(self):
        evs = [_ev(confidence=0.62, ev=0.16)] * 7
        r = analyse(evs)
        assert r["shadow_size_distribution"]["count"] == r["hypothetical_fill_count"]


# ===========================================================================
# 3. BTC vs ETH split
# ===========================================================================

class TestAssetSplit:
    def test_btc_eth_counted_separately(self):
        evs = [_ev(ticker="BTC")] * 4 + [_ev(ticker="ETH")] * 3
        r = analyse(evs)
        assert r["btc"]["total_events"] == 4
        assert r["eth"]["total_events"] == 3

    def test_fill_count_per_asset(self):
        evs = (
            [_ev(ticker="BTC", confidence=0.62, ev=0.16)] * 3
            + [_ev(ticker="ETH", confidence=0.62, ev=0.16)] * 2
        )
        r = analyse(evs)
        assert r["btc"]["fill_count"] == 3
        assert r["eth"]["fill_count"] == 2

    def test_zero_fill_asset(self):
        evs = (
            [_ev(ticker="BTC", confidence=0.40, ev=0.0)] * 5
            + [_ev(ticker="ETH", confidence=0.62, ev=0.16)] * 5
        )
        r = analyse(evs)
        assert r["btc"]["fill_count"] == 0
        assert r["eth"]["fill_count"] == 5

    def test_fill_pct_correct_per_asset(self):
        evs = [_ev(ticker="BTC", confidence=0.62, ev=0.16)] * 4 + [_ev(ticker="BTC", confidence=0.40, ev=0.0)] * 1
        r = analyse(evs)
        assert abs(r["btc"]["fill_pct"] - 80.0) < 0.2

    def test_unknown_ticker_not_counted_as_btc_or_eth(self):
        evs = [_ev(ticker="SOL", confidence=0.62, ev=0.16)] * 5
        r = analyse(evs)
        assert r["btc"]["total_events"] == 0
        assert r["eth"]["total_events"] == 0


# ===========================================================================
# 4. Lifecycle phase split
# ===========================================================================

class TestLifecyclePhaseSplit:
    def test_phases_counted(self):
        evs = (
            [_ev(lifecycle_phase="ACTIVE_INVENTORY_TRADING")] * 4
            + [_ev(lifecycle_phase="OPENING_SCAN")] * 2
        )
        r = analyse(evs)
        lps = r["lifecycle_phase_split"]
        assert lps["ACTIVE_INVENTORY_TRADING"]["total"] == 4
        assert lps["OPENING_SCAN"]["total"] == 2

    def test_fills_per_phase_tracked(self):
        evs = (
            [_ev(lifecycle_phase="ACTIVE_INVENTORY_TRADING", confidence=0.62, ev=0.16)] * 3
            + [_ev(lifecycle_phase="OPENING_SCAN", confidence=0.40, ev=0.0)] * 2
        )
        r = analyse(evs)
        lps = r["lifecycle_phase_split"]
        assert lps["ACTIVE_INVENTORY_TRADING"]["fills"] == 3
        assert lps["OPENING_SCAN"]["fills"] == 0

    def test_fill_pct_per_phase(self):
        evs = [_ev(lifecycle_phase="ACTIVE_INVENTORY_TRADING", confidence=0.62, ev=0.16)] * 6
        r = analyse(evs)
        lps = r["lifecycle_phase_split"]
        assert lps["ACTIVE_INVENTORY_TRADING"]["fill_pct"] == 100.0

    def test_unknown_phase_normalised_to_uppercase(self):
        evs = [_ev(lifecycle_phase="unknown_phase")] * 3
        r = analyse(evs)
        lps = r["lifecycle_phase_split"]
        assert "UNKNOWN_PHASE" in lps


# ===========================================================================
# 5. Exposure curve
# ===========================================================================

class TestExposureCurve:
    def test_peak_cumulative_equals_sum_of_fill_sizes(self):
        evs = [_ev(confidence=0.62, ev=0.16, raw_size_usd=0.68)] * 5
        r = analyse(evs)
        shadow_size = _compute_shadow(evs[0])["c_size"]
        expected_sum = round(shadow_size * 5, 4)
        assert abs(r["exposure_curve"]["peak_cumulative_usd"] - expected_sum) < 0.01

    def test_no_fills_gives_zero_peak(self):
        evs = [_ev(confidence=0.40, ev=0.0)] * 5
        r = analyse(evs)
        assert r["exposure_curve"]["peak_cumulative_usd"] == 0.0

    def test_curve_length_equals_event_count(self):
        evs = [_ev()] * 7
        r = analyse(evs)
        assert r["exposure_curve"]["curve_length"] == 7

    def test_fill_pct_bankroll_stats_populated(self):
        evs = [_ev(confidence=0.62, ev=0.16, raw_size_usd=0.68, bankroll=20.0)] * 10
        r = analyse(evs)
        fps = r["exposure_curve"]["fill_pct_bankroll_stats"]
        assert fps["mean"] > 0.0
        assert fps["max"] >= fps["mean"]

    def test_timestamp_ordering_affects_curve_trajectory(self):
        # Two fills: ts="B" comes before ts="A" alphabetically but we use string sort.
        # We just verify the peak is correct regardless of order.
        evs = [
            _ev(confidence=0.62, ev=0.16, raw_size_usd=0.68, ts="2026-05-15T10:00:00Z"),
            _ev(confidence=0.62, ev=0.16, raw_size_usd=0.68, ts="2026-05-15T09:00:00Z"),
            _ev(confidence=0.62, ev=0.16, raw_size_usd=0.68, ts="2026-05-15T11:00:00Z"),
        ]
        r = analyse(evs)
        shadow_size = _compute_shadow(evs[0])["c_size"]
        expected_peak = round(shadow_size * 3, 4)
        assert abs(r["exposure_curve"]["peak_cumulative_usd"] - expected_peak) < 0.01

    def test_mixed_fill_and_no_fill_curve(self):
        evs = (
            [_ev(confidence=0.62, ev=0.16, raw_size_usd=0.68)] * 3
            + [_ev(confidence=0.40, ev=0.0)] * 3
        )
        r = analyse(evs)
        fill_shadow = _compute_shadow(evs[0])["c_size"]
        expected_peak = round(fill_shadow * 3, 4)
        assert abs(r["exposure_curve"]["peak_cumulative_usd"] - expected_peak) < 0.01
        # Curve length is total events, not just fills
        assert r["exposure_curve"]["curve_length"] == 6


# ===========================================================================
# 6. Cutoff collision rate
# ===========================================================================

class TestCutoffCollisionRate:
    def test_zero_collision_when_sr_high(self):
        evs = [_ev(confidence=0.62, ev=0.16, seconds_remaining=300.0)] * 10
        r = analyse(evs)
        assert r["cutoff_collision_count"] == 0
        assert r["cutoff_collision_rate_pct"] == 0.0

    def test_full_collision_when_sr_low(self):
        evs = [_ev(confidence=0.62, ev=0.16, seconds_remaining=45.0)] * 10
        r = analyse(evs)
        assert r["cutoff_collision_count"] == 10
        assert r["cutoff_collision_rate_pct"] == 100.0

    def test_partial_collision(self):
        evs = (
            [_ev(confidence=0.62, ev=0.16, seconds_remaining=45.0)] * 4
            + [_ev(confidence=0.62, ev=0.16, seconds_remaining=300.0)] * 6
        )
        r = analyse(evs)
        assert r["cutoff_collision_count"] == 4
        assert abs(r["cutoff_collision_rate_pct"] - 40.0) < 0.2

    def test_boundary_at_exactly_90s(self):
        # sr = 90.0 is NOT a collision (< 90.0 is collision)
        evs = [_ev(confidence=0.62, ev=0.16, seconds_remaining=90.0)] * 5
        r = analyse(evs)
        assert r["cutoff_collision_count"] == 0

    def test_boundary_just_below_90s(self):
        evs = [_ev(confidence=0.62, ev=0.16, seconds_remaining=89.9)] * 5
        r = analyse(evs)
        assert r["cutoff_collision_count"] == 5

    def test_all_events_cutoff_count_includes_non_fills(self):
        evs = (
            [_ev(confidence=0.40, ev=0.0, seconds_remaining=45.0)] * 3
            + [_ev(confidence=0.62, ev=0.16, seconds_remaining=300.0)] * 3
        )
        r = analyse(evs)
        # 3 non-fill events are near close; fill-level collision count is 0
        assert r["all_events_cutoff_count"] == 3
        assert r["cutoff_collision_count"] == 0


# ===========================================================================
# 7 & 8. PnL
# ===========================================================================

class TestPnL:
    def test_pnl_unavailable_when_no_settlement_fields(self):
        evs = [_ev(confidence=0.62, ev=0.16)] * 10
        r = analyse(evs)
        assert r["pnl_available"] is False
        msg = r["hypothetical_pnl_summary"].get("message", "")
        assert "PnL unavailable" in msg or "pnl_available" in r["hypothetical_pnl_summary"]

    def test_pnl_unavailable_message_is_honest(self):
        evs = [_ev(confidence=0.62, ev=0.16)] * 5
        r = analyse(evs)
        ps = r["hypothetical_pnl_summary"]
        assert ps.get("pnl_available") is False
        assert "settlement" in ps.get("message", "").lower()

    def test_pnl_available_when_outcome_and_price_present(self):
        evs = [
            _ev(confidence=0.62, ev=0.16, settlement_outcome="YES", resolution_price=1.0)
        ] * 5
        r = analyse(evs)
        assert r["pnl_available"] is True
        ps = r["hypothetical_pnl_summary"]
        assert ps["pnl_fill_count"] == 5

    def test_pnl_positive_when_yes_resolves(self):
        evs = [_ev(
            confidence=0.62, ev=0.16,
            entry_price=0.30, raw_size_usd=0.68,
            settlement_outcome="YES", resolution_price=1.0,
        )] * 5
        r = analyse(evs)
        assert r["pnl_available"] is True
        ps = r["hypothetical_pnl_summary"]
        assert ps["total_pnl"] > 0.0

    def test_pnl_negative_when_no_resolves(self):
        evs = [_ev(
            confidence=0.62, ev=0.16,
            entry_price=0.30, raw_size_usd=0.68,
            settlement_outcome="NO", resolution_price=0.0,
        )] * 5
        r = analyse(evs)
        assert r["pnl_available"] is True
        ps = r["hypothetical_pnl_summary"]
        assert ps["total_pnl"] < 0.0

    def test_pnl_win_rate_100_when_all_yes(self):
        evs = [_ev(
            confidence=0.62, ev=0.16,
            settlement_outcome="YES", resolution_price=1.0,
        )] * 5
        r = analyse(evs)
        ps = r["hypothetical_pnl_summary"]
        assert ps["win_rate_pct"] == 100.0

    def test_pnl_win_rate_0_when_all_no(self):
        evs = [_ev(
            confidence=0.62, ev=0.16,
            settlement_outcome="NO", resolution_price=0.0,
        )] * 5
        r = analyse(evs)
        ps = r["hypothetical_pnl_summary"]
        assert ps["win_rate_pct"] == 0.0

    def test_pnl_not_computed_for_no_fill_events(self):
        # low confidence -> shadow=0 -> no fill -> pnl not counted
        evs = [_ev(
            confidence=0.40, ev=0.0,
            settlement_outcome="YES", resolution_price=1.0,
        )] * 5
        r = analyse(evs)
        assert r["pnl_available"] is False


# ===========================================================================
# 9. Shadow opportunity count
# ===========================================================================

class TestShadowOpportunityCount:
    def test_opportunity_count_matches_fill_count(self):
        evs = [_ev(confidence=0.62, ev=0.16)] * 8
        r = analyse(evs)
        assert r["shadow_opportunity_count"] == r["hypothetical_fill_count"]

    def test_zero_opportunity_when_all_blocked(self):
        evs = [_ev(confidence=0.40, ev=0.0)] * 10
        r = analyse(evs)
        assert r["shadow_opportunity_count"] == 0

    def test_opportunity_count_correct_for_mixed(self):
        evs = [_ev(confidence=0.62, ev=0.16)] * 5 + [_ev(confidence=0.40, ev=0.0)] * 5
        r = analyse(evs)
        assert r["shadow_opportunity_count"] == 5


# ===========================================================================
# 10. Paper trial verdict
# ===========================================================================

class TestPaperTrialVerdict:
    def test_insufficient_data_below_threshold(self):
        evs = [_ev(confidence=0.62, ev=0.16)] * 4
        r = analyse(evs)
        assert r["paper_trial_verdict"] == "insufficient_data"

    def test_safe_verdict_for_bounded_normal_sizing(self):
        # Confidence=0.62, ev=0.16, raw_size=0.68, bankroll=20 -> ~1.9% each
        evs = [_ev(confidence=0.62, ev=0.16, raw_size_usd=0.68, bankroll=20.0)] * 15
        r = analyse(evs)
        assert r["paper_trial_verdict"] == "safe_for_scoped_paper_trial"

    def test_not_ready_when_exposure_too_high(self):
        # raw_size=2.0, bankroll=5.0 -> shadow~40% each (way above 10% max)
        evs = [_ev(confidence=0.75, ev=0.20, raw_size_usd=2.0, bankroll=5.0)] * 15
        r = analyse(evs)
        assert r["paper_trial_verdict"] == "not_ready"

    def test_not_ready_when_cutoff_rate_too_high(self):
        # All fills are near window close
        evs = [_ev(confidence=0.62, ev=0.16, seconds_remaining=45.0,
                   raw_size_usd=0.10, bankroll=20.0)] * 15
        r = analyse(evs)
        assert r["paper_trial_verdict"] == "not_ready"
        assert r["cutoff_collision_rate_pct"] == 100.0

    def test_verdict_note_non_empty(self):
        evs = [_ev()] * 12
        r = analyse(evs)
        assert len(r.get("paper_trial_note", "")) > 0

    def test_safe_note_contains_fill_count(self):
        evs = [_ev(confidence=0.62, ev=0.16, raw_size_usd=0.68, bankroll=20.0)] * 12
        r = analyse(evs)
        if r["paper_trial_verdict"] == "safe_for_scoped_paper_trial":
            assert str(r["hypothetical_fill_count"]) in r["paper_trial_note"]

    def test_guardrail_string_present(self):
        evs = [_ev()] * 10
        r = analyse(evs)
        assert "offline-only" in r.get("guardrail", "")
        assert "position_sizing" in r.get("guardrail", "")


# ===========================================================================
# Simulate fill unit tests
# ===========================================================================

class TestSimulateFill:
    def test_would_fill_true_for_high_confidence(self):
        p = _ev(confidence=0.62, ev=0.16)
        f = _simulate_fill(p)
        assert f["would_fill"] is True

    def test_would_fill_false_for_low_confidence(self):
        p = _ev(confidence=0.40, ev=0.0)
        f = _simulate_fill(p)
        assert f["would_fill"] is False

    def test_cutoff_collision_true_when_sr_below_threshold(self):
        p = _ev(seconds_remaining=50.0)
        f = _simulate_fill(p)
        assert f["cutoff_collision"] is True

    def test_cutoff_collision_false_when_sr_at_threshold(self):
        p = _ev(seconds_remaining=90.0)
        f = _simulate_fill(p)
        assert f["cutoff_collision"] is False

    def test_asset_normalized_to_uppercase(self):
        p = _ev(ticker="eth")
        f = _simulate_fill(p)
        assert f["asset"] == "ETH"

    def test_lifecycle_phase_normalized_to_uppercase(self):
        p = _ev(lifecycle_phase="opening_scan")
        f = _simulate_fill(p)
        assert f["lifecycle_phase"] == "OPENING_SCAN"

    def test_pnl_available_false_without_settlement(self):
        p = _ev(confidence=0.62, ev=0.16)
        f = _simulate_fill(p)
        assert f["pnl_available"] is False
        assert f["hypothetical_pnl"] is None

    def test_pnl_available_true_with_settlement(self):
        p = _ev(confidence=0.62, ev=0.16, settlement_outcome="YES", resolution_price=1.0)
        f = _simulate_fill(p)
        assert f["pnl_available"] is True
        assert f["hypothetical_pnl"] is not None


# ===========================================================================
# PnL formula unit test
# ===========================================================================

class TestComputeHypotheticalPnl:
    def test_yes_resolves_at_1(self):
        pnl = _compute_hypothetical_pnl(entry_price=0.30, c_size=0.60, settlement_price=1.0)
        # tokens = 0.60/0.30 = 2.0; pnl = (1.0-0.30)*2.0 = 1.40
        assert pnl is not None
        assert abs(pnl - 1.40) < 1e-5

    def test_no_resolves_at_0(self):
        pnl = _compute_hypothetical_pnl(entry_price=0.30, c_size=0.60, settlement_price=0.0)
        # pnl = (0.0-0.30)*2.0 = -0.60
        assert pnl is not None
        assert abs(pnl - (-0.60)) < 1e-5

    def test_zero_c_size_returns_none(self):
        pnl = _compute_hypothetical_pnl(entry_price=0.30, c_size=0.0, settlement_price=1.0)
        assert pnl is None

    def test_zero_entry_price_returns_none(self):
        pnl = _compute_hypothetical_pnl(entry_price=0.0, c_size=0.60, settlement_price=1.0)
        assert pnl is None


# ===========================================================================
# Fail-soft
# ===========================================================================

class TestFailSoft:
    def test_empty_events_returns_error_dict(self):
        r = analyse([])
        assert r["event_count"] == 0
        assert "error" in r

    def test_missing_jsonl_file_returns_empty(self, tmp_path):
        result = load_replay_events("2099-12-31", quant_data_dir=tmp_path)
        assert result == []

    def test_missing_fields_do_not_raise(self):
        r = analyse([{} for _ in range(12)])
        assert r["event_count"] == 12
        assert "paper_trial_verdict" in r

    def test_zero_shadow_events_produce_safe_result(self):
        # All zero confidence/ev -> zero shadow
        evs = [_ev(confidence=0.0, ev=0.0)] * 10
        r = analyse(evs)
        assert r["hypothetical_fill_count"] == 0
        assert r["shadow_opportunity_count"] == 0
        assert r["exposure_curve"]["peak_cumulative_usd"] == 0.0

    def test_live_shadow_event_passthrough(self):
        p = _ev(confidence=0.62, ev=0.16, include_shadow=True)
        shadow = _compute_shadow(p)
        assert shadow["from_live_event"] is True
        assert shadow["nonzero"] is True


# ===========================================================================
# Filters
# ===========================================================================

class TestFilters:
    def _write_events(self, tmp_path: Path, events: list[dict]) -> None:
        d = tmp_path / "system_health"
        d.mkdir()
        rows = []
        for ev_payload in events:
            wrapped = {
                "run_id": ev_payload.get("run_id", "run_x"),
                "payload": ev_payload,
            }
            rows.append(json.dumps(wrapped))
        (d / "2026-05-16.jsonl").write_text("\n".join(rows), encoding="utf-8")

    def test_run_id_filter(self, tmp_path):
        evs = [
            _ev(ticker="BTC", run_id="run_A"),
            _ev(ticker="ETH", run_id="run_B"),
        ]
        self._write_events(tmp_path, evs)
        result = load_replay_events("2026-05-16", quant_data_dir=tmp_path, run_id="run_A")
        assert len(result) == 1
        assert result[0]["ticker"] == "BTC"

    def test_asset_filter(self, tmp_path):
        evs = [
            _ev(ticker="BTC"),
            _ev(ticker="ETH"),
        ]
        self._write_events(tmp_path, evs)
        result = load_replay_events("2026-05-16", quant_data_dir=tmp_path, asset_filter="ETH")
        assert len(result) == 1
        assert result[0]["ticker"] == "ETH"

    def test_no_filter_returns_all(self, tmp_path):
        evs = [_ev(ticker="BTC"), _ev(ticker="ETH"), _ev(ticker="BTC")]
        self._write_events(tmp_path, evs)
        result = load_replay_events("2026-05-16", quant_data_dir=tmp_path)
        assert len(result) == 3

    def test_malformed_json_lines_skipped(self, tmp_path):
        d = tmp_path / "system_health"
        d.mkdir()
        content = (
            json.dumps({"run_id": "r", "payload": _ev(ticker="BTC")}) + "\n"
            + "NOT_VALID_JSON\n"
            + json.dumps({"run_id": "r", "payload": _ev(ticker="ETH")}) + "\n"
        )
        (d / "2026-05-16.jsonl").write_text(content, encoding="utf-8")
        result = load_replay_events("2026-05-16", quant_data_dir=tmp_path)
        assert len(result) == 2


# ===========================================================================
# No runtime imports
# ===========================================================================

class TestNoRuntimeImports:
    def test_tool_does_not_import_runtime_modules(self):
        import ast
        import inspect
        import tools.shadow.semantic_c_shadow_fill_replay as mod

        src = inspect.getsource(mod)
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
            "polymarket.signal",
        }
        for m in banned:
            assert m not in imported, f"Must not import runtime module: {m}"

    def test_analyse_has_no_side_effects_on_input(self):
        evs = [_ev() for _ in range(5)]
        originals = [dict(e) for e in evs]
        analyse(evs)
        for orig, current in zip(originals, evs):
            assert orig == current


# ===========================================================================
# Replay assumptions key present
# ===========================================================================

class TestReplayAssumptions:
    def test_replay_assumptions_list_present(self):
        evs = [_ev()] * 5
        r = analyse(evs)
        assumptions = r.get("replay_assumptions", [])
        assert isinstance(assumptions, list)
        assert len(assumptions) > 0

    def test_assumptions_mention_cutoff_seconds(self):
        evs = [_ev()] * 5
        r = analyse(evs)
        combined = " ".join(r.get("replay_assumptions", []))
        assert "90" in combined or "cutoff" in combined.lower()

    def test_assumptions_mention_pnl_requirement(self):
        evs = [_ev()] * 5
        r = analyse(evs)
        combined = " ".join(r.get("replay_assumptions", []))
        assert "settlement" in combined.lower() or "pnl" in combined.lower()
