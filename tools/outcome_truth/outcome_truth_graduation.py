"""Evaluate frozen Outcome Truth coverage and graduation gates offline."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


COVERAGE_SCHEMA_VERSION = "outcome_truth_coverage_report_v1"
GRADUATION_SCHEMA_VERSION = "outcome_truth_graduation_report_v1"
READY = "OUTCOME_TRUTH_READY"
NOT_READY = "OUTCOME_TRUTH_NOT_READY"


class GraduationError(RuntimeError):
    """Raised when graduation inputs are incomplete or internally inconsistent."""


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise GraduationError(f"{label} is missing")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise GraduationError(f"{label} must be an object")
    return payload


def _frozen_buckets(path: Path) -> tuple[list[str], str]:
    if not path.is_file():
        raise GraduationError("frozen calibration specification is missing")
    with path.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()
    text = "".join(lines)
    if "FROZEN CANDIDATE SPECIFICATION" not in text:
        raise GraduationError("frozen calibration specification status is invalid")
    fingerprint_match = re.search(r"^fingerprint_hash:\s*([0-9a-fA-F]{64})\s*$", text, re.MULTILINE)
    if not fingerprint_match:
        raise GraduationError("frozen calibration specification fingerprint is missing")
    bucket_line = next(
        (line for line in lines if line.strip().startswith("probability_buckets:")),
        None,
    )
    buckets = re.findall(r"\[[0-9.]+,[0-9.]+[\)\]]", bucket_line or "")
    if not buckets or len(set(buckets)) != len(buckets):
        raise GraduationError("frozen calibration specification buckets are invalid")
    return buckets, fingerprint_match.group(1).lower()


def _nonnegative_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field, 0)
    if isinstance(value, bool):
        raise GraduationError(f"{field} must be a nonnegative integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise GraduationError(f"{field} must be a nonnegative integer") from exc
    if number < 0 or number != value:
        raise GraduationError(f"{field} must be a nonnegative integer")
    return number


def _read_joined_rows(path: Path, frozen_buckets: set[str]) -> tuple[Counter[str], Counter[str], int]:
    if not path.is_file():
        raise GraduationError("joined official outcomes are missing")
    population: Counter[str] = Counter()
    joined: Counter[str] = Counter()
    unresolved = 0
    with path.open("r", encoding="utf-8", errors="strict") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise GraduationError(f"malformed joined outcome row: line {line_number}") from exc
            if not isinstance(row, dict):
                raise GraduationError(f"joined outcome row must be an object: line {line_number}")
            bucket = row.get("frozen_probability_bucket")
            if bucket not in frozen_buckets:
                raise GraduationError(
                    f"frozen_probability_bucket missing or invalid: line {line_number}"
                )
            population[bucket] += 1
            status = row.get("join_status")
            if status == "JOINED_OFFICIAL_RESOLVED":
                joined[bucket] += 1
            elif status == "UNRESOLVED":
                unresolved += 1
            else:
                raise GraduationError(f"invalid join_status: line {line_number}")
    return population, joined, unresolved


def graduate_outcome_truth(
    *,
    joined_outcomes: str | Path,
    outcome_join_report: str | Path,
    calibration_spec: str | Path,
    loss_bound_evidence: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Write deterministic coverage and graduation reports."""
    joined_outcomes = Path(joined_outcomes)
    outcome_join_report = Path(outcome_join_report)
    calibration_spec = Path(calibration_spec)
    loss_bound_evidence = Path(loss_bound_evidence)
    output_dir = Path(output_dir)

    buckets, fingerprint = _frozen_buckets(calibration_spec)
    join_report = _load_json(outcome_join_report, "outcome join report")
    loss_bound = _load_json(loss_bound_evidence, "loss-bound evidence")
    eligible = _nonnegative_int(join_report, "eligible_population")
    report_joined = _nonnegative_int(join_report, "joined_rows")
    report_unresolved = _nonnegative_int(join_report, "unresolved_rows")
    conflicts = _nonnegative_int(join_report, "conflicting_rows")
    ambiguous = _nonnegative_int(join_report, "ambiguous_rows")
    known_lost = _nonnegative_int(loss_bound, "known_lost_events")
    unknown = _nonnegative_int(loss_bound, "unknown_events")
    denominator_error = _nonnegative_int(loss_bound, "maximum_possible_denominator_error")

    bucket_population, bucket_joined, unresolved = _read_joined_rows(
        joined_outcomes, set(buckets)
    )
    computed_population = sum(bucket_population.values())
    computed_joined = sum(bucket_joined.values())
    bucket_analysis = []
    nonempty_coverages = []
    for bucket in buckets:
        population_count = bucket_population[bucket]
        joined_count = bucket_joined[bucket]
        if not population_count:
            continue
        coverage = joined_count / population_count
        nonempty_coverages.append(coverage)
        bucket_analysis.append(
            {
                "frozen_probability_bucket": bucket,
                "bucket_population": population_count,
                "bucket_joined": joined_count,
                "bucket_coverage": round(coverage, 12),
            }
        )

    direct_coverage = computed_joined / eligible if eligible else 0.0
    worst_case_denominator = eligible + denominator_error
    worst_case_coverage = (
        computed_joined / worst_case_denominator if worst_case_denominator else 0.0
    )
    max_delta = (
        (max(nonempty_coverages) - min(nonempty_coverages)) * 100
        if nonempty_coverages
        else 0.0
    )
    accounting_consistent = (
        join_report.get("status") == "PASS"
        and computed_population == eligible
        and computed_joined == report_joined
        and unresolved == report_unresolved
        and computed_joined + unresolved == eligible
    )
    gates = {
        "join_report_pass": join_report.get("status") == "PASS",
        "population_accounting_consistent": accounting_consistent,
        "overall_coverage_gte_90pct": direct_coverage >= 0.90,
        "worst_case_coverage_gte_90pct": worst_case_coverage >= 0.90,
        "bucket_delta_lte_10pp": max_delta <= 10.0,
        "zero_conflicts": conflicts == 0,
        "zero_ambiguous_included_mappings": ambiguous == 0,
    }
    verdict = READY if all(gates.values()) else NOT_READY

    coverage_report = {
        "schema_version": COVERAGE_SCHEMA_VERSION,
        "calibration_fingerprint_hash": fingerprint,
        "eligible_population": eligible,
        "joined_population": computed_joined,
        "unresolved_population": unresolved,
        "direct_outcome_coverage": round(direct_coverage, 12),
        "worst_case_eligible_population": worst_case_denominator,
        "worst_case_direct_outcome_coverage": round(worst_case_coverage, 12),
        "bucket_analysis": bucket_analysis,
        "max_bucket_coverage_delta_pp": round(max_delta, 12),
        "conflicting_rows": conflicts,
        "ambiguous_included_mappings": ambiguous,
        "loss_bound": {
            "known_lost_events": known_lost,
            "unknown_events": unknown,
            "maximum_possible_denominator_error": denominator_error,
        },
    }
    coverage_bytes = _canonical_bytes(coverage_report)
    coverage_hash = hashlib.sha256(coverage_bytes).hexdigest()
    graduation_report = {
        "schema_version": GRADUATION_SCHEMA_VERSION,
        "verdict": verdict,
        "eligible_population": eligible,
        "joined_population": computed_joined,
        "unresolved_population": unresolved,
        "direct_outcome_coverage": round(direct_coverage, 12),
        "worst_case_direct_outcome_coverage": round(worst_case_coverage, 12),
        "max_bucket_coverage_delta_pp": round(max_delta, 12),
        "gates": gates,
        "coverage_report_sha256": coverage_hash,
        "calibration_fingerprint_hash": fingerprint,
    }
    _atomic_write(output_dir / "outcome_truth_coverage_report.json", coverage_bytes)
    _atomic_write(
        output_dir / "outcome_truth_graduation_report.json",
        _canonical_bytes(graduation_report),
    )
    return graduation_report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--joined-outcomes", required=True, type=Path)
    parser.add_argument("--outcome-join-report", required=True, type=Path)
    parser.add_argument("--calibration-spec", required=True, type=Path)
    parser.add_argument("--loss-bound-evidence", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        report = graduate_outcome_truth(
            joined_outcomes=args.joined_outcomes,
            outcome_join_report=args.outcome_join_report,
            calibration_spec=args.calibration_spec,
            loss_bound_evidence=args.loss_bound_evidence,
            output_dir=args.output_dir,
        )
    except (OSError, ValueError, json.JSONDecodeError, GraduationError) as exc:
        print(f"outcome truth graduation failed: {type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["verdict"] == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
