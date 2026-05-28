# 09h Regime Exception Audit

Generated: 2026-05-23  
Scope: read-only comparison of 02h UTC worst hour versus 09h UTC best hour.  
Sources:

- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`
- `runtime/quant_data/decision_log/2026-05-23.jsonl`

No code, replay, runtime, policy, strategy, risk, execution, live, or S3 changes were made.

## Method

- Closed-trade outcomes use `trade_journal` `trade_close`.
- ENTRY lifecycle, elapsed, quote source, quote ages, `quote_stale_ms`, EV, confidence, and risk mode are joined from ENTRY `paper_fill` / `trade_open` by `paper_trade_replay_key`.
- Skip reasons use hourly `candidate_block_reason` from `decision_log`.
- Hours are UTC.

## Executive Summary

09h broke the simple Opening hypothesis because ACTIVE and >30s entries both won, and the effect was cross-asset.

The evidence does not support `EDGE_BREAK` yet. 09h is better classified as `REGIME_SPLIT`: a trend/continuation regime where ACTIVE entries remained profitable, unlike the 02h adverse-chop regime where both OPENING and ACTIVE failed.

Final classification: `REGIME_SPLIT`

## 02h vs 09h Summary

| Metric | 02h UTC - Worst | 09h UTC - Best |
|---|---:|---:|
| Closed trades | 8 | 4 |
| BTC | 1 | 2 |
| ETH | 7 | 2 |
| TP | 0 | 4 |
| SL | 8 | 0 |
| ACTIVE trades | 4 | 2 |
| ACTIVE TP rate | 0% | 100% |
| OPENING trades | 4 | 2 |
| OPENING TP rate | 0% | 100% |
| Mean elapsed | 30.75s | 44.00s |
| Elapsed range | 7s-49s | 20s-74s |
| Mean `quote_stale_ms` | 23146.514 | 9974.105 |
| Quote stale range | 10016.489-59356.153 | 7280.510-11365.973 |
| Mean EV | 0.134098 | 0.107765 |
| Mean confidence | 0.595918 | 0.608890 |
| Mean entry price | 0.523750 | 0.555000 |
| Mean exit price | 0.435000 | 0.715000 |
| Mean PnL | -0.008145 USDC | +0.013548 USDC |
| Dominant skip reason | `delta_extreme` | `delta_extreme` |
| market_analysis_exception | 0 | 0 |

## Quote Source And Staleness

| Hour | Quote Sources | Interpretation |
|---:|---|---|
| 02h | `decision_cycle_fetch`: 5, `display_snapshot_sampling`: 3 | Mixed quote lineage; two oldest OPENING ETH losses used 59.356s stale quotes. |
| 09h | `decision_cycle_fetch`: 4 | Uniform quote source; all winners had lower and tighter staleness around 7.281s-11.366s. |

Staleness did not single-handedly explain the regime split, but 09h had materially cleaner quote freshness than 02h.

## Trade-Level Comparison

### 02h UTC

| Time | Asset | Side | Result | Lifecycle | Elapsed | quote_stale_ms | EV | Confidence | Entry | Exit | PnL |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 02:10:11 | ETH | NO | SL | OPENING_SCAN | 7s | 59356.153 | 0.144311 | 0.541526 | 0.51 | 0.46 | -0.004927 |
| 02:10:15 | ETH | NO | SL | OPENING_SCAN | 7s | 59356.153 | 0.144311 | 0.541526 | 0.50 | 0.46 | -0.004020 |
| 02:10:52 | ETH | YES | SL | ACTIVE_INVENTORY_TRADING | 47s | 10255.262 | 0.088397 | 0.566816 | 0.58 | 0.42 | -0.015325 |
| 02:20:54 | ETH | YES | SL | ACTIVE_INVENTORY_TRADING | 49s | 10016.489 | 0.136766 | 0.554604 | 0.53 | 0.43 | -0.009473 |
| 02:20:55 | ETH | YES | SL | ACTIVE_INVENTORY_TRADING | 49s | 10016.489 | 0.136766 | 0.554604 | 0.52 | 0.41 | -0.010628 |
| 02:20:59 | ETH | YES | SL | ACTIVE_INVENTORY_TRADING | 49s | 10016.489 | 0.136766 | 0.554604 | 0.54 | 0.41 | -0.012094 |
| 02:30:35 | BTC | YES | SL | OPENING_SCAN | 30s | 10173.355 | 0.140997 | 0.731396 | 0.51 | 0.45 | -0.005679 |
| 02:40:16 | ETH | NO | SL | OPENING_SCAN | 8s | 15981.722 | 0.144475 | 0.722265 | 0.50 | 0.44 | -0.003011 |

02h signature: high apparent EV did not translate into fills that moved favorably. ETH dominated, both YES and NO sides lost, and ACTIVE YES entries repriced sharply against the position.

### 09h UTC

| Time | Asset | Side | Result | Lifecycle | Elapsed | quote_stale_ms | EV | Confidence | Entry | Exit | PnL |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 09:10:41 | BTC | YES | TP | OPENING_SCAN | 30s | 10548.364 | 0.036999 | 0.767799 | 0.64 | 0.73 | +0.002008 |
| 09:17:06 | ETH | YES | TP | ACTIVE_INVENTORY_TRADING | 52s | 10701.571 | 0.129286 | 0.557250 | 0.53 | 0.87 | +0.032193 |
| 09:20:31 | ETH | NO | TP | OPENING_SCAN | 20s | 7280.510 | 0.138976 | 0.546425 | 0.51 | 0.59 | +0.007885 |
| 09:22:03 | BTC | YES | TP | ACTIVE_INVENTORY_TRADING | 74s | 11365.973 | 0.125798 | 0.564088 | 0.54 | 0.67 | +0.012105 |

09h signature: both BTC and ETH produced favorable repricing, both OPENING and ACTIVE worked, and >30s timing did not fail.

## Skip Reason Comparison

Top hourly skip reasons from `decision_log`:

| Rank | 02h Skip Reason | Count | 09h Skip Reason | Count |
|---:|---|---:|---|---:|
| 1 | `delta_extreme` | 718 | `delta_extreme` | 1064 |
| 2 | `confidence_too_low` | 341 | `confidence_too_low` | 546 |
| 3 | `time_unsafe` | 179 | `time_unsafe` | 236 |
| 4 | `frequency_cooldown` | 123 | `frequency_cooldown` | 70 |
| 5 | `risk_plan_zero` | 19 | `max_trades_per_hour_reached` | 34 |
| 6 | `empty_book` | 18 | `empty_book` | 24 |
| 7 | `ev_below_threshold` | 7 | `ev_below_threshold` | 14 |

Skip reasons did not materially change in kind. The dominant no-trade context was still `delta_extreme`, which means the key difference was not a cleaner admission environment. The key difference was that the admitted trades in 09h entered a favorable continuation regime instead of adverse chop.

## What Changed At 09h?

1. Outcome polarity flipped.
   - 02h: 0 TP / 8 SL.
   - 09h: 4 TP / 0 SL.

2. ACTIVE stopped being toxic.
   - 02h ACTIVE TP rate: 0%.
   - 09h ACTIVE TP rate: 100%.

3. OPENING also recovered.
   - 02h OPENING TP rate: 0%.
   - 09h OPENING TP rate: 100%.

4. Quote staleness improved.
   - 02h mean `quote_stale_ms`: 23.147s.
   - 09h mean `quote_stale_ms`: 9.974s.
   - 02h contained two 59.356s stale OPENING ETH losses.

5. Quote lineage became uniform.
   - 02h mixed `decision_cycle_fetch` and `display_snapshot_sampling`.
   - 09h all trades used `decision_cycle_fetch`.

6. Favorable price movement dominated.
   - 02h mean entry to exit: 0.524 -> 0.435.
   - 09h mean entry to exit: 0.555 -> 0.715.

7. EV was not the explanation by itself.
   - 02h mean EV was higher than 09h, but all trades lost.
   - 09h lower mean EV still won, implying regime/microstructure/timing mattered more than raw EV score.

## Why Did ACTIVE Work Only There?

The ACTIVE winners in 09h look like continuation trades, not late-chase noise:

- ETH YES at 52s moved from 0.53 to 0.87.
- BTC YES at 74s moved from 0.54 to 0.67.
- Both had quote staleness near 10s-11s, not extreme stale quotes.
- Both occurred in the same hour as successful OPENING trades.

In 02h, ACTIVE entries clustered on ETH YES and all repriced downward:

- 0.58 -> 0.42
- 0.53 -> 0.43
- 0.52 -> 0.41
- 0.54 -> 0.41

Interpretation: ACTIVE did not become universally good. It worked when the hour supported directional continuation and failed when the hour was adverse/choppy.

## Market Regime Classification

| Hour | Regime | Evidence |
|---:|---|---|
| 02h | Mean reversion / adverse chop | Both YES and NO lost; OPENING and ACTIVE both 0% TP; repeated ETH adverse repricing. |
| 09h | Trend / continuation plus opening dislocation | Both BTC and ETH won; OPENING and ACTIVE both 100% TP; >30s entries won; exits repriced favorably. |

09h is not simply an opening dislocation. It contains opening dislocation plus continuation. That continuation is what broke the Opening-only hypothesis.

## Temporary Anomaly Or New Regime?

Classification: `REGIME_SPLIT`

Rationale:

- Not `ANOMALY`: 09h had four wins across BTC and ETH, OPENING and ACTIVE, <=30s and >30s. That is more structured than a single lucky print.
- Not `EDGE_BREAK`: the evidence remains one-hour concentrated, and OPENING still worked in 09h. There is not enough sample to abandon the Opening edge.
- `REGIME_SPLIT`: 02h and 09h behave like different market regimes. The opening hypothesis is conditional, not universal.

## Final Answers

1. What changed at 09h?
   - The admitted trades entered a favorable trend/continuation regime with lower/tighter quote staleness and uniform quote source.

2. Why ACTIVE works only there?
   - ACTIVE worked because price continued after the opening window instead of mean-reverting or chopping against entries.

3. Market regime?
   - 02h: mean reversion / adverse chop.
   - 09h: trend / continuation plus opening dislocation.

4. Temporary anomaly or new regime?
   - `REGIME_SPLIT`. It is a regime exception, not yet a durable new rule.

Runtime behavior changed: No  
Live behavior changed: No  
Tests: not run, docs-only  
Persistent tests unchanged
