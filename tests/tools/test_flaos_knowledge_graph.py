"""Tests for FLAOS Runtime Knowledge Graph query tool."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from flaos.knowledge_graph import (
    KnowledgeGraph,
    cmd_safety_check,
    cmd_blast_radius,
    cmd_evidence_for_commit,
    cmd_why_deferred,
    cmd_graph_health,
    NODES_FILE,
    EDGES_FILE,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def graph():
    """Load real seeded graph (module scope — load once)."""
    return KnowledgeGraph(NODES_FILE, EDGES_FILE)


# ---------------------------------------------------------------------------
# Graph loading
# ---------------------------------------------------------------------------

class TestGraphLoading:
    def test_loads_nodes_and_edges(self, graph):
        assert len(graph.nodes) == 66
        assert len(graph.edges) == 45

    def test_node_types_present(self, graph):
        types = {n["node_type"] for n in graph.nodes.values()}
        assert "safety_rule" in types
        assert "function" in types
        assert "commit" in types
        assert "runtime_validation" in types

    def test_safety_rule_nodes_count(self, graph):
        qs = [n for n in graph.nodes.values() if n.get("node_type") == "safety_rule"]
        assert len(qs) == 10

    def test_no_polymarket_import(self):
        """Verify knowledge_graph.py does not import polymarket."""
        src = (Path(__file__).resolve().parents[2] / "tools" / "flaos" / "knowledge_graph.py").read_text(encoding="utf-8")
        assert "import polymarket" not in src
        assert "from polymarket" not in src


# ---------------------------------------------------------------------------
# Graph health
# ---------------------------------------------------------------------------

class TestGraphHealth:
    def test_graph_health_66_nodes_45_edges(self, capsys, graph):
        rc = cmd_graph_health(graph, pretty=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["total_nodes"] == 66
        assert out["total_edges"] == 45

    def test_qs_rules_complete(self, capsys, graph):
        rc = cmd_graph_health(graph, pretty=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        assert out["qs_rules_complete"] is True
        assert out["qs_rule_count"] == 10

    def test_graph_health_has_required_schema(self, capsys, graph):
        cmd_graph_health(graph, pretty=False)
        out = json.loads(capsys.readouterr().out)
        for field in ("total_nodes", "total_edges", "node_types", "edge_types",
                      "orphaned_edges", "qs_rules_complete", "graph_health_checks"):
            assert field in out


# ---------------------------------------------------------------------------
# safety-check
# ---------------------------------------------------------------------------

class TestSafetyCheck:
    def test_permanent_field_surfaces_qs003(self, capsys, graph):
        rc = cmd_safety_check(graph, "_last_quote_lineage_context", pretty=False)
        assert rc == 0
        out = json.loads(capsys.readouterr().out)
        rule_ids = {f.get("rule", "") for f in out["safety_findings"]}
        # PERMANENT_FLAG should be surfaced (is_permanent=true on node)
        assert any("PERMANENT" in r or "QS-003" in r for r in rule_ids)

    def test_permanent_flag_surfaces_stop(self, capsys, graph):
        cmd_safety_check(graph, "_phase4_build_quote_lineage", pretty=False)
        out = json.loads(capsys.readouterr().out)
        assert out["status"] in ("STOP_REQUIRED", "GATE")
        assert len(out["safety_findings"]) > 0

    def test_missing_target_returns_degraded(self, capsys, graph):
        cmd_safety_check(graph, "nonexistent_method_xyz", pretty=False)
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "DEGRADED"

    def test_safe_target_no_findings(self, capsys, graph):
        # TraderObservabilityHelper class has no QS rules targeting it
        cmd_safety_check(graph, "TraderObservabilityHelper", pretty=False)
        out = json.loads(capsys.readouterr().out)
        assert out["status"] in ("PASS", "DEGRADED")  # PASS if no QS findings

    def test_output_schema_has_contract_attachment(self, capsys, graph):
        cmd_safety_check(graph, "_last_quote_lineage_context", pretty=False)
        out = json.loads(capsys.readouterr().out)
        assert "execution_contract_attachment" in out
        att = out["execution_contract_attachment"]
        assert "safety_findings_count" in att
        assert "recommended_workflow_tier" in att


# ---------------------------------------------------------------------------
# blast-radius
# ---------------------------------------------------------------------------

class TestBlastRadius:
    def test_blast_radius_includes_safety_finding(self, capsys, graph):
        # _last_quote_lineage_context is permanent — safety should appear
        cmd_blast_radius(graph, "_last_quote_lineage_context", pretty=False)
        out = json.loads(capsys.readouterr().out)
        # Should have STOP_REQUIRED due to QS-003
        assert out["status"] in ("STOP_REQUIRED", "GATE")
        assert len(out["safety_findings"]) > 0

    def test_blast_radius_on_safe_target(self, capsys, graph):
        cmd_blast_radius(graph, "TraderObservabilityHelper", pretty=False)
        out = json.loads(capsys.readouterr().out)
        assert out["status"] in ("PASS", "DEGRADED")
        assert "execution_contract_attachment" in out

    def test_blast_radius_missing_target_degraded(self, capsys, graph):
        cmd_blast_radius(graph, "no_such_method_abc", pretty=False)
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "DEGRADED"

    def test_blast_radius_deferred_target(self, capsys, graph):
        cmd_blast_radius(graph, "_phase2_observability_payload", pretty=False)
        out = json.loads(capsys.readouterr().out)
        assert out.get("is_deferred") is True
        assert "DEFERRED_TARGET" in out["stop_conditions"]


# ---------------------------------------------------------------------------
# evidence-for-commit
# ---------------------------------------------------------------------------

class TestEvidenceForCommit:
    def test_batch_3c_commit_returns_evidence(self, capsys, graph):
        cmd_evidence_for_commit(graph, "3c5b781", pretty=False)
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "PASS"
        assert len(out["evidence"]) >= 1
        grades = {e["grade"] for e in out["evidence"]}
        assert len(grades) > 0

    def test_commit_evidence_has_batch(self, capsys, graph):
        cmd_evidence_for_commit(graph, "3c5b781", pretty=False)
        out = json.loads(capsys.readouterr().out)
        assert out.get("batch") == "Batch-3C"

    def test_missing_commit_returns_degraded(self, capsys, graph):
        cmd_evidence_for_commit(graph, "deadbeef", pretty=False)
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "DEGRADED"

    def test_evidence_for_commit_has_contract_attachment(self, capsys, graph):
        cmd_evidence_for_commit(graph, "a491820", pretty=False)
        out = json.loads(capsys.readouterr().out)
        assert "execution_contract_attachment" in out


# ---------------------------------------------------------------------------
# why-deferred
# ---------------------------------------------------------------------------

class TestWhyDeferred:
    def test_batch_3d_gate_check_returns_deferred_info(self, capsys, graph):
        cmd_why_deferred(graph, "BATCH_3D_GATE_CHECK_001", pretty=False)
        out = json.loads(capsys.readouterr().out)
        assert out["status"] in ("PASS", "DEGRADED")
        # Should reference the gate check audit
        all_nodes = out["affected_nodes"]
        assert any("BATCH_3D" in n or "PAUSE" in str(out.get("gate_verdict", "")) for n in all_nodes) or \
               out.get("deferred_by") is not None

    def test_why_deferred_batch3d_returns_pause_verdict(self, capsys, graph):
        cmd_why_deferred(graph, "BATCH_3D_GATE_CHECK_001", pretty=False)
        out = json.loads(capsys.readouterr().out)

        assert out["status"] in ("PASS", "GATE")
        assert out["gate_verdict"] == "PAUSE_BATCH_3D_DEFER"
        assert any("PAUSE_BATCH_3D_DEFER" in json.dumps(item) for item in out["evidence"])
        assert any("docs/audits/BATCH_3D_GATE_CHECK_001.md" in json.dumps(item) for item in out["evidence"])

    def test_why_deferred_batch3d_returns_deferred_methods(self, capsys, graph):
        cmd_why_deferred(graph, "BATCH_3D_GATE_CHECK_001", pretty=False)
        out = json.loads(capsys.readouterr().out)

        assert "_phase2_complete_lifecycle_observability" in out["deferred_methods"]
        assert "_phase2_observability_payload" in out["deferred_methods"]

    def test_why_deferred_missing_target(self, capsys, graph):
        cmd_why_deferred(graph, "nonexistent_task_xyz", pretty=False)
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "DEGRADED"

    def test_why_deferred_missing_target_returns_degraded(self, capsys, graph):
        cmd_why_deferred(graph, "missing_deferred_target_zzz", pretty=False)
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "DEGRADED"
        assert "TARGET_NOT_IN_GRAPH" in out["stop_conditions"]

    def test_why_deferred_deferred_method_has_evidence(self, capsys, graph):
        cmd_why_deferred(graph, "_phase2_observability_payload", pretty=False)
        out = json.loads(capsys.readouterr().out)
        # Should find deferred_by edge to audit
        assert len(out["affected_nodes"]) >= 1

    def test_why_deferred_has_contract_attachment(self, capsys, graph):
        cmd_why_deferred(graph, "BATCH_3D_GATE_CHECK_001", pretty=False)
        out = json.loads(capsys.readouterr().out)
        assert "execution_contract_attachment" in out
