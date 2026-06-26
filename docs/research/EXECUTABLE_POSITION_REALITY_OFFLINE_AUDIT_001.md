# EXECUTABLE_POSITION_REALITY_OFFLINE_AUDIT_001

Date: 2026-06-20

Mode: READ ONLY / OFFLINE AUDIT

Runtime behavior changed: No
Config changed: No
Strategy/risk/execution changed: No
Sizer changed: No
Commits: No

## Objective

Replay historical paper trades through executable-reality tracks without changing runtime sizing or execution behavior.

## Source And Method

| Item | Value |
|---|---:|
| source directory | `runtime/quant_data/trade_journal/*.jsonl` |
| files scanned | `40` |
| lines scanned | `2337` |
| malformed rows | `0` |
| trade_open rows | `732` |
| trade_close rows | `1605` |
| unique open keys | `711` |
| matched open/close trades used | `708` |
| open trades excluded because not closed/matched | `3` |
| keys with duplicate close rows | `16` |

Actual paper order size uses `payload.notional_size` and `payload.receipt.filled_size`. `payload.min_fillable_size_usd` is book/liquidity metadata and is not used as actual order size.

`signal_pnl` is current dust-sized paper PnL from `trade_close.pnl_usdc`.

`executable_pnl_estimate_pass_only` counts PnL only for rows whose actual paper size passes the track. Because current fills are dust-sized, this is zero for all non-dust tracks.

`counterfactual_scaled_pnl_estimate` scales each matched trade by the track-required shares using observed PnL per share. This is a diagnostic estimate only, not executable fill proof.

## Track Summary

| Track | Trade Count | Pass | Reject | Pass Rate | Signal PnL | Executable PnL Estimate Pass-Only | Counterfactual Scaled PnL Estimate | Median Required Notional | Median Required Shares | Top Reject Reasons |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `current_dust` | `708` | `708` | `0` | `100.00%` | `$-0.275395` | `$-0.275395` | `$-0.275395` | `$0.050271` | `0.095032` | - |
| `min_1_usd` | `708` | `0` | `708` | `0.00%` | `$-0.275395` | `$0.000000` | `$-6.676416` | `$1.000000` | `1.886792` | below_minimum_practical_notional=708 |
| `min_5_shares` | `708` | `0` | `708` | `0.00%` | `$-0.275395` | `$0.000000` | `$-17.867314` | `$2.650000` | `5.000000` | below_minimum_practical_shares=708 |
| `min_10_shares` | `708` | `0` | `708` | `0.00%` | `$-0.275395` | `$0.000000` | `$-35.734628` | `$5.300000` | `10.000000` | below_minimum_practical_shares=708 |
| `min_5_usd` | `708` | `0` | `708` | `0.00%` | `$-0.275395` | `$0.000000` | `$-33.382081` | `$5.000000` | `9.433962` | below_minimum_practical_notional=708 |

## Comparison Table

| Reality | Track | Current Pass Rate | Median Required Notional | Median Required Shares | Interpretation |
|---|---|---:|---:|---:|---|
| Current Dust Reality | `current_dust` | `100.00%` | `$0.050271` | `0.095032` | Current signal ledger; not executable truth. |
| Min 1 USD Reality | `min_1_usd` | `0.00%` | `$1.000000` | `1.886792` | All current trades fail; smallest notional realism already collapses actual filled frequency. |
| Min 5 Shares Reality | `min_5_shares` | `0.00%` | `$2.650000` | `5.000000` | All current trades fail; conservative practical-share track requires about 50x current median shares. |
| Min 10 Shares Reality | `min_10_shares` | `0.00%` | `$5.300000` | `10.000000` | All current trades fail; stricter execution realism requires about 100x current median shares. |
| Min 5 USD Reality | `min_5_usd` | `0.00%` | `$5.000000` | `9.433962` | All current trades fail; strong bankroll-realism track is incompatible with current paper sizing. |

## Required Size Distributions

| Track | Required Notional Min | Required Notional Median | Required Notional Max | Required Shares Min | Required Shares Median | Required Shares Max |
|---|---:|---:|---:|---:|---:|---:|
| `current_dust` | `$0.012615` | `$0.050271` | `$0.189061` | `0.020346` | `0.095032` | `0.450145` |
| `min_1_usd` | `$1.000000` | `$1.000000` | `$1.000000` | `1.315789` | `1.886792` | `3.333333` |
| `min_5_shares` | `$1.500000` | `$2.650000` | `$3.800000` | `5.000000` | `5.000000` | `5.000000` |
| `min_10_shares` | `$3.000000` | `$5.300000` | `$7.600000` | `10.000000` | `10.000000` | `10.000000` |
| `min_5_usd` | `$5.000000` | `$5.000000` | `$5.000000` | `6.578947` | `9.433962` | `16.666667` |

## Questions

### 1. At what threshold does trade frequency collapse?

Trade frequency collapses immediately at `min_1_usd`. Current actual paper fills have a `0 / 708` pass count at `$1` notional, `5 shares`, `10 shares`, and `$5` notional. The current paper regime is therefore entirely dust-sized.

### 2. At what threshold does expected PnL materially change?

Actual executable PnL changes materially at the first executable threshold, `min_1_usd`, because pass-only executable PnL drops from the current dust signal ledger to `$0.000000` for all non-dust tracks. Counterfactual scaled PnL changes in magnitude as required size increases, but this is only a diagnostic estimate and is not executable evidence because no current rows pass the size constraints.

### 3. Which threshold is most realistic for future paper execution mode?

The most realistic first paper execution threshold is `min_5_shares`. It is more microstructure-relevant than `$1` notional because Polymarket executability is share/depth constrained, while still less severe than `min_10_shares` or `min_5_usd`. A `min_1_usd` track can remain a softer diagnostic track, but it should not be the main execution-mode gate.

### 4. Do current research conclusions survive executable reality constraints?

They survive only as SIGNAL_MODE conclusions. They do not survive as executable PnL or live-readiness conclusions. Current Option D, Delta Extreme Shadow, Micro Recovery, Entry Funnel, and low-price evidence must be reported as signal/candidate/lifecycle evidence until a future shadow overlay or paper execution mode produces rows that pass executable tracks.

## Audit Interpretation

- Current dust paper is useful for signal lifecycle and candidate discovery.
- Current dust paper is not useful for executable-size PnL claims.
- The first executable threshold already eliminates all actual filled rows.
- Counterfactual scaled estimates can guide research priority, but must not be promoted to execution truth.
- `min_5_shares` is the best candidate threshold for future paper execution mode because it aligns with share/depth realism.

## Promotion Implication

The next safe step is a shadow overlay that emits or compiles executable track labels without changing sizing or order behavior. The overlay should prove field coverage, reject reason stability, and depth/spread/freshness availability before any paper execution sizing experiment.

## Final Verdict

`READY_FOR_SHADOW_OVERLAY`

Reason: the offline audit establishes a deterministic and severe separation between current SIGNAL_MODE dust fills and executable-size reality. The next useful step is shadow labeling/telemetry, not a sizing or execution change.
