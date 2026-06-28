from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.outcome_truth.free_outcome_truth_provisional_readiness import assess_provisional_readiness


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def _joined(classification: str, condition_id: str = "0xaaa") -> dict:
    return {
        "condition_id": condition_id,
        "normalized_epoch_start_ts": 1,
        "classification": classification,
        "terminal_outcome": "YES" if classification.endswith("RESOLVED") else None,
        "frozen_probability_bucket": "[0.50,0.60)",
        "allowed_use": "PROVISIONAL_DIAGNOSTIC",
        "official_pass_fail_allowed": False,
    }


def test_readiness_allows_only_provisional_diagnostic(tmp_path: Path) -> None:
    joined = _write_jsonl(tmp_path / "joined.jsonl", [_joined("PROVISIONAL_RESOLVED")])
    report = assess_provisional_readiness(joined, tmp_path / "output")

    assert report["verdict"] == "OUTCOME_TRUTH_PROVISIONAL_READY"
    assert report["allowed_use"] == "PROVISIONAL_DIAGNOSTIC"
    assert report["official_pass_fail_allowed"] is False
    assert "OUTCOME_TRUTH_READY" not in json.dumps(report)


def test_no_resolved_diagnostic_rows_is_not_ready(tmp_path: Path) -> None:
    joined = _write_jsonl(tmp_path / "joined.jsonl", [_joined("UNRESOLVED")])
    report = assess_provisional_readiness(joined, tmp_path / "output")

    assert report["verdict"] == "OUTCOME_TRUTH_PROVISIONAL_NOT_READY"


def test_readiness_report_is_deterministic_and_hashed(tmp_path: Path) -> None:
    rows = [_joined("PROVISIONAL_RESOLVED", "0xbbb"), _joined("AMBIGUOUS", "0xaaa")]
    first_path = _write_jsonl(tmp_path / "first.jsonl", rows)
    second_path = _write_jsonl(tmp_path / "second.jsonl", list(reversed(rows)))

    first = assess_provisional_readiness(first_path, tmp_path / "first-out")
    second = assess_provisional_readiness(second_path, tmp_path / "second-out")
    first_bytes = (tmp_path / "first-out" / "provisional_readiness_report.json").read_bytes()
    second_bytes = (tmp_path / "second-out" / "provisional_readiness_report.json").read_bytes()

    assert first == second
    assert first_bytes == second_bytes
    assert first["joined_input_sha256"] == hashlib.sha256(
        b"".join(
            (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
            for row in sorted(rows, key=lambda value: value["condition_id"])
        )
    ).hexdigest()


def test_readiness_tool_has_no_official_graduation_or_runtime_imports() -> None:
    source = Path("tools/outcome_truth/free_outcome_truth_provisional_readiness.py").read_text(encoding="utf-8")

    assert "outcome_truth_graduation" not in source
    assert "polymarket." not in source
    assert "main.py" not in source
