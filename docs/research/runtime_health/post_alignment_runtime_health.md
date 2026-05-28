# Post-Alignment Runtime Health Audit

Updated: 2026-05-23

Scope: read-only audit of post-alignment runtime evidence for 2026-05-22 and 2026-05-23.

Inspected:

- `runtime/quant_data/trade_journal/2026-05-22.jsonl`
- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-22.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`
- `runtime/quant_data/decision_log/2026-05-22.jsonl`
- `runtime/quant_data/decision_log/2026-05-23.jsonl`
- `runtime/quant_data/system_health/2026-05-22.jsonl`
- `runtime/quant_data/system_health/2026-05-23.jsonl`
- latest local runtime logs under `logs/`

No code changed. No replay run. No runtime, strategy, risk, execution, live, or S3 behavior changed.

## Executive Verdict

Status: CAUTION

Replay continuity is usable for post-alignment research, but runtime health is not clean enough to call the evidence fully complete.

Green:

- Trade open/close pairing is complete.
- Execution events link to trade keys with no missing execution key.
- 2026-05-23 quote-stale coverage is complete for outcome-truth closes.
- Latest clean shutdown evidence remains intact for completed Ctrl+C runs.

Yellow:

- Some 2026-05-22 and system-health JSONL lines are corrupted fragments.
- 38 trade-close events still lack `trade_result`.
- `signal_generated_ts` and `decision_complete_ts` are missing from execution-linked truth keys.
- Telegram delivery/routing is not structured in `runtime/quant_data`, so route health cannot be proven from JSONL.

Red:

- The newest paper process was still running during inspection, so the latest log had no shutdown footer yet.
- 219 `market_analysis_exception` execution events exist on 2026-05-22, all sampled examples tied to unavailable/token-not-ready market state. 2026-05-23 had 0.

## Snapshot

| Area | Result |
| --- | --- |
| Trade journal JSONL lines | 164 across 2026-05-22/23 |
| Trade open events | 82 |
| Trade close events | 82 |
| Unique trade keys | 72 |
| Close without open | 0 |
| Open without close | 0 |
| Outcome-truth close events | 44 |
| Latest outcome-truth close | 2026-05-23T12:55:37.277989Z |
| Execution log lines | 711 |
| Execution invalid JSON | 0 |
| Decision log parsed events | 47,131 |
| Decision invalid JSON fragments | 10 |
| System-health parsed events | 57,340 |
| System-health invalid JSON fragments | 15 |

Note: the runtime was active during inspection (`py.exe` and child `python.exe` running `main.py --mode paper --interval 10 --ui compact ...`), so counts may advance after this audit.

## 1. Replay Continuity

| Check | Result | Evidence |
| --- | --- | --- |
| Open/close pairing | PASS | 72 unique trade keys, all with open and close. |
| Execution key linkage | PASS | 72 execution keys, 0 missing from trade keys, 0 trade keys missing execution. |
| Outcome-truth coverage | CAUTION | 44 close events have `trade_result`; 38 close events still lack `trade_result`. |
| Legacy/no-truth closes | CAUTION | Missing `trade_result` closes are mostly older/legacy close rows with reason fields such as `stop_loss` or `take_profit_target_reached`. |

Answer: replay gaps exist only for outcome truth on older close rows. Key continuity itself is healthy.

## 2. Lifecycle Observability Completeness

| Field / area | Result |
| --- | --- |
| `paper_trade_replay_key` linkage | PASS |
| `quote_lineage_id` / `quote_capture_ts` | PASS at execution-event level |
| `quote_age_at_submit_ms` / `quote_age_at_fill_ms` | PASS for outcome-truth trades on both dates |
| `quote_stale_ms` | PASS for 2026-05-23, absent for 2026-05-22 |
| `derived_metric_source` | PASS on linked truth keys |
| `signal_generated_ts` | GAP in execution-linked truth keys |
| `decision_complete_ts` | GAP in execution-linked truth keys |
| lifecycle phase | PASS in trade and execution linkage |

Answer: lifecycle identity is good; full Phase 1 timestamp completeness is still not proven in execution-linked truth records.

## 3. Telegram Routing Path

Findings:

- `decision_log` contains 0 `telegram` mentions.
- Recent logs show startup/config warnings: `TELEGRAM_ENABLED missing; Telegram will enable only when token/chat_id are configured`.
- No sampled recent log showed Telegram send failure, alert failure, traceback, or bot exception.
- Telegram is not represented as structured route/ack/failure events in `runtime/quant_data`.

Answer: no Telegram failure was found, but Telegram route health is not auditable from JSONL. Current evidence supports "no visible failure," not "delivery proven."

## 4. Event Completeness

Execution event counts:

| Event | Count |
| --- | ---: |
| `order_intent_approved` | 164 |
| `order_submit_attempt` | 164 |
| `paper_fill` | 164 |
| `market_analysis_exception` | 219 |

Interpretation:

- Order-intent, submit, and paper-fill counts are internally balanced.
- `market_analysis_exception` is concentrated on 2026-05-22.
- Sampled exception payloads show `orderbook_state_classification=unavailable` and `market_readiness_state=token_not_ready`; this looks like market-readiness observability noise or exception naming, not a trade execution orphan.

Answer: core execution event completeness is good, but exception naming/counts need monitoring.

## 5. quote_stale_ms Coverage

| Date | Outcome-truth closes | quote_age_at_submit_ms | quote_age_at_fill_ms | quote_stale_ms |
| --- | ---: | ---: | ---: | ---: |
| 2026-05-22 | 17 | 17 | 17 | 0 |
| 2026-05-23 | 27 | 27 | 27 | 27 |
| Total | 44 | 44 | 44 | 27 |

Answer: Phase 6 `quote_stale_ms` coverage is healthy on 2026-05-23 and absent on pre-Phase-6 2026-05-22 rows. This is expected for the implementation timeline, but mixed-date analyses must not treat 2026-05-22 as quote-stale-complete.

## 6. Session Evidence Quality

| Slice | Trades | TP | SL | Mean pnl_usdc | Dates |
| --- | ---: | ---: | ---: | ---: | ---: |
| 09h10h | 12 | 8 | 4 | 0.004471 | 2 |
| Other hours | 32 | 7 | 25 | -0.005134 | 2 |

Date matrix:

| Date | 09h10h TP/SL | 09h10h mean pnl | Other TP/SL | Other mean pnl |
| --- | --- | ---: | --- | ---: |
| 2026-05-22 | 2/2 | -0.002349 | 4/9 | -0.003870 |
| 2026-05-23 | 6/2 | 0.007882 | 3/16 | -0.005998 |

Answer: session evidence quality is useful but still candidate-grade. The 09h10h advantage persists directionally across two dates, but the strongest evidence remains 2026-05-23-heavy.

## 7. Shutdown Fix Integrity

Evidence:

- Recent completed Ctrl+C logs include clean shutdown footers, for example:
  - `polytrade_bot_20260523_175940_29096.log`: `[SHUTDOWN] Ctrl+C received; runtime stopped cleanly after 2 cycles.`
  - `polytrade_bot_20260523_180138_7368.log`: `[SHUTDOWN] Ctrl+C received; runtime stopped cleanly after 216 cycles.`
- Those logs show no traceback and no `httpx` INFO spam after shutdown.
- The current newest log `polytrade_bot_20260523_184024_28096.log` had no shutdown footer because the paper process was still running at inspection time.

Answer: completed shutdowns look clean. Current active process means final shutdown integrity for the newest run is pending, not failed.

## Direct Answers

Replay gaps?

Yes, but not key-linkage gaps. Open/close and execution linkage are intact. The remaining replay gap is missing `trade_result` on 38 legacy close events.

Missing fields?

Yes. `signal_generated_ts` and `decision_complete_ts` are missing from execution-linked truth-key coverage. `quote_stale_ms` is absent on 2026-05-22 but complete on 2026-05-23.

Stale timelines?

No 60s+ quote-stale issue was identified in the current Phase 6 coverage. However, mixed pre/post-Phase-6 rows can create stale-timeline ambiguity if joined naively.

Telegram failures?

No explicit send failure found. But Telegram routing is not structured in JSONL, so delivery health is unproven.

Orphan events?

No execution/trade key orphan found. There are 31 execution-linked trade keys without outcome truth, corresponding to trade pairs whose closes lack `trade_result`.

Session evidence health?

Healthy enough for research, not promotion. The 09h10h split is candidate-grade only.

## Recommended Follow-Up

1. Add a future observability monitor for JSONL invalid-line count by file/date.
2. Treat `market_analysis_exception` count as a health gate and split true exceptions from expected token-not-ready states.
3. Add structured Telegram route events only if alert delivery needs auditability.
4. Keep session-regime claims candidate-grade until at least three dates and more BTC/Active samples exist.

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Tests: not run, docs-only

Persistent tests unchanged
