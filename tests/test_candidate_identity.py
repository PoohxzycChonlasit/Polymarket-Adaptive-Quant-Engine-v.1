from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError, replace
from inspect import Parameter, signature

import pytest

from polymarket.delta_engine import DeltaRegime
from polymarket.expected_value import ExpectedValueTier
from polymarket.opportunity_scanner import (
    OpportunityCandidate,
    OpportunityInput,
    OpportunityScanContext,
    _candidate_from_input,
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


def _opportunity_input(**overrides: object) -> OpportunityInput:
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
    }
    values.update(overrides)
    return OpportunityInput(**values)


def _context() -> OpportunityScanContext:
    return OpportunityScanContext(
        ev_tier=ExpectedValueTier(name="test", min_ev=0.02),
        bankroll_tier="MICRO",
        max_trades_per_market=2,
    )


@pytest.mark.parametrize("factory", [_opportunity_input, _candidate])
def test_legacy_constructor_generates_immutable_candidate_identity(factory) -> None:
    value = factory()

    assert value.candidate_id.startswith("candidate_")
    assert len(value.candidate_id) == len("candidate_") + 32
    assert value.candidate_trace_id.startswith("ct_")
    assert len(value.candidate_trace_id) == len("ct_") + 16
    assert value.candidate_created_at.endswith("Z")
    assert value.candidate_identity_schema_version == "1.0"

    with pytest.raises(FrozenInstanceError):
        value.candidate_id = "candidate_changed"


@pytest.mark.parametrize("factory", [_opportunity_input, _candidate])
def test_explicit_identity_is_preserved_and_trace_is_deterministic(factory) -> None:
    first = factory(
        candidate_id="candidate_explicit",
        candidate_created_at="2026-06-15T00:00:00Z",
        candidate_identity_schema_version="1.0",
    )
    second = factory(
        candidate_id="candidate_explicit",
        candidate_created_at="2026-06-15T00:01:00Z",
        candidate_identity_schema_version="1.0",
    )
    injected = factory(
        candidate_id="candidate_explicit",
        candidate_trace_id="ct_explicit",
        candidate_created_at="2026-06-15T00:00:00Z",
        candidate_identity_schema_version="1.0",
    )

    assert first.candidate_trace_id == second.candidate_trace_id
    expected_digest = hashlib.sha256(b"1.0|candidate_explicit").hexdigest()[:16]
    assert first.candidate_trace_id == f"ct_{expected_digest}"
    assert injected.candidate_trace_id == "ct_explicit"
    assert injected.candidate_created_at == "2026-06-15T00:00:00Z"


def test_opportunity_input_identity_is_copied_to_candidate() -> None:
    opportunity = _opportunity_input(
        candidate_id="candidate_input",
        candidate_trace_id="ct_input",
        candidate_created_at="2026-06-15T00:00:00Z",
        candidate_identity_schema_version="1.0",
    )

    candidate = _candidate_from_input(opportunity)

    assert candidate.candidate_id == opportunity.candidate_id
    assert candidate.candidate_trace_id == opportunity.candidate_trace_id
    assert candidate.candidate_created_at == opportunity.candidate_created_at
    assert candidate.candidate_identity_schema_version == opportunity.candidate_identity_schema_version


def test_identity_does_not_change_equality_or_scanner_result() -> None:
    first = _candidate(candidate_id="candidate_first", candidate_trace_id="ct_first")
    second = replace(first, candidate_id="candidate_second", candidate_trace_id="ct_second")

    assert first == second

    first_result = scan_opportunities([first], _context())
    second_result = scan_opportunities([second], _context())
    assert first_result.decision == second_result.decision
    assert first_result.best_trade is not None
    assert second_result.best_trade is not None
    assert first_result.best_trade.side == second_result.best_trade.side
    assert first_result.best_trade.score == second_result.best_trade.score
    assert first_result.best_trade.ev == second_result.best_trade.ev


def test_candidate_identity_does_not_include_signal_identity_fields() -> None:
    candidate = _candidate()

    assert not hasattr(candidate, "signal_name")
    assert not hasattr(candidate, "signal_reason")


def test_candidate_identity_fields_are_keyword_only_and_generated_ids_are_unique() -> None:
    for candidate_type in (OpportunityInput, OpportunityCandidate):
        parameters = signature(candidate_type).parameters
        for field_name in (
            "candidate_id",
            "candidate_trace_id",
            "candidate_created_at",
            "candidate_identity_schema_version",
        ):
            assert parameters[field_name].kind is Parameter.KEYWORD_ONLY

    assert _candidate().candidate_id != _candidate().candidate_id
