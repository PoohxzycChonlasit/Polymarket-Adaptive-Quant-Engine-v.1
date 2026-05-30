# 09h10h Early Failure Filter Design

Date: 2026-05-24

Scope: docs-only design for a future paper/replay policy concept.

Runtime behavior changed: No  
Live behavior changed: No

## Purpose

Design a future research-only policy concept for the `09h10h + 0.50-0.70` signal bucket:

```text
If a trade fails within 0-30s, cut or confirm stop.
If a trade survives 30s with favorable state, allow hold, runner, or profit management.
```

This is not a runtime rule. It is a replay hypothesis to test whether the observed 09h10h survival structure is real or sample noise.

## Sources

- `docs/research/session_09h10h_structural_edge.md`
- `docs/research/positive_expectancy_zone_deep_dive.md`
- `docs/research/dynamic_executable_expectancy_audit.md`

## Evidence Basis

Observed 09h10h structural pattern:

| Hold Bucket | Trades | TP | SL | Signal PnL | Read |
|---|---:|---:|---:|---:|---|
| `0-5s` | `4` | `0` | `4` | `-$0.031055` | immediate adverse selection |
| `5-15s` | `9` | `5` | `4` | `+$0.015933` | mixed but positive |
| `15-30s` | `8` | `4` | `4` | `+$0.003834` | balanced, slight positive |
| `30s+` | `6` | `6` | `0` | `+$0.080666` | strongest survival zone |

Fast exit facts:

- `8/12` SL occurred within `15s`.
- `12/12` SL occurred within `30s`.
- `6/6` trades that survived past `30s` were TP in the current sample.

Design implication:

The candidate filter is not "take profit faster." It is:

```text
detect early failure quickly, then let true survivors breathe.
```

## Policy Concept

Name:

```text
09h10h_EARLY_FAILURE_FILTER_V1
```

Mode:

```text
PAPER_REPLAY_ONLY
```

Eligible research bucket:

| Field | Required Value |
|---|---|
| session hour | `09h` or `10h` UTC |
| entry price | `0.50 <= entry_price < 0.70` |
| evidence mode | `SIGNAL_MODE` |
| lifecycle | `OPENING_SCAN` or `ACTIVE_INVENTORY_TRADING` |
| asset | BTC or ETH |
| side | YES or NO |

Explicit non-goals:

- no runtime activation;
- no live activation;
- no stop-loss change;
- no risk change;
- no position sizing change;
- no martingale;
- no reload;
- no averaging down;
- no execution routing change.

## Early Failure Condition

Early failure window:

```text
0s <= hold_seconds <= 30s
```

A replay row should be classified as early failure when any of the following is true inside the early window:

| Condition | Required Fields | Meaning |
|---|---|---|
| stop event observed | `trade_result=SL` or exit reason contains stop loss | current exit system already closed the trade as failure |
| adverse price move | `entry_price`, mark/exit/proxy price, side | price moved against entry before 30s |
| no favorable excursion | `mfe_candidate_price`, `mae_candidate_price`, entry price | trade never developed positive excursion before failure |
| stale adverse quote | `quote_stale_ms`, `quote_age_at_fill_ms`, mark/exit price | stale or delayed quote coincides with early loss |

Replay classification:

```text
EARLY_FAILURE_CONFIRMED
EARLY_FAILURE_PROBABLE
EARLY_FAILURE_UNPROVEN
```

Design rule:

If `EARLY_FAILURE_CONFIRMED`, the replay policy should keep or accelerate the stop outcome. It should not allow runner logic.

Stop-loss preservation:

The design does not loosen the existing stop. Existing stop-loss wins over the future filter. The filter can only confirm early failure in replay, not bypass or delay protective exit.

## Survivor Condition

Survivor checkpoint:

```text
hold_seconds >= 30s
```

A replay row should be classified as a survivor only if the trade reaches the checkpoint and has favorable state evidence.

Required survivor state:

| Field | Condition |
|---|---|
| `hold_seconds` | `>= 30` |
| `trade_result` or replay mark | not already SL before 30s |
| price state | not below stop threshold at checkpoint |
| quote freshness | `quote_stale_ms` present or freshness class known |
| market state | orderbook or quote state not unavailable |
| lifecycle state | still inside valid 09h10h bucket context |

Survivor classifications:

```text
SURVIVOR_CONFIRMED
SURVIVOR_PROBABLE
SURVIVOR_UNPROVEN
```

Design rule:

Only `SURVIVOR_CONFIRMED` rows may be tested for runner or profit-management replay variants.

## Runner Eligibility

Runner eligibility is a second gate after survival. It is not automatic.

Eligible only when:

| Requirement | Rule |
|---|---|
| survivor status | `SURVIVOR_CONFIRMED` |
| unrealized state | favorable or at least not adverse at 30s |
| quote freshness | not stale beyond the replay threshold being tested |
| lifecycle | `OPENING_SCAN` or 09h10h-specific positive ACTIVE pocket |
| executable overlay | label retained as SIGNAL_ONLY unless executable checks pass |
| risk state | no drawdown, LOCKDOWN, or risk-state block in replay row |

Runner modes to replay:

| Mode | Meaning |
|---|---|
| `NO_RUNNER_BASELINE` | keep existing behavior as control |
| `HOLD_TO_CURRENT_TP` | allow current TP logic only |
| `PROFIT_MANAGEMENT_REDUCE` | simulated partial take-profit after favorable excursion |
| `RUNNER_TO_TIME_CAP` | allow a small runner until a fixed time cap |

Hard limits:

- no reload;
- no averaging down;
- no martingale;
- no increased size;
- no live execution;
- no bypass of stop-loss or forced-exit safety.

## Required Fields

Minimum fields for replay:

| Field | Purpose |
|---|---|
| `run_id` | prevent cross-run joins |
| `paper_trade_replay_key` | match open, execution, close rows |
| `timestamp_utc` | derive hour/session |
| `asset` / `ticker` | BTC vs ETH split |
| `side` / `outcome` | YES vs NO split |
| `entry_price` | price bucket and adverse/favorable movement |
| `exit_price` | realized close comparison |
| `trade_result` | TP/SL truth |
| `pnl_usdc` | signal PnL |
| `hold_seconds` | early failure vs survivor classification |
| `reason` | exit reason distribution |
| `lifecycle_phase` | OPENING vs ACTIVE split |
| `seconds_remaining` | time remaining at entry |
| `quote_stale_ms` | quote freshness |
| `quote_age_at_submit_ms` | submit quote age |
| `quote_age_at_fill_ms` | fill quote age |
| `quote_source` | quote provenance |
| `executable_book_state` | microstructure state |
| `executable_spread_state` | spread state proxy |
| numeric spread if available | actual spread cost |
| `mfe_candidate_price` | favorable excursion proxy |
| `mae_candidate_price` | adverse excursion proxy |

Optional but high-value fields:

- mark price at 5s, 15s, 30s;
- top bid/ask depth at entry and checkpoint;
- spread at entry and checkpoint;
- stop threshold active at entry;
- risk mode and bankroll tier;
- executable overlay class.

## Missing Evidence

Current blockers before implementation:

| Missing / Weak Evidence | Why It Matters |
|---|---|
| numeric spread missing on matched rows | cannot quantify microstructure cost |
| quote freshness coverage only `8/27` for 09h10h | weak stale-quote confidence |
| no checkpoint mark at exactly 30s | cannot prove favorable state at survivor checkpoint |
| MFE/MAE not mature enough for policy replay | hard to distinguish lucky hold from structural continuation |
| all trades are dust-zone | no executable PnL evidence |
| cross-date recurrence is mixed | edge may be cluster-driven |
| sample size is small | `27` target rows, only `6` confirmed 30s+ survivors |

## Evidence Gates Before Implementation

Minimum gates before any runtime implementation can even be considered:

| Gate | Minimum |
|---|---:|
| target bucket trades | `>= 100` |
| target bucket dates | `>= 7` complete dates |
| 30s+ survivor trades | `>= 25` |
| 30s+ survivor TP rate | `>= 60%` |
| 0-30s early-failure classification coverage | `>= 90%` |
| quote freshness coverage | `>= 80%` |
| numeric spread coverage | `>= 80%` |
| checkpoint mark coverage at 30s | `>= 80%` |
| executable eligible trades | `> 0`, tracked separately |
| 02h negative-control persistence | still materially worse than 09h10h |

Recommended higher-confidence gates:

| Gate | Preferred |
|---|---:|
| target bucket trades | `>= 200` |
| target bucket dates | `>= 14` complete dates |
| 30s+ survivor trades | `>= 50` |
| executable eligible trades | `>= 30` |

## Sample Size Needed

Current state:

```text
09h10h + 0.50-0.70 trades = 27
30s+ survivors = 6
executable trades = 0
```

Minimum research sample:

```text
100 target trades
25 survivor rows
7 complete dates
```

Implementation-quality paper sample:

```text
200 target trades
50 survivor rows
14 complete dates
30 executable-eligible rows if executable overlay is part of the claim
```

Interpretation:

The idea is interesting enough to replay-test, but far too early for runtime policy.

## Replay Test Design

Replay first, no runtime.

### Step 1: Build Baseline Ledger

Filter historical matched trades:

```text
hour in (09, 10)
0.50 <= entry_price < 0.70
mode = paper
valid trade_result or proxy outcome
```

Compute:

- TP/SL;
- signal PnL;
- expectancy;
- profit factor;
- hold bucket;
- lifecycle split;
- side split;
- asset split;
- quote freshness;
- executable overlay.

### Step 2: Add Checkpoint Ledger

Create replay-only checkpoint rows:

```text
5s
15s
30s
```

For each checkpoint, attach:

- mark/exit proxy price;
- favorable/adverse state;
- quote age;
- spread state;
- lifecycle state;
- time remaining.

### Step 3: Simulate Early Failure Filter

Replay variants:

| Variant | Rule |
|---|---|
| `BASELINE` | current paper result |
| `CUT_AT_15_IF_ADVERSE` | cut if adverse at 15s |
| `CUT_AT_30_IF_ADVERSE` | cut if adverse at 30s |
| `CONFIRM_STOP_ONLY` | no earlier cut, just label early stop confirmation |
| `SURVIVOR_HOLD` | if not adverse by 30s, allow current TP logic |
| `SURVIVOR_RUNNER_LIMITED` | if favorable by 30s, allow bounded runner simulation |

### Step 4: Compare Against Controls

Controls:

- `02h + 0.50-0.70`;
- `16h + 0.50-0.70`;
- all other `0.50-0.70`;
- 09h10h outside `0.50-0.70`.

Required comparisons:

- Does filter improve 09h10h but not 02h?
- Does 30s survival still predict TP on new dates?
- Does it help both BTC and ETH?
- Does it help both YES and NO?
- Does ACTIVE remain positive?
- Does spread/quote staleness erase the edge?

### Step 5: Separate Signal vs Executable Ledgers

Every replay output must produce:

```text
signal_pnl
simulation_only_pnl
executable_pnl
executable_trade_count
dust_trade_count
```

No executable claim is allowed unless executable trade count is nonzero and separately reported.

## What Could Break

| Risk | Failure Mode |
|---|---|
| overfitting | 30s survivor pattern came from only `6` rows |
| stop-loss distortion | replay design accidentally loosens protective stops |
| survivor bias | only counting trades that already survived in completed outcomes |
| missing checkpoint truth | no real 30s mark means replay may infer favorable state incorrectly |
| quote staleness | stale quotes may make 30s state look better than executable reality |
| spread omission | normalized spread state may hide actual cost |
| dust evidence | tiny paper orders exaggerate feasibility |
| date instability | 09h10h has positive and negative dates |
| ACTIVE exception overfit | ACTIVE positive inside 09h10h may not repeat |
| side/asset drift | YES or ETH contribution may shift in future data |

Hard safety response:

If any replay variant requires widening stop-loss, increasing size, reloading, averaging down, or delaying a confirmed stop, reject the variant.

## Stop-Loss Preservation Rules

The future replay policy must obey:

```text
existing stop-loss remains authoritative
confirmed SL cannot become runner
runner cannot bypass forced exit
runner cannot bypass final derisk
runner cannot add size
```

Allowed replay action:

```text
earlier or equal exit
same stop behavior
post-30s profit-management simulation only when survivor state is confirmed
```

Forbidden replay action:

```text
widen stop
ignore stop
reload after SL
average down
increase notional
turn SL into hold by assumption
```

## No-Martingale / No-Reload Constraint

This design is a filter, not an inventory engine.

It must not:

- reload after early loss;
- add to a losing position;
- double size after SL;
- treat 02h losses as a recovery opportunity;
- use 30s survival as permission to increase exposure;
- change bankroll tier or risk budget.

## Answered Questions

1. What fields are required?

At minimum: `(run_id, paper_trade_replay_key)`, timestamp, hour, asset, side, lifecycle, entry price, exit price, trade result, PnL, hold seconds, exit reason, quote age/staleness, time remaining, orderbook/spread state, and MFE/MAE or checkpoint mark proxies.

2. What evidence is missing?

The biggest gaps are exact 30s mark truth, mature MFE/MAE, numeric spread, high quote-staleness coverage, executable-size rows, and enough 30s+ survivors across multiple dates.

3. What sample size is needed?

Minimum: `100` target-bucket trades, `25` 30s+ survivor rows, `7` complete dates. Preferred: `200` target-bucket trades, `50` survivor rows, `14` dates, and at least `30` executable-eligible rows before making executable-edge claims.

4. How to replay-test before runtime?

Create an offline ledger with baseline, early-cut, confirm-stop-only, survivor-hold, and limited-runner variants. Compare against 02h, 16h, and all other mid-price buckets. Report signal and executable ledgers separately.

5. What could break?

Overfitting, survivor bias, missing checkpoint truth, quote staleness, spread omission, dust sizing, and accidental stop-loss weakening. The design must reject any variant that loosens safety controls.

## Final Recommendation

```text
DESIGN_STATUS: REPLAY_CONCEPT_ONLY
RUNTIME_ACTIVATION: NO
STOPLOSS_CHANGE: NO
RISK_CHANGE: NO
LIVE_CHANGE: NO
NEXT_STEP: OFFLINE_REPLAY_SPEC
```

The early failure filter is a plausible research concept because current 09h10h evidence shows all observed SL occurred by 30s while all 30s+ survivors became TP. It is not implementation-ready. The correct next step is a paper/replay-only experiment with checkpoint truth and strict safety preservation.

Tests: not run; docs-only design.
