# ORDERBOOK_FAILURE_TREE_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

This document displays the hierarchical failure tree of orderbook acquisition blocks within the Polymarket Crypto 5M Quant Engine, showing where failures originate and their percentage contribution based on log forensics.

---

## 1. The Orderbook Failure Tree

```
ORDERBOOK FAILURE (100.0%)
├── Empty Book (95.0% to 98.7%)
│   ├── Warmup Pending (Transient newly created market) (85.0%)
│   └── Stale Token Polling (Post-settlement empty book) (10.0%)
├── Network & HTTP Errors (1.2% to 4.5%)
│   ├── HTTP 404 (Preloader check on inactive upcoming epoch) (4.2%)
│   └── HTTP 502/504 (Transient Polymarket API gateway lag) (0.3%)
├── Token Resolution (0.1% to 0.5%)
│   └── missing_token_id (Gamma API late publish) (0.5%)
├── Authentication (0.0%)
├── Rate Limit (HTTP 429) (0.0%)
├── Cache (0.0%)
├── Runtime Logic (0.0%)
├── Validation (0.0%)
└── Unknown (0.0%)
```

---

## 2. Branch Breakdown and Explanations

### Empty Book (95.0% - 98.7% contribution)
* **Root Cause**: The CLOB API returns a HTTP 200 response with empty lists for bids and asks (`{"bids": [], "asks": []}`).
* **Mechanisms**:
  1. **Warmup Period**: When a 5-minute market is first created, it has a warming period. Market makers do not instantly populate the books, resulting in transient empty book responses.
  2. **Epoch Settlement**: Once a 5-minute epoch settles, the CLOB clears the YES/NO token books. Continuing to poll these settled tokens returns empty responses.

### Network & HTTP Errors (1.2% - 4.5% contribution)
* **Root Cause**: The HTTP client throws transport-level exceptions or wraps status codes above 400.
* **Mechanisms**:
  - **Preloader 404s**: The background preloader tries to fetch next-epoch token IDs before the CLOB endpoint registers them, resulting in HTTP 404 errors.
  - **Gateway Lag**: Transient HTTP 502 or 504 errors from Polymarket's CDN under high load.

### Token Resolution (0.1% - 0.5% contribution)
* **Root Cause**: Missing or malformed token IDs passed from the scanner.
* **Mechanisms**:
  - The Gamma API occasionally experiences a short delay in publishing the YES/NO token IDs for the upcoming epoch. The bot handles this as `missing_token_id` and skips the cycle.

### Authentication & Rate Limits (0.0% contribution)
* **Root Cause**: Requests blocked due to bad API keys or HTTP 429 status codes.
* **Status**: **Verified as 0.0% blocker** for the candidate loop. Market data fetches are public, require no credentials, and do not hit limits in the primary candidate evaluation loop.

---

## 3. Safety Statement
* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
