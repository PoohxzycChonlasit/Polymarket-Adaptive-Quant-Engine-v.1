from __future__ import annotations

import argparse
import gzip
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MANIFEST_SCHEMA_VERSION = "1.0"
DEFAULT_RUNTIME_ROOT = Path("runtime")
DEFAULT_MANIFEST_ROOT = DEFAULT_RUNTIME_ROOT / "storage_manifests" / "dry_run"
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


@dataclass(frozen=True)
class ScanEntry:
    path: Path
    reason: str = ""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run cold JSONL runtime storage compression planning.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Scan and write a compression dry-run manifest.")
    mode.add_argument("--compress", action="store_true", help="Reserved for a future explicitly approved compression task.")
    mode.add_argument("--restore", action="store_true", help="Reserved for a future explicitly approved restore task.")
    parser.add_argument("--age-days", type=int, required=True, help="Only consider files at least this many days old.")
    parser.add_argument("--algorithm", choices=("gzip", "zstd"), required=True)
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT), help="Runtime root. Defaults to runtime/.")
    parser.add_argument(
        "--manifest-root",
        default=str(DEFAULT_MANIFEST_ROOT),
        help="Dry-run manifest output directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    if args.compress:
        parser.error("--compress is not implemented in this dry-run-first tool.")
    if args.restore:
        parser.error("--restore is not implemented in this dry-run-first tool.")

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


if __name__ == "__main__":
    raise SystemExit(main())
