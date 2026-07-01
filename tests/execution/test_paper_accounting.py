from unittest.mock import MagicMock
from polymarket.trader import PolymarketTrader, BankrollState
from polymarket.execution.paper_accounting import PAPER_RESEARCH_BANKROLL_USD

def test_paper_research_bankroll_isolation():
    # Setup mock trader with PAPER_RESEARCH_BANKROLL mode
    trader = MagicMock()
    
    # Initialize bankroll state as it would be in paper mode
    state = BankrollState(
        starting_bankroll=PAPER_RESEARCH_BANKROLL_USD,
        current_cash_balance=PAPER_RESEARCH_BANKROLL_USD,
        capital_basis="PAPER_RESEARCH_BANKROLL",
        paper_research_bankroll_usd=PAPER_RESEARCH_BANKROLL_USD,
        live_reference_bankroll_usd=10.0,
        valid_for_live_reference_bankroll_claim=False,
        valid_for_strategy_edge_research=True,
    )
    # Assume 10.0 peak so far just from init
    state.peak_bankroll = PAPER_RESEARCH_BANKROLL_USD
    state.realized_pnl = 0.0
    
    trader.bankroll_state = state
    trader._paper_open_position_entry_cost.return_value = 0.0
    
    # Extract the original method to test
    _apply_paper_reference_balance = PolymarketTrader._apply_paper_reference_balance
    
    # Execute the method against our mock trader
    live_wallet_balance = 10.0
    _apply_paper_reference_balance(trader, live_wallet_balance, reset_starting_balance=False)
    
    # VERIFY: Cash balance remains PAPER_RESEARCH_BANKROLL_USD, not live_wallet_balance
    assert trader.bankroll_state.current_cash_balance == PAPER_RESEARCH_BANKROLL_USD
    # VERIFY: Metadata is updated with live wallet balance
    assert trader.bankroll_state.live_reference_bankroll_usd == 10.0
    # VERIFY: starting_bankroll is NOT overwritten
    assert trader.bankroll_state.starting_bankroll == PAPER_RESEARCH_BANKROLL_USD
    
    # Execute again with reset_starting_balance=True (forced refresh)
    _apply_paper_reference_balance(trader, live_wallet_balance, reset_starting_balance=True)
    
    # VERIFY: Cash balance and starting bankroll STILL remain PAPER_RESEARCH_BANKROLL_USD
    assert trader.bankroll_state.current_cash_balance == PAPER_RESEARCH_BANKROLL_USD
    assert trader.bankroll_state.starting_bankroll == PAPER_RESEARCH_BANKROLL_USD
    
def test_live_bankroll_behavior():
    # Setup mock trader with normal LIVE_BANKROLL mode
    trader = MagicMock()
    
    # Initialize bankroll state as it would be in live mode
    state = BankrollState(
        starting_bankroll=10.0,
        current_cash_balance=10.0,
        capital_basis="LIVE_BANKROLL",
        paper_research_bankroll_usd=0.0,
        live_reference_bankroll_usd=10.0,
        valid_for_live_reference_bankroll_claim=True,
        valid_for_strategy_edge_research=True,
    )
    state.peak_bankroll = 10.0
    state.realized_pnl = 0.0
    
    trader.bankroll_state = state
    trader._paper_open_position_entry_cost.return_value = 0.0
    
    _apply_paper_reference_balance = PolymarketTrader._apply_paper_reference_balance
    
    # Execute the method against our mock trader
    new_live_balance = 12.0
    _apply_paper_reference_balance(trader, new_live_balance, reset_starting_balance=False)
    
    # VERIFY: Cash balance IS updated to new_live_balance
    assert trader.bankroll_state.current_cash_balance == 12.0
    # VERIFY: starting_bankroll is NOT overwritten if reset_starting_balance=False
    assert trader.bankroll_state.starting_bankroll == 10.0
    
    # Execute again with reset_starting_balance=True
    _apply_paper_reference_balance(trader, new_live_balance, reset_starting_balance=True)
    
    # VERIFY: Cash balance IS updated
    assert trader.bankroll_state.current_cash_balance == 12.0
    # VERIFY: starting_bankroll IS overwritten
    assert trader.bankroll_state.starting_bankroll == 12.0
