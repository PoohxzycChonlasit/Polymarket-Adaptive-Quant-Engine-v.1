# BOOK_WARMING_ROOT_CAUSE_AND_MARKET_LIFECYCLE_AUDIT_001

## Verdict

`book_warming` did not directly block the cited CLOB-compliant paper runs. [A]

The raw decision rows for the three inspected run IDs show `skip_reason=risk_off` and `raw_skip_reason=risk_mode_lockdown:hard_drawdown` on every decision row. [A] The `book_warming` value appears as `skip_reason_primary` and `timing_block_reason` after the additive no-entry root-cause classifier enriches the decision payload. [B]

Root cause classification:

`CLASSIFIER_ATTRIBUTION_FALSE_POSITIVE_OVER_RUNTIME_RISK_OFF`

This is not evidence that the Polymarket Crypto 5M orderbook warmup can never clear. It is evidence that the current no-entry classifier can mislabel risk-off lockdown rows as `book_warming` when `normalized_skip_reason=risk_off` is not classified as risk and lifecycle evidence contains `executable_book_state=NONZERO_BOOK`. [A][B]

## Files Read

| File | Purpose | Evidence |
|---|---|---|
| `C:\Users\poh_2\.codex\attachments\18c97dce-81ae-485e-871d-b5fae3da4f57\pasted-text.txt` | Task scope and Tech Lead authorization | A |
| `docs/reports/CLOB_COMPLIANT_EXTENDED_PAPER_EVIDENCE_RUN_001.md` | Recent extended paper evidence summary | D |
| `docs/reports/CLOB_COMPLIANT_PAPER_EVIDENCE_SMOKE_001.md` | Recent smoke evidence summary | D |
| `docs/reports/run_evidence/20260701T075916Z_45556_5818ec95_canonical_evidence_summary.json` | Phase B canonical summary | A |
| `docs/reports/run_evidence/20260701T075106Z_54212_3734c20c_canonical_evidence_summary.json` | Phase A canonical summary | A |
| `runtime/quant_data/decision_log/2026-07-01.jsonl` | Raw decision rows for run IDs | A |
| `runtime/quant_data/system_health/2026-07-01.jsonl` | Lifecycle and health evidence | A |
| `runtime/event_stream/runtime_events_2026-07-01_001.jsonl` | Runtime event stream confirmation | A |
| `tools/canonical_run_evidence_summary_builder.py` | Top no-trade reason selection | B |
| `utils/no_entry_root_cause_classifier.py` | `book_warming` source label and classifier rules | B |
| `polymarket/observability/trader_decision_diagnostics.py` | Runtime diagnostic enrichment call site | B |
| `polymarket/trader.py` | Runtime orderbook warmup and skip reason source paths | B |
| `polymarket/client.py` | `OrderbookSnapshot` timestamp and age path | B |
| `polymarket/observability/trader_lifecycle_observability.py` | `_obs_orderbook_age_ms` implementation | B |
| `07_RUNTIME_SCOREBOARD.md` | Existing scoreboard interpretation | D |
| `08_MINI_EVIDENCE_PIPELINE.md` | Evidence pipeline guidance | D |
| `11_LOGGING_AND_MARKET_TIME_TRUTH.md` | Time truth standard | D |

Note: the task named `polymarket/no_entry_root_cause_classifier.py` and `polymarket/no_entry_diagnostics.py`; those files were not present. The actual classifier files are `utils/no_entry_root_cause_classifier.py` and `utils/no_entry_diagnostics.py`. [B]

## Source Paths

| Concern | Source path | Finding |
|---|---|---|
| `book_warming` label | `utils/no_entry_root_cause_classifier.py` | `_TIMING_KEYWORDS` maps `book_warming`, `empty_book`, `orderbook_unavailable`, `warmup`, CLOB error strings, and `preload` to `book_warming`; lifecycle refinement can also produce `book_warming` for `BOOK_SEEN` or `NONZERO_BOOK`. [B] |
| Runtime classifier call | `polymarket/observability/trader_decision_diagnostics.py` | `_decision_diagnostics_payload` imports `classify_no_entry_root_cause` and adds fields if absent. [B] |
| Runtime orderbook warmup | `polymarket/trader.py::_classify_orderbook_readiness_reason` | Runtime returns `warmup_pending`, not `book_warming`, when early empty/invalid orderbook state has no prior successful orderbook age. [B] |
| Orderbook age | `polymarket/observability/trader_lifecycle_observability.py::orderbook_age_ms` | Converts `snapshot.age_seconds` to milliseconds. [B] |
| CLOB timestamp parsing | `polymarket/client.py::PolymarketClient.get_orderbook` | Parses `timestamp`, `ts`, `updated_at`, or `updatedAt` if present; rejects stale snapshots over 3 seconds when a source timestamp exists. [B] |

## Runtime Or Classifier Status

Classification:

`CLASSIFIER_LABEL_IN_RUNTIME_OBSERVABILITY_NOT_DIRECT_RUNTIME_BLOCKER`

Explanation:

- Runtime decision rows used `skip_reason=risk_off`. [A]
- Runtime decision rows used `raw_skip_reason=risk_mode_lockdown:hard_drawdown`. [A]
- The no-entry classifier added `skip_reason_primary=book_warming` and `timing_block_reason=book_warming`. [A][B]
- Canonical evidence summary counts top no-trade reasons from `skip_reason_primary` before `normalized_skip_reason` or `skip_reason`, so it surfaced `book_warming` instead of `risk_off`. [A][B]

The requested categories do not perfectly fit because this classifier runs during runtime observability enrichment, not only offline. The operational truth is: the value is a classifier label, not the decision blocker that prevented entries. [B]

## Exact Trigger Condition

Observed trigger in the cited runs:

1. Runtime creates a skipped decision with `normalized_skip_reason=risk_off`, `skip_reason=risk_off`, and `raw_skip_reason=risk_mode_lockdown:hard_drawdown`. [A]
2. The no-entry classifier checks `_RISK_KEYWORDS`, but `risk_off` is not in the risk keyword table. [B]
3. With no category assigned from the reason string, the classifier evaluates lifecycle evidence. [B]
4. `executable_book_state=NONZERO_BOOK` is in `_TIMING_READINESS_STATES`. [A][B]
5. For `NONZERO_BOOK`, lifecycle refinement assigns `lifecycle_primary=book_warming`, then `category=timing`, `primary=book_warming`, `confidence=0.6`. [B]
6. `tools/canonical_run_evidence_summary_builder.py` ranks no-trade reasons using `skip_reason_primary` before `normalized_skip_reason` and `skip_reason`, so the canonical summary reports `book_warming` as the top reason. [B]

Runtime orderbook warmup trigger, separate from the observed false attribution:

1. Token IDs missing or mapping warning returns token-related readiness reasons. [B]
2. CLOB category errors return their category. [B]
3. Stale orderbook errors return `stale_book`. [B]
4. Empty/invalid orderbook errors or zero ask prices check `_last_orderbook_age_ms[ticker.upper()]`. [B]
5. If there is no successful prior age and `_orderbook_warmup_pending_counts[ticker.upper()] <= orderbook_warmup_pending_threshold`, runtime returns `warmup_pending`. [B]
6. Default threshold is read from `orderbook_warmup_pending_threshold` with fallback `3`. [B]
7. After the threshold, the same empty/invalid condition returns `empty_book`. [B]

## Orderbook Age And Freshness Path

Source path:

```text
PolymarketClient.get_orderbook(token_id)
-> OrderbookSnapshot.timestamp_ms / age_seconds
-> PolymarketTrader._orderbook_age_ms(snapshot)
-> polymarket.observability.trader_lifecycle_observability.orderbook_age_ms(snapshot)
-> decision payload / lineage / canonical data_age_ms alias
```

Findings:

- `OrderbookSnapshot` has `timestamp_ms` and `age_seconds` fields. [B]
- `get_orderbook` parses raw `timestamp`, `ts`, `updated_at`, or `updatedAt` fields when present. [B]
- If a parsed source timestamp exists and age is greater than 3 seconds, `get_orderbook` raises a stale orderbook error. [B]
- If no source timestamp exists, `timestamp_ms=0` and `age_seconds=0.0`; this makes `orderbook_age_ms=0`, which is indistinguishable from perfectly fresh local capture unless separate source timestamp fields are present. [B]
- In the inspected decision rows, `quote_capture_ts` / `quote_capture_ts_utc` were present, but `source_orderbook_ts_utc` was absent and `orderbook_age_ms` was 0. [A]
- The cited runs had `executable_book_state=NONZERO_BOOK` on all decision rows, so lifecycle evidence did not show empty or warming books. [A]

## Warmup Duration Or Sample Requirement

Runtime orderbook warmup is sample-count based in the inspected code, not a fixed time duration. [B]

The default runtime pending threshold is 3 readiness classifications per ticker when no successful orderbook age has been recorded. [B] The returned runtime string is `warmup_pending`, not `book_warming`. [B]

This threshold did not explain the recent `46/46 book_warming` canonical summary because the raw decisions did not use `warmup_pending` or `orderbook_unavailable`; they used `risk_off` with `raw_skip_reason=risk_mode_lockdown:hard_drawdown`. [A]

## Market Lifecycle Compatibility

For the inspected runs, market lifecycle was not the first failing blocker. [A]

| Run ID | Decision rows | Unique BTC/ETH slugs | Raw blocker | Classifier primary | Executable book state |
|---|---:|---:|---|---|---|
| `20260701T072001Z_35052_048b6e8d` | 16 | 4 | `risk_mode_lockdown:hard_drawdown` | `book_warming` | `NONZERO_BOOK` on 16/16 |
| `20260701T075106Z_54212_3734c20c` | 16 | 4 | `risk_mode_lockdown:hard_drawdown` | `book_warming` | `NONZERO_BOOK` on 16/16 |
| `20260701T075916Z_45556_5818ec95` | 46 | 12 | `risk_mode_lockdown:hard_drawdown` | `book_warming` | `NONZERO_BOOK` on 46/46 |

Phase B covered 12 unique BTC/ETH 5-minute slugs over 22.31 minutes. [A] The rows showed seconds-since-open values from 28 to 273 and seconds remaining from 27 to 272. [A] Those values prove market rollover was represented, but they do not prove orderbook warmup failure because the raw blocker was risk lockdown. [A]

Compatibility conclusion:

- A runtime `warmup_pending` policy based on 3 samples per ticker could be compatible with 5-minute markets if polling occurs more than three times per asset per window. [E]
- The current evidence cannot validate or invalidate that compatibility because the inspected run was stopped by hard-drawdown risk-off before model/risk approval could progress. [A]
- The `book_warming` summary count should not be used as market lifecycle evidence until classifier attribution is corrected or reports include both raw and classified blockers side by side. [B]

## Recent Run Log Evidence

| Evidence item | Phase A | Phase B | Smoke | Evidence |
|---|---:|---:|---:|---|
| Run ID | `20260701T075106Z_54212_3734c20c` | `20260701T075916Z_45556_5818ec95` | `20260701T072001Z_35052_048b6e8d` | A |
| Decision rows inspected | 16 | 46 | 16 | A |
| Raw `skip_reason` | `risk_off` 16/16 | `risk_off` 46/46 | `risk_off` 16/16 | A |
| Raw `raw_skip_reason` | `risk_mode_lockdown:hard_drawdown` 16/16 | `risk_mode_lockdown:hard_drawdown` 46/46 | `risk_mode_lockdown:hard_drawdown` 16/16 | A |
| `skip_reason_primary` | `book_warming` 16/16 | `book_warming` 46/46 | `book_warming` 16/16 | A |
| `timing_block_reason` | `book_warming` 16/16 | `book_warming` 46/46 | `book_warming` 16/16 | A |
| `model_activation_block_group` | `RUNTIME_SAFETY_GATE` 16/16 | `RUNTIME_SAFETY_GATE` 46/46 | `RUNTIME_SAFETY_GATE` 16/16 | A |
| `model_not_run_reason` | `risk_off` 16/16 | `risk_off` 46/46 | `risk_off` 16/16 | A |
| `executable_book_state` | `NONZERO_BOOK` 16/16 | `NONZERO_BOOK` 46/46 | `NONZERO_BOOK` 16/16 | A |
| `source_orderbook_ts_utc` | absent | absent | absent | A |
| `quote_capture_ts_utc` | present | present | present | A |

## Longer Run Justification

A longer run is not justified for the purpose of clearing `book_warming` based on this evidence. [A]

Reason:

- The observed `book_warming` is not the runtime blocker. [A][B]
- The observed runtime blocker is `risk_mode_lockdown:hard_drawdown`. [A]
- A 2-6 hour run under the same risk-off state would likely continue to produce skipped decisions before executable evidence is collected. [E]

A longer run may be justified only after Tech Lead review authorizes one of these narrower evidence goals:

- Verify paper account/risk state is actually normal before launch. [E]
- Emit or report raw blocker and classifier blocker side by side. [E]
- Run a bounded paper session with stop conditions for `risk_mode=NORMAL`, `warmup_pending` count, `empty_book` count, and first EV-evaluable decision. [E]

## No Behavior Change Proof

This task made no runtime, strategy, risk, sizing, execution, config, or `.env` changes. [A]

Files changed were limited to docs and ops:

- `docs/reports/BOOK_WARMING_ROOT_CAUSE_AND_MARKET_LIFECYCLE_AUDIT_001.md`
- `04_CURRENT_PROJECT_STATUS.md`
- `07_RUNTIME_SCOREBOARD.md`
- `08_MINI_EVIDENCE_PIPELINE.md`
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- `docs/operations/loop_memory/LOOP_MEMORY_20260701_001.json`

## Remaining Uncertainty

- The underlying hard-drawdown state for the cited CLOB-compliant runs was observed in the rows but not repaired in this task. [A]
- The runtime `warmup_pending` policy was source-audited but not separately exercised in a fresh `risk_mode=NORMAL` paper session. [B]
- `source_orderbook_ts_utc` is absent in the inspected rows; `quote_capture_ts_utc` exists as a local/runtime capture timestamp. [A]
- The canonical summary builder currently surfaces `skip_reason_primary` first; this is useful for classifier-led diagnostics, but misleading when the classifier primary conflicts with raw runtime skip reason. [B]

## Tech Lead Review Candidates

Candidate tasks only; no automatic next task is authorized.

1. `NO_ENTRY_CLASSIFIER_RISK_OFF_LABEL_REPAIR_001`
   - Scope: observability classifier/tests only.
   - Goal: classify `risk_off`, `risk_mode_lockdown`, and `hard_drawdown` as risk/safety blockers before lifecycle fallback.

2. `CANONICAL_SUMMARY_RAW_VS_CLASSIFIED_BLOCKER_REPORTING_001`
   - Scope: offline summary/reporting only.
   - Goal: report raw runtime blocker and classifier primary side by side so summaries cannot hide runtime safety gates.

3. `PAPER_RISK_STATE_PREFLIGHT_BEFORE_EVIDENCE_RUN_001`
   - Scope: validation only.
   - Goal: prove `risk_mode=NORMAL`, drawdown, paper balance, and owner state before any bounded paper evidence run.

4. `ORDERBOOK_WARMUP_POLICY_RISK_NORMAL_RUNTIME_DIAGNOSTIC_001`
   - Scope: diagnostic only.
   - Goal: only after risk state is normal, measure actual `warmup_pending`, `empty_book`, and `NONZERO_BOOK` lifecycle transitions across 5-minute rollovers.
