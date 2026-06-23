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
        "research_analytics",
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


def test_research_analytics_present_in_dashboard_state(tmp_path: Path) -> None:
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)

    assert "research_analytics" in state
    assert state["research_analytics"]["status"] in {"MISSING", "PARTIAL"}
    assert state["research_analytics"]["latest_research_state"]["blind_spots"] == []


def test_research_state_compact_fields_are_parsed(tmp_path: Path) -> None:
    research_state = tmp_path / "research_state" / "latest_research_state.md"
    research_state.parent.mkdir(parents=True)
    research_state.write_text(
        "\n".join(
            [
                "# Latest Research State",
                "",
                "generated_at: 2026-05-11T04:48:52Z",
                "latest_run_id: run_123",
                "replay_truth_maturity: PARTIAL_DIRECT_TRUTH",
                "direct_field_maturity: LOW_DIRECT_FIELD_COVERAGE",
                "latest_replay_confidence: MEDIUM_DIRECT",
                "direct_field_rate: 0.6176",
                "proxy_field_rate: 0.5",
                "unknown_lifecycle_rate: 0.0",
                "",
                "## Top Candidate Loss Reasons",
                "- candidate_blocked_before_ev: 3",
                "- missed_starter_candidates: 0",
                "",
                "## Top Lifecycle Bottlenecks",
                "- ACTIVE_INVENTORY_TRADING: 3",
                "",
                "## Top EV Null Reasons",
                "- no_probability_model_output: 9",
                "",
                "## Current Blind Spots",
                "- mfe_mae_support",
                "- reload_unload_truth",
                "",
                "## Recommended Next Step",
                "- add offline MFE/MAE candidate path evidence before full lifecycle replay claims",
            ]
        ),
        encoding="utf-8",
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    research = state["research_analytics"]

    assert research["status"] == "PARTIAL"
    assert research["latest_research_state"]["latest_run_id"] == "run_123"
    assert research["latest_research_state"]["replay_truth_maturity"] == "PARTIAL_DIRECT_TRUTH"
    assert research["latest_research_state"]["direct_field_rate"] == 0.6176
    assert research["latest_research_state"]["recommended_next_step"].startswith("add offline MFE/MAE")
    assert research["latest_research_state"]["blind_spots"] == ["mfe_mae_support", "reload_unload_truth"]
    assert research["candidate_loss_reasons"] == [
        {"name": "candidate_blocked_before_ev", "count": 3},
        {"name": "missed_starter_candidates", "count": 0},
    ]
    assert research["lifecycle_bottlenecks"] == [{"name": "ACTIVE_INVENTORY_TRADING", "count": 3}]
    assert research["ev_null_reasons"] == [{"name": "no_probability_model_output", "count": 9}]


def test_malformed_research_state_does_not_crash_aggregator(tmp_path: Path) -> None:
    research_state = tmp_path / "research_state" / "latest_research_state.md"
    research_state.parent.mkdir(parents=True)
    research_state.write_text("\x00\x00not-a-compact-state", encoding="utf-8")

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)

    assert state["research_analytics"]["status"] in {"MISSING", "PARTIAL"}
    assert any(alert["code"] == "RESEARCH_STATE_PARSE_WARNING" for alert in state["research_analytics"]["alerts"])


def test_research_analytics_maps_latest_report_summaries(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "reports" / "replay_report_2026-06-23.json",
        {
            "date_from": "2026-06-23",
            "date_to": "2026-06-23",
            "events_loaded": 10,
            "total_trades": 2,
            "wins": 1,
            "losses": 1,
            "win_rate": 0.5,
            "gross_pnl": 0.03,
            "average_pnl": 0.015,
            "approved_decisions": 3,
            "rejected_decisions": 7,
            "risk_reject_count": 1,
            "lifecycle_replay_confidence": "MEDIUM_PROXY",
            "top_skip_reasons": [["delta_extreme", 4]],
            "phase2_coverage": {"status": "READY_FOR_PHASE2_REPLAY_RESEARCH"},
            "missed_starter_candidates": [{"candidate_key": "c1"}],
            "bad_json_lines": 0,
        },
    )
    _write_json(
        tmp_path / "reports" / "no_entry_report_2026-06-23.json",
        {
            "date": "2026-06-23",
            "total_scanned": 11,
            "total_entered": 1,
            "total_skipped": 10,
            "root_cause_category": "strategy",
            "root_cause_counts": {"strategy": 7},
            "top_skip_reasons": [["confidence_too_low", 6]],
            "recommendations": ["Collect more paper evidence."],
        },
    )
    _write_json(
        tmp_path / "reports" / "quant_data_quality_2026-06-23.json",
        {
            "ok": False,
            "files_scanned": 3,
            "lines_scanned": 100,
            "valid_events": 99,
            "bad_json_lines": 1,
            "phase2_coverage": {"status": "available"},
            "replay_continuity": {"status": "CAUTION", "trustworthy_for_replay": False},
            "research_log_integrity": {"status": "PASS"},
        },
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    reports = state["research_analytics"]["reports"]

    assert reports["replay"]["total_trades"] == 2
    assert reports["replay"]["phase2_coverage_status"] == "READY_FOR_PHASE2_REPLAY_RESEARCH"
    assert reports["replay"]["missed_starter_candidate_count"] == 1
    assert reports["no_entry"]["root_cause_category"] == "strategy"
    assert reports["data_quality"]["ok"] is False
    assert reports["data_quality"]["replay_continuity_status"] == "CAUTION"


def test_replay_analytics_when_report_exists(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "reports" / "replay_report_2026-06-23.json",
        {
            "date_from": "2026-06-23",
            "date_to": "2026-06-23",
            "total_trades": 2,
            "wins": 1,
            "losses": 1,
            "win_rate": 0.5,
            "gross_pnl": 0.03,
            "skipped_decisions": 10,
            "approved_decisions": 2,
            "risk_reject_count": 0,
            "timing_decay_summary": {"avg_seconds_remaining": 120.0},
            "top_skip_reasons": [["delta_extreme", 5]],
            "trades": [
                {
                    "timestamp_utc": "2026-06-23T12:00:00Z",
                    "ticker": "BTC",
                    "side": "YES",
                    "pnl": 0.05,
                    "holding_seconds": 30.0,
                    "outcome": "YES",
                },
                {
                    "timestamp_utc": "2026-06-23T12:01:00Z",
                    "ticker": "ETH",
                    "side": "NO",
                    "pnl": -0.02,
                    "holding_seconds": 45.0,
                    "outcome": "YES",
                }
            ]
        }
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    replay_an = state["research_analytics"]["replay_analytics"]

    assert replay_an["status"] == "OK"
    assert replay_an["summary"]["trades"] == 2
    assert replay_an["summary"]["wins"] == 1
    assert replay_an["summary"]["losses"] == 1
    assert replay_an["summary"]["net_pnl"] == 0.03
    assert replay_an["summary"]["profit_factor"] == 2.5 # 0.05 / 0.02
    assert replay_an["lifecycle_funnel"]["candidates"] == 12
    assert replay_an["lifecycle_funnel"]["signals"] == 2
    assert replay_an["lifecycle_funnel"]["risk_pass"] == 2
    assert replay_an["lifecycle_funnel"]["entries"] == 2
    assert len(replay_an["top_winners"]) == 2
    assert len(replay_an["top_losers"]) == 2
    assert len(replay_an["evidence_table"]) == 2
    assert replay_an["evidence_table"][0]["asset"] == "BTC"
    assert replay_an["evidence_table"][1]["pnl"] == -0.02
    assert len(replay_an["session_breakdown"]) == 1
    assert replay_an["session_breakdown"][0]["verdict"] == "PASS"


def test_replay_analytics_when_report_missing(tmp_path: Path) -> None:
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    replay_an = state["research_analytics"]["replay_analytics"]

    assert replay_an["status"] == "MISSING"
    assert replay_an["summary"]["trades"] == 0
    assert replay_an["session_breakdown"] == []


def test_replay_analytics_when_report_malformed(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "replay_report_2026-06-23.json").write_text("{bad json}", encoding="utf-8")

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    replay_an = state["research_analytics"]["replay_analytics"]

    assert replay_an["status"] == "MISSING"
    assert any(alert["code"] == "REPLAY_REPORT_UNREADABLE" for alert in state["research_analytics"]["alerts"])


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
