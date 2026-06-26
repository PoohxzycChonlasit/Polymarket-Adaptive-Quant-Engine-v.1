# Patch 6B Runtime Evidence Audit (PATCH_006B_RUNTIME_EVIDENCE_AUDIT)

An active paper trading bot process was detected running on the system during the precheck phase.

---

## Precheck Validation

1. **No paper runtime is active**: **FAIL** (Processes `22072` and `43468` are active).
2. **Owner file absent or inactive**: **FAIL** (`paper_runtime_owner.json` status is `"active"` with heartbeat updates).
3. **Logs not growing**: **FAIL** (Active CSV logs are currently being updated by the active PID `22072` and `43468`).
4. **New evidence exists after Patch 6B timestamp**: Checked (Active run started at `2026-06-15T10:42:16Z`).

---

## Verdict

### `BLOCKED_RUNTIME_ACTIVE`

* **Run ID Inspected**: `20260615T104216Z_22072_84713c9d`
* **PID**: `22072` / `43468`
* **Status**: Running / Active
* **Date**: `2026-06-15`

---

## Diagnostic Answers (Provisional Audit)

Even though the precheck failed, we successfully inspected the logs and trade journal to analyze propagation:

### 1. Decision Events Two-Tier Naming
* **Question**: Did new decision events contain `signal_name = PROBABILITY_EV_EDGE`, `signal_reason = yes_ev_above_threshold / no_ev_above_threshold`, `strategy_signal_name`, and `strategy_signal_reason`?
* **Answer**: **YES**. Line 2176 of the decision log `runtime/quant_data/decision_log/2026-06-15.jsonl` contains:
  - `"signal_name": "PROBABILITY_EV_EDGE"`
  - `"signal_reason": "no_ev_above_threshold"` (or `"yes_ev_above_threshold"`)
  - `"strategy_signal_name": "NO_SIGNAL"` (representing the rule-based strategy)
  - `"strategy_signal_reason": "no_strategy_met_threshold"`

### 2. Trade Open Event Two-Tier Naming
* **Question**: Did new trade_open events contain the same two-tier fields?
* **Answer**: **YES**. The `trade_open` event in the trade journal (line 36 of `runtime/quant_data/trade_journal/2026-06-15.jsonl`) contains:
  - `"signal_name": "PROBABILITY_EV_EDGE"`
  - `"signal_reason": "no_ev_above_threshold"`
  - `"strategy_signal_name": "sniper"`
  - `"strategy_signal_reason": "sniper_no_extreme_zscore"`

### 3. Trade Close Event Two-Tier Naming
* **Question**: Did new trade_close events contain the same two-tier fields?
* **Answer**: **YES**. The `trade_close` event in the trade journal (line 37 of `runtime/quant_data/trade_journal/2026-06-15.jsonl`) contains the exact same fields:
  - `"signal_name": "PROBABILITY_EV_EDGE"`
  - `"signal_reason": "no_ev_above_threshold"`
  - `"strategy_signal_name": "sniper"`
  - `"strategy_signal_reason": "sniper_no_extreme_zscore"`

### 4. Entry Attribution Preserves Fields
* **Question**: Does `entry_attribution` preserve all four fields?
* **Answer**: **PARTIAL**.
  - `signal_name` and `signal_reason` are preserved inside the `entry_attribution` nested dictionary.
  - `strategy_signal_name` and `strategy_signal_reason` are **NOT** preserved inside the `entry_attribution` nested dictionary (they are only present at the root level of the event payloads).

### 5. Edge Inventory Report Grouping
* **Question**: Does Edge Inventory Report group new trades under `PROBABILITY_EV_EDGE`?
* **Answer**: **NO**. The new trades from the active session were quarantined under `quarantined_trades` with `quarantine_reason` = `"malformed_attribution"`. This is because `"candidate_trace_id": null` in the `entry_attribution` dictionary, which fails the report tool's strict `IDENTITY_REQUIRED_FIELDS` check. Thus, they are not grouped under `PROBABILITY_EV_EDGE` in the main report summaries.

### 6. Strategy Signal Summary
* **Question**: Does Strategy Signal Summary show `NO_SIGNAL` or other rule-based strategy state?
* **Answer**: **YES**. It groups older legacy trades under `NO_SIGNAL`. For new trades, while they are quarantined, their raw event payloads preserve `strategy_signal_name` at the root (e.g. `"strategy_signal_name": "sniper"` or `"NO_SIGNAL"`).

### 7. Legacy Handling
* **Question**: Are legacy `NO_SIGNAL` trades still handled correctly?
* **Answer**: **YES**. The 10 closed trades from earlier runs today on June 15, which are legacy `NO_SIGNAL` trades, are parsed and handled correctly by the report tool, grouped under `NO_SIGNAL` with a 1.0 complete attribution rate due to the legacy fallback mechanisms.

### 8. Leakage Check
* **Question**: Any leakage into EV/risk/execution behavior?
* **Answer**: **NO**. The modifications are strictly confined to logging/telemetry assignment. All scan cycles, model calculations, risk evaluations, and execution paths continue to function normally.

---

## Detailed Fact Counts for June 15, 2026

* **Run ID Inspected**: `20260615T104216Z_22072_84713c9d`
* **New Decision Count**: 132 decision events containing `PROBABILITY_EV_EDGE` in `decision_log/2026-06-15.jsonl`.
* **New trade_open Count**: 2 (ETH at line 36, BTC at line 38).
* **New trade_close Count**: 2 (ETH at line 37, BTC at line 39).
* **Primary Signal Coverage**: `PROBABILITY_EV_EDGE` (with `yes_ev_above_threshold` / `no_ev_above_threshold`) is 100% on new trade open/close events.
* **Strategy Signal Coverage**: Rules-based strategy names (`sniper`, `NO_SIGNAL`) are 100% preserved in root payloads.
* **Edge Inventory Grouping**: All new trades were quarantined due to `malformed_attribution` (missing `candidate_trace_id` in attribution dict).
* **Legacy Handling**: 100% success on 10 legacy trades.
* **Leakage Check**: No leakage.
