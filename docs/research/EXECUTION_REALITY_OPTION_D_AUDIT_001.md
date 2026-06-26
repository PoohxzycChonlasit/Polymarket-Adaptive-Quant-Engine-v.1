# EXECUTION_REALITY_OPTION_D_AUDIT_001

Date: 2026-06-20

Mode: READ ONLY AUDIT ONLY

Runtime behavior changed: No
Config changed: No
Strategy/risk/execution changed: No
Sizer changed: No
Runtime restarted: No
Commits: No

## Source

- `OPTION_D_COUNTERFACTUAL_AUDIT_001.md`
- `OPTION_D_STOP_DISTRIBUTION_AUDIT_001.md`

This audit scales the documented 12 Option D stop events from dust size to fixed share sizes using entry price, stop price, and the existing audit column `Price 5m Later/expiry` as the held-to-expiry counterfactual. This remains a counterfactual estimate, not live execution proof.

## Option D Scaled Results

| Target Size | Stops | Saved Loss Count | Destroyed Profit Count | Saved Losses | Destroyed Profits | Net Value Added | Actual Stop PnL | Hold-To-Expiry PnL | Drawdown Reduction | Whipsaw Rate |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `1` share | `12` | `7` | `5` | `$2.480000` | `$2.640000` | `$-0.160000` | `$-1.300000` | `$-1.140000` | `$0.260000` | `41.67%` |
| `2` share | `12` | `7` | `5` | `$4.960000` | `$5.280000` | `$-0.320000` | `$-2.600000` | `$-2.280000` | `$0.520000` | `41.67%` |
| `5` share | `12` | `7` | `5` | `$12.400000` | `$13.200000` | `$-0.800000` | `$-6.500000` | `$-5.700000` | `$1.300000` | `41.67%` |
| `10` share | `12` | `7` | `5` | `$24.800000` | `$26.400000` | `$-1.600000` | `$-13.000000` | `$-11.400000` | `$2.600000` | `41.67%` |

## Interpretation

- Option D remains net protective in the documented stop-event subset at all fixed sizes because the original saved-loss / destroyed-profit split scales linearly with shares.
- Whipsaw sensitivity remains material: `5 / 12` stops destroyed later profits.
- At larger sizes, both saved losses and destroyed profits become operationally significant rather than cosmetic.
- Option D should not be treated as a universal execution-mode solution; the previous distribution audit found edge concentration by entry price and side.

## Verdict

`OPTION_D_PROTECTIVE_BUT_SIZE_SENSITIVE`
