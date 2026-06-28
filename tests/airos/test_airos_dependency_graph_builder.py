import os
import json
import tempfile
import subprocess
from pathlib import Path
import pytest

from tools.airos.dependency_graph_builder import (
    resolve_import,
    build_graph,
)


def test_resolve_import():
    # Mock file index containing some standard paths
    file_index = {
        "tools/audit/_opp_capture_audit.py": {},
        "tools/shadow_filter_evaluator.py": {},
        "polymarket/trader.py": {},
    }
    
    # 1. Standard package import
    res, is_internal = resolve_import("tools.shadow_filter_evaluator", file_index)
    assert res == "tools/shadow_filter_evaluator.py"
    assert is_internal is True
    
    # 2. Standard subdirectory package import
    res, is_internal = resolve_import("tools.audit._opp_capture_audit", file_index)
    assert res == "tools/audit/_opp_capture_audit.py"
    assert is_internal is True
    
    # 3. Core runtime import
    res, is_internal = resolve_import("polymarket.trader", file_index)
    assert res == "polymarket/trader.py"
    assert is_internal is True
    
    # 4. External import
    res, is_internal = resolve_import("urllib.request", file_index)
    assert res is None
    assert is_internal is False
    
    # 5. Missing internal import
    res, is_internal = resolve_import("tools.missing_tool", file_index)
    assert res is None
    assert is_internal is True


def test_build_graph():
    # Mock indexes
    index_data = {
        "tools/tool_a.py": {
            "is_tool": True,
            "category": "tools",
            "is_runtime_sensitive": False,
            "direct_imports": ["tools.tool_b", "urllib.parse"],
        },
        "tools/tool_b.py": {
            "is_tool": True,
            "category": "tools",
            "is_runtime_sensitive": False,
            "direct_imports": ["polymarket.trader", "tools.missing_helper"],
        },
        "polymarket/trader.py": {
            "is_tool": False,
            "category": "runtime",
            "is_runtime_sensitive": True,
            "direct_imports": [],
        }
    }
    
    test_data = {
        "source_to_test": {
            "tools/tool_a.py": ["tests/test_tool_a.py"]
        },
        "test_to_source": {
            "tests/test_tool_a.py": ["tools/tool_a.py"]
        }
    }
    
    graph = build_graph(index_data, test_data)
    
    # Assert nodes and edges
    assert "tools/tool_a.py" in graph["nodes"]
    assert "tools/tool_b.py" in graph["nodes"]
    assert ["tools/tool_a.py", "tools/tool_b.py"] in graph["edges"]
    assert ["tools/tool_b.py", "polymarket/trader.py"] in graph["edges"]
    
    # Assert direct/reverse dependencies
    assert graph["direct_imports_by_file"]["tools/tool_a.py"] == ["tools/tool_b.py"]
    assert graph["reverse_importers"]["tools/tool_b.py"] == ["tools/tool_a.py"]
    
    # Assert unresolved imports
    assert "urllib.parse" in graph["unresolved_imports"]["tools/tool_a.py"]["unresolved_external"]
    assert "tools.missing_helper" in graph["unresolved_imports"]["tools/tool_b.py"]["unresolved_internal"]
    
    # Assert tests link
    assert graph["tests_by_file"]["tools/tool_a.py"] == ["tests/test_tool_a.py"]
    
    # Assert sensitive nodes
    assert "polymarket/trader.py" in graph["runtime_sensitive_nodes"]
    
    # Assert blast radius scoring & safety levels
    # tool_a has 0 inbound + 1 outbound = 1 dep. Not sensitive. Score = 1 -> SAFE_ATOMIC
    assert graph["migration_safety_summary"]["tools/tool_a.py"]["blast_radius_score"] == 1
    assert graph["migration_safety_summary"]["tools/tool_a.py"]["migration_safety_status"] == "SAFE_ATOMIC"
    
    # trader.py is category "runtime" -> DO_NOT_MOVE
    assert graph["migration_safety_summary"]["polymarket/trader.py"]["migration_safety_status"] == "DO_NOT_MOVE"


def test_cli_smoke():
    with tempfile.TemporaryDirectory() as temp_dir:
        index_data = {
            "tools/sample.py": {
                "is_tool": True,
                "category": "tools",
                "is_runtime_sensitive": False,
                "direct_imports": []
            }
        }
        test_data = {"source_to_test": {}, "test_to_source": {}}
        
        with open(os.path.join(temp_dir, "repository_index.json"), "w") as f:
            json.dump(index_data, f)
        with open(os.path.join(temp_dir, "test_registry.json"), "w") as f:
            json.dump(test_data, f)
            
        builder_script = os.path.join(os.path.dirname(__file__), "..", "tools", "airos", "dependency_graph_builder.py")
        cmd = [
            "python",
            builder_script,
            "--input-dir", temp_dir,
            "--pretty"
        ]
        
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        out_file = os.path.join(temp_dir, "dependency_graph.json")
        assert os.path.exists(out_file)
        with open(out_file, "r") as f:
            graph = json.load(f)
            assert graph["schema_version"] == "dependency_graph_v1"
            assert "nodes" in graph
            assert "edges" in graph
