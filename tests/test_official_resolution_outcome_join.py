from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.official_resolution_outcome_join import join_official_outcomes


def _population_row(condition_id: str, epoch: int) -> dict:
    return {
        "condition_id": condition_id,
        "normalized_epoch_start_ts": epoch,
        "asset": "ETH",
        "market_slug": f"eth-updown-5m-{epoch}",
        "source_file": "2026-06-01.jsonl",
        "source_line": epoch,
        "decision_timestamp_utc": "2026-06-01T00:00:00Z",
        "model_probability_yes": 0.55,
        "frozen_probability_bucket": "[0.50,0.60)",
        "manifest_row_sha256": f"row-{epoch}",
    }


def _outcome_row(
    condition_id: str,
    epoch: int,
    *,
    status: str = "OFFICIAL_RESOLVED",
    outcome: str | None = "Up",
) -> dict:
    return {
        "condition_id": condition_id,
        "normalized_epoch_start_ts": epoch,
        "outcome_status": status,
        "terminal_outcome": outcome,
        "resolution_block_number": 100,
        "resolution_block_hash": "0xblock",
        "resolution_transaction_hash": "0xtx",
        "resolution_log_index": 1,
        "state_source_block_number": 100,
        "state_source_block_hash": "0xblock",
    }


def _write_json(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def _run(
    tmp_path: Path,
    population: list[dict],
    outcomes: list[dict],
    *,
    aggregate_status: str = "PASS",
) -> tuple[dict, bytes, bytes]:
    manifest = _write_json(
        tmp_path / "inputs" / "population.json",
        {"schema_version": "population_v1", "conditions": population},
    )
    rows = _write_jsonl(tmp_path / "inputs" / "outcome_rows.jsonl", outcomes)
    aggregate = _write_json(
        tmp_path / "inputs" / "aggregate.json",
        {"status": aggregate_status, "committed_conditions": len(outcomes)},
    )
    output = tmp_path / "output"
    report = join_official_outcomes(
        population_manifest=manifest,
        outcome_rows=rows,
        aggregate_verification=aggregate,
        output_dir=output,
    )
    return (
        report,
        (output / "joined_official_outcomes.jsonl").read_bytes(),
        (output / "outcome_join_report.json").read_bytes(),
    )


def test_exact_join_passes_and_reports_direct_coverage(tmp_path: Path) -> None:
    report, joined_bytes, _ = _run(
        tmp_path,
        [_population_row("0xaaa", 1)],
        [_outcome_row("0xAAA", 1)],
    )
    joined = [json.loads(line) for line in joined_bytes.splitlines()]

    assert report["status"] == "PASS"
    assert report["eligible_population"] == 1
    assert report["joined_rows"] == 1
    assert report["direct_join_coverage"] == 1.0
    assert joined[0]["join_status"] == "JOINED_OFFICIAL_RESOLVED"
    assert joined[0]["terminal_outcome"] == "Up"
    assert joined[0]["model_probability_yes"] == 0.55
    assert joined[0]["frozen_probability_bucket"] == "[0.50,0.60)"


def test_deterministic_output_and_hash_across_repeated_runs(tmp_path: Path) -> None:
    population = [_population_row("0xbbb", 2), _population_row("0xaaa", 1)]
    outcomes = [_outcome_row("0xaaa", 1), _outcome_row("0xbbb", 2)]
    first, first_joined, first_report = _run(tmp_path / "first", population, outcomes)
    second, second_joined, second_report = _run(tmp_path / "second", population, outcomes)

    assert first_joined == second_joined
    assert first_report == second_report
    assert first == second
    assert first["joined_output_sha256"] == hashlib.sha256(first_joined).hexdigest()


def test_epoch_mismatch_is_rejected(tmp_path: Path) -> None:
    report, joined, _ = _run(
        tmp_path,
        [_population_row("0xaaa", 1)],
        [_outcome_row("0xaaa", 2)],
    )

    assert report["status"] == "FAIL"
    assert report["excluded_rows"]["epoch_mismatch"] == 1
    assert joined == b""


def test_duplicate_identical_outcome_rows_are_rejected(tmp_path: Path) -> None:
    row = _outcome_row("0xaaa", 1)
    report, joined, _ = _run(tmp_path, [_population_row("0xaaa", 1)], [row, row])

    assert report["status"] == "FAIL"
    assert report["duplicate_rows"] == 1
    assert report["excluded_rows"]["duplicate_outcome_rows"] == 1
    assert joined == b""


def test_conflicting_outcomes_are_rejected(tmp_path: Path) -> None:
    report, joined, _ = _run(
        tmp_path,
        [_population_row("0xaaa", 1)],
        [_outcome_row("0xaaa", 1, outcome="Up"), _outcome_row("0xaaa", 1, outcome="Down")],
    )

    assert report["status"] == "FAIL"
    assert report["conflicting_rows"] == 2
    assert report["excluded_rows"]["conflicting_outcomes"] == 1
    assert joined == b""


def test_ambiguous_mapping_is_rejected(tmp_path: Path) -> None:
    report, joined, _ = _run(
        tmp_path,
        [_population_row("0xaaa", 1)],
        [_outcome_row("0xaaa", 1, status="AMBIGUOUS_MAPPING", outcome=None)],
    )

    assert report["status"] == "FAIL"
    assert report["ambiguous_rows"] == 1
    assert report["excluded_rows"]["ambiguous_mapping"] == 1
    assert joined == b""


def test_unverified_aggregate_rejects_all_rows(tmp_path: Path) -> None:
    report, joined, _ = _run(
        tmp_path,
        [_population_row("0xaaa", 1)],
        [_outcome_row("0xaaa", 1)],
        aggregate_status="FAIL",
    )

    assert report["status"] == "FAIL"
    assert report["excluded_rows"]["unverified_package_population"] == 1
    assert joined == b""


def test_missing_condition_is_reported(tmp_path: Path) -> None:
    report, _, _ = _run(
        tmp_path,
        [_population_row("0xaaa", 1), _population_row("0xbbb", 2)],
        [_outcome_row("0xaaa", 1)],
    )

    assert report["status"] == "FAIL"
    assert report["missing_conditions"] == ["0xbbb"]
    assert report["excluded_rows"]["missing_condition"] == 1


def test_unexpected_condition_is_reported(tmp_path: Path) -> None:
    report, _, _ = _run(
        tmp_path,
        [_population_row("0xaaa", 1)],
        [_outcome_row("0xaaa", 1), _outcome_row("0xbbb", 2)],
    )

    assert report["status"] == "FAIL"
    assert report["unexpected_conditions"] == ["0xbbb"]
    assert report["excluded_rows"]["unexpected_condition"] == 1


def test_unresolved_outcome_is_preserved_without_counting_as_direct_join(tmp_path: Path) -> None:
    report, joined_bytes, _ = _run(
        tmp_path,
        [_population_row("0xaaa", 1)],
        [_outcome_row("0xaaa", 1, status="OFFICIAL_UNRESOLVED", outcome=None)],
    )
    joined = json.loads(joined_bytes)

    assert report["status"] == "PASS"
    assert report["unresolved_rows"] == 1
    assert report["joined_rows"] == 0
    assert report["direct_join_coverage"] == 0.0
    assert joined["join_status"] == "UNRESOLVED"
    assert joined["terminal_outcome"] is None


def test_outcome_rows_directory_is_read_deterministically(tmp_path: Path) -> None:
    population = [_population_row("0xaaa", 1), _population_row("0xbbb", 2)]
    manifest = _write_json(tmp_path / "population.json", {"conditions": population})
    rows_dir = tmp_path / "packages"
    _write_jsonl(rows_dir / "b" / "outcome_rows.jsonl", [_outcome_row("0xbbb", 2)])
    _write_jsonl(rows_dir / "a" / "outcome_rows.jsonl", [_outcome_row("0xaaa", 1)])
    aggregate = _write_json(tmp_path / "aggregate.json", {"status": "PASS"})
    output = tmp_path / "output"

    report = join_official_outcomes(
        population_manifest=manifest,
        outcome_rows=rows_dir,
        aggregate_verification=aggregate,
        output_dir=output,
    )

    assert report["status"] == "PASS"
    assert report["outcome_source_files"] == [
        "a/outcome_rows.jsonl",
        "b/outcome_rows.jsonl",
    ]


def test_repeated_run_in_same_output_directory_is_identical(tmp_path: Path) -> None:
    population = [_population_row("0xaaa", 1)]
    outcomes = [_outcome_row("0xaaa", 1)]
    first = _run(tmp_path, population, outcomes)
    second = _run(tmp_path, population, outcomes)

    assert first == second
