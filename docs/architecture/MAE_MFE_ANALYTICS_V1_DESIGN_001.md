# MAE/MFE Analytics V1 — Design Document

**ID:** MAE_MFE_ANALYTICS_V1_DESIGN_001
**Date:** 2026-06-23
**Status:** DESIGN ONLY — DO NOT IMPLEMENT
**Authored by:** Antigravity (DESIGN phase)

---

## 1. Purpose

Determine whether entries, exits, TP/SL levels, and holding periods are destroying
expectancy by surfacing objective evidence from completed-trade research exports.

The goal is **operator-readable intelligence**, not runtime control.

---

## 2. Scope Boundaries

| Permitted | Not Permitted |
|-----------|---------------|
| Read `canonical_regime_enriched_trades_v1.csv` | Modify strategy or EV logic |
| Read `replay_report_*.json` | Add runtime API endpoints |
| Add `mae_mfe_analytics` namespace to `dashboard_state.json` | Change sizing, risk, execution |
| Add `MaeMfeAnalytics` TypeScript type | Modify `.env` |
| Add `MaeMfePanel` UI component | Commit or push |
| Add unit tests | Create new analyzers |

---

## 3. Research Questions Answered

| # | Question | Data Source |
|---|----------|-------------|
| Q1 | Average PnL proxy for winners (MFE proxy) | `pnl_usdc` for WIN rows |
| Q2 | Average PnL proxy for losers (MAE proxy) | `pnl_usdc` for LOSS rows |
| Q3 | Exit price move for winners (MFE price proxy) | `exit_price - entry_price` for TP rows |
| Q4 | Exit price move for losers (MAE price proxy) | `entry_price - exit_price` for SL rows |
| Q5 | Is TP harvesting too early? | Hold-time bucket win-rate trend (positive slope = longer is better) |
| Q6 | Is SL too wide or too narrow? | SL price move distribution vs TP price move |
| Q7 | What is expectancy by hold duration? | `hold_seconds` bucketed PnL and win-rate |
| Q8 | What is the optimal hold-time bucket? | Highest PF bucket from hold-time table |
| Q9 | Profit factor (TP total / |SL| total) | Sum aggregation from CSV |
| Q10 | Exit reason distribution | `exit_reason` Counter |

---

## 4. Data Availability Audit

### 4.1 Primary Source

**`runtime/research_exports/canonical_regime_enriched_trades_v1.csv`**

- 731 rows (all canonical_retained_flag = true)
- Columns available for this analytics module:

| Column | Use |
|--------|-----|
| `hold_seconds` | Hold-time bucketing |
| `entry_price` | MAE/MFE price proxy |
| `exit_price` | MAE/MFE price proxy |
| `pnl_usdc` | PnL distributions |
| `exit_reason` | TP vs SL classification |
| `outcome_win_loss` | Winner/Loser segmentation |
| `market_regime` | Cross-segment breakdown |
| `side` | YES/NO segmentation |
| `asset` | BTC/ETH segmentation |
| `canonical_entry_lifecycle_phase` | Lifecycle context |

### 4.2 MAE/MFE Field Status

> **IMPORTANT:** True tick-level MAE/MFE (intra-trade min/max price during hold) are NOT
> recorded in the current JSONL schema. The QUANT_DATA schema does not emit
> `max_adverse_excursion` or `max_favorable_excursion` fields.

This design uses **entry-to-exit price movement** as a proxy:

- **MFE proxy (winner):** `exit_price - entry_price` (TP trades; price moved favorably)
- **MAE proxy (loser):** `entry_price - exit_price` (SL trades; price moved adversely)

These are **terminal excursion proxies only**, not intra-trade min/max. The UI must
label them as "Exit Excursion Proxy" to avoid misleading the operator.

### 4.3 Baseline Statistics from Current Dataset

| Metric | Value |
|--------|-------|
| Total trades | 731 |
| Winners (TP) | 269 (36.7%) |
| Losers (SL/forced) | 462 (63.2%) |
| Win rate | 36.8% |
| Avg winner PnL | +$0.01171 |
| Avg loser PnL | -$0.00765 |
| Avg winner hold | 25.6s |
| Avg loser hold | 15.0s |
| Profit factor | **0.89** (net negative) |
| Avg entry price | $0.528 |
| TP price move proxy (mean) | +$0.116 |
| SL price move proxy (mean) | -$0.077 |

### 4.4 Hold-Time Bucket Expectancy (Key Finding)

| Bucket | n | Win Rate | Mean PnL | Total PnL |
|--------|---|----------|----------|-----------|
| 0-15s | 405 | **26.7%** | -$0.00272 | **-$1.100** |
| 15-30s | 189 | 42.9% | +$0.00003 | +$0.006 |
| 30-45s | 73 | 52.1% | +$0.00276 | +$0.201 |
| 45-60s | 38 | 65.8% | +$0.00504 | +$0.192 |
| 60s+ | 26 | **69.2%** | +$0.01265 | **+$0.329** |

> Key finding: Win rate and expectancy improve monotonically with hold time.
> The 0-15s bucket accounts for 55.4% of trades and -$1.10 total PnL.
> This is strong evidence that early stop-loss exits are destroying expectancy.

---

## 5. Namespace Schema: `mae_mfe_analytics`

Add to `research_analytics` in `dashboard_state.json`:

```json
"mae_mfe_analytics": {
  "status": "MISSING | PARTIAL | OK",
  "generated_at": "<ISO-Z>",
  "data_warning": "Exit excursion proxies only. No intra-trade tick MAE/MFE recorded.",
  "source_csv": "runtime/research_exports/canonical_regime_enriched_trades_v1.csv",
  "total_trades": 0,
  "summary": {
    "win_rate": null,
    "profit_factor": null,
    "avg_winner_pnl": null,
    "avg_loser_pnl": null,
    "avg_winner_hold_s": null,
    "avg_loser_hold_s": null,
    "avg_mfe_proxy": null,
    "avg_mae_proxy": null,
    "tp_count": 0,
    "sl_count": 0,
    "forced_exit_count": 0
  },
  "exit_reason_distribution": [
    { "reason": "take_profit_target_reached", "count": 0, "share": 0.0 },
    { "reason": "stop_loss",                  "count": 0, "share": 0.0 },
    { "reason": "stop_loss_hit",              "count": 0, "share": 0.0 },
    { "reason": "forced_exit",               "count": 0, "share": 0.0 }
  ],
  "hold_time_buckets": [
    { "bucket": "0-15s", "n": 0, "win_rate": null, "mean_pnl": null, "total_pnl": null, "tp_count": 0, "sl_count": 0 }
  ],
  "mfe_proxy": {
    "label": "Exit Price - Entry Price (TP trades only)",
    "winner_mean": null, "winner_median": null, "winner_max": null,
    "winner_min": null, "winner_p25": null, "winner_p75": null
  },
  "mae_proxy": {
    "label": "Entry Price - Exit Price (SL trades only)",
    "loser_mean": null, "loser_median": null, "loser_max": null,
    "loser_min": null, "loser_p25": null, "loser_p75": null
  },
  "regime_breakdown": [],
  "side_breakdown": [],
  "asset_breakdown": [],
  "optimal_hold_bucket": null,
  "dominant_loss_bucket": null,
  "verdict": null,
  "verdict_reason": null,
  "alerts": []
}
```

---

## 6. Computed Metrics Logic

### 6.1 Classification

```python
tp_rows   = [r for r in rows if r["exit_reason"] == "take_profit_target_reached"]
sl_rows   = [r for r in rows if "stop_loss" in r["exit_reason"]]
win_rows  = [r for r in rows if r["outcome_win_loss"] == "WIN"]
loss_rows = [r for r in rows if r["outcome_win_loss"] == "LOSS"]
```

### 6.2 MFE Proxy (TP trades)

```python
mfe_values = [float(r["exit_price"]) - float(r["entry_price"]) for r in tp_rows]
# Percentiles via statistics.quantiles(mfe_values, n=4)
```

### 6.3 MAE Proxy (SL trades)

```python
mae_values = [float(r["entry_price"]) - float(r["exit_price"]) for r in sl_rows]
# Absolute adverse move (always positive for SL trades)
```

### 6.4 Profit Factor

```python
total_tp_pnl = sum(float(r["pnl_usdc"]) for r in tp_rows)
total_sl_pnl = abs(sum(float(r["pnl_usdc"]) for r in sl_rows))
profit_factor = total_tp_pnl / total_sl_pnl if total_sl_pnl > 0 else None
```

### 6.5 Hold-Time Buckets

```python
BUCKETS = [("0-15s", 0, 15), ("15-30s", 15, 30), ("30-45s", 30, 45),
           ("45-60s", 45, 60), ("60s+", 60, float("inf"))]
```

### 6.6 Verdict Logic

```python
if profit_factor is None or profit_factor < 1.0:
    verdict = "EXPECTANCY_NEGATIVE"
elif profit_factor >= 1.0:
    verdict = "EXPECTANCY_POSITIVE"
```

### 6.7 Fail-Soft Rules

- CSV missing -> `status: "MISSING"`, all fields null, no crash
- CSV < 10 rows -> `status: "PARTIAL"`
- Unparseable row fields -> skip row, count as parse_error
- Percentile: use `statistics.quantiles` (Python >= 3.8)

---

## 7. Backend Changes: `tools/dashboard_state_aggregator.py`

### 7.1 `_empty_state` addition

Add inside `"research_analytics"` dict, after `"regime_analytics"`:

```python
"mae_mfe_analytics": {
    "status": "MISSING",
    "generated_at": _iso_z(now),
    "data_warning": "Exit excursion proxies only. No intra-trade tick MAE/MFE recorded.",
    "source_csv": "",
    "total_trades": 0,
    "summary": {
        "win_rate": None, "profit_factor": None, "avg_winner_pnl": None,
        "avg_loser_pnl": None, "avg_winner_hold_s": None, "avg_loser_hold_s": None,
        "avg_mfe_proxy": None, "avg_mae_proxy": None,
        "tp_count": 0, "sl_count": 0, "forced_exit_count": 0,
    },
    "exit_reason_distribution": [],
    "hold_time_buckets": [],
    "mfe_proxy": {
        "label": "Exit Price - Entry Price (TP trades)",
        "winner_mean": None, "winner_median": None, "winner_max": None,
        "winner_min": None, "winner_p25": None, "winner_p75": None,
    },
    "mae_proxy": {
        "label": "Entry Price - Exit Price (SL trades)",
        "loser_mean": None, "loser_median": None, "loser_max": None,
        "loser_min": None, "loser_p25": None, "loser_p75": None,
    },
    "regime_breakdown": [],
    "side_breakdown": [],
    "asset_breakdown": [],
    "optimal_hold_bucket": None,
    "dominant_loss_bucket": None,
    "verdict": None,
    "verdict_reason": None,
    "alerts": [],
},
```

### 7.2 New function `_extract_mae_mfe_analytics(root_dir: Path) -> dict`

**Location:** After `_extract_regime_analytics`

**Reads:** `root_dir / "research_exports" / "canonical_regime_enriched_trades_v1.csv"`

**Steps:**
1. Try open CSV; on failure return empty state with `status: "MISSING"`
2. Parse all rows; skip rows with bad `hold_seconds` or `pnl_usdc`
3. Classify into `tp_rows`, `sl_rows`, `win_rows`, `loss_rows`
4. Compute `summary`, `mfe_proxy`, `mae_proxy`
5. Compute `hold_time_buckets` (5 standard buckets)
6. Compute `exit_reason_distribution`
7. Compute `regime_breakdown`, `side_breakdown`, `asset_breakdown`
8. Derive `optimal_hold_bucket` and `dominant_loss_bucket`
9. Set `verdict` and `verdict_reason`
10. Set `status: "OK"` if total trades >= 10, else `"PARTIAL"`

Uses `csv.DictReader` (already imported by aggregator).

### 7.3 Wire into `_apply_research_reports`

```python
state["research_analytics"]["mae_mfe_analytics"] = _extract_mae_mfe_analytics(root)
```

---

## 8. TypeScript Type Changes: `dashboard/src/types/dashboard.ts`

```typescript
export interface MfeMaeProxy {
  label: string;
  winner_mean: number | null;
  winner_median: number | null;
  winner_max: number | null;
  winner_min: number | null;
  winner_p25: number | null;
  winner_p75: number | null;
}

export interface HoldTimeBucket {
  bucket: string;
  n: number;
  win_rate: number | null;
  mean_pnl: number | null;
  total_pnl: number | null;
  tp_count: number;
  sl_count: number;
}

export interface ExitReasonRow {
  reason: string;
  count: number;
  share: number;
}

export interface MaeMfeSummary {
  win_rate: number | null;
  profit_factor: number | null;
  avg_winner_pnl: number | null;
  avg_loser_pnl: number | null;
  avg_winner_hold_s: number | null;
  avg_loser_hold_s: number | null;
  avg_mfe_proxy: number | null;
  avg_mae_proxy: number | null;
  tp_count: number;
  sl_count: number;
  forced_exit_count: number;
}

export interface BreakdownRow {
  regime?: string;
  side?: string;
  asset?: string;
  n: number;
  win_rate: number | null;
  mean_pnl: number | null;
  avg_hold_s: number | null;
  tp_count?: number;
  sl_count?: number;
}

export interface MaeMfeAnalytics {
  status: "MISSING" | "PARTIAL" | "OK";
  generated_at: string;
  data_warning: string;
  source_csv: string;
  total_trades: number;
  summary: MaeMfeSummary;
  exit_reason_distribution: ExitReasonRow[];
  hold_time_buckets: HoldTimeBucket[];
  mfe_proxy: MfeMaeProxy;
  mae_proxy: MfeMaeProxy;
  regime_breakdown: BreakdownRow[];
  side_breakdown: BreakdownRow[];
  asset_breakdown: BreakdownRow[];
  optimal_hold_bucket: string | null;
  dominant_loss_bucket: string | null;
  verdict: string | null;
  verdict_reason: string | null;
  alerts: string[];
}
```

Add to `ResearchAnalytics`:
```typescript
mae_mfe_analytics: MaeMfeAnalytics;
```

---

## 9. UI Widget Design: `dashboard/src/pages/research/ResearchPage.tsx`

### 9.1 Bloomberg V3 Light Theme

- Background: `#F5F5F0`
- Card: `#FFFFFF` with `1px solid #D4C5A9`
- Primary label: `#1A1A2E` bold
- UP accent (winners/TP): `#006B3C` (Bloomberg green)
- DOWN accent (losers/SL): `#8B0000` (Bloomberg deep red)
- Neutral: `#5C4A1E` (Bloomberg amber)
- Data note: `#6B6B8A` italic

### 9.2 Widget Layout

```
+------------------------------------------------------------------+
|  MAE/MFE ANALYTICS  [status]    [data_warning italic note]       |
+------------+------------+------------+------------+--------------+
| TOTAL      | WIN RATE   | PROFIT     | AVG WINNER | AVG LOSER    |
| TRADES     |            | FACTOR     | HOLD       | HOLD         |
|  731       |  36.8%     |  0.89 !!   |  25.6s     |  15.0s       |
+------------+------------+------------+------------+--------------+
|  HOLD TIME EXPECTANCY TABLE                                      |
|  Bucket  | n   | Win%  | Mean PnL  | Total PnL | TP  | SL      |
|  0-15s   | 405 | 26.7% | -$0.003   | -$1.100   | ... | ...     |
|  15-30s  | 189 | 42.9% | +$0.000   | +$0.006   | ... | ...     |
|  30-45s  |  73 | 52.1% | +$0.003   | +$0.201   | ... | ...     |
|  45-60s  |  38 | 65.8% | +$0.005   | +$0.192   | ... | ...     |
|  60s+    |  26 | 69.2% | +$0.013   | +$0.329   | ... | ...     |
+----------------------------------+-------------------------------+
|  EXIT EXCURSION PROXY            |  EXIT REASON DISTRIBUTION     |
|  MFE proxy (avg): +$0.116        |  TP:  269 / 36.8%             |
|  MAE proxy (avg): -$0.077        |  SL:  461 / 63.0%             |
|                                  |  FORCED: 1 / 0.1%             |
+------------------------------------------------------------------+
|  REGIME / SIDE / ASSET BREAKDOWN (mini-cards)                    |
+------------------------------------------------------------------+
|  VERDICT                                                         |
|  !! EXPECTANCY_NEGATIVE -- Profit Factor 0.89 < 1.0             |
|  Dominant loss bucket: 0-15s (-$1.10, 55.4% of all trades)      |
|  Optimal hold bucket: 60s+ (PF>1.0, 69% win rate)               |
+------------------------------------------------------------------+
```

### 9.3 Visual Rules

| Element | Rule |
|---------|------|
| Profit Factor badge | Red if < 1.0, green if >= 1.0 |
| Hold-time row color | Red for negative total_pnl, green for positive |
| Dominant loss bucket | Amber badge |
| Optimal hold bucket | Green badge |
| Data warning | Grey italic note |

### 9.4 Roadmap Badge

```tsx
{ id: "mae-mfe", label: "MAE/MFE Analytics V1", status: "in-progress" }
// -> "done" after implementation
```

---

## 10. Test Strategy

### 10.1 Unit Tests in `tests/test_dashboard_state_aggregator.py`

| Test | Assertion |
|------|-----------|
| `test_mae_mfe_missing_csv` | status: "MISSING" when CSV absent |
| `test_mae_mfe_empty_csv` | status: "PARTIAL" for 0-row CSV |
| `test_mae_mfe_minimal_csv` | Correct aggregation for synthetic 5-row CSV |
| `test_mae_mfe_win_loss_split` | tp_count + sl_count + forced ~= total_trades |
| `test_mae_mfe_hold_time_buckets` | All 5 buckets present; n sums to total |
| `test_mae_mfe_profit_factor` | Matches manual sum(TP pnl) / abs(sum(SL pnl)) |
| `test_mae_mfe_verdict_negative` | verdict = "EXPECTANCY_NEGATIVE" when PF < 1 |
| `test_mae_mfe_verdict_positive` | verdict = "EXPECTANCY_POSITIVE" when PF >= 1 |
| `test_mae_mfe_bad_rows_skipped` | Rows with null/bad hold_seconds skipped |
| `test_mae_mfe_in_dashboard_state` | build_dashboard_state() includes mae_mfe_analytics key |

### 10.2 Frontend Build

```bash
cd dashboard
npm run test:run
npm run build
```

### 10.3 Python Syntax Check

```bash
python -m py_compile tools/dashboard_state_aggregator.py
python -m pytest tests/test_dashboard_state_aggregator.py -q
```

---

## 11. Evidence Guardrails

- Offline read-only from historical research exports
- Does not authorize runtime policy changes
- Does not authorize sizing, risk, or execution changes
- Does not claim live PnL or live-trading readiness
- Does not fabricate intra-trade price paths
- `mae_mfe_analytics` is evidence context only; operator decides action

---

## 12. Open Questions

| # | Question | Default |
|---|----------|---------|
| OQ1 | Include intra-trade tick MAE/MFE in future (requires JSONL schema)? | Future Phase |
| OQ2 | regime_breakdown: use `market_regime` or also `trend_regime`? | `market_regime` only |
| OQ3 | Hold-time table: bar chart or sortable table? | Table for V1 |
| OQ4 | `forced_exit` rows: LOSS or separate? | Separate `forced_exit_count` |

---

## 13. Implementation File Targets

| File | Change |
|------|--------|
| `tools/dashboard_state_aggregator.py` | Add `_extract_mae_mfe_analytics()`, update `_empty_state`, wire in `_apply_research_reports` |
| `tests/test_dashboard_state_aggregator.py` | Add ~10 new test functions |
| `dashboard/src/types/dashboard.ts` | Add `MaeMfeAnalytics` and sub-interfaces |
| `dashboard/src/pages/research/ResearchPage.tsx` | Add `MaeMfePanel` component |
| `MAE_MFE_ANALYTICS_V1_IMPLEMENTATION_REPORT_001.md` | Created during implementation |
| `MAE_MFE_ANALYTICS_V1_PRE_COMMIT_AUDIT_001.md` | Created before commit |

---

## 14. Final Verdict

```
READY_FOR_MAE_MFE_ANALYTICS_V1_IMPLEMENTATION
```

Evidence: `canonical_regime_enriched_trades_v1.csv` contains all required fields
across 731 canonical trades. True intra-trade MAE/MFE is not available (JSONL schema
gap noted in `latest_research_state.md`) but terminal exit excursion proxies are
sufficient for V1 operator-level intelligence.

Critical insight surfaced during design: The 0-15s hold bucket represents 55.4% of all
trades and -$1.10 total PnL, while the 60s+ bucket has 69.2% win rate and +$0.33 total
PnL. This hold-time duration paradox is the dominant pattern to surface for the operator.
