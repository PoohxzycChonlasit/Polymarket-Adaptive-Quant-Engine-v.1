# Event-to-Dashboard State Map V1

This document specifies how each event type from the **Runtime Event Taxonomy V1** updates the client-side state schema of the real-time Dashboard.

---

## 1. Dashboard State Schema

The dashboard maintains an in-memory client state structured as follows:

```json
{
  "runtime": {
    "alive": false,
    "state": "IDLE",
    "uptime": 0.0,
    "cpu": 0.0,
    "memory": 0.0,
    "queue_depth": 0
  },
  "bankroll": {
    "cash": 0.0,
    "equity": 0.0,
    "tier": "UNKNOWN",
    "mode": "NORMAL",
    "drawdown": 0.0
  },
  "positions": {
    "open": [],
    "closed": []
  },
  "candidates": {
    "active": [],
    "reject_distribution": {}
  },
  "alerts": []
}
```

---

## 2. Event State Mappings

| Event Type | Target State Path | Update Action |
| :--- | :--- | :--- |
| `runtime_started_v1` | `runtime.alive`<br>`runtime.state` | Set to `true`<br>Set to `"STARTING"` |
| `runtime_shutdown_v1` | `runtime.alive`<br>`runtime.state` | Set to `false`<br>Set to `"SHUTDOWN"` |
| `runtime_heartbeat_v1` | `runtime.alive`<br>`runtime.uptime`<br>`runtime.cpu`<br>`runtime.memory`<br>`runtime.queue_depth`<br>`runtime.state` | Set to `payload.runtime_alive`<br>Set to `payload.uptime_seconds`<br>Set to `payload.cpu_percent`<br>Set to `payload.memory_mb`<br>Set to `payload.queue_depth`<br>Set to `payload.runtime_state` |
| `bankroll_changed_v1` | `bankroll.cash`<br>`bankroll.equity`<br>`bankroll.drawdown` | Set to `payload.cash`<br>Set to `payload.equity`<br>Set to `payload.drawdown_pct` |
| `bankroll_tier_changed_v1` | `bankroll.tier` | Set to `payload.new_tier` |
| `risk_mode_changed_v1` | `bankroll.mode` | Set to `payload.new_mode` |
| `position_opened_v1` | `positions.open` | Append new position dictionary: `{"position_id": payload.position_id, ...}` |
| `position_closed_v1` | `positions.open`<br>`positions.closed` | Remove position matching `position_id` from `positions.open` and append to `positions.closed`. |
| `candidate_generated_v1` | `candidates.active` | Append/Overwrite candidate item in `candidates.active` list. |
| `candidate_rejected_v1` | `candidates.reject_distribution` | Increment rejection category counter: `reject_distribution[payload.blocking_gate] += 1` |
| `runtime_warning_v1` | `alerts` | Prepend error alert dictionary with TTL (Time To Live). |
| `runtime_snapshot_v1` | *Entire State Schema* | Full replace of all fields (initial bootstrap load). |
