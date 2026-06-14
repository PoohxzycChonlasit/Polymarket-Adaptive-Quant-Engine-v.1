"""Assess whether joined free-source outcomes support provisional diagnostics."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "free_outcome_truth_provisional_readiness_v1"
READY = "OUTCOME_TRUTH_PROVISIONAL_READY"
NOT_READY = "OUTCOME_TRUTH_PROVISIONAL_NOT_READY"
RESOLVED = {"OFFICIAL_FREE_RESOLVED", "PROVISIONAL_RESOLVED"}


class ProvisionalReadinessError(RuntimeError):
    """Raised when provisional readiness inputs violate diagnostic-only rules."""


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


def assess_provisional_readiness(
    joined_outcomes: str | Path, output_dir: str | Path
) -> dict[str, Any]:
    """Write a diagnostic-only readiness report without official graduation."""
    rows = []
    with Path(joined_outcomes).open("r", encoding="utf-8", errors="strict") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ProvisionalReadinessError(f"malformed joined JSON: line {line_number}") from exc
            if not isinstance(row, dict):
                raise ProvisionalReadinessError(f"joined row must be an object: line {line_number}")
            if (
                row.get("allowed_use") != "PROVISIONAL_DIAGNOSTIC"
                or row.get("official_pass_fail_allowed") is not False
            ):
                raise ProvisionalReadinessError(
                    f"joined row violates diagnostic-only contract: line {line_number}"
                )
            rows.append(row)
    rows.sort(
        key=lambda row: (
            str(row.get("condition_id", "")).lower(),
            row.get("normalized_epoch_start_ts", 0),
        )
    )
    joined_bytes = b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in rows
    )
    counts = Counter(row.get("classification") for row in rows)
    resolved_count = sum(counts[classification] for classification in RESOLVED)
    verdict = READY if rows and resolved_count > 0 else NOT_READY
    report = {
        "schema_version": SCHEMA_VERSION,
        "verdict": verdict,
        "allowed_use": "PROVISIONAL_DIAGNOSTIC",
        "official_pass_fail_allowed": False,
        "official_graduation_status": "BLOCKED_BY_DESIGN",
        "eligible_population": len(rows),
        "diagnostic_resolved_population": resolved_count,
        "diagnostic_coverage": round(resolved_count / len(rows), 12) if rows else 0.0,
        "classification_counts": dict(sorted(counts.items())),
        "joined_input_sha256": hashlib.sha256(joined_bytes).hexdigest(),
    }
    _atomic_write(Path(output_dir) / "provisional_readiness_report.json", _canonical_bytes(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--joined-outcomes", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = assess_provisional_readiness(args.joined_outcomes, args.output_dir)
    except (OSError, ValueError, json.JSONDecodeError, ProvisionalReadinessError) as exc:
        print(f"provisional readiness assessment failed: {type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["verdict"] == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
