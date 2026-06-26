# COLD-LOG COMPRESSION UTILITY SPECIFICATION (COLD_JSONL_COMPRESSION_TOOL_DESIGN_001)

This document specifies the design for `tools/runtime_storage_compressor.py`, a safe command-line utility to compress historical flat JSONL logs and restore them in the event of an operational rollback.

---

## 1. Tool CLI & Interface Specification

The utility will support three mutually exclusive execution modes:

```bash
# Dry-run execution (Default)
python tools/runtime_storage_compressor.py --dry-run

# Physical compression run
python tools/runtime_storage_compressor.py --compress --age-days 7

# Rollback restore run
python tools/runtime_storage_compressor.py --restore --manifest runtime/storage_manifests/compression_manifest_20260622.json
```

### CLI Parameters
- `--dry-run` (flag): Scans files, calculates footprint sizes, prints proposal targets, and verifies directory locks without making filesystem writes or deletions.
- `--compress` (flag): Triggers physical compression.
- `--restore` (flag): Triggers recovery/decompression.
- `--age-days` (int, default: `7`): The minimum age in days for log file compression.
- `--algorithm` (choice: `zstd`, `gzip`, default: `zstd`): Specifies the compression module.
- `--manifest` (str): Absolute or relative path to a manifest file for the `--restore` workflow.

---

## 2. Safety Shields & Exclusions

The script will enforce hardcoded safety overrides at startup. Any path matching these criteria will be excluded from the scan:

1. **Current UTC Day Shield:** The current system date file (`YYYY-MM-DD.jsonl`) is locked to prevent collisions with active file handles.
2. **Trade Journal Shield:** Exclusion of `runtime/quant_data/trade_journal/` (reconciliation and fill journals).
3. **Daily Snapshot Shield:** Exclusion of `runtime/quant_data/reports/phase_b_daily_snapshots/`.
4. **Ownership Shield:** Exclusion of directories containing `ownership/` or matching lockfiles.
5. **Source Code & Config Shield:** Globally ignores `.py`, `.sh`, `.ini`, `.cfg`, `.json`, `.db`, `.sqlite`, and `.env` files.

---

## 3. Compression Evaluation

We evaluated two key compression algorithms:

| Metric | Gzip (`gz`) | Zstandard (`zstd`) | Recommendation |
| :--- | :--- | :--- | :--- |
| **Compression Ratio** | **~85%** (8.5:1) | **~90%** (10:1) | **Zstandard Wins** (Higher compression efficiency for raw JSON data). |
| **Compression Speed** | Medium (~25 MB/s) | High (~100 MB/s at Level 3) | **Zstandard Wins** (Lower CPU overhead during execution). |
| **Decompression Speed**| Medium (~80 MB/s) | Very High (~300+ MB/s) | **Zstandard Wins** (Crucial for fast research/replay queries). |
| **Dependency Complexity**| Standard library (`gzip`) | External package (`zstandard`) | **Gzip Wins** (No install needed). |

- **Default Recommendation:** **Zstandard (`zstd`)** will be the default algorithm due to its superior compression ratio and query decompression speeds. The utility will dynamically fall back to **Gzip (`gzip`)** if the `zstandard` module is not installed in the current python interpreter.

---

## 4. Manifest Specification

Every execution of `--compress` generates a date-stamped manifest inside `runtime/storage_manifests/`:

**Path:** `runtime/storage_manifests/compression_manifest_YYYYMMDD.json`

### JSON Schema
```json
{
  "timestamp_utc": "2026-06-22T19:27:02.123456Z",
  "compression_algorithm": "zstd",
  "age_days_threshold": 7,
  "summary": {
    "total_files_compressed": 3,
    "original_bytes_total": 2045893041,
    "compressed_bytes_total": 204589304,
    "space_saved_bytes": 1841303737,
    "savings_ratio_pct": 90.0
  },
  "records": [
    {
      "source_file": "runtime\\quant_data\\decision_log\\2026-06-14.jsonl",
      "compressed_file": "runtime\\quant_data\\decision_log\\2026-06-14.jsonl.zst",
      "original_size": 1137536390,
      "compressed_size": 113753639,
      "original_sha256": "8f4f...a342",
      "compressed_sha256": "c4d2...d193",
      "original_row_count": 38100,
      "timestamp": "2026-06-22T19:27:02Z"
    }
  ]
}
```

---

## 5. Failure Recovery & Resiliency

To prevent data corruption during power loss, filesystem failures, or disk limits, the utility implements **transient state buffering**:

```mermaid
graph TD
    A[Original Log] -->|1. Compress| B[Temp Archive .tmp.zst]
    B -->|2. Verify Integrity & Row Counts| C{Pass?}
    C -->|Yes| D[Rename to Target .jsonl.zst]
    D -->|3. Remove Source Log| E[Done]
    C -->|No| F[Delete Temp Archive & Raise Alert]
```

1. **Write to Temporary File:** The script writes compression output to a temporary file (`.jsonl.zst.tmp`). It only renames it to `.jsonl.zst` once verification checks pass.
2. **Power Loss Protection:** If the program terminates prematurely, the `.tmp` file is ignored, and the original `.jsonl` file remains completely intact.
3. **Disk Space Exhaustion Safety:** Prior to compression, the script checks if free disk space is at least $1.2 \times$ the size of the single largest target file. If not, it fails closed to prevent disk lockout.
4. **Archive Corruption Recovery:** In `--restore` mode, if a `.zst` file fails the decompression checksum, the script terminates, leaving the compressed file intact, and issues an alert.

---

## 6. Verification Pipeline

The utility performs verification before removing any source files:

1. **Row Count Validation:**
   - Decompress the temporary `.zst.tmp` in memory and count lines.
   - Verify that:
     $$\text{JSONL Line Count} = \text{Decompressed Line Count}$$
2. **Hash Validation:**
   - Calculate SHA-256 hash of the input file and record it in the manifest.
   - When running `--restore`, verify that the SHA-256 hash of the decompressed file matches the manifest value.
3. **Size Delta Reporting:**
   - Calculate and display:
     $$\text{Space Saved} = \text{Original Size} - \text{Compressed Size}$$

---

## 7. Operator Workflow & Cadence

We recommend the following operation intervals:

- **Daily (Automated cron):** A daily cron job executes at `00:05:00 UTC` with `--compress --age-days 7` to compress log files that rolled over one week ago.
- **Weekly (Manual Review):** Operator reviews `runtime/storage_manifests/` to check savings ratios and disk health.
- **Monthly (Integrity Audit):** Operator runs a verification scan across archived logs to ensure no file drift or corruption has occurred.

---

## 8. Estimated Savings Projections

Based on our `25.43 GB` flat log footprint:

- **7-Day Threshold (Active buffer kept flat, logs compressed after 7 days):**
  - Reclaims: **`17.69 GB`** immediately.
- **30-Day Threshold:**
  - Reclaims: **`14.20 GB`** immediately.
- **90-Day Threshold:**
  - Reclaims: **`8.50 GB`** immediately.

---

## 9. Final Verdict

The proposed design satisfies all safety requirements and provides a robust backup-and-restore compression layer.

> [!IMPORTANT]
> **VERDICT: READY_FOR_COMPRESSION_DRY_RUN_IMPLEMENTATION**
