"""ComparisonEngine — diff and rank multiple policy replay results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tools.backtest_engine_v2.scenario import ScenarioResult
from tools.backtest_engine_v2.metrics import TradeMetrics


@dataclass
class PolicySummary:
    policy_name: str
    accepted: int
    rejected: int
    win_rate: float
    total_pnl: float
    sharpe: float
    sortino: float
    profit_factor: float
    expectancy: float
    max_drawdown_pct: float
    total_return_pct: float
    skipped_ev_total: float
    capital_utilization: float
    rank: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_name": self.policy_name,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "win_rate": round(self.win_rate, 4),
            "total_pnl": round(self.total_pnl, 4),
            "sharpe": round(self.sharpe, 4),
            "sortino": round(self.sortino, 4),
            "profit_factor": round(self.profit_factor, 4),
            "expectancy": round(self.expectancy, 6),
            "max_drawdown_pct": round(self.max_drawdown_pct, 4),
            "total_return_pct": round(self.total_return_pct, 4),
            "skipped_ev_total": round(self.skipped_ev_total, 6),
            "capital_utilization": round(self.capital_utilization, 4),
            "rank": self.rank,
        }


@dataclass
class ComparisonReport:
    summaries: list[PolicySummary] = field(default_factory=list)
    best_sharpe: PolicySummary | None = None
    best_pnl: PolicySummary | None = None
    best_win_rate: PolicySummary | None = None
    lowest_drawdown: PolicySummary | None = None
    baseline_name: str = ""
    baseline: PolicySummary | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "summaries": [s.to_dict() for s in self.summaries],
            "best_sharpe": self.best_sharpe.to_dict() if self.best_sharpe else None,
            "best_pnl": self.best_pnl.to_dict() if self.best_pnl else None,
            "best_win_rate": self.best_win_rate.to_dict() if self.best_win_rate else None,
            "lowest_drawdown": self.lowest_drawdown.to_dict() if self.lowest_drawdown else None,
            "baseline": self.baseline.to_dict() if self.baseline else None,
        }


class ComparisonEngine:
    """Compare multiple scenario results and surface the best policies."""

    def compare(
        self,
        results: list[ScenarioResult],
        *,
        baseline_name: str = "",
    ) -> ComparisonReport:
        summaries: list[PolicySummary] = []
        for r in results:
            m = r.replay.metrics
            s = PolicySummary(
                policy_name=r.policy_name,
                accepted=m.accepted_trades,
                rejected=m.rejected_trades,
                win_rate=m.win_rate,
                total_pnl=m.total_pnl,
                sharpe=m.sharpe,
                sortino=m.sortino,
                profit_factor=m.profit_factor,
                expectancy=m.expectancy,
                max_drawdown_pct=m.max_drawdown_pct,
                total_return_pct=m.total_return_pct,
                skipped_ev_total=m.skipped_ev_total,
                capital_utilization=m.capital_utilization,
                rank=r.rank,
            )
            summaries.append(s)

        if not summaries:
            return ComparisonReport()

        report = ComparisonReport(summaries=summaries, baseline_name=baseline_name)

        valid = [s for s in summaries if s.accepted > 0]
        if valid:
            report.best_sharpe = max(valid, key=lambda s: s.sharpe)
            report.best_pnl = max(valid, key=lambda s: s.total_pnl)
            report.best_win_rate = max(valid, key=lambda s: s.win_rate)
            report.lowest_drawdown = min(valid, key=lambda s: s.max_drawdown_pct)

        if baseline_name:
            report.baseline = next(
                (s for s in summaries if s.policy_name == baseline_name), None
            )

        return report

    def diff(
        self,
        a: PolicySummary,
        b: PolicySummary,
    ) -> dict[str, Any]:
        """Return per-metric delta (b - a) for two policies."""
        numeric_fields = [
            "accepted", "rejected", "win_rate", "total_pnl", "sharpe", "sortino",
            "profit_factor", "expectancy", "max_drawdown_pct", "total_return_pct",
            "skipped_ev_total", "capital_utilization",
        ]
        result: dict[str, Any] = {
            "policy_a": a.policy_name,
            "policy_b": b.policy_name,
        }
        for f in numeric_fields:
            va = getattr(a, f, 0.0)
            vb = getattr(b, f, 0.0)
            try:
                result[f"delta_{f}"] = round(float(vb) - float(va), 6)
            except (TypeError, ValueError):
                result[f"delta_{f}"] = None
        return result
