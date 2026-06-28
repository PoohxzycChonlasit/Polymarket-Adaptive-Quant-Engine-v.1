import pytest
from unittest.mock import MagicMock
from polymarket.bankroll_rank_engine import BankrollRankEngine, CapitalState, RiskProfile
from polymarket.trader import PolymarketTrader, BankrollState
from utils.position_tracker import Position
from config.settings import Settings

def test_bankroll_rank_engine_basic_evaluation():
    engine = BankrollRankEngine(alpha=0.20)
    
    # Create mock closed positions
    pos1 = MagicMock(spec=Position)
    pos1.exit_time = "2026-06-28T00:00:00Z"
    pos1.realized_pnl = 10.0
    
    pos2 = MagicMock(spec=Position)
    pos2.exit_time = "2026-06-28T00:01:00Z"
    pos2.realized_pnl = -5.0
    
    pos3 = MagicMock(spec=Position)
    pos3.exit_time = "2026-06-28T00:02:00Z"
    pos3.realized_pnl = -3.0

    # 1. Test consecutive losses streak (2 consecutive losses at the end)
    eval1 = engine.evaluate(
        current_bankroll=100.0,
        equity=100.0,
        realized_pnl=2.0,
        unrealized_pnl=0.0,
        drawdown_pct=0.0,
        closed_positions=[pos1, pos2, pos3],
    )
    
    assert eval1["metrics"]["consecutive_losses"] == 2
    assert eval1["metrics"]["consecutive_wins"] == 0
    assert eval1["expected_risk_profile"] == RiskProfile.MODERATE

    # 2. Test consecutive wins streak
    pos4 = MagicMock(spec=Position)
    pos4.exit_time = "2026-06-28T00:03:00Z"
    pos4.realized_pnl = 4.0
    
    eval2 = engine.evaluate(
        current_bankroll=104.0,
        equity=104.0,
        realized_pnl=6.0,
        unrealized_pnl=0.0,
        drawdown_pct=0.0,
        closed_positions=[pos1, pos2, pos3, pos4],
    )
    
    assert eval2["metrics"]["consecutive_losses"] == 0
    assert eval2["metrics"]["consecutive_wins"] == 1
    assert eval2["expected_risk_profile"] == RiskProfile.AGGRESSIVE

def test_bankroll_rank_engine_drawdown_penalty_and_transitions():
    engine = BankrollRankEngine(alpha=0.50) # high alpha for fast transition in tests
    
    # Initial state is healthy, score is 1.0
    assert engine.current_state == CapitalState.HEALTHY
    
    # 1. Apply high drawdown (12%)
    eval_down = engine.evaluate(
        current_bankroll=100.0,
        equity=88.0,
        realized_pnl=-12.0,
        unrealized_pnl=0.0,
        drawdown_pct=0.12,
        closed_positions=[],
    )
    
    # Drawdown penalty reduces raw score, smoothed score drops
    assert eval_down["capital_score"] < 1.0
    
    # 2. Trigger degraded transition by dropping smoothed score below 0.65
    engine.smoothed_score = 0.60
    eval_degraded = engine.evaluate(
        current_bankroll=100.0,
        equity=85.0,
        realized_pnl=-15.0,
        unrealized_pnl=0.0,
        drawdown_pct=0.15, # raw_score becomes 0.50 -> smoothed = 0.5 * 0.5 + 0.5 * 0.6 = 0.55
        closed_positions=[],
    )
    assert eval_degraded["capital_state"] == CapitalState.DEGRADED

    # 3. Hysteresis check: must clear 0.70 to return to HEALTHY from DEGRADED
    engine.smoothed_score = 0.68
    eval_still_degraded = engine.evaluate(
        current_bankroll=100.0,
        equity=100.0,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        drawdown_pct=0.0, # raw_score = 1.0 -> smoothed = 0.5 * 1.0 + 0.5 * 0.68 = 0.84, which transitions to HEALTHY
        closed_positions=[],
    )
    # Wait, if raw_score = 1.0, smoothed immediately goes to 0.84.
    # To test hysteresis keeping it in DEGRADED, we need smoothed_score to settle between 0.65 and 0.70.
    # If raw_score = 0.70, and smoothed_score starts at 0.66:
    # smoothed = 0.5 * 0.70 + 0.5 * 0.66 = 0.68. Since 0.68 < 0.70, it should remain DEGRADED!
    engine.smoothed_score = 0.66
    eval_still_degraded = engine.evaluate(
        current_bankroll=100.0,
        equity=88.0,
        realized_pnl=-12.0,
        unrealized_pnl=0.0,
        drawdown_pct=0.09, # raw_score = 1.0 - 0.09/0.15*0.5 = 0.70
        closed_positions=[],
    )
    assert eval_still_degraded["capital_state"] == CapitalState.DEGRADED
    
    # Now clear it with a high score (drawdown = 0 -> raw_score = 1.0)
    engine.smoothed_score = 0.70
    eval_healthy_again = engine.evaluate(
        current_bankroll=100.0,
        equity=100.0,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        drawdown_pct=0.0,
        closed_positions=[],
    )
    assert eval_healthy_again["capital_state"] == CapitalState.HEALTHY

def test_trader_integration_evaluates_rank_engine():
    s = Settings()
    s.paper_trading = True
    s.account_balance = 500.0
    
    trader = PolymarketTrader(settings=s)
    
    # Mock closed positions with consecutive losses
    pos1 = MagicMock(spec=Position)
    pos1.exit_time = "2026-06-28T00:00:00Z"
    pos1.realized_pnl = -10.0
    trader.tracker.closed_positions = lambda: [pos1]
    
    # Emitted events collector
    emitted_events = []
    trader._emit_quant_event = lambda event_type, payload: emitted_events.append((event_type, payload))
    
    # Update bankroll state
    state = trader._update_bankroll_state(refresh_wallet_reference=False)
    
    # Assert evaluation results stored on state
    assert state.capital_score is not None
    assert state.capital_state == "HEALTHY"
    
    # Assert JSONL log event emitted
    eval_events = [p for e_type, p in emitted_events if e_type == "log_bankroll_rank_evaluation"]
    assert len(eval_events) == 1
    assert eval_events[0]["consecutive_losses"] == 1
    assert eval_events[0]["capital_state"] == "HEALTHY"
