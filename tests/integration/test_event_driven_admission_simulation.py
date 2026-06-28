from __future__ import annotations

import json
from pathlib import Path

from tools.probes.event_driven_admission_simulation import (
    build_event_driven_admission_simulation_report,
    write_event_driven_admission_simulation_report,
)


DATE = "2026-05-12"


def _write_event(base_dir: Path, category: str, event: dict) -> None:
    path = base_dir / category / f"{DATE}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")


def _snapshot_payload(**overrides):
    payload = {
        "condition_id": "cond-1",
        "market_slug": "btc-updown-5m",
        "yes_token_id": "yes-1",
        "no_token_id": "no-1",
        "yes_bid": 0.47,
        "yes_ask": 0.49,
        "no_bid": 0.50,
        "no_ask": 0.52,
        "orderbook_age_ms": 250,
        "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
        "current_price": 100_000,
        "price_to_beat": 100_100,
        "seconds_remaining": 200,
        "liquidity_state": "ready",
        "risk_state": "observable",
    }
    payload.update(overrides)
    return payload


def test_event_driven_admission_simulation_counts_funnel_gates(tmp_path) -> None:
    base_dir = tmp_path / "quant_data"
    report_dir = tmp_path / "reports"
    events = [
        _snapshot_payload(),
        _snapshot_payload(yes_token_id=None, no_token_id=None),
        _snapshot_payload(lifecycle_phase="FINAL_DERISK"),
        _snapshot_payload(orderbook_age_ms=6_000),
        _snapshot_payload(yes_bid=0.30, yes_ask=0.48),
        _snapshot_payload(lifecycle_phase="PROFIT_MANAGEMENT", risk_state=None, risk_mode=None),
    ]
    for payload in events:
        _write_event(
            base_dir,
            "market_snapshots",
            {
                "timestamp_utc": "2026-05-12T01:00:00Z",
                "run_id": "run-a",
                "payload": payload,
            },
        )
    _write_event(
        base_dir,
        "decision_log",
        {
            "timestamp_utc": "2026-05-12T01:01:00Z",
            "run_id": "run-a",
            "payload": {"probability_model_called": True},
        },
    )

    report = build_event_driven_admission_simulation_report(date=DATE, base_dir=base_dir)
    path = write_event_driven_admission_simulation_report(report, report_dir=report_dir)

    assert path == report_dir / f"event_driven_admission_simulation_{DATE}.json"
    assert report["scope"] == "offline_replay_simulation_only"
    assert report["schema_version"] == "event_driven_admission_simulation_v5"
    assert report["guardrails"]["offline_only"] is True
    assert report["guardrails"]["runtime_behavior_changed"] is False
    assert report["simulation_funnel"]["executable_liquidity_event_count"] == 6
    assert report["simulation_funnel"]["same_token_pair_count"] == 5
    assert report["simulation_funnel"]["model_eligibility_would_be_reached_count"] == 2
    assert report["simulation_funnel"]["risk_gate_observable_count"] == 1
    assert report["fail_counts_by_gate"] == {
        "token_pair_lineage_ok": 1,
        "lifecycle_window_ok": 1,
        "freshness_ok": 1,
        "spread_ok": 1,
    }
    assert report["active_profit_final_derisk_phase_split"] == {
        "ACTIVE_INVENTORY_TRADING": 4,
        "PROFIT_MANAGEMENT": 1,
        "FINAL_DERISK": 1,
    }
    assert report["observed_probability_model_called_count"] == 1
    assert report["estimated_probability_model_called_uplift"] == 1
    assert report["required_missing_fields"] == []
    assert report["ev_input_coverage"]["underlying_price_available_count"] == 2
    assert report["ev_input_coverage"]["target_price_available_count"] == 2
    assert report["ev_input_coverage"]["risk_gate_offline_estimation"] == {
        "risk_gate_observable_count": 1,
        "risk_gate_observable_rate": 0.5,
        "can_estimate_without_runtime_risk_decision_changes": True,
        "reason": "risk_fields_available_on_some_simulated_model_eligible_events",
        "fields_audited": [
            "risk_state",
            "risk_decision",
            "risk_mode",
            "risk_block_reason",
            "available_risk_budget",
            "remaining_risk_budget",
            "risk_budget_used",
            "current_exposure",
            "target_exposure",
            "reconciliation_state",
        ],
    }
    packet_gap = report["packet_schema_gap"]
    assert packet_gap["packet_schema_version"] == "event_driven_admission_packet_schema_v1"
    assert packet_gap["packet_event_count"] == 2
    assert "underlying_price" in packet_gap["required_fields"]
    assert "risk_context" in packet_gap["optional_fields"]
    assert packet_gap["missing_required_fields"] == []
    assert packet_gap["field_source_map"]["underlying_price"] == "BTC/ETH price feed or oracle/PTB context"
    price_mapping = report["price_source_mapping"]
    assert price_mapping["schema_version"] == "price_source_mapping_v1"
    assert price_mapping["fields"]["underlying_price"]["joinability_classification_counts"] == {"alias_present": 2}
    assert price_mapping["fields"]["target_price"]["joinability_classification_counts"] == {"alias_present": 2}
    diagnostics = report["packet_price_enrichment_diagnostics"]
    assert diagnostics["model_eligible_packet_count"] == 2
    assert diagnostics["model_eligible_packets_with_price_fields"] == 2
    assert diagnostics["enrichment_drop_reason_counts"] == {"price_fields_present": 2}
    assert diagnostics["dominant_propagation_drop_reason"] == "NONE"


def test_event_driven_admission_simulation_reports_required_missing_fields(tmp_path) -> None:
    base_dir = tmp_path / "quant_data"
    _write_event(
        base_dir,
        "market_snapshots",
        {
            "timestamp_utc": "2026-05-12T01:00:00Z",
            "run_id": "run-a",
            "payload": _snapshot_payload(current_price=None, price_to_beat=None, liquidity_state=None),
        },
    )

    report = build_event_driven_admission_simulation_report(date=DATE, base_dir=base_dir)

    assert report["simulation_funnel"]["model_eligibility_would_be_reached_count"] == 1
    assert report["model_ev_required_field_missing_counts"] == {
        "underlying_price": 1,
        "target_price": 1,
        "liquidity": 1,
    }
    assert report["required_missing_fields"] == ["liquidity", "target_price", "underlying_price"]
    coverage = report["ev_input_coverage"]["field_group_coverage"]
    assert coverage["underlying_price"]["model_eligible_missing_reason_counts"] == {"not_emitted_in_loaded_replay": 1}
    assert coverage["target_price"]["model_eligible_missing_reason_counts"] == {"not_emitted_in_loaded_replay": 1}
    assert report["ev_input_coverage"]["minimum_additional_offline_fields_needed"] == [
        "liquidity",
        "target_price",
        "underlying_price",
    ]
    assert report["packet_schema_gap"]["missing_required_fields"] == ["underlying_price", "target_price", "liquidity"]
    packet_fields = {field["field"]: field for field in report["packet_schema_gap"]["fields"]}
    assert packet_fields["underlying_price"]["missing_reason_counts"] == {"not_emitted_in_loaded_replay": 1}
    assert packet_fields["target_price"]["missing_reason_counts"] == {"not_emitted_in_loaded_replay": 1}
    assert packet_fields["risk_context"]["current_coverage_count"] == 1
    price_mapping = report["price_source_mapping"]
    assert price_mapping["fields"]["underlying_price"]["joinability_classification_counts"] == {
        "not_available_in_replay": 1
    }
    assert price_mapping["fields"]["target_price"]["joinability_classification_counts"] == {
        "not_available_in_replay": 1
    }
    assert price_mapping["offline_join_possible"] is False
    diagnostics = report["packet_price_enrichment_diagnostics"]
    assert diagnostics["model_eligible_packets_without_price_fields"] == 1
    assert diagnostics["packets_missing_due_to_snapshot_only_path"] == 1
    assert diagnostics["enrichment_drop_reason_counts"] == {"legacy_no_packet_price_diagnostics": 1}


def test_event_driven_admission_simulation_ignores_non_executable_and_non_source_events(tmp_path) -> None:
    base_dir = tmp_path / "quant_data"
    _write_event(
        base_dir,
        "market_snapshots",
        {
            "timestamp_utc": "2026-05-12T01:00:00Z",
            "run_id": "run-a",
            "payload": _snapshot_payload(no_ask=None),
        },
    )
    _write_event(
        base_dir,
        "execution_log",
        {
            "timestamp_utc": "2026-05-12T01:00:01Z",
            "run_id": "run-a",
            "payload": _snapshot_payload(),
        },
    )

    report = build_event_driven_admission_simulation_report(date=DATE, base_dir=base_dir)

    assert report["simulation_funnel"]["executable_liquidity_event_count"] == 0
    assert report["simulation_funnel"]["model_eligibility_would_be_reached_count"] == 0
    assert report["recommended_next_patch"] == (
        "Collect fresh market_snapshot JSONL with YES/NO bid/ask fields before simulating admission."
    )


def test_event_driven_admission_simulation_audits_ev_input_aliases(tmp_path) -> None:
    base_dir = tmp_path / "quant_data"
    _write_event(
        base_dir,
        "market_snapshots",
        {
            "timestamp_utc": "2026-05-12T01:00:00Z",
            "run_id": "run-a",
            "payload": _snapshot_payload(
                current_price=None,
                price_to_beat=None,
                spot_price=100_010,
                strike_price=100_100,
                packet_schema_version="event_driven_admission_packet_v1",
                price_enrichment_source="ptb_info",
                ptb_context_available=True,
                oracle_price_available=True,
                target_price_available=True,
                packet_schema_price_fields_present=True,
            ),
        },
    )

    report = build_event_driven_admission_simulation_report(date=DATE, base_dir=base_dir)
    coverage = report["ev_input_coverage"]["field_group_coverage"]
    packet_fields = {field["field"]: field for field in report["packet_schema_gap"]["fields"]}

    assert report["required_missing_fields"] == []
    assert coverage["underlying_price"]["model_eligible_alias_hits"] == {"spot_price": 1}
    assert coverage["target_price"]["model_eligible_alias_hits"] == {"strike_price": 1}
    assert packet_fields["packet_schema_version"]["current_coverage_count"] == 1
    assert packet_fields["packet_schema_version"]["alias_hits"] == {"packet_schema_version": 1}
    diagnostics = report["packet_price_enrichment_diagnostics"]
    assert diagnostics["packets_with_ptb_context"] == 1
    assert diagnostics["packets_after_ptb_ready"] == 1
    assert diagnostics["enrichment_source_counts"] == {"ptb_info": 1}
    assert diagnostics["packet_schema_price_field_counts"] == {"packet_schema_price_fields_present_true": 1}
    assert report["price_source_mapping"]["fields"]["underlying_price"]["joinability_classification_counts"] == {
        "alias_present": 1
    }
    assert report["price_source_mapping"]["fields"]["target_price"]["joinability_classification_counts"] == {
        "alias_present": 1
    }


def test_event_driven_admission_simulation_maps_joinable_price_sources(tmp_path) -> None:
    base_dir = tmp_path / "quant_data"
    _write_event(
        base_dir,
        "market_snapshots",
        {
            "timestamp_utc": "2026-05-12T01:00:00Z",
            "run_id": "run-a",
            "payload": _snapshot_payload(current_price=None, price_to_beat=None),
        },
    )
    _write_event(
        base_dir,
        "decision_log",
        {
            "timestamp_utc": "2026-05-12T01:00:01Z",
            "run_id": "run-a",
            "payload": {
                "condition_id": "cond-1",
                "current_price": 100_005,
                "price_to_beat": 100_100,
            },
        },
    )

    report = build_event_driven_admission_simulation_report(date=DATE, base_dir=base_dir)
    mapping = report["price_source_mapping"]

    assert mapping["fields"]["underlying_price"]["joinability_classification_counts"] == {
        "joinable_from_metadata": 1
    }
    assert mapping["fields"]["target_price"]["joinability_classification_counts"] == {
        "joinable_from_metadata": 1
    }
    assert mapping["fields"]["underlying_price"]["same_market_join_sources"] == {"decision_log:current_price": 1}
    assert mapping["fields"]["target_price"]["same_market_join_sources"] == {"decision_log:price_to_beat": 1}
    assert mapping["offline_join_possible"] is True


def test_event_driven_admission_simulation_classifies_price_enrichment_drop_reasons(tmp_path) -> None:
    base_dir = tmp_path / "quant_data"
    _write_event(
        base_dir,
        "market_snapshots",
        {
            "timestamp_utc": "2026-05-12T01:00:00Z",
            "run_id": "run-a",
            "payload": _snapshot_payload(
                current_price=None,
                price_to_beat=None,
                packet_schema_version="event_driven_admission_packet_v1",
                price_enrichment_source="ptb_info",
                ptb_context_available=True,
                oracle_price_available=False,
                target_price_available=False,
                packet_schema_price_fields_present=False,
                enrichment_drop_reason="oracle_and_target_missing",
            ),
        },
    )

    report = build_event_driven_admission_simulation_report(date=DATE, base_dir=base_dir)
    diagnostics = report["packet_price_enrichment_diagnostics"]

    assert diagnostics["packets_with_ptb_context"] == 1
    assert diagnostics["packets_missing_propagation"] == 1
    assert diagnostics["packets_missing_source_fields"] == 0
    assert diagnostics["enrichment_drop_reason_counts"] == {"oracle_and_target_missing": 1}
    assert diagnostics["dominant_propagation_drop_reason"] == "oracle_and_target_missing"
    assert diagnostics["ptb_context_availability_counts"] == {"ptb_context_available_true": 1}
    assert diagnostics["oracle_context_availability_counts"] == {"oracle_price_available_false": 1}
    assert diagnostics["target_context_availability_counts"] == {"target_price_available_false": 1}
