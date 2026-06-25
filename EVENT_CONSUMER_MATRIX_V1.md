# Event Consumer Matrix V1

This document maps every official event type in the **Runtime Event Taxonomy V1** to its target downstream consumers.

---

## 1. Consumer Matrix Definitions

- **Dashboard**: Consumes the event in real-time to update the operator UI components.
- **Replay**: Consumes the event during historical playback to reconstruct state cycles.
- **Analytics**: Consumes the event offline for quant metrics, performance auditing, and statistics.

---

## 2. Matrix Table

| Event Type | Dashboard | Replay | Analytics |
| :--- | :---: | :---: | :---: |
| `runtime_started_v1` | **YES** | **YES** | **YES** |
| `runtime_shutdown_v1` | **YES** | **YES** | **YES** |
| `runtime_heartbeat_v1` | **YES** | NO | NO |
| `runtime_warning_v1` | **YES** | **YES** | **YES** |
| `runtime_error_v1` | **YES** | **YES** | **YES** |
| `market_snapshot_v1` | NO | NO | **YES** |
| `orderbook_state_changed_v1` | **YES** | NO | **YES** |
| `candidate_generated_v1` | **YES** | **YES** | **YES** |
| `candidate_ranked_v1` | **YES** | **YES** | **YES** |
| `candidate_rejected_v1` | **YES** | **YES** | **YES** |
| `candidate_pipeline_stage_v1` | NO | NO | **YES** |
| `go_no_go_decision_v1` | **YES** | **YES** | **YES** |
| `decision_veto_v1` | **YES** | **YES** | **YES** |
| `risk_mode_changed_v1` | **YES** | **YES** | **YES** |
| `risk_limit_warning_v1` | **YES** | **YES** | **YES** |
| `bankroll_changed_v1` | **YES** | **YES** | **YES** |
| `bankroll_tier_changed_v1` | **YES** | **YES** | **YES** |
| `sizing_evaluated_v1` | **YES** | **YES** | **YES** |
| `sizing_rejected_v1` | **YES** | **YES** | **YES** |
| `sizing_approved_v1` | **YES** | **YES** | **YES** |
| `order_intent_created_v1` | **YES** | **YES** | **YES** |
| `order_intent_rejected_v1` | **YES** | **YES** | **YES** |
| `paper_order_submitted_v1` | **YES** | **YES** | **YES** |
| `paper_fill_v1` | **YES** | **YES** | **YES** |
| `paper_order_rejected_v1` | **YES** | **YES** | **YES** |
| `exit_signal_v1` | **YES** | **YES** | **YES** |
| `exit_order_submitted_v1` | **YES** | **YES** | **YES** |
| `exit_fill_v1` | **YES** | **YES** | **YES** |
| `exit_failed_v1` | **YES** | **YES** | **YES** |
| `position_opened_v1` | **YES** | **YES** | **YES** |
| `position_closed_v1` | **YES** | **YES** | **YES** |
| `position_reconciled_v1` | **YES** | **YES** | **YES** |
| `inventory_changed_v1` | **YES** | **YES** | **YES** |
| `analytics_loaded_v1` | **YES** | NO | NO |
| `analytics_stale_v1` | **YES** | **YES** | **YES** |
| `ghost_position_detected_v1` | **YES** | **YES** | **YES** |
| `ghost_position_sentinel_summary_v1`| **YES** | **YES** | **YES** |
| `runtime_snapshot_v1` | **YES** | NO | NO |
