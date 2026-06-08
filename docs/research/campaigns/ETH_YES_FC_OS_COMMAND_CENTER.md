# ETH_YES_FC_OS Command Center

Generated: 2026-06-07T23:20:48Z

Source evidence: `canonical_export:runtime/research_exports/canonical_regime_enriched_trades_v1.csv`

Mode: offline report-only

Non-authorization: this report does not change strategy, risk, execution, sizing, live behavior, runtime policy, or alerts.

---

## Panel A: Gate Status

### Promotion Gates

| Gate | Criterion | Status | Current |
|---|---|---|---|
| P1 | n >= 100 | OPEN | Canonical n = 62 |
| P2 | WR > 52% | PASS | 56.5% |
| P3 | PF > 1.5 | PASS | 1.980 |
| P4 | p < 0.05 at or before n=100 | OPEN | p=0.187; n_required=156 |
| P5 | >= 3 calendar weeks | PASS | 3 weeks (2026-W21, 2026-W22, 2026-W23) |

### Canonical Count

| Metric | Value |
|---|---:|
| Raw filtered rows | 63 |
| Duplicate rows removed | 1 |
| Canonical n | 62 |
| Remaining to n=70 | 8 |
| Remaining to n=100 | 38 |

### Runtime Integrity

| Check | Status |
|---|---|
| JSONL Writer | BLOCKED |
| Source mode | canonical_export |
| Export validation | VALID |
| Source freshness | FRESH/RECENT (0.0 hours) |
| Unknown regime rate | 0.0% |

---

## Panel B: Progress Rail

```text
n = 62 / 100  [#########################---------------]  62.0%
```

| Metric | Current | Target | Gap |
|---|---:|---:|---:|
| WR | 56.5% | >52.0% | 4.5% |
| PF | 1.980 | >1.500 | 0.480 |
| p-value | 0.187 | <0.050 | n_required=156 |

### P4 Transform

| WR scenario | n required for p < 0.05 |
|---|---:|
| Current WR (56.5%) | 156 |
| 59.0% | 78 |
| 60.0% | 62 |

### ETA To Next Snapshot

| Velocity basis | Rate | ETA to n=70 |
|---|---:|---:|
| 7-day rolling | 0.57/day | 14 days |
| 14-day rolling | 2.14/day | 4 days |
| Historical campaign | 3.10/day | 3 days |

---

## Panel C: Leading Indicators

### nc_PF Monitor

| Metric | Value |
|---|---:|
| Current nc_PF window=20 | 2.367 |
| Consecutive below 1.0 | 0 |
| Trough index | 45 |
| Trough value | 0.596 |
| nc_PF data quality | RELIABLE |
| Tripwire status | CLEAR |

### Market Structure

| Metric | Value |
|---|---|
| Decision log scan window | 1 dated files |
| Latest decision date | [MANUAL REQUIRED] |
| ETH COMPRESSION share latest | [MANUAL REQUIRED] |
| ETH COMPRESSION share 7d | [MANUAL REQUIRED] |
| Historical COMPRESSION share | 43.1% |
| Last COMPRESSION date >5% | [MANUAL REQUIRED] |
| COMPRESSION absence days | [MANUAL REQUIRED] |
| BTC regime latest | [MANUAL REQUIRED] |
| Latest decision count | [MANUAL REQUIRED] |

### Velocity And Stall

| Metric | Value |
|---|---:|
| Qualifying trades today | 1 |
| Days since last qualifying trade | 0 |
| 7d velocity | 0.57/day |
| 14d velocity | 2.14/day |
| Velocity status | ACCUMULATING_SLOWLY |

### Last-5 Regime Sequence

```text
COMPRESSION -> COMPRESSION -> COMPRESSION -> SIDEWAY -> SIDEWAY
```

Regime mix:

```text
COMPRESSION:21, SIDEWAY:16, TREND_DOWN:18, TREND_UP:7
```

---

## Panel D: Kill Criterion Monitors

| Guard | Criterion | Status | Current |
|---|---|---|---|
| K1 | New-block WR < 48% on >=30 new trades | INACTIVE | n_new=1; WR=0.0%; PF=0.000 |
| K2 | Cumulative PF < 1.3 at n>=80 | INACTIVE | PF=1.980; buffer=0.680 |
| K3 | BTC WR > 40% on n_BTC>=20 | INACTIVE | n_BTC=11; WR=27.3% |
| K4 | Excl. top-5 PF < 1.0 at n=100 | INACTIVE | excl_top_5_pf=1.373 |
| nc_PF | >10 consecutive below 1.0 advisory | CLEAR | 0/10 |

---

## Snapshot Summary

| Metric | Value |
|---|---:|
| Wins | 35 |
| Losses | 27 |
| Gross win PnL | +0.388473 |
| Gross loss PnL | -0.196232 |
| Net PnL | +0.192241 |
| Median PnL | +0.005783 |

## Governor Read

This command center is observational only. Use it to decide whether to continue accumulation, trigger a drift review, or prepare the next milestone snapshot. It does not authorize runtime filters, execution changes, risk changes, or live trading.
