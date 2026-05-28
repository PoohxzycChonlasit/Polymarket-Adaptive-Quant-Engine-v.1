# Dynamic Executable Threshold + Expectancy Audit

Date: 2026-05-24

Scope: read-only research audit of the latest five complete paper-trade dates.

Runtime behavior changed: No  
Live behavior changed: No

## Role Routing

Primary role: `08_RESEARCH_QUANT_AGENT.md`

Supporting roles:

- `21_EXECUTION_MICROSTRUCTURE_AGENT.md`
- `10_BACKTEST_REPLAY_AGENT.md`
- `16_PAPER_EVALUATION_AGENT.md`

Why selected:

This audit separates signal evidence from executable evidence, then checks whether any price, session, lifecycle, or asset bucket survives dynamic minimum-order-size assumptions.

Files inspected:

- `CODEX_START_HERE.md`
- `PROJECT_RULES.md`
- `AGENTS.md`
- `MASTER_AGENT_ROUTER.md`
- `CURRENT_PROJECT_STATUS.md`
- `FILE_INDEX.md`
- `runtime/research_state/latest_research_state.md`
- `docs/research/executable_truth/minimum_executable_reality_audit.md`
- `docs/research/executable_truth/executable_reality_overlay_design.md`
- `docs/research/executable_truth/executable_reality_monitor.md`
- `docs/research/session_edge/session_pressure_comparison_audit.md`
- `runtime/quant_data/trade_journal/2026-05-19.jsonl`
- `runtime/quant_data/trade_journal/2026-05-20.jsonl`
- `runtime/quant_data/trade_journal/2026-05-21.jsonl`
- `runtime/quant_data/trade_journal/2026-05-22.jsonl`
- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-19.jsonl`
- `runtime/quant_data/execution_log/2026-05-20.jsonl`
- `runtime/quant_data/execution_log/2026-05-21.jsonl`
- `runtime/quant_data/execution_log/2026-05-22.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`

Files intentionally ignored:

- runtime code
- strategy modules
- risk manager
- position sizing
- stop-loss code
- wallet/live config
- replay execution

## Method

Evidence window:

```text
2026-05-19 through 2026-05-23
```

The audit used matched paper trades from `trade_close` rows and joined them to `trade_open` / entry execution fields by:

```text
(run_id, paper_trade_replay_key)
```

Rows without `trade_result` were classified by close reason or PnL sign. PnL in this report is signal-mode simulated paper PnL unless explicitly stated otherwise.

Dynamic executable overlay:

```text
mos=1 share
mos=3 shares
mos=5 shares
cost = entry_price * mos
eligible = paper_filled_shares >= mos
```

Important: the local evidence still does not expose authoritative Polymarket market metadata for `min_order_size`, `minimum_order_size`, or `mos`. The dynamic MOS levels are research scenarios, not live exchange truth.

## Executive Verdict

The signal ledger is barely positive across the five-day window, but no executable edge exists under `mos=1`, `mos=3`, or `mos=5`.

| Ledger | Result |
|---|---|
| Signal edge | weak positive, `+$0.021545` across `178` matched paper trades |
| Tradable edge, `mos=1` | none, `0/178` eligible |
| Executable edge, `mos=3` | none, `0/178` eligible |
| Executable edge, `mos=5` | none, `0/178` eligible |
| Live readiness | not established |
| Profitability claim | not allowed |

Answers:

1. Is signal edge positive?

Yes, but only weakly in the paper signal ledger:

```text
178 trades
74 TP / 104 SL
signal PnL = +$0.021545
expectancy = +$0.000121/trade
profit factor = 1.027
```

This is too small and too dust-dominated to claim profitability.

2. Is executable edge positive?

No executable edge is measurable. Every matched trade remains below `mos=1`, `mos=3`, and `mos=5`.

3. Which price buckets survive best?

Only the `0.30-0.50` and `0.50-0.70` buckets appear in matched evidence. Both are mildly positive in the signal ledger, but both have `100%` dust ratio under all MOS scenarios.

4. Where does expectancy actually exist?

Expectancy exists only in signal-mode paper evidence, especially:

- `16h + 0.50-0.70`
- `09h10h + 0.50-0.70`
- non-special sessions in `0.30-0.50`

It does not exist in executable evidence because executable trade count is zero.

## SIGNAL EDGE

Overall five-day signal ledger:

| Metric | Value |
|---|---:|
| Matched trades | `178` |
| TP | `74` |
| SL | `104` |
| TP rate | `41.6%` |
| Signal PnL | `+$0.021545` |
| Expectancy | `+$0.000121/trade` |
| Profit factor | `1.027` |
| Mean TP | `+$0.010978` |
| Mean SL | `-$0.007604` |
| RR | `1.444` |
| Median TP | `+$0.008766` |
| Median SL | `-$0.006066` |
| Average hold | `19.65s` |
| Median hold | `14.5s` |

Daily signal trend:

| Date | Trades | TP | SL | Signal PnL |
|---|---:|---:|---:|---:|
| 2026-05-19 | `33` | `19` | `14` | `+$0.106736` |
| 2026-05-20 | `24` | `12` | `12` | `+$0.045388` |
| 2026-05-21 | `29` | `10` | `19` | `+$0.017684` |
| 2026-05-22 | `55` | `22` | `33` | `-$0.031036` |
| 2026-05-23 | `37` | `11` | `26` | `-$0.117227` |

Interpretation:

The signal ledger is positive only because earlier positive days offset the latest two adverse days. Edge is weakening, not confirmed.

## TRADABLE EDGE

`mos=1` is the least strict scenario and should be treated as the minimum "tradable" overlay. Even under this loose standard:

| MOS scenario | Eligible trades | Survival rate | Dust ratio | Executable PnL |
|---:|---:|---:|---:|---:|
| `1` share | `0/178` | `0.0%` | `100.0%` | `N/A` |
| `3` shares | `0/178` | `0.0%` | `100.0%` | `N/A` |
| `5` shares | `0/178` | `0.0%` | `100.0%` | `N/A` |

Observed paper shares:

| Metric | Value |
|---|---:|
| Min shares | `0.022311` |
| Mean shares | `0.100331` |
| Median shares | `0.096627` |
| Max shares | `0.235702` |

Interpretation:

The current system remains `SIGNAL_MODE`. It does not yet produce even 1-share tradable evidence.

## EXECUTABLE EDGE

No executable-edge ledger exists in this five-day sample.

| Field | Result |
|---|---|
| Executable trade count, `mos=1` | `0` |
| Executable trade count, `mos=3` | `0` |
| Executable trade count, `mos=5` | `0` |
| Executable PnL | `N/A` |
| Dust PnL | `+$0.021545` |
| Executable conclusion | `NO_EXECUTABLE_EDGE_ESTABLISHED` |

This does not mean the signal cannot become executable later. It means the current paper evidence cannot prove executable expectancy.

## PRICE BUCKET ANALYSIS

Entry price distribution:

| Price Bucket | Trades | TP | SL | TP Rate | Signal PnL | Avg Hold | Median Hold | Expectancy | Profit Factor | Mean TP | Mean SL | RR | Median TP | Median SL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `0.10-0.30` | `0` | `0` | `0` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` |
| `0.30-0.50` | `31` | `12` | `19` | `38.7%` | `+$0.007524` | `14.71s` | `8.0s` | `+$0.000243` | `1.055` | `+$0.012042` | `-$0.007210` | `1.670` | `+$0.009741` | `-$0.006952` |
| `0.50-0.70` | `147` | `62` | `85` | `42.2%` | `+$0.014021` | `20.69s` | `17.0s` | `+$0.000095` | `1.021` | `+$0.010772` | `-$0.007693` | `1.400` | `+$0.008354` | `-$0.006051` |
| `0.70+` | `0` | `0` | `0` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` |

Entry price range:

```text
min = 0.32
mean = 0.5269
median = 0.53
max = 0.64
```

Important correction:

The recent matched paper evidence did not trade only `0.40`, `0.50`, or `0.60`, but it also did not cover all possible Polymarket price regimes. The actual matched range was `0.32-0.64`, concentrated in `0.50-0.70`.

Dynamic executable cost by price bucket:

| Price Bucket | Trades | Entry Range | Mean Paper Notional | Mean Cost @ MOS 1 | Mean Cost @ MOS 3 | Mean Cost @ MOS 5 | MOS Eligibility |
|---|---:|---|---:|---:|---:|---:|---|
| `0.10-0.30` | `0` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | no evidence |
| `0.30-0.50` | `31` | `0.32-0.49` | `$0.056481` | `$0.455161` | `$1.365484` | `$2.275806` | `0/31` at all MOS levels |
| `0.50-0.70` | `147` | `0.50-0.64` | `$0.051400` | `$0.541973` | `$1.625918` | `$2.709864` | `0/147` at all MOS levels |
| `0.70+` | `0` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | no evidence |

Fast SL by price bucket:

| Price Bucket | SL | SL <=15s | SL <=30s |
|---|---:|---:|---:|
| `0.30-0.50` | `19` | `15` | `17` |
| `0.50-0.70` | `85` | `51` | `76` |

Interpretation:

The `0.30-0.50` bucket has slightly better expectancy and RR, but lower win rate and tiny sample. The `0.50-0.70` bucket carries most of the evidence and is mildly positive only in signal mode.

## SESSION ANALYSIS

| Session | Trades | TP | SL | TP Rate | Signal PnL | Expectancy | Profit Factor | Mean TP | Mean SL | RR | Median Hold | Mean Quote Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `01h` | `2` | `1` | `1` | `50.0%` | `+$0.002250` | `+$0.001125` | `1.574` | `+$0.006170` | `-$0.003920` | `1.574` | `20.0s` | `29010ms` |
| `02h` | `15` | `1` | `14` | `6.7%` | `-$0.100156` | `-$0.006677` | `0.052` | `+$0.005468` | `-$0.007545` | `0.725` | `7.0s` | `22983ms` |
| `09h10h` | `29` | `16` | `13` | `55.2%` | `+$0.072870` | `+$0.002513` | `1.808` | `+$0.010188` | `-$0.006934` | `1.469` | `12.0s` | `10003ms` |
| `16h` | `13` | `7` | `6` | `53.8%` | `+$0.023332` | `+$0.001795` | `1.423` | `+$0.011216` | `-$0.009197` | `1.220` | `20.0s` | `15718ms` |
| `other` | `119` | `49` | `70` | `41.2%` | `+$0.023249` | `+$0.000195` | `1.043` | `+$0.011413` | `-$0.007657` | `1.491` | `16.0s` | `14600ms` |

Fast SL by session:

| Session | SL | SL <=15s | SL <=30s |
|---|---:|---:|---:|
| `01h` | `1` | `0` | `1` |
| `02h` | `14` | `10` | `13` |
| `09h10h` | `13` | `9` | `13` |
| `16h` | `6` | `4` | `5` |
| `other` | `70` | `43` | `61` |

Session interpretation:

- `02h` remains the clearest hostile signal bucket.
- `09h10h` remains the best session-edge candidate in signal mode.
- `16h` improves on the five-day view, but prior recurrence work still says it needs more stability.
- `01h` remains too thin.

All sessions remain `100%` dust under `mos=1`, `mos=3`, and `mos=5`.

## LIFECYCLE ANALYSIS

| Lifecycle | Trades | TP | SL | TP Rate | Signal PnL | Expectancy | Profit Factor | Mean TP | Mean SL | RR | Median Hold | Mean Quote Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `OPENING` | `145` | `67` | `78` | `46.2%` | `+$0.159725` | `+$0.001102` | `1.281` | `+$0.010868` | `-$0.007287` | `1.491` | `16.0s` | `20189ms` |
| `ACTIVE` | `33` | `7` | `26` | `21.2%` | `-$0.138181` | `-$0.004187` | `0.379` | `+$0.012035` | `-$0.008555` | `1.407` | `11.0s` | `10791ms` |

Fast SL by lifecycle:

| Lifecycle | SL | SL <=15s | SL <=30s |
|---|---:|---:|---:|
| `OPENING` | `78` | `48` | `70` |
| `ACTIVE` | `26` | `18` | `23` |

Lifecycle interpretation:

`OPENING` is the only positive lifecycle bucket in signal mode. `ACTIVE` is materially negative despite a larger average TP than average SL because the win rate is too low.

## ASSET ANALYSIS

| Asset | Trades | TP | SL | TP Rate | Signal PnL | Expectancy | Profit Factor | Mean TP | Mean SL | RR | Median Hold | Mean Quote Stale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `BTC` | `38` | `15` | `23` | `39.5%` | `+$0.039098` | `+$0.001029` | `1.237` | `+$0.013603` | `-$0.007171` | `1.897` | `9.0s` | `11746ms` |
| `ETH` | `140` | `59` | `81` | `42.1%` | `-$0.017554` | `-$0.000125` | `0.972` | `+$0.010311` | `-$0.007727` | `1.334` | `17.5s` | `17657ms` |

Fast SL by asset:

| Asset | SL | SL <=15s | SL <=30s |
|---|---:|---:|---:|
| `BTC` | `23` | `19` | `21` |
| `ETH` | `81` | `47` | `72` |

Asset interpretation:

BTC has better RR and positive signal PnL, but fewer trades. ETH carries most of the sample and is slightly negative.

## BEST SURVIVAL MATRIX

Best price + session combinations by signal expectancy, requiring at least three trades:

| Rank | Session + Price Bucket | Trades | TP | SL | TP Rate | Signal PnL | Expectancy | Profit Factor | Median Hold | Dust @ MOS 5 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `16h + 0.50-0.70` | `11` | `7` | `4` | `63.6%` | `+$0.043901` | `+$0.003991` | `2.268` | `20.0s` | `100%` |
| 2 | `09h10h + 0.50-0.70` | `27` | `15` | `12` | `55.6%` | `+$0.069378` | `+$0.002570` | `1.812` | `18.0s` | `100%` |
| 3 | `other + 0.30-0.50` | `25` | `10` | `15` | `40.0%` | `+$0.024989` | `+$0.001000` | `1.236` | `11.0s` | `100%` |

Interpretation:

These are best signal-survival combinations, not executable-survival combinations. Each remains `100%` dust under the practical overlay.

## WORST SURVIVAL MATRIX

Worst price + session combinations by signal expectancy, requiring at least three trades:

| Rank | Session + Price Bucket | Trades | TP | SL | TP Rate | Signal PnL | Expectancy | Profit Factor | Median Hold | Dust @ MOS 5 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | `02h + 0.50-0.70` | `13` | `0` | `13` | `0.0%` | `-$0.099767` | `-$0.007674` | `0.000` | `7.0s` | `100%` |
| 2 | `other + 0.50-0.70` | `94` | `39` | `55` | `41.5%` | `-$0.001740` | `-$0.000019` | `0.996` | `17.5s` | `100%` |

Interpretation:

The 02h failure is concentrated in the same dominant price region as the best 09h10h/16h candidates. Price alone does not explain survival. Session and lifecycle context matter.

## Price + Session Matrix

| Session | Price Bucket | Trades | TP | SL | TP Rate | Signal PnL | Expectancy | Read |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `02h` | `0.30-0.50` | `2` | `1` | `1` | `50.0%` | `-$0.000388` | `-$0.000194` | too thin |
| `02h` | `0.50-0.70` | `13` | `0` | `13` | `0.0%` | `-$0.099767` | `-$0.007674` | worst combination |
| `09h10h` | `0.30-0.50` | `2` | `1` | `1` | `50.0%` | `+$0.003492` | `+$0.001746` | too thin |
| `09h10h` | `0.50-0.70` | `27` | `15` | `12` | `55.6%` | `+$0.069378` | `+$0.002570` | strongest repeat candidate |
| `16h` | `0.30-0.50` | `2` | `0` | `2` | `0.0%` | `-$0.020569` | `-$0.010284` | too thin but adverse |
| `16h` | `0.50-0.70` | `11` | `7` | `4` | `63.6%` | `+$0.043901` | `+$0.003991` | best signal expectancy |
| `01h` | `0.50-0.70` | `2` | `1` | `1` | `50.0%` | `+$0.002250` | `+$0.001125` | too thin |
| `other` | `0.30-0.50` | `25` | `10` | `15` | `40.0%` | `+$0.024989` | `+$0.001000` | positive through RR, not winrate |
| `other` | `0.50-0.70` | `94` | `39` | `55` | `41.5%` | `-$0.001740` | `-$0.000019` | near-flat negative |

No matched rows appeared in `0.10-0.30` or `0.70+`.

## TOP HYPOTHESES

1. `OPENING` still carries the only broad signal edge.

Evidence:

- `OPENING`: `67 TP / 78 SL`, `+$0.159725`, profit factor `1.281`.
- `ACTIVE`: `7 TP / 26 SL`, `-$0.138181`, profit factor `0.379`.

Research implication:

Keep separating lifecycle in all future signal and executable overlays. Do not combine ACTIVE losses into the same expectancy estimate as OPENING unless the goal is all-runtime baseline.

2. Session dominates price bucket.

Evidence:

- `09h10h + 0.50-0.70`: `15 TP / 12 SL`, `+$0.069378`.
- `16h + 0.50-0.70`: `7 TP / 4 SL`, `+$0.043901`.
- `02h + 0.50-0.70`: `0 TP / 13 SL`, `-$0.099767`.

Research implication:

The same price region can be best or worst depending on session. Price-only thresholds would likely overfit or discard useful context.

3. Executable reality remains the dominant blocker.

Evidence:

- Max observed paper size was `0.235702` shares.
- `mos=1`, `mos=3`, and `mos=5` all have `0/178` eligible trades.
- All positive signal buckets have `100%` dust ratio.

Research implication:

Any future paper/replay dashboard must keep `signal_pnl` separate from `executable_pnl`. Current dust PnL should not be trusted as live or practical PnL.

## Three Future Options

OPTION 1 - SAFE EV PRESERVATION:

Keep all current runtime behavior unchanged. Continue collecting signal evidence while labeling every matched row with executable overlay fields offline.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:

Build an offline-only replay report that recomputes these MOS ledgers daily for `mos=1`, `mos=3`, `mos=5`, and authoritative market metadata if it becomes available.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:

Investigate why actual paper size remains below even one share and map the interaction between bankroll tier, micro survival, risk mode, confidence, and final size. This should remain research/design until explicitly scoped as implementation.

Recommended next action:

OPTION 2. The most useful next step is an offline recurring executable-expectancy report, because it preserves runtime safety while making signal-vs-executable drift visible.

## Final Conclusion

```text
SIGNAL_EDGE: WEAK_POSITIVE
TRADABLE_EDGE_MOS1: NOT_ESTABLISHED
EXECUTABLE_EDGE_MOS3: NOT_ESTABLISHED
EXECUTABLE_EDGE_MOS5: NOT_ESTABLISHED
BEST_SIGNAL_BUCKETS: 16h + 0.50-0.70, 09h10h + 0.50-0.70
WORST_SIGNAL_BUCKET: 02h + 0.50-0.70
PRICE_BUCKETS_SURVIVING_BEST: 0.30-0.50 by RR, 0.50-0.70 by sample depth
EXECUTABLE_PNL: N/A
LIVE_READINESS: NO
```

This audit does not support changing sizing, stop-loss, strategy, risk, execution, runtime, or live mode. It supports only continued research separation between signal evidence and executable evidence.

Tests: not run; docs-only read-only audit.
