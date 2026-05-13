import json
from pathlib import Path

from tools.ev_field_coverage import (
    build_ev_field_coverage_report,
    main,
    write_ev_field_coverage_report,
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
    event_type: str = "market_snapshot",
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


def test_ev_field_coverage_treats_model_probability_aliases_as_visible_outputs(tmp_path):
    base_dir = tmp_path / "quant_data"
    _write_jsonl(
        base_dir,
        "decision_log",
        [
            _event(
                "2026-05-08T12:00:00Z",
                {
                    "candidate_trace_id": "trace-model-visible",
                    "candidate_id": "candidate-model-visible",
                    "signal_id": "signal-model-visible",
                    "market_id": "condition-model-visible",
                    "condition_id": "condition-model-visible",
                    "token_id": "token-model-visible",
                    "side": "SKIP",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "model_probability_yes": 0.57,
                    "model_probability_no": 0.43,
                    "fair_value_yes": 0.57,
                    "fair_value_no": 0.43,
                    "market_price": 0.55,
                    "ev": -0.01,
                    "model_attempted": True,
                    "probability_model_stage": "probability_model_output",
                    "probability_model_gate_reason": "model_output_visible",
                },
                event_type="decision_snapshot",
            )
        ],
    )

    report = build_ev_field_coverage_report(base_dir=base_dir, date=DATE, run_id="run-target")
    row = report["candidate_ev_coverage"][0]

    assert row["ev_trace_break_phase"] != "EV_NEVER_VISIBLE"
    assert row["ev_visibility_confirmed"] is True
    assert row["field_continuity"]["true_probability"]["available_events"] == 1
    assert row["field_continuity"]["fair_value"]["available_events"] == 1
    assert row["field_continuity"]["ev_after_spread"]["available_events"] == 1


def test_ev_field_coverage_uses_runtime_model_activation_gate_fields(tmp_path):
    base_dir = tmp_path / "quant_data"
    _write_jsonl(
        base_dir,
        "decision_log",
        [
            _event(
                "2026-05-08T12:00:00Z",
                {
                    "candidate_trace_id": "trace-cutoff",
                    "candidate_id": "candidate-cutoff",
                    "signal_id": "signal-cutoff",
                    "market_id": "condition-cutoff",
                    "condition_id": "condition-cutoff",
                    "token_id": "token-cutoff",
                    "side": "YES",
                    "lifecycle_phase": "FINAL_DERISK",
                    "fair_value_available": False,
                    "market_price_available": False,
                    "true_probability_available": False,
                    "ev_after_spread_available": False,
                    "probability_model_stage": "pre_model_skip",
                    "model_activation_state": "BLOCKED_BEFORE_MODEL",
                    "model_activation_block_group": "TIME_CUTOFF_GATE",
                    "model_activation_block_reason": "hard_close_zone",
                },
                event_type="decision_snapshot",
            )
        ],
    )

    report = build_ev_field_coverage_report(base_dir=base_dir, date=DATE, run_id="run-target")

    assert report["model_state_gap_counts"]["BLOCKED_BEFORE_MODEL"] == 1
    assert report["model_attempt_gate_counts"]["TIME_CUTOFF_GATE"] == 1
    assert report["dominant_model_attempt_gate"] == "TIME_CUTOFF_GATE"
    row = report["candidate_ev_coverage"][0]
    assert row["model_attempt_gate_report"]["model_attempt_gates"] == ["TIME_CUTOFF_GATE", "LIFECYCLE_PHASE_GATE"]
    assert row["compact_events"][0]["model_activation_block_group"] == "TIME_CUTOFF_GATE"


def test_ev_field_coverage_detects_component_dropout(tmp_path):
    base_dir = tmp_path / "quant_data"
    _write_jsonl(
        base_dir,
        "market_snapshots",
        [
            _event(
                "2026-05-08T12:00:00Z",
                {
                    "candidate_id": "candidate-a",
                    "signal_id": "signal-a",
                    "market_id": "btc-market",
                    "lifecycle_phase": "OPENING_SCAN",
                    "fair_value": 0.60,
                    "fair_value_available": True,
                    "market_price": 0.56,
                    "market_price_available": True,
                    "true_probability": 0.60,
                    "true_probability_available": True,
                    "ev_after_spread": 0.02,
                    "ev_after_spread_available": True,
                },
            ),
            _event(
                "2026-05-08T12:00:10Z",
                {
                    "candidate_id": "candidate-a",
                    "signal_id": "signal-a",
                    "market_id": "btc-market",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "fair_value": 0.63,
                    "fair_value_available": True,
                    "market_price": 0.57,
                    "market_price_available": True,
                    "true_probability": 0.63,
                    "true_probability_available": True,
                    "ev_after_spread": 0.04,
                    "ev_after_spread_available": True,
                },
            ),
            _event(
                "2026-05-08T12:00:20Z",
                {
                    "candidate_id": "candidate-a",
                    "signal_id": "signal-a",
                    "market_id": "btc-market",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "fair_value_available": False,
                    "fair_value_null_reason": "no_probability_model_output",
                    "market_price": 0.58,
                    "market_price_available": True,
                    "true_probability_available": False,
                    "true_probability_null_reason": "no_probability_model_output",
                    "ev_after_spread_available": False,
                    "ev_after_spread_null_reason": "candidate_blocked_before_ev",
                    "candidate_block_stage": "pre_ev",
                    "candidate_block_reason": "no_probability_model_output",
                    "candidate_survival_ms": 20000,
                    "candidate_expiry_reason": "blocked",
                },
            ),
        ],
    )

    report = build_ev_field_coverage_report(base_dir=base_dir, date=DATE, run_id="run-target")

    assert report["scope"] == "offline_research_replay_only"
    assert report["schema_version"] == "ev_field_coverage_v1"
    assert report["schema_generation_version"] == "ev_field_coverage_post_fallback_condition_coverage_verification_v1"
    assert report["replay_schema_freshness"] == "fresh"
    assert report["stale_schema_detected"] is False
    assert report["does_not_claim_profitability"] is True
    assert report["does_not_authorize_runtime_decisions"] is True
    assert report["does_not_infer_execution"] is True
    assert report["does_not_claim_mfe_mae"] is True
    assert report["summary"]["candidate_ev_coverage_rows"] == 1

    row = report["candidate_ev_coverage"][0]
    assert row["candidate_ev_visibility_state"] == "EV_FIELD_DROPOUT"
    assert row["ev_observability_quality"] == "PARTIAL_EV_COMPONENTS"
    assert row["ev_field_continuity_rate"] == 0.75
    assert row["ev_visibility_duration_ms"] == 20000
    assert row["field_continuity"]["fair_value"]["continuity_rate"] == 0.6667
    assert row["field_continuity"]["market_price"]["continuity_rate"] == 1.0
    assert row["field_dropout_reasons"]["fair_value"] == "no_probability_model_output"
    assert row["field_dropout_reasons"]["ev_after_spread"] == "candidate_blocked_before_ev"
    assert row["sparse_ev_path_reason"].startswith("field_dropout:")
    assert report["dominant_ev_blind_causes"]["null_reasons"]["no_probability_model_output"] == 2
    assert report["candidate_identity_upgrade_requirements_schema"]["version"] == "candidate_identity_upgrade_requirements_v1"
    assert "candidate_trace_id" in report["identity_confidence_requirements"]["DIRECT"]
    assert "market_key" in report["identity_confidence_requirements"]["STRONG"]
    assert report["missing_fields_preventing_direct_identity"]["candidate_trace_id"] == 1
    assert report["missing_fields_preventing_strong_identity"]["condition_id"] == 1
    assert report["highest_impact_identity_field"]["field"] in {"candidate_trace_id", "condition_id", "token_id", "side", "parent_candidate_trace_id"}
    assert sum(report["candidate_identity_upgrade_path_counts"].values()) == 1
    assert next(iter(report["candidate_identity_upgrade_path_counts"])) in {
        "ACTUAL_DIRECT_CANONICAL_FIELDS_MISSING",
        "ACTUAL_STRONG_CANONICAL_FIELDS_MISSING",
    }
    assert report["post_emission_data_status"] == "POST_EMISSION_DATA_NOT_FOUND"
    assert report["post_normalization_data_status"] == "POST_NORMALIZATION_DATA_NOT_FOUND"
    assert report["post_condition_enrichment_data_status"] == "POST_CONDITION_ENRICHMENT_DATA_NOT_FOUND"
    assert report["post_fallback_data_status"] == "POST_FALLBACK_DATA_NOT_FOUND"
    assert report["candidate_trace_id_present_count"] == 0
    assert report["traced_events_with_condition_id_after_enrichment"] == 0
    assert report["traced_events_with_condition_id"] == 0


def test_ev_field_coverage_labels_never_visible_candidates(tmp_path):
    base_dir = tmp_path / "quant_data"
    _write_jsonl(
        base_dir,
        "market_snapshots",
        [
            _event(
                "2026-05-08T12:00:00Z",
                {
                    "candidate_id": "candidate-blind",
                    "signal_id": "signal-blind",
                    "market_id": "eth-market",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "fair_value_available": False,
                    "fair_value_null_reason": "no_probability_model_output",
                    "market_price_available": False,
                    "market_price_null_reason": "no_market_price",
                    "true_probability_available": False,
                    "true_probability_null_reason": "no_probability_model_output",
                    "ev_after_spread_available": False,
                    "ev_after_spread_null_reason": "candidate_blocked_before_ev",
                    "candidate_block_stage": "pre_ev",
                    "candidate_block_reason": "no_probability_model_output",
                    "market_readiness_state": "spread_not_ready",
                    "orderbook_state_classification": "empty_book",
                    "candidate_expiry_reason": "blocked",
                },
                asset="ETH",
            ),
        ],
    )

    report = build_ev_field_coverage_report(base_dir=base_dir, date=DATE, run_id="run-target")
    row = report["candidate_ev_coverage"][0]

    assert row["candidate_ev_visibility_state"] == "EV_NEVER_VISIBLE"
    assert row["ev_observability_quality"] == "EV_BLIND"


def test_ev_field_coverage_detects_post_emission_trace_fields(tmp_path):
    base_dir = tmp_path / "quant_data"
    _write_jsonl(
        base_dir,
        "market_snapshots",
        [
            _event(
                "2026-05-08T12:00:00Z",
                {
                    "candidate_trace_id": "ct_market",
                    "parent_candidate_trace_id": "candidate-a",
                    "trace_link_reason": "passive_deterministic_existing_fields",
                    "market_key": "btc-market",
                    "condition_id": "condition-a",
                    "token_id": "token-a",
                    "side": "YES",
                    "lifecycle_phase": "OPENING_SCAN",
                    "candidate_id": "candidate-a",
                    "market_id": "btc-market",
                    "fair_value_available": False,
                    "market_price_available": False,
                    "true_probability_available": False,
                    "ev_after_spread_available": False,
                },
            )
        ],
    )
    _write_jsonl(
        base_dir,
        "decision_log",
        [
            _event(
                "2026-05-08T12:00:01Z",
                {
                    "candidate_trace_id": "ct_decision",
                    "trace_link_reason": "passive_deterministic_existing_fields",
                    "market_key": "btc-market",
                    "condition_id": "condition-a",
                    "token_id": "token-a",
                    "side": "YES",
                    "conditionId": "condition-a",
                    "tokenId": "token-a",
                    "asset_side": "YES",
                    "lifecycle_phase": "OPENING_SCAN",
                    "candidate_id": "candidate-a",
                    "decision": "SKIP",
                    "fair_value_available": False,
                    "market_price_available": False,
                    "true_probability_available": False,
                    "ev_after_spread_available": False,
                },
                event_type="decision",
            )
        ],
    )

    report = build_ev_field_coverage_report(base_dir=base_dir, date=DATE, run_id="run-target")

    assert report["post_emission_data_status"] == "POST_EMISSION_DATA_FOUND"
    assert report["candidate_trace_id_present_count"] == 2
    assert report["candidate_trace_id_presence_by_producer"]["market_snapshots"]["present_count"] == 1
    assert report["candidate_trace_id_presence_by_producer"]["decision_log"]["present_count"] == 1
    assert report["parent_candidate_trace_id_presence_by_producer"]["market_snapshots"]["present_count"] == 1
    assert report["trace_link_reason_presence_by_producer"]["decision_log"]["present_count"] == 1
    assert report["market_key_presence_by_producer"]["decision_log"]["present_count"] == 1
    assert report["condition_id_presence_by_producer"]["decision_log"]["present_count"] == 1
    assert report["token_id_presence_by_producer"]["decision_log"]["present_count"] == 1
    assert report["side_presence_by_producer"]["decision_log"]["present_count"] == 1
    assert report["post_emission_direct_identity_candidates"] == 1
    assert report["post_emission_strong_identity_candidates"] == 2
    assert report["direct_identity_improvement_possible"] is True
    assert report["fields_still_preventing_direct_identity"]["parent_candidate_trace_id"] == 1
    assert report["post_normalization_data_status"] == "POST_NORMALIZATION_DATA_FOUND"
    assert report["alias_normalized_field_counts"]["condition_id"] == 1
    assert report["alias_normalized_field_counts"]["token_id"] == 1
    assert report["alias_normalized_field_counts"]["side"] == 1
    assert report["alias_source_field_counts"]["conditionId"] == 1
    assert report["alias_source_field_counts"]["tokenId"] == 1
    assert report["alias_source_field_counts"]["asset_side"] == 1
    assert report["canonical_identity_field_presence_after_normalization"]["condition_id"]["present_count"] == 2
    assert report["canonical_identity_field_presence_after_normalization"]["condition_id"]["origin_counts"]["normalized_alias"] == 1
    assert report["producer_alias_dependency_counts"]["decision_log"]["condition_id"] == 1
    assert report["producer_canonical_presence_counts"]["decision_log"]["condition_id"]["present_count"] == 1
    assert report["trace_events_with_candidate_trace_id"] == 2
    assert report["trace_events_with_condition_id"] == 2
    assert report["trace_events_with_token_id"] == 2
    assert report["trace_events_with_side"] == 2
    assert report["trace_events_direct_ready"] == 1
    assert report["trace_events_strong_ready"] == 2
    assert report["fields_still_missing_after_alias_normalization"]["parent_candidate_trace_id"] == 1
    assert report["condition_identity_alias_counts"]["condition_id"] == 2
    assert report["condition_identity_alias_counts"]["conditionId"] == 1
    assert report["condition_identity_alias_by_producer"]["market_snapshots"]["condition_id"] == 1
    assert report["condition_identity_alias_by_producer"]["decision_log"]["conditionId"] == 1
    assert report["traced_events_with_any_condition_alias"] == 2
    assert report["traced_events_condition_alias_missing"] == 0
    assert report["condition_identity_best_alias"]["alias"] == "condition_id"
    assert report["condition_identity_alias_coverage_rate"] == 1.0
    assert report["condition_id_truly_absent_or_alias_hidden"] == "condition_id_present"
    assert report["post_condition_enrichment_verification_schema"]["version"] == "post_condition_enrichment_verification_v1"
    assert report["post_condition_enrichment_data_status"] == "POST_CONDITION_ENRICHMENT_DATA_FOUND"
    assert report["pre_patch_traced_events_with_condition_id"] == 0
    assert report["pre_patch_trace_events_direct_ready"] == 0
    assert report["pre_patch_trace_events_strong_ready"] == 0
    assert report["traced_events_with_condition_id_after_enrichment"] == 2
    assert report["condition_id_presence_by_producer_after_enrichment"]["market_snapshots"]["present_count"] == 1
    assert report["condition_id_presence_by_producer_after_enrichment"]["decision_log"]["present_count"] == 1
    assert report["condition_id_enrichment_candidate_count"] == 2
    assert report["trace_events_direct_ready_after_condition_enrichment"] == 1
    assert report["trace_events_strong_ready_after_condition_enrichment"] == 2
    assert report["condition_enrichment_delta"]["traced_events_with_condition_id_delta"] == 2
    assert report["fields_still_preventing_direct_identity_after_condition_enrichment"]["parent_candidate_trace_id"] == 1
    assert report["post_fallback_condition_coverage_verification_schema"]["version"] == "post_fallback_condition_coverage_verification_v1"
    assert report["post_fallback_data_status"] == "POST_FALLBACK_DATA_FOUND"
    assert report["pre_fallback_condition_id"] == 0
    assert report["pre_fallback_direct_ready"] == 0
    assert report["pre_fallback_strong_ready"] == 0
    assert report["traced_events_with_condition_id"] == 2
    assert report["post_fallback_condition_id_presence_by_producer"]["decision_log"]["present_count"] == 1
    assert report["post_fallback_trace_events_direct_ready"] == 1
    assert report["post_fallback_trace_events_strong_ready"] == 2
    assert report["remaining_identity_blockers"]["parent_candidate_trace_id"] == 1


def test_ev_field_coverage_normalizes_missing_ev_reasons(tmp_path):
    base_dir = tmp_path / "quant_data"
    _write_jsonl(
        base_dir,
        "market_snapshots",
        [
            _event(
                "2026-05-08T12:00:00Z",
                {
                    "candidate_id": "candidate-normalize",
                    "signal_id": "signal-normalize",
                    "market_id": "btc-market",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "fair_value_available": False,
                    "market_price_available": False,
                    "market_price_null_reason": "missing_value",
                    "true_probability_available": False,
                    "probability_model_stage": "no_probability_model_output",
                    "candidate_expiry_reason": "blocked",
                },
            )
        ],
    )

    report = build_ev_field_coverage_report(base_dir=base_dir, date=DATE, run_id="run-target")
    row = report["candidate_ev_coverage"][0]

    assert "missing_value" not in report["summary"]["ev_null_reason_counts"]
    assert row["field_never_visible_reasons"]["fair_value"] == "no_probability_model_output"
    assert row["field_never_visible_reasons"]["market_price"] == "legacy_missing_reason"
    assert row["field_never_visible_reasons"]["true_probability"] == "no_probability_model_output"
    assert row["field_never_visible_reasons"]["ev_after_spread"] == "no_probability_model_output"
    assert "legacy_missing_reason" in report["normalized_ev_null_reason_schema"]["categories"]
    assert "field_not_emitted" in report["normalized_ev_null_reason_schema"]["categories"]


def test_ev_field_coverage_attributes_missing_fields_to_event_producers(tmp_path):
    base_dir = tmp_path / "quant_data"
    candidate = {
        "candidate_id": "candidate-producer",
        "signal_id": "signal-producer",
        "market_id": "btc-market",
        "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
    }
    _write_jsonl(
        base_dir,
        "decision_log",
        [
            _event(
                "2026-05-08T12:00:00Z",
                {
                    **candidate,
                    "fair_value": 0.60,
                    "market_price": 0.55,
                    "true_probability": 0.60,
                    "ev_after_spread": 0.03,
                },
                event_type="decision_snapshot",
            )
        ],
    )
    _write_jsonl(
        base_dir,
        "market_snapshots",
        [
            _event(
                "2026-05-08T12:00:05Z",
                {
                    **candidate,
                },
            )
        ],
    )
    _write_jsonl(
        base_dir,
        "risk_log",
        [
            _event(
                "2026-05-08T12:00:10Z",
                {
                    **candidate,
                    "fair_value_available": False,
                    "fair_value_null_reason": "missing_value",
                    "market_price_available": False,
                    "market_price_null_reason": "missing_value",
                    "true_probability_available": False,
                    "true_probability_null_reason": "missing_value",
                    "ev_after_spread_available": False,
                    "ev_after_spread_null_reason": "missing_value",
                    "candidate_expiry_reason": "blocked",
                },
                event_type="risk_snapshot",
            )
        ],
    )

    report = build_ev_field_coverage_report(base_dir=base_dir, date=DATE, run_id="run-target")

    producer_missing = report["ev_field_missing_by_event_category"]
    assert producer_missing["market_snapshots"]["field_not_emitted"] == 4
    assert producer_missing["risk_log"]["legacy_missing_reason"] == 4
    assert report["dominant_missing_producer"]["event_category"] == "market_snapshots"
    assert report["dominant_missing_producer"]["missing_uncertain_ev_fields"] == 4
    assert report["producer_missing_share"]["market_snapshots"] == 0.5
    assert report["producer_missing_share"]["risk_log"] == 0.5
    assert report["producer_level_ev_visibility"]["best_ev_continuity_producer"]["event_category"] == "decision_log"
    assert report["producer_level_ev_visibility"]["by_event_category"]["decision_log"]["ev_field_continuity_rate"] == 1.0
    assert report["producer_level_ev_visibility"]["by_event_category"]["market_snapshots"]["ev_field_continuity_rate"] == 0.0
    assert report["ev_producer_observability_quality"] == "HAS_EV_PRODUCER_CONTINUITY"


def test_ev_field_coverage_traces_candidate_lifecycle_ev_disappearance(tmp_path):
    base_dir = tmp_path / "quant_data"
    candidate = {
        "candidate_id": "candidate-trace",
        "signal_id": "signal-trace",
        "market_id": "btc-market",
    }
    _write_jsonl(
        base_dir,
        "market_snapshots",
        [
            _event(
                "2026-05-08T12:00:00Z",
                {
                    **candidate,
                    "lifecycle_phase": "OPENING_SCAN",
                    "fair_value": 0.61,
                    "market_price": 0.57,
                    "true_probability": 0.61,
                    "ev_after_spread": 0.025,
                },
            )
        ],
    )
    _write_jsonl(
        base_dir,
        "decision_log",
        [
            _event(
                "2026-05-08T12:00:04Z",
                {
                    **candidate,
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "fair_value": 0.62,
                    "market_price": 0.58,
                    "true_probability": 0.62,
                    "ev_after_spread": 0.03,
                },
                event_type="decision_snapshot",
            )
        ],
    )
    _write_jsonl(
        base_dir,
        "risk_log",
        [
            _event(
                "2026-05-08T12:00:08Z",
                {
                    **candidate,
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "fair_value_available": False,
                    "fair_value_null_reason": "candidate_blocked_after_ev",
                    "market_price_available": False,
                    "market_price_null_reason": "field_not_emitted",
                    "true_probability_available": False,
                    "true_probability_null_reason": "candidate_blocked_after_ev",
                    "ev_after_spread_available": False,
                    "ev_after_spread_null_reason": "candidate_blocked_after_ev",
                    "candidate_block_stage": "post_ev",
                    "candidate_block_reason": "candidate_blocked_after_ev",
                    "candidate_expiry_reason": "blocked",
                },
                event_type="risk_snapshot",
            )
        ],
    )

    report = build_ev_field_coverage_report(base_dir=base_dir, date=DATE, run_id="run-target")
    row = report["candidate_ev_coverage"][0]
    trace = row["ev_candidate_lifecycle_trace"]

    assert row["first_ev_visible_phase"] == "OPENING_SCAN"
    assert row["first_ev_visible_producer"] == "market_snapshots"
    assert row["last_ev_visible_producer"] == "decision_log"
    assert row["ev_disappearance_phase"] == "ACTIVE_INVENTORY_TRADING"
    assert row["ev_trace_break_phase"] == "ACTIVE_INVENTORY_TRADING"
    assert row["producer_handoff_quality"] == "PARTIAL_PRODUCER_HANDOFF"
    assert row["lifecycle_observability_quality"] in {"EV_TRACE_BREAK", "EV_TRACE_INTERRUPTED"}
    assert row["producer_handoff_failure_count"] == 1
    assert row["candidate_phase_coverage"]["OPENING_SCAN"]["ev_visibility_rate"] == 1.0
    assert trace["where_ev_disappeared"]["producer"] == "risk_log"
    assert trace["lifecycle_timing_caused_disappearance"] is True
    assert report["ev_candidate_lifecycle_trace_summary"]["traceable_candidates"] == 1
    assert report["ev_trace_break_phase_counts"]["ACTIVE_INVENTORY_TRADING"] == 1
    assert report["producer_handoff_quality_counts"]["PARTIAL_PRODUCER_HANDOFF"] == 1


def test_ev_field_coverage_classifies_candidate_trace_confidence(tmp_path):
    base_dir = tmp_path / "quant_data"
    candidate = {
        "candidate_id": "candidate-confidence",
        "signal_id": "signal-confidence",
        "market_id": "btc-market",
        "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
    }
    _write_jsonl(
        base_dir,
        "market_snapshots",
        [
            _event(
                "2026-05-08T12:00:00Z",
                {
                    **candidate,
                    "fair_value_available": False,
                    "fair_value_null_reason": "candidate_blocked_before_ev",
                    "market_price_available": False,
                    "market_price_null_reason": "candidate_blocked_before_ev",
                    "true_probability_available": False,
                    "true_probability_null_reason": "candidate_blocked_before_ev",
                    "ev_after_spread_available": False,
                    "ev_after_spread_null_reason": "candidate_blocked_before_ev",
                    "candidate_block_stage": "pre_ev",
                    "candidate_block_reason": "candidate_blocked_before_ev",
                },
            )
        ],
    )
    _write_jsonl(
        base_dir,
        "decision_log",
        [
            _event(
                "2026-05-08T12:00:04Z",
                {
                    **candidate,
                    "fair_value_available": False,
                    "fair_value_null_reason": "no_probability_model_output",
                    "market_price_available": False,
                    "market_price_null_reason": "no_market_price",
                    "true_probability_available": False,
                    "true_probability_null_reason": "no_probability_model_output",
                    "ev_after_spread_available": False,
                    "ev_after_spread_null_reason": "no_probability_model_output",
                    "probability_model_stage": "no_probability_model_output",
                    "candidate_block_stage": "pre_ev",
                    "candidate_block_reason": "candidate_blocked_before_ev",
                },
                event_type="decision_snapshot",
            )
        ],
    )

    report = build_ev_field_coverage_report(base_dir=base_dir, date=DATE, run_id="run-target")
    row = report["candidate_ev_coverage"][0]

    assert row["candidate_trace_confidence"] == "DIRECT"
    assert row["identity_fragmentation_detected"] is False
    assert row["propagation_gap_detected"] is False
    assert row["candidate_blocked_before_ev"] is True
    assert row["ev_visibility_attempted"] is True
    assert row["ev_visibility_confirmed"] is False
    assert row["ev_attempted_but_not_visible"] is True
    assert row["candidate_seen_but_never_evaluable"] is False
    assert report["candidate_trace_confidence_counts"]["DIRECT"] == 1
    assert report["candidate_trace_confidence_diagnostics"]["ev_attempted_but_not_visible_count"] == 1
    assert report["identity_confidence_by_producer"]["market_snapshots"]["DIRECT"] == 1
    assert report["identity_confidence_by_producer"]["decision_log"]["DIRECT"] == 1
    assert report["identity_confidence_by_producer"]["market_snapshots"]["proxy_dependency_rate"] == 0.0
    assert report["candidate_trace_envelope_spec"]["version"] == "candidate_trace_envelope_v1"
    assert "candidate_trace_id" in report["producer_required_fields"]["decision_log"]
    assert report["missing_envelope_fields_by_producer"]["risk_log"]["candidate_trace_id"]["missing_count"] == 1
    assert report["weakest_envelope_producer"]["producer"] in {"execution_log", "risk_log", "trade_journal"}
    assert "candidate_trace_id" in report["runtime_observability_fields_needed"]["risk_log"]
    assert report["risk_log_identity_missing_count"] == 1
    assert report["risk_log_risk_state_missing_count"] == 1
    assert report["decision_to_risk_handoff_quality"]["NO_RISK_EVENT"] == 1
    assert report["risk_to_execution_handoff_quality"]["NO_RISK_EVENT"] == 1
    assert report["dominant_risk_visibility_failure"] == "no_risk_event_exists"
    assert report["decision_to_risk_boundary_counts"]["BLOCKED_BEFORE_RISK"] == 1
    assert report["risk_reachability_rate"] == 0.0
    assert report["risk_serialization_visibility_rate"] == 0.0
    assert report["pre_risk_block_share"] == 1.0
    assert report["dominant_decision_to_risk_boundary_failure"] == "BLOCKED_BEFORE_RISK"
    assert report["pre_risk_block_cause_counts"]["EV_NOT_VISIBLE"] == 1
    assert report["pre_risk_block_cause_counts"]["PROBABILITY_NOT_VISIBLE"] == 1
    assert report["pre_risk_block_cause_counts"]["FAIR_VALUE_NOT_VISIBLE"] == 1
    assert report["dominant_pre_risk_block_cause"] == "EV_NOT_VISIBLE"
    assert report["ev_related_pre_risk_block_share"] == 1.0
    assert report["unknown_pre_risk_block_share"] == 0.0
    assert report["model_state_gap_counts"]["BLOCKED_BEFORE_MODEL"] == 1
    assert report["probability_state_gap_counts"]["BLOCKED_BEFORE_MODEL"] == 1
    assert report["fair_value_state_gap_counts"]["BLOCKED_BEFORE_MODEL"] == 1
    assert report["ev_state_gap_counts"]["BLOCKED_BEFORE_MODEL"] == 1
    assert report["model_attempt_visibility_rate"] == 0.0
    assert report["model_output_serialization_rate"] == 0.0
    assert report["identity_blocked_model_link_rate"] == 0.0
    assert report["dominant_model_state_gap"] == "BLOCKED_BEFORE_MODEL"
    assert report["model_attempt_gate_counts"]["ORDERBOOK_GATE"] == 1
    assert report["dominant_model_attempt_gate"] == "ORDERBOOK_GATE"
    assert report["model_gate_microstructure_share"] == 1.0
    assert report["model_gate_timing_share"] == 0.0
    assert report["model_gate_identity_share"] == 0.0
    assert report["model_gate_unknown_share"] == 0.0
    assert report["model_attempt_eligibility_rate"] == 0.0
    assert "risk_state" in report["runtime_observability_fields_needed_for_risk_layer"]
    transition = report["producer_transition_identity_gap_tables"]["market_snapshots->decision_log"]
    assert transition["DIRECT"] == 1
    assert transition["direct_identity_rate"] == 1.0
    assert transition["strong_or_direct_rate"] == 1.0
    assert report["weakest_identity_transition"]["key"] == "decision_log->risk_log"
    assert report["dominant_identity_failure_transition"]["identity_gap_count"] >= 1


def test_ev_field_coverage_accepts_canonical_trace_aliases_for_risk_readiness(tmp_path):
    base_dir = tmp_path / "quant_data"
    candidate = {
        "candidate_id": "candidate-risk",
        "signal_id": "signal-risk",
        "market_id": "condition-risk",
        "lifecycle_phase": "OPENING_SCAN",
    }
    _write_jsonl(
        base_dir,
        "market_snapshots",
        [
            _event(
                "2026-05-08T12:00:00Z",
                {
                    **candidate,
                    "candidate_trace_id": "trace-risk",
                    "market_key": "condition-risk",
                    "condition_id": "condition-risk",
                    "token_id": "token-risk",
                    "side": "YES",
                    "fair_value_available": False,
                    "fair_value_null_reason": "no_probability_model_output",
                    "market_price_available": False,
                    "market_price_null_reason": "no_market_price",
                    "true_probability_available": False,
                    "true_probability_null_reason": "no_probability_model_output",
                    "ev_after_spread_available": False,
                    "ev_after_spread_null_reason": "no_probability_model_output",
                },
            ),
            _event(
                "2026-05-08T12:00:05Z",
                {
                    **candidate,
                    "candidate_trace_id": "trace-risk",
                    "market_key": "condition-risk",
                    "condition_id": "condition-risk",
                    "token_id": "token-risk",
                    "side": "YES",
                    "fair_value_available": False,
                    "market_price_available": False,
                    "true_probability_available": False,
                    "ev_after_spread_available": False,
                },
            ),
        ],
    )
    _write_jsonl(
        base_dir,
        "risk_log",
        [
            _event(
                "2026-05-08T12:00:03Z",
                {
                    "candidate_trace_id": "trace-risk",
                    "parent_candidate_trace_id": "candidate-risk",
                    "market_key": "condition-risk",
                    "condition_id": "condition-risk",
                    "lifecycle_phase": "OPENING_SCAN",
                    "risk_decision": "blocked_before_risk_budget",
                    "fair_value_available": False,
                    "market_price_available": False,
                    "true_probability_available": False,
                    "ev_after_spread_available": False,
                },
                event_type="risk_snapshot",
            )
        ],
    )

    report = build_ev_field_coverage_report(base_dir=base_dir, date=DATE, run_id="run-target")

    assert report["risk_layer_trace_readiness"] == 1.0
    assert report["risk_log_identity_missing_count"] == 0
    assert report["risk_log_market_key_missing_count"] == 0
    assert report["risk_log_lifecycle_phase_missing_count"] == 0
    assert report["risk_log_risk_state_missing_count"] == 0
    assert report["decision_to_risk_handoff_quality"]["NO_DECISION_EVIDENCE"] == 1
    assert report["ev_risk_chain_gap_diagnostics"]["classification"] == "EV_CHAIN_NOT_VISIBLE"
    assert "candidate_trace_id" in report["ev_risk_chain_gap_diagnostics"]["risk_layer_trace_readiness_requirements"]["candidate_identity"]


def test_write_ev_field_coverage_report_includes_sanitized_run_id(tmp_path):
    report = {
        "date_from": DATE,
        "date_to": DATE,
        "run_id": "run/id:target",
        "time_filter": {"since": "12:00", "until": "12:05", "applied": True},
        "summary": {},
        "candidate_ev_coverage": [],
    }

    path = write_ev_field_coverage_report(report, report_dir=tmp_path / "reports")

    assert path.name == "ev_field_coverage_2026-05-08_1200_to_1205_run_run_id_target.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["run_id"] == "run/id:target"


def test_ev_field_coverage_cli_writes_report(tmp_path, monkeypatch, capsys):
    base_dir = tmp_path / "quant_data"
    report_dir = tmp_path / "reports"
    _write_jsonl(
        base_dir,
        "market_snapshots",
        [
            _event(
                "2026-05-08T12:00:01Z",
                {
                    "candidate_id": "candidate-cli",
                    "signal_id": "signal-cli",
                    "market_id": "btc-market",
                    "lifecycle_phase": "OPENING_SCAN",
                    "fair_value_available": False,
                    "fair_value_null_reason": "no_probability_model_output",
                    "candidate_block_stage": "pre_ev",
                    "candidate_block_reason": "no_probability_model_output",
                },
            )
        ],
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "ev_field_coverage",
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
    assert "EV Field Coverage Diagnostics" in output
    assert (report_dir / "ev_field_coverage_2026-05-08_run_run-target.json").exists()
