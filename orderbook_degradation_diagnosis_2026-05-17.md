# Orderbook Degradation Diagnosis - 2026-05-17

## Scope

Read-only diagnosis for the 2026-05-17 S3 evidence block.

Runtime behavior changed: No  
Live behavior changed: No

## Role Routing

- Primary role: `14_NO_ENTRY_DIAGNOSTICS_AGENT`
- Supporting roles: `05_MARKET_DATA_AGENT`, `10_BACKTEST_REPLAY_AGENT`, `11_OBSERVABILITY_INCIDENT_AGENT`
- Skills used: `.codex/skills/no-entry-root-cause.md`, `.codex/skills/replay-diagnostics.md`, `.codex/skills/session-regime-analysis.md`
- Scope boundary: diagnosis/report only; no runtime patch, no S3 rerun, no gate loosening.

## Root Cause Classification

Primary classification: decision-pipeline orderbook handoff/completeness regression.

The CLOB/orderbook source was not simply unavailable. `market_snapshots` repeatedly captured parsed YES/NO bid/ask data, token IDs, condition IDs, healthy liquidity, and `orderbook_state_classification=ready`. The decision path then reclassified the same market lifecycle as `orderbook_state_classification=unavailable`, omitted serialized YES/NO bid/ask fields, set model/probability/fair-value/EV visibility to null, and blocked at the pre-model orderbook gate.

Most likely category: code logic / state handoff bug, with evidence hygiene contamination from stale or overlapping writers.

Not primary root cause:

- Market data source outage: unlikely; snapshots had executable books.
- CLOB parser failure: unlikely; snapshots parsed YES/NO bid/ask fields.
- Gamma discovery failure: unlikely; condition IDs and token IDs were present in decision and snapshot payloads.
- Token/condition mismatch: unlikely as primary; sampled decision/snapshot examples shared matching condition/token IDs.
- Reconciliation dead-loop: not supported; `reconciliation_blocks_trading=true` was not observed in parsed raw files.
- MICRO_SURVIVAL/risk mode: not primary; model/orderbook gates blocked before risk sizing.
- Execution failure: not primary; no true submit/fill/cancel attempt happened.
- File/logging issue: secondary evidence-quality issue, not the trading blocker itself.

## Top Evidence

1. `runtime/quant_data/market_snapshots/2026-05-17.jsonl`
   - 1,769 / 1,769 snapshots had `orderbook_state_classification=ready`.
   - 1,769 / 1,769 snapshots had `orderbook_current_fetch_status=fresh_fetch_executable`.
   - 1,769 / 1,769 snapshots had YES/NO book fields.

2. `runtime/quant_data/decision_log/2026-05-17.jsonl`
   - 661 / 661 decisions had `orderbook_state_classification=unavailable`.
   - 0 / 661 decisions had confidence > 0.
   - 0 / 661 decisions had calculated order size > 0.
   - Admission block stages: `ORDERBOOK=298`, `CUTOFF=210`, `MODEL_GATE=144`, `NORMALIZATION=9`.
   - Normalized skip reasons: `time_unsafe=288`, `stale_data=234`, `orderbook_unavailable=139`.

3. Decision/snapshot contradiction in the same real May 17 run:
   - `decision_log` line 133, run `20260517T142049Z_12712_d4120fa6`: `normalized_skip_reason=orderbook_unavailable`, `market_readiness_state=unavailable`, `orderbook_current_fetch_status=fresh_fetch_non_executable`, but `executable_book_state=TRADABLE`.
   - `market_snapshots` line 311, same run and same condition/token: `market_readiness_state=ready`, `orderbook_state_classification=ready`, `fresh_fetch_executable`, `yes_bid=0.36`, `yes_ask=0.39`, `no_bid=0.61`, `no_ask=0.64`.

4. `runtime/quant_data/execution_log/2026-05-17.jsonl`
   - 1,665 / 1,665 execution rows were `payload.event=market_analysis_exception`.
   - No `order_submit_attempt`, `paper_fill`, or true execution-stage attempt was observed for May 17.
   - Execution exceptions are downstream diagnostics from pre-model/no-entry state, not failed order placement.

5. Evidence hygiene issue:
   - May 17 JSONL contains real May 17 run IDs plus May 15 run IDs writing May 17 timestamps.
   - `runtime/realtime_logs/2026-05-17/` includes `scan_log_20260515_115312_36468.csv` and `scan_log_20260515_115556_30196.csv`.
   - `runtime/reports` could not be listed: Windows returned `The file or directory is corrupted and unreadable`.
   - `runtime/quant_data/market_snapshots/2026-05-15.jsonl` also returned a corrupted/unreadable error during comparison.

## Count And Classification Summary

Parsed current raw May 17 files:

- `decision_log`: 661 rows, 0 malformed.
- `market_snapshots`: 1,769 rows, 0 malformed.
- `execution_log`: 1,665 rows, 0 malformed.
- `system_health`: 1,940 rows, 0 malformed.
- `research_log`: 1,720 rows, 0 malformed.
- `risk_log`: 872 rows, 0 malformed.
- `trade_journal`: missing for May 17.

Key May 17 counts:

- `market_analysis_exception`: 1,665 parsed execution payload events.
- `market_discovery_refresh`: 1,066 parsed system health payload events.
- `cycle_start`: 333 parsed system health reason values.
- `reconciliation_blocks_trading=true`: 0 parsed rows.
- `reconciliation_blocks_trading=false`: 350 parsed rows.
- `empty_book_recovery_attempted=true`: 0 parsed rows.
- `empty_book_recovery_success=true`: 0 parsed rows.
- `zero_size_probe_v1`: 0.
- `entry_budget_probe_v1`: 0.
- `cycle_selection_probe_v1`: 0.

Note: these current raw counts differ from the supplied audit in places, likely because the runtime kept writing after that audit and because day-level evidence is contaminated by stale May 15 run IDs. The direction of the diagnosis is unchanged: decisions never reached usable model/EV/risk output.

## Lifecycle And Dropout Pattern

Decision lifecycle phases:

- `ACTIVE_INVENTORY_TRADING=278`
- `FINAL_DERISK=240`
- `PROFIT_MANAGEMENT=115`
- `OPENING_SCAN=28`

Market snapshot lifecycle phases:

- `ACTIVE_INVENTORY_TRADING=1,386`
- `OPENING_SCAN=233`
- `PROFIT_MANAGEMENT=150`

Decision dropout:

- `ORDERBOOK_GATE=373`
- `TIME_CUTOFF_GATE=288`
- `pre_model_gate_reason=time_unsafe=288`
- `pre_model_gate_reason=model_output_not_visible=234`
- `pre_model_gate_reason=orderbook_unavailable=139`

Interpretation: the model/probability path was blocked before S3 evidence could form. Some decisions later degrade into cutoff/hard-close states, but the deeper failure is that executable snapshot books did not survive into decision/model readiness.

## Comparison To S1/S2

2026-05-16 raw quant files were not available in the inspected `runtime/quant_data` folders.

2026-05-15 comparison was partially blocked by filesystem corruption:

- `runtime/quant_data/market_snapshots/2026-05-15.jsonl`: unreadable/corrupted.
- `runtime/reports`: unreadable/corrupted.
- Available May 15 scan logs for known paper runs showed `time_unsafe` as the dominant skip reason and did not show the May 17 decision/snapshot contradiction in the same way.

Given the user-provided context that S1 and S2 are valid, May 17 should be treated as a degraded/blocked evidence day rather than a valid S3 continuation.

## Root Cause Verdict

This is most likely a code logic or state propagation issue in the decision/orderbook readiness path, not a Polymarket data-source outage.

The strongest signature is:

```text
snapshot path: fresh_fetch_executable + ready + YES/NO bid/ask present
decision path: fresh_fetch_non_executable/not_attempted + unavailable + no serialized book fields
```

That points to a handoff/cache/readiness regression between market snapshot sampling and scheduled decision/model admission. Evidence contamination from overlapping/stale writers makes day-level totals noisy, but the same contradiction remains inside real May 17 runs.

## S3 Status

S3-final is blocked.

Do not run S3-final on 2026-05-17 evidence. It lacks probability, fair value, EV, nonzero confidence, nonzero order sizing, and clean decision-stage orderbook readiness.

## Safest Next Action

Recommended path: stop all paper runtimes, confirm no stale writer/process is still appending, then start one clean paper runtime/run only after preserving this diagnosis.

After restart, verify read-only:

- terminal shows BTC/ETH `BID`, `ASK`, and `SPREAD`;
- one new run ID only;
- `market_snapshots` and `decision_log` agree on condition/token IDs;
- decision rows serialize usable orderbook fields or at least do not classify ready snapshot books as unavailable;
- confidence/probability/fair-value/EV can become visible before cutoff;
- `reconciliation_blocks_trading` remains false.

If the clean single-run evidence still shows snapshot-ready but decision-unavailable, a code patch is likely needed in the orderbook readiness/handoff path before any S3 continuation.

## Restart Recommendation

Restart is recommended as a hygiene step, but restart alone is not sufficient proof.

The May 17 evidence includes stale May 15 run IDs and overlapping-looking scan logs, so a clean process boundary is necessary. However, because the contradiction appears inside real May 17 run IDs too, a restart should be followed by a focused verification pass before S3 resumes.

## Future Options

1. OPTION 1 - SAFE EV PRESERVATION: pause S3-final, cleanly restart one paper runtime, and collect a short fresh run solely to verify orderbook handoff consistency.
2. OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY: run a paper-only diagnostic session with extra offline comparison of market snapshot versus decision candidate identity, without loosening gates or changing execution.
3. OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH: inspect and patch the decision-stage orderbook readiness/cache handoff if a clean run reproduces snapshot-ready versus decision-unavailable divergence.

Recommended: Option 1 first, then Option 3 only if the clean single-run check reproduces the mismatch.

## Files Inspected

- `CODEX_START_HERE.md`
- `PROJECT_RULES.md`
- `AGENTS.md`
- `MASTER_AGENT_ROUTER.md`
- `CURRENT_PROJECT_STATUS.md`
- `runtime/research_state/latest_research_state.md`
- `.codex/README.md`
- `.codex/security/AI_AGENT_SECURITY_CHECKLIST.md`
- `.codex/skills/replay-diagnostics.md`
- `.codex/skills/no-entry-root-cause.md`
- `.codex/skills/session-regime-analysis.md`
- `docs/quant_agent_setup_md/roles/14_NO_ENTRY_DIAGNOSTICS_AGENT.md`
- `docs/quant_agent_setup_md/roles/05_MARKET_DATA_AGENT.md`
- `docs/quant_agent_setup_md/roles/10_BACKTEST_REPLAY_AGENT.md`
- `docs/quant_agent_setup_md/roles/11_OBSERVABILITY_INCIDENT_AGENT.md`
- `runtime/quant_data/system_health/2026-05-17.jsonl`
- `runtime/quant_data/decision_log/2026-05-17.jsonl`
- `runtime/quant_data/execution_log/2026-05-17.jsonl`
- `runtime/quant_data/market_snapshots/2026-05-17.jsonl`
- `runtime/quant_data/research_log/2026-05-17.jsonl`
- `runtime/quant_data/risk_log/2026-05-17.jsonl`
- `runtime/realtime_logs/2026-05-17/*.csv`
- selected 2026-05-15 comparison logs where readable

## Not Touched

- `polymarket/trader.py`
- `polymarket/order_manager.py`
- risk, strategy, execution, wallet, or live config files
- JSONL evidence
- tests
- S3 validation

## Tests / Commands

No runtime tests were run. The work used read-only PowerShell parsing and targeted file inspection only.
