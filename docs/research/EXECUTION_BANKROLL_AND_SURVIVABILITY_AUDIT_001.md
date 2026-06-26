# EXECUTION_BANKROLL_AND_SURVIVABILITY_AUDIT_001

Date: 2026-06-20

Mode: READ ONLY / DOCS ONLY

Runtime behavior changed: No

Strategy/risk/execution changed: No

Commit status: Not committed

## Objective

Determine whether `$20`, `$50`, `$100`, `$250`, and `$500` are viable starting bankrolls for a future `5_share` Execution Paper Runtime.

This audit does not change code, config, sizing, strategy, runtime, risk, Option D, Delta Shadow, or live behavior.

## Section 1 - Dataset

Primary sources:

- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`
- `OPTION_D_COUNTERFACTUAL_AUDIT_001.md`
- `OPTION_D_STOP_DISTRIBUTION_AUDIT_001.md`
- `docs/research/EXECUTION_REALITY_INVENTORY_AUDIT_001.md`
- `docs/research/EXECUTION_REALITY_LIQUIDITY_AUDIT_001.md`
- `docs/research/EXECUTION_REALITY_OPTION_D_AUDIT_001.md`
- `docs/research/CAPITAL_TRUTH_AUDIT_001.md`
- `docs/research/EXECUTION_REALITY_GAP_AUDIT_001.md`

Canonical sample from the execution reality audit set:

| Item | Count |
|---|---:|
| trade journal files scanned | `40` |
| trade journal lines scanned | `2337` |
| malformed trade journal rows | `0` |
| trade_open rows | `732` |
| trade_close rows | `1605` |
| matched open/close trades used | `708` |
| duplicate close keys | `16` |
| Option D stop rows parsed | `12` |

Path-truth note:

Path truth is supporting evidence for later MAE/MFE and markout analysis. The bankroll replay itself uses matched trade open/close outcomes because survivability is an equity-ledger question. Path truth should be required before future execution-mode stop or runner policies are promoted, but it is not the primary denominator for this bankroll audit.

## Section 2 - 5 Share Replay

Primary validation track:

```text
5_share fixed sizing
```

Canonical 5-share capital replay from `CAPITAL_TRUTH_AUDIT_001`:

| Metric | Value |
|---|---:|
| matched trades | `708` |
| total PnL / net PnL | `$-17.867314` |
| final equity on `$20` bankroll | `$2.132686` |
| max drawdown | `$32.789535` |
| profit factor | `0.897` |
| longest loss streak | `18` |
| recovery duration | `579` trades |
| observed risk of ruin on `$20` | `True` |

Supplemental direct trade-journal first-close replay check:

| Metric | Value |
|---|---:|
| matched trades | `708` |
| wins | `268` |
| losses | `440` |
| win rate | `37.85%` |
| gross profit | `$156.10` |
| gross loss | `$170.35` |
| net PnL | `$-14.25` |
| profit factor | `0.916` |

Interpretation:

The direct first-close replay is slightly less severe than the canonical capital audit, but both agree on the decision-bearing conclusion: fixed `5_share` replay is negative, drawdown is material, and `$20` is not survivable.

For bankroll decisions, this audit uses the more conservative canonical capital-audit path.

## Section 3 - Loss Streak Analysis

Canonical loss-streak findings:

| Metric | Value |
|---|---:|
| longest loss streak | `18` trades |
| 95th percentile loss streak | `7` trades |
| worst consecutive loss cluster at `5_share` | approximately `$-9.45` to `$-6.00` depending on replay convention |
| risk mode distribution near opens | `NORMAL=258`, `DEFENSIVE=51`, `MICRO_RECOVERY=53`, `UNKNOWN=346` |

Cluster behavior:

- Losses are not isolated one-off events.
- The longest observed loss streak is large enough to dominate a `$20` bankroll and materially stress a `$50` bankroll.
- The loss-streak shape is survivable only if the bankroll can absorb repeated fixed-share losses without forcing execution-mode risk state into permanent defense or shutdown.

## Section 4 - Drawdown Analysis

Canonical 5-share drawdown:

| Metric | Value |
|---|---:|
| max drawdown | `$32.789535` |
| max drawdown as % of `$20` bankroll | `103.20%` |
| max drawdown as % of `$50` bankroll | `53.08%` |
| max drawdown as % of `$100` bankroll | `29.34%` |
| max drawdown as % of `$250` bankroll | `12.53%` |
| max drawdown as % of `$500` bankroll | `6.41%` |
| recovery duration | `579` trades |

Interpretation:

- `$20` fails outright because max drawdown exceeds the bankroll.
- `$50` technically avoids final-account ruin in the replay, but a 53% drawdown is not a stable execution-validation base.
- `$100` survives but spends too much of the test in high drawdown pressure.
- `$250` is the first tier where the observed max drawdown is below 15%.
- `$500` is comfortable for validation but may be more capital than needed for the first execution-paper stage.

## Section 5 - Bankroll Tiers

| Starting Bankroll | Final Equity | Net PnL | Largest Drawdown % | Observed Ruin | Survivability | Classification |
|---:|---:|---:|---:|---|---|---|
| `$20` | `$2.132686` | `$-17.867314` | `103.20%` | `True` | Not survivable | `FAIL` |
| `$50` | `$32.132686` | `$-17.867314` | `53.08%` | `False` | Technically survives, operationally unstable | `FAIL` |
| `$100` | `$82.132686` | `$-17.867314` | `29.34%` | `False` | Survivable with material stress | `CAUTION` |
| `$250` | `$232.132686` | `$-17.867314` | `12.53%` | `False` | Practical validation tier | `PASS` |
| `$500` | `$482.132686` | `$-17.867314` | `6.41%` | `False` | Comfortable validation tier | `PASS` |

### Risk Of Ruin Estimate

This is a deterministic historical replay, not a Monte Carlo risk model.

| Starting Bankroll | Replay Ruin | Qualitative Risk |
|---:|---|---|
| `$20` | `True` | High |
| `$50` | `False` | High / unstable |
| `$100` | `False` | Moderate |
| `$250` | `False` | Low to moderate |
| `$500` | `False` | Low under observed replay |

The replay does not include slippage, partial fills, outages, latency, live reconciliation failures, or adverse fill quality. Those omissions mean the real survivability requirement may be higher.

## Section 6 - Option D Impact

5-share Option D event subset from `EXECUTION_REALITY_OPTION_D_AUDIT_001`:

| Metric | Value |
|---|---:|
| stop events analyzed | `12` |
| saved-loss count | `7` |
| destroyed-profit count | `5` |
| saved losses | `$12.400000` |
| destroyed profits | `$13.200000` |
| net value added vs hold counterfactual | `$-0.800000` |
| actual stop PnL | `$-6.500000` |
| hold-to-expiry counterfactual PnL | `$-5.700000` |
| drawdown reduction | `$1.300000` |
| whipsaw rate | `41.67%` |

Interpretation:

- Option D may reduce some drawdown pressure, but it does not improve net survivability under the documented 5-share stop subset.
- The observed saved-loss count is favorable, but destroyed-profit magnitude offsets the savings.
- Option D should remain a shadow comparison in the first Execution Paper Runtime phase.
- It should not be reused as an authoritative execution-mode stop rule until fixed-size execution evidence proves net benefit.

Conclusion:

```text
Option D does not currently improve 5_share bankroll survivability enough to lower the bankroll requirement.
```

## Section 7 - Promotion Threshold

### Minimum Viable Bankroll

```text
$100
```

Reason:

`$100` survives the canonical 5-share replay without observed ruin, but drawdown reaches `29.34%`. It is viable only as a cautionary research tier, not a comfortable validation base.

### Recommended Bankroll

```text
$250
```

Reason:

`$250` reduces observed max drawdown to `12.53%`, which is a more practical base for execution-paper validation and leaves room for slippage and missing execution realism.

### Comfortable Bankroll

```text
$500
```

Reason:

`$500` reduces observed max drawdown to `6.41%` under the historical replay. It is the cleanest validation tier if the objective is to study execution behavior without bankroll stress dominating the experiment.

## Final Verdict

Minimum viable bankroll:

```text
$100
```

Recommended bankroll:

```text
$250
```

Comfortable bankroll:

```text
$500
```

Risk of ruin estimate:

```text
$20 = observed ruin / FAIL
$50 = high stress / FAIL
$100 = survives with material drawdown / CAUTION
$250 = practical survivability / PASS
$500 = comfortable survivability / PASS
```

Overall classification:

```text
CAUTION
```

Reason:

A `5_share` Execution Paper Runtime is survivable only above the current `$20` signal bankroll. The historical replay is negative, Option D does not yet improve net 5-share survivability, and execution-mode validation should not begin below `$100`. The recommended starting bankroll for credible execution-paper validation is `$250`, with `$500` preferred if the operator wants drawdown pressure to stay secondary to execution-quality measurement.

