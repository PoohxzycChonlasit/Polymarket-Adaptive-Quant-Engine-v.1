# PROJECT_OS_V1_IMPLEMENTATION_ROADMAP

## 1. Executive Summary
This document converts all completed Project OS V1 and Research Governance V1 work into a structured **Implementation Roadmap**. It sequences the rollout of the registry infrastructure, file reorganization, rules reconciliation, and context optimization.

- **Phase 1 (Critical)**: Establishes tracking substrates (`AUDIT_REGISTRY.json`, `DECISION_REGISTRY.json`) and reconciles `PROJECT_RULES.md` and `AGENTS.md`.
- **Phase 2 (Important)**: Executes folder reorganization, prunes duplicate parent copies in `docs/research/`, and merges redundant known issue lists.
- **Phase 3 (Optional)**: Integrates dashboard registry counters and automates archive compression scripts.

---

## 2. Implementation Readiness

The repository is currently **Design Ready**. All schemas, workflows, and rule adjustments have been validated and reconciled in:
- `PROJECT_OS_V1_DESIGN`
- `RESEARCH_GOVERNANCE_V1_DESIGN`
- `CANONICAL_DOCUMENT_RECONCILIATION_001`
- `PROJECT_DOCUMENT_INVENTORY_001`

### What is Already Decided
- Standard schemas for the Audit Registry and Decision Registry.
- Core rules for search pruning (excluding `docs/archive/` from scans).
- Core metrics for anti-loop controls (3 polling checks, 30s timeout).
- Canonical directory mapping under `docs/`.

### What is Still Undecided
- Automated git hooks to block subagent loops (currently manual agent-level enforcement).
- The exact retention duration window for raw `.jsonl` files (currently hot/warm definitions are conceptual only).

### What Should NEVER Be Implemented
- Autonomous parameter updates (the bot must never alter risk sizing or trade flags automatically based on registry results; all updates require explicit operator write-in).
- Destructive auto-deletions of raw evidence (all deletions require manual operator commands).

---

## 3. Priority Roadmap

### PHASE 1: Critical (Registry Setup & Rules Reconciliation)
- **Objective**: Establish registries to prevent duplicate runs and update agent rules for anti-loop/search pruning.
- **Files Affected**:
  - `[NEW]` [AUDIT_REGISTRY.json](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/AUDIT_REGISTRY.json)
  - `[NEW]` [DECISION_REGISTRY.json](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/DECISION_REGISTRY.json)
  - `[MODIFY]` [PROJECT_RULES.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/PROJECT_RULES.md) (Anti-loop and search pruning additions)
  - `[MODIFY]` [AGENTS.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/AGENTS.md) (Exclude `docs/archive/` and force registry check)
- **Risk Level**: **LOW**. Does not affect Python runtime files.
- **Expected Benefit**: Immediately stops subagent loop/quota exhaustion and reduces agent context scanning.
- **Approval Required**: Operator approval on modified rules content.

---

### PHASE 2: Important (Folder Reorganization & Duplicate Pruning)
- **Objective**: Clean the workspace structure to eliminate redundant context files.
- **Files Affected**:
  - `[DELETE]` 15 duplicate parent files in `docs/research/`.
  - `[DELETE]` Root pointer stubs `PROJECT_STRUCTURE.md` and `KNOWN_ISSUES.md`.
  - `[MODIFY]` Move active rules, routers, and structure maps to `docs/core/` and `docs/architecture/` respectively.
  - `[MODIFY]` Merge `KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md` and `docs/KNOWN_ISSUES.md`.
- **Risk Level**: **MEDIUM**. Requires updating all relative markdown references and file-index lookups. Incorrect updates could break agent navigation.
- **Expected Benefit**: Eliminates file redundancy and reduces token context size during file walks.
- **Approval Required**: Operator approval for document deletion and folder move commands.

---

### PHASE 3: Optional (Archive Automation & Dashboard Integrations)
- **Objective**: Improve operator visibility and automate compression pipelines.
- **Files Affected**:
  - `[NEW]` `scripts/compress_logs.py` (compression engine for logs/raw evidence).
  - `[MODIFY]` `main.py` / Dashboard files (integrate lightweight seen/pending registry counts).
- **Risk Level**: **LOW**. Executed as separate offline utilities.
- **Expected Benefit**: Saves disk space on VPS and provides operator dashboard metrics.
- **Approval Required**: Standard PM code review and testing validation.

---

## 4. Recommended First Implementation

We recommend launching **Phase 1 (Critical)** immediately. 
The concrete step is:
1. Initialize the empty registries `docs/research/AUDIT_REGISTRY.json` and `docs/research/DECISION_REGISTRY.json`.
2. Append the reconciled rules for anti-loop controls, registry checks, and search pruning directly to `PROJECT_RULES.md` and `AGENTS.md`.
