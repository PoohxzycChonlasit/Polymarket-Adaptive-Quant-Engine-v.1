from __future__ import annotations

import logging
import time
from unittest.mock import MagicMock

from polymarket.oracle_price_feed import PolymarketOracleFeed
from polymarket.trader import PolymarketTrader
from utils.logger import SafeStreamHandler


def _install_waiting_oracle_threads(feed: PolymarketOracleFeed) -> None:
    def _wait_until_stopped() -> None:
        feed._stop_event.wait(10)

    feed._run_loop = _wait_until_stopped  # type: ignore[method-assign]
    feed._price_loop = _wait_until_stopped  # type: ignore[method-assign]
    feed._ws_run = _wait_until_stopped  # type: ignore[method-assign]


def test_oracle_start_stop_leaves_no_running_threads() -> None:
    feed = PolymarketOracleFeed(refresh_interval=0.01, timeout=0.1)
    _install_waiting_oracle_threads(feed)

    feed.start()
    assert feed.is_running()

    feed.stop(join_timeout=1.0)

    assert not feed.is_running()
    assert all(thread is None or not thread.is_alive() for thread in feed._background_threads())


def test_oracle_repeated_start_does_not_duplicate_threads() -> None:
    feed = PolymarketOracleFeed(refresh_interval=0.01, timeout=0.1)
    _install_waiting_oracle_threads(feed)

    feed.start()
    first_threads = tuple(feed._background_threads())
    feed.start()

    assert tuple(feed._background_threads()) == first_threads
    assert sum(1 for thread in first_threads if thread and thread.is_alive()) == 3

    feed.stop(join_timeout=1.0)

    feed.start()
    second_threads = tuple(feed._background_threads())
    assert second_threads != first_threads

    feed.stop(join_timeout=1.0)
    assert not feed.is_running()


def test_trader_shutdown_closes_ptb_tracker() -> None:
    trader = PolymarketTrader()
    tracker = MagicMock()
    trader.ptb_tracker = tracker

    trader.shutdown()
    trader.shutdown()

    tracker.close.assert_called_once()


class _ClosedStream:
    def write(self, _message: str) -> None:
        raise ValueError("I/O operation on closed file")

    def flush(self) -> None:
        raise ValueError("I/O operation on closed file")


def test_closed_logging_stream_is_fail_soft_after_shutdown(capsys) -> None:
    logger = logging.getLogger("polymarket.oracle_price_feed")
    handler = SafeStreamHandler(_ClosedStream())
    handler.setLevel(logging.INFO)
    old_propagate = logger.propagate
    logger.propagate = False
    logger.addHandler(handler)

    try:
        feed = PolymarketOracleFeed(refresh_interval=0.01, timeout=0.1)
        _install_waiting_oracle_threads(feed)
        feed.start()
        time.sleep(0.02)
        feed.stop(join_timeout=1.0)
    finally:
        logger.removeHandler(handler)
        logger.propagate = old_propagate

    captured = capsys.readouterr()
    assert "Logging error" not in captured.err
