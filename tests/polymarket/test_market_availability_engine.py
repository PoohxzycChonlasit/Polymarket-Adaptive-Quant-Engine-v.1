"""Tests for MarketAvailabilityEngine and related wiring.

All tests are purely offline — no real HTTP calls.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from polymarket.market_availability_engine import (
    MarketAvailabilityEngine,
    MarketAvailabilityResult,
    MarketAvailabilityState,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _engine(**kwargs) -> MarketAvailabilityEngine:
    """Engine with aggressive cache TTL for testing."""
    defaults = dict(
        cache_ttl_sec=0,
        between_epochs_sleep_sec=15,
        not_scheduled_sleep_sec=300,
        api_unavailable_base_sleep_sec=60,
        api_unavailable_max_sleep_sec=600,
    )
    defaults.update(kwargs)
    return MarketAvailabilityEngine(**defaults)


def _market(
    slug: str = "btc-updown-5m-1782565800",
    active: bool = True,
    accepting: bool = True,
    bid: float = 0.48,
    ask: float = 0.52,
) -> dict:
    return {
        "slug": slug,
        "active": active,
        "acceptingOrders": accepting,
        "bestBid": bid,
        "bestAsk": ask,
    }


def _mock_response(markets: list[dict], status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = markets
    return resp


# ---------------------------------------------------------------------------
# State detection tests
# ---------------------------------------------------------------------------

class TestMarketAvailabilityStates:
    def test_active_state(self):
        engine = _engine()
        markets = [_market("btc-updown-5m-1782565800", bid=0.48, ask=0.52)]
        with patch("polymarket.market_availability_engine._requests.get",
                   return_value=_mock_response(markets)):
            result = engine.check()
        assert result.state == MarketAvailabilityState.ACTIVE
        assert result.active_market_count == 1
        assert result.is_active()
        assert not result.should_skip_scan()
        assert "BTC" in result.symbols_available

    def test_active_state_eth(self):
        engine = _engine()
        markets = [_market("eth-updown-5m-1782565800", bid=0.45, ask=0.55)]
        with patch("polymarket.market_availability_engine._requests.get",
                   return_value=_mock_response(markets)):
            result = engine.check()
        assert result.state == MarketAvailabilityState.ACTIVE
        assert "ETH" in result.symbols_available

    def test_active_state_both_symbols(self):
        engine = _engine()
        markets = [
            _market("btc-updown-5m-1782565800"),
            _market("eth-updown-5m-1782565800"),
        ]
        with patch("polymarket.market_availability_engine._requests.get",
                   return_value=_mock_response(markets)):
            result = engine.check()
        assert result.state == MarketAvailabilityState.ACTIVE
        assert sorted(result.symbols_available) == ["BTC", "ETH"]
        assert result.btc_market_count == 1
        assert result.eth_market_count == 1

    def test_between_epochs(self):
        engine = _engine()
        # Market exists but orderbook is empty (bid=0, ask=0)
        markets = [_market("btc-updown-5m-1782565800", bid=0.0, ask=0.0)]
        with patch("polymarket.market_availability_engine._requests.get",
                   return_value=_mock_response(markets)):
            result = engine.check()
        assert result.state == MarketAvailabilityState.BETWEEN_EPOCHS
        assert result.active_market_count == 0
        assert result.should_skip_scan()
        assert result.next_check_seconds == 15

    def test_between_epochs_not_accepting_orders(self):
        engine = _engine()
        markets = [_market("btc-updown-5m-1782565800", accepting=False, bid=0.48, ask=0.52)]
        with patch("polymarket.market_availability_engine._requests.get",
                   return_value=_mock_response(markets)):
            result = engine.check()
        assert result.state == MarketAvailabilityState.BETWEEN_EPOCHS

    def test_market_not_scheduled(self):
        engine = _engine()
        # No 5m markets at all
        markets = [_market("will-bitcoin-hit-1m", bid=0.4, ask=0.5)]
        with patch("polymarket.market_availability_engine._requests.get",
                   return_value=_mock_response(markets)):
            result = engine.check()
        assert result.state == MarketAvailabilityState.MARKET_NOT_SCHEDULED
        assert result.active_market_count == 0
        assert result.should_skip_scan()
        assert result.next_check_seconds == 300

    def test_market_not_scheduled_empty_api(self):
        engine = _engine()
        with patch("polymarket.market_availability_engine._requests.get",
                   return_value=_mock_response([])):
            result = engine.check()
        assert result.state == MarketAvailabilityState.MARKET_NOT_SCHEDULED
        assert result.next_check_seconds == 300

    def test_exact_slug_fallback_active_when_broad_scan_empty(self):
        engine = _engine()
        exact_market = _market("btc-updown-5m-1782565800", bid=0.48, ask=0.52)
        event_payload = [{"slug": "btc-updown-5m-1782565800", "markets": [exact_market]}]

        def fake_get(url, params=None, timeout=None):
            if params and "limit" in params:
                return _mock_response([])
            if params and params.get("slug") == "btc-updown-5m-1782565800":
                return _mock_response(event_payload)
            return _mock_response([])

        with patch("polymarket.market_availability_engine.time.time", return_value=1782565800), \
             patch("polymarket.market_availability_engine._requests.get", side_effect=fake_get) as mock_get:
            result = engine.check()

        assert result.state == MarketAvailabilityState.ACTIVE
        assert result.active_market_count == 1
        assert result.btc_market_count == 1
        assert result.eth_market_count == 0
        assert result.fallback_used is True
        assert result.exact_slug_checked == [
            "btc-updown-5m-1782565800",
            "btc-updown-5m-1782566100",
            "eth-updown-5m-1782565800",
            "eth-updown-5m-1782566100",
        ]
        assert result.exact_slug_match_count == 1
        assert result.availability_source == "exact_slug_fallback"
        assert mock_get.call_count == 5

    def test_exact_slug_fallback_empty_preserves_market_not_scheduled(self):
        engine = _engine()

        def fake_get(url, params=None, timeout=None):
            return _mock_response([])

        with patch("polymarket.market_availability_engine.time.time", return_value=1782565800), \
             patch("polymarket.market_availability_engine._requests.get", side_effect=fake_get):
            result = engine.check()

        assert result.state == MarketAvailabilityState.MARKET_NOT_SCHEDULED
        assert result.active_market_count == 0
        assert result.fallback_used is True
        assert result.exact_slug_checked == [
            "btc-updown-5m-1782565800",
            "btc-updown-5m-1782566100",
            "eth-updown-5m-1782565800",
            "eth-updown-5m-1782566100",
        ]
        assert result.exact_slug_match_count == 0
        assert result.availability_source == "exact_slug_fallback"

    def test_exact_slug_fallback_diagnostics_in_telemetry_payload(self):
        result = MarketAvailabilityResult(
            state=MarketAvailabilityState.ACTIVE,
            fallback_used=True,
            exact_slug_checked=["btc-updown-5m-1782565800"],
            exact_slug_match_count=1,
            availability_source="exact_slug_fallback",
        )

        payload = result.to_telemetry_payload()

        assert payload["fallback_used"] is True
        assert payload["exact_slug_checked"] == ["btc-updown-5m-1782565800"]
        assert payload["exact_slug_match_count"] == 1
        assert payload["availability_source"] == "exact_slug_fallback"

    def test_existing_broad_scan_active_path_does_not_use_fallback(self):
        engine = _engine()
        markets = [_market("btc-updown-5m-1782565800", bid=0.48, ask=0.52)]

        with patch("polymarket.market_availability_engine._requests.get",
                   return_value=_mock_response(markets)) as mock_get:
            result = engine.check()

        assert result.state == MarketAvailabilityState.ACTIVE
        assert result.fallback_used is False
        assert result.exact_slug_checked == []
        assert result.exact_slug_match_count == 0
        assert result.availability_source == "broad_markets"
        assert mock_get.call_count == 1

    def test_api_unavailable_request_exception(self):
        engine = _engine()
        with patch("polymarket.market_availability_engine._requests.get",
                   side_effect=ConnectionError("timeout")):
            result = engine.check()
        assert result.state == MarketAvailabilityState.API_UNAVAILABLE
        assert result.should_skip_scan()
        assert result.error is not None
        assert result.next_check_seconds == 60  # base sleep, first failure

    def test_api_unavailable_http_error(self):
        engine = _engine()
        with patch("polymarket.market_availability_engine._requests.get",
                   return_value=_mock_response([], status_code=503)):
            result = engine.check()
        assert result.state == MarketAvailabilityState.API_UNAVAILABLE

    def test_api_unavailable_exponential_backoff(self):
        engine = _engine()
        # Simulate 3 consecutive failures
        with patch("polymarket.market_availability_engine._requests.get",
                   side_effect=ConnectionError("x")):
            r1 = engine.check()
            engine.invalidate_cache()
            r2 = engine.check()
            engine.invalidate_cache()
            r3 = engine.check()
        assert r1.next_check_seconds == 60   # 60 * 2^0
        assert r2.next_check_seconds == 120  # 60 * 2^1
        assert r3.next_check_seconds == 240  # 60 * 2^2

    def test_api_unavailable_max_backoff(self):
        engine = _engine(api_unavailable_base_sleep_sec=60, api_unavailable_max_sleep_sec=100)
        with patch("polymarket.market_availability_engine._requests.get",
                   side_effect=ConnectionError("x")):
            for _ in range(5):
                engine.check()
                engine.invalidate_cache()
            result = engine.check()
        assert result.next_check_seconds <= 100

    def test_unknown_state_malformed_json(self):
        engine = _engine()
        resp = MagicMock()
        resp.status_code = 200
        resp.json.side_effect = ValueError("bad json")
        with patch("polymarket.market_availability_engine._requests.get", return_value=resp):
            result = engine.check()
        assert result.state == MarketAvailabilityState.API_UNAVAILABLE

    def test_unknown_state_unexpected_schema(self):
        engine = _engine()
        with patch("polymarket.market_availability_engine._requests.get",
                   return_value=_mock_response({"unexpected": "object"})):
            result = engine.check()
        # Dict returned by API → classified based on empty candidates
        assert result.state in (
            MarketAvailabilityState.MARKET_NOT_SCHEDULED,
            MarketAvailabilityState.UNKNOWN,
        )


# ---------------------------------------------------------------------------
# Cache behaviour
# ---------------------------------------------------------------------------

class TestCacheBehaviour:
    def test_cache_hit_returns_cached(self):
        engine = _engine(cache_ttl_sec=60)
        markets = [_market("btc-updown-5m-1")]
        with patch("polymarket.market_availability_engine._requests.get",
                   return_value=_mock_response(markets)) as mock_get:
            r1 = engine.check()
            r2 = engine.check()
        # Only one real API call; second should be cached
        assert mock_get.call_count == 1
        assert r1.state == r2.state
        assert not r1.cache_hit
        assert r2.cache_hit

    def test_cache_miss_when_expired(self):
        engine = _engine(cache_ttl_sec=0)
        markets = [_market("btc-updown-5m-1")]
        with patch("polymarket.market_availability_engine._requests.get",
                   return_value=_mock_response(markets)) as mock_get:
            engine.check()
            engine.check()
        assert mock_get.call_count == 2

    def test_invalidate_cache_forces_refetch(self):
        engine = _engine(cache_ttl_sec=60)
        markets = [_market("btc-updown-5m-1")]
        with patch("polymarket.market_availability_engine._requests.get",
                   return_value=_mock_response(markets)) as mock_get:
            engine.check()
            engine.invalidate_cache()
            engine.check()
        assert mock_get.call_count == 2


# ---------------------------------------------------------------------------
# Slug pattern matching
# ---------------------------------------------------------------------------

class TestSlugPatternMatching:
    def _classify(self, slug: str) -> bool:
        engine = MarketAvailabilityEngine()
        return engine._is_5m_binary({"slug": slug})

    def test_btc_updown_5m(self):
        assert self._classify("btc-updown-5m-1782565800")

    def test_eth_updown_5m(self):
        assert self._classify("eth-updown-5m-1782565800")

    def test_btcusd_5m(self):
        assert self._classify("btcusd-5m-1782565800")

    def test_long_duration_not_matched(self):
        assert not self._classify("will-bitcoin-hit-1m-before-gta-vi")

    def test_empty_slug_not_matched(self):
        assert not self._classify("")

    def test_case_insensitive(self):
        assert self._classify("BTC-UPDOWN-5M-1782565800")

    def test_symbol_extraction_btc(self):
        engine = MarketAvailabilityEngine()
        assert engine._symbol_from_slug("btc-updown-5m-1782565800") == "BTC"

    def test_symbol_extraction_eth(self):
        engine = MarketAvailabilityEngine()
        assert engine._symbol_from_slug("eth-updown-5m-1782565800") == "ETH"

    def test_symbol_extraction_unknown(self):
        engine = MarketAvailabilityEngine()
        assert engine._symbol_from_slug("unknown-market") == ""


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

class TestTelemetry:
    def test_log_market_availability_check_method_exists(self):
        from utils.quant_event_logger import QuantEventLogger
        logger = QuantEventLogger(enabled=False)
        assert hasattr(logger, "log_market_availability_check")
        assert callable(logger.log_market_availability_check)

    def test_log_market_availability_check_no_error(self, tmp_path):
        from utils.quant_event_logger import QuantEventLogger
        logger = QuantEventLogger(base_dir=str(tmp_path / "qdata"))
        result = logger.log_market_availability_check({
            "state": "MARKET_NOT_SCHEDULED",
            "active_market_count": 0,
            "symbols_available": [],
            "next_check_seconds": 300,
            "cache_hit": False,
            "schema_version": "market_availability_v1",
        })
        assert isinstance(result, bool)

    def test_log_market_availability_check_writes_to_research_log(self, tmp_path):
        from utils.quant_event_logger import QuantEventLogger
        logger = QuantEventLogger(base_dir=str(tmp_path / "qdata"))
        engine = _engine()
        markets = [_market("btc-updown-5m-1", bid=0.0, ask=0.0)]
        with patch("polymarket.market_availability_engine._requests.get",
                   return_value=_mock_response(markets)):
            result = engine.check()

        logger.log_market_availability_check(result.to_telemetry_payload())

        research_files = list((tmp_path / "qdata" / "research_log").glob("*.jsonl"))
        assert len(research_files) == 1
        events = [json.loads(l) for l in research_files[0].read_text(encoding="utf-8").splitlines() if l.strip()]
        assert events[0].get("event_type") == "market_availability_check"
        payload = events[0].get("payload") or {}
        assert payload.get("state") == "BETWEEN_EPOCHS"
        assert payload.get("schema_version") == "market_availability_v1"

    def test_result_to_telemetry_payload(self):
        result = MarketAvailabilityResult(
            state=MarketAvailabilityState.ACTIVE,
            active_market_count=2,
            symbols_available=["BTC", "ETH"],
            next_check_seconds=30,
        )
        payload = result.to_telemetry_payload()
        assert payload["state"] == "ACTIVE"
        assert payload["active_market_count"] == 2
        assert payload["symbols_available"] == ["BTC", "ETH"]
        assert payload["schema_version"] == "market_availability_v1"


# ---------------------------------------------------------------------------
# Trader integration
# ---------------------------------------------------------------------------

class TestTraderIntegration:
    def _make_trader(self, settings_override: dict | None = None):
        from unittest.mock import MagicMock
        from config.settings import Settings
        import tempfile, os
        s = Settings()
        s.paper_trading = True
        s.quant_data_dir = tempfile.mkdtemp()
        if settings_override:
            for k, v in settings_override.items():
                setattr(s, k, v)
        return s

    def test_trader_skips_scan_when_not_scheduled(self, tmp_path):
        from polymarket.trader import PolymarketTrader
        settings = self._make_trader({"quant_data_dir": str(tmp_path / "qdata"),
                                      "enable_market_availability_guard": True})
        trader = PolymarketTrader(settings=settings)

        captured = []
        trader._emit_quant_event = lambda et, p: captured.append((et, p))

        # Patch availability engine to return NOT_SCHEDULED
        not_scheduled = MarketAvailabilityResult(
            state=MarketAvailabilityState.MARKET_NOT_SCHEDULED,
            next_check_seconds=300,
        )
        trader.market_availability_engine = MagicMock()
        trader.market_availability_engine.check.return_value = not_scheduled

        # Also mock the expensive parts so no real network calls happen
        trader._begin_cycle_timing = MagicMock()
        trader._finish_cycle_timing = MagicMock()
        trader._ensure_connected = MagicMock()
        trader.reconcile_live_positions = MagicMock(return_value=MagicMock(block_new_trading=False))
        trader._update_bankroll_state = MagicMock()
        trader._maybe_emit_risk_state_event = MagicMock()
        trader._maybe_emit_system_health = MagicMock()
        trader._block_on_reconciliation_if_needed = MagicMock(return_value=False)
        trader._cancel_stale_entry_orders_if_needed = MagicMock()
        trader._check_stalled_positions = MagicMock()
        trader._manage_open_positions_for_cycle = MagicMock()
        trader._preload_next_market = MagicMock()
        trader._maybe_log_cycle_summary = MagicMock()
        trader.auto_redeem_cycle = MagicMock()
        trader._paused_insufficient_funds = False
        trader._risk_pause_until = 0.0

        outcomes = trader.run_single_cycle()

        # Must return empty list (scan skipped)
        assert outcomes == []
        # Must emit market_availability_check telemetry
        emitted_types = [et for et, _ in captured]
        assert "log_market_availability_check" in emitted_types

    def test_trader_guard_disabled_proceeds(self, tmp_path):
        """When guard is disabled, _select_markets is called normally."""
        from polymarket.trader import PolymarketTrader
        settings = self._make_trader({"quant_data_dir": str(tmp_path / "qdata"),
                                      "enable_market_availability_guard": False})
        trader = PolymarketTrader(settings=settings)

        trader.market_availability_engine = MagicMock()
        trader._begin_cycle_timing = MagicMock()
        trader._finish_cycle_timing = MagicMock()
        trader._ensure_connected = MagicMock()
        trader.reconcile_live_positions = MagicMock(return_value=MagicMock(block_new_trading=False))
        trader._update_bankroll_state = MagicMock()
        trader._maybe_emit_risk_state_event = MagicMock()
        trader._maybe_emit_system_health = MagicMock()
        trader._block_on_reconciliation_if_needed = MagicMock(return_value=False)
        trader._cancel_stale_entry_orders_if_needed = MagicMock()
        trader._check_stalled_positions = MagicMock()
        trader._manage_open_positions_for_cycle = MagicMock()
        trader._preload_next_market = MagicMock()
        trader._maybe_log_cycle_summary = MagicMock()
        trader.auto_redeem_cycle = MagicMock()
        trader._select_markets = MagicMock(return_value=[])
        trader._emit_quant_event = MagicMock()
        trader._emit_cycle_selection_probe_event = MagicMock()
        trader._paused_insufficient_funds = False
        trader._risk_pause_until = 0.0

        trader.run_single_cycle()

        # With guard disabled, engine.check() must NOT be called
        trader.market_availability_engine.check.assert_not_called()
        # But _select_markets IS called
        trader._select_markets.assert_called_once()


# ---------------------------------------------------------------------------
# Bankroll rank schema tests
# ---------------------------------------------------------------------------

class TestBankrollRankSchema:
    def _update_and_get(self, tmp_path) -> tuple:
        """Run _update_bankroll_state and return (last_bankroll_rank, last_capital_score)."""
        from polymarket.trader import PolymarketTrader
        from config.settings import Settings
        s = Settings()
        s.paper_trading = True
        s.quant_data_dir = str(tmp_path / "qdata")
        trader = PolymarketTrader(settings=s)
        trader._emit_quant_event = MagicMock()

        # Mock engine to return controlled values
        trader.bankroll_rank_engine = MagicMock()
        trader.bankroll_rank_engine.evaluate.return_value = {
            "bankroll_rank": "T0_MICRO_SEED",
            "bankroll_family": "MICRO",
            "capital_score": 0.75,
            "capital_state": "HEALTHY",
            "promotion_candidate": False,
            "demotion_candidate": False,
            "expected_risk_profile": "MODERATE",
            "metrics": {"consecutive_wins": 0, "consecutive_losses": 0,
                        "recovery_factor": 1.0, "volatility": 0.0},
        }
        trader._update_bankroll_rank_lock = MagicMock(return_value=MagicMock(active_tier=MagicMock(value="T0_MICRO_SEED")))
        trader._update_risk_mode = MagicMock()
        trader._sync_sizing_bankroll = MagicMock()

        trader._update_bankroll_state()
        return trader._last_bankroll_rank, trader._last_capital_score

    def test_bankroll_rank_is_string(self, tmp_path):
        rank, score = self._update_and_get(tmp_path)
        assert isinstance(rank, str), f"Expected str, got {type(rank)}: {rank!r}"
        assert rank == "T0_MICRO_SEED"

    def test_capital_score_is_float(self, tmp_path):
        rank, score = self._update_and_get(tmp_path)
        assert isinstance(score, float), f"Expected float, got {type(score)}: {score!r}"
        assert score == 0.75

    def test_bankroll_rank_not_equal_to_capital_score(self, tmp_path):
        rank, score = self._update_and_get(tmp_path)
        assert rank != score, "bankroll_rank must NOT equal capital_score (type or value mismatch)"


# ---------------------------------------------------------------------------
# Canonical builder bankroll_rank schema
# ---------------------------------------------------------------------------

class TestCanonicalBuilderBankrollSchema:
    def _build_row_with(self, bankroll_rank_val, capital_score_val, tmp_path) -> dict:
        import json
        from tools.runtime.canonical_trade_context_builder import CanonicalContextBuilder
        date_str = "2026-06-28"
        rkey = "cond|1782565800|BTC|YES|token"
        run_id = "run_schema_test"

        open_event = {
            "event_type": "trade_open",
            "timestamp_utc": "2026-06-28T10:00:00Z",
            "run_id": run_id,
            "payload": {
                "paper_trade_replay_key": rkey,
                "position_id": "pos_schema",
                "ticker": "BTC",
                "ev": 0.10,
                "true_probability": 0.65,
                "fair_value": 0.65,
                "bankroll_tier_id": "T0_MICRO_SEED",
                "risk_mode": "NORMAL",
                "entry_price": 0.50,
                "size": 1.0,
                "bankroll_rank": bankroll_rank_val,
                "capital_score": capital_score_val,
            },
        }
        close_event = {
            "event_type": "trade_close",
            "timestamp_utc": "2026-06-28T10:01:00Z",
            "run_id": run_id,
            "payload": {
                "paper_trade_replay_key": rkey,
                "position_id": "pos_schema",
                "exit_price": 0.60,
                "pnl": 0.10,
                "exit_reason": "take_profit",
            },
        }
        base = tmp_path / "qdata"
        (base / "trade_journal").mkdir(parents=True)
        with open(base / "trade_journal" / f"{date_str}.jsonl", "w") as f:
            f.write(json.dumps(open_event) + "\n")
            f.write(json.dumps(close_event) + "\n")

        builder = CanonicalContextBuilder(base, [date_str])
        builder.load_all()
        rows, _ = builder.compile()
        return rows[0] if rows else {}

    def test_bankroll_rank_string_preserved(self, tmp_path):
        row = self._build_row_with("T0_MICRO_SEED", 0.75, tmp_path)
        assert row.get("bankroll_rank") == "T0_MICRO_SEED", (
            f"Expected 'T0_MICRO_SEED' got {row.get('bankroll_rank')!r}"
        )

    def test_capital_score_float_parsed(self, tmp_path):
        row = self._build_row_with("T0_MICRO_SEED", 0.75, tmp_path)
        assert row.get("capital_score") == 0.75, (
            f"Expected 0.75 got {row.get('capital_score')!r}"
        )

    def test_bankroll_rank_none_when_absent(self, tmp_path):
        """When bankroll_rank is not in events, canonical row gets None (not a float)."""
        row = self._build_row_with(None, None, tmp_path)
        assert row.get("bankroll_rank") is None

    def test_legacy_rows_compatible(self, tmp_path):
        """Legacy rows without bankroll_rank still compile without error."""
        row = self._build_row_with(None, None, tmp_path)
        assert "trade_id" in row
        assert row.get("data_quality_grade") in ("A", "B", "C", "D")
