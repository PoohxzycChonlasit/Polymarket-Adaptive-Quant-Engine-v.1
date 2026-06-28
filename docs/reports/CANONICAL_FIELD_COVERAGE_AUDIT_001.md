# CANONICAL_FIELD_COVERAGE_AUDIT_001

**Date:** 2026-06-28  
**Task Class:** 1 AUDIT  
**Status:** COMPLETE

---

## Summary

| Dimension | Value |
|---|---|
| Canonical files audited | 4 |
| Total rows | 1,794 |
| Signal-driven rows (grade A / HIGH conf) | **886** |
| Unique schema fields | **88** |
| Fields at 100% coverage | 30 (34%) |
| Fields at 0% coverage (fully missing) | 22 (25%) |
| Critical backfill targets | **5** |

---

## Dataset Overview

| File | Date Range | Total Rows | Grade A | Grade D | Signal-driven |
|---|---|---|---|---|---|
| `canonical_trade_context_20260523.jsonl` | May 22-23 | 92 | 92 | 0 | 92 |
| `canonical_trade_context_20260531.jsonl` | May 18-31 | 634 | 425 | 208 | 426 |
| `canonical_trade_context_20260614.jsonl` | Jun 1-14 | 170 | 170 | 0 | 170 |
| `canonical_trade_context_20260627.jsonl` | Jun 15-27 | 898 | 198 | 700 | 198 |
| **Total** | **40 days** | **1,794** | **885** | **908** | **886** |

---

## Complete Field Coverage Table

Coverage is computed across **all 1,794 rows**. Signal-driven coverage is the percentage among the **886 signal-driven rows only** (the usable policy backtest set).

### Tier 1 — Full Coverage (100%)

These 30 fields are reliably populated in every row.

| Field | Group | Coverage | Signal-driven |
|---|---|---|---|
| `asset_id` | Telemetry | 100% | 100% |
| `capital_state` | Capital | 100% | 100% |
| `counterfactual_available` | Research | 100% | 100% |
| `data_quality_grade` | Telemetry | 100% | 100% |
| `demotion_candidate` | Capital | 100% | 100% |
| `event_classification` | Telemetry | 100% | 100% |
| `expected_risk_profile` | Risk | 100% | 100% |
| `fill_price` | Execution | 100% | 100% |
| `fill_status` | Execution | 100% | 100% |
| `filled_size` | Execution | 100% | 100% |
| `intended_notional` | Execution | 100% | 100% |
| `intended_price` | Execution | 100% | 100% |
| `intended_size` | Execution | 100% | 100% |
| `inventory_state` | Inventory | 100% | 100% |
| `join_confidence` | Telemetry | 100% | 100% |
| `market_id` | Telemetry | 100% | 100% |
| `missing_fields` | Telemetry | 100% | 100% |
| `order_id` | Execution | 100% | 100% |
| `order_type` | Execution | 100% | 100% |
| `outcome` | Telemetry | 100% | 100% |
| `promotion_candidate` | Capital | 100% | 100% |
| `replay_version` | Telemetry | 100% | 100% |
| `resolved_outcome` | Telemetry | 100% | 100% |
| `risk_mode` | Risk | 100% | 100% |
| `side` | Telemetry | 100% | 100% |
| `slippage` | Execution | 100% | 100% |
| `source_event_ids` | Telemetry | 100% | 100% |
| `source_streams` | Telemetry | 100% | 100% |
| `ticker` | Telemetry | 100% | 100% |
| `timeout_status` | Execution | 100% | 100% |
| `trade_id` | Telemetry | 100% | 100% |

**Notes on Tier 1 semantic gaps (fields present but using defaults):**
- `capital_state`: always `"HEALTHY"` — not computed dynamically
- `counterfactual_available`: always `False`
- `expected_risk_profile`: always `"MODERATE"`
- `inventory_state`: always `"FLAT"` on grade A rows — not tracking inventory state at time of entry
- `market_state`: see Tier 5 (classified as UNKNOWN, not truly populated)
- `position_lifecycle_state`: see Tier 5 (classified as UNKNOWN)

### Tier 2 — High Coverage (95-100%)

| Field | Group | All Rows | Signal-driven | Gap Cause |
|---|---|---|---|---|
| `exit_price` | Execution | 99.8% | 100% | 3 rows missing close event |
| `exit_reason` | Execution | 99.8% | 100% | same 3 rows |
| `exit_timestamp` | Execution | 99.8% | 100% | same 3 rows |
| `hold_seconds` | Execution | 99.7% | 100% | 5 rows with unparseable timestamps |
| `pnl_pct` | Execution | 99.8% | 100% | 3 rows missing pnl |
| `realized_pnl` | Execution | 99.8% | 100% | 3 rows missing close event |
| `reason_codes` | Signal | 99.8% | 100% | 3 rows missing open event |
| `trade_result` | Execution | 99.8% | 100% | 3 rows missing close event |

### Tier 3 — Moderate Coverage (49-78%)

These fields are present on ALL signal-driven rows but absent on all grade D rows, explaining the ~49% overall rate.

| Field | Group | All Rows | Signal-driven | Gap Cause |
|---|---|---|---|---|
| `submitted_at` | Execution | 77.0% | 100% | Missing on 413 grade D rows |
| `position_id` | Telemetry | 61.2% | 99.9% | Not always carried in legacy closes |
| `market_slug` | Telemetry | 49.7% | 100% | Missing on grade D rows |
| `current_exposure` | Capital | 49.6% | 100% | Missing on grade D rows |
| `fair_value` | Signal | 49.6% | 100% | Missing on grade D rows |
| `lifecycle_phase` | Signal | 49.6% | 100% | UNKNOWN for 905 grade D rows |
| `probability` | Signal | 49.6% | 100% | Missing on grade D rows |
| `risk_budget` | Risk | 49.6% | 100% | Missing on grade D rows |
| `seconds_remaining` | Signal | 49.6% | 100% | Missing on grade D rows |
| `target_exposure` | Capital | 49.6% | 100% | Missing on grade D rows |
| `bankroll` | Capital | 49.4% | 99.9% | Missing on grade D rows |
| `bankroll_tier_id` | Bankroll Rank | 49.4% | 99.9% | Missing on grade D rows |
| `equity` | Capital | 49.4% | 99.9% | Missing on grade D rows |
| `ev` | Signal | 49.4% | 100% | Missing on grade D rows |
| `ev_after_spread` | Signal | 49.4% | 100% | Missing on grade D rows |
| `quote_age_ms` | Signal | 49.4% | 100% | Missing on grade D rows |
| `replay_key` | Telemetry | 49.4% | 100% | Missing on grade D rows |
| `grade_d_diagnosis` | Telemetry | 50.6% | n/a | Only set on grade D rows |

**Important:** All Tier 3 fields are 100% present on signal-driven rows. The ~49% overall rate reflects the grade D split only.

### Tier 4 — Partial Coverage (10-55%)

| Field | Group | All Rows | Signal-driven | Gap Cause |
|---|---|---|---|---|
| `mfe_price` | Research | 27.4% | 55.4% | path_truth data missing from May 22-23; partial May 18-31 |
| `mae_price` | Research | 27.4% | 55.4% | same |
| `mfe_usdc` | Research | 27.4% | 55.4% | same |
| `mae_usdc` | Research | 27.4% | 55.4% | same |
| `signal_name` | Signal | 10.8% | 21.8% | Not emitted in early trade_open events; only appears in Jun 15-27 (97%) |
| `decision_score` | Signal | 2.3% | 4.6% | Even more recent addition; Jun 15-27 partial (21%) |

**MFE/MAE by file:**
- May 22-23: 0% (no path_truth stream)
- May 18-31: 29% (partial path_truth)
- Jun 1-14: 100%
- Jun 15-27: 100%

**signal_name and decision_score timeline:**
- May 22-23 and May 18-31: 0% — field not yet emitted
- Jun 1-14: 0% — still not present
- Jun 15-27: signal_name=97%, decision_score=21% — recently added

`ev_after_spread` is identical to `ev` in all 886 signal-driven rows (zero spread deduction applied). The spread is not being subtracted from EV, making this field redundant with `ev`.

### Tier 5 — Zero Coverage (0%)

#### 5A — Always-Default (present as UNKNOWN sentinel, not truly populated)

| Field | Group | Coverage | Default Value | Fix |
|---|---|---|---|---|
| `market_state` | Signal | 0% meaningful | `"UNKNOWN"` always | Requires market regime classifier |
| `position_lifecycle_state` | Execution | 0% meaningful | `"UNKNOWN"` always | Requires lifecycle state machine |
| `size_sharp_bucket` | Size Sharp | 0% meaningful | `"UNKNOWN"` always | Emit from Size Sharp engine |
| `size_sharp_confidence_grade` | Size Sharp | 0% meaningful | `"UNKNOWN"` always | Emit from Size Sharp engine |
| `size_sharp_deployment_state` | Size Sharp | 0% meaningful | `"UNKNOWN"` always | Emit from Size Sharp engine |
| `size_sharp_limiting_factor` | Size Sharp | 0% meaningful | `"UNKNOWN"` always | Emit from Size Sharp engine |
| `size_sharp_schema_version` | Size Sharp | 0% meaningful | `"missing_legacy_metadata"` | Emit from Size Sharp engine |

#### 5B — Never Populated (null/None on every row)

| Field | Group | Coverage | Root Cause |
|---|---|---|---|
| `bankroll_rank` | Bankroll Rank | 0% | Engine implemented; never emitted in trade_open payload |
| `blockers` | Signal | 0% | Not computed/emitted |
| `capital_score` | Capital | 0% | Not implemented |
| `expected_pnl_at_entry` | Risk | 0% | Not computed (requires EV × size at entry) |
| `market_exposure_after` | Inventory | 0% | Not tracked |
| `market_exposure_before` | Inventory | 0% | Not tracked |
| `max_daily_loss_usd` | Risk | 0% | Live-only setting; never populated in paper |
| `max_open_exposure_usd` | Risk | 0% | Live-only setting; never populated in paper |
| `max_order_usd` | Risk | 0% | Live-only setting; never populated in paper |
| `open_position_count` | Inventory | 0% | Not tracked at entry time |
| `realized_pnl_before` | Risk | 0% | Not tracked (would need cumulative PnL state) |
| `size_sharp_at_entry` | Size Sharp | 0% | Engine implemented; never emitted in trade_open payload |
| `size_sharp_boosts` | Size Sharp | 0% | Same |
| `size_sharp_component_scores` | Size Sharp | 0% | Same |
| `size_sharp_hard_caps` | Size Sharp | 0% | Same |
| `size_sharp_missing_inputs` | Size Sharp | 0% | Same |
| `size_sharp_penalties` | Size Sharp | 0% | Same |
| `trade_id` | Telemetry | 100% | ✓ Already populated |
| `unrealized_pnl_before` | Risk | 0% | Not tracked (would need open position value at entry) |

---

## Field Coverage by Group

### Signal Fields (10 fields)

| Field | Coverage (All) | Coverage (Signal) | Status |
|---|---|---|---|
| `ev` | 49.4% | **100%** | ✓ Complete on signal rows |
| `ev_after_spread` | 49.4% | **100%** | ⚠ Present but = ev (spread not deducted) |
| `fair_value` | 49.6% | **100%** | ✓ Complete on signal rows |
| `probability` | 49.6% | **100%** | ✓ Complete on signal rows |
| `seconds_remaining` | 49.6% | **100%** | ✓ Complete on signal rows |
| `lifecycle_phase` | 49.6% | **100%** | ✓ Complete on signal rows |
| `quote_age_ms` | 49.4% | **100%** | ✓ Complete on signal rows |
| `signal_name` | 10.8% | 21.8% | ⚠ Only Jun 15-27 batch |
| `decision_score` | 2.3% | 4.6% | ⚠ Very recent; sparse |
| `market_state` | 0% | 0% | ✗ Always UNKNOWN default |
| `blockers` | 0% | 0% | ✗ Never populated |

### Execution Fields (16 fields)

| Field | Coverage (All) | Coverage (Signal) | Status |
|---|---|---|---|
| `fill_price` | 100% | 100% | ✓ |
| `fill_status` | 100% | 100% | ✓ |
| `filled_size` | 100% | 100% | ✓ |
| `intended_notional` | 100% | 100% | ✓ |
| `intended_price` | 100% | 100% | ✓ |
| `intended_size` | 100% | 100% | ✓ |
| `order_id` | 100% | 100% | ✓ |
| `order_type` | 100% | 100% | ✓ |
| `slippage` | 100% | 100% | ✓ |
| `timeout_status` | 100% | 100% | ✓ |
| `trade_result` | 99.8% | 100% | ✓ |
| `exit_price` | 99.8% | 100% | ✓ |
| `exit_reason` | 99.8% | 100% | ✓ |
| `exit_timestamp` | 99.8% | 100% | ✓ |
| `hold_seconds` | 99.7% | 100% | ✓ |
| `submitted_at` | 77.0% | 100% | ✓ on signal rows |
| `realized_pnl` | 99.8% | 100% | ✓ |
| `pnl_pct` | 99.8% | 100% | ✓ |
| `position_lifecycle_state` | 0% | 0% | ✗ Always UNKNOWN |

### Risk Fields (9 fields)

| Field | Coverage (All) | Coverage (Signal) | Status |
|---|---|---|---|
| `risk_mode` | 100% | 100% | ✓ |
| `expected_risk_profile` | 100% | 100% | ⚠ Always "MODERATE" default |
| `risk_budget` | 49.6% | 100% | ✓ on signal rows |
| `max_order_usd` | 0% | 0% | ✗ Live-only, never populated in paper |
| `max_daily_loss_usd` | 0% | 0% | ✗ Live-only, never populated in paper |
| `max_open_exposure_usd` | 0% | 0% | ✗ Live-only, never populated in paper |
| `expected_pnl_at_entry` | 0% | 0% | ✗ Not computed |
| `realized_pnl_before` | 0% | 0% | ✗ Not tracked |
| `unrealized_pnl_before` | 0% | 0% | ✗ Not tracked |

### Capital Fields (11 fields)

| Field | Coverage (All) | Coverage (Signal) | Status |
|---|---|---|---|
| `capital_state` | 100% | 100% | ⚠ Always "HEALTHY" |
| `promotion_candidate` | 100% | 100% | ✓ |
| `demotion_candidate` | 100% | 100% | ✓ |
| `bankroll` | 49.4% | 99.9% | ✓ on signal rows |
| `equity` | 49.4% | 99.9% | ✓ on signal rows |
| `bankroll_tier_id` | 49.4% | 99.9% | ✓ on signal rows |
| `current_exposure` | 49.6% | 100% | ✓ on signal rows |
| `target_exposure` | 49.6% | 100% | ✓ on signal rows |
| `capital_score` | 0% | 0% | ✗ Not implemented |
| `market_exposure_before` | 0% | 0% | ✗ Not tracked |
| `market_exposure_after` | 0% | 0% | ✗ Not tracked |

### Inventory Fields (4 fields)

| Field | Coverage (All) | Coverage (Signal) | Status |
|---|---|---|---|
| `inventory_state` | 100% | 100% | ⚠ Always "FLAT" (not tracked mid-session) |
| `open_position_count` | 0% | 0% | ✗ Not tracked at entry time |
| `market_exposure_before` | 0% | 0% | ✗ Not tracked |
| `market_exposure_after` | 0% | 0% | ✗ Not tracked |

### Research/MFE/MAE Fields (5 fields)

| Field | Coverage (All) | Coverage (Signal) | Status |
|---|---|---|---|
| `mfe_price` | 27.4% | 55.4% | ⚠ Partial — missing for May 22-23 and partial May 18-31 |
| `mae_price` | 27.4% | 55.4% | ⚠ Same |
| `mfe_usdc` | 27.4% | 55.4% | ⚠ Same |
| `mae_usdc` | 27.4% | 55.4% | ⚠ Same |
| `counterfactual_available` | 100% | 100% | ⚠ Always False |
| `expected_pnl_at_entry` | 0% | 0% | ✗ Not computed |

### Size Sharp Fields (11 fields — all at 0% meaningful coverage)

| Field | Coverage (All) | Coverage (Signal) | Root Cause |
|---|---|---|---|
| `size_sharp_at_entry` | 0% | 0% | Engine built; never emitted in trade_open payload |
| `size_sharp_bucket` | 0% meaningful | 0% | Same (UNKNOWN sentinel) |
| `size_sharp_component_scores` | 0% | 0% | Same |
| `size_sharp_confidence_grade` | 0% meaningful | 0% | Same (UNKNOWN sentinel) |
| `size_sharp_deployment_state` | 0% meaningful | 0% | Same (UNKNOWN sentinel) |
| `size_sharp_hard_caps` | 0% | 0% | Same |
| `size_sharp_limiting_factor` | 0% meaningful | 0% | Same (UNKNOWN sentinel) |
| `size_sharp_missing_inputs` | 0% | 0% | Same |
| `size_sharp_penalties` | 0% | 0% | Same |
| `size_sharp_schema_version` | 0% meaningful | 0% | Same ("missing_legacy_metadata" sentinel) |
| `size_sharp_boosts` | 0% | 0% | Same |

### Bankroll Rank Fields (2 fields)

| Field | Coverage (All) | Coverage (Signal) | Root Cause |
|---|---|---|---|
| `bankroll_rank` | 0% | 0% | Engine built; never emitted in trade_open payload |
| `bankroll_tier_id` | 49.4% | 99.9% | ✓ Present on signal rows — tier populated, rank not |

---

## System Dependencies: Which Missing Fields Block What

### Replay (BacktestEngineV2)

The `ReplayEngine` currently uses: `ev`, `ev_after_spread`, `probability`, `decision_score`, `seconds_remaining`, `risk_mode`, `lifecycle_phase`, `inventory_state`, `risk_budget`, `realized_pnl`, `intended_notional`, `bankroll`, `submitted_at`.

| Required Field | Coverage | Status | Impact if Missing |
|---|---|---|---|
| `ev` | 100% signal | ✓ | — |
| `probability` | 100% signal | ✓ | — |
| `realized_pnl` | 100% signal | ✓ | — |
| `risk_mode` | 100% signal | ✓ | — |
| `lifecycle_phase` | 100% signal | ✓ | — |
| `bankroll` | 99.9% signal | ✓ | — |
| `risk_budget` | 100% signal | ✓ | — |
| `decision_score` | 4.6% signal | ✗ | `min_decision_score` policy filter unusable; filter returns poor results |
| `signal_name` | 21.8% signal | ✗ | Signal-type policy filter only works on Jun 15-27 subset |
| `size_sharp_at_entry` | 0% | ✗ | **Size Sharp policy bucket filters completely blocked** |
| `bankroll_rank` | 0% | ✗ | **Bankroll Rank policy filters completely blocked** |

**Replay verdict: USABLE** for EV/probability/risk_mode/lifecycle_phase policies. **BLOCKED** for Size Sharp and Bankroll Rank policies.

### BacktestEngineV2 PolicyConfig Gaps

| PolicyConfig param | Backing field | Signal coverage | Usable now? |
|---|---|---|---|
| `min_ev` | `ev` | 100% | ✓ Yes |
| `min_ev_after_spread` | `ev_after_spread` | 100% (= ev) | ⚠ Identical to ev — no spread deduction |
| `min_probability` | `probability` | 100% | ✓ Yes |
| `min_decision_score` | `decision_score` | 4.6% | ✗ Sample too small |
| `min_seconds_remaining` | `seconds_remaining` | 100% | ✓ Yes (but negative filter effect found) |
| `risk_mode_allowlist` | `risk_mode` | 100% | ✓ Yes |
| `lifecycle_phase_allowlist` | `lifecycle_phase` | 100% | ✓ Yes |
| `inventory_state_allowlist` | `inventory_state` | 100% | ⚠ Always FLAT |
| `market_state_allowlist` | `market_state` | 0% | ✗ Always UNKNOWN |
| `min_risk_budget` | `risk_budget` | 100% | ✓ Yes |
| `max_position_notional` | `intended_notional` | 100% | ✓ Yes |
| `min_size_sharp` / `max_size_sharp` | `size_sharp_at_entry` | 0% | ✗ **Blocked** |
| `min_bankroll_rank` (future) | `bankroll_rank` | 0% | ✗ **Blocked** |

### Quant Intelligence Engine

The QIE requires calibration data. Key gaps:

| QIE Function | Required Fields | Coverage | Status |
|---|---|---|---|
| Signal calibration | `ev`, `probability`, `realized_pnl` | 100% signal | ✓ Usable |
| MFE/MAE analysis | `mfe_price`, `mae_price` | 55.4% signal | ⚠ Partial (395 rows missing) |
| Stop-loss analysis | `exit_reason`, `hold_seconds` | 100% signal | ✓ Usable |
| EV spread calibration | `ev_after_spread` | 100% (= ev) | ✗ Spread deduction gap |
| Size Sharp calibration | `size_sharp_at_entry` | 0% | ✗ Blocked |
| Bankroll Rank calibration | `bankroll_rank` | 0% | ✗ Blocked |
| Position context | `open_position_count`, `market_exposure_before` | 0% | ✗ Not tracked |
| Regime analysis | `market_state` | 0% | ✗ Always UNKNOWN |

### Size Sharp Validation

**Completely blocked.** All 11 size_sharp fields are either 0% populated or at UNKNOWN/sentinel defaults.

Root cause: The Size Sharp engine is implemented as observability-only — it computes the score during decision evaluation and logs to `decision_log`, but does NOT embed the result in the `trade_open` event payload. The canonical builder's `extract_field()` correctly looks for these fields in event payloads, but they are never written there.

**Required fix:** Emit `size_sharp_at_entry`, `size_sharp_bucket`, `size_sharp_schema_version`, and `size_sharp_deployment_state` in the `trade_open` event payload.

### Bankroll Rank Validation

**Completely blocked.** `bankroll_rank` is 0% populated.

Root cause: Same pattern as Size Sharp — engine implemented, rank computed, but result never embedded in `trade_open` payload.

**Required fix:** Emit `bankroll_rank` in the `trade_open` event payload.

---

## Prioritized Backfill Roadmap

### Priority 1 — Critical / Unblocks Policy Decisions

| Backfill Target | Fields Unlocked | Effort | Risk |
|---|---|---|---|
| **Emit `size_sharp_at_entry` in trade_open payload** | `size_sharp_at_entry`, `size_sharp_bucket`, `size_sharp_deployment_state`, `size_sharp_limiting_factor`, `size_sharp_confidence_grade`, `size_sharp_schema_version` | Low | Observability-only |
| **Emit `bankroll_rank` in trade_open payload** | `bankroll_rank` | Low | Observability-only |

Both are Class 5 OBSERVABILITY tasks. They add fields to the `trade_open` event payload without changing any strategy, risk, or execution behavior. Once emitted, re-running the canonical builder on new sessions will populate these fields.

### Priority 2 — High / Improves QIE Calibration

| Backfill Target | Fields Unlocked | Effort | Risk |
|---|---|---|---|
| **Fix `ev_after_spread` computation** | `ev_after_spread` (currently = `ev`) | Medium | Strategy-adjacent |
| **Emit `signal_name` consistently** | `signal_name` (21.8% → 100%) | Low | Observability-only |
| **Emit `decision_score` consistently** | `decision_score` (4.6% → 100%) | Low | Observability-only |
| **Rebuild May 22-23 with path_truth** | `mfe_price`, `mae_price`, `mfe_usdc`, `mae_usdc` (0% → 100%) | Low | Offline rebuild |

### Priority 3 — Medium / Inventory Context

| Backfill Target | Fields Unlocked | Effort | Risk |
|---|---|---|---|
| **Emit `open_position_count` at entry** | `open_position_count` | Medium | Read-only position tracker query |
| **Emit `market_exposure_before`** | `market_exposure_before` | Medium | Read-only position tracker query |
| **Emit `expected_pnl_at_entry`** | `expected_pnl_at_entry` | Low | Computed: `ev × intended_notional` |

### Priority 4 — Low / Research Only

| Backfill Target | Fields Unlocked | Effort | Risk |
|---|---|---|---|
| **Market State Classifier** | `market_state` | High | New feature |
| **Lifecycle state tracking** | `position_lifecycle_state` | Medium | State machine |
| **Cumulative PnL tracking** | `realized_pnl_before`, `unrealized_pnl_before` | High | Requires session-state carry |
| **Live paper capital limits** | `max_order_usd`, `max_daily_loss_usd`, `max_open_exposure_usd` | Low | Write settings values to payload |

### Priority 5 — Deferred / Not Needed Now

| Field | Reason Deferred |
|---|---|
| `capital_score` | Not implemented; no design spec |
| `counterfactual_available` | Always False; requires counterfactual engine |
| `unrealized_pnl_before` | Requires open position value snapshot at entry |

---

## Grade D Diagnosis Distribution (908 grade D rows)

| Diagnosis | Count | Pct of D | Meaning |
|---|---|---|---|
| `test_event_no_signal_context` | **479** | 52.8% | `exit_reason=test` or round PnL — harness test events |
| `forced_exit_no_replay_key` | 232 | 25.6% | `emergency_flatten`/`forced_exit` — inventory management |
| `close_only_no_replay_key_legacy_schema` | 194 | 21.4% | Pre-telemetry closes — no replay_key emitted |
| `unmatched_unknown` | 3 | 0.3% | Unclassifiable |

**Impact:** The 479 test events are confirmed as false PnL inflation ($302 fake baseline). The 232 forced-exit rows represent real position closures that lack entry metadata and cannot be used for signal-based backtest. The 194 legacy-schema rows represent the pre-telemetry data gap.

---

## Key Semantic Gaps (Fields Present but Misleading)

| Field | Observed Value | Issue | Fix |
|---|---|---|---|
| `ev_after_spread` | Identical to `ev` (0 rows differ) | Spread is not being deducted from EV | Compute `ev - (ask - bid) × side_adjustment` and emit separately |
| `inventory_state` | Always `"FLAT"` | Inventory state was always FLAT at entry — positions not tracked across entries | Emit live inventory state at decision time |
| `market_state` | Always `"UNKNOWN"` | Market State Classifier not yet implemented | Requires classifier feature |
| `position_lifecycle_state` | Always `"UNKNOWN"` | Lifecycle state machine not implemented | Requires lifecycle engine |
| `capital_state` | Always `"HEALTHY"` | Not dynamically computed | Requires capital health scoring |
| `expected_risk_profile` | Always `"MODERATE"` | Not dynamically computed | Requires risk profile engine |

---

## Next Steps

1. **Immediately actionable (Class 5 Observability, no behavior change):**
   - `CANONICAL_TRADE_OPEN_TELEMETRY_BACKFILL_001`: emit `size_sharp_at_entry` + `bankroll_rank` in `trade_open` payload
   - After next paper session: re-run canonical builder → first rows with Size Sharp and Bankroll Rank data

2. **After next paper session:**
   - Re-run `canonical_trade_context_builder.py` to get `signal_name` and `decision_score` consistently
   - Check if May 22-23 date now has path_truth (rebuild for MFE/MAE)

3. **Medium-term:**
   - Fix `ev_after_spread` computation (deduct spread)
   - Add `open_position_count` and `market_exposure_before` to trade_open payload
   - Compute `expected_pnl_at_entry = ev × intended_notional` at entry time

4. **Deferred until market regime classifier is designed and approved:**
   - `market_state` population
   - `position_lifecycle_state` tracking
