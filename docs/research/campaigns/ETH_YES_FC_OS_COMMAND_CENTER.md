# ETH_YES_FC_OS Command Center

Generated: 2026-06-07T14:39:59Z

Source evidence: `trade_journal:runtime/quant_data/trade_journal`

Mode: offline report-only

Non-authorization: this report does not change strategy, risk, execution, sizing, live behavior, runtime policy, or alerts.

---

## Panel A: Gate Status

### Promotion Gates

| Gate | Criterion | Status | Current |
|---|---|---|---|
| P1 | n >= 100 | OPEN | Canonical n = 61 |
| P2 | WR > 52% | PASS | 57.4% |
| P3 | PF > 1.5 | PASS | 2.031 |
| P4 | p < 0.05 at or before n=100 | OPEN | p=0.153; n_required=117 |
| P5 | >= 3 calendar weeks | PASS | 3 weeks (2026-W21, 2026-W22, 2026-W23) |

### Canonical Count

| Metric | Value |
|---|---:|
| Raw filtered rows | 62 |
| Duplicate rows removed | 1 |
| Canonical n | 61 |
| Remaining to n=70 | 9 |
| Remaining to n=100 | 39 |

### Runtime Integrity

| Check | Status |
|---|---|
| JSONL Writer | BLOCKED |
| CSV freshness | STALE >24h (57.9 hours) |

---

## Panel B: Progress Rail

```text
n = 61 / 100  [########################----------------]  61.0%
```

| Metric | Current | Target | Gap |
|---|---:|---:|---:|
| WR | 57.4% | >52.0% | 5.4% |
| PF | 2.031 | >1.500 | 0.531 |
| p-value | 0.153 | <0.050 | n_required=117 |

### P4 Transform

| WR scenario | n required for p < 0.05 |
|---|---:|
| Current WR (57.4%) | 117 |
| 59.0% | 78 |
| 60.0% | 62 |

### ETA To Next Snapshot

| Velocity basis | Rate | ETA to n=70 |
|---|---:|---:|
| 7-day rolling | 0.43/day | 21 days |
| 14-day rolling | 2.07/day | 5 days |
| Historical campaign | 3.05/day | 3 days |

---

## Panel C: Leading Indicators

### nc_PF Monitor

| Metric | Value |
|---|---:|
| Current nc_PF window=20 | 2.551 |
| Consecutive below 1.0 | 0 |
| Trough index | 4 |
| Trough value | 1.010 |
| Tripwire status | CLEAR |

### Market Structure

| Metric | Value |
|---|---|
| Decision log scan window | 1 dated files |
| Latest decision date | 2026-06-07 |
| ETH COMPRESSION share latest | 0.0% |
| ETH COMPRESSION share 7d | 0.0% |
| Historical COMPRESSION share | 43.1% |
| Last COMPRESSION date >5% | [MANUAL REQUIRED] |
| COMPRESSION absence days | [MANUAL REQUIRED] |
| BTC regime latest | TREND_UP |
| Latest decision count | 9034 |

### Velocity And Stall

| Metric | Value |
|---|---:|
| Qualifying trades today | 0 |
| Days since last qualifying trade | 1 |
| 7d velocity | 0.43/day |
| 14d velocity | 2.07/day |
| Velocity status | STALLED |

### Last-5 Regime Sequence

```text
UNKNOWN -> UNKNOWN -> UNKNOWN -> UNKNOWN -> UNKNOWN
```

Regime mix:

```text
UNKNOWN:61
```

---

## Panel D: Kill Criterion Monitors

| Guard | Criterion | Status | Current |
|---|---|---|---|
| K1 | New-block WR < 48% on >=30 new trades | INACTIVE | n_new=0; WR=N/A; PF=N/A |
| K2 | Cumulative PF < 1.3 at n>=80 | INACTIVE | PF=2.031; buffer=0.731 |
| K3 | BTC WR > 40% on n_BTC>=20 | INACTIVE | n_BTC=11; WR=27.3% |
| K4 | Excl. top-5 PF < 1.0 at n=100 | INACTIVE | excl_top_5_pf=1.409 |
| nc_PF | >10 consecutive below 1.0 advisory | CLEAR | 0/10 |

---

## Snapshot Summary

| Metric | Value |
|---|---:|
| Wins | 35 |
| Losses | 26 |
| Gross win PnL | +0.388473 |
| Gross loss PnL | -0.191308 |
| Net PnL | +0.197165 |
| Median PnL | +0.005883 |

## Governor Read

This command center is observational only. Use it to decide whether to continue accumulation, trigger a drift review, or prepare the next milestone snapshot. It does not authorize runtime filters, execution changes, risk changes, or live trading.
