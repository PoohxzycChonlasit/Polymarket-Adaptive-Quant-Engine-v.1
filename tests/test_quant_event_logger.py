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


def test_quant_event_logger_adds_deterministic_candidate_trace_id(tmp_path: Path) -> None:
    logger = QuantEventLogger(
        base_dir=tmp_path,
        enabled=True,
        mode="paper",
        run_id="run-test",
        schema_version="1.0",
        now=_fixed_now,
    )
    payload = {
        "market_id": "btc-5m-20260508",
        "condition_id": "condition-1",
        "token_id": "token-yes",
        "side": "YES",
        "lifecycle_phase": "OPENING_SCAN",
        "market_epoch_start": 1770000000,
        "candidate_id": "candidate-existing",
    }

    first = QuantEventLogger._candidate_trace_identity_fields(payload, "2026-05-08T12:30:00Z")
    second = QuantEventLogger._candidate_trace_identity_fields(dict(reversed(list(payload.items()))), "2026-05-08T12:30:00Z")

    assert first["candidate_trace_id"] == second["candidate_trace_id"]
    assert first["candidate_trace_id"].startswith("ct_")
    assert first["parent_candidate_trace_id"] == "candidate-existing"
    assert first["trace_link_reason"] == "passive_deterministic_existing_fields"

    original = dict(payload)
    assert logger.log_market_snapshot(payload)
    assert payload == original
    event = _read_jsonl(tmp_path / "market_snapshots" / "2026-05-08.jsonl")[0]
    assert event["payload"]["candidate_trace_id"] == first["candidate_trace_id"]
    assert event["payload"]["market_key"] == "btc-5m-20260508"
    assert event["payload"]["condition_id"] == "condition-1"
    assert event["payload"]["token_id"] == "token-yes"
    assert event["payload"]["side"] == "YES"
    assert event["payload"]["lifecycle_phase"] == "OPENING_SCAN"


def test_quant_event_logger_normalizes_identity_aliases_before_emission(tmp_path: Path) -> None:
    logger = QuantEventLogger(
        base_dir=tmp_path,
        enabled=True,
        mode="paper",
        run_id="run-test",
        schema_version="1.0",
        now=_fixed_now,
    )
    alias_payload = {
        "market_id": "btc-5m-20260508",
        "slug": "btc-5m-slug",
        "conditionId": "condition-alias",
        "tokenId": "token-alias",
        "asset_side": "NO",
        "lifecycle_phase": "OPENING_SCAN",
        "market_epoch_start": 1770000000,
    }
    canonical_payload = {
        "market_key": "btc-5m-20260508",
        "market_slug": "btc-5m-slug",
        "condition_id": "condition-alias",
        "token_id": "token-alias",
        "side": "NO",
        "lifecycle_phase": "OPENING_SCAN",
        "market_epoch_start": 1770000000,
    }

    alias_identity = QuantEventLogger._candidate_trace_identity_fields(alias_payload, "2026-05-08T12:30:00Z")
    canonical_identity = QuantEventLogger._candidate_trace_identity_fields(canonical_payload, "2026-05-08T12:30:00Z")
    assert alias_identity["candidate_trace_id"] == canonical_identity["candidate_trace_id"]

    original = dict(alias_payload)
    assert logger.log_market_snapshot(alias_payload)
    assert alias_payload == original

    event = _read_jsonl(tmp_path / "market_snapshots" / "2026-05-08.jsonl")[0]
    payload = event["payload"]
    assert payload["candidate_trace_id"] == canonical_identity["candidate_trace_id"]
    assert payload["market_key"] == "btc-5m-20260508"
    assert payload["market_slug"] == "btc-5m-slug"
    assert payload["condition_id"] == "condition-alias"
    assert payload["token_id"] == "token-alias"
    assert payload["side"] == "NO"
    assert payload["conditionId"] == "condition-alias"
    assert payload["tokenId"] == "token-alias"
    assert payload["asset_side"] == "NO"


def test_quant_event_logger_trace_identity_handles_missing_fields_safely(tmp_path: Path) -> None:
    logger = QuantEventLogger(base_dir=tmp_path, enabled=True, run_id="run-test", now=_fixed_now)

    assert QuantEventLogger._candidate_trace_identity_fields({"decision": "SKIP"}, "2026-05-08T12:30:00Z") == {}
    assert logger.log_decision({"decision": "SKIP"})

    event = _read_jsonl(tmp_path / "decision_log" / "2026-05-08.jsonl")[0]
    assert event["payload"]["decision"] == "SKIP"
    assert "candidate_trace_id" not in event["payload"]
    assert "condition_id" not in event["payload"]
    assert "token_id" not in event["payload"]
    assert "side" not in event["payload"]


def test_market_observation_key_helper_resolves_epoch_aliases() -> None:
    aliases = (
        ("epoch_start_ts", 1779926400),
        ("epoch_start", "1779926401"),
        ("market_epoch_start_ts", 1779926402),
        ("market_epoch_start", 1779926403),
        ("event_start_ts", 1779926404),
    )

    for field, value in aliases:
        key, source = QuantEventLogger._compute_market_observation_key(
            {
                "condition_id": "condition-1",
                field: value,
            }
        )
        assert key == f"condition-1|{value}"
        assert source == "resolved"


def test_market_observation_key_helper_fails_soft_when_identity_missing() -> None:
    missing_condition_key, missing_condition_reason = QuantEventLogger._compute_market_observation_key(
        {"epoch_start": 1779926400}
    )
    missing_epoch_key, missing_epoch_reason = QuantEventLogger._compute_market_observation_key(
        {"condition_id": "condition-1"}
    )

    assert missing_condition_key == ""
    assert missing_condition_reason == "condition_id_absent"
    assert missing_epoch_key == ""
    assert missing_epoch_reason == "epoch_unresolvable"


def test_market_observation_key_emits_on_market_snapshot_and_decision_only(tmp_path: Path) -> None:
    logger = QuantEventLogger(
        base_dir=tmp_path,
        enabled=True,
        mode="paper",
        run_id="run-test",
        schema_version="1.0",
        now=_fixed_now,
    )

    assert logger.log_market_snapshot(
        {
            "condition_id": "condition-1",
            "epoch_start_ts": 1779926400,
            "yes_token_id": "yes-token",
            "no_token_id": "no-token",
            "outcome": "YES/NO",
        }
    )
    assert logger.log_decision(
        {
            "condition_id": "condition-1",
            "epoch_start": 1779926400,
            "token_id": "yes-token",
            "side": "YES",
        }
    )
    assert logger.log_risk_event(
        {
            "condition_id": "condition-1",
            "market_epoch_start": 1779926400,
            "token_id": "yes-token",
            "side": "YES",
        }
    )
    assert logger.log_trade_open(
        {
            "condition_id": "condition-1",
            "epoch_start_ts": 1779926400,
            "asset": "BTC",
            "token_id": "yes-token",
            "side": "YES",
        }
    )

    market_payload = _read_jsonl(tmp_path / "market_snapshots" / "2026-05-08.jsonl")[0]["payload"]
    decision_payload = _read_jsonl(tmp_path / "decision_log" / "2026-05-08.jsonl")[0]["payload"]
    risk_payload = _read_jsonl(tmp_path / "risk_log" / "2026-05-08.jsonl")[0]["payload"]
    trade_payload = _read_jsonl(tmp_path / "trade_journal" / "2026-05-08.jsonl")[0]["payload"]

    assert market_payload["market_observation_key"] == "condition-1|1779926400"
    assert market_payload["market_observation_key_source"] == "resolved"
    assert "market_observation_key_missing_reason" not in market_payload
    assert decision_payload["market_observation_key"] == "condition-1|1779926400"
    assert decision_payload["market_observation_key_source"] == "resolved"
    assert "market_observation_key_missing_reason" not in decision_payload

    assert "market_observation_key" not in risk_payload
    assert "market_observation_key_source" not in risk_payload
    assert "market_observation_key_missing_reason" not in risk_payload
    assert "market_observation_key" not in trade_payload
    assert "market_observation_key_source" not in trade_payload
    assert "market_observation_key_missing_reason" not in trade_payload


def test_market_observation_key_preserves_candidate_and_replay_keys(tmp_path: Path) -> None:
    logger = QuantEventLogger(
        base_dir=tmp_path,
        enabled=True,
        mode="paper",
        run_id="run-test",
        schema_version="1.0",
        now=_fixed_now,
    )
    payload = {
        "condition_id": "condition-1",
        "epoch_start": 1779926400,
        "asset": "BTC",
        "token_id": "yes-token",
        "side": "YES",
        "lifecycle_phase": "OPENING_SCAN",
    }
    expected_trace = QuantEventLogger._candidate_trace_identity_fields(payload, "2026-05-08T12:30:00Z")[
        "candidate_trace_id"
    ]
    expected_replay_key = QuantEventLogger._compute_paper_trade_replay_key(payload)

    assert logger.log_decision(payload)

    emitted = _read_jsonl(tmp_path / "decision_log" / "2026-05-08.jsonl")[0]["payload"]
    assert emitted["candidate_trace_id"] == expected_trace
    assert emitted["paper_trade_replay_key"] == expected_replay_key
    assert emitted["market_observation_key"] == "condition-1|1779926400"


def test_quant_event_logger_trace_id_remains_observability_only_for_execution(tmp_path: Path) -> None:
    logger = QuantEventLogger(base_dir=tmp_path, enabled=True, mode="live", run_id="run-test", now=_fixed_now)

    assert logger.log_execution({
        "event": "order_intent_approved",
        "token_id": "token-yes",
        "source_market_id": "condition-1",
        "outcome": "YES",
        "side": "BUY",
        "size": 1.0,
        "price": 0.51,
    })

    event = _read_jsonl(tmp_path / "execution_log" / "2026-05-08.jsonl")[0]
    assert event["event_type"] == "execution"
    assert event["mode"] == "live"
    assert event["payload"]["candidate_trace_id"].startswith("ct_")
    assert event["payload"]["event"] == "order_intent_approved"
    assert event["payload"]["size"] == 1.0
    assert event["payload"]["price"] == 0.51


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
