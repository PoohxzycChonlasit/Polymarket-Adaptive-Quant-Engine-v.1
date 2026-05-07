from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from polymarket.client import OrderbookSnapshot, PolymarketClient


@dataclass(slots=True)
class ArbitrageOpportunity:
    ticker: str
    market_id: str = ""
    yes_token_id: str = ""
    no_token_id: str = ""
    yes_bid: float = 0.0
    yes_ask: float = 0.0
    yes_bid_size: float = 0.0
    yes_ask_size: float = 0.0
    no_bid: float = 0.0
    no_ask: float = 0.0
    no_bid_size: float = 0.0
    no_ask_size: float = 0.0
    ask_sum: float = 0.0
    bid_sum: float = 0.0
    gross_edge: float = 0.0
    exit_edge: float = 0.0
    net_edge: float = 0.0
    exit_net_edge: float = 0.0
    total_entry_buffer: float = 0.0
    total_exit_buffer: float = 0.0
    max_size: float = 0.0
    est_profit: float = 0.0
    est_exit_profit: float = 0.0
    executable: bool = False
    action: str = "WAIT"
    opportunity_type: Literal["BUY_BOTH_ARB", "EXIT_ARB", "WAIT"] = "WAIT"
    fill_risk: str = "UNKNOWN"
    reason: str = "missing_orderbook"

    @property
    def has_orderbook(self) -> bool:
        return self.yes_ask > 0 and self.no_ask > 0


class ArbitrageScanner:
    def __init__(
        self,
        client: PolymarketClient,
        *,
        min_net_edge: float = 0.005,
        min_profit_usdc: float = 0.02,
        fee_buffer: float = 0.002,
        slippage_buffer: float = 0.003,
        fail_risk_buffer: float = 0.003,
        max_leg_spread: float = 0.08,
    ) -> None:
        self.client = client
        self.min_net_edge = min_net_edge
        self.min_profit_usdc = min_profit_usdc
        self.fee_buffer = fee_buffer
        self.slippage_buffer = slippage_buffer
        self.fail_risk_buffer = fail_risk_buffer
        self.max_leg_spread = max_leg_spread

    def scan(
        self,
        ticker: str,
        yes_token_id: str,
        no_token_id: str,
        market_id: str = "",
    ) -> ArbitrageOpportunity:
        opp = ArbitrageOpportunity(
            ticker=ticker.upper(),
            market_id=market_id,
            yes_token_id=yes_token_id,
            no_token_id=no_token_id,
        )
        if not yes_token_id or not no_token_id:
            opp.reason = "missing_token_ids"
            return opp

        yes_ob = self.client.get_orderbook(yes_token_id)
        no_ob = self.client.get_orderbook(no_token_id)
        self._apply_orderbooks(opp, yes_ob, no_ob)
        self._score(opp, yes_ob, no_ob)
        return opp

    def _apply_orderbooks(
        self,
        opp: ArbitrageOpportunity,
        yes_ob: OrderbookSnapshot,
        no_ob: OrderbookSnapshot,
    ) -> None:
        opp.yes_bid = yes_ob.best_bid
        opp.yes_ask = yes_ob.best_ask
        opp.yes_bid_size = yes_ob.bid_size
        opp.yes_ask_size = yes_ob.ask_size
        opp.no_bid = no_ob.best_bid
        opp.no_ask = no_ob.best_ask
        opp.no_bid_size = no_ob.bid_size
        opp.no_ask_size = no_ob.ask_size

    def _score(
        self,
        opp: ArbitrageOpportunity,
        yes_ob: OrderbookSnapshot,
        no_ob: OrderbookSnapshot,
    ) -> None:
        if not opp.has_orderbook:
            opp.reason = "missing_bid_ask"
            return

        opp.ask_sum = opp.yes_ask + opp.no_ask
        opp.bid_sum = opp.yes_bid + opp.no_bid if opp.yes_bid > 0 and opp.no_bid > 0 else 0.0
        opp.gross_edge = 1.0 - opp.ask_sum
        opp.exit_edge = opp.bid_sum - 1.0 if opp.bid_sum > 0 else 0.0
        opp.total_entry_buffer = self.fee_buffer + self.slippage_buffer + self.fail_risk_buffer
        opp.total_exit_buffer = self.fee_buffer + self.slippage_buffer
        opp.net_edge = opp.gross_edge - opp.total_entry_buffer
        opp.exit_net_edge = opp.exit_edge - opp.total_exit_buffer if opp.bid_sum > 0 else 0.0
        opp.max_size = min(opp.yes_ask_size, opp.no_ask_size)
        opp.est_profit = max(0.0, opp.net_edge * opp.max_size)
        opp.est_exit_profit = max(0.0, opp.exit_net_edge * min(opp.yes_bid_size, opp.no_bid_size))

        widest_spread = max(yes_ob.spread, no_ob.spread)
        if widest_spread <= 0.02 and opp.max_size >= 10:
            opp.fill_risk = "LOW"
        elif widest_spread <= self.max_leg_spread and opp.max_size > 0:
            opp.fill_risk = "MEDIUM"
        else:
            opp.fill_risk = "HIGH"

        if opp.net_edge >= self.min_net_edge and opp.est_profit >= self.min_profit_usdc:
            if widest_spread > self.max_leg_spread:
                opp.action = "SKIP_WIDE"
                opp.reason = f"leg_spread={widest_spread:.4f}>{self.max_leg_spread:.4f}"
                return
            opp.executable = True
            opp.action = "BUY_BOTH_ARB"
            opp.opportunity_type = "BUY_BOTH_ARB"
            opp.reason = "locked_profit_detected"
            return

        if opp.exit_net_edge > 0:
            opp.action = "EXIT_ARB"
            opp.opportunity_type = "EXIT_ARB"
            opp.reason = "bid_sum_above_one_requires_inventory"
            return

        opp.action = "WAIT"
        opp.opportunity_type = "WAIT"
        opp.reason = "net_edge_below_threshold"
