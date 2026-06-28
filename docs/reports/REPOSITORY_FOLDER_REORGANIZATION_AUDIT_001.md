# REPOSITORY_FOLDER_REORGANIZATION_AUDIT_001

**Date:** 2026-06-28  
**Task Class:** 2 DESIGN  
**Status:** COMPLETE

---

## FINAL_VERDICT

**PLAN COMPLETE** — Three top-level areas need structural work:
1. `tools/` — 80 flat scripts need 10 subdirectories
2. `tests/` — 161 flat test files need 15 subdirectories  
3. Root `.md` files — 27 files, most should move to `docs/`

`polymarket/` flat structure is tolerable now but Phase 5+ extraction (from Trader Decomposition Audit) will naturally create subdirectories. No immediate polymarket/ restructuring recommended.

---

## CURRENT_REPO_STRUCTURE

```
.                           ← 27 .md + 6 .py + .env files at root
├── config/                 ← 2 files (clean)
├── docs/                   ← 1,156 files across architecture/, audits/, operations/, reports/
├── polymarket/             ← 35 .py modules (flat, plus orchestration/ subdir)
│   └── orchestration/      ← Batch 3C extractions
├── runtime/                ← 369 files (gitignored — quant_data, logs, reports)
├── scratch/                ← 116 files (gitignored)
├── tests/                  ← 161 .py test files (ALL FLAT — major problem)
├── tools/                  ← 80 .py scripts (mostly flat — major problem)
│   ├── backtest_engine_v2/ ← ✓ already organized (9 files)
│   └── flaos/              ← ✓ already organized (8 files)
└── utils/                  ← 18 files (mostly clean)
```

### Problem summary

| Area | Files | Problem | Severity |
|---|---|---|---|
| `tests/` | 161 flat | No grouping; impossible to run targeted suites by category | **HIGH** |
| `tools/` | 80 flat | Mixed probes/canonical/research/audit at same level | **HIGH** |
| Root `*.md` | 27 files | Research plans, AI handoffs, prompts polluting root | **MEDIUM** |
| Root `*.py` | 6 files | Scripts (daily_report.py, etc.) with unclear ownership | **LOW** |
| `polymarket/` | 35 flat | Growing but tolerable; will self-organize via decomposition | **DEFERRED** |

---

## CURRENT_REPO_STRUCTURE (detailed)

### tools/ — 80 flat Python files

Currently 2 organized subdirs: `backtest_engine_v2/` (clean), `flaos/` (clean).

**Naming patterns reveal implicit categories already:**
- `_audit_*.py` (7 files) — audit scripts
- `canonical_*.py` (3 files) — canonical builders
- `phase_b_*.py` (6 files) — phase B pipeline
- `outcome_truth_*.py` (3 files) — resolution pipeline
- `official_resolution_*.py` (4 files) — resolution pipeline
- `free_outcome_truth_*.py` (3 files) — resolution pipeline
- `semantic_c_*.py` (5 files) — semantic C replay suite
- `lifecycle_*.py` (5 files) — lifecycle analysis
- `*_probe.py` (8 files) — admission/timing probes
- `*_replay.py` (6+ files) — replay tools
- `research_*.py` (3 files) — research state management

### tests/ — 161 flat Python files

```
Execution:     test_execution_*.py (6), test_live_*.py (5), test_proxy_*.py (1)
Telemetry:     test_telemetry_*.py (1), test_quant_event_logger.py, test_orderbook_lineage_*.py
Canonical:     test_canonical_*.py (5), test_backtest_engine_v2.py
Replay:        test_*_replay.py (10+), test_lifecycle_truth_*.py
Policy:        test_shadow_policy.py, test_market_availability_engine.py
Shadow:        test_shadow_*.py (4), test_semantic_c_*.py (5)
Bankroll:      test_bankroll_*.py (2), test_size_sharp_engine.py
Lifecycle:     test_lifecycle_*.py (9)
Runtime:       test_paper_mode.py, test_runtime_*.py (5), test_polymarket_trader.py
Market:        test_delta_engine.py, test_probability_model.py, test_opportunity_scanner.py (4)
Live/Client:   test_live_*.py (7), test_polymarket_client_v2.py
FLAOS:         test_flaos_*.py (6)
Outcome:       test_outcome_truth_*.py (5), test_free_outcome_truth_*.py (3)
Phase B:       test_phase_b_*.py (3)
Probes:        test_*_probe.py (9), test_discovery_harness.py
Research:      test_research_*.py (3), test_quant_intelligence_engine.py
```

---

## TARGET_REPO_STRUCTURE

```
.
├── main.py                       ← keep at root (entry point)
├── check_balance.py              ← keep at root (CLI utility)
├── CLAUDE.md                     ← keep at root (required by Claude Code)
├── AGENTS.md                     ← keep at root (AI governance)
├── PROJECT_RULES.md              ← keep at root (operator reference)
├── CODEX_START_HERE.md           ← keep at root
├── README.md                     ← keep at root
├── MASTER_AGENT_ROUTER.md        ← keep at root
├── CURRENT_PROJECT_STATUS.md     ← keep at root
│
├── config/                       ← unchanged (2 files)
├── utils/                        ← unchanged (18 files)
├── polymarket/                   ← gradually decomposed by trader audit
├── runtime/                      ← unchanged (gitignored)
│
├── docs/
│   ├── architecture/             ← unchanged
│   ├── audits/                   ← unchanged
│   ├── operations/               ← unchanged
│   ├── reports/                  ← unchanged
│   └── research/                 ← MOVE root research .md files here
│       ├── BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md
│       ├── INVENTORY_REPLAY_RESEARCH_PLAN.md
│       ├── MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md
│       ├── QUANT_FUTURE_DECISION_ENGINE.md
│       ├── QUANT_LIFECYCLE_INVENTORY_ENGINE.md
│       └── QUANT_REGIME_PROBABILITY_ENGINE.md
│
├── tools/
│   ├── backtest_engine_v2/       ← ✓ already organized
│   ├── flaos/                    ← ✓ already organized
│   ├── canonical/                ← NEW
│   ├── replay/                   ← NEW
│   ├── probes/                   ← NEW
│   ├── phase_b/                  ← NEW
│   ├── outcome_truth/            ← NEW
│   ├── research/                 ← NEW
│   ├── audit/                    ← NEW
│   ├── runtime/                  ← NEW
│   └── shadow/                   ← NEW
│
└── tests/
    ├── execution/                ← NEW
    ├── telemetry/                ← NEW
    ├── canonical/                ← NEW
    ├── replay/                   ← NEW
    ├── policy/                   ← NEW
    ├── shadow/                   ← NEW
    ├── bankroll/                 ← NEW
    ├── lifecycle/                ← NEW
    ├── runtime/                  ← NEW
    ├── market/                   ← NEW
    ├── live/                     ← NEW
    ├── flaos/                    ← NEW
    ├── outcome_truth/            ← NEW
    ├── phase_b/                  ← NEW
    └── probes/                   ← NEW
```

---

## MOVE_MATRIX_SUMMARY

### Root .md → `docs/research/`

| File | Move to | Risk |
|---|---|---|
| `BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md` | `docs/research/` | NO_IMPORT_RISK |
| `INVENTORY_REPLAY_RESEARCH_PLAN.md` | `docs/research/` | NO_IMPORT_RISK |
| `MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md` | `docs/research/` | NO_IMPORT_RISK |
| `QUANT_FUTURE_DECISION_ENGINE.md` | `docs/research/` | NO_IMPORT_RISK |
| `QUANT_LIFECYCLE_INVENTORY_ENGINE.md` | `docs/research/` | NO_IMPORT_RISK |
| `QUANT_REGIME_PROBABILITY_ENGINE.md` | `docs/research/` | NO_IMPORT_RISK |
| `CHATGPT_PROJECT_START_PROMPT.md` | `docs/research/` or delete | NO_IMPORT_RISK |
| `CODEX_START_PROMPT.md` | `docs/` or delete if superseded | NO_IMPORT_RISK |
| `VULTR_PAPER_RUN.md` | `docs/operations/` | NO_IMPORT_RISK |
| `DOCUMENTATION_MAP.md` | `docs/` | NO_IMPORT_RISK |
| `FILE_INDEX.md` | `docs/` | NO_IMPORT_RISK |
| `PROJECT_STRUCTURE.md` | `docs/` | NO_IMPORT_RISK |
| `KNOWN_ISSUES.md` | `docs/` | NO_IMPORT_RISK |
| `AI_HANDOFF_*.md` (7 files) | Delete or `docs/sessions/` | NO_IMPORT_RISK |

### tools/ → subdirectories

| Target subdirectory | Files |
|---|---|
| `tools/canonical/` | `canonical_trade_context_builder.py`, `canonical_regime_export.py`, `canonical_trade_table_v1.py` |
| `tools/replay/` | `replay_analyzer.py`, `runtime_event_replay.py`, `commitment_regime_replay.py`, `convergence_regime_classification_replay.py`, `exit_convergence_intelligence_replay.py`, `lifecycle_profit_management_replay.py`, `stabilization_survival_replay.py`, `lifecycle_truth_backfill.py`, `lifecycle_truth_tables.py` |
| `tools/probes/` | `decision_cycle_timing_probe.py`, `entry_budget_consumption_probe.py`, `epoch_boundary_alignment_probe.py`, `executable_state_persistence_probe.py`, `market_readiness_admission_probe.py`, `probability_semantics_calibration_probe.py`, `silent_zone_selection_probe.py`, `zero_size_risk_floor_probe.py`, `event_driven_admission_simulation.py`, `event_driven_fair_value_simulation.py`, `lifecycle_latency_report.py`, `lifecycle_timing_report.py`, `candidate_continuity.py`, `candidate_path_observability.py`, `discovery_harness_validation.py` |
| `tools/phase_b/` | `phase_b_daily_evidence_collector.py`, `phase_b_daily_report.py`, `phase_b_run_daily_pipeline.py`, `phase_b_snapshot_archiver.py`, `phase_b_snapshot_summary.py`, `phase_b_weekly_review_engine.py` |
| `tools/outcome_truth/` | `free_outcome_truth_provisional.py`, `free_outcome_truth_provisional_join.py`, `free_outcome_truth_provisional_readiness.py`, `official_resolution_acquire_pilot.py`, `official_resolution_full_history_runner.py`, `official_resolution_outcome_join.py`, `official_resolution_rpc_client.py`, `outcome_truth_graduation.py`, `outcome_truth_population_manifest.py`, `outcome_truth_streaming_scan.py` |
| `tools/research/` | `research_gap_analyzer.py`, `research_memory_writer.py`, `research_state_writer.py`, `quant_intelligence_engine.py`, `quant_data_quality.py`, `edge_inventory_report.py`, `no_entry_analyzer.py`, `no_entry_root_cause_report.py` |
| `tools/audit/` | `_audit_cs_btc.py`, `_audit_decision_state.py`, `_audit_w21_w22.py`, `_delta_audit.py`, `_delta_causal_verify.py`, `_drift_audit.py`, `_opp_capture_audit.py`, `ev_field_coverage.py`, `ev_field_coverage_audit.py`, `executable_truth_overlay.py` |
| `tools/runtime/` | `multi_session_runner.py`, `session_runtime_evaluator.py`, `runtime_storage_compressor.py`, `dashboard_state_aggregator.py`, `execution_paper_runtime.py`, `paper_evaluation_report.py`, `operator_summary.py`, `offline_telegram_summary.py`, `compact_run_summary.py`, `joined_records_builder.py`, `decision_log_slim_index.py` |
| `tools/shadow/` | `shadow_filter_evaluator.py`, `semantic_c_bounded_reload_replay.py`, `semantic_c_inventory_continuity_replay.py`, `semantic_c_shadow_fill_replay.py`, `semantic_c_shadow_observability_report.py`, `semantic_c_shadow_pnl_truth.py`, `cross_run_ev_blindness.py`, `cross_run_lifecycle_truth.py` |
| `tools/eth_os/` or keep at root | `eth_yes_fc_os_command_center.py` — active command center |

### tests/ → subdirectories

| Target subdirectory | Files (selected) |
|---|---|
| `tests/execution/` | `test_execution_*.py`, `test_live_allowance_preflight.py`, `test_live_credential_and_allowance_readiness.py`, `test_proxy_allowance_semantics.py`, `test_live_fill_loop.py`, `test_live_reconciliation_timer.py` |
| `tests/telemetry/` | `test_telemetry_backfill.py`, `test_quant_event_logger.py`, `test_orderbook_lineage_probe_v1.py`, `test_entry_model_truth_envelope_v1.py`, `test_entry_attribution_snapshot.py`, `test_quote_lineage_phase4.py`, `test_quote_age_phase5.py` |
| `tests/canonical/` | `test_canonical_*.py` (5), `test_backtest_engine_v2.py`, `test_replay_analyzer.py` |
| `tests/replay/` | `test_*_replay.py` (~10), `test_lifecycle_truth_backfill.py`, `test_lifecycle_truth_tables.py`, `test_stabilization_survival_replay.py`, `test_commitment_regime_replay.py`, `test_convergence_regime_classification_replay.py`, `test_exit_convergence_intelligence_replay.py`, `test_lifecycle_profit_management_replay.py` |
| `tests/policy/` | `test_shadow_policy.py`, `test_market_availability_engine.py`, `test_risk_modes.py` |
| `tests/shadow/` | `test_shadow_filters.py`, `test_shadow_filter_evaluator.py`, `test_option_d_shadow.py`, `test_delta_shadow.py`, `test_stop_loss_shadow.py`, `test_semantic_c_*.py` (5) |
| `tests/bankroll/` | `test_bankroll_rank_engine.py`, `test_bankroll_tiers.py`, `test_size_sharp_engine.py` |
| `tests/lifecycle/` | `test_lifecycle_*.py` (~9), `test_path_truth_checkpoints.py`, `test_exit_agent.py` |
| `tests/runtime/` | `test_paper_mode.py`, `test_runtime_*.py` (5), `test_polymarket_trader.py`, `test_runtime_ownership.py`, `test_logging_resilience.py` |
| `tests/market/` | `test_delta_engine.py`, `test_expected_value.py`, `test_probability_model.py`, `test_opportunity_scanner.py`, `test_realtime_feed.py`, `test_regime_diagnostics.py`, `test_signal_identity*.py` |
| `tests/live/` | `test_live_telegram_visibility.py`, `test_verify_mode.py`, `test_polymarket_client_v2.py`, `test_ghost_position_sentinel.py` |
| `tests/flaos/` | `test_flaos_*.py` (6) |
| `tests/outcome_truth/` | `test_outcome_truth_*.py` (5), `test_free_outcome_truth_*.py` (3) |
| `tests/phase_b/` | `test_phase_b_*.py` (3) |
| `tests/probes/` | `test_*_probe.py` (9), `test_discovery_harness_validation.py`, `test_market_readiness_*.py` |

---

## IMPORT_RISK_CLASSIFICATION

### tools/ moves

| Risk level | Applies to |
|---|---|
| `NO_IMPORT_RISK` | All tools/ moves — tools are standalone scripts, not imported by runtime |
| Exception: `canonical_trade_context_builder.py` | Imported by `tests/test_canonical_*.py` — tests must update `from tools.canonical.canonical_trade_context_builder import ...` |
| Exception: `backtest_engine_v2/` | Already a package, already imported correctly via `from tools.backtest_engine_v2 import ...` — no change needed if subdir stays |

### tests/ moves

| Risk level | Applies to |
|---|---|
| `MEDIUM_TEST_DISCOVERY_RISK` | ALL test file moves — pytest's `testpaths` in `pytest.ini` must be updated, or `conftest.py` added per subdirectory |
| `LOW_PATH_RISK` | Tests that import `from tools.X import Y` — path stays correct if tools/ structure unchanged OR updated together |

**pytest.ini impact:** Current `pytest.ini` likely specifies `testpaths = tests`. After reorganization, this stays valid — pytest discovers recursively. However, CI/CD scripts or targeted runs like `pytest tests/test_paper_mode.py` must be updated to `pytest tests/runtime/test_paper_mode.py`.

### polymarket/ moves (Phases 5-8 only)

| Risk level | Applies to |
|---|---|
| `HIGH_RUNTIME_IMPORT_RISK` | Any `polymarket/*.py` move — trader.py, main.py, and many test files import `from polymarket.X import Y`. Every move requires updating ALL import sites. |
| Exception | `shadow_policy.py` — already correctly placed. `market_availability_engine.py` — already correctly placed. These don't need moving. |

---

## PHASED_MIGRATION_PLAN

### Phase 0 — Root Markdown Cleanup (NOW, ZERO RISK)

Move 14 research/planning/obsolete `.md` files from root to `docs/research/` or `docs/`.  
Delete 7 `AI_HANDOFF_*.md` files (session artifacts, not project docs).  
Keep at root: `CLAUDE.md`, `AGENTS.md`, `PROJECT_RULES.md`, `MASTER_AGENT_ROUTER.md`, `CODEX_START_HERE.md`, `README.md`, `CURRENT_PROJECT_STATUS.md`.

**Risk:** `NO_IMPORT_RISK`. No code reads these files.  
**Gate:** `git status` clean. No broken links in CLAUDE.md or AGENTS.md.

---

### Phase 1 — tools/audit/ and tools/shadow/ (SAFE, no test impact)

Move the `_audit_*.py` files and `semantic_c_*.py` files to subdirectories.  
**Risk:** `NO_IMPORT_RISK` (tools not imported by runtime).  
Tests importing these tools must update: `from tools.audit._delta_audit import ...` etc.  
**Gate:** `tests/test_drift_audit.py`, `tests/test_semantic_c_*.py` all pass after import update.

---

### Phase 2 — tools/canonical/, tools/phase_b/, tools/outcome_truth/

Move the three clearest groupings with coherent naming.  
**Risk:** `LOW_PATH_RISK` — canonical builder IS imported by canonical tests.  
**Update required:** All `from tools.canonical_trade_context_builder import` → `from tools.canonical.canonical_trade_context_builder import`.  
**Gate:** `pytest tests/test_canonical_*.py -q` passes.

---

### Phase 3 — tools/replay/, tools/probes/, tools/research/, tools/runtime/

Move remaining tools groups.  
**Risk:** `NO_IMPORT_RISK` for runtime/research/probes. `LOW_PATH_RISK` for replay (tests import replay_analyzer).  
**Gate:** All test_*.py that import from moved modules pass.

---

### Phase 4 — tests/ subdirectory creation (HIGH IMPACT, requires planning)

Create 15 test subdirectories and add `__init__.py` or `conftest.py` to each.  
Move test files per the classification above.  
**Risk:** `MEDIUM_TEST_DISCOVERY_RISK` — all targeted test run commands in:
- `CLAUDE.md` (commands section)
- `docs/operations/AI_RESOURCE_GOVERNANCE_001.md`
- `docs/operations/REPOSITORY_HEALTH_CHECK_001.md`
- CI/CD scripts
must be updated to new paths.

**Do NOT move tests until ALL of the following are updated:**
1. `pytest.ini` testpaths (if absolute)
2. All targeted test commands in governance docs
3. All `AI_RESOURCE_GOVERNANCE_001.md` test command examples
4. CLAUDE.md test commands

**Recommended approach:** Add `conftest.py` files to each subdirectory rather than updating pytest.ini — this allows pytest's recursive discovery to work without path changes.

**Gate:** `pytest --collect-only tests/ -q | wc -l` shows same count before and after.

---

### Phase 5 — polymarket/ non-runtime modules (AFTER Trader Decomposition Phase 1-4)

Only move these after `TRADER_MODULE_DECOMPOSITION_AUDIT_001` Phase 1-4 are complete:
- `polymarket/shadow_policy.py` → already in correct place
- `polymarket/market_availability_engine.py` → already in correct place
- `polymarket/bankroll_rank_engine.py` → could move to `polymarket/analytics/`
- `polymarket/size_sharp_engine.py` → could move to `polymarket/analytics/`

**Risk:** `HIGH_RUNTIME_IMPORT_RISK` — trader.py imports these at line 46+. Every import site must be updated simultaneously.  
**Gate:** Full paper session (10+ cycles) after any polymarket/ module move.

---

### Phases 6-8 — trader.py decomposition (per TRADER_MODULE_DECOMPOSITION_AUDIT_001)

Follow the 8-phase plan from the trader audit. These phases create new files in:
- `polymarket/observability/`
- `polymarket/orchestration/`

No moves of existing files — only new files receive extracted code.

---

## DO_NOT_MOVE_YET

### polymarket/ — never move these without a dedicated task and full regression

| File | Reason |
|---|---|
| `polymarket/trader.py` | The god class — can only be decomposed, not moved |
| `polymarket/client.py` | Runtime CLOB client — imported everywhere |
| `polymarket/order_manager.py` | Execution critical |
| `polymarket/order_intent.py` | Execution guard |
| `polymarket/position_manager.py` | Position tracking |
| `polymarket/probability_model.py` | Strategy core |
| `polymarket/signal.py` | Strategy core |
| `polymarket/opportunity_scanner.py` | Scan core |
| `polymarket/risk_modes.py` | Risk enforcement |
| `polymarket/position_sizing.py` | Sizing |
| `polymarket/expected_value.py` | EV calculation |

### tests/ — do not move until pytest commands are audited

| File | Reason |
|---|---|
| `tests/test_paper_mode.py` | Referenced in CLAUDE.md and AI_RESOURCE_GOVERNANCE_001.md explicitly |
| `tests/test_execution_risk_controls.py` | Referenced in many task task notes |
| `tests/test_canonical_trade_context_builder.py` | Referenced in CANONICAL_* task outputs |
| Any test file referenced in ACTIVE_WORKFLOW_STATE_001.json notes | Must update docs first |

### tools/ — do not move

| File | Reason |
|---|---|
| `tools/canonical_trade_context_builder.py` | Imported in CI verification commands — update commands first |
| `tools/backtest_engine_v2/` | Already correctly organized as package |
| `tools/flaos/` | Already correctly organized as package |
| `tools/eth_yes_fc_os_command_center.py` | Active command center — confirm no active runs first |
| `tools/quant_intelligence_engine.py` | Referenced in task QUANT_INTELLIGENCE_ENGINE_OFFLINE_BUILDER_001 outputs |

---

## ROLLBACK PLAN

All phases are reversible via `git revert` since no runtime files are modified. For each phase:

1. Before moving: commit clean state with tag `pre-phase-N-reorganize`
2. Move files: single atomic commit with full move matrix
3. Test: run targeted pytest suite for moved category
4. If any failure: `git revert HEAD` immediately — do not patch-forward

**Never squash phase commits** — each phase must be independently revertible.

---

## PRIORITY ORDER

| Priority | Action | Risk | Effort |
|---|---|---|---|
| 1 | Delete `AI_HANDOFF_*.md` root files | ZERO | 5 min |
| 2 | Move 14 research `.md` to `docs/research/` | ZERO | 15 min |
| 3 | Create `tools/audit/` + move `_audit_*.py` | NO IMPORT | 30 min |
| 4 | Create `tools/phase_b/` + move `phase_b_*.py` | NO IMPORT | 15 min |
| 5 | Create `tools/outcome_truth/` + move resolution files | NO IMPORT | 15 min |
| 6 | Create `tools/canonical/` + move + update test imports | LOW | 30 min |
| 7 | Create `tools/shadow/`, `tools/replay/`, etc. | LOW | 1 hour |
| 8 | Create `tests/` subdirs + move + update docs | MEDIUM | 3 hours |
| 9 | `polymarket/` moves post-trader decomposition | HIGH | Separate task |
