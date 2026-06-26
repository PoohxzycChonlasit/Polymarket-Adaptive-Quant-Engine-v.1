# RISK_PLAN_ZERO_DISTRIBUTION_001

**Task:** MICRO_RECOVERY_RISK_PLAN_ZERO_AUDIT_001  
**Mode:** DISCOVERY ONLY  
**Date:** 2026-06-25  
**Source:** decision_log/2026-06-25.jsonl — risk_plan_zero events with confidence ≥ 0.75

---

## Overview

This document characterizes the 53 `risk_plan_zero` events from the post-DEFENSIVE window (08:32–14:25 UTC, June 25) that PASSED the MICRO_RECOVERY confidence floor (0.75) yet produced zero sizing.

---

## 1. Sample of 10 Extracted Events (14:10–14:25 UTC)

| Timestamp UTC | Session Mode | Composite Conf | NO Ask Price | Raw p_no | Time Rem | freq_mult | Block Reason |
|---|---|---|---|---|---|---|---|
| 14:16:33 | MICRO_RECOVERY | 0.8551 | 0.08 | 0.2607 | 207s | 1.0 | confidence_too_low |
| 14:16:43 | DEFENSIVE | 0.8633 | 0.06 | 0.2548 | 197s | 1.0 | confidence_too_low |
| 14:17:34 | MICRO_RECOVERY | 0.8449 | 0.17 | 0.2679 | 146s | 1.0 | confidence_too_low |
| 14:17:44 | DEFENSIVE | 0.8057 | 0.08 | 0.2959 | 137s | 1.0 | confidence_too_low |
| 14:20:41 | MICRO_RECOVERY | 0.7751 | 0.23 | 0.3178 | 260s | 1.0 | confidence_too_low |
| 14:20:48 | DEFENSIVE | 0.7896 | 0.26 | 0.3074 | 253s | 1.0 | confidence_too_low |
| 14:21:37 | MICRO_RECOVERY | 0.8402 | 0.11 | 0.2713 | 203s | 1.0 | confidence_too_low |
| 14:21:45 | DEFENSIVE | 0.8418 | 0.11 | 0.2702 | 196s | 1.0 | confidence_too_low |
| 14:22:39 | MICRO_RECOVERY | 0.8298 | 0.13 | 0.2787 | 142s | 1.0 | confidence_too_low |
| 14:22:45 | DEFENSIVE | 0.8384 | 0.11 | 0.2725 | 135s | 1.0 | confidence_too_low |

All 10 sampled events show `confidence_too_low` as the underlying block reason in sizing diagnostics.

---

## 2. Key Metric Ranges (All Sampled Events)

| Metric | Min | Max | Notes |
|---|---|---|---|
| Composite confidence | 0.7751 | 0.8633 | All > MICRO_RECOVERY floor (0.75) |
| Raw p_no (entry_price + edge) | 0.2548 | 0.3178 | All < sizing floor (0.54) |
| NO entry price | 0.06 | 0.26 | BTC trending bullish — NO is cheap |
| Edge | 0.0474 | 0.2159 | All positive |
| Time remaining | 135s | 260s | All well above 90s threshold |
| frequency_multiplier | 0.5–1.0 | — | Not 0.0, not blocking |
| delta_multiplier | 0.5–0.8 | — | Not zero |
| Block reason (sizing) | confidence_too_low | confidence_too_low | Unanimous |

---

## 3. Session Attribution

The events alternate between two concurrent sessions at ~10-second intervals:

```
14:16:33 → 065019Z (MICRO_RECOVERY)
14:16:43 → 100130Z (DEFENSIVE)
14:17:34 → 065019Z
14:17:44 → 100130Z
...
```

The same BTC market condition triggers identical `risk_plan_zero` blocks in both sessions simultaneously. Both sessions evaluate the same BTC candidate within 10 seconds of each other and both are blocked by `confidence_too_low` in sizing.

**No session-specific factor:** The block is identical across MICRO_RECOVERY and DEFENSIVE modes because the sizing confidence check (`p_no < 0.54`) is mode-independent.

---

## 4. Composite Confidence vs Raw Probability — The Mismatch

```
Composite Confidence (used at risk mode gate, passes):
  0.86  █████████████████████████████████████████████████████
  0.85  ██████████████████████████████████████████████████
  0.84  █████████████████████████████████████████████████
  0.81  ██████████████████████████████████████████████
  0.79  ████████████████████████████████████████████
  0.78  ████████████████████████████████████████████
  0.84  █████████████████████████████████████████████████
  0.84  █████████████████████████████████████████████████
  0.83  ████████████████████████████████████████████████
  0.84  █████████████████████████████████████████████████
        ────────────────────── MICRO_RECOVERY GATE = 0.75 ──────

Raw p_no (used in sizing, blocked):
  0.26  ██████
  0.25  █████
  0.27  ██████
  0.30  ███████
  0.32  ████████
  0.31  ████████
  0.27  ██████
  0.27  ██████
  0.28  ███████
  0.27  ██████
        ────────────────────── SIZING FLOOR = 0.54 ─────────────
        ← ALL BELOW FLOOR
```

**The composite confidence (0.77–0.86) is 2.6–3.4× the raw p_no (0.25–0.32).** The gap is large enough that no plausible recalibration of the sizing floor within the 0.54–0.75 range would allow these NO bets to pass.

---

## 5. Why p_no is Structurally Low for BTC NO Bets

BTC 5-minute market mechanics on June 25:
- BTC was in `TREND_UP` regime (confirmed from decision_log: `market_regime: TREND_UP`)
- In a bullish regime, the YES outcome (BTC goes up) is heavily favored
- YES ask price was high (0.92+), NO ask price was low (0.06–0.26)
- The model identifies NO as underpriced (edge positive), producing high composite confidence
- But p_no — the raw model probability — remains structurally low (~0.26) in a bullish market

The composite confidence inflates the "attractiveness" of the NO bet by weighting regime alignment and indicator signals. But the raw probability (p_no=0.26) is the actual prediction for the outcome.

The sizing function treats p_no as the "confidence" metric and applies the 0.54 floor. In bullish BTC conditions where p_no ≈ 0.26–0.32, this floor can never be met.

---

## 6. Timing of risk_plan_zero Occurrences — Session Duration

The 53 risk_plan_zero events for BTC at conf ≥ 0.75 are distributed across the post-08:31 window:

| Window | Approx Count | Mode |
|---|---|---|
| 08:31–10:00 | ~10 (est.) | 065019Z=MICRO_RECOVERY, 061908Z=DEFENSIVE |
| 10:00–10:26 | ~5 (est.) | 065019Z=MICRO_RECOVERY, 100130Z=NORMAL |
| 10:26–14:25 | ~38 (est.) | 065019Z=MICRO_RECOVERY, 100130Z=DEFENSIVE |

The events occur throughout the entire post-DEFENSIVE window. They are NOT triggered by MICRO_RECOVERY — they also occur in DEFENSIVE and even in the 10:00–10:26 window when 100130Z was in NORMAL mode. This confirms the block is mode-independent.

---

## 7. Frequency Multiplier Behavior

For T0_MICRO_SEED (`max_trades_per_hour=4`) after T9 at 08:31:

| Time Window | trades_last_hour | used_ratio | freq_mult | Max Reached? |
|---|---|---|---|---|
| 08:31–09:31 | 0 (T9 falls out at 09:31) | 0/4 = 0% | 1.0 | No |
| 09:31+ | 0 | 0% | 1.0 | No |

Frequency multiplier remained 1.0 throughout the post-08:31 stall. This eliminates frequency throttle as a contributing factor.

---

## 8. `micro_position_size` Diagnostic Field

All events show `micro_position_size: 0.1` (or `0.10`). This is the hypothetical rescue output — what the micro_survival plan WOULD produce if the rescue condition were met. It is computed and logged for observability but the rescue never executes because:

```
blocked_reasons = ["confidence_too_low"] ≠ {"below_min_position_size"}
→ rescue aborted at polymarket/trader.py:717
```

---

## 9. Comparison: Executed BTC Trades vs Blocked BTC NO Bets

| Property | T5 BTC (EXECUTED) | T7 BTC (EXECUTED) | Blocked BTC NO bets |
|---|---|---|---|
| Side | YES | YES | NO |
| Composite confidence | 0.7448 | 0.7348 | 0.775–0.863 |
| Entry price | ~0.51 | ~0.49 | 0.06–0.26 |
| Raw win_rate passed to sizing | p_yes ≈ 0.7448 | p_yes ≈ 0.7348 | p_no ≈ 0.26–0.32 |
| Sizing floor | 0.54 | 0.54 | 0.54 |
| Sizing confidence check | 0.74 > 0.54 ✓ PASS | 0.73 > 0.54 ✓ PASS | 0.26 < 0.54 ✗ FAIL |
| Result | Executed $0.064 | Executed $0.050 | risk_plan_zero |

BTC YES trades executed because p_yes (0.73–0.74) was above the sizing floor. BTC NO trades are blocked because p_no (0.26–0.32) is below the sizing floor. This is not a risk mode effect — it is an asymmetry between YES and NO bet sizability at the current market regime.

---

## 10. Summary

| Metric | Value |
|---|---|
| Total risk_plan_zero events (high conf BTC, post-DEFENSIVE) | 53 |
| Events sampled and analyzed | 10 (100% consensus on root cause) |
| Root cause | confidence_too_low in sizing (p_no < 0.54 floor) |
| Contributing mode factor | None — mode-independent |
| Timing block? | No (time_remaining 135–260s) |
| Frequency block? | No (freq_mult 1.0) |
| Spread block? | No (spread 0.01 << max_spread 0.10) |
| Liquidity block? | No (liq 1200+ >> min 10.0) |
| Rescue path? | Blocked (wrong blocked_reason type) |
| Mode-specific to MICRO_RECOVERY? | No |
