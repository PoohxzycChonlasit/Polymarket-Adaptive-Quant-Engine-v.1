# MARKET_INTELLIGENCE_CONTRACTS_001

## 1. Interface Contracts

Below are the formal Python `dataclass` contract structures that define the Market Intelligence Layer (MIL) interfaces.

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass(frozen=True)
class FeatureVector:
    """Raw features extracted from raw market data feed updates."""
    timestamp_utc: str
    price: float
    spread: float
    liquidity_usd: float
    quote_age_ms: int
    seconds_remaining: float
    closes_5m: List[float] = field(default_factory=list)
    opens_5m: List[float] = field(default_factory=list)
    highs_5m: List[float] = field(default_factory=list)
    lows_5m: List[float] = field(default_factory=list)
    vols_5m: List[float] = field(default_factory=list)
    closes_1m: List[float] = field(default_factory=list)
    opens_1m: List[float] = field(default_factory=list)

@dataclass(frozen=True)
class VolatilityResult:
    """Volatility metrics computed by the Volatility Engine."""
    atr_14: float
    realized_volatility_30: float
    volatility_score: float
    volatility_regime: str  # "LOW_VOL" | "NORMAL_VOL" | "HIGH_VOL" | "EXTREME_VOL"

@dataclass(frozen=True)
class TrendResult:
    """Trend and directionality metrics computed by the Trend Engine."""
    trend_regime: str       # "SIDEWAY" | "WEAK_UPTREND" | "STRONG_UPTREND" | "WEAK_DOWNTREND" | "STRONG_DOWNTREND" | "BREAKOUT"
    trend_strength: float   # Normalized 0.0 to 1.0
    momentum_persistence: float
    ema_gap: float
    ema_slope: float

@dataclass(frozen=True)
class CompressionResult:
    """Squeeze metrics computed by the Compression Engine."""
    compression_score: float  # Normalized 0.0 to 1.0
    bandwidth_ratio: float

@dataclass(frozen=True)
class ReversalRiskResult:
    """Mean reversion exhaustion metrics computed by Reversal Detection."""
    rsi_14: float
    z_score_20: float
    vwap_deviation: float
    reversal_risk: float      # Normalized 0.0 to 1.0

@dataclass(frozen=True)
class ProbabilityResult:
    """Directional probabilities computed by the Probability Engine."""
    bullish_probability: float  # 0.05 to 0.95
    bearish_probability: float  # 0.05 to 0.95
    confidence_score: float     # 0.0 to 1.0

@dataclass(frozen=True)
class RegimeResult:
    """Mutually exclusive regime classification result."""
    market_regime: str      # "TREND_UP" | "TREND_DOWN" | "SIDEWAY" | "COMPRESSION" | "EXTREME_VOLATILITY"
    volatility_regime: str  # "LOW_VOL" | "NORMAL_VOL" | "HIGH_VOL" | "EXTREME_VOL"
    trend_regime: str       # "SIDEWAY" | "WEAK_UPTREND" | "STRONG_UPTREND" | ...
    reason: str

@dataclass(frozen=True)
class IndicatorEvidence:
    """Formatted evidence summary of all technical indicators."""
    formatted: str

@dataclass(frozen=True)
class ConfidenceResult:
    """Data quality and latency check confidence metrics."""
    confidence_score: float  # 0.0 to 1.0
    data_fresh: bool
    latency_ok: bool

@dataclass(frozen=True)
class MarketIntelligenceSnapshot:
    """Aggregated immutable snapshot of the entire Market Intelligence Layer."""
    schema_version: str = "market_state_v1"
    timestamp_utc: str = ""
    market_key: str = ""
    features: Optional[FeatureVector] = None
    regime: Optional[RegimeResult] = None
    probability_engine: Optional[ProbabilityResult] = None
    trend_engine: Optional[TrendResult] = None
    volatility_engine: Optional[VolatilityResult] = None
    compression_engine: Optional[CompressionResult] = None
    reversal_detection: Optional[ReversalRiskResult] = None
    indicator_evidence: Optional[IndicatorEvidence] = None
    confidence: Optional[ConfidenceResult] = None

    def to_payload(self) -> Dict[str, object]:
        """Serializes snapshot to JSON-safe dictionary representation."""
        return {
            "schema_version": self.schema_version,
            "timestamp_utc": self.timestamp_utc,
            "market_key": self.market_key,
            "regime": {
                "market_regime": self.regime.market_regime if self.regime else "UNKNOWN",
                "volatility_regime": self.regime.volatility_regime if self.regime else "UNKNOWN",
                "trend_regime": self.regime.trend_regime if self.regime else "UNKNOWN",
                "reason": self.regime.reason if self.regime else ""
            },
            "probability_engine": {
                "bullish_probability": round(self.probability_engine.bullish_probability, 8) if self.probability_engine else 0.5,
                "bearish_probability": round(self.probability_engine.bearish_probability, 8) if self.probability_engine else 0.5,
                "confidence_score": round(self.probability_engine.confidence_score, 8) if self.probability_engine else 1.0
            },
            "trend_engine": {
                "trend_strength": round(self.trend_engine.trend_strength, 8) if self.trend_engine else 0.0,
                "momentum_persistence": round(self.trend_engine.momentum_persistence, 8) if self.trend_engine else 0.0,
                "ema_gap": round(self.trend_engine.ema_gap, 8) if self.trend_engine else 0.0,
                "ema_slope": round(self.trend_engine.ema_slope, 8) if self.trend_engine else 0.0
            },
            "volatility_engine": {
                "atr_14": round(self.volatility_engine.atr_14, 8) if self.volatility_engine else 0.0,
                "realized_volatility_30": round(self.volatility_engine.realized_volatility_30, 8) if self.volatility_engine else 0.0,
                "volatility_score": round(self.volatility_engine.volatility_score, 8) if self.volatility_engine else 0.0
            },
            "compression_engine": {
                "compression_score": round(self.compression_engine.compression_score, 8) if self.compression_engine else 0.0,
                "bandwidth_ratio": round(self.compression_engine.bandwidth_ratio, 8) if self.compression_engine else 0.0
            },
            "reversal_detection": {
                "rsi_14": round(self.reversal_detection.rsi_14, 8) if self.reversal_detection else 50.0,
                "z_score_20": round(self.reversal_detection.z_score_20, 8) if self.reversal_detection else 0.0,
                "vwap_deviation": round(self.reversal_detection.vwap_deviation, 8) if self.reversal_detection else 0.0,
                "reversal_risk": round(self.reversal_detection.reversal_risk, 8) if self.reversal_detection else 0.0
            },
            "indicator_evidence": {
                "formatted": self.indicator_evidence.formatted if self.indicator_evidence else ""
            }
        }
```

---

## 2. Producer/Consumer Ownership Model

| Module / Component | Role | Input Contract | Output Contract |
|---|---|---|---|
| **Gamma Fetcher / CLOB Feed** | Producer (Data) | Raw WebSockets / API | `FeatureVector` |
| **Market Intelligence Engine** | Orchestrator / Producer | `FeatureVector` | `MarketIntelligenceSnapshot` |
| **Volatility Engine** | Calculator | `FeatureVector` | `VolatilityResult` |
| **Trend Engine** | Calculator | `FeatureVector` | `TrendResult` |
| **Compression Engine** | Calculator | `FeatureVector` | `CompressionResult` |
| **Reversal Detection** | Calculator | `FeatureVector` | `ReversalRiskResult` |
| **Probability Engine** | Calculator | `TrendResult`, `ReversalRiskResult` | `ProbabilityResult` |
| **Regime Classifier** | Classifier | `VolatilityResult`, `TrendResult`, `CompressionResult` | `RegimeResult` |
| **Quant Event Logger** | Consumer (Logs) | `MarketIntelligenceSnapshot` | `JSONL Event Stream` |
| **Dashboard Aggregator** | Consumer (TUI/Web) | `JSONL Event Stream` | `dashboard_state.json` |
| **Replay Analyzer** | Consumer (Offline) | `QuantIntelligenceEngine` Output | Expectancy Metrics |
| **Lifecycle Inventory Engine** | Consumer (Future) | `MarketIntelligenceSnapshot` | Target Exposure Limits |

---

## 3. Backward Compatibility Rules

1. **Schema Non-Breakage**: Fields must never be deleted from the snapshot payload structure. If a metric is deprecated, it must still be serialized with a default value (e.g. `0.0` or `"UNKNOWN"`).
2. **Missing Field Tolerance**: Downstream consumers (dashboard, replay, telemetry) must use safe dictionary getters (e.g. `payload.get("compression_engine", {}).get("compression_score", 0.0)`) to ensure compatibility with legacy logs.
3. **Legacy Log Translation**: When parsing pre-MIL logs, the `quant_intelligence_engine` compiler must backfill missing indicators:
   - If `volatility_score` is missing, estimate using `realized_volatility`.
   - If `compression_score` is missing, default to `0.0`.
   - If `market_regime` is missing, fall back to `"UNKNOWN"`.

---

## 4. Multi-Market Archetype Extensibility

The interface is decoupled from specific asset pricing scales using **Normalized Ratios**:
* **Spread Ratio**: Bid-ask spread normalized by mid-price:
  $$\text{SpreadRatio} = \frac{\text{Spread}}{\text{Price}}$$
* **Depth Ratio**: USD orderbook depth normalized by normal target order size:
  $$\text{DepthRatio} = \frac{\text{Depth}_{\text{USD}}}{\text{TargetSizing}_{\text{USD}}}$$
* **Threshold Groups**: Threshold parameters (such as low/normal/extreme volatility cutoffs) are stored in archetype maps:
  ```python
  ARCHETYPE_SETTINGS = {
      "BTC_5M": {"extreme_vol_cutoff": 0.009, "base_spread_limit": 0.005},
      "ETH_5M": {"extreme_vol_cutoff": 0.012, "base_spread_limit": 0.007},
      "POLITICS_DAILY": {"extreme_vol_cutoff": 0.050, "base_spread_limit": 0.030}
  }
  ```
This allows the engine to passively interpret binary prediction markets, political event markets, and daily spot indices under a single interface contract.
