# ETH_YES_FC_OS Command Center

Generated: 2026-06-21T01:01:30Z

Source evidence: `canonical_export:runtime/research_exports/canonical_regime_enriched_trades_v1.csv`

Mode: offline report-only

Non-authorization: this report does not change strategy, risk, execution, sizing, live behavior, runtime policy, or alerts.

---

## Panel A: Gate Status

### Promotion Gates

| Gate | Criterion | Status | Current |
|---|---|---|---|
| P1 | n >= 100 | OPEN | Canonical n = 97 |
| P2 | WR > 52% | PASS | 56.7% |
| P3 | PF > 1.5 | PASS | 2.133 |
| P4 | p < 0.05 at or before n=100 | OPEN | p=0.111; n_required=143 |
| P5 | >= 3 calendar weeks | PASS | 5 weeks (2026-W21, 2026-W22, 2026-W23, 2026-W24, 2026-W25) |

### Canonical Count

| Metric | Value |
|---|---:|
| Raw filtered rows | 98 |
| Duplicate rows removed | 1 |
| Canonical n | 97 |
| Remaining to n=70 | 0 |
| Remaining to n=100 | 3 |

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
n = 97 / 100  [#######################################-]  97.0%
```

| Metric | Current | Target | Gap |
|---|---:|---:|---:|
| WR | 56.7% | >52.0% | 4.7% |
| PF | 2.133 | >1.500 | 0.633 |
| p-value | 0.111 | <0.050 | n_required=143 |

### P4 Transform

| WR scenario | n required for p < 0.05 |
|---|---:|
| Current WR (56.7%) | 143 |
| 59.0% | 78 |
| 60.0% | 62 |

### ETA To Next Snapshot

| Velocity basis | Rate | ETA to n=70 |
|---|---:|---:|
| 7-day rolling | 3.43/day | 0 days |
| 14-day rolling | 2.57/day | 0 days |
| Historical campaign | 2.85/day | 0 days |

---

## Panel C: Leading Indicators

### nc_PF Monitor

| Metric | Value |
|---|---:|
| Current nc_PF window=20 | 2.521 |
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
| Qualifying trades today | 0 |
| Days since last qualifying trade | 1 |
| 7d velocity | 3.43/day |
| 14d velocity | 2.57/day |
| Velocity status | ACTIVE |

### Last-5 Regime Sequence

```text
SIDEWAY -> SIDEWAY -> COMPRESSION -> SIDEWAY -> COMPRESSION
```

Regime mix:

```text
COMPRESSION:24, SIDEWAY:30, TREND_DOWN:26, TREND_UP:17
```

---

## Panel D: Kill Criterion Monitors

| Guard | Criterion | Status | Current |
|---|---|---|---|
| K1 | New-block WR < 48% on >=30 new trades | PASS | n_new=36; WR=55.6%; PF=2.331 |
| K2 | Cumulative PF < 1.3 at n>=80 | PASS | PF=2.133; buffer=0.833 |
| K3 | BTC WR > 40% on n_BTC>=20 | INACTIVE | n_BTC=17; WR=23.5% |
| K4 | Excl. top-5 PF < 1.0 at n=100 | INACTIVE | excl_top_5_pf=1.677 |
| nc_PF | >10 consecutive below 1.0 advisory | CLEAR | 0/10 |

---

## Snapshot Summary

| Metric | Value |
|---|---:|
| Wins | 55 |
| Losses | 42 |
| Gross win PnL | +0.620165 |
| Gross loss PnL | -0.290699 |
| Net PnL | +0.329465 |
| Median PnL | +0.005520 |

## Governor Read

This command center is observational only. Use it to decide whether to continue accumulation, trigger a drift review, or prepare the next milestone snapshot. It does not authorize runtime filters, execution changes, risk changes, or live trading.
