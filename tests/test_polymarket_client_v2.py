from __future__ import annotations

import unittest
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from polymarket.client import BUY, SELL, PolymarketClient


def _settings(paper: bool = True):
    return SimpleNamespace(
        paper_trading=paper,
        api_retry_attempts=1,
        api_retry_backoff_base=0.0,
        api_circuit_breaker_threshold=99,
        api_circuit_breaker_cooldown=0,
        polymarket_host="https://clob.polymarket.com",
        polymarket_proxy_wallet="0xProxy",
        polymarket_funder="0xFunder",
    )


def _client(paper: bool = True) -> tuple[PolymarketClient, MagicMock]:
    client = PolymarketClient()
    client.settings = _settings(paper=paper)
    mock_clob = MagicMock()
    mock_clob.create_order.return_value = {"signed": True}
    mock_clob.post_order.return_value = {
        "orderID": "ord-1",
        "status": "open",
        "price": "0.42",
        "size": "5",
        "filled_size": "0",
    }
    client._client = mock_clob
    return client, mock_clob


class PolymarketClientV2OrderTests(unittest.TestCase):
    def test_place_limit_order_supports_all_declared_order_types(self) -> None:
        for order_type in ("GTC", "GTD", "FOK", "FAK"):
            client, mock_clob = _client(paper=False)

            receipt = client.place_limit_order(
                token_id="token-1",
                price=0.42,
                size=5.0,
                side=BUY,
                order_type=order_type,
                check_balance=False,
            )

            self.assertEqual(receipt.order_id, "ord-1")
            self.assertEqual(receipt.order_type, order_type)
            mock_clob.post_order.assert_called_once()
            self.assertEqual(mock_clob.post_order.call_args.args[1], order_type)

    def test_post_only_rejected_for_immediate_order_types(self) -> None:
        client, _ = _client(paper=False)

        with self.assertRaises(ValueError):
            client.place_limit_order(
                token_id="token-1",
                price=0.42,
                size=5.0,
                side=BUY,
                order_type="FOK",
                post_only=True,
                check_balance=False,
            )

    def test_get_order_status_normalizes_mock_response(self) -> None:
        client, mock_clob = _client(paper=False)
        mock_clob.get_order.return_value = {
            "id": "ord-2",
            "status": "matched",
            "asset_id": "token-2",
            "side": SELL,
            "price": "0.61",
            "size": "7",
            "filled_size": "7",
            "remaining_size": "0",
            "order_type": "GTC",
        }

        receipt = client.get_order_status("ord-2")

        self.assertEqual(receipt.order_id, "ord-2")
        self.assertEqual(receipt.status, "matched")
        self.assertEqual(receipt.token_id, "token-2")
        self.assertEqual(receipt.side, SELL)
        self.assertEqual(receipt.filled_size, 7.0)
        self.assertEqual(receipt.remaining_size, 0.0)

    def test_wait_for_fill_cancels_gtc_on_timeout(self) -> None:
        client, mock_clob = _client(paper=False)
        mock_clob.get_order.return_value = {
            "id": "ord-1",
            "status": "open",
            "asset_id": "token-1",
            "side": BUY,
            "price": "0.42",
            "size": "5",
            "filled_size": "0",
            "remaining_size": "5",
            "order_type": "GTC",
        }

        receipt = client.place_limit_order(
            token_id="token-1",
            price=0.42,
            size=5.0,
            side=BUY,
            order_type="GTC",
            timeout_sec=0.0,
            check_balance=False,
        )

        mock_clob.cancel.assert_called_once_with("ord-1")
        self.assertEqual(receipt.status, "timeout_cancelled")
        self.assertEqual(receipt.filled_size, 0.0)
        self.assertEqual(receipt.remaining_size, 5.0)

    def test_paper_mode_blocks_direct_live_order_api(self) -> None:
        client, mock_clob = _client(paper=True)

        with self.assertRaises(RuntimeError):
            client.place_limit_order(
                token_id="token-1",
                price=0.42,
                size=5.0,
                side=BUY,
                check_balance=False,
            )

        mock_clob.create_order.assert_not_called()
        mock_clob.post_order.assert_not_called()

    def test_live_order_checks_balance_before_posting(self) -> None:
        client, mock_clob = _client(paper=False)

        with patch.object(client, "get_balance_allowance", return_value={"balance": 1.0, "allowance": 1.0}):
            with self.assertRaises(RuntimeError):
                client.place_limit_order(
                    token_id="token-1",
                    price=0.50,
                    size=5.0,
                    side=BUY,
                    order_type="GTC",
                )

        mock_clob.post_order.assert_not_called()

    def test_get_orderbook_uses_public_market_data_client_without_auth_connect(self) -> None:
        client = PolymarketClient()
        client.settings = _settings()
        raw_book = {
            "market": "condition-1",
            "asset_id": "token-1",
            "timestamp": str(int(time.time() * 1000)),
            "bids": [{"price": "0.51", "size": "10"}],
            "asks": [{"price": "0.53", "size": "12"}],
        }

        with patch("polymarket.client.ClobClient") as clob_cls:
            public_client = MagicMock()
            public_client.get_order_book.return_value = raw_book
            clob_cls.return_value = public_client

            book = client.get_orderbook("token-1")

        clob_cls.assert_called_once_with(host=client.settings.polymarket_host)
        public_client.get_order_book.assert_called_once_with("token-1")
        self.assertEqual(book.condition_id, "condition-1")
        self.assertEqual(book.best_bid, 0.51)
        self.assertEqual(book.best_ask, 0.53)

    def test_get_orderbook_retries_empty_temporary_response(self) -> None:
        client, mock_clob = _client()
        client.settings.api_retry_attempts = 2
        mock_clob.get_order_book.side_effect = [
            {
                "market": "condition-1",
                "asset_id": "token-1",
                "timestamp": str(int(time.time() * 1000)),
                "bids": [],
                "asks": [],
            },
            {
                "market": "condition-1",
                "asset_id": "token-1",
                "timestamp": str(int(time.time() * 1000)),
                "bids": [{"price": "0.48", "size": "7"}],
                "asks": [{"price": "0.50", "size": "9"}],
            },
        ]

        book = client.get_orderbook("token-1")

        self.assertEqual(mock_clob.get_order_book.call_count, 2)
        self.assertEqual(book.best_bid, 0.48)
        self.assertEqual(book.best_ask, 0.50)

    def test_get_orderbook_rejects_stale_book_older_than_three_seconds(self) -> None:
        client, mock_clob = _client()
        stale_ms = int((time.time() - 4.0) * 1000)
        mock_clob.get_order_book.return_value = {
            "market": "condition-1",
            "asset_id": "token-1",
            "timestamp": str(stale_ms),
            "bids": [{"price": "0.48", "size": "7"}],
            "asks": [{"price": "0.50", "size": "9"}],
        }

        with self.assertRaises(RuntimeError) as ctx:
            client.get_orderbook("token-1")

        self.assertIn("stale_orderbook", str(ctx.exception))

    def test_usdc_balance_snapshot_prefers_clob_collateral_source(self) -> None:
        client, _ = _client()
        with patch.object(client, "_fetch_clob_balance", return_value=12.5), \
             patch.object(client, "_fetch_onchain_balance", return_value=99.0):
            snapshot = client.get_usdc_balance_snapshot()
            balance = client.get_usdc_balance()

        self.assertEqual(snapshot.balance, 12.5)
        self.assertEqual(snapshot.source, "clob_collateral")
        self.assertEqual(snapshot.wallet_address, "0xProxy")
        self.assertEqual(balance, 12.5)


if __name__ == "__main__":
    unittest.main()
