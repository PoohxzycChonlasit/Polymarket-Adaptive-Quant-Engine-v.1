# SESSION_EDGE Missing Split Refresh Audit

Date: 2026-05-27

Mode: read-only, docs-only research audit. No code, runtime, replay, promotion, strategy, risk, execution, stoploss, or live changes.

## Lineage

Canonical memory id:

```text
CM-20260525-CA5703
```

Current candidate state:

```text
SESSION_EDGE: PARTIALLY_INVALIDATED
```

Lineage preserved:

- Historical signal-mode research supported `09h10h` as a session-edge candidate.
- `docs/research/dynamic_executable_expectancy_audit.md` reported:
  - `09h10h`: 29 trades, 16 TP / 13 SL, +0.072870 PnL.
  - `09h10h + 0.50-0.70`: 27 trades, 15 TP / 12 SL, +0.069378 PnL.
- `docs/research/positive_expectancy_zone_deep_dive.md` treated `09h10h + 0.50-0.70` as a primary signal-harvest candidate.
- Newer path-truth-era evidence in `docs/research/path_truth/early_research_gate_review.md` and `docs/research/session_edge/session_edge_outside_control_audit.md` weakened the claim:
  - Current completed-gate `09h10h`: 3 trades, 0 TP / 3 SL, -0.035710 PnL.

This refresh does not erase the older signal-mode support. It updates the missing split status using the current completed path-truth gate slice.

## Role Routing

Primary role: `10_BACKTEST_REPLAY_AGENT.md`

Supporting roles: `16_PAPER_EVALUATION_AGENT.md`, `18_MARKET_REGIME_AGENT.md`

Why selected:
- The task compares a session-edge target against controls.
- It needs split-level outcome refresh, evidence sufficiency caution, and regime availability assessment.

Files inspected:
- `runtime/research_state/latest_research_state.md`
- `MASTER_AGENT_ROUTER.md`
- `docs/research/session_edge/session_edge_outside_control_audit.md`
- `docs/research/path_truth/early_research_gate_review.md`
- `docs/research/dynamic_executable_expectancy_audit.md`
- `docs/research/positive_expectancy_zone_deep_dive.md`
- `runtime/quant_data/trade_journal/2026-05-24.jsonl`
- `runtime/quant_data/trade_journal/2026-05-25.jsonl`
- `runtime/quant_data/trade_journal/2026-05-26.jsonl`

Files intentionally ignored:
- Strategy modules, risk modules, execution modules, wallet/live config, replay execution, and runtime mutation paths.

## Classification Rules

| Classification | Meaning |
|---|---|
| SUPPORTED | Current `09h10h` target split outperforms controls with usable sample depth. |
| WEAKENED | Prior support remains in lineage, but current split is thin, mixed, or no longer confirms. |
| ADVERSE | Current `09h10h` target split is worse than controls or all observed current rows fail. |
| UNAVAILABLE | Field or target split is missing from direct evidence. |

## Evidence Window

Current refresh window:

- Completed path-truth gate dates only.
- Dates: 2026-05-24, 2026-05-25, 2026-05-26.

Groups:

| Group | Definition |
|---|---|
| `09h10h target` | paired trade where UTC open hour is 09 or 10 |
| `outside_control20` | first 20 chronological paired trades where UTC open hour is not 09 or 10 |
| `outside_all` | all paired trades in the completed gate where UTC open hour is not 09 or 10 |

Topline:

| Group | Trades | TP | SL | Win Rate | PnL | Median Hold |
|---|---:|---:|---:|---:|---:|---:|
| 09h10h target | 3 | 0 | 3 | 0.0% | -0.035710 | 7s |
| outside_control20 | 20 | 9 | 11 | 45.0% | +0.026830 | 22s |
| outside_all | 102 | 31 | 71 | 30.4% | -0.144839 | 12s |

Current `09h10h` target rows:

| Date | Asset | Side | Phase | Entry | Price Bucket | Result | PnL | Hold |
|---|---|---|---|---:|---|---|---:|---:|
| 2026-05-25 | BTC | YES | OPENING | 0.62 | 0.50-0.70 | SL | -0.001221 | 32s |
| 2026-05-26 | BTC | YES | OPENING | 0.51 | 0.50-0.70 | SL | -0.029299 | 7s |
| 2026-05-26 | ETH | YES | ACTIVE | 0.58 | 0.50-0.70 | SL | -0.005190 | 5s |

## Missing Split Refresh

### BTC / ETH

| Split | 09h10h Target | Outside Control20 | Outside All | Classification |
|---|---:|---:|---:|---|
| BTC | 0 TP / 2 SL, -0.030520 | 1 TP / 3 SL, -0.012136 | 6 TP / 33 SL, -0.163593 | ADVERSE |
| ETH | 0 TP / 1 SL, -0.005190 | 8 TP / 8 SL, +0.038966 | 25 TP / 38 SL, +0.018754 | ADVERSE |

Interpretation:

The current `09h10h` slice no longer shows the historical BTC recovery. BTC fails inside the target, and ETH also fails in its single target row. Because the target sample is only 3 rows, this is adverse but not final invalidation.

### YES / NO

| Split | 09h10h Target | Outside Control20 | Outside All | Classification |
|---|---:|---:|---:|---|
| YES | 0 TP / 3 SL, -0.035710 | 6 TP / 7 SL, +0.029956 | 17 TP / 33 SL, -0.028739 | ADVERSE |
| NO | 0 rows | 3 TP / 4 SL, -0.003126 | 14 TP / 38 SL, -0.116100 | UNAVAILABLE |

Interpretation:

The current `09h10h` target has only YES rows, and all three are SL. There is no current path-truth-gate `09h10h + NO` evidence, so NO cannot be refreshed directly.

### OPENING / ACTIVE

| Split | 09h10h Target | Outside Control20 | Outside All | Classification |
|---|---:|---:|---:|---|
| OPENING | 0 TP / 2 SL, -0.030520 | 6 TP / 10 SL, +0.011412 | 23 TP / 56 SL, -0.130210 | ADVERSE |
| ACTIVE | 0 TP / 1 SL, -0.005190 | 3 TP / 1 SL, +0.015418 | 8 TP / 15 SL, -0.014629 | ADVERSE |

Interpretation:

The current target weakens both lifecycle claims. Historical `09h10h` support included OPENING and ACTIVE survival; the current completed-gate target has neither.

### Price Bucket

| Split | 09h10h Target | Outside Control20 | Outside All | Classification |
|---|---:|---:|---:|---|
| `<0.30` | 0 rows | 0 rows | 0 rows | UNAVAILABLE |
| `0.30-0.50` | 0 rows | 0 TP / 1 SL, -0.004474 | 5 TP / 12 SL, -0.031192 | UNAVAILABLE |
| `0.50-0.70` | 0 TP / 3 SL, -0.035710 | 9 TP / 10 SL, +0.031304 | 26 TP / 59 SL, -0.113647 | ADVERSE |
| `0.70+` | 0 rows | 0 rows | 0 rows | UNAVAILABLE |

Interpretation:

All current target rows are in the same `0.50-0.70` bucket that historically supported `09h10h`. The refreshed result is the opposite direction: 0 TP / 3 SL. This is the most direct current split-level adverse finding.

### Regime

| Split | 09h10h Target | Outside Controls | Classification |
|---|---|---|---|
| market_regime | not directly present in `trade_journal` / `path_truth` target rows | not directly present in paired control rows | UNAVAILABLE |
| trend_regime | not directly present in `trade_journal` / `path_truth` target rows | not directly present in paired control rows | UNAVAILABLE |
| volatility_regime | not directly present in `trade_journal` / `path_truth` target rows | not directly present in paired control rows | UNAVAILABLE |
| delta_regime | not directly present in `trade_journal` / `path_truth` target rows | not directly present in paired control rows | UNAVAILABLE |

Interpretation:

Regime fields exist in `decision_log`, but this refresh did not treat them as canonical because the paired trade/path-truth control surface does not directly carry regime. A future docs-only join-confidence audit can attempt regime reconstruction, but this report preserves the direct-source lineage and marks regime unavailable.

## Refresh Verdict

| Split Family | Classification | Reason |
|---|---|---|
| BTC / ETH | ADVERSE | Both current target asset splits are 0 TP. |
| YES / NO | ADVERSE / UNAVAILABLE | YES is adverse; NO has no current target rows. |
| OPENING / ACTIVE | ADVERSE | Both current lifecycle target splits are 0 TP. |
| Price bucket | ADVERSE / UNAVAILABLE | `0.50-0.70` is adverse; other target buckets are absent. |
| Regime | UNAVAILABLE | Not directly present in paired target/control evidence. |

Overall refreshed status:

```text
SESSION_EDGE_MISSING_SPLITS_REFRESH: ADVERSE_CURRENT_SLICE
CM-20260525-CA5703: PARTIALLY_INVALIDATED
```

Why not fully invalidated:

- Current `09h10h` target sample is only 3 trades.
- NO-side target evidence is absent.
- Regime split is unavailable directly.
- Historical signal-mode lineage had meaningful positive support.

Why not supported:

- Every current path-truth-gate `09h10h` row is SL.
- The same `0.50-0.70` price bucket that historically supported the edge is adverse in the refreshed target.
- Outside controls outperform the target in the fixed 20-control batch, and the full outside pool is less bad by win rate.

## Research State Update

Current interpretation:

`09h10h` remains a review-only candidate. Its historical signal-mode edge is now under active disconfirmation pressure from path-truth-era evidence.

Survives:

- The lineage survives as a hypothesis.
- The need for more `09h10h` evidence survives.

Does not survive as current claim:

- `09h10h` as a supported edge.
- `09h10h + 0.50-0.70` as currently supported.
- BTC recovery inside current `09h10h`.
- ACTIVE survival inside current `09h10h`.

Blocked:

- NO split refresh.
- Regime split refresh.
- Any executable or live claim.

## Next Safe Step

Continue evidence farming until there are enough current path-truth-era `09h10h` rows to retest the missing splits:

- At least 20 current `09h10h` paired trades.
- At least 5 BTC and 5 ETH target rows.
- At least 5 YES and 5 NO target rows.
- At least 5 OPENING and 5 ACTIVE target rows.
- Direct regime fields in paired trade/path-truth events, or a separate documented join-confidence audit.

No strategy, stoploss, risk, execution, replay, promotion, or live action should follow from this refresh.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Replay run: No

Promotion: No

Tests run: Not required. This was a docs-only read-only audit.
