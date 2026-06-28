from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.outcome_truth.free_outcome_truth_provisional import (
    ProvisionalOutcomeError,
    build_provisional_outcomes,
    classify_provisional_evidence,
)


def _evidence(**overrides: object) -> dict:
    row = {
        "condition_id": "0xabc",
        "normalized_epoch_start_ts": 100,
        "asset": "ETH",
        "market_slug": "eth-updown-5m-100",
        "gamma": {},
        "clob": {},
        "ctf": {},
        "local_snapshot": {},
    }
    row.update(overrides)
    return row


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def test_gamma_clob_agreement_is_provisional_resolved() -> None:
    row = classify_provisional_evidence(
        _evidence(
            gamma={"closed": True, "winner": "YES"},
            clob={"closed": True, "winner": "YES"},
        )
    )

    assert row["classification"] == "PROVISIONAL_RESOLVED"
    assert row["terminal_outcome"] == "YES"
    assert row["authority_class"] == "PROVISIONAL_PLATFORM_METADATA"


def test_gamma_clob_disagreement_is_ambiguous() -> None:
    row = classify_provisional_evidence(
        _evidence(
            gamma={"closed": True, "winner": "YES"},
            clob={"closed": True, "winner": "NO"},
        )
    )

    assert row["classification"] == "AMBIGUOUS"
    assert row["terminal_outcome"] is None


def test_deterministic_ctf_state_is_official_free_resolved_without_provenance() -> None:
    row = classify_provisional_evidence(
        _evidence(
            gamma={"closed": True, "winner": "YES"},
            clob={"closed": True, "winner": "YES"},
            ctf={
                "payout_vector": [1, 0],
                "payout_denominator": 1,
                "outcome_slot_order": ["YES", "NO"],
            },
        )
    )

    assert row["classification"] == "OFFICIAL_FREE_RESOLVED"
    assert row["terminal_outcome"] == "YES"
    assert row["historical_provenance_status"] == "MISSING_EVENT_BLOCK_RECEIPT"


def test_ambiguous_ctf_payout_vector_is_ambiguous() -> None:
    row = classify_provisional_evidence(
        _evidence(
            ctf={
                "payout_vector": [1, 1],
                "payout_denominator": 1,
                "outcome_slot_order": ["YES", "NO"],
            }
        )
    )

    assert row["classification"] == "AMBIGUOUS"
    assert row["terminal_outcome"] is None


def test_unresolved_case_remains_unresolved() -> None:
    row = classify_provisional_evidence(
        _evidence(gamma={"closed": False}, clob={"closed": False})
    )

    assert row["classification"] == "UNRESOLVED"
    assert row["terminal_outcome"] is None


def test_local_snapshot_is_proxy_only_and_cannot_decide_outcome() -> None:
    row = classify_provisional_evidence(
        _evidence(local_snapshot={"proxy_winner": "YES", "near_close": True})
    )

    assert row["classification"] == "UNRESOLVED"
    assert row["source_classes"]["local_snapshot"] == "PROXY_ONLY"


def test_missing_identity_fails_closed() -> None:
    with pytest.raises(ProvisionalOutcomeError, match="condition_id"):
        classify_provisional_evidence(_evidence(condition_id=None))


def test_build_output_and_hash_are_deterministic(tmp_path: Path) -> None:
    evidence = [
        _evidence(
            condition_id="0xbbb",
            normalized_epoch_start_ts=200,
            gamma={"closed": True, "winner": "NO"},
            clob={"closed": True, "winner": "NO"},
        ),
        _evidence(
            condition_id="0xaaa",
            normalized_epoch_start_ts=100,
            gamma={"closed": True, "winner": "YES"},
            clob={"closed": True, "winner": "YES"},
        ),
    ]
    first_path = _write_jsonl(tmp_path / "first.jsonl", evidence)
    second_path = _write_jsonl(tmp_path / "second.jsonl", list(reversed(evidence)))

    first = build_provisional_outcomes(first_path, tmp_path / "first-out")
    second = build_provisional_outcomes(second_path, tmp_path / "second-out")
    first_bytes = (tmp_path / "first-out" / "provisional_outcomes.jsonl").read_bytes()
    second_bytes = (tmp_path / "second-out" / "provisional_outcomes.jsonl").read_bytes()

    assert first_bytes == second_bytes
    assert first == second
    assert first["output_sha256"] == hashlib.sha256(first_bytes).hexdigest()


def test_no_paid_provider_dependency_or_runtime_imports() -> None:
    source = Path("tools/outcome_truth/free_outcome_truth_provisional.py").read_text(encoding="utf-8")

    for forbidden in ("chainstack", "quicknode", "alchemy", "infura", "main.py", "polymarket.trader"):
        assert forbidden not in source.lower()
