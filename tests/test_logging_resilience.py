from __future__ import annotations

import builtins
import logging
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import polymarket.realtime_logger as realtime_logger
import utils.logger as logger_utils
from polymarket.realtime_logger import RealtimeLogger, ScanRecord


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
