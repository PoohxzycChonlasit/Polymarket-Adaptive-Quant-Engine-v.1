# 09h10h Truth Layer Inventory Audit

Date: 2026-05-24

Scope: read-only docs and evidence audit for whether current logs can support 09h10h early failure / survivor replay.

Runtime behavior changed: No  
Live behavior changed: No

## Goal

Determine whether current logs contain enough truth fields to support:

1. early failure detection;
2. checkpoint replay;
3. survivor hold replay;
4. runner replay;
5. MFE/MAE truth;
6. quote freshness truth;
7. spread/liquidity truth;
8. executable reality.

This audit does not implement an analyzer, replay job, runtime policy, stop-loss change, risk change, or live behavior.

## Sources

- `docs/research/session_edge/session_09h10h_early_failure_replay_test_plan.md`
- `docs/research/session_edge/session_09h10h_structural_edge.md`
- `docs/research/executable_truth/dynamic_executable_expectancy_audit.md`
- `runtime/quant_data/trade_journal/2026-05-19.jsonl`
- `runtime/quant_data/trade_journal/2026-05-20.jsonl`
- `runtime/quant_data/trade_journal/2026-05-21.jsonl`
- `runtime/quant_data/trade_journal/2026-05-22.jsonl`
- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-19.jsonl`
- `runtime/quant_data/execution_log/2026-05-20.jsonl`
- `runtime/quant_data/execution_log/2026-05-21.jsonl`
- `runtime/quant_data/execution_log/2026-05-22.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`
- `runtime/quant_data/decision_log/2026-05-19.jsonl`
- `runtime/quant_data/decision_log/2026-05-20.jsonl`
- `runtime/quant_data/decision_log/2026-05-21.jsonl`
- `runtime/quant_data/decision_log/2026-05-22.jsonl`
- `runtime/quant_data/decision_log/2026-05-23.jsonl`

Target population:

```text
09h10h + 0.50 <= entry_price < 0.70
2026-05-19 through 2026-05-23
matched by (run_id, paper_trade_replay_key)
```

Target count:

```text
27 trades
15 TP / 12 SL
6 trades held 30s+
```

## Summary Verdict

Current logs are enough for baseline signal analysis and post-hoc early-failure labeling, but not enough for trusted checkpoint replay, survivor replay, runner replay, or MFE/MAE truth.

| Capability | Status | Why |
|---|---|---|
| early failure detection | `PARTIAL` | `hold_seconds`, `trade_result`, and exit reason are present, but no path checkpoints prove adverse state before the stop. |
| checkpoint replay | `MISSING` | no +15s, +30s, +45s, +60s price checkpoints are serialized. |
| survivor hold replay | `PARTIAL` | 30s+ survivors can be identified by hold time, but favorable state at 30s is not proven. |
| runner replay | `MISSING` | no runner exit truth, no path marks, no bounded runner PnL truth. |
| MFE/MAE truth | `MISSING` | fields exist but are entry-price placeholders / zero peaks, not realized path extrema. |
| quote freshness truth | `PARTIAL` | quote age fields exist on only part of the target bucket. |
| spread/liquidity truth | `PARTIAL` | liquidity states/depth exist; numeric spread is missing. |
| executable reality | `PARTIAL` | shares/notional exist and prove dust-zone status, but no executable trades exist. |

Blocking conclusion:

```text
Replay implementation is blocked by missing path truth, not by missing entry/exit truth.
```

## ENTRY Truth

Target bucket coverage:

| Field | Coverage | Status | Notes |
|---|---:|---|---|
| entry timestamp | `27/27` | `PARTIAL` | present, but mixed sources include fill/order/receipt timestamps; older rows may not be clean UTC. |
| entry price | `27/27` | `READY` | sufficient for price bucket and baseline replay. |
| quote age | `12/27` | `PARTIAL` | combined quote age available for less than half. |
| `quote_stale_ms` | `8/27` | `PARTIAL` | direct Phase 6 field exists only on newer rows. |
| `quote_age_at_submit_ms` | `12/27` | `PARTIAL` | useful but below replay quality gate. |
| `quote_age_at_fill_ms` | `12/27` | `PARTIAL` | useful but below replay quality gate. |
| `quote_lineage_id` | `14/27` | `PARTIAL` | lineage exists on about half. |
| `quote_source` | `14/27` | `PARTIAL` | source exists on about half. |
| numeric spread | `0/27` | `MISSING` | spread state exists, numeric spread does not. |
| `executable_spread_state` | `27/27` | `PARTIAL` | all `NORMALIZED`, but not costed. |
| `executable_book_state` | `27/27` | `READY` | all `TRADABLE`. |
| liquidity state | `27/27` | `READY` | mostly `THIN`, plus `ACCEPTABLE`/`UNSTABLE`. |
| top ask depth | `27/27` | `READY` | entry depth available. |
| top bid depth | `27/27` | `READY` | entry depth available. |
| lifecycle phase | `27/27` | `READY` | OPENING / ACTIVE available. |
| session/hour | `27/27` | `READY` | hour can be derived from timestamp. |
| seconds remaining | `27/27` | `READY` | available for entry timing. |
| shares / size | `27/27` | `READY` | supports dust-zone classification. |
| notional | `27/27` | `READY` | paper notional available. |

ENTRY verdict:

```text
PARTIAL
```

Entry is usable for baseline signal replay and population filtering. It is not sufficient for executable microstructure replay because numeric spread and full quote freshness are incomplete.

## PATH Truth

Required path checkpoints:

```text
+15s
+30s
+45s
+60s
event_end
```

Current coverage:

| Field / Truth | Coverage | Status | Notes |
|---|---:|---|---|
| +15s price checkpoint | `0/27` | `MISSING` | not serialized per trade. |
| +30s price checkpoint | `0/27` | `MISSING` | core blocker for survivor replay. |
| +45s price checkpoint | `0/27` | `MISSING` | not serialized. |
| +60s price checkpoint | `0/27` | `MISSING` | not serialized. |
| event-end mark | `0/27` | `MISSING` | no settlement/event-end path truth attached. |
| MAE price | `27/27` field present | `MISSING` | values match entry in sampled rows; not real adverse path extrema. |
| MFE price | `27/27` field present | `MISSING` | values match entry in sampled rows; not real favorable path extrema. |
| adverse excursion timing | `0/27` | `MISSING` | no timestamp for adverse move. |
| favorable excursion timing | `0/27` | `MISSING` | no timestamp for favorable move. |
| candidate peak favorable | `27/27` field present | `MISSING` | sampled values are `0.0`; not path truth. |
| candidate peak adverse | `27/27` field present | `MISSING` | sampled values are `0.0`; not path truth. |

PATH verdict:

```text
MISSING
```

This is the main blocker. Current logs can say a trade closed at 8s or 42s, but they cannot prove the trade's state at exactly 15s or 30s.

## EXIT Truth

Target bucket coverage:

| Field | Coverage | Status | Notes |
|---|---:|---|---|
| exit timestamp | `27/27` | `READY` | available for close event. |
| exit price | `27/27` | `READY` | supports baseline PnL explanation. |
| exit reason | `27/27` | `READY` | reason distribution available. |
| TP truth | `15/27` | `READY` | TP classified from result/reason. |
| SL truth | `12/27` | `READY` | SL classified from result/reason. |
| event settle | `0/27` | `MISSING` | no settlement truth attached to these rows. |
| forced exit | `0/27` observed | `PARTIAL` | no forced exits observed; field/reason coverage is indirect. |
| runner exit | `0/27` observed | `MISSING` | no runner lifecycle exists in current evidence. |

Exit reason distribution:

| Reason | Count |
|---|---:|
| `take_profit_target_reached` | `15` |
| `stop_loss` | `10` |
| `stop_loss_hit` | `2` |

EXIT verdict:

```text
READY for baseline TP/SL
MISSING for settlement / runner replay
```

## Capability Classification

### 1. Early Failure Detection

Status:

```text
PARTIAL
```

Supported today:

- `hold_seconds`;
- `trade_result`;
- exit reason;
- entry price;
- exit price;
- entry/exit timestamps.

Not supported today:

- checkpoint state at 15s or 30s;
- adverse excursion timing;
- quote freshness for all rows;
- actual mark trajectory before exit.

Interpretation:

Current logs can label observed early SL after the fact. They cannot prove that an earlier cut would have been valid before the existing stop fired.

### 2. Checkpoint Replay

Status:

```text
MISSING
```

Required but absent:

- mark at +15s;
- mark at +30s;
- mark at +45s;
- mark at +60s;
- side-aware favorable/adverse state at each checkpoint;
- quote/spread state at each checkpoint.

Interpretation:

This prevents trusted replay implementation today.

### 3. Survivor Hold Replay

Status:

```text
PARTIAL
```

Supported today:

- identify trades with `hold_seconds >= 30`;
- compare their final TP/SL;
- compute baseline signal PnL.

Not supported today:

- prove the survivor was favorable or non-adverse at 30s;
- simulate hold from 30s using checkpoint truth;
- separate good survivor from lucky delayed mark.

Interpretation:

Current evidence supports a survivor hypothesis, not a replayable survivor policy.

### 4. Runner Replay

Status:

```text
MISSING
```

Required but absent:

- post-30s path marks;
- runner exit rule truth;
- profit-management states;
- partial reduce / runner PnL fields;
- time-cap exit truth.

Interpretation:

Runner replay cannot be trusted from current logs. Any runner result would be inference-heavy.

### 5. MFE/MAE Truth

Status:

```text
MISSING
```

Observed:

- `mfe_candidate_price` present on `27/27`;
- `mae_candidate_price` present on `27/27`;
- `candidate_peak_favorable` present on `27/27`;
- `candidate_peak_adverse` present on `27/27`.

Problem:

Sampled MFE/MAE prices match entry prices and peak values are `0.0`. These fields are not mature path extrema for this replay need.

Interpretation:

Field presence is not truth. MFE/MAE cannot support early failure or runner replay yet.

### 6. Quote Freshness Truth

Status:

```text
PARTIAL
```

Observed:

| Field | Coverage |
|---|---:|
| quote age combined | `12/27` |
| `quote_stale_ms` | `8/27` |
| `quote_age_at_submit_ms` | `12/27` |
| `quote_age_at_fill_ms` | `12/27` |
| `quote_lineage_id` | `14/27` |
| `quote_source` | `14/27` |

Interpretation:

Quote freshness is useful for newer rows but below the `>=80%` coverage gate. It can be reported as a sensitivity dimension, not trusted as a full replay condition.

### 7. Spread / Liquidity Truth

Status:

```text
PARTIAL
```

Ready:

- `executable_book_state`: `27/27`, all `TRADABLE`;
- `executable_spread_state`: `27/27`, all `NORMALIZED`;
- `liquidity_depth_state`: `27/27`;
- top ask depth: `27/27`;
- top bid depth: `27/27`;
- market/orderbook readiness state available.

Missing:

- numeric spread at entry;
- numeric spread at +15s/+30s;
- depth and spread at checkpoints;
- actual spread cost in PnL.

Interpretation:

Liquidity state is good enough for baseline classification. It is not enough for costed microstructure replay.

### 8. Executable Reality

Status:

```text
PARTIAL
```

Ready:

- shares/size available: `27/27`;
- notional available: `27/27`;
- entry price available: `27/27`;
- dust-zone classification can be made.

Result:

```text
executable trades = 0
current target bucket = SIGNAL_MODE / SIMULATION_ONLY
```

Interpretation:

Current logs can prove the evidence is not executable. They cannot produce executable expectancy because no row clears even the loose executable overlay.

## READY / PARTIAL / MISSING Inventory

| Layer | Status | Replay Use |
|---|---|---|
| target population filter | `READY` | can identify 09h10h + 0.50-0.70 rows |
| baseline TP/SL | `READY` | can compute current signal ledger |
| baseline signal PnL | `READY` | can compute expectancy and profit factor |
| entry timing | `PARTIAL` | enough for hour/session; source quality mixed |
| lifecycle phase | `READY` | OPENING vs ACTIVE usable |
| time remaining | `READY` | entry timing usable |
| quote freshness | `PARTIAL` | below coverage gate |
| numeric spread | `MISSING` | no costed spread replay |
| liquidity/depth at entry | `READY` | entry state usable |
| liquidity/depth at checkpoints | `MISSING` | no checkpoint microstructure replay |
| MFE/MAE path truth | `MISSING` | fields are placeholders, not path truth |
| +15s checkpoint | `MISSING` | cannot test 15s cut |
| +30s checkpoint | `MISSING` | cannot test survivor rule |
| +45s checkpoint | `MISSING` | cannot test runner path |
| +60s checkpoint | `MISSING` | cannot test runner path |
| event-end / settlement | `MISSING` | no settlement replay truth |
| forced exit truth | `PARTIAL` | no observed forced exits; reason-only visibility |
| runner exit truth | `MISSING` | no runner mechanics in current evidence |
| executable overlay | `PARTIAL` | can label dust; cannot claim executable edge |

## What Prevents Replay Implementation Today?

Primary blockers:

1. No checkpoint price truth.

The proposed filter depends on 15s/30s state. Current logs only show entry and exit, not the path between them.

2. MFE/MAE is not real path truth.

Fields exist, but current target rows show entry-price placeholders and zero peak excursion values.

3. Numeric spread is missing.

The logs show `NORMALIZED` spread state, but not numeric spread cost. This blocks microstructure-aware replay.

4. Quote freshness coverage is incomplete.

`quote_stale_ms` appears on only `8/27` target rows, below the replay gate.

5. No runner or profit-management truth exists.

Current rows end as TP/SL. There are no runner exits, partial reductions, or time-cap exits to validate runner replay.

6. Executable evidence is zero.

All target rows remain signal-only / dust-zone. Any replay result would still be simulation-only.

## What Can Be Done Today?

Allowed from current truth:

- baseline 09h10h signal ledger;
- post-hoc early SL count;
- post-hoc `30s+` survivor count;
- session/asset/side/lifecycle splits;
- quote freshness sensitivity on covered rows;
- dust-zone/executable labeling;
- identify missing checkpoint truth.

Not trustworthy today:

- treatment PnL for cut-at-15s or cut-at-30s;
- survivor hold replay;
- runner replay;
- MFE/MAE replay;
- executable PnL;
- spread-adjusted expectancy.

## Final Classification

```text
EARLY_FAILURE_DETECTION: PARTIAL
CHECKPOINT_REPLAY: MISSING
SURVIVOR_HOLD_REPLAY: PARTIAL
RUNNER_REPLAY: MISSING
MFE_MAE_TRUTH: MISSING
QUOTE_FRESHNESS_TRUTH: PARTIAL
SPREAD_LIQUIDITY_TRUTH: PARTIAL
EXECUTABLE_REALITY: PARTIAL

REPLAY_IMPLEMENTATION_READY: NO
SAFE_NEXT_BOUNDARY: TRUTH_LAYER_SPEC_OR_OFFLINE_GAP_REPORT
```

## Recommendation

Do not implement the early failure replay analyzer yet if the goal is treatment testing. First define the missing truth-layer contract:

- checkpoint marks at +15s/+30s/+45s/+60s;
- side-aware favorable/adverse state;
- real MFE/MAE extrema and timing;
- numeric spread at entry and checkpoints;
- quote freshness at entry and checkpoints;
- runner/profit-management exit schema;
- executable overlay fields.

Once those fields exist with adequate coverage, replay can test whether the 09h10h early failure filter improves expectancy without weakening stop-loss behavior.

Tests: not run; docs-only audit.
