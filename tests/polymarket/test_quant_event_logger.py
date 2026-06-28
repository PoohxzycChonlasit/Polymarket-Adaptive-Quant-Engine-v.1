from __future__ import annotations

import builtins
import json
from datetime import datetime, timezone
from pathlib import Path

from config.settings import get_settings
from utils.quant_event_logger import QuantEventLogger


def _fixed_now() -> datetime:
    return datetime(2026, 5, 8, 12, 30, 0, tzinfo=timezone.utc)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


DISPLAY_ONLY_KEYS = [
    "adaptive_cutoff_denied_reason",
    "ask_price",
    "best_market",
    "best_side",
    "book_to_tradable_seconds",
    "clob_consecutive_failures",
    "clob_last_error_category",
    "clob_last_error_class",
    "delta_multiplier",
    "delta_regime",
    "depth_ready",
    "discovery_to_book_seconds",
    "distance_from_ptb_pct",
    "epoch_end_ts",
    "epoch_start_ts",
    "final_size",
    "frequency_multiplier",
    "last_successful_orderbook_age_ms",
    "liquidity_ready",
    "min_ev",
    "mode",
    "model_p_no",
    "model_p_yes",
    "no_orderbook_age_ms",
    "p_no",
    "p_yes",
    "price_change_pct",
    "price_velocity",
    "realized_volatility",
    "risk_plan_zero_diagnostics",
    "score",
    "total_discovery_to_tradable_seconds",
    "yes_orderbook_age_ms",
]


def _display_payload() -> dict:
    return {
        "adaptive_cutoff_denied_reason": "test_reason",
        "ask_price": 0.55,
        "best_market": "btc-5m",
        "best_side": "YES",
        "book_to_tradable_seconds": 12,
        "clob_consecutive_failures": 0,
        "clob_last_error_category": "NONE",
        "clob_last_error_class": "NONE",
        "delta_multiplier": 1.5,
        "delta_regime": "UP",
        "depth_ready": True,
        "discovery_to_book_seconds": 5,
        "distance_from_ptb_pct": 0.02,
        "epoch_end_ts": 1770000000,
        "epoch_start_ts": 1769999700,
        "final_size": 20.0,
        "frequency_multiplier": 1.0,
        "last_successful_orderbook_age_ms": 350,
        "liquidity_ready": True,
        "min_ev": 0.01,
        "mode": "paper",
        "model_p_no": 0.35,
        "model_p_yes": 0.65,
        "no_orderbook_age_ms": 120,
        "p_no": 0.38,
        "p_yes": 0.62,
        "price_change_pct": 0.005,
        "price_velocity": 0.0001,
        "realized_volatility": 0.012,
        "risk_plan_zero_diagnostics": {"reason": "zero_budget"},
        "score": 45.2,
        "total_discovery_to_tradable_seconds": 15,
        "yes_orderbook_age_ms": 110,
    }


def _decision_payload_with_display() -> dict:
    display = _display_payload()
    return {
        "ticker": "BTC",
        "decision_type": "skipped",
        "display": display,
        **display,
    }


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


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


def test_slim_decision_logging_default_preserves_display(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("SLIM_DECISION_LOGGING", raising=False)
    _reset_settings_cache()

    logger = QuantEventLogger(base_dir=tmp_path, enabled=True, run_id="run-test", now=_fixed_now)
    payload = _decision_payload_with_display()

    try:
        assert logger.log_decision(payload)
    finally:
        _reset_settings_cache()

    emitted = _read_jsonl(tmp_path / "decision_log" / "2026-05-08.jsonl")[0]["payload"]
    assert emitted["display"] == payload["display"]
    for key in DISPLAY_ONLY_KEYS:
        assert emitted[key] == payload[key]


def test_slim_decision_logging_enabled_removes_display_and_keeps_promoted_keys(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SLIM_DECISION_LOGGING", "true")
    _reset_settings_cache()

    logger = QuantEventLogger(base_dir=tmp_path, enabled=True, run_id="run-test", now=_fixed_now)
    payload = _decision_payload_with_display()
    original_display = dict(payload["display"])

    try:
        assert logger.log_decision(payload)
    finally:
        _reset_settings_cache()

    emitted = _read_jsonl(tmp_path / "decision_log" / "2026-05-08.jsonl")[0]["payload"]
    assert "display" not in emitted
    assert payload["display"] == original_display
    for key in DISPLAY_ONLY_KEYS:
        assert emitted[key] == payload[key]


def test_slim_decision_logging_preserves_display_for_non_decision_categories(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SLIM_DECISION_LOGGING", "true")
    _reset_settings_cache()

    logger = QuantEventLogger(base_dir=tmp_path, enabled=True, run_id="run-test", now=_fixed_now)
    display = {"trend_regime": "up", "score": 42}

    try:
        assert logger.log_market_snapshot({"asset": "BTC", "display": display})
        assert logger.log_risk_event({"reason": "risk_check", "display": display})
        assert logger.log_research_snapshot({"topic": "schema_slimming", "display": display})
    finally:
        _reset_settings_cache()

    market_payload = _read_jsonl(tmp_path / "market_snapshots" / "2026-05-08.jsonl")[0]["payload"]
    risk_payload = _read_jsonl(tmp_path / "risk_log" / "2026-05-08.jsonl")[0]["payload"]
    research_payload = _read_jsonl(tmp_path / "research_log" / "2026-05-08.jsonl")[0]["payload"]

    assert market_payload["display"] == display
    assert risk_payload["display"] == display
    assert research_payload["display"] == display


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
