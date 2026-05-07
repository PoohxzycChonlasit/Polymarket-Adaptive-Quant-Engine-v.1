from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PositionState(str, Enum):
    FLAT = "FLAT"
    PENDING_ENTRY = "PENDING_ENTRY"
    OPEN_YES = "OPEN_YES"
    OPEN_NO = "OPEN_NO"
    TAKE_PROFIT_READY = "TAKE_PROFIT_READY"
    STOP_LOSS_READY = "STOP_LOSS_READY"
    EXITING = "EXITING"
    BLOCKED_RISK = "BLOCKED_RISK"
    BLOCKED_RECONCILIATION = "BLOCKED_RECONCILIATION"


class PositionAction(str, Enum):
    HOLD = "HOLD"
    PLACE_LIMIT_ENTRY = "PLACE_LIMIT_ENTRY"
    CANCEL_ENTRY = "CANCEL_ENTRY"
    SELL_HELD_TOKEN = "SELL_HELD_TOKEN"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class PositionManagerInput:
    state: PositionState | str
    current_ev: float
    confidence_score: float
    time_remaining_seconds: int
    held_outcome: str = ""
    held_token_id: str = ""
    entry_order_id: str = ""
    entry_order_type: str = "LIMIT"
    entry_order_age_seconds: float = 0.0
    max_entry_order_age_seconds: float = 20.0
    stop_loss_hit: bool = False
    take_profit_hit: bool = False
    confidence_floor: float = 0.54
    reconciliation_safe: bool = True
    add_requested: bool = False
    position_is_losing: bool = False
    allow_averaging_down: bool = False
    tier_allows_averaging_down: bool = False


@dataclass(frozen=True, slots=True)
class PositionManagerDecision:
    state: PositionState
    action: PositionAction
    reason: str
    order_side: str = ""
    token_id: str = ""
    cancel_order_id: str = ""
    use_limit_order: bool = True


def _state(value: PositionState | str) -> PositionState:
    if isinstance(value, PositionState):
        return value
    return PositionState[str(value).upper()]


def _exit_decision(position_input: PositionManagerInput, state: PositionState, reason: str) -> PositionManagerDecision:
    return PositionManagerDecision(
        state=state,
        action=PositionAction.SELL_HELD_TOKEN,
        reason=reason,
        order_side="SELL",
        token_id=position_input.held_token_id,
        use_limit_order=True,
    )


def classify_position_state(
    *,
    has_position: bool = False,
    held_outcome: str = "",
    has_pending_entry: bool = False,
    risk_blocked: bool = False,
    reconciliation_safe: bool = True,
) -> PositionState:
    if not reconciliation_safe:
        return PositionState.BLOCKED_RECONCILIATION
    if risk_blocked:
        return PositionState.BLOCKED_RISK
    if has_pending_entry:
        return PositionState.PENDING_ENTRY
    if not has_position:
        return PositionState.FLAT

    outcome = held_outcome.upper()
    if outcome == "YES":
        return PositionState.OPEN_YES
    if outcome == "NO":
        return PositionState.OPEN_NO
    return PositionState.BLOCKED_RISK


def should_cancel_stale_order(
    entry_order_age_seconds: float,
    max_entry_order_age_seconds: float = 20.0,
) -> bool:
    return float(entry_order_age_seconds) >= float(max_entry_order_age_seconds)


def should_cancel_if_ev_disappears(current_ev: float) -> bool:
    return float(current_ev) <= 0.0


def should_exit_position(
    *,
    current_ev: float,
    confidence_score: float,
    confidence_floor: float = 0.54,
    stop_loss_hit: bool = False,
    take_profit_hit: bool = False,
    time_remaining_seconds: int = 300,
) -> tuple[bool, str]:
    if stop_loss_hit:
        return True, "stop_loss_hit"
    if take_profit_hit:
        return True, "take_profit_target_reached"
    if float(current_ev) < 0:
        return True, "position_ev_negative"
    if float(confidence_score) < float(confidence_floor):
        return True, "confidence_collapsed"
    if int(time_remaining_seconds) <= 60:
        return True, "time_exit_tightened"
    if int(time_remaining_seconds) <= 120 and float(current_ev) <= 0.01:
        return True, "time_ev_tightened"
    return False, ""


def manage_position(position_input: PositionManagerInput) -> PositionManagerDecision:
    state = _state(position_input.state)

    if not position_input.reconciliation_safe:
        return PositionManagerDecision(PositionState.BLOCKED_RECONCILIATION, PositionAction.BLOCK, "reconciliation_unsafe")

    if position_input.entry_order_type.upper() != "LIMIT":
        return PositionManagerDecision(PositionState.BLOCKED_RISK, PositionAction.BLOCK, "limit_orders_only")

    if state == PositionState.PENDING_ENTRY:
        if should_cancel_stale_order(position_input.entry_order_age_seconds, position_input.max_entry_order_age_seconds):
            return PositionManagerDecision(
                PositionState.FLAT,
                PositionAction.CANCEL_ENTRY,
                "stale_entry_order",
                cancel_order_id=position_input.entry_order_id,
            )
        if should_cancel_if_ev_disappears(position_input.current_ev):
            return PositionManagerDecision(
                PositionState.FLAT,
                PositionAction.CANCEL_ENTRY,
                "entry_ev_disappeared",
                cancel_order_id=position_input.entry_order_id,
            )
        return PositionManagerDecision(PositionState.PENDING_ENTRY, PositionAction.HOLD, "entry_pending")

    if state not in {PositionState.OPEN_YES, PositionState.OPEN_NO}:
        return PositionManagerDecision(state, PositionAction.HOLD, "no_open_position")

    if position_input.add_requested and position_input.position_is_losing:
        allowed = (
            position_input.current_ev > 0
            and position_input.allow_averaging_down
            and position_input.tier_allows_averaging_down
        )
        if not allowed:
            return PositionManagerDecision(PositionState.BLOCKED_RISK, PositionAction.BLOCK, "averaging_down_blocked")

    should_exit, exit_reason = should_exit_position(
        current_ev=position_input.current_ev,
        confidence_score=position_input.confidence_score,
        confidence_floor=position_input.confidence_floor,
        stop_loss_hit=position_input.stop_loss_hit,
        take_profit_hit=position_input.take_profit_hit,
        time_remaining_seconds=position_input.time_remaining_seconds,
    )
    if should_exit:
        if exit_reason == "stop_loss_hit":
            return _exit_decision(position_input, PositionState.STOP_LOSS_READY, exit_reason)
        if exit_reason == "take_profit_target_reached":
            return _exit_decision(position_input, PositionState.TAKE_PROFIT_READY, exit_reason)
        return _exit_decision(position_input, PositionState.EXITING, exit_reason)

    return PositionManagerDecision(state, PositionAction.HOLD, "hold_position")
