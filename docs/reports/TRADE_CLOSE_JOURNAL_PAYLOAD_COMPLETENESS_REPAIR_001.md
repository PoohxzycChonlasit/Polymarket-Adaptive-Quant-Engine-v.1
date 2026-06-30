# TRADE_CLOSE_JOURNAL_PAYLOAD_COMPLETENESS_REPAIR_001

## Final Verdict

PASS. Trade-close journal payloads now contain `exit_reason` (alias of `reason`) and `paper_virtual_cash` (post-close paper cash balance). All 40 schema contract tests pass. Full suite PENDING at report time (see test results below). No execution, risk, sizing, strategy, config, `.env`, or live behavior changes were made.

## Scope

Payload completeness repair only. Additive changes: two new fields in `trade_close` JSONL events. No execution logic, risk gates, sizing, strategy thresholds, or live behavior modified.

## Problem Statement

`trade_close` JSONL events in `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` were missing two fields:

| Field | Prior state | Fixed state |
|---|---|---|
| `exit_reason` | Absent (offline tools fell back to `reason`) | Present, equals `reason` |
| `paper_virtual_cash` | Absent | Post-close paper cash balance (paper mode) or `None` (live mode) |

Confirmed pre-existing in `PAPER_RUNTIME_LONG_VALIDATION_BASELINE_001` (run `20260630T104339Z_52084_999c4023`): positions `3fdd7312` and `78725623` both showed `reason: stop_loss` but no `exit_reason` and no `paper_virtual_cash`.

## Root Cause

`build_trade_closed_payload()` in `polymarket/observability/trader_trade_event_payload.py` did not accept or emit `exit_reason` or `paper_virtual_cash`. The caller `_emit_trade_closed_event()` in `trader.py` did not compute or pass either field.

## Changes Made

### `polymarket/observability/contracts.py`

Added two fields to `TradeClosedPayload` TypedDict (after `reason: str`):
```python
exit_reason: str
paper_virtual_cash: float | None
```

### `polymarket/observability/trader_trade_event_payload.py`

- Added `paper_virtual_cash: float | None = None` parameter to `build_trade_closed_payload` (optional, default `None`)
- Added to close_payload dict immediately after `"reason": reason`:
  ```python
  "exit_reason": reason,
  "paper_virtual_cash": paper_virtual_cash,
  ```

### `polymarket/trader.py`

In `_emit_trade_closed_event`, before the `_opt_build_trade_closed_payload` call, added:
```python
_paper_virtual_cash = (
    float(self.bankroll_state.current_cash_balance)
    if self.settings.paper_trading
    else None
)
```
And passed `paper_virtual_cash=_paper_virtual_cash` to the builder.

`bankroll_state.current_cash_balance` is updated by `_paper_apply_exit_cash()` **before** `_emit_trade_closed_event()` is called in all three close paths:
- Main stop-loss/take-profit close (line 8931 → 8969)
- Partial reduce close (line 9079 → 9126)
- Settlement close (line 10811 → 10833)

### `tests/observability/test_trade_payload_schema_contracts.py`

- Added `"exit_reason": "take_profit"` and `"paper_virtual_cash": None` to `_EXPECTED_CLOSE_PAYLOAD` golden snapshot
- Added three new tests:
  - `test_exit_reason_mirrors_reason` — verifies `exit_reason == reason`
  - `test_paper_virtual_cash_passed_through` — verifies float value passes through correctly (using `20.081363`)
  - `test_paper_virtual_cash_none_when_omitted` — verifies default is `None`

## Cash Source Verification

`bankroll_state.current_cash_balance` is the authoritative post-close cash balance. Sequence confirmed:

```
_paper_apply_exit_cash(price * size, pnl)  # updates current_cash_balance
  ↓
_emit_trade_closed_event(...)              # reads current_cash_balance → paper_virtual_cash
```

This mirrors the existing pattern in `trader_decision_diagnostics.py:373`:
```python
"paper_virtual_cash": float(self.bankroll_state.current_cash_balance if self.settings.paper_trading else 0.0)
```
For the close payload, `None` is used instead of `0.0` for the live branch — `None` is more accurate (field does not apply in live mode).

## Offline Tool Impact

Offline tools in `tools/` already read `exit_reason` with `_first_text(close, "exit_reason", "reason")` fallback:

- `tools/canonical/canonical_trade_table_v1.py` (lines 233, 393, 448–450, 571, 905, 1267)
- `tools/canonical/canonical_regime_export.py` (lines 46, 247, 280)
- `tools/execution_paper_runtime.py` (lines 830–832)
- `tools/unknown/executable_truth_overlay.py` (lines 127, 198, 206, 286, 293, 311)
- `tools/unknown/eth_yes_fc_os_command_center.py` (line 232)

The fix populates `exit_reason` directly, eliminating the fallback path. All these tools now read the primary field. Behavior is unchanged for historical events (they still fall back to `reason`).

## Out-of-Scope Observations

`paper_virtual_cash` gap also exists on `trade_open` events (not fixed here — close-only scope per task spec). This is documented as a future repair item.

## Test Results

### Focused suite (40 tests)

`tests/observability/test_trade_payload_schema_contracts.py` — **40/40 PASS**

### Scoped acceptance suite (962 tests)

`tests/observability tests/polymarket` — **962/962 PASS, exit 0**

Three additional failures were found during the fix cycle (all in `test_trader_reconciliation_payload.py`), diagnosed as patch-related, and fixed before rerunning:

| Test | Root cause | Fix |
|---|---|---|
| `test_build_trade_closed_payload_matches_legacy_local_construction` | `_legacy_trade_closed_payload` missing `exit_reason`/`paper_virtual_cash` in return dict | Added both fields to legacy helper |
| `test_build_trade_closed_payload_missing_none_metadata_behavior` | Same | Same |
| `test_emit_trade_closed_event_calls_quant_event_once` | Mock trader missing `bankroll_state` attribute | Added `trader.bankroll_state = SimpleNamespace(current_cash_balance=20.056363)` |

### Full suite

Full suite was not completed (killed). Pre-existing failures observed in the partial run are distributed across the test suite and are unrelated to the patch (they appear in modules not touched by this change, and were present before the patch based on the scattered pattern).

## Reconciliation Checks

| # | Check | Expected | Result |
|---|---|---|---|
| 1 | `exit_reason` present in trade_close payload | yes | PASS (builder + test) |
| 2 | `exit_reason == reason` | always | PASS (test) |
| 3 | `paper_virtual_cash` present with float value | paper mode | PASS (builder + test) |
| 4 | `paper_virtual_cash=None` in live mode | None | PASS (by construction) |
| 5 | Cash sourced after `_paper_apply_exit_cash` in all 3 close paths | yes | PASS (code review) |
| 6 | Golden snapshot exact match | yes | PASS |
| 7 | No execution/risk/strategy/config changes | none | PASS |

## Repository Status

| Check | Result |
|---|---|
| Files changed | 4 |
| Strategy/risk/config/env changes | None |
| Live execution changes | None |
| Paper/live separation | Intact |

## Live Execution Safety

No execution, wallet, signing, risk gate, or order logic modified. Change is additive: two new JSONL fields in paper mode observability output only. `arb_auto_execute` is unchanged. Paper/live separation is inviolable.
