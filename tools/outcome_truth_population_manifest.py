"""Build a deterministic Outcome Truth population manifest from decision JSONL.

This offline tool streams source files line-by-line and retains only the
earliest model-ready observation for each condition/epoch unit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from pathlib import Path
from typing import Any


MANIFEST_SCHEMA_VERSION = "outcome_truth_population_manifest_v1"
REPORT_SCHEMA_VERSION = "outcome_truth_population_manifest_report_v1"
EPOCH_ALIASES = (
    "epoch_start_ts",
    "epoch_start",
    "market_epoch_start_ts",
    "market_epoch_start",
    "event_start_ts",
)
MODEL_PROBABILITY_ALIASES = ("model_probability_yes", "model_p_yes", "p_yes")


class PopulationManifestError(RuntimeError):
    """Raised when a population manifest cannot be built deterministically."""


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _hash_canonical(value: Any) -> str:
    compact = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(compact).hexdigest()


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


def _load_small_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else event


def _is_model_ready(payload: dict[str, Any]) -> bool:
    envelope = payload.get("entry_model_truth_envelope_v1")
    envelope = envelope if isinstance(envelope, dict) else {}
    return payload.get("model_output_ready") is True or any(
        payload.get(alias) not in (None, "") for alias in MODEL_PROBABILITY_ALIASES
    ) or envelope.get("model_probability_yes") not in (None, "")


def _normalize_epoch_value(value: Any) -> int:
    if isinstance(value, bool) or value in (None, ""):
        raise PopulationManifestError("invalid epoch value")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise PopulationManifestError(f"invalid epoch value: {value!r}") from exc
    if not number.is_integer():
        raise PopulationManifestError(f"invalid epoch value: {value!r}")
    return int(number)


def _normalized_epoch(payload: dict[str, Any], source: str) -> int:
    values = {
        _normalize_epoch_value(payload[alias])
        for alias in EPOCH_ALIASES
        if payload.get(alias) not in (None, "")
    }
    if not values:
        raise PopulationManifestError(f"missing epoch for model-ready row: {source}")
    if len(values) != 1:
        raise PopulationManifestError(f"ambiguous epoch normalization: {source}")
    return next(iter(values))


def _normalized_timestamp(event: dict[str, Any], payload: dict[str, Any], source: str) -> str:
    raw = next(
        (
            value
            for value in (
                payload.get("decision_timestamp"),
                event.get("timestamp_utc"),
                payload.get("timestamp"),
            )
            if value not in (None, "")
        ),
        None,
    )
    if raw is None:
        raise PopulationManifestError(f"missing decision timestamp: {source}")
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError as exc:
        raise PopulationManifestError(f"invalid decision timestamp: {source}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _model_probability_yes(payload: dict[str, Any], source: str) -> float:
    envelope = payload.get("entry_model_truth_envelope_v1")
    envelope = envelope if isinstance(envelope, dict) else {}
    raw = next(
        (
            value
            for value in (
                *(payload.get(alias) for alias in MODEL_PROBABILITY_ALIASES),
                envelope.get("model_probability_yes"),
            )
            if value not in (None, "")
        ),
        None,
    )
    if raw is None or isinstance(raw, bool):
        raise PopulationManifestError(f"missing model_probability_yes: {source}")
    try:
        probability = Decimal(str(raw))
    except (InvalidOperation, ValueError) as exc:
        raise PopulationManifestError(f"invalid model_probability_yes: {source}") from exc
    if not probability.is_finite() or probability < 0 or probability > 1:
        raise PopulationManifestError(f"invalid model_probability_yes: {source}")
    return float(probability)


def _frozen_probability_bucket(model_probability_yes: float) -> str:
    probability = Decimal(str(model_probability_yes))
    bucket_index = min(
        int((probability * Decimal("10")).to_integral_value(rounding=ROUND_FLOOR)),
        9,
    )
    lower = Decimal(bucket_index) / Decimal("10")
    upper = Decimal(bucket_index + 1) / Decimal("10")
    close = "]" if bucket_index == 9 else ")"
    return f"[{lower:.2f},{upper:.2f}{close}"


def _quarantine_rows(payload: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if isinstance(payload, list):
        return payload, {}
    if not isinstance(payload, dict):
        raise PopulationManifestError("quarantine inventory must be an object or list")
    rows = payload.get("rows", payload.get("quarantined_rows", []))
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise PopulationManifestError("quarantine inventory rows must be a list of objects")
    disclosure_fields = (
        "known_lost_events",
        "unknown_events",
        "maximum_possible_denominator_error",
        "affected_files",
        "materiality_classification",
    )
    disclosure = {field: payload.get(field) for field in disclosure_fields}
    return rows, disclosure


def _quarantine_index(rows: list[dict[str, Any]]) -> dict[tuple[str, int], str]:
    result: dict[tuple[str, int], str] = {}
    for row in rows:
        source_file = str(row.get("source_file", "")).replace("\\", "/")
        line_number = row.get("line_number", row.get("line"))
        digest = str(row.get("sha256", "")).lower()
        if not source_file or not isinstance(line_number, int) or len(digest) != 64:
            raise PopulationManifestError("invalid quarantine inventory row")
        result[(source_file, line_number)] = digest
        result[(Path(source_file).name, line_number)] = digest
    return result


def _row_from_event(
    *,
    event: dict[str, Any],
    relative_source: str,
    line_number: int,
) -> tuple[tuple[str, int], tuple[datetime, str, int], dict[str, Any]]:
    payload = _payload(event)
    source = f"{relative_source}:{line_number}"
    raw_condition_id = payload.get("condition_id")
    if raw_condition_id in (None, ""):
        raise PopulationManifestError(f"missing condition_id for model-ready row: {source}")
    condition_id = str(raw_condition_id).strip().lower()
    if not condition_id:
        raise PopulationManifestError(f"missing condition_id for model-ready row: {source}")
    epoch = _normalized_epoch(payload, source)
    timestamp = _normalized_timestamp(event, payload, source)
    timestamp_order = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    model_probability_yes = _model_probability_yes(payload, source)
    row_without_hash = {
        "condition_id": condition_id,
        "normalized_epoch_start_ts": epoch,
        "asset": payload.get("asset", payload.get("ticker")),
        "market_slug": payload.get("market_slug", payload.get("slug")),
        "source_file": relative_source,
        "source_line": line_number,
        "decision_timestamp_utc": timestamp,
        "model_probability_yes": model_probability_yes,
        "frozen_probability_bucket": _frozen_probability_bucket(model_probability_yes),
    }
    row = dict(row_without_hash)
    row["manifest_row_sha256"] = _hash_canonical(row_without_hash)
    return (condition_id, epoch), (timestamp_order, relative_source, line_number), row


def generate_population_manifest(
    *,
    source_dir: str | Path,
    quarantine_inventory: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Stream decision logs and write deterministic manifest/report outputs."""
    source_dir = Path(source_dir)
    quarantine_inventory = Path(quarantine_inventory)
    output_dir = Path(output_dir)
    quarantine_payload = _load_small_json(quarantine_inventory)
    approved_rows, loss_bound_disclosure = _quarantine_rows(quarantine_payload)
    approved = _quarantine_index(approved_rows)

    counts: Counter[str] = Counter()
    excluded: Counter[str] = Counter()
    selected: dict[tuple[str, int], tuple[tuple[datetime, str, int], dict[str, Any]]] = {}
    source_files: list[str] = []

    for source_file in sorted(path for path in source_dir.glob("*.jsonl") if path.is_file()):
        relative_source = source_file.relative_to(source_dir).as_posix()
        source_files.append(relative_source)
        with source_file.open("r", encoding="utf-8", errors="strict") as handle:
            for line_number, line in enumerate(handle, start=1):
                counts["raw_rows"] += 1
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict):
                        raise json.JSONDecodeError("event must be an object", line, 0)
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    counts["malformed_rows"] += 1
                    digests = {
                        hashlib.sha256(line.encode("utf-8")).hexdigest(),
                        hashlib.sha256(line.rstrip("\r\n").encode("utf-8")).hexdigest(),
                    }
                    expected = approved.get((relative_source, line_number))
                    if expected not in digests:
                        raise PopulationManifestError(
                            f"unapproved malformed JSON: {relative_source}:{line_number}"
                        ) from exc
                    counts["quarantined_rows"] += 1
                    excluded["quarantined_malformed"] += 1
                    continue

                counts["valid_rows"] += 1
                payload = _payload(event)
                if not _is_model_ready(payload):
                    excluded["not_model_ready"] += 1
                    continue
                counts["model_ready_rows"] += 1
                key, order, row = _row_from_event(
                    event=event,
                    relative_source=relative_source,
                    line_number=line_number,
                )
                current = selected.get(key)
                if current is None or order < current[0]:
                    if current is not None:
                        excluded["duplicate_model_ready_unit"] += 1
                    selected[key] = (order, row)
                else:
                    excluded["duplicate_model_ready_unit"] += 1

    conditions = [
        selected[key][1]
        for key in sorted(selected, key=lambda value: (value[0], value[1]))
    ]
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "decision_bearing_unit": "earliest_model_ready_per_condition_id_normalized_epoch_start_ts",
        "conditions": conditions,
    }
    manifest_bytes = _canonical_bytes(manifest)
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "raw_rows": counts["raw_rows"],
        "valid_rows": counts["valid_rows"],
        "malformed_rows": counts["malformed_rows"],
        "quarantined_rows": counts["quarantined_rows"],
        "model_ready_rows": counts["model_ready_rows"],
        "unique_conditions": len({row["condition_id"] for row in conditions}),
        "unique_condition_epoch_units": len(conditions),
        "excluded_rows": dict(sorted(excluded.items())),
        "loss_bound_disclosure": loss_bound_disclosure,
        "source_files": source_files,
        "quarantine_inventory_sha256": hashlib.sha256(
            _canonical_bytes(quarantine_payload)
        ).hexdigest(),
        "manifest_sha256": manifest_sha256,
    }
    _atomic_write(output_dir / "population_manifest.json", manifest_bytes)
    _atomic_write(output_dir / "population_manifest_report.json", _canonical_bytes(report))
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--quarantine-inventory", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        report = generate_population_manifest(
            source_dir=args.source_dir,
            quarantine_inventory=args.quarantine_inventory,
            output_dir=args.output_dir,
        )
    except (OSError, ValueError, json.JSONDecodeError, PopulationManifestError) as exc:
        print(f"population manifest generation failed: {type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
