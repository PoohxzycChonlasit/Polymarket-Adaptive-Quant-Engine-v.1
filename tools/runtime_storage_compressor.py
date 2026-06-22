from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MANIFEST_SCHEMA_VERSION = "1.0"
COMPRESS_MANIFEST_SCHEMA_VERSION = "2.0"
DEFAULT_RUNTIME_ROOT = Path("runtime")
DEFAULT_MANIFEST_ROOT = DEFAULT_RUNTIME_ROOT / "storage_manifests" / "dry_run"
DEFAULT_COMPRESS_MANIFEST_ROOT = DEFAULT_RUNTIME_ROOT / "storage_manifests" / "compress"
DEFAULT_RESTORE_MANIFEST_ROOT = DEFAULT_RUNTIME_ROOT / "storage_manifests" / "restore"
DEFAULT_MANIFEST_NAME = "compression_dry_run_manifest_001.json"
TARGET_RELATIVE_DIRS = (
    Path("quant_data/decision_log"),
    Path("quant_data/research_log"),
    Path("quant_data/risk_log"),
    Path("quant_data/market_snapshots"),
)
PROTECTED_RELATIVE_DIRS = (
    Path("quant_data/trade_journal"),
    Path("quant_data/reports/phase_b_daily_snapshots"),
    Path("ownership"),
)
COMPRESSED_SUFFIXES = (".gz", ".gzip", ".zst", ".zstd")
MAX_EXACT_ESTIMATE_BYTES = 8 * 1024 * 1024
SAMPLE_BYTES_PER_REGION = 256 * 1024
COPY_BUFFER_BYTES = 1024 * 1024
DEFAULT_MIN_FREE_DISK_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True)
class ScanEntry:
    path: Path
    reason: str = ""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp_for_filename() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _date_from_jsonl_name(path: Path) -> date | None:
    try:
        return date.fromisoformat(path.stem)
    except ValueError:
        return None


def _iter_existing_files(runtime_root: Path) -> Iterable[Path]:
    quant_data = runtime_root / "quant_data"
    if not quant_data.exists():
        return []
    return sorted(path for path in quant_data.rglob("*") if path.is_file())


def _target_dirs(runtime_root: Path) -> tuple[Path, ...]:
    return tuple(runtime_root / relative for relative in TARGET_RELATIVE_DIRS)


def _protected_dirs(runtime_root: Path) -> tuple[Path, ...]:
    return tuple(runtime_root / relative for relative in PROTECTED_RELATIVE_DIRS)


def _classify_file(path: Path, runtime_root: Path, today: date, age_days: int) -> ScanEntry:
    if any(_is_relative_to(path, protected) for protected in _protected_dirs(runtime_root)):
        return ScanEntry(path, "protected_folder")

    if any(path.name.endswith(suffix) for suffix in COMPRESSED_SUFFIXES):
        return ScanEntry(path, "already_compressed")

    if path.suffix != ".jsonl":
        return ScanEntry(path, "non_jsonl")

    if not any(_is_relative_to(path, target) for target in _target_dirs(runtime_root)):
        return ScanEntry(path, "outside_target_folders")

    file_date = _date_from_jsonl_name(path)
    if file_date is None:
        return ScanEntry(path, "date_unparseable")

    if file_date == today:
        return ScanEntry(path, "current_utc_day")

    age = (today - file_date).days
    if age < age_days:
        return ScanEntry(path, "younger_than_age_days")

    return ScanEntry(path)


def _sample_file_bytes(path: Path, file_size: int) -> bytes:
    if file_size <= MAX_EXACT_ESTIMATE_BYTES:
        return path.read_bytes()

    chunk_size = min(SAMPLE_BYTES_PER_REGION, file_size)
    middle_start = max(0, (file_size // 2) - (chunk_size // 2))
    tail_start = max(0, file_size - chunk_size)
    regions = (0, middle_start, tail_start)
    chunks: list[bytes] = []
    with path.open("rb") as handle:
        for start in regions:
            handle.seek(start)
            chunks.append(handle.read(chunk_size))
    return b"".join(chunks)


def _estimate_gzip_size(path: Path) -> tuple[int, str]:
    file_size = path.stat().st_size
    if file_size <= MAX_EXACT_ESTIMATE_BYTES:
        data = path.read_bytes()
        return len(gzip.compress(data)), "exact"

    sample = _sample_file_bytes(path, file_size)
    compressed_sample_size = len(gzip.compress(sample))
    ratio = compressed_sample_size / max(1, len(sample))
    return max(1, int(file_size * ratio)), "sampled"


def _estimate_zstd_size(path: Path) -> tuple[int, str]:
    file_size = path.stat().st_size
    sample = _sample_file_bytes(path, file_size)
    method = "exact" if file_size <= MAX_EXACT_ESTIMATE_BYTES else "sampled"
    data_len = max(1, len(sample))
    try:
        import zstandard as zstd  # type: ignore

        compressed_sample_size = len(zstd.ZstdCompressor(level=3).compress(sample))
        ratio = compressed_sample_size / data_len
        return max(1, int(file_size * ratio)), method
    except Exception:
        return max(1, int(file_size * 0.35)), f"{method}_fallback_ratio"


def _estimate_compressed_size(path: Path, algorithm: str) -> tuple[int, str]:
    if algorithm == "gzip":
        return _estimate_gzip_size(path)
    if algorithm == "zstd":
        return _estimate_zstd_size(path)
    raise ValueError(f"unsupported algorithm: {algorithm}")


def _candidate_record(path: Path, algorithm: str) -> dict[str, Any]:
    original_size = path.stat().st_size
    estimated_size, estimate_method = _estimate_compressed_size(path, algorithm)
    return {
        "path": str(path),
        "original_size_bytes": original_size,
        "estimated_compressed_size_bytes": estimated_size,
        "estimated_savings_bytes": max(0, original_size - estimated_size),
        "estimate_method": estimate_method,
        "algorithm": algorithm,
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(COPY_BUFFER_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _count_lines(path: Path) -> int:
    count = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(COPY_BUFFER_BYTES), b""):
            count += chunk.count(b"\n")
    return count


def _gzip_sha256_and_line_count(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    line_count = 0
    with gzip.open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(COPY_BUFFER_BYTES), b""):
            digest.update(chunk)
            line_count += chunk.count(b"\n")
    return digest.hexdigest(), line_count


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _manifest_path(manifest_root: Path, prefix: str) -> Path:
    return manifest_root / f"{prefix}_{_timestamp_for_filename()}.json"


def build_dry_run_manifest(
    *,
    runtime_root: str | Path = DEFAULT_RUNTIME_ROOT,
    manifest_root: str | Path = DEFAULT_MANIFEST_ROOT,
    age_days: int,
    algorithm: str,
    today: date | None = None,
    write_manifest: bool = True,
) -> dict[str, Any]:
    runtime_root = Path(runtime_root)
    manifest_root = Path(manifest_root)
    today = today or _utc_now().date()

    if age_days < 1:
        raise ValueError("age_days must be >= 1")

    candidates: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for path in _iter_existing_files(runtime_root):
        entry = _classify_file(path, runtime_root, today, age_days)
        if entry.reason:
            exclusions.append({"path": str(entry.path), "reason": entry.reason})
        else:
            candidates.append(_candidate_record(entry.path, algorithm))

    candidates.sort(key=lambda item: item["original_size_bytes"], reverse=True)
    exclusions.sort(key=lambda item: item["path"])
    total_original = sum(item["original_size_bytes"] for item in candidates)
    total_estimated = sum(item["estimated_compressed_size_bytes"] for item in candidates)
    total_reclaim = sum(item["estimated_savings_bytes"] for item in candidates)
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "timestamp_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "dry_run",
        "age_days": age_days,
        "algorithm": algorithm,
        "target_folders": [str(runtime_root / relative) for relative in TARGET_RELATIVE_DIRS],
        "protected_folders": [str(runtime_root / relative) for relative in PROTECTED_RELATIVE_DIRS]
        + ["scratch", ".env", "source code folders"],
        "candidates": candidates,
        "exclusions": exclusions,
        "summary": {
            "candidate_count": len(candidates),
            "exclusion_count": len(exclusions),
            "total_original_size_bytes": total_original,
            "total_estimated_compressed_size_bytes": total_estimated,
            "total_expected_reclaim_bytes": total_reclaim,
            "top_20_candidates_by_size": candidates[:20],
        },
    }

    if write_manifest:
        manifest_root.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_root / DEFAULT_MANIFEST_NAME
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return manifest


def _compress_rejection_record(path: Path, reason: str) -> dict[str, Any]:
    return {
        "source_path": str(path),
        "archive_path": str(path.with_name(path.name + ".gz")),
        "algorithm": "gzip",
        "status": "rejected",
        "reason": reason,
        "timestamp_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _compress_one_gzip(
    source: Path,
    *,
    cleanup_tmp: bool,
    min_free_disk_bytes: int | None,
) -> dict[str, Any]:
    archive = source.with_name(source.name + ".gz")
    tmp = source.with_name(source.name + ".gz.tmp")
    original_size = source.stat().st_size
    required_free = min_free_disk_bytes or max(original_size, DEFAULT_MIN_FREE_DISK_BYTES)
    free = shutil.disk_usage(source.parent).free
    if free < required_free:
        return _compress_rejection_record(source, "insufficient_free_disk")

    if archive.exists():
        return _compress_rejection_record(source, "archive_exists")

    if tmp.exists():
        if not cleanup_tmp:
            return _compress_rejection_record(source, "tmp_exists")
        tmp.unlink()

    source_sha256_before = _sha256_file(source)
    line_count_before = _count_lines(source)
    try:
        with source.open("rb") as src, gzip.open(tmp, "wb", compresslevel=6) as dst:
            shutil.copyfileobj(src, dst, length=COPY_BUFFER_BYTES)

        archive_sha256 = _sha256_file(tmp)
        decompressed_sha256, line_count_after = _gzip_sha256_and_line_count(tmp)
        if decompressed_sha256 != source_sha256_before:
            return _compress_rejection_record(source, "decompressed_sha256_mismatch")
        if line_count_after != line_count_before:
            return _compress_rejection_record(source, "line_count_mismatch")

        source_sha256_after = _sha256_file(source)
        if source_sha256_after != source_sha256_before:
            return _compress_rejection_record(source, "source_changed_during_compression")

        tmp.replace(archive)
        final_archive_sha256 = _sha256_file(archive)
        if final_archive_sha256 != archive_sha256:
            return _compress_rejection_record(source, "archive_sha256_mismatch_after_rename")

        source.unlink()
        return {
            "source_path": str(source),
            "archive_path": str(archive),
            "tmp_path": str(tmp),
            "algorithm": "gzip",
            "status": "compressed",
            "original_size_bytes": original_size,
            "archive_size_bytes": archive.stat().st_size,
            "source_sha256_before": source_sha256_before,
            "source_sha256_after": source_sha256_after,
            "archive_sha256": archive_sha256,
            "line_count_before": line_count_before,
            "line_count_after_decompress": line_count_after,
            "verified_before_source_remove": True,
            "source_removed": True,
            "timestamp_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    finally:
        if tmp.exists():
            tmp.unlink()


def _iter_compression_targets(
    runtime_root: Path,
    *,
    today: date,
    age_days: int,
    one_file: Path | None,
) -> Iterable[ScanEntry]:
    wanted = one_file.resolve() if one_file is not None else None
    found_one_file = False
    for path in _iter_existing_files(runtime_root):
        if wanted is not None and path.resolve() != wanted:
            continue
        found_one_file = True
        entry = _classify_file(path, runtime_root, today, age_days)
        yield entry
    if wanted is not None and not found_one_file:
        yield ScanEntry(one_file or Path(""), "missing_source")


def compress_candidates(
    *,
    runtime_root: str | Path = DEFAULT_RUNTIME_ROOT,
    manifest_root: str | Path = DEFAULT_COMPRESS_MANIFEST_ROOT,
    age_days: int,
    algorithm: str,
    today: date | None = None,
    max_files: int | None = None,
    one_file: str | Path | None = None,
    cleanup_tmp: bool = False,
    min_free_disk_bytes: int | None = None,
    write_manifest: bool = True,
) -> dict[str, Any]:
    runtime_root = Path(runtime_root)
    manifest_root = Path(manifest_root)
    today = today or _utc_now().date()
    one_file_path = Path(one_file) if one_file is not None else None

    if algorithm != "gzip":
        raise ValueError("--compress currently supports gzip only")
    if age_days < 1:
        raise ValueError("age_days must be >= 1")
    if max_files is not None and max_files < 1:
        raise ValueError("max_files must be >= 1")

    dry_run = build_dry_run_manifest(
        runtime_root=runtime_root,
        manifest_root=manifest_root,
        age_days=age_days,
        algorithm=algorithm,
        today=today,
        write_manifest=False,
    )
    manifest = {
        "schema_version": COMPRESS_MANIFEST_SCHEMA_VERSION,
        "timestamp_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "compress",
        "algorithm": algorithm,
        "age_days": age_days,
        "runtime_root": str(runtime_root),
        "dry_run_candidate_count": dry_run["summary"]["candidate_count"],
        "max_files": max_files,
        "one_file": str(one_file_path) if one_file_path is not None else "",
        "candidate_selection_source": "shared_scanner",
        "records": [],
        "exclusions": [],
        "summary": {},
    }
    manifest_path = _manifest_path(manifest_root, "compression_manifest")

    processed = 0
    for entry in _iter_compression_targets(runtime_root, today=today, age_days=age_days, one_file=one_file_path):
        if max_files is not None and processed >= max_files:
            break

        if entry.reason:
            record = _compress_rejection_record(entry.path, entry.reason)
        else:
            record = _compress_one_gzip(
                entry.path,
                cleanup_tmp=cleanup_tmp,
                min_free_disk_bytes=min_free_disk_bytes,
            )
        manifest["records"].append(record)
        processed += 1
        if write_manifest:
            _finalize_compress_summary(manifest)
            _write_json(manifest_path, manifest)

    _finalize_compress_summary(manifest)
    if write_manifest:
        _write_json(manifest_path, manifest)
        manifest["manifest_path"] = str(manifest_path)
        _write_json(manifest_path, manifest)
    return manifest


def _finalize_compress_summary(manifest: dict[str, Any]) -> None:
    records = manifest["records"]
    compressed = [record for record in records if record.get("status") == "compressed"]
    rejected = [record for record in records if record.get("status") == "rejected"]
    manifest["summary"] = {
        "record_count": len(records),
        "compressed_count": len(compressed),
        "rejected_count": len(rejected),
        "original_size_bytes": sum(record.get("original_size_bytes", 0) for record in compressed),
        "archive_size_bytes": sum(record.get("archive_size_bytes", 0) for record in compressed),
        "source_removed_count": sum(1 for record in compressed if record.get("source_removed") is True),
    }


def _restore_rejection_record(record: dict[str, Any], reason: str) -> dict[str, Any]:
    archive = Path(record.get("archive_path", ""))
    restore_path = Path(record.get("source_path", ""))
    return {
        "archive_path": str(archive),
        "restore_path": str(restore_path),
        "status": "rejected",
        "reason": reason,
        "timestamp_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _restore_one_gzip(
    record: dict[str, Any],
    *,
    allow_overwrite: bool,
    verify_only: bool,
    cleanup_tmp: bool,
) -> dict[str, Any]:
    if record.get("status") != "compressed":
        return _restore_rejection_record(record, "record_not_compressed")

    archive = Path(record["archive_path"])
    restore_path = Path(record["source_path"])
    tmp_restore = restore_path.with_name(restore_path.name + ".restore.tmp")

    if not archive.exists():
        return _restore_rejection_record(record, "archive_missing")
    if restore_path.exists() and not allow_overwrite:
        return _restore_rejection_record(record, "restore_path_exists")
    if tmp_restore.exists():
        if not cleanup_tmp:
            return _restore_rejection_record(record, "tmp_restore_exists")
        tmp_restore.unlink()

    archive_sha256_actual = _sha256_file(archive)
    if archive_sha256_actual != record.get("archive_sha256"):
        return _restore_rejection_record(record, "archive_sha256_mismatch")

    try:
        tmp_restore.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(archive, "rb") as src, tmp_restore.open("wb") as dst:
            shutil.copyfileobj(src, dst, length=COPY_BUFFER_BYTES)

        restored_sha256 = _sha256_file(tmp_restore)
        line_count_restored = _count_lines(tmp_restore)
        if restored_sha256 != record.get("source_sha256_before"):
            return _restore_rejection_record(record, "restored_sha256_mismatch")
        if line_count_restored != record.get("line_count_before"):
            return _restore_rejection_record(record, "line_count_mismatch")

        status = "verified" if verify_only else "restored"
        if verify_only:
            tmp_restore.unlink()
        else:
            tmp_restore.replace(restore_path)
            restored_sha256 = _sha256_file(restore_path)

        return {
            "archive_path": str(archive),
            "restore_path": str(restore_path),
            "tmp_restore_path": str(tmp_restore),
            "status": status,
            "archive_sha256_expected": record.get("archive_sha256", ""),
            "archive_sha256_actual": archive_sha256_actual,
            "restored_sha256": restored_sha256,
            "source_sha256_expected": record.get("source_sha256_before", ""),
            "line_count_expected": record.get("line_count_before", 0),
            "line_count_restored": line_count_restored,
            "overwrite_used": allow_overwrite,
            "verify_only": verify_only,
            "timestamp_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    finally:
        if tmp_restore.exists():
            tmp_restore.unlink()


def restore_from_manifest(
    *,
    manifest: dict[str, Any] | None = None,
    manifest_path: str | Path | None = None,
    report_root: str | Path = DEFAULT_RESTORE_MANIFEST_ROOT,
    max_files: int | None = None,
    one_file: str | Path | None = None,
    allow_overwrite: bool = False,
    verify_only: bool = False,
    cleanup_tmp: bool = False,
    write_report: bool = True,
) -> dict[str, Any]:
    if manifest is None:
        if manifest_path is None:
            raise ValueError("manifest or manifest_path is required")
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))

    if max_files is not None and max_files < 1:
        raise ValueError("max_files must be >= 1")

    wanted = Path(one_file).resolve() if one_file is not None else None
    report = {
        "schema_version": COMPRESS_MANIFEST_SCHEMA_VERSION,
        "timestamp_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "restore",
        "source_manifest_path": str(manifest_path or ""),
        "max_files": max_files,
        "one_file": str(one_file or ""),
        "verify_only": verify_only,
        "records": [],
        "summary": {},
    }
    report_path = _manifest_path(Path(report_root), "restore_manifest")

    processed = 0
    for record in manifest.get("records", []):
        if max_files is not None and processed >= max_files:
            break
        archive = Path(record.get("archive_path", ""))
        source = Path(record.get("source_path", ""))
        if wanted is not None and archive.resolve() != wanted and source.resolve() != wanted:
            continue

        restore_record = _restore_one_gzip(
            record,
            allow_overwrite=allow_overwrite,
            verify_only=verify_only,
            cleanup_tmp=cleanup_tmp,
        )
        report["records"].append(restore_record)
        processed += 1
        if write_report:
            _finalize_restore_summary(report)
            _write_json(report_path, report)

    _finalize_restore_summary(report)
    if write_report:
        _write_json(report_path, report)
        report["manifest_path"] = str(report_path)
        _write_json(report_path, report)
    return report


def _finalize_restore_summary(report: dict[str, Any]) -> None:
    records = report["records"]
    restored = [record for record in records if record.get("status") == "restored"]
    verified = [record for record in records if record.get("status") == "verified"]
    rejected = [record for record in records if record.get("status") == "rejected"]
    report["summary"] = {
        "record_count": len(records),
        "restored_count": len(restored),
        "verified_count": len(verified),
        "rejected_count": len(rejected),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run cold JSONL runtime storage compression planning.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Scan and write a compression dry-run manifest.")
    mode.add_argument("--compress", action="store_true", help="Compress selected cold JSONL files with gzip.")
    mode.add_argument("--restore", action="store_true", help="Restore gzip archives from a compression manifest.")
    parser.add_argument("--age-days", type=int, default=None, help="Only consider files at least this many days old.")
    parser.add_argument("--algorithm", choices=("gzip", "zstd"), default="gzip")
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT), help="Runtime root. Defaults to runtime/.")
    parser.add_argument(
        "--manifest-root",
        default=str(DEFAULT_MANIFEST_ROOT),
        help="Dry-run or compression manifest output directory.",
    )
    parser.add_argument("--manifest", default="", help="Compression manifest path for restore mode.")
    parser.add_argument("--max-files", type=int, default=None, help="Maximum files to compress or restore.")
    parser.add_argument("--one-file", default="", help="Restrict operation to one source or archive path.")
    parser.add_argument("--allow-overwrite", action="store_true", help="Allow restore to overwrite an existing JSONL file.")
    parser.add_argument("--verify-only", action="store_true", help="Verify restore integrity without recreating JSONL files.")
    parser.add_argument("--cleanup-tmp", action="store_true", help="Remove stale tool-owned tmp files before continuing.")
    parser.add_argument("--min-free-disk-bytes", type=int, default=None, help="Minimum free disk required before compression.")
    parser.add_argument("--report-root", default=str(DEFAULT_RESTORE_MANIFEST_ROOT), help="Restore report output directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    if args.dry_run and args.age_days is None:
        parser.error("--dry-run requires --age-days")

    if args.dry_run:
        manifest = build_dry_run_manifest(
            runtime_root=args.runtime_root,
            manifest_root=args.manifest_root,
            age_days=args.age_days,
            algorithm=args.algorithm,
            write_manifest=True,
        )
        summary = manifest["summary"]
        print("Runtime storage compression dry-run")
        print(f"algorithm: {manifest['algorithm']}")
        print(f"age_days: {manifest['age_days']}")
        print(f"candidate_count: {summary['candidate_count']}")
        print(f"exclusion_count: {summary['exclusion_count']}")
        print(f"total_expected_reclaim_bytes: {summary['total_expected_reclaim_bytes']}")
        print(f"manifest: {Path(args.manifest_root) / DEFAULT_MANIFEST_NAME}")
        return 0

    if args.compress:
        if args.algorithm != "gzip":
            parser.error("--compress currently supports --algorithm gzip only")
        if args.age_days is None:
            parser.error("--compress requires --age-days")
        if args.max_files is None:
            parser.error("--compress requires --max-files")
        manifest_root = Path(args.manifest_root)
        if manifest_root == DEFAULT_MANIFEST_ROOT:
            manifest_root = DEFAULT_COMPRESS_MANIFEST_ROOT
        manifest = compress_candidates(
            runtime_root=args.runtime_root,
            manifest_root=manifest_root,
            age_days=args.age_days,
            algorithm=args.algorithm,
            max_files=args.max_files,
            one_file=args.one_file or None,
            cleanup_tmp=args.cleanup_tmp,
            min_free_disk_bytes=args.min_free_disk_bytes,
            write_manifest=True,
        )
        summary = manifest["summary"]
        print("Runtime storage compression")
        print(f"algorithm: {manifest['algorithm']}")
        print(f"compressed_count: {summary['compressed_count']}")
        print(f"rejected_count: {summary['rejected_count']}")
        print(f"manifest: {manifest.get('manifest_path', '')}")
        return 0

    if args.restore:
        if not args.manifest:
            parser.error("--restore requires --manifest")
        report = restore_from_manifest(
            manifest_path=args.manifest,
            report_root=args.report_root,
            max_files=args.max_files,
            one_file=args.one_file or None,
            allow_overwrite=args.allow_overwrite,
            verify_only=args.verify_only,
            cleanup_tmp=args.cleanup_tmp,
            write_report=True,
        )
        summary = report["summary"]
        print("Runtime storage restore")
        print(f"restored_count: {summary['restored_count']}")
        print(f"verified_count: {summary['verified_count']}")
        print(f"rejected_count: {summary['rejected_count']}")
        print(f"manifest: {report.get('manifest_path', '')}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
