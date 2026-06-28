# ETH_YES_FC_OS Command Center

Generated: 2026-06-28T01:05:37Z

Source evidence: `canonical_export:runtime/research_exports/canonical_regime_enriched_trades_v1.csv`

Mode: offline report-only

Non-authorization: this report does not change strategy, risk, execution, sizing, live behavior, runtime policy, or alerts.

---

## Panel A: Gate Status

### Promotion Gates

| Gate | Criterion | Status | Current |
|---|---|---|---|
| P1 | n >= 100 | PASS | Canonical n = 105 |
| P2 | WR > 52% | PASS | 57.1% |
| P3 | PF > 1.5 | PASS | 2.134 |
| P4 | p < 0.05 at or before n=100 | OPEN | p=0.086; n_required=128 |
| P5 | >= 3 calendar weeks | PASS | 6 weeks (2026-W21, 2026-W22, 2026-W23, 2026-W24, 2026-W25, 2026-W26) |

### Canonical Count

| Metric | Value |
|---|---:|
| Raw filtered rows | 106 |
| Duplicate rows removed | 1 |
| Canonical n | 105 |
| Remaining to n=70 | 0 |
| Remaining to n=100 | 0 |

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
n = 105 / 100  [########################################]  105.0%
```

| Metric | Current | Target | Gap |
|---|---:|---:|---:|
| WR | 57.1% | >52.0% | 5.1% |
| PF | 2.134 | >1.500 | 0.634 |
| p-value | 0.086 | <0.050 | n_required=128 |

### P4 Transform

| WR scenario | n required for p < 0.05 |
|---|---:|
| Current WR (57.1%) | 128 |
| 59.0% | 78 |
| 60.0% | 62 |

### ETA To Next Snapshot

| Velocity basis | Rate | ETA to n=70 |
|---|---:|---:|
| 7-day rolling | 1.14/day | 0 days |
| 14-day rolling | 2.29/day | 0 days |
| Historical campaign | 2.56/day | 0 days |

---

## Panel C: Leading Indicators

### nc_PF Monitor

| Metric | Value |
|---|---:|
| Current nc_PF window=20 | 1.580 |
| Consecutive below 1.0 | 0 |
| Trough index | 45 |
| Trough value | 0.596 |
| nc_PF data quality | RELIABLE |
| Tripwire status | CLEAR |

### Market Structure

| Metric | Value |
|---|---|
| Decision log scan window | 1 dated files |
| Latest decision date | 2026-06-28 |
| ETH COMPRESSION share latest | 0.0% |
| ETH COMPRESSION share 7d | 0.0% |
| Historical COMPRESSION share | 43.1% |
| Last COMPRESSION date >5% | [MANUAL REQUIRED] |
| COMPRESSION absence days | [MANUAL REQUIRED] |
| BTC regime latest | COMPRESSION |
| Latest decision count | 51 |

### Velocity And Stall

| Metric | Value |
|---|---:|
| Qualifying trades today | 0 |
| Days since last qualifying trade | 3 |
| 7d velocity | 1.14/day |
| 14d velocity | 2.29/day |
| Velocity status | ACTIVE |

### Last-5 Regime Sequence

```text
TREND_DOWN -> COMPRESSION -> TREND_UP -> TREND_DOWN -> SIDEWAY
```

Regime mix:

```text
COMPRESSION:25, SIDEWAY:32, TREND_DOWN:28, TREND_UP:20
```

---

## Panel D: Kill Criterion Monitors

| Guard | Criterion | Status | Current |
|---|---|---|---|
| K1 | New-block WR < 48% on >=30 new trades | PASS | n_new=44; WR=56.8%; PF=2.264 |
| K2 | Cumulative PF < 1.3 at n>=80 | PASS | PF=2.134; buffer=0.834 |
| K3 | BTC WR > 40% on n_BTC>=20 | INACTIVE | n_BTC=19; WR=21.1% |
| K4 | Excl. top-5 PF < 1.0 at n=100 | PASS | excl_top_5_pf=1.691 |
| nc_PF | >10 consecutive below 1.0 advisory | CLEAR | 0/10 |

---

## Snapshot Summary

| Metric | Value |
|---|---:|
| Wins | 60 |
| Losses | 45 |
| Gross win PnL | +0.734053 |
| Gross loss PnL | -0.343983 |
| Net PnL | +0.390070 |
| Median PnL | +0.005657 |

## Governor Read

This command center is observational only. Use it to decide whether to continue accumulation, trigger a drift review, or prepare the next milestone snapshot. It does not authorize runtime filters, execution changes, risk changes, or live trading.
