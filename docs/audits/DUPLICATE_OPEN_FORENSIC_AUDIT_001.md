# DUPLICATE_OPEN_FORENSIC_AUDIT_001

## 1. Objective & Event Details
We investigated a `duplicate_open` failure in the historical logs for **May 22, 2026** (`2026-05-22.jsonl`) on lines 1 and 2, which share the resolved identifier `ep_paper-71824750` derived from the fallback `receipt.order_id` `"paper-71824750"`.

---

## 2. Event Extraction & Analysis

### Line 1 (Open Event A)
- **Timestamp**: `2026-05-22T02:35:25.555854Z`
- **Run ID**: `20260521T133858Z_45768_ed644582`
- **Condition ID**: `0xe96b70608ff35b54aa6d59ae4cd3fe6661b94cf458db9dc7d04dd99df3ddf146`
- **Asset**: `BTC`
- **Outcome**: `YES`
- **Entry Price**: `0.63`
- **Receipt Order ID**: `paper-71824750`
- **Order Size**: `0.034277`
- **Receipt Details**:
  - `status`: `paper`
  - `token_id`: `71824750372376322825332505515488915011114848109096973164929529604849475996762`

### Line 2 (Open Event B)
- **Timestamp**: `2026-05-22T02:35:28.667052Z`
- **Run ID**: `20260521T044143Z_13704_948b4757`
- **Condition ID**: `0xe96b70608ff35b54aa6d59ae4cd3fe6661b94cf458db9dc7d04dd99df3ddf146`
- **Asset**: `BTC`
- **Outcome**: `YES`
- **Entry Price**: `0.61`
- **Receipt Order ID**: `paper-71824750`
- **Order Size**: `0.052241`
- **Receipt Details**:
  - `status`: `paper`
  - `token_id`: `71824750372376322825332505515488915011114848109096973164929529604849475996762`

---

## 3. Surrounding Context & Lifecycle Trace

To verify if these are duplicate logs, partial fills, or independent runs, we traced the events chronologically forward:

### Line 3 (Close Event A)
- **Timestamp**: `2026-05-22T02:35:31.962414Z`
- **Run ID**: `20260521T133858Z_45768_ed644582` (matches Open A)
- **Position ID**: `5a806135`
- **Exit Price**: `0.51`
- **Size**: `0.034277` (matches Open A size exactly)
- **PnL**: `-0.00411324` (matches calculation: $(0.51 - 0.63) \times 0.034277 = -0.00411324$)

### Line 4 (Close Event B)
- **Timestamp**: `2026-05-22T02:35:34.307585Z`
- **Run ID**: `20260521T044143Z_13704_948b4757` (matches Open B)
- **Position ID**: `acbd5150`
- **Exit Price**: `0.51`
- **Size**: `0.052241` (matches Open B size exactly)
- **PnL**: `-0.0052241` (matches calculation: $(0.51 - 0.61) \times 0.052241 = -0.0052241$)

---

## 4. Key Findings

1. **Two Independent Lifecycles**: The logs record two distinct, independent open-and-close trading lifecycles.
2. **Parallel Process Overlap**: The operations ran concurrently on two separate process instances or restarts, as indicated by different `run_id` strings (`20260521T133858Z_...` and `20260521T044143Z_...`).
3. **Identifier Collision**: Because they were running in `paper` mode, the order ID generation code constructed the dummy `order_id` by extracting the first 8 digits of the token ID (`"71824750"`). Since both runs traded the exact same YES token on the same condition, both ended up generating the identical receipt order ID `"paper-71824750"`.
4. **Reconciliation Failure**: Our historical parser correctly resolved both to `"ep_paper-71824750"`, leading to a `duplicate_open` collision when the second open occurred before the first was closed.

---

## 5. Final Verdict

**LEGITIMATE_MULTI_OPEN**

> [!NOTE]
> The duplicate open is caused by a **legitimate second position** running under a separate process. The identity collision occurred because the bot's paper mode generated non-unique order IDs based solely on the token's prefix. In production / live execution, order IDs are unique strings returned by the CLOB API, preventing this style of identity collision.
