from __future__ import annotations

import json
import time
import unittest
from unittest.mock import MagicMock, patch

from crypto_scalper.realtime_feed import (
    CryptoRealtimeFeed,
    LiveTick,
    _binance_parse,
    _bybit_parse,
    _coinbase_parse,
)


def _binance_ticker_msg(
    symbol: str = "BTCUSDT",
    last: str = "65000.00",
    bid: str = "64999.00",
    ask: str = "65001.00",
    volume: str = "1234567890",
    change_pct: str = "1.25",
    ts: int = 1713268800000,
) -> str:
    return json.dumps({
        "e": "24hrTicker",
        "E": ts,
        "s": symbol,
        "c": last,
        "b": bid,
        "a": ask,
        "q": volume,
        "P": change_pct,
    })


def _bybit_ticker_msg(
    symbol: str = "BTCUSDT",
    last: str = "65000.00",
    bid: str = "64999.00",
    ask: str = "65001.00",
    volume: str = "1234567890",
    change_pct: str = "0.0125",
    ts: int = 1713268800000,
) -> str:
    return json.dumps({
        "topic": f"tickers.{symbol}",
        "ts": ts,
        "type": "snapshot",
        "data": {
            "lastPrice": last,
            "bid1Price": bid,
            "ask1Price": ask,
            "turnover24h": volume,
            "price24hPcnt": change_pct,
        },
    })


def _coinbase_ticker_msg(
    product_id: str = "BTC-USD",
    price: str = "65000.00",
    bid: str = "64999.00",
    ask: str = "65001.00",
    volume: str = "1234567890",
    change_pct: str = "1.25",
    ts: str = "2026-04-16T12:00:00Z",
) -> str:
    return json.dumps({
        "channel": "ticker",
        "timestamp": ts,
        "events": [{
            "type": "update",
            "tickers": [{
                "product_id": product_id,
                "price": price,
                "best_bid": bid,
                "best_ask": ask,
                "volume_24_h": volume,
                "price_percent_chg_24_h": change_pct,
            }],
        }],
    })


# ------------------------------------------------------------------
# Parser unit tests
# ------------------------------------------------------------------

class BinanceParserTests(unittest.TestCase):
    def test_parses_valid_ticker(self) -> None:
        raw = _binance_ticker_msg()
        tick = _binance_parse(raw, "BTC/USDT")
        self.assertIsNotNone(tick)
        self.assertEqual(tick.last_price, 65000.0)
        self.assertEqual(tick.bid, 64999.0)
        self.assertEqual(tick.ask, 65001.0)
        self.assertAlmostEqual(tick.spread, 2.0)
        self.assertEqual(tick.change_pct_24h, 1.25)
        self.assertEqual(tick.source, "binance")
        self.assertEqual(tick.symbol, "BTC/USDT")

    def test_returns_none_for_non_ticker_event(self) -> None:
        raw = json.dumps({"e": "trade", "p": "65000"})
        self.assertIsNone(_binance_parse(raw, "BTC/USDT"))

    def test_returns_none_for_malformed_json(self) -> None:
        self.assertIsNone(_binance_parse("not-json", "BTC/USDT"))

    def test_spread_is_never_negative(self) -> None:
        # ask < bid (anomalous) — spread should clamp to 0
        raw = _binance_ticker_msg(bid="65002.00", ask="64998.00")
        tick = _binance_parse(raw, "BTC/USDT")
        self.assertIsNotNone(tick)
        self.assertEqual(tick.spread, 0.0)


class BybitParserTests(unittest.TestCase):
    def test_parses_valid_ticker(self) -> None:
        raw = _bybit_ticker_msg()
        tick = _bybit_parse(raw, "BTC/USDT")
        self.assertIsNotNone(tick)
        self.assertEqual(tick.last_price, 65000.0)
        self.assertEqual(tick.source, "bybit")
        self.assertAlmostEqual(tick.change_pct_24h, 1.25)

    def test_returns_none_for_non_ticker_topic(self) -> None:
        raw = json.dumps({"topic": "orderbook.BTCUSDT", "data": {}})
        self.assertIsNone(_bybit_parse(raw, "BTC/USDT"))

    def test_returns_none_for_malformed_json(self) -> None:
        self.assertIsNone(_bybit_parse("{bad", "BTC/USDT"))


class CoinbaseParserTests(unittest.TestCase):
    def test_parses_valid_ticker(self) -> None:
        raw = _coinbase_ticker_msg()
        tick = _coinbase_parse(raw, "BTC/USD")
        self.assertIsNotNone(tick)
        self.assertEqual(tick.last_price, 65000.0)
        self.assertEqual(tick.bid, 64999.0)
        self.assertEqual(tick.source, "coinbase")
        self.assertEqual(tick.change_pct_24h, 1.25)

    def test_returns_none_when_no_events(self) -> None:
        raw = json.dumps({"channel": "ticker", "timestamp": "2026-04-16T00:00:00Z", "events": []})
        self.assertIsNone(_coinbase_parse(raw, "BTC/USD"))

    def test_returns_none_for_malformed_json(self) -> None:
        self.assertIsNone(_coinbase_parse("oops", "BTC/USD"))


# ------------------------------------------------------------------
# CryptoRealtimeFeed unit tests (no live network calls)
# ------------------------------------------------------------------

class RealtimeFeedTests(unittest.TestCase):
    def _make_feed(self, exchange: str = "binance") -> CryptoRealtimeFeed:
        settings = MagicMock()
        settings.crypto_exchange = exchange
        return CryptoRealtimeFeed(symbol="BTC/USDT", settings=settings)

    def test_get_latest_returns_none_before_start(self) -> None:
        feed = self._make_feed()
        self.assertIsNone(feed.get_latest())

    def test_subscribe_and_callback_invoked(self) -> None:
        feed = self._make_feed()
        received: list[LiveTick] = []
        feed.subscribe(received.append)

        tick = LiveTick(
            symbol="BTC/USDT", source="binance",
            timestamp_utc="2026-04-16T12:00:00Z",
            last_price=65000.0, bid=64999.0, ask=65001.0,
            spread=2.0, volume_24h=1_000_000.0, change_pct_24h=1.25,
        )
        feed._on_tick(tick)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].last_price, 65000.0)

    def test_get_latest_updated_after_on_tick(self) -> None:
        feed = self._make_feed()
        tick = LiveTick(
            symbol="BTC/USDT", source="binance",
            timestamp_utc="2026-04-16T12:00:00Z",
            last_price=66000.0, bid=65999.0, ask=66001.0,
            spread=2.0, volume_24h=500_000.0, change_pct_24h=-0.5,
        )
        feed._on_tick(tick)
        self.assertEqual(feed.get_latest().last_price, 66000.0)

    def test_resolve_exchange_binance(self) -> None:
        feed = self._make_feed("binance")
        url, sub, parser = feed._resolve_exchange()
        self.assertIn("stream.binance.com", url)
        self.assertIsNone(sub)

    def test_resolve_exchange_bybit(self) -> None:
        feed = self._make_feed("bybit")
        url, sub, parser = feed._resolve_exchange()
        self.assertIn("stream.bybit.com", url)
        self.assertIsNotNone(sub)

    def test_resolve_exchange_coinbase(self) -> None:
        feed = self._make_feed("coinbase")
        url, sub, parser = feed._resolve_exchange()
        self.assertIn("coinbase.com", url)
        self.assertIsNotNone(sub)

    def test_resolve_exchange_raises_on_unknown(self) -> None:
        feed = self._make_feed("unknown_exchange")
        with self.assertRaises(ValueError):
            feed._resolve_exchange()

    def test_callback_exception_does_not_crash_feed(self) -> None:
        feed = self._make_feed()
        feed.subscribe(lambda _: (_ for _ in ()).throw(RuntimeError("boom")))  # type: ignore[arg-type]

        tick = LiveTick(
            symbol="BTC/USDT", source="binance",
            timestamp_utc="2026-04-16T12:00:00Z",
            last_price=65000.0, bid=64999.0, ask=65001.0,
            spread=2.0, volume_24h=1_000_000.0, change_pct_24h=0.0,
        )
        # Should not raise
        feed._on_tick(tick)

    def test_is_running_false_before_start(self) -> None:
        feed = self._make_feed()
        self.assertFalse(feed.is_running())

    def test_start_stop_lifecycle(self) -> None:
        """Feed starts a background thread and stop() shuts it down cleanly."""
        feed = self._make_feed("binance")

        async def _fake_stream_noop() -> None:
            import asyncio
            await asyncio.sleep(60)  # blocked — stop_event will interrupt

        with patch.object(feed, "_stream", side_effect=_fake_stream_noop):
            feed.start()
            time.sleep(0.05)  # let thread spin up
            self.assertTrue(feed.is_running())
            feed.stop()
            self.assertFalse(feed.is_running())


if __name__ == "__main__":
    unittest.main()
