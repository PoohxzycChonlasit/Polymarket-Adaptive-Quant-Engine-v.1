# Outcome Truth Audit v1

Date: 2026-05-22

Scope: read-only audit of why `trade_result` and `pnl_usdc` are null on all instrumentation-era and historical trade_close events.

Runtime behavior changed: No.

Live behavior changed: No.

Paper launch: No.

Replay run: No.

Code changed: No.

---

## Audit Scope

Files inspected:

| Source | Event type | Dates | Count |
|---|---|---|---:|
| `trade_journal/*.jsonl` | `trade_close` | 2026-05-08 → 2026-05-22 | 670 |
| `trade_journal/*.jsonl` | `trade_open` | 2026-05-08 → 2026-05-22 | 141 |
| `execution_log/2026-05-22.jsonl` | `paper_fill` | 2026-05-22 | 72 |
| `polymarket/trader.py` | `_emit_trade_closed_event`, `_emit_trade_opened_event` | — | — |
| `utils/position_tracker.py` | `Position`, `close_position` | — | — |

---

## Codebase Search Results

```
grep -rn "trade_result" *.py → 0 matches in trader.py, position_tracker.py
grep -rn "pnl_usdc"    *.py → 0 matches anywhere in codebase
```

Neither `trade_result` nor `pnl_usdc` appear anywhere in the producer code. They are never computed, never assembled, never emitted. They are absent from every dict literal in every emit path.

---

## Producer Flow

```
ENTRY
  _submit_order()
    → OrderReceipt (paper fill)
  _emit_trade_opened_event()
    → log_trade_open → trade_journal
    Emits: entry_price, size, notional_size, ev_after_spread,
           true_probability, receipt, paper_trade_replay_key,
           condition_id, epoch_start_ts, asset, ticker
    NOT emitted: stop_loss_price, take_profit_price (in risk_plan arg, not extracted)

POSITION STATE
  position_tracker.add_position()
    → Position object: entry_price, stop_loss, take_profit, size, entry_time

EXIT TRIGGER
  update_price() → stop_loss / take_profit trigger → _close_position_order()
  OR timeout / forced exit → _close_position_order()

  _close_position_order(pos, reason, exit_price)
    pnl = (exit_price - pos.entry_price) * pos.size
    position_tracker.close_position(pos.position_id, exit_price, reason)
      position.status = reason  ← "stopped_out" | "take_profit_hit" | "closed"
    _emit_trade_closed_event(
        position=pos, reason=reason, exit_price=exit_price,
        size=pos.size, pnl=pnl, receipt=receipt
    )

  _emit_trade_closed_event()   [trader.py:4108]
    → log_trade_close → trade_journal
    Emits: position_id, market_id, ticker, outcome, reason,
           exit_price, exit_timestamp, hold_seconds, size, pnl,
           partial, receipt, condition_id, epoch_start_ts, asset,
           paper_trade_replay_key, candidate_peak_favorable=None,
           candidate_peak_adverse=None
    NOT emitted: trade_result, pnl_usdc, entry_price, stop_loss_price, take_profit_price
```

`pos.entry_price` is available as a local variable at the close boundary — it is read to compute `pnl` but not written into the payload.

---

## Field-by-Field Analysis

### `trade_result`

| Question | Answer |
|---|---|
| Where should it originate? | `_emit_trade_closed_event`, derived from `reason` |
| Where should it be computed? | Not computed anywhere — never defined as a derived field |
| Did it ever exist in JSONL? | No — 0 non-null across 670 trade_close events |
| Serialization issue? | No — the field is not in the payload dict |
| Producer boundary issue? | No — the producer has everything needed but makes no mapping |
| Missing at source? | Yes — never added to payload dict |
| Lost during carry? | N/A — never emitted |
| Never emitted? | Correct |

**Root cause:** `reason` already encodes the close type (`stop_loss`, `stop_loss_hit`, `take_profit`, `take_profit_target_reached`, `forced_exit`, `emergency_flatten`, `settlement`, `residual_sweep`). A canonical `trade_result` label (WIN / LOSS / TP / SL / EXIT) was never derived from `reason` and never added to the payload. The information is present in `reason`; the normalization step was never built.

**Reason distribution across all 670 closes:**

| `reason` | Count | Implied trade_result |
|---|---:|---|
| `take_profit` | 107 | TP |
| `take_profit_target_reached` | 63 | TP |
| `take_profit_full` | 45 | TP |
| `take_profit_partial` | 65 | TP (partial) |
| `take_profit_runner` | 10 | TP |
| `stop_loss` | 102 | SL |
| `stop_loss_hit` | 12 | SL |
| `forced_exit` | 92 | EXIT |
| `emergency_flatten` | 20 | EXIT |
| `residual_sweep` | 10 | EXIT |
| `test` | 144 | DISCARD |

The mapping is stable and unambiguous. `trade_result` = canonical normalization of `reason`.

**Classification: C — Missing Calculation.**

---

### `pnl_usdc`

| Question | Answer |
|---|---|
| Where should it originate? | `_emit_trade_closed_event`, USDC-denominated version of `pnl` |
| Where should it be computed? | Not computed anywhere — string "pnl_usdc" does not exist in codebase |
| Did it ever exist in JSONL? | No — 0 non-null across 670 trade_close events |
| Is there a functionally equivalent field? | Yes — `pnl` field IS emitted |
| What is `pnl` denominated in? | Token PnL: `(exit_price − entry_price) × size` |
| Is `pnl` semantically equivalent to USDC PnL? | Yes — Polymarket prices are in USD; `pnl` is already USD-denominated |
| Serialization issue? | No — the field is not in the payload dict |

**What `pnl` actually is (instrumentation era, Phase 5 run):**

| Trade | `reason` | entry | exit | size | `pnl` computed | `pnl_usdc` equiv |
|---|---|---:|---:|---:|---:|---:|
| 1 | `stop_loss_hit` | 0.57 | 0.55 | 0.0925 | −0.001850 | −$0.001850 |
| 2 | `take_profit_target_reached` | 0.49 | 0.59 | 0.1025 | +0.010254 | +$0.010254 |
| 3 | `stop_loss` | 0.52 | 0.34 | 0.0967 | −0.017401 | −$0.017401 |

`pnl` = `(exit_price − entry_price) × size` — computed in `_close_position_order` at line 8982, passed directly to `_emit_trade_closed_event`. In Polymarket's binary market model (token prices in [0, 1] USD), this is already the USD PnL. `pnl_usdc` would be a label that makes the denomination explicit — the underlying value is identical.

**Root cause:** `pnl_usdc` was a planned field label that was never added to the payload. `pnl` carries the same value. The label gap is the only gap.

**Classification: C — Missing Calculation (label gap variant).**

---

### Secondary Finding A: `entry_price` on `trade_close`

`entry_price` is not emitted in the close event payload (`_emit_trade_closed_event` has no `entry_price` key). It IS available on the `pos` object as `pos.entry_price` at call time — it is read to compute `pnl` but dropped. Without `entry_price` on the close event, the close cannot be fully self-describing; the open must be joined to recover the entry.

**Classification: A — Observability Gap.**

---

### Secondary Finding A: `stop_loss_price` / `take_profit_price` on `trade_open`

`_emit_trade_opened_event` receives `risk_plan: RiskPlan` as a parameter. `risk_plan.stop_loss_price` and `risk_plan.take_profit_price` are populated and passed in. Neither is extracted into the payload dict. The `"risk_plan"` key is only present in the `decision` log (via `_risk_plan_payload`), not in the trade_open journal event.

**Classification: A — Observability Gap.**

---

### Secondary Finding D: Trace ID Misalignment Between trade_open and trade_close

`execution_trace_id` and `candidate_trace_id` differ between trade_open and trade_close for the same position. They cannot be used as join keys.

**Valid join key:** `paper_trade_replay_key` — confirmed identical across trade_open and trade_close for all three Phase 5 pairs:

| Pair | trade_open `et` | trade_close `et` | `paper_trade_replay_key` match |
|---|---|---|---|
| 1 | `et_6daf5acfe035229b` | `et_9fdfea55c8b34c16` | YES |
| 2 | `et_a6a74c3350b157b4` | `et_04078d5a8e30bc14` | YES |
| 3 | `et_5e3b944f28a967ba` | `et_0e605bdf9923eb5c` | YES |

**Classification: D — Producer Boundary loss.** The trace ID chain breaks at the open-to-close boundary. `paper_trade_replay_key` is the reliable join key, but it requires a cross-event join to reconstruct full trade evidence.

---

## Historical Evidence Check

Swept all 670 `trade_close` events across 2026-05-08 → 2026-05-22.

| Field | Non-null count | Null count | Ever populated? |
|---|---:|---:|---|
| `trade_result` | 0 | 670 | Never |
| `pnl_usdc` | 0 | 670 | Never |
| `pnl` | 670 | 0 | Always |
| `reason` | 670 | 0 | Always |
| `exit_price` | 670 | 0 | Always |
| `entry_price` (on close) | 0 | 670 | Never |

`pnl` and `reason` have been consistently emitted since 2026-05-08. `trade_result` and `pnl_usdc` have never appeared. This is not a regression — they were never implemented.

---

## Classification Summary

| Field | Category | Classification | Root Cause |
|---|---|---|---|
| `trade_result` | **C** | Missing Calculation | Never computed or emitted; `reason` is functional equivalent, mapping not built |
| `pnl_usdc` | **C** | Missing Calculation (label gap) | Never emitted; `pnl` is the identical value without the explicit denomination label |
| `entry_price` on close | **A** | Observability Gap | Available on `pos.entry_price` at close time, not written into payload |
| `stop_loss_price` / `take_profit_price` on open | **A** | Observability Gap | In `risk_plan` arg, not extracted into payload |
| trace ID chain break | **D** | Producer Boundary Loss | `et` / `ct` differ; `paper_trade_replay_key` is correct join key |

No Category B (serialization gap) — JSONL structure intact throughout.  
No Category E (intentional null) — no evidence these were deliberately excluded.

---

## Patch Candidate Assessment

All three primary gaps (`trade_result`, `pnl_usdc`, `entry_price` on close) are patchable from a single method: `_emit_trade_closed_event` in `trader.py:4108`.

**Proposed additions to `_emit_trade_closed_event` payload:**

```python
# trade_result: derive from reason
_reason_to_result = {
    "take_profit": "TP", "take_profit_target_reached": "TP",
    "take_profit_full": "TP", "take_profit_partial": "TP_PARTIAL",
    "take_profit_runner": "TP",
    "stop_loss": "SL", "stop_loss_hit": "SL",
    "forced_exit": "EXIT", "emergency_flatten": "EXIT",
    "residual_sweep": "EXIT", "settlement": "SETTLEMENT",
}
trade_result = _reason_to_result.get(reason, "EXIT")

# pnl_usdc: same value as pnl (already USD in polymarket binary model)
# entry_price: already available as pos.entry_price at close time
```

Payload additions (additive, no existing field changed):

```python
"entry_price": float(getattr(position, "entry_price", None) or 0.0),
"trade_result": trade_result,
"pnl_usdc": float(pnl),  # same formula, explicit denomination
```

**Stop_loss_price / take_profit_price** require `risk_plan` to be passed to `_emit_trade_closed_event` (it currently is not) or retrieved from position metadata.

---

## Recommendation

```
PATCH_CANDIDATE
```

`trade_result` and `pnl_usdc` are both computationally trivial to add. All required inputs (`reason`, `pnl`, `pos.entry_price`) are available at the close boundary without any new data collection. The patch is additive, does not touch execution paths, and does not affect any runtime behavior.

**Patch scope:** `_emit_trade_closed_event` only — one method, three new payload keys.

**Separate scope (lower priority):** `stop_loss_price` / `take_profit_price` on trade_open — requires extracting from `risk_plan` in `_emit_trade_opened_event`. Useful for Phase 6 threshold auditing but not blocking.

**Evidence impact:** After patch, the harvest monitor can record confirmed `trade_result` values instead of inferred outcomes. TP/SL readiness gate counts become reliable. The patch does not change Phase 6 readiness status — existing evidence remains insufficient — but future runs will produce clean ground-truth outcome data.

**Pre-patch:** The inferred outcome analysis in the harvest monitor (using `reason` + `pnl` sign) is directionally correct and can be used as interim evidence with the caveat that outcomes are inferred, not confirmed.

---

## Confidence

| Claim | Confidence |
|---|---|
| `trade_result` never emitted | HIGH — grep confirms zero occurrences in codebase |
| `pnl_usdc` never emitted | HIGH — grep confirms zero occurrences in codebase |
| `pnl` = USD-equivalent PnL | HIGH — formula confirmed as `(exit−entry)×size`; Polymarket binary prices in USD |
| `reason` is reliable TP/SL proxy | HIGH — 670 closes, consistent vocabulary, stable distribution |
| `paper_trade_replay_key` is correct join key | HIGH — confirmed identical across all 3 Phase 5 pairs |
| Patch is safe (additive only) | HIGH — no execution path touched, payload-only change |
