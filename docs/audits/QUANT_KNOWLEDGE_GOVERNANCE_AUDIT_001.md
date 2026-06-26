# QUANT_KNOWLEDGE_GOVERNANCE_AUDIT_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-24**  

This document presents a comprehensive audit of all markdown files governing the behavior, routing, research direction, project memory, architecture, and agent operations of the Polymarket Adaptive Quant Engine.

---

## Part 1: Global Files Audit

### 1. [MASTER_AGENT_ROUTER.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/MASTER_AGENT_ROUTER.md)
* **Purpose**: Orchestrates AI agent selection by mapping task types to a primary role file and zero to three supporting role files.
* **Last Known Project Phase Reflected**: Phase 2 (Planned).
* **Missing Knowledge**:
  - The React/Vite/TypeScript dashboard structure (`dashboard/src/`) and the state aggregator (`tools/dashboard_state_aggregator.py`).
  - Implementation of MAE/MFE Analytics V1.
  - Gating of agent tasks based on `docs/research/ACTIVE_QUESTION.md` and registries.
* **Outdated Knowledge**:
  - Describes Streamlit/Next.js dashboards as experimental overlapping paths (line 224), when React/Vite is now the core frontend UI.
  - Lists Phase 2 replay analytics and MFE/MAE tracking as planned (line 122) instead of implemented.
* **Contradictions**:
  - Lists `22_INVENTORY_ANALYTICS_AGENT.md` as planned, but lists its MFE/MAE scope as a primary task type in the table.
* **Required Upgrades**:
  - Update router tables to map React frontend changes to the Code Architect and Test CI agents.
  - Mark Phase 2 (replay, MFE/MAE) as implemented in the status section.
  - Enforce checking registries before routing.
* **Priority**: P1
* **Classification**: PARTIALLY_OUTDATED

---

### 2. [PROJECT_RULES.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/PROJECT_RULES.md)
* **Purpose**: Defines critical guidelines for token discipline, safe commands, coding style, active question locks, and logging budgets.
* **Last Known Project Phase Reflected**: Phase 2.
* **Missing Knowledge**:
  - React/Vite dashboard structure and schema slimming/compaction tools.
  - Implementation details of MAE/MFE Analytics V1.
* **Outdated Knowledge**:
  - Describes Phase 2 MFE/MAE tracking and reload/unload analysis as future roadmap items (line 71), whereas these are now implemented as offline/dashboard analytics.
* **Contradictions**: None.
* **Required Upgrades**:
  - Update roadmap section to mark Phase 2 (replay, MFE/MAE) as implemented in offline/dashboard tools.
  - Add guidelines for editing React/Vite frontend code in `dashboard/` (e.g., maintaining TypeScript types, Tailwind conventions).
* **Priority**: P2
* **Classification**: CURRENT

---

### 3. [AGENTS.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/AGENTS.md)
* **Purpose**: Central prompt instructions auto-loaded for AI sessions to enforce safety boundaries, active paths, and rules.
* **Last Known Project Phase Reflected**: Phase 2 (Planned).
* **Missing Knowledge**:
  - React/Vite dashboard structure and files (e.g., `dashboard/src/`, `tools/dashboard_state_aggregator.py`).
  - MAE/MFE Analytics V1 changes.
  - Schema slimming/compaction updates.
* **Outdated Knowledge**:
  - Under `Available AI Agent Role Docs` table, describes `22_INVENTORY_ANALYTICS_AGENT.md` as planned research, when the aggregator now actively extracts `replay_analytics` and `lifecycle_analytics`.
  - Lists `dashboard/` and `web-dashboard/` as secondary/overlapping experimental paths (line 224).
* **Contradictions**:
  - Lists `dashboard/` as experimental but describes the Terminal UI V2 dashboard as main (which is python-based streamlit, but we have migrated to React/Vite).
* **Required Upgrades**:
  - Align role responsibilities with implemented tools (e.g., Backtest Replay, Inventory Analytics, Observability are now fully supported by the React dashboard aggregator).
  - Explicitly restrict edits to the React dashboard src files unless requested.
* **Priority**: P1
* **Classification**: PARTIALLY_OUTDATED

---

### 4. [CURRENT_PROJECT_STATUS.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CURRENT_PROJECT_STATUS.md)
* **Purpose**: Single source of truth for active project development, listing working systems, blockers, and next priorities.
* **Last Known Project Phase Reflected**: Phase 2 (Option D shadow running, host migration, risk/funnel audits).
* **Missing Knowledge**:
  - Complete omission of MAE/MFE Analytics V1 (new TypeScript interfaces, `ResearchPage.tsx` panels, and aggregator helper `_extract_mae_mfe_analytics`).
  - Misses the React dashboard router V1 changes (`REACT_DASHBOARD_ROUTER_V1` implemented in June 2026).
* **Outdated Knowledge**:
  - Describes Streamlit dashboards in `dashboard/` as overlapping UI (line 404), while Vite + React + TS has become the primary UI interface.
  - Does not list `tools/dashboard_state_aggregator.py` or the `mae_mfe_analytics` subkey as active components.
* **Contradictions**: None.
* **Required Upgrades**:
  - Document the completion of MAE/MFE Analytics V1 and React Dashboard Router V1.
  - Move React dashboard files from "Secondary or Experimental Paths" to "What Works Now / Primary UI".
  - Update Next Priority Tasks to reflect the latest active research questions and dashboard integration steps.
* **Priority**: P1
* **Classification**: CRITICAL_GAP

---

### 5. [FILE_INDEX.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/FILE_INDEX.md)
* **Purpose**: Direct index mapping active files, documentation directories, and tests.
* **Last Known Project Phase Reflected**: Phase 2 (June 21, 2026).
* **Missing Knowledge**:
  - The new dashboard React src files, type definitions (`dashboard/src/types/dashboard.ts`), and `ResearchPage.tsx`.
  - Design/report markdown files for MAE/MFE Analytics V1.
* **Outdated Knowledge**:
  - Lists `dashboard/` and `web-dashboard/` as secondary/experimental (line 270) and Streamlit dashboards as active.
* **Contradictions**: None.
* **Required Upgrades**:
  - Index the new React dashboard files, aggregator, and MAE/MFE analytics tools/tests.
  - Move Vite/React files to primary sections.
* **Priority**: P1
* **Classification**: PARTIALLY_OUTDATED

---

### 6. [DOCUMENTATION_MAP.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/DOCUMENTATION_MAP.md)
* **Purpose**: Guides reading sequence for new AI agents and categorizes docs under `docs/`.
* **Last Known Project Phase Reflected**: Phase 2 (June 21, 2026).
* **Missing Knowledge**:
  - React dashboard router reports and MAE/MFE V1 design/audit docs.
* **Outdated Knowledge**:
  - Lists `dashboard/` as Next.js/Streamlit secondary dashboard (line 270).
* **Contradictions**: None.
* **Required Upgrades**:
  - Include new MAE/MFE and dashboard design/report documents in the map.
  - Re-classify dashboard documentation as primary frontend specs.
* **Priority**: P2
* **Classification**: PARTIALLY_OUTDATED

---

### 7. [latest_research_state.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/runtime/research_state/latest_research_state.md)
* **Purpose**: Compact research state tracking bottlenecks, EV coverage rates, and research gaps.
* **Last Known Project Phase Reflected**: Phase 2 (May 11, 2026 - before MAE/MFE implementation).
* **Missing Knowledge**:
  - Recent paper shadow runs (Option D), machine migration results (2026-06-20), micro-recovery and funnel audits.
  - Under "Current Blind Spots", it still lists `mfe_mae_support` and `reload_unload_truth` (line 28), which have since been addressed in code (or at least MFE/MAE support is now coded and tested).
* **Outdated Knowledge**:
  - Reflects state as of May 11, 2026. The latest run ID, metrics, and bottlenecks are completely outdated compared to June 2026 status.
* **Contradictions**:
  - Lists `mfe_mae_support` as a blind spot but code now has it.
* **Required Upgrades**:
  - Needs to be regenerated or updated to reflect the latest shadow run data, new MFE/MAE analytics extraction, and the active question status.
* **Priority**: P1
* **Classification**: OUTDATED

---

### 8. [session_memory_template.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/research/session_memory_template.md)
* **Purpose**: Handoff session template to preserve session context and direct choices.
* **Last Known Project Phase Reflected**: Phase-independent.
* **Missing Knowledge**:
  - React dashboard or UI validation testing commands.
* **Outdated Knowledge**:
  - Replay and trade metrics do not mention MAE/MFE metrics.
* **Contradictions**: None.
* **Required Upgrades**:
  - Add MFE/MAE metrics and React dashboard compilation/smoke tests to the template.
* **Priority**: P3
* **Classification**: CURRENT

---

## Part 2: Agent Role Files Audit (`docs/quant_agent_setup_md/roles/`)

### 9. `01_PROJECT_MANAGER_AGENT.md`
* **Purpose**: Directs sequencing, scope control, delivery gates, and phase boundaries.
* **Last Known Project Phase Reflected**: Phase 2 (Planned).
* **Missing Knowledge**: React/Vite dashboard UI verification and state aggregation; MAE/MFE implemented state.
* **Outdated Knowledge**: Roadmap treats Phase 2 replay/MFE/MAE as planned instead of implemented.
* **Contradictions**: None.
* **Required Upgrades**: Update Phase 2 status to "Implemented in offline and dashboard analytics". Add gates for UI/dashboard promotion (Vite builds, TypeScript compilation, responsive layouts).
* **Priority**: P2
* **Classification**: PARTIALLY_OUTDATED

### 10. `02_CODE_ARCHITECT_AGENT.md`
* **Purpose**: Controls interfaces, file boundaries, dependency direction, and module cohesion.
* **Last Known Project Phase Reflected**: Phase 1/2.
* **Missing Knowledge**: React/Vite TypeScript frontend architecture, Vite configuration, and backend-to-frontend state contracts (types/dashboard.ts, dashboard_state.json).
* **Outdated Knowledge**: Refers only to Streamlit/Next.js overlapping dashboards as secondary.
* **Contradictions**: None.
* **Required Upgrades**: Add Vite/React frontend file boundary rules and state schema validation requirements. Enforce TypeScript typings and Tailwind CSS rules for any frontend code modifications.
* **Priority**: P1
* **Classification**: PARTIALLY_OUTDATED

### 11. `03_RISK_MANAGER_AGENT.md`
* **Purpose**: Controls Dynamic Quant Risk Budget, sizing, drawdown, and LOCKDOWN approval.
* **Last Known Project Phase Reflected**: Phase 2 (Option D shadow running).
* **Missing Knowledge**: MFE/MAE tracking as active risk controls or post-trade reviews.
* **Outdated Knowledge**: Sizing and risk rules are focused entirely on virtual paper or read-only wallet reference, without recognizing shadow sizer designs or low-price expectancy gates.
* **Contradictions**: None.
* **Required Upgrades**: Include MFE/MAE indicators as inputs for risk review. Acknowledge shadow sizing and low-price gating rules.
* **Priority**: P2
* **Classification**: CURRENT

### 12. `04_EXIT_EXECUTION_AGENT.md`
* **Purpose**: Controls profit unload, stop loss, final derisk, forced exit, and panic closeouts.
* **Last Known Project Phase Reflected**: Phase 1/2.
* **Missing Knowledge**: MAE/MFE analytics V1 integration. The exit agent should read MAE/MFE distributions to optimize exit triggers.
* **Outdated Knowledge**: Exit models do not recognize the actual statistics of MAE/MFE collected from recent paper runs.
* **Contradictions**: None.
* **Required Upgrades**: Instruct Exit Agent to use MFE/MAE analysis to review exit thresholds and validate stop-loss/profit-unload efficiency.
* **Priority**: P1
* **Classification**: CRITICAL_GAP

### 13. `05_MARKET_DATA_AGENT.md`
* **Purpose**: Owns scanner lifecycle, orderbook freshness, and market windows.
* **Last Known Project Phase Reflected**: Phase 1/2.
* **Missing Knowledge**: New CLOB rate limit/HTTP classification and empty-book recovery state details.
* **Outdated Knowledge**: Refers to old orderbook display issues.
* **Contradictions**: None.
* **Required Upgrades**: Document the empty-book retry routing in `polymarket/client.py` and the `empty_orderbook` recovery window.
* **Priority**: P2
* **Classification**: CURRENT

### 14. `06_POSITION_RECONCILIATION_AGENT.md`
* **Purpose**: Controls true inventory, open orders, fills, and reconciliation gates.
* **Last Known Project Phase Reflected**: Phase 1/2.
* **Missing Knowledge**: Run-scoped identity patch and generator changes to prevent paper order collisions.
* **Outdated Knowledge**: Stated that `polymarket/position_manager.py` validation was completely unvalidated, but we now have shadow telemetry tracking positions with unique run IDs.
* **Contradictions**: None.
* **Required Upgrades**: Document how `paper_trade_replay_key` is used as the only reliable join key for position reconciliation across cycles.
* **Priority**: P2
* **Classification**: PARTIALLY_OUTDATED

### 15. `07_TEST_CI_AGENT.md`
* **Purpose**: Owns targeted tests, regression gates, and safety proof.
* **Last Known Project Phase Reflected**: Phase 2.
* **Missing Knowledge**: React dashboard unit/smoke tests, type checks (`tsc`), and Vite build checks. Tests for `dashboard_state_aggregator` and MAE/MFE analytics.
* **Outdated Knowledge**: Does not document dashboard/frontend test scripts.
* **Contradictions**: None.
* **Required Upgrades**: Add React/Vite compilation tests (`npm run build` or `npx tsc`) and aggregator tests to the active testing playbook.
* **Priority**: P2
* **Classification**: PARTIALLY_OUTDATED

### 16. `08_RESEARCH_QUANT_AGENT.md`
* **Purpose**: Owns hypothesis testing, EV research, and experiment design.
* **Last Known Project Phase Reflected**: Phase 1/2.
* **Missing Knowledge**: Active question lock framework (`docs/research/ACTIVE_QUESTION.md`) as a hard gate. Existence of MAE/MFE panels on the dashboard to visualize research statistics.
* **Outdated Knowledge**: Refers to offline analytics only without realizing they are aggregated into the dashboard UI.
* **Contradictions**: None.
* **Required Upgrades**: Document the `ACTIVE_QUESTION.md` check as the very first research gate. Direct the agent to use the React dashboard research analytics stack for hypothesis verification.
* **Priority**: P1
* **Classification**: CRITICAL_GAP

### 17. `09_SIGNAL_STRATEGY_AGENT.md`
* **Purpose**: Controls signal, probability, and EV changes.
* **Last Known Project Phase Reflected**: Phase 1/2.
* **Missing Knowledge**: Existence of `entry_model_truth_envelope_v1` carried through the decision logs. Low-price ask limits (<$0.05) and active question locks.
* **Outdated Knowledge**: Standard strategy rules do not mention the new envelope sub-object in `decision_log` and `risk_log`.
* **Contradictions**: None.
* **Required Upgrades**: Document the structure of `entry_model_truth_envelope_v1`. Add gates regarding low-priced contracts and the active question lock.
* **Priority**: P1
* **Classification**: CRITICAL_GAP

### 18. `10_BACKTEST_REPLAY_AGENT.md`
* **Purpose**: Owns backtesting, replays, MFE/MAE, and candidate lifecycles.
* **Last Known Project Phase Reflected**: Phase 1/2.
* **Missing Knowledge**: Implementation details of MFE/MAE analytics in Vite dashboard. `entry_model_truth_envelope_v1` as the data structure for candidate replay joins.
* **Outdated Knowledge**: Describes MFE/MAE tracking as planned (line 438) rather than implemented.
* **Contradictions**: None.
* **Required Upgrades**: Document the MAE/MFE panel and typescript interfaces for candidate lifecycle analysis. Update task routing guidelines to include Vite dashboard representation.
* **Priority**: P1
* **Classification**: PARTIALLY_OUTDATED

### 19. `11_OBSERVABILITY_INCIDENT_AGENT.md`
* **Purpose**: Controls JSONL logs, health signals, and alert routing.
* **Last Known Project Phase Reflected**: Phase 2.
* **Missing Knowledge**: `tools/dashboard_state_aggregator.py` as the compiler of JSONL data. Exception observability logging details (e.g. `runtime_loop_exception` rows in JSONL).
* **Outdated Knowledge**: Lists Telegram summaries as unaligned to CSV per-run timestamps.
* **Contradictions**: None.
* **Required Upgrades**: Add details on `dashboard_state_aggregator.py` and JSONL schema definitions. Document exception logging properties.
* **Priority**: P2
* **Classification**: PARTIALLY_OUTDATED

### 20. `12_REVIEW_LEARNING_AGENT.md`
* **Purpose**: Controls session postmortems and next-experiment selection.
* **Last Known Project Phase Reflected**: Phase 1/2.
* **Missing Knowledge**: `ACTIVE_QUESTION.md` as the gatekeeper of next-experiment registry. Dashboard research panels as primary tools for postmortems.
* **Outdated Knowledge**: Recommends offline markdown report analysis without mentioning React UI.
* **Contradictions**: None.
* **Required Upgrades**: Incorporate the React dashboard as a core tool for session review. Enforce updating `docs/research/ACTIVE_QUESTION.md` and registries at session end.
* **Priority**: P2
* **Classification**: PARTIALLY_OUTDATED

### 21. `13_TELEGRAM_ALERT_AGENT.md`
* **Purpose**: Controls Telegram alerts, cooldowns, and reports.
* **Last Known Project Phase Reflected**: Phase 2.
* **Missing Knowledge**: Exact alert methods available via `utils/telegram_alerts.py` (startup, entry, exit, risk, critical, summary, incident).
* **Outdated Knowledge**: Wording of daily report templates needs cleanup.
* **Contradictions**: None.
* **Required Upgrades**: Document the methods of `TelegramAlertLayer` and direct alerts.
* **Priority**: P3
* **Classification**: CURRENT

### 22. `14_NO_ENTRY_DIAGNOSTICS_AGENT.md`
* **Purpose**: Investigates zero-trade sessions.
* **Last Known Project Phase Reflected**: Phase 1/2.
* **Missing Knowledge**: Vite dashboard no-entry panel details. `delta_extreme` as a key historical alpha leak.
* **Outdated Knowledge**: Stale orderbook diagnostic descriptions are unaligned with the current client empty-book recovery logic.
* **Contradictions**: None.
* **Required Upgrades**: Direct the agent to inspect Vite dashboard's no-entry analysis panel. Add empty-orderbook retry classification logic.
* **Priority**: P2
* **Classification**: PARTIALLY_OUTDATED

### 23. `15_CONFIG_SAFETY_AGENT.md`
* **Purpose**: Controls config safety, env safety, and commands.
* **Last Known Project Phase Reflected**: Phase 1/2.
* **Missing Knowledge**: New pydantic settings or config validator structures for dashboard and aggregator options.
* **Outdated Knowledge**: Default paper mode flags.
* **Contradictions**: None.
* **Required Upgrades**: Document `PAPER_BALANCE_SOURCE` options and validation checks.
* **Priority**: P3
* **Classification**: CURRENT

### 24. `16_PAPER_EVALUATION_AGENT.md`
* **Purpose**: Assigns PASS/CAUTION/FAIL session marks.
* **Last Known Project Phase Reflected**: Phase 1/2.
* **Missing Knowledge**: Role of the React dashboard in displaying evaluation summaries. MAE/MFE thresholds in PASS/FAIL logic.
* **Outdated Knowledge**: Offline json files were the only target; dashboard now aggregates them.
* **Contradictions**: None.
* **Required Upgrades**: Add MFE/MAE variance checks to evaluation criteria.
* **Priority**: P2
* **Classification**: PARTIALLY_OUTDATED

### 25. `17_CLEAN_SHUTDOWN_AGENT.md`
* **Purpose**: Owns clean shutdown paths for feeds/loggers.
* **Last Known Project Phase Reflected**: Phase 2.
* **Missing Knowledge**: Dashboard aggregator shutdown/lock handling.
* **Outdated Knowledge**: Pytest streams closed warnings are already resolved.
* **Contradictions**: None.
* **Required Upgrades**: Add details about clean shutdown for React dev servers or Python aggregator tasks.
* **Priority**: P3
* **Classification**: CURRENT

### 26. `18_MARKET_REGIME_AGENT.md`
* **Purpose**: Controls volatility and trend regime classification.
* **Last Known Project Phase Reflected**: Phase 2.
* **Missing Knowledge**: Vite dashboard regime analytics panel. `entry_model_truth_envelope_v1` regime fields.
* **Outdated Knowledge**: Passive diagnostics are described as purely file-based.
* **Contradictions**: None.
* **Required Upgrades**: Integrate regime classification checks with Vite dashboard regime panels.
* **Priority**: P1
* **Classification**: CRITICAL_GAP

### 27. `19_FAIR_VALUE_ENGINE_AGENT.md`
* **Purpose**: Controls fair value and implied probability.
* **Last Known Project Phase Reflected**: Phase 2.
* **Missing Knowledge**: `entry_model_truth_envelope_v1` details. Vite dashboard fair-value/probability tracking.
* **Outdated Knowledge**: EV is described as unaligned with the aggregator's schema version.
* **Contradictions**: None.
* **Required Upgrades**: Document Vite dashboard integration for EV metrics. Document the truth envelope format.
* **Priority**: P2
* **Classification**: PARTIALLY_OUTDATED

### 28. `20_INVENTORY_ENGINE_AGENT.md`
* **Purpose**: Designs future bounded inventory logic.
* **Last Known Project Phase Reflected**: Phase 2 (offline reloads/unloads).
* **Missing Knowledge**: Offline inventory analytics outputs in Vite dashboard.
* **Outdated Knowledge**: Roadmap treats all Phase 2 reload/unload replays as planned research rather than active python scripts that exist (e.g. `tools/semantic_c_bounded_reload_replay.py`).
* **Contradictions**: None.
* **Required Upgrades**: Acknowledge the completed reload/unload and profit-management python simulators. Update required inputs to include the completed replay scripts.
* **Priority**: P2
* **Classification**: PARTIALLY_OUTDATED

### 29. `21_EXECUTION_MICROSTRUCTURE_AGENT.md`
* **Purpose**: Owns spread, liquidity, and adverse selection.
* **Last Known Project Phase Reflected**: Phase 2.
* **Missing Knowledge**: `tools/dashboard_state_aggregator.py` and Vite dashboard panels.
* **Outdated Knowledge**: Diagnostic metrics are described as log-based only.
* **Contradictions**: None.
* **Required Upgrades**: Align microstructure validation with dashboard state definitions.
* **Priority**: P2
* **Classification**: PARTIALLY_OUTDATED

### 30. `22_INVENTORY_ANALYTICS_AGENT.md`
* **Purpose**: Owns offline missed reload/unload research, MFE/MAE, and Phase 2 evidence.
* **Last Known Project Phase Reflected**: Phase 2 (Planned).
* **Missing Knowledge**: Complete omission of MAE/MFE Analytics V1 implementation, typescript interfaces, and dashboard pages.
* **Outdated Knowledge**: Mentions MAE/MFE and reload/unload as planned research (line 955, 976).
* **Contradictions**: None.
* **Required Upgrades**: Document implemented status of MAE/MFE Analytics V1. Add Vite dashboard and typescript types as required inputs.
* **Priority**: P1
* **Classification**: CRITICAL_GAP

### 31. `23_QUANT_LIFECYCLE_INVENTORY_AGENT.md`
* **Purpose**: Coordinates the combined future lifecycle system.
* **Last Known Project Phase Reflected**: Phase 2/3.
* **Missing Knowledge**: Vite dashboard lifecycle analytics panel details. MAE/MFE implemented state.
* **Outdated Knowledge**: Phase 2 replays are described as planned.
* **Contradictions**: None.
* **Required Upgrades**: Reference the React dashboard lifecycle panel. Mark Phase 2 replays as implemented.
* **Priority**: P2
* **Classification**: PARTIALLY_OUTDATED

---

## Part 3: Knowledge Audit Summary Metrics

| Status Class | Count | Files |
| :--- | :--- | :--- |
| **CURRENT** | 7 | `PROJECT_RULES.md`, `session_memory_template.md`, `03_RISK_MANAGER_AGENT.md`, `05_MARKET_DATA_AGENT.md`, `13_TELEGRAM_ALERT_AGENT.md`, `15_CONFIG_SAFETY_AGENT.md`, `17_CLEAN_SHUTDOWN_AGENT.md` |
| **PARTIALLY_OUTDATED** | 17 | `MASTER_AGENT_ROUTER.md`, `AGENTS.md`, `FILE_INDEX.md`, `DOCUMENTATION_MAP.md`, `01_PROJECT_MANAGER_AGENT.md`, `02_CODE_ARCHITECT_AGENT.md`, `06_POSITION_RECONCILIATION_AGENT.md`, `07_TEST_CI_AGENT.md`, `10_BACKTEST_REPLAY_AGENT.md`, `11_OBSERVABILITY_INCIDENT_AGENT.md`, `12_REVIEW_LEARNING_AGENT.md`, `14_NO_ENTRY_DIAGNOSTICS_AGENT.md`, `16_PAPER_EVALUATION_AGENT.md`, `19_FAIR_VALUE_ENGINE_AGENT.md`, `20_INVENTORY_ENGINE_AGENT.md`, `21_EXECUTION_MICROSTRUCTURE_AGENT.md`, `23_QUANT_LIFECYCLE_INVENTORY_AGENT.md` |
| **OUTDATED** | 1 | `latest_research_state.md` |
| **CRITICAL_GAP** | 6 | `CURRENT_PROJECT_STATUS.md`, `04_EXIT_EXECUTION_AGENT.md`, `08_RESEARCH_QUANT_AGENT.md`, `09_SIGNAL_STRATEGY_AGENT.md`, `18_MARKET_REGIME_AGENT.md`, `22_INVENTORY_ANALYTICS_AGENT.md` |

---

## Verdict: QUANT_KNOWLEDGE_AUDIT_COMPLETE
