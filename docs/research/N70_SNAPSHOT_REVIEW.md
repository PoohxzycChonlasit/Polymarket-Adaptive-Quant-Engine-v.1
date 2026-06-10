# N70 Snapshot Review

Date: 2026-06-10

Mode: research governance only

Verdict: `CONTINUE_ACCUMULATION`

## Frozen Evidence

| Field | Value |
|---|---|
| Export path | `runtime/research_exports/canonical_regime_enriched_trades_v1.csv` |
| Export generated at | `2026-06-10T12:19:03Z` |
| Export validation | `PASS` |
| Export freshness | `FRESH` |
| Raw filtered rows | 71 |
| Duplicate rows removed | 1 |
| Canonical opportunities | 70 |
| Regime join rate | 100.0% |
| Direct/strong join rate | 100.0% |
| UNKNOWN regime rate | 0.0% |

Canonical duplicate policy:

```text
condition_id | epoch_start_ts | asset | side | candidate_id
```

The runless logical-opportunity key removed one duplicate execution row. The
frozen N70 view is the first 70 retained canonical opportunities ordered by
entry timestamp and row id.

## Latest Canonical Trade

| Field | Value |
|---|---|
| Exit timestamp | `2026-06-10T11:55:42.833541Z` |
| Run id | `20260609T024002Z_25468_963d7af6` |
| Asset / side | ETH / YES |
| Lifecycle | OPENING_SCAN |
| Hold | 23 seconds |
| Result | TP |
| PnL | +$0.00615426 |
| Regime | SIDEWAY |
| Canonical key | `0x1fa575bbed0f36c467a717e566b575fea885572e90222356c197adbd0efe7e02|1781092500|ETH|YES|candidate_67d47b4c4cbd` |

## N70 Metrics

| Metric | N70 value | Gate | Status |
|---|---:|---:|---|
| Wins / losses | 40 / 30 | - | Recorded |
| WR | 57.1% | >52% | PASS |
| PF | 2.006 | >1.5 | PASS |
| Net PnL | +$0.215774 | >0 | PASS |
| Median PnL | +$0.005783 | >0 | PASS |
| p-value | 0.141 | <0.05 | OPEN |
| nc_PF, rolling non-COMPRESSION window=20 | 3.865 | >=1.0 | PASS |
| Consecutive nc_PF below 1.0 | 0 | <=5 | PASS |
| Calendar weeks | 4 | >=3 | PASS |
| Excluding top-5 PF | 1.451 | >1.0 at n=100 | PASS advisory |

## Regime Mix

| Regime | n | Share | WR | PF | Net PnL |
|---|---:|---:|---:|---:|---:|
| COMPRESSION | 21 | 30.0% | 61.9% | 3.372 | +$0.130067 |
| TREND_DOWN | 19 | 27.1% | 57.9% | 2.209 | +$0.064221 |
| SIDEWAY | 18 | 25.7% | 55.6% | 1.150 | +$0.010131 |
| TREND_UP | 12 | 17.1% | 50.0% | 1.292 | +$0.011355 |

COMPRESSION contributed no trades to the n=62-70 block. TREND_UP expanded to
12 trades but remains below its sample-doubling tripwire of 14.

## N62-N70 Block

| Metric | Value | N70 threshold | Status |
|---|---:|---:|---|
| n | 9 | 9 | PASS |
| Wins / losses | 5 / 4 | - | Recorded |
| WR | 55.6% | >=50% | PASS |
| PF | 1.803 | >=1.3 | PASS |
| Net PnL | +$0.018609 | >0 | PASS |
| Median PnL | +$0.005190 | - | Recorded |
| Regime mix | TREND_UP 5, SIDEWAY 3, TREND_DOWN 1, COMPRESSION 0 | Explained | CAUTION |

| # | Exit timestamp | Regime | Result | PnL | Canonical key |
|---:|---|---|---|---:|---|
| 62 | `2026-06-07T16:05:37.998371Z` | SIDEWAY | SL | -$0.004924 | `0x7b3e3efb99c5f3c840fe37df86942679c8b2efaca0fb9b169f0c72c0085eaab1|1780848300|ETH|YES|candidate_6a572a570b85` |
| 63 | `2026-06-08T18:15:40.125932Z` | TREND_UP | SL | -$0.004318 | `0x4627da498b6488a995e4ee0ee2d891a26235b2c968fd2bbd36138372d3c11cdf|1780942500|ETH|YES|candidate_3290883c047e` |
| 64 | `2026-06-08T20:30:28.055344Z` | TREND_DOWN | TP | +$0.005190 | `0x87e8dd6bf67bf3d663e7c9dec5b30891f58cc1b4e97cd29685f5d264d0b88969|1780950600|ETH|YES|candidate_3775f125496f` |
| 65 | `2026-06-08T21:20:28.276561Z` | TREND_UP | TP | +$0.017614 | `0xf0c4d28df2dc3883d13c6b7a3ff794b687e5cccbed7e78ad20c0957b36dce9b4|1780953600|ETH|YES|candidate_d4b2d9220fc7` |
| 66 | `2026-06-08T22:56:08.574031Z` | TREND_UP | TP | +$0.006897 | `0xe71caf8b60add3a8f5791804da0e38548e4c66a6932c02f4ec361f83c85e04b4|1780959300|ETH|YES|candidate_38b6027fd746` |
| 67 | `2026-06-08T23:30:27.454175Z` | SIDEWAY | SL | -$0.009307 | `0x5dd28695403f0878f0417f9399863202a29b6daac9cf0e8b0f9b14732f25cb0d|1780961400|ETH|YES|candidate_ae11d9a4bd40` |
| 68 | `2026-06-10T10:50:44.038635Z` | TREND_UP | TP | +$0.005939 | `0xac0b1bf3212f85a3f30ee32456b85bee81c1a52c2e877a6583983c4354876ece|1781088600|ETH|YES|candidate_a5935e975648` |
| 69 | `2026-06-10T10:56:01.556448Z` | TREND_UP | SL | -$0.004636 | `0x4b7a9e250aa8c1a125f9167079c08793de8029c2ea976e293dce38dcc9ddb284|1781088900|ETH|YES|candidate_1d23c5caae6b` |
| 70 | `2026-06-10T11:55:42.833541Z` | SIDEWAY | TP | +$0.006154 | `0x1fa575bbed0f36c467a717e566b575fea885572e90222356c197adbd0efe7e02|1781092500|ETH|YES|candidate_67d47b4c4cbd` |

## Gate Review

| Gate | Status |
|---|---|
| Count integrity | PASS: exactly 70 canonical opportunities reproduced |
| Cumulative WR and PF | PASS |
| N62-N70 block WR and PF | PASS |
| Export validation and regime joins | PASS |
| nc_PF tripwire | CLEAR |
| Formal kill criteria | 0 triggered |
| Promotion to VERIFIED | BLOCKED: n<100 and p-value>0.05 |

Warnings:

- COMPRESSION remains absent from the new nine-trade block.
- TREND_UP contributed 5/9 new trades and has cumulative PF 1.292.
- The N70 snapshot is signal-evidence governance only and does not establish
  executable or live-trading readiness.

## Forward Block

```text
Rows 1-70   = discovery / retrospective selected-slice evidence
Rows 71-100 = forward validation block
```

The next formal milestone is n=80. N71 is the first trade in the forward
validation block. N70 rules, cell definition, duplicate policy, and thresholds
are frozen and must not be changed after seeing this snapshot.

## N70 Verdict

`CONTINUE_ACCUMULATION`

The real N70 event is complete. Count integrity, cumulative gates, the n=62-70
block, and drift monitoring pass the governing N70 thresholds. The candidate
remains `VERIFICATION_IN_PROGRESS`; it is not promoted and has no runtime
authority.
