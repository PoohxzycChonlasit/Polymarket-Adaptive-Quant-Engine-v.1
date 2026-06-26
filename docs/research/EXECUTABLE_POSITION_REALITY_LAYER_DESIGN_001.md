# EXECUTABLE_POSITION_REALITY_LAYER_DESIGN_001

Date: 2026-06-20

Mode: DESIGN ONLY

Runtime behavior changed: No
Live behavior changed: No
Strategy/risk/execution changed: No
Sizer changed: No

## Objective

Design a second truth layer that separates current dust-sized paper fills from realistic Polymarket executable sizing.

This design does not replace current paper mode. It creates a research layer that answers:

```text
Did the signal work?
```

separately from:

```text
Could the same signal have been traded at a realistic executable size?
```

## Current Evidence

`POSITION_SIZE_REALITY_AUDIT_001` found:

| Metric | Value |
|---|---:|
| paper trade opens analyzed | `732` |
| median paper notional | `$0.050269` |
| mean paper notional | `$0.051645` |
| max paper notional | `$0.189061` |
| median shares | `0.095004` |
| max shares | `0.450145` |
| below `$1` | `100%` |
| below `5 shares` | `100%` |
| below `10 shares` | `100%` |
| current regime | `SIGNAL_MODE` |

Important field rule:

```text
payload.notional_size = actual paper order notional
payload.receipt.filled_size = actual paper filled shares
payload.min_fillable_size_usd = liquidity/book metadata, not actual order size
```

## 1. Terminology

### SIGNAL_MODE

The current paper mode with tiny simulated fills.

Purpose:

- signal lifecycle research;
- candidate discovery;
- stop-loss and take-profit behavior;
- timing and lifecycle analysis;
- regime/session analysis;
- paper-only PnL diagnostics.

SIGNAL_MODE must not be used for executable-PnL claims.

### EXECUTABLE_REALITY_MODE

An offline or shadow overlay that reclassifies the same paper signals under realistic minimum notional, share, spread, and depth constraints.

Purpose:

- determine whether paper signals survive minimum executable size assumptions;
- separate dust wins from executable evidence;
- estimate executable PnL only when a row passes executable constraints;
- prevent promotion decisions from relying on dust-sized fills.

### signal_pnl

The current paper PnL from the simulated dust-sized paper fill.

Rule:

```text
signal_pnl = paper PnL from current trade_journal
```

Use only for signal, lifecycle, and model diagnostics.

### executable_pnl

PnL counted only when the same trade passes an executable-reality track.

Rule:

```text
if executable_pass:
    executable_pnl = size_adjusted_or_overlay_pnl
else:
    executable_pnl = null
```

Version 1 may report proportional estimated PnL per selected track, but must label it as an overlay estimate until execution-mode paper fills exist.

### dust_zone

A trade is in the dust zone when its actual paper fill is too small to represent practical execution.

Default dust-zone rule:

```text
paper_notional < executable_min_notional_usd
or
paper_shares < executable_min_shares
```

Current evidence places all 732 analyzed paper opens in the dust zone.

### executable_notional

The notional required or assumed under an executable-reality track.

Examples:

```text
min_5_shares executable_notional = entry_price * 5
min_10_shares executable_notional = entry_price * 10
min_1_usd executable_notional = max(1.00, entry_price * executable_min_shares)
```

### executable_shares

The share size required or assumed under an executable-reality track.

Examples:

```text
min_5_shares executable_shares = 5
min_10_shares executable_shares = 10
min_1_usd executable_shares = 1.00 / entry_price
```

### executable_reject_reason

The reason a paper signal cannot be counted as executable evidence.

Recommended values:

| Reason | Meaning |
|---|---|
| `below_minimum_practical_shares` | paper shares below selected share threshold |
| `below_minimum_practical_notional` | paper notional below selected notional threshold |
| `missing_entry_price` | cannot compute required shares/notional |
| `missing_exit_price` | cannot compute executable overlay PnL |
| `missing_depth` | top-of-book size unavailable for feasibility check |
| `insufficient_depth` | available depth below executable share requirement |
| `missing_quote_age` | freshness cannot be checked |
| `stale_quote` | future freshness threshold fails |
| `spread_cost_unmodeled` | executable spread impact cannot be estimated |
| `missing_outcome_truth` | no terminal result or close evidence |

### minimum practical notional

The minimum dollar notional required for a trade to be treated as realistic under a track.

Default research tracks include `$1` and optional `$5`.

### minimum practical shares

The minimum share count required for a trade to be treated as realistic under a track.

Default research tracks include `5 shares` and `10 shares`.

## 2. Data Model

The first implementation should add fields only to offline reports or shadow overlays. It must not change runtime order sizing.

Recommended fields:

| Field | Type | Meaning |
|---|---|---|
| `paper_notional` | float | actual current paper notional, from `payload.notional_size` |
| `paper_shares` | float | actual paper shares, from `payload.receipt.filled_size` or equivalent |
| `paper_entry_price` | float | actual paper entry price |
| `paper_exit_price` | float/null | actual paper exit price when available |
| `signal_pnl` | float/null | current simulated paper PnL |
| `executable_track_enabled` | bool | whether executable overlay is computed |
| `executable_track_name` | string | `current_dust`, `min_5_shares`, `min_10_shares`, `min_1_usd`, `min_5_usd` |
| `executable_min_notional_usd` | float | selected track notional floor |
| `executable_min_shares` | float | selected track share floor |
| `executable_required_notional` | float | notional required at entry price |
| `executable_required_shares` | float | shares required by track |
| `executable_pass` | bool | true only if paper row meets selected track conditions |
| `executable_reject_reason` | string/null | fail-closed reason |
| `executable_entry_price` | float/null | price used by overlay |
| `executable_exit_price` | float/null | exit price used by overlay |
| `executable_pnl` | float/null | executable overlay PnL, null when rejected |
| `executable_drawdown_estimate` | float/null | estimated worst drawdown using same path, if path truth exists |
| `depth_available_shares` | float/null | relevant top-of-book or depth evidence |
| `spread_at_entry` | float/null | observed spread at entry |
| `quote_age_ms` | int/null | quote freshness evidence |
| `executable_truth_class` | string | `SIMULATION_ONLY`, `LOW_REALISM`, `PRACTICAL`, `SAFE_EXECUTION` |

Hash-stable output should include the source row identity:

```text
source_file
source_line
run_id
trade_id
condition_id
epoch_start_ts
asset
selected_side
```

## 3. Threshold Tracks

### Track 1: current_dust

Purpose:

Preserve the current paper signal ledger.

Formula:

```text
paper_notional = payload.notional_size
paper_shares = payload.receipt.filled_size
executable_pass = false for executable claims
signal_pnl = paper PnL
executable_pnl = null
```

Pass/fail logic:

- Signal pass if entry, side, close, and outcome fields exist.
- Executable pass is false by design.

Expected bankroll impact:

- Minimal paper drawdown.
- Preserves MICRO survival behavior.
- Does not test real execution capacity.

Expected trade frequency:

- Highest frequency.
- Captures all current paper entries.

### Track 2: min_5_shares

Purpose:

Conservative practical-share overlay.

Formula:

```text
executable_min_shares = 5
executable_required_notional = paper_entry_price * 5
executable_pass = paper_shares >= 5 and paper_notional >= executable_required_notional
```

Pass/fail logic:

- Reject if `paper_shares < 5`.
- Reject if required notional cannot be computed.
- Later versions should also reject if available depth is below 5 shares.

Expected bankroll impact:

At common prices:

| Entry Price | Required Notional |
|---:|---:|
| `0.30` | `$1.50` |
| `0.50` | `$2.50` |
| `0.70` | `$3.50` |

This is materially larger than the current `$0.05` fills and will stress MICRO bankroll assumptions.

Expected trade frequency:

- Current pass rate: `0 / 732`.
- Future pass rate depends on paper sizing, depth, and risk mode.

### Track 3: min_10_shares

Purpose:

Stricter executable realism track.

Formula:

```text
executable_min_shares = 10
executable_required_notional = paper_entry_price * 10
executable_pass = paper_shares >= 10 and paper_notional >= executable_required_notional
```

Expected bankroll impact:

At common prices:

| Entry Price | Required Notional |
|---:|---:|
| `0.30` | `$3.00` |
| `0.50` | `$5.00` |
| `0.70` | `$7.00` |

This likely requires a different paper execution bankroll posture before it can be tested as actual fills.

Expected trade frequency:

- Current pass rate: `0 / 732`.
- Lower than `min_5_shares`.
- Better suited for later PAPER_EXECUTION_MODE than initial offline overlay.

### Track 4: min_1_usd

Purpose:

Smallest notional realism track.

Formula:

```text
executable_min_notional_usd = 1.00
executable_required_shares = 1.00 / paper_entry_price
executable_pass = paper_notional >= 1.00
```

Optional combined pass:

```text
executable_pass = paper_notional >= 1.00 and paper_shares >= executable_min_shares
```

Expected bankroll impact:

- About 20x current median notional.
- Less strict than 5 shares at prices above `$0.20`.

Expected trade frequency:

- Current pass rate: `0 / 732`.
- Useful as an early diagnostic threshold, but weaker than share-based realism.

### Track 5: min_5_usd

Purpose:

Optional stronger notional track for future paper execution validation.

Formula:

```text
executable_min_notional_usd = 5.00
executable_required_shares = 5.00 / paper_entry_price
executable_pass = paper_notional >= 5.00
```

Expected bankroll impact:

- About 100x current median notional.
- Likely incompatible with current MICRO-sized paper posture.

Expected trade frequency:

- Current pass rate: `0 / 732`.
- Should be reserved for later bankroll realism analysis.

## 4. Integration Plan

Three possible paths:

### Option A: Offline report compiler only

Add executable-reality fields in an offline analyzer or report compiler.

Pros:

- no runtime risk;
- no sizer changes;
- no execution changes;
- can process historical evidence;
- compatible with the active low-price truth question.

Cons:

- cannot prove actual future fill behavior;
- depends on logged entry/exit/depth/freshness fields.

### Option B: Shadow telemetry overlay

Emit executable-reality labels during runtime without changing order size or trade decisions.

Pros:

- collects fresh real-time feasibility evidence;
- helps monitor depth, spread, and quote age at signal time;
- can prepare for later paper execution mode.

Cons:

- touches runtime observability;
- requires tests for fail-soft logging and no decision authority;
- should wait until offline contract is stable.

### Option C: Paper runtime sizing change

Change paper sizing to enforce executable minimums.

Pros:

- directly tests larger paper fills.

Cons:

- changes the current evidence regime;
- risks contaminating N/current signal continuity;
- crosses into sizer/risk behavior;
- blocked by the current scope and active research governance.

Recommended safest first phase:

```text
A. offline report compiler only
```

The first implementation should be a read-only offline compiler that produces dual ledgers:

```text
signal_ledger
executable_reality_ledger
```

No runtime, sizer, risk, execution, or config changes should occur in the first phase.

## 5. Interaction With Current Research

### Option D

Option D evidence should be interpreted in two ledgers:

- `signal_ledger`: keeps current dust-sized signal results.
- `executable_reality_ledger`: reports whether those same signals pass executable tracks.

If Option D looks profitable in SIGNAL_MODE but has zero executable-track pass rate, it remains signal evidence only.

### Delta Extreme Shadow

Delta Extreme Shadow should not be promoted from shadow evidence to executable evidence unless rows pass at least one executable track.

Required interpretation:

```text
delta_extreme_shadow_signal = allowed
delta_extreme_shadow_executable = only if executable_pass
```

If Delta Extreme captures low-price or dust opportunities, the layer must prevent those rows from being counted as executable truth.

### Micro Recovery

Micro Recovery may correctly protect the bankroll while also suppressing larger executable-track candidates.

The layer should therefore report:

```text
risk_mode
paper_notional
required_executable_notional
executable_pass
executable_reject_reason
```

This separates:

- protective risk behavior;
- signal scarcity;
- executable-size infeasibility.

### Entry Funnel

Entry Funnel should add an executable-size branch after signal approval:

```text
generated
model_ready
approved_signal
paper_filled
executable_track_pass
executable_track_reject
```

This prevents a filled paper trade from being mistaken for an executable trade.

### Executable Truth Claims

No current dust-sized paper trade should support executable truth claims.

Required language:

```text
Current paper rows may support signal truth.
Current paper rows do not support executable PnL truth unless they pass an executable track.
```

## 6. Promotion Path

### DESIGN -> OFFLINE AUDIT

Required:

- this design is accepted;
- source fields are confirmed stable:
  - `payload.notional_size`
  - `payload.receipt.filled_size`
  - `payload.entry_price`
  - close price and PnL fields
- offline analyzer spec is written;
- no runtime or sizer changes are included.

Exit criteria:

- offline report can classify historical rows into tracks;
- output is deterministic;
- current 732-row evidence reproduces `SIGNAL_MODE` and zero executable passes.

### OFFLINE AUDIT -> SHADOW OVERLAY

Required:

- offline audit shows the fields needed for executable classification;
- missing-field rates are documented;
- reject reasons are stable;
- tests prove fail-soft report generation.

Exit criteria:

- runtime can emit shadow-only executable labels without changing decisions;
- telemetry explicitly has no order authority;
- paper/live separation tests pass.

### SHADOW OVERLAY -> PAPER EXECUTION MODE

Required:

- shadow overlay has enough sample size to estimate executable-track frequency;
- depth and spread evidence are reliable;
- risk mode interaction is understood;
- operator explicitly approves a separate paper execution sizing experiment.

Exit criteria:

- paper execution mode produces fills at or above selected minimum track;
- signal PnL and executable PnL are reported separately;
- drawdown and stop behavior remain within paper risk limits.

### PAPER EXECUTION MODE -> LIVE CANDIDATE

Required:

- live readiness blockers are independently resolved;
- allowance, order placement, fill, cancel, and reconciliation are proven;
- executable paper evidence has sufficient sample size;
- PF, WR, drawdown, spread/slippage, and partial-fill behavior survive realistic sizing;
- no active governance question blocks promotion.

Exit criteria:

- explicit operator approval;
- live preflight passes;
- tiny controlled live validation plan exists;
- no automatic promotion from paper evidence.

## 7. Safety Constraints

Hard constraints:

- no sizer changes yet;
- no live trading;
- no order execution changes;
- no risk mode changes;
- no current runtime restart;
- no strategy changes;
- no threshold activation;
- no config changes;
- no changes to paper/live separation;
- no reinterpretation of dust PnL as executable PnL.

The active question `LOW_PRICE_TRUTH_RESOLUTION_001` still blocks strategy, sizer, execution, threshold, and inventory changes. This design is allowed only as a documentation and future offline-analysis artifact.

## Counterfactual Design Recommendations

Future offline reports should produce all five tracks side by side:

| Track | Primary Question |
|---|---|
| `current_dust` | Did the tiny paper signal work? |
| `min_5_shares` | Would the signal clear a conservative practical share floor? |
| `min_10_shares` | Would the signal clear a stricter share floor? |
| `min_1_usd` | Would the signal clear minimum notional realism? |
| `min_5_usd` | Would the signal survive stronger bankroll-realism assumptions? |

Recommended first report outputs:

```text
track_name
trade_count
pass_count
reject_count
pass_rate
signal_pnl
executable_pnl
median_required_notional
median_required_shares
top_reject_reasons
```

The report should be explicit that counterfactual executable PnL is not actual fill evidence until PAPER_EXECUTION_MODE is separately run.

## Final Verdict

`READY_FOR_OFFLINE_AUDIT`

The current evidence is sufficient to design and run an offline executable-reality audit. It is not sufficient to change runtime sizing, execution, risk mode, or live trading behavior.

