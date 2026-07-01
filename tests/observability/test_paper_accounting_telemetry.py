from unittest.mock import MagicMock
from polymarket.observability.paper_accounting_telemetry import enrich_paper_accounting_telemetry
from polymarket.execution.paper_accounting import PAPER_RESEARCH_BANKROLL_USD

def test_paper_accounting_telemetry_adds_capital_basis():
    mock_trader = MagicMock()
    mock_trader.bankroll_state = MagicMock()
    mock_trader.bankroll_state.capital_basis = "PAPER_RESEARCH_BANKROLL"
    mock_trader.bankroll_state.paper_research_bankroll_usd = PAPER_RESEARCH_BANKROLL_USD
    mock_trader.bankroll_state.live_reference_bankroll_usd = 20.0
    mock_trader.bankroll_state.valid_for_live_reference_bankroll_claim = False
    mock_trader.bankroll_state.deprecated_valid_for_live_20_bankroll_claim = False
    mock_trader.bankroll_state.valid_for_strategy_edge_research = True
    
    payload = {"clob_size_valid": True, "clob_tick_valid": True, "proposed_notional": 20.0}
    enriched = enrich_paper_accounting_telemetry(payload, mock_trader)
    
    assert enriched["capital_basis"] == "PAPER_RESEARCH_BANKROLL"
    assert enriched["paper_research_bankroll_usd"] == 200.0
    assert enriched["live_reference_bankroll_usd"] == 20.0
    assert enriched["valid_for_live_reference_bankroll_claim"] is False
    assert enriched["deprecated_valid_for_live_20_bankroll_claim"] is False
    assert enriched["valid_for_strategy_edge_research"] is True
    assert enriched["position_notional_pct_of_research_bankroll"] == 20.0 / 200.0
    assert enriched["position_notional_pct_of_live_reference_bankroll"] == 20.0 / 20.0
    assert enriched["clob_compliant_paper_trade"] is True

def test_canonical_builder_separation_logic():
    # Simulate a builder process to ensure paper dust count and executability are recorded
    from tools.canonical_run_evidence_summary_builder import build_trade_funnel_summary
    
    mock_records = [
        {
            "event": "log_execution",
            "capital_basis": "PAPER_RESEARCH_BANKROLL",
            "paper_research_bankroll_usd": 200.0,
            "live_reference_bankroll_usd": 10.0,
            "valid_for_live_reference_bankroll_claim": False,
            "deprecated_valid_for_live_20_bankroll_claim": False,
            "valid_for_strategy_edge_research": True,
            "clob_size_valid": True,
            "clob_tick_valid": True,
        }
    ]
    
    field_map = {
        "chainlink_reference_ts_utc": {"status": "PRESENT"},
        "order_ack_ts_utc": {"status": "PRESENT"},
        "settlement_ts_utc": {"status": "PRESENT"},
        "submit_latency_ms": {"status": "PRESENT"},
        "fill_latency_ms": {"status": "PRESENT"},
        "clock_drift_status": {"status": "PRESENT"},
    }
    summary = build_trade_funnel_summary(mock_records, run_id="test_run", field_map=field_map)
    assert summary["capital_basis"] == "PAPER_RESEARCH_BANKROLL"
    assert summary["paper_research_bankroll_usd"] == 200.0
    assert summary["live_reference_bankroll_usd"] == 10.0
    assert summary["valid_for_live_reference_bankroll_claim"] is False
    assert summary["deprecated_valid_for_live_20_bankroll_claim"] is False
    assert summary["valid_for_strategy_edge_research"] is True
    assert summary["pnl_denominator_usd"] == 200.0
    assert summary["paper_executable_candidate_count"] == 1
    assert summary["paper_dust_rejected_count"] == 0
    assert "capital_reference_warning" in summary
    assert "deprecated live_20_bankroll claim field exists" in summary["capital_reference_warning"]
