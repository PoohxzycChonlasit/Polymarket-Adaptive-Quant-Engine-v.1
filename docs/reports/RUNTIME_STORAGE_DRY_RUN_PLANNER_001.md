# RUNTIME STORAGE DRY-RUN PLANNER REPORT (RUNTIME_STORAGE_DRY_RUN_PLANNER_001)

This report presents the results of the dry-run storage lifecycle planner, detailing the files classified, safety shields applied, and projected storage savings.

---

## 1. Safety Shields & Exclusions Applied
The dry-run planner applied strict programmatic overrides to ensure zero risk to critical runtime data:
- **Current Day Shield:** Active log files matching the system date `2026-06-22` are classified as **`PROTECTED`** (never touched).
- **Source of Truth Shield:** All logs inside `trade_journal/` are classified as **`PROTECTED`** (kept forever).
- **Snapshot Shield:** Daily snapshots inside `phase_b_daily_snapshots/` are classified as **`PROTECTED`** (never pruned).
- **System Security Shield:** All ownership directories and standard configuration files (`.env`, `config/`) are locked and **`PROTECTED`**.
- **Source Code Shield:** All Python, shell, and metadata configuration files are globally locked and **`PROTECTED`**.

---

## 2. Aggregated Storage Projections

- **Total Files Inspected:** 519
- **Total Initial Footprint:** **`38.86 GB (41,726,550,604 bytes)`**
- **Total Reclaimable Space:** **`37.17 GB (39,912,430,582 bytes)`** (**95.7%** of inspected space)
- **Post-Cleanup Estimated Footprint:** **`1.69 GB (1,814,120,022 bytes)`**

### Savings Breakdown
1. **Reclaimable by Deletion:** **`28.85 GB (30,980,756,108 bytes)`** (Exceeded retention logs in `decision_log/`, `market_snapshots/`, and `scratch/`).
2. **Reclaimable by Compression:** **`2.68 GB (2,880,821,482 bytes)`** (Zstd/Gzip compression on rollover targets).
3. **Reclaimable by Archiving:** **`5.64 GB (6,050,852,992 bytes)`** (Parquet columnar conversion on `research_log/` files aged `> 7 days`).

---

## 3. Top 20 Cleanup Candidate Files

These represent the largest individual files identified by the dry-run planner for pruning or archiving:

| Rank | File Path | Action | Size (MB) | Reason |
| :--- | :--- | :--- | :---: | :--- |
| 1 | `runtime\quant_data\decision_log\2026-05-25.jsonl` | **DELETE** | 1,084.84 | decision_log_retention_exceeded_28_days |
| 2 | `scratch\decision_log_validation_root\2026-05-25.jsonl` | **DELETE** | 1,084.84 | decision_log_retention_exceeded_28_days |
| 3 | `runtime\quant_data\decision_log\2026-05-22.jsonl` | **DELETE** | 814.18 | decision_log_retention_exceeded_31_days |
| 4 | `scratch\decision_log_validation_root\2026-05-22.jsonl` | **DELETE** | 814.18 | decision_log_retention_exceeded_31_days |
| 5 | `runtime\quant_data\decision_log\2026-05-23.jsonl` | **DELETE** | 718.03 | decision_log_retention_exceeded_30_days |
| 6 | `scratch\decision_log_validation_root\2026-05-23.jsonl` | **DELETE** | 718.03 | decision_log_retention_exceeded_30_days |
| 7 | `runtime\quant_data\decision_log\2026-05-21.jsonl` | **DELETE** | 665.62 | decision_log_retention_exceeded_32_days |
| 8 | `scratch\decision_log_validation_root\2026-05-21.jsonl` | **DELETE** | 665.62 | decision_log_retention_exceeded_32_days |
| 9 | `runtime\quant_data\decision_log\2026-05-28.jsonl` | **DELETE** | 621.27 | decision_log_retention_exceeded_25_days |
| 10 | `scratch\decision_log_validation_root\2026-05-28.jsonl` | **DELETE** | 621.27 | decision_log_retention_exceeded_25_days |
| 11 | `runtime\quant_data\research_log\2026-05-25.jsonl` | **ARCHIVE** | 600.52 | research_log_parquet_archive_exceeded_28_days |
| 12 | `runtime\quant_data\decision_log\2026-06-01.jsonl` | **DELETE** | 495.61 | decision_log_retention_exceeded_21_days |
| 13 | `scratch\decision_log_validation_root\2026-06-01.jsonl` | **DELETE** | 495.61 | decision_log_retention_exceeded_21_days |
| 14 | `runtime\quant_data\decision_log\2026-05-31.jsonl` | **DELETE** | 469.96 | decision_log_retention_exceeded_22_days |
| 15 | `scratch\decision_log_validation_root\2026-05-31.jsonl` | **DELETE** | 469.96 | decision_log_retention_exceeded_22_days |
| 16 | `runtime\quant_data\decision_log\2026-06-08.jsonl` | **DELETE** | 462.57 | decision_log_retention_exceeded_14_days |
| 17 | `scratch\decision_log_validation_root\2026-06-08.jsonl` | **DELETE** | 462.57 | decision_log_retention_exceeded_14_days |
| 18 | `runtime\quant_data\research_log\2026-05-22.jsonl` | **ARCHIVE** | 452.01 | research_log_parquet_archive_exceeded_31_days |
| 19 | `runtime\quant_data\decision_log\2026-06-13.jsonl` | **DELETE** | 446.03 | decision_log_retention_exceeded_9_days |
| 20 | `scratch\decision_log_validation_root\2026-06-13.jsonl` | **DELETE** | 446.03 | decision_log_retention_exceeded_9_days |

---

## 4. Final Verdict

All target classifications and safety shields were verified programmatically. The dry-run manifest has been output to `runtime/storage_dry_run_manifest_001.json`.

> [!IMPORTANT]
> **VERDICT: READY_FOR_MANUAL_STORAGE_CLEANUP**
