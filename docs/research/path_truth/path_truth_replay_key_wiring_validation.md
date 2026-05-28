# Path Truth Replay Key Wiring Validation

Date: 2026-05-27

Mode: read-only validation report. No code, runtime mutation, replay, strategy, risk, execution, wallet, or live changes.

## Executive Verdict

```text
RUNTIME_VALIDATION_STATUS: NOT_YET_VALIDATED
```

The implementation contract is present in code, but the newest existing runtime evidence does not yet show `path_truth.paper_trade_replay_key` populated.

Latest `path_truth` file inspected:

```text
runtime/quant_data/path_truth/2026-05-27.jsonl
```

Result:

| Metric | Count |
|---|---:|
| `trade_path_checkpoint` rows | 3 |
| rows with `paper_trade_replay_key` populated | 0 |
| rows with `paper_trade_replay_key` null/missing | 3 |
| direct joins to `trade_journal` by `(run_id, paper_trade_replay_key)` | 0 |
| direct join rate over all checkpoints | 0 / 3 = 0.0% |
| direct join rate over keyed checkpoints | N/A, no keyed path-truth rows |
| parse errors | 0 |
| duplicate `(run_id, paper_trade_replay_key, checkpoint_elapsed_s)` rows | 0 |

Interpretation:

- This does not prove the wiring failed.
- It proves no post-wiring `trade_path_checkpoint` row with a populated `paper_trade_replay_key` exists yet in current runtime evidence.
- The newest path-truth rows are `event_end` rows whose payloads lack `paper_trade_replay_key`, `epoch_start_ts`, and `token_id`, so they remain legacy/proxy-only.
- A fresh runtime process that loads the patched code and opens a new position is still required before the runtime evidence can validate the new metadata propagation.

## Source Files Inspected

Primary evidence:

- `runtime/quant_data/path_truth/2026-05-27.jsonl`
- `runtime/quant_data/trade_journal/2026-05-27.jsonl`

Legacy comparison:

- `runtime/quant_data/path_truth/2026-05-24.jsonl`
- `runtime/quant_data/path_truth/2026-05-25.jsonl`
- `runtime/quant_data/path_truth/2026-05-26.jsonl`
- `docs/research/path_truth/path_join_root_cause_map.md`

Runtime health spot-check:

- `runtime/quant_data/system_health/2026-05-27.jsonl`
- latest log files under `logs/` by modification time

## Latest Path Truth Inventory

Latest file:

```text
runtime/quant_data/path_truth/2026-05-27.jsonl
```

Rows:

| Line | Run ID | Asset | Side | Checkpoint | `paper_trade_replay_key` | Condition ID Present | Epoch/Token Present |
|---:|---|---|---|---|---|---|---|
| 1 | `20260527T012251Z_59360_9c0a035a` | BTC | NO | `event_end` | null | yes | no |
| 2 | `20260527T012251Z_59360_9c0a035a` | ETH | NO | `event_end` | null | yes | no |
| 3 | `20260527T063527Z_33304_32db8c40` | ETH | NO | `event_end` | null | yes | no |

Checkpoint distribution:

| Checkpoint | Count |
|---|---:|
| `event_end` | 3 |
| `15` | 0 |
| `30` | 0 |
| `45` | 0 |
| `60` | 0 |

Asset distribution:

| Asset | Count |
|---|---:|
| BTC | 1 |
| ETH | 2 |

## Trade Journal Comparison

Same-day trade journal:

```text
runtime/quant_data/trade_journal/2026-05-27.jsonl
```

Trade journal rows:

| Metric | Count |
|---|---:|
| rows parsed | 6 |
| parse errors | 0 |
| rows with `paper_trade_replay_key` | 6 |
| apparent trade pairs | 3 opens + 3 closes |

The trade journal has direct replay keys for the same run/market context. Example:

```text
run_id:
  20260527T063527Z_33304_32db8c40

trade_journal.paper_trade_replay_key:
  0x80162bbd0c9266c5b0cffe19ff15886e763171a89549ae895c551a36cac0c3ae|1779864600|ETH|NO|87775116719751096460536129780229713249956032878590980728855279078837481845518

path_truth.paper_trade_replay_key:
  null
```

Direct join result:

```text
path_truth -> trade_journal by (run_id, paper_trade_replay_key)
0 / 3
```

The same-day rows may still be proxy-joinable by condition/asset/side, but this validation deliberately does not count proxy matches as success.

## Comparison To Old `PATH_JOIN_0_77`

Prior blocker:

```text
PATH_JOIN_0_77:
  sampled trade closes had (run_id, paper_trade_replay_key)
  path_truth had 0 rows with paper_trade_replay_key
  direct path join = 0 / 77
```

Current latest evidence:

```text
latest path_truth rows = 3
rows with paper_trade_replay_key = 0
direct path join = 0 / 3
```

Verdict:

```text
PATH_JOIN_0_77 is not cleared by existing runtime evidence.
```

The old blocker remains the correct evidence-state label until at least one new path-truth row with a populated `paper_trade_replay_key` is emitted and joins to the trade journal by `(run_id, paper_trade_replay_key)`.

## Legacy Row Status

All path-truth files currently remain legacy/null for `paper_trade_replay_key`:

| File | Checkpoint Rows | Keyed Rows | Null/Legacy Rows | Parse Errors |
|---|---:|---:|---:|---:|
| `2026-05-24.jsonl` | 46 | 0 | 46 | 0 |
| `2026-05-25.jsonl` | 49 | 0 | 49 | 0 |
| `2026-05-26.jsonl` | 45 | 0 | 45 | 0 |
| `2026-05-27.jsonl` | 3 | 0 | 3 | 0 |

This is expected for old rows. Historical JSONL was not rewritten and should remain classified as:

```text
legacy_path_truth_proxy_only
direct_join_eligible = false
```

## Duplicate And Parse Checks

Latest path-truth file:

| Check | Result |
|---|---|
| JSONL parse errors | 0 |
| duplicate `(run_id, paper_trade_replay_key, checkpoint_elapsed_s)` rows | 0 |
| duplicate populated replay keys at same checkpoint | 0 |
| duplicate keyed checkpoint evidence | none, because no keyed rows exist |

Repeated `paper_trade_replay_key` across multiple checkpoints will be valid in future evidence, because a single trade can emit `15`, `30`, `45`, `60`, and `event_end` rows. The duplicate check used here is the stricter checkpoint-level identity:

```text
(run_id, paper_trade_replay_key, checkpoint_elapsed_s)
```

## Runtime Error Check

`system_health/2026-05-27.jsonl`:

| Metric | Count |
|---|---:|
| rows parsed | 4,351 |
| parse errors | 0 |

Latest log spot-check found:

- no `Traceback` in sampled newest logs;
- no `CRITICAL` in sampled newest logs;
- no path-truth write failure found in sampled newest logs;
- Oracle websocket handshake retries are present;
- empty-orderbook recovery warnings are present.

Those log warnings are runtime data/feed quality signals, not direct evidence of a path-truth identity writer failure.

## Validation Status

```text
paper_trade_replay_key wiring in path_truth:
  NOT_YET_VALIDATED_BY_RUNTIME_EVIDENCE

reason:
  newest path_truth rows are all legacy/null event_end checkpoints

needed evidence:
  at least one new position opened by a runtime process using the patched code,
  followed by a path_truth checkpoint carrying metadata.paper_trade_replay_key
```

Future positive validation criteria:

| Criterion | Required |
|---|---|
| `path_truth.paper_trade_replay_key` populated | yes |
| `(run_id, paper_trade_replay_key)` joins to `trade_journal` | yes |
| scheduled checkpoint or `event_end` with key | yes |
| parse errors | 0 |
| duplicate checkpoint identity | 0 |
| old rows preserved as null/legacy | yes |

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Replay run: No

Bot/runtime launch: No

Code changes: No
