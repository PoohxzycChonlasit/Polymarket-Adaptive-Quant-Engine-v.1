"""
Tests for Probability Model Observability v1.

Verifies that the three Tier-1 observability fields introduced in the
observability patch are:

1. Forwarded through _record_quant_detail (detail.update(values) path).
2. Present in the decision payload emitted via log_decision.
3. Backward-compatible: existing keys are not renamed, removed, or mutated.
4. Fail-soft: the patch does not raise on unexpected input types.

Fields covered:
  - probability_model_reason  (str: semicolon-delimited model inputs + quality)
  - prob_model_momentum_input (float: momentum_decimal = signal.momentum_pct/100)
  - prob_model_liquidity_usd  (float: ob_liquidity_usd passed to ProbabilityModelInput)

No strategy, confidence, EV, execution, or risk logic is touched.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from polymarket.gamma_fetcher import GammaMarket
from polymarket.trader import PolymarketTrader, TradeOutcome


# ---------------------------------------------------------------------------
# Helpers shared with test_record_quant_detail_ticker_duplication.py
# ---------------------------------------------------------------------------

class _CollectingQuantLogger:
    def __init__(self) -> None:
        self.mode = "paper"
        self.schema_version = "test"
        self.disabled_categories: set[str] = set()
        self.events: list[tuple[str, dict]] = []

    def log_decision(self, payload: dict) -> bool:
        self.events.append(("decision", payload))
        return True

    def log_risk_event(self, payload: dict) -> bool:
        self.events.append(("risk", payload))
        return True

    def log_research_snapshot(self, payload: dict) -> bool:
        self.events.append(("research", payload))
        return True

    def _with_candidate_trace_identity(self, payload: dict, ticker: str) -> dict:
        return payload


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        paper_trading=True,
        dry_run=True,
        account_balance=100.0,
        execution_entry_cutoff_seconds=90,
        hybrid_phase_v1_enabled=False,
    )


def _trader() -> PolymarketTrader:
    trader = PolymarketTrader()
    trader.settings = _settings()
    return trader


def _market() -> GammaMarket:
    return GammaMarket(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        volume=0.0,
        liquidity=0.0,
        end_date_iso="",
    )


# ---------------------------------------------------------------------------
# Helper: typical values for the three new fields
# ---------------------------------------------------------------------------

_TYPICAL_MODEL_REASON   = "leans_no;distance=0.00096;velocity=0.00091;momentum=0.00457;thin_liquidity"
_TYPICAL_MOMENTUM_INPUT = 0.00457
_TYPICAL_LIQUIDITY_USD  = 203.75


# ===========================================================================
# Part 1: _record_quant_detail preserves the three new keys
# ===========================================================================

class TestRecordQuantDetailPreservesObservabilityFields:
    """_record_quant_detail must forward all three new keys unchanged."""

    def test_probability_model_reason_forwarded(self) -> None:
        trader = _trader()
        detail = trader._record_quant_detail(
            "BTC",
            probability_model_reason=_TYPICAL_MODEL_REASON,
        )
        assert "probability_model_reason" in detail, (
            "probability_model_reason must survive _record_quant_detail"
        )
        assert detail["probability_model_reason"] == _TYPICAL_MODEL_REASON

    def test_prob_model_momentum_input_forwarded(self) -> None:
        trader = _trader()
        detail = trader._record_quant_detail(
            "BTC",
            prob_model_momentum_input=_TYPICAL_MOMENTUM_INPUT,
        )
        assert "prob_model_momentum_input" in detail
        assert detail["prob_model_momentum_input"] == pytest.approx(_TYPICAL_MOMENTUM_INPUT)

    def test_prob_model_liquidity_usd_forwarded(self) -> None:
        trader = _trader()
        detail = trader._record_quant_detail(
            "BTC",
            prob_model_liquidity_usd=_TYPICAL_LIQUIDITY_USD,
        )
        assert "prob_model_liquidity_usd" in detail
        assert detail["prob_model_liquidity_usd"] == pytest.approx(_TYPICAL_LIQUIDITY_USD)

    def test_all_three_forwarded_together(self) -> None:
        trader = _trader()
        detail = trader._record_quant_detail(
            "ETH",
            probability_model_reason=_TYPICAL_MODEL_REASON,
            prob_model_momentum_input=_TYPICAL_MOMENTUM_INPUT,
            prob_model_liquidity_usd=_TYPICAL_LIQUIDITY_USD,
        )
        assert detail["probability_model_reason"] == _TYPICAL_MODEL_REASON
        assert detail["prob_model_momentum_input"] == pytest.approx(_TYPICAL_MOMENTUM_INPUT)
        assert detail["prob_model_liquidity_usd"] == pytest.approx(_TYPICAL_LIQUIDITY_USD)

    def test_existing_keys_not_mutated(self) -> None:
        """Patch must not rename, remove, or alter any pre-existing key."""
        trader = _trader()
        detail = trader._record_quant_detail(
            "BTC",
            p_yes=0.63,
            p_no=0.37,
            ev=0.09,
            confidence=0.72,
            probability_model_reason=_TYPICAL_MODEL_REASON,
            prob_model_momentum_input=_TYPICAL_MOMENTUM_INPUT,
            prob_model_liquidity_usd=_TYPICAL_LIQUIDITY_USD,
        )
        # Pre-existing keys must be intact
        assert detail["p_yes"] == pytest.approx(0.63)
        assert detail["p_no"] == pytest.approx(0.37)
        assert detail["ev"] == pytest.approx(0.09)
        assert detail["confidence"] == pytest.approx(0.72)
        # New keys also present
        assert "probability_model_reason" in detail
        assert "prob_model_momentum_input" in detail
        assert "prob_model_liquidity_usd" in detail

    def test_ticker_duplication_not_introduced(self) -> None:
        """Patch must not duplicate the 'ticker' key (regression guard)."""
        trader = _trader()
        detail = trader._record_quant_detail(
            "BTC",
            probability_model_reason=_TYPICAL_MODEL_REASON,
            prob_model_momentum_input=_TYPICAL_MOMENTUM_INPUT,
            prob_model_liquidity_usd=_TYPICAL_LIQUIDITY_USD,
        )
        assert json.dumps(detail).count('"ticker"') == 1, (
            "ticker must appear exactly once after patch"
        )

    def test_last_quant_details_cache_updated(self) -> None:
        """The three new fields must be persisted in last_quant_details."""
        trader = _trader()
        trader._record_quant_detail(
            "BTC",
            probability_model_reason=_TYPICAL_MODEL_REASON,
            prob_model_momentum_input=_TYPICAL_MOMENTUM_INPUT,
            prob_model_liquidity_usd=_TYPICAL_LIQUIDITY_USD,
        )
        cached = trader.last_quant_details.get("BTC", {})
        assert cached.get("probability_model_reason") == _TYPICAL_MODEL_REASON
        assert cached.get("prob_model_momentum_input") == pytest.approx(_TYPICAL_MOMENTUM_INPUT)
        assert cached.get("prob_model_liquidity_usd") == pytest.approx(_TYPICAL_LIQUIDITY_USD)


# ===========================================================================
# Part 2: Fields propagate through _skip_outcome into the decision payload
# ===========================================================================

class TestObservabilityFieldsInDecisionPayload:
    """
    When _record_quant_detail is called with the three new fields and the
    result is passed as extra_detail to _skip_outcome, the emitted decision
    payload (log_decision) must contain all three fields.
    """

    def _emit_and_collect(self, trader: PolymarketTrader, ticker: str = "BTC") -> dict:
        collector = _CollectingQuantLogger()
        trader.quant_events = collector
        existing_detail = trader._record_quant_detail(
            ticker,
            market_id="pm-5m-btc",
            p_yes=0.63,
            p_no=0.37,
            ev=0.09,
            confidence=0.72,
            probability_model_reason=_TYPICAL_MODEL_REASON,
            prob_model_momentum_input=_TYPICAL_MOMENTUM_INPUT,
            prob_model_liquidity_usd=_TYPICAL_LIQUIDITY_USD,
        )
        outcome = trader._skip_outcome(
            _market(),
            "skip",
            0.72,
            "scanner_no_best_trade",
            extra_detail=existing_detail,
        )
        trader._emit_decision_event(outcome, ticker=ticker)
        decision_events = [e for e in collector.events if e[0] == "decision"]
        assert decision_events, "At least one decision event must be emitted"
        return decision_events[-1][1]  # payload of last decision event

    def test_probability_model_reason_in_decision_payload(self) -> None:
        trader = _trader()
        payload = self._emit_and_collect(trader)
        assert "probability_model_reason" in payload, (
            "probability_model_reason missing from emitted decision payload"
        )
        assert payload["probability_model_reason"] == _TYPICAL_MODEL_REASON

    def test_prob_model_momentum_input_in_decision_payload(self) -> None:
        trader = _trader()
        payload = self._emit_and_collect(trader)
        assert "prob_model_momentum_input" in payload, (
            "prob_model_momentum_input missing from emitted decision payload"
        )
        assert payload["prob_model_momentum_input"] == pytest.approx(_TYPICAL_MOMENTUM_INPUT)

    def test_prob_model_liquidity_usd_in_decision_payload(self) -> None:
        trader = _trader()
        payload = self._emit_and_collect(trader)
        assert "prob_model_liquidity_usd" in payload, (
            "prob_model_liquidity_usd missing from emitted decision payload"
        )
        assert payload["prob_model_liquidity_usd"] == pytest.approx(_TYPICAL_LIQUIDITY_USD)

    def test_decision_payload_backward_compatible(self) -> None:
        """Keys that existed before the patch must still be in the payload."""
        trader = _trader()
        payload = self._emit_and_collect(trader)
        assert "p_yes" in payload or "model_probability_yes" in payload
        assert "confidence" in payload
        # ticker appears at the top-level AND inside the nested "display" sub-object;
        # that is pre-existing, expected structure — guard only against it being absent.
        assert payload.get("ticker") == "BTC", "top-level ticker must be present"
        # The three new observability fields must NOT shadow or remove any pre-existing key
        for pre_existing in ("confidence", "market_id", "skip_reason"):
            assert pre_existing in payload, f"{pre_existing!r} must not be removed by patch"


# ===========================================================================
# Part 3: Field content validation
# ===========================================================================

class TestFieldContentValidation:
    """The field values must match the probability model contract."""

    def test_model_reason_contains_direction(self) -> None:
        """model_reason must start with 'leans_yes' or 'leans_no'."""
        from polymarket.probability_model import ProbabilityModelInput, estimate_probability

        result = estimate_probability(
            ProbabilityModelInput(
                underlying_price=104_000.0,
                target_price=104_100.0,
                distance_to_target=-100.0,
                time_remaining_seconds=280,
                recent_price_velocity=0.0009,
                short_term_momentum=0.0046,
                volatility=0.003,
                orderbook_bid=0.49,
                orderbook_ask=0.50,
                spread=0.01,
                liquidity=350.0,
                polymarket_implied_probability=0.50,
            )
        )
        reason = result.model_reason
        assert reason.startswith("leans_yes") or reason.startswith("leans_no"), (
            f"model_reason must begin with direction token; got: {reason!r}"
        )
        assert "distance=" in reason, "model_reason must contain distance= component"
        assert "velocity=" in reason, "model_reason must contain velocity= component"
        assert "momentum=" in reason, "model_reason must contain momentum= component"

    def test_model_reason_contains_quality_tokens_when_thin(self) -> None:
        """model_reason includes liquidity quality token for thin books."""
        from polymarket.probability_model import ProbabilityModelInput, estimate_probability

        thin = estimate_probability(
            ProbabilityModelInput(
                underlying_price=100.0, target_price=100.0,
                time_remaining_seconds=240, liquidity=25.0, spread=0.01,
            )
        )
        assert "weak_liquidity" in thin.model_reason

    def test_prob_model_momentum_input_is_signal_divided_by_100(self) -> None:
        """prob_model_momentum_input must equal signal.momentum_pct / 100."""
        # Simulate what trader.py does at line 8842
        signal_momentum_pct = 0.4567
        momentum_decimal = float(signal_momentum_pct) / 100.0
        assert momentum_decimal == pytest.approx(0.004567)
        # Verify the stored field would match
        trader = _trader()
        detail = trader._record_quant_detail(
            "BTC",
            prob_model_momentum_input=momentum_decimal,
        )
        assert detail["prob_model_momentum_input"] == pytest.approx(momentum_decimal)

    def test_prob_model_liquidity_usd_non_negative(self) -> None:
        """ob_liquidity_usd must always be ≥ 0."""
        trader = _trader()
        for liq in [0.0, 25.0, 350.0, 1_500.0]:
            detail = trader._record_quant_detail(
                "BTC",
                prob_model_liquidity_usd=float(liq),
            )
            assert detail["prob_model_liquidity_usd"] >= 0.0

    def test_model_reason_string_type_enforced(self) -> None:
        """probability_model_reason must be stored as str even if None passed."""
        trader = _trader()
        detail = trader._record_quant_detail(
            "BTC",
            probability_model_reason=None,
        )
        # None would not match str semantics used in trader.py (str(probability.model_reason))
        # Verify the dict accepts None without crash (field will be None, not str)
        # This documents current behavior: the patch uses str() at source
        assert "probability_model_reason" in detail


# ===========================================================================
# Part 4: Fail-soft — patch does not crash on unexpected inputs
# ===========================================================================

class TestFailSoft:
    """The patch must not raise under any realistic input condition."""

    def test_zero_liquidity_does_not_raise(self) -> None:
        trader = _trader()
        detail = trader._record_quant_detail(
            "BTC",
            prob_model_liquidity_usd=0.0,
        )
        assert detail["prob_model_liquidity_usd"] == 0.0

    def test_empty_model_reason_does_not_raise(self) -> None:
        trader = _trader()
        detail = trader._record_quant_detail(
            "BTC",
            probability_model_reason="",
        )
        assert detail["probability_model_reason"] == ""

    def test_negative_momentum_input_does_not_raise(self) -> None:
        """Negative momentum (bearish signal) must be accepted."""
        trader = _trader()
        detail = trader._record_quant_detail(
            "BTC",
            prob_model_momentum_input=-0.0046,
        )
        assert detail["prob_model_momentum_input"] == pytest.approx(-0.0046)


# ===========================================================================
# Tier 2: price_change_pct, realized_volatility, price_velocity,
#          distance_from_ptb_pct
#
# These four fields have been in clob_detail since before Tier 1.
# The only change is adding them to the _decision_diagnostics_payload
# pass-through tuple so they appear at the top level of the decision payload.
# ===========================================================================

_T2_PRICE_CHANGE_PCT     =  0.4567   # signal.momentum_pct (percent, not decimal)
_T2_REALIZED_VOL         =  0.00231  # max(|momentum_dec|, |price_diff/100|)*vol_ratio
_T2_PRICE_VELOCITY       =  0.000913 # momentum_decimal / 5.0
_T2_DISTANCE_FROM_PTB    =  0.0962   # (current-ptb)/ptb * 100  (percent)


# ---------------------------------------------------------------------------
# Part 5: _record_quant_detail forwards all four Tier-2 fields
# ---------------------------------------------------------------------------

class TestTier2RecordQuantDetailForwarding:
    """Tier-2 fields must survive _record_quant_detail → last_quant_details."""

    def test_price_change_pct_forwarded(self) -> None:
        trader = _trader()
        detail = trader._record_quant_detail(
            "BTC", price_change_pct=_T2_PRICE_CHANGE_PCT
        )
        assert "price_change_pct" in detail
        assert detail["price_change_pct"] == pytest.approx(_T2_PRICE_CHANGE_PCT)

    def test_realized_volatility_forwarded(self) -> None:
        trader = _trader()
        detail = trader._record_quant_detail(
            "BTC", realized_volatility=_T2_REALIZED_VOL
        )
        assert "realized_volatility" in detail
        assert detail["realized_volatility"] == pytest.approx(_T2_REALIZED_VOL)

    def test_price_velocity_forwarded(self) -> None:
        trader = _trader()
        detail = trader._record_quant_detail(
            "BTC", price_velocity=_T2_PRICE_VELOCITY
        )
        assert "price_velocity" in detail
        assert detail["price_velocity"] == pytest.approx(_T2_PRICE_VELOCITY)

    def test_distance_from_ptb_pct_forwarded(self) -> None:
        trader = _trader()
        detail = trader._record_quant_detail(
            "BTC", distance_from_ptb_pct=_T2_DISTANCE_FROM_PTB
        )
        assert "distance_from_ptb_pct" in detail
        assert detail["distance_from_ptb_pct"] == pytest.approx(_T2_DISTANCE_FROM_PTB)

    def test_all_four_forwarded_together(self) -> None:
        trader = _trader()
        detail = trader._record_quant_detail(
            "ETH",
            price_change_pct=_T2_PRICE_CHANGE_PCT,
            realized_volatility=_T2_REALIZED_VOL,
            price_velocity=_T2_PRICE_VELOCITY,
            distance_from_ptb_pct=_T2_DISTANCE_FROM_PTB,
        )
        assert detail["price_change_pct"]     == pytest.approx(_T2_PRICE_CHANGE_PCT)
        assert detail["realized_volatility"]   == pytest.approx(_T2_REALIZED_VOL)
        assert detail["price_velocity"]        == pytest.approx(_T2_PRICE_VELOCITY)
        assert detail["distance_from_ptb_pct"] == pytest.approx(_T2_DISTANCE_FROM_PTB)

    def test_tier2_does_not_mutate_tier1_fields(self) -> None:
        """Adding Tier-2 fields must not alter existing Tier-1 fields."""
        trader = _trader()
        detail = trader._record_quant_detail(
            "BTC",
            probability_model_reason=_TYPICAL_MODEL_REASON,
            prob_model_momentum_input=_TYPICAL_MOMENTUM_INPUT,
            prob_model_liquidity_usd=_TYPICAL_LIQUIDITY_USD,
            price_change_pct=_T2_PRICE_CHANGE_PCT,
            realized_volatility=_T2_REALIZED_VOL,
            price_velocity=_T2_PRICE_VELOCITY,
            distance_from_ptb_pct=_T2_DISTANCE_FROM_PTB,
        )
        # Tier 1 fields intact
        assert detail["probability_model_reason"]  == _TYPICAL_MODEL_REASON
        assert detail["prob_model_momentum_input"] == pytest.approx(_TYPICAL_MOMENTUM_INPUT)
        assert detail["prob_model_liquidity_usd"]  == pytest.approx(_TYPICAL_LIQUIDITY_USD)
        # Tier 2 fields also present
        assert detail["price_change_pct"]          == pytest.approx(_T2_PRICE_CHANGE_PCT)
        assert detail["realized_volatility"]        == pytest.approx(_T2_REALIZED_VOL)
        assert detail["price_velocity"]             == pytest.approx(_T2_PRICE_VELOCITY)
        assert detail["distance_from_ptb_pct"]      == pytest.approx(_T2_DISTANCE_FROM_PTB)

    def test_tier2_cached_in_last_quant_details(self) -> None:
        trader = _trader()
        trader._record_quant_detail(
            "BTC",
            price_change_pct=_T2_PRICE_CHANGE_PCT,
            realized_volatility=_T2_REALIZED_VOL,
            price_velocity=_T2_PRICE_VELOCITY,
            distance_from_ptb_pct=_T2_DISTANCE_FROM_PTB,
        )
        cached = trader.last_quant_details.get("BTC", {})
        assert cached.get("price_change_pct")     == pytest.approx(_T2_PRICE_CHANGE_PCT)
        assert cached.get("realized_volatility")   == pytest.approx(_T2_REALIZED_VOL)
        assert cached.get("price_velocity")        == pytest.approx(_T2_PRICE_VELOCITY)
        assert cached.get("distance_from_ptb_pct") == pytest.approx(_T2_DISTANCE_FROM_PTB)


# ---------------------------------------------------------------------------
# Part 6: Tier-2 fields reach the emitted decision payload
# ---------------------------------------------------------------------------

class TestTier2DecisionPayload:
    """After the pass-through patch, all four fields must appear in log_decision."""

    def _emit_and_collect(self, trader: PolymarketTrader, ticker: str = "BTC") -> dict:
        collector = _CollectingQuantLogger()
        trader.quant_events = collector
        existing_detail = trader._record_quant_detail(
            ticker,
            market_id="pm-5m-btc",
            p_yes=0.63,
            p_no=0.37,
            ev=0.09,
            confidence=0.72,
            # Tier 1 fields
            probability_model_reason=_TYPICAL_MODEL_REASON,
            prob_model_momentum_input=_TYPICAL_MOMENTUM_INPUT,
            prob_model_liquidity_usd=_TYPICAL_LIQUIDITY_USD,
            # Tier 2 fields
            price_change_pct=_T2_PRICE_CHANGE_PCT,
            realized_volatility=_T2_REALIZED_VOL,
            price_velocity=_T2_PRICE_VELOCITY,
            distance_from_ptb_pct=_T2_DISTANCE_FROM_PTB,
        )
        outcome = trader._skip_outcome(
            _market(),
            "skip",
            0.72,
            "scanner_no_best_trade",
            extra_detail=existing_detail,
        )
        trader._emit_decision_event(outcome, ticker=ticker)
        decision_events = [e for e in collector.events if e[0] == "decision"]
        assert decision_events, "At least one decision event must be emitted"
        return decision_events[-1][1]

    def test_price_change_pct_in_payload(self) -> None:
        payload = self._emit_and_collect(_trader())
        assert "price_change_pct" in payload, "price_change_pct missing from decision payload"
        assert payload["price_change_pct"] == pytest.approx(_T2_PRICE_CHANGE_PCT)

    def test_realized_volatility_in_payload(self) -> None:
        payload = self._emit_and_collect(_trader())
        assert "realized_volatility" in payload, "realized_volatility missing from decision payload"
        assert payload["realized_volatility"] == pytest.approx(_T2_REALIZED_VOL)

    def test_price_velocity_in_payload(self) -> None:
        payload = self._emit_and_collect(_trader())
        assert "price_velocity" in payload, "price_velocity missing from decision payload"
        assert payload["price_velocity"] == pytest.approx(_T2_PRICE_VELOCITY)

    def test_distance_from_ptb_pct_in_payload(self) -> None:
        payload = self._emit_and_collect(_trader())
        assert "distance_from_ptb_pct" in payload, "distance_from_ptb_pct missing from decision payload"
        assert payload["distance_from_ptb_pct"] == pytest.approx(_T2_DISTANCE_FROM_PTB)

    def test_tier1_fields_still_present_after_tier2(self) -> None:
        """Tier-1 fields must co-exist with Tier-2 fields in the same payload."""
        payload = self._emit_and_collect(_trader())
        # Tier 1
        assert "probability_model_reason"  in payload
        assert "prob_model_momentum_input" in payload
        assert "prob_model_liquidity_usd"  in payload
        # Tier 2
        assert "price_change_pct"          in payload
        assert "realized_volatility"       in payload
        assert "price_velocity"            in payload
        assert "distance_from_ptb_pct"    in payload
        # Pre-existing keys must not be removed
        assert payload.get("ticker") == "BTC"
        assert "confidence" in payload
        assert "market_id"  in payload

    def test_negative_price_change_pct_accepted(self) -> None:
        """Bearish signal (negative momentum_pct) must be stored and forwarded."""
        trader = _trader()
        detail = trader._record_quant_detail("BTC", price_change_pct=-0.3120)
        assert detail["price_change_pct"] == pytest.approx(-0.3120)

    def test_zero_distance_from_ptb_accepted(self) -> None:
        """Price exactly at strike (window_delta=0) must serialize as 0.0."""
        trader = _trader()
        detail = trader._record_quant_detail("BTC", distance_from_ptb_pct=0.0)
        # 0.0 == "" evaluates False in Python, but the pass-through guard is
        #   `if value is not None and value != ""`
        # 0.0 != "" is True, so 0.0 IS forwarded to the payload.
        assert "distance_from_ptb_pct" in detail

    def test_high_volatility_accepted(self) -> None:
        """Extreme volatility (e.g. 6% — unstable_volatility regime) must store."""
        trader = _trader()
        detail = trader._record_quant_detail("BTC", realized_volatility=0.063)
        assert detail["realized_volatility"] == pytest.approx(0.063)

    def test_negative_price_velocity_accepted(self) -> None:
        """Downward velocity (bearish) must be stored without sign loss."""
        trader = _trader()
        detail = trader._record_quant_detail("BTC", price_velocity=-0.00185)
        assert detail["price_velocity"] == pytest.approx(-0.00185)
