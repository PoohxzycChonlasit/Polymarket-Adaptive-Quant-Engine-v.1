# TECHNICAL_DEBT_REGISTER_V2

**Task:** FULL_PROJECT_REALITY_AUDIT_001  
**Mode:** DISCOVERY ONLY — no code changes  
**Date:** 2026-06-26  
**Supersedes:** `TECHNICAL_DEBT_REGISTER_001.md` (organizational debt only)  
**Scope:** Full repository — code + organization + architecture

---

## Debt Classification

| Severity | Meaning |
|---|---|
| CRITICAL | Actively impairs development, AI context loading, navigation, or presents ongoing maintainability risk |
| HIGH | Significant architecture, performance, or reliability concern — should resolve before next major feature |
| MEDIUM | Real debt, no immediate impact on functionality |
| LOW | Cosmetic or minor — address during regular maintenance |

---

## CRITICAL Debt

---

### DEBT-C001: Root Directory Markdown Pollution (395 files)

**Severity:** CRITICAL  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-001  
**Evidence:** PowerShell count at audit time: 395 markdown files in project root  

**Description:**  
Every audit report, design doc, patch report, forensic investigation, commit record, and implementation note has been written to the repository root. This makes the root:
- Unnavigable for humans
- Extremely expensive for AI context loading (agent must parse 395+ filenames)
- Git status always overwhelming (every new file adds `??` noise)

**Impact:** AI Readability=2/10, Repository Organization=2/10

**Suggested future action:** Move ~376 moveable markdown files to organized `docs/` subfolders per `SAFE_MOVE_PLAN_001.md`. ~19 files must remain in root (CLAUDE.md, AGENTS.md, main.py, requirements.txt, .env*, .gitignore, pytest.ini, README.md, and AI startup context files).

**Fix risk:** LOW — markdown files have no runtime dependencies.

---

### DEBT-C002: polymarket/trader.py is a 634KB God Class

**Severity:** CRITICAL (code architecture)  
**File:** `polymarket/trader.py` (649,554 bytes, ~13,000+ lines)  
**Evidence:** File size measurement, `__init__` structure read (trader.py:363–541)

**Description:**  
`PolymarketTrader` performs at minimum 12 distinct responsibilities:
1. Market selection (GammaFetcher orchestration)
2. Signal evaluation (compute_realtime_signal coordination)
3. Probability scoring (ProbabilityModelInput construction)
4. EV calculation (ExpectedValueInput construction)
5. Risk mode management (RiskModeState updates)
6. Bankroll tier management (BankrollRankLock updates)
7. Position sizing (calculate_position_size coordination)
8. Order plan construction (build_order_plan)
9. Order intent validation (validate_order_intent)
10. Paper execution (virtual position management)
11. Position reconciliation (ReconciliationReport management)
12. Event logging orchestration (QuantEventLogger, RuntimeEventStream coordination)

Plus: stop-loss monitoring, arbitrage scanning, WebSocket management, Telegram alerts, terminal UI coordination, path-truth checkpoint emission, preload-next-market logic, empty-book recovery, shadow telemetry.

**Impact:** Any change to any subsystem requires understanding 13,000 lines of context. Maintainability score 4/10. A bug in market selection and a bug in stop-loss monitoring look identical in `git diff trader.py`.

**Suggested future action:** Decompose into domain-specific modules. Example split:
- `polymarket/market_selector.py` — GammaFetcher orchestration
- `polymarket/decision_pipeline.py` — Signal → Probability → EV coordination
- `polymarket/execution_coordinator.py` — Order plan + intent validation + paper execution
- `polymarket/position_lifecycle.py` — Position tracking, reconciliation, stop-loss
- `polymarket/session_manager.py` — Startup/shutdown, ownership, health monitoring
- `polymarket/trader.py` — Thin dispatcher only

**Fix risk:** VERY HIGH. Requires careful refactoring of 13,000 lines with extensive integration testing. Do not attempt without a complete test suite green baseline.

---

### DEBT-C003: Three Venv Backups in Repository Root

**Severity:** CRITICAL (disk pollution)  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-002  
**Folders:** `.venv_BROKEN_poh2_py312_backup/`, `.venv_broken_POOHXYZ_migration_backup/`, `.venv_migration_old_backup/`

**Description:**  
Three full Python virtual environment backups in the project root, each likely 500MB+. Pollutes directory listings and could confuse Python environment tooling.

**Fix risk:** ZERO — package caches only. `pip install -r requirements.txt` recreates.

---

## HIGH Debt

---

### DEBT-H001: polymarket/signal.py Module-Level Import Side Effect

**Severity:** HIGH  
**File:** `polymarket/signal.py:36-51`  
**Evidence:** Source read — `_s = get_settings()` at module level, then `_MIN_RSI`, `_MAX_RSI`, etc. set from `_s`

**Description:**  
`polymarket/signal.py` calls `get_settings()` at module import time. This means:
1. Importing `polymarket.signal` requires a valid `.env` file or environment variables
2. Signal module cannot be imported in clean environments (CI without env, test without env setup)
3. Settings are baked into module constants at first import — any settings change requires Python process restart
4. `_load_validated_metrics()` also runs at import time, reading from CWD-relative `backtest_results/polymarket_5m/latest_metrics.json`

**Impact:** Test isolation is harder. Any test that imports `polymarket.signal` must mock or provide a complete `.env`. Makes signal.py non-importable in clean CI.

**Suggested future action:** Move settings loading to a function call inside `compute_realtime_signal()`. Cache results locally if performance requires it.

**Fix risk:** MEDIUM — requires updating signal.py and verifying backtest mirror still matches.

---

### DEBT-H002: Two Competing Dashboard Directories

**Severity:** HIGH  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-004  
**Folders:** `dashboard/` (active), `research_cockpit/` (orphaned), `web-dashboard/` (orphaned)

**Description:**  
Only `dashboard/` shows active development. `research_cockpit/` and `web-dashboard/` appear to be abandoned prototypes. No Python imports reference either orphaned directory.

**Fix risk:** LOW — confirm no test references, then delete.

---

### DEBT-H003: Secondary Mode Folders at Top-Level (hft/, crypto_scalper/)

**Severity:** HIGH  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-003  
**Folders:** `hft/`, `crypto_scalper/`  
**Evidence:** `main.py:17` (module-level crypto_scalper import), `main.py:1410` (lazy hft import)

**Description:**  
Both packages are active (imported by main.py) but sit at top-level scope, appearing visually equivalent to the core `polymarket/` engine. This obscures their secondary status.

**Coupling points for hft:**
- `main.py:1410` lazy import `from hft.main import run_hft`
- No test imports found (HFT tests likely covered via runtime testing)

**Coupling points for crypto_scalper:**
- `main.py:17` module-level `from crypto_scalper.live_runner import main as run_scalper`
- `main.py:1313` module-level `from crypto_scalper.realtime_feed import CryptoRealtimeFeed`
- `tests/test_runtime_shutdown.py:83` `monkeypatch.setitem(sys.modules, "crypto_scalper.live_runner", ...)`

**Suggested future action:** Move to `experiments/hft/` and `experiments/crypto_scalper/`. Requires 3 import updates in main.py + 1 in test_runtime_shutdown.py.

**Fix risk:** HIGH — moving without updating all import paths breaks `python main.py` for scalper and hft modes.

---

### DEBT-H004: logs/ Has 980 Files Flat

**Severity:** HIGH  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-006  
**Folder:** `logs/`

**Description:**  
980 log files in a flat directory. Slow to list in Windows Explorer and certain tools. Should be structured by date.

---

### DEBT-H005: Two Parallel Event Systems With Overlapping Domain

**Severity:** HIGH (new finding)  
**Files:** `utils/quant_event_logger.py`, `utils/runtime_event_stream.py`  
**Evidence:** Both initialized in `PolymarketTrader.__init__()` (trader.py:533, adjacent lines). Both handle trade and risk events.

**Description:**  
Two separate event logging systems coexist:
- `QuantEventLogger` — synchronous, JSONL per-category (14 event types), priority-classified
- `RuntimeEventStream` — asynchronous, bounded deque, background writer, priority-ranked drop policy

Both appear in trader.__init__ and both handle similar event types (trade open/close, risk events). No documented boundary exists between "which events go to QuantEventLogger" vs "which events go to RuntimeEventStream." This creates:
1. Potential for duplicate events in some JSONL files
2. Potential for missed events if one system is conditionally disabled
3. Two separate recovery paths if a writer crashes

**NOT VERIFIED RUNTIME:** Cannot confirm from source alone whether both are always active or if one is conditional.

**Suggested future action:** Document the ownership boundary clearly. Verify no event type is written to both systems. Consider a unified event bus that routes to both systems transparently.

---

## MEDIUM Debt

---

### DEBT-M001: utils/risk_manager.py Legacy TierInfo Wrapper

**Severity:** MEDIUM (new finding)  
**Files:** `utils/risk_manager.py`, `polymarket/bankroll_tiers.py`

**Description:**  
`utils/risk_manager.py` defines a `TierInfo` NamedTuple that wraps `BankrollTierConfig`. The `get_bankroll_tier()` function in risk_manager calls `polymarket.bankroll_tiers.get_tier_config()` and returns a `TierInfo`. This creates an adapter layer for backward compatibility. The hard limits in risk_manager.py (`HARD_CAP_SINGLE_TRADE=0.03`, `FLOOR_BALANCE=5.00`, etc.) are genuine values not in bankroll_tiers.py, so the file is not redundant — but the `TierInfo` wrapper is legacy indirection.

---

### DEBT-M002: api/ Single-File Folder

**Severity:** MEDIUM  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-009  
**File:** `api/dashboard_api.py` (sole file in `api/`)

**Description:**  
One file in one folder. Belongs in `dashboard/`. Import in `tests/test_dashboard_api.py` would need updating.

---

### DEBT-M003: scratch/ Has No Boundary or .gitignore

**Severity:** MEDIUM  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-008

---

### DEBT-M004: research/ and docs/research/ Overlap

**Severity:** MEDIUM  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-014

---

### DEBT-M005: Duplicate Documentation Files

**Severity:** MEDIUM  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-010  
**Pairs:** KNOWN_ISSUES.md (root stub 267B vs docs/ canonical 18.7KB), PROJECT_STRUCTURE.md (root stub 671B vs docs/ 13.4KB), BANKROLL_TIER_FRAMEWORK_V1.md (both in root and docs/)

---

### DEBT-M006: hardcoded backtest_results/ Path in signal.py

**Severity:** MEDIUM (new finding)  
**File:** `polymarket/signal.py:56`  
**Evidence:** `_METRICS_PATH = Path("backtest_results/polymarket_5m/latest_metrics.json")` — hardcoded CWD-relative path, not configurable via settings

**Description:**  
The path is silently ignored if the file doesn't exist (falls back to hardcoded defaults). But the path cannot be redirected via configuration — any non-standard working directory will silently fall back to defaults without notification. Should use `settings.backtest_results_dir` or equivalent.

---

### DEBT-M007: memory/ in Project Root Instead of .claude/

**Severity:** MEDIUM  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-013

---

### DEBT-M008: .env.backup.local in Root

**Severity:** MEDIUM (security)  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-011

---

### DEBT-M009: docs.zip in Root

**Severity:** MEDIUM  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-012

---

### DEBT-M010: anthropic in Runtime requirements.txt

**Severity:** MEDIUM (new finding)  
**File:** `requirements.txt:1` — `anthropic==0.95.0`

**Description:**  
The `anthropic` package is listed in the main `requirements.txt`. This suggests the AI client is a runtime dependency of the paper trading engine. This should be verified: if anthropic is only used by tools/ scripts (e.g., `tools/research_memory_writer.py`), it should be in a separate `requirements-tools.txt`. If it is used at runtime, its 8-second timeout (`ai_timeout_seconds: int = 8` in settings.py) must be verified as non-blocking on the trading hot path.

---

## LOW Debt

---

### DEBT-L001: main.py Is a Monolithic 63KB File

**Severity:** LOW for docs, HIGH for code  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-007  
**File:** `main.py` (63,323 bytes)

**Description:**  
`main.py` contains mode-routing dispatch logic, paper session startup, live session startup, verify mode, dashboard modes, helper functions, and shutdown sequencing. Should be decomposed into mode-specific handlers. Currently a HIGH code-architecture concern but LOW for documentation purposes.

---

### DEBT-L002: Naming Convention Inconsistency

**Severity:** LOW  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-016

---

### DEBT-L003: task.md in Root

**Severity:** LOW  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-017

---

### DEBT-L004: Scripts Split Between Root and scripts/

**Severity:** LOW  
**Inherited from:** TECHNICAL_DEBT_REGISTER_001 DEBT-019

---

### DEBT-L005: display.py (217KB) Has No Test Coverage

**Severity:** LOW  
**File:** `utils/display.py` (217,420 bytes)

**Description:**  
The terminal UI renderer is the second-largest file in the repository after trader.py. It has no direct test file. Display logic is typically hard to unit test, but 217KB of untested rendering code creates regression risk on any change.

---

### DEBT-L006: freqtrade in Runtime requirements.txt

**Severity:** LOW  
**File:** `requirements.txt` — `freqtrade==2026.2`

**Description:**  
FreqTrade is a full trading framework listed as a runtime dependency. It is unclear what specific components are imported from it. If only a few utilities are used (e.g., TA-Lib indicators), this is a heavyweight dependency that brings in many transitive packages. Should verify actual usage and consider replacing specific imports with lighter alternatives.

---

## Complete Debt Registry

| ID | Severity | Description | Fix Risk |
|---|---|---|---|
| DEBT-C001 | CRITICAL | 395 markdown files in root | LOW |
| DEBT-C002 | CRITICAL | trader.py 634KB god class | VERY HIGH |
| DEBT-C003 | CRITICAL | 3 venv backups in root | ZERO |
| DEBT-H001 | HIGH | signal.py module-level settings loading side effect | MEDIUM |
| DEBT-H002 | HIGH | Two orphaned dashboard directories | LOW |
| DEBT-H003 | HIGH | hft/ and crypto_scalper/ at top-level (active, not orphaned) | HIGH |
| DEBT-H004 | HIGH | logs/ 980 files flat | MEDIUM |
| DEBT-H005 | HIGH | Two parallel event systems with overlapping domain | MEDIUM |
| DEBT-M001 | MEDIUM | risk_manager.py legacy TierInfo wrapper | LOW |
| DEBT-M002 | MEDIUM | api/ single-file folder | LOW |
| DEBT-M003 | MEDIUM | scratch/ no boundary | LOW |
| DEBT-M004 | MEDIUM | research/ vs docs/research/ overlap | LOW |
| DEBT-M005 | MEDIUM | Duplicate documentation files (3 pairs) | LOW |
| DEBT-M006 | MEDIUM | signal.py hardcoded backtest_results/ path | LOW |
| DEBT-M007 | MEDIUM | memory/ in root instead of .claude/ | LOW |
| DEBT-M008 | MEDIUM | .env.backup.local security risk | LOW (delete) |
| DEBT-M009 | MEDIUM | docs.zip in root | LOW |
| DEBT-M010 | MEDIUM | anthropic in runtime requirements — verify usage | LOW |
| DEBT-L001 | LOW | main.py 63KB (code concern) | HIGH if changed |
| DEBT-L002 | LOW | Naming convention inconsistency | LOW |
| DEBT-L003 | LOW | task.md in root | LOW (delete) |
| DEBT-L004 | LOW | Scripts split between root and scripts/ | LOW |
| DEBT-L005 | LOW | display.py 217KB no test coverage | LOW |
| DEBT-L006 | LOW | freqtrade in requirements — verify actual usage | LOW |

**Total: 3 CRITICAL, 5 HIGH, 8 MEDIUM, 6 LOW**

---

## Priority Order for Resolution

**Sequence 1 — Zero-risk cleanup (do immediately, no code changes):**
- DEBT-C003: Delete 3 venv backups
- DEBT-M008: Delete .env.backup.local
- DEBT-L003: Delete or move task.md
- DEBT-M009: Extract docs.zip and delete if contents already in docs/

**Sequence 2 — Low-risk organization (safe batch moves):**
- DEBT-C001: Move ~376 root markdown files to docs/ per SAFE_MOVE_PLAN_001.md
- DEBT-M007: Move memory/ to .claude/memory/
- DEBT-M002: Move api/dashboard_api.py to dashboard/ + update test import

**Sequence 3 — Medium-risk code quality (requires testing):**
- DEBT-H001: Move signal.py settings loading inside compute_realtime_signal()
- DEBT-H005: Document event system ownership boundary; verify no duplicate events

**Sequence 4 — High-risk structural changes (requires careful planning):**
- DEBT-H003: Move hft/ and crypto_scalper/ to experiments/ (3 import updates + 1 test)
- DEBT-H002: Delete orphaned dashboard directories after confirming no references

**Sequence 5 — Long-horizon architecture (requires major refactor):**
- DEBT-C002: Decompose trader.py into domain modules
- DEBT-L001: Decompose main.py into mode handlers
