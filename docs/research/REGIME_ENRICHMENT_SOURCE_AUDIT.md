# Regime Enrichment Source Audit

Date: 2026-06-07

Scope: READ ONLY / research source audit

Tool context:

- `tools/eth_yes_fc_os_command_center.py`
- `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md`
- `docs/research/COMMAND_CENTER_OPERATIONAL_READINESS.md`

Verdict: `DECISION_LOG_AUTHORITATIVE__FRESH_CANONICAL_EXPORT_RECOMMENDED`

## Executive Summary

The cleanest authoritative source for regime labels is `decision_log`, specifically `payload.market_regime` on decision events.

The cleanest operational source for the command center should be a fresh enriched canonical export that joins:

```text
trade_journal canonical opportunity truth
  + decision_log market_regime
```

The current raw `trade_journal` path correctly reproduces canonical `n=61`, but it has no regime fields. The current completed-trades CSV has regime labels, but it is stale and not identity-safe enough to be the canonical count source by itself.

## Evidence Summary

### Current Command-Center Problem

Raw trade-journal mode:

| Metric | Status |
|---|---|
| Canonical n | Correct |
| WR/PF | Correct |
| Velocity | Correct |
| Regime sequence | Degraded |
| nc_PF | Degraded |

Observed generated report:

```text
Last-5 regime sequence: UNKNOWN -> UNKNOWN -> UNKNOWN -> UNKNOWN -> UNKNOWN
Regime mix: UNKNOWN:61
```

### Source Field Coverage

| Source | Regime fields observed? | Notes |
|---|---|---|
| `trade_journal` | No | Recent sampled payloads had no `regime` or `market_regime` fields |
| `execution_log` | No | Recent sampled payloads had lifecycle/candidate identity but no regime fields |
| `decision_log` | Yes | `payload.market_regime`, `payload.trend_regime`, `payload.volatility_regime`, `payload.regime_reason` |
| `completed_trades_v1_2.csv` | Yes | Has `regime` column, but current export is stale and lacks `candidate_id` |
| replay/report outputs | Derived | Useful for historical context, not authoritative source of fresh daily truth |

## Source Audit

## 1. decision_log

Status: `AUTHORITATIVE_REGIME_SOURCE`

Recent schema evidence from `runtime/quant_data/decision_log/2026-06-07.jsonl`:

| Field | Present |
|---|---|
| `payload.market_regime` | Yes |
| `payload.trend_regime` | Yes |
| `payload.volatility_regime` | Yes |
| `payload.regime_reason` | Yes |
| `payload.asset` | Yes |
| `payload.side` / `payload.outcome` | Yes |
| `payload.lifecycle_phase` | Yes |
| `payload.paper_trade_replay_key` | Yes |
| `payload.candidate_id` | Yes |

Jun 6 canonical W23 trade check:

| Source | candidate | regime | lifecycle |
|---|---|---|---|
| decision_log | `candidate_9ed8765c0bc1` | SIDEWAY | OPENING_SCAN then ACTIVE_INVENTORY_TRADING |
| execution_log | same candidate | missing | OPENING_SCAN |
| trade_journal | same candidate | missing | OPENING_SCAN / UNKNOWN close |

Interpretation:

- `decision_log` is the regime producer.
- It has the correct identity keys to enrich trade rows.
- It is fresh through the current runtime date.
- It is large, so full historical scans are operationally expensive.

Recommended join key:

```text
run_id + paper_trade_replay_key
```

Secondary tie-breakers:

```text
candidate_id
lifecycle_phase contains OPENING_SCAN
decision timestamp nearest trade_open timestamp
```

Preferred regime row:

1. matching `run_id + paper_trade_replay_key + candidate_id`
2. `lifecycle_phase == OPENING_SCAN`
3. nearest decision timestamp at or before/near trade_open
4. fallback to earliest matching decision for the trade key

## 2. execution_log

Status: `NOT_A_REGIME_SOURCE`

Recent sampled execution-log payloads contain:

- asset
- side/outcome
- lifecycle_phase
- candidate_id
- paper_trade_replay_key

But they do not contain:

- `market_regime`
- `regime`
- `trend_regime`
- `volatility_regime`

Last-five-file scan result:

```text
execution_log regime_events = 0
regime fields = none
```

Interpretation:

- Execution logs are useful for identity, lifecycle, quote age, and fill observability.
- They are not useful for regime enrichment today.
- Joining through execution_log would add complexity without solving the missing regime problem.

## 3. completed_trades CSV / canonical exports

Status: `CONVENIENT_BUT_STALE_AND_IDENTITY_LIMITED`

Current files:

| File | Rows | Regime column | candidate_id column | LastWriteTime |
|---|---:|---|---|---|
| `completed_trades_v1.csv` | 440 | Yes | No | 2026-06-05 |
| `completed_trades_v1_1.csv` | 440 | Yes | No | 2026-06-05 |
| `completed_trades_v1_2.csv` | 440 | Yes | No | 2026-06-05 |

Current `completed_trades_v1_2.csv` ETH YES FC OS filter:

| Metric | Value |
|---|---:|
| Filtered rows | 61 |
| Regime coverage | 61 / 61 |
| Unique replay keys | 60 |
| Unique `(run_id, replay_key)` | 61 |
| Candidate ID coverage | 0 / 61 |
| Latest qualifying entry | 2026-05-31 |

Regime distribution in current CSV:

| Regime | Count |
|---|---:|
| COMPRESSION | 21 |
| TREND_DOWN | 19 |
| SIDEWAY | 14 |
| TREND_UP | 7 |

Critical caveat:

The CSV row count appears to match `n=61`, but it is not the locked canonical `n=61` set:

- it stops at 2026-05-31
- it does not include the 2026-06-06 W23 SIDEWAY TP canonical trade
- it contains a duplicate replay key
- it lacks `candidate_id`

Interpretation:

- Current CSV is excellent for historical regime context through May 31.
- It is unsafe as the command center's canonical count source.
- It is safe only if freshly regenerated and reconciled against the canonical logical key.

## 4. replay outputs / runtime reports

Status: `DERIVED_REFERENCE_ONLY`

Replay and research reports contain regime conclusions and historical summaries, but they are not the right daily enrichment source.

Reasons:

- reports are derived artifacts
- refresh cadence is not guaranteed
- they may encode prior assumptions or stale filters
- they do not provide the most direct row-level regime join

Use replay/report outputs for:

- sanity checks
- historical interpretation
- governor narrative

Do not use them as the authoritative command-center regime source.

## Approach Comparison

## A. Join trade_journal -> decision_log

Description:

Start from raw trade-journal canonical opportunities, then enrich each trade with `decision_log.payload.market_regime`.

| Dimension | Rating | Notes |
|---|---|---|
| Correctness | High | Uses canonical trade truth and authoritative regime producer |
| Reproducibility | High if join rules are explicit | Needs deterministic tie-breaker for multiple decisions per candidate |
| Maintenance burden | Medium | Join logic must handle large files and multiple decision rows |
| Runtime cost | Medium to High | Full decision-log scan is expensive; target-key/date-limited scan is acceptable |
| Freshness | High | Uses raw current JSONL |

Best implementation shape:

```text
1. Build canonical trade keys from trade_journal.
2. Extract target dates and target replay/candidate keys.
3. Stream only relevant decision_log date files.
4. Match by run_id + paper_trade_replay_key + candidate_id.
5. Prefer OPENING_SCAN decision row nearest trade_open.
```

Verdict: `BEST_AUTHORITATIVE_JOIN_PATH`

## B. Join trade_journal -> execution_log

Description:

Start from raw trade-journal canonical opportunities and attempt to enrich regime from execution events.

| Dimension | Rating | Notes |
|---|---|---|
| Correctness | Low | Execution logs do not currently carry regime fields |
| Reproducibility | Medium for identity, low for regime | It can join trades, but not supply regime |
| Maintenance burden | Medium | Adds a join without solving the field gap |
| Runtime cost | Low | Execution logs are much smaller than decision logs |
| Freshness | High | Current files exist |

Verdict: `NOT_RECOMMENDED_FOR_REGIME`

Use execution_log only as a supporting source for:

- quote age
- fill lifecycle
- submit/fill truth
- execution continuity

## C. Use enriched canonical CSV

Description:

Use `runtime/research_exports/completed_trades_v1_2.csv` as the command-center source.

| Dimension | Rating | Notes |
|---|---|---|
| Correctness | Medium if stale, high if fresh and reconciled | Current CSV has regime labels but stale population |
| Reproducibility | Medium | Current export lacks `candidate_id`, making the canonical key incomplete |
| Maintenance burden | Low | Simple and fast consumer path |
| Runtime cost | Very low | CSV read is fast |
| Freshness | Currently low | Current export was last written 2026-06-05 |

Verdict: `GOOD_CONSUMER_FORMAT_BUT_NOT_CURRENTLY_AUTHORITATIVE`

This is the best daily-report input only after a fresh export step is performed and verified against raw canonical count.

## D. Generate new canonical export first

Description:

Before command-center generation, run or produce a fresh canonical export that joins raw trade truth to decision-log regime labels.

| Dimension | Rating | Notes |
|---|---|---|
| Correctness | Highest if export uses canonical key | Combines authoritative trade truth and authoritative regime truth |
| Reproducibility | Highest | Snapshot artifact can be archived and re-read |
| Maintenance burden | Medium | Requires a reliable export build step |
| Runtime cost | Medium once per day | Avoids repeated ad hoc decision-log scans by every report |
| Freshness | High if run daily | Export timestamp makes staleness visible |

Verdict: `BEST_OPERATIONAL_ARCHITECTURE`

The generated export must include:

```text
condition_id
epoch_start_ts
asset
side
candidate_id
run_id
paper_trade_replay_key
entry_ts
trade_result
pnl_usdc
canonical_entry_lifecycle_phase
market_regime
trend_regime
volatility_regime
regime_source = decision_log
regime_join_key
regime_join_confidence
```

## Ranking

| Rank | Approach | Correctness | Reproducibility | Maintenance | Cost | Overall |
|---:|---|---|---|---|---|---|
| 1 | D. Generate fresh canonical export first | Highest | Highest | Medium | Medium | Best operational path |
| 2 | A. Join trade_journal -> decision_log inside command center | High | High | Medium | Medium/High | Best direct source path |
| 3 | C. Use enriched canonical CSV | Medium today / High if fresh | Medium today / High if fixed | Low | Low | Best consumer format, unsafe stale |
| 4 | B. Join trade_journal -> execution_log | Low | Low for regime | Medium | Low | Not a regime solution |

## Recommended Design

Use a two-layer model:

### Layer 1: Canonical Evidence Build

Authoritative build step:

```text
raw trade_journal canonical opportunities
  + decision_log market_regime enrichment
  -> fresh canonical export
```

This layer owns:

- canonical count
- duplicate removal
- outcome truth
- regime enrichment
- source timestamps
- join confidence

### Layer 2: Command Center Consumer

Command center reads the fresh canonical export and renders:

- n
- WR
- PF
- nc_PF
- velocity
- regime sequence
- promotion gates
- kill monitors

This keeps the command center simple and fast while preserving reproducibility.

## Required Guardrails

Any future regime-enriched export must:

1. Preserve the locked canonical opportunity key:

```text
condition_id | epoch_start_ts | asset | side | candidate_id
```

2. Label regime source explicitly:

```text
regime_source = decision_log.payload.market_regime
```

3. Preserve missing-regime states:

```text
market_regime = UNKNOWN
regime_join_confidence = MISSING
```

4. Refuse silent fallback to stale CSV if raw n and export n disagree.

5. Display export freshness in the command center.

6. Keep outputs report-only and offline-only.

## Final Answer

Authoritative regime source:

```text
decision_log.payload.market_regime
```

Best immediate enrichment path:

```text
trade_journal -> decision_log
```

Best operational architecture:

```text
generate fresh canonical regime-enriched export first,
then let the command center consume that export
```

Do not use execution_log for regime enrichment. Do not trust the current completed-trades CSV as canonical without regeneration and reconciliation.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No
