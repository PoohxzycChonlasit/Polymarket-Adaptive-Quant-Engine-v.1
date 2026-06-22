# COMPRESS_RESTORE_PATCH_REPORT_001

## Final Verdict

COMPRESS_RESTORE_PATCH_PASS

## Scope

Implemented real gzip-backed compression and restore support in:

```text
tools/runtime_storage_compressor.py
```

Updated focused tests in:

```text
tests/test_runtime_storage_compressor.py
```

No real compression was run against runtime data. No restore was run against runtime data.

## Compression Implementation

Implemented `--compress` for `--algorithm gzip` only.

Compression flow:

1. Reuses the existing dry-run scanner and classifier.
2. Excludes current UTC day.
3. Excludes protected folders and non-target folders.
4. Requires `--max-files` from CLI before compression can run.
5. Computes source sha256 before compression.
6. Counts source lines.
7. Writes gzip archive to:

```text
<source>.gz.tmp
```

8. Computes archive sha256 on temp archive.
9. Decompresses temp archive and verifies:

```text
decompressed_sha256 == source_sha256_before
line_count_after_decompress == line_count_before
```

10. Recomputes source sha256 before removal.
11. Atomically renames temp archive to:

```text
<source>.gz
```

12. Verifies final archive sha256.
13. Deletes source only after all verification passes.
14. Writes compression manifest under:

```text
runtime/storage_manifests/compress/
```

## Restore Implementation

Implemented manifest-backed `--restore` for gzip archives created by the tool.

Restore flow:

1. Reads compression manifest from `--manifest`.
2. Verifies archive exists.
3. Verifies archive sha256.
4. Refuses to overwrite existing `.jsonl` unless `--allow-overwrite` is passed.
5. Writes restored JSONL to:

```text
<source>.restore.tmp
```

6. Verifies restored sha256.
7. Verifies restored line count.
8. Supports `--verify-only`, which validates the archive without recreating the JSONL.
9. Preserves archive in all restore modes.
10. Writes restore report under:

```text
runtime/storage_manifests/restore/
```

## CLI Added

Implemented:

```text
--compress
--restore
--manifest
--max-files
--one-file
--allow-overwrite
--verify-only
--cleanup-tmp
```

Additional safety/utility flag:

```text
--min-free-disk-bytes
```

Real compression support:

```text
--compress --algorithm gzip
```

Blocked:

```text
--compress --algorithm zstd
```

Dry-run zstd estimation remains unchanged.

## Tests Added / Updated

Added coverage for:

- Compression roundtrip.
- Restore roundtrip.
- Verify-only restore.
- Temp archive protection.
- Restore overwrite protection.
- Compression manifest schema.
- Current day exclusion in compression path.
- CLI requires `--max-files` for compression.
- CLI restore reads manifest path.

Existing dry-run tests remain covered:

- Current day excluded.
- Protected folders excluded.
- Only `.jsonl` targeted.
- Already compressed files excluded.
- Dry-run does not modify files.
- Expected savings computed.
- Manifest schema valid.
- Large-file estimation uses bounded samples.

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
16 passed
```

Command:

```powershell
git diff --check
```

Result:

```text
exit 0
```

Notes:

- Git emitted CRLF normalization warnings for touched Python files.
- No whitespace errors were reported.

## Commands Not Run

Not run:

```powershell
python tools/runtime_storage_compressor.py --compress ...
python tools/runtime_storage_compressor.py --restore ...
```

Reason:

```text
Task explicitly forbids real compression and restore on runtime files.
```

## Safety Confirmation

Real runtime compression: No

Runtime restore: No

Runtime restart: No

Strategy changed: No

EV changed: No

Risk changed: No

Sizing changed: No

Execution changed: No

`.env` edited: No

Commit: No

Push: No
