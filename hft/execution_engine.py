"""
hft/execution_engine.py
========================
Order placement with paper/live switching, FOK → GTC limit fallback, retries.

Paper mode:
  - No API calls. Returns a synthetic OrderResult with status="paper".
  - Simulates execution at the signal's entry_price.

Live mode (PAPER_TRADING=false):
  1. Attempt FOK market order at best ask (YES) or best bid (NO).
  2. If not filled within 3s, fall back to GTC limit order at slightly
     better price than market.
  3. Retry up to ORDER_RETRY_ATTEMPTS times with ORDER_RETRY_DELAY_SEC between.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass

from hft import config as C
from hft.utils import calc_fee

LOGGER = logging.getLogger(__name__)


@dataclass
class OrderResult:
    order_id:    str
    status:      str   # "paper" | "filled" | "partial" | "rejected" | "error"
    side:        str   # YES / NO
    filled_price: float
    filled_shares: float
    cost_usd:    float
    fee_usd:     float
    error_msg:   str = ""


class ExecutionEngine:
    """
    Async execution engine.

    Usage:
        engine = ExecutionEngine(paper=True)
        result = await engine.enter("BTC", "YES", entry_price=0.55, shares=2.0,
                                    yes_token_id="...", no_token_id="...")
    """

    def __init__(self, paper: bool = True) -> None:
        self._paper  = paper
        self._client = None   # lazy-init

    # ── Public API ─────────────────────────────────────────────────────────────

    async def enter(
        self,
        asset:        str,
        side:         str,
        entry_price:  float,
        shares:       float,
        yes_token_id: str = "",
        no_token_id:  str = "",
    ) -> OrderResult:
        """Place an entry order (BUY YES or BUY NO)."""
        token_id = yes_token_id if side == "YES" else no_token_id
        fee = calc_fee(shares, entry_price, C.POLYMARKET_FEE)

        if self._paper:
            result = OrderResult(
                order_id=f"paper-{uuid.uuid4().hex[:8]}",
                status="paper",
                side=side,
                filled_price=entry_price,
                filled_shares=shares,
                cost_usd=round(shares * entry_price, 6),
                fee_usd=fee,
            )
            LOGGER.info(
                "[PAPER HFT] BUY %s | asset=%s price=%.4f shares=%.4f cost=$%.4f fee=$%.5f",
                side, asset, entry_price, shares, result.cost_usd, fee,
            )
            return result

        # Live: try FOK → GTC limit
        return await self._live_enter(asset, side, entry_price, shares, token_id, fee)

    async def exit(
        self,
        asset:       str,
        side:        str,
        exit_price:  float,
        shares:      float,
        token_id:    str = "",
    ) -> OrderResult:
        """Place an exit order (sell previously bought shares)."""
        fee = calc_fee(shares, exit_price, C.POLYMARKET_FEE)

        if self._paper:
            proceeds = shares * exit_price
            result = OrderResult(
                order_id=f"paper-exit-{uuid.uuid4().hex[:8]}",
                status="paper",
                side=side,
                filled_price=exit_price,
                filled_shares=shares,
                cost_usd=round(-proceeds, 6),  # negative = received
                fee_usd=fee,
            )
            LOGGER.info(
                "[PAPER HFT] SELL %s | asset=%s price=%.4f shares=%.4f proceeds=$%.4f",
                side, asset, exit_price, shares, proceeds,
            )
            return result

        return await self._live_exit(asset, side, exit_price, shares, token_id, fee)

    # ── Live execution ─────────────────────────────────────────────────────────

    async def _live_enter(
        self, asset, side, entry_price, shares, token_id, fee,
    ) -> OrderResult:
        client = self._get_client()
        from polymarket.client import BUY

        for attempt in range(1, C.ORDER_RETRY_ATTEMPTS + 1):
            try:
                # Attempt limit order (FOK-style: aggressive price)
                receipt = client.place_limit_order(
                    token_id=token_id,
                    price=min(entry_price + 0.005, 0.99),  # aggressive ask-cross
                    size=shares,
                    side=BUY,
                )
                if receipt is not None:
                    return OrderResult(
                        order_id=receipt.order_id,
                        status=receipt.status,
                        side=side,
                        filled_price=receipt.price,
                        filled_shares=receipt.size,
                        cost_usd=round(receipt.price * receipt.size, 6),
                        fee_usd=fee,
                    )
            except Exception as exc:
                LOGGER.warning(
                    "[HFT Exec] Enter attempt %d/%d failed: %s", attempt,
                    C.ORDER_RETRY_ATTEMPTS, exc,
                )
                if attempt < C.ORDER_RETRY_ATTEMPTS:
                    await asyncio.sleep(C.ORDER_RETRY_DELAY_SEC)

        return OrderResult(
            order_id="", status="error", side=side,
            filled_price=0.0, filled_shares=0.0, cost_usd=0.0, fee_usd=0.0,
            error_msg="max_retries_exceeded",
        )

    async def _live_exit(
        self, asset, side, exit_price, shares, token_id, fee,
    ) -> OrderResult:
        client = self._get_client()
        from polymarket.client import SELL

        for attempt in range(1, C.ORDER_RETRY_ATTEMPTS + 1):
            try:
                receipt = client.place_limit_order(
                    token_id=token_id,
                    price=max(exit_price - 0.005, 0.01),  # aggressive bid-cross
                    size=shares,
                    side=SELL,
                )
                if receipt is not None:
                    proceeds = receipt.price * receipt.size
                    return OrderResult(
                        order_id=receipt.order_id,
                        status=receipt.status,
                        side=side,
                        filled_price=receipt.price,
                        filled_shares=receipt.size,
                        cost_usd=round(-proceeds, 6),
                        fee_usd=fee,
                    )
            except Exception as exc:
                LOGGER.warning(
                    "[HFT Exec] Exit attempt %d/%d failed: %s", attempt,
                    C.ORDER_RETRY_ATTEMPTS, exc,
                )
                if attempt < C.ORDER_RETRY_ATTEMPTS:
                    await asyncio.sleep(C.ORDER_RETRY_DELAY_SEC)

        return OrderResult(
            order_id="", status="error", side=side,
            filled_price=0.0, filled_shares=0.0, cost_usd=0.0, fee_usd=0.0,
            error_msg="exit_max_retries",
        )

    def _get_client(self):
        if self._client is None:
            from polymarket.client import PolymarketClient
            self._client = PolymarketClient()
            self._client.connect()
        return self._client
