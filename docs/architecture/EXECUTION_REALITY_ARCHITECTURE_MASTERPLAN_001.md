# EXECUTION_REALITY_ARCHITECTURE_MASTERPLAN_001

**Date:** 2026-06-30
**Status:** ARCHITECTURE ONLY — No code changes. No commits. Design document.
**Scope:** Long-term execution intelligence architecture for the Adaptive Prediction Market Platform
**Baseline:** Post-`08ae0a70` (Executable Sizing Reality Audit complete). Paper validated. Zero paper fills.
**Supersedes/Extends:** `QUANT_ARCHITECTURE_MASTER_PLAN_001.md` (structural decomposition plan, not replaced)
**Prerequisite reading:** `QUANT_ARCHITECTURE_MASTER_PLAN_001.md`, `QUANT_LIFECYCLE_INVENTORY_ENGINE.md`, `POLYMARKET_EXECUTABLE_SIZING_REALITY_AUDIT_001.md`

---

## Executive Summary

The current system is a **Signal → Trade** scalper: one signal, one decision, one order attempt, no inventory management. This architecture was correct for Phase 1 (observability-first, evidence-collection, no fills yet). It is not adequate for Phase 3 and beyond.

Real Polymarket BTC/ETH 5-minute traders do not think in one-shot trades. They:
- Build positions across multiple entries within a 5-minute window
- Hold inventory across market phases as probability evolves
- Add to profitable inventory when edge and liquidity agree
- Reduce and harvest as the window closes
- Run simultaneous positions across BTC and ETH
- Manage buying power, exposure, and risk budget dynamically — not as isolated per-trade Kelly calculations

This document designs the **target execution intelligence architecture** required to support that behavior. It is a seven-layer pipeline:

```
Market Intelligence
  → Opportunity Intelligence
    → Execution Intelligence
      → Portfolio Intelligence
        → Execution
          → Replay 2.0
            → Learning Engine
```

**Critical grounding facts from current evidence:**
- **Zero paper fills.** The fill path, PnL accounting, and position tracking have never been exercised. No architecture milestone may claim execution readiness until this is proven.
- **`max_active_positions_per_market=1`, `max_entries_per_market=1`.** These settings structurally forbid the multi-entry inventory model this architecture targets. Lifting them is a gated dependency for Phases 3–4.
- **30-minute loss cluster pause is incompatible** with continuous operation. All risk responses in this architecture use adaptive sizing, RiskMode degradation, and capital reallocation — never wall-clock pauses.
- The **God Object** (`polymarket/trader.py`, 13,125 lines) must be decomposed (per `QUANT_ARCHITECTURE_MASTER_PLAN_001.md`) before this intelligence layer can be modularly implemented. This document defines what to build; that document defines where to put it.

---

## 1. Current Architecture

### 1.1 Current Flow

```
main.py --mode paper
  └─► PolymarketTrader (trader.py — 13,125 lines, God Object)
        ├─ GammaFetcher → active BTC/ETH markets
        ├─ MarketAvailabilityEngine → epoch guard
        ├─ OraclePriceFeed + MarketFeed → external price
        ├─ CLOB orderbook fetch → best bid/ask/spread
        ├─ signal.py → Counter-Momentum + Markov Bounds
        ├─ probability_model.py → estimated P(YES), P(NO)
        ├─ expected_value.py → EV (edge = P_estimate - price)
        ├─ RiskManager → risk plan (kelly, bankroll tier, multipliers)
        ├─ OrderManager → build_order_plan (single order, single side)
        ├─ validate_order_intent → guard rail
        ├─ VirtualPTB (paper) → simulate fill
        └─ QuantEventLogger → JSONL
```

### 1.2 Current Decision Model

```
ENTER (one position, one side, one price)
  or
SKIP (reason)
```

No lifecycle awareness. No inventory state. No multi-entry. No position management after entry.

### 1.3 Current Module Strengths (Carry Forward)

| Module | Strength |
|--------|----------|
| MarketAvailabilityEngine | Epoch-aware market guard, exact-slug fallback |
| OrderIntent validation | Strict entry/exit guard; never bypass |
| RiskManager | Risk mode ladder, bankroll tiers, Kelly chain |
| BankrollTierManager | 13-tier hysteresis, family/profile segmentation |
| QuantEventLogger | Event-driven JSONL, run-scoped telemetry |
| VirtualPTB | Paper fill simulation |
| RuntimeOwnership | Duplicate-process guard |
| ExceptionObservability | Crash-resilient runtime loop |

### 1.4 Current Blockers for Target Architecture

| Blocker | Severity | Gating |
|---------|----------|--------|
| Zero paper fills — fill path unverified | CRITICAL | Blocks all execution intelligence phases |
| God Object trader.py | CRITICAL | Must decompose before modular impl |
| max_active_positions=1, max_entries=1 | HIGH | Must lift before inventory engine |
| 30-min loss cluster pause | HIGH | Must replace with adaptive sizing |
| No position inventory state machine | HIGH | No basis for Build/Add/Reduce decisions |
| No opportunity queue | HIGH | No cross-market capital allocation |
| No capital allocation engine | HIGH | Kelly per-trade ≠ portfolio capital flow |
| CLOB $0.10 minimum pre-submission check missing | MEDIUM | Required before live |

---

## 2. Target Architecture

### 2.1 Vision

A **continuous, inventory-aware, portfolio-level prediction market platform** that:

1. Discovers market opportunities early (pre-open, epoch boundary scan)
2. Ranks and queues opportunities by edge, liquidity, time horizon, and capital fit
3. Builds inventory across multiple entries within the 5-minute window
4. Manages open inventory through hold, add, reduce, and harvest decisions
5. Allocates capital portfolio-wide against a shared risk budget, not per-trade Kelly in isolation
6. Records every decision transition for offline replay and learning
7. Learns from replay to improve future execution parameters

### 2.2 Target Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    MARKET INTELLIGENCE                       │
│  GammaFetcher · MarketAvailabilityEngine · OraclePriceFeed  │
│  CLOB WebSocket · MarketWindowTracker · EpochGuard           │
└──────────────────────────┬──────────────────────────────────┘
                           │ market snapshots
┌──────────────────────────▼──────────────────────────────────┐
│                 OPPORTUNITY INTELLIGENCE                      │
│  SignalEngine · ProbabilityModel · ExpectedValueEngine       │
│  RegimeDiagnostics · LiquidityScorer · SpreadQualityGate     │
└──────────────────────────┬──────────────────────────────────┘
                           │ scored opportunities
┌──────────────────────────▼──────────────────────────────────┐
│                    OPPORTUNITY QUEUE                         │
│  Rank · Deduplicate · Filter · Compete for capital           │
└──────────────────────────┬──────────────────────────────────┘
                           │ ranked queue
┌──────────────────────────▼──────────────────────────────────┐
│                 EXECUTION INTELLIGENCE                        │
│  ExecutionPlanner · InventoryEngine · LadderEngine           │
│  PositionLifecycleEngine · OpportunityThrottle               │
└──────────────────────────┬──────────────────────────────────┘
                           │ execution plans
┌──────────────────────────▼──────────────────────────────────┐
│                 PORTFOLIO INTELLIGENCE                        │
│  CapitalAllocationEngine · BuyingPowerManager               │
│  ExposureController · RiskBudgetTracker                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ allocated + gated orders
┌──────────────────────────▼──────────────────────────────────┐
│                      EXECUTION LAYER                         │
│  OrderIntentValidator · OrderManager · VirtualPTB (paper)   │
│  CLOBClient (live) · FillTracker · PositionTracker           │
└──────────────────────────┬──────────────────────────────────┘
                           │ events
┌──────────────────────────▼──────────────────────────────────┐
│                       REPLAY 2.0                             │
│  ExecutionReplayEngine · PlanVsActualReconciler              │
│  InventoryReplayAnalyzer · MFE/MAE/DecayTracker              │
└──────────────────────────┬──────────────────────────────────┘
                           │ replay evidence
┌──────────────────────────▼──────────────────────────────────┐
│                     LEARNING ENGINE                          │
│  ParameterFeedback · ThrottleCalibrator · AlphaDecayMonitor │
│  RegimeStrategyRouter · RoadmapGatePromoter                  │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Design Principles (Beyond QUANT_ARCHITECTURE_MASTER_PLAN_001.md)

| Principle | Meaning |
|-----------|---------|
| **Continuous operation** | Runtime never pauses for risk events — risk responds through sizing and mode |
| **Inventory-first** | Every execution decision is relative to current inventory state, not signal-in-vacuum |
| **Opportunity competition** | Capital flows to highest-edge opportunity — not first-seen, not round-robin |
| **Evidence-gated promotion** | Each lifecycle phase requires paper evidence before activation |
| **Adaptive risk only** | Loss events → RiskMode degradation + size reduction. Never wall-clock pauses. |
| **Replay completeness** | Every plan, intent, and execution outcome is recorded for offline replay |
| **Portfolio-level capital** | Risk budget and buying power are portfolio quantities, not per-market silos |

---

## 3. Execution Intelligence Layer

### 3.1 Responsibilities

The Execution Intelligence layer transforms a **ranked opportunity** into a **concrete execution plan** that respects:
- Current inventory state (what we already hold)
- Available buying power (what capital we can deploy)
- Risk mode (NORMAL / DEFENSIVE / MICRO_RECOVERY / LOCKDOWN)
- Market window phase (OPENING_SCAN / ACTIVE_INVENTORY_TRADING / etc.)
- Lifecycle state of the position (Probe / Build / Add / Reduce)
- Execution constraints (CLOB $0.10 min, spread, time remaining)

It does **not** decide which opportunity to pursue (Opportunity Queue does that) and does **not** allocate capital (Portfolio Intelligence does that). It converts a qualified opportunity + capital allocation into a sized, timed, prioritized order ladder.

### 3.2 Inputs

| Input | Source |
|-------|--------|
| Opportunity snapshot | Opportunity Intelligence |
| Capital budget for this opportunity | Portfolio Intelligence / Capital Allocation Engine |
| Current position inventory | Inventory Engine |
| Market window phase | MarketWindowTracker |
| Risk mode | RiskManager |
| CLOB orderbook state | Market Intelligence |
| Time remaining in epoch | EpochGuard |

### 3.3 Outputs

| Output | Consumer |
|--------|----------|
| Execution plan (ladder of intents) | OrderIntentValidator → OrderManager |
| Plan metadata (rationale, tier, risk) | QuantEventLogger (JSONL) |
| Position lifecycle transition | InventoryEngine |
| Execution feedback | OpportunityQueue (throttle) |

### 3.4 Internal Modules

| Module | Purpose |
|--------|---------|
| `ExecutionPlanner` | Converts opportunity + capital into a laddered plan |
| `LadderEngine` | Produces Probe/Base/Add order sizes respecting CLOB minimum |
| `InventoryEngine` | Tracks current position state machine |
| `PositionLifecycleEngine` | Governs valid transitions between lifecycle states |
| `OpportunityThrottle` | Adaptive throttle: reduces size or skips, never pauses |
| `ExecutionPlanSerializer` | Serializes plans to JSONL for Replay 2.0 |

---

## 4. Portfolio Intelligence Layer

### 4.1 Inventory

**What we own, priced at current mid.**

The Inventory Engine (see Section 8) maintains:
- `positions: dict[market_id, InventoryRecord]`
- `total_exposure_dollars: float`
- `total_exposure_pct_of_bankroll: float`
- `exposure_by_asset: dict[str, float]` (BTC vs ETH)
- `unrealized_pnl: float`
- `mark_price_by_position: dict[str, float]`

Inventory is the ground truth for all execution decisions. No order may be placed without consulting inventory state first.

### 4.2 Buying Power

**What capital is available to deploy right now.**

```
buying_power = bankroll - (total_deployed_collateral + reserved_buffer)
reserved_buffer = bankroll × reserved_pct  # tier-dependent, e.g. 20%
```

Buying power is a live number updated after every fill or position change. The Capital Allocation Engine draws from buying power, not directly from bankroll.

### 4.3 Exposure

**How much of the bankroll is at risk across all open positions.**

Three exposure controls:
1. **Per-position cap:** `max_exposure_per_position = bankroll × tier.max_market_exposure_pct`
2. **Per-asset cap:** `max_exposure_btc = bankroll × 0.15`, same for ETH (prevents concentration)
3. **Portfolio cap:** `max_total_exposure = bankroll × global_portfolio_cap` (e.g. 25% at T0)

Any execution plan that would breach any cap is reduced to fit or rejected.

### 4.4 Risk Budget

**The dynamic quantity governing how aggressively capital is deployed this session.**

```python
@dataclass
class RiskBudget:
    session_loss_dollars: float      # cumulative realized losses this session
    session_win_dollars: float       # cumulative realized gains this session
    daily_loss_pct: float            # as fraction of session-start bankroll
    consecutive_losses: int          # recent loss streak
    risk_mode: RiskMode              # NORMAL / DEFENSIVE / MICRO_RECOVERY / LOCKDOWN
    risk_multiplier: float           # 1.0 / 0.5 / 0.25 / 0.0
    budget_remaining_pct: float      # fraction of daily drawdown cap not yet consumed
```

Risk budget is the **shared signal** consumed by both the Capital Allocation Engine and the Opportunity Throttle. When the budget degrades, all new plans receive proportionally smaller capital allocations.

### 4.5 Capital Allocation Engine

The Capital Allocation Engine answers one question: **"Given my current risk budget, buying power, and opportunity queue, how much capital should I allocate to each opportunity?"**

This replaces the single-Kelly-output model. See Section 9 for full design.

---

## 5. Position Lifecycle Engine

### 5.1 Reconciling Two Vocabularies

This project has two complementary lifecycle vocabularies that operate on different axes:

**Market Window Lifecycle** (from `QUANT_LIFECYCLE_INVENTORY_ENGINE.md`) — governs WHEN actions are permitted in a 5-minute epoch:

| Phase | Window | Gate |
|-------|--------|------|
| `OPENING_SCAN` | 0–35s | No entries |
| `ACTIVE_INVENTORY_TRADING` | 35–240s | Probe + Build + Add allowed |
| `PROFIT_MANAGEMENT` | 240–270s | Reduce only |
| `FINAL_DERISK` | 270–300s | Exit only |
| `CLOSED_OR_UNSAFE` | Any unsafe state | No action |

**Position Lifecycle States** (this document) — governs HOW a position evolves from first intent to close:

| State | Meaning | Permitted Actions |
|-------|---------|-------------------|
| `PROBE` | First tiny order placed to verify fill path | None until filled |
| `BUILD` | Probe filled; main position being established | Add base orders |
| `ADD` | Position profitable, EV still positive, window open | Add up to cap |
| `HOLD` | Position open, no new adds warranted | Monitor only |
| `REDUCE` | Window closing or EV deteriorating | Partial sell orders |
| `MERGE` | Multiple partial fills collapsed into single inventory record | Internal reconciliation |
| `REDEEM` | Market resolved; token redeemable; await settlement | Submit redemption |
| `EXIT` | Active sell at current mid before settlement | Submit exit sell |
| `CLOSED` | Position fully liquidated or redeemed | No action |

**The relationship:** Market Window Phase **gates** which Position Lifecycle States are valid at any moment:

```
OPENING_SCAN           → only PROBE allowed, and only for fill-path verification
ACTIVE_INVENTORY_TRADING → PROBE → BUILD → ADD → HOLD all valid
PROFIT_MANAGEMENT      → HOLD → REDUCE valid; no new PROBE/BUILD/ADD
FINAL_DERISK           → REDUCE → EXIT; all remaining inventory must exit or be monitored
CLOSED_OR_UNSAFE       → CLOSED only; no position transitions
```

### 5.2 State Machine

```
          ┌──────────────────────────────────────────────────┐
          │              Position Lifecycle                   │
          │                                                   │
          │   [order placed]            [probe filled]        │
  START──►  PROBE ────────────────────► BUILD                │
          │   │                           │                   │
          │   │ [order rejected]          │ [add condition]   │
          │   ▼                           ▼                   │
          │  CLOSED           ADD ◄──────────────────►HOLD   │
          │                   │                       │       │
          │                   │ [reduce condition]    │       │
          │                   ▼                       ▼       │
          │                REDUCE ──────────────► EXIT        │
          │                   │                   │           │
          │                   │ [market resolves] │           │
          │                   ▼                   │           │
          │                REDEEM                 │           │
          │                   │                   │           │
          │                   └──────► CLOSED ◄───┘           │
          └──────────────────────────────────────────────────┘
```

### 5.3 Lifecycle Transition Rules

**PROBE → BUILD:**
- Probe fill confirmed in VirtualPTB (paper) or CLOB fill tracker (live)
- Position tracker record created
- `InventoryRecord.state` set to `BUILD`

**BUILD → ADD:**
- Position P&L ≥ 0 (not underwater)
- Market window phase ≤ `ACTIVE_INVENTORY_TRADING`
- Risk mode is NORMAL or DEFENSIVE
- Remaining time ≥ 120s (add cutoff gate)
- Capital available for add within per-market and portfolio caps
- Spread ≤ 4%

**ADD → HOLD:**
- Max adds reached (tier-defined), OR
- Remaining time < 120s, OR
- Risk mode degraded to MICRO_RECOVERY, OR
- No further capital within cap

**HOLD → REDUCE:**
- Market window enters `PROFIT_MANAGEMENT`, OR
- Position P&L < stop-loss threshold, OR
- EV estimate turns negative

**REDUCE → EXIT:**
- Remaining time < 30s, OR
- Market window enters `FINAL_DERISK`, OR
- Risk mode = LOCKDOWN, OR
- Forced exit triggered

**BUILD/ADD/HOLD → REDEEM:**
- Market resolved (settlement timestamp passed)
- Position is in YES or NO with known outcome
- Token balance > 0

**Any → CLOSED_OR_UNSAFE:**
- Reconciliation unsafe (from `PositionTracker`)
- Orderbook stale
- RiskMode = LOCKDOWN

### 5.4 Required Position Record Fields

```python
@dataclass
class InventoryRecord:
    position_id: str               # uuid
    market_id: str
    asset: str                     # BTC or ETH
    side: str                      # YES or NO
    token_id: str
    lifecycle_state: str           # PROBE / BUILD / ADD / HOLD / REDUCE / EXIT / REDEEM / CLOSED
    market_window_phase: str       # current epoch phase
    entries: list[EntryRecord]     # all fills contributing to this position
    total_shares: float            # sum of all fills
    average_cost_basis: float      # weighted average entry price
    current_mark_price: float      # latest mid from orderbook
    unrealized_pnl_dollars: float  # (mark - avg_cost) × shares
    add_count: int                 # how many adds have occurred
    max_adds_allowed: int          # tier-defined
    stop_loss_threshold: float     # pct of position cost basis
    opened_at: str                 # UTC ISO
    last_updated_at: str           # UTC ISO
    run_id: str
```

---

## 6. Execution Planner

### 6.1 Plan Generation

The Execution Planner receives a qualified opportunity and produces an `ExecutionPlan`:

```python
@dataclass
class ExecutionPlan:
    plan_id: str
    opportunity_id: str
    market_id: str
    asset: str
    side: str
    token_id: str
    lifecycle_intent: str          # PROBE / BUILD_BASE / ADD / REDUCE / EXIT
    orders: list[OrderIntent]      # concrete order sequence
    total_notional: float          # sum of order sizes
    capital_budget: float          # what CAE allocated
    risk_mode_at_plan_time: str
    market_window_phase_at_plan_time: str
    time_remaining_at_plan_time: float
    plan_rationale: dict           # edge, ev, spread, liquidity snapshot
    created_at: str
    expiry: str                    # orders expire if not placed within N seconds
```

### 6.2 Laddering

The ladder is a sequence of price-size pairs ordered by priority:

```
Probe tier:   1 × $0.10 at best_ask          (fill-path verification only)
Base tier:    1–3 × kelly_sized at best_ask  (core exposure)
Add tier:     1 × 50% of base at best_ask    (reinforcement if profitable)
```

Ladder construction rules:
- All orders must be ≥ CLOB minimum ($0.10)
- All orders must clear dynamic minimum shares override (≥ 1 share)
- Base size = min(kelly_output × risk_mode_multiplier, capital_budget, per_market_cap)
- Add size = min(50% of base, remaining_capital_budget, 1 add per lifecycle state)
- No order is placed if spread > 4% (spread quality gate)
- No order is placed if time_remaining < 90s (time gate)

### 6.3 How Adds Work

An "add" is a new entry into an existing open position when all of the following agree:
1. Position is in `ADD`-eligible lifecycle state
2. Current P&L is non-negative
3. EV estimate is still positive on the current mark price
4. Market window phase ≤ `ACTIVE_INVENTORY_TRADING`
5. Risk mode ≤ DEFENSIVE
6. `add_count < max_adds_allowed` for the bankroll tier
7. Capital available: `capital_budget_remaining > add_min_size`
8. Time remaining ≥ 120s

Add sizing: `add_size = base_size × 0.50`, further reduced by risk mode multiplier.

Add throttle: after any add, the next add requires an additional evidence check (spread quality, EV recalculation). This prevents blind averaging.

### 6.4 How Exits Work

The Execution Planner generates exit orders in two modes:

**Managed exit (REDUCE):** Partial sell at current mid when P&L ≥ 0 and window is closing.
```
exit_size = total_shares × reduce_fraction  # e.g., 0.50 at PROFIT_MANAGEMENT start
exit_price = best_bid - 0.01              # small concession to ensure fill
```

**Forced exit (EXIT):** Full position sell when time forces closure or risk triggers.
```
exit_size = total_shares
exit_price = best_bid - 0.02              # larger concession for speed
```

**Paper exit:** VirtualPTB simulates fill at mid. Records exit PnL to position record.
**Live exit:** CLOB SELL order submitted via CLOBClient. Fill tracked by FillTracker.

Exit orders bypass the Opportunity Queue — they are priority-routed directly through OrderIntentValidator.

---

## 7. Opportunity Queue

### 7.1 Design

The Opportunity Queue is a **live ranked priority queue** of scored market opportunities competing for capital. It replaces the current serial scan (BTC first, then ETH) with a unified cross-market capital competition.

```python
@dataclass
class QueuedOpportunity:
    opportunity_id: str
    market_id: str
    asset: str
    side: str
    lifecycle_intent: str          # PROBE / BUILD / ADD
    composite_score: float         # ranking score
    edge: float
    ev: float
    probability: float
    confidence: float
    spread: float
    liquidity_depth: float
    time_remaining: float
    regime: str
    enqueued_at: str
    expires_at: str                # auto-expire after 1 cycle if not consumed
```

### 7.2 Ranking

Composite score for ranking:

```
score = edge × ev_weight × confidence × liquidity_factor × time_factor × regime_factor
```

Weights (design-time, tunable by Learning Engine):
- `ev_weight`: linear with EV (0 at EV=0, 1.0 at EV=0.15+)
- `liquidity_factor`: 1.0 if L1 depth > $100, scaling to 0.25 below $20
- `time_factor`: 1.0 at 240s remaining, decays to 0.0 at 90s remaining
- `regime_factor`: 1.2× in favorable regime, 0.7× in adverse regime

### 7.3 Capital Competition

When multiple opportunities are queued simultaneously (e.g., both BTC and ETH have edge):

1. Rank all opportunities by composite score
2. Capital Allocation Engine sets a budget for the top-N opportunities
3. Budget is distributed proportionally by score: `alloc_i = total_budget × (score_i / sum_scores)`
4. Minimum allocation = CLOB minimum ($0.10); opportunities below minimum are deferred to next cycle
5. Per-market and per-asset exposure caps applied after allocation

**Hard rule:** No opportunity receives capital if it would push total portfolio exposure above the portfolio cap, regardless of its score.

### 7.4 Deduplication

An opportunity is deduplicated if:
- Same market_id + side + lifecycle_intent is already in queue, OR
- A position for this market already exists in `PROBE` or `BUILD` state (prevents double-entry), OR
- The opportunity expired (time_remaining < 90s at evaluation time)

---

## 8. Capital Allocation Engine

### 8.1 Purpose

The Capital Allocation Engine (CAE) answers: **"How much capital should flow to each queued opportunity, given current risk state, buying power, exposure, and portfolio caps?"**

This is fundamentally a **portfolio-level optimization**, not per-trade Kelly.

### 8.2 Capital Flow Model

```
Step 1: Compute available_capital
  available_capital = min(buying_power, daily_budget_remaining)

Step 2: Apply risk mode reduction
  deployable_capital = available_capital × risk_mode_multiplier
  # NORMAL=1.0, DEFENSIVE=0.5, MICRO_RECOVERY=0.25, LOCKDOWN=0.0

Step 3: Reserve emergency buffer
  reserve = deployable_capital × reserve_fraction  # tier-dependent, e.g. 20%
  allocatable = deployable_capital - reserve

Step 4: Compute opportunity scores
  scores = [opp.composite_score for opp in opportunity_queue]

Step 5: Distribute proportionally
  for each opp in queue (up to top-N):
    raw_alloc = allocatable × (opp.score / sum_scores)
    clipped_alloc = min(raw_alloc, per_market_cap - current_market_exposure)
    if clipped_alloc >= CLOB_MINIMUM:
        alloc[opp.opportunity_id] = clipped_alloc

Step 6: Check portfolio cap
  for each alloc:
    if total_exposure_after_alloc > portfolio_cap:
        reject or reduce alloc
```

### 8.3 Kelly in the CAE

Kelly is not abandoned — it is repositioned as a **maximum size hint** within the CAE, not a single directive:

```
kelly_hint = (edge / (1 - entry_price)) × kelly_fraction × bankroll
kelly_hint_reduced = kelly_hint × risk_mode_multiplier

# CAE allocates min(kelly_hint_reduced, proportional_share_from_step_5)
# This prevents a single high-edge opportunity from consuming all capital
```

Kelly sets a ceiling; portfolio rules set the floor and the competition structure.

### 8.4 Loss Response (Not Pause)

When the risk budget degrades:

| Event | Response | Mechanism |
|-------|----------|-----------|
| 1 loss | No change | Monitor |
| 2 consecutive losses | DEFENSIVE mode | `risk_mode_multiplier = 0.5` |
| 3 consecutive losses | MICRO_RECOVERY | `risk_mode_multiplier = 0.25` |
| Daily drawdown ≥ 5% | MICRO_RECOVERY | `risk_mode_multiplier = 0.25` |
| Daily drawdown ≥ 10% | LOCKDOWN | `risk_mode_multiplier = 0.0` |
| Win after loss streak | Restore one level | `consecutive_losses = max(0, n-1)` |

**No wall-clock pauses.** The system continues scanning, scoring, and queuing opportunities in all risk modes. In LOCKDOWN, no capital is allocated (multiplier=0.0), but scanning and learning continue. The system re-enters MICRO_RECOVERY on the next winning trade.

---

## 9. Inventory Engine

### 9.1 Design

The Inventory Engine is the **runtime source of truth for all open positions**. It replaces the current `position_tracker.py` point-in-time reconciliation with a continuous, event-driven inventory state machine.

It is the single source of truth consulted by:
- ExecutionPlanner (before placing any order)
- Capital Allocation Engine (before allocating capital)
- OpportunityQueue (before enqueuing adds)
- OrderIntentValidator (before approving exits)
- FillTracker (after each fill confirmation)

### 9.2 State Machine

```
Position events drive state transitions:

PROBE_ORDER_PLACED      → position enters PROBE
PROBE_FILL_CONFIRMED    → position enters BUILD
BUILD_ORDER_PLACED      → position remains BUILD
BUILD_FILL_CONFIRMED    → position enters HOLD (after all base fills)
ADD_CONDITION_MET       → position enters ADD
ADD_ORDER_PLACED        → position remains ADD
ADD_FILL_CONFIRMED      → position enters HOLD (after all add fills)
HOLD_REDUCE_TRIGGERED   → position enters REDUCE
REDUCE_FILL_CONFIRMED   → position re-enters HOLD (partial) or EXIT (full)
EXIT_FILL_CONFIRMED     → position enters CLOSED
MARKET_RESOLVED         → position enters REDEEM
REDEMPTION_SUBMITTED    → position enters CLOSED
RECONCILIATION_UNSAFE   → position enters CLOSED_OR_UNSAFE
```

### 9.3 Required Data

```python
@dataclass
class InventoryEngine:
    positions: dict[str, InventoryRecord]   # keyed by position_id
    fill_log: list[FillRecord]              # append-only fill history
    event_log: list[InventoryEvent]         # append-only state transition log
    total_exposure_dollars: float
    total_exposure_pct: float
    exposure_by_asset: dict[str, float]
    unrealized_pnl: float
    session_realized_pnl: float
    consecutive_losses: int
    risk_mode: RiskMode
```

### 9.4 Inventory vs. Position Tracker

The existing `utils/position_tracker.py` is a **reconciliation guard** (pre-flight check against external CLOB state). The Inventory Engine is the **internal authoritative state**. These are complementary:

```
Inventory Engine  ←──── FillTracker (internal confirmed fills)
PositionTracker   ←──── CLOBClient  (external CLOB state read)
                   ↓
         reconciliation match check
                   ↓
            entry/exit approved or blocked
```

The Inventory Engine must agree with the PositionTracker on shape (total shares) before any new entry is approved. Discrepancies go to `CLOSED_OR_UNSAFE`.

---

## 10. Replay 2.0

### 10.1 What Replay 1.0 Can Do

Current offline tools (`tools/replay_analyzer.py`, `tools/paper_evaluation_report.py`) reconstruct trade outcomes from JSONL. They answer: "what did we trade, what was the result?"

### 10.2 What Replay 2.0 Must Do

Once Execution Intelligence exists, replay must answer much richer questions:

| Question | Replay 2.0 Tool |
|----------|-----------------|
| Was the execution plan optimal given orderbook at plan time? | `ExecutionPlanVsActualAnalyzer` |
| Did the add conditions fire correctly? | `AddConditionReplayVerifier` |
| What was MFE/MAE relative to the entry and each add? | `InventoryMFEMAETracker` |
| Did opportunity decay make the BUILD window too tight? | `OpportunityDecayAnalyzer` |
| Which phase of the market window produced the most fills? | `FillPhaseDistribution` |
| How did the Capital Allocation Engine distribute capital? | `CAPlanReplayLog` |
| Did the Opportunity Queue rank correctly vs outcomes? | `OpportunityRankingAudit` |
| When did the Learning Engine update parameters? | `LearningEventLog` |

### 10.3 Replay 2.0 Architecture

```
Execution Layer emits → ExecutionPlanEvent (JSONL)
                      → FillEvent (JSONL)
                      → InventoryStateTransition (JSONL)
                      → OpportunityQueueSnapshot (JSONL)
                      → CAPAllocationEvent (JSONL)

Offline tools consume these events to reconstruct:
  - full execution plan timeline
  - fill path verification (paper vs live fill probability)
  - inventory build curve (shares over time within epoch)
  - capital utilization efficiency
  - opportunity loss (edge that was queued but never filled)
```

### 10.4 Replay 2.0 Requirements

- All execution plans serialized with `plan_id` for cross-join with fills
- All fills tagged with `plan_id`, `position_id`, `run_id`
- All inventory state transitions tagged with `event_type`, `position_id`, `run_id`
- Offline tools must never mutate runtime state (current constraint, maintained)
- Replay 2.0 tools in `tools/replay_v2/` namespace (separate from current `tools/`)

---

## 11. Learning Engine

### 11.1 Philosophy

The Learning Engine is the **feedback loop from Replay 2.0 evidence into execution parameters**. It is always offline, never runtime-wired without explicit approval.

Learning does NOT mean:
- Automatic strategy changes
- Automatic risk threshold changes
- Automatic live deployment

Learning DOES mean:
- Generating parameter update **candidates** from replay evidence
- A human (or future promotion gate) reviews and approves parameter changes
- Parameters flow into config, not code

### 11.2 Learning Targets

| Parameter | Learning Signal | Update Frequency |
|-----------|-----------------|-----------------|
| Add condition EV threshold | Replay: did adds improve outcome? | Per batch (10+ fills) |
| Opportunity score weights | Replay: did high-score opps outperform? | Per batch |
| Add cooldown (evidence-based, not time) | Replay: how many cycles after entry did add improve P&L? | Per batch |
| Spread quality threshold | Replay: did high-spread entries perform worse? | Per batch |
| Time-remaining gate | Replay: did late entries have worse MFE? | Per batch |
| Regime routing | Replay: which regimes produced highest fill rates? | Per 50+ fills |
| Capital allocation ratios | Replay: did BTC vs ETH allocation match performance? | Per 50+ fills |

### 11.3 Learning Engine Modules

| Module | Purpose |
|--------|---------|
| `ParameterCandidateGenerator` | Reads Replay 2.0 output, proposes parameter deltas |
| `EvidenceGateChecker` | Blocks promotions without minimum evidence count |
| `ProposalLog` | JSONL log of all proposed changes (approved or rejected) |
| `ThrottleCalibrator` | Tunes OpportunityThrottle parameters from replay data |
| `AlphaDecayMonitor` | Detects when edge is deteriorating over time |
| `RegimeStrategyRouter` | Learns which signal strategies work in which regimes |
| `RoadmapGatePromoter` | Checks paper evidence gates before promoting a phase |

### 11.4 Evidence Gates

Before any Learning Engine proposal is approved:

| Gate | Minimum Evidence |
|------|-----------------|
| Fill path verified | ≥ 1 paper fill confirmed |
| Add optimization | ≥ 10 positions that reached ADD state |
| Spread calibration | ≥ 50 fills with spread recorded |
| Regime routing | ≥ 30 fills per regime type |
| Capital allocation tuning | ≥ 100 cross-market opportunities in queue |
| Live parameter promotion | Paper evidence grade A + human approval |

---

## 12. Subsystem Breakdown

| Subsystem | New or Existing | Priority | Blocking Gate |
|-----------|----------------|----------|---------------|
| MarketWindowTracker | New | HIGH | Needed before inventory |
| InventoryEngine | New | CRITICAL | Blocks entire Phase 3 |
| ExecutionPlanner | New | CRITICAL | Blocks Phase 3 |
| LadderEngine | New | HIGH | Blocks multi-order |
| OpportunityQueue | New | HIGH | Blocks capital competition |
| CapitalAllocationEngine | New | HIGH | Blocks portfolio-level |
| PositionLifecycleEngine | New | HIGH | Blocks BUILD/ADD/REDUCE |
| OpportunityThrottle | New (replaces 30-min sleep) | HIGH | Must fix before Phase 3 |
| FillTracker | New (paper: VirtualPTB extension) | CRITICAL | Zero fills today |
| Replay 2.0 | New | MEDIUM | Phase 3 observation |
| LearningEngine | New | LOW | Phase 4 |
| PositionTracker (existing) | Keep + integrate | CRITICAL | Reconciliation guard |
| OrderIntentValidator (existing) | Keep + extend | CRITICAL | Never bypass |
| RiskManager (existing) | Keep + integrate | CRITICAL | Never bypass |
| BankrollTierManager (existing) | Keep + reference | HIGH | Tier thresholds |

---

## 13. Data Flow

### 13.1 Entry Data Flow

```
Clock tick
  → MarketWindowTracker.update_phase()
  → GammaFetcher.get_active_markets()
    → MarketAvailabilityEngine.check()
      → if CLOSED_OR_UNSAFE: skip cycle
  → CLOB WebSocket cache → orderbook snapshot
  → SignalEngine.compute(snapshot)
    → RegimeDiagnostics.classify()
    → ProbabilityModel.estimate()
    → ExpectedValueEngine.compute()
    → LiquidityScorer.score()
    → SpreadQualityGate.check()
  → OpportunityQueue.enqueue(scored_opportunity)
    → deduplicate → rank → expire old
  → CapitalAllocationEngine.allocate(queue, risk_budget, buying_power)
  → ExecutionPlanner.plan(opportunity, allocation)
    → LadderEngine.build_ladder()
    → InventoryEngine.check_position_state()
    → PositionLifecycleEngine.validate_transition()
  → OrderIntentValidator.validate(order_intent)
  → OrderManager.execute(validated_intent)
    → VirtualPTB (paper) / CLOBClient (live)
  → FillTracker.record_fill(fill)
  → InventoryEngine.update_position(fill)
  → QuantEventLogger.emit(all events)
```

### 13.2 Exit Data Flow

```
PositionLifecycleEngine.trigger_reduce() / trigger_exit()
  → ExecutionPlanner.plan_exit(position)
  → OrderIntentValidator.validate(exit_intent)
  → OrderManager.execute_exit()
    → VirtualPTB (paper) / CLOBClient (live)
  → FillTracker.record_fill(exit_fill)
  → InventoryEngine.close_position(position_id)
  → RiskBudget.record_outcome(pnl)
    → consecutive_losses / wins update
    → risk_mode transition if needed
  → QuantEventLogger.emit(exit events)
```

### 13.3 Replay Data Flow

```
runtime/event_stream/
  ├── execution_plans_YYYY-MM-DD.jsonl       ← new in Phase 3
  ├── inventory_transitions_YYYY-MM-DD.jsonl ← new in Phase 3
  ├── opportunity_queue_YYYY-MM-DD.jsonl     ← new in Phase 3
  ├── capital_allocation_YYYY-MM-DD.jsonl    ← new in Phase 3
  └── (existing: research, system_health, risk, quant_data)

tools/replay_v2/
  ├── execution_plan_analyzer.py
  ├── inventory_mfe_mae_tracker.py
  ├── opportunity_decay_analyzer.py
  ├── fill_phase_distribution.py
  ├── cap_allocation_replay.py
  └── ranking_audit.py
```

---

## 14. Required Runtime Components

For Phase 3 (bounded multi-price inventory):

| Component | File (target) | Depends on |
|-----------|--------------|------------|
| MarketWindowTracker | `polymarket/market_window_tracker.py` | epoch_guard, timestamps |
| InventoryEngine | `polymarket/inventory_engine.py` | position_tracker, fill_tracker |
| FillTracker | `polymarket/fill_tracker.py` | virtual_ptb (paper), clob_client (live) |
| PositionLifecycleEngine | `polymarket/position_lifecycle.py` | inventory_engine |
| ExecutionPlanner | `polymarket/execution_planner.py` | lifecycle_engine, risk_manager, bankroll_tiers |
| LadderEngine | `polymarket/ladder_engine.py` | bankroll_tiers, settings |
| OpportunityQueue | `polymarket/opportunity_queue.py` | signal_engine, ev_engine |
| CapitalAllocationEngine | `polymarket/capital_allocation.py` | risk_budget, opportunity_queue |
| OpportunityThrottle | `polymarket/opportunity_throttle.py` | risk_manager |
| ExecutionPlanSerializer | `polymarket/execution_plan_serializer.py` | quant_event_logger |

For Phase 2 (paper inventory replay only):

| Component | File (target) | Depends on |
|-----------|--------------|------------|
| InventoryReplaySimulator | `tools/replay_v2/inventory_replay_sim.py` | JSONL event log |
| MFE/MAE Tracker | `tools/replay_v2/mfe_mae_tracker.py` | JSONL event log |
| OpportunityDecayAnalyzer | `tools/replay_v2/opportunity_decay.py` | JSONL event log |

---

## 15. Required Replay Components

| Component | Purpose |
|-----------|---------|
| ExecutionPlanVsActualAnalyzer | Did planned ladder match actual fills? |
| AddConditionReplayVerifier | Did add conditions fire at correct times? |
| InventoryMFEMAETracker | Max favorable/adverse excursion per position |
| OpportunityDecayAnalyzer | How quickly did edge decay after opportunity identified? |
| FillPhaseDistribution | Which market window phases had most fills? |
| CAPlanReplayLog | Capital allocation decisions vs outcomes |
| OpportunityRankingAudit | Were high-ranked opportunities better outcomes? |
| LearningEventLog | Parameter updates and their evidence basis |

---

## 16. Migration Plan

### Phase 1.5 (CURRENT — must complete before Phase 2)

These are prerequisites that do not implement execution intelligence but unblock it:

1. **Verify ≥ 1 paper fill** — Run paper sessions until at least one PAPER_FILL event appears. This is the single most important milestone. Without it, the fill path, PnL accounting, and InventoryEngine are unproven.

2. **Replace 30-min loss cluster pause** — Replace `LOSS_CLUSTER_PAUSE_SECONDS=1800` in `risk_manager.py` with the adaptive throttle: 3 consecutive losses → MICRO_RECOVERY mode for 1 cycle, then resume. Requires scoped task + tests + paper validation.

3. **Lift max_active_positions=1** — Currently hardcoded in `config/settings.py`. Must be raised to ≥ 3 before any multi-order ladder can be tested. Requires scoped task.

4. **God Object decomposition** — `polymarket/trader.py` must be decomposed (per `QUANT_ARCHITECTURE_MASTER_PLAN_001.md` Batches 2–N) before the new modules can be inserted into the runtime loop cleanly.

### Phase 2 (Paper Inventory Replay — offline only)

5. **MarketWindowTracker** — Implement phase tracking for OPENING_SCAN / ACTIVE_INVENTORY_TRADING / PROFIT_MANAGEMENT / FINAL_DERISK / CLOSED_OR_UNSAFE. Emit phase transitions to JSONL. Paper only, no execution changes.

6. **InventoryReplaySimulator** — Offline tool that reads existing JSONL and simulates what inventory would look like if multi-order had been allowed. Validates lifecycle state transitions and MFE/MAE retrospectively.

7. **FillPhaseDistribution analysis** — Analyze existing paper JSONL to identify which epochs and phases produced fill-capable conditions. Evidence base for Phase 3 timing.

### Phase 3 (Bounded Multi-Price Inventory — paper only first)

8. **FillTracker** — Extend VirtualPTB to emit structured fill events with position_id, plan_id, fill_price, fill_shares. Required before InventoryEngine can track fills.

9. **InventoryEngine** — Implement the state machine. Paper-only first. Requires FillTracker working.

10. **ExecutionPlanner + LadderEngine** — Generate multi-order plans. Paper only. Requires InventoryEngine.

11. **PositionLifecycleEngine** — State transition logic. Paper only. Requires ExecutionPlanner.

12. **OpportunityQueue** — Cross-market ranking. Paper only. Requires scored opportunities from Signal layer.

13. **CapitalAllocationEngine** — Portfolio-level allocation. Paper only. Requires OpportunityQueue + RiskBudget.

14. **Paper validation: multi-order lifecycle** — Run ≥ 30 paper sessions. Evidence gate: ≥ 10 positions that reach ADD state, ≥ 5 clean exits, ≥ 1 REDUCE event.

### Phase 4 (Continuous Inventory — paper first, then micro live)

15. **Replay 2.0 tools** — ExecutionPlanVsActualAnalyzer, MFE/MAE, add-condition verifier. Offline only.

16. **Learning Engine v1** — ParameterCandidateGenerator + ProposalLog. Human-approved. No auto-promotion.

17. **Live allowance + execution validation** — Blocked on Phase 1.5 paper fill evidence and live allowance readiness.

18. **Micro Live Pilot** — Single market, Probe only, $0.10, controlled conditions. Requires all Phase 3 evidence gates to pass. See roadmap.

---

## 17. Dependencies

```
Phase 1.5 prerequisites:
  paper_fill_verified ───────────────────► ALL Phase 3 components
  trader_decomposition (QUANT_ARCH_001) ► modular insertion points
  max_positions_lifted ─────────────────► LadderEngine / multi-order
  loss_pause_replaced ──────────────────► OpportunityThrottle

Phase 2:
  market_window_tracker ────────────────► Phase 3 timing gates
  phase_transition_JSONL ───────────────► Replay 2.0

Phase 3:
  fill_tracker ────────────────────────► InventoryEngine
  inventory_engine ────────────────────► ExecutionPlanner
  execution_planner ───────────────────► PositionLifecycleEngine
  position_lifecycle ──────────────────► OpportunityQueue (add gates)
  opportunity_queue ───────────────────► CapitalAllocationEngine
  capital_allocation ──────────────────► complete paper evidence

Phase 4:
  replay_2.0 ──────────────────────────► LearningEngine
  live_allowance ──────────────────────► Micro Live Pilot
  paper_fill_grade_A ──────────────────► Micro Live Pilot
```

---

## 18. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Paper fills never occur (microstructure blocks all entries) | MEDIUM | CRITICAL | Tune microstructure gates (imbalance_extreme threshold) in separate scoped task |
| InventoryEngine diverges from PositionTracker | LOW | CRITICAL | Reconciliation gate in InventoryEngine; never skip |
| Multi-order creates runaway exposure | LOW | HIGH | Per-position, per-asset, portfolio caps enforced in CAE |
| LadderEngine produces sub-$0.10 orders | MEDIUM | MEDIUM | Explicit CLOB minimum check in LadderEngine before emit |
| OpportunityQueue starves one asset | LOW | MEDIUM | Per-asset minimum allocation floor |
| Learning Engine auto-promotes bad parameters | LOW | HIGH | EvidenceGateChecker blocks promotions without minimum fills; human gate |
| trader.py God Object makes modular insertion impossible | HIGH | HIGH | Decomposition (QUANT_ARCH_001) must precede insertion — design dependency explicit |
| Epoch rollover causes stale opportunity in queue | MEDIUM | MEDIUM | Opportunity expiry = 1 cycle; auto-purge stale slugs |

---

## 19. Recommended Implementation Order

```
Priority 1 (Paper Fill + Structural):
  1a. Long paper sessions → verify ≥ 1 paper fill
  1b. trader.py decomposition Batch 2+ (QUANT_ARCH_001)
  1c. Replace LOSS_CLUSTER_PAUSE with adaptive OpportunityThrottle
  1d. Lift max_active_positions / max_entries to 3

Priority 2 (Phase 2 — Offline Replay):
  2a. MarketWindowTracker (phase tagging, JSONL only)
  2b. InventoryReplaySimulator (offline tool)
  2c. MFE/MAE offline tracker
  2d. Phase distribution analysis

Priority 3 (Phase 3 — Paper Inventory):
  3a. FillTracker (extend VirtualPTB)
  3b. InventoryEngine (state machine)
  3c. LadderEngine (multi-order sizing)
  3d. ExecutionPlanner (plan generation)
  3e. PositionLifecycleEngine (transition logic)
  3f. OpportunityQueue (cross-market ranking)
  3g. CapitalAllocationEngine (portfolio allocation)
  3h. Paper validation: ≥ 10 ADD transitions, ≥ 5 exits

Priority 4 (Phase 4 — Learning + Live Prep):
  4a. Replay 2.0 tools
  4b. Learning Engine v1 (proposals + evidence gate)
  4c. Live allowance resolution
  4d. CLOB $0.10 pre-submission check
  4e. Micro Live Pilot (Probe only, $0.10, single market)
```

---

## 20. Success Criteria

| Milestone | Criterion |
|-----------|-----------|
| Phase 1.5 complete | ≥ 1 paper fill event logged; 30-min pause replaced; max_positions ≥ 3; trader.py ≤ 8,000 lines |
| Phase 2 complete | InventoryReplaySimulator reconstructs ≥ 10 hypothetical multi-order sessions; MFE/MAE captured |
| Phase 3 paper gate | ≥ 10 paper positions reach ADD state; ≥ 5 REDUCE events; zero reconciliation mismatches |
| Phase 3 exit gate | ≥ 5 clean paper exits tracked through FillTracker → InventoryEngine → trade_close JSONL |
| Phase 4 paper gate | Evidence grade A from ≥ 30 paper sessions; Learning Engine generates ≥ 1 approved parameter update |
| Micro Live Pilot gate | All Phase 3+4 gates; live allowance confirmed; CLOB $0.10 check implemented; human approval |

---

## 21. Prioritized Roadmap to Micro Live Pilot

All dates are approximate planning targets, not commitments.

```
┌─────────────────────────────────────────────────────────────────────┐
│  TODAY (2026-06-30) — Baseline: Paper validated, zero fills          │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
          ┌─────────────────────────▼────────────────────────────────┐
          │  MILESTONE 1: PAPER FILL VERIFICATION                     │
          │  Goal: ≥ 1 paper fill event logged                        │
          │  How: Longer sessions (30+ min), tune imbalance_extreme   │
          │  gate threshold in separate scoped task                    │
          │  Gate: PAPER_FILL event in JSONL; P&L accounting visible  │
          │  This is the CRITICAL PATH item. Nothing else unblocks    │
          │  execution intelligence without this.                      │
          └─────────────────────────┬────────────────────────────────┘
                                    │
          ┌─────────────────────────▼────────────────────────────────┐
          │  MILESTONE 2: STRUCTURAL UNBLOCKING                       │
          │  2a. trader.py decomposition Batches 2–5                  │
          │      (per QUANT_ARCHITECTURE_MASTER_PLAN_001.md)          │
          │  2b. LOSS_CLUSTER_PAUSE → OpportunityThrottle             │
          │  2c. max_active_positions / max_entries lifted to 3       │
          │  2d. CLOB $0.10 pre-submission check added                │
          │  Gate: All tests pass; paper runtime validated             │
          └─────────────────────────┬────────────────────────────────┘
                                    │
          ┌─────────────────────────▼────────────────────────────────┐
          │  MILESTONE 3: MARKET WINDOW PHASE VISIBILITY              │
          │  MarketWindowTracker emits OPENING_SCAN /                 │
          │  ACTIVE_INVENTORY_TRADING / PROFIT_MANAGEMENT /           │
          │  FINAL_DERISK phases to JSONL                             │
          │  Gate: Phase transitions visible in paper JSONL           │
          └─────────────────────────┬────────────────────────────────┘
                                    │
          ┌─────────────────────────▼────────────────────────────────┐
          │  MILESTONE 4: INVENTORY REPLAY RESEARCH (Phase 2)         │
          │  Offline: InventoryReplaySimulator, MFE/MAE tracker       │
          │  Answer: "If we had multi-ordered, what would we hold?"   │
          │  Gate: ≥ 10 hypothetical sessions analyzed; MFE/MAE       │
          │  distribution captured; phase coverage ≥ ACTIVE_TRADING   │
          └─────────────────────────┬────────────────────────────────┘
                                    │
          ┌─────────────────────────▼────────────────────────────────┐
          │  MILESTONE 5: FILL TRACKER + INVENTORY ENGINE (Phase 3)   │
          │  FillTracker: extends VirtualPTB with position_id links   │
          │  InventoryEngine: state machine, position records         │
          │  Gate: Paper fills tracked through full lifecycle;        │
          │  trade_close JSONL shows InventoryRecord match            │
          └─────────────────────────┬────────────────────────────────┘
                                    │
          ┌─────────────────────────▼────────────────────────────────┐
          │  MILESTONE 6: EXECUTION PLANNER + LADDER (Phase 3)        │
          │  LadderEngine: Probe/Base/Add sizing                      │
          │  ExecutionPlanner: plan generation with allocation         │
          │  PositionLifecycleEngine: state transitions               │
          │  Gate: ≥ 5 paper positions enter ADD state               │
          └─────────────────────────┬────────────────────────────────┘
                                    │
          ┌─────────────────────────▼────────────────────────────────┐
          │  MILESTONE 7: OPPORTUNITY QUEUE + CAE (Phase 3)           │
          │  OpportunityQueue: cross-market ranking                   │
          │  CapitalAllocationEngine: portfolio-level allocation      │
          │  Gate: BTC + ETH compete for capital in same cycle;       │
          │  per-market and portfolio caps enforced                   │
          └─────────────────────────┬────────────────────────────────┘
                                    │
          ┌─────────────────────────▼────────────────────────────────┐
          │  MILESTONE 8: PHASE 3 PAPER EVIDENCE GATE                 │
          │  ≥ 10 positions reach ADD state                           │
          │  ≥ 5 REDUCE events                                        │
          │  ≥ 5 clean exits tracked through InventoryEngine         │
          │  Zero reconciliation mismatches                           │
          │  Evidence grade A (PASS from paper_evaluation_report.py) │
          └─────────────────────────┬────────────────────────────────┘
                                    │
          ┌─────────────────────────▼────────────────────────────────┐
          │  MILESTONE 9: REPLAY 2.0 + LEARNING ENGINE v1 (Phase 4)  │
          │  Replay 2.0 offline tools                                 │
          │  Learning Engine proposal log                             │
          │  ≥ 1 approved parameter update                           │
          │  Gate: Evidence grade A sustained across ≥ 30 sessions   │
          └─────────────────────────┬────────────────────────────────┘
                                    │
          ┌─────────────────────────▼────────────────────────────────┐
          │  MILESTONE 10: LIVE READINESS PREFLIGHT                   │
          │  Live allowance resolved (not missing_allowance)         │
          │  CLOB $0.10 check implemented and tested                  │
          │  Order placement smoke test (single $0.10 order)          │
          │  Fill detection confirmed                                 │
          │  Cancel path confirmed                                    │
          │  Reconciliation with live CLOB state confirmed            │
          └─────────────────────────┬────────────────────────────────┘
                                    │
          ┌─────────────────────────▼────────────────────────────────┐
          │  MILESTONE 11: MICRO LIVE PILOT                           │
          │  Single market (ETH or BTC)                               │
          │  Probe only ($0.10, 1 share)                              │
          │  T0_MICRO_SEED tier                                       │
          │  Controlled conditions: ACTIVE_INVENTORY_TRADING only    │
          │  Human approval required                                  │
          │  Success: fill confirmed, P&L recorded, clean exit        │
          └─────────────────────────────────────────────────────────┘
```

### Critical Path Summary

```
Paper fill verified
  → trader.py structurally decomposed
    → max_positions lifted + adaptive throttle
      → MarketWindowTracker live
        → Inventory replay analysis complete
          → FillTracker + InventoryEngine proven in paper
            → ExecutionPlanner + LadderEngine proven in paper
              → OpportunityQueue + CAE proven in paper
                → ≥ 30 paper sessions, evidence grade A
                  → Live allowance confirmed
                    → MICRO LIVE PILOT
```

**The zero-fills reality is the critical path constraint.** Every other milestone can be designed in parallel, but none can be validated without real paper fills. The first priority in any session after this document is verified is to achieve ≥ 1 paper fill through either longer sessions, tuned microstructure gates (scoped task), or both.

---

## Appendix A: Vocabulary Reconciliation

| Existing Term (QUANT_LIFECYCLE_INVENTORY_ENGINE.md) | New Term (this document) | Relationship |
|------------------------------------------------------|--------------------------|--------------|
| `OPENING_SCAN` | — | Market Window Phase (temporal gate) |
| `ACTIVE_INVENTORY_TRADING` | — | Market Window Phase (permits PROBE/BUILD/ADD) |
| `PROFIT_MANAGEMENT` | — | Market Window Phase (permits HOLD/REDUCE) |
| `FINAL_DERISK` | — | Market Window Phase (permits EXIT only) |
| `CLOSED_OR_UNSAFE` | — | Market Window Phase (no action) |
| — | `PROBE` | Position Lifecycle State |
| — | `BUILD` | Position Lifecycle State |
| — | `ADD` | Position Lifecycle State |
| — | `HOLD` | Position Lifecycle State |
| — | `REDUCE` | Position Lifecycle State |
| — | `MERGE` | Position Lifecycle State (reconciliation) |
| — | `REDEEM` | Position Lifecycle State (settlement) |
| — | `EXIT` | Position Lifecycle State |
| — | `CLOSED` | Position Lifecycle State |

Market Window Phases and Position Lifecycle States are **orthogonal axes**. Phases govern WHEN; States govern HOW. A position in `BUILD` state can only transition to `ADD` if the Market Window Phase is `ACTIVE_INVENTORY_TRADING`. A position in `HOLD` state in `FINAL_DERISK` must transition to `REDUCE` or `EXIT`.

---

## Appendix B: Existing Modules Not Changed by This Design

Per the DO NOT MODIFY rule, none of the following are changed by this document:

- `polymarket/trader.py` (decomposed separately per QUANT_ARCH_001)
- `config/settings.py`
- `.env`
- `utils/risk_manager.py` (OpportunityThrottle added alongside, does not replace)
- `polymarket/order_intent.py`
- `polymarket/order_manager.py`
- Paper execution path (`polymarket/virtual_ptb.py`)
- Live execution path (`polymarket/client.py`)
- Risk thresholds
- Strategy modules (`polymarket/signal.py`, `polymarket/probability_model.py`)

This architecture document defines WHAT to build. It does not modify anything.

---

*Document status: ARCHITECTURE ONLY. No code. No commits. Design complete.*
*Next step: Commit decision to be confirmed with user.*
