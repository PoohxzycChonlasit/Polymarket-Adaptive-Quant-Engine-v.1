# TRADER_PHASE3L_TRADE_EVENT_PAYLOAD_HELPER_AUDIT_001

## 1. Task Identity

- Task: `TRADER_PHASE3L_TRADE_EVENT_PAYLOAD_HELPER_AUDIT_001`
- Task class: 2 DESIGN / ARCHITECTURE AUDIT
- Primary role: `02_CODE_ARCHITECT_AGENT.md`
- Supporting roles: `07_TEST_CI_AGENT.md`, `11_OBSERVABILITY_INCIDENT_AGENT.md`
- Prior reports:
  - `docs/reports/TRADER_PHASE3F_RECONCILIATION_OBSERVABILITY_EXTRA_001.md`
  - `docs/reports/TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001.md`
  - `docs/reports/TRADER_PHASE3J_TRADE_OPEN_CONTEXT_COLLECTOR_EXTRACTION_001.md`
  - `docs/reports/TRADER_PHASE3K_TRADE_OPEN_PAYLOAD_BUILDER_EXTRACTION_001.md`
- Runtime scope: **design/audit only — no runtime code changes, no file moves**.

## 2. Final Verdict

`PASS / AUDIT_COMPLETE`

`trader_reconciliation_payload.py` has grown from 6 carry/metadata helpers (~350L) at Phase 3F to 10 symbols (~670L) after Phases 3H/3J/3K. The module now spans **6 responsibility domains** and has grown 91% from its creation LOC. The module name is partially misleading for 57% of its current content. Cohesion score is LOW-MEDIUM.

**Recommendation: SPLIT** — extract trade-event payload builders into a new `trader_trade_event_payload.py` module. Schema contracts and golden snapshot tests are both recommended as follow-on work.

## 3. Helpers Inventoried

10 symbols: 9 public functions + 1 private inline helper.

| Symbol | Domain | Coupling Tier | LOC (est.) | Phase Added | Test Count |
|---|---|---|---|---|---|
| `carry_entry_model_truth_from_metadata` | Entry model truth carry | Tier 1 | ~15 | 3F | 1 |
| `build_paper_trade_replay_key` | Replay key builder | Tier 1 | ~10 | 3F | 1 |
| `size_sharp_metadata` | Size sharp formatter | Tier 1 | ~25 | 3F | 1 |
| `size_sharp_close_carry` | Size sharp carry | Tier 1 | ~15 | 3F | 1 |
| `build_entry_model_truth_envelope` | Model truth envelope | Tier 1 | ~90 | 3F | 1 |
| `build_trade_position_metadata` | Position metadata constructor | Tier 1 | ~100 | 3F | 1 |
| `_trade_open_context_value_available` | Private inline guard | Tier 1 | ~5 | 3J | 0 (indirect) |
| `collect_trade_open_context` | Trade-open context collector | Tier 3 | ~160 | 3J | 3 |
| `build_trade_opened_payload` | Trade-open payload builder | Tier 1 | ~80 | 3K | 2 |
| `build_trade_closed_payload` | Trade-closed payload builder | Tier 1 | ~100 | 3H | 4 |

**Totals:** 9 Tier 1 + 1 Tier 3. All symbols covered (9 directly, 1 indirectly via `collect_trade_open_context`).

## 4. Responsibility Map

Six distinct domains in one module:

| Domain | Symbols | LOC (est.) | Phase |
|---|---|---|---|
| **1. Entry model truth** | `carry_entry_model_truth_from_metadata`, `build_entry_model_truth_envelope` | ~105 | 3F |
| **2. Size sharp metadata** | `size_sharp_metadata`, `size_sharp_close_carry` | ~40 | 3F |
| **3. Replay key** | `build_paper_trade_replay_key` | ~10 | 3F |
| **4. Position metadata** | `build_trade_position_metadata` | ~100 | 3F |
| **5. Trade open event** | `_trade_open_context_value_available`, `collect_trade_open_context`, `build_trade_opened_payload` | ~245 | 3J, 3K |
| **6. Trade closed event** | `build_trade_closed_payload` | ~100 | 3H |

Domains 1–4 are all **Phase 3F reconciliation carry** concerns (stateless metadata construction for position tracking). Domains 5–6 are **trade lifecycle event payload builders** (constructing JSONL event dicts emitted by `_emit_trade_opened_event` and `_emit_trade_closed_event`). These two groups have different callers, different lifecycle attachment points, and different future extension vectors.

## 5. Coupling Analysis

| Function | Coupling Tier | trader dependency |
|---|---|---|
| `carry_entry_model_truth_from_metadata` | Tier 1 | None |
| `build_paper_trade_replay_key` | Tier 1 | None |
| `size_sharp_metadata` | Tier 1 | None |
| `size_sharp_close_carry` | Tier 1 | None |
| `build_entry_model_truth_envelope` | Tier 1 | None |
| `build_trade_position_metadata` | Tier 1 | None |
| `_trade_open_context_value_available` | Tier 1 | None (private) |
| `collect_trade_open_context` | **Tier 3** | Reads `trader.last_quant_details`, `trader._runtime_mode()`, `trader._last_bankroll_rank`, `trader._phase2_observability_payload(...)`, `trader._build_paper_trade_replay_key(...)`, `trader._size_sharp_metadata(...)`, `trader._build_entry_model_truth_envelope(...)` |
| `build_trade_opened_payload` | Tier 1 | None |
| `build_trade_closed_payload` | Tier 1 | None |

**9 of 10 symbols are Tier 1 (pure).** The sole Tier 3 function (`collect_trade_open_context`) is the appropriate location for trader state access — it is the intentional boundary where trader runtime state is snapshotted into a plain dict.

`collect_trade_open_context` itself calls five wrapper methods on trader (`_build_paper_trade_replay_key`, `_size_sharp_metadata`, `_build_entry_model_truth_envelope`, `_phase2_observability_payload`, `_build_entry_model_truth_envelope`) — all of which delegate back to Tier 1 helpers in this same module. This creates an internal dependency cycle: the Tier 3 function calls trader wrappers that call back into this module. The cycle is shallow (one hop) and functional, but it means the Tier 3 function is tightly bound to the reconciliation carry helpers at runtime.

## 6. Import Dependency Tree

**Module imports:**
```python
from typing import Any
```
Only stdlib. No polymarket dependencies. The module has zero internal polymarket imports.

**Who imports this module:**
- `polymarket/trader.py` — 9 aliased imports (all public symbols except `_trade_open_context_value_available`)

**Who imports from test files:**
- `tests/observability/test_trader_reconciliation_payload.py` — imports 7 helpers directly
- `tests/observability/test_trader_trade_open_context.py` — imports `collect_trade_open_context`, `build_trade_opened_payload` (inferred from Phase 3J/3K reports; test file confirms context + payload)

**Dependency graph:**
```
trader.py
└── trader_reconciliation_payload.py  (9 aliased imports)
    └── typing.Any  (stdlib only)
```

Clean. No circular imports. The module is a pure leaf in the dependency graph.

## 7. Test Coverage Gaps

| Symbol | Test count | Coverage type |
|---|---|---|
| `carry_entry_model_truth_from_metadata` | 1 | Direct |
| `build_paper_trade_replay_key` | 1 | Direct |
| `size_sharp_metadata` | 1 | Direct |
| `size_sharp_close_carry` | 1 | Direct |
| `build_entry_model_truth_envelope` | 1 | Direct |
| `build_trade_position_metadata` | 1 | Direct + equivalence |
| `_trade_open_context_value_available` | 0 | Indirect (via collect_trade_open_context) |
| `collect_trade_open_context` | 3 | Direct |
| `build_trade_opened_payload` | 2 | Direct |
| `build_trade_closed_payload` | 4 | Direct |

**No zero-coverage gaps for public symbols.** The private inline guard `_trade_open_context_value_available` is exercised indirectly whenever `collect_trade_open_context` runs, but has no isolated unit test. This is acceptable for a private inline.

**Coverage thinness:** The Phase 3F helpers (carry, replay key, size sharp, envelope, position metadata) each have exactly 1 test. These tests verify the happy path. They do not cover edge cases like `None` inputs, missing keys, or type coercion. For production confidence, each of these single-test helpers should receive at least one negative/boundary case.

## 8. Naming Coherence

- **Current name:** `trader_reconciliation_payload.py`
- **"reconciliation"** accurately described the Phase 3F scope: carry-forward of position metadata, size sharp state, model truth envelopes, and replay keys — all supporting the position reconciliation loop.
- After Phases 3H/3J/3K, the module also contains **trade lifecycle event builders** that construct the `log_trade_open` and `log_trade_close` JSONL event payloads. These are fundamentally different from reconciliation carry — they are event emission artifacts, not position tracking artifacts.

**LOC breakdown by name accuracy:**

| Content type | LOC (est.) | Name accurate? |
|---|---|---|
| Reconciliation/carry (Domains 1–4) | ~255 | Yes — "reconciliation_payload" fits |
| Trade event builders (Domains 5–6) | ~345 | No — "reconciliation_payload" does not describe event builders |

Approximately 52% of the module's current LOC is misnamed. A reader browsing the module name in an import block cannot infer that it contains `build_trade_opened_payload` or `build_trade_closed_payload`.

## 9. Growth Trajectory

| Phase | Function added | Cumulative LOC (est.) | Growth |
|---|---|---|---|
| 3F | 6 carry/metadata helpers | ~350 | Baseline |
| 3H | `build_trade_closed_payload` | ~450 | +100L (+29%) |
| 3J | `collect_trade_open_context` + private inline | ~615 | +165L (+37%) |
| 3K | `build_trade_opened_payload` | ~670 | +55L (+9%) |

**Total growth:** +320L in 3 phases from the creation baseline. The module has grown 91% since creation and now exceeds one screenful (~670L). The growth trajectory is driven by trade event builders, not reconciliation helpers.

## 10. Module Cohesion Score

| Dimension | Score | Notes |
|---|---|---|
| Single Responsibility | 2/5 | 6 domains in 1 module |
| Thematic proximity | 3/5 | All trade lifecycle related |
| Coupling purity | 5/5 | 9/10 functions Tier 1 (pure) |
| Name coherence | 2/5 | Name accurate for only 48% of LOC |
| Test depth | 3/5 | Phase 3F helpers have 1 test each; Phase 3H/3J/3K helpers have 3–4 each |

**Weighted overall cohesion: LOW-MEDIUM (3/5)**

The module has excellent coupling purity (almost entirely Tier 1 pure functions) but poor SRP — six domains in one 670L module with a partially misleading name.

## 11. Split Recommendation

**PRIMARY RECOMMENDATION: SPLIT**

Split `trader_reconciliation_payload.py` into two modules:

### Module A: `trader_reconciliation_carry.py` (retain existing filename)
- **Scope:** Phase 3F carry/metadata construction helpers only
- **Content:** `carry_entry_model_truth_from_metadata`, `build_paper_trade_replay_key`, `size_sharp_metadata`, `size_sharp_close_carry`, `build_entry_model_truth_envelope`, `build_trade_position_metadata`
- **LOC (est.):** ~255
- **Coupling:** 6 Tier 1 functions — fully pure
- **Callers in trader.py:** `_opt_carry_entry_model_truth`, `_opt_build_paper_key`, `_opt_size_sharp_meta`, `_opt_size_sharp_carry`, `_opt_build_envelope`, `_opt_build_position_metadata`
- **Tests:** `test_trader_reconciliation_payload.py` — 7 tests targeting these helpers

### Module B: `trader_trade_event_payload.py` (new file)
- **Scope:** Trade lifecycle event payload construction
- **Content:** `_trade_open_context_value_available`, `collect_trade_open_context`, `build_trade_opened_payload`, `build_trade_closed_payload`
- **LOC (est.):** ~345
- **Coupling:** 3 Tier 1 + 1 Tier 3 (`collect_trade_open_context`)
- **Callers in trader.py:** `_opt_collect_trade_open_context`, `_opt_build_trade_opened_payload`, `_opt_build_trade_closed_payload`
- **Tests:** `test_trader_trade_open_context.py` (6 tests) + 4 closed payload tests currently in `test_trader_reconciliation_payload.py`

**Why this split?**

1. **SRP:** Module A contains stateless carry/metadata helpers for position reconciliation. Module B contains event payload builders for trade lifecycle events. These have different callers, different change rates, and different semantic purposes.
2. **Name accuracy:** After the split, both module names will be accurate for 100% of their content.
3. **Size:** Both resulting modules are ~250–350L — within one-screenful readability limit.
4. **Test isolation:** The test split aligns naturally: reconciliation carry tests → `test_trader_reconciliation_payload.py`, event payload tests → `test_trader_trade_event_payload.py`.

**Internal cycle note:** `collect_trade_open_context` currently calls trader wrappers (`trader._size_sharp_metadata`, etc.) that delegate back to Module A helpers. After the split, Module B would import from Module A, making the dependency direction explicit: `trader.py → trader_trade_event_payload.py → trader_reconciliation_carry.py`. This is the correct dependency direction (event builders depend on carry helpers, not vice versa).

## 12. Schema Contract Recommendation

**RECOMMENDATION: ADD** — add TypedDict schema definitions after the split.

Priority targets:

| Dict output | TypedDict name | Justification |
|---|---|---|
| `build_trade_opened_payload` return | `TradeOpenedPayload` | Highest blast radius — goes directly to `log_trade_open` JSONL event |
| `build_trade_closed_payload` return | `TradeClosedPayload` | Second highest — goes to `log_trade_close` JSONL event |
| `build_trade_position_metadata` return | `TradePositionMetadata` | Long-lived metadata attached to every position; key renames are silent regressions |

Implementation approach: create `polymarket/observability/trader_trade_payload_schema.py` containing the three TypedDicts. Import them as return type annotations in the two split modules. Zero runtime impact — TypedDicts are erased at runtime.

## 13. Golden Snapshot Recommendation

**RECOMMENDATION: ADD** — add frozen JSON fixture snapshots for the two highest-blast-radius payload builders.

Priority targets:

| Function | Fixture file | Trigger |
|---|---|---|
| `build_trade_opened_payload` | `tests/fixtures/trade_opened_payload_golden.json` | Any key added, renamed, or removed triggers test failure |
| `build_trade_closed_payload` | `tests/fixtures/trade_closed_payload_golden.json` | Any key added, renamed, or removed triggers test failure |

These two functions produce the canonical JSONL event dicts that downstream tools (`backtest_engine_v2`, `canonical_trade_context_builder`, QIE) parse. Silent key regressions are the highest-risk failure mode. Golden snapshots catch them with zero maintenance cost once the fixture is committed.

**Implementation:** after the split, add one test class per builder that reads the golden JSON from disk and asserts `output == golden`. Regenerate the fixture by running the builder with a controlled input and writing the output. Pin the fixture to git.

## 14. Validation

| Item | Status |
|---|---|
| All 4 prior phase reports read | PASS |
| Module fully read (669 LOC) | PASS |
| Both test files inspected (18 tests collected) | PASS |
| Import block in trader.py confirmed (9 aliases) | PASS |
| Caller count confirmed (18 call sites) | PASS |
| git status — clean tree | CONFIRMED |

No runtime code was modified in this task.

## 15. Safety Verdict

`PASS / DESIGN-ONLY`

No runtime code, no test code, no module files were created or modified. This report is a documentation artifact only. All findings are derived from static analysis of existing committed code.

## 16. Output Fields

| Field | Value |
|---|---|
| FINAL_VERDICT | PASS / AUDIT_COMPLETE |
| HELPERS_INVENTORIED | 10 (9 public + 1 private inline) |
| RESPONSIBILITY_MAP | 6 domains — see Section 4 |
| MODULE_COHESION_SCORE | LOW-MEDIUM (3/5) |
| SPLIT_RECOMMENDATION | SPLIT — into `trader_reconciliation_carry.py` (retain) + `trader_trade_event_payload.py` (new) |
| SCHEMA_CONTRACT_RECOMMENDATION | ADD — TypedDict definitions for `TradeOpenedPayload`, `TradeClosedPayload`, `TradePositionMetadata` in a new `trader_trade_payload_schema.py` |
| GOLDEN_SNAPSHOT_RECOMMENDATION | ADD — frozen JSON fixtures for `build_trade_opened_payload` and `build_trade_closed_payload` |
| NEXT_EXECUTABLE_TASK | `TRADER_PHASE3M_TRADE_EVENT_PAYLOAD_SPLIT_001` |
| REPOSITORY_STATUS | Clean tree, 851 tests passing (observability + polymarket suites) |
