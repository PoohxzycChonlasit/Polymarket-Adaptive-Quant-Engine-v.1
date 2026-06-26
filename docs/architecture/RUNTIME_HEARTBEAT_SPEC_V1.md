# Runtime Heartbeat Specification V1

This document specifies the schema, metrics, and operational requirements of the periodic heartbeat event emitted by the Polymarket Adaptive Quant Engine.

---

## Heartbeat Properties

- **Event Type:** `heartbeat`
- **Emission Interval:** Every **5 seconds** (controlled by the main loop timer)
- **Liveness Gate:** Must be emitted continuously by the active trader loop. If missing for more than 15 seconds, the dashboard will flag the bot as `"UNRESPONSIVE"`.

---

## Heartbeat Schema Layout

```json
{
  "event_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
  "event_type": "heartbeat",
  "event_version": "1.0.0",
  "runtime_session_id": "20260625T052627Z_48728_55bb248a",
  "sequence_number": 880,
  "timestamp": "2026-06-25T10:47:57.000000Z",
  "payload": {
    "runtime_alive": true,
    "uptime_seconds": 3600.0,
    "system_metrics": {
      "cpu_percent": 1.25,
      "memory_mb": 74.50,
      "events_per_second": 8.4
    },
    "portfolio": {
      "paper_trading": true,
      "current_cash": 20.099,
      "current_equity": 20.099,
      "current_exposure": 0.00,
      "realized_pnl": 0.099,
      "unrealized_pnl": 0.00,
      "drawdown_pct": 0.00,
      "bankroll_tier": "MICRO_SURVIVAL"
    },
    "risk": {
      "risk_mode": "NORMAL",
      "lockdown_active": false,
      "sizing_multiplier": 1.0
    },
    "active_positions": []
  }
}
```

---

## Metric Descriptions & Sources

### 1. `system_metrics`
- **`cpu_percent`**: Measured via `psutil.Process().cpu_percent()`. Used to monitor thread exhaustion or event loop blocks.
- **`memory_mb`**: Measured via `psutil.Process().memory_info().rss / (1024 * 1024)`. Detects memory leaks in the market feed cache.
- **`events_per_second`**: Moving average of event logger throughput.

### 2. `portfolio`
- **`current_cash` / `current_equity`**: Derived directly from the bot's `BankrollState` object.
- **`bankroll_tier`**: The active hysteresis rank (e.g. `MICRO_SURVIVAL`, `STANDARD`, `GROWTH`).

### 3. `risk`
- **`risk_mode`**: Current mode ladder stage (e.g. `NORMAL`, `DEFENSIVE`, `MICRO_RECOVERY`, `LOCKDOWN`).
- **`lockdown_active`**: True if any critical reconciliation failure or risk limit breach has locked entry orders.

### 4. `active_positions`
Contains a list of currently open positions, summarized in a compact footprint:
```json
[
  {
    "position_id": "8a3d2c12",
    "symbol": "pm-5m-btc",
    "side": "BUY",
    "entry_price": 0.52,
    "size": 10.0,
    "unrealized_pnl": 0.20
  }
]
```
