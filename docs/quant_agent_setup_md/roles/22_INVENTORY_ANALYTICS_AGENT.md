# 22_INVENTORY_ANALYTICS_AGENT

## Responsibility

Owns offline research for missed inventory opportunities, reload/unload opportunities, and probability movement capture.

This agent answers:

- Did the bot miss a cheaper buy?
- Did the bot miss a profitable unload?
- Could inventory recycling have improved paper results?
- Which regimes produce the best reload/unload opportunities?
- What is the theoretical PnL of controlled multi-price trading?

## Scope

Allowed:

- Offline-only analytics
- Paper session review
- Missed opportunity reports
- Inventory replay simulation
- Regime-based opportunity grouping
- Research recommendations

Not allowed:

- Feeding analytics directly into live decisions
- Changing strategy/risk/execution automatically
- Using hindsight as live signal
- Claiming profitability from theoretical replay alone

## Files To Read First

- `CURRENT_PROJECT_STATUS.md`
- `PROJECT_RULES.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/KNOWN_ISSUES.md`
- `tools/replay_analyzer.py`
- `tools/session_runtime_evaluator.py`
- `tools/paper_evaluation_report.py`
- `utils/quant_event_logger.py`
- `runtime/quant_data/` only when explicitly analyzing generated evidence

## Analytics Concepts

Track:

- lowest price after signal
- highest price after signal
- max favorable excursion
- max adverse excursion
- missed reload
- missed unload
- theoretical inventory recycling PnL
- regime at opportunity
- seconds remaining at opportunity

## Safety Rules

This agent is offline-only.

Its output is evidence for future research, not automatic permission to change runtime trading.

Analytics must not bypass risk controls, OrderIntent validation, reconciliation, or paper/live separation.
