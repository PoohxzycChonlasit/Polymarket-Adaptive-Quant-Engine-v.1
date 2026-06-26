# SMALL_BATCH_COMPRESSION_VALIDATION_001

## Final Verdict

SMALL_BATCH_COMPRESSION_VALIDATION_PASS

## Mode

Controlled real data validation.

Compressed exactly four cold JSONL files using repeated one-file commands because the tool does not yet support a multi-file whitelist.

No decision logs were compressed. No research logs were compressed. No trade journal files were touched. No phase B daily snapshots were touched. No current UTC day files were touched.

## Runtime Context

An active paper runtime process was observed before validation:

```text
main.py --mode paper ...
```

The selected files were old cold `risk_log` files from May 2026. They were not current-day runtime files.

## Dry-Run

Command:

```powershell
python tools/runtime_storage_compressor.py --dry-run --age-days 7 --algorithm gzip
```

Result:

```text
candidate_count: 143
exclusion_count: 232
total_expected_reclaim_bytes: 24223376544
manifest: runtime\storage_manifests\dry_run\compression_dry_run_manifest_001.json
```

Selection evidence written to:

```text
runtime/storage_manifests/dry_run/small_batch_selected_candidates.json
```

## Selected Files

| File | Folder | Original bytes | Lines | Pre-compression sha256 |
|---|---|---:|---:|---|
| `runtime/quant_data/risk_log/2026-05-08.jsonl` | `risk_log` | 523,125 | 1,102 | `583b9e333bd2cdfe1e0b5b6d51df84c21c55dbf0eb9eee02a728b2bac37f53b1` |
| `runtime/quant_data/risk_log/2026-05-10.jsonl` | `risk_log` | 669,689 | 692 | `6fdb726ce8749adb52d31908195e4d077f4b8c6a8087ebb7b6b5b9dfb940c485` |
| `runtime/quant_data/risk_log/2026-05-11.jsonl` | `risk_log` | 729,625 | 828 | `7d43803f2ce5f107800ca90f279eea5952831ea1f48553ff0aeac718a7c98116` |
| `runtime/quant_data/risk_log/2026-05-09.jsonl` | `risk_log` | 804,076 | 1,268 | `7021a5061f59ee45c0ccfdaa319719cea5b2a7756bcbcd731a2236c4098a8ab5` |

Selection rules confirmed:

```text
older_than_7_days: yes
current_utc_day: no
dry_run_candidate: yes
decision_log: no
research_log: no
trade_journal: no
phase_b_daily_snapshots: no
already_validated_market_snapshot_excluded: yes
```

## Compression Commands

Because the tool cannot restrict to a selected set of four paths in one command, compression used `--one-file` repeatedly.

Commands:

```powershell
python tools/runtime_storage_compressor.py --compress --age-days 7 --algorithm gzip --max-files 1 --one-file runtime/quant_data/risk_log/2026-05-08.jsonl
python tools/runtime_storage_compressor.py --compress --age-days 7 --algorithm gzip --max-files 1 --one-file runtime/quant_data/risk_log/2026-05-10.jsonl
python tools/runtime_storage_compressor.py --compress --age-days 7 --algorithm gzip --max-files 1 --one-file runtime/quant_data/risk_log/2026-05-11.jsonl
python tools/runtime_storage_compressor.py --compress --age-days 7 --algorithm gzip --max-files 1 --one-file runtime/quant_data/risk_log/2026-05-09.jsonl
```

Each command returned:

```text
compressed_count: 1
rejected_count: 0
```

Compression command log:

```text
runtime/storage_manifests/compress/small_batch_compress_commands.json
```

Compression manifests:

```text
runtime/storage_manifests/compress/compression_manifest_20260622T142727Z.json
runtime/storage_manifests/compress/compression_manifest_20260622T142731Z.json
runtime/storage_manifests/compress/compression_manifest_20260622T142736Z.json
runtime/storage_manifests/compress/compression_manifest_20260622T142740Z.json
```

## Compression Verification

Verification file:

```text
runtime/storage_manifests/compress/small_batch_compress_verification.json
```

| Source | Archive | Archive bytes | Source removed | Sha256 parity | Line parity | Temp files |
|---|---|---:|---|---|---|---|
| `2026-05-08.jsonl` | `2026-05-08.jsonl.gz` | 19,329 | Yes | Pass | Pass | None |
| `2026-05-10.jsonl` | `2026-05-10.jsonl.gz` | 10,993 | Yes | Pass | Pass | None |
| `2026-05-11.jsonl` | `2026-05-11.jsonl.gz` | 14,083 | Yes | Pass | Pass | None |
| `2026-05-09.jsonl` | `2026-05-09.jsonl.gz` | 23,092 | Yes | Pass | Pass | None |

Compression totals:

```text
original_total_bytes: 2726515
archive_total_bytes: 67497
observed_reclaim_bytes: 2659018
```

## Restore Verify-Only

Restore verify-only was run for each compression manifest. No real restore was performed.

Commands used:

```powershell
python tools/runtime_storage_compressor.py --restore --manifest runtime/storage_manifests/compress/compression_manifest_20260622T142727Z.json --verify-only --max-files 1
python tools/runtime_storage_compressor.py --restore --manifest runtime/storage_manifests/compress/compression_manifest_20260622T142731Z.json --verify-only --max-files 1
python tools/runtime_storage_compressor.py --restore --manifest runtime/storage_manifests/compress/compression_manifest_20260622T142736Z.json --verify-only --max-files 1
python tools/runtime_storage_compressor.py --restore --manifest runtime/storage_manifests/compress/compression_manifest_20260622T142740Z.json --verify-only --max-files 1
```

Each command returned:

```text
restored_count: 0
verified_count: 1
rejected_count: 0
```

Verify-only command log:

```text
runtime/storage_manifests/restore/small_batch_verify_only_commands.json
```

Verify-only verification file:

```text
runtime/storage_manifests/restore/small_batch_verify_only_verification.json
```

Final verify-only state:

```text
source_exists_after_verify_only: false for all 4
archive_exists_after_verify_only: true for all 4
tmp_archive_exists: false for all 4
tmp_restore_exists: false for all 4
```

## Final File State

Archives now present:

```text
runtime/quant_data/risk_log/2026-05-08.jsonl.gz
runtime/quant_data/risk_log/2026-05-09.jsonl.gz
runtime/quant_data/risk_log/2026-05-10.jsonl.gz
runtime/quant_data/risk_log/2026-05-11.jsonl.gz
```

Source JSONL files are intentionally absent after compression:

```text
runtime/quant_data/risk_log/2026-05-08.jsonl
runtime/quant_data/risk_log/2026-05-09.jsonl
runtime/quant_data/risk_log/2026-05-10.jsonl
runtime/quant_data/risk_log/2026-05-11.jsonl
```

No real restore was performed because verify-only passed.

## Validation Commands

Command:

```powershell
python -m pytest tests/test_runtime_storage_compressor.py -q
```

Result:

```text
16 passed
```

Command:

```powershell
git diff --check
```

Result:

```text
passed
```

Command:

```powershell
git status --short
```

Result:

```text
Reviewed. Workspace still contains unrelated pre-existing modified and untracked files.
```

## Safety Confirmation

Compressed file count: 4

Decision log compressed: No

Research log compressed: No

Trade journal touched: No

Phase B daily snapshots touched: No

Current UTC day touched: No

Real restore performed: No

Verify-only restore performed: Yes

Batch larger than 4: No

Cleanup performed: No

Strategy changed: No

Risk changed: No

Sizing changed: No

Execution changed: No

`.env` edited: No

Runtime restarted: No

Commit: No

Push: No
