from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from tools.unknown.edge_inventory_report import (
    ATTRIBUTION_FIELDS,
    NOT_READY_METRICS,
    build_report,
    load_trade_journal_events,
    main,
)


RUN_ID = "run-edge-1"
POSITION_ID = "position-1"


def _attribution(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "candidate_id": "candidate-logical",
        "candidate_trace_id": "ct-legacy",
        "candidate_instance_id": "candidate-instance",
        "candidate_instance_trace_id": "ct-instance",
        "candidate_instance_created_at": "2026-06-15T00:00:00Z",
        "candidate_instance_identity_schema_version": "1.0",
        "candidate_instance_identity_source": "opportunity_candidate",
        "legacy_candidate_identity_source": "phase2_market_side_epoch_hash",
        "signal_name": "trend",
        "signal_reason": "trend_yes_adx_ema_confirmed",
        "paper_trade_replay_key": "condition|epoch|BTC|YES|token",
        "entry_ev": 0.08,
        "entry_probability": 0.64,
        "selected_side": "YES",
    }
    value.update(overrides)
    return value


def _event(
    event_type: str,
    timestamp: str,
    payload: dict[str, object],
    *,
    run_id: str = RUN_ID,
    mode: str = "paper",
) -> dict[str, object]:
    return {
        "event_type": event_type,
        "timestamp_utc": timestamp,
        "run_id": run_id,
        "mode": mode,
        "payload": payload,
    }


def _open(
    *,
    run_id: str = RUN_ID,
    position_id: str = POSITION_ID,
    attribution: dict[str, object] | None = None,
    status: str = "ready",
    mode: str = "paper",
) -> dict[str, object]:
    payload: dict[str, object] = {
        "position_id": position_id,
        "entry_attribution_status": status,
    }
    if attribution is not None or status != "missing_legacy":
        payload["entry_attribution"] = attribution if attribution is not None else _attribution()
    return _event("trade_open", "2026-06-15T00:00:00Z", payload, run_id=run_id, mode=mode)


def _close(
    *,
    run_id: str = RUN_ID,
    position_id: str = POSITION_ID,
    attribution: dict[str, object] | None = None,
    status: str = "ready",
    partial: bool = False,
    **pnl_fields: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "position_id": position_id,
        "entry_attribution_status": status,
        "partial": partial,
        **({"pnl_usdc": 0.20} if not pnl_fields else pnl_fields),
    }
    if attribution is not None or status != "missing_legacy":
        payload["entry_attribution"] = attribution if attribution is not None else _attribution()
    return _event("trade_close", "2026-06-15T00:01:00Z", payload, run_id=run_id)


def _write_jsonl(path: Path, events: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")


def test_joins_by_run_id_and_position_id_and_preserves_attribution() -> None:
    attribution = _attribution()

    report = build_report([_open(attribution=attribution), _close(attribution=attribution)])

    assert report["summary"]["closed_trade_count"] == 1
    row = report["closed_trades"][0]
    assert row["run_id"] == RUN_ID
    assert row["position_id"] == POSITION_ID
    assert all(row["entry_attribution"][k] == v for k, v in attribution.items())
    assert all(row[field] == row["entry_attribution"][field] for field in ATTRIBUTION_FIELDS)
    assert row["realized_pnl"] == pytest.approx(0.20)
    assert row["outcome"] == "win"


def test_cross_run_position_collision_produces_two_trades() -> None:
    events = [
        _open(run_id="run-a"),
        _close(run_id="run-a"),
        _open(run_id="run-b"),
        _close(run_id="run-b", pnl_usdc=-0.10),
    ]

    report = build_report(events)

    assert report["summary"]["closed_trade_count"] == 2
    assert {(row["run_id"], row["position_id"]) for row in report["closed_trades"]} == {
        ("run-a", POSITION_ID),
        ("run-b", POSITION_ID),
    }


def test_partial_closes_sum_pnl_and_require_one_terminal_close() -> None:
    events = [
        _open(),
        _close(partial=True, pnl_usdc=0.05),
        _close(partial=True, pnl_usdc=0.03),
        _close(partial=False, pnl_usdc=-0.02),
        _open(position_id="open-only"),
        _close(position_id="open-only", partial=True, pnl_usdc=0.10),
    ]

    report = build_report(events)

    row = report["closed_trades"][0]
    assert row["realized_pnl"] == pytest.approx(0.06)
    assert row["partial_close_count"] == 2
    assert report["summary"]["open_only_count"] == 1


def test_pnl_fallback_precedence_and_outcome_classification() -> None:
    events = [
        _open(position_id="win"),
        _close(position_id="win", pnl_usdc=0.30, pnl=-9.0, realized_pnl=-8.0),
        _open(position_id="loss"),
        _close(position_id="loss", pnl=-0.20, realized_pnl=8.0),
        _open(position_id="flat"),
        _close(position_id="flat", realized_pnl=0.0),
    ]

    report = build_report(events)
    rows = {row["position_id"]: row for row in report["closed_trades"]}

    assert rows["win"]["realized_pnl"] == pytest.approx(0.30)
    assert rows["loss"]["realized_pnl"] == pytest.approx(-0.20)
    assert rows["flat"]["realized_pnl"] == pytest.approx(0.0)
    assert [rows[name]["outcome"] for name in ("win", "loss", "flat")] == [
        "win",
        "loss",
        "breakeven",
    ]


def test_group_tables_metrics_and_null_safe_average_denominators() -> None:
    events = [
        _open(position_id="one"),
        _close(position_id="one", pnl_usdc=0.30),
        _open(position_id="two", attribution=_attribution(entry_ev=None, entry_probability=None)),
        _close(
            position_id="two",
            attribution=_attribution(entry_ev=None, entry_probability=None),
            pnl_usdc=-0.10,
        ),
    ]

    report = build_report(events)
    signal = report["signal_edge_summary"][0]

    assert signal["signal_name"] == "trend"
    assert signal["closed_trade_count"] == 2
    assert signal["win_count"] == 1
    assert signal["loss_count"] == 1
    assert signal["breakeven_count"] == 0
    assert signal["win_rate"] == pytest.approx(0.5)
    assert signal["total_realized_pnl"] == pytest.approx(0.20)
    assert signal["avg_realized_pnl"] == pytest.approx(0.10)
    assert signal["avg_entry_ev"] == pytest.approx(0.08)
    assert signal["avg_entry_ev_denominator"] == 1
    assert signal["missing_entry_ev_count"] == 1
    assert signal["avg_entry_probability_denominator"] == 1
    assert signal["missing_entry_probability_count"] == 1
    assert report["signal_reason_summary"][0]["signal_reason"] == "trend_yes_adx_ema_confirmed"
    assert report["logical_candidate_summary"][0]["candidate_id"] == "candidate-logical"
    assert report["candidate_instance_summary"][0]["candidate_instance_id"] == "candidate-instance"


def test_legacy_is_segregated_and_not_added_to_identity_tables() -> None:
    report = build_report(
        [
            _open(status="missing_legacy"),
            _close(status="missing_legacy", pnl_usdc=0.15),
        ]
    )

    assert report["summary"]["closed_trade_count"] == 1
    assert report["summary"]["legacy_trade_count"] == 1
    assert len(report["unattributed_legacy_trades"]) == 1
    assert report["signal_edge_summary"] == []
    assert report["logical_candidate_summary"] == []
    assert "signal_name" not in report["unattributed_legacy_trades"][0]


@pytest.mark.parametrize(
    ("events", "reason"),
    [
        ([_open(), _open(), _close()], "duplicate_open"),
        ([_open(), _close(), _close()], "duplicate_terminal_close"),
        (
            [_open(), _close(attribution=_attribution(signal_name="reversion"))],
            "conflicting_attribution",
        ),
        (
            [_open(attribution=_attribution(candidate_id=None)), _close(attribution=_attribution(candidate_id=None))],
            "malformed_attribution",
        ),
    ],
)
def test_invalid_completed_positions_are_quarantined(
    events: list[dict[str, object]],
    reason: str,
) -> None:
    report = build_report(events)

    assert report["summary"]["closed_trade_count"] == 0
    assert report["summary"]["quarantined_trade_count"] == 1
    assert reason in report["quarantined_trades"][0]["quarantine_reason"]


def test_missing_position_id_is_quarantined() -> None:
    event = _open()
    del event["payload"]["position_id"]  # type: ignore[index]

    report = build_report([event])

    assert report["summary"]["quarantined_trade_count"] == 1
    assert report["quarantined_trades"][0]["quarantine_reason"] == "missing_position_id"


def test_missing_close_pnl_is_quarantined_instead_of_fabricating_breakeven() -> None:
    report = build_report([_open(), _close(pnl_usdc=None)])

    assert report["summary"]["closed_trade_count"] == 0
    assert report["quarantined_trades"][0]["quarantine_reason"] == "missing_close_pnl"


def test_empty_input_and_metadata_are_fail_soft() -> None:
    report = build_report([])

    assert report["summary"]["closed_trade_count"] == 0
    assert report["report_readiness_verdict"] == "NO_CLOSED_TRADES"
    assert report["metadata"]["offline_only"] is True
    assert set(report["metadata"]["not_ready_metrics"]) == set(NOT_READY_METRICS)


def test_loader_filters_date_mode_and_event_type(tmp_path: Path) -> None:
    journal = tmp_path / "trade_journal"
    _write_jsonl(
        journal / "2026-06-15.jsonl",
        [_open(), _event("decision", "2026-06-15T00:00:00Z", {}), _open(mode="live")],
    )
    _write_jsonl(journal / "2026-06-16.jsonl", [_open(run_id="next")])

    events = load_trade_journal_events(journal, date_from="2026-06-15", date_to="2026-06-15")

    assert len(events) == 1
    assert events[0]["event_type"] == "trade_open"
    assert events[0]["mode"] == "paper"


def test_cli_defaults_to_print_only_and_write_flags_are_explicit(tmp_path: Path, capsys) -> None:
    journal = tmp_path / "quant_data" / "trade_journal"
    _write_jsonl(journal / "2026-06-15.jsonl", [_open(), _close()])
    reports = tmp_path / "reports"
    exports = tmp_path / "exports"

    assert main(
        [
            "--date",
            "2026-06-15",
            "--trade-journal-dir",
            str(journal),
            "--report-dir",
            str(reports),
            "--export-dir",
            str(exports),
        ]
    ) == 0
    assert "closed_trade_count=1" in capsys.readouterr().out
    assert not reports.exists()
    assert not exports.exists()

    assert main(
        [
            "--from",
            "2026-06-15",
            "--to",
            "2026-06-15",
            "--trade-journal-dir",
            str(journal),
            "--report-dir",
            str(reports),
            "--export-dir",
            str(exports),
            "--write-json",
            "--write-md",
            "--write-csv",
        ]
    ) == 0
    assert (reports / "edge_inventory_report_v1.json").exists()
    assert (reports / "edge_inventory_report_v1.md").exists()
    assert (exports / "edge_inventory_closed_trades_v1.csv").exists()


def test_tool_has_no_runtime_or_replay_dependency() -> None:
    path = Path(__file__).resolve().parents[1] / "tools" / "edge_inventory_report.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert not any(
        name == "main"
        or name.startswith("polymarket")
        or name.startswith("utils")
        or name.startswith("tools.replay_analyzer")
        for name in imports
    )


def test_two_tier_schema_attribution_and_legacy_fallback() -> None:
    # 1. Existing Patch-5 rows without strategy fields remain attribution-complete.
    # 3. Missing strategy fields are normalized without modifying raw input.
    legacy_attr = _attribution()
    assert "strategy_signal_name" not in legacy_attr
    assert "strategy_signal_reason" not in legacy_attr

    legacy_attr_copy = dict(legacy_attr)

    report = build_report([_open(attribution=legacy_attr), _close(attribution=legacy_attr)])
    assert report["summary"]["closed_trade_count"] == 1
    assert report["summary"]["valid_attributed_trade_count"] == 1

    row = report["closed_trades"][0]
    # Strategy fields are normalized/present in output
    assert row["strategy_signal_name"] == "trend"
    assert row["strategy_signal_reason"] == "trend_yes_adx_ema_confirmed"

    # 4. Primary signal grouping remains unchanged.
    assert report["signal_edge_summary"][0]["signal_name"] == "trend"
    assert report["signal_reason_summary"][0]["signal_reason"] == "trend_yes_adx_ema_confirmed"

    # Verify raw input was not modified
    assert "strategy_signal_name" not in legacy_attr
    assert legacy_attr == legacy_attr_copy

    # 2. New two-tier rows with strategy fields are parsed correctly.
    # 5. Strategy fields appear in closed-trade row output.
    new_attr = _attribution(
        signal_name="PROBABILITY_EV_EDGE",
        signal_reason="yes_ev_above_threshold",
        strategy_signal_name="reversion",
        strategy_signal_reason="reversion_yes_threshold_met"
    )
    report_new = build_report([_open(attribution=new_attr), _close(attribution=new_attr)])
    assert report_new["summary"]["closed_trade_count"] == 1
    assert report_new["summary"]["valid_attributed_trade_count"] == 1

    row_new = report_new["closed_trades"][0]
    assert row_new["signal_name"] == "PROBABILITY_EV_EDGE"
    assert row_new["signal_reason"] == "yes_ev_above_threshold"
    assert row_new["strategy_signal_name"] == "reversion"
    assert row_new["strategy_signal_reason"] == "reversion_yes_threshold_met"

    # Strategy summaries are populated correctly
    assert report_new["strategy_signal_edge_summary"][0]["strategy_signal_name"] == "reversion"
    assert report_new["strategy_signal_reason_summary"][0]["strategy_signal_reason"] == "reversion_yes_threshold_met"
    # Primary signal grouping remains "PROBABILITY_EV_EDGE"
    assert report_new["signal_edge_summary"][0]["signal_name"] == "PROBABILITY_EV_EDGE"
    assert report_new["signal_reason_summary"][0]["signal_reason"] == "yes_ev_above_threshold"

    # 6. Legacy NO_SIGNAL remains NO_SIGNAL in primary grouping
    no_sig_attr = _attribution(
        signal_name="NO_SIGNAL",
        signal_reason="no_strategy_met_threshold"
    )
    report_no_sig = build_report([_open(attribution=no_sig_attr), _close(attribution=no_sig_attr)])
    assert report_no_sig["signal_edge_summary"][0]["signal_name"] == "NO_SIGNAL"
    assert report_no_sig["strategy_signal_edge_summary"][0]["strategy_signal_name"] == "NO_SIGNAL"
    assert report_no_sig["strategy_signal_reason_summary"][0]["strategy_signal_reason"] == "no_strategy_met_threshold"
