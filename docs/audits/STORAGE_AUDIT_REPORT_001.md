# STORAGE AUDIT REPORT (STORAGE_AUDIT_REPORT_001)

This report presents a storage growth and footprint audit of the `runtime/` directory inside the repository, identifying key drivers, risks, and retention policies.

---

## 1. Directory and File Footprints (Audit Output)

### A. Top 20 Largest Directories in `runtime/`
1. **`runtime`** | **29,451.2930 MB (28.76 GB)** (Total Folder Size)
2. **`runtime\quant_data`** | **28,251.9645 MB (27.59 GB)**
3. **`runtime\quant_data\decision_log`** | **12,553.9212 MB (12.26 GB)**
4. **`runtime\quant_data\research_log`** | **6,855.9093 MB (6.70 GB)**
5. **`runtime\quant_data\market_snapshots`** | **4,144.4933 MB (4.05 GB)**
6. **`runtime\quant_data\risk_log`** | **2,539.5657 MB (2.48 GB)**
7. **`runtime\quant_data\orderbook_lineage`** | **945.9986 MB (946.00 MB)**
8. **`runtime\quant_data\system_health`** | **914.9415 MB (914.94 MB)**
9. **`runtime\quant_data\execution_log`** | **267.7222 MB (267.72 MB)**
10. **`runtime\realtime_logs`** | **204.3095 MB (204.31 MB)**
11. **`runtime\realtime_logs\2026-05-25`** | **18.1245 MB**
12. **`runtime\realtime_logs\2026-05-22`** | **13.5354 MB**
13. **`runtime\quant_data\trade_journal`** | **12.3301 MB**
14. **`runtime\realtime_logs\2026-05-23`** | **11.9147 MB**
15. **`runtime\realtime_logs\2026-05-21`** | **11.3742 MB**
16. **`runtime\ui_validation`** | **10.4770 MB**
17. **`runtime\realtime_logs\2026-05-28`** | **10.1942 MB**
18. **`runtime\quant_data\signal_filter_shadow`** | **8.3985 MB**
19. **`runtime\realtime_logs\2026-06-01`** | **7.7268 MB**
20. **`runtime\realtime_logs\2026-05-31`** | **7.3582 MB**

---

### B. Top 50 Largest Files in `runtime/`
1. `runtime\quant_data\decision_log\2026-05-25.jsonl` | **1,084.8392 MB (1.08 GB)**
2. `runtime\quant_data\decision_log\2026-05-22.jsonl` | **814.1788 MB**
3. `runtime\quant_data\decision_log\2026-05-23.jsonl` | **718.0335 MB**
4. `runtime\quant_data\decision_log\2026-05-21.jsonl` | **665.6224 MB**
5. `runtime\quant_data\decision_log\2026-05-28.jsonl` | **621.2670 MB**
6. `runtime\quant_data\research_log\2026-05-25.jsonl` | **600.5169 MB**
7. `runtime\quant_data\decision_log\2026-06-01.jsonl` | **495.6150 MB**
8. `runtime\quant_data\decision_log\2026-05-31.jsonl` | **469.9617 MB**
9. `runtime\paper_harvest_20260523_085423.out.log` | **464.8817 MB**
10. `runtime\quant_data\decision_log\2026-06-08.jsonl` | **462.5672 MB**
11. `runtime\paper_harvest_stdout.txt` | **458.0149 MB**
12. `runtime\quant_data\research_log\2026-05-22.jsonl` | **452.0057 MB**
13. `runtime\quant_data\decision_log\2026-06-13.jsonl` | **446.0315 MB**
14. `runtime\quant_data\decision_log\2026-06-07.jsonl` | **444.0998 MB**
15. `runtime\quant_data\decision_log\2026-06-10.jsonl` | **438.6317 MB**
16. `runtime\quant_data\decision_log\2026-06-14.jsonl` | **418.4659 MB**
17. `runtime\quant_data\decision_log\2026-06-11.jsonl` | **416.9155 MB**
18. `runtime\quant_data\decision_log\2026-06-02.jsonl` | **416.5447 MB**
19. `runtime\quant_data\decision_log\2026-06-09.jsonl` | **415.8038 MB**
20. `runtime\quant_data\decision_log\2026-05-26.jsonl` | **406.5979 MB**
21. `runtime\quant_data\decision_log\2026-06-12.jsonl` | **397.5534 MB**
22. `runtime\quant_data\research_log\2026-05-23.jsonl` | **395.5877 MB**
23. `runtime\quant_data\decision_log\2026-05-24.jsonl` | **393.6429 MB**
24. `runtime\quant_data\research_log\2026-05-21.jsonl` | **378.1987 MB**
25. `runtime\quant_data\decision_log\2026-05-27.jsonl` | **367.2079 MB**
26. `runtime\quant_data\market_snapshots\2026-05-25.jsonl` | **345.4639 MB**
27. `runtime\quant_data\research_log\2026-05-28.jsonl` | **339.8150 MB**
28. `runtime\quant_data\decision_log\2026-05-30.jsonl` | **332.3353 MB**
29. `runtime\quant_data\decision_log\2026-06-16.jsonl` | **327.3761 MB**
30. `runtime\quant_data\decision_log\2026-06-06.jsonl` | **323.9409 MB**
31. `runtime\quant_data\decision_log\2026-06-05.jsonl` | **297.1039 MB**
32. `runtime\quant_data\decision_log\2026-05-29.jsonl` | **284.6319 MB**
33. `runtime\quant_data\research_log\2026-06-01.jsonl` | **263.5938 MB**
34. `runtime\quant_data\market_snapshots\2026-05-22.jsonl` | **252.6542 MB**
35. `runtime\quant_data\research_log\2026-05-31.jsonl` | **251.1045 MB**
36. `runtime\quant_data\research_log\2026-06-08.jsonl` | **245.8746 MB**
37. `runtime\quant_data\research_log\2026-06-13.jsonl` | **237.3685 MB**
38. `runtime\quant_data\research_log\2026-06-07.jsonl` | **236.5520 MB**
39. `runtime\quant_data\research_log\2026-06-10.jsonl` | **233.2119 MB**
40. `runtime\quant_data\research_log\2026-05-30.jsonl` | **230.2250 MB**
41. `runtime\quant_data\market_snapshots\2026-05-23.jsonl` | **225.6897 MB**
42. `runtime\quant_data\market_snapshots\2026-05-21.jsonl` | **224.6848 MB**
43. `runtime\quant_data\research_log\2026-05-26.jsonl` | **223.1667 MB**
44. `runtime\quant_data\decision_log\2026-06-15.jsonl` | **222.9812 MB**
45. `runtime\quant_data\research_log\2026-06-14.jsonl` | **222.6454 MB**
46. `runtime\quant_data\research_log\2026-06-02.jsonl` | **221.7321 MB**
47. `runtime\quant_data\research_log\2026-06-11.jsonl` | **221.6614 MB**
48. `runtime\quant_data\research_log\2026-06-09.jsonl` | **221.2524 MB**
49. `runtime\quant_data\research_log\2026-05-24.jsonl` | **216.7685 MB**
50. `runtime\quant_data\research_log\2026-06-12.jsonl` | **212.1396 MB**

---

## 2. Growth Drivers & Storage Projection

- **Average Daily Growth Rate:**
  The audited logs span approximately 30 days (from late May to mid-June).
  $$\text{Daily Growth Rate} = \frac{28,760 \text{ MB}}{30 \text{ days}} \approx 958.67 \text{ MB/day}$$
- **Key Storage Drivers:**
  1. **`decision_log`:** Generates ~410 MB/day. It records verbose model inferences, input feature vectors, and candidate scans on every loop tick.
  2. **`research_log`:** Generates ~220 MB/day. It dumps model-training features andCOUNTERFACTUAL backtest parameters.
  3. **`market_snapshots`:** Generates ~138 MB/day. Verbose CLOB book states (bids/asks/depths) at each scan step.
  4. **`stdout/harvest logs`:** Legacy text files like `paper_harvest_stdout.txt` (~480 MB) and `validation_extended_run.log` (~24 MB) accumulate raw prints due to console handlers lacking size limits.
- **Projected 1-Year Storage Growth:**
  Without any optimization or compression layer, the projected growth is:
  $$958.67 \text{ MB/day} \times 365 \text{ days} = 349,914 \text{ MB} \approx \mathbf{341.7 \text{ GB / year}}$$
  *Risk:* VPS instances usually have SSD quotas between 50 GB and 100 GB. Disk exhaustion would cause immediate scan loop crashes, log writing PermissionErrors, and database write lockouts.

---

## 3. Recommended Retention Policy

To manage this footprint, we propose the following lifecycle policies:

| Dataset Category | Directory | Recommended Retention | Action at Expiry |
| :--- | :--- | :--- | :--- |
| **Trade Journals** | `trade_journal/` | **Keep Forever** | None (Source of Truth) |
| **System Health** | `system_health/` | **30 Days** | Delete |
| **Decision Logs** | `decision_log/` | **7 Days** | Archive & Compress |
| **Research Logs** | `research_log/` | **7 Days** | Move to Cold Storage (Prune) |
| **Market Snapshots** | `market_snapshots/` | **3 Days** | Delete |
| **Realtime Console Logs**| `realtime_logs/` | **14 Days** | Delete |
| **UI/Staged validation** | `ui_validation/` | **1 Day** | Delete |

---

## 4. Future Architecture Recommendation

Flat, uncompressed JSONL is highly redundant because field keys (e.g. `"timestamp_utc"`, `"candidate_trace_id"`) are repeated on every line. We recommend introducing:

1. **Compression Layer (Zstandard / Gzip):**
   - Implement post-rollover compression for closed daily log files.
   - Text logs compress by `> 85-90%`. This would reduce the 1-year footprint from **341.7 GB** to **~34.1 GB**.
2. **DuckDB / Parquet for Research Log:**
   - Instead of JSONL, save research logs in compressed **Parquet** files. Parquet's columnar storage is native for Pandas, reduces size by up to `90%` over JSON, and speeds up analytical lookups.
3. **SQLite for Trade State Tracking:**
   - Move active position tracking and system health events from flat files to a lightweight **SQLite** database to guarantee ACID transactions and prevent state file corruption during mid-epoch restarts.
