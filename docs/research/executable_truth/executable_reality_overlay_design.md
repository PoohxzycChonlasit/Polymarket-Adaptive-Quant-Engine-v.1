# Executable Reality Overlay Design

Date: 2026-05-23

Scope: docs-only design for a future research overlay that separates signal evidence from executable evidence.

Runtime behavior changed: No
Live behavior changed: No

## Goal

Create a future research overlay with two evidence modes:

```text
SIGNAL_MODE
EXECUTABLE_MODE
```

The overlay must let paper continue answering "did the signal direction work?" while separately answering "could this trade have been executed with realistic minimum size, spread, liquidity, and fill assumptions?"

This design does not authorize runtime sizing changes, policy thresholds, live mode, replay mutation, or execution changes.

## Motivation

Current T0 paper evidence includes orders around:

```text
notional ~= $0.05
shares ~= 0.09
```

Those fills are useful for lifecycle and signal research, but they are too small to support live-executable PnL claims. Local metadata did not expose authoritative Polymarket `min_order_size`, `minimum_order_size`, or `mos`, so the current conservative audit used:

```text
assumed minimum practical shares = 5
```

Under that assumption, minimum executable notional is:

| Price | Shares | Minimum Notional |
|---:|---:|---:|
| `0.20` | `5` | `$1.00` |
| `0.50` | `5` | `$2.50` |
| `0.80` | `5` | `$4.00` |

## Mode Definitions

### SIGNAL_MODE

`SIGNAL_MODE` preserves current simulation sizing.

Purpose:

- measure directional signal quality;
- evaluate TP/SL by lifecycle phase;
- evaluate quote age, quote staleness, and timing;
- study BTC vs ETH, YES vs NO, session effects, and opening/active regime splits;
- keep MICRO seed evidence without pretending it is live executable.

Allowed evidence:

- simulated paper fills;
- fractional-share fills;
- dust notional fills;
- current paper `trade_result`;
- current paper `pnl_usdc`, but labeled as `signal_pnl_simulated`;
- quote-age and lifecycle fields.

Not allowed:

- executable-PnL claims;
- live fill probability claims;
- live minimum-order acceptance claims;
- maker/taker queue realism claims.

### EXECUTABLE_MODE

`EXECUTABLE_MODE` enforces a practical minimum overlay for research classification.

Purpose:

- decide whether a paper trade would be large enough to represent a realistic executable order;
- separate dust signal wins from executable edge;
- estimate executable PnL only for trades that pass practical minimum checks;
- identify bankroll tiers where the ladder becomes practical.

Required overlay checks:

| Check | Rule |
|---|---|
| minimum practical shares | default `5` shares until authoritative metadata is available |
| minimum executable notional | `minimum_practical_shares * entry_price` |
| order notional test | planned notional must be `>= minimum_executable_notional` |
| top-of-book depth test | top relevant depth should be `>= minimum_practical_shares` |
| quote freshness | quote age and `quote_stale_ms` must be available and bucketed |
| spread cost | spread cost should be deducted or at least reported |
| partial-fill realism | classify if top depth is below practical shares |

## Evidence Labels

Every matched trade should receive two independent labels:

| Field | Meaning |
|---|---|
| `signal_evidence_class` | whether the trade is usable for signal research |
| `executable_evidence_class` | whether the trade is usable for executable-edge research |

Recommended values:

| Label | Meaning |
|---|---|
| `SIGNAL_VALID` | trade can be used for signal, lifecycle, timing, and outcome-truth research |
| `SIGNAL_INVALID` | missing outcome, price, side, or lifecycle fields make signal evidence unsafe |
| `SIMULATION_ONLY` | dust/fractional order below practical minimum |
| `LOW_REALISM` | near minimum but only executable under favorable price/depth assumptions |
| `PRACTICAL` | clears common practical minimum and has usable depth/freshness evidence |
| `SAFE_EXECUTION` | clears practical minimum with comfortable depth and freshness margin |

## Dust Zone

The dust zone is any trade where:

```text
planned_shares < minimum_practical_shares
```

or:

```text
planned_notional < minimum_practical_shares * entry_price
```

Current `$0.05` T0 paper trades are dust-zone examples.

Dust-zone rows should remain in:

- signal win/loss tables;
- lifecycle timing tables;
- quote-age analysis;
- session/regime studies;
- model disconfirmation research.

Dust-zone rows should be excluded from:

- executable PnL;
- fill realism;
- live-readiness claims;
- minimum viable bankroll conclusions.

## Minimum Practical Shares

Default research assumption:

```text
minimum_practical_shares = 5
minimum_practical_source = "conservative_assumption"
```

When authoritative market metadata becomes available, the overlay should prefer:

```text
minimum_practical_shares = market_metadata.minimum_order_size
minimum_practical_source = "market_metadata"
```

If metadata is missing:

```text
minimum_practical_shares = 5
minimum_practical_source = "conservative_assumption"
minimum_practical_confidence = "ASSUMED"
```

## Derived Fields

Future offline/research rows should derive these fields without changing runtime behavior:

| Field | Formula / Meaning |
|---|---|
| `overlay_mode` | `SIGNAL_MODE` or `EXECUTABLE_MODE` |
| `minimum_practical_shares` | market metadata if available, else conservative default |
| `minimum_practical_source` | `market_metadata`, `config`, or `conservative_assumption` |
| `minimum_executable_notional` | `minimum_practical_shares * entry_price` |
| `planned_shares` | paper order size |
| `planned_notional` | paper order notional |
| `minimum_multiple` | `planned_shares / minimum_practical_shares` |
| `executable_minimum_met` | true if planned shares meet practical minimum |
| `depth_minimum_met` | true if top relevant depth meets practical minimum |
| `quote_freshness_class` | bucket from `quote_stale_ms` / quote age |
| `dust_zone` | true if practical minimum is not met |
| `executable_reject_reason` | reason executable mode rejects the row |
| `signal_pnl_simulated` | original paper `pnl_usdc` |
| `executable_pnl` | PnL counted only when executable checks pass |

## Replay Separation

Replay should produce two ledgers from the same matched trades.

### Signal Ledger

The signal ledger answers:

```text
Did the model pick the right side at the right time?
```

Include:

- all rows with valid side, entry, exit, and `trade_result`;
- dust trades;
- fractional-share fills;
- T0/T1 MICRO evidence;
- `signal_pnl_simulated`.

Do not use this ledger for executable-PnL claims.

### Executable Ledger

The executable ledger answers:

```text
Would this edge survive realistic minimum order size and fill constraints?
```

Include only rows that pass:

- minimum practical shares;
- minimum executable notional;
- top-depth feasibility;
- quote freshness visibility;
- valid entry/exit prices;
- valid outcome truth.

For rows that fail, keep them in the table with classification and reject reason, but exclude them from executable PnL aggregates.

## PnL Rules

| PnL Field | Source | Use |
|---|---|---|
| `pnl_usdc` | current paper journal | raw paper result |
| `signal_pnl_simulated` | alias of paper `pnl_usdc` | signal-mode diagnostics |
| `executable_pnl` | `pnl_usdc` only when executable checks pass | executable-edge aggregates |
| `executable_pnl_adjusted` | future optional spread/slippage-adjusted PnL | deeper microstructure research |

Default rule:

```text
if executable_evidence_class in ["PRACTICAL", "SAFE_EXECUTION"]:
    executable_pnl = pnl_usdc
else:
    executable_pnl = null
```

Do not rewrite or discard the original paper PnL. Label it.

## Reject Reasons

Recommended executable reject reasons:

| Reason | Meaning |
|---|---|
| `below_minimum_practical_shares` | planned shares below practical minimum |
| `below_minimum_executable_notional` | planned notional below price-adjusted minimum |
| `insufficient_top_depth` | top-of-book depth cannot satisfy practical size |
| `missing_minimum_metadata` | no authoritative market minimum; conservative assumption used |
| `missing_depth_evidence` | top depth unavailable |
| `missing_quote_age` | quote freshness unavailable |
| `stale_quote` | quote age exceeds future research threshold |
| `missing_outcome_truth` | no `trade_result` or terminal result |
| `missing_price` | entry/exit price unavailable |

## Example Classification

Current latest T0 paper order:

```text
entry_price = 0.53
planned_notional = $0.050562
planned_shares = 0.095400
minimum_practical_shares = 5
minimum_executable_notional = $2.65
minimum_multiple = 0.01908
```

Classification:

| Mode | Result |
|---|---|
| `SIGNAL_MODE` | `SIGNAL_VALID` if side/entry/exit/outcome are present |
| `EXECUTABLE_MODE` | `SIMULATION_ONLY` |
| executable reject reason | `below_minimum_practical_shares` |
| `signal_pnl_simulated` | keep paper `pnl_usdc` |
| `executable_pnl` | `null` |

## Reporting Contract

Future monitors should show both views:

| Metric | Signal View | Executable View |
|---|---|---|
| trade count | all valid signal rows | only practical/safe rows |
| TP/SL | all valid signal rows | only practical/safe rows |
| mean PnL | `signal_pnl_simulated` | `executable_pnl` |
| quote age | all valid signal rows | practical/safe rows plus rejected-row diagnostics |
| bankroll tier | all rows | grouped by executable class |
| readiness | signal readiness and executable readiness separately |

Suggested readiness split:

```text
signal_readiness_pct
executable_readiness_pct
```

This prevents a dust-heavy run from appearing ready for executable policy.

## Answer: Signal Edge vs Executable Edge

Replay should separate signal edge from executable edge by treating every matched trade as two possible observations:

1. A signal observation, where fractional simulated sizing is allowed and the question is whether the model chose the correct side.
2. An executable observation, where the same trade must pass minimum shares, minimum notional, top-depth, quote freshness, and outcome-truth checks before its PnL counts.

In short:

```text
signal edge = directional correctness under paper simulation
executable edge = directional correctness that survives minimum size and microstructure constraints
```

Current T0/T1 paper trades can support signal edge. They should not support executable edge unless they pass the overlay.

## Implementation Boundary For Later

This design is intentionally future-facing. A later implementation should be:

- offline or paper-research only first;
- fail-soft;
- additive to JSONL/report outputs;
- explicit about assumption source;
- isolated from live trading and strategy/risk decisions.

Do not use this overlay to block runtime trades or change sizing unless a separate future task explicitly scopes policy enforcement.

## Future Options

OPTION 1 - SAFE EV PRESERVATION:

Add labels only in docs and research monitors. Keep runtime unchanged. This is the recommended immediate path.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:

Build an offline analyzer that replays historical matched trades into signal and executable ledgers, using `mos=5` until metadata is available.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:

Add future runtime observability fields for market minimum metadata, top-depth feasibility, and executable overlay labels, but still avoid policy enforcement.

Recommended sequence:

```text
docs design -> offline analyzer -> paper monitor labels -> optional runtime observability -> policy only after evidence
```

## Final Status

Design status: ready for future offline/research implementation.

Runtime behavior changed: No
Live behavior changed: No
Tests: not run; docs-only design.
