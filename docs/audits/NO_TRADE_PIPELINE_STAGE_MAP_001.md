# NO_TRADE_PIPELINE_STAGE_MAP_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

This document maps the sequential stages of the candidate market evaluation pipeline in the Polymarket Crypto 5M Quant Engine, showing where candidates are processed, checked, and vetoed.

---

## The Candidate Pipeline Stage Map

```
   [ 1. MARKET DISCOVERY ]
              │
              ▼
   [ 2. TOKEN RESOLUTION ] ──────► Block: token_mapping_warning
              │
              ▼
   [ 3. ORDERBOOK READINESS ] ───► Block: clob_empty_response / ClobOrderbookCooldown
              │
              ▼
   [ 4. CUTOFF TIME CHECK ] ─────► Block: time_unsafe (remaining_seconds < 90s)
              │
              ▼
   [ 5. SIGNAL GENERATION ] ─────► Skip: score <= 0.0 (no trade signal)
              │
              ▼
   [ 6. PROBABILITY MODEL ] ─────► Block: confidence < confidence_floor (0.54)
              │
              ▼
   [ 7. EV CALCULATION ] ────────► Block: ev <= min_ev (0.02)
              │
              ▼
   [ 8. DECISION GATES ] ────────► Block: max_active_positions, duplicate_order, delta_extreme
              │
              ▼
   [ 9. RISK MANAGER GATES ] ────► Block: drawdown lockdown, max_market_exposure
              │
              ▼
   [ 10. POSITION SIZING ] ──────► Block: below_min_position_size / risk_plan_zero
              │
              ▼
   [ 11. ORDERINTENT CHECK ] ────► Block: reconciliation_gate_blocked, lockdown_active
              │
              ▼
   [ 12. PAPER EXECUTION ] ──────► Simulated Fill (paper order created)
```

---

## Detailed Stage Analysis

### 1. Market Discovery
* **Target Path**: `polymarket/trader.py:L7400` -> `_select_markets`
* **Function**: Queries Gamma API or creates synthetic candidates for target assets (BTC/ETH).
* **Vetoes/Gates**: None. Universal mock assets are always injected.

### 2. Token / Condition ID Resolution
* **Target Path**: `polymarket/trader.py:L3569` -> `_promote_preloaded_market`
* **Function**: Resolves the exact Polymarket CLOB condition ID and YES/NO token IDs for the active 5-minute epoch.
* **Vetoes/Gates**: If mappings are missing, the loop logs `missing_yes_no_token_ids` and skips the cycle.

### 3. Orderbook Ingestion & Readiness
* **Target Path**: `polymarket/client.py:L622` -> `get_orderbook`
* **Function**: Requests bid/ask levels and sizes for YES and NO tokens from the CLOB API.
* **Vetoes/Gates**: 
  - Raises `clob_empty_response` on empty response payloads.
  - Raises `stale_orderbook` if snapshot timestamp age is > 3 seconds.
  - Raises `ClobOrderbookCooldown` if the client's internal rate-limiting circuit breaker is open.

### 4. Cutoff Time Check
* **Target Path**: `polymarket/trader.py:L9387`
* **Function**: Checks the remaining seconds before the active 5-minute market epoch matures.
* **Vetoes/Gates**: Blocks cycles if remaining time is less than the `execution_entry_cutoff_seconds` (default: 90 seconds).

### 5. Signal Generation
* **Target Path**: `polymarket/signal.py` -> `compute_realtime_signal`
* **Function**: Computes RSI, volume ratios, ADX, and orderbook imbalance to determine the market trend or reversion side (YES/NO/SKIP).
* **Vetoes/Gates**: Skips if the strategy indicators return neutral/skipped states.

### 6. Probability / Confidence Model
* **Target Path**: `polymarket/probability_model.py` -> `estimate_probability`
* **Function**: Estimates true win probability based on price velocity, distance to strike, and orderbook imbalances.
* **Vetoes/Gates**: Blocks if the probability confidence score is below the configured `confidence_floor` (default: 0.54).

### 7. Expected Value (EV) Calculation
* **Target Path**: `polymarket/expected_value.py` -> `scan_opportunities`
* **Function**: Subtracts market price and bid-ask spread costs from win probability to find the net expected value.
* **Vetoes/Gates**: Blocks if `ev <= 0.02` (standard EV threshold).

### 8. Decision Gate Vetoes
* **Target Path**: `polymarket/trader.py:L9751-L9765`
* **Function**: Applies structural bounds (max positions, duplicate trades, price limits).
* **Vetoes/Gates**: 
  - Blocks if `delta.delta_regime == DeltaRegime.EXTREME`.
  - Blocks if the asset was already panic-sold or entered in this cycle.

### 9. Risk Manager Budget
* **Target Path**: `utils/risk_manager.py` & `polymarket/risk_modes.py`
* **Function**: Verifies portfolio health, realized daily loss limits, and consecutive loss cluster pauses.
* **Vetoes/Gates**: Blocks all entries if `can_trade() = False` (due to drawdown or lockdown modes).

### 10. Sizing & MEF checks
* **Target Path**: `polymarket/position_sizing.py` -> `calculate_position_size`
* **Function**: Computes the optimal USDC risk plan allocation.
* **Vetoes/Gates**: 
  - Blocks with `below_min_position_size` if sizing falls below minimum bounds.
  - Micro-Survival Mode rescues this **only** if no other decision-level vetoes (low confidence, delta extreme) are active.

### 11. OrderIntent Verification
* **Target Path**: `polymarket/order_intent.py` -> `validate_order_intent`
* **Function**: Run-time sanity check before order dispatch.
* **Vetoes/Gates**: Blocks on `reconciliation_gate_blocked` (if local ledger disagrees with CLOB) or `lockdown_active`.

### 12. Paper Execution
* **Target Path**: `polymarket/trader.py:L12026`
* **Function**: Simulates order match and appends position to local tracker.
* **Vetoes/Gates**: None. Simulated fill completes.

---

## Safety Statement
* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Live behavior changed**: No
