#!/usr/bin/env python3
"""
AIROS v2 Atomic Batch Executor.
Executes batch migrations from batch_candidates.json atomically,
including git mv, import rewrites, targeted pytest checks, and rollback on failure.
"""

import os
import sys
import json
import argparse
import subprocess
import shutil

# Ignored directory names for import rewrites
IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "runtime",
    ".pytest_cache",
    "node_modules",
    "htmlcov",
    "dist",
    "build",
}


def rewrite_imports_in_file(filepath, import_maps):
    """Rewrite python imports to match the new relocated modules."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        modified = False
        for old, new in import_maps.items():
            # Pattern 1: from tools.abc import
            old_from = f"from {old}"
            new_from = f"from {new}"
            if old_from in content:
                content = content.replace(old_from, new_from)
                modified = True

            # Pattern 2: import tools.abc
            old_import = f"import {old}"
            new_import = f"import {new}"
            if old_import in content:
                content = content.replace(old_import, new_import)
                modified = True

            # Pattern 3: from tools import abc -> from tools.domain import abc
            parts = old.split(".")
            if len(parts) == 2 and parts[0] == "tools":
                old_from_tools = f"from tools import {parts[1]}"
                new_from_tools = f"from tools.{new.split('.')[1]} import {parts[1]}"
                if old_from_tools in content:
                    content = content.replace(old_from_tools, new_from_tools)
                    modified = True

        if modified:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Rewrote imports in: {filepath}")
    except Exception as e:
        print(f"Error rewriting imports in {filepath}: {e}", file=sys.stderr)


def run_command(cmd_str, repo_root):
    """Run shell command synchronously in the repository root."""
    print(f"Executing: {cmd_str}")
    # Normalize command for cross-platform execution (e.g. converting windows python path to standard python if needed)
    args = cmd_str.split(" ")
    if sys.platform != "win32":
        # Resolve python runner
        if args[0].endswith(".exe") or "Scripts" in args[0]:
            args[0] = sys.executable
            
    res = subprocess.run(args, cwd=repo_root, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        print(f"Command failed: {cmd_str}", file=sys.stderr)
        print(f"Stdout:\n{res.stdout}", file=sys.stderr)
        print(f"Stderr:\n{res.stderr}", file=sys.stderr)
    return res.returncode == 0


def execute_rollback(rollback_cmds, repo_root):
    """Run all rollback commands to restore pristine state."""
    print("\n--- INITIATING ROLLBACK ---", file=sys.stderr)
    for cmd in rollback_cmds:
        # Convert cmd format if needed
        args = cmd.split(" ")
        if sys.platform != "win32" and "checkout" in cmd:
            args = ["git", "checkout", "--"] + args[3:]
            
        print(f"Rolling back: {cmd}")
        subprocess.run(args, cwd=repo_root, check=False)
    print("--- ROLLBACK COMPLETE ---", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="AIROS v2 Atomic Batch Executor")
    parser.add_argument(
        "--batch-candidates",
        required=True,
        help="Path to batch_candidates.json",
    )
    parser.add_argument(
        "--batch-id",
        help="Specific Batch ID to run (defaults to recommended_next_batch)",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Path to repository root",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run: print commands without running them",
    )

    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo_root)

    if not os.path.exists(args.batch_candidates):
        print(f"Error: candidates file '{args.batch_candidates}' does not exist.", file=sys.stderr)
        sys.exit(1)

    with open(args.batch_candidates, "r", encoding="utf-8") as f:
        candidates_data = json.load(f)

    # Resolve batch
    batch_id = args.batch_id
    if not batch_id:
        batch_id = candidates_data.get("recommended_next_batch")
        if not batch_id:
            print("Error: No recommended next batch found in candidates file.", file=sys.stderr)
            sys.exit(1)

    # Find the target batch candidate
    target_batch = None
    for cand in candidates_data.get("candidates", []):
        if cand["batch_id"] == batch_id:
            target_batch = cand
            break

    if not target_batch:
        print(f"Error: Target batch '{batch_id}' not found in candidates list.", file=sys.stderr)
        sys.exit(1)

    print(f"Selected Batch: {batch_id}")
    print(f"Risk Level: {target_batch['risk_level']}")
    print(f"Files to Move: {len(target_batch['source_paths'])}")

    # Safety Gate Check
    if target_batch["risk_level"] not in ("SAFE_ATOMIC", "MEDIUM_ATOMIC"):
        print(f"Error: Execution of '{batch_id}' blocked. Risk level is '{target_batch['risk_level']}' (only SAFE/MEDIUM allowed).", file=sys.stderr)
        sys.exit(1)

    # Create mapping of old import module to new import module
    import_maps = {}
    for sp, tp in zip(target_batch["source_paths"], target_batch["target_paths"]):
        old_mod = sp.replace(".py", "").replace("/", ".")
        new_mod = tp.replace(".py", "").replace("/", ".")
        import_maps[old_mod] = new_mod

    if args.dry_run:
        print("\n--- DRY RUN: Listing Moves ---")
        for sp, tp in zip(target_batch["source_paths"], target_batch["target_paths"]):
            print(f"git mv {sp} -> {tp}")
        print("\n--- DRY RUN: Imports Rewrite Map ---")
        print(json.dumps(import_maps, indent=2))
        sys.exit(0)

    # 1. Execute Git Moves
    moved_files = []
    try:
        for sp, tp in zip(target_batch["source_paths"], target_batch["target_paths"]):
            source_abs = os.path.join(repo_root, sp)
            target_abs = os.path.join(repo_root, tp)
            
            # Ensure parent directories exist
            os.makedirs(os.path.dirname(target_abs), exist_ok=True)
            
            print(f"Moving: {sp} -> {tp}")
            # Run git mv
            res = subprocess.run(["git", "mv", sp, tp], cwd=repo_root, capture_output=True, text=True, check=False)
            if res.returncode != 0:
                # Fallback to shutil.move and git add/rm
                if os.path.exists(source_abs):
                    shutil.move(source_abs, target_abs)
                    subprocess.run(["git", "add", tp], cwd=repo_root, check=False)
                    subprocess.run(["git", "rm", sp], cwd=repo_root, check=False)
                else:
                    raise Exception(f"Failed to move file {sp}. Git mv returned: {res.stderr}")
                    
            moved_files.append((sp, tp))
    except Exception as e:
        print(f"Failed to execute moves: {e}", file=sys.stderr)
        execute_rollback(target_batch["rollback_commands"], repo_root)
        sys.exit(1)

    # 2. Rewrite Imports in affected files
    # Scan all files under tools/ and tests/ to perform rewriting
    for folder in ("tools", "tests"):
        folder_abs = os.path.join(repo_root, folder)
        if not os.path.exists(folder_abs):
            continue
        for root, dirs, files in os.walk(folder_abs):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    rewrite_imports_in_file(file_path, import_maps)

    # 3. Compile Moved Files
    for cmd in target_batch.get("compile_commands", []):
        if not run_command(cmd, repo_root):
            print("Compilation check failed!", file=sys.stderr)
            execute_rollback(target_batch["rollback_commands"], repo_root)
            sys.exit(1)

    # 4. Run Pytest Checks
    for cmd in target_batch.get("pytest_commands", []):
        if not run_command(cmd, repo_root):
            print("Targeted test check failed!", file=sys.stderr)
            execute_rollback(target_batch["rollback_commands"], repo_root)
            sys.exit(1)

    print(f"\nSuccessfully executed batch '{batch_id}' atomically!")


if __name__ == "__main__":
    main()
