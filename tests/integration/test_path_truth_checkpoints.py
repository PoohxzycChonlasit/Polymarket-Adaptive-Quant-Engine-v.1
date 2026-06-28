from __future__ import annotations

import builtins
import json
import time
from datetime import UTC, datetime
from types import SimpleNamespace

from polymarket.trader import PolymarketTrader
from utils.quant_event_logger import QuantEventLogger


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _position(*, entry_time: datetime | None = None, metadata: dict | None = None):
    entry = entry_time or datetime(2026, 5, 24, 9, 0, 0, tzinfo=UTC)
    return SimpleNamespace(
        position_id="pos-path-1",
        symbol="pm-5m-btc",
        side="BUY",
        entry_price=0.6,
        entry_time=entry.isoformat().replace("+00:00", "Z"),
        size=2.0,
        status="open",
        metadata=metadata
        if metadata is not None
        else {
            "token_id": "token-yes",
            "outcome": "YES",
            "condition_id": "condition-1",
            "epoch_start_ts": int(entry.timestamp()),
            "market_slug": "btc-up-down",
            "lifecycle_phase": "OPENING_SCAN",
        },
    )


def _quant_logger(tmp_path, *, mode: str = "paper", run_id: str = "run-path-test") -> QuantEventLogger:
    return QuantEventLogger(
        base_dir=tmp_path,
        enabled=True,
        mode=mode,
        run_id=run_id,
        now=lambda: datetime(2026, 5, 24, 9, 0, 15, tzinfo=UTC),
    )


def test_path_truth_checkpoint_schedule_has_no_duplicates(tmp_path) -> None:
    trader = PolymarketTrader()
    trader.settings.paper_trading = True
    trader.quant_events = _quant_logger(tmp_path)
    pos = _position()

    trader._path_truth_market_state = lambda _pos: {
        "current_mark_price": 0.66,
        "bid": 0.65,
        "ask": 0.67,
        "spread": 0.02,
        "quote_age_ms": 123,
        "liquidity_state": "ACCEPTABLE",
    }

    trader._maybe_emit_path_truth_checkpoints([pos], now=datetime(2026, 5, 24, 9, 0, 14, tzinfo=UTC))
    trader._maybe_emit_path_truth_checkpoints([pos], now=datetime(2026, 5, 24, 9, 0, 15, tzinfo=UTC))
    trader._maybe_emit_path_truth_checkpoints([pos], now=datetime(2026, 5, 24, 9, 0, 16, tzinfo=UTC))
    trader._maybe_emit_path_truth_checkpoints([pos], now=datetime(2026, 5, 24, 9, 0, 30, tzinfo=UTC))

    rows = _read_jsonl(tmp_path / "path_truth" / "2026-05-24.jsonl")
    assert [row["event_type"] for row in rows] == ["trade_path_checkpoint", "trade_path_checkpoint"]
    assert [row["payload"]["checkpoint_elapsed_s"] for row in rows] == [15, 30]
    assert rows[0]["payload"]["trade_id"] == "pos-path-1"
    assert rows[0]["payload"]["unrealized_pnl"] == 0.12
    assert rows[0]["payload"]["favorable_from_entry"] is True
    assert rows[0]["payload"]["adverse_from_entry"] is False


def test_trade_open_metadata_builder_stores_paper_trade_replay_key() -> None:
    trader = PolymarketTrader()

    metadata = trader._build_trade_position_metadata(
        strategy="ENTER_QUANT",
        signal_strategy="momentum",
        token_id="token-yes",
        outcome="YES",
        entry_ev=0.12,
        confidence=0.77,
        delta_regime="TRENDING",
        condition_id="condition-1",
        epoch_start_ts=1770000000,
        market_slug="btc-up-down",
        lifecycle_phase="OPENING_SCAN",
        ticker="BTC",
    )

    assert metadata["paper_trade_replay_key"] == "condition-1|1770000000|BTC|YES|token-yes"
    assert metadata["token_id"] == "token-yes"
    assert metadata["outcome"] == "YES"
    assert "candidate_id" not in metadata
    assert "decision_id" not in metadata


def test_path_truth_checkpoint_emits_paper_trade_replay_key(tmp_path) -> None:
    trader = PolymarketTrader()
    trader.settings.paper_trading = True
    trader.quant_events = _quant_logger(tmp_path)
    trader._path_truth_market_state = lambda _pos: {}

    pos = _position(metadata={
        "paper_trade_replay_key": "condition-1|1770000000|BTC|YES|token-yes",
        "token_id": "token-yes",
        "outcome": "YES",
        "condition_id": "condition-1",
        "epoch_start_ts": 1770000000,
    })
    trader._maybe_emit_path_truth_checkpoints([pos], now=datetime(2026, 5, 24, 9, 0, 15, tzinfo=UTC))

    rows = _read_jsonl(tmp_path / "path_truth" / "2026-05-24.jsonl")
    assert rows[0]["payload"]["paper_trade_replay_key"] == "condition-1|1770000000|BTC|YES|token-yes"


def test_path_truth_does_not_backfill_missed_checkpoint_with_current_mark(tmp_path) -> None:
    trader = PolymarketTrader()
    trader.settings.paper_trading = True
    trader.quant_events = _quant_logger(tmp_path)
    trader._path_truth_market_state = lambda _pos: {
        "current_mark_price": 0.66,
        "bid": 0.65,
        "ask": 0.67,
        "spread": 0.02,
    }

    trader._maybe_emit_path_truth_checkpoints([_position()], now=datetime(2026, 5, 24, 9, 0, 29, tzinfo=UTC))

    assert not (tmp_path / "path_truth").exists()


def test_path_truth_checkpoint_writer_fail_soft(tmp_path, monkeypatch) -> None:
    logger = _quant_logger(tmp_path)
    real_open = builtins.open

    def locked_open(path, *args, **kwargs):
        if "path_truth" in str(path):
            raise PermissionError("locked path truth")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", locked_open)

    assert logger.log_trade_path_checkpoint({"trade_id": "pos-path-1"}) is False
    assert "path_truth" in logger.disabled_categories


def test_path_truth_checkpoints_are_paper_only(tmp_path) -> None:
    trader = PolymarketTrader()
    original_paper_trading = trader.settings.paper_trading
    trader.settings.paper_trading = False
    trader.quant_events = _quant_logger(tmp_path, mode="live", run_id="run-live-test")

    try:
        trader._maybe_emit_path_truth_checkpoints([_position()], now=datetime(2026, 5, 24, 9, 0, 15, tzinfo=UTC))
    finally:
        trader.settings.paper_trading = original_paper_trading

    assert not (tmp_path / "path_truth").exists()


def test_path_truth_missing_fields_are_null_safe(tmp_path) -> None:
    trader = PolymarketTrader()
    trader.settings.paper_trading = True
    trader.quant_events = _quant_logger(tmp_path)
    trader._path_truth_market_state = lambda _pos: {}

    pos = _position(metadata={})
    trader._maybe_emit_path_truth_checkpoints([pos], now=datetime(2026, 5, 24, 9, 0, 15, tzinfo=UTC))

    rows = _read_jsonl(tmp_path / "path_truth" / "2026-05-24.jsonl")
    payload = rows[0]["payload"]
    assert payload["paper_trade_replay_key"] is None
    assert payload["candidate_id"] is None
    assert payload["decision_id"] is None
    assert payload["condition_id"] is None
    assert payload["current_mark_price"] is None
    assert payload["spread"] is None
    assert payload["unrealized_pnl"] is None


def test_path_truth_shutdown_emits_event_end_without_hanging(tmp_path) -> None:
    trader = PolymarketTrader()
    trader.settings.paper_trading = True
    trader.quant_events = _quant_logger(tmp_path)
    trader.tracker.open_positions = lambda: [_position()]
    trader._path_truth_market_state = lambda _pos: {}

    started = time.monotonic()
    trader.shutdown(join_timeout=0.01)

    assert time.monotonic() - started < 0.5
    rows = _read_jsonl(tmp_path / "path_truth" / "2026-05-24.jsonl")
    assert rows[-1]["payload"]["checkpoint_reason"] == "event_end"
    assert rows[-1]["payload"]["checkpoint_elapsed_s"] == "event_end"
