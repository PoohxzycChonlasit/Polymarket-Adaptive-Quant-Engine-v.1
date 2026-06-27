"""ReplayEngine — loads canonical context JSONL and replays against a policy."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tools.backtest_engine_v2.policy import PolicyConfig, PolicyEngine
from tools.backtest_engine_v2.equity import EquitySimulator, EquityState
from tools.backtest_engine_v2.metrics import MetricsEngine, TradeMetrics


@dataclass
class ReplayResult:
    policy_name: str
    total_rows: int
    accepted: list[dict[str, Any]]
    rejected: list[dict[str, Any]]
    reject_reasons: list[tuple[dict[str, Any], str]]
    equity_state: EquityState
    metrics: TradeMetrics


class ReplayEngine:
    """Load canonical context rows and replay under a given policy.

    This is the primary entry point. It is deterministic:
    given the same rows and policy, output is identical.
    """

    def __init__(self) -> None:
        self._equity = EquitySimulator()
        self._metrics = MetricsEngine()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_jsonl(self, path: Path) -> list[dict[str, Any]]:
        """Load canonical context rows from a JSONL file."""
        rows: list[dict[str, Any]] = []
        if not path.is_file():
            return rows
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        rows.append(obj)
                except json.JSONDecodeError:
                    continue
        return rows

    def load_directory(self, directory: Path, pattern: str = "canonical_trade_context_*.jsonl") -> list[dict[str, Any]]:
        """Load all canonical context JSONL files from a directory."""
        rows: list[dict[str, Any]] = []
        for path in sorted(directory.glob(pattern)):
            rows.extend(self.load_jsonl(path))
        return rows

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------

    def replay(
        self,
        rows: list[dict[str, Any]],
        policy: PolicyConfig,
        *,
        starting_equity: float | None = None,
        quality_filter: str | None = None,
    ) -> ReplayResult:
        """Replay rows against policy and compute metrics.

        Args:
            rows: canonical context rows (order-independent for filter; equity sorted by time)
            policy: filter criteria
            starting_equity: override starting equity (default: from first accepted row)
            quality_filter: if set, only replay rows with data_quality_grade == this value
        """
        if quality_filter:
            rows = [r for r in rows if r.get("data_quality_grade") == quality_filter]

        engine = PolicyEngine(policy)
        accepted: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        reject_reasons: list[tuple[dict[str, Any], str]] = []

        for row in rows:
            ok, reason = engine.evaluate(row)
            if ok:
                accepted.append(row)
            else:
                rejected.append(row)
                reject_reasons.append((row, reason))

        equity_state = self._equity.simulate(accepted, starting_equity=starting_equity)
        metrics = self._metrics.compute(accepted, rejected, equity_state)

        return ReplayResult(
            policy_name=policy.name,
            total_rows=len(rows),
            accepted=accepted,
            rejected=rejected,
            reject_reasons=reject_reasons,
            equity_state=equity_state,
            metrics=metrics,
        )
