# Session Edge Outside Control Audit

Date: 2026-05-27

Mode: read-only, docs-only research audit. No replay, runtime launch, strategy, risk, execution, stoploss, or live changes.

## Role Routing

Primary role: `10_BACKTEST_REPLAY_AGENT.md`

Supporting roles: `16_PAPER_EVALUATION_AGENT.md`, `18_MARKET_REGIME_AGENT.md`

Why selected:
- The task is a session-edge control collection and comparison problem.
- It requires paired trade outcome review, paper evidence caution, and regime field availability assessment.

Files inspected:
- `runtime/research_state/latest_research_state.md`
- `MASTER_AGENT_ROUTER.md`
- `docs/quant_agent_setup_md/roles/10_BACKTEST_REPLAY_AGENT.md`
- `docs/quant_agent_setup_md/roles/16_PAPER_EVALUATION_AGENT.md`
- `docs/quant_agent_setup_md/roles/18_MARKET_REGIME_AGENT.md`
- `docs/research/path_truth_multiday_coverage_monitor.md`
- `docs/research/early_research_gate_review.md`
- `docs/research/dynamic_executable_expectancy_audit.md`
- `runtime/quant_data/trade_journal/2026-05-24.jsonl`
- `runtime/quant_data/trade_journal/2026-05-25.jsonl`
- `runtime/quant_data/trade_journal/2026-05-26.jsonl`
- `runtime/quant_data/path_truth/2026-05-24.jsonl`
- `runtime/quant_data/path_truth/2026-05-25.jsonl`
- `runtime/quant_data/path_truth/2026-05-26.jsonl`

Files intentionally ignored:
- Strategy modules, risk modules, order execution, wallet/live config, replay execution, and runtime mutation paths.

## Purpose

Start collecting outside-session controls for the `SESSION_EDGE` review.

Control definition:

```text
outside-session = paired paper trade where UTC hour is NOT 09h and NOT 10h
target = 20 controls
```

Comparison target:

```text
09h10h sample = paired paper trade where UTC hour is 09h or 10h
```

This audit uses completed path-truth gate dates only:

- 2026-05-24
- 2026-05-25
- 2026-05-26

## Data Availability

| Field | Source | Status |
|---|---|---|
| Asset | `trade_journal` trade_open | available |
| Side | `trade_journal` trade_open outcome | available |
| Lifecycle phase | `trade_journal` trade_open | available |
| Entry price | `trade_journal` trade_open | available |
| Price bucket | derived from entry price | available |
| TP / SL | `trade_journal` trade_close | available |
| Hold seconds | `trade_journal` trade_close | available |
| PnL | `trade_journal` trade_close | available |
| Session hour | derived from trade_open timestamp | available |
| Regime | direct trade/path-truth event | not available |

Regime note:

`decision_log` contains fields such as `market_regime`, `trend_regime`, `volatility_regime`, and `delta_regime`, but `trade_journal` and `path_truth` do not directly carry those fields. Because this audit is read-only and no canonical decision join is currently guaranteed in the path-truth collector, regime is classified as `UNAVAILABLE_DIRECT` for the control set.

This is a source coverage gap, not a strategy finding.

## Control Collection Status

| Pool | Trades | TP | SL | Win Rate | PnL | Median Hold | Fast <60s |
|---|---:|---:|---:|---:|---:|---:|---:|
| Outside-session all available | 102 | 31 | 71 | 30.4% | -0.144839 | 12s | 98 |
| Outside-session first 20 controls | 20 | 9 | 11 | 45.0% | +0.026830 | 22s | 17 |
| 09h10h gate sample | 3 | 0 | 3 | 0.0% | -0.035710 | 7s | 3 |

Target status:

```text
OUTSIDE_CONTROL_TARGET_REACHED: 20 / 20
```

Important interpretation:

- The 20-control collector target is reached.
- The full outside-session pool is much larger than the initial target.
- The first 20 controls are positive, but the full outside pool is negative.
- The 09h10h gate sample is too small and currently adverse.

## First 20 Outside Controls

The first control batch is chronological from the completed gate dates.

| Date | Session | Asset | Side | Phase | Entry | Price Bucket | Result | PnL | Hold |
|---|---|---|---|---|---:|---|---|---:|---:|
| 2026-05-24 | 03h | BTC | NO | ACTIVE | 0.51 | 0.50-0.70 | TP | +0.007468 | 11s |
| 2026-05-24 | 03h | ETH | NO | OPENING | 0.51 | 0.50-0.70 | TP | +0.007872 | 19s |
| 2026-05-24 | 03h | ETH | YES | OPENING | 0.53 | 0.50-0.70 | SL | -0.004736 | 10s |
| 2026-05-24 | 03h | BTC | YES | ACTIVE | 0.55 | 0.50-0.70 | SL | -0.004563 | 22s |
| 2026-05-24 | 04h | ETH | YES | ACTIVE | 0.60 | 0.50-0.70 | TP | +0.005862 | 11s |
| 2026-05-24 | 04h | BTC | NO | OPENING | 0.50 | 0.50-0.70 | SL | -0.012623 | 72s |
| 2026-05-24 | 04h | ETH | YES | OPENING | 0.50 | 0.50-0.70 | TP | +0.027140 | 77s |
| 2026-05-24 | 05h | ETH | YES | OPENING | 0.51 | 0.50-0.70 | SL | -0.008867 | 8s |
| 2026-05-24 | 05h | ETH | YES | OPENING | 0.59 | 0.50-0.70 | TP | +0.005959 | 22s |
| 2026-05-24 | 05h | ETH | NO | OPENING | 0.54 | 0.50-0.70 | SL | -0.005582 | 4s |
| 2026-05-24 | 05h | ETH | NO | ACTIVE | 0.57 | 0.50-0.70 | TP | +0.006650 | 23s |
| 2026-05-24 | 05h | ETH | YES | OPENING | 0.54 | 0.50-0.70 | SL | -0.008377 | 24s |
| 2026-05-24 | 05h | ETH | YES | OPENING | 0.56 | 0.50-0.70 | TP | +0.011664 | 7s |
| 2026-05-24 | 05h | ETH | YES | OPENING | 0.58 | 0.50-0.70 | SL | -0.005201 | 24s |
| 2026-05-24 | 06h | ETH | YES | OPENING | 0.52 | 0.50-0.70 | TP | +0.016431 | 74s |
| 2026-05-24 | 06h | ETH | YES | OPENING | 0.54 | 0.50-0.70 | TP | +0.011178 | 6s |
| 2026-05-24 | 06h | ETH | YES | OPENING | 0.45 | 0.30-0.50 | SL | -0.004474 | 37s |
| 2026-05-24 | 07h | ETH | NO | OPENING | 0.56 | 0.50-0.70 | SL | -0.004493 | 59s |
| 2026-05-24 | 07h | BTC | NO | OPENING | 0.52 | 0.50-0.70 | SL | -0.002419 | 27s |
| 2026-05-24 | 13h | ETH | YES | OPENING | 0.50 | 0.50-0.70 | SL | -0.012060 | 23s |

## Control Classification

### Asset

| Asset | Trades | TP | SL | Win Rate | PnL | Median Hold |
|---|---:|---:|---:|---:|---:|---:|
| BTC | 4 | 1 | 3 | 25.0% | -0.012136 | 22s |
| ETH | 16 | 8 | 8 | 50.0% | +0.038966 | 22s |

Interpretation:

The first 20 outside controls are ETH-heavy and positive because ETH offsets BTC. BTC remains weak inside the control batch.

### Lifecycle

| Phase | Trades | TP | SL | Win Rate | PnL | Median Hold |
|---|---:|---:|---:|---:|---:|---:|
| OPENING | 16 | 6 | 10 | 37.5% | +0.011412 | 23s |
| ACTIVE | 4 | 3 | 1 | 75.0% | +0.015418 | 11s |

Interpretation:

The first 20 controls do not show ACTIVE weakness. This is a small batch effect and conflicts with broader fast-close research where ACTIVE is mostly a fast-close accelerator.

### Price Bucket

Price buckets use the prior session-edge research convention:

- `<0.30`
- `0.30-0.50`
- `0.50-0.70`
- `0.70+`

| Price Bucket | Trades | TP | SL | Win Rate | PnL | Median Hold |
|---|---:|---:|---:|---:|---:|---:|
| 0.50-0.70 | 19 | 9 | 10 | 47.4% | +0.031304 | 22s |
| 0.30-0.50 | 1 | 0 | 1 | 0.0% | -0.004474 | 37s |

Interpretation:

The initial control batch mostly sits in the same `0.50-0.70` zone used by prior 09h10h edge research, which is useful for comparison. The batch is not price-diverse.

### Regime

| Regime Class | Trades | Notes |
|---|---:|---|
| UNAVAILABLE_DIRECT | 20 | `trade_journal` and `path_truth` do not directly carry market regime fields for this control collector. |

Interpretation:

Regime classification is blocked for direct control collection. A future offline join can attempt to map `candidate_id` / `decision_id` / `paper_trade_replay_key` into `decision_log`, but current path-truth controls should not pretend regime is known.

## Outside Pool Context

The first 20 controls are not representative of the full outside-session pool.

### Full Outside Pool by Asset

| Asset | Trades | TP | SL | Win Rate | PnL | Median Hold |
|---|---:|---:|---:|---:|---:|---:|
| BTC | 39 | 6 | 33 | 15.4% | -0.163593 | 10s |
| ETH | 63 | 25 | 38 | 39.7% | +0.018754 | 16s |

### Full Outside Pool by Lifecycle

| Phase | Trades | TP | SL | Win Rate | PnL | Median Hold |
|---|---:|---:|---:|---:|---:|---:|
| OPENING | 79 | 23 | 56 | 29.1% | -0.130210 | 12s |
| ACTIVE | 23 | 8 | 15 | 34.8% | -0.014629 | 11s |

### Full Outside Pool by Price Bucket

| Price Bucket | Trades | TP | SL | Win Rate | PnL | Median Hold |
|---|---:|---:|---:|---:|---:|---:|
| 0.50-0.70 | 85 | 26 | 59 | 30.6% | -0.113647 | 12s |
| 0.30-0.50 | 17 | 5 | 12 | 29.4% | -0.031192 | 8s |

Interpretation:

The full outside-session pool is negative despite the first 20 controls being positive. This means the control collector should continue tracking both:

- the fixed initial 20-control batch;
- the full accumulated outside-session pool.

## 09h10h Comparison

Current completed-gate 09h10h sample:

| Date | Session | Asset | Side | Phase | Entry | Price Bucket | Result | PnL | Hold |
|---|---|---|---|---|---:|---|---|---:|---:|
| 2026-05-25 | 09h10h | BTC | YES | OPENING | 0.62 | 0.50-0.70 | SL | -0.001221 | 32s |
| 2026-05-26 | 09h10h | BTC | YES | OPENING | 0.51 | 0.50-0.70 | SL | -0.029299 | 7s |
| 2026-05-26 | 09h10h | ETH | YES | ACTIVE | 0.58 | 0.50-0.70 | SL | -0.005190 | 5s |

Gate-slice comparison:

| Group | Trades | TP | SL | Win Rate | PnL | Median Hold |
|---|---:|---:|---:|---:|---:|---:|
| Outside first 20 controls | 20 | 9 | 11 | 45.0% | +0.026830 | 22s |
| Outside all available | 102 | 31 | 71 | 30.4% | -0.144839 | 12s |
| 09h10h gate sample | 3 | 0 | 3 | 0.0% | -0.035710 | 7s |

Historical comparison from prior signal-mode research:

- `09h10h`: 29 trades, 16 TP / 13 SL, +0.072870.
- `09h10h + 0.50-0.70`: 27 trades, 15 TP / 12 SL, +0.069378.

Interpretation:

The current path-truth gate slice does not confirm the older 09h10h edge. It shows degradation, but only across 3 trades. The outside control collector is now ready, but more 09h10h observations are needed before accepting or killing the session-edge hypothesis.

## Findings

1. Outside-session control target is reached.

The first 20 controls exist and can be used as the initial comparator batch.

2. The full outside-session pool is negative.

Outside all available is 31 TP / 71 SL with negative PnL. The positive first-20 control batch is not enough to claim outside sessions are healthy.

3. Current 09h10h gate sample is adverse.

The completed gate has only 3 09h10h trades, all SL. This weakens but does not invalidate historical 09h10h research.

4. BTC weakness persists in controls.

The first 20 controls have BTC at 1 TP / 3 SL. The full outside pool has BTC at 6 TP / 33 SL.

5. Price bucket comparison is usable.

Most controls and all current 09h10h samples are in `0.50-0.70`, making the bucket comparison meaningful once more 09h10h trades arrive.

6. Regime comparison is blocked.

Regime is not directly present in paired trade/path-truth control events. It should remain `UNAVAILABLE_DIRECT` until a safe canonical join is available.

## Verdict

```text
OUTSIDE_CONTROL_COLLECTION: STARTED
OUTSIDE_CONTROL_TARGET: REACHED_20_OF_20
SESSION_EDGE_COMPARISON: BLOCKED_BY_THIN_09H10H_SAMPLE
REGIME_CLASSIFICATION: BLOCKED_DIRECT_FIELD_GAP
```

Current research status:

- Outside controls are sufficient to start comparison.
- 09h10h current-gate evidence is insufficient.
- Regime cannot be safely classified from direct control sources.
- No implementation decision should be made from this audit.

## Future Options

OPTION 1 - SAFE EV PRESERVATION:
Continue evidence farming until at least 20 fresh 09h10h path-truth-era trades exist, then compare against the fixed first-20 outside controls and full outside pool.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:
Run a read-only offline join audit that maps trade controls to `decision_log` regime fields by candidate identity, explicitly scoring join confidence.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:
Design a future additive observability field contract for copying regime labels into `trade_open` and path-truth events, but do not wire it before the implementation gate.

Recommended option: OPTION 1 now, with OPTION 2 as the next docs-only audit if regime becomes necessary before 7 completed dates.

## What Not To Do

- Do not change strategy.
- Do not add stoploss rules.
- Do not change risk.
- Do not change execution.
- Do not run replay.
- Do not promote live.
- Do not wire fields before the implementation gate.
- Do not treat the first 20 positive controls as proof that outside sessions are safe.
- Do not treat 3 adverse 09h10h trades as proof that historical 09h10h edge is dead.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Replay run: No

Paper runtime launched: No

Tests run: Not required. This was a docs-only read-only audit.
