# BATCH_MIGRATION_RISK_MODEL_001

**Status:** ACTIVE  
**Date:** 2026-06-28  
**Purpose:** Quantitative risk scoring and categorization for repository migration files.

---

## 1. Risk Dimensions and Scoring

Each file candidate is evaluated across 8 risk dimensions. The sum of these scores determines the file's migration risk classification.

$$\text{Total File Risk Score} = \sum (\text{Dimension Scores})$$

### 1.1 Runtime Import Risk (Weight: 4)
* **Score 0:** No runtime imports.
* **Score 2:** Imported by non-core runtime utilities.
* **Score 4:** Imported by `polymarket/` or core runtime modules.

### 1.2 Execution/Risk/Sizing Import Risk (Weight: 5)
* **Score 0:** No execution/risk/sizing imports.
* **Score 5:** Imported by `polymarket/trader.py`, risk managers, or sizing modules.

### 1.3 Test Coverage Risk (Weight: 2)
* **Score 0:** Dedicated test suite exists with $\ge 80\%$ coverage.
* **Score 1:** Dedicated test exists but coverage is $< 80\%$.
* **Score 2:** No dedicated test file exists.

### 1.4 Dynamic Import Risk (Weight: 3)
* **Score 0:** Evaluated via static imports only.
* **Score 3:** Evaluated dynamically (e.g. `importlib.import_module` in `multi_session_runner.py`).

### 1.5 CLI Command Risk (Weight: 2)
* **Score 0:** No CLI or terminal execution history.
* **Score 1:** Simple manual command line utility.
* **Score 2:** Hardcoded in runner scripts or automated pipelines.

### 1.6 Docs-only Reference Risk (Weight: 1)
* **Score 0:** No references in markdown docs.
* **Score 1:** Reference exists in developer/architecture docs (docs-only update needed).

### 1.7 Ops Active Reference Risk (Weight: 3)
* **Score 0:** Not referenced in ops files.
* **Score 3:** Named directly in `ACTIVE_WORKFLOW_STATE_001.json` or `TASK_QUEUE_001.json`.

### 1.8 Unknown Reference Risk (Weight: 4)
* **Score 0:** Dependency graph is fully mapped and verified.
* **Score 4:** Unresolved or obsolete dependencies exist.

---

## 2. Output Risk Levels

The total score of a batch (or individual candidate) maps to one of four action levels:

| Total Score | Level | Definition | Protocol |
|---|---|---|---|
| **$0 - 3$** | `SAFE_ATOMIC` | Minimal dependency and low validation requirements. | Move, update test imports, compile, test, commit, and push in one go. |
| **$4 - 7$** | `MEDIUM_ATOMIC` | Moderate dependencies or dynamic module strings. | Same-session execution allowed. Requires pre-move imports scan and targeted dry run. |
| **$8 - 11$** | `PLAN_REQUIRED` | Complex dependencies, cross-tool imports, or active state references. | Requires a Class 2 Plan task + operator review before execution. |
| **$\ge 12$** | `DO_NOT_MOVE` | Core runtime imports, safety-critical code, or untested modules. | **LOCKED**. Migration is forbidden without a formal architectural review. |
