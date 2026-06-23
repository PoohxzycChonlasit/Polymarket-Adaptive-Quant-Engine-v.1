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
