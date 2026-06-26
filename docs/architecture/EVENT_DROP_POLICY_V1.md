# Event Drop Policy V1

This document defines the queue congestion drop policy and prioritization rules for the **Runtime Event Stream V1**.

---

## 1. Priority-Based Drop Rules

When the thread-safe communication queue (`queue.Queue`) reaches its capacity limits, the engine must drop events to prevent memory bloat, while preserving system state and audit integrity.

| Priority | Drop Rule | Eviction Strategy | Associated Event Types |
| :--- | :--- | :--- | :--- |
| **CRITICAL** | **NEVER DROPPED** | Writer blocks the caller thread or evicts lower priority events from the queue until space is available. | `runtime_started_v1`, `runtime_shutdown_v1`, `runtime_heartbeat_v1`, `runtime_error_v1`, `bankroll_tier_changed_v1`, `paper_fill_v1`, `exit_fill_v1`, `exit_failed_v1`, `position_opened_v1`, `position_closed_v1`, `ghost_position_detected_v1`, `ghost_position_sentinel_summary_v1` |
| **HIGH** | **DROPPED ONLY IF DEGRADED** | Dropped only if the queue contains no lower priority (`NORMAL` or `LOW`) events to evict, AND the system is in a critical resource boundary. | `runtime_warning_v1`, `go_no_go_decision_v1`, `decision_veto_v1`, `risk_mode_changed_v1`, `risk_limit_warning_v1`, `bankroll_changed_v1`, `sizing_rejected_v1`, `sizing_approved_v1`, `order_intent_created_v1`, `order_intent_rejected_v1`, `paper_order_submitted_v1`, `paper_order_rejected_v1`, `exit_signal_v1`, `exit_order_submitted_v1`, `position_reconciled_v1`, `inventory_changed_v1`, `analytics_stale_v1`, `runtime_snapshot_v1` |
| **NORMAL** | **BUFFERED / EVICATABLE** | Queued ordinarily. Evicted if the queue fills up and space is required for a `CRITICAL` or `HIGH` event. | `candidate_generated_v1`, `candidate_ranked_v1`, `sizing_evaluated_v1`, `analytics_loaded_v1` |
| **LOW** | **DROPPABLE ON CONGESTION** | Dropped immediately on write if queue space is below 15% remaining capacity, or evicted first when capacity is reached. | `market_snapshot_v1`, `orderbook_state_changed_v1`, `candidate_rejected_v1`, `candidate_pipeline_stage_v1` |

---

## 2. Drop Constraints

- **State-Changing Invariance**: Any event that changes the state of active holdings, ledger cash balances, or tier statuses (`state_changing: true`) MUST NOT be dropped, regardless of priority category.
- **Eviction Direction**: Eviction scans the queue from oldest to newest, removing the oldest matching `LOW` priority events first.

---

## 3. Queue Overflow Event
When any event is dropped or evicted, the logger emits:
- **Event Name**: `event_stream_queue_overflow_v1`
- **Category**: Errors / Warnings
- **Priority**: HIGH
- **Payload Fields**: `{"dropped_event_type": str, "dropped_event_priority": str, "current_queue_depth": int}`
