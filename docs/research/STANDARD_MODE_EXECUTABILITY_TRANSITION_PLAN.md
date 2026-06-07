# Standard Mode Executability Transition Plan

**Date:** 2026-06-07
**Scope:** Docs only. Paper-only transition design. No runtime changes. No strategy changes. No risk changes. No live trading.

---

## Executive Summary

The current paper system is in `SIGNAL_MODE`.

The Share Size And Executable Reality Audit confirmed:

- `$20` paper mode is `SIGNAL_CAPTURE` only.
- All `440` completed paper trades are below `1` share.
- `executable_pnl` is intentionally `None` for all rows.
- Live mode would skip the current `$20` dust trades.
- `$100` is the first bankroll level that exits `MICRO_SURVIVAL`.
- Standard-mode multiplier behavior has not been empirically measured yet.

The next paper-only step is not live trading. The next step is a controlled transition design into:

```text
STANDARD_PAPER_EXECUTABILITY_MODE
```

This mode should answer one question:

```text
When MICRO_SURVIVAL is no longer active, does standard paper sizing produce trades that clear
minimum executable size while preserving signal quality and risk discipline?
```

---

## 1. Current State

### Current Mode: SIGNAL_MODE

Current bankroll is about `$20`, which maps to:

| Field | Current State |
|---|---|
| Tier | `T0_MICRO_SEED` |
| Family | `MICRO` |
| Runtime mode | `MICRO_SURVIVAL` |
| Typical notional | about `$0.05` |
| Typical shares | about `0.09-0.10` |
| Executable status | below `1` share |
| Evidence class | signal / lifecycle / outcome truth only |

Current paper PnL is useful for:

- direction research;
- lifecycle timing;
- quote freshness and staleness research;
- regime/session analysis;
- watchlist evidence accumulation.

Current paper PnL is not useful for:

- executable PnL claims;
- live fill realism;
- slippage realism;
- partial-fill risk;
- live readiness.

---

## 2. Transition Definition

### SIGNAL_MODE

`SIGNAL_MODE` is the current sub-`$100` paper state.

Definition:

```text
bankroll < $100
OR
MICRO_SURVIVAL active
OR
planned shares < 1
```

Evidence rules:

- `signal_pnl` may be tracked.
- `paper_pnl` may be tracked.
- `executable_pnl` remains `null`.
- Trades are labeled `SIMULATION_ONLY` or `DUST_ZONE`.
- No live-readiness claim is allowed.

### STANDARD_PAPER_EXECUTABILITY_MODE

`STANDARD_PAPER_EXECUTABILITY_MODE` is a future paper-only state where MICRO_SURVIVAL is inactive and standard sizing is measured directly.

Definition:

```text
bankroll >= $100
paper mode only
MICRO_SURVIVAL inactive
standard sizing path active
sub-1-share gate active
```

Purpose:

- measure actual standard-mode shares;
- measure actual standard-mode notional;
- measure how often paper candidates clear `>= 1` share;
- measure how often paper candidates clear `>= $1` notional;
- separate `signal_pnl` from `executable_pnl`;
- determine whether standard sizing preserves or destroys the signal edge.

This is not live mode. It is paper-only executability research.

### EXECUTABLE_EVIDENCE_MODE

`EXECUTABLE_EVIDENCE_MODE` begins only after enough standard paper trades pass minimum-size and microstructure gates.

Definition:

```text
standard paper trades with:
shares >= 1
notional >= $1
fresh quote
acceptable spread
sufficient top-depth
confirmed outcome truth
```

`EXECUTABLE_EVIDENCE_MODE` still does not authorize live trading.

---

## 3. Bankroll Levels

The current tier ladder creates three important thresholds.

| Bankroll | Tier | Family | Interpretation |
|---:|---|---|---|
| `$20` | `T0_MICRO_SEED` | MICRO | Signal capture only. Dust trades dominate. |
| `$25` | `T1_MICRO_BUILD` | MICRO | Leaves seed protection but still MICRO. Not enough. |
| `$50` | `T2_MICRO_SURVIVAL` | MICRO | Still MICRO_SURVIVAL. Max shares remain below 1 in common price zones. |
| `$100` | `T3_BASE_BUILD` | BASE | First level that exits MICRO_SURVIVAL. Standard sizing can be measured. |
| `$250` | `T4_BASE_STABLE` | BASE | Safer executable evidence tier. Better margin across price bands. |

Conclusion:

```text
Minimum bankroll to exit MICRO_SURVIVAL: $100
Minimum bankroll to begin STANDARD_PAPER_EXECUTABILITY_MODE: $100
Preferred bankroll for robust executable evidence: $250
```

Important distinction:

- `$25` exits seed protection.
- `$100` exits MICRO_SURVIVAL.
- `$250` begins stronger executable-evidence quality.

---

## 4. Why $100 Is Necessary

Within MICRO_SURVIVAL, the notional formula is constrained by the survival fraction:

```text
notional ~= bankroll * 0.0025
```

At just under `$100`:

```text
max_micro_notional ~= $100 * 0.0025 = $0.25
```

At a typical entry price around `0.53`:

```text
max_micro_shares ~= $0.25 / 0.53 = 0.47 shares
```

Therefore:

```text
MICRO_SURVIVAL cannot produce >= 1 share at common BTC/ETH 5m prices.
```

The transition requires leaving MICRO_SURVIVAL entirely.

---

## 5. How To Test Standard-Mode Sizing Without Live Trading

Testing must remain paper-only and staged.

### Stage 1: Offline Projection

Use historical matched trades and calculate hypothetical standard-mode sizes at bankroll levels:

```text
$100
$150
$250
$500
```

For each historical candidate, compute:

- projected standard notional;
- projected shares;
- `>= 1 share` pass/fail;
- `>= $1 notional` pass/fail;
- projected executable candidate flag;
- projected executable PnL placeholder.

This stage does not change runtime.

### Stage 2: Standard Paper Shadow Report

In a future explicitly scoped observability phase, add a paper-only report that computes standard-mode sizing alongside current paper sizing.

It should not alter orders.

It should emit comparison fields such as:

```text
actual_paper_shares
actual_paper_notional
shadow_standard_shares
shadow_standard_notional
shadow_executable_candidate
```

This is still observability only.

### Stage 3: Standard Paper Run

Only after explicit approval, run paper mode with a paper bankroll state that naturally places the system in `T3_BASE_BUILD` or higher.

Rules:

- paper only;
- no live flags;
- no wallet signing;
- no strategy changes;
- no risk changes;
- no stop-loss changes;
- no execution changes;
- collect standard-mode trades exactly as the current logic produces them.

The purpose is to measure the actual standard multiplier stack instead of inferring it from MICRO_SURVIVAL dust data.

---

## 6. Required Metrics

Every standard-mode paper report should include these fields.

### Per-Trade Fields

| Field | Meaning |
|---|---|
| `run_id` | Runtime identity. |
| `candidate_id` | Candidate identity. |
| `condition_id` | Market identity. |
| `epoch_start_ts` | Market window start. |
| `asset` | BTC or ETH. |
| `side` | YES or NO. |
| `lifecycle_phase` | Entry lifecycle phase. |
| `entry_price` | Entry contract price. |
| `shares` | Filled or planned paper shares. |
| `notional` | `shares * entry_price`. |
| `min_shares_threshold` | Usually `1` until authoritative metadata says otherwise. |
| `min_notional_threshold` | `$1` monitoring threshold. |
| `one_share_minimum_met` | `shares >= 1`. |
| `one_dollar_notional_met` | `notional >= $1`. |
| `executable_candidate` | True only if share, notional, freshness, spread, and depth checks pass. |
| `quote_stale_ms` | Staleness at paper fill. |
| `spread` | Entry spread. |
| `top_depth_relevant_side` | Fill realism input. |
| `signal_pnl` | Current signal/paper PnL. |
| `executable_pnl` | `signal_pnl` only when executable checks pass; otherwise `null`. |

### Aggregate Fields

| Metric | Definition |
|---|---|
| `standard_paper_trade_count` | Number of paper trades produced in standard mode. |
| `one_share_pass_count` | Trades where `shares >= 1`. |
| `one_share_pass_rate` | `one_share_pass_count / standard_paper_trade_count`. |
| `one_dollar_notional_pass_count` | Trades where `notional >= $1`. |
| `one_dollar_notional_pass_rate` | Count divided by standard paper trades. |
| `executable_candidate_count` | Trades passing all executable-candidate checks. |
| `executable_candidate_rate` | Executable candidates divided by standard paper trades. |
| `signal_pnl_total` | PnL for all standard-mode paper trades. |
| `executable_pnl_total` | PnL for executable-candidate rows only. |
| `executable_pnl_null_count` | Rows rejected from executable PnL. |
| `spread_cost_estimate` | Estimated cost at actual standard paper size. |
| `slippage_bucket` | Paper-only estimate from spread/depth. |

---

## 7. Standard-Mode Quality Gates

These gates are research gates only. Passing them still does not authorize live trading.

### Gate 1: Standard Paper Sample Size

Minimum:

```text
n >= 100 standard-mode paper trades
```

Preferred:

```text
n >= 250 standard-mode paper trades
```

Reason:

The 440-trade SIGNAL_MODE sample proves dust status, not standard-mode behavior. Standard-mode needs its own sample.

### Gate 2: Minimum Share Pass Rate

Minimum:

```text
>= 90% of standard-mode paper trades clear >= 1 share
```

Preferred:

```text
>= 95%
```

Reason:

If standard sizing still produces frequent sub-1-share candidates, the system has not actually left simulation-only behavior.

### Gate 3: Minimum Notional Pass Rate

Minimum:

```text
>= 90% of standard-mode paper trades clear >= $1 notional
```

Preferred:

```text
>= 95%
```

Reason:

One-share trades at very low price may be technically above share minimum but still too small for robust fill/PnL research.

### Gate 4: Executable Candidate Rate

Minimum:

```text
>= 80% executable_candidate_rate
```

The executable candidate check must include:

- `shares >= 1`;
- `notional >= $1`;
- quote freshness available;
- acceptable spread;
- enough top-depth on the relevant side;
- valid outcome truth.

### Gate 5: PF After Executable Sizing

Minimum research gate:

```text
executable PF > 1.10 over n >= 100
```

Preferred live-review gate:

```text
executable PF >= 1.25 over n >= 250
```

This must be measured on executable-candidate rows only.

### Gate 6: Slippage And Spread Realism

Before any live consideration:

- quote freshness coverage must be complete or explicitly classified;
- spread must be measured at entry and exit;
- top-depth must support the planned share size;
- slippage estimate must be reported;
- adverse selection notes must be tracked by session and regime.

### Gate 7: Operational Safety

The following must remain true:

- no live orders;
- no live wallet signing;
- no strategy changes;
- no risk changes;
- no stop-loss changes;
- no sizing overrides;
- no martingale;
- no averaging down;
- no bypass of OrderIntent, reconciliation, stale-orderbook, or risk gates.

---

## 8. Live Trading Is Explicitly Forbidden

This transition plan forbids live trading.

Do not:

- enable live mode;
- change `.env` live flags;
- use real wallet allowance;
- place live orders;
- cancel live orders;
- redeem live positions;
- modify strategy to force executable size;
- modify risk to force executable size;
- bypass the sub-1-share gate;
- treat SIGNAL_MODE PnL as executable PnL.

The only approved next work is paper-only research and observability.

---

## 9. Recommended Next Paper-Only Step

Recommended next action:

```text
Build a docs/research standard-mode sizing projection table first.
```

Inputs:

- the 440 completed trades from the Share Size Reality Report;
- tier ladder from the capital ladder audit;
- entry price, shares, notional, and PnL fields;
- hypothetical bankroll levels: `$100`, `$150`, `$250`, `$500`.

Outputs:

- projected `shares`;
- projected `notional`;
- `>= 1 share` pass rate;
- `>= $1 notional` pass rate;
- `executable_candidate_count`;
- `signal_pnl` versus `executable_pnl` placeholder;
- unresolved standard multiplier assumptions.

This should be a report only. It should not change runtime behavior.

---

## Governor Verdict

`STANDARD_PAPER_EXECUTABILITY_MODE_DESIGN_READY`

The project should remain in `SIGNAL_MODE` until the bankroll or controlled paper state reaches at least `$100`. The first standard-mode milestone is paper-only measurement of actual standard sizing. Live trading remains explicitly forbidden.
