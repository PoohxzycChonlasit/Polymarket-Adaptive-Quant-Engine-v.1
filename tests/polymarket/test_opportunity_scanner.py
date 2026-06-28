from __future__ import annotations

from polymarket.delta_engine import DeltaRegime
from polymarket.expected_value import ExpectedValueTier
from polymarket.opportunity_scanner import (
    OpportunityCandidate,
    OpportunityDecision,
    OpportunityInput,
    OpportunityScanContext,
    rank_opportunities,
    scan_opportunity,
    scan_opportunities,
)


def _candidate(**overrides: object) -> OpportunityCandidate:
    values = {
        "market_id": "btc-5m-1",
        "asset": "BTC",
        "p_yes": 0.62,
        "p_no": 0.38,
        "yes_ask": 0.56,
        "no_ask": 0.36,
        "confidence_score": 0.72,
        "delta_score": 1.2,
        "delta_regime": DeltaRegime.NORMAL,
        "spread": 0.02,
        "liquidity": 1_500.0,
        "time_remaining_seconds": 240,
        "price_velocity": 0.002,
        "distance_to_strike": 0.004,
        "orderbook_bid_size": 80.0,
        "orderbook_ask_size": 40.0,
    }
    values.update(overrides)
    return OpportunityCandidate(**values)


def _context(**overrides: object) -> OpportunityScanContext:
    values = {
        "ev_tier": ExpectedValueTier(name="test", min_ev=0.02),
        "bankroll_tier": "MICRO",
        "trades_last_hour": 0,
        "max_trades_per_market": 2,
    }
    values.update(overrides)
    return OpportunityScanContext(**values)


def test_scanner_ranks_best_opportunity() -> None:
    weak = _candidate(market_id="weak", p_yes=0.57, yes_ask=0.54, liquidity=500.0, price_velocity=0.001)
    strong = _candidate(market_id="strong", p_yes=0.66, yes_ask=0.56, liquidity=2_500.0, price_velocity=0.004)

    result = scan_opportunities([weak, strong], _context())

    assert result.decision == OpportunityDecision.BEST_TRADE
    assert result.best_trade is not None
    assert result.best_trade.candidate.market_id == "strong"
    assert result.best_trade.side == "YES"


def test_no_forced_trade_when_ev_is_bad() -> None:
    candidate = _candidate(p_yes=0.53, p_no=0.47, yes_ask=0.52, no_ask=0.46)

    result = scan_opportunities([candidate], _context())

    assert result.decision == OpportunityDecision.SKIP
    assert result.best_trade is None
    assert result.skipped[0].skip_reason == "ev_below_threshold"


def test_scan_opportunity_public_api_returns_best_trade() -> None:
    result = scan_opportunity(
        OpportunityInput(
            market_id="btc-api",
            asset="BTC",
            p_yes=0.62,
            p_no=0.38,
            yes_ask=0.56,
            no_ask=0.36,
            confidence_score=0.72,
            delta_score=1.2,
            delta_regime=DeltaRegime.NORMAL,
            delta_multiplier=0.8,
            spread=0.02,
            liquidity=1_500.0,
            time_remaining_seconds=240,
            price_velocity=0.002,
            distance_to_strike=0.004,
        ),
        _context(),
    )

    assert result.decision == OpportunityDecision.BEST_TRADE
    assert result.side == "YES"


def test_rank_opportunities_sorts_best_score_first() -> None:
    weak = OpportunityInput(
        market_id="weak",
        asset="BTC",
        p_yes=0.58,
        p_no=0.42,
        yes_ask=0.54,
        no_ask=0.40,
        confidence_score=0.68,
        delta_score=1.0,
        delta_regime=DeltaRegime.NORMAL,
        spread=0.02,
        liquidity=800.0,
        time_remaining_seconds=240,
        price_velocity=0.001,
        distance_to_strike=0.006,
    )
    strong = OpportunityInput(
        market_id="strong",
        asset="BTC",
        p_yes=0.66,
        p_no=0.34,
        yes_ask=0.56,
        no_ask=0.32,
        confidence_score=0.76,
        delta_score=1.0,
        delta_regime=DeltaRegime.NORMAL,
        spread=0.01,
        liquidity=2_500.0,
        time_remaining_seconds=240,
        price_velocity=0.004,
        distance_to_strike=0.004,
    )

    ranked = rank_opportunities([weak, strong], _context())

    assert ranked[0].market_id == "strong"


def test_skip_when_spread_is_wide() -> None:
    result = scan_opportunities([_candidate(spread=0.12)], _context())

    assert result.decision == OpportunityDecision.SKIP
    assert result.skipped[0].skip_reason == "spread_too_wide"


def test_skip_when_confidence_too_low() -> None:
    result = scan_opportunities([_candidate(confidence_score=0.50)], _context())

    assert result.decision == OpportunityDecision.SKIP
    assert result.skipped[0].skip_reason == "confidence_too_low"


def test_skip_when_liquidity_too_low() -> None:
    result = scan_opportunities([_candidate(liquidity=5.0)], _context())

    assert result.decision == OpportunityDecision.SKIP
    assert result.skipped[0].skip_reason == "liquidity_too_low"


def test_skip_when_delta_is_extreme() -> None:
    result = scan_opportunities(
        [_candidate(delta_score=8.0, delta_regime=DeltaRegime.EXTREME)],
        _context(),
    )

    assert result.decision == OpportunityDecision.SKIP
    assert result.skipped[0].skip_reason == "delta_extreme"


def test_skip_when_delta_multiplier_blocks_entry() -> None:
    result = scan_opportunities(
        [_candidate(delta_score=2.0, delta_regime=DeltaRegime.HIGH, delta_multiplier=0.0)],
        _context(),
    )

    assert result.decision == OpportunityDecision.SKIP
    assert result.skipped[0].skip_reason == "delta_extreme"


def test_skip_when_time_remaining_is_at_entry_cutoff() -> None:
    result = scan_opportunities([_candidate(time_remaining_seconds=90)], _context())

    assert result.decision == OpportunityDecision.SKIP
    assert result.skipped[0].skip_reason == "time_remaining_le_90s"


def test_risk_off_keeps_opportunity_on_watchlist_not_best_trade() -> None:
    result = scan_opportunities([_candidate()], _context(risk_off=True))

    assert result.decision == OpportunityDecision.SKIP
    assert result.best_trade is None
    assert "risk_off" in result.skipped[0].skip_reason
