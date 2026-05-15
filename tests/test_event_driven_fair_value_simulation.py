from __future__ import annotations

import json
from types import SimpleNamespace
from pathlib import Path

import tools.event_driven_fair_value_simulation as fair_value_sim
from tools.event_driven_fair_value_simulation import (
    build_event_driven_fair_value_cross_session_report,
    build_event_driven_fair_value_simulation_report,
    write_event_driven_fair_value_cross_session_report,
    write_event_driven_fair_value_simulation_report,
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
        "underlying_price": 100_200,
        "target_price": 100_000,
        "seconds_remaining": 200,
        "liquidity_state": "ready",
    }
    payload.update(overrides)
    return payload


def _write_snapshot(base_dir: Path, payload: dict, *, run_id: str = "run-a", timestamp: str = "2026-05-12T01:00:00Z") -> None:
    _write_event(
        base_dir,
        "market_snapshots",
        {
            "timestamp_utc": timestamp,
            "run_id": run_id,
            "payload": payload,
        },
    )


def test_event_driven_fair_value_simulation_computes_ev_and_lifecycle_groups(tmp_path) -> None:
    base_dir = tmp_path / "quant_data"
    report_dir = tmp_path / "reports"
    _write_snapshot(base_dir, _snapshot_payload())
    _write_snapshot(
        base_dir,
        _snapshot_payload(
            lifecycle_phase="PROFIT_MANAGEMENT",
            underlying_price=99_800,
            yes_bid=0.50,
            yes_ask=0.52,
            no_bid=0.47,
            no_ask=0.49,
        ),
    )

    report = build_event_driven_fair_value_simulation_report(date=DATE, base_dir=base_dir)
    path = write_event_driven_fair_value_simulation_report(report, report_dir=report_dir)

    assert path == report_dir / f"event_driven_fair_value_simulation_{DATE}.json"
    assert report["schema_version"] == "event_driven_fair_value_simulation_v1"
    assert report["guardrails"]["offline_only"] is True
    assert report["guardrails"]["runtime_behavior_changed"] is False
    assert report["guardrails"]["strategy_changed"] is False
    assert report["probability_method"]["name"] == "offline_placeholder_logistic_price_to_beat_v1"
    assert report["executable_liquidity_event_count"] == 2
    assert report["model_eligibility_would_be_reached_count"] == 2
    assert report["packets_with_full_ev_inputs"] == 2
    assert report["positive_ev_count"] == 2
    assert report["positive_ev_rate"] == 1.0
    assert report["liquidity_eligible_count"] == 2
    assert set(report["ev_distribution_by_lifecycle_phase"]) == {"ACTIVE_INVENTORY_TRADING", "PROFIT_MANAGEMENT"}


def test_event_driven_fair_value_simulation_excludes_missing_fields(tmp_path) -> None:
    base_dir = tmp_path / "quant_data"
    _write_snapshot(base_dir, _snapshot_payload(underlying_price=None, current_price=None))
    _write_snapshot(base_dir, _snapshot_payload(underlying_price=None, target_price=None, current_price=None))

    report = build_event_driven_fair_value_simulation_report(date=DATE, base_dir=base_dir)

    assert report["model_eligibility_would_be_reached_count"] == 2
    assert report["packets_with_full_ev_inputs"] == 0
    assert report["excluded_missing_price"] == 2
    assert report["missing_field_exclusions"] == {"underlying_price": 2, "target_price": 1}
    assert report["positive_ev_count"] == 0


def test_event_driven_fair_value_simulation_counts_spread_killed_packets(tmp_path) -> None:
    base_dir = tmp_path / "quant_data"
    _write_snapshot(
        base_dir,
        _snapshot_payload(
            underlying_price=100_100,
            target_price=100_000,
            yes_bid=0.55,
            yes_ask=0.64,
            no_bid=0.35,
            no_ask=0.44,
        ),
    )

    report = build_event_driven_fair_value_simulation_report(
        date=DATE,
        base_dir=base_dir,
        max_side_spread=0.10,
    )

    assert report["packets_with_full_ev_inputs"] == 1
    assert report["positive_ev_count"] == 0
    assert report["spread_killed_count"] == 1
    assert report["spread_kill_rate"] == 1.0


def test_event_driven_fair_value_simulation_keeps_gate_exclusions_offline(tmp_path) -> None:
    base_dir = tmp_path / "quant_data"
    _write_snapshot(base_dir, _snapshot_payload(lifecycle_phase="OPENING_SCAN"))
    _write_snapshot(base_dir, _snapshot_payload(orderbook_age_ms=6_000))

    report = build_event_driven_fair_value_simulation_report(date=DATE, base_dir=base_dir)

    assert report["executable_liquidity_event_count"] == 2
    assert report["model_eligibility_would_be_reached_count"] == 0
    assert report["gate_exclusions"] == {
        "lifecycle_window_ok": 1,
        "stale_executable_book": 1,
    }
    assert report["guardrails"]["simulation_wired_to_trading"] is False


def test_event_driven_fair_value_simulation_real_model_adapter_maps_inputs(tmp_path, monkeypatch) -> None:
    base_dir = tmp_path / "quant_data"
    captured = {}

    class StubInput:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    def fake_estimate_probability(model_input):
        assert model_input is not None
        return SimpleNamespace(
            p_yes=0.70,
            p_no=0.30,
            confidence_score=0.82,
            model_reason="stub_real_model",
            skipped=False,
            skip_reason="",
        )

    monkeypatch.setattr(fair_value_sim, "ProbabilityModelInput", StubInput)
    monkeypatch.setattr(fair_value_sim, "estimate_probability", fake_estimate_probability)
    monkeypatch.setattr(fair_value_sim, "REAL_MODEL_IMPORT_ERROR", "")
    _write_snapshot(base_dir, _snapshot_payload(liquidity=750.0, orderbook_age_ms=400))

    report = build_event_driven_fair_value_simulation_report(
        date=DATE,
        base_dir=base_dir,
        probability_method="real_model",
    )

    assert report["probability_method_requested"] == "real_model"
    assert report["probability_model_audit"]["real_model_safe_to_import_offline"] is True
    assert report["real_model_probability_available_count"] == 1
    assert report["positive_ev_count_real_model"] == 1
    assert report["probability_comparison"]["placeholder_packet_count"] == 1
    assert captured["underlying_price"] == 100_200
    assert captured["target_price"] == 100_000
    assert captured["time_remaining_seconds"] == 200
    assert captured["orderbook_bid"] == 0.47
    assert captured["orderbook_ask"] == 0.49
    assert captured["yes_ask"] == 0.49
    assert captured["no_ask"] == 0.52
    assert captured["liquidity"] == 750.0
    assert captured["data_age_seconds"] == 0.4


def test_event_driven_fair_value_simulation_compare_keeps_placeholder_and_real_model(tmp_path, monkeypatch) -> None:
    base_dir = tmp_path / "quant_data"

    class StubInput:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    def fake_estimate_probability(_model_input):
        return SimpleNamespace(
            p_yes=0.10,
            p_no=0.90,
            confidence_score=0.70,
            model_reason="stub_no_edge",
            skipped=False,
            skip_reason="",
        )

    monkeypatch.setattr(fair_value_sim, "ProbabilityModelInput", StubInput)
    monkeypatch.setattr(fair_value_sim, "estimate_probability", fake_estimate_probability)
    monkeypatch.setattr(fair_value_sim, "REAL_MODEL_IMPORT_ERROR", "")
    _write_snapshot(base_dir, _snapshot_payload())

    report = build_event_driven_fair_value_simulation_report(
        date=DATE,
        base_dir=base_dir,
        probability_method="compare",
    )

    comparison = report["probability_comparison"]
    assert report["probability_method_requested"] == "compare"
    assert comparison["placeholder_packet_count"] == 1
    assert comparison["real_model_packet_count"] == 1
    assert comparison["positive_ev_count_placeholder"] == 1
    assert comparison["positive_ev_count_real_model"] == 1
    assert comparison["average_ev_after_spread_real_model"] == 0.38


def test_event_driven_fair_value_simulation_real_model_unavailable_is_fail_soft(tmp_path, monkeypatch) -> None:
    base_dir = tmp_path / "quant_data"
    monkeypatch.setattr(fair_value_sim, "ProbabilityModelInput", None)
    monkeypatch.setattr(fair_value_sim, "estimate_probability", None)
    monkeypatch.setattr(fair_value_sim, "REAL_MODEL_IMPORT_ERROR", "ImportError: blocked")
    _write_snapshot(base_dir, _snapshot_payload())

    report = build_event_driven_fair_value_simulation_report(
        date=DATE,
        base_dir=base_dir,
        probability_method="real_model",
    )

    assert report["probability_model_audit"]["real_model_safe_to_import_offline"] is False
    assert report["real_model_probability_available_count"] == 0
    assert report["positive_ev_count"] == 0
    assert report["probability_comparison"]["placeholder_packet_count"] == 1
    assert report["model_error_counts"] == {"ImportError: blocked": 1}


def test_event_driven_fair_value_cross_session_filters_time_windows(tmp_path) -> None:
    base_dir = tmp_path / "quant_data"
    _write_snapshot(base_dir, _snapshot_payload(), run_id="run-a", timestamp="2026-05-12T01:00:00Z")
    _write_snapshot(base_dir, _snapshot_payload(), run_id="run-b", timestamp="2026-05-12T02:00:00Z")

    report = build_event_driven_fair_value_cross_session_report(
        date=DATE,
        base_dir=base_dir,
        since="01:30",
        until="02:30",
    )

    assert report["runs_windows_analyzed"] == 1
    assert report["windows_with_full_ev_inputs"] == 1
    assert report["run_ids_analyzed"] == ["run-b"]
    assert report["full_ev_input_packets_total"] == 1
    assert report["stability_classification"] == "INSUFFICIENT_COVERAGE"


def test_event_driven_fair_value_cross_session_filters_run_id(tmp_path) -> None:
    base_dir = tmp_path / "quant_data"
    _write_snapshot(base_dir, _snapshot_payload(), run_id="run-a")
    _write_snapshot(base_dir, _snapshot_payload(), run_id="run-b")

    report = build_event_driven_fair_value_cross_session_report(date=DATE, base_dir=base_dir, run_id="run-b")

    assert report["runs_windows_analyzed"] == 1
    assert report["run_ids_analyzed"] == ["run-b"]
    assert report["windows"][0]["run_id"] == "run-b"
    assert report["full_ev_input_packets_total"] == 1


def test_event_driven_fair_value_cross_session_classifies_robust_positive_ev(tmp_path) -> None:
    base_dir = tmp_path / "quant_data"
    report_dir = tmp_path / "reports"
    _write_snapshot(base_dir, _snapshot_payload(), run_id="run-a")
    _write_snapshot(base_dir, _snapshot_payload(underlying_price=100_250), run_id="run-b")

    report = build_event_driven_fair_value_cross_session_report(date=DATE, base_dir=base_dir)
    path = write_event_driven_fair_value_cross_session_report(report, report_dir=report_dir)

    assert path == report_dir / f"event_driven_fair_value_cross_session_{DATE}.json"
    assert report["schema_version"] == "event_driven_fair_value_cross_session_v1"
    assert report["guardrails"]["offline_only"] is True
    assert report["guardrails"]["runtime_behavior_changed"] is False
    assert report["guardrails"]["probability_model_logic_changed"] is False
    assert report["runs_windows_analyzed"] == 2
    assert report["windows_with_full_ev_inputs"] == 2
    assert report["full_ev_input_packets_total"] == 2
    assert report["positive_ev_count_real_model_total"] == 2
    assert report["stability_classification"] == "ROBUST_POSITIVE_EV_REPLAY"


def test_event_driven_fair_value_cross_session_empty_window_is_insufficient(tmp_path) -> None:
    base_dir = tmp_path / "quant_data"
    _write_snapshot(base_dir, _snapshot_payload(), run_id="run-a", timestamp="2026-05-12T01:00:00Z")

    report = build_event_driven_fair_value_cross_session_report(
        date=DATE,
        base_dir=base_dir,
        since="02:00",
        until="03:00",
    )

    assert report["source_events_loaded"] == 0
    assert report["runs_windows_analyzed"] == 0
    assert report["windows_with_full_ev_inputs"] == 0
    assert report["full_ev_input_packets_total"] == 0
    assert report["stability_classification"] == "INSUFFICIENT_COVERAGE"
