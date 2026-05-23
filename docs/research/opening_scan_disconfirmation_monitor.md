# Opening Scan Disconfirmation Monitor v1

Document type: standing disconfirmation tracker. Updated whenever a disconfirmation event occurs or a snapshot is added to `opening_scan_policy_evidence_monitor.md`.

Created: 2026-05-23

Runtime behavior changed: No. Code changed: No.

---

## Purpose

The opening-scan timing edge (`OPENING_SCAN_EDGE_CANDIDATE`) rests on two patterns observed across 28 trades:

1. All TP trades occurred within the first 30 seconds of their epoch window.
2. All `ACTIVE_INVENTORY_TRADING` entries resolved as SL.

Both patterns are intact but unconfirmed. This document exists to prevent those patterns from being treated as confirmed before the evidence threshold is met. It tracks specific events that would weaken or break the hypothesis, and classifies the current edge state on every update.

**The cost of false confirmation is higher than the cost of delay.** A policy gate applied prematurely based on 28 trades could suppress valid entries, reduce learning signal, and cause real financial harm in any eventual live session. This monitor is the standing counterweight to confirmation bias.

---

## Current Classification

```
EDGE_INTACT
```

As of: 2026-05-23, Snapshot 1 (28 matched trades).

All six disconfirmation event counters are at zero. Both core patterns hold without exception. Evidence is insufficient for confirmation — the current classification describes only the absence of disconfirmation, not the presence of confirmed edge.

---

## Classification Rules

### EDGE_INTACT

All of the following must be true:

- Event 1 count (ACTIVE TP) = 0
- Event 2 count (>30s TP) = 0
- Policy D false-block count = 0
- Policy B false-block count = 0
- OPENING_SCAN TP rate ≥ 25% over cumulative matched trades
- No single session produces ≥ 3 SL from the ≤30s window with 0 TP

Classification does **not** mean the edge is confirmed. It means no specific disconfirmation event has occurred yet.

### EDGE_WEAKENING

Any one of the following:

- Event 1 or Event 2 count = 1 (first ACTIVE TP or first >30s TP — isolated, possibly noise)
- Policy D or Policy B false-block count reaches 1–2
- OPENING_SCAN TP rate drops below 25% over the most recent 20 OPENING_SCAN trades (rolling)
- TP rate differential between elapsed ≤30s and elapsed >30s narrows to < 15 percentage points over any 20-trade rolling window
- BTC TP rate becomes > 0 AND the BTC TP occurred within the ≤30s window (would complicate the ETH-only narrative but not necessarily break the ETH timing pattern)

When EDGE_WEAKENING is reached: **do not act on any policy candidate**. Collect more evidence. Note the specific event in Section 2. Update this document. Do not revert classification without explicit written rationale.

### EDGE_BROKEN

Any one of the following hard-break conditions:

- Event 1 count (ACTIVE TP) ≥ 3
- Event 2 count (>30s TP) ≥ 3
- ACTIVE_INVENTORY_TRADING TP rate reaches ≥ 15% over the full matched dataset
- elapsed >30s TP rate reaches ≥ 15% over the full matched dataset
- OPENING_SCAN TP rate drops below 15% over the cumulative matched dataset
- Policy D or Policy B cumulative false-block rate ≥ 10%

When EDGE_BROKEN is reached: **all policy candidates (B, C, D, E) from `opening_scan_policy_candidate_design.md` are suspended**. The design document must be revised before any further replay evaluation is authorized. Note the breaking event, timestamp, run ID, and trade detail in Section 2.

---

## Section 1 — Disconfirmation Event Definitions and Thresholds

### Event 1 — ACTIVE_INVENTORY_TRADING TP

**Definition:** Any matched trade where `trade_open.lifecycle_phase = ACTIVE_INVENTORY_TRADING` AND `trade_close.trade_result = TP`.

**Why it matters:** Policy D blocks all ACTIVE_INVENTORY_TRADING entries. If any ACTIVE entry produces TP, Policy D would have incorrectly suppressed a profitable trade. One such event may be noise; three would structurally weaken the policy.

| Threshold | Classification impact |
|---|---|
| Count = 0 | No impact (current state) |
| Count = 1–2 | EDGE_WEAKENING |
| Count ≥ 3 | EDGE_BROKEN |
| ACTIVE TP rate ≥ 15% cumulative | EDGE_BROKEN regardless of count |

### Event 2 — Elapsed > 30s TP

**Definition:** Any matched trade where `epoch_elapsed_s > 30` AND `trade_close.trade_result = TP`.

**Why it matters:** Policy B blocks all entries after 30 seconds elapsed. A TP trade after 30s means Policy B would have blocked a real winner. The 30-second cliff is currently clean across 12 consecutive post-30s SL trades. A single TP after 30s reopens the question of where — or whether — the boundary exists.

| Threshold | Classification impact |
|---|---|
| Count = 0 | No impact (current state) |
| Count = 1–2 | EDGE_WEAKENING |
| Count ≥ 3 | EDGE_BROKEN |
| >30s TP rate ≥ 15% cumulative | EDGE_BROKEN regardless of count |

### Event 3 — Policy D False-Block Count

**Definition:** Cumulative count of ACTIVE_INVENTORY_TRADING entries that resolved TP (same as Event 1 count, viewed as a false-block metric).

**Note:** Event 3 tracks the same underlying trades as Event 1 but frames them as a policy metric rather than an evidence metric. Both are updated together.

| Threshold | Classification impact |
|---|---|
| 0 | No impact (current state) |
| 1 | EDGE_WEAKENING |
| ≥ 3, or rate ≥ 10% | EDGE_BROKEN |

### Event 4 — Policy B False-Block Count

**Definition:** Cumulative count of elapsed > 30s entries that resolved TP (same as Event 2 count, viewed as a false-block metric).

**Note:** Event 4 tracks the same underlying trades as Event 2 but frames them as a policy metric. Both are updated together.

| Threshold | Classification impact |
|---|---|
| 0 | No impact (current state) |
| 1 | EDGE_WEAKENING |
| ≥ 3, or rate ≥ 10% | EDGE_BROKEN |

### Event 5 — BTC TP (any elapsed)

**Definition:** Any matched BTC trade where `trade_close.trade_result = TP`, regardless of elapsed time or lifecycle phase.

**Why it matters:** BTC is currently 0/4 TP across all timing windows, lifecycle phases, and quote sources. The opening-scan timing hypothesis applies primarily to ETH in the current evidence base. BTC may have independent market structure. A first BTC TP does not directly disconfirm the ETH timing edge, but it changes the BTC-specific story and affects how a future runtime policy would be scoped (ETH-only vs both assets).

**Classification rule:**
- First BTC TP within elapsed ≤ 30s and OPENING_SCAN phase: note as contextual update, **no classification change** (consistent with the ETH timing pattern).
- First BTC TP within elapsed > 30s or ACTIVE_INVENTORY_TRADING: **EDGE_WEAKENING** (BTC behavior diverges from ETH pattern; policies that treat both assets identically would need reassessment).
- BTC TP rate ≥ 15% after ≥ 10 BTC trades: **EDGE_WEAKENING** (BTC asset classification changes).

| Threshold | Classification impact |
|---|---|
| 0 BTC TP | No impact (current state) |
| First BTC TP, ≤30s OPENING_SCAN | Contextual note only; no classification change |
| First BTC TP, >30s or ACTIVE | EDGE_WEAKENING |
| BTC TP rate ≥ 15% after ≥ 10 BTC trades | EDGE_WEAKENING |

### Event 6 — OPENING_SCAN TP Collapse

**Definition:** OPENING_SCAN TP rate drops below 25% over the most recent 20 OPENING_SCAN matched trades (rolling window), OR drops below 15% cumulatively across all matched trades.

**Why it matters:** The timing hypothesis depends on OPENING_SCAN entries having meaningfully higher TP rates than ACTIVE_INVENTORY_TRADING entries. If the OPENING_SCAN TP rate degrades toward the baseline (≈25%), the lifecycle-phase gate loses its discriminatory value. Cumulative OPENING_SCAN TP rate is currently 36.8% (7/19); a sustained fall toward 20–25% would suggest the early-window advantage is eroding, not just that late entries are failing.

| Threshold | Classification impact |
|---|---|
| OPENING_SCAN TP rate ≥ 25% (rolling 20) | No impact (current state: 36.8%) |
| OPENING_SCAN TP rate 20–24% (rolling 20) | EDGE_WEAKENING |
| OPENING_SCAN TP rate < 20% (rolling 20) | EDGE_WEAKENING |
| OPENING_SCAN TP rate < 15% cumulative | EDGE_BROKEN |

---

## Section 2 — Event Log

### Current state: No disconfirmation events recorded.

| Seq | Event type | Date | Run ID | Asset | Side | Elapsed | Lifecycle | PnL | Classification change |
|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | — | — |

*This table is append-only. Rows are never removed.*

When a disconfirmation event occurs, add a row using this format:

```
| N | Event[1-6] | YYYY-MM-DD | run_id_prefix | ETH/BTC | YES/NO | Xs | PHASE | ±0.XXXXXX | INTACT→WEAKENING / WEAKENING→BROKEN |
```

---

## Section 3 — Running Counters

Updated at each snapshot.

| Counter | Value | Last updated |
|---|---|---|
| Event 1 — ACTIVE TP count | **0** | 2026-05-23 Snapshot 1 |
| Event 2 — >30s TP count | **0** | 2026-05-23 Snapshot 1 |
| Event 3 — Policy D false-block | **0** | 2026-05-23 Snapshot 1 |
| Event 4 — Policy B false-block | **0** | 2026-05-23 Snapshot 1 |
| Event 5 — BTC TP count | **0** | 2026-05-23 Snapshot 1 |
| Event 6 — OPENING_SCAN TP rate (cumulative) | **36.8%** (7/19) | 2026-05-23 Snapshot 1 |
| Event 6 — OPENING_SCAN TP rate (rolling 20) | **36.8%** (n < 20; full window) | 2026-05-23 Snapshot 1 |
| Total matched trades | **28** | 2026-05-23 Snapshot 1 |
| Current classification | **EDGE_INTACT** | 2026-05-23 Snapshot 1 |

---

## Section 4 — What Does NOT Count as Disconfirmation

The following observations are consistent with the current evidence and do not trigger a classification change:

| Observation | Why it is not disconfirmation |
|---|---|
| OPENING_SCAN entry resolves SL | Expected — OPENING_SCAN TP rate is 36.8%, not 100%. SL within ≤30s is normal variance |
| BTC entry resolves SL | BTC = 0/4 TP already; additional BTC SL just adds to the existing BTC-SL pattern |
| Very early entry (≤7s) resolves SL | 0–7s TP rate is 66.7% from n=3 — highly unstable; a single SL is expected |
| Session with 0 TP trades | A session without TP trades adds SL evidence and is expected given ~25–37% TP rates |
| OPENING_SCAN TP rate drops in one session | One session's TP rate is noise; rolling-20 and cumulative rates are what matter |
| elapsed = 31–35s entry resolves SL | Adds to the >30s all-SL count; consistent with Policy B hypothesis |
| Any `display_snapshot_sampling` entry resolves SL | Quote source is not the signal; timing is |
| EV remains high on SL trades | Already established in `opening_scan_survival_audit.md`; EV is blind to timing |

---

## Section 5 — Classification Decision Rules

### When EDGE_WEAKENING is reached

1. Record the disconfirmation event in Section 2 immediately.
2. Update the running counters in Section 3.
3. Do not act on any policy candidate from `opening_scan_policy_candidate_design.md`.
4. Do not update the policy design document yet — collect at least 10 more matched trades first.
5. If the event is isolated (count = 1) and no further disconfirmation events occur in the next 20 trades, the classification may be reviewed — but **it does not automatically revert to EDGE_INTACT**. A written rationale is required.
6. Continue paper session monitoring normally.

### When EDGE_BROKEN is reached

1. Record the breaking event in Section 2 with full detail.
2. Update the classification in the header of this document.
3. **Suspend all policy candidates B, C, D, E.**
4. Add a note to `opening_scan_policy_candidate_design.md` referencing this event.
5. The policy design process must restart from the evidence base, not from the existing candidate definitions.
6. Do not revert from EDGE_BROKEN without a new set of ≥ 50 matched trades showing the pattern has restabilized.

### When evidence threshold is reached without disconfirmation

If total matched trades reaches 100 AND ETH TP in ≤30s reaches ≥ 20 AND dates covered reaches ≥ 5 AND all event counters remain at zero throughout:

- Classification upgrades from EDGE_INTACT to a new review-eligible state.
- That upgrade is documented in `opening_scan_policy_evidence_monitor.md`, not here.
- This document continues tracking disconfirmation events independently of the review state.

---

## Section 6 — Update Schedule

| Trigger | Required action |
|---|---|
| New snapshot in `opening_scan_policy_evidence_monitor.md` | Update Section 3 counters; verify classification |
| Any disconfirmation event occurs | Update Section 2 log AND Section 3 counters immediately; reassess classification |
| Classification changes | Update header; add note to `opening_scan_policy_candidate_design.md` |
| Total matched trades crosses 50, 75, 100 | Update Section 3; note milestone |

---

## Guardrails

- This document tracks disconfirmation only. It does not recommend policy actions.
- A classification of EDGE_INTACT does not authorize runtime policy changes.
- A classification of EDGE_INTACT does not mean the edge is confirmed.
- This document must be updated before any replay evaluation is initiated.
- All events are read from existing offline JSONL data only. No runtime, no live data queries, no strategy changes.
