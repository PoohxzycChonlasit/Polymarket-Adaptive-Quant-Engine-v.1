def enrich_paper_accounting_telemetry(payload: dict, trader: "PolymarketTrader") -> dict:
    """
    Enrich telemetry payload with capital basis, bankroll separation metadata,
    and CLOB-compliant sizing percentages to ensure paper edge evidence is
    never misrepresented as a $20 live claim.
    """
    if payload is None:
        payload = {}
        
    state = trader.bankroll_state
    if not state:
        return payload
        
    payload.setdefault("capital_basis", state.capital_basis)
    payload.setdefault("paper_research_bankroll_usd", state.paper_research_bankroll_usd)
    payload.setdefault("live_reference_bankroll_usd", state.live_reference_bankroll_usd)
    payload.setdefault("valid_for_live_reference_bankroll_claim", state.valid_for_live_reference_bankroll_claim)
    payload.setdefault("deprecated_valid_for_live_20_bankroll_claim", state.deprecated_valid_for_live_20_bankroll_claim)
    payload.setdefault("valid_for_strategy_edge_research", state.valid_for_strategy_edge_research)
    
    proposed_notional = payload.get("proposed_notional") or payload.get("cost_to_enter") or payload.get("execution_cost") or payload.get("trade_cost")
    
    if proposed_notional is not None:
        try:
            notional = float(proposed_notional)
            if state.paper_research_bankroll_usd > 0:
                payload.setdefault("position_notional_pct_of_research_bankroll", notional / state.paper_research_bankroll_usd)
            if state.live_reference_bankroll_usd > 0:
                payload.setdefault("position_notional_pct_of_live_reference_bankroll", notional / state.live_reference_bankroll_usd)
        except (ValueError, TypeError):
            pass
            
    if payload.get("clob_size_valid") and payload.get("clob_tick_valid"):
        payload.setdefault("clob_compliant_paper_trade", True)
    elif payload.get("capital_basis") == "LIVE_BANKROLL":
        payload.setdefault("clob_compliant_paper_trade", None)
    elif payload.get("execution_realism_status") in ("PAPER_ONLY_DUST_REJECTED", "PAPER_ONLY_TICK_REJECTED"):
        payload.setdefault("clob_compliant_paper_trade", False)

    return payload
