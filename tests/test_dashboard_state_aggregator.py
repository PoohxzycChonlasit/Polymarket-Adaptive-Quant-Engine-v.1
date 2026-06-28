import json
from datetime import datetime, timezone
from pathlib import Path

from tools.runtime.dashboard_state_aggregator import build_dashboard_state, write_dashboard_state


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


def test_no_entry_analytics_when_report_exists(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "reports" / "no_entry_report_2026-06-23.json",
        {
            "date": "2026-06-23",
            "total_scanned": 100,
            "total_entered": 0,
            "total_skipped": 100,
            "count_time_unsafe": 10,
            "count_risk_plan_zero": 5,
            "count_orderbook_unavailable_or_stale": 20,
            "root_cause_counts": {"strategy": 50, "risk": 5, "cutoff": 10, "data": 20, "execution": 15},
            "top_skip_reasons": [["confidence_too_low", 50], ["delta_extreme", 15]],
            "timing_decay_summary": {
                "avg_seconds_remaining": 45.5,
                "min_seconds_remaining": 12.0
            },
            "phase2_coverage": {
                "bankroll_tier_name": "Tier 1",
                "bankroll_mode": "defensive",
                "micro_position_size": 25.0,
                "micro_survival_active": True
            },
            "market_data_quality": {
                "average_orderbook_age_ms": 120.0,
                "token_mapping_warning_count": 2,
                "clob_error_categories": {"timeout": 3}
            },
            "skip_reason_counts": {
                "no_probability_model_output": 8,
                "no_market_price": 4
            },
            "recommendations": ["Review strategy thresholds."]
        }
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    no_entry_an = state["research_analytics"]["no_entry_analytics"]

    assert no_entry_an["status"] == "OK"
    assert no_entry_an["summary"]["total_candidates"] == 100
    assert no_entry_an["summary"]["entries"] == 0
    assert no_entry_an["summary"]["entry_rate"] == 0.0
    assert len(no_entry_an["root_causes"]) == 5
    assert len(no_entry_an["blocker_categories"]) == 2
    assert no_entry_an["timing_cutoff"]["count_time_unsafe"] == 10
    assert no_entry_an["timing_cutoff"]["avg_seconds_remaining"] == 45.5
    assert no_entry_an["timing_cutoff"]["closest_seconds_remaining"] == 12.0
    assert no_entry_an["risk_zero"]["count_risk_plan_zero"] == 5
    assert no_entry_an["risk_zero"]["bankroll_tier_name"] == "Tier 1"
    assert no_entry_an["risk_zero"]["micro_position_size"] == 25.0
    assert no_entry_an["risk_zero"]["micro_survival_active"] is True
    assert no_entry_an["liquidity"]["count_orderbook_unavailable_or_stale"] == 20
    assert no_entry_an["liquidity"]["average_orderbook_age_ms"] == 120.0
    assert no_entry_an["liquidity"]["token_mapping_warning_count"] == 2
    assert no_entry_an["ev_missing"]["no_probability_model_output"] == 8
    assert no_entry_an["ev_missing"]["no_market_price"] == 4
    assert no_entry_an["clob_errors"] == {"timeout": 3}
    assert no_entry_an["recommended_investigation"] == ["Review strategy thresholds."]


def test_no_entry_analytics_when_report_missing(tmp_path: Path) -> None:
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    no_entry_an = state["research_analytics"]["no_entry_analytics"]

    assert no_entry_an["status"] == "MISSING"
    assert no_entry_an["summary"]["total_candidates"] == 0


def test_no_entry_analytics_when_report_malformed(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "no_entry_report_2026-06-23.json").write_text("{bad json}", encoding="utf-8")

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    no_entry_an = state["research_analytics"]["no_entry_analytics"]

    assert no_entry_an["status"] == "MISSING"
    assert any(alert["code"] == "NO_ENTRY_REPORT_UNREADABLE" for alert in state["research_analytics"]["alerts"])


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


def test_session_analytics_when_report_exists(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "reports" / "session_runtime_evaluation_2026-06-23.json",
        {
            "date": "2026-06-23",
            "session_status": "PASS",
            "primary_bottleneck": "none",
            "secondary_bottleneck": "none",
            "scanned": 100,
            "entered": 20,
            "skipped": 80,
            "top_skip_reasons": [["delta_extreme", 30]],
            "recommendations": ["No recommendations needed."],
            "inventory_replay_readiness": {"ok": True},
            "timing_quality": {"average_seconds_remaining": 120.0},
        }
    )
    _write_json(
        tmp_path / "reports" / "replay_report_2026-06-23.json",
        {
            "date_from": "2026-06-23",
            "total_trades": 20,
            "wins": 12,
            "losses": 8,
            "win_rate": 0.6,
            "gross_pnl": 150.0,
            "average_pnl": 7.5,
            "trades": []
        }
    )
    _write_json(
        tmp_path / "reports" / "no_entry_report_2026-06-23.json",
        {
            "date": "2026-06-23",
            "total_scanned": 100,
            "total_entered": 20,
            "total_skipped": 80,
            "count_risk_plan_zero": 5
        }
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    session_an = state["research_analytics"]["session_analytics"]

    assert session_an["status"] == "OK"
    assert session_an["summary"]["best_session"] == "2026-06-23 ($150.00)"
    assert session_an["summary"]["worst_session"] == "2026-06-23 ($150.00)"
    assert session_an["summary"]["highest_entry_rate_session"] == "2026-06-23 (20.0%)"
    assert session_an["summary"]["highest_no_entry_session"] == "2026-06-23 (80.0%)"
    assert len(session_an["leaderboard"]) == 1
    assert session_an["leaderboard"][0]["date"] == "2026-06-23"
    assert session_an["leaderboard"][0]["trades"] == 20
    assert session_an["leaderboard"][0]["wins"] == 12
    assert session_an["leaderboard"][0]["losses"] == 8
    assert session_an["leaderboard"][0]["win_rate"] == 0.6
    assert session_an["leaderboard"][0]["net_pnl"] == 150.0
    assert session_an["leaderboard"][0]["entry_rate"] == 0.2
    assert session_an["leaderboard"][0]["risk_rejects"] == 5
    assert session_an["leaderboard"][0]["expectancy"] == 7.5
    assert session_an["leaderboard"][0]["verdict"] == "PASS"

    assert session_an["entry_rate"] == [{"date": "2026-06-23", "entry_rate": 0.2}]
    assert session_an["no_entry_rate"] == [{"date": "2026-06-23", "no_entry_rate": 0.8}]
    assert session_an["risk_reject_rate"] == [{"date": "2026-06-23", "risk_reject_rate": 0.05}]
    assert session_an["expectancy"] == [{"date": "2026-06-23", "expectancy": 7.5}]
    assert len(session_an["recommended_sessions"]) == 1
    assert session_an["recommended_sessions"][0]["date"] == "2026-06-23"
    assert session_an["sessions_to_avoid"] == []


def test_session_analytics_when_report_missing(tmp_path: Path) -> None:
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    session_an = state["research_analytics"]["session_analytics"]

    assert session_an["status"] == "MISSING"
    assert session_an["summary"]["best_session"] == ""
    assert session_an["leaderboard"] == []


def test_session_analytics_when_report_malformed(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "session_runtime_evaluation_2026-06-23.json").write_text("{bad json}", encoding="utf-8")

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    session_an = state["research_analytics"]["session_analytics"]

    assert session_an["status"] == "MISSING"
    assert any(alert["code"] == "SESSION_RUNTIME_REPORT_UNREADABLE" for alert in state["research_analytics"]["alerts"])


def test_session_analytics_status_transitions(tmp_path: Path) -> None:
    # 1. No reports at all: status is MISSING
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    assert state["research_analytics"]["session_analytics"]["status"] == "MISSING"

    # 2. Only replay report exists: status is OK because leaderboard has 1 item
    _write_json(
        tmp_path / "reports" / "replay_report_2026-06-23.json",
        {
            "date_from": "2026-06-23",
            "total_trades": 10,
            "wins": 5,
            "losses": 5,
            "win_rate": 0.5,
            "gross_pnl": 10.0,
            "trades": []
        }
    )
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    assert state["research_analytics"]["session_analytics"]["status"] == "OK"


def test_lifecycle_analytics_when_reports_exist(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "reports" / "no_entry_report_2026-06-23.json",
        {
            "date": "2026-06-23",
            "total_scanned": 100,
            "total_entered": 5,
            "total_skipped": 95,
            "skip_reason_counts": {
                "confidence_too_low": 20,
                "ev_below_threshold": 30,
                "risk_plan_zero": 10,
                "time_unsafe": 15
            }
        }
    )
    _write_json(
        tmp_path / "reports" / "replay_report_2026-06-23.json",
        {
            "date_from": "2026-06-23",
            "approved_decisions": 50,
            "risk_reject_count": 10,
            "total_trades": 5,
            "wins": 3,
            "losses": 2,
            "win_rate": 0.6,
            "gross_pnl": 50.0,
            "top_skip_reasons": [["delta_extreme", 10]],
            "trades": []
        }
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    lc_an = state["research_analytics"]["lifecycle_analytics"]

    assert lc_an["status"] == "OK"
    summary = lc_an["summary"]
    assert summary["candidate_count"] == 100
    assert summary["signal_pass_count"] == 80
    assert summary["ev_pass_count"] == 50
    assert summary["risk_pass_count"] == 40
    assert summary["execution_pass_count"] == 5
    assert summary["entry_count"] == 5
    assert summary["exit_count"] == 5


def test_lifecycle_analytics_when_reports_missing(tmp_path: Path) -> None:
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    lc_an = state["research_analytics"]["lifecycle_analytics"]

    assert lc_an["status"] == "MISSING"
    assert lc_an["summary"]["candidate_count"] == 0
    assert lc_an["funnel"] == []


def test_lifecycle_analytics_when_reports_malformed(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "no_entry_report_2026-06-23.json").write_text("{bad json}", encoding="utf-8")

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    lc_an = state["research_analytics"]["lifecycle_analytics"]

    assert lc_an["status"] == "MISSING"
    assert lc_an["summary"]["candidate_count"] == 0


def test_lifecycle_analytics_funnel_monotonicity(tmp_path: Path) -> None:
    # Set up inconsistent report counts that would normally violate monotonicity
    _write_json(
        tmp_path / "reports" / "no_entry_report_2026-06-23.json",
        {
            "date": "2026-06-23",
            "total_scanned": 10,
            "total_entered": 50,
            "total_skipped": 0,
            "skip_reason_counts": {}
        }
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    lc_an = state["research_analytics"]["lifecycle_analytics"]

    assert lc_an["status"] == "OK"
    summary = lc_an["summary"]
    assert summary["candidate_count"] == 10
    assert summary["signal_pass_count"] == 10
    assert summary["ev_pass_count"] == 10
    assert summary["risk_pass_count"] == 10
    assert summary["execution_pass_count"] == 10
    assert summary["entry_count"] == 10
    assert summary["exit_count"] == 10

    # Yields should not exceed 100%
    for f in lc_an["funnel"]:
        assert f["yield"] <= 100.0


def test_lifecycle_analytics_stage_loss_non_negative(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "reports" / "no_entry_report_2026-06-23.json",
        {
            "date": "2026-06-23",
            "total_scanned": 100,
            "total_entered": 10,
            "total_skipped": 90,
            "skip_reason_counts": {
                "confidence_too_low": 5,
            }
        }
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    lc_an = state["research_analytics"]["lifecycle_analytics"]

    for loss in lc_an["stage_losses"]:
        assert loss["lost"] >= 0


def test_regime_analytics_when_reports_exist(tmp_path: Path) -> None:
    # 1. Create research_exports/canonical_regime_enriched_trades_v1.csv
    exports_dir = tmp_path / "research_exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    csv_file = exports_dir / "canonical_regime_enriched_trades_v1.csv"
    csv_file.write_text(
        "market_regime,pnl_usdc,outcome_win_loss\n"
        "TREND_UP,10.0,WIN\n"
        "TREND_UP,-5.0,LOSS\n"
        "TREND_DOWN,-2.0,LOSS\n",
        encoding="utf-8"
    )

    # 2. Create reports/session_runtime_evaluation_2026-06-23.json
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        reports_dir / "session_runtime_evaluation_2026-06-23.json",
        {
            "date": "2026-06-23",
            "regime_probability_summary": {
                "market_regimes": [["TREND_UP", 10], ["TREND_DOWN", 5]],
                "skip_decisions_by_regime": {"TREND_UP": 8, "TREND_DOWN": 4},
                "enter_candidates_by_regime": {"TREND_UP": 2, "TREND_DOWN": 1},
                "skip_reasons_by_regime": {
                    "TREND_UP": [["confidence_too_low", 4], ["risk_plan_zero", 4]],
                    "TREND_DOWN": [["ev_below_threshold", 4]]
                }
            }
        }
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    reg_an = state["research_analytics"]["regime_analytics"]

    assert reg_an["status"] == "OK"
    assert reg_an["summary"]["best_regime"] == "TREND_UP"
    assert reg_an["summary"]["worst_regime"] == "TREND_DOWN"

    leaderboard = {item["regime"]: item for item in reg_an["leaderboard"]}
    assert "TREND_UP" in leaderboard
    assert "TREND_DOWN" in leaderboard

    # Check TREND_UP
    trend_up = leaderboard["TREND_UP"]
    assert trend_up["scanned"] == 10
    assert trend_up["entries"] == 2
    assert trend_up["entry_rate"] == 0.2
    assert trend_up["no_entries"] == 8
    assert trend_up["risk_rejections"] == 4
    assert trend_up["risk_rejection_rate"] == 0.5
    assert trend_up["net_pnl"] == 5.0
    assert trend_up["expectancy"] == 2.5
    assert trend_up["win_rate"] == 0.5

    # Check recommended/avoid
    assert any(item["regime"] == "TREND_UP" for item in reg_an["recommended_regimes"])


def test_regime_analytics_when_reports_missing(tmp_path: Path) -> None:
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    reg_an = state["research_analytics"]["regime_analytics"]

    assert reg_an["status"] == "MISSING"
    assert reg_an["summary"]["best_regime"] == ""
    assert reg_an["leaderboard"] == []


def test_regime_analytics_when_reports_malformed(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "session_runtime_evaluation_2026-06-23.json").write_text("{bad json}", encoding="utf-8")

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    reg_an = state["research_analytics"]["regime_analytics"]

    assert reg_an["status"] == "MISSING"


def test_regime_analytics_sorting(tmp_path: Path) -> None:
    exports_dir = tmp_path / "research_exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    csv_file = exports_dir / "canonical_regime_enriched_trades_v1.csv"
    csv_file.write_text(
        "market_regime,pnl_usdc,outcome_win_loss\n"
        "TREND_UP,-10.0,LOSS\n"
        "TREND_DOWN,15.0,WIN\n"
        "SIDEWAY,2.0,WIN\n",
        encoding="utf-8"
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    reg_an = state["research_analytics"]["regime_analytics"]

    assert reg_an["status"] == "PARTIAL"  # No session evaluations, but CSV exists
    leaderboard = reg_an["leaderboard"]
    assert len(leaderboard) == 3

    # Sorted by net_pnl descending
    assert leaderboard[0]["regime"] == "TREND_DOWN"  # PnL = 15.0
    assert leaderboard[1]["regime"] == "SIDEWAY"     # PnL = 2.0
    assert leaderboard[2]["regime"] == "TREND_UP"     # PnL = -10.0


def test_regime_analytics_rates_non_negative(tmp_path: Path) -> None:
    exports_dir = tmp_path / "research_exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    csv_file = exports_dir / "canonical_regime_enriched_trades_v1.csv"
    csv_file.write_text(
        "market_regime,pnl_usdc,outcome_win_loss\n"
        "TREND_UP,-5.0,LOSS\n",
        encoding="utf-8"
    )

    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    reg_an = state["research_analytics"]["regime_analytics"]

    for item in reg_an["leaderboard"]:
        assert item["entry_rate"] >= 0.0
        assert item["no_entry_rate"] >= 0.0
        assert item["risk_rejection_rate"] >= 0.0
        assert item["win_rate"] >= 0.0
        assert item["profit_factor"] >= 0.0


# ---------------------------------------------------------------------------
# MAE/MFE Analytics V1 Tests
# ---------------------------------------------------------------------------

_MAE_MFE_CSV_HEADER = (
    "hold_seconds,entry_price,exit_price,pnl_usdc,"
    "exit_reason,outcome_win_loss,market_regime,side,asset\n"
)


def _mae_mfe_csv_rows(rows: list[tuple]) -> str:
    """Format rows as CSV lines for MAE/MFE analytics tests."""
    return _MAE_MFE_CSV_HEADER + "".join(
        f"{hs},{ep},{xp},{pnl},{reason},{wl},{regime},{side},{asset}\n"
        for hs, ep, xp, pnl, reason, wl, regime, side, asset in rows
    )


def _write_mae_mfe_csv(tmp_path: Path, content: str) -> None:
    exports = tmp_path / "research_exports"
    exports.mkdir(parents=True, exist_ok=True)
    (exports / "canonical_regime_enriched_trades_v1.csv").write_text(content, encoding="utf-8")


def test_mae_mfe_missing_csv(tmp_path: Path) -> None:
    """When CSV is absent status must be MISSING and fields null."""
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    mae = state["research_analytics"]["mae_mfe_analytics"]
    assert mae["status"] == "MISSING"
    assert mae["total_trades"] == 0
    assert mae["summary"]["win_rate"] is None
    assert mae["summary"]["profit_factor"] is None


def test_mae_mfe_empty_csv(tmp_path: Path) -> None:
    """A CSV with only a header row must yield status PARTIAL, not crash."""
    _write_mae_mfe_csv(tmp_path, _MAE_MFE_CSV_HEADER)
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    mae = state["research_analytics"]["mae_mfe_analytics"]
    assert mae["status"] == "PARTIAL"
    assert mae["total_trades"] == 0


def test_mae_mfe_minimal_csv(tmp_path: Path) -> None:
    """Correct aggregation for a small synthetic CSV."""
    rows = [
        # (hold_s, entry, exit, pnl, exit_reason, wl, regime, side, asset)
        (20, 0.50, 0.60, 0.0086, "take_profit_target_reached", "WIN", "COMPRESSION", "YES", "ETH"),
        (10, 0.50, 0.44, -0.0052, "stop_loss", "LOSS", "COMPRESSION", "YES", "ETH"),
        (25, 0.55, 0.65, 0.0091, "take_profit_target_reached", "WIN", "TREND_UP",   "NO",  "BTC"),
        (12, 0.55, 0.49, -0.0048, "stop_loss_hit", "LOSS", "TREND_UP",   "NO",  "BTC"),
        (30, 0.60, 0.70, 0.0088, "take_profit_target_reached", "WIN", "SIDEWAY",    "YES", "ETH"),
        (8,  0.60, 0.54, -0.0051, "stop_loss", "LOSS", "SIDEWAY",    "YES", "ETH"),
        (35, 0.52, 0.62, 0.0090, "take_profit_target_reached", "WIN", "COMPRESSION", "NO",  "BTC"),
        (11, 0.52, 0.46, -0.0049, "stop_loss", "LOSS", "COMPRESSION", "NO",  "BTC"),
        (22, 0.48, 0.58, 0.0084, "take_profit_target_reached", "WIN", "TREND_DOWN", "YES", "ETH"),
        (9,  0.48, 0.42, -0.0050, "stop_loss", "LOSS", "TREND_DOWN", "YES", "ETH"),
    ]
    _write_mae_mfe_csv(tmp_path, _mae_mfe_csv_rows(rows))
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    mae = state["research_analytics"]["mae_mfe_analytics"]

    assert mae["status"] == "OK"
    assert mae["total_trades"] == 10
    assert mae["summary"]["tp_count"] == 5
    assert mae["summary"]["sl_count"] == 5
    assert mae["summary"]["win_rate"] == 0.5
    assert mae["mfe_proxy"]["winner_mean"] is not None
    assert mae["mae_proxy"]["loser_mean"] is not None


def test_mae_mfe_win_loss_split(tmp_path: Path) -> None:
    """tp_count + sl_count + forced_exit_count must cover all trades."""
    rows = [
        (20, 0.50, 0.60,  0.009, "take_profit_target_reached", "WIN",  "COMPRESSION", "YES", "ETH"),
        (10, 0.50, 0.44, -0.005, "stop_loss",                  "LOSS", "COMPRESSION", "YES", "ETH"),
        (15, 0.55, 0.49, -0.005, "stop_loss_hit",              "LOSS", "TREND_UP",    "NO",  "BTC"),
        (18, 0.55, 0.49, -0.005, "forced_exit",                "LOSS", "TREND_UP",    "NO",  "BTC"),
    ]
    _write_mae_mfe_csv(tmp_path, _mae_mfe_csv_rows(rows))
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    mae = state["research_analytics"]["mae_mfe_analytics"]
    s = mae["summary"]
    assert s["tp_count"] + s["sl_count"] + s["forced_exit_count"] == mae["total_trades"]


def test_mae_mfe_hold_time_buckets(tmp_path: Path) -> None:
    """All 5 hold-time buckets must be present; n totals must equal total_trades."""
    rows = [
        (5,  0.50, 0.44, -0.005, "stop_loss",                  "LOSS", "COMPRESSION", "YES", "ETH"),
        (18, 0.50, 0.60,  0.009, "take_profit_target_reached", "WIN",  "COMPRESSION", "YES", "ETH"),
        (33, 0.55, 0.65,  0.009, "take_profit_target_reached", "WIN",  "TREND_UP",    "NO",  "BTC"),
        (50, 0.55, 0.49, -0.005, "stop_loss",                  "LOSS", "TREND_UP",    "NO",  "BTC"),
        (90, 0.60, 0.70,  0.009, "take_profit_target_reached", "WIN",  "SIDEWAY",     "YES", "ETH"),
    ]
    _write_mae_mfe_csv(tmp_path, _mae_mfe_csv_rows(rows))
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    mae = state["research_analytics"]["mae_mfe_analytics"]

    labels = [b["bucket"] for b in mae["hold_time_buckets"]]
    assert labels == ["0-15s", "15-30s", "30-45s", "45-60s", "60s+"]
    total_n = sum(b["n"] for b in mae["hold_time_buckets"])
    assert total_n == mae["total_trades"]


def test_mae_mfe_profit_factor(tmp_path: Path) -> None:
    """Profit factor must match manual sum(TP pnl) / abs(sum(SL pnl))."""
    rows = [
        (20, 0.50, 0.60, 0.010, "take_profit_target_reached", "WIN",  "COMPRESSION", "YES", "ETH"),
        (10, 0.50, 0.44, -0.006, "stop_loss",                 "LOSS", "COMPRESSION", "YES", "ETH"),
        (25, 0.55, 0.65, 0.010, "take_profit_target_reached", "WIN",  "TREND_UP",    "NO",  "BTC"),
        (12, 0.55, 0.49, -0.005, "stop_loss",                 "LOSS", "TREND_UP",    "NO",  "BTC"),
    ]
    _write_mae_mfe_csv(tmp_path, _mae_mfe_csv_rows(rows))
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    mae = state["research_analytics"]["mae_mfe_analytics"]

    expected_pf = round(0.020 / 0.011, 4)
    assert abs(mae["summary"]["profit_factor"] - expected_pf) < 0.001


def test_mae_mfe_verdict_negative(tmp_path: Path) -> None:
    """When profit factor < 1.0 verdict must be EXPECTANCY_NEGATIVE."""
    rows = [
        (10, 0.50, 0.55, 0.004, "take_profit_target_reached", "WIN",  "COMPRESSION", "YES", "ETH"),
        (8,  0.50, 0.44, -0.008, "stop_loss",                 "LOSS", "COMPRESSION", "YES", "ETH"),
        (12, 0.55, 0.60, 0.004, "take_profit_target_reached", "WIN",  "TREND_UP",    "NO",  "BTC"),
        (9,  0.55, 0.49, -0.008, "stop_loss",                 "LOSS", "TREND_UP",    "NO",  "BTC"),
    ]
    _write_mae_mfe_csv(tmp_path, _mae_mfe_csv_rows(rows))
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    mae = state["research_analytics"]["mae_mfe_analytics"]
    assert mae["verdict"] == "EXPECTANCY_NEGATIVE"
    assert mae["summary"]["profit_factor"] < 1.0


def test_mae_mfe_verdict_positive(tmp_path: Path) -> None:
    """When profit factor >= 1.0 verdict must be EXPECTANCY_POSITIVE."""
    rows = [
        (20, 0.50, 0.60, 0.012, "take_profit_target_reached", "WIN",  "COMPRESSION", "YES", "ETH"),
        (10, 0.50, 0.47, -0.004, "stop_loss",                 "LOSS", "COMPRESSION", "YES", "ETH"),
        (25, 0.55, 0.65, 0.012, "take_profit_target_reached", "WIN",  "TREND_UP",    "NO",  "BTC"),
        (11, 0.55, 0.52, -0.004, "stop_loss",                 "LOSS", "TREND_UP",    "NO",  "BTC"),
    ]
    _write_mae_mfe_csv(tmp_path, _mae_mfe_csv_rows(rows))
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    mae = state["research_analytics"]["mae_mfe_analytics"]
    assert mae["verdict"] == "EXPECTANCY_POSITIVE"
    assert mae["summary"]["profit_factor"] >= 1.0


def test_mae_mfe_bad_rows_skipped(tmp_path: Path) -> None:
    """Rows with non-numeric hold_seconds or pnl_usdc must be skipped without crashing."""
    content = (
        _MAE_MFE_CSV_HEADER
        + "BADHOLD,0.50,0.60,0.009,take_profit_target_reached,WIN,COMPRESSION,YES,ETH\n"
        + "20,BADENTRY,0.60,0.009,take_profit_target_reached,WIN,COMPRESSION,YES,ETH\n"
        + "20,0.50,0.60,BADPNL,take_profit_target_reached,WIN,COMPRESSION,YES,ETH\n"
        + "18,0.50,0.60,0.009,take_profit_target_reached,WIN,COMPRESSION,YES,ETH\n"
        + "10,0.50,0.44,-0.005,stop_loss,LOSS,COMPRESSION,YES,ETH\n"
    )
    _write_mae_mfe_csv(tmp_path, content)
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    mae = state["research_analytics"]["mae_mfe_analytics"]

    # 3 bad rows skipped, 2 valid rows remain
    assert mae["total_trades"] == 2
    assert any("PARSE_ERRORS" in a for a in mae["alerts"])


def test_mae_mfe_in_dashboard_state(tmp_path: Path) -> None:
    """build_dashboard_state must always include mae_mfe_analytics key."""
    state = build_dashboard_state(tmp_path, date="2026-06-23", now=NOW)
    assert "mae_mfe_analytics" in state["research_analytics"]
    mae = state["research_analytics"]["mae_mfe_analytics"]
    # Required top-level keys must always be present
    required_keys = {
        "status", "generated_at", "data_warning", "source_csv", "total_trades",
        "summary", "exit_reason_distribution", "hold_time_buckets",
        "mfe_proxy", "mae_proxy", "regime_breakdown", "side_breakdown",
        "asset_breakdown", "optimal_hold_bucket", "dominant_loss_bucket",
        "verdict", "verdict_reason", "alerts",
    }
    assert required_keys.issubset(set(mae.keys()))
