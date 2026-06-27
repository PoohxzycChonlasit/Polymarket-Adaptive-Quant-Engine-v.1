"""Backtest Engine V2 — offline replay over Canonical Context data.

Lives entirely in tools/. Never modifies runtime behavior.
"""
from __future__ import annotations

from tools.backtest_engine_v2.engine import ReplayEngine
from tools.backtest_engine_v2.policy import PolicyConfig, PolicyEngine, PolicyRegistry
from tools.backtest_engine_v2.equity import EquitySimulator
from tools.backtest_engine_v2.metrics import MetricsEngine, TradeMetrics
from tools.backtest_engine_v2.scenario import ScenarioRunner, ScenarioResult
from tools.backtest_engine_v2.comparison import ComparisonEngine, ComparisonReport
from tools.backtest_engine_v2.registry import ExperimentRegistry, ExperimentRecord
from tools.backtest_engine_v2.exporter import RecommendationExporter

__all__ = [
    "ReplayEngine",
    "PolicyConfig",
    "PolicyEngine",
    "PolicyRegistry",
    "EquitySimulator",
    "MetricsEngine",
    "TradeMetrics",
    "ScenarioRunner",
    "ScenarioResult",
    "ComparisonEngine",
    "ComparisonReport",
    "ExperimentRegistry",
    "ExperimentRecord",
    "RecommendationExporter",
]
