# Canonical Trade Context v1 Report

> **TASK_CLASS: 2 — DESIGN / ARCHITECTURE**
> **Date: 2026-06-28 | Evidence Grade: B (source-code verified) + D (docs aligned)**

---

## 1. Summary

Designed the **Canonical Trade Context v1** schema to establish a single, unified trade-level representation across all analysis, replay, backtesting, and future adaptive sizing engines.

## 2. Key Details

### Data Reality & Joins
- Real trade records exist across `trade_journal/` (797 opens, 2,148 closes, 1,469 matched PnL pairs).
- `trade_close` events are currently missing critical entry-time context (EV, probability, sizer tier, risk mode).
- Joining them today is complex and legacy data has missing or incomplete keys.

### Schema Design (Flat Dictionary Structure)
- **Identity**: trade_id (sha1 unique digest), position_id, market_id, asset_id, ticker, market_slug, outcome, side, source_event_ids, replay_key.
- **Entry Decision**: signal_name, probability, fair_value, ev, ev_after_spread, decision_score, reason_codes, blockers, market_state, lifecycle_phase, seconds_remaining, quote_age_ms.
- **Execution**: intended_price, intended_size, intended_notional, order_type, order_id, submitted_at, fill_status, filled_size, fill_price, slippage, timeout_status.
- **Capital/Risk**: bankroll, equity, realized_pnl_before, unrealized_pnl_before, bankroll_tier_id, bankroll_rank, risk_mode, risk_budget, max_order_usd, max_daily_loss_usd, max_open_exposure_usd, current_exposure, target_exposure.
- **Inventory**: inventory_state, open_position_count, market_exposure_before, market_exposure_after, position_lifecycle_state.
- **Exit/Outcome**: exit_reason, exit_price, exit_timestamp, hold_seconds, realized_pnl, expected_pnl_at_entry, pnl_pct, trade_result, resolved_outcome.
- **Replay/Backtest**: replay_version, data_quality_grade, missing_fields, source_streams, join_confidence, counterfactual_available.

### Required Runtime Backfill
1. Carry-forward 10 key entry-time fields within `Position` metadata at entry-time.
2. Emit those carry-forward fields directly in the `trade_close` payload, making closes self-contained.

---

## 3. Recommended Next Task

**`CANONICAL_TRADE_CONTEXT_OFFLINE_BUILDER_001`**

By building the offline builder first, we can test and validate this schema against the 28.6 GB historical log repository without modifying live runtime code, ensuring zero-risk verification.
