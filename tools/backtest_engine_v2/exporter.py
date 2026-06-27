"""RecommendationExporter — produce structured recommendation output."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.backtest_engine_v2.comparison import ComparisonReport, PolicySummary
from tools.backtest_engine_v2.scenario import ScenarioResult


@dataclass
class Recommendation:
    category: str
    policy_name: str
    rationale: str
    metrics: dict[str, Any]
    confidence: str


class RecommendationExporter:
    """Generate human-readable recommendations from comparison results.

    Output is structured JSON suitable for operator review.
    Does not touch runtime configuration.
    """

    def generate(
        self,
        report: ComparisonReport,
        *,
        min_accepted_trades: int = 3,
    ) -> list[Recommendation]:
        recs: list[Recommendation] = []

        def _summary_metrics(s: PolicySummary) -> dict[str, Any]:
            return {
                "accepted_trades": s.accepted,
                "win_rate": round(s.win_rate, 4),
                "total_pnl": round(s.total_pnl, 4),
                "sharpe": round(s.sharpe, 4),
                "profit_factor": round(s.profit_factor, 4),
                "max_drawdown_pct": round(s.max_drawdown_pct, 4),
                "capital_utilization": round(s.capital_utilization, 4),
                "skipped_ev_total": round(s.skipped_ev_total, 6),
            }

        if report.best_sharpe and report.best_sharpe.accepted >= min_accepted_trades:
            recs.append(Recommendation(
                category="BEST_SHARPE",
                policy_name=report.best_sharpe.policy_name,
                rationale=(
                    f"Highest risk-adjusted return: Sharpe={report.best_sharpe.sharpe:.4f}. "
                    f"Accepted {report.best_sharpe.accepted} trades with "
                    f"win_rate={report.best_sharpe.win_rate:.1%}."
                ),
                metrics=_summary_metrics(report.best_sharpe),
                confidence="HIGH" if report.best_sharpe.accepted >= 10 else "MEDIUM",
            ))

        if report.best_pnl and report.best_pnl.accepted >= min_accepted_trades:
            recs.append(Recommendation(
                category="BEST_PNL",
                policy_name=report.best_pnl.policy_name,
                rationale=(
                    f"Highest absolute PnL: {report.best_pnl.total_pnl:.4f} USDC. "
                    f"Profit factor={report.best_pnl.profit_factor:.4f}."
                ),
                metrics=_summary_metrics(report.best_pnl),
                confidence="HIGH" if report.best_pnl.accepted >= 10 else "MEDIUM",
            ))

        if report.lowest_drawdown and report.lowest_drawdown.accepted >= min_accepted_trades:
            recs.append(Recommendation(
                category="LOWEST_DRAWDOWN",
                policy_name=report.lowest_drawdown.policy_name,
                rationale=(
                    f"Lowest max drawdown: {report.lowest_drawdown.max_drawdown_pct:.1%}. "
                    f"Accepted {report.lowest_drawdown.accepted} trades."
                ),
                metrics=_summary_metrics(report.lowest_drawdown),
                confidence="HIGH" if report.lowest_drawdown.accepted >= 10 else "MEDIUM",
            ))

        if report.best_win_rate and report.best_win_rate.accepted >= min_accepted_trades:
            recs.append(Recommendation(
                category="BEST_WIN_RATE",
                policy_name=report.best_win_rate.policy_name,
                rationale=(
                    f"Highest win rate: {report.best_win_rate.win_rate:.1%}. "
                    f"Accepted {report.best_win_rate.accepted} trades."
                ),
                metrics=_summary_metrics(report.best_win_rate),
                confidence="MEDIUM",
            ))

        return recs

    def export_json(self, recs: list[Recommendation], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "category": r.category,
                "policy_name": r.policy_name,
                "rationale": r.rationale,
                "metrics": r.metrics,
                "confidence": r.confidence,
            }
            for r in recs
        ]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def export_comparison_csv(self, report: ComparisonReport, path: Path) -> None:
        """Write comparison table as CSV for spreadsheet analysis."""
        path.parent.mkdir(parents=True, exist_ok=True)
        if not report.summaries:
            return
        headers = list(report.summaries[0].to_dict().keys())
        lines = [",".join(str(h) for h in headers)]
        for s in report.summaries:
            row = s.to_dict()
            lines.append(",".join(str(row.get(h, "")) for h in headers))
        path.write_text("\n".join(lines), encoding="utf-8")
