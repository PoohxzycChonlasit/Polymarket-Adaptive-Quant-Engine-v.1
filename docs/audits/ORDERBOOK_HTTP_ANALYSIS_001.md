# ORDERBOOK_HTTP_ANALYSIS_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

This document details the HTTP response status code distribution for all orderbook requests in the Polymarket Crypto 5M Quant Engine across recent sessions.

---

## 1. HTTP Status Code Distribution

The table below breaks down the HTTP status codes returned by the Polymarket CLOB API. 

*Note: The CLOB REST client throws `PolyApiException` for non-200 responses, which are caught and logged under `clob_status_code` in the decision log.*

### Session 1: June 19, 2026 (Total Requests Evaluated = 3,696)
| HTTP Status | Count | Percentage | Classification | Cause / Description |
| :--- | :---: | :---: | :--- | :--- |
| **200 OK** | 3,695 | 99.97% | Success (or Empty payload) | Valid orderbook returned or empty `{"bids": [], "asks": []}` |
| **404 Not Found** | 1 | 0.03% | Token Error | Token ID not registered on CLOB yet |
| **400 Bad Request** | 0 | 0.00% | Client Error | None |
| **401 Unauthorized**| 0 | 0.00% | Authentication Error | None |
| **403 Forbidden** | 0 | 0.00% | Authentication Error | None |
| **408 Timeout** | 0 | 0.00% | Timeout Error | None |
| **429 Rate Limit** | 0 | 0.00% | Throttling | None (handled by client's preloader backoffs) |
| **500 Internal Error**| 0 | 0.00% | Server Error | None |
| **502 Bad Gateway** | 0 | 0.00% | CDN Error | None |
| **503 Service Unavail**| 0 | 0.00% | Server Error | None |
| **504 Gateway Timeout**| 0 | 0.00% | CDN Timeout | None |

---

### Session 2: June 20, 2026 (Total Requests Evaluated = 3,177)
| HTTP Status | Count | Percentage | Classification | Cause / Description |
| :--- | :---: | :---: | :--- | :--- |
| **200 OK** | 3,136 | 98.71% | Success (or Empty payload) | Valid orderbook returned or empty `{"bids": [], "asks": []}` |
| **404 Not Found** | 41 | 1.29% | Token Error | Token ID not registered on CLOB yet (next-epoch preloader check) |
| **400 Bad Request** | 0 | 0.00% | Client Error | None |
| **401/403 Auth** | 0 | 0.00% | Authentication Error | None |
| **429 Rate Limit** | 0 | 0.00% | Throttling | None |
| **500/502/504 Server**| 0 | 0.00% | Server Error | None |

---

## 2. HTTP Exception Mapping Table

When non-200 statuses or empty responses occur, the client translates them into the following exceptions:

| Exception Type | Trigger Condition | Error Category | Action Taken |
| :--- | :--- | :--- | :--- |
| **`RuntimeError`** | Bids or Asks list empty in JSON payload | `clob_empty_response` | Triggers recovery retries; raises if all fail |
| **`PolyApiException`** | HTTP Status >= 400 (e.g. 404, 429) | `clob_http_error` | Raises immediately; opens circuit breaker |
| **`ClobOrderbookCooldown`**| Fetch attempted while circuit breaker open | `clob_empty_response` | Discards candidate instantly for that cycle |

---

## 3. Safety Statement
* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
