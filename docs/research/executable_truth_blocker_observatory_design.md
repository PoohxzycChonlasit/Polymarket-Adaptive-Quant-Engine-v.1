# Executable Truth Blocker Observatory Design

Date: 2026-05-26

Scope: read-only design document. No code changes. No runtime changes. No replay. No bot run. No live.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Role Routing

- Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`
- Supporting roles: `21_EXECUTION_MICROSTRUCTURE_AGENT.md`, `16_PAPER_EVALUATION_AGENT.md`
- Why selected: the task designs an observability layer for executable-truth blockers, especially minimum size, MOS, dust, path joins, fill truth, cancel truth, and partial-fill truth.
- Files inspected: `runtime/research_state/latest_research_state.md`, `MASTER_AGENT_ROUTER.md`, selected role docs, executable-truth research docs, and Hermes executable ingest rules.
- Files intentionally ignored: runtime code, strategy modules, risk modules, execution modules, live config, raw runtime logs, bot launch paths, and replay execution paths.

## Executive Verdict

```text
CURRENT_STATE: SIGNAL_MODE / EVIDENCE_FARMING
EXECUTABLE_TRUTH: NOT_REACHED
OBSERVATORY_PURPOSE: COUNT_BLOCKERS_NOT_APPROVE_PNL
EXECUTABLE_PNL: BLOCKED / N_A
```

The next useful layer is a blocker observatory that makes executable-truth blockers visible at trade, run, date, session, asset, side, lifecycle, and price-bucket levels.

This observatory should not approve executable PnL. It should answer:

- how many rows remain dust;
- which MOS assumptions reject each row;
- where path-truth joins fail;
- where fill truth is missing;
- where cancel truth is missing;
- where partial-fill truth is missing;
- whether blocker rates are improving enough to justify a future JSONL truth layer.

## Current Blockers

| Blocker | Current Status | What It Means | Observable Today? | Future Need |
|---|---|---|---|---|
| minimum size failures | active | paper rows remain below practical executable size | yes, from `shares`, `entry_price`, and assumed MOS | count per MOS scenario and per segment |
| MOS failures | active | MOS can reject claims, but cannot approve because MOS is not authoritative | yes, as assumption only | `mos_source`, `mos_assumption`, authoritative market metadata if available |
| dust zone | active | all sampled closes are simulation-only under MOS 1/3/5 | yes, derived offline | canonical `dust_zone` and dust subclass later |
| path join failures | active | path truth is useful but not directly joined by `(run_id, paper_trade_replay_key)` | yes, from join coverage | direct path-truth trade key |
| missing fill truth | active | paper fill is simulated, not exchange fill reality | partially visible as missing approval fields | fill source, fill size, fill ratio, fill truth label |
| missing cancel truth | active | cancel submit/ack, latency, and late-fill risk are not proven | no canonical coverage yet | cancel timestamps, cancel result, late-fill flag |
| missing partial-fill truth | active | top depth can reject weak rows, but cannot prove fill mechanics | no canonical coverage yet | requested size, filled size, fill ratio, partial-fill flag |

Current sampled facts from prior research:

- sampled closes: `77`
- MOS1 rejects: `77 / 77`
- MOS3 rejects: `77 / 77`
- MOS5 rejects: `77 / 77`
- direct trade/execution/decision/research joins: `77 / 77`
- direct path-truth joins by `(run_id, paper_trade_replay_key)`: `0 / 77`
- proxy path-truth joins: `60 / 77`

These counts are blocker evidence. They are not executable profitability evidence.

## Metrics

### Trade-Level Blocker Fields

The observatory should eventually produce one row per closed paper trade or ledger candidate.

| Metric | Type | Count / Aggregate | Source Class | Meaning |
|---|---|---|---|---|
| `signal_trade_count` | count | total rows with paper trade outcome | existing | signal evidence volume |
| `signal_pnl_sum` | sum | sum of `pnl_usdc` as `signal_pnl` | existing alias | paper signal PnL only |
| `shares` | value | min / median / mean / max | existing | size truth for MOS tests |
| `notional` | value | min / median / mean / max | derived | `entry_price * shares` |
| `mos_assumption` | value | counts by `1`, `3`, `5`, future authoritative MOS | future/derived | scenario used for minimum-size test |
| `dynamic_min_cost` | value | `entry_price * mos_assumption` | derived | minimum notional implied by MOS |
| `minimum_size_fail` | boolean | count and percent | derived | `shares < mos_assumption` |
| `mos_fail` | boolean | count and percent by MOS | derived | fails assumed or authoritative MOS |
| `dust_zone` | boolean | count and percent | derived | below practical executable threshold |
| `dust_subclass` | enum | MICRO_DUST / SUB_MOS / NEAR_MOS | derived | distance from executable size |
| `executable_minimum_met` | boolean | count and percent | derived | `shares >= mos and notional >= dynamic_min_cost` |
| `path_join_status` | enum | DIRECT / STRONG / WEAK / PROXY / BLOCKED | derived | path linkage reliability |
| `path_join_fail` | boolean | count and percent | derived | path truth not direct enough |
| `fill_truth_status` | enum | PRESENT / PAPER_SIMULATED / MISSING | future | whether fill truth can support execution reality |
| `cancel_truth_status` | enum | PRESENT / PAPER_SIMULATED / MISSING | future | whether cancel truth can support final derisk realism |
| `partial_fill_truth_status` | enum | PRESENT / PAPER_SIMULATED / MISSING | future | whether partial-fill risk is observable |
| `executable_blocker_primary` | enum | count and percent | derived | first blocker that prevents executable PnL |
| `executable_blockers_all` | list | blocker frequency | derived | all blockers on the row |
| `executable_pnl_status` | enum | BLOCKED_N_A unless approved later | derived | approval state, not PnL value |

### Aggregation Dimensions

Aggregate every blocker metric by:

- date
- run_id
- session_hour_utc
- asset: BTC / ETH
- side: YES / NO
- lifecycle_phase
- price_bucket
- trade_result: TP / SL / EXPIRY / UNKNOWN
- path coverage class: FULL_COVERAGE / FAST_CLOSE_PARTIAL / NO_PATH
- join confidence: DIRECT / STRONG / WEAK / PROXY / BLOCKED
- MOS scenario: 1 / 3 / 5 / authoritative when available

### Dashboard-Level Counts

The daily blocker observatory should be able to report:

| Count | Question Answered |
|---|---|
| `rows_total` | how much signal evidence exists? |
| `rows_signal_only` | how many rows are paper-signal-only? |
| `rows_dust_zone` | how many rows are simulation-only dust? |
| `rows_minimum_size_fail_mos1` | does anything clear the most permissive MOS scenario? |
| `rows_minimum_size_fail_mos3` | does anything clear a moderate MOS scenario? |
| `rows_minimum_size_fail_mos5` | does anything clear conservative MOS? |
| `rows_path_join_direct` | how many rows can be joined safely to path truth? |
| `rows_path_join_proxy` | how much evidence remains proxy-only? |
| `rows_missing_fill_truth` | how many rows still lack fill realism? |
| `rows_missing_cancel_truth` | how many rows still lack cancel realism? |
| `rows_missing_partial_fill_truth` | how many rows still lack partial-fill realism? |
| `rows_executable_candidate` | how many rows survive first-order blockers? |
| `rows_executable_pnl_approved` | should remain zero until full truth is present |

### Health Ratios

| Ratio | Formula | Read |
|---|---|---|
| `dust_zone_rate` | `rows_dust_zone / rows_total` | lower is better, but only if risk remains safe |
| `mos_clear_rate` | `rows_executable_minimum_met / rows_total` | first sign that paper sizing reached executable scale |
| `path_direct_join_rate` | `rows_path_join_direct / rows_total` | path truth lineage maturity |
| `fill_truth_coverage_rate` | `rows_fill_truth_present / rows_total` | fill realism maturity |
| `cancel_truth_coverage_rate` | `rows_cancel_truth_present / rows_total` | final derisk realism maturity |
| `partial_fill_truth_coverage_rate` | `rows_partial_fill_truth_present / rows_total` | queue/depth realism maturity |
| `executable_candidate_rate` | `rows_executable_candidate / rows_total` | frontier pressure toward executable truth |
| `executable_pnl_approval_rate` | `rows_executable_pnl_approved / rows_total` | must stay zero until approval contract exists |

## JSONL Candidates

This is a future field design only. No fields are implemented by this document.

### Candidate Event Type

Future event name:

```text
executable_truth_blocker_snapshot
```

Purpose:

- compact blocker summary per trade close or per offline ledger row;
- additive only;
- fail-soft when fields are missing;
- never used as order approval;
- never used to alter strategy/risk/execution.

### Candidate Destinations

| Destination | Use | Status |
|---|---|---|
| `runtime/quant_data/research_log/YYYY-MM-DD.jsonl` | research-only blocker snapshots | future candidate |
| `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | additive close-row blocker fields | future candidate, higher compatibility risk |
| `runtime/reports/executable_truth_blocker_observatory_*.json` | offline report artifact | safest next step |
| `docs/research/*.md` | daily human-readable summaries | available now as docs-only |

Recommended initial path:

```text
offline report first -> docs summary -> JSONL truth layer later
```

### Candidate Payload Shape

```json
{
  "event_type": "executable_truth_blocker_snapshot",
  "run_id": "2026...",
  "paper_trade_replay_key": "...",
  "candidate_id": "...",
  "decision_id": null,
  "asset": "BTC",
  "side": "YES",
  "session_hour_utc": 9,
  "lifecycle_phase": "OPENING_SCAN",
  "entry_price": 0.54,
  "shares": 0.09,
  "notional": 0.0486,
  "signal_pnl": -0.002,
  "mos_assumption": 5,
  "mos_source": "research_assumption",
  "dynamic_min_cost": 2.7,
  "minimum_size_fail": true,
  "mos_fail": true,
  "dust_zone": true,
  "dust_subclass": "MICRO_DUST",
  "executable_minimum_met": false,
  "path_join_status": "PROXY",
  "path_join_fail": true,
  "fill_truth_status": "PAPER_SIMULATED",
  "cancel_truth_status": "MISSING",
  "partial_fill_truth_status": "MISSING",
  "executable_blocker_primary": "MINIMUM_SIZE_FAIL",
  "executable_blockers_all": [
    "MINIMUM_SIZE_FAIL",
    "MOS_ASSUMPTION_NOT_AUTHORITATIVE",
    "PATH_JOIN_PROXY",
    "FILL_TRUTH_MISSING",
    "CANCEL_TRUTH_MISSING",
    "PARTIAL_FILL_TRUTH_MISSING"
  ],
  "executable_pnl": null,
  "executable_pnl_status": "BLOCKED_N_A",
  "hermes_ingest_status": "BLOCKER_EVIDENCE_ONLY"
}
```

### Blocker Enum Candidates

| Enum | Meaning |
|---|---|
| `MINIMUM_SIZE_FAIL` | shares or notional below MOS threshold |
| `MOS_ASSUMPTION_NOT_AUTHORITATIVE` | MOS is research assumption, not exchange-confirmed truth |
| `DUST_ZONE` | trade remains simulation-only at practical size |
| `PATH_JOIN_DIRECT_MISSING` | path truth lacks direct trade linkage |
| `PATH_JOIN_PROXY` | path truth can only be joined by proxy fields |
| `FILL_TRUTH_MISSING` | live/realistic fill truth absent |
| `CANCEL_TRUTH_MISSING` | cancel submit/ack/latency truth absent |
| `PARTIAL_FILL_TRUTH_MISSING` | partial-fill behavior absent |
| `QUOTE_FRESHNESS_MISSING` | quote age/staleness unavailable for approval |
| `DEPTH_SUPPORT_MISSING` | depth support cannot validate requested size |
| `SPREAD_COST_MISSING` | executable spread cost unavailable |
| `PAPER_SIMULATION_ONLY` | truth source is paper simulated |

### Fail-Soft Rules

- Missing fields must produce `UNKNOWN` or `MISSING`, not runtime errors.
- `executable_pnl` remains `null` unless every approval dependency exists.
- Assumed MOS can reject a row but cannot approve a row as executable.
- Paper fill truth must stay labeled `PAPER_SIMULATED`.
- Proxy path joins must not be upgraded to direct joins.
- The observatory is additive and backwards compatible.

## UI Candidates

Future runtime UI should show blocker observability as a compact operator panel, not as a trade approval surface.

### Header Strip Candidate

Add only after explicit UI scope:

```text
EXEC n/a | DUST 77/77 | MOS1 0 | PATH direct 0% | FILL missing
```

Meaning:

- `EXEC n/a`: executable PnL is blocked;
- `DUST 77/77`: current rows are dust-zone blocker evidence;
- `MOS1 0`: zero rows clear MOS1;
- `PATH direct 0%`: path join is not canonical;
- `FILL missing`: fill truth is not sufficient.

### Compact Panel Candidate

Panel title:

```text
Executable Truth Blockers
```

Rows:

| Row | Fields |
|---|---|
| Mode | `SIGNAL_MODE`, `EVIDENCE_FARMING`, `EXECUTABLE_TRUTH_NOT_REACHED` |
| Minimum Size | `MOS1 clear`, `MOS3 clear`, `MOS5 clear`, `dust rate` |
| Joins | `trade direct`, `path direct`, `path proxy`, `blocked` |
| Fill Truth | `fill`, `cancel`, `partial`, `quote age` |
| Candidate Pressure | `executable candidates`, `approved executable PnL` |

### Operator Value

The UI should help the operator answer:

- Are we still in signal-only mode?
- Did any trade clear even MOS1?
- Is dust decreasing?
- Is path truth directly joinable yet?
- Are fill/cancel/partial-fill blockers still total?
- Is Growth Mode still blocked?

### UI Red Lines

The UI must not:

- display paper PnL as executable PnL;
- imply Growth Mode readiness;
- use blocker fields to approve trades;
- hide `N/A` or blocked states behind green styling;
- merge paper simulated fill with live observed fill.

## Hermes Ingestion

Hermes should ingest blocker observatory output as cognition, not as executable PnL.

### Allowed Ingest

| Ingest Type | Label |
|---|---|
| paper signal outcomes | `SIGNAL_TRUTH` |
| minimum-size failures | `BLOCKER_EVIDENCE` |
| MOS rejections | `BLOCKER_EVIDENCE` |
| dust-zone counts | `DUST_ZONE` / `SIMULATION_ONLY` |
| path join failures | `PATH_TRUTH_BLOCKER` |
| missing fill truth | `EXECUTION_REALITY_BLOCKER` |
| missing cancel truth | `FINAL_DERISK_BLOCKER` |
| missing partial-fill truth | `FILL_REALISM_BLOCKER` |

### Blocked Ingest

Hermes must not ingest:

- `executable_pnl` as a value;
- `EXECUTABLE_PNL_APPROVED`;
- Growth Mode readiness;
- live profitability;
- assumed MOS as exchange-confirmed truth;
- proxy path truth as canonical continuity;
- paper simulated fill as live fill truth.

### Hermes Summary Contract

Every blocker observatory summary should carry:

```text
hermes_ingest_status = BLOCKER_EVIDENCE_ONLY
executable_pnl_status = BLOCKED_N_A
growth_readiness = BLOCKED
truth_level = SIGNAL_MODE / PAPER_SIMULATED
```

## Future Unlock Path

### Option 1 - Safe EV Preservation

Keep this as a docs/report-only blocker monitor. Continue daily evidence farming and refresh blocker counts without runtime JSONL changes.

Pros:

- lowest risk;
- keeps executable PnL blocked correctly;
- gives Hermes stable cognition.

Cons:

- blocker data remains offline/manual until a later report generator exists.

### Option 2 - Aggressive Information Discovery

Build a read-only offline report generator later that joins trade, execution, decision, research, and path truth evidence into an executable blocker ledger.

Pros:

- repeatable daily counts;
- faster detection of any non-dust candidate;
- still no runtime behavior change.

Cons:

- requires careful join-quality handling;
- can produce misleading confidence if proxy joins are not labeled loudly.

### Option 3 - Structural / Root-Cause Path

After path truth gates are met, design a canonical JSONL truth layer for blocker fields.

Pros:

- creates stable downstream observability;
- reduces manual joins;
- prepares future UI panels.

Cons:

- requires implementation scope, tests, and backward-compatibility review;
- still cannot approve executable PnL without fill/cancel/partial-fill truth and MOS authority.

Recommended next step:

```text
OPTION 1 now, OPTION 2 next.
```

Keep this design as the cognition/spec layer. The next safe actionable step, when requested, is an offline blocker ledger report design or read-only audit. JSONL/runtime wiring should wait for explicit scope and path-truth gate maturity.

## Unlock Criteria

Executable truth remains blocked until all of these are true:

1. At least some paper rows clear an explicitly labeled MOS scenario.
2. MOS source is authoritative or explicitly preserved as an assumption.
3. Path truth has direct or strong joins to the trade ledger.
4. Quote age and quote lineage are available for submit/fill.
5. Depth and spread support the intended size.
6. Fill truth distinguishes paper simulated from live observed.
7. Cancel truth captures submit, ack, latency, and late-fill risk.
8. Partial-fill truth captures requested size, filled size, fill ratio, and residual risk.
9. `executable_pnl_status` has an approval contract.
10. Hermes labels the row as executable only after every blocker is cleared.

Until then:

```text
executable_pnl = null
executable_pnl_status = BLOCKED_N_A
Hermes ingest = signal + dust + blocker + path evidence only
Growth Mode = BLOCKED
```

## What Not To Do

- Do not implement runtime JSONL fields from this document.
- Do not run replay.
- Do not run paper.
- Do not alter strategy, risk, sizing, stoploss, execution, or live config.
- Do not use assumed MOS to approve executable PnL.
- Do not treat paper simulated fill as live fill truth.
- Do not treat proxy path joins as canonical identity.
- Do not promote Growth Mode.

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Tests: not run; this is docs-only design work.

