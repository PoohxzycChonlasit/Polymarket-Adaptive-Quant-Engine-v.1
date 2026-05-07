from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from polymarket.client import BUY, SELL


class OrderIntentType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"


@dataclass(frozen=True, slots=True)
class OrderIntent:
    intent_type: OrderIntentType
    token_id: str
    side: str
    price: float
    size: float
    market_id: str = ""
    outcome: str = ""
    position_id: str = ""
    risk_plan_present: bool = False
    risk_approved: bool = False
    reconciliation_safe: bool = True
    lockdown_active: bool = False
    tracked_inventory_size: float = 0.0


@dataclass(frozen=True, slots=True)
class OrderIntentDecision:
    approved: bool
    reason: str


def validate_order_intent(intent: OrderIntent) -> OrderIntentDecision:
    side = str(intent.side).upper()
    if side not in {BUY, SELL}:
        return OrderIntentDecision(False, "invalid_side")
    if not str(intent.token_id or "").strip():
        return OrderIntentDecision(False, "missing_token_id")
    if float(intent.size) <= 0:
        return OrderIntentDecision(False, "non_positive_size")
    if not 0.0 < float(intent.price) < 1.0:
        return OrderIntentDecision(False, "invalid_price")

    if intent.intent_type == OrderIntentType.ENTRY:
        if side != BUY:
            return OrderIntentDecision(False, "entry_must_be_buy")
        if intent.lockdown_active:
            return OrderIntentDecision(False, "risk_mode_lockdown")
        if not intent.reconciliation_safe:
            return OrderIntentDecision(False, "reconciliation_gate_blocked")
        if not intent.risk_plan_present:
            return OrderIntentDecision(False, "missing_risk_plan")
        if not intent.risk_approved:
            return OrderIntentDecision(False, "risk_plan_not_approved")
        outcome = str(intent.outcome or "").upper()
        if outcome and outcome not in {"YES", "NO"}:
            return OrderIntentDecision(False, "invalid_entry_outcome")
        return OrderIntentDecision(True, "entry_approved")

    if side != SELL:
        return OrderIntentDecision(False, "exit_must_be_sell")
    if not intent.position_id:
        return OrderIntentDecision(False, "missing_exit_position")
    if intent.tracked_inventory_size <= 0:
        return OrderIntentDecision(False, "sell_without_tracked_inventory")
    if float(intent.size) > intent.tracked_inventory_size + 1e-9:
        return OrderIntentDecision(False, "sell_exceeds_tracked_inventory")
    return OrderIntentDecision(True, "exit_approved")
