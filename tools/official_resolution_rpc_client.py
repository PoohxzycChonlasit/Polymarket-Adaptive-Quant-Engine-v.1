"""Credential-safe archive Polygon JSON-RPC client for offline outcome research."""
from __future__ import annotations

import hashlib
import os
import random
import time
from typing import Any, Callable, Mapping

import requests


ARCHIVE_RPC_ENV_VAR = "POLYGON_ARCHIVE_RPC_URL"
DEFAULT_LOG_CHUNK_SIZE = 10_000
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_ATTEMPTS = 4
RETRY_DELAYS_SECONDS = (5.0, 30.0, 120.0)


class ArchiveRpcError(RuntimeError):
    """Credential-safe archive RPC failure."""


Transport = Callable[[str, dict[str, Any], float], Any]


def _endpoint_fingerprint(endpoint: str) -> str:
    return "sha256:" + hashlib.sha256(endpoint.encode("utf-8")).hexdigest()


def _default_transport(endpoint: str, payload: dict[str, Any], timeout: float) -> Any:
    return requests.post(endpoint, json=payload, timeout=timeout)


class ArchiveRpcClient:
    """Small fail-closed JSON-RPC client that never exposes its endpoint."""

    def __init__(
        self,
        *,
        endpoint: str,
        log_chunk_size: int = DEFAULT_LOG_CHUNK_SIZE,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        transport: Transport = _default_transport,
        sleep_fn: Callable[[float], None] = time.sleep,
        jitter_fn: Callable[[], float] = random.random,
    ) -> None:
        if not endpoint:
            raise ArchiveRpcError(f"missing required environment variable {ARCHIVE_RPC_ENV_VAR}")
        if log_chunk_size <= 0:
            raise ValueError("log_chunk_size must be positive")
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        self._endpoint = endpoint
        self._transport = transport
        self._sleep_fn = sleep_fn
        self._jitter_fn = jitter_fn
        self._timeout_seconds = float(timeout_seconds)
        self._max_attempts = int(max_attempts)
        self.log_chunk_size = int(log_chunk_size)
        self.rpc_endpoint_fingerprint = _endpoint_fingerprint(endpoint)
        self._request_id = 0

    @classmethod
    def from_env(
        cls,
        *,
        env: Mapping[str, str] | None = None,
        log_chunk_size: int = DEFAULT_LOG_CHUNK_SIZE,
        **kwargs: Any,
    ) -> "ArchiveRpcClient":
        source = os.environ if env is None else env
        endpoint = source.get(ARCHIVE_RPC_ENV_VAR, "")
        if not endpoint:
            raise ArchiveRpcError(f"missing required environment variable {ARCHIVE_RPC_ENV_VAR}")
        return cls(endpoint=endpoint, log_chunk_size=log_chunk_size, **kwargs)

    def public_metadata(self) -> dict[str, Any]:
        return {
            "log_chunk_size": self.log_chunk_size,
            "rpc_endpoint_fingerprint": self.rpc_endpoint_fingerprint,
        }

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _retry_delay(self, attempt: int, response: Any | None = None) -> float:
        if response is not None:
            retry_after = getattr(response, "headers", {}).get("Retry-After")
            if retry_after is not None:
                try:
                    return max(0.0, float(retry_after)) + max(
                        0.0, float(self._jitter_fn())
                    )
                except (TypeError, ValueError):
                    pass
        index = min(attempt - 1, len(RETRY_DELAYS_SECONDS) - 1)
        return RETRY_DELAYS_SECONDS[index] + max(0.0, float(self._jitter_fn()))

    def _request(self, method: str, params: list[Any]) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._next_id(),
        }
        for attempt in range(1, self._max_attempts + 1):
            response = None
            try:
                response = self._transport(self._endpoint, payload, self._timeout_seconds)
                status = int(getattr(response, "status_code", 0))
                if status == 429 or 500 <= status <= 599:
                    if attempt >= self._max_attempts:
                        raise ArchiveRpcError(
                            f"archive RPC transient HTTP failure after {attempt} attempts"
                        )
                    self._sleep_fn(self._retry_delay(attempt, response))
                    continue
                if status < 200 or status >= 300:
                    raise ArchiveRpcError(f"archive RPC HTTP failure status={status}")
                result = response.json()
                if not isinstance(result, dict):
                    raise ArchiveRpcError("archive RPC returned a non-object response")
                if result.get("error"):
                    raise ArchiveRpcError("archive RPC returned a JSON-RPC error")
                return result
            except ArchiveRpcError:
                raise
            except (requests.Timeout, requests.ConnectionError, ConnectionError, TimeoutError):
                if attempt >= self._max_attempts:
                    raise ArchiveRpcError(
                        f"archive RPC transport failure after {attempt} attempts"
                    ) from None
                self._sleep_fn(self._retry_delay(attempt, response))
            except (ValueError, TypeError):
                raise ArchiveRpcError("archive RPC response decoding failed") from None
            except Exception:
                raise ArchiveRpcError("archive RPC unexpected transport failure") from None
        raise ArchiveRpcError("archive RPC request failed")

    def call(self, method: str, params: list[Any]) -> dict[str, Any]:
        if method == "eth_getLogs":
            if len(params) != 1 or not isinstance(params[0], dict):
                raise ArchiveRpcError("eth_getLogs requires one query object")
            return self.eth_get_logs(params[0])
        return self._request(method, params)

    def eth_chain_id(self) -> dict[str, Any]:
        return self._request("eth_chainId", [])

    def eth_block_number(self) -> dict[str, Any]:
        return self._request("eth_blockNumber", [])

    def eth_get_block_by_number(
        self, block_number: str, full_transactions: bool = False
    ) -> dict[str, Any]:
        return self._request("eth_getBlockByNumber", [block_number, full_transactions])

    def eth_get_transaction_receipt(self, transaction_hash: str) -> dict[str, Any]:
        return self._request("eth_getTransactionReceipt", [transaction_hash])

    def eth_call(self, transaction: dict[str, Any], block_number: str) -> dict[str, Any]:
        return self._request("eth_call", [transaction, block_number])

    def eth_get_logs(self, query: dict[str, Any]) -> dict[str, Any]:
        if "fromBlock" not in query or "toBlock" not in query:
            return self._request("eth_getLogs", [dict(query)])
        start = int(str(query["fromBlock"]), 16)
        end = int(str(query["toBlock"]), 16)
        if end < start:
            raise ArchiveRpcError("eth_getLogs block range is invalid")
        logs: list[Any] = []
        cursor = start
        last_response: dict[str, Any] | None = None
        while cursor <= end:
            range_end = min(end, cursor + self.log_chunk_size - 1)
            chunk_query = dict(query)
            chunk_query["fromBlock"] = hex(cursor)
            chunk_query["toBlock"] = hex(range_end)
            last_response = self._request("eth_getLogs", [chunk_query])
            chunk_logs = last_response.get("result")
            if not isinstance(chunk_logs, list):
                raise ArchiveRpcError("eth_getLogs result is not a list")
            logs.extend(chunk_logs)
            cursor = range_end + 1
        response = dict(last_response or {"jsonrpc": "2.0", "id": self._next_id()})
        response["result"] = logs
        return response
