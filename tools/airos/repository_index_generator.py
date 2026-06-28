#!/usr/bin/env python3
"""
AIROS v2 Repository Index Generator.
Scans the codebase, analyzes python file AST imports, computes risk levels,
and generates JSON registries (index, tools, tests, health) for AI agents.
"""

import os
import sys
import json
import ast
import argparse
import subprocess
from datetime import datetime, timezone

# Ignored directory names
IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "runtime",
    ".pytest_cache",
    "node_modules",
    "htmlcov",
    "dist",
    "build",
}

# High-risk path keywords
HIGH_RISK_KEYWORDS = {
    "risk_manager",
    "execution",
    "trader",
}


def get_relative_path(root_path, filepath):
    """Return relative path with forward slashes for cross-platform stability."""
    rel = os.path.relpath(filepath, root_path)
    return rel.replace(os.sep, "/")


def get_file_category(rel_path, extension):
    """Categorize file by its primary destination folder or extension."""
    if rel_path.startswith("polymarket/") or rel_path.startswith("config/"):
        return "runtime"
    if rel_path.startswith("tools/"):
        return "tools"
    if rel_path.startswith("tests/") or rel_path.split("/")[-1].startswith("test_"):
        return "tests"
    if extension in (".md", ".txt") or rel_path.startswith("docs/"):
        return "docs"
    if extension in (".json", ".toml", ".yaml", ".yml") or rel_path.split("/")[-1] == ".env":
        return "config"
    return "unclassified"


def get_tool_domain(rel_path):
    """Categorize tool by its directory domain or filename characteristics."""
    if not rel_path.startswith("tools/"):
        return "unknown"
    
    parts = rel_path.split("/")
    if len(parts) > 2 and parts[1] in ("audit", "replay", "shadow", "outcome_truth", "probes", "research", "runtime", "canonical", "airos"):
        return parts[1]
    
    filename = parts[-1].lower()
    if filename.startswith("_audit") or "_audit" in filename:
        return "audit"
    if "shadow" in filename or "semantic_c" in filename:
        return "shadow"
    if "replay" in filename or "runner" in filename:
        return "replay"
    if "outcome_truth" in filename or "resolution" in filename:
        return "outcome_truth"
    if "probe" in filename or "simulation" in filename or (filename.startswith("lifecycle_") and "report" in filename):
        return "probes"
    if "research_" in filename or "quant_" in filename or "no_entry" in filename:
        return "research"
    if "runtime" in filename or "paper" in filename or "dashboard" in filename or "summary" in filename or "builder" in filename or "aggregator" in filename or "compressor" in filename:
        return "runtime"
    if "canonical_" in filename:
        return "canonical"
    
    return "unknown"


def check_runtime_sensitive(rel_path):
    """Check if file path or name matches high-risk core components."""
    if rel_path.startswith("polymarket/") or rel_path.startswith("config/") or rel_path.endswith(".env"):
        return True
    filename = rel_path.split("/")[-1].lower()
    for kw in HIGH_RISK_KEYWORDS:
        if kw in filename or kw in rel_path.lower():
            return True
    return False


def get_line_count(filepath):
    """Count lines in text file safely."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def extract_python_imports(filepath):
    """Extract direct python imports using AST module parsing."""
    imports = set()
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            tree = ast.parse(f.read(), filename=filepath)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
    except Exception:
        pass
    return sorted(list(imports))


def get_git_health():
    """Retrieve git statistics (ahead, behind, dirty) via command line."""
    health = {"ahead": 0, "behind": 0, "dirty": False}
    try:
        # Check dirty
        status_res = subprocess.run(
            ["git", "status", "--short"], capture_output=True, text=True, check=False
        )
        if status_res.returncode == 0 and status_res.stdout.strip():
            health["dirty"] = True

        # Check ahead/behind
        branch_res = subprocess.run(
            ["git", "branch", "-vv"], capture_output=True, text=True, check=False
        )
        if branch_res.returncode == 0:
            for line in branch_res.stdout.splitlines():
                if line.startswith("*"):
                    if "ahead" in line:
                        parts = line.split("ahead ")
                        if len(parts) > 1:
                            health["ahead"] = int(parts[1].split("]")[0].split(",")[0].strip())
                    if "behind" in line:
                        parts = line.split("behind ")
                        if len(parts) > 1:
                            health["behind"] = int(parts[1].split("]")[0].split(",")[0].strip())
                    break
    except Exception:
        pass
    return health


def generate_registries(repo_root):
    """Walk repo, extract metadata, compile index, registries, and health state."""
    repo_root = os.path.abspath(repo_root)
    file_index = {}
    tool_registry = {
        "audit": [],
        "replay": [],
        "shadow": [],
        "outcome_truth": [],
        "probes": [],
        "research": [],
        "runtime": [],
        "canonical": [],
        "airos": [],
        "unknown": [],
    }
    
    # 1. First Pass: Scan all files
    for root, dirs, files in os.walk(repo_root):
        # Exclude ignored directories in-place (prune virtual envs and backups)
        dirs[:] = [d for d in dirs if not (d in IGNORED_DIRS or d.startswith(".venv") or d.startswith("venv") or d.startswith("tmp"))]
        
        for file in files:
            filepath = os.path.join(root, file)
            rel_path = get_relative_path(repo_root, filepath)
            
            # File properties
            _, ext = os.path.splitext(file)
            ext = ext.lower()
            size = os.path.getsize(filepath)
            
            is_py = ext == ".py"
            line_cnt = get_line_count(filepath) if ext in (".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml") else 0
            
            category = get_file_category(rel_path, ext)
            is_runtime_sensitive = check_runtime_sensitive(rel_path)
            
            direct_imports = extract_python_imports(filepath) if is_py else []
            
            is_test = category == "tests"
            is_tool = category == "tools"
            is_doc = category == "docs"
            is_config = category == "config"
            
            # Safe candidate classification:
            # Must be a tool, not in a package subfolder like backtest_engine_v2/flaos,
            # and not runtime sensitive.
            safe_to_move = False
            if is_tool:
                parts = rel_path.split("/")
                # Exclude backtest_engine_v2, flaos, and our own package airos
                if len(parts) > 1 and parts[1] not in ("backtest_engine_v2", "flaos", "airos"):
                    if not is_runtime_sensitive:
                        safe_to_move = True
            
            domain = get_tool_domain(rel_path) if is_tool else "unknown"
            
            file_meta = {
                "path": rel_path,
                "extension": ext,
                "file_type": ext.lstrip("."),
                "category": category,
                "domain": domain,
                "is_runtime_sensitive": is_runtime_sensitive,
                "is_test": is_test,
                "is_tool": is_tool,
                "is_doc": is_doc,
                "is_config": is_config,
                "line_count": line_cnt,
                "size_bytes": size,
                "import_count": len(direct_imports),
                "direct_imports": direct_imports,
                "likely_test_files": [],
                "safe_to_move_candidate": safe_to_move,
                "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
            
            file_index[rel_path] = file_meta
            
            if is_tool:
                tool_registry[domain].append(rel_path)

    # 2. Second Pass: Resolve test mappings
    test_registry = {
        "source_to_test": {},
        "test_to_source": {},
    }
    
    # Parse test imports to map tests back to source files
    for rel_path, meta in file_index.items():
        if meta["is_test"] and meta["extension"] == ".py":
            # Find which modules this test imports
            test_imports = meta["direct_imports"]
            for imp in test_imports:
                # E.g. tools.shadow.shadow_filter_evaluator or tools.shadow_filter_evaluator
                # Let's map module back to actual relative path:
                # Try matching by module parts
                mod_parts = imp.split(".")
                if mod_parts[0] in ("tools", "polymarket"):
                    target_path = "/".join(mod_parts) + ".py"
                    if target_path in file_index:
                        test_registry["source_to_test"].setdefault(target_path, []).append(rel_path)
                        test_registry["test_to_source"].setdefault(rel_path, []).append(target_path)
                    else:
                        # Try finding a filename matches without folder structure
                        basename = mod_parts[-1] + ".py"
                        for p in file_index:
                            if p.endswith("/" + basename) or p == basename:
                                test_registry["source_to_test"].setdefault(p, []).append(rel_path)
                                test_registry["test_to_source"].setdefault(rel_path, []).append(p)
            
            # Fallback by naming convention: e.g. tests/test_abc.py maps to tools/abc.py
            filename = rel_path.split("/")[-1]
            if filename.startswith("test_"):
                core_name = filename[5:] # strip test_
                for p in file_index:
                    if p.split("/")[-1] == core_name and p != rel_path:
                        test_registry["source_to_test"].setdefault(p, []).append(rel_path)
                        test_registry["test_to_source"].setdefault(rel_path, []).append(p)

    # Clean duplicates in test registry and map back to file index
    for src, tests in test_registry["source_to_test"].items():
        unique_tests = sorted(list(set(tests)))
        test_registry["source_to_test"][src] = unique_tests
        if src in file_index:
            file_index[src]["likely_test_files"] = unique_tests
            
    for tst, srcs in test_registry["test_to_source"].items():
        test_registry["test_to_source"][tst] = sorted(list(set(srcs)))

    # 3. Third Pass: Build repo health state
    total_files = len(file_index)
    total_lines = sum(meta["line_count"] for meta in file_index.values())
    total_bytes = sum(meta["size_bytes"] for meta in file_index.values())
    
    git_info = get_git_health()
    
    # Read active workflow state if exists
    active_task = "unknown"
    active_memory = "unknown"
    state_file = os.path.join(repo_root, "docs", "operations", "ACTIVE_WORKFLOW_STATE_001.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as sf:
                state_data = json.load(sf)
                active_task = state_data.get("next_task", "unknown")
                active_memory = state_data.get("workflow_governance", {}).get("active_loop_memory_file", "unknown")
        except Exception:
            pass

    repo_health = {
        "status": "HEALTHY",
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "metrics": {
            "total_files": total_files,
            "total_lines": total_lines,
            "total_size_bytes": total_bytes,
            "tools_count": sum(1 for m in file_index.values() if m["is_tool"]),
            "tests_count": sum(1 for m in file_index.values() if m["is_test"]),
            "runtime_files": sum(1 for m in file_index.values() if m["category"] == "runtime"),
        },
        "git_state": {
            "dirty": git_info["dirty"],
            "branch_ahead": git_info["ahead"],
            "branch_behind": git_info["behind"],
        },
        "active_workflow": {
            "active_task_id": active_task,
            "active_loop_memory_file": active_memory,
        },
    }

    # Sort all lists inside registries for determinism
    for dom in tool_registry:
        tool_registry[dom] = sorted(tool_registry[dom])

    # Convert test_registry to sorted dicts
    test_registry["source_to_test"] = {k: sorted(v) for k, v in sorted(test_registry["source_to_test"].items())}
    test_registry["test_to_source"] = {k: sorted(v) for k, v in sorted(test_registry["test_to_source"].items())}

    # Deterministic sort file index by key
    sorted_file_index = {k: file_index[k] for k in sorted(file_index.keys())}

    return sorted_file_index, tool_registry, test_registry, repo_health


def main():
    parser = argparse.ArgumentParser(description="AIROS v2 Repository Index Generator")
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory to save generated JSON registries",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print output JSON files",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Path to repository root directory",
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.repo_root):
        print(f"Error: repo-root path '{args.repo_root}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    os.makedirs(args.output_dir, exist_ok=True)
    
    index, tools, tests, health = generate_registries(args.repo_root)
    
    indent = 2 if args.pretty else None
    
    files_to_write = {
        "repository_index.json": index,
        "tool_registry.json": tools,
        "test_registry.json": tests,
        "repo_health.json": health,
    }
    
    for filename, data in files_to_write.items():
        out_path = os.path.join(args.output_dir, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, sort_keys=True)
        print(f"Generated: {out_path}")


if __name__ == "__main__":
    main()
