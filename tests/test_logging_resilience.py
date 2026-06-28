from __future__ import annotations

import builtins
import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from requests import Timeout

import pytest

import polymarket.observability.realtime_logger as realtime_logger
import utils.logger as logger_utils
from polymarket.observability.realtime_logger import RealtimeLogger, ScanRecord


class _Secret:
    def get_secret_value(self) -> str:
        return ""


def _record() -> ScanRecord:
    now = datetime.now(timezone.utc)
    return ScanRecord(
        timestamp_utc=now.isoformat(),
        date_th=now.strftime("%d/%m/%Y"),
        time_th=now.strftime("%H:%M:%S"),
        asset="BTC",
        feed="paper",
        decision="skip",
        confidence=0.0,
        edge=0.0,
        momentum_pct=0.0,
        score=0.0,
        signal="SKIP",
        position_size=0.0,
        order_id="",
        order_status="",
        skip_reason="test",
        daily_pnl_pct=0.0,
        bankroll=100.0,
    )


def test_setup_logger_continues_console_only_when_log_dir_is_locked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("config.settings.get_settings", lambda: SimpleNamespace(
        telegram_bot_token=_Secret(),
        telegram_chat_id=_Secret(),
    ))
    monkeypatch.setattr(logger_utils.Path, "mkdir", lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("locked")))

    log = logger_utils.setup_logger("INFO", "locked-logs")

    assert log.name == "polytrade_bot"
    assert not any(isinstance(handler, logger_utils.SafeRotatingFileHandler) for handler in logging.getLogger().handlers)


def test_setup_logger_suppresses_http_client_info_logs(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr("config.settings.get_settings", lambda: SimpleNamespace(
        telegram_bot_token=_Secret(),
        telegram_chat_id=_Secret(),
    ))

    logger_utils.setup_logger("INFO", str(tmp_path))

    for logger_name in ("httpx", "httpcore"):
        noisy_logger = logging.getLogger(logger_name)
        assert not noisy_logger.isEnabledFor(logging.INFO)
        assert noisy_logger.isEnabledFor(logging.ERROR)


class _TelegramResponse:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, bool]:
        return {"ok": True}


class _TelegramSession:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    def mount(self, *_args, **_kwargs) -> None:
        return None

    def post(self, *_args, **_kwargs):
        if self.fail:
            raise Timeout("token and message must not leak")
        return _TelegramResponse()

    def close(self) -> None:
        return None


def test_telegram_notifier_emits_async_success_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[dict[str, object]] = []
    monkeypatch.setattr(logger_utils.requests, "Session", lambda: _TelegramSession())

    notifier = logger_utils.TelegramNotifier("secret-token", "secret-chat")
    notifier.send_message(
        "secret message body",
        route="entry",
        source_event_id="trade_open:abc",
        run_id="run-telegram-test",
        telemetry_emit=events.append,
    )
    notifier.close(wait=True)

    assert [event["event_type"] for event in events] == ["telegram_send_success"]
    assert events[0]["route"] == "entry"
    assert events[0]["source_event_id"] == "trade_open:abc"
    assert events[0]["http_status"] == 200
    assert events[0]["telegram_ok"] is True
    assert "secret" not in str(events)


def test_telegram_notifier_emits_async_failure_telemetry_without_message_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[dict[str, object]] = []
    monkeypatch.setattr(logger_utils.requests, "Session", lambda: _TelegramSession(fail=True))

    notifier = logger_utils.TelegramNotifier("secret-token", "secret-chat")
    notifier.send_message(
        "secret message body",
        route="critical",
        source_event_id="incident:def",
        run_id="run-telegram-test",
        telemetry_emit=events.append,
    )
    notifier.close(wait=True)

    assert [event["event_type"] for event in events] == ["telegram_send_failure"]
    assert events[0]["route"] == "critical"
    assert events[0]["exception_class"] == "Timeout"
    assert events[0]["failure_stage"] == "http_post"
    assert "secret" not in str(events)


def test_realtime_logger_disables_csv_when_open_is_permission_denied(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(realtime_logger, "LOG_ROOT", tmp_path)
    real_open = builtins.open

    def locked_open(*args, **kwargs):
        if str(args[0]).endswith(".csv"):
            raise PermissionError("csv locked")
        return real_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", locked_open)
    log = RealtimeLogger(initial_balance=100.0)

    log.log_scan(_record())

    assert log.daily_scans == 1
    assert log._csv_disabled
    assert log._csv_writer is None


def test_realtime_logger_disables_csv_when_write_is_permission_denied(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(realtime_logger, "LOG_ROOT", tmp_path)
    log = RealtimeLogger(initial_balance=100.0)
    log._check_new_day(datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    class LockedWriter:
        def writerow(self, _row):
            raise PermissionError("write locked")

    log._csv_writer = LockedWriter()
    log.log_scan(_record())

    assert log._csv_disabled
    assert log._csv_writer is None


def test_realtime_logger_disables_csv_when_flush_is_permission_denied(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(realtime_logger, "LOG_ROOT", tmp_path)
    log = RealtimeLogger(initial_balance=100.0)
    log._check_new_day(datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    class Writer:
        def writerow(self, _row):
            return None

    class LockedFlush:
        def flush(self):
            raise PermissionError("flush locked")

        def close(self):
            return None

    log._csv_writer = Writer()
    log._csv_file = LockedFlush()
    log.log_scan(_record())

    assert log._csv_disabled
    assert log._csv_file is None


def test_realtime_logger_close_permission_error_does_not_raise(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(realtime_logger, "LOG_ROOT", tmp_path)
    log = RealtimeLogger(initial_balance=100.0)

    class LockedClose:
        def flush(self):
            return None

        def close(self):
            raise PermissionError("close locked")

    log._csv_file = LockedClose()
    log._csv_writer = object()

    log._close_csv()

    assert log._csv_disabled
    assert log._csv_file is None
