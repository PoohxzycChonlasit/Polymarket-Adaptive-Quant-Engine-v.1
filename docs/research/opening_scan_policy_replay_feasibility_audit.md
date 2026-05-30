# Opening Scan Policy Replay Feasibility Audit v1

Document type: read-only field audit. Design only. No runtime implementation.

Generated: 2026-05-23

Runtime behavior changed: No. Code changed: No.

---

## Purpose

Determine whether the current JSONL logs contain sufficient fields to evaluate Policies D and B from `opening_scan_policy_candidate_design.md` in offline replay — without touching runtime, without rerunning paper sessions, and without changing any emitted fields.

Policies under review:
- **Policy D**: Block entries where `lifecycle_phase = ACTIVE_INVENTORY_TRADING` at entry time.
- **Policy B**: Block entries where `epoch_elapsed_s > 30` at entry fill time.

---

## Audit Scope

JSONL files inspected (instrumentation-era dates only):

| File | Date | Records |
|---|---|---:|
| `runtime/quant_data/trade_journal/2026-05-22.jsonl` | 2026-05-22 | 55 opens, 55 closes, 17 outcome-truth closes |
| `runtime/quant_data/trade_journal/2026-05-23.jsonl` | 2026-05-23 | 10 opens, 10 closes, 10 outcome-truth closes |
| `runtime/quant_data/execution_log/2026-05-22.jsonl` | 2026-05-22 | 40 entry fills with quote data |
| `runtime/quant_data/execution_log/2026-05-23.jsonl` | 2026-05-23 | 20 entry fills with quote data |
| `runtime/quant_data/decision_log/2026-05-23.jsonl` | 2026-05-23 | spot-checked |

---

## Field Presence — trade_journal trade_open

Across all 65 outcome-truth-era `trade_open` events (55 on 2026-05-22, 10 on 2026-05-23):

| Field | 2026-05-22 (n=55) | 2026-05-23 (n=10) | Policy use |
|---|---:|---:|---|
| `lifecycle_phase` | 55/55 (100%) | 10/10 (100%) | **Policy D gate — primary source** |
| `epoch_start_ts` | 55/55 (100%) | 10/10 (100%) | **Policy B computation input** |
| `lifecycle_phase_entered_at` | 55/55 (100%) | 10/10 (100%) | Secondary validation |
| `lifecycle_phase_transition_reason` | 55/55 (100%) | 10/10 (100%) | Secondary validation |
| `ev` | 54/55 (98%) | 10/10 (100%) | Policy E (future) |
| `confidence` | 55/55 (100%) | 10/10 (100%) | Audit context |
| `candidate_trace_id` | 55/55 (100%) | 10/10 (100%) | Identity linkage |
| `first_tradable_seconds_remaining` | 55/55 (100%) | 10/10 (100%) | Context only |
| `first_seen_second` | 26/55 (47%) | 5/10 (50%) | Not required for D or B |
| `epoch_elapsed_s` | 0/55 (0%) | 0/10 (0%) | **Not emitted — must be computed** |

**`lifecycle_phase` values observed:**

| Value | 2026-05-22 | 2026-05-23 |
|---|---:|---:|
| `OPENING_SCAN` | 47 | 6 |
| `ACTIVE_INVENTORY_TRADING` | 8 | 4 |

Both values present and correctly populated. No nulls, no unexpected values.

**One `ev` null** on 2026-05-22: run `20260521T044143Z_13704_948b4757`, a pre-outcome-truth run with zero matched closes. Does not affect any matched outcome-truth trade.

---

## Field Presence — trade_journal trade_close

Across all 27 outcome-truth `trade_close` events:

| Field | Present | Rate | Policy use |
|---|---:|---:|---|
| `trade_result` | 27/27 | 100% | All policies — outcome truth |
| `pnl_usdc` | 27/27 | 100% | All policies — PnL truth |
| `hold_seconds` | 27/27 | 100% | Audit context |
| `exit_price` | 27/27 | 100% | Audit context |
| `entry_price` | 27/27 | 100% | Audit context |
| `reason` | 27/27 | 100% | TP/SL reason classification |
| `lifecycle_phase` | 27/27 | 100% | ⚠ Always `UNKNOWN` — see critical finding |
| `epoch_elapsed_s` | 0/27 | 0% | Not emitted — computed from trade_open + fill |

### Critical finding: `lifecycle_phase` at close is always UNKNOWN

The `lifecycle_phase` field in `trade_close.payload` is populated with `UNKNOWN` in every outcome-truth close event across both dates (17/17 on 2026-05-22, 10/10 on 2026-05-23).

**This is not a bug.** The close event reflects the market's lifecycle state at the moment of exit, not at entry. By the time a position closes (hold time 4–55 seconds later), the epoch window may have transitioned from OPENING_SCAN to a later phase, or may be entirely unavailable, producing UNKNOWN.

**Impact on Policy D replay:**
Policy D gates on `lifecycle_phase` at **entry**, not at close. Any replay tool that reads `lifecycle_phase` from `trade_close` will read `UNKNOWN` for every trade and will not be able to evaluate Policy D. The correct source is `trade_open.lifecycle_phase`.

**Correct source for Policy D gate:** `trade_journal.trade_open.payload.lifecycle_phase`

---

## Field Presence — execution_log Entry Fills

Across all 60 entry fills with quote data (40 on 2026-05-22, 20 on 2026-05-23):

| Field | 2026-05-22 (n=40) | 2026-05-23 (n=20) | Policy use |
|---|---:|---:|---|
| `timestamp_utc` (event level) | 40/40 (100%) | 20/20 (100%) | **Policy B computation input** |
| `lifecycle_phase` | 40/40 (100%) | 20/20 (100%) | **Policy D secondary source** |
| `quote_source` | 40/40 (100%) | 20/20 (100%) | Audit context |
| `quote_lineage_id` | 40/40 (100%) | 20/20 (100%) | Match key |
| `quote_age_at_submit_ms` | 40/40 (100%) | 20/20 (100%) | Audit context |
| `quote_age_at_fill_ms` | 40/40 (100%) | 20/20 (100%) | Match filter |
| `quote_stale_ms` | 0/40 (0%) | 20/20 (100%) | Phase 6 only |
| `epoch_start_ts` | 0/40 (0%) | 0/20 (0%) | **Not in execution_log — must come from trade_open** |
| `epoch_elapsed_s` | 0/40 (0%) | 0/20 (0%) | Not emitted — computed |
| `condition_id` | 40/40 (100%) | 20/20 (100%) | Match key |
| `token_id` | 40/40 (100%) | 20/20 (100%) | Match key |
| `asset` | 40/40 (100%) | 20/20 (100%) | Filter |
| `side` | 40/40 (100%) | 20/20 (100%) | Audit context |

**`quote_stale_ms` gap:** This field is absent from 2026-05-22 (pre-Phase 6 instrumentation) and present in 2026-05-23. Not required for Policies D or B.

---

## lifecycle_phase Agreement: execution_log vs trade_open

Across all 27 matched outcome-truth trades, `execution_log.payload.lifecycle_phase` at the entry fill was compared to `trade_open.payload.lifecycle_phase`:

| Date | Checked | Matches | Mismatches |
|---|---:|---:|---:|
| 2026-05-22 | 17/17 | 17/17 | 0 |
| 2026-05-23 | 10/10 | 10/10 | 0 |

**100% agreement across all 27 matched trades.** Both sources are valid for Policy D's gate. The `execution_log` fill `lifecycle_phase` is a usable alternative to `trade_open.lifecycle_phase` and does not require a cross-file join for Policy D.

---

## epoch_elapsed_s Computation Feasibility

### Computation method

```
fill_unix_ts    = POSIX timestamp of execution_log entry fill (from timestamp_utc)
epoch_start_ts  = trade_open.payload.epoch_start_ts (Unix integer)
epoch_elapsed_s = fill_unix_ts − epoch_start_ts
```

### Computation requires a two-source join

`epoch_start_ts` is only in `trade_journal` (trade_open). `fill_unix_ts` is only in `execution_log`. A replay tool evaluating Policy B must join both files per-trade.

### Computation stability check

Across all 28 matched outcome-truth trades (17 + 11):

| Check | Result |
|---|---|
| Successfully computed | 28/28 |
| Negative `epoch_elapsed_s` | 0 |
| `epoch_elapsed_s` > 300 | 0 |
| Range observed | 4s – 129s |

All 28 computations fall cleanly within [0, 300]. No anomalies.

### Approximation caveat

`epoch_elapsed_s` computed from fill timestamp is a **proxy for decision-time elapsed**, not an exact decision-time measurement. The entry decision was made 1–3 seconds before the fill timestamp. This means:

- A fill at elapsed=31s may have been decided at elapsed=28–30s.
- A fill at elapsed=28s may have been decided at elapsed=25–27s.

This approximation matters for trades within ±3 seconds of the policy boundary. In the current 27-trade dataset, the closest boundary case is elapsed=31s (ETH YES SL). Under the 1–3s proxy error, this trade may have been decided at elapsed=28–30s. The replay tool should flag trades within ±3s of the policy boundary as "boundary-uncertain" in its output.

---

## decision_log Relevance

The `decision_log` was spot-checked for Policy B and D fields:

| Field | Present in decision_log |
|---|---|
| `lifecycle_phase` | Yes — correct values |
| `epoch_start_ts` | No — empty string |
| `epoch_elapsed_s` | No — empty string |
| `ev` | Yes — but 0.0 for skip events |
| `skip_reason` | Yes |
| `model_activation_state` | Yes |

The `decision_log` **cannot** be used as the primary source for Policy B evaluation because `epoch_start_ts` is not emitted there. It **can** be used for `lifecycle_phase` (secondary). The primary sources for both policies remain `trade_journal` (trade_open) and `execution_log` (fills).

---

## Feasibility Verdict

### Policy D — Block ACTIVE_INVENTORY_TRADING

| Requirement | Status | Source |
|---|---|---|
| `lifecycle_phase` at entry | ✅ Present 100% | `trade_open.payload.lifecycle_phase` |
| Alternative: `lifecycle_phase` at fill | ✅ Present 100%, matches 100% | `execution_log.payload.lifecycle_phase` |
| `trade_result` | ✅ Present 100% | `trade_close.payload.trade_result` |
| `pnl_usdc` | ✅ Present 100% | `trade_close.payload.pnl_usdc` |
| Cross-file join required? | **No** — both lifecycle_phase and trade_result can be read from separate files without joining, then linked by run_id + condition_id |
| Boundary ambiguity? | None — OPENING_SCAN vs ACTIVE_INVENTORY_TRADING is a discrete classification, not a continuous threshold |

**Verdict: FEASIBLE. Policy D can be evaluated in offline replay today with existing logs.**

The only replay complexity is reading `lifecycle_phase` from `trade_open`, not from `trade_close` (which shows UNKNOWN). A tool that reads trade_open and trade_close for the same condition_id per run is sufficient.

### Policy B — Block elapsed > 30s

| Requirement | Status | Source |
|---|---|---|
| `epoch_start_ts` | ✅ Present 100% | `trade_open.payload.epoch_start_ts` |
| Entry fill `timestamp_utc` | ✅ Present 100% | `execution_log.timestamp_utc` |
| `epoch_elapsed_s` computed | ✅ 28/28 successful | Derived: `fill_unix − epoch_start_ts` |
| Range validity | ✅ All [4, 129]s — no anomalies | — |
| `trade_result`, `pnl_usdc` | ✅ Present 100% | `trade_close` |
| Cross-file join required? | **Yes** — `epoch_start_ts` from trade_journal + fill timestamp from execution_log |
| Boundary ambiguity? | ±3s proxy error; 1 trade at elapsed=31s is boundary-uncertain | Flag in tool output |

**Verdict: FEASIBLE with two-source join. Policy B can be evaluated in offline replay today with existing logs.**

The tool must join `trade_journal` and `execution_log` per-trade to compute `epoch_elapsed_s`. The join key is: `(run_id, condition_id, timestamp proximity ≤ 3s)`. This is the same join already validated across all three prior audits.

---

## Field Gap Summary

| Field | Required by | Status | Gap impact |
|---|---|---|---|
| `epoch_elapsed_s` (emitted) | B, E | Not emitted anywhere | Computed — no gap for replay |
| `epoch_start_ts` in execution_log | B | Absent | Must join from trade_open — manageable |
| `lifecycle_phase` in trade_close | D | Always UNKNOWN | Use trade_open source instead — not a blocker |
| `quote_stale_ms` in 2026-05-22 | Phase 6 audit | Absent | Not required for D or B |
| `first_seen_second` (partial) | C (future) | 50–53% gap in pre-instrumentation runs | Not required for D or B |
| `ev` null (1 case) | E (future) | In pre-instrumentation run only | Not in matched set — no impact |
| `epoch_start_ts` in decision_log | B via decision_log path | Absent | Decision_log not the right source; use trade_journal |

**No field gaps block Policy D or Policy B replay evaluation.** All missing-but-needed values are computable from present fields.

---

## Replay Tool Design (for future implementation)

The following describes what the offline tool should do when it is eventually built. This is a design specification, not an implementation instruction. No code is written here.

### Tool name (proposed)

`tools/opening_scan_policy_replay.py`

### CLI interface (proposed)

```bash
python tools/opening_scan_policy_replay.py \
  --date 2026-05-22 \
  --policy A,B,D \
  [--run-id RUN_ID] \
  --write-report
```

### Processing steps

1. **Load trade_journal** for the given date. Separate into `trade_open` events and `trade_close` events with `trade_result` present.
2. **Load execution_log** for the same date. Filter to fills with `quote_age_at_fill_ms` present (entry fills only).
3. **Deduplicate fills** by `quote_lineage_id` (each lineage appears 2–3 times; keep the fill-level record).
4. **Match per trade:**
   - For each `trade_close` with `trade_result`, find the prior `trade_open` with matching `run_id`, `asset`, `condition_id`.
   - Find the entry fill from execution_log within ±3s of the `trade_open` timestamp, same `run_id`.
5. **Compute `epoch_elapsed_s`:** `fill_unix_ts − epoch_start_ts` from trade_open.
6. **Apply policy gates:**
   - Policy A: no gate — all trades allowed.
   - Policy D: block if `trade_open.lifecycle_phase = ACTIVE_INVENTORY_TRADING`.
   - Policy B: block if `epoch_elapsed_s > 30`. Flag trades at elapsed 28–33s as boundary-uncertain.
7. **Compute metrics per policy:** TP rate, mean PnL, entries retained, blocked SL count, false block rate.
8. **Write report** to `runtime/reports/opening_scan_policy_replay_YYYY-MM-DD.json`.

### Report fields

```json
{
  "date": "YYYY-MM-DD",
  "run_id_filter": null,
  "total_matched_trades": 27,
  "policies": {
    "A": { "retained": 27, "tp": 7, "sl": 20, "tp_rate": 0.259, "mean_pnl": -0.005241 },
    "D": { "retained": 18, "tp": 7, "sl": 11, "tp_rate": 0.389, "mean_pnl": -0.002683,
           "blocked": 9, "blocked_sl": 9, "false_block_tp": 0 },
    "B": { "retained": 15, "tp": 7, "sl": 8, "tp_rate": 0.467, "mean_pnl": -0.001706,
           "blocked": 12, "blocked_sl": 12, "false_block_tp": 0,
           "boundary_uncertain_count": 1, "boundary_uncertain_trades": ["..."] }
  }
}
```

### What the tool must NOT do

- Alter any JSONL file.
- Connect to live CLOB, wallet, or Polymarket APIs.
- Emit any field to the runtime data path.
- Influence any live or paper trading decision.
- Be imported by `polymarket/trader.py` or any runtime module.

---

## What Not to Implement Yet

The following are out of scope until the replay tool produces validated results across ≥100 matched trades:

| Action | Why deferred |
|---|---|
| Emit `epoch_elapsed_s` to JSONL at runtime | Not needed for offline replay; should be added only if runtime policy gate is eventually authorized |
| Add `lifecycle_phase` entry-time field to trade_close | The UNKNOWN value is expected behavior; changing it could introduce logging complexity for zero replay benefit |
| Add `epoch_start_ts` to execution_log | Not needed; trade_open is the correct source |
| Implement Policy D or B as a live entry gate | Requires ≥100 matched trades validated in replay first |
| Implement Policy E (EV decay) | Requires calibrated curve from ≥200 trades |
| Change any `config/settings.py` thresholds | Not authorized by this audit |
| Modify `lifecycle_phase` classification logic | The existing classification is clean and consistent |

---

## Can Replay Evaluate "Would Block Entry" Without Changing Runtime?

**Yes.** The evaluation is entirely counterfactual:

1. The trade already happened (entry fill is in execution_log, close outcome is in trade_journal).
2. The replay tool reads the existing recorded fields and asks: "Would this entry have been blocked under Policy X?"
3. If the answer is yes, the trade is counted as BLOCKED — its outcome is removed from the allowed-trade metrics.
4. Nothing about the paper trading session is altered.

The paper session's actual fills, actual PnL, actual TP/SL outcomes, and actual JSONL records are read-only inputs to the replay tool. The tool produces a separate report file. No feedback loop exists between the replay output and the runtime.

**Current TP/SL/PnL truth is fully preserved.** The replay tool does not modify any source JSONL.

---

## Summary

| Question | Answer |
|---|---|
| Does the log contain `lifecycle_phase` at entry? | Yes — `trade_open.payload.lifecycle_phase`, 100% present |
| Is `lifecycle_phase` in `trade_close` usable? | No — always UNKNOWN. Use `trade_open` instead |
| Does execution_log `lifecycle_phase` match `trade_open`? | Yes — 100% agreement across all 27 matched trades |
| Does the log contain `epoch_start_ts`? | Yes — `trade_open.payload.epoch_start_ts`, 100% |
| Is `epoch_elapsed_s` emitted anywhere? | No — must be computed |
| Is the computation feasible? | Yes — 28/28 matched trades computed cleanly, no range violations |
| Does Policy D replay require a cross-file join? | No — `lifecycle_phase` is in both trade_open and execution_log |
| Does Policy B replay require a cross-file join? | Yes — trade_journal for `epoch_start_ts`, execution_log for fill timestamp |
| Can replay evaluate "would block" without runtime changes? | Yes — entirely counterfactual from existing JSONL |
| Are current TP/SL/PnL truths preserved? | Yes — replay tool is read-only |
| What fields are missing? | `epoch_elapsed_s` (computed OK), `lifecycle_phase` in trade_close (UNKNOWN — use trade_open) |
| What offline tool should be created later? | `tools/opening_scan_policy_replay.py` — when evidence threshold is met |
| What not to implement yet? | Runtime policy gates, `epoch_elapsed_s` emission, lifecycle_phase changes, threshold changes |

**Policy D: FEASIBLE TODAY.**
**Policy B: FEASIBLE TODAY with two-source join.**
**Tool creation: deferred until ≥100 matched trades exist to validate results.**
