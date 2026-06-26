# EXECUTABLE_REALITY_SHADOW_OVERLAY_SPEC_001

Date: 2026-06-20

Mode: DESIGN ONLY

Runtime behavior changed: No
Config changed: No
Strategy/risk/execution changed: No
Sizer changed: No
Commits: No

## Objective

Design a passive runtime shadow overlay that labels paper trades with executable-reality fields while preserving current dust-sized SIGNAL_MODE paper execution.

The overlay must answer:

```text
Would this paper trade have passed realistic executable-size constraints?
```

without changing:

```text
position size
order placement
risk approval
stop loss
take profit
strategy
live behavior
```

## Context

`EXECUTABLE_POSITION_REALITY_OFFLINE_AUDIT_001` found:

| Track | Pass Rate |
|---|---:|
| `current_dust` | `100.00%` |
| `min_1_usd` | `0.00%` |
| `min_5_shares` | `0.00%` |
| `min_10_shares` | `0.00%` |
| `min_5_usd` | `0.00%` |

Matched paper trades analyzed: `708`

Current paper mode is therefore:

```text
SIGNAL_MODE only
```

Executable PnL is not proven.

## 1. Event Schema

Recommended JSONL event:

```text
event_type = executable_reality_shadow
```

Recommended storage:

```text
runtime/quant_data/executable_reality_shadow/YYYY-MM-DD.jsonl
```

Required fields:

| Field | Type | Meaning |
|---|---|---|
| `timestamp_utc` | string | event timestamp in UTC |
| `run_id` | string/null | active runtime run id |
| `market` | string/null | market id, market key, or slug |
| `asset` | string/null | BTC or ETH |
| `side` | string/null | selected YES/NO side |
| `token_id` | string/null | selected token id |
| `condition_id` | string/null | market condition id, recommended for joins |
| `epoch_start_ts` | int/null | 5-minute market epoch start |
| `paper_trade_replay_key` | string/null | canonical trade join key when available |
| `position_id` | string/null | paper position id when available |
| `entry_price` | float/null | actual paper entry price |
| `paper_notional` | float/null | actual paper notional, from `payload.notional_size` |
| `paper_shares` | float/null | actual paper shares, from fill receipt |
| `spread` | float/null | entry spread if available |
| `bid_size` | float/null | relevant top bid size if available |
| `ask_size` | float/null | relevant top ask size if available |
| `quote_age_ms` | int/null | orderbook quote age if available |
| `oracle_age_ms` | int/null | oracle or price-feed age if available |
| `seconds_remaining` | int/null | seconds remaining in the market at entry |
| `track_current_dust_pass` | bool | true when current dust paper evidence is usable |
| `track_min_1_usd_pass` | bool | true when actual paper size clears `$1` notional |
| `track_min_5_shares_pass` | bool | true when actual paper size clears `5` shares |
| `track_min_10_shares_pass` | bool | true when actual paper size clears `10` shares |
| `track_min_5_usd_pass` | bool | true when actual paper size clears `$5` notional |
| `required_notional_min_1_usd` | float/null | always `1.00` when entry price exists |
| `required_notional_min_5_shares` | float/null | `entry_price * 5` |
| `required_notional_min_10_shares` | float/null | `entry_price * 10` |
| `required_notional_min_5_usd` | float/null | always `5.00` when entry price exists |
| `required_shares_min_1_usd` | float/null | `1.00 / entry_price` |
| `required_shares_min_5_shares` | float/null | `5.00` |
| `required_shares_min_10_shares` | float/null | `10.00` |
| `required_shares_min_5_usd` | float/null | `5.00 / entry_price` |
| `executable_reject_reason` | string/null | primary reject reason for the strongest selected track |
| `executable_truth_class` | string | executable classification |

Recommended extra fields:

| Field | Type | Meaning |
|---|---|---|
| `shadow_subject_type` | string | `paper_trade_open` for v1; future `decision_signal` if expanded |
| `executable_overlay_version` | string | schema version, e.g. `1.0` |
| `source_event_type` | string | source event, e.g. `trade_open` |
| `source_module` | string/null | emitting module |
| `lifecycle_phase` | string/null | OPENING_SCAN or ACTIVE_INVENTORY_TRADING |
| `risk_mode` | string/null | NORMAL, DEFENSIVE, MICRO_RECOVERY, LOCKDOWN |
| `bankroll_tier_id` | string/null | tier id if available |
| `min_fillable_size_usd_metadata` | float/null | preserve as metadata only, never actual order size |

### executable_truth_class

Allowed values:

| Class | Meaning |
|---|---|
| `SIGNAL_ONLY_DUST` | current paper fill is valid signal evidence but not executable evidence |
| `LOW_REALISM` | clears `$1` but not `5` shares |
| `PRACTICAL` | clears `5` shares |
| `SAFE_EXECUTION_CANDIDATE` | clears `10` shares or `$5` notional plus depth/freshness checks |
| `UNKNOWN` | required fields missing |

Current expected class:

```text
SIGNAL_ONLY_DUST
```

## 2. Track Rules

All tracks are passive labels. They must never block or approve trades.

### current_dust

Pass logic:

```text
track_current_dust_pass =
    entry_price is not null
    and paper_notional is not null
    and paper_shares is not null
```

Reject reason:

```text
missing_entry_price
missing_paper_notional
missing_paper_shares
```

### min_1_usd

Required:

```text
required_notional_min_1_usd = 1.00
required_shares_min_1_usd = 1.00 / entry_price
```

Pass logic:

```text
track_min_1_usd_pass =
    paper_notional >= 1.00
```

Primary reject reason:

```text
below_minimum_practical_notional
```

### min_5_shares

Required:

```text
required_notional_min_5_shares = entry_price * 5
required_shares_min_5_shares = 5
```

Pass logic:

```text
track_min_5_shares_pass =
    paper_shares >= 5
    and paper_notional >= entry_price * 5
```

Primary reject reason order:

```text
missing_entry_price
missing_paper_shares
below_minimum_practical_shares
below_minimum_practical_notional
```

### min_10_shares

Required:

```text
required_notional_min_10_shares = entry_price * 10
required_shares_min_10_shares = 10
```

Pass logic:

```text
track_min_10_shares_pass =
    paper_shares >= 10
    and paper_notional >= entry_price * 10
```

Primary reject reason order:

```text
missing_entry_price
missing_paper_shares
below_minimum_practical_shares
below_minimum_practical_notional
```

### min_5_usd

Required:

```text
required_notional_min_5_usd = 5.00
required_shares_min_5_usd = 5.00 / entry_price
```

Pass logic:

```text
track_min_5_usd_pass =
    paper_notional >= 5.00
```

Primary reject reason:

```text
below_minimum_practical_notional
```

### executable_truth_class Selection

Recommended class selection:

```text
if required fields missing:
    UNKNOWN
elif track_min_10_shares_pass or track_min_5_usd_pass:
    SAFE_EXECUTION_CANDIDATE
elif track_min_5_shares_pass:
    PRACTICAL
elif track_min_1_usd_pass:
    LOW_REALISM
else:
    SIGNAL_ONLY_DUST
```

## 3. Hook Point

Candidate hooks:

| Option | Hook | Pros | Cons |
|---|---|---|---|
| A | paper trade open | has actual fill size, entry price, token, condition, run id, replay key | only labels filled paper trades |
| B | decision envelope | can label generated/approved signals before fill | lacks actual filled paper size and can confuse signal intent with trade evidence |
| C | trade close | has final PnL and exit price | too late to capture entry quote/depth/freshness cleanly |
| D | offline only | zero runtime risk | no fresh shadow telemetry during paper runtime |

Recommended hook:

```text
A. at paper trade open
```

Reason:

`_emit_trade_opened_event` already assembles the authoritative trade-open payload with:

- actual `entry_price`;
- actual `risk_plan.notional_size`;
- actual `risk_plan.position_size`;
- fill `receipt`;
- `token_id`;
- `condition_id`;
- `epoch_start_ts`;
- `paper_trade_replay_key`;
- lifecycle and model context.

This is the safest runtime hook because it records executable reality after paper sizing and simulated fill have happened, but before any close/PnL interpretation. It does not need to participate in decision approval, risk planning, order placement, or stop-loss logic.

Future v2 may add a decision-envelope shadow event for non-filled signals, but v1 should be trade-open only.

## 4. Logger Design

### Log Category

Recommended category:

```text
executable_reality_shadow
```

### Log Directory

Recommended directory:

```text
runtime/quant_data/executable_reality_shadow/YYYY-MM-DD.jsonl
```

Alternative if reusing `QuantEventLogger` category routing:

```text
runtime/quant_data/execution_log/YYYY-MM-DD.jsonl
```

Preferred:

```text
dedicated executable_reality_shadow directory
```

because it keeps passive feasibility labels separate from actual execution events.

### Fail-Soft Behavior

Rules:

- logger exceptions must be caught;
- logger failure must not block the trade;
- missing fields must emit `UNKNOWN` or a specific reject reason;
- no full orderbook snapshots;
- no secrets;
- no wallet addresses;
- no Telegram alerts;
- no blocking I/O in the trade path.

### Daily Size Estimate

Assumption:

```text
1 shadow row per paper trade_open
~1.5 KB to 3.0 KB per row uncompressed
```

Estimated size:

| Paper Trades / Day | Estimated JSONL / Day |
|---:|---:|
| `50` | `<0.15 MB` |
| `250` | `<0.75 MB` |
| `1,000` | `<3.00 MB` |
| `5,000` | `<15.00 MB` |

This is acceptable if logs remain one row per trade and do not include orderbook depth arrays.

## 5. Metrics

Daily shadow report fields:

| Metric | Definition |
|---|---|
| `total_paper_trades` | count of shadow rows |
| `dust_zone_pct` | `% executable_truth_class == SIGNAL_ONLY_DUST` |
| `min_1_usd_pass_pct` | `% track_min_1_usd_pass` |
| `min_5_shares_pass_pct` | `% track_min_5_shares_pass` |
| `min_10_shares_pass_pct` | `% track_min_10_shares_pass` |
| `min_5_usd_pass_pct` | `% track_min_5_usd_pass` |
| `top_reject_reasons` | count by `executable_reject_reason` |
| `signal_pnl` | sum of normal paper PnL from trade journal after close join |
| `executable_pnl_pass_only` | sum PnL only for rows passing a selected executable track |
| `scaled_pnl_estimate` | counterfactual PnL scaled by required shares, diagnostic only |

Recommended daily table:

| Track | Trades | Pass | Reject | Pass % | Signal PnL | Pass-Only Executable PnL | Scaled PnL Estimate |
|---|---:|---:|---:|---:|---:|---:|---:|
| `current_dust` | all | current dust pass | reject | pass rate | paper PnL | paper PnL | paper PnL |
| `min_1_usd` | all | pass | reject | pass rate | paper PnL | pass-only | scaled estimate |
| `min_5_shares` | all | pass | reject | pass rate | paper PnL | pass-only | scaled estimate |
| `min_10_shares` | all | pass | reject | pass rate | paper PnL | pass-only | scaled estimate |
| `min_5_usd` | all | pass | reject | pass rate | paper PnL | pass-only | scaled estimate |

## 6. Interaction With Existing Systems

### Option D

Option D remains signal evidence unless the overlay shows executable-track passes.

Required interpretation:

```text
Option D signal result != Option D executable result
```

### Delta Shadow

Delta Shadow may continue collecting signal-side evidence, but executable claims require:

```text
track_min_5_shares_pass == true
```

or a stricter explicitly selected track.

### Risk Modes

Risk modes must not be changed by this overlay.

The overlay should record `risk_mode` when available so later audits can determine whether `MICRO_RECOVERY` or other modes suppress executable-size feasibility.

### Entry Funnel

Entry Funnel should add a passive post-fill branch:

```text
paper_filled
  -> executable_shadow_current_dust
  -> executable_shadow_min_1_usd
  -> executable_shadow_min_5_shares
  -> executable_shadow_min_10_shares
  -> executable_shadow_min_5_usd
```

This branch is observability only. It must not alter admission, risk, or order submission.

### Paper PnL Reports

Paper PnL reports must split:

```text
signal_pnl
executable_pnl_pass_only
scaled_pnl_estimate
```

Rules:

- `signal_pnl` may include dust trades.
- `executable_pnl_pass_only` may include only rows passing the selected executable track.
- `scaled_pnl_estimate` must be labeled diagnostic and not actual fill evidence.

## 7. Safety Boundaries

Hard constraints:

- no sizing change;
- no order change;
- no execution change;
- no risk mode change;
- no stop-loss change;
- no take-profit change;
- no strategy change;
- no config change;
- no current runtime restart;
- no live trading;
- no Telegram spam;
- no full orderbook logging;
- no promotion of dust PnL to executable truth.

The active question `LOW_PRICE_TRUTH_RESOLUTION_001` still blocks strategy, sizer, execution, threshold, and inventory changes. This shadow overlay is allowed only as passive observability after separate implementation approval.

## 8. Promotion Gates

### DESIGN -> SHADOW IMPLEMENTATION

Required:

- this spec is accepted;
- implementation is scoped as observability only;
- tests prove no strategy/risk/execution imports or changes;
- event writer is fail-soft;
- output schema is deterministic;
- no restart is performed without operator approval.

Pass criteria:

- one shadow row per paper trade open;
- missing fields classified, not fatal;
- no runtime decision reads shadow labels;
- log size remains bounded.

### SHADOW -> PAPER EXECUTION MODE

Required:

- shadow overlay runs long enough to measure pass rates;
- reject reasons are stable;
- depth/spread/freshness coverage is adequate;
- `min_5_shares` or selected executable track has enough candidate frequency to justify a paper sizing experiment;
- operator explicitly approves a new paper execution mode task.

Pass criteria:

- shadow evidence proves the selected track is measurable;
- paper execution mode design is separately frozen;
- risk and bankroll impact are reviewed before any size change.

### PAPER EXECUTION MODE -> EXECUTABLE CLAIMS

Required:

- paper execution mode actually fills at selected executable size;
- PnL, drawdown, spread, slippage, stop-loss behavior, and partial-fill behavior are measured;
- official outcome truth and low-price settlement questions are resolved when relevant;
- no active governance question blocks promotion.

Pass criteria:

- executable PnL is based on actual executable-sized paper fills, not dust-scaled estimates;
- live readiness remains separately blocked until wallet, allowance, order, fill, cancel, and reconciliation are proven.

## Final Verdict

`READY_FOR_SHADOW_IMPLEMENTATION`

Reason:

The offline audit already proved that current paper fills are SIGNAL_MODE-only. A passive trade-open shadow overlay is the smallest safe next step because it records executable feasibility during live paper runtime without changing sizing, risk, order placement, stop-loss, strategy, or live behavior.

