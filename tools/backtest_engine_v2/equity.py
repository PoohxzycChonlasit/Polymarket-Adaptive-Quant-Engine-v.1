"""EquitySimulator — tracks equity curve and drawdown for accepted trades."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EquityPoint:
    trade_id: str
    submitted_at: str
    equity: float
    pnl: float
    drawdown_pct: float
    high_watermark: float


@dataclass
class EquityState:
    points: list[EquityPoint] = field(default_factory=list)
    starting_equity: float = 0.0
    ending_equity: float = 0.0
    high_watermark: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_usdc: float = 0.0


class EquitySimulator:
    """Replays accepted trades in chronological order and builds equity curve.

    Starting equity is inferred from the bankroll of the first accepted trade.
    Each trade's realized_pnl is applied sequentially.
    """

    def simulate(
        self,
        accepted_rows: list[dict[str, Any]],
        *,
        starting_equity: float | None = None,
    ) -> EquityState:
        state = EquityState()
        if not accepted_rows:
            return state

        sorted_rows = sorted(
            accepted_rows,
            key=lambda r: str(r.get("submitted_at") or r.get("exit_timestamp") or ""),
        )

        first = sorted_rows[0]
        if starting_equity is None:
            starting_equity = float(first.get("bankroll") or first.get("equity") or 0.0)

        equity = starting_equity
        hwm = equity
        max_dd_pct = 0.0
        max_dd_usdc = 0.0

        state.starting_equity = starting_equity
        state.high_watermark = hwm

        for row in sorted_rows:
            pnl = float(row.get("realized_pnl") or 0.0)
            equity += pnl
            if equity > hwm:
                hwm = equity
            dd_usdc = hwm - equity
            dd_pct = dd_usdc / hwm if hwm > 0 else 0.0
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
                max_dd_usdc = dd_usdc

            pt = EquityPoint(
                trade_id=str(row.get("trade_id") or ""),
                submitted_at=str(row.get("submitted_at") or ""),
                equity=round(equity, 6),
                pnl=round(pnl, 6),
                drawdown_pct=round(dd_pct, 6),
                high_watermark=round(hwm, 6),
            )
            state.points.append(pt)

        state.ending_equity = round(equity, 6)
        state.high_watermark = round(hwm, 6)
        state.max_drawdown_pct = round(max_dd_pct, 6)
        state.max_drawdown_usdc = round(max_dd_usdc, 6)
        return state
