from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_OUTPUT_FIELDS = (
    "timestamp_utc",
    "run_id",
    "source_file",
    "source_line",
    "asset",
    "market_slug",
    "side",
    "outcome",
    "edge",
    "ev",
    "ev_after_spread",
    "true_probability",
    "volatility_regime",
    "trend_regime",
    "execution_pnl_5_share_model",
    "execution_entry_price",
    "execution_exit_price",
    "execution_shares",
    "historical_position_uid",
    "execution_position_id",
    "signal_id",
    "join_status",
    "join_offset_seconds",
)


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def is_safe_scratch_path(path: str | Path) -> bool:
    resolved = Path(path).resolve()
    workspace = _workspace_root()
    runtime_root = (workspace / "runtime").resolve()
    if resolved == runtime_root or runtime_root in resolved.parents:
        return False
    return any(part.lower() == "scratch" for part in resolved.parts)


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _line_hash(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def _read_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            yield line_no, _line_hash(line), json.loads(line)


def _payload(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {}
    payload = row.get("payload")
    return payload if isinstance(payload, dict) else {}


def _get(row: dict[str, Any] | None, key: str) -> Any:
    if not row:
        return None
    payload = _payload(row)
    if key in payload:
        return payload.get(key)
    return row.get(key)


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _seconds_between(left: Any, right: Any) -> float | None:
    left_ts = _parse_ts(left)
    right_ts = _parse_ts(right)
    if left_ts is None or right_ts is None:
        return None
    return (left_ts - right_ts).total_seconds()


def _norm_path(path: str | Path) -> str:
    return Path(path).as_posix().replace("\\", "/")


def _source_ref_keys(source_file: str | Path, source_line: int) -> list[tuple[str, int]]:
    raw = str(source_file)
    path = Path(raw)
    keys = [
        (_norm_path(raw), source_line),
        (_norm_path(path.resolve()) if path.exists() else _norm_path(raw), source_line),
        (path.name, source_line),
    ]
    seen: set[tuple[str, int]] = set()
    deduped: list[tuple[str, int]] = []
    for key in keys:
        if key not in seen:
            deduped.append(key)
            seen.add(key)
    return deduped


def _identity_values(row: dict[str, Any] | None) -> set[str]:
    payload = _payload(row)
    values: set[str] = set()
    for key in ("historical_position_uid", "execution_position_id", "position_id", "order_id"):
        value = payload.get(key) if key in payload else (row or {}).get(key)
        if value:
            values.add(str(value))
    receipt = payload.get("receipt")
    if isinstance(receipt, dict) and receipt.get("order_id"):
        values.add(str(receipt["order_id"]))
    expanded = set(values)
    for value in values:
        if value.startswith("ep_"):
            expanded.add(value[3:])
        else:
            expanded.add(f"ep_{value}")
    return expanded


def _identity_key(row: dict[str, Any] | None, key: str) -> str | None:
    value = _get(row, key)
    if value is None or value == "":
        return None
    return str(value)


def _append_index(index: dict[Any, list[dict[str, Any]]], key: Any, row: dict[str, Any]) -> None:
    if key is not None:
        index[key].append(row)


def _stringify_required(values: set[str] | set[tuple[str, str]]) -> set[str]:
    result: set[str] = set()
    for value in values:
        if isinstance(value, tuple):
            result.add(str(value[1]))
        else:
            result.add(str(value))
    return {value for value in result if value}


def _load_execution_closes(execution_root: Path, max_records: int) -> list[dict[str, Any]]:
    closes: list[dict[str, Any]] = []
    for path in sorted((execution_root / "journals" / "trade").glob("*.jsonl")):
        for _, _, row in _read_jsonl(path):
            if row.get("event_type") == "execution_paper_close":
                closes.append(row)
                if max_records and len(closes) >= max_records:
                    return closes
    return closes


def _load_trade_indexes(trade_root: Path) -> dict[str, Any]:
    source_ref: dict[tuple[str, int], dict[str, Any]] = {}
    open_by_identity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    open_by_signal: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    open_by_candidate: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    open_by_condition_epoch: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)

    for path in sorted(trade_root.glob("*.jsonl")):
        for line_no, line_sha, row in _read_jsonl(path):
            row["_source_file_actual"] = str(path)
            row["_source_line"] = line_no
            row["_source_event_sha256"] = line_sha
            for key in _source_ref_keys(path, line_no):
                source_ref[key] = row
            event_type = row.get("event_type")
            if event_type != "trade_open":
                continue
            for value in _identity_values(row):
                open_by_identity[value].append(row)
            run_id = str(row.get("run_id") or "")
            signal_id = _identity_key(row, "signal_id")
            candidate_id = _identity_key(row, "candidate_id")
            if run_id and signal_id:
                open_by_signal[(run_id, signal_id)].append(row)
            if run_id and candidate_id:
                open_by_candidate[(run_id, candidate_id)].append(row)
            condition_key = (
                run_id,
                _identity_key(row, "condition_id"),
                _get(row, "epoch_start_ts"),
                _get(row, "asset") or _get(row, "ticker"),
                _get(row, "outcome") or _get(row, "side"),
            )
            open_by_condition_epoch[condition_key].append(row)

    return {
        "source_ref": source_ref,
        "open_by_identity": open_by_identity,
        "open_by_signal": open_by_signal,
        "open_by_candidate": open_by_candidate,
        "open_by_condition_epoch": open_by_condition_epoch,
    }


def _project_decision_row(row: dict[str, Any], path: Path, line_no: int) -> dict[str, Any]:
    payload = _payload(row)
    return {
        "timestamp_utc": row.get("timestamp_utc") or payload.get("timestamp_utc"),
        "run_id": str(row.get("run_id") or ""),
        "signal_id": payload.get("signal_id") or row.get("signal_id"),
        "candidate_id": payload.get("candidate_id") or row.get("candidate_id"),
        "condition_id": payload.get("condition_id") or row.get("condition_id"),
        "edge": payload.get("edge") if "edge" in payload else row.get("edge"),
        "ev": payload.get("ev") if "ev" in payload else row.get("ev"),
        "ev_after_spread": payload.get("ev_after_spread") if "ev_after_spread" in payload else row.get("ev_after_spread"),
        "true_probability": payload.get("true_probability") if "true_probability" in payload else row.get("true_probability"),
        "volatility_regime": payload.get("volatility_regime") if "volatility_regime" in payload else row.get("volatility_regime"),
        "trend_regime": payload.get("trend_regime") if "trend_regime" in payload else row.get("trend_regime"),
        "source_file": str(path),
        "source_line": line_no,
    }


def _load_decision_indexes(
    decision_root: Path,
    required_run_ids: set[str],
    required_signal_ids: set[tuple[str, str]],
    required_candidate_ids: set[tuple[str, str]],
    required_condition_ids: set[tuple[str, str]],
    max_decision_rows_loaded: int,
    progress_every_files: int,
) -> dict[str, Any]:
    by_signal: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_candidate: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_condition: dict[tuple[str, str], list[tuple[datetime, dict[str, Any]]]] = defaultdict(list)
    stats = {
        "decision_rows_seen": 0,
        "decision_rows_parsed": 0,
        "decision_rows_retained": 0,
        "decision_rows_skipped_run_id": 0,
        "decision_rows_skipped_key": 0,
        "required_run_id_count": len(required_run_ids),
        "required_condition_id_count": len(_stringify_required(required_condition_ids)),
        "required_signal_id_count": len(_stringify_required(required_signal_ids)),
        "required_candidate_id_count": len(_stringify_required(required_candidate_ids)),
        "memory_guard_status": "OK",
    }

    run_id_tokens = tuple(json.dumps(run_id, separators=(",", ":")) for run_id in sorted(required_run_ids) if run_id)
    signal_tokens = tuple(json.dumps(value, separators=(",", ":")) for value in sorted(_stringify_required(required_signal_ids)) if value)
    candidate_tokens = tuple(json.dumps(value, separators=(",", ":")) for value in sorted(_stringify_required(required_candidate_ids)) if value)
    condition_tokens = tuple(json.dumps(value, separators=(",", ":")) for value in sorted(_stringify_required(required_condition_ids)) if value)

    for file_index, path in enumerate(sorted(decision_root.glob("*.jsonl")), start=1):
        if progress_every_files and file_index % progress_every_files == 0:
            print(
                _json_dumps(
                    {
                        "event": "joined_records_builder_decision_scan_progress",
                        "files_scanned": file_index,
                        "decision_rows_seen": stats["decision_rows_seen"],
                        "decision_rows_retained": stats["decision_rows_retained"],
                    }
                )
            )
        with path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                stats["decision_rows_seen"] += 1
                if not required_run_ids or not (required_signal_ids or required_candidate_ids or required_condition_ids):
                    stats["decision_rows_skipped_key"] += 1
                    continue
                if run_id_tokens and not any(token in line for token in run_id_tokens):
                    stats["decision_rows_skipped_run_id"] += 1
                    continue
                if (
                    signal_tokens
                    or candidate_tokens
                    or condition_tokens
                ) and not (
                    any(token in line for token in signal_tokens)
                    or any(token in line for token in candidate_tokens)
                    or any(token in line for token in condition_tokens)
                ):
                    stats["decision_rows_skipped_key"] += 1
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                stats["decision_rows_parsed"] += 1
                payload = _payload(row)
                if not payload:
                    continue
                run_id = str(row.get("run_id") or "")
                if run_id not in required_run_ids:
                    stats["decision_rows_skipped_run_id"] += 1
                    continue
                signal_id = payload.get("signal_id")
                candidate_id = payload.get("candidate_id")
                condition_id = payload.get("condition_id")
                signal_key = (run_id, str(signal_id)) if signal_id else None
                candidate_key = (run_id, str(candidate_id)) if candidate_id else None
                condition_key = (run_id, str(condition_id)) if condition_id else None
                matches_signal = bool(signal_key and signal_key in required_signal_ids)
                matches_candidate = bool(candidate_key and candidate_key in required_candidate_ids)
                matches_condition = bool(condition_key and condition_key in required_condition_ids)
                if not (matches_signal or matches_candidate or matches_condition):
                    stats["decision_rows_skipped_key"] += 1
                    continue

                projected = _project_decision_row(row, path, line_no)
                stats["decision_rows_retained"] += 1
                if stats["decision_rows_retained"] > max_decision_rows_loaded:
                    stats["memory_guard_status"] = "FAILED_MAX_DECISION_ROWS_LOADED"
                    raise ValueError(
                        f"max_decision_rows_loaded exceeded: {stats['decision_rows_retained']} > {max_decision_rows_loaded}"
                    )

                if matches_signal and signal_key:
                    by_signal[signal_key].append(projected)
                if matches_candidate and candidate_key:
                    by_candidate[candidate_key].append(projected)
                if matches_condition and condition_key:
                    timestamp = _parse_ts(projected.get("timestamp_utc"))
                    if timestamp:
                        by_condition[condition_key].append((timestamp, projected))

    for values in by_condition.values():
        values.sort(key=lambda item: item[0])
    parsed = stats["decision_rows_parsed"]
    stats["decision_retention_rate"] = stats["decision_rows_retained"] / parsed if parsed else 0.0
    return {"by_signal": by_signal, "by_candidate": by_candidate, "by_condition": by_condition, "stats": stats}


def _choose_first(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return rows[0]


def _find_source_close(indexes: dict[str, Any], close: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    source_file = close.get("source_file")
    source_line = int(close.get("source_line") or 0)
    for key in _source_ref_keys(str(source_file or ""), source_line):
        row = indexes["source_ref"].get(key)
        if row is not None:
            expected = close.get("source_event_sha256")
            mismatch = bool(expected and row.get("_source_event_sha256") and expected != row.get("_source_event_sha256"))
            return row, mismatch
    return None, False


def _find_source_open(indexes: dict[str, Any], close: dict[str, Any], source_close: dict[str, Any]) -> dict[str, Any] | None:
    for value in _identity_values(close) | _identity_values(source_close):
        match = _choose_first(indexes["open_by_identity"].get(value, []))
        if match:
            return match

    run_id = str(source_close.get("run_id") or close.get("source_run_id") or "")
    signal_id = _identity_key(source_close, "signal_id")
    candidate_id = _identity_key(source_close, "candidate_id")
    if run_id and signal_id:
        match = _choose_first(indexes["open_by_signal"].get((run_id, signal_id), []))
        if match:
            return match
    if run_id and candidate_id:
        match = _choose_first(indexes["open_by_candidate"].get((run_id, candidate_id), []))
        if match:
            return match

    condition_key = (
        run_id,
        _identity_key(source_close, "condition_id"),
        _get(source_close, "epoch_start_ts"),
        _get(source_close, "asset") or _get(source_close, "ticker"),
        _get(source_close, "outcome") or _get(source_close, "side"),
    )
    return _choose_first(indexes["open_by_condition_epoch"].get(condition_key, []))


def _nearest_decision(
    decisions: list[tuple[datetime, dict[str, Any]]],
    target: datetime,
    max_seconds: float,
) -> tuple[dict[str, Any] | None, float | None, bool]:
    timestamps = [item[0] for item in decisions]
    pos = bisect.bisect_left(timestamps, target)
    candidates: list[tuple[float, datetime, dict[str, Any]]] = []
    for idx in (pos - 1, pos):
        if 0 <= idx < len(decisions):
            ts, row = decisions[idx]
            offset = (ts - target).total_seconds()
            if abs(offset) <= max_seconds:
                candidates.append((abs(offset), ts, row))
    if not candidates:
        return None, None, False
    candidates.sort(key=lambda item: (item[0], item[1]))
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        return None, candidates[0][0], True
    chosen = candidates[0]
    return chosen[2], (chosen[1] - target).total_seconds(), False


def _find_decision(
    decision_indexes: dict[str, Any],
    source_open: dict[str, Any],
    max_join_seconds: float,
) -> tuple[dict[str, Any] | None, str, float | None]:
    run_id = str(source_open.get("run_id") or "")
    signal_id = _identity_key(source_open, "signal_id")
    candidate_id = _identity_key(source_open, "candidate_id")
    if run_id and signal_id:
        match = _choose_first(decision_indexes["by_signal"].get((run_id, signal_id), []))
        if match:
            return match, "JOINED_SIGNAL_ID", _seconds_between(match.get("timestamp_utc"), source_open.get("timestamp_utc"))
    if run_id and candidate_id:
        match = _choose_first(decision_indexes["by_candidate"].get((run_id, candidate_id), []))
        if match:
            return match, "JOINED_CANDIDATE_ID", _seconds_between(match.get("timestamp_utc"), source_open.get("timestamp_utc"))
    condition_id = _identity_key(source_open, "condition_id")
    target = _parse_ts(source_open.get("timestamp_utc"))
    if run_id and condition_id and target:
        match, offset, ambiguous = _nearest_decision(
            decision_indexes["by_condition"].get((run_id, condition_id), []),
            target,
            max_join_seconds,
        )
        if ambiguous:
            return None, "AMBIGUOUS_DECISION_JOIN", offset
        if match:
            return match, "JOINED_NEAREST_CONDITION", offset
    return None, "JOINED_TRADE_OPEN_ONLY", None


def _collect_decision_requirements(
    closes: list[dict[str, Any]],
    trade_indexes: dict[str, Any],
) -> dict[str, set[Any]]:
    run_ids: set[str] = set()
    signal_ids: set[tuple[str, str]] = set()
    candidate_ids: set[tuple[str, str]] = set()
    condition_ids: set[tuple[str, str]] = set()

    for close in closes:
        source_close, _ = _find_source_close(trade_indexes, close)
        if source_close is None:
            continue
        source_open = _find_source_open(trade_indexes, close, source_close)
        if source_open is None:
            continue
        run_id = str(source_open.get("run_id") or "")
        if not run_id:
            continue
        run_ids.add(run_id)
        signal_id = _identity_key(source_open, "signal_id")
        candidate_id = _identity_key(source_open, "candidate_id")
        condition_id = _identity_key(source_open, "condition_id")
        if signal_id:
            signal_ids.add((run_id, signal_id))
        if candidate_id:
            candidate_ids.add((run_id, candidate_id))
        if condition_id:
            condition_ids.add((run_id, condition_id))

    return {
        "run_ids": run_ids,
        "signal_ids": signal_ids,
        "candidate_ids": candidate_ids,
        "condition_ids": condition_ids,
    }


def _first_non_null(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _field(name: str, source_open: dict[str, Any] | None, source_close: dict[str, Any] | None, decision: dict[str, Any] | None, close: dict[str, Any]) -> Any:
    return _first_non_null(_get(source_open, name), _get(source_close, name), _get(decision, name), close.get(name))


def _base_record(close: dict[str, Any], join_status: str) -> dict[str, Any]:
    return {field: None for field in REQUIRED_OUTPUT_FIELDS} | {
        "timestamp_utc": close.get("timestamp_utc"),
        "run_id": close.get("source_run_id"),
        "source_file": close.get("source_file"),
        "source_line": close.get("source_line"),
        "asset": close.get("asset"),
        "side": close.get("side"),
        "outcome": close.get("side"),
        "execution_pnl_5_share_model": close.get("execution_pnl"),
        "execution_entry_price": close.get("execution_entry_price"),
        "execution_exit_price": close.get("execution_exit_price"),
        "execution_shares": close.get("execution_shares"),
        "historical_position_uid": close.get("historical_position_uid"),
        "execution_position_id": close.get("execution_position_id"),
        "join_status": join_status,
        "join_offset_seconds": None,
        "execution_run_id": close.get("execution_run_id"),
        "execution_source_event_sha256": close.get("source_event_sha256"),
    }


def _build_record(
    close: dict[str, Any],
    source_close: dict[str, Any] | None,
    source_open: dict[str, Any] | None,
    decision: dict[str, Any] | None,
    join_status: str,
    join_offset: float | None,
) -> dict[str, Any]:
    record = _base_record(close, join_status)
    record.update(
        {
            "timestamp_utc": _first_non_null(close.get("timestamp_utc"), _get(source_close, "timestamp_utc")),
            "run_id": _first_non_null(_get(source_open, "run_id"), _get(source_close, "run_id"), close.get("source_run_id")),
            "asset": _field("asset", source_open, source_close, decision, close) or _field("ticker", source_open, source_close, decision, close),
            "market_slug": _field("market_slug", source_open, source_close, decision, close),
            "side": _field("side", source_open, source_close, decision, close),
            "outcome": _field("outcome", source_open, source_close, decision, close) or _field("side", source_open, source_close, decision, close),
            "edge": _field("edge", source_open, source_close, decision, close),
            "ev": _field("ev", source_open, source_close, decision, close),
            "ev_after_spread": _field("ev_after_spread", source_open, source_close, decision, close),
            "true_probability": _field("true_probability", source_open, source_close, decision, close),
            "volatility_regime": _field("volatility_regime", source_open, source_close, decision, close),
            "trend_regime": _field("trend_regime", source_open, source_close, decision, close),
            "signal_id": _field("signal_id", source_open, source_close, decision, close),
            "candidate_id": _field("candidate_id", source_open, source_close, decision, close),
            "condition_id": _field("condition_id", source_open, source_close, decision, close),
            "epoch_start_ts": _field("epoch_start_ts", source_open, source_close, decision, close),
            "join_offset_seconds": join_offset,
            "trade_open_source_file": source_open.get("_source_file_actual") if source_open else None,
            "trade_open_source_line": source_open.get("_source_line") if source_open else None,
            "trade_close_source_file": source_close.get("_source_file_actual") if source_close else None,
            "trade_close_source_line": source_close.get("_source_line") if source_close else None,
            "decision_source_file": decision.get("source_file") if decision else None,
            "decision_source_line": decision.get("source_line") if decision else None,
        }
    )
    if record["side"] == "BUY" and record["outcome"] in ("YES", "NO"):
        record["side"] = record["outcome"]
    return record


def _write_outputs(output_dir: Path, records: list[dict[str, Any]], report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "joined_records.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(_json_dumps(record) + "\n")
    with (output_dir / "joined_records_report.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")


def _report(
    records: list[dict[str, Any]],
    total_closes: int,
    source_hash_mismatch_count: int,
    decision_stats: dict[str, Any],
) -> dict[str, Any]:
    status_counts = Counter(record["join_status"] for record in records)
    joined = sum(count for status, count in status_counts.items() if status.startswith("JOINED_"))
    unjoined = total_closes - joined
    offsets = [float(record["join_offset_seconds"]) for record in records if record.get("join_offset_seconds") is not None]
    return {
        "total_closes": total_closes,
        "joined_closes": joined,
        "unjoined_closes": unjoined,
        "join_rate": joined / total_closes if total_closes else 0.0,
        "avg_join_offset_seconds": sum(offsets) / len(offsets) if offsets else None,
        "max_join_offset_seconds": max(abs(value) for value in offsets) if offsets else None,
        "missing_edge_count": sum(1 for record in records if record.get("edge") is None),
        "missing_ev_count": sum(1 for record in records if record.get("ev") is None),
        "missing_volatility_count": sum(1 for record in records if record.get("volatility_regime") is None),
        "missing_trend_count": sum(1 for record in records if record.get("trend_regime") is None),
        "missing_true_probability_count": sum(1 for record in records if record.get("true_probability") is None),
        "join_status_counts": dict(sorted(status_counts.items())),
        "source_hash_mismatch_count": source_hash_mismatch_count,
        "ambiguous_join_count": status_counts.get("AMBIGUOUS_DECISION_JOIN", 0),
        "output_record_count": len(records),
    } | decision_stats


def build_joined_records(
    execution_journal_root: str | Path,
    trade_journal_root: str | Path,
    decision_log_root: str | Path,
    output_dir: str | Path,
    *,
    max_join_seconds: float = 120,
    fail_on_source_hash_mismatch: bool = False,
    max_records: int = 0,
    max_decision_rows_loaded: int = 250000,
    progress_every_files: int = 5,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    if not is_safe_scratch_path(output_path):
        raise ValueError(f"output directory outside scratch: {output_dir}")

    closes = _load_execution_closes(Path(execution_journal_root), max_records)
    trade_indexes = _load_trade_indexes(Path(trade_journal_root))
    requirements = _collect_decision_requirements(closes, trade_indexes)
    decision_indexes = _load_decision_indexes(
        Path(decision_log_root),
        requirements["run_ids"],
        requirements["signal_ids"],
        requirements["candidate_ids"],
        requirements["condition_ids"],
        max_decision_rows_loaded,
        progress_every_files,
    )

    records: list[dict[str, Any]] = []
    source_hash_mismatch_count = 0
    for close in closes:
        source_close, hash_mismatch = _find_source_close(trade_indexes, close)
        if source_close is None:
            records.append(_base_record(close, "UNJOINED_SOURCE_CLOSE_MISSING"))
            continue
        if hash_mismatch:
            source_hash_mismatch_count += 1
            if fail_on_source_hash_mismatch:
                raise ValueError("source hash mismatch")
            records.append(_base_record(close, "SOURCE_HASH_MISMATCH"))
            continue

        source_open = _find_source_open(trade_indexes, close, source_close)
        if source_open is None:
            records.append(_build_record(close, source_close, None, None, "UNJOINED_SOURCE_OPEN_MISSING", None))
            continue

        decision, join_status, join_offset = _find_decision(decision_indexes, source_open, max_join_seconds)
        records.append(_build_record(close, source_close, source_open, decision, join_status, join_offset))

    report = _report(records, len(closes), source_hash_mismatch_count, decision_indexes.get("stats", {}))
    _write_outputs(output_path, records, report)
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build evaluator-compatible joined execution records.")
    parser.add_argument("--execution-journal-root", required=True, type=Path)
    parser.add_argument("--trade-journal-root", required=True, type=Path)
    parser.add_argument("--decision-log-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-join-seconds", type=float, default=120)
    parser.add_argument("--fail-on-source-hash-mismatch", action="store_true")
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument("--max-decision-rows-loaded", type=int, default=250000)
    parser.add_argument("--progress-every-files", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = build_joined_records(
        args.execution_journal_root,
        args.trade_journal_root,
        args.decision_log_root,
        args.output_dir,
        max_join_seconds=args.max_join_seconds,
        fail_on_source_hash_mismatch=args.fail_on_source_hash_mismatch,
        max_records=args.max_records,
        max_decision_rows_loaded=args.max_decision_rows_loaded,
        progress_every_files=args.progress_every_files,
    )
    print(_json_dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
