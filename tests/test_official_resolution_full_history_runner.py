from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.official_resolution_full_history_runner import (
    IntegrityFailure,
    TransientAcquisitionError,
    aggregate_verify,
    deterministic_batches,
    load_population_manifest,
    run_full_history,
)


def _conditions(count: int) -> list[dict]:
    return [
        {
            "condition_id": "0x" + f"{index:064x}",
            "epoch_start_ts": index,
            "asset": "ETH",
        }
        for index in range(1, count + 1)
    ]


def _write_population(path: Path, count: int, *, extra: dict | None = None) -> Path:
    payload = {"schema_version": "population_v1", "conditions": _conditions(count)}
    if extra:
        payload.update(extra)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _fake_acquirer(calls: list[str] | None = None):
    def acquire(*, selected: list[dict], output_dir: Path) -> dict:
        if calls is not None:
            calls.append(selected[0]["condition_id"])
        output_dir.mkdir(parents=True, exist_ok=True)
        root = "root-" + selected[0]["condition_id"][-8:]
        manifest = {
            "selected_conditions": selected,
            "package_root_sha256": root,
        }
        (output_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (output_dir / "COMMITTED").write_text(root + "\n", encoding="utf-8")
        return manifest

    return acquire


def _fake_verifier(output_dir: Path) -> dict:
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    committed = (output_dir / "COMMITTED").read_text(encoding="utf-8").strip()
    root = manifest["package_root_sha256"]
    return {
        "status": "PASS" if committed == root else "FAIL",
        "package_root_sha256": root,
        "canonical_rows": len(manifest["selected_conditions"]),
    }


def _run(
    tmp_path: Path,
    count: int,
    *,
    acquire=None,
    verify=None,
    resume: bool = False,
    batch_size: int = 10,
    max_attempts: int = 4,
    sleep_calls: list[float] | None = None,
    manifest_extra: dict | None = None,
):
    population = _write_population(tmp_path / "population.json", count, extra=manifest_extra)
    return run_full_history(
        population_manifest=population,
        output_dir=tmp_path / "run",
        batch_size=batch_size,
        resume=resume,
        runner_mode="mock",
        acquire_package=acquire or _fake_acquirer(),
        verify_package=verify or _fake_verifier,
        max_attempts=max_attempts,
        sleep_fn=(sleep_calls.append if sleep_calls is not None else lambda _seconds: None),
    )


def test_deterministic_batching() -> None:
    conditions = _conditions(21)

    first = deterministic_batches(conditions, batch_size=10)
    second = deterministic_batches(conditions, batch_size=10)

    assert first == second
    assert [batch["batch_id"] for batch in first] == [
        batch["batch_id"] for batch in second
    ]
    assert [len(batch["conditions"]) for batch in first] == [10, 10, 1]


def test_final_batch_size_handling(tmp_path: Path) -> None:
    result = _run(tmp_path, 26)

    assert [batch["condition_count"] for batch in result["checkpoint"]["batches"]] == [
        10,
        10,
        6,
    ]


def test_checkpoint_creation_and_state_machine(tmp_path: Path) -> None:
    result = _run(tmp_path, 10)

    checkpoint_path = tmp_path / "run" / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    batch = checkpoint["batches"][0]
    assert result["status"] == "PASS"
    assert batch["status"] == "COMMITTED"
    assert batch["state_history"] == ["PENDING", "ACQUIRED", "VERIFIED", "COMMITTED"]


def test_resume_skips_verified_committed_batches(tmp_path: Path) -> None:
    calls: list[str] = []
    population = _write_population(tmp_path / "population.json", 20)
    first = run_full_history(
        population_manifest=population,
        output_dir=tmp_path / "run",
        runner_mode="mock",
        acquire_package=_fake_acquirer(calls),
        verify_package=_fake_verifier,
        sleep_fn=lambda _seconds: None,
    )
    second = run_full_history(
        population_manifest=population,
        output_dir=tmp_path / "run",
        runner_mode="mock",
        resume=True,
        acquire_package=_fake_acquirer(calls),
        verify_package=_fake_verifier,
        sleep_fn=lambda _seconds: None,
    )

    assert first["status"] == second["status"] == "PASS"
    assert len(calls) == 2


def test_resume_fails_on_manifest_hash_mismatch(tmp_path: Path) -> None:
    population = _write_population(tmp_path / "population.json", 10)
    run_full_history(
        population_manifest=population,
        output_dir=tmp_path / "run",
        runner_mode="mock",
        acquire_package=_fake_acquirer(),
        verify_package=_fake_verifier,
        sleep_fn=lambda _seconds: None,
    )
    _write_population(population, 11)

    with pytest.raises(IntegrityFailure, match="population manifest hash mismatch"):
        run_full_history(
            population_manifest=population,
            output_dir=tmp_path / "run",
            runner_mode="mock",
            resume=True,
            acquire_package=_fake_acquirer(),
            verify_package=_fake_verifier,
            sleep_fn=lambda _seconds: None,
        )


def test_transient_retry_succeeds(tmp_path: Path) -> None:
    attempts = 0
    sleep_calls: list[float] = []

    def acquire(*, selected: list[dict], output_dir: Path) -> dict:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TransientAcquisitionError("temporary")
        return _fake_acquirer()(selected=selected, output_dir=output_dir)

    result = _run(tmp_path, 10, acquire=acquire, sleep_calls=sleep_calls)

    assert result["status"] == "PASS"
    assert attempts == 3
    assert sleep_calls == [5.0, 30.0]


def test_transient_retry_exhaustion_marks_batch_failed(tmp_path: Path) -> None:
    attempts = 0

    def acquire(*, selected: list[dict], output_dir: Path) -> dict:
        nonlocal attempts
        attempts += 1
        raise TransientAcquisitionError("temporary")

    result = _run(tmp_path, 10, acquire=acquire, max_attempts=3)
    batch = result["checkpoint"]["batches"][0]

    assert result["status"] == "FAIL"
    assert attempts == 3
    assert batch["status"] == "FAILED"
    assert batch["failure_class"] == "TRANSIENT_RETRY_EXHAUSTED"


def test_integrity_failure_marks_failed_without_retry(tmp_path: Path) -> None:
    attempts = 0

    def acquire(*, selected: list[dict], output_dir: Path) -> dict:
        nonlocal attempts
        attempts += 1
        raise IntegrityFailure("event/state mismatch")

    result = _run(tmp_path, 10, acquire=acquire)

    assert result["status"] == "FAIL"
    assert attempts == 1
    assert result["checkpoint"]["batches"][0]["failure_class"] == "INTEGRITY_FAILURE"


def test_manual_interruption_simulation_resumes_correctly(tmp_path: Path) -> None:
    population = _write_population(tmp_path / "population.json", 20)
    calls = 0

    def interrupted(*, selected: list[dict], output_dir: Path) -> dict:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        return _fake_acquirer()(selected=selected, output_dir=output_dir)

    with pytest.raises(KeyboardInterrupt):
        run_full_history(
            population_manifest=population,
            output_dir=tmp_path / "run",
            runner_mode="mock",
            acquire_package=interrupted,
            verify_package=_fake_verifier,
            sleep_fn=lambda _seconds: None,
        )

    resumed_calls: list[str] = []
    result = run_full_history(
        population_manifest=population,
        output_dir=tmp_path / "run",
        runner_mode="mock",
        resume=True,
        acquire_package=_fake_acquirer(resumed_calls),
        verify_package=_fake_verifier,
        sleep_fn=lambda _seconds: None,
    )

    assert result["status"] == "PASS"
    assert len(resumed_calls) == 1


def test_duplicate_condition_detection(tmp_path: Path) -> None:
    population = tmp_path / "population.json"
    duplicate = _conditions(1)[0]
    population.write_text(json.dumps({"conditions": [duplicate, duplicate]}), encoding="utf-8")

    result = run_full_history(
        population_manifest=population,
        output_dir=tmp_path / "run",
        runner_mode="mock",
        dry_run=True,
    )

    assert result["aggregate"]["duplicate_condition_ids"] == [duplicate["condition_id"]]
    assert result["aggregate"]["status"] == "FAIL"


def test_missing_condition_detection(tmp_path: Path) -> None:
    result = _run(tmp_path, 20)
    checkpoint = result["checkpoint"]
    checkpoint["batches"][1]["condition_ids"] = checkpoint["batches"][1]["condition_ids"][:-1]

    aggregate = aggregate_verify(
        conditions=load_population_manifest(tmp_path / "population.json")["conditions"],
        checkpoint=checkpoint,
        output_dir=tmp_path / "run",
        verify_package=_fake_verifier,
    )

    assert len(aggregate["missing_condition_ids"]) == 1
    assert aggregate["status"] == "FAIL"


def test_aggregate_verifier_fails_on_failed_batch(tmp_path: Path) -> None:
    def fail(*, selected: list[dict], output_dir: Path) -> dict:
        raise IntegrityFailure("bad")

    result = _run(tmp_path, 10, acquire=fail)

    assert result["aggregate"]["failed_batches"] == 1
    assert result["aggregate"]["status"] == "FAIL"


def test_aggregate_verifier_passes_all_committed_batches(tmp_path: Path) -> None:
    result = _run(tmp_path, 21)

    assert result["aggregate"]["committed_batches"] == 3
    assert result["aggregate"]["committed_conditions"] == 21
    assert result["aggregate"]["status"] == "PASS"


def test_credentials_are_not_written_to_checkpoint(tmp_path: Path) -> None:
    _run(
        tmp_path,
        10,
        manifest_extra={
            "rpc_url": "https://user:secret@example.invalid",
            "api_key": "super-secret",
        },
    )

    checkpoint_text = (tmp_path / "run" / "checkpoint.json").read_text(encoding="utf-8")
    assert "super-secret" not in checkpoint_text
    assert "user:secret" not in checkpoint_text
    assert "rpc_url" not in checkpoint_text
    assert "api_key" not in checkpoint_text


def test_resume_hash_verifies_committed_batches(tmp_path: Path) -> None:
    population = _write_population(tmp_path / "population.json", 10)
    run_full_history(
        population_manifest=population,
        output_dir=tmp_path / "run",
        runner_mode="mock",
        acquire_package=_fake_acquirer(),
        verify_package=_fake_verifier,
        sleep_fn=lambda _seconds: None,
    )
    committed = next((tmp_path / "run" / "batches").glob("*/package/COMMITTED"))
    committed.write_text("tampered\n", encoding="utf-8")

    result = run_full_history(
        population_manifest=population,
        output_dir=tmp_path / "run",
        runner_mode="mock",
        resume=True,
        acquire_package=_fake_acquirer(),
        verify_package=_fake_verifier,
        sleep_fn=lambda _seconds: None,
    )

    assert result["status"] == "FAIL"
    assert result["checkpoint"]["batches"][0]["failure_class"] == "RESUME_VERIFICATION_FAILED"


def test_no_runtime_module_imports() -> None:
    source = Path("tools/official_resolution_full_history_runner.py").read_text(encoding="utf-8")

    forbidden = ("polymarket.", "utils.risk_manager", "main.py", "config.settings")
    assert all(item not in source for item in forbidden)
