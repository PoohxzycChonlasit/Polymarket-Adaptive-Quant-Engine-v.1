"""Tests for polymarket/observability/market_availability.py.

Covers: all 6 TypedDicts importable, all 9 reason codes reachable,
precedence table, golden payload snapshots for evaluate_market_availability
and build_market_availability_payload, summary aggregation, health verdicts,
and JSON serializability.
"""
import json

import pytest

from polymarket.observability.market_availability import (
    EMPTY_ORDERBOOK,
    HIGH_SPREAD,
    LOW_LIQUIDITY,
    MARKET_CLOSED,
    ORDERBOOK_NOT_READY,
    REASON_ACTIVE,
    REASON_CODES,
    STALE_FEED,
    TOKEN_NOT_FOUND,
    UNKNOWN,
    AvailabilityDiagnostics,
    AvailabilityHealth,
    AvailabilityReason,
    AvailabilityScore,
    AvailabilitySnapshot,
    AvailabilitySummary,
    build_availability_health,
    build_market_availability_payload,
    evaluate_market_availability,
    summarize_market_availability,
    CLIENT_ERROR,
)


# ---------------------------------------------------------------------------
# Golden snapshot — evaluate_market_availability (tradable ACTIVE case)
# ---------------------------------------------------------------------------

_EXPECTED_EVAL_SNAPSHOT: dict = {
    "market_id": "pm-5m-btc",
    "ticker": "BTC",
    "token_id": "tok-abc",
    "outcome": "YES",
    "best_bid": 0.49,
    "best_ask": 0.51,
    "orderbook_depth": 5,
    "is_accepting_orders": True,
    "has_valid_bid": True,
    "has_valid_ask": True,
    "feed_age_seconds": None,
    "cache_hit": False,
    "api_latency_ms": 30,
    "checked_at": "2026-01-01T00:00:00Z",
    "schema_version": "market_availability_obs_v1",
    "state": "ACTIVE",
    "reason": {
        "reason_code": "ACTIVE",
        "reason_detail": "Market is tradable",
        "severity": "info",
    },
    "is_tradable": True,
    "spread": 0.02,
    "spread_pct": 0.039216,
}


def _make_eval_snapshot_active() -> dict:
    return evaluate_market_availability(
        ticker="BTC",
        market_id="pm-5m-btc",
        token_id="tok-abc",
        outcome="YES",
        best_bid=0.49,
        best_ask=0.51,
        orderbook_depth=5,
        accepting_orders=True,
        is_active=True,
        checked_at="2026-01-01T00:00:00Z",
        api_latency_ms=30,
    )


# ---------------------------------------------------------------------------
# Golden snapshot — build_market_availability_payload (ACTIVE state)
# ---------------------------------------------------------------------------

_PAYLOAD_INPUTS = dict(
    state="ACTIVE",
    active_market_count=2,
    btc_market_count=1,
    eth_market_count=1,
    symbols_available=["BTC", "ETH"],
    matching_slugs=["btc-updown-5m-001", "eth-updown-5m-001"],
    next_check_seconds=30,
    cache_hit=False,
    api_latency_ms=45,
    error=None,
    ticker="BTC",
    checked_at="2026-01-01T00:00:00Z",
)

_EXPECTED_PAYLOAD: dict = {
    "state": "ACTIVE",
    "active_market_count": 2,
    "btc_market_count": 1,
    "eth_market_count": 1,
    "symbols_available": ["BTC", "ETH"],
    "matching_slugs": ["btc-updown-5m-001", "eth-updown-5m-001"],
    "next_check_seconds": 30,
    "cache_hit": False,
    "api_latency_ms": 45,
    "error": None,
    "ticker": "BTC",
    "checked_at": "2026-01-01T00:00:00Z",
    "primary_reason_code": "ACTIVE",
    "health": {
        "health_score": 1.0,
        "health_grade": "A",
        "health_verdict": "HEALTHY",
        "availability_score": {
            "bid_ask_score": 1.0,
            "liquidity_score": 1.0,
            "latency_score": 1.0,
            "availability_penalty": 0.0,
            "final_score": 1.0,
            "score_schema_version": "availability_score_v1",
        },
        "degradation_reasons": [],
        "recovery_suggestion": "",
        "schema_version": "availability_health_v1",
    },
    "schema_version": "market_availability_obs_v1",
}


# ---------------------------------------------------------------------------
# Tests: reason code constants
# ---------------------------------------------------------------------------


class TestReasonCodeConstants:
    def test_all_nine_codes_in_tuple(self):
        for code in (
            MARKET_CLOSED, STALE_FEED, EMPTY_ORDERBOOK, LOW_LIQUIDITY,
            HIGH_SPREAD, TOKEN_NOT_FOUND, CLIENT_ERROR, ORDERBOOK_NOT_READY,
            UNKNOWN,
        ):
            assert code in REASON_CODES

    def test_reason_codes_are_distinct_strings(self):
        assert len(set(REASON_CODES)) == 9
        for code in REASON_CODES:
            assert isinstance(code, str)

    def test_reason_active_not_in_reason_codes(self):
        assert REASON_ACTIVE not in REASON_CODES
        assert REASON_ACTIVE == "ACTIVE"


# ---------------------------------------------------------------------------
# Tests: all 6 TypedDicts importable
# ---------------------------------------------------------------------------


class TestAllTypeDictsImportable:
    def test_six_typedicts_importable(self):
        names = [
            AvailabilityReason,
            AvailabilityScore,
            AvailabilitySnapshot,
            AvailabilitySummary,
            AvailabilityHealth,
            AvailabilityDiagnostics,
        ]
        assert len(names) == 6

    def test_typeddict_constructors_produce_dicts(self):
        r = AvailabilityReason(reason_code="ACTIVE", reason_detail="ok", severity="info")
        assert isinstance(r, dict)
        assert r["reason_code"] == "ACTIVE"

    def test_availability_score_constructor(self):
        s = AvailabilityScore(bid_ask_score=1.0, final_score=1.0, score_schema_version="v1")
        assert isinstance(s, dict)
        assert s["bid_ask_score"] == 1.0


# ---------------------------------------------------------------------------
# Tests: evaluate_market_availability — precedence table
# ---------------------------------------------------------------------------

_DEFAULTS = {"ticker": "BTC", "market_id": "pm-5m-btc"}

_PRECEDENCE_CASES = [
    # (id, kwargs_override, expected_reason_code)
    (
        "client_error",
        {"client_error": "timeout", "token_id": "tok",
         "accepting_orders": True, "is_active": True,
         "best_bid": 0.49, "best_ask": 0.51},
        CLIENT_ERROR,
    ),
    (
        "token_not_found_none",
        {"token_id": None, "accepting_orders": False, "is_active": False},
        TOKEN_NOT_FOUND,
    ),
    (
        "token_not_found_empty",
        {"token_id": "", "accepting_orders": True, "is_active": True},
        TOKEN_NOT_FOUND,
    ),
    (
        "market_closed_not_active",
        {"token_id": "tok", "accepting_orders": True, "is_active": False},
        MARKET_CLOSED,
    ),
    (
        "market_closed_not_accepting",
        {"token_id": "tok", "accepting_orders": False, "is_active": True},
        MARKET_CLOSED,
    ),
    (
        "stale_feed",
        {"token_id": "tok", "accepting_orders": True, "is_active": True,
         "feed_age_seconds": 90.0, "feed_staleness_threshold": 60.0},
        STALE_FEED,
    ),
    (
        "orderbook_not_ready_bid_none",
        {"token_id": "tok", "accepting_orders": True, "is_active": True,
         "best_bid": None, "best_ask": 0.5},
        ORDERBOOK_NOT_READY,
    ),
    (
        "orderbook_not_ready_ask_none",
        {"token_id": "tok", "accepting_orders": True, "is_active": True,
         "best_bid": 0.5, "best_ask": None},
        ORDERBOOK_NOT_READY,
    ),
    (
        "empty_orderbook_bid_zero",
        {"token_id": "tok", "accepting_orders": True, "is_active": True,
         "best_bid": 0.0, "best_ask": 0.5},
        EMPTY_ORDERBOOK,
    ),
    (
        "empty_orderbook_ask_zero",
        {"token_id": "tok", "accepting_orders": True, "is_active": True,
         "best_bid": 0.5, "best_ask": 0.0},
        EMPTY_ORDERBOOK,
    ),
    (
        "unknown_crossed_book",
        {"token_id": "tok", "accepting_orders": True, "is_active": True,
         "best_bid": 0.7, "best_ask": 0.3},
        UNKNOWN,
    ),
    (
        "low_liquidity",
        {"token_id": "tok", "accepting_orders": True, "is_active": True,
         "best_bid": 0.49, "best_ask": 0.51,
         "orderbook_depth": 2, "liquidity_threshold": 5},
        LOW_LIQUIDITY,
    ),
    (
        "high_spread",
        {"token_id": "tok", "accepting_orders": True, "is_active": True,
         "best_bid": 0.1, "best_ask": 0.9, "spread_threshold": 0.05},
        HIGH_SPREAD,
    ),
    (
        "active_tradable",
        {"token_id": "tok", "accepting_orders": True, "is_active": True,
         "best_bid": 0.49, "best_ask": 0.51},
        REASON_ACTIVE,
    ),
]


class TestEvaluateMarketAvailabilityPrecedence:
    @pytest.mark.parametrize("case_id,kwargs,expected_code", _PRECEDENCE_CASES, ids=[c[0] for c in _PRECEDENCE_CASES])
    def test_reason_code_precedence(self, case_id, kwargs, expected_code):
        snap = evaluate_market_availability(**{**_DEFAULTS, **kwargs})
        assert snap["reason"]["reason_code"] == expected_code, (
            f"[{case_id}] expected {expected_code}, got {snap['reason']['reason_code']}"
        )
        assert snap["state"] == expected_code

    @pytest.mark.parametrize("case_id,kwargs,expected_code", _PRECEDENCE_CASES, ids=[c[0] for c in _PRECEDENCE_CASES])
    def test_is_tradable_only_for_active(self, case_id, kwargs, expected_code):
        snap = evaluate_market_availability(**{**_DEFAULTS, **kwargs})
        if expected_code == REASON_ACTIVE:
            assert snap["is_tradable"] is True
        else:
            assert snap["is_tradable"] is False

    def test_all_nine_reason_codes_covered(self):
        covered = {kwargs_code for _, _, kwargs_code in _PRECEDENCE_CASES}
        for code in REASON_CODES:
            assert code in covered, f"{code} not covered by precedence table"


# ---------------------------------------------------------------------------
# Tests: evaluate_market_availability — golden snapshot
# ---------------------------------------------------------------------------


class TestEvaluateMarketAvailabilityGoldenSnapshot:
    def test_golden_snapshot_exact_match(self):
        snap = _make_eval_snapshot_active()
        assert snap == _EXPECTED_EVAL_SNAPSHOT

    def test_golden_snapshot_key_count(self):
        snap = _make_eval_snapshot_active()
        assert len(snap) == len(_EXPECTED_EVAL_SNAPSHOT)

    def test_no_unexpected_keys(self):
        snap = _make_eval_snapshot_active()
        assert set(snap.keys()) == set(_EXPECTED_EVAL_SNAPSHOT.keys())

    def test_reason_is_nested_dict(self):
        snap = _make_eval_snapshot_active()
        assert isinstance(snap["reason"], dict)
        assert set(snap["reason"].keys()) == {"reason_code", "reason_detail", "severity"}

    def test_schema_version_distinct_from_engine(self):
        snap = _make_eval_snapshot_active()
        assert snap["schema_version"] == "market_availability_obs_v1"
        assert snap["schema_version"] != "market_availability_v1"


# ---------------------------------------------------------------------------
# Tests: summarize_market_availability
# ---------------------------------------------------------------------------


def _btc_active_snap() -> dict:
    return evaluate_market_availability(
        ticker="BTC", market_id="pm-btc", token_id="tok-btc",
        accepting_orders=True, is_active=True,
        best_bid=0.49, best_ask=0.51,
        checked_at="2026-01-01T00:00:00Z",
    )


def _eth_active_snap() -> dict:
    return evaluate_market_availability(
        ticker="ETH", market_id="pm-eth", token_id="tok-eth",
        accepting_orders=True, is_active=True,
        best_bid=0.49, best_ask=0.51,
        checked_at="2026-01-01T00:00:00Z",
    )


def _btc_closed_snap() -> dict:
    return evaluate_market_availability(
        ticker="BTC", market_id="pm-btc-2", token_id="tok-btc-2",
        accepting_orders=False, is_active=True,
        checked_at="2026-01-01T00:00:00Z",
    )


class TestSummarizeMarketAvailability:
    def test_empty_snapshots(self):
        summary = summarize_market_availability([])
        assert summary["tradable_count"] == 0
        assert summary["non_tradable_count"] == 0
        assert summary["overall_state"] == "UNKNOWN"
        assert summary["primary_reason_code"] == REASON_ACTIVE
        assert summary["schema_version"] == "market_availability_obs_v1"

    def test_all_tradable(self):
        summary = summarize_market_availability([_btc_active_snap(), _eth_active_snap()])
        assert summary["tradable_count"] == 2
        assert summary["non_tradable_count"] == 0
        assert summary["overall_state"] == "ACTIVE"
        assert summary["primary_reason_code"] == REASON_ACTIVE
        assert summary["btc_market_count"] == 1
        assert summary["eth_market_count"] == 1
        assert summary["symbols_available"] == ["BTC", "ETH"]

    def test_mixed_tradable_and_closed(self):
        summary = summarize_market_availability(
            [_btc_active_snap(), _eth_active_snap(), _btc_closed_snap()],
        )
        assert summary["tradable_count"] == 2
        assert summary["non_tradable_count"] == 1
        assert summary["primary_reason_code"] == MARKET_CLOSED

    def test_overall_state_from_arg(self):
        summary = summarize_market_availability(
            [_btc_active_snap()],
            overall_state="BETWEEN_EPOCHS",
        )
        assert summary["overall_state"] == "BETWEEN_EPOCHS"

    def test_api_error_propagated(self):
        summary = summarize_market_availability(
            [],
            api_error="connection refused",
            api_latency_ms=500,
        )
        assert summary["api_error"] == "connection refused"
        assert summary["api_latency_ms"] == 500


# ---------------------------------------------------------------------------
# Tests: build_availability_health
# ---------------------------------------------------------------------------


class TestBuildAvailabilityHealth:
    def test_active_state_healthy(self):
        h = build_availability_health(state="ACTIVE", api_latency_ms=50, active_market_count=2)
        assert h["health_verdict"] == "HEALTHY"
        assert h["health_grade"] == "A"
        assert h["health_score"] == 1.0
        assert h["degradation_reasons"] == []
        assert h["recovery_suggestion"] == ""

    def test_between_epochs_degraded(self):
        h = build_availability_health(state="BETWEEN_EPOCHS")
        assert h["health_verdict"] == "DEGRADED"
        assert h["health_grade"] == "B"
        assert "BETWEEN_EPOCHS" in h["degradation_reasons"]

    def test_market_not_scheduled_degraded(self):
        h = build_availability_health(state="MARKET_NOT_SCHEDULED")
        assert h["health_verdict"] == "DEGRADED"
        assert h["health_grade"] == "C"

    def test_api_unavailable_unavailable(self):
        h = build_availability_health(state="API_UNAVAILABLE", error="timeout")
        assert h["health_verdict"] == "UNAVAILABLE"
        assert h["health_grade"] == "D"
        assert "API_UNAVAILABLE" in h["degradation_reasons"]
        assert "timeout" in h["degradation_reasons"]

    def test_unknown_state_unavailable_grade_f(self):
        h = build_availability_health(state="UNKNOWN")
        assert h["health_verdict"] == "UNAVAILABLE"
        assert h["health_grade"] == "F"

    def test_embeds_availability_score(self):
        h = build_availability_health(state="ACTIVE", api_latency_ms=50, active_market_count=1)
        assert "availability_score" in h
        score = h["availability_score"]
        assert "final_score" in score
        assert "bid_ask_score" in score
        assert score["score_schema_version"] == "availability_score_v1"
        assert 0.0 <= score["final_score"] <= 1.0

    def test_score_reflects_latency_penalty(self):
        low_lat = build_availability_health(state="ACTIVE", api_latency_ms=10, active_market_count=1)
        high_lat = build_availability_health(state="ACTIVE", api_latency_ms=1500, active_market_count=1)
        assert low_lat["availability_score"]["final_score"] > high_lat["availability_score"]["final_score"]

    def test_health_schema_version(self):
        h = build_availability_health(state="ACTIVE")
        assert h["schema_version"] == "availability_health_v1"


# ---------------------------------------------------------------------------
# Tests: build_market_availability_payload — golden snapshot
# ---------------------------------------------------------------------------


class TestBuildMarketAvailabilityPayloadGoldenSnapshot:
    def test_golden_snapshot_exact_match(self):
        payload = build_market_availability_payload(**_PAYLOAD_INPUTS)
        assert payload == _EXPECTED_PAYLOAD

    def test_golden_snapshot_key_count(self):
        payload = build_market_availability_payload(**_PAYLOAD_INPUTS)
        assert len(payload) == len(_EXPECTED_PAYLOAD)

    def test_no_unexpected_keys(self):
        payload = build_market_availability_payload(**_PAYLOAD_INPUTS)
        assert set(payload.keys()) == set(_EXPECTED_PAYLOAD.keys())

    def test_health_embedded_as_dict(self):
        payload = build_market_availability_payload(**_PAYLOAD_INPUTS)
        assert isinstance(payload["health"], dict)
        assert set(payload["health"].keys()) == {
            "health_score", "health_grade", "health_verdict",
            "availability_score", "degradation_reasons",
            "recovery_suggestion", "schema_version",
        }

    def test_schema_version_distinct_from_engine(self):
        payload = build_market_availability_payload(**_PAYLOAD_INPUTS)
        assert payload["schema_version"] == "market_availability_obs_v1"
        assert payload["schema_version"] != "market_availability_v1"

    def test_json_serializable(self):
        payload = build_market_availability_payload(**_PAYLOAD_INPUTS)
        dumped = json.dumps(payload)
        loaded = json.loads(dumped)
        assert loaded["state"] == "ACTIVE"
        assert loaded["primary_reason_code"] == "ACTIVE"

    def test_between_epochs_reason_code(self):
        payload = build_market_availability_payload(
            state="BETWEEN_EPOCHS",
            active_market_count=0,
            btc_market_count=0,
            checked_at="2026-01-01T00:00:00Z",
        )
        assert payload["primary_reason_code"] == EMPTY_ORDERBOOK
        assert payload["health"]["health_verdict"] == "DEGRADED"

    def test_api_unavailable_reason_code(self):
        payload = build_market_availability_payload(
            state="API_UNAVAILABLE",
            error="connection refused",
            checked_at="2026-01-01T00:00:00Z",
        )
        assert payload["primary_reason_code"] == CLIENT_ERROR
        assert payload["health"]["health_verdict"] == "UNAVAILABLE"
        assert payload["health"]["degradation_reasons"] == [
            "API_UNAVAILABLE", "connection refused"
        ]

    def test_symbols_available_defaults_to_empty_list(self):
        payload = build_market_availability_payload(
            state="MARKET_NOT_SCHEDULED",
        )
        assert payload["symbols_available"] == []
        assert payload["matching_slugs"] == []
