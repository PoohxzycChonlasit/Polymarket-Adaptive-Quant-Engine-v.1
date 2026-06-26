# CANONICAL_DOCUMENT_RECONCILIATION_001

## 1. Executive Summary

This audit reconciles the newly designed **RESEARCH_GOVERNANCE_V1_DESIGN** and **PROJECT_OS_V1_DESIGN** against the existing repository core files (`CURRENT_PROJECT_STATUS.md`, `PROJECT_RULES.md`, `AGENTS.md`, `MASTER_AGENT_ROUTER.md`).

- **Key Finding**: The current repository has excellent conceptual guidelines (role routing, 3-option rule, logging budgets) but lacks any active tracking registers (no audit registries, no decision ledgers).
- **Core Recommendation**: Integrate the Audit and Decision registries as active files, standardize the audit format, and write the anti-loop rules and search-pruning constraints directly into `PROJECT_RULES.md`.

---

## 2. Current Canonical State

The repository's active governance is document-driven and relies on:
- `PROJECT_RULES.md`: Sets limits on VPS storage (~5GB), daily log sizes (<150MB/day), websocket caching, and file inspection boundaries.
- `MASTER_AGENT_ROUTER.md` & `AGENTS.md`: Enforce primary/supporting role scopes.
- `QUANT_FUTURE_DECISION_ENGINE.md`: Enforces the Three-Option Rule for parameter edits.
- `CURRENT_PROJECT_STATUS.md`: Tracks active blockers and milestones.

---

## 3. Gap Analysis

### A. Concepts Already Exist
- **Role Scopes & Allowed Files**: Existing rules specify which directories agents may open.
- **Three-Option Framework**: Already defined and operational.
- **Paper Mode Safety**: Enforced as the default operating state.

### B. Missing Components (Gaps)
- **Active Registries**: The workspace has no tracking databases (`AUDIT_REGISTRY.json` or `DECISION_REGISTRY.json`).
- **Standardized Audit Schema**: There is no template dictating that audits must link to `run_id` or state a verdict like `EDGE_REAL` / `EDGE_WEAK`.
- **Search Pruning Limits**: Agents have no rule directing them to exclude archived files (`docs/archive/`) from directory walks to conserve tokens.
- **Anti-Loop Metrics**: The 3-polling check and 30-second timeout are missing from `PROJECT_RULES.md`.

---

## 4. Redundant and Conflicting Components

### A. Redundancies (Duplications)
- **Read-First Sequences**: The file sequence to read is repeated across `PROJECT_RULES.md`, `MASTER_AGENT_ROUTER.md`, `.codex/README.md`, and `docs/quant_agent_setup_md/01_QUANT_OPERATING_SYSTEM.md`.
- **Roadmap Definitions**: The 4-phase roadmap is copied verbatim in status reports, maps, and rules.
- **Role Specifications**: Desk roles are defined in `01_QUANT_OPERATING_SYSTEM.md` and duplicated in agent routing tables.

### B. Conflicts
- **Subagent Spawning**:
  - `MASTER_AGENT_ROUTER.md` permits launching multiple subagents concurrently.
  - `PROJECT_OS_V1_DESIGN` blocks runaway subagent spawning to prevent quota depletion.
- **File Modification Rules**:
  - `PROJECT_RULES.md` allows local modifications inside tasks.
  - Governance designs enforce a strict "lockdown" on research tasks, preventing *any* file write, move, or rename without explicit approval.
- **Log Budget vs. Registry Detail**:
  - `PROJECT_RULES.md` enforces a strict VPS disk budget (<150MB/day).
  - The OS registry models require compiling schemas. The storage cost of logging detailed JSONL registries must be reconciled against VPS limits.

---

## 5. Recommended Core Document Changes

To integrate the new Project OS V1 and Research Governance V1 designs, we recommend the following modifications:

### A. Modifications to `PROJECT_RULES.md`
- **Add Section: Active Registries**: Detail the requirement to check `docs/research/AUDIT_REGISTRY.json` and `docs/research/DECISION_REGISTRY.json` before starting work.
- **Add Section: Anti-Loop & Timeouts**: Write the 3-polling and 30s timeout rules directly into the file.
- **Add Section: Search Pruning**: Add rules directing agents to ignore files under `docs/archive/` and `archive/` during read-only scans.

### B. Modifications to `AGENTS.md`
- **Clarify Subagent Boundaries**: State that subagents must not be spawned for research tasks if a quota limit or redundant audit is registered.
- **Lockdown Rules**: Standardize that research-scoped runs are STRICT READ-ONLY.

### C. Modifications to `CURRENT_PROJECT_STATUS.md`
- Integrate the Audit Registry and Decision Registry status as active tracking items under the current project lifecycle.

---

## 6. Single Recommended Next Step

Add the updated, reconciled text sections for `PROJECT_RULES.md` to `docs/core/PROJECT_RULES_RECONCILED.md` in the draft folder to serve as the blueprint for the next operator-approved rules update.
