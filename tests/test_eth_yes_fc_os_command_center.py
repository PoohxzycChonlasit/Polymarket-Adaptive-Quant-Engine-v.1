from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

import tools.eth_yes_fc_os_command_center as command_center


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "condition_id",
        "epoch_start_ts",
        "candidate_id",
        "asset",
        "side",
        "canonical_entry_lifecycle_phase",
        "hold_seconds",
        "pnl_usdc",
        "outcome_win_loss",
        "trade_result",
        "entry_ts",
        "regime",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "condition_id": "condition-a",
        "epoch_start_ts": 1780000000,
        "candidate_id": "candidate-a",
        "asset": "ETH",
        "side": "YES",
        "canonical_entry_lifecycle_phase": "OPENING_SCAN",
        "hold_seconds": 20,
        "pnl_usdc": 0.01,
        "outcome_win_loss": "WIN",
        "trade_result": "TP",
        "entry_ts": "2026-06-06T05:00:00Z",
        "regime": "TREND_DOWN",
    }
    row.update(overrides)
    return row


def _write_decision_log(path: Path) -> None:
    path.mkdir(parents=True)
    events = [
        {"event_type": "decision", "timestamp_utc": "2026-06-06T00:00:00Z", "payload": {"asset": "ETH", "market_regime": "COMPRESSION", "decision_id": "d1"}},
        {"event_type": "decision", "timestamp_utc": "2026-06-06T00:00:10Z", "payload": {"asset": "ETH", "market_regime": "TREND_DOWN", "decision_id": "d2"}},
        {"event_type": "decision", "timestamp_utc": "2026-06-06T00:00:20Z", "payload": {"asset": "BTC", "market_regime": "SIDEWAY", "decision_id": "d3"}},
    ]
    with (path / "2026-06-06.jsonl").open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")


def test_generates_four_panel_report_and_deduplicates_canonical_opportunities(tmp_path: Path) -> None:
    csv_path = tmp_path / "completed_trades_v1_2.csv"
    output_path = tmp_path / "command_center.md"
    decision_dir = tmp_path / "decision_log"
    _write_csv(
        csv_path,
        [
            _row(),
            _row(pnl_usdc=0.02),  # duplicate logical opportunity; ignored for canonical n
            _row(condition_id="condition-b", epoch_start_ts=1780000300, candidate_id="candidate-b", pnl_usdc=-0.004, outcome_win_loss="LOSS", trade_result="SL", regime="SIDEWAY"),
            _row(asset="BTC", condition_id="condition-c", candidate_id="candidate-c", pnl_usdc=-0.01, outcome_win_loss="LOSS", trade_result="SL"),
            _row(side="NO", condition_id="condition-d", candidate_id="candidate-d"),
            _row(hold_seconds=10, condition_id="condition-e", candidate_id="candidate-e"),
        ],
    )
    _write_decision_log(decision_dir)

    metrics = command_center.generate_command_center_report(
        csv_path=csv_path,
        output_path=output_path,
        decision_log_dir=decision_dir,
        today="2026-06-07",
    )

    assert metrics.n == 2
    assert metrics.duplicate_rows_removed == 1
    assert metrics.wr == pytest.approx(0.5)
    assert metrics.pf == pytest.approx(2.5)
    assert metrics.decision_metrics.eth_compression_share_latest == pytest.approx(0.5)
    assert metrics.decision_metrics.btc_regime_latest == "SIDEWAY"
    report = output_path.read_text(encoding="utf-8")
    assert "## Panel A: Gate Status" in report
    assert "## Panel B: Progress Rail" in report
    assert "## Panel C: Leading Indicators" in report
    assert "## Panel D: Kill Criterion Monitors" in report
    assert "Canonical n | 2" in report
    assert "Duplicate rows removed | 1" in report


def test_csv_only_mode_marks_decision_metrics_manual(tmp_path: Path) -> None:
    csv_path = tmp_path / "completed_trades_v1_2.csv"
    output_path = tmp_path / "command_center.md"
    _write_csv(csv_path, [_row()])

    metrics = command_center.generate_command_center_report(
        csv_path=csv_path,
        output_path=output_path,
        today="2026-06-07",
    )

    assert metrics.n == 1
    assert metrics.decision_metrics.available is False
    report = output_path.read_text(encoding="utf-8")
    assert "[MANUAL REQUIRED]" in report
