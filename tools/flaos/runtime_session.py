import argparse
import datetime
import json
import os
import signal
import subprocess
import sys
from typing import Optional

# Ensure tools/flaos is on Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from session_schema import SessionMetadata

def get_python_processes() -> list[dict]:
    processes = []
    current_pid = os.getpid()
    
    if sys.platform == 'win32':
        try:
            # Run wmic to get command lines and process ids
            output = subprocess.check_output(
                'wmic process where "name=\'python.exe\'" get ProcessID, CommandLine',
                shell=True,
                text=True
            )
            lines = output.strip().split('\n')
            if len(lines) > 1:
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    # ProcessID is typically the last column
                    parts = line.strip().rsplit(None, 1)
                    if len(parts) == 2:
                        cmd, pid_str = parts
                        try:
                            pid = int(pid_str)
                            if pid != current_pid:
                                processes.append({"pid": pid, "command": cmd})
                        except ValueError:
                            pass
        except Exception:
            pass
    else:
        try:
            # Run ps to get command lines and process ids on Unix/macOS
            output = subprocess.check_output('ps -eo pid,args', shell=True, text=True)
            for line in output.strip().split('\n'):
                if not line.strip() or "ps -eo" in line:
                    continue
                parts = line.strip().split(None, 1)
                if len(parts) == 2:
                    pid_str, cmd = parts
                    try:
                        pid = int(pid_str)
                        if pid != current_pid and "python" in cmd.lower():
                            processes.append({"pid": pid, "command": cmd})
                    except ValueError:
                        pass
        except Exception:
            pass
            
    return processes

def detect_active_paper_runs() -> list[dict]:
    procs = get_python_processes()
    paper_runs = []
    for p in procs:
        cmd = p["command"].lower()
        # Verify it's the paper run script and not the session manager itself
        if "main.py" in cmd and "mode paper" in cmd and "runtime_session.py" not in cmd:
            paper_runs.append(p)
    return paper_runs

def is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == 'win32':
        try:
            # Check process using tasklist on Windows
            output = subprocess.check_output(
                f'tasklist /FI "PID eq {pid}"',
                shell=True,
                text=True
            )
            return str(pid) in output
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

def terminate_process(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if sys.platform == 'win32':
            subprocess.check_call(f'taskkill /PID {pid} /T /F', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(pid, signal.SIGKILL)
        return True
    except Exception:
        return False

def cmd_create(args) -> int:
    if args.mode.lower() == 'live':
        print(json.dumps({"status": "ERROR", "message": "Live mode execution is strictly rejected by safety guard."}))
        return 1
        
    session_id = args.session_id or datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    # Define paths
    os.makedirs("runtime/validation", exist_ok=True)
    os.makedirs("runtime/sessions", exist_ok=True)
    
    stdout_log = f"runtime/validation/session_{session_id}_stdout.log"
    stderr_log = f"runtime/validation/session_{session_id}_stderr.log"
    metadata_path = f"runtime/sessions/session_{session_id}.json"
    
    # Check if session file already exists
    if os.path.exists(metadata_path):
        print(json.dumps({"status": "ERROR", "message": f"Session metadata already exists for session_id '{session_id}'."}))
        return 1
        
    command = f"python main.py --mode {args.mode} --interval 60 --ui auto --fps medium"
    
    metadata = SessionMetadata(
        session_id=session_id,
        task_id=args.task_id,
        mode=args.mode,
        status="CREATED",
        created_at=datetime.datetime.utcnow().isoformat() + "Z",
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        metadata_path=metadata_path,
        pid=None,
        expected_duration_seconds=args.expected_duration,
        command=command
    )
    
    metadata.save()
    print(metadata.to_json())
    return 0

def cmd_status(args) -> int:
    metadata_path = f"runtime/sessions/session_{args.session_id}.json"
    if not os.path.exists(metadata_path):
        print(json.dumps({"status": "ERROR", "message": f"Session metadata file not found: {metadata_path}"}))
        return 1
        
    try:
        metadata = SessionMetadata.load(metadata_path)
    except Exception as e:
        print(json.dumps({"status": "ERROR", "message": f"Failed to load session metadata: {e}"}))
        return 1
        
    pid = metadata.pid
    alive = is_process_alive(pid) if pid else False
    
    # Calculate elapsed seconds
    created_dt = datetime.datetime.fromisoformat(metadata.created_at.replace("Z", ""))
    elapsed = int((datetime.datetime.utcnow() - created_dt).total_seconds())
    
    status_data = {
        "session_id": metadata.session_id,
        "task_id": metadata.task_id,
        "status": metadata.status,
        "pid": pid,
        "process_alive": alive,
        "elapsed_seconds": elapsed,
        "stdout_log": metadata.stdout_log,
        "stderr_log": metadata.stderr_log,
        "metadata_path": metadata.metadata_path
    }
    
    print(json.dumps(status_data, indent=2))
    return 0

def cmd_detect(args) -> int:
    runs = detect_active_paper_runs()
    print(json.dumps({"active_runs": runs}, indent=2))
    return 0

def cmd_guard(args) -> int:
    runs = detect_active_paper_runs()
    if runs:
        print(json.dumps({
            "status": "DUPLICATE_RUN_DETECTED",
            "message": "Duplicate paper runtime is currently active. Launch blocked.",
            "active_runs": runs
        }, indent=2))
        return 1
    
    print(json.dumps({"status": "OK", "message": "No active duplicate paper runs detected."}))
    return 0

def cmd_cleanup(args) -> int:
    metadata_path = f"runtime/sessions/session_{args.session_id}.json"
    if not os.path.exists(metadata_path):
        print(json.dumps({"status": "ERROR", "message": f"Session metadata file not found: {metadata_path}"}))
        return 1
        
    try:
        metadata = SessionMetadata.load(metadata_path)
    except Exception as e:
        print(json.dumps({"status": "ERROR", "message": f"Failed to load session metadata: {e}"}))
        return 1
        
    pid = metadata.pid
    terminated = False
    
    if pid and is_process_alive(pid):
        if args.terminate:
            terminated = terminate_process(pid)
            metadata.status = "TERMINATED"
        else:
            metadata.status = "UNKNOWN"
    else:
        metadata.status = "COMPLETED"
        
    metadata.save()
    
    print(json.dumps({
        "session_id": metadata.session_id,
        "status": metadata.status,
        "pid": pid,
        "terminated_successfully": terminated
    }, indent=2))
    return 0

def cmd_launch(args) -> int:
    if args.mode.lower() == 'live':
        print(json.dumps({"status": "ERROR", "message": "Live mode execution is strictly rejected by safety guard."}))
        return 1
        
    # Check guard
    runs = detect_active_paper_runs()
    if runs:
        print(json.dumps({
            "status": "ERROR",
            "message": "Duplicate paper runtime is active. Launch blocked.",
            "active_runs": runs
        }, indent=2))
        return 1
        
    session_id = args.session_id or datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    os.makedirs("runtime/validation", exist_ok=True)
    os.makedirs("runtime/sessions", exist_ok=True)
    
    stdout_log = f"runtime/validation/session_{session_id}_stdout.log"
    stderr_log = f"runtime/validation/session_{session_id}_stderr.log"
    metadata_path = f"runtime/sessions/session_{session_id}.json"
    
    if os.path.exists(metadata_path):
        print(json.dumps({"status": "ERROR", "message": f"Session metadata already exists for session_id '{session_id}'."}))
        return 1
        
    # Setup process execution command list
    cmd_list = [
        sys.executable,
        "main.py",
        "--mode", args.mode,
        "--interval", "60",
        "--ui", "auto",
        "--fps", "medium"
    ]
    
    command_str = " ".join(cmd_list)
    
    metadata = SessionMetadata(
        session_id=session_id,
        task_id=args.task_id,
        mode=args.mode,
        status="RUNNING",
        created_at=datetime.datetime.utcnow().isoformat() + "Z",
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        metadata_path=metadata_path,
        pid=None,
        expected_duration_seconds=args.expected_duration,
        command=command_str
    )
    
    # Save metadata first to ensure record exists
    metadata.save()
    
    try:
        out_f = open(stdout_log, 'w', encoding='utf-8')
        err_f = open(stderr_log, 'w', encoding='utf-8')
        
        p = subprocess.Popen(
            cmd_list,
            stdout=out_f,
            stderr=err_f
        )
        
        metadata.pid = p.pid
        metadata.save()
    except Exception as e:
        metadata.status = "FAILED"
        metadata.save()
        print(json.dumps({"status": "ERROR", "message": f"Failed to spawn runtime process: {e}"}))
        return 1
        
    print(metadata.to_json())
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description="FLAOS Runtime Session Coordinator Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # create subcommand
    p_create = subparsers.add_parser("create", help="Create a session metadata file")
    p_create.add_argument("--session-id", help="Session ID (optional)")
    p_create.add_argument("--task-id", required=True, help="Task ID reference")
    p_create.add_argument("--mode", required=True, help="Execution mode (paper/live)")
    p_create.add_argument("--expected-duration", type=int, default=60, help="Expected duration in seconds")
    
    # status subcommand
    p_status = subparsers.add_parser("status", help="Get status of a session")
    p_status.add_argument("--session-id", required=True, help="Session ID")
    
    # detect subcommand
    subparsers.add_parser("detect", help="Detect active paper runs")
    
    # guard subcommand
    subparsers.add_parser("guard", help="Verify if active duplicates exist")
    
    # cleanup subcommand
    p_cleanup = subparsers.add_parser("cleanup", help="Cleanup session status")
    p_cleanup.add_argument("--session-id", required=True, help="Session ID")
    p_cleanup.add_argument("--terminate", action="store_true", help="Terminate process if still running")
    
    # launch subcommand
    p_launch = subparsers.add_parser("launch", help="Launch paper mode asynchronously")
    p_launch.add_argument("--session-id", help="Session ID (optional)")
    p_launch.add_argument("--task-id", required=True, help="Task ID reference")
    p_launch.add_argument("--mode", required=True, help="Execution mode")
    p_launch.add_argument("--expected-duration", type=int, default=60, help="Expected duration in seconds")
    
    args = parser.parse_args()
    
    if args.command == "create":
        return cmd_create(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "detect":
        return cmd_detect(args)
    elif args.command == "guard":
        return cmd_guard(args)
    elif args.command == "cleanup":
        return cmd_cleanup(args)
    elif args.command == "launch":
        return cmd_launch(args)
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
