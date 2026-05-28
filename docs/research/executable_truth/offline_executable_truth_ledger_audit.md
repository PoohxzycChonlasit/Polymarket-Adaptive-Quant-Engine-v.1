# Offline Executable Truth Ledger Audit v1

Date: 2026-05-26

Scope: docs-only, read-only audit/specification. No code. No runtime change. No replay run. No bot run. No live.

## 1. Executive Verdict

```text
OFFLINE_EXECUTABLE_TRUTH_LEDGER: CONSTRUCTIBLE_AS_AUDIT
EXECUTABLE_PNL_APPROVED: BLOCKED
EXECUTABLE_PNL: N/A
HERMES_INGEST_STATUS: SAFE_AS_SIGNAL_MODE_AND_BLOCKER_EVIDENCE
```

Existing evidence can support an **offline ledger concept** that separates:

1. `signal_pnl`
2. dust / simulation-only trades
3. executable minimum rejects
4. executable candidates, if any appear later
5. `executable_pnl = N/A / BLOCKED`

It cannot support approved executable PnL yet. Current paper evidence remains `SIGNAL_MODE / PAPER_SIMULATED`, and every sampled closed trade from 2026-05-24 through 2026-05-26 fails `mos=1`, `mos=3`, and `mos=5` minimum-share tests.

Latest sampled runtime evidence:

| Metric | Value |
|---|---:|
| sampled dates | 2026-05-24, 2026-05-25, 2026-05-26 |
| trade_open | 77 |
| trade_close | 77 |
| closes with `(run_id, paper_trade_replay_key)` | 77 / 77 |
| closes joinable to trade_open by preferred key | 77 / 77 |
| closes joinable to execution_log by preferred key | 77 / 77 |
| closes joinable to decision_log by preferred key | 77 / 77 |
| closes joinable to research_log by preferred key | 77 / 77 |
| closes directly joinable to path_truth by preferred key | 0 / 77 |
| closes proxy-joinable to path_truth by `(run_id, condition_id, asset, side)` | 60 / 77 |
| closes below `mos=1` | 77 / 77 |
| closes below `mos=3` | 77 / 77 |
| closes below `mos=5` | 77 / 77 |
| signal PnL in sample | `-$0.1045715` |

## 2. Source Files Inspected

Primary source doc:

- `docs/research/executable_truth/runtime_executable_truth_source_audit.md`

Executable evidence docs:

- `docs/research/executable_truth/dynamic_executable_expectancy_audit.md`
- `docs/research/executable_truth/minimum_executable_reality_audit.md`
- `docs/research/executable_truth/executable_reality_overlay_design.md`
- `docs/research/executable_truth/executable_overlay_phase_a.md`
- `docs/research/executable_truth/paper_sizing_audit.md`
- `docs/research/path_truth/path_truth_multiday_coverage_monitor.md`

Runtime JSONL sampled:

- `runtime/quant_data/trade_journal/2026-05-24.jsonl`
- `runtime/quant_data/trade_journal/2026-05-25.jsonl`
- `runtime/quant_data/trade_journal/2026-05-26.jsonl`
- `runtime/quant_data/execution_log/2026-05-24.jsonl`
- `runtime/quant_data/execution_log/2026-05-25.jsonl`
- `runtime/quant_data/execution_log/2026-05-26.jsonl`
- `runtime/quant_data/decision_log/2026-05-24.jsonl`
- `runtime/quant_data/decision_log/2026-05-25.jsonl`
- `runtime/quant_data/decision_log/2026-05-26.jsonl`
- `runtime/quant_data/market_snapshots/2026-05-24.jsonl`
- `runtime/quant_data/market_snapshots/2026-05-25.jsonl`
- `runtime/quant_data/market_snapshots/2026-05-26.jsonl`
- `runtime/quant_data/research_log/2026-05-24.jsonl`
- `runtime/quant_data/research_log/2026-05-25.jsonl`
- `runtime/quant_data/research_log/2026-05-26.jsonl`
- `runtime/quant_data/path_truth/2026-05-24.jsonl`
- `runtime/quant_data/path_truth/2026-05-25.jsonl`
- `runtime/quant_data/path_truth/2026-05-26.jsonl`

Role routing:

- Primary: `10_BACKTEST_REPLAY_AGENT.md`
- Supporting: `21_EXECUTION_MICROSTRUCTURE_AGENT.md`, `16_PAPER_EVALUATION_AGENT.md`, `11_OBSERVABILITY_INCIDENT_AGENT.md`, `07_TEST_CI_AGENT.md`

Files intentionally ignored:

- strategy modules
- risk modules
- stoploss code
- sizing code
- execution code
- live config
- bot launch paths
- replay execution paths

## 3. Join Key Reliability

Preferred join key:

```text
(run_id, paper_trade_replay_key)
```

Join reliability:

| Join Target | Reliability | Current Evidence | Notes |
|---|---|---:|---|
| `trade_close -> trade_open` | DIRECT | 77 / 77 | Safe for entry/exit, size, side, asset, price, PnL, and lifecycle reconstruction. |
| `trade_close -> execution_log` | DIRECT | 77 / 77 | Safe for execution event context and quote-stale evidence where emitted. |
| `trade_close -> decision_log` | DIRECT | 77 / 77 | Safe for decision context and regime fields where emitted. |
| `trade_close -> research_log` | DIRECT | 77 / 77 | Safe for research/regime context where emitted. |
| `trade_close -> market_snapshots` | BLOCKED by preferred key | 0 / 77 | Market snapshots have useful market state, but sampled direct preferred-key join did not match closes. |
| `trade_close -> path_truth` | BLOCKED by preferred key | 0 / 77 | Path truth currently lacks `paper_trade_replay_key` direct linkage in sampled rows. |
| `trade_close -> path_truth` proxy | PROXY | 60 / 77 | Possible by `(run_id, condition_id, asset, side)`, but not canonical enough for executable PnL approval. |

Join confidence labels:

| Label | Meaning | Current Use |
|---|---|---|
| DIRECT | `(run_id, paper_trade_replay_key)` links the same paper trade across producers. | trade journal, execution, decision, research joins |
| STRONG | Direct trade key absent, but canonical identity fields are sufficient and collision-resistant. | not established for path truth yet |
| WEAK | Contextual fields align, but one or more identity fields are missing. | possible path truth joins by run/condition/asset/side |
| PROXY | Time/window/asset/side context suggests relation but cannot prove per-trade identity. | path truth today |
| BLOCKED | Required identity is missing or ambiguous. | market snapshot direct close join, path truth direct close join |

Path truth join verdict:

```text
PATH_TRUTH_JOIN: PROXY_ONLY_FOR_CURRENT_LEDGER
```

Path truth is useful for path coverage, fast close, and checkpoint health. It should not be used as canonical executable PnL approval evidence until it carries a direct trade key or an equivalent canonical link.

Candidate and decision identifiers:

- `candidate_id`: present on sampled trade close/open rows, execution rows, decision rows, and research rows; absent from sampled path truth rows.
- `decision_id`: absent from sampled trade close/open rows; present in execution/decision/research rows; absent from sampled path truth rows.
- `candidate_trace_id`: present on sampled trade close/open rows and path truth rows.

Conclusion:

`candidate_id` and `decision_id` are **not required now** to construct a signal/dust ledger from trade and execution logs. They are required later for canonical candidate-to-path and decision-to-trade lineage.

## 4. Existing Field Coverage

Sample scope: 77 trade close rows across 2026-05-24 through 2026-05-26.

| Field | Coverage | Quality |
|---|---:|---|
| `run_id` | 77 / 77 | READY |
| `paper_trade_replay_key` | 77 / 77 | READY |
| `trade_id` | 0 / 77 | MISSING |
| `candidate_id` | 77 / 77 | READY for trade/execution, missing from path truth |
| `decision_id` | 0 / 77 on trade rows | PARTIAL via execution/decision/research logs |
| `candidate_trace_id` | 77 / 77 | READY on trade rows |
| `asset` | 77 / 77 | READY |
| `side` | 77 / 77 | READY |
| `market_slug` | 77 / 77 | READY |
| `condition_id` | 77 / 77 | READY |
| `token_id` | 77 / 77 | READY |
| `lifecycle_phase` | 77 / 77 | READY, but close-phase meaning needs care |
| `session_hour_utc` | 0 / 77 on trade rows | DERIVABLE from timestamps; present in path truth |
| `entry_ts` | 77 / 77 | READY, using trade_open or timestamp fields |
| `exit_ts` | 77 / 77 | READY, using trade_close timestamp fields |
| `entry_price` | 77 / 77 | READY |
| `exit_price` | 77 / 77 | READY |
| `size / shares` | 77 / 77 | READY |
| `pnl_usdc` | 77 / 77 | READY as `signal_pnl` alias |
| `trade_result` | 70 / 77 | PARTIAL; fallback can use `exit_reason` or PnL sign with caveat |
| `exit_reason` | 77 / 77 | READY |
| `quote_stale_ms / quote_age_ms` | 0 / 77 on trade rows | PARTIAL via execution_log; absent on trade close rows |
| `liquidity_state` | 77 / 77 | READY |
| `depth / depth_top` | 77 / 77 | READY on trade rows for entry depth context |
| `spread / spread_state` | 77 / 77 | READY as state/label, numeric spread quality varies |
| `price_bucket` | 0 / 77 as a stored field | DERIVABLE from `entry_price` |
| path truth checkpoints | 107 rows sampled | PARTIAL; proxy-only join to closes |

Current numeric sample:

| Metric | Value |
|---|---:|
| shares min | `0.020346` |
| shares mean | `0.092046` |
| shares max | `0.286708` |
| notional min | `$0.012615` |
| notional mean | `$0.048954` |
| notional max | `$0.145337` |
| entry price min | `0.37` |
| entry price mean | `0.542857` |
| entry price max | `0.63` |
| signal PnL sum | `-$0.1045715` |

Price buckets:

| Price Bucket | Trades |
|---|---:|
| `0.30-0.50` | 10 |
| `0.50-0.70` | 67 |

## 5. Executable Classification Rules

These are offline classifications only. They do not block runtime trades and do not change sizing.

### SIGNAL_ONLY

Required:

- paper trade exists
- `pnl_usdc` exists
- entry price and size exist
- outcome is present or recoverable by `trade_result`, `exit_reason`, or PnL sign

Meaning:

`pnl_usdc` can be copied to `signal_pnl`. This is paper-simulated directional evidence only.

### DUST_ZONE

Required:

- `shares < mos`

Meaning:

The trade is below practical executable size. It can still be useful signal evidence, but cannot support executable PnL.

### EXECUTABLE_MIN_REJECT

Triggers:

- `shares < mos`, or
- `notional < entry_price * mos`, or
- future authoritative minimum-order metadata says the order is below minimum

Meaning:

The trade fails the offline minimum-size gate. `executable_pnl` remains null.

### EXECUTABLE_CANDIDATE

Required:

- `shares >= mos`
- `notional >= entry_price * mos`
- entry and exit truth present
- quote freshness present
- top-depth evidence present
- spread or spread state present

Meaning:

The row can be studied as a possible executable candidate, but still does not get executable PnL approval until microstructure checks pass.

### EXECUTABLE_PNL_APPROVED

Required:

- executable minimum met
- quote freshness acceptable
- top-depth supports the requested size
- spread cost visible or bounded
- entry/exit outcome truth present
- join confidence DIRECT or STRONG
- no missing identity blocker
- no live/paper truth mislabel

Current status:

```text
EXECUTABLE_PNL_APPROVED: BLOCKED
```

### BLOCKED / N_A

Default when:

- minimum size fails,
- microstructure truth is missing,
- join confidence is WEAK/PROXY/BLOCKED,
- or MOS is not authoritative.

Current ledger output should use:

```text
executable_pnl = null
executable_pnl_status = BLOCKED_MINIMUM_SIZE
```

or, where identity is incomplete:

```text
executable_pnl_status = BLOCKED_JOIN_CONFIDENCE
```

## 6. Proposed Offline Ledger Schema

Identity columns:

| Column | Source / Rule |
|---|---|
| `run_id` | trade journal preferred |
| `paper_trade_replay_key` | trade journal preferred |
| `trade_id` | null today unless producer provides it |
| `candidate_id` | trade/execution/decision when present |
| `decision_id` | execution/decision when present |
| `asset` | trade journal |
| `side` | trade journal normalized to YES/NO |
| `market_slug` | trade journal or execution |
| `condition_id` | trade journal or execution |
| `token_id` | trade journal or execution |

Timing columns:

| Column | Source / Rule |
|---|---|
| `entry_ts` | trade_open timestamp or order/fill timestamp |
| `exit_ts` | trade_close timestamp |
| `hold_seconds` | existing field if present, otherwise `exit_ts - entry_ts` |
| `session_hour_utc` | derive from `entry_ts`; path truth can provide supporting field |
| `lifecycle_phase` | prefer trade_open/execution entry lifecycle |
| `price_bucket` | derive from `entry_price` |

Signal truth columns:

| Column | Source / Rule |
|---|---|
| `entry_price` | trade journal |
| `exit_price` | trade journal |
| `shares` | `size` / shares field |
| `notional` | `entry_price * shares` |
| `pnl_usdc` | trade close |
| `trade_result` | trade close when present; else recover from exit reason or PnL sign with caveat |
| `exit_reason` | trade close |
| `signal_pnl` | alias of `pnl_usdc` |

Executable truth columns:

| Column | Source / Rule |
|---|---|
| `mos_assumption` | `1`, `3`, or `5`; source must be `conservative_assumption` until exchange metadata exists |
| `dynamic_min_cost` | `entry_price * mos_assumption` |
| `dust_zone` | `shares < mos_assumption` |
| `executable_minimum_met` | `shares >= mos_assumption and notional >= dynamic_min_cost` |
| `executable_classification` | `SIGNAL_ONLY`, `DUST_ZONE`, `EXECUTABLE_MIN_REJECT`, `EXECUTABLE_CANDIDATE`, `EXECUTABLE_PNL_APPROVED`, `BLOCKED_N_A` |
| `executable_pnl` | null unless `EXECUTABLE_PNL_APPROVED` |
| `executable_pnl_status` | `N_A_BLOCKED`, `BLOCKED_MINIMUM_SIZE`, `BLOCKED_JOIN_CONFIDENCE`, `APPROVED` |

Microstructure columns:

| Column | Source / Rule |
|---|---|
| `quote_age_ms` / `quote_stale_ms` | execution log where joinable |
| `spread` | numeric if present |
| `spread_state` | decision/trade/research state labels |
| `liquidity_state` | trade/decision/research |
| `depth_top` | top ask/bid or best ask/bid size |
| `book_state` | executable book state if present, otherwise derived label |

Path truth columns:

| Column | Source / Rule |
|---|---|
| `has_path_truth` | true only for DIRECT/STRONG path join; proxy separately labeled |
| `checkpoint_count` | count of linked checkpoints |
| `has_15s` | path checkpoint |
| `has_30s` | path checkpoint |
| `has_45s` | path checkpoint |
| `has_60s` | path checkpoint |
| `has_event_end` | terminal path event |
| `fast_close` | event_end without full checkpoint sequence |
| `full_coverage` | 15s, 30s, 45s, 60s, and event_end present |

Reliability columns:

| Column | Source / Rule |
|---|---|
| `join_confidence` | DIRECT / STRONG / WEAK / PROXY / BLOCKED |
| `missing_fields` | list of absent required fields |
| `caveats` | MOS assumption, proxy path join, missing quote age, missing spread, etc. |
| `hermes_ingest_status` | `SAFE_SIGNAL_ONLY`, `SAFE_BLOCKER_ONLY`, `BLOCK_EXECUTABLE_PNL`, `DO_NOT_INGEST` |

## 7. MOS / Dynamic Minimum Cost Logic

MOS assumptions:

```text
mos = 1 share
mos = 3 shares
mos = 5 shares
```

These are research assumptions only. The repo docs repeatedly state that authoritative Polymarket exchange metadata for `min_order_size`, `minimum_order_size`, or `mos` is not currently present in local evidence.

Per-trade formula:

```text
dynamic_min_cost = entry_price * mos
notional = entry_price * shares
executable_minimum_met = shares >= mos and notional >= dynamic_min_cost
```

Sample result across 77 recent closes:

| MOS | Minimum Met | Minimum Reject | Read |
|---:|---:|---:|---|
| 1 share | 0 | 77 | all dust |
| 3 shares | 0 | 77 | all dust |
| 5 shares | 0 | 77 | all dust |

Because all sampled trades are below `mos=1`, they are automatically below `mos=3` and `mos=5`.

Depth and quote freshness:

- Depth exists on trade/decision evidence, but depth cannot rescue a trade that fails minimum shares.
- Quote freshness exists in execution evidence for joinable rows, but quote freshness also cannot rescue a trade that fails minimum shares.
- A future `EXECUTABLE_CANDIDATE` must pass minimum size first, then depth and quote checks.

## 8. Signal vs Executable Truth

### Can current runtime evidence support `signal_pnl`?

```text
YES
```

`signal_pnl` can be safely defined offline as:

```text
signal_pnl = pnl_usdc
```

This must be labeled:

```text
SIGNAL_MODE
PAPER_SIMULATED
NOT_EXECUTABLE_PNL
```

### Can current runtime evidence support dust-zone classification?

```text
YES
```

Entry price and size are present on all sampled close/open pairs. The sample is below every MOS threshold.

### Can current runtime evidence support `executable_minimum_met`?

```text
YES, AS A RESEARCH ASSUMPTION
```

Under `mos=1`, `mos=3`, and `mos=5`, all sampled rows are minimum rejects. This is safe as blocker evidence because it does not promote anything.

### Can current runtime evidence support `EXECUTABLE_CANDIDATE`?

```text
CONDITIONALLY, BUT CURRENT SAMPLE HAS ZERO CANDIDATES
```

The schema can represent executable candidates later if trades clear minimum size. No sampled row does.

### Can current runtime evidence support `EXECUTABLE_PNL_APPROVED`?

```text
NO
```

Blocking fields and conditions:

- no sampled trade meets `mos=1`, `mos=3`, or `mos=5`
- no authoritative MOS metadata
- path truth direct join is missing
- market snapshot direct close join is missing
- quote age is not present on trade close rows
- spread cost is not yet consistently numeric and costed
- queue and partial-fill truth are absent
- live order acceptance, fill, cancel, and reconciliation truth are absent

## 9. Hermes Ingest Safety

Hermes can ingest this safely if it uses these labels:

| Evidence | Hermes Label |
|---|---|
| `pnl_usdc` | `signal_pnl` |
| paper trade PnL | `PAPER_SIMULATED` |
| all current sampled rows | `SIGNAL_ONLY` |
| all current sampled rows under MOS 1/3/5 | `DUST_ZONE` and `EXECUTABLE_MIN_REJECT` |
| executable PnL | `N_A_BLOCKED` |
| executable edge | `NOT_ESTABLISHED` |
| runtime truth | `PARTIAL_RAW_EVIDENCE` |
| path truth join | `PROXY_ONLY` unless direct key is added |

Hermes must not ingest:

- signal PnL as executable PnL
- dust PnL as live-ready PnL
- proxy path truth as approved executable truth
- assumed MOS as exchange-confirmed MOS
- any current row as `EXECUTABLE_PNL_APPROVED`

Answers to required questions:

| Question | Answer |
|---|---|
| Can current runtime evidence support executable_pnl? | No. It supports `executable_pnl = null / blocked`. |
| Can current runtime evidence support signal_pnl? | Yes, via `pnl_usdc`. |
| Can current runtime evidence support dust_zone classification? | Yes. |
| Can current runtime evidence support executable_minimum_met? | Yes as offline assumed-MOS blocker logic. |
| Can current runtime evidence support executable_candidate? | Schema can, but current sampled rows have zero candidates. |
| What blocks `EXECUTABLE_PNL_APPROVED`? | Minimum size failure, assumed MOS, missing direct path join, missing live fill/cancel truth, incomplete quote/spread/depth costing. |
| Is `(run_id, paper_trade_replay_key)` enough? | Enough for trade/execution/decision/research ledger construction, not enough for path truth today because path truth lacks the key. |
| Are `candidate_id` / `decision_id` required now or later? | Later for canonical candidate/path lineage; not required now for signal/dust ledger. |
| Can Hermes ingest this safely? | Yes, as signal-only and blocker evidence. |
| What should Hermes label as blocked? | `executable_pnl`, executable edge, live readiness, and any current dust PnL promotion. |
| What should be the next safe step? | Create a docs/report-only ledger artifact from existing JSONL, or first freeze a formal ledger field contract. |

## 10. Blockers

Hard blockers for executable PnL approval:

1. No sampled trade clears `mos=1`, `mos=3`, or `mos=5`.
2. MOS remains an assumption, not exchange-confirmed metadata.
3. Path truth does not directly join on `(run_id, paper_trade_replay_key)`.
4. Market snapshots do not directly join to closes by the preferred key in the sampled evidence.
5. Quote age is not on trade close rows and must be joined from execution logs.
6. Numeric spread cost is not consistently ready for executable PnL adjustment.
7. Partial fill, queue, live order reject, cancel latency, and reconciliation truth are absent.
8. Current path-truth gate remains below implementation readiness: Stage A 2 / 3, Stage B 2 / 7.

Soft blockers / caveats:

- `trade_result` is present on 70 / 77 sampled closes; 7 rows need fallback classification.
- `session_hour_utc` is not stored on trade close rows, but can be derived from timestamps.
- `price_bucket` is not stored, but can be derived from entry price.
- close lifecycle phase should be treated carefully; entry/execution lifecycle is safer for session-edge studies.

## 11. Next Safe Step

Recommended:

```text
OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY
```

Create a future read-only, docs/report-only ledger artifact that computes the proposed columns from existing JSONL and writes a research report. Do not wire it into runtime. Do not run replay. Do not promote Growth Mode.

Three future options:

1. OPTION 1 - SAFE EV PRESERVATION: keep Hermes blocked and use only current docs as blocker evidence.
2. OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY: generate a read-only ledger report from existing JSONL, preserving all blocker labels.
3. OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH: freeze a formal ledger field contract before any tool or runtime observability implementation.

The best next move is Option 2 only if scoped as read-only report generation. If implementation is not desired, Option 3 should come first as a pure contract freeze.

## 12. What Not To Do

Do not:

- change code
- implement the ledger in runtime
- run replay
- run the bot
- change runtime
- change strategy
- change risk
- change stoploss
- change sizing
- change execution
- change live config
- wire offline output into runtime
- claim executable profitability
- claim live readiness
- promote Growth Mode
- treat assumed MOS as exchange truth
- treat `signal_pnl` as `executable_pnl`
- treat path-truth proxy joins as canonical execution truth

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Tests: not run; docs-only/read-only audit. No markdown/link test was required.
