from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

import tools.runtime_storage_compressor as compressor
from tools.runtime_storage_compressor import (
    MANIFEST_SCHEMA_VERSION,
    build_dry_run_manifest,
    main,
)


def _write(path: Path, text: str = "{\"ok\": true}\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _manifest(root: Path, *, today: date = date(2026, 6, 22), age_days: int = 7) -> dict:
    return build_dry_run_manifest(
        runtime_root=root / "runtime",
        manifest_root=root / "runtime" / "storage_manifests" / "dry_run",
        age_days=age_days,
        algorithm="gzip",
        today=today,
        write_manifest=False,
    )


def test_current_utc_day_is_excluded(tmp_path: Path) -> None:
    current = tmp_path / "runtime" / "quant_data" / "decision_log" / "2026-06-22.jsonl"
    old = tmp_path / "runtime" / "quant_data" / "decision_log" / "2026-06-14.jsonl"
    _write(current)
    _write(old)

    manifest = _manifest(tmp_path)

    candidate_paths = {item["path"] for item in manifest["candidates"]}
    assert str(old) in candidate_paths
    assert str(current) not in candidate_paths
    assert any(item["path"] == str(current) and item["reason"] == "current_utc_day" for item in manifest["exclusions"])


def test_protected_folders_are_excluded(tmp_path: Path) -> None:
    trade = tmp_path / "runtime" / "quant_data" / "trade_journal" / "2026-06-14.jsonl"
    snapshot = tmp_path / "runtime" / "quant_data" / "reports" / "phase_b_daily_snapshots" / "2026-06-14.jsonl"
    target = tmp_path / "runtime" / "quant_data" / "risk_log" / "2026-06-14.jsonl"
    _write(trade)
    _write(snapshot)
    _write(target)

    manifest = _manifest(tmp_path)

    candidate_paths = {item["path"] for item in manifest["candidates"]}
    assert str(target) in candidate_paths
    assert str(trade) not in candidate_paths
    assert str(snapshot) not in candidate_paths
    assert any(item["path"] == str(trade) and item["reason"] == "protected_folder" for item in manifest["exclusions"])
    assert any(item["path"] == str(snapshot) and item["reason"] == "protected_folder" for item in manifest["exclusions"])


def test_only_jsonl_targets_and_compressed_files_are_excluded(tmp_path: Path) -> None:
    jsonl = tmp_path / "runtime" / "quant_data" / "research_log" / "2026-06-14.jsonl"
    text = tmp_path / "runtime" / "quant_data" / "research_log" / "2026-06-14.txt"
    gzip_file = tmp_path / "runtime" / "quant_data" / "research_log" / "2026-06-13.jsonl.gz"
    zstd_file = tmp_path / "runtime" / "quant_data" / "research_log" / "2026-06-12.jsonl.zst"
    _write(jsonl)
    _write(text)
    _write(gzip_file)
    _write(zstd_file)

    manifest = _manifest(tmp_path)

    candidate_paths = {item["path"] for item in manifest["candidates"]}
    exclusions = {(item["path"], item["reason"]) for item in manifest["exclusions"]}
    assert str(jsonl) in candidate_paths
    assert (str(text), "non_jsonl") in exclusions
    assert (str(gzip_file), "already_compressed") in exclusions
    assert (str(zstd_file), "already_compressed") in exclusions


def test_age_days_excludes_recent_non_current_files(tmp_path: Path) -> None:
    recent = tmp_path / "runtime" / "quant_data" / "market_snapshots" / "2026-06-20.jsonl"
    old = tmp_path / "runtime" / "quant_data" / "market_snapshots" / "2026-06-14.jsonl"
    _write(recent)
    _write(old)

    manifest = _manifest(tmp_path, today=date(2026, 6, 22), age_days=7)

    candidate_paths = {item["path"] for item in manifest["candidates"]}
    assert str(old) in candidate_paths
    assert str(recent) not in candidate_paths
    assert any(item["path"] == str(recent) and item["reason"] == "younger_than_age_days" for item in manifest["exclusions"])


def test_dry_run_does_not_modify_files_and_writes_manifest(tmp_path: Path) -> None:
    target = tmp_path / "runtime" / "quant_data" / "decision_log" / "2026-06-14.jsonl"
    original = "{\"payload\":\"" + ("abc" * 100) + "\"}\n"
    _write(target, original)
    before_bytes = target.read_bytes()

    manifest_root = tmp_path / "runtime" / "storage_manifests" / "dry_run"
    manifest = build_dry_run_manifest(
        runtime_root=tmp_path / "runtime",
        manifest_root=manifest_root,
        age_days=7,
        algorithm="gzip",
        today=date(2026, 6, 22),
        write_manifest=True,
    )

    assert target.read_bytes() == before_bytes
    assert target.exists()
    manifest_path = manifest_root / "compression_dry_run_manifest_001.json"
    assert manifest_path.exists()
    written = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert written == manifest


def test_expected_savings_and_manifest_schema_are_valid(tmp_path: Path) -> None:
    target = tmp_path / "runtime" / "quant_data" / "decision_log" / "2026-06-14.jsonl"
    _write(target, "{\"payload\":\"" + ("abc" * 1000) + "\"}\n")

    manifest = _manifest(tmp_path)
    candidate = manifest["candidates"][0]

    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["mode"] == "dry_run"
    assert manifest["age_days"] == 7
    assert manifest["algorithm"] == "gzip"
    assert isinstance(manifest["timestamp_utc"], str)
    assert candidate["original_size_bytes"] > 0
    assert candidate["estimated_compressed_size_bytes"] > 0
    assert candidate["estimated_savings_bytes"] == (
        candidate["original_size_bytes"] - candidate["estimated_compressed_size_bytes"]
    )
    assert manifest["summary"]["candidate_count"] == 1
    assert manifest["summary"]["total_expected_reclaim_bytes"] == candidate["estimated_savings_bytes"]
    assert manifest["summary"]["top_20_candidates_by_size"][0]["path"] == str(target)


def test_large_file_estimation_uses_bounded_sample(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "runtime" / "quant_data" / "decision_log" / "2026-06-14.jsonl"
    oversized = b"a" * (compressor.MAX_EXACT_ESTIMATE_BYTES + 1024)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(oversized)
    compressed_input_sizes: list[int] = []

    def fake_compress(data: bytes) -> bytes:
        compressed_input_sizes.append(len(data))
        return b"x" * max(1, len(data) // 2)

    monkeypatch.setattr(compressor.gzip, "compress", fake_compress)

    manifest = _manifest(tmp_path)
    candidate = manifest["candidates"][0]

    assert compressed_input_sizes
    assert compressed_input_sizes[0] < len(oversized)
    assert candidate["estimate_method"] == "sampled"
    assert candidate["original_size_bytes"] == len(oversized)


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
    assert record["line_count_restored"] == manifest["records"][0]["line_count_before"]


def test_verify_only_restore_validates_without_recreating_jsonl(tmp_path: Path) -> None:
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
    archive = source.with_name(source.name + ".gz")

    restore_report = compressor.restore_from_manifest(
        manifest=manifest,
        max_files=1,
        allow_overwrite=False,
        verify_only=True,
    )

    assert not source.exists()
    assert archive.exists()
    assert not source.with_name(source.name + ".restore.tmp").exists()
    assert restore_report["records"][0]["status"] == "verified"


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
    assert source.read_text(encoding="utf-8") == "existing replacement\n"


def test_compress_manifest_schema_is_valid(tmp_path: Path) -> None:
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

    assert manifest["schema_version"] == "2.0"
    assert manifest["mode"] == "compress"
    assert manifest["algorithm"] == "gzip"
    assert manifest["summary"]["compressed_count"] == 1
    assert manifest["summary"]["rejected_count"] == 0
    assert manifest["records"][0]["archive_sha256"]
    assert manifest["records"][0]["source_sha256_before"]


def test_compress_still_excludes_current_day(tmp_path: Path) -> None:
    source = tmp_path / "runtime" / "quant_data" / "risk_log" / "2026-06-22.jsonl"
    _write(source, "{\"a\":1}\n")

    manifest = compressor.compress_candidates(
        runtime_root=tmp_path / "runtime",
        manifest_root=tmp_path / "runtime" / "storage_manifests" / "compress",
        age_days=1,
        algorithm="gzip",
        today=date(2026, 6, 22),
        max_files=1,
        one_file=source,
    )

    assert source.exists()
    assert not source.with_name(source.name + ".gz").exists()
    assert manifest["records"][0]["status"] == "rejected"
    assert manifest["records"][0]["reason"] == "current_utc_day"


def test_compress_cli_requires_max_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main([
            "--compress",
            "--age-days",
            "7",
            "--algorithm",
            "gzip",
            "--runtime-root",
            str(tmp_path / "runtime"),
        ])
    assert exc.value.code == 2
    assert "max-files" in capsys.readouterr().err.lower()


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

    result = main([
        "--restore",
        "--manifest",
        str(manifest_path),
        "--max-files",
        "1",
    ])

    assert result == 0
    assert source.exists()
