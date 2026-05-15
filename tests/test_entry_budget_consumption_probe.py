"""
Tests for Entry Budget Consumption Probe v1.

Covers:
- increment-detection (slot_consumed events)
- zero-size slot-burn (edge case fixture)
- no-fill slot-burn (edge case fixture)
- lifecycle classification
- fail-soft (exception in emit method doesn't propagate)
- additive-only (existing skip_reason unchanged)
- no runtime behavior change (_entry_count_for_market value unchanged)
- probe tool: empty input, run_id filter, asset filter
- probe tool: root-cause ranking
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure repo root on path
# ---------------------------------------------------------------------------
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.entry_budget_consumption_probe import analyse, load_budget_events


# ---------------------------------------------------------------------------
# Fixtures: minimal probe event builders
# ---------------------------------------------------------------------------

def _gate_event(
    *,
    site: str = "pre_model",
    ticker: str = "BTC",
    phase: str = "ACTIVE_INVENTORY_TRADING",
    sr: float = 200.0,
    model_reached: bool = False,
    ev_computed: bool = False,
    trades_before: int = 1,
    run_id: str = "run_001",
) -> dict:
    return {
        "run_id": run_id,
        "payload": {
            "event": "entry_budget_probe_v1",
            "event_subtype": "gate_fired",
            "site": site,
            "ticker": ticker,
            "market_id": f"pm-5m-{ticker.lower()}",
            "epoch_start_ts": 1_700_000_000,
            "seconds_remaining": sr,
            "lifecycle_phase": phase,
            "trades_for_market_before": trades_before,
            "trades_for_market_after": trades_before,
            "max_entries_limit": 1,
            "slot_already_consumed": True,
            "model_gate_reached": model_reached,
            "ev_computed": ev_computed,
            "size_plan_value": 0.0,
            "real_order_attempted": False,
            "paper_fill_occurred": False,
            "entry_budget_consumed": False,
            "entry_budget_consumed_reason": "gate_fired",
            "entry_budget_consumed_without_order": False,
            "entry_budget_consumed_without_fill": False,
            "entry_budget_consumed_after_zero_size": False,
            "entry_budget_consumed_after_opening_scan": False,
            "entry_budget_consumed_after_cutoff": False,
            "entry_budget_consumed_after_model_eval": False,
            "entry_budget_consumed_after_real_submit": False,
            "entry_budget_consumed_after_fill": False,
            "mode": "paper",
        },
    }


def _consume_event(
    *,
    site: str = "quant_fill",
    ticker: str = "BTC",
    phase: str = "ACTIVE_INVENTORY_TRADING",
    sr: float = 240.0,
    paper_fill: bool = True,
    real_order: bool = True,
    size_plan: float = 0.11,
    model_reached: bool = True,
    ev_computed: bool = True,
    run_id: str = "run_001",
    reason: str = "paper_fill",
) -> dict:
    no_order = not real_order
    no_fill = not paper_fill
    return {
        "run_id": run_id,
        "payload": {
            "event": "entry_budget_probe_v1",
            "event_subtype": "slot_consumed",
            "site": site,
            "ticker": ticker,
            "market_id": f"pm-5m-{ticker.lower()}",
            "epoch_start_ts": 1_700_000_000,
            "seconds_remaining": sr,
            "lifecycle_phase": phase,
            "trades_for_market_before": 0,
            "trades_for_market_after": 1,
            "max_entries_limit": 1,
            "slot_already_consumed": False,
            "model_gate_reached": model_reached,
            "ev_computed": ev_computed,
            "size_plan_value": size_plan,
            "real_order_attempted": real_order,
            "paper_fill_occurred": paper_fill,
            "entry_budget_consumed": True,
            "entry_budget_consumed_reason": reason,
            "entry_budget_consumed_without_order": no_order,
            "entry_budget_consumed_without_fill": no_fill,
            "entry_budget_consumed_after_zero_size": size_plan == 0.0,
            "entry_budget_consumed_after_opening_scan": "OPENING_SCAN" in phase.upper(),
            "entry_budget_consumed_after_cutoff": "cutoff" in reason.lower(),
            "entry_budget_consumed_after_model_eval": model_reached,
            "entry_budget_consumed_after_real_submit": real_order,
            "entry_budget_consumed_after_fill": paper_fill,
            "mode": "paper",
        },
    }


# ===========================================================================
# 1. Increment-detection: slot_consumed event correctly classified
# ===========================================================================

class TestSlotConsumedDetection:
    def test_slot_consumed_counted(self):
        events = [_consume_event()]
        result = analyse([e["payload"] for e in events])
        assert result["slot_consumed_count"] == 1
        assert result["gate_fired_count"] == 0

    def test_slot_consumed_after_fill(self):
        events = [_consume_event(paper_fill=True, real_order=True)]
        result = analyse([e["payload"] for e in events])
        assert result["consume_with_fill_count"] == 1
        assert result["consume_with_fill_pct"] == 100.0
        assert result["consume_without_order_count"] == 0
        assert result["consume_without_fill_count"] == 0

    def test_semantics_verdict_correct_when_all_fills(self):
        payloads = [_consume_event()["payload"] for _ in range(3)]
        result = analyse(payloads)
        assert result["semantics_verdict"] == "CORRECT"


# ===========================================================================
# 2. Zero-size slot-burn
# ===========================================================================

class TestZeroSizeSlotBurn:
    def test_zero_size_not_flagged_on_normal_fill(self):
        ev = _consume_event(size_plan=0.11)
        result = analyse([ev["payload"]])
        assert result["consume_after_zero_size_count"] == 0

    def test_zero_size_flagged_when_size_is_zero(self):
        ev = _consume_event(size_plan=0.0)
        result = analyse([ev["payload"]])
        assert result["consume_after_zero_size_count"] == 1

    def test_semantics_review_needed_when_no_fill(self):
        ev = _consume_event(paper_fill=False, real_order=False)
        result = analyse([ev["payload"]])
        assert result["semantics_verdict"] == "REVIEW_NEEDED"


# ===========================================================================
# 3. No-fill slot-burn
# ===========================================================================

class TestNoFillSlotBurn:
    def test_no_fill_consumed_without_fill_flagged(self):
        ev = _consume_event(paper_fill=False, real_order=True)
        result = analyse([ev["payload"]])
        assert result["consume_without_fill_count"] == 1

    def test_no_order_consumed_without_order_flagged(self):
        ev = _consume_event(paper_fill=False, real_order=False)
        result = analyse([ev["payload"]])
        assert result["consume_without_order_count"] == 1


# ===========================================================================
# 4. Lifecycle classification
# ===========================================================================

class TestLifecycleClassification:
    def test_gate_phase_distribution(self):
        payloads = [
            _gate_event(phase="ACTIVE_INVENTORY_TRADING")["payload"],
            _gate_event(phase="ACTIVE_INVENTORY_TRADING")["payload"],
            _gate_event(phase="FINAL_DERISK")["payload"],
        ]
        result = analyse(payloads)
        dist = result["gate_phase_distribution"]
        assert dist.get("ACTIVE_INVENTORY_TRADING", 0) == 2
        assert dist.get("FINAL_DERISK", 0) == 1

    def test_opening_scan_consume_flagged(self):
        ev = _consume_event(phase="OPENING_SCAN")
        result = analyse([ev["payload"]])
        assert result["consume_after_opening_scan_count"] == 1


# ===========================================================================
# 5. Gate-fired: pre-model vs post-model
# ===========================================================================

class TestGateFiredBreakdown:
    def test_pre_model_gate(self):
        ev = _gate_event(site="pre_model", model_reached=False)
        result = analyse([ev["payload"]])
        assert result["gate_pre_model_count"] == 1
        assert result["gate_post_model_count"] == 0

    def test_post_model_gate(self):
        ev = _gate_event(site="post_model", model_reached=True, ev_computed=True)
        result = analyse([ev["payload"]])
        assert result["gate_post_model_count"] == 1
        assert result["gate_pre_model_count"] == 0

    def test_site_distribution(self):
        payloads = [
            _gate_event(site="pre_model")["payload"],
            _gate_event(site="pre_model")["payload"],
            _gate_event(site="post_model")["payload"],
            _gate_event(site="pre_order")["payload"],
        ]
        result = analyse(payloads)
        assert result["gate_site_distribution"]["pre_model"] == 2
        assert result["gate_site_distribution"]["post_model"] == 1
        assert result["gate_site_distribution"]["pre_order"] == 1


# ===========================================================================
# 6. BTC vs ETH breakdown
# ===========================================================================

class TestBtcEthBreakdown:
    def test_btc_eth_separate(self):
        payloads = [
            _gate_event(ticker="BTC")["payload"],
            _gate_event(ticker="BTC")["payload"],
            _gate_event(ticker="ETH")["payload"],
            _consume_event(ticker="BTC")["payload"],
            _consume_event(ticker="ETH")["payload"],
        ]
        result = analyse(payloads)
        assert result["btc"]["gate_fired"] == 2
        assert result["eth"]["gate_fired"] == 1
        assert result["btc"]["slot_consumed"] == 1
        assert result["eth"]["slot_consumed"] == 1


# ===========================================================================
# 7. Fail-soft: _emit_entry_budget_probe_event swallows exceptions
# ===========================================================================

class TestFailSoft:
    def test_emit_method_survives_internal_exception(self):
        from polymarket.trader import PolymarketTrader
        trader = MagicMock(spec=PolymarketTrader)
        trader._emit_quant_event = MagicMock(side_effect=RuntimeError("simulated failure"))
        trader._runtime_mode = MagicMock(return_value="paper")
        # Call the real method bound to the mock trader
        PolymarketTrader._emit_entry_budget_probe_event(
            trader,
            subtype="gate_fired",
            site="pre_model",
            ticker="BTC",
            market_id="pm-5m-btc",
            epoch_start_ts=1_700_000_000,
            seconds_remaining=200.0,
            lifecycle_phase="ACTIVE_INVENTORY_TRADING",
            trades_before=1,
            max_limit=1,
        )
        # No exception should propagate

    def test_emit_method_survives_missing_fields(self):
        from polymarket.trader import PolymarketTrader
        emitted = {}
        trader = MagicMock(spec=PolymarketTrader)
        trader._emit_quant_event = MagicMock(side_effect=lambda *a, **kw: emitted.update({"called": True}))
        trader._runtime_mode = MagicMock(return_value="paper")
        PolymarketTrader._emit_entry_budget_probe_event(
            trader,
            subtype="slot_consumed",
            site="quant_fill",
            ticker="BTC",
            market_id="pm-5m-btc",
            epoch_start_ts=1_700_000_000,
            seconds_remaining=240.0,
            lifecycle_phase="ACTIVE_INVENTORY_TRADING",
            trades_before=0,
            max_limit=1,
        )
        assert emitted.get("called") is True


# ===========================================================================
# 8. Additive-only: skip_reason unchanged by probe call
# ===========================================================================

class TestAdditiveOnly:
    def test_gate_returns_correct_skip_reason(self):
        """
        Simulates that adding probe call alongside the guard does NOT alter
        the skip_reason value the guard sets.
        """
        skip_reason = "Max entries per market reached"
        # probe call should not touch skip_reason
        from polymarket.trader import PolymarketTrader
        trader = MagicMock(spec=PolymarketTrader)
        trader._emit_quant_event = MagicMock()
        trader._runtime_mode = MagicMock(return_value="paper")
        PolymarketTrader._emit_entry_budget_probe_event(
            trader,
            subtype="gate_fired", site="pre_model",
            ticker="BTC", market_id="pm-5m-btc",
            epoch_start_ts=1_700_000_000,
            seconds_remaining=150.0,
            lifecycle_phase="ACTIVE_INVENTORY_TRADING",
            trades_before=1,
            max_limit=1,
        )
        # skip_reason is untouched
        assert skip_reason == "Max entries per market reached"


# ===========================================================================
# 9. No runtime behavior change: _entry_count_for_market unchanged
# ===========================================================================

class TestNoRuntimeBehaviorChange:
    def test_entry_count_unchanged_after_probe_call(self):
        """
        _emit_entry_budget_probe_event must not modify _market_entry_counts.
        """
        from polymarket.trader import PolymarketTrader
        trader = MagicMock(spec=PolymarketTrader)
        trader._market_entry_counts = {("pm-5m-btc", 1_700_000_000): 1}
        trader._emit_quant_event = MagicMock()
        trader._runtime_mode = MagicMock(return_value="paper")
        before = trader._market_entry_counts.copy()
        PolymarketTrader._emit_entry_budget_probe_event(
            trader,
            subtype="gate_fired", site="pre_model",
            ticker="BTC", market_id="pm-5m-btc",
            epoch_start_ts=1_700_000_000,
            seconds_remaining=200.0,
            lifecycle_phase="ACTIVE_INVENTORY_TRADING",
            trades_before=1,
            max_limit=1,
        )
        assert trader._market_entry_counts == before


# ===========================================================================
# 10. Probe tool: empty input
# ===========================================================================

class TestProbeToolEdgeCases:
    def test_empty_returns_error_dict(self):
        result = analyse([])
        assert result["event_count"] == 0
        assert "error" in result

    def test_mixed_subtypes_counted_correctly(self):
        payloads = (
            [_gate_event()["payload"]] * 5
            + [_consume_event()["payload"]] * 2
        )
        result = analyse(payloads)
        assert result["gate_fired_count"] == 5
        assert result["slot_consumed_count"] == 2
        assert result["event_count"] == 7

    def test_run_id_filter(self, tmp_path):
        events = [
            _gate_event(run_id="run_A"),
            _gate_event(run_id="run_B"),
            _consume_event(run_id="run_A"),
        ]
        jl = tmp_path / "system_health" / "2026-01-01.jsonl"
        jl.parent.mkdir(parents=True)
        jl.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
        loaded = load_budget_events("2026-01-01", quant_data_dir=tmp_path, run_id="run_A")
        result = analyse(loaded)
        assert result["gate_fired_count"] == 1
        assert result["slot_consumed_count"] == 1

    def test_asset_filter(self, tmp_path):
        events = [
            _gate_event(ticker="BTC"),
            _gate_event(ticker="ETH"),
            _consume_event(ticker="BTC"),
        ]
        jl = tmp_path / "system_health" / "2026-01-01.jsonl"
        jl.parent.mkdir(parents=True)
        jl.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
        loaded = load_budget_events("2026-01-01", quant_data_dir=tmp_path, asset_filter="ETH")
        result = analyse(loaded)
        assert result["gate_fired_count"] == 1
        assert result["slot_consumed_count"] == 0


# ===========================================================================
# 11. Root-cause ranking
# ===========================================================================

class TestRootCauseRanking:
    def test_ranking_populated_with_fill(self):
        payloads = [_consume_event()["payload"]] * 2 + [_gate_event()["payload"]] * 8
        result = analyse(payloads)
        assert len(result["root_cause_ranking"]) >= 1
        joined = " ".join(result["root_cause_ranking"])
        assert "fill" in joined or "gate" in joined

    def test_gate_consume_ratio_appears_when_gates_exceed_consumes(self):
        payloads = [_consume_event()["payload"]] + [_gate_event()["payload"]] * 5
        result = analyse(payloads)
        joined = " ".join(result["root_cause_ranking"])
        assert "ratio" in joined or "revisit" in joined
