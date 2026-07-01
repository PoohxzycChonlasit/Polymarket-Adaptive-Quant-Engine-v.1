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
