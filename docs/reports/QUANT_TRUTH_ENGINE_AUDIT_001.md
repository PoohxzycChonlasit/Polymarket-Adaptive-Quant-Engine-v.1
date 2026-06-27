# QUANT_TRUTH_ENGINE_AUDIT_001 - Report

> Generated: 2026-06-28
> Full audit: docs/audits/QUANT_TRUTH_ENGINE_AUDIT_001.md

---

## Summary

Performed a complete read-only audit of the JSONL event stream, replay tools, and backtest tools
to determine readiness for the Quant Truth Engine.

## Key Findings

### Data Assets
- 51 calendar days of JSONL data (2026-05-08 to 2026-06-27)
- ~28.6 GB across 8 subdirectories
- 797 trade_open events; 1,469 real trade_close events (non-test, with PnL)
- Paper win rate: 62.9% | Gross PnL: +$347.43

### Critical Gap
**trade_close is missing key entry-time context fields:**
- true_probability / fair_value / EV not carried to close
- bankroll_tier_id / risk_mode not present at close
- lifecycle_phase = UNKNOWN in most close events

This makes cross-analysis (e.g., EV accuracy vs actual outcome, tier-based PnL grouping) require
fragile cross-stream joins. Some legacy closes lack the paper_trade_replay_key join field entirely.

### Metrics Ready Now
- Win rate, expectancy, profit factor: READY (simple aggregation from trade_close)
- Max drawdown, Sharpe, Sortino: PARTIAL (need equity curve reconstruction)
- EV accuracy, Kelly estimate: PARTIAL (join required)
- Slippage, adverse selection, opportunity cost: NOT READY

## Next Task Recommendation

**TELEMETRY_BACKFILL_FOR_QUANT_TRUTH_001** (Class 5 - OBSERVABILITY)

Carry forward 10 entry-time fields into trade_close payloads in trader.py.
This is the minimum viable fix before Bankroll Rank and Size Sharp can be built on solid data.
No strategy, sizing, or risk logic changes are required for this task.
