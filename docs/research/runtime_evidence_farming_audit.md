# Runtime + Evidence Farming Audit

Date: 2026-05-25 18:20 Asia/Bangkok

Scope: read-only observability and evidence farming audit for the current `PATH TRUTH / EVIDENCE FARMING` phase.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Role Routing

Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`

Supporting roles:

- `10_BACKTEST_REPLAY_AGENT.md`
- `16_PAPER_EVALUATION_AGENT.md`
- `07_TEST_CI_AGENT.md`

Why selected: this task is primarily runtime/log/JSONL health plus evidence sufficiency, with replay-style segmentation and docs-only verification.

## Files Inspected

- `runtime/research_state/latest_research_state.md`
- `MASTER_AGENT_ROUTER.md`
- `docs/quant_agent_setup_md/roles/11_OBSERVABILITY_INCIDENT_AGENT.md`
- `docs/quant_agent_setup_md/roles/10_BACKTEST_REPLAY_AGENT.md`
- `docs/quant_agent_setup_md/roles/16_PAPER_EVALUATION_AGENT.md`
- `docs/quant_agent_setup_md/roles/07_TEST_CI_AGENT.md`
- `logs/polytrade_bot_20260525_135420_53560.log`
- `runtime/quant_data/path_truth/*.jsonl`
- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/decision_log/2026-05-25.jsonl`
- `runtime/quant_data/execution_log/2026-05-25.jsonl`
- `runtime/quant_data/system_health/2026-05-25.jsonl`
- `docs/research/path_truth_multiday_coverage_monitor.md`

Files intentionally ignored:

- `polymarket/trader.py`
- `polymarket/order_manager.py`
- `utils/risk_manager.py`
- wallet/live config
- replay execution paths

## Check 1 - Runtime Health

Runtime alive: Yes.

Newest visible runtime process:

| PID | Process | Start Time | Command |
|---:|---|---|---|
| 53560 | `python.exe` | 2026-05-25 13:54:17 local | `main.py --mode paper --interval 10 --ui compact --fps medium` |
| 57084 | `py.exe` launcher | 2026-05-25 13:54:17 local | launcher parent for the same paper command |

Active/newest run evidence:

- active log: `logs/polytrade_bot_20260525_135420_53560.log`
- newest path-truth run id: `20260525T065423Z_53560_1b672958`
- active log tail shows ongoing paper cycles through at least cycle `1340`
- latest active summary showed:
  - cycles: `1340`
  - markets: `2338`
  - opportunities: `267`
  - orders: `10`
  - fills: `10`
  - exits: `5`
  - win rate: `40.0%`
  - pnl: approximately `-0.0019`
  - risk mode: `MICRO_RECOVERY`

Health checks on active log:

| Signal | Count / Result |
|---|---:|
| `Traceback` | 0 |
| true `| ERROR |` severity lines | 0 |
| `FATAL` / fatal | 0 |
| write failure patterns | 0 |
| permission/write exceptions | 0 |
| Telegram failure patterns | 0 |
| shutdown marker | 0 |

Observed warnings:

- transient `[ORDERBOOK_RECOVERY]` and `[ORDERBOOK_FLOW]` warnings appear in the active log.
- These did not escalate to tracebacks or fatal runtime failure in the inspected tail.

Important runtime hygiene note:

Multiple older paper processes are still visible:

- `20260521T044143Z_13704_948b4757`
- `20260522T052610Z_31032_cfe7068f`
- `20260522T075658Z_26740_b69f35b9`
- `20260522T094222Z_46088_040fac20`
- other older process IDs also remain visible

This means day-level JSONL can be multi-process contaminated. Evidence should be filtered by `run_id` for research claims. No processes were stopped.

## Check 2 - Path Truth Growth

Path truth files:

| Date | Status | Size | Lines | Runs | Trades | Parse Errors | Duplicate Keys |
|---|---|---:|---:|---:|---:|---:|---:|
| 2026-05-24 | completed | 68,943 B | 46 | 4 | 21 | 0 | 0 |
| 2026-05-25 | in-progress | 28,520 B | 19 | 3 | 14 | 0 | 0 |

Checkpoint distribution:

| Date | 15s | 30s | 45s | 60s | event_end |
|---|---:|---:|---:|---:|---:|
| 2026-05-24 | 13 | 5 | 4 | 3 | 21 |
| 2026-05-25 | 4 | 1 | 0 | 0 | 14 |
| Total | 17 | 6 | 4 | 3 | 35 |

Coverage classification:

| Date | Full Coverage | Fast Close Partial | Detail |
|---|---:|---:|---|
| 2026-05-24 | 3 | 18 | first: 8, second: 8, third: 1, before 60s: 1 |
| 2026-05-25 | 0 | 14 | first: 10, second: 3, third: 1 |
| Total | 3 | 32 | all partials are fast-close explained |

Growth versus previous state:

Previous state:

- 46 lines
- 21 trades
- 3 full coverage trades
- 18 fast-close partial trades

Current total:

- 65 lines
- 35 trades
- 3 full coverage trades
- 32 fast-close partial trades

Growth:

- lines: `+19` (`+41.3%`)
- trades: `+14` (`+66.7%`)
- full coverage: unchanged
- fast-close partial: `+14` (`+77.8%`)

Interpretation:

Evidence farming is growing, but the new growth is on the in-progress date and remains fast-close heavy. This supports "fast close is real behavior" rather than a path-truth writer failure.

## Check 3 - Coverage Gate

Current gate status:

| Gate | Requirement | Current | Verdict |
|---|---:|---:|---|
| EARLY_RESEARCH_GATE | 3 completed dates | 1 / 3 | INSUFFICIENT_DATES |
| IMPLEMENTATION_GATE | 7 completed dates | 1 / 7 | BLOCKED |

Coverage verdict:

```text
INSUFFICIENT_DATES
```

Regression verdict:

```text
COVERAGE_STABLE
```

Reason:

- `2026-05-24` is the only completed path-truth date.
- `2026-05-25` is still in progress and should not count as completed.
- completed-date eligible full coverage remains `3 / 3 = 100%`.
- parse errors: 0
- duplicate checkpoint keys: 0
- write errors: 0

The coverage monitor was updated:

- `docs/research/path_truth_multiday_coverage_monitor.md`

## Check 4 - Field Gap Status

Tracked fields:

| Field | 2026-05-24 Present | 2026-05-24 Missing | 2026-05-25 Present | 2026-05-25 Missing | Trend |
|---|---:|---:|---:|---:|---|
| `quote_age_ms` | 0 / 46 | 100% | 0 / 19 | 100% | unchanged |
| `candidate_id` | 0 / 46 | 100% | 0 / 19 | 100% | unchanged |
| `decision_id` | 0 / 46 | 100% | 0 / 19 | 100% | unchanged |

Verdict:

```text
KNOWN_FIELD_GAP_UNCHANGED
```

No regression was detected. These fields remain blocked until the path-truth gate permits field wiring under a future implementation task.

## Check 5 - Failure Candidates

Latest path-truth-backed outcome sample:

| Candidate | Current Path-Truth Evidence | Read |
|---|---|---|
| BTC | `0 TP / 10 SL` | BTC_HOSTILE_CANDIDATE strengthened |
| NO | `2 TP / 13 SL` | NO_SESSION_DEPENDENT remains; path-truth NO still weak |
| 02h | `0 TP / 1 SL` | still hostile but new path-truth sample is tiny |
| 09h10h | `0 trades` | no new path-truth evidence |
| BTC + NO | `0 TP / 4 SL` | weak interaction persists |
| ETH + NO + OPENING | `1 TP / 8 SL` | still weak; one new TP prevents a clean zero, but not the weakness |

Failure-candidate interpretation:

- `BTC_HOSTILE_CANDIDATE`: stable to stronger. Path-truth-backed BTC is now `0 / 10`.
- `NO_SESSION_DEPENDENT`: stable. Broader NO has partial session recovery, but path-truth NO remains weak.
- `02h_NO_HOSTILE`: stable but thin in current path truth.
- `09h10h PARTIAL_SURVIVAL`: unchanged; no new path-truth rows in 09h/10h.
- Fast close remains real behavior: current path-truth total has `32 / 35` fast-close partial trades.

## Next Action

Recommended action:

```text
KEEP_EVIDENCE_FARMING
```

Reason:

- Runtime is alive.
- Evidence is growing.
- Completed-date gate remains `1 / 3`.
- No parse/write/duplicate regression was found.
- Multiple paper processes are visible, so future research should filter by `run_id` and avoid day-level merges unless explicitly decontaminated.

Do not:

- wire fields,
- change stoploss,
- change strategy,
- change risk,
- enable live,
- stop old processes without explicit operator instruction.

## Final Status

Files created:

- `docs/research/runtime_evidence_farming_audit.md`

Files modified:

- `docs/research/path_truth_multiday_coverage_monitor.md`

Tests run: none. This was a read-only observability and documentation audit.

Persistent tests unchanged.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No
