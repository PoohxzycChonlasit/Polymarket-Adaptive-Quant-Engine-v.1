from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch
import pytest

from config.settings import get_settings
from polymarket.client import OrderReceipt
from polymarket.gamma_fetcher import GammaMarket
from polymarket.trader import PolymarketTrader
from polymarket.delta_engine import DeltaRegime
from polymarket.opportunity_scanner import OpportunityDecision


class MockSettings:
    def __init__(self, paper_trading: bool) -> None:
        try:
            self._real_settings = get_settings()
        except Exception:
            self._real_settings = SimpleNamespace()
        self.paper_trading = paper_trading
        self.dry_run = True
        self.account_balance = 100000.0
        self.bankroll_floor = 5.0
        self.max_risk_per_trade = 0.10
        self.default_stop_loss_pct = 0.08
        self.kelly_fraction_cap = 0.25
        self.execution_entry_cutoff_seconds = 90
        self.adaptive_entry_hard_block_seconds = 45
        self.entry_min_seconds_remaining = 30
        self.exit_agent_entry_cutoff_seconds = 45
        self.exit_agent_cancel_entries_seconds = 35
        self.exit_agent_force_exit_seconds = 25
        self.adaptive_entry_max_spread = 0.06
        self.api_retry_attempts = 1
        self.max_active_positions_per_market = 1
        self.max_entries_per_market = 1
        self.max_feed_age_seconds = 10.0
        self.micro_adaptive_timing_enabled = False
        self.hybrid_phase_v1_enabled = False
        self.verbose_scan_logs = False
        self.verbose_model_logs = False
        self.execution_stop_loss_pct = 0.08
        self.execution_take_profit_pct = 0.10
        self.min_shares_per_order = 10.0
        self.polymarket_proxy_wallet = ""
        self.polymarket_funder = ""
        self.arb_min_net_edge = 0.010
        self.arb_min_profit_usdc = 0.02
        self.arb_fee_buffer = 0.002
        self.arb_slippage_buffer = 0.003
        self.arb_fail_risk_buffer = 0.003
        self.arb_max_leg_spread = 0.03
        self.arb_display_enabled = False
        self.arb_auto_execute = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real_settings, name)


class _CollectingQuantLogger:
    def __init__(self) -> None:
        self.mode = "paper"
        self.run_id = "test_run_123"
        self.schema_version = "test_version"
        self.events = []

    def _timestamp(self) -> str:
        return "2026-06-17T05:00:00Z"

    def log_signal_filter_shadow(self, payload: dict) -> bool:
        self.events.append(("signal_filter_shadow", payload))
        return True


def _settings(paper_trading=True) -> MockSettings:
    return MockSettings(paper_trading)


def _market() -> GammaMarket:
    return GammaMarket(
        market_id="pm-5m-btc",
        question="Will BTC close above the target?",
        volume=1000.0,
        liquidity=100.0,
        end_date_iso="",
    )


def _ptb_info() -> SimpleNamespace:
    epoch_start = int(time.time()) - 120
    return SimpleNamespace(
        current_price=100000.0,
        price_to_beat=100100.0,
        price_diff_pct=-0.10,
        seconds_remaining=180,
        epoch_start_ts=epoch_start,
        epoch_end_ts=epoch_start + 300,
        last_updated=time.time(),
        feed_age_seconds=1.0,
    )


def _setup_mocked_trader(paper_trading=True) -> PolymarketTrader:
    settings_obj = _settings(paper_trading)
    trader = PolymarketTrader(settings=settings_obj)
    trader.quant_events = _CollectingQuantLogger()
    
    def mock_get_orderbook(token_id):
        from polymarket.client import OrderbookSnapshot
        if token_id == "yes-token":
            return OrderbookSnapshot("yes-token", 0.50, 0.51, 0.01, 10000.0, 10000.0, age_seconds=0.05)
        else:
            return OrderbookSnapshot("no-token", 0.49, 0.50, 0.01, 10000.0, 10000.0, age_seconds=0.05)
            
    trader.client.get_orderbook = MagicMock(side_effect=mock_get_orderbook)
    trader._real_token_ids["BTC"] = ("yes-token", "no-token")
    trader._market_token_meta["BTC"] = {
        "slug": "btc-updown-5m",
        "condition_id": "condition-btc",
        "yes_token_id": "yes-token",
        "no_token_id": "no-token",
        "epoch_start_ts": int(time.time()) - 120,
        "epoch_end_ts": int(time.time()) + 180,
    }
    # Mock submission
    trader._submit_order = MagicMock(return_value=OrderReceipt(order_id="ord_123", status="FILLED", token_id="yes-token", side="BUY", price=0.51, size=10.0))
    return trader


def _run_evaluation(trader, p_yes, p_no, ev_yes, ev_no, side="YES", approved=True):
    # Mock model functions inside trader module scope
    prob_result = SimpleNamespace(
        p_yes=p_yes,
        p_no=p_no,
        confidence_score=0.75,
        model_reason="test_model_reason",
        skipped=False,
        skip_reason="",
    )
    delta_result = SimpleNamespace(
        delta_score=0.1,
        delta_regime=DeltaRegime.NORMAL,
        delta_multiplier=1.0,
    )
    ev_result = SimpleNamespace(
        approved=approved,
        side=side,
        ev_yes=ev_yes,
        ev_no=ev_no,
        min_ev=0.02,
    )
    scored = SimpleNamespace(
        ev_result=ev_result,
        score=0.95,
        skip_reason="",
    )
    scan_result = SimpleNamespace(
        best_trade=scored,
        watchlist=[scored],
        skipped=[],
        decision=OpportunityDecision.BEST_TRADE,
    )

    with patch("polymarket.trader.estimate_probability", return_value=prob_result), \
         patch("polymarket.trader.estimate_micro_delta", return_value=delta_result), \
         patch("polymarket.trader.scan_opportunities", return_value=scan_result), \
         patch("polymarket.trader.trade_quality_allowed", return_value=(True, "")):
        
        return trader._analyze_market_quant(_market(), "BTC", _ptb_info())


# Test Cases

def test_shadow_event_emitted_for_paper_baseline_approved_candidate() -> None:
    # 1. Shadow event emitted for paper baseline-approved candidate.
    trader = _setup_mocked_trader(paper_trading=True)
    # entry_ev=0.16 (toxicity: True), entry_probability=0.61 (YES floor: False)
    _run_evaluation(trader, p_yes=0.61, p_no=0.39, ev_yes=0.16, ev_no=0.01, side="YES")

    assert len(trader.quant_events.events) == 1
    event_name, payload = trader.quant_events.events[0]
    assert event_name == "signal_filter_shadow"
    assert payload["baseline_approved"] is True
    assert payload["shadow_would_reject"] is True
    assert "ev_cap_toxicity" in payload["shadow_filter_reasons"]


def test_candidate_approval_unchanged() -> None:
    # 2. Candidate approval unchanged.
    trader = _setup_mocked_trader(paper_trading=True)
    # Filters would reject (ev=0.16, p_yes=0.55), but actual baseline should enter
    outcome = _run_evaluation(trader, p_yes=0.55, p_no=0.45, ev_yes=0.16, ev_no=0.01, side="YES")

    # The filter would reject, but actual outcome is not skipped (decision="buy" for YES entries)
    assert outcome.skipped is False
    assert outcome.decision == "buy"
    assert trader.quant_events.events[0][1]["shadow_would_reject"] is True


def test_candidate_trade_path_unchanged() -> None:
    # 3. Candidate trade path unchanged.
    trader = _setup_mocked_trader(paper_trading=True)
    with patch.object(trader, "_submit_order", return_value=OrderReceipt(order_id="ord_123", status="FILLED", token_id="yes-token", side="BUY", price=0.51, size=10.0)) as mock_submit:
        _run_evaluation(trader, p_yes=0.55, p_no=0.45, ev_yes=0.16, ev_no=0.01, side="YES")
        # Ensure trade order was placed (submit was called)
        assert mock_submit.call_count == 1


def test_live_mode_emits_no_shadow_event() -> None:
    # 4. Live mode emits no shadow event.
    trader = _setup_mocked_trader(paper_trading=False) # live mode
    _run_evaluation(trader, p_yes=0.55, p_no=0.45, ev_yes=0.16, ev_no=0.01, side="YES")

    assert len(trader.quant_events.events) == 0
    assert trader._baseline_accepted == 0
    assert trader._shadow_would_reject == 0


def test_ev_cap_reason_emitted_correctly() -> None:
    # 5. EV cap reason emitted correctly (and not YES floor if YES prob >= 0.60).
    trader = _setup_mocked_trader(paper_trading=True)
    _run_evaluation(trader, p_yes=0.65, p_no=0.35, ev_yes=0.18, ev_no=0.01, side="YES")

    payload = trader.quant_events.events[0][1]
    assert payload["shadow_would_reject"] is True
    assert payload["shadow_filter_reasons"] == ["ev_cap_toxicity"]


def test_yes_floor_reason_emitted_correctly() -> None:
    # 6. YES floor reason emitted correctly (and not EV cap if EV < 0.15).
    trader = _setup_mocked_trader(paper_trading=True)
    _run_evaluation(trader, p_yes=0.58, p_no=0.42, ev_yes=0.12, ev_no=0.01, side="YES")

    payload = trader.quant_events.events[0][1]
    assert payload["shadow_would_reject"] is True
    assert payload["shadow_filter_reasons"] == ["yes_probability_floor"]


def test_both_reasons_emitted_if_both_conditions_match() -> None:
    # 7. Both reasons emitted if both conditions match.
    trader = _setup_mocked_trader(paper_trading=True)
    _run_evaluation(trader, p_yes=0.58, p_no=0.42, ev_yes=0.16, ev_no=0.01, side="YES")

    payload = trader.quant_events.events[0][1]
    assert payload["shadow_would_reject"] is True
    assert set(payload["shadow_filter_reasons"]) == {"ev_cap_toxicity", "yes_probability_floor"}


def test_required_attribution_fields_exist() -> None:
    # 8. Required attribution fields exist.
    trader = _setup_mocked_trader(paper_trading=True)
    _run_evaluation(trader, p_yes=0.61, p_no=0.39, ev_yes=0.16, ev_no=0.01, side="YES")

    payload = trader.quant_events.events[0][1]
    required_keys = [
        "filter_version",
        "run_id",
        "candidate_trace_id",
        "candidate_instance_id",
        "shadow_decision_id",
        "market",
        "ticker",
        "selected_side",
        "signal_reason",
        "entry_ev",
        "entry_probability",
        "ev_cap_threshold",
        "yes_prob_floor",
        "baseline_approved",
        "shadow_would_reject",
        "shadow_filter_reasons",
        "shadow_outcome",
        "shadow_outcome_pnl",
        "replay_chain_id",
        "paper_trade_replay_key",
        "position_id",
        "timestamp_utc"
    ]
    for key in required_keys:
        assert key in payload
    
    assert payload["filter_version"] == "signal_filter_v1_shadow"
    assert payload["run_id"] == "test_run_123"
    assert payload["shadow_outcome"] is None
    assert payload["shadow_outcome_pnl"] is None
    assert payload["position_id"] is None
    assert "condition-btc" in payload["paper_trade_replay_key"]
