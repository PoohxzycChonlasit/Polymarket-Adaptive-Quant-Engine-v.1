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


def test_compress_and_restore_modes_are_safe_stubs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as compress_exit:
        main(["--compress", "--age-days", "7", "--algorithm", "gzip", "--runtime-root", str(tmp_path / "runtime")])
    assert compress_exit.value.code == 2
    assert "not implemented" in capsys.readouterr().err.lower()

    with pytest.raises(SystemExit) as restore_exit:
        main(["--restore", "--age-days", "7", "--algorithm", "gzip", "--runtime-root", str(tmp_path / "runtime")])
    assert restore_exit.value.code == 2
    assert "not implemented" in capsys.readouterr().err.lower()
