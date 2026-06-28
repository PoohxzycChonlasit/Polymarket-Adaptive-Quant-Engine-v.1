# ENTERPRISE_BATCH_MIGRATION_SYSTEM_001

**Status:** ACTIVE  
**Date:** 2026-06-28  
**Purpose:** Standardize and accelerate repository reorganizations through risk-aware atomic batch migrations, eliminating slow single-file planning cycles.

---

## 1. Migration Philosophy

We prioritize **velocity with safety**. The old workflow of moving 1-2 files per plan/move cycle is slow, increases operational overhead, and generates redundant commits. We replace it with a structured, automated batch migration workflow where moves are classified by risk and executed in safe, cohesive batches.

---

## 2. Stop Micro-Move Rule

Micro-moves (moving fewer than 3 files that share similar low-risk characteristics in separate plan/move tasks) are **DISCOURAGED**.
* If a set of files is classified as `SAFE_ATOMIC` or `MEDIUM_ATOMIC` and falls within the same domain, they MUST be batched together.
* Separate plan-only and move-only tasks are required ONLY if the batch risk score is `PLAN_REQUIRED` or `DO_NOT_MOVE`, or when the operator explicitly requests it.

---

## 3. Batch Size Rules

To ensure reviews and validation remain manageable, we enforce the following batch limits:
* **Maximum files per batch:** 12 files (including moved scripts and their associated tests).
* **Maximum line diff per batch:** 1,500 lines.
* **Maximum decoupled modules:** 4 unrelated feature areas.

---

## 4. Blast Radius Scoring Model

The blast radius of a batch is calculated based on the dependency count and execution paths of all files in the batch.

$$\text{Blast Radius Score} = \text{Dependency Count} \times \text{Risk Coefficient}$$

| Blast Radius Score | Level | Definition | Action Required |
|---|---|---|---|
| $0 - 2$ | **LOW** | No runtime imports; test-only or diagnostic utility dependencies. | Direct atomic execution allowed. |
| $3 - 6$ | **MEDIUM** | Dynamic imports, CLI task runner scripts, or internal tools dependencies. | Targeted pre-move imports scan required. |
| $> 6$ | **HIGH** | Runtime imports, strategy/risk/sizing imports, or missing test suites. | **STOP**. Requires explicit design plan approval. |

---

## 5. Dependency Graph Requirements

Before initiating any batch migration, the AI must verify:
1. **Outbound Dependencies:** All imports of target files are resolved (stdlib, external packages, internal `polymarket` runtime).
2. **Inbound Dependencies:** All scripts, tests, and config files importing target files are mapped using `rg` or a knowledge graph query.
3. **Dynamic References:** All references in task runners (e.g., `multi_session_runner.py`'s `REPLAY_STEPS`) are verified.

---

## 6. Safe Batch Criteria (`SAFE_ATOMIC`)

A batch is classified as `SAFE_ATOMIC` and can be moved without a separate planning task if:
* Total Blast Radius Score of the batch is **LOW**.
* Files have zero inbound imports from core runtime (`polymarket/`).
* Files have dedicated test files with $\ge 80\%$ code coverage.
* No files are imported by other root tools.

---

## 7. Medium-Risk Batch Criteria (`MEDIUM_ATOMIC`)

A batch is classified as `MEDIUM_ATOMIC` and can be moved in a single atomic commit with targeted validation if:
* Total Blast Radius Score of the batch is **MEDIUM**.
* Files are referenced in dynamic task runners (like `multi_session_runner.py`) but module string updates are straightforward.
* Files have inbound imports only from other non-runtime tools (diagnostic/research scripts).

---

## 8. Defer Criteria

A file must be deferred from the current batch if:
* Moving it would exceed the batch size limit (12 files/1,500 line diffs).
* Its imports are highly coupled to another pending batch.
* Its corresponding test suite is missing or broken.

---

## 9. Forbidden Batch Criteria

A batch is **FORBIDDEN** and must trigger an immediate safety halt if it contains:
* Files from `polymarket/` or `config/`.
* Strategy, sizing, risk, or execution code.
* Files with unknown or unmapped dependencies.
* Files containing `_risk_plan_zero_diagnostics`, `_diagnostic_float`, or `_diagnostic_int`.

---

## 10. Validation Matrix

| Risk Level | Compilation | Targeted Tests | Full Pytest | Runbook Validation |
|---|---|---|---|---|
| **SAFE_ATOMIC** | Required | Required | Not Required | Not Required |
| **MEDIUM_ATOMIC**| Required | Required | Recommended | Required (Dry Run) |
| **PLAN_REQUIRED**| Required | Required | Required | Required (Full Run) |

---

## 11. Rollback Protocol

If validation fails post-move, the agent must execute the following commands immediately to restore the branch state:
```bash
# 1. Revert file moves using git mv back to original locations
git mv tools/target/file.py tools/file.py

# 2. Revert import changes and state files
git checkout -- tests/ docs/operations/ ACTIVE_WORKFLOW_STATE_001.json TASK_QUEUE_001.json
```
*Do NOT use `git reset --hard` unless explicitly authorized by the operator.*

---

## 12. Commit/Push Protocol

All changes for a batch (moves, test updates, reports, ops JSONs, loop memory) must be committed together:
* **Commit Message Format:** `refactor(batch): move <Batch Name> tools to <Target Folder>`
* **Push Policy:** Always push to `origin main` immediately after a successful local commit to keep parallel sessions synced.

---

## 13. Operator Approval Thresholds

* **SAFE_ATOMIC:** No plan task required; direct atomic implementation and commit.
* **MEDIUM_ATOMIC:** Direct execution allowed unless the operator requests a plan-first gate.
* **PLAN_REQUIRED / HIGH:** Planning phase and explicit operator approval mandatory before execution.
