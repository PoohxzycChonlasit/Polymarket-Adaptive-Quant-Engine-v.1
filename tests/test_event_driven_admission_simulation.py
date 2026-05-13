from __future__ import annotations

import json
from pathlib import Path

from tools.event_driven_admission_simulation import (
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
