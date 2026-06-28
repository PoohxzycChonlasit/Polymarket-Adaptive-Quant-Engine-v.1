# MARKET_INTELLIGENCE_CONTRACTS_EXPANSION_001

## 1. Final Verdict
* **FINAL_VERDICT**: `DESIGN_COMPLETE_EXPANSION_NOT_STARTED`
* **Status**: Completed formalizing the Market Intelligence Layer contracts, schemas, and dependency graph.

## 2. Files Created
1. `docs/architecture/MARKET_INTELLIGENCE_CONTRACTS_001.md`: Defines formal python interface data structures, producer/consumer matrix, and archetype rules.
2. `docs/architecture/MARKET_STATE_SCHEMA_001.md`: Specifies the exact fields, types, JSONL serialization rules, and legacy row defaults.
3. `docs/architecture/MARKET_INTELLIGENCE_DEPENDENCY_GRAPH_001.md`: Graphs the complete data flow using Mermaid diagrams and establishes forbidden import rules.

## 3. Safety Verdict
* **SAFETY_VERDICT**: `PASS`
* **Compliance**:
  - Strictly docs-only modifications.
  - No Python runtime files changed.
  - Zero risk of execution path change.
  - No strategy or sizing threshold modifications.

## 4. Future Implementation Path
When implementing this layer in subsequent phases:
1. **Types Integration**: Add the interface contracts to `polymarket/types.py` or `polymarket/regime_diagnostics.py`.
2. **Calculation Hardening**: Expand the calculations in `polymarket/regime_diagnostics.py` to populate the `MarketIntelligenceSnapshot` fields.
3. **Telemetry Integration**: Wire the snapshot builder into the main quant loop in `polymarket/trader.py` to write JSONL lines of type `market_state_snapshot`.
4. **Dashboard Enrichment**: Extend the React dashboard and TUI page to display these metrics.

## 5. Remaining Uncertainty
* **Calculated Volatility Archetypes**: Need to review historical candle spreads for ETH and political markets to calibrate exact threshold boundaries for `extreme_volatility` flags.
