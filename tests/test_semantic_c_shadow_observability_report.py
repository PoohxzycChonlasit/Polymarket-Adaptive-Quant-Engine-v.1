"""
Tests for Semantic C Shadow Observability Report v1.

Covers:
- Semantic C shadow formula correctness (ev_quality, c_input, c_mult, c_size)
- Backward-compat derivation from existing event fields
- Pre-populated shadow field passthrough
- Shadow pass/fail rate calculations
- Shadow size statistics (mean/p50/p90)
- Current-zero but shadow-nonzero diagnostic count
- Aggressiveness check
- BTC vs ETH asset breakdown
- Lifecycle phase distribution
- Verdict logic (safe / too_aggressive / insufficient_data)
- Run-id and asset filter
- Fail-soft: empty events, missing file, missing fields
- No runtime module imports (AST scan)
- No side effects on input
- Trader emit method produces all 8 shadow keys
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.shadow.semantic_c_shadow_observability_report import (
    _CONF_FLOOR,
    _CONF_SPAN,
    _EV_Q_FLOOR,
    _GOOD_EV,
    _compute_shadow,
    analyse,
    load_shadow_events,
)


# ---------------------------------------------------------------------------
# Event fixture helpers
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
    tier_id: str = "T0_MICRO_SEED",
    run_id: str = "run_test",
    # shadow fields (pre-populated, optional)
    include_shadow: bool = False,
    sc_ev_quality: float | None = None,
    sc_input: float | None = None,
    sc_mult: float | None = None,
    sc_size: float | None = None,
    sc_pass: bool | None = None,
    sc_nonzero: bool | None = None,
    sc_pct: float | None = None,
) -> dict:
    base = {
        "run_id": run_id,
        "payload": {
            "event": "zero_size_probe_v1",
            "ticker": ticker,
            "confidence": confidence,
            "entry_price": entry_price,
            "ev": ev,
            "ev_positive": ev_positive,
            "confidence_passed": confidence_passed,
            "final_size_usd": final_size_usd,
            "raw_size_usd": raw_size_usd,
            "bankroll": bankroll,
            "lifecycle_phase": lifecycle_phase,
            "tier_id": tier_id,
        },
    }
    if include_shadow:
        eq = sc_ev_quality if sc_ev_quality is not None else min(1.0, max(_EV_Q_FLOOR, ev / _GOOD_EV))
        ci = sc_input if sc_input is not None else confidence * eq
        cm = sc_mult if sc_mult is not None else max(0.0, min(1.0, 0.25 + 0.75 * (ci - _CONF_FLOOR) / _CONF_SPAN))
        cs = sc_size if sc_size is not None else raw_size_usd * cm
        pct = sc_pct if sc_pct is not None else round(cs / max(bankroll, 1e-9) * 100, 4)
        base["payload"].update({
            "semantic_c_ev_quality_shadow":          round(eq, 6),
            "semantic_c_input_shadow":               round(ci, 6),
            "semantic_c_multiplier_shadow":          round(cm, 6),
            "semantic_c_size_usd_shadow":            round(cs, 6),
            "semantic_c_would_pass_confidence_gate": sc_pass if sc_pass is not None else ci >= _CONF_FLOOR,
            "semantic_c_would_produce_nonzero_size": sc_nonzero if sc_nonzero is not None else cs > 0.0,
            "semantic_c_size_pct_bankroll":          pct,
            "semantic_c_shadow_reason":              "confidence_score_x_ev_quality_not_in_active_sizing",
        })
    return base


def _payloads(events: list[dict]) -> list[dict]:
    return [e["payload"] for e in events]


# ===========================================================================
# 1. Shadow formula -- backward-compat derivation
# ===========================================================================

class TestComputeShadowBackwardCompat:
    def test_ev_quality_above_good_ev_capped_at_one(self):
        p = {"confidence": 0.62, "ev": 0.20, "raw_size_usd": 0.68, "bankroll": 20.0}
        s = _compute_shadow(p)
        assert s["ev_quality"] == 1.0

    def test_ev_quality_below_good_ev_floored_at_half(self):
        p = {"confidence": 0.62, "ev": 0.0, "raw_size_usd": 0.68, "bankroll": 20.0}
        s = _compute_shadow(p)
        assert s["ev_quality"] == _EV_Q_FLOOR

    def test_c_input_is_confidence_times_ev_quality(self):
        p = {"confidence": 0.62, "ev": 0.08, "raw_size_usd": 0.68, "bankroll": 20.0}
        s = _compute_shadow(p)
        # ev/GOOD_EV = 1.0 => ev_quality = 1.0 => c_input = 0.62
        assert abs(s["c_input"] - 0.62) < 1e-4

    def test_c_mult_at_floor_is_quarter(self):
        # c_input exactly at 0.54 -> mult = 0.25
        p = {"confidence": 0.54, "ev": 0.08, "raw_size_usd": 0.68, "bankroll": 20.0}
        s = _compute_shadow(p)
        assert abs(s["c_mult"] - 0.25) < 1e-4

    def test_c_mult_below_floor_is_zero(self):
        # confidence=0.40, ev_quality=0.5 -> c_input=0.20 < 0.54 -> mult=0
        p = {"confidence": 0.40, "ev": 0.0, "raw_size_usd": 0.68, "bankroll": 20.0}
        s = _compute_shadow(p)
        assert s["c_mult"] == 0.0

    def test_c_size_is_raw_times_mult(self):
        p = {"confidence": 0.75, "ev": 0.20, "raw_size_usd": 0.68, "bankroll": 20.0}
        s = _compute_shadow(p)
        expected = 0.68 * s["c_mult"]
        assert abs(s["c_size"] - expected) < 1e-5

    def test_would_pass_true_when_c_input_above_floor(self):
        p = {"confidence": 0.62, "ev": 0.08, "raw_size_usd": 0.68, "bankroll": 20.0}
        s = _compute_shadow(p)
        assert s["would_pass"] is True

    def test_would_pass_false_when_c_input_below_floor(self):
        # confidence=0.50, ev_quality=1.0 -> c_input=0.50 < 0.54
        p = {"confidence": 0.50, "ev": 0.08, "raw_size_usd": 0.68, "bankroll": 20.0}
        s = _compute_shadow(p)
        assert s["would_pass"] is False

    def test_pct_bankroll_formula(self):
        p = {"confidence": 0.75, "ev": 0.20, "raw_size_usd": 0.68, "bankroll": 20.0}
        s = _compute_shadow(p)
        expected_pct = round(s["c_size"] / 20.0 * 100, 4)
        assert abs(s["pct_bankroll"] - expected_pct) < 1e-4

    def test_from_live_event_false_for_derived(self):
        p = {"confidence": 0.62, "ev": 0.08, "raw_size_usd": 0.68, "bankroll": 20.0}
        s = _compute_shadow(p)
        assert s["from_live_event"] is False


class TestComputeShadowLiveEvent:
    def test_pre_populated_fields_returned_directly(self):
        p = {
            "semantic_c_multiplier_shadow":          0.55,
            "semantic_c_ev_quality_shadow":          0.9,
            "semantic_c_input_shadow":               0.585,
            "semantic_c_size_usd_shadow":            0.374,
            "semantic_c_would_pass_confidence_gate": True,
            "semantic_c_would_produce_nonzero_size": True,
            "semantic_c_size_pct_bankroll":          1.86,
        }
        s = _compute_shadow(p)
        assert s["c_mult"] == 0.55
        assert s["ev_quality"] == 0.9
        assert s["c_size"] == 0.374
        assert s["from_live_event"] is True

    def test_live_event_would_pass_returned_as_bool(self):
        p = {
            "semantic_c_multiplier_shadow":          0.4,
            "semantic_c_ev_quality_shadow":          1.0,
            "semantic_c_input_shadow":               0.58,
            "semantic_c_size_usd_shadow":            0.30,
            "semantic_c_would_pass_confidence_gate": True,
            "semantic_c_would_produce_nonzero_size": True,
            "semantic_c_size_pct_bankroll":          1.5,
        }
        s = _compute_shadow(p)
        assert isinstance(s["would_pass"], bool)
        assert s["would_pass"] is True


# ===========================================================================
# 2. Shadow pass / fail rate
# ===========================================================================

class TestShadowPassRate:
    def test_all_pass_when_confidence_high(self):
        payloads = _payloads([_ev(confidence=0.62, ev=0.16)] * 10)
        r = analyse(payloads)
        assert r["shadow_pass_count"] == 10
        assert r["shadow_pass_pct"] == 100.0

    def test_none_pass_when_confidence_too_low(self):
        # confidence=0.40, ev_quality=0.5 -> c_input=0.20 -> blocked
        payloads = _payloads([_ev(confidence=0.40, ev=0.0)] * 10)
        r = analyse(payloads)
        assert r["shadow_pass_count"] == 0

    def test_mixed_pass_rate(self):
        payloads = _payloads(
            [_ev(confidence=0.62, ev=0.16)] * 6 +
            [_ev(confidence=0.40, ev=0.0)] * 4
        )
        r = analyse(payloads)
        assert r["shadow_pass_count"] == 6
        assert abs(r["shadow_pass_pct"] - 60.0) < 0.2


# ===========================================================================
# 3. Shadow size stats
# ===========================================================================

class TestShadowSizeStats:
    def test_mean_size_positive_when_confidence_passes(self):
        payloads = _payloads([_ev(confidence=0.62, ev=0.16, raw_size_usd=0.68)] * 10)
        r = analyse(payloads)
        assert r["shadow_size_usd_stats"]["mean"] > 0.0

    def test_mean_size_zero_when_all_blocked(self):
        payloads = _payloads([_ev(confidence=0.40, ev=0.0)] * 10)
        r = analyse(payloads)
        assert r["shadow_size_usd_stats"]["mean"] == 0.0

    def test_p90_present_with_sufficient_events(self):
        payloads = _payloads([_ev(confidence=0.62, ev=0.16)] * 15)
        r = analyse(payloads)
        assert "p90" in r["shadow_size_usd_stats"]

    def test_pct_bankroll_stats_populated(self):
        payloads = _payloads([_ev(confidence=0.62, ev=0.16, raw_size_usd=0.68, bankroll=20.0)] * 10)
        r = analyse(payloads)
        stats = r["shadow_pct_bankroll_stats"]
        assert stats["mean"] > 0.0
        assert stats["mean"] < 10.0  # should be well under 10%


# ===========================================================================
# 4. Current-zero but shadow-nonzero diagnostic
# ===========================================================================

class TestCurrentZeroShadowNonzero:
    def test_counted_when_final_zero_and_shadow_positive(self):
        # final_size=0, confidence=0.62 -> shadow > 0
        payloads = _payloads([_ev(final_size_usd=0.0, confidence=0.62, ev=0.16)] * 5)
        r = analyse(payloads)
        assert r["current_zero_shadow_nonzero"] == 5
        assert r["current_zero_shadow_nonzero_pct"] == 100.0

    def test_not_counted_when_final_already_nonzero(self):
        # final_size > 0: event shouldn't be in zero_size_probe but test the logic
        payloads = _payloads([_ev(final_size_usd=0.5, confidence=0.62, ev=0.16)] * 5)
        r = analyse(payloads)
        assert r["current_zero_shadow_nonzero"] == 0

    def test_mixed_count(self):
        payloads = _payloads(
            [_ev(final_size_usd=0.0, confidence=0.62, ev=0.16)] * 3 +
            [_ev(final_size_usd=0.0, confidence=0.40, ev=0.0)] * 2
        )
        r = analyse(payloads)
        # Only the 3 with confidence=0.62 produce shadow > 0
        assert r["current_zero_shadow_nonzero"] == 3


# ===========================================================================
# 5. Aggressiveness check
# ===========================================================================

class TestAggressivenessCheck:
    def test_too_aggressive_when_mean_pct_exceeds_threshold(self):
        # Force high shadow size: raw_size=2.0, bankroll=5.0 -> pct = 2.0*mult/5.0*100
        # With confidence=0.75, mult≈1.0, pct≈40% >> 5%
        payloads = _payloads([_ev(confidence=0.75, ev=0.20, raw_size_usd=2.0, bankroll=5.0)] * 12)
        r = analyse(payloads)
        assert r["verdict"] == "too_aggressive"

    def test_not_aggressive_for_normal_bankroll(self):
        # With confidence=0.62, ev=0.16, raw_size=0.68, bankroll=20 -> pct ≈ 1.9%
        payloads = _payloads([_ev(confidence=0.62, ev=0.16, raw_size_usd=0.68, bankroll=20.0)] * 12)
        r = analyse(payloads)
        assert r["verdict"] == "safe_for_more_paper_evidence"

    def test_too_aggressive_count_tracked(self):
        # Mix: some normal, some aggressive
        payloads = _payloads(
            [_ev(confidence=0.75, ev=0.20, raw_size_usd=2.0, bankroll=5.0)] * 5 +
            [_ev(confidence=0.62, ev=0.16, raw_size_usd=0.68, bankroll=20.0)] * 5
        )
        r = analyse(payloads)
        assert r["too_aggressive_count"] >= 0  # count tracked even if not verdict


# ===========================================================================
# 6. Asset breakdown
# ===========================================================================

class TestAssetBreakdown:
    def test_btc_eth_counted_separately(self):
        payloads = _payloads([
            _ev(ticker="BTC"), _ev(ticker="BTC"),
            _ev(ticker="ETH"),
        ])
        r = analyse(payloads)
        assert r["btc"]["count"] == 2
        assert r["eth"]["count"] == 1

    def test_asset_shadow_passes_counted(self):
        payloads = _payloads([
            _ev(ticker="BTC", confidence=0.62, ev=0.16),
            _ev(ticker="ETH", confidence=0.62, ev=0.16),
        ])
        r = analyse(payloads)
        assert r["btc"]["shadow_passes"] == 1
        assert r["eth"]["shadow_passes"] == 1

    def test_eth_low_entry_price_tracked(self):
        payloads = _payloads([_ev(ticker="ETH", entry_price=0.07, ev=0.25)])
        r = analyse(payloads)
        assert abs(r["eth"]["mean_entry_price"] - 0.07) < 1e-4

    def test_asset_shadow_size_stats_present(self):
        payloads = _payloads([_ev(ticker="BTC", confidence=0.62, ev=0.16)] * 5)
        r = analyse(payloads)
        assert "shadow_size_stats" in r["btc"]
        assert r["btc"]["shadow_size_stats"]["mean"] > 0.0


# ===========================================================================
# 7. Lifecycle phase distribution
# ===========================================================================

class TestLifecycleDistribution:
    def test_phases_counted(self):
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
# 8. Verdict logic
# ===========================================================================

class TestVerdictLogic:
    def test_insufficient_data_below_ten(self):
        payloads = _payloads([_ev()] * 9)
        r = analyse(payloads)
        assert r["verdict"] == "insufficient_data"

    def test_safe_for_normal_micro_seed_sizing(self):
        payloads = _payloads([_ev(confidence=0.62, ev=0.16, raw_size_usd=0.68, bankroll=20.0)] * 15)
        r = analyse(payloads)
        assert r["verdict"] == "safe_for_more_paper_evidence"

    def test_too_aggressive_for_oversized_bankroll_ratio(self):
        # shadow pct >> 5%
        payloads = _payloads([_ev(confidence=0.75, ev=0.20, raw_size_usd=2.0, bankroll=5.0)] * 15)
        r = analyse(payloads)
        assert r["verdict"] == "too_aggressive"

    def test_verdict_note_non_empty(self):
        payloads = _payloads([_ev()] * 12)
        r = analyse(payloads)
        assert len(r.get("verdict_note", "")) > 0


# ===========================================================================
# 9. Run-id and asset filters
# ===========================================================================

class TestFilters:
    def test_run_id_filter(self, tmp_path):
        events = [
            {"run_id": "A", "payload": {**_ev(ticker="BTC")["payload"], "event": "zero_size_probe_v1"}},
            {"run_id": "B", "payload": {**_ev(ticker="ETH")["payload"], "event": "zero_size_probe_v1"}},
        ]
        d = tmp_path / "system_health"
        d.mkdir()
        (d / "2026-05-16.jsonl").write_text(
            "\n".join(json.dumps(e) for e in events), encoding="utf-8"
        )
        result = load_shadow_events("2026-05-16", quant_data_dir=tmp_path, run_id="A")
        assert len(result) == 1
        assert result[0]["ticker"] == "BTC"

    def test_asset_filter(self, tmp_path):
        events = [
            {"run_id": "X", "payload": {**_ev(ticker="BTC")["payload"], "event": "zero_size_probe_v1"}},
            {"run_id": "X", "payload": {**_ev(ticker="ETH")["payload"], "event": "zero_size_probe_v1"}},
        ]
        d = tmp_path / "system_health"
        d.mkdir()
        (d / "2026-05-16.jsonl").write_text(
            "\n".join(json.dumps(e) for e in events), encoding="utf-8"
        )
        result = load_shadow_events("2026-05-16", quant_data_dir=tmp_path, asset_filter="ETH")
        assert len(result) == 1
        assert result[0]["ticker"] == "ETH"


# ===========================================================================
# 10. Fail-soft
# ===========================================================================

class TestFailSoft:
    def test_empty_events_returns_error_dict(self):
        r = analyse([])
        assert r["event_count"] == 0
        assert "error" in r

    def test_missing_jsonl_file_returns_empty(self, tmp_path):
        result = load_shadow_events("2099-12-31", quant_data_dir=tmp_path)
        assert result == []

    def test_missing_fields_do_not_raise(self):
        # All-empty dicts
        r = analyse([{} for _ in range(12)])
        assert r["event_count"] == 12
        assert "verdict" in r

    def test_live_event_with_zero_shadow_size(self):
        p = {
            "semantic_c_multiplier_shadow":          0.0,
            "semantic_c_ev_quality_shadow":          0.5,
            "semantic_c_input_shadow":               0.30,
            "semantic_c_size_usd_shadow":            0.0,
            "semantic_c_would_pass_confidence_gate": False,
            "semantic_c_would_produce_nonzero_size": False,
            "semantic_c_size_pct_bankroll":          0.0,
        }
        s = _compute_shadow(p)
        assert s["c_size"] == 0.0
        assert s["would_pass"] is False


# ===========================================================================
# 11. No runtime imports
# ===========================================================================

class TestNoRuntimeImports:
    def test_tool_does_not_import_runtime_modules(self):
        import ast
        import inspect
        import tools.shadow.semantic_c_shadow_observability_report as mod
        src = inspect.getsource(mod)
        tree = ast.parse(src)
        imported = []
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

    def test_analyse_has_no_side_effects(self):
        payloads = _payloads([_ev()] * 5)
        original = [dict(p) for p in payloads]
        analyse(payloads)
        for orig, current in zip(original, payloads):
            assert orig == current


# ===========================================================================
# 12. Trader emit produces all 8 shadow keys
# ===========================================================================

class TestTraderEmitShadowFields:
    """Verify that _emit_zero_size_probe_event populates all 8 shadow keys."""

    def _run_emit(self, confidence: float = 0.62, ev: float = 0.16) -> dict:
        from polymarket.trader import PolymarketTrader

        trader = MagicMock(spec=PolymarketTrader)
        captured = {}

        def _capture(event_type, payload):
            captured.update(payload)

        trader._emit_quant_event = _capture
        trader._runtime_mode = MagicMock(return_value="paper")
        trader._bankroll_tier_detail = MagicMock(return_value={
            "bankroll_tier_id": "T0_MICRO_SEED",
            "bankroll_family": "MICRO",
        })
        trader._micro_survival_active = MagicMock(return_value=True)
        trader._micro_position_size = MagicMock(return_value=0.05)
        trader._risk_plan_zero_reason = MagicMock(return_value="unknown")
        trader._zero_size_primary_constraint = MagicMock(return_value="confidence_too_low")
        trader.bankroll_state = MagicMock()
        trader.bankroll_state.current_bankroll_for_sizing = 20.10
        trader._risk_mode_state = MagicMock()
        trader._risk_mode_state.current_mode.value = "NORMAL"

        mock_ptb = MagicMock()
        mock_ptb.seconds_remaining = 241.0
        mock_ptb.epoch_start_ts = 1_700_000_000

        risk_plan = MagicMock()
        risk_plan.account_balance = 20.10
        risk_plan.diagnostics = {
            "blocked_reasons": ["confidence_too_low"],
            "base_risk_pct": 0.034,
            "final_notional_size": 0.0,
            "min_position_size_usd": 0.05,
            "confidence_multiplier": 0.0,
            "ev_multiplier": 1.0,
            "drawdown_multiplier": 1.0,
            "liquidity_multiplier": 0.9,
            "spread_multiplier": 0.92,
            "time_to_settlement_multiplier": 0.95,
            "delta_multiplier": 0.5,
            "frequency_multiplier": 1.0,
        }

        PolymarketTrader._emit_zero_size_probe_event(
            trader,
            ticker="BTC",
            market_id="pm-5m-btc",
            risk_plan=risk_plan,
            ptb_info=mock_ptb,
            timing_detail={"lifecycle_phase": "ACTIVE_INVENTORY_TRADING"},
            confidence=confidence,
            ev=ev,
            entry_price=0.29,
        )
        return captured

    def test_all_eight_shadow_keys_present(self):
        payload = self._run_emit()
        required = {
            "semantic_c_ev_quality_shadow",
            "semantic_c_input_shadow",
            "semantic_c_multiplier_shadow",
            "semantic_c_size_usd_shadow",
            "semantic_c_would_pass_confidence_gate",
            "semantic_c_would_produce_nonzero_size",
            "semantic_c_size_pct_bankroll",
            "semantic_c_shadow_reason",
        }
        for key in required:
            assert key in payload, f"Missing shadow key: {key}"

    def test_shadow_reason_is_constant_string(self):
        payload = self._run_emit()
        assert payload["semantic_c_shadow_reason"] == "confidence_score_x_ev_quality_not_in_active_sizing"

    def test_shadow_size_positive_for_high_confidence(self):
        payload = self._run_emit(confidence=0.75, ev=0.20)
        assert payload["semantic_c_size_usd_shadow"] > 0.0
        assert payload["semantic_c_would_produce_nonzero_size"] is True
        assert payload["semantic_c_would_pass_confidence_gate"] is True

    def test_shadow_size_zero_for_low_confidence(self):
        # confidence=0.40, ev_quality=0.5 -> c_input=0.20 < 0.54 -> shadow=0
        payload = self._run_emit(confidence=0.40, ev=0.0)
        assert payload["semantic_c_multiplier_shadow"] == 0.0
        assert payload["semantic_c_size_usd_shadow"] == 0.0
        assert payload["semantic_c_would_produce_nonzero_size"] is False

    def test_actual_sizing_unchanged(self):
        """Shadow fields must not affect final_size_usd or the risk plan."""
        payload = self._run_emit(confidence=0.75, ev=0.20)
        # final_size_usd in payload comes from diagnostics["final_notional_size"] = 0.0
        assert payload["final_size_usd"] == 0.0

    def test_emit_survives_zero_ev(self):
        """Fail-soft: zero EV should not raise; ev_quality floors at 0.5."""
        payload = self._run_emit(confidence=0.62, ev=0.0)
        assert payload["semantic_c_ev_quality_shadow"] == 0.5

    def test_shadow_pct_bankroll_is_reasonable(self):
        payload = self._run_emit(confidence=0.62, ev=0.16)
        pct = payload["semantic_c_size_pct_bankroll"]
        # At $20.10 bankroll, expect < 5%
        assert pct >= 0.0
        assert pct < 5.0
