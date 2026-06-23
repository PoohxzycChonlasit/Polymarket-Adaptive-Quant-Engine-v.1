"""Read-only dashboard state aggregator for Quant Dashboard V0."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "dashboard_state.v0"
MAX_JSONL_TAIL_LINES = 1000


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso_z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: Any) -> datetime | None:
    if not _has_value(value):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _age_seconds(value: Any, now: datetime) -> float | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    return max(0.0, round((now.astimezone(UTC) - parsed).total_seconds(), 3))


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return None, "missing"
    except Exception as exc:
        return None, f"unreadable: {exc}"
    if not isinstance(payload, dict):
        return None, "not_object"
    return payload, None


def _read_jsonl_tail(path: Path, *, max_lines: int = MAX_JSONL_TAIL_LINES) -> tuple[list[dict[str, Any]], int, str | None]:
    rows: deque[dict[str, Any]] = deque(maxlen=max_lines)
    bad_json = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    bad_json += 1
                    continue
                if isinstance(payload, dict):
                    rows.append(payload)
                else:
                    bad_json += 1
    except FileNotFoundError:
        return [], 0, "missing"
    except Exception as exc:
        return [], bad_json, f"unreadable: {exc}"
    return list(rows), bad_json, None


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


def _event_type(event: dict[str, Any]) -> str:
    return str(event.get("event_type") or _payload(event).get("event_type") or "")


def _first_present(*values: Any) -> Any:
    for value in values:
        if _has_value(value):
            return value
    return None


def _as_float(value: Any) -> float | None:
    if not _has_value(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_value(value: Any) -> bool:
    return value is not None and value != ""


def _round_money(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 10)


def _alert(severity: str, code: str, message: str, source: str, now: datetime) -> dict[str, Any]:
    timestamp = _iso_z(now)
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "source": source,
        "first_seen_utc": timestamp,
        "last_seen_utc": timestamp,
    }


def _empty_state(root: Path, date: str, now: datetime) -> dict[str, Any]:
    return {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at_utc": _iso_z(now),
            "source_date_utc": date,
            "aggregator_mode": "read_only",
            "state_status": "OK",
            "state_status_reason": "",
            "partial": False,
            "errors": [],
            "warnings": [],
            "source_files": {
                "bot_status": str(root / "bot_status.json"),
                "owner": str(root / "ownership" / "paper_runtime_owner.json"),
                "system_health": str(root / "quant_data" / "system_health" / f"{date}.jsonl"),
                "decision_log": str(root / "quant_data" / "decision_log" / f"{date}.jsonl"),
                "trade_journal": str(root / "quant_data" / "trade_journal" / f"{date}.jsonl"),
                "risk_log": str(root / "quant_data" / "risk_log" / f"{date}.jsonl"),
            },
        },
        "runtime": {
            "execution_mode": "UNKNOWN",
            "is_paper_trading": None,
            "bot_status_timestamp": None,
            "bot_status_age_seconds": None,
            "runtime_freshness": "UNKNOWN",
            "owner_status": "UNKNOWN",
            "owner_pid": None,
            "owner_run_id": None,
            "owner_heartbeat_count": None,
            "owner_heartbeat_utc": None,
            "owner_heartbeat_age_seconds": None,
            "runtime_liveness_verdict": "PARTIAL_EVIDENCE",
            "current_countdown": None,
            "last_update": None,
        },
        "safety": {
            "paper_only": None,
            "live_trading_detected": False,
            "execution_mode_label": "UNKNOWN",
            "balance_source": None,
            "paper_balance_source": None,
            "reconciliation_blocks_trading": None,
            "reconciliation_class": "UNKNOWN",
            "quant_disabled_writers": [],
            "safety_banner": "UNKNOWN",
            "safety_status": "UNKNOWN",
        },
        "portfolio": {
            "account_balance": None,
            "wallet_reference_balance": None,
            "wallet_reference_error": "",
            "bankroll_tier_id": None,
            "bankroll_tier_name": None,
            "bankroll_family": None,
            "bankroll_risk_profile": None,
            "bankroll_tier_locked": None,
            "bankroll_hysteresis_active": None,
            "bankroll_mode": None,
            "micro_survival_active": None,
            "micro_position_size": None,
            "open_position_count": 0,
            "open_positions": [],
        },
        "signals": {
            "assets": {},
            "updated_at": None,
        },
        "trades": {
            "today": {
                "trade_open_count": 0,
                "trade_close_count": 0,
                "closed_trade_count": 0,
                "win_count": 0,
                "loss_count": 0,
                "breakeven_count": 0,
                "win_rate": None,
                "total_realized_pnl": 0.0,
                "avg_realized_pnl": None,
                "attribution_complete_rate": None,
                "latest_trades": [],
            },
            "latest_report": {},
        },
        "risk": {
            "risk_mode": "UNKNOWN",
            "available_risk_budget": None,
            "current_exposure": None,
            "risk_event_count_today": 0,
            "latest_risk_events": [],
            "risk_plan_zero_count_today": 0,
            "reconciliation_blocks_trading": None,
            "lockdown_active": False,
        },
        "health": {
            "system_health_rows_today": 0,
            "latest_health_timestamp_utc": None,
            "latest_scan_cycle_duration_ms": None,
            "avg_scan_cycle_duration_ms_recent": None,
            "max_scan_cycle_duration_ms_recent": None,
            "market_discovery_duration_ms_recent": None,
            "jsonl_status": "UNKNOWN",
            "quant_disabled_writers": [],
            "telegram": {
                "heartbeat_generated_count_today": 0,
                "heartbeat_send_failed_count_today": 0,
                "heartbeat_suppressed_count_today": 0,
                "latest_route": None,
                "latest_suppression_reason": None,
            },
            "freshness": {
                "bot_status_age_seconds": None,
                "owner_heartbeat_age_seconds": None,
                "system_health_age_seconds": None,
                "decision_log_age_seconds": None,
                "trade_journal_age_seconds": None,
            },
        },
        "storage": {
            "last_refreshed_utc": _iso_z(now),
            "runtime_total_mb": None,
            "quant_data_total_mb": None,
            "categories": {},
            "compression": {
                "dry_run_manifest": None,
                "candidate_count": 0,
                "expected_reclaim_bytes": 0,
                "algorithm": None,
                "age_days": None,
                "latest_compress_verification_status": "UNKNOWN",
                "latest_restore_verification_status": "UNKNOWN",
            },
        },
        "phase_b": {
            "candidate_funnel_today": {
                "decision_count": 0,
                "skip_reason_counts": {},
                "asset_counts": {},
                "signal_name_counts": {},
                "latest_decisions": [],
            },
            "edge_inventory": {},
            "canonical_regime_export": {},
            "latest_replay_report": {},
            "latest_no_entry_report": {},
        },
        "research_analytics": {
            "status": "MISSING",
            "generated_at": _iso_z(now),
            "latest_research_state": {
                "latest_run_id": None,
                "replay_truth_maturity": None,
                "direct_field_maturity": None,
                "latest_replay_confidence": None,
                "direct_field_rate": None,
                "proxy_field_rate": None,
                "unknown_lifecycle_rate": None,
                "recommended_next_step": None,
                "blind_spots": [],
            },
            "candidate_loss_reasons": [],
            "lifecycle_bottlenecks": [],
            "ev_null_reasons": [],
            "reports": {
                "replay": {},
                "no_entry": {},
                "session_runtime": {},
                "data_quality": {},
            },
            "replay_analytics": {
                "status": "MISSING",
                "summary": {
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "breakeven": 0,
                    "win_rate": 0.0,
                    "net_pnl": 0.0,
                    "profit_factor": 0.0,
                },
                "opportunity_cost": {
                    "timing_decay": {},
                    "top_skip_reasons": [],
                },
                "lifecycle_funnel": {
                    "candidates": 0,
                    "signals": 0,
                    "risk_pass": 0,
                    "entries": 0,
                },
                "session_breakdown": [],
                "top_winners": [],
                "top_losers": [],
                "evidence_table": [],
            },
            "no_entry_analytics": {
                "status": "MISSING",
                "summary": {
                    "total_candidates": 0,
                    "entries": 0,
                    "entry_rate": 0.0,
                },
                "root_causes": [],
                "blocker_categories": [],
                "timing_cutoff": {},
                "risk_zero": {},
                "liquidity": {},
                "ev_missing": {},
                "clob_errors": {},
                "recommended_investigation": [],
            },
            "session_analytics": {
                "status": "MISSING",
                "summary": {
                    "best_session": "",
                    "worst_session": "",
                    "highest_entry_rate_session": "",
                    "highest_no_entry_session": "",
                },
                "leaderboard": [],
                "entry_rate": [],
                "no_entry_rate": [],
                "risk_reject_rate": [],
                "expectancy": [],
                "recommended_sessions": [],
                "sessions_to_avoid": [],
            },
            "lifecycle_analytics": {
                "status": "MISSING",
                "summary": {
                    "candidate_count": 0,
                    "signal_pass_count": 0,
                    "ev_pass_count": 0,
                    "risk_pass_count": 0,
                    "execution_pass_count": 0,
                    "entry_count": 0,
                    "exit_count": 0
                },
                "funnel": [],
                "stage_losses": [],
                "top_kill_reasons": [],
                "opportunity_cost": [],
                "leaderboard": [],
                "alerts": []
            },
            "alerts": [],
        },
        "alerts": {
            "active": [],
            "recent": [],
            "counts": {"critical": 0, "warning": 0, "info": 0},
        },
    }


def _add_alert(state: dict[str, Any], severity: str, code: str, message: str, source: Path | str, now: datetime) -> None:
    alert = _alert(severity, code, message, str(source), now)
    state["alerts"]["active"].append(alert)
    state["alerts"]["recent"].append(alert)
    state["alerts"]["counts"][severity] = int(state["alerts"]["counts"].get(severity, 0)) + 1
    if severity in {"critical", "warning"}:
        state["meta"]["warnings"].append(f"{code}: {message}")


def _mark_partial(state: dict[str, Any], reason: str) -> None:
    state["meta"]["partial"] = True
    state["meta"]["state_status"] = "PARTIAL"
    if reason not in state["meta"]["errors"]:
        state["meta"]["errors"].append(reason)
    state["meta"]["state_status_reason"] = "; ".join(state["meta"]["errors"])


def _apply_bot_status(state: dict[str, Any], root: Path, now: datetime) -> None:
    path = root / "bot_status.json"
    data, error = _read_json(path)
    if error:
        _mark_partial(state, f"bot_status {error}")
        _add_alert(state, "warning", "BOT_STATUS_MISSING", "runtime/bot_status.json is not available", path, now)
        return

    timestamp = data.get("timestamp")
    age = _age_seconds(timestamp, now)
    is_paper = data.get("is_paper_trading")
    execution_mode = str(data.get("execution_mode") or "UNKNOWN")
    open_positions = data.get("open_positions") if isinstance(data.get("open_positions"), list) else []

    state["runtime"].update(
        {
            "execution_mode": execution_mode,
            "is_paper_trading": is_paper,
            "bot_status_timestamp": timestamp,
            "bot_status_age_seconds": age,
            "runtime_freshness": "FRESH" if age is not None and age <= 30 else "STALE",
            "current_countdown": data.get("current_countdown"),
            "last_update": data.get("last_update"),
        }
    )
    state["health"]["freshness"]["bot_status_age_seconds"] = age
    if age is not None and age > 30:
        _add_alert(state, "warning", "BOT_STATUS_STALE", "runtime/bot_status.json is older than 30 seconds", path, now)

    paper_only = bool(is_paper) or "PAPER" in execution_mode.upper()
    state["safety"].update(
        {
            "paper_only": paper_only,
            "live_trading_detected": not paper_only,
            "execution_mode_label": execution_mode,
            "balance_source": data.get("balance_source"),
            "paper_balance_source": data.get("paper_balance_source"),
            "safety_banner": "PAPER ONLY - NO LIVE ORDERS" if paper_only else "LIVE RISK REVIEW REQUIRED",
            "safety_status": "SAFE_PAPER" if paper_only else "LIVE_RISK_REVIEW_REQUIRED",
        }
    )

    portfolio_keys = (
        "account_balance",
        "wallet_reference_balance",
        "wallet_reference_error",
        "bankroll_tier_id",
        "bankroll_tier_name",
        "bankroll_family",
        "bankroll_risk_profile",
        "bankroll_tier_locked",
        "bankroll_hysteresis_active",
        "bankroll_mode",
        "micro_survival_active",
        "micro_position_size",
    )
    for key in portfolio_keys:
        if key in data:
            state["portfolio"][key] = data.get(key)
    state["portfolio"]["open_positions"] = open_positions
    state["portfolio"]["open_position_count"] = len(open_positions)

    signals = data.get("last_signals") if isinstance(data.get("last_signals"), dict) else {}
    state["signals"]["assets"] = signals
    state["signals"]["updated_at"] = timestamp


def _apply_owner(state: dict[str, Any], root: Path, now: datetime) -> None:
    path = root / "ownership" / "paper_runtime_owner.json"
    data, error = _read_json(path)
    if error:
        _add_alert(state, "warning", "OWNER_FILE_MISSING", "paper runtime owner file is not available", path, now)
        return

    heartbeat = data.get("heartbeat_utc")
    age = _age_seconds(heartbeat, now)
    state["runtime"].update(
        {
            "owner_status": data.get("status", "UNKNOWN"),
            "owner_pid": data.get("pid"),
            "owner_run_id": data.get("run_id"),
            "owner_heartbeat_count": data.get("heartbeat_count"),
            "owner_heartbeat_utc": heartbeat,
            "owner_heartbeat_age_seconds": age,
        }
    )
    state["health"]["freshness"]["owner_heartbeat_age_seconds"] = age
    if str(data.get("status") or "").lower() == "active" and age is not None and age <= 30:
        if state["runtime"]["runtime_freshness"] == "FRESH":
            state["runtime"]["runtime_liveness_verdict"] = "ACTIVE"
        else:
            state["runtime"]["runtime_liveness_verdict"] = "STALE_BOT_STATUS"
    elif age is not None and age > 30:
        state["runtime"]["runtime_liveness_verdict"] = "STALE_OWNER"
        _add_alert(state, "warning", "OWNER_HEARTBEAT_STALE", "paper runtime owner heartbeat is stale", path, now)


def _apply_trades(state: dict[str, Any], root: Path, date: str, now: datetime) -> None:
    path = root / "quant_data" / "trade_journal" / f"{date}.jsonl"
    rows, bad_json, error = _read_jsonl_tail(path)
    if error == "missing":
        return
    if error:
        _add_alert(state, "warning", "TRADE_JOURNAL_UNREADABLE", f"trade journal is {error}", path, now)
        return
    if bad_json:
        _add_alert(state, "warning", "TRADE_JOURNAL_BAD_JSON", f"{bad_json} bad trade journal rows", path, now)

    opens = 0
    closes = 0
    wins = 0
    losses = 0
    breakevens = 0
    pnl_values: list[float] = []
    attributed = 0
    latest: list[dict[str, Any]] = []
    latest_ts: str | None = None

    for event in rows:
        payload = _payload(event)
        event_type = _event_type(event)
        latest_ts = event.get("timestamp_utc") or payload.get("timestamp_utc") or latest_ts
        if event_type == "trade_open":
            opens += 1
        elif event_type == "trade_close":
            closes += 1
            pnl = _as_float(_first_present(payload.get("pnl_usdc"), payload.get("pnl")))
            if pnl is not None:
                pnl_values.append(pnl)
                if pnl > 0:
                    wins += 1
                elif pnl < 0:
                    losses += 1
                else:
                    breakevens += 1
            if isinstance(payload.get("entry_attribution"), dict) or payload.get("entry_attribution_status") == "complete":
                attributed += 1
        if event_type in {"trade_open", "trade_close"}:
            latest.append(
                {
                    "timestamp_utc": event.get("timestamp_utc"),
                    "event_type": event_type,
                    "position_id": payload.get("position_id"),
                    "asset": payload.get("asset") or payload.get("ticker"),
                    "side": payload.get("side"),
                    "pnl": _first_present(payload.get("pnl_usdc"), payload.get("pnl")),
                }
            )

    closed = closes
    total_pnl = sum(pnl_values)
    state["trades"]["today"].update(
        {
            "trade_open_count": opens,
            "trade_close_count": closes,
            "closed_trade_count": closed,
            "win_count": wins,
            "loss_count": losses,
            "breakeven_count": breakevens,
            "win_rate": (wins / closed) if closed else None,
            "total_realized_pnl": _round_money(total_pnl) or 0.0,
            "avg_realized_pnl": _round_money(total_pnl / len(pnl_values)) if pnl_values else None,
            "attribution_complete_rate": (attributed / closed) if closed else None,
            "latest_trades": latest[-10:],
        }
    )
    state["health"]["freshness"]["trade_journal_age_seconds"] = _age_seconds(latest_ts, now)


def _apply_decisions(state: dict[str, Any], root: Path, date: str, now: datetime) -> None:
    path = root / "quant_data" / "decision_log" / f"{date}.jsonl"
    rows, bad_json, error = _read_jsonl_tail(path)
    if error == "missing":
        return
    if error:
        _add_alert(state, "warning", "DECISION_LOG_UNREADABLE", f"decision log is {error}", path, now)
        return
    if bad_json:
        _add_alert(state, "warning", "DECISION_LOG_BAD_JSON", f"{bad_json} bad decision rows", path, now)

    skip_reasons: Counter[str] = Counter()
    assets: Counter[str] = Counter()
    signal_names: Counter[str] = Counter()
    latest: list[dict[str, Any]] = []
    latest_ts: str | None = None

    for event in rows:
        payload = _payload(event)
        latest_ts = event.get("timestamp_utc") or payload.get("timestamp_utc") or latest_ts
        asset = str(payload.get("asset") or payload.get("ticker") or "").upper()
        if asset:
            assets[asset] += 1
        signal_name = str(payload.get("signal_name") or "").strip()
        if signal_name:
            signal_names[signal_name] += 1
        decision = str(payload.get("decision") or payload.get("decision_type") or "").lower()
        reason = str(_first_present(payload.get("skip_reason"), payload.get("raw_skip_reason"), payload.get("reason")) or "").strip()
        if reason and decision in {"skip", "skipped", "no_trade", "hold", ""}:
            skip_reasons[reason] += 1
        latest.append(
            {
                "timestamp_utc": event.get("timestamp_utc"),
                "decision": payload.get("decision"),
                "asset": asset or None,
                "signal_name": signal_name or None,
                "skip_reason": reason or None,
            }
        )

    state["phase_b"]["candidate_funnel_today"].update(
        {
            "decision_count": len(rows),
            "skip_reason_counts": dict(skip_reasons),
            "asset_counts": dict(assets),
            "signal_name_counts": dict(signal_names),
            "latest_decisions": latest[-10:],
        }
    )
    state["health"]["freshness"]["decision_log_age_seconds"] = _age_seconds(latest_ts, now)


def _apply_risk(state: dict[str, Any], root: Path, date: str, now: datetime) -> None:
    path = root / "quant_data" / "risk_log" / f"{date}.jsonl"
    rows, bad_json, error = _read_jsonl_tail(path)
    if error == "missing":
        return
    if error:
        _add_alert(state, "warning", "RISK_LOG_UNREADABLE", f"risk log is {error}", path, now)
        return
    if bad_json:
        _add_alert(state, "warning", "RISK_LOG_BAD_JSON", f"{bad_json} bad risk rows", path, now)

    latest_events: list[dict[str, Any]] = []
    for event in rows:
        payload = _payload(event)
        if _has_value(payload.get("risk_mode")):
            state["risk"]["risk_mode"] = payload.get("risk_mode")
        if _has_value(payload.get("available_risk_budget")):
            state["risk"]["available_risk_budget"] = payload.get("available_risk_budget")
        if _has_value(payload.get("current_exposure")):
            state["risk"]["current_exposure"] = payload.get("current_exposure")
        if str(payload.get("risk_mode") or "").upper() == "LOCKDOWN":
            state["risk"]["lockdown_active"] = True
        if payload.get("risk_plan_zero") or payload.get("risk_plan_zero_diagnostics"):
            state["risk"]["risk_plan_zero_count_today"] += 1
        latest_events.append(
            {
                "timestamp_utc": event.get("timestamp_utc"),
                "event": payload.get("event") or event.get("event_type"),
                "risk_mode": payload.get("risk_mode"),
                "available_risk_budget": payload.get("available_risk_budget"),
            }
        )

    state["risk"]["risk_event_count_today"] = len(rows)
    state["risk"]["latest_risk_events"] = latest_events[-10:]


def _apply_health(state: dict[str, Any], root: Path, date: str, now: datetime) -> None:
    path = root / "quant_data" / "system_health" / f"{date}.jsonl"
    rows, bad_json, error = _read_jsonl_tail(path)
    if error == "missing":
        _add_alert(state, "warning", "SYSTEM_HEALTH_MISSING", "current-day system health log is missing", path, now)
        return
    if error:
        _add_alert(state, "warning", "SYSTEM_HEALTH_UNREADABLE", f"system health log is {error}", path, now)
        return
    if bad_json:
        _add_alert(state, "warning", "SYSTEM_HEALTH_BAD_JSON", f"{bad_json} bad system health rows", path, now)

    scan_values: list[float] = []
    latest_ts: str | None = None
    for event in rows:
        payload = _payload(event)
        latest_ts = event.get("timestamp_utc") or payload.get("timestamp_utc") or latest_ts
        scan = _as_float(payload.get("scan_cycle_duration_ms"))
        if scan is not None:
            scan_values.append(scan)
            state["health"]["latest_scan_cycle_duration_ms"] = scan
        if _has_value(payload.get("market_discovery_duration_ms")):
            state["health"]["market_discovery_duration_ms_recent"] = payload.get("market_discovery_duration_ms")
        if _has_value(payload.get("quant_disabled_writers")):
            writers = payload.get("quant_disabled_writers")
            state["health"]["quant_disabled_writers"] = writers if isinstance(writers, list) else [writers]
            state["safety"]["quant_disabled_writers"] = state["health"]["quant_disabled_writers"]
        if _has_value(payload.get("reconciliation_blocks_trading")):
            state["risk"]["reconciliation_blocks_trading"] = payload.get("reconciliation_blocks_trading")
            state["safety"]["reconciliation_blocks_trading"] = payload.get("reconciliation_blocks_trading")
        if _has_value(payload.get("reconciliation_class")):
            state["safety"]["reconciliation_class"] = payload.get("reconciliation_class")
        event_type = str(payload.get("event_type") or payload.get("event") or "").lower()
        if "heartbeat_generated" in event_type:
            state["health"]["telegram"]["heartbeat_generated_count_today"] += 1
        if "heartbeat_send_failed" in event_type or "telegram_send_failure" in event_type:
            state["health"]["telegram"]["heartbeat_send_failed_count_today"] += 1
        if "heartbeat_suppressed" in event_type or payload.get("suppression_reason"):
            state["health"]["telegram"]["heartbeat_suppressed_count_today"] += 1
        if _has_value(payload.get("route")):
            state["health"]["telegram"]["latest_route"] = payload.get("route")
        if _has_value(payload.get("suppression_reason")):
            state["health"]["telegram"]["latest_suppression_reason"] = payload.get("suppression_reason")

    state["health"]["system_health_rows_today"] = len(rows)
    state["health"]["latest_health_timestamp_utc"] = latest_ts
    state["health"]["freshness"]["system_health_age_seconds"] = _age_seconds(latest_ts, now)
    if scan_values:
        state["health"]["avg_scan_cycle_duration_ms_recent"] = round(sum(scan_values) / len(scan_values), 3)
        state["health"]["max_scan_cycle_duration_ms_recent"] = max(scan_values)


def _dir_size_mb(path: Path) -> float | None:
    if not path.exists():
        return None
    total = 0
    try:
        for file_path in path.rglob("*"):
            if file_path.is_file():
                total += file_path.stat().st_size
    except OSError:
        return None
    return round(total / 1024 / 1024, 2)


def _latest_mtime_iso(files: list[Path]) -> str | None:
    if not files:
        return None
    latest = max(files, key=lambda item: item.stat().st_mtime)
    return _iso_z(datetime.fromtimestamp(latest.stat().st_mtime, tz=UTC))


def _apply_storage(state: dict[str, Any], root: Path, now: datetime) -> None:
    state["storage"]["runtime_total_mb"] = _dir_size_mb(root)
    quant_root = root / "quant_data"
    state["storage"]["quant_data_total_mb"] = _dir_size_mb(quant_root)

    if quant_root.exists():
        for category in sorted(path for path in quant_root.iterdir() if path.is_dir()):
            files = [item for item in category.rglob("*") if item.is_file()]
            jsonl_files = [item for item in files if item.name.endswith(".jsonl")]
            gz_files = [item for item in files if item.name.endswith(".gz")]
            latest_file = max(files, key=lambda item: item.stat().st_mtime) if files else None
            state["storage"]["categories"][category.name] = {
                "size_mb": round(sum(item.stat().st_size for item in files) / 1024 / 1024, 2),
                "jsonl_count": len(jsonl_files),
                "gz_count": len(gz_files),
                "latest_file": str(latest_file) if latest_file else None,
                "latest_mtime_utc": _latest_mtime_iso(files),
            }

    manifest_path = root / "storage_manifests" / "dry_run" / "compression_dry_run_manifest_001.json"
    manifest, error = _read_json(manifest_path)
    if error is None and manifest:
        summary = manifest.get("summary") if isinstance(manifest.get("summary"), dict) else {}
        state["storage"]["compression"].update(
            {
                "dry_run_manifest": str(manifest_path),
                "candidate_count": summary.get("candidate_count", 0),
                "expected_reclaim_bytes": summary.get("total_expected_reclaim_bytes", 0),
                "algorithm": manifest.get("algorithm"),
                "age_days": manifest.get("age_days"),
            }
        )


def _latest_json_file(path: Path, pattern: str) -> Path | None:
    files = sorted(path.glob(pattern), key=lambda item: item.stat().st_mtime)
    return files[-1] if files else None


def _apply_reports(state: dict[str, Any], root: Path) -> None:
    reports = root / "reports"
    edge_path = reports / "edge_inventory_report_v1.json"
    edge, _ = _read_json(edge_path)
    if edge:
        summary = edge.get("summary") if isinstance(edge.get("summary"), dict) else {}
        state["phase_b"]["edge_inventory"] = {
            "report_path": str(edge_path),
            "valid_attributed_trade_count": summary.get("valid_attributed_trade_count"),
            "win_rate": summary.get("win_rate"),
            "total_realized_pnl": summary.get("total_realized_pnl"),
            "attribution_complete_rate": summary.get("attribution_complete_rate"),
            "quarantined_trade_count": summary.get("quarantined_trade_count"),
            "report_readiness_verdict": edge.get("report_readiness_verdict"),
        }
        state["trades"]["latest_report"] = state["phase_b"]["edge_inventory"]

    replay_path = _latest_json_file(reports, "replay_report_*.json")
    replay, _ = _read_json(replay_path) if replay_path else (None, None)
    if replay:
        state["phase_b"]["latest_replay_report"] = {
            "path": str(replay_path),
            "gross_pnl": replay.get("gross_pnl"),
            "wins": replay.get("wins"),
            "losses": replay.get("losses"),
            "top_skip_reasons": replay.get("top_skip_reasons", []),
        }

    no_entry_path = _latest_json_file(reports, "no_entry_report_*.json")
    no_entry, _ = _read_json(no_entry_path) if no_entry_path else (None, None)
    if no_entry:
        state["phase_b"]["latest_no_entry_report"] = {
            "path": str(no_entry_path),
            "root_cause_category": no_entry.get("root_cause_category"),
            "top_skip_reasons": no_entry.get("top_skip_reasons", []),
        }


def _apply_research_exports(state: dict[str, Any], root: Path) -> None:
    meta_path = root / "research_exports" / "canonical_regime_enriched_trades_v1_meta.json"
    data, _ = _read_json(meta_path)
    if not data:
        return
    validation = data.get("validation") if isinstance(data.get("validation"), dict) else {}
    freshness = data.get("freshness") if isinstance(data.get("freshness"), dict) else {}
    state["phase_b"]["canonical_regime_export"] = {
        "meta_path": str(meta_path),
        "status": validation.get("status"),
        "canonical_n": validation.get("canonical_n"),
        "regime_join_rate": validation.get("regime_join_rate"),
        "unknown_regime_rate": validation.get("unknown_regime_rate"),
        "freshness_status": freshness.get("status"),
    }


def _research_alert(state: dict[str, Any], code: str, message: str, source: Path | str) -> None:
    state["research_analytics"]["alerts"].append(
        {
            "severity": "warning",
            "code": code,
            "message": message,
            "source": str(source),
        }
    )


def _parse_research_count_item(line: str) -> dict[str, Any] | None:
    text = line.strip()
    if not text.startswith("- "):
        return None
    item = text[2:].strip()
    if not item:
        return None
    if ":" not in item:
        return {"name": item, "count": None}
    name, raw_count = item.split(":", 1)
    name = name.strip()
    try:
        count: int | None = int(raw_count.strip())
    except ValueError:
        count = None
    return {"name": name, "count": count}


def _parse_research_state_markdown(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None, "missing"
    except Exception as exc:
        return None, f"unreadable: {exc}"
    if "\x00" in text:
        return None, "contains_nul"

    scalar_keys = {
        "latest_run_id",
        "replay_truth_maturity",
        "direct_field_maturity",
        "latest_replay_confidence",
        "direct_field_rate",
        "proxy_field_rate",
        "unknown_lifecycle_rate",
    }
    parsed: dict[str, Any] = {
        "latest_research_state": {
            "latest_run_id": None,
            "replay_truth_maturity": None,
            "direct_field_maturity": None,
            "latest_replay_confidence": None,
            "direct_field_rate": None,
            "proxy_field_rate": None,
            "unknown_lifecycle_rate": None,
            "recommended_next_step": None,
            "blind_spots": [],
        },
        "candidate_loss_reasons": [],
        "lifecycle_bottlenecks": [],
        "ev_null_reasons": [],
    }
    section = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            section = line[3:].strip().lower()
            continue
        if ":" in line and not line.startswith("- "):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key in scalar_keys:
                parsed["latest_research_state"][key] = _as_float(value) if key.endswith("_rate") else value
            continue
        if not line.startswith("- "):
            continue
        item_text = line[2:].strip()
        if section == "top candidate loss reasons":
            item = _parse_research_count_item(line)
            if item:
                parsed["candidate_loss_reasons"].append(item)
        elif section == "top lifecycle bottlenecks":
            item = _parse_research_count_item(line)
            if item:
                parsed["lifecycle_bottlenecks"].append(item)
        elif section == "top ev null reasons":
            item = _parse_research_count_item(line)
            if item:
                parsed["ev_null_reasons"].append(item)
        elif section == "current blind spots" and item_text:
            parsed["latest_research_state"]["blind_spots"].append(item_text)
        elif section == "recommended next step" and item_text:
            parsed["latest_research_state"]["recommended_next_step"] = item_text

    if not any(_has_value(parsed["latest_research_state"].get(key)) for key in scalar_keys):
        return parsed, "no_compact_fields"
    return parsed, None


def _safe_list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _extract_replay_analytics(replay: dict[str, Any] | None, reports_dir: Path) -> dict[str, Any]:
    if not replay:
        return {
            "status": "MISSING",
            "summary": {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "breakeven": 0,
                "win_rate": 0.0,
                "net_pnl": 0.0,
                "profit_factor": 0.0,
            },
            "opportunity_cost": {
                "timing_decay": {},
                "top_skip_reasons": [],
            },
            "lifecycle_funnel": {
                "candidates": 0,
                "signals": 0,
                "risk_pass": 0,
                "entries": 0,
            },
            "session_breakdown": [],
            "top_winners": [],
            "top_losers": [],
            "evidence_table": [],
        }

    trades_list = replay.get("trades")
    if not isinstance(trades_list, list):
        trades_list = []

    # Calculate profit factor
    gross_profits = sum(t.get("pnl", 0.0) for t in trades_list if isinstance(t, dict) and t.get("pnl", 0.0) > 0)
    gross_losses = sum(abs(t.get("pnl", 0.0)) for t in trades_list if isinstance(t, dict) and t.get("pnl", 0.0) < 0)
    profit_factor = round(gross_profits / gross_losses, 4) if gross_losses > 0 else (99.0 if gross_profits > 0 else 1.0)

    # Sort trades for winners / losers
    sorted_trades = sorted(trades_list, key=lambda x: x.get("pnl", 0.0) if isinstance(x, dict) else 0.0)

    def _map_trade(t: Any) -> dict[str, Any]:
        if not isinstance(t, dict):
            return {}
        return {
            "timestamp_utc": t.get("timestamp_utc", "n/a"),
            "asset": t.get("ticker") or t.get("market_id") or "n/a",
            "side": t.get("side", "n/a"),
            "signal": t.get("signal") or "n/a",
            "holding_seconds": t.get("holding_seconds"),
            "outcome": t.get("outcome", "n/a"),
            "pnl": t.get("pnl", 0.0),
        }

    top_losers = [_map_trade(t) for t in sorted_trades[:5] if isinstance(t, dict)]
    top_winners = [_map_trade(t) for t in reversed(sorted_trades[-5:]) if isinstance(t, dict)]
    evidence_table = [_map_trade(t) for t in trades_list if isinstance(t, dict)]

    total_trades = replay.get("total_trades", 0)
    wins = replay.get("wins", 0)
    losses = replay.get("losses", 0)
    breakeven = max(0, total_trades - wins - losses)

    skipped = replay.get("skipped_decisions", 0) or 0
    approved = replay.get("approved_decisions", 0) or 0
    risk_reject = replay.get("risk_reject_count", 0) or 0

    timing_decay = replay.get("timing_decay_summary") or {}
    top_skip_reasons = replay.get("top_skip_reasons") or []

    session_breakdown = []
    try:
        for p in sorted(reports_dir.glob("replay_report_*.json")):
            try:
                with p.open("r", encoding="utf-8") as h:
                    rep = json.load(h)
                if isinstance(rep, dict):
                    rep_wins = rep.get("wins", 0) or 0
                    rep_losses = rep.get("losses", 0) or 0
                    rep_pnl = rep.get("gross_pnl", 0.0) or 0.0
                    rep_win_rate = rep.get("win_rate", 0.0) or 0.0

                    verdict = "PASS" if rep_win_rate >= 0.5 and rep_pnl > 0 else "CAUTION"
                    rep_skips = rep.get("top_skip_reasons", [])
                    bottleneck = rep_skips[0][0] if rep_skips else "none"

                    session_breakdown.append({
                        "date": rep.get("date_from") or p.stem.replace("replay_report_", ""),
                        "verdict": verdict,
                        "trades": f"{rep_wins}W / {rep_losses}L",
                        "pnl": rep_pnl,
                        "bottleneck": bottleneck,
                    })
            except Exception:
                continue
    except Exception:
        pass

    return {
        "status": "OK" if trades_list else "PARTIAL",
        "summary": {
            "trades": total_trades,
            "wins": wins,
            "losses": losses,
            "breakeven": breakeven,
            "win_rate": replay.get("win_rate", 0.0) or 0.0,
            "net_pnl": replay.get("gross_pnl", 0.0) or 0.0,
            "profit_factor": profit_factor,
        },
        "opportunity_cost": {
            "timing_decay": timing_decay,
            "top_skip_reasons": top_skip_reasons,
        },
        "lifecycle_funnel": {
            "candidates": skipped + approved,
            "signals": approved,
            "risk_pass": max(0, approved - risk_reject),
            "entries": total_trades,
        },
        "session_breakdown": session_breakdown,
        "top_winners": top_winners,
        "top_losers": top_losers,
        "evidence_table": evidence_table,
    }


def _extract_no_entry_analytics(no_entry: dict[str, Any] | None) -> dict[str, Any]:
    if not no_entry:
        return {
            "status": "MISSING",
            "summary": {
                "total_candidates": 0,
                "entries": 0,
                "entry_rate": 0.0,
            },
            "root_causes": [],
            "blocker_categories": [],
            "timing_cutoff": {},
            "risk_zero": {},
            "liquidity": {},
            "ev_missing": {},
            "clob_errors": {},
            "recommended_investigation": [],
        }

    total_scanned = no_entry.get("total_scanned", 0)
    total_entered = no_entry.get("total_entered", 0)
    entry_rate = round(total_entered / total_scanned, 4) if total_scanned > 0 else 0.0

    root_cause_counts = no_entry.get("root_cause_counts", {})
    root_causes = [[k, v] for k, v in root_cause_counts.items()] if isinstance(root_cause_counts, dict) else []

    top_skip_reasons = no_entry.get("top_skip_reasons", [])
    blocker_categories = top_skip_reasons if isinstance(top_skip_reasons, list) else []

    timing_decay = no_entry.get("timing_decay_summary") or {}
    timing_cutoff = {
        "count_time_unsafe": no_entry.get("count_time_unsafe", 0),
        "avg_seconds_remaining": timing_decay.get("avg_seconds_remaining", 0.0),
        "closest_seconds_remaining": timing_decay.get("closest_seconds_remaining") or timing_decay.get("min_seconds_remaining"),
        "timing_buckets": no_entry.get("skip_by_time_bucket", {}),
    }

    phase2 = no_entry.get("phase2_coverage") or {}
    risk_zero = {
        "count_risk_plan_zero": no_entry.get("count_risk_plan_zero", 0),
        "bankroll_tier_name": phase2.get("bankroll_tier_name") or "n/a",
        "bankroll_mode": phase2.get("bankroll_mode") or "n/a",
        "micro_position_size": phase2.get("micro_position_size") or 0.0,
        "micro_survival_active": phase2.get("micro_survival_active") or False,
    }

    quality = no_entry.get("market_data_quality") or {}
    liquidity = {
        "count_orderbook_unavailable_or_stale": no_entry.get("count_orderbook_unavailable_or_stale", 0),
        "average_orderbook_age_ms": quality.get("average_orderbook_age_ms", 0.0),
        "token_mapping_warning_count": quality.get("token_mapping_warning_count", 0),
    }

    skip_reasons = no_entry.get("skip_reason_counts") or {}
    ev_missing = {
        "no_probability_model_output": skip_reasons.get("no_probability_model_output", 0) + skip_reasons.get("ev_not_visible", 0),
        "no_market_price": skip_reasons.get("no_market_price", 0) + skip_reasons.get("price_not_visible", 0),
    }

    clob_errors = quality.get("clob_error_categories") or {}

    recommended_investigation = no_entry.get("recommendations") or []

    return {
        "status": "OK" if total_scanned > 0 else "PARTIAL",
        "summary": {
            "total_candidates": total_scanned,
            "entries": total_entered,
            "entry_rate": entry_rate,
        },
        "root_causes": root_causes,
        "blocker_categories": blocker_categories,
        "timing_cutoff": timing_cutoff,
        "risk_zero": risk_zero,
        "liquidity": liquidity,
        "ev_missing": ev_missing,
        "clob_errors": clob_errors,
        "recommended_investigation": recommended_investigation,
    }


def _extract_session_analytics(session: dict[str, Any] | None, reports_dir: Path) -> dict[str, Any]:
    by_date = {}

    # 1. Scan replay reports
    try:
        for p in reports_dir.glob("replay_report_*.json"):
            stem = p.stem
            parts = stem.split("_")
            date_str = ""
            for part in parts:
                if len(part) == 10 and part.count("-") == 2:
                    date_str = part
                    break
            if not date_str:
                date_str = stem.replace("replay_report_", "")[:10]
            try:
                with p.open("r", encoding="utf-8") as h:
                    rep = json.load(h)
                if isinstance(rep, dict):
                    by_date.setdefault(date_str, {})["replay"] = rep
            except Exception:
                continue
    except Exception:
        pass

    # 2. Scan no_entry reports
    try:
        for p in reports_dir.glob("no_entry_report_*.json"):
            stem = p.stem
            parts = stem.split("_")
            date_str = ""
            for part in parts:
                if len(part) == 10 and part.count("-") == 2:
                    date_str = part
                    break
            if not date_str:
                date_str = stem.replace("no_entry_report_", "")[:10]
            try:
                with p.open("r", encoding="utf-8") as h:
                    rep = json.load(h)
                if isinstance(rep, dict):
                    by_date.setdefault(date_str, {})["no_entry"] = rep
            except Exception:
                continue
    except Exception:
        pass

    # 3. Scan session evaluations
    try:
        for p in reports_dir.glob("session_runtime_evaluation_*.json"):
            stem = p.stem
            parts = stem.split("_")
            date_str = ""
            for part in parts:
                if len(part) == 10 and part.count("-") == 2:
                    date_str = part
                    break
            if not date_str:
                date_str = stem.replace("session_runtime_evaluation_", "")[:10]
            try:
                with p.open("r", encoding="utf-8") as h:
                    rep = json.load(h)
                if isinstance(rep, dict):
                    by_date.setdefault(date_str, {})["evaluation"] = rep
            except Exception:
                continue
    except Exception:
        pass

    if session:
        eval_date = session.get("date")
        if eval_date:
            by_date.setdefault(eval_date, {})["evaluation"] = session

    if not by_date:
        return {
            "status": "MISSING",
            "summary": {
                "best_session": "",
                "worst_session": "",
                "highest_entry_rate_session": "",
                "highest_no_entry_session": "",
            },
            "leaderboard": [],
            "entry_rate": [],
            "no_entry_rate": [],
            "risk_reject_rate": [],
            "expectancy": [],
            "recommended_sessions": [],
            "sessions_to_avoid": [],
        }

    leaderboard = []
    entry_rates = []
    no_entry_rates = []
    risk_reject_rates = []
    expectancies = []
    recommended_sessions = []
    sessions_to_avoid = []

    for d, data in sorted(by_date.items()):
        replay = data.get("replay") or {}
        no_entry = data.get("no_entry") or {}
        evaluation = data.get("evaluation") or {}

        total_trades = replay.get("total_trades", 0)
        wins = replay.get("wins", 0)
        losses = replay.get("losses", 0)
        net_pnl = replay.get("gross_pnl", 0.0) or 0.0
        win_rate = replay.get("win_rate", 0.0) or 0.0

        trades_list = replay.get("trades") or []
        gross_profits = sum(t.get("pnl", 0.0) for t in trades_list if isinstance(t, dict) and t.get("pnl", 0.0) > 0)
        gross_losses = sum(abs(t.get("pnl", 0.0)) for t in trades_list if isinstance(t, dict) and t.get("pnl", 0.0) < 0)
        profit_factor = round(gross_profits / gross_losses, 4) if gross_losses > 0 else (99.0 if gross_profits > 0 else 1.0)

        scanned = no_entry.get("total_scanned") or evaluation.get("health_summary", {}).get("scanned") or total_trades or 1
        entered = no_entry.get("total_entered") or evaluation.get("health_summary", {}).get("entered") or total_trades
        skipped = no_entry.get("total_skipped") or evaluation.get("health_summary", {}).get("skipped") or 0
        risk_rejects = no_entry.get("count_risk_plan_zero", 0) or evaluation.get("risk_blocks", {}).get("count_risk_plan_zero", 0)

        entry_rate = round(entered / scanned, 4) if scanned > 0 else 0.0
        no_entry_rate = round(skipped / scanned, 4) if scanned > 0 else 0.0
        risk_reject_rate = round(risk_rejects / scanned, 4) if scanned > 0 else 0.0

        expectancy = replay.get("average_pnl") or (round(net_pnl / total_trades, 4) if total_trades > 0 else 0.0)

        primary_bottleneck = evaluation.get("primary_bottleneck") or no_entry.get("root_cause_category") or "none"
        session_status = evaluation.get("session_status") or ("PASS" if win_rate >= 0.5 and net_pnl >= 0 else "CAUTION")

        leaderboard.append({
            "date": d,
            "trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "net_pnl": net_pnl,
            "profit_factor": profit_factor,
            "entry_rate": entry_rate,
            "no_entry_rate": no_entry_rate,
            "risk_rejects": risk_rejects,
            "expectancy": expectancy,
            "primary_bottleneck": primary_bottleneck,
            "verdict": session_status,
        })

        entry_rates.append({"date": d, "entry_rate": entry_rate})
        no_entry_rates.append({"date": d, "no_entry_rate": no_entry_rate})
        risk_reject_rates.append({"date": d, "risk_reject_rate": risk_reject_rate})
        expectancies.append({"date": d, "expectancy": expectancy})

        verdict = session_status.upper()
        if verdict == "PASS":
            recommended_sessions.append({
                "date": d,
                "reason": f"High Win Rate ({win_rate*100:.1f}%) and positive PnL (${net_pnl:.2f})."
            })
        elif verdict == "FAIL" or primary_bottleneck in {"latency", "websocket_instability", "websocket_dropped", "stale_data"}:
            sessions_to_avoid.append({
                "date": d,
                "reason": f"Fail status or operational bottleneck: {primary_bottleneck}."
            })

    best_session = ""
    worst_session = ""
    highest_entry_rate_session = ""
    highest_no_entry_session = ""

    if leaderboard:
        best = max(leaderboard, key=lambda x: x["net_pnl"])
        best_session = f"{best['date']} (${best['net_pnl']:.2f})"
        worst = min(leaderboard, key=lambda x: x["net_pnl"])
        worst_session = f"{worst['date']} (${worst['net_pnl']:.2f})"
        high_entry = max(leaderboard, key=lambda x: x["entry_rate"])
        highest_entry_rate_session = f"{high_entry['date']} ({high_entry['entry_rate']*100:.1f}%)"
        high_no_entry = max(leaderboard, key=lambda x: x["no_entry_rate"])
        highest_no_entry_session = f"{high_no_entry['date']} ({high_no_entry['no_entry_rate']*100:.1f}%)"

    return {
        "status": "OK" if leaderboard else "PARTIAL",
        "summary": {
            "best_session": best_session,
            "worst_session": worst_session,
            "highest_entry_rate_session": highest_entry_rate_session,
            "highest_no_entry_session": highest_no_entry_session,
        },
        "leaderboard": leaderboard,
        "entry_rate": entry_rates,
        "no_entry_rate": no_entry_rates,
        "risk_reject_rate": risk_reject_rates,
        "expectancy": expectancies,
        "recommended_sessions": recommended_sessions,
        "sessions_to_avoid": sessions_to_avoid,
    }


def _extract_lifecycle_analytics(reports_dir: Path) -> dict[str, Any]:
    by_date = {}

    # Scan replay reports
    try:
        for p in reports_dir.glob("replay_report_*.json"):
            stem = p.stem
            parts = stem.split("_")
            date_str = ""
            for part in parts:
                if len(part) == 10 and part.count("-") == 2:
                    date_str = part
                    break
            if not date_str:
                date_str = stem.replace("replay_report_", "")[:10]
            try:
                with p.open("r", encoding="utf-8") as h:
                    rep = json.load(h)
                if isinstance(rep, dict):
                    by_date.setdefault(date_str, {})["replay"] = rep
            except Exception:
                continue
    except Exception:
        pass

    # Scan no_entry reports
    try:
        for p in reports_dir.glob("no_entry_report_*.json"):
            stem = p.stem
            parts = stem.split("_")
            date_str = ""
            for part in parts:
                if len(part) == 10 and part.count("-") == 2:
                    date_str = part
                    break
            if not date_str:
                date_str = stem.replace("no_entry_report_", "")[:10]
            try:
                with p.open("r", encoding="utf-8") as h:
                    rep = json.load(h)
                if isinstance(rep, dict):
                    by_date.setdefault(date_str, {})["no_entry"] = rep
            except Exception:
                continue
    except Exception:
        pass

    if not by_date:
        return {
            "status": "MISSING",
            "summary": {
                "candidate_count": 0,
                "signal_pass_count": 0,
                "ev_pass_count": 0,
                "risk_pass_count": 0,
                "execution_pass_count": 0,
                "entry_count": 0,
                "exit_count": 0
            },
            "funnel": [],
            "stage_losses": [],
            "top_kill_reasons": [],
            "opportunity_cost": [],
            "leaderboard": [],
            "alerts": []
        }

    # Consolidated counts across all sessions
    total_candidates = 0
    total_signal_pass = 0
    total_ev_pass = 0
    total_risk_pass = 0
    total_execution_pass = 0
    total_entries = 0
    total_exits = 0

    kill_reasons_counter = Counter()
    opportunity_counter = Counter()
    leaderboard = []

    for d, data in sorted(by_date.items()):
        replay = data.get("replay") or {}
        no_entry = data.get("no_entry") or {}

        # 1. Candidate count
        c_count = no_entry.get("total_scanned") or replay.get("total_trades", 0) or 0

        # 2. Signal Passed
        sig_skips = no_entry.get("skip_reason_counts", {}).get("confidence_too_low", 0) + no_entry.get("skip_reason_counts", {}).get("stale_data", 0)
        sig_pass = max(0, c_count - sig_skips)

        # 3. EV Passed
        ev_pass = replay.get("approved_decisions")
        if ev_pass is None:
            ev_skips = no_entry.get("skip_reason_counts", {}).get("ev_below_threshold", 0) + no_entry.get("skip_reason_counts", {}).get("delta_extreme", 0)
            ev_pass = max(0, sig_pass - ev_skips)

        # 4. Risk Passed
        risk_pass = ev_pass
        if replay:
            risk_pass = max(0, ev_pass - replay.get("risk_reject_count", 0))
        else:
            risk_skips = no_entry.get("skip_reason_counts", {}).get("risk_plan_zero", 0)
            risk_pass = max(0, ev_pass - risk_skips)

        # 5. Execution Passed
        exec_pass = risk_pass
        if replay:
            exec_pass = replay.get("total_trades", 0)
        else:
            exec_skips = (no_entry.get("skip_reason_counts", {}).get("clob_empty_response", 0) +
                          no_entry.get("skip_reason_counts", {}).get("clob_http_error", 0) +
                          no_entry.get("skip_reason_counts", {}).get("time_unsafe", 0))
            exec_pass = max(0, risk_pass - exec_skips)

        # 6. Entry Created
        ent_count = replay.get("total_trades") or no_entry.get("total_entered") or 0

        # 7. Exit Completed
        ext_count = ent_count

        # Enforce monotonicity
        c_count = max(0, int(c_count))
        sig_pass = min(c_count, max(0, int(sig_pass)))
        ev_pass = min(sig_pass, max(0, int(ev_pass)))
        risk_pass = min(ev_pass, max(0, int(risk_pass)))
        exec_pass = min(risk_pass, max(0, int(exec_pass)))
        ent_count = min(exec_pass, max(0, int(ent_count)))
        ext_count = min(ent_count, max(0, int(ext_count)))

        total_candidates += c_count
        total_signal_pass += sig_pass
        total_ev_pass += ev_pass
        total_risk_pass += risk_pass
        total_execution_pass += exec_pass
        total_entries += ent_count
        total_exits += ext_count

        # Kill reasons aggregation
        for reason, count in no_entry.get("skip_reason_counts", {}).items():
            kill_reasons_counter[reason] += count
        for reason_pair in replay.get("top_skip_reasons", []):
            if isinstance(reason_pair, list) and len(reason_pair) == 2:
                kill_reasons_counter[reason_pair[0]] += reason_pair[1]

        # Opportunity cost aggregation
        for reason, count in no_entry.get("skip_reason_counts", {}).items():
            opportunity_counter[reason] += count

        dominant_blocker = no_entry.get("root_cause_category") or "none"
        leaderboard.append({
            "date": d,
            "scanned": c_count,
            "entries": ent_count,
            "throughput_rate": round(ent_count / c_count, 4) if c_count > 0 else 0.0,
            "dominant_blocker": dominant_blocker
        })

    # Total funnel yields
    funnel = [
        {"stage": "Candidate Created", "count": total_candidates, "yield": 100.0},
        {"stage": "Signal Passed", "count": total_signal_pass, "yield": round(total_signal_pass / total_candidates * 100, 2) if total_candidates > 0 else 0.0},
        {"stage": "EV Passed", "count": total_ev_pass, "yield": round(total_ev_pass / total_signal_pass * 100, 2) if total_signal_pass > 0 else 0.0},
        {"stage": "Risk Passed", "count": total_risk_pass, "yield": round(total_risk_pass / total_ev_pass * 100, 2) if total_ev_pass > 0 else 0.0},
        {"stage": "Execution Passed", "count": total_execution_pass, "yield": round(total_execution_pass / total_risk_pass * 100, 2) if total_risk_pass > 0 else 0.0},
        {"stage": "Entry Created", "count": total_entries, "yield": round(total_entries / total_execution_pass * 100, 2) if total_execution_pass > 0 else 0.0},
        {"stage": "Exit Completed", "count": total_exits, "yield": round(total_exits / total_entries * 100, 2) if total_entries > 0 else 0.0},
    ]

    stage_losses = [
        {"stage": "Signal Filters", "lost": total_candidates - total_signal_pass},
        {"stage": "EV Filters", "lost": total_signal_pass - total_ev_pass},
        {"stage": "Risk Filters", "lost": total_ev_pass - total_risk_pass},
        {"stage": "Execution Gates", "lost": total_risk_pass - total_execution_pass},
        {"stage": "Fill Slippage", "lost": total_execution_pass - total_entries},
    ]

    top_kill_reasons = [{"reason": reason, "count": count} for reason, count in kill_reasons_counter.most_common(5)]
    opportunity_cost = [{"reason": reason, "lost_candidates": count} for reason, count in opportunity_counter.most_common(5)]

    return {
        "status": "OK" if total_candidates > 0 else "PARTIAL",
        "summary": {
            "candidate_count": total_candidates,
            "signal_pass_count": total_signal_pass,
            "ev_pass_count": total_ev_pass,
            "risk_pass_count": total_risk_pass,
            "execution_pass_count": total_execution_pass,
            "entry_count": total_entries,
            "exit_count": total_exits
        },
        "funnel": funnel,
        "stage_losses": stage_losses,
        "top_kill_reasons": top_kill_reasons,
        "opportunity_cost": opportunity_cost,
        "leaderboard": leaderboard,
        "alerts": []
    }


def _apply_research_reports(state: dict[str, Any], root: Path) -> bool:
    reports = root / "reports"
    found = False

    replay_path = _latest_json_file(reports, "replay_report_*.json")
    replay, replay_error = _read_json(replay_path) if replay_path else (None, "missing")
    if replay:
        found = True
        phase2 = replay.get("phase2_coverage") if isinstance(replay.get("phase2_coverage"), dict) else {}
        state["research_analytics"]["reports"]["replay"] = {
            "path": str(replay_path),
            "date_from": replay.get("date_from"),
            "date_to": replay.get("date_to"),
            "run_id": replay.get("run_id"),
            "events_loaded": replay.get("events_loaded"),
            "total_trades": replay.get("total_trades"),
            "wins": replay.get("wins"),
            "losses": replay.get("losses"),
            "win_rate": replay.get("win_rate"),
            "gross_pnl": replay.get("gross_pnl"),
            "average_pnl": replay.get("average_pnl"),
            "approved_decisions": replay.get("approved_decisions"),
            "rejected_decisions": replay.get("rejected_decisions"),
            "risk_reject_count": replay.get("risk_reject_count"),
            "lifecycle_replay_confidence": replay.get("lifecycle_replay_confidence"),
            "phase2_coverage_status": phase2.get("status"),
            "missed_starter_candidate_count": _safe_list_count(replay.get("missed_starter_candidates")),
            "top_skip_reasons": replay.get("top_skip_reasons", []),
            "bad_json_lines": replay.get("bad_json_lines"),
        }
        state["research_analytics"]["replay_analytics"] = _extract_replay_analytics(replay, reports)
    else:
        state["research_analytics"]["replay_analytics"] = _extract_replay_analytics(None, reports)
        if replay_error != "missing":
            _research_alert(state, "REPLAY_REPORT_UNREADABLE", str(replay_error), replay_path or reports)

    no_entry_path = _latest_json_file(reports, "no_entry_report_*.json")
    no_entry, no_entry_error = _read_json(no_entry_path) if no_entry_path else (None, "missing")
    if no_entry:
        found = True
        state["research_analytics"]["reports"]["no_entry"] = {
            "path": str(no_entry_path),
            "date": no_entry.get("date"),
            "total_scanned": no_entry.get("total_scanned"),
            "total_entered": no_entry.get("total_entered"),
            "total_skipped": no_entry.get("total_skipped"),
            "root_cause_category": no_entry.get("root_cause_category"),
            "root_cause_counts": no_entry.get("root_cause_counts", {}),
            "root_cause_details": no_entry.get("root_cause_details", []),
            "top_skip_reasons": no_entry.get("top_skip_reasons", []),
            "recommendations": no_entry.get("recommendations", []),
            "market_data_quality": no_entry.get("market_data_quality", {}),
        }
        state["research_analytics"]["no_entry_analytics"] = _extract_no_entry_analytics(no_entry)
    else:
        state["research_analytics"]["no_entry_analytics"] = _extract_no_entry_analytics(None)
        if no_entry_error != "missing":
            _research_alert(state, "NO_ENTRY_REPORT_UNREADABLE", str(no_entry_error), no_entry_path or reports)

    session_path = _latest_json_file(reports, "session_runtime_evaluation_*.json")
    session, session_error = _read_json(session_path) if session_path else (None, "missing")
    if session:
        found = True
        state["research_analytics"]["reports"]["session_runtime"] = {
            "path": str(session_path),
            "session_status": session.get("session_status"),
            "primary_bottleneck": session.get("primary_bottleneck"),
            "secondary_bottleneck": session.get("secondary_bottleneck"),
            "scanned": session.get("scanned"),
            "entered": session.get("entered"),
            "skipped": session.get("skipped"),
            "top_skip_reasons": session.get("top_skip_reasons", []),
            "recommendations": session.get("recommendations", []),
            "inventory_replay_readiness": session.get("inventory_replay_readiness", {}),
            "timing_quality": session.get("timing_quality", {}),
        }
        state["research_analytics"]["session_analytics"] = _extract_session_analytics(session, reports)
    else:
        state["research_analytics"]["session_analytics"] = _extract_session_analytics(None, reports)
        if session_error != "missing":
            _research_alert(state, "SESSION_RUNTIME_REPORT_UNREADABLE", str(session_error), session_path or reports)

    quality_path = _latest_json_file(reports, "quant_data_quality_*.json")
    quality, quality_error = _read_json(quality_path) if quality_path else (None, "missing")
    if quality:
        found = True
        replay_continuity = quality.get("replay_continuity") if isinstance(quality.get("replay_continuity"), dict) else {}
        research_log_integrity = quality.get("research_log_integrity") if isinstance(quality.get("research_log_integrity"), dict) else {}
        phase2 = quality.get("phase2_coverage") if isinstance(quality.get("phase2_coverage"), dict) else {}
        state["research_analytics"]["reports"]["data_quality"] = {
            "path": str(quality_path),
            "ok": quality.get("ok"),
            "files_scanned": quality.get("files_scanned"),
            "lines_scanned": quality.get("lines_scanned"),
            "valid_events": quality.get("valid_events"),
            "bad_json_lines": quality.get("bad_json_lines"),
            "missing_required_fields": quality.get("missing_required_fields"),
            "invalid_timestamps": quality.get("invalid_timestamps"),
            "invalid_event_types": quality.get("invalid_event_types"),
            "invalid_modes": quality.get("invalid_modes"),
            "invalid_numeric_fields": quality.get("invalid_numeric_fields"),
            "empty_files": quality.get("empty_files"),
            "unreadable_files": quality.get("unreadable_files"),
            "replay_continuity_status": replay_continuity.get("status"),
            "trustworthy_for_replay": replay_continuity.get("trustworthy_for_replay"),
            "research_log_integrity_status": research_log_integrity.get("status"),
            "phase2_coverage_status": phase2.get("status"),
        }
    elif quality_error != "missing":
        _research_alert(state, "DATA_QUALITY_REPORT_UNREADABLE", str(quality_error), quality_path or reports)

    state["research_analytics"]["lifecycle_analytics"] = _extract_lifecycle_analytics(reports)
    return found


def _apply_research_analytics(state: dict[str, Any], root: Path) -> None:
    research_path = root / "research_state" / "latest_research_state.md"
    parsed, error = _parse_research_state_markdown(research_path)
    has_research_state = parsed is not None and error is None
    if parsed:
        state["research_analytics"]["latest_research_state"].update(parsed["latest_research_state"])
        state["research_analytics"]["candidate_loss_reasons"] = parsed["candidate_loss_reasons"]
        state["research_analytics"]["lifecycle_bottlenecks"] = parsed["lifecycle_bottlenecks"]
        state["research_analytics"]["ev_null_reasons"] = parsed["ev_null_reasons"]
    if error and error != "missing":
        _research_alert(state, "RESEARCH_STATE_PARSE_WARNING", str(error), research_path)

    has_reports = _apply_research_reports(state, root)
    if has_research_state and has_reports and not state["research_analytics"]["alerts"]:
        state["research_analytics"]["status"] = "OK"
    elif has_research_state or has_reports or state["research_analytics"]["alerts"]:
        state["research_analytics"]["status"] = "PARTIAL"
    else:
        state["research_analytics"]["status"] = "MISSING"


def build_dashboard_state(
    runtime_root: str | Path = "runtime",
    *,
    date: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a derived dashboard state from runtime files without modifying sources."""

    root = Path(runtime_root)
    now_dt = now.astimezone(UTC) if now else _utc_now()
    source_date = date or now_dt.date().isoformat()
    state = _empty_state(root, source_date, now_dt)

    _apply_bot_status(state, root, now_dt)
    _apply_owner(state, root, now_dt)
    _apply_trades(state, root, source_date, now_dt)
    _apply_decisions(state, root, source_date, now_dt)
    _apply_risk(state, root, source_date, now_dt)
    _apply_health(state, root, source_date, now_dt)
    _apply_storage(state, root, now_dt)
    _apply_reports(state, root)
    _apply_research_exports(state, root)
    _apply_research_analytics(state, root)

    if state["meta"]["partial"]:
        state["meta"]["state_status"] = "PARTIAL"
    elif state["alerts"]["active"]:
        state["meta"]["state_status"] = "PARTIAL"
        state["meta"]["partial"] = True
        state["meta"]["state_status_reason"] = "active alerts"
    else:
        state["meta"]["state_status"] = "OK"
        state["meta"]["state_status_reason"] = ""

    return state


def write_dashboard_state(state: dict[str, Any], output_path: str | Path = "runtime/dashboard_state.json") -> Path:
    """Atomically write dashboard state JSON."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    os.replace(tmp_path, path)
    return path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build read-only dashboard_state.json from runtime evidence.")
    parser.add_argument("--once", action="store_true", help="Build the dashboard state once and exit.")
    parser.add_argument("--output", default="runtime/dashboard_state.json", help="Output path for dashboard state JSON.")
    parser.add_argument("--date", default=None, help="UTC date to read, YYYY-MM-DD. Defaults to current UTC date.")
    parser.add_argument("--runtime-root", default="runtime", help="Runtime root directory. Defaults to runtime.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.once:
        parser.error("only --once mode is implemented")

    state = build_dashboard_state(args.runtime_root, date=args.date)
    output = write_dashboard_state(state, args.output)
    print(f"dashboard_state_written={output}")
    print(f"state_status={state['meta']['state_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
