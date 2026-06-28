# AIROS_V2_MIGRATION_COMPILER_SPEC_001

**Status:** ACTIVE  
**Date:** 2026-06-28  
**Purpose:** Implementation specification for the AIROS v2 Migration Compiler.

---

## 1. Translating Batches into Executable Task Plans

The Migration Compiler consumes the selected batch from `batch_candidates.json` and produces a concrete, executable script/plan.

---

## 2. Command Generation Rules

### 2.1 Git Move Generation
The compiler iterates over the `files_to_move` array and generates exact `git mv` shell commands:
```powershell
# Generated move script block
git mv tools/file1.py tools/folder/file1.py
```
*Creates parent directories using `mkdir -Force` prior to the move.*

### 2.2 Import Rewrite Guidance
The compiler maps all import changes by:
1. Scanning test files and other tools for `import tools.file1` or `from tools.file1 import`.
2. Emitting regex-based replacement rules for code editing tools:
   * **Target:** `from tools.file1`
   * **Replacement:** `from tools.folder.file1`

### 2.3 Targeted Compilation (`py_compile`)
The compiler generates exact verification scripts to compile all moved files:
```powershell
.venv\Scripts\python.exe -m py_compile tools/folder/file1.py
```

### 2.4 Targeted Pytest Generation
The compiler resolves the test files from `test_registry.json` and generates the pytest runner line:
```powershell
.venv\Scripts\python.exe -m pytest tests/test_file1.py -q
```
*Ensures `-q` flag is used to limit console output verbosity.*

### 2.5 Docs/Index Refresh Generation
The compiler automatically targets links in indices:
* Rewrites `FILE_INDEX.md` line matching `tools/file1.py` to `tools/folder/file1.py`.
* Prepares markdown link updates for `DOCUMENTATION_MAP.md` and `README.md`.

---

## 3. Rollback Command Generation

The compiler generates a corresponding `rollback_script.ps1` file for every execution batch:
```powershell
# Automatically generated rollback pipeline
git mv tools/folder/file1.py tools/file1.py
git checkout -- tests/test_file1.py docs/operations/ACTIVE_WORKFLOW_STATE_001.json TASK_QUEUE_001.json
```
*No hard resets allowed unless explicitly approved by the operator.*

---

## 4. Commit/Push Protocol

The compiler enforces commit cohesion:
1. **Staging:** `git add` exactly the moved files, updated tests, reports, and ops updates.
2. **Commit:** `git commit -m "refactor(batch): move <Batch Name> tools to tools/<folder>/"`
3. **Sync:** `git push origin main` immediately after successful commit validation.
