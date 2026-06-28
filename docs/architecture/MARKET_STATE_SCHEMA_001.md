# MARKET_STATE_SCHEMA_001

## 1. Schema Specifications

* **Schema Version**: `market_state_v1`
* **Format**: Single-line JSON representation (JSON Lines compatible)

### Field Map & Types

| Field JSON Path | Type | Nullable | Allowed Enums / Range | Default Value | Description |
|---|---|---|---|---|---|
| `schema_version` | `STRING` | No | `"market_state_v1"` | `"market_state_v1"` | Schema contract identifier. |
| `timestamp_utc` | `STRING` | No | ISO-8601 UTC format | `""` | ISO timestamp of evaluation cycle. |
| `market_key` | `STRING` | No | Match regex `^[A-Z0-9\-]+$` | `""` | Market identifier (e.g. `BTC-20260628-2100`). |
| `regime.market_regime` | `STRING` | No | `"TREND_UP"`, `"TREND_DOWN"`, `"SIDEWAY"`, `"COMPRESSION"`, `"EXTREME_VOLATILITY"`, `"UNKNOWN"` | `"UNKNOWN"` | Mutually exclusive regime label. |
| `regime.volatility_regime` | `STRING` | No | `"LOW_VOL"`, `"NORMAL_VOL"`, `"HIGH_VOL"`, `"EXTREME_VOL"`, `"UNKNOWN"` | `"UNKNOWN"` | Volatility band classification. |
| `regime.trend_regime` | `STRING` | No | `"SIDEWAY"`, `"WEAK_UPTREND"`, `"STRONG_UPTREND"`, `"WEAK_DOWNTREND"`, `"STRONG_DOWNTREND"`, `"BREAKOUT"`, `"REVERSAL_RISK"`, `"UNKNOWN"` | `"UNKNOWN"` | Detailed trend-specific regime label. |
| `regime.reason` | `STRING` | No | Raw string | `""` | Traceable reason parameters. |
| `probability_engine.bullish_probability` | `FLOAT` | No | `0.05` to `0.95` | `0.5` | Estimated probability of bullish finish. |
| `probability_engine.bearish_probability` | `FLOAT` | No | `0.05` to `0.95` | `0.5` | Estimated probability of bearish finish. |
| `probability_engine.confidence_score` | `FLOAT` | No | `0.0` to `1.0` | `1.0` | Reliability indicator of calculation. |
| `trend_engine.trend_strength` | `FLOAT` | No | `0.0` to `1.0` | `0.0` | Strength coefficient. |
| `trend_engine.momentum_persistence` | `FLOAT` | No | `0.0` to `1.0` | `0.0` | Candle persistence ratio. |
| `trend_engine.ema_gap` | `FLOAT` | No | Real numbers | `0.0` | Percentage distance between EMAs. |
| `trend_engine.ema_slope` | `FLOAT` | No | Real numbers | `0.0` | Slope of fast EMA. |
| `volatility_engine.atr_14` | `FLOAT` | No | Non-negative real numbers | `0.0` | Average True Range over 14 cycles. |
| `volatility_engine.realized_volatility_30` | `FLOAT` | No | Non-negative real numbers | `0.0` | Stdev of log price changes. |
| `volatility_engine.volatility_score` | `FLOAT` | No | Non-negative real numbers | `0.0` | Normalised volatility. |
| `compression_engine.compression_score` | `FLOAT` | No | `0.0` to `1.0` | `0.0` | Normalized squeeze rating. |
| `compression_engine.bandwidth_ratio` | `FLOAT` | No | Non-negative real numbers | `0.0` | Bollinger Band width ratio. |
| `reversal_detection.rsi_14` | `FLOAT` | No | `0.0` to `100.0` | `50.0` | Relative Strength Index (14-period). |
| `reversal_detection.z_score_20` | `FLOAT` | No | Real numbers | `0.0` | Deviation from moving average. |
| `reversal_detection.vwap_deviation` | `FLOAT` | No | Real numbers | `0.0` | Close excursion from VWAP. |
| `reversal_detection.reversal_risk` | `FLOAT` | No | `0.0` to `1.0` | `0.0` | Calculated reversal probability weight. |
| `indicator_evidence.formatted` | `STRING` | No | Text | `""` | Formatted telemetry context string. |

---

## 2. Serialization & Storage Rules

1. **Format Constraint**: Must be serialized as a single compact line (no carriage returns or indentation inside rows).
2. **Target File Location**: Append-only JSONL files saved in the runtime logging directory:
   - `runtime/decision_logs/decision_log_[YYYYMMDD].jsonl`
   - Event type tag: `"event_type": "market_state_snapshot"`
3. **Number Rounding**: All float values must be rounded to exactly **8 decimal places** prior to serialization to conserve log space and optimize replay parsing speeds:
   `"bullish_probability": round(val, 8)`

---

## 3. Legacy Row Handling

Pre-MIL logs do not contain the nested `market_state_snapshot` fields. Downstream ingestion modules (such as `quant_data_quality` and `dashboard_state_aggregator`) must apply these parser rules:

1. **Existence Guard**: Check if `schema_version` is present. If missing, treat as a legacy row.
2. **Missing Field Injection**: Populate the missing structures using default values from the schema definition above:
   ```python
   def parse_legacy_row(row: dict) -> dict:
       if "schema_version" not in row:
           row["schema_version"] = "market_state_v1"
           row["regime"] = {
               "market_regime": "UNKNOWN",
               "volatility_regime": "UNKNOWN",
               "trend_regime": "UNKNOWN",
               "reason": "legacy_log_row"
           }
           row["probability_engine"] = {
               "bullish_probability": 0.5,
               "bearish_probability": 0.5,
               "confidence_score": 0.0
           }
           # ... populate remaining defaults ...
       return row
   ```

---

## 4. Replay Compatibility & Determinism

To ensure replay reproducibility:
* **Seed Neutrality**: Engines must use only deterministic indicators derived from price sequences and orderbooks. No random seeds, time-dependent network latency features, or system performance metrics may be used to classify states.
* **Interval alignment**: Replay analysis tools (`tools/replay/runtime_event_replay.py`) must evaluate the features at the exact historical timestamp of the trade decision cycle to guarantee identical outcomes.
