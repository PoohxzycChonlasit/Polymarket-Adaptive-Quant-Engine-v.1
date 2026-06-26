# EXECUTION_SHADOW_TELEMETRY_IMPLEMENTATION_PLAN_001

* **Date:** 2026-06-21
* **Target Workspace:** `c:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
* **Status:** **`IMPLEMENTATION PLAN COMPLETE`**
* **Primary Role:** `02_CODE_ARCHITECT_AGENT` (Systems Architecture & Modularity)
* **Supporting Roles:** `03_RISK_MANAGER_AGENT` (Safety Boundaries), `08_RESEARCH_QUANT_AGENT` (Telemetry Validation)

---

## 1. Shadow Telemetry Purpose & Scope

The purpose of this document is to design the implementation plan for the passive shadow telemetry substrate. This substrate evaluates five candidate filters:
1. `block_btc_shadow`
2. `block_edge_lt_005_shadow`
3. `block_normal_vol_shadow`
4. `combined_broad_shadow`
5. `combined_conservative_shadow`

This plan strictly enforces **passive-only** execution. Under no circumstances will this shadow layer modify active order routing, sizer inputs, or risk limits.

---

## 2. Insertion Points

The shadow telemetry layer will be integrated across three core areas of the codebase:

```
                  ┌──────────────────────────────┐
                  │      REPLAY PIPELINE         │
                  │  tools/execution_paper_runtime.py
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │   EXECUTION REPLAY REPORTS   │
                  │   tools/replay_analyzer.py   │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │      VALIDATION REPORTS      │
                  │ tools/paper_evaluation_report.py
                  └──────────────────────────────┘
```

### A. Replay Pipeline
- **Target File**: [execution_paper_runtime.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/execution_paper_runtime.py)
- **Insertion**: Modify the output loop that writes closed trade journals. As each `execution_paper_close` is written, evaluate it against the five shadow filters using the nearest matched decision log event.

### B. Execution Replay Reports
- **Target File**: [replay_analyzer.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/replay_analyzer.py)
- **Insertion**: Update the aggregator section to output baseline metrics side-by-side with the five shadow filter configurations.

### C. Validation Reports
- **Target File**: [paper_evaluation_report.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/paper_evaluation_report.py)
- **Insertion**: Incorporate shadow statistics into the output JSON report (`paper_evaluation_YYYY-MM-DD.json`). Introduce a new section `shadow_filter_metrics` to log evaluation pass rates and simulated PnL.

---

## 3. Data Flow

Telemetry data flows sequentially from active decision logs to the finalized shadow metrics dashboard:

```
[ decision_log ] ──► [ Join Engine ] ◄── [ trade_journal (close) ]
                           │
                           ▼
                  [ Joined Close Event ]
                           │
                           ▼
                 [ Shadow Evaluation ]
                           │
                           ├─► block_btc_shadow
                           ├─► block_edge_lt_005_shadow
                           ├─► block_normal_vol_shadow
                           ├─► combined_broad_shadow
                           └─► combined_conservative_shadow
                           │
                           ▼
                   [ Shadow Metrics ]
                           │
                           ▼
               [ JSONL / Report Output ]
```

1. **`decision_log`**: Captures strategy inputs (`volatility_regime`, `edge`, `ev`) in real-time.
2. **Replay Join**: Uses `run_id` + `condition_id` / `ticker` + nearest timestamp to join the strategy inputs to the execution logs.
3. **`execution_paper_close`**: Dispatches the joined execution record.
4. **Shadow Evaluation**: Runs the five filters concurrently over each joined close.
5. **Shadow Metrics**: Computes simulated PnL, Win Rate, Profit Factor, Drawdown, and Loss Streaks for each filter.

---

## 4. Required Files

To implement this plan, the following files will be modified:

### Offline Phase Modifications:
- **[replay_analyzer.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/replay_analyzer.py)**: Define filter lambdas and metric collectors to calculate and print shadow metrics.
- **[paper_evaluation_report.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/paper_evaluation_report.py)**: Add shadow filter results into the daily JSON validation reports.

### Passive Runtime Modifications (Paper-only):
- **[quant_event_logger.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/quant_event_logger.py)**: Register new event schema `shadow_filter_event` to write to JSONL.
- **[trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py)**: Add a passive method `_evaluate_shadow_telemetry` that fires at the end of each decision cycle. Evaluates the candidate against all filters and emits the telemetry JSONL.

---

## 5. Telemetry Outputs

The shadow layer will output three primary telemetry formats:

### A. Raw JSONL (`runtime/quant_data/execution_paper/shadow_filters/[date].jsonl`)
Emits a structured row for every evaluated candidate signal:
```json
{
  "timestamp_utc": "2026-06-21T03:30:00Z",
  "run_id": "20260621T033000Z_9999",
  "asset": "ETH",
  "edge": 0.0825,
  "volatility_regime": "HIGH_VOL",
  "active_entry_allowed": true,
  "shadow_filter_name": "combined_conservative_shadow",
  "shadow_pass": true,
  "shadow_reject_reason": null,
  "execution_pnl_5_share_model": 0.3500
}
```

### B. Reports (`runtime/reports/shadow_evaluation_[date].json`)
Summarizes daily counts and performance metrics:
```json
{
  "date": "2026-06-21",
  "baseline_pnl": -0.85,
  "baseline_pf": 0.88,
  "filters": {
    "combined_conservative_shadow": {
      "trades_kept": 2,
      "wins": 1,
      "losses": 1,
      "net_pnl": 0.35,
      "pf": 2.14,
      "sample_class": "LOW_SAMPLE"
    }
  }
}
```

---

## 6. Migration Plan

```
[ Phase A: Offline Replay Only ]
              │
              ▼
[ Phase B: Paper Runtime Passive Telemetry ]
              │
              ▼
[ Phase C: 7-Day Shadow Observation ]
```

### Phase A: Offline Replay Only
- Implement the filters and summary tables inside the offline `tools/replay_analyzer.py` and `tools/paper_evaluation_report.py`.
- Run validation reruns over the historical Phase C dataset (730 trades) to verify that generated numbers are identical to the audit baseline.

### Phase B: Paper Runtime Passive Telemetry
- Wire the passive `_evaluate_shadow_telemetry` call site into `polymarket/trader.py` (paper execution path only).
- Verify that this tracker runs inside a `try/except` block to ensure that database, formatting, or parsing exceptions cannot crash the core trading cycles.

### Phase C: 7-Day Shadow Observation
- Deploy the passive paper runtime on VPS.
- Gather 7 continuous days of paper telemetry data. Confirm that zero active trades were blocked, and that the shadow telemetry files update daily under `runtime/quant_data/execution_paper/shadow_filters/`.

---

## 7. Rollback Plan

If telemetry issues or log write locks occur during Phase B or C:
1. **Pydantic Config Flag**: Define `SHADOW_TELEMETRY_ENABLED: bool = True` in [settings.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/config/settings.py) and map it to `.env` as `SHADOW_TELEMETRY_ENABLED`.
2. **Immediate Override**: Setting `SHADOW_TELEMETRY_ENABLED=false` in `.env` immediately bypasses the telemetry evaluation block.
3. **Fail-Soft Catch**: If any write failure or file-lock exception is raised during JSONL append, catch the exception, write a diagnostic error to the log, and disable `SHADOW_TELEMETRY_ENABLED` dynamically for the remainder of the session without crashing the system.

---

## 8. Complexity Estimation

* **Overall Complexity**: **`LOW`**
* **Rationale**:
  - The filters are defined by simple, non-stateful conditional boolean checks.
  - The offline backtest logic has already been proven in `run_filter_impact_audit.py`.
  - The runtime integration requires only an additive passive telemetry hook in `trader.py`, utilizing existing variables with zero state tracking or active order management modifications.

---

## 9. Deliverable

Create: **[EXECUTION_SHADOW_TELEMETRY_IMPLEMENTATION_PLAN_001.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/EXECUTION_SHADOW_TELEMETRY_IMPLEMENTATION_PLAN_001.md)**

---

## 10. Final Verdict

### Final Verdict: **`READY_FOR_TELEMETRY_IMPLEMENTATION`**

> [!NOTE]
> The architectural design, insertion points, data flows, and rollback plans are fully specified. 
> The system is ready to proceed to Phase A implementation.
