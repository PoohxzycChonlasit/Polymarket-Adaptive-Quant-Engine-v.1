# SAFE_MOVE_PLAN_001

**Task:** REPOSITORY_ORGANIZATION_AUDIT_001  
**Mode:** DISCOVERY ONLY — DO NOT EXECUTE  
**Date:** 2026-06-26  
**Status:** PROPOSED — requires explicit approval before any moves

---

## How to Read This Document

Each section is an independent batch. Batches are ordered by risk: lowest-risk actions first.

For each move:
- **Current** → where the file is now
- **Proposed** → where it should go
- **Reason** → why
- **Risk** → what could break
- **Files needing update** → which files reference the current path

**Do NOT execute anything in this document without the user explicitly assigning each batch.**

---

## BATCH 0 — Deletions and Cleanup (Zero-Risk)

These are pure deletions or removals. Nothing depends on them.

### 0.1 — Delete Abandoned Venv Backups

| Action | Path |
|---|---|
| DELETE FOLDER | `.venv_BROKEN_poh2_py312_backup/` |
| DELETE FOLDER | `.venv_broken_POOHXYZ_migration_backup/` |
| DELETE FOLDER | `.venv_migration_old_backup/` |

**Risk:** ZERO — these are package caches. Active venv is `.venv/`.  
**Files needing update:** None.  
**Pre-condition:** Verify `.venv/` is functional (`python -m pip list` or `pytest -q tests/test_paper_mode.py`).

---

### 0.2 — Delete Sensitive Backup File

| Action | Path |
|---|---|
| DELETE FILE | `.env.backup.local` |

**Risk:** ZERO — if credentials are needed, they are in `.env` or should be in a secrets manager.  
**Files needing update:** None.  
**Note:** Verify `.gitignore` includes `.env.backup*` to prevent recurrence.

---

### 0.3 — Delete Root Stub Files (Superseded by docs/ copies)

Verify content first — these are believed to be stubs but confirm before deleting.

| Action | Path | Verify Against |
|---|---|---|
| DELETE after verify | `KNOWN_ISSUES.md` (267B) | `docs/KNOWN_ISSUES.md` (18.7KB) |
| DELETE after verify | `PROJECT_STRUCTURE.md` (671B) | `docs/PROJECT_STRUCTURE.md` (13.4KB) |

**Risk:** LOW — stubs are tiny; canonical copies are in docs/.  
**Pre-condition:** Read both copies and confirm docs/ version is current.

---

### 0.4 — Verify .gitignore Covers .pyc Files (NOT a git-tracking cleanup)

**Verified finding:** `git ls-files | grep \.pyc` returns zero results — .pyc files are already NOT git-tracked. The `git rm --cached` step is a no-op and should NOT be executed.

The actual action is narrower:

| Action | Scope |
|---|---|
| Verify `.gitignore` has | `**/__pycache__/` and `**/*.pyc` rules |
| Optional: delete disk artifacts | `Get-ChildItem -Recurse -Filter "*.pyc" \| Remove-Item` |

**Risk:** ZERO — .pyc are build artifacts; they regenerate on next Python import.  
**Files needing update:** `.gitignore` only if the rules are missing.

---

### 0.5 — Move docs.zip

| Current | Proposed |
|---|---|
| `docs.zip` | `archive/docs_snapshot.zip` |

**Risk:** ZERO — not referenced by any code.

---

### 0.6 — Delete or Move task.md

| Action | Path |
|---|---|
| DELETE (if stale) OR MOVE | `task.md` → `scratch/task.md` |

**Risk:** ZERO.

---

## BATCH 1 — Move Root Python Scripts to scripts/

Low risk — no import dependencies for these utility scripts.

| Current | Proposed | Risk |
|---|---|---|
| `check_balance.py` | `scripts/check_balance.py` | LOW — check no other scripts call it |
| `daily_report.py` | `scripts/daily_report.py` | LOW — check no tests import it |
| `generate_bypass.py` | `scripts/generate_bypass.py` | LOW — read file first, confirm purpose |
| `register_api_keys.py` | `scripts/register_api_keys.py` | LOW — check no runtime references |
| `hft_paper_run.py` | `experiments/hft/hft_paper_run.py` | LOW — moves with hft/ folder |

**Files needing update:**  
- README.md (if it references these scripts by path)
- CLAUDE.md commands section (if it references these scripts)
- Any documentation that shows commands to run these scripts

---

## BATCH 2 — Move Single-File Folder

**Verified import dependencies (from actual grep):**
- `tests/test_dashboard_api.py` line 6: `from api.dashboard_api import create_app` — this test file MUST be updated alongside the move
- No other Python files in `dashboard/`, `polymarket/`, `utils/`, `tools/` reference `api.dashboard_api`

| Current | Proposed | Risk | Files Needing Update |
|---|---|---|---|
| `api/dashboard_api.py` | `dashboard/dashboard_api.py` | LOW | `tests/test_dashboard_api.py` line 6 (confirmed); check `dashboard/app.py` for import path; check startup scripts |

**Execute atomically:** Move the file AND update `tests/test_dashboard_api.py` in the same operation. A move without the test update will cause test failures.

**Pre-condition:** Confirm no other references: grep all `.py` files for `api.dashboard_api` before moving.

---

## BATCH 3 — Move memory/ into .claude/

| Current | Proposed | Risk | Files Needing Update |
|---|---|---|---|
| `memory/MEMORY.md` | `.claude/memory/MEMORY.md` | LOW | CLAUDE.md auto-memory section references `C:\Users\...\memory\` — check system config |
| `memory/project_exit_convergence_replay.md` | `.claude/memory/project_exit_convergence_replay.md` | LOW | Same |

**Note:** The auto-memory system in CLAUDE.md references a path at `C:\Users\poh_2\.claude\projects\...`. Verify which `memory/` this references — it may be the user-level memory, not the project-level one.

---

## BATCH 4 — Move Secondary Mode Projects to experiments/

**⚠ RISK RECLASSIFIED: HIGH** — `main.py` imports both packages by name. Moving the folders without updating imports breaks `python main.py` for the `crypto_scalper` and `hft` modes.

**Confirmed imports (verified from actual source):**
```python
# main.py line 17
from crypto_scalper.live_runner import main as run_scalper
# main.py line 1313
from crypto_scalper.realtime_feed import CryptoRealtimeFeed
# main.py line 1410
from hft.main import run_hft
```

**Confirmed test references — COMPLETE import map (verified via grep, 2026-06-26):**

External imports (break if folders move without sys.path or rename approach):
```python
# main.py line 17
from crypto_scalper.live_runner import main as run_scalper
# main.py line 1313
from crypto_scalper.realtime_feed import CryptoRealtimeFeed
# main.py line 1410
from hft.main import run_hft
```

Real test import — NOT a mock (breaks test suite without sys.path or import update):
```python
# tests/test_realtime_feed.py lines 8–14
from crypto_scalper.realtime_feed import (
    CryptoRealtimeFeed,
    LiveTick,
    _binance_parse,
    _bybit_parse,
    _coinbase_parse,
)
```

Test mocks (patching sys.modules — break if bare package name changes):
```python
# tests/test_runtime_shutdown.py line 83
monkeypatch.setitem(sys.modules, "crypto_scalper.live_runner", ...)
# tests/test_runtime_loop_exception_observability.py line 12
monkeypatch.setitem(sys.modules, "crypto_scalper.live_runner", ...)
```

Internal package imports within hft/ (12 statements across 4 files — all use bare package name `hft`):
```python
# hft/execution_engine.py
from hft import config as C
from hft.utils import calc_fee
# hft/main.py
from hft import config as C
from hft.market_manager import MarketManager, OpenPosition
from hft.signal_engine import HFTSignalEngine, HFTSignal
from hft.risk_manager import HFTRiskManager
from hft.execution_engine import ExecutionEngine
from hft.utils import (...)
# hft/market_manager.py
from hft import config as C
from hft.utils import current_epoch, epoch_end, seconds_remaining, window_label
# hft/signal_engine.py
from hft import config as C
from hft.utils import (...)
```

Internal package imports within crypto_scalper/ (2 statements — both verified by grep 2026-06-26):
```python
# crypto_scalper/live_runner.py line 14
from crypto_scalper.config import write_freqtrade_config
# crypto_scalper/backtest.py line 18
from crypto_scalper.config import write_freqtrade_config
```

**Additional finding:** `crypto_scalper/market_data.py` and `crypto_scalper/realtime_feed.py` both import `from config.settings import Settings, get_settings` — a reference to the project's top-level `config/` package, not a self-referential import. Under either approach (sys.path or rename), these do NOT require changes: the project root is always in sys.path, so `config.settings` resolves unchanged.

**Total import references: 22 statements across 10 files** (2 external + 2 internal in crypto_scalper/ + 1 real test import + 4 mock calls across 2 test files = 9 crypto_scalper; 1 external + 12 internal in hft/ = 13 hft; 9 + 13 = 22).

**Approach note:** Under the sys.path approach (adding `sys.path.insert(0, 'experiments/')` to main.py), ALL 22 references continue to work with zero edits, because every reference uses the bare top-level package name (`hft` or `crypto_scalper`). This is the recommended approach. Under the rename approach, all 22 statements require updating.

| Current | Proposed | Risk | Files Needing Update |
|---|---|---|---|
| `hft/` (entire folder) | `experiments/hft/` | HIGH | `main.py` line 1410; `hft_paper_run.py` (review imports); see full import map above |
| `crypto_scalper/` (entire folder) | `experiments/crypto_scalper/` | HIGH | `main.py` lines 17 and 1313; `tests/test_realtime_feed.py` lines 8–14 (real import); `tests/test_runtime_shutdown.py` line 83 (mock); `tests/test_runtime_loop_exception_observability.py` line 12 (mock); all internal crypto_scalper/ imports |

**Required steps before executing this batch:**
1. Choose approach: sys.path (recommended) or rename
2. If sys.path: add `sys.path.insert(0, os.path.join(os.path.dirname(__file__), "experiments"))` to main.py top and to `conftest.py` or `pytest.ini [tool:pytest] pythonpath = experiments`
3. If rename: update all 22 import references (see full import map above)
4. Create `experiments/__init__.py` to make it a Python package root
5. Run `pytest tests/ -q` after the move — must pass all of: `test_realtime_feed.py`, `test_runtime_shutdown.py`, `test_runtime_loop_exception_observability.py`, and general test suite
6. Run `python main.py --mode verify` to confirm engine startup still resolves both packages

**Alternative approach (lower risk):** Add `experiments/` as a `sys.path` entry in `main.py` so that `from crypto_scalper.live_runner import ...` continues to work unchanged after the folder moves. This avoids touching all import statements but requires a `sys.path` modification.

**Pre-condition check:**
```powershell
# Find ALL references to hft and crypto_scalper
Select-String -Path "main.py", "tests\*.py", "scripts\*.py", "polymarket\*.py", "tools\*.py" -Pattern "hft|crypto_scalper" -AllMatches
```

---

## BATCH 5 — Archive/Delete Orphaned Dashboard Prototypes

| Current | Proposed | Risk | Pre-condition |
|---|---|---|---|
| `research_cockpit/` | `archive/research_cockpit/` or DELETE | MEDIUM | Verify no Python file imports from research_cockpit/; check if any test references it |
| `web-dashboard/` | `archive/web-dashboard/` or DELETE | MEDIUM | Same check |

**Pre-condition:**
```powershell
Select-String -Path "tests\*.py", "polymarket\*.py", "tools\*.py" -Pattern "research_cockpit|web.dashboard"
```

---

## BATCH 6 — Move Root Markdown to docs/

This is the largest batch (~388 files, updated from ~376 — the 6 audit deliverable documents created during REPOSITORY_ORGANIZATION_AUDIT_001 were added to root after the original count was taken). It should be executed in sub-batches organized by category.

### Batch 6A — AI Context Prompts (2 files)

| Current | Proposed |
|---|---|
| `CHATGPT_PROJECT_START_PROMPT.md` | `docs/ai_context/CHATGPT_PROJECT_START_PROMPT.md` |
| `CODEX_START_PROMPT.md` | Keep in root OR `docs/ai_context/CODEX_START_PROMPT.md` |

**Note:** Evaluate whether Codex auto-loads from root or can be configured to load from docs/. If root-required, keep in root.

---

### Batch 6B — Architecture/Design Documents (~54 files → docs/architecture/)

Move all files matching these patterns:
- `*_V1_DESIGN_*.md`
- `*_V1.md` (design spec files)
- `*FRAMEWORK*.md`
- `*ARCHITECTURE*.md`
- `*ENGINE_V1*.md`
- `*_DESIGN_001.md`

Target: `docs/architecture/`

Examples:
- `ALWAYS_ACTIVE_ENGINE_V1_DESIGN_001.md` → `docs/architecture/`
- `ANALYTICS_AUTHORITY_MATRIX_001.md` → `docs/architecture/`
- `BANKROLL_ENGINE_V1_DESIGN_001.md` → `docs/architecture/`
- `EVENT_CATALOG_V1.md` → `docs/architecture/`
- `POSITION_SIZING_ENGINE_V1_DESIGN_001.md` → `docs/architecture/`
- `RUNTIME_STATE_MACHINE_V1.md` → `docs/architecture/`
- (See MARKDOWN_CLASSIFICATION_001.md Class 2 for full list)

**Risk:** LOW — none of these are imported by Python code.  
**Files needing update:** FILE_INDEX.md, DOCUMENTATION_MAP.md.

---

### Batch 6C — Implementation Plans and Feature Specs (~22 files → docs/design/)

Move all files matching these patterns:
- `*_IMPLEMENTATION_PLAN_*.md`
- `*_SPEC_*.md`
- `*_PLAN_*.md` (non-action plans)

Target: `docs/design/`

Examples:
- `COLD_JSONL_COMPRESSION_REAL_IMPLEMENTATION_PLAN_001.md`
- `DASHBOARD_STATE_DESIGN_001.md`
- `EXECUTION_SHADOW_FILTER_SPEC_001.md`
- `OPTION_D_SHADOW_IMPLEMENTATION_PLAN_001.md`
- `RUNTIME_STORAGE_POLICY_DESIGN_001.md`
- `STOP_LOSS_POLICY_FIX_PLAN_001.md`
- (See MARKDOWN_CLASSIFICATION_001.md Class 7 for full list)

**Risk:** LOW.

---

### Batch 6D — Commit Reports and Implementation Reports (~120 files → docs/reports/)

Move all files matching:
- `*_COMMIT_REPORT_*.md`
- `*_IMPLEMENTATION_REPORT_*.md`
- `*_PRE_COMMIT_AUDIT_*.md`
- `dashboard_v2a_commit_report.md`
- `patch_*_report.md`

Target: `docs/reports/`  
Optional: Organize into `docs/reports/2026-04/`, `docs/reports/2026-05/`, `docs/reports/2026-06/` by file date.

**Risk:** LOW — these are historical records only.

---

### Batch 6E — Research/Forensic Audit Documents (~80 files → docs/research/)

Move all research files to appropriate docs/research/ subfolders.

Target subfolders:
- `docs/research/session_edge/` — trade execution, risk mode, sizing, signal audits
- `docs/research/runtime_health/` — orderbook, CLOB, session health
- `docs/research/performance/` — EV, edge, stop-loss, trade quality
- `docs/research/discovery/` — hypothesis ledger, new frontiers
- `docs/research/risk_modes/` (NEW) — MICRO_RECOVERY, DEFENSIVE, risk mode audits

Key files for `docs/research/risk_modes/` (current session):
- `DEFENSIVE_CONFIDENCE_DISTRIBUTION_001.md`
- `DEFENSIVE_COUNTERFACTUAL_PASS_ANALYSIS_001.md`
- `DEFENSIVE_MODE_FORENSIC_VALIDATION_001.md`
- `DEFENSIVE_MODE_NEXT_ACTIONS_001.md`
- `MICRO_BANKROLL_EXECUTABILITY_ANALYSIS_001.md`
- `MICRO_RECOVERY_COUNTERFACTUAL_ANALYSIS_001.md`
- `MICRO_RECOVERY_NEXT_ACTIONS_001.md`
- `MICRO_RECOVERY_RISK_PLAN_ZERO_AUDIT_001.md`
- `MICRO_RECOVERY_TRAP_RESOLUTION_DESIGN_001.md`
- `MICRO_RECOVERY_ZERO_PIPELINE_TRACE_001.md`
- `RISK_MODE_TRANSITION_TIMELINE_001.md`
- `RISK_PLAN_ZERO_DISTRIBUTION_001.md`
- `RISK_PLAN_ZERO_FORENSIC_AUDIT_001.md`

**Risk:** LOW.

---

### Batch 6F — Operations and Runbooks (~5 files → docs/operations/)

- `VULTR_PAPER_RUN.md` → `docs/operations/`
- `MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md` → `docs/research/discovery/`
- `INVENTORY_REPLAY_RESEARCH_PLAN.md` → `docs/research/discovery/`

---

### Batch 6G — Governance and Compliance (~10 files → docs/audits/ or docs/architecture/)

- `GOVERNANCE_BOOTSTRAP_001_DESIGN_PACKAGE.md` → `docs/architecture/`
- `GOVERNANCE_BOOTSTRAP_001_REFINED.md` → `docs/architecture/`
- `GOVERNANCE_BOOTSTRAP_001_PHASE1_IMPLEMENTATION_REPORT.md` → `docs/reports/`
- `GOVERNANCE_HARDENING_001_REPORT.md` → `docs/reports/`
- `GOVERNANCE_V1_CLOSURE_AUDIT_001.md` → `docs/audits/`
- `ARCHITECTURE_PRINCIPLE_COMPLIANCE_001.md` → `docs/architecture/`
- `FINAL_SOURCE_OF_TRUTH_HIERARCHY_001.md` → `docs/architecture/`
- `QUANT_KNOWLEDGE_GOVERNANCE_AUDIT_001.md` → `docs/audits/`

---

### Batch 6H — Prior Reorganization Artifacts

| File | Action |
|---|---|
| `ROOT_MD_BATCH_1_MOVE_REPORT_001.md` | Move to `docs/reports/` |
| `ROOT_MD_BATCH_2_MOVE_REPORT_001.md` | Move to `docs/reports/` |
| `ROOT_MD_INVENTORY_001.md` | Move to `docs/audits/` (superseded) |
| `ROOT_MD_REORGANIZATION_PLAN_001.md` | Move to `docs/design/` (superseded by this plan) |
| `CANONICAL_DOCUMENT_RECONCILIATION_001.md` | Move to `docs/audits/` |
| `AUDIT_CLASSIFICATION_REVIEW.md` | Move to `docs/audits/` |

---

## BATCH 7 — After All Moves: Update Navigation Files

These files reference paths that will change after Batches 0–6. Update after moves complete.

| File | What to Update |
|---|---|
| `FILE_INDEX.md` | All moved file paths → new paths |
| `DOCUMENTATION_MAP.md` | All moved file paths → new paths |
| `MASTER_AGENT_ROUTER.md` | Any documentation path references |
| `CURRENT_PROJECT_STATUS.md` | References to root-level docs |
| `README.md` | Any hardcoded doc links |

---

## BATCH 8 — docs/research/ Internal Cleanup

After root markdown is moved, the 149 unclassified files in `docs/research/` root should be sorted into subfolders. This is lower priority and can be a separate task.

---

## Verification Checklist (Before Any Batch)

Run these checks before executing each batch:

```powershell
# 1. Confirm pytest passes before any moves
python -m pytest tests/ -q --tb=short

# 2. Grep for any Python files that import from paths being moved
# (For each batch, grep the specific patterns)

# 3. Confirm .gitignore covers .pyc before removing them
Get-Content .gitignore

# 4. Run git status to see current state
git status

# 5. After moves, run pytest again to confirm nothing broke
python -m pytest tests/ -q --tb=short
```

---

## Move Table Summary

| Batch | Action | Files | Risk |
|---|---|---|---|
| 0.1 | Delete 3 venv backups | 3 folders | ZERO |
| 0.2 | Delete .env.backup.local | 1 file | ZERO |
| 0.3 | Delete 2 stub MD files | 2 files | LOW |
| 0.4 | Verify .gitignore covers .pyc (NOT git-tracked — no git rm needed) | ~750 disk files | ZERO |
| 0.5 | Move docs.zip → archive/ | 1 file | ZERO |
| 0.6 | Delete/move task.md | 1 file | ZERO |
| 1 | Move root scripts → scripts/ | 4 files | LOW |
| 2 | Move api/ → dashboard/ (update tests/test_dashboard_api.py atomically) | 1 file + 1 test update | LOW |
| 3 | Move memory/ → .claude/memory/ | 2 files | LOW |
| 4 | Move hft/ crypto_scalper/ → experiments/ | 2 folders | HIGH (main.py imports both — requires import path updates) |
| 5 | Archive research_cockpit/ web-dashboard/ | 2 folders | MEDIUM |
| 6A | Move AI context prompts | 2 files | LOW |
| 6B | Move architecture docs → docs/architecture/ | ~54 files | LOW |
| 6C | Move impl plans → docs/design/ | ~22 files | LOW |
| 6D | Move commit/impl reports → docs/reports/ | ~120 files | LOW |
| 6E | Move research docs → docs/research/ | ~80 files | LOW |
| 6F | Move operations docs → docs/operations/ | ~5 files | LOW |
| 6G | Move governance docs → docs/architecture/ | ~10 files | LOW |
| 6H | Move prior reorg artifacts → docs/ | 6 files | LOW |
| 7 | Update FILE_INDEX, DOCUMENTATION_MAP, etc. | 5 files | LOW |
| 8 | docs/research/ internal sort | ~149 files | LOW |

**Total files affected: ~1,120 files**  
**Net reduction in root: 401 → ~18 markdown files** (root had 395 at audit start; 6 audit deliverable documents added since then bring the current count to 401)  
**Estimated execution time with verification: 2–4 hours**

---

## What This Plan Does NOT Cover

- `main.py` decomposition (DEBT-007) — separate HIGH-risk task
- `logs/` restructuring (DEBT-006) — requires confirming no Python hardcodes `logs/` paths
- `docs/research/` internal sort of 149 root files (Batch 8) — separate task after Batch 6E
- Renaming files to fix naming conventions (DEBT-016) — separate LOW-priority task
- `CURRENT_PROJECT_STATUS.md` split (large 50KB file) — separate task
