"""
Tests for Probability Semantics Calibration Probe v1.

Covers:
- win_rate_implied derivation (entry_price + ev)
- multiplier formula correctness
- four semantic alternative computations
- EV-positive / zero-multiplier detection
- mismatch count (conf_score passes, win_rate fails)
- run_id and asset filters
- lifecycle breakdown
- verdict logic
- fail-soft on empty/missing data
- no runtime module imports
- no runtime behavior change
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.probability_semantics_calibration_probe import (
    CONFIDENCE_FLOOR,
    CONFIDENCE_SPAN,
    EV_QUALITY_FLOOR,
    GOOD_EV,
    _multiplier_formula,
    _semantic_a,
    _semantic_b,
    _semantic_c,
    _semantic_d,
    analyse,
    load_calibration_events,
)


# ---------------------------------------------------------------------------
# Event fixture helpers
# ---------------------------------------------------------------------------

def _ev(
    *,
    ticker: str = "BTC",
    confidence: float = 0.60,
    entry_price: float = 0.29,
    ev: float = 0.157,
    ev_positive: bool = True,
    confidence_passed: bool = True,
    confidence_multiplier: float = 0.0,
    raw_size_usd: float = 0.68,
    blocked_reasons: list | None = None,
    lifecycle_phase: str = "ACTIVE_INVENTORY_TRADING",
    tier_id: str = "T0_MICRO_SEED",
    run_id: str = "run_test",
    micro_survival_active: bool = True,
) -> dict:
    """Build a minimal zero_size_probe_v1 payload dict."""
    return {
        "run_id": run_id,
        "payload": {
            "event": "zero_size_probe_v1",
            "ticker": ticker,
            "confidence": confidence,
            "entry_price": entry_price,
            "ev": ev,
            "ev_positive": ev_positive,
            "confidence_passed": confidence_passed,
            "confidence_multiplier": confidence_multiplier,
            "raw_size_usd": raw_size_usd,
            "blocked_reasons": blocked_reasons or ["confidence_too_low"],
            "lifecycle_phase": lifecycle_phase,
            "tier_id": tier_id,
            "micro_survival_active": micro_survival_active,
        },
    }


def _payloads(events: list[dict]) -> list[dict]:
    """Extract payload dicts (as load_calibration_events returns)."""
    return [e["payload"] for e in events]


# ===========================================================================
# 1. Multiplier formula
# ===========================================================================

class TestMultiplierFormula:
    def test_at_floor_returns_quarter(self):
        # win_rate = confidence_floor => 0.25 + 0.75 * 0 = 0.25
        assert abs(_multiplier_formula(CONFIDENCE_FLOOR) - 0.25) < 1e-6

    def test_at_ceiling_returns_one(self):
        # win_rate = confidence_ceiling => 1.0
        assert abs(_multiplier_formula(0.75) - 1.0) < 1e-6

    def test_below_floor_clamps_to_zero(self):
        # win_rate = 0.47 < 0.54
        assert _multiplier_formula(0.47) == 0.0

    def test_above_ceiling_clamps_to_one(self):
        assert _multiplier_formula(0.90) == 1.0

    def test_midpoint(self):
        # win_rate = 0.645 => (0.645-0.54)/0.21 = 0.5 => 0.25 + 0.75*0.5 = 0.625
        result = _multiplier_formula(0.645)
        assert abs(result - 0.625) < 1e-4

    def test_zero_win_rate_clamps_to_zero(self):
        assert _multiplier_formula(0.0) == 0.0


# ===========================================================================
# 2. Semantic A -- current (p_yes_implied = entry_price + ev)
# ===========================================================================

class TestSemanticA:
    def test_low_entry_plus_ev_below_floor(self):
        # 0.29 + 0.157 = 0.447 < 0.54 -> multiplier = 0
        p = {"entry_price": 0.29, "ev": 0.157}
        r = _semantic_a(p)
        assert abs(r["win_rate"] - 0.447) < 1e-4
        assert r["multiplier"] == 0.0

    def test_clamps_win_rate_to_one(self):
        p = {"entry_price": 0.90, "ev": 0.20}
        r = _semantic_a(p)
        assert r["win_rate"] == 1.0

    def test_clamps_win_rate_to_zero(self):
        p = {"entry_price": 0.0, "ev": -0.5}
        r = _semantic_a(p)
        assert r["win_rate"] == 0.0

    def test_missing_fields_default_to_zero(self):
        r = _semantic_a({})
        assert r["win_rate"] == 0.0
        assert r["multiplier"] == 0.0


# ===========================================================================
# 3. Semantic B -- confidence_score as win_rate
# ===========================================================================

class TestSemanticB:
    def test_confidence_above_floor_gives_nonzero_multiplier(self):
        p = {"confidence": 0.60, "entry_price": 0.29, "ev": 0.157}
        r = _semantic_b(p)
        assert r["win_rate"] == 0.60
        assert r["multiplier"] > 0.0

    def test_confidence_at_floor_gives_quarter(self):
        p = {"confidence": CONFIDENCE_FLOOR}
        r = _semantic_b(p)
        assert abs(r["multiplier"] - 0.25) < 1e-6

    def test_confidence_below_floor_gives_zero(self):
        p = {"confidence": 0.40}
        r = _semantic_b(p)
        assert r["multiplier"] == 0.0

    def test_confidence_at_0_60_multiplier_value(self):
        # (0.60 - 0.54) / 0.21 = 0.2857; 0.25 + 0.75*0.2857 = 0.4643
        p = {"confidence": 0.60}
        r = _semantic_b(p)
        assert abs(r["multiplier"] - 0.4643) < 0.001

    def test_missing_confidence_defaults_zero(self):
        r = _semantic_b({})
        assert r["multiplier"] == 0.0


# ===========================================================================
# 4. Semantic C -- edge-aware (confidence_score * ev_quality)
# ===========================================================================

class TestSemanticC:
    def test_high_ev_high_conf_gives_nonzero(self):
        # ev=0.157, good_ev=0.08 -> ev_quality=min(1, 0.157/0.08)=1.0
        # win_rate = 0.60 * 1.0 = 0.60 > 0.54
        p = {"confidence": 0.60, "ev": 0.157}
        r = _semantic_c(p)
        assert r["multiplier"] > 0.0

    def test_ev_quality_floor_applied(self):
        # ev=0.0 -> raw ev_quality = 0; clamped to EV_QUALITY_FLOOR=0.5
        p = {"confidence": 0.60, "ev": 0.0}
        r = _semantic_c(p)
        assert r["ev_quality"] == EV_QUALITY_FLOOR
        # win_rate = 0.60 * 0.5 = 0.30 < 0.54 -> multiplier = 0
        assert r["win_rate"] == pytest.approx(0.30, abs=1e-4)
        assert r["multiplier"] == 0.0

    def test_ev_quality_capped_at_one(self):
        # ev=0.20 >> good_ev=0.08 -> ev_quality capped at 1.0
        p = {"confidence": 0.60, "ev": 0.20}
        r = _semantic_c(p)
        assert r["ev_quality"] == 1.0

    def test_low_confidence_still_blocked(self):
        # confidence=0.40, ev_quality=1.0 -> win_rate=0.40*1.0=0.40<0.54
        p = {"confidence": 0.40, "ev": 0.20}
        r = _semantic_c(p)
        assert r["multiplier"] == 0.0

    def test_missing_fields_default(self):
        r = _semantic_c({})
        assert r["multiplier"] == 0.0


# ===========================================================================
# 5. Semantic D -- price-relative
# ===========================================================================

class TestSemanticD:
    def test_positive_ev_over_price_passes(self):
        # entry=0.29, ev=0.157 -> edge_yield=0.157/0.29=0.541
        # win_rate = 0.54 + 0.541*0.21 = 0.54 + 0.1136 = 0.6536 -> mult > 0
        p = {"entry_price": 0.29, "ev": 0.157}
        r = _semantic_d(p)
        assert r["win_rate"] > CONFIDENCE_FLOOR
        assert r["multiplier"] > 0.0

    def test_zero_ev_gives_floor_win_rate(self):
        # ev=0.0 -> win_rate = conf_floor + 0 = 0.54 -> multiplier = 0.25
        p = {"entry_price": 0.29, "ev": 0.0}
        r = _semantic_d(p)
        assert abs(r["win_rate"] - CONFIDENCE_FLOOR) < 1e-6
        assert abs(r["multiplier"] - 0.25) < 1e-6

    def test_large_edge_capped_at_ceiling(self):
        # edge_yield >> 1 -> win_rate capped at 1.0
        p = {"entry_price": 0.10, "ev": 5.0}
        r = _semantic_d(p)
        assert r["win_rate"] == 1.0

    def test_negative_ev_gives_floor_or_below(self):
        p = {"entry_price": 0.29, "ev": -0.10}
        r = _semantic_d(p)
        # Should not go negative
        assert r["win_rate"] >= 0.0


# ===========================================================================
# 6. EV-positive / zero-multiplier mismatch detection
# ===========================================================================

class TestEvPositiveZeroMultiplier:
    def test_all_ev_positive_zero_multiplier_detected(self):
        payloads = _payloads([
            _ev(ev_positive=True, confidence_multiplier=0.0),
            _ev(ev_positive=True, confidence_multiplier=0.0),
            _ev(ev_positive=False, confidence_multiplier=0.0),
        ])
        r = analyse(payloads)
        assert r["ev_pos_zero_multiplier_count"] == 2
        assert abs(r["ev_pos_zero_multiplier_pct"] - 66.7) < 0.2

    def test_no_mismatch_when_multiplier_nonzero(self):
        payloads = _payloads([_ev(ev_positive=True, confidence_multiplier=0.5)])
        r = analyse(payloads)
        assert r["ev_pos_zero_multiplier_count"] == 0


# ===========================================================================
# 7. Mismatch count (conf_score passes, win_rate fails)
# ===========================================================================

class TestMismatchCount:
    def test_mismatch_detected_when_conf_pass_wrate_fail(self):
        # confidence=0.60 (passes), entry_price+ev=0.447 (fails)
        payloads = _payloads([
            _ev(confidence=0.60, entry_price=0.29, ev=0.157,
                confidence_passed=True),
        ])
        r = analyse(payloads)
        assert r["mismatch_count"] == 1
        assert r["conf_score_passes_count"] == 1
        assert r["win_rate_fails_count"] == 1

    def test_no_mismatch_when_both_pass(self):
        # confidence=0.65 (passes), entry_price+ev=0.70 (passes)
        payloads = _payloads([
            _ev(confidence=0.65, entry_price=0.55, ev=0.15,
                confidence_passed=True),
        ])
        r = analyse(payloads)
        assert r["mismatch_count"] == 0

    def test_mismatch_pct_calculation(self):
        payloads = _payloads([
            _ev(confidence=0.60, entry_price=0.29, ev=0.157, confidence_passed=True),
            _ev(confidence=0.60, entry_price=0.29, ev=0.157, confidence_passed=True),
            _ev(confidence=0.65, entry_price=0.55, ev=0.15, confidence_passed=True),
        ])
        r = analyse(payloads)
        assert r["mismatch_count"] == 2
        assert abs(r["mismatch_pct"] - 66.7) < 0.2


# ===========================================================================
# 8. Semantic simulation -- pass/fail counts
# ===========================================================================

class TestSemanticSimulationCounts:
    def test_semantic_a_blocks_low_priced_market(self):
        # entry=0.29, ev=0.157 -> win_rate_implied=0.447 < 0.54 -> blocked
        payloads = _payloads([_ev(entry_price=0.29, ev=0.157)] * 5)
        r = analyse(payloads)
        assert r["semantic_a"]["passes"] == 0
        assert r["semantic_a"]["blocks"] == 5

    def test_semantic_b_passes_when_confidence_above_floor(self):
        # confidence=0.60 > 0.54 -> passes
        payloads = _payloads([_ev(confidence=0.60, entry_price=0.29, ev=0.157)] * 5)
        r = analyse(payloads)
        assert r["semantic_b"]["passes"] == 5

    def test_semantic_c_passes_with_high_ev(self):
        # confidence=0.60, ev=0.157, ev_quality=1.0 -> win_rate=0.60 -> passes
        payloads = _payloads([_ev(confidence=0.60, ev=0.157)] * 3)
        r = analyse(payloads)
        assert r["semantic_c"]["passes"] == 3

    def test_semantic_d_passes_with_positive_ev_ratio(self):
        # entry=0.29, ev=0.157 -> edge_yield=0.54, win_rate=0.654 -> passes
        payloads = _payloads([_ev(entry_price=0.29, ev=0.157)] * 3)
        r = analyse(payloads)
        assert r["semantic_d"]["passes"] == 3

    def test_hypothetical_size_zero_under_semantic_a(self):
        payloads = _payloads([_ev(entry_price=0.29, ev=0.157, raw_size_usd=0.68)] * 5)
        r = analyse(payloads)
        assert r["semantic_a"]["hyp_size_usd_stats"]["mean"] == 0.0

    def test_hypothetical_size_nonzero_under_semantic_b(self):
        payloads = _payloads([_ev(confidence=0.60, raw_size_usd=0.68)] * 5)
        r = analyse(payloads)
        # multiplier ≈ 0.464; size ≈ 0.68 * 0.464 ≈ 0.316
        assert r["semantic_b"]["hyp_size_usd_stats"]["mean"] > 0.0


# ===========================================================================
# 9. Asset breakdown
# ===========================================================================

class TestAssetBreakdown:
    def test_btc_eth_counted_separately(self):
        payloads = _payloads([
            _ev(ticker="BTC"),
            _ev(ticker="BTC"),
            _ev(ticker="ETH"),
        ])
        r = analyse(payloads)
        assert r["btc"]["count"] == 2
        assert r["eth"]["count"] == 1

    def test_btc_sem_b_passes_counted(self):
        payloads = _payloads([_ev(ticker="BTC", confidence=0.62)] * 3)
        r = analyse(payloads)
        assert r["btc"]["sem_b_passes"] == 3
        assert r["eth"]["count"] == 0

    def test_asset_breakdown_ev_positive(self):
        payloads = _payloads([
            _ev(ticker="BTC", ev_positive=True),
            _ev(ticker="ETH", ev_positive=False),
        ])
        r = analyse(payloads)
        assert r["btc"]["ev_positive"] == 1
        assert r["eth"]["ev_positive"] == 0


# ===========================================================================
# 10. Lifecycle phase breakdown
# ===========================================================================

class TestLifecycleBreakdown:
    def test_phase_distribution_counted(self):
        payloads = _payloads([
            _ev(lifecycle_phase="ACTIVE_INVENTORY_TRADING"),
            _ev(lifecycle_phase="ACTIVE_INVENTORY_TRADING"),
            _ev(lifecycle_phase="OPENING_SCAN"),
        ])
        r = analyse(payloads)
        dist = r["lifecycle_phase_distribution"]
        assert dist.get("ACTIVE_INVENTORY_TRADING", 0) == 2
        assert dist.get("OPENING_SCAN", 0) == 1


# ===========================================================================
# 11. Run-id and asset filters
# ===========================================================================

class TestFilters:
    def test_run_id_filter(self, tmp_path):
        events = [
            {
                "run_id": "run_A",
                "payload": {**_ev(ticker="BTC")["payload"], "event": "zero_size_probe_v1"},
            },
            {
                "run_id": "run_B",
                "payload": {**_ev(ticker="ETH")["payload"], "event": "zero_size_probe_v1"},
            },
        ]
        d = tmp_path / "system_health"
        d.mkdir()
        jf = d / "2026-05-15.jsonl"
        jf.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")

        result = load_calibration_events("2026-05-15", quant_data_dir=tmp_path, run_id="run_A")
        assert len(result) == 1
        assert result[0]["ticker"] == "BTC"

    def test_asset_filter(self, tmp_path):
        events = [
            {
                "run_id": "run_X",
                "payload": {**_ev(ticker="BTC")["payload"], "event": "zero_size_probe_v1"},
            },
            {
                "run_id": "run_X",
                "payload": {**_ev(ticker="ETH")["payload"], "event": "zero_size_probe_v1"},
            },
        ]
        d = tmp_path / "system_health"
        d.mkdir()
        jf = d / "2026-05-15.jsonl"
        jf.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")

        result = load_calibration_events("2026-05-15", quant_data_dir=tmp_path, asset_filter="ETH")
        assert len(result) == 1
        assert result[0]["ticker"] == "ETH"


# ===========================================================================
# 12. Verdict logic
# ===========================================================================

class TestVerdictLogic:
    def test_mismatch_confirmed_when_majority_mismatch(self):
        # All events: confidence=0.60 (passes), entry+ev=0.447 (fails)
        payloads = _payloads([
            _ev(confidence=0.60, entry_price=0.29, ev=0.157,
                confidence_passed=True) for _ in range(10)
        ])
        r = analyse(payloads)
        assert r["verdict"] == "semantic_mismatch_confirmed"

    def test_correct_conservative_when_no_mismatch(self):
        # All events: confidence=0.65, entry+ev=0.70 (both pass)
        payloads = _payloads([
            _ev(confidence=0.65, entry_price=0.55, ev=0.15,
                confidence_passed=True) for _ in range(10)
        ])
        r = analyse(payloads)
        assert r["verdict"] == "correct_conservative"

    def test_insufficient_evidence_for_tiny_sample(self):
        payloads = _payloads([_ev()] * 3)
        r = analyse(payloads)
        assert r["verdict"] == "insufficient_evidence"


# ===========================================================================
# 13. Fail-soft
# ===========================================================================

class TestFailSoft:
    def test_empty_events_returns_error_dict(self):
        r = analyse([])
        assert r["event_count"] == 0
        assert "error" in r
        assert "guardrail" in r

    def test_missing_fields_do_not_raise(self):
        # All fields missing from event
        r = analyse([{} for _ in range(6)])
        assert r["event_count"] == 6
        assert "verdict" in r

    def test_missing_jsonl_file_returns_empty(self, tmp_path):
        result = load_calibration_events("2099-01-01", quant_data_dir=tmp_path)
        assert result == []


# ===========================================================================
# 14. No runtime imports
# ===========================================================================

class TestNoRuntimeImports:
    def test_tool_does_not_import_trader(self):
        import ast, importlib, inspect
        import tools.probability_semantics_calibration_probe as mod
        src = inspect.getsource(mod)
        tree = ast.parse(src)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.append(node.module)
        runtime_modules = {
            "polymarket.trader", "polymarket.order_manager",
            "polymarket.position_sizing", "utils.risk_manager",
            "polymarket.bankroll_tiers",
        }
        for m in runtime_modules:
            assert m not in imported, f"Probe must not import runtime module: {m}"

    def test_analyse_has_no_side_effects(self):
        """analyse() must not modify input list."""
        payloads = _payloads([_ev()] * 5)
        original_len = len(payloads)
        original_first = dict(payloads[0])
        analyse(payloads)
        assert len(payloads) == original_len
        assert payloads[0] == original_first


# ===========================================================================
# 15. Hypothetical size stays within bankroll floor
# ===========================================================================

class TestSizeWithinBankrollFloor:
    def test_hypothetical_size_does_not_exceed_raw_size(self):
        # multiplier is at most 1.0; hyp_size <= raw_size
        payloads = _payloads([_ev(confidence=0.75, raw_size_usd=0.68)] * 5)
        r = analyse(payloads)
        assert r["semantic_b"]["hyp_size_usd_stats"]["max"] <= 0.69  # raw_size * 1.0 + float tolerance

    def test_hypothetical_size_positive_nonzero_under_b(self):
        payloads = _payloads([_ev(confidence=0.60, raw_size_usd=0.68)] * 5)
        r = analyse(payloads)
        assert r["semantic_b"]["hyp_size_usd_stats"]["mean"] > 0.0
        assert r["semantic_b"]["hyp_size_usd_stats"]["mean"] < 0.68
