#!/usr/bin/env python3
"""
AIROS v2 Batch Generator.
Consumes repository_index.json, dependency_graph.json, and test_registry.json,
clusters root tools into risk-aware target batch candidates, and writes batch_candidates.json.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone

SCHEMA_VERSION = "batch_candidates_v1"

# Ignored subfolders under tools/
EXCLUDED_TOOLS_SUBFOLDERS = {"airos", "backtest_engine_v2", "flaos"}


def is_root_tool(rel_path, file_meta):
    """Check if file is a tool currently located directly in the root tools/ folder."""
    if not file_meta.get("is_tool", False):
        return False
    parts = rel_path.split("/")
    # Must be tools/file.py (length 2)
    return len(parts) == 2 and parts[0] == "tools"


def generate_validation_commands(source_paths, target_paths, test_files):
    """Generate py_compile, pytest, and ref check commands for verification."""
    compiles = [f".venv\\Scripts\\python.exe -m py_compile {tp.replace('/', os.sep)}" for tp in target_paths]
    
    # Pytest commands for affected tests
    pytest_cmds = []
    if test_files:
        pytest_cmds = [f".venv\\Scripts\\python.exe -m pytest {tf.replace('/', os.sep)} -q" for tf in sorted(test_files)]
        
    # Reference checks
    ref_checks = []
    for sp in sorted(source_paths):
        mod_name = sp.replace(".py", "").replace("/", ".")
        ref_checks.append(f"git grep \"{mod_name}\"")
        
    return compiles, pytest_cmds, ref_checks


def generate_rollback_commands(source_paths, target_paths, test_files):
    """Generate git mv and checkout commands to undo migration actions."""
    rollbacks = []
    for sp, tp in zip(source_paths, target_paths):
        rollbacks.append(f"git mv {tp.replace('/', os.sep)} {sp.replace('/', os.sep)}")
    
    checkouts = ["git checkout -- docs/operations/ACTIVE_WORKFLOW_STATE_001.json docs/operations/TASK_QUEUE_001.json"]
    if test_files:
        checkouts.append("git checkout -- " + " ".join(tf.replace('/', os.sep) for tf in sorted(test_files)))
        
    rollbacks.extend(checkouts)
    return rollbacks


def build_candidates(index_data, graph_data):
    """Cluster eligible root-level tools by domain and analyze batch migration risks."""
    nodes = graph_data.get("nodes", [])
    safety_summary = graph_data.get("migration_safety_summary", {})
    source_to_test = graph_data.get("tests_by_file", {})
    
    # 1. Group candidates by domain
    domain_groups = {}
    deferred_files = []
    
    for node in nodes:
        meta = index_data.get(node, {})
        if is_root_tool(node, meta):
            safety_meta = safety_summary.get(node, {})
            status = safety_meta.get("migration_safety_status", "DO_NOT_MOVE")
            
            if status == "DO_NOT_MOVE":
                deferred_files.append({
                    "path": node,
                    "reason": "FLAGGED_DO_NOT_MOVE_BY_GRAPH_METRICS"
                })
                continue
                
            domain = meta.get("domain", "unknown")
            domain_groups.setdefault(domain, []).append(node)

    # 2. Compile candidate batches
    candidates = []
    batch_counter = 1
    
    for domain, files in sorted(domain_groups.items()):
        if not files:
            continue
            
        source_paths = sorted(files)
        target_paths = [f"tools/{domain}/{os.path.basename(p)}" for p in source_paths]
        
        # Gather all affected tests and imports
        batch_tests = set()
        affected_imports = []
        
        # Check overall batch risk
        batch_risk = "SAFE_ATOMIC"
        has_unresolved_internal = False
        
        for p in source_paths:
            # Map tests
            tests = source_to_test.get(p, [])
            batch_tests.update(tests)
            
            # Map imports to rewrite
            mod_name = p.replace(".py", "").replace("/", ".")
            affected_imports.append(mod_name)
            
            # Check individual safety metrics
            safety_meta = safety_summary.get(p, {})
            status = safety_meta.get("migration_safety_status", "SAFE_ATOMIC")
            
            # Unresolved internal check
            unresolved = graph_data.get("unresolved_imports", {}).get(p, {})
            if unresolved.get("unresolved_internal", []):
                has_unresolved_internal = True
                
            if status == "PLAN_REQUIRED":
                batch_risk = "PLAN_REQUIRED"
            elif status == "MEDIUM_ATOMIC" and batch_risk == "SAFE_ATOMIC":
                batch_risk = "MEDIUM_ATOMIC"

        if has_unresolved_internal:
            batch_risk = "PLAN_REQUIRED"

        # Apply batch size limits
        # Max SAFE_ATOMIC size: 30 files; Max MEDIUM_ATOMIC size: 15 files.
        limit = 30 if batch_risk == "SAFE_ATOMIC" else 15
        if len(source_paths) > limit:
            # Split candidate or flag PLAN_REQUIRED due to size
            batch_risk = "PLAN_REQUIRED"

        batch_id = f"REPOSITORY_PHASE1_{domain.upper()}_BATCH_{batch_counter:03d}"
        batch_counter += 1
        
        compiles, pytests, ref_checks = generate_validation_commands(source_paths, target_paths, batch_tests)
        rollbacks = generate_rollback_commands(source_paths, target_paths, batch_tests)
        
        approval_required = batch_risk in ("PLAN_REQUIRED", "DO_NOT_MOVE")
        blocked_by = []
        if approval_required:
            blocked_by.append(f"{batch_id}_PLAN_001")
            
        candidate_batch = {
            "batch_id": batch_id,
            "batch_type": "TOOLS_ORGANIZATION",
            "risk_level": batch_risk,
            "confidence": "HIGH" if batch_risk in ("SAFE_ATOMIC", "MEDIUM_ATOMIC") else "MEDIUM",
            "source_paths": source_paths,
            "target_paths": target_paths,
            "reason": f"Atomic consolidation of root level tools into target tools/{domain}/ domain subfolder.",
            "affected_imports": sorted(affected_imports),
            "affected_tests": sorted(list(batch_tests)),
            "compile_commands": compiles,
            "pytest_commands": pytests,
            "reference_validation_commands": ref_checks,
            "rollback_commands": rollbacks,
            "commit_message": f"refactor(batch): relocate {domain} tools",
            "approval_required": approval_required,
            "blocked_by": blocked_by,
        }
        
        candidates.append(candidate_batch)

    # 3. Formulate recommended next batch
    recommended = None
    # Prioritize SAFE_ATOMIC batches, then MEDIUM_ATOMIC, then PLAN_REQUIRED
    for risk in ("SAFE_ATOMIC", "MEDIUM_ATOMIC", "PLAN_REQUIRED"):
        for cand in candidates:
            if cand["risk_level"] == risk:
                recommended = cand["batch_id"]
                break
        if recommended:
            break

    # Build safety summary metrics
    safety_summary_metrics = {
        "total_safe_atomic_batches": sum(1 for c in candidates if c["risk_level"] == "SAFE_ATOMIC"),
        "total_medium_atomic_batches": sum(1 for c in candidates if c["risk_level"] == "MEDIUM_ATOMIC"),
        "total_plan_required_batches": sum(1 for c in candidates if c["risk_level"] == "PLAN_REQUIRED"),
        "total_deferred_files": len(deferred_files),
    }

    batch_output = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_files": nodes,
        "batch_count": len(candidates),
        "candidates": candidates,
        "deferred_files": sorted(deferred_files, key=lambda x: x["path"]),
        "safety_summary": safety_summary_metrics,
        "recommended_next_batch": recommended,
    }
    
    return batch_output


def main():
    parser = argparse.ArgumentParser(description="AIROS v2 Batch Generator")
    parser.add_argument(
        "--input-dir",
        default=".",
        help="Directory containing repository_index.json and dependency_graph.json",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print output JSON file",
    )
    
    args = parser.parse_args()
    
    index_file = os.path.join(args.input_dir, "repository_index.json")
    graph_file = os.path.join(args.input_dir, "dependency_graph.json")
    
    if not os.path.exists(index_file) or not os.path.exists(graph_file):
        print(f"Error: Missing index or dependency graph in '{args.input_dir}'.", file=sys.stderr)
        sys.exit(1)
        
    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)
        
    with open(graph_file, "r", encoding="utf-8") as f:
        graph_data = json.load(f)
        
    batch_candidates = build_candidates(index_data, graph_data)
    
    out_file = os.path.join(args.input_dir, "batch_candidates.json")
    indent = 2 if args.pretty else None
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(batch_candidates, f, indent=indent, sort_keys=True)
        
    print(f"Generated: {out_file}")


if __name__ == "__main__":
    main()
