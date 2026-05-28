# New Day Runtime + Research State Audit

Date: 2026-05-26 09:30 Asia/Bangkok

Scope: read-only audit. No code changes. No runtime changes. No field wiring. No strategy, stoploss, risk, execution, or live changes.

Role routing:

- Primary: `11_OBSERVABILITY_INCIDENT_AGENT.md`
- Supporting: `10_BACKTEST_REPLAY_AGENT.md`, `16_PAPER_EVALUATION_AGENT.md`, `07_TEST_CI_AGENT.md`
- Files inspected: active Python process list, `runtime/bot_status.json`, latest `logs/polytrade_bot_*.log`, `runtime/quant_data/path_truth/*.jsonl`, recent `runtime/quant_data/system_health/*.jsonl`, `runtime/quant_data/trade_journal/*.jsonl`, `utils/display.py`, `docs/research/path_truth/path_truth_multiday_coverage_monitor.md`
- Files intentionally ignored: strategy/risk/execution/live config files except the display surface needed for header-strip verification

## Runtime Health

Runtime status: **RUNNING**

Active paper bot process:

| Field | Value |
|---|---|
| Active PID | `52872` |
| Launcher PID | `53860` |
| Command | `main.py --mode paper --interval 10 --ui compact --fps medium` |
| Start time | 2026-05-25 21:54:12 Asia/Bangkok |
| Active run_id | `20260525T145417Z_52872_1761df0e` |
| Active log | `logs/polytrade_bot_20260525_215415_52872.log` |
| Bot status timestamp | 2026-05-26 09:22:32 Asia/Bangkok |

Log health for the active log:

| Check | Count / Status |
|---|---:|
| log-level `ERROR` | 0 |
| log-level `CRITICAL` | 0 |
| `FATAL` | 0 |
| `Traceback` | 0 |
| write failures | 0 |
| Telegram errors | 0 |
| shutdown markers | none observed |

Notes:

- The log contains orderbook recovery warnings for expected empty-book paths, but no fatal, traceback, write, or Telegram failure was observed.
- Latest summary lines show the process still cycling and writing health. Recent summary state included `orders=8`, `fills=8`, `exits=4`, `entered=4`, `pnl=-0.0307`, `risk_mode=MICRO_RECOVERY`.
- No processes were stopped.

## Header Research Strip

Stage 1 Research Header Strip status: **present in display code and locally renderable**

Static/display verification:

| Field | Verification |
|---|---|
| `PHASE` | renders |
| `GATE` | renders, including `2/3` progress when provided |
| `RUN` | renders short suffix, e.g. `1761df0e` |
| `SESSION` | renders when provided |
| `PATH` | renders at wider compact widths; clipped out at 88 columns when session text is long |
| Missing fields | fail soft to `n/a` by display design |
| Overflow | not observed; max rendered width stayed within terminal width |

Compact fit finding:

- At 88 columns, the strip stayed within width but clipped the trailing `PATH` segment after a long `SESSION` label.
- At 100 columns, `PATH` label was visible but the value was clipped.
- At 120 columns, `PATH FAST_CLOSE_HEAVY` was visible.

Operator implication: the header strip is safe from overflow, but `PATH` visibility is not guaranteed on narrow compact terminals when session labels are long. This is a UI observability gap, not a runtime blocker.

## Path Truth Growth

Files inspected:

| File | Size | Last Write |
|---|---:|---|
| `runtime/quant_data/path_truth/2026-05-24.jsonl` | 68,943 B | 2026-05-25 06:10:41 |
| `runtime/quant_data/path_truth/2026-05-25.jsonl` | 73,532 B | 2026-05-26 06:40:35 |

Completed dates: **2**

Gate progress:

| Gate | Progress | Verdict |
|---|---:|---|
| `EARLY_RESEARCH_GATE` | 2 / 3 | not ready |
| `IMPLEMENTATION_GATE` | 2 / 7 | not ready |

Aggregate path truth coverage:

| Metric | Count |
|---|---:|
| JSONL files | 2 |
| JSONL lines | 95 |
| parse errors | 0 |
| duplicate checkpoint keys | 0 |
| event-end trades | 51 |
| full coverage trades | 3 |
| fast-close partial trades | 48 |
| fast-close share | 94.1% |

Checkpoint distribution:

| Checkpoint | 2026-05-24 | 2026-05-25 | Total |
|---|---:|---:|---:|
| 15s | 13 | 12 | 25 |
| 30s | 5 | 5 | 10 |
| 45s | 4 | 2 | 6 |
| 60s | 3 | 0 | 3 |
| event_end | 21 | 30 | 51 |

Growth versus previous monitor:

| Metric | Previous | Current | Growth |
|---|---:|---:|---:|
| lines | 86 | 95 | +9 |
| event-end trades | 46 | 51 | +5 |
| full coverage | 3 | 3 | unchanged |
| fast-close partial | 43 | 48 | +5 |

Field gap status:

| Field | Missing |
|---|---:|
| `quote_age_ms` | 95 / 95 |
| `candidate_id` | 95 / 95 |
| `decision_id` | 95 / 95 |

Read: field gaps remain known and unchanged. Field wiring is still blocked by the gates.

## Research Candidates

Candidate read based on current 2026-05-24 and 2026-05-25 trade-journal evidence:

| Candidate | Current Evidence | Read |
|---|---|---|
| BTC hostile | 2 TP / 25 SL across 2026-05-24/25; 1 TP / 18 SL on 2026-05-25 | stable hostile candidate |
| NO session dependent | 9 TP / 22 SL across 2026-05-24/25; 6 TP / 16 SL on 2026-05-25 | weak overall, not uniformly dead; session dependence remains plausible |
| 02h hostile | 0 TP / 5 SL in current 2026-05-24/25 slice | stable hostile candidate; aligns with prior broader 0 TP / 12 SL context |
| 09h10h edge | 0 TP / 1 SL in current 2026-05-24/25 slice | not invalidated, but no fresh support; still insufficient sample |
| Fast close | 48 / 51 path-truth event-end trades partial before full scheduled path | real behavior, stronger in current monitor |

Synthesis:

- BTC weakness remains the strongest current candidate.
- NO weakness remains session-dependent rather than cleanly global.
- 02h hostility remains consistent.
- 09h10h still needs more evidence before treating it as a reliable escape window.
- Fast close is not a display artifact; it dominates path-truth coverage.

## Gate Progress

Current verdict:

```text
INSUFFICIENT_DATES
```

Reason:

- `EARLY_RESEARCH_GATE` is 2 / 3 completed dates.
- `IMPLEMENTATION_GATE` is 2 / 7 completed dates.
- JSONL writer health is clean: 0 parse errors, 0 duplicate keys, 0 observed write errors.
- Path depth remains fast-close-heavy.
- `quote_age_ms`, `candidate_id`, and `decision_id` remain 100% missing and should not be wired before the gate.

## Next Action

Recommended next action: **continue paper evidence farming until the third completed path-truth date exists**.

Three possible follow-up paths:

1. Safe: continue read-only daily path-truth monitor after the next completed date.
2. Research-heavy: refresh BTC / NO / 02h / 09h10h candidate splits once the third date lands.
3. Implementation-gated: only after gate approval, scope field wiring for `quote_age_ms`, `candidate_id`, and `decision_id`.

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Tests: not run; this was a read-only/docs audit with no runtime code changes.

Persistent tests unchanged; no tests were deleted.
