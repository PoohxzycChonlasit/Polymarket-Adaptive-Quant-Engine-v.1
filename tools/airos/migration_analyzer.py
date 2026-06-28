#!/usr/bin/env python3
"""
AIROS v2 Migration Analyzer.

Reads batch_candidates.json and produces migration_patch_plan.json with
a complete pre-move analysis of every rewriting and patching requirement
before any file is relocated. Designed to feed the atomic_batch_executor
with pre-computed knowledge so all patterns are handled deterministically.

Detected patterns:
  1. Python import statements: import tools.x / from tools.x import y / from tools import x
  2. Monkeypatch/mock string references: "tools.x.func" / 'tools.x.func'
  3. Hardcoded source path reads: Path("tools/x.py") / Path('tools/x.py')
  4. _REPO / "tools" / "x.py" style path builds
  5. AST source readers that may break after relocation
  6. importlib.import_module("tools.x") / importlib.import_module('tools.x')
  7. Target package directory __init__.py requirements
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "migration_patch_plan_v1"
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
SCAN_FOLDERS = ("tools", "tests")


# ---------------------------------------------------------------------------
# Pattern detection helpers
# ---------------------------------------------------------------------------


def _slashpath(mod: str) -> str:
    """Convert module dotted name to slash path fragment (no extension)."""
    return mod.replace(".", "/")


def _detect_patterns_in_file(
    filepath: str,
    old_mod: str,
    old_slashpath: str,
) -> dict[str, list[dict[str, Any]]]:
    """
    Scan a single file for all patterns that reference old_mod or old_slashpath.

    Returns a dict keyed by pattern type, each containing a list of match
    records: {line_no, line_content, pattern_type}.
    """
    results: dict[str, list[dict[str, Any]]] = {
        "import_statements": [],
        "monkeypatch_strings": [],
        "path_literals": [],
        "repo_path_builds": [],
        "ast_source_readers": [],
        "importlib_strings": [],
    }

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except OSError:
        return results

    # Pre-compile patterns relative to this old_mod / old_slashpath
    # Pattern 1: Python imports
    re_import = re.compile(
        r"(?:^|\s)(import\s+" + re.escape(old_mod) + r"(?:\s|$|;))"
        r"|(?:^|\s)(from\s+" + re.escape(old_mod) + r"\s+import)"
        r"|(?:^|\s)(from\s+tools\s+import\s+" + re.escape(old_mod.split(".")[-1]) + r"(?:\s|,|$))"
    )

    # Pattern 2: monkeypatch / mock string references (quoted module prefix)
    # Matches: "tools.x.something" or 'tools.x.something' (may continue with .func etc.)
    re_monkeypatch = re.compile(
        r"""['"]{1}""" + re.escape(old_mod) + r"""(?:\.[A-Za-z_][A-Za-z0-9_]*)*['"]{1}"""
    )

    # Pattern 3: Path("tools/x.py") or Path('tools/x.py')
    re_path_literal = re.compile(
        r"""Path\s*\(\s*['"]""" + re.escape(old_slashpath) + r"""\.py['"]\s*\)"""
    )

    # Pattern 4: _REPO / "tools" / "x.py" style (chain of / operators)
    # Simplified: any string containing the basename with .py that appears after /
    basename = old_slashpath.split("/")[-1]
    re_repo_path = re.compile(
        r"""["']""" + re.escape(basename) + r"""\.py["']"""
    )

    # Pattern 5: ast.parse(Path(...).read_text) — heuristic: Path( near .read_text
    re_ast_source = re.compile(
        r"""ast\.parse\s*\("""
        + r""".*"""
        + re.escape(basename)
    )

    # Pattern 6: importlib.import_module("tools.x") or importlib.import_module('tools.x')
    re_importlib = re.compile(
        r"""importlib\.import_module\s*\(\s*['"]""" + re.escape(old_mod) + r"""['"]\s*\)"""
    )

    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\n")

        if re_import.search(line):
            results["import_statements"].append(
                {"line_no": lineno, "line_content": line.strip(), "pattern_type": "import"}
            )
        if re_monkeypatch.search(line):
            results["monkeypatch_strings"].append(
                {"line_no": lineno, "line_content": line.strip(), "pattern_type": "monkeypatch_string"}
            )
        if re_path_literal.search(line):
            results["path_literals"].append(
                {"line_no": lineno, "line_content": line.strip(), "pattern_type": "path_literal"}
            )
        if re_repo_path.search(line):
            results["repo_path_builds"].append(
                {"line_no": lineno, "line_content": line.strip(), "pattern_type": "repo_path_build"}
            )
        if re_ast_source.search(line):
            results["ast_source_readers"].append(
                {"line_no": lineno, "line_content": line.strip(), "pattern_type": "ast_source_reader"}
            )
        if re_importlib.search(line):
            results["importlib_strings"].append(
                {"line_no": lineno, "line_content": line.strip(), "pattern_type": "importlib_string"}
            )

    return results


def _scan_repo(
    repo_root: str,
    old_mod: str,
    old_slashpath: str,
) -> dict[str, dict[str, list[dict]]]:
    """
    Walk tools/ and tests/ directories, returning per-file pattern matches.
    """
    all_matches: dict[str, dict[str, list[dict]]] = {}
    for folder in SCAN_FOLDERS:
        folder_abs = os.path.join(repo_root, folder)
        if not os.path.isdir(folder_abs):
            continue
        for root, dirs, files in os.walk(folder_abs):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                matches = _detect_patterns_in_file(fpath, old_mod, old_slashpath)
                has_any = any(v for v in matches.values())
                if has_any:
                    rel = os.path.relpath(fpath, repo_root).replace("\\", "/")
                    all_matches[rel] = matches
    return all_matches


# ---------------------------------------------------------------------------
# Patch plan builder
# ---------------------------------------------------------------------------


def build_patch_plan(
    batch: dict[str, Any],
    repo_root: str,
) -> dict[str, Any]:
    """
    Build a complete migration_patch_plan for a single batch candidate.
    """
    source_paths: list[str] = batch.get("source_paths", [])
    target_paths: list[str] = batch.get("target_paths", [])

    # Build module rewrite map
    module_rewrite_map: dict[str, str] = {}
    file_path_rewrite_map: dict[str, str] = {}
    for sp, tp in zip(source_paths, target_paths):
        old_mod = sp.replace(".py", "").replace("/", ".")
        new_mod = tp.replace(".py", "").replace("/", ".")
        module_rewrite_map[old_mod] = new_mod
        file_path_rewrite_map[sp] = tp

    # Determine which __init__.py files are needed
    init_files_required: list[str] = []
    seen_target_dirs: set[str] = set()
    for tp in target_paths:
        target_dir = os.path.dirname(tp)
        if target_dir and target_dir not in seen_target_dirs:
            seen_target_dirs.add(target_dir)
            init_path = os.path.join(target_dir, "__init__.py").replace("\\", "/")
            full_init = os.path.join(repo_root, init_path)
            if not os.path.exists(full_init):
                init_files_required.append(init_path)

    # Aggregate per-file scan results across all moved modules
    affected_files: dict[str, dict] = {}
    monkeypatch_rewrites: list[dict] = []
    path_literal_rewrites: list[dict] = []
    dynamic_import_rewrites: list[dict] = []
    unresolved_patterns: list[dict] = []

    for old_mod, new_mod in module_rewrite_map.items():
        old_slashpath = _slashpath(old_mod)
        per_file = _scan_repo(repo_root, old_mod, old_slashpath)

        for rel_path, matches in per_file.items():
            if rel_path not in affected_files:
                affected_files[rel_path] = {
                    "import_statements": [],
                    "monkeypatch_strings": [],
                    "path_literals": [],
                    "repo_path_builds": [],
                    "ast_source_readers": [],
                    "importlib_strings": [],
                }
            for pat_type, hits in matches.items():
                affected_files[rel_path][pat_type].extend(hits)

            # Build monkeypatch_rewrites list
            for hit in matches["monkeypatch_strings"]:
                raw = hit["line_content"]
                new_raw = raw.replace(old_mod, new_mod)
                monkeypatch_rewrites.append({
                    "file": rel_path,
                    "line_no": hit["line_no"],
                    "old_string": old_mod,
                    "new_string": new_mod,
                    "line_before": raw,
                    "line_after": new_raw,
                })

            # Build path_literal_rewrites list
            for hit in matches["path_literals"]:
                raw = hit["line_content"]
                old_slash = old_slashpath
                new_slash = _slashpath(new_mod)
                new_raw = raw.replace(old_slash + ".py", new_slash + ".py")
                path_literal_rewrites.append({
                    "file": rel_path,
                    "line_no": hit["line_no"],
                    "old_path": old_slash + ".py",
                    "new_path": new_slash + ".py",
                    "line_before": raw,
                    "line_after": new_raw,
                    "recommendation": "Replace with: import <module>; Path(module.__file__).read_text(...)",
                })

            # Repo path builds - flag as unresolved (need dynamic fix)
            for hit in matches["repo_path_builds"]:
                unresolved_patterns.append({
                    "file": rel_path,
                    "line_no": hit["line_no"],
                    "pattern_type": "repo_path_build",
                    "line_content": hit["line_content"],
                    "recommendation": (
                        "Replace _REPO / 'tools' / 'x.py' with Path(module.__file__) "
                        "after importing the module."
                    ),
                })

            # AST source readers - flag
            for hit in matches["ast_source_readers"]:
                unresolved_patterns.append({
                    "file": rel_path,
                    "line_no": hit["line_no"],
                    "pattern_type": "ast_source_reader",
                    "line_content": hit["line_content"],
                    "recommendation": (
                        "Import the module and use Path(module.__file__).read_text() "
                        "instead of a hardcoded path."
                    ),
                })

            # Dynamic import rewrites
            for hit in matches["importlib_strings"]:
                raw = hit["line_content"]
                new_raw = raw.replace(old_mod, new_mod)
                dynamic_import_rewrites.append({
                    "file": rel_path,
                    "line_no": hit["line_no"],
                    "old_module": old_mod,
                    "new_module": new_mod,
                    "line_before": raw,
                    "line_after": new_raw,
                })

    # Sort for determinism
    sorted_affected = dict(sorted(affected_files.items()))
    monkeypatch_rewrites.sort(key=lambda x: (x["file"], x["line_no"]))
    path_literal_rewrites.sort(key=lambda x: (x["file"], x["line_no"]))
    dynamic_import_rewrites.sort(key=lambda x: (x["file"], x["line_no"]))
    unresolved_patterns.sort(key=lambda x: (x["file"], x["line_no"]))
    init_files_required.sort()

    test_files = sorted(batch.get("affected_tests", []))

    # Build pre-move patch recommendations
    pre_move_patch_recommendations: list[str] = []
    if monkeypatch_rewrites:
        pre_move_patch_recommendations.append(
            f"Rewrite {len(monkeypatch_rewrites)} monkeypatch string literal(s) before or during move."
        )
    if path_literal_rewrites:
        pre_move_patch_recommendations.append(
            f"Rewrite {len(path_literal_rewrites)} Path('tools/x.py') literal(s) to use module.__file__."
        )
    if dynamic_import_rewrites:
        pre_move_patch_recommendations.append(
            f"Rewrite {len(dynamic_import_rewrites)} importlib.import_module string(s)."
        )
    if unresolved_patterns:
        pre_move_patch_recommendations.append(
            f"Manually review {len(unresolved_patterns)} unresolved pattern(s) before move."
        )
    if init_files_required:
        pre_move_patch_recommendations.append(
            f"Create __init__.py in {len(init_files_required)} target director(ies): {init_files_required}."
        )

    post_move_validation_commands = (
        batch.get("compile_commands", [])
        + batch.get("pytest_commands", [])
        + batch.get("reference_validation_commands", [])
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "batch_id": batch["batch_id"],
        "risk_level": batch.get("risk_level", "UNKNOWN"),
        "approval_required": batch.get("approval_required", False),
        "source_paths": source_paths,
        "target_paths": target_paths,
        "module_rewrite_map": module_rewrite_map,
        "file_path_rewrite_map": file_path_rewrite_map,
        "affected_files": sorted_affected,
        "test_files": test_files,
        "monkeypatch_rewrites": monkeypatch_rewrites,
        "path_literal_rewrites": path_literal_rewrites,
        "dynamic_import_rewrites": dynamic_import_rewrites,
        "init_files_required": init_files_required,
        "pre_move_patch_recommendations": pre_move_patch_recommendations,
        "post_move_validation_commands": post_move_validation_commands,
        "unresolved_patterns": unresolved_patterns,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="AIROS v2 Migration Analyzer")
    parser.add_argument(
        "--batch-candidates",
        required=True,
        help="Path to batch_candidates.json",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Specific batch ID to analyze (defaults to recommended_next_batch)",
    )
    parser.add_argument(
        "--output",
        default="docs/operations/repository/migration_patch_plan.json",
        help="Output path for migration_patch_plan.json",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Path to repository root",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo_root)
    candidates_path = os.path.join(repo_root, args.batch_candidates) if not os.path.isabs(args.batch_candidates) else args.batch_candidates

    if not os.path.exists(candidates_path):
        print(f"Error: batch_candidates file not found: {candidates_path}", file=sys.stderr)
        sys.exit(1)

    with open(candidates_path, "r", encoding="utf-8") as fh:
        candidates_data = json.load(fh)

    batch_id = args.batch_id or candidates_data.get("recommended_next_batch")
    if not batch_id:
        print("Error: No batch_id specified and no recommended_next_batch in candidates file.", file=sys.stderr)
        sys.exit(1)

    target_batch = None
    for cand in candidates_data.get("candidates", []):
        if cand["batch_id"] == batch_id:
            target_batch = cand
            break

    if not target_batch:
        print(f"Error: Batch '{batch_id}' not found in candidates file.", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing batch: {batch_id}")
    patch_plan = build_patch_plan(target_batch, repo_root)

    output_path = os.path.join(repo_root, args.output) if not os.path.isabs(args.output) else args.output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    indent = 2 if args.pretty else None
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(patch_plan, fh, indent=indent, ensure_ascii=False)
        fh.write("\n")

    print(f"Patch plan written to: {output_path}")

    # Summary
    print(f"\n--- PATCH PLAN SUMMARY ---")
    print(f"  Batch:                {patch_plan['batch_id']}")
    print(f"  Risk level:           {patch_plan['risk_level']}")
    print(f"  Files to move:        {len(patch_plan['source_paths'])}")
    print(f"  Affected files:       {len(patch_plan['affected_files'])}")
    print(f"  Monkeypatch rewrites: {len(patch_plan['monkeypatch_rewrites'])}")
    print(f"  Path literal rewrites:{len(patch_plan['path_literal_rewrites'])}")
    print(f"  Dynamic import fixes: {len(patch_plan['dynamic_import_rewrites'])}")
    print(f"  __init__.py required: {len(patch_plan['init_files_required'])}")
    print(f"  Unresolved patterns:  {len(patch_plan['unresolved_patterns'])}")
    if patch_plan["pre_move_patch_recommendations"]:
        print(f"\n--- RECOMMENDATIONS ---")
        for rec in patch_plan["pre_move_patch_recommendations"]:
            print(f"  * {rec}")


if __name__ == "__main__":
    main()
