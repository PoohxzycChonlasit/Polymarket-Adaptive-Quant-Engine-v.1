# Outcome Truth Monitor Update

Date: 2026-05-22

Scope: Phase 5 evidence monitor refresh from inferred outcomes to ground-truth `trade_result` and `pnl_usdc`.

Runtime behavior changed: No.

Live behavior changed: No.

Paper launch: No.

Replay run: No.

Tests: not run, docs-only evidence refresh.

---

## Evidence Source

Targeted read-only JSONL inspection:

- `runtime/quant_data/execution_log/2026-05-22.jsonl`
- `runtime/quant_data/trade_journal/2026-05-22.jsonl`
- `docs/research/sessions/2026-05-22/outcome_truth_patch_validation.md`

Outcome Truth Patch validation commit referenced by operator: `2f02297`.

No runtime, replay, paper launch, code edit, or JSONL rewrite was performed for this monitor update.

---

## Included Runs

Only latest clean outcome-truth instrumentation runs were included:

| Run ID | Fills | Paired trades | Asset | Confirmed `trade_result` / `pnl_usdc` closes | mex |
|---|---:|---:|---|---:|---:|
| `20260522T094222Z_46088_040fac20` | 10 | 5 | ETH | 5/5 | 0 |
| `20260522T130017Z_21712_035b3af7` | 6 | 3 | ETH | 3/3 | 0 |
| Total | 16 | 8 | ETH only | 8/8 | 0 |

The earlier clean Phase 5 run `20260522T082440Z_32952_1b709e78` has quote-age fields but predates outcome truth. It remains excluded from confirmed TP/SL readiness counts.

---

## Current Confirmed Counts

| Metric | Count |
|---|---:|
| Confirmed paired trades | 8 |
| BTC confirmed paired trades | 0 |
| ETH confirmed paired trades | 8 |
| TP confirmed by `trade_result` | 3 |
| SL confirmed by `trade_result` | 5 |
| WIN by `pnl_usdc > 0` | 3 |
| LOSS by `pnl_usdc < 0` | 5 |

`trade_result` and `pnl_usdc` sign agree on all 8 confirmed trade closes.

---

## Quote-Age Distribution

All confirmed fills:

| Bucket | Count |
|---|---:|
| 0-5s | 2 |
| 5-15s | 8 |
| 15-30s | 3 |
| 30-60s | 2 |
| 60s+ | 1 |

Entry fills only:

| Bucket | Trades |
|---|---:|
| 0-5s | 0 |
| 5-15s | 5 |
| 15-30s | 0 |
| 30-60s | 2 |
| 60s+ | 1 |

Exit fills only:

| Bucket | Trades |
|---|---:|
| 0-5s | 2 |
| 5-15s | 3 |
| 15-30s | 3 |
| 30-60s | 0 |
| 60s+ | 0 |

---

## Mean PnL By Entry Quote-Age Bucket

| Entry quote-age bucket | Trades | TP | SL | Mean `pnl_usdc` |
|---|---:|---:|---:|---:|
| 0-5s | 0 | 0 | 0 | n/a |
| 5-15s | 5 | 1 | 4 | -0.006089 |
| 15-30s | 0 | 0 | 0 | n/a |
| 30-60s | 2 | 1 | 1 | -0.005459 |
| 60s+ | 1 | 1 | 0 | +0.012388 |

---

## Quote-Age Vs Outcome Matrix

| Entry quote-age bucket | TP / WIN | SL / LOSS | Total |
|---|---:|---:|---:|
| 0-5s | 0 | 0 | 0 |
| 5-15s | 1 | 4 | 5 |
| 15-30s | 0 | 0 | 0 |
| 30-60s | 1 | 1 | 2 |
| 60s+ | 1 | 0 | 1 |
| Total | 3 | 5 | 8 |

---

## Interpretation

Older quotes do not yet show a confirmed monotonic loss relationship. The 5-15s entry bucket has the strongest SL concentration, but the only 60s+ entry trade was a TP with positive PnL.

Older quotes do not yet show confirmed PnL decay. Mean PnL is negative in 5-15s and 30-60s, but the 60s+ sample is positive and only n=1.

There is no reliable TP concentration. TPs appear once each in 5-15s, 30-60s, and 60s+.

There is an SL concentration in the 5-15s entry bucket: 4 of 5 SLs. This is not enough to set a stale-quote threshold because the sample is ETH-only and total confirmed trades are 8.

BTC vs ETH cannot be compared yet. Confirmed outcome-truth coverage is ETH-only.

---

## Readiness Gates

| Gate | Required | Current | Status |
|---|---:|---:|---|
| Confirmed paired trades | >= 20 | 8 | NOT MET |
| BTC confirmed paired trades | >= 5 | 0 | NOT MET |
| ETH confirmed paired trades | >= 5 | 8 | MET |
| TP confirmed outcomes | >= 5 | 3 | NOT MET |
| SL confirmed outcomes | >= 5 | 5 | MET |
| 60s+ evidence OR strong stale relationship | >= 1 or strong relationship | 1 fill, no strong relationship | PARTIAL |

---

## Phase 6 Recommendation

```
COLLECT_MORE_EVIDENCE
```

Reason: confirmed outcome truth is now present, but Phase 6 readiness is blocked by insufficient paired sample size, zero BTC coverage, and insufficient TP count. The stale-quote relationship is not strong enough to promote because the lone 60s+ trade was profitable.

Persistent tests unchanged.
