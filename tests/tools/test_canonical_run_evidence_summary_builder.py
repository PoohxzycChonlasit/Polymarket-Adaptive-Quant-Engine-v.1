import json
from pathlib import Path

from tools.canonical_run_evidence_summary_builder import (
    build_canonical_run_evidence_summary,
    load_run_records,
    write_summary,
)


def test_builds_trade_funnel_and_conservative_validity_from_minimal_records():
    records = [
        {
            "run_id": "run-1",
            "mode": "paper",
            "timestamp_utc": "2026-06-30T10:00:00Z",
            "event_type": "decision",
            "payload": {
                "market_id": "m-1",
                "candidate_id": "c-1",
                "ev_after_spread": 0.06,
                "min_ev": 0.05,
                "skip_reason": "delta_extreme",
                "market_readiness_state": "ready",
                "epoch_start_ts": "2026-06-30T09:59:00Z",
                "epoch_end_ts": "2026-06-30T10:04:00Z",
                "seconds_remaining": 240,
                "candidate_seen_ts": "2026-06-30T10:00:00Z",
                "decision_latency_ms": 12,
                "orderbook_age_ms": 150,
            },
        },
        {
            "run_id": "run-1",
            "timestamp_utc": "2026-06-30T10:00:05Z",
            "event_type": "execution",
            "payload": {
                "market_id": "m-1",
                "reason": "entry_approved",
                "order_intent": "ENTRY",
                "event": "paper_fill",
                "order_submit_timestamp_utc": "2026-06-30T10:00:04Z",
            },
        },
        {
            "run_id": "run-1",
            "timestamp_utc": "2026-06-30T10:00:06Z",
            "event_type": "trade_open",
            "payload": {"position_id": "p-1"},
        },
        {
            "run_id": "run-1",
            "timestamp_utc": "2026-06-30T10:00:30Z",
            "event_type": "trade_close",
            "payload": {
                "position_id": "p-1",
                "exit_reason": "stop_loss",
                "realized_pnl": -0.01,
                "exit_timestamp": "2026-06-30T10:00:30Z",
            },
        },
    ]

    summary = build_canonical_run_evidence_summary(records, run_id="run-1")

    funnel = summary["trade_funnel_summary_v1"]
    assert funnel["run_id"] == "run-1"
    assert funnel["mode"] == "paper"
    assert funnel["decisions"] == 1
    assert funnel["active_markets_seen"] == 1
    assert funnel["tradable_markets"] == 1
    assert funnel["candidates"] == 1
    assert funnel["ev_pass_count"] == 1
    assert funnel["risk_approved_count"] == 1
    assert funnel["order_intents"] == 1
    assert funnel["fills"] == 1
    assert funnel["opens"] == 1
    assert funnel["closes"] == 1
    assert funnel["tp_count"] == 0
    assert funnel["sl_count"] == 1
    assert funnel["net_pnl"] == -0.01
    assert funnel["top_no_trade_reasons"] == [{"reason": "delta_extreme", "count": 1}]

    field_map = summary["market_time_truth_field_map_v1"]
    assert field_map["market_window_start_utc"]["status"] == "ALIAS_PRESENT"
    assert field_map["market_window_end_utc"]["status"] == "ALIAS_PRESENT"
    assert field_map["decision_latency_ms"]["status"] == "KNOWN_PRESENT"
    assert field_map["source_orderbook_ts_utc"]["status"] == "ALIAS_PRESENT"
    assert field_map["chainlink_reference_ts_utc"]["status"] == "MISSING"

    validity = summary["evidence_validity_v1"]["labels"]
    assert "VALID_FOR_BLOCKER_DIAGNOSIS" in validity
    assert "VALID_FOR_ACCOUNTING_CHECK" in validity
    assert "PARTIAL_FOR_MARKET_REALISM" in validity
    assert "INVALID_FOR_PROFIT_CLAIM" in validity


def test_missing_fields_do_not_crash_and_profit_claim_remains_invalid():
    summary = build_canonical_run_evidence_summary(
        [
            {
                "run_id": "run-missing",
                "timestamp_utc": "2026-06-30T10:00:00Z",
                "event_type": "decision",
                "payload": {},
            }
        ],
        run_id="run-missing",
    )

    field_map = summary["market_time_truth_field_map_v1"]
    assert field_map["market_window_start_utc"]["status"] == "MISSING"
    assert field_map["settlement_ts_utc"]["status"] == "MISSING"
    assert summary["dashboard_data_availability_v1"]["Time Truth Board"] == "PARTIAL"
    assert summary["trade_funnel_summary_v1"]["evidence_validity"] == [
        "VALID_FOR_BLOCKER_DIAGNOSIS",
        "PARTIAL_FOR_MARKET_REALISM",
        "INVALID_FOR_PROFIT_CLAIM",
    ]


def test_reports_raw_and_classified_blockers_side_by_side_when_they_conflict():
    records = [
        {
            "run_id": "run-conflict",
            "timestamp_utc": "2026-06-30T10:00:00Z",
            "event_type": "decision",
            "payload": {
                "market_id": "m-1",
                "skip_reason": "risk_off",
                "normalized_skip_reason": "risk_off",
                "raw_skip_reason": "risk_mode_lockdown:hard_drawdown",
                "model_not_run_reason": "risk_off",
                "model_activation_block_group": "RUNTIME_SAFETY_GATE",
                "skip_reason_primary": "book_warming",
                "skip_reason_category": "timing",
                "timing_block_reason": "book_warming",
                "no_entry_root_cause_confidence": 0.6,
                "executable_book_state": "NONZERO_BOOK",
            },
        }
    ]

    summary = build_canonical_run_evidence_summary(records, run_id="run-conflict")
    funnel = summary["trade_funnel_summary_v1"]

    assert funnel["primary_runtime_blocker"] == "risk_off"
    assert funnel["primary_classifier_blocker"] == "book_warming"
    assert funnel["blocker_source_priority"] == "raw_runtime_first"
    assert funnel["raw_vs_classified_blocker_conflict"] is True
    assert funnel["raw_vs_classified_conflict_count"] == 1
    assert funnel["raw_vs_classified_conflict_rate"] == 1.0
    assert funnel["evidence_blocker_truth_status"] == "RAW_CLASSIFIED_CONFLICT"

    raw_summary = funnel["raw_runtime_blocker_summary"]
    assert raw_summary["skip_reason_counts"] == [{"reason": "risk_off", "count": 1}]
    assert raw_summary["raw_skip_reason_counts"] == [
        {"reason": "risk_mode_lockdown:hard_drawdown", "count": 1}
    ]
    assert raw_summary["model_not_run_reason_counts"] == [{"reason": "risk_off", "count": 1}]
    assert raw_summary["risk_safety_blocker_counts"] == [
        {"reason": "risk_mode_lockdown:hard_drawdown", "count": 1}
    ]

    classified_summary = funnel["classified_blocker_summary"]
    assert classified_summary["skip_reason_primary_counts"] == [{"reason": "book_warming", "count": 1}]
    assert classified_summary["timing_block_reason_counts"] == [{"reason": "book_warming", "count": 1}]
    assert classified_summary["skip_reason_category_counts"] == [{"reason": "timing", "count": 1}]

    conflict_summary = funnel["blocker_conflict_summary"]
    assert conflict_summary["conflict_count"] == 1
    assert conflict_summary["warnings"] == [
        "classifier_primary_differs_from_raw_runtime_blocker",
        "runtime_safety_gate_with_classifier_timing_blocker",
    ]
    assert conflict_summary["examples"][0]["raw_runtime_blocker"] == "risk_off"
    assert conflict_summary["examples"][0]["raw_skip_reason"] == "risk_mode_lockdown:hard_drawdown"
    assert conflict_summary["examples"][0]["classifier_blocker"] == "book_warming"


def test_legacy_top_no_trade_reasons_prefers_raw_runtime_blocker_over_classifier_label():
    records = [
        {
            "run_id": "run-raw-first",
            "timestamp_utc": "2026-06-30T10:00:00Z",
            "event_type": "decision",
            "payload": {
                "skip_reason": "risk_off",
                "raw_skip_reason": "risk_mode_lockdown:hard_drawdown",
                "model_not_run_reason": "risk_off",
                "skip_reason_primary": "book_warming",
                "timing_block_reason": "book_warming",
            },
        },
        {
            "run_id": "run-raw-first",
            "timestamp_utc": "2026-06-30T10:01:00Z",
            "event_type": "decision",
            "payload": {
                "skip_reason": "risk_off",
                "raw_skip_reason": "risk_mode_lockdown:hard_drawdown",
                "model_not_run_reason": "risk_off",
                "skip_reason_primary": "book_warming",
                "timing_block_reason": "book_warming",
            },
        },
    ]

    summary = build_canonical_run_evidence_summary(records, run_id="run-raw-first")
    funnel = summary["trade_funnel_summary_v1"]

    assert funnel["top_no_trade_reasons"] == [{"reason": "risk_off", "count": 2}]
    assert funnel["classified_blocker_summary"]["skip_reason_primary_counts"] == [
        {"reason": "book_warming", "count": 2}
    ]
    assert funnel["raw_vs_classified_conflict_count"] == 2


def test_load_run_records_filters_by_run_id_and_tags_source_stream(tmp_path):
    quant_data = tmp_path / "runtime" / "quant_data"
    decision_dir = quant_data / "decision_log"
    trade_dir = quant_data / "trade_journal"
    decision_dir.mkdir(parents=True)
    trade_dir.mkdir(parents=True)
    date = "2026-06-30"

    (decision_dir / f"{date}.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "run_id": "wanted",
                        "timestamp_utc": "2026-06-30T10:00:00Z",
                        "event_type": "decision",
                    }
                ),
                json.dumps(
                    {
                        "run_id": "other",
                        "timestamp_utc": "2026-06-30T10:01:00Z",
                        "event_type": "decision",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (trade_dir / f"{date}.jsonl").write_text(
        json.dumps(
            {
                "run_id": "wanted",
                "timestamp_utc": "2026-06-30T10:00:10Z",
                "event_type": "trade_open",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    records = load_run_records(quant_data, date=date, run_id="wanted")

    assert len(records) == 2
    assert {record["_source_stream"] for record in records} == {
        "decision_log",
        "trade_journal",
    }
    assert {record["run_id"] for record in records} == {"wanted"}


def test_write_summary_emits_valid_json(tmp_path):
    summary = build_canonical_run_evidence_summary([], run_id="empty-run")

    output_path = write_summary(summary, tmp_path, pretty=True)

    assert output_path == tmp_path / "empty-run_canonical_evidence_summary.json"
    assert json.loads(output_path.read_text(encoding="utf-8"))["schema_version"] == (
        "canonical_run_evidence_summary.v1"
    )
