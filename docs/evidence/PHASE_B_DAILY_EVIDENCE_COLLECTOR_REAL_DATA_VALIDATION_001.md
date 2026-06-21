# Real Data Validation Report: Phase B Daily Evidence Collector
**ID**: PHASE_B_DAILY_EVIDENCE_COLLECTOR_REAL_DATA_VALIDATION_001  
**Status**: REAL_DATA_COLLECTOR_PASS  

## 1. Execution Command & Files Created
* **Command Executed**:
  `python tools/phase_b_daily_evidence_collector.py --shadow-root runtime/quant_data/signal_filter_shadow_phase_b --trade-journal-root runtime/quant_data/trade_journal --system-health-root runtime/quant_data/system_health --output-dir scratch/phase_b_daily_evidence_real/output --date 2026-06-21 --rolling-days 7`
* **Output Files Generated**:
  - [phase_b_daily_evidence_2026-06-21.json](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/scratch/phase_b_daily_evidence_real/output/phase_b_daily_evidence_2026-06-21.json)
  - [phase_b_daily_evidence_2026-06-21.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/scratch/phase_b_daily_evidence_real/output/phase_b_daily_evidence_2026-06-21.md)

---

## 2. Inspected Filter Metrics
All active Phase B filters successfully completed logic processing on 2026-06-21 real telemetry data:

| Filter | Candidates Seen | Closed Joined | Pass Rate | Realized PnL | Rejected PnL | Profit Factor | Winrate | Max DD | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `block_btc_shadow` | 20 | 3 | 25.0% | $0.0005 | $0.0000 | UNDERPOWERED | 33.3% | $0.02 | **NOT_READY** |
| `block_normal_vol_shadow` | 20 | 3 | 0.0% | $0.0000 | $0.0005 | UNDERPOWERED | 0.0% | $0.00 | **NOT_READY** |
| `combined_broad_shadow` | 20 | 3 | 25.0% | $0.0005 | $0.0000 | UNDERPOWERED | 33.3% | $0.02 | **NOT_READY** |
| `combined_conservative_shadow` | 20 | 3 | 25.0% | $0.0005 | $0.0000 | UNDERPOWERED | 33.3% | $0.02 | **NOT_READY** |

*Note: Since Phase B just started running today, the low calendar days observed (1) and joined trades count (3) correctly keep all filters in the `NOT_READY` state, exactly as designed.*

---

## 3. Schema Health Checks
* **Required Keys**: All 20 parsed telemetry lines for each filter were 100% schema complete.
* **Schema Complete Rows**: 20 rows complete across all filters.
* **Schema Incomplete Rows**: 0 rows incomplete.
* **Telemetry Exception Count**: 0.

---

## 4. Runtime Health Checks
* **Active Run ID**: `20260621T135117Z_28788_c56985cf`
* **Active PID**: `unknown` (heartbeat owner PID)
* **Heartbeat Fresh**: `True` (heartbeat was logged within the last 300 seconds)
* **Duplicate Runtime Status**: `False` (no competing runs detected in log folder today)
* **Total Closed Trades**: 305

---

## 5. Git Status
* `git diff --check`: **PASS** (No whitespace errors).
* `git diff --cached --name-only`: **PASS** (No changes staged).

---

## 6. Final Verdict

```text
REAL_DATA_COLLECTOR_PASS
```
