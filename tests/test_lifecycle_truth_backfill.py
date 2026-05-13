import json
from pathlib import Path

from tools.lifecycle_truth_backfill import build_lifecycle_truth_backfill, main, write_lifecycle_truth_backfill_manifest


DATE = "2026-05-08"
NEXT_DATE = "2026-05-09"


def _write_jsonl(base_dir: Path, category: str, date: str, events: list[dict]) -> None:
    path = base_dir / category / f"{date}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n",
        encoding="utf-8",
    )


def _event(timestamp: str, *, run_id: str = "", mode: str = "paper", payload: dict | None = None) -> dict:
    event = {
        "timestamp_utc": timestamp,
        "event_type": "candidate_decision",
        "mode": mode,
        "source_module": "synthetic_test",
        "schema_version": "1.0",
        "payload": payload or {},
    }
    if run_id:
        event["run_id"] = run_id
    return event


def _write_synthetic_history(base_dir: Path) -> None:
    _write_jsonl(
        base_dir,
        "decision_log",
        DATE,
        [
            _event(
                f"{DATE}T01:00:01Z",
                run_id="run-compatible",
                payload={
                    "decision": "skip",
                    "normalized_skip_reason": "time_unsafe",
                    "candidate_id": "candidate-compatible",
                    "signal_id": "signal-compatible",
                    "lifecycle_phase": "OPENING_SCAN",
                    "fair_value": 0.61,
                    "market_price": 0.58,
                    "true_probability": 0.61,
                    "ev_after_spread": 0.02,
                    "starter_candidate": True,
                    "ev_calculation_stage": "risk_blocked_after_ev",
                },
            ),
            _event(
                f"{DATE}T01:00:02Z",
                payload={
                    "decision": "skip",
                    "normalized_skip_reason": "missing_run_id_legacy",
                    "candidate_id": "candidate-missing-run",
                },
            ),
            _event(
                f"{DATE}T01:00:03Z",
                run_id="run-live",
                mode="live",
                payload={"candidate_id": "candidate-live", "decision": "skip"},
            ),
        ],
    )
    _write_jsonl(
        base_dir,
        "system_health",
        NEXT_DATE,
        [
            _event(
                f"{NEXT_DATE}T01:00:01Z",
                run_id="run-partial",
                payload={"heartbeat": "ok", "scanner_state": "legacy_no_candidate_fields"},
            )
        ],
    )


def test_build_lifecycle_truth_backfill_labels_compatibility_and_reruns_cross_run(tmp_path: Path) -> None:
    base_dir = tmp_path / "quant_data"
    report_dir = tmp_path / "reports"
    memory_index_dir = tmp_path / "memory" / "index"
    _write_synthetic_history(base_dir)

    manifest = build_lifecycle_truth_backfill(
        base_dir=base_dir,
        report_dir=report_dir,
        memory_index_dir=memory_index_dir,
        date_from=DATE,
        date_to=NEXT_DATE,
    )

    assert manifest["scope"] == "offline_research_replay_only"
    assert manifest["does_not_claim_profitability"] is True
    assert manifest["does_not_authorize_runtime_decisions"] is True
    assert manifest["does_not_implement_inventory_execution"] is True
    assert manifest["historical_run_counts"]["dates"] == 2
    assert manifest["historical_run_counts"]["run_ids_discovered"] == 4
    assert manifest["historical_run_counts"]["truth_tables_generated"] == 2
    assert manifest["compatibility_counts"]["compatible"] == 1
    assert manifest["compatibility_counts"]["partial_legacy"] == 1
    assert manifest["compatibility_counts"]["incompatible_legacy"] == 2

    entries = {entry["run_id"]: entry for entry in manifest["runs"]}
    assert entries["run-compatible"]["compatibility_level"] == "compatible"
    assert entries["run-compatible"]["truth_table_path"].endswith("lifecycle_truth_tables_2026-05-08_run_run-compatible.json")
    assert entries["run-compatible"]["candidate_events"] == 1
    assert entries["run-compatible"]["direct_field_rate"] > 0
    assert entries["run-compatible"]["replay_truth_confidence"]
    assert entries["run-partial"]["compatibility_level"] == "partial_legacy"
    assert entries["run-partial"]["truth_table_path"].endswith("lifecycle_truth_tables_2026-05-09_run_run-partial.json")
    assert entries["run-partial"]["candidate_events"] == 0
    assert entries["missing_run_id"]["compatibility_level"] == "incompatible_legacy"
    assert entries["missing_run_id"]["truth_table_path"] == ""
    assert entries["run-live"]["compatibility_level"] == "incompatible_legacy"
    assert "live_mode_evidence_skipped" in entries["run-live"]["compatibility_reasons"]

    cross = manifest["cross_run_lifecycle_truth"]
    assert cross["path"].endswith(f"cross_run_lifecycle_truth_{DATE}_to_{NEXT_DATE}.json")
    assert cross["runs_analyzed"] == 2
    assert cross["candidate_events"] == 1
    assert cross["repeated_failure_confidence"]
    assert (report_dir / f"cross_run_lifecycle_truth_{DATE}_to_{NEXT_DATE}.json").exists()


def test_write_lifecycle_truth_backfill_manifest(tmp_path: Path) -> None:
    manifest = {"runs": [], "compatibility_counts": {}}

    path = write_lifecycle_truth_backfill_manifest(manifest, report_dir=tmp_path / "reports")

    assert path.name == "lifecycle_truth_backfill_manifest.json"
    assert json.loads(path.read_text(encoding="utf-8"))["runs"] == []


def test_lifecycle_truth_backfill_cli_writes_manifest_and_cross_run(tmp_path: Path, capsys) -> None:
    base_dir = tmp_path / "quant_data"
    report_dir = tmp_path / "reports"
    memory_index_dir = tmp_path / "memory" / "index"
    _write_synthetic_history(base_dir)

    assert main([
        "--from",
        DATE,
        "--to",
        NEXT_DATE,
        "--base-dir",
        str(base_dir),
        "--report-dir",
        str(report_dir),
        "--memory-index-dir",
        str(memory_index_dir),
    ]) == 0

    output = capsys.readouterr().out
    assert "Lifecycle Truth Backfill" in output
    assert "compatible=1" in output
    assert "partial_legacy=1" in output
    assert "incompatible_legacy=2" in output
    assert (report_dir / "lifecycle_truth_backfill_manifest.json").exists()
    assert (report_dir / f"cross_run_lifecycle_truth_{DATE}_to_{NEXT_DATE}.json").exists()
