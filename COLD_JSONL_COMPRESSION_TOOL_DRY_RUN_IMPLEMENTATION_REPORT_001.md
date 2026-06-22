# COLD_JSONL_COMPRESSION_TOOL_DRY_RUN_IMPLEMENTATION_REPORT_001

## Final Verdict

COLD_JSONL_COMPRESSION_DRY_RUN_PASS

## Scope

Implemented a safe dry-run-first cold JSONL compression utility:

```text
tools/runtime_storage_compressor.py
```

Added focused tests:

```text
tests/test_runtime_storage_compressor.py
```

No real compression was run. No files were deleted, moved, compressed, or restored.

## Implemented CLI

Supported modes:

```text
--dry-run
--compress
--restore
```

Supported options:

```text
--age-days
--algorithm gzip|zstd
--runtime-root
--manifest-root
```

Implemented behavior:

- `--dry-run` scans and writes a dry-run manifest.
- `--compress` is a safe stub and exits with parser error.
- `--restore` is a safe stub and exits with parser error.

## Target Folders

Only these runtime folders are eligible:

```text
runtime/quant_data/decision_log/
runtime/quant_data/research_log/
runtime/quant_data/risk_log/
runtime/quant_data/market_snapshots/
```

## Protected / Excluded Areas

Protected folders:

```text
runtime/quant_data/trade_journal/
runtime/quant_data/reports/phase_b_daily_snapshots/
runtime/ownership/
scratch/
.env
source code folders
```

Dry-run scanner also excludes:

- Current UTC day.
- Non-`.jsonl` files.
- Already compressed files: `.gz`, `.gzip`, `.zst`, `.zstd`.
- Files outside the approved target folders.
- Files younger than `--age-days`.

## Estimation Safety

Initial exact gzip estimation over real runtime files timed out because some JSONL files are very large, up to approximately 1.1GB.

Fix implemented:

- Files up to `8 MiB` use exact compression estimation.
- Larger files use bounded sampling from head, middle, and tail regions.
- Manifest records `estimate_method` as `exact`, `sampled`, or fallback variant.

This preserves dry-run safety and keeps the scan bounded.

## Real Dry-Run Result

Command:

```powershell
python tools/runtime_storage_compressor.py --dry-run --age-days 7 --algorithm gzip
```

Result:

```text
Runtime storage compression dry-run
algorithm: gzip
age_days: 7
candidate_count: 143
exclusion_count: 231
total_expected_reclaim_bytes: 24223376544
manifest: runtime\storage_manifests\dry_run\compression_dry_run_manifest_001.json
```

Manifest path:

```text
runtime/storage_manifests/dry_run/compression_dry_run_manifest_001.json
```

Summary:

```text
candidate_count: 143
exclusion_count: 231
total_original_size_bytes: 25,614,079,816
total_estimated_compressed_size_bytes: 1,390,703,272
total_expected_reclaim_bytes: 24,223,376,544
top_20_candidates_by_size: 20
```

Candidate folder distribution:

```text
decision_log: 37
market_snapshots: 37
research_log: 32
risk_log: 37
```

Exclusion reason distribution:

```text
current_utc_day: 4
outside_target_folders: 156
protected_folder: 47
younger_than_age_days: 24
```

Largest candidate:

```text
runtime/quant_data/decision_log/2026-05-25.jsonl
original_size_bytes: 1,137,536,390
estimated_compressed_size_bytes: 66,173,747
estimated_savings_bytes: 1,071,362,643
estimate_method: sampled
```

## Validation

Command:

```powershell
python -m py_compile tools/runtime_storage_compressor.py
```

Result:

```text
passed
```

Command:

```powershell
python -m pytest tests/test_runtime_storage_compressor.py -q
```

Result:

```text
8 passed
```

Command:

```powershell
git diff --check
```

Result:

```text
passed
```

## Safety Confirmation

Real compression run: No

Delete files: No

Move files: No

Restore files: No

Runtime data modified: dry-run manifest only

Runtime restarted: No

Strategy changed: No

EV changed: No

Risk changed: No

Sizing changed: No

Execution changed: No

`.env` edited: No

Commit: No

Push: No
