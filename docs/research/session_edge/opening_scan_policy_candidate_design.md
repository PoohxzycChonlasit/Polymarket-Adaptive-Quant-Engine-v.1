# Opening Scan Policy Candidate Design v1

Document type: design-only, read-only evidence design. No runtime implementation.

Generated: 2026-05-23

Runtime behavior changed: No. Code changed: No.

---

## Context

Three offline audits established the following evidence chain:

| Audit | Key finding |
|---|---|
| `quote_source_outcome_audit.md` | `display_snapshot_sampling` appeared to outperform `decision_cycle_fetch` (50% vs 17.6% TP rate). Flagged as likely confound. |
| `epoch_timing_outcome_audit.md` | Timing is the primary variable. All 7 TP trades occurred within the first 30 seconds of their epoch window. Zero TP after 30s. The quote-source gap was an artifact. |
| `opening_scan_survival_audit.md` | Verdict: `OPENING_SCAN_EDGE_CANDIDATE`. ETH-only TP signal. 30-second survival cliff. `ACTIVE_INVENTORY_TRADING` = 0/9 TP. EV blind to epoch timing. n=27, insufficient for statistical conclusions. |

This document designs five policy candidates for future offline replay evaluation. None are implemented. None are authorized for runtime use.

---

## Design Principles

A candidate policy is well-formed if it satisfies all four conditions:

1. **Observable.** The gate condition can be computed from fields already emitted to JSONL. No new runtime instrumentation required for replay evaluation.
2. **Non-destructive.** The policy filters or adjusts entries; it does not change signal computation, risk sizing, fair-value logic, or exit behavior.
3. **Falsifiable.** There is a specific metric (TP rate, mean PnL, blocked-entry rate) that would disconfirm the policy's hypothesis at sufficient sample size.
4. **Evidence-gated.** The policy has an explicit evidence threshold that must be met before runtime consideration is permitted.

---

## Policy A — Baseline (Current Behavior)

### Definition

No timing restriction. Entries are allowed at any `epoch_elapsed_s` value, in any lifecycle phase, at any EV level above the existing threshold.

### Gate condition

None. All entries that pass existing signal, risk, EV, and cutoff gates proceed to execution.

### Observed behavior (n=27)

| Metric | Value |
|---|---|
| Total entries | 27 |
| TP | 7 |
| SL | 20 |
| TP rate | 25.9% |
| Mean PnL | −0.005241 |
| OPENING_SCAN entries | 18 |
| ACTIVE_INVENTORY_TRADING entries | 9 |
| Entries at elapsed >30s | 12 |
| TP from entries at elapsed >30s | 0 |

### Role in replay

Policy A is the baseline comparator. All other policies are evaluated against A. Any policy that does not outperform A on TP rate and mean PnL in replay is disqualified.

---

## Policy B — Opening-Only Entry (0–30s Window)

### Definition

Allow new entries only when `epoch_elapsed_s ≤ 30` at the time of the entry fill. Block all entries where more than 30 seconds have elapsed since `epoch_start_ts`.

### Gate condition

```
ALLOW entry  if  epoch_elapsed_s ≤ 30
BLOCK entry  if  epoch_elapsed_s > 30
```

### Hypothesis

The apparent TP rate advantage of very early entries reflects a real opening-scan pricing dislocation in 5-minute Polymarket prediction windows. After 30 seconds of active trading, the dislocation is absorbed and the edge expires. Entries after this point produce only losses in the current evidence set.

### Simulated effect on current 27-trade dataset

| Metric | Policy A | Policy B | Delta |
|---|---:|---:|---:|
| Entries | 27 | 15 | −12 |
| TP | 7 | 7 | 0 |
| SL | 20 | 8 | −12 |
| TP rate | 25.9% | 46.7% | +20.8pp |
| Mean PnL | −0.005241 | −0.001706 | +0.003535 |
| Blocked entries | 0 | 12 | — |
| All blocked entries were SL | — | Yes (12/12) | — |

The 12 blocked entries under Policy B are all SL in the current dataset. None were TP. Mean PnL improves from −0.005241 to −0.001706.

### Required replay fields

| Field | Source | Note |
|---|---|---|
| `epoch_elapsed_s` | Computed: `fill_ts_unix − epoch_start_ts` | Already derivable from execution_log fill ts + trade_journal epoch_start_ts |
| `epoch_start_ts` | `trade_journal.trade_open.payload.epoch_start_ts` | Present and populated |
| `trade_result` | `trade_journal.trade_close.payload.trade_result` | Present in instrumentation era |
| `pnl_usdc` | `trade_journal.trade_close.payload.pnl_usdc` | Present in instrumentation era |
| `lifecycle_phase` | `trade_journal.trade_open.payload.lifecycle_phase` | Present; secondary validation |

### Key risks

| Risk | Severity | Notes |
|---|---|---|
| 30-second boundary is from 27 trades | High | May not hold across sessions, regimes, or assets |
| ETH-only TP pattern — generalization unknown | High | 0 BTC TP in any window; policy treats ETH and BTC identically |
| Blocks potentially valid entries at elapsed 31–35s (OPENING_SCAN) | Medium | Elapsed 31s and 35s are both OPENING_SCAN lifecycle but both SL in current data |
| Reduces total entry volume, reducing learning signal | Medium | Fewer entries means slower evidence accumulation for future audits |
| 30-second cliff may be a regime artifact | Medium | If both audit sessions shared a common market structure, the cliff may not be structural |
| Within 0–30s, 8/15 entries are still SL (53%) | Medium | Policy B does not eliminate SL; it only removes the worst-timing cohort |
| No TP baseline possible if edge is narrow | Low | If real edge is only 0–7s, Policy B is still too permissive |

### Evidence required before runtime consideration

- ≥ 100 matched trades with `epoch_elapsed_s`
- ≥ 20 ETH TP trades in the 0–30s window across ≥ 5 distinct dates
- 0–30s TP rate ≥ 35% sustained across the expanded dataset
- Zero TP at elapsed > 30s in the expanded dataset, or TP rate at elapsed > 30s < 10%
- Explicit operator sign-off after offline replay evaluation

---

## Policy C — Ultra-Opening Entry (0–7s Window)

### Definition

Allow new entries only when `epoch_elapsed_s ≤ 7`. All entries after 7 seconds elapsed are blocked.

### Gate condition

```
ALLOW entry  if  epoch_elapsed_s ≤ 7
BLOCK entry  if  epoch_elapsed_s > 7
```

### Hypothesis

The highest TP rate is concentrated in the first 7 seconds of an epoch window, capturing a brief window of maximum market dislocation at epoch open before any decision-cycle CLOB fetch has been issued. The opening spread normalizes within the first few seconds; entries after 7 seconds face a market that has already begun re-equilibrating. Restricting to this window maximizes the signal-to-noise ratio of entries.

### Simulated effect on current 27-trade dataset

| Metric | Policy A | Policy C | Delta |
|---|---:|---:|---:|
| Entries | 27 | 3 | −24 |
| TP | 7 | 2 | −5 |
| SL | 20 | 1 | −19 |
| TP rate | 25.9% | 66.7% | +40.8pp |
| Mean PnL | −0.005241 | +0.002240 | +0.007481 |
| Blocked entries | 0 | 24 | — |

**Critical caveat:** The 3-trade sample is entirely from `display_snapshot_sampling` entries and entirely from ETH NO. This is the smallest and least generalizable sub-sample in the dataset. The +66.7% TP rate and positive mean PnL are not evidence of a structural edge; they are noise from 3 data points.

### Required replay fields

All fields from Policy B, plus:

| Field | Source | Note |
|---|---|---|
| `first_spread_normalized_seconds_remaining` | `trade_journal.trade_open.payload` | Verifies market was tradable at entry; needed to confirm 0–7s entries have a liquid book |
| `first_tradable_seconds_remaining` | `trade_journal.trade_open.payload` | Confirms book was ready before entry |
| `executable_book_state` | `trade_journal.trade_open.payload` | Must be TRADABLE for 0–7s entries to be valid |

### Key risks

| Risk | Severity | Notes |
|---|---|---|
| n=3 is statistically meaningless | Critical | Any policy derived from 3 data points is indistinguishable from chance |
| All 3 current observations are ETH NO via display_snapshot_sampling | Critical | The 0–7s window may be a DSS artifact, not a market structure artifact |
| Book may not be ready at 0–7s | High | `first_tradable_seconds_remaining` shows books become tradable ~286–297s remaining (elapsed ~3–14s); some epochs the book is thin in the first seconds |
| Virtually eliminates trading activity | High | 3/27 entries = 11.1% retention; meaningful throughput reduction |
| Cannot detect false negatives | High | Unknown how many TP opportunities occur at elapsed 8–30s that Policy C would miss |
| Any new session could immediately disconfirm with a single SL at elapsed ≤7s | Medium | The 2/3 TP record is fragile |

### Evidence required before runtime consideration

- ≥ 50 matched trades in the 0–7s elapsed window across ≥ 10 distinct dates
- ≥ 15 ETH TP trades in the 0–7s window with diverse quote sources (not exclusively DSS)
- Confirmation that `executable_book_state = TRADABLE` at entry time in ≥ 90% of 0–7s entries
- Policy C may only be viable after Policy B is validated at scale

---

## Policy D — Block ACTIVE_INVENTORY_TRADING Entries

### Definition

Block any new entry where `lifecycle_phase = ACTIVE_INVENTORY_TRADING` at the time of the trade open event. Allow all `OPENING_SCAN` entries regardless of elapsed time.

### Gate condition

```
ALLOW entry  if  lifecycle_phase = OPENING_SCAN
BLOCK entry  if  lifecycle_phase = ACTIVE_INVENTORY_TRADING
```

### Hypothesis

`ACTIVE_INVENTORY_TRADING` lifecycle phase marks entries that occur after the market's opening-scan phase has ended — either a repeat entry into an already-active epoch window or a follow-on position in a market that has been trading for 40+ seconds. These entries systematically lack the opening-dislocation edge and produce only losses. The lifecycle phase is a more semantically grounded gate than a raw elapsed-time cutoff because it reflects the system's own classification of the market state.

### Simulated effect on current 27-trade dataset

| Metric | Policy A | Policy D | Delta |
|---|---:|---:|---:|
| Entries | 27 | 18 | −9 |
| TP | 7 | 7 | 0 |
| SL | 20 | 11 | −9 |
| TP rate | 25.9% | 38.9% | +13.0pp |
| Mean PnL | −0.005241 | −0.002683 | +0.002558 |
| Blocked entries | 0 | 9 | — |
| All blocked entries were SL | — | Yes (9/9) | — |

Policy D blocks 9 ACTIVE_INVENTORY_TRADING entries — all SL in the current dataset — while retaining 2 OPENING_SCAN entries at elapsed 31s and 35s that are also SL. Policy B is more aggressive on those two; Policy D is more conservative (uses semantic lifecycle rather than raw elapsed).

### Relationship to Policy B

Policy D and Policy B are related but not identical:

| Elapsed range | Lifecycle | Policy A | Policy B | Policy D |
|---|---|---|---|---|
| 0–30s OPENING_SCAN | OPENING_SCAN | Allow | Allow | Allow |
| 31–35s OPENING_SCAN | OPENING_SCAN | Allow | Block | **Allow** |
| 41s+ ACTIVE_INVENTORY_TRADING | ACTIVE_INVENTORY_TRADING | Allow | Block | Block |

Policy D retains the 31s and 35s OPENING_SCAN entries that Policy B would block. In the current dataset, both are SL, so Policy D's TP rate (38.9%) is lower than Policy B's (46.7%).

### Required replay fields

| Field | Source | Note |
|---|---|---|
| `lifecycle_phase` | `trade_journal.trade_open.payload.lifecycle_phase` | Must be set at entry time, not post-hoc |
| `lifecycle_phase_entered_at` | `trade_journal.trade_open.payload` | Verifies phase was active before entry decision |
| `lifecycle_phase_transition_reason` | `trade_journal.trade_open.payload` | Confirms phase transition logic at entry |
| `epoch_elapsed_s` | Computed | Secondary validation against lifecycle label |

**Critical replay dependency:** Policy D requires that `lifecycle_phase` is set deterministically and reproducibly by the system at entry decision time. If `lifecycle_phase` is set after the entry decision (e.g., at logging time), the replay simulation would be valid but the runtime implementation would require a pre-decision lifecycle evaluation that does not currently exist as a blocking gate.

### Key risks

| Risk | Severity | Notes |
|---|---|---|
| ACTIVE_INVENTORY_TRADING = 0 TP is from n=9 only | High | 9 trades across 2 sessions; may not hold across regimes |
| Policy retains two known SL entries (elapsed 31s, 35s OPENING_SCAN) | Medium | Those are currently OPENING_SCAN; future sessions may have more late-OPENING_SCAN SLs |
| Lifecycle_phase semantics may evolve | Medium | If lifecycle_phase classification logic changes, the policy gate changes silently |
| ACTIVE_INVENTORY_TRADING may occasionally have different behavior in strong-trend regimes | Low | Unknown; not observable from 2-session data |
| Less aggressive than Policy B in the current evidence | Low | For this dataset, D removes fewer SL trades than B |

### Evidence required before runtime consideration

- ≥ 20 ACTIVE_INVENTORY_TRADING entries confirmed SL across ≥ 5 distinct dates
- ≥ 0 ACTIVE_INVENTORY_TRADING entries producing TP across those sessions (or TP rate < 10%)
- Verification that `lifecycle_phase` is set deterministically at entry decision time, not post-hoc
- Explicit operator sign-off after offline replay evaluation

---

## Policy E — Timing-Decay EV Penalty

### Definition

Apply a multiplicative decay factor to the observed EV based on epoch elapsed time at entry. The adjusted EV replaces the raw EV for the entry threshold gate. Entries that pass the raw EV threshold but fail the adjusted EV threshold are blocked.

### Gate condition

```
adjusted_ev = ev × decay_factor(epoch_elapsed_s)

decay_factor(e):
  if e ≤ 30:   1.00   (no penalty)
  if e ≤ 60:   0.70   (30% penalty)
  if e ≤ 120:  0.50   (50% penalty)
  if e > 120:  0.25   (75% penalty)

ALLOW entry  if  adjusted_ev ≥ ev_threshold
BLOCK entry  if  adjusted_ev < ev_threshold
```

The decay factor values above are illustrative design parameters. They are **not calibrated to empirical data** and must not be treated as validated.

### Hypothesis

The EV model computes fair value from probability scores that are blind to epoch timing. A market evaluated at elapsed=80s may have the same computed EV as the same market at elapsed=5s, but the evidence shows that late-entry EV does not translate to realized profit. Applying a timing-decay penalty to EV forces later entries to clear a higher implicit bar, effectively requiring stronger probability signals to justify entry as the epoch progresses. This calibrates the EV signal for its observed epoch-timing sensitivity without changing the probability model itself.

### Simulated effect on current 27-trade dataset

This cannot be precisely simulated without knowing the `ev_threshold` setting from `config/settings.py`. The following analysis uses the current EV distribution to estimate block rates at a hypothetical `ev_threshold = 0.05`:

| Elapsed range | n | Mean raw EV | Decay | Mean adjusted EV | Entries blocked (if threshold=0.05) |
|---|---:|---:|---:|---:|---:|
| 0–30s | 15 | 0.110 | 1.00 | 0.110 | 0 |
| 31–60s | 9 | 0.118 | 0.70 | 0.082 | 0 (above 0.05) |
| 61–120s | 1 | 0.079 | 0.50 | 0.039 | 1 (below 0.05) |
| >120s | 1 | 0.313 | 0.25 | 0.078 | 0 (above 0.05) |

At `ev_threshold = 0.05`, only the 1 entry at elapsed=78s would be blocked by Policy E. All other late entries remain above threshold even with the penalty. This is because the current EV threshold is low relative to observed EV levels.

At `ev_threshold = 0.08`, adjusted analysis:
- 31–60s: adjusted EV range ≈ 0.050–0.130. Entries with raw EV < 0.114 blocked (mean ≈ several of the 9 blocked). ~4–5 of 9 blocked.
- 61–120s: 0.039 < 0.08 → blocked
- >120s: 0.078 < 0.08 → blocked

**The blocking efficacy of Policy E is entirely parameter-dependent.** Without calibrated decay values and a known EV threshold, the simulated effect is indeterminate.

### Required replay fields

All fields from Policy B, plus:

| Field | Source | Note |
|---|---|---|
| `ev` at decision time | `trade_journal.trade_open.payload.ev` | The raw EV before any adjustment |
| `ev_after_spread` | `trade_journal.trade_open.payload.ev_after_spread` | Which EV variant the threshold currently applies to |
| Current `ev_threshold` config value | `config/settings.py` or `.env` | Required to compute actual block rate |
| `epoch_elapsed_s` | Computed | Gate input |

### Calibration methodology (design-only)

Before Policy E can be validly evaluated in replay, a calibration step is required:

1. **Fit decay curve from replay data.** For each elapsed bucket, compute `P(TP | ev, elapsed)` from the replay dataset. The decay curve should reflect the empirical drop in TP probability as a function of elapsed time at fixed EV levels.
2. **Set decay factors to equalize expected TP rates.** If the target is equal probability of TP across elapsed buckets, set `decay(elapsed) = P(TP | elapsed=0) / P(TP | elapsed)`.
3. **This requires ≥ 100 trades per elapsed bucket** to produce stable calibration estimates.

Until this calibration is done, Policy E's decay values are illustrative parameters only.

### Key risks

| Risk | Severity | Notes |
|---|---|---|
| Decay curve is uncalibrated — arbitrary values | Critical | Illustrative decay values must not be used in replay without empirical calibration |
| Low current EV threshold may nullify most blocking | High | If ev_threshold is low (e.g., 0.03–0.05), even penalized late-entry EVs clear the bar |
| Decay curve interacts with existing EV threshold nonlinearly | High | The combined effect on block rate is highly sensitive to the threshold setting |
| Adds a new tunable parameter with no empirical basis | Medium | Risk of overfitting to the 27-trade dataset |
| May block high-EV late entries that have no sample yet in TP | Medium | Currently 0 TP at elapsed>30s, but the model may be correctly identifying real opportunities that happen to have failed in this small sample |
| Most complex to implement correctly when runtime consideration arises | Low | Policy E requires a new EV adjustment step in the decision path |

### Evidence required before runtime consideration

- Calibrated decay curve from ≥ 200 matched trades spanning the full elapsed range
- Empirical measurement of `P(TP | elapsed)` for each 10-second bucket
- Verification that the current EV threshold is known and consistent across sessions
- Replay simulation showing Policy E blocks ≥ 80% of late-window SL entries at the calibrated decay without blocking any TP entries
- Explicit operator sign-off after calibration and replay evaluation

---

## Cross-Policy Comparison

### Effect summary

| Policy | Entries retained | TP | SL | TP rate | Mean PnL | Blocked entries | All blocked = SL? |
|---|---:|---:|---:|---:|---:|---:|---|
| A Baseline | 27 | 7 | 20 | 25.9% | −0.005241 | 0 | — |
| B Opening-only (0–30s) | 15 | 7 | 8 | 46.7% | −0.001706 | 12 | Yes (12/12) |
| C Ultra-opening (0–7s) | 3 | 2 | 1 | 66.7% | +0.002240 | 24 | Yes (24/24) |
| D No ACTIVE phase | 18 | 7 | 11 | 38.9% | −0.002683 | 9 | Yes (9/9) |
| E EV-decay (illustrative) | 25–27 | 7 | 17–20 | 26–28% | varies | 0–2 | Dependent on params |

*Simulated effects are in-sample on 27 trades. None of these numbers are out-of-sample estimates.*

### Trade-off matrix

| Policy | Aggressiveness | Semantic clarity | Calibration required | Runtime complexity | Evidence maturity |
|---|---|---|---|---|---|
| A Baseline | None | N/A | None | None | Current |
| B Opening-only | High | Moderate (raw time) | No | Low | Needs ≥100 trades |
| C Ultra-opening | Very high | Low (3-trade basis) | No | Low | Needs ≥50 early-window trades |
| D No ACTIVE phase | Moderate | High (lifecycle label) | No | Low | Needs ≥20 ACTIVE trades |
| E EV-decay | Low to moderate | Low (uncalibrated curve) | Yes (extensive) | Moderate | Needs ≥200 trades + calibration |

### Recommended evaluation sequence

The policies are not equally ready for replay evaluation. The recommended evaluation order, based on evidence maturity and semantic clarity:

1. **Policy D first.** Uses an existing first-class field (`lifecycle_phase`), blocks the most clearly characterized cohort (ACTIVE_INVENTORY_TRADING = 0/9 TP), and requires no new calibration. The lowest-risk policy to evaluate in replay.

2. **Policy B second.** Requires computing `epoch_elapsed_s` from existing fields. Addresses the broader timing hypothesis. Can be evaluated alongside Policy D in the same replay run.

3. **Policy A as comparator.** Always include baseline in every replay run.

4. **Policy C third, after B is validated.** Ultra-opening is only meaningful if Policy B shows the edge persists with more data. Requires the 0–7s window to have ≥50 trades before evaluation.

5. **Policy E last.** Requires calibration data from the prior three policies' replay runs before its decay curve can be set empirically.

---

## Required Replay Infrastructure

The following JSONL fields must be populated and verified before any of these policies can be evaluated in replay:

### Fields already present and verified

| Field | Status | Verified in |
|---|---|---|
| `epoch_start_ts` | Present | `opening_scan_survival_audit.md` |
| `lifecycle_phase` | Present | `opening_scan_survival_audit.md` |
| `ev` | Present | `opening_scan_survival_audit.md` |
| `ev_after_spread` | Present | `epoch_timing_outcome_audit.md` |
| `trade_result` | Present | All three audits |
| `pnl_usdc` | Present | All three audits |
| `hold_seconds` | Present | `opening_scan_survival_audit.md` |
| `entry_price`, `exit_price` | Present | `opening_scan_survival_audit.md` |
| Entry fill timestamp | Derivable from `execution_log` | `epoch_timing_outcome_audit.md` |

### Fields requiring verification or new addition

| Field | Status | Policy | Notes |
|---|---|---|---|
| `epoch_elapsed_s` at decision time | Not directly emitted; currently computed post-hoc | B, C, E | The current computation uses fill_ts − epoch_start_ts as proxy. True decision time is 1–3s earlier. For replay, fill-ts proxy is acceptable. For runtime, the decision cycle would need to compute this at evaluation time. |
| `first_spread_normalized_seconds_remaining` | Present in trade_open | C | Needed to verify book readiness in 0–7s entries |
| `ev_threshold` config value at session time | Not in JSONL | E | Required to simulate adjusted-EV blocking |
| `lifecycle_phase_entered_at` | Present in trade_open | D | Secondary validation that phase was active before entry |

### Computed field: `epoch_elapsed_s`

For replay simulation, `epoch_elapsed_s` is computed as:

```
entry_fill_unix_ts  =  [DateTimeOffset]::Parse(execution_log.fill.timestamp_utc).ToUnixTimeSeconds()
epoch_elapsed_s     =  entry_fill_unix_ts  −  trade_open.payload.epoch_start_ts
```

This proxy is within 1–3 seconds of the true decision time in all 27 observed cases. For replay evaluation purposes, this approximation is acceptable. A note should be added to any replay report that `epoch_elapsed_s` is a fill-time proxy, not a decision-time measurement.

---

## Simulation Methodology

When the evidence threshold is met and a replay run is authorized, the following approach applies for each policy:

### Step 1: Build the matched trade dataset

Using the matching methodology from `epoch_timing_outcome_audit.md`:
- For each `trade_close` with `trade_result` present, find the matching `trade_open` (same run_id, asset, condition_id, closest prior timestamp)
- Find the entry fill from `execution_log` (same run_id, within 3s of trade_open timestamp)
- Compute `epoch_elapsed_s = fill_unix - epoch_start_ts`
- Record `lifecycle_phase`, `ev`, `trade_result`, `pnl_usdc`, `hold_seconds`

### Step 2: Apply each policy gate

For each matched trade, apply the policy gate conditions and classify:
- `ALLOWED`: trade would proceed under this policy
- `BLOCKED`: trade would be blocked under this policy

### Step 3: Compute outcome metrics for allowed trades only

| Metric | Definition |
|---|---|
| TP rate | TP / (TP + SL) among ALLOWED trades |
| Mean PnL | Sum(pnl_usdc) / n among ALLOWED trades |
| Trade retention | ALLOWED / total |
| Blocked SL rate | SL blocked / total SL |
| False block rate | TP blocked / total TP |

### Step 4: Compare to Policy A (baseline)

Report delta in TP rate, mean PnL, and false-block rate vs baseline. A policy is a candidate improvement only if:
- TP rate improves vs baseline
- Mean PnL improves vs baseline
- False block rate = 0 (no TP trades blocked)

The third condition is strict given current sample size. If a policy blocks any TP trade, it must be explained and justified before proceeding.

### Step 5: Confidence assessment

Given sample size, report:
- Binomial confidence interval on TP rate for ALLOWED trades
- The width of the confidence interval at n=15 (Policy B) is approximately ±25pp at 95% confidence — wide enough to contain the baseline TP rate. This is why the evidence threshold requires ≥100 trades before any claim is made.

---

## Evidence Thresholds Before Runtime Consideration

No policy moves from this design document to runtime consideration without meeting the following thresholds. These are hard gates, not soft suggestions.

| Policy | Minimum trades | Minimum TP | Minimum dates | Additional |
|---|---:|---:|---:|---|
| B Opening-only | ≥ 100 matched | ≥ 20 ETH TP in 0–30s | ≥ 5 | 0–30s TP rate ≥ 35% sustained |
| C Ultra-opening | ≥ 50 in 0–7s window | ≥ 15 ETH TP in 0–7s | ≥ 10 | Policy B validated first |
| D No ACTIVE phase | ≥ 50 ACTIVE_INVENTORY_TRADING | ≥ 0 ACTIVE TP (or < 10% ACTIVE TP rate) | ≥ 5 | lifecycle_phase determinism verified |
| E EV-decay | ≥ 200 matched | ≥ 30 TP | ≥ 10 | Calibrated decay curve from data |

After any threshold is met, the policy must be evaluated in **offline replay only**, with a written replay report, before any runtime consideration. The replay report must show the false-block rate = 0 or provide explicit justification for any blocked TP trade.

---

## What This Document Does Not Authorize

- Modification of `polymarket/trader.py`, `polymarket/order_manager.py`, or any runtime file.
- Changes to `ev_threshold`, `entry_cutoff`, or any setting in `config/settings.py` or `.env`.
- Changes to lifecycle phase classification logic in any module.
- Running offline replay tools against current session data as a policy-validation step.
- Promotion of the S3 caution flag or any live-readiness gate.
- Use of any policy gate in the live order path.

---

## Guardrails

- This document is design-only. No implementation exists or is authorized.
- The simulated effects in this document are in-sample on 27 trades. They are not predictions of out-of-sample performance.
- The 30-second boundary, the ACTIVE_INVENTORY_TRADING classification, and the EV decay values are hypotheses derived from 27 trades. They require validation before any action.
- All future replay reports produced against this design must state that findings are offline-only and do not authorize runtime changes.
- This document must be updated if the evidence base changes materially (e.g., if a future session produces TP trades at elapsed > 30s, the hypothesis changes).
