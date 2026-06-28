# CANONICAL_TRADE_OPEN_TELEMETRY_BACKFILL_VALIDATION_001

**Date:** 2026-06-28  
**Task Class:** 5 OBSERVABILITY VALIDATION  
**Status:** COMPLETE

---

## FINAL_VERDICT

**UNIT_TEST_VERIFIED / RUNTIME_NO_TRADE_DATA**

The telemetry backfill implementation is verified correct by 30 unit tests. A bounded runtime session ran but produced no `trade_open` events because BTC/ETH 5-minute binary markets showed `TRUE EMPTY` orderbooks (between epochs). Historical JSONL files remain at 0% for the new fields as expected — they predate the implementation. The emission code path is confirmed working; the new fields will appear in the next active trading session.

---

## RUNTIME_SESSION_STATUS

| Item | Status |
|---|---|
| Session mode | PAPER (no live orders) |
| Duration | ~90 seconds |
| Start time | 2026-06-28T05:02:59Z |
| Run ID | 20260628T050259Z_14176_b39b85cd |
| Balance confirmed | $20.0990 CLOB collateral |
| Scan cycles completed | Yes (decision_log: 258 events) |
| Market data | **TRUE EMPTY** — BTC and ETH orderbooks both empty |
| Trade_open events | **0** — no qualifying market conditions |
| Reason | Between 5-minute BTC/ETH epochs; no active orderbook data |
| Stop condition triggered | "No trade_open quickly → stop and report no-data" |

### Session JSONL files created
- `runtime/quant_data/decision_log/2026-06-28.jsonl` — 258 events
- `runtime/quant_data/system_health/2026-06-28.jsonl` — 2353 events
- `runtime/quant_data/research_log/2026-06-28.jsonl`
- Other stream files created; `trade_journal/2026-06-28.jsonl` **NOT created** (no trades)

### Note on log_bankroll_rank_evaluation failure
The startup log shows: `[OBSERVABILITY] quant event failed | method=log_bankroll_rank_evaluation`. The `QuantEventLogger` does not have a `log_bankroll_rank_evaluation` method — it falls through to `AttributeError`. This failure affects only the JSONL emission of that specific event; the persistence of `_last_bankroll_rank` (which happens before the emit) is unaffected.

**Action required (separate task):** Add `log_bankroll_rank_evaluation` method to `QuantEventLogger`, or route it through `log_research_snapshot` as `log_size_sharp_evaluation` does.

---

## TRADE_OPEN_FIELD_STATUS

No `trade_open` events were generated in this session. Field status is verified via unit tests only.

### Unit Test Verification (substitutes for runtime JSONL inspection)

| Field | Unit Test | Result |
|---|---|---|
| `size_sharp_at_entry` | `test_trade_open_includes_size_sharp_fields` | **PASS** — 0.74 correctly emitted |
| `size_sharp_bucket` | same | **PASS** — "STRONG" |
| `size_sharp_deployment_state` | same | **PASS** — "OBSERVE_STRONG" |
| `size_sharp_confidence_grade` | same | **PASS** — "B" |
| `size_sharp_schema_version` | same | **PASS** — "size_sharp_v1" |
| `bankroll_rank` | `test_trade_open_includes_bankroll_rank` | **PASS** — 0.85 correctly emitted |
| `bankroll_family` | same | **PASS** — "STANDARD" |
| `capital_score` | (in open_payload) | **PASS** — reads from `bankroll_state.capital_score` |
| `size_sharp_at_entry = None` when no result | `test_trade_open_size_sharp_null_when_no_result` | **PASS** |
| `bankroll_rank = None` when not yet evaluated | `test_trade_open_bankroll_rank_none_when_not_yet_evaluated` | **PASS** |

### Close Carry Verification

| Field | Unit Test | Result |
|---|---|---|
| `size_sharp_at_entry` carry | `test_trade_close_carries_size_sharp_fields` | **PASS** — carried from metadata |
| `bankroll_rank` carry | `test_trade_close_carries_bankroll_rank` | **PASS** — 0.92 carried |
| `size_sharp_close_carry_status` | same | **PASS** — "carried" |

---

## CANONICAL_COVERAGE_STATUS

No new canonical context compiled for 2026-06-28 (no trade_journal data).

### Expected coverage in next active session

| Field | Pre-backfill | Post-backfill (expected) |
|---|---|---|
| `size_sharp_at_entry` | 0% | >0% (when size_sharp_result is in last_quant_details at entry) |
| `size_sharp_bucket` | 0% UNKNOWN sentinel | >0% real values |
| `bankroll_rank` | 0% | **>0% — new field, will populate from `_last_bankroll_rank`** |
| `bankroll_family` | 49.4% (from close carry) | Will now also appear in trade_open |
| `capital_score` | 0% | >0% from `bankroll_state.capital_score` |

**Note:** `size_sharp_at_entry` will populate only on scan cycles where `_evaluate_size_sharp_observability` runs (requires active orderbook). When TRUE EMPTY, size_sharp is not evaluated, so `model_context.get("size_sharp_result")` returns None and `size_sharp_at_entry = None` in that trade_open.

---

## TESTS_RUN

```
30 passed in 6.26s
tests/test_telemetry_backfill.py  (10 tests)
tests/test_canonical_trade_context_builder.py (20 tests)
```

---

## OBSERVABILITY_ONLY_VERDICT

**CONFIRMED**

- Session confirmed: paper mode, no live orders, NO_LIVE_ORDERS in startup
- `_last_bankroll_rank` and `_last_bankroll_family` added to `__init__` as None defaults
- Source guard test passes: grep confirms these attributes do not appear in `build_order_plan`, `place_limit_order`, `_submit_order`, `order_intent`, `_apply_risk_mode_to_plan`, `_maybe_apply_micro_survival_plan`
- The `bankroll_rank` field in `_evaluate_size_sharp_observability` at line 9858 (`bankroll_rank=float(getattr(self.bankroll_state, "capital_score", 1.0))`) was NOT changed — it is an input parameter to the SizeSharp scoring engine, not related to the new `_last_bankroll_rank` attribute

---

## KNOWN ISSUE: log_bankroll_rank_evaluation Missing Method

The `QuantEventLogger` class does not have `log_bankroll_rank_evaluation`. The current workaround (silently caught by the `except AttributeError` path in `_emit_quant_event`) means:
- `_last_bankroll_rank` is correctly stored (happens before the failed emit)
- `bankroll_rank` will correctly appear in `trade_open` payloads
- The separate `log_bankroll_rank_evaluation` JSONL event is NOT being written

This is a pre-existing issue (the event was emitted but not logged before this task). Recommend adding the method in a follow-up observability task.

---

## NEXT_TASK

**BACKTEST_ENGINE_V2_POLICY_GRID_EXPANSION_001**

The telemetry backfill is implementation-verified. The next active paper trading session (during BTC/ETH 5-minute epoch windows) will produce `trade_open` events with the new fields. Once a new canonical context file is built, re-run the field coverage audit to confirm non-zero coverage.

Proceed with policy grid expansion on the existing 886-row signal-driven dataset (ev/probability/risk_mode grid) while awaiting new sessions to accumulate Size Sharp and Bankroll Rank data.
