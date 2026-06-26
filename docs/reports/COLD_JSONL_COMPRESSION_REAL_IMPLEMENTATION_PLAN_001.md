# Cold JSONL Compression Real Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement safe, reversible `--compress` and `--restore` modes for cold runtime JSONL logs after the dry-run tool has proven candidate selection.

**Architecture:** Keep `tools/runtime_storage_compressor.py` as the only production tool. Reuse the existing dry-run scanner for candidate selection, add manifest-backed compression and restore records, and require explicit CLI flags for every operation that can write or remove files. Real compression must be atomic: write archive to `.tmp`, verify archive and source, rename to final archive, then remove source only after verification succeeds.

**Tech Stack:** Python standard library (`argparse`, `gzip`, `hashlib`, `json`, `shutil`, `tempfile`, `pathlib`, `datetime`), optional `zstandard` only after gzip path is proven, `pytest`.

---

## Current State

Committed dry-run tool:

```text
tools/runtime_storage_compressor.py
```

Committed tests:

```text
tests/test_runtime_storage_compressor.py
```

Dry-run evidence:

```text
candidates: 143
expected_reclaim: ~24.22 GB
real_compression: none
--compress: safe stub
--restore: safe stub
```

Current candidate target folders:

```text
runtime/quant_data/decision_log/
runtime/quant_data/research_log/
runtime/quant_data/risk_log/
runtime/quant_data/market_snapshots/
```

Permanent protected folders:

```text
runtime/quant_data/trade_journal/
runtime/quant_data/reports/phase_b_daily_snapshots/
runtime/ownership/
scratch/
.env
source code folders
```

## Final Verdict

READY_FOR_COMPRESS_RESTORE_PATCH

## Compression Algorithm Decision

Implement `gzip` first.

Reason:

- Python standard library support.
- No dependency/install risk.
- Existing dry-run tests already use `gzip`.
- Restore can be implemented with standard `gzip.open`.
- Cross-platform operator recovery is simple.

Keep `zstd` accepted by the dry-run estimator, but real `--compress --algorithm zstd` must remain blocked until a separate zstd patch proves dependency availability and restore parity.

Real patch behavior:

```text
--dry-run --algorithm gzip: supported
--dry-run --algorithm zstd: remains supported as estimate-only
--compress --algorithm gzip: implement
--compress --algorithm zstd: fail safely with explicit unsupported message
--restore: support gzip archives created by this tool
```

## File Structure

Modify:

```text
tools/runtime_storage_compressor.py
tests/test_runtime_storage_compressor.py
```

Optional reports for the implementation task:

```text
COLD_JSONL_COMPRESSION_REAL_PATCH_REPORT_001.md
COLD_JSONL_COMPRESSION_REAL_PRE_COMMIT_AUDIT_001.md
```

Do not modify:

```text
strategy modules
risk modules
sizing modules
execution modules
.env
runtime/quant_data source logs except explicitly approved compression target during real execution task
```

## CLI Contract

Add flags:

```text
--manifest PATH
--max-files N
--one-file PATH
--allow-overwrite
--verify-only
--cleanup-tmp
--min-free-disk-bytes N
```

Compression examples:

```powershell
python tools/runtime_storage_compressor.py --dry-run --age-days 7 --algorithm gzip
python tools/runtime_storage_compressor.py --compress --age-days 7 --algorithm gzip --max-files 1 --one-file runtime/quant_data/risk_log/YYYY-MM-DD.jsonl
python tools/runtime_storage_compressor.py --compress --age-days 7 --algorithm gzip --max-files 50
```

Restore examples:

```powershell
python tools/runtime_storage_compressor.py --restore --manifest runtime/storage_manifests/compress/compression_manifest_YYYYMMDDTHHMMSSZ.json --max-files 1
python tools/runtime_storage_compressor.py --restore --manifest runtime/storage_manifests/compress/compression_manifest_YYYYMMDDTHHMMSSZ.json --one-file runtime/quant_data/risk_log/YYYY-MM-DD.jsonl.gz
```

Verification-only example:

```powershell
python tools/runtime_storage_compressor.py --restore --manifest runtime/storage_manifests/compress/compression_manifest_YYYYMMDDTHHMMSSZ.json --verify-only
```

## Manifest Paths

Dry-run manifest remains:

```text
runtime/storage_manifests/dry_run/compression_dry_run_manifest_001.json
```

Real compression manifest directory:

```text
runtime/storage_manifests/compress/
```

Real compression manifest naming:

```text
compression_manifest_YYYYMMDDTHHMMSSZ.json
```

Restore report directory:

```text
runtime/storage_manifests/restore/
```

Restore report naming:

```text
restore_manifest_YYYYMMDDTHHMMSSZ.json
```

## Manifest Schema Additions

Compression manifest root fields:

```json
{
  "schema_version": "2.0",
  "timestamp_utc": "2026-06-22T00:00:00Z",
  "mode": "compress",
  "algorithm": "gzip",
  "age_days": 7,
  "runtime_root": "runtime",
  "dry_run_manifest_path": "runtime/storage_manifests/dry_run/compression_dry_run_manifest_001.json",
  "dry_run_candidate_count": 143,
  "max_files": 1,
  "one_file": "runtime/quant_data/risk_log/YYYY-MM-DD.jsonl",
  "records": [],
  "exclusions": [],
  "summary": {}
}
```

Compression record fields:

```json
{
  "source_path": "runtime/quant_data/risk_log/YYYY-MM-DD.jsonl",
  "archive_path": "runtime/quant_data/risk_log/YYYY-MM-DD.jsonl.gz",
  "tmp_path": "runtime/quant_data/risk_log/YYYY-MM-DD.jsonl.gz.tmp",
  "algorithm": "gzip",
  "status": "compressed",
  "original_size_bytes": 123,
  "archive_size_bytes": 45,
  "source_sha256_before": "hex",
  "source_sha256_after": "hex",
  "archive_sha256": "hex",
  "line_count_before": 10,
  "line_count_after_decompress": 10,
  "verified_before_source_remove": true,
  "source_removed": true,
  "timestamp_utc": "2026-06-22T00:00:00Z"
}
```

Restore record fields:

```json
{
  "archive_path": "runtime/quant_data/risk_log/YYYY-MM-DD.jsonl.gz",
  "restore_path": "runtime/quant_data/risk_log/YYYY-MM-DD.jsonl",
  "tmp_restore_path": "runtime/quant_data/risk_log/YYYY-MM-DD.jsonl.restore.tmp",
  "status": "restored",
  "archive_sha256_expected": "hex",
  "archive_sha256_actual": "hex",
  "restored_sha256": "hex",
  "source_sha256_expected": "hex",
  "line_count_expected": 10,
  "line_count_restored": 10,
  "overwrite_used": false,
  "timestamp_utc": "2026-06-22T00:00:00Z"
}
```

## Exact Compression Write Flow

For each candidate:

1. Re-run classification with current UTC date and `age_days`.
2. Reject if current UTC day, protected folder, non-jsonl, already compressed, outside target folders, younger than age threshold, missing file, or git-tracked source path outside runtime.
3. If `--one-file` is set, only accept that exact candidate after normal classification.
4. If `--max-files` is set, stop after that many accepted candidates.
5. Check free disk before writing:

```python
required_free = min_free_disk_bytes or max(candidate.original_size_bytes, 256 * 1024 * 1024)
free = shutil.disk_usage(candidate.path.parent).free
if free < required_free:
    reject with reason "insufficient_free_disk"
```

6. Compute `source_sha256_before`.
7. Count source lines by streaming bytes.
8. Build paths:

```text
archive_path = source_path + ".gz"
tmp_path = archive_path + ".tmp"
```

9. Reject if `archive_path` exists.
10. Remove stale `tmp_path` only if `--cleanup-tmp` is provided; otherwise reject with `tmp_exists`.
11. Stream source to gzip temp:

```python
with source.open("rb") as src, gzip.open(tmp_path, "wb", compresslevel=6) as dst:
    shutil.copyfileobj(src, dst, length=1024 * 1024)
```

12. Flush/close temp file.
13. Compute `archive_sha256` on `tmp_path`.
14. Decompress `tmp_path` as a stream and compute:

```text
decompressed_sha256
line_count_after_decompress
```

15. Verify:

```text
decompressed_sha256 == source_sha256_before
line_count_after_decompress == line_count_before
```

16. Recompute `source_sha256_after` before removal.
17. Verify:

```text
source_sha256_after == source_sha256_before
```

18. Atomically rename temp to archive:

```python
tmp_path.replace(archive_path)
```

19. Verify final archive hash equals `archive_sha256`.
20. Remove source only after all verification passes:

```python
source_path.unlink()
```

21. Write/update compression manifest after each file record so interruption preserves completed work.

## Exact Restore Flow

For each selected manifest record:

1. Read compression manifest.
2. Reject records without `status == "compressed"`.
3. Require `archive_path` exists.
4. Reject if `restore_path` exists unless `--allow-overwrite` is passed.
5. Verify `archive_sha256_actual == archive_sha256_expected`.
6. Build temp restore path:

```text
restore_path + ".restore.tmp"
```

7. Reject stale restore temp unless `--cleanup-tmp` is passed.
8. Decompress archive to temp restore path by streaming.
9. Compute restored sha256 and line count.
10. Verify:

```text
restored_sha256 == source_sha256_before
line_count_restored == line_count_before
```

11. If `--verify-only`, delete temp restore path and do not write final restore file.
12. If not verify-only:

```python
tmp_restore_path.replace(restore_path)
```

13. Recompute restored file hash after final rename.
14. Preserve compressed archive until restore is verified.
15. Write restore report record.

## Safety Gates

Hard gates:

- Never target current UTC day.
- Never target `trade_journal`.
- Never target `runtime/quant_data/reports/phase_b_daily_snapshots`.
- Never target `runtime/ownership`.
- Never target `scratch`.
- Never target `.env`.
- Never target source code folders.
- Never target non-`.jsonl` files for compression.
- Never target already compressed files for compression.
- Never overwrite existing archive.
- Never overwrite restored `.jsonl` unless `--allow-overwrite` is explicit.
- Never remove source before archive verification.
- Never remove archive during restore.
- Real `zstd` compression blocked until separate patch.

Required verification gates:

- Free disk check before compression.
- Source sha256 before compression.
- Source sha256 immediately before source removal.
- Compressed archive sha256.
- Decompressed sha256 parity.
- Line count parity.
- Dry-run parity with compress target list.
- `--max-files` required for first real runs.

## Dry-Run Parity Rule

Before real compression, run:

```powershell
python tools/runtime_storage_compressor.py --dry-run --age-days 7 --algorithm gzip
```

Compression must build its candidate set from the same scanner and classification logic.

For `--compress`, store in manifest:

```text
dry_run_candidate_count
compress_selected_count
compress_rejected_count
candidate_selection_source = "shared_scanner"
```

If a file selected for compression was not eligible in the shared dry-run scanner, reject it.

## First Real Execution Strategy

Stage A: one small file only.

Command shape:

```powershell
python tools/runtime_storage_compressor.py --compress --age-days 7 --algorithm gzip --max-files 1 --one-file runtime/quant_data/risk_log/YYYY-MM-DD.jsonl
```

Selection rule:

- Pick a small `risk_log` or `market_snapshots` candidate from the dry-run manifest.
- Avoid huge `decision_log` files in the first compression run.
- Confirm archive exists, source removed, manifest verifies, restore verify-only passes.

Stage B: one full day across approved target folders.

Command shape:

```powershell
python tools/runtime_storage_compressor.py --compress --age-days 7 --algorithm gzip --max-files 4 --date YYYY-MM-DD
```

Implementation note:

- Add `--date YYYY-MM-DD` if needed during real patch.
- Date-scoped compression must still exclude protected folders.

Stage C: all files older than 7 days.

Command shape:

```powershell
python tools/runtime_storage_compressor.py --compress --age-days 7 --algorithm gzip --max-files 25
```

Repeat in bounded batches. Do not run unbounded all-file compression on the first real day.

## Test Plan

### Task 1: Gzip Compression Roundtrip

**Files:**

- Modify: `tools/runtime_storage_compressor.py`
- Modify: `tests/test_runtime_storage_compressor.py`

- [ ] **Step 1: Write failing test**

```python
def test_gzip_compress_roundtrip_removes_source_after_verification(tmp_path: Path) -> None:
    source = tmp_path / "runtime" / "quant_data" / "risk_log" / "2026-06-14.jsonl"
    _write(source, "{\"a\":1}\n{\"b\":2}\n")

    manifest = compressor.compress_candidates(
        runtime_root=tmp_path / "runtime",
        manifest_root=tmp_path / "runtime" / "storage_manifests" / "compress",
        age_days=7,
        algorithm="gzip",
        today=date(2026, 6, 22),
        max_files=1,
        one_file=source,
    )

    archive = source.with_name(source.name + ".gz")
    assert not source.exists()
    assert archive.exists()
    record = manifest["records"][0]
    assert record["status"] == "compressed"
    assert record["line_count_before"] == 2
    assert record["line_count_after_decompress"] == 2
    assert record["source_sha256_before"] == record["source_sha256_after"]
    assert record["verified_before_source_remove"] is True
    assert record["source_removed"] is True
```

- [ ] **Step 2: Run failing test**

```powershell
python -m pytest tests/test_runtime_storage_compressor.py::test_gzip_compress_roundtrip_removes_source_after_verification -q
```

Expected: fail because `compress_candidates` does not exist.

- [ ] **Step 3: Implement minimal compression helper**

Add helper functions:

```python
def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _count_lines(path: Path) -> int:
    count = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            count += chunk.count(b"\n")
    return count
```

Add `compress_candidates(...)` using the exact compression write flow above.

- [ ] **Step 4: Run test**

```powershell
python -m pytest tests/test_runtime_storage_compressor.py::test_gzip_compress_roundtrip_removes_source_after_verification -q
```

Expected: pass.

### Task 2: Restore Roundtrip

- [ ] **Step 1: Write failing test**

```python
def test_restore_roundtrip_recreates_original_jsonl_without_removing_archive(tmp_path: Path) -> None:
    source = tmp_path / "runtime" / "quant_data" / "risk_log" / "2026-06-14.jsonl"
    original = "{\"a\":1}\n{\"b\":2}\n"
    _write(source, original)
    manifest = compressor.compress_candidates(
        runtime_root=tmp_path / "runtime",
        manifest_root=tmp_path / "runtime" / "storage_manifests" / "compress",
        age_days=7,
        algorithm="gzip",
        today=date(2026, 6, 22),
        max_files=1,
        one_file=source,
    )
    archive = source.with_name(source.name + ".gz")

    restore_report = compressor.restore_from_manifest(
        manifest=manifest,
        max_files=1,
        allow_overwrite=False,
        verify_only=False,
    )

    assert source.read_text(encoding="utf-8") == original
    assert archive.exists()
    record = restore_report["records"][0]
    assert record["status"] == "restored"
    assert record["restored_sha256"] == manifest["records"][0]["source_sha256_before"]
```

- [ ] **Step 2: Run failing test**

```powershell
python -m pytest tests/test_runtime_storage_compressor.py::test_restore_roundtrip_recreates_original_jsonl_without_removing_archive -q
```

Expected: fail because `restore_from_manifest` does not exist.

- [ ] **Step 3: Implement restore helper**

Implement the exact restore flow above.

- [ ] **Step 4: Run test**

```powershell
python -m pytest tests/test_runtime_storage_compressor.py::test_restore_roundtrip_recreates_original_jsonl_without_removing_archive -q
```

Expected: pass.

### Task 3: Interruption And Temp Safety

- [ ] **Step 1: Add tests**

```python
def test_compress_rejects_existing_tmp_without_cleanup_flag(tmp_path: Path) -> None:
    source = tmp_path / "runtime" / "quant_data" / "risk_log" / "2026-06-14.jsonl"
    _write(source, "{\"a\":1}\n")
    tmp_archive = source.with_name(source.name + ".gz.tmp")
    _write(tmp_archive, "partial")

    manifest = compressor.compress_candidates(
        runtime_root=tmp_path / "runtime",
        manifest_root=tmp_path / "runtime" / "storage_manifests" / "compress",
        age_days=7,
        algorithm="gzip",
        today=date(2026, 6, 22),
        max_files=1,
        one_file=source,
        cleanup_tmp=False,
    )

    assert source.exists()
    assert tmp_archive.exists()
    assert manifest["records"][0]["status"] == "rejected"
    assert manifest["records"][0]["reason"] == "tmp_exists"
```

```python
def test_restore_rejects_existing_jsonl_without_allow_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "runtime" / "quant_data" / "risk_log" / "2026-06-14.jsonl"
    _write(source, "{\"a\":1}\n")
    manifest = compressor.compress_candidates(
        runtime_root=tmp_path / "runtime",
        manifest_root=tmp_path / "runtime" / "storage_manifests" / "compress",
        age_days=7,
        algorithm="gzip",
        today=date(2026, 6, 22),
        max_files=1,
        one_file=source,
    )
    source.write_text("existing replacement\n", encoding="utf-8")

    report = compressor.restore_from_manifest(
        manifest=manifest,
        max_files=1,
        allow_overwrite=False,
        verify_only=False,
    )

    assert report["records"][0]["status"] == "rejected"
    assert report["records"][0]["reason"] == "restore_path_exists"
```

- [ ] **Step 2: Run tests**

```powershell
python -m pytest tests/test_runtime_storage_compressor.py::test_compress_rejects_existing_tmp_without_cleanup_flag tests/test_runtime_storage_compressor.py::test_restore_rejects_existing_jsonl_without_allow_overwrite -q
```

Expected: fail, then pass after temp safety is implemented.

### Task 4: CLI Integration

- [ ] **Step 1: Add CLI tests**

```python
def test_compress_cli_requires_max_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        compressor.main([
            "--compress",
            "--age-days", "7",
            "--algorithm", "gzip",
            "--runtime-root", str(tmp_path / "runtime"),
        ])
    assert exc.value.code == 2
    assert "max-files" in capsys.readouterr().err.lower()
```

```python
def test_restore_cli_reads_manifest_path(tmp_path: Path) -> None:
    source = tmp_path / "runtime" / "quant_data" / "risk_log" / "2026-06-14.jsonl"
    _write(source, "{\"a\":1}\n")
    manifest = compressor.compress_candidates(
        runtime_root=tmp_path / "runtime",
        manifest_root=tmp_path / "runtime" / "storage_manifests" / "compress",
        age_days=7,
        algorithm="gzip",
        today=date(2026, 6, 22),
        max_files=1,
        one_file=source,
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = compressor.main([
        "--restore",
        "--manifest", str(manifest_path),
        "--max-files", "1",
    ])

    assert result == 0
    assert source.exists()
```

- [ ] **Step 2: Implement CLI options**

Add parser options exactly as listed in CLI Contract.

- [ ] **Step 3: Run CLI tests**

```powershell
python -m pytest tests/test_runtime_storage_compressor.py::test_compress_cli_requires_max_files tests/test_runtime_storage_compressor.py::test_restore_cli_reads_manifest_path -q
```

Expected: pass.

### Task 5: Full Validation

- [ ] **Step 1: Run compile**

```powershell
python -m py_compile tools/runtime_storage_compressor.py
```

Expected: exit 0.

- [ ] **Step 2: Run focused tests**

```powershell
python -m pytest tests/test_runtime_storage_compressor.py -q
```

Expected: all tests pass.

- [ ] **Step 3: Run diff check**

```powershell
git diff --check
```

Expected: exit 0.

- [ ] **Step 4: Run dry-run again**

```powershell
python tools/runtime_storage_compressor.py --dry-run --age-days 7 --algorithm gzip
```

Expected: dry-run manifest written only, no `.gz` created.

- [ ] **Step 5: Do not run real compression in implementation patch unless explicitly scoped**

Real compression execution should be a separate task after patch commit, starting with one small file.

## Rollback Plan

Manual restore command:

```powershell
python tools/runtime_storage_compressor.py --restore --manifest runtime/storage_manifests/compress/compression_manifest_YYYYMMDDTHHMMSSZ.json --max-files 1
```

Full manifest restore in batches:

```powershell
python tools/runtime_storage_compressor.py --restore --manifest runtime/storage_manifests/compress/compression_manifest_YYYYMMDDTHHMMSSZ.json --max-files 25
```

Verification-only before restore:

```powershell
python tools/runtime_storage_compressor.py --restore --manifest runtime/storage_manifests/compress/compression_manifest_YYYYMMDDTHHMMSSZ.json --verify-only --max-files 25
```

Rollback rules:

- Preserve compressed archive until restored file hash and line count are verified.
- Do not delete archive during restore.
- Do not overwrite existing `.jsonl` unless `--allow-overwrite` is explicit.
- If restore fails, leave archive and any original file untouched.
- If `.restore.tmp` remains after interruption, require `--cleanup-tmp` to continue.

## Operator Command Set

Dry-run:

```powershell
python tools/runtime_storage_compressor.py --dry-run --age-days 7 --algorithm gzip
```

One-file compression:

```powershell
python tools/runtime_storage_compressor.py --compress --age-days 7 --algorithm gzip --max-files 1 --one-file runtime/quant_data/risk_log/YYYY-MM-DD.jsonl
```

Restore:

```powershell
python tools/runtime_storage_compressor.py --restore --manifest runtime/storage_manifests/compress/compression_manifest_YYYYMMDDTHHMMSSZ.json --max-files 1
```

Verify-only restore:

```powershell
python tools/runtime_storage_compressor.py --restore --manifest runtime/storage_manifests/compress/compression_manifest_YYYYMMDDTHHMMSSZ.json --verify-only --max-files 1
```

Check no current-day target:

```powershell
python tools/runtime_storage_compressor.py --dry-run --age-days 1 --algorithm gzip
```

Then inspect manifest exclusions for:

```text
current_utc_day
```

## Spec Coverage Review

Compression implementation scope: covered.

Restore implementation scope: covered.

Safety gates: covered.

First real execution strategy: covered.

Test plan: covered.

Rollback plan: covered.

Operator commands: covered.

## Final Recommendation

READY_FOR_COMPRESS_RESTORE_PATCH
