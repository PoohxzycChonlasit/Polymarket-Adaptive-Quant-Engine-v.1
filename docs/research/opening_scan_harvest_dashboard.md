# Opening Scan Harvest Dashboard

Updated: 2026-05-23 — Snapshot 1

---

## Classification

```
╔══════════════════════════════╗
║       HARVESTING             ║
║  28 / 100 trades · 28%      ║
╚══════════════════════════════╝
```

No disconfirmation events recorded. All evidence gates accumulating. Not yet eligible for replay evaluation.

---

## Evidence Gates

Three gates must clear simultaneously before offline replay evaluation is authorised.
All disconfirmation counters must remain at zero throughout.

```
GATE 1 — Matched trades
─────────────────────────────────────────────────────
Target   100
Current   28  ██████░░░░░░░░░░░░░░░░░░░░░░  28%
Remain    72
ETA      ~7 days  (rate: ~10.5 trades/day observed)

GATE 2 — ETH TP in elapsed ≤ 30s
─────────────────────────────────────────────────────
Target   20
Current   7  ████████░░░░░░░░░░░░░░░░░░░░  35%
Remain   13
ETA      ~5 days  (rate: ~2.6 ETH TP/day observed)

GATE 3 — Distinct dates
─────────────────────────────────────────────────────
Target    5
Current   2  ████████████░░░░░░░░░░░░░░░░  40%
Remain    3
ETA      ~3 days  (one new date per active session day)

BINDING CONSTRAINT: Gate 1 — matched trades (~7 days)
```

ETA estimates assume current observed rates: 8 sessions, ~3.5 trades/session, ~3 sessions/day.
Rates are volatile and may change materially with session length, market activity, or regime shift.

---

## Disconfirmation Counters

All counters must remain at zero for classification to stay HARVESTING or advance to READY_FOR_REPLAY.

```
Event 1  ACTIVE_INVENTORY_TRADING TP     0        ✓ CLEAR
Event 2  elapsed >30s TP                 0        ✓ CLEAR
Event 3  Policy D false-block            0        ✓ CLEAR
Event 4  Policy B false-block            0        ✓ CLEAR
Event 5  BTC TP (any elapsed)            0        ✓ CLEAR
Event 6  OPENING_SCAN TP collapse        —        ✓ 36.8% (threshold: <25%)
```

First disconfirmation event triggers immediate reassessment.
See `opening_scan_disconfirmation_monitor.md` for full event definitions and classification rules.

---

## Core Metrics

```
Metric                        Value     Trend    Note
──────────────────────────────────────────────────────────────────
Matched trades                  28        ↑      Accumulating
OPENING_SCAN  n               19 TP=7    ↓~     One new SL added this session
ACTIVE  n                      9 TP=0    →      Stable at 0% TP
elapsed ≤30s  n               16 TP=7    ↑      +1 new ≤30s trade (SL)
elapsed >30s  n               12 TP=0    ↑      +1 new >30s trade (SL), cliff intact
ETH  n                        24 TP=7    ↑      29.2% TP rate
BTC  n                         4 TP=0    →      0% TP; no BTC TP observed
Overall TP rate               25.0%      →      Stable
OPENING_SCAN TP rate          36.8%      ↓~     Was 38.9% at n=18; one new SL
>30s cliff                    intact     →      12 consecutive SL, 0 TP
ACTIVE cliff                  intact     →       9 consecutive SL, 0 TP
```

Trend key: ↑ improving · ↓ declining · → stable · ↓~ minor decline within normal range

---

## Sub-window Survival Map

```
Elapsed        n    TP    SL    TP%    Bar
──────────────────────────────────────────────────────
0 –  7s        3     2     1   66.7%  ██████████████  (n=3 — noise only)
8 – 14s        8     3     5   37.5%  ████████
15 – 30s       5     2     3   40.0%  ████████
─── 30s boundary ─────────────────────────────────────
31 – 60s       9     0     9    0.0%  ░░░░░░░░░░░░░░
61 –120s       1     0     1    0.0%  ░░░░░░░░░░░░░░
  >120s        1     0     1    0.0%  ░░░░░░░░░░░░░░
──────────────────────────────────────────────────────
TOTAL         28     7    21   25.0%
```

30-second cliff: **intact**. 12 consecutive SL after 30s elapsed. Zero TP observed past 30s.

---

## Policy Readiness

```
Policy    Gate      Status       Blocking factor
──────────────────────────────────────────────────────────────────────
A  Baseline          —           —        Reference only
D  No ACTIVE        Need         Not ready  9/50 ACTIVE trades (18%)
B  0–30s only       Need         Not ready  28/100 matched, 7/20 ETH TP
C  Ultra 0–7s       Need         Not ready  3/50 early-window trades (6%)
E  EV-decay         Need         Not ready  Requires calibration from ≥200 trades
```

No policy is ready for replay evaluation. No policy is authorised for runtime.
Tool to build: `tools/opening_scan_policy_replay.py` — deferred until Gate 1 clears.

---

## Lifecycle Phase Breakdown

```
OPENING_SCAN           19  TP=7  SL=12  TP%=36.8%  ████████████░░░░░░░░
ACTIVE_INVENTORY        9  TP=0  SL= 9  TP%= 0.0%  ░░░░░░░░░░░░░░░░░░░░

Gap: 36.8pp  (WEAKENING threshold: gap narrows below 15pp)
```

---

## Asset Breakdown

```
ETH   24 trades   TP= 7  SL=17   TP%=29.2%   ██████░░░░░░░░░░░░░░
BTC    4 trades   TP= 0  SL= 4   TP%= 0.0%   ░░░░░░░░░░░░░░░░░░░░

ETH TP inside ≤30s: 7/7  (100% of all TP are early-window ETH)
BTC TP inside ≤30s: 0/3
```

---

## Session Ledger

| Date | Sessions | Matched | ≤30s | >30s | OPENING | ACTIVE | TP | SL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-05-22 | 5 | 17 | 10 | 7 | 14 | 3† | 6 | 11 |
| 2026-05-23 | 3 | 11 | 6 | 5 | 5 | 6† | 1 | 10 |
| **Total** | **8** | **28** | **16** | **12** | **19** | **9** | **7** | **21** |

† Run-level lifecycle split is approximate; totals are exact from matched dataset.

---

## Snapshot History

| Snapshot | Date | Trades | ETH TP ≤30s | Dates | OPENING TP% | ACTIVE TP | >30s TP | Classification |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 2026-05-23 | 28 | 7 | 2 | 36.8% | 0 | 0 | HARVESTING |

---

## Classification Rules

| Classification | Condition |
|---|---|
| **HARVESTING** | Default while any evidence gate is unmet and all disconfirmation counters = 0 |
| **READY_FOR_REPLAY** | All three gates met (≥100 trades, ≥20 ETH TP ≤30s, ≥5 dates) AND all disconfirmation counters = 0 |
| **EDGE_WEAKENING** | Any disconfirmation event counter ≥ 1 OR OPENING_SCAN TP rate drops below 25% rolling-20 |
| **EDGE_BROKEN** | Any disconfirmation event counter ≥ 3 OR rate threshold breached (see disconfirmation monitor) |

READY_FOR_REPLAY authorises offline replay tool creation and execution only.
It does not authorise runtime policy changes.

---

## ETA Detail

```
Binding gate: GATE 1 (matched trades)

Observed rate
  Sessions total:       8
  Trades total:        28
  Trades / session:   3.5
  Sessions / day:      ~3  (observed; varies with operator schedule)
  Trades / day:       10.5

To READY_FOR_REPLAY
  Trades needed:       72  → ~7 days
  ETH TP needed:       13  → ~5 days  (non-binding)
  Dates needed:         3  → ~3 days  (non-binding)
  ETA (estimated):  2026-05-30  (±4 days depending on session volume)

Rate sensitivity
  If 2 sessions/day:   ~12 days  (ETA 2026-06-04)
  If 5 sessions/day:   ~4 days   (ETA 2026-05-27)
```

ETA is approximate. ETH TP rate within ≤30s (43.8%) and the overall trade rate (3.5/session)
may both shift with market regime, session length, or BTC/ETH market availability.

---

## What to Do Next

```
RIGHT NOW
  Continue paper session monitoring.
  Update opening_scan_policy_evidence_monitor.md when ≥ 5 new trades appear.
  Update this dashboard at each monitor snapshot.

IF a disconfirmation event occurs
  Update opening_scan_disconfirmation_monitor.md first.
  Update Section 2 event log and running counters there.
  Update disconfirmation counters in this dashboard.
  Reassess classification. Do NOT act on any policy candidate.

WHEN Gate 1 clears (≥ 100 trades)
  Verify Gates 2 and 3 also met.
  Confirm all disconfirmation counters still at zero.
  Create tools/opening_scan_policy_replay.py (no runtime changes).
  Run offline replay for Policies D and B.
  Update this dashboard with READY_FOR_REPLAY classification.

DO NOT
  Modify trader.py or any runtime file.
  Change EV threshold or entry cutoff settings.
  Enable any runtime policy gate.
  Promote S3 or change live-readiness state.
  Treat READY_FOR_REPLAY as authorisation for runtime changes.
```

---

## Source Documents

| Document | Role |
|---|---|
| `opening_scan_survival_audit.md` | Six-question evidence analysis; establishes the 30s cliff |
| `epoch_timing_outcome_audit.md` | Timing vs quote-source; confirms timing is the primary variable |
| `quote_source_outcome_audit.md` | Quote-source audit; result: spurious confound |
| `opening_scan_policy_candidate_design.md` | Policy A–E definitions; simulation effects; evidence requirements |
| `opening_scan_policy_replay_feasibility_audit.md` | Field presence audit; confirms JSONL can support D and B replay |
| `opening_scan_policy_evidence_monitor.md` | Cumulative trade counts; detailed session ledger; snapshot template |
| `opening_scan_disconfirmation_monitor.md` | Event log; classification rules; what breaks the edge |
| **This document** | Single-view dashboard; progress bars; ETA; snapshot history |
