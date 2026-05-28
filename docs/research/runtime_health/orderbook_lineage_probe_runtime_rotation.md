# ORDERBOOK_LINEAGE_PROBE_V1 Runtime Rotation Report

Date: 2026-05-28
Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
Mode: controlled paper runtime rotation, observability validation only.

## Lifecycle Classification

```text
PAPER_VALIDATED
```

All four promotion conditions are met. Fresh paper runtime emits all 11 canonical alias
fields. Runtime is healthy. No malformed rows. No governance violations. No policy
authority introduced.

---

## Context

The `ORDERBOOK_LINEAGE_PROBE_V1` schema completion patch was implemented and tests passed
on 2026-05-28 (`docs/research/runtime_health/orderbook_lineage_probe_v1_schema_completion_report.md`).

Round 2 paper validation (`orderbook_lineage_probe_v1_paper_validation_round2.md`) confirmed
that the active runtime at the time of that audit was still emitting the pre-schema-completion
payload (0/11 canonical fields across 134 rows). Validation was blocked pending a runtime
rotation so the patched code could emit fresh rows.

This report covers the controlled rotation and resulting validation.

---

## Step 1 — Old Runtime Identification

| Field | Value |
|---|---|
| PID | `38660` |
| run_id | `20260528T074009Z_38660_884a713e` |
| Log file | `logs/polytrade_bot_20260528_143959_38660.log` |
| Pre-patch canonical field coverage | 0/11 across 174 rows |
| Process status at rotation time | **Already ended** (process not found) |

The old process had ended naturally before rotation was performed. No kill, no forced stop,
no process termination was required or executed.

Old runtime last write evidence:

| Source | Rows | Latest UTC |
|---|---:|---|
| `orderbook_lineage/2026-05-28.jsonl` | 174 | `2026-05-28T08:10:28Z` |
| Log tail | — | `2026-05-28 15:10:17 local` |

---

## Step 2 — New Runtime Launch

Launch command used:

```bash
python main.py --mode paper --interval 60
```

This is the canonical safe paper command from `CODEX_START_HERE.md`. No flags were added to
alter strategy, risk, sizing, execution, thresholds, or replay behavior.

| Field | Value |
|---|---|
| Log-filename PID | `39092` (derived from log filename; Python process confirmed active via ongoing log writes) |
| New run_id | `20260528T081158Z_39092_3d32c465` |
| Log file | `logs/polytrade_bot_20260528_151154_39092.log` |
| Launch confirmed at | `2026-05-28T08:11:58Z` (UTC) |
| Mode confirmed | `paper` |

---

## Step 3 — Startup Confirmation

Runtime startup evidence from log:

```text
Mode: PAPER
Execution: PAPER ONLY
Paper Starting Balance Source: live_wallet_reference
```

Active orderbook fetching confirmed within 2 cycles:

```text
[ORDERBOOK_FLOW] ticker=BTC ...
[ORDERBOOK_RESPONSE] token=... bids_count=40 asks_count=59 ...
[ORDERBOOK_BEST] bid=0.4000 ask=0.4100 spread=0.010000 age=0.274s
```

---

## Step 4 — Runtime Health Confirmation

Checked after first fresh lineage rows appeared.

| Source | New Run Rows | Latest UTC |
|---|---:|---|
| `system_health` | 17 | `2026-05-28T08:14:25Z` |
| `decision_log` | 6 | `2026-05-28T08:14:25Z` |
| `orderbook_lineage` | 4 | `2026-05-28T08:13:27Z` |

Log error/traceback/critical scan: **0 matches**

Active cycle log evidence at check time:

```text
[REALTIME 1s] BTC PTB=$73,294.99 Oracle=$73,315.20 Edge=0.00% | ETH ...
[ORDERBOOK_FLOW] ticker=BTC outcome=YES ...
```

Runtime healthy: **Yes**

---

## Step 5 — First Canonical Field Observation

First fresh `orderbook_lineage` row with canonical fields appeared in row `1` of the new run.

| Timestamp | `2026-05-28T08:12:57Z` |
|---|---|
| run_id | `20260528T081158Z_39092_3d32c465` |
| Canonical fields present | 11/11 |

---

## Step 6 — Full Canonical Field Validation

Checked across all 20 fresh rows from the new run (updated at `2026-05-28T08:23:40Z`).

| Field | Present | Coverage |
|---|---:|---:|
| `book_used_for_decision` | 20/20 | 100% |
| `book_used_token_pair_match` | 20/20 | 100% |
| `empty_book_role` | 20/20 | 100% |
| `serialized_book_source` | 20/20 | 100% |
| `serialized_yes_no_bid_ask_present` | 20/20 | 100% |
| `serialized_depth_present` | 20/20 | 100% |
| `serialized_spread_present` | 20/20 | 100% |
| `terminal_skip_reason` | 20/20 | 100% |
| `terminal_gate_stage` | 20/20 | 100% |
| `yes_normalization_status` | 20/20 | 100% |
| `no_normalization_status` | 20/20 | 100% |

All 11/11 canonical alias fields are present on all 20 fresh rows. Coverage: **100%**.

### Canonical Value Distribution (20 fresh rows)

| Field | Value | Count |
|---|---|---:|
| `current_fetch_status` | `fresh_fetch_executable` | 17 |
| `current_fetch_status` | `fresh_fetch_failed` | 3 |
| `empty_book_role` | `absent` | 17 |
| `empty_book_role` | `terminal` | 3 |
| `terminal_skip_reason` | `null` | 17 |
| `terminal_skip_reason` | `empty_book` | 3 |
| `terminal_gate_stage` | `none` | 17 |
| `terminal_gate_stage` | `market_data` | 3 |
| `yes_normalization_status` | `accepted_executable` | 17 |
| `yes_normalization_status` | `unknown` | 3 |
| `no_normalization_status` | `accepted_executable` | 17 |
| `no_normalization_status` | `unknown` | 3 |
| `book_used_for_decision` | `current_fetch` | 17 |
| `book_used_for_decision` | `unavailable` | 3 |

Both success-path (`fresh_fetch_executable`, `absent`, `accepted_executable`, `current_fetch`) and
failure-path (`fresh_fetch_failed`, `terminal`, `empty_book`, `market_data`, `unavailable`, `unknown`)
canonical values are represented in fresh paper runtime emission.

Sample canonical values from row 1 (success path):

| Field | Value |
|---|---|
| `book_used_for_decision` | `current_fetch` |
| `book_used_token_pair_match` | `True` |
| `empty_book_role` | `absent` |
| `serialized_book_source` | `current_fetch` |
| `serialized_yes_no_bid_ask_present` | `True` |
| `serialized_depth_present` | `True` |
| `serialized_spread_present` | `True` |
| `terminal_skip_reason` | `None` |
| `terminal_gate_stage` | `none` |
| `yes_normalization_status` | `accepted_executable` |
| `no_normalization_status` | `accepted_executable` |

All values match the canonical schema definitions from the schema completion report.

---

## Step 7 — Governance and Integrity Check

### Governance Fields (4/4 fresh rows)

| Field | Value |
|---|---|
| `probe_authority_level` | `evidence_only` |
| `policy_authority` | `none` |
| `runtime_decision_authority` | `False` |
| `execution_authority` | `False` |
| `risk_authority` | `False` |

No governance violations. No policy authority fields observed.

### Data Integrity

| Check | Result |
|---|---|
| Parse errors | 0 |
| Malformed rows | 0 |
| Rows over 8 KB | 0 |
| Max row size | 4,551 bytes |
| Raw orderbook arrays emitted | None |
| Log errors / tracebacks | 0 |
| Cross-run contamination | None |

---

## Comparison: Pre vs Post Rotation

| Metric | Old Run (pre-patch) | New Run (post-rotation) |
|---|---|---|
| run_id | `38660_884a713e` | `39092_3d32c465` |
| Canonical fields present | 0/11 | **11/11** |
| Row coverage | 0/174 | 20/20 (100%) |
| Success-path rows | — | 17 |
| Failure-path rows (`fresh_fetch_failed` / terminal empty-book) | — | 3 |
| Parse errors | 0 | 0 |
| Governance clean | Yes | Yes |
| Max row size | 4,125 bytes | 4,551 bytes |

---

## Promotion Rule Verification

| Condition | Met |
|---|---|
| Fresh runtime rows contain canonical alias fields | **Yes** — 11/11 fields, 20/20 rows |
| Both success-path and failure-path canonical values observed | **Yes** — 17 success, 3 failure-path (`terminal`, `empty_book`, `unavailable`, `unknown`) |
| Runtime remains healthy | **Yes** — active log writes, zero errors |
| No malformed rows | **Yes** — 0 parse errors, 0 oversized rows |
| No governance violations | **Yes** — evidence_only, no policy authority |
| No policy authority introduced | **Yes** — confirmed in each row |

All conditions met.

---

## Final Classification

```text
PAPER_VALIDATED
```

The ORDERBOOK_LINEAGE_PROBE_V1 schema-completion canonical alias fields have been confirmed
in fresh paper runtime output. The probe remains observability-only. No policy consumers,
runtime decisions, strategy changes, risk changes, execution changes, or live config changes
were introduced.

---

## Safety Confirmation

| Dimension | Changed |
|---|---|
| Runtime behavior | No |
| Strategy / risk / execution | No |
| Thresholds | No |
| Live behavior | No |
| Replay execution | No |
| Code changes during rotation | No |
| Policy authority introduced | No |
| Existing logs/evidence preserved | Yes |

---

## Note on Telegram

The paper runtime launch may have triggered a Telegram startup alert via
`utils/telegram_alerts.py`. This is normal behavior for a paper runtime startup and is
within the authorized scope of this task. No Telegram behavior was changed.
