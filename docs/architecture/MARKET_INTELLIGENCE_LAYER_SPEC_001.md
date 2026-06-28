# MARKET_INTELLIGENCE_LAYER_SPEC_001

## 1. Executive Summary & Objective

The **Market Intelligence Layer (MIL)** is the standardized market interpretation and evidence engine for the Polymarket Adaptive Quant Engine. It translates raw multi-interval orderbook and price telemetry into structured, explainable market state contexts. 

This architecture transitions the system from simple hardcoded `ENTER/SKIP` rules to a formal interpretation framework. It provides diagnostic intelligence for offline replays, dashboard visualizations, and stages future compatibility with the bounded multi-price **Quant Lifecycle Inventory Engine**.

This document represents a **DESIGN + DISCOVERY** specification. It does not modify runtime sizing, risk limits, EV thresholds, or live-trading execution paths.

---

## 2. Design Principles

1. **Offline-First & Replay-First**: The MIL modules must compile identically during live, paper, and backtest replays using historical `decision_log` and `path_truth` telemetry.
2. **Explainable and Deterministic**: All classifications must be governed by mathematical rules with traceable reasons, eliminating "black-box" model drift.
3. **Passive-Only Execution**: The layer runs side-channel diagnostics, feeding metrics to logs and alerts without altering sizer or wallet parameters.
4. **Cohesive State Serialisation**: Market indicators, probability scores, and evidence are bundled into a single immutable `MarketState` object for downstream evaluation.

---

## 3. Layered Intelligence Architecture

The MIL is composed of seven distinct engines feeding a unified Market State Object:

```
[ Raw Telemetry ] ──> [ Volatility Engine ] ────┐
                  ──> [ Trend Engine ] ─────────┼──> [ Market State Object ]
                  ──> [ Compression Engine ] ───┤
                  ──> [ Reversal Detection ] ───┤
                  ──> [ Probability Engine ] ───┘
```

### 3.1. Volatility Engine
Calculates market speed, spread, and deviation:
* **Average True Range (ATR)**: Computed over a rolling 14-period window:
  $$\text{TR} = \max(\text{High} - \text{Low}, |\text{High} - \text{Close}_{\text{prev}}|, |\text{Low} - \text{Close}_{\text{prev}}|)$$
* **Realized Volatility**: Standard deviation of log-return changes over the past 30 periods:
  $$\sigma = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (R_i - \bar{R})^2}$$
* **Volatility Score**: Normalised indicator mapping volatility to $[0, 1]$ relative to historical averages:
  $$\text{VolScore} = \max\left(\frac{\text{ATR}}{\text{Price}}, \frac{\text{Spread}}{4}\right)$$

### 3.2. Trend Engine
Quantifies directionality and persistence:
* **Trend Strength**: Combines Fast (9 EMA) and Slow (21 EMA) gaps with fast EMA slope:
  $$\text{Strength} = \text{Clamp}\left(|(EMA_{9} - EMA_{21}) / \text{Price}| \times 100, 0.0, 1.0\right)$$
* **Momentum Persistence**: Directional candle consistency over the last 8 intervals:
  $$\text{Persistence} = \frac{1}{8} \sum_{i=1}^{8} \mathbb{I}(\text{Close}_i > \text{Open}_i)$$

### 3.3. Compression Engine
Measures price squeeze and volatility contracting phases:
* **Bandwidth Squeeze**: Ratio of Bollinger Band width to moving average:
  $$\text{Bandwidth} = \frac{\text{BB}_{\text{upper}} - \text{BB}_{\text{lower}}}{\text{BB}_{\text{mid}}}$$
* **Compression Score**: Normalised value $[0, 1]$ where $1.0$ is tight consolidation:
  $$\text{Compression} = \text{Clamp}\left(\frac{\text{Threshold}_{\text{squeeze}} - \text{Bandwidth}}{\text{Threshold}_{\text{squeeze}}}, 0.0, 1.0\right)$$

### 3.4. Reversal Detection Engine
Identifies exhaustion at support/resistance levels:
* **Excursion Limits**: RSI boundaries ($RSI > 70$ or $RSI < 30$).
* **Z-Score Deviation**: Z-score of middle price relative to a 20-period rolling mean:
  $$Z = \frac{\text{Price} - \mu_{20}}{\sigma_{20}}$$
* **VWAP Deviation**: Distance between last close and Volume-Weighted Average Price:
  $$\text{VWAPDev} = \frac{\text{Price} - \text{VWAP}}{\text{VWAP}}$$

### 3.5. Probability Engine
Outputs implied directional probabilities:
* **Bullish/Bearish Probability**:Implied direction calculated by trend strength and momentum persistence, corrected downward by exhaustion-level reversal risk:
  $$P_{\text{bull}} = 0.5 + (\text{DirectionalEvidence} \times 0.22)$$
  $$P_{\text{bear}} = 1.0 - P_{\text{bull}}$$

### 3.6. Market Regime Classifier
Maps engine outputs to five mutually exclusive states:
1. **`EXTREME_VOLATILITY`**: Triggered when `VolatilityScore` exceeds extreme thresholds (e.g. $> 0.009$).
2. **`COMPRESSION`**: Consolidation with low trend strength: `CompressionScore >= 0.65` and `TrendStrength < 0.35`.
3. **`TREND_UP`**: Bullish momentum exceeding breakout threshold: `DirectionalEvidence >= 0.18`.
4. **`TREND_DOWN`**: Bearish momentum exceeding breakout threshold: `DirectionalEvidence <= -0.18`.
5. **`SIDEWAY`**: Default state when no trend, compression, or extreme volatility triggers.

---

## 4. Market State Object Schema

All metrics are consolidated into the `MarketState` payload:

```json
{
  "$schema": "https://quant.polytrade.io/schemas/market_state_v1.json",
  "timestamp_utc": "2026-06-28T15:20:00Z",
  "market_key": "BTC-20260628-2100",
  "regime": {
    "market_regime": "COMPRESSION",
    "volatility_regime": "LOW_VOL",
    "trend_regime": "SIDEWAY",
    "reason": "vol=LOW_VOL trend=SIDEWAY strength=0.120 spread=0.00150"
  },
  "probability_engine": {
    "bullish_probability": 0.52,
    "bearish_probability": 0.48,
    "confidence_score": 0.85
  },
  "trend_engine": {
    "trend_strength": 0.12,
    "momentum_persistence": 0.50,
    "ema_gap": 0.00012,
    "ema_slope": 0.00004
  },
  "volatility_engine": {
    "atr_14": 0.0012,
    "realized_volatility_30": 0.0022,
    "volatility_score": 0.0014
  },
  "compression_engine": {
    "compression_score": 0.72,
    "bandwidth_ratio": 0.0011
  },
  "reversal_detection": {
    "rsi_14": 52.4,
    "z_score_20": 0.45,
    "vwap_deviation": 0.0001,
    "reversal_risk": 0.15
  },
  "indicator_evidence": {
    "formatted": "rsi=52.4 ema_gap=0.00012 atr=0.00120 vwap_dev=0.00010"
  }
}
```

---

## 5. JSON Schema Specification

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MarketState",
  "type": "OBJECT",
  "required": [
    "$schema",
    "timestamp_utc",
    "market_key",
    "regime",
    "probability_engine",
    "trend_engine",
    "volatility_engine",
    "compression_engine",
    "reversal_detection",
    "indicator_evidence"
  ],
  "properties": {
    "$schema": { "type": "STRING" },
    "timestamp_utc": { "type": "STRING", "format": "date-time" },
    "market_key": { "type": "STRING" },
    "regime": {
      "type": "OBJECT",
      "required": ["market_regime", "volatility_regime", "trend_regime", "reason"],
      "properties": {
        "market_regime": { "type": "STRING", "enum": ["TREND_UP", "TREND_DOWN", "SIDEWAY", "COMPRESSION", "EXTREME_VOLATILITY", "UNKNOWN"] },
        "volatility_regime": { "type": "STRING", "enum": ["LOW_VOL", "NORMAL_VOL", "HIGH_VOL", "EXTREME_VOL", "UNKNOWN"] },
        "trend_regime": { "type": "STRING", "enum": ["SIDEWAY", "WEAK_UPTREND", "STRONG_UPTREND", "WEAK_DOWNTREND", "STRONG_DOWNTREND", "BREAKOUT", "REVERSAL_RISK", "UNKNOWN"] },
        "reason": { "type": "STRING" }
      }
    },
    "probability_engine": {
      "type": "OBJECT",
      "required": ["bullish_probability", "bearish_probability", "confidence_score"],
      "properties": {
        "bullish_probability": { "type": "NUMBER", "minimum": 0.0, "maximum": 1.0 },
        "bearish_probability": { "type": "NUMBER", "minimum": 0.0, "maximum": 1.0 },
        "confidence_score": { "type": "NUMBER", "minimum": 0.0, "maximum": 1.0 }
      }
    },
    "trend_engine": {
      "type": "OBJECT",
      "required": ["trend_strength", "momentum_persistence", "ema_gap", "ema_slope"],
      "properties": {
        "trend_strength": { "type": "NUMBER" },
        "momentum_persistence": { "type": "NUMBER" },
        "ema_gap": { "type": "NUMBER" },
        "ema_slope": { "type": "NUMBER" }
      }
    },
    "volatility_engine": {
      "type": "OBJECT",
      "required": ["atr_14", "realized_volatility_30", "volatility_score"],
      "properties": {
        "atr_14": { "type": "NUMBER" },
        "realized_volatility_30": { "type": "NUMBER" },
        "volatility_score": { "type": "NUMBER" }
      }
    },
    "compression_engine": {
      "type": "OBJECT",
      "required": ["compression_score", "bandwidth_ratio"],
      "properties": {
        "compression_score": { "type": "NUMBER", "minimum": 0.0, "maximum": 1.0 },
        "bandwidth_ratio": { "type": "NUMBER" }
      }
    },
    "reversal_detection": {
      "type": "OBJECT",
      "required": ["rsi_14", "z_score_20", "vwap_deviation", "reversal_risk"],
      "properties": {
        "rsi_14": { "type": "NUMBER" },
        "z_score_20": { "type": "NUMBER" },
        "vwap_deviation": { "type": "NUMBER" },
        "reversal_risk": { "type": "NUMBER", "minimum": 0.0, "maximum": 1.0 }
      }
    },
    "indicator_evidence": {
      "type": "OBJECT",
      "required": ["formatted"],
      "properties": {
        "formatted": { "type": "STRING" }
      }
    }
  }
}
```

---

## 6. Terminal Dashboard & Telemetry Additions

The MIL outputs must be displayed passively on the Terminal User Interface (TUI) and Telegram alert channels.

### TUI Panel Design (Diagnostic Only)
```text
┌───────────────────────── MARKET INTELLIGENCE ─────────────────────────┐
│  Regime: COMPRESSION      VolRegime: LOW_VOL      Trend: SIDEWAY      │
│  Bullish Prob: 0.520      Bearish Prob: 0.480     Confidence: 0.85    │
│  Trend Strength: 0.120    Momentum Persist: 0.50  Reversal Risk: 0.15 │
│  Compression: 0.720       Volatility Score: 0.001 ATR_14: 0.00120     │
│  Evidence: rsi=52.4 ema_gap=0.00012 atr=0.00120 vwap_dev=0.00010      │
└───────────────────────────────────────────────────────────────────────┘
```

### Telegram Alert Integration
```text
🔔 Polymarket Candidate Evaluated
Task/Cycle: BATCH_5A / Cycle 480
Market State: COMPRESSION (Confidence: 85%)
Bullish/Bearish: 52% / 48% (Neutral Bias)
Indicator Evidence: rsi=52.4 ema_gap=0.00012 atr=0.00120 vwap_dev=0.00010
Action Result: skipped - neutral compression boundary
```

---

## 7. Replay Compatibility & Backtest Integration

* **Historical Replay Enrichment**: The offline `quant_intelligence_engine` builder will read historical event streams and populate the nested `MarketState` metrics directly into versioned `Completed Trades` datasets.
* **Expectancy Calibration**: Offline replay analysis tools (`replay_analyzer.py`) will read the compiled `MarketState` values to calculate win rates and trade expectancies partitioned by regime:
  $$\text{Expectancy}_R = \frac{\text{Net PnL}_R}{\text{Total Trades}_R}$$
* This allows operators to determine if the platform should disable entries in specific regimes (e.g. `EXTREME_VOLATILITY`).

---

## 8. Future Extensibility: Quant Lifecycle Inventory Engine

The MIL is designed to stage future compatibility with the **Quant Lifecycle Inventory Engine**:

```
[ OPENING_SCAN ] ──> Evaluates MIL compression & trend strength triggers.
[ ACTIVE_INVENTORY_TRADING ] ──> Evaluates implied probability bias.
[ PROFIT_MANAGEMENT ] ──> Adjusts target exit thresholds based on volatility score.
[ FINAL_DERISK ] ──> Triggers forced exits if reversal risk or extreme volatility thresholds cross.
```

By standardizing these metrics inside the `MarketState` payload now, the platform establishes the data-layer contract required for bounded inventory policies without needing subsequent schema breaking changes.
