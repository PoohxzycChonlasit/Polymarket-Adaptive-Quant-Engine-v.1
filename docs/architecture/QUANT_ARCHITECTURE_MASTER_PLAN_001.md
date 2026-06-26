# QUANT_ARCHITECTURE_MASTER_PLAN_001

**Date:** 2026-06-26  
**Status:** DESIGN ONLY — No code changes authorized by this document  
**Scope:** Long-term enterprise architecture for the Adaptive Quant Platform  
**Baseline:** Post-Batch-1 (`e76581fb`), paper runtime validated, 11 cycles / 443 events clean  

---

## 1. Current Architecture Assessment

### What Exists

The platform is a working Python trading bot targeting Polymarket 5-minute BTC/ETH binary prediction markets. It was paper-validated successfully on 2026-06-26 under `run_id=20260626T135846Z_19480_d6b9f23e`.

**Strengths:**
- Clean paper/live separation enforced at the mode layer
- Event-driven JSONL observability already in place (`runtime_event_stream`)
- Bankroll tier system with hysteresis is operational
- WebSocket-first market data architecture
- Runtime ownership guard prevents duplicate processes
- Exception observability captures runtime errors without crashing the loop
- Signal → EV → risk → intent → execution guard chain is intact
- 2200+ tests across the lifecycle

**Weaknesses:**
- `polymarket/trader.py` is 13,125 lines — a God Object that owns orchestration, market data assembly, signal routing, risk delegation, paper execution, presentation, and state management simultaneously
- `tools/` is a flat namespace of 70+ offline scripts with no internal hierarchy or ownership boundaries
- `utils/` mixes display, observability, risk, config, and runtime infrastructure without grouping
- Dashboard (`dashboard/`) and offline tooling have no formal API contract with the runtime
- No formal module interface layer — cross-module imports are direct and unguarded
- Research tooling (`tools/`) mixed with production tools (`tools/dashboard_state_aggregator.py`)
- No formal data schema registry — JSONL field contracts are implicit
- `runtime/` directory is a mixed bag of logs, exports, events, state, reports, and data files with no enforced retention policy

### What Batch 1 Fixed

Batch 1 (`e76581fb`) extracted `trader_presentation.py` (206 lines) from `trader.py`, proving the decomposition pattern is safe. This is the architectural foundation for Batches 2–N.

### Technical Debt Register (Architecture-Level)

| Item | Severity | Location |
|------|----------|----------|
| God Object `trader.py` (13,125 lines) | CRITICAL | `polymarket/trader.py` |
| Flat `tools/` namespace (70+ files) | HIGH | `tools/` |
| No module interface layer | HIGH | All packages |
| No JSONL schema registry | HIGH | `runtime/event_stream/` |
| Mixed `utils/` concerns | MEDIUM | `utils/` |
| Dashboard has no runtime API contract | MEDIUM | `dashboard/` |
| No retention enforcement on `runtime/` | MEDIUM | `runtime/` |
| Experimental paths not isolated | LOW | `hft/`, `crypto_scalper/` |

---

## 2. Long-Term Target Architecture

### Vision

A modular, layered quant platform where:

1. **Runtime core** is a small, stable, well-tested loop that is easy to reason about and hard to break
2. **Domain packages** own their boundaries and expose stable interfaces
3. **Offline research** is completely separated from runtime decisions
4. **Dashboard** consumes a versioned state API, not internal runtime state directly
5. **Schema contracts** are explicit and versioned for JSONL events
6. **Data flows** are unidirectional: Runtime → Event Stream → Offline → Dashboard

### Core Design Principles

| Principle | Meaning |
|-----------|---------|
| **Runtime-safe** | Runtime loop cannot be broken by adding offline features |
| **Event-driven** | State transitions produce events; consumers read events, never state directly |
| **Replay-first** | Every runtime decision must be reproducible from the event log |
| **Paper/live inviolable** | Paper execution path and live execution path share zero code below the mode gate |
| **Offline is read-only** | Offline tools never write to runtime state, only read events |
| **Fail-soft everywhere** | Observability, Telegram, logging failures must not propagate to trading |
| **Schema-versioned** | JSONL event fields carry `schema_version`; consumers reject unknown versions |
| **Interface-gated** | Cross-package calls go through declared interfaces, not internal imports |

---

## 3. Layered Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         OPERATOR LAYER                              │
│  Terminal UI (utils/display.py)   Telegram Alerts   Dashboard UI    │
└────────────────────────────────────┬────────────────────────────────┘
                                     │ read-only
┌────────────────────────────────────▼────────────────────────────────┐
│                         OBSERVABILITY LAYER                         │
│  runtime_event_stream  │  JSONL Schema Registry  │  Heartbeat       │
│  dashboard_state.json  │  bot_status.json        │  Log rotation     │
└────────────────────────────────────┬────────────────────────────────┘
                                     │ write-only from runtime
┌────────────────────────────────────▼────────────────────────────────┐
│                          RUNTIME CORE                               │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐   │
│  │  Orchestrat-│  │  Market Data │  │  Signal / Alpha Engine  │   │
│  │  ion Layer  │  │  Layer       │  │                         │   │
│  │  main.py    │  │  (WebSocket- │  │  signal.py              │   │
│  │  trader.py  │  │   first)     │  │  regime_diagnostics.py  │   │
│  │  (slim)     │  │              │  │  probability_model.py   │   │
│  └──────┬──────┘  └──────┬───────┘  │  expected_value.py      │   │
│         │                │          └──────────────┬──────────┘   │
│         │                │                         │               │
│  ┌──────▼────────────────▼─────────────────────────▼──────────┐   │
│  │                    DECISION GATE LAYER                      │   │
│  │  order_intent.py  │  risk_modes.py  │  bankroll_tiers.py   │   │
│  │  position_sizing.py  │  risk_manager.py                     │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │                                     │
│  ┌────────────────────────────▼────────────────────────────────┐   │
│  │                    EXECUTION LAYER                          │   │
│  │  PAPER PATH          │          LIVE PATH                  │   │
│  │  virtual_ptb.py      │          client.py                  │   │
│  │  (simulated fills)   │          order_manager.py           │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │                                     │
│  ┌────────────────────────────▼────────────────────────────────┐   │
│  │               RECONCILIATION LAYER                          │   │
│  │  position_tracker.py  │  position_manager.py                │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                     │ event stream only
┌────────────────────────────────────▼────────────────────────────────┐
│                        OFFLINE RESEARCH LAYER                       │
│  tools/research/     tools/replay/     tools/analytics/             │
│  tools/lifecycle/    tools/evaluation/ tools/diagnostics/           │
│                                                                     │
│  HARD RULE: Nothing in this layer writes to runtime state           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Folder Structure Roadmap

### Target Structure (Multi-Year)

```
/
├── main.py                          # CLI entry point only — no business logic
├── config/
│   └── settings.py                  # Pydantic BaseSettings; single source of truth
│
├── polymarket/                      # Runtime domain package
│   ├── __init__.py
│   ├── interfaces/                  # NEW: explicit module interfaces
│   │   ├── market_data.py           # MarketDataProvider protocol
│   │   ├── signal_engine.py         # SignalEngine protocol
│   │   ├── execution.py             # ExecutionProvider protocol
│   │   └── reconciliation.py        # ReconciliationProvider protocol
│   ├── orchestration/               # NEW: extracted from trader.py
│   │   ├── trader.py                # Slim orchestrator only (~500 lines target)
│   │   ├── trader_presentation.py   # UI formatting (Batch 1 done)
│   │   ├── trader_state.py          # NEW: runtime state dataclass
│   │   ├── trader_cycle.py          # NEW: single-cycle execution logic
│   │   └── trader_lifecycle.py      # NEW: startup/shutdown/cleanup
│   ├── market_data/                 # NEW: consolidated market data
│   │   ├── gamma_fetcher.py
│   │   ├── market_feed.py
│   │   ├── oracle_price_feed.py
│   │   ├── virtual_ptb.py
│   │   ├── price_to_beat_fetcher.py
│   │   └── quant_indicators.py
│   ├── alpha/                       # NEW: signal and probability
│   │   ├── signal.py
│   │   ├── regime_diagnostics.py
│   │   ├── probability_model.py
│   │   ├── expected_value.py
│   │   └── delta_engine.py
│   ├── risk/                        # NEW: risk and sizing consolidated
│   │   ├── bankroll_tiers.py
│   │   ├── position_sizing.py
│   │   ├── risk_modes.py
│   │   └── order_intent.py
│   ├── execution/                   # NEW: paper and live paths
│   │   ├── paper/
│   │   │   └── virtual_ptb.py       # Paper fill simulation
│   │   ├── live/
│   │   │   ├── client.py
│   │   │   └── order_manager.py
│   │   └── shadow_telemetry.py
│   ├── reconciliation/              # NEW: position and fill reconciliation
│   │   ├── position_manager.py
│   │   └── arbitrage_executor.py
│   └── backtester_5m.py            # Backtest path (separate from runtime)
│
├── utils/                           # Cross-cutting runtime infrastructure
│   ├── risk_manager.py              # Canonical hard risk policy
│   ├── position_tracker.py          # In-memory position and drawdown
│   ├── display.py                   # Terminal UI V2
│   ├── logger.py                    # Log setup
│   ├── config_validator.py          # Startup validation
│   ├── runtime_event_stream.py      # JSONL event writer
│   ├── runtime_ownership.py         # Duplicate process guard
│   ├── quant_event_logger.py        # High-level event API
│   ├── telegram_alerts.py           # Fail-soft Telegram
│   ├── telegram_reporter.py         # Report formatting
│   ├── scan_log_loader.py           # CSV log reader
│   └── rate_limiter.py              # API rate limiter
│
├── schema/                          # NEW: JSONL schema registry
│   ├── __init__.py
│   ├── v1/
│   │   ├── runtime_heartbeat_v1.py
│   │   ├── market_snapshot_v1.py
│   │   ├── go_no_go_decision_v1.py
│   │   ├── candidate_rejected_v1.py
│   │   ├── paper_order_submitted_v1.py
│   │   ├── position_closed_v1.py
│   │   └── ...
│   └── registry.py                  # Schema lookup and validation
│
├── tools/                           # Offline tools — grouped by purpose
│   ├── __init__.py
│   ├── research/                    # Research and investigation tools
│   │   ├── canonical_regime_export.py
│   │   ├── research_state_writer.py
│   │   ├── research_memory_writer.py
│   │   └── research_gap_analyzer.py
│   ├── replay/                      # Trade replay and lifecycle
│   │   ├── replay_analyzer.py
│   │   ├── runtime_event_replay.py
│   │   ├── lifecycle_truth_tables.py
│   │   ├── lifecycle_latency_report.py
│   │   └── semantic_c_*.py
│   ├── analytics/                   # Post-session analytics
│   │   ├── edge_inventory_report.py
│   │   ├── ev_field_coverage.py
│   │   ├── decision_log_slim_index.py
│   │   └── canonical_trade_table_v1.py
│   ├── evaluation/                  # Paper session evaluation
│   │   ├── paper_evaluation_report.py
│   │   ├── session_runtime_evaluator.py
│   │   ├── no_entry_analyzer.py
│   │   └── quant_data_quality.py
│   ├── lifecycle/                   # Outcome truth and lifecycle
│   │   ├── outcome_truth_graduation.py
│   │   ├── lifecycle_truth_backfill.py
│   │   ├── joined_records_builder.py
│   │   └── official_resolution_*.py
│   ├── diagnostics/                 # Runtime diagnostics probes
│   │   ├── market_readiness_admission_probe.py
│   │   ├── decision_cycle_timing_probe.py
│   │   ├── executable_state_persistence_probe.py
│   │   └── epoch_boundary_alignment_probe.py
│   └── dashboard_state_aggregator.py  # Dashboard state builder
│
├── dashboard/                       # React web dashboard
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── services/
│   │   │   └── api.ts               # Typed API client for dashboard state
│   │   └── types/
│   │       └── dashboard.ts         # TypeScript types matching Python schema
│   └── package.json
│
├── tests/                           # Test suite (2200+ tests)
│   ├── fixtures/
│   ├── test_*.py
│   └── __init__.py
│
├── runtime/                         # Runtime data (gitignored except structure)
│   ├── event_stream/                # JSONL event logs (primary)
│   ├── research_state/              # Compact research summaries
│   ├── research_exports/            # Canonical export tables
│   ├── realtime_logs/               # Per-session CSV logs
│   ├── reports/                     # Offline analyzer outputs
│   ├── quant_data/                  # Legacy JSONL path (deprecating)
│   └── dashboard_state.json         # Dashboard state snapshot
│
├── docs/                            # Design and operational docs
│   ├── architecture/
│   ├── research/
│   ├── operations/
│   ├── quant_agent_setup_md/
│   └── ...
│
└── logs/                            # Rotating application logs
```

---

## 5. Python Modularization Strategy

### The Decomposition Target: `trader.py`

`trader.py` at 13,125 lines is the primary decomposition target. Batch 1 removed presentation (206 lines). The full decomposition roadmap:

| Extract | Target File | Estimated Lines | Batch |
|---------|------------|-----------------|-------|
| Presentation helpers | `trader_presentation.py` | 206 | **Done (Batch 1)** |
| Runtime state dataclass | `trader_state.py` | ~150 | Batch 2 |
| Startup/shutdown lifecycle | `trader_lifecycle.py` | ~400 | Batch 2 |
| Single-cycle execution | `trader_cycle.py` | ~600 | Batch 3 |
| Market data assembly | `polymarket/market_data/` | ~800 | Batch 3 |
| Signal orchestration | `polymarket/alpha/` | ~500 | Batch 4 |
| Risk delegation layer | delegated to `risk/` | ~300 | Batch 4 |
| Paper execution bridge | `polymarket/execution/paper/` | ~300 | Batch 5 |
| Residual orchestrator | `trader.py` (final) | ~800 | Batch 5+ |

**Target:** `trader.py` ≤ 1,000 lines, orchestrating well-named collaborators.

### Decomposition Safety Rules

1. **One extraction per batch** — never split two concerns in the same commit
2. **Proxy delegation first** — new file gets the logic; old method becomes a one-line proxy
3. **Tests must pass before and after** — zero regressions permitted
4. **No behavior changes during extraction** — pure structural moves only
5. **Runtime validation after each batch** — paper mode must boot and run 3+ cycles
6. **Commit message must state**: which methods moved, what behavior is unchanged, which tests cover the extraction

---

## 6. Shared Components

Components used by more than one package must live in `utils/` or `schema/`, never inside a domain package.

### Current Shared Components (Stable)

| Component | Location | Used By |
|-----------|----------|---------|
| `RuntimeEventStream` | `utils/runtime_event_stream.py` | trader, risk, reconciliation, lifecycle |
| `QuantEventLogger` | `utils/quant_event_logger.py` | trader, tools |
| `TelegramAlerts` | `utils/telegram_alerts.py` | trader, tools, main |
| `RiskManager` | `utils/risk_manager.py` | trader, tests |
| `PositionTracker` | `utils/position_tracker.py` | trader, reconciliation |
| `RuntimeOwnership` | `utils/runtime_ownership.py` | main |
| `ScanLogLoader` | `utils/scan_log_loader.py` | tools/evaluation |
| `Settings` | `config/settings.py` | everything |

### New Shared Components (Target)

| Component | Location | Purpose |
|-----------|----------|---------|
| `SchemaRegistry` | `schema/registry.py` | Validate JSONL events at write time |
| `MarketDataProvider` | `polymarket/interfaces/market_data.py` | Protocol for data sources |
| `ExecutionProvider` | `polymarket/interfaces/execution.py` | Protocol for paper/live execution |
| `DashboardStateWriter` | `utils/dashboard_state_writer.py` | Single writer for `dashboard_state.json` |

---

## 7. Runtime Ownership

### Who Owns What at Runtime

| Concern | Owner | Constraint |
|---------|-------|-----------|
| Process singleton | `utils/runtime_ownership.py` | One paper runtime at a time |
| Market data state | `polymarket/market_data/` | WebSocket-first; REST fallback only |
| Signal state | `polymarket/alpha/` | Read-only input from market data |
| Risk state | `utils/risk_manager.py` + `utils/position_tracker.py` | Mutated only by reconciliation and trade lifecycle |
| Execution decisions | `polymarket/risk/order_intent.py` | All exits/entries must pass OrderIntent gate |
| Paper fills | `polymarket/execution/paper/virtual_ptb.py` | No live calls |
| Live fills | `polymarket/execution/live/client.py` | Live mode only, requires preflight |
| Event emission | `utils/runtime_event_stream.py` | Single writer; all events funnel through here |
| Dashboard state | `tools/dashboard_state_aggregator.py` | Runs offline; reads events, writes `dashboard_state.json` |
| Telegram | `utils/telegram_alerts.py` | All outbound Telegram goes through cooldown layer |

### Runtime Ownership Anti-Patterns (Forbidden)

- Dashboard reads runtime Python objects directly (must read `dashboard_state.json`)
- Offline tools call into `polymarket/` during their execution
- Risk manager is called from two different threads without a lock
- Signal computation happens inside the event emission path
- `trader.py` imports from `tools/`

---

## 8. Dashboard Architecture

### Current State

The React dashboard (`dashboard/`) reads from `dashboard_state.json`, which is written by `tools/dashboard_state_aggregator.py` reading from the JSONL event stream. This is correct architecture.

### Target Architecture

```
Runtime
  └── utils/runtime_event_stream.py
        └── runtime/event_stream/runtime_events_YYYY-MM-DD_NNN.jsonl
              └── tools/dashboard_state_aggregator.py (polling, offline)
                    └── runtime/dashboard_state.json
                          └── FastAPI server (utils/dashboard_api.py)
                                └── dashboard/src (React, Vite)
                                      └── Browser
```

### Dashboard Contracts

**`dashboard_state.json` schema** must be versioned:

```json
{
  "schema_version": "v2",
  "generated_at": "ISO8601",
  "run_id": "...",
  "portfolio": { ... },
  "risk": { ... },
  "market_scan": { ... },
  "decisions": [ ... ],
  "heartbeat": { ... }
}
```

**Rules:**
- Dashboard never imports Python runtime modules
- TypeScript types in `dashboard/src/types/dashboard.ts` must mirror Python schema
- `dashboard_state.json` is written atomically (write temp → rename)
- Dashboard is read-only; it never writes back to the runtime
- Dashboard displays run_id prominently; stale state must show age warning

---

## 9. Data Architecture

### Event Stream (Primary Source of Truth)

```
runtime/event_stream/runtime_events_YYYY-MM-DD_NNN.jsonl
```

- Append-only
- One event per line
- Each event: `schema_version`, `event_type`, `event_version`, `git_commit`, `runtime_session_id`, `session_sequence`, `payload`
- Max file size: rotate at 50 MB (creates `_002`, `_003`, etc.)
- Retention: 30 days raw; compress to `.jsonl.gz` after 7 days; delete after 30

### Secondary Data Paths

| Path | Contents | Owner | Retention |
|------|----------|-------|-----------|
| `runtime/realtime_logs/YYYY-MM-DD/` | Per-run scan CSV | `realtime_logger.py` | 14 days |
| `runtime/research_state/` | Compact research summaries | `tools/research/research_state_writer.py` | Keep all |
| `runtime/research_exports/` | Canonical trade tables | `tools/analytics/` | Keep all |
| `runtime/reports/` | Offline analyzer JSON outputs | `tools/evaluation/` | 30 days |
| `runtime/dashboard_state.json` | Live dashboard snapshot | `tools/dashboard_state_aggregator.py` | Overwrite |
| `runtime/bot_status.json` | Runtime liveness signal | `utils/runtime_ownership.py` | Overwrite |
| `logs/` | Rotating application logs | `utils/logger.py` | 7 days |

### JSONL Schema Registry Target

Every event type gets a versioned Python dataclass in `schema/v1/`:

```python
# schema/v1/runtime_heartbeat_v1.py
@dataclass
class RuntimeHeartbeatV1:
    schema_version: str = "1.0"
    event_type: str = "runtime_heartbeat_v1"
    active_positions: int = 0
    current_bankroll_tier: str = ""
    decision_latency_ms: float = 0.0
    # ... all fields explicit
```

The registry validates payloads at write time (fail-soft — log warning, do not raise) and at read time in offline tools (strict — reject unknown versions).

### Data Flow Diagram

```
WebSocket Feed ──► market_data/  ──► alpha/ ──► risk/ ──► execution/
                                                              │
                                              reconciliation/ │
                                                    │         │
                                                    ▼         ▼
                                          RuntimeEventStream (single writer)
                                                    │
                                                    ▼
                                    runtime/event_stream/*.jsonl
                                         │              │
                                         ▼              ▼
                              tools/replay/        tools/dashboard_state_aggregator.py
                                         │              │
                                         ▼              ▼
                              runtime/reports/    runtime/dashboard_state.json
                                                        │
                                                        ▼
                                                  dashboard/ (React)
```

---

## 10. Replay Architecture

### Design Principle

Every trade decision must be fully reproducible from the event log. The replay system is the primary source of truth for strategy research.

### Replay Layers

| Layer | Purpose | Location |
|-------|---------|----------|
| **Raw replay** | Re-read events in order, reconstruct state | `tools/replay/runtime_event_replay.py` |
| **Trade lifecycle** | Join open → path → close → resolution | `tools/lifecycle/lifecycle_truth_tables.py` |
| **Signal replay** | Re-evaluate signal logic against historical market snapshots | `tools/replay/replay_analyzer.py` |
| **Semantic replay** | Category-specific deep analysis (Shadow C, bounded reload) | `tools/replay/semantic_c_*.py` |
| **Outcome truth** | Join with official Polymarket resolution | `tools/lifecycle/outcome_truth_graduation.py` |

### Replay Contracts

1. Replay tools **never** write to `runtime/event_stream/`
2. Replay outputs go to `runtime/reports/` or `runtime/research_exports/`
3. Replay tools must declare their input schema version explicitly
4. Any replay finding that could influence strategy must be promoted via a separate explicit task — replay itself is evidence only

### Phase Roadmap for Replay

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 1 | Observability — regime classification, probability, JSONL | **Active** |
| Phase 2 | Paper inventory replay — MFE/MAE, decay, reload/unload | Planned |
| Phase 3 | Bounded inventory engine — caps, stop-loss, forced exit | Future |
| Phase 4 | Continuous probabilistic inventory trading | Future (evidence-gated) |

---

## 11. AI Agent Architecture

### Current Agent System

23 role-based agent markdown playbooks in `docs/quant_agent_setup_md/roles/`. These are human-readable guidance documents that structure how AI coding assistants should approach different task types.

### Target Agent Architecture

The agent system should evolve to have **explicit task routing** and **role enforcement**:

```
MASTER_AGENT_ROUTER.md
    │
    ├── Task Classification
    │     ├── RUNTIME_CHANGE → requires risk/exec agent + CI agent
    │     ├── RESEARCH → requires quant/replay agent
    │     ├── OBSERVABILITY → requires observability agent
    │     ├── REFACTOR → requires architect agent + CI agent
    │     └── DASHBOARD → requires architect agent only
    │
    ├── Role Selection (PRIMARY + up to 3 SUPPORTING)
    │
    └── Scope Enforcement
          ├── Research tasks CANNOT modify runtime
          ├── Refactor tasks CANNOT change behavior
          └── Dashboard tasks CANNOT import polymarket.*
```

### AI Agent Design Rules

| Rule | Rationale |
|------|-----------|
| No LLM calls inside the trading loop | Latency and determinism |
| Agents read only their designated files | Prevents scope creep |
| Research agents cannot promote findings to runtime unilaterally | Evidence ≠ authorization |
| Refactor agents must prove zero behavior change | Structural moves only |
| CI agent must validate every implementation task | Tests before claims |

### Future: Autonomous Monitoring Agent

A lightweight monitoring agent that reads `bot_status.json` and `runtime/event_stream/` to detect anomalies and produce Telegram summaries. This agent is offline-only and never influences trading decisions.

---

## 12. Dependency Rules

### Hard Dependency Rules

```
main.py
  └── may import: config, polymarket/orchestration, utils
  └── must NOT import: tools, dashboard, schema (except at startup validation)

polymarket/orchestration/
  └── may import: polymarket/market_data, polymarket/alpha, polymarket/risk,
                  polymarket/execution, utils, config, schema
  └── must NOT import: tools, dashboard

polymarket/alpha/
  └── may import: config, schema
  └── must NOT import: polymarket/execution, polymarket/reconciliation, tools

polymarket/execution/paper/
  └── may import: config, utils, schema
  └── must NOT import: polymarket/execution/live

polymarket/execution/live/
  └── may import: config, utils, schema
  └── must NOT import: polymarket/execution/paper

tools/
  └── may import: config, schema, utils/scan_log_loader, utils/logger
  └── must NOT import: polymarket/orchestration, polymarket/execution,
                       utils/runtime_event_stream (only reads files)

dashboard/src/
  └── may consume: runtime/dashboard_state.json (via HTTP/file)
  └── must NOT import: Python packages
```

### Dependency Graph (Simplified)

```
config ◄── all packages

schema ◄── runtime_event_stream ◄── polymarket/orchestration
                                 ◄── utils/quant_event_logger
                                 ◄── tools/ (read-only consumers)

utils/ ◄── polymarket/*
       ◄── tools/ (selected utilities only)

polymarket/market_data ◄── polymarket/orchestration
polymarket/alpha        ◄── polymarket/orchestration
polymarket/risk         ◄── polymarket/orchestration
polymarket/execution    ◄── polymarket/orchestration
polymarket/reconciliation ◄── polymarket/orchestration
```

---

## 13. Import Rules

### Forbidden Import Patterns

```python
# FORBIDDEN: tool importing live execution
from polymarket.execution.live.client import PolymarketClient  # in tools/

# FORBIDDEN: paper importing live
from polymarket.execution.live import order_manager  # in execution/paper/

# FORBIDDEN: alpha importing execution
from polymarket.execution.paper import virtual_ptb  # in alpha/

# FORBIDDEN: runtime importing tools
from tools.replay.replay_analyzer import ReplayAnalyzer  # in trader.py

# FORBIDDEN: dashboard importing runtime Python
from polymarket.trader import PolymarketTrader  # in dashboard backend
```

### Required Import Patterns

```python
# CORRECT: orchestration uses interface protocol
from polymarket.interfaces.market_data import MarketDataProvider

# CORRECT: tools read from filesystem, not runtime objects
events = read_jsonl("runtime/event_stream/runtime_events_2026-06-26_001.jsonl")

# CORRECT: dashboard reads state file
state = json.load(open("runtime/dashboard_state.json"))

# CORRECT: event emission goes through single writer
event_stream.emit(RuntimeHeartbeatV1(active_positions=0, ...))
```

### Import Enforcement Strategy

Long-term: add `import-linter` or `forbidden-imports` pre-commit hook that validates the dependency graph on every commit. Medium-term: enforce via code review and PR description template. Immediate: document in `CLAUDE.md` and `PROJECT_RULES.md`.

---

## 14. Refactor Roadmap (Batch 2+)

### Batch 2 — Trader Lifecycle Extraction
**Scope:** Extract startup/shutdown from `trader.py`  
**Target:** `polymarket/orchestration/trader_lifecycle.py`  
**Estimated lines moved:** ~400  
**Residual `trader.py`:** ~12,725  
**Tests required:** Lifecycle tests (startup, clean shutdown, SIGTERM)  
**Validation:** Paper runtime boots and runs 3+ cycles, clean SIGTERM shutdown

### Batch 3 — Trader State Dataclass
**Scope:** Extract runtime state from `trader.py` into a dataclass  
**Target:** `polymarket/orchestration/trader_state.py`  
**Estimated lines moved:** ~150 (state declarations + property accessors)  
**Residual `trader.py`:** ~12,575  
**Tests required:** State isolation tests  
**Validation:** Paper runtime boots, state is serializable, dashboard state unchanged

### Batch 4 — Single-Cycle Extraction
**Scope:** Extract one-cycle execution logic from `trader.py`  
**Target:** `polymarket/orchestration/trader_cycle.py`  
**Estimated lines moved:** ~600  
**Residual `trader.py`:** ~11,975  
**Tests required:** Cycle isolation tests, mock injection  
**Validation:** Paper runtime completes 10+ cycles, events emitted correctly

### Batch 5 — Market Data Package
**Scope:** Consolidate market data modules under `polymarket/market_data/`  
**Target:** Move `gamma_fetcher.py`, `market_feed.py`, `oracle_price_feed.py`, `virtual_ptb.py`, `price_to_beat_fetcher.py`, `quant_indicators.py`  
**Nature:** Move + re-export proxies; no logic changes  
**Tests required:** Full import smoke, feed integration tests  
**Validation:** Paper runtime with live market data, no feed regressions

### Batch 6 — Alpha Package
**Scope:** Consolidate signal/alpha modules under `polymarket/alpha/`  
**Target:** Move `signal.py`, `regime_diagnostics.py`, `probability_model.py`, `expected_value.py`, `delta_engine.py`  
**Nature:** Move + re-export proxies  
**Tests required:** Signal and backtest tests  
**Validation:** Backtest smoke, paper runtime signal values unchanged

### Batch 7 — Risk Package
**Scope:** Consolidate risk modules under `polymarket/risk/`  
**Target:** Move `bankroll_tiers.py`, `position_sizing.py`, `risk_modes.py`, `order_intent.py`  
**Nature:** Move + re-export proxies  
**Tests required:** Risk mode, bankroll, sizing, and intent tests  
**Validation:** Risk gate behavior unchanged through paper validation

### Batch 8 — Tools Reorganization
**Scope:** Group `tools/` flat namespace into subdirectories  
**Target:** `tools/research/`, `tools/replay/`, `tools/analytics/`, `tools/evaluation/`, `tools/lifecycle/`, `tools/diagnostics/`  
**Nature:** Move files + update all imports  
**Tests required:** All tool imports pass, no broken test fixtures  
**Validation:** All existing tool tests pass

### Batch 9 — Schema Registry
**Scope:** Create `schema/` package with versioned event dataclasses  
**Target:** `schema/v1/*.py`, `schema/registry.py`  
**Nature:** New code, no renames  
**Tests required:** Schema validation tests, round-trip tests  
**Validation:** All emitted events pass schema validation in offline check

### Batch 10+ — Interface Layer
**Scope:** Add `polymarket/interfaces/` protocol definitions  
**Target:** `MarketDataProvider`, `SignalEngine`, `ExecutionProvider`, `ReconciliationProvider`  
**Nature:** New abstractions, old code becomes concrete implementations  
**Tests required:** Protocol conformance tests  
**Validation:** Paper runtime uses implementations, offline tools use protocols

### Batch Constraints

| Constraint | Rule |
|-----------|------|
| One concern per batch | Never mix two extraction concerns |
| No behavior changes | Structural moves only until explicitly scoped |
| Runtime validation required | Every batch needs paper cycle validation |
| Tests before merge | CI must be green |
| Commit message must state invariants | What moved, what is unchanged |

---

## 15. Risks

### Risk 1: Trader.py God Object Regression (HIGH)
**Risk:** Extraction introduces subtle behavioral changes (state mutation order, initialization sequence, exception handling path)  
**Mitigation:** Proxy delegation pattern (Batch 1 proven); full test run + runtime validation after every batch  
**Threshold:** Any test regression stops the batch immediately

### Risk 2: Import Cycle Introduction (MEDIUM)
**Risk:** New package structure creates circular imports  
**Mitigation:** Strict one-way dependency rule; interface layer breaks cycles; lint on every commit  
**Detection:** `python -c "import polymarket.orchestration.trader"` must work clean

### Risk 3: JSONL Schema Drift (MEDIUM)
**Risk:** New code emits events that offline tools cannot parse; dashboard shows stale/broken state  
**Mitigation:** Schema registry with version field; all consumers check `schema_version` before parsing  
**Detection:** Schema validation test suite

### Risk 4: Dashboard State Staleness (LOW-MEDIUM)
**Risk:** `dashboard_state_aggregator.py` runs infrequently or fails, leaving dashboard showing stale data  
**Mitigation:** Dashboard shows `generated_at` age; warn if > 120 seconds old; aggregator runs as daemon during paper sessions  
**Detection:** Dashboard health panel

### Risk 5: Tools Accidental Runtime Import (MEDIUM)
**Risk:** Offline tool accidentally imports `polymarket/execution/live/client.py`, creating a live-risk surface  
**Mitigation:** Import linter in CI; `tools/` explicitly forbidden from importing `polymarket/execution/live/`  
**Detection:** Pre-commit hook or CI import check

### Risk 6: Phase Boundary Violation (HIGH)
**Risk:** Research finding from Phase 1 gets wired into runtime decision-making without an explicit implementation phase  
**Mitigation:** Active Question system (max 1 open); DECISION_REGISTRY.json; explicit task scope required for runtime changes  
**Detection:** Code review; `PROJECT_RULES.md` enforcement

### Risk 7: VPS Disk Overflow (MEDIUM)
**Risk:** JSONL event stream grows without compaction; 5GB VPS disk fills  
**Mitigation:** 50 MB file rotation; 7-day compress; 30-day delete; `runtime_storage_compressor.py` runs daily  
**Monitor:** `dashboard_state.json` includes `event_stream_file_size`; alert at 80% disk usage

---

## 16. Migration Strategy

### Guiding Principle: Additive-then-Prune

Never delete old code until new code is proven in production. Always add → validate → prune, never prune → add.

### Stage 1: Foundation (Batches 2–4) — Trader Decomposition
- Extract lifecycle, state, cycle from `trader.py`
- Keep all existing imports working via proxy delegation
- No folder restructuring yet
- Estimated timeline: 3 batches

### Stage 2: Package Consolidation (Batches 5–7) — Module Grouping
- Create `polymarket/market_data/`, `polymarket/alpha/`, `polymarket/risk/`
- Move files into new packages; keep re-export shims at old paths for 2 batches
- Remove re-export shims after all importers are updated
- Estimated timeline: 3 batches

### Stage 3: Schema Registry (Batch 9)
- Create `schema/` package
- All new event emissions use dataclasses from registry
- Existing emissions continue working; migrate incrementally
- Estimated timeline: 1 batch + incremental migration

### Stage 4: Interface Layer (Batch 10+)
- Add protocol definitions
- Make existing implementations conform to protocols
- Replace direct class imports with protocol typing where beneficial
- Estimated timeline: 2-3 batches

### Stage 5: Tools Reorganization (Batch 8)
- Move flat `tools/` into subdirectories
- Update all test imports
- This is safe to do in one batch since tools have no runtime coupling
- Estimated timeline: 1 batch

### Migration Anti-Patterns (Forbidden)

- Big-bang refactors that touch 10+ files in one commit
- Deleting old import paths before confirming all consumers updated
- Moving files and changing logic in the same commit
- Schema version changes without backwards compatibility plan
- Reorganizing `runtime/` data directories while a live paper session is running

---

## 17. Success Criteria

### Architecture Success Criteria

| Criterion | Metric | Target |
|-----------|--------|--------|
| `trader.py` size | Lines | ≤ 1,000 |
| Module cohesion | Max lines per module | ≤ 500 (except trader.py during migration) |
| Circular imports | Count | 0 |
| Forbidden import violations | Count | 0 |
| Test coverage (existing tests pass) | Pass rate | 100% (excluding pre-existing known failures) |
| Paper runtime boot time | Seconds | ≤ 5 |
| Paper cycle completion | Cycles in 10 min | ≥ 8 |
| JSONL event emission | Events per cycle | ≥ 30 |
| Schema validation errors | Count per session | 0 |
| Dashboard staleness | Age when displayed | < 120 seconds |

### Runtime Safety Success Criteria (Non-Negotiable)

| Criterion | Standard |
|-----------|---------|
| Paper/live separation | Paper path NEVER calls live client.py |
| OrderIntent gate | All entries/exits pass validation |
| Risk manager | All sizing goes through canonical `risk_manager.py` |
| No live orders from paper | Zero calls to CLOB order endpoints in paper mode |
| Clean SIGTERM shutdown | All threads join within 5 seconds |
| Exception containment | Runtime loop continues after cycle exception |
| Log budget | < 150 MB/day compressed |

### Research Success Criteria

| Criterion | Standard |
|-----------|---------|
| Replay reproducibility | Given same event stream, replay produces same result |
| Schema version coverage | All event types have versioned schema |
| Offline/runtime isolation | Zero tool imports from `polymarket/execution/live/` |
| Phase boundary enforcement | Research findings require explicit task scope to reach runtime |

### Long-Term Success Vision (2+ Years)

When this architecture is complete:

1. A new contributor can understand the system by reading `main.py` → `orchestration/trader.py` → `interfaces/` in under 2 hours
2. Any module can be unit-tested in isolation without mocking 13,000 lines of collaborator code
3. Adding a new event type requires: create `schema/v1/new_event.py`, register it, emit it — 3 files, no existing file changes
4. Adding a new offline analysis tool requires: create `tools/analytics/my_tool.py`, read JSONL, write report — zero runtime changes
5. The dashboard always reflects real runtime state within 60 seconds
6. A 24/7 paper session runs for 7 days without operator intervention, with automatic compaction and Telegram health alerts

---

## Appendix: Current Module Inventory

| Module | Lines | Responsibility | Target Package |
|--------|-------|---------------|----------------|
| `polymarket/trader.py` | 13,125 | God Object | Decompose → orchestration/ |
| `polymarket/trader_presentation.py` | 206 | UI formatting | orchestration/ (done) |
| `polymarket/signal.py` | 664 | Signal logic | alpha/ |
| `utils/position_tracker.py` | 828 | Position state | utils/ (stable) |
| `utils/risk_manager.py` | 577 | Risk policy | utils/ (stable) |
| `polymarket/order_intent.py` | 72 | Entry/exit guard | risk/ |
| `polymarket/bankroll_tiers.py` | — | Tier hysteresis | risk/ |
| `polymarket/position_sizing.py` | — | Sizing | risk/ |
| `polymarket/regime_diagnostics.py` | — | Regime | alpha/ |
| `polymarket/probability_model.py` | — | Probability | alpha/ |
| `polymarket/expected_value.py` | — | EV | alpha/ |
| `polymarket/gamma_fetcher.py` | — | Discovery | market_data/ |
| `polymarket/market_feed.py` | — | Binance feed | market_data/ |
| `polymarket/oracle_price_feed.py` | — | Oracle/PTB | market_data/ |
| `polymarket/virtual_ptb.py` | — | Paper PTB | market_data/ + execution/paper/ |
| `polymarket/client.py` | — | CLOB live | execution/live/ |
| `polymarket/order_manager.py` | — | Order plans | execution/live/ |
| `polymarket/position_manager.py` | — | Fill reconcile | reconciliation/ |
| `utils/runtime_event_stream.py` | — | JSONL writer | utils/ (stable) |
| `utils/display.py` | — | Terminal UI V2 | utils/ (stable) |
| `tools/` (70+ files) | — | Offline tools | tools/research/ replay/ analytics/ etc. |

---

*This document is a design artifact only. No code changes are authorized by this document. Each batch requires a separate scoped implementation task with explicit approval.*
