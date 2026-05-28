# Executable Reality Monitor

Date: 2026-05-23

Scope: read-only monitor of latest paper evidence using the executable reality overlay.

Runtime behavior changed: No
Live behavior changed: No

## Verdict

Latest paper evidence is `SIGNAL_MODE` only.

Under the current conservative executable overlay:

```text
minimum practical shares = 5
minimum practical source = conservative_assumption
```

the latest matched paper trades are all:

```text
DUST_ZONE
SIMULATION_ONLY
```

Current paper PnL is not executable PnL. It should be used as signal/lifecycle/outcome-truth evidence only.

## Sources

- `docs/research/paper_sizing_audit.md`
- `docs/research/capital_ladder_audit.md`
- `docs/research/minimum_executable_reality_audit.md`
- `docs/research/executable_reality_overlay_design.md`
- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`
- `runtime/quant_data/decision_log/2026-05-23.jsonl`

## Latest Evidence Scope

Latest run:

```text
run_id = 20260523T160429Z_24512_1677a602
```

Latest run counts:

| Metric | Count |
|---|---:|
| trade_open | `4` |
| trade_close | `4` |
| matched paper trades | `4` |
| paper_fill events | `8` |

Same-day context from the latest trade journal:

| Metric | Count |
|---|---:|
| 2026-05-23 trade_open | `32` |
| 2026-05-23 trade_close | `32` |

The monitor below uses the latest run for classification.

## Overlay Rules

| Mode / Label | Rule | Current Result |
|---|---|---|
| `SIGNAL_MODE` | valid entry, exit, side, and `trade_result` | `4` trades |
| `EXECUTABLE_MODE` | must pass minimum practical shares and notional | `0` trades |
| `DUST_ZONE` | shares below minimum practical shares | `4` trades |
| `SIMULATION_ONLY` | signal-valid but not executable-realistic | `4` trades |

Assumed minimum:

```text
mos = 5 shares
minimum_executable_notional = mos * entry_price
```

Representative minimum notional:

| Price | Minimum Shares | Minimum Notional |
|---:|---:|---:|
| `0.20` | `5` | `$1.00` |
| `0.50` | `5` | `$2.50` |
| `0.80` | `5` | `$4.00` |

Latest run entry prices were `0.51-0.55`, so the estimated minimum executable notional range was:

```text
$2.55-$2.75
```

## Summary Numbers

| Field | Value |
|---|---:|
| total latest-run paper trades | `4` |
| signal-only trades | `4` |
| executable-realistic trades | `0` |
| dust-zone trades | `4` |
| simulation-only trades | `4` |
| executable_trade_count | `0` |
| dust_trade_count | `4` |
| current paper balance | about `$20.09-$20.10` |
| current tier | `T0_MICRO_SEED` |
| current family | `MICRO` |
| current mode | `MICRO_SURVIVAL` |
| current average notional | `$0.0503395` |
| current average shares | `0.095978` |
| estimated MOS threshold | `5 shares` |
| mean estimated minimum notional | `$2.625` |
| mean minimum multiple | `0.0192x` |

Interpretation:

The average paper trade is only about `1.92%` of the assumed minimum practical share size.

## PnL Split

| PnL Ledger | Value | Meaning |
|---|---:|---|
| `signal_pnl` | `-$0.01010051` | raw latest-run paper PnL, valid only as signal-mode evidence |
| `executable_pnl` | `N/A` | no executable-realistic trades passed the overlay |
| `simulation_only_pnl` | `-$0.01010051` | all latest-run PnL belongs to dust/simulation-only evidence |

Executable PnL claim:

```text
NO_EXECUTABLE_PNL
```

## Latest Examples

| UTC | Asset | Side | Entry | Shares | Notional | Min Notional @ 5 Shares | Minimum Multiple | Result | PnL | Class |
|---|---|---|---:|---:|---:|---:|---:|---|---:|---|
| 16:05:11 | ETH | NO | `0.53` | `0.095400` | `$0.050562` | `$2.65` | `0.01908x` | TP | `+$0.005724` | `SIMULATION_ONLY` |
| 16:10:37 | ETH | YES | `0.51` | `0.098553` | `$0.050262` | `$2.55` | `0.01971x` | TP | `+$0.007884` | `SIMULATION_ONLY` |
| 16:15:11 | ETH | NO | `0.51` | `0.098592` | `$0.050282` | `$2.55` | `0.01972x` | SL | `-$0.011831` | `SIMULATION_ONLY` |
| 16:20:25 | BTC | YES | `0.55` | `0.091367` | `$0.050252` | `$2.75` | `0.01827x` | SL | `-$0.011878` | `SIMULATION_ONLY` |

Depth note:

- ETH 16:15 had top ask/bid depth of only `3.00` shares, below the assumed `5` share practical size.
- BTC 16:20 had ample top depth, but the simulated order was still only `0.091367` shares.

So the dominant blocker is order size, not always displayed book depth.

## Executable Reality Classification

| Evidence Type | Count | Status |
|---|---:|---|
| `SIGNAL_MODE` | `4` | valid for signal/outcome analysis |
| `EXECUTABLE_MODE` | `0` | no executable-realistic evidence |
| `DUST_ZONE` | `4` | all trades below practical minimum |
| `SIMULATION_ONLY` | `4` | all PnL simulation-only |

## Bankroll Threshold

From `capital_ladder_audit.md` and `minimum_executable_reality_audit.md`:

| Bankroll | Expected Executable Reality |
|---:|---|
| `$20` | `SIMULATION_ONLY` |
| `$25-$99` | `LOW_REALISM` |
| `$100-$249` | `PRACTICAL` |
| `$250+` | `SAFE_EXECUTION` |

Answer:

```text
practical executable evidence begins around $100 bankroll
safe executable evidence begins around $250 bankroll
```

Current `$20` T0 paper evidence is too small for executable-PnL claims.

## 02h Session Addendum

Updated 2026-05-24 from `docs/research/session_edge/session_02h_fast_sl_audit.md`.

02h UTC classification:

```text
HOSTILE_SESSION_CANDIDATE
```

02h executable reality:

| Metric | Value |
|---|---:|
| 02h matched trades | `8` |
| 02h TP | `0` |
| 02h SL | `8` |
| SL <= 15s | `6/8` |
| SL <= 30s | `8/8` |
| median hold | `6.5s` |
| dust-zone trades | `8/8` |
| executable trades | `0/8` |
| signal PnL | `-$0.06515721` |
| executable PnL | `N/A` |

Interpretation:

02h is a negative signal bucket, not executable evidence. It should be excluded from positive session-edge claims and tracked separately as a hostile-session candidate. This does not authorize a runtime block, threshold change, stop-loss change, risk change, or live behavior change.

## Required Answers

1. Total paper trades:

Latest run: `4` matched paper trades. Same-day latest journal context: `32` opens and `32` closes.

2. Signal-only trades:

`4`.

3. Executable-realistic trades:

`0`.

4. Dust-zone trades:

`4`.

5. Current paper balance / tier:

About `$20.09-$20.10`, `T0_MICRO_SEED`, `MICRO`, `MICRO_SURVIVAL`.

6. Current average notional:

`$0.0503395`.

7. Current average shares:

`0.095978`.

8. Estimated MOS threshold:

`5 shares` by conservative assumption because authoritative minimum-order metadata was not available locally.

9. Whether PnL is executable or simulation-only:

Simulation-only. `executable_pnl` is not available because `executable_trade_count = 0`.

10. Bankroll level needed for practical executable evidence:

About `$100` for practical evidence; about `$250` for safer executable evidence.

## Monitor Status

```text
SIGNAL_MODE: ACTIVE
EXECUTABLE_MODE: NO_EVIDENCE
DUST_ZONE: 4/4
SIMULATION_ONLY: 4/4
EXECUTABLE_PNL: NONE
```

Recommended interpretation:

Keep using current paper results for signal, lifecycle, quote-staleness, and outcome-truth research. Do not use the current T0 dust-sized trades for executable-PnL or live-readiness claims.

Tests: not run; docs-only read-only monitor.
