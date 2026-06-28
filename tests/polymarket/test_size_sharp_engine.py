from pathlib import Path

from config.settings import Settings
from polymarket.size_sharp_engine import SizeSharpEngine, SizeSharpInput
from polymarket.trader import PolymarketTrader


def _base_input(**overrides):
    values = {
        "probability": 0.62,
        "fair_value": 0.62,
        "ev": 0.11,
        "ev_after_spread": 0.09,
        "confidence": 0.78,
        "spread": 0.03,
        "depth_usd": 50.0,
        "quote_age_ms": 500,
        "fill_probability": 0.80,
        "slippage_risk": 0.10,
        "regime": "TREND",
        "volatility": 0.25,
        "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
        "seconds_remaining": 150,
        "current_exposure": 2.0,
        "market_exposure": 0.0,
        "open_position_count": 1,
        "bankroll_rank": 1.0,
        "capital_score": 0.85,
        "capital_state": "HEALTHY",
        "risk_mode": "NORMAL",
        "alternative_candidate_count": 1,
        "best_alternative_ev_after_spread": 0.04,
        "recent_rejected_opportunity_count": 0,
        "recent_rejected_best_ev_after_spread": None,
        "candidate_rank_in_cycle": 1,
    }
    values.update(overrides)
    return SizeSharpInput(**values)


def test_engine_output_is_deterministic_and_schema_stable():
    engine = SizeSharpEngine()
    first = engine.evaluate(_base_input())
    second = engine.evaluate(_base_input())

    assert first == second
    assert 0.0 <= first.size_sharp <= 1.0
    assert first.schema_version == "size_sharp_v1"
    assert first.size_sharp_bucket in {"BLOCKED", "WEAK", "WATCH", "GOOD", "STRONG", "ELITE"}
    assert first.deployment_state == f"OBSERVE_{first.size_sharp_bucket}"
    assert set(first.component_scores) == {
        "signal_edge",
        "execution_quality",
        "market_state",
        "inventory_room",
        "capital_alignment",
        "opportunity_cost",
    }


def test_missing_ev_caps_score_and_reports_missing_input():
    result = SizeSharpEngine().evaluate(_base_input(ev=None, ev_after_spread=None))

    assert result.size_sharp <= 0.45
    assert "missing_ev" in result.hard_caps
    assert "ev_after_spread" in result.missing_inputs
    assert result.limiting_factor == "missing_inputs"


def test_critical_capital_and_lockdown_caps_score():
    critical = SizeSharpEngine().evaluate(_base_input(capital_state="CRITICAL"))
    lockdown = SizeSharpEngine().evaluate(_base_input(risk_mode="LOCKDOWN"))

    assert critical.size_sharp <= 0.30
    assert "capital_critical" in critical.hard_caps
    assert lockdown.size_sharp == 0.0
    assert lockdown.size_sharp_bucket == "BLOCKED"
    assert "risk_mode_lockdown" in lockdown.hard_caps


def test_stale_quote_spread_depth_and_inventory_caps_are_visible():
    result = SizeSharpEngine().evaluate(
        _base_input(
            quote_age_ms=6000,
            spread=0.20,
            depth_usd=0.25,
            market_exposure=20.0,
            open_position_count=6,
        )
    )

    assert result.size_sharp <= 0.20
    assert "stale_quote" in result.hard_caps
    assert "excessive_spread" in result.hard_caps
    assert "low_depth" in result.hard_caps
    assert "inventory_concentration" in result.hard_caps
    assert result.confidence_grade in {"C", "D", "F"}


def test_bucket_mapping_and_confidence_grade_boundaries():
    engine = SizeSharpEngine()

    assert engine.bucket_for_score(0.00) == "BLOCKED"
    assert engine.bucket_for_score(0.20) == "WEAK"
    assert engine.bucket_for_score(0.40) == "WATCH"
    assert engine.bucket_for_score(0.60) == "GOOD"
    assert engine.bucket_for_score(0.75) == "STRONG"
    assert engine.bucket_for_score(0.90) == "ELITE"

    assert engine.confidence_grade_for(missing_count=0, hard_caps=[]) == "A"
    assert engine.confidence_grade_for(missing_count=2, hard_caps=[]) == "B"
    assert engine.confidence_grade_for(missing_count=4, hard_caps=["stale_quote"]) == "D"
    assert engine.confidence_grade_for(missing_count=7, hard_caps=["risk_mode_lockdown"]) == "F"


def test_trader_size_sharp_helpers_are_observability_only():
    engine_result = SizeSharpEngine().evaluate(_base_input())
    metadata = PolymarketTrader._size_sharp_metadata(engine_result)

    assert metadata["size_sharp_at_entry"] == engine_result.size_sharp
    assert metadata["size_sharp_bucket"] == engine_result.size_sharp_bucket
    assert metadata["size_sharp_schema_version"] == "size_sharp_v1"
    assert "risk_plan" not in metadata
    assert "position_size" not in metadata


def test_trader_evaluation_emits_passive_size_sharp_event(tmp_path):
    settings = Settings()
    settings.paper_trading = True
    settings.quant_data_dir = str(tmp_path / "quant_data")
    trader = PolymarketTrader(settings=settings)
    emitted = []
    trader._emit_quant_event = lambda event_type, payload: emitted.append((event_type, payload))

    result = trader._evaluate_size_sharp_observability(
        ticker="BTC",
        market_id="test-market",
        side="YES",
        probability=0.62,
        fair_value=0.62,
        ev=0.10,
        ev_after_spread=0.08,
        confidence=0.75,
        spread=0.03,
        depth_usd=25.0,
        quote_age_ms=500,
        fill_probability=0.80,
        slippage_risk=0.10,
        lifecycle_phase="ACTIVE_INVENTORY_TRADING",
        seconds_remaining=150,
        current_exposure=0.0,
        market_exposure=0.0,
        open_position_count=0,
        bankroll_rank=1.0,
        capital_score=0.85,
        capital_state="HEALTHY",
        risk_mode="NORMAL",
    )

    assert emitted[0][0] == "log_size_sharp_evaluation"
    assert emitted[0][1]["event_type"] == "log_size_sharp_evaluation"
    assert emitted[0][1]["size_sharp"] == result.size_sharp
    assert emitted[0][1]["schema_version"] == "size_sharp_v1"


def test_trader_source_does_not_feed_size_sharp_into_policy_paths():
    source = Path("polymarket/trader.py").read_text(encoding="utf-8")
    forbidden_contexts = (
        "build_order_plan",
        "_maybe_apply_micro_survival_plan",
        "_apply_risk_mode_to_plan",
        "_submit_order",
        "place_limit_order",
        "validate_order_intent",
    )

    for line in source.splitlines():
        if "size_sharp" in line:
            assert not any(context in line for context in forbidden_contexts)
