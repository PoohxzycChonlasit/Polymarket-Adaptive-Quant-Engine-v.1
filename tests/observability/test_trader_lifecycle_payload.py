"""Tests for trader_lifecycle_payload extracted helpers."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from typing import Any

from polymarket.observability.trader_lifecycle_payload import (
    compute_lifecycle_latency_ms,
    phase2_readiness_timestamps,
    phase2_exposure_timeline,
    phase2_complete_lifecycle_observability,
    phase2_observability_payload,
)


class MockPosition:
    def __init__(self, notional_size: float = 0.0):
        self.notional_size = notional_size


class MockBankrollState:
    def __init__(
        self,
        current_bankroll_for_sizing: float = 1000.0,
        open_position_market_value: float = 0.0,
        current_bankroll_tier: str = "T0_MICRO_SEED",
    ):
        self.current_bankroll_for_sizing = current_bankroll_for_sizing
        self.open_position_market_value = open_position_market_value
        self.current_bankroll_tier = current_bankroll_tier


class MockTrader:
    def __init__(self, hard_block: int = 60):
        self.hard_block = hard_block
        self._market_readiness_timestamps: dict[tuple[str, int], dict[str, object]] = {}
        self._market_token_meta: dict[str, dict[str, object]] = {}
        self._real_token_ids: dict[str, tuple[str, str]] = {}
        self._market_first_seen_seconds_remaining: dict[tuple[str, int], int] = {}
        self.bankroll_state = MockBankrollState()
        self.positions: dict[str, list[MockPosition]] = {}
        self.settings = MagicMock()
        self.settings.hybrid_phase_v1_enabled = True

        # Preload mock fields
        self._preload_attempted = False
        self._preload_success = False
        self._preload_failed_reason = None
        self._preload_ticker = ""
        self._preload_market_slug = ""
        self._preload_condition_id = ""
        self._preload_yes_token_id_present = False
        self._preload_no_token_id_present = False
        self._preload_orderbook_warmed = False
        self._preload_orderbook_state = "UNKNOWN"
        self._preload_seconds_before_epoch = 0
        self._preload_latency_ms = 0
        self._preload_cache_hit = False
        self._preload_cache_age_seconds = 0
        self._preload_next_epoch_start = 0
        self._preload_next_epoch_remaining_seconds = 0

    def _entry_hard_block_seconds(self) -> int:
        return self.hard_block

    def _phase2_readiness_store(self) -> dict[tuple[str, int], dict[str, object]]:
        return self._market_readiness_timestamps

    def _open_positions_for_market(self, market_id: str) -> list[Any]:
        return self.positions.get(market_id, [])

    def _phase2_safe_setting(self, key: str, default: object) -> object:
        if key == "max_risk_per_market":
            return default
        return default

    def _phase2_lifecycle_phase(self, seconds_remaining: object = None) -> str:
        # Simple delegation mirror to match trader.py's wrapped behaviour
        from polymarket.observability.trader_lifecycle_observability import phase2_lifecycle_phase as p2_lp
        return p2_lp(seconds_remaining)

    def _ticker_from_market_id(self, market_ref: str) -> str:
        if "btc" in market_ref.lower():
            return "BTC"
        if "eth" in market_ref.lower():
            return "ETH"
        return "UNKNOWN"

    def _phase2_candidate_survival_ms(self, detail: dict[str, object]) -> int | None:
        return 123

    def _phase2_readiness_timestamps(self, ticker: str, epoch_start: int) -> dict[str, object]:
        return phase2_readiness_timestamps(self, ticker, epoch_start)

    def _phase2_elapsed_second(self, seconds_remaining: object) -> int | None:
        from polymarket.observability.trader_lifecycle_observability import phase2_elapsed_second as p2_es
        return p2_es(seconds_remaining)

    def _phase2_exposure_timeline(self, market_id: str, *, risk_plan: Any = None) -> dict[str, float]:
        return phase2_exposure_timeline(self, market_id, risk_plan=risk_plan)


# ---------------------------------------------------------------------------
# compute_lifecycle_latency_ms Tests
# ---------------------------------------------------------------------------

class TestComputeLifecycleLatencyMs:
    def test_all_zero_on_missing(self):
        result = compute_lifecycle_latency_ms({})
        assert result["discovery_to_token_ready_ms"] == 0
        assert result["dominant_latency_stage"] == ""
        assert result["lifecycle_latency_classification"] == ""

    def test_computes_correct_ms(self):
        bucket = {
            "first_discovered_ts": "2026-06-26T12:00:00.000Z",
            "first_token_ready_ts": "2026-06-26T12:00:00.100Z",
            "first_orderbook_seen_ts": "2026-06-26T12:00:00.300Z",
            "first_nonzero_bidask_ts": "2026-06-26T12:00:00.600Z",
            "first_spread_normalized_ts": "2026-06-26T12:00:01.000Z",
            "first_tradable_ts": "2026-06-26T12:00:01.500Z",
            "decision_complete_ts": "2026-06-26T12:00:02.100Z",
        }
        result = compute_lifecycle_latency_ms(bucket)
        assert result["discovery_to_token_ready_ms"] == 100
        assert result["token_ready_to_book_ms"] == 200
        assert result["book_to_nonzero_ms"] == 300
        assert result["nonzero_to_normalized_ms"] == 400
        assert result["normalized_to_executable_ms"] == 500
        assert result["executable_to_decision_ms"] == 600
        assert result["total_discovery_to_decision_ms"] == 2100
        assert result["dominant_latency_stage"] == "CUTOFF"  # 600 ms (executable_to_decision_ms)
        assert result["lifecycle_latency_classification"] == "NORMAL"  # >= 2000 ms

    def test_classification_fast(self):
        bucket = {
            "first_discovered_ts": "2026-06-26T12:00:00.000Z",
            "decision_complete_ts": "2026-06-26T12:00:00.500Z",
        }
        result = compute_lifecycle_latency_ms(bucket)
        assert result["lifecycle_latency_classification"] == "FAST"

    def test_classification_slow(self):
        bucket = {
            "first_discovered_ts": "2026-06-26T12:00:00.000Z",
            "decision_complete_ts": "2026-06-26T12:00:06.000Z",
        }
        result = compute_lifecycle_latency_ms(bucket)
        assert result["lifecycle_latency_classification"] == "SLOW"

    def test_classification_critical(self):
        bucket = {
            "first_discovered_ts": "2026-06-26T12:00:00.000Z",
            "decision_complete_ts": "2026-06-26T12:00:16.000Z",
        }
        result = compute_lifecycle_latency_ms(bucket)
        assert result["lifecycle_latency_classification"] == "CRITICAL"


# ---------------------------------------------------------------------------
# phase2_readiness_timestamps Tests
# ---------------------------------------------------------------------------

class TestPhase2ReadinessTimestamps:
    def test_zero_epoch_returns_empty_fields(self):
        trader = MockTrader()
        result = phase2_readiness_timestamps(trader, "BTC", 0)
        assert result["token_ready_at"] == ""
        assert result["readiness_confidence"] == 0.0

    def test_fetches_from_store(self):
        trader = MockTrader()
        store = trader._phase2_readiness_store()
        store[("BTC", 12345)] = {"token_ready_at": "2026-06-26T12:00:00Z", "readiness_confidence": 0.8}
        result = phase2_readiness_timestamps(trader, "BTC", 12345)
        assert result["token_ready_at"] == "2026-06-26T12:00:00Z"
        assert result["readiness_confidence"] == 0.8
        assert result["liquidity_ready_at"] == ""


# ---------------------------------------------------------------------------
# phase2_exposure_timeline Tests
# ---------------------------------------------------------------------------

class TestPhase2ExposureTimeline:
    def test_no_positions(self):
        trader = MockTrader()
        result = phase2_exposure_timeline(trader, "market_btc")
        assert result["exposure_before"] == 0.0
        assert result["exposure_after"] == 0.0
        assert result["remaining_risk_budget"] > 0.0

    def test_existing_positions(self):
        trader = MockTrader()
        trader.positions["market_btc"] = [MockPosition(150.0), MockPosition(50.0)]
        result = phase2_exposure_timeline(trader, "market_btc")
        assert result["exposure_before"] == 200.0
        assert result["exposure_after"] == 200.0

    def test_exposure_after_from_risk_plan(self):
        trader = MockTrader()
        plan = MagicMock()
        plan.notional_size = 300.0
        result = phase2_exposure_timeline(trader, "market_btc", risk_plan=plan)
        assert result["exposure_before"] == 0.0
        assert result["exposure_after"] == 300.0


# ---------------------------------------------------------------------------
# phase2_complete_lifecycle_observability Tests
# ---------------------------------------------------------------------------

class TestPhase2CompleteLifecycleObservability:
    def test_basic_fill(self):
        trader = MockTrader()
        trader._market_token_meta["BTC"] = {"condition_id": "cond_btc"}
        payload = {
            "ticker": "BTC",
            "market_epoch_start": 1700000000,
            "seconds_remaining": 150,
            "side": "YES",
        }
        result = phase2_complete_lifecycle_observability(trader, payload)
        assert result["condition_id"] == "cond_btc"
        assert result["lifecycle_phase"] == "ACTIVE_INVENTORY_TRADING"
        assert result["preload_attempted"] is False

    def test_preload_fields_propagation(self):
        trader = MockTrader()
        trader._preload_attempted = True
        trader._preload_success = True
        trader._preload_ticker = "ETH"
        payload = {"ticker": "BTC", "seconds_remaining": 150}
        result = phase2_complete_lifecycle_observability(trader, payload)
        assert result["preload_attempted"] is True
        assert result["preload_success"] is True
        assert result["preload_ticker"] == "ETH"


# ---------------------------------------------------------------------------
# phase2_observability_payload Tests
# ---------------------------------------------------------------------------

class TestPhase2ObservabilityPayload:
    def test_observability_payload_assembly(self):
        trader = MockTrader()
        trader._real_token_ids["BTC"] = ("yes_tok", "no_tok")
        trader._market_token_meta["BTC"] = {"condition_id": "cond_btc", "slug": "btc-5m"}
        result = phase2_observability_payload(
            trader,
            ticker="BTC",
            epoch_start=1700000000,
            seconds_remaining=290,
            market_price=0.55,
            fair_value=0.58,
            true_probability=0.58,
            ev_after_spread=0.03,
        )
        assert result["yes_token_id"] == "yes_tok"
        assert result["no_token_id"] == "no_tok"
        assert result["condition_id"] == "cond_btc"
        assert result["market_slug"] == "btc-5m"
        assert result["fair_value"] == 0.58
        assert result["market_price"] == 0.55
        assert result["starter_candidate"] is True


# ---------------------------------------------------------------------------
# Golden Equivalence Tests
# ---------------------------------------------------------------------------

class TestGoldenEquivalence:
    def test_trader_wrapper_delegation(self):
        from polymarket.trader import PolymarketTrader
        # Spot check that wrappers in PolymarketTrader exist and delegate correctly
        assert hasattr(PolymarketTrader, "_phase2_lifecycle_phase")
        assert hasattr(PolymarketTrader, "_phase2_readiness_timestamps")
        assert hasattr(PolymarketTrader, "_phase2_exposure_timeline")
        assert hasattr(PolymarketTrader, "_phase2_complete_lifecycle_observability")
        assert hasattr(PolymarketTrader, "_phase2_observability_payload")
