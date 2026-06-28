from __future__ import annotations

from polymarket.position_manager import (
    PositionAction,
    PositionManagerInput,
    PositionState,
    classify_position_state,
    manage_position,
    should_cancel_if_ev_disappears,
    should_cancel_stale_order,
    should_exit_position,
)


def test_classify_flat_pending_open_yes_open_no() -> None:
    assert classify_position_state() == PositionState.FLAT
    assert classify_position_state(has_pending_entry=True) == PositionState.PENDING_ENTRY
    assert classify_position_state(has_position=True, held_outcome="YES") == PositionState.OPEN_YES
    assert classify_position_state(has_position=True, held_outcome="NO") == PositionState.OPEN_NO


def test_stale_entry_order_cancels() -> None:
    assert should_cancel_stale_order(30, 20)
    decision = manage_position(
        PositionManagerInput(
            state=PositionState.PENDING_ENTRY,
            current_ev=0.04,
            confidence_score=0.70,
            time_remaining_seconds=240,
            entry_order_id="entry-1",
            entry_order_age_seconds=30,
            max_entry_order_age_seconds=20,
        )
    )

    assert decision.action == PositionAction.CANCEL_ENTRY
    assert decision.cancel_order_id == "entry-1"
    assert decision.reason == "stale_entry_order"


def test_ev_disappearing_cancels_pending_entry() -> None:
    assert should_cancel_if_ev_disappears(0.0)
    decision = manage_position(
        PositionManagerInput(
            state=PositionState.PENDING_ENTRY,
            current_ev=-0.01,
            confidence_score=0.70,
            time_remaining_seconds=240,
            entry_order_id="entry-2",
        )
    )

    assert decision.action == PositionAction.CANCEL_ENTRY
    assert decision.cancel_order_id == "entry-2"
    assert decision.reason == "entry_ev_disappeared"


def test_negative_ev_exits_position() -> None:
    should_exit, reason = should_exit_position(
        current_ev=-0.01,
        confidence_score=0.70,
        time_remaining_seconds=180,
    )
    decision = manage_position(
        PositionManagerInput(
            state=PositionState.OPEN_YES,
            current_ev=-0.01,
            confidence_score=0.70,
            time_remaining_seconds=180,
            held_token_id="yes-token",
        )
    )

    assert should_exit
    assert reason == "position_ev_negative"
    assert decision.action == PositionAction.SELL_HELD_TOKEN
    assert decision.reason == "position_ev_negative"


def test_exit_sells_held_token_only() -> None:
    decision = manage_position(
        PositionManagerInput(
            state=PositionState.OPEN_NO,
            current_ev=-0.02,
            confidence_score=0.70,
            time_remaining_seconds=180,
            held_outcome="NO",
            held_token_id="no-token",
        )
    )

    assert decision.action == PositionAction.SELL_HELD_TOKEN
    assert decision.order_side == "SELL"
    assert decision.token_id == "no-token"
    assert decision.use_limit_order


def test_confidence_collapse_exits_position() -> None:
    should_exit, reason = should_exit_position(
        current_ev=0.03,
        confidence_score=0.40,
        time_remaining_seconds=180,
    )
    decision = manage_position(
        PositionManagerInput(
            state=PositionState.OPEN_YES,
            current_ev=0.03,
            confidence_score=0.40,
            time_remaining_seconds=180,
            held_token_id="yes-token",
        )
    )

    assert should_exit
    assert reason == "confidence_collapsed"
    assert decision.action == PositionAction.SELL_HELD_TOKEN
    assert decision.reason == "confidence_collapsed"


def test_stop_loss_and_take_profit_prepare_exit() -> None:
    stop = manage_position(
        PositionManagerInput(
            state=PositionState.OPEN_YES,
            current_ev=0.03,
            confidence_score=0.70,
            time_remaining_seconds=180,
            held_token_id="yes-token",
            stop_loss_hit=True,
        )
    )
    take_profit = manage_position(
        PositionManagerInput(
            state=PositionState.OPEN_YES,
            current_ev=0.03,
            confidence_score=0.70,
            time_remaining_seconds=180,
            held_token_id="yes-token",
            take_profit_hit=True,
        )
    )

    assert stop.state == PositionState.STOP_LOSS_READY
    assert stop.action == PositionAction.SELL_HELD_TOKEN
    assert take_profit.state == PositionState.TAKE_PROFIT_READY
    assert take_profit.action == PositionAction.SELL_HELD_TOKEN


def test_time_remaining_tightens_exit() -> None:
    decision = manage_position(
        PositionManagerInput(
            state=PositionState.OPEN_YES,
            current_ev=0.005,
            confidence_score=0.70,
            time_remaining_seconds=120,
            held_token_id="yes-token",
        )
    )

    assert decision.action == PositionAction.SELL_HELD_TOKEN
    assert decision.reason == "time_ev_tightened"


def test_limit_orders_only() -> None:
    decision = manage_position(
        PositionManagerInput(
            state=PositionState.PENDING_ENTRY,
            current_ev=0.03,
            confidence_score=0.70,
            time_remaining_seconds=180,
            entry_order_type="MARKET",
        )
    )

    assert decision.state == PositionState.BLOCKED_RISK
    assert decision.action == PositionAction.BLOCK
    assert decision.reason == "limit_orders_only"


def test_no_averaging_down_by_default() -> None:
    decision = manage_position(
        PositionManagerInput(
            state=PositionState.OPEN_YES,
            current_ev=0.05,
            confidence_score=0.70,
            time_remaining_seconds=180,
            held_token_id="yes-token",
            add_requested=True,
            position_is_losing=True,
        )
    )

    assert decision.state == PositionState.BLOCKED_RISK
    assert decision.action == PositionAction.BLOCK
    assert decision.reason == "averaging_down_blocked"


def test_reconciliation_unsafe_blocks() -> None:
    decision = manage_position(
        PositionManagerInput(
            state=PositionState.OPEN_YES,
            current_ev=0.05,
            confidence_score=0.70,
            time_remaining_seconds=180,
            reconciliation_safe=False,
        )
    )

    assert decision.state == PositionState.BLOCKED_RECONCILIATION
    assert decision.action == PositionAction.BLOCK
