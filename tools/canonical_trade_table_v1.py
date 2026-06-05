from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable


DEFAULT_QUANT_DATA_DIR = Path("runtime/quant_data")
DEFAULT_OUTPUT_DIR = Path("runtime/research_exports")
CSV_NAME = "completed_trades_v1.csv"
SUMMARY_NAME = "completed_trades_v1_summary.md"
CSV_V1_1_NAME = "completed_trades_v1_1.csv"
SUMMARY_V1_1_NAME = "completed_trades_v1_1_summary.md"
CSV_V1_2_NAME = "completed_trades_v1_2.csv"
SUMMARY_V1_2_NAME = "completed_trades_v1_2_summary.md"
PNL_TOLERANCE_USDC = 1e-6
MOS_ASSUMPTION_SHARES = 1.0


@dataclass
class BuildResult:
    rows: list[dict[str, Any]]
    summary: dict[str, Any]
    breakdowns: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


def _get(event: dict[str, Any], *names: str) -> Any:
    payload = _payload(event)
    envelope = payload.get("entry_model_truth_envelope_v1")
    envelope_data = envelope if isinstance(envelope, dict) else {}
    for name in names:
        if name in payload and payload.get(name) not in ("", "null"):
            return payload.get(name)
        if name in event and event.get(name) not in ("", "null"):
            return event.get(name)
        if name in envelope_data and envelope_data.get(name) not in ("", "null"):
            return envelope_data.get(name)
    return None


def _event_type(event: dict[str, Any]) -> str:
    return str(event.get("event_type") or _payload(event).get("event_type") or "").strip()


def _run_id(event: dict[str, Any]) -> str:
    return str(event.get("run_id") or _payload(event).get("run_id") or "").strip()


def _paper_key(event: dict[str, Any]) -> str:
    return str(_get(event, "paper_trade_replay_key") or "").strip()


def _join_key(event: dict[str, Any]) -> tuple[str, str] | None:
    run_id = _run_id(event)
    paper_key = _paper_key(event)
    if not run_id or not paper_key:
        return None
    return (run_id, paper_key)


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _ts_text(event: dict[str, Any], *names: str) -> str | None:
    for name in names:
        value = _get(event, name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    timestamp = event.get("timestamp_utc")
    if isinstance(timestamp, str) and timestamp.strip():
        return timestamp.strip()
    return None


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _first_float(event: dict[str, Any], *names: str) -> float | None:
    for name in names:
        value = _to_float(_get(event, name))
        if value is not None:
            return value
    return None


def _first_text(event: dict[str, Any], *names: str) -> str | None:
    for name in names:
        value = _get(event, name)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _side_from_key(paper_key: str) -> str | None:
    parts = paper_key.split("|")
    if len(parts) >= 4 and parts[3].strip():
        return parts[3].strip().upper()
    return None


def _asset_from_key(paper_key: str) -> str | None:
    parts = paper_key.split("|")
    if len(parts) >= 3 and parts[2].strip():
        return parts[2].strip().upper()
    return None


def _epoch_from_key(paper_key: str) -> int | None:
    parts = paper_key.split("|")
    if len(parts) >= 2:
        value = _to_float(parts[1])
        return int(value) if value is not None else None
    return None


def _condition_from_key(paper_key: str) -> str | None:
    parts = paper_key.split("|")
    return parts[0].strip() if parts and parts[0].strip() else None


def _token_from_key(paper_key: str) -> str | None:
    parts = paper_key.split("|")
    return parts[4].strip() if len(parts) >= 5 and parts[4].strip() else None


def _canonical_trade_id(run_id: str, paper_key: str) -> str:
    digest = hashlib.sha1(f"{run_id}|{paper_key}".encode("utf-8")).hexdigest()
    return f"ct_{digest[:20]}"


def _price_bucket(price: float | None) -> str:
    if price is None:
        return "unknown"
    if price < 0.25:
        return "0.00-0.25"
    if price < 0.50:
        return "0.25-0.50"
    if price < 0.75:
        return "0.50-0.75"
    return "0.75-1.00"


def _hold_bucket(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    if seconds < 15:
        return "0-15s"
    if seconds < 30:
        return "15-30s"
    if seconds < 45:
        return "30-45s"
    if seconds < 60:
        return "45-60s"
    return "60s+"


def _quartile_buckets(rows: list[dict[str, Any]], field: str, target: str) -> None:
    values = sorted(value for row in rows for value in [_to_float(row.get(field))] if value is not None)
    if not values:
        for row in rows:
            row[target] = "unknown"
        return

    def cutoff(index_fraction: float) -> float:
        index = min(len(values) - 1, max(0, int(round((len(values) - 1) * index_fraction))))
        return values[index]

    q1, q2, q3 = cutoff(0.25), cutoff(0.50), cutoff(0.75)
    for row in rows:
        value = _to_float(row.get(field))
        if value is None:
            row[target] = "unknown"
        elif value <= q1:
            row[target] = "Q1"
        elif value <= q2:
            row[target] = "Q2"
        elif value <= q3:
            row[target] = "Q3"
        else:
            row[target] = "Q4"


def _classification(row: dict[str, Any], *, has_decision: bool, has_execution: bool, reconstructed: bool) -> str:
    if row["quarantine_flag"]:
        return "UNTRUSTWORTHY"
    if reconstructed:
        return "RECONSTRUCTED"
    if has_decision and has_execution:
        return "FULL"
    return "PARTIAL"


def _outcome(row: dict[str, Any], close: dict[str, Any]) -> tuple[str | None, bool]:
    result = (_first_text(close, "trade_result", "result", "exit_type") or "").upper()
    reason = (_first_text(close, "exit_reason", "reason") or "").upper()
    pnl = _to_float(row.get("pnl_usdc"))
    if result in {"TP", "WIN", "PROFIT"} or "TAKE_PROFIT" in reason:
        return "WIN", False
    if result in {"SL", "LOSS", "STOP"} or "STOP" in reason:
        return "LOSS", False
    if pnl is None:
        return None, False
    return ("WIN" if pnl > 0 else "LOSS" if pnl < 0 else "FLAT"), True


def _path_price(event: dict[str, Any]) -> float | None:
    return _first_float(
        event,
        "current_mark_price",
        "mark_price",
        "path_price",
        "token_price",
        "price",
        "mid_price",
        "current_price",
        "exit_price",
    )


def _checkpoint_label(event: dict[str, Any]) -> str:
    value = _get(event, "checkpoint_elapsed_s") or _get(event, "checkpoint_reason") or _event_type(event)
    return str(value or "").strip()


def _mfe_mae(path_events: list[dict[str, Any]], entry_price: float | None, shares: float | None) -> dict[str, Any]:
    prices = [price for event in path_events for price in [_path_price(event)] if price is not None]
    checkpoints = {_checkpoint_label(event) for event in path_events}
    if entry_price is None or not prices:
        return {
            "mfe_price": None,
            "mae_price": None,
            "mfe_usdc": None,
            "mae_usdc": None,
            "path_full_coverage": False,
            "checkpoint_count": len(path_events),
        }
    max_price = max(prices)
    min_price = min(prices)
    size = shares or 0.0
    required = {"15", "30", "45", "60", "event_end"}
    normalized_checkpoints = {str(item).replace(".0", "") for item in checkpoints}
    return {
        "mfe_price": max_price,
        "mae_price": min_price,
        "mfe_usdc": (max_price - entry_price) * size if shares is not None else None,
        "mae_usdc": (min_price - entry_price) * size if shares is not None else None,
        "path_full_coverage": required.issubset(normalized_checkpoints),
        "checkpoint_count": len(path_events),
    }


def _event_file(event: dict[str, Any]) -> str:
    return str(event.get("_source_file") or "")


def _index_by_key(events: Iterable[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    indexed: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        key = _join_key(event)
        if key:
            indexed[key].append(event)
    return indexed


def build_canonical_trade_table(
    *,
    trade_events: Iterable[dict[str, Any]],
    decision_events: Iterable[dict[str, Any]] = (),
    execution_events: Iterable[dict[str, Any]] = (),
    path_truth_events: Iterable[dict[str, Any]] = (),
) -> BuildResult:
    trade_events = list(trade_events)
    opens = [event for event in trade_events if _event_type(event) == "trade_open"]
    closes = [event for event in trade_events if _event_type(event) == "trade_close"]
    opens_by_key = _index_by_key(opens)
    closes_by_key = _index_by_key(closes)
    decisions_by_key = _index_by_key(decision_events)
    executions_by_key = _index_by_key(execution_events)
    path_by_key = _index_by_key(path_truth_events)
    completed_keys = sorted(set(opens_by_key) & set(closes_by_key))

    rows: list[dict[str, Any]] = []
    duplicate_key_count = 0
    for key in completed_keys:
        open_rows = sorted(opens_by_key[key], key=lambda event: _ts_text(event) or "")
        close_rows = sorted(closes_by_key[key], key=lambda event: _ts_text(event) or "")
        open_event = open_rows[0]
        close_event = close_rows[0]
        decision_event = decisions_by_key.get(key, [None])[-1]
        execution_event = executions_by_key.get(key, [None])[-1]
        path_events = path_by_key.get(key, [])
        run_id, paper_key = key
        duplicate_reasons: list[str] = []
        if len(open_rows) > 1:
            duplicate_reasons.append(f"duplicate_open_count={len(open_rows)}")
        if len(close_rows) > 1:
            duplicate_reasons.append(f"duplicate_close_count={len(close_rows)}")
        if duplicate_reasons:
            duplicate_key_count += 1

        entry_ts_text = _ts_text(open_event, "entry_timestamp", "entry_ts", "ts")
        exit_ts_text = _ts_text(close_event, "exit_timestamp", "exit_ts", "ts")
        entry_ts = _parse_ts(entry_ts_text)
        exit_ts = _parse_ts(exit_ts_text)
        hold_seconds = _first_float(close_event, "hold_seconds", "holding_seconds")
        if hold_seconds is None and entry_ts and exit_ts:
            hold_seconds = (exit_ts - entry_ts).total_seconds()

        side = (
            _first_text(decision_event or {}, "side", "selected_side", "outcome")
            or _first_text(close_event, "side", "outcome")
            or _side_from_key(paper_key)
        )
        if side == "BUY":
            side = _side_from_key(paper_key)
        asset = (
            _first_text(decision_event or {}, "asset", "ticker")
            or _first_text(open_event, "asset", "ticker")
            or _first_text(close_event, "asset", "ticker")
            or _asset_from_key(paper_key)
        )
        entry_price = _first_float(open_event, "entry_price", "price", "market_price")
        exit_price = _first_float(close_event, "exit_price", "price")
        shares = _first_float(close_event, "size", "shares", "filled_size", "quantity") or _first_float(open_event, "size", "shares", "filled_size", "quantity")
        pnl = _first_float(close_event, "pnl_usdc", "pnl", "realized_pnl")
        pnl_recomputed = (exit_price - entry_price) * shares if None not in (entry_price, exit_price, shares) else None

        row: dict[str, Any] = {
            "canonical_trade_id": _canonical_trade_id(run_id, paper_key),
            "run_id": run_id,
            "paper_trade_replay_key": paper_key,
            "condition_id": _first_text(open_event, "condition_id") or _condition_from_key(paper_key),
            "token_id": _first_text(open_event, "token_id") or _token_from_key(paper_key),
            "market_slug": _first_text(open_event, "market_slug") or _first_text(close_event, "market_slug"),
            "asset": str(asset or "").upper() or None,
            "side": str(side or "").upper() or None,
            "entry_ts": entry_ts_text,
            "exit_ts": exit_ts_text,
            "hold_seconds": hold_seconds,
            "session_hour_utc": entry_ts.hour if entry_ts else None,
            "epoch_start_ts": _first_float(open_event, "epoch_start_ts", "epoch_start", "market_epoch_start") or _epoch_from_key(paper_key),
            "lifecycle_phase": _first_text(decision_event or {}, "lifecycle_phase") or _first_text(open_event, "lifecycle_phase"),
            "regime": _first_text(decision_event or {}, "market_regime", "regime", "trend_regime") or _first_text(open_event, "market_regime", "regime", "trend_regime"),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "shares": shares,
            "notional_entry": entry_price * shares if None not in (entry_price, shares) else None,
            "notional_exit": exit_price * shares if None not in (exit_price, shares) else None,
            "pnl_usdc": pnl,
            "pnl_recomputed": pnl_recomputed,
            "signal_pnl": pnl,
            "paper_pnl": pnl,
            "executable_pnl": None,
            "executable_pnl_status": "BLOCKED_NO_TRUE_EXECUTABLE_DATA",
            "exit_reason": _first_text(close_event, "exit_reason", "reason"),
            "trade_result": _first_text(close_event, "trade_result", "result", "exit_type"),
            "model_output_ready": _get(decision_event or open_event, "model_output_ready"),
            "true_probability": _first_float(decision_event or open_event, "true_probability"),
            "fair_value": _first_float(decision_event or open_event, "fair_value"),
            "expected_value": _first_float(decision_event or open_event, "expected_value", "ev_after_spread", "ev"),
            "ev_after_spread": _first_float(decision_event or open_event, "ev_after_spread", "expected_value", "ev"),
            "confidence": _first_float(decision_event or open_event, "confidence"),
            "probability_model_reason": _first_text(decision_event or open_event, "probability_model_reason"),
            "distance_from_ptb": _first_float(decision_event or open_event, "distance_from_ptb", "distance_from_ptb_pct"),
            "quote_age_at_submit_ms": _first_float(execution_event or {}, "quote_age_at_submit_ms", "quote_stale_ms", "quote_age_ms"),
            "quote_age_at_fill_ms": _first_float(execution_event or {}, "quote_age_at_fill_ms"),
            "liquidity_state": _first_text(execution_event or {}, "liquidity_state", "liquidity_depth_state"),
            "spread": _first_float(decision_event or open_event, "spread"),
            "decision_joined": decision_event is not None,
            "execution_joined": execution_event is not None,
            "path_truth_joined": bool(path_events),
            "join_confidence": "DIRECT",
            "quarantine_flag": False,
            "quarantine_reason": "",
            "source_files": ";".join(sorted({item for item in (_event_file(open_event), _event_file(close_event), _event_file(decision_event or {}), _event_file(execution_event or {})) if item})),
        }

        if row["distance_from_ptb"] is None and row["probability_model_reason"]:
            match = re.search(r"distance=([+-]?\d+(?:\.\d+)?)", str(row["probability_model_reason"]))
            if match:
                row["distance_from_ptb"] = _to_float(match.group(1))

        path_metrics = _mfe_mae(path_events, entry_price, shares)
        row.update(path_metrics)
        row["fast_close"] = hold_seconds is not None and hold_seconds < 60
        row["entry_price_bucket"] = _price_bucket(entry_price)
        row["hold_time_bucket"] = _hold_bucket(hold_seconds)
        row["mos_assumption"] = MOS_ASSUMPTION_SHARES
        row["mos_source"] = "research_assumption"
        row["dust_zone"] = shares is not None and shares < MOS_ASSUMPTION_SHARES
        row["executable_minimum_met"] = shares is not None and shares >= MOS_ASSUMPTION_SHARES
        row["executable_candidate"] = bool(row["executable_minimum_met"] and row["quote_age_at_submit_ms"] is not None and row["liquidity_state"])

        quarantine_reasons = list(duplicate_reasons)
        if entry_ts and exit_ts and not entry_ts < exit_ts:
            quarantine_reasons.append("entry_exit_order_invalid")
        if entry_price is None or not 0 <= entry_price <= 1:
            quarantine_reasons.append("entry_price_invalid")
        if exit_price is None or not 0 <= exit_price <= 1:
            quarantine_reasons.append("exit_price_invalid")
        if shares is None or shares <= 0:
            quarantine_reasons.append("shares_invalid")
        if pnl is None:
            quarantine_reasons.append("pnl_missing")
        if pnl is not None and pnl_recomputed is not None and abs(pnl - pnl_recomputed) > PNL_TOLERANCE_USDC:
            quarantine_reasons.append(f"pnl_mismatch={pnl - pnl_recomputed:.8f}")

        outcome, reconstructed_outcome = _outcome(row, close_event)
        row["outcome_win_loss"] = outcome
        row["tp_hit"] = (row["trade_result"] or "").upper() == "TP" or (row["exit_reason"] or "").lower().startswith("take_profit")
        row["sl_hit"] = (row["trade_result"] or "").upper() == "SL" or "stop" in str(row["exit_reason"] or "").lower()
        row["expired"] = "expiry" in str(row["exit_reason"] or "").lower() or (row["trade_result"] or "").upper() == "EXPIRY"
        if reconstructed_outcome:
            quarantine_reasons.append("outcome_reconstructed")

        row["quarantine_flag"] = any(reason for reason in quarantine_reasons if not reason.startswith("outcome_reconstructed"))
        row["quarantine_reason"] = ";".join(quarantine_reasons)
        row["row_completeness"] = _classification(
            row,
            has_decision=decision_event is not None,
            has_execution=execution_event is not None,
            reconstructed=reconstructed_outcome,
        )
        if row["row_completeness"] == "UNTRUSTWORTHY":
            row["join_confidence"] = "BLOCKED"
        rows.append(row)

    _quartile_buckets(rows, "expected_value", "ev_quartile")
    _quartile_buckets(rows, "confidence", "confidence_quartile")
    summary = _build_summary(
        rows,
        total_opens=len(opens),
        total_closes=len(closes),
        unmatched_opens=max(0, len(opens) - len(completed_keys)),
        unmatched_closes=max(0, len(closes) - len(completed_keys)),
        duplicate_key_count=duplicate_key_count,
    )
    return BuildResult(rows=rows, summary=summary, breakdowns=_build_breakdowns(rows))


def _rate(count: int, total: int) -> float:
    return count / total if total else 0.0


def _profit_factor(pnls: list[float]) -> float | None:
    wins = sum(value for value in pnls if value > 0)
    losses = abs(sum(value for value in pnls if value < 0))
    if losses == 0:
        return None if wins == 0 else float("inf")
    return wins / losses


def _build_summary(
    rows: list[dict[str, Any]],
    *,
    total_opens: int,
    total_closes: int,
    unmatched_opens: int,
    unmatched_closes: int,
    duplicate_key_count: int,
) -> dict[str, Any]:
    total = len(rows)
    pnls = [value for row in rows for value in [_to_float(row.get("pnl_usdc"))] if value is not None]
    full_rows = [row for row in rows if row.get("row_completeness") == "FULL"]
    full_pnls = [value for row in full_rows for value in [_to_float(row.get("pnl_usdc"))] if value is not None]
    wins = sum(1 for row in rows if row.get("outcome_win_loss") == "WIN")
    return {
        "total_trade_open_rows": total_opens,
        "total_trade_close_rows": total_closes,
        "completed_trade_count": total,
        "unmatched_open_count": unmatched_opens,
        "unmatched_close_count": unmatched_closes,
        "duplicate_key_count": duplicate_key_count,
        "FULL_rows": sum(1 for row in rows if row.get("row_completeness") == "FULL"),
        "PARTIAL_rows": sum(1 for row in rows if row.get("row_completeness") == "PARTIAL"),
        "RECONSTRUCTED_rows": sum(1 for row in rows if row.get("row_completeness") == "RECONSTRUCTED"),
        "UNTRUSTWORTHY_rows": sum(1 for row in rows if row.get("row_completeness") == "UNTRUSTWORTHY"),
        "decision_join_rate": _rate(sum(1 for row in rows if row.get("decision_joined")), total),
        "execution_join_rate": _rate(sum(1 for row in rows if row.get("execution_joined")), total),
        "path_truth_join_rate": _rate(sum(1 for row in rows if row.get("path_truth_joined")), total),
        "MFE_available_count": sum(1 for row in rows if row.get("mfe_price") is not None),
        "MAE_available_count": sum(1 for row in rows if row.get("mae_price") is not None),
        "win_rate": _rate(wins, total),
        "profit_factor": _profit_factor(pnls),
        "mean_pnl": mean(pnls) if pnls else 0.0,
        "median_pnl": median(pnls) if pnls else 0.0,
        "total_pnl": sum(pnls),
        "TP_count": sum(1 for row in rows if row.get("tp_hit")),
        "SL_count": sum(1 for row in rows if row.get("sl_hit")),
        "fast_close_count": sum(1 for row in rows if row.get("fast_close")),
        "dust_zone_count": sum(1 for row in rows if row.get("dust_zone")),
        "MOS_pass_count": sum(1 for row in rows if row.get("executable_minimum_met")),
        "executable_candidate_count": sum(1 for row in rows if row.get("executable_candidate")),
        "executable_pnl_approved_count": sum(1 for row in rows if row.get("executable_pnl_status") == "APPROVED"),
        "FULL_expectancy_total_pnl": sum(full_pnls),
        "FULL_expectancy_mean_pnl": mean(full_pnls) if full_pnls else 0.0,
        "FULL_expectancy_win_rate": _rate(sum(1 for row in full_rows if row.get("outcome_win_loss") == "WIN"), len(full_rows)),
    }


def _build_breakdown(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        value = row.get(field)
        grouped[str(value if value not in (None, "") else "unknown")].append(row)
    output: list[dict[str, Any]] = []
    for value, items in sorted(grouped.items()):
        pnls = [pnl for row in items for pnl in [_to_float(row.get("pnl_usdc"))] if pnl is not None]
        wins = sum(1 for row in items if row.get("outcome_win_loss") == "WIN")
        output.append({
            "bucket": value,
            "count": len(items),
            "wins": wins,
            "losses": sum(1 for row in items if row.get("outcome_win_loss") == "LOSS"),
            "win_rate": _rate(wins, len(items)),
            "total_pnl": sum(pnls),
            "mean_pnl": mean(pnls) if pnls else 0.0,
        })
    return output


def _build_breakdowns(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    fields = (
        "asset",
        "side",
        "lifecycle_phase",
        "regime",
        "session_hour_utc",
        "entry_price_bucket",
        "ev_quartile",
        "confidence_quartile",
        "hold_time_bucket",
        "exit_reason",
        "row_completeness",
        "join_confidence",
    )
    return {field: _build_breakdown(rows, field) for field in fields}


def _iter_jsonl(paths: Iterable[Path], *, key_filter: set[tuple[str, str]] | None = None) -> Iterable[dict[str, Any]]:
    for path in paths:
        try:
            with path.open(encoding="utf-8") as handle:
                for line_number, raw_line in enumerate(handle, start=1):
                    text = raw_line.strip()
                    if not text:
                        continue
                    try:
                        event = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(event, dict):
                        continue
                    event["_source_file"] = f"{path}:{line_number}"
                    if key_filter is not None and _join_key(event) not in key_filter:
                        continue
                    yield event
        except OSError:
            continue


def _paths(base_dir: Path, category: str) -> list[Path]:
    root = base_dir / category
    if not root.exists():
        return []
    return sorted(root.glob("*.jsonl"))


def build_from_files(base_dir: str | Path = DEFAULT_QUANT_DATA_DIR) -> BuildResult:
    root = Path(base_dir)
    trade_events = list(_iter_jsonl(_paths(root, "trade_journal")))
    target_keys = {key for event in trade_events for key in [_join_key(event)] if key}
    decision_events = list(_iter_jsonl(_paths(root, "decision_log"), key_filter=target_keys))
    execution_events = list(_iter_jsonl(_paths(root, "execution_log"), key_filter=target_keys))
    path_events = list(_iter_jsonl(_paths(root, "path_truth"), key_filter=target_keys))
    return build_canonical_trade_table(
        trade_events=trade_events,
        decision_events=decision_events,
        execution_events=execution_events,
        path_truth_events=path_events,
    )


def _event_payload_name(event: dict[str, Any]) -> str:
    return str(_payload(event).get("event") or _event_type(event) or "").strip()


def _preferred_entry_execution(events: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    if not events:
        return None, "MISSING"
    ordered = sorted(events, key=lambda event: _ts_text(event, "order_submit_ts", "order_intent_ts") or _ts_text(event) or "")
    for event in ordered:
        if _event_payload_name(event) == "order_submit_attempt":
            return event, "DIRECT"
    for event in ordered:
        if _event_payload_name(event) == "order_intent_approved":
            return event, "STRONG"
    return ordered[-1], "WEAK"


def _preferred_entry_risk(events: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    if not events:
        return None, "MISSING"
    prioritized = sorted(
        events,
        key=lambda event: (
            2 if str(_get(event, "risk_state") or "").lower() in {"approved", "blocked"} else 1,
            _ts_text(event) or "",
        ),
    )
    return prioritized[-1], "DIRECT"


def _preferred_fill_execution(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    ordered = sorted(events, key=lambda event: _ts_text(event) or "")
    for event in ordered:
        if _event_payload_name(event) == "paper_fill":
            return event
    return None


def _preferred_joined_decision(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not events:
        return None
    return sorted(events, key=lambda event: _ts_text(event) or "")[-1]


def _seconds_between(later: datetime | None, earlier: datetime | None) -> float | None:
    if later is None or earlier is None:
        return None
    return (later - earlier).total_seconds()


def _bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _enrichment_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    return {
        "total_rows": total,
        "rows_with_risk_mode_entry": sum(1 for row in rows if row.get("risk_mode_entry") not in (None, "", "unknown")),
        "rows_with_bankroll_mode_entry": sum(1 for row in rows if row.get("bankroll_mode_entry") not in (None, "", "unknown")),
        "rows_with_entry_submit_event_type": sum(1 for row in rows if row.get("entry_submit_event_type") not in (None, "")),
        "rows_with_entry_submit_ts": sum(1 for row in rows if row.get("entry_submit_ts") not in (None, "")),
        "rows_with_entry_quote_age_ms": sum(1 for row in rows if row.get("entry_quote_age_ms") not in (None, "")),
        "enrichment_join_rate": _rate(sum(1 for row in rows if row.get("entry_risk_join_confidence") != "MISSING"), total),
        "missing_risk_lineage_count": sum(1 for row in rows if row.get("entry_risk_join_confidence") == "MISSING"),
        "missing_execution_lineage_count": sum(1 for row in rows if row.get("execution_join_confidence") == "MISSING"),
    }


def enrich_canonical_rows_v1_1(
    rows: Iterable[dict[str, Any]],
    *,
    execution_events: Iterable[dict[str, Any]] = (),
    risk_events: Iterable[dict[str, Any]] = (),
    trade_events: Iterable[dict[str, Any]] = (),
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return V1 rows enriched with entry risk/execution lineage.

    This is offline-only enrichment. It does not reinterpret identity or fabricate
    executable PnL.
    """
    base_rows = [dict(row) for row in rows]
    execution_by_key = _index_by_key(execution_events)
    risk_by_key = _index_by_key(risk_events)
    trade_open_by_key = _index_by_key(event for event in trade_events if _event_type(event) == "trade_open")
    enriched: list[dict[str, Any]] = []
    for row in base_rows:
        key = (str(row.get("run_id") or ""), str(row.get("paper_trade_replay_key") or ""))
        entry_execution, execution_confidence = _preferred_entry_execution(execution_by_key.get(key, []))
        entry_risk, risk_confidence = _preferred_entry_risk(risk_by_key.get(key, []))
        entry_trade = (trade_open_by_key.get(key) or [None])[0]
        risk_source_event = entry_execution or entry_risk
        bankroll_source_event = entry_execution or entry_risk or entry_trade
        if _first_text(bankroll_source_event or {}, "bankroll_mode") in (None, "unknown") and entry_trade is not None:
            bankroll_source_event = entry_trade
        risk_join_source = "missing"
        entry_risk_confidence = "MISSING"
        if entry_execution is not None:
            entry_risk_confidence = execution_confidence
            risk_join_source = f"execution_log.{_event_payload_name(entry_execution) or 'execution'}"
        elif entry_risk is not None:
            entry_risk_confidence = risk_confidence
            risk_join_source = "risk_log.risk_event"

        row.update(
            {
                "risk_mode_entry": _first_text(risk_source_event or {}, "risk_mode") or "unknown",
                "bankroll_mode_entry": _first_text(bankroll_source_event or {}, "bankroll_mode") or "unknown",
                "bankroll_tier_entry": _first_text(bankroll_source_event or {}, "bankroll_tier_id", "tier") or "unknown",
                "bankroll_family_entry": _first_text(bankroll_source_event or {}, "bankroll_family") or "unknown",
                "risk_profile_entry": _first_text(bankroll_source_event or {}, "bankroll_risk_profile", "risk_profile") or "unknown",
                "micro_survival_active_entry": _bool_or_none(_get(bankroll_source_event or {}, "micro_survival_active")),
                "available_risk_budget_entry": _first_float(bankroll_source_event or {}, "available_risk_budget", "remaining_risk_budget"),
                "current_exposure_entry": _first_float(bankroll_source_event or {}, "current_exposure"),
                "entry_submit_event_type": _event_payload_name(entry_execution) if entry_execution is not None else "",
                "entry_submit_ts": _ts_text(entry_execution or {}, "order_submit_ts", "order_intent_ts") if entry_execution is not None else "",
                "entry_submit_price": _first_float(entry_execution or {}, "limit_price", "price", "signal_price", "market_price"),
                "entry_submit_size": _first_float(entry_execution or {}, "size", "shares", "filled_size"),
                "entry_quote_age_ms": _first_float(entry_execution or {}, "quote_age_at_submit_ms", "quote_stale_ms", "quote_age_ms"),
                "entry_risk_plan_present": _bool_or_none(_get(entry_execution or entry_risk or {}, "risk_plan_present")),
                "entry_risk_join_confidence": entry_risk_confidence,
                "entry_risk_join_source": risk_join_source,
                "execution_join_confidence": execution_confidence,
                "lineage_enrichment_version": "1.1",
            }
        )
        row["executable_pnl"] = row.get("executable_pnl") or None
        row["executable_pnl_status"] = row.get("executable_pnl_status") or "BLOCKED_NO_TRUE_EXECUTABLE_DATA"
        enriched.append(row)
    return enriched, _enrichment_summary(enriched)


LIFECYCLE_V1_2_FIELDS = (
    "trade_open_lifecycle_phase",
    "execution_fill_lifecycle_phase",
    "decision_join_lifecycle_phase",
    "decision_join_ts",
    "decision_join_ts_delta_from_open_s",
    "decision_join_ts_delta_from_close_s",
    "lifecycle_truth_status",
    "lifecycle_conflict_flag",
    "lifecycle_conflict_reason",
    "canonical_entry_lifecycle_phase",
    "canonical_entry_lifecycle_source",
)


def _lifecycle_v1_2_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    return {
        "total_rows": total,
        "rows_with_trade_open_lifecycle_phase": sum(1 for row in rows if row.get("trade_open_lifecycle_phase") not in (None, "")),
        "rows_with_execution_fill_lifecycle_phase": sum(1 for row in rows if row.get("execution_fill_lifecycle_phase") not in (None, "")),
        "rows_with_decision_join_lifecycle_phase": sum(1 for row in rows if row.get("decision_join_lifecycle_phase") not in (None, "")),
        "lifecycle_conflict_count": sum(1 for row in rows if row.get("lifecycle_conflict_flag") is True),
        "late_decision_join_count": sum(1 for row in rows if row.get("lifecycle_truth_status") == "LATE_DECISION_JOIN"),
        "canonical_entry_lifecycle_coverage_rate": _rate(
            sum(1 for row in rows if row.get("canonical_entry_lifecycle_phase") not in (None, "")),
            total,
        ),
    }


def enrich_canonical_rows_v1_2(
    rows: Iterable[dict[str, Any]],
    *,
    trade_events: Iterable[dict[str, Any]] = (),
    execution_events: Iterable[dict[str, Any]] = (),
    decision_events: Iterable[dict[str, Any]] = (),
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return CTT rows enriched with lifecycle truth lineage.

    This is offline-only enrichment. Trade-open lifecycle is authoritative for
    entry lifecycle, with execution fill as a fallback. Joined decision
    lifecycle is retained as reference and cannot override entry lifecycle.
    """
    base_rows = [dict(row) for row in rows]
    trade_open_by_key = _index_by_key(event for event in trade_events if _event_type(event) == "trade_open")
    execution_by_key = _index_by_key(execution_events)
    decision_by_key = _index_by_key(decision_events)
    enriched: list[dict[str, Any]] = []

    for row in base_rows:
        key = (str(row.get("run_id") or ""), str(row.get("paper_trade_replay_key") or ""))
        trade_open = (trade_open_by_key.get(key) or [None])[0]
        fill_execution = _preferred_fill_execution(execution_by_key.get(key, []))
        joined_decision = _preferred_joined_decision(decision_by_key.get(key, []))

        trade_open_lifecycle = _first_text(trade_open or {}, "lifecycle_phase")
        execution_fill_lifecycle = _first_text(fill_execution or {}, "lifecycle_phase")
        decision_lifecycle = _first_text(joined_decision or {}, "lifecycle_phase")
        decision_ts_text = _ts_text(joined_decision or {}) if joined_decision is not None else None
        entry_ts = _parse_ts(row.get("entry_ts"))
        exit_ts = _parse_ts(row.get("exit_ts"))
        decision_ts = _parse_ts(decision_ts_text)

        canonical_lifecycle = trade_open_lifecycle or execution_fill_lifecycle
        canonical_source = ""
        if trade_open_lifecycle:
            canonical_source = "trade_journal.trade_open"
        elif execution_fill_lifecycle:
            canonical_source = "execution_log.paper_fill"

        reasons: list[str] = []
        if trade_open_lifecycle and decision_lifecycle and trade_open_lifecycle != decision_lifecycle:
            reasons.append("trade_open_vs_decision_lifecycle")
        if execution_fill_lifecycle and decision_lifecycle and execution_fill_lifecycle != decision_lifecycle:
            reasons.append("execution_fill_vs_decision_lifecycle")
        if trade_open_lifecycle and execution_fill_lifecycle and trade_open_lifecycle != execution_fill_lifecycle:
            reasons.append("trade_open_vs_execution_fill_lifecycle")

        late_decision = decision_ts is not None and exit_ts is not None and decision_ts > exit_ts
        if late_decision:
            reasons.append("late_decision_join")

        if late_decision:
            truth_status = "LATE_DECISION_JOIN"
        elif reasons:
            truth_status = "LIFECYCLE_CONFLICT"
        elif canonical_lifecycle:
            truth_status = "OK"
        else:
            truth_status = "UNKNOWN"

        row.update(
            {
                "trade_open_lifecycle_phase": trade_open_lifecycle,
                "execution_fill_lifecycle_phase": execution_fill_lifecycle,
                "decision_join_lifecycle_phase": decision_lifecycle,
                "decision_join_ts": decision_ts_text,
                "decision_join_ts_delta_from_open_s": _seconds_between(decision_ts, entry_ts),
                "decision_join_ts_delta_from_close_s": _seconds_between(decision_ts, exit_ts),
                "lifecycle_truth_status": truth_status,
                "lifecycle_conflict_flag": bool(reasons),
                "lifecycle_conflict_reason": ";".join(reasons),
                "canonical_entry_lifecycle_phase": canonical_lifecycle,
                "canonical_entry_lifecycle_source": canonical_source,
            }
        )
        row["lineage_enrichment_version"] = "1.2"
        row["executable_pnl"] = row.get("executable_pnl") or None
        row["executable_pnl_status"] = row.get("executable_pnl_status") or "BLOCKED_NO_TRUE_EXECUTABLE_DATA"
        enriched.append(row)

    return enriched, _lifecycle_v1_2_summary(enriched)


CSV_COLUMNS = (
    "canonical_trade_id",
    "run_id",
    "paper_trade_replay_key",
    "condition_id",
    "token_id",
    "market_slug",
    "asset",
    "side",
    "entry_ts",
    "exit_ts",
    "hold_seconds",
    "session_hour_utc",
    "epoch_start_ts",
    "lifecycle_phase",
    "regime",
    "entry_price",
    "exit_price",
    "shares",
    "notional_entry",
    "notional_exit",
    "pnl_usdc",
    "pnl_recomputed",
    "signal_pnl",
    "paper_pnl",
    "executable_pnl",
    "executable_pnl_status",
    "exit_reason",
    "trade_result",
    "outcome_win_loss",
    "tp_hit",
    "sl_hit",
    "expired",
    "model_output_ready",
    "true_probability",
    "fair_value",
    "expected_value",
    "ev_after_spread",
    "ev_quartile",
    "confidence",
    "confidence_quartile",
    "probability_model_reason",
    "distance_from_ptb",
    "entry_price_bucket",
    "hold_time_bucket",
    "quote_age_at_submit_ms",
    "quote_age_at_fill_ms",
    "liquidity_state",
    "spread",
    "mfe_price",
    "mae_price",
    "mfe_usdc",
    "mae_usdc",
    "path_full_coverage",
    "checkpoint_count",
    "fast_close",
    "mos_assumption",
    "mos_source",
    "dust_zone",
    "executable_minimum_met",
    "executable_candidate",
    "decision_joined",
    "execution_joined",
    "path_truth_joined",
    "join_confidence",
    "row_completeness",
    "quarantine_flag",
    "quarantine_reason",
    "source_files",
    "risk_mode_entry",
    "bankroll_mode_entry",
    "bankroll_tier_entry",
    "bankroll_family_entry",
    "risk_profile_entry",
    "micro_survival_active_entry",
    "available_risk_budget_entry",
    "current_exposure_entry",
    "entry_submit_event_type",
    "entry_submit_ts",
    "entry_submit_price",
    "entry_submit_size",
    "entry_quote_age_ms",
    "entry_risk_plan_present",
    "entry_risk_join_confidence",
    "entry_risk_join_source",
    "execution_join_confidence",
    "lineage_enrichment_version",
)


CSV_V1_2_COLUMNS = CSV_COLUMNS + LIFECYCLE_V1_2_FIELDS


def write_csv(rows: list[dict[str, Any]], path: str | Path, *, columns: Iterable[str] = CSV_COLUMNS) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return output


def read_csv_rows(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        if value == float("inf"):
            return "inf"
        return f"{value:.6f}"
    return str(value)


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_none_\n"
    columns = list(rows[0].keys())
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines) + "\n"


def write_summary(result: BuildResult, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = result.summary
    clean_signal_rows = summary["FULL_rows"] + summary["RECONSTRUCTED_rows"]
    path_rows = summary["MFE_available_count"]
    blocker = _biggest_blocker(summary)
    lines = [
        "# Canonical Trade Table V1 Summary",
        "",
        "## Executive Summary",
        "",
        f"- Completed trades: {summary['completed_trade_count']}",
        f"- Clean enough for signal expectancy: {clean_signal_rows}",
        f"- Clean enough for path/MFE/MAE analysis: {path_rows}",
        f"- Executable candidates: {summary['executable_candidate_count']}",
        f"- FULL-only total PnL: {_fmt(summary['FULL_expectancy_total_pnl'])}",
        f"- Biggest remaining data blocker: {blocker}",
        "",
        "## Coverage Metrics",
        "",
        _markdown_table([
            {"metric": key, "value": value}
            for key, value in summary.items()
            if key.endswith("count") or key.endswith("rows") or key in {"completed_trade_count", "total_trade_open_rows", "total_trade_close_rows"}
        ]),
        "## Join Rates",
        "",
        _markdown_table([
            {"join": "decision", "rate": summary["decision_join_rate"]},
            {"join": "execution", "rate": summary["execution_join_rate"]},
            {"join": "path_truth", "rate": summary["path_truth_join_rate"]},
        ]),
        "## Expectancy Metrics",
        "",
        _markdown_table([
            {"metric": "win_rate", "value": summary["win_rate"]},
            {"metric": "profit_factor", "value": summary["profit_factor"]},
            {"metric": "mean_pnl", "value": summary["mean_pnl"]},
            {"metric": "median_pnl", "value": summary["median_pnl"]},
            {"metric": "total_pnl", "value": summary["total_pnl"]},
            {"metric": "FULL_expectancy_win_rate", "value": summary["FULL_expectancy_win_rate"]},
            {"metric": "FULL_expectancy_mean_pnl", "value": summary["FULL_expectancy_mean_pnl"]},
        ]),
        "## Breakdowns",
        "",
    ]
    for name, rows in result.breakdowns.items():
        lines.extend([f"### {name}", "", _markdown_table(rows), ""])
    lines.extend([
        "## Validation Results",
        "",
        "- canonical_trade_id is deterministic and unique per completed `(run_id, paper_trade_replay_key)` row.",
        "- Invalid timestamps, prices, shares, PnL mismatch, and duplicate open/close keys are quarantined.",
        "- `executable_pnl` is intentionally null and blocked for every row.",
        "",
        "## Quarantine Summary",
        "",
        _markdown_table(_build_breakdown(result.rows, "quarantine_reason")[:25]),
        "## Governor Verdict",
        "",
        "Canonical Trade Table V1 is an offline research artifact. It establishes completed-trade N without changing runtime, strategy, risk, execution, replay semantics, live behavior, Telegram, or source JSONL evidence.",
        "",
    ])
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def _metric_table_for_field(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    return _build_breakdown(rows, field)


def _subset(rows: list[dict[str, Any]], **criteria: str) -> list[dict[str, Any]]:
    selected = rows
    for field, expected in criteria.items():
        selected = [row for row in selected if str(row.get(field) or "unknown") == str(expected)]
    return selected


def _top_win_concentration(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pnls = sorted((value for row in rows for value in [_to_float(row.get("pnl_usdc"))] if value is not None), reverse=True)
    total = sum(pnls)
    if total <= 0:
        return {"top1_share": None, "top2_share": None, "top5_share": None, "median_pnl": median(pnls) if pnls else 0.0}
    return {
        "top1_share": pnls[0] / total if len(pnls) >= 1 else None,
        "top2_share": sum(pnls[:2]) / total if len(pnls) >= 2 else None,
        "top5_share": sum(pnls[:5]) / total if len(pnls) >= 5 else None,
        "median_pnl": median(pnls) if pnls else 0.0,
    }


def _risk_split(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(field) or "unknown")].append(row)
    output: list[dict[str, Any]] = []
    for risk_mode, items in sorted(grouped.items()):
        pnls = [value for row in items for value in [_to_float(row.get("pnl_usdc"))] if value is not None]
        wins = sum(1 for row in items if row.get("outcome_win_loss") == "WIN")
        output.append(
            {
                "bucket": risk_mode,
                "n": len(items),
                "win_rate": _rate(wins, len(items)),
                "total_pnl": sum(pnls),
                "mean_pnl": mean(pnls) if pnls else 0.0,
                "median_pnl": median(pnls) if pnls else 0.0,
                "profit_factor": _profit_factor(pnls),
                "fast_close_rate": _rate(sum(1 for row in items if row.get("fast_close") in {True, "True", "true", "1"}), len(items)),
                "TP": sum(1 for row in items if row.get("tp_hit") in {True, "True", "true", "1"}),
                "SL": sum(1 for row in items if row.get("sl_hit") in {True, "True", "true", "1"}),
            }
        )
    return output


def _interaction_table(rows: list[dict[str, Any]], left: str, right: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get(left) or "unknown"), str(row.get(right) or "unknown"))].append(row)
    output: list[dict[str, Any]] = []
    for (left_value, right_value), items in sorted(grouped.items()):
        metrics = _risk_split(items, left)[0]
        output.append(
            {
                "bucket": f"{left_value} | {right_value}",
                "n": metrics["n"],
                "win_rate": metrics["win_rate"],
                "total_pnl": metrics["total_pnl"],
                "mean_pnl": metrics["mean_pnl"],
                "median_pnl": metrics["median_pnl"],
                "profit_factor": metrics["profit_factor"],
                "fast_close_rate": metrics["fast_close_rate"],
                "TP": metrics["TP"],
                "SL": metrics["SL"],
            }
        )
    return output


def _deep_dive(rows: list[dict[str, Any]], risk_mode: str) -> list[tuple[str, list[dict[str, Any]]]]:
    selected = [row for row in rows if row.get("risk_mode_entry") == risk_mode]
    return [
        ("summary", _risk_split(selected, "risk_mode_entry")),
        ("asset split", _metric_table_for_field(selected, "asset")),
        ("side split", _metric_table_for_field(selected, "side")),
        ("regime split", _metric_table_for_field(selected, "regime")),
        ("lifecycle split", _metric_table_for_field(selected, "lifecycle_phase")),
        ("hold-time split", _metric_table_for_field(selected, "hold_time_bucket")),
        ("concentration", [{**_top_win_concentration(selected)}]),
    ]


def write_v1_1_summary(rows: list[dict[str, Any]], coverage: dict[str, Any], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fast_close_rows = [row for row in rows if row.get("hold_time_bucket") == "0-15s"]
    positive_subsets = {
        "ETH + YES": _subset(rows, asset="ETH", side="YES"),
        "FINAL_DERISK + COMPRESSION": _subset(rows, lifecycle_phase="FINAL_DERISK", regime="COMPRESSION"),
        "FINAL_DERISK + TREND_DOWN": _subset(rows, lifecycle_phase="FINAL_DERISK", regime="TREND_DOWN"),
        "FINAL_DERISK overall": _subset(rows, lifecycle_phase="FINAL_DERISK"),
    }
    lines = [
        "# Canonical Trade Table V1.1 Summary",
        "",
        "## Executive Summary",
        "",
        f"- Total rows enriched: {coverage['total_rows']}",
        f"- Rows with risk_mode_entry: {coverage['rows_with_risk_mode_entry']}",
        f"- Rows with entry submit timestamp: {coverage['rows_with_entry_submit_ts']}",
        f"- Enrichment join rate: {_fmt(coverage['enrichment_join_rate'])}",
        f"- Missing risk lineage count: {coverage['missing_risk_lineage_count']}",
        f"- Missing execution lineage count: {coverage['missing_execution_lineage_count']}",
        "",
        "## Enrichment Coverage",
        "",
        _markdown_table([{"metric": key, "value": value} for key, value in coverage.items()]),
        "## Risk Mode Breakdown",
        "",
        _markdown_table(_risk_split(rows, "risk_mode_entry")),
        "## Bankroll Mode Breakdown",
        "",
        _markdown_table(_risk_split(rows, "bankroll_mode_entry")),
        "## Risk x Killer Bucket",
        "",
        "### risk_mode_entry x hold_time_bucket",
        "",
        _markdown_table(_interaction_table(rows, "risk_mode_entry", "hold_time_bucket")),
        "### risk_mode_entry x market_regime",
        "",
        _markdown_table(_interaction_table(rows, "risk_mode_entry", "regime")),
        "### risk_mode_entry x lifecycle_phase_entry",
        "",
        _markdown_table(_interaction_table(rows, "risk_mode_entry", "lifecycle_phase")),
        "### risk_mode_entry x asset",
        "",
        _markdown_table(_interaction_table(rows, "risk_mode_entry", "asset")),
        "### risk_mode_entry x side",
        "",
        _markdown_table(_interaction_table(rows, "risk_mode_entry", "side")),
        "## DEFENSIVE Deep Dive",
        "",
    ]
    for title, table in _deep_dive(rows, "DEFENSIVE"):
        lines.extend([f"### {title}", "", _markdown_table(table), ""])
    lines.extend(["## MICRO_RECOVERY Deep Dive", ""])
    for title, table in _deep_dive(rows, "MICRO_RECOVERY"):
        lines.extend([f"### {title}", "", _markdown_table(table), ""])
    lines.extend(["## Positive Subset Recheck", ""])
    for name, subset_rows in positive_subsets.items():
        lines.extend([f"### {name}", "", _markdown_table(_risk_split(subset_rows, "risk_mode_entry")), ""])
    lines.extend(
        [
            "## Fast Close Killer Analysis",
            "",
            f"- Hold 0-15s rows: {len(fast_close_rows)}",
            f"- Damage contribution: {_fmt(sum(_to_float(row.get('pnl_usdc')) or 0.0 for row in fast_close_rows))}",
            "",
            "### risk mode split",
            "",
            _markdown_table(_risk_split(fast_close_rows, "risk_mode_entry")),
            "### asset split",
            "",
            _markdown_table(_metric_table_for_field(fast_close_rows, "asset")),
            "### side split",
            "",
            _markdown_table(_metric_table_for_field(fast_close_rows, "side")),
            "### regime split",
            "",
            _markdown_table(_metric_table_for_field(fast_close_rows, "regime")),
            "### lifecycle split",
            "",
            _markdown_table(_metric_table_for_field(fast_close_rows, "lifecycle_phase")),
            "## Validation Results",
            "",
            "- V1 completed trade count is preserved.",
            "- Enrichment is additive and offline-only.",
            "- `executable_pnl` remains blocked/null; no executable truth was fabricated.",
            "",
            "## Governor Verdict",
            "",
            "CTT V1.1 adds risk/execution lineage for subset review only. It does not authorize runtime policy, sizing, execution, live trading, or executable PnL claims.",
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def _positive_subset_scan(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = (
        "asset",
        "side",
        "risk_mode_entry",
        "canonical_entry_lifecycle_phase",
        "regime",
        "session_hour_utc",
        "entry_price_bucket",
        "ev_quartile",
        "confidence_quartile",
        "hold_time_bucket",
        "exit_reason",
    )
    candidates: list[dict[str, Any]] = []
    for field in fields:
        for item in _risk_split(rows, field):
            if item["n"] >= 20 and item["total_pnl"] > 0 and item["mean_pnl"] > 0:
                profit_factor = item.get("profit_factor")
                if profit_factor is not None and profit_factor > 1.05:
                    candidates.append({"field": field, **item})
    return sorted(
        candidates,
        key=lambda item: (
            item["profit_factor"] if item["profit_factor"] != float("inf") else 999999.0,
            item["mean_pnl"],
            item["n"],
        ),
        reverse=True,
    )[:25]


def _lifecycle_artifact_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("lifecycle_conflict_flag") not in {True, "True", "true", "1"}:
            continue
        grouped[
            (
                str(row.get("lifecycle_phase") or "unknown"),
                str(row.get("canonical_entry_lifecycle_phase") or "unknown"),
                str(row.get("lifecycle_truth_status") or "unknown"),
            )
        ].append(row)
    output: list[dict[str, Any]] = []
    for (old_phase, canonical_phase, status), items in sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True):
        pnls = [value for row in items for value in [_to_float(row.get("pnl_usdc"))] if value is not None]
        output.append(
            {
                "old_lifecycle_phase": old_phase,
                "canonical_entry_lifecycle_phase": canonical_phase,
                "truth_status": status,
                "n": len(items),
                "total_pnl_distorted": sum(pnls),
                "mean_pnl": mean(pnls) if pnls else 0.0,
            }
        )
    return output[:25]


def write_v1_2_summary(rows: list[dict[str, Any]], coverage: dict[str, Any], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    false_pocket_old = [
        row
        for row in rows
        if row.get("risk_mode_entry") == "DEFENSIVE" and row.get("lifecycle_phase") == "FINAL_DERISK"
    ]
    false_pocket_recheck = [
        row
        for row in rows
        if row.get("risk_mode_entry") == "DEFENSIVE"
        and row.get("canonical_entry_lifecycle_phase") in {"FINAL_DERISK", "OPENING_SCAN", "ACTIVE_INVENTORY_TRADING"}
    ]
    fast_close_rows = [row for row in rows if row.get("hold_time_bucket") == "0-15s"]
    lines = [
        "# Canonical Trade Table V1.2 Lifecycle Truth Summary",
        "",
        "## Executive Summary",
        "",
        f"- Total rows built: {coverage['total_rows']}",
        f"- Rows with trade_open lifecycle: {coverage['rows_with_trade_open_lifecycle_phase']}",
        f"- Rows with execution fill lifecycle: {coverage['rows_with_execution_fill_lifecycle_phase']}",
        f"- Rows with decision join lifecycle: {coverage['rows_with_decision_join_lifecycle_phase']}",
        f"- Lifecycle conflicts: {coverage['lifecycle_conflict_count']}",
        f"- Late decision joins: {coverage['late_decision_join_count']}",
        "- Canonical entry lifecycle now comes from trade_open first, execution fill second, never a late decision row.",
        "- `executable_pnl` remains null/BLOCKED for every row.",
        "",
        "## Lifecycle Coverage",
        "",
        _markdown_table([{"metric": key, "value": value} for key, value in coverage.items()]),
        "## Lifecycle Conflict Summary",
        "",
        _markdown_table(_risk_split(rows, "lifecycle_truth_status")),
        "## Corrected Lifecycle Expectancy",
        "",
        _markdown_table(_risk_split(rows, "canonical_entry_lifecycle_phase")),
        "## False Pocket Recheck",
        "",
        "### Previous DEFENSIVE + joined decision FINAL_DERISK",
        "",
        _markdown_table(_risk_split(false_pocket_old, "lifecycle_phase")),
        "### DEFENSIVE by corrected canonical entry lifecycle",
        "",
        _markdown_table(_risk_split(false_pocket_recheck, "canonical_entry_lifecycle_phase")),
        "## Positive Subset Recheck",
        "",
        _markdown_table(_positive_subset_scan(rows)),
        "## Fast Close Recheck",
        "",
        "### 0-15s by corrected lifecycle",
        "",
        _markdown_table(_risk_split(fast_close_rows, "canonical_entry_lifecycle_phase")),
        "### 0-15s by risk mode",
        "",
        _markdown_table(_risk_split(fast_close_rows, "risk_mode_entry")),
        "### 0-15s by risk mode x corrected lifecycle",
        "",
        _markdown_table(_interaction_table(fast_close_rows, "risk_mode_entry", "canonical_entry_lifecycle_phase")),
        "## Artifact Report",
        "",
        _markdown_table(_lifecycle_artifact_table(rows)),
        "## Validation Results",
        "",
        "- Completed trade count is preserved from V1.1.",
        "- Late decision joins are additive metadata only.",
        "- Joined decision lifecycle is retained for audit but cannot override entry lifecycle.",
        "- Runtime JSONL evidence was not modified.",
        "- `executable_pnl` remains blocked/null; no executable truth was fabricated.",
        "",
        "## Governor Verdict",
        "",
        "CTT V1.2 corrects lifecycle attribution for offline research. It does not authorize runtime policy, sizing, execution, live trading, replay semantic changes, or executable PnL claims.",
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def _biggest_blocker(summary: dict[str, Any]) -> str:
    if summary["path_truth_join_rate"] < 0.95:
        return "missing_path_truth_join"
    if summary["decision_join_rate"] < 0.95:
        return "missing_decision_join"
    if summary["execution_join_rate"] < 0.95:
        return "missing_execution_join"
    if summary["executable_pnl_approved_count"] == 0:
        return "executable_truth_blocked"
    return "none_detected"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Canonical Trade Table V1 from offline JSONL evidence.")
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)

    result = build_from_files(args.base_dir)
    output_dir = Path(args.output_dir)
    csv_path = write_csv(result.rows, output_dir / CSV_NAME)
    summary_path = write_summary(result, output_dir / SUMMARY_NAME)
    v1_rows = read_csv_rows(csv_path)
    target_keys = {
        (str(row.get("run_id") or ""), str(row.get("paper_trade_replay_key") or ""))
        for row in v1_rows
        if row.get("run_id") and row.get("paper_trade_replay_key")
    }
    quant_root = Path(args.base_dir)
    trade_events = list(_iter_jsonl(_paths(quant_root, "trade_journal"), key_filter=target_keys))
    decision_events = list(_iter_jsonl(_paths(quant_root, "decision_log"), key_filter=target_keys))
    execution_events = list(_iter_jsonl(_paths(quant_root, "execution_log"), key_filter=target_keys))
    risk_events = list(_iter_jsonl(_paths(quant_root, "risk_log"), key_filter=target_keys))
    enriched_rows, enrichment_summary = enrich_canonical_rows_v1_1(
        v1_rows,
        execution_events=execution_events,
        risk_events=risk_events,
        trade_events=trade_events,
    )
    v1_1_csv_path = write_csv(enriched_rows, output_dir / CSV_V1_1_NAME)
    v1_1_summary_path = write_v1_1_summary(enriched_rows, enrichment_summary, output_dir / SUMMARY_V1_1_NAME)
    v1_2_rows, lifecycle_summary = enrich_canonical_rows_v1_2(
        enriched_rows,
        trade_events=trade_events,
        execution_events=execution_events,
        decision_events=decision_events,
    )
    v1_2_csv_path = write_csv(v1_2_rows, output_dir / CSV_V1_2_NAME, columns=CSV_V1_2_COLUMNS)
    v1_2_summary_path = write_v1_2_summary(v1_2_rows, lifecycle_summary, output_dir / SUMMARY_V1_2_NAME)
    print(f"wrote {csv_path}")
    print(f"wrote {summary_path}")
    print(f"wrote {v1_1_csv_path}")
    print(f"wrote {v1_1_summary_path}")
    print(f"wrote {v1_2_csv_path}")
    print(f"wrote {v1_2_summary_path}")
    print(f"completed_trade_count={result.summary['completed_trade_count']}")
    print(f"v1_1_enriched_rows={enrichment_summary['total_rows']}")
    print(f"v1_2_lifecycle_rows={lifecycle_summary['total_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
