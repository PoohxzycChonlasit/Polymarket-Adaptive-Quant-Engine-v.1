# Session Personality Stability Audit

Generated: 2026-05-23  
Scope: read-only stability audit across all historical JSONL dates.  
Hours are UTC.

No code, replay, runtime, policy, strategy, risk, execution, live, or S3 changes were made.

## Sources

- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/execution_log/*.jsonl`
- `runtime/quant_data/decision_log/*.jsonl`

Dates:

`2026-05-08`, `2026-05-09`, `2026-05-10`, `2026-05-11`, `2026-05-12`, `2026-05-13`, `2026-05-14`, `2026-05-15`, `2026-05-17`, `2026-05-18`, `2026-05-19`, `2026-05-20`, `2026-05-21`, `2026-05-22`, `2026-05-23`.

## Method And Caveats

- Confirmed `TP/SL` uses `trade_result` when present.
- Legacy `W/L` uses PnL sign where `trade_result` is missing.
- OPENING / ACTIVE use joined ENTRY `paper_fill` lifecycle and elapsed fields when available.
- Older rows often lack lifecycle, quote staleness, and outcome truth. Stability classifications are therefore conservative.

Legend:

- `.` = no closed trades in that hour/date.
- `xT/yS` = confirmed TP/SL.
- `xW/yL` = legacy PnL-sign proxy.

## Hour x Date Matrix

| Hour | 2026-05-08 | 2026-05-09 | 2026-05-10 | 2026-05-11 | 2026-05-12 | 2026-05-13 | 2026-05-14 | 2026-05-15 | 2026-05-17 | 2026-05-18 | 2026-05-19 | 2026-05-20 | 2026-05-21 | 2026-05-22 | 2026-05-23 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 00h | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . |
| 01h | . | . | . | . | 3W/0L | 2W/0L | . | . | . | . | . | . | . | . | 1T/1S |
| 02h | . | . | . | . | 2W/0L | 4W/0L | . | 46W/6L | . | 0W/2L | 1W/1L | 0W/1L | 0W/2L | 0W/2L | 0T/8S |
| 03h | . | . | . | . | 4W/0L | . | . | 2W/0L | . | 1W/2L | 1W/1L | . | 0W/1L | 3W/1L | 0T/1S |
| 04h | 16W/4L | . | . | . | 4W/0L | 1W/0L | . | 56W/6L | . | 3W/1L | . | 0W/1L | 3W/3L | 1W/3L | . |
| 05h | . | . | . | . | 2W/0L | . | . | . | . | 1W/3L | 0W/3L | . | 1W/2L | 3W/3L | . |
| 06h | . | . | . | . | 3W/0L | . | . | 36W/4L | . | 2W/0L | . | . | 3W/1L | 3W/4L | . |
| 07h | . | . | . | . | 3W/0L | 2W/0L | . | . | . | 0W/2L | . | . | 0W/2L | 0W/4L | . |
| 08h | . | . | . | . | . | . | . | . | . | 1W/0L | 2W/2L | . | . | 5W/2L | . |
| 09h | . | 7W/2L | . | . | 6W/0L | . | . | . | . | 0W/2L | 4W/0L | 2W/2L | 0W/1L | 1T/1S | 4T/0S |
| 10h | . | 7W/2L | . | . | 1W/0L | . | . | . | . | . | 1W/0L | 1W/3L | 0W/1L | 1T/1S | 1T/0S |
| 11h | 24W/6L | . | . | . | . | . | 37W/4L | . | . | . | 2W/2L | 3W/1L | 0W/1L | . | . |
| 12h | 42W/10L | 2W/0L | . | . | 1W/0L | . | . | . | . | . | 2W/0L | 2W/1L | . | 0T/1S | . |
| 13h | 32W/8L | 3W/0L | 3W/0L | . | . | . | 18W/2L | . | . | . | 2W/1L | 2W/0L | 1W/1L | 1T/2S | . |
| 14h | . | 1W/0L | . | . | . | 2W/0L | . | . | . | . | 1W/2L | 1W/1L | 2W/2L | . | . |
| 15h | . | 16W/4L | . | . | . | . | . | . | . | . | . | 1W/2L | 0W/1L | 0T/2S | . |
| 16h | . | 13W/4L | . | 4W/0L | . | . | . | . | . | . | 3W/1L | . | . | 2T/1S | . |
| 17h | . | 1W/0L | . | 7W/0L | . | . | . | . | . | . | 0W/1L | . | . | 1T/2S | . |
| 18h | 17W/4L | . | . | . | . | . | . | . | . | . | . | . | . | . | . |
| 19h | 1W/0L | 1W/0L | . | . | . | . | . | . | . | . | . | . | . | 0T/1S | . |
| 20h | 8W/2L | 16W/4L | . | . | . | . | . | . | . | . | . | . | . | . | . |
| 21h | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . |
| 22h | . | . | . | . | . | . | . | . | . | . | . | . | 0W/1L | . | . |
| 23h | . | . | . | . | . | . | . | . | . | . | . | . | . | . | . |

## Stability Summary

| Hour | Active Dates | Win Dates | Loss Dates | Confirmed TP | Confirmed SL | OPENING Positive Dates | ACTIVE Positive Dates | Mean Date PnL | Stability Class | Personality |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 00h | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | UNSTABLE | unstable session |
| 01h | 3 | 2 | 0 | 1 | 1 | 1 | 0 | +0.667042 | UNSTABLE | unstable session |
| 02h | 9 | 3 | 5 | 0 | 8 | 1 | 0 | +0.265611 | UNSTABLE | chop recurring |
| 03h | 7 | 3 | 3 | 0 | 1 | 2 | 0 | +0.330842 | LEGACY_BIASED | chop recurring |
| 04h | 8 | 5 | 2 | 0 | 0 | 2 | 0 | +0.362339 | LEGACY_BIASED | chop recurring |
| 05h | 5 | 1 | 3 | 0 | 0 | 1 | 0 | +0.200161 | UNSTABLE | chop recurring |
| 06h | 5 | 4 | 1 | 0 | 0 | 2 | 2 | +0.279418 | STABLE_SESSION_EDGE | stable trend session |
| 07h | 5 | 2 | 3 | 0 | 0 | 0 | 0 | +0.395394 | UNSTABLE | chop recurring |
| 08h | 3 | 2 | 0 | 0 | 0 | 3 | 1 | +0.015591 | UNSTABLE | opening recurring |
| 09h | 8 | 4 | 3 | 5 | 1 | 3 | 1 | +0.179540 | UNSTABLE | opening recurring |
| 10h | 7 | 4 | 2 | 2 | 1 | 1 | 2 | +0.206355 | LEGACY_BIASED | trend candidate |
| 11h | 5 | 3 | 1 | 0 | 0 | 2 | 0 | +0.177506 | LEGACY_BIASED | unstable session |
| 12h | 6 | 5 | 1 | 0 | 1 | 2 | 0 | +0.421392 | LEGACY_BIASED | unstable session |
| 13h | 8 | 6 | 1 | 1 | 2 | 4 | 1 | +0.360969 | LEGACY_BIASED | opening recurring |
| 14h | 5 | 2 | 1 | 0 | 0 | 2 | 0 | +0.399028 | LEGACY_BIASED | unstable session |
| 15h | 4 | 1 | 3 | 0 | 2 | 1 | 0 | +0.115971 | UNSTABLE | chop recurring |
| 16h | 4 | 4 | 0 | 2 | 1 | 2 | 0 | +0.374834 | STABLE_SESSION_EDGE | stable trend session |
| 17h | 4 | 2 | 2 | 1 | 2 | 0 | 0 | +0.498445 | UNSTABLE | chop recurring |
| 18h | 1 | 1 | 0 | 0 | 0 | 0 | 0 | +0.513333 | UNSTABLE | unstable session |
| 19h | 3 | 2 | 1 | 0 | 1 | 0 | 0 | +0.665322 | UNSTABLE | unstable session |
| 20h | 2 | 2 | 0 | 0 | 0 | 0 | 0 | +0.489000 | UNSTABLE | unstable session |
| 21h | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | UNSTABLE | unstable session |
| 22h | 1 | 0 | 1 | 0 | 0 | 0 | 0 | -0.002402 | UNSTABLE | unstable session |
| 23h | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | UNSTABLE | unstable session |

## Key Questions

### Is 09h stable?

No. 09h is promising but unstable.

Evidence:

- Active dates: 8.
- Win dates: 4.
- Loss dates: 3.
- Mixed dates: 1.
- Confirmed outcome-truth is favorable: 5 TP / 1 SL.
- 2026-05-23 was excellent at 4T/0S, but 2026-05-18, 2026-05-21, and 2026-05-22 were negative or mixed.

Interpretation: 09h survives as a session candidate, but not as a stable session edge.

Classification: `UNSTABLE`

### Is 02h always chop?

No, but recent outcome-truth says 02h is currently chop.

Evidence:

- Active dates: 9.
- Win dates: 3.
- Loss dates: 5.
- Confirmed outcome-truth: 0 TP / 8 SL.
- 2026-05-12, 2026-05-13, and 2026-05-15 legacy rows were positive.
- 2026-05-18 through 2026-05-23 skew negative, with 2026-05-23 at 0T/8S.

Interpretation: not always chop historically, but current Phase 6 evidence makes 02h a recurring chop/risk session until proven otherwise.

Classification: `UNSTABLE`

### Are 01h / 14h recurring?

01h:

- Active dates: 3.
- Positive legacy dates: 2026-05-12 and 2026-05-13.
- 2026-05-23 confirmed result: 1T/1S.
- Too few modern samples.

14h:

- Active dates: 5.
- Win dates: 2.
- Loss dates: 1.
- Mixed dates: 2.
- No confirmed TP/SL.
- Legacy-biased and inconsistent.

Interpretation: 01h and 14h are weak opening/session candidates, not stable recurrence.

Classification: `LEGACY_BIASED` for 14h, `UNSTABLE` for 01h.

### Which session survives cross-date?

Best cross-date survivors:

1. 06h - `STABLE_SESSION_EDGE`, but legacy-heavy.
   - Active dates: 5.
   - Win dates: 4.
   - Loss dates: 1.
   - OPENING positive dates: 2.
   - ACTIVE positive dates: 2.
   - Needs modern outcome-truth confirmation.

2. 16h - `STABLE_SESSION_EDGE`, but still thin.
   - Active dates: 4.
   - Win dates: 4.
   - Loss dates: 0.
   - Confirmed outcome-truth: 2 TP / 1 SL.
   - More promising than most legacy-heavy hours.

3. 09h - `UNSTABLE`, but highest modern relevance.
   - Active dates: 8.
   - Confirmed outcome-truth: 5 TP / 1 SL.
   - Not stable across dates, but strongest Phase 6 session candidate.

## Final Classification

Overall classification: `UNSTABLE`

Reason:

- The most interesting modern session, 09h, is not stable across dates.
- The most stable cross-date sessions, 06h and 16h, are partly legacy-biased and need more Phase 6 outcome truth.
- 02h is not always chop historically, but recent Phase 6 evidence is strongly adverse.

## Practical Read

- Keep 09h as a high-priority evidence window, not a hard policy window.
- Treat 02h as a current chop/risk window.
- Track 06h and 16h for recurrence under modern outcome-truth fields.
- Do not promote any hour into runtime policy from this audit alone.

Runtime behavior changed: No  
Live behavior changed: No  
Tests: not run, docs-only  
Persistent tests unchanged
