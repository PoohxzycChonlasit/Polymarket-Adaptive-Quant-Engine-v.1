import json
from pathlib import Path

from tools.shadow.cross_run_ev_blindness import (
    build_cross_run_ev_blindness_report,
    main,
    write_cross_run_ev_blindness_report,
)


DATE = "2026-05-08"
NEXT_DATE = "2026-05-09"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _ev_report(
    *,
    date: str,
    run_id: str,
    avg_rate: float,
    no_probability_model_output: int,
    no_market_price: int,
    legacy_missing_reason: int,
    lifecycle_phase: str,
    block_stage: str,
    market_readiness: str,
    orderbook_state: str,
) -> dict:
    total_nulls = no_probability_model_output + no_market_price + legacy_missing_reason
    producer_missing = {
        "market_snapshots": {
            "field_not_emitted": no_probability_model_output,
            "legacy_missing_reason": 0,
            "missing_uncertain_ev_fields": no_probability_model_output,
            "total_ev_field_slots": no_probability_model_output + 4,
        },
        "risk_log": {
            "field_not_emitted": 0,
            "legacy_missing_reason": legacy_missing_reason,
            "missing_uncertain_ev_fields": legacy_missing_reason,
            "total_ev_field_slots": legacy_missing_reason + 4,
        },
    }
    return {
        "date_from": date,
        "date_to": date,
        "run_id": run_id,
        "scope": "offline_research_replay_only",
        "schema_version": "ev_field_coverage_v1",
        "schema_generation_version": "ev_field_coverage_post_fallback_condition_coverage_verification_v1",
        "replay_schema_freshness": "fresh",
        "stale_schema_detected": False,
        "stale_report_reason": "",
        "candidate_trace_confidence_schema": {
            "version": "candidate_trace_confidence_v1",
            "classes": ["DIRECT", "STRONG", "WEAK", "PROXY", "UNKNOWN"],
        },
        "direct_vs_proxy_identity_gap_schema": {
            "version": "direct_vs_proxy_identity_gap_tables_v1",
            "producer_transitions": [
                "market_snapshots->decision_log",
                "decision_log->risk_log",
                "risk_log->execution_log",
                "execution_log->trade_journal",
            ],
            "classes": ["DIRECT", "STRONG", "WEAK", "PROXY", "UNKNOWN"],
        },
        "candidate_trace_envelope_spec": {
            "version": "candidate_trace_envelope_v1",
            "scope": "offline_replay_observability_spec_only",
            "fields": ["candidate_trace_id", "market_key", "producer", "identity_confidence"],
        },
        "risk_layer_envelope_gap_schema": {
            "version": "risk_layer_envelope_gap_report_v1",
            "transitions": ["decision_log->risk_log", "risk_log->execution_log"],
        },
        "decision_to_risk_boundary_schema": {
            "version": "decision_to_risk_boundary_classification_v1",
            "categories": [
                "BLOCKED_BEFORE_RISK",
                "RISK_NOT_REACHED",
                "RISK_REACHED_NOT_SERIALIZED",
                "RISK_PRODUCER_NOT_RESPONSIBLE",
                "NO_DECISION_EVIDENCE",
                "LEGACY_OR_UNKNOWN",
            ],
        },
        "pre_risk_block_cause_taxonomy_schema": {
            "version": "pre_risk_block_cause_taxonomy_v1",
            "categories": [
                "EV_NOT_VISIBLE",
                "PROBABILITY_NOT_VISIBLE",
                "FAIR_VALUE_NOT_VISIBLE",
                "ORDERBOOK_NOT_READY",
                "LIQUIDITY_NOT_READY",
                "SPREAD_NOT_EXECUTABLE",
                "CUTOFF_OR_TIME_BLOCK",
                "LIFECYCLE_PHASE_BLOCK",
                "MARKET_NOT_EVALUABLE",
                "IDENTITY_LINK_WEAK",
                "UNKNOWN_PRE_RISK_BLOCK",
            ],
        },
        "model_state_attempt_emission_gap_schema": {
            "version": "model_state_attempt_vs_emission_gap_v1",
            "categories": [
                "MODEL_NOT_ATTEMPTED",
                "MODEL_ATTEMPTED_OUTPUT_MISSING",
                "MODEL_OUTPUT_EXISTS_NOT_SERIALIZED",
                "BLOCKED_BEFORE_MODEL",
                "IDENTITY_TOO_WEAK_TO_LINK_MODEL_STATE",
                "MODEL_STATE_UNKNOWN",
            ],
        },
        "model_attempt_gate_taxonomy_schema": {
            "version": "model_attempt_gate_taxonomy_v1",
            "categories": [
                "ORDERBOOK_GATE",
                "LIQUIDITY_GATE",
                "SPREAD_GATE",
                "TIME_CUTOFF_GATE",
                "LIFECYCLE_PHASE_GATE",
                "IDENTITY_CONFIDENCE_GATE",
                "MARKET_NOT_EVALUABLE_GATE",
                "PRODUCER_NOT_RESPONSIBLE",
                "MODEL_GATE_UNKNOWN",
            ],
        },
        "candidate_identity_upgrade_requirements_schema": {
            "version": "candidate_identity_upgrade_requirements_v1",
            "fields": [
                "candidate_trace_id",
                "parent_candidate_trace_id",
                "market_key",
                "condition_id",
                "token_id",
                "side",
                "lifecycle_phase",
                "candidate_seen_ts",
                "producer_event_type",
                "trace_link_reason",
            ],
            "requirements": {
                "DIRECT": [
                    "candidate_trace_id",
                    "parent_candidate_trace_id",
                    "market_key",
                    "condition_id",
                    "token_id",
                    "side",
                    "lifecycle_phase",
                    "candidate_seen_ts",
                    "producer_event_type",
                    "trace_link_reason",
                ],
                "STRONG": [
                    "market_key",
                    "condition_id",
                    "token_id",
                    "side",
                    "lifecycle_phase",
                    "candidate_seen_ts",
                    "producer_event_type",
                    "trace_link_reason",
                ],
                "WEAK": ["market_key", "lifecycle_phase", "candidate_seen_ts"],
                "PROXY": ["market_key", "candidate_seen_ts"],
                "UNKNOWN": [],
            },
        },
        "candidate_trace_id_post_emission_verification_schema": {
            "version": "candidate_trace_id_post_emission_verification_v1",
            "fields": [
                "candidate_trace_id",
                "parent_candidate_trace_id",
                "trace_link_reason",
                "market_key",
                "condition_id",
                "token_id",
                "side",
            ],
        },
        "alias_normalization_coverage_schema": {
            "version": "alias_normalization_coverage_verification_v1",
            "canonical_fields": ["condition_id", "token_id", "side", "market_key", "market_slug"],
            "origin_classes": ["original_canonical", "normalized_alias", "missing"],
        },
        "post_condition_enrichment_verification_schema": {
            "version": "post_condition_enrichment_verification_v1",
        },
        "post_fallback_condition_coverage_verification_schema": {
            "version": "post_fallback_condition_coverage_verification_v1",
        },
        "does_not_claim_profitability": True,
        "does_not_authorize_runtime_decisions": True,
        "does_not_infer_execution": True,
        "does_not_claim_mfe_mae": True,
        "events_loaded": 20,
        "continuity_chains_loaded": 2,
        "summary": {
            "candidate_ev_coverage_rows": 2,
            "avg_ev_field_continuity_rate": avg_rate,
            "avg_ev_visibility_duration_ms": 1000.0 if avg_rate else 0.0,
            "candidate_ev_visibility_state_counts": {
                "EV_NEVER_VISIBLE": 2 if avg_rate == 0 else 1,
                "EV_PARTIAL_VISIBLE": 0 if avg_rate == 0 else 1,
            },
            "ev_null_reason_counts": {
                "no_probability_model_output": no_probability_model_output,
                "no_market_price": no_market_price,
                "legacy_missing_reason": legacy_missing_reason,
            },
            "dominant_ev_blindness_context": {
                "dimension": "lifecycle_phase",
                "context": lifecycle_phase,
                "reason": "no_probability_model_output" if no_probability_model_output >= no_market_price else "no_market_price",
                "count": max(no_probability_model_output, no_market_price, legacy_missing_reason),
                "share": round(max(no_probability_model_output, no_market_price, legacy_missing_reason) / total_nulls, 4),
            },
            "ev_blindness_root_cause_confidence": "MEDIUM_CONTEXT_ALIGNED" if not legacy_missing_reason else "LOW_UNCERTAIN_LEGACY_HEAVY",
            "ev_candidate_lifecycle_trace_summary": {
                "traceable_candidates": 2,
                "avg_ev_lifecycle_visibility_score": avg_rate,
                "avg_continuity_survival_rate": 0.0 if avg_rate == 0 else 0.25,
                "first_ev_visible_phase_counts": {
                    "NO_EV_VISIBLE": 2 if avg_rate == 0 else 1,
                    "OPENING_SCAN": 0 if avg_rate == 0 else 1,
                },
                "last_ev_visible_phase_counts": {
                    "NO_EV_VISIBLE": 2 if avg_rate == 0 else 1,
                    "ACTIVE_INVENTORY_TRADING": 0 if avg_rate == 0 else 1,
                },
                "ev_disappearance_phase_counts": {
                    "NO_EV_VISIBLE": 2 if avg_rate == 0 else 0,
                    "ACTIVE_INVENTORY_TRADING": 0 if avg_rate == 0 else 1,
                },
                "ev_disappearance_reason_counts": {
                    "never_ev_visible": 2 if avg_rate == 0 else 0,
                    "candidate_blocked_after_ev": 0 if avg_rate == 0 else 1,
                },
                "ev_trace_break_phase_counts": {
                    "NO_EV_VISIBLE": 2 if avg_rate == 0 else 0,
                    "ACTIVE_INVENTORY_TRADING": 0 if avg_rate == 0 else 1,
                },
                "producer_handoff_quality_counts": {
                    "BROKEN_PRODUCER_HANDOFF": 2 if avg_rate == 0 else 1,
                    "PARTIAL_PRODUCER_HANDOFF": 0 if avg_rate == 0 else 1,
                },
                "lifecycle_observability_quality_counts": {
                    "EV_TRACE_BLIND": 2 if avg_rate == 0 else 1,
                    "EV_TRACE_BREAK": 0 if avg_rate == 0 else 1,
                },
                "candidate_trace_confidence_counts": {
                    "PROXY": 2 if avg_rate == 0 else 0,
                    "STRONG": 0 if avg_rate == 0 else 2,
                },
            },
        },
        "candidate_trace_confidence_diagnostics": {
            "identity_fragmentation_detected_count": 2 if avg_rate == 0 else 0,
            "propagation_gap_detected_count": 2 if avg_rate == 0 else 1,
            "lifecycle_propagation_interruption_count": 2,
            "candidate_seen_but_never_evaluable_count": 2 if avg_rate == 0 else 0,
            "candidate_blocked_before_ev_count": 2,
            "ev_attempted_but_not_visible_count": 0 if avg_rate == 0 else 1,
            "ev_visibility_attempted_count": 0 if avg_rate == 0 else 1,
            "ev_visibility_confirmed_count": 0 if avg_rate == 0 else 1,
        },
        "ev_null_by_lifecycle_phase": {
            lifecycle_phase: {
                "no_probability_model_output": no_probability_model_output,
                "no_market_price": no_market_price,
            },
            "UNKNOWN": {"legacy_missing_reason": legacy_missing_reason},
        },
        "ev_null_by_block_stage": {
            block_stage: {
                "no_probability_model_output": no_probability_model_output,
                "no_market_price": no_market_price,
            },
            "UNKNOWN": {"legacy_missing_reason": legacy_missing_reason},
        },
        "ev_null_by_block_reason": {
            "no_probability_model_output": {"no_probability_model_output": no_probability_model_output},
            "no_market_price": {"no_market_price": no_market_price},
            "UNKNOWN": {"legacy_missing_reason": legacy_missing_reason},
        },
        "ev_null_by_market_readiness": {
            market_readiness: {
                "no_probability_model_output": no_probability_model_output,
                "no_market_price": no_market_price,
                "legacy_missing_reason": legacy_missing_reason,
            }
        },
        "ev_null_by_orderbook_state": {
            orderbook_state: {
                "no_probability_model_output": no_probability_model_output,
                "no_market_price": no_market_price,
                "legacy_missing_reason": legacy_missing_reason,
            }
        },
        "ev_field_missing_by_event_category": producer_missing,
        "dominant_missing_producer": {
            "event_category": "market_snapshots" if no_probability_model_output >= legacy_missing_reason else "risk_log",
            "missing_uncertain_ev_fields": max(no_probability_model_output, legacy_missing_reason),
            "share": round(max(no_probability_model_output, legacy_missing_reason) / max(1, no_probability_model_output + legacy_missing_reason), 4),
        },
        "producer_missing_share": {
            "market_snapshots": round(no_probability_model_output / max(1, no_probability_model_output + legacy_missing_reason), 4),
            "risk_log": round(legacy_missing_reason / max(1, no_probability_model_output + legacy_missing_reason), 4),
        },
        "producer_level_ev_visibility": {
            "best_ev_continuity_producer": {
                "event_category": "decision_log",
                "ev_field_continuity_rate": 1.0 if avg_rate else 0.0,
            },
            "by_event_category": {
                "decision_log": {
                    "event_count": 1,
                    "total_ev_field_slots": 4,
                    "visible_ev_field_slots": 4 if avg_rate else 0,
                    "ev_visible_event_count": 1 if avg_rate else 0,
                    "ev_field_continuity_rate": 1.0 if avg_rate else 0.0,
                    "missing_reason_counts": {},
                },
                "market_snapshots": {
                    "event_count": 1,
                    "total_ev_field_slots": no_probability_model_output + 4,
                    "visible_ev_field_slots": 0,
                    "ev_visible_event_count": 0,
                    "ev_field_continuity_rate": 0.0,
                    "missing_reason_counts": {"field_not_emitted": no_probability_model_output},
                },
                "risk_log": {
                    "event_count": 1,
                    "total_ev_field_slots": legacy_missing_reason + 4,
                    "visible_ev_field_slots": 0,
                    "ev_visible_event_count": 0,
                    "ev_field_continuity_rate": 0.0,
                    "missing_reason_counts": {"legacy_missing_reason": legacy_missing_reason},
                },
            },
        },
        "identity_confidence_by_producer": {
            "decision_log": {
                "DIRECT": 0,
                "STRONG": 0 if avg_rate == 0 else 2,
                "WEAK": 0,
                "PROXY": 2 if avg_rate == 0 else 0,
                "UNKNOWN": 0,
                "total_candidates": 2,
                "direct_identity_event_count": 0 if avg_rate == 0 else 2,
                "proxy_match_event_count": 2 if avg_rate == 0 else 0,
                "total_identity_events": 2,
                "identity_gap_count": 2 if avg_rate == 0 else 0,
                "proxy_dependency_count": 2 if avg_rate == 0 else 0,
                "direct_identity_absence_count": 2 if avg_rate == 0 else 0,
                "identity_fragmentation_count": 2 if avg_rate == 0 else 0,
            },
            "market_snapshots": {
                "DIRECT": 0,
                "STRONG": 0 if avg_rate == 0 else 2,
                "WEAK": 0,
                "PROXY": 2 if avg_rate == 0 else 0,
                "UNKNOWN": 0,
                "total_candidates": 2,
                "direct_identity_event_count": 0 if avg_rate == 0 else 2,
                "proxy_match_event_count": 2 if avg_rate == 0 else 0,
                "total_identity_events": 2,
                "identity_gap_count": 2 if avg_rate == 0 else 0,
                "proxy_dependency_count": 2 if avg_rate == 0 else 0,
                "direct_identity_absence_count": 2 if avg_rate == 0 else 0,
                "identity_fragmentation_count": 2 if avg_rate == 0 else 0,
            },
        },
        "producer_transition_identity_gap_tables": {
            "market_snapshots->decision_log": {
                "DIRECT": 0,
                "STRONG": 0 if avg_rate == 0 else 2,
                "WEAK": 0,
                "PROXY": 2 if avg_rate == 0 else 0,
                "UNKNOWN": 0,
                "total_candidates": 2,
                "identity_gap_count": 2 if avg_rate == 0 else 0,
                "proxy_dependency_count": 2 if avg_rate == 0 else 0,
                "direct_identity_absence_count": 2,
                "identity_fragmentation_count": 2 if avg_rate == 0 else 0,
            },
            "decision_log->risk_log": {
                "DIRECT": 0,
                "STRONG": 0,
                "WEAK": 0,
                "PROXY": 0,
                "UNKNOWN": 2,
                "total_candidates": 2,
                "identity_gap_count": 2,
                "proxy_dependency_count": 0,
                "direct_identity_absence_count": 2,
                "identity_fragmentation_count": 2 if avg_rate == 0 else 0,
            },
        },
        "producer_required_fields": {
            "market_snapshots": ["candidate_trace_id", "market_key", "producer", "identity_confidence"],
            "decision_log": ["candidate_trace_id", "market_key", "producer", "identity_confidence"],
        },
        "missing_envelope_fields_by_producer": {
            "market_snapshots": {
                "candidate_trace_id": {"missing_count": 0 if avg_rate else 2, "present_count": 2 if avg_rate else 0, "required_count": 2, "missing_rate": 0.0 if avg_rate else 1.0},
                "identity_confidence": {"missing_count": 0, "present_count": 2, "required_count": 2, "missing_rate": 0.0},
            },
            "decision_log": {
                "candidate_trace_id": {"missing_count": 0, "present_count": 2, "required_count": 2, "missing_rate": 0.0},
                "identity_confidence": {"missing_count": 0, "present_count": 2, "required_count": 2, "missing_rate": 0.0},
            },
        },
        "envelope_readiness_score": 0.75 if avg_rate else 0.5,
        "weakest_envelope_producer": {
            "producer": "market_snapshots",
            "envelope_readiness_score": 0.5 if avg_rate == 0 else 1.0,
        },
        "runtime_observability_fields_needed": {
            "market_snapshots": ["candidate_trace_id"] if avg_rate == 0 else [],
            "decision_log": [],
        },
        "candidate_trace_id_post_emission_verification": {
            "post_emission_data_status": "POST_EMISSION_DATA_FOUND" if avg_rate else "POST_EMISSION_DATA_NOT_FOUND",
            "post_emission_data_exists": bool(avg_rate),
            "events_scanned": 2,
            "candidate_trace_id_present_count": 2 if avg_rate else 0,
            "candidate_trace_id_missing_count": 0 if avg_rate else 2,
            "candidate_trace_id_presence_by_producer": {
                "market_snapshots": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
                "decision_log": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
            },
            "parent_candidate_trace_id_presence_by_producer": {
                "market_snapshots": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
                "decision_log": {"present_count": 0, "missing_count": 1, "total_events": 1, "presence_rate": 0.0},
            },
            "trace_link_reason_presence_by_producer": {
                "market_snapshots": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
                "decision_log": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
            },
            "market_key_presence_by_producer": {
                "market_snapshots": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
                "decision_log": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
            },
            "condition_id_presence_by_producer": {
                "market_snapshots": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
                "decision_log": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
            },
            "token_id_presence_by_producer": {
                "market_snapshots": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
                "decision_log": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
            },
            "side_presence_by_producer": {
                "market_snapshots": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
                "decision_log": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
            },
            "post_emission_direct_identity_candidates": 1 if avg_rate else 0,
            "post_emission_strong_identity_candidates": 2 if avg_rate else 0,
            "post_emission_proxy_candidates": 0,
            "direct_identity_improvement_possible": bool(avg_rate),
            "fields_still_preventing_direct_identity": {"parent_candidate_trace_id": 1} if avg_rate else {},
        },
        "candidate_trace_alias_normalization_verification": {
            "post_normalization_data_status": "POST_NORMALIZATION_DATA_FOUND" if avg_rate else "POST_NORMALIZATION_DATA_NOT_FOUND",
            "post_normalization_data_exists": bool(avg_rate),
            "events_scanned": 2,
            "trace_events_scanned": 2 if avg_rate else 0,
            "alias_normalized_field_counts": {"condition_id": 1, "token_id": 1, "side": 1} if avg_rate else {},
            "alias_source_field_counts": {"conditionId": 1, "tokenId": 1, "asset_side": 1} if avg_rate else {},
            "canonical_identity_field_presence_after_normalization": {
                "condition_id": {
                    "present_count": 2,
                    "missing_count": 0,
                    "total_events": 2,
                    "presence_rate": 1.0,
                    "origin_counts": {"original_canonical": 1, "normalized_alias": 1, "missing": 0},
                },
                "token_id": {
                    "present_count": 2,
                    "missing_count": 0,
                    "total_events": 2,
                    "presence_rate": 1.0,
                    "origin_counts": {"original_canonical": 1, "normalized_alias": 1, "missing": 0},
                },
                "side": {
                    "present_count": 2,
                    "missing_count": 0,
                    "total_events": 2,
                    "presence_rate": 1.0,
                    "origin_counts": {"original_canonical": 1, "normalized_alias": 1, "missing": 0},
                },
            } if avg_rate else {},
            "producer_alias_dependency_counts": {"decision_log": {"condition_id": 1, "token_id": 1, "side": 1}} if avg_rate else {},
            "producer_canonical_presence_counts": {
                "market_snapshots": {
                    "condition_id": {"present_count": 1, "missing_count": 0, "total_events": 1, "presence_rate": 1.0},
                    "token_id": {"present_count": 1, "missing_count": 0, "total_events": 1, "presence_rate": 1.0},
                    "side": {"present_count": 1, "missing_count": 0, "total_events": 1, "presence_rate": 1.0},
                },
                "decision_log": {
                    "condition_id": {"present_count": 1, "missing_count": 0, "total_events": 1, "presence_rate": 1.0},
                    "token_id": {"present_count": 1, "missing_count": 0, "total_events": 1, "presence_rate": 1.0},
                    "side": {"present_count": 1, "missing_count": 0, "total_events": 1, "presence_rate": 1.0},
                },
            } if avg_rate else {},
            "trace_events_with_candidate_trace_id": 2 if avg_rate else 0,
            "trace_events_with_condition_id": 2 if avg_rate else 0,
            "trace_events_with_token_id": 2 if avg_rate else 0,
            "trace_events_with_side": 2 if avg_rate else 0,
            "trace_events_direct_ready": 1 if avg_rate else 0,
            "trace_events_strong_ready": 2 if avg_rate else 0,
            "fields_still_missing_after_alias_normalization": {"parent_candidate_trace_id": 1} if avg_rate else {},
        },
        "post_condition_enrichment_verification": {
            "post_condition_enrichment_data_status": "POST_CONDITION_ENRICHMENT_DATA_FOUND" if avg_rate else "POST_CONDITION_ENRICHMENT_DATA_NOT_FOUND",
            "post_condition_enrichment_data_exists": bool(avg_rate),
            "events_scanned": 2,
            "trace_events_scanned": 2 if avg_rate else 0,
            "pre_patch_traced_events_with_condition_id": 0,
            "pre_patch_trace_events_direct_ready": 0,
            "pre_patch_trace_events_strong_ready": 0,
            "traced_events_with_condition_id_after_enrichment": 2 if avg_rate else 0,
            "condition_id_presence_by_producer_after_enrichment": {
                "market_snapshots": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
                "decision_log": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
            },
            "condition_id_enrichment_candidate_count": 2 if avg_rate else 0,
            "trace_events_direct_ready_after_condition_enrichment": 1 if avg_rate else 0,
            "trace_events_strong_ready_after_condition_enrichment": 2 if avg_rate else 0,
            "condition_enrichment_delta": {
                "traced_events_with_condition_id_delta": 2 if avg_rate else 0,
                "trace_events_direct_ready_delta": 1 if avg_rate else 0,
                "trace_events_strong_ready_delta": 2 if avg_rate else 0,
            },
            "fields_still_preventing_direct_identity_after_condition_enrichment": {"parent_candidate_trace_id": 1} if avg_rate else {},
            "fields_still_preventing_strong_identity_after_condition_enrichment": {},
        },
        "post_fallback_condition_coverage_verification": {
            "post_fallback_data_status": "POST_FALLBACK_DATA_FOUND" if avg_rate else "POST_FALLBACK_DATA_NOT_FOUND",
            "post_fallback_data_exists": bool(avg_rate),
            "pre_fallback_condition_id": 0,
            "pre_fallback_direct_ready": 0,
            "pre_fallback_strong_ready": 0,
            "trace_events_with_candidate_trace_id": 2 if avg_rate else 0,
            "traced_events_with_condition_id": 2 if avg_rate else 0,
            "condition_id_presence_by_producer": {
                "market_snapshots": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
                "decision_log": {"present_count": 1 if avg_rate else 0, "missing_count": 0 if avg_rate else 1, "total_events": 1, "presence_rate": 1.0 if avg_rate else 0.0},
            },
            "trace_events_direct_ready": 1 if avg_rate else 0,
            "trace_events_strong_ready": 2 if avg_rate else 0,
            "remaining_identity_blockers": {"parent_candidate_trace_id": 1} if avg_rate else {},
            "post_fallback_delta": {
                "condition_id_delta": 2 if avg_rate else 0,
                "direct_ready_delta": 1 if avg_rate else 0,
                "strong_ready_delta": 2 if avg_rate else 0,
            },
        },
        "risk_layer_envelope_gap_report": {
            "risk_log_identity_missing_count": 2,
            "risk_log_market_key_missing_count": 2,
            "risk_log_lifecycle_phase_missing_count": 2,
            "risk_log_risk_state_missing_count": 2,
            "no_risk_event_exists_count": 2,
            "risk_event_exists_but_lacks_candidate_identity_count": 0,
            "risk_event_exists_but_lacks_risk_state_count": 0,
            "candidate_blocked_before_risk_visibility_count": 2 if avg_rate == 0 else 0,
            "ev_visible_before_risk_missing_after_count": 0 if avg_rate == 0 else 1,
            "risk_producer_not_responsible_count": 2 if avg_rate == 0 else 0,
            "stale_legacy_schema_count": 0,
            "decision_to_risk_handoff_quality": {"NO_RISK_EVENT": 2},
            "risk_to_execution_handoff_quality": {"NO_RISK_EVENT": 2},
            "risk_layer_trace_readiness": 0.0,
            "risk_layer_block_visibility": {
                "CANDIDATE_BLOCKED_BEFORE_RISK_SERIALIZATION": 2 if avg_rate == 0 else 0,
                "NO_RISK_EVENT": 0 if avg_rate == 0 else 2,
            },
            "weakest_risk_gap_reason": "no_risk_event_exists",
            "dominant_risk_visibility_failure": "no_risk_event_exists",
            "risk_visibility_failure_counts": {"no_risk_event_exists": 2},
            "decision_to_risk_boundary_counts": {
                "BLOCKED_BEFORE_RISK": 2 if avg_rate == 0 else 0,
                "RISK_NOT_REACHED": 0 if avg_rate == 0 else 2,
                "RISK_REACHED_NOT_SERIALIZED": 0,
                "RISK_PRODUCER_NOT_RESPONSIBLE": 0,
                "NO_DECISION_EVIDENCE": 0,
                "LEGACY_OR_UNKNOWN": 0,
            },
            "risk_reachability_rate": 0.0,
            "risk_serialization_visibility_rate": 0.0,
            "pre_risk_block_share": 1.0 if avg_rate == 0 else 0.0,
            "no_decision_evidence_share": 0.0,
            "dominant_decision_to_risk_boundary_failure": "BLOCKED_BEFORE_RISK" if avg_rate == 0 else "RISK_NOT_REACHED",
            "pre_risk_block_cause_counts": {
                "EV_NOT_VISIBLE": 2 if avg_rate == 0 else 0,
                "PROBABILITY_NOT_VISIBLE": 2 if avg_rate == 0 else 0,
                "FAIR_VALUE_NOT_VISIBLE": 2 if avg_rate == 0 else 0,
                "ORDERBOOK_NOT_READY": 2 if avg_rate == 0 else 0,
                "LIQUIDITY_NOT_READY": 0,
                "SPREAD_NOT_EXECUTABLE": 2 if avg_rate == 0 else 0,
                "CUTOFF_OR_TIME_BLOCK": 0,
                "LIFECYCLE_PHASE_BLOCK": 0,
                "MARKET_NOT_EVALUABLE": 0,
                "IDENTITY_LINK_WEAK": 0,
                "UNKNOWN_PRE_RISK_BLOCK": 0,
            },
            "dominant_pre_risk_block_cause": "EV_NOT_VISIBLE" if avg_rate == 0 else "none",
            "pre_risk_block_cause_share": {
                "EV_NOT_VISIBLE": 1.0 if avg_rate == 0 else 0.0,
                "PROBABILITY_NOT_VISIBLE": 1.0 if avg_rate == 0 else 0.0,
                "FAIR_VALUE_NOT_VISIBLE": 1.0 if avg_rate == 0 else 0.0,
                "ORDERBOOK_NOT_READY": 1.0 if avg_rate == 0 else 0.0,
                "SPREAD_NOT_EXECUTABLE": 1.0 if avg_rate == 0 else 0.0,
            },
            "ev_related_pre_risk_block_count": 2 if avg_rate == 0 else 0,
            "microstructure_related_pre_risk_block_count": 2 if avg_rate == 0 else 0,
            "timing_related_pre_risk_block_count": 0,
            "identity_related_pre_risk_block_count": 0,
            "unknown_pre_risk_block_count": 0,
            "ev_related_pre_risk_block_share": 1.0 if avg_rate == 0 else 0.0,
            "microstructure_related_pre_risk_block_share": 1.0 if avg_rate == 0 else 0.0,
            "timing_related_pre_risk_block_share": 0.0,
            "identity_related_pre_risk_block_share": 0.0,
            "unknown_pre_risk_block_share": 0.0,
            "model_state_gap_counts": {
                "BLOCKED_BEFORE_MODEL": 2 if avg_rate == 0 else 0,
                "MODEL_OUTPUT_EXISTS_NOT_SERIALIZED": 0 if avg_rate == 0 else 2,
                "MODEL_NOT_ATTEMPTED": 0,
                "MODEL_ATTEMPTED_OUTPUT_MISSING": 0,
                "IDENTITY_TOO_WEAK_TO_LINK_MODEL_STATE": 0,
                "MODEL_STATE_UNKNOWN": 0,
            },
            "probability_state_gap_counts": {
                "BLOCKED_BEFORE_MODEL": 2 if avg_rate == 0 else 0,
                "MODEL_OUTPUT_EXISTS_NOT_SERIALIZED": 0 if avg_rate == 0 else 2,
                "MODEL_NOT_ATTEMPTED": 0,
                "MODEL_ATTEMPTED_OUTPUT_MISSING": 0,
                "IDENTITY_TOO_WEAK_TO_LINK_MODEL_STATE": 0,
                "MODEL_STATE_UNKNOWN": 0,
            },
            "fair_value_state_gap_counts": {
                "BLOCKED_BEFORE_MODEL": 2 if avg_rate == 0 else 0,
                "MODEL_OUTPUT_EXISTS_NOT_SERIALIZED": 0 if avg_rate == 0 else 2,
                "MODEL_NOT_ATTEMPTED": 0,
                "MODEL_ATTEMPTED_OUTPUT_MISSING": 0,
                "IDENTITY_TOO_WEAK_TO_LINK_MODEL_STATE": 0,
                "MODEL_STATE_UNKNOWN": 0,
            },
            "ev_state_gap_counts": {
                "BLOCKED_BEFORE_MODEL": 2 if avg_rate == 0 else 0,
                "MODEL_OUTPUT_EXISTS_NOT_SERIALIZED": 0 if avg_rate == 0 else 2,
                "MODEL_NOT_ATTEMPTED": 0,
                "MODEL_ATTEMPTED_OUTPUT_MISSING": 0,
                "IDENTITY_TOO_WEAK_TO_LINK_MODEL_STATE": 0,
                "MODEL_STATE_UNKNOWN": 0,
            },
            "model_attempt_visible_count": 0 if avg_rate == 0 else 2,
            "model_output_serialized_count": 0,
            "identity_blocked_model_link_count": 0,
            "model_attempt_visibility_rate": 0.0 if avg_rate == 0 else 1.0,
            "model_output_serialization_rate": 0.0,
            "identity_blocked_model_link_rate": 0.0,
            "dominant_model_state_gap": "BLOCKED_BEFORE_MODEL" if avg_rate == 0 else "MODEL_OUTPUT_EXISTS_NOT_SERIALIZED",
            "model_attempt_gate_counts": {
                "ORDERBOOK_GATE": 2 if avg_rate == 0 else 0,
                "SPREAD_GATE": 2 if avg_rate == 0 else 0,
                "LIQUIDITY_GATE": 0,
                "TIME_CUTOFF_GATE": 0,
                "LIFECYCLE_PHASE_GATE": 0,
                "IDENTITY_CONFIDENCE_GATE": 0,
                "MARKET_NOT_EVALUABLE_GATE": 0,
                "PRODUCER_NOT_RESPONSIBLE": 0,
                "MODEL_GATE_UNKNOWN": 0,
            },
            "dominant_model_attempt_gate": "ORDERBOOK_GATE" if avg_rate == 0 else "none",
            "model_gate_microstructure_count": 2 if avg_rate == 0 else 0,
            "model_gate_timing_count": 0,
            "model_gate_identity_count": 0,
            "model_gate_unknown_count": 0,
            "model_gate_microstructure_share": 1.0 if avg_rate == 0 else 0.0,
            "model_gate_timing_share": 0.0,
            "model_gate_identity_share": 0.0,
            "model_gate_unknown_share": 0.0,
            "model_attempt_eligible_count": 0 if avg_rate == 0 else 2,
            "model_attempt_eligibility_rate": 0.0 if avg_rate == 0 else 1.0,
            "identity_confidence_requirements": {
                "DIRECT": [
                    "candidate_trace_id",
                    "parent_candidate_trace_id",
                    "market_key",
                    "condition_id",
                    "token_id",
                    "side",
                    "lifecycle_phase",
                    "candidate_seen_ts",
                    "producer_event_type",
                    "trace_link_reason",
                ],
                "STRONG": [
                    "market_key",
                    "condition_id",
                    "token_id",
                    "side",
                    "lifecycle_phase",
                    "candidate_seen_ts",
                    "producer_event_type",
                    "trace_link_reason",
                ],
                "WEAK": ["market_key", "lifecycle_phase", "candidate_seen_ts"],
                "PROXY": ["market_key", "candidate_seen_ts"],
                "UNKNOWN": [],
            },
            "identity_upgrade_required_fields": [
                "candidate_trace_id",
                "parent_candidate_trace_id",
                "market_key",
                "condition_id",
                "token_id",
                "side",
                "lifecycle_phase",
                "candidate_seen_ts",
                "producer_event_type",
                "trace_link_reason",
            ],
            "missing_fields_preventing_direct_identity": {
                "candidate_trace_id": 2,
                "parent_candidate_trace_id": 2,
            },
            "missing_fields_preventing_strong_identity": {} if avg_rate else {
                "condition_id": 2,
                "token_id": 2,
                "side": 2,
                "lifecycle_phase": 2,
                "producer_event_type": 2,
                "trace_link_reason": 2,
            },
            "candidate_identity_upgrade_path_counts": {
                "PROXY_OR_UNKNOWN_NEEDS_IDENTITY_FIELDS": 2 if avg_rate == 0 else 0,
                "ACTUAL_STRONG_CANONICAL_FIELDS_MISSING": 0 if avg_rate == 0 else 2,
            },
            "easiest_identity_upgrade_field": {
                "field": "candidate_trace_id",
                "blocked_candidate_field_mentions": 2,
            },
            "highest_impact_identity_field": {
                "field": "candidate_trace_id",
                "blocked_candidate_field_mentions": 2,
                "direct_missing_count": 2,
                "strong_missing_count": 0,
            },
            "direct_identity_blocker_rank": [
                {"field": "candidate_trace_id", "missing_count": 2, "share": 1.0},
                {"field": "parent_candidate_trace_id", "missing_count": 2, "share": 1.0},
            ],
            "strong_identity_blocker_rank": [] if avg_rate else [
                {"field": "condition_id", "missing_count": 2, "share": 1.0},
                {"field": "token_id", "missing_count": 2, "share": 1.0},
                {"field": "side", "missing_count": 2, "share": 1.0},
                {"field": "lifecycle_phase", "missing_count": 2, "share": 1.0},
                {"field": "producer_event_type", "missing_count": 2, "share": 1.0},
                {"field": "trace_link_reason", "missing_count": 2, "share": 1.0},
            ],
            "hypothetical_identity_upgrade_impact": {
                "field_impact_counts": {
                    "candidate_trace_id": 2,
                    "parent_candidate_trace_id": 2,
                    **({} if avg_rate else {
                        "condition_id": 2,
                        "token_id": 2,
                        "side": 2,
                        "lifecycle_phase": 2,
                        "producer_event_type": 2,
                        "trace_link_reason": 2,
                    }),
                },
                "rule": "hypothetical missing-field impact only; actual candidate_trace_confidence remains unchanged",
            },
            "runtime_observability_fields_needed_for_risk_layer": [
                "candidate_trace_id",
                "market_key",
                "lifecycle_phase",
                "risk_state",
            ],
            "transition_analysis": {
                "decision_log->risk_log": {"NO_RISK_EVENT": 2},
                "risk_log->execution_log": {"NO_RISK_EVENT": 2},
            },
        },
        "candidate_ev_coverage": [],
    }


def _write_report_set(report_dir: Path) -> None:
    _write_json(
        report_dir / f"ev_field_coverage_{DATE}_run_run-alpha.json",
        _ev_report(
            date=DATE,
            run_id="run-alpha",
            avg_rate=0.0,
            no_probability_model_output=6,
            no_market_price=1,
            legacy_missing_reason=0,
            lifecycle_phase="ACTIVE_INVENTORY_TRADING",
            block_stage="candidate_blocked_before_ev",
            market_readiness="spread_not_ready",
            orderbook_state="empty_book",
        ),
    )
    _write_json(
        report_dir / f"ev_field_coverage_{NEXT_DATE}_run_run-beta.json",
        _ev_report(
            date=NEXT_DATE,
            run_id="run-beta",
            avg_rate=0.5,
            no_probability_model_output=2,
            no_market_price=4,
            legacy_missing_reason=3,
            lifecycle_phase="ACTIVE_INVENTORY_TRADING",
            block_stage="candidate_blocked_before_ev",
            market_readiness="legacy_missing_reason",
            orderbook_state="legacy_missing_reason",
        ),
    )


def test_cross_run_ev_blindness_aggregates_patterns_and_trend(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    _write_report_set(report_dir)

    report = build_cross_run_ev_blindness_report(
        report_dir=report_dir,
        date_from=DATE,
        date_to=NEXT_DATE,
        migration_before_fresh_reports=0,
        migration_before_stale_reports=2,
        migration_before_schema_compatible_candidates=0,
        migration_before_stale_schema_candidates=4,
        reports_regenerated=2,
    )

    assert report["scope"] == "offline_research_replay_only"
    assert report["schema_version"] == "cross_run_ev_blindness_v1"
    assert report["does_not_claim_profitability"] is True
    assert report["does_not_authorize_runtime_decisions"] is True
    assert report["does_not_infer_execution"] is True
    assert report["does_not_claim_mfe_mae"] is True
    assert report["source_inputs"]["counts"]["ev_field_coverage_reports"] == 2
    assert report["aggregate"]["runs_analyzed"] == 2
    assert report["aggregate"]["total_ev_nulls"] == 16
    assert report["aggregate"]["recurring_ev_null_reasons"]["no_probability_model_output"] == 8
    assert report["recurring_lifecycle_ev_failures"]["ACTIVE_INVENTORY_TRADING"]["no_probability_model_output"] == 8
    assert report["cross_tabs"]["ev_null_by_block_stage"]["candidate_blocked_before_ev"]["no_market_price"] == 5
    assert report["cross_tabs"]["ev_null_by_market_readiness"]["legacy_missing_reason"]["legacy_missing_reason"] == 3
    assert report["recurring_model_output_failures"]["count"] == 8
    assert report["recurring_model_output_failures"]["trend"] == "decreasing"
    assert report["recurring_market_price_failures"]["count"] == 5
    assert report["recurring_market_price_failures"]["trend"] == "increasing"
    assert report["recurring_legacy_uncertainty"]["count"] == 3
    assert report["recurring_legacy_uncertainty"]["trend"] == "increasing"
    assert report["ev_observability_trend"]["visibility_rate_trend"] == "increasing"
    assert report["ev_visibility_maturity"] == "PARTIAL_EV_OBSERVABILITY"
    assert report["dominant_cross_run_ev_failure"]["reason"] == "no_probability_model_output"
    assert report["producer_attribution"]["dominant_missing_producer"]["event_category"] == "market_snapshots"
    assert report["producer_attribution"]["ev_field_missing_by_event_category"]["market_snapshots"]["field_not_emitted"] == 8
    assert report["producer_attribution"]["ev_field_missing_by_event_category"]["risk_log"]["legacy_missing_reason"] == 3
    assert report["producer_attribution"]["producer_level_ev_visibility"]["best_ev_continuity_producer"]["event_category"] == "decision_log"
    assert report["schema_freshness"]["fresh_reports"] == 2
    assert report["schema_freshness"]["stale_reports"] == 0
    assert report["schema_freshness"]["schema_compatible_candidate_count"] == 4
    assert report["freshness_filtered_cross_run_metrics"]["fresh_reports_analyzed"] == 2
    assert report["freshness_filtered_cross_run_metrics"]["schema_compatible_candidate_count"] == 4
    assert report["schema_migration_summary"]["reports_regenerated"] == 2
    assert report["schema_migration_summary"]["reports_remaining_stale"] == 0
    assert report["schema_migration_summary"]["stale_to_fresh_candidate_count"] == 4
    assert report["schema_migration_summary"]["schema_migration_completed"] is True
    assert report["schema_migration_summary"]["before_after_schema_migration_comparison"]["fresh_report_count_before"] == 0
    assert report["schema_migration_summary"]["before_after_schema_migration_comparison"]["fresh_report_count_after"] == 2
    assert report["cross_run_ev_candidate_lifecycle_trace"]["traceable_candidates"] == 4
    assert report["cross_run_ev_candidate_lifecycle_trace"]["dominant_ev_trace_break"]["phase"] == "NO_EV_VISIBLE"
    assert report["cross_run_ev_candidate_lifecycle_trace"]["candidate_trace_confidence_counts"]["PROXY"] == 2
    assert report["cross_run_ev_candidate_lifecycle_trace"]["candidate_trace_confidence_counts"]["STRONG"] == 2
    assert report["cross_run_ev_candidate_lifecycle_trace"]["candidate_trace_confidence_diagnostics"]["candidate_blocked_before_ev_count"] == 4
    identity = report["cross_run_identity_gap_tables"]
    assert identity["identity_confidence_by_producer"]["market_snapshots"]["PROXY"] == 2
    assert identity["identity_confidence_by_producer"]["market_snapshots"]["STRONG"] == 2
    assert identity["producer_transition_identity_gap_tables"]["market_snapshots->decision_log"]["PROXY"] == 2
    assert identity["producer_transition_identity_gap_tables"]["market_snapshots->decision_log"]["STRONG"] == 2
    assert identity["weakest_identity_transition"]["key"] == "decision_log->risk_log"
    assert identity["dominant_identity_failure_transition"]["identity_gap_count"] == 4
    assert report["candidate_trace_envelope_spec"]["version"] == "candidate_trace_envelope_v1"
    assert report["envelope_readiness_score"] == 0.875
    assert report["missing_envelope_fields_by_producer"]["market_snapshots"]["candidate_trace_id"]["missing_count"] == 2
    assert report["weakest_envelope_producer"]["producer"] == "market_snapshots"
    assert "candidate_trace_id" in report["runtime_observability_fields_needed"]["market_snapshots"]
    assert report["risk_log_identity_missing_count"] == 4
    assert report["risk_log_risk_state_missing_count"] == 4
    assert report["decision_to_risk_handoff_quality"]["NO_RISK_EVENT"] == 4
    assert report["risk_to_execution_handoff_quality"]["NO_RISK_EVENT"] == 4
    assert report["candidate_blocked_before_risk_visibility_count"] == 2
    assert report["ev_visible_before_risk_missing_after_count"] == 1
    assert report["dominant_risk_visibility_failure"] == "no_risk_event_exists"
    assert report["decision_to_risk_boundary_counts"]["BLOCKED_BEFORE_RISK"] == 2
    assert report["decision_to_risk_boundary_counts"]["RISK_NOT_REACHED"] == 2
    assert report["risk_reachability_rate"] == 0.0
    assert report["risk_serialization_visibility_rate"] == 0.0
    assert report["pre_risk_block_share"] == 0.5
    assert report["dominant_decision_to_risk_boundary_failure"] == "BLOCKED_BEFORE_RISK"
    assert report["pre_risk_block_cause_counts"]["EV_NOT_VISIBLE"] == 2
    assert report["pre_risk_block_cause_counts"]["ORDERBOOK_NOT_READY"] == 2
    assert report["dominant_pre_risk_block_cause"] == "EV_NOT_VISIBLE"
    assert report["ev_related_pre_risk_block_share"] == 1.0
    assert report["microstructure_related_pre_risk_block_share"] == 1.0
    assert report["timing_related_pre_risk_block_share"] == 0.0
    assert report["identity_related_pre_risk_block_share"] == 0.0
    assert report["unknown_pre_risk_block_share"] == 0.0
    assert report["model_state_gap_counts"]["BLOCKED_BEFORE_MODEL"] == 2
    assert report["model_state_gap_counts"]["MODEL_OUTPUT_EXISTS_NOT_SERIALIZED"] == 2
    assert report["probability_state_gap_counts"]["BLOCKED_BEFORE_MODEL"] == 2
    assert report["fair_value_state_gap_counts"]["MODEL_OUTPUT_EXISTS_NOT_SERIALIZED"] == 2
    assert report["ev_state_gap_counts"]["MODEL_OUTPUT_EXISTS_NOT_SERIALIZED"] == 2
    assert report["model_attempt_visibility_rate"] == 0.5
    assert report["model_output_serialization_rate"] == 0.0
    assert report["identity_blocked_model_link_rate"] == 0.0
    assert report["dominant_model_state_gap"] == "BLOCKED_BEFORE_MODEL"
    assert report["model_attempt_gate_counts"]["ORDERBOOK_GATE"] == 2
    assert report["model_attempt_gate_counts"]["SPREAD_GATE"] == 2
    assert report["dominant_model_attempt_gate"] == "ORDERBOOK_GATE"
    assert report["model_gate_microstructure_share"] == 1.0
    assert report["model_gate_timing_share"] == 0.0
    assert report["model_gate_identity_share"] == 0.0
    assert report["model_gate_unknown_share"] == 0.0
    assert report["model_attempt_eligibility_rate"] == 0.5
    assert report["post_emission_data_status"] == "POST_EMISSION_DATA_FOUND"
    assert report["candidate_trace_id_present_count"] == 2
    assert report["candidate_trace_id_presence_by_producer"]["market_snapshots"]["present_count"] == 1
    assert report["candidate_trace_id_presence_by_producer"]["decision_log"]["present_count"] == 1
    assert report["post_emission_direct_identity_candidates"] == 1
    assert report["post_emission_strong_identity_candidates"] == 2
    assert report["fields_still_preventing_direct_identity"]["parent_candidate_trace_id"] == 1
    assert report["post_normalization_data_status"] == "POST_NORMALIZATION_DATA_FOUND"
    assert report["alias_normalized_field_counts"]["condition_id"] == 1
    assert report["alias_normalized_field_counts"]["token_id"] == 1
    assert report["alias_normalized_field_counts"]["side"] == 1
    assert report["alias_source_field_counts"]["conditionId"] == 1
    assert report["producer_alias_dependency_counts"]["decision_log"]["condition_id"] == 1
    assert report["producer_canonical_presence_counts"]["decision_log"]["condition_id"]["present_count"] == 1
    assert report["trace_events_direct_ready"] == 1
    assert report["trace_events_strong_ready"] == 2
    assert report["fields_still_missing_after_alias_normalization"]["parent_candidate_trace_id"] == 1
    assert report["post_condition_enrichment_data_status"] == "POST_CONDITION_ENRICHMENT_DATA_FOUND"
    assert report["traced_events_with_condition_id_after_enrichment"] == 2
    assert report["condition_id_presence_by_producer_after_enrichment"]["decision_log"]["present_count"] == 1
    assert report["condition_id_enrichment_candidate_count"] == 2
    assert report["trace_events_direct_ready_after_condition_enrichment"] == 1
    assert report["trace_events_strong_ready_after_condition_enrichment"] == 2
    assert report["post_fallback_data_status"] == "POST_FALLBACK_DATA_FOUND"
    assert report["traced_events_with_condition_id"] == 2
    assert report["post_fallback_condition_id_presence_by_producer"]["decision_log"]["present_count"] == 1
    assert report["post_fallback_trace_events_direct_ready"] == 1
    assert report["post_fallback_trace_events_strong_ready"] == 2
    assert report["remaining_identity_blockers"]["parent_candidate_trace_id"] == 1
    assert "risk_state" in report["runtime_observability_fields_needed_for_risk_layer"]
    assert report["research_questions"]["dominant_ev_trace_break"]["phase"] == "NO_EV_VISIBLE"
    assert report["research_questions"]["candidate_trace_confidence_counts"]["PROXY"] == 2
    assert report["recurring_ev_blindness_patterns"]
    assert report["research_questions"]["model_output_failure_trend"] == "decreasing"


def test_cross_run_ev_blindness_excludes_stale_schema_from_trace_confidence(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    fresh = _ev_report(
        date=DATE,
        run_id="run-fresh",
        avg_rate=0.5,
        no_probability_model_output=2,
        no_market_price=1,
        legacy_missing_reason=0,
        lifecycle_phase="ACTIVE_INVENTORY_TRADING",
        block_stage="candidate_blocked_before_ev",
        market_readiness="spread_not_ready",
        orderbook_state="empty_book",
    )
    stale = _ev_report(
        date=NEXT_DATE,
        run_id="run-stale",
        avg_rate=0.0,
        no_probability_model_output=10,
        no_market_price=0,
        legacy_missing_reason=0,
        lifecycle_phase="ACTIVE_INVENTORY_TRADING",
        block_stage="candidate_blocked_before_ev",
        market_readiness="spread_not_ready",
        orderbook_state="empty_book",
    )
    for key in (
        "schema_generation_version",
        "replay_schema_freshness",
        "stale_schema_detected",
        "stale_report_reason",
        "candidate_trace_confidence_schema",
        "candidate_trace_confidence_diagnostics",
    ):
        stale.pop(key, None)
    stale["summary"].pop("candidate_trace_confidence_counts", None)
    stale["summary"].pop("ev_visibility_attempted_count", None)
    stale["summary"].pop("propagation_gap_detected_count", None)
    _write_json(report_dir / f"ev_field_coverage_{DATE}_run_run-fresh.json", fresh)
    _write_json(report_dir / f"ev_field_coverage_{NEXT_DATE}_run_run-stale.json", stale)

    report = build_cross_run_ev_blindness_report(
        report_dir=report_dir,
        date_from=DATE,
        date_to=NEXT_DATE,
    )

    assert report["source_inputs"]["counts"]["ev_field_coverage_reports"] == 2
    assert report["schema_freshness"]["fresh_reports"] == 1
    assert report["schema_freshness"]["stale_reports"] == 1
    assert report["schema_freshness"]["schema_compatible_candidate_count"] == 2
    assert report["schema_freshness"]["stale_schema_candidate_count"] == 2
    assert report["schema_freshness"]["stale_reports_detail"][0]["run_id"] == "run-stale"
    assert "schema_generation_version" in report["schema_freshness"]["stale_reports_detail"][0]["stale_report_reason"]
    assert report["freshness_filtered_cross_run_metrics"]["fresh_reports_analyzed"] == 1
    assert report["freshness_filtered_cross_run_metrics"]["stale_reports_excluded_from_continuity"] == 1
    assert report["cross_run_ev_candidate_lifecycle_trace"]["traceable_candidates"] == 2
    assert report["cross_run_ev_candidate_lifecycle_trace"]["candidate_trace_confidence_counts"]["STRONG"] == 2
    assert "PROXY" not in report["cross_run_ev_candidate_lifecycle_trace"]["candidate_trace_confidence_counts"]
    assert report["cross_run_identity_gap_tables"]["identity_confidence_by_producer"]["market_snapshots"]["STRONG"] == 2
    assert report["cross_run_identity_gap_tables"]["identity_confidence_by_producer"]["market_snapshots"]["PROXY"] == 0
    assert report["post_emission_data_status"] == "POST_EMISSION_DATA_FOUND"
    assert report["candidate_trace_id_present_count"] == 2
    assert report["post_normalization_data_status"] == "POST_NORMALIZATION_DATA_FOUND"
    assert report["trace_events_strong_ready"] == 2
    assert report["post_condition_enrichment_data_status"] == "POST_CONDITION_ENRICHMENT_DATA_FOUND"
    assert report["traced_events_with_condition_id_after_enrichment"] == 2
    assert report["post_fallback_data_status"] == "POST_FALLBACK_DATA_FOUND"
    assert report["traced_events_with_condition_id"] == 2


def test_write_cross_run_ev_blindness_report_uses_date_range_and_run_filter(tmp_path: Path) -> None:
    report = {
        "date_from": DATE,
        "date_to": NEXT_DATE,
        "run_id_filter": "run/id",
    }

    path = write_cross_run_ev_blindness_report(report, report_dir=tmp_path / "reports")

    assert path.name == f"cross_run_ev_blindness_{DATE}_to_{NEXT_DATE}_run_run_id.json"
    assert json.loads(path.read_text(encoding="utf-8"))["run_id_filter"] == "run/id"


def test_cross_run_ev_blindness_cli_writes_report(tmp_path: Path, capsys) -> None:
    report_dir = tmp_path / "reports"
    _write_report_set(report_dir)

    assert main([
        "--from",
        DATE,
        "--to",
        NEXT_DATE,
        "--report-dir",
        str(report_dir),
    ]) == 0

    output = capsys.readouterr().out
    assert "Cross-Run EV Blindness Trend Analysis" in output
    assert "reports=2" in output
    assert (report_dir / f"cross_run_ev_blindness_{DATE}_to_{NEXT_DATE}.json").exists()
