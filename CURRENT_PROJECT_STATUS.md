# PolyTrade Bot / Polymarket 5M BTC-ETH Quant System - Current Project Status

> Updated: 2026-06-27
> Purpose: Single source of truth for future AI assistants and project work.
> Important: This project is not confirmed live-trading ready. Do not claim live readiness until orderbook, wallet sync, execution, fill/cancel, allowance, and reconciliation are all proven in terminal/runtime evidence.

---

## 1. Current Project Identity

This repository is the **PolyTrade Bot / Polymarket 5M BTC-ETH Quant System**.

It is a Python trading bot for Polymarket 5-minute BTC/ETH binary prediction markets. The system is intended to run paper-first, validate real market data and risk behavior, then move toward live execution only after the missing live-risk pieces are verified.

Do not treat this repo as a new project. Do not recommend rebuilding from scratch. The project already has a working terminal UI, market scanner, price/oracle feed path, cycle loop, paper mode, and multiple strategy/risk modules. Current work should focus on validating and completing the existing runtime path.

Current strategic direction:

```text
single-entry signal trading
  -> regime-aware probability diagnostics
  -> paper-only inventory replay research
  -> bounded multi-price inventory design
  -> continuous probabilistic inventory trading only after evidence supports it
```

This roadmap does not change current execution behavior. Phase 1 is observability-only: regime classification, probability scoring, indicator evidence, terminal visibility, and JSONL visibility. Phase 2 is offline/paper-only inventory replay. Phase 3 is bounded inventory design with max inventory cap, max risk cap, stop loss, forced exit, no martingale, and no unlimited averaging down. Phase 4 is future continuous probabilistic inventory trading only after paper evidence supports it.

Canonical safe paper command:

```bash
python main.py
```

Explicit paper command:

```bash
python main.py --mode paper --interval 60
```

Live runtime requires explicit operator intent:

```bash
python main.py --mode live --interval 60
```

Live mode is still blocked by readiness checks while allowance/execution validation is incomplete. Always inspect `.env` and `config/settings.py` before live-risk work.

---

## 1.5 Governance Status

The project enforces a strict cross-agent governance substrate to prevent duplicate investigations and token context waste.

- **Governance Phase**: `PROJECT_OS_V1` (Phase 1 Complete, Phase 1.5 Hardened)
- **Active Question**: `LOW_PRICE_TRUTH_RESOLUTION_001` (Active, blocking strategy/sizer/execution changes)
- **Audit Registry Status**: ACTIVE / IMPLEMENTED (`docs/research/AUDIT_REGISTRY.json`)
- **Decision Registry Status**: ACTIVE / IMPLEMENTED (`docs/research/DECISION_REGISTRY.json`)
- **Authority Map Status**: ACTIVE / IMPLEMENTED (`docs/research/RESEARCH_AUTHORITY_MAP_V2.md`)

*Core Constraint*: No strategy changes, sizer weight edits, or execution modifications are permitted until the active question is closed.

---

## 1.7 Desktop Migration and Refactor Session (2026-06-26)

### Environment

- **Desktop Migration**: Repository moved from notebook (user `poh_2`) to desktop (user `POOHXYZ`). The `.venv` was broken due to hardcoded path mismatch. Rebuilt fresh using `C:\Users\POOHXYZ\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv` followed by `pip install -r requirements.txt`. All 297 dependencies installed cleanly.
- **Environment Status**: Python 3.12.10 under `POOHXYZ`. `pydantic` 2.12.5, `py-clob-client` 0.34.6, `websockets` 16.0 all verified. `PolymarketTrader` import confirmed clean. `py_compile` passes for `trader.py` and `trader_presentation.py`.

### Trader Refactor Batch 1 — COMMITTED

- **Commit**: `e76581fb` — `refactor: extract trader presentation helpers`
- **Scope**: Extracted presentation formatting helpers from `PolymarketTrader` into `polymarket/trader_presentation.py` (206 lines). Existing method names preserved via proxy delegation. No execution, risk, sizing, reconciliation, or live/paper behavior changed.
- **Files changed**: `polymarket/trader.py` (−98 lines), `polymarket/trader_presentation.py` (new, +206 lines)
- **Status**: `BATCH_1_COMPLETE`. Batch 2 has NOT started and requires Architecture Governance gate check before proceeding.

### Paper Runtime Validation — COMPLETED

- **Run ID**: `20260626T135846Z_19480_d6b9f23e`
- **Duration**: 10 minutes 54 seconds
- **Cycles**: 11 completed
- **Events emitted**: 443 (from `runtime/event_stream/runtime_events_2026-06-26_001.jsonl`)
- **Heartbeat rate**: 132 events ≈ exactly 660s ÷ 5s interval
- **DATA status**: DEGRADED on startup (orderbook warm-up) → OK after first cycle
- **Paper guard**: Enforced throughout — zero live orders, zero wallet writes
- **Risk state**: NORMAL, 0% exposure, guard OK
- **Shutdown**: SIGTERM at 660s limit (timeout wrapper), exit 124, expected

### Agent Operating System v1 — COMMITTED

- **Commit**: `65711bc` — `docs: implement AI agent operating system rules`
- **Scope**: Added 6 new agent roles (24–29), Task Class system (0–9), Evidence Grade system (A–E), mandatory task output contract, session handoff rule, commit boundary rules, Batch 2 gate rule, and `.md` routing rule to `AGENTS.md`, `MASTER_AGENT_ROUTER.md`, and `PROJECT_RULES.md`.
- **Design document**: `docs/architecture/AI_AGENT_OPERATING_SYSTEM_DESIGN_001.md`

### Architecture Master Plan — COMMITTED

- **Document**: `docs/architecture/QUANT_ARCHITECTURE_MASTER_PLAN_001.md`
- **Scope**: Full 17-section enterprise architecture plan. Target state: `trader.py` ≤ 1,000 lines (currently 13,125). 10-batch decomposition roadmap defined. Module ownership, dependency rules, import rules, data architecture, schema registry, dashboard contract, and replay architecture all specified.

### Repository Documentation Cleanup — COMMITTED (12 commits)

Root markdown cleanup completed across two phases:

| Phase | Method | Files Handled |
|-------|--------|--------------|
| Untracked R1–R7 (+ Pilot + R6) | `mv` + `git add` | ~345 files |
| Tracked T1–T5 | `git mv` (R100 renames, history preserved) | 113 files |
| Duplicate removed | `rm` | 1 file |
| **Total** | | **~459 files** |

**Repository `docs/` state after cleanup:**
- `docs/architecture/`: 107 files (design docs, specs, plans, governance)
- `docs/audits/`: 236 files (forensic audits, pre-commit audits, validations)
- `docs/reports/`: 165 files (commit reports, implementation reports, batch reports)
- `docs/research/`: committed research governance, registries, and evidence docs

**Root tracked `.md`**: Now exactly the 20 designated entrypoints (AGENTS.md, README.md, PROJECT_RULES.md, MASTER_AGENT_ROUTER.md, CURRENT_PROJECT_STATUS.md, CODEX_START_HERE.md, FILE_INDEX.md, DOCUMENTATION_MAP.md, CLAUDE.md, and 12 others) plus 1 session batch report.

### Current HEAD

`6505296` — docs: add log governance post execution validation (2026-06-27)

---

## 1.8 Runtime Log Governance Phase A — COMPLETE (2026-06-27)

### What was done

The `logs/` directory accumulated **1.6 GB** of session log files from 856 old trading sessions (May–June 2026). A new offline FLAOS maintenance tool (`tools/flaos/log_governance.py`) was designed, implemented, and executed to safely reclaim this space.

**Phase A results:**
- **Files deleted**: 856 old `polytrade_bot_YYYYMMDD_HHMMSS_PID.log[.N]` session log files
- **Space reclaimed**: **1,411.7 MB** across two execute passes
- **`logs/` before**: 1.6 GB → **after: 219 MB**
- **JSONL event stream files**: **3 files intact, untouched**
- **Trading/runtime code changed**: **NO — offline tool only**
- **Bootstrap post-execution**: HEALTHY
- **Failures**: 0

### Safety gates completed

1. Gate audit (`BATCH_3D_GATE_CHECK_001`-level review) confirmed: age ≥ 8 days, 0 JSONL deletes, 0 non-polytrade files, session guard PASS
2. User explicitly authorized execute via `RUNTIME_LOG_GOVERNANCE_EXECUTE_AUTHORIZATION_001`
3. Post-execution validation confirmed JSONL intact and bootstrap HEALTHY

### What is NOT done (Phase B — separate gate required)

- `utils/logger.py` `backupCount` fix to prevent future accumulation — **CLASS 7, separate gate**
- JSONL compression (files < 3 days old at time of execution) — **Phase C, when JSONL ages**

### FLAOS Tooling Added

| Tool | Location | Purpose |
|------|----------|---------|
| `tools/flaos/log_governance.py` | New | inspect / plan / dry-run / execute / report subcommands |
| `tests/test_flaos_log_governance.py` | New | 28 tests, all pass |
| `tools/flaos/bootstrap.py` | Updated | Health check, pipeline resolution |
| `tools/flaos/runtime_session.py` | Pre-existing | Session guard for maintenance ops |

### Next recommended direction

A **POST_MAINTENANCE_STRATEGY_REVIEW_001** gate check is recommended before resuming Batch 3D structural refactoring. The maintenance sprint changed the operational environment; a brief strategy review confirms the correct next refactor scope and evidence posture before continuing `trader.py` decomposition.

---

## 1.6 Migration, Recovery, and Audits (2026-06-20)

- **Machine Migration**: Successfully migrated the workspace to a new host machine on 2026-06-20.
- **Environment Status**: Fully recovered under Python 3.12.10. The virtual environment `.venv` was recreated, clean dependencies installed, and all 23 targeted tests passed.
- **Option D Telemetry Restart**: The paper shadow telemetry run has been successfully restarted (`OPTION_D_RESTART_AFTER_MIGRATION_001` verdict `RESTART_SUCCESS`) under Run ID `20260619T174124Z_9572_52c34f1f`. It is actively scanning markets and outputting system health and stop-loss telemetry.
- **Risk Audit Completed**: Completed the `MICRO_RECOVERY` Counterfactual Audit (`MICRO_RECOVERY_COUNTERFACTUAL_AUDIT_001`). Verdict is **`PROTECTIVE_CORRECT`**: current tight gates correctly prevent overtrading in bad regimes, saving the bot from an estimated ~$0.63 USD (micro-size) or ~$12.65 USD (standard size) in unnecessary losses over the last 24h.
- **Funnel Audit Completed**: Completed the Entry Funnel Root Cause Audit (`ENTRY_FUNNEL_ROOT_CAUSE_AUDIT_001`). Verdict is **`YES`**: under-trading exists (capture rate of 0.29%). Timing gates (13.10% removed, 15.6% win rate) and risk floors (16.40% removed, 37.5% win rate) are protective, but `delta_extreme` (51.14% removed, 20.8% win rate but extremely cheap entry prices) is a genuine **alpha leak** worth +$6.17 USD (standard sizer) in missed profit.



---

## 2. What Works Now

The following parts are currently working or present in the project:

- Terminal UI works and has been upgraded in place to Terminal UI V2 responsive dashboard mode.
- Terminal UI V2 supports `--ui auto|compact|standard|wide|fullscreen`; default is `auto`.
- Terminal UI V2 supports `--fps low|medium|high`; default is `medium`.
- Terminal UI V2 detects terminal width/height, falls back to compact mode when the terminal is too small, and shows minimum/recommended terminal size guidance.
- Terminal UI V2 keeps long messages inside bounded rolling log panels with safe truncation.
- BTC/ETH 5-minute market scanner works.
- Binance/price oracle feed works.
- WebSocket status shows `Synced`.
- Cycle loop works.
- Paper mode exists.
- Paper mode is now the default runtime unless `--mode live` is explicitly passed.
- Paper mode uses real Polymarket market data/orderbooks but simulates orders and fills locally.
- Paper mode never connects to live wallet balance, never requires allowance, and never sends live orders.
- Paper mode logging is now fail-soft on Windows file locks:
  - File logs use unique per-run filenames.
  - Realtime CSV logs use unique per-run filenames.
  - If Windows locks a log or CSV file, that file logger is disabled for the session and paper mode continues.
- Phase 1/2 observability fixes were implemented on 2026-05-08:
  - `daily_report.py` and `utils/telegram_reporter.py` now load and combine `scan_log*.csv` files, including old `scan_log.csv` and new per-run `scan_log_<timestamp>_<pid>.csv`.
  - `utils/quant_event_logger.py` writes fail-soft JSONL quant events under `runtime/quant_data/`.
  - `utils/telegram_alerts.py` provides a fail-soft alert cooldown/dedup layer.
- Phase 3 observability wiring was implemented on 2026-05-08:
  - `PolymarketTrader` initializes `QuantEventLogger` and `TelegramAlertLayer` safely.
  - Runtime now emits JSONL events for market snapshots, decisions, order intent/submit/fill/fail, trade open/close, risk events, reconciliation blocks, and low-frequency system health.
  - Clear trader Telegram sends were routed through centralized `notify_startup`, `notify_entry`, `notify_exit`, `notify_risk`, `notify_critical`, `notify_summary`, and `notify_incident` helpers where safe.
  - Observability and Telegram failures are caught and must not crash paper execution.
- Runtime Ownership v1 was paper-validated on 2026-05-29:
  - Controlled consolidation removed two pre-ownership duplicate paper runtimes, then fresh patched run `20260529T033511Z_32308_89dc46d3` validated the owner guard.
  - Paper runtime owner file creation, heartbeat update, duplicate startup block, Ctrl+Break shutdown, and owner release were observed.
  - Fresh patched run PID `32308` exited with return code `0` and had zero run-scoped parse errors across emitted rows.
  - Previous date-level evidence from duplicate-runtime periods remains contamination-risk evidence; use run-scoped analysis only for old mixed periods.
- Exception Observability v1 is PAPER_VALIDATED as of 2026-05-29:
  - Targeted tests passed and simulated `runtime_loop_exception` system_health emission works.
  - Paper run B `20260529T062249Z_57004_46908310` produced 77 `runtime_loop_exception` system_health rows (cycles 124–200+) from a real `AttributeError: 'RiskManager' object has no attribute '_balance'` bug.
  - All 77 exception rows were correctly captured with: `health_event: runtime_loop_exception`, `exception_type: AttributeError`, `exception_message`, `cycle_num`, `run_id_in_payload`, `recovery_action: cycle_skipped_continue`. The runtime loop never crashed.
  - Bug root cause: 4 call sites in `polymarket/trader.py` accessed `_balance` incorrectly on `RiskManager`. Three used `self._risk_mgr._balance` directly (raised `AttributeError` at runtime). A fourth used `getattr(self._risk_mgr, "_balance", 0.0)` which silently returned `0.0` for every `cycle_risk_pause` JSONL event. Fixed 2026-05-29: all 4 changed to `self._risk_mgr.balance` (public property). `cycle_risk_pause` events now carry the real bankroll balance.
  - Exception Observability validated: real runtime-loop exceptions are captured in `system_health` JSONL, runtime continues via `cycle_skipped_continue`, no crash.
- ENTRY_MODEL_TRUTH_ENVELOPE_V1 is PAPER_VALIDATED as of 2026-05-29 (Verdict: PASS — all 5 JSONL categories confirmed across two paper runs):
  - Implemented 2026-05-29. Additive `entry_model_truth_envelope_v1` sub-object added to decision_log, risk_log, trade_open, position.metadata, path_truth, and trade_close.
  - Envelope carries: schema_version, truth_status, producer_stage, model_output_ready, model_attempted, model_probability_yes/no, selected_side, true_probability, fair_value, ev_after_spread, expected_value, confidence, ev_missing_reason, lineage_reference_only.
  - truth_status values: full | probability_only | ev_only | absent.
  - path_truth and trade_close carry the envelope from position.metadata; emit entry_model_truth_carry_status=absent_in_metadata for legacy/minimal fill paths.
  - 23 focused tests pass. No regressions introduced (all pre-existing failures confirmed pre-existing).
  - Paper validation run A `20260529T050453Z_42972_33b927b5`: decision_log 100% envelope (truth_status: ev_only + absent + full observed), risk_log carry-path confirmed, 0 orphans.
  - Trade lifecycle audit (Run A zero trades): TRADE_BLOCKED — delta_extreme/imbalance_extreme post-EV guard blocked all EV-positive cycles. Report: `docs/research/runtime_health/trade_lifecycle_evidence_audit_20260529.md`.
  - Paper validation run B `20260529T062249Z_57004_46908310` (snapshot 06:31:35Z): 2 ETH NO trades opened and closed naturally.
    - trade_open (2 rows): truth_status=full, computed_by=trade_open_context, serialization_source=last_quant_details, model_probability_yes/no non-null.
    - path_truth (6 rows, 3 per trade): truth_status=full, carried_from=position_metadata, model_probability_yes/no=None (expected thinning), true_probability exact float match to trade_open.
    - trade_close (2 rows): truth_status=full, carried_from=position_metadata, true_probability exact match.
    - Cross-stage paper_trade_replay_key join confirmed: Trade 1 → DL=27, TJ=2, PT=3; Trade 2 → DL=9, TJ=2, PT=3.
    - candidate_trace_id differs between trade_open and trade_close (empirically confirmed — paper_trade_replay_key is the only reliable cross-stage join key).
  - All 8 confirmation items confirmed. No bugs found. No lineage contamination. No runtime impact.
  - Paper validation report: `docs/research/runtime_health/entry_model_truth_envelope_v1_paper_validation.md`.
  - Lifecycle audit report: `docs/research/runtime_health/entry_model_truth_envelope_v1_lifecycle_audit.md`.
- Phase 4 runtime stability / clean shutdown hardening was implemented on 2026-05-08:
  - `PolymarketOracleFeed` start/stop is now idempotent and owns clean shutdown for its price, epoch/PTB, and WebSocket threads.
  - Oracle shutdown signals the WebSocket loop, joins background threads with timeouts, closes the HTTP client, and suppresses closed-stream logging failures.
  - `VirtualPriceToBeatTracker`, `PolymarketTrader`, `RealtimeLogger`, Binance market feed, quant indicator feed, Telegram notifier, and the daily report scheduler now expose shutdown/close-style cleanup hooks.
  - The realtime paper/live loop now closes the realtime logger, trader-owned feeds, and daily report scheduler on normal shutdown.
  - Added shutdown regression tests covering oracle thread cleanup, repeated start/stop, trader shutdown, and closed-stream logging behavior.
- Phase 5 offline data quality and replay analyzer tools were implemented on 2026-05-08:
  - `tools/quant_data_quality.py` validates quant JSONL files under `runtime/quant_data/` without touching runtime trading behavior.
  - `tools/replay_analyzer.py` reads trade, decision, execution, risk, and market snapshot JSONL files and writes offline replay summaries under `runtime/reports/`.
  - Replay metrics include trade count, win rate, PnL, holding time, skip reasons, approved/rejected decisions, risk rejects, execution failures, entry spread/confidence, and PnL by outcome/asset.
  - These tools are offline-only and must not be used to alter strategy, risk sizing, wallet, orderbook, or execution decisions until a separate explicitly scoped phase.
- Compact Research State Layer was implemented on 2026-05-11:
  - `tools/research_state_writer.py` writes compact research summaries under `runtime/research_state/`.
  - Future research/replay/lifecycle/no-entry/observability-review tasks should read `runtime/research_state/latest_research_state.md` before opening large reports, logs, or JSONL.
  - Compact state files summarize replay maturity, direct/proxy field rates, candidate-loss counts, lifecycle bottlenecks, UNKNOWN lifecycle rate, EV-null reasons, latest run ID, blind spots, and recommended next step.
  - These files are offline summaries only and must not feed runtime trading decisions.
- Phase 6 paper trading runbook and evaluation workflow was implemented on 2026-05-08:
  - `docs/PAPER_TRADING_RUNBOOK.md` documents paper start commands, expected files, Telegram expectations, stop conditions, a 24-hour checklist, post-run analysis commands, pass/fail criteria, and live-readiness review items.
  - `tools/paper_evaluation_report.py` reads generated data quality and replay reports and writes `paper_evaluation_YYYY-MM-DD.json` or `paper_evaluation_YYYY-MM-DD_to_YYYY-MM-DD.json` under `runtime/reports/`.
  - The evaluation returns `PASS`, `CAUTION`, or `FAIL` using conservative offline-only criteria for data quality, execution failures, severe risk/system-health issues, sample size, spread/liquidity skips, PnL, and drawdown.
  - The evaluator does not affect trading runtime state and must not be used as automatic permission to trade live.
- Paper balance source option was implemented on 2026-05-08:
  - `PAPER_BALANCE_SOURCE=virtual` remains the default and keeps existing isolated paper cash behavior.
  - `PAPER_BALANCE_SOURCE=wallet_reference` fetches real wallet/CLOB collateral balance as a read-only paper sizing reference and labels the source as `wallet_reference_paper`.
  - Wallet-reference paper mode shows wallet bankroll, paper sizing balance, paper cash, source, `PAPER ONLY`, and `NO LIVE ORDERS` in startup/dashboard surfaces.
  - If wallet balance fetch fails, paper mode logs a warning, falls back to `paper_virtual`, and continues without enabling live execution.
  - `WALLET_REFERENCE_REFRESH_SECONDS` controls low-frequency refresh; default is 300 seconds.
- Bankroll/runtime diagnostics work through 2026-05-10:
  - `BANKROLL_TIER_ARCHITECTURE_V2` is implemented through centralized bankroll tier metadata and hysteresis. Runtime surfaces `bankroll_tier_id`, `bankroll_tier_name`, `bankroll_family`, `bankroll_risk_profile`, tier lock, and hysteresis state.
  - `MICRO_SURVIVAL_MODE` is available for paper MICRO bankrolls under the configured threshold and remains isolated from live mode and bankrolls >= `$100`.
  - MICRO adaptive timing is available only for paper MICRO family tiers. It does not loosen STANDARD / BASE / GROWTH / CAPITAL behavior and keeps the hard MICRO close floor.
  - Orderbook empty-book recovery uses a short bounded recovery window and reports `liquidity_state`, recovery attempt/success/failure, and retry count.
  - CLOB orderbook resilience classifies HTTP/rate-limit/timeout/token/client issues, uses bounded retry/backoff/cooldowns, and degrades safely without changing strategy or execution behavior.
  - `empty_orderbook` retry regression fixed 2026-05-29 in `polymarket/client.py`: epoch-boundary empty books were previously in the immediate-raise block alongside `stale_orderbook` and `invalid_orderbook`, bypassing all retry machinery. Fixed by removing `empty_orderbook` from the raise block and routing it through the `clob_empty_response` retry path. `stale_orderbook` and `invalid_orderbook` remain terminal.
  - `tools/session_runtime_evaluator.py` supports same-day UTC filters with `--since HH:MM` and `--until HH:MM`, so current runs can be evaluated without stale same-day events.
  - Terminal UI V2 now shows compact bankroll tier, MICRO survival, MICRO timing, liquidity/recovery, cutoff reason, and early-window timing fields.
- Strict startup config validation was implemented on 2026-05-08:
  - `utils/config_validator.py` validates `MODE`, `PAPER_BALANCE_SOURCE`, `TELEGRAM_ENABLED`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `LIVE_TRADING_ENABLED`.
  - Invalid `MODE` or invalid critical boolean values fail startup clearly with allowed values where applicable.
  - Invalid `PAPER_BALANCE_SOURCE` falls back to `virtual` with a warning.
  - Telegram disables safely when enabled but token/chat ID is missing.
  - Startup logs now include a redacted configuration summary for mode, execution, live-order status, balance source, wallet-reference status, Telegram, quant logging, replay analyzer, RiskAgent, and ExitAgent.
  - Secrets are not printed in startup validation output.
- Documentation Sync Phase was performed on 2026-05-08 before new feature work:
  - `README.md`, `CURRENT_PROJECT_STATUS.md`, `CODEX_START_HERE.md`, `PROJECT_RULES.md`, `AGENTS.md`, `docs/PROJECT_STRUCTURE.md`, `PROJECT_STRUCTURE.md`, `docs/OBSERVABILITY_PLAN.md`, and `docs/KNOWN_ISSUES.md` were aligned to the current implementation.
- Market window timing works.
- Portfolio panel displays values.
- AI cycle panel displays decisions.
- Live orderbook read path now returns fresh BTC/ETH 5-minute `BID`, `ASK`, and `SPREAD` values through the trader/display metrics path.
- Wallet/portfolio source is now explicit:
  - Paper mode uses virtual paper capital only.
  - Live mode refreshes terminal portfolio cash/equity from live CLOB collateral balance.
  - Terminal portfolio includes `balance_source` so operators can see whether values are paper virtual or live wallet/CLOB sourced.

Strategy and risk modules exist:

- Counter-Momentum.
- Markov Bounds.
- Kelly Sizing.
- Micro-Grinder mode.
- ExitAgent protection.
- Risk floor.

These working parts are meaningful. Future assistants should build on them instead of replacing the architecture.

Stability classification:

- Stable enough for continued paper validation:
  - Paper mode default.
  - Terminal UI V2 rendering and responsive layout tests.
  - Paper/live mode separation tests.
  - Windows logging PermissionError resilience tests.
  - OrderIntent guard tests.
  - Bankroll rank hysteresis tests.
  - Risk mode transition tests.
- Implemented but needs ongoing live-data monitoring:
  - BTC/ETH active market scanner.
  - Live CLOB orderbook display path.
  - Binance/oracle/PTB feed path.
  - Portfolio source labeling.
- Partially implemented / live-risky:
  - Live order placement path.
  - Live balance/allowance readiness.
  - Fill/cancel/reconcile lifecycle.
  - Telegram daily reporting content still needs review before relying on it operationally.
- Implemented observability:
  - JSONL quant event logger utility and trader runtime wiring.
  - Telegram alert cooldown/dedup utility and safe trader routing for clear alert call sites.
  - Daily report aggregation over per-run CSV logs.
- Implemented runtime stability hardening:
  - Oracle/WebSocket background threads stop cleanly through explicit lifecycle hooks.
  - Repeated oracle start/stop does not duplicate worker threads.
  - Closed pytest/logging streams are handled fail-soft during shutdown.
  - Runtime Ownership v1 prevents duplicate paper runtime startup through a paper owner file, startup guard, heartbeat, stale-owner recovery, explicit operator override, and graceful release. Status: `PAPER_VALIDATED` on run `20260529T033511Z_32308_89dc46d3`.
  - Exception Observability v1 emits structured `runtime_loop_exception` system_health telemetry in tests. Status: `TEST_VALIDATED`; natural paper-runtime exception evidence is still required.
- Implemented offline quant analysis:
  - Quant JSONL data quality checker.
  - Offline replay analyzer and report writer.
  - Offline no-entry analyzer and session runtime evaluator for paper-session bottleneck classification.
  - Offline paper evaluation report that combines data quality and replay outputs into `PASS`, `CAUTION`, or `FAIL`.
  - Run-scoped continuity checks can isolate a real paper `run_id` from same-day tiny/probe runs and malformed day-level lines.
  - Offline no-entry reporting now distinguishes execution-log diagnostic volume from true execution-stage submit/fill/cancel attempts.
  - Offline Telegram summary formatter exists for report-derived paper evidence summaries; it is not wired into runtime and sending is explicit.
  - Tests covering valid, malformed, empty, and date-range datasets.

---

## 3. What Is Not Working Yet

The bot is not fully validated for live trading.

Current known gaps:

- Execution is not validated.
- No confirmed live order placement has been proven.
- No confirmed fill/cancel/reconcile cycle has been proven.
- Live account allowance is not ready in current verification evidence.
- Live runtime is not the default and must not be started except with explicit `--mode live`.

Orderbook status:

- The previous `no_orderbook` blocker was fixed in code on 2026-05-07.
- `python main.py --mode verify` reported BTC and ETH `orderbook=OK` with live `BID`, `ASK`, and `SPREAD`.
- The same `PolymarketTrader.get_market_display_metrics()` path feeding the realtime terminal returned live BTC/ETH YES/NO orderbook values.
- Continue monitoring the full realtime UI, but do not restart/rebuild the orderbook architecture unless fresh evidence shows it regressed.

Wallet/portfolio status:

- The previous wallet/portfolio source ambiguity was fixed in code on 2026-05-07.
- In paper mode, the terminal remains virtual and must not fetch live balances.
- Paper mode uses virtual starting balance, simulated cash/equity/exposure/PnL, and `balance_source=paper_virtual`.
- Paper mode can optionally use real wallet/CLOB collateral as a read-only sizing reference with `balance_source=wallet_reference_paper`; execution remains paper-only.
- Startup validation warns if `LIVE_TRADING_ENABLED=true` is present while running paper mode and keeps live orders disabled.
- In live mode, `dashboard_portfolio_state()` refreshes from the live CLOB collateral balance after connection.
- In live mode, `Start`, `Cash`, and `Equity` are aligned to the live wallet/CLOB balance at session startup instead of the paper/config seed.
- `python main.py --mode verify` reported balance source `clob_collateral` with cash/equity/sizing matching.
- The same verify run still reported `missing_allowance`, so do not describe the bot as live-ready.

---

## 4. Current Terminal Evidence

Observed terminal evidence:

- Terminal UI renders.
- BTC/ETH scanner panels render.
- Price/oracle feed updates.
- WebSocket status shows `Synced`.
- Cycle loop continues running.
- AI cycle panel shows decisions.
- Portfolio panel shows `Start`, `Cash`, and `Equity` values.
- Portfolio panel now carries a `Source` value, such as `paper_virtual` or `clob_collateral`.
- Paper runtime prints a clear `PAPER MODE` banner showing real market data on, live orders off, simulated execution on, and wallet risk none.
- Read-only verify mode showed live BTC/ETH orderbooks with non-empty `BID`, `ASK`, and `SPREAD`.
- Example verification status: BTC `orderbook=OK`, ETH `orderbook=OK`.
- Read-only verify mode logged `[WALLET CONNECTED]`, `[USDC BALANCE]`, `[VERIFY BALANCE]`, and `[LIVE MODE READY]`.
- Latest verify evidence showed wallet balance source `clob_collateral`, balance status `MATCH`, zero positions, and `[LIVE MODE READY] ready=False` because `missing_allowance` remains.
- Paper validation run on 2026-05-07 used real BTC/ETH 5-minute markets and live CLOB orderbooks with `balance_source=paper_virtual`.
- The paper session summary reported `cycles_scanned=6`, `total_markets_scanned=12`, `total_opportunities_found=3`, `paper_orders_created=0`, `paper_fills=0`, `paper_exits=0`, `simulated_pnl=0.0`, and `max_drawdown=0.0`.
- Top paper skip reasons in that run were `confidence_too_low` (4), `Risk plan returned zero position size -- skipping.` (3), entry cutoff near market close (4 total), and `ev_below_threshold` (1).
- The strategy/orderbook path moved beyond the old `no_orderbook` failure: live orderbook EV evaluation produced an EV-level `decision=ENTER` candidate, but the risk/sizing layer blocked it with zero size. This indicates the observed no-trade result was caused by current risk/strategy thresholds and tiny bankroll sizing, not missing orderbook data.
- Windows logging finding on 2026-05-08:
  - Paper mode could start correctly but crash if `RotatingFileHandler` could not write/roll over a locked log file, or if `polymarket/realtime_logger.py` hit `PermissionError` during CSV `flush()`.
  - This is a runtime logging resilience issue, not a strategy/orderbook/wallet/execution issue.
  - Code now catches `PermissionError`/Windows errno 13 on log setup, CSV open, write, flush, close, and daily summary save. The affected file logger is disabled for the session and the trading loop should continue safely.
- Runtime shutdown finding on 2026-05-08:
  - The oracle WebSocket path could leave a background thread logging after pytest/log capture streams were closed.
  - `PolymarketOracleFeed.stop()` now signals all oracle workers, actively asks the WebSocket loop to close, joins threads, and closes the HTTP client.
  - Trader/runtime shutdown now calls the PTB/oracle cleanup path and closes realtime CSV logging on normal exit.
  - Validation passed without a post-pytest logging-to-closed-stream warning.
- Terminal UI V2 finding on 2026-05-08:
  - The old terminal dashboard could overflow, compress panels in fullscreen, and let important messages scroll away.
  - `utils/display.py` now contains a responsive Polymarket dashboard renderer with System Status, Portfolio, Risk, BTC Market, ETH Market, AI Decision, Execution, Skip Reasons, and Rolling Logs panels.
  - The bottom status line now shows `WS | ORACLE | ORDERBOOK | MODE | RISK | LATENCY | LOGGING`.
  - This is a UI/display-layer change only. It does not change strategy, risk, wallet, orderbook, or execution behavior.
- Terminal UI visibility update on 2026-05-10:
  - Portfolio/Risk panels now surface `BANKROLL_TIER_V2`, bankroll family/profile, bankroll mode, MICRO survival state, and micro position size.
  - Market/AI panels now show remaining time, first seen/evaluable seconds, cutoff policy/effective cutoff, MICRO timing branch/allow/deny state, latest deny reason, liquidity state, and empty-book recovery status.
  - Footer tags include compact `TIER | MICRO | LIQ | CUTOFF | RECOVERY` state.
  - This is observability-only. It does not change strategy, risk sizing, execution, wallet/allowance, order intent, reconciliation, paper/live separation, or websocket/orderbook behavior.
- Regime/probability documentation alignment on 2026-05-10:
  - Official roadmap docs now separate Phase 1 regime/probability diagnostics, Phase 2 inventory replay research, Phase 3 bounded multi-price inventory design, and Phase 4 future continuous probabilistic inventory trading.
  - These docs do not implement inventory trading and do not authorize execution behavior changes.
- Documentation/observability finding on 2026-05-08:
  - Older docs still described stale HFT/live-ready assumptions and fixed `scan_log.csv` daily reporting.
  - Runtime logging now writes per-run CSV files named `scan_log_<timestamp>_<pid>.csv`.
  - Fixed: `daily_report.py` and `utils/telegram_reporter.py` now aggregate `scan_log*.csv` and sort by `timestamp_utc` when available.
  - Fixed: `utils/telegram_alerts.py` adds central cooldown/dedup wrappers for startup, entry, exit, risk, critical, summary, and incident alerts.
  - Added: `utils/quant_event_logger.py` writes structured JSONL under `runtime/quant_data/` and disables only the affected writer on `PermissionError` / Windows errno 13.
- Offline analyzer finding on 2026-05-08:
  - Added `python tools/quant_data_quality.py --date YYYY-MM-DD --write-report`.
  - Added `python tools/replay_analyzer.py --date YYYY-MM-DD --csv` and `python tools/replay_analyzer.py --from YYYY-MM-DD --to YYYY-MM-DD --csv`.
  - Reports are written under `runtime/reports/` and are read-only with respect to trading runtime state.
- Paper evaluation finding on 2026-05-08:
  - Added `python tools/paper_evaluation_report.py --date YYYY-MM-DD`.
  - Added `python tools/paper_evaluation_report.py --from YYYY-MM-DD --to YYYY-MM-DD`.
  - The report reads offline analyzer outputs only and writes `runtime/reports/paper_evaluation_*.json`.
  - `PASS` means paper evidence is clean enough for further review, not that live profitability or live readiness is guaranteed.
- Run-scoped offline evidence finding on 2026-05-15:
  - Selected real paper run: `20260515T143223Z_22760_1b6c0b35`.
  - `tools/quant_data_quality.py --date 2026-05-15 --run-id 20260515T143223Z_22760_1b6c0b35 --write-report` reported scoped continuity `PASS`.
  - Whole-day May 15 quality still has malformed JSONL warnings, but scoped continuity found no direct malformed-line match to the selected run ID.
  - Offline no-entry/root-cause reports classify the selected run as `cutoff` / `time_unsafe` primary with `risk_plan_zero` secondary.
  - Execution is not the root cause for this run: execution-log rows were diagnostic/non-attempt `market_analysis_exception` evidence, with zero true execution-stage attempts/failures after cutoff/risk blocks.
  - Admission/selection probes showed analysis was present: cycles reached analysis, executable/model/EV evaluation was visible, and the stop occurred at risk/cutoff gates.
  - Orderbook/liquidity was not the primary blocker: orderbook unavailable/stale counts were zero and liquidity was reported healthy in the scoped offline evidence.
  - Added `tools/offline_telegram_summary.py` to format a Telegram-safe offline paper evidence summary from generated reports; default behavior prints only, and `--send` is explicit.
  - Added a local read-only Offline Quant Report Dashboard for completed `runtime/reports/*.json` files: `python dashboard/offline_quant_report_dashboard.py --reports-dir runtime/reports --host 127.0.0.1 --port 8765`.
  - The dashboard is offline/report-only and must not be wired into runtime decisions, live APIs, websockets, strategy, risk sizing, cutoff rules, execution, wallet, or paper/live behavior.
  - No runtime behavior, strategy, risk sizing, cutoff rules, execution path, wallet/live config, or `polymarket/trader.py` behavior changed from this evidence.

Interpretation:

- Market discovery, timing, and feed plumbing are partly operational.
- The bot is cycling and can now read fresh live CLOB orderbooks for active BTC/ETH 5-minute markets.
- Portfolio values are now source-labeled. In live mode they are wired to CLOB collateral balance; in paper mode they stay virtual.
- Paper mode is operating safely with real market data and isolated virtual capital. A short validation session did not naturally create paper orders/fills/exits because risk/strategy gates blocked all entries.

Do not over-interpret the UI panels. Visible portfolio numbers are only meaningful when the displayed/logged source is checked. `clob_collateral` means live CLOB balance; `paper_virtual` means simulated paper capital.

---

## 5. Architecture Status

Primary runtime path:

```text
main.py
  -> polymarket realtime mode
  -> polymarket/trader.py
  -> market discovery / scanner
  -> Binance and oracle price feed
  -> signal modules
  -> risk and order planning
  -> terminal display and logging
```

Important project areas:

- `main.py` - CLI dispatcher and realtime loop orchestration.
- `config/settings.py` - environment settings, live/paper flags, validation.
- `polymarket/trader.py` - main Polymarket trading coordinator.
- `polymarket/client.py` - CLOB authentication, balances, orders, redemption helpers.
- `polymarket/gamma_fetcher.py` - market/event/token discovery.
- `polymarket/market_feed.py` - Binance feed singleton.
- `polymarket/oracle_price_feed.py` - oracle/PTB price path.
- `polymarket/virtual_ptb.py` - virtual price-to-beat tracker.
- `polymarket/signal.py` - realtime signal logic.
- `polymarket/backtester_5m.py` - backtest signal/performance path.
- `polymarket/order_manager.py` - converts signal/risk inputs into order risk plans.
- `polymarket/realtime_logger.py` - scan/trade logging.
- `utils/risk_manager.py` - canonical Polymarket risk policy.
- `utils/position_tracker.py` - position and drawdown state.
- `utils/display.py` - terminal display.
- `utils/display.py` now includes Terminal UI V2 responsive layout logic for the Polymarket realtime dashboard.
- `utils/telegram_reporter.py` - Telegram alerts and reports.
- `utils/telegram_alerts.py` - fail-soft Telegram cooldown/dedup utility.
- `utils/quant_event_logger.py` - fail-soft structured JSONL quant event utility.
- `utils/scan_log_loader.py` - shared reader for old and per-run realtime scan CSV files.
- `daily_report.py` - daily summary/report sender; now reads combined `scan_log*.csv`.
- `tools/offline_telegram_summary.py` - offline-only Telegram summary formatter/sender for generated paper evidence reports; not wired into runtime.
- `docs/OBSERVABILITY_PLAN.md` - logging/Telegram/JSONL observability status and roadmap.
- `docs/KNOWN_ISSUES.md` - current bugs, technical debt, and unfinished systems.

Secondary or experimental paths:

- `hft_paper_run.py` - active HFT paper simulation utility.
- `main.py --mode hft` and `hft/` - experimental HFT engine; paper-first only.
- `crypto_scalper/` - separate crypto scalper path.
- `dashboard/` and `web-dashboard/` - overlapping dashboards retained until a dedicated consolidation task.
- `polymarket/five_min_monitor.py` - standalone monitor.

Current architecture should be repaired and verified in place. Do not replace it with a new bot unless the user explicitly requests a rebuild.

Default runtime behavior:

```text
python main.py
  -> paper mode
  -> real market scanner/orderbooks
  -> local simulated execution only
  -> no wallet collateral or live order APIs

python main.py --mode live
  -> live readiness preflight
  -> blocked if allowance/execution readiness is not proven
```

---

## 6. Active Blockers

### 1. no_orderbook - fixed, monitor for regression

Previous symptoms:

- `BID`, `ASK`, and `SPREAD` are empty.
- Decision shows `SKIP no_orderbook`.
- Strategy cannot calculate real EV from live orderbook yet.

Current outcome:

- Terminal displays real `BID`, `ASK`, and `SPREAD` for active BTC/ETH 5-minute markets.
- Signal/risk path consumes the same orderbook values displayed in terminal.
- Orderbook reads retry temporary empty responses and reject stale books older than 3 seconds.
- Logs include market slug, condition ID, YES/NO token IDs, compact orderbook response, and best bid/ask.

Remaining caution:

- If `SKIP no_orderbook` reappears, first inspect fresh logs for stale or empty orderbook responses before changing strategy modules.

### 2. Wallet/Portfolio Sync - fixed, monitor for regression

Previous symptoms:

- Terminal shows `Start`, `Cash`, and `Equity`.
- It was not verified whether these values came from real wallet balance, paper seed, runtime state, or hardcoded config.

Current outcome:

- In paper mode, terminal clearly uses paper capital/state.
- In live mode, terminal `Start`, `Cash`, `Equity`, and sizing state connect to the live CLOB collateral balance.
- Logs include wallet address, balance source, cash/equity, exposure, and positions count.
- Startup/verify logs include `[WALLET CONNECTED]`, `[USDC BALANCE]`, and `[LIVE MODE READY]`.

Remaining caution:

- Current runtime `.env` still has `PAPER_TRADING=true` and `DRY_RUN=true`.
- Verify mode currently reports `missing_allowance`, so live mode is not ready for execution.
- Future assistants must still inspect `.env`, `config/settings.py`, and wallet/client code before making claims about balance sync.

### 3. Live Allowance / Execution Not Yet Validated

Symptoms:

- Verify mode reports `missing_allowance`.
- No confirmed live order placement.
- No confirmed fill/cancel/reconcile cycle.

Required outcome:

- A tiny controlled live-order validation plan exists before any live-risk execution.
- Order placement, fill detection, cancellation, and reconciliation are proven end to end.
- Logs and terminal output confirm exactly what happened.

### 4. Safe Paper Runtime - active default

Current outcome:

- `--mode` is no longer required; no argument defaults to safe paper mode.
- Legacy `--mode polymarket-realtime` and `--mode polymarket-paper` route to paper mode.
- Live runtime requires explicit `--mode live`.
- Paper order APIs are blocked from calling live CLOB order placement directly.
- Windows locked log/CSV files no longer crash paper mode. Future assistants should not alter strategy/risk/execution to fix logging `PermissionError`; inspect `utils/logger.py` and `polymarket/realtime_logger.py` first.
- Paper logs include `[PAPER ORDER]`, `[PAPER FILL]`, `[PAPER EXIT]`, and `[PAPER PNL]`.
- Paper session summary logs include cycles scanned, markets scanned, opportunities found, paper orders, fills, exits, PnL, max drawdown, and top skip reasons.

Latest paper validation:

- A real-data BTC/ETH paper run completed without touching live order APIs.
- Fresh BTC/ETH YES/NO orderbooks were visible in logs with bid/ask/spread and age under 3 seconds.
- The run found opportunities, including one EV-level `ENTER`, but all entries were blocked before execution by entry cutoff, low confidence, low EV, or zero-size risk planning.
- Result: no paper orders/fills/exits occurred in that short session; simulated cash/equity stayed at `$8.70`, exposure stayed `$0.00`, PnL stayed `0.0`.
- Latest scoped no-entry evidence for run `20260515T143223Z_22760_1b6c0b35`:
  - Continuity: `PASS`.
  - Primary blocker: `cutoff` / `time_unsafe`.
  - Secondary blocker: `risk_plan_zero`.
  - Execution is not root cause because no entry passed cutoff/risk into a true submit/fill/cancel attempt.
  - EV/probability fields were visible in offline admission/no-entry evidence.
  - Liquidity/orderbook readiness was healthy enough for analysis and was not the main blocker.
  - The local Offline Quant Report Dashboard can visualize this evidence from generated report JSON only; it is read-only and did not change runtime behavior.

### 5. Observability / Telegram Drift - partially fixed

Current status:

- App file logging and realtime CSV logging are fail-soft on Windows file locks.
- Terminal UI V2 has a bounded rolling log panel.
- Optional Telegram notifier exists and sends asynchronously.
- Telegram message builders exist for startup, trade, exit, settlement, risk, and error alerts.
- Daily report readers now combine old and per-run scan CSV files.
- JSONL quant event logger utility exists with fail-soft Windows lock handling.
- Telegram alert cooldown/dedup utility exists.
- Offline Telegram paper-evidence summary formatting exists through `tools/offline_telegram_summary.py`; it consumes generated offline reports and has no runtime integration.

Fixed in Phase 1/2 observability pass:

- `daily_report.py` and `utils/telegram_reporter.py` use `utils/scan_log_loader.py`.
- `utils/scan_log_loader.py` loads `runtime/realtime_logs/YYYY-MM-DD/scan_log*.csv`, preserves old `scan_log.csv` compatibility, and sorts rows by `timestamp_utc` when available.
- Tests: `tests/test_scan_log_loading.py`, `tests/test_quant_event_logger.py`, `tests/test_telegram_alerts.py`.

Remaining gap:

- Quant event logger and Telegram alert layer are now wired into the main trader loop for market snapshots, decisions, execution, trade, risk, and health events.
- Current paper diagnostics include cutoff behavior, MICRO timing branch state, liquidity/recovery state, bankroll tier metadata, and session evaluator UTC time filters.
- Some existing Telegram daily message content still contains stale wording and needs a dedicated copy/content cleanup.
- Offline Telegram summary is report-derived only; it should remain separate from runtime decision-making and automatic trading behavior.
- Full retention/compaction and incident-report files remain planned.

---

## 7. Do Not Rebuild Rules

- Do not tell the user to rebuild the bot from scratch.
- Do not replace the terminal UI, scanner, feed, strategy, or risk modules unless the user explicitly asks. Terminal UI V2 was added in place and should be extended, not rebuilt from scratch.
- Do not delete runtime logs, trade logs, scan logs, backtest results, config files, wallet helpers, or research records.
- Do not rewrite strategy logic during cleanup or documentation tasks.
- Do not bypass floor balance, single-trade cap, daily drawdown, reconciliation, or unknown-state guards.
- Do not claim live trading is ready without verified orderbook, wallet, execution, fill/cancel, and reconciliation evidence.
- Do not switch the default runtime away from paper mode.
- Do not route legacy realtime commands to live order execution.
- Do not call live order, cancel, redeem, signing, allowance, or wallet collateral paths from paper runtime.
- Do not claim orderbook works until `BID`, `ASK`, and `SPREAD` are visible in terminal.
- Do not claim wallet balance is synced unless the terminal reads real wallet balance.
- Do not promote HFT/live behavior from paper results alone.

If `.env` has `PAPER_TRADING=false` or `DRY_RUN=false`, treat the repo as live-risk until proven otherwise.

---

## 8. Next Priority Tasks

### Immediate (2026-06-26 session follow-up)

0. **Architecture Governance Gate Check** (`BATCH_2_GATE_CHECK_001`) — Role 29 gate check required before any Trader Refactor Batch 2 work begins. Preconditions: HEAD at `9acbda4`, core runtime clean, paper validated on `20260626T135846Z_19480_d6b9f23e`, active question status checked, all Batch 1 tests passing.

0a. **Update dashboard work** — `dashboard/src/pages/research/ResearchPage.tsx`, `tools/dashboard_state_aggregator.py`, and related files have uncommitted changes from the pre-migration session. These should be reviewed and committed as a separate dashboard batch before Batch 2 begins.

0b. **Update `CURRENT_PROJECT_STATUS.md`** — Done (this file, 2026-06-26).

### Ongoing

1. Continue Phase 1 regime/probability evidence collection in safe paper sessions.
   - Use the existing paper runtime only.
   - Treat `market_regime`, probability fields, indicator evidence, spread, liquidity, and cutoff diagnostics as research evidence.
   - Do not use these fields as automatic trade approval.

2. Build Phase 2 paper-only inventory replay research only after enough Phase 1 evidence exists.
   - Analyze reload/unload opportunity, opportunity decay, MFE/MAE, and regime-specific tradeability.
   - Keep replay output offline-only.

3. Continue longer safe paper sessions with live market data.
   - Use `python main.py` or `python main.py --mode paper --interval 60`.
   - Confirm the paper banner is visible.
   - Confirm terminal `Source paper_virtual`.
   - Confirm real `BID`, `ASK`, and `SPREAD` remain visible.
   - Watch whether natural market conditions create `[PAPER ORDER]`, `[PAPER FILL]`, `[PAPER EXIT]`, and `[PAPER PNL]` events without loosening risk rules.
   - If sessions keep skipping, compare top skip reasons before changing any strategy or risk thresholds.

4. Resolve live account allowance.
   - Confirm collateral allowance source and required approval path.
   - Do not bypass allowance checks.
   - Keep `[LIVE MODE READY] ready=False` until balance, floor, allowance, and verification checks pass.

5. Validate execution safely after allowance is fixed.
   - Confirm order creation code path.
   - Confirm cancel path.
   - Confirm fill detection.
   - Confirm position reconciliation.
   - Use paper mode or a tiny controlled live test only after explicit user approval.

6. Monitor orderbook regression.
   - Confirm full realtime terminal continues showing non-empty `BID`, `ASK`, and `SPREAD`.
   - If books are stale or empty, inspect `[TOKEN_FLOW]`, `[ORDERBOOK_FLOW]`, `[ORDERBOOK_RESPONSE]`, and `[ORDERBOOK_BEST]` logs.

7. Monitor portfolio regression.
   - Confirm paper mode keeps `Source paper_virtual`.
   - Confirm live mode keeps `Source clob_collateral`.
   - Confirm `[PORTFOLIO_SYNC]` logs cash/equity/exposure/positions count.

8. Keep docs aligned.
   - Update this file when terminal evidence changes.
   - Update `docs/PROJECT_STRUCTURE.md` when main path or data flow changes.
   - Update `docs/PROJECT_CLEANUP_REPORT.md` for cleanup decisions.
   - Update `README.md` only for user-facing command/path changes.

9. Continue observability hardening carefully.
   - Review generated JSONL during longer paper sessions and adjust payload fields only if needed.
   - Route any future high-volume Telegram alerts through `utils/telegram_alerts.py`.
   - Review and clean stale daily Telegram message wording.
   - Add retention/compaction and incident-report writers only in a scoped phase.
   - Keep logging changes isolated from strategy/risk/execution behavior.
   - Treat Runtime Ownership v1 as `PAPER_VALIDATED`; duplicate paper runtimes should now be blocked unless `--allow-duplicate-paper-runtime` is explicitly used.
   - Treat Exception Observability v1 as `PAPER_VALIDATED`; status confirmed by paper run B `20260529T062249Z_57004_46908310` (77 natural `runtime_loop_exception` rows from real `AttributeError` bug).
   - Keep old duplicate-runtime date-level evidence under contamination caveat; prefer run-scoped evidence for 2026-05-28/2026-05-29 mixed periods.
   - JSONL Writer Integrity v1.1 remains a future blocker; Runtime Ownership v1 reduces duplicate writers but does not add interprocess writer locking.

10. Monitor shutdown behavior during longer paper sessions.
   - Confirm Ctrl+C exits stop the oracle/WebSocket feed without delayed logging.
   - If new background helpers are added, give them explicit `stop()` / `close()` / `shutdown()` ownership and tests.

11. Use offline analyzers after paper sessions.
   - Run `python tools/quant_data_quality.py --date YYYY-MM-DD --write-report` before trusting a replay.
   - For run-level evidence, prefer `python tools/quant_data_quality.py --date YYYY-MM-DD --run-id RUN_ID --write-report` before drawing root-cause conclusions.
   - Run `python tools/replay_analyzer.py --date YYYY-MM-DD --csv` to summarize JSONL events.
   - Run `python tools/no_entry_analyzer.py --date YYYY-MM-DD --run-id RUN_ID --write-report` for scoped no-entry classification.
   - Use `python tools/offline_telegram_summary.py --date YYYY-MM-DD --run-id RUN_ID` to preview a Telegram-safe offline evidence summary; add `--send` only when explicitly intending to send.
   - Treat analyzer output as review evidence only; do not wire it into trading decisions without a separate approved phase.

---

## 9. Codex Working Instructions

Before modifying code:

1. Read `CURRENT_PROJECT_STATUS.md`.
2. For research, replay, lifecycle truth, no-entry, observability-review, or paper-session evidence tasks, read `runtime/research_state/latest_research_state.md` before opening large reports/logs/JSONL.
3. Read the latest real daily note in `research/daily/YYYY-MM-DD.md` when the task depends on daily notes.
4. Read `docs/PROJECT_STRUCTURE.md`.
5. Read `docs/PROJECT_CLEANUP_REPORT.md` if the task touches structure or cleanup.
6. Inspect `.env` and `config/settings.py` before any live-risk work.
7. For observability tasks, read `docs/OBSERVABILITY_PLAN.md` and `docs/KNOWN_ISSUES.md`.

Compact-state-first rule:

- Prefer `runtime/research_state/latest_research_state.md` over raw logs, JSONL, or large analyzer reports.
- Use larger reports only when compact state identifies a gap, the task explicitly requests deeper evidence, or targeted debugging requires it.
- Prefer counts/distributions over dumps.
- Avoid large report pastes and repeated replay summaries.
- Keep responses compact unless the user asks for exhaustive evidence.

Testing guidance:

```bash
# Full test suite
python -m pytest tests/ -q

# Import smoke
python -c "from polymarket.backtester_5m import PolymarketBacktester5m; print('OK')"

# Strategy smoke when strategy or import paths changed
python main.py --mode polymarket-backtest --days 3 --asset BTC

# Safe default paper loop
python main.py

# Explicit paper loop
python main.py --mode paper --interval 60

# Explicit live loop; readiness preflight must pass first
python main.py --mode live --interval 60
```

Run the strategy smoke only when strategy or import paths changed.

Known pre-existing test failures (do not fix without a scoped task):

- `tests/test_paper_mode.py`: 3 failures in the `event_driven_admission_packet_price_detail` family — correct specs for an unimplemented feature, intentionally deferred.
- `tests/test_stale_feed_kill_switch.py::test_fresh_feed_allows_normal_analysis_to_continue` — pre-existing integration gap.
- Total pre-existing: ~7 failures; all others pass (2217+ tests pass).

Any signal change must update both:

- `polymarket/signal.py`
- `polymarket/backtester_5m.py`

Any signal change requires a backtest before promotion.

---

## 10. Definition of Done

The project can only be described as live-trading ready when all of the following are true:

- Terminal shows active BTC/ETH 5-minute market windows.
- Terminal shows real `BID`, `ASK`, and `SPREAD`.
- Strategy calculates EV from the live orderbook data path.
- `SKIP no_orderbook` is resolved for valid active markets.
- Paper mode is clearly separated from live mode.
- Paper mode is the default runtime.
- Paper mode uses real market data and local simulated execution only.
- Live mode portfolio reads actual wallet balance.
- Live account allowance is confirmed ready.
- Order placement is confirmed.
- Cancel path is confirmed.
- Fill detection is confirmed.
- Position reconciliation is confirmed.
- Risk floor, single-trade cap, daily drawdown, and unknown-state guards remain active.
- Logs and terminal output provide evidence for every live-risk claim.

Until then, describe the bot as an active, partially working Polymarket 5-minute scalper with important live-readiness blockers, not as fully live-trading ready.
