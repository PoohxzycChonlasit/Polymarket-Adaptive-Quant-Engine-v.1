# EXECUTION_TRACK_PROFITABILITY_AUDIT_001

Date: 2026-06-20

Mode: READ ONLY / DOCS ONLY

Runtime behavior changed: No

Strategy/risk/execution changed: No

Commit status: Not committed

## Objective

Determine which execution track is the most viable future execution-paper validation track:

- `1_share`
- `2_share`
- `5_share`
- `10_share`

This audit uses the existing execution reality audit set and read-only trade-journal replay math. It does not change code, runtime, sizing, strategy, risk, config, Option D, Delta Shadow, or live behavior.

## Source And Coverage

| Item | Value |
|---|---:|
| trade journal files scanned | `40` |
| trade journal lines scanned | `2337` |
| malformed trade journal rows | `0` |
| trade_open rows | `732` |
| trade_close rows | `1605` |
| matched open/close trades used | `708` |
| duplicate close keys | `16` |
| Option D stop rows parsed | `12` |

Primary supporting docs:

- `docs/research/CAPITAL_TRUTH_AUDIT_001.md`
- `docs/research/EXECUTION_REALITY_LIQUIDITY_AUDIT_001.md`
- `docs/research/EXECUTION_REALITY_OPTION_D_AUDIT_001.md`
- `docs/research/EXECUTION_BANKROLL_AND_SURVIVABILITY_AUDIT_001.md`
- `docs/research/EXECUTION_REALITY_GAP_AUDIT_001.md`

## Section 1 - Track Replay

Fixed-share replay uses the same matched trade sequence scaled to each target share size. Profit factor and win rate are therefore path-invariant across tracks; absolute PnL and drawdown scale linearly with shares.

Gross profit and gross loss below are derived from the canonical capital replay net PnL and rounded PF from `CAPITAL_TRUTH_AUDIT_001`, so they should be treated as approximate audit-level values, not cent-perfect accounting.

| Track | Trade Count | Gross Profit | Gross Loss | Net PnL | Profit Factor | Win Rate |
|---|---:|---:|---:|---:|---:|---:|
| `1_share` | `708` | `$31.120353` | `$34.693816` | `$-3.573463` | `0.897` | `37.85%` |
| `2_share` | `708` | `$62.240705` | `$69.387631` | `$-7.146926` | `0.897` | `37.85%` |
| `5_share` | `708` | `$155.601754` | `$173.469068` | `$-17.867314` | `0.897` | `37.85%` |
| `10_share` | `708` | `$311.203508` | `$346.938136` | `$-35.734628` | `0.897` | `37.85%` |

Profitability finding:

```text
No track is profitable on the historical replay.
```

Absolute-loss ranking:

1. `1_share`
2. `2_share`
3. `5_share`
4. `10_share`

Per-dollar profitability ranking:

```text
TIE
```

because all tracks scale the same underlying trade path.

## Section 2 - Capital Efficiency

Total deployed notional is computed as:

```text
sum(entry_price * track_shares) across matched trades
```

Observed sum of 1-share entry prices across the matched sample:

```text
373.19
```

| Track | Total Deployed Notional | Net PnL | PnL / Dollar Deployed | Max Drawdown | Drawdown / Dollar Deployed | Capital Efficiency Score |
|---|---:|---:|---:|---:|---:|---:|
| `1_share` | `$373.19` | `$-3.573463` | `-0.9575%` | `$6.557907` | `1.7573%` | `72.85` |
| `2_share` | `$746.38` | `$-7.146926` | `-0.9575%` | `$13.115814` | `1.7573%` | `72.85` |
| `5_share` | `$1865.95` | `$-17.867314` | `-0.9575%` | `$32.789535` | `1.7573%` | `72.85` |
| `10_share` | `$3731.90` | `$-35.734628` | `-0.9575%` | `$65.579070` | `1.7573%` | `72.85` |

Score definition:

```text
capital_efficiency_score =
100
- abs(PnL / Dollar Deployed * 1000)
- Drawdown / Dollar Deployed * 1000
```

Interpretation:

- Capital efficiency per dollar deployed is identical because all tracks scale the same historical path.
- Track selection cannot be justified by per-dollar profitability alone.
- The decision must come from survivability, liquidity realism, and whether the size is meaningful enough to validate execution.

## Section 3 - Liquidity Stress

Liquidity results use top-of-book trade-open fields from `EXECUTION_REALITY_LIQUIDITY_AUDIT_001`.

| Track | Entry Depth Pass | Entry Depth Fail | Round-Trip Depth Pass | Round-Trip Depth Fail | Round-Trip Reject % | Spread Normalized | Size Pressure |
|---|---:|---:|---:|---:|---:|---:|---|
| `1_share` | `702 / 708` | `6` | `700 / 708` | `8` | `1.13%` | `100.00%` | Low |
| `2_share` | `699 / 708` | `9` | `694 / 708` | `14` | `1.98%` | `100.00%` | Low |
| `5_share` | `680 / 708` | `28` | `669 / 708` | `39` | `5.51%` | `100.00%` | Moderate |
| `10_share` | `631 / 708` | `77` | `606 / 708` | `102` | `14.41%` | `100.00%` | High |

Liquidity interpretation:

- `1_share` and `2_share` have the best top-of-book feasibility, but they are weaker execution-realism tests.
- `5_share` has acceptable but non-trivial liquidity stress and is the best practical validation candidate.
- `10_share` introduces materially higher depth rejection and size pressure.

Slippage sensitivity:

- `1_share`: lowest sensitivity.
- `2_share`: low sensitivity.
- `5_share`: moderate sensitivity; useful for realistic paper validation.
- `10_share`: high sensitivity; should remain a stress track until more evidence exists.

## Section 4 - Survivability

Bankroll survivability from `CAPITAL_TRUTH_AUDIT_001`:

| Track | Bankroll | Final Equity | Max Drawdown | Max Drawdown % | Risk Of Ruin | Classification |
|---|---:|---:|---:|---:|---|---|
| `1_share` | `$100` | `$96.426537` | `$6.557907` | `6.41%` | `False` | `PASS` |
| `1_share` | `$250` | `$246.426537` | `$6.557907` | `2.60%` | `False` | `PASS` |
| `1_share` | `$500` | `$496.426537` | `$6.557907` | `1.31%` | `False` | `PASS` |
| `2_share` | `$100` | `$92.853074` | `$13.115814` | `12.53%` | `False` | `PASS` |
| `2_share` | `$250` | `$242.853074` | `$13.115814` | `5.15%` | `False` | `PASS` |
| `2_share` | `$500` | `$492.853074` | `$13.115814` | `2.60%` | `False` | `PASS` |
| `5_share` | `$100` | `$82.132686` | `$32.789535` | `29.34%` | `False` | `CAUTION` |
| `5_share` | `$250` | `$232.132686` | `$32.789535` | `12.53%` | `False` | `PASS` |
| `5_share` | `$500` | `$482.132686` | `$32.789535` | `6.41%` | `False` | `PASS` |
| `10_share` | `$100` | `$64.265372` | `$65.579070` | `53.08%` | `False` | `FAIL` |
| `10_share` | `$250` | `$214.265372` | `$65.579070` | `23.97%` | `False` | `CAUTION` |
| `10_share` | `$500` | `$464.265372` | `$65.579070` | `12.53%` | `False` | `PASS` |

Survivability ranking:

1. `1_share`
2. `2_share`
3. `5_share`
4. `10_share`

Execution-validation usefulness ranking:

1. `5_share`
2. `2_share`
3. `10_share`
4. `1_share`

Reason:

`1_share` survives best but is the weakest practical execution-mode validation. `5_share` is the first track that meaningfully tests execution reality while staying viable at `$250+`.

## Section 5 - Option D

Option D fixed-share stop subset:

| Track | Stops | Saved Loss Count | Destroyed Profit Count | Saved Losses | Destroyed Profits | Net Value Added | Actual Stop PnL | Hold-To-Expiry PnL | Whipsaw Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `1_share` | `12` | `7` | `5` | `$2.480000` | `$2.640000` | `$-0.160000` | `$-1.300000` | `$-1.140000` | `41.67%` |
| `2_share` | `12` | `7` | `5` | `$4.960000` | `$5.280000` | `$-0.320000` | `$-2.600000` | `$-2.280000` | `41.67%` |
| `5_share` | `12` | `7` | `5` | `$12.400000` | `$13.200000` | `$-0.800000` | `$-6.500000` | `$-5.700000` | `41.67%` |
| `10_share` | `12` | `7` | `5` | `$24.800000` | `$26.400000` | `$-1.600000` | `$-13.000000` | `$-11.400000` | `41.67%` |

Option D interpretation:

- Option D does not improve net PnL in the documented fixed-share stop subset.
- Option D may reduce some drawdown, but destroyed-profit magnitude offsets saved-loss magnitude.
- Option D should remain a shadow comparison during execution-track validation.
- No track should promote Option D as an execution stop rule from this evidence alone.

## Section 6 - Track Ranking

### Profitability Ranking

| Rank | Track | Reason |
|---:|---|---|
| `1` | `1_share` | smallest absolute loss |
| `2` | `2_share` | second smallest absolute loss |
| `3` | `5_share` | larger absolute loss, same negative PF |
| `4` | `10_share` | largest absolute loss |

Per-dollar profitability is tied and negative across all tracks.

### Survivability Ranking

| Rank | Track | Reason |
|---:|---|---|
| `1` | `1_share` | passes all tested bankrolls with low drawdown |
| `2` | `2_share` | passes all tested bankrolls with manageable drawdown |
| `3` | `5_share` | needs `$250+` for clean validation |
| `4` | `10_share` | too drawdown-heavy below `$500` |

### Liquidity Realism Ranking

| Rank | Track | Reason |
|---:|---|---|
| `1` | `5_share` | best balance of practical size and manageable depth rejection |
| `2` | `2_share` | good feasibility, but less realistic as an execution validation target |
| `3` | `1_share` | easiest fill, weakest execution-reality test |
| `4` | `10_share` | high depth pressure and slippage sensitivity |

### Capital Efficiency Ranking

| Rank | Track | Reason |
|---:|---|---|
| `1` | all tracks tied | same path-scaled PnL per dollar deployed |

### Composite Track Ranking

| Rank | Track | Summary |
|---:|---|---|
| `1` | `5_share` | best validation track despite negative replay, because it is practical and survivable at `$250+` |
| `2` | `2_share` | best fallback track if operator wants lower drawdown and less liquidity stress |
| `3` | `1_share` | safe diagnostic track, but too weak as primary validation |
| `4` | `10_share` | useful only as stress track |

## Final Verdict

Best track:

```text
5_share
```

Worst track:

```text
10_share
```

Recommended validation track:

```text
5_share
```

Recommended fallback track:

```text
2_share
```

Promotion recommendation:

```text
Do not promote any track to execution claims yet.
Use 5_share as the primary Execution Paper Runtime validation track,
with 2_share as the fallback survivability track and 10_share as stress-only.
```

Reason:

All tracks are negative on historical replay and have identical per-dollar profitability because the same path is scaled. The purpose of the next phase is not to choose the smallest loss, but to find the smallest realistic track that can validate executable behavior without immediate bankroll failure. `5_share` is the best balance of execution realism, liquidity feasibility, and survivability when paired with a recommended `$250+` bankroll.

