from __future__ import annotations

import json
from pathlib import Path

from tools.runtime.paper_evaluation_report import (
    DECISION_CAUTION,
    DECISION_FAIL,
    DECISION_PASS,
    evaluate_paper_run,
)


DATE = "2026-05-08"
NEXT_DATE = "2026-05-09"


def _quality_report(**overrides) -> dict:
    report = {
        "date": DATE,
        "files_scanned": 5,
        "lines_scanned": 100,
        "valid_events": 100,
        "bad_json_lines": 0,
        "missing_required_fields": 0,
        "invalid_timestamps": 0,
        "invalid_event_types": 0,
        "invalid_modes": 0,
        "invalid_numeric_fields": 0,
        "unreadable_files": 0,
        "ok": True,
    }
    report.update(overrides)
    return report


def _replay_report(**overrides) -> dict:
    report = {
        "date_from": DATE,
        "date_to": DATE,
        "events_loaded": 120,
        "bad_json_lines": 0,
        "total_trades": 25,
        "wins": 16,
        "losses": 9,
        "win_rate": 0.64,
        "gross_pnl": 4.25,
        "average_pnl": 0.17,
        "max_win": 0.8,
        "max_loss": -0.4,
        "max_drawdown_pct": 0.02,
        "skipped_decisions": 4,
        "top_skip_reasons": [["confidence_too_low", 4]],
        "approved_decisions": 25,
        "rejected_decisions": 4,
        "risk_reject_count": 0,
        "execution_failure_count": 0,
        "average_spread_at_entry": 0.03,
        "average_confidence_at_entry": 0.68,
        "confidence_pnl_correlation": 0.25,
        "pnl_by_outcome": {"YES": 2.0, "NO": 2.25},
        "pnl_by_asset": {"BTC": 2.5, "ETH": 1.75},
    }
    report.update(overrides)
    return report


def _write_reports(report_dir: Path, quality: dict | None = None, replay: dict | None = None) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    if quality is not None:
        (report_dir / f"quant_data_quality_{DATE}.json").write_text(
            json.dumps(quality),
            encoding="utf-8",
        )
    if replay is not None:
        (report_dir / f"replay_report_{DATE}.json").write_text(
            json.dumps(replay),
            encoding="utf-8",
        )


def test_clean_profitable_report_returns_pass(tmp_path: Path) -> None:
    report_dir = tmp_path / "runtime" / "reports"
    _write_reports(report_dir, _quality_report(), _replay_report())

    report = evaluate_paper_run(report_dir=report_dir, date=DATE)

    assert report.decision == DECISION_PASS
    assert report.fail_reasons == []
    assert report.caution_reasons == []


def test_malformed_data_quality_returns_fail(tmp_path: Path) -> None:
    report_dir = tmp_path / "runtime" / "reports"
    _write_reports(report_dir, _quality_report(bad_json_lines=1, ok=False), _replay_report())

    report = evaluate_paper_run(report_dir=report_dir, date=DATE)

    assert report.decision == DECISION_FAIL
    assert "data_quality_bad_json_lines" in report.fail_reasons


def test_severe_risk_events_return_fail(tmp_path: Path) -> None:
    report_dir = tmp_path / "runtime" / "reports"
    _write_reports(report_dir, _quality_report(), _replay_report(severe_risk_events=1))

    report = evaluate_paper_run(report_dir=report_dir, date=DATE)

    assert report.decision == DECISION_FAIL
    assert "severe_risk_events_present" in report.fail_reasons


def test_too_small_sample_returns_caution(tmp_path: Path) -> None:
    report_dir = tmp_path / "runtime" / "reports"
    _write_reports(
        report_dir,
        _quality_report(),
        _replay_report(total_trades=3, wins=2, losses=1, win_rate=2 / 3, gross_pnl=0.4, approved_decisions=3),
    )

    report = evaluate_paper_run(report_dir=report_dir, date=DATE)

    assert report.decision == DECISION_CAUTION
    assert "sample_size_too_small" in report.caution_reasons


def test_empty_reports_fail_softly(tmp_path: Path) -> None:
    report = evaluate_paper_run(report_dir=tmp_path / "missing", date=DATE)

    assert report.decision == DECISION_FAIL
    assert "missing_or_empty_data_quality_report" in report.fail_reasons
    assert "missing_or_empty_replay_report" in report.fail_reasons


def test_output_json_is_created(tmp_path: Path) -> None:
    report_dir = tmp_path / "runtime" / "reports"
    _write_reports(report_dir, _quality_report(), _replay_report())

    report = evaluate_paper_run(report_dir=report_dir, date=DATE, write_report=True)
    output = report_dir / f"paper_evaluation_{DATE}.json"

    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["decision"] == report.decision


def test_date_range_uses_range_replay_and_daily_quality_reports(tmp_path: Path) -> None:
    report_dir = tmp_path / "runtime" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / f"quant_data_quality_{DATE}.json").write_text(json.dumps(_quality_report()), encoding="utf-8")
    (report_dir / f"quant_data_quality_{NEXT_DATE}.json").write_text(
        json.dumps(_quality_report(date=NEXT_DATE, lines_scanned=50, valid_events=50)),
        encoding="utf-8",
    )
    (report_dir / f"replay_report_{DATE}_to_{NEXT_DATE}.json").write_text(
        json.dumps(_replay_report(date_from=DATE, date_to=NEXT_DATE)),
        encoding="utf-8",
    )

    report = evaluate_paper_run(report_dir=report_dir, date_from=DATE, date_to=NEXT_DATE)

    assert report.decision == DECISION_PASS
    assert report.metrics["quality"]["bad_json_lines"] == 0
    assert (report_dir / f"paper_evaluation_{DATE}_to_{NEXT_DATE}.json").exists()
