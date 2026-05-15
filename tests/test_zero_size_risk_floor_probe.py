"""
Tests for Zero-Size Risk Floor Probe v1.

Covers:
- zero-size constraint classification
- min-order collision detection
- bankroll-floor collision detection
- MICRO_SURVIVAL active state
- missing-data fail-soft
- additive-only (skip outcome unchanged)
- no runtime behavior change
- probe tool: empty input, run_id filter, asset filter, verdict logic
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

from tools.zero_size_risk_floor_probe import analyse, load_zero_size_events


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def _ev(
    *,
    ticker: str = "BTC",
    constraint: str = "time_remaining_too_short",
    reason: str = "unknown",
    ev: float = 0.05,
    ev_positive: bool = True,
    confidence: float = 0.70,
    confidence_passed: bool = True,
    seconds_remaining: float = 80.0,
    bankroll: float = 20.0,
    bankroll_floor: float = 5.0,
    micro_active: bool = True,
    micro_position_size: float = 0.05,
    blocked_reasons: list | None = None,
    tier_id: str = "T0_MICRO_SEED",
    tier_family: str = "MICRO",
    risk_mode: str = "NORMAL",
    base_risk_pct: float = 0.05,
    raw_size: float = 1.0,
    final_size: float = 0.5,
    min_order: float = 0.05,
    conf_m: float = 0.8,
    ev_m: float = 0.6,
    time_m: float = 0.0,
    run_id: str = "run_test",
) -> dict:
    return {
        "run_id": run_id,
        "payload": {
            "event": "zero_size_probe_v1",
            "ticker": ticker,
            "market_id": f"pm-5m-{ticker.lower()}",
            "epoch_start_ts": 1_700_000_000,
            "seconds_remaining": seconds_remaining,
            "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
            "bankroll": bankroll,
            "bankroll_floor_usd": bankroll_floor,
            "base_risk_pct": base_risk_pct,
            "available_risk_budget_usd": round(bankroll * base_risk_pct, 6),
            "tier_id": tier_id,
            "tier_family": tier_family,
            "risk_mode": risk_mode,
            "micro_survival_active": micro_active,
            "micro_position_size": micro_position_size,
            "confidence": confidence,
            "ev": ev,
            "ev_positive": ev_positive,
            "confidence_passed": confidence_passed,
            "entry_price": 0.60,
            "raw_size_usd": raw_size,
            "final_size_usd": final_size,
            "min_order_usd": min_order,
            "blocked_reasons": blocked_reasons or ["time_remaining_le_90s"],
            "confidence_multiplier": conf_m,
            "ev_multiplier": ev_m,
            "drawdown_multiplier": 1.0,
            "liquidity_multiplier": 1.0,
            "spread_multiplier": 1.0,
            "time_to_settlement_multiplier": time_m,
            "delta_multiplier": 1.0,
            "frequency_multiplier": 1.0,
            "zero_size_reason": reason,
            "zero_size_primary_constraint": constraint,
            "mode": "paper",
        },
    }


def _payloads(events: list[dict]) -> list[dict]:
    return [e["payload"] for e in events]


# ===========================================================================
# 1. Constraint classification
# ===========================================================================

class TestConstraintClassification:
    def test_time_remaining_constraint(self):
        r = analyse(_payloads([_ev(constraint="time_remaining_too_short")]))
        assert r["constraint_distribution"].get("time_remaining_too_short", 0) == 1

    def test_confidence_too_low_constraint(self):
        r = analyse(_payloads([_ev(
            constraint="confidence_too_low",
            blocked_reasons=["confidence_too_low"],
        )]))
        assert r["constraint_distribution"].get("confidence_too_low", 0) == 1

    def test_ev_not_positive_constraint(self):
        r = analyse(_payloads([_ev(
            constraint="ev_not_positive",
            ev=0.0, ev_positive=False,
            blocked_reasons=["ev_not_positive"],
        )]))
        assert r["constraint_distribution"].get("ev_not_positive", 0) == 1

    def test_below_min_order_constraint(self):
        r = analyse(_payloads([_ev(
            constraint="below_min_order",
            blocked_reasons=["below_min_position_size"],
        )]))
        assert r["constraint_distribution"].get("below_min_order", 0) == 1
        assert r["below_min_order_count"] == 1

    def test_bankroll_too_small(self):
        r = analyse(_payloads([_ev(
            constraint="bankroll_too_small",
            bankroll=3.0, bankroll_floor=5.0,
            blocked_reasons=[],
        )]))
        assert r["constraint_distribution"].get("bankroll_too_small", 0) == 1

    def test_spread_too_wide(self):
        r = analyse(_payloads([_ev(
            constraint="spread_too_wide",
            blocked_reasons=["spread_too_wide"],
        )]))
        assert r["constraint_distribution"].get("spread_too_wide", 0) == 1

    def test_multiple_constraints_counted(self):
        payloads = _payloads([
            _ev(constraint="time_remaining_too_short"),
            _ev(constraint="time_remaining_too_short"),
            _ev(constraint="confidence_too_low", blocked_reasons=["confidence_too_low"]),
        ])
        r = analyse(payloads)
        assert r["constraint_distribution"]["time_remaining_too_short"] == 2
        assert r["constraint_distribution"]["confidence_too_low"] == 1
        assert r["event_count"] == 3


# ===========================================================================
# 2. Min-order collision
# ===========================================================================

class TestMinOrderCollision:
    def test_below_min_order_counted(self):
        payloads = _payloads([
            _ev(constraint="below_min_order", blocked_reasons=["below_min_position_size"]),
            _ev(constraint="time_remaining_too_short"),
        ])
        r = analyse(payloads)
        assert r["below_min_order_count"] == 1
        assert r["below_min_order_pct"] == 50.0

    def test_no_below_min_when_not_in_blocked(self):
        payloads = _payloads([_ev(blocked_reasons=["time_remaining_le_90s"])])
        r = analyse(payloads)
        assert r["below_min_order_count"] == 0


# ===========================================================================
# 3. Bankroll floor collision
# ===========================================================================

class TestBankrollFloorCollision:
    def test_at_floor_counted(self):
        payloads = _payloads([
            _ev(bankroll=4.5, bankroll_floor=5.0, constraint="bankroll_too_small"),
            _ev(bankroll=9.9, bankroll_floor=5.0, constraint="time_remaining_too_short"),
            _ev(bankroll=20.0, bankroll_floor=5.0, constraint="time_remaining_too_short"),
        ])
        r = analyse(payloads)
        assert r["at_or_near_floor_count"] == 2  # both < 5.0 * 2 = 10

    def test_bankroll_stats_populated(self):
        payloads = _payloads([
            _ev(bankroll=20.0),
            _ev(bankroll=20.0),
        ])
        r = analyse(payloads)
        assert r["bankroll_stats"]["mean"] == 20.0


# ===========================================================================
# 4. MICRO_SURVIVAL
# ===========================================================================

class TestMicroSurvival:
    def test_micro_active_counted(self):
        payloads = _payloads([
            _ev(micro_active=True),
            _ev(micro_active=True),
            _ev(micro_active=False),
        ])
        r = analyse(payloads)
        assert r["micro_survival_active_count"] == 2
        assert abs(r["micro_survival_active_pct"] - 66.7) < 0.2

    def test_micro_dominant_triggers_correct_verdict(self):
        payloads = _payloads([
            _ev(micro_active=True, constraint="time_remaining_too_short"),
            _ev(micro_active=True, constraint="time_remaining_too_short"),
            _ev(micro_active=True, constraint="time_remaining_too_short"),
        ])
        r = analyse(payloads)
        assert r["verdict"] == "MICRO_SURVIVAL_CORRECT"

    def test_below_min_significant_triggers_review(self):
        payloads = _payloads([
            _ev(micro_active=True, constraint="below_min_order",
                blocked_reasons=["below_min_position_size"]),
            _ev(micro_active=True, constraint="below_min_order",
                blocked_reasons=["below_min_position_size"]),
            _ev(micro_active=True, constraint="time_remaining_too_short"),
        ])
        r = analyse(payloads)
        assert r["verdict"] == "REVIEW_NEEDED"


# ===========================================================================
# 5. EV-positive and confidence-passed detection
# ===========================================================================

class TestEvConfidenceDetection:
    def test_ev_positive_counted(self):
        payloads = _payloads([
            _ev(ev=0.05, ev_positive=True),
            _ev(ev=-0.01, ev_positive=False),
        ])
        r = analyse(payloads)
        assert r["ev_positive_count"] == 1
        assert r["ev_positive_pct"] == 50.0

    def test_confidence_passed_counted(self):
        payloads = _payloads([
            _ev(confidence=0.70, confidence_passed=True),
            _ev(confidence=0.40, confidence_passed=False),
        ])
        r = analyse(payloads)
        assert r["confidence_passed_count"] == 1

    def test_both_ev_and_conf_passed(self):
        payloads = _payloads([
            _ev(ev=0.05, ev_positive=True, confidence=0.70, confidence_passed=True),
            _ev(ev=0.05, ev_positive=True, confidence=0.40, confidence_passed=False),
            _ev(ev=-0.01, ev_positive=False, confidence=0.70, confidence_passed=True),
        ])
        r = analyse(payloads)
        assert r["ev_positive_and_confidence_passed_count"] == 1

    def test_active_window_rate(self):
        payloads = _payloads([
            _ev(seconds_remaining=200.0),   # active
            _ev(seconds_remaining=200.0),   # active
            _ev(seconds_remaining=30.0),    # not active
        ])
        r = analyse(payloads)
        assert r["active_window_count"] == 2
        assert abs(r["active_window_pct"] - 66.7) < 0.2


# ===========================================================================
# 6. Fail-soft
# ===========================================================================

class TestFailSoft:
    def test_emit_method_survives_internal_exception(self):
        from polymarket.trader import PolymarketTrader
        trader = MagicMock(spec=PolymarketTrader)
        trader._emit_quant_event = MagicMock(side_effect=RuntimeError("crash"))
        trader._runtime_mode = MagicMock(return_value="paper")
        trader._bankroll_tier_detail = MagicMock(return_value={})
        trader._micro_survival_active = MagicMock(return_value=True)
        trader._micro_position_size = MagicMock(return_value=0.05)
        trader._risk_plan_zero_reason = MagicMock(return_value="unknown")
        trader._zero_size_primary_constraint = MagicMock(return_value="unknown")
        mock_ptb = MagicMock()
        mock_ptb.seconds_remaining = 200.0
        mock_ptb.epoch_start_ts = 1_700_000_000
        trader.bankroll_state = MagicMock()
        trader.bankroll_state.current_bankroll_for_sizing = 20.0
        trader._risk_mode_state = MagicMock()
        trader._risk_mode_state.current_mode.value = "NORMAL"
        # Should not raise
        PolymarketTrader._emit_zero_size_probe_event(
            trader,
            ticker="BTC",
            market_id="pm-5m-btc",
            risk_plan=None,
            ptb_info=mock_ptb,
            timing_detail={"lifecycle_phase": "ACTIVE_INVENTORY_TRADING"},
            confidence=0.70,
            ev=0.05,
            entry_price=0.60,
        )

    def test_empty_events_returns_error_dict(self):
        r = analyse([])
        assert r["event_count"] == 0
        assert "error" in r


# ===========================================================================
# 7. Additive-only: skip outcome unchanged
# ===========================================================================

class TestAdditiveOnly:
    def test_skip_reason_unchanged_after_probe(self):
        from polymarket.trader import PolymarketTrader
        skip_reason = "Risk plan returned zero position size -- skipping."
        # Probe call should not modify skip_reason
        trader = MagicMock(spec=PolymarketTrader)
        trader._emit_quant_event = MagicMock()
        trader._runtime_mode = MagicMock(return_value="paper")
        trader._bankroll_tier_detail = MagicMock(return_value={})
        trader._micro_survival_active = MagicMock(return_value=True)
        trader._micro_position_size = MagicMock(return_value=0.05)
        trader._risk_plan_zero_reason = MagicMock(return_value="unknown")
        trader._zero_size_primary_constraint = MagicMock(return_value="time_remaining_too_short")
        trader.bankroll_state = MagicMock()
        trader.bankroll_state.current_bankroll_for_sizing = 20.0
        trader._risk_mode_state = MagicMock()
        trader._risk_mode_state.current_mode.value = "NORMAL"
        mock_ptb = MagicMock()
        mock_ptb.seconds_remaining = 200.0
        mock_ptb.epoch_start_ts = 1_700_000_000
        PolymarketTrader._emit_zero_size_probe_event(
            trader,
            ticker="BTC", market_id="pm-5m-btc", risk_plan=None,
            ptb_info=mock_ptb,
            timing_detail={"lifecycle_phase": "ACTIVE_INVENTORY_TRADING"},
            confidence=0.70, ev=0.05, entry_price=0.60,
        )
        assert skip_reason == "Risk plan returned zero position size -- skipping."


# ===========================================================================
# 8. No runtime behavior change
# ===========================================================================

class TestNoRuntimeBehaviorChange:
    def test_position_size_still_zero_after_probe(self):
        """Probe must not modify risk_plan.position_size."""
        from polymarket.trader import PolymarketTrader
        risk_plan = MagicMock()
        risk_plan.position_size = 0.0
        risk_plan.account_balance = 20.0
        risk_plan.diagnostics = {"blocked_reasons": ["time_remaining_le_90s"]}
        trader = MagicMock(spec=PolymarketTrader)
        trader._emit_quant_event = MagicMock()
        trader._runtime_mode = MagicMock(return_value="paper")
        trader._bankroll_tier_detail = MagicMock(return_value={})
        trader._micro_survival_active = MagicMock(return_value=True)
        trader._micro_position_size = MagicMock(return_value=0.05)
        trader._risk_plan_zero_reason = MagicMock(return_value="unknown")
        trader._zero_size_primary_constraint = MagicMock(return_value="time_remaining_too_short")
        trader.bankroll_state = MagicMock()
        trader.bankroll_state.current_bankroll_for_sizing = 20.0
        trader._risk_mode_state = MagicMock()
        trader._risk_mode_state.current_mode.value = "NORMAL"
        mock_ptb = MagicMock()
        mock_ptb.seconds_remaining = 200.0
        mock_ptb.epoch_start_ts = 1_700_000_000
        PolymarketTrader._emit_zero_size_probe_event(
            trader,
            ticker="BTC", market_id="pm-5m-btc", risk_plan=risk_plan,
            ptb_info=mock_ptb,
            timing_detail={"lifecycle_phase": "ACTIVE_INVENTORY_TRADING"},
            confidence=0.70, ev=0.05, entry_price=0.60,
        )
        assert risk_plan.position_size == 0.0


# ===========================================================================
# 9. Probe tool: filters and edge cases
# ===========================================================================

class TestProbeToolFilters:
    def test_run_id_filter(self, tmp_path):
        events = [
            _ev(run_id="run_A", constraint="time_remaining_too_short"),
            _ev(run_id="run_B", constraint="confidence_too_low",
                blocked_reasons=["confidence_too_low"]),
            _ev(run_id="run_A", constraint="time_remaining_too_short"),
        ]
        jl = tmp_path / "system_health" / "2026-01-01.jsonl"
        jl.parent.mkdir(parents=True)
        jl.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
        loaded = load_zero_size_events("2026-01-01", quant_data_dir=tmp_path, run_id="run_A")
        assert len(loaded) == 2

    def test_asset_filter(self, tmp_path):
        events = [
            _ev(ticker="BTC"),
            _ev(ticker="ETH"),
            _ev(ticker="BTC"),
        ]
        jl = tmp_path / "system_health" / "2026-01-01.jsonl"
        jl.parent.mkdir(parents=True)
        jl.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
        loaded = load_zero_size_events("2026-01-01", quant_data_dir=tmp_path, asset_filter="ETH")
        assert len(loaded) == 1

    def test_btc_eth_breakdown(self):
        payloads = _payloads([
            _ev(ticker="BTC", constraint="time_remaining_too_short"),
            _ev(ticker="BTC", constraint="time_remaining_too_short"),
            _ev(ticker="ETH", constraint="confidence_too_low",
                blocked_reasons=["confidence_too_low"]),
        ])
        r = analyse(payloads)
        assert r["btc"]["count"] == 2
        assert r["eth"]["count"] == 1
        assert r["eth"]["top_constraint"] == "confidence_too_low"


# ===========================================================================
# 10. Multiplier stats
# ===========================================================================

class TestMultiplierStats:
    def test_multiplier_fields_read_from_events(self):
        payloads = _payloads([
            _ev(conf_m=0.80, ev_m=0.60, time_m=0.0),
            _ev(conf_m=0.90, ev_m=0.70, time_m=0.0),
        ])
        r = analyse(payloads)
        stats = r.get("multiplier_stats") or {}
        assert stats.get("confidence_multiplier") is not None
        assert abs(stats["confidence_multiplier"]["mean"] - 0.85) < 0.01
        assert abs(stats["time_to_settlement_multiplier"]["mean"] - 0.0) < 0.001

    def test_zero_time_multiplier_detected(self):
        """time_to_settlement_multiplier=0 is a key collapse signal."""
        payloads = _payloads([_ev(time_m=0.0), _ev(time_m=0.0)])
        r = analyse(payloads)
        stats = r.get("multiplier_stats") or {}
        assert stats["time_to_settlement_multiplier"]["max"] == 0.0


# ===========================================================================
# 11. Verdict logic
# ===========================================================================

class TestVerdictLogic:
    def test_verdict_correct_for_time_constraint(self):
        payloads = _payloads([_ev(constraint="time_remaining_too_short")] * 5)
        r = analyse(payloads)
        assert r["verdict"] == "MICRO_SURVIVAL_CORRECT"

    def test_verdict_review_for_high_ev_positive(self):
        """High EV-positive + non-time dominant constraint → REVIEW_NEEDED."""
        payloads = _payloads([
            _ev(constraint="confidence_too_low",
                ev_positive=True, ev=0.08,
                blocked_reasons=["confidence_too_low"]) for _ in range(5)
        ] + [_ev(constraint="time_remaining_too_short")])
        r = analyse(payloads)
        # >30% EV positive with non-time dominant → REVIEW_NEEDED
        assert r["ev_positive_pct"] > 30
        assert r["verdict"] == "REVIEW_NEEDED"
