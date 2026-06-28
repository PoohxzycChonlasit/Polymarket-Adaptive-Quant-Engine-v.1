from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from tools.outcome_truth_population_manifest import (
    PopulationManifestError,
    generate_population_manifest,
)


def _event(
    condition_id: str | None,
    epoch: int | None,
    *,
    timestamp: str = "2026-06-01T00:00:00Z",
    model_ready: bool = True,
    model_probability_yes: float | None = 0.55,
    aliases: dict | None = None,
) -> dict:
    payload = {
        "condition_id": condition_id,
        "epoch_start": epoch,
        "asset": "ETH",
        "market_slug": f"eth-updown-5m-{epoch}",
        "model_output_ready": model_ready,
        "decision_timestamp": timestamp,
    }
    if model_probability_yes is not None and model_ready:
        payload["model_probability_yes"] = model_probability_yes
    payload.update(aliases or {})
    return {
        "timestamp_utc": timestamp,
        "event_type": "decision",
        "payload": payload,
    }


def _write_jsonl(path: Path, rows: list[dict | str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write((row if isinstance(row, str) else json.dumps(row)) + "\n")


def _run(tmp_path: Path, rows: list[dict | str], quarantine: dict | None = None) -> tuple[dict, bytes, bytes]:
    source_dir = tmp_path / "decision_log"
    _write_jsonl(source_dir / "2026-06-01.jsonl", rows)
    quarantine_path = tmp_path / "quarantine.json"
    quarantine_path.write_text(json.dumps(quarantine or {"rows": []}), encoding="utf-8")
    output_dir = tmp_path / "output"
    report = generate_population_manifest(
        source_dir=source_dir,
        quarantine_inventory=quarantine_path,
        output_dir=output_dir,
    )
    return (
        report,
        (output_dir / "population_manifest.json").read_bytes(),
        (output_dir / "population_manifest_report.json").read_bytes(),
    )


def test_deterministic_output_and_hash_across_repeated_runs(tmp_path: Path) -> None:
    rows = [
        _event("0xbbb", 2, timestamp="2026-06-01T00:00:02Z"),
        _event("0xaaa", 1, timestamp="2026-06-01T00:00:01Z"),
    ]
    first_report, first_manifest, first_report_bytes = _run(tmp_path / "first", rows)
    second_report, second_manifest, second_report_bytes = _run(tmp_path / "second", rows)

    assert first_manifest == second_manifest
    assert first_report_bytes == second_report_bytes
    assert first_report["manifest_sha256"] == hashlib.sha256(first_manifest).hexdigest()
    assert first_report == second_report


def test_duplicate_units_keep_earliest_model_ready_observation(tmp_path: Path) -> None:
    rows = [
        _event("0xaaa", 1, timestamp="2026-06-01T00:00:05Z"),
        _event("0xaaa", 1, timestamp="2026-06-01T00:00:01Z"),
        _event("0xaaa", 1, timestamp="2026-06-01T00:00:00Z", model_ready=False),
    ]
    report, manifest_bytes, _ = _run(tmp_path, rows)
    manifest = json.loads(manifest_bytes)

    assert report["model_ready_rows"] == 2
    assert report["unique_condition_epoch_units"] == 1
    assert report["excluded_rows"]["duplicate_model_ready_unit"] == 1
    assert manifest["conditions"][0]["source_line"] == 2
    assert manifest["conditions"][0]["decision_timestamp_utc"] == "2026-06-01T00:00:01Z"


def test_earliest_selection_compares_timestamp_value_not_text(tmp_path: Path) -> None:
    rows = [
        _event("0xaaa", 1, timestamp="2026-06-01T00:00:00.100000Z"),
        _event("0xaaa", 1, timestamp="2026-06-01T00:00:00Z"),
    ]
    _, manifest_bytes, _ = _run(tmp_path, rows)

    assert json.loads(manifest_bytes)["conditions"][0]["source_line"] == 2


def test_epoch_aliases_normalize_to_one_integer(tmp_path: Path) -> None:
    row = _event(
        "0xaaa",
        None,
        aliases={"epoch_start_ts": "123", "market_epoch_start": 123.0},
    )
    _, manifest_bytes, _ = _run(tmp_path, [row])

    assert json.loads(manifest_bytes)["conditions"][0]["normalized_epoch_start_ts"] == 123


def test_matching_quarantine_row_is_skipped_and_disclosed(tmp_path: Path) -> None:
    malformed = '{"broken":'
    digest = hashlib.sha256(malformed.encode("utf-8")).hexdigest()
    quarantine = {
        "rows": [
            {
                "source_file": "2026-06-01.jsonl",
                "line_number": 2,
                "sha256": digest,
                "classification": "WRITER_INTERRUPTION_ARTIFACT",
            }
        ],
        "known_lost_events": 23,
        "unknown_events": 1,
        "maximum_possible_denominator_error": 24,
        "affected_files": ["2026-05-21.jsonl"],
        "materiality_classification": "LOW",
    }
    report, _, _ = _run(tmp_path, [_event("0xaaa", 1), malformed], quarantine)

    assert report["raw_rows"] == 2
    assert report["valid_rows"] == 1
    assert report["malformed_rows"] == 1
    assert report["quarantined_rows"] == 1
    assert report["loss_bound_disclosure"]["known_lost_events"] == 23


def test_quarantine_accepts_sha256_of_raw_line_with_newline(tmp_path: Path) -> None:
    malformed = '{"broken":'
    quarantine = {
        "rows": [
            {
                "source_file": "2026-06-01.jsonl",
                "line_number": 2,
                "sha256": hashlib.sha256((malformed + "\n").encode("utf-8")).hexdigest(),
            }
        ]
    }

    report, _, _ = _run(tmp_path, [_event("0xaaa", 1), malformed], quarantine)

    assert report["quarantined_rows"] == 1


def test_unapproved_malformed_row_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(PopulationManifestError, match="unapproved malformed JSON"):
        _run(tmp_path, [_event("0xaaa", 1), '{"broken":'])


def test_missing_condition_id_fails_closed_for_model_ready_row(tmp_path: Path) -> None:
    with pytest.raises(PopulationManifestError, match="missing condition_id"):
        _run(tmp_path, [_event(None, 1)])


def test_ambiguous_epoch_aliases_fail_closed(tmp_path: Path) -> None:
    row = _event("0xaaa", 1, aliases={"epoch_start_ts": 2})

    with pytest.raises(PopulationManifestError, match="ambiguous epoch"):
        _run(tmp_path, [row])


def test_non_model_ready_rows_are_excluded_without_identity_failure(tmp_path: Path) -> None:
    report, manifest_bytes, _ = _run(tmp_path, [_event(None, None, model_ready=False)])

    assert json.loads(manifest_bytes)["conditions"] == []
    assert report["excluded_rows"]["not_model_ready"] == 1


def test_manifest_rows_contain_required_fields_and_stable_row_hash(tmp_path: Path) -> None:
    report, manifest_bytes, _ = _run(tmp_path, [_event("0xAAA", 1)])
    row = json.loads(manifest_bytes)["conditions"][0]

    assert set(row) == {
        "condition_id",
        "normalized_epoch_start_ts",
        "asset",
        "market_slug",
        "source_file",
        "source_line",
        "decision_timestamp_utc",
        "model_probability_yes",
        "frozen_probability_bucket",
        "manifest_row_sha256",
    }
    unhashed = {key: value for key, value in row.items() if key != "manifest_row_sha256"}
    encoded = json.dumps(unhashed, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert row["condition_id"] == "0xaaa"
    assert row["model_probability_yes"] == 0.55
    assert row["frozen_probability_bucket"] == "[0.50,0.60)"
    assert row["manifest_row_sha256"] == hashlib.sha256(encoded).hexdigest()
    assert report["unique_conditions"] == 1


def test_model_probability_and_bucket_are_preserved_deterministically(tmp_path: Path) -> None:
    rows = [
        _event("0xaaa", 1, model_probability_yes=0.0),
        _event("0xbbb", 2, model_probability_yes=0.999),
        _event("0xccc", 3, model_probability_yes=1.0),
    ]

    _, first_bytes, _ = _run(tmp_path / "first", rows)
    _, second_bytes, _ = _run(tmp_path / "second", rows)
    conditions = json.loads(first_bytes)["conditions"]

    assert first_bytes == second_bytes
    assert [(row["model_probability_yes"], row["frozen_probability_bucket"]) for row in conditions] == [
        (0.0, "[0.00,0.10)"),
        (0.999, "[0.90,1.00]"),
        (1.0, "[0.90,1.00]"),
    ]


def test_model_ready_row_without_probability_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(PopulationManifestError, match="model_probability_yes"):
        _run(tmp_path, [_event("0xaaa", 1, model_probability_yes=None)])


def test_source_jsonl_is_streamed_without_whole_file_loading() -> None:
    import tools.outcome_truth_population_manifest as target_module
    source = Path(target_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    attributes = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]

    assert "readlines" not in attributes
    assert "read_text" not in attributes
    assert "read_bytes" not in attributes
    assert "list(file" not in source
