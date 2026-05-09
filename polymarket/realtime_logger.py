from __future__ import annotations

import csv
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

LOGGER = logging.getLogger(__name__)

LOG_ROOT = Path("runtime/realtime_logs")


@dataclass
class ScanRecord:
    timestamp_utc: str
    date_th: str
    time_th: str
    asset: str
    feed: str
    decision: str
    confidence: float
    edge: float
    momentum_pct: float
    score: float
    signal: str
    position_size: float
    order_id: str
    order_status: str
    skip_reason: str
    daily_pnl_pct: float
    bankroll: float
    raw_skip_reason: str = ""
    normalized_skip_reason: str = ""
    seconds_remaining: int = 0
    entry_cutoff_seconds: int = 0
    time_bucket: str = ""
    epoch_start: str = ""
    market_start_time: str = ""
    market_end_time: str = ""
    token_id: str = ""
    outcome: str = ""
    source_module: str = ""
    market_slug: str = ""
    condition_id: str = ""
    orderbook_age_ms: int = 0
    oracle_age_ms: int = 0
    market_feed_age_ms: int = 0
    token_mapping_warning: str = ""


@dataclass
class DailySummary:
    date: str
    start_balance: float
    end_balance: float
    net_pnl: float
    return_pct: float
    total_scans: int
    trades_executed: int
    trades_skipped: int
    wins: int
    losses: int
    win_rate: float
    best_asset: str
    worst_asset: str
    target_hit: bool
    notes: str = ""
    asset_breakdown: dict = field(default_factory=dict)


class RealtimeLogger:
    """Write realtime scan/trade logs without endangering the trading loop."""

    def __init__(self, initial_balance: float = 10.0, daily_target_pct: float = 0.10):
        self.initial_balance = initial_balance
        self.daily_target_pct = daily_target_pct

        self.current_date = ""
        self.start_of_day_balance = initial_balance
        self.balance = initial_balance

        self.daily_scans = 0
        self.daily_executed = 0
        self.daily_skipped = 0
        self.daily_wins = 0
        self.daily_losses = 0
        self.asset_pnl: dict[str, float] = {}

        self._csv_path: Path | None = None
        self._csv_writer: csv.writer | None = None
        self._csv_file = None
        self._csv_disabled = False
        self._closed = False
        self._run_id = f"{datetime.now():%Y%m%d_%H%M%S}_{os.getpid()}"

        try:
            LOG_ROOT.mkdir(parents=True, exist_ok=True)
        except PermissionError as exc:
            self._disable_csv_logger("create_log_root", exc)
        except OSError as exc:
            if getattr(exc, "errno", None) == 13:
                self._disable_csv_logger("create_log_root", exc)
            else:
                raise

    def _check_new_day(self, date_str: str) -> bool:
        if date_str == self.current_date:
            return False

        if self.current_date:
            self._close_csv()
            self._save_daily_summary()

        self.current_date = date_str
        self.start_of_day_balance = self.balance
        self.daily_scans = 0
        self.daily_executed = 0
        self.daily_skipped = 0
        self.daily_wins = 0
        self.daily_losses = 0
        self.asset_pnl = {}
        self._open_csv(date_str)
        LOGGER.info("[Logger] New day %s | Start balance: $%.4f", date_str, self.start_of_day_balance)
        return True

    def _open_csv(self, date_str: str) -> None:
        if self._csv_disabled or self._closed:
            return
        day_dir = LOG_ROOT / date_str
        try:
            day_dir.mkdir(parents=True, exist_ok=True)
            self._csv_path = day_dir / f"scan_log_{self._run_id}.csv"
            file_exists = self._csv_path.exists()
            self._csv_file = open(self._csv_path, "a", newline="", encoding="utf-8")
            self._csv_writer = csv.writer(self._csv_file)
            if not file_exists:
                self._csv_writer.writerow([
                    "timestamp_utc", "date_th", "time_th", "asset", "feed",
                    "decision", "confidence", "edge", "momentum_pct", "score",
                    "signal", "position_size", "order_id", "order_status",
                    "skip_reason", "daily_pnl_pct", "bankroll",
                    "raw_skip_reason", "normalized_skip_reason",
                    "seconds_remaining", "entry_cutoff_seconds", "time_bucket",
                    "epoch_start", "market_start_time", "market_end_time",
                    "token_id", "outcome", "source_module", "market_slug", "condition_id",
                    "orderbook_age_ms", "oracle_age_ms", "market_feed_age_ms", "token_mapping_warning",
                ])
                self._safe_flush_csv("header_flush")
        except PermissionError as exc:
            self._disable_csv_logger("open_csv", exc)
            return
        except OSError as exc:
            if getattr(exc, "errno", None) == 13:
                self._disable_csv_logger("open_csv", exc)
                return
            raise
        LOGGER.info("[Logger] Opened CSV log: %s", self._csv_path)

    def _close_csv(self) -> None:
        if not self._csv_file:
            return
        if not self._safe_flush_csv("close_flush"):
            return
        try:
            self._csv_file.close()
        except PermissionError as exc:
            self._disable_csv_logger("close_csv", exc)
            return
        except OSError as exc:
            if getattr(exc, "errno", None) == 13:
                self._disable_csv_logger("close_csv", exc)
                return
            raise
        self._csv_file = None
        self._csv_writer = None

    def _disable_csv_logger(self, operation: str, exc: BaseException) -> None:
        self._csv_disabled = True
        self._csv_writer = None
        file_obj = self._csv_file
        self._csv_file = None
        if file_obj is not None:
            try:
                file_obj.close()
            except Exception:
                pass
        LOGGER.warning(
            "[Logger] CSV file logging disabled for this session | operation=%s path=%s error=%s",
            operation,
            self._csv_path or "unknown",
            exc,
        )

    def _safe_flush_csv(self, operation: str) -> bool:
        if not self._csv_file:
            return False
        try:
            self._csv_file.flush()
            return True
        except PermissionError as exc:
            self._disable_csv_logger(operation, exc)
            return False
        except OSError as exc:
            if getattr(exc, "errno", None) == 13:
                self._disable_csv_logger(operation, exc)
                return False
            raise

    def log_scan(self, record: ScanRecord) -> None:
        if self._closed:
            return
        now_utc = datetime.now(timezone.utc)
        date_str = now_utc.strftime("%Y-%m-%d")
        self._check_new_day(date_str)

        self.daily_scans += 1
        if record.decision.lower() in ("buy", "long"):
            self.daily_executed += 1
        else:
            self.daily_skipped += 1

        if not self._csv_writer or self._csv_disabled:
            return

        try:
            self._csv_writer.writerow([
                record.timestamp_utc, record.date_th, record.time_th,
                record.asset, record.feed, record.decision,
                f"{record.confidence:.4f}", f"{record.edge:.4f}",
                f"{record.momentum_pct:.4f}", f"{record.score:.4f}",
                record.signal, f"{record.position_size:.6f}",
                record.order_id, record.order_status, record.skip_reason,
                f"{record.daily_pnl_pct:.4f}", f"{record.bankroll:.4f}",
                record.raw_skip_reason,
                record.normalized_skip_reason,
                str(record.seconds_remaining),
                str(record.entry_cutoff_seconds),
                record.time_bucket,
                record.epoch_start,
                record.market_start_time,
                record.market_end_time,
                record.token_id,
                record.outcome,
                record.source_module,
                record.market_slug,
                record.condition_id,
                str(record.orderbook_age_ms),
                str(record.oracle_age_ms),
                str(record.market_feed_age_ms),
                record.token_mapping_warning,
            ])
        except PermissionError as exc:
            self._disable_csv_logger("write_scan", exc)
            return
        except OSError as exc:
            if getattr(exc, "errno", None) == 13:
                self._disable_csv_logger("write_scan", exc)
                return
            raise
        self._safe_flush_csv("flush_scan")

    def log_trade_result(self, asset: str, pnl: float) -> None:
        self.balance += pnl
        if asset not in self.asset_pnl:
            self.asset_pnl[asset] = 0.0
        self.asset_pnl[asset] += pnl

        if pnl > 0:
            self.daily_wins += 1
        else:
            self.daily_losses += 1

    def get_daily_pnl_pct(self) -> float:
        if self.start_of_day_balance <= 0:
            return 0.0
        return (self.balance - self.start_of_day_balance) / self.start_of_day_balance

    def target_hit(self) -> bool:
        return self.get_daily_pnl_pct() >= self.daily_target_pct

    def _save_daily_summary(self) -> None:
        if not self.current_date:
            return

        total_trades = self.daily_wins + self.daily_losses
        win_rate = (self.daily_wins / total_trades * 100) if total_trades > 0 else 0.0
        daily_pnl = self.balance - self.start_of_day_balance
        return_pct = (daily_pnl / self.start_of_day_balance * 100) if self.start_of_day_balance > 0 else 0.0

        best_asset = max(self.asset_pnl, key=self.asset_pnl.get) if self.asset_pnl else "-"
        worst_asset = min(self.asset_pnl, key=self.asset_pnl.get) if self.asset_pnl else "-"

        summary = DailySummary(
            date=self.current_date,
            start_balance=self.start_of_day_balance,
            end_balance=self.balance,
            net_pnl=daily_pnl,
            return_pct=return_pct,
            total_scans=self.daily_scans,
            trades_executed=self.daily_executed,
            trades_skipped=self.daily_skipped,
            wins=self.daily_wins,
            losses=self.daily_losses,
            win_rate=win_rate,
            best_asset=best_asset,
            worst_asset=worst_asset,
            target_hit=self.target_hit(),
            asset_breakdown=dict(self.asset_pnl),
        )

        try:
            day_dir = LOG_ROOT / self.current_date
            day_dir.mkdir(parents=True, exist_ok=True)
            summary_path = day_dir / f"daily_summary_{self._run_id}.json"
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(asdict(summary), f, ensure_ascii=False, indent=2)
        except PermissionError as exc:
            LOGGER.warning("[Logger] Daily summary file disabled for this save | error=%s", exc)
            return
        except OSError as exc:
            if getattr(exc, "errno", None) == 13:
                LOGGER.warning("[Logger] Daily summary file disabled for this save | error=%s", exc)
                return
            raise

        LOGGER.info(
            "[Logger] Saved daily summary: %s | P&L: %+.2f%% | Trades: %d",
            self.current_date, return_pct, total_trades,
        )

    def force_save_summary(self) -> None:
        self.close(save_summary=True)

    def close(self, *, save_summary: bool = False) -> None:
        if self._closed and not save_summary:
            return
        self._close_csv()
        if save_summary:
            self._save_daily_summary()
        self._closed = True

    def shutdown(self) -> None:
        self.close(save_summary=True)

    def stop(self) -> None:
        self.close(save_summary=True)

    def __enter__(self) -> "RealtimeLogger":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close(save_summary=True)

    @staticmethod
    def load_all_summaries() -> list[dict]:
        LOG_ROOT.mkdir(parents=True, exist_ok=True)
        summaries: list[dict] = []
        for day_dir in sorted(LOG_ROOT.iterdir()):
            if not day_dir.is_dir():
                continue
            summary_paths = sorted(day_dir.glob("daily_summary*.json"))
            for summary_path in summary_paths:
                with open(summary_path, encoding="utf-8") as f:
                    summaries.append(json.load(f))
        return summaries
