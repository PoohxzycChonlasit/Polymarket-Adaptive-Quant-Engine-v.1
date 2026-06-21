from __future__ import annotations

import sys
import json
import pytest
import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from tools.phase_b_run_daily_pipeline import main

# Mock dashboard JSON data
MOCK_DASHBOARD_DATA = json.dumps({
    "overall_system_status": "CANDIDATE",
    "global_metrics": {
        "total_closed_trades": 12
    },
    "filters": {
        "block_btc_shadow": {
            "joined_trades": 12,
            "join_coverage_pct": 98.5
        }
    }
})

# Mock index JSON data
MOCK_INDEX_DATA = json.dumps({
    "2026-06-21": {
        "date": "2026-06-21",
        "overall_status": "CANDIDATE",
        "joined_trades": 12,
        "join_coverage_pct": 98.5,
        "exception_count": 0,
        "heartbeat_age_seconds": 15.0
    }
})

def mock_open_file(filepath, *args, **kwargs):
    path = str(filepath)
    if "phase_b_dashboard.json" in path:
        return mock_open(read_data=MOCK_DASHBOARD_DATA)()
    elif "phase_b_snapshot_index.json" in path:
        return mock_open(read_data=MOCK_INDEX_DATA)()
    return mock_open()()

@pytest.fixture
def mock_subprocess_run():
    with patch("subprocess.run") as mock_run:
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = "Success"
        completed.stderr = ""
        mock_run.return_value = completed
        yield mock_run

def test_successful_pipeline_sequence(mock_subprocess_run):
    """Test successful run: all subprocesses called, health checks pass."""
    def custom_exists(self):
        # exists returns False for snapshot directory (so it runs archiver)
        # and True for health check files
        path_str = str(self)
        if "reports/phase_b_daily_snapshots/2026-06-21" in path_str.replace("\\", "/"):
            return False
        return True

    with patch.object(Path, "exists", autospec=True) as mock_exists, \
         patch("builtins.open", mock_open_file), \
         patch("sys.argv", ["tools/phase_b_run_daily_pipeline.py", "--date", "2026-06-21"]):
        
        mock_exists.side_effect = custom_exists
        main()

        # Check daily report, snapshot archiver, and snapshot summary called
        assert mock_subprocess_run.call_count == 3
        calls = [call[0][0] for call in mock_subprocess_run.call_args_list]
        
        # Verify correct script names executed
        assert any("phase_b_daily_report.py" in str(cmd) for cmd in calls)
        assert any("phase_b_snapshot_archiver.py" in str(cmd) for cmd in calls)
        assert any("phase_b_snapshot_summary.py" in str(cmd) for cmd in calls)

def test_duplicate_snapshot_skips_archiver(mock_subprocess_run):
    """Test duplicate folder exists: archiver is skipped, exits 0."""
    def custom_exists(self):
        # snapshot folder exists
        return True

    with patch.object(Path, "exists", autospec=True) as mock_exists, \
         patch("builtins.open", mock_open_file), \
         patch("sys.argv", ["tools/phase_b_run_daily_pipeline.py", "--date", "2026-06-21"]):
        
        mock_exists.side_effect = custom_exists
        main()

        # Check only daily report and snapshot summary called (2 calls)
        assert mock_subprocess_run.call_count == 2
        calls = [call[0][0] for call in mock_subprocess_run.call_args_list]
        
        assert any("phase_b_daily_report.py" in str(cmd) for cmd in calls)
        assert not any("phase_b_snapshot_archiver.py" in str(cmd) for cmd in calls)
        assert any("phase_b_snapshot_summary.py" in str(cmd) for cmd in calls)

def test_subprocess_failure_exits_1(mock_subprocess_run):
    """Test that subprocess non-zero exit status terminates pipeline with SystemExit(1)."""
    # Force daily_report to fail
    failed = MagicMock()
    failed.returncode = 1
    failed.stdout = ""
    failed.stderr = "Daily report execution error"
    mock_subprocess_run.return_value = failed

    with patch.object(Path, "exists", return_value=True), \
         pytest.raises(SystemExit) as exc_info, \
         patch("sys.argv", ["tools/phase_b_run_daily_pipeline.py", "--date", "2026-06-21"]):
        
        main()
        
    assert exc_info.value.code == 1

def test_missing_dashboard_health_check_fails(mock_subprocess_run):
    """Test that health check fails if compiled dashboard file is missing."""
    def custom_exists(self):
        # Mock dash_json_path.exists() as False
        path_str = str(self).replace("\\", "/")
        if "phase_b_dashboard.json" in path_str:
            return False
        return True

    with patch.object(Path, "exists", autospec=True) as mock_exists, \
         pytest.raises(SystemExit) as exc_info, \
         patch("sys.argv", ["tools/phase_b_run_daily_pipeline.py", "--date", "2026-06-21"]):
        
        mock_exists.side_effect = custom_exists
        main()
        
    assert exc_info.value.code == 1

def test_index_json_parse_failure_exits_1(mock_subprocess_run):
    """Test malformed index JSON throws SystemExit(1)."""
    def mock_open_malformed(filepath, *args, **kwargs):
        path = str(filepath)
        if "phase_b_dashboard.json" in path:
            return mock_open(read_data=MOCK_DASHBOARD_DATA)()
        elif "phase_b_snapshot_index.json" in path:
            return mock_open(read_data="{malformed_json_here")()
        return mock_open()()

    with patch.object(Path, "exists", return_value=True), \
         patch("builtins.open", mock_open_malformed), \
         pytest.raises(SystemExit) as exc_info, \
         patch("sys.argv", ["tools/phase_b_run_daily_pipeline.py", "--date", "2026-06-21"]):
        
        main()
        
    assert exc_info.value.code == 1

def test_date_argument_parsing(mock_subprocess_run):
    """Verify script fails on invalid date format input."""
    # Test valid date format passes date checks
    with patch.object(Path, "exists", return_value=True), \
         patch("builtins.open", mock_open_file), \
         patch("sys.argv", ["tools/phase_b_run_daily_pipeline.py", "--date", "2026-06-21"]):
        main()  # Should not raise ValueError/SystemExit for format

    # Test invalid format triggers exit
    with patch("sys.argv", ["tools/phase_b_run_daily_pipeline.py", "--date", "invalid-date-format"]), \
         pytest.raises(SystemExit) as exc_info:
        main()
        
    assert exc_info.value.code == 1
