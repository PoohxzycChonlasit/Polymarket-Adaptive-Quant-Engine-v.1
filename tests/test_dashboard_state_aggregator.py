import json
from datetime import datetime, timezone
from pathlib import Path

from tools.dashboard_state_aggregator import build_dashboard_state, write_dashboard_state


NOW = datetime(2026, 6, 23, 12, 0, 0, tzinfo=timezone.utc)


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _event(ts: str, event_type: str, payload: dict, *, run_id: str = "run_1") -> dict:
    return {
        "timestamp_utc": ts,
        "event_type": event_type,
        "mode": "paper",
        "run_id": run_id,
        "source_module": "test",
        "schema_version": "1.0",
        "payload": payload,
    }


def test_missing_bot_status_produces_partial_state_and_alert(tmp_path: Path) -> None:
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)

    assert state["meta"]["partial"] is True
    assert state["meta"]["state_status"] == "PARTIAL"
    assert any(alert["code"] == "BOT_STATUS_MISSING" for alert in state["alerts"]["active"])
    assert set(state) == {
        "meta",
        "runtime",
        "safety",
        "portfolio",
        "signals",
        "trades",
        "risk",
        "health",
        "storage",
        "phase_b",
        "alerts",
    }


def test_bot_status_maps_runtime_safety_portfolio_and_signals(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "bot_status.json",
        {
            "timestamp": "2026-06-23T11:59:55Z",
            "execution_mode": "PAPER ONLY",
            "is_paper_trading": True,
            "balance_source": "wallet_reference_paper",
            "paper_balance_source": "wallet_reference",
            "account_balance": 20.5,
            "wallet_reference_balance": 21.0,
            "wallet_reference_error": "",
            "bankroll_tier_id": "T0_MICRO_SEED",
            "bankroll_tier_name": "Micro Seed",
            "bankroll_family": "MICRO",
            "bankroll_mode": "MICRO_SURVIVAL",
            "micro_survival_active": True,
            "micro_position_size": 0.05,
            "open_positions": [{"position_id": "pos_1"}],
            "current_countdown": 42,
            "last_update": "11:59:55",
            "last_signals": {
                "BTC": {
                    "asset": "BTC",
                    "signal_name": "sniper",
                    "signal_reason": "sniper_yes_extreme_zscore",
                    "score": 0.83,
                }
            },
        },
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)

    assert state["runtime"]["execution_mode"] == "PAPER ONLY"
    assert state["runtime"]["is_paper_trading"] is True
    assert state["runtime"]["current_countdown"] == 42
    assert state["safety"]["paper_only"] is True
    assert state["safety"]["live_trading_detected"] is False
    assert state["portfolio"]["account_balance"] == 20.5
    assert state["portfolio"]["open_position_count"] == 1
    assert state["signals"]["assets"]["BTC"]["signal_name"] == "sniper"


def test_owner_file_maps_heartbeat_and_owner_fields(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "ownership" / "paper_runtime_owner.json",
        {
            "status": "active",
            "pid": 1234,
            "run_id": "run_owner",
            "heartbeat_count": 9,
            "heartbeat_utc": "2026-06-23T11:59:50Z",
        },
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)

    assert state["runtime"]["owner_status"] == "active"
    assert state["runtime"]["owner_pid"] == 1234
    assert state["runtime"]["owner_run_id"] == "run_owner"
    assert state["runtime"]["owner_heartbeat_count"] == 9
    assert state["runtime"]["runtime_liveness_verdict"] in {"ACTIVE", "STALE_BOT_STATUS", "PARTIAL_EVIDENCE"}


def test_trade_journal_aggregates_count_pnl_and_winrate(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "quant_data" / "trade_journal" / "2026-06-23.jsonl",
        [
            _event("2026-06-23T11:00:00Z", "trade_open", {"position_id": "p1", "asset": "ETH"}),
            _event("2026-06-23T11:01:00Z", "trade_close", {"position_id": "p1", "pnl_usdc": 0.03, "asset": "ETH"}),
            _event("2026-06-23T11:02:00Z", "trade_open", {"position_id": "p2", "asset": "BTC"}),
            _event("2026-06-23T11:03:00Z", "trade_close", {"position_id": "p2", "pnl": -0.01, "asset": "BTC"}),
        ],
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    today = state["trades"]["today"]

    assert today["trade_open_count"] == 2
    assert today["trade_close_count"] == 2
    assert today["closed_trade_count"] == 2
    assert today["win_count"] == 1
    assert today["loss_count"] == 1
    assert today["win_rate"] == 0.5
    assert today["total_realized_pnl"] == 0.02


def test_decision_log_aggregates_decision_count_and_skip_reasons(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "quant_data" / "decision_log" / "2026-06-23.jsonl",
        [
            _event("2026-06-23T11:00:00Z", "decision", {"decision": "skip", "skip_reason": "confidence_too_low", "asset": "BTC"}),
            _event("2026-06-23T11:00:30Z", "decision", {"decision": "skip", "raw_skip_reason": "ev_below_threshold", "asset": "ETH"}),
            _event("2026-06-23T11:01:00Z", "decision", {"decision": "enter", "signal_name": "trend", "asset": "ETH"}),
        ],
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    decisions = state["phase_b"]["candidate_funnel_today"]

    assert decisions["decision_count"] == 3
    assert decisions["skip_reason_counts"] == {"confidence_too_low": 1, "ev_below_threshold": 1}
    assert decisions["asset_counts"] == {"BTC": 1, "ETH": 2}
    assert decisions["signal_name_counts"] == {"trend": 1}


def test_risk_log_maps_latest_risk_mode(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "quant_data" / "risk_log" / "2026-06-23.jsonl",
        [
            _event("2026-06-23T11:00:00Z", "risk_event", {"risk_mode": "NORMAL", "available_risk_budget": 1.0}),
            _event("2026-06-23T11:05:00Z", "risk_event", {"risk_mode": "DEFENSIVE", "available_risk_budget": 0.5}),
        ],
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)

    assert state["risk"]["risk_mode"] == "DEFENSIVE"
    assert state["risk"]["available_risk_budget"] == 0.5
    assert state["risk"]["risk_event_count_today"] == 2


def test_system_health_accepts_list_quant_disabled_writers(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "quant_data" / "system_health" / "2026-06-23.jsonl",
        [
            _event(
                "2026-06-23T11:00:00Z",
                "system_health",
                {
                    "scan_cycle_duration_ms": 120.5,
                    "quant_disabled_writers": ["decision_log"],
                    "reconciliation_blocks_trading": False,
                    "reconciliation_class": "OK",
                },
            )
        ],
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)

    assert state["health"]["quant_disabled_writers"] == ["decision_log"]
    assert state["safety"]["quant_disabled_writers"] == ["decision_log"]
    assert state["health"]["latest_scan_cycle_duration_ms"] == 120.5


def test_storage_manifest_maps_candidate_count_and_expected_reclaim(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "storage_manifests" / "dry_run" / "compression_dry_run_manifest_001.json",
        {
            "mode": "dry_run",
            "algorithm": "gzip",
            "age_days": 7,
            "summary": {
                "candidate_count": 143,
                "total_expected_reclaim_bytes": 24223376544,
            },
        },
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)

    assert state["storage"]["compression"]["candidate_count"] == 143
    assert state["storage"]["compression"]["expected_reclaim_bytes"] == 24223376544
    assert state["storage"]["compression"]["algorithm"] == "gzip"


def test_atomic_write_creates_valid_json(tmp_path: Path) -> None:
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    output = tmp_path / "dashboard_state.json"

    write_dashboard_state(state, output)

    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["meta"]["schema_version"] == "dashboard_state.v0"
    assert not output.with_suffix(".json.tmp").exists()


def test_no_source_file_is_modified(tmp_path: Path) -> None:
    source = _write_json(tmp_path / "bot_status.json", {"timestamp": "2026-06-23T11:59:55Z"})
    before = (source.stat().st_size, source.stat().st_mtime_ns)

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    write_dashboard_state(state, tmp_path / "dashboard_state.json")

    after = (source.stat().st_size, source.stat().st_mtime_ns)
    assert after == before
