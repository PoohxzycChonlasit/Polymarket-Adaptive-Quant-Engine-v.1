# Trade Schema Availability Audit
**Date:** 2026-06-05  
**Role:** Quant Research Auditor (Read-Only)  
**Objective:** Determine whether authoritative data exists to construct the Canonical Trade Table required for Executable Expectancy research.

---

## Source Index

| Source | Log Path | Authority Scope |
|---|---|---|
| **Path Truth** | `runtime/quant_data/path_truth/YYYY-MM-DD.jsonl` | Trade-path mark-price checkpoints, entry price confirmation, session context. **Only event type present: `trade_path_checkpoint`. No completion/settlement records.** |
| **Decision Log** | `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | Signal generation, model probability, intended prices, intended sizing, confidence, EV, regime classification |
| **Replay History** | `tools/replay_analyzer.py` + `docs/research_memory/lifecycle_replay/` | MFE/MAE computation — offline tool only; lifecycle replay memory sparse (2 files, 2026-05-11 only) |
| **Trade Journal** | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | **Cross-check per task hierarchy. De facto source for fill/settlement fields not carried by Path Truth.** See authority gap note below. |

**Data range confirmed:** `path_truth` 2026-05-24 → 2026-06-04. `trade_journal` 2026-05-08 → 2026-06-05.

### Authority Hierarchy Gap — Critical Finding

Path Truth is designated as the authoritative source for fills, realized PnL, fees, and fill timestamps. However, confirmed by field enumeration (`Get-Member` across all path_truth events), **path_truth contains only `trade_path_checkpoint` events**. It does not carry completion records: `filled_size`, `exit_price`, `pnl_usdc`, `hold_seconds`, `exit_timestamp`, or `exit_reason` are absent.

These fields exist only in the Trade Journal (`trade_open` / `trade_close` events). Per the task's source hierarchy the Trade Journal is "cross-check only, never authoritative when conflicting with path truth." Since there is no conflicting path truth record for these fields — the designated authority simply does not carry them — the Trade Journal is the **de facto sole source**, noted explicitly per field below.

---

## Field Availability Table

### Identifiers

| Field | Source | Exists | Authority Level | Reconstruction Possible | Notes |
|---|---|---|---|---|---|
| `trade_id` | `path_truth.payload.trade_id` | ✅ YES | AUTHORITATIVE — Path Truth | — | Present directly in checkpoint payloads. E.g. `"cf9c14b5"`. Also echoed in `trade_journal.payload.position_id` (same value) |
| `market_id` | `decision_log.payload.market_id` | ✅ YES | AUTHORITATIVE — Decision Log | — | `"pm-5m-eth"`, `"pm-5m-btc"`. Present in decision_log; also in trade_journal |
| `series_id` | Not a direct field | ⚠️ PARTIAL | DERIVABLE | YES | Derivable from `market_slug` (e.g. `"eth-updown-5m-1780544700"`) or from `condition_id` + `epoch_start_ts`. Both available in decision_log |

---

### Timestamps

| Field | Source | Exists | Authority Level | Reconstruction Possible | Notes |
|---|---|---|---|---|---|
| `signal_ts` | `decision_log.payload.candidate_created_at` | ⚠️ PARTIAL | RECONSTRUCTABLE | YES | `candidate_created_at` is the signal birth time. Must be joined to trade_journal via `signal_id` / `candidate_id`. Not a single-record lookup |
| `decision_ts` | `decision_log.payload.decision_complete_ts` | ✅ YES | AUTHORITATIVE — Decision Log | — | Also as `decision_timestamp`. Microsecond precision |
| `order_submit_ts` | `trade_journal.payload.receipt.created_at` | ✅ YES | **DE FACTO — Trade Journal** | — | Path Truth carries no submission record. Trade Journal receipt is the only source. E.g. `"2026-06-04T10:46:22.887902"` |
| `first_fill_ts` | `trade_journal.payload.receipt.created_at` | ✅ YES | **DE FACTO — Trade Journal** | — | Paper mode: instantaneous single fill. Same as `order_submit_ts`. Path Truth carries no fill event |
| `exit_signal_ts` | Not logged | ❌ NO | MISSING | NO | No dedicated exit-signal timestamp. `exit_timestamp` is exit-execution time. The SL trigger decision is not separately timestamped |
| `exit_fill_ts` | `trade_journal.payload.exit_timestamp` | ✅ YES | **DE FACTO — Trade Journal** | — | E.g. `"2026-06-04T03:46:54.829997Z"`. Path Truth carries no exit/settlement record |
| `resolution_ts` | Not logged | ❌ NO | MISSING | NO | Market settlement timestamp (YES/NO outcome) not captured. `lifecycle_phase_exited_at` records epoch window close, not market resolution |

---

### Prices

| Field | Source | Exists | Authority Level | Reconstruction Possible | Notes |
|---|---|---|---|---|---|
| `model_prob` | `decision_log.payload.true_probability` | ✅ YES | AUTHORITATIVE — Decision Log | — | E.g. `0.6593643618`. Also `model_probability_yes/no`. Carried into trade_journal via `entry_model_truth_envelope_v1` but decision_log is primary |
| `market_mid_at_decision` | `decision_log.payload.display.*` bid/ask | ⚠️ PARTIAL | RECONSTRUCTABLE | YES | No single `market_mid` field. Derivable as `(ask + bid) / 2` from `display.ask_price` + bid fields in the matched decision_log entry. Requires join by `signal_id` |
| `intended_entry_px` | `decision_log.payload.entry_price` (for approved trades) | ✅ YES | AUTHORITATIVE — Decision Log | — | E.g. `0.5`. Also `execution_log.payload.price`. Decision log emission precedes trade_journal |
| `intended_exit_px` | Not logged | ❌ NO | MISSING | NO | No TP (take-profit) price pre-logged per trade. Stop-loss level is implicit in strategy configuration, not emitted as a named field |
| `avg_entry_fill_px` | `trade_journal.payload.receipt.price` (trade_open) | ✅ YES | **DE FACTO — Trade Journal** | — | Paper: single fill at stated price. `receipt.price = 0.5`. Path Truth carries no fill record |
| `avg_exit_fill_px` | `trade_journal.payload.exit_price` (trade_close) | ✅ YES | **DE FACTO — Trade Journal** | — | E.g. `0.46`. Also `receipt.price` in trade_close. Path Truth has `current_mark_price` at exit checkpoint but this is mark, not fill confirmation |

---

### Counterfactual Path

| Field | Source | Exists | Authority Level | Reconstruction Possible | Notes |
|---|---|---|---|---|---|
| `MFE` | `path_truth` checkpoints — `current_mark_price` sequence | ⚠️ PARTIAL | RECONSTRUCTABLE | YES | `candidate_peak_favorable` is present in trade_open but resolves to `0.0` (initialized, not updated during hold) and `null` in trade_close. Path Truth checkpoints log `current_mark_price` at 15s, 30s, and `event_end`. MFE = max(checkpoints) − entry_price. **Data exists; field not precomputed.** `replay_analyzer.py` lists `mfe_mae_support` as a known coverage gap (lines 119–128) |
| `MAE` | `path_truth` checkpoints — `current_mark_price` sequence | ⚠️ PARTIAL | RECONSTRUCTABLE | YES | Same situation as MFE. `candidate_peak_adverse` is `0.0` / `null`. MAE = entry_price − min(checkpoints). Requires join on `trade_id` across path_truth records |
| `post_stop_reached_tp` | Not logged | ❌ NO | MISSING | NO | Post-exit price path is not tracked. No continuation of path_truth after trade_close |
| `post_stop_path_min` | Not logged | ❌ NO | MISSING | NO | Not tracked |
| `post_stop_path_max` | Not logged | ❌ NO | MISSING | NO | Not tracked |

---

### Size / Fill

| Field | Source | Exists | Authority Level | Reconstruction Possible | Notes |
|---|---|---|---|---|---|
| `intended_size` | `decision_log.payload.notional_size` | ✅ YES | AUTHORITATIVE — Decision Log | — | E.g. `0.050248 USD`. Also `calculated_order_size`. Present in decision records preceding entry |
| `filled_size` | `trade_journal.payload.receipt.filled_size` | ✅ YES | **DE FACTO — Trade Journal** | — | E.g. `0.100496` (shares). `receipt.remaining_size = 0.0` confirms full fill. Path Truth carries no fill record |
| `fill_count` | Not a direct field | ⚠️ PARTIAL | DERIVABLE | YES | Paper mode: always 1 fill per order. No explicit `fill_count` field. Derivable as `1` when `receipt.remaining_size = 0.0` and `status = "paper"` |
| `fill_ratio` | `receipt.filled_size` / `receipt.size` | ⚠️ PARTIAL | DERIVABLE | YES | Both numerator and denominator present in trade_journal receipt. Paper mode always `1.0` |

---

### Costs

| Field | Source | Exists | Authority Level | Reconstruction Possible | Notes |
|---|---|---|---|---|---|
| `entry_fee` | Not logged | ❌ NO | MISSING | PARTIAL | Paper mode does not compute or log fees. Polymarket fee schedule (~1% on the fillable side) is external knowledge; can be imputed as `entry_price × filled_size × fee_rate` but this is an approximation, not realized data |
| `exit_fee` | Not logged | ❌ NO | MISSING | PARTIAL | Same as `entry_fee`. Not applicable in paper mode |
| `entry_spread_bps` | `path_truth.payload.spread` (first checkpoint per trade) | ⚠️ PARTIAL | RECONSTRUCTABLE | YES | Path Truth first checkpoint carries `spread = 0.01` (100 bps in observed examples). Requires join on `trade_id` to identify the opening checkpoint. Decision_log also has bid/ask for derivation but similarly requires a join |
| `exit_spread_bps` | Not reliably available | ❌ NO | MISSING | NO | At SL exit (epoch close), path_truth final checkpoint shows `ask=null, bid=null, spread=null`. The market is gone at exit; spread is not captured |
| `realized_pnl_gross` | `trade_journal.payload.pnl_usdc` (trade_close) | ✅ YES | **DE FACTO — Trade Journal** | — | E.g. `-0.00402 USDC`. Paper mode: no fee deduction. This is gross PnL. Path Truth has `unrealized_pnl` at checkpoints, not final realized PnL |
| `realized_pnl_net` | Same as gross in paper mode | ⚠️ PARTIAL | DERIVABLE | YES | `pnl_net = pnl_gross` is the only meaningful derivation in paper mode (no logged fees). Cannot compute true net without fee imputation |

---

### Context

| Field | Source | Exists | Authority Level | Reconstruction Possible | Notes |
|---|---|---|---|---|---|
| `entry_regime` | `decision_log.payload.market_regime` + `delta_regime` + `trend_regime` + `volatility_regime` | ⚠️ PARTIAL | RECONSTRUCTABLE | YES | Multiple regime sub-fields in decision_log (e.g. `delta_regime: "HIGH"`, `trend_regime`, `volatility_regime`, `regime_reason`). No single canonical field. Requires join to entry decision event via `signal_id` / `candidate_id` |
| `exit_regime` | Not logged | ❌ NO | MISSING | NO | Regime classification absent from trade_close events. Would require joining to a concurrent decision_log event at exit time, which may not exist (exit is SL-triggered, not decision-driven) |
| `session_hour_utc` | `path_truth.payload.session_hour_utc` | ✅ YES | AUTHORITATIVE — Path Truth | — | E.g. `3` (03:00 UTC). Present directly in every path_truth checkpoint |
| `day_of_week` | Derivable from `timestamp_utc` | ⚠️ PARTIAL | DERIVABLE | YES | No direct field. Trivially: `datetime.fromisoformat(timestamp_utc).weekday()`. Available on every event |

---

### Signal Meta

| Field | Source | Exists | Authority Level | Reconstruction Possible | Notes |
|---|---|---|---|---|---|
| `strategy_version` | `trade_journal.payload.strategy` | ⚠️ PARTIAL | DERIVABLE | YES | `strategy = "NORMAL_SCALP"` present. No explicit version string. `run_id` encodes session start (e.g. `20260604T034610Z_58792_76ebb6e9`) and can serve as a version proxy |
| `confidence` | `decision_log.payload.confidence` | ✅ YES | AUTHORITATIVE — Decision Log | — | E.g. `0.5573325799273668`. Also carried in trade_journal via `entry_model_truth_envelope_v1.confidence` |
| `computed_ev` | `decision_log.payload.ev_after_spread` | ✅ YES | AUTHORITATIVE — Decision Log | — | E.g. `0.15936436183558744`. Also `expected_value`. Decision log is primary |

---

### Outcome

| Field | Source | Exists | Authority Level | Reconstruction Possible | Notes |
|---|---|---|---|---|---|
| `exit_reason` | `trade_journal.payload.reason` + `trade_result` | ✅ YES | **DE FACTO — Trade Journal** | — | `reason = "stop_loss_hit"` / `"stop_loss"`, `trade_result = "SL"`. Path Truth carries no exit event |
| `is_win` | Derivable from `pnl_usdc > 0` | ⚠️ PARTIAL | DERIVABLE | YES | `trade_result = "SL"` or `"TP"`. Derivable as `pnl_usdc > 0`. TP exits observed in earlier sessions |
| `hold_duration_s` | `trade_journal.payload.hold_seconds` | ✅ YES | **DE FACTO — Trade Journal** | — | E.g. `31` seconds. Direct field in trade_close. Path Truth last checkpoint `checkpoint_elapsed_s = "event_end"` provides a cross-check |

---

## Field Coverage Summary

| Authority Level | Count | Fields |
|---|---|---|
| **AUTHORITATIVE** (path_truth or decision_log as designated) | 7 | `trade_id` *(path_truth)*, `market_id` *(decision_log)*, `decision_ts` *(decision_log)*, `model_prob` *(decision_log)*, `intended_entry_px` *(decision_log)*, `intended_size` *(decision_log)*, `session_hour_utc` *(path_truth)*, `confidence` *(decision_log)*, `computed_ev` *(decision_log)* |
| **DE FACTO** (trade_journal sole source; path_truth completion records absent) | 9 | `order_submit_ts`, `first_fill_ts`, `exit_fill_ts`, `avg_entry_fill_px`, `avg_exit_fill_px`, `filled_size`, `realized_pnl_gross`, `exit_reason`, `hold_duration_s` |
| **DERIVABLE** (single-expression computation) | 8 | `series_id`, `market_mid_at_decision`, `realized_pnl_net`, `fill_count`, `fill_ratio`, `day_of_week`, `strategy_version`, `is_win` |
| **RECONSTRUCTABLE** (cross-stream join required) | 5 | `signal_ts`, `MFE`, `MAE`, `entry_spread_bps`, `entry_regime` |
| **MISSING** (no data exists) | 10 | `intended_exit_px`, `exit_signal_ts`, `resolution_ts`, `post_stop_reached_tp`, `post_stop_path_min`, `post_stop_path_max`, `entry_fee`, `exit_fee`, `exit_spread_bps`, `exit_regime` |
| **TOTAL** | **39** | *(Note: `fill_count` counted once as DERIVABLE; `realized_pnl_net` counted once as DERIVABLE)* |

> **Authority Gap Summary:** 9 of the 18 source-confirmed fields (those marked DE FACTO) reside only in the Trade Journal — the lowest tier in the task's hierarchy. Path Truth does not emit completion events. This is not a data-loss risk for paper mode (the journal is reliable and internally consistent), but it means the designated authority chain is incomplete at the settlement layer.

---

## Blocking Gaps

Evaluated against minimum requirement: one row per completed trade, with model-predicted edge and realized outcome.

| Gap | Blocks Expectancy? | Reasoning |
|---|---|---|
| `intended_exit_px` | **NO** | Entry and exit price are present. TP target is optional context |
| `exit_signal_ts` | **NO** | Latency analysis is Phase 2. Not required for win/loss expectancy |
| `resolution_ts` | **NO** | Trade outcome captured in `pnl_usdc`; settlement timestamp not needed |
| `exit_spread_bps` | **NO** | Exit spread absent only at epoch-close exits. Entry spread reconstructable |
| `exit_regime` | **NO** | Context enrichment. Entry regime reconstructable and sufficient for initial stratification |
| `entry_fee` / `exit_fee` | **NO** | Paper mode. Fees are zero or imputable. No realized fee data is by design |
| `post_stop_*` | **NO** | Phase 2 / advanced research. Not required for basic expectancy |
| `MFE` / `MAE` | **SOFT BLOCK** | Required for quality-of-execution analysis and distinguishing model-error from stop-size losses. Data exists in path_truth checkpoints. Not a hard blocker — minimal expectancy table constructable without, but analytical depth is limited |
| Path Truth completion records absent | **STRUCTURAL NOTE** | The designated authority tier lacks settlement data. Trade Journal is reliable in practice and internally consistent, but the chain of custody is incomplete. This is a known architectural pattern, not an emergency |

**Hard blockers:** NONE  
**Soft blockers:** MFE and MAE (data in path_truth; precomputation step required)  
**Structural note:** Path Truth authority gap at the settlement layer

---

## Trade Table Readiness Verdict

```
READY_AFTER_RECONSTRUCTION
```

**Rationale:**

The 7 AUTHORITATIVE + 9 DE FACTO fields together cover every required column for a minimal executable expectancy table: trade identity, timestamps (decision/open/close), model probability, entry/exit prices, realized PnL, confidence, EV, hold duration, and exit reason. The 8 DERIVABLE fields add no engineering complexity beyond single expressions on already-present fields.

The 5 RECONSTRUCTABLE fields (signal_ts, MFE, MAE, entry_spread_bps, entry_regime) each require an offline join across JSONL streams, keyed by `trade_id` or `signal_id`. The source data for all five is on disk. The join is mechanical — it is not a data-collection problem.

The 10 MISSING fields are either not applicable to paper mode (fees), Phase 2 research items (post-stop path), or context enrichment rather than expectancy inputs.

---

## Minimal Next Step

> **One offline reconstruction script. No runtime changes. No strategy changes. No data modifications.**

**Scope:** An offline tool (placed in `tools/`) that:
1. Iterates `trade_journal` JSONL files, pairs `trade_open` + `trade_close` by `position_id`
2. Joins `path_truth` checkpoint sequences by `trade_id` → computes MFE and MAE per trade
3. Optionally joins the matched `decision_log` entry by `signal_id` → adds `entry_regime`, `signal_ts`, `market_mid_at_decision`, `entry_spread_bps`
4. Emits one flat CSV row per completed trade

**Join keys:**
- `trade_journal.payload.position_id` == `path_truth.payload.trade_id`
- `trade_journal.payload.signal_id` == `decision_log.payload.signal_id` (to be confirmed in decision_log)

**MFE:** `max(current_mark_price over path_truth checkpoints for trade_id) − entry_price`  
**MAE:** `entry_price − min(current_mark_price over path_truth checkpoints for trade_id)`

**Output dataset date range:** 2026-05-24 → present (`path_truth` start date is the binding constraint)  
**Estimated trade count:** Several hundred (trade_journal 2026-05-29 alone: 1.18 MB at ~14KB/trade pair)

---

## Audit Answers

| Question | Answer |
|---|---|
| Do we already have enough data? | **YES** for 24/39 fields (authoritative + de facto + derivable). **YES with one offline join** for 5 more (reconstructable). No data exists for 10 missing fields |
| Which logs are authoritative? | **Decision Log** for model signals, probability, EV, intended prices/sizes, regime. **Path Truth** for mark-price path, trade_id, session context. **Trade Journal is de facto sole source** for fills/PnL/exit data (Path Truth lacks completion records) |
| What is missing? | Fees (paper mode by design), exit regime, post-stop counterfactual path, TP target price, exit spread at epoch-close |
| Can a completed-trade dataset be built now? | **YES** — 24 of 39 fields immediately available or trivially derivable. MFE/MAE require one join step. Missing fields are not required for expectancy analysis |
| Smallest path to executable expectancy research? | One offline join script in `tools/`. No runtime, strategy, or governance changes. Produce a flat CSV. Begin expectancy analysis immediately. |

---

*Audit generated: 2026-06-05. Read-only. No code, runtime, strategy, risk logic, replay logic, or data modified.*
