"""ScenarioRunner — run 100+ policy configurations in isolation."""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

from tools.backtest_engine_v2.engine import ReplayEngine, ReplayResult
from tools.backtest_engine_v2.policy import PolicyConfig
from tools.backtest_engine_v2.metrics import TradeMetrics


@dataclass
class ScenarioResult:
    policy_name: str
    replay: ReplayResult
    rank: int = 0


class ScenarioRunner:
    """Run multiple PolicyConfigs over the same canonical rows.

    Each config runs with a completely fresh ReplayEngine instance so state
    cannot leak between scenarios. Results are deterministic.
    """

    def run(
        self,
        rows: list[dict[str, Any]],
        policies: list[PolicyConfig],
        *,
        quality_filter: str | None = None,
        starting_equity: float | None = None,
    ) -> list[ScenarioResult]:
        results: list[ScenarioResult] = []
        for policy in policies:
            engine = ReplayEngine()
            replay = engine.replay(
                rows,
                policy,
                quality_filter=quality_filter,
                starting_equity=starting_equity,
            )
            results.append(ScenarioResult(policy_name=policy.name, replay=replay))
        return results

    @staticmethod
    def build_ev_grid(
        ev_thresholds: list[float] | None = None,
        prob_thresholds: list[float] | None = None,
        seconds_remaining: list[float] | None = None,
        risk_modes: list[list[str]] | None = None,
        lifecycle_phases: list[list[str]] | None = None,
    ) -> list[PolicyConfig]:
        """Generate a Cartesian product grid of policy configs.

        Default produces >100 combinations covering EV, probability, time, and regime.
        """
        if ev_thresholds is None:
            ev_thresholds = [0.0, 0.02, 0.05, 0.08, 0.10, 0.15, 0.20]
        if prob_thresholds is None:
            prob_thresholds = [0.0, 0.55, 0.60, 0.65, 0.70]
        if seconds_remaining is None:
            seconds_remaining = [0.0, 30.0, 60.0, 120.0]
        if risk_modes is None:
            risk_modes = [[], ["NORMAL"], ["MICRO_RECOVERY", "NORMAL"]]
        if lifecycle_phases is None:
            lifecycle_phases = [[], ["OPENING_SCAN"], ["OPENING_SCAN", "ACTIVE_INVENTORY_TRADING"]]

        configs: list[PolicyConfig] = []
        for ev, prob, secs, modes, phases in itertools.product(
            ev_thresholds, prob_thresholds, seconds_remaining, risk_modes, lifecycle_phases
        ):
            mode_tag = "_".join(modes) if modes else "all"
            phase_tag = "_".join(p[:4] for p in phases) if phases else "all"
            name = f"ev{ev:.2f}_p{prob:.2f}_s{int(secs)}_m{mode_tag[:8]}_ph{phase_tag[:8]}"
            configs.append(PolicyConfig(
                name=name,
                min_ev=ev,
                min_probability=prob,
                min_seconds_remaining=secs,
                risk_mode_allowlist=list(modes),
                lifecycle_phase_allowlist=list(phases),
            ))
        return configs

    @staticmethod
    def build_custom_grid(param_overrides: list[dict[str, Any]]) -> list[PolicyConfig]:
        """Build configs from explicit list of parameter dicts.

        Each dict must contain at least "name" and overrides for desired fields.
        """
        configs: list[PolicyConfig] = []
        for i, override in enumerate(param_overrides):
            name = str(override.get("name") or f"custom_{i:04d}")
            kwargs = {k: v for k, v in override.items() if k != "name"}
            configs.append(PolicyConfig(name=name, **kwargs))
        return configs

    def rank_by(
        self,
        results: list[ScenarioResult],
        key: str = "sharpe",
        ascending: bool = False,
    ) -> list[ScenarioResult]:
        """Return results ranked by a metric field from TradeMetrics."""
        def _key(r: ScenarioResult) -> float:
            val = getattr(r.replay.metrics, key, None)
            if val is None or (isinstance(val, float) and val != val):
                return float("-inf")
            f = float(val)
            return f if not ascending else -f

        ranked = sorted(results, key=_key, reverse=True)
        for i, r in enumerate(ranked):
            r.rank = i + 1
        return ranked
