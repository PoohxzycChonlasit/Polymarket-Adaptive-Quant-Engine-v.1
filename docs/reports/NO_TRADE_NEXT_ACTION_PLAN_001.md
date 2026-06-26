# NO_TRADE_NEXT_ACTION_PLAN_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

Based on the forensic findings of `NO_TRADE_ROOT_CAUSE_AUDIT_001` and the statistical distribution in `NO_TRADE_REJECT_REASON_DISTRIBUTION_001`, this document outlines the next action items to restore normal paper/live trading functionality while keeping strict risk bounds intact.

---

## 1. Resolution Strategy: Option 1 (Safe EV Preservation)

We choose **Option 1**. We preserve the strict Kelly sizing guidelines, probability floors, and price boundary limits. The high skip rate at those gates is correct defensive behavior for a T0 bankroll ($20.13). 
Instead, we focus on unblocking the **Orderbook Readiness** stage, which currently discards 87%–92% of cycles due to public API rate limiting.

---

## 2. Phase 1 Actions: Orderbook Ingestion Hardening

### Action 1.1: Integrate API Key Authentication Headers
* **Target File**: [config/settings.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/config/settings.py), [polymarket/client.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/client.py)
* **Description**: Support credentials for Polymarket CLOB authentication in settings (API Key, Secret, Passphrase). Update the client's HTTP session builder to automatically sign and attach these authentication headers to all orderbook polling requests. Authenticated requests benefit from significantly higher rate limits.
* **Status**: Ready to design.

### Action 1.2: Implement Proxy Rotation for Public Fallbacks
* **Target File**: [config/settings.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/config/settings.py), [polymarket/client.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/client.py)
* **Description**: Add support for a list of proxy URIs in the config settings. Configure the HTTP client to cycle through proxies when hitting rate limits, preventing single-IP public rate-limit exhaustion.
* **Status**: Ready to design.

### Action 1.3: Decouple Ingestion via Async WebSocket Orderbook Cache
* **Target File**: [polymarket/client.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/client.py)
* **Description**: Refactor the orderbook retrieval mechanism from synchronous HTTP polling to a persistent WebSocket subscription (CLOB WebSocket feed). Maintain a local, thread-safe memory cache of the top-of-book bid/ask levels. This eliminates polling rate limits entirely and guarantees sub-millisecond local lookups.
* **Status**: Recommended for Phase 3.

---

## 3. Phase 2 Actions: Micro-Sizing Rescue Optimization

### Action 2.1: Permit Micro-Survival Rescue Under defensive states
* **Target File**: [polymarket/position_sizing.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py)
* **Description**: Modify the `_maybe_apply_micro_survival_plan` function to allow lot sizing rescue to occur even if secondary mild vetoes (such as soft probability warnings or wider spreads) are active, provided the win confidence is still above the absolute hard floor (e.g. 0.50) and risk budget is positive.
* **Status**: Design only.

---

## 4. Verification Plan

After the above changes are implemented in a future execution task, the following validation protocol must be performed:

### Automated Tests
1. **API Auth Verification**:
   ```bash
   python -m unittest tests/test_client_auth.py
   ```
2. **Orderbook Rate-Limit Mock Test**:
   ```bash
   python -m pytest tests/test_rate_limit_backoff.py
   ```

### Manual Verification
1. Run the bot in paper mode for 1 hour:
   ```bash
   python main.py --mode paper --interval 60
   ```
2. Verify in the console output and `runtime/bot_status.json` that:
   - Orderbook rate limit cooldowns drop to < 5% of cycles.
   - Candidate evaluations successfully reach the Probability Model and Expected Value stages on > 90% of cycles.
   - Successful mock order placements are logged when EV edge is discovered.

---

## 5. Safety Statement
* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Live behavior changed**: No
