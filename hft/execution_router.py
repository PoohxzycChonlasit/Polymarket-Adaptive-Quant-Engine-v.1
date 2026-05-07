"""
hft/execution_router.py
========================
Intelligent execution router — hunts for best price before resorting to market.

Decision logic:
  1. If signal says use_limit=True → attempt Maker limit order at limit_price
  2. Wait up to LIMIT_WAIT_SEC for fill
  3. If not filled AND (EV > 0.05 AND Edge > 0.05) → fallback to FOK market order
  4. If EV/Edge too low for FOK → cancel limit and skip

Paper mode: simulates all of the above without API calls.
Live mode:  uses PolymarketClient (py-clob-client) with retry logic.

Order tracking:
  - open_orders: dict of order_id → OrderTrack
  - Async background task polls fill status every 2s
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

LOGGER = logging.getLogger(__name__)

# Execution thresholds
LIMIT_WAIT_SEC        = 8.0    # Tier 1/2: wait this long for limit fill
MAKER_FIRST_WAIT_SEC  = 5.0    # Tier 3/4: shorter maker window, then cancel+FOK
FOK_MIN_EV            = 0.05   # minimum EV to allow FOK fallback (Tier 1/2)
FOK_TIER34_MIN_EV     = 0.04   # Tier 3/4: lower bar for FOK (save time, not fees)
FOK_MIN_EDGE          = 0.05   # minimum edge to allow FOK fallback
PRICE_IMPROVE_PCT     = 0.005  # try to improve price by 0.5% vs market


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class ExecutionResult:
    order_id:      str
    status:        str     # "paper" | "filled" | "partial" | "limit_pending"
                           # | "fok_filled" | "rejected" | "error" | "skipped"
    side:          str
    filled_price:  float
    filled_shares: float
    cost_usd:      float
    fee_usd:       float
    strategy:      str = ""
    error_msg:     str = ""


@dataclass
class OrderTrack:
    order_id:    str
    token_id:    str
    side:        str
    price:       float
    shares:      float
    placed_at:   float = field(default_factory=time.time)
    filled:      bool  = False
    cancelled:   bool  = False


# ── Router ─────────────────────────────────────────────────────────────────────

class ExecutionRouter:
    """
    Async execution router.

    Usage (paper):
        router = ExecutionRouter(paper=True)
        result = await router.enter(asset="BTC", side="YES",
                                    market_price=0.52, shares=3.0,
                                    ev=0.08, edge=0.06,
                                    use_limit=True, limit_price=0.50,
                                    yes_token_id="...", no_token_id="...")
    """

    def __init__(self, paper: bool = True) -> None:
        self._paper       = paper
        self._client      = None
        self._open_orders: Dict[str, OrderTrack] = {}

    # ── Public API ─────────────────────────────────────────────────────────────

    async def enter(
        self,
        asset:        str,
        side:         str,
        market_price: float,
        shares:       float,
        ev:           float,
        edge:         float,
        use_limit:    bool  = True,
        limit_price:  float = 0.0,
        yes_token_id: str   = "",
        no_token_id:  str   = "",
        strategy:     str   = "",
        tier:         int   = 1,    # bankroll tier from RiskManager
    ) -> ExecutionResult:
        """
        Route entry through smart limit → FOK pipeline.

        Tier 1/2: standard flow (limit 8s → FOK if EV > 0.05)
        Tier 3/4: maker-first flow (maker limit 5s → cancel → FOK if EV > 0.04)
                  Saves ~0.2% fee per trade at scale — significant at $1K+ bankroll.
        """
        token_id = yes_token_id if side == "YES" else no_token_id
        fee      = self._fee(shares, market_price)

        if self._paper:
            return self._paper_enter(
                side, market_price, shares, cost=shares * market_price,
                fee=fee, use_limit=use_limit, limit_price=limit_price,
                strategy=strategy,
            )

        # ── Tier 3/4: Maker-first with cancel/replace ──────────────────────────
        if tier >= 3 and use_limit and limit_price > 0:
            LOGGER.info(
                "[Router] Tier %d MAKER-FIRST | side=%s maker_price=%.4f "
                "shares=%.4f | waiting %.1fs for fill",
                tier, side, limit_price, shares, MAKER_FIRST_WAIT_SEC,
            )
            result = await self._live_maker_first_enter(
                asset, side, limit_price, shares, token_id, fee, strategy,
                market_price=market_price, ev=ev,
            )
            return result

        # ── Tier 1/2: Standard limit → FOK ────────────────────────────────────
        if use_limit and limit_price > 0:
            result = await self._live_limit_enter(
                asset, side, limit_price, shares, token_id, fee, strategy,
            )
            if result.status == "filled":
                return result
            if ev >= FOK_MIN_EV and edge >= FOK_MIN_EDGE:
                LOGGER.info(
                    "[Router] Limit miss → FOK fallback | EV=%.4f edge=%.4f",
                    ev, edge,
                )
                return await self._live_fok_enter(
                    asset, side, market_price, shares, token_id, fee, strategy,
                )
            return ExecutionResult(
                order_id=result.order_id, status="skipped",
                side=side, filled_price=0.0, filled_shares=0.0,
                cost_usd=0.0, fee_usd=0.0, strategy=strategy,
                error_msg=f"limit_miss_ev_too_low:{ev:.4f}<{FOK_MIN_EV}",
            )

        # No limit → direct FOK if EV sufficient
        if ev >= FOK_MIN_EV and edge >= FOK_MIN_EDGE:
            return await self._live_fok_enter(
                asset, side, market_price, shares, token_id, fee, strategy,
            )

        return ExecutionResult(
            order_id="", status="skipped",
            side=side, filled_price=0.0, filled_shares=0.0,
            cost_usd=0.0, fee_usd=0.0, strategy=strategy,
            error_msg=f"ev_too_low:{ev:.4f}<{FOK_MIN_EV}",
        )

    async def exit(
        self,
        asset:    str,
        side:     str,
        price:    float,
        shares:   float,
        token_id: str = "",
        strategy: str = "",
    ) -> ExecutionResult:
        """Exit an open position."""
        fee = self._fee(shares, price)

        if self._paper:
            proceeds = shares * price
            return ExecutionResult(
                order_id=f"paper-exit-{uuid.uuid4().hex[:8]}",
                status="paper",
                side=side, filled_price=price,
                filled_shares=shares,
                cost_usd=-round(proceeds, 6),
                fee_usd=fee, strategy=strategy,
            )

        return await self._live_exit(asset, side, price, shares, token_id, fee, strategy)

    async def cancel_all_pending(self) -> int:
        """Cancel all open limit orders. Returns count cancelled."""
        if self._paper:
            n = len(self._open_orders)
            self._open_orders.clear()
            return n
        cancelled = 0
        client = self._get_client()
        for oid, track in list(self._open_orders.items()):
            if not track.filled and not track.cancelled:
                try:
                    client.cancel_order(oid)
                    track.cancelled = True
                    cancelled += 1
                    LOGGER.info("[Router] Cancelled order %s", oid[:12])
                except Exception as exc:
                    LOGGER.warning("[Router] Cancel failed %s: %s", oid[:12], exc)
        self._open_orders = {k: v for k, v in self._open_orders.items()
                             if not v.cancelled}
        return cancelled

    # ── Paper simulation ───────────────────────────────────────────────────────

    def _paper_enter(
        self,
        side:        str,
        market_price: float,
        shares:      float,
        cost:        float,
        fee:         float,
        use_limit:   bool,
        limit_price: float,
        strategy:    str,
    ) -> ExecutionResult:
        # Simulate price improvement: limit fills at limit_price if better
        fill_price = market_price
        if use_limit and 0 < limit_price < market_price:
            # Simulate partial fill at limit — assume 60% chance it fills better
            import random
            fill_price = limit_price if random.random() < 0.60 else market_price

        actual_cost = shares * fill_price
        oid = f"paper-{'limit' if use_limit else 'fok'}-{uuid.uuid4().hex[:8]}"

        LOGGER.info(
            "[PAPER] BUY %s | strat=%s price=%.4f→%.4f shares=%.4f cost=$%.4f",
            side, strategy, market_price, fill_price, shares, actual_cost,
        )
        return ExecutionResult(
            order_id=oid, status="paper",
            side=side, filled_price=fill_price,
            filled_shares=shares, cost_usd=round(actual_cost, 6),
            fee_usd=fee, strategy=strategy,
        )

    # ── Tier 3/4 Maker-first with cancel/replace ──────────────────────────────

    async def _live_maker_first_enter(
        self,
        asset:        str,
        side:         str,
        maker_price:  float,
        shares:       float,
        token_id:     str,
        fee:          float,
        strategy:     str,
        market_price: float,
        ev:           float,
    ) -> ExecutionResult:
        """
        Tier 3/4 execution flow:
          1. Post Maker limit at maker_price (passive, earns rebate or zero fee)
          2. Poll for fill for MAKER_FIRST_WAIT_SEC (5s)
          3. If filled → great, log fee saving
          4. If not filled → cancel immediately
             - EV still > FOK_TIER34_MIN_EV → send FOK at market
             - EV degraded → skip (market moved against us)
        """
        from polymarket.client import BUY
        client = self._get_client()

        # Step 1: place maker limit
        try:
            receipt = await asyncio.to_thread(
                client.place_limit_order,
                token_id=token_id,
                price=maker_price,
                size=shares,
                side=BUY,
            )
        except Exception as exc:
            LOGGER.warning("[Router] Maker limit placement failed: %s — falling back to FOK", exc)
            if ev >= FOK_TIER34_MIN_EV:
                return await self._live_fok_enter(
                    asset, side, market_price, shares, token_id, fee, strategy,
                )
            return ExecutionResult(
                order_id="", status="error", side=side,
                filled_price=0.0, filled_shares=0.0,
                cost_usd=0.0, fee_usd=0.0, strategy=strategy,
                error_msg=str(exc),
            )

        if not receipt:
            return ExecutionResult(
                order_id="", status="error", side=side,
                filled_price=0.0, filled_shares=0.0,
                cost_usd=0.0, fee_usd=0.0, strategy=strategy,
                error_msg="maker_receipt_none",
            )

        order_id = receipt.order_id
        track = OrderTrack(
            order_id=order_id, token_id=token_id,
            side=side, price=maker_price, shares=shares,
        )
        self._open_orders[order_id] = track

        LOGGER.info(
            "[Router] Tier3/4 MAKER posted | id=%s price=%.4f | polling %.1fs",
            order_id[:12], maker_price, MAKER_FIRST_WAIT_SEC,
        )

        # Step 2: poll for fill
        filled = await self._poll_fill(order_id, MAKER_FIRST_WAIT_SEC)

        if filled:
            fee_saving = shares * (market_price - maker_price)
            LOGGER.info(
                "[Router] MAKER FILLED | id=%s price=%.4f vs market=%.4f | "
                "fee_saving~=$%.4f",
                order_id[:12], maker_price, market_price, fee_saving,
            )
            return ExecutionResult(
                order_id=order_id, status="filled",
                side=side, filled_price=maker_price,
                filled_shares=shares,
                cost_usd=round(maker_price * shares, 6),
                fee_usd=fee, strategy=strategy,
            )

        # Step 3: not filled — cancel and assess FOK
        LOGGER.info(
            "[Router] Maker NOT filled in %.1fs | cancelling id=%s | "
            "checking FOK eligibility (EV=%.4f threshold=%.4f)",
            MAKER_FIRST_WAIT_SEC, order_id[:12], ev, FOK_TIER34_MIN_EV,
        )
        try:
            await asyncio.to_thread(client.cancel_order, order_id)
            track.cancelled = True
            LOGGER.info("[Router] Maker order %s cancelled", order_id[:12])
        except Exception as exc:
            LOGGER.warning("[Router] Cancel failed for %s: %s", order_id[:12], exc)

        # Step 4: FOK if EV still justifies it
        if ev >= FOK_TIER34_MIN_EV:
            LOGGER.info(
                "[Router] EV=%.4f >= %.4f → sending FOK at market=%.4f",
                ev, FOK_TIER34_MIN_EV, market_price,
            )
            return await self._live_fok_enter(
                asset, side, market_price, shares, token_id, fee, strategy,
            )

        LOGGER.info(
            "[Router] EV=%.4f < %.4f after maker miss → SKIP (market moved against us)",
            ev, FOK_TIER34_MIN_EV,
        )
        return ExecutionResult(
            order_id=order_id, status="skipped",
            side=side, filled_price=0.0, filled_shares=0.0,
            cost_usd=0.0, fee_usd=0.0, strategy=strategy,
            error_msg=f"maker_miss_ev_degraded:{ev:.4f}<{FOK_TIER34_MIN_EV}",
        )

    # ── Live limit ─────────────────────────────────────────────────────────────

    async def _live_limit_enter(
        self,
        asset: str, side: str, price: float, shares: float,
        token_id: str, fee: float, strategy: str,
    ) -> ExecutionResult:
        from polymarket.client import BUY
        client = self._get_client()

        # Slightly above limit price for fill priority (still maker)
        aggressive_price = min(price + PRICE_IMPROVE_PCT, 0.99)

        try:
            receipt = await asyncio.to_thread(
                client.place_limit_order,
                token_id=token_id,
                price=aggressive_price,
                size=shares,
                side=BUY,
            )
            if receipt:
                track = OrderTrack(
                    order_id=receipt.order_id, token_id=token_id,
                    side=side, price=aggressive_price, shares=shares,
                )
                self._open_orders[receipt.order_id] = track

                # Poll for fill
                filled = await self._poll_fill(receipt.order_id, LIMIT_WAIT_SEC)
                if filled:
                    return ExecutionResult(
                        order_id=receipt.order_id, status="filled",
                        side=side, filled_price=aggressive_price,
                        filled_shares=shares,
                        cost_usd=round(aggressive_price * shares, 6),
                        fee_usd=fee, strategy=strategy,
                    )
                # Not filled in time
                LOGGER.info("[Router] Limit order %s not filled in %.1fs",
                            receipt.order_id[:12], LIMIT_WAIT_SEC)
                return ExecutionResult(
                    order_id=receipt.order_id, status="limit_pending",
                    side=side, filled_price=0.0, filled_shares=0.0,
                    cost_usd=0.0, fee_usd=0.0, strategy=strategy,
                )
        except Exception as exc:
            LOGGER.warning("[Router] Limit enter failed: %s", exc)
            return ExecutionResult(
                order_id="", status="error", side=side,
                filled_price=0.0, filled_shares=0.0,
                cost_usd=0.0, fee_usd=0.0, strategy=strategy,
                error_msg=str(exc),
            )

    # ── Live FOK ──────────────────────────────────────────────────────────────

    async def _live_fok_enter(
        self,
        asset: str, side: str, price: float, shares: float,
        token_id: str, fee: float, strategy: str,
    ) -> ExecutionResult:
        from polymarket.client import BUY
        client = self._get_client()

        # FOK: cross the spread aggressively
        fok_price = min(price + 0.005, 0.99)

        for attempt in range(1, 4):
            try:
                receipt = await asyncio.to_thread(
                    client.place_limit_order,
                    token_id=token_id,
                    price=fok_price,
                    size=shares,
                    side=BUY,
                )
                if receipt:
                    LOGGER.info(
                        "[Router] FOK filled | attempt=%d price=%.4f shares=%.4f",
                        attempt, fok_price, shares,
                    )
                    return ExecutionResult(
                        order_id=receipt.order_id, status="fok_filled",
                        side=side, filled_price=fok_price,
                        filled_shares=shares,
                        cost_usd=round(fok_price * shares, 6),
                        fee_usd=fee, strategy=strategy,
                    )
            except Exception as exc:
                LOGGER.warning("[Router] FOK attempt %d failed: %s", attempt, exc)
                if attempt < 3:
                    await asyncio.sleep(1.5)

        return ExecutionResult(
            order_id="", status="error", side=side,
            filled_price=0.0, filled_shares=0.0,
            cost_usd=0.0, fee_usd=0.0, strategy=strategy,
            error_msg="fok_max_retries",
        )

    # ── Live exit ─────────────────────────────────────────────────────────────

    async def _live_exit(
        self,
        asset: str, side: str, price: float, shares: float,
        token_id: str, fee: float, strategy: str,
    ) -> ExecutionResult:
        from polymarket.client import SELL
        client = self._get_client()
        sell_price = max(price - 0.005, 0.01)

        for attempt in range(1, 4):
            try:
                receipt = await asyncio.to_thread(
                    client.place_limit_order,
                    token_id=token_id,
                    price=sell_price,
                    size=shares,
                    side=SELL,
                )
                if receipt:
                    proceeds = sell_price * shares
                    return ExecutionResult(
                        order_id=receipt.order_id, status="filled",
                        side=side, filled_price=sell_price,
                        filled_shares=shares,
                        cost_usd=-round(proceeds, 6),
                        fee_usd=fee, strategy=strategy,
                    )
            except Exception as exc:
                LOGGER.warning("[Router] Exit attempt %d failed: %s", attempt, exc)
                if attempt < 3:
                    await asyncio.sleep(1.5)

        return ExecutionResult(
            order_id="", status="error", side=side,
            filled_price=0.0, filled_shares=0.0,
            cost_usd=0.0, fee_usd=0.0, strategy=strategy,
            error_msg="exit_max_retries",
        )

    # ── Polling ───────────────────────────────────────────────────────────────

    async def _poll_fill(self, order_id: str, timeout: float) -> bool:
        """Poll order status until filled or timeout."""
        deadline = time.monotonic() + timeout
        client   = self._get_client()
        while time.monotonic() < deadline:
            try:
                orders = await asyncio.to_thread(client.get_open_orders)
                open_ids = {o.get("id", o.get("orderID", "")) for o in orders}
                if order_id not in open_ids:
                    track = self._open_orders.get(order_id)
                    if track:
                        track.filled = True
                    return True
            except Exception as exc:
                LOGGER.debug("[Router] Poll error: %s", exc)
            await asyncio.sleep(2.0)
        return False

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fee(shares: float, price: float, rate: float = 0.002) -> float:
        return round(shares * price * rate, 6)

    def _get_client(self):
        if self._client is None:
            from polymarket.client import PolymarketClient
            self._client = PolymarketClient()
            self._client.connect()
        return self._client
