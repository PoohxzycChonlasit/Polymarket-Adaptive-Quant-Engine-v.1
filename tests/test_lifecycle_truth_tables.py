import json
from pathlib import Path

from tools.lifecycle_truth_tables import (
    build_lifecycle_truth_tables,
    main,
    write_lifecycle_truth_tables,
)


DATE = "2026-05-08"


def _write_jsonl(base_dir: Path, category: str, events: list[dict]) -> None:
    path = base_dir / category / f"{DATE}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n",
        encoding="utf-8",
    )


def _event(
    timestamp: str,
    payload: dict,
    *,
    run_id: str = "run-target",
    event_type: str = "candidate_decision",
    asset: str = "BTC",
) -> dict:
    return {
        "timestamp_utc": timestamp,
        "event_type": event_type,
        "mode": "paper",
        "asset": asset,
        "run_id": run_id,
        "source_module": "synthetic_test",
        "schema_version": "1.0",
        "payload": payload,
    }


def test_build_lifecycle_truth_tables_classifies_direct_and_proxy_rows(tmp_path):
    base_dir = tmp_path / "quant_data"
    _write_jsonl(
        base_dir,
        "decision_log",
        [
            _event(
                "2026-05-08T12:00:01Z",
                {
                    "decision": "skip",
                    "normalized_skip_reason": "risk_plan_zero",
                    "candidate_id": "candidate-btc-after-ev",
                    "signal_id": "signal-btc-after-ev",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "token_ready_at": "2026-05-08T12:00:00Z",
                    "orderbook_ready_at": "2026-05-08T12:00:00Z",
                    "liquidity_ready_at": "2026-05-08T12:00:00Z",
                    "spread_ready_at": "2026-05-08T12:00:00Z",
                    "first_tradable_at": "2026-05-08T12:00:00Z",
                    "first_evaluable_at": "2026-05-08T12:00:01Z",
                    "fair_value": 0.62,
                    "market_price": 0.58,
                    "true_probability": 0.62,
                    "ev_after_spread": 0.03,
                    "fair_value_available": True,
                    "market_price_available": True,
                    "true_probability_available": True,
                    "ev_after_spread_available": True,
                    "probability_model_stage": "completed",
                    "ev_calculation_stage": "risk_blocked_after_ev",
                    "candidate_block_reason": "risk_plan_zero",
                    "candidate_block_stage": "post_ev",
                    "readiness_transition_reason": "ready",
                    "market_readiness_state": "ready",
                    "candidate_survival_ms": 1500,
                    "candidate_expiry_reason": "risk_block",
                    "lifecycle_phase_transition_reason": "epoch_window_direct",
                    "lifecycle_phase_entered_at": "2026-05-08T12:00:35Z",
                    "lifecycle_phase_exited_at": "2026-05-08T12:04:00Z",
                    "ev_candidate_ready": True,
                    "model_output_ready": True,
                    "orderbook_state_classification": "ready",
                    "inventory_action": "OPEN",
                    "starter_candidate": True,
                    "exposure_before": 0.0,
                    "exposure_after": 0.0,
                    "risk_budget_used": 0.2,
                    "remaining_risk_budget": 0.8,
                    "liquidity_state": "READY",
                },
            ),
            _event(
                "2026-05-08T12:00:02Z",
                {
                    "decision": "skip",
                    "normalized_skip_reason": "time_unsafe",
                    "candidate_id": "candidate-eth-before-ev",
                    "signal_id": "signal-eth-before-ev",
                    "lifecycle_phase": "PROFIT_MANAGEMENT",
                    "fair_value_available": False,
                    "fair_value_null_reason": "time_unsafe",
                    "market_price_available": False,
                    "market_price_null_reason": "no_market_price",
                    "true_probability_available": False,
                    "true_probability_null_reason": "pre_model_skip",
                    "ev_after_spread_available": False,
                    "ev_after_spread_null_reason": "candidate_blocked_before_ev",
                    "probability_model_stage": "pre_model_skip",
                    "ev_calculation_stage": "candidate_blocked_before_ev",
                    "starter_candidate": True,
                    "seconds_remaining": 42,
                },
                asset="ETH",
            ),
            _event(
                "2026-05-08T12:00:03Z",
                {
                    "decision": "skip",
                    "normalized_skip_reason": "orderbook_unavailable",
                    "orderbook_unavailable_reason": "empty_book",
                    "candidate_id": "candidate-btc-empty-book",
                    "signal_id": "signal-btc-empty-book",
                    "lifecycle_phase": "OPENING_SCAN",
                    "fair_value_available": False,
                    "fair_value_null_reason": "no_orderbook",
                    "market_price_available": False,
                    "market_price_null_reason": "empty_book",
                    "ev_after_spread_available": False,
                    "ev_after_spread_null_reason": "no_orderbook",
                    "starter_candidate": True,
                    "liquidity_state": "EMPTY",
                },
            ),
            _event(
                "2026-05-08T12:00:04Z",
                {
                    "decision": "skip",
                    "normalized_skip_reason": "other_run",
                    "candidate_id": "candidate-other-run",
                    "starter_candidate": True,
                },
                run_id="run-other",
            ),
        ],
    )

    report = build_lifecycle_truth_tables(
        base_dir=base_dir,
        date_from=DATE,
        date_to=DATE,
        run_id="run-target",
    )

    assert report["events_loaded"] == 3
    assert report["candidate_events"] == 3
    assert report["run_id"] == "run-target"
    assert report["does_not_claim_profitability"] is True
    assert report["does_not_authorize_runtime_decisions"] is True
    assert report["direct_field_rate"] > 0
    assert report["proxy_field_rate"] > 0

    tables = report["tables"]
    assert {row["candidate_id"] for row in tables["starter_candidates"]} == {
        "candidate-btc-after-ev",
        "candidate-eth-before-ev",
        "candidate-btc-empty-book",
    }
    assert {row["candidate_id"] for row in tables["candidate_blocked_after_ev"]} == {
        "candidate-btc-after-ev"
    }
    after_ev_row = tables["candidate_blocked_after_ev"][0]
    assert after_ev_row["lifecycle_observability"]["candidate_block_stage"] == "post_ev"
    assert after_ev_row["lifecycle_observability"]["market_readiness_state"] == "ready"
    assert after_ev_row["lifecycle_observability"]["candidate_survival_ms"] == 1500
    assert "candidate-eth-before-ev" in {
        row["candidate_id"] for row in tables["candidate_blocked_before_ev"]
    }
    assert {row["candidate_id"] for row in tables["time_unsafe_candidates"]} == {
        "candidate-eth-before-ev"
    }
    assert {row["candidate_id"] for row in tables["liquidity_or_orderbook_blocked_candidates"]} == {
        "candidate-btc-empty-book"
    }

    assert tables["lifecycle_phase_distribution"]["counts"]["OPENING_SCAN"] == 1
    assert tables["lifecycle_phase_distribution"]["counts"]["PROFIT_MANAGEMENT"] == 1
    assert tables["ev_null_reason_distribution"]["counts"]["no_orderbook"] >= 1
    assert report["research_questions"]["are_btc_and_eth_failing_differently"]["answer"] == "compare_asset_counts"


def test_write_lifecycle_truth_tables_includes_sanitized_run_id(tmp_path):
    report = {
        "date_from": DATE,
        "date_to": DATE,
        "run_id": "run/id:target",
        "time_filter": {"since": "12:00", "until": "12:05", "applied": True},
        "tables": {},
    }

    path = write_lifecycle_truth_tables(report, report_dir=tmp_path / "reports")

    assert path.name == "lifecycle_truth_tables_2026-05-08_1200_to_1205_run_run_id_target.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["run_id"] == "run/id:target"


def test_lifecycle_truth_tables_excludes_telemetry_without_candidate_continuity(tmp_path):
    base_dir = tmp_path / "quant_data"
    _write_jsonl(
        base_dir,
        "market_snapshots",
        [
            _event(
                "2026-05-08T12:00:01Z",
                {
                    "candidate_id": "candidate-market",
                    "signal_id": "signal-market",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "candidate_block_stage": "pre_ev",
                    "candidate_block_reason": "no_probability_model_output",
                    "fair_value_null_reason": "no_probability_model_output",
                    "market_readiness_state": "ready",
                    "orderbook_state_classification": "ready",
                },
            ),
        ],
    )
    _write_jsonl(
        base_dir,
        "execution_log",
        [
            _event(
                "2026-05-08T12:00:02Z",
                {
                    "event": "order_attempt",
                    "ev_after_spread_null_reason": "no_probability_model_output",
                    "market_price_null_reason": "no_market_price",
                },
                event_type="execution",
            ),
            _event(
                "2026-05-08T12:00:03Z",
                {
                    "event": "order_attempt",
                    "candidate_id": "candidate-execution-unowned",
                    "signal_id": "signal-execution-unowned",
                },
                event_type="execution",
            ),
            _event(
                "2026-05-08T12:00:04Z",
                {
                    "event": "order_attempt",
                    "candidate_id": "candidate-execution-owned",
                    "lifecycle_phase": "FINAL_DERISK",
                    "candidate_block_stage": "post_ev",
                    "candidate_block_reason": "risk_blocked_after_ev",
                },
                event_type="execution",
            ),
        ],
    )

    report = build_lifecycle_truth_tables(
        base_dir=base_dir,
        date_from=DATE,
        date_to=DATE,
        run_id="run-target",
    )

    assert report["events_loaded"] == 4
    assert report["candidate_events"] == 2
    assert report["excluded_telemetry_counts"]["excluded_total"] == 2
    assert report["excluded_telemetry_counts"]["excluded_legacy_candidate_like_events"] == 2
    assert report["excluded_telemetry_counts"]["by_category"]["execution_log"] == 2
    assert report["excluded_telemetry_counts"]["by_reason"]["excluded_telemetry_without_lifecycle_ownership"] == 2
    assert report["unknown_lifecycle_precision_metrics"]["legacy_candidate_like_events"] == 4
    assert report["unknown_lifecycle_precision_metrics"]["refined_candidate_events"] == 2
    assert report["unknown_lifecycle_precision_metrics"]["legacy_unknown_lifecycle_events"] == 2
    assert report["unknown_lifecycle_precision_metrics"]["refined_unknown_lifecycle_events"] == 0
    assert report["unknown_lifecycle_precision_metrics"]["unknown_lifecycle_events_removed_by_filter"] == 2
    assert report["evidence_completeness"]["candidate_classification_reasons"]["direct_candidate_identity"] == 2
    assert "UNKNOWN" not in report["tables"]["lifecycle_phase_distribution"]["counts"]
    before_row = report["tables"]["candidate_blocked_before_ev"][0]
    assert before_row["candidate_classification_reason"] == "direct_candidate_identity"
    assert before_row["candidate_classification_confidence"] == "high"


def test_lifecycle_truth_tables_cli_writes_report(tmp_path, monkeypatch, capsys):
    base_dir = tmp_path / "quant_data"
    report_dir = tmp_path / "reports"
    _write_jsonl(
        base_dir,
        "decision_log",
        [
            _event(
                "2026-05-08T12:00:01Z",
                {
                    "decision": "skip",
                    "normalized_skip_reason": "time_unsafe",
                    "candidate_id": "candidate-cli",
                    "signal_id": "signal-cli",
                    "starter_candidate": True,
                    "ev_after_spread_null_reason": "time_unsafe",
                },
            )
        ],
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "lifecycle_truth_tables",
            "--date",
            DATE,
            "--run-id",
            "run-target",
            "--base-dir",
            str(base_dir),
            "--report-dir",
            str(report_dir),
        ],
    )

    assert main() == 0
    output = capsys.readouterr().out
    assert "Lifecycle Truth Tables" in output
    assert (report_dir / "lifecycle_truth_tables_2026-05-08_run_run-target.json").exists()
