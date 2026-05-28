# Replay Key Validation After New Trade

Date: 2026-05-28
Scope: Read-only audit of 2026-05-27 path_truth and trade_journal after first post-patch trade.
Mode: No code, no runtime restart, no replay, no strategy/risk/execution/live changes.

## Executive Verdict

```text
VALIDATION_STATUS: CONFIRMED_DIRECT_JOIN
JOIN_RATE_POST_PATCH: 100.0%
BLOCKER: NONE
```

The post-patch run `20260527T110608Z_26764_9d379e2c` produced 3 paper trades, 4 path-truth
checkpoints, and a 100% direct join rate on `(run_id, paper_trade_replay_key)`.
PATH_JOIN_0_77 is superseded — the blocking gap no longer applies to new runs.

---

## Run Under Validation

| Field | Value |
|---|---|
| Run ID | `20260527T110608Z_26764_9d379e2c` |
| Date | 2026-05-27 |
| Mode | paper |
| Status | ended cleanly |

---

## Trade Counts

| Source | Rows | Detail |
|---|---|---|
| `trade_journal` trade_open | 3 | trades `a453a7b3`, `812087f4`, `ef82d77a` |
| `trade_journal` trade_close | 3 | matching closes for all 3 |
| `trade_journal` keyed rows | 6 | all 6 rows carry `paper_trade_replay_key` |
| `path_truth` checkpoint rows | 4 | 3 unique trades (one trade has 2 checkpoints) |
| `path_truth` keyed rows | 4 | 100% of path_truth rows carry `paper_trade_replay_key` |
| `path_truth` null/unkeyed rows | 0 | none in post-patch run |

---

## Path Truth Checkpoint Detail

| trade_id | checkpoint_reason | paper_trade_replay_key (prefix) |
|---|---|---|
| `a453a7b3` | `event_end` | `0x776f84c75c6f58ef…` |
| `812087f4` | `late` | `0x314a3c60dee7fc40…` |
| `812087f4` | `event_end` | `0x314a3c60dee7fc40…` (same trade, 2nd checkpoint) |
| `ef82d77a` | `event_end` | `0x249fcbec0f532f92…` |

---

## Direct Join Result

Join key: `(run_id, paper_trade_replay_key)`

| Metric | Count |
|---|---:|
| path_truth rows with replay key | 4 |
| trade_journal unique replay keys | 3 |
| direct join count | 4 |
| unjoined path_truth rows | 0 |
| **join rate (keyed)** | **100.0%** |
| **join rate (all path_truth)** | **100.0%** |
| parse errors | 0 |

---

## Duplicate Checkpoint Keys

One trade (`812087f4`) produced two path_truth checkpoints sharing the same
`paper_trade_replay_key`. This is expected — the trade received a `late` checkpoint
followed by an `event_end` checkpoint. Both join successfully.

| Metric | Count |
|---|---:|
| Duplicate replay key pairs | 1 |
| Cause | multi-checkpoint per trade (late + event_end) |
| Join integrity impact | None — both checkpoints join correctly |

---

## Legacy / Null Rows

Three path_truth rows from earlier runs exist in the same-day file. They carry no
`paper_trade_replay_key` because those runs predated the patch.

| Run ID | path_truth rows | Keyed | Status |
|---|---:|---:|---|
| `20260527T012251Z_59360_9c0a035a` | 2 | 0 | pre-patch, null |
| `20260527T063527Z_33304_32db8c40` | 1 | 0 | pre-patch, null |

Note: the trade_journal for those legacy runs **does** carry `paper_trade_replay_key`
(the trade_journal wiring was present earlier), but path_truth did not yet emit
the field. The null legacy rows should not be mixed into post-patch validation.

---

## PATH_JOIN_0_77 Status

Prior blocker name: `PATH_JOIN_0_77`
Prior state: path_truth lacked `paper_trade_replay_key`, preventing joinability.

| Prior gap | Post-patch state |
|---|---|
| path_truth key emission rate: unknown/0% | **100% for run `26764`** |
| direct join rate: N/A | **100%** |
| trades required to test: 0 | **3 trades observed** |

PATH_JOIN_0_77 is **resolved** for runs after the patch. The field is emitted and
joins directly.

---

## Same-Day File Summary (2026-05-27)

| File | Total rows | Post-patch rows | Keyed post-patch | Parse errors |
|---|---:|---:|---:|---:|
| `path_truth/2026-05-27.jsonl` | 7 | 4 | 4 | 0 |
| `trade_journal/2026-05-27.jsonl` | 12 | 6 | 6 | 0 |

---

## Integrity Checks

| Check | Result |
|---|---|
| Parse errors | 0 |
| Null replay key in post-patch path_truth | 0 |
| Unjoined path_truth rows (post-patch) | 0 |
| Duplicate checkpoint keys causing join collision | 0 (duplicates share key intentionally) |
| Cross-run contamination | None observed |

---

## Safety Confirmation

| Dimension | Changed |
|---|---|
| Runtime behavior | No |
| Live behavior | No |
| Strategy / risk / execution | No |
| Code changes | No |
| Replay run | No |
| Runtime restart | No |
