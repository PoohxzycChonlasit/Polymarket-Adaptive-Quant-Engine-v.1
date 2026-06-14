from __future__ import annotations

import json

import pytest
import requests

from tools.official_resolution_rpc_client import (
    ARCHIVE_RPC_ENV_VAR,
    ArchiveRpcClient,
    ArchiveRpcError,
)


SECRET_ENDPOINT = "https://user:top-secret@polygon.example.invalid/archive-key"


class FakeResponse:
    def __init__(self, status_code: int, payload: dict, headers: dict | None = None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self) -> dict:
        return self._payload


def test_missing_credential_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ARCHIVE_RPC_ENV_VAR, raising=False)

    with pytest.raises(ArchiveRpcError, match=ARCHIVE_RPC_ENV_VAR):
        ArchiveRpcClient.from_env()


def test_environment_client_accepts_provider_chunk_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ARCHIVE_RPC_ENV_VAR, SECRET_ENDPOINT)

    client = ArchiveRpcClient.from_env(
        log_chunk_size=25,
        transport=lambda *_args: FakeResponse(200, {"jsonrpc": "2.0", "id": 1, "result": []}),
    )

    assert client.log_chunk_size == 25
    assert client.public_metadata()["log_chunk_size"] == 25


def test_endpoint_fingerprint_only_and_no_endpoint_leakage() -> None:
    def transport(_endpoint: str, _payload: dict, _timeout: float) -> FakeResponse:
        raise requests.ConnectionError(f"connection failed for {SECRET_ENDPOINT}")

    client = ArchiveRpcClient(
        endpoint=SECRET_ENDPOINT,
        transport=transport,
        sleep_fn=lambda _seconds: None,
        jitter_fn=lambda: 0.0,
        max_attempts=1,
    )

    with pytest.raises(ArchiveRpcError) as error:
        client.eth_chain_id()

    assert SECRET_ENDPOINT not in str(error.value)
    assert "top-secret" not in str(error.value)
    assert client.rpc_endpoint_fingerprint
    assert SECRET_ENDPOINT not in client.rpc_endpoint_fingerprint


def test_supported_rpc_methods_use_sanitized_transport() -> None:
    methods: list[str] = []

    def transport(_endpoint: str, payload: dict, _timeout: float) -> FakeResponse:
        methods.append(payload["method"])
        return FakeResponse(200, {"jsonrpc": "2.0", "id": payload["id"], "result": "0x1"})

    client = ArchiveRpcClient(endpoint=SECRET_ENDPOINT, transport=transport)

    client.eth_chain_id()
    client.eth_get_block_by_number("0x1")
    client.eth_get_transaction_receipt("0xabc")
    client.eth_call({"to": "0x1", "data": "0x2"}, "0x1")

    assert methods == [
        "eth_chainId",
        "eth_getBlockByNumber",
        "eth_getTransactionReceipt",
        "eth_call",
    ]


def test_eth_get_logs_paginates_with_default_chunk_size() -> None:
    queries: list[dict] = []

    def transport(_endpoint: str, payload: dict, _timeout: float) -> FakeResponse:
        query = payload["params"][0]
        queries.append(query)
        return FakeResponse(200, {"jsonrpc": "2.0", "id": payload["id"], "result": []})

    client = ArchiveRpcClient(endpoint=SECRET_ENDPOINT, transport=transport)
    response = client.eth_get_logs({"fromBlock": "0x0", "toBlock": hex(20_004)})

    assert response["result"] == []
    assert [(int(q["fromBlock"], 16), int(q["toBlock"], 16)) for q in queries] == [
        (0, 9_999),
        (10_000, 19_999),
        (20_000, 20_004),
    ]


def test_provider_chunk_override_is_respected() -> None:
    queries: list[dict] = []

    def transport(_endpoint: str, payload: dict, _timeout: float) -> FakeResponse:
        queries.append(payload["params"][0])
        return FakeResponse(200, {"jsonrpc": "2.0", "id": payload["id"], "result": []})

    client = ArchiveRpcClient(endpoint=SECRET_ENDPOINT, transport=transport, log_chunk_size=10)
    client.eth_get_logs({"fromBlock": "0x0", "toBlock": "0x18"})

    assert len(queries) == 3
    assert all(int(q["toBlock"], 16) - int(q["fromBlock"], 16) + 1 <= 10 for q in queries)


def test_http_429_retries_and_honors_retry_after() -> None:
    responses = [
        FakeResponse(429, {}, headers={"Retry-After": "7"}),
        FakeResponse(200, {"jsonrpc": "2.0", "id": 2, "result": "0x89"}),
    ]
    sleeps: list[float] = []

    client = ArchiveRpcClient(
        endpoint=SECRET_ENDPOINT,
        transport=lambda *_args: responses.pop(0),
        sleep_fn=sleeps.append,
        jitter_fn=lambda: 0.0,
    )

    assert client.eth_chain_id()["result"] == "0x89"
    assert sleeps == [7.0]


def test_timeout_retries_with_backoff() -> None:
    attempts = 0
    sleeps: list[float] = []

    def transport(_endpoint: str, _payload: dict, _timeout: float) -> FakeResponse:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise requests.Timeout("slow")
        return FakeResponse(200, {"jsonrpc": "2.0", "id": attempts, "result": "0x89"})

    client = ArchiveRpcClient(
        endpoint=SECRET_ENDPOINT,
        transport=transport,
        sleep_fn=sleeps.append,
        jitter_fn=lambda: 0.0,
    )

    assert client.eth_chain_id()["result"] == "0x89"
    assert sleeps == [5.0, 30.0]


def test_rpc_error_is_sanitized() -> None:
    response = FakeResponse(
        200,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32000, "message": f"bad endpoint {SECRET_ENDPOINT}"},
        },
    )
    client = ArchiveRpcClient(endpoint=SECRET_ENDPOINT, transport=lambda *_args: response)

    with pytest.raises(ArchiveRpcError) as error:
        client.eth_chain_id()

    assert SECRET_ENDPOINT not in str(error.value)
    assert "top-secret" not in str(error.value)


def test_unexpected_transport_error_is_sanitized() -> None:
    def transport(_endpoint: str, _payload: dict, _timeout: float) -> FakeResponse:
        raise RuntimeError(f"unexpected failure at {SECRET_ENDPOINT}")

    client = ArchiveRpcClient(endpoint=SECRET_ENDPOINT, transport=transport)

    with pytest.raises(ArchiveRpcError) as error:
        client.eth_chain_id()

    assert SECRET_ENDPOINT not in str(error.value)
    assert "top-secret" not in str(error.value)


def test_client_public_state_contains_no_endpoint() -> None:
    client = ArchiveRpcClient(endpoint=SECRET_ENDPOINT, transport=lambda *_args: None)

    serialized = json.dumps(client.public_metadata(), sort_keys=True)

    assert SECRET_ENDPOINT not in serialized
    assert "top-secret" not in serialized
    assert serialized == json.dumps(
        {
            "log_chunk_size": 10_000,
            "rpc_endpoint_fingerprint": client.rpc_endpoint_fingerprint,
        },
        sort_keys=True,
    )
