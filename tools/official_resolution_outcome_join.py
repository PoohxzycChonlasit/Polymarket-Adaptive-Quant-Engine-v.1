"""Deterministically join replay-verified official outcomes to a population."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


JOIN_SCHEMA_VERSION = "official_resolution_outcome_join_v1"
REPORT_SCHEMA_VERSION = "official_resolution_outcome_join_report_v1"
RESOLVED_STATUS = "OFFICIAL_RESOLVED"
UNRESOLVED_STATUS = "OFFICIAL_UNRESOLVED"
AMBIGUOUS_STATUS = "AMBIGUOUS_MAPPING"


class OutcomeJoinError(RuntimeError):
    """Raised when join inputs do not satisfy their required contract."""


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _compact_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _condition_id(row: dict[str, Any], source: str) -> str:
    raw = row.get("condition_id")
    if raw in (None, ""):
        raise OutcomeJoinError(f"condition_id missing: {source}")
    return str(raw).strip().lower()


def _epoch(row: dict[str, Any], source: str) -> int:
    raw = row.get("normalized_epoch_start_ts")
    if isinstance(raw, bool) or raw in (None, ""):
        raise OutcomeJoinError(f"normalized_epoch_start_ts missing: {source}")
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise OutcomeJoinError(f"normalized_epoch_start_ts invalid: {source}") from exc
    if not value.is_integer():
        raise OutcomeJoinError(f"normalized_epoch_start_ts invalid: {source}")
    return int(value)


def _outcome_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise OutcomeJoinError(f"outcome rows path unavailable: {path}")
    return sorted(item for item in path.rglob("outcome_rows.jsonl") if item.is_file())


def _relative_sources(root: Path, files: list[Path]) -> list[str]:
    if root.is_file():
        return [root.name]
    return [path.relative_to(root).as_posix() for path in files]


def _load_population(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    rows = payload if isinstance(payload, list) else payload.get("conditions")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise OutcomeJoinError("population manifest must contain a conditions list")
    return rows


def _read_outcomes(files: list[Path]) -> tuple[dict[str, list[dict[str, Any]]], int]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    raw_rows = 0
    for source_file in files:
        with source_file.open("r", encoding="utf-8", errors="strict") as handle:
            for line_number, line in enumerate(handle, start=1):
                raw_rows += 1
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise OutcomeJoinError(
                        f"malformed outcome JSON: {source_file}:{line_number}"
                    ) from exc
                if not isinstance(row, dict):
                    raise OutcomeJoinError(
                        f"outcome row must be an object: {source_file}:{line_number}"
                    )
                groups[_condition_id(row, f"{source_file}:{line_number}")].append(row)
    return groups, raw_rows


def _joined_row(population: dict[str, Any], outcome: dict[str, Any], join_status: str) -> dict[str, Any]:
    row_without_hash = {
        "schema_version": JOIN_SCHEMA_VERSION,
        "condition_id": _condition_id(population, "population"),
        "normalized_epoch_start_ts": _epoch(population, "population"),
        "asset": population.get("asset"),
        "market_slug": population.get("market_slug"),
        "decision_timestamp_utc": population.get("decision_timestamp_utc"),
        "model_probability_yes": population.get("model_probability_yes"),
        "frozen_probability_bucket": population.get("frozen_probability_bucket"),
        "population_manifest_row_sha256": population.get("manifest_row_sha256"),
        "join_status": join_status,
        "outcome_status": outcome.get("outcome_status"),
        "terminal_outcome": outcome.get("terminal_outcome"),
        "resolution_block_number": outcome.get("resolution_block_number"),
        "resolution_block_hash": outcome.get("resolution_block_hash"),
        "resolution_transaction_hash": outcome.get("resolution_transaction_hash"),
        "resolution_log_index": outcome.get("resolution_log_index"),
        "state_source_block_number": outcome.get("state_source_block_number"),
        "state_source_block_hash": outcome.get("state_source_block_hash"),
    }
    row = dict(row_without_hash)
    row["joined_row_sha256"] = _compact_hash(row_without_hash)
    return row


def join_official_outcomes(
    *,
    population_manifest: str | Path,
    outcome_rows: str | Path,
    aggregate_verification: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Join official outcome rows and write deterministic fail-closed outputs."""
    population_manifest = Path(population_manifest)
    outcome_rows = Path(outcome_rows)
    aggregate_verification = Path(aggregate_verification)
    output_dir = Path(output_dir)

    population_rows = _load_population(population_manifest)
    population_by_id: dict[str, dict[str, Any]] = {}
    population_duplicates: list[str] = []
    for index, row in enumerate(population_rows, start=1):
        condition_id = _condition_id(row, f"population:{index}")
        _epoch(row, f"population:{index}")
        if condition_id in population_by_id:
            population_duplicates.append(condition_id)
        else:
            population_by_id[condition_id] = row

    aggregate = _load_json(aggregate_verification)
    verified = isinstance(aggregate, dict) and aggregate.get("status") == "PASS"
    files = _outcome_files(outcome_rows)
    source_files = _relative_sources(outcome_rows, files)
    groups, raw_outcome_rows = _read_outcomes(files)

    excluded: Counter[str] = Counter()
    joined_rows: list[dict[str, Any]] = []
    missing_conditions: list[str] = []
    unexpected_conditions = sorted(set(groups) - set(population_by_id))
    duplicate_rows = 0
    conflicting_rows = 0
    ambiguous_rows = 0
    integrity_failures = bool(population_duplicates)

    if population_duplicates:
        excluded["duplicate_population_condition"] += len(set(population_duplicates))
    if not verified:
        excluded["unverified_package_population"] += len(population_by_id)
        integrity_failures = True
    else:
        if unexpected_conditions:
            excluded["unexpected_condition"] += len(unexpected_conditions)
            integrity_failures = True

        for condition_id in sorted(population_by_id):
            population = population_by_id[condition_id]
            rows = groups.get(condition_id, [])
            if not rows:
                missing_conditions.append(condition_id)
                excluded["missing_condition"] += 1
                integrity_failures = True
                continue

            unique: dict[str, dict[str, Any]] = {}
            for row in rows:
                unique.setdefault(_compact_hash(row), row)
            duplicate_count = len(rows) - len(unique)
            if duplicate_count:
                duplicate_rows += duplicate_count
                excluded["duplicate_outcome_rows"] += 1
                integrity_failures = True
                continue

            unique_rows = list(unique.values())
            statuses = {
                (row.get("outcome_status"), row.get("terminal_outcome"), _epoch(row, condition_id))
                for row in unique_rows
            }
            if len(statuses) > 1:
                conflicting_rows += len(unique_rows)
                excluded["conflicting_outcomes"] += 1
                integrity_failures = True
                continue

            row = unique_rows[0]
            if row.get("outcome_status") == AMBIGUOUS_STATUS:
                ambiguous_rows += 1
                excluded["ambiguous_mapping"] += 1
                integrity_failures = True
                continue
            if _epoch(row, condition_id) != _epoch(population, condition_id):
                excluded["epoch_mismatch"] += 1
                integrity_failures = True
                continue

            status = row.get("outcome_status")
            if status == RESOLVED_STATUS and row.get("terminal_outcome") not in (None, ""):
                joined_rows.append(_joined_row(population, row, "JOINED_OFFICIAL_RESOLVED"))
            elif status == UNRESOLVED_STATUS and row.get("terminal_outcome") in (None, ""):
                joined_rows.append(_joined_row(population, row, "UNRESOLVED"))
            else:
                excluded["invalid_outcome_status"] += 1
                integrity_failures = True

    joined_rows.sort(key=lambda row: (row["condition_id"], row["normalized_epoch_start_ts"]))
    output_bytes = b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in joined_rows
    )
    resolved_count = sum(row["join_status"] == "JOINED_OFFICIAL_RESOLVED" for row in joined_rows)
    unresolved_count = sum(row["join_status"] == "UNRESOLVED" for row in joined_rows)
    eligible = len(population_by_id)
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": "FAIL" if integrity_failures else "PASS",
        "aggregate_verification_status": aggregate.get("status") if isinstance(aggregate, dict) else None,
        "eligible_population": eligible,
        "raw_outcome_rows": raw_outcome_rows,
        "joined_rows": resolved_count,
        "unresolved_rows": unresolved_count,
        "excluded_rows": dict(sorted(excluded.items())),
        "duplicate_rows": duplicate_rows,
        "conflicting_rows": conflicting_rows,
        "ambiguous_rows": ambiguous_rows,
        "missing_conditions": missing_conditions,
        "unexpected_conditions": unexpected_conditions,
        "duplicate_population_conditions": sorted(set(population_duplicates)),
        "direct_join_coverage": round(resolved_count / eligible, 12) if eligible else 0.0,
        "outcome_source_files": source_files,
        "joined_output_sha256": hashlib.sha256(output_bytes).hexdigest(),
    }
    _atomic_write(output_dir / "joined_official_outcomes.jsonl", output_bytes)
    _atomic_write(output_dir / "outcome_join_report.json", _canonical_bytes(report))
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population-manifest", required=True, type=Path)
    parser.add_argument("--outcome-rows", required=True, type=Path)
    parser.add_argument("--aggregate-verification", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        report = join_official_outcomes(
            population_manifest=args.population_manifest,
            outcome_rows=args.outcome_rows,
            aggregate_verification=args.aggregate_verification,
            output_dir=args.output_dir,
        )
    except (OSError, ValueError, json.JSONDecodeError, OutcomeJoinError) as exc:
        print(f"official outcome join failed: {type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
