import json
import pytest
from pathlib import Path
from unittest.mock import patch
from tools.flaos import bootstrap

@pytest.fixture
def clean_files():
    return bootstrap.FILES.copy()

def test_diagnose_healthy(clean_files):
    with patch("tools.flaos.bootstrap.FILES", clean_files):
        stdout_data = []
        def mock_print(*args, **kwargs):
            stdout_data.append(" ".join(map(str, args)))
        
        with patch("builtins.print", side_effect=mock_print):
            code = bootstrap.build_snapshot(pretty=True, diagnose=True)
            assert code == 0
            
        report = json.loads("\n".join(stdout_data))
        assert report["status"] == "HEALTHY"
        assert report["diagnose"]["files_exist"]["state"] is True
        assert report["diagnose"]["loop_memory_status"] == "OK"

def test_missing_required_file(clean_files):
    clean_files["state"] = bootstrap.ROOT / "non_existent_file_that_does_not_exist.json"
    with patch("tools.flaos.bootstrap.FILES", clean_files):
        stdout_data = []
        def mock_print(*args, **kwargs):
            stdout_data.append(" ".join(map(str, args)))
        with patch("builtins.print", side_effect=mock_print):
            with pytest.raises(SystemExit) as excinfo:
                bootstrap.build_snapshot(pretty=True, diagnose=True)
            assert excinfo.value.code == 1
        stop_report = json.loads("\n".join(stdout_data))
        assert stop_report["status"] == "STOP_AND_ESCALATE"
        assert stop_report["error_type"] == "MISSING_REQUIRED_FILE"
        assert stop_report["missing_or_invalid_file"] == "non_existent_file_that_does_not_exist.json"

def test_invalid_json_format(clean_files, tmp_path):
    bad_state = tmp_path / "bad_state.json"
    bad_state.write_text("{invalid json", encoding="utf-8")
    clean_files["state"] = bad_state
    
    with patch("tools.flaos.bootstrap.FILES", clean_files):
        stdout_data = []
        def mock_print(*args, **kwargs):
            stdout_data.append(" ".join(map(str, args)))
        with patch("builtins.print", side_effect=mock_print):
            with pytest.raises(SystemExit) as excinfo:
                bootstrap.build_snapshot(pretty=True, diagnose=True)
            assert excinfo.value.code == 1
        stop_report = json.loads("\n".join(stdout_data))
        assert stop_report["status"] == "STOP_AND_ESCALATE"
        assert stop_report["error_type"] == "INVALID_JSON_FORMAT"
        assert stop_report["missing_or_invalid_file"] == "bad_state.json"

def test_missing_loop_memory_read_task(clean_files):
    clean_files["loop_memory"] = bootstrap.ROOT / "non_existent_loop_memory.json"
    
    original_load = bootstrap._load_file_or_fail
    def mock_load(key):
        if key == "state":
            return {
                "next_task": "TEST_TASK",
                "next_workflow_tier": "LOOP",
                "blocked": False,
                "current_phase": "testing"
            }
        return original_load(key)

    with patch("tools.flaos.bootstrap.FILES", clean_files):
        mock_entry = {"task_class": 9, "allowed_scope": ["docs/"]}
        with patch("tools.flaos.bootstrap._next_task_entry", return_value=mock_entry):
            with patch("tools.flaos.bootstrap._load_file_or_fail", side_effect=mock_load):
                stdout_data = []
                def mock_print(*args, **kwargs):
                    stdout_data.append(" ".join(map(str, args)))
                with patch("builtins.print", side_effect=mock_print):
                    code = bootstrap.build_snapshot(pretty=True, diagnose=False)
                    assert code == 0
                snapshot = json.loads("\n".join(stdout_data))
                assert snapshot["last_loop_id"] == "UNKNOWN"
                assert snapshot["last_loop_result"] == "UNKNOWN"

def test_missing_loop_memory_write_task(clean_files):
    clean_files["loop_memory"] = bootstrap.ROOT / "non_existent_loop_memory.json"
    
    with patch("tools.flaos.bootstrap.FILES", clean_files):
        mock_entry = {"task_class": 4, "allowed_scope": ["tools/"]}
        with patch("tools.flaos.bootstrap._next_task_entry", return_value=mock_entry):
            stdout_data = []
            def mock_print(*args, **kwargs):
                stdout_data.append(" ".join(map(str, args)))
            with patch("builtins.print", side_effect=mock_print):
                with pytest.raises(SystemExit) as excinfo:
                    bootstrap.build_snapshot(pretty=True, diagnose=False)
                assert excinfo.value.code == 1
            stop_report = json.loads("\n".join(stdout_data))
            assert stop_report["status"] == "STOP_AND_ESCALATE"
            assert stop_report["error_type"] == "MISSING_LOOP_MEMORY_FOR_WRITE_TASK"
