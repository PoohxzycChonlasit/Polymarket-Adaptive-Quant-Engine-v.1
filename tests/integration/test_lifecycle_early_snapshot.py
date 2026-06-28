"""
Lifecycle Early Snapshot Emission v1 tests.
Verifies that lifecycle milestone events are emitted from _phase2_mark_readiness
before any _emit_decision_event fires, with first-call-wins semantics,
paper/live separation, and bounded log volume.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, call, patch

import pytest

from polymarket.trader import PolymarketTrader, TradeOutcome


@pytest.fixture
def trader_with_milestone_enabled():
    trader = PolymarketTrader()
    trader.settings = MagicMock()
    trader.settings.paper_trading = True
    trader.settings.hybrid_phase_v1_enabled = True
    trader.settings.adaptive_entry_max_spread = 0.06
    trader.settings.execution_entry_hard_block_seconds = 35
    trader._connected = True
    trader.quant_events = MagicMock()
    trader.quant_events._with_candidate_trace_identity = MagicMock(side_effect=lambda p, t: p)
    trader.quant_events.log_research_snapshot.return_value = True
    trader.quant_events.log_decision.return_value = True
    return trader


@pytest.fixture
def epoch_now():
    return int(time.time()) // 300 * 300


def _readiness_call(trader, ticker, epoch_start, **flags):
    """Thin wrapper: call _phase2_mark_readiness with sensible defaults."""
    return trader._phase2_mark_readiness(
        ticker=ticker,
        epoch_start=epoch_start,
        epoch_end=epoch_start + 300,
        seconds_remaining=flags.pop("seconds_remaining", 280),
        token_ready=flags.pop("token_ready", False),
        orderbook_ready=flags.pop("orderbook_ready", False),
        nonzero_bidask=flags.pop("nonzero_bidask", False),
        spread_ready=flags.pop("spread_ready", False),
        first_tradable_ready=flags.pop("first_tradable_ready", False),
        first_evaluable_ready=flags.pop("first_evaluable_ready", False),
        liquidity_ready=flags.pop("liquidity_ready", False),
    )


# ---------------------------------------------------------------------------
# 1. Milestone emits BEFORE any _emit_decision_event
# ---------------------------------------------------------------------------

def test_lifecycle_milestone_emits_before_decision_event(trader_with_milestone_enabled, epoch_now):
    """
    _phase2_mark_readiness must emit lifecycle_milestone events independently
    of _emit_decision_event. Milestone events can appear without any decision.
    """
    trader = trader_with_milestone_enabled
    ticker = "BTC"

    # Discovery only — no decision event fired
    _readiness_call(trader, ticker, epoch_now)

    calls = trader.quant_events.log_research_snapshot.call_args_list
    assert len(calls) >= 1, "At least market_discovered milestone must emit"

    # Verify lifecycle_phase field in first call
    payload = calls[0][0][0]
    assert payload.get("lifecycle_phase") == "market_discovered"
    assert payload.get("event_subtype") == "lifecycle_milestone"

    # Confirm no decision event was fired
    trader.quant_events.log_decision.assert_not_called()


# ---------------------------------------------------------------------------
# 2. All 7 milestones emit in progression order
# ---------------------------------------------------------------------------

def test_all_seven_milestones_emit_in_progression(trader_with_milestone_enabled, epoch_now):
    """
    A full milestone progression through all 7 states must emit exactly 7
    research_snapshot events, one per milestone, in order.
    """
    trader = trader_with_milestone_enabled
    ticker = "ETH"
    epoch = epoch_now

    _readiness_call(trader, ticker, epoch, seconds_remaining=299)                                          # market_discovered
    _readiness_call(trader, ticker, epoch, token_ready=True, seconds_remaining=295)                        # token_ready
    _readiness_call(trader, ticker, epoch, token_ready=True, orderbook_ready=True, seconds_remaining=290)  # first_orderbook_seen
    _readiness_call(trader, ticker, epoch, token_ready=True, orderbook_ready=True,
                    nonzero_bidask=True, seconds_remaining=280)                                            # first_nonzero_book
    _readiness_call(trader, ticker, epoch, token_ready=True, orderbook_ready=True,
                    nonzero_bidask=True, spread_ready=True, seconds_remaining=270)                         # first_normalized_book
    _readiness_call(trader, ticker, epoch, token_ready=True, orderbook_ready=True,
                    nonzero_bidask=True, spread_ready=True, first_tradable_ready=True,
                    seconds_remaining=260)                                                                  # first_executable_book
    _readiness_call(trader, ticker, epoch, token_ready=True, orderbook_ready=True,
                    nonzero_bidask=True, spread_ready=True, first_tradable_ready=True,
                    first_evaluable_ready=True, seconds_remaining=250)                                     # first_decision_evaluable

    calls = trader.quant_events.log_research_snapshot.call_args_list
    phases = [c[0][0]["lifecycle_phase"] for c in calls]

    expected_order = [
        "market_discovered",
        "token_ready",
        "first_orderbook_seen",
        "first_nonzero_book",
        "first_normalized_book",
        "first_executable_book",
        "first_decision_evaluable",
    ]
    assert phases == expected_order, f"Expected {expected_order}, got {phases}"


# ---------------------------------------------------------------------------
# 3. First-call-wins — repeated calls do NOT re-emit the same milestone
# ---------------------------------------------------------------------------

def test_lifecycle_milestone_first_call_wins_no_repeat_emission(trader_with_milestone_enabled, epoch_now):
    """
    Calling _phase2_mark_readiness multiple times with token_ready=True must
    emit the token_ready milestone only ONCE, never on subsequent calls.
    """
    trader = trader_with_milestone_enabled
    ticker = "BTC"
    epoch = epoch_now

    for _ in range(5):
        _readiness_call(trader, ticker, epoch, token_ready=True, seconds_remaining=280)

    calls = trader.quant_events.log_research_snapshot.call_args_list
    token_ready_calls = [c for c in calls if c[0][0].get("lifecycle_phase") == "token_ready"]
    assert len(token_ready_calls) == 1, (
        f"token_ready milestone must emit exactly once; got {len(token_ready_calls)}"
    )


def test_lifecycle_milestone_total_events_bounded_per_epoch(trader_with_milestone_enabled, epoch_now):
    """
    No matter how many cycles run, total milestone events per (ticker, epoch) must
    never exceed 7 (one per milestone).
    """
    trader = trader_with_milestone_enabled
    ticker = "BTC"
    epoch = epoch_now

    # Simulate 20 cycles — all flags True after first few cycles
    for i in range(20):
        _readiness_call(
            trader, ticker, epoch,
            token_ready=True,
            orderbook_ready=True,
            nonzero_bidask=True,
            spread_ready=True,
            first_tradable_ready=True,
            first_evaluable_ready=True,
            seconds_remaining=max(1, 280 - i * 10),
        )

    calls = trader.quant_events.log_research_snapshot.call_args_list
    assert len(calls) <= 7, f"Must emit at most 7 milestone events; got {len(calls)}"


# ---------------------------------------------------------------------------
# 4. Milestone timestamps are monotonically non-decreasing
# ---------------------------------------------------------------------------

def test_lifecycle_milestone_seconds_since_open_increases(trader_with_milestone_enabled, epoch_now):
    """
    seconds_since_market_open in successive milestones must be non-decreasing
    (market time only moves forward within an epoch).
    """
    trader = trader_with_milestone_enabled
    ticker = "BTC"
    epoch = epoch_now

    _readiness_call(trader, ticker, epoch, seconds_remaining=290)
    _readiness_call(trader, ticker, epoch, token_ready=True, seconds_remaining=280)
    _readiness_call(trader, ticker, epoch, token_ready=True, orderbook_ready=True, seconds_remaining=270)

    calls = trader.quant_events.log_research_snapshot.call_args_list
    since_open_values = [c[0][0]["seconds_since_market_open"] for c in calls]

    for i in range(1, len(since_open_values)):
        assert since_open_values[i] >= since_open_values[i - 1], (
            f"seconds_since_market_open must be non-decreasing: {since_open_values}"
        )


# ---------------------------------------------------------------------------
# 5. Paper/live separation — no emission when flag disabled
# ---------------------------------------------------------------------------

def test_lifecycle_milestone_no_emission_when_flag_disabled(epoch_now):
    """
    When hybrid_phase_v1_enabled=False, no lifecycle_milestone events must emit.
    """
    trader = PolymarketTrader()
    trader.settings = MagicMock()
    trader.settings.paper_trading = True
    trader.settings.hybrid_phase_v1_enabled = False  # disabled
    trader.settings.adaptive_entry_max_spread = 0.06
    trader.settings.execution_entry_hard_block_seconds = 35
    trader._connected = True
    trader.quant_events = MagicMock()
    trader.quant_events._with_candidate_trace_identity = MagicMock(side_effect=lambda p, t: p)
    trader.quant_events.log_research_snapshot.return_value = True

    _readiness_call(trader, "BTC", epoch_now, token_ready=True, seconds_remaining=280)

    milestone_calls = [
        c for c in trader.quant_events.log_research_snapshot.call_args_list
        if c[0][0].get("event_subtype") == "lifecycle_milestone"
    ]
    assert milestone_calls == [], "No lifecycle_milestone events when hybrid_phase_v1_enabled=False"


# ---------------------------------------------------------------------------
# 6. Existing _emit_decision_event behavior unchanged
# ---------------------------------------------------------------------------

def test_existing_decision_emission_still_works(trader_with_milestone_enabled, epoch_now):
    """
    _emit_decision_event must still call log_decision and log_research_snapshot
    as before — lifecycle milestone emission must not interfere.
    """
    trader = trader_with_milestone_enabled

    # First emit some milestones
    _readiness_call(trader, "BTC", epoch_now, token_ready=True)

    # Reset call counts to isolate decision event check
    trader.quant_events.log_decision.reset_mock()
    trader.quant_events.log_research_snapshot.reset_mock()
    trader.quant_events.log_research_snapshot.return_value = True
    trader.quant_events.log_risk_event = MagicMock(return_value=True)

    outcome = TradeOutcome(
        market_id="pm-5m-btc-001",
        question="Will BTC close above...",
        decision="skip",
        confidence=0.5,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason="confidence_too_low",
        display={"seconds_remaining": 100, "market_epoch_start": epoch_now},
    )
    trader._emit_decision_event(outcome, ticker="BTC")

    trader.quant_events.log_decision.assert_called_once()


# ---------------------------------------------------------------------------
# 7. Milestone payload contains required fields
# ---------------------------------------------------------------------------

def test_lifecycle_milestone_payload_contains_required_fields(trader_with_milestone_enabled, epoch_now):
    """
    Every lifecycle_milestone event must include all 8 required fields.
    """
    trader = trader_with_milestone_enabled
    _readiness_call(trader, "BTC", epoch_now, token_ready=True, seconds_remaining=270)

    calls = [
        c for c in trader.quant_events.log_research_snapshot.call_args_list
        if c[0][0].get("lifecycle_phase") == "token_ready"
    ]
    assert len(calls) == 1
    payload = calls[0][0][0]

    required = [
        "event_subtype",
        "lifecycle_phase",
        "seconds_since_market_open",
        "readiness_state",
        "dominant_latency_stage_so_far",
        "lifecycle_latency_classification_so_far",
        "readiness_confidence",
        "market_epoch_start",
    ]
    for field in required:
        assert field in payload, f"Required field '{field}' missing from milestone payload"

    assert payload["event_subtype"] == "lifecycle_milestone"
    assert payload["lifecycle_phase"] == "token_ready"
    assert payload["seconds_since_market_open"] >= 0
    assert payload["market_epoch_start"] == epoch_now


# ---------------------------------------------------------------------------
# 8. Milestones isolated per epoch — different epoch gets fresh emission
# ---------------------------------------------------------------------------

def test_lifecycle_milestone_separate_epochs_emit_independently(trader_with_milestone_enabled):
    """
    Two distinct (ticker, epoch) pairs each emit their own full milestone sequence.
    Milestones from epoch A must not suppress emission in epoch B.
    """
    trader = trader_with_milestone_enabled
    epoch_a = int(time.time()) // 300 * 300
    epoch_b = epoch_a + 300

    _readiness_call(trader, "BTC", epoch_a, token_ready=True, seconds_remaining=280)
    _readiness_call(trader, "BTC", epoch_b, token_ready=True, seconds_remaining=280)

    token_ready_calls = [
        c for c in trader.quant_events.log_research_snapshot.call_args_list
        if c[0][0].get("lifecycle_phase") == "token_ready"
    ]
    # Should have one per epoch
    assert len(token_ready_calls) == 2, (
        "token_ready must emit once per epoch, independently"
    )
    epochs_seen = {c[0][0]["market_epoch_start"] for c in token_ready_calls}
    assert epoch_a in epochs_seen
    assert epoch_b in epochs_seen
