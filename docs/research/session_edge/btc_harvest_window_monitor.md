# BTC Harvest Window Monitor

Document type: read-only BTC active-window evidence accumulation tracker.

Created: 2026-05-23

Updated: 2026-05-23

Runtime behavior changed: No.

Live behavior changed: No.

Paper launch: No.

Replay run: No.

Code changed: No.

Tests: none, docs-only.

---

## Purpose

Track BTC evidence accumulation in the active windows identified by `btc_session_intelligence.md`:

- Primary window: 04h-05h UTC
- Secondary window: 12h UTC

Evidence outside these windows still counts toward the global BTC gate. The latest clean run added two BTC outcome-truth trades outside the active windows.

---

## Classification

Active-window state:

```text
BTC_BLOCKED
```

Global gate state:

```text
READY_FOR_PHASE6_REVIEW
```

Reason: active-window post-patch BTC outcome-truth count remains 0, but global BTC outcome-truth count is now 3 and clears the current BTC task gate.

---

## Latest Clean Run Snapshot

Latest clean run:

```text
20260522T163940Z_15384_a58a5171
```

| Metric | Latest clean run |
|---|---:|
| Paired | 6 |
| BTC | 2 |
| ETH | 4 |
| TP | 3 |
| SL | 3 |
| BTC TP | 0 |
| BTC SL | 2 |
| `market_analysis_exception` | 0 |
| 60s+ count | 1 |
| Mean `quote_age_at_submit_ms` | 22,815.579 |
| Mean `quote_age_at_fill_ms` | 22,816.736 |

The two latest BTC trades occurred at 17:55 UTC and 19:47 UTC, outside the defined 04h-05h and 12h BTC harvest windows.

---

## Gate Summary

| Gate | Required | Active-window count | Global count | Status |
|---|---:|---:|---:|---|
| BTC outcome-truth trades | >= 3 | 0 | 3 | GLOBAL MET / WINDOW BLOCKED |
| BTC TP outcomes | track only | 0 | 0 | NONE YET |
| BTC SL outcomes | track only | 0 | 3 | GLOBAL SL-HEAVY |

---

## Active Window Definitions

| Window | UTC hours | Why active | Historical BTC opens |
|---|---|---|---:|
| Primary | 04h-05h | 10 of 30 BTC opens; 6 of 12 BTC sessions started here | 10 |
| Secondary | 12h | 4 of 30 BTC opens; secondary cluster, STRONG depth observed | 4 |
| Total | | | 14 |

14 of 30 historical BTC opens occurred inside active windows, but all active-window historical BTC opens predate the outcome-truth patch.

---

## Post-Patch Session Coverage

Outcome-truth patch applied before first eligible run `20260522T094222Z_46088_040fac20`.

| Run | Start UTC | In 04-05h window? | In 12h window? | BTC entries | Active-window BTC OT | Note |
|---|---:|---|---|---:|---:|---|
| `094222Z_040fac20` | 09:42 | No | No | 0 | 0 | Missed both windows |
| `130017Z_035b3af7` | 13:05 | No | No | 1 | 0 | BTC SL at 15h, outside windows |
| `153403Z_65a54e7a` | 15:34 | No | No | 0 | 0 | ETH only |
| `162413Z_394d4a33` | 16:24 | No | No | 0 | 0 | ETH only |
| `163940Z_a58a5171` | 16:39 | No | No | 2 | 0 | Two BTC SL, outside windows |

Zero post-patch sessions have started during 04h-05h UTC. Zero post-patch sessions have produced BTC at the 12h window.

---

## Active-Window BTC Outcome-Truth Ledger

| Date | Window | Run | Result | PnL | Entry age | Depth | Conf |
|---|---|---|---|---:|---:|---|---:|
| - | - | no post-patch active-window sessions yet | - | - | - | - | - |

Current active-window count: 0.

---

## Global BTC Outcome-Truth Ledger

| Date | UTC time | Run | Window? | Result | PnL | Entry submit age | Entry fill age |
|---|---:|---|---|---|---:|---:|---:|
| 2026-05-22 | 15:10 | `130017Z_035b3af7` | No | SL | -0.020121 | 48.617s | 48.619s |
| 2026-05-22 | 17:55 | `163940Z_a58a5171` | No | SL | -0.004023 | 7.265s | 7.266s |
| 2026-05-22 | 19:47 | `163940Z_a58a5171` | No | SL | -0.004033 | 11.963s | 11.964s |

---

## Delta Vs Previous Monitor

| Field | Previous | Current | Delta |
|---|---:|---:|---:|
| Global BTC OT trades | 1 | 3 | +2 |
| Active-window BTC OT trades | 0 | 0 | 0 |
| BTC TP | 0 | 0 | 0 |
| BTC SL | 1 | 3 | +2 |
| Overall readiness | 79% | 89% | +10pp |

---

## Readiness Impact

| Global BTC OT | Old formula BTC contribution | Overall readiness | Current task BTC gate | Review state |
|---:|---:|---:|---|---|
| 1 previous | 20% | 79% | NOT MET | Not ready |
| 3 current | 60% | 89% | MET | READY_FOR_PHASE6_REVIEW |
| 5 future | 100% | 97% | MET | Stronger BTC count |

---

## What Still Needs Active-Window Evidence

The global BTC gate is clear, but the active-window thesis remains unproven post-patch. A first active-window BTC outcome-truth trade would confirm:

1. Active-window sessions still produce BTC entries after the outcome-truth patch.
2. Active-window BTC entries carry direct `trade_result` and `pnl_usdc`.
3. Active-window quote age is measurable.
4. Active-window BTC does not depend on the later 17h-19h sample.

---

## Exactly Three Future Options

### OPTION 1 - SAFE EV PRESERVATION

Thesis: proceed to Phase 6 review while preserving the active-window caveat.

Quant logic: global BTC count and readiness gates are met, but active-window BTC remains unobserved post-patch.

Likely outcome: review can distinguish global evidence readiness from active-window scheduling evidence.

Hidden risk: treating global BTC readiness as proof of active-window harvest quality would overstate the schedule thesis.

Recommended action: open Phase 6 review; keep active-window monitor open.

### OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY

Thesis: run a 04h-05h UTC session before review to add active-window BTC truth.

Quant logic: historical BTC opens concentrate in 04h-05h UTC, but none have outcome truth yet.

Likely outcome: one active-window session may add 1-3 BTC outcome-truth trades.

Hidden risk: a window run may still produce no BTC entries.

Recommended action: schedule one clean paper session in the primary BTC window if review quality needs the window thesis.

### OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

Thesis: split BTC readiness into global count readiness and window thesis readiness.

Quant logic: global count gates can be met outside active windows, while the harvest-window hypothesis remains blocked.

Likely outcome: cleaner future monitoring and less confusion.

Hidden risk: additional readiness layers may complicate dashboard presentation.

Recommended action: keep this monitor separate from the daily Phase 6 readiness score.

---

## Recommendation

```text
READY_FOR_PHASE6_REVIEW
```

Global BTC count and readiness gates are met. Active-window evidence remains blocked. Do not promote S3 or change runtime policy.
