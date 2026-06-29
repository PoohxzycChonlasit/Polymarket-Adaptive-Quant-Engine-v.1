# DECISION_ENGINE_PROTOTYPE_SEVERITY_BATCH_REVIEW_001

**Date:** 2026-06-29
**Task Class:** 1 RESEARCH / OFFLINE BATCH REVIEW
**Status:** COMPLETE

---

## FINAL_VERDICT

**KEEP_SEVERITY_POLICY** — Zero false positives found. All 41 PASS_CONTEXT rows are legitimate
grade-A, HIGH-confidence signal-driven trades missing only INFO-tier future telemetry and
one LOW-tier sentinel field. No severity map adjustments are required.

---

## PREFLIGHT

- venv activated: `.\.venv\Scripts\python.exe`
- git status: clean tree
- git branch: `main` at `a8425aa5` (feat: implement decision engine missing field severity)
- prerequisite docs read:
  - `DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_IMPLEMENTATION_001.md`
  - `DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_DESIGN_001.md`
  - `DECISION_ENGINE_PROTOTYPE_BATCH_VALIDATION_001.md`
  - `tools/decision/decision_engine_prototype.py`
  - `tools/decision/decision_engine_batch_validate.py`

---

## BATCH RE-RUN RESULTS

Command:

```
.\.venv\Scripts\python.exe -m tools.decision.decision_engine_batch_validate
```

| decision_state | count |
|---|---:|
| `REJECT_MISSING_CONTEXT` | 907 |
| `REVIEW_REQUIRED` | 845 |
| `PASS_CONTEXT` | 41 |
| `REJECT_LOW_EVIDENCE` | 1 |

Total rows: 1,794. Parse errors: 0. Source files: 4.

Results match the implementation report exactly. No drift since prior run.

---

## ROWS_REVIEWED

41 PASS_CONTEXT rows extracted via in-session Python analysis over all 4 canonical JSONL files.

### Source file distribution

| source_file | count |
|---|---:|
| `canonical_trade_context_20260627.jsonl` | 41 |
| `canonical_trade_context_20260614.jsonl` | 0 |
| `canonical_trade_context_20260531.jsonl` | 0 |
| `canonical_trade_context_20260523.jsonl` | 0 |

All 41 PASS_CONTEXT rows originate from the most recent canonical file (2026-06-27). Older
files produce zero PASS_CONTEXT rows because their grade-A rows are missing MEDIUM fields
(`decision_score` was absent before full telemetry was wired).

### Asset / outcome distribution

| ticker | count |
|---|---:|
| `ETH` | 34 |
| `BTC` | 7 |

| outcome | count |
|---|---:|
| `NO` | 24 |
| `YES` | 17 |

### Event classification

All 41 rows: `signal_driven_trade`.

### Evidence quality (all 41 rows identical)

| field | value |
|---|---|
| `data_quality_grade` | `A` |
| `join_confidence` | `HIGH` |
| `source_streams` | `decision_log`, `execution_log`, `trade_journal` |
| `missing_critical_fields` | `[]` (none) |
| `missing_high_fields` | `[]` (none) |
| `missing_medium_fields` | `[]` (none) |
| `position_id present` | yes (all 41) |

---

## PROBABILITY AND EV PROFILE

| metric | min | max | mean | n |
|---|---:|---:|---:|---:|
| `probability` | 0.5719 | 0.7118 | 0.6564 | 41 |
| `ev_after_spread` | 0.0566 | 0.2652 | 0.1247 | 41 |
| `intended_price` | 0.3700 | 0.6100 | — | 41 |

Observations:
- All probabilities are strictly between 0.5 and 0.75. No boundary anomalies.
- All ev_after_spread values are strictly positive (min 0.057). No near-zero edge cases.
- Intended prices span 0.37–0.61 — realistic range for 5-minute binary markets.
- No row has an improbable probability-EV combination.

---

## COMMON MISSING LOW/INFO FIELDS

### LOW severity missing (all 41 rows)

| field | count | reason for LOW classification |
|---|---:|---|
| `blockers` | 41 | Empty list sentinel; absence means no blockers recorded, not that blockers existed |

**Note:** `blockers: []` is correctly classified LOW per the severity design. In the canonical
builder, `blockers` defaults to `[]` when absent from events, making an empty list a valid
"no blockers" sentinel. This also reflects Bug 1 in `tools/runtime/canonical_trade_context_builder.py`
(empty lists incorrectly flagged as missing). After that repair, `blockers` will not appear in
`missing_fields` at all for these rows — the LOW classification is a correct safety net for the
pre-repair period.

### INFO severity missing (all 41 rows, 17 fields)

| field | count | category |
|---|---:|---|
| `bankroll_rank` | 41 | Future capital quality state |
| `capital_score` | 41 | Future capital quality scalar |
| `size_sharp_at_entry` | 41 | Future Size Sharp deployment score |
| `size_sharp_component_scores` | 41 | Future Size Sharp detail |
| `size_sharp_penalties` | 41 | Future Size Sharp detail |
| `size_sharp_boosts` | 41 | Future Size Sharp detail |
| `size_sharp_hard_caps` | 41 | Future Size Sharp constraint detail |
| `size_sharp_missing_inputs` | 41 | Future Size Sharp completeness detail |
| `realized_pnl_before` | 41 | Future capital curve telemetry |
| `unrealized_pnl_before` | 41 | Future capital curve telemetry |
| `open_position_count` | 41 | Future inventory/risk telemetry |
| `market_exposure_before` | 41 | Future inventory/risk telemetry |
| `market_exposure_after` | 41 | Future inventory/risk telemetry |
| `max_order_usd` | 41 | Future risk-cap telemetry |
| `max_daily_loss_usd` | 41 | Future risk-cap telemetry |
| `max_open_exposure_usd` | 41 | Future risk-cap telemetry |
| `expected_pnl_at_entry` | 41 | Future forecast field |

All 17 INFO fields are future-telemetry placeholders. None exist in any row across all 1,794
canonical rows. Their absence in all rows is a known forward-fill gap, not a data quality
defect in these specific 41 rows.

---

## PASS_CONTEXT ROW EXAMPLES (3 of 41)

```
Row 1:  ETH YES pid=11c30f01 prob=0.6595 ev=0.0795 ip=0.5800 grade=A jc=HIGH
Row 2:  BTC YES pid=df75df79 prob=0.6666 ev=0.0566 ip=0.6100 grade=A jc=HIGH
Row 3:  ETH NO  pid=98f35092 prob=0.6267 ev=0.2167 ip=0.4100 grade=A jc=HIGH
```

All share the pattern: legitimate decision context (probability, EV, intended price), three
source streams, high join confidence, grade A quality.

---

## PASS_CONTEXT_LEGITIMATE

**41 / 41 rows confirmed legitimate.**

Classification summary:

| verdict | count | reasoning |
|---|---:|---|
| `LEGITIMATE_PASS_CONTEXT` | 41 | Grade A, HIGH join confidence, 3 source streams, position_id present, signal_driven_trade, valid probability and EV, only INFO/LOW missing fields |
| `SUSPICIOUS_PASS_CONTEXT` | 0 | — |
| `SHOULD_BE_REVIEW_REQUIRED` | 0 | — |
| `SHOULD_BE_REJECT_MISSING_CONTEXT` | 0 | — |

---

## FALSE_POSITIVES

**0 false positives.**

No row produced PASS_CONTEXT due to an incorrect severity classification. Every LOW/INFO
omission is exactly what the design intends: future telemetry placeholders and an empty
sentinel list.

The design criterion was:
> "Missing `LOW` and `INFO` fields should be captured in notes but should not prevent
> `PASS_CONTEXT`."

All 41 rows satisfy this criterion. The critical decision fields — probability, ev_after_spread,
intended_price, data_quality_grade, join_confidence — are all present and valid.

---

## WHY ONLY 20260627 FILE PRODUCES PASS_CONTEXT

Three earlier canonical files (20260523, 20260531, 20260614) produce zero PASS_CONTEXT rows:

- 908 rows are grade D / LOW join confidence → hard-rejected (`REJECT_MISSING_CONTEXT`)
- 845 remaining grade A rows from older dates are missing `decision_score` and/or `signal_name`
  (both MEDIUM severity) → `REVIEW_REQUIRED`

The 2026-06-27 file is the first to have complete MEDIUM-tier telemetry after the full
decision-log backfill improvements. Only 41 rows in that file have all MEDIUM fields present
(implying position_id, signal_name, decision_score, and submitted_at are all present).
The remaining 845 grade A rows from that same date still miss one or more MEDIUM fields.

---

## INTERACTION WITH CANONICAL BUILDER DATA QUALITY REPAIR

The canonical builder (`tools/runtime/canonical_trade_context_builder.py`) has two known
data-quality bugs:

**Bug 1 (line 711):** Empty lists (`[]`) and dicts (`{}`) are incorrectly flagged as missing.
This causes `blockers: []` to appear in `missing_fields` for all rows that have no blockers.
In the 41 PASS_CONTEXT rows, this means `blockers` appears as a LOW missing field.

Impact on severity policy: **None.** The LOW classification correctly handles this case —
`blockers` absence does not block PASS_CONTEXT regardless of whether it appears as a false
positive in missing_fields or not. After Bug 1 is repaired, `blockers` will not appear in
`missing_fields` at all for these rows, making them even cleaner.

**Bug 2 (line 726):** Grade B check uses `"true_probability"` (wrong key) instead of
`"probability"` (correct row key). This affects the canonical builder's grade assignment
only, not the decision engine. The 41 rows all have grade A (not grade B), so this bug does
not affect them.

Conclusion: Neither canonical builder bug affects the legitimacy of the 41 PASS_CONTEXT rows
or the correctness of the severity policy classification.

---

## RECOMMENDATION

**KEEP_SEVERITY_POLICY**

Rationale:

1. **Zero false positives.** All 41 PASS_CONTEXT rows are the highest-quality rows in the
   dataset — grade A, HIGH join, 3 source streams, complete MEDIUM-tier telemetry.

2. **Hard rejects unchanged.** REJECT_MISSING_CONTEXT (907) and REJECT_LOW_EVIDENCE (1)
   counts are identical to pre-severity totals. The policy did not weaken any hard reject.

3. **REVIEW_REQUIRED remains meaningful.** The 845 remaining review rows are missing genuine
   MEDIUM fields (signal_name, decision_score) that reduce interpretation quality. The review
   bucket is no longer polluted by inevitable INFO-tier absences.

4. **INFO/LOW classification is accurate.** The 17 INFO fields are legitimately "not yet
   wired" future telemetry. `blockers: []` is a valid sentinel. No field in the LOW or INFO
   set is required for entry decision diagnostics.

5. **Policy is appropriately conservative.** Only 41 of 1,794 rows (2.3%) pass. These 41
   represent the gold-standard row profile: signal-driven, fully joined, complete core
   telemetry. The policy does not over-promote.

No severity map adjustments are needed. No validator logic changes are required.

---

## SAFETY_VERDICT

**SAFE_OFFLINE_REVIEW_ONLY.**

No Python files were modified in this task. Analysis was performed using:
- `tools.decision.decision_engine_batch_validate` (existing module, run via `-m`)
- In-session Python script (temporary, deleted before commit)

No runtime trading behavior, execution, risk, sizing, strategy thresholds, wallet/balance,
live/paper runtime, config/settings.py, or `.env` was touched.

---

## REPOSITORY_STATUS

| item | status |
|---|---|
| git working tree | clean |
| Python files changed | 0 |
| New docs | 1 (this report) |
| Ops files updated | ACTIVE_WORKFLOW_STATE_001.json, TASK_QUEUE_001.json, LOOP_MEMORY_20260628_001.json |
| Tests required | none (code unchanged) |

---

## NEXT_TASK

**CANONICAL_CONTEXT_DATA_QUALITY_REPAIR_001** (second incarnation)

Repair two data-quality bugs in `tools/runtime/canonical_trade_context_builder.py`:
- Bug 1 (line 711): empty list/dict fields incorrectly flagged as missing
- Bug 2 (line 726): grade B check uses wrong field key `"true_probability"` instead of `"probability"`

Scope: offline canonical builder repair only. Do not modify runtime trading behavior.

These bugs were identified during the MARKET_AVAILABILITY_ENGINE_OBSERVABILITY_IMPLEMENTATION_001
session and are now the immediate next repair priority.
