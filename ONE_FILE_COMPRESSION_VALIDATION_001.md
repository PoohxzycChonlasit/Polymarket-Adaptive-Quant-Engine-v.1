# ONE_FILE_COMPRESSION_VALIDATION_001

## Final Verdict

ONE_FILE_COMPRESSION_VALIDATION_PASS

## Mode

Controlled real data validation.

Exactly one cold JSONL file was compressed and restored.

No batch compression was run. No cleanup was performed. No commit or push was performed.

## Runtime Context

An active paper runtime process was observed before validation:

```text
main.py --mode paper ...
```

The selected validation file was old, cold, not current day, small, and outside `trade_journal`.

## Dry-Run

Command:

```powershell
python tools/runtime_storage_compressor.py --dry-run --age-days 7 --algorithm gzip
```

Result:

```text
candidate_count: 143
exclusion_count: 231
total_expected_reclaim_bytes: 24223376544
manifest: runtime\storage_manifests\dry_run\compression_dry_run_manifest_001.json
```

## Selected File

Selected file:

```text
runtime/quant_data/market_snapshots/2026-05-08.jsonl
```

Selection evidence:

```text
folder: market_snapshots
age: older than 7 days
current UTC day: no
dry-run candidate: yes
decision_log: no
trade_journal: no
phase_b_daily_snapshots: no
archive existed before: no
```

Pre-compression evidence:

```text
size_bytes: 297811
line_count: 331
sha256: 747fbad481348846a5d0513fcd55852d76f4fc1e428576bb873ef6568b93bf37
estimated_compressed_size_bytes: 31734
estimated_savings_bytes: 266077
estimate_method: exact
```

Selection evidence file:

```text
runtime/storage_manifests/dry_run/one_file_selected_candidate.json
```

## Compression

Command:

```powershell
python tools/runtime_storage_compressor.py --compress --age-days 7 --algorithm gzip --max-files 1 --one-file runtime/quant_data/market_snapshots/2026-05-08.jsonl
```

Result:

```text
compressed_count: 1
rejected_count: 0
manifest: runtime\storage_manifests\compress\compression_manifest_20260622T142136Z.json
```

Compression verification:

```text
source_exists_after_compress: false
archive_exists_after_compress: true
archive_size_bytes: 33218
record_status: compressed
line_count_before: 331
line_count_after_decompress: 331
line_count_parity: true
source_sha256_before: 747fbad481348846a5d0513fcd55852d76f4fc1e428576bb873ef6568b93bf37
source_sha256_after: 747fbad481348846a5d0513fcd55852d76f4fc1e428576bb873ef6568b93bf37
source_sha256_recheck_passed: true
archive_sha256: 7dc821e6ff647d31fd9842eecb56345e7431026a536bc227d2b8a04b1660334b
verified_before_source_remove: true
source_removed: true
tmp_archive_exists: false
tmp_restore_exists: false
```

Compression verification file:

```text
runtime/storage_manifests/compress/one_file_compress_verification.json
```

## Restore Verify-Only

Command:

```powershell
python tools/runtime_storage_compressor.py --restore --manifest runtime/storage_manifests/compress/compression_manifest_20260622T142136Z.json --verify-only --max-files 1
```

Result:

```text
restored_count: 0
verified_count: 1
rejected_count: 0
manifest: runtime\storage_manifests\restore\restore_manifest_20260622T142201Z.json
```

Verify-only status:

```text
status: verified
jsonl recreated during verify-only: no
```

## Real Restore

Command:

```powershell
python tools/runtime_storage_compressor.py --restore --manifest runtime/storage_manifests/compress/compression_manifest_20260622T142136Z.json --max-files 1
```

Result:

```text
restored_count: 1
verified_count: 0
rejected_count: 0
manifest: runtime\storage_manifests\restore\restore_manifest_20260622T142208Z.json
```

Post-restore verification:

```text
source_exists_after_restore: true
archive_preserved_after_restore: true
archive_size_bytes: 33218
restored_sha256: 747fbad481348846a5d0513fcd55852d76f4fc1e428576bb873ef6568b93bf37
expected_sha256: 747fbad481348846a5d0513fcd55852d76f4fc1e428576bb873ef6568b93bf37
sha256_matches_original: true
restored_line_count: 331
expected_line_count: 331
line_count_matches_original: true
restore_status: restored
restore_record_sha_matches: true
restore_record_line_matches: true
tmp_archive_exists: false
tmp_restore_exists: false
```

Restore verification file:

```text
runtime/storage_manifests/restore/one_file_restore_verification.json
```

Final file state:

```text
runtime/quant_data/market_snapshots/2026-05-08.jsonl
runtime/quant_data/market_snapshots/2026-05-08.jsonl.gz
```

The `.jsonl.gz` archive was intentionally preserved per rollback policy.

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

Compressed files count: 1

Restored files count: 1

Batch compression: No

Decision log compressed: No

Trade journal touched: No

Phase B daily snapshots touched: No

Current UTC day touched: No

Strategy changed: No

Risk changed: No

Sizing changed: No

Execution changed: No

`.env` edited: No

Runtime restarted: No

Commit: No

Push: No

Cleanup: No
