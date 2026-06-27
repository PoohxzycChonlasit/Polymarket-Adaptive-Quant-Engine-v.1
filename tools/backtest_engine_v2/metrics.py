"""MetricsEngine — compute Sharpe, profit factor, expectancy, win rate, skipped EV."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from tools.backtest_engine_v2.equity import EquityState


@dataclass
class TradeMetrics:
    total_trades: int = 0
    accepted_trades: int = 0
    rejected_trades: int = 0
    acceptance_rate: float = 0.0
    capital_utilization: float = 0.0

    win_count: int = 0
    loss_count: int = 0
    win_rate: float = 0.0

    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0

    avg_win: float = 0.0
    avg_loss: float = 0.0

    sharpe: float = 0.0
    sortino: float = 0.0

    max_drawdown_pct: float = 0.0
    max_drawdown_usdc: float = 0.0
    starting_equity: float = 0.0
    ending_equity: float = 0.0
    total_return_pct: float = 0.0

    skipped_ev_total: float = 0.0
    skipped_ev_count: int = 0
    skipped_ev_avg: float = 0.0

    avg_hold_seconds: float = 0.0
    avg_ev: float = 0.0
    avg_probability: float = 0.0


class MetricsEngine:
    """Compute performance metrics from accepted and rejected canonical rows."""

    def compute(
        self,
        accepted: list[dict[str, Any]],
        rejected: list[dict[str, Any]],
        equity_state: EquityState,
    ) -> TradeMetrics:
        m = TradeMetrics()
        total = len(accepted) + len(rejected)
        m.total_trades = total
        m.accepted_trades = len(accepted)
        m.rejected_trades = len(rejected)
        m.acceptance_rate = len(accepted) / total if total > 0 else 0.0
        m.capital_utilization = m.acceptance_rate

        m.starting_equity = equity_state.starting_equity
        m.ending_equity = equity_state.ending_equity
        m.max_drawdown_pct = equity_state.max_drawdown_pct
        m.max_drawdown_usdc = equity_state.max_drawdown_usdc

        if m.starting_equity > 0:
            m.total_return_pct = (m.ending_equity - m.starting_equity) / m.starting_equity

        pnls = [float(r.get("realized_pnl") or 0.0) for r in accepted]
        if pnls:
            m.total_pnl = round(sum(pnls), 6)
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            m.win_count = len(wins)
            m.loss_count = len(losses)
            m.win_rate = m.win_count / len(pnls) if pnls else 0.0
            m.gross_profit = round(sum(wins), 6)
            m.gross_loss = round(sum(losses), 6)
            m.profit_factor = (
                abs(m.gross_profit / m.gross_loss) if m.gross_loss != 0 else float("inf")
            )
            m.expectancy = round(m.total_pnl / len(pnls), 6)
            m.avg_win = round(sum(wins) / m.win_count, 6) if m.win_count else 0.0
            m.avg_loss = round(sum(losses) / m.loss_count, 6) if m.loss_count else 0.0

            m.sharpe = _sharpe(pnls)
            m.sortino = _sortino(pnls)

        holds = [float(r.get("hold_seconds") or 0.0) for r in accepted]
        if holds:
            m.avg_hold_seconds = round(sum(holds) / len(holds), 2)

        evs = [float(r.get("ev") or 0.0) for r in accepted]
        if evs:
            m.avg_ev = round(sum(evs) / len(evs), 6)

        probs = [float(r.get("probability") or 0.0) for r in accepted]
        if probs:
            m.avg_probability = round(sum(probs) / len(probs), 6)

        # Skipped EV: sum of EV × notional for rejected trades
        skipped_evs = []
        for r in rejected:
            ev = float(r.get("ev") or 0.0)
            notional = float(r.get("intended_notional") or 0.0)
            skipped_evs.append(ev * notional)
        m.skipped_ev_count = len(skipped_evs)
        m.skipped_ev_total = round(sum(skipped_evs), 6)
        m.skipped_ev_avg = round(sum(skipped_evs) / len(skipped_evs), 6) if skipped_evs else 0.0

        return m


def _sharpe(pnls: list[float], risk_free: float = 0.0) -> float:
    n = len(pnls)
    if n < 2:
        return 0.0
    mean = sum(pnls) / n - risk_free
    var = sum((p - (sum(pnls) / n)) ** 2 for p in pnls) / (n - 1)
    std = math.sqrt(var)
    if std == 0.0:
        return 0.0
    return round(mean / std, 4)


def _sortino(pnls: list[float], risk_free: float = 0.0) -> float:
    n = len(pnls)
    if n < 2:
        return 0.0
    mean = sum(pnls) / n - risk_free
    downside = [p for p in pnls if p < 0]
    if not downside:
        return float("inf")
    down_var = sum(p ** 2 for p in downside) / len(downside)
    down_std = math.sqrt(down_var)
    if down_std == 0.0:
        return 0.0
    return round(mean / down_std, 4)
