# TRADER_PHASE3N_TRADE_EVENT_PAYLOAD_SCHEMA_CONTRACT_001

## 1. Task Identity

- Task: `TRADER_PHASE3N_TRADE_EVENT_PAYLOAD_SCHEMA_CONTRACT_001`
- Task class: 2 DESIGN / SCHEMA CONTRACT
- Primary role: `02_CODE_ARCHITECT_AGENT.md`
- Supporting roles: `07_TEST_CI_AGENT.md`, `11_OBSERVABILITY_INCIDENT_AGENT.md`
- Prior report: `docs/reports/TRADER_PHASE3M_TRADE_EVENT_PAYLOAD_SPLIT_001.md`
- Runtime scope: type annotations and documentation only — no behavior change.

## 2. Final Verdict

`PASS`

TypedDict schema contracts introduced for all extracted trade-event payload builders. No runtime behavior changed. 37 new schema contract tests (including two golden payload snapshots). 891 tests pass (854 prior + 37 new).

## 3. Contracts Module

### `polymarket/observability/contracts.py` (new, 9 TypedDicts)

| TypedDict | Annotates Return Of |
|---|---|
| `EntryModelTruthEnvelope` | Inner envelope dict (field-level schema) |
| `EntryModelTruthEnvelopeWrapper` | `build_entry_model_truth_envelope()` |
| `SizeSharpMetadata` | `size_sharp_metadata()` |
| `SizeSharpCloseCarry` | `size_sharp_close_carry()` |
| `CarryMetadata` | `carry_entry_model_truth_from_metadata()` |
| `TradeOpenContext` | `collect_trade_open_context()` |
| `TradePositionMetadata` | `build_trade_position_metadata()` |
| `TradeOpenedPayload` | `build_trade_opened_payload()` |
| `TradeClosedPayload` | `build_trade_closed_payload()` |

All TypedDicts use `total=False` because several builders use `**spread` operators (phase2_detail, size_sharp_payload, entry_model_truth_envelope) that can add keys beyond those explicitly listed. The declared fields are the stable contract; spread-contributed keys are additive and must not remove declared keys.

### Design Decisions

- **`total=False` universally.** Avoids false negatives from `**spread` patterns in `build_trade_opened_payload` and `build_trade_closed_payload`. TypedDicts serve as documentation and annotation targets, not runtime validators.
- **Two shapes in one TypedDict.** `SizeSharpMetadata` and `CarryMetadata` each cover two possible return shapes (null sentinel vs full payload) using `total=False` rather than Union types. This avoids overloads while still documenting both shapes.
- **`EntryModelTruthEnvelopeWrapper` separate from `EntryModelTruthEnvelope`.** The outer wrapper (`{"entry_model_truth_envelope_v1": {...}}`) and inner dict are distinct TypedDicts — `EntryModelTruthEnvelope` is reused in `TradePositionMetadata.entry_model_truth_envelope_v1`.
- **`carried_from` added to `EntryModelTruthEnvelope`.** `carry_entry_model_truth_from_metadata` adds `carried_from: "position_metadata"` to the inner envelope — documented as an optional field.

## 4. Return Annotations Updated

### `polymarket/observability/trader_reconciliation_carry.py`

| Function | Old Annotation | New Annotation |
|---|---|---|
| `carry_entry_model_truth_from_metadata` | `dict[str, object]` | `CarryMetadata` |
| `size_sharp_metadata` | `dict[str, object]` | `SizeSharpMetadata` |
| `size_sharp_close_carry` | `dict[str, object]` | `SizeSharpCloseCarry` |
| `build_entry_model_truth_envelope` | `dict[str, object]` | `EntryModelTruthEnvelopeWrapper` |
| `build_trade_position_metadata` | `dict[str, object]` | `TradePositionMetadata` |

`build_paper_trade_replay_key` already returns `str` — no change needed.

### `polymarket/observability/trader_trade_event_payload.py`

| Function | Old Annotation | New Annotation |
|---|---|---|
| `collect_trade_open_context` | `dict[str, object]` | `TradeOpenContext` |
| `build_trade_opened_payload` | `dict[str, object]` | `TradeOpenedPayload` |
| `build_trade_closed_payload` | `dict[str, object]` | `TradeClosedPayload` |

## 5. Tests

### `tests/observability/test_trade_payload_schema_contracts.py` (new, 37 tests)

| Test Class | Tests | Purpose |
|---|---|---|
| `TestContractsImportable` | 3 | All TypedDicts importable; annotation types correct |
| `TestCarryMetadataContract` | 4 | `carry_entry_model_truth_from_metadata` shapes |
| `TestSizeSharpMetadataContract` | 3 | `size_sharp_metadata` null vs full shapes |
| `TestSizeSharpCloseCarryContract` | 4 | `size_sharp_close_carry` missing vs carry shapes |
| `TestEntryModelTruthEnvelopeContract` | 5 | `build_entry_model_truth_envelope` truth_status, required fields |
| `TestTradePositionMetadataContract` | 5 | `build_trade_position_metadata` required keys, shadow policy, AIROS fields |
| `TestTradeOpenedPayloadGoldenSnapshot` | 6 | Golden snapshot + no_unexpected_keys + edge cases |
| `TestTradeClosedPayloadGoldenSnapshot` | 7 | Golden snapshot + no_unexpected_keys + spread coverage |

### Golden Payload Snapshots

Two frozen literal dicts (controlled inputs, zero `**spread` contribution) verify exact key sets:

**`_EXPECTED_OPEN_PAYLOAD`** — 31 keys verified:
- Core identity: market_id, ticker, token_id, outcome, side, entry_price, size, notional_size, receipt, strategy, mode, condition_id, epoch_start_ts, asset, paper_trade_replay_key
- Signal fields: signal_name, signal_reason, strategy_signal_name, strategy_signal_reason
- Attribution: position_id, entry_attribution, entry_attribution_status
- Probability: true_probability, fair_value, ev_after_spread, expected_value, ev, confidence
- Spread contribution: size_sharp_close_carry_status
- Capital: bankroll_rank, bankroll_family, capital_score
- Shadow policy: 7 shadow_policy_* fields

**`_EXPECTED_CLOSE_PAYLOAD`** — 50 keys verified:
- Core identity: position_id, market_id, ticker, token_id, outcome, reason, exit_price, exit_timestamp, hold_seconds, size, pnl, pnl_usdc, trade_result, entry_price, partial, receipt, mode, condition_id, epoch_start_ts, asset, paper_trade_replay_key
- Placeholder: candidate_peak_favorable, candidate_peak_adverse
- Entry carry: true_probability, fair_value, ev, ev_after_spread, confidence
- Signal carry: signal_name, signal_reason, strategy_signal_name, strategy_signal_reason
- Position carry: lifecycle_phase, seconds_remaining, bankroll_tier_id, bankroll_family, risk_mode, risk_budget, current_exposure, target_exposure, notional_size, capital_score, capital_state, promotion_candidate, demotion_candidate, expected_risk_profile, bankroll_rank
- Shadow policy: shadow_policy_decision, shadow_policy_observed_ev, shadow_policy_observed_probability, shadow_policy_observed_risk_mode, shadow_policy_id
- Attribution: entry_attribution_status

## 6. Tests Run

| Command | Result |
|---|---|
| `py_compile` (4 modules) | PASS |
| `pytest tests/observability/test_trade_payload_schema_contracts.py -q` | PASS: **37 passed** |
| `pytest tests/observability tests/polymarket -q --tb=short -ra` | PASS: **891 passed**, 5 warnings |

854 tests were passing before this task. 37 new schema contract tests = 891 total.

## 7. AIROS Refresh

Ran after Python module changes:

- `tools\airos\repository_index_generator.py --output-dir docs\operations\repository --pretty`
- `tools\airos\dependency_graph_builder.py --input-dir docs\operations\repository --pretty`
- `tools\airos\repository_navigator.py --input-dir docs\operations\repository --pretty`

Updated: `repository_index.json`, `tool_registry.json`, `test_registry.json`, `repo_health.json`, `dependency_graph.json`, `symbol_index.json` (453 files, +2 from Phase 3M), `navigation.json`.

## 8. Validation

| Item | Result |
|---|---|
| py_compile (4 modules) | PASS |
| 37 focused schema contract tests | PASS |
| 891 acceptance tests | PASS |
| JSON ops files valid | PASS |

## 9. Safety Verdict

`PASS / ANNOTATION-ONLY`

No payload behavior changed. No event emission changed. No trader state mutations. No risk, sizing, execution, or live paths touched. TypedDicts are pure Python `total=False` classes that impose no runtime overhead or behavior change. Return type annotations are documentation only — Python's type system does not enforce them at runtime.

## 10. Module Dependency Direction After Phase 3N

```
trader.py
├── trader_reconciliation_carry.py   (6 carry helpers)
│   ├── typing.Any
│   └── contracts.py                 (TypedDicts — documentation only)
└── trader_trade_event_payload.py    (4 event builders)
    ├── typing.Any
    └── contracts.py                 (TypedDicts — documentation only)

trader_reconciliation_payload.py     (shim, re-exports only)
├── trader_reconciliation_carry.py
└── trader_trade_event_payload.py

contracts.py                         (leaf — no project imports)
└── typing (stdlib only)
```

Clean dependency. No cycles. `contracts.py` is a stdlib-only leaf. Both canonical modules import from it but not from each other.

## 11. Output Fields

| Field | Value |
|---|---|
| FINAL_VERDICT | PASS |
| SCHEMAS_CREATED | `polymarket/observability/contracts.py` (9 TypedDicts) |
| HELPERS_UPDATED | `trader_reconciliation_carry.py` (5 helpers), `trader_trade_event_payload.py` (3 helpers) |
| RETURN_TYPES_UPDATED | 8 functions |
| SNAPSHOT_TESTS | 2 golden snapshots (TradeOpenedPayload: 31 keys, TradeClosedPayload: 50 keys) |
| TESTS_RUN | 891 passed (854 prior + 37 new schema contract tests) |
| SAFETY_VERDICT | PASS / ANNOTATION-ONLY |
| REPOSITORY_STATUS | Clean tree, all tests pass |
| NEXT_TASK | `MARKET_AVAILABILITY_ENGINE_OBSERVABILITY_IMPLEMENTATION_001` |
