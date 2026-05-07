from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


LOGGER = logging.getLogger(__name__)

SummaryValue = float | int


@dataclass(slots=True)
class DashboardSnapshot:
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    summary: dict[str, SummaryValue]
    source_status: dict[str, int]


def _safe_read_json(path: Path) -> dict[str, SummaryValue]:
    if not path.exists():
        LOGGER.warning("JSON file not found: %s", path.as_posix())
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}

    normalized_payload: dict[str, SummaryValue] = {}
    for key, value in payload.items():
        if isinstance(value, (int, float)):
            normalized_payload[str(key)] = value
    return normalized_payload


def _safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        LOGGER.warning("CSV file not found: %s", path.as_posix())
        return pd.DataFrame()
    return pd.read_csv(path)


def _build_source_status(summary_path: Path, equity_path: Path, trades_path: Path) -> dict[str, int]:
    return {
        "summary_loaded": int(summary_path.exists()),
        "equity_loaded": int(equity_path.exists()),
        "trades_loaded": int(trades_path.exists()),
    }


def load_backtest_snapshot(base_dir: Path | None = None) -> DashboardSnapshot:
    resolved_dir = base_dir or Path("runtime")
    resolved_dir.mkdir(parents=True, exist_ok=True)

    summary_path = resolved_dir / "backtest_summary.json"
    equity_path = resolved_dir / "equity_curve.csv"
    trades_path = resolved_dir / "trades.csv"
    source_status = _build_source_status(summary_path, equity_path, trades_path)

    summary = _safe_read_json(summary_path)
    equity_curve = _safe_read_csv(equity_path)
    trades = _safe_read_csv(trades_path)

    if equity_curve.empty:
        equity_curve = pd.DataFrame(
            [
                {"timestamp": "2026-01-01 00:00:00", "equity": 10_000, "drawdown_pct": 0.0},
                {"timestamp": "2026-01-07 00:00:00", "equity": 10_250, "drawdown_pct": -0.8},
                {"timestamp": "2026-01-14 00:00:00", "equity": 10_480, "drawdown_pct": -0.3},
                {"timestamp": "2026-01-21 00:00:00", "equity": 10_150, "drawdown_pct": -2.4},
                {"timestamp": "2026-01-28 00:00:00", "equity": 10_720, "drawdown_pct": -0.4},
            ]
        )

    if trades.empty:
        trades = pd.DataFrame(
            [
                {"pair": "BTC/USDT", "side": "long", "profit_pct": 1.8, "duration_min": 35, "result": "win"},
                {"pair": "ETH/USDT", "side": "long", "profit_pct": -1.2, "duration_min": 22, "result": "loss"},
                {"pair": "SOL/USDT", "side": "long", "profit_pct": 2.4, "duration_min": 41, "result": "win"},
            ]
        )

    if not summary:
        win_rate = float((trades["result"] == "win").mean()) if "result" in trades else 0.0
        total_profit_pct = float(trades["profit_pct"].sum()) if "profit_pct" in trades else 0.0
        summary = {
            "starting_balance": 10_000,
            "ending_balance": float(equity_curve["equity"].iloc[-1]),
            "total_trades": int(len(trades)),
            "win_rate": round(win_rate * 100, 2),
            "profit_factor": 1.72,
            "max_drawdown_pct": float(abs(equity_curve["drawdown_pct"].min())),
            "total_profit_pct": round(total_profit_pct, 2),
        }

    LOGGER.info("Loaded dashboard snapshot from %s", resolved_dir.as_posix())
    return DashboardSnapshot(
        equity_curve=equity_curve,
        trades=trades,
        summary=summary,
        source_status=source_status,
    )
