"""Tests for ShadowPolicyEvaluator and wiring into trader/canonical builder.

OBSERVABILITY GUARANTEE: shadow_policy_decision must never gate execution.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from polymarket.shadow_policy import (
    DECISION_ACCEPT,
    DECISION_REJECT,
    REASON_EV_BELOW_THRESHOLD,
    REASON_MISSING_EV,
    REASON_MISSING_PROBABILITY,
    REASON_MISSING_RISK_MODE,
    REASON_PROBABILITY_BELOW_THRESHOLD,
    REASON_RISK_MODE_BLOCKED,
    SHADOW_MIN_EV,
    SHADOW_MIN_PROBABILITY,
    SHADOW_POLICY_ID,
    ShadowPolicyEvaluator,
    ShadowPolicyResult,
)


# ---------------------------------------------------------------------------
# ShadowPolicyEvaluator unit tests
# ---------------------------------------------------------------------------

class TestShadowPolicyEvaluator:
    def _e(self) -> ShadowPolicyEvaluator:
        return ShadowPolicyEvaluator()

    # ── ACCEPT cases ──────────────────────────────────────────────────────

    def test_accept_exact_thresholds(self):
        r = self._e().evaluate(ev=0.12, probability=0.65, risk_mode="NORMAL")
        assert r.decision == DECISION_ACCEPT
        assert r.reasons == []

    def test_accept_above_thresholds(self):
        r = self._e().evaluate(ev=0.20, probability=0.75, risk_mode="NORMAL")
        assert r.decision == DECISION_ACCEPT

    def test_accept_records_observed_values(self):
        r = self._e().evaluate(ev=0.15, probability=0.68, risk_mode="NORMAL")
        assert r.observed_ev == pytest.approx(0.15)
        assert r.observed_probability == pytest.approx(0.68)
        assert r.observed_risk_mode == "NORMAL"

    def test_accept_normal_uppercase(self):
        r = self._e().evaluate(ev=0.13, probability=0.66, risk_mode="NORMAL")
        assert r.decision == DECISION_ACCEPT

    # ── REJECT: EV below threshold ─────────────────────────────────────────

    def test_reject_low_ev(self):
        r = self._e().evaluate(ev=0.08, probability=0.68, risk_mode="NORMAL")
        assert r.decision == DECISION_REJECT
        assert REASON_EV_BELOW_THRESHOLD in r.reasons

    def test_reject_ev_just_below(self):
        r = self._e().evaluate(ev=0.1199, probability=0.68, risk_mode="NORMAL")
        assert r.decision == DECISION_REJECT
        assert REASON_EV_BELOW_THRESHOLD in r.reasons

    def test_reject_ev_zero(self):
        r = self._e().evaluate(ev=0.0, probability=0.68, risk_mode="NORMAL")
        assert REASON_EV_BELOW_THRESHOLD in r.reasons

    # ── REJECT: Probability below threshold ────────────────────────────────

    def test_reject_low_probability(self):
        r = self._e().evaluate(ev=0.15, probability=0.60, risk_mode="NORMAL")
        assert r.decision == DECISION_REJECT
        assert REASON_PROBABILITY_BELOW_THRESHOLD in r.reasons

    def test_reject_probability_just_below(self):
        r = self._e().evaluate(ev=0.15, probability=0.6499, risk_mode="NORMAL")
        assert REASON_PROBABILITY_BELOW_THRESHOLD in r.reasons

    # ── REJECT: Risk mode blocked ─────────────────────────────────────────

    def test_reject_micro_recovery_mode(self):
        r = self._e().evaluate(ev=0.15, probability=0.68, risk_mode="MICRO_RECOVERY")
        assert r.decision == DECISION_REJECT
        assert REASON_RISK_MODE_BLOCKED in r.reasons

    def test_reject_defensive_mode(self):
        r = self._e().evaluate(ev=0.15, probability=0.68, risk_mode="DEFENSIVE")
        assert REASON_RISK_MODE_BLOCKED in r.reasons

    def test_reject_lockdown_mode(self):
        r = self._e().evaluate(ev=0.15, probability=0.68, risk_mode="LOCKDOWN")
        assert REASON_RISK_MODE_BLOCKED in r.reasons

    # ── REJECT: Missing fields ────────────────────────────────────────────

    def test_reject_missing_ev(self):
        r = self._e().evaluate(ev=None, probability=0.68, risk_mode="NORMAL")
        assert r.decision == DECISION_REJECT
        assert REASON_MISSING_EV in r.reasons
        assert r.observed_ev is None

    def test_reject_missing_probability(self):
        r = self._e().evaluate(ev=0.15, probability=None, risk_mode="NORMAL")
        assert REASON_MISSING_PROBABILITY in r.reasons

    def test_reject_missing_risk_mode(self):
        r = self._e().evaluate(ev=0.15, probability=0.68, risk_mode=None)
        assert REASON_MISSING_RISK_MODE in r.reasons

    def test_reject_missing_risk_mode_empty_string(self):
        r = self._e().evaluate(ev=0.15, probability=0.68, risk_mode="")
        assert REASON_MISSING_RISK_MODE in r.reasons

    # ── Multi-reason REJECT ───────────────────────────────────────────────

    def test_reject_multiple_reasons(self):
        r = self._e().evaluate(ev=0.05, probability=0.55, risk_mode="MICRO_RECOVERY")
        assert r.decision == DECISION_REJECT
        assert REASON_EV_BELOW_THRESHOLD in r.reasons
        assert REASON_PROBABILITY_BELOW_THRESHOLD in r.reasons
        assert REASON_RISK_MODE_BLOCKED in r.reasons

    def test_all_missing_produces_three_missing_reasons(self):
        r = self._e().evaluate(ev=None, probability=None, risk_mode=None)
        assert REASON_MISSING_EV in r.reasons
        assert REASON_MISSING_PROBABILITY in r.reasons
        assert REASON_MISSING_RISK_MODE in r.reasons

    # ── to_dict ───────────────────────────────────────────────────────────

    def test_to_dict_accept(self):
        r = self._e().evaluate(ev=0.13, probability=0.67, risk_mode="NORMAL")
        d = r.to_dict()
        assert d["shadow_policy_decision"] == DECISION_ACCEPT
        assert d["shadow_policy_id"] == SHADOW_POLICY_ID
        assert d["shadow_policy_min_ev"] == SHADOW_MIN_EV
        assert d["shadow_policy_min_probability"] == SHADOW_MIN_PROBABILITY
        assert d["shadow_policy_allowed_risk_modes"] == ["NORMAL"]
        assert d["shadow_policy_observed_ev"] == pytest.approx(0.13)
        assert d["shadow_policy_confidence"] == "LOW_STATISTICAL_CONFIDENCE"
        assert d["shadow_policy_source"] == "BACKTEST_ENGINE_V2_POLICY_GRID_EXPANSION_001"

    def test_to_dict_reject_contains_reasons(self):
        r = self._e().evaluate(ev=0.05, probability=0.68, risk_mode="NORMAL")
        d = r.to_dict()
        assert d["shadow_policy_decision"] == DECISION_REJECT
        assert REASON_EV_BELOW_THRESHOLD in d["shadow_policy_reasons"]

    def test_to_dict_versions_present(self):
        r = self._e().evaluate(ev=0.13, probability=0.67, risk_mode="NORMAL")
        d = r.to_dict()
        assert "shadow_policy_version" in d
        assert "shadow_policy_id" in d


# ---------------------------------------------------------------------------
# Trader wiring: trade_open carries shadow policy fields
# ---------------------------------------------------------------------------

@dataclass
class _Receipt:
    order_id: str = "ord_shadow"
    status: str = "filled"
    filled_size: float = 1.0
    remaining_size: float = 0.0
    price: float = 0.55
    size: float = 1.0
    order_type: str = "GTC"


def _make_trader(tmp_path):
    from config.settings import Settings
    from polymarket.trader import PolymarketTrader
    s = Settings()
    s.paper_trading = True
    s.quant_data_dir = str(tmp_path / "qdata")
    trader = PolymarketTrader(settings=s)
    emitted: list = []
    trader._emit_quant_event = lambda et, p: emitted.append((et, p))
    trader._emitted_events = emitted
    return trader


class TestTraderWiring:
    def test_trade_open_carries_shadow_accept(self, tmp_path):
        trader = _make_trader(tmp_path)
        ticker = "BTC"
        trader.last_quant_details[ticker] = {
            "signal_name": "PROBABILITY_EV_EDGE",
            "size_sharp_result": None,
            "shadow_policy_decision": DECISION_ACCEPT,
            "shadow_policy_reasons": [],
            "shadow_policy_observed_ev": 0.15,
            "shadow_policy_observed_probability": 0.68,
            "shadow_policy_observed_risk_mode": "NORMAL",
            "shadow_policy_id": SHADOW_POLICY_ID,
            "shadow_policy_confidence": "LOW_STATISTICAL_CONFIDENCE",
        }
        rp = MagicMock()
        rp.position_size = 1.0
        rp.notional_size = 0.55
        trader._emit_trade_opened_event(
            market_id="pm-5m-btc",
            ticker=ticker,
            token_id="tok_001",
            outcome="YES",
            receipt=_Receipt(),
            risk_plan=rp,
            entry_price=0.55,
            strategy="NORMAL_SCALP",
        )
        calls = [p for et, p in trader._emitted_events if et == "log_trade_open"]
        assert len(calls) == 1
        payload = calls[0]
        assert payload.get("shadow_policy_decision") == DECISION_ACCEPT
        assert payload.get("shadow_policy_observed_ev") == pytest.approx(0.15)
        assert payload.get("shadow_policy_id") == SHADOW_POLICY_ID

    def test_trade_open_carries_shadow_reject(self, tmp_path):
        trader = _make_trader(tmp_path)
        ticker = "ETH"
        trader.last_quant_details[ticker] = {
            "shadow_policy_decision": DECISION_REJECT,
            "shadow_policy_reasons": [REASON_EV_BELOW_THRESHOLD],
            "shadow_policy_observed_ev": 0.08,
            "shadow_policy_observed_probability": 0.68,
            "shadow_policy_observed_risk_mode": "NORMAL",
            "shadow_policy_id": SHADOW_POLICY_ID,
            "shadow_policy_confidence": "LOW_STATISTICAL_CONFIDENCE",
        }
        rp = MagicMock()
        rp.position_size = 1.0
        rp.notional_size = 0.50
        trader._emit_trade_opened_event(
            market_id="pm-5m-eth",
            ticker=ticker,
            token_id="tok_002",
            outcome="NO",
            receipt=_Receipt(),
            risk_plan=rp,
            entry_price=0.50,
            strategy="NORMAL_SCALP",
        )
        calls = [p for et, p in trader._emitted_events if et == "log_trade_open"]
        payload = calls[0]
        assert payload.get("shadow_policy_decision") == DECISION_REJECT

    def test_trade_close_carries_shadow_fields(self, tmp_path):
        from polymarket.trader import PolymarketTrader
        trader = _make_trader(tmp_path)
        metadata = {
            "shadow_policy_decision": DECISION_ACCEPT,
            "shadow_policy_observed_ev": 0.14,
            "shadow_policy_observed_probability": 0.67,
            "shadow_policy_observed_risk_mode": "NORMAL",
            "shadow_policy_id": SHADOW_POLICY_ID,
            "shadow_policy_reasons": [],
        }
        position = trader.tracker.open_position(
            symbol="pm-5m-btc",
            source="polymarket",
            side="BUY",
            entry_price=0.55,
            size=1.0,
            stop_loss=0.45,
            take_profit=0.65,
            order_id="ord_sp_001",
            metadata=metadata,
        )
        closed = trader.tracker.close_position(position.position_id, 0.65, reason="take_profit")
        trader._emit_trade_closed_event(
            position=closed, reason="take_profit",
            exit_price=0.65, size=1.0, pnl=0.10, receipt=None,
        )
        calls = [p for et, p in trader._emitted_events if et == "log_trade_close"]
        assert len(calls) == 1
        payload = calls[0]
        assert payload.get("shadow_policy_decision") == DECISION_ACCEPT
        assert payload.get("shadow_policy_observed_ev") == pytest.approx(0.14)
        assert payload.get("shadow_policy_id") == SHADOW_POLICY_ID


# ---------------------------------------------------------------------------
# Canonical builder extraction
# ---------------------------------------------------------------------------

class TestCanonicalBuilderExtraction:
    def _build_row_with_shadow(self, decision: str, ev: float, tmp_path) -> dict:
        from tools.runtime.canonical_trade_context_builder import CanonicalContextBuilder
        date_str = "2026-06-28"
        rkey = f"cond|epoch|BTC|YES|tok_{decision}"
        run_id = f"run_shadow_{decision}"
        open_event = {
            "event_type": "trade_open",
            "timestamp_utc": "2026-06-28T10:00:00Z",
            "run_id": run_id,
            "payload": {
                "paper_trade_replay_key": rkey,
                "position_id": f"pos_sp_{decision}",
                "ticker": "BTC",
                "ev": ev,
                "true_probability": 0.68,
                "fair_value": 0.68,
                "bankroll_tier_id": "T0",
                "risk_mode": "NORMAL",
                "entry_price": 0.55,
                "size": 1.0,
                "shadow_policy_decision": decision,
                "shadow_policy_observed_ev": ev,
                "shadow_policy_observed_probability": 0.68,
                "shadow_policy_observed_risk_mode": "NORMAL",
                "shadow_policy_id": SHADOW_POLICY_ID,
                "shadow_policy_confidence": "LOW_STATISTICAL_CONFIDENCE",
                "shadow_policy_reasons": [] if decision == DECISION_ACCEPT else [REASON_EV_BELOW_THRESHOLD],
            },
        }
        close_event = {
            "event_type": "trade_close",
            "timestamp_utc": "2026-06-28T10:01:00Z",
            "run_id": run_id,
            "payload": {
                "paper_trade_replay_key": rkey,
                "position_id": f"pos_sp_{decision}",
                "exit_price": 0.60,
                "pnl": 0.05,
                "exit_reason": "take_profit",
            },
        }
        base = tmp_path / f"qdata_{decision}"
        (base / "trade_journal").mkdir(parents=True)
        with open(base / "trade_journal" / f"{date_str}.jsonl", "w") as f:
            f.write(json.dumps(open_event) + "\n")
            f.write(json.dumps(close_event) + "\n")
        builder = CanonicalContextBuilder(base, [date_str])
        builder.load_all()
        rows, _ = builder.compile()
        return rows[0] if rows else {}

    def test_accept_decision_extracted(self, tmp_path):
        row = self._build_row_with_shadow(DECISION_ACCEPT, 0.14, tmp_path)
        assert row.get("shadow_policy_decision") == DECISION_ACCEPT

    def test_reject_decision_extracted(self, tmp_path):
        row = self._build_row_with_shadow(DECISION_REJECT, 0.08, tmp_path)
        assert row.get("shadow_policy_decision") == DECISION_REJECT

    def test_observed_ev_extracted_as_float(self, tmp_path):
        row = self._build_row_with_shadow(DECISION_ACCEPT, 0.14, tmp_path)
        assert row.get("shadow_policy_observed_ev") == pytest.approx(0.14)

    def test_shadow_policy_id_extracted(self, tmp_path):
        row = self._build_row_with_shadow(DECISION_ACCEPT, 0.14, tmp_path)
        assert row.get("shadow_policy_id") == SHADOW_POLICY_ID

    def test_legacy_rows_without_shadow_compile_clean(self, tmp_path):
        from tools.runtime.canonical_trade_context_builder import CanonicalContextBuilder
        date_str = "2026-06-28"
        rkey = "cond|epoch|BTC|YES|tok_legacy"
        open_event = {
            "event_type": "trade_open", "timestamp_utc": "2026-06-28T10:00:00Z",
            "run_id": "run_legacy",
            "payload": {
                "paper_trade_replay_key": rkey, "position_id": "pos_legacy",
                "ticker": "BTC", "ev": 0.10, "true_probability": 0.65,
                "fair_value": 0.65, "bankroll_tier_id": "T0",
                "risk_mode": "NORMAL", "entry_price": 0.55, "size": 1.0,
                # No shadow_policy fields at all
            },
        }
        close_event = {
            "event_type": "trade_close", "timestamp_utc": "2026-06-28T10:01:00Z",
            "run_id": "run_legacy",
            "payload": {"paper_trade_replay_key": rkey, "position_id": "pos_legacy",
                        "exit_price": 0.60, "pnl": 0.05, "exit_reason": "take_profit"},
        }
        base = tmp_path / "qdata_legacy"
        (base / "trade_journal").mkdir(parents=True)
        with open(base / "trade_journal" / f"{date_str}.jsonl", "w") as f:
            f.write(json.dumps(open_event) + "\n")
            f.write(json.dumps(close_event) + "\n")
        builder = CanonicalContextBuilder(base, [date_str])
        builder.load_all()
        rows, _ = builder.compile()
        assert len(rows) == 1
        row = rows[0]
        assert row.get("shadow_policy_decision") is None
        assert row.get("shadow_policy_observed_ev") is None
        assert "trade_id" in row


# ---------------------------------------------------------------------------
# Source guard: no execution/risk/sizing path reads shadow_policy_decision
# ---------------------------------------------------------------------------

def test_source_guard_execution_paths_do_not_read_shadow_policy():
    """shadow_policy_decision must not appear in execution/risk/sizing methods."""
    source = Path("polymarket/trader.py").read_text(encoding="utf-8")
    forbidden_fns = [
        "build_order_plan",
        "place_limit_order",
        "_submit_order",
        "order_intent",
        "_apply_risk_mode_to_plan",
        "_maybe_apply_micro_survival_plan",
        "_preflight_balance_allowance",
    ]
    for fn in forbidden_fns:
        marker = f"def {fn}"
        if marker not in source:
            continue
        start = source.index(marker)
        next_def = source.find("\n    def ", start + 1)
        body = source[start:next_def] if next_def > 0 else source[start:]
        assert "shadow_policy_decision" not in body, (
            f"OBSERVABILITY VIOLATION: shadow_policy_decision found in {fn}"
        )
