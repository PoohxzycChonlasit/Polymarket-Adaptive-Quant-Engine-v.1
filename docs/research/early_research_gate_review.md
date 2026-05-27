# EARLY_RESEARCH_GATE Review

Date: 2026-05-27

Mode: read-only research review. No runtime, replay, strategy, stoploss, risk, execution, or live changes.

## Role Routing

Primary role: `10_BACKTEST_REPLAY_AGENT.md`

Supporting roles: `16_PAPER_EVALUATION_AGENT.md`, `11_OBSERVABILITY_INCIDENT_AGENT.md`

Why selected:
- This review evaluates path-truth and paired trade outcomes after the 3-date research gate.
- It classifies evidence candidates only. It does not authorize implementation.

Files inspected:
- `runtime/research_state/latest_research_state.md`
- `MASTER_AGENT_ROUTER.md`
- `docs/research/path_truth_multiday_coverage_monitor.md`
- `docs/research/fast_close_distribution_audit.md`
- `docs/research/failure_triangle_audit.md`
- `runtime/quant_data/path_truth/2026-05-24.jsonl`
- `runtime/quant_data/path_truth/2026-05-25.jsonl`
- `runtime/quant_data/path_truth/2026-05-26.jsonl`
- `runtime/quant_data/trade_journal/2026-05-24.jsonl`
- `runtime/quant_data/trade_journal/2026-05-25.jsonl`
- `runtime/quant_data/trade_journal/2026-05-26.jsonl`

Files intentionally ignored:
- Strategy, stoploss, risk, execution, live config, wallet, replay execution, and runtime code paths.

## Gate State

EARLY_RESEARCH_GATE is reached at 3 / 3 completed dates.

IMPLEMENTATION_GATE remains blocked at 3 / 7 completed dates.

Completed dates:
- 2026-05-24
- 2026-05-25
- 2026-05-26

Path truth aggregate:

| Metric | Value |
|---|---:|
| Path truth lines | 140 |
| Event-end trades | 88 |
| Full coverage trades | 3 |
| Fast-close partial trades | 85 |
| Parse errors | 0 |
| Duplicate keys | 0 |
| Fast-close share | 96.6% |

Paired trade-journal closes across the same completed dates:

| Metric | Value |
|---|---:|
| Trade closes | 105 |
| TP | 31 |
| SL | 74 |
| Win rate | 29.5% |
| Net PnL | -0.180549 |
| Median hold | 12s |
| Holds under 60s | 101 / 105 |

## Fast Close Behavior

Path-truth checkpoint bucket distribution:

| Bucket | Trades | Share |
|---|---:|---:|
| 0-15s | 55 | 62.5% |
| 15-30s | 22 | 25.0% |
| 30-45s | 5 | 5.7% |
| 45-60s | 3 | 3.4% |
| 60s+ | 3 | 3.4% |

Trade-journal hold bucket distribution:

| Bucket | Trades | TP | SL | Win Rate | PnL |
|---|---:|---:|---:|---:|---:|
| 0-15s | 59 | 12 | 47 | 20.3% | -0.185560 |
| 15-30s | 33 | 13 | 20 | 39.4% | -0.057224 |
| 30-45s | 5 | 1 | 4 | 20.0% | -0.002697 |
| 45-60s | 4 | 3 | 1 | 75.0% | +0.035231 |
| 60s+ | 4 | 2 | 2 | 50.0% | +0.029701 |

Classification: STABLE

Fast close is not weakening. It strengthened versus the earlier 25-trade snapshot, rising from 88% fast-close behavior to 96.6% path-truth fast-close partial coverage. The damage is concentrated in 0-15s and 15-30s. Longer holds are rare and, in this sample, less negative.

Verdict: survives as a core research candidate.

## BTC Weakness Stability

| Segment | Trades | TP | SL | Win Rate | PnL | Median Hold |
|---|---:|---:|---:|---:|---:|---:|
| 2026-05-24 to 2026-05-25 | 27 | 2 | 25 | 7.4% | -0.096723 | 10s |
| 2026-05-26 only | 14 | 4 | 10 | 28.6% | -0.097389 | 11s |
| 3-date gate total | 41 | 6 | 35 | 14.6% | -0.194113 | 10s |

Classification: STABLE

BTC improved on the third date by win rate, but not enough to weaken the candidate materially. The 3-date total remains deeply negative, with 35 SL against 6 TP and worse aggregate PnL than ETH.

Verdict: survives as a BTC_HOSTILE_CANDIDATE, research-only.

## NO Weakness Stability

| Segment | Trades | TP | SL | Win Rate | PnL | Median Hold |
|---|---:|---:|---:|---:|---:|---:|
| 2026-05-24 to 2026-05-25 | 31 | 9 | 22 | 29.0% | -0.070935 | 12s |
| 2026-05-26 only | 21 | 5 | 16 | 23.8% | -0.045165 | 9s |
| 3-date gate total | 52 | 14 | 38 | 26.9% | -0.116100 | 11s |

Classification: STABLE

NO remained negative on the third date and the total sample still shows materially worse outcomes than needed for a healthy side. This is not proven global structural weakness yet, because prior research showed session dependence, but the weakness remains active.

Verdict: survives as NO_SESSION_DEPENDENT / NO_WEAKNESS_CANDIDATE, research-only.

## 02h Hostility Stability

| Segment | Trades | TP | SL | Win Rate | PnL | Median Hold |
|---|---:|---:|---:|---:|---:|---:|
| 2026-05-24 to 2026-05-25 | 5 | 0 | 5 | 0.0% | -0.039490 | 12s |
| 2026-05-26 only | 3 | 1 | 2 | 33.3% | -0.002835 | 25s |
| 3-date gate total | 8 | 1 | 7 | 12.5% | -0.042325 | 12s |

Classification: WEAKENED

The third date introduced one TP and near-flat session PnL, so the hard 0 TP / 12 SL style claim no longer holds for this completed-date slice. The total is still hostile at 1 TP / 7 SL, but sample size is small and the latest date softened the pattern.

Verdict: survives only as a review candidate. It should not be treated as implementation-ready.

## 09h10h Degradation

| Segment | Trades | TP | SL | Win Rate | PnL | Median Hold |
|---|---:|---:|---:|---:|---:|---:|
| 2026-05-24 to 2026-05-25 | 1 | 0 | 1 | 0.0% | -0.001221 | 32s |
| 2026-05-26 only | 2 | 0 | 2 | 0.0% | -0.034490 | 5s |
| 3-date gate total | 3 | 0 | 3 | 0.0% | -0.035710 | 7s |

Classification: WEAKENED

The previous 09h10h edge candidate does not survive the fresh 3-date completed-gate slice as a positive edge. It is not statistically dead because the gate sample has only 3 trades in 09h10h, but current path-truth-era evidence points to degradation, not confirmation.

Verdict: downgraded to review-only. Do not use as an edge claim without more dates.

## Candidate Survival Summary

| Candidate | Classification | Survives? | Status |
|---|---|---|---|
| Fast close behavior | STABLE | Yes | Core research candidate |
| BTC weakness | STABLE | Yes | Research-only hostile candidate |
| NO weakness | STABLE | Yes | Research-only, session-dependent candidate |
| 02h hostility | WEAKENED | Yes, weakly | Review-only |
| 09h10h edge | WEAKENED | No as edge claim | Review-only, degraded |

## Which Candidates Survive

Survive:
- Fast close behavior
- BTC weakness
- NO weakness

Survive only as review candidates:
- 02h hostility
- 09h10h degradation / edge question

Die:
- No candidate is fully invalidated by this gate review.
- The 09h10h positive edge claim does not survive as a current evidence-backed edge, but the sample is too small to kill the hypothesis outright.

## Interpretation

The EARLY_RESEARCH_GATE confirms that path truth is producing useful evidence across multiple dates, but it does not authorize implementation. The main stable signal is not a new strategy edge. It is a failure-shape map:

- Most trades close before 60 seconds.
- The first 15 seconds are especially hostile.
- BTC remains materially worse than ETH.
- NO remains negative and likely session-dependent.
- 02h remains concerning but softened.
- 09h10h no longer has fresh support as an edge in the completed-date slice.

## Next Safe Step

Continue evidence farming toward the 7-date IMPLEMENTATION_GATE. The next review should require:

- At least 7 completed path-truth dates.
- Re-check of fast-close buckets by session, asset, side, and lifecycle phase.
- Confirmation whether 02h hostility remains after more dates.
- Confirmation whether 09h10h degradation persists or was a tiny-sample artifact.
- No field wiring, stoploss, strategy, risk, or live changes before IMPLEMENTATION_GATE.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Replay run: No

Paper runtime launched: No

Tests run: Not required. This was a docs-only, read-only research review.
