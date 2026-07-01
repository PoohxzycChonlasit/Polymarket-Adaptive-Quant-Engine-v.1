# 04 Current Project Status

## Status Date

2026-07-01

## Current Mission

The repository is being reset around the Profit Engine mission:

Paper profit first. Micro live only after evidence.

## Current Truth

- Paper runtime has recently proven startup, fill path, trade open, trade close, PnL accounting, cash return, exposure clearing, and bot status freshness in bounded validations.
- A 60-minute paper baseline produced two complete stop-loss cycles and negative session PnL.
- A later 60-minute TP-evidence run produced zero entries, so no take-profit sample was observed.
- Entry blocker analysis showed the strongest design question is `risk_plan_zero` side-confidence semantics.
- Entry throughput and market-realism audit now confirms current evidence is valid for blocker diagnosis and paper accounting, but not valid for a profit claim or live sizing realism.
- Canonical evidence and market-time truth review now defines the per-run funnel, alias map, evidence-validity classes, and dashboard availability needed before more replay/tuning work.
- Offline canonical run evidence summary builder now emits per-run `trade_funnel_summary_v1`, market-time truth maps, dashboard availability, and conservative evidence validity JSON under `docs/reports/run_evidence/`.
- `BOOK_WARMING_ROOT_CAUSE_AND_MARKET_LIFECYCLE_AUDIT_001` found recent CLOB-compliant runs were not directly blocked by orderbook warmup. Raw decisions were `risk_off` / `risk_mode_lockdown:hard_drawdown`; `book_warming` was an additive classifier label over `NONZERO_BOOK` lifecycle evidence.
- `CANONICAL_SUMMARY_RAW_VS_CLASSIFIED_BLOCKER_REPORTING_001` updates canonical summaries to show raw runtime blockers and classified no-entry labels side by side, with conflict counts and examples.
- `NO_ENTRY_CLASSIFIER_RISK_OFF_LABEL_REPAIR_001` repairs the additive no-entry classifier so `risk_off`, `risk_mode_lockdown`, `hard_drawdown`, and runtime safety gate evidence classify as risk before lifecycle `book_warming` fallback.
- `ORDER_MANAGER_CONFIDENCE_MAPPING_BUG_FIX_001` resolves a structural block where underdog predictions (win rate < 0.54) were automatically rejected by the risk engine because `win_rate` was conflated with `confidence_score`.
- `CANONICAL_PAPER_OPEN_COUNT_RECONCILIATION_001` reconciles CLOB-cleared paper-fill counts versus actual paper-open truth. Use `actual_position_opened_count`, not legacy `paper_opened_after_clob_constraints_count`, for lifecycle open counts.
- Shadow strategy framework work exists, but the mission reset freezes further framework expansion unless it directly supports profit evidence.

## Current Blockers

| Blocker | Status | Why It Matters |
|---|---|---|
| Positive expectancy | Not proven | No profitability claim is allowed. |
| Entry throughput | Insufficient in some runs | Zero-entry sessions cannot produce TP/PnL evidence. |
| Take-profit exits | Not observed in latest TP evidence run | Cannot design winning-position ladder from absent winning samples. |
| Market-realistic sizing | Needs explicit validation | Paper fractional sizing may not match live CLOB mechanics. |
| Time truth | Needs strict governance | Profit evidence is invalid if timing is ambiguous. |
| Market/live sizing realism | Not proven | Current paper opens can use `$0.10` fractional shares; live CLOB fractional/minimum-order behavior is unresolved. |
| Canonical evidence summary | Implemented offline | Future replay and dashboard work can consume generated per-run evidence summaries instead of re-deriving aliases ad hoc. |
| Paper open count attribution | Reconciled in canonical summary | CLOB-cleared fills and actual opened positions are now separate; latest run had 4 CLOB-valid fills but 2 actual opens. |
| No-entry blocker attribution | Classifier repaired; future runtime evidence needed | Canonical summaries show raw and classified blockers side by side, and the classifier now maps risk-off rows to risk labels before lifecycle fallback. Historical JSONL still preserves old emitted labels. |
| Live execution | Not validated | Micro live remains blocked. |

## Active Safety Position

- Runtime behavior unchanged by governance reset.
- Strategy/risk/sizing/execution thresholds unchanged.
- Live behavior unchanged.
- Paper remains the default validation path.

## Current Next Priority

Tech Lead review is required before any next task. Candidate review topics: event-stream JSONL integrity audit and CLOB-compliant bounded paper evidence run after the confidence mapping fix.
