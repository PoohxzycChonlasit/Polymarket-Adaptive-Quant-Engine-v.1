from __future__ import annotations

import builtins
import json
from datetime import datetime, timezone
from pathlib import Path

from utils.quant_event_logger import QuantEventLogger


def _fixed_now() -> datetime:
    return datetime(2026, 5, 8, 12, 30, 0, tzinfo=timezone.utc)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_quant_event_logger_writes_required_jsonl_fields(tmp_path: Path) -> None:
    logger = QuantEventLogger(
        base_dir=tmp_path,
        enabled=True,
        mode="paper",
        run_id="run-test",
        schema_version="1.0",
        now=_fixed_now,
    )

    assert logger.log_market_snapshot({"asset": "BTC", "bid": 0.51})
    assert logger.log_decision({"asset": "ETH", "decision": "SKIP"})
    assert logger.log_execution({"order_id": "paper-1"})
    assert logger.log_trade_open({"market": "btc-5m"})
    assert logger.log_trade_close({"market": "btc-5m"})
    assert logger.log_risk_event({"reason": "drawdown"})
    assert logger.log_system_health({"ws": "Synced"})

    files = [
        tmp_path / "market_snapshots" / "2026-05-08.jsonl",
        tmp_path / "decision_log" / "2026-05-08.jsonl",
        tmp_path / "execution_log" / "2026-05-08.jsonl",
        tmp_path / "trade_journal" / "2026-05-08.jsonl",
        tmp_path / "risk_log" / "2026-05-08.jsonl",
        tmp_path / "system_health" / "2026-05-08.jsonl",
    ]
    for path in files:
        assert path.exists()

    event = _read_jsonl(tmp_path / "market_snapshots" / "2026-05-08.jsonl")[0]
    assert event["timestamp_utc"] == "2026-05-08T12:30:00Z"
    assert event["event_type"] == "market_snapshot"
    assert event["mode"] == "paper"
    assert event["run_id"] == "run-test"
    assert event["source_module"] == "utils.quant_event_logger"
    assert event["schema_version"] == "1.0"
    assert event["payload"]["asset"] == "BTC"


def test_quant_event_logger_disables_only_locked_writer(monkeypatch, tmp_path: Path) -> None:
    real_open = builtins.open

    def locked_market_open(path, *args, **kwargs):
        if "market_snapshots" in str(path):
            raise PermissionError("market log locked")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", locked_market_open)
    logger = QuantEventLogger(base_dir=tmp_path, enabled=True, run_id="run-test", now=_fixed_now)

    assert not logger.log_market_snapshot({"asset": "BTC"})
    assert "market_snapshots" in logger.disabled_categories
    assert logger.log_decision({"asset": "ETH"})
    assert (tmp_path / "decision_log" / "2026-05-08.jsonl").exists()


def test_quant_event_logger_handles_windows_errno_13_on_flush(monkeypatch, tmp_path: Path) -> None:
    real_open = builtins.open

    class LockedFlush:
        def write(self, _text):
            return None

        def flush(self):
            raise OSError(13, "locked")

        def close(self):
            return None

    def locked_flush_open(path, *args, **kwargs):
        if "execution_log" in str(path):
            return LockedFlush()
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", locked_flush_open)
    logger = QuantEventLogger(base_dir=tmp_path, enabled=True, run_id="run-test", now=_fixed_now)

    assert not logger.log_execution({"order_id": "paper-1"})
    assert "execution_log" in logger.disabled_categories
    assert logger.log_system_health({"ok": True})
