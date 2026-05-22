# Staleness Contradiction Audit v1

Date: 2026-05-22

Scope: Read-only Phase 5 staleness contradiction audit.

Runtime behavior changed: No.

Live behavior changed: No.

Paper launch: No.

Replay run: No.

Tests: none.

---

## Question

Expected relationship:

```text
older quote -> worse outcome
```

Observed contradiction from the Phase 5 monitor:

```text
60s+ entry quote bucket mean pnl_usdc = +0.012388
```

Goal: determine whether the relationship is inverted, noisy, a small sample artifact, or an execution alpha candidate.

---

## Evidence Scope

Targeted read-only sources:

- `runtime/quant_data/execution_log/2026-05-22.jsonl`
- `runtime/quant_data/trade_journal/2026-05-22.jsonl`
- `docs/research/sessions/2026-05-22/phase5_evidence_monitor.md`
- `docs/research/sessions/2026-05-22/outcome_truth_monitor_update.md`

No code, paper launch, replay, runtime command, or JSONL rewrite was performed.

---

## Instrumentation-Era Clean Runs

| Run ID | Phase 5 fills | Outcome-truth closes | Assets | mex | Included for outcome audit |
|---|---:|---:|---|---:|---|
| `20260522T082440Z_32952_1b709e78` | 6 | 0 | ETH | 0 | No, quote-age only, pre-outcome-truth |
| `20260522T094222Z_46088_040fac20` | 10 | 5 | ETH | 0 | Yes |
| `20260522T130017Z_21712_035b3af7` | 6 | 3 | ETH | 0 | Yes |

The contradiction audit uses the two clean outcome-truth runs for `trade_result` and `pnl_usdc`. The earlier clean Phase 5 run is retained as instrumentation context only because `trade_result` and `pnl_usdc` are absent.

---

## Confirmed Trade Matrix

| Run ID | Asset | Side | Result | `pnl_usdc` | Entry quote age | Entry bucket | Exit quote age | Exit bucket | Entry lifecycle | Exit lifecycle |
|---|---|---|---|---:|---:|---|---:|---|---|---|
| `20260522T094222Z_46088_040fac20` | ETH | YES | SL | -0.016166 | 10.394s | 5-15s | 5.129s | 5-15s | OPENING_SCAN | OPENING_SCAN |
| `20260522T094222Z_46088_040fac20` | ETH | YES | TP | +0.005477 | 5.893s | 5-15s | 16.262s | 15-30s | OPENING_SCAN | ACTIVE_INVENTORY_TRADING |
| `20260522T094222Z_46088_040fac20` | ETH | NO | SL | -0.004185 | 10.716s | 5-15s | 4.863s | 0-5s | ACTIVE_INVENTORY_TRADING | ACTIVE_INVENTORY_TRADING |
| `20260522T094222Z_46088_040fac20` | ETH | NO | TP | +0.005477 | 44.956s | 30-60s | 16.463s | 15-30s | OPENING_SCAN | ACTIVE_INVENTORY_TRADING |
| `20260522T094222Z_46088_040fac20` | ETH | YES | SL | -0.010546 | 10.091s | 5-15s | 11.501s | 5-15s | OPENING_SCAN | OPENING_SCAN |
| `20260522T130017Z_21712_035b3af7` | ETH | NO | TP | +0.012388 | 65.794s | 60s+ | 17.775s | 15-30s | OPENING_SCAN | OPENING_SCAN |
| `20260522T130017Z_21712_035b3af7` | ETH | NO | SL | -0.016395 | 45.841s | 30-60s | 4.709s | 0-5s | OPENING_SCAN | OPENING_SCAN |
| `20260522T130017Z_21712_035b3af7` | ETH | NO | SL | -0.005024 | 9.923s | 5-15s | 6.650s | 5-15s | ACTIVE_INVENTORY_TRADING | ACTIVE_INVENTORY_TRADING |

---

## Entry Quote-Age Buckets

| Entry bucket | Trades | TP | SL | Mean `pnl_usdc` | Median `pnl_usdc` | Quote source | Lifecycle mix |
|---|---:|---:|---:|---:|---:|---|---|
| 0-5s | 0 | 0 | 0 | n/a | n/a | n/a | n/a |
| 5-15s | 5 | 1 | 4 | -0.006089 | -0.005024 | `decision_cycle_fetch` 5/5 | OPENING_SCAN 3, ACTIVE_INVENTORY_TRADING 2 |
| 15-30s | 0 | 0 | 0 | n/a | n/a | n/a | n/a |
| 30-60s | 2 | 1 | 1 | -0.005459 | -0.005459 | `display_snapshot_sampling` 2/2 | OPENING_SCAN 2 |
| 60s+ | 1 | 1 | 0 | +0.012388 | +0.012388 | `display_snapshot_sampling` 1/1 | OPENING_SCAN 1 |

---

## Exit Quote-Age Buckets

| Exit bucket | Trades | TP | SL | Mean `pnl_usdc` | Median `pnl_usdc` | Quote source |
|---|---:|---:|---:|---:|---:|---|
| 0-5s | 2 | 0 | 2 | -0.010290 | -0.010290 | `decision_cycle_fetch` 2/2 |
| 5-15s | 3 | 0 | 3 | -0.010579 | -0.010546 | `decision_cycle_fetch` 3/3 |
| 15-30s | 3 | 3 | 0 | +0.007781 | +0.005477 | `display_snapshot_sampling` 3/3 |
| 30-60s | 0 | 0 | 0 | n/a | n/a | n/a |
| 60s+ | 0 | 0 | 0 | n/a | n/a | n/a |

Exit quote-age pattern is opposite the stale-entry hypothesis: all TP exits are in 15-30s and all SL exits are below 15s. This likely reflects exit trigger timing and quote-source differences, not standalone stale-entry alpha.

---

## 60s+ Contradiction Detail

The 60s+ bucket is a single trade.

| Field | Value |
|---|---|
| Run ID | `20260522T130017Z_21712_035b3af7` |
| Asset | ETH |
| Side | NO |
| `trade_result` | TP |
| `pnl_usdc` | +0.01238848 |
| Entry quote age | 65.794s |
| Entry quote source | `display_snapshot_sampling` |
| Exit quote age | 17.775s |
| Exit quote source | `display_snapshot_sampling` |
| Entry lifecycle | OPENING_SCAN |
| Exit lifecycle | OPENING_SCAN |
| Entry price | 0.54 |
| Exit price | 0.67 |
| Reason | `take_profit_target_reached` |
| Inventory context | `inv_20260522_ad6f0c60d437` |
| Reload candidate | false |
| Unload candidate | false |
| Starter candidate | false |
| Inventory action | empty |

Answers:

- Was 60s+ TP or SL? TP.
- Single trade or multiple? Single trade.
- Entry age or exit age caused it? The 60s+ bucket is entry age. Exit age was only 17.775s.
- Any lifecycle concentration? Yes, the 60s+ example is OPENING_SCAN on entry and exit.
- Any directional bias? Yes, it is ETH NO. More broadly, ETH NO has older average entry quotes than ETH YES in this sample.
- Any inventory effect? No visible reload/unload/inventory-action effect. The trade had a unique inventory context and no reload/unload flags.

---

## Directional Bias

| Direction | Trades | TP | SL | Mean entry quote age | Mean `pnl_usdc` |
|---|---:|---:|---:|---:|---:|
| ETH YES | 3 | 1 | 2 | 8.793s | -0.007078 |
| ETH NO | 5 | 2 | 3 | 35.446s | -0.001548 |

The oldest quotes are concentrated in ETH NO trades. This creates a directional confound: the 60s+ positive result may reflect ETH NO market movement in that specific epoch, not an independent benefit from quote staleness.

---

## Lifecycle Concentration

| Entry lifecycle | Trades | TP | SL | Mean `pnl_usdc` |
|---|---:|---:|---:|---:|
| OPENING_SCAN | 6 | 3 | 3 | -0.003294 |
| ACTIVE_INVENTORY_TRADING | 2 | 0 | 2 | -0.004604 |

The 60s+ TP occurred in OPENING_SCAN. OPENING_SCAN is mixed overall, with 3 TP and 3 SL. ACTIVE_INVENTORY_TRADING has only two trades and both are SL. This is not enough to classify lifecycle as the cause of the contradiction.

---

## Inventory Effect

No confirmed inventory-driven effect was found:

- 8/8 confirmed trades have unique `inventory_context_id` values.
- 8/8 have `reload_candidate=false`.
- 8/8 have `unload_candidate=false`.
- 8/8 have `starter_candidate=false`.
- 8/8 have blank `inventory_action`.
- Open exposure was approximately one small single-position exposure per trade, not a reload ladder.

Interpretation: the 60s+ TP is not explained by reload/unload recycling or bounded inventory behavior. It is best treated as a single-position outcome.

---

## Classification

Classification: **B = small sample artifact**

Reason:

- The contradiction comes from exactly one 60s+ trade.
- That trade is ETH-only, NO-side, OPENING_SCAN, and single-position.
- The 30-60s bucket is mixed: 1 TP, 1 SL.
- The 5-15s bucket is negative and SL-heavy, but that bucket uses a different quote source (`decision_cycle_fetch`) than the old-entry buckets (`display_snapshot_sampling`).
- No BTC outcome-truth coverage exists.
- No repeated 60s+ wins exist.
- No inventory or lifecycle mechanism proves stale quotes are beneficial.

Rejected classifications:

- A = noise: possible, but the stronger label is small sample artifact because the contradiction is exactly one observation.
- C = inverted relationship: not supported. A true inversion would require repeated older-quote wins or improving PnL across stale buckets.
- D = execution alpha candidate: not supported. There is no repeated 60s+ edge, no BTC confirmation, and no independent mechanism beyond one ETH NO TP.

---

## Exactly Three Future Options

## OPTION 1 - SAFE EV PRESERVATION

Thesis: keep stale quote skepticism intact until the sample proves otherwise.

Quant logic: the confirmed dataset is 8 trades, ETH-only, with one 60s+ TP. A stale quote threshold built from this would overfit.

Likely outcome: more evidence either normalizes the 60s+ bucket downward or shows the current TP was direction-specific.

Hidden risk: ignoring quote-source confounding could make display-snapshot age look like market alpha.

Recommended action: continue collecting clean outcome-truth runs without changing thresholds.

## OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY

Thesis: treat 60s+ display-snapshot quotes as a watchlist feature, not a trading signal.

Quant logic: the 60s+ TP may indicate that some stale display quotes remain directionally useful in slow-moving OPENING_SCAN windows, but evidence is only n=1.

Likely outcome: additional 60s+ observations reveal whether this was a one-off ETH NO movement or a reproducible microstructure condition.

Hidden risk: the next few stale quotes may cluster by asset/side and falsely look predictive.

Recommended action: require at least 5 more 60s+ confirmed trades before considering the relationship anything other than provisional.

## OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

Thesis: the visible contradiction may actually be quote-source and lifecycle confounding.

Quant logic: 5-15s entries are all `decision_cycle_fetch`, while 30s+ entries are all `display_snapshot_sampling`; outcome may be attached to quote source, timing, or side rather than staleness itself.

Likely outcome: separating quote source, lifecycle, and side will explain more variance than age bucket alone.

Hidden risk: Phase 6 could optimize against quote age while the true feature is asset-side regime or snapshot source.

Recommended action: next monitor should stratify `quote_age_bucket x quote_source x side x lifecycle_phase`.

---

## Final Verdict

```
COLLECT_MORE_EVIDENCE
```

The stale quote relationship is not confirmed inverted. Current evidence supports a small sample artifact: one ETH NO OPENING_SCAN TP with a 65.794s entry quote age and a 17.775s exit quote age.

Phase 6 is not ready from this audit.
