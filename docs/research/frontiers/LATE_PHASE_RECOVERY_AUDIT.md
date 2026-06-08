# Late Phase Recovery Audit

Date: 2026-06-08

Population: ETH YES FIRST_CYCLE OPENING_SCAN, hold > 15s, canonical retained opportunities from `runtime/research_exports/canonical_regime_enriched_trades_v1.csv`.

Question: why does late phase `#41-62` show stronger performance?

## Summary

| Segment | n | WR | PF | Net PnL |
| --- | ---: | ---: | ---: | ---: |
| Full cell | 62 | 56.5% | 1.980 | +$0.19224 |
| Early #1-20 | 20 | 55.0% | 2.020 | Not primary focus |
| Mid #21-40 | 20 | 50.0% | 1.613 | Trough segment |
| Late #41-62 | 22 | 63.6% | 2.418 | +$0.07893 |

Late phase recovery is real in the observed sample, but it is not broad enough to classify as sustainable. It is best explained as **regime-specific recovery with sample-size warning**.

## Regime Mix

| Regime | Late n | TP / SL | WR | PF | Net PnL | Interpretation |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| COMPRESSION | 6 | 4 / 2 | 66.7% | 2.227 | +$0.02015 | Still positive but no longer dominant |
| TREND_DOWN | 7 | 5 / 2 | 71.4% | 3.552 | +$0.04078 | Main late recovery engine |
| SIDEWAY | 7 | 4 / 3 | 57.1% | 2.572 | +$0.02209 | Better than full-sample SIDEWAY, but small |
| TREND_UP | 2 | 1 / 1 | 50.0% | 0.557 | -$0.00408 | Continued drag |

The late segment is healthier because TREND_DOWN and SIDEWAY both improved while TREND_UP exposure stayed small.

## COMPRESSION Contribution

COMPRESSION contributed 6 of 22 late opportunities and +$0.02015 net. It remained profitable, but it did not drive the whole recovery. This matters because W23 has no COMPRESSION contribution; current continuation depends on non-COMPRESSION quality.

## TREND_DOWN Contribution

TREND_DOWN contributed the strongest late segment:

- n=7.
- WR 71.4%.
- PF 3.552.
- Net +$0.04078.

The recovery therefore depends heavily on TREND_DOWN staying constructive. The TREND_DOWN fast-resolution audit warns that W23 fast holds are episodic and under-sampled, so this should remain a monitoring hypothesis rather than a runtime filter.

## SIDEWAY Contribution

SIDEWAY late-phase performance improved versus full-sample SIDEWAY:

- Late SIDEWAY: n=7, WR 57.1%, PF 2.572.
- Full SIDEWAY: n=16, WR 56.2%, PF 1.228.

The improvement is meaningful but too small to prove a standalone SIDEWAY edge. One W23 SIDEWAY TP and one W23 SIDEWAY SL are now included, leaving the post-COMPRESSION SIDEWAY picture mixed.

## TREND_UP Drag

TREND_UP remains the weakest component:

- Full TREND_UP: n=7, WR 42.9%, PF 0.661, net -$0.01014.
- Late TREND_UP: n=2, PF 0.557, net -$0.00408.

TREND_UP exposure did not prevent late recovery only because exposure stayed small.

## Hold Seconds

| Metric | Late #41-62 |
| --- | ---: |
| Mean hold | 30.3s |
| Median hold | 25.0s |

Late-phase trades continued to hold beyond the 15s qualification line, but they were not extremely long. The recovery is not simply a long-hold artifact; it reflects better realized outcomes in the 20-40s zone plus selected longer COMPRESSION holds.

## Entry And Exit Price

| Metric | Late #41-62 |
| --- | ---: |
| Mean entry price | 0.535 |
| Median entry price | 0.525 |
| Mean exit price | 0.574 |
| Median exit price | 0.610 |

Entry prices remained in the mid-price band. The positive late segment came from favorable exits rather than unusually cheap entries.

## PnL Distribution

| Metric | Late #41-62 |
| --- | ---: |
| Net PnL | +$0.07893 |
| Mean PnL | +$0.00359 |
| Median PnL | +$0.00578 |
| Best trade | +$0.02120 |
| Worst trade | -$0.01232 |

The recovery is not a single-trade artifact. The largest late winner accounts for about 26.9% of late net PnL, and the top contribution is spread across TREND_DOWN, SIDEWAY, and COMPRESSION.

## TP / SL Split

Late phase has 14 TP and 8 SL. The improvement is driven by both a higher TP rate and controlled SL magnitude. Losses did not disappear; they were offset by several mid-sized wins.

## Concentration

Late opportunities occurred across eight dates:

| Date | Count |
| --- | ---: |
| 2026-05-25 | 5 |
| 2026-05-26 | 3 |
| 2026-05-28 | 4 |
| 2026-05-29 | 3 |
| 2026-05-30 | 3 |
| 2026-05-31 | 2 |
| 2026-06-06 | 1 |
| 2026-06-07 | 1 |

This reduces single-day concentration risk, but the effective late recovery is still mostly a late-W22 cluster plus two W23 trades.

## Market Structure Or Sample Artifact?

Evidence for market-structure-driven recovery:

- TREND_DOWN improved after the mid-sequence trough.
- SIDEWAY late PF improved despite COMPRESSION no longer dominating the sequence.
- Recovery persisted across multiple late-W22 dates.

Evidence for sample-size warning:

- Late segment is only 22 trades.
- W23 has only 2 qualifying trades.
- TREND_DOWN and SIDEWAY post-COMPRESSION evidence is still sparse.
- TREND_UP remains negative and could drag PF if exposure rises.

## Verdict

Classification: **REGIME_SPECIFIC_RECOVERY_WITH_SAMPLE_SIZE_WARNING**.

The late phase recovery is not enough to promote or change runtime policy. It is enough to keep evidence accumulation active and to monitor whether new W23/W24 non-COMPRESSION trades maintain nc_PF above 1.0, preferably above 1.5, before the N70 review.
