"""
realtime_logger.py
==================
เก็บ Log การเทรด Realtime ทุก cycle ลงไฟล์ CSV + JSON แยกรายวัน
เพื่อใช้วิเคราะห์ผลการเทรดวันต่อวัน
"""
from __future__ import annotations

import csv
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

LOG_ROOT = Path("runtime/realtime_logs")


# ──────────────────────────────────────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ScanRecord:
    """บันทึก 1 รอบการ scan (1 asset per cycle)"""
    timestamp_utc: str          # ISO-8601
    date_th: str                # วันที่ไทย dd/mm/yyyy
    time_th: str                # เวลาไทย HH:MM:SS
    asset: str
    feed: str
    decision: str               # buy / sell / skip
    confidence: float
    edge: float
    momentum_pct: float         # 3-candle momentum at signal time
    score: float                # composite signal score
    signal: str                 # YES / NO / SKIP
    position_size: float
    order_id: str
    order_status: str
    skip_reason: str
    daily_pnl_pct: float        # % P&L ของวันนี้
    bankroll: float             # ยอดพอร์ตปัจจุบัน


@dataclass
class DailySummary:
    """สรุปผลรายวัน — บันทึกเมื่อจบวัน"""
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
    target_hit: bool            # ถึงเป้า 10% หรือยัง
    notes: str = ""
    asset_breakdown: dict = field(default_factory=dict)


# ──────────────────────────────────────────────────────────────────────────────
# RealtimeLogger Class
# ──────────────────────────────────────────────────────────────────────────────

class RealtimeLogger:
    """
    จัดการ Log ทั้งหมดของ Realtime Trader:
    - บันทึกทุก scan cycle ลง CSV รายวัน
    - สร้าง JSON Summary รายวัน
    - ติดตาม P&L และ เป้าหมายรายวัน
    """

    def __init__(self, initial_balance: float = 10.0, daily_target_pct: float = 0.10):
        self.initial_balance = initial_balance
        self.daily_target_pct = daily_target_pct

        # State ปัจจุบัน
        self.current_date = ""
        self.start_of_day_balance = initial_balance
        self.balance = initial_balance

        # สถิติรายวัน
        self.daily_scans = 0
        self.daily_executed = 0
        self.daily_skipped = 0
        self.daily_wins = 0
        self.daily_losses = 0
        self.asset_pnl: dict[str, float] = {}

        # ไฟล์ CSV ปัจจุบัน
        self._csv_path: Path | None = None
        self._csv_writer = None
        self._csv_file = None

        LOG_ROOT.mkdir(parents=True, exist_ok=True)

    # ─── วันใหม่ ─────────────────────────────────────────────────────────────

    def _check_new_day(self, date_str: str) -> bool:
        """ตรวจว่าเป็นวันใหม่ ถ้าใช่ให้ปิด log เก่าและเปิดใหม่"""
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
        LOGGER.info("[Logger] วันใหม่ %s | Balance เริ่มต้น: $%.4f", date_str, self.start_of_day_balance)
        return True

    def _open_csv(self, date_str: str):
        day_dir = LOG_ROOT / date_str
        day_dir.mkdir(parents=True, exist_ok=True)
        self._csv_path = day_dir / "scan_log.csv"

        file_exists = self._csv_path.exists()
        self._csv_file = open(self._csv_path, "a", newline="", encoding="utf-8")
        self._csv_writer = csv.writer(self._csv_file)
        if not file_exists:
            self._csv_writer.writerow([
                "timestamp_utc", "date_th", "time_th", "asset", "feed",
                "decision", "confidence", "edge", "momentum_pct", "score",
                "signal", "position_size", "order_id", "order_status",
                "skip_reason", "daily_pnl_pct", "bankroll",
            ])
        LOGGER.info("[Logger] เปิด CSV Log: %s", self._csv_path)

    def _close_csv(self):
        if self._csv_file:
            self._csv_file.flush()
            self._csv_file.close()
            self._csv_file = None
            self._csv_writer = None

    # ─── บันทึก 1 scan record ────────────────────────────────────────────────

    def log_scan(self, record: ScanRecord):
        """บันทึก 1 asset ใน 1 cycle"""
        now_utc = datetime.now(timezone.utc)
        date_str = now_utc.strftime("%Y-%m-%d")
        self._check_new_day(date_str)

        self.daily_scans += 1

        if record.decision.lower() in ("buy", "long"):
            self.daily_executed += 1
        else:
            self.daily_skipped += 1

        if self._csv_writer:
            self._csv_writer.writerow([
                record.timestamp_utc, record.date_th, record.time_th,
                record.asset, record.feed, record.decision,
                f"{record.confidence:.4f}", f"{record.edge:.4f}",
                f"{record.momentum_pct:.4f}", f"{record.score:.4f}",
                record.signal, f"{record.position_size:.6f}",
                record.order_id, record.order_status, record.skip_reason,
                f"{record.daily_pnl_pct:.4f}", f"{record.bankroll:.4f}",
            ])
            if self._csv_file:
                self._csv_file.flush()

    # ─── บันทึก trade ปิด (Win/Loss) ─────────────────────────────────────────

    def log_trade_result(self, asset: str, pnl: float):
        """เรียกเมื่อ trade ปิด (paper หรือจริง)"""
        self.balance += pnl
        if asset not in self.asset_pnl:
            self.asset_pnl[asset] = 0.0
        self.asset_pnl[asset] += pnl

        if pnl > 0:
            self.daily_wins += 1
        else:
            self.daily_losses += 1

    # ─── ดึง daily P&L % ─────────────────────────────────────────────────────

    def get_daily_pnl_pct(self) -> float:
        if self.start_of_day_balance <= 0:
            return 0.0
        return (self.balance - self.start_of_day_balance) / self.start_of_day_balance

    def target_hit(self) -> bool:
        return self.get_daily_pnl_pct() >= self.daily_target_pct

    # ─── บันทึก Summary JSON รายวัน ──────────────────────────────────────────

    def _save_daily_summary(self):
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

        day_dir = LOG_ROOT / self.current_date
        day_dir.mkdir(parents=True, exist_ok=True)
        summary_path = day_dir / "daily_summary.json"

        summary_dict = asdict(summary)
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_dict, f, ensure_ascii=False, indent=2)

        LOGGER.info(
            "[Logger] บันทึก Daily Summary: %s | P&L: %+.2f%% | Trades: %d",
            self.current_date, return_pct, total_trades
        )

    def force_save_summary(self):
        """เรียกตอน shutdown เพื่อ save summary ของวันปัจจุบัน"""
        self._close_csv()
        self._save_daily_summary()

    # ─── อ่าน Summaries ทั้งหมด (สำหรับ report) ──────────────────────────────

    @staticmethod
    def load_all_summaries() -> list[dict]:
        LOG_ROOT.mkdir(parents=True, exist_ok=True)
        summaries = []
        for day_dir in sorted(LOG_ROOT.iterdir()):
            summary_path = day_dir / "daily_summary.json"
            if summary_path.exists():
                with open(summary_path, encoding="utf-8") as f:
                    summaries.append(json.load(f))
        return summaries
