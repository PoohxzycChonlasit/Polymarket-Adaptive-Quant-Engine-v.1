# ORDERBOOK_RATE_LIMIT_ANALYSIS_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

This document provides a detailed rate-limiting and throttling analysis for the Polymarket CLOB orderbook API client inside the quant engine.

---

## 1. Rate Limit Parameters & Metrics

### Public Endpoint Limits
* **Endpoint**: `https://clob.polymarket.com/book?token_id=<token_id>`
* **Limit Type**: IP-based rate limiting.
* **Observed Limit**: 60 to 120 requests per minute per IP. 

### Current Request Rate
* **Primary Loop**: Evaluates 2 markets (BTC and ETH) with YES/NO tokens (4 tokens total).
* **Base Request Frequency**: At a default cycle interval of 5 seconds, the bot performs 4 fetches per cycle, resulting in **48 requests/minute** for the candidate loop.
* **Preloader Overhead**: At epoch boundaries, the preloader adds YES/NO fetches for next-epoch tokens, adding **4–8 requests/minute**.
* **Average Request Rate**: **52 requests/minute** (close to the public rate-limiting threshold).
* **Peak Request Rate**: Can burst up to **100+ requests/minute** during retry cascades or rapid startup cycle restarts.

---

## 2. Retry and Cooldown Policies

### Retry Policy
* **Configuration**:
  - `clob_orderbook_retry_count`: 1 (Maximum of 2 total attempts)
  - `clob_orderbook_retry_backoff_ms`: 150ms
* **Mechanism**: If a transient issue (`clob_empty_response`, HTTP 500, etc.) occurs, the client sleeps for 150ms and retries once. Subsequent retries use exponential backoff, capped at 1.0 second.

### Cooldown / Circuit Breaker Policy
* **Configuration**:
  - `clob_circuit_breaker_threshold`: 3 failures
  - `clob_circuit_breaker_window_seconds`: 60 seconds
  - `clob_market_error_cooldown_seconds`: 10 seconds
  - `clob_rate_limit_cooldown_seconds`: 30 seconds
* **Mechanism**: If a token ID experiences 3 failures within 60 seconds, the client opens its circuit breaker for 10 seconds (or 30 seconds if it was an HTTP 429). Any request to this token during the cooldown immediately raises `ClobOrderbookCooldown` without executing a network call.

---

## 3. Rate Limit Recovery Recommendation

To eliminate rate-limiting constraints entirely:
1. **Authenticated Headers**: Add CLOB API keys. Authenticated requests enjoy significantly higher rate limits (up to 1,000 requests/minute).
2. **WebSocket Ingestion**: Shift from REST HTTP polling to a persistent WebSocket feed, which is free of REST rate-limit bounds and updates in real-time.

---

## 4. Safety Statement
* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
