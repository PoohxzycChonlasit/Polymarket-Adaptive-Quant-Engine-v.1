# EXECUTION_REALITY_LIQUIDITY_AUDIT_001

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


## Fill Feasibility By Asset

Pass definition: entry top ask depth must satisfy target size. Round-trip pass additionally requires top bid depth to satisfy target size for a later exit. Spread pass uses `executable_spread_state == NORMALIZED`.

| Target Size | Asset | Trades | Entry Depth Pass | Entry Pass % | Round-Trip Depth Pass | Round-Trip Pass % | Liquidity Reject % | Spread Normalized % | Ask Missing | Bid Missing |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `1` share | `BTC` | `204` | `203` | `99.51%` | `202` | `99.02%` | `0.98%` | `100.00%` | `0` | `0` |
| `1` share | `ETH` | `504` | `499` | `99.01%` | `498` | `98.81%` | `1.19%` | `100.00%` | `0` | `0` |
| `2` share | `BTC` | `204` | `203` | `99.51%` | `201` | `98.53%` | `1.47%` | `100.00%` | `0` | `0` |
| `2` share | `ETH` | `504` | `496` | `98.41%` | `493` | `97.82%` | `2.18%` | `100.00%` | `0` | `0` |
| `5` share | `BTC` | `204` | `202` | `99.02%` | `198` | `97.06%` | `2.94%` | `100.00%` | `0` | `0` |
| `5` share | `ETH` | `504` | `478` | `94.84%` | `471` | `93.45%` | `6.55%` | `100.00%` | `0` | `0` |
| `10` share | `BTC` | `204` | `195` | `95.59%` | `188` | `92.16%` | `7.84%` | `100.00%` | `0` | `0` |
| `10` share | `ETH` | `504` | `436` | `86.51%` | `418` | `82.94%` | `17.06%` | `100.00%` | `0` | `0` |

## Depth Bottlenecks

- Historical admitted paper trades usually had enough top-of-book depth for `1`, `2`, `5`, and `10` share entry tests, but this is based on top-level size fields at trade open, not full-orderbook execution simulation.
- Round-trip feasibility is stricter because exits require bid depth. Top bid fields were available in trade-open payloads, but not guaranteed at actual exit time.
- Spread bottleneck evidence is limited to `executable_spread_state`; numeric spread is not consistently present in trade-open rows.

## Verdict

`LIQUIDITY_FEASIBILITY_PARTIAL`
