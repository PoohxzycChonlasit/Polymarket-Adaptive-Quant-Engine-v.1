from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.outcome_truth.free_outcome_truth_provisional_join import (
    ProvisionalJoinError,
    join_provisional_outcomes,
)


def _population(condition_id: str, epoch: int) -> dict:
    return {
        "condition_id": condition_id,
        "normalized_epoch_start_ts": epoch,
        "asset": "ETH",
        "market_slug": f"eth-updown-5m-{epoch}",
        "model_probability_yes": 0.55,
        "frozen_probability_bucket": "[0.50,0.60)",
        "manifest_row_sha256": f"manifest-{epoch}",
    }


def _outcome(condition_id: str, epoch: int, classification: str = "PROVISIONAL_RESOLVED") -> dict:
    return {
        "condition_id": condition_id,
        "normalized_epoch_start_ts": epoch,
        "classification": classification,
        "terminal_outcome": "YES" if "RESOLVED" in classification else None,
        "row_sha256": f"outcome-{epoch}",
        "source_classes": {"gamma": "PROVISIONAL_PLATFORM_METADATA"},
        "authority_class": "PROVISIONAL_PLATFORM_METADATA",
        "historical_provenance_status": "NOT_APPLICABLE",
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


def _run(tmp_path: Path, population: list[dict], outcomes: list[dict]) -> tuple[dict, bytes]:
    manifest = _write_json(tmp_path / "population.json", {"conditions": population})
    outcome_path = _write_jsonl(tmp_path / "outcomes.jsonl", outcomes)
    report = join_provisional_outcomes(
        population_manifest=manifest,
        provisional_outcomes=outcome_path,
        output_dir=tmp_path / "output",
    )
    return report, (tmp_path / "output" / "provisional_joined_outcomes.jsonl").read_bytes()


def test_join_is_deterministic_and_preserves_diagnostic_authority(tmp_path: Path) -> None:
    population = [_population("0xbbb", 2), _population("0xaaa", 1)]
    outcomes = [_outcome("0xaaa", 1), _outcome("0xbbb", 2, "OFFICIAL_FREE_RESOLVED")]

    first, first_bytes = _run(tmp_path / "first", population, outcomes)
    second, second_bytes = _run(tmp_path / "second", list(reversed(population)), list(reversed(outcomes)))
    joined = [json.loads(line) for line in first_bytes.splitlines()]

    assert first == second
    assert first_bytes == second_bytes
    assert first["output_sha256"] == hashlib.sha256(first_bytes).hexdigest()
    assert all(row["allowed_use"] == "PROVISIONAL_DIAGNOSTIC" for row in joined)
    assert all(row["official_pass_fail_allowed"] is False for row in joined)


def test_missing_provisional_row_is_preserved_as_unresolved(tmp_path: Path) -> None:
    report, joined_bytes = _run(tmp_path, [_population("0xaaa", 1)], [])
    joined = json.loads(joined_bytes)

    assert report["missing_rows"] == 1
    assert joined["classification"] == "UNRESOLVED"


def test_duplicate_identity_fails_closed(tmp_path: Path) -> None:
    row = _outcome("0xaaa", 1)
    with pytest.raises(ProvisionalJoinError, match="duplicate"):
        _run(tmp_path, [_population("0xaaa", 1)], [row, row])
