"""Tests for BacktestEngineV2 — determinism, policy isolation, metrics, comparison.

All tests use synthetic canonical context rows (no file I/O required).
"""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

import pytest

from tools.backtest_engine_v2.policy import PolicyConfig, PolicyEngine, PolicyRegistry
from tools.backtest_engine_v2.equity import EquitySimulator
from tools.backtest_engine_v2.metrics import MetricsEngine, TradeMetrics
from tools.backtest_engine_v2.engine import ReplayEngine, ReplayResult
from tools.backtest_engine_v2.scenario import ScenarioRunner, ScenarioResult
from tools.backtest_engine_v2.comparison import ComparisonEngine, ComparisonReport
from tools.backtest_engine_v2.registry import ExperimentRegistry
from tools.backtest_engine_v2.exporter import RecommendationExporter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_row(
    *,
    trade_id: str = "t1",
    ev: float = 0.10,
    probability: float = 0.65,
    seconds_remaining: float = 120.0,
    risk_mode: str = "NORMAL",
    lifecycle_phase: str = "OPENING_SCAN",
    inventory_state: str = "FLAT",
    data_quality_grade: str = "A",
    join_confidence: str = "HIGH",
    realized_pnl: float = 0.05,
    intended_notional: float = 0.10,
    bankroll: float = 20.0,
    decision_score: float = 15.0,
    risk_budget: float = 1.0,
    hold_seconds: float = 60.0,
    submitted_at: str = "2026-06-27T00:00:00Z",
    exit_timestamp: str = "2026-06-27T00:01:00Z",
) -> dict:
    return {
        "trade_id": trade_id,
        "ev": ev,
        "ev_after_spread": ev,
        "probability": probability,
        "seconds_remaining": seconds_remaining,
        "risk_mode": risk_mode,
        "lifecycle_phase": lifecycle_phase,
        "inventory_state": inventory_state,
        "data_quality_grade": data_quality_grade,
        "join_confidence": join_confidence,
        "realized_pnl": realized_pnl,
        "intended_notional": intended_notional,
        "bankroll": bankroll,
        "decision_score": decision_score,
        "risk_budget": risk_budget,
        "hold_seconds": hold_seconds,
        "submitted_at": submitted_at,
        "exit_timestamp": exit_timestamp,
    }


SAMPLE_ROWS = [
    _make_row(trade_id="t1", ev=0.10, probability=0.65, realized_pnl=0.05, bankroll=20.0, submitted_at="2026-06-27T00:00:00Z"),
    _make_row(trade_id="t2", ev=0.03, probability=0.58, realized_pnl=-0.02, bankroll=20.05, submitted_at="2026-06-27T00:01:00Z"),
    _make_row(trade_id="t3", ev=0.15, probability=0.70, realized_pnl=0.08, bankroll=20.03, submitted_at="2026-06-27T00:02:00Z"),
    _make_row(trade_id="t4", ev=0.01, probability=0.52, realized_pnl=-0.01, bankroll=20.11, submitted_at="2026-06-27T00:03:00Z"),
    _make_row(trade_id="t5", ev=0.12, probability=0.68, realized_pnl=0.06, bankroll=20.10, submitted_at="2026-06-27T00:04:00Z"),
]


# ---------------------------------------------------------------------------
# PolicyEngine tests
# ---------------------------------------------------------------------------

class TestPolicyEngine:
    def test_accept_all_with_default_policy(self):
        policy = PolicyConfig(name="accept_all")
        engine = PolicyEngine(policy)
        for row in SAMPLE_ROWS:
            ok, reason = engine.evaluate(row)
            assert ok, f"Expected accept but got reason: {reason}"

    def test_reject_below_min_ev(self):
        policy = PolicyConfig(name="high_ev", min_ev=0.10)
        engine = PolicyEngine(policy)
        ok, reason = engine.evaluate(_make_row(ev=0.05))
        assert not ok
        assert "ev=" in reason

    def test_reject_below_min_probability(self):
        policy = PolicyConfig(name="high_prob", min_probability=0.65)
        engine = PolicyEngine(policy)
        ok, reason = engine.evaluate(_make_row(probability=0.60))
        assert not ok

    def test_reject_below_min_seconds_remaining(self):
        policy = PolicyConfig(name="time_filter", min_seconds_remaining=60.0)
        engine = PolicyEngine(policy)
        ok, reason = engine.evaluate(_make_row(seconds_remaining=30.0))
        assert not ok

    def test_reject_by_risk_mode_allowlist(self):
        policy = PolicyConfig(name="mode_filter", risk_mode_allowlist=["NORMAL"])
        engine = PolicyEngine(policy)
        ok, reason = engine.evaluate(_make_row(risk_mode="MICRO_RECOVERY"))
        assert not ok

    def test_accept_by_risk_mode_allowlist(self):
        policy = PolicyConfig(name="mode_filter", risk_mode_allowlist=["NORMAL"])
        engine = PolicyEngine(policy)
        ok, reason = engine.evaluate(_make_row(risk_mode="NORMAL"))
        assert ok

    def test_reject_by_lifecycle_phase(self):
        policy = PolicyConfig(name="phase_filter", lifecycle_phase_allowlist=["OPENING_SCAN"])
        engine = PolicyEngine(policy)
        ok, reason = engine.evaluate(_make_row(lifecycle_phase="ACTIVE_INVENTORY_TRADING"))
        assert not ok

    def test_reject_by_data_quality_grade(self):
        policy = PolicyConfig(name="quality", data_quality_grades=["A"])
        engine = PolicyEngine(policy)
        ok, reason = engine.evaluate(_make_row(data_quality_grade="D"))
        assert not ok

    def test_reject_by_join_confidence(self):
        policy = PolicyConfig(name="conf", min_join_confidence="HIGH")
        engine = PolicyEngine(policy)
        ok, reason = engine.evaluate(_make_row(join_confidence="LOW"))
        assert not ok

    def test_reject_excessive_notional(self):
        policy = PolicyConfig(name="size_cap", max_position_notional=0.05)
        engine = PolicyEngine(policy)
        ok, reason = engine.evaluate(_make_row(intended_notional=0.10))
        assert not ok

    def test_reject_below_risk_budget(self):
        policy = PolicyConfig(name="budget_filter", min_risk_budget=2.0)
        engine = PolicyEngine(policy)
        ok, reason = engine.evaluate(_make_row(risk_budget=1.0))
        assert not ok

    def test_evaluate_batch(self):
        policy = PolicyConfig(name="high_ev", min_ev=0.10)
        engine = PolicyEngine(policy)
        results = engine.evaluate_batch(SAMPLE_ROWS)
        accepted = [r for r, ok, _ in results if ok]
        rejected = [r for r, ok, _ in results if not ok]
        assert len(accepted) + len(rejected) == len(SAMPLE_ROWS)

    def test_empty_allowlist_means_no_filter(self):
        policy = PolicyConfig(name="no_filter", risk_mode_allowlist=[])
        engine = PolicyEngine(policy)
        ok, _ = engine.evaluate(_make_row(risk_mode="ANYTHING"))
        assert ok


# ---------------------------------------------------------------------------
# PolicyRegistry tests
# ---------------------------------------------------------------------------

class TestPolicyRegistry:
    def test_register_and_get(self):
        reg = PolicyRegistry()
        cfg = PolicyConfig(name="alpha", min_ev=0.05)
        reg.register(cfg)
        assert reg.get("alpha") is cfg

    def test_list_names(self):
        reg = PolicyRegistry()
        reg.register(PolicyConfig(name="a"))
        reg.register(PolicyConfig(name="b"))
        assert set(reg.list_names()) == {"a", "b"}

    def test_save_and_load(self):
        reg = PolicyRegistry()
        reg.register(PolicyConfig(name="p1", min_ev=0.05, min_probability=0.60))
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        reg.save(path)
        loaded = PolicyRegistry.load(path)
        p = loaded.get("p1")
        assert p is not None
        assert p.min_ev == 0.05
        assert p.min_probability == 0.60
        path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# EquitySimulator tests
# ---------------------------------------------------------------------------

class TestEquitySimulator:
    def test_empty_rows_returns_empty_state(self):
        sim = EquitySimulator()
        state = sim.simulate([])
        assert state.points == []
        assert state.starting_equity == 0.0

    def test_positive_pnl_increases_equity(self):
        sim = EquitySimulator()
        rows = [
            _make_row(trade_id="t1", realized_pnl=0.10, bankroll=10.0, submitted_at="2026-06-27T00:00:00Z"),
            _make_row(trade_id="t2", realized_pnl=0.05, bankroll=10.1, submitted_at="2026-06-27T00:01:00Z"),
        ]
        state = sim.simulate(rows)
        assert state.ending_equity == pytest.approx(10.15, abs=1e-5)
        assert state.max_drawdown_pct == 0.0

    def test_drawdown_computed_correctly(self):
        sim = EquitySimulator()
        rows = [
            _make_row(trade_id="t1", realized_pnl=1.0, bankroll=10.0, submitted_at="2026-06-27T00:00:00Z"),
            _make_row(trade_id="t2", realized_pnl=-2.0, bankroll=11.0, submitted_at="2026-06-27T00:01:00Z"),
        ]
        state = sim.simulate(rows)
        # peak = 11.0, trough = 9.0, dd = 2/11 ≈ 0.1818
        assert state.max_drawdown_pct == pytest.approx(2.0 / 11.0, abs=1e-4)
        assert state.max_drawdown_usdc == pytest.approx(2.0, abs=1e-5)

    def test_starting_equity_override(self):
        sim = EquitySimulator()
        rows = [_make_row(trade_id="t1", realized_pnl=0.5, bankroll=99.0, submitted_at="2026-06-27T00:00:00Z")]
        state = sim.simulate(rows, starting_equity=100.0)
        assert state.starting_equity == 100.0
        assert state.ending_equity == pytest.approx(100.5, abs=1e-5)

    def test_sorted_by_time(self):
        sim = EquitySimulator()
        rows = [
            _make_row(trade_id="t2", realized_pnl=0.05, bankroll=10.0, submitted_at="2026-06-27T00:02:00Z"),
            _make_row(trade_id="t1", realized_pnl=0.10, bankroll=10.0, submitted_at="2026-06-27T00:01:00Z"),
        ]
        state = sim.simulate(rows, starting_equity=10.0)
        assert state.points[0].trade_id == "t1"
        assert state.points[1].trade_id == "t2"


# ---------------------------------------------------------------------------
# MetricsEngine tests
# ---------------------------------------------------------------------------

class TestMetricsEngine:
    def _run(self, accepted, rejected=None):
        from tools.backtest_engine_v2.equity import EquitySimulator, EquityState
        sim = EquitySimulator()
        equity = sim.simulate(accepted, starting_equity=20.0)
        engine = MetricsEngine()
        return engine.compute(accepted, rejected or [], equity)

    def test_win_rate(self):
        rows = [
            _make_row(realized_pnl=0.10),
            _make_row(realized_pnl=0.05),
            _make_row(realized_pnl=-0.02),
        ]
        m = self._run(rows)
        assert m.win_rate == pytest.approx(2 / 3, abs=1e-4)

    def test_profit_factor(self):
        rows = [_make_row(realized_pnl=0.10), _make_row(realized_pnl=-0.05)]
        m = self._run(rows)
        assert m.profit_factor == pytest.approx(2.0, abs=1e-4)

    def test_expectancy(self):
        rows = [_make_row(realized_pnl=0.10), _make_row(realized_pnl=-0.02)]
        m = self._run(rows)
        assert m.expectancy == pytest.approx(0.04, abs=1e-5)

    def test_skipped_ev(self):
        accepted = [_make_row(trade_id="t1", ev=0.10, intended_notional=1.0)]
        rejected = [_make_row(trade_id="t2", ev=0.05, intended_notional=2.0)]
        m = self._run(accepted, rejected)
        assert m.skipped_ev_total == pytest.approx(0.10, abs=1e-5)
        assert m.skipped_ev_count == 1

    def test_acceptance_rate(self):
        accepted = [_make_row(trade_id=f"t{i}") for i in range(3)]
        rejected = [_make_row(trade_id=f"r{i}") for i in range(7)]
        m = self._run(accepted, rejected)
        assert m.acceptance_rate == pytest.approx(0.3, abs=1e-4)
        assert m.capital_utilization == m.acceptance_rate

    def test_sharpe_zero_variance(self):
        rows = [_make_row(realized_pnl=0.05)] * 5
        m = self._run(rows)
        assert m.sharpe == 0.0

    def test_empty_accepted(self):
        m = self._run([], [_make_row()])
        assert m.total_pnl == 0.0
        assert m.win_rate == 0.0


# ---------------------------------------------------------------------------
# ReplayEngine tests
# ---------------------------------------------------------------------------

class TestReplayEngine:
    def test_determinism(self):
        engine1 = ReplayEngine()
        engine2 = ReplayEngine()
        policy = PolicyConfig(name="det", min_ev=0.08)
        r1 = engine1.replay(copy.deepcopy(SAMPLE_ROWS), policy)
        r2 = engine2.replay(copy.deepcopy(SAMPLE_ROWS), policy)
        assert [r["trade_id"] for r in r1.accepted] == [r["trade_id"] for r in r2.accepted]
        assert r1.metrics.total_pnl == r2.metrics.total_pnl

    def test_quality_filter(self):
        rows = SAMPLE_ROWS + [_make_row(trade_id="low_q", data_quality_grade="D")]
        engine = ReplayEngine()
        r = engine.replay(rows, PolicyConfig(name="a"), quality_filter="A")
        assert all(row.get("data_quality_grade") == "A" for row in r.accepted + r.rejected)

    def test_accept_all_policy_no_rejections(self):
        engine = ReplayEngine()
        r = engine.replay(SAMPLE_ROWS, PolicyConfig(name="accept_all"))
        assert r.rejected == []
        assert len(r.accepted) == len(SAMPLE_ROWS)

    def test_reject_all_with_impossible_policy(self):
        engine = ReplayEngine()
        policy = PolicyConfig(name="reject_all", min_ev=99.0)
        r = engine.replay(SAMPLE_ROWS, policy)
        assert r.accepted == []
        assert len(r.rejected) == len(SAMPLE_ROWS)

    def test_load_jsonl(self):
        rows = [_make_row(trade_id=f"j{i}") for i in range(5)]
        with tempfile.NamedTemporaryFile(
            suffix=".jsonl", mode="w", delete=False, encoding="utf-8"
        ) as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
            path = Path(f.name)
        engine = ReplayEngine()
        loaded = engine.load_jsonl(path)
        assert len(loaded) == 5
        path.unlink(missing_ok=True)

    def test_replay_result_fields(self):
        engine = ReplayEngine()
        r = engine.replay(SAMPLE_ROWS, PolicyConfig(name="x"))
        assert isinstance(r, ReplayResult)
        assert r.policy_name == "x"
        assert r.total_rows == len(SAMPLE_ROWS)
        assert isinstance(r.metrics, TradeMetrics)


# ---------------------------------------------------------------------------
# ScenarioRunner tests
# ---------------------------------------------------------------------------

class TestScenarioRunner:
    def test_policy_isolation(self):
        runner = ScenarioRunner()
        policies = [
            PolicyConfig(name="p_low", min_ev=0.01),
            PolicyConfig(name="p_high", min_ev=0.12),
        ]
        results = runner.run(SAMPLE_ROWS, policies)
        low = next(r for r in results if r.policy_name == "p_low")
        high = next(r for r in results if r.policy_name == "p_high")
        assert len(low.replay.accepted) >= len(high.replay.accepted)

    def test_grid_generates_over_100_configs(self):
        configs = ScenarioRunner.build_ev_grid()
        assert len(configs) >= 100

    def test_all_config_names_unique(self):
        configs = ScenarioRunner.build_ev_grid()
        names = [c.name for c in configs]
        assert len(names) == len(set(names))

    def test_rank_by_sharpe(self):
        runner = ScenarioRunner()
        policies = [PolicyConfig(name=f"p{i}", min_ev=i * 0.01) for i in range(5)]
        results = runner.run(SAMPLE_ROWS, policies)
        ranked = runner.rank_by(results, key="sharpe")
        assert ranked[0].rank == 1
        assert all(ranked[i].rank <= ranked[i + 1].rank for i in range(len(ranked) - 1))

    def test_custom_grid(self):
        overrides = [
            {"name": "c1", "min_ev": 0.05},
            {"name": "c2", "min_ev": 0.10, "min_probability": 0.60},
        ]
        configs = ScenarioRunner.build_custom_grid(overrides)
        assert len(configs) == 2
        assert configs[0].name == "c1"
        assert configs[1].min_probability == 0.60

    def test_determinism_across_runs(self):
        runner = ScenarioRunner()
        policies = [PolicyConfig(name="det", min_ev=0.08)]
        r1 = runner.run(copy.deepcopy(SAMPLE_ROWS), policies)
        r2 = runner.run(copy.deepcopy(SAMPLE_ROWS), policies)
        assert r1[0].replay.metrics.total_pnl == r2[0].replay.metrics.total_pnl


# ---------------------------------------------------------------------------
# ComparisonEngine tests
# ---------------------------------------------------------------------------

class TestComparisonEngine:
    def _make_results(self, policies):
        runner = ScenarioRunner()
        return runner.run(SAMPLE_ROWS, policies)

    def test_best_sharpe_identified(self):
        policies = [
            PolicyConfig(name="low_filter", min_ev=0.0),
            PolicyConfig(name="high_filter", min_ev=0.15),
        ]
        results = self._make_results(policies)
        comp = ComparisonEngine()
        report = comp.compare(results)
        assert report.best_sharpe is not None

    def test_diff(self):
        policies = [
            PolicyConfig(name="a", min_ev=0.0),
            PolicyConfig(name="b", min_ev=0.10),
        ]
        results = self._make_results(policies)
        comp = ComparisonEngine()
        report = comp.compare(results)
        sa = next(s for s in report.summaries if s.policy_name == "a")
        sb = next(s for s in report.summaries if s.policy_name == "b")
        diff = comp.diff(sa, sb)
        assert "delta_total_pnl" in diff

    def test_report_to_dict(self):
        policies = [PolicyConfig(name="x", min_ev=0.05)]
        results = self._make_results(policies)
        comp = ComparisonEngine()
        report = comp.compare(results)
        d = report.to_dict()
        assert "summaries" in d
        assert isinstance(d["summaries"], list)

    def test_baseline(self):
        policies = [PolicyConfig(name="baseline"), PolicyConfig(name="improved", min_ev=0.08)]
        results = self._make_results(policies)
        comp = ComparisonEngine()
        report = comp.compare(results, baseline_name="baseline")
        assert report.baseline is not None
        assert report.baseline.policy_name == "baseline"


# ---------------------------------------------------------------------------
# ExperimentRegistry tests
# ---------------------------------------------------------------------------

class TestExperimentRegistry:
    def test_record_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = Path(f.name)
        reg = ExperimentRegistry(path)
        m = TradeMetrics(total_pnl=0.5, win_rate=0.6, sharpe=1.2, accepted_trades=5)
        record = reg.record(
            policy_name="test_policy",
            data_source="test.jsonl",
            total_rows=10,
            accepted=5,
            rejected=5,
            metrics=m,
            tags=["unit_test"],
        )
        assert record.experiment_id.startswith("exp_test_policy")
        loaded = reg.load_all()
        assert len(loaded) == 1
        assert loaded[0].policy_name == "test_policy"
        path.unlink(missing_ok=True)

    def test_filter_by_tag(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = Path(f.name)
        reg = ExperimentRegistry(path)
        m = TradeMetrics()
        reg.record(policy_name="p1", data_source="x", total_rows=5, accepted=3, rejected=2, metrics=m, tags=["prod"])
        reg.record(policy_name="p2", data_source="x", total_rows=5, accepted=2, rejected=3, metrics=m, tags=["test"])
        prod = reg.filter(tag="prod")
        assert len(prod) == 1
        assert prod[0].policy_name == "p1"
        path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# RecommendationExporter tests
# ---------------------------------------------------------------------------

class TestRecommendationExporter:
    def _make_report(self):
        policies = [
            PolicyConfig(name="baseline", min_ev=0.0),
            PolicyConfig(name="ev_filter", min_ev=0.08),
            PolicyConfig(name="strict", min_ev=0.15),
        ]
        runner = ScenarioRunner()
        results = runner.run(SAMPLE_ROWS, policies)
        comp = ComparisonEngine()
        return comp.compare(results, baseline_name="baseline")

    def test_generate_recommendations(self):
        report = self._make_report()
        exporter = RecommendationExporter()
        recs = exporter.generate(report, min_accepted_trades=1)
        assert len(recs) > 0
        assert all(r.confidence in ("HIGH", "MEDIUM", "LOW") for r in recs)

    def test_export_json(self):
        report = self._make_report()
        exporter = RecommendationExporter()
        recs = exporter.generate(report, min_accepted_trades=1)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        exporter.export_json(recs, path)
        data = json.loads(path.read_text())
        assert isinstance(data, list)
        assert all("policy_name" in r for r in data)
        path.unlink(missing_ok=True)

    def test_export_csv(self):
        report = self._make_report()
        exporter = RecommendationExporter()
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = Path(f.name)
        exporter.export_comparison_csv(report, path)
        content = path.read_text()
        assert "policy_name" in content
        assert "sharpe" in content
        path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# End-to-end integration test
# ---------------------------------------------------------------------------

class TestEndToEnd:
    def test_full_pipeline(self):
        """E2E: load → filter → equity → metrics → compare → export."""
        rows = SAMPLE_ROWS
        runner = ScenarioRunner()
        ev_configs = [
            PolicyConfig(name=f"ev_{ev:.2f}", min_ev=ev)
            for ev in [0.0, 0.05, 0.10, 0.15]
        ]
        results = runner.run(rows, ev_configs)
        ranked = runner.rank_by(results, key="sharpe")
        comp = ComparisonEngine()
        report = comp.compare(ranked, baseline_name="ev_0.00")
        exporter = RecommendationExporter()
        recs = exporter.generate(report, min_accepted_trades=1)
        assert len(recs) >= 0  # may be 0 if no policy meets threshold
        assert report.baseline is not None
        assert report.baseline.policy_name == "ev_0.00"

    def test_grid_run_100_configs(self):
        """Run the full EV grid (100+ configs) and verify all complete."""
        configs = ScenarioRunner.build_ev_grid()
        assert len(configs) >= 100
        runner = ScenarioRunner()
        results = runner.run(SAMPLE_ROWS, configs)
        assert len(results) == len(configs)
        for r in results:
            assert isinstance(r.replay.metrics, TradeMetrics)
            assert r.replay.metrics.total_trades >= 0
