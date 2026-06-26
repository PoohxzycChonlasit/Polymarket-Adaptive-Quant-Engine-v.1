# RISK_MODE_TRANSITION_TIMELINE_001

**Task:** DEFENSIVE_MODE_FORENSIC_VALIDATION_001  
**Mode:** DISCOVERY ONLY  
**Date:** 2026-06-25  
**Source:** risk_log/2026-06-25.jsonl, trade_journal/2026-06-25.jsonl

---

## Session Registry — June 25, 2026

| Session ID | Start UTC | End UTC | Cycles | Risk Modes Observed | Cash |
|---|---|---|---|---|---|
| `20260623T072817Z_36904_32fea5ff` | 02:31 | 02:39 | 3 | MICRO_RECOVERY | $20.14 (prior session) |
| `20260625T024001Z_2744_ec64fec3` | 02:46 | 06:18 | 209 | LOCKDOWN | $0.00 (ghost/test) |
| `20260625T045145Z–045154Z` (5 PIDs) | 04:51 | 04:51 | 1 each | NORMAL | $10K or $10 (test) |
| `20260625T052627Z_48728_55bb248a` | 05:26 | 05:28 | 3 | NORMAL | $20.10 (brief probe) |
| **`20260625T061908Z_44848_cb552b16`** | **06:19** | **10:01** | **216** | **NORMAL,DEFENSIVE** | **$20.10** |
| **`20260625T065019Z_20608_0bee180b`** | **06:50** | **14:23** | **442** | **NORMAL,DEFENSIVE,MICRO_RECOVERY** | **$20.10** |
| **`20260625T100130Z_42540_83ff6585`** | **10:01** | **14:22** | **259** | **NORMAL,DEFENSIVE** | **$20.10** |
| `20260625T125534Z–125548Z` (4 PIDs) | 12:55 | 12:55 | 1 each | NORMAL | $10K or $10 (test) |

**Bold rows = primary production sessions. Others = ghost/test/probe sessions.**

---

## Complete Trade Sequence — Primary Sessions

### Session `20260625T061908Z_44848_cb552b16`

| # | Time (UTC) | Market | Conf | Price | Notional | Mode | Result | cons_losses |
|---|---|---|---|---|---|---|---|---|
| T1 | 06:30:27 open / 06:30:55 close | ETH | 0.5603 | 0.57 | $0.100 | NORMAL | LOSS −$0.025 | 0→1 |
| — | 07:21:07 | — | — | — | — | **DEFENSIVE** | — | after T4 close |
| T4 | 07:20:11 open / 07:20:22 close | ETH | 0.5442 | 0.51 | $0.100 | NORMAL | LOSS −$0.012 | 1→2 |
| **→** | **07:21:07** | — | — | — | — | **NORMAL→DEFENSIVE** | — | cons=2 |
| T5 | 07:36:19 open / 07:37:22 close | BTC | 0.7448 | 0.51 | $0.064 | **DEFENSIVE** | **WIN +$0.010** | 2→0 |
| **→** | **07:39:21** | — | — | — | — | **DEFENSIVE→NORMAL** | — | cons=0 (WIN) |
| T6 | 07:46:28 open / 07:46:36 close | ETH | 0.5731 | 0.57 | $0.100 | NORMAL | LOSS −$0.016 | 0→1 |
| T8 | 08:25:11 open / 08:25:18 close | ETH | 0.5422 | 0.50 | $0.100 | NORMAL | LOSS −$0.020 | 1→2 |
| **→** | **08:26:07** | — | — | — | — | **NORMAL→DEFENSIVE** | — | cons=2 |
| **STALL** | 08:26→10:01 | — | — | — | — | **DEFENSIVE** | 0 trades | 1h 35m |

Session ended at 10:01 UTC. Replaced by session 100130Z.

---

### Session `20260625T065019Z_20608_0bee180b`

| # | Time (UTC) | Market | Conf | Price | Notional | Mode | Result | cons_losses |
|---|---|---|---|---|---|---|---|---|
| T2 | 06:55:34 open / 06:55:52 close | ETH | 0.5408 | 0.47 | $0.100 | NORMAL | LOSS −$0.021 | 0→1 |
| T3 | 07:05:39 open / 07:05:47 close | ETH | 0.5671 | 0.59 | $0.100 | NORMAL | LOSS −$0.014 | 1→2 |
| **→** | **07:06:36** | — | — | — | — | **NORMAL→DEFENSIVE** | — | cons=2 |
| T7 | 07:51:03 open / 07:51:11 close | BTC | 0.7348 | 0.49 | $0.050 | **DEFENSIVE** | LOSS −$0.020 | 2→3 |
| **→** | **07:52:00** | — | — | — | — | **DEFENSIVE→MICRO_RECOVERY** | — | cons=3 |
| T9 | 08:30:14 open / 08:31:33 close | ETH | 0.7518 | 0.60 | $0.025 | **MICRO_RECOVERY** | LOSS −$0.005 | 3→4 |
| **STALL** | 08:31→14:23 | — | — | — | — | **MICRO_RECOVERY** | 0 trades | 5h 52m |

Session terminated at 14:23 UTC without recovery.

---

### Session `20260625T100130Z_42540_83ff6585`

| # | Time (UTC) | Market | Conf | Price | Notional | Mode | Result | cons_losses |
|---|---|---|---|---|---|---|---|---|
| T10 | 10:05:44 open / 10:06:40 close | ETH | 0.5513 | 0.51 | $0.100 | NORMAL | **WIN +$0.077** | 0→0 |
| T11 | 10:15:50 open / 10:15:57 close | ETH | 0.5503 | 0.50 | $0.100 | NORMAL | LOSS −$0.014 | 0→1 |
| T12 | 10:25:57 open / 10:26:05 close | ETH | 0.5426 | 0.46 | $0.100 | NORMAL | LOSS −$0.011 | 1→2 |
| **→** | **10:26:55** | — | — | — | — | **NORMAL→DEFENSIVE** | — | cons=2 |
| **STALL** | 10:26→14:22 | — | — | — | — | **DEFENSIVE** | 0 trades | 3h 55m |

Session data last observed at 14:22 UTC.

---

## Risk Mode Transition Summary

| Timestamp | Session | Transition | Trigger | Duration Until Next |
|---|---|---|---|---|
| 07:06:36 | 065019Z | NORMAL→DEFENSIVE | cons_losses=2 (T3 close) | 45 min |
| 07:21:07 | 061908Z | NORMAL→DEFENSIVE | cons_losses=2 (T4 close) | 18 min |
| 07:39:21 | 061908Z | DEFENSIVE→NORMAL | WIN (T5 BTC) | 47 min |
| 07:52:00 | 065019Z | DEFENSIVE→MICRO_RECOVERY | cons_losses=3 (T7 close) | ~6 hours (no recovery) |
| 08:26:07 | 061908Z | NORMAL→DEFENSIVE | cons_losses=2 (T8 close) | ~95 min (session ends) |
| 10:26:55 | 100130Z | NORMAL→DEFENSIVE | cons_losses=2 (T12 close) | ~4 hours (no recovery) |

---

## Annotated Mode Chart

```
Time (UTC)  061908Z           065019Z           100130Z
────────────────────────────────────────────────────────
06:19       NORMAL ●start     
06:30       T1 LOSS
06:50                         NORMAL ●start
06:55                         T2 LOSS
07:05                         T3 LOSS
07:06                         ▼DEFENSIVE
07:20       T4 LOSS
07:21       ▼DEFENSIVE
07:36       T5 BTC WIN ✓
07:37       (T5 closed)
07:39       ▲NORMAL
07:46       T6 LOSS
07:51                         T7 BTC LOSS
07:52                         ▼MICRO_RECOVERY
08:25       T8 LOSS
08:26       ▼DEFENSIVE
08:30                         T9 ETH LOSS
08:31                         [STALL 5h 52m]
08:26→      [STALL]
10:01       ●session ends
10:01                                           NORMAL ●start (fresh)
10:05                                           T10 ETH WIN ✓
10:15                                           T11 LOSS
10:25                                           T12 LOSS
10:26                                           ▼DEFENSIVE
10:26→14:22                                     [STALL 3h 55m]
14:23                         ●session ends

▼ = mode escalation  ▲ = mode recovery  ✓ = WIN trade
```

---

## Consecutive Loss Counter Reconstruction

| Session | Trade | Outcome | cons_losses After |
|---|---|---|---|
| 061908Z | T1 | LOSS | 1 |
| 061908Z | T4 | LOSS | 2 → **DEFENSIVE** |
| 061908Z | T5 BTC | WIN | 0 → NORMAL |
| 061908Z | T6 | LOSS | 1 |
| 061908Z | T8 | LOSS | 2 → **DEFENSIVE** |
| — | — | — | — |
| 065019Z | T2 | LOSS | 1 |
| 065019Z | T3 | LOSS | 2 → **DEFENSIVE** |
| 065019Z | T7 BTC | LOSS | 3 → **MICRO_RECOVERY** |
| 065019Z | T9 ETH | LOSS | 4 → MICRO_RECOVERY (unchanged) |
| — | — | — | — |
| 100130Z | T10 | WIN | 0 |
| 100130Z | T11 | LOSS | 1 |
| 100130Z | T12 | LOSS | 2 → **DEFENSIVE** |

**Note:** `consecutive_losses` is never logged to the risk_log (always null). This reconstruction is derived from trade outcomes matched to risk mode transitions.

---

## Key Observations

1. **2 losses → DEFENSIVE in all 3 sessions** — pattern is consistent and predictable
2. **DEFENSIVE → recovery only via WIN** — confirmed once (T5 BTC WIN at 07:37)
3. **DEFENSIVE → MICRO_RECOVERY if next trade loses** — confirmed (T7 BTC LOSS at 07:51)
4. **MICRO_RECOVERY has no autonomous exit** — session 065019Z stalled 5h 52m without recovery
5. **Session restart = the only reliable recovery** — session 100130Z started fresh at 10:01 and immediately traded (T10 at 10:05)
6. **MICRO_RECOVERY + risk_plan_zero creates complete deadlock** — even BTC at 0.77–0.86 confidence blocked by sizing after MICRO_RECOVERY + consecutive losses

---

## Hold Duration Analysis

Short hold times indicate forced exits at epoch close, not stop-loss:

| Trade | Hold | Exit Reason |
|---|---|---|
| T1 | 28s | Epoch ending |
| T2 | 18s | Epoch ending |
| T3 | 7s | Epoch ending |
| T4 | 11s | Epoch ending |
| T5 | 63s | Epoch ending (WIN) |
| T6 | 7s | Epoch ending |
| T7 | 7s | Epoch ending |
| T8 | 7s | Epoch ending |
| T9 | 79s | Epoch ending (largest hold, LOSS) |
| T10 | 56s | Epoch ending (WIN) |
| T11 | 7s | Epoch ending |
| T12 | 7s | Epoch ending |

All trades were closed at epoch boundary (pre-close exit mechanism). No stop-loss triggered. The 7-second hold time is the minimum window between order placement and forced epoch exit.

**Short hold times (7–28s) mean positions close with adverse fill at epoch end** — they enter near the end of the epoch and are forced out. This contributes to the high loss rate: the entry model fires a signal but the epoch closes before favorable price movement can develop.
