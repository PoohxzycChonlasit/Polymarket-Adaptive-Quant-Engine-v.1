"""Offline, resumable full-history orchestrator for official outcome packages.

This module is intentionally limited to mock/offline execution. It does not
import trading runtime modules and does not contain archive RPC credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SCHEMA_VERSION = "official_resolution_full_history_runner_v1"
CHECKPOINT_NAME = "checkpoint.json"
AGGREGATE_NAME = "aggregate_verification.json"
LOCK_NAME = ".full_history_runner.lock"
TRANSIENT_DELAYS_SECONDS = (5.0, 30.0, 120.0)


class IntegrityFailure(RuntimeError):
    """Raised when evidence cannot safely enter the committed population."""


class TransientAcquisitionError(RuntimeError):
    """Raised when an acquisition attempt may be retried safely."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_population_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    raw = manifest_path.read_bytes()
    payload = json.loads(raw)
    conditions = payload if isinstance(payload, list) else payload.get("conditions")
    if not isinstance(conditions, list) or not all(isinstance(item, dict) for item in conditions):
        raise IntegrityFailure("population manifest must contain a conditions list")
    for item in conditions:
        if not item.get("condition_id"):
            raise IntegrityFailure("population condition missing condition_id")
    return {
        "path": str(manifest_path.resolve()),
        "sha256": _sha256_bytes(raw),
        "conditions": conditions,
    }


def deterministic_batches(conditions: list[dict[str, Any]], batch_size: int = 10) -> list[dict[str, Any]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    batches = []
    for offset in range(0, len(conditions), batch_size):
        selected = conditions[offset : offset + batch_size]
        identity = "\n".join(str(item["condition_id"]).lower() for item in selected)
        suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
        index = offset // batch_size + 1
        batches.append(
            {
                "batch_id": f"batch-{index:06d}-{suffix}",
                "batch_index": index,
                "conditions": selected,
            }
        )
    return batches


def _new_batch_checkpoint(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "batch_id": batch["batch_id"],
        "batch_index": batch["batch_index"],
        "condition_ids": [item["condition_id"] for item in batch["conditions"]],
        "condition_count": len(batch["conditions"]),
        "status": "PENDING",
        "state_history": ["PENDING"],
        "attempt_count": 0,
        "last_success_at": None,
        "last_failure_at": None,
        "failure_class": None,
        "package_path": None,
        "package_root_sha256": None,
        "verification_status": None,
    }


def _new_checkpoint(
    manifest: dict[str, Any],
    batches: list[dict[str, Any]],
    batch_size: int,
    *,
    now_fn: Callable[[], str] = utc_now,
    rpc_endpoint_fingerprint: str | None = None,
) -> dict[str, Any]:
    checkpoint = {
        "schema_version": SCHEMA_VERSION,
        "created_at": now_fn(),
        "updated_at": now_fn(),
        "population_manifest_path": manifest["path"],
        "population_manifest_sha256": manifest["sha256"],
        "population_count": len(manifest["conditions"]),
        "batch_size": batch_size,
        "batches": [_new_batch_checkpoint(batch) for batch in batches],
    }
    if rpc_endpoint_fingerprint:
        checkpoint["rpc_endpoint_fingerprint"] = rpc_endpoint_fingerprint
    return checkpoint


def _write_checkpoint(
    output_dir: Path,
    checkpoint: dict[str, Any],
    *,
    now_fn: Callable[[], str] = utc_now,
) -> None:
    checkpoint["updated_at"] = now_fn()
    atomic_write_json(output_dir / CHECKPOINT_NAME, checkpoint)


def _transition(batch: dict[str, Any], status: str) -> None:
    batch["status"] = status
    if not batch["state_history"] or batch["state_history"][-1] != status:
        batch["state_history"].append(status)


def _mark_failed(
    batch: dict[str, Any],
    failure_class: str,
    *,
    now_fn: Callable[[], str] = utc_now,
) -> None:
    _transition(batch, "FAILED")
    batch["failure_class"] = failure_class
    batch["last_failure_at"] = now_fn()
    batch["verification_status"] = "FAIL"


def _mock_acquire_package(*, selected: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_hash = _sha256_bytes(
        json.dumps(selected, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    manifest = {
        "schema_version": "official_resolution_mock_package_v1",
        "selected_conditions": selected,
        "package_root_sha256": selected_hash,
    }
    atomic_write_json(output_dir / "manifest.json", manifest)
    _atomic_write(output_dir / "COMMITTED", selected_hash + "\n")
    return manifest


def _mock_verify_package(output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "manifest.json"
    committed_path = output_dir / "COMMITTED"
    if not manifest_path.exists() or not committed_path.exists():
        return {"status": "FAIL", "package_root_sha256": None}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = manifest.get("package_root_sha256")
    passed = bool(root) and committed_path.read_text(encoding="utf-8").strip() == root
    return {
        "status": "PASS" if passed else "FAIL",
        "package_root_sha256": root,
        "canonical_rows": len(manifest.get("selected_conditions", [])),
    }


def _package_manifest(package_dir: Path) -> dict[str, Any]:
    path = package_dir / "manifest.json"
    if not path.exists():
        raise IntegrityFailure("package manifest missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("package_root_sha256"):
        raise IntegrityFailure("package root hash missing")
    return payload


def _verify_committed_package(
    package_dir: Path, verify_package: Callable[[Path], dict[str, Any]]
) -> tuple[bool, str | None]:
    try:
        manifest = _package_manifest(package_dir)
        marker = package_dir / "COMMITTED"
        if not marker.exists():
            return False, None
        root = manifest["package_root_sha256"]
        if marker.read_text(encoding="utf-8").strip() != root:
            return False, root
        verification = verify_package(package_dir)
        return verification.get("status") == "PASS" and verification.get(
            "package_root_sha256"
        ) == root, root
    except (OSError, ValueError, json.JSONDecodeError, IntegrityFailure):
        return False, None


def aggregate_verify(
    *,
    conditions: list[dict[str, Any]],
    checkpoint: dict[str, Any],
    output_dir: Path,
    verify_package: Callable[[Path], dict[str, Any]],
) -> dict[str, Any]:
    expected_ids = [str(item["condition_id"]) for item in conditions]
    duplicate_ids = sorted(
        condition_id
        for condition_id, count in Counter(expected_ids).items()
        if count > 1
    )
    committed_ids: list[str] = []
    package_hash_failures: list[str] = []
    committed_batches = 0
    failed_batches = 0

    for batch in checkpoint["batches"]:
        if batch["status"] == "FAILED":
            failed_batches += 1
        if batch["status"] != "COMMITTED":
            continue
        committed_batches += 1
        package_dir = output_dir / "batches" / batch["batch_id"] / "package"
        verified, root = _verify_committed_package(package_dir, verify_package)
        if not verified or root != batch.get("package_root_sha256"):
            package_hash_failures.append(batch["batch_id"])
            continue
        committed_ids.extend(str(value) for value in batch["condition_ids"])

    expected_unique = set(expected_ids)
    committed_unique = set(committed_ids)
    missing_ids = sorted(expected_unique - committed_unique)
    unexpected_ids = sorted(committed_unique - expected_unique)
    passed = not any(
        (duplicate_ids, missing_ids, unexpected_ids, package_hash_failures, failed_batches)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": "PASS" if passed else "FAIL",
        "population_conditions": len(expected_ids),
        "committed_conditions": len(committed_ids),
        "committed_batches": committed_batches,
        "failed_batches": failed_batches,
        "duplicate_condition_ids": duplicate_ids,
        "missing_condition_ids": missing_ids,
        "unexpected_condition_ids": unexpected_ids,
        "package_hash_failures": package_hash_failures,
    }


def _archive_components(
    *,
    rpc_client: Any | None,
    archive_get_json: Callable[[str], object] | None,
    rpc_log_chunk_size: int,
) -> tuple[
    Callable[..., dict[str, Any]],
    Callable[[Path], dict[str, Any]],
    str,
]:
    from tools.official_resolution_acquire_pilot import (
        _default_get_json,
        build_pilot_package,
        verify_pilot_package,
    )
    from tools.official_resolution_rpc_client import ArchiveRpcClient

    client = rpc_client or ArchiveRpcClient.from_env(log_chunk_size=rpc_log_chunk_size)
    get_json = archive_get_json or _default_get_json

    def acquire(*, selected: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
        normalized = []
        for item in selected:
            value = dict(item)
            if "epoch_start_ts" not in value and "normalized_epoch_start_ts" in value:
                value["epoch_start_ts"] = value["normalized_epoch_start_ts"]
            normalized.append(value)
        return build_pilot_package(
            selected=normalized,
            output_dir=output_dir,
            get_json=get_json,
            rpc_call=client.call,
            rpc_endpoint_fingerprint=client.rpc_endpoint_fingerprint,
            max_log_block_range=client.log_chunk_size,
            enforce_pilot_size=False,
        )

    return acquire, verify_pilot_package, str(client.rpc_endpoint_fingerprint)


def _acquire_output_lock(output_dir: Path) -> Path:
    lock_path = output_dir / LOCK_NAME
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise IntegrityFailure("output directory is already in use") from None
    try:
        os.write(descriptor, b"offline full-history runner lock\n")
    finally:
        os.close(descriptor)
    return lock_path


def _run_full_history_locked(
    *,
    population_manifest: str | Path,
    output_dir: str | Path,
    batch_size: int = 10,
    max_batches: int | None = None,
    resume: bool = False,
    dry_run: bool = False,
    runner_mode: str = "mock",
    acquire_package: Callable[..., dict[str, Any]] | None = None,
    verify_package: Callable[[Path], dict[str, Any]] | None = None,
    rpc_client: Any | None = None,
    archive_get_json: Callable[[str], object] | None = None,
    rpc_log_chunk_size: int = 10_000,
    max_attempts: int = 4,
    sleep_fn: Callable[[float], None] = time.sleep,
    now_fn: Callable[[], str] = utc_now,
) -> dict[str, Any]:
    if runner_mode not in {"mock", "archive"}:
        raise ValueError("runner_mode must be mock or archive")
    if max_attempts <= 0:
        raise ValueError("max_attempts must be positive")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_population_manifest(population_manifest)
    batches = deterministic_batches(manifest["conditions"], batch_size=batch_size)
    checkpoint_path = output_dir / CHECKPOINT_NAME
    rpc_endpoint_fingerprint = None
    if runner_mode == "archive" and (acquire_package is None or verify_package is None):
        archive_acquire, archive_verify, rpc_endpoint_fingerprint = _archive_components(
            rpc_client=rpc_client,
            archive_get_json=archive_get_json,
            rpc_log_chunk_size=rpc_log_chunk_size,
        )
        acquire = acquire_package or archive_acquire
        verifier = verify_package or archive_verify
    else:
        acquire = acquire_package or _mock_acquire_package
        verifier = verify_package or _mock_verify_package
        if runner_mode == "archive" and rpc_client is not None:
            rpc_endpoint_fingerprint = str(rpc_client.rpc_endpoint_fingerprint)

    if resume:
        if not checkpoint_path.exists():
            raise IntegrityFailure("resume checkpoint missing")
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if checkpoint.get("population_manifest_sha256") != manifest["sha256"]:
            raise IntegrityFailure("population manifest hash mismatch")
    else:
        if checkpoint_path.exists():
            raise IntegrityFailure("output directory already contains a run")
        checkpoint = _new_checkpoint(
            manifest,
            batches,
            batch_size,
            now_fn=now_fn,
            rpc_endpoint_fingerprint=rpc_endpoint_fingerprint,
        )
        _write_checkpoint(output_dir, checkpoint, now_fn=now_fn)

    if dry_run:
        aggregate = aggregate_verify(
            conditions=manifest["conditions"],
            checkpoint=checkpoint,
            output_dir=output_dir,
            verify_package=verifier,
        )
        atomic_write_json(output_dir / AGGREGATE_NAME, aggregate)
        return {"status": aggregate["status"], "checkpoint": checkpoint, "aggregate": aggregate}

    executable = checkpoint["batches"]
    if max_batches is not None:
        executable = executable[: max(0, max_batches)]

    for batch in executable:
        batch_root = output_dir / "batches" / batch["batch_id"]
        package_dir = batch_root / "package"

        if resume and batch["status"] == "COMMITTED":
            verified, root = _verify_committed_package(package_dir, verifier)
            if verified and root == batch.get("package_root_sha256"):
                continue
            _mark_failed(batch, "RESUME_VERIFICATION_FAILED", now_fn=now_fn)
            _write_checkpoint(output_dir, checkpoint, now_fn=now_fn)
            continue
        if batch["status"] == "FAILED":
            continue

        selected = next(item["conditions"] for item in batches if item["batch_id"] == batch["batch_id"])
        for attempt in range(batch["attempt_count"] + 1, max_attempts + 1):
            batch["attempt_count"] = attempt
            _transition(batch, "PENDING")
            _write_checkpoint(output_dir, checkpoint, now_fn=now_fn)
            attempt_dir = batch_root / "staging" / f"attempt-{attempt:04d}"
            try:
                acquired = acquire(selected=selected, output_dir=attempt_dir)
                _transition(batch, "ACQUIRED")
                _write_checkpoint(output_dir, checkpoint, now_fn=now_fn)
                verification = verifier(attempt_dir)
                if verification.get("status") != "PASS":
                    raise IntegrityFailure("package replay verification failed")
                root = acquired.get("package_root_sha256")
                if not root or verification.get("package_root_sha256") != root:
                    raise IntegrityFailure("package root hash mismatch")
                _transition(batch, "VERIFIED")
                batch["verification_status"] = "PASS"
                _write_checkpoint(output_dir, checkpoint, now_fn=now_fn)
                package_dir.parent.mkdir(parents=True, exist_ok=True)
                if package_dir.exists():
                    raise IntegrityFailure("committed package overwrite is forbidden")
                os.replace(attempt_dir, package_dir)
                verified, committed_root = _verify_committed_package(package_dir, verifier)
                if not verified or committed_root != root:
                    raise IntegrityFailure("committed package verification failed")
                _transition(batch, "COMMITTED")
                batch["package_path"] = package_dir.relative_to(output_dir).as_posix()
                batch["package_root_sha256"] = root
                batch["last_success_at"] = now_fn()
                batch["failure_class"] = None
                _write_checkpoint(output_dir, checkpoint, now_fn=now_fn)
                break
            except KeyboardInterrupt:
                _write_checkpoint(output_dir, checkpoint, now_fn=now_fn)
                raise
            except IntegrityFailure:
                _mark_failed(batch, "INTEGRITY_FAILURE", now_fn=now_fn)
                _write_checkpoint(output_dir, checkpoint, now_fn=now_fn)
                break
            except (TransientAcquisitionError, TimeoutError, ConnectionError):
                if attempt >= max_attempts:
                    _mark_failed(batch, "TRANSIENT_RETRY_EXHAUSTED", now_fn=now_fn)
                    _write_checkpoint(output_dir, checkpoint, now_fn=now_fn)
                    break
                delay_index = min(attempt - 1, len(TRANSIENT_DELAYS_SECONDS) - 1)
                sleep_fn(TRANSIENT_DELAYS_SECONDS[delay_index])
            except Exception:
                _mark_failed(batch, "UNEXPECTED_FAILURE", now_fn=now_fn)
                _write_checkpoint(output_dir, checkpoint, now_fn=now_fn)
                break

    aggregate = aggregate_verify(
        conditions=manifest["conditions"],
        checkpoint=checkpoint,
        output_dir=output_dir,
        verify_package=verifier,
    )
    atomic_write_json(output_dir / AGGREGATE_NAME, aggregate)
    return {"status": aggregate["status"], "checkpoint": checkpoint, "aggregate": aggregate}


def run_full_history(
    *,
    population_manifest: str | Path,
    output_dir: str | Path,
    batch_size: int = 10,
    max_batches: int | None = None,
    resume: bool = False,
    dry_run: bool = False,
    runner_mode: str = "mock",
    acquire_package: Callable[..., dict[str, Any]] | None = None,
    verify_package: Callable[[Path], dict[str, Any]] | None = None,
    rpc_client: Any | None = None,
    archive_get_json: Callable[[str], object] | None = None,
    rpc_log_chunk_size: int = 10_000,
    max_attempts: int = 4,
    sleep_fn: Callable[[float], None] = time.sleep,
    now_fn: Callable[[], str] = utc_now,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    lock_path = _acquire_output_lock(output_path)
    try:
        return _run_full_history_locked(
            population_manifest=population_manifest,
            output_dir=output_path,
            batch_size=batch_size,
            max_batches=max_batches,
            resume=resume,
            dry_run=dry_run,
            runner_mode=runner_mode,
            acquire_package=acquire_package,
            verify_package=verify_package,
            rpc_client=rpc_client,
            archive_get_json=archive_get_json,
            rpc_log_chunk_size=rpc_log_chunk_size,
            max_attempts=max_attempts,
            sleep_fn=sleep_fn,
            now_fn=now_fn,
        )
    finally:
        lock_path.unlink(missing_ok=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--max-batches", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--runner-mode", choices=("mock", "archive"), default="mock")
    parser.add_argument("--rpc-log-chunk-size", type=int, default=10_000)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        result = run_full_history(
            population_manifest=args.population_manifest,
            output_dir=args.output_dir,
            batch_size=args.batch_size,
            max_batches=args.max_batches,
            resume=args.resume,
            dry_run=args.dry_run,
            runner_mode=args.runner_mode,
            rpc_log_chunk_size=args.rpc_log_chunk_size,
        )
    except (IntegrityFailure, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"full-history runner failed: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(json.dumps({"status": result["status"], "aggregate": result["aggregate"]}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
