# Runtime Event Taxonomy V1

This document defines the high-level structure, categories, and naming conventions of the official **Runtime Event Taxonomy V1** for the Polymarket Adaptive Quant Engine.

---

## 1. Introduction

The Runtime Event Taxonomy V1 provides the single source of truth (SSoT) for event streaming, state tracking, real-time dashboard aggregation, and telemetry playback. 

Every action or state transition within the engine is classified under a designated functional category and follows a standardized schema layout.

---

## 2. Event Categories

Events are grouped into 16 distinct categories based on their origin within the quant engine:

1. **Runtime Lifecycle**: Bootstrapping, initialization, shutdown, and liveness signals.
2. **Runtime Health**: Connectivity, database, process, and external API circuit breaker status.
3. **Market Data**: Ingestion of Binance price ticks and CLOB orderbook updates.
4. **Candidate Pipeline**: Market discovery, scanning, and filtration metrics.
5. **Decision Engine**: EV (Expected Value) checks and final cycle trading actions.
6. **Risk Engine**: Drawdown checks, loss clustering, and lockdown mode alerts.
7. **Bankroll Engine**: Hysteresis tracking, rank promotions/demotions, and cash/equity updates.
8. **Position Sizing**: Sizing multiplier calculations, threshold checks, and approval gates.
9. **Order Intent**: Structural validations for ENTRY and EXIT order constraints.
10. **Paper Execution**: Virtual order generation, limit matches, and simulated fills.
11. **Exit Execution**: Take Profit (TP), Stop Loss (SL), panic, and residual exit dispatches.
12. **Inventory / Reconciliation**: Local database audits, discrepancies, and CLOB reconciliation.
13. **Analytics Loader**: Offline load events for sentiment, volatility, and regime diagnostic caches.
14. **Ghost Position Sentinel**: Startup scans and quarantine tracking.
15. **Errors / Warnings**: System exceptions and boundary warnings.
16. **Dashboard Snapshot**: Full state dump serialization events.
