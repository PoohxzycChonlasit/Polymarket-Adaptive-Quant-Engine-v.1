# Identity Confidence Gate Root Cause Audit

Date: 2026-05-28
Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
Mode: read-only audit, docs only, no implementation, no runtime mutation.

---

## Executive Finding

**IDENTITY_CONFIDENCE_GATE is not a production runtime gate.** It is a post-hoc classification applied in offline analysis tools (`tools/ev_field_coverage.py`, `tools/cross_run_ev_blindness.py`) when inspecting JSONL evidence. It has never blocked model execution, EV computation, or trade decisions.

The research state file (`runtime/research_state/latest_research_state.md`) is dated 2026-05-11 and reflects a pre-implementation snapshot. The alarming metrics it contains — 961/961 candidates PROXY, MODEL_NOT_ATTEMPTED=848, avg_ev_lifecycle_visibility_score=0.0 — do not reflect current runtime state.

Current runtime state (2026-05-28, verified from live JSONL):

| Producer | lineage_confidence | candidate_trace_id |
|---|---|---|
| `market_snapshots` | DIRECT — 100% | 100% |
| `decision_log` | DIRECT — 100% | 100% |
| `risk_log` (per-candidate rows) | DIRECT — ~91% | 91% |
| `risk_log` (system health rows) | UNKNOWN — ~9% | 0% (correct — no market identity) |
| `trade_journal` | DIRECT — 100% | 100% |
| `path_truth` | WEAK — 100% | 100% |

EV and probability are computed and serialized. `MODEL_OUTPUT_VISIBLE` = 100% of sampled decision_log rows.

---

## Scope

This audit answers seven questions from the task specification:

1. Where should `candidate_trace_id` be created?
2. Where is it missing?
3. Is IDENTITY_CONFIDENCE_GATE correct safety or over-blocking?
4. Is EV/probability computed but not serialized?
5. Which identity fields are canonical now?
6. What is the next smallest safe unlock?
7. What should NOT be changed?

---

## Question 1 — Where Should `candidate_trace_id` Be Created?

`candidate_trace_id` is derived deterministically by `quant_event_logger.py:_candidate_trace_identity_fields()`. The derivation is a SHA1 hash over the resolved values of `TRACE_ID_SOURCE_FIELDS` that are present in the event payload. Generation requires at least one source field from:

```python
TRACE_ID_SOURCE_FIELDS = (
    "market_key", "marketKey", "market_id", "source_market_id",
    "market_slug", "marketSlug", "slug",
    "condition_id", "conditionId",
    "token_id", "tokenId", "clob_token_id", "clobTokenId",
    "yes_token_id", "no_token_id",
)
```

The trace ID should exist on every event that carries market identity — i.e., every event associated with a specific market, token pair, or trade candidate. System-level health events (bankroll state, portfolio state, risk_mode updates) legitimately have no market identity and should emit `candidate_trace_id_missing_reason=no_identity_source_fields`.

**Finding**: The trace derivation site (`_with_candidate_trace_identity()`, lines 159–218) is correct. Trace IDs are generated on all market-associated events.

---

## Question 2 — Where Is `candidate_trace_id` Missing?

### 2a — Legitimately Missing

`risk_log` system health events (approximately 1,907 of 19,888 rows = 9.6%). These carry no market identity fields (`balance_source`, `bankroll_family`, `cash`, `equity`, `event`, `risk_mode`, `open_positions`). `candidate_trace_id_missing_reason=no_identity_source_fields` is the correct classification. This is not a bug.

### 2b — Functionally Present But Cross-Producer Broken

All major producers carry a `candidate_trace_id` value, but the IDs do not match across producer boundaries. This is the critical gap. See Question 3 / Root Cause #1 below.

| Producer pair | Unique IDs (today) | Cross-producer overlap |
|---|---|---|
| `market_snapshots` | 595 | — |
| `decision_log` | 1,157 | — |
| MS → DL | — | **0** (zero overlap) |
| `risk_log` (candidate rows) | 1,153 | — |
| DL → RL | — | 1,155 (near-perfect) |
| DL → `trade_journal` | — | **0** (zero overlap) |

The market_snapshots → decision_log boundary is fully broken. The decision_log → trade_journal boundary is also broken. The decision_log → risk_log boundary is preserved because both operate on the same side-contaminated hash.

---

## Question 3 — Is IDENTITY_CONFIDENCE_GATE Correct Safety or Over-Blocking?

**IDENTITY_CONFIDENCE_GATE is a correct safety classification in offline analysis tools. It is not over-blocking because it does not exist in production.**

Gate location:
- `tools/ev_field_coverage.py:1942`
- `tools/cross_run_ev_blindness.py:66`

Gate trigger condition (ev_field_coverage.py:1936–1942):
```python
trace_confidence = str(lifecycle_trace.get("candidate_trace_confidence") or "UNKNOWN")
if (trace_confidence in {"PROXY", "UNKNOWN"}
    or bool(lifecycle_trace.get("identity_fragmentation_detected"))
    or any(event.get("match_inference") == "market_window_proxy" for event in window_events)):
    gates.add("IDENTITY_CONFIDENCE_GATE")
```

This gate fires in analysis tools when they cannot confidently link pre-model and post-model events to the same candidate lifecycle. When it fires, the tool cannot attribute EV visibility scores to the correct candidate — so it correctly classifies the lifecycle as ungradeable rather than fabricating a false score.

The gate is doing its job correctly. The problem it is detecting (cross-producer identity fragmentation) is real. The gate's existence is not the problem; the root cause of the fragmentation is.

---

## Root Cause #1 — Side Field Carries Decision Direction, Not Token Side

**This is the primary cause of zero cross-producer trace ID overlap.**

`decision_log` payloads have `side='SKIP'` directly in the payload — not via alias fallthrough. This was confirmed by reading raw JSONL rows.

**How `side='SKIP'` ends up in the payload**:

In `polymarket/trader.py:3551`:
```python
candidate_side = str(display.get("side") or display.get("best_side") or display.get("outcome") or outcome.decision)
```

When there is no directional signal (no YES/NO decision), this expression falls through to `outcome.decision` = `"skip"`, yielding `candidate_side="SKIP"`. This is then written to the decision_log payload at line 3753:
```python
"side": str(candidate_side or "UNKNOWN").upper(),
```

**Why the correction in `quant_event_logger.py` does not fix it**:

`quant_event_logger.py` has correction logic at lines 970–978 that can derive YES/NO from `token_id` vs `yes_token_id`/`no_token_id`. However, the final guard at line 977 is:
```python
if enriched.get("side") in {None, "", "BUY", "SELL"}:
    enriched["side"] = outcome
```

`"SKIP"` is not in that set. When `side='SKIP'` arrives pre-set in the payload, the correction does not override it — even though `token_id`, `yes_token_id`, and `no_token_id` are all present and the correct token side (YES or NO) could be derived from them.

**Verified**: On SKIP rows, `token_id` is present in 3,561/3,561 rows. `yes_token_id` and `no_token_id` are also present in all 3,561 rows. For the sample row: `token_id == yes_token_id`, meaning this was a YES-side scan that was skipped — the correct derivable side is YES, not SKIP.

Result: decision_log trace IDs are hashed with `side=SKIP`. market_snapshots trace IDs are hashed with `side=YES/NO` (combined string for both-sided scan). These two hash inputs never match.

| Producer | Side value in trace hash | Source |
|---|---|---|
| `market_snapshots` | `YES/NO` | direct `side` field (combined scan) |
| `decision_log` (SKIP rows) | `SKIP` | `candidate_side` fallthrough to decision direction |
| `decision_log` (YES/NO rows) | `YES` or `NO` | directional signal present |
| `risk_log` (candidate rows) | inherits from decision_log | same contamination pattern |
| `trade_journal` | `BUY` | `side` = order direction |

The contamination is consistent within the decision→risk boundary (both use the same hash), which is why DL ∩ RL = 1,155 but MS ∩ DL = 0.

**Confirmed by sampling**:
- decision_log side distribution (200 rows): SKIP=122, YES=46, NO=32
- market_snapshots side: always `YES/NO`
- trade_journal side: `BUY` (order direction, third distinct value)

---

## Root Cause #2 — Stale Research State

The research state at `runtime/research_state/latest_research_state.md` was last updated 2026-05-11. At that date:

- `candidate_trace_id` was present on 17 of 3,998 events (0.4%)
- `MODEL_NOT_ATTEMPTED=848` was the dominant activation state
- `avg_ev_lifecycle_visibility_score=0.0`
- The side alias implementation and trace derivation wiring were pre-implementation

These metrics caused the alarming interpretation that identity confidence was blocking model attempts. They do not apply to the current codebase.

Current state (2026-05-28):
- `candidate_trace_id` present on 100% of market-associated events across all main producers
- `MODEL_OUTPUT_VISIBLE=1,000/1,000` sampled decision_log rows
- `ev_after_spread` present on 100% of decision_log rows
- `true_probability` non-null on 78/200 rows (null case = `empty_book` — correct)

The stale research state is the reason the task description treated IDENTITY_CONFIDENCE_GATE as if it were a production blocker. It is not.

---

## Question 4 — Is EV/Probability Computed But Not Serialized?

**No. EV and probability are computed and serialized in current runtime.**

Evidence from decision_log (1,000-row sample, today):

| Field | Coverage | Notes |
|---|---|---|
| `model_activation_state` | 1,000/1,000 | all `MODEL_OUTPUT_VISIBLE` |
| `ev_after_spread` | 1,000/1,000 | sometimes 0.0 (computed zero, not null) |
| `true_probability` | 78/200 non-null | null when `true_probability_null_reason=empty_book` |
| `fair_value` | present | |
| EV zero reason | `""` (599), `time_unsafe` (75), `empty_book` (6) | blank = computed zero |

The null `true_probability` cases are correct. When the orderbook is unavailable, there is no bid/ask input for the probability model. `empty_book` as the null reason is the expected safe behavior.

The `MODEL_NOT_ATTEMPTED=848` figure in the research state was from 2026-05-11 pre-implementation data and does not apply now.

---

## Question 5 — Which Identity Fields Are Canonical Now?

The following identity fields are reliably present and correctly valued in current paper runtime:

| Field | Producer(s) | Reliability | Notes |
|---|---|---|---|
| `candidate_trace_id` | All except system health rows | 100% on market events | Hash contaminated by side alias — not cross-producer joinable |
| `condition_id` | All producers | 100% | Clean, cross-producer joinable |
| `market_key` | market_snapshots, decision_log, path_truth | 100% | Clean |
| `lifecycle_instance_id` | path_truth | 100% | |
| `paper_trade_replay_key` | path_truth, decision_log (when trade is open) | 100% on applicable rows | Clean deterministic join key — the working cross-producer join mechanism |
| `parent_candidate_trace_id` | decision_log, trade_journal, risk_log | 100% on applicable rows | Cross-producer value format mismatch (see below) |
| `run_id` | All | 100% | Session-scoped, not market-scoped |
| `lineage_confidence` | All | 100% | Per-event completeness score, not join accuracy |

**`paper_trade_replay_key`** is the canonical cross-producer join key for open trade positions:
```
{condition_id}|{epoch_start_ts}|{asset}|{side}|{token_id}
```
This uses dedicated field lookups (not the alias mechanism) and is unaffected by the side alias conflict. Confirmed working in `docs/research/path_truth_replay_key_live_validation.md`.

**Note on `parent_candidate_trace_id`**:
- decision_log value format: `candidate_75b12751000a` (prefix + hash fragment)
- `candidate_trace_id` value format: `ct_0fe35c81aa8d90c0` (different prefix and length)
- These formats differ — a direct string join between `parent_candidate_trace_id` and `candidate_trace_id` across producers will not match. This is a separate schema inconsistency, not investigated here.

---

## Question 6 — What Is the Next Smallest Safe Unlock?

Ranked by impact and risk:

### Unlock A — Add token-ID-based side derivation in `_candidate_trace_identity_fields` (Smallest, targeted)

**What**: In `quant_event_logger.py:_candidate_trace_identity_fields` (around line 230), after resolving `side` from `TRACE_FIELD_ALIASES["side"]`, add a correction step before building the hash input:

```python
side = cls._first_text(payload, TRACE_FIELD_ALIASES["side"])
# Correct non-YES/NO side values using token_id identity if available
if side and side.upper() not in {"YES", "NO", "YES/NO"}:
    token_id_val = cls._first_text(payload, TRACE_FIELD_ALIASES["token_id"])
    yes_token_id_val = cls._first_text(payload, ("yes_token_id",))
    no_token_id_val = cls._first_text(payload, ("no_token_id",))
    if token_id_val and yes_token_id_val and token_id_val == yes_token_id_val:
        side = "YES"
    elif token_id_val and no_token_id_val and token_id_val == no_token_id_val:
        side = "NO"
```

**Why this location**: `_candidate_trace_identity_fields` is the shared codepath all producers traverse for hash computation. The existing correction at `trader.py:977` (inside `_execution_payload_with_parent_context`) only runs for `log_execution` events — it does NOT run for `log_decision`, `log_market_snapshot`, or `log_trade_open`. Only a fix inside `_candidate_trace_identity_fields` uniformly affects all producers.

**Why it works (within DL→RL boundary)**: For SKIP-outcome decision_log rows, `token_id`, `yes_token_id`, and `no_token_id` are all present (confirmed: 3,561/3,561 SKIP rows have all three fields). The correction can deterministically derive YES or NO from the token identity. This removes the SKIP contamination from the trace hash — producing correct YES/NO side values in the hash for decision_log and risk_log.

**Why it does NOT close the MS→DL gap**: market_snapshots always emits `side='YES/NO'` as a combined string (confirmed: 500/500 rows, 100%). After Unlock A, decision_log SKIP rows would hash with `side='YES'` or `side='NO'` (individual). `'YES'` ≠ `'YES/NO'` as a hash input — the SHA1 output still differs. The MS→DL cross-producer overlap remains 0 after Unlock A alone. Unlock A is a necessary precondition for eventual alignment, not a sufficient fix for this boundary.

**What MS→DL alignment would additionally require**: Either (a) normalize market_snapshots to emit per-direction rows (one row each for YES and NO side), so the hash input uses individual `'YES'` / `'NO'`, or (b) modify `_candidate_trace_identity_fields` to normalize combined `'YES/NO'` to the per-token side before hashing, using `token_id` vs `yes_token_id`/`no_token_id`. Neither is in scope for Unlock A. Both require a separate scoped audit and implementation.

**Effect if implemented**: For SKIP-outcome rows, `side` in the trace hash changes from `'SKIP'` to `'YES'` or `'NO'`. DL→RL overlap is preserved (both producers traverse the same correction). MS→DL overlap remains 0 (side encoding mismatch, see above). The emitted `side` field in decision_log JSONL payloads does NOT change — this fix only affects the hash input, not `enriched["side"]`. Requires a fresh paper runtime to confirm DL→RL overlap is unbroken.

**Side note — trace hash only, not emitted side**: Unlike a fix at trader.py:977, this change does not mutate the `side` field in the emitted payload. The `side='SKIP'` value in decision_log JSONL rows stays as-is. Only `candidate_trace_id` hash changes. Downstream analytics on `side='SKIP'` are unaffected.

**Risk**: Low — hash computation change only. Does not affect EV computation, risk gates, strategy, execution, sizing, or live behavior. Does change `candidate_trace_id` hash values for SKIP-outcome rows, breaking backward continuity with historical trace IDs (correct behavior — old IDs were wrong). Requires test coverage verification in `tests/test_quant_event_logger.py`.

**Scope boundary — DL→RL only**: This fix cleans SKIP contamination within the decision→risk boundary. The MS→DL gap and the DL→TJ gap are separate problems requiring separate solutions.

**Do not implement in this audit.** Requires a dedicated implementation phase with test verification and paper runtime validation.

#### Note: trade_journal DL→TJ gap is a separate codepath problem

`trade_journal` events are emitted via `log_trade_open` with `"side": BUY` explicitly in the payload (trader.py:4519). At the hash computation stage in `_candidate_trace_identity_fields`, `side = "BUY"`. The token-ID correction in Unlock A would also apply here — `token_id`, `yes_token_id`, and `no_token_id` are present in trade_open payloads. The same Unlock A fix, if applied, would also correct `side='BUY'` to YES/NO for trade_journal rows.

However, whether the DL→TJ overlap improves after Unlock A depends on whether `token_id`, `lifecycle_phase`, and `time_bucket` align between the decision and the subsequent trade_open events. This is not verified here. There may also be the same market_snapshots YES/NO combined-string issue if TJ is compared to MS. Trade_journal cross-producer trace analysis should be scoped as a separate audit task.

### Unlock B — Add `token_id` to `path_truth` payloads

**What**: Ensure `path_truth` events carry `token_id` so lineage_confidence reaches STRONG.

**Why it matters**: path_truth currently emits WEAK (has trace + condition_id, missing token_id). Adding token_id would promote to STRONG and enable tighter cross-producer joins.

**Risk**: Low, but path_truth payload changes require a dedicated scoped implementation with paper validation. Lower urgency than Unlock A because `paper_trade_replay_key` already provides an effective join for path_truth rows.

### Unlock C — Update research state (Documentation only, zero risk)

**What**: Update `runtime/research_state/latest_research_state.md` to reflect current state.

**Why it matters**: The stale 2026-05-11 state is actively misleading. It reports metrics that do not exist in current runtime and causes tasks to be scoped around phantom blockers.

**Risk**: None. Documentation update only. Requires a scoped documentation task.

---

## Question 7 — What Should NOT Be Changed?

| Item | Reason |
|---|---|
| `IDENTITY_CONFIDENCE_GATE` in analysis tools | Correctly detects real fragmentation. Remove it only after cross-producer trace overlap is verified. |
| `candidate_trace_id` hash algorithm | Deterministic SHA1 derivation is correct. Only the side field input contamination should be fixed. |
| `TRACE_FIELD_ALIASES["side"]` alias list | Not the primary cause. `side='SKIP'` is directly in the payload, not from alias fallthrough. Changing the alias list alone would have no effect. |
| `trader.py:_execution_payload_with_parent_context` correction guard (line 977) | This runs only for `log_execution`. Extending it would not fix `log_decision` or `log_trade_open` cross-producer gaps. The correct fix is in the shared `_candidate_trace_identity_fields` path. |
| `paper_trade_replay_key` join mechanism | Working and verified. Do not replace with trace-ID-based joins until trace IDs are clean cross-producer. |
| EV/probability computation | Currently correct. `MODEL_OUTPUT_VISIBLE=100%`. Null on empty_book is correct behavior. |
| risk_log UNKNOWN rows | System health events legitimately have no market identity. `no_identity_source_fields` is correct. |
| lineage_confidence classification thresholds | Correct per-event completeness logic. WEAK on path_truth is an accurate report of missing fields, not over-restriction. |
| Any live behavior, strategy, risk, execution, sizing, gates, thresholds | Not within scope of observability/identity work. |

---

## Producer Identity Classification Summary

| Producer | lineage_confidence | Cross-producer joinable | Notes |
|---|---|---|---|
| `market_snapshots` | DIRECT | No — via trace ID | side=YES/NO in hash |
| `decision_log` | DIRECT | No — via trace ID | side=SKIP in hash (alias bug) |
| `risk_log` (candidate) | DIRECT | Partial — DL↔RL only | inherits same side contamination |
| `risk_log` (system) | UNKNOWN | N/A | No market identity, correct |
| `trade_journal` | DIRECT | No — via trace ID | side=BUY in hash |
| `path_truth` | WEAK | Via paper_trade_replay_key | Missing token_id; working join via replay key |
| `execution_log` | DIRECT | Not measured | Not in scope of this audit |

---

## Recommendation on `latest_research_state.md`

**Recommend update in a dedicated scoped task.**

The current state (2026-05-11) contains metrics that are no longer accurate and actively mislead task scoping:

| Stale metric | Current reality |
|---|---|
| candidate_trace_id: 17/3998 (0.4%) | 100% on market events |
| MODEL_NOT_ATTEMPTED=848 | MODEL_OUTPUT_VISIBLE=100% |
| avg_ev_lifecycle_visibility_score=0.0 | EV serialized, score not re-measured |
| 961/961 candidates PROXY | Main producers DIRECT within boundary |
| IDENTITY_CONFIDENCE_GATE as production blocker | Post-hoc analysis tool only |

The update should be scoped as a documentation-only task. It should not be done inline with implementation tasks because the research state update itself requires verifying current metrics from live JSONL before writing, and that work should be its own clean audit.

**Do not update `latest_research_state.md` in this task.** Scope it separately.

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
| Executable truth inferred | No |
| Readiness promoted | No |

This audit is read-only evidence synthesis. All findings are derived from existing JSONL, source code inspection, and cross-producer measurement. No promotion, no implementation.

---

## Files Inspected

- `utils/quant_event_logger.py` (lines 24–348)
- `polymarket/trader.py` (lines 898–989 `_execution_payload_with_parent_context`; 1030–1064 `_emit_quant_event`; 2895–2974 `_phase2_complete_lifecycle_observability`; 3551, 3753; 4197–4254 `_emit_decision_event`; 4505–4535 `log_trade_open` payload)
- `tools/ev_field_coverage.py` (lines 130, 137, 518–523, 1936–1942, 2212–2223)
- `tools/candidate_path_observability.py` (lines 88–105)
- `tools/cross_run_ev_blindness.py` (line 66)
- `runtime/quant_data/decision_log/` (1,000-row sample + SKIP/YES side field verification, today)
- `runtime/quant_data/market_snapshots/` (all rows, today)
- `runtime/quant_data/risk_log/` (all rows, today)
- `runtime/quant_data/trade_journal/` (all rows, today)
- `runtime/quant_data/path_truth/` (all rows, today and 2026-05-27)
- `runtime/research_state/latest_research_state.md`
- `docs/research/path_truth_replay_key_live_validation.md`
