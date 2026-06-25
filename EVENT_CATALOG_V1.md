# Event Catalog V1

This document catalog lists every official event type in the **Runtime Event Taxonomy V1**.

---

## 1. Runtime Lifecycle & Health

### `runtime_started_v1`
- **category:** Runtime Lifecycle
- **priority:** CRITICAL
- **frequency:** rare
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["runtime_session_id", "timestamp_utc", "environment", "engine_version", "git_commit"]`
- **payload_optional_fields:** `["command_line_args", "config_digest"]`
- **notes:** Emitted once at engine bootstrap.

### `runtime_shutdown_v1`
- **category:** Runtime Lifecycle
- **priority:** CRITICAL
- **frequency:** rare
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["runtime_session_id", "uptime_seconds", "shutdown_reason", "final_sequence_number"]`
- **payload_optional_fields:** `["clean_exit"]`
- **notes:** Emitted during clean teardown or SIGINT/SIGTERM handlers.

### `runtime_heartbeat_v1`
- **category:** Runtime Lifecycle
- **priority:** CRITICAL
- **frequency:** high
- **state_changing:** false
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** false
- **analytics_consumer:** false
- **payload_required_fields:** `["runtime_alive", "uptime_seconds", "paper_balance", "active_positions", "current_bankroll_tier", "risk_mode", "candidate_count", "events_per_second", "memory_mb", "cpu_percent", "runtime_state"]`
- **payload_optional_fields:** `["loop_latency_ms", "decision_latency_ms", "queue_depth"]`
- **notes:** Emitted every 5 seconds.

### `runtime_warning_v1`
- **category:** Errors / Warnings
- **priority:** HIGH
- **frequency:** low
- **state_changing:** false
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["warning_code", "message", "source_module"]`
- **payload_optional_fields:** `["traceback"]`
- **notes:** Emitted on non-fatal issues (e.g. database locks, slow responses).

### `runtime_error_v1`
- **category:** Errors / Warnings
- **priority:** CRITICAL
- **frequency:** rare
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["error_code", "message", "source_module", "fatal"]`
- **payload_optional_fields:** `["traceback"]`
- **notes:** Emitted on critical failures (e.g. key decryption errors).

---

## 2. Market Data

### `market_snapshot_v1`
- **category:** Market Data
- **priority:** LOW
- **frequency:** high
- **state_changing:** false
- **droppable:** true
- **dashboard_consumer:** false
- **replay_consumer:** false
- **analytics_consumer:** true
- **payload_required_fields:** `["market_id", "symbol", "ref_price", "oracle_price", "timestamp_utc"]`
- **payload_optional_fields:** `[]`
- **notes:** Raw price feed ticks. Droppable under log pressure.

### `orderbook_state_changed_v1`
- **category:** Market Data
- **priority:** LOW
- **frequency:** high
- **state_changing:** false
- **droppable:** true
- **dashboard_consumer:** true
- **replay_consumer:** false
- **analytics_consumer:** true
- **payload_required_fields:** `["market_id", "best_bid", "best_ask", "spread", "liquidity_depth_usd"]`
- **payload_optional_fields:** `["bids_depth_matrix", "asks_depth_matrix"]`
- **notes:** Level-2 bid/ask changes. Dropped first under storage limit pressure.

---

## 3. Candidate Pipeline

### `candidate_generated_v1`
- **category:** Candidate Pipeline
- **priority:** NORMAL
- **frequency:** medium
- **state_changing:** false
- **droppable:** true
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["market_id", "indicator_score", "timestamp_utc"]`
- **payload_optional_fields:** `["technical_indicators"]`
- **notes:** Emitted when a market passes basic universe filters.

### `candidate_ranked_v1`
- **category:** Candidate Pipeline
- **priority:** NORMAL
- **frequency:** medium
- **state_changing:** false
- **droppable:** true
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["ranked_markets", "top_candidates"]`
- **payload_optional_fields:** `[]`
- **notes:** Final sorted candidates list per cycle.

### `candidate_rejected_v1`
- **category:** Candidate Pipeline
- **priority:** LOW
- **frequency:** high
- **state_changing:** false
- **droppable:** true
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["market_id", "rejection_reason", "blocking_gate"]`
- **payload_optional_fields:** `["diagnostics"]`
- **notes:** Catalog of why candidates failed.

### `candidate_pipeline_stage_v1`
- **category:** Candidate Pipeline
- **priority:** LOW
- **frequency:** high
- **state_changing:** false
- **droppable:** true
- **dashboard_consumer:** false
- **replay_consumer:** false
- **analytics_consumer:** true
- **payload_required_fields:** `["market_id", "stage", "status"]`
- **payload_optional_fields:** `[]`
- **notes:** Fine-grained execution trace events.

---

## 4. Decision & Risk Engines

### `go_no_go_decision_v1`
- **category:** Decision Engine
- **priority:** HIGH
- **frequency:** medium
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["market_id", "action", "confidence", "direction"]`
- **payload_optional_fields:** `["technical_summary"]`
- **notes:** Core trade trigger event.

### `decision_veto_v1`
- **category:** Decision Engine
- **priority:** HIGH
- **frequency:** low
- **state_changing:** false
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["market_id", "veto_gate", "reason"]`
- **payload_optional_fields:** `["original_confidence"]`
- **notes:** Emitted if risk or sizer vetos a trade entry.

### `risk_mode_changed_v1`
- **category:** Risk Engine
- **priority:** CRITICAL
- **frequency:** rare
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["previous_mode", "new_mode", "trigger_reason"]`
- **payload_optional_fields:** `["diagnostics"]`
- **notes:** Changes active sizing multipliers (e.g. entering lockdown).

### `risk_limit_warning_v1`
- **category:** Risk Engine
- **priority:** HIGH
- **frequency:** low
- **state_changing:** false
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["metric_name", "current_value", "threshold_value"]`
- **payload_optional_fields:** `[]`
- **notes:** E.g., approaching daily drawdown limits.

---

## 5. Bankroll Engine

### `bankroll_changed_v1`
- **category:** Bankroll Engine
- **priority:** HIGH
- **frequency:** medium
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["cash", "equity", "exposure", "drawdown_pct"]`
- **payload_optional_fields:** `["realized_pnl"]`
- **notes:** Emitted on cycle update or trade fill.

### `bankroll_tier_changed_v1`
- **category:** Bankroll Engine
- **priority:** CRITICAL
- **frequency:** rare
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["previous_tier", "new_tier", "reason"]`
- **payload_optional_fields:** `[]`
- **notes:** Emitted on hysteresis rank shift.

---

## 6. Position Sizing

### `sizing_evaluated_v1`
- **category:** Position Sizing
- **priority:** NORMAL
- **frequency:** medium
- **state_changing:** false
- **droppable:** true
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["market_id", "proposed_size_shares", "sizing_model"]`
- **payload_optional_fields:** `["raw_kelly_fraction"]`
- **notes:** Sizer calculations.

### `sizing_rejected_v1`
- **category:** Position Sizing
- **priority:** HIGH
- **frequency:** low
- **state_changing:** false
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["market_id", "rejection_reason", "sizing_floor"]`
- **payload_optional_fields:** `["proposed_size_usd"]`
- **notes:** Size under minimum bounds.

### `sizing_approved_v1`
- **category:** Position Sizing
- **priority:** HIGH
- **frequency:** medium
- **state_changing:** false
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["market_id", "approved_size_shares", "approved_notional_usd"]`
- **payload_optional_fields:** `[]`
- **notes:** Sizer approval confirmation.

---

## 7. Order Intent

### `order_intent_created_v1`
- **category:** Order Intent
- **priority:** HIGH
- **frequency:** medium
- **state_changing:** false
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["intent_id", "market_id", "order_type", "side", "shares", "price"]`
- **payload_optional_fields:** `[]`
- **notes:** Order details before execution pre-flight checks.

### `order_intent_rejected_v1`
- **category:** Order Intent
- **priority:** HIGH
- **frequency:** low
- **state_changing:** false
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["intent_id", "rejection_reason"]`
- **payload_optional_fields:** `[]`
- **notes:** E.g., selling without inventory.

---

## 8. Paper Execution

### `paper_order_submitted_v1`
- **category:** Paper Execution
- **priority:** HIGH
- **frequency:** medium
- **state_changing:** false
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["order_id", "market_id", "side", "shares", "price"]`
- **payload_optional_fields:** `[]`
- **notes:** Simulated order sent to engine's local matcher.

### `paper_fill_v1`
- **category:** Paper Execution
- **priority:** CRITICAL
- **frequency:** medium
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["order_id", "market_id", "filled_shares", "fill_price", "is_full_fill"]`
- **payload_optional_fields:** `[]`
- **notes:** Virtual limit order fill.

### `paper_order_rejected_v1`
- **category:** Paper Execution
- **priority:** HIGH
- **frequency:** low
- **state_changing:** false
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["order_id", "reason"]`
- **payload_optional_fields:** `[]`
- **notes:** Simulated matcher cancellation/rejection.

---

## 9. Exit Execution

### `exit_signal_v1`
- **category:** Exit Execution
- **priority:** HIGH
- **frequency:** medium
- **state_changing:** false
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["position_id", "trigger_type", "price"]`
- **payload_optional_fields:** `["description"]`
- **notes:** Trigger type is one of: `TAKE_PROFIT`, `STOP_LOSS`, `FORCED_EXIT`, `PANIC_EXIT`, `RESIDUAL_SWEEP`.

### `exit_order_submitted_v1`
- **category:** Exit Execution
- **priority:** HIGH
- **frequency:** medium
- **state_changing:** false
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["order_id", "position_id", "shares", "price"]`
- **payload_optional_fields:** `[]`
- **notes:** EXIT order limit submitted.

### `exit_fill_v1`
- **category:** Exit Execution
- **priority:** CRITICAL
- **frequency:** medium
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["order_id", "position_id", "filled_shares", "fill_price"]`
- **payload_optional_fields:** `[]`
- **notes:** Exit order matched.

### `exit_failed_v1`
- **category:** Exit Execution
- **priority:** CRITICAL
- **frequency:** low
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["order_id", "position_id", "failure_reason"]`
- **payload_optional_fields:** `[]`
- **notes:** Critical exit blockages.

---

## 10. Inventory & Reconciliation

### `position_opened_v1`
- **category:** Inventory / Reconciliation
- **priority:** CRITICAL
- **frequency:** medium
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["position_id", "market_id", "side", "entry_price", "size_shares"]`
- **payload_optional_fields:** `["lifecycle_phase", "runtime_session_id"]`
- **notes:** Emitted when local tracker registers a new open trade.

### `position_closed_v1`
- **category:** Inventory / Reconciliation
- **priority:** CRITICAL
- **frequency:** medium
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["position_id", "exit_price", "realized_pnl"]`
- **payload_optional_fields:** `[]`
- **notes:** Emitted when local tracker closes a position.

### `position_reconciled_v1`
- **category:** Inventory / Reconciliation
- **priority:** HIGH
- **frequency:** medium
- **state_changing:** false
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["reconciliation_status", "mismatches_found"]`
- **payload_optional_fields:** `["clob_positions", "local_positions"]`
- **notes:** Reports audits matching local state with CLOB state.

### `inventory_changed_v1`
- **category:** Inventory / Reconciliation
- **priority:** HIGH
- **frequency:** medium
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["active_positions_count", "total_exposure_usd"]`
- **payload_optional_fields:** `[]`
- **notes:** Aggregated updates on active holdings.

---

## 11. Analytics & Sentinel

### `analytics_loaded_v1`
- **category:** Analytics Loader
- **priority:** NORMAL
- **frequency:** medium
- **state_changing:** false
- **droppable:** true
- **dashboard_consumer:** true
- **replay_consumer:** false
- **analytics_consumer:** false
- **payload_required_fields:** `["source_file", "records_count", "time_elapsed_ms"]`
- **payload_optional_fields:** `[]`
- **notes:** Loads model diagnostic variables.

### `analytics_stale_v1`
- **category:** Analytics Loader
- **priority:** HIGH
- **frequency:** low
- **state_changing:** false
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["data_source", "age_seconds", "threshold_seconds"]`
- **payload_optional_fields:** `[]`
- **notes:** Warns if offline model caches are stale.

### `ghost_position_detected_v1`
- **category:** Ghost Position Sentinel
- **priority:** CRITICAL
- **frequency:** rare
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["position_id", "runtime_session_id", "ghost_reason", "quarantined"]`
- **payload_optional_fields:** `["position_runtime_session_id"]`
- **notes:** Sentinel quarantine reports.

### `ghost_position_sentinel_summary_v1`
- **category:** Ghost Position Sentinel
- **priority:** CRITICAL
- **frequency:** rare
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** true
- **analytics_consumer:** true
- **payload_required_fields:** `["positions_scanned", "ghost_positions_found", "ghost_positions_quarantined", "valid_positions_remaining", "startup_safe"]`
- **payload_optional_fields:** `[]`
- **notes:** Sentinel startup metrics.

---

## 12. State Snapshot

### `runtime_snapshot_v1`
- **category:** Dashboard Snapshot
- **priority:** HIGH
- **frequency:** low
- **state_changing:** true
- **droppable:** false
- **dashboard_consumer:** true
- **replay_consumer:** false
- **analytics_consumer:** false
- **payload_required_fields:** `["timestamp_utc", "active_positions", "bankroll", "settings"]`
- **payload_optional_fields:** `[]`
- **notes:** Emitted on dashboard demand or connection to synchronize state.
