from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.outcome_truth.official_resolution_rpc_client import ARCHIVE_RPC_ENV_VAR, ArchiveRpcError
from tools.replay.official_resolution_full_history_runner import (
    IntegrityFailure,
    TransientAcquisitionError,
    _build_parser,
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
    path.parent.mkdir(parents=True, exist_ok=True)
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


def test_failed_batch_can_recover_on_resume_with_audit_history(tmp_path: Path) -> None:
    population = _write_population(tmp_path / "population.json", 2)

    def fail(*, selected: list[dict], output_dir: Path) -> dict:
        raise TransientAcquisitionError("temporary")

    first = run_full_history(
        population_manifest=population,
        output_dir=tmp_path / "run",
        runner_mode="mock",
        acquire_package=fail,
        verify_package=_fake_verifier,
        max_attempts=1,
        sleep_fn=lambda _seconds: None,
        now_fn=lambda: "2026-06-14T00:00:00Z",
    )
    recovered = run_full_history(
        population_manifest=population,
        output_dir=tmp_path / "run",
        runner_mode="mock",
        resume=True,
        acquire_package=_fake_acquirer(),
        verify_package=_fake_verifier,
        max_attempts=1,
        sleep_fn=lambda _seconds: None,
        now_fn=lambda: "2026-06-14T00:01:00Z",
    )
    batch = recovered["checkpoint"]["batches"][0]

    assert first["status"] == "FAIL"
    assert recovered["status"] == "PASS"
    assert batch["status"] == "COMMITTED"
    assert batch["attempt_count"] == 2
    assert batch["state_history"] == [
        "PENDING",
        "FAILED",
        "RETRYABLE",
        "PENDING",
        "ACQUIRED",
        "VERIFIED",
        "COMMITTED",
    ]
    assert batch["failure_history"] == [
        {
            "attempt_count": 1,
            "failed_at": "2026-06-14T00:00:00Z",
            "failure_class": "TRANSIENT_RETRY_EXHAUSTED",
        }
    ]


def test_repeated_failed_resume_tracks_each_failure(tmp_path: Path) -> None:
    population = _write_population(tmp_path / "population.json", 1)

    def fail(*, selected: list[dict], output_dir: Path) -> dict:
        raise TransientAcquisitionError("temporary")

    for resume, timestamp in (
        (False, "2026-06-14T00:00:00Z"),
        (True, "2026-06-14T00:01:00Z"),
    ):
        result = run_full_history(
            population_manifest=population,
            output_dir=tmp_path / "run",
            runner_mode="mock",
            resume=resume,
            acquire_package=fail,
            verify_package=_fake_verifier,
            max_attempts=1,
            sleep_fn=lambda _seconds: None,
            now_fn=lambda timestamp=timestamp: timestamp,
        )

    batch = result["checkpoint"]["batches"][0]
    assert batch["status"] == "FAILED"
    assert batch["attempt_count"] == 2
    assert [entry["failure_class"] for entry in batch["failure_history"]] == [
        "TRANSIENT_RETRY_EXHAUSTED",
        "TRANSIENT_RETRY_EXHAUSTED",
    ]
    assert batch["state_history"] == ["PENDING", "FAILED", "RETRYABLE", "PENDING", "FAILED"]


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
    import tools.replay.official_resolution_full_history_runner as target_module
    source = Path(target_module.__file__).read_text(encoding="utf-8")

    forbidden = ("polymarket.", "utils.risk_manager", "main.py", "config.settings")
    assert all(item not in source for item in forbidden)


def test_archive_mode_commits_batch_and_records_fingerprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    population = _write_population(tmp_path / "population.json", 2)
    calls: list[list[dict]] = []
    client = SimpleNamespace(
        call=lambda _method, _params: {},
        log_chunk_size=321,
        rpc_endpoint_fingerprint="sha256:archive",
        endpoint="https://user:secret@example.invalid/archive",
    )

    def build_pilot_package(**kwargs):
        calls.append(kwargs["selected"])
        assert kwargs["enforce_pilot_size"] is False
        return _fake_acquirer()(selected=kwargs["selected"], output_dir=kwargs["output_dir"])

    monkeypatch.setattr(
        "tools.outcome_truth.official_resolution_acquire_pilot.build_pilot_package", build_pilot_package
    )
    monkeypatch.setattr(
        "tools.outcome_truth.official_resolution_acquire_pilot.verify_pilot_package", _fake_verifier
    )

    result = run_full_history(
        population_manifest=population,
        output_dir=tmp_path / "run",
        runner_mode="archive",
        rpc_client=client,
        archive_get_json=lambda _url: {},
        sleep_fn=lambda _seconds: None,
    )
    checkpoint_text = (tmp_path / "run" / "checkpoint.json").read_text(encoding="utf-8")

    assert result["status"] == "PASS"
    assert len(calls) == 1
    assert result["checkpoint"]["rpc_endpoint_fingerprint"] == "sha256:archive"
    assert "archive-key" not in checkpoint_text
    all_outputs = "".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (tmp_path / "run").rglob("*")
        if path.is_file()
    )
    assert client.endpoint not in all_outputs
    assert "user:secret" not in all_outputs


def test_archive_resume_skips_verified_committed_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    population = _write_population(tmp_path / "population.json", 2)
    calls = 0
    client = SimpleNamespace(
        call=lambda _method, _params: {},
        log_chunk_size=10_000,
        rpc_endpoint_fingerprint="sha256:archive",
    )

    def build_pilot_package(**kwargs):
        nonlocal calls
        calls += 1
        return _fake_acquirer()(selected=kwargs["selected"], output_dir=kwargs["output_dir"])

    monkeypatch.setattr(
        "tools.outcome_truth.official_resolution_acquire_pilot.build_pilot_package", build_pilot_package
    )
    monkeypatch.setattr(
        "tools.outcome_truth.official_resolution_acquire_pilot.verify_pilot_package", _fake_verifier
    )
    common = {
        "population_manifest": population,
        "output_dir": tmp_path / "run",
        "runner_mode": "archive",
        "rpc_client": client,
        "archive_get_json": lambda _url: {},
        "sleep_fn": lambda _seconds: None,
    }

    run_full_history(**common)
    result = run_full_history(**common, resume=True)

    assert result["status"] == "PASS"
    assert calls == 1


def test_archive_mode_without_credential_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ARCHIVE_RPC_ENV_VAR, raising=False)
    population = _write_population(tmp_path / "population.json", 1)

    with pytest.raises(ArchiveRpcError, match=ARCHIVE_RPC_ENV_VAR):
        run_full_history(
            population_manifest=population,
            output_dir=tmp_path / "run",
            runner_mode="archive",
        )

    assert not (tmp_path / "run" / ".full_history_runner.lock").exists()


def test_duplicate_output_directory_is_rejected(tmp_path: Path) -> None:
    _run(tmp_path, 1)

    with pytest.raises(IntegrityFailure, match="output directory already contains a run"):
        _run(tmp_path, 1)


def test_active_output_directory_lock_is_rejected(tmp_path: Path) -> None:
    population = _write_population(tmp_path / "population.json", 1)
    output = tmp_path / "run"
    output.mkdir()
    (output / ".full_history_runner.lock").write_text("locked\n", encoding="utf-8")

    with pytest.raises(IntegrityFailure, match="output directory is already in use"):
        run_full_history(
            population_manifest=population,
            output_dir=output,
            runner_mode="mock",
        )


def test_committed_package_overwrite_is_rejected(tmp_path: Path) -> None:
    population = _write_population(tmp_path / "population.json", 1)
    output = tmp_path / "run"
    batches = deterministic_batches(_conditions(1))
    package = output / "batches" / batches[0]["batch_id"] / "package"
    package.mkdir(parents=True)
    (package / "COMMITTED").write_text("existing\n", encoding="utf-8")

    result = run_full_history(
        population_manifest=population,
        output_dir=output,
        runner_mode="mock",
        acquire_package=_fake_acquirer(),
        verify_package=_fake_verifier,
        sleep_fn=lambda _seconds: None,
    )

    assert result["status"] == "FAIL"
    assert result["checkpoint"]["batches"][0]["failure_class"] == "INTEGRITY_FAILURE"
    assert (package / "COMMITTED").read_text(encoding="utf-8") == "existing\n"


def test_mock_mode_remains_default_and_unchanged(tmp_path: Path) -> None:
    result = _run(tmp_path, 3)

    assert result["status"] == "PASS"
    assert "rpc_endpoint_fingerprint" not in result["checkpoint"]


def test_archive_cli_accepts_provider_log_chunk_override() -> None:
    args = _build_parser().parse_args(
        [
            "--population-manifest",
            "population.json",
            "--output-dir",
            "output",
            "--runner-mode",
            "archive",
            "--rpc-log-chunk-size",
            "25",
        ]
    )

    assert args.runner_mode == "archive"
    assert args.rpc_log_chunk_size == 25


def test_checkpoint_output_is_deterministic_with_fixed_clock(tmp_path: Path) -> None:
    fixed_clock = lambda: "2026-06-14T00:00:00Z"
    population_a = _write_population(tmp_path / "a" / "population.json", 2)
    population_b = _write_population(tmp_path / "b" / "population.json", 2)

    for population, output in (
        (population_a, tmp_path / "a" / "run"),
        (population_b, tmp_path / "b" / "run"),
    ):
        run_full_history(
            population_manifest=population,
            output_dir=output,
            runner_mode="mock",
            acquire_package=_fake_acquirer(),
            verify_package=_fake_verifier,
            sleep_fn=lambda _seconds: None,
            now_fn=fixed_clock,
        )

    first = json.loads((tmp_path / "a" / "run" / "checkpoint.json").read_text(encoding="utf-8"))
    second = json.loads((tmp_path / "b" / "run" / "checkpoint.json").read_text(encoding="utf-8"))
    first.pop("population_manifest_path")
    second.pop("population_manifest_path")

    assert first == second
