"""
Tests for tools/commitment_regime_replay.py

Coverage: score formulas, no-future-leakage, threshold sweep,
precision/recall, PnL guard simulation, BTC/ETH aggregation,
verdict branches, commitment decay, false positive count, AST scan.

All tests are offline-only.  No runtime modules are imported.
"""
from __future__ import annotations

import ast
import copy
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from tools.replay.commitment_regime_replay import (
    CANDIDATE_GUARD_ACCURACY_THR,
    CANDIDATE_GUARD_PRECISION_THR,
    CONSERVATIVE_VOL_SCALE,
    CONSERVATIVE_VOL_THRESHOLD,
    ETH_ASSET_BONUS,
    FAILED_LATE_REVERSAL,
    FAILED_RESURGENCE,
    MIN_STABILIZED_FOR_VERDICT,
    N_THRESHOLD_STEPS,
    NO_STABILIZATION,
    SCORE_KEYS,
    SLOPE_SCALE,
    SURVIVED,
    VOL_PENALTY_SCALE,
    WEAK_SIGNAL_ACCURACY_THR,
    _asset_score_stats,
    _best_threshold_row,
    _classify_survival,
    _commitment_decay_summary,
    _compute_commitment_scores,
    _feature_importance_ranking,
    _score_report,
    _score_verdict,
    _simulate_guard_pnl,
    _threshold_sweep,
    analyse,
)


# ===========================================================================
# TestCommitmentScoreFormulas
# ===========================================================================

class TestCommitmentScoreFormulas:
    def _p(self, dist=0.3, slope=0.001, vol=0.03, asset="BTC", stab=True):
        return {
            "stabilization_found": stab,
            "bid_distance_from_0_5": dist if stab else None,
            "pre_stabilization_slope": slope,
            "pre_stabilization_volatility": vol,
            "asset": asset,
        }

    def test_score_a_equals_distance(self):
        scores = _compute_commitment_scores(self._p(dist=0.30))
        assert scores["distance_only_score"] == pytest.approx(0.30, rel=1e-5)

    def test_score_b_adds_slope_contribution(self):
        scores = _compute_commitment_scores(self._p(dist=0.30, slope=0.001))
        expected = 0.30 + abs(0.001) * SLOPE_SCALE
        assert scores["slope_distance_score"] == pytest.approx(expected, rel=1e-5)

    def test_score_c_subtracts_vol_penalty(self):
        scores = _compute_commitment_scores(self._p(dist=0.30, vol=0.05))
        expected = 0.30 - 0.05 * VOL_PENALTY_SCALE
        assert scores["distance_minus_vol_score"] == pytest.approx(expected, rel=1e-5)

    def test_score_d_eth_receives_bonus(self):
        scores = _compute_commitment_scores(self._p(dist=0.30, asset="ETH"))
        assert scores["asset_adjusted_commitment_score"] == pytest.approx(
            0.30 + ETH_ASSET_BONUS, rel=1e-5
        )

    def test_score_d_btc_no_bonus(self):
        scores = _compute_commitment_scores(self._p(dist=0.30, asset="BTC"))
        assert scores["asset_adjusted_commitment_score"] == pytest.approx(0.30, rel=1e-5)

    def test_score_e_no_penalty_when_vol_below_threshold(self):
        # vol=0.03 < CONSERVATIVE_VOL_THRESHOLD=0.05 → no excess penalty
        scores = _compute_commitment_scores(self._p(dist=0.30, slope=0.001, vol=0.03))
        expected = 0.30 + abs(0.001) * SLOPE_SCALE  # same as score B
        assert scores["conservative_commitment_score"] == pytest.approx(expected, rel=1e-5)

    def test_score_e_applies_excess_vol_penalty(self):
        # vol=0.10 > 0.05 → excess = (0.10-0.05)*2.0 = 0.10
        scores = _compute_commitment_scores(self._p(dist=0.30, slope=0.001, vol=0.10))
        slope_contrib = abs(0.001) * SLOPE_SCALE
        excess = max(0.0, 0.10 - CONSERVATIVE_VOL_THRESHOLD) * CONSERVATIVE_VOL_SCALE
        expected = max(0.0, 0.30 + slope_contrib - excess)
        assert scores["conservative_commitment_score"] == pytest.approx(expected, rel=1e-5)

    def test_score_e_clips_to_zero(self):
        # dist=0.05, slope=0.001, vol=0.20 → score E should be 0
        scores = _compute_commitment_scores(self._p(dist=0.05, slope=0.001, vol=0.20))
        # slope_contrib=0.20, excess=(0.20-0.05)*2.0=0.30 → 0.05+0.20-0.30=-0.05 → 0
        assert scores["conservative_commitment_score"] == pytest.approx(0.0, abs=1e-9)

    def test_none_slope_treated_as_zero(self):
        scores_none = _compute_commitment_scores(self._p(dist=0.30, slope=None, vol=0.0))
        scores_zero = _compute_commitment_scores(self._p(dist=0.30, slope=0.0, vol=0.0))
        assert scores_none["slope_distance_score"] == pytest.approx(
            scores_zero["slope_distance_score"], rel=1e-5
        )

    def test_none_vol_treated_as_zero(self):
        scores_none = _compute_commitment_scores(self._p(dist=0.30, slope=0.0, vol=None))
        scores_zero = _compute_commitment_scores(self._p(dist=0.30, slope=0.0, vol=0.0))
        assert scores_none["distance_minus_vol_score"] == pytest.approx(
            scores_zero["distance_minus_vol_score"], rel=1e-5
        )

    def test_no_stabilization_returns_all_none(self):
        scores = _compute_commitment_scores(self._p(stab=False))
        assert all(v is None for v in scores.values())

    def test_none_distance_returns_all_none(self):
        p = {"stabilization_found": True, "bid_distance_from_0_5": None,
             "pre_stabilization_slope": 0.001, "pre_stabilization_volatility": 0.02,
             "asset": "BTC"}
        scores = _compute_commitment_scores(p)
        assert all(v is None for v in scores.values())

    def test_returns_all_five_score_keys(self):
        scores = _compute_commitment_scores(self._p())
        assert set(scores.keys()) == set(SCORE_KEYS)


# ===========================================================================
# TestNoFutureLeakage
# ===========================================================================

class TestNoFutureLeakage:
    def _base(self):
        return {
            "stabilization_found": True,
            "bid_distance_from_0_5": 0.30,
            "pre_stabilization_slope": 0.001,
            "pre_stabilization_volatility": 0.02,
            "asset": "BTC",
        }

    def test_identical_features_same_scores_regardless_of_survival_label(self):
        b = self._base()
        scores_surv = _compute_commitment_scores({**b, "survival": SURVIVED})
        scores_fail = _compute_commitment_scores({**b, "survival": FAILED_RESURGENCE})
        assert scores_surv == scores_fail

    def test_commitment_decay_field_does_not_affect_scores(self):
        b = self._base()
        scores_no_decay  = _compute_commitment_scores(b)
        scores_with_decay = _compute_commitment_scores(
            {**b, "commitment_decay_after_stabilization": 0.999}
        )
        assert scores_no_decay == scores_with_decay

    def test_settlement_price_does_not_affect_scores(self):
        b = self._base()
        scores_no_sett = _compute_commitment_scores(b)
        scores_with_sett = _compute_commitment_scores(
            {**b, "settlement_price": 1.0, "settlement": "YES"}
        )
        assert scores_no_sett == scores_with_sett

    def test_post_stab_bids_not_used_as_score_input(self):
        # Survival label (derived from post-stab data) must not influence score
        b = self._base()
        for sv in [SURVIVED, FAILED_RESURGENCE, FAILED_LATE_REVERSAL, NO_STABILIZATION]:
            scores = _compute_commitment_scores({**b, "survival": sv})
            assert scores["distance_only_score"] == pytest.approx(0.30, rel=1e-5)


# ===========================================================================
# TestThresholdClassification
# ===========================================================================

class TestThresholdClassification:
    def _clean_positions(self):
        # 2 SURVIVED with high scores, 2 FAILED with low scores → perfect separation
        return [
            {"slope_distance_score": 0.80, "survival": SURVIVED,          "stabilization_found": True},
            {"slope_distance_score": 0.70, "survival": SURVIVED,          "stabilization_found": True},
            {"slope_distance_score": 0.30, "survival": FAILED_RESURGENCE, "stabilization_found": True},
            {"slope_distance_score": 0.20, "survival": FAILED_RESURGENCE, "stabilization_found": True},
        ]

    def test_sweep_has_n_threshold_steps_plus_one_rows(self):
        sweep = _threshold_sweep(self._clean_positions(), "slope_distance_score")
        assert len(sweep) == N_THRESHOLD_STEPS + 1

    def test_tp_fp_fn_tn_sum_to_total_n(self):
        sweep = _threshold_sweep(self._clean_positions(), "slope_distance_score")
        n = len(self._clean_positions())
        for row in sweep:
            assert row["tp"] + row["fp"] + row["fn"] + row["tn"] == n

    def test_perfect_separation_achieves_accuracy_one(self):
        sweep = _threshold_sweep(self._clean_positions(), "slope_distance_score")
        best = max(sweep, key=lambda r: r["accuracy"])
        assert best["accuracy"] == pytest.approx(1.0)
        assert best["fp"] == 0
        assert best["fn"] == 0

    def test_lowest_threshold_predicts_all_survived(self):
        sweep = _threshold_sweep(self._clean_positions(), "slope_distance_score")
        first = sweep[0]  # threshold = lo → all scores >= lo → all predicted SURVIVED
        assert first["fn"] == 0
        assert first["tn"] == 0
        assert first["tp"] + first["fp"] == len(self._clean_positions())

    def test_returns_empty_for_single_valid_position(self):
        positions = [{"slope_distance_score": 0.5, "survival": SURVIVED, "stabilization_found": True}]
        assert _threshold_sweep(positions, "slope_distance_score") == []

    def test_returns_empty_for_uniform_scores(self):
        positions = [
            {"slope_distance_score": 0.5, "survival": SURVIVED,          "stabilization_found": True},
            {"slope_distance_score": 0.5, "survival": FAILED_RESURGENCE, "stabilization_found": True},
        ]
        assert _threshold_sweep(positions, "slope_distance_score") == []

    def test_none_scores_excluded_from_sweep(self):
        positions = [
            {"slope_distance_score": None, "survival": SURVIVED,          "stabilization_found": True},
            {"slope_distance_score": 0.8,  "survival": SURVIVED,          "stabilization_found": True},
            {"slope_distance_score": 0.2,  "survival": FAILED_RESURGENCE, "stabilization_found": True},
        ]
        sweep = _threshold_sweep(positions, "slope_distance_score")
        # Only 2 valid positions → sweep is valid
        assert len(sweep) > 0
        for row in sweep:
            assert row["tp"] + row["fp"] + row["fn"] + row["tn"] == 2

    def test_best_threshold_row_max_f1(self):
        sweep = [
            {"f1": 0.50, "accuracy": 0.80},
            {"f1": 0.75, "accuracy": 0.70},
            {"f1": 0.60, "accuracy": 0.90},
        ]
        best = _best_threshold_row(sweep)
        assert best["f1"] == pytest.approx(0.75)

    def test_best_threshold_row_breaks_ties_by_accuracy(self):
        sweep = [
            {"f1": 0.70, "accuracy": 0.80},
            {"f1": 0.70, "accuracy": 0.90},
        ]
        best = _best_threshold_row(sweep)
        assert best["accuracy"] == pytest.approx(0.90)

    def test_best_threshold_row_none_for_empty(self):
        assert _best_threshold_row([]) is None


# ===========================================================================
# TestPrecisionRecall
# ===========================================================================

class TestPrecisionRecall:
    def _mixed_positions(self):
        return [
            {"distance_only_score": 0.90, "survival": SURVIVED,          "stabilization_found": True},
            {"distance_only_score": 0.60, "survival": FAILED_RESURGENCE, "stabilization_found": True},
            {"distance_only_score": 0.40, "survival": SURVIVED,          "stabilization_found": True},
            {"distance_only_score": 0.10, "survival": FAILED_RESURGENCE, "stabilization_found": True},
        ]

    def test_f1_derived_from_precision_and_recall(self):
        sweep = _threshold_sweep(self._mixed_positions(), "distance_only_score")
        for row in sweep:
            prec, rec = row["precision"], row["recall"]
            expected = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
            assert row["f1"] == pytest.approx(expected, abs=1e-4)

    def test_accuracy_derived_from_tp_tn_total(self):
        sweep = _threshold_sweep(self._mixed_positions(), "distance_only_score")
        for row in sweep:
            total = row["tp"] + row["fp"] + row["fn"] + row["tn"]
            expected = (row["tp"] + row["tn"]) / total if total > 0 else 0.0
            assert row["accuracy"] == pytest.approx(expected, abs=1e-4)

    def test_fpr_fnr_computed_correctly(self):
        sweep = _threshold_sweep(self._mixed_positions(), "distance_only_score")
        for row in sweep:
            fp, tn = row["fp"], row["tn"]
            fn, tp = row["fn"], row["tp"]
            expected_fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
            expected_fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
            assert row["false_positive_rate"] == pytest.approx(expected_fpr, abs=1e-4)
            assert row["false_negative_rate"] == pytest.approx(expected_fnr, abs=1e-4)

    def test_no_exception_on_all_same_survival(self):
        # All SURVIVED → fp always 0; FPR denominator = 0 → protected
        positions = [
            {"distance_only_score": 0.9, "survival": SURVIVED, "stabilization_found": True},
            {"distance_only_score": 0.7, "survival": SURVIVED, "stabilization_found": True},
            {"distance_only_score": 0.5, "survival": SURVIVED, "stabilization_found": True},
        ]
        sweep = _threshold_sweep(positions, "distance_only_score")
        for row in sweep:
            assert isinstance(row["f1"], float)
            assert isinstance(row["precision"], float)
            assert isinstance(row["false_positive_rate"], float)


# ===========================================================================
# TestPnLGuardSimulation
# ===========================================================================

class TestPnLGuardSimulation:
    def test_high_score_uses_policy_a_hold(self):
        positions = [{"slope_distance_score": 0.80, "pnl_policy_a": 5.0, "pnl_policy_b": 1.0}]
        assert _simulate_guard_pnl(positions, "slope_distance_score", 0.50) == pytest.approx(5.0)

    def test_low_score_uses_policy_b_exit(self):
        positions = [{"slope_distance_score": 0.20, "pnl_policy_a": 5.0, "pnl_policy_b": 1.0}]
        assert _simulate_guard_pnl(positions, "slope_distance_score", 0.50) == pytest.approx(1.0)

    def test_none_score_falls_back_to_policy_b(self):
        positions = [{"slope_distance_score": None, "pnl_policy_a": 5.0, "pnl_policy_b": 1.0}]
        assert _simulate_guard_pnl(positions, "slope_distance_score", 0.50) == pytest.approx(1.0)

    def test_score_equal_threshold_is_hold(self):
        # score >= threshold → HOLD
        positions = [{"slope_distance_score": 0.50, "pnl_policy_a": 3.0, "pnl_policy_b": 1.0}]
        assert _simulate_guard_pnl(positions, "slope_distance_score", 0.50) == pytest.approx(3.0)

    def test_total_pnl_summed_across_positions(self):
        positions = [
            {"slope_distance_score": 0.80, "pnl_policy_a": 5.0, "pnl_policy_b": 1.0},  # HOLD → 5
            {"slope_distance_score": 0.20, "pnl_policy_a": 5.0, "pnl_policy_b": 1.0},  # EXIT → 1
            {"slope_distance_score": None, "pnl_policy_a": 5.0, "pnl_policy_b": 2.0},  # EXIT → 2
        ]
        assert _simulate_guard_pnl(positions, "slope_distance_score", 0.50) == pytest.approx(8.0)

    def test_none_pnl_a_falls_back_to_b_when_holding(self):
        positions = [{"slope_distance_score": 0.80, "pnl_policy_a": None, "pnl_policy_b": 2.0}]
        assert _simulate_guard_pnl(positions, "slope_distance_score", 0.50) == pytest.approx(2.0)

    def test_none_pnl_b_falls_back_to_a_when_exiting(self):
        positions = [{"slope_distance_score": 0.20, "pnl_policy_a": 3.0, "pnl_policy_b": None}]
        assert _simulate_guard_pnl(positions, "slope_distance_score", 0.50) == pytest.approx(3.0)

    def test_empty_positions_returns_zero(self):
        assert _simulate_guard_pnl([], "slope_distance_score", 0.50) == pytest.approx(0.0)


# ===========================================================================
# TestBtcEthAggregation
# ===========================================================================

class TestBtcEthAggregation:
    def test_mean_score_computed_over_all_valid(self):
        positions = [
            {"slope_distance_score": 0.80, "survival": SURVIVED},
            {"slope_distance_score": 0.40, "survival": FAILED_RESURGENCE},
        ]
        stats = _asset_score_stats(positions, "slope_distance_score")
        assert stats is not None
        assert stats["mean_score"] == pytest.approx((0.80 + 0.40) / 2, rel=1e-4)

    def test_mean_survived_and_mean_failed_separated(self):
        positions = [
            {"slope_distance_score": 0.90, "survival": SURVIVED},
            {"slope_distance_score": 0.70, "survival": SURVIVED},
            {"slope_distance_score": 0.30, "survival": FAILED_RESURGENCE},
            {"slope_distance_score": 0.10, "survival": FAILED_LATE_REVERSAL},
        ]
        stats = _asset_score_stats(positions, "slope_distance_score")
        assert stats["mean_survived"] == pytest.approx((0.90 + 0.70) / 2)
        assert stats["mean_failed"] == pytest.approx((0.30 + 0.10) / 2)

    def test_returns_none_when_all_scores_none(self):
        positions = [{"slope_distance_score": None, "survival": SURVIVED}]
        assert _asset_score_stats(positions, "slope_distance_score") is None

    def test_no_survived_gives_none_mean_survived(self):
        positions = [{"slope_distance_score": 0.50, "survival": FAILED_RESURGENCE}]
        stats = _asset_score_stats(positions, "slope_distance_score")
        assert stats["mean_survived"] is None

    def test_no_failed_gives_none_mean_failed(self):
        positions = [{"slope_distance_score": 0.50, "survival": SURVIVED}]
        stats = _asset_score_stats(positions, "slope_distance_score")
        assert stats["mean_failed"] is None

    def test_count_matches_non_none_scores(self):
        positions = [
            {"slope_distance_score": 0.80, "survival": SURVIVED},
            {"slope_distance_score": None, "survival": SURVIVED},
            {"slope_distance_score": 0.30, "survival": FAILED_RESURGENCE},
        ]
        stats = _asset_score_stats(positions, "slope_distance_score")
        assert stats["count"] == 2


# ===========================================================================
# TestVerdictBranches
# ===========================================================================

class TestVerdictBranches:
    def _row(self, acc, prec, rec):
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        return {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1}

    def test_candidate_guard_all_conditions_met(self):
        # acc >= 0.60, prec >= 0.45, uplift > 0
        verdict, _ = _score_verdict(self._row(0.65, 0.50, 0.60), uplift_vs_b=1.0, n_stab=15)
        assert verdict == "candidate_guard"

    def test_candidate_guard_requires_positive_uplift(self):
        verdict, _ = _score_verdict(self._row(0.65, 0.50, 0.60), uplift_vs_b=0.0, n_stab=15)
        assert verdict != "candidate_guard"

    def test_overfit_risk_high_acc_low_recall(self):
        # acc >= 0.60 but rec < 0.30 and uplift <= 0
        verdict, _ = _score_verdict(self._row(0.65, 0.80, 0.20), uplift_vs_b=-1.0, n_stab=15)
        assert verdict == "overfit_risk"

    def test_weak_signal_low_accuracy(self):
        # acc < 0.55
        verdict, _ = _score_verdict(self._row(0.50, 0.40, 0.50), uplift_vs_b=0.0, n_stab=15)
        assert verdict == "weak_signal"

    def test_needs_more_data_insufficient_epochs(self):
        # n_stab < MIN_STABILIZED_FOR_VERDICT
        verdict, _ = _score_verdict(self._row(0.70, 0.60, 0.70), uplift_vs_b=5.0, n_stab=5)
        assert verdict == "needs_more_data"

    def test_needs_more_data_borderline_accuracy(self):
        # acc between 0.55 and 0.60 → candidate_guard threshold not met, weak_signal not met
        verdict, _ = _score_verdict(self._row(0.57, 0.48, 0.55), uplift_vs_b=1.0, n_stab=15)
        assert verdict == "needs_more_data"

    def test_all_four_verdict_strings_reachable(self):
        verdicts = set()
        verdicts.add(_score_verdict(self._row(0.65, 0.50, 0.60), 1.0, 15)[0])   # candidate_guard
        verdicts.add(_score_verdict(self._row(0.65, 0.80, 0.20), -1.0, 15)[0])  # overfit_risk
        verdicts.add(_score_verdict(self._row(0.50, 0.40, 0.50), 0.0, 15)[0])   # weak_signal
        verdicts.add(_score_verdict(self._row(0.70, 0.60, 0.70), 5.0, 5)[0])    # needs_more_data
        assert verdicts == {"candidate_guard", "overfit_risk", "weak_signal", "needs_more_data"}

    def test_verdict_note_is_nonempty_string(self):
        for row, uplift, n in [
            (self._row(0.65, 0.50, 0.60), 1.0, 15),
            (self._row(0.65, 0.80, 0.20), -1.0, 15),
            (self._row(0.50, 0.40, 0.50), 0.0, 15),
            (self._row(0.70, 0.60, 0.70), 5.0, 5),
        ]:
            _, note = _score_verdict(row, uplift, n)
            assert isinstance(note, str) and len(note) > 0


# ===========================================================================
# TestCommitmentDecay
# ===========================================================================

class TestCommitmentDecay:
    """
    _classify_survival computes commitment_decay_after_stabilization:
      stab_dist - min(abs(yb - 0.5) for post-stab bids)
    Positive = bid moved toward midpoint.  None when no post-stab snaps.
    """

    def test_decay_zero_when_post_stab_stays_at_stab_level(self):
        # stab at SR=100, bid=0.85; all post-stab bids also 0.85
        stab = {"stabilization_sr": 100.0, "stabilization_bid_level": 0.85,
                "vol_at_stabilization": 0.0, "n_stable_snaps": 3}
        timeline = [(150, 0.85), (100, 0.85), (80, 0.85), (60, 0.85)]
        result = _classify_survival(timeline, stab)
        # stab_dist=0.35; post_stab bids=[0.85,0.85]; min_post_dist=0.35; decay=0.0
        assert result["commitment_decay_after_stabilization"] == pytest.approx(0.0, abs=1e-6)

    def test_decay_positive_when_bid_drifts_toward_midpoint(self):
        # stab at SR=100, bid=0.85; post-stab drifts toward 0.55
        stab = {"stabilization_sr": 100.0, "stabilization_bid_level": 0.85,
                "vol_at_stabilization": 0.0, "n_stable_snaps": 3}
        timeline = [(150, 0.85), (100, 0.85), (80, 0.70), (60, 0.60), (40, 0.55)]
        result = _classify_survival(timeline, stab)
        # post_stab = [(80,0.70),(60,0.60),(40,0.55)]
        # stab_dist=0.35; min_post_dist=abs(0.55-0.5)=0.05; decay=0.30
        assert result["commitment_decay_after_stabilization"] == pytest.approx(0.30, abs=1e-5)

    def test_decay_none_when_no_post_stab_snapshots(self):
        # stab_sr=50; all timeline snaps have sr >= 50 → no post-stab data
        stab = {"stabilization_sr": 50.0, "stabilization_bid_level": 0.85,
                "vol_at_stabilization": 0.0, "n_stable_snaps": 3}
        timeline = [(150, 0.85), (100, 0.85), (50, 0.85)]
        result = _classify_survival(timeline, stab)
        assert result["commitment_decay_after_stabilization"] is None

    def test_decay_key_present_in_classify_survival_result(self):
        stab = {"stabilization_sr": 100.0, "stabilization_bid_level": 0.85,
                "vol_at_stabilization": 0.0, "n_stable_snaps": 3}
        timeline = [(150, 0.85), (100, 0.85), (80, 0.85)]
        result = _classify_survival(timeline, stab)
        assert "commitment_decay_after_stabilization" in result

    def test_decay_summary_survived_lower_mean_than_failed(self):
        positions = [
            {"survival": SURVIVED,          "stabilization_found": True, "commitment_decay_after_stabilization": 0.02},
            {"survival": SURVIVED,          "stabilization_found": True, "commitment_decay_after_stabilization": 0.03},
            {"survival": FAILED_RESURGENCE, "stabilization_found": True, "commitment_decay_after_stabilization": 0.25},
            {"survival": FAILED_RESURGENCE, "stabilization_found": True, "commitment_decay_after_stabilization": 0.35},
        ]
        summary = _commitment_decay_summary(positions)
        assert summary["survived"]["mean"] < summary["failed_resurgence"]["mean"]

    def test_decay_summary_none_values_excluded_from_stats(self):
        positions = [
            {"survival": SURVIVED, "stabilization_found": True, "commitment_decay_after_stabilization": None},
            {"survival": SURVIVED, "stabilization_found": True, "commitment_decay_after_stabilization": 0.05},
        ]
        summary = _commitment_decay_summary(positions)
        assert summary["survived"]["count"] == 1
        assert summary["survived"]["mean"] == pytest.approx(0.05)

    def test_decay_summary_diagnostic_note_present(self):
        summary = _commitment_decay_summary([])
        assert "diagnostic_note" in summary
        assert "diagnostic" in summary["diagnostic_note"].lower()


# ===========================================================================
# TestHighCommitmentFalsePositiveCount
# ===========================================================================

class TestHighCommitmentFalsePositiveCount:
    def _positions(self, n_surv=3, n_fail=7):
        # SURVIVED: high scores (clearly above FAILED scores)
        positions = []
        for i in range(n_surv):
            score = 0.80 - i * 0.05
            positions.append({
                "distance_only_score": score,
                "survival": SURVIVED,
                "stabilization_found": True,
                "asset": "BTC",
                "pnl_policy_a": 1.0,
                "pnl_policy_b": 0.5,
            })
        for i in range(n_fail):
            score = 0.40 - i * 0.03
            positions.append({
                "distance_only_score": score,
                "survival": FAILED_RESURGENCE,
                "stabilization_found": True,
                "asset": "BTC",
                "pnl_policy_a": -1.0,
                "pnl_policy_b": 0.5,
            })
        return positions

    def test_fp_count_matches_best_row_fp_in_sweep(self):
        positions = self._positions()
        report = _score_report(positions, "distance_only_score", baseline_a=0.0, baseline_b=0.0)
        sweep  = _threshold_sweep(positions, "distance_only_score")
        best   = _best_threshold_row(sweep)
        assert report["high_commitment_false_positive_count"] == best["fp"]

    def test_fp_count_is_non_negative_integer(self):
        report = _score_report(self._positions(), "distance_only_score", 0.0, 0.0)
        fp = report["high_commitment_false_positive_count"]
        assert isinstance(fp, int)
        assert fp >= 0

    def test_fp_count_key_present_in_report(self):
        report = _score_report(self._positions(), "distance_only_score", 0.0, 0.0)
        assert "high_commitment_false_positive_count" in report

    def test_perfect_separation_gives_fp_zero(self):
        # Survived scores all > max failed score → best threshold gives FP=0
        positions = self._positions(n_surv=3, n_fail=7)
        report = _score_report(positions, "distance_only_score", 0.0, 0.0)
        assert report["high_commitment_false_positive_count"] == 0

    def test_pnl_uplift_present_in_report(self):
        report = _score_report(self._positions(), "distance_only_score", 0.0, 0.0)
        assert "pnl_uplift_vs_fixed_derisk" in report
        assert "pnl_guarded" in report


# ===========================================================================
# TestNoRuntimeImportASTScan
# ===========================================================================

class TestNoRuntimeImportASTScan:
    TOOL_PATH = _REPO / "tools" / "replay" / "commitment_regime_replay.py"
    RUNTIME_MODULES = frozenset({
        "polymarket", "utils", "config", "main",
        "trader", "risk_manager", "order_manager",
        "position_sizing", "virtual_ptb", "signal",
        "bankroll_tiers", "gamma_fetcher", "market_feed",
        "probability_model", "expected_value", "regime_diagnostics",
        "realtime_logger", "quant_event_logger", "telegram_alerts",
    })

    def test_tool_file_exists(self):
        assert self.TOOL_PATH.exists(), f"Tool file not found: {self.TOOL_PATH}"

    def test_no_runtime_imports(self):
        source = self.TOOL_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top not in self.RUNTIME_MODULES, (
                        f"Forbidden runtime import: import {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                assert top not in self.RUNTIME_MODULES, (
                    f"Forbidden runtime import: from {node.module} ..."
                )

    def test_no_tools_imports_from_other_tools(self):
        source = self.TOOL_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("tools."), (
                    f"Tool must not import from other tools: from {node.module}"
                )


# ===========================================================================
# TestNoSideEffects
# ===========================================================================

class TestNoSideEffects:
    def test_analyse_empty_events_returns_error_key(self):
        result = analyse([], {}, {})
        assert "error" in result

    def test_analyse_returns_guardrail_key(self):
        result = analyse([], {}, {})
        assert "guardrail" in result
        assert "offline" in result["guardrail"].lower()

    def test_compute_scores_does_not_mutate_input(self):
        p = {"stabilization_found": True, "bid_distance_from_0_5": 0.30,
             "pre_stabilization_slope": 0.001, "pre_stabilization_volatility": 0.02,
             "asset": "BTC"}
        original = dict(p)
        _compute_commitment_scores(p)
        assert p == original

    def test_threshold_sweep_does_not_mutate_positions(self):
        positions = [
            {"distance_only_score": 0.80, "survival": SURVIVED,          "stabilization_found": True},
            {"distance_only_score": 0.20, "survival": FAILED_RESURGENCE, "stabilization_found": True},
        ]
        original = copy.deepcopy(positions)
        _threshold_sweep(positions, "distance_only_score")
        assert positions == original

    def test_feature_importance_excludes_commitment_decay(self):
        survived_feat = {
            "survival": SURVIVED, "stabilization_found": True,
            "bid_distance_from_0_5": 0.30, "pre_stabilization_slope": 0.001,
            "pre_stabilization_volatility": 0.02, "stabilization_bid_level": 0.80,
            "bid_stability_score": 0.025, "stable_streak_length": 3,
            "stabilization_sr": 100.0, "shadow_pct_bankroll": 2.0, "entry_price": 0.6,
            "commitment_decay_after_stabilization": 0.99,  # diagnostic; must be excluded
        }
        failed_feat = {
            "survival": FAILED_RESURGENCE, "stabilization_found": True,
            "bid_distance_from_0_5": 0.10, "pre_stabilization_slope": 0.0001,
            "pre_stabilization_volatility": 0.05, "stabilization_bid_level": 0.60,
            "bid_stability_score": 0.083, "stable_streak_length": 3,
            "stabilization_sr": 90.0, "shadow_pct_bankroll": 1.5, "entry_price": 0.55,
            "commitment_decay_after_stabilization": 0.01,
        }
        rankings = _feature_importance_ranking([survived_feat, failed_feat])
        feature_names = [r["feature"] for r in rankings]
        assert "commitment_decay_after_stabilization" not in feature_names

    def test_simulate_guard_pnl_does_not_mutate_positions(self):
        positions = [
            {"slope_distance_score": 0.80, "pnl_policy_a": 2.0, "pnl_policy_b": 1.0},
        ]
        original = copy.deepcopy(positions)
        _simulate_guard_pnl(positions, "slope_distance_score", 0.50)
        assert positions == original
