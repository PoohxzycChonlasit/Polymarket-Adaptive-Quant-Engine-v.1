"""Repository Navigator and Symbol Index Generator.

Reads repository_index.json and dependency_graph.json to produce three
machine-readable outputs for AI agent navigation:

  navigation.json     — domain map, do-not-touch zones, AI startup read order
  module_registry.json — per-module metadata, blast-radius, move safety
  symbol_index.json    — AST-parsed classes/functions/methods with risk labels

Usage:
  python tools/airos/repository_navigator.py --input-dir docs/operations/repository --pretty
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "repository_navigator_v1"

# ── Risk name patterns ──────────────────────────────────────────────────────
_HIGH_RISK_NAME_PATTERNS = re.compile(
    r"submit_order|place_limit_order|place_order|validate_submit|"
    r"_execution|execution_|order_intent|execute_|_execute|"
    r"reconcil|_reconcil|reconcile_|"
    r"stop_loss|take_profit|panic_sell|check_stop|check_take|"
    r"_risk_|risk_plan|_sizing|sizing_|position_size|"
    r"_live_|live_order|live_fill|live_balance|"
    r"wallet|balance|allowance|"
    r"_trigger_lockdown|apply_risk",
    re.IGNORECASE,
)

# ── Trader method group patterns ────────────────────────────────────────────
_TRADER_GROUPS: list[tuple[str, re.Pattern]] = [
    ("observability",    re.compile(r"_phase2_|observability|_lifecycle_obs|lifecycle_obs", re.I)),
    ("telemetry",        re.compile(r"_size_sharp|_shadow_policy|_bankroll_carry|_emit_trade|_emit_decision|_emit_risk|_emit_cycle|_emit_entry|_emit_zero|_emit_path|telemetry", re.I)),
    ("path_truth",       re.compile(r"_path_truth|path_truth|_emit_path_truth", re.I)),
    ("orderbook_lineage",re.compile(r"orderbook_lineage|_build_orderbook_lineage|_mark_orderbook|_orderbook_refresh", re.I)),
    ("decision_diag",    re.compile(r"_decision_diagnostics|_risk_boundary_payload", re.I)),
    ("paper",            re.compile(r"_paper_|paper_session|paper_stats|_paper_enabled", re.I)),
    ("dashboard",        re.compile(r"dashboard|update_dashboard|paper_session_summary|_compile_dashboard|_log_session", re.I)),
    ("position",         re.compile(r"_open_tracked|_close_tracked|_position_token|_position_outcome|_position_mark|_open_positions|_entry_count|_record_market_entry", re.I)),
    ("market_evaluation",re.compile(r"_analyze_market|_select_markets|_fetch_orderbook|_token_mapping|_classify_orderbook|get_market_display|_check_and_alert|verify_account", re.I)),
    ("execution",        re.compile(r"_submit_order|_validate_submit|_verify_balance|_close_position_with|_reduce_position_with|_force_exit|_compute_limit_price|auto_redeem", re.I)),
    ("risk",             re.compile(r"check_stop_loss|check_take_profit|panic_sell|_trigger_lockdown|_update_risk_mode|_apply_risk_mode|_risk_off|_risk_mode_decision", re.I)),
    ("sizing",           re.compile(r"_maybe_apply_micro|_micro_survival|_entry_min_position|_bankroll_mode|_sync_sizing", re.I)),
    ("reconciliation",   re.compile(r"reconcile_live|_block_on_reconcil|_poll_pending_live|_reconcile_after", re.I)),
    ("balance",          re.compile(r"_update_bankroll_state|_update_bankroll_rank|_apply_balance|refresh_live_balance|_fetch_live_balance|_record_balance|_apply_paper", re.I)),
    ("lifecycle_infra",  re.compile(r"close\b|shutdown|stop\b|_call_shutdown|_begin_cycle|_finish_cycle|_cycle_elapsed|set_runtime_cadence|_mark_market_eval|run_single_cycle|run_ghost", re.I)),
]

_EXECUTION_RISK_GROUPS = {"execution", "risk", "sizing", "reconciliation", "balance"}
_SAFE_FIRST_GROUPS = {"observability", "telemetry", "path_truth", "orderbook_lineage", "decision_diag", "paper", "dashboard"}

# ── Do-not-touch module list ────────────────────────────────────────────────
DO_NOT_TOUCH_MODULES = {
    "polymarket/trader.py",
    "polymarket/client.py",
    "polymarket/signal.py",
    "polymarket/oracle_price_feed.py",
    "polymarket/opportunity_scanner.py",
    "polymarket/price_to_beat_fetcher.py",
    "polymarket/market_feed.py",
    "polymarket/bankroll_rank_engine.py",
    "polymarket/bankroll_tiers.py",
    "polymarket/arbitrage_executor.py",
    "polymarket/order_intent.py",
    "polymarket/order_manager.py",
    "polymarket/position_manager.py",
    "polymarket/position_sizing.py",
    "polymarket/risk_modes.py",
    "polymarket/trade_frequency.py",
    "polymarket/virtual_ptb.py",
    "polymarket/shadow_policy.py",
    "polymarket/market_availability_engine.py",
    "polymarket/size_sharp_engine.py",
    "config/settings.py",
    "main.py",
    "tools/execution_paper_runtime.py",
    "tools/replay_analyzer.py",
}

SAFE_MOVE_MODULES = {
    "polymarket/regime_diagnostics.py": "polymarket/observability/",
    "polymarket/realtime_logger.py": "polymarket/observability/",
    "polymarket/shadow_telemetry.py": "polymarket/observability/",
    "polymarket/trader_presentation.py": "polymarket/observability/",
    "polymarket/probability_model.py": "polymarket/models/",
    "polymarket/quant_indicators.py": "polymarket/models/",
    "polymarket/expected_value.py": "polymarket/models/",
    "polymarket/delta_engine.py": "polymarket/models/",
    "polymarket/gamma_fetcher.py": "polymarket/market/",
    "polymarket/five_min_monitor.py": "polymarket/market/",
    "polymarket/trend_runner.py": "polymarket/market/",
    "polymarket/lucky_shot.py": "polymarket/market/",
    "polymarket/arbitrage.py": "polymarket/market/",
    "polymarket/backtester_5m.py": "polymarket/backtest/",
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _line_count(path: str) -> int:
    try:
        return sum(1 for _ in open(path, encoding="utf-8", errors="ignore"))
    except OSError:
        return 0


# ────────────────────────────────────────────────────────────────────────────
# AST Symbol Extraction
# ────────────────────────────────────────────────────────────────────────────

def _is_runtime_sensitive_symbol(name: str) -> bool:
    return bool(_HIGH_RISK_NAME_PATTERNS.search(name))


def _trader_group(method_name: str) -> str:
    for group_name, pattern in _TRADER_GROUPS:
        if pattern.search(method_name):
            return group_name
    return "unknown"


def _extract_symbols(filepath: str) -> dict[str, Any]:
    """Parse a Python file and extract its top-level and class symbols."""
    try:
        source = Path(filepath).read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, OSError):
        return {"parse_error": True, "path": filepath}

    total_lines = source.count("\n") + 1
    classes: list[dict] = []
    top_functions: list[dict] = []
    all_methods: list[dict] = []
    is_trader = filepath.endswith("trader.py") and "polymarket" in filepath

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    end_line = getattr(item, "end_lineno", item.lineno)
                    size = end_line - item.lineno + 1
                    m = {
                        "name": item.name,
                        "line": item.lineno,
                        "size": size,
                        "runtime_sensitive": _is_runtime_sensitive_symbol(item.name),
                    }
                    if is_trader:
                        m["trader_group"] = _trader_group(item.name)
                        m["safe_first_extraction"] = m["trader_group"] in _SAFE_FIRST_GROUPS
                        m["high_risk"] = m["trader_group"] in _EXECUTION_RISK_GROUPS
                    methods.append(m)
                    all_methods.append({"class": node.name, **m})

            classes.append({
                "name": node.name,
                "line": node.lineno,
                "method_count": len(methods),
                "methods": methods,
            })

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_line = getattr(node, "end_lineno", node.lineno)
            top_functions.append({
                "name": node.name,
                "line": node.lineno,
                "size": end_line - node.lineno + 1,
                "runtime_sensitive": _is_runtime_sensitive_symbol(node.name),
            })

    # Largest symbols
    all_syms = [
        {"name": m["name"], "class": m.get("class"), "size": m["size"]}
        for m in all_methods
    ] + [
        {"name": f["name"], "class": None, "size": f["size"]}
        for f in top_functions
    ]
    largest = sorted(all_syms, key=lambda x: -x["size"])[:10]

    result: dict[str, Any] = {
        "path": filepath,
        "total_lines": total_lines,
        "class_count": len(classes),
        "top_function_count": len(top_functions),
        "method_count": len(all_methods),
        "classes": classes,
        "top_functions": top_functions,
        "largest_symbols": largest,
        "runtime_sensitive_symbols": [
            m["name"] for m in all_methods if m.get("runtime_sensitive")
        ] + [f["name"] for f in top_functions if f.get("runtime_sensitive")],
    }

    if is_trader:
        # Build trader method groups summary
        groups: dict[str, list[str]] = {}
        for m in all_methods:
            g = m.get("trader_group", "unknown")
            groups.setdefault(g, []).append(m["name"])
        result["trader_py_method_groups"] = {
            g: {
                "count": len(names),
                "methods": sorted(names),
                "high_risk": g in _EXECUTION_RISK_GROUPS,
                "safe_first_extraction": g in _SAFE_FIRST_GROUPS,
            }
            for g, names in sorted(groups.items())
        }

    return result


# ────────────────────────────────────────────────────────────────────────────
# Module Registry Builder
# ────────────────────────────────────────────────────────────────────────────

def build_module_registry(
    repository_index: dict,
    dependency_graph: dict,
) -> dict[str, Any]:
    """Build per-module metadata from AIROS registries."""
    safety_summary = dependency_graph.get("migration_safety_summary", {})
    reverse_importers = dependency_graph.get("reverse_importers", {})
    direct_imports = dependency_graph.get("direct_imports_by_file", {})
    files_by_test = dependency_graph.get("files_by_test", {})

    modules: list[dict] = []

    # Collect all Python module paths from the repository index
    all_paths: set[str] = set()
    for key in repository_index:
        if isinstance(key, str) and key.endswith(".py"):
            all_paths.add(key.replace("\\", "/"))

    # Add polymarket + tools + utils + config modules explicitly
    for root in ("polymarket", "tools", "utils", "config", "tests"):
        for p in Path(root).rglob("*.py"):
            all_paths.add(str(p).replace("\\", "/"))

    for path in sorted(all_paths):
        if "__pycache__" in path:
            continue
        norm = path.replace("\\", "/")
        safety = safety_summary.get(norm, {})
        blast = safety.get("blast_radius_score", 0)
        status = safety.get("migration_safety_status", "UNKNOWN")

        # Determine domain
        if norm.startswith("polymarket/"):
            domain = "polymarket"
        elif norm.startswith("tools/outcome_truth/"):
            domain = "tools.outcome_truth"
        elif norm.startswith("tools/replay/"):
            domain = "tools.replay"
        elif norm.startswith("tools/research/"):
            domain = "tools.research"
        elif norm.startswith("tools/runtime/"):
            domain = "tools.runtime"
        elif norm.startswith("tools/unknown/"):
            domain = "tools.unknown"
        elif norm.startswith("tools/airos/"):
            domain = "tools.airos"
        elif norm.startswith("tools/flaos/"):
            domain = "tools.flaos"
        elif norm.startswith("tools/backtest_engine_v2/"):
            domain = "tools.backtest_engine_v2"
        elif norm.startswith("tools/"):
            domain = "tools"
        elif norm.startswith("utils/"):
            domain = "utils"
        elif norm.startswith("config/"):
            domain = "config"
        elif norm.startswith("tests/"):
            domain = "tests"
        else:
            domain = "root"

        module_name = norm.replace("/", ".").removesuffix(".py")
        package = "/".join(norm.split("/")[:-1]) or "."
        is_do_not_touch = norm in DO_NOT_TOUCH_MODULES
        safe_move_target = SAFE_MOVE_MODULES.get(norm)
        runtime_sensitive = (
            is_do_not_touch
            or blast >= 10
            or any(keyword in norm for keyword in ["execution", "risk", "sizing", "order", "wallet", "balance"])
        )

        modules.append({
            "path": norm,
            "module_name": module_name,
            "domain": domain,
            "package": package,
            "line_count": _line_count(norm) if Path(norm).exists() else 0,
            "blast_radius_score": blast,
            "migration_safety_status": status,
            "runtime_sensitive": runtime_sensitive,
            "do_not_touch": is_do_not_touch,
            "direct_imports": sorted(direct_imports.get(norm, [])),
            "reverse_importers": sorted(reverse_importers.get(norm, [])),
            "tests": sorted(files_by_test.get(norm, [])),
            "safe_move_status": (
                "DO_NOT_MOVE" if is_do_not_touch
                else ("SAFE_MOVE" if safe_move_target else status)
            ),
            "recommended_target_folder": safe_move_target or None,
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _utcnow(),
        "module_count": len(modules),
        "modules": modules,
    }


# ────────────────────────────────────────────────────────────────────────────
# Symbol Index Builder
# ────────────────────────────────────────────────────────────────────────────

def build_symbol_index(module_registry: dict) -> dict[str, Any]:
    """Parse AST of all Python modules and build a symbol index."""
    files: list[dict] = []
    largest_overall: list[dict] = []

    priority_files = ["polymarket/trader.py"]
    all_py = [m["path"] for m in module_registry["modules"] if m["path"].endswith(".py")]

    # Parse priority files first, then the rest
    ordered = priority_files + [p for p in all_py if p not in priority_files]

    for path in ordered:
        if not Path(path).exists():
            continue
        sym = _extract_symbols(path)
        files.append(sym)
        for s in sym.get("largest_symbols", []):
            largest_overall.append({"file": path, **s})

    largest_overall.sort(key=lambda x: -x["size"])

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _utcnow(),
        "file_count": len(files),
        "files": files,
        "largest_symbols_across_repo": largest_overall[:25],
        "runtime_sensitive_files": [
            {"path": f["path"], "symbols": f.get("runtime_sensitive_symbols", [])}
            for f in files
            if f.get("runtime_sensitive_symbols")
        ],
    }


# ────────────────────────────────────────────────────────────────────────────
# Navigation Map Builder
# ────────────────────────────────────────────────────────────────────────────

def build_navigation(
    module_registry: dict,
    symbol_index: dict,
    wave_optimizer_path: str | None = None,
) -> dict[str, Any]:
    """Build high-level navigation map for AI agent startup."""
    modules = module_registry["modules"]

    # Current folder map
    folder_counts: dict[str, int] = {}
    for m in modules:
        folder = m["package"]
        folder_counts[folder] = folder_counts.get(folder, 0) + 1

    # Trader method groups from symbol index
    trader_groups: dict[str, Any] = {}
    for f in symbol_index.get("files", []):
        if f.get("path", "").endswith("trader.py") and "polymarket" in f.get("path", ""):
            trader_groups = f.get("trader_py_method_groups", {})
            break

    # Safe move candidates
    safe_moves = [m for m in modules if m["safe_move_status"] == "SAFE_MOVE"]
    do_not_touch = [m["path"] for m in modules if m["do_not_touch"]]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _utcnow(),
        "major_domains": {
            "polymarket": {
                "description": "Runtime trading modules — execution loop, market data, models, signals",
                "module_count": sum(1 for m in modules if m["domain"] == "polymarket"),
                "safe_move_candidates": len(safe_moves),
                "do_not_touch_count": len([m for m in modules if m["do_not_touch"] and m["domain"] == "polymarket"]),
            },
            "tools": {
                "description": "Offline analysis, replay, research, and AIROS tooling",
                "subdomains": {
                    "tools.airos": sum(1 for m in modules if m["domain"] == "tools.airos"),
                    "tools.flaos": sum(1 for m in modules if m["domain"] == "tools.flaos"),
                    "tools.backtest_engine_v2": sum(1 for m in modules if m["domain"] == "tools.backtest_engine_v2"),
                    "tools.outcome_truth": sum(1 for m in modules if m["domain"] == "tools.outcome_truth"),
                    "tools.replay": sum(1 for m in modules if m["domain"] == "tools.replay"),
                    "tools.research": sum(1 for m in modules if m["domain"] == "tools.research"),
                    "tools.runtime": sum(1 for m in modules if m["domain"] == "tools.runtime"),
                    "tools.unknown": sum(1 for m in modules if m["domain"] == "tools.unknown"),
                },
            },
            "tests": {
                "description": "Test suite (flat, 160+ files — Wave 3 will organize)",
                "module_count": sum(1 for m in modules if m["domain"] == "tests"),
            },
            "utils": {
                "description": "Shared utilities: logging, Telegram alerts, quant event logger",
                "module_count": sum(1 for m in modules if m["domain"] == "utils"),
            },
        },
        "current_folder_map": dict(sorted(folder_counts.items())),
        "target_folder_map": {
            "polymarket/models/": [m["path"] for m in safe_moves if "models" in (m["recommended_target_folder"] or "")],
            "polymarket/market/": [m["path"] for m in safe_moves if "market" in (m["recommended_target_folder"] or "")],
            "polymarket/observability/": [m["path"] for m in safe_moves if "observability" in (m["recommended_target_folder"] or "")],
            "polymarket/backtest/": [m["path"] for m in safe_moves if "backtest" in (m["recommended_target_folder"] or "")],
        },
        "runtime_sensitive_zones": {
            "description": "Modules that must not be moved or modified without explicit operator approval",
            "files": sorted(do_not_touch),
        },
        "do_not_touch_zones": {
            "execution_path": [
                "polymarket/trader.py (_submit_order, _validate_submit_order_intent)",
                "polymarket/client.py",
                "polymarket/order_manager.py",
                "polymarket/order_intent.py",
            ],
            "risk_sizing": [
                "polymarket/position_sizing.py",
                "polymarket/bankroll_tiers.py",
                "polymarket/bankroll_rank_engine.py",
                "polymarket/risk_modes.py",
                "polymarket/size_sharp_engine.py",
            ],
            "live_market_feed": [
                "polymarket/signal.py",
                "polymarket/oracle_price_feed.py",
                "polymarket/market_feed.py",
                "polymarket/price_to_beat_fetcher.py",
                "polymarket/opportunity_scanner.py",
            ],
            "configuration": ["config/settings.py", ".env"],
            "flagged_by_graph": [
                "tools/execution_paper_runtime.py",
                "tools/replay_analyzer.py",
            ],
        },
        "trader_py_method_groups": trader_groups,
        "next_wave_recommendation": {
            "wave": 2,
            "task": "REPOSITORY_WAVE2_POLYMARKET_SAFE_PACKAGES_001",
            "description": "Move 14 SAFE_MOVE polymarket/ files into models/, market/, observability/, backtest/",
            "safe_move_candidates": [
                {"path": m["path"], "target": m["recommended_target_folder"]}
                for m in safe_moves
            ],
            "prerequisite": "blast-radius check via dependency_graph.json before execution",
        },
        "ai_startup_read_order": [
            "docs/operations/AI_REPO_BOOTSTRAP_001.md",
            "PROJECT_RULES.md",
            "MASTER_AGENT_ROUTER.md",
            "docs/operations/ACTIVE_WORKFLOW_STATE_001.json",
            "docs/operations/repository/navigation.json",        # ← this file
            "docs/operations/repository/module_registry.json",   # ← fast module lookup
            "docs/operations/repository/symbol_index.json",      # ← trader.py method map
            "docs/operations/TASK_QUEUE_001.json",
            "docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json",
        ],
    }


# ────────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repository Navigator and Symbol Index Generator.")
    parser.add_argument("--input-dir", default="docs/operations/repository",
                        help="Directory containing repository_index.json and dependency_graph.json")
    parser.add_argument("--output-dir", default=None,
                        help="Output directory (defaults to --input-dir)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--wave-optimizer", default=None,
                        help="Path to REPOSITORY_WAVE_OPTIMIZER_001.md (optional)")
    args = parser.parse_args(argv)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir) if args.output_dir else input_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    indent = 2 if args.pretty else None

    repo_index_path = input_dir / "repository_index.json"
    dep_graph_path = input_dir / "dependency_graph.json"

    if not repo_index_path.exists():
        print(f"ERROR: {repo_index_path} not found", file=sys.stderr)
        return 1
    if not dep_graph_path.exists():
        print(f"ERROR: {dep_graph_path} not found", file=sys.stderr)
        return 1

    print(f"Loading {repo_index_path}...")
    repository_index = json.loads(repo_index_path.read_text(encoding="utf-8"))
    print(f"Loading {dep_graph_path}...")
    dependency_graph = json.loads(dep_graph_path.read_text(encoding="utf-8"))

    print("Building module registry...")
    module_registry = build_module_registry(repository_index, dependency_graph)
    out_registry = output_dir / "module_registry.json"
    out_registry.write_text(json.dumps(module_registry, indent=indent), encoding="utf-8")
    print(f"Generated: {out_registry} ({module_registry['module_count']} modules)")

    print("Building symbol index (parsing AST)...")
    symbol_index = build_symbol_index(module_registry)
    out_symbols = output_dir / "symbol_index.json"
    out_symbols.write_text(json.dumps(symbol_index, indent=indent), encoding="utf-8")
    print(f"Generated: {out_symbols} ({symbol_index['file_count']} files parsed)")

    print("Building navigation map...")
    navigation = build_navigation(module_registry, symbol_index, args.wave_optimizer)
    out_nav = output_dir / "navigation.json"
    out_nav.write_text(json.dumps(navigation, indent=indent), encoding="utf-8")
    print(f"Generated: {out_nav}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
