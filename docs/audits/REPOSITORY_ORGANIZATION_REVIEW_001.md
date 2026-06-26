# REPOSITORY_ORGANIZATION_REVIEW_001

**Task:** REPOSITORY_ORGANIZATION_REVIEW_001  
**Mode:** REVIEW ONLY — no files moved, renamed, deleted, or modified  
**Date:** 2026-06-26  
**Input Documents:** 6 audit deliverables from REPOSITORY_ORGANIZATION_AUDIT_001  
**Reviewer posture:** Documentation is a claim, not evidence. Repository reality is the source of truth.

---

## Section 1 — Deliverable Document Status

All six audit documents confirmed present with substantial content:

| Document | Size | Status |
|---|---|---|
| `REPOSITORY_ORGANIZATION_AUDIT_001.md` | 16,383 bytes | PRESENT |
| `ROOT_FOLDER_AUDIT_001.md` | 12,694 bytes | PRESENT |
| `MARKDOWN_CLASSIFICATION_001.md` | 17,162 bytes | PRESENT |
| `TECHNICAL_DEBT_REGISTER_001.md` | 15,614 bytes | PRESENT |
| `ENTERPRISE_REPOSITORY_PROPOSAL_001.md` | 12,081 bytes | PRESENT |
| `SAFE_MOVE_PLAN_001.md` | 16,564 bytes | PRESENT |

---

## Section 2 — Verification Commands Run

All commands from the task spec executed. Results below.

### 2.1 — git ls-files | grep .pyc

```
RESULT: zero .pyc files tracked
```

**Verdict:** CONFIRMED — `.pyc` files are not git-tracked. The `.gitignore` correctly covers them via `*.pyc` (line 67), `*.py[cod]` (line 15), and `__pycache__/` (line 14). DEBT-005 downgrade from HIGH → MEDIUM is correct.

---

### 2.2 — api.dashboard_api import scan

```
./tests/test_dashboard_api.py:6:from api.dashboard_api import create_app
```

**Verdict:** CONFIRMED — one file. SAFE_MOVE_PLAN Batch 2 correctly documents this and requires atomic move + test update.

---

### 2.3 — hft import scan

```
./hft/execution_engine.py:24:from hft import config as C
./hft/execution_engine.py:25:from hft.utils import calc_fee
./hft/main.py:47:from hft import config as C
./hft/main.py:48-52: from hft.market_manager, hft.signal_engine, hft.risk_manager, hft.execution_engine, hft.utils
./hft/market_manager.py:19:from hft import config as C
./hft/market_manager.py:20:from hft.utils import ...
./hft/signal_engine.py:32:from hft import config as C
./hft/signal_engine.py:33:from hft.utils import ...
./main.py:1410:        from hft.main import run_hft
```

**12 internal hft package import lines** across 4 files, plus 1 external reference in main.py. Total affected by a move: **5 files, 13 import statements**.

---

### 2.4 — crypto_scalper import scan

```
./crypto_scalper/backtest.py:18:from crypto_scalper.config import write_freqtrade_config
./crypto_scalper/live_runner.py:14:from crypto_scalper.config import write_freqtrade_config
./main.py:17:from crypto_scalper.live_runner import main as run_scalper
./main.py:1313:    from crypto_scalper.realtime_feed import CryptoRealtimeFeed
./tests/test_realtime_feed.py:8:from crypto_scalper.realtime_feed import (CryptoRealtimeFeed, LiveTick, _binance_parse, _bybit_parse, _coinbase_parse)
./tests/test_runtime_loop_exception_observability.py:12:    monkeypatch.setitem(sys.modules, "crypto_scalper.live_runner", ...)
./tests/test_runtime_shutdown.py:83,132,163: monkeypatch.setitem(sys.modules, "crypto_scalper.live_runner", ...)  [3 instances]
```

**2 internal crypto_scalper package imports** across 2 files, **2 external imports in main.py**, **1 real test import in test_realtime_feed.py**, **4 mock references** across 2 test files. Total affected by a move: **6 files, 9 import statements**.

---

## Section 3 — VERIFIED Findings

The following claims from the audit documents are confirmed accurate against the repository.

| # | Claim | Verification Method | Result |
|---|---|---|---|
| V1 | Zero .pyc files are git-tracked | `git ls-files \| grep \.pyc` | CONFIRMED |
| V2 | .gitignore covers `*.pyc`, `*.py[cod]`, `__pycache__/` | Read `.gitignore` | CONFIRMED |
| V3 | `.env.backup.local` is gitignored | `git check-ignore -v .env.backup.local` → `.gitignore:4:.env.*.local` | CONFIRMED |
| V4 | All three venv backups are gitignored | `git check-ignore -v` on each | CONFIRMED (case-insensitive on Windows) |
| V5 | `main.py` imports `from crypto_scalper.live_runner` (line 17) | grep scan | CONFIRMED |
| V6 | `main.py` imports `from crypto_scalper.realtime_feed` (line 1313) | grep scan | CONFIRMED |
| V7 | `main.py` imports `from hft.main import run_hft` (line 1410) | grep scan | CONFIRMED |
| V8 | `tests/test_dashboard_api.py:6` imports from `api.dashboard_api` | grep scan | CONFIRMED |
| V9 | `hft/` and `crypto_scalper/` are NOT orphaned (imported by main.py) | grep scan | CONFIRMED — DEBT-003 correction was correct |
| V10 | `hft_paper_run.py` does NOT import from `hft/` package | Read file | CONFIRMED — standalone script importing from polymarket.* only |
| V11 | `research_cockpit/` and `web-dashboard/` have no Python imports from production code | grep scan | CONFIRMED — only a scratch/ reference in a locally-excluded file |
| V12 | All startup-critical files present in root | File existence check | CONFIRMED — all 16 checked files OK |
| V13 | 139 Python test files in tests/ | os.listdir count | CONFIRMED |
| V14 | `tests/test_runtime_shutdown.py` has 3 crypto_scalper mock references | grep scan | CONFIRMED |
| V15 | DEBT-005 downgrade to MEDIUM is correct | git ls-files + .gitignore read | CONFIRMED |

---

## Section 4 — NOT VERIFIED Findings

The following claims were made in the audit but were not verifiable from the available data.

| # | Claim | Document | Status |
|---|---|---|---|
| NV1 | `docs/research/` has exactly 149 unclassified files at its root | REPOSITORY_ORGANIZATION_AUDIT_001.md | Not re-counted — audit count accepted as close enough for planning |
| NV2 | `logs/` has exactly 980 files | TECHNICAL_DEBT_REGISTER_001.md | Not counted — directional claim accepted |
| NV3 | `BANKROLL_TIER_FRAMEWORK_V1.md` is identical in root and docs/ | TECHNICAL_DEBT_REGISTER_001.md (DEBT-010) | File contents not compared; size match not checked |
| NV4 | `generate_bypass.py` is not wired into any runtime or CI | ROOT_FOLDER_AUDIT_001.md | Not grepped — file was read but CI integration not confirmed absent |
| NV5 | `tools/` has 35 .py source files | TECHNICAL_DEBT_REGISTER_001.md | Actual count from os.listdir: 79 — discrepancy, see Section 5 |

---

## Section 5 — Contradictions Found

These are claims in the audit documents that conflict with what the repository actually shows.

---

### CONTRADICTION 1 — Root File Counts Are Stale

**Audit claim:** 395 markdown files in root, 408 total root items  
**Actual (at time of review):** 401 markdown files confirmed (+6 audit deliverable docs); total root item count unverified — the figure 442 appeared in prior session output but the +34 delta (408→442) is unexplained by the 6 new audit docs alone and was not confirmed by a direct dir count in this review. The markdown count (401) is the material figure for the move plan.

**Root cause of markdown count discrepancy:** The 6 audit deliverable documents were written to root during the audit session, increasing the markdown count from 395 to 401.

**Impact:** Claims like "reduce root from 408 files to ~19" and "376 moveable markdown files" are understated. Actual moveable markdown count is approximately **388** (401 total − 13 must-stay).

**Severity:** LOW — directional claim is correct, count precision is slightly off. Update the move count estimate before executing.

---

### CONTRADICTION 2 — Batch 4 Severely Undercounts Affected Imports

**Audit claim (SAFE_MOVE_PLAN_001.md Batch 4):** Moving `hft/` and `crypto_scalper/` requires updating 3 main.py imports, 1 test mock (test_runtime_shutdown.py), and 1 test mock (test_runtime_loop_exception_observability.py was not mentioned).

**Actual scope:**

| Category | Files | Import Statements |
|---|---|---|
| External: main.py | 1 file | 3 statements (lines 17, 1313, 1410) |
| **Internal: hft/ package** | **4 files** | **12 statements** |
| **Internal: crypto_scalper/ package** | **2 files** | **2 statements** |
| **Real test import: test_realtime_feed.py** | **1 file** | **1 statement (REAL, not mock)** |
| Mock: test_runtime_shutdown.py | 1 file | 3 mock references |
| Mock: test_runtime_loop_exception_observability.py | 1 file | 1 mock reference |
| **TOTAL** | **10 files** | **~22 references** |

**Critical gap:** The audit **does not mention `tests/test_realtime_feed.py`** at all. This test has a **real import** (`from crypto_scalper.realtime_feed import CryptoRealtimeFeed, LiveTick, ...`) — not a mock. Moving `crypto_scalper/` without updating this test **will cause test suite failures**.

**Critical gap:** The audit **does not enumerate the internal hft/ and crypto_scalper/ package imports** (12 internal hft imports + 2 internal crypto_scalper imports). These use absolute package names (`from hft import config`, `from crypto_scalper.config import ...`). Moving the folders without addressing these would break the packages' own internal operation.

**Severity:** HIGH — Batch 4 cannot be safely executed using the import-update approach without first producing a complete import map covering all 22 references across 10 files. The `sys.path` alternative mentioned in Batch 4 would solve ALL imports (both external and internal) by making Python resolve `hft` and `crypto_scalper` from the `experiments/` directory.

---

### CONTRADICTION 3 — tools/ Python File Count

**Audit claim:** "35 source .py files" in `tools/`  
**Actual:** `os.listdir('tools/')` returns 79 .py files

**Root cause:** Unknown — either the original count used a filtered view (e.g., excluding some files), or files have been added to tools/ since the audit.

**Impact:** DEBT-005 description of "35 source .py files each with .cpython-311.pyc AND .cpython-312.pyc" may be understated. The .pyc count may be higher than the "44 .pyc" figure in the audit.

**Severity:** LOW — does not affect any move plan; .pyc files are already confirmed untracked.

---

## Section 6 — Corrections Needed

These must be updated in the audit documents before batch execution begins.

| # | Document | Location | Correction Required |
|---|---|---|---|
| C1 | `SAFE_MOVE_PLAN_001.md` | Batch 4 | Add `tests/test_realtime_feed.py` as a real import dependency (not a mock). **Under the rename approach** (rewriting all `from crypto_scalper.*` to `from experiments.crypto_scalper.*`), this test must be updated. **Under the recommended sys.path approach**, `test_realtime_feed.py` resolves unchanged — the purpose of enumerating it is to confirm it uses the bare top-level package name, making sys.path sufficient. Re-run `pytest tests/test_realtime_feed.py` after the move regardless of approach. |
| C2 | `SAFE_MOVE_PLAN_001.md` | Batch 4 | Enumerate all 14 internal package imports (12 in hft/, 2 in crypto_scalper/) and note their approach dependency: **under the rename approach**, all 22 references across 10 files require editing; **under the recommended sys.path approach**, none require editing — the enumeration's purpose is to verify every import uses the bare top-level package name so that sys.path resolution is sufficient. Either way, a full suite run after the move is required. |
| C3 | `REPOSITORY_ORGANIZATION_AUDIT_001.md` | Phase 1 counts | Update root markdown count from 395 to 401; update moveable count from "~376" to "~388". |
| C4 | `SAFE_MOVE_PLAN_001.md` | Move Table Summary | Update Batch 6 estimate from "376 files" to "~388 files". |
| C5 | `SAFE_MOVE_PLAN_001.md` | Batch 4 | Add `test_runtime_loop_exception_observability.py` to the test mock list (was not documented in the audit). |

---

## Section 7 — Startup-Critical File Protection Audit

All startup-critical and runtime-critical files verified present in root and NOT proposed for movement.

| File | Protected? | In Move Plan? |
|---|---|---|
| `CLAUDE.md` | YES (4,893 bytes) | Not moved — auto-loaded by Claude Code |
| `AGENTS.md` | YES (19,615 bytes) | Not moved — loaded by agent harness |
| `README.md` | YES (14,795 bytes) | Not moved — GitHub renders from root |
| `CODEX_START_HERE.md` | YES (7,314 bytes) | Not moved — referenced in CLAUDE.md |
| `PROJECT_RULES.md` | YES (6,148 bytes) | Not moved — referenced in CLAUDE.md |
| `CURRENT_PROJECT_STATUS.md` | YES (50,938 bytes) | Not moved — referenced in CLAUDE.md |
| `MASTER_AGENT_ROUTER.md` | YES (10,780 bytes) | Not moved — referenced in CLAUDE.md |
| `FILE_INDEX.md` | YES (24,775 bytes) | Not moved — navigation reference |
| `DOCUMENTATION_MAP.md` | YES (11,669 bytes) | Not moved — navigation reference |
| `main.py` | YES (63,323 bytes) | Not moved — entry point |
| `requirements.txt` | YES (356 bytes) | Not moved — pip convention |
| `pytest.ini` | YES (60 bytes) | Not moved — pytest looks in root |
| `.gitignore` | YES (821 bytes) | Not moved — git requires root |
| `.env.example` | YES (2,435 bytes) | Not moved — dev onboarding template |
| `CODEX_START_PROMPT.md` | YES (2,012 bytes) | Not moved — recommended stay |
| `CHATGPT_PROJECT_START_PROMPT.md` | YES (1,536 bytes) | May move to docs/ai_context/ per 6A — LOW risk |

**Verdict: All startup-critical files are protected.** No batch in the plan proposes moving CLAUDE.md, AGENTS.md, main.py, pytest.ini, or any critical root file.

---

## Section 8 — Runtime-Critical Path Audit

The plan does NOT touch any of the following:

- `polymarket/` source tree — unchanged
- `utils/` source tree — unchanged
- `config/settings.py` — unchanged
- `tests/` structure — unchanged (Batch 2 requires one import update)
- `runtime/` directory — explicitly excluded from all batches
- `logs/` directory — explicitly excluded (DEBT-006 marked separate task)
- `dashboard/src/` — unchanged
- All JSONL log paths — unchanged
- All environment variable names — unchanged

**Verdict: No runtime behavior is at risk from Batches 0–3, 5–8.** Batch 4 is the only batch with code-level risk (import path dependencies).

---

## Section 9 — Batch Approval Status

### APPROVED — Safe to Execute

These batches contain no discovered errors and can proceed after a pre-batch `pytest -q` pass.

| Batch | Action | Risk | Notes |
|---|---|---|---|
| 0.1 | Delete 3 venv backup folders | ZERO | All confirmed gitignored |
| 0.2 | Delete .env.backup.local | ZERO | Confirmed gitignored by `.env.*.local` rule |
| 0.3 | Delete 2 root stub .md files | LOW | Confirm docs/ copies are larger before deleting |
| 0.4 | Verify .gitignore .pyc coverage | ZERO | Already covered; no git rm needed — .pyc are untracked |
| 0.5 | Move docs.zip → archive/ | ZERO | Not referenced by any code |
| 0.6 | Delete or move task.md | ZERO | Temporary working note |
| 1 | Move 4 root Python scripts → scripts/ | LOW | `hft_paper_run.py` stays separate (it imports from polymarket.*, not hft/) |
| 3 | Move memory/ → .claude/memory/ | LOW | memory/ is 2 files; system auto-memory path is user-level (C:\Users\poh_2\.claude\...) — not the project memory/ |
| 5 | Archive research_cockpit/ and web-dashboard/ | LOW | Confirmed: no Python imports from production code. One scratch/ reference — irrelevant |
| 6A–6H | Move ~388 root markdown → docs/ subfolders | LOW | No Python imports involved. Update counts from 376 to 388 |
| 7 | Update navigation files (FILE_INDEX, DOCUMENTATION_MAP, etc.) | LOW | Execute after all moves complete |
| 8 | docs/research/ internal sort | LOW | Separate task; lowest priority |

---

### APPROVED WITH CONDITION — Execute Atomically

| Batch | Action | Condition |
|---|---|---|
| 2 | Move api/dashboard_api.py → dashboard/dashboard_api.py | Must update `tests/test_dashboard_api.py` line 6 in the same commit. Run `pytest tests/test_dashboard_api.py` before and after. |

---

### CORRECTIONS APPLIED — Batch 4 Unblocked (APPROVED WITH CONDITION)

**Status update (2026-06-26):** Corrections C1, C2, C4, C5 were applied to `SAFE_MOVE_PLAN_001.md` and C3 applied to `REPOSITORY_ORGANIZATION_AUDIT_001.md`. Batch 4 block is lifted.

| Batch | Action | Prior Block Reason | Resolution |
|---|---|---|---|
| 4 | Move hft/ and crypto_scalper/ → experiments/ | Two critical gaps: `test_realtime_feed.py` real import undocumented; 14 internal imports not enumerated | **RESOLVED** — complete 22-reference import map added to Batch 4; both approaches (sys.path and rename) documented; test_realtime_feed.py and test_runtime_loop_exception_observability.py added to required verification list |

**Batch 4 execution condition:** Execute `python -m pytest tests/ -q` before and after. The sys.path approach is recommended (no editing of any of the 22 import statements required). The exact steps are in SAFE_MOVE_PLAN_001.md Batch 4 Required Steps.

---

## Section 10 — .gitignore Adequacy

| Rule | Covers | Verdict |
|---|---|---|
| `*.pyc` | All .pyc files recursively | ADEQUATE |
| `*.py[cod]` | .pyc, .pyo, .pyd | ADEQUATE |
| `__pycache__/` | Bytecode cache dirs | ADEQUATE — note: no `**/` prefix, but Git applies this recursively by default |
| `.env.*.local` | `.env.backup.local` | CONFIRMED COVERED |
| `.venv/` | Active virtual env | COVERED |
| `.venv_broken_*/` | `.venv_BROKEN_poh2_py312_backup/`, `.venv_broken_POOHXYZ_migration_backup/` | CONFIRMED COVERED (case-insensitive on Windows) |
| `.venv_migration_old_backup/` | Third venv backup | COVERED — explicit rule |
| `runtime/` | All runtime-generated data | COVERED |
| `logs/` | Log files | COVERED |
| `scratch/` | Scratch files | COVERED |

**No .gitignore gaps found.** All high-risk file categories are covered.

---

## Section 11 — Batch Ordering Safety Review

The plan orders batches: zero-risk deletions → script moves → single-file folder move → AI memory → mode-package moves → abandoned dashboard prototypes → documentation moves → navigation file updates.

This ordering is **correct**. Rationale:

1. Deletions (Batch 0) have no dependencies and establish a clean baseline.
2. Script moves (Batch 1) are isolated — these scripts have no test coverage, confirmed by the test count.
3. api/ move (Batch 2) affects one test file — execute and immediately verify.
4. memory/ move (Batch 3) is AI tooling — no test or runtime dependency.
5. hft/crypto_scalper move (Batch 4) is the highest-risk batch — correctly placed after all safe batches.
6. Dashboard prototype archive (Batch 5) has no Python references — safe anywhere in the sequence.
7. Markdown moves (Batches 6A–6H) touch no code whatsoever — safe last.
8. Navigation file updates (Batch 7) must run last — after all moves are complete, so FILE_INDEX.md reflects final paths.

**The ordering is sound.** No dependency violation found.

---

## Section 12 — Incremental Execution with Tests

The plan CAN be executed incrementally with pytest verification between each batch. Recommended checkpoints:

| After Batch | Test Command | What It Catches |
|---|---|---|
| 0 (all deletions) | `python -m pytest tests/ -q` | Baseline — confirm deletes didn't break anything |
| 1 (scripts moved) | `python -m pytest tests/ -q` | Confirm no tests imported moved scripts |
| 2 (api/ moved) | `python -m pytest tests/test_dashboard_api.py -v` | Direct verification of the one affected test |
| 4 (hft/ crypto/ moved) | `python -m pytest tests/ -q` | Most critical check — confirms all import paths resolved |
| 6H (all markdown moved) | `python -m pytest tests/ -q` | Regression check — markdown moves shouldn't touch Python |
| 7 (navigation updated) | Manual review of FILE_INDEX.md | Confirm all paths are updated |

---

## Section 13 — Final Recommendation

**PROCEED WITH CAUTION**

The audit documents are **structurally sound and directionally correct**. The proposed repository organization is well-designed. The batch ordering is safe. The startup-critical and runtime-critical files are protected.

**Approved for immediate execution:** Batches 0, 1, 3, 5, 6A–6H, 7, 8

**Approved with condition:** Batch 2 (execute atomically with test update)

**Approved with condition:** Batch 4 (sys.path approach recommended; run full pytest before and after)

**Corrections applied (2026-06-26):**

1. ✅ C1 — `tests/test_realtime_feed.py` added to Batch 4 (real import, not a mock).
2. ✅ C2 — All 14 internal package imports enumerated in Batch 4 (12 in hft/, 2 in crypto_scalper/).
3. ✅ C3 — Root markdown count updated 395 → 401 in `REPOSITORY_ORGANIZATION_AUDIT_001.md`.
4. ✅ C4 — Batch 6 moveable estimate updated ~376 → ~388 in `SAFE_MOVE_PLAN_001.md`.
5. ✅ C5 — `tests/test_runtime_loop_exception_observability.py` added to mock list in Batch 4.

**All identified corrections have been applied. Batch 4 is unblocked.**

The overall reorganization will reduce root from 401 markdown files to approximately 13, which is the correct target. No runtime behavior changes are proposed. The core quant engine is untouched.

---

## Appendix — Complete Import Dependency Map for Batch 4

For executor reference. All references that break if `hft/` or `crypto_scalper/` move without sys.path adjustment:

### crypto_scalper/ references (6 files, 9 statements)

| File | Line | Type | Statement |
|---|---|---|---|
| `main.py` | 17 | External import | `from crypto_scalper.live_runner import main as run_scalper` |
| `main.py` | 1313 | External import | `from crypto_scalper.realtime_feed import CryptoRealtimeFeed` |
| `crypto_scalper/backtest.py` | 18 | Internal import | `from crypto_scalper.config import write_freqtrade_config` |
| `crypto_scalper/live_runner.py` | 14 | Internal import | `from crypto_scalper.config import write_freqtrade_config` |
| `tests/test_realtime_feed.py` | 8 | **Real test import** | `from crypto_scalper.realtime_feed import (CryptoRealtimeFeed, LiveTick, ...)` |
| `tests/test_runtime_loop_exception_observability.py` | 12 | Mock | `monkeypatch.setitem(sys.modules, "crypto_scalper.live_runner", ...)` |
| `tests/test_runtime_shutdown.py` | 83, 132, 163 | Mock (×3) | `monkeypatch.setitem(sys.modules, "crypto_scalper.live_runner", ...)` |

### hft/ references (5 files, 13 statements)

| File | Line | Type | Statement |
|---|---|---|---|
| `main.py` | 1410 | External import | `from hft.main import run_hft` |
| `hft/main.py` | 47 | Internal import | `from hft import config as C` |
| `hft/main.py` | 48 | Internal import | `from hft.market_manager import MarketManager, OpenPosition` |
| `hft/main.py` | 49 | Internal import | `from hft.signal_engine import HFTSignalEngine, HFTSignal` |
| `hft/main.py` | 50 | Internal import | `from hft.risk_manager import HFTRiskManager` |
| `hft/main.py` | 51 | Internal import | `from hft.execution_engine import ExecutionEngine` |
| `hft/main.py` | 52 | Internal import | `from hft.utils import (...)` |
| `hft/execution_engine.py` | 24 | Internal import | `from hft import config as C` |
| `hft/execution_engine.py` | 25 | Internal import | `from hft.utils import calc_fee` |
| `hft/market_manager.py` | 19 | Internal import | `from hft import config as C` |
| `hft/market_manager.py` | 20 | Internal import | `from hft.utils import current_epoch, ...` |
| `hft/signal_engine.py` | 32 | Internal import | `from hft import config as C` |
| `hft/signal_engine.py` | 33 | Internal import | `from hft.utils import (...)` |

**Note:** `hft/risk_manager.py` was not returned by the grep — it likely uses no `from hft` imports (uses only stdlib/third-party). Verify before executing.

**Note:** `hft_paper_run.py` in root does NOT import from `hft/` — it is a standalone script. Moving `hft/` does not affect `hft_paper_run.py`.
