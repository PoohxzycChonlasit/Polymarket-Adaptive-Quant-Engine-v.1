from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from tools.runtime import compact_run_summary


DATE = "2026-05-12"


def _write_event(base_dir: Path, category: str, event: dict) -> None:
    path = base_dir / category / f"{DATE}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")


def _report(payload: dict):
    return SimpleNamespace(to_dict=lambda: payload)


def test_compact_summary_writes_prompt_sized_observability_report(tmp_path, monkeypatch) -> None:
    base_dir = tmp_path / "quant_data"
    report_dir = tmp_path / "reports"
    _write_event(
        base_dir,
        "decision_log",
        {
            "timestamp_utc": "2026-05-12T01:00:00Z",
            "run_id": "run-a",
            "payload": {
                "candidate_trace_id": "trace-1",
                "condition_id": "cond-1",
                "token_id": "token-yes",
                "side": "YES",
                "lifecycle_phase": "OPENING_SCAN",
                "market_key": "btc-5m",
                "skip_reason": "EV_NEVER_VISIBLE",
                "model_activation_state": "BLOCKED_BEFORE_MODEL",
                "model_activation_block_group": "ORDERBOOK_GATE",
                "model_activation_block_reason": "orderbook_not_ready",
                "model_attempt_eligible": False,
                "probability_model_called": False,
                "probability_model_output_visible": False,
                "model_handoff_stage": "PRE_MODEL_GATE",
                "model_output_missing_reason": "orderbook_not_ready",
                "pre_model_gate_name": "ORDERBOOK_COMPLETENESS_GATE",
                "pre_model_gate_group": "ORDERBOOK_GATE",
                "pre_model_gate_blocks_probability_model": True,
                "probability_model_call_path": "blocked_before_probability_model",
                "model_activation_seconds_remaining": 220,
                "first_seen_second": 40,
                "first_orderbook_ready_second": 80,
                "candidate_lifecycle_duration_seconds": 20,
                "ev": 0.01,
            },
        },
    )
    _write_event(
        base_dir,
        "risk_log",
        {
            "timestamp_utc": "2026-05-12T01:01:00Z",
            "run_id": "run-a",
            "payload": {"event": "risk_snapshot"},
        },
    )
    _write_event(
        base_dir,
        "decision_log",
        {
            "timestamp_utc": "2026-05-12T01:01:30Z",
            "run_id": "run-a",
            "payload": {
                "candidate_trace_id": "trace-derisk",
                "condition_id": "cond-1",
                "token_id": "token-no",
                "side": "NO",
                "lifecycle_phase": "FINAL_DERISK",
                "market_key": "btc-5m",
                "skip_reason": "hard_close_zone",
                "model_activation_state": "BLOCKED_BEFORE_MODEL",
                "model_activation_block_group": "TIME_CUTOFF_GATE",
                "model_activation_block_reason": "hard_close_zone",
                "model_attempt_eligible": False,
                "probability_model_called": False,
                "probability_model_output_visible": False,
                "model_handoff_stage": "PRE_MODEL_GATE",
                "model_output_missing_reason": "hard_close_zone",
                "pre_model_gate_name": "TIME_CUTOFF_GATE",
                "pre_model_gate_group": "TIME_CUTOFF_GATE",
                "pre_model_gate_blocks_probability_model": True,
                "probability_model_call_path": "blocked_before_probability_model",
                "model_activation_seconds_remaining": 25,
                "first_candidate_ready_second": 250,
            },
        },
    )
    _write_event(
        base_dir,
        "execution_log",
        {
            "timestamp_utc": "2026-05-12T01:02:00Z",
            "run_id": "run-a",
            "payload": {
                "event": "paper_order_submitted",
                "candidate_trace_id": "trace-1",
                "decision_id": "decision-1",
                "condition_id": "cond-1",
                "token_id": "token-yes",
                "side": "YES",
                "market_slug": "btc-updown-5m",
                "lifecycle_phase": "OPENING_SCAN",
                "true_probability": 0.61,
                "fair_value": 0.61,
                "probability_model_called": True,
                "probability_model_output_visible": True,
                "model_handoff_stage": "MODEL_OUTPUT_SERIALIZED",
                "model_output_source": "parent_decision_context",
                "risk_state": "approved",
            },
        },
    )
    _write_event(
        base_dir,
        "system_health",
        {
            "timestamp_utc": "2026-05-12T01:03:00Z",
            "run_id": "run-a",
            "payload": {"event": "heartbeat", "jsonl_status": "OK"},
        },
    )

    monkeypatch.setattr(
        compact_run_summary,
        "analyze_replay",
        lambda **_: _report(
            {
                "total_trades": 0,
                "top_skip_reasons": [["EV_NEVER_VISIBLE", 2]],
                "orderbook_readiness_reasons": [["ORDERBOOK_NOT_READY", 1]],
                "cutoff_block_count": 1,
                "average_orderbook_age_ms": 25.0,
                "max_orderbook_age_ms": 80.0,
            }
        ),
    )
    monkeypatch.setattr(
        compact_run_summary,
        "evaluate_session_runtime",
        lambda **_: _report({"skip_summary": {"top_skip_reasons": [["cutoff", 1]]}}),
    )
    monkeypatch.setattr(
        compact_run_summary,
        "build_ev_field_coverage_report",
        lambda **_: {
            "candidate_trace_confidence_counts": {"STRONG": 1, "PROXY": 1},
            "ev_trace_break_phase_counts": {"EV_NEVER_VISIBLE": 2},
            "candidate_trace_confidence_diagnostics": {
                "ev_visibility_attempted_count": 0,
                "ev_visibility_confirmed_count": 0,
            },
            "risk_layer_trace_readiness": 0.0,
            "pre_risk_block_cause_counts": {"ORDERBOOK_NOT_READY": 1, "CUTOFF_OR_TIME_BLOCK": 1},
            "model_attempt_gate_counts": {"ORDERBOOK_GATE": 1},
            "microstructure_related_pre_risk_block_share": 0.5,
            "timing_related_pre_risk_block_share": 0.5,
            "dominant_model_state_gap": "MODEL_NOT_ATTEMPTED",
            "ev_risk_chain_gap_diagnostics": {
                "classification": "EV_AND_RISK_CHAIN_NOT_VISIBLE",
                "ev_never_visible_count": 2,
                "risk_layer_trace_readiness": 0.0,
                "likely_gap_types": ["field_not_emitted", "producer_handoff_gap"],
                "explanation": "test diagnostic",
            },
        },
    )

    summary = compact_run_summary.build_compact_run_summary(
        date=DATE,
        base_dir=base_dir,
        report_dir=report_dir,
    )
    path = compact_run_summary.write_compact_run_summary(summary, report_dir=report_dir)

    assert path == report_dir / f"compact_run_summary_{DATE}.json"
    assert summary["scope"] == "offline_compact_observability_only"
    assert summary["run_id"] == "run-a"
    assert summary["paper_activity"]["orders"] == 1
    assert summary["ev_visibility"]["EV_NEVER_VISIBLE"] == 2
    assert summary["risk_layer_trace_readiness"] == 0.0
    assert summary["event_id_vs_chain_status"]["status"] == "EVENT_AND_CHAIN_HAVE_STRONG_IDENTITY"
    assert summary["missing_fields_by_producer"]["risk_log"]["top_missing_fields"]["candidate_trace_id"] == 1
    assert summary["missing_fields_by_producer"]["decision_log"]["alias_field_hits"]["candidate_id<-candidate_trace_id"] == 2
    assert "decision_id" not in summary["missing_fields_by_producer"]["execution_log"]["top_missing_fields"]
    assert "true_probability" not in summary["missing_fields_by_producer"]["execution_log"]["top_missing_fields"]
    assert "fair_value" not in summary["missing_fields_by_producer"]["execution_log"]["top_missing_fields"]
    assert "risk_state" not in summary["missing_fields_by_producer"]["execution_log"]["top_missing_fields"]
    assert summary["ev_risk_chain_gap_diagnostics"]["classification"] == "EV_AND_RISK_CHAIN_NOT_VISIBLE"
    assert summary["model_activation_diagnostics"]["dominant_model_activation_block_group"] == "ORDERBOOK_GATE"
    assert summary["model_activation_diagnostics"]["model_activation_state_counts"]["BLOCKED_BEFORE_MODEL"] == 2
    assert summary["model_activation_diagnostics"]["seconds_remaining_range"] == {"min": 25, "max": 220}
    assert summary["model_handoff_diagnostics"]["probability_model_call_counts"] == {"not_called": 4, "called": 1}
    assert summary["model_handoff_diagnostics"]["probability_model_output_visibility_counts"] == {"not_visible": 4, "visible": 1}
    assert summary["model_handoff_diagnostics"]["model_handoff_stage_counts"]["PRE_MODEL_GATE"] == 2
    assert summary["model_handoff_diagnostics"]["model_handoff_stage_counts"]["MODEL_OUTPUT_SERIALIZED"] == 1
    assert summary["model_handoff_diagnostics"]["pre_model_gate_counts"]["ORDERBOOK_COMPLETENESS_GATE"] == 1
    assert summary["model_handoff_diagnostics"]["pre_model_gate_counts"]["TIME_CUTOFF_GATE"] == 1
    assert summary["model_handoff_diagnostics"]["pre_model_gate_group_counts"]["ORDERBOOK_GATE"] == 1
    assert summary["model_handoff_diagnostics"]["candidate_ready_pre_model_gate_counts"]["TIME_CUTOFF_GATE"] == 1
    assert summary["model_handoff_diagnostics"]["candidate_ready_model_not_called_count"] == 1
    assert summary["model_handoff_diagnostics"]["model_output_source_counts"]["parent_decision_context"] == 1
    assert summary["decision_cycle_orderbook_readiness_audit"]["decision_candidate_event_count"] == 2
    assert summary["decision_cycle_orderbook_readiness_audit"]["current_cycle_orderbook_ready_count"] == 0
    assert summary["decision_cycle_orderbook_readiness_audit"]["candidate_ready_without_current_orderbook_count"] == 1
    assert summary["decision_cycle_orderbook_readiness_audit"]["orderbook_fetch_result_counts"]["orderbook_not_ready"] == 1
    assert summary["decision_cycle_orderbook_readiness_audit"]["token_pair_presence_counts"]["token_id_only"] == 2
    assert summary["decision_cycle_orderbook_readiness_audit"]["orderbook_fetch_result_origin_counts"]["pre_model_orderbook_gate_classification"] == 1
    assert summary["decision_cycle_orderbook_readiness_audit"]["orderbook_fetch_result_origin_counts"]["no_fetch_result_fields"] == 1
    assert summary["decision_cycle_orderbook_readiness_audit"]["dominant_decision_cycle_orderbook_blocker"] == "CURRENT_CYCLE_ORDERBOOK_NOT_COMPLETE"
    assert summary["orderbook_freshness_reuse_diagnostics"]["decision_event_count"] == 2
    assert summary["candidate_timing_diagnostics"]["events_with_timing_fields"] == 2
    assert summary["candidate_timing_diagnostics"]["candidate_relevant_events"] == 4
    assert summary["candidate_timing_diagnostics"]["lifecycle_transition_timing"]["active_inventory_trading_start_second"] == 35
    assert summary["candidate_timing_diagnostics"]["lifecycle_transition_timing"]["final_derisk_start_second"] == 270
    assert summary["candidate_timing_diagnostics"]["lifecycle_transition_timing"]["active_phase_duration_seconds"] == 205
    assert summary["candidate_timing_diagnostics"]["lifecycle_transition_timing"]["active_to_final_derisk_elapsed_seconds"] == 235
    assert summary["candidate_timing_diagnostics"]["candidate_ready_phase_counts"]["PROFIT_MANAGEMENT"] == 1
    assert summary["candidate_timing_diagnostics"]["candidate_ready_to_final_derisk_seconds_range"] == {"min": 20, "max": 20, "avg": 20.0}
    assert summary["candidate_timing_diagnostics"]["lifecycle_transition_summary"]["final_derisk_event_count"] == 1
    assert summary["candidate_timing_diagnostics"]["lifecycle_transition_summary"]["candidate_ready_before_final_derisk_count"] == 1
    assert summary["candidate_timing_diagnostics"]["lifecycle_transition_summary"]["final_derisk_before_model_eligible_count"] == 1
    assert summary["candidate_timing_diagnostics"]["lifecycle_transition_summary"]["final_derisk_before_model_output_count"] == 1
    assert summary["candidate_timing_diagnostics"]["lifecycle_transition_summary"]["model_eligibility_window_status"] == "CANDIDATE_READY_BUT_MODEL_NEVER_ELIGIBLE"
    assert summary["candidate_timing_diagnostics"]["first_seen_second_range"] == {"min": 40, "max": 40, "avg": 40.0}
    assert summary["candidate_timing_diagnostics"]["first_orderbook_ready_second_range"] == {"min": 80, "max": 80, "avg": 80.0}
    assert summary["candidate_timing_diagnostics"]["lifecycle_unknown_reason_counts"] == {
        "NON_CANDIDATE_TELEMETRY": 1,
        "MISSING_TIMING_AND_LIFECYCLE_FIELDS": 1,
    }
    assert summary["candidate_timing_diagnostics"]["dominant_timing_bottleneck"] == "ORDERBOOK_READINESS_BEFORE_MODEL"
    assert summary["model_output_propagation"]["execution_log"]["canonical_present"]["true_probability"] == 1
    assert summary["model_output_propagation"]["execution_log"]["canonical_present"]["fair_value"] == 1
    assert summary["model_output_propagation"]["decision_log"]["alias_present"]["ev_after_spread<-ev"] == 1
    assert summary["model_output_propagation"]["risk_log"]["missing"]["true_probability"] == 1
    assert summary["identity_continuity_diagnostics"]["orphan_risk_count"] == 1
    assert summary["identity_continuity_diagnostics"]["decision_to_risk_identity_gap_count"] == 2
    assert summary["identity_continuity_diagnostics"]["risk_to_execution_identity_gap_count"] == 0
    assert summary["identity_continuity_diagnostics"]["deterministic_chain_rate"] == 0.0
    assert summary["orphan_risk_count"] == 1
    assert summary["decision_to_risk_identity_gap_count"] == 2
    assert summary["deterministic_chain_rate"] == 0.0
    assert summary["root_cause_candidate"] == "EV_AND_RISK_CHAIN_NOT_VISIBLE"
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["recommended_next_codex_patch_target"].startswith("offline replay continuity")


def test_model_handoff_excludes_producer_observations_from_pre_model_gate_counts() -> None:
    diagnostics = compact_run_summary._model_handoff_diagnostics(
        [
            {
                "_category": "market_snapshots",
                "payload": {
                    "producer_event_type": "market_snapshots",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "first_candidate_ready_second": 50,
                    "probability_model_called": False,
                    "probability_model_output_visible": False,
                    "model_handoff_stage": "MODEL_OUTPUT_NOT_VISIBLE",
                    "pre_model_gate_name": "PRODUCER_PRE_MODEL_OBSERVATION",
                    "pre_model_gate_group": "PRODUCER_NOT_RESPONSIBLE",
                    "probability_model_call_path": "producer_not_responsible_pre_model_observation",
                },
            },
            {
                "_category": "decision_log",
                "payload": {
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "first_candidate_ready_second": 60,
                    "probability_model_called": False,
                    "probability_model_output_visible": False,
                    "model_handoff_stage": "PRE_MODEL_GATE",
                    "pre_model_gate_name": "ENTRY_FREQUENCY_GATE",
                    "pre_model_gate_group": "ENTRY_FREQUENCY_GATE",
                    "probability_model_call_path": "blocked_before_probability_model",
                },
            },
        ]
    )

    assert diagnostics["producer_pre_model_observation_counts"] == {"market_snapshots": 1}
    assert diagnostics["pre_model_gate_counts"] == {"ENTRY_FREQUENCY_GATE": 1}
    assert diagnostics["probability_model_call_counts"] == {"not_called": 2}
    assert diagnostics["runtime_return_path_probability_model_call_counts"] == {"not_called": 1}
    assert diagnostics["candidate_ready_pre_model_gate_counts"] == {"ENTRY_FREQUENCY_GATE": 1}
    assert diagnostics["active_candidate_ready_pre_model_gate_counts"] == {"ENTRY_FREQUENCY_GATE": 1}
    assert diagnostics["candidate_ready_model_not_called_count"] == 2
    assert diagnostics["candidate_ready_runtime_return_model_not_called_count"] == 1
    assert diagnostics["active_candidate_ready_runtime_return_model_not_called_count"] == 1


def test_decision_runtime_funnel_filters_passive_producers_and_counts_stage_survivors() -> None:
    funnel = compact_run_summary._decision_runtime_eligibility_funnel(
        [
            {
                "_category": "market_snapshots",
                "payload": {
                    "candidate_trace_id": "snapshot-trace",
                    "probability_model_called": False,
                    "pre_model_gate_name": "PRODUCER_PRE_MODEL_OBSERVATION",
                    "pre_model_gate_group": "PRODUCER_NOT_RESPONSIBLE",
                    "orderbook_state_classification": "ready",
                },
            },
            {
                "_category": "system_health",
                "payload": {"jsonl_status": "OK"},
            },
            {
                "_category": "execution_log",
                "payload": {
                    "candidate_trace_id": "execution-trace",
                    "probability_model_called": True,
                    "probability_model_output_visible": True,
                },
            },
            {
                "_category": "decision_log",
                "payload": {
                    "candidate_trace_id": "blocked-orderbook",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "orderbook_state_classification": "unavailable",
                    "pre_model_gate_name": "ORDERBOOK_COMPLETENESS_GATE",
                    "pre_model_gate_group": "ORDERBOOK_GATE",
                    "model_activation_block_reason": "unavailable",
                    "probability_model_called": False,
                    "probability_model_output_visible": False,
                },
            },
            {
                "_category": "decision_log",
                "payload": {
                    "candidate_trace_id": "blocked-cutoff",
                    "lifecycle_phase": "FINAL_DERISK",
                    "orderbook_state_classification": "ready",
                    "first_candidate_ready_second": 275,
                    "pre_model_gate_name": "TIME_CUTOFF_GATE",
                    "pre_model_gate_group": "TIME_CUTOFF_GATE",
                    "model_activation_block_reason": "hard_close_zone",
                    "model_attempt_eligible": False,
                    "probability_model_called": False,
                    "probability_model_output_visible": False,
                },
            },
            {
                "_category": "decision_log",
                "payload": {
                    "candidate_trace_id": "model-visible",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "orderbook_state_classification": "ready",
                    "first_candidate_ready_second": 60,
                    "model_attempt_eligible": True,
                    "probability_model_called": True,
                    "probability_model_output_visible": True,
                    "true_probability": 0.61,
                    "fair_value": 0.61,
                    "ev_after_spread": 0.03,
                },
            },
        ]
    )

    assert funnel["decision_candidate_event_count"] == 3
    assert funnel["excluded_producer_counts"] == {
        "market_snapshots": 1,
        "system_health": 1,
        "execution_log": 1,
    }
    assert funnel["stages"]["candidate_seen"]["survivor_count"] == 3
    assert funnel["stages"]["orderbook_ready"]["survivor_count"] == 2
    assert funnel["stages"]["orderbook_ready"]["independent_observed_count"] == 2
    assert funnel["stages"]["orderbook_ready"]["dominant_blocker"] == "ORDERBOOK_COMPLETENESS_GATE"
    assert funnel["stages"]["candidate_ready"]["survivor_count"] == 2
    assert funnel["stages"]["candidate_ready"]["independent_observed_count"] == 2
    assert funnel["stages"]["current_cycle_model_eligible"]["survivor_count"] == 1
    assert funnel["stages"]["current_cycle_model_eligible"]["independent_observed_count"] == 1
    assert funnel["stages"]["current_cycle_model_eligible"]["dominant_blocker"] == "TIME_CUTOFF_GATE"
    assert funnel["stages"]["probability_model_called"]["survivor_count"] == 1
    assert funnel["stages"]["model_output_visible"]["survivor_count"] == 1
    assert funnel["stages"]["fair_value_visible"]["survivor_count"] == 1
    assert funnel["stages"]["EV_visible"]["survivor_count"] == 1
    assert funnel["probability_model_path_reachable_after_filtering"] is True


def test_decision_cycle_orderbook_audit_distinguishes_lifecycle_ready_from_current_book_ready() -> None:
    audit = compact_run_summary._decision_cycle_orderbook_readiness_audit(
        [
            {
                "_category": "market_snapshots",
                "payload": {
                    "candidate_trace_id": "snapshot-trace",
                    "orderbook_state_classification": "ready",
                    "pre_model_gate_name": "PRODUCER_PRE_MODEL_OBSERVATION",
                    "pre_model_gate_group": "PRODUCER_NOT_RESPONSIBLE",
                },
            },
            {
                "_category": "decision_log",
                "payload": {
                    "candidate_trace_id": "warmup",
                    "token_id": "yes-token",
                    "yes_token_id": "yes-token",
                    "no_token_id": "no-token",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "first_candidate_ready_second": 50,
                    "orderbook_readiness_reason": "warmup_pending",
                    "orderbook_state_classification": "warmup_pending",
                    "pre_model_gate_name": "ORDERBOOK_COMPLETENESS_GATE",
                    "pre_model_gate_group": "ORDERBOOK_GATE",
                    "model_activation_block_reason": "warmup_pending",
                },
            },
            {
                "_category": "decision_log",
                "payload": {
                    "candidate_trace_id": "ready",
                    "token_id": "yes-token",
                    "yes_token_id": "yes-token",
                    "no_token_id": "no-token",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "first_candidate_ready_second": 60,
                    "orderbook_state_classification": "ready",
                    "yes_ask": 0.51,
                    "no_ask": 0.50,
                    "spread": 0.01,
                    "spread_limit": 0.06,
                },
            },
        ]
    )

    assert audit["decision_candidate_event_count"] == 2
    assert audit["current_cycle_orderbook_ready_count"] == 1
    assert audit["lifecycle_candidate_ready_count"] == 2
    assert audit["candidate_ready_without_current_orderbook_count"] == 1
    assert audit["token_mapping_status_counts"]["token_fields_present"] == 2
    assert audit["token_pair_presence_counts"]["yes_no_pair_present"] == 2
    assert audit["orderbook_fetch_attempt_visibility_counts"]["visible"] == 2
    assert audit["orderbook_fetch_result_origin_counts"]["local_readiness_classification"] == 1
    assert audit["orderbook_fetch_result_origin_counts"]["explicit_price_fields"] == 1
    assert audit["orderbook_fetch_result_counts"]["warmup_pending"] == 1
    assert audit["orderbook_fetch_result_counts"]["ready"] == 1
    assert audit["ask_presence_counts"]["yes_ask_positive"] == 1
    assert audit["ask_presence_counts"]["no_ask_positive"] == 1
    assert audit["empty_book_recovery_visibility_counts"]["not_attempted_or_not_serialized"] == 2
    assert audit["blocker_counts"]["CURRENT_CYCLE_ORDERBOOK_NOT_COMPLETE"] == 1


def test_global_vs_decision_orderbook_sync_audit_explains_ready_mismatch() -> None:
    audit = compact_run_summary._global_vs_decision_orderbook_sync_audit(
        [
            {
                "_category": "market_snapshots",
                "timestamp_utc": "2026-05-12T01:00:00Z",
                "payload": {
                    "condition_id": "condition-btc",
                    "market_slug": "btc-updown-5m",
                    "orderbook_state_classification": "ready",
                    "yes_ask": 0.51,
                    "no_ask": 0.50,
                },
            },
            {
                "_category": "decision_log",
                "timestamp_utc": "2026-05-12T01:00:02Z",
                "payload": {
                    "candidate_trace_id": "candidate-1",
                    "condition_id": "condition-btc",
                    "market_slug": "btc-updown-5m",
                    "token_id": "yes-token",
                    "yes_token_id": "yes-token",
                    "no_token_id": "no-token",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "first_candidate_ready_second": 45,
                    "first_tradable_at": "2026-05-12T01:00:01Z",
                    "token_ready_at": "2026-05-12T00:59:59.500Z",
                    "orderbook_ready_at": "2026-05-12T01:00:00Z",
                    "decision_timestamp": "2026-05-12T01:00:02Z",
                    "orderbook_state_classification": "empty_book",
                    "orderbook_readiness_reason": "empty_book",
                    "pre_model_gate_name": "ORDERBOOK_COMPLETENESS_GATE",
                    "pre_model_gate_group": "ORDERBOOK_GATE",
                },
            },
            {
                "_category": "decision_log",
                "timestamp_utc": "2026-05-12T01:00:05Z",
                "payload": {
                    "candidate_trace_id": "candidate-2",
                    "condition_id": "condition-eth",
                    "market_slug": "eth-updown-5m",
                    "token_id": "eth-yes-token",
                    "yes_token_id": "eth-yes-token",
                    "no_token_id": "eth-no-token",
                    "skip_reason": "warmup_pending",
                    "orderbook_state_classification": "warmup_pending",
                    "pre_model_gate_name": "ORDERBOOK_COMPLETENESS_GATE",
                },
            },
            {
                "_category": "market_snapshots",
                "timestamp_utc": "2026-05-12T01:00:00Z",
                "payload": {
                    "condition_id": "condition-eth",
                    "market_slug": "eth-updown-5m",
                    "orderbook_state_classification": "ready",
                    "yes_ask": 0.52,
                    "no_ask": 0.49,
                },
            },
            {
                "_category": "decision_log",
                "timestamp_utc": "2026-05-12T01:00:12Z",
                "payload": {
                    "candidate_trace_id": "candidate-3",
                    "condition_id": "condition-eth",
                    "market_slug": "eth-updown-5m",
                    "token_id": "eth-yes-token",
                    "yes_token_id": "eth-yes-token",
                    "no_token_id": "eth-no-token",
                    "lifecycle_phase": "FINAL_DERISK",
                    "skip_reason": "hard_close_zone",
                    "orderbook_state_classification": "unavailable",
                    "orderbook_readiness_reason": "hard_close_zone",
                    "pre_model_gate_name": "ORDERBOOK_COMPLETENESS_GATE",
                    "pre_model_gate_group": "ORDERBOOK_GATE",
                },
            },
        ]
    )

    assert audit["global_ready_event_count"] == 2
    assert audit["ready_by_producer"]["market_snapshots"] == 2
    assert audit["decision_event_count"] == 3
    assert audit["decision_ready_event_count"] == 0
    assert audit["same_market_global_ready_before_decision_count"] == 2
    assert audit["fresh_global_ready_before_decision_count"] == 1
    assert audit["global_ready_before_decision_but_local_incomplete_count"] == 2
    assert audit["decision_without_prior_global_ready_count"] == 1
    assert audit["global_to_decision_delay_ms_range"] == {"min": 2000, "max": 12000, "avg": 7000.0}
    assert audit["global_to_decision_latency_bucket_counts"] == {"<=3s": 1, ">10s": 1}
    assert audit["median_executable_window_age_ms"] == 7000.0
    assert audit["executable_liquidity_decay_distribution"]["within_3s_count"] == 1
    assert audit["executable_liquidity_decay_distribution"]["within_5s_count"] == 1
    assert audit["executable_liquidity_decay_distribution"]["over_10s_count"] == 1
    assert audit["local_decay_after_global_ready_counts"]["global_ready_but_local_empty"] == 1
    assert audit["local_decay_after_global_ready_counts"]["global_ready_but_cutoff_reached"] == 1
    assert audit["lifecycle_latency_bucket_counts"]["ACTIVE_INVENTORY_TRADING"]["<=3s"] == 1
    assert audit["lifecycle_latency_bucket_counts"]["FINAL_DERISK"][">10s"] == 1
    assert audit["active_decisions_after_global_ready_count"] == 1
    assert audit["active_decisions_exceeding_5s_count"] == 0
    assert audit["active_inventory_trading_arrival_status"] == "ACTIVE_DECISIONS_MOSTLY_WITHIN_5S_WINDOW"
    assert audit["final_derisk_freshness_loss_count"] == 1
    assert audit["executable_books_disappeared_before_decision_count"] == 2
    pipeline = audit["latency_pipeline_decomposition"]
    assert pipeline["stage_latency_stats_ms"]["market_snapshot_received_to_decision_serialized"]["median_ms"] == 7000.0
    assert pipeline["stage_latency_stats_ms"]["market_snapshot_received_to_decision_serialized"]["p95_ms"] == 12000
    assert pipeline["stage_latency_stats_ms"]["token_mapping_ready_to_orderbook_fetch_complete"]["median_ms"] == 500
    assert pipeline["stage_latency_stats_ms"]["orderbook_fetch_complete_to_candidate_ready"]["median_ms"] == 1000
    assert pipeline["stage_latency_stats_ms"]["candidate_ready_to_decision_event_created"]["median_ms"] == 1000
    assert pipeline["stage_latency_stats_ms"]["decision_event_created_to_decision_serialized"]["median_ms"] == 0
    assert pipeline["dominant_slow_stage"] == "orderbook_fetch_complete_to_candidate_ready"
    assert pipeline["freshness_loss_by_stage_counts"]["market_snapshot_received_to_decision_serialized"] == 1
    assert pipeline["freshness_loss_by_stage_counts"]["candidate_ready_to_decision_event_created"] == 1
    assert pipeline["latency_attribution_counts"]["latency_caused_by_serialization_gap"] == 1
    assert pipeline["latency_attribution_counts"]["latency_caused_by_lifecycle_timing"] == 1
    assert audit["ask_synchronization_counts"]["market_snapshots:yes_no_asks_positive"] == 2
    assert audit["ask_synchronization_counts"]["decision_log:asks_not_positive_or_not_serialized"] == 3
    assert audit["synchronization_mismatch_classification"] == "GLOBAL_READY_DECISION_LOCAL_INCOMPLETE"


def test_latency_split_uses_latest_ready_to_avoid_sticky_first_ready_overstatement() -> None:
    audit = compact_run_summary._global_vs_decision_orderbook_sync_audit(
        [
            {
                "_category": "market_snapshots",
                "timestamp_utc": "2026-05-12T01:00:00Z",
                "run_id": "run-a",
                "payload": {
                    "condition_id": "condition-btc",
                    "market_slug": "btc-updown-5m",
                    "market_epoch_start": 1_746_999_600,
                    "orderbook_state_classification": "ready",
                    "yes_ask": 0.51,
                    "no_ask": 0.50,
                },
            },
            {
                "_category": "decision_log",
                "timestamp_utc": "2026-05-12T01:00:09Z",
                "run_id": "run-a",
                "payload": {
                    "candidate_trace_id": "candidate-prior",
                    "condition_id": "condition-btc",
                    "market_slug": "btc-updown-5m",
                    "market_epoch_start": 1_746_999_600,
                    "first_tradable_at": "2026-05-12T01:00:00Z",
                    "first_candidate_ready_second": 0,
                    "decision_timestamp": "2026-05-12T01:00:09Z",
                    "token_id": "yes-token",
                    "yes_token_id": "yes-token",
                    "no_token_id": "no-token",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "orderbook_state_classification": "empty_book",
                    "orderbook_readiness_reason": "empty_book",
                    "pre_model_gate_name": "ORDERBOOK_COMPLETENESS_GATE",
                },
            },
            {
                "_category": "decision_log",
                "timestamp_utc": "2026-05-12T01:00:10Z",
                "run_id": "run-a",
                "payload": {
                    "candidate_trace_id": "candidate-later",
                    "condition_id": "condition-btc",
                    "market_slug": "btc-updown-5m",
                    "market_epoch_start": 1_746_999_600,
                    "first_tradable_at": "2026-05-12T01:00:00Z",
                    "first_candidate_ready_second": 0,
                    "decision_timestamp": "2026-05-12T01:00:10Z",
                    "token_id": "yes-token",
                    "yes_token_id": "yes-token",
                    "no_token_id": "no-token",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "orderbook_state_classification": "empty_book",
                    "orderbook_readiness_reason": "empty_book",
                    "pre_model_gate_name": "ORDERBOOK_COMPLETENESS_GATE",
                },
            },
        ]
    )

    split = audit["latency_pipeline_decomposition"]["timestamp_semantics_split"]
    assert split["first_candidate_ready_to_decision_event_created_ms"]["range_ms"] == {
        "min": 9000,
        "max": 10000,
        "avg": 9500.0,
    }
    assert split["latest_candidate_ready_to_decision_event_created_ms"]["range_ms"] == {
        "min": 1000,
        "max": 1000,
        "avg": 1000.0,
    }
    assert split["latest_candidate_ready_to_decision_event_created_ms"]["unobservable_count"] == 1
    assert split["same_run_last_global_ready_to_decision_event_created_ms"]["range_ms"] == {
        "min": 9000,
        "max": 10000,
        "avg": 9500.0,
    }
    assert "first-seen timestamp" in split["sticky_first_ready_warning"]


def test_orderbook_freshness_reuse_diagnostics_classifies_stale_reuse() -> None:
    diagnostics = compact_run_summary._orderbook_freshness_reuse_diagnostics(
        [
            {
                "_category": "decision_log",
                "timestamp_utc": "2026-05-12T01:00:00Z",
                "payload": {
                    "candidate_trace_id": "candidate-a",
                    "condition_id": "condition-btc",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "pre_model_gate_name": "ORDERBOOK_COMPLETENESS_GATE",
                    "orderbook_reuse_detected": True,
                    "orderbook_snapshot_age_ms_at_decision": 61000,
                    "executable_book_last_seen_age_ms": 61000,
                    "decision_cycle_interval_seconds": 1.0,
                    "orderbook_current_fetch_status": "fresh_fetch_failed",
                    "orderbook_stale_reuse_source": "CURRENT_FETCH_FAILED_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR",
                    "orderbook_lineage_match": True,
                    "last_orderbook_refresh_at": "2026-05-12T00:59:00Z",
                    "last_successful_yes_no_book_at": "2026-05-12T00:59:00Z",
                    "orderbook_refresh_source": "market_snapshot",
                    "orderbook_refresh_trigger": "snapshot_sampling",
                    "empty_book_recovery_attempted": True,
                    "empty_book_recovery_failed": True,
                    "recovery_branch_skipped_reason": "empty_book_retries_exhausted",
                },
            },
            {
                "_category": "decision_log",
                "timestamp_utc": "2026-05-12T01:00:01Z",
                "payload": {
                    "candidate_trace_id": "candidate-b",
                    "condition_id": "condition-btc",
                    "lifecycle_phase": "FINAL_DERISK",
                    "pre_model_gate_name": "ORDERBOOK_COMPLETENESS_GATE",
                    "orderbook_reuse_detected": False,
                    "orderbook_snapshot_age_ms_at_decision": 100,
                    "decision_cycle_interval_seconds": 1.0,
                    "orderbook_current_fetch_status": "fresh_fetch_executable",
                    "orderbook_stale_reuse_source": "CURRENT_DECISION_FETCH_EXECUTABLE",
                    "orderbook_lineage_match": True,
                    "last_orderbook_refresh_at": "2026-05-12T01:00:01Z",
                    "orderbook_refresh_source": "decision_cycle_fetch",
                    "orderbook_refresh_trigger": "candidate_evaluation",
                },
            },
        ]
    )

    assert diagnostics["decision_event_count"] == 2
    assert diagnostics["cadence_fields_observed_count"] == 2
    assert diagnostics["orderbook_reuse_detected_count"] == 1
    assert diagnostics["stale_orderbook_reuse_count"] == 1
    assert diagnostics["refresh_cadence_distribution"]["<=1s"] == 2
    assert diagnostics["orderbook_snapshot_age_at_decision_distribution"][">60s"] == 1
    assert diagnostics["executable_book_age_at_decision_distribution"][">60s"] == 1
    assert diagnostics["refresh_source_counts"]["market_snapshot"] == 1
    assert diagnostics["fresh_fetch_vs_cache_source_counts"]["fresh_fetch_failed"] == 1
    assert diagnostics["stale_reuse_source_classification_counts"]["CURRENT_FETCH_FAILED_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR"] == 1
    assert diagnostics["token_pair_lineage_counts"]["same_token_pair"] == 2
    assert diagnostics["reuse_by_lifecycle_phase"]["ACTIVE_INVENTORY_TRADING"] == 1
    assert diagnostics["polling_cycle_drift_diagnostics"]["refresh_age_exceeds_2x_decision_interval"] == 1
    assert diagnostics["empty_book_recovery_delay_diagnostics"]["recovery_failed"] == 1
    assert diagnostics["runtime_cadence_hypothesis"] == "FRESH_FETCH_FAILED_AFTER_PRIOR_READY_SAME_TOKEN_PAIR"


def test_scheduler_cadence_diagnostics_splits_interval_recovery_and_sequence() -> None:
    diagnostics = compact_run_summary._scheduler_cadence_diagnostics(
        [
            {
                "_category": "decision_log",
                "timestamp_utc": "2026-05-12T01:00:00Z",
                "payload": {
                    "decision_id": "decision-a",
                    "decision_cycle_started_at": "2026-05-12T01:00:00Z",
                    "candidate_trace_id": "candidate-a",
                    "condition_id": "condition-btc",
                    "ticker": "BTC",
                    "scheduler_cadence_source": "run_single_cycle_market_loop",
                    "hot_path_timing_source": "runtime_market_evaluation",
                    "market_evaluation_asset": "BTC",
                    "market_evaluation_started_ms_since_cycle": 100,
                    "market_evaluation_duration_ms": 25,
                    "market_sequence_index": 1,
                    "market_sequence_count": 2,
                    "candidate_queue_age_ms": 20000,
                    "hot_path_admission_wait_ms": 20000,
                    "candidate_queue_ownership": "implicit_orderbook_refresh_cache",
                    "candidate_revisit_scheduling_source": "scheduled_run_single_cycle",
                    "hot_path_admission_trigger": "scheduled_decision_cycle",
                    "event_vs_polling_classification": "polling_revisit_driven",
                    "executable_liquidity_event_role": "passive_telemetry_only",
                    "market_snapshot_decision_pipeline_linkage": "disconnected_passive_snapshot_to_scheduled_decision",
                    "candidate_handoff_boundary": "display_snapshot_sampling->scheduled_run_single_cycle",
                    "empty_book_recovery_duration_ms": 300,
                    "decision_cycle_interval_seconds": 1.0,
                    "actual_market_revisit_frequency_seconds": 1.0,
                    "configured_decision_loop_interval_seconds": 1.0,
                    "intended_decision_loop_target_seconds": 1.0,
                    "effective_outer_loop_interval_seconds": 1.0,
                    "snapshot_sampling_interval_seconds": 5.0,
                    "market_discovery_interval_seconds": 15.0,
                },
            },
            {
                "_category": "decision_log",
                "timestamp_utc": "2026-05-12T01:00:00.100Z",
                "payload": {
                    "decision_id": "decision-b",
                    "decision_cycle_started_at": "2026-05-12T01:00:00Z",
                    "candidate_trace_id": "candidate-b",
                    "condition_id": "condition-eth",
                    "ticker": "ETH",
                    "scheduler_cadence_source": "run_single_cycle_market_loop",
                    "hot_path_timing_source": "runtime_market_evaluation",
                    "market_evaluation_asset": "ETH",
                    "market_evaluation_started_ms_since_cycle": 150,
                    "market_evaluation_duration_ms": 35,
                    "market_sequence_index": 2,
                    "market_sequence_count": 2,
                    "candidate_queue_age_ms": 21000,
                    "hot_path_admission_wait_ms": 21000,
                    "candidate_queue_ownership": "implicit_orderbook_refresh_cache",
                    "candidate_revisit_scheduling_source": "scheduled_run_single_cycle",
                    "hot_path_admission_trigger": "scheduled_decision_cycle",
                    "event_vs_polling_classification": "polling_revisit_driven",
                    "executable_liquidity_event_role": "passive_telemetry_only",
                    "market_snapshot_decision_pipeline_linkage": "disconnected_passive_snapshot_to_scheduled_decision",
                    "candidate_handoff_boundary": "display_snapshot_sampling->scheduled_run_single_cycle",
                    "empty_book_recovery_duration_ms": 0,
                    "decision_cycle_interval_seconds": 1.0,
                    "actual_market_revisit_frequency_seconds": 1.0,
                    "configured_decision_loop_interval_seconds": 1.0,
                    "intended_decision_loop_target_seconds": 1.0,
                    "effective_outer_loop_interval_seconds": 1.0,
                    "snapshot_sampling_interval_seconds": 5.0,
                    "market_discovery_interval_seconds": 15.0,
                },
            },
        ]
    )

    assert diagnostics["decision_event_count"] == 2
    assert diagnostics["scheduler_timing_fields_observed_count"] == 2
    assert diagnostics["dominant_scheduler_bottleneck"] == "PASSIVE_EXECUTABLE_BOOK_WAITING_FOR_POLLING_HOT_PATH"
    assert diagnostics["market_evaluation_duration_ms_stats"]["median_ms"] == 30.0
    assert diagnostics["candidate_queue_age_ms_stats"]["median_ms"] == 20500.0
    assert diagnostics["hot_path_admission_wait_ms_stats"]["median_ms"] == 20500.0
    assert diagnostics["empty_book_recovery_duration_ms_stats"]["p95_ms"] == 300
    assert diagnostics["configured_decision_loop_interval_seconds_stats"]["median_seconds"] == 1.0
    assert diagnostics["effective_outer_loop_interval_seconds_stats"]["median_seconds"] == 1.0
    assert diagnostics["actual_market_revisit_frequency_seconds_stats"]["median_seconds"] == 1.0
    assert diagnostics["intended_architecture_cadence_seconds"] == {
        "decision_loop_target": 1,
        "snapshot_sampling_median": 5.0,
        "market_discovery_median": 15.0,
    }
    assert diagnostics["btc_eth_sequencing_duration_ms_stats"]["median_ms"] == 85
    assert diagnostics["market_sequence_index_counts"] == {"1": 1, "2": 1}
    assert diagnostics["root_candidate_flags"]["fast_decision_path_after_stale_prior_book"] is True
    assert diagnostics["root_candidate_flags"]["polling_centric_candidate_handoff"] is True
    assert diagnostics["root_candidate_flags"]["executable_liquidity_is_passive_telemetry"] is True
    assert diagnostics["root_candidate_flags"]["recovery_retry_timing_is_root_candidate"] is False
    assert diagnostics["root_candidate_flags"]["sequential_btc_eth_evaluation_contributes"] is False
    handoff = diagnostics["candidate_handoff_diagnostics"]
    assert handoff["dominant_candidate_aging_source"] == "PASSIVE_EXECUTABLE_LIQUIDITY_WAITING_FOR_SCHEDULED_DECISION_REVISIT"
    assert handoff["minimal_future_architecture_direction"] == "event_driven_executable_liquidity_hot_path_admission"
    assert handoff["event_vs_polling_classification_counts"]["polling_revisit_driven"] == 2
    assert handoff["executable_liquidity_event_role_counts"]["passive_telemetry_only"] == 2


def test_scheduler_cadence_diagnostics_flags_configured_interval_target_violation() -> None:
    diagnostics = compact_run_summary._scheduler_cadence_diagnostics(
        [
            {
                "_category": "decision_log",
                "timestamp_utc": "2026-05-12T01:00:00Z",
                "payload": {
                    "decision_id": "decision-a",
                    "candidate_trace_id": "candidate-a",
                    "condition_id": "condition-btc",
                    "scheduler_cadence_source": "run_single_cycle_market_loop",
                    "market_evaluation_duration_ms": 20,
                    "candidate_queue_age_ms": 20000,
                    "configured_decision_loop_interval_seconds": 60,
                    "intended_decision_loop_target_seconds": 1,
                    "effective_outer_loop_interval_seconds": 60,
                    "actual_market_revisit_frequency_seconds": 60,
                },
            }
        ]
    )

    assert diagnostics["dominant_scheduler_bottleneck"] == "CONFIGURED_DECISION_INTERVAL_EXCEEDS_TARGET"
    assert diagnostics["configured_decision_loop_interval_seconds_stats"]["median_seconds"] == 60
    assert diagnostics["effective_outer_loop_interval_seconds_stats"]["median_seconds"] == 60
    assert diagnostics["actual_market_revisit_frequency_seconds_stats"]["median_seconds"] == 60
    assert diagnostics["root_candidate_flags"]["configured_interval_violates_decision_target"] is True
    assert diagnostics["root_candidate_flags"]["effective_outer_loop_violates_decision_target"] is True
    assert diagnostics["root_candidate_flags"]["market_revisit_frequency_violates_decision_target"] is True


def test_compact_summary_applies_since_until_filter(tmp_path, monkeypatch) -> None:
    base_dir = tmp_path / "quant_data"
    report_dir = tmp_path / "reports"
    _write_event(
        base_dir,
        "decision_log",
        {
            "timestamp_utc": "2026-05-12T00:59:00Z",
            "run_id": "old-run",
            "payload": {"skip_reason": "outside"},
        },
    )
    _write_event(
        base_dir,
        "decision_log",
        {
            "timestamp_utc": "2026-05-12T01:05:00Z",
            "run_id": "filtered-run",
            "payload": {"candidate_trace_id": "trace-2", "condition_id": "cond-2"},
        },
    )
    monkeypatch.setattr(compact_run_summary, "analyze_replay", lambda **_: _report({"top_skip_reasons": []}))
    monkeypatch.setattr(compact_run_summary, "evaluate_session_runtime", lambda **_: _report({}))
    monkeypatch.setattr(
        compact_run_summary,
        "build_ev_field_coverage_report",
        lambda **_: {
            "candidate_trace_confidence_counts": {},
            "ev_trace_break_phase_counts": {},
            "candidate_trace_confidence_diagnostics": {},
            "risk_layer_trace_readiness": 0.0,
        },
    )

    summary = compact_run_summary.build_compact_run_summary(
        date=DATE,
        since="01:00",
        until="01:10",
        base_dir=base_dir,
        report_dir=report_dir,
    )

    assert summary["run_id"] == "filtered-run"
    assert summary["time_range"]["events_loaded"] == 1
    assert summary["time_range"]["first_event_utc"] == "2026-05-12T01:05:00Z"
    assert summary["source_inputs"]["bad_json_lines"] == 0
