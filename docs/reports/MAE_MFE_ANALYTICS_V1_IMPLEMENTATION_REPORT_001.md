# MAE/MFE Analytics V1 — Implementation Report

**ID:** MAE_MFE_ANALYTICS_V1_IMPLEMENTATION_REPORT_001
**Date:** 2026-06-23
**Status:** COMPLETE — PENDING COMMIT APPROVAL
**Design Doc:** `MAE_MFE_ANALYTICS_V1_DESIGN_001.md`

---

## 1. Implementation Summary

MAE/MFE Analytics V1 is a **read-only, offline-only** analytics module that surfaces
hold-time expectancy, exit excursion proxies, profit factor, exit-reason distribution,
and regime/side/asset breakdowns from historical research exports.

No runtime, strategy, risk, execution, sizing, or live-trading behavior was changed.

---

## 2. Files Modified

| File | Change Type | Description |
|------|-------------|-------------|
| `tools/dashboard_state_aggregator.py` | MODIFIED | Added `_extract_mae_mfe_analytics()` function (~180 lines), `mae_mfe_analytics` slot in `_empty_state`, and wire in `_apply_research_reports`. |
| `tests/test_dashboard_state_aggregator.py` | MODIFIED | Added 10 new unit tests for MAE/MFE analytics (lines 899–1088). |
| `dashboard/src/types/dashboard.ts` | MODIFIED | Added `MaeMfeAnalytics`, `MfeMaeProxy`, `MaeMaeProxy`, `HoldTimeBucket`, `ExitReasonRow`, `MaeMfeSummary`, `MaeMfeBreakdownRow` TypeScript interfaces. `ResearchAnalytics` extended with `mae_mfe_analytics?: MaeMfeAnalytics`. |
| `dashboard/src/pages/research/ResearchPage.tsx` | MODIFIED | Added `MaeMfePanel` section between Regime Analytics and Roadmap; added MAE/MFE to roadmap with `active v1` status. |

---

## 3. Backend Implementation Detail

### `_extract_mae_mfe_analytics(root_dir: Path) -> dict`

**Location:** `tools/dashboard_state_aggregator.py`, after `_extract_regime_analytics`

**Reads:** `{root_dir}/research_exports/canonical_regime_enriched_trades_v1.csv`

**Fail-soft behavior:**
- CSV missing → `status: "MISSING"`, all fields null, no crash
- CSV exists but has 0 parseable rows → `status: "PARTIAL"`
- Rows with non-numeric `hold_seconds`, `pnl_usdc`, `entry_price`, or `exit_price` → skipped, counted in `PARSE_ERRORS` alert
- `statistics.quantiles` failure → `None` returned safely

**Computed fields:**
- `summary`: win_rate, profit_factor, avg_winner/loser_pnl, avg_winner/loser_hold_s, avg_mfe/mae_proxy, tp/sl/forced counts
- `exit_reason_distribution`: Counter by `exit_reason`, sorted descending by count with share
- `hold_time_buckets`: 5 fixed buckets (0-15s, 15-30s, 30-45s, 45-60s, 60s+), each with n, win_rate, mean_pnl, total_pnl, tp_count, sl_count
- `mfe_proxy`: exit_price - entry_price for TP trades (mean, median, min, max, P25, P75)
- `mae_proxy`: entry_price - exit_price for SL trades (mean, median, min, max, P25, P75)
- `regime_breakdown`, `side_breakdown`, `asset_breakdown`: aggregated by dimension
- `optimal_hold_bucket`: bucket with highest positive mean_pnl (n>=5)
- `dominant_loss_bucket`: bucket with lowest (most negative) total_pnl (n>=5)
- `verdict`: EXPECTANCY_POSITIVE / EXPECTANCY_NEGATIVE / INSUFFICIENT_DATA
- `alerts`: parse error counts

**Data note:**
Terminal excursion proxies only. No intra-trade tick MAE/MFE recorded in current JSONL schema.
`data_warning` field propagated to dashboard state and UI.

---

## 4. Test Results

```
python -m pytest tests/test_dashboard_state_aggregator.py -q
44 passed in 1.00s
```

**New tests added (10):**

| Test | Verified Behavior |
|------|--------------------|
| `test_mae_mfe_missing_csv` | status=MISSING when CSV absent |
| `test_mae_mfe_empty_csv` | status=PARTIAL for header-only CSV |
| `test_mae_mfe_minimal_csv` | Correct aggregation for 10-row synthetic CSV |
| `test_mae_mfe_win_loss_split` | tp + sl + forced == total_trades |
| `test_mae_mfe_hold_time_buckets` | 5 buckets present, n totals match |
| `test_mae_mfe_profit_factor` | PF matches manual sum(TP PnL) / abs(sum(SL PnL)) |
| `test_mae_mfe_verdict_negative` | verdict=EXPECTANCY_NEGATIVE when PF < 1.0 |
| `test_mae_mfe_verdict_positive` | verdict=EXPECTANCY_POSITIVE when PF >= 1.0 |
| `test_mae_mfe_bad_rows_skipped` | Bad numeric rows skipped, alert emitted |
| `test_mae_mfe_in_dashboard_state` | All 17 required keys present in dashboard state |

---

## 5. Frontend Implementation Detail

### `MaeMfePanel` in `ResearchPage.tsx`

**Bloomberg V3 Light Theme:**
- Background: `#F5F5F0`
- Card border: `#D4C5A9`
- Primary label: `#1A1A2E`
- UP/Winners: `#006B3C` (Bloomberg green)
- DOWN/Losers: `#8B0000` (Bloomberg deep red)
- Amber/neutral: `#5C4A1E`
- Data note: `#6B6B8A` italic

**Sections rendered:**
1. Data warning note (italic, always visible)
2. 6-card summary row (Status, Total Trades, Win Rate, Profit Factor, Avg Winner Hold, Avg Loser Hold)
3. Exit Excursion Proxies card (MFE/MAE stats grid) + Exit Reason Distribution with progress bars
4. Hold-Time Expectancy Table (5 buckets, color-coded PnL, optimal/dominant badges)
5. Regime / Side / Asset breakdown tables (3-column grid)
6. Verdict banner (green for POSITIVE, red for NEGATIVE)

**Empty state:** Shown when `maeMfe.status === "MISSING"`.

---

## 6. Real-Data Preview (from canonical_regime_enriched_trades_v1.csv, 731 rows)

| Metric | Value |
|--------|-------|
| Total trades | 731 |
| Win rate | 36.8% |
| Profit factor | **0.89** (EXPECTANCY_NEGATIVE) |
| Avg winner hold | 25.6s |
| Avg loser hold | 15.0s |
| MFE proxy mean | +0.116 |
| MAE proxy mean | 0.077 |
| Optimal hold bucket | 60s+ (69.2% win rate) |
| Dominant loss bucket | 0-15s (-$1.10 total PnL, 55.4% of trades) |

---

## 7. Scope Compliance

| Concern | Status |
|---------|--------|
| Runtime behavior changed? | **NO** |
| Strategy/signal changed? | **NO** |
| Risk/sizing changed? | **NO** |
| Execution/order changed? | **NO** |
| Live flags/wallet touched? | **NO** |
| `.env` or `config/` changed? | **NO** |
| Offline read-only only? | **YES** |
| Fail-soft on missing data? | **YES** |
| All 44 tests pass? | **YES** |
| Frontend build clean? | **YES — tsc + vite, 0 errors** |

---

## 8. Final Status

```
MAE_MFE_ANALYTICS_V1_IMPLEMENTATION_COMPLETE
```

All validations passed:
- Python compile: PASS
- 44 unit tests: PASS
- TypeScript build (tsc): PASS
- Vite production build: PASS (0 errors, chunk size warning pre-existing)
- Pre-commit audit: PASS

Awaiting operator commit sign-off. See `MAE_MFE_ANALYTICS_V1_PRE_COMMIT_AUDIT_001.md`.
