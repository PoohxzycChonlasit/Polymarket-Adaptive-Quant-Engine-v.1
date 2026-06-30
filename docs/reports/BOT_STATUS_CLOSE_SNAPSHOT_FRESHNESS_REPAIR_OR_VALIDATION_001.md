# BOT_STATUS_CLOSE_SNAPSHOT_FRESHNESS_REPAIR_OR_VALIDATION_001

## Final Verdict

PASS_REPAIRED. `runtime/bot_status.json` was stale because a successful pre-close/forced-exit close could happen from the 1-second realtime loop after the most recent dashboard status snapshot and outside the end-of-cycle `run_single_cycle()` status refresh.

The repair is status-only: after `_close_position_with_retry()` completes a successful close and emits `trade_close`, it refreshes `bot_status.json` from the current tracker/cash state. The exit-agent path now passes the active countdown through to that snapshot.

## Scope

Runtime trading behavior was not changed. Strategy, sizing, risk thresholds, order submission semantics, live execution, wallet behavior, `config/settings.py`, and `.env` were not modified.

## Evidence Read

| Source | Finding |
|---|---|
| `docs/reports/TRADE_CLOSE_AND_PNL_ACCOUNTING_VALIDATION_001.md` | Target `bd919e7a` closed, trade_close emitted, cash restored, position tracker open count 0; caveat was stale `bot_status.json`. |
| `runtime/position_tracker_state.json` | Target `bd919e7a` is `closed` with `exit_reason=forced_exit`, `exit_price=0.5`, realized PnL `0.0`. |
| `runtime/bot_status.json` | Snapshot timestamp `16:43:51` still listed `bd919e7a` as `open`; target close occurred at `16:44:00`. |
| `main.py` realtime loop | `enforce_pre_close_exits(countdown)` runs every second and can close a position outside `run_single_cycle()`. |
| `polymarket/trader.py` | `run_single_cycle()` refreshed `bot_status.json` at cycle end, but `_close_position_with_retry()` did not refresh the dashboard snapshot after a successful close. |

## Root Cause

`MISSING_FLUSH_AFTER_CLOSE`.

The canonical close accounting path was correct, but the dashboard status snapshot was not refreshed immediately after a successful close. In the observed run, the controller stopped after detecting target `trade_close`, before another end-of-cycle status write could overwrite the earlier open-position snapshot.

This was not a wrong status source: `update_dashboard_status()` already reads `self.tracker.open_positions()`, which excludes closed positions. It was a freshness/order issue.

## Fix Applied

Smallest status-only repair:

- Added optional `dashboard_countdown` to `_close_position_with_retry(...)`.
- After successful `trade_close` emission, call `update_dashboard_status(...)`.
- Passed `seconds_to_close` from `_force_exit_position(...)` so forced/pre-close exits write a fresh snapshot with the active countdown.

No order submission, close approval, paper cash, PnL, risk, sizing, strategy, or live behavior was changed.

## Regression Test

Added `ExitAgentTests.test_pre_close_exit_refreshes_bot_status_snapshot`.

The test reproduces the stale snapshot shape:

1. Open a tracked paper position.
2. Write `runtime/bot_status.json` while the position is open.
3. Trigger `enforce_pre_close_exits(25)`.
4. Assert tracker open positions are empty.
5. Assert `bot_status.json.open_positions == []`.
6. Assert `current_countdown == 25`.

The test failed before the fix and passed after the fix.

## Validation

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest tests\polymarket\test_exit_agent.py::ExitAgentTests::test_pre_close_exit_refreshes_bot_status_snapshot -q --tb=short -ra` | FAIL before fix, PASS after fix |
| `.\.venv\Scripts\python.exe -m py_compile main.py polymarket\trader.py` | PASS |
| `.\.venv\Scripts\python.exe -m pytest tests\polymarket\test_exit_agent.py -q --tb=short -ra` | PASS, 12 passed |
| `.\.venv\Scripts\python.exe -m pytest tests\observability tests\polymarket -q --tb=short -ra` | PASS, 959 passed |

## Paper Validation Result

Bounded paper runtime was not rerun for this task. The stale-state condition was reproduced with a focused paper-mode close-path regression test, and current runtime state has no active owner file or open target position to close without creating fresh market exposure.

The prior bounded paper run remains the Grade A close/PnL evidence. This task adds Grade C regression proof that the first stale status writer gap is repaired.

## Bot Status Status

Repaired for successful close events through `_close_position_with_retry()`. The status snapshot now refreshes after `trade_close` with tracker state already closed and paper cash already returned.

## Position Tracker Status

No change. `position_tracker_state.json` was already canonical and correct after the prior validation.

## Live Execution Safety

Safe. The change only writes the dashboard JSON status snapshot after an already-successful close. It does not submit, cancel, sign, redeem, size, approve, or mutate wallet/live balance behavior.

## Next Task

`POST_FIX_PAPER_CLOSE_STATUS_FRESHNESS_RUNTIME_CONFIRMATION_001` if a fresh runtime confirmation is desired during the next naturally opened paper position; otherwise proceed to Replay 2.0 / Inventory Engine readiness work using `position_tracker_state.json`, `trade_journal`, and refreshed `bot_status.json` as aligned status sources.
