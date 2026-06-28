import json
import os
import shutil
import unittest
from unittest.mock import patch, MagicMock
from tools.flaos.session_schema import SessionMetadata
from tools.flaos import runtime_session

class TestFlaosRuntimeSession(unittest.TestCase):
    def setUp(self):
        # Create temp testing dir
        self.test_session_id = "test_session_12345"
        self.metadata_path = f"runtime/sessions/session_{self.test_session_id}.json"
        
    def tearDown(self):
        # Cleanup temp metadata and logs
        if os.path.exists(self.metadata_path):
            try:
                os.remove(self.metadata_path)
            except Exception:
                pass
        stdout_log = f"runtime/validation/session_{self.test_session_id}_stdout.log"
        stderr_log = f"runtime/validation/session_{self.test_session_id}_stderr.log"
        if os.path.exists(stdout_log):
            try:
                os.remove(stdout_log)
            except Exception:
                pass
        if os.path.exists(stderr_log):
            try:
                os.remove(stderr_log)
            except Exception:
                pass

    def test_session_metadata_serialization(self):
        meta = SessionMetadata(
            session_id=self.test_session_id,
            task_id="TEST_TASK_001",
            mode="paper",
            status="CREATED",
            created_at="2026-06-27T12:00:00Z",
            stdout_log=f"runtime/validation/session_{self.test_session_id}_stdout.log",
            stderr_log=f"runtime/validation/session_{self.test_session_id}_stderr.log",
            metadata_path=self.metadata_path,
            pid=None,
            expected_duration_seconds=60,
            command="python main.py"
        )
        
        # Test to_dict
        d = meta.to_dict()
        self.assertEqual(d["session_id"], self.test_session_id)
        self.assertEqual(d["status"], "CREATED")
        
        # Test save and load
        os.makedirs("runtime/sessions", exist_ok=True)
        meta.save()
        self.assertTrue(os.path.exists(self.metadata_path))
        
        loaded = SessionMetadata.load(self.metadata_path)
        self.assertEqual(loaded.task_id, "TEST_TASK_001")
        self.assertEqual(loaded.pid, None)

    def test_live_mode_rejected(self):
        # Use argparse mock to test cmd_create rejecting live mode
        args = MagicMock()
        args.mode = "live"
        args.task_id = "TEST_TASK"
        args.session_id = self.test_session_id
        args.expected_duration = 60
        
        with patch('sys.stdout') as mock_stdout:
            exit_code = runtime_session.cmd_create(args)
            self.assertEqual(exit_code, 1)
            
            # Print output contains error message
            mock_stdout.write.assert_any_call(
                json.dumps({"status": "ERROR", "message": "Live mode execution is strictly rejected by safety guard."})
            )

    @patch('tools.flaos.runtime_session.get_python_processes')
    def test_detect_returns_valid_json(self, mock_get_procs):
        mock_get_procs.return_value = [
            {"pid": 101, "command": "python main.py --mode paper --interval 60"},
            {"pid": 102, "command": "python other_script.py"}
        ]
        
        runs = runtime_session.detect_active_paper_runs()
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["pid"], 101)

    @patch('tools.flaos.runtime_session.get_python_processes')
    def test_guard_behavior(self, mock_get_procs):
        # Test guard passing (no duplicate)
        mock_get_procs.return_value = [
            {"pid": 102, "command": "python other_script.py"}
        ]
        
        args = MagicMock()
        exit_code = runtime_session.cmd_guard(args)
        self.assertEqual(exit_code, 0)
        
        # Test guard failing (duplicate exists)
        mock_get_procs.return_value = [
            {"pid": 101, "command": "python main.py --mode paper --interval 60"},
            {"pid": 102, "command": "python other_script.py"}
        ]
        exit_code = runtime_session.cmd_guard(args)
        self.assertEqual(exit_code, 1)

    @patch('tools.flaos.runtime_session.is_process_alive')
    def test_cleanup_does_not_delete_logs(self, mock_is_alive):
        mock_is_alive.return_value = False
        
        meta = SessionMetadata(
            session_id=self.test_session_id,
            task_id="TEST_TASK_001",
            mode="paper",
            status="RUNNING",
            created_at="2026-06-27T12:00:00Z",
            stdout_log=f"runtime/validation/session_{self.test_session_id}_stdout.log",
            stderr_log=f"runtime/validation/session_{self.test_session_id}_stderr.log",
            metadata_path=self.metadata_path,
            pid=9999,
            expected_duration_seconds=60,
            command="python main.py"
        )
        os.makedirs("runtime/sessions", exist_ok=True)
        os.makedirs("runtime/validation", exist_ok=True)
        
        # Write dummy log files
        with open(meta.stdout_log, 'w') as f:
            f.write("stdout log info")
        with open(meta.stderr_log, 'w') as f:
            f.write("stderr log info")
        meta.save()
        
        args = MagicMock()
        args.session_id = self.test_session_id
        args.terminate = False
        
        exit_code = runtime_session.cmd_cleanup(args)
        self.assertEqual(exit_code, 0)
        
        # Verify metadata is updated to COMPLETED
        updated = SessionMetadata.load(self.metadata_path)
        self.assertEqual(updated.status, "COMPLETED")
        
        # Verify log files still exist
        self.assertTrue(os.path.exists(meta.stdout_log))
        self.assertTrue(os.path.exists(meta.stderr_log))

if __name__ == "__main__":
    unittest.main()
