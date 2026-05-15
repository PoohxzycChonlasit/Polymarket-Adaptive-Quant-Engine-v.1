"""
Tests for Market Readiness Admission Probe v1.

Coverage:
- classify_admission_probe: probe state classification
- first_executable_before_cutoff derivation
- cutoff_policy_state classification
- admission_block_stage ordering
- model/ev/risk gate detection
- missing-data / fail-soft behaviour
- aggregate() structure and key metrics
- cutoff_passed correlation
- BTC vs ETH comparison
- lifecycle_phase distribution
- extract_record: runtime-emitted probe passthrough
- no runtime modification assertions
- paper/live separation unchanged
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from utils.admission_probe_classifier import (
    classify_admission_probe,
    _unknown_defaults,
)
from tools.market_readiness_admission_probe import (
    aggregate,
    extract_record,
    load_decision_events,
    render_console,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_payload(**overrides) -> dict:
    """Typical cutoff-blocked event — times out at end, no model reached."""
    base = {
        "asset": "BTC",
        "lifecycle_phase": "FINAL_DERISK",
        "seconds_remaining": 1,
        "entry_cutoff_seconds": 90,
        "effective_cutoff_seconds": 90,
        "first_tradable_seconds_remaining": 0,
        "first_evaluable_seconds_remaining": 0,
        "first_seen_seconds_remaining": 5,
        "executable_book_state": "TOKEN_READY",
        "model_attempted": False,
        "probability_model_output_visible": False,
        "fair_value_available": False,
        "true_probability_available": False,
        "ev_after_spread_available": False,
        "ev_after_spread": None,
        "calculated_order_size": 0.0,
        "risk_per_trade": 0.0,
        "late_entry_hard_block": True,
        "normalized_skip_reason": "time_unsafe",
        "skip_reason_category": "timing",
        "skip_reason_primary": "cutoff_passed",
        "model_activation_block_reason": "hard_close_zone",
    }
    base.update(overrides)
    return base


def _exec_payload(**overrides) -> dict:
    """Event where first_executable occurred before cutoff but model never ran."""
    base = _base_payload()
    base.update({
        "seconds_remaining": 50,
        "effective_cutoff_seconds": 35,
        "first_tradable_seconds_remaining": 200,  # well before 35s cutoff
        "executable_book_state": "TOKEN_READY",
        "late_entry_hard_block": False,
        "normalized_skip_reason": "time_unsafe",
    })
    base.update(overrides)
    return base


def _event(payload: dict, *, asset: str = "BTC", run_id: str = "r1") -> dict:
    payload["asset"] = asset
    return {"payload": payload, "run_id": run_id}


# ---------------------------------------------------------------------------
# classify_admission_probe: basic probes
# ---------------------------------------------------------------------------

class TestClassifyAdmissionProbe:
    def test_returns_all_keys(self):
        result = classify_admission_probe(_base_payload())
        expected = {
            "readiness_before_cutoff", "first_executable_before_cutoff",
            "admission_probe_state", "admission_probe_reason",
            "admission_block_stage", "model_gate_reached",
            "ev_gate_reached", "risk_gate_reached",
            "candidate_seen_before_cutoff", "candidate_evaluable_before_cutoff",
            "cutoff_policy_state", "effective_cutoff_seconds",
        }
        assert set(result.keys()) == expected

    def test_empty_payload_returns_unknown_defaults(self):
        result = classify_admission_probe({})
        # Should not raise; should return defaults
        assert result["admission_probe_state"] in {"UNKNOWN", "LATE_DISCOVERY", "TOKEN_READY_NOT_EXECUTABLE",
                                                    "CUTOFF_HARD_BLOCK", "EXECUTABLE_BEFORE_CUTOFF_NO_MODEL",
                                                    "SEEN_NOT_EXECUTABLE_BEFORE_CUTOFF", "EXECUTABLE_EVALUATED",
                                                    "EXECUTABLE_BEFORE_CUTOFF_NO_EV"}

    def test_hard_block_no_exec_gives_cutoff_hard_block(self):
        p = _base_payload(
            late_entry_hard_block=True,
            first_tradable_seconds_remaining=0,
        )
        result = classify_admission_probe(p)
        assert result["cutoff_policy_state"] == "HARD_BLOCK"
        assert result["admission_probe_state"] == "CUTOFF_HARD_BLOCK"
        assert result["first_executable_before_cutoff"] is False

    def test_exec_before_cutoff_no_model(self):
        p = _exec_payload()
        result = classify_admission_probe(p)
        assert result["first_executable_before_cutoff"] is True
        assert result["model_gate_reached"] is False
        assert result["admission_probe_state"] == "EXECUTABLE_BEFORE_CUTOFF_NO_MODEL"

    def test_exec_before_cutoff_model_reached_no_ev(self):
        p = _exec_payload(
            model_attempted=True,
            probability_model_output_visible=True,
            fair_value_available=False,
            ev_after_spread_available=False,
            ev_after_spread=None,
        )
        result = classify_admission_probe(p)
        assert result["first_executable_before_cutoff"] is True
        assert result["model_gate_reached"] is True
        assert result["ev_gate_reached"] is False
        assert result["admission_probe_state"] == "EXECUTABLE_BEFORE_CUTOFF_NO_EV"

    def test_exec_before_cutoff_ev_reached(self):
        p = _exec_payload(
            model_attempted=True,
            fair_value_available=True,
            ev_after_spread_available=True,
            ev_after_spread=0.02,
        )
        result = classify_admission_probe(p)
        assert result["first_executable_before_cutoff"] is True
        assert result["ev_gate_reached"] is True
        assert result["admission_probe_state"] == "EXECUTABLE_EVALUATED"

    def test_zero_first_tradable_not_executable(self):
        p = _base_payload(first_tradable_seconds_remaining=0)
        result = classify_admission_probe(p)
        assert result["first_executable_before_cutoff"] is False

    def test_first_tradable_equal_cutoff_not_executable(self):
        # exactly at cutoff is NOT before cutoff
        p = _base_payload(
            first_tradable_seconds_remaining=90,
            effective_cutoff_seconds=90,
        )
        result = classify_admission_probe(p)
        assert result["first_executable_before_cutoff"] is False

    def test_first_tradable_above_cutoff_is_executable(self):
        p = _base_payload(
            first_tradable_seconds_remaining=91,
            effective_cutoff_seconds=90,
            late_entry_hard_block=False,
        )
        result = classify_admission_probe(p)
        assert result["first_executable_before_cutoff"] is True

    def test_token_ready_state_admission_block(self):
        p = _base_payload(
            executable_book_state="TOKEN_READY",
            first_tradable_seconds_remaining=0,
            late_entry_hard_block=False,
            seconds_remaining=200,
        )
        result = classify_admission_probe(p)
        assert result["admission_block_stage"] == "ORDERBOOK"

    def test_discovered_state_admission_block(self):
        p = _base_payload(
            executable_book_state="DISCOVERED",
            first_tradable_seconds_remaining=0,
            late_entry_hard_block=False,
            seconds_remaining=200,
        )
        result = classify_admission_probe(p)
        assert result["admission_block_stage"] == "TOKEN"

    def test_nonzero_book_state_admission_block(self):
        p = _base_payload(
            executable_book_state="NONZERO_BOOK",
            first_tradable_seconds_remaining=0,
            late_entry_hard_block=False,
            seconds_remaining=200,
        )
        result = classify_admission_probe(p)
        assert result["admission_block_stage"] == "NORMALIZATION"

    def test_model_gate_block(self):
        p = _exec_payload(
            executable_book_state="SPREAD_NORMALIZED",
            model_attempted=False,
        )
        result = classify_admission_probe(p)
        assert result["admission_block_stage"] == "MODEL_GATE"

    def test_ev_gate_block(self):
        p = _exec_payload(
            executable_book_state="SPREAD_NORMALIZED",
            model_attempted=True,
            probability_model_output_visible=True,
            ev_after_spread_available=False,
            fair_value_available=False,
            ev_after_spread=None,
        )
        result = classify_admission_probe(p)
        assert result["admission_block_stage"] == "EV_GATE"

    def test_risk_gate_block(self):
        p = _exec_payload(
            executable_book_state="SPREAD_NORMALIZED",
            model_attempted=True,
            probability_model_output_visible=True,
            ev_after_spread_available=True,
            ev_after_spread=0.02,
            fair_value_available=True,
            calculated_order_size=0.0,
            risk_per_trade=0.0,
        )
        result = classify_admission_probe(p)
        assert result["admission_block_stage"] == "RISK_GATE"

    def test_none_block_when_all_gates_passed(self):
        p = _exec_payload(
            executable_book_state="SPREAD_NORMALIZED",
            model_attempted=True,
            probability_model_output_visible=True,
            ev_after_spread_available=True,
            ev_after_spread=0.02,
            fair_value_available=True,
            calculated_order_size=10.0,
        )
        result = classify_admission_probe(p)
        assert result["admission_block_stage"] == "NONE"

    def test_cutoff_policy_soft_block(self):
        p = _base_payload(
            seconds_remaining=50,
            effective_cutoff_seconds=90,
            late_entry_hard_block=False,
        )
        result = classify_admission_probe(p)
        assert result["cutoff_policy_state"] == "SOFT_BLOCK"

    def test_cutoff_policy_open(self):
        p = _base_payload(
            seconds_remaining=200,
            effective_cutoff_seconds=90,
            late_entry_hard_block=False,
        )
        result = classify_admission_probe(p)
        assert result["cutoff_policy_state"] == "OPEN"

    def test_seen_before_cutoff(self):
        p = _base_payload(
            first_seen_seconds_remaining=150,
            effective_cutoff_seconds=90,
        )
        result = classify_admission_probe(p)
        assert result["candidate_seen_before_cutoff"] is True

    def test_not_seen_before_cutoff_zero(self):
        p = _base_payload(first_seen_seconds_remaining=0)
        result = classify_admission_probe(p)
        assert result["candidate_seen_before_cutoff"] is False

    def test_model_gate_reached_via_true_prob_available(self):
        p = _exec_payload(true_probability_available=True)
        result = classify_admission_probe(p)
        assert result["model_gate_reached"] is True

    def test_ev_gate_reached_via_nonzero_ev(self):
        p = _exec_payload(ev_after_spread=0.05, ev_after_spread_available=False)
        result = classify_admission_probe(p)
        assert result["ev_gate_reached"] is True

    def test_risk_gate_reached_via_risk_per_trade(self):
        p = _exec_payload(risk_per_trade=5.0, calculated_order_size=0.0)
        result = classify_admission_probe(p)
        assert result["risk_gate_reached"] is True

    def test_fail_soft_on_exception(self):
        # Passing a non-dict should not raise
        result = classify_admission_probe(None)  # type: ignore
        assert result == _unknown_defaults()

    def test_probe_reason_includes_exec_timing(self):
        p = _exec_payload()
        result = classify_admission_probe(p)
        assert "first_exec_at_200s" in result["admission_probe_reason"]

    def test_probe_reason_includes_model_block(self):
        p = _exec_payload(model_activation_block_reason="hard_close_zone")
        result = classify_admission_probe(p)
        assert "model_blocked:hard_close_zone" in result["admission_probe_reason"]

    def test_does_not_mutate_payload(self):
        import copy
        p = _exec_payload()
        original = copy.deepcopy(p)
        classify_admission_probe(p)
        assert p == original

    def test_effective_cutoff_returned(self):
        p = _base_payload(effective_cutoff_seconds=45)
        result = classify_admission_probe(p)
        assert result["effective_cutoff_seconds"] == 45


# ---------------------------------------------------------------------------
# extract_record: passthrough of runtime-emitted probe fields
# ---------------------------------------------------------------------------

class TestExtractRecord:
    def test_uses_offline_classifier_when_no_probe_fields(self):
        event = _event(_exec_payload())
        record = extract_record(event)
        assert record["first_executable_before_cutoff"] is True
        assert record["admission_probe_state"] == "EXECUTABLE_BEFORE_CUTOFF_NO_MODEL"

    def test_uses_runtime_fields_when_present(self):
        p = _exec_payload()
        p["admission_probe_state"] = "EXECUTABLE_EVALUATED"
        p["first_executable_before_cutoff"] = True
        p["model_gate_reached"] = True
        p["ev_gate_reached"] = True
        p["risk_gate_reached"] = False
        p["cutoff_policy_state"] = "OPEN"
        p["admission_block_stage"] = "RISK_GATE"
        p["admission_probe_reason"] = "runtime_reason"
        p["readiness_before_cutoff"] = True
        p["candidate_seen_before_cutoff"] = True
        p["candidate_evaluable_before_cutoff"] = False
        p["effective_cutoff_seconds"] = 35
        event = _event(p)
        record = extract_record(event)
        assert record["admission_probe_state"] == "EXECUTABLE_EVALUATED"
        assert record["model_gate_reached"] is True

    def test_asset_forwarded(self):
        event = _event(_exec_payload(), asset="ETH")
        record = extract_record(event)
        assert record["asset"] == "ETH"

    def test_lifecycle_phase_forwarded(self):
        p = _exec_payload(lifecycle_phase="OPENING_SCAN")
        event = _event(p)
        record = extract_record(event)
        assert record["lifecycle_phase"] == "OPENING_SCAN"


# ---------------------------------------------------------------------------
# aggregate
# ---------------------------------------------------------------------------

class TestAggregate:
    def _make_records(self, n_exec_no_model=0, n_cutoff=0, n_evaluated=0,
                      asset="BTC", phase="FINAL_DERISK"):
        recs = []
        for _ in range(n_exec_no_model):
            recs.append(extract_record(_event(_exec_payload(
                lifecycle_phase=phase,
                skip_reason_category="timing",
                skip_reason_primary="cutoff_passed",
                normalized_skip_reason="time_unsafe",
            ), asset=asset)))
        for _ in range(n_cutoff):
            recs.append(extract_record(_event(_base_payload(
                lifecycle_phase=phase,
            ), asset=asset)))
        for _ in range(n_evaluated):
            p = _exec_payload(
                lifecycle_phase=phase,
                model_attempted=True,
                fair_value_available=True,
                ev_after_spread_available=True,
                ev_after_spread=0.02,
                skip_reason_category="evidence",
                normalized_skip_reason="ev_negative",
            )
            recs.append(extract_record(_event(p, asset=asset)))
        return recs

    def test_empty_returns_no_data(self):
        result = aggregate([])
        assert result["total_events"] == 0

    def test_total_events(self):
        recs = self._make_records(n_exec_no_model=3, n_cutoff=2)
        result = aggregate(recs)
        assert result["total_events"] == 5

    def test_required_keys_present(self):
        recs = self._make_records(n_exec_no_model=1)
        result = aggregate(recs)
        required = {
            "total_events", "exec_before_cutoff_count", "exec_before_cutoff_pct",
            "exec_before_cutoff_no_model_count", "exec_before_cutoff_no_model_pct",
            "admission_probe_state_distribution", "admission_block_stage_distribution",
            "gate_funnel", "asset_breakdown", "cutoff_passed_correlation",
            "lifecycle_phase_probe_distribution", "first_executable_timing_seconds_remaining",
            "cutoff_policy_distribution",
        }
        assert required.issubset(result.keys())

    def test_exec_before_cutoff_count(self):
        recs = self._make_records(n_exec_no_model=3, n_cutoff=2)
        result = aggregate(recs)
        assert result["exec_before_cutoff_count"] == 3

    def test_exec_before_cutoff_no_model_count(self):
        recs = self._make_records(n_exec_no_model=4, n_cutoff=1)
        result = aggregate(recs)
        assert result["exec_before_cutoff_no_model_count"] == 4

    def test_gate_funnel_keys(self):
        recs = self._make_records(n_exec_no_model=2)
        result = aggregate(recs)
        gf = result["gate_funnel"]
        for k in ("total", "executable_before_cutoff", "model_gate_reached",
                  "ev_gate_reached", "risk_gate_reached"):
            assert k in gf

    def test_model_gate_reached_count(self):
        recs = self._make_records(n_exec_no_model=2, n_evaluated=2)
        result = aggregate(recs)
        # n_evaluated events have model_attempted=True
        assert result["gate_funnel"]["model_gate_reached"] == 2

    def test_asset_breakdown_btc_eth(self):
        btc_recs = self._make_records(n_exec_no_model=3, asset="BTC")
        eth_recs = self._make_records(n_cutoff=2, asset="ETH")
        result = aggregate(btc_recs + eth_recs)
        ab = result["asset_breakdown"]
        assert "BTC" in ab
        assert "ETH" in ab
        assert ab["BTC"]["exec_before_cutoff"] == 3
        assert ab["ETH"]["exec_before_cutoff"] == 0

    def test_cutoff_passed_correlation(self):
        recs = self._make_records(n_exec_no_model=5, n_cutoff=3)
        result = aggregate(recs)
        cc = result["cutoff_passed_correlation"]
        assert cc["total_cutoff_events"] > 0
        # exec_before_cutoff events have timing skip reason too
        assert cc["exec_before_cutoff_in_cutoff_events"] == 5

    def test_lifecycle_phase_distribution(self):
        recs = (
            self._make_records(n_exec_no_model=2, phase="FINAL_DERISK")
            + self._make_records(n_cutoff=2, phase="OPENING_SCAN")
        )
        result = aggregate(recs)
        lc = result["lifecycle_phase_probe_distribution"]
        assert "FINAL_DERISK" in lc
        assert "OPENING_SCAN" in lc

    def test_first_executable_timing_populated(self):
        recs = self._make_records(n_exec_no_model=5)
        result = aggregate(recs)
        et = result["first_executable_timing_seconds_remaining"]
        assert et["count"] == 5
        assert et["min"] == 200
        assert et["max"] == 200

    def test_does_not_mutate_records(self):
        import copy
        recs = self._make_records(n_exec_no_model=2)
        original = copy.deepcopy(recs)
        aggregate(recs)
        assert recs == original


# ---------------------------------------------------------------------------
# load_decision_events filtering
# ---------------------------------------------------------------------------

class TestLoadDecisionEvents:
    def _write(self, path: Path, events: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")

    def test_nonexistent_file_empty(self, tmp_path):
        assert load_decision_events("2099-01-01", tmp_path / "qd") == []

    def test_run_id_filter(self, tmp_path):
        qd = tmp_path / "qd"
        self._write(qd / "decision_log" / "2026-05-15.jsonl", [
            {"run_id": "r1", "payload": {"asset": "BTC"}},
            {"run_id": "r2", "payload": {"asset": "BTC"}},
        ])
        events = load_decision_events("2026-05-15", qd, run_id="r1")
        assert len(events) == 1

    def test_asset_filter(self, tmp_path):
        qd = tmp_path / "qd"
        self._write(qd / "decision_log" / "2026-05-15.jsonl", [
            {"run_id": "r1", "payload": {"asset": "BTC"}},
            {"run_id": "r1", "payload": {"asset": "ETH"}},
        ])
        events = load_decision_events("2026-05-15", qd, asset_filter="ETH")
        assert len(events) == 1


# ---------------------------------------------------------------------------
# render_console smoke
# ---------------------------------------------------------------------------

class TestRenderConsole:
    def test_no_data(self, capsys):
        render_console({"total_events": 0}, "2026-05-15", False)
        out = capsys.readouterr().out
        assert "No decision events" in out

    def test_renders_with_data(self, capsys):
        recs = [
            extract_record(_event(_exec_payload(lifecycle_phase="FINAL_DERISK",
                                                skip_reason_category="timing",
                                                normalized_skip_reason="time_unsafe")))
            for _ in range(3)
        ] + [
            extract_record(_event(_base_payload(lifecycle_phase="FINAL_DERISK")))
            for _ in range(2)
        ]
        summary = aggregate(recs)
        render_console(summary, "2026-05-15", False)
        out = capsys.readouterr().out
        assert "Market Readiness Admission Probe" in out
        assert "EXECUTABLE_BEFORE_CUTOFF_NO_MODEL" in out

    def test_hybrid_flag_shown(self, capsys):
        recs = [extract_record(_event(_exec_payload()))]
        summary = aggregate(recs)
        render_console(summary, "2026-05-15", True)
        out = capsys.readouterr().out
        assert "YES" in out


# ---------------------------------------------------------------------------
# Additive-only / no runtime modification
# ---------------------------------------------------------------------------

class TestAdditiveOnly:
    def test_classifier_no_runtime_imports(self):
        import utils.admission_probe_classifier as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        forbidden = ["polymarket.trader", "utils.risk_manager", "order_manager",
                     "virtual_ptb", "live_order", "execute_order"]
        for token in forbidden:
            assert token not in source

    def test_tool_no_runtime_imports(self):
        import tools.market_readiness_admission_probe as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        forbidden = ["polymarket.trader", "utils.risk_manager", "order_manager",
                     "virtual_ptb", "live_order", "execute_order"]
        for token in forbidden:
            assert token not in source

    def test_probe_fields_all_12(self):
        result = classify_admission_probe(_base_payload())
        assert len(result) == 12

    def test_unknown_defaults_all_12(self):
        assert len(_unknown_defaults()) == 12

    def test_trader_py_additive_pattern(self):
        source = Path(_repo_root / "polymarket" / "trader.py").read_text(encoding="utf-8")
        assert "Market Readiness Admission Probe v1" in source
        assert "classify_admission_probe" in source
        assert "if _k not in payload or payload[_k] in (None" in source

    def test_paper_live_separation_unaffected(self):
        source = Path(_repo_root / "polymarket" / "trader.py").read_text(encoding="utf-8")
        assert "arb_auto_execute" in source
        assert "paper_trading" in source
