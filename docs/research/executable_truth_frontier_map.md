# Executable Truth Frontier Map

Date: 2026-05-26

Scope: read-only research map from `SIGNAL_MODE` to `EXECUTABLE_TRUTH`. No code. No runtime change. No replay. No live.

## Executive Verdict

```text
CURRENT_STATE: SIGNAL_MODE / EVIDENCE_FARMING
FRONTIER: EXECUTABLE_TRUTH_NOT_REACHED
EXECUTABLE_PNL: BLOCKED
HERMES_INGEST: SIGNAL_AND_BLOCKER_EVIDENCE_ONLY
```

Current evidence can explain paper signal behavior and executable blockers. It cannot prove executable profitability.

The path forward is not "turn on executable PnL"; it is a staged truth migration:

```text
SIGNAL_MODE
-> offline executable overlay
-> JSONL truth layer
-> growth readiness
-> EXECUTABLE_TRUTH
```

## Inputs

- `docs/research/runtime_executable_truth_source_audit.md`
- `docs/research/offline_executable_truth_ledger_audit.md`
- `docs/research/path_truth/path_truth_multiday_coverage_monitor.md`

## Current Truth State

| Field | Current State | Evidence | Frontier Status |
|---|---|---|---|
| `signal_pnl` | available | alias of `trade_journal.payload.pnl_usdc` | usable now |
| `dust_zone` | derivable | `entry_price`, `size/shares`, and assumed MOS | usable as blocker evidence |
| `executable_minimum_met` | derivable | `shares >= MOS` and `entry_price * shares >= entry_price * MOS` | usable as assumed-MOS blocker evidence |
| `executable_candidate` | partial | schema can represent it, but latest sampled rows have zero candidates | waiting for larger paper sizes and stronger microstructure joins |
| `executable_pnl` | blocked | no sampled trade clears MOS 1/3/5; executable approval truth absent | not ingestible as PnL |

Current sampled ledger facts from the offline audit:

| Metric | Value |
|---|---:|
| sampled closes | 77 |
| closes below `mos=1` | 77 / 77 |
| closes below `mos=3` | 77 / 77 |
| closes below `mos=5` | 77 / 77 |
| direct trade/execution/decision/research joins | 77 / 77 |
| direct path-truth joins by `(run_id, paper_trade_replay_key)` | 0 / 77 |
| proxy path-truth joins | 60 / 77 |

## Frontier Blockers

### Minimum Size

Current paper trades are still tiny dust trades. They do not clear even `mos=1`.

Impact:

- `signal_pnl` remains valid as paper signal evidence.
- `executable_pnl` remains null.
- Any positive session or side bucket remains a signal candidate, not executable edge.

### MOS Assumption

The current MOS values are research assumptions:

```text
mos = 1 share
mos = 3 shares
mos = 5 shares
```

The docs state no authoritative local Polymarket `min_order_size`, `minimum_order_size`, or `mos` metadata is present.

Impact:

- MOS can safely block claims.
- MOS cannot safely approve executable PnL.

### Path Truth Proxy Joins

Path truth has useful checkpoint evidence, but it is not directly linked to trades by `(run_id, paper_trade_replay_key)`.

Current path-truth gate:

```text
EARLY_RESEARCH_GATE: 2 / 3 completed dates
IMPLEMENTATION_GATE: 2 / 7 completed dates
```

Known missing path fields:

- `quote_age_ms`
- `candidate_id`
- `decision_id`

Impact:

- Path truth can describe fast close and coverage health.
- Path truth cannot approve executable PnL until direct identity joins exist.

### Missing Fill Truth

Runtime paper fills are simulated. The evidence does not prove live minimum-order acceptance, queue priority, fill probability, or adverse-selection cost.

Impact:

- No `EXECUTABLE_PNL_APPROVED`.
- No live-readiness inference.

### Missing Cancel Truth

Cancel submit/ack and cancel latency truth are not available as a validated executable lifecycle.

Impact:

- Final derisk and late-fill risk remain unproven.
- Executable truth cannot include cancel realism yet.

### Missing Partial Fill Truth

Depth can be observed, but actual partial fill behavior is not proven.

Impact:

- Top-of-book depth can reject weak candidates.
- It cannot approve executable PnL without fill mechanics.

## Frontier Roadmap

### Stage A: Research Only

Status:

```text
ACTIVE
```

Allowed actions:

- label `pnl_usdc` as `signal_pnl`
- label current paper rows as `SIGNAL_MODE`
- derive `dust_zone` and `executable_minimum_met=false`
- keep Hermes executable PnL blocked
- continue path-truth evidence farming

Blocked actions:

- no runtime wiring
- no policy changes
- no live claims
- no executable profitability claims

Exit criteria:

- stable research docs agree on field meanings
- Hermes labels are unambiguous
- path truth reaches at least `EARLY_RESEARCH_GATE`

### Stage B: Offline Overlay

Status:

```text
NEXT SAFE FRONTIER
```

Purpose:

Build a docs/report-only overlay from existing JSONL that separates signal evidence from executable blocker evidence.

Required properties:

- read-only inputs
- no replay execution
- no runtime feed-back
- per-trade classifications:
  - `SIGNAL_ONLY`
  - `DUST_ZONE`
  - `EXECUTABLE_MIN_REJECT`
  - `EXECUTABLE_CANDIDATE`
  - `EXECUTABLE_PNL_APPROVED`
  - `BLOCKED_N_A`

What it unlocks:

- consistent Hermes blocker table
- repeatable signal-vs-executable separation
- daily visibility into whether any row ever clears assumed MOS

What remains blocked:

- runtime executable PnL
- live readiness
- policy enforcement

### Stage C: JSONL Truth Layer

Status:

```text
BLOCKED_BY_GATES_AND_CONTRACT
```

Purpose:

Add canonical runtime observability fields after the offline contract is stable.

Candidate future fields:

- `signal_pnl`
- `dust_zone`
- `executable_minimum_met`
- `executable_classification`
- `executable_pnl`
- `executable_pnl_status`
- `mos_assumption`
- `mos_source`
- `dynamic_min_cost`
- direct path-truth trade key

Prerequisites:

- explicit implementation task
- field contract freeze
- path truth gate progress
- fail-soft JSONL semantics
- tests for missing fields and paper/live labels

What it unlocks:

- canonical row-level truth layer
- fewer proxy joins
- safer downstream dashboards

What remains blocked:

- executable PnL approval if trade size remains below MOS
- executable PnL approval if fill/cancel/partial-fill truth remains absent

### Stage D: Growth Readiness

Status:

```text
FUTURE / NOT PROMOTED
```

Purpose:

Determine whether larger paper sizing can produce executable candidates without violating risk constraints.

Required before any growth claim:

- paper evidence at or above practical MOS
- direct joins across trade, execution, path, and microstructure evidence
- quote freshness truth
- depth sufficiency
- spread cost visibility
- partial fill and cancel truth
- no live-readiness blockers
- explicit risk review

What it unlocks:

- possible `EXECUTABLE_CANDIDATE` rows
- eventual review of `EXECUTABLE_PNL_APPROVED`

What remains blocked:

- Growth Mode promotion
- live mode
- strategy/risk/execution changes without separate approval

## What Unlocks Executable PnL?

Executable PnL unlock requires all of these:

1. A trade clears authoritative or explicitly assumed MOS:

```text
shares >= MOS
notional >= entry_price * MOS
```

2. MOS source is labeled:

```text
market_metadata
config
conservative_assumption
```

3. Join confidence is DIRECT or STRONG across:

- trade open
- trade close
- execution events
- path truth
- decision/research context

4. Microstructure truth is available:

- quote age or quote staleness
- spread or spread state with costability
- top-depth support
- liquidity/book state

5. Fill/cancel realism is not missing:

- fill truth
- partial fill truth
- cancel submit/ack truth where relevant
- late-fill/ghost-inventory guard visibility

6. Paper/live truth label is explicit:

```text
paper_simulated
live_observed
proxy
unknown
```

Until then:

```text
executable_pnl = null
executable_pnl_status = BLOCKED
```

## What Stays Blocked?

Blocked now:

- `EXECUTABLE_PNL_APPROVED`
- executable profitability
- live readiness
- Growth Mode promotion
- policy enforcement from offline labels
- path-truth-based executable approval
- fill realism claims
- cancel realism claims
- partial-fill risk claims as measured truth

Conditionally available now:

- `signal_pnl`
- `dust_zone`
- `executable_minimum_met=false`
- `EXECUTABLE_MIN_REJECT`
- `SIGNAL_ONLY`
- `SAFE_BLOCKER_ONLY`

## Hermes Ingest Rules

Hermes may ingest:

| Evidence | Hermes Label |
|---|---|
| `pnl_usdc` | `signal_pnl` |
| current paper rows | `SIGNAL_ONLY` |
| current paper rows below MOS | `DUST_ZONE` |
| minimum failure | `EXECUTABLE_MIN_REJECT` |
| executable PnL | `N_A_BLOCKED` |
| path truth today | `PROXY_ONLY_FOR_EXECUTABLE_JOIN` |
| runtime truth | `PARTIAL_RAW_EVIDENCE` |

Hermes must not ingest:

- dust PnL as executable PnL
- signal PnL as live profitability
- assumed MOS as exchange-confirmed MOS
- path truth proxy joins as direct truth
- any current row as executable approved
- any current state as Growth Mode ready

Recommended Hermes summary:

```text
SIGNAL_MODE: AVAILABLE
DUST_ZONE: DERIVABLE
EXECUTABLE_MINIMUM_MET: DERIVABLE_FALSE_FOR_CURRENT_SAMPLE
EXECUTABLE_CANDIDATE: ZERO_CURRENT_ROWS
EXECUTABLE_PNL: BLOCKED_N_A
LIVE_READINESS: NO
```

## Final Map

```text
SIGNAL_MODE
  available:
    - pnl_usdc -> signal_pnl
    - TP/SL outcome
    - entry/exit price
    - size/shares
    - session and lifecycle context

  frontier:
    - derive dust_zone
    - derive executable_minimum_met
    - label executable_min_reject

EXECUTABLE_TRUTH
  blocked by:
    - minimum size failure
    - assumed MOS
    - path truth proxy joins
    - missing fill truth
    - missing cancel truth
    - missing partial fill truth

  unlock path:
    Stage A research only
    -> Stage B offline overlay
    -> Stage C JSONL truth layer
    -> Stage D growth readiness
```

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Tests: not run; docs-only/read-only frontier map.
