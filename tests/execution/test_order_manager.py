import pytest
from polymarket.order_manager import PolymarketOrderManager, OrderRequest

def test_order_manager_confidence_mapping_bug_fix():
    # Fix mapping safely: underdog win_rate below confidence_floor but high confidence_score 
    # should not be rejected as confidence_too_low solely due to win_rate.
    manager = PolymarketOrderManager(
        account_balance=200.0,
        max_risk_per_trade=0.05,
        stop_loss_pct=0.08,
        kelly_fraction_cap=0.25,
    )

    request = OrderRequest(
        market_id="0x123",
        side="YES",
        entry_price=0.30,      # underdog price
        win_rate=0.35,         # underdog win_rate, below default confidence_floor (0.54)
        confidence_score=0.75, # high confidence in the underdog signal
        reward_risk_ratio=2.0,
        edge=0.05,
        time_remaining_seconds=3000,
        min_position_size_usd=1.0,
    )

    plan = manager.build_order_plan(request)
    
    # It should NOT be blocked by confidence_too_low.
    assert "confidence_too_low" not in plan.diagnostics.get("blocked_reasons", [])

def test_low_confidence_score_rejected():
    manager = PolymarketOrderManager(
        account_balance=200.0,
        max_risk_per_trade=0.05,
        stop_loss_pct=0.08,
        kelly_fraction_cap=0.25,
    )

    request = OrderRequest(
        market_id="0x123",
        side="YES",
        entry_price=0.30,
        win_rate=0.35,
        confidence_score=0.40, # low confidence score < 0.54
        reward_risk_ratio=2.0,
        edge=0.05,
        time_remaining_seconds=3000,
        min_position_size_usd=1.0,
    )

    plan = manager.build_order_plan(request)
    
    # It SHOULD be blocked by confidence_too_low because confidence_score < 0.54
    assert "confidence_too_low" in plan.diagnostics.get("blocked_reasons", [])
    assert plan.position_size == 0.0

