# PROJECT_CENSUS_AUDIT_001

## 1. Executive Summary

This audit establishes a complete manifest of files in the repository `c:\quant\Polymarket-Adaptive-Quant-Engine-v.1` to identify the true canonical documents and locate duplicate or obsolete files before any reorganization. 

- **Total Files**: 3,145 (excluding virtual environments, git histories, and node dependencies).
- **Markdown Files**: 487 (including 13 workspace-specific `.codex/` files).
- **Core Findings**:
  - The repository has an exceptionally rich documentation system (Agent Playbooks, Research Audits, Governance Specifications).
  - Safety constraints during past "docs-only migrations" prevented file deletions. This resulted in copy-paste duplicate files remaining in the parent `docs/research/` directory while their twins exist in subdirectories (`path_truth/`, `performance/`, `runtime_health/`).
  - There are zero `.yaml` or `.yml` files in the repository.
  - The overall documentation health is rated **GOOD**. Reorganizing the documentation layout and deleting duplicated copies will easily elevate it to **EXCELLENT**.

---

## 2. Repository Statistics

| Metric | Value | Notes |
|---|---|---|
| **Total Files** | **3,145** | Excluding `.venv`, `.git`, and `node_modules` |
| **Total Folders** | **163** | Excluding `.venv`, `.git`, and `node_modules` |
| **Python Files (.py)** | **309** | Core strategy, CLOB client, utilities, and tests |
| **Markdown Files (.md)** | **487** | Rules, designs, role playbooks, and research logs |
| **JSON Files (.json)** | **225** | Configs, package manifests, and test fixtures |
| **JSONL Files (.jsonl)** | **331** | Real-time scan and trade database files |
| **CSV Files (.csv)** | **262** | Scan records and transaction backups |
| **Log Files (.log)** | **264** | Execution console logs |
| **Numbered Logs (.1 to .5)** | **615** | Backed up log files |
| **YAML Files (.yaml / .yml)** | **0** | No yaml files detected |
| **Other Files** | **52** | TSX, TS, CSS, SVG, HTML, etc. |

### Top Folders by File Count (excluding dependencies)
1. `logs/`: 864 files
2. `runtime/`: 862 files
3. `docs/`: 387 files
4. `tests/`: 126 files (Note: 492 total files match the `tests` path name due to sub-fixtures)
5. `tools/`: 66 files

---

## 3. Markdown Inventory

The 487 markdown files are categorized as follows:

### A. CORE (9 Documents)
Key documents defining entry points, active parameters, and runtime security rules:
- [CODEX_START_HERE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CODEX_START_HERE.md)
- [PROJECT_RULES.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/PROJECT_RULES.md)
- [AGENTS.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/AGENTS.md)
- [MASTER_AGENT_ROUTER.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/MASTER_AGENT_ROUTER.md)
- [FILE_INDEX.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/FILE_INDEX.md)
- [DOCUMENTATION_MAP.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/DOCUMENTATION_MAP.md)
- [CURRENT_PROJECT_STATUS.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CURRENT_PROJECT_STATUS.md)
- [docs/KNOWN_ISSUES.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/KNOWN_ISSUES.md) (Forwarded from root `KNOWN_ISSUES.md`)
- [runtime/research_state/latest_research_state.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/runtime/research_state/latest_research_state.md)

### B. ARCHITECTURE (35 Documents)
Specifications for future state engines, plans, and role playbooks:
- [docs/PROJECT_STRUCTURE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/PROJECT_STRUCTURE.md) (Forwarded from root `PROJECT_STRUCTURE.md`)
- [QUANT_FUTURE_DECISION_ENGINE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/QUANT_FUTURE_DECISION_ENGINE.md)
- [QUANT_LIFECYCLE_INVENTORY_ENGINE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/QUANT_LIFECYCLE_INVENTORY_ENGINE.md)
- [BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md)
- [QUANT_REGIME_PROBABILITY_ENGINE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/QUANT_REGIME_PROBABILITY_ENGINE.md)
- [INVENTORY_REPLAY_RESEARCH_PLAN.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/INVENTORY_REPLAY_RESEARCH_PLAN.md)
- [MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md)
- [README.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/README.md)
- Agent Roles (23 files under `docs/quant_agent_setup_md/roles/`)
- Agent Master Contexts (3 files under `docs/quant_agent_setup_md/`)

### C. OPERATIONS (11 Documents)
Runbooks, checks, and cleanup parameters:
- [docs/PAPER_TRADING_RUNBOOK.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/PAPER_TRADING_RUNBOOK.md)
- [docs/OBSERVABILITY_PLAN.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/OBSERVABILITY_PLAN.md)
- [docs/DOC_SYNC_PROCEDURE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/DOC_SYNC_PROCEDURE.md)
- [docs/PROJECT_CLEANUP_REPORT.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/PROJECT_CLEANUP_REPORT.md)
- [overnight_maturity_check_2026-05-19.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/overnight_maturity_check_2026-05-19.md)
- [repo_canonical_check_2026-05-19.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/repo_canonical_check_2026-05-19.md)
- [runtime_clean_validation_2026-05-19.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/runtime_clean_validation_2026-05-19.md)
- [stop_loss_concentration_diagnosis_2026-05-19.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/stop_loss_concentration_diagnosis_2026-05-19.md)

### D. RESEARCH (357 Documents)
All research sessions, checklists, telemetry analyses, and watchlists located under:
- `docs/research/` (including subdirectories `frontiers/`, `discovery/`, `executable_truth/`, `path_truth/`, `performance/`, `runtime_health/`, `session_edge/`, `sessions/`, `watchlists/`, `research_memory/`)
- Historical audits in root: `DELTA_EXTREME_GATE_FORENSIC_AUDIT.md`, `EVIDENCE_QUALITY_AUDIT.md`, `FORWARD_VALIDATION_PROTOCOL_AUDIT.md`, `HYPOTHESIS_LEDGER_RECONSTRUCTION.md`, `RISK_PLAN_ZERO_FORENSIC_AUDIT_001.md`, `SELECTION_BIAS_AUDIT.md`

### E. HISTORICAL (10 Documents)
Archive setup templates and old prompts inside `archive/legacy/` and `docs/quant_agent_setup_md/templates/`.

---

## 4. Canonical Documents

| Document | Canonical Path | Status |
|---|---|---|
| **CURRENT_PROJECT_STATUS** | `CURRENT_PROJECT_STATUS.md` | Canonical |
| **PROJECT_RULES** | `PROJECT_RULES.md` | Canonical |
| **AGENTS** | `AGENTS.md` | Canonical |
| **MASTER_AGENT_ROUTER** | `MASTER_AGENT_ROUTER.md` | Canonical |
| **FILE_INDEX** | `FILE_INDEX.md` | Canonical |
| **DOCUMENTATION_MAP** | `DOCUMENTATION_MAP.md` | Canonical |
| **PROJECT_STRUCTURE** | `docs/PROJECT_STRUCTURE.md` | Canonical (root is a stub pointer) |
| **KNOWN_ISSUES** | `docs/KNOWN_ISSUES.md` | Canonical (root is a stub pointer) |
| **RESEARCH_STATE** | `runtime/research_state/latest_research_state.md` | Canonical |
| **GOVERNANCE_HUB** | `docs/research/GOVERNANCE_NAVIGATION_HUB.md` | Canonical |

---

## 5. Duplicate Analysis

### A. Forwarding Duplicates
- `PROJECT_STRUCTURE.md` (root, 671 bytes) pointing to `docs/PROJECT_STRUCTURE.md`.
- `KNOWN_ISSUES.md` (root, 267 bytes) pointing to `docs/KNOWN_ISSUES.md`.

### B. Migration Duplicates
The following files exist in `docs/research/` and also in subdirectories. The subdirectory versions are the target locations, leaving parent files as superseded duplicates due to "no delete" migration rules:

| Filename | Parent Folder Copy (Duplicate) | Subfolder Target Copy (Canonical) |
|---|---|---|
| `path_truth_checkpoint_validation.md` | `docs/research/` | `docs/research/path_truth/` |
| `path_truth_field_coverage_gap_audit.md` | `docs/research/` | `docs/research/path_truth/` |
| `path_truth_implementation_spec.md` | `docs/research/` | `docs/research/path_truth/` |
| `path_truth_multiday_coverage_monitor.md` | `docs/research/` | `docs/research/path_truth/` |
| `path_truth_observability_design.md` | `docs/research/` | `docs/research/path_truth/` |
| `replay_join_key_contract.md` | `docs/research/` | `docs/research/path_truth/` |
| `research_cockpit_frontend_blueprint_v1.md` | `docs/research/` | `docs/research/performance/` |
| `research_cockpit_ui_redesign_v1.md` | `docs/research/` | `docs/research/performance/` |
| `research_cockpit_v2_architecture.md` | `docs/research/` | `docs/research/performance/` |
| `research_cockpit_v2_roadmap.md` | `docs/research/` | `docs/research/performance/` |
| `telegram_operator_console_design.md` | `docs/research/` | `docs/research/performance/` |
| `terminal_ui_v2_redesign.md` | `docs/research/` | `docs/research/performance/` |
| `telegram_route_telemetry_design.md` | `docs/research/` | `docs/research/runtime_health/` |
| `telegram_routing_telemetry_audit.md` | `docs/research/` | `docs/research/runtime_health/` |
| `telegram_telemetry_validation.md` | `docs/research/` | `docs/research/runtime_health/` |

### C. Runtime Archive Duplicates
- `runtime/reports/` vs `docs/research/sessions/2026-05-18/runtime_reports/`: Twin copies of post-run markdown audits.
- `runtime/backup_untracked/` vs `docs/research/frontiers/` / `docs/research/discovery/`: Duplicate spec files.

---

## 6. Governance Analysis

- **RESEARCH_GOVERNANCE**: **PARTIAL**
  - *Why*: Research pathways (`GOVERNANCE_NAVIGATION_HUB.md`) and specs are present. However, there is no code separation, allowing research notes to be scattered inside active workspace paths.
- **DOCUMENTATION_GOVERNANCE**: **PARTIAL**
  - *Why*: Synchronizations are structured (`DOC_SYNC_PROCEDURE.md`), but safety rules blocking file deletions led to multiple duplicates.
- **AGENT_GOVERNANCE**: **PRESENT**
  - *Why*: The role routing in `AGENTS.md` and `MASTER_AGENT_ROUTER.md` enforces strict boundary rules.
- **TASK_GOVERNANCE**: **PARTIAL**
  - *Why*: Templates exist, but task histories are scattered across root and `docs/`.
- **DECISION_GOVERNANCE**: **PRESENT**
  - *Why*: Every major sizing/parameter decision requires the Three-Option protocol (`QUANT_FUTURE_DECISION_ENGINE.md`).
- **MEMORY_GOVERNANCE**: **PRESENT**
  - *Why*: Structured templates under `docs/research_memory/` and `.codex/` enforce logging of run findings.

---

## 7. Cleanup Opportunities

- **Safe Archive Candidates** (Move to `docs/archive/`):
  - Root pointer stubs: `PROJECT_STRUCTURE.md`, `KNOWN_ISSUES.md`.
  - Outdated prompts: `CODEX_START_PROMPT.md`, `CHATGPT_PROJECT_START_PROMPT.md`.
  - Parent copies of migrated path truth, performance, and runtime health files under `docs/research/`.
- **Safe Merge Candidates**:
  - Merge `KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md` into `docs/KNOWN_ISSUES.md`.
  - Merge `DOC_TRUTH_RECONCILIATION_2026-05-14.md` into `DOCUMENTATION_MAP.md`.
- **High Risk Files (Do NOT Touch)**:
  - `.env`, `config/settings.py` (secrets, default configurations).
  - `polymarket/trader.py`, `utils/risk_manager.py` (main loop, risk sizing logic).
  - `polymarket/order_intent.py` (order verification constraints).

---

## 8. Proposed Structure

We propose restructuring the `docs/` folder into four unified branches:

```text
docs/
├── core/                  # Canonical rules, entrypoints, and routers
│   ├── CODEX_START_HERE.md, PROJECT_RULES.md, AGENTS.md, MASTER_AGENT_ROUTER.md
│   ├── FILE_INDEX.md, DOCUMENTATION_MAP.md, KNOWN_ISSUES.md
│
├── architecture/          # Design specifications and technical roadmaps
│   ├── PROJECT_STRUCTURE.md, QUANT_FUTURE_DECISION_ENGINE.md
│   ├── QUANT_LIFECYCLE_INVENTORY_ENGINE.md, BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md
│   └── agent_setup/       # Roles and playbooks (01-23 roles)
│
├── research/              # Active research, audits, and hypotheses
│   ├── GOVERNANCE_NAVIGATION_HUB.md, INFRASTRUCTURE_GOVERNANCE_MAP.md
│   └── frontiers/, discovery/, path_truth/, executable_truth/, sessions/
│
├── operations/            # Runbooks and runtime monitoring logs
│   ├── PAPER_TRADING_RUNBOOK.md, OBSERVABILITY_PLAN.md
│   └── DOC_SYNC_PROCEDURE.md, PROJECT_CLEANUP_REPORT.md
│
└── archive/               # Historical and retired documentation
    └── legacy/
```

---

## 9. Top 20 Most Important Documents

1. [CODEX_START_HERE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CODEX_START_HERE.md) - Project gateway.
2. [PROJECT_RULES.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/PROJECT_RULES.md) - Sizing/safety rules.
3. [AGENTS.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/AGENTS.md) - LLM agent parameters.
4. [MASTER_AGENT_ROUTER.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/MASTER_AGENT_ROUTER.md) - Task mapping.
5. [DOCUMENTATION_MAP.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/DOCUMENTATION_MAP.md) - Reading order.
6. [FILE_INDEX.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/FILE_INDEX.md) - Directory of logs/files.
7. [CURRENT_PROJECT_STATUS.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CURRENT_PROJECT_STATUS.md) - Active blockers tracker.
8. [docs/PROJECT_STRUCTURE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/PROJECT_STRUCTURE.md) - Runtime folder design.
9. [docs/KNOWN_ISSUES.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/KNOWN_ISSUES.md) - Live execution blockers map.
10. [QUANT_LIFECYCLE_INVENTORY_ENGINE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/QUANT_LIFECYCLE_INVENTORY_ENGINE.md) - Core inventory system spec.
11. [QUANT_FUTURE_DECISION_ENGINE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/QUANT_FUTURE_DECISION_ENGINE.md) - Three-option rules.
12. [docs/research/GOVERNANCE_NAVIGATION_HUB.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/GOVERNANCE_NAVIGATION_HUB.md) - Promotion gates.
13. [runtime/research_state/latest_research_state.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/runtime/research_state/latest_research_state.md) - Latest run summary.
14. [docs/PAPER_TRADING_RUNBOOK.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/PAPER_TRADING_RUNBOOK.md) - Paper trading monitor instructions.
15. [docs/OBSERVABILITY_PLAN.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/OBSERVABILITY_PLAN.md) - Telemetry specs.
16. [roles/01_PROJECT_MANAGER_AGENT.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/quant_agent_setup_md/roles/01_PROJECT_MANAGER_AGENT.md) - PM rules.
17. [roles/03_RISK_MANAGER_AGENT.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/quant_agent_setup_md/roles/03_RISK_MANAGER_AGENT.md) - Risk rules.
18. [roles/10_BACKTEST_REPLAY_AGENT.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/quant_agent_setup_md/roles/10_BACKTEST_REPLAY_AGENT.md) - Evaluation rules.
19. [BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md) - Inventory plan.
20. [docs/research/INFRASTRUCTURE_GOVERNANCE_MAP.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/INFRASTRUCTURE_GOVERNANCE_MAP.md) - Archive guidelines.

---

## 10. Final Verdict

**PROJECT_DOCUMENTATION_HEALTH = GOOD**

*Rationale*: The documentation quality, coverage, and detail are outstanding, representing a highly disciplined quantitative framework. It falls short of "EXCELLENT" only because of the accumulation of duplicate markdown files caused by past no-delete migration safety rules.
