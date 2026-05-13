from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

from tools import operator_summary


def _summary() -> dict:
    return {
        "run_id": "run-operator",
        "time_range": {
            "date": "2026-05-12",
            "first_event_utc": "2026-05-12T01:00:00Z",
            "last_event_utc": "2026-05-12T01:10:00Z",
        },
        "source_inputs": {"events_loaded": 120},
        "paper_activity": {"orders": 3, "fills": 2, "exits": 1, "replay_total_trades": 2},
        "ev_visibility": {
            "ev_visibility_status": "EV_NEVER_VISIBLE",
            "EV_NEVER_VISIBLE": 8,
            "ev_visibility_confirmed": 0,
            "dominant_model_gap": "BLOCKED_BEFORE_MODEL",
        },
        "risk_layer_trace_readiness": 0.4595,
        "candidate_chain_trace_confidence": {"DIRECT": 4, "STRONG": 2, "WEAK": 1},
        "decision_cycle_orderbook_readiness_audit": {
            "decision_candidate_event_count": 31,
            "current_cycle_orderbook_ready_count": 0,
            "lifecycle_candidate_ready_count": 31,
            "dominant_decision_cycle_orderbook_blocker": "CURRENT_CYCLE_ORDERBOOK_NOT_COMPLETE",
        },
        "decision_runtime_eligibility_funnel": {
            "dominant_decision_path_blocker": "ORDERBOOK_COMPLETENESS_GATE",
            "stages": {
                "probability_model_called": {"survivor_count": 0},
                "model_output_visible": {"survivor_count": 0},
            },
        },
        "model_handoff_diagnostics": {
            "probability_model_call_counts": {"not_called": 31, "called": 0},
            "probability_model_output_visibility_counts": {"not_visible": 31, "visible": 0},
            "pre_model_gate_counts": {"ORDERBOOK_COMPLETENESS_GATE": 18, "TIME_CUTOFF_GATE": 3},
        },
        "orderbook_health": {"state_counts": {"ready": 44, "unavailable": 60, "empty_book": 14}},
        "global_vs_decision_orderbook_sync_audit": {
            "global_ready_event_count": 923,
            "decision_event_count": 31,
            "decision_ready_event_count": 0,
            "same_market_global_ready_before_decision_count": 179,
            "fresh_global_ready_before_decision_count": 4,
            "median_executable_window_age_ms": 61381,
            "synchronization_mismatch_classification": "GLOBAL_READY_DECISION_LOCAL_INCOMPLETE",
            "lifecycle_freshness_loss_counts": {"ACTIVE_INVENTORY_TRADING": 29, "FINAL_DERISK": 5},
            "latency_pipeline_decomposition": {
                "dominant_slow_stage": "candidate_ready_to_decision_event_created"
            },
        },
        "candidate_timing_diagnostics": {
            "lifecycle_transition_summary": {
                "active_candidate_ready_without_model_eligibility_count": 29,
                "final_derisk_before_model_output_count": 5,
            }
        },
        "root_cause_candidate": "EV_CHAIN_NOT_VISIBLE",
        "recommended_next_codex_patch_target": "decision-cycle orderbook readiness diagnostics",
    }


def test_operator_summary_renders_required_sections_and_metrics() -> None:
    text = operator_summary.render_operator_summary(_summary())

    for header in (
        "SYSTEM STATUS",
        "DECISION FUNNEL",
        "ORDERBOOK / FRESHNESS",
        "MODEL STATUS",
        "RISK / EV STATUS",
        "EXECUTION STATUS",
        "DOMINANT ROOT CAUSE",
        "RECOMMENDED NEXT ACTION",
    ):
        assert header in text
    assert "decision_ready_event_count: 0 / 31" in text
    assert "probability_model_called: 0" in text
    assert "model_output_visible: 0" in text
    assert "ev_visibility: EV_NEVER_VISIBLE" in text
    assert "risk_layer_trace_readiness: 0.4595" in text
    assert "freshness_decay_median: 61.38s" in text
    assert "global_vs_local_mismatch: GLOBAL_READY_DECISION_LOCAL_INCOMPLETE" in text
    assert "orders: 3 fills: 2 exits: 1 trades: 2" in text


def test_operator_summary_compact_is_section_sized() -> None:
    text = operator_summary.render_operator_summary(_summary(), compact=True)

    assert len(text.splitlines()) == 8
    assert "DECISION FUNNEL:" in text
    assert "decision_ready_event_count=0/31" in text
    assert "{" not in text
    assert "}" not in text


def test_operator_summary_telegram_is_single_compact_text_block() -> None:
    text = operator_summary.render_operator_summary(_summary(), telegram=True)

    assert "\n\n" not in text
    assert "FUNNEL decision_ready_event_count=0/31" in text
    assert "ROOT EV_CHAIN_NOT_VISIBLE" in text
    assert "{" not in text
    assert "}" not in text


def test_operator_summary_sanitizes_nested_action_for_operator_text() -> None:
    summary = _summary()
    summary["recommended_next_codex_patch_target"] = {
        "event_category": "execution_log",
        "missing_uncertain_ev_fields": 192,
        "share": 0.8,
    }

    text = operator_summary.render_operator_summary(summary, compact=True)

    assert "event_category=execution_log" in text
    assert "missing_uncertain_ev_fields=192" in text
    assert "{" not in text
    assert "}" not in text


def test_operator_summary_loads_json_path(monkeypatch) -> None:
    def fake_open(self, *args, **kwargs):  # noqa: ANN001
        return StringIO(json.dumps(_summary()))

    monkeypatch.setattr(Path, "open", fake_open)

    assert operator_summary.load_summary("compact_run_summary_2026-05-12.json")["run_id"] == "run-operator"


def test_operator_summary_cli_formats_loaded_summary(capsys, monkeypatch) -> None:
    monkeypatch.setattr(operator_summary, "load_summary", lambda _: _summary())

    assert operator_summary.main(["compact_run_summary_2026-05-12.json", "--compact"]) == 0
    output = capsys.readouterr().out

    assert "SYSTEM STATUS: run=run-operator" in output
    assert "RECOMMENDED NEXT ACTION: decision-cycle orderbook readiness diagnostics" in output
