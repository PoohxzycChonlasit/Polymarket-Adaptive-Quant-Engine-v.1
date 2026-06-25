# Event Schema Standard V1

This document defines the standardized event schema structure for all event types in the **Runtime Event Stream V1**.

---

## Base Event envelope

Every single event emitted by the runtime MUST conform to the following JSON structure:

```json
{
  "event_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "event_type": "event_type_name",
  "event_version": "1.0.0",
  "runtime_session_id": "20260625T052627Z_48728_55bb248a",
  "sequence_number": 105,
  "timestamp": "2026-06-25T10:47:57.123456Z",
  "payload": {}
}
```

### Base Envelope Field Definitions

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `event_id` | String (UUIDv4) | Universally unique identifier for de-duplication. |
| `event_type` | String | String identifier matching the logical event name (e.g. `heartbeat`, `entry_submitted`). |
| `event_version` | String (SemVer) | The version of the event payload schema (e.g., `"1.0.0"`). |
| `runtime_session_id` | String | Unique string representing the active runtime process session startup timestamp and PID. |
| `sequence_number` | Integer | Monotonically increasing, 1-indexed count of events emitted by this session. |
| `timestamp` | String (ISO-8601) | ISO-8601 UTC timestamp format: `YYYY-MM-DDTHH:MM:SS.ffffffZ`. |
| `payload` | Object | Event-specific data dictionary. |

---

## Specific Event Payloads

### 1. `candidate_found` (Scanner)
Emitted when a candidate is identified by the market scanner as matching basic admission parameters.
```json
{
  "market_id": "pm-5m-btc",
  "question": "Will BTC close above 68250.00 at 17:50?",
  "volume": 12500.50,
  "liquidity": 48200.00,
  "current_yes_price": 0.52,
  "current_no_price": 0.49
}
```

### 2. `candidate_rejected` (Scanner / Opportunity Gate)
Emitted when a candidate fails a screening or admission gate.
```json
{
  "market_id": "pm-5m-btc",
  "rejection_reason": "stale_orderbook",
  "blocking_gate": "orderbook_freshness",
  "diagnostics": {
    "last_update_age_seconds": 4.25,
    "max_allowed_age_seconds": 3.0
  }
}
```

### 3. `entry_submitted` (Execution)
Emitted when a validated trade reaches the execution sizer and an entry limit order is submitted.
```json
{
  "market_id": "pm-5m-btc",
  "side": "BUY",
  "outcome": "YES",
  "price": 0.53,
  "size_shares": 100.0,
  "notional_size_usd": 53.00,
  "order_intent": "ENTRY",
  "order_id": "order-001"
}
```

### 4. `entry_filled` (Execution)
Emitted when an entry limit order is filled.
```json
{
  "market_id": "pm-5m-btc",
  "order_id": "order-001",
  "filled_shares": 100.0,
  "avg_fill_price": 0.53,
  "remaining_shares": 0.0,
  "is_virtual": true
}
```

### 5. `risk_state_changed` (Risk Engine)
Emitted when the risk tier, drawdown state, or active risk mode transitions.
```json
{
  "previous_mode": "NORMAL",
  "new_mode": "DEFENSIVE",
  "trigger_reason": "loss_cluster_detected",
  "diagnostics": {
    "realized_drawdown_pct": 0.045,
    "consecutive_losses": 3
  }
}
```
