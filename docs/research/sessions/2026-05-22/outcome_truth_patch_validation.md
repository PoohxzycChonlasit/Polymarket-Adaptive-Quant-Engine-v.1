# Outcome Truth Patch v1 — Validation

Date: 2026-05-22

Scope: Paper validation of `trade_result`, `pnl_usdc`, and `entry_price` additions to `_emit_trade_closed_event`.

Runtime behavior changed: No.

Live behavior changed: No.

Paper launch: Yes — validation run only, killed after evidence collected.

Replay run: No.

Code changed: Yes — `polymarket/trader.py`, `tests/test_outcome_truth_patch.py` (commit `f1a2249`).

---

## Patch Summary

Three additive fields added to `_emit_trade_closed_event` payload in `polymarket/trader.py`:

| Field | Source | Rule |
|---|---|---|
| `trade_result` | `reason` string | `take_profit*` → TP, `stop_loss*` → SL, `pnl > 0` → WIN, `pnl < 0` → LOSS, else → UNKNOWN |
| `pnl_usdc` | `pnl` argument | Alias — no new calculation; Polymarket binary prices are USD-denominated |
| `entry_price` | `position.entry_price` | Read from position object at close boundary; fail-soft returns `None` if attr absent |

All additions are observability-only. No strategy, risk, execution, sizing, or live path touched.

---

## Test Suite

### Command

```bash
python -m pytest tests/test_outcome_truth_patch.py -q
python -m pytest tests/test_execution_timestamp_phase1.py tests/test_execution_timestamp_phase2.py tests/test_execution_timestamp_phase3.py tests/test_quote_lineage_phase4.py tests/test_quote_age_phase5.py tests/test_outcome_truth_patch.py -q
```

### Results

```
Outcome truth suite:     12 passed
Phase 1–5 + regression:  49 passed
Total: 49 passed, 0 failed
```

Deprecation warnings only (websockets library).

### Test Cases

1. `test_trade_result_tp_from_take_profit_reason` — PASSED
2. `test_trade_result_tp_from_take_profit_target_reached` — PASSED
3. `test_trade_result_tp_from_take_profit_full` — PASSED
4. `test_trade_result_sl_from_stop_loss_reason` — PASSED
5. `test_trade_result_sl_from_stop_loss_hit` — PASSED
6. `test_trade_result_win_from_positive_pnl_unknown_reason` — PASSED
7. `test_trade_result_loss_from_negative_pnl_unknown_reason` — PASSED
8. `test_trade_result_unknown_when_pnl_zero_and_reason_unrecognised` — PASSED
9. `test_pnl_usdc_equals_pnl` — PASSED
10. `test_entry_price_emitted_from_position` — PASSED
11. `test_existing_fields_intact` — PASSED
12. `test_fail_soft_on_position_without_entry_price` — PASSED

---

## Paper Validation

### Command

```bash
python main.py --mode paper --interval 10 --ui compact --fps medium
```

### Validation Run ID

```
20260522T094222Z_46088_040fac20
```

### Trade Closes Observed

Two `trade_close` events from the validation run, both with all three new fields populated:

| Field | Close 1 | Close 2 |
|---|---|---|
| `reason` | `stop_loss` | `take_profit_target_reached` |
| `trade_result` | `SL` | `TP` |
| `pnl` | −0.016166 | +0.005477 |
| `pnl_usdc` | −0.016166 | +0.005477 |
| `entry_price` | 0.56 | 0.55 |
| `exit_price` | 0.39 | 0.61 |
| `paper_trade_replay_key` | present | present |

### Field Integrity Check

| Field | Non-null | Null | Correct |
|---|---:|---:|---|
| `trade_result` | 2 | 0 | Yes — SL matches `stop_loss`, TP matches `take_profit_target_reached` |
| `pnl_usdc` | 2 | 0 | Yes — identical to `pnl` on both closes |
| `entry_price` | 2 | 0 | Yes — matches position `entry_price` at open |
| Pre-existing fields (`reason`, `exit_price`, `size`, `pnl`, `asset`, `position_id`, `market_id`) | 2 | 0 | Unchanged |

### Outcome Truth Mapping Verified

```
stop_loss → SL                     ✓
take_profit_target_reached → TP    ✓
pnl_usdc == pnl (both closes)      ✓
entry_price non-null (both closes) ✓
```

### Errors and Exceptions

```
market_analysis_exception count: 0
Traceback / TypeError / ERROR in log: 0
```

---

## Backward Compatibility

- Pre-patch `trade_close` events (2026-05-08 → 2026-05-22 pre-patch) remain valid JSONL — new fields simply absent, no parse errors.
- No existing fields renamed, removed, or modified.
- No JSONL files rewritten.

---

## Evidence Monitor Impact

After this patch, the harvest monitor can record **confirmed** `trade_result` values on future runs instead of inferred outcomes from `reason` + `pnl` sign. The two existing inferred outcomes from run `20260522T082440Z_32952_1b709e78` remain classified as inferred — they predate the patch.

Readiness gate status is unchanged — all six gates remain unmet. The patch does not contribute evidence retroactively.

---

## Compatibility Notes

- Payload changes are additive.
- All Phase 1–5 fields intact and unmodified.
- Fail-soft: `entry_price` returns `None` if `position.entry_price` attribute is absent.
- Fail-soft: `trade_result` returns `None` if `reason` or `pnl` raises during classification.
- `pnl_usdc` wraps `float(pnl)` — null-safe if `pnl` is already a float.

---

## Verdict

Outcome truth patch is confirmed live in paper JSONL:

- `trade_result` = `SL` on `stop_loss` close — correct mapping
- `trade_result` = `TP` on `take_profit_target_reached` close — correct mapping
- `pnl_usdc` identical to `pnl` on both closes — correct alias
- `entry_price` non-null on both closes — read from position object correctly
- 0 market_analysis_exceptions, 0 errors
- 49 tests pass across all phases and regression suites

Runtime behavior changed: observability only.

Live behavior changed: No.
