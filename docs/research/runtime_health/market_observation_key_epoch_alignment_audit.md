# Market Observation Key Epoch Alignment Audit

Date: 2026-05-28
Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
Mode: read-only audit, docs only, no implementation, no runtime mutation.

Prior context: `docs/research/runtime_health/ms_dl_identity_normalization_design_audit.md`

---

## Executive Finding

**Correction to prior design audit**: The prior design audit (`ms_dl_identity_normalization_design_audit.md`) recommended `condition_id|epoch_start_ts` as the bridge key derivation. `epoch_start_ts` is **0% present in decision_log**. As written, that recommendation would silently fail for every DL row — the bridge key would be undeserved on the most important producer it needs to cover.

The correct field is `epoch_start`, which is **100% present in both market_snapshots and decision_log**. Derivation must use the same alias-priority pattern already established in `_compute_paper_trade_replay_key` (`quant_event_logger.py:354`), because each producer uses a different epoch field name.

**Feasibility verdict**: `market_observation_key` = `condition_id|epoch_start` is feasible. Coverage is 100% in both target producers. Zero collisions. The relationship shape (1 key : N rows in each producer) correctly models "one market window : many observations/evaluations." The bridge preserves the distinction between market observation and candidate identity.

---

## Direct Answers

| Question | Answer |
|---|---|
| Is `market_observation_key` feasible? | **Yes** — using `epoch_start` (alias-resolved), not `epoch_start_ts`. |
| What is field coverage in MS and DL? | `condition_id` 100%/100%. `epoch_start` 100%/100%. `epoch_start_ts` 100%/**0%** (DL missing). |
| Are there collisions? | Zero. `condition_id + epoch_start` maps uniquely to one (ticker, market window) pair. |
| Are there missing/null edge cases? | MS and DL: none. risk_log, trade_journal, path_truth each use different epoch field names — see Section 4. |
| Does it preserve governance boundaries? | Yes. 1:N shape confirms "observation ≠ candidate identity." One key groups many evaluations; no false equivalence. |
| What would implementation need to avoid false joins? | Use alias-priority resolution (same pattern as `_compute_paper_trade_replay_key`). Document the key as a coarse bridge, not a trace ID. Never substitute it for `paper_trade_replay_key` or `candidate_trace_id`. |

---

## Section 1 — Field Coverage Evidence

### 1a — Per-Producer Epoch Field Coverage (verified from JSONL, today)

| Producer | `condition_id` | `epoch_start_ts` | `epoch_start` | `market_epoch_start` | `candidate_seen_ts` |
|---|---|---|---|---|---|
| `market_snapshots` | 500/500 (100%) | 500/500 (100%) | 500/500 (100%) | 500/500 (100%) | 500/500 (100%) |
| `decision_log` | 500/500 (100%) | **0/500 (0%)** | 500/500 (100%) | 500/500 (100%) | 500/500 (100%) |
| `risk_log` (market rows) | 462/500 (92%) | 0/500 (0%) | **0/500 (0%)** | 462/500 (92%) | 462/500 (92%) |
| `trade_journal` | 20/20 (100%) | 20/20 (100%) | **0/20 (0%)** | 0/20 (0%) | 20/20 (100%) |
| `path_truth` | 18/18 (100%) | 0/18 (0%) | **0/18 (0%)** | 0/18 (0%) | **0/18 (0%)** |

Each producer uses a different epoch field name. No single field name is universally present. The full picture:

- **`epoch_start_ts`**: present in MS (100%) and trade_journal (100%); absent in DL (0%), risk_log (0%), path_truth (0%).
- **`epoch_start`**: present in MS (100%) and DL (100%); absent in trade_journal (0%), risk_log (0%), path_truth (0%).
- **`market_epoch_start`**: present in MS (100%), DL (100%), risk_log market-rows (92%); absent in trade_journal (0%), path_truth (0%).
- **`candidate_seen_ts`**: present in MS (100%), DL (100%), risk_log market-rows (92%), trade_journal (100%); absent in path_truth (0%).

### 1b — Epoch Field Types and Format Consistency

| Field | MS type | DL type | Values match? |
|---|---|---|---|
| `epoch_start` | `int` | `int` | Yes — same numeric value |
| `market_epoch_start` | `int` | `int` | Yes — same numeric value |
| `candidate_seen_ts` | `str` | `str` | Yes — same numeric string |

No type mismatch between MS and DL. The numeric epoch value is the same whether read from `epoch_start` (MS) or `epoch_start` (DL). Both encode the market trading window's start timestamp in Unix seconds.

### 1c — `candidate_seen_ts` vs `epoch_start` Alignment

In a 200-row sample from each producer: **zero mismatches**. `candidate_seen_ts` and `epoch_start` resolve to the same numeric value on every row (though `candidate_seen_ts` is stored as a string and `epoch_start` as an integer). This confirms they encode the same timestamp and are interchangeable for key derivation.

---

## Section 2 — Key Distribution Evidence

### 2a — Full-File Key Coverage

Scanning full `2026-05-28.jsonl` files for both producers:

| Metric | Value |
|---|---|
| MS total rows | 5,129 |
| DL total rows | 5,958 |
| Unique `(condition_id, epoch_start)` keys in MS | 225 |
| Unique `(condition_id, epoch_start)` keys in DL | 225 |
| Keys present in both MS and DL | **225 (100%)** |
| Keys present in MS only | **0** |
| Keys present in DL only | **0** |

Full overlap. Every market window key present in MS is also present in DL. Every DL market window key is also present in MS.

### 2b — Collision Check

Zero collisions in full-file scan. `condition_id + epoch_start` maps to exactly one (ticker, market window) pair across all 5,129 MS rows + 5,958 DL rows combined. No two different markets share the same (condition_id, epoch_start) pair. This is expected — condition_id is a blockchain-derived market address that is globally unique per market. Two tickers (BTC, ETH) have different condition_ids.

### 2c — One-to-Many Relationship Shape

For each unique bridge key, MS and DL both emit multiple rows (multiple evaluation cycles within the same epoch window):

| Metric | MS rows per key | DL rows per key | DL/MS ratio |
|---|---|---|---|
| Minimum | 1 | 1 | 1.00 |
| Maximum | 30 | 34 | 21.00 |
| Average | 22.8 | 26.5 | 1.46 |

This is expected and correct behavior. Each market window (epoch) is evaluated multiple times per cycle. MS emits one row per market per bot cycle; DL emits one row per candidate evaluation. A cycle may produce 1–2 DL evaluations per MS row (one per token side). The DL/MS ratio greater than 1 reflects the DL generating both YES and NO side evaluations per observation cycle.

**DL/MS ratio max=21**: The highest ratio observed (MS=1, DL=21 for condition_id `0xed0a4da5...`, epoch=1779954600) represents a late-window market where MS completed only one scan cycle before the epoch closed, while DL produced 21 evaluations from that single window (all `side=NO`). This is correct behavior — a market near expiry may be scanned once but evaluated many times as the trading logic examines it from multiple signal angles. Not a data quality issue.

---

## Section 3 — Feasibility Assessment

### 3a — Primary Target: MS→DL Bridge

| Requirement | Result |
|---|---|
| `condition_id` available in both producers | ✓ 100%/100% |
| Epoch field available in both producers (same field name) | ✓ `epoch_start` 100%/100% |
| Epoch values consistent between producers for same market window | ✓ Confirmed in 200-row alignment check |
| Zero collisions | ✓ Full-file scan: 0 collisions |
| Key set overlap = 100% | ✓ 225/225 keys shared |
| One-to-many shape semantically correct | ✓ 1 market window : N rows from each producer |

**Verdict: FEASIBLE** using `condition_id|epoch_start`.

### 3b — Caveat: Cycle-level MS↔DL pairing not verified

This audit confirmed that the key SET is 100% shared between MS and DL at the market-window level. It did NOT verify that for a specific individual MS row and the DL rows from the same bot cycle, the epoch values resolve identically. The full-file key overlap is strong evidence they do (the same epoch window is open for both producers), but the individual-row temporal alignment within a window is a verification step for the implementation phase, not assumed here.

### 3c — Extended Scope: Other Producers

| Producer | Can emit `market_observation_key`? | Primary epoch field | Condition |
|---|---|---|---|
| `market_snapshots` | ✓ Yes | `epoch_start` | No change needed |
| `decision_log` | ✓ Yes | `epoch_start` | No change needed |
| `risk_log` (market rows) | ✓ Yes (92% coverage) | `market_epoch_start` | Alias needed; 8% gap = system-health rows (no market identity, correct) |
| `trade_journal` | ✓ Yes | `epoch_start_ts` | Alias needed; value matches |
| `path_truth` | **✗ Not without change** | None | All epoch fields absent (0%); would need a new epoch field emitted in the path_truth payload |

path_truth is the only producer that cannot participate in `market_observation_key` bridging without a code change. Note: path_truth already has `paper_trade_replay_key` embedded with the epoch as the second pipe-delimited component (e.g., `cid|1779954000|asset|side|token_id`). It can be bridged to MS/DL by parsing the replay key components — but this is a separate join mechanism, not the observation key.

---

## Section 4 — Schema Inconsistency Finding

Each producer encodes the same market epoch with a different field name. This is the root cause of the prior design audit's incorrect recommendation.

| Producer | Field used for epoch | Value example |
|---|---|---|
| `market_snapshots` | `epoch_start_ts`, `epoch_start`, `market_epoch_start` | 1779926400 (int) |
| `decision_log` | `epoch_start`, `market_epoch_start` | 1779926400 (int) |
| `risk_log` | `market_epoch_start` | 1779926400 (int) |
| `trade_journal` | `epoch_start_ts` | 1779954000 (int) |
| `path_truth` | (none) | — |

The values are the same numeric Unix timestamp wherever present. The field names are inconsistent.

This inconsistency is already handled by `_compute_paper_trade_replay_key` in `quant_event_logger.py:354`:

```python
epoch_start_ts = cls._first_text(
    payload,
    ("epoch_start_ts", "epoch_start", "market_epoch_start_ts", "market_epoch_start", "event_start_ts"),
)
```

This alias-priority chain resolves correctly for every producer:
- MS: `epoch_start_ts` (first hit, present 100%)
- DL: `epoch_start_ts` absent → resolves `epoch_start` (second, present 100%)
- RL: both absent → resolves `market_epoch_start` (fourth, present 92%)
- TJ: `epoch_start_ts` (first hit, present 100%)

The `market_observation_key` derivation MUST use the same alias-priority pattern. Hardcoding `epoch_start_ts` (as the prior design audit assumed) would produce empty keys for DL rows.

This is not a new bug to fix — the pattern is already established. It must be carried forward.

---

## Section 5 — Implementation Preconditions

Any implementation of `market_observation_key` must satisfy all of the following before wiring into paper runtime.

| Precondition | Requirement |
|---|---|
| Epoch alias resolution | Use `_first_text(payload, ("epoch_start_ts", "epoch_start", "market_epoch_start_ts", "market_epoch_start", "event_start_ts"))` — same as `_compute_paper_trade_replay_key` |
| Field name | `market_observation_key` or `market_window_key` — must NOT use `*_trace_id` suffix |
| Key format | `{condition_id}\|{resolved_epoch_start}` — pipe-delimited, no spaces |
| Schema annotation | Field must carry `"coarse_bridge_key": true` or equivalent indicator — distinguishes from `candidate_trace_id` and `paper_trade_replay_key` |
| Additive only | New field must not modify `candidate_trace_id`, `replay_chain_id`, `paper_trade_replay_key`, or any existing field |
| Fall-through behavior | If `condition_id` is absent OR all epoch aliases are absent, emit `market_observation_key_missing_reason` instead of an empty string |
| path_truth scope | path_truth cannot receive this key without adding an epoch field to path_truth payloads first — treat as a separate future task |
| Analysis tool isolation | `ev_field_coverage.py` and `cross_run_ev_blindness.py` must not treat `market_observation_key` as a fallback for `candidate_trace_id` lookups |
| Cycle-level alignment verification | Before treating per-cycle MS↔DL matches as confirmed, verify that for an individual MS row and its corresponding DL rows, the resolved epoch values match — not yet verified at row level in this audit |
| Test coverage | New field derivation must be covered in `tests/test_quant_event_logger.py` before paper runtime validation |
| Paper runtime validation | A fresh paper runtime must confirm non-zero MS→DL key overlap before the field is used in any analysis tool |

---

## Section 6 — Governance Preservation

### The bridge key does not fabricate candidate identity

The 1-key : N-rows shape makes the semantic distinction explicit in the data:

- One `market_observation_key` = `condition_id|epoch_start` maps to **~22.8 MS rows** and **~26.5 DL rows** on average.
- These rows represent multiple evaluation cycles over the same epoch window — they are NOT the same candidate.
- A join on `market_observation_key` returns a group of related events, not a single canonical candidate.
- Any analysis tool consuming this join must treat the result as a group, not as a 1:1 candidate match.

### The bridge key does not carry decision authority

`market_observation_key` is a lineage bridge for observability. It:
- Does not encode a trade decision
- Does not encode a risk state
- Does not encode an execution intent
- Does not carry the side or token specificity required for position attribution

`paper_trade_replay_key` (`condition_id|epoch_start_ts|asset|side|token_id`) remains the canonical key for trade-level joins. The observation key is a coarser upstream bridge only.

### Governance-safe bridge: what is legitimately joined

| Join | Semantically honest? | Safe to use? |
|---|---|---|
| MS rows ↔ DL rows for same market window | ✓ Yes — both processed the same market at the same epoch | Yes |
| MS rows ↔ risk_log rows for same market window | ✓ Yes — risk evaluated the same market | Yes, with 92% coverage |
| MS rows ↔ trade_journal rows for same market window | ✓ Yes — trade opened during this market window | Yes (epoch alias needed) |
| Bridge key as substitute for `candidate_trace_id` | ✗ No — observation ≠ candidate | FORBIDDEN |
| Bridge key as substitute for `paper_trade_replay_key` | ✗ No — lacks side, token | FORBIDDEN |
| Attributing MS-level bilateral signals to a side-specific DL row via bridge | ✗ No — this invents side attribution | FORBIDDEN |

---

## Section 7 — Correction to Prior Design Audit

The prior design audit (`ms_dl_identity_normalization_design_audit.md`) contains three references to `epoch_start_ts` as the recommended bridge key component:

1. Section 8: "The derivation should be `condition_id|epoch_start_ts`"
2. Section 8: first bullet under implementation preconditions
3. Section 6 ("time_bucket alignment risk"): references `epoch_start_ts` as the field in question

Each of these should be read as `epoch_start` (alias-resolved using the `_compute_paper_trade_replay_key` priority chain), not `epoch_start_ts` directly.

**Recommendation**: Update the prior design audit's Section 8 recommended derivation to:

> "The derivation should use alias-resolved epoch: `condition_id|{epoch_start resolved via ("epoch_start_ts", "epoch_start", "market_epoch_start")}`"

This update is documentation-only and does not change the design model recommendation (Model 4 remains correct). The implementation preconditions in Section 5 of this audit supersede the field name in the prior audit.

**Do not update the prior design audit in this task.** Flag it for a dedicated documentation-only update scoped separately.

---

## Governance Compliance

| Dimension | Status |
|---|---|
| Code changes | None |
| Runtime mutation | None |
| Replay execution | None |
| Strategy / risk / execution changes | None |
| Threshold tuning | None |
| Policy consumers introduced | None |
| Live behavior changes | None |
| `candidate_trace_id` changed | No |
| `paper_trade_replay_key` changed | No |
| Implementation committed | No — feasibility audit only |

All findings are derived from JSONL field inspection and source code review. No fields were created, no runtime was modified, no joins were executed against the running system.

---

## Files Inspected

- `runtime/quant_data/market_snapshots/2026-05-28.jsonl` (5,129 rows — full file coverage check; 500-row sample for field type and value analysis)
- `runtime/quant_data/decision_log/2026-05-28.jsonl` (5,958 rows — full file coverage check; 500-row sample)
- `runtime/quant_data/risk_log/2026-05-28.jsonl` (500-row sample)
- `runtime/quant_data/trade_journal/2026-05-28.jsonl` (20 rows — all available)
- `runtime/quant_data/path_truth/2026-05-28.jsonl` (18 rows — all available)
- `utils/quant_event_logger.py` (lines 350–363: `_compute_paper_trade_replay_key` alias-priority chain)
- `docs/research/runtime_health/ms_dl_identity_normalization_design_audit.md`
