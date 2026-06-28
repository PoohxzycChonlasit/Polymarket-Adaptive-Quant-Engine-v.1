#!/usr/bin/env python3
"""
AIROS v2 Dependency Graph Builder.
Loads repository_index.json and test_registry.json, resolves python imports,
builds direct/reverse dependency linkages, calculates blast radius, and writes dependency_graph.json.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone

SCHEMA_VERSION = "dependency_graph_v1"

# Internal package prefixes
INTERNAL_PREFIXES = ("tools", "polymarket", "config", "utils")


def resolve_import(import_name, file_index):
    """
    Resolve a python import string to a relative file path in the repo index.
    Returns (resolved_path, is_internal).
    """
    if not any(import_name.startswith(p) for p in INTERNAL_PREFIXES):
        return None, False

    # Standard dot-to-slash conversion
    path_proposal = import_name.replace(".", "/") + ".py"
    if path_proposal in file_index:
        return path_proposal, True

    # Check if it could be a root tools module (e.g. tools.my_script -> tools/my_script.py)
    parts = import_name.split(".")
    if len(parts) == 2 and parts[0] == "tools":
        root_proposal = f"tools/{parts[1]}.py"
        if root_proposal in file_index:
            return root_proposal, True

    # If it starts with our internal package but doesn't resolve to a file
    return None, True


def build_graph(index_data, test_data):
    """Analyze imports and construct the dependency graph with risk/blast metrics."""
    nodes = sorted(list(index_data.keys()))
    edges = []
    
    # Adjacency matrices
    direct_imports_by_file = {}
    reverse_importers = {node: [] for node in nodes}
    unresolved_imports = {}
    
    for node in nodes:
        meta = index_data[node]
        direct_imports_by_file[node] = []
        unresolved_imports[node] = {
            "unresolved_external": [],
            "unresolved_internal": [],
        }
        
        if not meta["is_tool"] and not meta["category"] in ("runtime", "tests"):
            # Only resolve imports for code files
            continue
            
        for imp in meta.get("direct_imports", []):
            resolved_path, is_internal = resolve_import(imp, index_data)
            if resolved_path:
                edges.append([node, resolved_path])
                direct_imports_by_file[node].append(resolved_path)
                reverse_importers[resolved_path].append(node)
            elif is_internal:
                unresolved_imports[node]["unresolved_internal"].append(imp)
            else:
                unresolved_imports[node]["unresolved_external"].append(imp)

    # De-duplicate and sort edges/relationships
    sorted_edges = sorted(list(set(tuple(e) for e in edges)))
    edges_list = [list(e) for e in sorted_edges]

    for k in direct_imports_by_file:
        direct_imports_by_file[k] = sorted(list(set(direct_imports_by_file[k])))
        
    for k in reverse_importers:
        reverse_importers[k] = sorted(list(set(reverse_importers[k])))
        
    for k in unresolved_imports:
        unresolved_imports[k]["unresolved_external"] = sorted(list(set(unresolved_imports[k]["unresolved_external"])))
        unresolved_imports[k]["unresolved_internal"] = sorted(list(set(unresolved_imports[k]["unresolved_internal"])))

    # Link test relationships
    source_to_test = test_data.get("source_to_test", {})
    test_to_source = test_data.get("test_to_source", {})
    
    # Runtime sensitive nodes
    runtime_sensitive_nodes = sorted([n for n, m in index_data.items() if m.get("is_runtime_sensitive", False)])

    # Compute migration safety summary
    migration_safety_summary = {}
    for node in nodes:
        meta = index_data[node]
        
        # Risk factor based on sensitive code
        is_sensitive = meta.get("is_runtime_sensitive", False)
        risk_multiplier = 3 if is_sensitive else 1
        
        # Dependency count is inbound (reverse) + outbound direct internal dependencies
        inbound_count = len(reverse_importers.get(node, []))
        outbound_count = len(direct_imports_by_file.get(node, []))
        dep_count = inbound_count + outbound_count
        
        blast_radius = dep_count * risk_multiplier
        
        # Safety level mapping
        if is_sensitive or meta["category"] == "runtime":
            status = "DO_NOT_MOVE"
        elif blast_radius <= 3:
            status = "SAFE_ATOMIC"
        elif blast_radius <= 7:
            status = "MEDIUM_ATOMIC"
        elif blast_radius <= 11:
            status = "PLAN_REQUIRED"
        else:
            status = "DO_NOT_MOVE"
            
        migration_safety_summary[node] = {
            "blast_radius_score": blast_radius,
            "migration_safety_status": status,
            "inbound_dependencies_count": inbound_count,
            "outbound_dependencies_count": outbound_count,
        }

    graph_data = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "node_count": len(nodes),
        "edge_count": len(edges_list),
        "nodes": nodes,
        "edges": edges_list,
        "reverse_importers": reverse_importers,
        "direct_imports_by_file": direct_imports_by_file,
        "tests_by_file": source_to_test,
        "files_by_test": test_to_source,
        "unresolved_imports": unresolved_imports,
        "runtime_sensitive_nodes": runtime_sensitive_nodes,
        "migration_safety_summary": migration_safety_summary,
    }
    
    return graph_data


def main():
    parser = argparse.ArgumentParser(description="AIROS v2 Dependency Graph Builder")
    parser.add_argument(
        "--input-dir",
        default=".",
        help="Directory containing repository_index.json and test_registry.json",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print output JSON file",
    )
    
    args = parser.parse_args()
    
    index_file = os.path.join(args.input_dir, "repository_index.json")
    test_file = os.path.join(args.input_dir, "test_registry.json")
    
    if not os.path.exists(index_file) or not os.path.exists(test_file):
        print(f"Error: Missing index or test registry files in '{args.input_dir}'.", file=sys.stderr)
        sys.exit(1)
        
    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)
        
    with open(test_file, "r", encoding="utf-8") as f:
        test_data = json.load(f)
        
    graph_data = build_graph(index_data, test_data)
    
    out_file = os.path.join(args.input_dir, "dependency_graph.json")
    indent = 2 if args.pretty else None
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=indent, sort_keys=True)
        
    print(f"Generated: {out_file}")


if __name__ == "__main__":
    main()
