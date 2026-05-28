# Runtime Executable Truth Source Audit

Date: 2026-05-26

Scope: read-only source audit for Hermes Phase64 `SESSION_EDGE` evidence requirements. No code changes. No runtime changes. No bot run. No replay. No commit. No push.

## Role Routing

- Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`
- Supporting roles: `10_BACKTEST_REPLAY_AGENT.md`, `16_PAPER_EVALUATION_AGENT.md`, `07_TEST_CI_AGENT.md`
- Why selected: the task asks whether existing runtime, report, and research evidence can support executable-truth intake without changing runtime behavior.
- Files allowed to inspect: `docs/`, `runtime/reports/`, `runtime/quant_data/`, existing audits, generated summaries, and compact research state.
- Files intentionally ignored: `polymarket/trader.py`, strategy modules, risk modules, execution modules, wallet/live config, bot launch paths, replay execution paths.

## Executive Verdict

```text
EXECUTABLE TRUTH STATUS: PARTIAL
HERMES PHASE64 EXECUTABLE_PNL: BLOCKED
RUNTIME TRUTH: PARTIAL, NOT CANONICAL EXECUTABLE TRUTH
```

Executable truth does not exist yet as a canonical runtime ledger or JSONL field. The repo does contain:

- raw paper signal PnL in `trade_journal` as `pnl_usdc`;
- raw execution context in `execution_log`, including size, price, quote staleness, lifecycle phase, and replay keys;
- entry depth/liquidity context in `trade_journal`, `decision_log`, and `market_snapshots`;
- research audits that manually classify current paper evidence as `DUST_ZONE` / `SIMULATION_ONLY`;
- design docs for future `signal_pnl`, `executable_pnl`, `dust_zone`, and MOS overlay fields.

This means Hermes can ingest the current state as **signal-mode evidence with executable blockers**, not as executable PnL evidence.

## Source Matrix

| Field | Source exists? | Path | Quality | Gap | Recommendation |
|---|---|---|---|---|---|
| `executable_pnl` | Partial | `docs/research/executable_truth/executable_reality_monitor.md`; `docs/research/executable_truth/dynamic_executable_expectancy_audit.md`; `docs/research/executable_truth/executable_overlay_phase_a.md`; future design in `docs/research/executable_truth/executable_reality_overlay_design.md` | Research/manual only. Existing audits consistently conclude `executable_pnl = N/A` because executable trade count is zero. | No canonical `executable_pnl` field in runtime JSONL; no generated executable ledger for latest dates; MOS is assumed, not authoritative. | Keep Phase64 `executable_pnl` blocked. Run a future read-only executable truth ledger audit that joins existing JSONL and emits a docs/report artifact only. |
| `signal_pnl` | Yes, as alias | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` field `payload.pnl_usdc`; defined in `docs/research/executable_truth/executable_overlay_phase_a.md`; summarized in `docs/research/executable_truth/dynamic_executable_expectancy_audit.md` | Good for paper signal/outcome research. Recent schema has `trade_result`, `entry_price`, `size`, `paper_trade_replay_key`, and `pnl_usdc` on close rows. | Runtime does not emit a field literally named `signal_pnl`; it must be aliased from `pnl_usdc`. | Hermes may use `pnl_usdc` as `signal_pnl` with label `SIGNAL_MODE / PAPER_SIMULATED`, never as executable PnL. |
| executable realism | Partial | `runtime/quant_data/execution_log/YYYY-MM-DD.jsonl`; `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl`; `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl`; `runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl`; `docs/research/executable_truth/minimum_executable_reality_audit.md` | Raw ingredients exist: size, price, quote staleness on some execution rows, top depth/liquidity on entry/decision/snapshot rows, replay key linkage. | No canonical fill-probability, queue, partial-fill, cancel realism, executable minimum pass/fail, or per-trade executable class. | Future audit should compute an offline executable-realism table: quote freshness, top-depth coverage, size-vs-MOS, dust class, and null executable PnL when blocked. |
| MOS / share threshold | Partial | `docs/research/executable_truth/minimum_executable_reality_audit.md`; `docs/research/executable_truth/executable_reality_monitor.md`; `docs/research/executable_truth/dynamic_executable_expectancy_audit.md`; `docs/research/growth_mode_feasibility_audit.md` | Consistent research assumption: `mos=5 shares`; docs also note a local `min_shares_per_order=1` guard observed by prior audit. | No authoritative Polymarket market metadata found locally for `min_order_size`, `minimum_order_size`, or `mos`; runtime JSONL does not emit MOS. | Keep MOS as `conservative_assumption`, not exchange truth. Future audit should verify authoritative market metadata before any executable claim. |
| dust zone | Partial | `docs/research/executable_truth/executable_reality_monitor.md`; `docs/research/executable_truth/dynamic_executable_expectancy_audit.md`; `docs/research/executable_truth/executable_overlay_phase_a.md`; `docs/research/session_edge/session_pressure_comparison_audit.md` | Strong research classification: prior audits found all compared paper trades are dust/simulation-only, including `0/178` eligible under `mos=1`, `mos=3`, and `mos=5`. | Runtime JSONL does not emit `dust_zone`, `dust_trade_flag`, or `executable_min_reject`. Latest-date dust status must be recomputed. | Hermes can ingest dust-zone status from existing audits as historical blocker evidence, but latest intake needs a fresh read-only overlay audit. |
| trade sample | Yes | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl`; `runtime/quant_data/execution_log/YYYY-MM-DD.jsonl`; `runtime/quant_data/path_truth/YYYY-MM-DD.jsonl`; `docs/research/path_truth/path_truth_multiday_coverage_monitor.md` | Good. Recent trade rows include `run_id`, `paper_trade_replay_key`, `asset`, `side`, `entry_price`, `size`, and `trade_result` on closes. | Historical schema varies; close lifecycle can be `UNKNOWN`; path truth lacks some join fields like `candidate_id` and `decision_id`. | Use `(run_id, paper_trade_replay_key)` where present. Record schema-compatible count and skipped legacy rows in any future audit. |
| session window | Partial | Derivable from JSONL timestamps; `runtime/quant_data/path_truth/YYYY-MM-DD.jsonl` has `payload.session_hour_utc`; session docs include `docs/research/session_edge/session_pressure_comparison_audit.md`, `docs/research/session_edge/session_regime_09h10h_persistence.md`, and `docs/research/session_edge/session_09h10h_structural_edge.md` | Good enough for UTC-hour buckets such as `02h`, `09h10h`, `16h`. | No canonical `session_window` field on trade close rows; named session labels are research docs, not runtime fields. | Future audit should derive `session_bucket` from close/open timestamp and attach research labels separately as evidence annotations. |
| price bucket | Partial | `payload.entry_price` in `trade_journal`; `payload.entry_price` in `path_truth`; price bucket tables in `docs/research/executable_truth/dynamic_executable_expectancy_audit.md` and `docs/research/session_edge/session_09h10h_truth_layer_audit.md` | Entry price is present and sufficient to derive buckets like `0.30-0.50` and `0.50-0.70`. | No runtime field named `price_bucket`; buckets are computed in research docs. | Derive offline from `entry_price`; do not treat price buckets as runtime policy. |
| lifecycle phase | Yes / partial | `trade_journal`, `execution_log`, `decision_log`, `market_snapshots`, `path_truth`; supporting audits `docs/research/session_edge/session_09h10h_truth_layer_audit.md` and `runtime/reports/position_maturity_observation_2026-05-18.md` | Entry/decision/execution/path lifecycle is available. Recent samples show `OPENING_SCAN`, `ACTIVE_INVENTORY_TRADING`, `PROFIT_MANAGEMENT`, and `FINAL_DERISK`. | Trade close lifecycle is often `UNKNOWN`; close-time lifecycle truth is weaker than entry/execution lifecycle truth. | Use entry/execution lifecycle for session-edge splits; mark close lifecycle as partial/unknown when not present. |
| regime | Partial | `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl`; `runtime/quant_data/research_log/YYYY-MM-DD.jsonl`; `runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl`; older observations in `docs/research/sessions/2026-05-17/research_cockpit_runtime_observation_2026-05-17.md` | Decision and research logs emit useful values such as `SIDEWAY`, `COMPRESSION`, `TREND_UP`, `TREND_DOWN`, and `UNKNOWN`. | Recent market snapshots sampled as `market_regime=UNKNOWN`; regime is not reliably joined to trade-close executable truth. | Use decision/research logs for regime evidence with coverage counts; do not rely on market snapshots alone. |

## Runtime Evidence Field Check

Recent JSONL sampling of 2026-05-24 through 2026-05-26 showed:

| Source | Useful present fields | Missing executable fields |
|---|---|---|
| `trade_journal` | `pnl_usdc`, `trade_result`, `entry_price`, `size`, `asset`, `ticker`, `side`, `lifecycle_phase`, `top_ask_depth`, `top_bid_depth`, `liquidity_depth_state`, `paper_trade_replay_key`, `run_id` | `signal_pnl`, `executable_pnl`, `dust_zone`, `mos`, `price_bucket`, canonical `session_window` |
| `execution_log` | `size`, `price`, `asset`, `side`, `lifecycle_phase`, `quote_stale_ms`, `paper_trade_replay_key`, `run_id`, `market_slug`, `condition_id` | `executable_pnl`, `executable_minimum_met`, queue/fill probability, partial-fill truth |
| `decision_log` | `asset`, `side`, `lifecycle_phase`, `market_regime`, depth/liquidity fields, replay key, run id | executable overlay labels and final trade PnL |
| `market_snapshots` | depth/liquidity, lifecycle, replay key, run id | market snapshot regime was `UNKNOWN` in sampled recent rows; no executable ledger fields |
| `path_truth` | `entry_price`, `asset`, `side`, `session_hour_utc`, `lifecycle_phase`, `run_id`, `condition_id` | `quote_age_ms`, `candidate_id`, `decision_id`, executable overlay labels |
| `research_log` | `market_regime`, lifecycle, depth/liquidity, run id | final executable PnL and trade-close outcome linkage |

Interpretation: runtime evidence contains enough raw data to **build an offline executable truth audit**, but it does not already contain a finished executable truth product.

## EXECUTABLE TRUTH STATUS

Does executable truth already exist?

```text
PARTIAL
```

Why not `YES`:

- `executable_pnl` is not emitted in runtime JSONL.
- Current executable audits are manual/docs-level and older than the newest runtime evidence.
- Existing audits classify current paper evidence as `DUST_ZONE` / `SIMULATION_ONLY`, not executable.
- MOS is an assumed conservative threshold, not confirmed exchange metadata.
- Queue, partial fill, cancel, and live order-rejection truth are absent.

Why not `NO`:

- `signal_pnl` exists as `pnl_usdc`.
- size, entry price, depth, quote staleness, lifecycle, session, side, asset, and replay keys exist.
- prior audits already establish the executable blocker pattern for recent samples.

Hermes Phase64 intake should therefore remain:

```text
executable_pnl = N/A / BLOCKED
runtime_truth = PARTIAL_RAW_EVIDENCE
session_edge_evidence = SIGNAL_MODE_ONLY
```

## Required Future Audit

Future audit required if Hermes needs an ingestible executable-truth table:

```text
Offline Executable Truth Ledger Audit
```

Read-only inputs:

- `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl`
- `runtime/quant_data/execution_log/YYYY-MM-DD.jsonl`
- `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl`
- `runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl`
- `runtime/quant_data/path_truth/YYYY-MM-DD.jsonl`
- existing session and executable overlay research docs

Required outputs:

- per-trade `signal_pnl = pnl_usdc`
- per-trade `executable_pnl = null` unless executable checks pass
- `dust_zone`
- `executable_min_reject`
- assumed or confirmed `mos`
- `session_bucket`
- `price_bucket`
- `lifecycle_phase_source`
- `regime_source`
- join coverage by `(run_id, paper_trade_replay_key)`
- clear `PARTIAL_RAW`, `SIGNAL_MODE`, or `EXECUTABLE_MODE` truth label

No replay is required for this audit. It should be a JSONL/report join over existing runtime evidence only.

## Three Future Options

OPTION 1 - SAFE EV PRESERVATION:

Keep Hermes Phase64 blocked on executable PnL. Ingest only the negative fact that current evidence is `SIGNAL_MODE / DUST_ZONE / SIMULATION_ONLY`.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:

Run a read-only offline executable truth ledger audit over the latest completed evidence dates to refresh dust/executable classifications without changing runtime.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:

Design a future canonical runtime/report field contract for `signal_pnl`, `executable_pnl`, `dust_zone`, `executable_minimum_met`, and authoritative MOS provenance.

Recommended next action: **OPTION 2**. Hermes needs a fresh source-of-truth artifact, but runtime and replay should remain untouched.

## Safety Confirmation

Runtime untouched: Yes

No replay: Yes

No bot: Yes

No commit: Yes

No push: Yes

Live behavior changed: No

Strategy/risk/execution changed: No

Tests: not run; docs-only read-only source audit.
