# PAPER_RUNTIME_LONG_VALIDATION_BASELINE_001

## Final Verdict

PASS_WITH_MINOR_ISSUES. 60-minute bounded paper runtime completed successfully. Two complete open+close trade cycles observed. All reconciliation checks pass: position counts, cash accounting, exposure, and bot_status/position_tracker consistency are all correct. Risk mode transitioned to DEFENSIVE after consecutive stop-loss hits and correctly suppressed further entries for the remainder of the run. Runtime was stable, produced no exceptions, and shows no live execution markers. Minor pre-existing gaps: `exit_reason` and `paper_virtual_cash` fields are `None` in trade_close journal payloads (pre-existing, not introduced by any recent change).

## Scope

Validation only. No strategy threshold, signal logic, sizing logic, risk threshold, execution behavior, live execution, wallet/live balance, `config/settings.py`, or `.env` changes were made.

## Runtime

```text
.\.venv\Scripts\python.exe main.py --mode paper --interval 60 --ui compact
```

| Field | Value |
|---|---|
| Run ID | `20260630T104339Z_52084_999c4023` |
| PID | `52084` |
| Start UTC | `2026-06-30T10:43:41Z` |
| Stop UTC | `2026-06-30T11:44:14Z` |
| Duration | 60.6 minutes (3636 seconds) |
| Stop method | `Stop-Process -Id 52084 -Force` after Monitor T+60 signal |

## Pre-Run State

| Field | Value |
|---|---|
| wallet_reference_balance | $20.09901 |
| position_tracker open positions | 0 |
| position_tracker daily_realized_pnl (prior) | −$0.015094 (from 5e5f073b stop_loss) |
| bot_status open_positions | [] |
| is_paper_trading | true |
| execution_mode | PAPER ONLY |
| bankroll_tier | T0_MICRO_SEED / MICRO_SURVIVAL |

Note: runtime resets paper cash to `wallet_reference_balance` at startup when `trades_simulated=0` and `realized_pnl≈0` in-memory — so the session started with $20.09901 regardless of the prior session ending balance of $20.083915.

## Decision Summary

120 decisions over 60 minutes (60-second interval).

| Skip Reason | Count | % |
|---|---|---|
| delta_extreme | 45 | 37.5% |
| hard_close_zone | 16 | 13.3% |
| risk_mode_defensive:confidence_below_defensive | 16 | 13.3% |
| micro_adaptive_cutoff | 15 | 12.5% |
| confidence_too_low | 7 | 5.8% |
| clob_empty_response | 7 | 5.8% |
| Max entries per market reached | 6 | 5.0% |
| Risk plan returned zero position size | 3 | 2.5% |
| ev_below_threshold | 3 | 2.5% |
| sell | 2 | 1.7% |

2 of 120 decisions resulted in entries (1.7% entry rate). Both were ETH YES positions.

## Trade Cycles

### Cycle 1 — Position `3fdd7312`

| Event | Timestamp UTC | Price | Detail |
|---|---|---|---|
| trade_open | `2026-06-30T11:00:58Z` | 0.51 | ETH YES, $0.10 notional, 0.196078 shares |
| trade_close | `2026-06-30T11:01:25Z` | 0.42 | stop_loss, hold=27s |

Realized PnL: −$0.017647 | Exposure after: $0.00

### Cycle 2 — Position `78725623`

| Event | Timestamp UTC | Price | Detail |
|---|---|---|---|
| trade_open | `2026-06-30T11:06:00Z` | 0.48 | ETH YES, $0.10 notional, 0.208333 shares |
| trade_close | `2026-06-30T11:06:29Z` | 0.36 | stop_loss, hold=29s |

Realized PnL: −$0.025000 | Exposure after: $0.00

### Session PnL

| Trade | PnL |
|---|---|
| 3fdd7312 (stop_loss) | −$0.017647 |
| 78725623 (stop_loss) | −$0.025000 |
| **Total** | **−$0.042647** |

## Execution Events

| Event | Intent | Count |
|---|---|---|
| order_intent_approved | ENTRY | 2 |
| order_submit_attempt | ENTRY | 2 |
| paper_fill | ENTRY | 2 |
| order_intent_approved | EXIT | 2 |
| order_submit_attempt | EXIT | 2 |
| paper_fill | EXIT | 2 |
| **Total** | — | **12** |

No live execution markers. All events are paper-only.

## Execution Timeline (from 2-minute monitor)

| Time (T+) | Decisions | Fills | Opens | Closes | Cash | Open Pos |
|---|---|---|---|---|---|---|
| T+2min | 6 | 0 | 0 | 0 | $20.09901 | 0 |
| T+16min | 38 | 0 | 0 | 0 | $20.09901 | 0 |
| T+18min | 42 | 1 | 1 | 1 | $20.081363 | 0 |
| T+22min | 46 | 2 | 2 | 2 | $20.056363 | 0 |
| T+26–60min | 50–120 | 2 | 2 | 2 | $20.056363 | 0 |

Cash and positions were fully stable from T+22 to end of run (38 minutes of stable state with 0 open positions and no new fills).

## Risk Mode Behavior

| Mode | Risk Log Rows | % |
|---|---|---|
| DEFENSIVE | 111 | 58.1% |
| NORMAL | 67 | 35.1% |
| (unknown) | 13 | 6.8% |

Timeline:
1. T+0 to T+17min: NORMAL mode — allowed entries
2. T+17min: First stop_loss (3fdd7312) → risk mode shifted to DEFENSIVE
3. T+22min: Brief NORMAL window → second entry (78725623) approved
4. T+22min: Second stop_loss (78725623) → risk mode returned to DEFENSIVE
5. T+22 to T+60min: DEFENSIVE mode — `confidence_below_defensive` blocked all 16 attempted entries

The DEFENSIVE mode activation after consecutive stop-loss hits is correct, expected behavior. The 16 `risk_mode_defensive` skips prevented further entries during a losing streak and a TREND_DOWN regime.

## Reconciliation Checks

| # | Check | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | tracker_open == bot_status_open | 0 | 0 | PASS |
| 2 | trade_open_count == trade_close_count | 2 | 2 | PASS |
| 3 | open_ids == close_ids | {3fdd7312, 78725623} | {3fdd7312, 78725623} | PASS |
| 4 | Cash: wallet_ref − PnL | $20.056363 | $20.056363 | PASS (diff=0.00000036) |
| 5 | Open exposure | 0.0 | 0.0 | PASS |
| 6 | No runtime_owner.json | absent | absent | PASS |
| 7 | Live markers in exec log | 0 | 0 | PASS |

**All 7 reconciliation checks: PASS.**

## Position Tracker Final State

| Field | Value |
|---|---|
| Open positions | 0 |
| Closed positions | 4 (2 prior + 2 this session) |
| daily_realized_pnl | −$0.057741 (all 4 closes today) |
| peak_equity | $20.09901 |
| pos 3fdd7312 | closed, stop_loss, entry=0.51, exit=0.42, pnl=−$0.017647 |
| pos 78725623 | closed, stop_loss, entry=0.48, exit=0.36, pnl=−$0.025000 |

## bot_status.json Final State

| Field | Value | Check |
|---|---|---|
| account_balance | $20.056363 | PASS |
| wallet_reference_balance | $20.09901 | Unchanged |
| open_positions | [] | PASS |
| is_paper_trading | true | PASS |
| execution_mode | PAPER ONLY | PASS |
| bankroll_tier_id | T0_MICRO_SEED | PASS |
| bankroll_mode | MICRO_SURVIVAL | PASS |
| last_update | 18:43:10 (= 11:43:10 UTC) | PASS |

## Live Execution Safety

| Check | Result |
|---|---|
| execution_mode | PAPER ONLY |
| is_paper_trading | true |
| Live order markers in execution_log | 0 |
| Live wallet mutations | None |
| runtime_owner.json leftover | None |

## Issues Found

### Issue 1 — MINOR: `exit_reason=None` in trade_close journal payload (pre-existing)

Both `trade_close` events in `trade_journal/2026-06-30.jsonl` have `exit_reason: None`. The position tracker state correctly records `exit_reason: stop_loss` for both. The gap is in the journal payload builder, not in the underlying close logic. Pre-existing; not introduced by any recent change.

### Issue 2 — MINOR: `paper_virtual_cash=None` in trade_close journal payload (pre-existing)

Same pre-existing gap noted in `POST_FIX_PAPER_CLOSE_STATUS_FRESHNESS_RUNTIME_CONFIRMATION_001`. The correct cash value is visible in `bot_status.json` and derivable from position tracker PnL. Not a blocker.

### Issue 3 — OBSERVATION: All fills were ETH YES stop-losses within 27–29 seconds

Both entries were ETH YES positions that hit stop_loss within 30 seconds at entry prices of 0.51 and 0.48. Market regime during entries was `TREND_DOWN / WEAK_DOWNTREND` per last_signals in bot_status. The stop_loss trigger suggests the exit price dropped rapidly. This is expected regime behavior, not a system defect. Statistical significance requires >>2 positions.

## Runtime Stability Metrics

| Metric | Value |
|---|---|
| Total cycles | 120 |
| Python exceptions in exec log | 0 |
| Unclosed positions at stop | 0 |
| Cash drift from expected | $0.00000036 (float precision only) |
| State corruption | None |
| Log file growth | Normal |

## Repository Status

| Check | Result |
|---|---|
| Code changes made | None |
| Working tree | Clean |
| GitHub branch | main |

## Final Metrics

| Metric | Value |
|---|---|
| FINAL_VERDICT | PASS_WITH_MINOR_ISSUES |
| RUN_ID | `20260630T104339Z_52084_999c4023` |
| DURATION | 60.6 minutes (3636 seconds) |
| FILL_COUNT | 2 |
| TRADE_OPEN_COUNT | 2 |
| TRADE_CLOSE_COUNT | 2 |
| PNL_SUMMARY | Session: −$0.042647 (3fdd7312: −$0.017647, 78725623: −$0.025000). Both stop_loss exits. |
| CASH_EXPOSURE_RECONCILIATION | PASS — cash $20.056363 matches wallet_ref ($20.09901) minus session PnL (−$0.042647); diff=0.00000036; exposure=0.0 |
| POSITION_BOT_STATUS_RECONCILIATION | PASS — tracker=0 open, bot_status=0 open, IDs match, no orphans |
| RISK_MODE_SUMMARY | DEFENSIVE dominant (58.1%). NORMAL allowed 2 entries; DEFENSIVE blocked all further entries after 2 consecutive stop-losses. Expected behavior. |
| LIVE_EXECUTION_SAFETY | SAFE — PAPER ONLY throughout, 0 live markers, no wallet mutations |
| ISSUES_FOUND | MINOR: exit_reason=None in trade_close journal (pre-existing); paper_virtual_cash=None in trade_close journal (pre-existing). No blockers. |
| REPOSITORY_STATUS | CLEAN — no code changes |
| NEXT_TASK | POST_FILL_ACCOUNTING_PIPELINE_REPAIR_001 (fix exit_reason and paper_virtual_cash None in trade journal payloads) |
