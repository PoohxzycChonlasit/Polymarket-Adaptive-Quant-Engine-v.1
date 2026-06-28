"""
Tests for tools/airos/migration_analyzer.py
"""
from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path

import pytest

# Ensure repo root on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.airos.migration_analyzer import (
    build_patch_plan,
    _detect_patterns_in_file,
    _scan_repo,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


@pytest.fixture()
def simple_batch() -> dict:
    return {
        "batch_id": "TEST_BATCH_001",
        "risk_level": "SAFE_ATOMIC",
        "approval_required": False,
        "source_paths": ["tools/foo_tool.py"],
        "target_paths": ["tools/mygroup/foo_tool.py"],
        "affected_imports": ["tools.foo_tool"],
        "affected_tests": ["tests/test_foo_tool.py"],
        "compile_commands": [".venv/Scripts/python.exe -m py_compile tools/mygroup/foo_tool.py"],
        "pytest_commands": [".venv/Scripts/python.exe -m pytest tests/test_foo_tool.py -q"],
        "reference_validation_commands": ['git grep "tools.foo_tool"'],
        "rollback_commands": ["git mv tools/mygroup/foo_tool.py tools/foo_tool.py"],
    }


# ---------------------------------------------------------------------------
# Test: module rewrite map is built correctly
# ---------------------------------------------------------------------------


def test_module_rewrite_map_built(tmp_path, simple_batch):
    plan = build_patch_plan(simple_batch, str(tmp_path))
    assert plan["module_rewrite_map"] == {
        "tools.foo_tool": "tools.mygroup.foo_tool"
    }


def test_file_path_rewrite_map_built(tmp_path, simple_batch):
    plan = build_patch_plan(simple_batch, str(tmp_path))
    assert plan["file_path_rewrite_map"] == {
        "tools/foo_tool.py": "tools/mygroup/foo_tool.py"
    }


# ---------------------------------------------------------------------------
# Test: selects recommended_next_batch when batch_id omitted
# ---------------------------------------------------------------------------


def test_recommended_next_batch_selection(tmp_path):
    """Verify CLI uses recommended_next_batch when no --batch-id given."""
    candidates = {
        "recommended_next_batch": "BATCH_A",
        "candidates": [
            {
                "batch_id": "BATCH_A",
                "risk_level": "SAFE_ATOMIC",
                "approval_required": False,
                "source_paths": ["tools/alpha.py"],
                "target_paths": ["tools/group/alpha.py"],
                "affected_tests": [],
                "compile_commands": [],
                "pytest_commands": [],
                "reference_validation_commands": [],
                "rollback_commands": [],
            }
        ],
    }
    cand_path = tmp_path / "batch_candidates.json"
    cand_path.write_text(json.dumps(candidates), encoding="utf-8")
    out_path = tmp_path / "plan.json"

    import subprocess
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "airos" / "migration_analyzer.py"),
            "--batch-candidates", str(cand_path),
            "--output", str(out_path),
            "--repo-root", str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    plan = json.loads(out_path.read_text(encoding="utf-8"))
    assert plan["batch_id"] == "BATCH_A"


# ---------------------------------------------------------------------------
# Test: detects monkeypatch string references
# ---------------------------------------------------------------------------


def test_detects_monkeypatch_strings(tmp_path):
    test_file = _write(
        tmp_path,
        "tests/test_sample.py",
        """\
        import pytest

        def test_something(monkeypatch):
            monkeypatch.setattr(
                "tools.foo_tool.my_func", lambda: None
            )
        """,
    )
    results = _detect_patterns_in_file(
        str(test_file),
        old_mod="tools.foo_tool",
        old_slashpath="tools/foo_tool",
    )
    assert len(results["monkeypatch_strings"]) >= 1
    assert any("tools.foo_tool.my_func" in h["line_content"] for h in results["monkeypatch_strings"])


def test_monkeypatch_rewrites_in_plan(tmp_path, simple_batch):
    """Monkeypatch references appear in plan.monkeypatch_rewrites."""
    _write(
        tmp_path,
        "tests/test_foo_tool.py",
        """\
        def test_x(monkeypatch):
            monkeypatch.setattr("tools.foo_tool.run", lambda: None)
        """,
    )
    plan = build_patch_plan(simple_batch, str(tmp_path))
    assert len(plan["monkeypatch_rewrites"]) >= 1
    rewrite = plan["monkeypatch_rewrites"][0]
    assert rewrite["old_string"] == "tools.foo_tool"
    assert rewrite["new_string"] == "tools.mygroup.foo_tool"


# ---------------------------------------------------------------------------
# Test: detects Path("tools/x.py") literals
# ---------------------------------------------------------------------------


def test_detects_path_literal(tmp_path):
    test_file = _write(
        tmp_path,
        "tests/test_source.py",
        """\
        from pathlib import Path
        def test_source():
            src = Path("tools/foo_tool.py").read_text()
        """,
    )
    results = _detect_patterns_in_file(
        str(test_file),
        old_mod="tools.foo_tool",
        old_slashpath="tools/foo_tool",
    )
    assert len(results["path_literals"]) >= 1


def test_path_literal_rewrites_in_plan(tmp_path, simple_batch):
    _write(
        tmp_path,
        "tests/test_foo_tool.py",
        """\
        from pathlib import Path
        def test_no_imports():
            src = Path("tools/foo_tool.py").read_text(encoding="utf-8")
        """,
    )
    plan = build_patch_plan(simple_batch, str(tmp_path))
    assert len(plan["path_literal_rewrites"]) >= 1
    rewrite = plan["path_literal_rewrites"][0]
    assert rewrite["old_path"] == "tools/foo_tool.py"
    assert rewrite["new_path"] == "tools/mygroup/foo_tool.py"


# ---------------------------------------------------------------------------
# Test: detects _REPO / "tools" / "x.py" style builds
# ---------------------------------------------------------------------------


def test_detects_repo_path_build(tmp_path):
    test_file = _write(
        tmp_path,
        "tests/test_ast.py",
        """\
        _REPO = Path(__file__).parents[1]
        def test_something():
            src = (_REPO / "tools" / "foo_tool.py").read_text()
        """,
    )
    results = _detect_patterns_in_file(
        str(test_file),
        old_mod="tools.foo_tool",
        old_slashpath="tools/foo_tool",
    )
    assert len(results["repo_path_builds"]) >= 1


# ---------------------------------------------------------------------------
# Test: detects importlib.import_module strings
# ---------------------------------------------------------------------------


def test_detects_importlib_strings(tmp_path):
    test_file = _write(
        tmp_path,
        "tests/test_dynamic.py",
        """\
        import importlib
        def test_dynamic():
            mod = importlib.import_module("tools.foo_tool")
        """,
    )
    results = _detect_patterns_in_file(
        str(test_file),
        old_mod="tools.foo_tool",
        old_slashpath="tools/foo_tool",
    )
    assert len(results["importlib_strings"]) >= 1


def test_dynamic_import_rewrites_in_plan(tmp_path, simple_batch):
    _write(
        tmp_path,
        "tests/test_foo_tool.py",
        """\
        import importlib
        mod = importlib.import_module("tools.foo_tool")
        """,
    )
    plan = build_patch_plan(simple_batch, str(tmp_path))
    assert len(plan["dynamic_import_rewrites"]) >= 1
    rewrite = plan["dynamic_import_rewrites"][0]
    assert rewrite["old_module"] == "tools.foo_tool"
    assert rewrite["new_module"] == "tools.mygroup.foo_tool"


# ---------------------------------------------------------------------------
# Test: detects __init__.py requirement
# ---------------------------------------------------------------------------


def test_init_files_required_when_dir_missing(tmp_path, simple_batch):
    """tools/mygroup/ doesn't exist in tmp_path, so __init__.py is required."""
    plan = build_patch_plan(simple_batch, str(tmp_path))
    assert "tools/mygroup/__init__.py" in plan["init_files_required"]


def test_init_files_not_required_when_exists(tmp_path, simple_batch):
    """When __init__.py already exists, it's not listed as required."""
    init_dir = tmp_path / "tools" / "mygroup"
    init_dir.mkdir(parents=True, exist_ok=True)
    (init_dir / "__init__.py").write_text('"""pkg."""\n', encoding="utf-8")
    plan = build_patch_plan(simple_batch, str(tmp_path))
    assert "tools/mygroup/__init__.py" not in plan["init_files_required"]


# ---------------------------------------------------------------------------
# Test: deterministic sorted output
# ---------------------------------------------------------------------------


def test_affected_files_sorted(tmp_path, simple_batch):
    _write(tmp_path, "tests/test_zzz.py", 'from tools.foo_tool import x\n')
    _write(tmp_path, "tests/test_aaa.py", 'from tools.foo_tool import y\n')
    plan = build_patch_plan(simple_batch, str(tmp_path))
    keys = list(plan["affected_files"].keys())
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Test: CLI smoke test writes migration_patch_plan.json
# ---------------------------------------------------------------------------


def test_cli_smoke_writes_patch_plan(tmp_path):
    candidates = {
        "recommended_next_batch": "BATCH_SMOKE",
        "candidates": [
            {
                "batch_id": "BATCH_SMOKE",
                "risk_level": "SAFE_ATOMIC",
                "approval_required": False,
                "source_paths": ["tools/smoke_tool.py"],
                "target_paths": ["tools/smoke/smoke_tool.py"],
                "affected_tests": [],
                "compile_commands": [],
                "pytest_commands": [],
                "reference_validation_commands": [],
                "rollback_commands": [],
            }
        ],
    }
    cand_path = tmp_path / "batch_candidates.json"
    cand_path.write_text(json.dumps(candidates), encoding="utf-8")
    out_path = tmp_path / "migration_patch_plan.json"

    import subprocess
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "airos" / "migration_analyzer.py"),
            "--batch-candidates", str(cand_path),
            "--output", str(out_path),
            "--repo-root", str(tmp_path),
            "--pretty",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert out_path.exists()
    plan = json.loads(out_path.read_text(encoding="utf-8"))
    assert plan["schema_version"] == "migration_patch_plan_v1"
    assert plan["batch_id"] == "BATCH_SMOKE"
    assert "module_rewrite_map" in plan
    assert "init_files_required" in plan
    assert "monkeypatch_rewrites" in plan
    assert "path_literal_rewrites" in plan
    assert "dynamic_import_rewrites" in plan
    assert "unresolved_patterns" in plan
    assert "pre_move_patch_recommendations" in plan
    assert "post_move_validation_commands" in plan
