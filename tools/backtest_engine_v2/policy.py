"""PolicyEngine and PolicyRegistry.

A Policy is a set of filter criteria applied to each canonical context row
to decide whether a trade would be accepted or rejected.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class PolicyConfig:
    """Filter criteria that determine which canonical trades are accepted.

    None / float("inf") / empty list means "no filter on this dimension".
    """
    name: str = "default"

    # Signal quality
    min_ev: float = 0.0
    min_ev_after_spread: float = 0.0
    min_probability: float = 0.0
    min_decision_score: float = 0.0

    # Market conditions
    min_seconds_remaining: float = 0.0
    max_spread: float = 1.0
    min_liquidity_notional: float = 0.0

    # Position sizing
    max_position_notional: float = float("inf")
    min_size_sharp: float = 0.0
    max_size_sharp: float = float("inf")

    # Risk budget
    min_risk_budget: float = 0.0

    # Inventory / regime
    inventory_state_allowlist: list[str] = field(default_factory=list)
    lifecycle_phase_allowlist: list[str] = field(default_factory=list)
    risk_mode_allowlist: list[str] = field(default_factory=list)
    market_state_allowlist: list[str] = field(default_factory=list)

    # Data quality
    data_quality_grades: list[str] = field(default_factory=list)
    min_join_confidence: str = ""

    # Time filters
    max_hold_seconds: float = float("inf")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class PolicyEngine:
    """Applies a PolicyConfig to a canonical trade row and returns accept/reject."""

    def __init__(self, config: PolicyConfig) -> None:
        self.config = config

    def evaluate(self, row: dict[str, Any]) -> tuple[bool, str]:
        """Return (accepted, reason).

        reason is empty string on accept, a short code on reject.
        """
        c = self.config

        ev = _float(row, "ev", 0.0)
        if ev < c.min_ev:
            return False, f"ev={ev:.4f}<min_ev={c.min_ev:.4f}"

        ev_spread = _float(row, "ev_after_spread", ev)
        if ev_spread < c.min_ev_after_spread:
            return False, f"ev_after_spread={ev_spread:.4f}<min={c.min_ev_after_spread:.4f}"

        prob = _float(row, "probability", 0.0)
        if prob < c.min_probability:
            return False, f"probability={prob:.4f}<min={c.min_probability:.4f}"

        score = _float(row, "decision_score", 0.0)
        if score < c.min_decision_score:
            return False, f"decision_score={score:.4f}<min={c.min_decision_score:.4f}"

        secs = _float(row, "seconds_remaining", float("inf"))
        if secs < c.min_seconds_remaining:
            return False, f"seconds_remaining={secs:.1f}<min={c.min_seconds_remaining:.1f}"

        notional = _float(row, "intended_notional", 0.0)
        if notional > c.max_position_notional:
            return False, f"notional={notional:.4f}>max={c.max_position_notional:.4f}"

        risk_budget = _float(row, "risk_budget", float("inf"))
        if risk_budget < c.min_risk_budget:
            return False, f"risk_budget={risk_budget:.4f}<min={c.min_risk_budget:.4f}"

        if c.inventory_state_allowlist:
            inv = str(row.get("inventory_state") or "")
            if inv not in c.inventory_state_allowlist:
                return False, f"inventory_state={inv!r} not in allowlist"

        if c.lifecycle_phase_allowlist:
            phase = str(row.get("lifecycle_phase") or "")
            if phase not in c.lifecycle_phase_allowlist:
                return False, f"lifecycle_phase={phase!r} not in allowlist"

        if c.risk_mode_allowlist:
            mode = str(row.get("risk_mode") or "")
            if mode not in c.risk_mode_allowlist:
                return False, f"risk_mode={mode!r} not in allowlist"

        if c.market_state_allowlist:
            mstate = str(row.get("market_state") or "")
            if mstate not in c.market_state_allowlist:
                return False, f"market_state={mstate!r} not in allowlist"

        if c.data_quality_grades:
            grade = str(row.get("data_quality_grade") or "")
            if grade not in c.data_quality_grades:
                return False, f"data_quality_grade={grade!r} not in allowlist"

        if c.min_join_confidence:
            conf = str(row.get("join_confidence") or "")
            _order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
            if _order.get(conf, -1) < _order.get(c.min_join_confidence, 0):
                return False, f"join_confidence={conf!r}<min={c.min_join_confidence!r}"

        return True, ""

    def evaluate_batch(
        self, rows: list[dict[str, Any]]
    ) -> list[tuple[dict[str, Any], bool, str]]:
        """Return list of (row, accepted, reason) for all rows."""
        return [(row, *self.evaluate(row)) for row in rows]


def _float(row: dict[str, Any], key: str, default: float) -> float:
    val = row.get(key)
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


class PolicyRegistry:
    """In-memory registry of named PolicyConfig instances."""

    def __init__(self) -> None:
        self._policies: dict[str, PolicyConfig] = {}

    def register(self, config: PolicyConfig) -> None:
        self._policies[config.name] = config

    def get(self, name: str) -> PolicyConfig | None:
        return self._policies.get(name)

    def list_names(self) -> list[str]:
        return list(self._policies.keys())

    def all(self) -> list[PolicyConfig]:
        return list(self._policies.values())

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {name: p.to_dict() for name, p in self._policies.items()}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "PolicyRegistry":
        registry = cls()
        if not path.exists():
            return registry
        data = json.loads(path.read_text(encoding="utf-8"))
        for name, pdict in data.items():
            pdict["name"] = name
            registry.register(PolicyConfig.from_dict(pdict))
        return registry
