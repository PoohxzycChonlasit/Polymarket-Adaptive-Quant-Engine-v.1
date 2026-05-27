# PATH_JOIN_0_77 Root Cause Map

Date: 2026-05-27

Mode: read-only, docs-only root-cause audit. No code, runtime mutation, replay, promotion, strategy, risk, execution, stoploss, or live changes.

## Context

Blocker:

```text
PATH_JOIN_0_77
```

Why it matters:

- Blocks executable-truth approval.
- Blocks canonical runtime-truth ledger claims.
- Forces path truth to remain proxy evidence instead of direct trade lineage.
- Prevents Hermes from ingesting path truth as executable evidence.

Source lineage:

- `docs/research/offline_executable_truth_ledger_audit.md`
- `docs/research/runtime_executable_truth_source_audit.md`
- `docs/research/executable_truth_frontier_map.md`
- `docs/research/executable_truth_blocker_observatory_design.md`
- `docs/research/path_truth_field_coverage_gap_audit.md`
- `docs/research/path_truth_checkpoint_validation.md`
- `docs/research/replay_join_key_contract.md`

## Executive Verdict

```text
PATH_JOIN_0_77_ROOT_CAUSE:
  path_truth and trade/execution/decision/research producers use different identity islands.

DIRECT_JOIN_BY_PREFERRED_KEY:
  BLOCKED

WHY 0 / 77:
  sampled trade closes all have (run_id, paper_trade_replay_key),
  but path_truth has 0 rows with paper_trade_replay_key.
```

This is not a lack of path-truth data. Path truth exists and is useful. The failure is a direct-lineage gap:

- trade/execution/decision/research use `paper_trade_replay_key`, `candidate_id`, and `decision_id`;
- path truth uses `trade_id`, `run_id`, `condition_id`, `asset`, `side`, `candidate_trace_id`, `replay_chain_id`, `lifecycle_instance_id`, and `inventory_context_id`;
- the path-truth `candidate_id` and `decision_id` fields are null;
- path-truth `candidate_trace_id` is synthetic/weak and does not match execution/decision trace IDs.

Result:

```text
trade_close -> path_truth by (run_id, paper_trade_replay_key) = 0 / 77
trade_close -> path_truth by proxy composite = 60 / 77
```

## Sample Scope

The `PATH_JOIN_0_77` blocker comes from the offline executable truth ledger sample:

| Metric | Value |
|---|---:|
| sampled closes | 77 |
| close rows with `(run_id, paper_trade_replay_key)` | 77 / 77 |
| close -> trade_open direct join | 77 / 77 |
| close -> execution_log direct join | 77 / 77 |
| close -> decision_log direct join | 77 / 77 |
| close -> research_log direct join | 77 / 77 |
| close -> path_truth direct join | 0 / 77 |
| close -> path_truth proxy join | 60 / 77 |

Fresh schema spot-check across completed path-truth gate dates `2026-05-24` to `2026-05-26` confirms the same identity asymmetry:

| Producer | Records | `paper_trade_replay_key` | `trade_id` | `candidate_id` | `decision_id` |
|---|---:|---:|---:|---:|---:|
| `path_truth` | 140 | 0 | 140 | 0 | 0 |
| `trade_journal` | 210 | 210 | 0 | 210 | 0 |

The direct join blocker is therefore structural and still present in the completed path-truth gate slice.

## Join Key Inventory

### Path Truth Keys

Source: `runtime/quant_data/path_truth/YYYY-MM-DD.jsonl`

| Key | Status | Classification | Notes |
|---|---|---|---|
| `run_id` | populated | DIRECT context | Run-scopes all joins. Not enough alone. |
| `paper_trade_replay_key` | absent | MISSING | Primary cause of `0 / 77` preferred-key failure. |
| `trade_id` | populated | WEAK local identity | Path-local position/trade identifier. Not present in trade journal, execution, decision, or research producers. |
| `candidate_id` | null | MISSING | Available elsewhere, but not carried into path truth. |
| `decision_id` | null | MISSING | Available in execution/decision/research, but not carried into path truth. |
| `candidate_trace_id` | populated | WEAK | Generated from passive deterministic path-truth fields; does not match decision/execution trace IDs. |
| `replay_chain_id` | populated | WEAK | Useful within path truth, not proven as cross-producer canonical identity. |
| `condition_id` | populated | PROXY | Can help proxy join with asset/side/run. Not unique per trade. |
| `asset` | populated | PROXY | Required for proxy joins. Not unique. |
| `side` | populated | PROXY | Required for proxy joins. Not unique. |
| `lifecycle_instance_id` | populated | WEAK / candidate unlock | Also appears in trade journal, but not yet validated as the canonical per-trade join for the 77-row ledger. |
| `inventory_context_id` | populated | WEAK / candidate unlock | Useful context, not sufficient alone for executable-truth approval. |
| `session_hour_utc` | populated | context only | Good for session research; not identity. |

### Trade Journal Keys

Source: `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl`

| Key | Status | Classification | Notes |
|---|---|---|---|
| `run_id` | populated | DIRECT context | Required run scope. |
| `paper_trade_replay_key` | populated | DIRECT | Primary trade open/close and execution continuity key. |
| `trade_id` | absent | MISSING for path join | Cannot consume path-truth `trade_id`. |
| `candidate_id` | populated | DIRECT for candidate lineage | Joins to decision/execution when run-scoped. |
| `decision_id` | absent | MISSING | Separate trade-journal gap; decision_id is available elsewhere. |
| `candidate_trace_id` | populated | WEAK / trace context | Does not solve path join because path trace ID is synthetic. |
| `execution_trace_id` | populated | DIRECT / fallback | Useful for execution lineage. |
| `replay_chain_id` | populated | WEAK | Helpful context, but not the preferred direct join. |
| `condition_id`, `asset`, `side`, `token_id` | populated | PROXY / composite | Good fallback fields, not canonical per-trade identity. |
| `lifecycle_instance_id`, `inventory_context_id` | populated | WEAK / candidate unlock | Possible future path bridge if validated. |

### Decision Keys

Source: `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl`

| Key | Status | Classification | Notes |
|---|---|---|---|
| `run_id` | populated | DIRECT context | Required run scope. |
| `paper_trade_replay_key` | populated on relevant decision rows | DIRECT to trade/execution/research | Direct ledger joins work in the 77-row audit. |
| `candidate_id` | populated | DIRECT | Preferred decision-to-trade fallback when run-scoped. |
| `decision_id` | populated | DIRECT | Preferred decision-to-execution key. |
| `candidate_trace_id` | populated | DIRECT within decision lineage | Does not match path-truth synthetic trace IDs. |
| `execution_trace_id` | partial | WEAK / fallback | Useful when present. |
| `condition_id`, `asset`, `side`, `token_id` | populated | PROXY / composite | Useful fallback only. |
| `market_regime`, `trend_regime`, `volatility_regime` | populated | context | Useful for regime evidence once direct trade join exists. |

### Execution Keys

Source: `runtime/quant_data/execution_log/YYYY-MM-DD.jsonl`

| Key | Status | Classification | Notes |
|---|---|---|---|
| `run_id` | populated | DIRECT context | Required run scope. |
| `paper_trade_replay_key` | populated on relevant execution rows | DIRECT | Direct execution-to-trade joins work in the 77-row audit. |
| `trade_id` | absent | MISSING for path join | Cannot consume path-truth `trade_id`. |
| `candidate_id` | populated | DIRECT | Available at execution time. |
| `decision_id` | populated | DIRECT | Available at execution time. |
| `candidate_trace_id` | populated | DIRECT within execution lineage | Does not match path-truth synthetic trace IDs. |
| `execution_trace_id` | populated | DIRECT / fallback | Useful for decision/execution lineage. |
| `condition_id`, `asset`, `side`, `token_id` | populated | PROXY / composite | Supports fallback matching, not executable approval. |
| `quote_stale_ms`, quote timing fields | partial context | context | Useful after direct trade linkage; not identity. |

### Research Keys

Source: `runtime/quant_data/research_log/YYYY-MM-DD.jsonl`

| Key | Status | Classification | Notes |
|---|---|---|---|
| `run_id` | populated | DIRECT context | Required run scope. |
| `paper_trade_replay_key` | populated on relevant research snapshots | DIRECT for ledger sample | Offline ledger found 77 / 77 direct research joins. |
| `candidate_id` | populated on relevant research snapshots | DIRECT | Useful when run-scoped. |
| `decision_id` | populated on relevant research snapshots | DIRECT | Useful for decision lineage. |
| `candidate_trace_id` | populated on relevant research snapshots | DIRECT within research/decision context | Does not solve path-truth trace mismatch. |
| `condition_id`, `asset`, `side`, `token_id` | populated on relevant snapshots | PROXY / composite | Useful fallback only. |
| `market_regime`, `trend_regime`, `volatility_regime` | populated on relevant snapshots | context | Can inform research/regime once direct trade lineage is established. |

## Join Graph

```mermaid
flowchart LR
  D["decision_log\n(run_id, decision_id, candidate_id,\npaper_trade_replay_key)"]
  E["execution_log\n(run_id, decision_id, candidate_id,\npaper_trade_replay_key)"]
  T["trade_journal\n(run_id, paper_trade_replay_key,\ncandidate_id)"]
  R["research_log\n(run_id, decision_id, candidate_id,\npaper_trade_replay_key on relevant rows)"]
  P["path_truth\n(run_id, trade_id,\ncondition_id, asset, side,\ncandidate_id=null,\ndecision_id=null,\npaper_trade_replay_key missing)"]

  D -- "DIRECT 77/77" --> E
  E -- "DIRECT 77/77" --> T
  D -- "DIRECT 77/77" --> T
  R -- "DIRECT 77/77" --> T
  T -- "DIRECT preferred key 0/77" -. BLOCKED .-> P
  T -- "PROXY 60/77\n(run_id, condition_id, asset, side)" -. proxy .-> P
```

## Missing Lineage

The missing lineage is the bridge from the position/path checkpoint writer back to the canonical trade identity.

Missing from path truth:

1. `paper_trade_replay_key`
2. `candidate_id`
3. `decision_id`

Missing from trade/execution/decision/research side:

1. path-truth `trade_id`
2. matching path-truth `candidate_trace_id`

Mismatched:

1. `candidate_trace_id`
   - present in path truth;
   - present in execution/decision/research;
   - not the same value for the same trade;
   - path-truth version is labeled weak/passive and should not be used as cross-producer identity.

The path-truth writer is attached to an in-memory position object after the trade opens. That object has enough local information to write checkpoints, but it does not carry the upstream decision/execution identity fields into `pos.metadata`.

## Blocked Paths

| Desired Join | Current Result | Classification | Root Cause |
|---|---:|---|---|
| `trade_close -> path_truth` by `(run_id, paper_trade_replay_key)` | 0 / 77 | MISSING | `paper_trade_replay_key` absent from path truth. |
| `trade_close -> path_truth` by `(run_id, trade_id)` | 0 / 77 | MISSING | `trade_id` absent from trade journal. |
| `decision_log -> path_truth` by `(run_id, decision_id)` | 0 / 77 | MISSING | `decision_id` absent/null in path truth. |
| `decision_log -> path_truth` by `(run_id, candidate_id)` | 0 / 77 | MISSING | `candidate_id` absent/null in path truth. |
| `execution_log -> path_truth` by `(run_id, candidate_trace_id)` | not safe | WEAK | path-truth trace ID is synthetic and non-matching. |
| `trade_close -> path_truth` by `(run_id, condition_id, asset, side)` | 60 / 77 | PROXY | Composite context can match many rows, but cannot prove per-trade identity. |
| `trade_close -> path_truth` by time window | possible in small windows | PROXY / WEAK | Works when no same-run same-asset same-side collision exists; unsafe as canonical ledger truth. |
| `trade_journal -> path_truth` by `lifecycle_instance_id` | candidate path | WEAK | Present on both sides, but not yet validated as the 77-row canonical bridge. |

## Why Direct Joins Fail

The failure is deterministic:

1. The preferred ledger join key is `(run_id, paper_trade_replay_key)`.
2. All sampled trade closes have this key: 77 / 77.
3. Path truth has no `paper_trade_replay_key`.
4. Therefore every direct lookup from the 77 closes into path truth misses.

In short:

```text
trade_close.paper_trade_replay_key exists
path_truth.paper_trade_replay_key missing
= direct path join impossible
```

The secondary fields do not rescue direct lineage:

- `candidate_id` is present in trade/execution/decision/research but null in path truth.
- `decision_id` is present in execution/decision/research but null in path truth and absent from trade journal.
- `trade_id` is present in path truth but absent from trade/execution/decision/research.
- `candidate_trace_id` exists on both sides but does not match across producers.

This creates two separate identity islands:

```text
Island A:
  trade_journal / execution_log / decision_log / research_log
  keys = paper_trade_replay_key, candidate_id, decision_id, execution_trace_id

Island B:
  path_truth
  keys = trade_id, synthetic candidate_trace_id, replay_chain_id, condition_id, asset, side
```

`PATH_JOIN_0_77` is the result of no canonical bridge between Island A and Island B.

## Why Proxy Joins Only Reach 60 / 77

The proxy join uses:

```text
(run_id, condition_id, asset, side)
```

This can attach some path-truth rows to trade closes because those fields exist in both identity islands.

It still fails or remains unsafe because:

- the composite is not per-trade unique;
- a single market can have multiple same-asset same-side positions/checkpoints;
- fast closes may only emit `event_end` or no scheduled checkpoint depth;
- path-truth rows are checkpoint events, not one row per trade-close ledger row;
- no `paper_trade_replay_key`, `candidate_id`, or `decision_id` confirms the match;
- path-truth `trade_id` cannot be checked against the trade journal.

So `60 / 77` is useful blocker evidence, not a canonical executable-truth join.

## Candidate Unlocks

### Unlock 1: Carry `paper_trade_replay_key` into path truth

Classification if implemented later: DIRECT

Effect:

```text
trade_close -> path_truth by (run_id, paper_trade_replay_key)
```

This is the cleanest unlock for executable-truth ledger joins. It aligns path truth with the existing direct trade/execution/decision/research ledger.

### Unlock 2: Carry `candidate_id` and `decision_id` into position metadata

Classification if implemented later: DIRECT for candidate/decision lineage

Known root cause from prior audit:

```text
pos.metadata is empty at checkpoint time
```

The path-truth writer already tries to read:

```text
metadata["candidate_id"]
metadata["decision_id"]
```

But those values are not written into the position object at trade-open time.

### Unlock 3: Validate `lifecycle_instance_id` as a bridge

Classification: candidate WEAK -> DIRECT only if proven unique and stable

Current state:

- present in path truth;
- present in trade journal;
- not the preferred executable ledger key;
- not yet proven across the 77-row sample as collision-safe.

This may become a useful interim bridge, but it should not be promoted without a join-confidence audit.

### Unlock 4: Align `candidate_trace_id`

Classification if implemented later: DIRECT / fallback

Current issue:

Path truth creates a weak synthetic trace ID instead of carrying the execution/decision trace ID. Aligning it would improve replay lineage, but it is broader than the minimum path join unlock.

## Current Classification Matrix

| Path | Classification | Current Use |
|---|---|---|
| trade/execution/decision/research by `(run_id, paper_trade_replay_key)` | DIRECT | Safe for signal/dust ledger. |
| trade/execution/decision by `(run_id, candidate_id)` | DIRECT | Safe when run-scoped. |
| decision/execution by `(run_id, decision_id)` | DIRECT | Safe when both sides carry it. |
| trade/research/decision/execution to path by `paper_trade_replay_key` | MISSING | Blocked: path truth lacks key. |
| trade/research/decision/execution to path by `candidate_id` | MISSING | Blocked: path truth candidate_id null. |
| trade/research/decision/execution to path by `decision_id` | MISSING | Blocked: path truth decision_id null. |
| trade to path by `trade_id` | MISSING | Blocked: trade journal lacks path-local trade_id. |
| trace ID path joins | WEAK | Path truth trace IDs are synthetic/non-matching. |
| path proxy by `(run_id, condition_id, asset, side)` | PROXY | Useful for research only; not executable truth. |
| path time-window joins | PROXY / WEAK | Useful for local diagnosis; collision risk prevents canonical status. |

## Impact

Executable:

```text
EXECUTABLE_PNL_APPROVED remains BLOCKED.
```

Reason: path behavior can influence executable truth, but the path checkpoint evidence is not directly attached to the trade ledger.

Runtime truth:

```text
RUNTIME_TRUTH remains PARTIAL_RAW_EVIDENCE.
```

Reason: trade/execution/decision/research can join directly, but path truth remains proxy-only.

Hermes ingest:

```text
ALLOW:
  signal evidence
  dust evidence
  blocker evidence
  proxy path-truth caveats

BLOCK:
  executable_pnl
  direct path truth
  growth readiness
```

## Root Cause Summary

Primary root cause:

```text
path_truth does not emit paper_trade_replay_key.
```

Secondary root causes:

```text
candidate_id is not propagated into path_truth.
decision_id is not propagated into path_truth.
path_truth trade_id is local and absent from sibling logs.
path_truth candidate_trace_id is synthetic and non-matching.
```

Producer boundary:

```text
trade_open / position metadata carry boundary
```

The upstream decision/execution identity exists. The path-truth checkpoint writer does not receive it because the position metadata does not carry it forward.

## Recommended Next Step

Docs-only next step:

```text
PATH_JOIN_UNLOCK_READINESS_CHECKLIST
```

Required before implementation:

- Confirm 7 completed path-truth dates.
- Validate whether `lifecycle_instance_id` can bridge existing evidence without collisions.
- Define preferred path-truth identity contract:
  - `paper_trade_replay_key`
  - `candidate_id`
  - `decision_id`
  - `timestamp_source`
  - `lineage_confidence`
- Require additive-only JSONL changes.
- Preserve all existing path-truth fields.
- Keep proxy joins visibly labeled as proxy.

No implementation should occur from this root-cause map alone.

## What Not To Do

- Do not promote proxy path joins to direct evidence.
- Do not compute executable PnL from proxy path joins.
- Do not infer `decision_id` from candidate hash patterns as canonical truth.
- Do not join on raw `candidate_id` without `run_id`.
- Do not run replay.
- Do not mutate runtime.
- Do not change strategy, risk, stoploss, sizing, execution, wallet, or live config.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Replay run: No

Promotion: No

Tests run: Not required. This was a docs-only read-only root-cause audit.
