# TECHNICAL_DEBT_REGISTER_001

**Task:** REPOSITORY_ORGANIZATION_AUDIT_001  
**Mode:** DISCOVERY ONLY  
**Date:** 2026-06-26

---

## Severity Definitions

| Level | Meaning |
|---|---|
| CRITICAL | Actively impairs development, AI context loading, or navigation |
| HIGH | Significant bloat, confusion, or risk — should fix before next major feature |
| MEDIUM | Real debt, no immediate impact on functionality |
| LOW | Cosmetic or minor — address during regular maintenance |

---

## CRITICAL Debt

---

### DEBT-001: Root Directory Markdown Pollution

**Severity:** CRITICAL  
**Files affected:** 395 markdown files in repository root  
**Size impact:** ~10–15 MB of markdown in root  

**Description:**  
Every audit report, design doc, patch report, forensic investigation, commit record, and implementation note from the project's history has been written to the repository root. 395 of 408 root files are markdown.

This makes the root directory:
1. Unnavigable for humans scrolling directory listings
2. Extremely expensive for AI context loading (agent must parse 395 filenames to locate relevant docs)
3. Git status output is always overwhelming (any new file appears as `??` in a sea of noise)
4. PR diffs are polluted with root-level doc additions

**Prior attempt:**  
`ROOT_MD_BATCH_1_MOVE_REPORT_001.md` and `ROOT_MD_BATCH_2_MOVE_REPORT_001.md` document two prior move batches. The plan existed but was not fully executed. `ROOT_MD_REORGANIZATION_PLAN_001.md` (35KB) contains the prior plan.

**Fix:** Move all ~376 moveable markdown files from root to organized `docs/` subfolders. See `SAFE_MOVE_PLAN_001.md`.

**Risk:** LOW — markdown files have no runtime dependencies. Only AI context file references (FILE_INDEX.md, DOCUMENTATION_MAP.md) need updating after move.

---

### DEBT-002: Multiple Abandoned Virtual Environment Backups in Root

**Severity:** CRITICAL  
**Folders:** `.venv_BROKEN_poh2_py312_backup/`, `.venv_broken_POOHXYZ_migration_backup/`, `.venv_migration_old_backup/`  

**Description:**  
Three full Python virtual environment backups exist in the project root alongside the active `.venv`. Each contains thousands of files (packages, compiled extensions, etc.). These are:
- Polluting directory listings
- Consuming significant disk space (each venv is likely 500MB+)
- Potentially confusing tooling that auto-discovers Python environments

These were created during Python version migrations and were never cleaned up.

**Fix:** Delete all three backup venvs. Verify active `.venv` is functional first. Add `/.venv*/` pattern to `.gitignore` to prevent future backup venvs from being tracked.

**Risk:** ZERO to runtime — these are package caches, not code. Python `pip install -r requirements.txt` recreates the active venv if needed.

---

## HIGH Debt

---

### DEBT-003: Secondary Mode Folders Colocated as Top-Level Directories

**Severity:** HIGH  
**Folders:** `hft/`, `crypto_scalper/`

**Description:**  
Two standalone trading sub-projects exist as top-level directories in the PolyTrade repository root. They are **not orphaned** — `main.py` imports from both:

```python
# main.py line 17
from crypto_scalper.live_runner import main as run_scalper
# main.py line 1313
from crypto_scalper.realtime_feed import CryptoRealtimeFeed
# main.py line 1410
from hft.main import run_hft
```

A test also mocks the import path:
```python
# tests/test_runtime_shutdown.py line 83
monkeypatch.setitem(sys.modules, "crypto_scalper.live_runner", ...)
```

- `hft/` — HFT engine with its own `main.py`, `config.py`, `risk_manager.py`, `signal_engine.py`, `strategy_engine.py`, `execution_engine.py`, `market_manager.py`, `utils.py` (10 files)
- `crypto_scalper/` — 5-minute scalper with its own `main.py`, `config.py`, `backtest.py`, `realtime_feed.py`, `market_data.py` (7 files)

Both have compiled `.pyc` artifacts for Python 3.11 and 3.12. `hft_paper_run.py` in root is a separate entry point for the HFT engine.

The problem is not orphaning — it is that these projects live at top-level repo scope rather than in a clearly bounded `experiments/` namespace. The colocated structure obscures their secondary status relative to the core `polymarket/` engine.

**Fix:** Move both to `experiments/hft/` and `experiments/crypto_scalper/`. This requires:
1. Update `main.py` import paths (3 import statements)
2. Update the test mock in `tests/test_runtime_shutdown.py` (1 reference)
3. Update `hft_paper_run.py` (entry point — review its imports)
4. Add `__init__.py` to `experiments/` to maintain package resolution

**Risk:** HIGH — `main.py` imports both modules by package name. Moving the folders without updating all imports will break `python main.py` for the `crypto_scalper` and `hft` modes. Must update import paths atomically with the move.

---

### DEBT-004: Three Competing Dashboard Directories

**Severity:** HIGH  
**Folders:** `dashboard/`, `research_cockpit/`, `web-dashboard/`

**Description:**  
Three separate React dashboard builds exist:

| Folder | Status | Content |
|---|---|---|
| `dashboard/` | Active — React (Vite + TypeScript), has full src/, dist/, and Python backends | Active development |
| `research_cockpit/` | Orphaned — separate Vite project, only has index.html, package.json, and a dist/ | Abandoned prototype |
| `web-dashboard/` | Orphaned — another React build structure | Abandoned prototype |

Only `dashboard/` shows active development (recent commits touch `dashboard/src/pages/`). The others appear to be abandoned prototypes that were never removed.

**Fix:** Archive or delete `research_cockpit/` and `web-dashboard/` after confirming no test or build references.

**Risk:** MEDIUM — check if any Python file imports or references these paths.

---

### DEBT-005: Compiled .pyc Files Alongside Source Files (Not Git-Tracked)

**Severity:** MEDIUM (downgraded from HIGH — these are NOT git-tracked)  
**Folders:** `tools/` (44 .pyc files on disk), `tests/` (542 .pyc files on disk), `crypto_scalper/` (mixed)

**Description:**  
Python bytecode files (.pyc) are present alongside source files on disk:

- `tools/`: 35 source `.py` files each with `.cpython-311.pyc` AND `.cpython-312.pyc` siblings — 210+ .pyc files not in `__pycache__/`
- `tests/`: 542 `.pyc` files alongside 139 `.py` test files

**Verified:** `git ls-files | grep \.pyc` returns **zero results** — none are git-tracked. The `.gitignore` is already effective at excluding them from commits. The debt is not git pollution; it is disk clutter from Python runs that placed .pyc files outside `__pycache__/` directories (Python 2 behavior or direct execution patterns).

**Fix:**
1. Confirm `.gitignore` has `**/__pycache__/` and `**/*.pyc` rules — if missing, add them to prevent future accidents
2. `git rm --cached **/*.pyc` is **NOT needed** — nothing is tracked
3. Optionally: delete .pyc files from disk with PowerShell `Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item` (they regenerate on next import)

**Risk:** ZERO — .pyc are build artifacts. Python regenerates them on next import. No git state to clean.

---

### DEBT-006: `logs/` Has 980 Files Flat in Root

**Severity:** HIGH  
**Folder:** `logs/`

**Description:**  
`logs/` has 980 files in its root with no subdirectory structure. This creates extremely slow directory listing (Windows Explorer and certain tools struggle with large flat directories).

**Fix:** Either:
- Migrate to `runtime/realtime_logs/` (which already has this structure) and remove `logs/`
- OR add date-based subdirectories to `logs/` (logs/2026-06/, logs/2026-05/, etc.)

**Risk:** MEDIUM — confirm no hardcoded paths reference `logs/` in Python code before restructuring.

---

### DEBT-007: `main.py` Is a Monolithic 63KB File

**Severity:** HIGH  
**File:** `main.py`

**Description:**  
`main.py` is 63,323 bytes — approximately 1,500-2,000 lines of Python. For an "entry point," this is extremely large. It appears to contain routing logic, mode handlers, paper trading setup, verification logic, and potentially more.

This is a readability and maintainability issue — any AI agent or developer who reads `main.py` for context must parse a very large file.

**Fix:** Decompose `main.py` into mode-specific handlers (e.g., `modes/paper.py`, `modes/backtest.py`, `modes/verify.py`) with `main.py` remaining as a thin dispatcher.

**Risk:** HIGH for code change — requires careful testing. LOW for documentation. Note for future refactor task.

---

## MEDIUM Debt

---

### DEBT-008: `scratch/` Has No Boundary or .gitignore

**Severity:** MEDIUM  
**Folder:** `scratch/`

**Description:**  
237 files (120 JSONL, 60 Python, 49 JSON, 6 MD, 2 SQLite) with no clear naming convention, no README, and no .gitignore. It is unclear which files are active experiments vs abandoned.

**Fix:** Add `scratch/.gitignore` with `*` (ignore everything) and document in README that scratch/ is a local-only workspace.

**Risk:** LOW — if scratch/ content is needed, document it; otherwise exclude from git.

---

### DEBT-009: `api/` Is a Single-File Folder

**Severity:** MEDIUM  
**Folder:** `api/`

**Description:**  
`api/dashboard_api.py` is the only file in `api/`. This thin wrapper folder adds unnecessary nesting. The file should live in `dashboard/` where the rest of the dashboard code lives.

**Fix:** Move `api/dashboard_api.py` → `dashboard/dashboard_api.py` and remove empty `api/` folder.

**Risk:** LOW — check import references in `dashboard/app.py` or equivalent.

---

### DEBT-010: Duplicate Documentation Files

**Severity:** MEDIUM  

| Root file | docs/ file | Issue |
|---|---|---|
| `KNOWN_ISSUES.md` (267B) | `docs/KNOWN_ISSUES.md` (18.7KB) | Root is a 267-byte stub |
| `PROJECT_STRUCTURE.md` (671B) | `docs/PROJECT_STRUCTURE.md` (13.4KB) | Root is a 671-byte stub |
| `BANKROLL_TIER_FRAMEWORK_V1.md` | `docs/BANKROLL_TIER_FRAMEWORK_V1.md` | Same file in two places |

**Fix:** Delete root stubs after verifying docs/ copies are current. Keep only one copy of BANKROLL_TIER_FRAMEWORK_V1.

---

### DEBT-011: `.env.backup.local` in Repository Root

**Severity:** MEDIUM (SECURITY concern)  
**File:** `.env.backup.local`

**Description:**  
A backup of the `.env` file (containing API keys, secrets) exists in the repository root. Even if `.gitignore` excludes it, its presence is a risk. This file should never have been created in the repo directory.

**Fix:** Delete `.env.backup.local` and store env backups in a secure location outside the repository (password manager, secrets manager, or encrypted vault).

---

### DEBT-012: `docs.zip` in Root

**Severity:** MEDIUM  
**File:** `docs.zip` (66KB)

**Description:**  
A zip archive of documentation exists in the root. The contents are unknown. It may be a backup from before `docs/` was reorganized.

**Fix:** Extract and compare against current docs/. If content is already in docs/, delete the zip.

---

### DEBT-013: `memory/` Is in Project Root

**Severity:** MEDIUM  
**Folder:** `memory/`

**Description:**  
`memory/` contains two AI memory files (`MEMORY.md`, `project_exit_convergence_replay.md`). These are Claude session memory files and would be better stored in `.claude/` alongside other Claude-specific files.

**Fix:** Move `memory/` → `.claude/memory/` (or rename `.claude/` accordingly).

---

### DEBT-014: `research/` and `docs/research/` Overlap

**Severity:** MEDIUM  
**Folders:** `research/` (18 files) vs `docs/research/` (352 files)

**Description:**  
Two separate "research" directories exist. `research/` contains:
- Session notes (2026-04-18.md through 2026-05-16.md)
- Experimental Python files (markov_analysis.py, markov_backtest.py)
- Research metadata (OVERVIEW.md, TEMPLATE.md, session_memory_template.md)

`docs/research/` contains the bulk of research documents (352 files).

There is no clear rule for what goes in `research/` vs `docs/research/`. New research documents have been landing in root instead of either.

**Fix:** Define a rule: `research/` = live experiment code + session notes; `docs/research/` = completed research documents.

---

### DEBT-015: `PROJECT_CENSUS_AUDIT_001.md` May Be Superseded

**Severity:** MEDIUM  
**File:** `PROJECT_CENSUS_AUDIT_001.md` (15.8KB)

**Description:**  
This file appears to be a prior repository census. It may contain stale information now that `REPOSITORY_ORGANIZATION_AUDIT_001.md` (this audit) supersedes it.

**Fix:** After completing this audit cycle, mark PROJECT_CENSUS_AUDIT_001.md as superseded and move to docs/audits/.

---

## LOW Debt

---

### DEBT-016: Inconsistent Naming Conventions

**Severity:** LOW  

Several markdown files use different case conventions:
- Most use `UPPER_CASE_WITH_UNDERSCORES_001.md`
- Some use `lower_case_with_underscores_001.md` (e.g., `no_signal_root_cause_audit_001.md`, `decision_gate_audit_summary.md`)
- Some use `lower_case_mixed.md` (e.g., `dashboard_v2a_commit_report.md`)
- Some have dates in filename (e.g., `overnight_maturity_check_2026-05-19.md`)
- Some have no number suffix (e.g., `EVIDENCE_QUALITY_AUDIT.md` vs `EVIDENCE_QUALITY_AUDIT_001.md`)

**Fix:** Establish a single convention: `UPPER_CASE_TOPIC_NNNNN_NNNNN.md` for research/audit/reports, `UPPER_CASE_V1.md` for versioned design docs.

---

### DEBT-017: `task.md` in Root

**Severity:** LOW  
**File:** `task.md` (863B)

**Description:**  
A temporary task note is in the root directory. This appears to be a leftover working note.

**Fix:** Delete or move to scratch/.

---

### DEBT-018: `implementation_plan.md` in Root

**Severity:** LOW  
**File:** `implementation_plan.md` (3.0KB)

**Description:**  
A generic `implementation_plan.md` without context in filename. Likely stale.

**Fix:** Inspect content and either delete or rename with proper prefix and move to docs/.

---

### DEBT-019: Scripts Split Between Root and `scripts/`

**Severity:** LOW  

Scripts currently in root that should be in `scripts/`:
- `check_balance.py`
- `daily_report.py`
- `generate_bypass.py`
- `register_api_keys.py`

Scripts currently in `scripts/`:
- `ai_analyst.py`
- `hft_paper_summary.py`
- `vultr_deploy_paper.py`

**Fix:** Move root scripts to `scripts/` — 4 files, no import dependencies.

---

## Debt Registry Summary

| ID | Severity | Description | Fix Risk |
|---|---|---|---|
| DEBT-001 | CRITICAL | 395 markdown files in root | LOW |
| DEBT-002 | CRITICAL | 3 venv backups in root | ZERO |
| DEBT-003 | HIGH | hft/ and crypto_scalper/ at top-level (imported by main.py — NOT orphaned) | HIGH |
| DEBT-004 | HIGH | 3 competing dashboard directories | MEDIUM |
| DEBT-005 | MEDIUM | .pyc files on disk (NOT git-tracked) — disk clutter only | ZERO |
| DEBT-006 | HIGH | logs/ 980 files flat | MEDIUM |
| DEBT-007 | HIGH | main.py monolithic 63KB | HIGH |
| DEBT-008 | MEDIUM | scratch/ no boundary | LOW |
| DEBT-009 | MEDIUM | api/ single-file folder | LOW |
| DEBT-010 | MEDIUM | Duplicate docs (3 pairs) | LOW |
| DEBT-011 | MEDIUM | .env.backup.local in root | LOW (delete) |
| DEBT-012 | MEDIUM | docs.zip in root | LOW |
| DEBT-013 | MEDIUM | memory/ in root | LOW |
| DEBT-014 | MEDIUM | research/ vs docs/research/ overlap | LOW |
| DEBT-015 | MEDIUM | PROJECT_CENSUS_AUDIT superseded | LOW |
| DEBT-016 | LOW | Naming convention inconsistency | LOW |
| DEBT-017 | LOW | task.md in root | LOW |
| DEBT-018 | LOW | implementation_plan.md in root | LOW |
| DEBT-019 | LOW | Scripts split between root and scripts/ | LOW |

**Total: 2 CRITICAL, 4 HIGH, 9 MEDIUM, 4 LOW**  
*(DEBT-005 downgraded HIGH→MEDIUM after verifying .pyc files are NOT git-tracked)*
