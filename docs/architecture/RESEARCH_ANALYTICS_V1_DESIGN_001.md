# RESEARCH_ANALYTICS_V1_DESIGN_001

Date: 2026-06-23
Mode: DESIGN ONLY
Context commit: `fbe69ab22b6b4104bbc798c00c1f9310d91fd5e9`

## Role Routing

- Primary role: `08_RESEARCH_QUANT_AGENT.md`
- Supporting roles: `10_BACKTEST_REPLAY_AGENT.md`, `11_OBSERVABILITY_INCIDENT_AGENT.md`
- Why selected: Research Analytics V1 is an evidence interpretation surface built from replay, no-entry, session, data-quality, and research export artifacts.
- Files inspected: `MASTER_AGENT_ROUTER.md`, `runtime/research_state/latest_research_state.md`, research governance registries, report/export directories, analyzer CLIs, and `tools/dashboard_state_aggregator.py`.
- Files intentionally ignored: strategy modules, risk sizing, order execution, wallet/live config, and raw multi-day JSONL beyond compact report schema discovery.

## 1. Research Page Goals

The `/research` page should become the operator's read-only evidence terminal. Its job is not to recommend trades or tune thresholds. Its job is to answer, quickly:

- What did the latest replay say?
- Why were candidates skipped or blocked?
- Is the no-entry diagnosis data-driven or evidence-poor?
- Is the current evidence good enough to trust for research interpretation?
- Which replay or observability gaps are still blocking stronger conclusions?
- Are regime exports present and fresh enough to support later regime analytics?

The page should preserve the active research guardrail from `docs/research/ACTIVE_QUESTION.md`: current research remains constrained by `LOW_PRICE_TRUTH_RESOLUTION_001`, so dashboard copy must label these widgets as evidence summaries, not edge approval.

## 2. Data Sources And Report Files

### Primary Sources

| Source | Producer | Current Use |
|---|---|---|
| `runtime/research_state/latest_research_state.md` | research memory workflow | Compact research state, blind spots, latest run, guardrails. |
| `runtime/reports/replay_report_*.json` | `tools/replay_analyzer.py` | Replay Summary, skip reasons, trade/PnL summary, lifecycle confidence, timing/liquidity readiness. |
| `runtime/reports/no_entry_report_*.json` | `tools/no_entry_analyzer.py` | No Entry Root Cause, skip attribution, market-data quality, recommendations. |
| `runtime/reports/session_runtime_evaluation_*.json` | `tools/session_runtime_evaluator.py` | Session Analysis, bottlenecks, timing quality, phase2 readiness. |
| `runtime/reports/quant_data_quality_*.json` | `tools/quant_data_quality.py` | Data Quality, malformed/invalid fields, replay continuity, category counts. |
| `runtime/reports/edge_inventory_report_v1.json` | `tools/edge_inventory_report.py` | Optional trade attribution context and signal evidence summary. |
| `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json` | regime export pipeline | Regime Placeholder freshness, row count, join rate, validation status. |
| `runtime/research_exports/canonical_regime_enriched_trades_v1_summary.md` | regime export pipeline | Human-readable regime export note, optional link/display snippet later. |

### Existing Dashboard State Coverage

`tools/dashboard_state_aggregator.py` already exposes:

- `phase_b.latest_replay_report`
- `phase_b.latest_no_entry_report`
- `phase_b.edge_inventory`
- `phase_b.canonical_regime_export`
- `phase_b.candidate_funnel_today`

This is enough for a placeholder page, but not enough for the requested V1 widgets. V1 should add a normalized `research_analytics` section rather than forcing React components to parse raw analyzer shapes.

## 3. Dashboard Widgets

### Replay Summary

Purpose: show latest replay health and outcome without requiring the operator to open JSON.

Fields:

- report path
- date range
- run id, if present
- events loaded
- total trades
- wins / losses
- win rate
- gross PnL
- average PnL
- approved decisions
- rejected decisions
- risk reject count
- lifecycle replay confidence
- phase2 coverage status
- missed starter candidate count
- top skip reasons

Display:

- compact metric cards for trades, win rate, PnL, lifecycle confidence
- small table for top skip reasons
- warning badge if `bad_json_lines > 0` or lifecycle confidence is low

### No Entry Root Cause

Purpose: make no-entry sessions legible in one glance.

Fields:

- report path
- date
- total scanned / entered / skipped
- root cause category
- root cause counts
- root cause details
- top skip reasons
- orderbook unavailable or stale count
- confidence / EV / delta / risk / cutoff counts
- recommendations

Display:

- root cause badge
- bottleneck table sorted by count
- recommendation list labeled as diagnostic guidance only

### Skip Reason Attribution

Purpose: connect skip reasons to evidence quality and candidate funnel symptoms.

Fields:

- replay `top_skip_reasons`
- no-entry `skip_reason_counts`
- no-entry `skip_percentages`
- no-entry `average_confidence_by_skip_reason`
- no-entry `average_ev_by_skip_reason`
- current-day `phase_b.candidate_funnel_today.skip_reason_counts`

Display:

- chart: top skip reasons by count
- table: reason, count, percentage, avg confidence, avg EV, source
- source badge: `current_day`, `latest_replay`, `latest_no_entry`

Rule:

- If multiple sources disagree, show all source counts rather than merging silently.

### Signal Funnel Diagnostics

Purpose: answer why entries are low without implying a strategy change.

Fields:

- current-day decision count
- skip reason counts
- asset counts
- signal name counts
- latest decisions
- replay approved decisions
- replay rejected decisions
- replay risk reject count
- no-entry total entered / skipped

Derived display-only rates:

- skip rate
- approval rate
- entry rate
- risk rejection share, when denominator exists

Display:

```text
Decisions -> Signal/Decision Approved -> Risk Passed -> Entries/Trade Opens
```

All percentages must include denominators.

### Session Analysis

Purpose: show latest session runtime evaluation when available and fall back gracefully when absent.

Fields:

- session status
- primary bottleneck
- secondary bottleneck
- scanned / entered / skipped
- top skip reasons
- timing quality
- market data quality
- inventory replay readiness
- recommendations
- source availability flags

Fallback:

- If no `session_runtime_evaluation_*.json` exists, show `NO_SESSION_EVALUATION_REPORT` and populate only replay/no-entry context.

### Regime Placeholder

Purpose: provide a safe landing area for regime analytics without overstating readiness.

Fields:

- canonical regime export status
- canonical row count
- regime join rate
- unknown regime rate
- freshness status
- latest trade close timestamp
- latest decision timestamp scanned

Display:

- "Regime Analytics: Evidence Export Ready / Partial / Missing"
- no regime edge chart in V1 unless aggregated regime summaries are added to dashboard state

Explicit guardrail:

- Do not infer regime profitability from this widget in V1.

### Data Quality

Purpose: tell the operator whether research evidence should be trusted.

Fields:

- latest quality report path
- ok / fail
- files scanned
- lines scanned
- valid events
- bad JSON lines
- missing required fields
- invalid timestamps
- invalid event types
- invalid modes
- invalid numeric fields
- empty files
- unreadable files
- replay continuity status
- research log integrity status
- phase2 coverage status

Display:

- top-level PASS/CAUTION/FAIL badge
- issue table with counts
- replay continuity warning if `trustworthy_for_replay=false`

## 4. Required `dashboard_state.json` Additions

Add one top-level read-only section:

```json
{
  "research_analytics": {
    "schema_version": "research_analytics.v1",
    "generated_at_utc": "2026-06-23T00:00:00Z",
    "source_status": "OK|PARTIAL|MISSING|ERROR",
    "active_question": {},
    "research_state": {},
    "replay_summary": {},
    "no_entry_root_cause": {},
    "skip_reason_attribution": {},
    "signal_funnel_diagnostics": {},
    "session_analysis": {},
    "regime_placeholder": {},
    "data_quality": {},
    "alerts": []
  }
}
```

### Suggested Field Shape

`active_question`:

- `question_id`
- `status`
- `next_gate`
- `blocking`
- `allowed_work`

`research_state`:

- `generated_at`
- `latest_run_id`
- `latest_replay_confidence`
- `current_blind_spots`
- `recommended_next_step`
- `runtime_evidence_status`

`replay_summary`:

- `report_path`
- `date_from`
- `date_to`
- `run_id`
- `events_loaded`
- `total_trades`
- `wins`
- `losses`
- `win_rate`
- `gross_pnl`
- `average_pnl`
- `approved_decisions`
- `rejected_decisions`
- `risk_reject_count`
- `lifecycle_replay_confidence`
- `phase2_coverage_status`
- `missed_starter_candidate_count`
- `top_skip_reasons`
- `bad_json_lines`

`no_entry_root_cause`:

- `report_path`
- `date`
- `total_scanned`
- `total_entered`
- `total_skipped`
- `root_cause_category`
- `root_cause_counts`
- `root_cause_details`
- `top_skip_reasons`
- `recommendations`
- `market_data_quality`

`skip_reason_attribution`:

- `sources`
- `rows`: reason, source, count, percentage, avg_confidence, avg_ev

`signal_funnel_diagnostics`:

- `decision_count`
- `approved_decisions`
- `rejected_decisions`
- `risk_reject_count`
- `entry_count`
- `skip_reason_counts`
- `asset_counts`
- `signal_name_counts`
- `rates`

`session_analysis`:

- `report_path`
- `status`
- `primary_bottleneck`
- `secondary_bottleneck`
- `timing_quality`
- `inventory_replay_readiness`
- `recommendations`
- `source_availability`

`regime_placeholder`:

- `meta_path`
- `status`
- `canonical_n`
- `regime_join_rate`
- `unknown_regime_rate`
- `freshness_status`
- `latest_decision_ts_scanned`
- `latest_trade_close_ts`

`data_quality`:

- `report_path`
- `ok`
- `files_scanned`
- `lines_scanned`
- `valid_events`
- `bad_json_lines`
- `missing_required_fields`
- `invalid_timestamps`
- `invalid_event_types`
- `invalid_modes`
- `invalid_numeric_fields`
- `empty_files`
- `unreadable_files`
- `replay_continuity_status`
- `trustworthy_for_replay`
- `research_log_integrity_status`
- `phase2_coverage_status`

## 5. API Design

No new API endpoint is required for V1.

Use the existing endpoint:

```text
GET /api/dashboard/state
```

Reason:

- The dashboard already polls this endpoint.
- Research widgets are small summaries, not raw report payloads.
- A single state payload keeps the frontend simple and read-only.

Future API only if needed:

```text
GET /api/dashboard/research/report/{report_type}
```

This should be deferred unless the UI needs drill-down into large report details. V1 should not expose raw multi-megabyte JSON or CSV through the dashboard API.

## 6. Read-Only Safety Boundaries

Research Analytics V1 must not:

- start analyzers automatically
- run replay automatically
- change strategy
- change EV
- change risk
- change sizing
- change execution
- write to runtime trading logs
- edit `.env`
- infer live readiness
- mark edge as real from sample-poor evidence
- promote thresholds or signals

Allowed behavior:

- Read existing reports and exports.
- Read compact research state.
- Add normalized summary fields to `runtime/dashboard_state.json`.
- Render read-only React widgets.
- Fail soft with `source_status=PARTIAL` and alerts when reports are missing.

## 7. Implementation Phases

### Phase 1 - Aggregator State Expansion

Modify `tools/dashboard_state_aggregator.py` only.

Add parsers for:

- latest `replay_report_*.json`
- latest `no_entry_report_*.json`
- latest `session_runtime_evaluation_*.json`
- latest `quant_data_quality_*.json`
- `runtime/research_state/latest_research_state.md`
- `docs/research/ACTIVE_QUESTION.md`
- `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json`

Output:

- `research_analytics` section in `runtime/dashboard_state.json`

### Phase 2 - Frontend Research Page

Modify dashboard frontend only.

Replace static research placeholders with:

- Replay Summary panel
- No Entry Root Cause panel
- Skip Reason Attribution chart/table
- Signal Funnel Diagnostics panel
- Session Analysis panel
- Regime Placeholder panel
- Data Quality panel

Use existing `/api/dashboard/state` polling and existing read-only layout.

### Phase 3 - Optional Report Drilldown

Only if Phase 1 and Phase 2 become too cramped:

- Add a small read-only report detail endpoint or lazy-loaded frontend modal.
- Keep large raw reports off the default dashboard payload.

This phase is optional and should not be part of V1 unless the operator asks for drilldown.

## 8. Tests Required

### Aggregator Tests

Add or update `tests/test_dashboard_state_aggregator.py`:

- missing research reports returns `source_status=PARTIAL`
- latest replay report maps to `research_analytics.replay_summary`
- latest no-entry report maps to `research_analytics.no_entry_root_cause`
- latest session evaluation maps to `research_analytics.session_analysis`
- latest quality report maps to `research_analytics.data_quality`
- active question markdown maps to `research_analytics.active_question`
- compact research state maps blind spots and recommended next step
- skip reason attribution preserves source labels
- malformed report JSON creates alert and does not break state generation
- no raw large report arrays are copied into dashboard state

### API Tests

Existing dashboard API tests should remain valid:

- state endpoint returns new `research_analytics` section
- missing state behavior unchanged
- invalid JSON behavior unchanged

No new API tests are needed unless a new endpoint is added later.

### Frontend Tests

Add or update dashboard tests:

- `/research` renders Replay Summary
- `/research` renders No Entry Root Cause
- `/research` renders Skip Reason Attribution
- `/research` renders Signal Funnel Diagnostics
- `/research` renders Session Analysis fallback when report missing
- `/research` renders Regime Placeholder
- `/research` renders Data Quality
- partial/missing source warnings render clearly
- read-only banner remains visible

### Validation Commands

Suggested implementation validation:

```powershell
python -m py_compile tools/dashboard_state_aggregator.py api/dashboard_api.py
python -m pytest tests/test_dashboard_state_aggregator.py tests/test_dashboard_api.py -q
cd dashboard
npm run test:run
npm run build
cd ..
git diff --check
```

## Future Options

OPTION 1 - SAFE EV PRESERVATION:
Implement only normalized dashboard-state summaries and static Research page widgets. No analyzer execution, no drilldown API, no raw report payloads. This is the recommended V1 path.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:
Add report drilldown panels and optional links to raw report snippets. This improves exploration but risks bloating the dashboard state and should wait until V1 summary widgets are proven useful.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:
Create a dedicated research report index service and schema registry. This is cleaner long-term but too much structure for the first dashboard Research page.

## Final Recommendation

Implement Research Analytics V1 separately from any analyzer changes.

Recommended scope:

1. Extend `dashboard_state.json` with `research_analytics`.
2. Render read-only `/research` widgets from that state.
3. Keep all analyzers offline and manually run.
4. Do not introduce a new API endpoint in V1.
5. Do not make strategy, EV, risk, sizing, or execution recommendations from the widgets.

## Final Verdict

READY_FOR_RESEARCH_ANALYTICS_V1_IMPLEMENTATION

## Final Confirmation

Runtime changed: No
Strategy changed: No
EV changed: No
Risk changed: No
Execution changed: No
API changed: No
Commit: No
Push: No
