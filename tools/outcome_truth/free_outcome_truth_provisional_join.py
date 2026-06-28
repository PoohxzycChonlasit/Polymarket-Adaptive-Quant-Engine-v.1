"""Join provisional diagnostic outcomes to the frozen population manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "free_outcome_truth_provisional_join_v1"


class ProvisionalJoinError(RuntimeError):
    """Raised when provisional join inputs violate deterministic identity rules."""


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


def _identity(row: dict[str, Any], source: str) -> tuple[str, int]:
    raw_condition = row.get("condition_id")
    raw_epoch = row.get("normalized_epoch_start_ts")
    if raw_condition in (None, ""):
        raise ProvisionalJoinError(f"condition_id missing: {source}")
    if isinstance(raw_epoch, bool) or raw_epoch in (None, ""):
        raise ProvisionalJoinError(f"normalized_epoch_start_ts missing: {source}")
    try:
        epoch = int(raw_epoch)
    except (TypeError, ValueError) as exc:
        raise ProvisionalJoinError(f"normalized_epoch_start_ts invalid: {source}") from exc
    if epoch != raw_epoch:
        raise ProvisionalJoinError(f"normalized_epoch_start_ts invalid: {source}")
    return str(raw_condition).strip().lower(), epoch


def _load_population(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = payload if isinstance(payload, list) else payload.get("conditions")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ProvisionalJoinError("population manifest must contain conditions")
    return rows


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8", errors="strict") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ProvisionalJoinError(f"malformed provisional JSON: line {line_number}") from exc
            if not isinstance(row, dict):
                raise ProvisionalJoinError(f"provisional row must be an object: line {line_number}")
            rows.append(row)
    return rows


def join_provisional_outcomes(
    *,
    population_manifest: str | Path,
    provisional_outcomes: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Write one diagnostic-only joined row for every population unit."""
    population_rows = _load_population(Path(population_manifest))
    outcome_rows = _load_jsonl(Path(provisional_outcomes))
    population_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    outcome_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for index, row in enumerate(population_rows, start=1):
        key = _identity(row, f"population:{index}")
        if key in population_by_key:
            raise ProvisionalJoinError(f"duplicate population identity: {key}")
        population_by_key[key] = row
    for index, row in enumerate(outcome_rows, start=1):
        key = _identity(row, f"provisional:{index}")
        if key in outcome_by_key:
            raise ProvisionalJoinError(f"duplicate provisional identity: {key}")
        outcome_by_key[key] = row

    unexpected = sorted(set(outcome_by_key) - set(population_by_key))
    joined_rows = []
    missing_rows = 0
    for key in sorted(population_by_key):
        population = population_by_key[key]
        outcome = outcome_by_key.get(key)
        if outcome is None:
            missing_rows += 1
            outcome = {
                "classification": "UNRESOLVED",
                "terminal_outcome": None,
                "authority_class": "NO_TERMINAL_TRUTH",
                "historical_provenance_status": "NOT_APPLICABLE",
                "source_classes": {},
                "row_sha256": None,
            }
        row_without_hash = {
            "schema_version": SCHEMA_VERSION,
            "condition_id": key[0],
            "normalized_epoch_start_ts": key[1],
            "asset": population.get("asset"),
            "market_slug": population.get("market_slug"),
            "model_probability_yes": population.get("model_probability_yes"),
            "frozen_probability_bucket": population.get("frozen_probability_bucket"),
            "population_manifest_row_sha256": population.get("manifest_row_sha256"),
            "provisional_outcome_row_sha256": outcome.get("row_sha256"),
            "classification": outcome.get("classification"),
            "terminal_outcome": outcome.get("terminal_outcome"),
            "authority_class": outcome.get("authority_class"),
            "historical_provenance_status": outcome.get("historical_provenance_status"),
            "source_classes": outcome.get("source_classes", {}),
            "allowed_use": "PROVISIONAL_DIAGNOSTIC",
            "official_pass_fail_allowed": False,
        }
        row = dict(row_without_hash)
        row["joined_row_sha256"] = _compact_hash(row_without_hash)
        joined_rows.append(row)

    output_bytes = b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in joined_rows
    )
    _atomic_write(Path(output_dir) / "provisional_joined_outcomes.jsonl", output_bytes)
    return {
        "schema_version": SCHEMA_VERSION,
        "eligible_population": len(population_by_key),
        "joined_population": len(joined_rows),
        "missing_rows": missing_rows,
        "unexpected_outcome_rows": len(unexpected),
        "classification_counts": dict(
            sorted(Counter(row["classification"] for row in joined_rows).items())
        ),
        "output_sha256": hashlib.sha256(output_bytes).hexdigest(),
        "allowed_use": "PROVISIONAL_DIAGNOSTIC",
        "official_pass_fail_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population-manifest", required=True, type=Path)
    parser.add_argument("--provisional-outcomes", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = join_provisional_outcomes(
            population_manifest=args.population_manifest,
            provisional_outcomes=args.provisional_outcomes,
            output_dir=args.output_dir,
        )
    except (OSError, ValueError, json.JSONDecodeError, ProvisionalJoinError) as exc:
        print(f"provisional outcome join failed: {type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
