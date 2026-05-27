# New Day Runtime + Gate Audit

Date: 2026-05-27 07:55 Asia/Bangkok

Scope: read-only morning audit. No code changes. No runtime changes. No replay. No strategy, risk, execution, or live changes.

## Role Routing

- Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`
- Supporting roles: `10_BACKTEST_REPLAY_AGENT.md`, `16_PAPER_EVALUATION_AGENT.md`
- Why selected: the task checks runtime health, path-truth gate progress, and evidence-candidate stability without changing runtime behavior.
- Files inspected: process list, `runtime/bot_status.json`, active log, `runtime/quant_data/path_truth/*.jsonl`, `runtime/quant_data/trade_journal/*.jsonl`, `runtime/quant_data/system_health/*.jsonl`, prior `docs/research/path_truth_multiday_coverage_monitor.md`.
- Files intentionally ignored: strategy modules, risk modules, execution modules, wallet/live config, replay execution paths, and runtime code.

## Runtime Health

Runtime status: **RUNNING**

Active paper bot process:

| Field | Value |
|---|---|
| Launcher PID | `58580` |
| Worker PID | `19460` |
| Command | `main.py --mode paper --interval 10 --ui compact --fps medium` |
| Start time | 2026-05-26 19:02:47 Asia/Bangkok |
| Active run_id | `20260526T120255Z_19460_52b2e66e` |
| Active log | `logs/polytrade_bot_20260526_190251_19460.log` |
| Bot status timestamp | 2026-05-27 07:52:37 Asia/Bangkok |
| Execution mode | `PAPER ONLY` |
| Risk mode | `MICRO_RECOVERY` |

Active log health:

| Check | Count |
|---|---:|
| log-level `ERROR` | 0 |
| log-level `CRITICAL` | 0 |
| `Traceback` | 0 |
| `FATAL` | 0 |
| write failures | 0 |
| Telegram failures | 0 |

Notes:

- The runtime is alive and continuing cycles.
- No shutdown marker, traceback, fatal, write failure, or Telegram failure was observed in the active log.
- Other Python processes include Hermes workers and one older unittest process; they were not touched.

## Path Truth Growth

Completed path-truth dates: **3**

Gate status:

| Gate | Requirement | Current | Verdict |
|---|---:|---:|---|
| `EARLY_RESEARCH_GATE` | 3 completed dates | 3 / 3 | READY |
| `IMPLEMENTATION_GATE` | 7 completed dates | 3 / 7 | BLOCKED |

Aggregate coverage across completed dates:

| Metric | Previous 2026-05-26 monitor | Current 2026-05-27 audit | Change |
|---|---:|---:|---:|
| completed dates | 2 | 3 | +1 |
| lines | 95 | 140 | +45 |
| trades | 51 | 88 | +37 |
| full coverage | 3 | 3 | 0 |
| fast close partial | 48 | 85 | +37 |
| parse errors | 0 | 0 | 0 |
| duplicate keys | 0 | 0 | 0 |

Completed date table:

| Date | Lines | Trades | Full Cov | Fast Close | Parse Err | Dup Keys |
|---|---:|---:|---:|---:|---:|---:|
| 2026-05-24 | 46 | 21 | 3 | 18 | 0 | 0 |
| 2026-05-25 | 49 | 30 | 0 | 30 | 0 | 0 |
| 2026-05-26 | 45 | 37 | 0 | 37 | 0 | 0 |

Read:

- 2026-05-26 added a clean completed date.
- The early research gate is now ready.
- The implementation gate remains blocked.
- Full coverage did not grow; fast-close partial evidence grew materially.
- No parse or duplicate-key regression was observed.

## Candidate Re-Check

Sample scope: trade closes from completed path-truth dates `2026-05-24` through `2026-05-26`.

Overall trade outcome sample:

| Scope | Trades | TP | SL | WR | PnL | Median Hold | Fast <60s |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-05-24 to 2026-05-26 | 105 | 31 | 74 | 29.5% | -0.180549 | 12s | 101 |
| Baseline 2026-05-24 to 2026-05-25 | 68 | 19 | 49 | 27.9% | -0.094310 | 12s | 64 |
| New date 2026-05-26 | 37 | 12 | 25 | 32.4% | -0.086239 | 11s | 37 |

### BTC

| Scope | Trades | TP | SL | WR | PnL | Read |
|---|---:|---:|---:|---:|---:|---|
| Baseline 2026-05-24 to 2026-05-25 | 27 | 2 | 25 | 7.4% | -0.096723 | hostile |
| New date 2026-05-26 | 14 | 4 | 10 | 28.6% | -0.097389 | improved WR, still negative |
| Current total | 41 | 6 | 35 | 14.6% | -0.194113 | stable hostile candidate |

Verdict: **stable BTC weakness**, though 2026-05-26 added a less extreme TP rate than the baseline. PnL remained negative and the combined sample is still strongly SL-heavy.

### NO

| Scope | Trades | TP | SL | WR | PnL | Read |
|---|---:|---:|---:|---:|---:|---|
| Baseline 2026-05-24 to 2026-05-25 | 31 | 9 | 22 | 29.0% | -0.070935 | weak |
| New date 2026-05-26 | 21 | 5 | 16 | 23.8% | -0.045165 | weak |
| Current total | 52 | 14 | 38 | 26.9% | -0.116100 | stable weak / session-dependent |

Verdict: **stable NO weakness**, still better interpreted as session-dependent rather than globally dead. New evidence did not improve the NO side.

### 02h

| Scope | Trades | TP | SL | WR | PnL | Read |
|---|---:|---:|---:|---:|---:|---|
| Baseline 2026-05-24 to 2026-05-25 | 5 | 0 | 5 | 0.0% | -0.039490 | hostile |
| New date 2026-05-26 | 3 | 1 | 2 | 33.3% | -0.002835 | slightly less hostile, still negative |
| Current total | 8 | 1 | 7 | 12.5% | -0.042325 | stable hostile candidate |

Verdict: **02h remains hostile**, but the new date softened the absolute loss with 1 TP / 2 SL. Sample is still small.

### 09h10h

| Scope | Trades | TP | SL | WR | PnL | Read |
|---|---:|---:|---:|---:|---:|---|
| Baseline 2026-05-24 to 2026-05-25 | 1 | 0 | 1 | 0.0% | -0.001221 | insufficient |
| New date 2026-05-26 | 2 | 0 | 2 | 0.0% | -0.034490 | negative |
| Current total | 3 | 0 | 3 | 0.0% | -0.035710 | weakens fresh support |

Verdict: **09h10h edge is not supported by the current 2026-05-24 to 2026-05-26 slice**. This does not fully invalidate older wider-session findings, but it reduces confidence and keeps the candidate insufficient.

## Gate Interpretation

```text
EARLY_RESEARCH_GATE_READY
IMPLEMENTATION_GATE_BLOCKED
```

What changed:

- Completed dates advanced from 2 / 3 to 3 / 3 for the early research gate.
- Implementation gate advanced from 2 / 7 to 3 / 7, still blocked.
- Fast-close behavior strengthened: 85 / 88 event-end trades are partial before full scheduled path coverage.

What did not change:

- Field wiring is still blocked.
- Strategy/risk/execution/live behavior remains untouched.
- Full path coverage remains shallow.
- Candidate evidence remains CAUTION-grade research evidence, not policy.

## Recommended Next Action

OPTION 1 - SAFE EV PRESERVATION:

Continue evidence farming until the implementation gate reaches 7 completed dates. This is the safest path because it preserves current runtime behavior and lets the path-truth dataset mature.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:

Run a read-only refresh of BTC / NO / 02h / 09h10h splits after the next completed date, with no replay and no runtime changes.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:

Prepare a docs-only field wiring readiness checklist for `quote_age_ms`, `candidate_id`, and `decision_id`, but do not implement until the 7-date gate is met.

Recommended: **OPTION 1 now**, with **OPTION 2** after the next completed date.

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Replay run: No

Tests: not run; docs-only/read-only audit.

Persistent tests unchanged.
