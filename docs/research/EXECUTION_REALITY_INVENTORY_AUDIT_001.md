# EXECUTION_REALITY_INVENTORY_AUDIT_001

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


## Inventory Utilization By Target Size

| Target Size | Median Entry Notional | Max Concurrent Positions | Max Concurrent Exposure | Avg Time-Weighted Exposure | Multi-Position Time | Max Exposure / $20 | Max Exposure / $100 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| `1` share | `$0.530000` | `2` | `$1.160000` | `$0.002533` | `0.01%` | `5.80%` | `1.16%` |
| `2` share | `$1.060000` | `2` | `$2.320000` | `$0.005065` | `0.01%` | `11.60%` | `2.32%` |
| `5` share | `$2.650000` | `2` | `$5.800000` | `$0.012663` | `0.01%` | `29.00%` | `5.80%` |
| `10` share | `$5.300000` | `2` | `$11.600000` | `$0.025325` | `0.01%` | `58.00%` | `11.60%` |

## Position Limit Interactions

- Historical sequence reached `2` concurrent positions. Target size changes notional exposure, not position count.
- If the current runtime position-count cap is tighter than this historical overlap, execution-mode replay must enforce that cap before claiming executable capacity.
- At `10` shares, max concurrent exposure becomes material for `$20` and `$50` bankrolls even before slippage or failed exits.

## Loss Cluster And Risk Mode Interactions

| Target Size | Worst Consecutive Loss Cluster | Cluster Length | Longest Loss Streak | Risk Mode Distribution |
|---:|---:|---:|---:|---|
| `1` share | `$-1.890490` | `18` | `18` | {'NORMAL': 258, 'UNKNOWN': 346, 'DEFENSIVE': 51, 'MICRO_RECOVERY': 53} |
| `2` share | `$-3.780979` | `18` | `18` | {'NORMAL': 258, 'UNKNOWN': 346, 'DEFENSIVE': 51, 'MICRO_RECOVERY': 53} |
| `5` share | `$-9.452449` | `18` | `18` | {'NORMAL': 258, 'UNKNOWN': 346, 'DEFENSIVE': 51, 'MICRO_RECOVERY': 53} |
| `10` share | `$-18.904897` | `18` | `18` | {'NORMAL': 258, 'UNKNOWN': 346, 'DEFENSIVE': 51, 'MICRO_RECOVERY': 53} |

## Risk Mode / Option D Interpretation

- Risk mode near opens: `{'NORMAL': 258, 'UNKNOWN': 346, 'DEFENSIVE': 51, 'MICRO_RECOVERY': 53}`.
- Bankroll tier near opens: `{'UNKNOWN': 669, 'T0_MICRO_SEED': 39}`.
- Scaling from dust to executable sizes linearly magnifies loss clusters and Option D stop outcomes.
- Option D becomes more important as size increases because stopped trades no longer represent cents of loss; however, whipsaw losses are also magnified.

## Verdict

`INVENTORY_GAP_MATERIAL`
