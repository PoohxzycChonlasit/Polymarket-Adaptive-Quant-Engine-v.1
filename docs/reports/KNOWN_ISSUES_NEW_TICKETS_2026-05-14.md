# New Known Issues - 2026-05-14

> Purpose: New tickets identified during the 2026-05-14 documentation reconciliation and strategic review pass.
> These tickets follow the format used by `KNOWN_ISSUES.md`.
> Operator must review and merge into the main `KNOWN_ISSUES.md` or `docs/KNOWN_ISSUES.md` after review.
> Source review: full read of `AGENTS.md`, `CURRENT_PROJECT_STATUS.md`, `KNOWN_ISSUES.md`, `FILE_INDEX.md`, `DOCUMENTATION_MAP.md`, `CLAUDE.md`, `CODEX_START_HERE.md`, `PROJECT_RULES.md`, `MASTER_AGENT_ROUTER.md`, `QUANT_FUTURE_DECISION_ENGINE.md`, `PROJECT_STRUCTURE.md`.

---

## Documentation Drift Tickets

### DOC-005 - Cross-doc file list inconsistency

Status: open.

Evidence:

- `CLAUDE.md` references `polymarket/expected_value.py` and `polymarket/position_manager.py` that do not appear in `FILE_INDEX.md` or `AGENTS.md` Active Files.
- `AGENTS.md` Active Files is missing `polymarket/regime_diagnostics.py`, `polymarket/probability_model.py`, `polymarket/position_sizing.py`, `utils/scan_log_loader.py`, `utils/config_validator.py`, `tools/no_entry_analyzer.py`, and `tools/session_runtime_evaluator.py` even though they appear in `FILE_INDEX.md` and are described elsewhere as implemented.
- Telegram helper function list disagrees between `KNOWN_ISSUES.md` OBS-003 and `CURRENT_PROJECT_STATUS.md` line 79.

Impact:

- AI assistants receive inconsistent context depending on which file they load first.
- Codex auto-loads `AGENTS.md`, so its incompleteness has highest impact.
- Telegram observability and EV/probability/regime work has fragmented documentation ownership.

Next:

- Apply diffs proposed in `DOC_TRUTH_RECONCILIATION_2026-05-14.md` INC-001, INC-002, INC-003, INC-005.
- Verify filesystem ground truth for `expected_value.py` and `position_manager.py` before deciding fix direction.

### DOC-006 - `research/daily/` workflow referenced but undefined

Status: open.

Evidence:

- `CURRENT_PROJECT_STATUS.md` line 536 instructs AI assistants to read `research/daily/YYYY-MM-DD.md` before code changes.
- No other documentation references this folder.
- `FILE_INDEX.md` "Generated Or Evidence Folders" does not list `research/`.
- `CLAUDE.md` line 62 references a different research workflow at `runtime/research_state/latest_research_state.md`.

Impact:

- The documented Codex Working Instructions reference a workflow that is undefined elsewhere.
- AI assistants will either fail silently when reading the folder, or miss valuable research evidence if the folder exists but is undocumented.

Next:

- Verify filesystem existence of `research/daily/`.
- Either document the folder properly across all canonical docs, or replace the reference with `runtime/research_state/latest_research_state.md`.
- See `DOC_TRUTH_RECONCILIATION_2026-05-14.md` INC-004 for proposed resolution.

### DOC-007 - Documentation Sync Rule lacks concrete procedure

Status: open.

Evidence:

- `AGENTS.md` line 25 references a "documentation synchronization pass" with no concrete definition.
- The 2026-05-08 sync pass referenced in `CURRENT_PROJECT_STATUS.md` line 118 did not produce a reusable procedure document.
- This 2026-05-14 reconciliation pass had to invent a procedure ad hoc.

Impact:

- Each AI assistant invents a different sync procedure. Results are not reproducible.
- Doc drift compounds because there is no canonical detection step.

Next:

- Create `docs/DOC_SYNC_PROCEDURE.md` per `DOC_TRUTH_RECONCILIATION_2026-05-14.md` INC-006.
- Reference it from `AGENTS.md` Documentation Sync Rule section.

---

## Schema And Contract Tickets

### SCHEMA-001 - Decision JSONL schema is not versioned

Status: open.

Evidence:

- `utils/quant_event_logger.py` writes JSONL events with a `schema_version` field per `KNOWN_ISSUES.md` OBS-002.
- No documentation defines what the schema actually is. Field set is implicit in the code.
- Replay tooling assumes schema stability but the contract is not declared.
- Phase 2 inventory replay research requires schema stability across many sessions.

Impact:

- Any change to JSONL payload risks breaking offline replay analyzers silently.
- AI assistants asked to add fields cannot tell what version they are starting from.
- Cross-day replay can silently misinterpret fields if schema versions diverged.

Next:

- Create `docs/SCHEMAS/decision_snapshot_v1.md` documenting the current implicit schema.
- Add a regression test that fails if `schema_version` is missing or unrecognized.
- Define a bump policy: minor for additive fields, major for breaking changes.
- Future work to design `decision_snapshot_v2.md` should reuse this contract pattern.

### SCHEMA-002 - JSONL event types lack canonical enum documentation

Status: open.

Evidence:

- Per `KNOWN_ISSUES.md` OBS-002, events are written to `market_snapshots`, `decision_log`, `execution_log`, `trade_journal`, `risk_log`, `system_health`.
- The set of allowed `event_type` values within each file is not documented.
- The set of allowed `skip_reason` values is not documented.

Impact:

- Replay/no-entry analyzers depend on string matching against undocumented enums.
- Adding a new skip reason silently can break diagnostic classification.

Next:

- Document the enums in the new `docs/SCHEMAS/` folder.
- Add a regression test that fails if an emitted enum value is not in the documented set.

---

## Observability Tickets

### OBS-005 - Allowance status is not surfaced in runtime observability

Status: open.

Evidence:

- `KNOWN_ISSUES.md` LIVE-001 documents missing allowance as a live blocker.
- `CURRENT_PROJECT_STATUS.md` line 226 confirms verify mode reports `missing_allowance`.
- The allowance status is only visible in verify-mode logs. It is not in the JSONL system_health stream, terminal UI footer, daily Telegram summary, or startup banner of paper/live modes.

Impact:

- The single most important gating signal for live readiness is invisible during paper runtime.
- Operators cannot tell at a glance whether allowance has been resolved.
- When the day comes to enable live, allowance status will need to be verified by running a separate verify command instead of being already visible.

Next:

- Add `allowance_status: ready|missing|unknown` field to system_health JSONL events.
- Add `ALLOW: ready|missing|unknown` segment to terminal UI footer (alongside existing TIER/MICRO/LIQ/CUTOFF/RECOVERY).
- Add allowance status to startup banner and daily Telegram summary.
- Do not change verify mode behavior. Do not unblock live mode just because the field is visible.

### OBS-006 - Lifecycle Latency Observatory v1 has no offline aggregator

Status: open.

Evidence:

- Recent work added lifecycle latency fields per recent project context: `discovery_to_token_ready_ms`, `token_ready_to_book_ms`, `book_to_nonzero_ms`, `normalized_to_executable_ms`, and `decision_complete_ts`.
- Raw fields are written into decision JSONL.
- No offline tool aggregates lifecycle latency across markets, assets, phases, and dominant stage.

Impact:

- Raw fields exist but cannot be analyzed without manual JSONL inspection.
- The observatory cannot answer the question "which stage is the dominant latency bottleneck this week."
- Phase 1 evidence is collected but not summarized.

Next:

- Add `tools/lifecycle_latency_report.py`.
- Output a daily summary grouped by market_id, asset, phase, and dominant_latency_stage with P50/P90/P99 percentiles.
- Correlate dominant_stage with entry_taken vs no_entry outcome.
- Keep tool offline-only and read-only per `PROJECT_RULES.md`.

### OBS-007 - Logging degradation health event missing

Status: open.

Evidence:

- `KNOWN_ISSUES.md` WINLOG-001 confirms file logging can be silently disabled on Windows file locks.
- The session continues running but evidence integrity is degraded.
- There is no JSONL system_health event or terminal UI signal that announces this degradation.

Impact:

- A session can run with degraded evidence quality and the operator will not notice until manual log inspection.
- Replay analysis on a degraded session could produce misleading conclusions.

Next:

- Emit `LOGGING_DEGRADED` system_health event with affected writer name when SafeRotatingFileHandler or RealtimeLogger disable themselves.
- Add `LOGGING: ok|degraded` to terminal UI footer.
- Cooldown-protected Telegram alert if degraded state lasts more than N minutes.

---

## Budget And Sampling Tickets

### BUDGET-001 - Log budget target is not enforced

Status: open.

Evidence:

- `PROJECT_RULES.md` declares a target of <150MB/day compressed logs.
- No code currently tracks daily byte count for JSONL/CSV writers.
- No alert fires if the budget is exceeded.
- The Vultr VPS target has ~5GB disk per `PROJECT_RULES.md`.

Impact:

- Adding Phase 1 regime/probability fields, Lifecycle Latency Observatory, and future Phase 2 replay capture risks exceeding the budget silently.
- Disk exhaustion on the VPS would degrade runtime in an uncontrolled way.

Next:

- Implement `utils/log_budget_manager.py` that tracks daily byte count per writer.
- Add a daily compression job (gzip) for files older than 2 days, retention 30 days.
- Emit `LOG_BUDGET_PRESSURE` system_health event at 70% threshold and `LOG_BUDGET_CRITICAL` at 90%.
- Define priority tiers for events (CRITICAL always written, INFO sampled, DEBUG dropped under budget pressure).
- Keep this offline-aware; do not let budget pressure block trading decisions, only logging.

### SAMPLING-001 - JSONL events have no sampling policy

Status: open.

Evidence:

- Per `KNOWN_ISSUES.md` OBS-002, JSONL events are emitted for market snapshots, decisions, execution, trade open/close, risk, reconciliation, and low-frequency system health.
- The sampling cadence is documented in `PROJECT_RULES.md` only as a target (decision loop 1s, snapshot sampling 5s, market discovery 15s, full orderbook event-only).
- The actual enforcement is implicit in the code, not declared as a contract.

Impact:

- Adding new fields can silently raise per-event size.
- Multiplying event count by per-event size can exceed the 150MB/day budget without warning.
- AI assistants cannot reason about budget impact when adding observability without a declared policy.

Next:

- Document sampling policy in `docs/SCHEMAS/sampling_policy.md`.
- Reference it from `utils/quant_event_logger.py` docstring.
- Add a `sampled: bool` and `sampling_reason: str` field to events so replay can distinguish full from sampled snapshots.

---

## Tooling Tickets

### TD-004 - No automated documentation drift detector

Status: open.

Evidence:

- This 2026-05-14 pass found 6 inconsistencies that compounded silently over weeks.
- The detection method was a manual review with grep.
- The project has ~20 root `.md` files and 23 role docs in `docs/quant_agent_setup_md/roles/`.
- Drift detection at this scale needs tooling.

Impact:

- Inconsistency rate will rise over time without automated detection.
- Each AI assistant session is at risk of compounding drift instead of resolving it.

Next:

- Create `tools/doc_truth_check.py` (offline, read-only).
- Parse all `.md` files in repo root and `docs/`.
- Extract file path references and compare to filesystem.
- Compare cross-doc statements for known-fragile items (Telegram helpers, Active Files lists, Phase wording).
- Output `runtime/reports/doc_truth_YYYY-MM-DD.json`.
- Add as an optional pre-flight step in `docs/DOC_SYNC_PROCEDURE.md`.
- Keep the tool out of the runtime loop. Do not block trading on doc drift.

### TD-005 - 23 role docs lack consolidated index with status

Status: open.

Evidence:

- `MASTER_AGENT_ROUTER.md` lists roles 01 through 23 with task type, primary, and supporting agents.
- The router does not declare implemented vs planned status for each role.
- `AGENTS.md` has a similar table but uses the labels "Implemented / Partially implemented / Planned" only as overall status, not per-role.

Impact:

- AI assistants may select a "planned" role doc and treat it as authoritative for code work.
- Newer roles 18-23 (regime, fair value, inventory, microstructure, analytics, lifecycle inventory) are guidance only but this is not declared per-role.

Next:

- Add per-role status column to `MASTER_AGENT_ROUTER.md` Router Table.
- Mark roles 18-23 as "Guidance only / Planned runtime".
- Mark roles 01-17 status based on the existing "Implemented / Partial / Planned" classification.

---

## Lifecycle Tickets

### LIFECYCLE-001 - Lifecycle vocabulary used in docs but not enforced

Status: open.

Evidence:

- `DOCUMENTATION_MAP.md`, `AGENTS.md`, `CODEX_START_HERE.md`, `FILE_INDEX.md`, and `MASTER_AGENT_ROUTER.md` all use the lifecycle states OPENING_SCAN, ACTIVE_INVENTORY_TRADING, PROFIT_MANAGEMENT, FINAL_DERISK, CLOSED_OR_UNSAFE.
- No code currently emits a lifecycle_state field in JSONL.
- No terminal UI element shows current lifecycle state.

Impact:

- Vocabulary is documented but invisible in runtime evidence.
- Phase 2/3 design cannot reference real lifecycle state data because none is captured.

Next:

- Add `lifecycle_state` field to decision JSONL events.
- Default to OPENING_SCAN if no inventory exists.
- Future Phase 3 inventory work will populate the other states.
- Do not let lifecycle_state affect runtime decisions until Phase 3 explicitly enables it.
- This is observability-only until Phase 3.

### LIFECYCLE-002 - Risk Budget vocabulary used in docs but not surfaced

Status: open.

Evidence:

- `DOCUMENTATION_MAP.md` and `AGENTS.md` document the Dynamic Quant Risk Budget vocabulary: bankroll, open exposure, realized/unrealized PnL, market/session risk used, drawdown, tier id, risk mode, target exposure vs current exposure.
- Current JSONL captures some but not all of these fields.
- Terminal UI shows tier and risk mode but not target vs current exposure.

Impact:

- Phase 3 bounded inventory engine cannot reason about "target exposure vs current exposure" because the runtime never captures it.
- Replay cannot explain why a decision was sized smaller or larger than target.

Next:

- Audit `utils/quant_event_logger.py` and decision payload for risk budget field coverage.
- Add a `risk_budget` block to decision events with all 8 vocabulary fields.
- Add target vs current exposure to terminal UI Risk panel.
- Keep observability-only. Phase 3 will read these fields; Phase 1/2 only logs them.

---

## Priority Summary

P0 (apply this week, doc-only, no code):

- DOC-005, DOC-006, DOC-007 -> apply diffs from `DOC_TRUTH_RECONCILIATION_2026-05-14.md`.

P1 (next 2 weeks, code work, low risk):

- OBS-005 (allowance status) -> high operator value, low risk.
- OBS-007 (logging degraded event) -> evidence integrity fix.
- SCHEMA-001, SCHEMA-002 -> needed before any JSONL field addition.

P2 (next 4 weeks, code work, medium scope):

- OBS-006 (lifecycle latency aggregator) -> unlocks current observatory value.
- BUDGET-001, SAMPLING-001 -> needed before Phase 1 regime/probability JSONL expansion.
- LIFECYCLE-001, LIFECYCLE-002 -> needed before Phase 3 design.

P3 (next 6 weeks, tooling and documentation):

- TD-004 (doc truth checker) -> prevents future drift.
- TD-005 (role doc status index) -> AI assistant safety.

---

## Boundaries

Per `PROJECT_RULES.md`, `AGENTS.md`, and `CODEX_START_HERE.md`:

- These tickets do not authorize live trading.
- These tickets do not authorize bypassing OrderIntent, reconciliation, stale orderbook protection, forced exit, or panic exit.
- These tickets do not authorize broad refactoring of `polymarket/trader.py`.
- These tickets do not authorize deletion of any runtime logs, tests, research records, or config files.
- These tickets do not authorize loosening any risk gate.
- Each ticket must be implemented with its own scoped tests per `07_TEST_CI_AGENT.md`.

All P1 and P2 code work must keep paper as default and never touch wallet, sign, or live order paths.
