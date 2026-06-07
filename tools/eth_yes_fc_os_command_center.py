from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_CSV_PATH = Path("runtime/research_exports/completed_trades_v1_2.csv")
DEFAULT_TRADE_JOURNAL_DIR = Path("runtime/quant_data/trade_journal")
DEFAULT_OUTPUT_PATH = Path("docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md")
DEFAULT_BASELINE_N = 61
DEFAULT_BASELINE_DATE = "2026-06-06"
NEXT_SNAPSHOT_N = 70
TARGET_N = 100
HISTORICAL_COMPRESSION_SHARE = 0.431
DEFAULT_DECISION_LOG_DAYS = 1


@dataclass
class DecisionMetrics:
    available: bool = False
    scan_days: int = DEFAULT_DECISION_LOG_DAYS
    latest_date: str | None = None
    latest_decision_count: int = 0
    eth_compression_share_latest: float | None = None
    eth_compression_share_7d: float | None = None
    compression_absence_days: int | None = None
    last_compression_date: str | None = None
    btc_regime_latest: str | None = None


@dataclass
class CommandCenterMetrics:
    source_label: str
    n: int
    raw_filtered_n: int
    duplicate_rows_removed: int
    wins: int
    losses: int
    wr: float | None
    pf: float | None
    gross_win: float
    gross_loss: float
    net_pnl: float
    median_pnl: float | None
    p_value: float | None
    n_required_current_wr: int | None
    n_required_59: int | None
    n_required_60: int | None
    calendar_weeks: list[str]
    rate_7d: float
    rate_14d: float
    rate_historical: float
    days_since_last: int | None
    trades_today: int
    last_5_regimes: list[str]
    regime_counts: Counter[str]
    nc_pf_current: float | None
    nc_pf_consecutive_below_one: int
    nc_pf_trough_idx: int | None
    nc_pf_trough_value: float | None
    n_new: int
    new_block_wr: float | None
    new_block_pf: float | None
    btc_n: int
    btc_wr: float | None
    k2_buffer: float | None
    excl_top_5_pf: float | None
    csv_staleness_hours: float | None
    generated_at: str
    decision_metrics: DecisionMetrics = field(default_factory=DecisionMetrics)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _today_date(today: str | date | datetime | None) -> date:
    if isinstance(today, datetime):
        return today.date()
    if isinstance(today, date):
        return today
    if isinstance(today, str) and today.strip():
        return date.fromisoformat(today.strip()[:10])
    return datetime.now(timezone.utc).date()


def _is_win(row: dict[str, Any]) -> bool:
    outcome = str(row.get("outcome_win_loss") or "").strip().upper()
    result = str(row.get("trade_result") or "").strip().upper()
    pnl = _pnl(row)
    if outcome in {"W", "WIN", "TRUE"}:
        return True
    if outcome in {"L", "LOSS", "FALSE"}:
        return False
    if result == "TP":
        return True
    if result == "SL":
        return False
    return pnl is not None and pnl > 0


def _pnl(row: dict[str, Any]) -> float | None:
    return _to_float(row.get("pnl_usdc")) or _to_float(row.get("pnl_recomputed")) or _to_float(row.get("signal_pnl"))


def _canonical_key(row: dict[str, Any]) -> tuple[str, ...]:
    fields = ["condition_id", "epoch_start_ts", "asset", "side", "candidate_id"]
    values = [str(row.get(field) or "").strip() for field in fields]
    if all(values):
        return tuple(values)
    replay_key = str(row.get("paper_trade_replay_key") or "").strip()
    if replay_key:
        return ("paper_trade_replay_key", replay_key)
    canonical_trade_id = str(row.get("canonical_trade_id") or "").strip()
    if canonical_trade_id:
        return ("canonical_trade_id", canonical_trade_id)
    return tuple(str(row.get(field) or "").strip() for field in row)


def _read_csv_rows(csv_path: Path) -> list[dict[str, Any]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


def _event_text(event: dict[str, Any], *names: str) -> str:
    payload = _payload(event)
    for name in names:
        value = payload.get(name)
        if value not in (None, ""):
            return str(value)
        value = event.get(name)
        if value not in (None, ""):
            return str(value)
    return ""


def _event_float(event: dict[str, Any], *names: str) -> float | None:
    for name in names:
        value = _to_float(_payload(event).get(name))
        if value is not None:
            return value
        value = _to_float(event.get(name))
        if value is not None:
            return value
    return None


def _trade_journal_rows(trade_journal_dir: Path) -> list[dict[str, Any]]:
    opens: dict[tuple[str, str], dict[str, Any]] = {}
    closes: list[dict[str, Any]] = []
    for path in sorted(trade_journal_dir.glob("*.jsonl")):
        for event in _iter_jsonl(path):
            event_type = str(event.get("event_type") or _payload(event).get("event_type") or "")
            run_id = str(event.get("run_id") or _payload(event).get("run_id") or "")
            replay_key = _event_text(event, "paper_trade_replay_key")
            if not run_id or not replay_key:
                continue
            key = (run_id, replay_key)
            if event_type == "trade_open":
                opens[key] = event
            elif event_type == "trade_close":
                closes.append(event)

    rows: list[dict[str, Any]] = []
    for close in closes:
        run_id = str(close.get("run_id") or _payload(close).get("run_id") or "")
        replay_key = _event_text(close, "paper_trade_replay_key")
        open_event = opens.get((run_id, replay_key), {})
        asset = (_event_text(close, "asset", "ticker") or _event_text(open_event, "asset", "ticker")).upper()
        side = (_event_text(close, "outcome", "side") or _event_text(open_event, "outcome", "side")).upper()
        epoch = _event_text(close, "epoch_start_ts") or _event_text(open_event, "epoch_start_ts")
        if epoch.endswith(".0"):
            epoch = epoch[:-2]
        pnl = _event_float(close, "pnl_usdc", "pnl")
        reason = _event_text(close, "reason", "exit_reason")
        trade_result = _event_text(close, "trade_result")
        if not trade_result and reason == "take_profit_target_reached":
            trade_result = "TP"
        elif not trade_result and reason == "stop_loss":
            trade_result = "SL"
        outcome = "WIN" if trade_result == "TP" or (pnl is not None and pnl > 0) else "LOSS"
        rows.append(
            {
                "run_id": run_id,
                "paper_trade_replay_key": replay_key,
                "condition_id": _event_text(close, "condition_id") or _event_text(open_event, "condition_id") or replay_key.split("|")[0],
                "epoch_start_ts": epoch or (replay_key.split("|")[1] if len(replay_key.split("|")) > 1 else ""),
                "candidate_id": _event_text(close, "candidate_id") or _event_text(open_event, "candidate_id"),
                "asset": asset,
                "side": side,
                "canonical_entry_lifecycle_phase": _event_text(open_event, "lifecycle_phase") or _event_text(close, "lifecycle_phase"),
                "hold_seconds": _event_text(close, "hold_seconds"),
                "pnl_usdc": pnl,
                "outcome_win_loss": outcome,
                "trade_result": trade_result,
                "entry_ts": _event_text(open_event, "entry_timestamp", "timestamp_utc") or str(open_event.get("timestamp_utc") or ""),
                "exit_ts": _event_text(close, "exit_timestamp", "timestamp_utc") or str(close.get("timestamp_utc") or ""),
                "regime": _event_text(close, "regime", "market_regime") or _event_text(open_event, "regime", "market_regime") or "UNKNOWN",
            }
        )
    return rows


def _qualifies(row: dict[str, Any], *, asset: str = "ETH") -> bool:
    if str(row.get("asset") or "").strip().upper() != asset:
        return False
    if str(row.get("side") or "").strip().upper() != "YES":
        return False
    lifecycle = str(row.get("canonical_entry_lifecycle_phase") or row.get("lifecycle_phase") or "")
    if "OPENING_SCAN" not in lifecycle:
        return False
    hold = _to_float(row.get("hold_seconds"))
    return hold is not None and hold > 15


def _dedupe_rows(rows: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(_canonical_key(row), []).append(row)

    retained: list[dict[str, Any]] = []
    for group in grouped.values():
        retained.append(
            sorted(
                group,
                key=lambda item: (
                    _parse_datetime(item.get("entry_ts")) or datetime.min.replace(tzinfo=timezone.utc),
                    str(item.get("canonical_trade_id") or ""),
                ),
            )[0]
        )
    retained.sort(key=lambda item: (_parse_datetime(item.get("entry_ts")) or datetime.min.replace(tzinfo=timezone.utc), str(_canonical_key(item))))
    return retained, sum(len(group) - 1 for group in grouped.values())


def _profit_factor(rows: Iterable[dict[str, Any]]) -> float | None:
    pnl_values = [value for row in rows for value in [_pnl(row)] if value is not None]
    wins = [value for value in pnl_values if value > 0]
    losses = [value for value in pnl_values if value < 0]
    if not wins and not losses:
        return None
    if wins and not losses:
        return math.inf
    if losses and not wins:
        return 0.0
    return sum(wins) / abs(sum(losses))


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _one_sided_binomial_p_value(wins: int, n: int) -> float | None:
    if n <= 0:
        return None
    return sum(math.comb(n, k) for k in range(wins, n + 1)) / (2**n)


def _n_required_for_p_value(wr: float | None, *, max_n: int = 500) -> int | None:
    if wr is None or wr <= 0.5:
        return None
    for n in range(1, max_n + 1):
        wins = math.ceil(wr * n)
        p_value = _one_sided_binomial_p_value(wins, n)
        if p_value is not None and p_value < 0.05:
            return n
    return None


def _iso_weeks(rows: list[dict[str, Any]]) -> list[str]:
    weeks: set[str] = set()
    for row in rows:
        parsed = _parse_datetime(row.get("entry_ts"))
        if parsed is None:
            continue
        iso = parsed.isocalendar()
        weeks.add(f"{iso.year}-W{iso.week:02d}")
    return sorted(weeks)


def _velocity(rows: list[dict[str, Any]], today: date, days: int) -> float:
    threshold = today - timedelta(days=days)
    count = 0
    for row in rows:
        parsed = _parse_datetime(row.get("entry_ts"))
        if parsed is not None and parsed.date() >= threshold:
            count += 1
    return count / days


def _trades_today(rows: list[dict[str, Any]], today: date) -> int:
    return sum(1 for row in rows if (_parse_datetime(row.get("entry_ts")) or datetime.min.replace(tzinfo=timezone.utc)).date() == today)


def _days_since_last(rows: list[dict[str, Any]], today: date) -> int | None:
    dates = [parsed.date() for row in rows for parsed in [_parse_datetime(row.get("entry_ts"))] if parsed is not None]
    if not dates:
        return None
    return (today - max(dates)).days


def _historical_rate(rows: list[dict[str, Any]], today: date) -> float:
    dates = [parsed.date() for row in rows for parsed in [_parse_datetime(row.get("entry_ts"))] if parsed is not None]
    if not dates:
        return 0.0
    span = max(1, (today - min(dates)).days)
    return len(rows) / span


def _nc_pf_series(rows: list[dict[str, Any]], window_size: int = 20) -> list[tuple[int, float | None]]:
    series: list[tuple[int, float | None]] = []
    for index in range(len(rows)):
        window = rows[max(0, index - window_size + 1) : index + 1]
        non_compression = [row for row in window if str(row.get("regime") or "UNKNOWN").strip().upper() != "COMPRESSION"]
        series.append((index + 1, _profit_factor(non_compression)))
    return series


def _current_and_consecutive_nc_pf(series: list[tuple[int, float | None]]) -> tuple[float | None, int, int | None, float | None]:
    current = next((value for _, value in reversed(series) if value is not None), None)
    consecutive = 0
    for _, value in reversed(series):
        if value is not None and value < 1.0:
            consecutive += 1
        elif value is not None:
            break
    numeric = [(idx, value) for idx, value in series if value is not None]
    if not numeric:
        return current, consecutive, None, None
    trough_idx, trough_value = min(numeric, key=lambda pair: pair[1])
    return current, consecutive, trough_idx, trough_value


def _format_percent(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.{digits}f}%"


def _format_float(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "N/A"
    if math.isinf(value):
        return "INF"
    return f"{value:.{digits}f}"


def _format_money(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.6f}"


def _eta(days_remaining: int, rate: float) -> str:
    if days_remaining <= 0:
        return "0 days"
    if rate <= 0:
        return "N/A"
    return f"{math.ceil(days_remaining / rate)} days"


def _status(pass_condition: bool, fail_condition: bool = False) -> str:
    if fail_condition:
        return "FAIL"
    return "PASS" if pass_condition else "OPEN"


def _progress_bar(n: int, target: int = TARGET_N, width: int = 40) -> str:
    filled = min(width, max(0, round(width * n / target)))
    return "#" * filled + "-" * (width - filled)


def _parse_decision_file_counts(path: Path) -> dict[str, Any]:
    counts: dict[str, Any] = {
        "decision_count": 0,
        "eth_total": 0,
        "eth_compression": 0,
        "btc_regimes": Counter(),
    }
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("event_type") != "decision":
                continue
            payload = _decision_payload(event)
            asset = str(payload.get("asset") or "").upper()
            regime = str(payload.get("market_regime") or "UNKNOWN").upper()
            counts["decision_count"] += 1
            if asset == "ETH":
                counts["eth_total"] += 1
                if regime == "COMPRESSION":
                    counts["eth_compression"] += 1
            elif asset == "BTC":
                counts["btc_regimes"][regime] += 1
    return counts


def _decision_payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else {}


def _date_from_jsonl(path: Path) -> date | None:
    try:
        return date.fromisoformat(path.stem[:10])
    except ValueError:
        return None


def _compute_decision_metrics(decision_log_dir: Path | None, today: date, scan_days: int = DEFAULT_DECISION_LOG_DAYS) -> DecisionMetrics:
    if decision_log_dir is None:
        return DecisionMetrics(available=False)
    if not decision_log_dir.exists():
        return DecisionMetrics(available=False)

    dated_paths = [(event_date, path) for path in decision_log_dir.glob("*.jsonl") for event_date in [_date_from_jsonl(path)] if event_date is not None]
    dated_paths.sort(key=lambda pair: pair[0])
    if scan_days > 0:
        dated_paths = dated_paths[-scan_days:]
    if not dated_paths:
        return DecisionMetrics(available=False)

    daily_counts: list[tuple[date, dict[str, Any]]] = []
    for event_date, path in dated_paths:
        daily_counts.append((event_date, _parse_decision_file_counts(path)))

    latest_date, latest_counts = max(daily_counts, key=lambda pair: pair[0])
    latest_share = latest_counts["eth_compression"] / latest_counts["eth_total"] if latest_counts["eth_total"] else None

    threshold = latest_date - timedelta(days=7)
    seven_day_eth_total = 0
    seven_day_eth_comp = 0
    last_compression_date: date | None = None
    for event_date, counts in daily_counts:
        share = counts["eth_compression"] / counts["eth_total"] if counts["eth_total"] else 0.0
        if share > 0.05:
            last_compression_date = event_date
        if event_date >= threshold:
            seven_day_eth_total += counts["eth_total"]
            seven_day_eth_comp += counts["eth_compression"]

    seven_day_share = seven_day_eth_comp / seven_day_eth_total if seven_day_eth_total else None
    btc_mode = latest_counts["btc_regimes"].most_common(1)[0][0] if latest_counts["btc_regimes"] else None
    absence_days = (today - last_compression_date).days if last_compression_date is not None else None

    return DecisionMetrics(
        available=True,
        scan_days=scan_days,
        latest_date=latest_date.isoformat(),
        latest_decision_count=latest_counts["decision_count"],
        eth_compression_share_latest=latest_share,
        eth_compression_share_7d=seven_day_share,
        compression_absence_days=absence_days,
        last_compression_date=last_compression_date.isoformat() if last_compression_date is not None else None,
        btc_regime_latest=btc_mode,
    )


def compute_metrics(
    *,
    csv_path: Path,
    trade_journal_dir: Path | None = None,
    decision_log_dir: Path | None = None,
    baseline_n: int = DEFAULT_BASELINE_N,
    baseline_date: str = DEFAULT_BASELINE_DATE,
    decision_log_days: int = DEFAULT_DECISION_LOG_DAYS,
    today: str | date | datetime | None = None,
) -> CommandCenterMetrics:
    today_value = _today_date(today)
    if trade_journal_dir is not None and trade_journal_dir.exists():
        raw_rows = _trade_journal_rows(trade_journal_dir)
        source_label = f"trade_journal:{trade_journal_dir.as_posix()}"
    else:
        raw_rows = _read_csv_rows(csv_path)
        source_label = f"csv:{csv_path.as_posix()}"
    raw_filtered = [row for row in raw_rows if _qualifies(row, asset="ETH")]
    rows, duplicate_rows_removed = _dedupe_rows(raw_filtered)
    btc_rows, _ = _dedupe_rows(row for row in raw_rows if _qualifies(row, asset="BTC"))

    pnl_values = [value for row in rows for value in [_pnl(row)] if value is not None]
    wins = sum(1 for row in rows if _is_win(row))
    losses = len(rows) - wins
    gross_win = sum(value for value in pnl_values if value > 0)
    gross_loss = sum(value for value in pnl_values if value < 0)
    wr = wins / len(rows) if rows else None
    pf = _profit_factor(rows)
    p_value = _one_sided_binomial_p_value(wins, len(rows)) if rows else None
    weeks = _iso_weeks(rows)
    rate_7d = _velocity(rows, today_value, 7)
    rate_14d = _velocity(rows, today_value, 14)
    rate_historical = _historical_rate(rows, today_value)
    regime_counts = Counter(str(row.get("regime") or "UNKNOWN").strip().upper() or "UNKNOWN" for row in rows)
    last_5_regimes = [str(row.get("regime") or "UNKNOWN").strip().upper() or "UNKNOWN" for row in rows[-5:]]
    nc_current, nc_consecutive, nc_trough_idx, nc_trough_value = _current_and_consecutive_nc_pf(_nc_pf_series(rows))

    baseline_day = date.fromisoformat(baseline_date)
    new_rows = [
        row
        for row in rows
        if (_parse_datetime(row.get("entry_ts")) is not None and _parse_datetime(row.get("entry_ts")).date() > baseline_day)
    ]
    new_block_wr = sum(1 for row in new_rows if _is_win(row)) / len(new_rows) if new_rows else None
    new_block_pf = _profit_factor(new_rows)
    btc_wr = sum(1 for row in btc_rows if _is_win(row)) / len(btc_rows) if btc_rows else None
    k2_buffer = pf - 1.3 if pf is not None and not math.isinf(pf) else pf
    excl_top_5_pf = _profit_factor(sorted(rows, key=lambda row: _pnl(row) or 0.0, reverse=True)[5:]) if len(rows) > 5 else None

    staleness_hours: float | None = None
    try:
        modified = datetime.fromtimestamp(csv_path.stat().st_mtime, tz=timezone.utc)
        staleness_hours = (datetime.now(timezone.utc) - modified).total_seconds() / 3600
    except OSError:
        pass

    return CommandCenterMetrics(
        source_label=source_label,
        n=len(rows),
        raw_filtered_n=len(raw_filtered),
        duplicate_rows_removed=duplicate_rows_removed,
        wins=wins,
        losses=losses,
        wr=wr,
        pf=pf,
        gross_win=gross_win,
        gross_loss=gross_loss,
        net_pnl=sum(pnl_values),
        median_pnl=_median(pnl_values),
        p_value=p_value,
        n_required_current_wr=_n_required_for_p_value(wr),
        n_required_59=_n_required_for_p_value(0.59),
        n_required_60=_n_required_for_p_value(0.60),
        calendar_weeks=weeks,
        rate_7d=rate_7d,
        rate_14d=rate_14d,
        rate_historical=rate_historical,
        days_since_last=_days_since_last(rows, today_value),
        trades_today=_trades_today(rows, today_value),
        last_5_regimes=last_5_regimes,
        regime_counts=regime_counts,
        nc_pf_current=nc_current,
        nc_pf_consecutive_below_one=nc_consecutive,
        nc_pf_trough_idx=nc_trough_idx,
        nc_pf_trough_value=nc_trough_value,
        n_new=max(0, len(rows) - baseline_n) if not new_rows else len(new_rows),
        new_block_wr=new_block_wr,
        new_block_pf=new_block_pf,
        btc_n=len(btc_rows),
        btc_wr=btc_wr,
        k2_buffer=k2_buffer,
        excl_top_5_pf=excl_top_5_pf,
        csv_staleness_hours=staleness_hours,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        decision_metrics=_compute_decision_metrics(decision_log_dir, today_value, decision_log_days),
    )


def _render_decision_value(value: Any, *, percent: bool = False) -> str:
    if value is None:
        return "[MANUAL REQUIRED]"
    if percent:
        return _format_percent(value)
    return str(value)


def _render_report(metrics: CommandCenterMetrics, *, csv_path: Path, jsonl_integrity_status: str) -> str:
    n_remaining = max(0, NEXT_SNAPSHOT_N - metrics.n)
    target_remaining = max(0, TARGET_N - metrics.n)
    pct = metrics.n / TARGET_N if TARGET_N else 0.0
    p1 = _status(metrics.n >= TARGET_N)
    p2 = _status(metrics.wr is not None and metrics.wr > 0.52)
    p3 = _status(metrics.pf is not None and metrics.pf > 1.5)
    p4 = _status(metrics.n_required_current_wr is not None and metrics.n_required_current_wr <= TARGET_N)
    p5 = _status(len(metrics.calendar_weeks) >= 3)
    k1_status = "INACTIVE" if metrics.n_new < 30 else _status(metrics.new_block_wr is not None and metrics.new_block_wr >= 0.48, metrics.new_block_wr is not None and metrics.new_block_wr < 0.48)
    k2_status = "INACTIVE" if metrics.n < 80 else _status(metrics.pf is not None and metrics.pf >= 1.3, metrics.pf is not None and metrics.pf < 1.3)
    k3_status = "INACTIVE" if metrics.btc_n < 20 else _status(metrics.btc_wr is not None and metrics.btc_wr < 0.40, metrics.btc_wr is not None and metrics.btc_wr >= 0.40)
    k4_status = "INACTIVE" if metrics.n < TARGET_N else _status(metrics.excl_top_5_pf is not None and metrics.excl_top_5_pf > 1.0, metrics.excl_top_5_pf is not None and metrics.excl_top_5_pf <= 1.0)
    tripwire_status = "ADVISORY" if metrics.nc_pf_consecutive_below_one > 10 else "WARNING" if metrics.nc_pf_consecutive_below_one > 5 else "CLEAR"
    velocity_status = "STALLED" if metrics.rate_7d < 0.5 else "ACCUMULATING_SLOWLY" if metrics.rate_7d < 1.0 else "ACTIVE"
    stale_status = "STALE >24h" if metrics.csv_staleness_hours is not None and metrics.csv_staleness_hours > 24 else "FRESH/RECENT"
    weeks = ", ".join(metrics.calendar_weeks) if metrics.calendar_weeks else "N/A"
    regime_sequence = " -> ".join(metrics.last_5_regimes) if metrics.last_5_regimes else "N/A"
    regime_mix = ", ".join(f"{key}:{value}" for key, value in sorted(metrics.regime_counts.items())) or "N/A"
    decision = metrics.decision_metrics

    return f"""# ETH_YES_FC_OS Command Center

Generated: {metrics.generated_at}

Source evidence: `{metrics.source_label}`

Mode: offline report-only

Non-authorization: this report does not change strategy, risk, execution, sizing, live behavior, runtime policy, or alerts.

---

## Panel A: Gate Status

### Promotion Gates

| Gate | Criterion | Status | Current |
|---|---|---|---|
| P1 | n >= 100 | {p1} | Canonical n = {metrics.n} |
| P2 | WR > 52% | {p2} | {_format_percent(metrics.wr)} |
| P3 | PF > 1.5 | {p3} | {_format_float(metrics.pf)} |
| P4 | p < 0.05 at or before n=100 | {p4} | p={_format_float(metrics.p_value)}; n_required={metrics.n_required_current_wr or 'N/A'} |
| P5 | >= 3 calendar weeks | {p5} | {len(metrics.calendar_weeks)} weeks ({weeks}) |

### Canonical Count

| Metric | Value |
|---|---:|
| Raw filtered rows | {metrics.raw_filtered_n} |
| Duplicate rows removed | {metrics.duplicate_rows_removed} |
| Canonical n | {metrics.n} |
| Remaining to n=70 | {n_remaining} |
| Remaining to n=100 | {target_remaining} |

### Runtime Integrity

| Check | Status |
|---|---|
| JSONL Writer | {jsonl_integrity_status} |
| CSV freshness | {stale_status} ({_format_float(metrics.csv_staleness_hours, 1)} hours) |

---

## Panel B: Progress Rail

```text
n = {metrics.n} / {TARGET_N}  [{_progress_bar(metrics.n)}]  {pct * 100:.1f}%
```

| Metric | Current | Target | Gap |
|---|---:|---:|---:|
| WR | {_format_percent(metrics.wr)} | >52.0% | {_format_percent(None if metrics.wr is None else metrics.wr - 0.52)} |
| PF | {_format_float(metrics.pf)} | >1.500 | {_format_float(None if metrics.pf is None or math.isinf(metrics.pf) else metrics.pf - 1.5)} |
| p-value | {_format_float(metrics.p_value)} | <0.050 | n_required={metrics.n_required_current_wr or 'N/A'} |

### P4 Transform

| WR scenario | n required for p < 0.05 |
|---|---:|
| Current WR ({_format_percent(metrics.wr)}) | {metrics.n_required_current_wr or 'N/A'} |
| 59.0% | {metrics.n_required_59 or 'N/A'} |
| 60.0% | {metrics.n_required_60 or 'N/A'} |

### ETA To Next Snapshot

| Velocity basis | Rate | ETA to n=70 |
|---|---:|---:|
| 7-day rolling | {metrics.rate_7d:.2f}/day | {_eta(n_remaining, metrics.rate_7d)} |
| 14-day rolling | {metrics.rate_14d:.2f}/day | {_eta(n_remaining, metrics.rate_14d)} |
| Historical campaign | {metrics.rate_historical:.2f}/day | {_eta(n_remaining, metrics.rate_historical)} |

---

## Panel C: Leading Indicators

### nc_PF Monitor

| Metric | Value |
|---|---:|
| Current nc_PF window=20 | {_format_float(metrics.nc_pf_current)} |
| Consecutive below 1.0 | {metrics.nc_pf_consecutive_below_one} |
| Trough index | {metrics.nc_pf_trough_idx or 'N/A'} |
| Trough value | {_format_float(metrics.nc_pf_trough_value)} |
| Tripwire status | {tripwire_status} |

### Market Structure

| Metric | Value |
|---|---|
| Decision log scan window | {decision.scan_days} dated files |
| Latest decision date | {_render_decision_value(decision.latest_date)} |
| ETH COMPRESSION share latest | {_render_decision_value(decision.eth_compression_share_latest, percent=True)} |
| ETH COMPRESSION share 7d | {_render_decision_value(decision.eth_compression_share_7d, percent=True)} |
| Historical COMPRESSION share | {_format_percent(HISTORICAL_COMPRESSION_SHARE)} |
| Last COMPRESSION date >5% | {_render_decision_value(decision.last_compression_date)} |
| COMPRESSION absence days | {_render_decision_value(decision.compression_absence_days)} |
| BTC regime latest | {_render_decision_value(decision.btc_regime_latest)} |
| Latest decision count | {_render_decision_value(decision.latest_decision_count if decision.available else None)} |

### Velocity And Stall

| Metric | Value |
|---|---:|
| Qualifying trades today | {metrics.trades_today} |
| Days since last qualifying trade | {metrics.days_since_last if metrics.days_since_last is not None else 'N/A'} |
| 7d velocity | {metrics.rate_7d:.2f}/day |
| 14d velocity | {metrics.rate_14d:.2f}/day |
| Velocity status | {velocity_status} |

### Last-5 Regime Sequence

```text
{regime_sequence}
```

Regime mix:

```text
{regime_mix}
```

---

## Panel D: Kill Criterion Monitors

| Guard | Criterion | Status | Current |
|---|---|---|---|
| K1 | New-block WR < 48% on >=30 new trades | {k1_status} | n_new={metrics.n_new}; WR={_format_percent(metrics.new_block_wr)}; PF={_format_float(metrics.new_block_pf)} |
| K2 | Cumulative PF < 1.3 at n>=80 | {k2_status} | PF={_format_float(metrics.pf)}; buffer={_format_float(metrics.k2_buffer)} |
| K3 | BTC WR > 40% on n_BTC>=20 | {k3_status} | n_BTC={metrics.btc_n}; WR={_format_percent(metrics.btc_wr)} |
| K4 | Excl. top-5 PF < 1.0 at n=100 | {k4_status} | excl_top_5_pf={_format_float(metrics.excl_top_5_pf)} |
| nc_PF | >10 consecutive below 1.0 advisory | {tripwire_status} | {metrics.nc_pf_consecutive_below_one}/10 |

---

## Snapshot Summary

| Metric | Value |
|---|---:|
| Wins | {metrics.wins} |
| Losses | {metrics.losses} |
| Gross win PnL | {_format_money(metrics.gross_win)} |
| Gross loss PnL | {_format_money(metrics.gross_loss)} |
| Net PnL | {_format_money(metrics.net_pnl)} |
| Median PnL | {_format_money(metrics.median_pnl)} |

## Governor Read

This command center is observational only. Use it to decide whether to continue accumulation, trigger a drift review, or prepare the next milestone snapshot. It does not authorize runtime filters, execution changes, risk changes, or live trading.
"""


def generate_command_center_report(
    *,
    csv_path: Path = DEFAULT_CSV_PATH,
    trade_journal_dir: Path | None = None,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    decision_log_dir: Path | None = None,
    jsonl_integrity_status: str = "BLOCKED",
    baseline_n: int = DEFAULT_BASELINE_N,
    baseline_date: str = DEFAULT_BASELINE_DATE,
    decision_log_days: int = DEFAULT_DECISION_LOG_DAYS,
    today: str | date | datetime | None = None,
) -> CommandCenterMetrics:
    metrics = compute_metrics(
        csv_path=csv_path,
        trade_journal_dir=trade_journal_dir,
        decision_log_dir=decision_log_dir,
        baseline_n=baseline_n,
        baseline_date=baseline_date,
        decision_log_days=decision_log_days,
        today=today,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_report(metrics, csv_path=csv_path, jsonl_integrity_status=jsonl_integrity_status), encoding="utf-8")
    return metrics


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the ETH YES FC OS offline command-center report.")
    parser.add_argument("--csv-path", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--trade-journal-dir", type=Path, default=DEFAULT_TRADE_JOURNAL_DIR)
    parser.add_argument("--csv-only", action="store_true", help="Use only --csv-path and do not derive canonical count from trade journal JSONL.")
    parser.add_argument("--decision-log-dir", type=Path, default=None)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--jsonl-integrity-status", default="BLOCKED")
    parser.add_argument("--baseline-n", type=int, default=DEFAULT_BASELINE_N)
    parser.add_argument("--baseline-date", default=DEFAULT_BASELINE_DATE)
    parser.add_argument("--decision-log-days", type=int, default=DEFAULT_DECISION_LOG_DAYS, help="Number of latest dated decision-log files to scan; use 0 to scan all. Default is 1 because decision logs can be multi-GB.")
    parser.add_argument("--today", default=None, help="Optional YYYY-MM-DD override for deterministic reports.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    metrics = generate_command_center_report(
        csv_path=args.csv_path,
        trade_journal_dir=None if args.csv_only else args.trade_journal_dir,
        output_path=args.output_path,
        decision_log_dir=args.decision_log_dir,
        jsonl_integrity_status=args.jsonl_integrity_status,
        baseline_n=args.baseline_n,
        baseline_date=args.baseline_date,
        decision_log_days=args.decision_log_days,
        today=args.today,
    )
    print(
        "ETH_YES_FC_OS command center generated: "
        f"n={metrics.n}, WR={_format_percent(metrics.wr)}, PF={_format_float(metrics.pf)}, "
        f"p={_format_float(metrics.p_value)}, output={args.output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
