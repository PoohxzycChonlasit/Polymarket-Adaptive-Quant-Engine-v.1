# REPOSITORY_ORGANIZATION_AUDIT_001

**Task:** REPOSITORY_ORGANIZATION_AUDIT_001  
**Mode:** DISCOVERY ONLY — no code or file changes  
**Date:** 2026-06-26  
**Scope:** Full repository structure, classification, technical debt, and reorganization proposal

---

## Phase 1 — Repository Inventory

### Scope Boundary

All counts exclude: `.venv/`, `.venv_BROKEN_poh2_py312_backup/`, `.venv_broken_POOHXYZ_migration_backup/`, `.venv_migration_old_backup/`, `node_modules/`, `__pycache__/`, `.git/`, `.pytest_cache/`.

These are dependency/cache/tool directories that contain no project-owned source.

### File Count by Type

| File Type | Count | Notes |
|---|---|---|
| **Python (.py)** | ~330 project-owned | Excludes venv + pycache |
| **Markdown (.md)** | **1,003** | 401 in root (395 at audit start; 6 audit deliverable documents added to root since) |
| **JSONL (.jsonl)** | 535 | Almost entirely runtime-generated logs |
| **JSON (.json)** | 399 | Mix of package.json, lock files, runtime data |
| **CSV (.csv)** | 328 | Research exports, audit data |
| **TypeScript/TSX** | 65 | Dashboard React source |
| **TXT (.txt)** | 231 | Mixed: logs, README fragments |
| **CSS (.css)** | 8 | Dashboard styles |
| **Parquet (.parquet)** | 4 | Compressed research data |
| **YAML (.yaml/.yml)** | 1 | Single file |
| **ENV (.env\*)** | 3 | `.env`, `.env.backup.local`, `.env.example` |
| **Python compiled (.pyc)** | ~755+ on disk | In tools/ (44), tests/ (541), crypto_scalper/ — NOT git-tracked (git ls-files returns zero .pyc matches) |
| **Other** | ~280 | zip, sqlite, gitignore, ini, lock, etc. |

**Total tracked project files (excl. venvs/node_modules): ~3,300+ source + ~16,000+ runtime/generated**

### Top-Level Folder Summary

| Folder | File Count | Purpose | Status |
|---|---|---|---|
| `.claude/` | 4 | AI session memory | Tooling |
| `.codex/` | 12 | Codex AI prompts/context | Tooling |
| `api/` | 1 | Single dashboard API file | Misplaced |
| `archive/` | 10 | Archived markdown docs | Archive |
| `config/` | 2 | Runtime configuration | Active |
| `crypto_scalper/` | 7 | Standalone legacy scalper | Imported by main.py |
| `dashboard/` | 59 | Active React + Python dashboard | Active |
| `docs/` | 510 | Documentation hub | Active/Mixed |
| `hft/` | 10 | Standalone legacy HFT engine | Imported by main.py |
| `logs/` | 980 | Runtime logs (flat) | Generated |
| `memory/` | 2 | Project memory notes | Misplaced |
| `polymarket/` | 30 | Core trading engine | Active |
| `research/` | 18 | Session research notes | Active |
| `research_cockpit/` | 28 | Older React dashboard build | Orphaned |
| `runtime/` | 1069 | Runtime data and reports | Generated |
| `scratch/` | 237 | Experimental/temp files | Scratch |
| `scripts/` | 3 | Utility scripts | Active |
| `tests/` | 681 (140 py + 541 pyc) | Test suite | Active |
| `tools/` | 79 (35 py + 44 pyc) | Offline analysis tools | Active |
| `utils/` | 18 | Shared Python utilities | Active |
| `web-dashboard/` | 19 | Older/alternate React dashboard | Orphaned |
| **ROOT** | **408+** | **401 markdown** (count rises as audit docs are written to root) | **CRITICAL DEBT** |

---

## Phase 2 — Root Folder Audit

See `ROOT_FOLDER_AUDIT_001.md` for the complete per-file analysis.

**Summary:**
- 408+ files in the root directory (count as of audit; 6 audit deliverable documents written to root since, bringing MD count to 401)
- 401 are markdown files — almost all are audit docs, design docs, investigation reports, patch reports, and implementation notes
- 13 non-markdown files: main.py, 4 utility Python scripts, .env x3, .gitignore, requirements.txt, pytest.ini, task.md, docs.zip
- ~12 files are legitimately AI startup context and must stay in root (CLAUDE.md, AGENTS.md, etc.)
- ~7 files are legitimately project root files (main.py, requirements.txt, .gitignore, pytest.ini, .env.example)
- ~388 markdown files should be moved to docs/ with appropriate subfolder organization

---

## Phase 3 — Classification

### Classification Categories Used

| Category | Definition |
|---|---|
| **Runtime** | Generated at runtime, not committed or ephemeral |
| **Configuration** | Settings, environment, build config |
| **Documentation/Architecture** | Permanent design decisions |
| **Documentation/Research** | Investigation findings, forensic audits |
| **Documentation/Operations** | Runbooks, operational guides |
| **Documentation/Reports** | Commit reports, implementation reports, pre-commit audits |
| **AI Context** | Files loaded by Claude/Codex/ChatGPT at startup |
| **Testing** | Test suites and test utilities |
| **Dashboard** | Dashboard source (React, Python) |
| **Scripts** | Standalone utility scripts |
| **Analysis Tools** | Offline analysis and replay tools (tools/) |
| **Core Engine** | Active trading engine source (polymarket/, utils/, config/) |
| **Experimental** | scratch/, research experiments |
| **Orphaned** | hft/, crypto_scalper/, web-dashboard/, research_cockpit/ |
| **Generated** | logs/, runtime/, compiled pyc |
| **Archive** | Superseded documents |
| **Security** | .env files, API keys |

### File Distribution by Category

| Category | Approx Count | Primary Location |
|---|---|---|
| AI Context | 13 | Root |
| Core Engine | 85 | polymarket/, utils/, config/ |
| Analysis Tools | 35 | tools/ |
| Testing | 140 | tests/ |
| Dashboard | 59 | dashboard/ |
| Configuration | 8 | config/, root |
| Documentation/Architecture | ~30 | Root (should be docs/) |
| Documentation/Research | ~450 | Root + docs/ |
| Documentation/Operations | ~15 | Root + docs/ |
| Documentation/Reports | ~200 | Root (should be docs/) |
| Experimental | ~240 | scratch/, research/ |
| Orphaned | ~65 | hft/, crypto_scalper/, web-dashboard/, research_cockpit/ |
| Generated/Runtime | ~2000+ | runtime/, logs/ |
| Security | 3 | Root |
| Archive | 10 | archive/ |
| Generated/Compiled | ~755+ | tools/, tests/, crypto_scalper/ |

---

## Phase 4 — Folder Organization Audit

### Problems Identified

**1. Root directory is a documentation dump**  
395 markdown files in root. This is the single largest organizational issue. Every audit, design doc, research report, patch report, commit report, and investigation note was written to root. The root is now effectively unusable for navigation.

**2. Docs folder is partially organized**  
`docs/` has reasonable subfolders (research/, audits/, reports/, quant_agent_setup_md/) but:
- `docs/research/` root still has 149 unclassified files
- `docs/` root has 11 files (including duplicates of root files)
- No clear naming convention — some folders use snake_case, some use natural language

**3. Three separate dashboard directories**  
- `dashboard/` — active React (Vite + TypeScript) + Python offline dashboard
- `research_cockpit/` — older React build (separate vite project, appears incomplete/orphaned)
- `web-dashboard/` — another older React build

Only `dashboard/` appears active. The others appear to be abandoned prototypes.

**4. Two separate project-external codebases in root**  
- `hft/` — a complete standalone HFT engine with its own main.py, config, risk_manager, etc.
- `crypto_scalper/` — a separate scalper with its own main.py, backtest.py, realtime_feed.py

These are not part of the PolyTrade quant engine. They may be prototype/legacy experiments. Both have compiled .pyc artifacts for two Python versions (3.11 and 3.12).

**5. `logs/` is flat with 980 files**  
No subdirectory structure inside `logs/`. All 980 log files sit in the root of logs/. Should mirror runtime/ structure.

**6. `tools/` has compiled bytecode alongside source**  
Every .py file in tools/ has both `.cpython-311.pyc` and `.cpython-312.pyc` alongside it. These should be in `__pycache__/` subdirectories and excluded via .gitignore.

**7. `tests/` has 542 .pyc files**  
Same problem: compiled bytecode in tests/ is likely being tracked in git when it shouldn't be.

**8. `scratch/` has no clear boundary**  
237 files of mixed types (JSONL, Python, JSON, SQLite). Some may be active experiments, others may be abandoned. No clear naming convention.

**9. `api/` is a single-file folder**  
`api/dashboard_api.py` is the only file. This Flask API file belongs in `dashboard/`.

**10. `memory/` is in root**  
Contains project memory notes. Should be in `.claude/` or `docs/`.

---

## Phase 5 — Markdown Audit

See `MARKDOWN_CLASSIFICATION_001.md` for the complete classification.

**Summary statistics:**

| Category | Count |
|---|---|
| AI startup context (must stay root) | 10 |
| Active canonical documentation | ~25 |
| Architecture/design documents | ~60 |
| Research/forensic audit documents | ~250 |
| Patch/implementation/commit reports | ~200 |
| Operational runbooks | ~15 |
| Duplicate files | ~8 confirmed |
| Obsolete/superseded | ~30 estimated |
| Generated/historical reports | ~120 |

**Key duplicates confirmed:**

| Document | Root Copy | docs/ Copy |
|---|---|---|
| KNOWN_ISSUES.md | 267 bytes (stub) | 18,735 bytes (canonical) |
| PROJECT_STRUCTURE.md | 671 bytes (stub) | 13,417 bytes (canonical) |
| BANKROLL_TIER_FRAMEWORK_V1.md | 4,498 bytes | docs/BANKROLL_TIER_FRAMEWORK_V1.md |
| CLAUDE.md | 4,893 bytes (active) | archive/CLAUDE.md (2,940 bytes, archived) |

---

## Phase 6 — Dependency on File Location

### Files That MUST Stay in Root

These are loaded by tools that expect root-relative paths:

| File | Why Root | Safe to Move? |
|---|---|---|
| `CLAUDE.md` | Claude Code auto-loads from project root | NO |
| `AGENTS.md` | Agent SDK auto-loads from root | NO |
| `main.py` | Entry point, all docs reference it | NO |
| `.env` | Python-dotenv loads from CWD | NO |
| `.env.example` | Convention: env template in root | NO |
| `.gitignore` | Git requires root | NO |
| `requirements.txt` | pip convention: root | NO |
| `pytest.ini` | pytest looks for ini in root | NO |
| `README.md` | GitHub renders from root | NO |

### Files Where Location Is Flexible (But Needs Import Updates)

| File | Current | Constraint |
|---|---|---|
| `dashboard/app.py` | dashboard/ | Flask app, no import dependency |
| `api/dashboard_api.py` | api/ | No relative imports, moveable |
| `check_balance.py` | root | No imports from engine |
| `daily_report.py` | root | Could move to scripts/ |
| `generate_bypass.py` | root | Could move to scripts/ |
| `hft_paper_run.py` | root | References hft/ — keep near hft/ or move both |
| `register_api_keys.py` | root | Could move to scripts/ |

### AI Startup Context Files (Root Preference)

These files are referenced in CLAUDE.md's "Before Editing" section and are part of AI agent startup flow. They should remain in root or at a stable well-known path:

- `CODEX_START_HERE.md` — referenced in CLAUDE.md "Read in order"
- `PROJECT_RULES.md` — referenced in CLAUDE.md
- `CURRENT_PROJECT_STATUS.md` — referenced in CLAUDE.md
- `MASTER_AGENT_ROUTER.md` — referenced in CLAUDE.md
- `CODEX_START_PROMPT.md` — AI prompt file
- `CHATGPT_PROJECT_START_PROMPT.md` — AI prompt file
- `FILE_INDEX.md` — navigation
- `DOCUMENTATION_MAP.md` — navigation

---

## Phase 7 — Technical Debt

See `TECHNICAL_DEBT_REGISTER_001.md` for the complete register.

**Summary by severity:**

| Severity | Count | Examples |
|---|---|---|
| CRITICAL | 2 | Root markdown pollution (395 files), venv backups in root |
| HIGH | 5 | Orphaned projects, .pyc in source, duplicate dashboards, logs/ flat structure, monolithic main.py |
| MEDIUM | 7 | scratch/ boundary, api/ single-file folder, duplicate docs, task.md in root, docs.zip, .env.backup.local, memory/ location |
| LOW | 4 | Implementation_plan.md in root, naming inconsistencies, empty/near-empty folders, research/ vs docs/research/ overlap |

---

## Phase 8 — AI Readability Audit

### Current State

**Discoverability: POOR**  
An AI agent opening this repository for the first time faces 395 markdown files in the root directory. There is no clear hierarchy — audit reports sit next to architecture documents next to patch notes next to AI startup files. The signal-to-noise ratio for AI context loading is very low.

**Navigation: MEDIUM**  
`MASTER_AGENT_ROUTER.md`, `FILE_INDEX.md`, and `DOCUMENTATION_MAP.md` exist and attempt to solve navigation. However, they reference files that have since been moved (or not moved), creating stale links.

**Startup complexity: MEDIUM**  
The "Before Editing" sequence (CODEX_START_HERE → PROJECT_RULES → CURRENT_PROJECT_STATUS) is well-defined. However, CURRENT_PROJECT_STATUS.md is 50,938 bytes — over 50KB — which is a large context cost for every AI session.

**Documentation clarity: POOR**  
Three categories of documents are visually indistinguishable in the root directory:
1. Canonical architecture decisions (e.g., ARCHITECTURE_FREEZE_DECISION_001.md)
2. Historical audit reports (e.g., ORDERBOOK_TIMELINE_ANALYSIS_001.md)
3. AI working notes from prior sessions (e.g., MICRO_RECOVERY_NEXT_ACTIONS_001.md)

All three appear identical to an AI scanning the root. This wastes context on historical noise.

**Context loading: POOR**  
If an AI loads the root directory listing, it receives 395+ markdown filenames to process before identifying which are relevant. This is a significant context burden.

### Scores

| Dimension | Score | Notes |
|---|---|---|
| Discoverability | 3/10 | Root pollution overwhelms navigation |
| Navigation | 5/10 | Index files exist but stale |
| Startup complexity | 6/10 | Well-defined flow, but CURRENT_PROJECT_STATUS is 50KB |
| Documentation clarity | 3/10 | No visual distinction between categories |
| Context loading | 2/10 | 395 files before finding signal |

---

## Phase 9 — Enterprise Repository Proposal

See `ENTERPRISE_REPOSITORY_PROPOSAL_001.md`.

---

## Phase 10 — Safe Move Plan

See `SAFE_MOVE_PLAN_001.md`.

---

## Phase 11 — Verification Status

| Item | Status |
|---|---|
| Root file count (395 MD) | VERIFIED — PowerShell count |
| Folder structure | VERIFIED — directory listing |
| Active AI startup files | VERIFIED — CLAUDE.md confirms sequence |
| hft/ and crypto_scalper/ imports | CORRECTED — NOT orphaned. main.py imports both: `from crypto_scalper.live_runner import main as run_scalper` (line 17), `from crypto_scalper.realtime_feed import CryptoRealtimeFeed` (line 1313), `from hft.main import run_hft` (line 1410). See DEBT-003 correction. |
| Duplicate dashboards | VERIFIED — dashboard/, research_cockpit/, web-dashboard/ |
| Duplicate docs (KNOWN_ISSUES, PROJECT_STRUCTURE, BANKROLL_TIER) | VERIFIED — size mismatch confirms root stubs vs canonical in docs/ |
| .pyc files in tools/ | VERIFIED — 44 .pyc alongside 35 .py (on disk, NOT git-tracked) |
| .pyc files in tests/ | VERIFIED — 542 .pyc alongside 139 .py (on disk, NOT git-tracked) |
| Git tracking status of .pyc | VERIFIED — `git ls-files \| grep \.pyc` returns zero results. .pyc files are NOT tracked by git. `git rm --cached` is a no-op. |
| Previous reorganization attempt | VERIFIED — ROOT_MD_BATCH_1 and BATCH_2 reports exist |
| Import dependencies (api/) | VERIFIED — `tests/test_dashboard_api.py` line 6: `from api.dashboard_api import create_app`. Batch 2 affects both api/dashboard_api.py and this test file. |
| `web-dashboard/` and `research_cockpit/` imports | VERIFIED — no Python imports found referencing either path |

---

## Summary Verdict

**State:** The repository is functionally correct but organizationally critical.

The core engine (polymarket/, utils/, config/, tools/, tests/) is well-structured and coherent. The problem is entirely the documentation layer:

- 395 markdown files in root created a documentation dump that can never be navigated by AI or human
- `hft/` and `crypto_scalper/` are secondary mode projects sitting at top-level scope — imported by main.py, not orphaned, but their top-level placement obscures the primary engine
- Multiple venv backups consume disk and could confuse tooling
- .pyc files exist on disk in tools/ and tests/ but are **not** git-tracked — no `git rm --cached` step needed; verifying .gitignore rules prevent future commits is sufficient

**No runtime behavior is at risk from reorganization of documentation.** Moving `hft/` or `crypto_scalper/` requires updating main.py import paths (3 statements) and a test mock (1 reference) — this is code-level risk, not documentation-level.

**The single highest-value action** is moving the ~376 moveable markdown files from root to organized subdirectories in `docs/`. This alone would reduce root from 408 files to ~32, making the repository navigable again.
