from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from config.settings import Settings, get_settings
from polymarket.arbitrage import ArbitrageOpportunity
from polymarket.client import BUY, SELL, OrderReceipt, PolymarketClient
from utils.position_tracker import PositionTracker


LOGGER = logging.getLogger(__name__)

ArbSide = Literal["YES", "NO"]


@dataclass(slots=True)
class ArbSizing:
    bankroll: float
    max_cost_pct: float
    max_active_markets: int
    max_total_cost: float
    pair_cost: float
    shares: float
    reason: str = ""


@dataclass(slots=True)
class ArbInventory:
    yes_size: float = 0.0
    no_size: float = 0.0

    @property
    def hedged_size(self) -> float:
        return min(self.yes_size, self.no_size)

    @property
    def unhedged_yes(self) -> float:
        return max(0.0, self.yes_size - self.no_size)

    @property
    def unhedged_no(self) -> float:
        return max(0.0, self.no_size - self.yes_size)

    @property
    def is_balanced(self) -> bool:
        return abs(self.yes_size - self.no_size) < 1e-8


@dataclass(slots=True)
class ArbExecutionResult:
    attempted: bool
    success: bool
    action: str
    reason: str
    pair_id: str = ""
    target_shares: float = 0.0
    yes_filled: float = 0.0
    no_filled: float = 0.0
    unwound_yes: float = 0.0
    unwound_no: float = 0.0
    inventory: ArbInventory = field(default_factory=ArbInventory)
    receipts: list[OrderReceipt] = field(default_factory=list)


class ArbitrageExecutor:
    """Execute same-market YES/NO locked-payout arbitrage without naked exposure."""

    def __init__(
        self,
        client: PolymarketClient,
        *,
        settings: Settings | None = None,
        tracker: PositionTracker | None = None,
    ) -> None:
        self.client = client
        self.settings = settings or get_settings()
        self.tracker = tracker
        self._paper_inventory: dict[str, float] = {}

    def calculate_sizing(self, opp: ArbitrageOpportunity, bankroll: float) -> ArbSizing:
        max_cost_pct, max_active = self._tier_limits(bankroll)
        pair_cost = opp.ask_sum
        max_total_cost = bankroll * max_cost_pct
        if pair_cost <= 0:
            return ArbSizing(bankroll, max_cost_pct, max_active, max_total_cost, pair_cost, 0.0, "invalid_pair_cost")

        shares = min(opp.max_size, max_total_cost / pair_cost)
        if bankroll < 10:
            reason = "micro_bankroll_paper_only_recommended"
        elif shares <= 0:
            reason = "zero_sizing"
        else:
            reason = "ok"

        return ArbSizing(
            bankroll=bankroll,
            max_cost_pct=max_cost_pct,
            max_active_markets=max_active,
            max_total_cost=max_total_cost,
            pair_cost=pair_cost,
            shares=max(0.0, shares),
            reason=reason,
        )

    def execute_buy_both(
        self,
        opp: ArbitrageOpportunity,
        *,
        bankroll: float,
        seconds_remaining: int,
    ) -> ArbExecutionResult:
        pair_id = f"arb-{opp.ticker.lower()}-{uuid.uuid4().hex[:8]}"

        if not self.settings.arb_auto_execute:
            return self._result(False, False, "BUY_BOTH_ARB", "arb_auto_execute_disabled", pair_id, opp)
        if seconds_remaining <= self.settings.arb_force_cancel_seconds_remaining:
            self._cancel_stale_orders()
            return self._result(False, False, "BUY_BOTH_ARB", "force_cancel_window", pair_id, opp)
        if opp.opportunity_type != "BUY_BOTH_ARB" or not opp.executable:
            return self._result(False, False, "BUY_BOTH_ARB", f"not_executable:{opp.reason}", pair_id, opp)
        if seconds_remaining < self.settings.arb_entry_min_seconds_remaining:
            return self._result(False, False, "BUY_BOTH_ARB", "entry_time_cutoff", pair_id, opp)
        if max(opp.yes_ask - opp.yes_bid, opp.no_ask - opp.no_bid) > self.settings.arb_max_leg_spread:
            return self._result(False, False, "BUY_BOTH_ARB", "wide_leg_spread", pair_id, opp)
        if self._active_arb_market_count() >= self._tier_limits(bankroll)[1]:
            return self._result(False, False, "BUY_BOTH_ARB", "max_active_arb_markets", pair_id, opp)

        min_profit = self.settings.arb_min_profit_usdc if self.settings.paper_trading else self.settings.arb_live_min_profit_usdc
        if opp.est_profit < min_profit:
            return self._result(False, False, "BUY_BOTH_ARB", "profit_below_mode_minimum", pair_id, opp)

        sizing = self.calculate_sizing(opp, bankroll)
        if sizing.shares <= 0:
            return self._result(False, False, "BUY_BOTH_ARB", sizing.reason, pair_id, opp)

        LOGGER.info(
            "[ARB_ENTRY] pair=%s ticker=%s shares=%.6f ask_sum=%.4f net_edge=%.4f max_cost=$%.4f",
            pair_id, opp.ticker, sizing.shares, opp.ask_sum, opp.net_edge, sizing.max_total_cost,
        )

        receipts: list[OrderReceipt] = []
        yes_filled = self._place_and_wait(opp.yes_token_id, BUY, opp.yes_ask, sizing.shares, receipts)
        if yes_filled <= 0:
            self._cancel_stale_orders()
            inventory = self.reconcile_inventory(opp)
            return ArbExecutionResult(True, False, "BUY_BOTH_ARB", "yes_leg_not_filled", pair_id, sizing.shares, inventory=inventory, receipts=receipts)

        no_filled = 0.0
        for attempt in range(1, self.settings.arb_second_leg_retry + 2):
            remaining = max(0.0, yes_filled - no_filled)
            if remaining <= 0:
                break
            filled = self._place_and_wait(opp.no_token_id, BUY, opp.no_ask, remaining, receipts)
            no_filled += filled
            if no_filled >= yes_filled:
                break
            LOGGER.warning("[ARB_SECOND_LEG_RETRY] pair=%s attempt=%d yes=%.6f no=%.6f", pair_id, attempt, yes_filled, no_filled)

        unwound_yes = 0.0
        unwound_no = 0.0
        if abs(yes_filled - no_filled) > 1e-8:
            LOGGER.critical(
                "[ARB_PARTIAL_FILL] pair=%s yes=%.6f no=%.6f unwind=%s",
                pair_id, yes_filled, no_filled, self.settings.arb_unwind_on_partial_fill,
            )
            if self.settings.arb_unwind_on_partial_fill:
                if yes_filled > no_filled:
                    unwound_yes = self._unwind_leg(opp.yes_token_id, yes_filled - no_filled, opp.yes_bid, receipts)
                else:
                    unwound_no = self._unwind_leg(opp.no_token_id, no_filled - yes_filled, opp.no_bid, receipts)

        hedged = min(yes_filled - unwound_yes, no_filled - unwound_no)
        if hedged > 0:
            self._record_hedged_pair(opp, pair_id, hedged)

        self._cancel_stale_orders()
        inventory = self.reconcile_inventory(opp)
        success = inventory.is_balanced and hedged > 0
        if not inventory.is_balanced:
            LOGGER.critical(
                "[ARB_UNHEDGED_AFTER_ATTEMPT] pair=%s yes=%.6f no=%.6f",
                pair_id, inventory.yes_size, inventory.no_size,
            )

        return ArbExecutionResult(
            attempted=True,
            success=success,
            action="BUY_BOTH_ARB",
            reason="filled_balanced_pair" if success else "unhedged_after_attempt",
            pair_id=pair_id,
            target_shares=sizing.shares,
            yes_filled=yes_filled,
            no_filled=no_filled,
            unwound_yes=unwound_yes,
            unwound_no=unwound_no,
            inventory=inventory,
            receipts=receipts,
        )

    def execute_exit_arb(
        self,
        opp: ArbitrageOpportunity,
        *,
        inventory: ArbInventory | None = None,
    ) -> ArbExecutionResult:
        pair_id = f"exit-arb-{opp.ticker.lower()}-{uuid.uuid4().hex[:8]}"
        inv = inventory or self.reconcile_inventory(opp)

        if not self.settings.arb_auto_execute:
            return ArbExecutionResult(False, False, "EXIT_ARB", "arb_auto_execute_disabled", pair_id, inventory=inv)
        if opp.opportunity_type != "EXIT_ARB" or opp.exit_net_edge <= 0:
            return ArbExecutionResult(False, False, "EXIT_ARB", f"not_exit_arb:{opp.reason}", pair_id, inventory=inv)
        if not inv.is_balanced or inv.hedged_size <= 0:
            LOGGER.critical(
                "[ARB_EXIT_BLOCKED_UNHEDGED] ticker=%s yes=%.6f no=%.6f",
                opp.ticker, inv.yes_size, inv.no_size,
            )
            return ArbExecutionResult(False, False, "EXIT_ARB", "requires_equal_yes_no_inventory", pair_id, inventory=inv)

        size = min(inv.hedged_size, opp.yes_bid_size, opp.no_bid_size)
        if size <= 0:
            return ArbExecutionResult(False, False, "EXIT_ARB", "zero_exit_size", pair_id, inventory=inv)

        receipts: list[OrderReceipt] = []
        yes_sold = self._place_and_wait(opp.yes_token_id, SELL, opp.yes_bid, size, receipts)
        no_sold = self._place_and_wait(opp.no_token_id, SELL, opp.no_bid, size, receipts)
        self._cancel_stale_orders()
        after = self.reconcile_inventory(opp)
        success = yes_sold == no_sold == size and after.is_balanced

        if not success:
            LOGGER.critical(
                "[ARB_EXIT_INCOMPLETE] pair=%s yes_sold=%.6f no_sold=%.6f remaining_yes=%.6f remaining_no=%.6f",
                pair_id, yes_sold, no_sold, after.yes_size, after.no_size,
            )

        return ArbExecutionResult(
            attempted=True,
            success=success,
            action="EXIT_ARB",
            reason="exit_pair_sold" if success else "exit_incomplete",
            pair_id=pair_id,
            target_shares=size,
            yes_filled=yes_sold,
            no_filled=no_sold,
            inventory=after,
            receipts=receipts,
        )

    def cancel_stale_orders_if_needed(self, seconds_remaining: int) -> None:
        if seconds_remaining <= self.settings.arb_force_cancel_seconds_remaining:
            LOGGER.critical(
                "[ARB_FORCE_CANCEL] seconds_remaining=%ds <= %ds",
                seconds_remaining, self.settings.arb_force_cancel_seconds_remaining,
            )
            self._cancel_stale_orders()

    def reconcile_inventory(self, opp: ArbitrageOpportunity) -> ArbInventory:
        positions = self._safe_positions()
        if not positions:
            return ArbInventory(
                yes_size=self._paper_inventory.get(opp.yes_token_id, 0.0),
                no_size=self._paper_inventory.get(opp.no_token_id, 0.0),
            )

        yes = self._position_size_for_token(positions, opp.yes_token_id)
        no = self._position_size_for_token(positions, opp.no_token_id)
        inventory = ArbInventory(yes_size=yes, no_size=no)
        LOGGER.info("[ARB_RECONCILE] ticker=%s yes=%.6f no=%.6f balanced=%s", opp.ticker, yes, no, inventory.is_balanced)
        return inventory

    def _place_and_wait(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
        receipts: list[OrderReceipt],
    ) -> float:
        if size <= 0:
            return 0.0
        receipt = self.client.place_limit_order(token_id=token_id, price=price, size=size, side=side)
        receipts.append(receipt)
        filled = self._wait_for_fill(receipt, expected_size=size)
        if filled < size:
            self.client.cancel_order(receipt.order_id)
        self._apply_paper_fill(token_id, side, filled)
        return filled

    def _wait_for_fill(self, receipt: OrderReceipt, expected_size: float) -> float:
        if receipt.status.lower() in {"paper", "filled", "matched"}:
            return expected_size

        deadline = time.monotonic() + float(self.settings.arb_leg_fill_timeout_sec)
        while time.monotonic() < deadline:
            order = self._safe_order(receipt.order_id)
            status = str(order.get("status", receipt.status)).lower()
            filled = float(order.get("filled_size", order.get("filled", 0.0)) or 0.0)
            if status in {"filled", "matched"}:
                return filled or expected_size
            if filled > 0:
                return min(filled, expected_size)
            time.sleep(0.25)
        return 0.0

    def _unwind_leg(
        self,
        token_id: str,
        size: float,
        bid_price: float,
        receipts: list[OrderReceipt],
    ) -> float:
        if size <= 0:
            return 0.0
        price = max(0.01, min(0.99, bid_price))
        LOGGER.critical("[ARB_UNWIND] token=%s size=%.6f price=%.4f", token_id, size, price)
        return self._place_and_wait(token_id, SELL, price, size, receipts)

    def _cancel_stale_orders(self) -> None:
        for order in self.client.get_open_orders():
            order_id = str(order.get("id", order.get("order_id", order.get("orderID", ""))))
            if order_id:
                self.client.cancel_order(order_id)

    def _record_hedged_pair(self, opp: ArbitrageOpportunity, pair_id: str, size: float) -> None:
        if self.tracker is None:
            return
        notional_yes = opp.yes_ask * size
        notional_no = opp.no_ask * size
        metadata = {"kind": "arb", "pair_id": pair_id, "ticker": opp.ticker}
        self.tracker.open_position(
            symbol=opp.market_id or f"arb-{opp.ticker.lower()}",
            source="polymarket",
            side="BUY",
            entry_price=opp.yes_ask,
            size=size,
            stop_loss=0.0,
            take_profit=1.0,
            order_id=f"{pair_id}-yes",
            metadata={**metadata, "token_id": opp.yes_token_id, "outcome": "YES", "notional_override": notional_yes},
        )
        self.tracker.open_position(
            symbol=opp.market_id or f"arb-{opp.ticker.lower()}",
            source="polymarket",
            side="BUY",
            entry_price=opp.no_ask,
            size=size,
            stop_loss=0.0,
            take_profit=1.0,
            order_id=f"{pair_id}-no",
            metadata={**metadata, "token_id": opp.no_token_id, "outcome": "NO", "notional_override": notional_no},
        )

    def _active_arb_market_count(self) -> int:
        if self.tracker is None:
            return 0
        markets = {
            p.symbol for p in self.tracker.open_positions()
            if (getattr(p, "metadata", None) or {}).get("kind") == "arb"
        }
        return len(markets)

    def _tier_limits(self, bankroll: float) -> tuple[float, int]:
        if bankroll < 10:
            return 0.05, 0 if not self.settings.paper_trading else 1
        if bankroll < 50:
            return 0.10, self.settings.arb_max_active_markets_small_bankroll
        if bankroll < 100:
            return 0.12, 1
        if bankroll < 1000:
            return 0.08, 2
        return 0.05, 2

    def _safe_order(self, order_id: str) -> dict[str, Any]:
        if hasattr(self.client, "get_order"):
            order = self.client.get_order(order_id)
            return order if isinstance(order, dict) else {}
        return {}

    def _safe_positions(self) -> list[dict[str, Any]]:
        if hasattr(self.client, "get_positions"):
            positions = self.client.get_positions()
            return positions if isinstance(positions, list) else []
        return []

    def _position_size_for_token(self, positions: list[dict[str, Any]], token_id: str) -> float:
        total = 0.0
        for pos in positions:
            asset = str(pos.get("asset_id", pos.get("token_id", pos.get("token", ""))))
            if asset == token_id:
                total += float(pos.get("size", pos.get("balance", 0.0)) or 0.0)
        return total

    def _apply_paper_fill(self, token_id: str, side: str, size: float) -> None:
        if size <= 0 or not self.settings.paper_trading:
            return
        current = self._paper_inventory.get(token_id, 0.0)
        if side == BUY:
            self._paper_inventory[token_id] = current + size
        else:
            self._paper_inventory[token_id] = max(0.0, current - size)

    def _result(
        self,
        attempted: bool,
        success: bool,
        action: str,
        reason: str,
        pair_id: str,
        opp: ArbitrageOpportunity,
    ) -> ArbExecutionResult:
        inventory = self.reconcile_inventory(opp)
        LOGGER.info("[ARB_SKIP] action=%s ticker=%s reason=%s", action, opp.ticker, reason)
        return ArbExecutionResult(attempted, success, action, reason, pair_id, inventory=inventory)
