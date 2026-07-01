# 07 Runtime Scoreboard

## Purpose

The runtime scoreboard is the operator's first truth surface for the Profit Engine.

It should answer:

- Are we making money?
- If not, why not?
- Is the system protecting capital or missing valid opportunities?
- Is the market data fresh and market-time accurate?
- Is paper execution realistic enough to trust?

## Scoreboard Sections

### Profit Engine Header

- Mode.
- Live status.
- Bankroll.
- Equity.
- Daily PnL.
- Session PnL.
- Open positions.
- Risk mode.
- Current bottleneck.

### Trade Funnel

- Decisions.
- Tradable markets.
- Candidates.
- EV pass.
- Risk approved.
- Order intents.
- Orders sent.
- Fills.
- Closes.
- Net PnL.

### Gate Blocker Board

- Blocker counts.
- Protective or over-conservative label.
- Would-be EV if available.
- MFE/MAE evidence if available.
- Near-miss count.

### Quant Metrics

- Expectancy.
- Profit factor.
- Win rate.
- Average win.
- Average loss.
- Max drawdown.
- MFE.
- MAE.
- TP count.
- SL count.
- Average hold time.

### Market Reality / Sizing Reality

- Tick size.
- Minimum order.
- Fee assumption.
- Taker delay.
- Spread.
- Liquidity.
- Fillability.
- Current sizing mode.
- Paper realism warning.

### Time Truth / Data Freshness

- Data age.
- Orderbook freshness.
- Clock drift.
- Seconds to expiry.
- Source timestamps.
- Stale-data warning.

### Operator Action Panel

- Current bottleneck.
- Next action.
- Do-not-do list.
- Evidence status.

## Scoreboard Validity Rule

Scoreboard metrics are not profitability evidence unless time truth, cash/exposure/PnL reconciliation, and execution realism are present.

## Latest Audit Snapshot

`CANONICAL_RUN_EVIDENCE_SUMMARY_BUILDER_001` now generates per-run evidence summaries under `docs/reports/run_evidence/`.

- Trade funnel evidence exists as `trade_funnel_summary_v1`.
- Gate blocker counts are available and useful.
- Market/sizing reality is partial because fractional-share and minimum-order live behavior are not proven.
- Time-truth evidence is partial because current logs have timing proxies, but not all canonical field names from `11_LOGGING_AND_MARKET_TIME_TRUTH.md`.
- Current data is valid for blocker diagnosis and paper accounting, not for a profitability claim.

## Canonical Evidence Requirement

Before the scoreboard is treated as a profit surface, it must consume a per-run evidence summary with:

- `trade_funnel_summary_v1`
- `market_time_truth_field_map_v1`
- `dashboard_data_availability_v1`
- `evidence_validity_v1`

Those summaries are now available offline, but dashboard values remain operational diagnostics until time truth, sizing realism, costs, and settlement truth are complete.

## Latest Blocker Attribution Audit

`BOOK_WARMING_ROOT_CAUSE_AND_MARKET_LIFECYCLE_AUDIT_001` found that the recent `book_warming` top blocker in canonical summaries was not the raw runtime blocker. Raw decision rows for the inspected runs showed `skip_reason=risk_off` and `raw_skip_reason=risk_mode_lockdown:hard_drawdown`; `book_warming` came from additive no-entry classifier fields.

Scoreboard rule: show raw runtime blocker and classified root cause separately. Classified labels are diagnostic context, not proof that the runtime gate with the same name blocked entry.

`CANONICAL_SUMMARY_RAW_VS_CLASSIFIED_BLOCKER_REPORTING_001` implements this rule in generated canonical summaries. Scoreboards should prefer `primary_runtime_blocker` for current bottleneck and show `primary_classifier_blocker` as diagnostic context when `raw_vs_classified_blocker_conflict=true`.

`NO_ENTRY_CLASSIFIER_RISK_OFF_LABEL_REPAIR_001` repairs future no-entry classifier output so `risk_off`, `risk_mode_lockdown`, `hard_drawdown`, and runtime safety gate rows classify as risk before lifecycle `book_warming` fallback. Scoreboards should still preserve historical raw-vs-classified conflicts for old emitted logs.
