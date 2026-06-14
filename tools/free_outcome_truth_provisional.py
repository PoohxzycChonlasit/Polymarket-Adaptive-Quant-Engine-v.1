"""Build deterministic free-source provisional outcome rows for diagnostics only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "free_outcome_truth_provisional_v1"
CLASSIFICATIONS = {
    "OFFICIAL_FREE_RESOLVED",
    "PROVISIONAL_RESOLVED",
    "UNRESOLVED",
    "AMBIGUOUS",
    "NOT_RECOVERABLE_FREE",
}


class ProvisionalOutcomeError(RuntimeError):
    """Raised when provisional evidence cannot be classified safely."""


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


def _identity(evidence: dict[str, Any]) -> tuple[str, int]:
    raw_condition = evidence.get("condition_id")
    if raw_condition in (None, ""):
        raise ProvisionalOutcomeError("condition_id is required")
    condition_id = str(raw_condition).strip().lower()
    if not condition_id:
        raise ProvisionalOutcomeError("condition_id is required")
    raw_epoch = evidence.get("normalized_epoch_start_ts")
    if isinstance(raw_epoch, bool) or raw_epoch in (None, ""):
        raise ProvisionalOutcomeError("normalized_epoch_start_ts is required")
    try:
        epoch = int(raw_epoch)
    except (TypeError, ValueError) as exc:
        raise ProvisionalOutcomeError("normalized_epoch_start_ts is invalid") from exc
    if epoch != raw_epoch:
        raise ProvisionalOutcomeError("normalized_epoch_start_ts is invalid")
    return condition_id, epoch


def _normalized_winner(source: Any) -> str | None:
    if not isinstance(source, dict):
        return None
    raw = source.get("winner", source.get("terminal_outcome"))
    if raw in (None, ""):
        return None
    winner = str(raw).strip().upper()
    return winner or None


def _ctf_outcome(source: Any) -> tuple[str | None, bool, bool]:
    """Return outcome, is_final, is_ambiguous for the latest CTF payout state."""
    if not isinstance(source, dict) or not source:
        return None, False, False
    denominator = source.get("payout_denominator")
    vector = source.get("payout_vector")
    order = source.get("outcome_slot_order")
    if denominator in (None, 0, "0", "0x0"):
        return None, False, False
    if (
        isinstance(denominator, bool)
        or not isinstance(vector, list)
        or not isinstance(order, list)
        or len(vector) != len(order)
    ):
        return None, True, True
    try:
        denominator_int = int(denominator)
        winners = [index for index, value in enumerate(vector) if int(value) == denominator_int]
    except (TypeError, ValueError):
        return None, True, True
    if denominator_int <= 0 or len(winners) != 1:
        return None, True, True
    winner = str(order[winners[0]]).strip().upper()
    if not winner:
        return None, True, True
    return winner, True, False


def classify_provisional_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Classify one condition/epoch using free evidence without official promotion."""
    if not isinstance(evidence, dict):
        raise ProvisionalOutcomeError("evidence row must be an object")
    condition_id, epoch = _identity(evidence)
    gamma = evidence.get("gamma")
    clob = evidence.get("clob")
    ctf = evidence.get("ctf")
    gamma_winner = _normalized_winner(gamma)
    clob_winner = _normalized_winner(clob)
    ctf_winner, ctf_final, ctf_ambiguous = _ctf_outcome(ctf)
    decisive = [winner for winner in (gamma_winner, clob_winner, ctf_winner) if winner]
    disagreement = len(set(decisive)) > 1

    terminal_outcome = None
    authority_class = "NO_TERMINAL_TRUTH"
    historical_provenance = "NOT_APPLICABLE"
    if disagreement or ctf_ambiguous:
        classification = "AMBIGUOUS"
        authority_class = "CONFLICTING_OR_AMBIGUOUS_SOURCES"
    elif ctf_final and ctf_winner:
        classification = "OFFICIAL_FREE_RESOLVED"
        terminal_outcome = ctf_winner
        authority_class = "OFFICIAL_STATE_WITHOUT_HISTORICAL_PROVENANCE"
        has_provenance = all(
            isinstance(ctf, dict) and ctf.get(field) not in (None, "")
            for field in ("resolution_block_number", "transaction_hash", "log_index")
        )
        historical_provenance = (
            "PRESENT" if has_provenance else "MISSING_EVENT_BLOCK_RECEIPT"
        )
    elif gamma_winner and clob_winner and gamma_winner == clob_winner:
        classification = "PROVISIONAL_RESOLVED"
        terminal_outcome = gamma_winner
        authority_class = "PROVISIONAL_PLATFORM_METADATA"
    elif evidence.get("recovery_exhausted") is True:
        classification = "NOT_RECOVERABLE_FREE"
    else:
        classification = "UNRESOLVED"

    row_without_hash = {
        "schema_version": SCHEMA_VERSION,
        "condition_id": condition_id,
        "normalized_epoch_start_ts": epoch,
        "asset": evidence.get("asset"),
        "market_slug": evidence.get("market_slug"),
        "classification": classification,
        "terminal_outcome": terminal_outcome,
        "authority_class": authority_class,
        "historical_provenance_status": historical_provenance,
        "agreement_status": "DISAGREEMENT" if disagreement else "NO_CONFLICT_OBSERVED",
        "source_classes": {
            "gamma": "PROVISIONAL_PLATFORM_METADATA" if isinstance(gamma, dict) and gamma else "MISSING",
            "clob": "PROVISIONAL_PLATFORM_METADATA" if isinstance(clob, dict) and clob else "MISSING",
            "ctf": "OFFICIAL_LATEST_STATE" if isinstance(ctf, dict) and ctf else "MISSING",
            "local_snapshot": (
                "PROXY_ONLY"
                if isinstance(evidence.get("local_snapshot"), dict)
                and evidence.get("local_snapshot")
                else "MISSING"
            ),
        },
        "source_outcomes": {
            "gamma": gamma_winner,
            "clob": clob_winner,
            "ctf": ctf_winner,
        },
        "allowed_use": "PROVISIONAL_DIAGNOSTIC",
        "official_pass_fail_allowed": False,
    }
    row = dict(row_without_hash)
    row["row_sha256"] = _compact_hash(row_without_hash)
    return row


def build_provisional_outcomes(evidence_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Stream evidence JSONL and write deterministic provisional outcome rows."""
    evidence_path = Path(evidence_path)
    output_dir = Path(output_dir)
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    with evidence_path.open("r", encoding="utf-8", errors="strict") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                evidence = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ProvisionalOutcomeError(f"malformed evidence JSON: line {line_number}") from exc
            row = classify_provisional_evidence(evidence)
            key = (row["condition_id"], row["normalized_epoch_start_ts"])
            if key in seen:
                raise ProvisionalOutcomeError(f"duplicate evidence identity: {key}")
            seen.add(key)
            rows.append(row)
    rows.sort(key=lambda row: (row["condition_id"], row["normalized_epoch_start_ts"]))
    output_bytes = b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in rows
    )
    _atomic_write(output_dir / "provisional_outcomes.jsonl", output_bytes)
    return {
        "schema_version": SCHEMA_VERSION,
        "rows": len(rows),
        "classification_counts": dict(sorted(Counter(row["classification"] for row in rows).items())),
        "output_sha256": hashlib.sha256(output_bytes).hexdigest(),
        "allowed_use": "PROVISIONAL_DIAGNOSTIC",
        "official_pass_fail_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-path", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = build_provisional_outcomes(args.evidence_path, args.output_dir)
    except (OSError, ValueError, json.JSONDecodeError, ProvisionalOutcomeError) as exc:
        print(f"provisional outcome classification failed: {type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
