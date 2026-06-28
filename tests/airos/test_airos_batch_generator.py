import os
import json
import tempfile
import subprocess
from pathlib import Path
import pytest

from tools.airos.batch_generator import (
    is_root_tool,
    generate_validation_commands,
    generate_rollback_commands,
    build_candidates,
)


def test_is_root_tool():
    # Only root level tools under tools/*.py
    assert is_root_tool("tools/my_tool.py", {"is_tool": True}) is True
    assert is_root_tool("tools/shadow/shadow_tool.py", {"is_tool": True}) is False
    assert is_root_tool("polymarket/trader.py", {"is_tool": False}) is False


def test_generate_validation_commands():
    source_paths = ["tools/tool_a.py"]
    target_paths = ["tools/shadow/tool_a.py"]
    test_files = ["tests/test_tool_a.py"]
    
    compiles, pytests, ref_checks = generate_validation_commands(source_paths, target_paths, test_files)
    
    assert any("py_compile" in c for c in compiles)
    assert any("pytest" in p for p in pytests)
    assert any("git grep" in r for r in ref_checks)


def test_generate_rollback_commands():
    source_paths = ["tools/tool_a.py"]
    target_paths = ["tools/shadow/tool_a.py"]
    test_files = ["tests/test_tool_a.py"]
    
    rollbacks = generate_rollback_commands(source_paths, target_paths, test_files)
    
    assert any("git mv" in r for r in rollbacks)
    assert any("git checkout" in r for r in rollbacks)


def test_build_candidates():
    # Mock data
    index_data = {
        "tools/tool_a.py": {
            "is_tool": True,
            "category": "tools",
            "is_runtime_sensitive": False,
            "domain": "shadow",
        },
        "tools/tool_b.py": {
            "is_tool": True,
            "category": "tools",
            "is_runtime_sensitive": True, # Runtime sensitive -> DO_NOT_MOVE/deferred
            "domain": "audit",
        },
        "tools/airos/my_script.py": {
            "is_tool": True,
            "category": "tools",
            "is_runtime_sensitive": False,
            "domain": "airos",
        }
    }
    
    graph_data = {
        "nodes": ["tools/tool_a.py", "tools/tool_b.py", "tools/airos/my_script.py"],
        "edges": [],
        "tests_by_file": {
            "tools/tool_a.py": ["tests/test_tool_a.py"]
        },
        "migration_safety_summary": {
            "tools/tool_a.py": {
                "blast_radius_score": 1,
                "migration_safety_status": "SAFE_ATOMIC"
            },
            "tools/tool_b.py": {
                "blast_radius_score": 12,
                "migration_safety_status": "DO_NOT_MOVE"
            },
            "tools/airos/my_script.py": {
                "blast_radius_score": 1,
                "migration_safety_status": "SAFE_ATOMIC"
            }
        },
        "unresolved_imports": {
            "tools/tool_a.py": {
                "unresolved_internal": []
            }
        }
    }
    
    batches = build_candidates(index_data, graph_data)
    
    assert batches["schema_version"] == "batch_candidates_v1"
    
    # Excludes tools/airos and runtime sensitive files
    assert batches["batch_count"] == 1
    candidate = batches["candidates"][0]
    assert candidate["batch_id"] == "REPOSITORY_PHASE1_SHADOW_BATCH_001"
    assert candidate["risk_level"] == "SAFE_ATOMIC"
    assert candidate["source_paths"] == ["tools/tool_a.py"]
    assert candidate["target_paths"] == ["tools/shadow/tool_a.py"]
    
    # Verify deferred files contains the sensitive tool_b
    assert len(batches["deferred_files"]) == 1
    assert batches["deferred_files"][0]["path"] == "tools/tool_b.py"


def test_cli_smoke():
    with tempfile.TemporaryDirectory() as temp_dir:
        index_data = {
            "tools/sample.py": {
                "is_tool": True,
                "category": "tools",
                "is_runtime_sensitive": False,
                "domain": "shadow",
            }
        }
        graph_data = {
            "nodes": ["tools/sample.py"],
            "edges": [],
            "tests_by_file": {},
            "migration_safety_summary": {
                "tools/sample.py": {
                    "blast_radius_score": 0,
                    "migration_safety_status": "SAFE_ATOMIC"
                }
            },
            "unresolved_imports": {
                "tools/sample.py": {
                    "unresolved_internal": []
                }
            }
        }
        
        with open(os.path.join(temp_dir, "repository_index.json"), "w") as f:
            json.dump(index_data, f)
        with open(os.path.join(temp_dir, "dependency_graph.json"), "w") as f:
            json.dump(graph_data, f)
            
        generator_script = os.path.join(os.path.dirname(__file__), "..", "tools", "airos", "batch_generator.py")
        cmd = [
            "python",
            generator_script,
            "--input-dir", temp_dir,
            "--pretty"
        ]
        
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        out_file = os.path.join(temp_dir, "batch_candidates.json")
        assert os.path.exists(out_file)
        with open(out_file, "r") as f:
            candidates = json.load(f)
            assert candidates["schema_version"] == "batch_candidates_v1"
            assert "candidates" in candidates
            assert candidates["batch_count"] == 1
