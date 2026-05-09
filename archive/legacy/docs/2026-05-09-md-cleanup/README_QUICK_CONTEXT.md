# README_QUICK_CONTEXT.md

## Project Overview

This project is a websocket-first, event-driven quant trading system for
Polymarket BTC/ETH 5-minute prediction markets.
The project focuses on:

- event-driven trading
- probability/EV-based execution
- microstructure-aware decisions
- risk-first architecture
- paper-safe development
- lightweight VPS-friendly runtime
- replayable diagnostics
  The project is NOT:
- indicator-only trading
- high-frequency REST polling
- uncontrolled scalping
- unrestricted live trading

---

# Runtime Philosophy

Priority order:

1. Data quality
2. Observability
3. Execution safety
4. Replayability
5. Controlled scaling
6. Strategy optimization later

---

# Runtime Target

Environment:

- Vultr VPS
- ~5GB disk
- 24/7 runtime
- websocket-first architecture
  Runtime goals:
- lightweight logging
- compressed logs
- event-driven snapshots
- minimal REST API usage
- stable decision loop

---

# Current Priorities

1. paper balance visibility
2. websocket-first orderbook cache
3. market phase system
4. no-entry diagnostics
5. shadow entry logging
6. lightweight VPS logging

---

# Current Known Issues

- orderbook_unavailable too high
- time_unsafe too high
- decision loop too slow
- missing timing instrumentation
- risk_plan_zero visibility incomplete
- REST polling still used too much

---

# Architecture Constraints

Must preserve:

- websocket-first
- REST fallback only
- paper-safe by default
- risk-first behavior
- execution validation
- stale-data protection
- lightweight logging
- VPS-friendly runtime

---

# Do Not Modify Without Explicit Approval

- bankroll floors
- live order protections
- order intent validation
- paper/live separation
- stale orderbook safeguards
- max position protections

---

# Logging Constraints

Do NOT:

- log full orderbooks every second
- store raw websocket streams indefinitely
- create unbounded runtime files
  Use:
- sampled snapshots
- compressed logs
- log rotation
- event-driven diagnostics

---

# Paper vs Live

Paper mode:

- never submits live orders
- never spends real funds
- may read live wallet balance ONCE at startup as reference only
  Live mode:
- requires explicit enablement
- requires readiness checks
- requires risk protections

---

# Token Discipline

Always:

- read markdown/docs first
- inspect only relevant files
- minimize repository scanning
- avoid unrelated modules
- avoid recursive analysis
  Never:
- scan entire repository unnecessarily
- inspect runtime logs unless debugging explicitly requires them
