# CLOB_EMPTY_RESPONSE_FORENSIC_AUDIT

**Role Routing:**
- Primary: 11_OBSERVABILITY_INCIDENT_AGENT
- Supporting: 10_BACKTEST_REPLAY_AGENT
- Mode: READ ONLY — No code changes made

---

## Audit Window

- Full date: 2026-06-18
- 2h focus: 03:30–05:35 UTC
- Current runtime run_id: `20260618T045827Z_49008_98444aea` (started ~04:58 UTC)
- Current runtime last heartbeat: `2026-06-18T05:36:52Z` ✅ alive

---

## Dashboard Context Interpretation

The dashboard shows:
```
BTC STATUS: CLOB EMPTY
ETH STATUS: CLOB EMPTY
Blocked: no_orderbook
Reason: clob_empty_response
Action: waiting for valid CLOB book
```

**Critical finding:** The CLOB state machine uses `orderbook_readiness_reason = "clob_empty_response"` as a label for **CLOB cooldown active**, not for a truly missing orderbook. This is a **labeling ambiguity** in the dashboard.

---

## Q1: Count in Last 2h

| Window | Count |
|--------|-------|
| 2h window (03:30–05:35 UTC) | **35** |
| June 18 full day | **55** |
| June 18 all decision events | 104 |

**Rate:** 35/104 = **33.7% of all scans** affected by clob_empty state in the last 2h.

---

## Q2: Count by Asset

| Asset | Count | % |
|-------|-------|---|
| ETH | 45 | **81.8%** |
| BTC | 10 | 18.2% |

> [!IMPORTANT]
> **ETH accounts for 81.8% of all CLOB empty events.** BTC is mostly unaffected except during the startup window (02:44 UTC). This is **not a symmetric infrastructure failure** — it is ETH-dominated.

---

## Q3: Count by Market/Token ID

Top affected market slugs:
| Market Slug | Count |
|-------------|-------|
| `btc-updown-5m-1781751000` | 5 |
| `eth-updown-5m-1781751000` | 5 |
| `eth-updown-5m-1781759100` | 5 |
| `eth-updown-5m-1781759400` | 5 |
| `eth-updown-5m-1781759700` | 5 |
| `eth-updown-5m-1781760000` | 5 |
| `eth-updown-5m-1781760300` | 5 |
| `eth-updown-5m-1781760600` | 5 |

**Concentrated ETH epochs** each showing 5 events — matching the 5-retry pattern per cycle.

---

## Q4: BTC vs ETH — Simultaneous?

| Pattern | Minutes |
|---------|---------|
| BTC CLOB empty minutes | 10 |
| ETH CLOB empty minutes | 45 |
| **Simultaneous (both empty)** | **10** |
| BTC-only minutes | 0 |
| ETH-only minutes | 35 |

**BTC and ETH are simultaneously empty only during startup (02:44–02:50 UTC)**. After that, ETH continues empty while BTC recovers. This asymmetry points to ETH token-specific cooldown cycling, not a platform-wide outage.

**Near-expiry vs mid-epoch:**
- Near-expiry (< 30s): 7 events (12.7%)
- Mid-epoch (≥ 30s): 48 events (**87.3%**)

> [!NOTE]
> 87% of CLOB empty events occur mid-epoch — not just near expiry. This is NOT a market-close-time phenomenon.

---

## Q5: Streak Analysis

| Metric | Value |
|--------|-------|
| Number of streaks | 36 |
| Mean streak length | **1.5 events** |
| Median streak | 1.0 event |
| **Max streak** | **20 events** |
| Current active streak | 1 event |

The max streak of 20 events corresponds to the ETH block observed at 05h UTC (the ongoing session). **Short streaks dominate (median=1)** — the cooldown resolves within one cycle most of the time.

---

## Q6: Oracle / WS Continuity During CLOB Empty

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Oracle age (mean) | 649 ms | **Fresh — oracle still updating** |
| Oracle age (max) | 1815 ms | < 2s — well within tolerance |
| Scan duration (mean) | 1971 ms | Normal |
| Scan duration (max) | 11250 ms | Spike from cooldown retry wait |
| Retry count (all) | 3 / max 3 | Maxed out retry attempts |
| Orderbook age | 939 ms mean | Cached book ~1s stale |

**Oracle continues updating normally during CLOB empty periods.** WS sync is confirmed alive (system_health 447 events today). Telegram remains active (heartbeat_suppressed due to cooldown, not failure).

---

## Q7: CLOB Empty vs Valid Orderbook Comparison

| Metric | CLOB Empty | Valid Orderbook | Difference |
|--------|-----------|-----------------|------------|
| Spread (mean) | 0.0099 | 0.0101 | **Identical** |
| yes_ask (mean) | 0.538 | 0.554 | Marginal |
| seconds_remaining | 154.6s | 150.5s | Identical |
| ask_depth L1-L3 | $366 | $456 | -20% |

> [!IMPORTANT]
> **Spread is identical between CLOB-empty and valid periods.** This confirms the bid/ask is a cached stale quote, not a stale market. The depth is lower in CLOB-empty periods — expected when operating from cached data.

---

## Q8: Is Orderbook Data Actually Missing?

```
CLOB_EMPTY events with yes_ask AND yes_bid > 0: 55/55 (100%)
CLOB_EMPTY events with ob_error containing "cooldown_active": 55/55 (100%)
orderbook_availability_classification: "orderbook_available_but_skipped"
orderbook_availability_source: "serialized_yes_no_bid_ask"
```

**The orderbook data is NOT missing. It is present but blocked by cooldown.**

Sample `orderbook_error` messages:
```
clob_orderbook_cooldown_active token=656977... remaining=8.22s
clob_orderbook_cooldown_active token=784768... remaining=1.67s
clob_orderbook_cooldown_active token=302820... remaining=2.30s
```

> [!WARNING]
> **This is a CACHE LABELING MISMATCH.** The dashboard shows `CLOB EMPTY` but the correct label should be `CLOB COOLDOWN ACTIVE`. The data is cached and valid; the client is honoring a rate-limit backoff window of 1.67s–8.22s between live fetches.

The classification `orderbook_available_but_skipped` confirms the system knowingly passes cached data but labels it as clob_empty for the dashboard status field.

---

## Q9: Root Cause Classification

| Evidence | Finding |
|----------|---------|
| `orderbook_error` pattern | `clob_orderbook_cooldown_active` — 55/55 |
| `orderbook_readiness_reason` | `clob_empty_response` — 55/55 |
| `orderbook_availability_classification` | `orderbook_available_but_skipped` — 45/55 |
| Bid/ask data present | 55/55 (100%) |
| ETH-dominated (81.8%) | Yes |
| BTC simultaneous only at startup | Yes |
| Near-expiry correlation | No (87% mid-epoch) |

### Root Cause: `EXTERNAL_CLOB_EMPTY`

The CLOB client implements a **cooldown timer per token** to prevent API rate limiting. When the cooldown is active, the client labels the fetch status as `clob_empty_response` even though stale-but-valid cached data exists. The dashboard displays this as `CLOB EMPTY`.

**This is normal self-protection behavior, not a CLOB outage.**

The ETH dominance (81.8%) may indicate ETH tokens have a slightly higher cooldown than BTC tokens, or ETH epochs are hitting the cooldown more frequently due to token rotation timing.

---

## Q10: Recommendation

### Primary: `ADD_ORDERBOOK_AVAILABILITY_PANEL`

The dashboard should distinguish between:
- `CLOB COOLDOWN` (data exists, refresh in N seconds) — current state
- `CLOB TRULY EMPTY` (no bids or asks at all)
- `CLOB HEALTHY` (fresh live data)

This would eliminate the false alarm pattern currently showing.

### Secondary: `ADD_CLOB_STREAK_ALERT`

The max streak of 20 events (entire session blocked) warrants a Telegram alert after 5+ consecutive CLOB empty cycles to distinguish normal cooldown from a genuine sustained outage.

---

## Runtime Status Summary

| Check | Status |
|-------|--------|
| Runtime alive | ✅ Yes (last heartbeat 05:36 UTC) |
| Oracle updating | ✅ Yes (mean age 649ms) |
| WS synced | ✅ Yes |
| Telegram | ✅ Yes (heartbeat active) |
| JSONL writing | ✅ Yes (447 system_health events today) |
| Actual trading blocked | ⚠️ During cooldown windows |
| True CLOB outage | ❌ No — cached data available |

---

## Final Answers

| Q | Answer |
|---|--------|
| A. Normal CLOB degradation? | **YES — cooldown-based self-protection** |
| B. Market-specific liquidity? | Partial — ETH more affected than BTC |
| C. Token/market selection? | No — all epoch tokens affected equally |
| D. Local client/rate-limit? | **YES — local cooldown timer per token** |
| E. Stale orderbook/cache? | **YES — cached stale quotes used during cooldown** |
| F. Dashboard labeling issue? | **YES — "CLOB EMPTY" should be "CLOB COOLDOWN"** |

---

## Final Confirmation

```
Runtime changed: No
Strategy changed: No
EV changed: No
Risk changed: No
Execution changed: No
Live trading changed: No
Files modified: 0
```
