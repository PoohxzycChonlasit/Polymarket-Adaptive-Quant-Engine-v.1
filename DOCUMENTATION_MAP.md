# Documentation Map

> Last synced: 2026-06-27.
> Purpose: Official map for humans and AI assistants. This is docs-only and does not imply runtime behavior is implemented.

---

## 1. Recommended Reading Order for AI Agents

Before initiating any development, testing, or research task, new AI agents must read these core files in the following sequence to align constraints, avoid scope creep, and check active blockers:

1. **[`CODEX_START_HERE.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CODEX_START_HERE.md)**: Minimal session startup context, safe run commands, and environment diagnostics.
2. **[`PROJECT_RULES.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/PROJECT_RULES.md)**: **Critical Policy**: Token discipline, safety constraints, coding style rules, and workflow boundaries.
3. **[`AGENTS.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/AGENTS.md)**: Codex / Claude / Gemini safety rules, active workspace folders, and role boundaries.
4. **[`MASTER_AGENT_ROUTER.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/MASTER_AGENT_ROUTER.md)**: Directory checklist for selecting primary and supporting agent role files.
5. **[`CURRENT_PROJECT_STATUS.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CURRENT_PROJECT_STATUS.md)**: Current implementation truth, blockers, and next priorities. Read to avoid refactoring unrelated features.
6. **[`PROJECT_STRUCTURE.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/PROJECT_STRUCTURE.md)**: Pointer directory referencing canonical system components.
7. **[`KNOWN_ISSUES.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/KNOWN_ISSUES.md)**: Current live blockers, technical debt, and bugs.
8. **[`FILE_INDEX.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/FILE_INDEX.md)**: Quick map of active runtime files, tests, directories, and legacy folders.
9. **[`DOCUMENTATION_MAP.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/DOCUMENTATION_MAP.md)**: This overview guide mapping documentation folders.
10. **[`QUANT_FUTURE_DECISION_ENGINE.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/QUANT_FUTURE_DECISION_ENGINE.md)**: Exactly 3 future options for research/runtime decisions.

---

## 2. Docs Folder Routing

To prevent clutter in the project root, files are routed into dedicated directories under `docs/`:

| Directory | Purpose / Category | Description |
| :--- | :--- | :--- |
| **[`docs/architecture/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/architecture/)** | System Architecture | Blueprints, engine designs, data flow specifications, schemas, and structure maps. Includes `QUANT_ARCHITECTURE_MASTER_PLAN_001.md`, `AI_AGENT_OPERATING_SYSTEM_DESIGN_001.md`, and Batch 3 extraction designs. 100+ files. |
| **[`docs/audits/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/audits/)** | Forensics & Safety Audits | Point-in-time codebase reviews, pre-commit checklist checks, safety logs, and Batch 3 gate checks (`BATCH_3B1_GATE_CHECK_001.md`, `BATCH_3B2_GATE_CHECK_001.md`). 200+ files. |
| **[`docs/reports/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/reports/)** | Milestone Summaries | Implementation reports, commit reports, runtime validation reports, phase reviews, and architecture audits. Includes `PROJECT_WIDE_REFACTOR_AUDIT_001.md` and all Batch 3 reports. 160+ files. |
| **[`docs/evidence/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/evidence/)** | Validation Evidence | sqlite/shadow telemetry validation checks and dry-run proof logs. |
| **[`docs/research/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/)** | Strategy Research | Quant hypotheses, campaigns, registries, active question locks. Contains `ACTIVE_QUESTION.md`, `AUDIT_REGISTRY.json`, `DECISION_REGISTRY.json`. |
| **[`docs/operations/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/operations/)** | Operations & Deployment | Operating runbooks, VPS deployment configurations, and the **Loop Engineering Playbook** (`LOOP_ENGINEERING_PLAYBOOK_001.md`) — defines autonomous AI workflow mode for eligible task classes. |
| **[`docs/quant_agent_setup_md/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/quant_agent_setup_md/)** | AI Agent Setup | Safety role playbooks (roles 01–29), templates, and setup prompts. Roles 24–29 added 2026-06-26 (Librarian, Data Steward, Handoff, Verification Officer, Runtime Ops, Architecture Governance). |

---

## 3. Historical Evidence Policy & Warning

> [!IMPORTANT]
> **Historical Record Status**: Most files categorized in `docs/audits/`, `docs/reports/`, and `docs/evidence/` represent point-in-time logs confirming that a specific build or commit successfully passed safety checks.
> - **They are NOT active operational specifications or system instructions.**
> - AI agents must never interpret historical audit findings, merged implementation summaries, or completed validations as active rules or configurations.
> - Current operational rules, thresholds, and limits reside exclusively in the root files (e.g., [`PROJECT_RULES.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/PROJECT_RULES.md) and [`AGENTS.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/AGENTS.md)).

---

## 4. Phase B Evidence & Telemetry Routing

Phase B (Shadow Telemetry & Daily Evidence Collection) telemetry artifacts are routed cleanly across `docs/` and `tools/` based on their role:

### A. Active Telemetry Tools (`tools/`)
- [`tools/phase_b_daily_evidence_collector.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/phase_b_daily_evidence_collector.py): Compiles telemetry data for a specific UTC date.
- [`tools/phase_b_daily_report.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/phase_b_daily_report.py): Generates summary metrics, PnL details, and markdown dashboards.
- [`tools/phase_b_snapshot_archiver.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/phase_b_snapshot_archiver.py): Saves immutable dated dashboards and indexes.
- [`tools/phase_b_snapshot_summary.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/phase_b_snapshot_summary.py): Formats rolling metrics summaries.

### B. Validation Evidence (`docs/evidence/`)
- [`docs/evidence/PHASE_B_DAILY_EVIDENCE_COLLECTOR_REAL_DATA_VALIDATION_001.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/evidence/PHASE_B_DAILY_EVIDENCE_COLLECTOR_REAL_DATA_VALIDATION_001.md): Verification run on live Phase B databases.
- [`docs/evidence/SHADOW_TELEMETRY_PHASE_B_BOUNDED_RUNTIME_VALIDATION_001.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/evidence/SHADOW_TELEMETRY_PHASE_B_BOUNDED_RUNTIME_VALIDATION_001.md): Passive paper run confirmation.

### C. Implementation & Commit Reports (`docs/reports/`)
- [`docs/reports/PHASE_B_DAILY_EVIDENCE_COLLECTOR_IMPLEMENTATION_REPORT_001.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/reports/PHASE_B_DAILY_EVIDENCE_COLLECTOR_IMPLEMENTATION_REPORT_001.md): Summary of collector architecture.
- [`docs/reports/PHASE_B_DAILY_EVIDENCE_COLLECTOR_COMMIT_REPORT_001.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/reports/PHASE_B_DAILY_EVIDENCE_COLLECTOR_COMMIT_REPORT_001.md): Commit registry for collector files.
- [`docs/reports/PHASE_B_DAILY_AUTOMATED_REPORT_IMPLEMENTATION_REPORT_001.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/reports/PHASE_B_DAILY_AUTOMATED_REPORT_IMPLEMENTATION_REPORT_001.md): Report generation design.
- [`docs/reports/PHASE_B_DAILY_SNAPSHOT_ARCHIVER_IMPLEMENTATION_REPORT_001.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/reports/PHASE_B_DAILY_SNAPSHOT_ARCHIVER_IMPLEMENTATION_REPORT_001.md): Snapshot persistence system.
- [`docs/reports/SHADOW_TELEMETRY_PHASE_B_IMPLEMENTATION_REPORT_001.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/reports/SHADOW_TELEMETRY_PHASE_B_IMPLEMENTATION_REPORT_001.md) / [`docs/reports/SHADOW_TELEMETRY_PHASE_B_COMMIT_REPORT_001.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/reports/SHADOW_TELEMETRY_PHASE_B_COMMIT_REPORT_001.md): Shadow engine setup.

### D. pre-commit check & Forensic Audits (`docs/audits/`)
- [`docs/audits/PHASE_B_DAILY_EVIDENCE_COLLECTOR_PRE_COMMIT_AUDIT_001.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/audits/PHASE_B_DAILY_EVIDENCE_COLLECTOR_PRE_COMMIT_AUDIT_001.md): Checklist verification log.
- [`docs/audits/SHADOW_TELEMETRY_PHASE_B_PRE_COMMIT_AUDIT_001.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/audits/SHADOW_TELEMETRY_PHASE_B_PRE_COMMIT_AUDIT_001.md) / [`docs/audits/SHADOW_TELEMETRY_PHASE_B_PRE_COMMIT_SCOPE_AUDIT_001.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/audits/SHADOW_TELEMETRY_PHASE_B_PRE_COMMIT_SCOPE_AUDIT_001.md): Scope constraints confirmation.
- [`docs/audits/SHADOW_TELEMETRY_PHASE_B_PRE_IMPLEMENTATION_AUDIT_001.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/audits/SHADOW_TELEMETRY_PHASE_B_PRE_IMPLEMENTATION_AUDIT_001.md): Pre-implementation risk preflight.
- [`docs/audits/SHADOW_TELEMETRY_PHASE_B_ENABLE_READINESS_AUDIT_001.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/audits/SHADOW_TELEMETRY_PHASE_B_ENABLE_READINESS_AUDIT_001.md): Readiness sign-off check.

---

## 5. Research & Governance Layer

This layer coordinates active research campaigns, limits parameter drift, and defines the authority bounds of all quant audits.

| File | Purpose |
| :--- | :--- |
| **[`docs/research/ACTIVE_QUESTION.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/ACTIVE_QUESTION.md)** | **Read First**: Tracks the single active question that blocks code/sizer/strategy changes. |
| **[`docs/research/AUDIT_REGISTRY.json`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/AUDIT_REGISTRY.json)** | **Read Second**: Registry of verified mathematical and pipeline audits to prevent duplicate investigations. |
| **[`docs/research/DECISION_REGISTRY.json`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/DECISION_REGISTRY.json)** | **Read Third**: Registry of proposed and approved parameter, model, and sizer changes. |
| **[`docs/research/RESEARCH_AUTHORITY_MAP_V2.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/RESEARCH_AUTHORITY_MAP_V2.md)** | **Read Fourth**: Maps authority level, limitations, allowed and forbidden uses for past audits. |
| **[`docs/research/GOVERNANCE_STARTUP_SEQUENCE.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/GOVERNANCE_STARTUP_SEQUENCE.md)** | Startup check checklist to align assistant tasks. |

---

## 6. AI Agent Workflow Harness

Located in `.codex/`. Reusable prompts, checklists, and templates to guide AI agent sessions. These are instructions and guidelines, not active code.

| File | Purpose |
| :--- | :--- |
| **[`.codex/README.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.codex/README.md)** | Harness overview, safety boundaries, and skill selections. |
| **[`.codex/skills/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.codex/skills/)** | Guidance skills (no-entry root cause, regime analysis, replay diagnostics, risk budget checks). |
| **[`.codex/security/AI_AGENT_SECURITY_CHECKLIST.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.codex/security/AI_AGENT_SECURITY_CHECKLIST.md)** | Security checklist for secrets, wallet safety, and runtime separation. |
| **[`research/session_memory_template.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/research/session_memory_template.md)** | Handoff session template to maintain memory. |
| **[`research/daily/README.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/research/daily/README.md)** | Daily research diary workflow. |

---

## 6b. Batch 3 Trader Refactor Status (2026-06-27)

`polymarket/trader.py` is being decomposed via proxy delegation into orchestration helpers:

| Batch | Commit | Extracted to | Status |
| :--- | :--- | :--- | :--- |
| Batch 1 | `e76581fb` | `polymarket/trader_presentation.py` — `TraderPresentationHelper` | COMPLETE |
| Batch 2A | `c3b2bd2` | `polymarket/orchestration/trader_lifecycle.py` — `TraderLifecycleHelper` | COMPLETE |
| Batch 3A | `3c24111` | `polymarket/orchestration/trader_observability.py` (display state) — `TraderObservabilityHelper` | COMPLETE |
| Batch 3B-1 | `a491820` | `trader_observability.py` +8 orderbook refresh fields +2 methods | COMPLETE |
| Batch 3B-2 | `381cbc4` | `trader_observability.py` +5 cadence fields +3 methods; Presentation dedup fix in `6872a07` | COMPLETE |
| Batch 3C+ | TBD | Remaining lifecycle observability payload assembly | PLANNED |

`trader.py` is at 12,824 lines (architecture master plan target: ≤ 1,000 lines). See `docs/architecture/QUANT_ARCHITECTURE_MASTER_PLAN_001.md` for full decomposition roadmap.

---

## 7. Current Phase Roadmap

1. **Phase 1**: Regime classification, probability scoring, indicator evidence, and observability only.
2. **Phase 2**: Paper-only inventory replay research, reload/unload analysis, opportunity decay, and MFE/MAE tracking.
3. **Phase 3**: Bounded multi-price inventory engine design with max inventory cap, max risk cap, stop loss, forced exit, and no martingale.
4. **Phase 4**: Continuous probabilistic inventory trading only after paper evidence supports it.
