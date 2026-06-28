import os
import json
import tempfile
import shutil
import subprocess
from pathlib import Path
import pytest

from tools.airos.atomic_batch_executor import (
    rewrite_imports_in_file,
    run_command,
)


def test_rewrite_imports_in_file():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("import tools.canonical.canonical_trade_table_v1\nfrom tools.canonical.canonical_trade_table_v1 import foo\nfrom tools.canonical import canonical_trade_table_v1\n")
        temp_path = f.name
        
    try:
        import_maps = {
            "tools.canonical_trade_table_v1": "tools.canonical.canonical_trade_table_v1"
        }
        rewrite_imports_in_file(temp_path, import_maps)
        
        with open(temp_path, "r") as f:
            content = f.read()
            
        assert "import tools.canonical.canonical_trade_table_v1" in content
        assert "from tools.canonical.canonical_trade_table_v1 import foo" in content
        assert "from tools.canonical import canonical_trade_table_v1" in content
    finally:
        os.remove(temp_path)


def test_run_command():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Simple exit code tests
        assert run_command("python -c exit(0)", temp_dir) is True
        assert run_command("python -c exit(1)", temp_dir) is False


def test_cli_dry_run():
    with tempfile.TemporaryDirectory() as temp_dir:
        candidates = {
            "recommended_next_batch": "BATCH_CANONICAL_001",
            "candidates": [
                {
                    "batch_id": "BATCH_CANONICAL_001",
                    "risk_level": "SAFE_ATOMIC",
                    "source_paths": ["tools/canonical_trade_table_v1.py"],
                    "target_paths": ["tools/canonical/canonical_trade_table_v1.py"],
                    "rollback_commands": ["git checkout -- ."]
                }
            ]
        }
        
        candidates_file = os.path.join(temp_dir, "batch_candidates.json")
        with open(candidates_file, "w") as f:
            json.dump(candidates, f)
            
        executor_script = os.path.join(os.path.dirname(__file__), "..", "tools", "airos", "atomic_batch_executor.py")
        cmd = [
            "python",
            executor_script,
            "--batch-candidates", candidates_file,
            "--repo-root", temp_dir,
            "--dry-run"
        ]
        
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        assert "BATCH_CANONICAL_001" in res.stdout
        assert "git mv tools/canonical_trade_table_v1.py -> tools/canonical/canonical_trade_table_v1.py" in res.stdout
