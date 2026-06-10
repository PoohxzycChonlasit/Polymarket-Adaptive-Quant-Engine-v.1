# ETH_YES_FC_OS Command Center

Generated: 2026-06-10T12:20:32Z

Source evidence: `canonical_export:runtime/research_exports/canonical_regime_enriched_trades_v1.csv`

Mode: offline report-only

Non-authorization: this report does not change strategy, risk, execution, sizing, live behavior, runtime policy, or alerts.

---

## Panel A: Gate Status

### Promotion Gates

| Gate | Criterion | Status | Current |
|---|---|---|---|
| P1 | n >= 100 | OPEN | Canonical n = 70 |
| P2 | WR > 52% | PASS | 57.1% |
| P3 | PF > 1.5 | PASS | 2.006 |
| P4 | p < 0.05 at or before n=100 | OPEN | p=0.141; n_required=128 |
| P5 | >= 3 calendar weeks | PASS | 4 weeks (2026-W21, 2026-W22, 2026-W23, 2026-W24) |

### Canonical Count

| Metric | Value |
|---|---:|
| Raw filtered rows | 71 |
| Duplicate rows removed | 1 |
| Canonical n | 70 |
| Remaining to n=70 | 0 |
| Remaining to n=100 | 30 |

### Runtime Integrity

| Check | Status |
|---|---|
| JSONL Writer | PASS |
| Source mode | canonical_export |
| Export validation | VALID |
| Source freshness | FRESH/RECENT (0.0 hours) |
| Unknown regime rate | 0.0% |

---

## Panel B: Progress Rail

```text
n = 70 / 100  [############################------------]  70.0%
```

| Metric | Current | Target | Gap |
|---|---:|---:|---:|
| WR | 57.1% | >52.0% | 5.1% |
| PF | 2.006 | >1.500 | 0.506 |
| p-value | 0.141 | <0.050 | n_required=128 |

### P4 Transform

| WR scenario | n required for p < 0.05 |
|---|---:|
| Current WR (57.1%) | 128 |
| 59.0% | 78 |
| 60.0% | 62 |

### ETA To Next Snapshot

| Velocity basis | Rate | ETA to n=70 |
|---|---:|---:|
| 7-day rolling | 1.43/day | 0 days |
| 14-day rolling | 1.57/day | 0 days |
| Historical campaign | 3.04/day | 0 days |

---

## Panel C: Leading Indicators

### nc_PF Monitor

| Metric | Value |
|---|---:|
| Current nc_PF window=20 | 3.865 |
| Consecutive below 1.0 | 0 |
| Trough index | 45 |
| Trough value | 0.596 |
| nc_PF data quality | RELIABLE |
| Tripwire status | CLEAR |

### Market Structure

| Metric | Value |
|---|---|
| Decision log scan window | 1 dated files |
| Latest decision date | 2026-06-10 |
| ETH COMPRESSION share latest | 0.0% |
| ETH COMPRESSION share 7d | 0.0% |
| Historical COMPRESSION share | 43.1% |
| Last COMPRESSION date >5% | [MANUAL REQUIRED] |
| COMPRESSION absence days | [MANUAL REQUIRED] |
| BTC regime latest | SIDEWAY |
| Latest decision count | 7200 |

### Velocity And Stall

| Metric | Value |
|---|---:|
| Qualifying trades today | 3 |
| Days since last qualifying trade | 0 |
| 7d velocity | 1.43/day |
| 14d velocity | 1.57/day |
| Velocity status | ACTIVE |

### Last-5 Regime Sequence

```text
TREND_UP -> SIDEWAY -> TREND_UP -> TREND_UP -> SIDEWAY
```

Regime mix:

```text
COMPRESSION:21, SIDEWAY:18, TREND_DOWN:19, TREND_UP:12
```

---

## Panel D: Kill Criterion Monitors

| Guard | Criterion | Status | Current |
|---|---|---|---|
| K1 | New-block WR < 48% on >=30 new trades | INACTIVE | n_new=9; WR=55.6%; PF=1.803 |
| K2 | Cumulative PF < 1.3 at n>=80 | INACTIVE | PF=2.006; buffer=0.706 |
| K3 | BTC WR > 40% on n_BTC>=20 | INACTIVE | n_BTC=13; WR=23.1% |
| K4 | Excl. top-5 PF < 1.0 at n=100 | INACTIVE | excl_top_5_pf=1.451 |
| nc_PF | >10 consecutive below 1.0 advisory | CLEAR | 0/10 |

---

## Snapshot Summary

| Metric | Value |
|---|---:|
| Wins | 40 |
| Losses | 30 |
| Gross win PnL | +0.430267 |
| Gross loss PnL | -0.214493 |
| Net PnL | +0.215774 |
| Median PnL | +0.005783 |

## Governor Read

This command center is observational only. Use it to decide whether to continue accumulation, trigger a drift review, or prepare the next milestone snapshot. It does not authorize runtime filters, execution changes, risk changes, or live trading.
