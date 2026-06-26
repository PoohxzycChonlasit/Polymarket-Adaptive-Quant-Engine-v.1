# BATCH_3_OBSERVABILITY_BOUNDARY_AUDIT_001

**Date:** 2026-06-27  
**Role:** 29_ARCHITECTURE_GOVERNANCE_AGENT  
**Supporting Role:** 27_VERIFICATION_OFFICER_AGENT  
**Task Class:** 1 (RESEARCH / AUDIT)  
**Verdict:** READY_FOR_BATCH_3_DESIGN  
**Active Question Status:** OPEN — LOW_PRICE_TRUTH_RESOLUTION_001  

---

## 1. Current Git & Working Tree State

- **HEAD:** `3b2944b` — docs: add batch 3 gate check
- **Working Tree:** Clean (working tree clean, no untracked/modified files except this report)
- **Compilation Check:** Success (`COMPILE_OK` for `trader.py` and `trader_lifecycle.py`)
- **Import Check:** Success (`IMPORT_OK` for `PolymarketTrader` import)

---

## 2. Candidate State Classification Matrix

Below is the classification of each candidate field/method discovered in `polymarket/trader.py` that relates to display, observability, diagnostics, and telemetry.

### 2.1 Candidate Fields

| Name | Type | Used by Runtime Loop? | Used by Execution? | Used by Risk/Sizing? | Safe to Extract? | Reason |
|---|---|---|---|---|---|---|
| `_recent_display_trades` | `deque[dict]` | No | No | No | **Yes** | Tracks recent trades for terminal display/TUI only. |
| `_observability_health_display_state` | `dict` | No | No | No | **Yes** | Holds metrics displayed on dashboard/TUI; no logic impact. |
| `_last_orderbook_age_ms` | `dict[str, int]` | Yes | Yes | Yes | **NO** | Checked by entry-pricing, freshness, and simulated execution gates. |
| `_last_orderbook_refresh_at_utc` | `dict[str, str]` | No | No | No | **Yes** | Tracks orderbook update timestamps for event payload details only. |
| `_last_orderbook_refresh_monotonic` | `dict[str, float]` | No | No | No | **Yes** | Relative timestamps used for age calculation in event logs. |
| `_last_orderbook_refresh_source` | `dict[str, str]` | No | No | No | **Yes** | Telemetry tracking for where orderbook fetch originated (e.g. websocket vs REST). |
| `_last_orderbook_refresh_trigger` | `dict[str, str]` | No | No | No | **Yes** | Telemetry tracking of event/TUI panel that triggered refresh. |
| `_last_orderbook_refresh_token_pair_key` | `dict[str, str]` | No | No | No | **Yes** | Telemetry tracking for token pair refresh key consistency. |
| `_last_successful_yes_no_book_at_utc` | `dict[str, str]` | No | No | No | **Yes** | Tracks timing of last successful yes/no orderbook fetch for logging. |
| `_last_successful_yes_no_book_monotonic` | `dict[str, float]` | No | No | No | **Yes** | Tracks relative timing of last successful fetch for logging age. |
| `_last_successful_yes_no_book_token_pair_key` | `dict[str, str]` | No | No | No | **Yes** | Tracks token pair key of last successful fetch for lineage logs. |
| `_last_quote_lineage_context` | `dict[str, dict]` | No | No | No | **Yes** | Tracks lineage details (ids/ts) to map orders to source orderbooks. |
| `_last_decision_cycle_monotonic` | `dict[str, float]` | No | No | No | **Yes** | Tracks timestamps of decision cycles for logging latency metrics. |
| `_market_evaluation_started_monotonic` | `dict[str, float]` | No | No | No | **Yes** | Tracks start of market evaluation for logging cycle speed. |
| `_market_evaluation_started_at_utc` | `dict[str, str]` | No | No | No | **Yes** | Tracks starting timestamp of market evaluation for logs. |
| `_current_cycle_market_sequence_index` | `dict[str, int]` | No | No | No | **Yes** | Sequence index for logging position in cycle loops. |
| `_current_cycle_market_sequence_count` | `dict[str, int]` | No | No | No | **Yes** | Sequence count for logging total count in cycle loops. |
| `_orderbook_warmup_pending_counts` | `Counter[str]` | Yes | Yes | Yes | **NO** | Used by market readiness checks to determine if warmup period has passed. |

### 2.2 Candidate Methods

| Name | Type | Used by Runtime Loop? | Used by Execution? | Used by Risk/Sizing? | Safe to Extract? | Reason |
|---|---|---|---|---|---|---|
| `_mark_orderbook_refresh` | Method | No | No | No | **Yes** | Records refresh telemetry; does not affect trading logic. |
| `_orderbook_refresh_observability_detail` | Method | No | No | No | **Yes** | Compiles orderbook refresh telemetry data for event logs. |
| `_scheduler_cadence_observability_detail` | Method | No | No | No | **Yes** | Compiles loop cycle latency telemetry data for event logs. |
| `_phase4_build_quote_lineage` | Method | No | No | No | **Yes** | Hashes market metadata for lineage tracing and logging. |
| `_phase4_quote_lineage_carry` | Method | No | No | No | **Yes** | Retrieves cached lineage hash for payload inclusion. |
| `_emit_hybrid_v1_snapshot` | Method | No | No | No | **Yes** | Compiles and emits hybrid metrics payload; fail-soft. |
| `_observability_health_from_payload` | Method | No | No | No | **Yes** | Formats payload metrics for health monitoring. |
| `_display_field_present` | Method | No | No | No | **Yes** | Presentation helper; wraps field checks. |
| `_display_visibility_status` | Method | No | No | No | **Yes** | Presentation helper; returns presence status strings. |
| `_display_identity_readiness` | Method | No | No | No | **Yes** | Presentation helper; returns readiness status. |
| `_display_dominant_model_gap` | Method | No | No | No | **Yes** | Presentation helper; returns model gap reason. |
| `_event_producer_label` | Method | No | No | No | **Yes** | Maps event methods to event log categories. |
| `dashboard_observability_health_state` | Method | No | No | No | **Yes** (with proxy) | Accessed by display/TUI loop; must preserve proxy on trader. |
| `get_recent_display_trades` | Method | No | No | No | **Yes** (with proxy) | Accessed by display loop; must preserve proxy on trader. |
| `_record_display_trade` | Method | No | No | No | **Yes** | Appends trades to display deque. |
| `_diagnostic_float` | Method | No | No | No | **Yes** | Formats floats safely for logging/payload outputs. |
| `_diagnostic_int` | Method | No | No | No | **Yes** | Formats integers safely for logging/payload outputs. |
| `_risk_plan_zero_diagnostics` | Method | No | No | No | **Yes** | Formats sizing details for skip-candidate events. |

---

## 3. Scope Boundaries & Extractability Lists

### 3.1 Safe-to-Extract List (Allowed for Batch 3)

The following items are safe to extract into a dedicated display/observability container helper class (e.g., `PolymarketTraderObservability` or similar) under `polymarket/orchestration/`:

1. **State Fields:**
   - `_recent_display_trades`
   - `_observability_health_display_state`
   - `_last_orderbook_refresh_at_utc`
   - `_last_orderbook_refresh_monotonic`
   - `_last_orderbook_refresh_source`
   - `_last_orderbook_refresh_trigger`
   - `_last_orderbook_refresh_token_pair_key`
   - `_last_successful_yes_no_book_at_utc`
   - `_last_successful_yes_no_book_monotonic`
   - `_last_successful_yes_no_book_token_pair_key`
   - `_last_quote_lineage_context`
   - `_last_decision_cycle_monotonic`
   - `_market_evaluation_started_monotonic`
   - `_market_evaluation_started_at_utc`
   - `_current_cycle_market_sequence_index`
   - `_current_cycle_market_sequence_count`

2. **Helper Methods:**
   - `_mark_orderbook_refresh`
   - `_orderbook_refresh_observability_detail`
   - `_scheduler_cadence_observability_detail`
   - `_phase4_build_quote_lineage`
   - `_phase4_quote_lineage_carry`
   - `_emit_hybrid_v1_snapshot`
   - `_observability_health_from_payload`
   - `_display_field_present`
   - `_display_visibility_status`
   - `_display_identity_readiness`
   - `_display_dominant_model_gap`
   - `_event_producer_label`
   - `_record_display_trade`
   - `_diagnostic_float`
   - `_diagnostic_int`
   - `_risk_plan_zero_diagnostics`

3. **Public Display Wrappers:**
   - `dashboard_observability_health_state` (proxy/delegate method only)
   - `get_recent_display_trades` (proxy/delegate method only)

### 3.2 Forbidden List (NOT Allowed for Batch 3)

The following state variables, methods, and modules must **NOT** be modified or moved in Batch 3:

- **Core state fields:** `bankroll_state`, `_bankroll_rank_lock`, `_balance_source`, `_balance_wallet_address`, `_wallet_reference_balance`, `_wallet_reference_source`, `_wallet_reference_error`, `_real_token_ids`, `_market_token_meta`, `_placed_epochs`, `_market_entry_counts`, `_last_reconciliation`.
- **Order/Risk/Sizer/Execution/Reconciliation state:** Any pricing, signals, size calculations, risk boundaries, or fill parameters.
- **Timing fields coupled to decision logic:**
- `_last_orderbook_age_ms` (used to evaluate orderbook staleness and skip cycles)
- `_orderbook_warmup_pending_counts` (used to determine if warmup period prevents trading)
- **Paper/Live Gate state:** Mode sentinel flags, preflight checks, account readiness verifiers.
- **Dashboard UI / Exports:** React dashboard code, external dashboard API contracts, or files under `dashboard/` or `web-dashboard/`.

---

## 4. Recommended Batch 3 Scope

### Selection: Option C (Extract display + observability helper with proxy methods)

We recommend **Option C** as the cleanest, safest, and most cohesive path for Batch 3. This option:
- Groups all non-critical, display-only, and logging/telemetry telemetry containers into a dedicated helper (e.g., `polymarket/orchestration/trader_observability.py`).
- Leaves core decision metrics (`_last_orderbook_age_ms` and `_orderbook_warmup_pending_counts`) completely insulated within `polymarket/trader.py`.
- Integrates cleanly with `PolymarketTrader` using delegator/proxy methods for `get_recent_display_trades()` and `dashboard_observability_health_state()`, keeping `main.py` and downstream dashboard systems untouched.

---

## 5. Risks & Mitigation Plan

1. **Risk: Breaking Downstream Dashboard Integration (Medium)**
   - *Risk:* Downstream state builders or dashboard files fail because they expect to find properties directly on `PolymarketTrader`.
   - *Mitigation:* Retain one-line delegation wrappers/properties on `PolymarketTrader` that query the extracted helper. Do not modify public method signatures.

2. **Risk: Performance Overhead of Proxy Calls (Low)**
   - *Risk:* Delegating calls during the cycle loop introduces latency.
   - *Mitigation:* The cycle loop only writes to these fields at execution milestones or when emitting events (fail-soft paths). Monotonic timestamps are kept lightweight.

3. **Risk: Concurrency/Threading Issues (Low)**
   - *Risk:* Concurrent updates to logging deques or state dicts when thread-safety boundaries change.
   - *Mitigation:* The Python GIL ensures base dictionary/deque mutations are atomic; access will occur within the same lifecycle cycle thread.

---

## 6. Final Verdict

```
READY_FOR_BATCH_3_DESIGN
```
