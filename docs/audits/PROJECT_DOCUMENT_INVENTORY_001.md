# PROJECT_DOCUMENT_INVENTORY_001

## 1. Canonical Documents (Source of Truth)

These documents are the top-level files governing AI context, coding behavior, active parameters, and current blockers:

| Path | Purpose | Owner | Status | Dependencies | Recommended Action |
|---|---|---|---|---|---|
| [CODEX_START_HERE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CODEX_START_HERE.md) | Initial developer workspace setup and entry point. | Project Manager | Canonical | None | Keep at root. |
| [PROJECT_RULES.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/PROJECT_RULES.md) | Safety limits, no-martingale sizer rules, and VPS budgets. | Risk Manager | Canonical | None | Keep at root. |
| [AGENTS.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/AGENTS.md) | System prompt settings loaded for agent roles. | PM / Architect | Canonical | Role docs | Keep at root. |
| [MASTER_AGENT_ROUTER.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/MASTER_AGENT_ROUTER.md) | Maps coding/research tasks to primary/supporting roles. | Project Manager | Canonical | `AGENTS.md` | Keep at root. |
| [FILE_INDEX.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/FILE_INDEX.md) | Index of all codebase directories and logs. | Document Agent | Canonical | None | Keep at root. |
| [DOCUMENTATION_MAP.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/DOCUMENTATION_MAP.md) | Reading order roadmap for developers. | Document Agent | Canonical | None | Keep at root. |
| [CURRENT_PROJECT_STATUS.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CURRENT_PROJECT_STATUS.md) | Live blockers list, pipeline milestones, and active tasks. | Project Manager | Canonical | None | Update daily at root. |
| [docs/PROJECT_STRUCTURE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/PROJECT_STRUCTURE.md) | Canonical layout of folder structure and log scopes. | Code Architect | Canonical | Root stub | Keep in `docs/`. |
| [docs/KNOWN_ISSUES.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/KNOWN_ISSUES.md) | Technical debt and active trade pipeline blockers. | PM / Architect | Canonical | Root stub | Keep in `docs/`. |
| [runtime/research_state/latest_research_state.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/runtime/research_state/latest_research_state.md) | Compact state of the latest runs and evidence quality. | Research Agent | Canonical | Log files | Update after runs. |
| [docs/research/GOVERNANCE_NAVIGATION_HUB.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/GOVERNANCE_NAVIGATION_HUB.md) | Promotion gates, hierarchy of truth, and review rules. | PM / Architect | Canonical | None | Keep in `docs/research/`. |

---

## 2. Active Documents (Regularly Updated / Operative)

These files provide instructions, plans, or telemetry logs updated during active development and analysis:

| Group / Path | Purpose | Owner | Status | Dependencies | Recommended Action |
|---|---|---|---|---|---|
| **Agent Roles (23 files)** `docs/quant_agent_setup_md/roles/*.md` | Define guidelines, allowed files, and boundaries for each agent role. | Project Manager | Active | `AGENTS.md` | Keep. |
| [docs/PAPER_TRADING_RUNBOOK.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/PAPER_TRADING_RUNBOOK.md) | Run instructions and evaluation scripts. | Observability | Active | `main.py` | Keep. |
| [docs/OBSERVABILITY_PLAN.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/OBSERVABILITY_PLAN.md) | Logging, Telegram notification, and dashboard plans. | Observability | Active | None | Keep. |
| [QUANT_FUTURE_DECISION_ENGINE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/QUANT_FUTURE_DECISION_ENGINE.md) | Future options analysis framework (Three-Option rule). | Research Agent | Active | None | Keep at root. |
| [QUANT_LIFECYCLE_INVENTORY_ENGINE.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/QUANT_LIFECYCLE_INVENTORY_ENGINE.md) | Spec for future inventory states (OPENING_SCAN, etc.). | Research Agent | Active | None | Keep at root. |
| **Research Memory (17 files)** `docs/research_memory/**/*.md` | Records of daily parsed JSONL run findings. | Research Agent | Active | JSONL logs | Keep in memory folder. |

---

## 3. Reference Documents (Static / Informational Guides)

| Path | Purpose | Owner | Status | Dependencies | Recommended Action |
|---|---|---|---|---|---|
| [README.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/README.md) | Overview of codebase commands and installations. | Document Agent | Reference | None | Keep. |
| [docs/quant_agent_setup_md/00_MASTER_CONTEXT.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/quant_agent_setup_md/00_MASTER_CONTEXT.md) | Agent environment setup coordinates. | Code Architect | Reference | None | Keep. |
| [docs/quant_agent_setup_md/01_QUANT_OPERATING_SYSTEM.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/quant_agent_setup_md/01_QUANT_OPERATING_SYSTEM.md) | Desk roles and the daily loops protocol. | Code Architect | Reference | None | Keep. |
| [docs/quant_agent_setup_md/02_AGENT_INDEX.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/quant_agent_setup_md/02_AGENT_INDEX.md) | Index of active agent role folders. | Code Architect | Reference | None | Keep. |
| [docs/quant_agent_setup_md/playbooks/CODEX_WORKFLOW.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/quant_agent_setup_md/playbooks/CODEX_WORKFLOW.md) | Coding guidelines for Codex tasks. | Code Architect | Reference | None | Keep. |

---

## 4. Duplicate Documents

The following files represent exact or near duplicates due to "no delete" safety constraints applied during past migration batches:

| File Name | Location 1 (Redundant Copy) | Location 2 (Canonical Copy) | Purpose | Recommended Action |
|---|---|---|---|---|
| `PROJECT_STRUCTURE.md` | Root | `docs/PROJECT_STRUCTURE.md` | Stubs forwarding to canonical files. | Delete root stub once rules point to `docs/` directly. |
| `KNOWN_ISSUES.md` | Root | `docs/KNOWN_ISSUES.md` | Stubs forwarding to canonical files. | Delete root stub once rules point to `docs/` directly. |
| **Path Truth Specs (6 files)** | `docs/research/` | `docs/research/path_truth/` | Mapped specifications (e.g. `path_truth_observability_design.md`). | Delete parent copies in `docs/research/`. |
| **Performance Specs (6 files)** | `docs/research/` | `docs/research/performance/` | Redesign blueprints (e.g. `terminal_ui_v2_redesign.md`). | Delete parent copies in `docs/research/`. |
| **Telemetry Specs (3 files)** | `docs/research/` | `docs/research/runtime_health/` | Telemetry designs (e.g. `telegram_routing_telemetry_audit.md`). | Delete parent copies in `docs/research/`. |
| **Post-Run Audits (3 files)** | `runtime/reports/` | `docs/research/sessions/2026-05-18/runtime_reports/` | Duplicated post-run summaries. | Delete files in `runtime/reports/`. |
| **Drift Specs (2 files)** | `runtime/backup_untracked/` | `docs/research/discovery/` | Spec sheets. | Delete files in `runtime/backup_untracked/`. |
| **Checklist Specs (4 files)** | `runtime/backup_untracked/` | `docs/research/frontiers/` | Operational specs (e.g. `N70_PRELAUNCH_CHECKLIST.md`). | Delete files in `runtime/backup_untracked/`. |

---

## 5. Obsolete Documents

These files contain outdated templates or rules superseded by newer config folders:

| Path | Purpose | Owner | Status | Recommended Action |
|---|---|---|---|---|
| `CODEX_START_PROMPT.md` (root) | Startup instructions for Codex. | PM | Obsolete | Delete (superseded by `.codex/prompts/`). |
| `CHATGPT_PROJECT_START_PROMPT.md` (root) | Startup instructions for ChatGPT. | PM | Obsolete | Delete (superseded by `.codex/prompts/`). |
| `docs/quant_agent_setup_md/templates/*.md` (3 files) | Old templates. | PM | Obsolete | Archive. |
| `archive/legacy/` (10 files) | Retired prompt packs. | PM | Historical | Keep in archive. |

---

## 6. Missing Documents

The following governance structures are missing from the repository:
1. **Audit Registry (`docs/research/AUDIT_REGISTRY.json`)**: An active database tracking all run audits, verdicts, and target date scopes to prevent duplicate investigations.
2. **Decision Registry (`docs/research/DECISION_REGISTRY.json`)**: An active database recording configuration changes and parameter approvals.
3. **Subagent Spawning Limits**: Rules enforcing constraints against runaway subagent calls (needs to be written in `PROJECT_RULES.md`).
4. **Search Pruning Instructions**: Rules preventing agents from scanning `docs/archive/` (needs to be written in `PROJECT_RULES.md`).

---

## 7. Recommended Documentation Structure

We recommend organizing the documentation into five clean folders under `docs/`, removing root-level stubs and duplicate parent copies:

```text
docs/
├── core/                  # Canonical entry points and rules
│   ├── CODEX_START_HERE.md
│   ├── PROJECT_RULES.md
│   ├── AGENTS.md
│   ├── MASTER_AGENT_ROUTER.md
│   ├── FILE_INDEX.md
│   ├── DOCUMENTATION_MAP.md
│   └── KNOWN_ISSUES.md
│
├── architecture/          # blue prints and roadmaps
│   ├── PROJECT_STRUCTURE.md
│   ├── QUANT_FUTURE_DECISION_ENGINE.md
│   ├── QUANT_LIFECYCLE_INVENTORY_ENGINE.md
│   ├── BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md
│   ├── QUANT_REGIME_PROBABILITY_ENGINE.md
│   ├── INVENTORY_REPLAY_RESEARCH_PLAN.md
│   ├── MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md
│   └── agent_setup/ (roles/)
│
├── research/              # Active research registries and logs
│   ├── GOVERNANCE_NAVIGATION_HUB.md
│   ├── INFRASTRUCTURE_GOVERNANCE_MAP.md
│   ├── AUDIT_REGISTRY.json
│   ├── DECISION_REGISTRY.json
│   └── frontiers/, discovery/, path_truth/, executable_truth/
│
├── operations/            # Active trading runbooks and blueprints
│   ├── PAPER_TRADING_RUNBOOK.md
│   └── OBSERVABILITY_PLAN.md
│
└── archive/               # Historical logs, run audits, and legacy templates
    └── legacy/
```

---

## 8. Single Recommended Next Step

Add the empty JSON templates for `docs/research/AUDIT_REGISTRY.json` and `docs/research/DECISION_REGISTRY.json` to the repository to initialize the tracking substrates.
