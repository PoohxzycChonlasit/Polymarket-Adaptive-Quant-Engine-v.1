# Morning Runtime Health Check

Date: 2026-05-24

Checked at: 2026-05-24 18:57 Asia/Bangkok

Scope: read-only runtime health, path truth growth, Telegram UX evidence, coverage gate, and field-gap status. No code changes. No runtime changes.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Runtime Health

Verdict: **RUNNING**

Evidence:

- Active project runtime process:
  - PID `26444`
  - Command: `main.py --mode paper --interval 10 --ui compact --fps medium`
  - Started: 2026-05-24 12:27:40 Asia/Bangkok
- Two additional Python processes are `hermes_worker.py`; they are not the canonical `main.py` paper loop.
- `runtime/bot_status.json` was fresh at 2026-05-24 18:56:55 Asia/Bangkok.
- Latest app log `logs/polytrade_bot_20260524_122741_26444.log` was fresh at 2026-05-24 18:56:59 Asia/Bangkok.
- Latest scan CSV `runtime/realtime_logs/2026-05-24/scan_log_20260524_122744_26444.csv` was fresh at 2026-05-24 18:56:56 Asia/Bangkok.
- Latest active summary observed:
  - cycles: 2080+
  - markets: 3808+
  - orders: 18
  - fills: 18
  - exits: 9
  - risk mode: MICRO_RECOVERY
  - runtime continues scanning and writing fresh logs.

Errors / tracebacks:

- Active run `polytrade_bot_20260524_122741_26444.log`: 0 actual `ERROR`, `CRITICAL`, `Traceback`, or `PermissionError` matches.
- Active run warnings exist, mainly orderbook empty-book/transient readiness warnings. No observed crash or traceback.
- Earlier completed run `polytrade_bot_20260524_113314_29264.log` had 18 `CRITICAL` reconciliation lines from `PARTIALLY_HEDGED_ARB` / `PARTIAL_ARB_REQUIRES_UNWIND`. The safety block fired; no path-truth write failure was observed.
- Completed runs show `OracleFeed Stopped.` shutdown markers at:
  - `polytrade_bot_20260524_003616_15948.log`: 11:33:10
  - `polytrade_bot_20260524_113314_29264.log`: 11:52:05
  - `polytrade_bot_20260524_115211_24036.log`: 12:27:38
- Active run has no shutdown marker because it is still running.

Runtime interpretation:

The paper loop is alive and writing fresh status/log/CSV/JSONL evidence. The main caution is not liveness; it is prior reconciliation criticals and ongoing orderbook/readiness warnings. No runtime behavior change is authorized by this review.

## Path Truth Growth

Verdict: **GROWING_AND_PARSEABLE**

Path truth files:

| Metric | Value |
|---|---:|
| File count | 1 |
| Latest file | `runtime/quant_data/path_truth/2026-05-24.jsonl` |
| Latest file size | 55,404 bytes |
| Latest file last write | 2026-05-24 14:50:36 Asia/Bangkok |
| JSONL line count | 37 |
| Parse errors | 0 |
| Distinct runs | 3 |
| Distinct trades | 15 |

Growth:

- First checkpoint validation had 11 lines.
- Previous monitor revision had 14 lines.
- Current file has 37 lines.
- New events since first validation: 26.
- New events since prior monitor revision: 23.

Run distribution:

| Run ID | Events | Trades |
|---|---:|---:|
| `20260524T043315Z_29264_52c95bee` | 11 | 3 |
| `20260524T045213Z_24036_f64d2821` | 4 | 3 |
| `20260524T052743Z_26444_0defea84` | 22 | 9 |

Checkpoint coverage:

| Checkpoint | Count |
|---|---:|
| 15s | 10 |
| 30s | 5 |
| 45s | 4 |
| 60s | 3 |
| event_end | 15 |

Trade coverage:

- Full coverage trades: 3
- Fast-close partial trades: 12
- Eligible trades open >= 60s: 3
- Eligible full coverage: 3 / 3 = 100%
- Duplicate checkpoint keys: 0
- Path truth write errors in inspected logs: 0

Partial coverage classification:

| Classification | Count |
|---|---:|
| FAST_CLOSE_BEFORE_FIRST_CHECKPOINT | 5 |
| FAST_CLOSE_BEFORE_SECOND_CHECKPOINT | 5 |
| FAST_CLOSE_BEFORE_THIRD_CHECKPOINT | 1 |
| FAST_CLOSE_BEFORE_60S_CHECKPOINT | 1 |

Interpretation:

The path truth writer is producing usable checkpoint sequences. Partial rows are explained by fast closes before scheduled checkpoint times, not by observed scheduler failure. No parse errors, duplicate keys, or write exceptions were found.

## Telegram Health

Verdict: **SEND_TELEMETRY_HEALTHY; MESSAGE_BODY_AUDIT_LIMITED**

Telegram evidence came from `runtime/quant_data/system_health/2026-05-24.jsonl`. No Telegram messages were sent by this review.

Telemetry summary:

| Event | Count |
|---|---:|
| `telegram_route_attempt` | 47 |
| `telegram_send_success` | 42 |
| `telegram_suppressed_cooldown` | 5 |
| `telegram_send_failure` | 0 |

Route summary:

| Route / Event | Count |
|---|---:|
| startup attempts | 3 |
| startup successes | 3 |
| entry attempts | 19 |
| entry successes | 19 |
| exit attempts | 19 |
| exit successes | 19 |
| incident attempts | 6 |
| incident successes | 1 |
| incident cooldown suppressions | 5 |

Findings:

- Telegram delivery telemetry is working: success events include HTTP `200` and `telegram_ok=true`.
- No Telegram send failures were found.
- Incident cooldown suppression is working: 5 repeated incident alerts were suppressed.
- No evidence of raw scan/orderbook spam being sent to Telegram; visible Telegram routes are startup, entry, exit, and incident.
- ENTRY and EXIT route telemetry is present and matched by send success.

Format verification limits:

- Current logs/JSONL do not persist the actual Telegram message body.
- Therefore, `ENTRY OPENED`, `EXIT CLOSED`, `PAPER / SIGNAL`, and `Dust Zone` labels cannot be directly proven from sent-message logs alone.
- The route and delivery telemetry are healthy, but message-body UX verification remains indirect unless future telemetry records a safe, redacted template id or label set.

## Coverage Gate

Verdict: **INSUFFICIENT_DATES**

Gate status:

| Gate | Status |
|---|---|
| Completed dates with data >= 7 | No, 1 / 7 |
| Latest date parse errors = 0 | Yes |
| Latest date write errors = 0 | Yes |
| Latest date duplicate keys = 0 | Yes |
| Latest date eligible full coverage >= 80% | Yes, 100% |
| Ready for field wiring | No |

Coverage interpretation:

The single available date is stable, but the multi-day gate is closed. Do not wire `quote_age_ms`, `candidate_id`, or `decision_id` yet.

## Field Gap Status

Tracked fields:

| Field | Present / 37 | Missing % | Trend | Regression |
|---|---:|---:|---|---|
| `quote_age_ms` | 0 | 100% | unchanged from 11-line and 14-line checks | No new regression; persistent known gap |
| `candidate_id` | 0 | 100% | unchanged from 11-line and 14-line checks | No new regression; persistent known gap |
| `decision_id` | 0 | 100% | unchanged from 11-line and 14-line checks | No new regression; persistent known gap |

Interpretation:

The gaps remain exactly where expected. This is not a newly worsening field-coverage regression; it is the same known field-carry / quote-age serialization problem documented in `docs/research/path_truth/path_truth_field_coverage_gap_audit.md`.

## Next Action

OPTION 1 - SAFE EV PRESERVATION:
Keep the current paper loop collecting evidence without any code or runtime changes. This protects the current stable path truth writer and waits for more dates before field wiring.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:
Continue paper collection through additional sessions and update the monitor after every completed date. Focus on increasing date count and capturing whether eligible coverage stays >= 80% under different market conditions.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:
After 7 stable dates, open a separate scoped wiring task for `quote_age_ms`, `candidate_id`, and `decision_id`. Do not bundle that with strategy, risk, execution, stop-loss, live mode, or Telegram-send behavior.

Recommendation: **OPTION 1 now, OPTION 2 as the operational follow-up.**

No code changes. No runtime changes. No live changes. No strategy/risk/execution changes.

## Final Status

Files updated:

- `docs/research/path_truth/path_truth_multiday_coverage_monitor.md`
- `docs/research/morning_runtime_health_check.md`

Tests: not run; docs-only evidence review.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No
