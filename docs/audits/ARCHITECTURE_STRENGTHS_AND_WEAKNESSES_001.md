# Architectural Strengths & Weaknesses 001

This document provides a verified audit of the design strengths and weaknesses of the Polymarket Adaptive Quant Engine.

---

## 1. Architectural Weaknesses

### W1: God Object (`polymarket/trader.py`)
- **Repository Evidence:** `trader.py` is 13,205 lines and imports over 30 sub-modules, coordinating execution, sizing, risk validation, data preloads, TP/SL exit loops, and console UI display formatting.
- **Confidence:** 100% (Direct inspection).
- **Remaining Uncertainty:** None.

### W2: Mixed Responsibilities (Application / Presentation)
- **Repository Evidence:** `PolymarketTrader` contains logic for formatting Rich console payloads (`_display_payload_with_candidate_trace_identity` and `_observability_health_from_payload`), mixing user-interface requirements with execution logic.
- **Confidence:** 95% (Verification of Rich display functions in `trader.py`).
- **Remaining Uncertainty:** The formatting methods are display-only but reside inside the execution block.

### W3: Import-Time Side Effects & Configuration Leakage
- **Repository Evidence:** Importing `config/settings.py` automatically initializes `get_settings()`, which attempts to read `.env` immediately. If `.env` is invalid or missing, it fails at import-time.
- **Confidence:** 90%.
- **Remaining Uncertainty:** Pydantic models validate environment bounds, but immediate loading at runtime initialization can make mock testing of settings parameters more complex.

---

## 2. Architectural Strengths (Do NOT Change)

### S1: Decoupled Client and API Interface
- **Description:** `PolymarketClient` acts as an absolute layer separating Polymarket CLOB endpoints from the engine logic. It performs token mapping and CLOB HTTP requests.
- **Why Protect:** Keeps the core bot independent of API endpoint changes. If Polymarket updates its API schemas, only `client.py` needs adjustment.

### S2: Bounded RiskManager Safety Gate
- **Description:** `RiskManager.can_trade()` operates as a centralized gate checking drawdown percentages and cluster streaks prior to any trade evaluation.
- **Why Protect:** Guarantees that even if strategy indicators or EV calculations produce aberrant entry recommendations, the risk manager will block execution at the door.

### S3: File-Backed Telemetry Decoupling
- **Description:** Events are written directly to JSONL files via `QuantEventLogger`. No database connections or network sockets reside inside the execution thread.
- **Why Protect:** Prevents external UI or network latency spikes from blocking execution speed, maintaining safety guarantees for fast prediction markets.
