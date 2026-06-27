# POST_LONG_VALIDATION_REFACTOR_STRATEGY_REVIEW_001

## 1. Baseline State
- **Current HEAD Commit:** `44d51b4` — docs: finalize long validation commit hashes
- **Last Refactor Batches:** Batch 3A (Display State), Batch 3B (Observability cadences & orderbook timing shims), Batch 3C (Display proxy removal) successfully completed and committed.
- **Batch 3D Gate Status:** **DEFERRED** (`PAUSE_BATCH_3D_DEFER` verdict issued).

---

## 2. Long Validation Evidence Summary
The 30-minute validation run (`LONG_RUNTIME_VALIDATION_001`) successfully completed:
- **Duration:** 31 minutes 38 seconds (1,898 seconds total).
- **Cycles:** 33 full loops completed.
- **Safety checks:** 0 AttributeErrors, 0 Tracebacks, 0 loop exceptions. Confirmed `STATUS NO LIVE ORDERS`.
- **Telemetry verification:** Event stream populated with thousands of valid JSONL records (`orderbook_refresh_source`, `market_evaluation_duration_ms`, `decision_cycle_interval_seconds`, `runtime_heartbeat_v1`).

---

## 3. Batch 3D Defer Rationale
The gate check of Batch 3D (`_phase2_complete_lifecycle_observability` and `_phase2_observability_payload`) concluded with a **PAUSE/DEFER** decision for the following reasons:
1. **Low Safe Extraction Scores:** Assigned **5/10** and **3/10** respectively due to extreme coupling to 16 preloader attributes and 10+ private trader helper methods.
2. **Bidirectional Coupling:** Extracting these methods alone would force the helper to call back the trader instance continuously, increasing system complexity without achieving modular separation.
3. **Boundary Violation:** `_phase2_observability_payload` queries bankroll state and position sizes via `_phase2_exposure_timeline`, violating the strict separation between telemetry and risk/sizing logic.

---

## 4. Options Matrix

| Option | Description | Pros | Cons | Risk | Strategic Alignment |
|--------|-------------|------|------|------|--------------------|
| **Option A** | Resume `trader.py` refactor (Batch 3D) | Reduces `trader.py` line count directly. | Low safe extraction scores; requires heavy helper callbacks. | **HIGH** | Low. Telemetry helper would become tightly coupled to core trader. |
| **Option B** | Build Runtime Session Manager | Prevents duplicate runs, handles clean init/shutdown, automates validation runs. | Requires initial scripting effort. | **LOW** | **HIGH**. Directly addresses the orphaned duplicate PID issue exposed during long validation. |
| **Option C** | Repository Graph Enablement | Automates import cycle and coupling detection. | Offline tool development only; doesn't touch runtime. | **NONE** | **MEDIUM**. Highly valuable for future refactor validation. |
| **Option D** | Runtime Log Governance | Strips TUI redraw characters, governs rate-limiting and event stream file sizes. | Requires careful curses stream modifications. | **LOW-MEDIUM** | **HIGH**. Directly addresses the 27.8MB TUI raw log and 82.7MB daily JSONL size. |
| **Option E** | Resolve `LOW_PRICE_TRUTH_RESOLUTION_001` | Solves open quant strategy question. | Highly sensitive strategy/signal logic; requires backtesting. | **HIGH** | **LOW** (Orthogonal to codebase engineering hygiene). |

---

## 5. Primary Recommendation
### `RUNTIME_SESSION_MANAGER_ENABLEMENT_001` (Option B)
- **Why selected:** During `LONG_RUNTIME_VALIDATION_001`, we discovered that duplicate, orphaned Python processes (`9568` / `5448`) from a previous day's run were still running concurrently in the environment. A runtime session manager is critical to enforce single-process execution bounds, prevent API collisions, protect logs from write collisions, and guarantee a clean shutdown.
- **Deliverables:** A runtime coordinator script/tool to detect active sessions, enforce single-instance locks, rename and rotate log outputs cleanly, and safely manage process lifecycles.

---

## 6. Secondary Recommendation
### `RUNTIME_LOG_GOVERNANCE_001` (Option D)
- **Why selected:** The 30-minute validation run exposed massive log outputs: a 27.8 MB curses-drawn TUI log and an 82.7 MB daily event stream. We must implement log governance to strip TUI screen-clearing control characters, rotate log files automatically, and throttle repetitive event stream telemetry.

---

## 7. Next Task Contract

### Target Next Task
- **Task ID:** `RUNTIME_SESSION_MANAGER_ENABLEMENT_001`
- **Task Class:** 7 (FEATURE / TOOLING)
- **Workflow Tier:** LOOP

### Stop Conditions
- Any attempt to run live orders or mock live client keys.
- Any write operations outside `tools/`, `docs/`, and `utils/session_manager/`.

---

## 8. Final Verdict
```
POST_LONG_VALIDATION_REFACTOR_STRATEGY_REVIEW_COMMITTED
```
