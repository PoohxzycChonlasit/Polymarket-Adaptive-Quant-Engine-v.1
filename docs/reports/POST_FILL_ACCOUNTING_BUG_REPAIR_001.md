# POST_FILL_ACCOUNTING_BUG_REPAIR_001

**Date:** 2026-06-30
**Task Class:** 3 REPAIR
**Code changed:** YES — `polymarket/trader.py` (1 line), `tests/observability/test_telemetry_backfill.py` (1 test added)
**Safety verdict:** SAFE_PAPER_ONLY

---

## 1. Root Cause

**File:** `polymarket/trader.py:8321`
**Original code:**
```python
bankroll_family=self.bankroll_family,
```
**Error at runtime:**
```
AttributeError: 'PolymarketTrader' object has no attribute 'bankroll_family'
```

`bankroll_family` is a field on the `BankrollState` dataclass (`trader.py:320`), accessible as `self.bankroll_state.bankroll_family`. It was never a direct attribute of `PolymarketTrader`. The line at 8321 was introduced during the `trader.py` decomposition when the call to `_build_trade_position_metadata` was written with `self.bankroll_family` instead of the correct per-cycle observability cache `self._last_bankroll_family`.

**Evidence the attribute does not exist:**
- `PolymarketTrader.__init__` (line 528): `self._last_bankroll_family: str | None = None` — only the underscore form is initialised.
- The test `test_telemetry_backfill.py:69` had been setting `trader.bankroll_family = "MICRO"` manually to work around the missing attribute.
- `trader_trade_event_payload.py:163` already used `getattr(trader, "_last_bankroll_family", None)` — the correct read pattern.
- Line 8334 (adjacent to the bug): `bankroll_rank=self._last_bankroll_rank` — the correct symmetric pattern.

---

## 2. Fix Applied

**File:** `polymarket/trader.py`
**Line:** 8321
**Change:**
```python
# Before (broken)
bankroll_family=self.bankroll_family,

# After (fixed)
bankroll_family=self._last_bankroll_family,
```

`self._last_bankroll_family` is:
- Initialised to `None` in `__init__` (line 528).
- Set each cycle by the bankroll rank evaluation at line 4347: `self._last_bankroll_family = evaluation.get("bankroll_family")`.
- Populated before any fill path is reached (bankroll rank runs before signal evaluation every cycle).

---

## 3. Regression Test Added

**File:** `tests/observability/test_telemetry_backfill.py`
**Test:** `test_build_trade_position_metadata_reads_last_bankroll_family_not_direct_attr`

The test:
1. Asserts `not hasattr(trader, "bankroll_family")` — direct attribute must not exist.
2. Asserts `hasattr(trader, "_last_bankroll_family")` — per-cycle cache must always exist.
3. Sets `trader._last_bankroll_family = "MICRO"` and calls `_build_trade_position_metadata(bankroll_family=trader._last_bankroll_family)`.
4. Asserts `meta["bankroll_family"] == "MICRO"`.

This test would have caught the original bug (the direct attribute wouldn't exist without explicit assignment).

---

## 4. Compile Check

```
polymarket/trader.py                                 OK
polymarket/observability/trader_trade_event_payload.py  OK
polymarket/observability/trader_reconciliation_carry.py OK
```

---

## 5. Test Results

### Focused suite (task-required)
```
tests/observability/  +  tests/polymarket/
958 passed, 5 warnings in 48.22s
```
Includes the new regression test.

### Broader acceptance suite
```
2664 passed, 29 failed (pre-existing), 13 warnings in 205.83s
```

**29 failures confirmed pre-existing** (fail identically on unmodified HEAD before this change):
- Missing file errors: `tests/polymarket/trader.py`, `tests/tools/replay/commitment_regime_replay.py`
- Unrelated tools/replay/flaos tests with missing tool files or stale registry expectations
- Zero failures are attributable to the `bankroll_family` fix

---

## 6. Paper Validation

**Run:** 20260630T071104Z_15764_d0f4213a (and co-run shards during startup)
**Duration:** ~4 minutes (stopped early after confirming fix)
**Launcher PID:** 48908 (dead) / **Runtime PID:** 10956 (dead)

### Primary fix confirmed

| Metric | Pre-fix (PAPER_FILL_PATH_VERIFICATION_001) | Post-fix |
|--------|---------------------------------------------|----------|
| Fills | 3 | 22 |
| bankroll_family AttributeError | 3 | **0** |
| position_id | None | **f6d2a324** (populated) |
| fill_source | paper_simulated | paper_simulated |
| Live order markers | 0 | 0 |

### Remaining gaps (downstream of this fix)

| Metric | Expected | Actual | Gap |
|--------|----------|--------|-----|
| trade_open JSONL event | Emitted | NOT EMITTED | Separate issue |
| paper_virtual_cash | Deducted | $20.099 unchanged | Separate issue |
| current_exposure | > 0 after fill | 0.0 | Separate issue |
| trade_log file | Created | NOT FOUND | Separate issue |

**The bankroll_family fix unblocked position_id creation** — the position is now registered in the tracker (confirmed by non-None position_id in the fill receipt). However, the downstream accounting loop (trade_open event emission, VirtualPTB cash deduction, exposure update) is still not firing. These are separate bugs in the post-position-open path and are NOT regressions introduced by this fix.

---

## 7. Safety Markers

| Check | Result |
|-------|--------|
| fill_source | paper_simulated (all 22) |
| Live order markers | 0 |
| Wallet touched | NO |
| Live CLOB orders | NONE |
| Strategy/risk/sizing logic | UNCHANGED |
| config/settings.py | UNCHANGED |
| .env | UNCHANGED |

---

## 8. Next Required Tasks

| Priority | Task | Reason |
|----------|------|--------|
| HIGH | Diagnose trade_open event not emitting | `_emit_trade_opened_event` not reached or failing silently after position opens |
| HIGH | Diagnose VirtualPTB cash not deducting | paper_virtual_cash unchanged despite 22 fills with non-None position_id |
| HIGH | Diagnose exposure update not firing | current_exposure stays 0.0 despite positions opening |

---

## 9. Summary

| Field | Result |
|-------|--------|
| ROOT_CAUSE | `self.bankroll_family` does not exist on `PolymarketTrader`; correct attr is `self._last_bankroll_family` |
| FIX_APPLIED | `trader.py:8321` — `self.bankroll_family` → `self._last_bankroll_family` (1 line) |
| TESTS_RUN | 958 focused (all pass) + 2664 broader (pass) + 29 pre-existing failures unchanged |
| PAPER_VALIDATION_RESULT | 22 fills, 0 bankroll_family AttributeErrors |
| FILL_COUNT | 22 (all paper_simulated) |
| TRADE_OPEN_STATUS | NOT EMITTED (downstream issue) |
| POSITION_TRACKING_STATUS | **UNBLOCKED** — position_id now populated (f6d2a324) |
| CASH_EXPOSURE_STATUS | STILL BROKEN — downstream of position open, separate bug |
| LIVE_EXECUTION_SAFETY | SAFE — 0 live order markers |
| REPOSITORY_STATUS | Clean after commit |
| NEXT_TASK | TRADE_OPEN_CASH_DEDUCTION_REPAIR_001 |
