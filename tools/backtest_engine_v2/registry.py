"""ExperimentRegistry — persistent record of completed backtest runs."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.backtest_engine_v2.metrics import TradeMetrics


@dataclass
class ExperimentRecord:
    experiment_id: str
    policy_name: str
    run_at: str
    data_source: str
    total_rows: int
    accepted: int
    rejected: int
    metrics: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ExperimentRegistry:
    """Append-only JSONL registry of completed experiment runs.

    Each run is stored as one JSON line keyed by experiment_id.
    """

    def __init__(self, registry_path: Path) -> None:
        self.registry_path = registry_path

    def record(
        self,
        *,
        policy_name: str,
        data_source: str,
        total_rows: int,
        accepted: int,
        rejected: int,
        metrics: TradeMetrics,
        tags: list[str] | None = None,
        notes: str = "",
    ) -> ExperimentRecord:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        exp_id = f"exp_{policy_name[:20]}_{ts}"
        record = ExperimentRecord(
            experiment_id=exp_id,
            policy_name=policy_name,
            run_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            data_source=data_source,
            total_rows=total_rows,
            accepted=accepted,
            rejected=rejected,
            metrics=_metrics_to_dict(metrics),
            tags=tags or [],
            notes=notes,
        )
        self._append(record)
        return record

    def _append(self, record: ExperimentRecord) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with self.registry_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.to_dict()) + "\n")

    def load_all(self) -> list[ExperimentRecord]:
        if not self.registry_path.is_file():
            return []
        records: list[ExperimentRecord] = []
        with self.registry_path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    records.append(ExperimentRecord.from_dict(obj))
                except (json.JSONDecodeError, TypeError):
                    continue
        return records

    def filter(self, *, policy_name: str | None = None, tag: str | None = None) -> list[ExperimentRecord]:
        records = self.load_all()
        if policy_name:
            records = [r for r in records if r.policy_name == policy_name]
        if tag:
            records = [r for r in records if tag in r.tags]
        return records


def _metrics_to_dict(m: TradeMetrics) -> dict[str, Any]:
    return {
        "total_pnl": m.total_pnl,
        "win_rate": m.win_rate,
        "sharpe": m.sharpe,
        "sortino": m.sortino,
        "profit_factor": m.profit_factor,
        "expectancy": m.expectancy,
        "max_drawdown_pct": m.max_drawdown_pct,
        "total_return_pct": m.total_return_pct,
        "skipped_ev_total": m.skipped_ev_total,
        "capital_utilization": m.capital_utilization,
        "accepted_trades": m.accepted_trades,
        "rejected_trades": m.rejected_trades,
        "win_count": m.win_count,
        "loss_count": m.loss_count,
    }
