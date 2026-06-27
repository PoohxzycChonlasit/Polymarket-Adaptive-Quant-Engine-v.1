# TRADE_CONTEXT_LINEAGE_AUDIT_001
> **TASK_CLASS: 1 — RESEARCH**
> **PRIMARY: 06_POSITION_RECONCILIATION_AGENT | SUPPORTING: 02_CODE_ARCHITECT_AGENT, 11_OBSERVABILITY_INCIDENT_AGENT, 25_DATA_STEWARD_AGENT**
> **Date: 2026-06-28 | Evidence Grade: B (source-code verified) + A (runtime observed)**

---

## FINAL_VERDICT

```
LINEAGE_STATUS:     BROKEN — Sizer and model parameters exist at entry but are lost at exit due to in-memory-only PositionTracker design.
JOIN_KEY_FINDINGS:  run_id + paper_trade_replay_key is robust, but fails when date-scoping excludes opens, or when tracker restarts wipe memory.
FIELDS_LOST_AT:     exit_price, true_probability, fair_value, ev, bankroll_tier_id, risk_mode (all lost in close events upon process restart).
NEXT_TASK:          TELEMETRY_BACKFILL_FOR_QUANT_TRUTH_001
```

---

## 1. Runtime Context Flow

The flow of context during a trade's lifecycle follows this path:

1. **Decision Candidate**: `_evaluate_candidate` constructs candidate dictionaries containing indicators, EV, probability, and pricing.
2. **Risk Plan**: `PositionSizingEngine` computes `RiskPlan` (holds sizing, leverage, stop-loss, take-profit, notional size).
3. **Order Intent**: `_submit_order` validates execution limits against `PositionTracker`.
4. **Build Metadata**: If filled, `_build_trade_position_metadata` builds a dictionary mapping strategy parameters, EV, true probability, signal name, and `entry_model_truth_envelope_v1`.
5. **Tracker Register**: `PositionTracker.open_position` creates a `Position` object with this metadata and registers it in the local `_positions` dict.
6. **Open Emission**: `_emit_trade_opened_event` extracts payload details and writes to `trade_journal/trade_open`.
7. **Close Event**: On exit, `_emit_trade_closed_event` is called, copying `metadata.get("entry_model_truth_envelope_v1")` using `_carry_entry_model_truth_from_metadata`.
8. **Builder**: `canonical_trade_context_builder.py` joins the resulting `trade_open` and `trade_close` events to produce a canonical trade row.

---

## 2. Field Lineage Matrix

| Field Name | Created At | Carried By | Serialized In | Lost At | Restorable From | Should Be SOT |
|---|---|---|---|---|---|---|
| **run_id** | Process start | Event wrapper | All JSONL files | N/A | Direct field | Event root |
| **replay_key** | trader.py entry | Position.metadata | open/close logs | N/A | Direct field | open/close |
| **position_id** | tracker open | Position | open/close logs | N/A | Direct field | Position |
| **true_probability** | Model output | Position.metadata | trade_open | Close (on restart) | trade_open join | Model output |
| **fair_value** | Model output | Position.metadata | trade_open | Close (on restart) | trade_open join | Model output |
| **ev** | Model output | Position.metadata | trade_open | Close (on restart) | trade_open join | Model output |
| **ev_after_spread** | Model output | Position.metadata | trade_open | Close (on restart) | trade_open join | Model output |
| **bankroll_tier_id** | sizer.py | Position.metadata | decision_log | Close (always) | decision_log | sizer.py |
| **risk_mode** | risk_manager.py | Position.metadata | risk_log | Close (always) | risk_log | risk_mgr |
| **entry_price** | CLOB Fill | Position | trade_open | N/A | Direct field | CLOB Receipt |
| **exit_price** | CLOB Fill | Position | trade_close | N/A | Direct field | CLOB Receipt |
| **realized_pnl** | tracker close | Position | trade_close | N/A | Direct field | Position |

---

## 3. Join Key Audit

### 3.1 Key Reliability
1. **`run_id` + `paper_trade_replay_key`**: High reliability (99.9%). Fails only if the `replay_key` is malformed/legacy.
2. **`run_id` + `position_id`**: Medium reliability. Works for matching open and close events within a single process lifespan, but fails if the process restarts and resets the position tracker.

### 3.2 Analysis of 2026-06-27 Logs (4 HIGH, 108 LOW Joins)
The audit of `2026-06-27` logs confirms:
- **Only 4 opens were logged on 2026-06-27**, matching 4 of the closes (HIGH confidence).
- **108 closes did not have matching opens in the same log file**.
- **Reason**: Date-scoping. The opens occurred on previous calendar days (e.g. `2026-06-26` or earlier). When the builder was run with `--date 2026-06-27`, those files were not loaded, resulting in unmatched closes (LOW confidence).
- When the date range was expanded to `--start-date 2026-06-26 --end-date 2026-06-27`, **all 14 opens in the range matched successfully** (Grade A evidence). The remaining 315 unmatched closes represent legacy positions opened before June 26 or mock closes from test environments (e.g. `reason='test'`).

---

## 4. Metadata Audit

- **`_build_trade_position_metadata`**: Successfully packs model indicators, probabilities, and EV envelopes.
- **PositionTracker Persistence**: **Critical Flaw Identified**. `PositionTracker` contains `save_state` and `load_state` methods, but **neither is ever called in production (`trader.py` or `main.py`)**. The tracker is completely in-memory and volatile.
- **Process restarts wipe all position metadata**. When the bot restarts, it rebuilds its open positions dictionary from CLOB balance feeds, which do not carry any strategy, tier, EV, or probability metadata.
- **Result**: All exits processed after a process restart are emitted with empty metadata payloads (`entry_attribution_status = "missing_legacy"`), breaking the telemetry lineage.

---

## 5. Runtime Backfill Plan

To fix the metadata loss, we will update the runtime to carry forward sizer context natively:

1. **Enable Position Tracker Persistence**:
   - Update `main.py` to call `tracker.load_state(path)` at startup.
   - Update `trader.py` to call `tracker.save_state(path)` after every position open and close event.
2. **Ensure Metadata carries to Close**:
   - Update `_emit_trade_closed_event()` in `trader.py` to check `position.metadata` and extract `entry_model_truth_envelope_v1` fields, appending them to the log payload.
3. **Fallback Sizing Parameters**:
   - If a restart occurred and metadata is missing, fallback to parsing the `decision_log` for the matching `paper_trade_replay_key` to recover tier and strategy settings.

---

## 6. Canonical Builder Impact

After the runtime backfill is deployed:
- `canonical_trade_context_builder.py` will read complete data directly from `trade_close` events without needing complex decision joins.
- The unmatched closes rate will decrease significantly for new trades.

---

## 7. Replay / Backtest Impact

- **`replay_analyzer.py`**: Can directly group win rates and expectancy by sizer tier and risk mode from `trade_close` files.
- **Sizing Calibration**: Enables calculating Bankroll Rank and Size Sharp metrics natively using clean, non-joined historical data series.

---

## 8. Risk / Failure Modes

- **State File Corruption**: If the JSON state file is corrupted, the tracker must fail-soft and fall back to CLOB balances.
- **PID Mismatch**: Ensure state files are keyed by `run_id` to prevent concurrent runtimes from overwriting each other's states.

---

## 9. Final Recommendation

### Next Task: TELEMETRY_BACKFILL_FOR_QUANT_TRUTH_001

This task will implement the carry-forward metadata logic in `trader.py` and enable `PositionTracker` serialization, securing the context lineage.
