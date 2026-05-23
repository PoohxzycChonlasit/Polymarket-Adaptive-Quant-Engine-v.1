# Phase 6 Readiness Review - Quote Staleness

Date: 2026-05-22

Scope: read-only/docs-only Phase 6 readiness review for `quote_stale_ms`.

Runtime behavior changed: No.

Live behavior changed: No.

Paper launch: No.

Replay run: No.

Code changed: No.

Tests: none; markdown verification only.

---

## Verdict

```text
READY_FOR_PHASE6_METRIC_ONLY
```

Phase 6 may implement `quote_stale_ms` as an additive observability metric only. Current evidence does not support any stale-quote threshold, entry block, risk adjustment, asset policy, S3 promotion, or strategy/execution behavior change.

---

## Evidence Scope

Primary evidence docs:

- `docs/research/sessions/2026-05-22/quote_age_distribution_audit.md`
- `docs/research/sessions/2026-05-22/phase5_evidence_monitor.md`
- `docs/research/sessions/2026-05-22/staleness_contradiction_audit.md`
- Obsidian `06_MICROSTRUCTURE/execution_reality_daily_monitor.md`
- Obsidian `06_MICROSTRUCTURE/btc_evidence_watch.md`

Current review context:

| Metric | Current |
|---|---:|
| Paired outcome-truth trades | 17 |
| BTC paired trades | 3 |
| ETH paired trades | 14 |
| TP / WIN | 6 |
| SL / LOSS | 11 |
| Readiness | 89% |
| `market_analysis_exception` | 0 on latest clean run |
| 60s+ entry quote-age fills | 2 |

Critical caveat: BTC quality is weak at 0 TP / 3 SL.

---

## Quote-Age Evidence

Daily execution reality shows 17 outcome-truth trades with entry-side quote age:

| Entry quote-age bucket | Count | TP | SL |
|---|---:|---:|---:|
| 0-5s | 0 | 0 | 0 |
| 5-15s | 12 | 3 | 9 |
| 15-30s | 0 | 0 | 0 |
| 30-60s | 3 | 1 | 2 |
| 60s+ | 2 | 2 | 0 |

Daily means:

| Metric | Value |
|---|---:|
| Mean entry `quote_age_at_submit_ms` | 24.136s |
| Mean entry `quote_age_at_fill_ms` | 24.139s |
| Mean `pnl_usdc` | -0.003512 |

Earlier 9-trade outcome-truth monitor showed:

| Entry quote-age bucket | Trades | TP | SL | Mean `pnl_usdc` |
|---|---:|---:|---:|---:|
| 5-15s | 5 | 1 | 4 | -0.006089 |
| 30-60s | 3 | 1 | 2 | -0.010346 |
| 60s+ | 1 | 1 | 0 | +0.012388 |

Interpretation: quote age does not currently show the expected monotonic relationship where older quotes produce worse outcomes. The 60s+ bucket is positive, but only because it contains two ETH TP trades. This is not enough to infer stale-quote alpha; it is more likely small-sample, side, source, and lifecycle confounding.

---

## BTC Versus ETH

| Asset | Paired | TP | SL | Mean PnL |
|---|---:|---:|---:|---:|
| BTC | 3 | 0 | 3 | -0.009392 |
| ETH | 14 | 6 | 8 | -0.002252 |

BTC detail:

| Run ID | Asset | Side | Result | PnL | Entry submit age | Entry fill age | Quote source | Bucket |
|---|---|---|---|---:|---:|---:|---|---|
| `20260522T130017Z_21712_035b3af7` | BTC | NO | SL | -0.020121 | 48.617s | 48.619s | `display_snapshot_sampling` | 30-60s |
| `20260522T163940Z_15384_a58a5171` | BTC | NO | SL | -0.004023 | 7.265s | 7.266s | `decision_cycle_fetch` | 5-15s |
| `20260522T163940Z_15384_a58a5171` | BTC | NO | SL | -0.004033 | 11.963s | 11.964s | `decision_cycle_fetch` | 5-15s |

BTC losses are not mainly linked to 60s+ quote staleness. Two of three BTC SL trades were fresh 5-15s decision-cycle fetches. The larger BTC loss used a 30-60s display snapshot, so stale-ish quote age remains a plausible contributor for one BTC loss, but not the dominant explanation across BTC evidence.

---

## TP Versus SL

TP evidence:

- 6 total TP / WIN outcomes.
- The two 60s+ entries are both ETH TP.
- The 60s+ bucket therefore contradicts a simple "older quote equals worse outcome" rule.

SL evidence:

- 11 total SL / LOSS outcomes.
- 9 of 12 trades in the 5-15s bucket are SL.
- BTC contributes 3 SL and 0 TP.

Interpretation: SL concentration is present, but it is not concentrated only in stale quote buckets. The strongest visible weakness is BTC outcome quality and the 5-15s SL-heavy bucket, not confirmed 60s+ quote staleness.

---

## 60s+ Fills

Current 60s+ entry quote-age count is 2. Both are ETH TP. The prior contradiction audit already classified the first 60s+ TP as a small sample artifact because it was one ETH NO OPENING_SCAN trade with display-snapshot quote source and no BTC confirmation.

With two 60s+ TPs, the relationship is still not policy-ready:

- No 60s+ BTC trades exist.
- No 60s+ SL trades exist.
- The 60s+ sample is too small and asset-concentrated.
- Quote source and side remain confounds.

Phase 6 should preserve the raw ages and source segmentation rather than collapse this into a blocking threshold.

---

## Direct Answers

### 1. Does quote age correlate with SL?

Not cleanly. The 5-15s bucket is SL-heavy at 3 TP / 9 SL in the 17-trade daily table, while the 60s+ bucket is 2 TP / 0 SL. Earlier evidence showed 30-60s slightly worse than 5-15s by mean PnL, but the daily state does not support a simple stale-age-to-SL rule.

### 2. Does quote age correlate with PnL?

Only weakly and inconsistently. Overall mean PnL is negative, BTC mean PnL is negative, and the earlier 30-60s bucket was more negative than 5-15s. But the 60s+ bucket is positive due to ETH TP trades. Current evidence supports descriptive tracking, not a threshold.

### 3. Are BTC losses linked to quote staleness?

Partially, but not primarily. One BTC SL used a 48.6s display snapshot, while two BTC SL trades used fresh 7.3s and 12.0s decision-cycle quotes. BTC's 0 TP / 3 SL issue cannot be explained by 60s+ quote staleness.

### 4. Is `quote_stale_ms` useful now?

Yes, as a metric. It is useful because the required fields exist, lineage is present, and it can standardize review as `max(quote_age_at_submit_ms, quote_age_at_fill_ms)`. It is not useful yet as a policy input.

### 5. Should Phase 6 implement only metric, no policy?

Yes. Implement metric-only if Phase 6 proceeds. No runtime block, threshold, risk adjustment, strategy change, execution change, S3 promotion, or live-readiness claim should follow from this sample.

### 6. Is more BTC evidence needed before thresholds?

Yes. BTC count reached the task gate, but quality is weak at 0 TP / 3 SL. More BTC evidence is required before any stale-quote threshold, especially because current BTC losses include two fresh quote entries.

---

## Exactly Three Future Options

### OPTION 1 - SAFE EV PRESERVATION

Thesis: implement only `quote_stale_ms` as observability.

Quant logic: the metric is a low-risk derived field from already-present quote ages, while policy thresholds would overfit 17 trades and especially the 0 TP / 3 SL BTC slice.

Likely outcome: future reviews become cleaner because every fill has one staleness scalar without changing trade behavior.

Hidden risk: operators may treat the metric name as an implicit threshold even though no threshold is validated.

Recommended action: proceed with metric-only Phase 6 and label it non-policy.

### OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY

Thesis: delay all Phase 6 implementation until more BTC and 60s+ evidence accumulates.

Quant logic: BTC has no TP, no BTC 60s+ entries, and the 60s+ bucket is ETH-only positive.

Likely outcome: threshold discussion becomes less fragile after more BTC and stale-bucket observations.

Hidden risk: delaying the metric also delays better evidence collection because `quote_stale_ms` would simplify future monitoring.

Recommended action: use this only if the team cannot keep metric and policy clearly separated.

### OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

Thesis: the real issue may be asset/side/source/lifecycle confounding, not quote age alone.

Quant logic: 60s+ wins are ETH, BTC losses are mostly fresh, and quote source differs across buckets.

Likely outcome: stratifying by `quote_source`, asset, side, and lifecycle will explain more variance than staleness alone.

Hidden risk: a naive stale threshold could block the wrong trades and miss the BTC-specific weakness.

Recommended action: implement metric-only, then require review tables by asset, side, source, lifecycle, TP/SL, and PnL before any threshold.

---

## Recommendation

Proceed with Phase 6 metric-only implementation when scoped:

```text
quote_stale_ms = max(quote_age_at_submit_ms, quote_age_at_fill_ms)
```

Rules for that future implementation:

- Additive metric only.
- Fail soft to null.
- Preserve `quote_source`.
- Preserve submit-age and fill-age separately.
- Segment future reviews by BTC vs ETH, TP vs SL, 60s+ fills, quote source, side, and lifecycle.
- Do not use `quote_stale_ms` for entry blocks, risk sizing, exits, S3 promotion, or live readiness.

Final verdict:

```text
READY_FOR_PHASE6_METRIC_ONLY
```
