from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.replay.official_resolution_full_history_runner import run_full_history
from tools.outcome_truth.official_resolution_outcome_join import join_official_outcomes
from tools.outcome_truth.outcome_truth_graduation import graduate_outcome_truth
from tools.outcome_truth.outcome_truth_population_manifest import generate_population_manifest


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_manifest_acquisition_join_and_graduation_reaches_ready(tmp_path: Path) -> None:
    decision_dir = tmp_path / "decision_log"
    decision_dir.mkdir()
    rows = []
    for index in range(10):
        condition_id = "0x" + f"{index + 1:064x}"
        rows.append(
            {
                "timestamp_utc": f"2026-06-01T00:00:{index:02d}Z",
                "payload": {
                    "condition_id": condition_id,
                    "epoch_start_ts": index + 1,
                    "asset": "ETH",
                    "market_slug": f"eth-updown-5m-{index + 1}",
                    "model_output_ready": True,
                    "model_probability_yes": 0.55,
                    "decision_timestamp": f"2026-06-01T00:00:{index:02d}Z",
                },
            }
        )
    (decision_dir / "2026-06-01.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    quarantine = _write_json(
        tmp_path / "quarantine.json",
        {
            "rows": [],
            "known_lost_events": 0,
            "unknown_events": 0,
            "maximum_possible_denominator_error": 0,
        },
    )
    manifest_dir = tmp_path / "manifest"
    generate_population_manifest(
        source_dir=decision_dir,
        quarantine_inventory=quarantine,
        output_dir=manifest_dir,
    )
    population_manifest = manifest_dir / "population_manifest.json"

    def acquire(*, selected: list[dict], output_dir: Path) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        canonical = output_dir / "canonical" / "outcome_rows.jsonl"
        canonical.parent.mkdir()
        outcomes = [
            {
                "condition_id": item["condition_id"],
                "normalized_epoch_start_ts": item["normalized_epoch_start_ts"],
                "outcome_status": "OFFICIAL_RESOLVED",
                "terminal_outcome": "Up",
                "resolution_block_number": 100,
                "resolution_block_hash": "0xblock",
                "resolution_transaction_hash": "0xtx",
                "resolution_log_index": 1,
                "state_source_block_number": 100,
                "state_source_block_hash": "0xblock",
            }
            for item in selected
        ]
        canonical.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in outcomes),
            encoding="utf-8",
        )
        root = hashlib.sha256(canonical.read_bytes()).hexdigest()
        manifest = {"selected_conditions": selected, "package_root_sha256": root}
        _write_json(output_dir / "manifest.json", manifest)
        (output_dir / "COMMITTED").write_text(root + "\n", encoding="utf-8")
        return manifest

    def verify(output_dir: Path) -> dict:
        manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        return {"status": "PASS", "package_root_sha256": manifest["package_root_sha256"]}

    acquisition_dir = tmp_path / "acquisition"
    acquisition = run_full_history(
        population_manifest=population_manifest,
        output_dir=acquisition_dir,
        runner_mode="mock",
        acquire_package=acquire,
        verify_package=verify,
        sleep_fn=lambda _seconds: None,
    )
    assert acquisition["status"] == "PASS"

    join_dir = tmp_path / "join"
    join_report = join_official_outcomes(
        population_manifest=population_manifest,
        outcome_rows=acquisition_dir / "batches",
        aggregate_verification=acquisition_dir / "aggregate_verification.json",
        output_dir=join_dir,
    )
    assert join_report["status"] == "PASS"

    spec = tmp_path / "spec.md"
    spec.write_text(
        "\n".join(
            [
                "Status: FROZEN CANDIDATE SPECIFICATION",
                "probability_buckets: [0.00,0.10),[0.10,0.20),[0.20,0.30),[0.30,0.40),[0.40,0.50),[0.50,0.60),[0.60,0.70),[0.70,0.80),[0.80,0.90),[0.90,1.00]",
                "fingerprint_hash: " + "a" * 64,
            ]
        ),
        encoding="utf-8",
    )
    graduation = graduate_outcome_truth(
        joined_outcomes=join_dir / "joined_official_outcomes.jsonl",
        outcome_join_report=join_dir / "outcome_join_report.json",
        calibration_spec=spec,
        loss_bound_evidence=quarantine,
        output_dir=tmp_path / "graduation",
    )

    assert graduation["verdict"] == "OUTCOME_TRUTH_READY"
