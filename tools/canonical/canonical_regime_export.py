from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "canonical_regime_enriched_v1"
DEFAULT_TRADE_JOURNAL_DIR = Path("runtime/quant_data/trade_journal")
DEFAULT_DECISION_LOG_DIR = Path("runtime/quant_data/decision_log")
DEFAULT_OUTPUT_PATH = Path("runtime/research_exports/canonical_regime_enriched_trades_v1.csv")
DEFAULT_META_PATH = Path("runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json")
DEFAULT_SUMMARY_PATH = Path("runtime/research_exports/canonical_regime_enriched_trades_v1_summary.md")
_CANDIDATE_RE = re.compile(r'"candidate_id"\s*:\s*"([^"]+)"')
_REPLAY_KEY_RE = re.compile(r'"paper_trade_replay_key"\s*:\s*"([^"]+)"')

CSV_COLUMNS = [
    "export_schema_version",
    "export_generated_at_utc",
    "row_id",
    "canonical_opportunity_key",
    "run_id",
    "paper_trade_replay_key",
    "condition_id",
    "epoch_start_ts",
    "asset",
    "side",
    "candidate_id",
    "token_id",
    "entry_ts",
    "exit_ts",
    "hold_seconds",
    "entry_price",
    "exit_price",
    "size",
    "trade_result",
    "outcome_win_loss",
    "pnl_usdc",
    "exit_reason",
    "trade_open_lifecycle_phase",
    "trade_close_lifecycle_phase",
    "canonical_entry_lifecycle_phase",
    "canonical_entry_lifecycle_source",
    "market_regime",
    "trend_regime",
    "volatility_regime",
    "regime_reason",
    "regime_source",
    "regime_join_key",
    "regime_join_confidence",
    "regime_decision_ts",
    "regime_decision_delta_from_entry_s",
    "duplicate_opportunity_flag",
    "duplicate_opportunity_count",
    "canonical_retained_flag",
    "row_quality",
    "validation_notes",
]


@dataclass
class ExportResult:
    rows: list[dict[str, Any]]
    metadata: dict[str, Any]


@dataclass
class DecisionCandidate:
    event: dict[str, Any]
    payload: dict[str, Any]
    timestamp: datetime | None
    condition_id: str
    epoch_start_ts: str
    asset: str
    side: str
    candidate_id: str
    paper_trade_replay_key: str
    run_id: str


def parse_utc(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def classify_source_lag(seconds: float | int | None) -> str:
    if seconds is None:
        return "UNKNOWN"
    if seconds <= 2 * 60 * 60:
        return "FRESH"
    if seconds <= 24 * 60 * 60:
        return "STALE"
    return "EXPIRED"


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


def _event_type(event: dict[str, Any]) -> str:
    return str(event.get("event_type") or _payload(event).get("event_type") or "").strip()


def _run_id(event: dict[str, Any]) -> str:
    return str(event.get("run_id") or _payload(event).get("run_id") or "").strip()


def _text(event: dict[str, Any], *names: str) -> str:
    payload = _payload(event)
    for name in names:
        value = payload.get(name)
        if value not in (None, ""):
            return str(value).strip()
        value = event.get(name)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _float(event: dict[str, Any], *names: str) -> float | None:
    for name in names:
        for source in (_payload(event), event):
            value = source.get(name)
            if value in (None, "") or isinstance(value, bool):
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return None


def _parse_ts_from_event(event: dict[str, Any], *names: str) -> datetime | None:
    for name in names:
        text = _text(event, name)
        if text:
            try:
                return parse_utc(text)
            except ValueError:
                pass
    text = str(event.get("timestamp_utc") or "").strip()
    if text:
        try:
            return parse_utc(text)
        except ValueError:
            return None
    return None


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _key_part(paper_key: str, index: int) -> str:
    parts = paper_key.split("|")
    return parts[index].strip() if len(parts) > index else ""


def _side_from_event(event: dict[str, Any], paper_key: str = "") -> str:
    outcome = _text(event, "outcome")
    side = _text(event, "side")
    for value in (outcome, side, _key_part(paper_key, 3)):
        text = value.upper()
        if text in {"YES", "NO"}:
            return text
    return side.upper()


def _normalize_epoch(value: str) -> str:
    return value[:-2] if value.endswith(".0") else value


def _row_id(run_id: str, paper_key: str) -> str:
    digest = hashlib.sha1(f"{run_id}|{paper_key}".encode("utf-8")).hexdigest()
    return f"cre_{digest[:20]}"


def _canonical_key(condition_id: str, epoch_start_ts: str, asset: str, side: str, candidate_id: str) -> str:
    return "|".join([condition_id, epoch_start_ts, asset, side, candidate_id])


def _join_key(event: dict[str, Any]) -> tuple[str, str] | None:
    run_id = _run_id(event)
    paper_key = _text(event, "paper_trade_replay_key")
    if not run_id or not paper_key:
        return None
    return (run_id, paper_key)


def _trade_rows(trade_journal_dir: Path, generated_at: datetime) -> list[dict[str, Any]]:
    opens: dict[tuple[str, str], dict[str, Any]] = {}
    closes: list[dict[str, Any]] = []

    for path in sorted(trade_journal_dir.glob("*.jsonl")):
        for event in _read_jsonl(path):
            key = _join_key(event)
            if key is None:
                continue
            if _event_type(event) == "trade_open":
                opens[key] = event
            elif _event_type(event) == "trade_close":
                closes.append(event)

    rows: list[dict[str, Any]] = []
    for close in closes:
        key = _join_key(close)
        if key is None:
            continue
        open_event = opens.get(key)
        if open_event is None:
            continue

        run_id, paper_key = key
        condition_id = _text(close, "condition_id") or _text(open_event, "condition_id") or _key_part(paper_key, 0)
        epoch_start_ts = _normalize_epoch(_text(close, "epoch_start_ts") or _text(open_event, "epoch_start_ts") or _key_part(paper_key, 1))
        asset = (_text(close, "asset", "ticker") or _text(open_event, "asset", "ticker") or _key_part(paper_key, 2)).upper()
        side = _side_from_event(close, paper_key) or _side_from_event(open_event, paper_key)
        candidate_id = _text(close, "candidate_id") or _text(open_event, "candidate_id")
        entry_ts = _parse_ts_from_event(open_event, "entry_timestamp")
        exit_ts = _parse_ts_from_event(close, "exit_timestamp")
        hold_seconds = _float(close, "hold_seconds")
        if hold_seconds is None and entry_ts is not None and exit_ts is not None:
            hold_seconds = (exit_ts - entry_ts).total_seconds()
        pnl = _float(close, "pnl_usdc", "pnl")
        reason = _text(close, "exit_reason", "reason")
        trade_result = _text(close, "trade_result")
        if not trade_result and reason == "take_profit_target_reached":
            trade_result = "TP"
        elif not trade_result and reason == "stop_loss":
            trade_result = "SL"
        outcome_win_loss = "WIN" if trade_result == "TP" or (pnl is not None and pnl > 0) else "LOSS"
        trade_open_lifecycle = _text(open_event, "lifecycle_phase")
        trade_close_lifecycle = _text(close, "lifecycle_phase")

        rows.append(
            {
                "export_schema_version": SCHEMA_VERSION,
                "export_generated_at_utc": generated_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
                "row_id": _row_id(run_id, paper_key),
                "canonical_opportunity_key": _canonical_key(condition_id, epoch_start_ts, asset, side, candidate_id),
                "run_id": run_id,
                "paper_trade_replay_key": paper_key,
                "condition_id": condition_id,
                "epoch_start_ts": epoch_start_ts,
                "asset": asset,
                "side": side,
                "candidate_id": candidate_id,
                "token_id": _key_part(paper_key, 4),
                "entry_ts": entry_ts.isoformat(timespec="microseconds").replace("+00:00", "Z") if entry_ts else "",
                "exit_ts": exit_ts.isoformat(timespec="microseconds").replace("+00:00", "Z") if exit_ts else "",
                "hold_seconds": "" if hold_seconds is None else f"{hold_seconds:.6f}".rstrip("0").rstrip("."),
                "entry_price": _float(open_event, "entry_price", "price"),
                "exit_price": _float(close, "exit_price"),
                "size": _float(close, "size") or _float(open_event, "size"),
                "trade_result": trade_result,
                "outcome_win_loss": outcome_win_loss,
                "pnl_usdc": pnl,
                "exit_reason": reason,
                "trade_open_lifecycle_phase": trade_open_lifecycle,
                "trade_close_lifecycle_phase": trade_close_lifecycle,
                "canonical_entry_lifecycle_phase": trade_open_lifecycle,
                "canonical_entry_lifecycle_source": "trade_journal.trade_open" if trade_open_lifecycle else "missing",
                "market_regime": "UNKNOWN",
                "trend_regime": "UNKNOWN",
                "volatility_regime": "UNKNOWN",
                "regime_reason": "",
                "regime_source": "missing",
                "regime_join_key": "",
                "regime_join_confidence": "MISSING",
                "regime_decision_ts": "",
                "regime_decision_delta_from_entry_s": "",
                "duplicate_opportunity_flag": "false",
                "duplicate_opportunity_count": 1,
                "canonical_retained_flag": "true",
                "row_quality": "MISSING_REGIME",
                "validation_notes": "missing_regime",
            }
        )
    rows.sort(key=lambda row: (row.get("entry_ts") or "", row.get("row_id") or ""))
    return rows


def _date_from_filename(path: Path) -> str:
    return path.stem[:10]


def _target_decision_dates(rows: list[dict[str, Any]]) -> set[str]:
    return {str(row.get("entry_ts") or "")[:10] for row in rows if row.get("entry_ts")}


def _decision_candidate(event: dict[str, Any]) -> DecisionCandidate:
    payload = _payload(event)
    paper_key = _text(event, "paper_trade_replay_key")
    condition_id = _text(event, "condition_id") or _key_part(paper_key, 0)
    epoch_start_ts = _normalize_epoch(_text(event, "epoch_start_ts") or _key_part(paper_key, 1))
    return DecisionCandidate(
        event=event,
        payload=payload,
        timestamp=_parse_ts_from_event(event),
        condition_id=condition_id,
        epoch_start_ts=epoch_start_ts,
        asset=(_text(event, "asset", "ticker") or _key_part(paper_key, 2)).upper(),
        side=_side_from_event(event, paper_key),
        candidate_id=_text(event, "candidate_id"),
        paper_trade_replay_key=paper_key,
        run_id=_run_id(event),
    )


def _load_decisions(decision_log_dir: Path, rows: list[dict[str, Any]]) -> list[DecisionCandidate]:
    dates = _target_decision_dates(rows)
    target_candidates = {str(row.get("candidate_id") or "") for row in rows if row.get("candidate_id")}
    target_replay_keys = {str(row.get("paper_trade_replay_key") or "") for row in rows if row.get("paper_trade_replay_key")}
    output: list[DecisionCandidate] = []

    for path in sorted(decision_log_dir.glob("*.jsonl")):
        if dates and _date_from_filename(path) not in dates:
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                candidate_match = _CANDIDATE_RE.search(line)
                replay_match = _REPLAY_KEY_RE.search(line)
                candidate_id = candidate_match.group(1) if candidate_match else ""
                paper_key = replay_match.group(1) if replay_match else ""
                if candidate_id not in target_candidates and paper_key not in target_replay_keys:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if _event_type(event) != "decision":
                    continue
                output.append(_decision_candidate(event))
    return output


def _decision_match_rank(row: dict[str, Any], decision: DecisionCandidate) -> tuple[int, str] | None:
    if (
        row["run_id"] == decision.run_id
        and row["paper_trade_replay_key"] == decision.paper_trade_replay_key
        and row["candidate_id"] == decision.candidate_id
    ):
        return 0, "run_id+paper_trade_replay_key+candidate_id"
    if row["run_id"] == decision.run_id and row["paper_trade_replay_key"] == decision.paper_trade_replay_key:
        return 1, "run_id+paper_trade_replay_key"
    if (
        row["condition_id"] == decision.condition_id
        and str(row["epoch_start_ts"]) == str(decision.epoch_start_ts)
        and row["asset"] == decision.asset
        and row["side"] == decision.side
        and row["candidate_id"] == decision.candidate_id
    ):
        return 2, "condition_id+epoch_start_ts+asset+side+candidate_id"
    if (
        row["condition_id"] == decision.condition_id
        and str(row["epoch_start_ts"]) == str(decision.epoch_start_ts)
        and row["asset"] == decision.asset
        and row["side"] == decision.side
    ):
        return 3, "condition_id+epoch_start_ts+asset+side"
    return None


def _select_decision(row: dict[str, Any], decisions: list[DecisionCandidate]) -> tuple[DecisionCandidate | None, str, str, float | None]:
    entry_ts = parse_utc(str(row["entry_ts"])) if row.get("entry_ts") else None
    ranked: list[tuple[tuple[Any, ...], DecisionCandidate, str, float | None]] = []
    for decision in decisions:
        match = _decision_match_rank(row, decision)
        if match is None:
            continue
        match_rank, join_key = match
        lifecycle = str(decision.payload.get("lifecycle_phase") or "")
        lifecycle_rank = 0 if lifecycle == "OPENING_SCAN" else 1 if "OPENING_SCAN" in lifecycle else 2
        delta = None
        if entry_ts is not None and decision.timestamp is not None:
            delta = (decision.timestamp - entry_ts).total_seconds()
        window_rank = 0 if delta is not None and -5 <= delta <= 30 else 1
        abs_delta = abs(delta) if delta is not None else 999999.0
        regime = str(decision.payload.get("market_regime") or "UNKNOWN").upper()
        unknown_rank = 1 if regime == "UNKNOWN" else 0
        decision_ts = decision.timestamp.isoformat() if decision.timestamp else ""
        decision_id = str(decision.payload.get("decision_id") or "")
        ranked.append(((match_rank, lifecycle_rank, window_rank, abs_delta, unknown_rank, decision_ts, decision_id), decision, join_key, delta))
    if not ranked:
        return None, "", "MISSING", None
    ranked.sort(key=lambda item: item[0])
    _, selected, join_key, delta = ranked[0]
    regime = str(selected.payload.get("market_regime") or "UNKNOWN").upper()
    if regime == "UNKNOWN":
        confidence = "MISSING"
    elif ranked[0][0][0] == 0:
        confidence = "DIRECT"
    elif ranked[0][0][0] == 1 and delta is not None and -5 <= delta <= 30:
        confidence = "STRONG"
    else:
        confidence = "WEAK"
    return selected, join_key, confidence, delta


def _enrich_regimes(rows: list[dict[str, Any]], decisions: list[DecisionCandidate]) -> None:
    for row in rows:
        selected, join_key, confidence, delta = _select_decision(row, decisions)
        notes = []
        if selected is None:
            notes.append("missing_regime")
        else:
            regime = str(selected.payload.get("market_regime") or "UNKNOWN").upper()
            row["market_regime"] = regime
            row["trend_regime"] = str(selected.payload.get("trend_regime") or "UNKNOWN").upper()
            row["volatility_regime"] = str(selected.payload.get("volatility_regime") or "UNKNOWN").upper()
            row["regime_reason"] = str(selected.payload.get("regime_reason") or "")
            row["regime_source"] = "decision_log.payload.market_regime" if regime != "UNKNOWN" else "missing"
            row["regime_join_key"] = join_key
            row["regime_join_confidence"] = confidence
            row["regime_decision_ts"] = selected.timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z") if selected.timestamp else ""
            row["regime_decision_delta_from_entry_s"] = "" if delta is None else f"{delta:.6f}".rstrip("0").rstrip(".")
            if regime == "UNKNOWN":
                notes.append("missing_regime")
        row["row_quality"] = "FULL" if row["regime_join_confidence"] in {"DIRECT", "STRONG"} else ("PARTIAL" if row["regime_join_confidence"] == "WEAK" else "MISSING_REGIME")
        row["validation_notes"] = "|".join(notes)


def _cell_qualifies(row: dict[str, Any]) -> bool:
    try:
        hold = float(row.get("hold_seconds") or 0)
    except ValueError:
        hold = 0.0
    return (
        row.get("asset") == "ETH"
        and row.get("side") == "YES"
        and "OPENING_SCAN" in str(row.get("canonical_entry_lifecycle_phase") or "")
        and hold > 15
        and (row.get("trade_result") in {"TP", "SL"} or row.get("pnl_usdc") not in {None, ""})
    )


def _mark_duplicates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    cell_rows = [row for row in rows if _cell_qualifies(row)]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in cell_rows:
        groups[str(row["canonical_opportunity_key"])].append(row)

    duplicate_rows_removed = 0
    for group in groups.values():
        group.sort(key=lambda row: (row.get("exit_ts") or "", row.get("run_id") or ""))
        count = len(group)
        duplicate_rows_removed += max(0, count - 1)
        for index, row in enumerate(group):
            row["duplicate_opportunity_count"] = count
            row["duplicate_opportunity_flag"] = "true" if count > 1 else "false"
            row["canonical_retained_flag"] = "true" if index == 0 else "false"
            if count > 1:
                notes = [note for note in str(row.get("validation_notes") or "").split("|") if note]
                notes.append("duplicate_opportunity")
                row["validation_notes"] = "|".join(dict.fromkeys(notes))
                if index > 0:
                    row["row_quality"] = "DUPLICATE"

    return {
        "raw_filtered_rows": len(cell_rows),
        "duplicate_rows_removed": duplicate_rows_removed,
        "canonical_n": sum(1 for row in cell_rows if row["canonical_retained_flag"] == "true"),
    }


def _source_file_metadata(*dirs: Path) -> tuple[dict[str, Any], float | None]:
    source_files: dict[str, Any] = {}
    latest_mtime: float | None = None
    for directory in dirs:
        files = sorted(directory.glob("*.jsonl")) if directory.exists() else []
        key = directory.name
        source_files[f"{key}_count"] = len(files)
        if files:
            latest = max(files, key=lambda path: path.stat().st_mtime)
            source_files[f"{key}_latest_file"] = latest.as_posix()
            source_files[f"{key}_latest_mtime_utc"] = datetime.fromtimestamp(latest.stat().st_mtime, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            latest_mtime = max(latest_mtime or 0.0, latest.stat().st_mtime)
    return source_files, latest_mtime


def _metadata(rows: list[dict[str, Any]], validation: dict[str, Any], trade_journal_dir: Path, decision_log_dir: Path, generated_at: datetime) -> dict[str, Any]:
    source_files, latest_mtime = _source_file_metadata(trade_journal_dir, decision_log_dir)
    source_lag = max(0.0, generated_at.timestamp() - latest_mtime) if latest_mtime is not None else None
    cell_retained = [row for row in rows if _cell_qualifies(row) and row["canonical_retained_flag"] == "true"]
    unknown_count = sum(1 for row in cell_retained if row["market_regime"] == "UNKNOWN")
    joined_count = sum(1 for row in cell_retained if row["regime_join_confidence"] in {"DIRECT", "STRONG", "WEAK"})
    direct_strong_count = sum(1 for row in cell_retained if row["regime_join_confidence"] in {"DIRECT", "STRONG"})
    canonical_n = validation["canonical_n"]
    unknown_rate = unknown_count / canonical_n if canonical_n else 0.0
    join_rate = joined_count / canonical_n if canonical_n else 0.0
    direct_strong_rate = direct_strong_count / canonical_n if canonical_n else 0.0
    status = "PASS"
    if canonical_n <= 0 or unknown_rate > 0.20:
        status = "FAIL"
    elif unknown_rate > 0.05 or direct_strong_rate < 0.90:
        status = "CAUTION"
    validation = {
        **validation,
        "regime_join_rate": join_rate,
        "direct_strong_rate": direct_strong_rate,
        "unknown_regime_count": unknown_count,
        "unknown_regime_rate": unknown_rate,
        "status": status,
    }
    return {
        "export_schema_version": SCHEMA_VERSION,
        "export_generated_at_utc": generated_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source_files": source_files,
        "freshness": {
            "status": classify_source_lag(source_lag),
            "source_lag_seconds": source_lag,
            "latest_trade_close_ts": max((row.get("exit_ts") or "" for row in rows), default=""),
            "latest_decision_ts_scanned": max((row.get("regime_decision_ts") or "" for row in rows), default=""),
        },
        "validation": validation,
    }


def build_canonical_regime_export(
    *,
    trade_journal_dir: Path = DEFAULT_TRADE_JOURNAL_DIR,
    decision_log_dir: Path = DEFAULT_DECISION_LOG_DIR,
    generated_at: datetime | None = None,
) -> ExportResult:
    generated = generated_at or datetime.now(timezone.utc)
    rows = _trade_rows(trade_journal_dir, generated)
    decisions = _load_decisions(decision_log_dir, rows)
    _enrich_regimes(rows, decisions)
    validation = _mark_duplicates(rows)
    metadata = _metadata(rows, validation, trade_journal_dir, decision_log_dir, generated)
    return ExportResult(rows=rows, metadata=metadata)


def write_csv(rows: list[dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def write_metadata(metadata: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_summary(result: ExportResult, path: Path) -> Path:
    validation = result.metadata["validation"]
    freshness = result.metadata["freshness"]
    lines = [
        "# Canonical Regime Enriched Trades V1 Summary",
        "",
        f"- Export status: {validation['status']}",
        f"- Freshness: {freshness['status']}",
        f"- Raw ETH YES FC OS rows: {validation['raw_filtered_rows']}",
        f"- Duplicate rows removed: {validation['duplicate_rows_removed']}",
        f"- Canonical n: {validation['canonical_n']}",
        f"- Regime join rate: {validation['regime_join_rate']:.1%}",
        f"- Direct+Strong join rate: {validation['direct_strong_rate']:.1%}",
        f"- UNKNOWN regime rate: {validation['unknown_regime_rate']:.1%}",
        "",
        "Runtime behavior changed: No",
        "Live behavior changed: No",
        "Strategy/risk/execution changed: No",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build offline canonical regime-enriched trade export.")
    parser.add_argument("--trade-journal-dir", type=Path, default=DEFAULT_TRADE_JOURNAL_DIR)
    parser.add_argument("--decision-log-dir", type=Path, default=DEFAULT_DECISION_LOG_DIR)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--meta-path", type=Path, default=DEFAULT_META_PATH)
    parser.add_argument("--summary-path", type=Path, default=DEFAULT_SUMMARY_PATH)
    parser.add_argument("--generated-at", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = build_canonical_regime_export(
        trade_journal_dir=args.trade_journal_dir,
        decision_log_dir=args.decision_log_dir,
        generated_at=parse_utc(args.generated_at) if args.generated_at else None,
    )
    write_csv(result.rows, args.output_path)
    write_metadata(result.metadata, args.meta_path)
    write_summary(result, args.summary_path)
    validation = result.metadata["validation"]
    print(
        "canonical regime export generated: "
        f"rows={len(result.rows)}, raw_filtered={validation['raw_filtered_rows']}, "
        f"duplicates_removed={validation['duplicate_rows_removed']}, canonical_n={validation['canonical_n']}, "
        f"status={validation['status']}, output={args.output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
