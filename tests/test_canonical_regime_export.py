from __future__ import annotations

import json
from pathlib import Path

import tools.canonical.canonical_regime_export as cre


def _event(event_type: str, timestamp: str, payload: dict, *, run_id: str = "run-1") -> dict:
    return {
        "timestamp_utc": timestamp,
        "event_type": event_type,
        "mode": "paper",
        "run_id": run_id,
        "source_module": "test",
        "schema_version": "1.0",
        "payload": payload,
    }


def _write_jsonl(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")


def _key(index: int, *, candidate: str | None = None) -> str:
    candidate_id = candidate or f"candidate_{index:03d}"
    return f"condition_{index:03d}|178000{index:04d}|ETH|YES|token_{index:03d}", candidate_id


def _open_close(index: int, *, run_id: str = "run-1", candidate: str | None = None, pnl: float = 0.01) -> tuple[dict, dict, str, str]:
    replay_key, candidate_id = _key(index, candidate=candidate)
    open_event = _event(
        "trade_open",
        f"2026-06-06T00:{index % 60:02d}:00Z",
        {
            "paper_trade_replay_key": replay_key,
            "condition_id": replay_key.split("|")[0],
            "epoch_start_ts": replay_key.split("|")[1],
            "asset": "ETH",
            "outcome": "YES",
            "side": "BUY",
            "candidate_id": candidate_id,
            "lifecycle_phase": "OPENING_SCAN",
            "entry_price": 0.50,
            "size": 1.0,
        },
        run_id=run_id,
    )
    close_event = _event(
        "trade_close",
        f"2026-06-06T00:{index % 60:02d}:25Z",
        {
            "paper_trade_replay_key": replay_key,
            "condition_id": replay_key.split("|")[0],
            "epoch_start_ts": replay_key.split("|")[1],
            "asset": "ETH",
            "outcome": "YES",
            "side": "YES",
            "candidate_id": candidate_id,
            "hold_seconds": 25,
            "entry_price": 0.50,
            "exit_price": 0.60 if pnl > 0 else 0.40,
            "size": 1.0,
            "pnl_usdc": pnl,
            "trade_result": "TP" if pnl > 0 else "SL",
            "reason": "take_profit_target_reached" if pnl > 0 else "stop_loss",
        },
        run_id=run_id,
    )
    return open_event, close_event, replay_key, candidate_id


def _decision(index: int, replay_key: str, candidate_id: str, *, regime: str = "COMPRESSION", lifecycle: str = "OPENING_SCAN", run_id: str = "run-1", second: int = 1) -> dict:
    return _event(
        "decision",
        f"2026-06-06T00:{index % 60:02d}:{second:02d}Z",
        {
            "paper_trade_replay_key": replay_key,
            "condition_id": replay_key.split("|")[0],
            "epoch_start_ts": replay_key.split("|")[1],
            "asset": "ETH",
            "side": "YES",
            "outcome": "YES",
            "candidate_id": candidate_id,
            "lifecycle_phase": lifecycle,
            "market_regime": regime,
            "trend_regime": regime,
            "volatility_regime": "NORMAL_VOL",
            "regime_reason": "test",
            "decision_id": f"decision_{index}_{second}",
        },
        run_id=run_id,
    )


def test_n61_reconciliation_and_duplicate_removal(tmp_path: Path) -> None:
    trade_events = []
    decision_events = []
    for index in range(61):
        open_event, close_event, replay_key, candidate_id = _open_close(index)
        trade_events.extend([open_event, close_event])
        decision_events.append(_decision(index, replay_key, candidate_id))

    duplicate_open, duplicate_close, duplicate_key, duplicate_candidate = _open_close(
        0,
        run_id="run-duplicate",
        candidate="candidate_000",
        pnl=0.02,
    )
    trade_events.extend([duplicate_open, duplicate_close])
    decision_events.append(_decision(0, duplicate_key, duplicate_candidate, run_id="run-duplicate"))

    _write_jsonl(tmp_path / "trade_journal" / "2026-06-06.jsonl", trade_events)
    _write_jsonl(tmp_path / "decision_log" / "2026-06-06.jsonl", decision_events)

    result = cre.build_canonical_regime_export(
        trade_journal_dir=tmp_path / "trade_journal",
        decision_log_dir=tmp_path / "decision_log",
        generated_at=cre.parse_utc("2026-06-07T00:00:00Z"),
    )

    assert result.metadata["validation"]["raw_filtered_rows"] == 62
    assert result.metadata["validation"]["duplicate_rows_removed"] == 1
    assert result.metadata["validation"]["canonical_n"] == 61
    assert result.metadata["validation"]["status"] == "PASS"
    assert sum(1 for row in result.rows if row["canonical_retained_flag"] == "true") == 61


def test_direct_join_and_opening_scan_tie_break(tmp_path: Path) -> None:
    open_event, close_event, replay_key, candidate_id = _open_close(1)
    decisions = [
        _decision(1, replay_key, candidate_id, regime="TREND_UP", lifecycle="ACTIVE_INVENTORY_TRADING", second=1),
        _decision(1, replay_key, candidate_id, regime="SIDEWAY", lifecycle="OPENING_SCAN", second=5),
    ]
    _write_jsonl(tmp_path / "trade_journal" / "2026-06-06.jsonl", [open_event, close_event])
    _write_jsonl(tmp_path / "decision_log" / "2026-06-06.jsonl", decisions)

    result = cre.build_canonical_regime_export(
        trade_journal_dir=tmp_path / "trade_journal",
        decision_log_dir=tmp_path / "decision_log",
        generated_at=cre.parse_utc("2026-06-07T00:00:00Z"),
    )

    row = result.rows[0]
    assert row["market_regime"] == "SIDEWAY"
    assert row["regime_join_confidence"] == "DIRECT"
    assert row["regime_join_key"] == "run_id+paper_trade_replay_key+candidate_id"


def test_unknown_fallback_when_decision_missing(tmp_path: Path) -> None:
    open_event, close_event, _, _ = _open_close(2)
    _write_jsonl(tmp_path / "trade_journal" / "2026-06-06.jsonl", [open_event, close_event])
    _write_jsonl(tmp_path / "decision_log" / "2026-06-06.jsonl", [])

    result = cre.build_canonical_regime_export(
        trade_journal_dir=tmp_path / "trade_journal",
        decision_log_dir=tmp_path / "decision_log",
        generated_at=cre.parse_utc("2026-06-07T00:00:00Z"),
    )

    row = result.rows[0]
    assert row["market_regime"] == "UNKNOWN"
    assert row["regime_join_confidence"] == "MISSING"
    assert row["row_quality"] == "MISSING_REGIME"
    assert result.metadata["validation"]["unknown_regime_rate"] == 1.0


def test_freshness_classification() -> None:
    assert cre.classify_source_lag(60 * 60) == "FRESH"
    assert cre.classify_source_lag(3 * 60 * 60) == "STALE"
    assert cre.classify_source_lag(25 * 60 * 60) == "EXPIRED"
