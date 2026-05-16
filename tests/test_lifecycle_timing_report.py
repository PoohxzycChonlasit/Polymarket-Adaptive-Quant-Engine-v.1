from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.lifecycle_timing_report import analyze_lifecycle_timing, main as timing_main


DATE = "2026-05-15"
RUN_ID = "run-timing-test"


def _event(event_type: str, timestamp: str | None, payload: dict, *, run_id: str = RUN_ID) -> dict:
    event = {
        "event_type": event_type,
        "mode": "paper",
        "run_id": run_id,
        "source_module": "test",
        "schema_version": "1.0",
        "payload": payload,
    }
    if timestamp is not None:
        event["timestamp_utc"] = timestamp
    return event


def _append_jsonl(base_dir: Path, category: str, events: list[dict | str]) -> None:
    path = base_dir / category / f"{DATE}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for event in events:
            if isinstance(event, str):
                handle.write(event + "\n")
            else:
                handle.write(json.dumps(event) + "\n")


def test_lifecycle_timing_orders_events_and_extracts_core_milestones(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    _append_jsonl(
        base_dir,
        "decision_log",
        [
            _event(
                "decision",
                f"{DATE}T00:00:30Z",
                {
                    "candidate_id": "BTC-epoch-1",
                    "ticker": "BTC",
                    "decision_type": "approved",
                    "candidate_seen_ts": f"{DATE}T00:00:05Z",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "seconds_remaining": 270,
                    "ev": 0.012,
                    "true_probability": 0.57,
                },
            ),
            _event(
                "decision",
                f"{DATE}T00:01:20Z",
                {
                    "candidate_id": "BTC-epoch-1",
                    "ticker": "BTC",
                    "decision_type": "skipped",
                    "skip_reason": "time_unsafe",
                    "lifecycle_phase": "FINAL_DERISK",
                    "seconds_remaining": 35,
                },
            ),
        ],
    )
    _append_jsonl(
        base_dir,
        "execution_log",
        [
            _event(
                "execution",
                f"{DATE}T00:00:45Z",
                {"candidate_id": "BTC-epoch-1", "event": "order_submit_attempt"},
            )
        ],
    )

    report = analyze_lifecycle_timing(base_dir=base_dir, date=DATE, run_id=RUN_ID)

    coverage = report["candidate_timing_coverage"]
    assert coverage["first_seen"] == 1
    assert coverage["first_executable"] == 1
    assert coverage["first_ev_visible"] == 1
    assert coverage["first_probability_visible"] == 1
    assert coverage["first_trade_attempt"] == 1
    assert coverage["cutoff_ts"] == 1
    assert report["timing_metrics"]["executable_age_before_skip_seconds"]["p50"] == pytest.approx(50.0)
    assert report["timing_metrics"]["time_to_FINAL_DERISK_seconds"]["p50"] == pytest.approx(75.0)
    assert report["interpretation"]["cutoff_starvation_confirmed"] is True


def test_cooldown_distribution_and_collision_rate(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    _append_jsonl(
        base_dir,
        "decision_log",
        [
            _event(
                "decision",
                f"{DATE}T00:00:10Z",
                {
                    "candidate_id": "ETH-epoch-1",
                    "decision_type": "skipped",
                    "skip_reason": "frequency_cooldown",
                    "seconds_remaining": 130,
                },
            ),
            _event(
                "decision",
                f"{DATE}T00:00:40Z",
                {
                    "candidate_id": "ETH-epoch-1",
                    "decision_type": "skipped",
                    "skip_reason": "frequency_cooldown",
                    "seconds_remaining": 80,
                },
            ),
            _event(
                "decision",
                f"{DATE}T00:01:10Z",
                {
                    "candidate_id": "ETH-epoch-1",
                    "decision_type": "skipped",
                    "skip_reason": "time_unsafe",
                    "seconds_remaining": 50,
                },
            ),
        ],
    )

    report = analyze_lifecycle_timing(base_dir=base_dir, date=DATE, run_id=RUN_ID)

    metrics = report["timing_metrics"]
    assert metrics["cooldown_skip_count"] == 2
    assert metrics["cooldown_cutoff_collision_count"] == 1
    assert metrics["cooldown_collision_rate"] == pytest.approx(0.5)
    assert metrics["revisit_delay_distribution_seconds"]["count"] == 2
    assert metrics["revisit_delay_distribution_seconds"]["p50"] == pytest.approx(30.0)
    assert report["interpretation"]["revisit_cadence_pressure"] is True


def test_missing_timestamp_fails_soft(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    _append_jsonl(
        base_dir,
        "decision_log",
        [
            _event("decision", None, {"candidate_id": "missing-ts", "decision_type": "skipped"}),
            _event(
                "decision",
                f"{DATE}T00:00:10Z",
                {
                    "candidate_id": "valid-ts",
                    "decision_type": "skipped",
                    "skip_reason": "time_unsafe",
                    "seconds_remaining": 20,
                },
            ),
        ],
    )

    report = analyze_lifecycle_timing(base_dir=base_dir, date=DATE, run_id=RUN_ID)

    assert report["missing_timestamp_events"] == 1
    assert report["events_loaded"] == 2
    assert report["candidate_count"] == 1
    assert report["bad_json_lines"] == 0


def test_write_report_cli_creates_json_and_markdown(tmp_path: Path) -> None:
    base_dir = tmp_path / "runtime" / "quant_data"
    report_dir = tmp_path / "runtime" / "reports"
    _append_jsonl(
        base_dir,
        "decision_log",
        [
            _event(
                "decision",
                f"{DATE}T00:00:10Z",
                {
                    "candidate_id": "BTC-epoch-2",
                    "decision_type": "skipped",
                    "skip_reason": "time_unsafe",
                    "seconds_remaining": 12,
                    "lifecycle_phase": "FINAL_DERISK",
                },
            )
        ],
    )

    exit_code = timing_main(
        [
            "--date",
            DATE,
            "--run-id",
            RUN_ID,
            "--base-dir",
            str(base_dir),
            "--report-dir",
            str(report_dir),
            "--write-report",
        ]
    )

    assert exit_code == 0
    json_path = report_dir / f"lifecycle_timing_report_{DATE}_run_{RUN_ID}.json"
    markdown_path = report_dir / f"lifecycle_timing_report_{DATE}_run_{RUN_ID}.md"
    assert json_path.exists()
    assert markdown_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["interpretation"]["cutoff_starvation_confirmed"] is True
    assert "Cutoff Pressure Histogram" in markdown_path.read_text(encoding="utf-8")
