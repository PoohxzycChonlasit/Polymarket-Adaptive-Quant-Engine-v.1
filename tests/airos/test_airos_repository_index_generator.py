import os
import json
import tempfile
import shutil
import subprocess
from pathlib import Path
import pytest

from tools.airos.repository_index_generator import (
    get_file_category,
    get_tool_domain,
    check_runtime_sensitive,
    extract_python_imports,
    generate_registries,
)


def test_get_file_category():
    assert get_file_category("polymarket/trader.py", ".py") == "runtime"
    assert get_file_category("config/settings.py", ".py") == "runtime"
    assert get_file_category("tools/my_tool.py", ".py") == "tools"
    assert get_file_category("tests/test_my_tool.py", ".py") == "tests"
    assert get_file_category("docs/rules.md", ".md") == "docs"
    assert get_file_category("README.md", ".md") == "docs"
    assert get_file_category("my_config.json", ".json") == "config"
    assert get_file_category(".env", "") == "config"
    assert get_file_category("random.bin", ".bin") == "unclassified"


def test_get_tool_domain():
    assert get_tool_domain("tools/audit/_audit_cs_btc.py") == "audit"
    assert get_tool_domain("tools/_opp_capture_audit.py") == "audit"
    assert get_tool_domain("tools/semantic_c_shadow_fill_replay.py") == "shadow"
    assert get_tool_domain("tools/lifecycle_timing_report.py") == "probes"
    assert get_tool_domain("tools/zero_size_risk_floor_probe.py") == "probes"
    assert get_tool_domain("tools/quant_data_quality.py") == "research"
    assert get_tool_domain("tools/joined_records_builder.py") == "runtime"
    assert get_tool_domain("tools/canonical_trade_table_v1.py") == "canonical"
    assert get_tool_domain("tools/airos/repository_index_generator.py") == "airos"
    assert get_tool_domain("tools/random_unclassified_file.py") == "unknown"
    assert get_tool_domain("polymarket/trader.py") == "unknown"


def test_check_runtime_sensitive():
    assert check_runtime_sensitive("polymarket/trader.py") is True
    assert check_runtime_sensitive("config/settings.py") is True
    assert check_runtime_sensitive(".env") is True
    assert check_runtime_sensitive("tools/utils_risk_manager.py") is True
    assert check_runtime_sensitive("tools/shadow_filter_evaluator.py") is False


def test_extract_python_imports():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("import os\nfrom pathlib import Path\nimport tools.shadow.shadow_filter_evaluator\n")
        temp_path = f.name
        
    try:
        imports = extract_python_imports(temp_path)
        assert "os" in imports
        assert "pathlib" in imports
        assert "tools.shadow.shadow_filter_evaluator" in imports
    finally:
        os.remove(temp_path)


def test_generate_registries_mock_repo():
    # Set up a mock repo directory structure
    with tempfile.TemporaryDirectory() as temp_repo:
        os.makedirs(os.path.join(temp_repo, "polymarket"))
        os.makedirs(os.path.join(temp_repo, "tools", "shadow"))
        os.makedirs(os.path.join(temp_repo, "tests"))
        os.makedirs(os.path.join(temp_repo, ".venv")) # Should be ignored
        
        # Create mock files
        with open(os.path.join(temp_repo, "polymarket", "trader.py"), "w") as f:
            f.write("import os\n")
        with open(os.path.join(temp_repo, "tools", "shadow", "my_shadow.py"), "w") as f:
            f.write("import polymarket.trader\n")
        with open(os.path.join(temp_repo, "tests", "test_my_shadow.py"), "w") as f:
            f.write("import tools.shadow.my_shadow\n")
        with open(os.path.join(temp_repo, ".venv", "should_ignore.py"), "w") as f:
            f.write("import sys\n")
            
        index, tools, tests, health = generate_registries(temp_repo)
        
        # Verify ignored directories are skipped
        assert "should_ignore.py" not in index
        assert any(".venv" in p for p in index.keys()) is False
        
        # Verify file classification
        assert "polymarket/trader.py" in index
        assert index["polymarket/trader.py"]["category"] == "runtime"
        assert index["polymarket/trader.py"]["is_runtime_sensitive"] is True
        
        assert "tools/shadow/my_shadow.py" in index
        assert index["tools/shadow/my_shadow.py"]["category"] == "tools"
        assert index["tools/shadow/my_shadow.py"]["domain"] == "shadow"
        assert index["tools/shadow/my_shadow.py"]["safe_to_move_candidate"] is True
        
        # Verify test mappings
        assert "tests/test_my_shadow.py" in index
        assert index["tests/test_my_shadow.py"]["category"] == "tests"
        assert "tests/test_my_shadow.py" in index["tools/shadow/my_shadow.py"]["likely_test_files"]
        
        assert "tools/shadow/my_shadow.py" in tests["source_to_test"]
        assert tests["source_to_test"]["tools/shadow/my_shadow.py"] == ["tests/test_my_shadow.py"]
        assert tests["test_to_source"]["tests/test_my_shadow.py"] == ["tools/shadow/my_shadow.py"]
        
        # Verify health metrics
        assert health["status"] == "HEALTHY"
        assert health["metrics"]["total_files"] == 3
        assert health["metrics"]["tools_count"] == 1
        assert health["metrics"]["tests_count"] == 1
        assert health["metrics"]["runtime_files"] == 1


def test_cli_smoke():
    with tempfile.TemporaryDirectory() as temp_repo:
        os.makedirs(os.path.join(temp_repo, "tools"))
        with open(os.path.join(temp_repo, "tools", "sample.py"), "w") as f:
            f.write("# sample tool\n")
            
        with tempfile.TemporaryDirectory() as temp_out:
            # Call CLI command via subprocess
            generator_script = os.path.join(os.path.dirname(__file__), "..", "tools", "airos", "repository_index_generator.py")
            cmd = [
                "python",
                generator_script,
                "--repo-root", temp_repo,
                "--output-dir", temp_out,
                "--pretty"
            ]
            
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Verify the 4 files were written
            expected_files = [
                "repository_index.json",
                "tool_registry.json",
                "test_registry.json",
                "repo_health.json",
            ]
            for ef in expected_files:
                file_path = os.path.join(temp_out, ef)
                assert os.path.exists(file_path)
                with open(file_path, "r") as f:
                    data = json.load(f)
                    assert isinstance(data, dict)
