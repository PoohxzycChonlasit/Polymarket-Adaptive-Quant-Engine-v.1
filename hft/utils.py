"""
hft/utils.py
============
Timestamp helpers, fee math, trade record, CSV logging.
"""
from __future__ import annotations

import csv
import logging
import math
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger(__name__)


# ── Timestamp helpers ──────────────────────────────────────────────────────────

def current_epoch() -> int:
    """Return the Unix timestamp of the current 5-min window start (divisible by 300)."""
    now = int(time.time())
    return now - (now % 300)


def epoch_end(epoch: int) -> int:
    """Return the window end timestamp."""
    return epoch + 300


def seconds_remaining(epoch: int | None = None) -> int:
    """Seconds until the current (or given) 5-min window closes."""
    ep = epoch if epoch is not None else current_epoch()
    end = ep + 300
    return max(0, end - int(time.time()))


def time_progress(epoch: int | None = None) -> float:
    """How far through the current window: 0.0 = just started, 1.0 = ended."""
    secs = seconds_remaining(epoch)
    return max(0.0, min(1.0, 1.0 - secs / 300.0))


def window_label(epoch: int | None = None) -> str:
    """Human-readable window label e.g. '14:35-14:40'."""
    ep = epoch if epoch is not None else current_epoch()
    start = time.strftime("%H:%M", time.localtime(ep))
    end   = time.strftime("%H:%M", time.localtime(ep + 300))
    return f"{start}-{end}"


# ── Fee math ───────────────────────────────────────────────────────────────────

def calc_fee(shares: float, price: float, fee_rate: float = 0.002) -> float:
    """Trading fee in USD for a position."""
    return round(shares * price * fee_rate, 6)


def ev_for_yes(p_yes: float, yes_price: float, fee_rate: float = 0.002) -> float:
    """
    EV for buying YES at yes_price.

    Payout: p_yes * 1.0 per share if win, 0 if lose.
    Cost:   yes_price + fee per share.
    EV     = p_yes * (1 - yes_price) - (1 - p_yes) * yes_price - fee_rate
           = p_yes - yes_price - fee_rate
    """
    return p_yes - yes_price - fee_rate


def ev_for_no(p_yes: float, no_price: float, fee_rate: float = 0.002) -> float:
    """EV for buying NO (= betting price will be BELOW PTB)."""
    p_no = 1.0 - p_yes
    return p_no - no_price - fee_rate


def kelly_fraction(p: float, price: float) -> float:
    """
    Full Kelly fraction for a binary bet.

    b = net odds per dollar bet = (1 - price) / price
    f = (p*b - (1-p)) / b  =  p - (1-p)/b  =  p - (1-p)*price/(1-price)
    Simplified:  f = (p - price) / (1 - price)
    """
    if price <= 0 or price >= 1:
        return 0.0
    f = (p - price) / (1.0 - price)
    return max(0.0, f)


# ── Trade record ───────────────────────────────────────────────────────────────

@dataclass
class TradeRecord:
    trade_id:          str
    timestamp:         str
    asset:             str
    window_epoch:      int
    window_label:      str
    side:              str       # YES / NO
    entry_price:       float
    shares:            float
    cost_usd:          float
    p_model:           float
    edge:              float
    ev:                float
    momentum_pct:      float
    window_delta_pct:  float
    rsi:               float
    seconds_remaining: int
    exit_price:        float = 0.0
    pnl_usd:           float = 0.0
    outcome:           str   = ""   # WIN / LOSS / OPEN / CANCELLED
    paper:             bool  = True
    strategy:          str   = "hft_window_delta"
    bankroll_after:    float = 0.0
    brier_score:       float = 0.0

    def close(self, exit_price: float, won: bool, bankroll: float, brier: float) -> None:
        self.exit_price     = exit_price
        self.pnl_usd        = round(self.shares * (exit_price - self.entry_price), 6)
        self.outcome        = "WIN" if won else "LOSS"
        self.bankroll_after = bankroll
        self.brier_score    = brier


# ── CSV logger ─────────────────────────────────────────────────────────────────

class CSVTradeLogger:
    """Append trade records to a CSV file. Thread-safe via file open/close per write."""

    _FIELDS = list(TradeRecord.__dataclass_fields__.keys())

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            with open(self._path, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=self._FIELDS).writeheader()
            LOGGER.info("[CSVLogger] Created %s", self._path)

    def log(self, record: TradeRecord) -> None:
        row = asdict(record)
        with open(self._path, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=self._FIELDS).writerow(row)


# ── Misc ───────────────────────────────────────────────────────────────────────

def sigmoid(x: float, steepness: float = 1.0) -> float:
    return 1.0 / (1.0 + math.exp(-steepness * x))


def clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))
