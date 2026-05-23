from __future__ import annotations

import logging
import sys
import time
import types
from unittest.mock import MagicMock, patch

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


def test_trader_shutdown_accepts_bounded_join_timeout() -> None:
    trader = PolymarketTrader()
    tracker = MagicMock()
    trader.ptb_tracker = tracker

    with patch("builtins.__import__") as imported:
        imported.side_effect = ImportError("skip module feed shutdown")
        trader.shutdown(join_timeout=0.25)

    tracker.close.assert_called_once_with(join_timeout=0.25)


def test_realtime_shutdown_stops_trader_before_summary_and_restores_console(
    monkeypatch,
) -> None:
    monkeypatch.setitem(sys.modules, "crypto_scalper.live_runner", types.SimpleNamespace(main=lambda: 0))
    monkeypatch.setitem(sys.modules, "polymarket.signal", types.SimpleNamespace(BACKTEST_WIN_RATE=0.5))
    import main

    calls: list[str] = []
    root_log = logging.getLogger()
    handler = logging.StreamHandler()

    class Trader:
        def shutdown(self, *, join_timeout: float = 5.0) -> None:
            calls.append(f"trader.shutdown:{join_timeout}")

        def log_paper_session_summary(self, *, include_runtime_evaluation: bool = True) -> None:
            calls.append(f"trader.summary:{include_runtime_evaluation}")

    class RealtimeLogger:
        def force_save_summary(self) -> None:
            calls.append("realtime.summary")

    def quiet_http_logs() -> None:
        calls.append("quiet_http_logs")

    def stop_scheduler(*, join_timeout: float) -> None:
        calls.append(f"stop_scheduler:{join_timeout}")

    monkeypatch.setattr(main, "quiet_http_client_loggers_for_shutdown", quiet_http_logs)
    monkeypatch.setattr(root_log, "addHandler", lambda added: calls.append("restore_console") if added is handler else None)

    main._shutdown_realtime_resources(
        trader=Trader(),
        rl_logger=RealtimeLogger(),
        console_handlers=[handler],
        root_log=root_log,
        shutdown_requested=True,
        cycle_num=7,
        stop_scheduler=stop_scheduler,
    )

    assert calls == [
        "quiet_http_logs",
        "trader.shutdown:1.0",
        "trader.summary:False",
        "realtime.summary",
        "stop_scheduler:1.0",
        "restore_console",
    ]


def test_realtime_shutdown_path_is_bounded_for_slow_feeds(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "crypto_scalper.live_runner", types.SimpleNamespace(main=lambda: 0))
    monkeypatch.setitem(sys.modules, "polymarket.signal", types.SimpleNamespace(BACKTEST_WIN_RATE=0.5))
    import main

    class Trader:
        def shutdown(self, *, join_timeout: float = 5.0) -> None:
            time.sleep(join_timeout + 0.05)

        def log_paper_session_summary(self, *, include_runtime_evaluation: bool = True) -> None:
            assert include_runtime_evaluation is False

    class RealtimeLogger:
        def force_save_summary(self) -> None:
            return None

    started = time.monotonic()
    main._shutdown_realtime_resources(
        trader=Trader(),
        rl_logger=RealtimeLogger(),
        console_handlers=[],
        root_log=logging.getLogger(),
        shutdown_requested=True,
        cycle_num=1,
        stop_scheduler=lambda *, join_timeout: None,
        shutdown_join_timeout=0.1,
    )

    assert time.monotonic() - started < 1.0


def test_realtime_shutdown_signal_handler_unwinds_immediately(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "crypto_scalper.live_runner", types.SimpleNamespace(main=lambda: 0))
    monkeypatch.setitem(sys.modules, "polymarket.signal", types.SimpleNamespace(BACKTEST_WIN_RATE=0.5))
    import main

    stop_event = MagicMock()
    marked: list[bool] = []
    handler = main._build_realtime_shutdown_signal_handler(stop_event, lambda: marked.append(True))

    started = time.monotonic()
    try:
        handler()
        raise AssertionError("signal handler did not raise KeyboardInterrupt")
    except KeyboardInterrupt:
        pass

    assert marked == [True]
    stop_event.set.assert_called_once()
    assert time.monotonic() - started < 0.1


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
