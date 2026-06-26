# FULL_PROJECT_REALITY_AUDIT_001

**Task:** FULL_PROJECT_REALITY_AUDIT_001  
**Mode:** DISCOVERY ONLY — no code changes made  
**Date:** 2026-06-26  
**Verification hierarchy:** Repository → Source Code → Runtime Entry Points → Imports → Dependencies → Tests → Documentation  
**Evidence basis:** Source code only. No runtime execution observed. All runtime-only claims are marked NOT VERIFIED RUNTIME.

---

## 7 Deliverables

| Document | Contents |
|---|---|
| This file | Master index of all 16 phases |
| `RUNTIME_ARCHITECTURE_REALITY_001.md` | Phase 2 — Runtime call chain, entry points, mode dispatch |
| `MODULE_BOUNDARY_AUDIT_001.md` | Phase 3 — Module responsibility, boundary violations |
| `DEPENDENCY_GRAPH_AUDIT_001.md` | Phase 4 — Full import dependency graph, circular import analysis |
| `TEST_COVERAGE_REALITY_001.md` | Phase 9 — Coverage by module group |
| `PRODUCTION_READINESS_ASSESSMENT_001.md` | Phase 15 — Scored across 10 dimensions |
| `TECHNICAL_DEBT_REGISTER_V2.md` | Phase 14 — Full debt register (supersedes V1) |

---

## Phase 1 — Repository Structure Reality

### Verified Structure

| Folder | File Count | Active? | Notes |
|---|---|---|---|
| `polymarket/` | 30 .py | YES | Core trading engine |
| `utils/` | 18 .py | YES | Shared utilities |
| `config/` | 2 .py | YES | Pydantic settings |
| `tools/` | 79 .py | YES (offline) | Analysis tools — no runtime wiring |
| `tests/` | 139 .py | YES | Test suite |
| `dashboard/` | 42 TSX + 5 .py | YES | Active React + Python dashboard |
| `hft/` | 10 .py | YES (secondary mode) | HFT engine — imported by main.py:1410 |
| `crypto_scalper/` | 6 .py | YES (secondary mode) | Scalper — imported by main.py:17 |
| `api/` | 1 .py | YES | dashboard_api.py — misplaced, belongs in dashboard/ |
| `research_cockpit/` | ~28 files | NO (orphaned) | Abandoned prototype |
| `web-dashboard/` | ~19 files | NO (orphaned) | Abandoned prototype |
| `scratch/` | 237 files | LOCAL ONLY | Experimental files |
| `logs/` | 980 files flat | GENERATED | Runtime log output |
| `runtime/` | 1,069+ files | GENERATED | Runtime data, research state, quant data |
| `docs/` | 510+ files | MIXED | Documentation hub — active + historical |
| **ROOT** | **395+ markdown** | **CRITICAL DEBT** | See DEBT-C001 |

### Entry Points Verified

| File | Purpose |
|---|---|
| `main.py` (63,323 bytes) | Primary entry point — mode dispatcher |
| `main.py --mode paper` | Paper trading (default safe mode) |
| `main.py --mode live` | Live trading (blocked by default) |
| `main.py --mode verify` | Environment verification only |
| `main.py --mode scalper` | crypto_scalper secondary mode |
| `main.py --mode hft` | hft secondary mode (lazy import) |
| `dashboard/app.py` | Flask dashboard server |
| `scripts/vultr_deploy_paper.py` | Manual deployment script |

### Key File Sizes

| File | Size | Concern? |
|---|---|---|
| `polymarket/trader.py` | 649,554 bytes | CRITICAL — 634KB god class |
| `utils/display.py` | 217,420 bytes | HIGH — no tests |
| `tools/ev_field_coverage.py` | 207,919 bytes | Offline tool, low risk |
| `tools/session_runtime_evaluator.py` | 195,947 bytes | Offline tool, low risk |
| `tests/test_paper_mode.py` | 108,420 bytes | Large integration test |
| `tests/test_session_runtime_evaluator.py` | 112,211 bytes | Large integration test |

---

## Phase 2 — Runtime Architecture Reality

See `RUNTIME_ARCHITECTURE_REALITY_001.md` for full trace.

### Key Facts

- `main()` → `build_parser()` → `validate_env()` → `get_settings()` → mode handler
- Paper mode: `run_polymarket_paper()` → `_acquire_paper_runtime_owner()` → `PolymarketTrader(settings)` → trading loop
- `PolymarketTrader.__init__()` initializes 15+ subsystems (trader.py:363–541)
- `hft` mode uses lazy import — `from hft.main import run_hft` inside the dispatch block (main.py:1410)
- `scalper` mode uses module-level import — `from crypto_scalper.live_runner import main as run_scalper` (main.py:17)
- Default protection: `paper_trading=True`, `live_trading_enabled="false"` in settings

### Live Mode Protection Layers (verified from source)

1. `settings.live_trading_enabled == "false"` — config gate
2. `RiskModeState.current_mode != LOCKDOWN` — risk mode gate
3. `validate_order_intent()` — structural validation
4. `OrderIntent.risk_plan_present` and `OrderIntent.risk_approved` — risk plan gate
5. `OrderIntent.reconciliation_safe` — reconciliation gate

---

## Phase 3 — Module Boundary Audit

See `MODULE_BOUNDARY_AUDIT_001.md` for full analysis.

### Summary of Violations

| ID | Module | Violation | Severity |
|---|---|---|---|
| BV-001 | `polymarket/trader.py` | 12+ responsibilities in 634KB | CRITICAL |
| BV-002 | `polymarket/signal.py` | `get_settings()` at module load time | MEDIUM |
| BV-003 | `polymarket/signal.py` | Hardcoded CWD path at module load | MEDIUM |
| BV-004 | `utils/risk_manager.py` | Legacy TierInfo wrapper over bankroll_tiers | LOW |
| BV-005 | Two event systems | Overlapping domains, no ownership boundary | LOW |
| BV-006 | `api/dashboard_api.py` | Misplaced in api/ instead of dashboard/ | LOW |

---

## Phase 4 — Dependency Graph

See `DEPENDENCY_GRAPH_AUDIT_001.md` for full graph.

### Key Findings

- **No circular imports** — verified by exhaustive static analysis
- Dependency flows from Layer 3 (trader.py) → Layer 2 → Layer 1 → Layer 0 (pure modules)
- `config/settings.py` is the universal Layer 0 root — imported by 15+ modules
- `polymarket/trader.py` imports from 22 polymarket modules + 5 utils modules (hub module)
- Only 1 tool (`event_driven_fair_value_simulation.py`) imports a runtime module (`polymarket.probability_model`) with try/except guard
- `hft/` is fully isolated from `polymarket.*` at the module level
- `crypto_scalper/` shares only `config.settings` and `utils.logger`

### Dependency Layers

```
Layer 0 (pure): config.settings, bankroll_tiers, risk_modes, probability_model, expected_value, 
                 market_feed, quant_event_logger, runtime_event_stream, display, ...
Layer 1: client, order_intent, signal, position_tracker, risk_manager, trade_frequency, ...
Layer 2: position_sizing, order_manager, opportunity_scanner, arbitrage_executor, ...
Layer 3: trader.py (hub — 22 imports)
```

---

## Phase 5 — Position Sizing Path

Verified from source. Full path:

```
SignalResult.score + momentum_pct + rsi + vol_ratio + strategy   [polymarket/signal.py]
  ↓
ProbabilityModelInput → ProbabilityModelResult.confidence_score  [polymarket/probability_model.py]
  ↓
ExpectedValueInput → ExpectedValueResult.ev_yes / ev_no / side   [polymarket/expected_value.py]
  ↓
RiskModeDecision.size_multiplier + allow_new_entries             [polymarket/risk_modes.py]
  ↓
BankrollRankLockResult.active_tier                               [polymarket/bankroll_tiers.py]
  ↓
PositionSizingInput → calculate_position_size() → PositionSizingResult
  8 multipliers: confidence × EV × drawdown × liquidity × spread × time × delta × frequency
  Gate checks: confidence_floor=0.54, EV>0, spread, liquidity, time_remaining>90s, trades_per_hour
                                                                  [polymarket/position_sizing.py]
  ↓
OrderRequest → PolymarketOrderManager.build_order_plan() → RiskPlan  [polymarket/order_manager.py]
  ↓
OrderIntent → validate_order_intent() → OrderIntentDecision       [polymarket/order_intent.py]
  ↓
[Paper: record in PositionTracker, no CLOB call]
[Live: submit to CLOB — blocked by default]
```

### Confidence Floors (verified from source)

| Risk Mode | Minimum Confidence | Source |
|---|---|---|
| NORMAL | 0.54 (PositionSizingInput default) | position_sizing.py:32 |
| DEFENSIVE | 0.65 | risk_modes.py:105 |
| MICRO_RECOVERY | 0.75 | risk_modes.py:111 |
| LOCKDOWN | n/a — entries blocked entirely | risk_modes.py:97 |

---

## Phase 6 — Risk Engine Audit

### Risk Mode State Machine (verified from risk_modes.py)

| Mode | Trigger | Size Multiplier | New Entries |
|---|---|---|---|
| NORMAL | No special conditions | 1.0 | Allowed |
| DEFENSIVE | drawdown ≥ 2% OR consecutive_losses ≥ 2 | 0.5 | Allowed (grade/confidence filter) |
| MICRO_RECOVERY | drawdown ≥ 4% OR consecutive_losses ≥ 3 | 0.25 | Allowed (stricter filter) |
| LOCKDOWN | hard_drawdown_reached OR any lockdown_reason | 0.0 | BLOCKED |

### Hard Limits (verified from utils/risk_manager.py)

| Constant | Value | Meaning |
|---|---|---|
| `HARD_CAP_SINGLE_TRADE` | 0.03 (3%) | Max risk per trade |
| `HARD_DAILY_DRAWDOWN` | 0.10 (10%) | Stop trading if daily loss > 10% |
| `FLOOR_BALANCE` | $5.00 | Stop ALL trading below this |
| `LOSS_CLUSTER_THRESHOLD` | 3 | Consecutive losses before pause |
| `LOSS_CLUSTER_PAUSE_SECONDS` | 1800 | 30-minute pause after loss cluster |

### Risk Decision Flow

`RiskModeState` → `update(consecutive_losses, drawdown_pct)` → `evaluate_risk_mode()` → `RiskModeDecision`  
The decision is then consumed in `PolymarketTrader` to set `allow_new_entries` and `size_multiplier`.

`RiskModeState.trigger_lockdown(reason)` adds reasons to `lockdown_reasons` set — once triggered, lockdown persists until session restart (no automatic unlock found in source).

**NOT VERIFIED RUNTIME:** Whether `RiskModeState.lockdown_reasons` is ever cleared within a session.

---

## Phase 7 — Event Stream Audit

### Event Systems

**System 1: QuantEventLogger** (`utils/quant_event_logger.py`)
- 14 JSONL event categories → `runtime/quant_data/{category}/`
- Synchronous writes (fail-soft)
- Priority: CRITICAL / HIGH / NORMAL / LOW

**System 2: RuntimeEventStream** (`utils/runtime_event_stream.py`)
- Async, bounded deque (maxsize=1000)
- Background writer thread with exponential-backoff retry
- Priority-based drop: LOW events dropped when queue < 15% capacity
- File output: `runtime/event_stream/`

**System 3: RealtimeLogger** (`polymarket/realtime_logger.py`)
- CSV scan records → `runtime/realtime_logs/`
- Separate from JSONL systems

### Event Categories (QuantEventLogger)

| Category | JSONL File | Priority |
|---|---|---|
| decision | decision_log | HIGH |
| execution | execution_log | HIGH |
| trade_open | trade_journal | CRITICAL |
| trade_close | trade_journal | CRITICAL |
| trade_path_checkpoint | path_truth | HIGH |
| orderbook_lineage_probe | orderbook_lineage | LOW |
| risk_event | risk_log | HIGH |
| system_health | system_health | HIGH |
| ghost_position_detected | system_health | CRITICAL |
| research_snapshot | research_log | NORMAL |
| stop_loss_shadow | stop_loss_shadow | HIGH |
| signal_filter_shadow | signal_filter_shadow | LOW |
| signal_filter_shadow_phase_b | signal_filter_shadow_phase_b | LOW |
| delta_shadow | delta_shadow | NORMAL |

**Concern:** Both event systems handle trade and risk events. No documented ownership boundary distinguishes which system receives which events. NOT VERIFIED RUNTIME — cannot confirm whether events are deduplicated or whether both systems are always active.

---

## Phase 8 — Analytics Audit

### Tools Overview

- 79 Python tools in `tools/`
- All offline — none wired into runtime decisions
- Architecture rule enforced: only 1 tool imports a runtime module (with defensive try/except)

### Tool Categories

| Category | Count | Example |
|---|---|---|
| Replay simulation | 10+ | `replay_analyzer.py`, `commitment_regime_replay.py` |
| EV and coverage analysis | 5 | `ev_field_coverage.py`, `canonical_trade_table_v1.py` |
| Lifecycle analysis | 8 | `lifecycle_truth_tables.py`, `candidate_continuity.py` |
| Probe tools | 7 | `decision_cycle_timing_probe.py`, `zero_size_risk_floor_probe.py` |
| Outcome truth | 7 | `official_resolution_acquire_pilot.py`, `outcome_truth_graduation.py` |
| Phase B reporting | 7 | `phase_b_daily_report.py`, `phase_b_snapshot_archiver.py` |
| Session evaluation | 4 | `session_runtime_evaluator.py`, `paper_evaluation_report.py` |
| No-entry analysis | 3 | `no_entry_analyzer.py`, `no_entry_root_cause_report.py` |
| Runtime management | 3 | `runtime_storage_compressor.py`, `dashboard_state_aggregator.py` |
| Shadow filter evaluation | 2 | `shadow_filter_evaluator.py`, `semantic_c_shadow_*.py` |
| Research utilities | 3 | `research_memory_writer.py`, `research_state_writer.py` |

### Shared Foundation

`tools/replay_analyzer.py` is imported by 9 other tools — it is the shared analytical foundation for all replay-based tools.

`tools/lifecycle_truth_tables.py` is a secondary shared utility imported by 4 tools.

---

## Phase 9 — Test Coverage Reality

See `TEST_COVERAGE_REALITY_001.md` for full analysis.

### Summary

| Group | Coverage |
|---|---|
| Pure core modules (risk, sizing, EV, probability, tiers) | HIGH |
| Trader + paper mode integration | HIGH (via large integration tests) |
| Analytics tools (40+ tools) | HIGH |
| Infrastructure (config, shutdown, stale feed) | MEDIUM |
| Market data path (market_feed, gamma, oracle) | LOW |
| Display (display.py, 217KB) | NONE |
| Event streaming (runtime_event_stream) | LOW |
| Telegram alerting | NONE |

---

## Phase 10 — Dead Code Audit

### Confirmed Orphaned (no imports found)

| Item | Evidence |
|---|---|
| `research_cockpit/` (28 files) | No Python imports reference this path |
| `web-dashboard/` (19 files) | No Python imports reference this path |
| `archive/` (10 files) | Archive by name — old versions |

### Confirmed Active But Visually Orphaned

| Item | Actually Active | Evidence |
|---|---|---|
| `hft/` | YES | main.py:1410 lazy import |
| `crypto_scalper/` | YES | main.py:17 module-level import |

### Likely Legacy (not verified)

| Item | Assessment |
|---|---|
| `utils/risk_manager.py TierInfo` | Legacy wrapper — the new sizing path uses bankroll_tiers directly |
| `utils/risk_manager.RiskManager` class | Unclear if still called in trader.py — NOT VERIFIED |
| Some `tools/_audit_*.py` files | Filename prefix `_` suggests experimental/internal |

---

## Phase 11 — Duplicate Logic Audit

### Verified Duplicates

| ID | Logic | Locations | Type |
|---|---|---|---|
| DUP-001 | Bankroll tier lookup | `utils/risk_manager.get_bankroll_tier()` wraps `polymarket.bankroll_tiers.get_tier_config()` | Adapter wrapper (legacy) |
| DUP-002 | EV calculation | `calculate_ev()` in `expected_value.py` + possible inline EV in signal evaluation — NOT VERIFIED | Potential duplicate |
| DUP-003 | Trade event output | Both `QuantEventLogger` and `RuntimeEventStream` handle trade events | Parallel systems (intentional design, overlapping scope) |

### Not Confirmed As Duplicates

- Kelly calculation: `utils/risk_manager.kelly_for_binary()` vs any calculation in position_sizing.py — NOT VERIFIED whether position_sizing uses its own Kelly or calls risk_manager

---

## Phase 12 — Naming Consistency

### Python Code Naming

| Pattern | Examples | Consistent? |
|---|---|---|
| Classes | PascalCase throughout | YES |
| Functions | snake_case throughout | YES |
| Constants | UPPER_SNAKE (e.g., HARD_CAP_SINGLE_TRADE, RiskMode.NORMAL) | YES |
| Dataclasses | PascalCase, frozen=True+slots=True for value objects | YES |
| Private methods | `_method_name()` prefix | YES |

**Code naming: CONSISTENT**

### Module Naming

| Pattern | Examples | Consistent? |
|---|---|---|
| polymarket/ modules | snake_case.py | YES |
| utils/ modules | snake_case.py | YES |
| tools/ modules | snake_case.py, some with `_` prefix for internal/experimental | MOSTLY |

**Module naming: CONSISTENT**

### Documentation Naming

| Pattern | Examples | Consistent? |
|---|---|---|
| Audit reports | UPPER_CASE_001.md, lower_case_001.md | NO — mixed |
| Design docs | UPPER_CASE_V1.md vs lower_case_v1.md | NO — mixed |
| Date-stamped | overnight_maturity_check_2026-05-19.md | INCONSISTENT |
| No suffix | EVIDENCE_QUALITY_AUDIT.md vs EVIDENCE_QUALITY_AUDIT_001.md | INCONSISTENT |

**Documentation naming: INCONSISTENT** — mix of UPPER and lower case across 1000+ docs

---

## Phase 13 — Performance Hotspots

### Identified Hotspots (static analysis only — NOT VERIFIED RUNTIME)

| Item | Evidence | Risk |
|---|---|---|
| `signal.py` module-level `get_settings()` | Runs on every new Python process that imports signal | LOW (one-time, cached) |
| `signal.py` loading `latest_metrics.json` on import | File I/O at import time | LOW (one-time) |
| `trader.py` `__init__` initializes 15+ subsystems | Each system may have its own I/O or network calls | MEDIUM (startup latency) |
| `display.py` 217KB | Rich terminal rendering on every cycle | UNKNOWN (cannot profile without runtime) |
| `tools/ev_field_coverage.py` 208KB | Large tool — likely slow on large JSONL datasets | LOW (offline tool only) |
| `tools/session_runtime_evaluator.py` 196KB | Large tool — same | LOW (offline tool only) |
| WebSocket per-cycle state | WS cache is primary — REST is fallback; if WS is healthy, no REST overhead | UNKNOWN |
| `runtime/quant_data/` file write per event | JSONL append on every decision cycle | MEDIUM if cycle is frequent |

**Note:** Performance profiling requires runtime execution. All above are static observations about potential hotspots, not measured performance problems.

---

## Phase 14 — Technical Debt Register

See `TECHNICAL_DEBT_REGISTER_V2.md` for full register.

### Summary

| Severity | Count | Examples |
|---|---|---|
| CRITICAL | 3 | Root markdown pollution, trader.py god class, venv backups |
| HIGH | 5 | signal.py side effect, two event systems, orphaned dashboards |
| MEDIUM | 8 | legacy TierInfo, hardcoded path, api/ misplacement |
| LOW | 6 | naming inconsistency, display.py no tests, main.py size |
| **Total** | **22** | |

---

## Phase 15 — Production Readiness

See `PRODUCTION_READINESS_ASSESSMENT_001.md` for scored assessment.

### Summary Scores

| Dimension | Score |
|---|---|
| Architecture | 7/10 |
| Runtime (paper) | 7/10 |
| Maintainability | 4/10 |
| Observability | 8/10 |
| Testing | 6/10 |
| Documentation | 3/10 |
| Repository Organization | 2/10 |
| AI Readability | 2/10 |
| Configuration | 8/10 |
| Deployment | 3/10 |
| **Overall (paper)** | **5/10** |

**Verdict:** Ready for paper trading. Not ready for live trading (by design). Not ready for team development (trader.py + root pollution).

---

## Phase 16 — Remaining Unknowns

### Cannot Be Verified Without Runtime Execution

| Unknown | Why It Matters |
|---|---|
| Actual WebSocket connection lifecycle | WS-first architecture requires stable WS; REST fallback frequency is unknown |
| Exact market selection behavior per cycle | `_select_markets()` in trader.py not fully read — selection criteria unknown |
| Whether both event systems (QuantEventLogger + RuntimeEventStream) are always active | Risk of missed or duplicate events |
| Whether `RiskModeState.lockdown_reasons` is ever cleared within a session | If not cleared, lockdown is permanent until restart |
| Whether `utils/risk_manager.RiskManager` class is still used at runtime | May be a legacy class no longer called |
| Whether `anthropic` SDK is called on the trading hot path | Could introduce 8-second latency if called per cycle |
| Whether `freqtrade` is actually imported at runtime | It is in requirements.txt but usage location not found |
| Actual cycle timing (1-second decision loop vs 5-minute epoch boundary) | Affects how often events are generated |
| Empty orderbook recovery success rate | Tests exist but runtime success rate is unknown |
| Paper mode PnL accuracy vs live market prices | Requires comparing paper records to actual market outcomes |

### Cannot Be Verified Without Longer-Duration Testing

| Unknown | Minimum Duration |
|---|---|
| Log volume per day (budget vs actual) | 24 hours |
| Bankroll tier hysteresis behavior near tier boundaries | Multiple sessions |
| MICRO_RECOVERY and LOCKDOWN exit conditions | Enough paper sessions to trigger conditions |
| Preload-next-market success rate | Multiple 5-minute epochs |
| Ghost position detection accuracy | Requires position mismatches to occur |

### Cannot Be Verified From This Repository Alone

| Unknown | External Dependency |
|---|---|
| Polymarket CLOB API stability and rate limits | Live API observation required |
| Gamma API response format stability | Live API observation required |
| Binance WebSocket reconnect behavior | Live WS observation required |
| Actual market liquidity for BTC/ETH 5-minute markets | Market-dependent |

---

## Audit Completion Status

| Phase | Status |
|---|---|
| 1 — Repository Structure | COMPLETE |
| 2 — Runtime Architecture | COMPLETE (see RUNTIME_ARCHITECTURE_REALITY_001.md) |
| 3 — Module Boundary | COMPLETE (see MODULE_BOUNDARY_AUDIT_001.md) |
| 4 — Dependency Graph | COMPLETE (see DEPENDENCY_GRAPH_AUDIT_001.md) |
| 5 — Position Sizing Path | COMPLETE (in this document, Phase 5) |
| 6 — Risk Engine Audit | COMPLETE (in this document, Phase 6) |
| 7 — Event Stream Audit | COMPLETE (in this document, Phase 7) |
| 8 — Analytics Audit | COMPLETE (in this document, Phase 8) |
| 9 — Test Coverage | COMPLETE (see TEST_COVERAGE_REALITY_001.md) |
| 10 — Dead Code Audit | COMPLETE (in this document, Phase 10) |
| 11 — Duplicate Logic | COMPLETE (in this document, Phase 11) |
| 12 — Naming Consistency | COMPLETE (in this document, Phase 12) |
| 13 — Performance Hotspots | COMPLETE (in this document, Phase 13) |
| 14 — Technical Debt Register | COMPLETE (see TECHNICAL_DEBT_REGISTER_V2.md) |
| 15 — Production Readiness | COMPLETE (see PRODUCTION_READINESS_ASSESSMENT_001.md) |
| 16 — Remaining Unknowns | COMPLETE (in this document, Phase 16) |
