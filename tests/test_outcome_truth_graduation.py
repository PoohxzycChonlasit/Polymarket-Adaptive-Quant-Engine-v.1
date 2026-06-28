from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.outcome_truth.outcome_truth_graduation import GraduationError, graduate_outcome_truth


BUCKETS = ["[0.00,0.10)", "[0.10,0.20)", "[0.90,1.00]"]


def _joined(index: int, bucket: str, *, resolved: bool = True) -> dict:
    return {
        "condition_id": f"0x{index:064x}",
        "normalized_epoch_start_ts": index,
        "frozen_probability_bucket": bucket,
        "join_status": "JOINED_OFFICIAL_RESOLVED" if resolved else "UNRESOLVED",
        "outcome_status": "OFFICIAL_RESOLVED" if resolved else "OFFICIAL_UNRESOLVED",
        "terminal_outcome": "Up" if resolved else None,
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


def _write_spec(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Frozen Calibration Spec",
                "Status: FROZEN CANDIDATE SPECIFICATION",
                f"probability_buckets: {','.join(BUCKETS)}",
                "fingerprint_hash: " + "a" * 64,
            ]
        ),
        encoding="utf-8",
    )
    return path


def _rows(resolved: int, unresolved: int, *, buckets: list[str] = BUCKETS) -> list[dict]:
    rows = []
    for index in range(resolved + unresolved):
        rows.append(
            _joined(
                index,
                buckets[index % len(buckets)],
                resolved=index < resolved,
            )
        )
    return rows


def _run(
    tmp_path: Path,
    rows: list[dict],
    *,
    eligible: int | None = None,
    conflicts: int = 0,
    ambiguous: int = 0,
    join_status: str = "PASS",
    loss_bound: dict | None = None,
) -> tuple[dict, bytes, bytes]:
    eligible = len(rows) if eligible is None else eligible
    resolved = sum(row["join_status"] == "JOINED_OFFICIAL_RESOLVED" for row in rows)
    unresolved = sum(row["join_status"] == "UNRESOLVED" for row in rows)
    joined_path = _write_jsonl(tmp_path / "inputs" / "joined.jsonl", rows)
    join_report = _write_json(
        tmp_path / "inputs" / "join_report.json",
        {
            "status": join_status,
            "eligible_population": eligible,
            "joined_rows": resolved,
            "unresolved_rows": unresolved,
            "conflicting_rows": conflicts,
            "ambiguous_rows": ambiguous,
        },
    )
    spec = _write_spec(tmp_path / "inputs" / "spec.md")
    loss = _write_json(
        tmp_path / "inputs" / "loss.json",
        loss_bound
        or {
            "known_lost_events": 0,
            "unknown_events": 0,
            "maximum_possible_denominator_error": 0,
        },
    )
    output = tmp_path / "output"
    report = graduate_outcome_truth(
        joined_outcomes=joined_path,
        outcome_join_report=join_report,
        calibration_spec=spec,
        loss_bound_evidence=loss,
        output_dir=output,
    )
    return (
        report,
        (output / "outcome_truth_coverage_report.json").read_bytes(),
        (output / "outcome_truth_graduation_report.json").read_bytes(),
    )


def test_coverage_below_90_percent_fails(tmp_path: Path) -> None:
    report, _, _ = _run(tmp_path, _rows(89, 11))

    assert report["verdict"] == "OUTCOME_TRUTH_NOT_READY"
    assert report["gates"]["overall_coverage_gte_90pct"] is False


def test_bucket_coverage_delta_above_10pp_fails(tmp_path: Path) -> None:
    rows = [_joined(i, BUCKETS[0], resolved=i < 10) for i in range(10)]
    rows += [_joined(i + 10, BUCKETS[1], resolved=i < 8) for i in range(10)]
    report, _, _ = _run(tmp_path, rows)

    assert report["verdict"] == "OUTCOME_TRUTH_NOT_READY"
    assert report["max_bucket_coverage_delta_pp"] == 20.0
    assert report["gates"]["bucket_delta_lte_10pp"] is False


def test_conflicts_fail(tmp_path: Path) -> None:
    report, _, _ = _run(tmp_path, _rows(10, 0), conflicts=1)

    assert report["verdict"] == "OUTCOME_TRUTH_NOT_READY"
    assert report["gates"]["zero_conflicts"] is False


def test_ambiguous_mappings_fail(tmp_path: Path) -> None:
    report, _, _ = _run(tmp_path, _rows(10, 0), ambiguous=1)

    assert report["verdict"] == "OUTCOME_TRUTH_NOT_READY"
    assert report["gates"]["zero_ambiguous_included_mappings"] is False


def test_missing_frozen_spec_fails_closed(tmp_path: Path) -> None:
    joined = _write_jsonl(tmp_path / "joined.jsonl", _rows(10, 0))
    join_report = _write_json(
        tmp_path / "join.json",
        {"status": "PASS", "eligible_population": 10, "joined_rows": 10, "unresolved_rows": 0},
    )
    loss = _write_json(tmp_path / "loss.json", {"maximum_possible_denominator_error": 0})

    with pytest.raises(GraduationError, match="frozen calibration specification"):
        graduate_outcome_truth(
            joined_outcomes=joined,
            outcome_join_report=join_report,
            calibration_spec=tmp_path / "missing.md",
            loss_bound_evidence=loss,
            output_dir=tmp_path / "output",
        )


def test_loss_bound_worst_case_recalculation_can_fail_graduation(tmp_path: Path) -> None:
    report, _, _ = _run(
        tmp_path,
        _rows(100, 0),
        loss_bound={
            "known_lost_events": 23,
            "unknown_events": 1,
            "maximum_possible_denominator_error": 24,
        },
    )

    assert report["direct_outcome_coverage"] == 1.0
    assert report["worst_case_direct_outcome_coverage"] == pytest.approx(100 / 124)
    assert report["gates"]["worst_case_coverage_gte_90pct"] is False
    assert report["verdict"] == "OUTCOME_TRUTH_NOT_READY"


def test_passing_fixture_graduates(tmp_path: Path) -> None:
    report, _, _ = _run(tmp_path, _rows(100, 0))

    assert report["verdict"] == "OUTCOME_TRUTH_READY"
    assert all(report["gates"].values())


def test_deterministic_outputs_and_hashes(tmp_path: Path) -> None:
    first, first_coverage, first_graduation = _run(tmp_path / "first", _rows(100, 0))
    second, second_coverage, second_graduation = _run(tmp_path / "second", _rows(100, 0))

    assert first == second
    assert first_coverage == second_coverage
    assert first_graduation == second_graduation
    assert first["coverage_report_sha256"] == hashlib.sha256(first_coverage).hexdigest()


def test_unresolved_outcomes_are_reported(tmp_path: Path) -> None:
    report, coverage_bytes, _ = _run(tmp_path, _rows(95, 5))
    coverage = json.loads(coverage_bytes)

    assert report["unresolved_population"] == 5
    assert coverage["unresolved_population"] == 5
    assert report["direct_outcome_coverage"] == 0.95


def test_bucket_coverage_is_reported(tmp_path: Path) -> None:
    report, coverage_bytes, _ = _run(tmp_path, _rows(9, 1, buckets=[BUCKETS[0]]))
    coverage = json.loads(coverage_bytes)

    assert report["verdict"] == "OUTCOME_TRUTH_READY"
    assert coverage["bucket_analysis"] == [
        {
            "frozen_probability_bucket": BUCKETS[0],
            "bucket_population": 10,
            "bucket_joined": 9,
            "bucket_coverage": 0.9,
        }
    ]


def test_missing_bucket_field_fails_closed(tmp_path: Path) -> None:
    rows = _rows(10, 0)
    rows[0].pop("frozen_probability_bucket")

    with pytest.raises(GraduationError, match="frozen_probability_bucket"):
        _run(tmp_path, rows)


def test_repeated_runs_in_same_output_directory_are_identical(tmp_path: Path) -> None:
    first = _run(tmp_path, _rows(100, 0))
    second = _run(tmp_path, _rows(100, 0))

    assert first == second
