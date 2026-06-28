from __future__ import annotations

import json
from pathlib import Path

from tools.outcome_truth.official_resolution_acquire_pilot import (
    CONDITION_RESOLUTION_TOPIC,
    CTF_CONTRACT,
    build_pilot_package,
    verify_pilot_package,
)


def _selected() -> list[dict]:
    return [
        {
            "condition_id": "0x" + "11" * 32,
            "asset": "ETH",
            "market_slug": "eth-updown-5m-1",
            "epoch_start_ts": 1,
            "rationale": "normal resolved market",
        },
        {
            "condition_id": "0x" + "22" * 32,
            "asset": "BTC",
            "market_slug": "btc-updown-5m-2",
            "epoch_start_ts": 2,
            "rationale": "unresolved market",
        },
    ]


def _event_data(payouts: list[int]) -> str:
    words = [
        len(payouts),
        64,
        len(payouts),
        *payouts,
    ]
    return "0x" + "".join(value.to_bytes(32, "big").hex() for value in words)


def _dependencies(*, include_event: bool = True, event_payouts: list[int] | None = None):
    selected = _selected()

    def get_json(url: str) -> object:
        condition_id = url.rsplit("/", 1)[-1]
        if "gamma" in url:
            return []
        return {
            "condition_id": condition_id,
            "market_slug": selected[0]["market_slug"],
            "closed": condition_id == selected[0]["condition_id"],
            "tokens": [
                {"outcome": "Up", "winner": True},
                {"outcome": "Down", "winner": False},
            ],
        }

    def rpc_call(method: str, params: list) -> dict:
        if method == "eth_blockNumber":
            return {"jsonrpc": "2.0", "id": 1, "result": "0x64"}
        if method == "eth_getBlockByNumber":
            block_number = int(params[0], 16)
            return {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "number": params[0],
                    "hash": "0x" + "ab" * 32,
                    "timestamp": hex(block_number),
                },
            }
        if method == "eth_getTransactionReceipt":
            return {"jsonrpc": "2.0", "id": 1, "result": {"transactionHash": params[0], "logs": []}}
        if method == "eth_getLogs":
            condition_id = params[0]["topics"][1]
            resolved = condition_id == selected[0]["condition_id"]
            if not include_event or not resolved:
                return {"jsonrpc": "2.0", "id": 1, "result": []}
            payouts = event_payouts or [1, 0]
            return {
                "jsonrpc": "2.0",
                "id": 1,
                "result": [
                    {
                        "address": CTF_CONTRACT,
                        "blockNumber": "0x32",
                        "blockHash": "0x" + "cd" * 32,
                        "transactionHash": "0x" + "ef" * 32,
                        "logIndex": "0x1",
                        "topics": [
                            CONDITION_RESOLUTION_TOPIC,
                            condition_id,
                            "0x" + "00" * 12 + "12" * 20,
                            "0x" + "34" * 32,
                        ],
                        "data": _event_data(payouts),
                    }
                ],
            }
        data = params[0].get("data", "") if method == "eth_call" else ""
        condition_id = "0x" + data[10:74]
        resolved = condition_id == selected[0]["condition_id"]
        if data.startswith("0xdd34de67"):
            value = 1 if resolved else 0
        elif data.endswith("0" * 63 + "0"):
            value = 1 if resolved else 0
        else:
            value = 0
        return {"jsonrpc": "2.0", "id": 1, "result": hex(value)}

    return get_json, rpc_call


def test_build_and_replay_verify_hardened_pilot_package(tmp_path: Path) -> None:
    selected = _selected()
    get_json, rpc_call = _dependencies()

    result = build_pilot_package(
        selected=selected,
        output_dir=tmp_path / "pilot",
        get_json=get_json,
        rpc_call=rpc_call,
    )

    assert result["canonical_counts"] == {
        "OFFICIAL_RESOLVED": 1,
        "OFFICIAL_UNRESOLVED": 1,
    }
    assert (tmp_path / "pilot" / "manifest.json").exists()
    assert (tmp_path / "pilot" / "canonical" / "outcome_rows.jsonl").exists()
    assert (tmp_path / "pilot" / "COMMITTED").exists()

    verification = verify_pilot_package(tmp_path / "pilot")
    assert verification["status"] == "PASS"
    assert verification["canonical_rows"] == 2
    assert verification["event_state_consistency"] is True
    rows = [
        json.loads(line)
        for line in (tmp_path / "pilot" / "canonical" / "outcome_rows.jsonl").read_text().splitlines()
    ]
    assert rows[0]["resolution_block_number"] == 50
    assert rows[0]["resolution_transaction_hash"] == "0x" + "ef" * 32
    assert rows[0]["uma_lineage_status"] == "UMA_LINEAGE_NOT_FOUND"
    assert rows[1]["uma_lineage_status"] == "UMA_LINEAGE_NOT_APPLICABLE_UNRESOLVED"


def test_replay_verifier_fails_on_raw_evidence_mutation(tmp_path: Path) -> None:
    selected = _selected()[:1]
    get_json, rpc_call = _dependencies()

    build_pilot_package(
        selected=selected,
        output_dir=tmp_path / "pilot",
        get_json=get_json,
        rpc_call=rpc_call,
    )
    raw_file = next((tmp_path / "pilot" / "raw").rglob("*.json"))
    raw_file.write_text(json.dumps({"changed": True}), encoding="utf-8")

    verification = verify_pilot_package(tmp_path / "pilot")
    assert verification["status"] == "FAIL"
    assert verification["hash_failures"]


def test_replay_verifier_requires_event_provenance_for_resolved_state(tmp_path: Path) -> None:
    get_json, rpc_call = _dependencies(include_event=False)
    build_pilot_package(
        selected=_selected()[:1],
        output_dir=tmp_path / "pilot",
        get_json=get_json,
        rpc_call=rpc_call,
    )

    verification = verify_pilot_package(tmp_path / "pilot")

    assert verification["status"] == "FAIL"
    assert verification["required_evidence_failures"][0]["reason"] == "resolved_state_missing_condition_resolution_event"


def test_replay_verifier_requires_final_state_evidence(tmp_path: Path) -> None:
    get_json, rpc_call = _dependencies()
    build_pilot_package(
        selected=_selected()[:1],
        output_dir=tmp_path / "pilot",
        get_json=get_json,
        rpc_call=rpc_call,
    )
    next((tmp_path / "pilot" / "raw" / "ctf_state").glob("*.json")).unlink()

    verification = verify_pilot_package(tmp_path / "pilot")

    assert verification["status"] == "FAIL"
    assert verification["hash_failures"]


def test_missing_uma_lineage_is_explicit_and_does_not_block_final_ctf_truth(tmp_path: Path) -> None:
    get_json, rpc_call = _dependencies()
    build_pilot_package(
        selected=_selected()[:1],
        output_dir=tmp_path / "pilot",
        get_json=get_json,
        rpc_call=rpc_call,
    )

    verification = verify_pilot_package(tmp_path / "pilot")
    row = json.loads((tmp_path / "pilot" / "canonical" / "outcome_rows.jsonl").read_text().splitlines()[0])

    assert row["uma_lineage_status"] == "UMA_LINEAGE_NOT_FOUND"
    assert verification["status"] == "PASS"


def test_replay_verifier_fails_on_event_state_conflict(tmp_path: Path) -> None:
    get_json, rpc_call = _dependencies(event_payouts=[0, 1])
    build_pilot_package(
        selected=_selected()[:1],
        output_dir=tmp_path / "pilot",
        get_json=get_json,
        rpc_call=rpc_call,
    )

    verification = verify_pilot_package(tmp_path / "pilot")

    assert verification["status"] == "FAIL"
    assert verification["terminal_conflicts"]


def test_event_acquisition_never_exceeds_rpc_block_range(tmp_path: Path) -> None:
    get_json, base_rpc_call = _dependencies()
    observed_ranges: list[tuple[int, int]] = []

    def rpc_call(method: str, params: list) -> dict:
        if method == "eth_blockNumber":
            return {"jsonrpc": "2.0", "id": 1, "result": hex(1_000_000)}
        if method == "eth_getBlockByNumber":
            block_number = int(params[0], 16)
            return {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "number": params[0],
                    "hash": "0x" + "ab" * 32,
                    "timestamp": hex(block_number),
                },
            }
        if method == "eth_getLogs":
            start = int(params[0]["fromBlock"], 16)
            end = int(params[0]["toBlock"], 16)
            observed_ranges.append((start, end))
            if end - start + 1 > 10_000:
                raise RuntimeError("exceed maximum block range: 10000")
            return {"jsonrpc": "2.0", "id": 1, "result": []}
        return base_rpc_call(method, params)

    build_pilot_package(
        selected=_selected()[1:2],
        output_dir=tmp_path / "pilot",
        get_json=get_json,
        rpc_call=rpc_call,
    )

    assert observed_ranges
    assert all(end - start + 1 <= 10_000 for start, end in observed_ranges)


def test_pilot_manifest_stores_only_rpc_fingerprint_and_uses_chunk_override(
    tmp_path: Path,
) -> None:
    get_json, base_rpc_call = _dependencies()
    observed_ranges: list[tuple[int, int]] = []

    def rpc_call(method: str, params: list) -> dict:
        if method == "eth_blockNumber":
            return {"jsonrpc": "2.0", "id": 1, "result": hex(1_000)}
        if method == "eth_getBlockByNumber":
            block_number = int(params[0], 16)
            return {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "number": params[0],
                    "hash": "0x" + "ab" * 32,
                    "timestamp": hex(block_number),
                },
            }
        if method == "eth_getLogs":
            start = int(params[0]["fromBlock"], 16)
            end = int(params[0]["toBlock"], 16)
            observed_ranges.append((start, end))
            return {"jsonrpc": "2.0", "id": 1, "result": []}
        return base_rpc_call(method, params)

    build_pilot_package(
        selected=_selected()[1:2],
        output_dir=tmp_path / "pilot",
        get_json=get_json,
        rpc_call=rpc_call,
        rpc_endpoint_fingerprint="sha256:abc123",
        max_log_block_range=10,
    )
    manifest_text = (tmp_path / "pilot" / "manifest.json").read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)

    assert manifest["rpc_endpoint_fingerprint"] == "sha256:abc123"
    assert "rpc_url" not in manifest_text
    assert observed_ranges
    assert all(end - start + 1 <= 10 for start, end in observed_ranges)


def test_production_runner_can_disable_pilot_sample_size_gate(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    get_json, rpc_call = _dependencies()

    result = build_pilot_package(
        selected=_selected()[:1],
        output_dir=tmp_path / "package",
        get_json=get_json,
        rpc_call=rpc_call,
        enforce_pilot_size=False,
    )

    assert result["canonical_counts"] == {"OFFICIAL_RESOLVED": 1}
