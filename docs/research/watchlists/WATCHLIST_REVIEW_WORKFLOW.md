# Watchlist Review Workflow v1

type: process document
created: 2026-05-30
version: 1.0
code_changed: No
strategy_changed: No
runtime_changed: No

---

## Overview

This document defines the standard review process for all watchlists in
`docs/research/watchlists/`. It establishes:
- when to review each watchlist
- what to measure at each review
- the evidence thresholds required for status changes
- the governor checklist that must be completed before any promotion

All review outputs are **evidence only**. A promotion to VERIFIED does not
authorize any runtime, strategy, risk, EV, confidence, or execution change.
A separate governance decision is required for any such change.

---

## 1. Daily Review

**Trigger:** Run after each paper session closes OR at end of calendar day,
whichever comes first.

**Time required:** ~5 minutes per active watchlist.

### Steps

#### Step 1 — New Trade Count

For each P0 watchlist, count new trades in the tracked cell since last snapshot:

```
new_trades = total_n_today − last_snapshot_n
```

If `new_trades ≥ 10` for any P0 watchlist → **append a snapshot** to that file.
If `new_trades < 10` → log count only, do not append snapshot.

P1 watchlists: threshold is `new_trades ≥ 20` before appending snapshot.

#### Step 2 — Current n vs Required n

For each watchlist, compute promotion progress:

```
progress_pct = current_n / required_n_for_next_review × 100
```

Record in WATCHLIST_INDEX.md `current_n` column.

Flag any watchlist that has crossed 80% of its required n — it will likely
reach the review threshold within the next 2–3 days.

#### Step 3 — Promotion Progress Check

For each watchlist at ≥ 80% of required n:
- Is win rate still directionally consistent with current status?
- Has calibration gap changed by > 5pp since last snapshot?
- Has any session produced a result that contradicts the pattern?

If any of the above: note in the snapshot header as `⚠ movement_alert`.

#### Step 4 — CLOB Health Flag

Check `ORDERBOOK_STATE_HEALTH.md` daily:
- If `orderbook_unavailable` > 50% of daily decisions → flag as CLOB_DEGRADATION_DAY
- CLOB_DEGRADATION_DAY sessions should be tagged in snapshots but NOT excluded
  from the running n (they count as real paper trading evidence)
- Track rolling 7-day CLOB degradation rate; flag if > 3 days in 7 are degradation days

#### Daily Review Output

A brief note (not a full snapshot) added to `WATCHLIST_INDEX.md` last_updated:

```
YYYY-MM-DD: n=[N] in [WATCHLIST], [N_NEW] new trades. No snapshot triggered.
```

or if snapshot triggered:

```
YYYY-MM-DD: Snapshot appended to [WATCHLIST]. n=[N], wr=[W%].
```

---

## 2. Weekly Review

**Trigger:** Every 7 calendar days from session start, or after any single
week produces ≥ 50 new trades across all P0 watchlists.

**Time required:** ~30–45 minutes (full data query for all watchlists).

### Steps

#### Step 1 — Trend Change Detection

For each watchlist, compare the new snapshot win rate to the prior snapshot:

| Change | Label |
|---|---|
| Win rate moves > 5pp in either direction | `TREND_SHIFT` |
| Win rate moves > 10pp in either direction | `STRONG_TREND_SHIFT` |
| Win rate < 1pp movement | `STABLE` |

Flag any `STRONG_TREND_SHIFT` for immediate governor review.

#### Step 2 — Calibration Gap Stability

For each watchlist, compare `avg(true_p)` across the two most recent snapshots:

- If `avg(true_p)` changes by < 0.010: model behavior **STABLE**
- If `avg(true_p)` changes by 0.010–0.030: note as **DRIFT**
- If `avg(true_p)` changes by > 0.030: flag as **CALIBRATION_SHIFT** — requires investigation

The probability model's `true_p` assignment is expected to be mechanically stable
(confirmed: σ = 0.008 for ETH_NO_COMPRESSION across 23 sessions). Any drift
above 0.030 may indicate a code change or data quality issue.

#### Step 3 — Watchlist Status Review

For each watchlist, run the full promotion and downgrade decision tree
(defined in Sections 3 and 4 of this document). Document the decision
and its rationale in the snapshot header.

#### Step 4 — Cross-Watchlist Correlation Check

Check whether findings across watchlists are consistent:
- MICRO_RECOVERY_SELECTION and BTC_COMPRESSION_OPENING_SCAN should move together
  (they share BTC COMPRESSION as the problematic cell)
- ACTIVE_INVENTORY_EV_INVERSION and ETH_NO_COMPRESSION should move together
  (ETH NO COMPRESSION is the dominant AI loser)
- If these diverge significantly, flag for investigation

#### Step 5 — Session Coverage Audit

Check that new evidence comes from ≥ 3 independent sessions (not one long run):
- Evidence concentrated in a single session is fragile — note in snapshot
- Evidence from ≥ 5 sessions on ≥ 3 different calendar dates is preferred for any promotion

#### Weekly Review Output

Full snapshot appended to each watchlist file:

```markdown
## Snapshot N — YYYY-MM-DD [weekly]

trend: STABLE | TREND_SHIFT | STRONG_TREND_SHIFT
calibration: STABLE | DRIFT | CALIBRATION_SHIFT
sessions_since_last: N
new_trades_since_last: N

[core metrics table]
[win rate by confidence band if applicable]
[sessions covered]
```

---

## 3. Promotion Rules: OBSERVED → VERIFIED

A watchlist reaches VERIFIED when ALL of the following are met:

### Universal Requirements (all watchlists)

| Requirement | Threshold |
|---|---|
| Minimum total n | ≥ 50 per tracked cell |
| Session diversity | ≥ 3 independent sessions from different calendar periods |
| Calendar breadth | ≥ 7 unique calendar days |
| Statistical significance | p < 0.05 in the correct tail (see per-watchlist) |
| Direction consistency | Pattern direction consistent in ≥ 70% of sessions |
| Governor sign-off | Required before recording VERIFIED status |

### Per-Watchlist Specific Thresholds

#### MICRO_RECOVERY_SELECTION
- conf≥0.75 trades n ≥ 100 (currently 40)
- BTC share ≥ 80% in ≥ 5 sessions (already met: 87.5% in 22 sessions)
- BTC COMPRESSION win rate < 35% over n ≥ 50 BTC COMP hi-conf trades
- p (lower tail, BTC COMP conf≥0.75 vs baseline) < 0.05
- Note: mechanism is already VERIFIED (mathematical proof from liq_mult formula)

#### ETH_NO_COMPRESSION
- Total n ≥ 100 (currently 52)
- Win rate < 40% sustained over the new n ≥ 50 increment
- p (lower tail) < 0.05 — requires n ≈ 350 at observed effect size of −7.1pp
- Calibration gap > +0.25 in ≥ 5 sessions (currently 16/23 — already trending)
- Note: Full VERIFIED at current effect size requires ~300 more trades

#### BTC_COMPRESSION_OPENING_SCAN
- Total OS trades n ≥ 150 (currently 59)
- Confidence inversion monotonic with n ≥ 15 in ALL four confidence bands
- true_p 0.65–0.70 bucket actual win rate < 25% over n ≥ 50 in that bucket
- Calibration gap > +0.25 sustained
- Note: The 0.65–0.75 band currently has a minor inversion violation; needs resolution

#### ACTIVE_INVENTORY_EV_INVERSION
- Total AI trades n ≥ 500 (currently 384)
- Pearson r(EV, PnL) remains in [−0.05, +0.05] over new n ≥ 100
- Q4 win rate < Q1 win rate on new n ≥ 100 incremental trades
- ETH EV_Δ < 0 confirmed on new n ≥ 150 ETH AI trades

#### ORDERBOOK_STATE_HEALTH (per state)
- ready: n ≥ 250 (currently 161)
- empty_book: n ≥ 250 (currently 192)
- orderbook_unavailable anomaly: n ≥ 75 (currently 38)
- stale_orderbook: n ≥ 30 (currently 9)

### What VERIFIED Does NOT Authorize

VERIFIED status means the pattern is statistically confirmed. It does **NOT**:
- Authorize any code change
- Authorize any strategy modification
- Authorize any risk threshold change
- Authorize any confidence adjustment
- Authorize any EV formula change
- Authorize any execution change

A VERIFIED finding enters the governance backlog for Phase design consideration
(Phase 3 exit engine, Phase 4 inventory trading, etc.) as defined in CLAUDE.md.

---

## 4. Downgrade Rules: OBSERVED → NOT_SUPPORTED

A watchlist is downgraded when the evidence clearly contradicts the hypothesis.

### Downgrade Triggers (any one is sufficient)

| Trigger | Threshold |
|---|---|
| p-value (correct tail) | > 0.30 on new n ≥ 50 data block |
| Win rate reversal | New win rate exceeds old by > 10pp on n ≥ 30 |
| Calibration gap collapse | avg(true_p) − win_rate < +0.10 on n ≥ 30 |
| Session contradiction | ≥ 5 of last 10 sessions contradict the pattern |

### Per-Watchlist Specific Downgrade Criteria

#### MICRO_RECOVERY_SELECTION
- ETH achieves conf≥0.75 in > 20% of trades (structural change)
- BTC COMPRESSION win rate rises above 45% at conf≥0.75 over n ≥ 30 new trades
- Note: the selection mechanism itself cannot be downgraded — it follows from the
  liq_mult formula. Only the outcome degradation can be downgraded.

#### ETH_NO_COMPRESSION
- Win rate rises above 45% AND p > 0.30 (lower tail) over n ≥ 30 new trades
- avg(true_p) drifts below 0.62 (would indicate model change, not market change)

#### BTC_COMPRESSION_OPENING_SCAN
- Win rate in 0.65–0.75 conf band rises above 45% on n ≥ 20 new trades
- Monotonic inversion breaks clearly (mid-band win rate > low-band by > 5pp on n ≥ 20)

#### ACTIVE_INVENTORY_EV_INVERSION
- Pearson r > +0.15 over n ≥ 100 new AI trades
- Q4 win rate exceeds Q1 win rate by > 5pp on n ≥ 100 new trades

#### ORDERBOOK_STATE_HEALTH
- Per-state: win rate and calibration gap converge within 5pp of each other
- Anomaly resolution: orderbook_unavailable falls below 43% win rate on n ≥ 30

### Downgrade Process

1. Record the contradicting evidence in a new snapshot with header `⚠ DOWNGRADE_CANDIDATE`
2. Run governor review checklist (Section 6)
3. If governor approves: update status field in file header and WATCHLIST_INDEX.md
4. Document the reason for downgrade in the snapshot

---

## 5. Required Evidence Thresholds

### n Thresholds by Purpose

| Purpose | Minimum n | Rationale |
|---|---|---|
| WATCHLIST (mention-only) | < 10 | Not enough to characterize |
| WEAK_SIGNAL | 10–20 | Direction visible, high noise |
| OBSERVED | 20–50 | Pattern confirmed directionally |
| OBSERVED (strong) | 50–100 | Pattern directionally stable |
| VERIFIED | ≥ 50 per cell + p < 0.05 | Statistically significant |
| VERIFIED (robust) | ≥ 100 per cell + replication | High confidence |

### Statistical Significance Requirements

All p-values use the **correct tail** (the tail corresponding to the hypothesis):

| Hypothesis | Correct tail |
|---|---|
| Win rate significantly LOW | Lower tail: P(X ≤ W \| n, baseline_p) |
| Win rate significantly HIGH | Upper tail: P(X ≥ W \| n, baseline_p) |
| EV inversely correlated | Test: Pearson r < 0, H0: r = 0 |

**Baseline p for win rate tests:** Use the population win rate from the current
full dataset at the time of review (typically 37–40%). Do not use 50% — the
system is not a fair coin at baseline.

### Effect Size Guidance

| Effect | Win rate vs baseline | Cohen's h | Required n (80% power, α=0.05) |
|---|---|---|---|
| Small | 5pp deficit | ~0.10 | ~800 |
| Medium | 7–8pp deficit | ~0.15 | ~350 |
| Large | 10–12pp deficit | ~0.20 | ~200 |
| Very large | 15+pp deficit | ~0.30 | ~90 |

Current ETH_NO_COMPRESSION effect: −7.1pp → medium effect → n ≈ 350 for VERIFIED.
Current BTC_COMPRESSION_OPENING_SCAN overall: −8pp → medium → n ≈ 280 for VERIFIED.

### Calibration Gap Thresholds

| Calib gap | Interpretation |
|---|---|
| < +0.05 | Well calibrated — model and market agree |
| +0.05 to +0.15 | Mild overconfidence — monitor |
| +0.15 to +0.25 | Moderate overconfidence — OBSERVED range |
| +0.25 to +0.40 | Severe overconfidence — strong OBSERVED |
| > +0.40 | Catastrophic overconfidence — VERIFIED candidate |

---

## 6. Governor Review Checklist

This checklist must be completed before recording any status change
(promotion or downgrade) in any watchlist file.

### 6A. Before Recording VERIFIED

- [ ] **n threshold met**: Total n ≥ required n for this watchlist
- [ ] **p < 0.05**: Confirmed in correct tail with documented calculation
- [ ] **Session diversity**: Evidence from ≥ 3 sessions on ≥ 3 different calendar dates
- [ ] **No outlier contamination**: No single session contributes > 50% of the supporting evidence
- [ ] **Direction consistency**: ≥ 70% of sessions show the same directional pattern
- [ ] **Calibration gap stable**: avg(true_p) variance < 0.030 across sessions
- [ ] **No code change since last snapshot**: Confirm git log shows no relevant code changes
- [ ] **Model unchanged**: The probability model formula has not changed since evidence was collected
- [ ] **No strategy change since evidence collection**: Confirm no relevant parameter changes
- [ ] **Watchlist file updated**: New snapshot appended with all required metrics
- [ ] **WATCHLIST_INDEX updated**: Status column updated, last_snapshot date updated
- [ ] **Governance noted**: Status change recorded as evidence only, no action authorized

### 6B. Before Recording NOT_SUPPORTED

- [ ] **Contradicting evidence threshold met**: n ≥ 30 new trades that contradict the pattern
- [ ] **p > 0.30 confirmed**: Correct tail p-value documented
- [ ] **Direction reversal not explained by outlier**: No single session drives the reversal
- [ ] **Model or code unchanged**: Reversal is market behavior, not an artifact of system changes
- [ ] **Prior evidence archived**: All supporting snapshots remain in the file (do not delete)
- [ ] **Downgrade rationale documented**: Written explanation in new snapshot
- [ ] **WATCHLIST_INDEX updated**: Status changed to NOT_SUPPORTED
- [ ] **Governance noted**: Status change recorded; no action authorized

### 6C. Before Any Snapshot Append

- [ ] **Snapshot n is larger than prior snapshot n**: Confirm accumulation, not recount
- [ ] **Trade source is confirmed paper mode**: Verify `mode=paper` in trade_journal events
- [ ] **No test artifacts**: pnl_magnitude filter applied (|pnl| > $0.50 excluded)
- [ ] **run_id verified**: Confirm trades are from clean production runs, not test or verify sessions
- [ ] **Calculation method unchanged**: If methodology changed, document it in the snapshot header
- [ ] **Date and timestamp recorded**: snapshot header includes analysis_run date

---

## Appendix: Snapshot Format Template

Use this exact format for all snapshot entries:

```markdown
## Snapshot N — YYYY-MM-DD [trigger: daily | weekly | n_threshold | manual]

analysis_run: YYYY-MM-DD
trigger: [new_trades | 7_day | n_threshold | manual]
trend: STABLE | TREND_SHIFT | STRONG_TREND_SHIFT
calibration: STABLE | DRIFT | CALIBRATION_SHIFT
sessions_since_last: N
new_trades_since_last: N
movement_alert: None | ⚠ [description]

[progress bar]

### Core Metrics

| Metric | Value |
|---|---|
| Current n | N |
| Win rate | N% |
| [other watchlist-specific metrics] |

[optional: breakdown tables if n_threshold or weekly]
```

---

## File Ownership and Update Responsibility

These watchlist files are maintained by the research analyst role during
each audit session. No automated process writes to these files. Every
update is manually reviewed before commit.

Committed changes to watchlist files must be in a dedicated commit
with message format: `Update watchlist snapshots [YYYY-MM-DD]`

Structural changes (adding/removing metrics, changing thresholds) require
a separate commit with message: `Revise watchlist structure [reason]`
