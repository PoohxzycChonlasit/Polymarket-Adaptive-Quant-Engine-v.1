# ARCHITECTURE.md

# High-Level Architecture

WebSocket Feed
→ Local Cache
→ Market State Engine
→ Signal / EV Engine
→ Risk Engine
→ Execution Engine
→ Position Manager
→ Logging / Replay / Diagnostics
REST APIs are fallback only.

---

# Runtime Loops

Market Discovery Loop:

- every 15s
- discover active markets
- refresh market metadata
  Decision Loop:
- every 1s
- evaluate EV
- evaluate spread/liquidity
- evaluate phase
- evaluate risk
- generate decisions
  Exit Loop:
- every 1s
- manage open positions
- TP/SL logic
- emergency exits
  Snapshot Loop:
- every 5s
- lightweight market snapshots only

---

# Market Phases

OPENING_0_60

- observe
- tiny early snipe only
  MAIN_60_180
- normal entries allowed
  LATE_180_240
- reduced-size confirmation only
  EXIT_240_270
- no new entries
- exit management only
  RESOLVE_270_300
- emergency management only

---

# Core Principles

The system prioritizes:

1. execution safety
2. data quality
3. replayability
4. observability
5. controlled execution
   before:

- scaling
- optimization
- aggressive entries

---

# Logging Philosophy

Decision logs:

- every enter/skip/exit/shadow event
  Snapshots:
- sampled every 5s
  Full orderbooks:
- only before entry
- after entry
- before exit
- anomaly/failure events
  Compressed logs only.

---

# Orderbook Policy

Primary:

- websocket cache
  Fallback:
- REST orderbook refresh
  Never:
- REST poll every second for every market

---

# Paper Mode

Paper mode:

- fully simulated
- uses virtual balance
- may initialize from live wallet balance once
- never submits live orders

---

# Risk Principles

Always preserve:

- bankroll floors
- max position limits
- entry cutoffs
- stale data protections
- execution validation
