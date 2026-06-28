"""Tests for tools/airos/repository_navigator.py."""
from __future__ import annotations

import ast
import json
import textwrap
from pathlib import Path

import pytest

from tools.airos.repository_navigator import (
    DO_NOT_TOUCH_MODULES,
    SAFE_MOVE_MODULES,
    _extract_symbols,
    _is_runtime_sensitive_symbol,
    _trader_group,
    build_module_registry,
    build_navigation,
    build_symbol_index,
    main,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_repo_index():
    return {
        "polymarket/trader.py": {"type": "python"},
        "polymarket/delta_engine.py": {"type": "python"},
        "polymarket/client.py": {"type": "python"},
        "tools/airos/repository_navigator.py": {"type": "python"},
    }


@pytest.fixture
def minimal_dep_graph():
    return {
        "node_count": 4,
        "edge_count": 2,
        "edges": [],
        "nodes": [],
        "migration_safety_summary": {
            "polymarket/trader.py": {
                "blast_radius_score": 50,
                "migration_safety_status": "DO_NOT_MOVE",
            },
            "polymarket/delta_engine.py": {
                "blast_radius_score": 2,
                "migration_safety_status": "SAFE_ATOMIC",
            },
            "polymarket/client.py": {
                "blast_radius_score": 18,
                "migration_safety_status": "DO_NOT_MOVE",
            },
        },
        "reverse_importers": {
            "polymarket/delta_engine.py": ["polymarket/trader.py"],
        },
        "direct_imports_by_file": {
            "polymarket/trader.py": ["polymarket/delta_engine.py", "polymarket/client.py"],
        },
        "files_by_test": {
            "polymarket/delta_engine.py": ["tests/test_delta_engine.py"],
        },
        "runtime_sensitive_nodes": ["polymarket/client.py"],
    }


# ── Risk Symbol Detection ─────────────────────────────────────────────────

class TestRuntimeSensitiveSymbolDetection:
    def test_submit_order_is_sensitive(self):
        assert _is_runtime_sensitive_symbol("_submit_order")

    def test_place_limit_order_is_sensitive(self):
        assert _is_runtime_sensitive_symbol("place_limit_order")

    def test_reconcile_is_sensitive(self):
        assert _is_runtime_sensitive_symbol("reconcile_live_positions")

    def test_stop_loss_is_sensitive(self):
        assert _is_runtime_sensitive_symbol("check_stop_loss")

    def test_take_profit_is_sensitive(self):
        assert _is_runtime_sensitive_symbol("check_take_profit")

    def test_panic_sell_is_sensitive(self):
        assert _is_runtime_sensitive_symbol("panic_sell_check")

    def test_balance_is_sensitive(self):
        assert _is_runtime_sensitive_symbol("_fetch_live_balance_snapshot")

    def test_wallet_is_sensitive(self):
        assert _is_runtime_sensitive_symbol("_wallet_address_for_logs")

    def test_phase2_is_not_sensitive(self):
        assert not _is_runtime_sensitive_symbol("_phase2_observability_payload")

    def test_emit_is_not_sensitive(self):
        assert not _is_runtime_sensitive_symbol("_emit_trade_opened_event")

    def test_log_is_not_sensitive(self):
        assert not _is_runtime_sensitive_symbol("log_quant_summary")


# ── Trader Method Grouping ─────────────────────────────────────────────────

class TestTraderMethodGrouping:
    def test_phase2_is_observability(self):
        assert _trader_group("_phase2_complete_lifecycle_observability") == "observability"

    def test_size_sharp_is_telemetry(self):
        assert _trader_group("_size_sharp_metadata") == "telemetry"

    def test_path_truth_is_path_truth(self):
        assert _trader_group("_path_truth_parse_ts") == "path_truth"

    def test_submit_order_is_execution(self):
        assert _trader_group("_submit_order") == "execution"

    def test_validate_submit_is_execution(self):
        assert _trader_group("_validate_submit_order_intent") == "execution"

    def test_check_stop_loss_is_risk(self):
        assert _trader_group("check_stop_loss") == "risk"

    def test_check_take_profit_is_risk(self):
        assert _trader_group("check_take_profit") == "risk"

    def test_panic_sell_is_risk(self):
        assert _trader_group("panic_sell_check") == "risk"

    def test_position_sizing_is_sizing(self):
        assert _trader_group("_maybe_apply_micro_survival_plan") == "sizing"

    def test_reconcile_is_reconciliation(self):
        assert _trader_group("reconcile_live_positions") == "reconciliation"

    def test_bankroll_state_is_balance(self):
        assert _trader_group("_update_bankroll_state") == "balance"

    def test_paper_record_is_paper(self):
        assert _trader_group("_paper_record_skip") == "paper"

    def test_dashboard_is_dashboard(self):
        assert _trader_group("dashboard_portfolio_state") == "dashboard"

    def test_analyze_market_is_market_evaluation(self):
        assert _trader_group("_analyze_market") == "market_evaluation"

    def test_unknown_method(self):
        assert _trader_group("some_random_helper_xyz") == "unknown"


# ── AST Symbol Extraction ─────────────────────────────────────────────────

class TestExtractSymbols:
    def _write_py(self, tmp_path, name, source):
        p = tmp_path / name
        p.write_text(textwrap.dedent(source), encoding="utf-8")
        return str(p)

    def test_extracts_class_and_methods(self, tmp_path):
        path = self._write_py(tmp_path, "sample.py", """
            class MyClass:
                def method_a(self):
                    pass

                def method_b(self):
                    x = 1
                    y = 2
                    return x + y
        """)
        sym = _extract_symbols(path)
        assert sym["class_count"] == 1
        assert sym["method_count"] == 2
        cls = sym["classes"][0]
        assert cls["name"] == "MyClass"
        assert len(cls["methods"]) == 2
        names = [m["name"] for m in cls["methods"]]
        assert "method_a" in names
        assert "method_b" in names

    def test_extracts_top_functions(self, tmp_path):
        path = self._write_py(tmp_path, "funcs.py", """
            def func_one():
                pass

            def func_two():
                return 42
        """)
        sym = _extract_symbols(path)
        assert sym["top_function_count"] == 2
        names = [f["name"] for f in sym["top_functions"]]
        assert "func_one" in names
        assert "func_two" in names

    def test_runtime_sensitive_method_flagged(self, tmp_path):
        path = self._write_py(tmp_path, "exec.py", """
            class Trader:
                def _submit_order(self):
                    pass

                def _phase2_observability(self):
                    pass
        """)
        sym = _extract_symbols(path)
        methods = sym["classes"][0]["methods"]
        submit = next(m for m in methods if m["name"] == "_submit_order")
        phase2 = next(m for m in methods if m["name"] == "_phase2_observability")
        assert submit["runtime_sensitive"] is True
        assert phase2["runtime_sensitive"] is False

    def test_largest_symbols_sorted(self, tmp_path):
        path = self._write_py(tmp_path, "sizes.py", """
            class Big:
                def small(self):
                    pass

                def huge(self):
                    a = 1
                    b = 2
                    c = 3
                    d = 4
                    e = 5
                    return a + b + c + d + e
        """)
        sym = _extract_symbols(path)
        sizes = [s["size"] for s in sym["largest_symbols"]]
        assert sizes == sorted(sizes, reverse=True)

    def test_trader_method_groups_populated(self, tmp_path):
        # Must be in a 'polymarket/' path for trader group detection to activate
        (tmp_path / "polymarket").mkdir()
        p = tmp_path / "polymarket" / "trader.py"
        p.write_text(textwrap.dedent("""
            class PolymarketTrader:
                def _phase2_lifecycle(self):
                    pass
                def _submit_order(self):
                    pass
                def check_stop_loss(self):
                    pass
                def _paper_record_skip(self):
                    pass
        """), encoding="utf-8")
        sym = _extract_symbols(str(p))
        groups = sym.get("trader_py_method_groups", {})
        assert "observability" in groups
        assert "_phase2_lifecycle" in groups["observability"]["methods"]
        assert "execution" in groups
        assert "_submit_order" in groups["execution"]["methods"]
        assert groups["execution"]["high_risk"] is True
        assert groups["observability"]["safe_first_extraction"] is True

    def test_parse_error_handled_gracefully(self, tmp_path):
        path = self._write_py(tmp_path, "bad.py", "def broken(: !!!")
        sym = _extract_symbols(path)
        assert sym.get("parse_error") is True

    def test_line_numbers_present(self, tmp_path):
        path = self._write_py(tmp_path, "lines.py", """
            class C:
                def alpha(self):
                    pass
        """)
        sym = _extract_symbols(path)
        method = sym["classes"][0]["methods"][0]
        assert method["line"] > 0


# ── Module Registry ────────────────────────────────────────────────────────

class TestModuleRegistry:
    def test_builds_from_fixture(self, minimal_repo_index, minimal_dep_graph):
        registry = build_module_registry(minimal_repo_index, minimal_dep_graph)
        assert registry["module_count"] > 0
        paths = [m["path"] for m in registry["modules"]]
        assert "polymarket/trader.py" in paths

    def test_do_not_touch_flagged(self, minimal_repo_index, minimal_dep_graph):
        registry = build_module_registry(minimal_repo_index, minimal_dep_graph)
        trader = next(m for m in registry["modules"] if m["path"] == "polymarket/trader.py")
        assert trader["do_not_touch"] is True
        assert trader["safe_move_status"] == "DO_NOT_MOVE"

    def test_safe_move_flagged(self, minimal_repo_index, minimal_dep_graph):
        registry = build_module_registry(minimal_repo_index, minimal_dep_graph)
        delta = next((m for m in registry["modules"] if m["path"] == "polymarket/delta_engine.py"), None)
        if delta:
            assert delta["safe_move_status"] == "SAFE_MOVE"
            assert delta["recommended_target_folder"] == "polymarket/models/"

    def test_reverse_importers_present(self, minimal_repo_index, minimal_dep_graph):
        registry = build_module_registry(minimal_repo_index, minimal_dep_graph)
        delta = next((m for m in registry["modules"] if m["path"] == "polymarket/delta_engine.py"), None)
        if delta:
            assert "polymarket/trader.py" in delta["reverse_importers"]

    def test_domain_classification(self, minimal_repo_index, minimal_dep_graph):
        registry = build_module_registry(minimal_repo_index, minimal_dep_graph)
        modules_by_path = {m["path"]: m for m in registry["modules"]}
        if "polymarket/trader.py" in modules_by_path:
            assert modules_by_path["polymarket/trader.py"]["domain"] == "polymarket"

    def test_schema_version_present(self, minimal_repo_index, minimal_dep_graph):
        registry = build_module_registry(minimal_repo_index, minimal_dep_graph)
        assert "schema_version" in registry
        assert "generated_at_utc" in registry

    def test_sorted_output(self, minimal_repo_index, minimal_dep_graph):
        registry = build_module_registry(minimal_repo_index, minimal_dep_graph)
        paths = [m["path"] for m in registry["modules"]]
        assert paths == sorted(paths)


# ── Navigation ────────────────────────────────────────────────────────────

class TestNavigation:
    def _make_nav(self, minimal_repo_index, minimal_dep_graph):
        registry = build_module_registry(minimal_repo_index, minimal_dep_graph)
        sym = build_symbol_index(registry)
        return build_navigation(registry, sym)

    def test_do_not_touch_zones_present(self, minimal_repo_index, minimal_dep_graph):
        nav = self._make_nav(minimal_repo_index, minimal_dep_graph)
        zones = nav["do_not_touch_zones"]
        assert "execution_path" in zones
        assert "risk_sizing" in zones
        assert "configuration" in zones

    def test_runtime_sensitive_zones_include_trader(self, minimal_repo_index, minimal_dep_graph):
        nav = self._make_nav(minimal_repo_index, minimal_dep_graph)
        rt_files = nav["runtime_sensitive_zones"]["files"]
        assert "polymarket/trader.py" in rt_files

    def test_ai_startup_read_order_present(self, minimal_repo_index, minimal_dep_graph):
        nav = self._make_nav(minimal_repo_index, minimal_dep_graph)
        order = nav["ai_startup_read_order"]
        assert len(order) >= 5
        assert any("ACTIVE_WORKFLOW_STATE" in p for p in order)
        assert any("navigation.json" in p for p in order)

    def test_next_wave_recommendation(self, minimal_repo_index, minimal_dep_graph):
        nav = self._make_nav(minimal_repo_index, minimal_dep_graph)
        rec = nav["next_wave_recommendation"]
        assert rec["wave"] == 2
        assert "WAVE2" in rec["task"]

    def test_major_domains_present(self, minimal_repo_index, minimal_dep_graph):
        nav = self._make_nav(minimal_repo_index, minimal_dep_graph)
        domains = nav["major_domains"]
        assert "polymarket" in domains
        assert "tools" in domains
        assert "tests" in domains

    def test_schema_version(self, minimal_repo_index, minimal_dep_graph):
        nav = self._make_nav(minimal_repo_index, minimal_dep_graph)
        assert nav["schema_version"] == "repository_navigator_v1"


# ── CLI Smoke Test ────────────────────────────────────────────────────────

class TestCLISmoke:
    def test_cli_writes_all_three_json_files(self, tmp_path, minimal_repo_index, minimal_dep_graph):
        input_dir = tmp_path / "repo"
        input_dir.mkdir()
        (input_dir / "repository_index.json").write_text(
            json.dumps(minimal_repo_index), encoding="utf-8"
        )
        (input_dir / "dependency_graph.json").write_text(
            json.dumps(minimal_dep_graph), encoding="utf-8"
        )
        ret = main(["--input-dir", str(input_dir), "--output-dir", str(tmp_path / "out"), "--pretty"])
        assert ret == 0
        out = tmp_path / "out"
        assert (out / "navigation.json").exists()
        assert (out / "symbol_index.json").exists()
        assert (out / "module_registry.json").exists()

    def test_cli_json_valid(self, tmp_path, minimal_repo_index, minimal_dep_graph):
        input_dir = tmp_path / "repo"
        input_dir.mkdir()
        (input_dir / "repository_index.json").write_text(
            json.dumps(minimal_repo_index), encoding="utf-8"
        )
        (input_dir / "dependency_graph.json").write_text(
            json.dumps(minimal_dep_graph), encoding="utf-8"
        )
        main(["--input-dir", str(input_dir), "--output-dir", str(tmp_path / "out")])
        for fname in ("navigation.json", "symbol_index.json", "module_registry.json"):
            content = (tmp_path / "out" / fname).read_text(encoding="utf-8")
            parsed = json.loads(content)
            assert isinstance(parsed, dict)

    def test_cli_missing_input_returns_error(self, tmp_path):
        ret = main(["--input-dir", str(tmp_path / "nonexistent"), "--output-dir", str(tmp_path)])
        assert ret == 1


# ── Do-Not-Touch Constants ────────────────────────────────────────────────

class TestConstants:
    def test_trader_in_do_not_touch(self):
        assert "polymarket/trader.py" in DO_NOT_TOUCH_MODULES

    def test_client_in_do_not_touch(self):
        assert "polymarket/client.py" in DO_NOT_TOUCH_MODULES

    def test_delta_engine_in_safe_move(self):
        assert "polymarket/delta_engine.py" in SAFE_MOVE_MODULES
        assert SAFE_MOVE_MODULES["polymarket/delta_engine.py"] == "polymarket/models/"

    def test_gamma_fetcher_in_safe_move(self):
        assert "polymarket/gamma_fetcher.py" in SAFE_MOVE_MODULES
        assert SAFE_MOVE_MODULES["polymarket/gamma_fetcher.py"] == "polymarket/market/"

    def test_backtester_in_safe_move(self):
        assert "polymarket/backtester_5m.py" in SAFE_MOVE_MODULES
        assert SAFE_MOVE_MODULES["polymarket/backtester_5m.py"] == "polymarket/backtest/"
