# MARKET_INTELLIGENCE_DEPENDENCY_GRAPH_001

## 1. Data Flow & Component Architecture

Below is the complete data flow and dependency graph of the Market Intelligence Layer:

```mermaid
graph TD
    %% Data Inputs
    subgraph Market Feeds
        feed_ob["CLOB WebSockets (Orderbook)"]
        feed_candle["Gamma REST API (Candles)"]
    end

    %% Market Intelligence Processing
    subgraph Market Intelligence Layer (MIL)
        ob_parser["Feature Extraction Parser"]
        indicators["Technical Indicators Engine (ATR, EMA, RSI)"]
        vol_eng["Volatility Engine"]
        trend_eng["Trend Engine"]
        comp_eng["Compression Engine"]
        rev_eng["Reversal Detection Engine"]
        prob_eng["Probability Engine"]
        regime_eng["Regime Classifier"]
        snapshot["MarketStateSnapshot Builder"]
    end

    %% Telemetry & Storage
    subgraph Telemetry & Logging
        logger["Quant Event Logger"]
        decision_log["decision_log.jsonl"]
    end

    %% Consumers
    subgraph Consumers & Analytics
        dashboard["Dashboard Aggregator"]
        replay["Replay Analyzer"]
        future_inv["Lifecycle Inventory Engine (Future Phase)"]
    end

    %% Connections
    feed_ob --> ob_parser
    feed_candle --> ob_parser
    ob_parser --> indicators
    indicators --> vol_eng
    indicators --> trend_eng
    indicators --> comp_eng
    indicators --> rev_eng
    trend_eng --> prob_eng
    rev_eng --> prob_eng
    vol_eng --> regime_eng
    trend_eng --> regime_eng
    comp_eng --> regime_eng
    
    vol_eng --> snapshot
    trend_eng --> snapshot
    comp_eng --> snapshot
    rev_eng --> snapshot
    prob_eng --> snapshot
    regime_eng --> snapshot

    snapshot --> logger
    logger --> decision_log
    decision_log --> dashboard
    decision_log --> replay
    snapshot --> future_inv
```

---

## 2. Dependency Boundaries

To preserve safety and modularity, the codebase is partitioned into distinct isolation zones:

```text
[ Isolation Zone 1: Feeds ] ────> [ Isolation Zone 2: MIL ] ────> [ Isolation Zone 3: Sizing/Risk/Execution ]
```

* **Zone 1 (Feeds)**: Responsible only for network retrieval and raw ingestion (WebSockets, REST API).
* **Zone 2 (Market Intelligence)**: Implements passive calculations, math models, and classifications. Strictly read-only relative to wallet/orders.
* **Zone 3 (Sizing, Risk, Execution)**: Consumes Zone 2 output state snapshots to enforce sizing constraints and place orders.

---

## 3. Forbidden Dependency Directions

To prevent tight coupling and accidental trade loop activation, the following import/dependency directions are strictly **FORBIDDEN**:

1. **Passive-Only Rule**: The Market Intelligence Engine must NEVER import from Strategy, Sizer, Risk, or Execution modules:
   - *Forbidden*: `from polymarket.trader import Trader` in `polymarket/regime_diagnostics.py`
   - *Forbidden*: `from utils.risk_manager import RiskManager` in `polymarket/regime_diagnostics.py`
2. **Execution Independence**: Sizing, risk, and execution modules must only read computed fields from the `MarketState` snapshot. They must not contain internal recalculations of indicator formulas:
   - *Reason*: Avoids code duplication and guarantees that dashboard, TUI, logs, and execution evaluate the exact same indicator logic.
3. **No Direct Wallet/CLOB Actions**: The MIL must not invoke order signing, balances check, or CLOB client buy/sell methods under any circumstance.
