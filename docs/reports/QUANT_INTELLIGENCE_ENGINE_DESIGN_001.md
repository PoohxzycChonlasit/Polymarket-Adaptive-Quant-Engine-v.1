# Quant Intelligence Engine (QIE) - Design & Specification Report

> **DOCUMENT_TYPE: report**
> **DESTINATION:   docs/reports/QUANT_INTELLIGENCE_ENGINE_DESIGN_001.md**
> **REASON:        Design report detailing the QIE schemas, failure modes, validation strategy, and upgrade roadmap.**
>
> **TASK_CLASS: 2 DESIGN_ONLY**
> **Status: DESIGN_ONLY**
> **Runtime Impact: NONE**

---

## 1. Schema Specifications (JSON Schema Draft-07)

Every schema is version-controlled and strict to ensure compatibility between legacy and future prediction market datasets.

### 1.1 Feature Registry Schema (`feature_registry_v1`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FeatureRegistryEntry",
  "type": "object",
  "properties": {
    "feature_id": { "type": "string", "pattern": "^feat_[a-z0-9_]{8,32}$" },
    "name": { "type": "string" },
    "definition": { "type": "string" },
    "owner": { "type": "string" },
    "dependencies": { "type": "array", "items": { "type": "string" } },
    "formula_version": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$" },
    "schema_version": { "type": "string" },
    "consumers": { "type": "array", "items": { "type": "string" } },
    "units": { "type": "string" },
    "validation_status": { "type": "string", "enum": ["UNTESTED", "PASSED", "DEGRADED", "FAILED"] }
  },
  "required": ["feature_id", "name", "definition", "formula_version", "schema_version", "validation_status"]
}
```

### 1.2 Metric Registry Schema (`metric_registry_v1`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MetricRegistryEntry",
  "type": "object",
  "properties": {
    "metric_id": { "type": "string", "pattern": "^met_[a-z0-9_]{8,32}$" },
    "name": { "type": "string" },
    "definition": { "type": "string" },
    "formula_python": { "type": "string" },
    "metric_version": { "type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$" },
    "schema_version": { "type": "string" },
    "handling_nulls": { "type": "string" }
  },
  "required": ["metric_id", "name", "definition", "formula_python", "metric_version", "schema_version"]
}
```

### 1.3 Evidence Unit Schema (`evidence_unit_v1`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EvidenceUnit",
  "type": "object",
  "properties": {
    "evidence_id": { "type": "string", "pattern": "^ev_unit_[a-z0-9_]{16}$" },
    "trade_id": { "type": "string" },
    "market_id": { "type": "string" },
    "ticker": { "type": "string" },
    "market_archetype": { "type": "string", "enum": ["CRYPTO", "WEATHER", "SPORTS", "POLITICS", "PRIVATE_MARKET"] },
    "timestamp_utc": { "type": "string", "format": "date-time" },
    "predictors": {
      "type": "object",
      "properties": {
        "bankroll_rank": { "type": ["number", "null"] },
        "capital_score": { "type": ["number", "null"] },
        "capital_state": { "type": "string" },
        "size_sharp": { "type": ["number", "null"] },
        "size_sharp_bucket": { "type": "string" },
        "size_sharp_confidence_grade": { "type": "string" }
      },
      "required": ["capital_state", "size_sharp_bucket", "size_sharp_confidence_grade"]
    },
    "market_archetype_details": { "type": "object" },
    "outcome": {
      "type": "object",
      "properties": {
        "resolved_side": { "type": "string", "enum": ["YES", "NO", "FLAT"] },
        "fill_price": { "type": "number" },
        "exit_price": { "type": "number" },
        "realized_pnl": { "type": "number" },
        "win_status": { "type": "string", "enum": ["WIN", "LOSS", "FLAT"] }
      },
      "required": ["resolved_side", "realized_pnl", "win_status"]
    }
  },
  "required": ["evidence_id", "trade_id", "market_id", "market_archetype", "timestamp_utc", "predictors", "outcome"]
}
```

### 1.4 Calibration Schema (`calibration_v1`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CalibrationReport",
  "type": "object",
  "properties": {
    "calibration_id": { "type": "string", "pattern": "^cal_[a-z0-9_]{16}$" },
    "engine_version": { "type": "string" },
    "timestamp_utc": { "type": "string", "format": "date-time" },
    "evidence_sample_count": { "type": "integer" },
    "bankroll_rank_calibrations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "capital_state": { "type": "string" },
          "trade_count": { "type": "integer" },
          "win_rate": { "type": "number" },
          "expectancy": { "type": "number" },
          "sharpe_ratio": { "type": "number" }
        },
        "required": ["capital_state", "trade_count", "win_rate", "expectancy"]
      }
    },
    "size_sharp_calibrations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "bucket": { "type": "string" },
          "trade_count": { "type": "integer" },
          "win_rate": { "type": "number" },
          "expectancy": { "type": "number" },
          "max_drawdown": { "type": "number" },
          "profit_factor": { "type": "number" },
          "recovery_speed": { "type": "number" }
        },
        "required": ["bucket", "trade_count", "win_rate", "expectancy", "max_drawdown"]
      }
    },
    "calibration_quality": { "type": "number" },
    "p_value_chi_squared": { "type": "number" }
  },
  "required": ["calibration_id", "engine_version", "timestamp_utc", "evidence_sample_count", "calibration_quality"]
}
```

### 1.5 Knowledge Schema (`knowledge_v1`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "KnowledgeEntry",
  "type": "object",
  "properties": {
    "knowledge_id": { "type": "string", "pattern": "^kn_[a-z0-9_]{16}$" },
    "market_archetype": { "type": "string" },
    "applicable_market_types": { "type": "array", "items": { "type": "string" } },
    "pattern_details": { "type": "object" },
    "confidence": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
    "evidence_strength": { "type": "string", "enum": ["LOW", "MEDIUM", "STRONG"] },
    "creation_date": { "type": "string", "format": "date-time" },
    "expiry_date": { "type": ["string", "null"] },
    "validation_state": { "type": "string", "enum": ["CANDIDATE", "OBSERVED", "VALIDATED", "PRODUCTION", "DEPRECATED", "ARCHIVED"] }
  },
  "required": ["knowledge_id", "applicable_market_types", "confidence", "evidence_strength", "validation_state"]
}
```

### 1.6 Experiment Schema (`experiment_v1`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ExperimentRecord",
  "type": "object",
  "properties": {
    "experiment_id": { "type": "string", "pattern": "^exp_[a-z0-9_]{16}$" },
    "hypothesis_id": { "type": "string" },
    "baseline_version": { "type": "string" },
    "modified_formula": { "type": "object" },
    "results": {
      "type": "object",
      "properties": {
        "expectancy_delta": { "type": "number" },
        "drawdown_delta": { "type": "number" },
        "sharpe_delta": { "type": "number" },
        "turnover_delta": { "type": "number" },
        "exposure_delta": { "type": "number" }
      },
      "required": ["expectancy_delta", "drawdown_delta", "sharpe_delta"]
    },
    "accepted": { "type": "boolean" },
    "confidence_level": { "type": "number" }
  },
  "required": ["experiment_id", "hypothesis_id", "baseline_version", "results", "accepted"]
}
```

### 1.7 Recommendation Schema (`recommendation_v1`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "RecommendationEntry",
  "type": "object",
  "properties": {
    "recommendation_id": { "type": "string", "pattern": "^rec_[a-z0-9_]{16}$" },
    "type": { "type": "string", "enum": ["INCREASE_WEIGHT", "DECREASE_WEIGHT", "TIGHTEN_CAP", "LOOSEN_CAP", "DISABLE_CONTEXT", "COLLECT_MORE_DATA"] },
    "parameter_target": { "type": "string" },
    "proposed_change": { "type": "string" },
    "evidence_links": { "type": "array", "items": { "type": "string" } },
    "confidence": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
    "status": { "type": "string", "enum": ["PROPOSED", "REJECTED", "APPROVED", "IMPLEMENTED"] }
  },
  "required": ["recommendation_id", "type", "parameter_target", "proposed_change", "evidence_links", "confidence", "status"]
}
```

### 1.8 Decision Memory Schema (`decision_memory_v1`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "DecisionMemoryEntry",
  "type": "object",
  "properties": {
    "decision_id": { "type": "string", "pattern": "^dec_mem_[a-z0-9_]{16}$" },
    "timestamp_utc": { "type": "string", "format": "date-time" },
    "summary": { "type": "string" },
    "evidence_references": { "type": "array", "items": { "type": "string" } },
    "affected_formulas": { "type": "array", "items": { "type": "string" } },
    "expected_improvement": { "type": "string" },
    "rollback_conditions": { "type": "string" },
    "approved_by": { "type": "array", "items": { "type": "string" } }
  },
  "required": ["decision_id", "timestamp_utc", "summary", "evidence_references", "affected_formulas", "rollback_conditions"]
}
```

---

## 2. Dashboard Metrics Specification

The passive dashboard format for displaying offline calibration and discovered patterns to human operators:

```text
================================================================================
   QIE OFFLINE CALIBRATION DASHBOARD | V1.0.0 | RUNTIME STATE: OBSERVABILITY-ONLY
================================================================================
[SUMMARY ENGINE]
  Evidence Units: 388         Calibration Quality: 94.20%  Chi-Sq p-value: 0.0122*
  Hypotheses Validated: 3     Active Recs Staged: 2        Decisions Logged: 14

[BANKROLL RANK CALIBRATION SUMMARY]
  RANK/STATE   TRADES   WIN RATE  IMPLIED RATE  EXPECTANCY (USDC)  SHARPE
  HEALTHY      306      78.87%    72.10%        +0.4465            1.82
  DEGRADED     82       52.12%    55.00%        -0.0120            0.12
  CRITICAL     0        0.00%     --            0.0000             --

[SIZE SHARP BUCKET CALIBRATION SUMMARY]
  BUCKET       TRADES   WIN RATE  EXPECTANCY    MAX DRAWDOWN       PROFIT FACTOR
  ELITE        14       92.86%    +1.2210       -0.0210            4.85
  STRONG       120      81.20%    +0.5210       -0.0830            2.10
  GOOD         154      72.40%    +0.1240       -0.1240            1.54
  WATCH        82       51.20%    -0.0210       -0.2200            0.92
  WEAK         18       38.89%    -0.1550       -0.4500            0.62
  BLOCKED      0        0.00%     --            --                 --

[PATTERN DISCOVERY ENGINE - HIGHEST MUTUAL INFORMATION CONTEXTS]
  ID        PATTERN COMBINATION                         SUPPORT  CONF  OUTCOME
  pat_001   SizeSharp STRONG + spread < 0.02           102      88.2% +EXPECTANCY
  pat_002   Bankroll Rank DEGRADED + vol > 0.40         34       31.2% -EXPECTANCY
  pat_003   lifecycle FINAL_DERISK + quote_age > 3000   18       12.2% -EXPECTANCY

[PENDING GOVERNANCE PROPOSALS]
  ID        RECOMMENDATION                              CONF     EVIDENCE
  rec_001   TIGHTEN_CAP: spread_cap (0.06 -> 0.04)      92.4%    [pat_003/ev_unit_2]
  rec_002   INCREASE_WEIGHT: execution_quality (+10%)   84.1%    [pat_001/ev_unit_5]
================================================================================
```

---

## 3. Failure Modes & Mitigations

| Failure Mode | Root Cause | Impact | Mitigation Strategy |
|---|---|---|---|
| **Legacy Schema Mismatch** | Older database records lack `size_sharp` fields at entry. | Incomplete datasets, statistics failure, crash in compiler. | Compiler defaults legacy rows to `"UNKNOWN"`, `"missing_legacy_metadata"`, and empty collections. |
| **Survivorship/Hindsight Bias** | Counterfactual simulator uses future parameter findings on the same dataset. | Overfitted parameters, false confidence in recommendations. | Strict out-of-sample partition (e.g., train on May data, validate on June data). |
| **Low Sample Size Contamination** | Making recommendation based on $N < 30$ observations. | Spurious correlations, high variance in expectancy. | The Confidence Engine forces confidence score to zero if bucket $N < 30$. |
| **Regime Drift Blind Spot** | A formula calibrated in a low-volatility regime fails in high-volatility. | Overconfidence in stale calibration scores. | Segment all calibrations and discovered patterns by market regime (e.g. Trend vs. Compress). |
| **Unmatched Close Resolution** | Historical log drops the open event due to crash/restart. | Missing entry predictors (Size Sharp and Bankroll Rank). | Outcome classified as `Grade D` (unmatched) and skipped from core calibration metrics. |

---

## 4. Validation Strategy

To guarantee the correctness of QIE design before code implementation:

1. **Deterministic Recalculation Tests**:
   - Save a subset of compiled Evidence Units.
   - Run the Calibration Engine, alter a weight, and assert that counterfactual results match hand-calculated metrics.
2. **Schema Drift Validation**:
   - Write a unit test that validates simulated json outputs against the draft-07 schemas using `jsonschema`.
3. **No-Mutation Checks**:
   - Write tests to verify that reading inputs (Canonical Context files) does not modify the original filesystem files.
4. **Out-of-Sample Parity**:
   - Verify that counterfactual parameter outputs generated on odd-day data match the performance trend on even-day data.

---

## 5. Upgrade Roadmap

```text
========================================================================================
   PHASE 1: Passive Diagnostics & Logging (CURRENT STATE)
   - Size Sharp and Bankroll Rank run as observability-only telemetry
   - Emits event streams, updates canonical contexts, and saves status logs
========================================================================================
                                      │
                                      ▼
========================================================================================
   PHASE 2: Offline QIE Engine Implementation (NEXT TASK Target)
   - Build offline compiler and registries
   - Calculate metrics, discover patterns, run counterfactual simulations
   - Output passive calibration recommendations (human-approval gated)
========================================================================================
                                      │
                                      ▼
========================================================================================
   PHASE 3: Passive Shadow Gating (STAGING Gate)
   - Run counterfactual simulator as real-time shadow process in paper mode
   - Emits shadow-reject logs to verify would-be performance before live deployment
========================================================================================
                                      │
                                      ▼
========================================================================================
   PHASE 4: Active Sizing & Risk Integration (PRODUCTION Gate)
   - Wire Bankroll Rank and Size Sharp directly into position_sizing.py
   - Apply hard caps, thresholds, and Dynamic Risk Budget constraints
========================================================================================
```
