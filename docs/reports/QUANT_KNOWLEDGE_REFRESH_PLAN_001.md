# QUANT_KNOWLEDGE_REFRESH_PLAN_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-24**  

This refresh plan outlines the specific, actionable updates required to synchronize the codebase documentation, AI agent setup files, and project memory with the newly implemented features (React/Vite/TypeScript/Tailwind dashboard, `tools/dashboard_state_aggregator.py`, and MAE/MFE Analytics V1).

---

## 1. Global Knowledge Updates Required
To align all files with the active environment, we must execute the following updates:
- **Default Dashboard Mapping**: Explicitly document the Vite/React app under `dashboard/` as the primary user interface. Streamlit-based references in root files must be deprecated.
- **Aggregated State Specifications**: Document the schema of `runtime/dashboard_state.json` (including version `dashboard_state.v0`) as the formal contract between backend metrics and the frontend interface.
- **Session Telemetry Identification**: Instruct all agents to use unique, run-scoped `run_id` strings and `paper_trade_replay_key` as the primary join keys for all analysis and debugging sessions to avoid duplicate run contamination.

---

## 2. Agent Role Updates Required
We must apply targeted edits to the role playbooks under `docs/quant_agent_setup_md/roles/`:

- **01 Project Manager Agent**:
  - Update Phase 2 status from "Planned" to "Implemented for Replay and MAE/MFE".
  - Add Vite frontend build smoke tests to the delivery gate criteria.
- **02 Code Architect Agent**:
  - Document the Vite/React file structure (`dashboard/src/`, `tsconfig.json`, `vite.config.ts`).
  - Add guidelines for TypeScript typings (`dashboard/src/types/dashboard.ts`) and Tailwind CSS rules.
- **04 Exit Execution Agent**:
  - Direct the agent to use MAE/MFE analytics state statistics (aggregated in the dashboard) to audit stop-loss and profit-unload efficiency.
- **06 Position Reconciliation Agent**:
  - Update instructions to use `paper_trade_replay_key` for joining cycle events.
- **07 Test CI Agent**:
  - Include dashboard type-checking (`npm run build` or `npx tsc`) and aggregator tests in the testing commands list.
- **08 Research Quant Agent**:
  - Establish `docs/research/ACTIVE_QUESTION.md` check as the first hard gate.
  - Integrate dashboard panels as primary tools for research visualization.
- **09 Signal Strategy Agent**:
  - Document the `entry_model_truth_envelope_v1` structure in the required inputs and diagnostics.
  - Integrate low-price limits (< $0.05) and active question locks.
- **10 Backtest Replay Agent**:
  - Mark MAE/MFE tracking and candidate lifecycle replays as active systems.
- **11 Observability Incident Agent**:
  - Include `tools/dashboard_state_aggregator.py` and JSONL exceptions (`runtime_loop_exception`) in logging schemas.
- **12 Review Learning Agent**:
  - Add post-session checks to verify active question closures and registry entries.
- **18 Market Regime Agent**:
  - Wire regime classification diagnostics with the new React regime panel.
- **22 Inventory Analytics Agent**:
  - Upgrade documentation to reflect the active status of MAE/MFE Analytics V1 and the typescript dashboard pages.
- **23 Quant Lifecycle Inventory Agent**:
  - Align lifecycle state transitions (OPENING_SCAN to FINAL_DERISK) with the dashboard's lifecycle panels.

---

## 3. Governance Updates Required
- **Active Question Lock Gating**:
  - Harden the gating mechanism in `AGENTS.md` and `PROJECT_RULES.md` to prevent any code changes if `docs/research/ACTIVE_QUESTION.md` is active.
- **Registry Synchronization**:
  - Update `docs/research/AUDIT_REGISTRY.json` and `docs/research/DECISION_REGISTRY.json` to include recent audits (e.g. MAE/MFE V1 pre-commit audits and React dashboard route validations).

---

## 4. Architecture Updates Required
- **Aggregated State File Contract**:
  - Standardize schema version `dashboard_state.v0` inside `tools/dashboard_state_aggregator.py`.
- **Schema Slimming & Compaction**:
  - Incorporate JSONL compression and retention policies into `PROJECT_RULES.md` and agent instructions to respect the 5GB VPS constraints.

---

## 5. Research Updates Required
- **Active Question Resolution**:
  - Resolve the current blocker question `LOW_PRICE_TRUTH_RESOLUTION_001` before attempting any strategy modifications.
- **Hypothesis Testing Ledger**:
  - Standardize the hypothesis ledger to check if a research date range was already validated by a previous agent session, preventing repetitive sweeps.

---

## 6. Dashboard Updates Required
- **Consolidation of Dashboard Folders**:
  - Deprecate Next.js `web-dashboard/` and Streamlit python scripts under `dashboard/` to prevent developer confusion.
- **MAE/MFE Integration**:
  - Regenerate `runtime/dashboard_state.json` to populate the `mae_mfe_analytics` sub-key, enabling the frontend `MaeMfePanel` in React.

---

## 7. Future Roadmap Updates Required
- Update the official roadmap in `README.md`, `CURRENT_PROJECT_STATUS.md`, and `DOCUMENTATION_MAP.md` as follows:
  - **Phase 1 (Regime & Probability Diagnostics)**: Complete.
  - **Phase 2 (Paper Replay, MFE/MAE Tracking)**: Complete in offline tools and UI panels.
  - **Phase 3 (Bounded Multi-Price Inventory)**: Active planning & simulation stage.
  - **Phase 4 (Continuous Probabilistic Sizing)**: Planned future research.

---

## Part 8: Special Focus Areas Implementation Guide

### 1. Executable Reality
* **Action**: Update `09_SIGNAL_STRATEGY_AGENT.md` and `21_EXECUTION_MICROSTRUCTURE_AGENT.md` to distinguish between provisional snapshot prices and official on-chain Polymarket resolutions (specifically for low-priced contracts < $0.05).
* **Target Files**: `09_SIGNAL_STRATEGY_AGENT.md`, `21_EXECUTION_MICROSTRUCTURE_AGENT.md`.

### 2. Bankroll Analytics
* **Action**: Include `bankroll_tier_id`, rank hysteresis, and `MICRO_SURVIVAL_MODE` details in `03_RISK_MANAGER_AGENT.md` to ensure correct sizing and drawdown monitoring.
* **Target Files**: `03_RISK_MANAGER_AGENT.md`, `docs/BANKROLL_TIER_SYSTEM.md`.

### 3. Position Sizing
* **Action**: Add sizer constraints to `03_RISK_MANAGER_AGENT.md` based on active question locks and shadow sizer design options for low-priced contracts.
* **Target Files**: `03_RISK_MANAGER_AGENT.md`.

### 4. Always Active Framework
* **Action**: Update `17_CLEAN_SHUTDOWN_AGENT.md` and `11_OBSERVABILITY_INCIDENT_AGENT.md` to cover fail-soft logging (Windows file-lock `PermissionError` handling) and duplicate runtime startup guards.
* **Target Files**: `17_CLEAN_SHUTDOWN_AGENT.md`, `11_OBSERVABILITY_INCIDENT_AGENT.md`.

### 5. Capacity Scaling
* **Action**: Update `02_CODE_ARCHITECT_AGENT.md` and `PROJECT_RULES.md` to enforce the 150MB/day logging limit, JSONL compaction, and database slimming rules.
* **Target Files**: `02_CODE_ARCHITECT_AGENT.md`, `PROJECT_RULES.md`.

### 6. Research Analytics Stack
* **Action**: Update all research and replay agent files (`08`, `10`, `22`, `23`) to formally reference the React dashboard panels: Replay, No Entry, Session, Lifecycle, Regime, and MAE/MFE Analytics.
* **Target Files**: `08_RESEARCH_QUANT_AGENT.md`, `10_BACKTEST_REPLAY_AGENT.md`, `22_INVENTORY_ANALYTICS_AGENT.md`, `23_QUANT_LIFECYCLE_INVENTORY_AGENT.md`.

### 7. Adaptive Prediction Market Platform Vision & Future Decision Engine
* **Action**: Ensure `session_memory_template.md` and the PM agent (`01`) enforce generating exactly three future options (Safe EV, Aggressive Info, Structural Root-Cause) for every design recommendation.
* **Target Files**: `session_memory_template.md`, `01_PROJECT_MANAGER_AGENT.md`.
