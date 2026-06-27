"""
FLAOS Runtime Knowledge Graph Query Tool.

Reads seeded JSONL graph files and provides structured query outputs
for Execution Contract knowledge_graph_evidence fields.

Standard library only. No polymarket imports.

Usage:
    python tools/flaos/knowledge_graph.py graph-health
    python tools/flaos/knowledge_graph.py safety-check TARGET
    python tools/flaos/knowledge_graph.py blast-radius TARGET
    python tools/flaos/knowledge_graph.py evidence-for-commit COMMIT_HASH
    python tools/flaos/knowledge_graph.py why-deferred TARGET
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
GRAPH_DIR = ROOT / "docs" / "operations" / "knowledge_graph"
NODES_FILE = GRAPH_DIR / "REPO_GRAPH_NODES_001.jsonl"
EDGES_FILE = GRAPH_DIR / "REPO_GRAPH_EDGES_001.jsonl"
INDEX_FILE = GRAPH_DIR / "GRAPH_INDEX_001.json"

CRITICAL_EDGE_TYPES = {"protects", "blocks"}
STOP_SEVERITY = {"CRITICAL"}

# Aliases: short name substring → node_id patterns to search
ALIAS_FIELDS = ("name", "node_id", "sha")


# ---------------------------------------------------------------------------
# Graph loader
# ---------------------------------------------------------------------------

class KnowledgeGraph:
    """In-memory graph loaded from JSONL seed files."""

    def __init__(self, nodes_path: Path = NODES_FILE, edges_path: Path = EDGES_FILE) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        # adjacency: from_node → list of edges
        self.adj_out: dict[str, list[dict]] = defaultdict(list)
        # reverse adjacency: to_node → list of edges
        self.adj_in: dict[str, list[dict]] = defaultdict(list)
        self._load(nodes_path, edges_path)

    def _load(self, nodes_path: Path, edges_path: Path) -> None:
        if not nodes_path.exists():
            raise FileNotFoundError(f"Nodes file not found: {nodes_path}")
        if not edges_path.exists():
            raise FileNotFoundError(f"Edges file not found: {edges_path}")
        for line in nodes_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                n = json.loads(line)
                self.nodes[n["node_id"]] = n
        for line in edges_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                e = json.loads(line)
                self.edges.append(e)
                self.adj_out[e.get("from_node", "")].append(e)
                self.adj_in[e.get("to_node", "")].append(e)

    # ------------------------------------------------------------------
    # Node resolution
    # ------------------------------------------------------------------

    def resolve(self, target: str) -> str | None:
        """Resolve a short name or full node_id to a node_id in the graph."""
        if target in self.nodes:
            return target
        # Exact sha match (for commits)
        for nid, node in self.nodes.items():
            if node.get("sha") == target:
                return nid
        # Substring match on name or node_id
        lower = target.lower()
        candidates = [
            nid for nid, node in self.nodes.items()
            if lower in node.get("name", "").lower() or lower in nid.lower()
        ]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            # Prefer exact name match
            for c in candidates:
                if self.nodes[c].get("name", "").lower() == lower:
                    return c
            return candidates[0]
        return None

    # ------------------------------------------------------------------
    # Safety check
    # ------------------------------------------------------------------

    def safety_check(self, target_id: str) -> dict[str, Any]:
        """Return safety findings for a resolved node_id."""
        node = self.nodes.get(target_id, {})
        findings = []
        # 1. Check is_permanent flag
        if node.get("is_permanent"):
            findings.append({
                "rule": "PERMANENT_FLAG",
                "reason": node.get("permanent_reason", "is_permanent=true in graph"),
                "severity": "CRITICAL",
                "source": "node_flag",
            })
        # 2. Find QS nodes with protects/blocks edges to target
        for edge in self.adj_in.get(target_id, []):
            if edge.get("edge_type") in CRITICAL_EDGE_TYPES:
                from_node = edge.get("from_node", "")
                from_data = self.nodes.get(from_node, {})
                if from_data.get("node_type") == "safety_rule":
                    findings.append({
                        "rule": from_data.get("name", from_node),
                        "reason": edge.get("notes", from_data.get("summary", "")),
                        "severity": from_data.get("severity", "CRITICAL"),
                        "edge_type": edge.get("edge_type"),
                        "edge_id": edge.get("edge_id"),
                        "source": "graph_edge",
                    })
        return findings

    # ------------------------------------------------------------------
    # BFS traversal
    # ------------------------------------------------------------------

    def bfs_from(self, start_id: str, max_depth: int = 3,
                 edge_types: set[str] | None = None) -> list[dict[str, Any]]:
        """BFS outbound from start node. Returns list of (node, edge) pairs visited."""
        visited: set[str] = {start_id}
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])
        results = []
        while queue:
            node_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in self.adj_out.get(node_id, []):
                etype = edge.get("edge_type", "")
                if edge_types and etype not in edge_types:
                    continue
                to_id = edge.get("to_node", "")
                if to_id and to_id not in visited:
                    visited.add(to_id)
                    queue.append((to_id, depth + 1))
                    results.append({"node": self.nodes.get(to_id, {"node_id": to_id}), "edge": edge})
        return results

    def bfs_reverse(self, start_id: str, max_depth: int = 3,
                    edge_types: set[str] | None = None) -> list[dict[str, Any]]:
        """BFS inbound (callers of start node)."""
        visited: set[str] = {start_id}
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])
        results = []
        while queue:
            node_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in self.adj_in.get(node_id, []):
                etype = edge.get("edge_type", "")
                if edge_types and etype not in edge_types:
                    continue
                from_id = edge.get("from_node", "")
                if from_id and from_id not in visited:
                    visited.add(from_id)
                    queue.append((from_id, depth + 1))
                    results.append({"node": self.nodes.get(from_id, {"node_id": from_id}), "edge": edge})
        return results


# ---------------------------------------------------------------------------
# Output builder
# ---------------------------------------------------------------------------

def _output(query_type: str, target: str, status: str, safety_findings: list,
            affected_nodes: list, affected_edges: list, evidence: list,
            recommended_tier: str, stop_conditions: list,
            confidence: float, fallback_required: bool,
            extra: dict | None = None) -> dict[str, Any]:
    attachment = {
        "graph_query_type": query_type,
        "graph_confidence": confidence,
        "safety_findings_count": len(safety_findings),
        "safety_findings": [f.get("rule", "") + ": " + f.get("reason", "")[:80] for f in safety_findings],
        "affected_nodes_count": len(affected_nodes),
        "affected_edges_count": len(affected_edges),
        "blast_radius_score": "HIGH" if len(affected_nodes) > 5 else ("MEDIUM" if len(affected_nodes) > 2 else "LOW"),
        "recommended_workflow_tier": recommended_tier,
        "fallback_required": fallback_required,
        "status": status,
    }
    result = {
        "$schema": "rkg_query_output_v1",
        "query_type": query_type,
        "target": target,
        "status": status,
        "safety_findings": safety_findings,
        "affected_nodes": affected_nodes,
        "affected_edges": affected_edges,
        "evidence": evidence,
        "recommended_workflow_tier": recommended_tier,
        "stop_conditions": stop_conditions,
        "confidence": confidence,
        "fallback_required": fallback_required,
        "execution_contract_attachment": attachment,
    }
    if extra:
        result.update(extra)
    return result


# ---------------------------------------------------------------------------
# Query implementations
# ---------------------------------------------------------------------------

def cmd_safety_check(graph: KnowledgeGraph, target: str, pretty: bool) -> int:
    target_id = graph.resolve(target)
    if not target_id:
        result = _output("safety_check", target, "DEGRADED", [], [], [], [],
                        "LOOP", ["TARGET_NOT_IN_GRAPH"], 0.0, True,
                        {"degraded_reason": f"Node '{target}' not found in graph"})
        _print(result, pretty)
        return 0

    findings = graph.safety_check(target_id)
    has_critical = any(f.get("severity") in STOP_SEVERITY for f in findings)
    status = "STOP_REQUIRED" if has_critical else ("GATE" if findings else "PASS")
    tier = "GATE" if findings else "LOOP"
    stops = ["QS_CRITICAL_FOUND"] if has_critical else []

    node = graph.nodes[target_id]
    affected_nodes = [target_id] + [f.get("rule", "") for f in findings]
    affected_edges = [f.get("edge_id", "") for f in findings if f.get("edge_id")]

    result = _output("safety_check", target, status, findings, affected_nodes, affected_edges,
                     [{"description": node.get("summary", ""), "grade": node.get("evidence_grade", "D")}],
                     tier, stops, node.get("confidence", 0.9), False)
    _print(result, pretty)
    return 0


def cmd_blast_radius(graph: KnowledgeGraph, target: str, pretty: bool) -> int:
    target_id = graph.resolve(target)
    if not target_id:
        result = _output("blast_radius", target, "DEGRADED", [], [], [], [],
                        "LOOP", ["TARGET_NOT_IN_GRAPH"], 0.0, True)
        _print(result, pretty)
        return 0

    # Safety check first
    findings = graph.safety_check(target_id)
    has_critical = any(f.get("severity") in STOP_SEVERITY for f in findings)

    # Outbound traversal (what this node depends on)
    out_results = graph.bfs_from(target_id, max_depth=3)
    # Inbound traversal (who calls/depends on this node)
    in_results = graph.bfs_reverse(target_id, max_depth=3,
                                   edge_types={"calls", "depends_on", "owns"})

    affected_nodes = list({r["node"]["node_id"] for r in out_results + in_results})
    affected_edges = [r["edge"]["edge_id"] for r in out_results + in_results if "edge_id" in r["edge"]]

    node = graph.nodes[target_id]
    evidence = []
    # Collect validation evidence linked to commits that touched this node
    touched_commits = [r for r in in_results if r["node"].get("node_type") == "commit"]
    for tc in touched_commits:
        cid = tc["node"]["node_id"]
        val_edges = [e for e in graph.adj_out.get(cid, []) if e.get("edge_type") == "validated_by"]
        for ve in val_edges:
            vnode = graph.nodes.get(ve.get("to_node", ""), {})
            evidence.append({"node_id": ve["to_node"], "grade": vnode.get("evidence_grade", "B"),
                             "description": f"Commit {cid} validated"})

    status = "STOP_REQUIRED" if has_critical else "PASS"
    tier = "GATE" if (has_critical or len(affected_nodes) > 5) else ("STANDARD" if len(affected_nodes) > 2 else "LOOP")
    stops = (["QS_CRITICAL_FOUND"] if has_critical else []) + (["DEFERRED_TARGET"] if node.get("is_deferred") else [])
    conf = min(1.0, 0.9 - (0.1 * sum(1 for r in out_results + in_results if r["edge"].get("confidence", 1.0) < 0.7)))

    extra = {
        "is_permanent": node.get("is_permanent", False),
        "is_deferred": node.get("is_deferred", False),
        "safe_extraction_score": node.get("safe_extraction_score"),
        "deferred_batch": node.get("deferred_batch"),
    }
    result = _output("blast_radius", target, status, findings, affected_nodes, affected_edges,
                     evidence, tier, stops, conf, False, extra)
    _print(result, pretty)
    return 0


def cmd_evidence_for_commit(graph: KnowledgeGraph, commit_hash: str, pretty: bool) -> int:
    target_id = graph.resolve(commit_hash)
    if not target_id or graph.nodes.get(target_id, {}).get("node_type") != "commit":
        result = _output("evidence_for_commit", commit_hash, "DEGRADED", [], [], [], [],
                        "LOOP", ["COMMIT_NOT_IN_GRAPH"], 0.0, True,
                        {"degraded_reason": f"Commit '{commit_hash}' not found in graph"})
        _print(result, pretty)
        return 0

    commit_node = graph.nodes[target_id]
    evidence = []
    affected_nodes = []
    affected_edges = []

    # generated_report edges
    for edge in graph.adj_out.get(target_id, []):
        if edge.get("edge_type") == "generated_report":
            rnode = graph.nodes.get(edge["to_node"], {})
            evidence.append({"node_id": edge["to_node"], "grade": rnode.get("evidence_grade", "C"),
                             "type": "report", "description": rnode.get("name", edge["to_node"])})
            affected_nodes.append(edge["to_node"])
            affected_edges.append(edge.get("edge_id", ""))

    # validated_by edges (commit → rtval)
    for edge in graph.adj_out.get(target_id, []):
        if edge.get("edge_type") == "validated_by":
            vnode = graph.nodes.get(edge["to_node"], {})
            desc = f"cycles={vnode.get('cycles')}, exit={vnode.get('exit_code')}, jsonl_events={vnode.get('jsonl_events')}"
            evidence.append({"node_id": edge["to_node"], "grade": vnode.get("evidence_grade", "A"),
                             "type": "runtime_validation", "description": desc})
            affected_nodes.append(edge["to_node"])
            affected_edges.append(edge.get("edge_id", ""))

    grades = {"A": 4, "B": 3, "C": 2, "D": 1}
    best_grade = max((e.get("grade", "D") for e in evidence), key=lambda g: grades.get(g, 0), default="D")
    status = "PASS" if evidence else "DEGRADED"

    result = _output("evidence_for_commit", commit_hash, status, [], affected_nodes, affected_edges,
                     evidence, "LOOP", [], 1.0, False,
                     {"batch": commit_node.get("batch"), "aggregate_grade": best_grade,
                      "message": commit_node.get("message", "")})
    _print(result, pretty)
    return 0


def cmd_why_deferred(graph: KnowledgeGraph, target: str, pretty: bool) -> int:
    target_id = graph.resolve(target)
    if not target_id:
        result = _output("why_deferred", target, "DEGRADED", [], [], [], [],
                        "LOOP", ["TARGET_NOT_IN_GRAPH"], 0.0, True)
        _print(result, pretty)
        return 0

    node = graph.nodes[target_id]
    affected_nodes = [target_id]
    affected_edges = []
    evidence = []
    deferred_info: dict[str, Any] = {}

    def add_unique(items: list[str], item: str | None) -> None:
        if item and item not in items:
            items.append(item)

    def display_name(node_id: str) -> str:
        graph_node = graph.nodes.get(node_id, {})
        return graph_node.get("name") or node_id.rsplit(".", 1)[-1].split(":", 1)[-1]

    suffix = target_id.split(":", 1)[-1]
    audit_ids: list[str] = []
    deferred_edges: list[dict[str, Any]] = []

    if node.get("node_type") == "audit":
        add_unique(audit_ids, target_id)

    audit_guess = f"audit:{suffix}"
    if audit_guess in graph.nodes:
        add_unique(audit_ids, audit_guess)

    # Gather direct deferral edges for function targets and audit-linked task targets.
    for edge in graph.edges:
        if edge.get("edge_type") != "deferred_by":
            continue
        from_node = edge.get("from_node", "")
        to_node = edge.get("to_node", "")
        if from_node == target_id or to_node == target_id or to_node in audit_ids:
            deferred_edges.append(edge)
            add_unique(audit_ids, to_node if graph.nodes.get(to_node, {}).get("node_type") == "audit" else None)

    # Once an audit is identified, include all methods deferred by that audit.
    for audit_id in list(audit_ids):
        for edge in graph.adj_in.get(audit_id, []):
            if edge.get("edge_type") == "deferred_by" and edge not in deferred_edges:
                deferred_edges.append(edge)

    deferred_methods = []
    deferred_method_nodes = []
    for edge in deferred_edges:
        audit_id = edge.get("to_node", "")
        audit_node = graph.nodes.get(audit_id, {})
        method_id = edge.get("from_node", "")
        add_unique(deferred_method_nodes, method_id)
        add_unique(deferred_methods, display_name(method_id))
        add_unique(affected_nodes, method_id)
        add_unique(affected_nodes, audit_id)
        add_unique(affected_edges, edge.get("edge_id", ""))
        if audit_node.get("node_type") == "audit":
            add_unique(audit_ids, audit_id)

    for audit_id in audit_ids:
        audit_node = graph.nodes.get(audit_id, {})
        if not audit_node:
            continue
        verdict = audit_node.get("verdict", "UNKNOWN")
        deferred_info.setdefault("deferred_by", audit_id)
        deferred_info.setdefault("gate_verdict", verdict)
        evidence.append({
            "node_id": audit_id,
            "grade": audit_node.get("evidence_grade", "B"),
            "type": "audit",
            "description": f"Gate verdict: {verdict}",
            "path": audit_node.get("path", ""),
        })

    # Find QS blocks edges to deferred methods
    safety_findings = graph.safety_check(target_id)

    deferred_info["deferred_methods"] = deferred_methods
    deferred_info["deferred_method_nodes"] = deferred_method_nodes
    if audit_ids:
        deferred_info["deferred_by_nodes"] = audit_ids

    status = "PASS" if (audit_ids or deferred_methods or safety_findings) else "DEGRADED"
    result = _output("why_deferred", target, status, safety_findings, affected_nodes, affected_edges,
                     evidence, "GATE", [], 0.9, False, deferred_info)
    _print(result, pretty)
    return 0


def cmd_graph_health(graph: KnowledgeGraph, pretty: bool) -> int:
    node_count = len(graph.nodes)
    edge_count = len(graph.edges)

    # Check for orphaned edges
    orphaned = [e for e in graph.edges
                if e.get("from_node") not in graph.nodes or e.get("to_node") not in graph.nodes]

    # Check QS rules present
    qs_nodes = [n for nid, n in graph.nodes.items() if n.get("node_type") == "safety_rule"]
    qs_ids = {n.get("name") for n in qs_nodes}
    qs_complete = all(f"QS-{i:03d}" in qs_ids for i in range(1, 11))

    # Check permanent nodes have protects edges
    permanent_nodes = [nid for nid, n in graph.nodes.items() if n.get("is_permanent")]
    permanent_with_protection = [
        nid for nid in permanent_nodes
        if any(e.get("edge_type") in ("protects", "blocks") for e in graph.adj_in.get(nid, []))
    ]

    from collections import Counter
    node_types = dict(Counter(n.get("node_type", "unknown") for n in graph.nodes.values()))
    edge_types = dict(Counter(e.get("edge_type", "unknown") for e in graph.edges))

    health = {
        "$schema": "rkg_health_v1",
        "status": "HEALTHY" if (not orphaned and qs_complete) else "DEGRADED",
        "total_nodes": node_count,
        "total_edges": edge_count,
        "node_types": node_types,
        "edge_types": edge_types,
        "orphaned_edges": len(orphaned),
        "qs_rules_complete": qs_complete,
        "qs_rule_count": len(qs_nodes),
        "permanent_nodes": len(permanent_nodes),
        "permanent_nodes_with_protection": len(permanent_with_protection),
        "graph_health_checks": {
            "all_edge_nodes_resolve": len(orphaned) == 0,
            "qs_001_to_010_all_present": qs_complete,
            "permanent_nodes_have_protection": len(permanent_nodes) == len(permanent_with_protection),
        },
    }
    _print(health, pretty)
    return 0


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _print(data: Any, pretty: bool) -> None:
    print(json.dumps(data, indent=2 if pretty else None, ensure_ascii=False))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="knowledge_graph.py",
        description="FLAOS Runtime Knowledge Graph Query Tool — stdlib only, read-only.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--nodes", default=str(NODES_FILE), help="Path to REPO_GRAPH_NODES_001.jsonl")
    parser.add_argument("--edges", default=str(EDGES_FILE), help="Path to REPO_GRAPH_EDGES_001.jsonl")

    sub = parser.add_subparsers(dest="subcommand", required=True)
    sub.add_parser("graph-health", help="Summarize graph stats and health checks")
    sc = sub.add_parser("safety-check", help="Surface QS safety rules for a target")
    sc.add_argument("target", help="Node name or node_id (e.g. _last_quote_lineage_context)")
    br = sub.add_parser("blast-radius", help="Compute blast radius of extracting target")
    br.add_argument("target")
    ec = sub.add_parser("evidence-for-commit", help="Collect validation evidence for a commit SHA")
    ec.add_argument("commit_hash")
    wd = sub.add_parser("why-deferred", help="Explain why a task/method was deferred")
    wd.add_argument("target")

    args = parser.parse_args()
    graph = KnowledgeGraph(Path(args.nodes), Path(args.edges))
    pretty = args.pretty

    if args.subcommand == "graph-health":
        sys.exit(cmd_graph_health(graph, pretty))
    elif args.subcommand == "safety-check":
        sys.exit(cmd_safety_check(graph, args.target, pretty))
    elif args.subcommand == "blast-radius":
        sys.exit(cmd_blast_radius(graph, args.target, pretty))
    elif args.subcommand == "evidence-for-commit":
        sys.exit(cmd_evidence_for_commit(graph, args.commit_hash, pretty))
    elif args.subcommand == "why-deferred":
        sys.exit(cmd_why_deferred(graph, args.target, pretty))


if __name__ == "__main__":
    main()
