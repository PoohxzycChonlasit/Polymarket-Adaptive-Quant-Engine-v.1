# GOVERNANCE_V1_CLOSURE_AUDIT_001

## 1. Governance Chain Review

This section verifies the internal consistency of the startup and governance reference chain:

```text
CODEX_START_HERE.md
  ↓
CURRENT_PROJECT_STATUS.md
  ↓
DOCUMENTATION_MAP.md
  ↓
FILE_INDEX.md
  ↓
ACTIVE_QUESTION.md
  ↓
AUDIT_REGISTRY.json
  ↓
DECISION_REGISTRY.json
  ↓
RESEARCH_AUTHORITY_MAP_V2.md
  ↓
GOVERNANCE_STARTUP_SEQUENCE.md
```

### Chain Integrity Assessment

1. **Can a fresh AI session discover the Active Question without operator help?**
   - **Yes**. A fresh AI session is instructed to read `CURRENT_PROJECT_STATUS.md` and `FILE_INDEX.md` immediately in `CODEX_START_HERE.md`. `CURRENT_PROJECT_STATUS.md` lists the current active question `LOW_PRICE_TRUTH_RESOLUTION_001` in the `## 1.5 Governance Status` section. `FILE_INDEX.md` and `DOCUMENTATION_MAP.md` direct the assistant directly to `docs/research/ACTIVE_QUESTION.md` where the blocking constraints are fully defined.

2. **Can a fresh AI session discover existing audits before launching a duplicate audit?**
   - **Yes**. The files `PROJECT_RULES.md` and `AGENTS.md` explicitly mandate checking `docs/research/AUDIT_REGISTRY.json` before starting any new research or audits. The registry is mapped inside `FILE_INDEX.md` and `DOCUMENTATION_MAP.md` under dedicated governance sections.

3. **Can a fresh AI session discover existing decisions before proposing changes?**
   - **Yes**. `docs/research/DECISION_REGISTRY.json` is listed in all key indices and is explicitly evaluated in Step 3 of the `GOVERNANCE_STARTUP_SEQUENCE.md`.

4. **Are there broken links?**
   - **No**. All links and file path references point to existing valid files inside the workspace root or `docs/research/`.

5. **Are there circular dependencies?**
   - **No**. The dependency flow is unidirectional, beginning with high-level entry points (`CODEX_START_HERE.md`), proceeding through project metrics (`CURRENT_PROJECT_STATUS.md`), indexing (`FILE_INDEX.md`), active blocks (`ACTIVE_QUESTION.md`), and historical registries.

6. **Are there startup gaps?**
   - **Yes**. The newly integrated `docs/research/GOVERNANCE_STARTUP_SEQUENCE.md` is not yet explicitly mentioned in the root `## Read First` list in `CODEX_START_HERE.md` or the Codex startup prompt files (`CODEX_START_PROMPT.md`), meaning an assistant could theoretically miss the step-by-step sequence.

---

## 2. Document Priority Audit (Document Tier Map)

Below is the classification of major repository documentation files based on operational requirements:

| Document Path | Tier | Purpose | Recommended Action |
|---|---|---|---|
| `CODEX_START_HERE.md` | **TIER_0** | Startup context & safe commands. | Keep and maintain. |
| `PROJECT_RULES.md` | **TIER_0** | Token limits & system safety rules. | Keep and maintain. |
| `AGENTS.md` | **TIER_0** | Auto-loaded Codex project constraints. | Keep and maintain. |
| `docs/research/ACTIVE_QUESTION.md` | **TIER_0** | Active research sizer lock control. | Read first. Keep updated. |
| `docs/research/GOVERNANCE_STARTUP_SEQUENCE.md` | **TIER_0** | Mandatory AI startup workflow. | Add to `CODEX_START_HERE.md`. |
| `CURRENT_PROJECT_STATUS.md` | **TIER_0** | Current status & registry summaries. | Keep updated daily. |
| `MASTER_AGENT_ROUTER.md` | **TIER_0** | Agent role boundaries & workflows. | Read before editing. |
| `FILE_INDEX.md` | **TIER_1** | Map of files, tests, & directories. | Update when files change. |
| `DOCUMENTATION_MAP.md` | **TIER_1** | Map of files organized by domain. | Reference during audits. |
| `docs/research/AUDIT_REGISTRY.json` | **TIER_1** | Registry of completed quant audits. | Read before starting research. |
| `docs/research/DECISION_REGISTRY.json` | **TIER_1** | Registry of proposed sizer changes. | Read before sizer updates. |
| `docs/research/RESEARCH_AUTHORITY_MAP_V2.md` | **TIER_1** | Authority level of completed audits. | Read before strategy updates. |
| `docs/PAPER_TRADING_RUNBOOK.md` | **TIER_1** | Operations guidelines for paper runs. | Reference for paper loops. |
| `docs/OBSERVABILITY_PLAN.md` | **TIER_1** | Observability design & checklist. | Reference for alert updates. |
| `docs/quant_agent_setup_md/roles/*.md` | **TIER_1** | Guidelines for specific AI roles. | Load only the primary role. |
| `QUANT_FUTURE_DECISION_ENGINE.md` | **TIER_1** | Rules for sizer/research decisions. | Reference for planning. |
| `QUANT_REGIME_PROBABILITY_ENGINE.md` | **TIER_2** | Phase 1 model development roadmap. | Archive on Phase 1 closure. |
| `INVENTORY_REPLAY_RESEARCH_PLAN.md` | **TIER_2** | Phase 2 replay research targets. | Reference during Phase 2. |
| `BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md` | **TIER_2** | Phase 3 engine architecture targets. | Reference during Phase 3. |
| `QUANT_LIFECYCLE_INVENTORY_ENGINE.md` | **TIER_2** | Lifecycle inventory spec sheet. | Reference during Phase 3. |
| `MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md` | **TIER_2** | Liquidity and spread plan. | Reference during research. |
| `docs/PROJECT_CLEANUP_REPORT.md` | **TIER_2** | List of completed cleanup decisions. | Reference only. |
| `VULTR_PAPER_RUN.md` | **TIER_3** | Obsolete deployment notes (HFT/legacy). | Archive candidate. |
| `Doc_Truth_Reconciliation_2026-05-14.md` | **TIER_3** | Historical document reconciliation. | Archive candidate. |
| `Known_Issues_New_Tickets_2026-05-14.md` | **TIER_3** | Obsolete tickets list. | Archive candidate. |
| `Overnight_Maturity_Check_2026-05-19.md` | **TIER_3** | Obsolete daily check instructions. | Archive candidate. |
| `Repo_Canonical_Check_2026-05-19.md` | **TIER_3** | Obsolete canonical validation checklist. | Archive candidate. |
| `docs/research/docs_research_migration_map.md` | **TIER_3** | Historical folder mapping. | Archive candidate. |
| `docs/research/docs_research_migration_dry_run_validation.md` | **TIER_3** | Obsolete dry run checks. | Archive candidate. |

---

## 3. Startup Token Efficiency Audit

### Context & Cost Estimations
- **Current Startup Reading Path**: Loading `CODEX_START_HERE.md` and all files listed in its "Read First" section.
- **Estimated Word/Character Count**: ~116KB of text.
- **Token cost per startup (Input)**: **~29,000 tokens**.
- **Iterative Cost (10 invocations)**: ~290,000 tokens (approx. $0.87 per agent task loop).

### Duplicated Context
- **AGENTS.md & PROJECT_RULES.md**: High overlap on general safety boundaries, workflow constraints, and role instructions.
- **FILE_INDEX.md & docs/PROJECT_STRUCTURE.md**: High duplication of folder trees, files descriptions, and CLI command flags.
- **CURRENT_PROJECT_STATUS.md & CODEX_START_HERE.md**: Both repeat summaries of what works, what is broken, and the quant roadmap.

### Context Optimization Strategies
1. **Defer Tier 1 & Tier 2 loading**: Only load Tier 0 files at startup. Tier 1 registries should only be referenced during specific research tasks.
2. **Prune Tier 3 files**: Moving all Tier 3 files to an archive directory prevents LLM code search mechanisms from scanning them.
3. **Registry Check Termination**: If Step 1 (`ACTIVE_QUESTION.md`) indicates the system is locked, the assistant should stop loading further files or proposing code changes, saving up to 80% of session tokens.

---

## 4. Research Readiness Audit

### Verdict: `B. MINOR_GOVERNANCE_GAPS`

### Evidence
- **Strengths**: The Research Governance Layer is fully designed, verified, and integrated. Path references, active question files, registries, and authority maps are in place. The indices correctly reflect the locking constraints.
- **Gaps**:
  - The startup sequence file `docs/research/GOVERNANCE_STARTUP_SEQUENCE.md` is omitted from the `CODEX_START_HERE.md` "Read First" list, introducing a startup discovery gap.
  - The repository root is cluttered with over 10 stale Tier 3 files (e.g. `Overnight_Maturity_Check_2026-05-19.md`, `Repo_Canonical_Check_2026-05-19.md`), which inflate directory listing tokens.
  - The active question lockout is document-based only; no program code validation enforces the lock during runtime testing.

---

## 5. Top 5 Remaining Governance Gaps

1. **Startup Sequence Visibility**: `GOVERNANCE_STARTUP_SEQUENCE.md` is not referenced in the root start instructions or the start prompt templates, leaving it vulnerable to being skipped.
2. **Workspace Root Clutter**: Obsolete Tier 3 research checklists and legacy deployment logs occupy token space in directory listings.
3. **No Programmatic Lockout**: `main.py` does not check the status of `ACTIVE_QUESTION.md` programmatically before running backtests or dry-runs.
4. **No Schema Verification Check**: The JSON integrity of `AUDIT_REGISTRY.json` and `DECISION_REGISTRY.json` is not validated by a script, raising a risk of formatting errors during manual updates.
5. **Observability UI Disconnect**: The Terminal UI Dashboard and Telegram alerts do not display the active question or lock state, keeping operators blind to governance locks.

---

## Single Highest Priority Next Step

**Add the `docs/research/GOVERNANCE_STARTUP_SEQUENCE.md` reference directly to the "Read First" list in `CODEX_START_HERE.md` to guarantee sequence compliance for all future AI sessions.**
