# CAPITAL_TRUTH_AUDIT_001

Date: 2026-06-20

Mode: READ ONLY AUDIT ONLY

Runtime behavior changed: No
Config changed: No
Strategy/risk/execution changed: No
Sizer changed: No
Runtime restarted: No
Commits: No

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
| stop-loss Option D rows parsed | `12` |


## Capital Replay Summary

| Mode | Bankroll | Total PnL | Final Equity | Max Drawdown | Max Drawdown % | Profit Factor | Longest Loss Streak | Recovery Duration Trades | Risk Of Ruin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `Dust Mode` | `$20` | `$-0.275395` | `$19.724605` | `$0.659168` | `3.25%` | `0.919` | `18` | `579` | `False` |
| `Dust Mode` | `$50` | `$-0.275395` | `$49.724605` | `$0.659168` | `1.31%` | `0.919` | `18` | `579` | `False` |
| `Dust Mode` | `$100` | `$-0.275395` | `$99.724605` | `$0.659168` | `0.66%` | `0.919` | `18` | `579` | `False` |
| `Dust Mode` | `$250` | `$-0.275395` | `$249.724605` | `$0.659168` | `0.26%` | `0.919` | `18` | `579` | `False` |
| `Dust Mode` | `$500` | `$-0.275395` | `$499.724605` | `$0.659168` | `0.13%` | `0.919` | `18` | `579` | `False` |
| `Dust Mode` | `$1000` | `$-0.275395` | `$999.724605` | `$0.659168` | `0.07%` | `0.919` | `18` | `579` | `False` |
| `1 Share` | `$20` | `$-3.573463` | `$16.426537` | `$6.557907` | `29.34%` | `0.897` | `18` | `579` | `False` |
| `1 Share` | `$50` | `$-3.573463` | `$46.426537` | `$6.557907` | `12.53%` | `0.897` | `18` | `579` | `False` |
| `1 Share` | `$100` | `$-3.573463` | `$96.426537` | `$6.557907` | `6.41%` | `0.897` | `18` | `579` | `False` |
| `1 Share` | `$250` | `$-3.573463` | `$246.426537` | `$6.557907` | `2.60%` | `0.897` | `18` | `579` | `False` |
| `1 Share` | `$500` | `$-3.573463` | `$496.426537` | `$6.557907` | `1.31%` | `0.897` | `18` | `579` | `False` |
| `1 Share` | `$1000` | `$-3.573463` | `$996.426537` | `$6.557907` | `0.65%` | `0.897` | `18` | `579` | `False` |
| `2 Share` | `$20` | `$-7.146926` | `$12.853074` | `$13.115814` | `53.08%` | `0.897` | `18` | `579` | `False` |
| `2 Share` | `$50` | `$-7.146926` | `$42.853074` | `$13.115814` | `23.97%` | `0.897` | `18` | `579` | `False` |
| `2 Share` | `$100` | `$-7.146926` | `$92.853074` | `$13.115814` | `12.53%` | `0.897` | `18` | `579` | `False` |
| `2 Share` | `$250` | `$-7.146926` | `$242.853074` | `$13.115814` | `5.15%` | `0.897` | `18` | `579` | `False` |
| `2 Share` | `$500` | `$-7.146926` | `$492.853074` | `$13.115814` | `2.60%` | `0.897` | `18` | `579` | `False` |
| `2 Share` | `$1000` | `$-7.146926` | `$992.853074` | `$13.115814` | `1.31%` | `0.897` | `18` | `579` | `False` |
| `5 Share` | `$20` | `$-17.867314` | `$2.132686` | `$32.789535` | `103.20%` | `0.897` | `18` | `579` | `True` |
| `5 Share` | `$50` | `$-17.867314` | `$32.132686` | `$32.789535` | `53.08%` | `0.897` | `18` | `579` | `False` |
| `5 Share` | `$100` | `$-17.867314` | `$82.132686` | `$32.789535` | `29.34%` | `0.897` | `18` | `579` | `False` |
| `5 Share` | `$250` | `$-17.867314` | `$232.132686` | `$32.789535` | `12.53%` | `0.897` | `18` | `579` | `False` |
| `5 Share` | `$500` | `$-17.867314` | `$482.132686` | `$32.789535` | `6.41%` | `0.897` | `18` | `579` | `False` |
| `5 Share` | `$1000` | `$-17.867314` | `$982.132686` | `$32.789535` | `3.24%` | `0.897` | `18` | `579` | `False` |
| `10 Share` | `$20` | `$-35.734628` | `$-15.734628` | `$65.579070` | `150.60%` | `0.897` | `18` | `579` | `True` |
| `10 Share` | `$50` | `$-35.734628` | `$14.265372` | `$65.579070` | `89.17%` | `0.897` | `18` | `579` | `False` |
| `10 Share` | `$100` | `$-35.734628` | `$64.265372` | `$65.579070` | `53.08%` | `0.897` | `18` | `579` | `False` |
| `10 Share` | `$250` | `$-35.734628` | `$214.265372` | `$65.579070` | `23.97%` | `0.897` | `18` | `579` | `False` |
| `10 Share` | `$500` | `$-35.734628` | `$464.265372` | `$65.579070` | `12.53%` | `0.897` | `18` | `579` | `False` |
| `10 Share` | `$1000` | `$-35.734628` | `$964.265372` | `$65.579070` | `6.41%` | `0.897` | `18` | `579` | `False` |

## Capital Interpretation

- The same historical sequence becomes materially different once shares are scaled from dust to `5` or `10` shares.
- Profit factor is size-invariant because the same realized path is scaled, but drawdown, loss clusters, and ruin pressure scale linearly.
- A `$20` bankroll is not a realistic base for `10`-share execution-mode behavior under the observed loss clusters.
- Bankroll assessment is still incomplete without slippage, partial fills, fees/costs if any, and live reconciliation proof.

## Verdict

`CAPITAL_REQUIREMENT_MATERIAL`
