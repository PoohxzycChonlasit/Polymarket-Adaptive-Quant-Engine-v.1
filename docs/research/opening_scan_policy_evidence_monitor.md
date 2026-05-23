# Opening Scan Policy Evidence Monitor v1

Document type: living evidence tracker. Updated after each paper session with new outcome-truth trades.

First entry: 2026-05-23

Runtime behavior changed: No. Code changed: No.

Evidence threshold (from `opening_scan_policy_candidate_design.md`):
- Policy D: ≥ 50 ACTIVE_INVENTORY_TRADING trades, ≥ 5 dates
- Policy B: ≥ 100 matched trades, ≥ 20 ETH TP in 0–30s, ≥ 5 dates
- Both: false-block rate must remain 0 (no TP blocked) throughout accumulation

---

## How to Read This Monitor

Each snapshot section is added after a paper session. Metrics are cumulative across all instrumentation-era dates. A new snapshot is added when ≥ 5 new matched trades exist since the prior snapshot.

**Match method:** `trade_open.lifecycle_phase` (Policy D gate) + computed `epoch_elapsed_s = fill_unix_ts − epoch_start_ts` (Policy B gate) + `trade_close.trade_result` / `pnl_usdc` (outcome truth). Methodology documented in `opening_scan_policy_replay_feasibility_audit.md`.

---

## Snapshot 1 — 2026-05-23 (Session Active)

Captured at: 2026-05-23, current harvest session `20260523T020201Z_1500_a1f33f5a` still running.

### Evidence Progress

```
Matched trades    28 / 100  [############################--------------------]  28%
ETH TP (0-30s)     7 / 20   [###############-------------------------------------]  35%
Dates covered      2 / 5    [########--------------------------------------------]  40%
```

### Core Counts

| Metric | Value |
|---|---|
| Total matched trades | 28 |
| Dates covered | 2026-05-22, 2026-05-23 |
| Instrumentation-era sessions | 8 |
| TP | 7 |
| SL | 21 |
| Overall TP rate | 25.0% |
| Overall mean PnL | −0.005295 |

### Policy D Gate — lifecycle_phase at Entry

| Lifecycle phase | n | TP | SL | TP rate | Mean PnL |
|---|---:|---:|---:|---:|---:|
| OPENING_SCAN | 19 | 7 | 12 | 36.8% | −0.003094 |
| ACTIVE_INVENTORY_TRADING | 9 | 0 | 9 | 0.0% | −0.008221 |

Policy D false-block count (ACTIVE TP): **0**
Policy D retained TP count: **7 / 7** (100% preserved)

```
ACTIVE_INVENTORY_TRADING SL   9 / 9   [####################] 100%  all blocked = SL
ACTIVE_INVENTORY_TRADING TP   0 / 0   no false blocks yet
Progress to D threshold       9 / 50  [####----------------]  18%
```

### Policy B Gate — epoch_elapsed_s at Entry Fill

| Elapsed bucket | n | TP | SL | TP rate | Mean PnL |
|---|---:|---:|---:|---:|---:|
| ≤ 30s (allow) | 16 | 7 | 9 | 43.8% | −0.001788 |
| > 30s (block) | 12 | 0 | 12 | 0.0% | −0.008680 |

Policy B false-block count (>30s TP): **0**
Policy B retained TP count: **7 / 7** (100% preserved)

```
>30s SL blocked   12 / 12  [####################] 100%  all blocked = SL
>30s TP blocked    0       no false blocks yet
Progress to B threshold   28 / 100  [######--------------]  28%
ETH TP in <=30s    7 / 20  [########------------]  35%
```

### Sub-window Survival (Policy B Context)

| Elapsed sub-bucket | n | TP | SL | TP rate |
|---|---:|---:|---:|---:|
| 0–7s | 3 | 2 | 1 | 66.7% |
| 8–14s | 8 | 3 | 5 | 37.5% |
| 15–30s | 5 | 2 | 3 | 40.0% |
| 31–60s | 9 | 0 | 9 | 0.0% |
| 61–120s | 1 | 0 | 1 | 0.0% |
| > 120s | 1 | 0 | 1 | 0.0% |

30-second cliff: intact (12 consecutive SL after 30s, 0 TP).

### Asset Breakdown

| Asset | n | TP | SL | TP rate |
|---|---:|---:|---:|---:|
| ETH | 24 | 7 | 17 | 29.2% |
| BTC | 4 | 0 | 4 | 0.0% |

BTC TP count: 0 across all elapsed ranges, both lifecycle phases, both sources.

### Pattern Stability Indicators

| Pattern | Snapshot 1 | Stable? |
|---|---|---|
| All TP within elapsed ≤ 30s | 7/7 | Yes (no exceptions yet) |
| All ACTIVE_INVENTORY_TRADING = SL | 9/9 | Yes (no exceptions yet) |
| Policy D false-block rate | 0/9 | Yes |
| Policy B false-block rate | 0/12 | Yes |
| BTC TP rate | 0/4 | Yes (consistent 0%) |
| ETH TP within ≤ 30s | 7/16 (43.8%) | Accumulating |

### Session Ledger

| Date | Run ID (prefix) | Matched closes | OPENING_SCAN | ACTIVE | ≤ 30s | > 30s | TP | SL |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-05-22 | `20260522T094222Z` | 5 | 5 | 0 | 3 | 2 | 6* | 11 |
| 2026-05-22 | `20260522T130017Z` | 4 | 1 | 3 | 2 | 2 | — | — |
| 2026-05-22 | `20260522T153403Z` | 1 | 1 | 0 | 1 | 0 | — | — |
| 2026-05-22 | `20260522T162413Z` | 1 | 1 | 0 | 1 | 0 | — | — |
| 2026-05-22 | `20260522T163940Z` | 6 | 6 | 0 | 4 | 2 | — | — |
| 2026-05-23 | `20260523T014953Z` | 4 | 3 | 1 | 2 | 2 | 1 | 10* |
| 2026-05-23 | `20260523T015426Z` | 2 | 1 | 1 | 0 | 2 | 0 | 2 |
| 2026-05-23 | `20260523T020201Z` | 2 | 2 | 0 | 1 | 1 | 0 | 2 |
| **Total** | | **28** | **19** | **9** | **16** | **12** | **7** | **21** |

\* TP/SL per-run detail not broken out individually here; totals are cumulative.

### What Would Disconfirm the Patterns

The following single events would require immediate note in the next snapshot:

| Event | Impact |
|---|---|
| Any ACTIVE_INVENTORY_TRADING entry resolves TP | Policy D false-block ≥ 1; pattern weakens |
| Any entry at elapsed > 30s resolves TP | Policy B false-block ≥ 1; 30s cliff broken |
| BTC entry at any elapsed resolves TP | BTC = 0 TP pattern broken; BTC research question changes |
| Elapsed ≤ 7s entry resolves SL × 3 consecutive | 0–7s sub-window loses 66.7% TP rate |
| OPENING_SCAN TP rate drops below 20% over next 20 trades | Signal weakening |

### Distance to Evidence Thresholds

| Threshold | Required | Current | Remaining | Est. sessions needed† |
|---|---:|---:|---:|---:|
| Total matched trades (Policy B) | ≥ 100 | 28 | 72 | ~26 |
| ETH TP in ≤ 30s (Policy B) | ≥ 20 | 7 | 13 | ~19 |
| Dates covered (both policies) | ≥ 5 | 2 | 3 | ~3 |
| ACTIVE_INVENTORY_TRADING trades (Policy D) | ≥ 50 | 9 | 41 | ~15 |

† Estimates assume ~2.7 matched trades/session (28 trades / 8 sessions observed). Rate may improve with longer session windows.

### Next Snapshot Trigger

Add a new snapshot row when any of the following occurs:
- ≥ 5 new matched outcome-truth trades since this snapshot (i.e., total ≥ 33)
- A disconfirmation event (ACTIVE TP or >30s TP) occurs at any count
- A new date is added to the evidence base
- Total matched trades crosses a round number (50, 75, 100)

---

## Snapshot Template (for future updates)

```
### Snapshot N — YYYY-MM-DD

Captured at: ...

#### Evidence Progress
[update bars]

#### Core Counts
[update table]

#### Policy D Gate
[update table + false-block count]

#### Policy B Gate
[update table + false-block count]

#### Sub-window Survival
[update table — flag any TP appearing after 30s]

#### Pattern Stability Indicators
[check each row — flag any change from prior snapshot]

#### Delta vs Previous Snapshot
| Metric | Snapshot N-1 | Snapshot N | Delta |
...

#### Notes
[any disconfirmation events, new dates, session anomalies]
```

---

## Appendix: Monitoring Methodology

### Match method

```
For each trade_close with trade_result present:
  1. Find prior trade_open (same run_id, asset, condition_id, ts < close_ts)
  2. Find entry fill from execution_log (same run_id, |fill_ts - open_ts| ≤ 3s)
  3. lifecycle_phase  ← trade_open.payload.lifecycle_phase
  4. epoch_elapsed_s  ← fill_unix_ts − trade_open.payload.epoch_start_ts
  5. trade_result, pnl_usdc ← trade_close.payload
```

### Why trade_close.lifecycle_phase is NOT used

`trade_close.payload.lifecycle_phase` is always `UNKNOWN` in current JSONL (verified across all 28 trades). The entry-time phase is only in `trade_open`. See `opening_scan_policy_replay_feasibility_audit.md`.

### False-block definition

- **Policy D false-block**: any trade where `lifecycle_phase = ACTIVE_INVENTORY_TRADING` AND `trade_result = TP`. Counts how many real TP trades Policy D would have incorrectly blocked.
- **Policy B false-block**: any trade where `epoch_elapsed_s > 30` AND `trade_result = TP`. Counts how many real TP trades Policy B would have incorrectly blocked.

A false-block rate of 0 is required throughout accumulation before any replay evaluation proceeds. If false-block rate becomes non-zero, the policy design document must be revisited.

### Instrumentation era

Only trades with `trade_result` and `pnl_usdc` present in `trade_close` are counted. Pre-instrumentation closes (missing these fields) are excluded from all counts.
