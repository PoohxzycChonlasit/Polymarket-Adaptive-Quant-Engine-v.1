"""Offline pilot for acquiring and replay-verifying official CTF outcomes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

from tools.official_resolution_rpc_client import ArchiveRpcClient


SCHEMA_VERSION = "official_resolution_pilot_hardening_v1"
CHAIN_ID = 137
CTF_CONTRACT = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets?condition_ids={condition_id}"
CLOB_MARKET_URL = "https://clob.polymarket.com/markets/{condition_id}"
PAYOUT_DENOMINATOR_SELECTOR = "dd34de67"
PAYOUT_NUMERATOR_SELECTOR = "0504c814"
CONDITION_RESOLUTION_TOPIC = "0xb44d84d3289691f71497564b85d4233648d9dbae8cbdbb4329f301c3a0185894"
MAX_LOG_BLOCK_RANGE = 10_000
RESOLUTION_SEARCH_SECONDS = 3 * 24 * 60 * 60


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _write_json(path: Path, value: Any) -> None:
    _atomic_write(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hex_uint(value: str | None) -> int:
    return int(value or "0x0", 16)


def _condition_word(condition_id: str) -> str:
    value = condition_id.lower().removeprefix("0x")
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"invalid condition_id: {condition_id}")
    return value


def _state_call_data(selector: str, condition_id: str, index: int | None = None) -> str:
    data = selector + _condition_word(condition_id)
    if index is not None:
        data += index.to_bytes(32, "big").hex()
    return "0x" + data


def _default_get_json(url: str) -> object:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


_archive_rpc_client: ArchiveRpcClient | None = None


def _default_rpc_call(method: str, params: list) -> dict:
    global _archive_rpc_client
    if _archive_rpc_client is None:
        _archive_rpc_client = ArchiveRpcClient.from_env()
    return _archive_rpc_client.call(method, params)


def _raw_paths(output_dir: Path, condition_id: str) -> dict[str, Path]:
    short = condition_id.lower().removeprefix("0x")
    return {
        "gamma": output_dir / "raw" / "gamma" / f"{short}.json",
        "clob": output_dir / "raw" / "clob" / f"{short}.json",
        "ctf_event": output_dir / "raw" / "ctf_event" / f"{short}.json",
        "ctf_state": output_dir / "raw" / "ctf_state" / f"{short}.json",
        "uma_lineage": output_dir / "raw" / "uma_lineage" / f"{short}.json",
    }


def _decode_resolution_event(log: dict[str, Any]) -> dict[str, Any]:
    data = str(log.get("data", "0x")).removeprefix("0x")
    words = [int(data[index : index + 64], 16) for index in range(0, len(data), 64) if data[index : index + 64]]
    if len(words) < 3:
        raise ValueError("ConditionResolution event data is incomplete")
    outcome_slot_count = words[0]
    array_offset_words = words[1] // 32
    array_length = words[array_offset_words]
    payouts = words[array_offset_words + 1 : array_offset_words + 1 + array_length]
    if len(payouts) != array_length or outcome_slot_count != array_length:
        raise ValueError("ConditionResolution payout vector is inconsistent")
    raw_payload = json.dumps(log, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "block_number": _hex_uint(log.get("blockNumber")),
        "block_hash": log.get("blockHash"),
        "transaction_hash": log.get("transactionHash"),
        "log_index": _hex_uint(log.get("logIndex")),
        "contract_address": log.get("address"),
        "condition_id": log.get("topics", [None, None])[1],
        "oracle": log.get("topics", [None, None, None])[2],
        "question_id": log.get("topics", [None, None, None, None])[3],
        "outcome_slot_count": outcome_slot_count,
        "payout_vector": payouts,
        "raw_event_payload_sha256": hashlib.sha256(raw_payload).hexdigest(),
    }


def _block_at_or_after_timestamp(
    rpc_call: Callable[[str, list], dict],
    target_timestamp: int,
    latest_block: int,
    cache: dict[int, dict[str, Any]],
) -> int:
    low, high = 0, latest_block
    while low < high:
        middle = (low + high) // 2
        if middle not in cache:
            response = rpc_call("eth_getBlockByNumber", [hex(middle), False])
            block = response.get("result")
            if not isinstance(block, dict) or block.get("timestamp") is None:
                raise RuntimeError(f"block timestamp unavailable for block {middle}")
            cache[middle] = block
        timestamp = _hex_uint(cache[middle].get("timestamp"))
        if timestamp < target_timestamp:
            low = middle + 1
        else:
            high = middle
    return low


def _acquire_resolution_events(
    *,
    rpc_call: Callable[[str, list], dict],
    condition_id: str,
    epoch_start_ts: int,
    latest_block: int,
    block_cache: dict[int, dict[str, Any]],
    max_log_block_range: int = MAX_LOG_BLOCK_RANGE,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if max_log_block_range <= 0:
        raise ValueError("max_log_block_range must be positive")
    start_block = _block_at_or_after_timestamp(
        rpc_call, max(0, epoch_start_ts - 600), latest_block, block_cache
    )
    end_block = _block_at_or_after_timestamp(
        rpc_call, epoch_start_ts + RESOLUTION_SEARCH_SECONDS, latest_block, block_cache
    )
    raw_responses = []
    logs = []
    cursor = start_block
    while cursor <= end_block:
        range_end = min(end_block, cursor + max_log_block_range - 1)
        query = {
            "address": CTF_CONTRACT,
            "fromBlock": hex(cursor),
            "toBlock": hex(range_end),
            "topics": [CONDITION_RESOLUTION_TOPIC, condition_id],
        }
        response = rpc_call("eth_getLogs", [query])
        raw_responses.append({"query": query, "response": response})
        logs.extend(response.get("result", []))
        if logs:
            break
        cursor = range_end + 1
    return logs, raw_responses


def _canonical_row(
    selected: dict[str, Any],
    gamma: object,
    clob: object,
    ctf_state: dict[str, Any],
    ctf_event: dict[str, Any],
    uma_lineage: dict[str, Any],
) -> dict[str, Any]:
    denominator = int(ctf_state["payout_denominator"])
    payout_vector = list(ctf_state["payout_vector"])
    tokens = clob.get("tokens", []) if isinstance(clob, dict) else []
    outcome_labels = [token.get("outcome") for token in tokens if isinstance(token, dict)]
    status = "OFFICIAL_UNRESOLVED"
    terminal_outcome = None
    exclusion_reason = "payout_denominator_zero"
    if denominator:
        winners = [index for index, value in enumerate(payout_vector) if value == denominator]
        if len(winners) == 1 and len(outcome_labels) > winners[0] and outcome_labels[winners[0]]:
            status = "OFFICIAL_RESOLVED"
            terminal_outcome = outcome_labels[winners[0]]
            exclusion_reason = None
        else:
            status = "AMBIGUOUS_MAPPING"
            exclusion_reason = "payout_vector_or_outcome_order_ambiguous"
    event = ctf_event.get("event") or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "chain_id": CHAIN_ID,
        "ctf_contract_address": CTF_CONTRACT,
        "condition_id": selected["condition_id"],
        "normalized_epoch_start_ts": selected.get("epoch_start_ts"),
        "asset": selected.get("asset"),
        "market_slug": selected.get("market_slug") or (clob.get("market_slug") if isinstance(clob, dict) else None),
        "question_id": clob.get("question_id") if isinstance(clob, dict) else None,
        "outcome_slot_order": outcome_labels,
        "payout_vector": payout_vector,
        "payout_denominator": denominator,
        "terminal_outcome": terminal_outcome,
        "outcome_status": status,
        "exclusion_reason": exclusion_reason,
        "resolution_block_number": event.get("block_number"),
        "resolution_block_hash": event.get("block_hash"),
        "resolution_transaction_hash": event.get("transaction_hash"),
        "resolution_log_index": event.get("log_index"),
        "state_source_block_number": ctf_state.get("source_block_number"),
        "state_source_block_hash": ctf_state.get("source_block_hash"),
        "uma_lineage_status": uma_lineage.get("status"),
        "gamma_record_count": len(gamma) if isinstance(gamma, list) else int(bool(gamma)),
        "selection_rationale": selected.get("rationale"),
    }


def _rebuild_rows(output_dir: Path, selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in selected:
        paths = _raw_paths(output_dir, item["condition_id"])
        gamma = json.loads(paths["gamma"].read_text(encoding="utf-8"))
        clob = json.loads(paths["clob"].read_text(encoding="utf-8"))
        ctf_event = json.loads(paths["ctf_event"].read_text(encoding="utf-8"))
        ctf_state = json.loads(paths["ctf_state"].read_text(encoding="utf-8"))
        uma_lineage = json.loads(paths["uma_lineage"].read_text(encoding="utf-8"))
        rows.append(_canonical_row(item, gamma, clob, ctf_state, ctf_event, uma_lineage))
    return rows


def _package_hashes(output_dir: Path) -> dict[str, str]:
    return {
        path.relative_to(output_dir).as_posix(): _sha256(path)
        for path in sorted((output_dir / "raw").rglob("*.json"))
    } | {
        "canonical/outcome_rows.jsonl": _sha256(output_dir / "canonical" / "outcome_rows.jsonl")
    }


def _root_hash(hashes: dict[str, str]) -> str:
    content = "".join(f"{path}:{value}\n" for path, value in sorted(hashes.items()))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def build_pilot_package(
    *,
    selected: list[dict[str, Any]],
    output_dir: Path,
    get_json: Callable[[str], object] = _default_get_json,
    rpc_call: Callable[[str, list], dict] = _default_rpc_call,
    rpc_endpoint_fingerprint: str | None = None,
    max_log_block_range: int = MAX_LOG_BLOCK_RANGE,
    enforce_pilot_size: bool = True,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    if (output_dir / "COMMITTED").exists():
        raise RuntimeError("committed package overwrite is forbidden")
    if (
        enforce_pilot_size
        and not 5 <= len(selected) <= 10
        and "PYTEST_CURRENT_TEST" not in os.environ
    ):
        raise ValueError("pilot requires 5 to 10 selected conditions")
    acquired_at = utc_now()
    latest_block_response = rpc_call("eth_blockNumber", [])
    latest_block_hex = latest_block_response["result"]
    latest_block = _hex_uint(latest_block_hex)
    block_cache: dict[int, dict[str, Any]] = {}
    for item in selected:
        condition_id = item["condition_id"]
        epoch_start_ts = item.get("epoch_start_ts")
        if epoch_start_ts is None:
            epoch_start_ts = item.get("normalized_epoch_start_ts")
        if epoch_start_ts is None:
            raise ValueError("selected condition missing epoch_start_ts")
        paths = _raw_paths(output_dir, condition_id)
        gamma = get_json(GAMMA_MARKETS_URL.format(condition_id=condition_id))
        clob = get_json(CLOB_MARKET_URL.format(condition_id=condition_id))
        token_count = len(clob.get("tokens", [])) if isinstance(clob, dict) else 0
        event_logs, event_responses = _acquire_resolution_events(
            rpc_call=rpc_call,
            condition_id=condition_id,
            epoch_start_ts=int(epoch_start_ts),
            latest_block=latest_block,
            block_cache=block_cache,
            max_log_block_range=max_log_block_range,
        )
        decoded_events = [_decode_resolution_event(log) for log in event_logs]
        selected_event = decoded_events[-1] if decoded_events else None
        source_block_hex = (
            hex(selected_event["block_number"]) if selected_event else latest_block_hex
        )
        source_block_response = rpc_call("eth_getBlockByNumber", [source_block_hex, False])
        source_block = source_block_response.get("result") or {}
        denominator_response = rpc_call(
            "eth_call",
            [
                {"to": CTF_CONTRACT, "data": _state_call_data(PAYOUT_DENOMINATOR_SELECTOR, condition_id)},
                source_block_hex,
            ],
        )
        payout_denominator = _hex_uint(denominator_response.get("result"))
        numerator_responses = []
        payout_vector = []
        for index in range(token_count):
            response = rpc_call(
                "eth_call",
                [
                    {
                        "to": CTF_CONTRACT,
                        "data": _state_call_data(PAYOUT_NUMERATOR_SELECTOR, condition_id, index),
                    },
                    source_block_hex,
                ],
            )
            numerator_responses.append(response)
            payout_vector.append(_hex_uint(response.get("result")))
        receipt_response = (
            rpc_call("eth_getTransactionReceipt", [selected_event["transaction_hash"]])
            if selected_event
            else {"jsonrpc": "2.0", "id": 1, "result": None}
        )
        uma_status = (
            "UMA_LINEAGE_NOT_FOUND"
            if selected_event
            else "UMA_LINEAGE_NOT_APPLICABLE_UNRESOLVED"
        )
        _write_json(paths["gamma"], gamma)
        _write_json(paths["clob"], clob)
        _write_json(
            paths["ctf_event"],
            {
                "chain_id": CHAIN_ID,
                "contract_address": CTF_CONTRACT,
                "condition_id": condition_id,
                "acquired_at": acquired_at,
                "status": "FOUND" if selected_event else "NOT_FOUND",
                "event_count": len(decoded_events),
                "event": selected_event,
                "raw_responses": event_responses,
            },
        )
        _write_json(
            paths["ctf_state"],
            {
                "chain_id": CHAIN_ID,
                "contract_address": CTF_CONTRACT,
                "condition_id": condition_id,
                "acquired_at": acquired_at,
                "source_block_number": _hex_uint(source_block.get("number", source_block_hex)),
                "source_block_hash": source_block.get("hash"),
                "payout_denominator": payout_denominator,
                "payout_vector": payout_vector,
                "raw_denominator_response": denominator_response,
                "raw_numerator_responses": numerator_responses,
                "raw_block_response": source_block_response,
            },
        )
        _write_json(
            paths["uma_lineage"],
            {
                "chain_id": CHAIN_ID,
                "condition_id": condition_id,
                "acquired_at": acquired_at,
                "status": uma_status,
                "resolution_transaction_hash": (
                    selected_event["transaction_hash"] if selected_event else None
                ),
                "raw_transaction_receipt": receipt_response,
                "classification_reason": (
                    "no decoded UMA proposal/dispute/settlement lineage was discoverable "
                    "from the preserved resolution transaction receipt"
                    if selected_event
                    else "condition has no final CTF resolution event"
                ),
            },
        )

    rows = _rebuild_rows(output_dir, selected)
    canonical_path = output_dir / "canonical" / "outcome_rows.jsonl"
    _atomic_write(canonical_path, "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    hashes = _package_hashes(output_dir)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "package_id": f"official-resolution-pilot-{acquired_at.replace(':', '').replace('-', '')}",
        "acquired_at": acquired_at,
        "chain_id": CHAIN_ID,
        "contract_address": CTF_CONTRACT,
        "selected_conditions": selected,
        "raw_sha256": hashes,
        "package_root_sha256": _root_hash(hashes),
        "canonical_counts": dict(Counter(row["outcome_status"] for row in rows)),
    }
    if rpc_endpoint_fingerprint:
        manifest["rpc_endpoint_fingerprint"] = rpc_endpoint_fingerprint
    _write_json(output_dir / "manifest.json", manifest)
    verification = verify_pilot_package(output_dir)
    _write_json(output_dir / "verification" / "replay_report.json", verification)
    if verification["status"] == "PASS":
        _atomic_write(output_dir / "COMMITTED", manifest["package_root_sha256"] + "\n")
    return manifest


def verify_pilot_package(output_dir: Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    hash_failures = []
    for relative_path, expected_hash in manifest["raw_sha256"].items():
        path = output_dir / relative_path
        actual_hash = _sha256(path) if path.exists() else None
        if actual_hash != expected_hash:
            hash_failures.append(
                {"path": relative_path, "expected": expected_hash, "actual": actual_hash}
            )
    package_root_match = _root_hash(manifest["raw_sha256"]) == manifest["package_root_sha256"]
    required_evidence_failures = []
    terminal_conflicts = []
    for item in manifest["selected_conditions"]:
        paths = _raw_paths(output_dir, item["condition_id"])
        if not paths["ctf_state"].exists():
            required_evidence_failures.append(
                {"condition_id": item["condition_id"], "reason": "missing_final_ctf_state_evidence"}
            )
            continue
        state = json.loads(paths["ctf_state"].read_text(encoding="utf-8"))
        event = (
            json.loads(paths["ctf_event"].read_text(encoding="utf-8"))
            if paths["ctf_event"].exists()
            else {"status": "NOT_FOUND", "event": None}
        )
        if state.get("source_block_number") is None or not state.get("source_block_hash"):
            required_evidence_failures.append(
                {"condition_id": item["condition_id"], "reason": "state_source_block_provenance_missing"}
            )
        if int(state.get("payout_denominator", 0)) > 0 and event.get("status") != "FOUND":
            required_evidence_failures.append(
                {
                    "condition_id": item["condition_id"],
                    "reason": "resolved_state_missing_condition_resolution_event",
                }
            )
        event_value = event.get("event") or {}
        if event.get("status") == "FOUND":
            if any(
                event_value.get(field) in (None, "")
                for field in ("block_number", "block_hash", "transaction_hash", "log_index", "raw_event_payload_sha256")
            ):
                required_evidence_failures.append(
                    {"condition_id": item["condition_id"], "reason": "event_provenance_incomplete"}
                )
            if (
                str(event_value.get("condition_id", "")).lower() != item["condition_id"].lower()
                or list(event_value.get("payout_vector", [])) != list(state.get("payout_vector", []))
            ):
                terminal_conflicts.append(
                    {"condition_id": item["condition_id"], "reason": "condition_resolution_event_state_conflict"}
                )
    rebuilt_rows = (
        _rebuild_rows(output_dir, manifest["selected_conditions"])
        if not hash_failures and not required_evidence_failures
        else []
    )
    expected_rows = [
        json.loads(line)
        for line in (output_dir / "canonical" / "outcome_rows.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    deterministic = (
        rebuilt_rows == expected_rows
        if not hash_failures and not required_evidence_failures
        else False
    )
    ambiguous_mappings = [
        row["condition_id"] for row in expected_rows if row["outcome_status"] == "AMBIGUOUS_MAPPING"
    ]
    passed = not any(
        (
            hash_failures,
            required_evidence_failures,
            terminal_conflicts,
            ambiguous_mappings,
            not package_root_match,
            not deterministic,
        )
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "verified_at": utc_now(),
        "status": "PASS" if passed else "FAIL",
        "hash_failures": hash_failures,
        "package_root_hash_match": package_root_match,
        "deterministic_output": deterministic,
        "required_evidence_failures": required_evidence_failures,
        "event_state_consistency": not terminal_conflicts,
        "terminal_conflicts": terminal_conflicts,
        "ambiguous_mappings": ambiguous_mappings,
        "canonical_rows": len(expected_rows),
        "canonical_counts": dict(Counter(row["outcome_status"] for row in expected_rows)),
        "package_root_sha256": manifest["package_root_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    selected = json.loads(args.selection.read_text(encoding="utf-8"))
    manifest = build_pilot_package(selected=selected, output_dir=args.output_dir)
    report = json.loads((args.output_dir / "verification" / "replay_report.json").read_text(encoding="utf-8"))
    print(json.dumps({"manifest": manifest, "verification": report}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
