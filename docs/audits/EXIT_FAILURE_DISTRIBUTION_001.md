# EXIT_FAILURE_DISTRIBUTION_001
**Mode: DISCOVERY ONLY**
**Date: 2026-06-25**
**Evidence: runtime/quant_data/execution_log/2026-06-25.jsonl + trade_journal/2026-06-25.jsonl**

---

## Methodology

Exit failures are identified by `payload.event: "exit_submit_failed"` in `execution_log/2026-06-25.jsonl`. Each event is attributed to a session via `run_id`. Sessions are categorized as PRIMARY (production) or GHOST (test/scratch artifacts).

Total `exit_submit_failed` events: **8**

---

## Session Attribution

| Session PID | UTC Start | Type | exit_submit_failed count | trade_close (ghost) |
|---|---|---|---|---|
| 20260625T045030Z_* | 04:50 UTC | GHOST (yes-token) | 2 | 1 |
| 20260625T045400Z_* | 04:54 UTC | GHOST (yes-token) | 2 | 1 |
| 20260625T051800Z_* | 05:18 UTC | GHOST (yes-token) | 2 | 1 |
| 20260625T053200Z_* | 05:32 UTC | GHOST (yes-token) | 2 | 1 |
| **20260625T061908Z_44848_cb552b16** | **06:19 UTC** | **PRIMARY** | **0** | **0 ghost, 45 real** |
| 20260625T075100Z_* | 07:51 UTC | Secondary (empty book) | 0 | 0 |
| **TOTAL** | | | **8** | |

---

## Failure Distribution by Type

| Failure Type | Count | % | Root Cause |
|---|---|---|---|
| Ghost session / test placeholder token_id | 8 | 100% | `yes-token` positions from `scratch/bounded_runtime_validation.py` |
| Primary session exit failure | 0 | 0% | — |
| Real production exit failure | 0 | 0% | — |

**All 8 failures are ghost artifacts. Zero primary session failures.**

---

## Failure Distribution by Attempt Number

Pattern per ghost session: 2 failed attempts followed by 1 successful attempt (producing `trade_close`).

| Attempt | Count | Outcome |
|---|---|---|
| Attempt 1 (all 4 ghost sessions) | 4 | FAILED → `exit_submit_failed` |
| Attempt 2 (all 4 ghost sessions) | 4 | FAILED → `exit_submit_failed` |
| Attempt 3 (all 4 ghost sessions) | 4 | SUCCEEDED → `trade_close` |

**Lockdown not triggered**: `_trigger_lockdown("exit_failure")` requires ALL 3 attempts to fail. Attempt 3 succeeded → no lockdown in any ghost session.

---

## Failure Distribution by Token Type

| Token ID | Count of exit_submit_failed | Source |
|---|---|---|
| `"yes-token"` (test placeholder) | 8 | `scratch/bounded_runtime_validation.py` |
| Real Polymarket token hashes | 0 | — |

---

## Ghost Position Profile

All 8 failures share identical position characteristics:

| Field | Value |
|---|---|
| `token_id` | `"yes-token"` |
| `size` | `10.0` |
| `entry_price` | `0.51` |
| `session_balance` | `$100.00` (mock) |
| `lifecycle_phase` | `UNKNOWN` |
| `seconds_remaining` | `null` |
| `exit_reason` | `forced_exit` |

These characteristics confirm origin from `scratch/bounded_runtime_validation.py:121`:
```python
OrderReceipt(order_id="ord_123", status="FILLED", token_id="yes-token", side="BUY", price=0.51, size=10.0)
```

---

## Inter-Attempt Timing Anomaly

| Session | Attempt 1 → Attempt 2 Interval | Expected (default 0.5s) |
|---|---|---|
| Ghost session 04:50 | ~3ms | 500ms |
| Ghost session 04:54 | ~3ms | 500ms |

**Explanation**: Ghost sessions likely used `MockSettings` with `close_order_retry_delay_seconds=0` or near-zero. The actual delay observed (3ms) is consistent with Python overhead and no `time.sleep` call.

---

## Primary Session Exit Statistics (Confirmation)

| Metric | Value |
|---|---|
| `order_intent_approved` | 57 |
| `paper_fill` | 57 |
| `exit_submit_failed` | **0** |
| Fill success rate | **100%** |
| Trade_close events (real) | 45 (prior positions) + new ETH close later |

Primary session: **perfect exit execution record**.

---

## Execution Log Event Summary (Full Day)

| `payload.event` | Count | Attribution |
|---|---|---|
| `order_intent_approved` | 57 | Primary session |
| `order_submit_attempt` | 57 | Primary session |
| `paper_fill` | 57 | Primary session |
| `order_intent_reject` | 17 | Mix (entry rejections + possible ghost) |
| `exit_submit_failed` | 8 | Ghost sessions ONLY |
| `cancel_order` | 1 | Primary session |
| `market_analysis_exception` | 1 | Secondary session (empty book) |
| **TOTAL** | **198** | |

---

## Historical Context

| Date | exit_submit_failed | Root Cause |
|---|---|---|
| 2026-06-23 | Unknown | No yes-token in trade journal; real session |
| 2026-06-24 | Unknown | ALL trade events contain yes-token; full test day |
| **2026-06-25** | **8** | **4 ghost sessions from June 24 test residue** |

The June 24 trade journal confirms a full day of test/scratch activity that seeded the ghost state encountered at 04:50–05:32 UTC on June 25.

---

## Distribution Verdict

**Exit failures are a ghost state artifact, not a pipeline bug.** The distribution is 100% attributable to test placeholder positions. Production exit path is clean.

No pattern of recurring failure exists in production code. The `exit_submit_failed` event class may reappear if:
- Additional test/scratch sessions are run against the live runtime environment without state isolation
- A real `_submit_order` returns None for a legitimate exit (live mode only — would require API failure)

Neither scenario has occurred in the primary paper session.
