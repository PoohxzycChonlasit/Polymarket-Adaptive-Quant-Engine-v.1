# Research Cockpit Mounting Spec

Date: 2026-05-25

Scope: read-only / design-only mounting specification for existing runtime UI surfaces.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Inputs

- `docs/research/runtime_ui_observability_gap_audit.md`
- `utils/display.py`
- `main.py`
- `polymarket/trader.py`
- `docs/research/path_truth_gate_revision.md`
- `docs/research/path_truth_multiday_coverage_monitor.md`

## Role Routing

- Primary role: `02_CODE_ARCHITECT_AGENT.md`
- Supporting role: `11_OBSERVABILITY_INCIDENT_AGENT.md`
- Why selected: this is a UI mounting/interface design task, with observability safety constraints.
- Files allowed to inspect: display layout code, runtime display wiring, current UI gap audit, path-truth gate docs.
- Files intentionally ignored: strategy, risk, order placement, wallet/live config, replay execution, paper runtime.

## Current Location

The existing Research Cockpit lives in `utils/display.py` inside `PolymarketRealtimeDisplay`.

Relevant surfaces:

| Surface | Purpose |
|---|---|
| `_research_obs` | in-memory display-only research dictionary |
| `update_research_obs(**kwargs)` | fail-soft setter for precomputed research fields |
| `_quant_research_panel(spec)` | Rich panel renderer titled `Research Cockpit` |
| `_markets` | per-ticker live display state used by the cockpit for regime/liquidity fields |
| `_observability_health` | JSONL / data quality display state used by the cockpit |

The existing cockpit renderer has seven sections:

1. Regime
2. Lifecycle
3. Semantic C / S3
4. Economic vs Classification
5. Research Health
6. Anomalies
7. Runtime

It is explicitly designed to degrade gracefully:

```text
missing fields show n/a or --
no JSONL reads
no disk I/O
caller populates via update_research_obs(**kwargs)
```

## Why It Is Dormant

The Research Cockpit is dormant because the active runtime layout never mounts `_quant_research_panel()`.

The active layout is `PolymarketRealtimeDisplay._render()`.

Current active mount points:

| Mode | Active panels |
|---|---|
| compact | header, portfolio, risk, market table, recent decisions, decision diagnostics, execution reality |
| standard | header, system, portfolio, risk, BTC market, ETH market, recent decisions, decision diagnostics, execution reality |
| wide/fullscreen | header, system, portfolio, risk, BTC market, ETH market, recent decisions, quote age, decision diagnostics, execution reality, rolling logs |

No branch in `_render()` calls `_quant_research_panel(spec)`.

The cockpit is also stale relative to the current Path Truth phase. Its renderer focuses on older S3/OOS and general research health fields, while the current operator need is:

- path truth gates
- fast-close distribution
- session intelligence
- BTC / NO research labels
- active evidence-farming phase

So the safest mounting plan is staged. Do not mount the full old cockpit as the first change.

## Active Layout Function To Mount Through

All future mounting should go through:

```text
PolymarketRealtimeDisplay._render()
```

Stage 1 also needs:

```text
PolymarketRealtimeDisplay._header(spec)
```

Rationale:

- `_render()` owns active mode branching.
- `_header()` is always visible across compact, standard, wide, and fullscreen.
- Render methods already consume in-memory state only.
- Existing update methods already follow the display-only pattern.

Do not mount by reading docs, JSONL, or reports inside `_render()` or panel methods.

## Data Already Available

### Header / Runtime State

| Field | Current source |
|---|---|
| run id | `_run_id`, `update_run_id()` |
| paper/live mode | `paper_trading` |
| data status | `_data_status_tag()` |
| readiness | `_execution_readiness_label()` |
| Phase6 | `_phase6_label()` from `_execution_reality` |
| S3 | `_s3_label()` from `_execution_reality` |
| JSONL status | `_footer_jsonl_compact_tag()` |
| git cleanliness | `_execution_reality["git_clean_state"]` |

### Market / Candidate State

| Field group | Current source |
|---|---|
| BTC / ETH prices | `_markets[ticker]` |
| YES / NO bid/ask/mid | `_markets[ticker]` |
| spread | `_markets[ticker]["spread"]` |
| model probabilities | `p_yes`, `p_no`, `model_p_yes`, `model_p_no` |
| EV / min EV | `ev`, `min_ev` |
| confidence | `confidence` |
| decision / skip reason | `decision`, `skip_reason` |
| liquidity state | `liquidity_state`, depth fields |
| lifecycle phase | `lifecycle_phase` |
| executable book/spread state | `executable_book_state`, `executable_spread_state` |
| timing milestones | token-ready, nonzero, tradable, latency fields |
| replay identifiers | `replay_chain_id`, `lifecycle_instance_id`, `lineage_confidence` |

### Existing Research / Evidence State

| Field group | Current source |
|---|---|
| probe counters | `_research_obs` via `update_research_obs()` |
| zero-size and cycle-selection counts | `trader.dashboard_probe_counts()` |
| S1/S2/S3 labels | `_research_obs`, `_execution_reality` |
| data quality / continuity | `_research_obs`, `_observability_health` |
| anomaly notes | `_research_obs` |
| paired/BTC/ETH/TP/SL counts | `_execution_reality` |
| win/loss counts | `_execution_reality` |
| 60s+ count | `_execution_reality` |
| quote-age buckets | `_quote_age` |
| session summary | `_session_summary` |

## Missing Fields

These are not currently available in display state as operator-ready fields:

| Missing field | Needed for |
|---|---|
| `research_phase` | header strip: `PATH_TRUTH / EVIDENCE_FARMING` |
| `path_truth_gate` | `INSUFFICIENT_DATES`, `EARLY_RESEARCH_GATE`, `IMPLEMENTATION_GATE`, `COVERAGE_REGRESSED` |
| `stage_a_completed_dates` / `stage_a_target_dates` | `1/3` gate display |
| `stage_b_completed_dates` / `stage_b_target_dates` | `1/7` gate display |
| `path_truth_trade_count` | Path Truth panel |
| `path_truth_full_coverage_count` | Path Truth panel |
| `path_truth_fast_close_count` | Path Truth panel |
| `path_truth_bucket_0_15` | fast-close distribution |
| `path_truth_bucket_15_30` | fast-close distribution |
| `path_truth_bucket_60_plus` | survival distribution |
| `path_truth_event_end_count` | terminal path write health |
| `path_truth_parse_error_count` | writer/data quality |
| `path_truth_duplicate_key_count` | writer/data quality |
| `quote_age_ms_missing_pct` | field gap visibility |
| `candidate_id_missing_pct` | field gap visibility |
| `decision_id_missing_pct` | field gap visibility |
| `current_utc_session_bucket` | Session Intelligence |
| `session_research_label` | `02h_HOSTILE`, `09h10h_EDGE`, `NEUTRAL_OR_UNKNOWN` |
| `btc_research_label` | `BTC_HOSTILE_CANDIDATE`, `BTC_09H10H_RECOVERY_CANDIDATE`, etc. |
| `no_research_label` | `NO_SESSION_DEPENDENT`, `02h_NO_HOSTILE`, etc. |
| `research_confidence_label` | sample/date confidence |
| `research_sample_hint` | compact context like `02h 0/12`, `BTC 0/10`, `NO path 2/13` |

Important boundary: missing fields should be injected as display summaries only. They must not be recomputed from raw JSONL inside the render loop.

## Mounting Principles

1. Mount small research surfaces before mounting the full cockpit.
2. Keep all research state display-only.
3. Feed panels from precomputed in-memory summaries.
4. Never read JSONL, docs, reports, or logs inside `_render()` or panel renderers.
5. Treat all labels as operator context, not policy.
6. Use `n/a`, `--`, or `UNKNOWN` when data is unavailable.
7. Preserve compact layout stability.
8. Do not remove paper/live safety language from header or portfolio.

## Stage 1 - Header Research Strip Only

Goal: make the current research phase and gates visible everywhere without adding a panel.

Mount point:

```text
PolymarketRealtimeDisplay._header(spec)
```

Needed display state:

| Field | Fallback |
|---|---|
| `research_phase` | `PATH_TRUTH` or `research n/a` |
| `path_truth_gate` | `UNKNOWN` |
| `stage_a_completed_dates` / `stage_a_target_dates` | `-/3` |
| `stage_b_completed_dates` / `stage_b_target_dates` | `-/7` |
| `current_utc_session_bucket` | computed UTC hour or `--` |
| `session_research_label` | `UNKNOWN` |

Example header strip:

```text
PHASE PATH_TRUTH | GATE INSUFF 1/3A 1/7B | UTC 02h HOSTILE
```

Recommended implementation shape later:

- add a small `_research_context` or extend `_research_obs` with the fields above
- add a `_research_header_label()` helper
- append the compact label to line 2 of `_header()`
- keep line length clipped with existing `_clip()`

Why Stage 1 first:

- lowest layout risk
- no panel allocation
- always visible in compact mode
- immediate operator value

Performance risk: negligible if data is already in memory.

Fallback behavior:

```text
PHASE research n/a | GATE UNKNOWN | UTC --
```

## Stage 2 - Path Truth Compact Panel

Goal: show evidence-farming quality without opening research docs.

Mount point:

```text
PolymarketRealtimeDisplay._render()
```

Future panel function:

```text
_path_truth_panel(spec)
```

Recommended active layout:

| Mode | Proposed mount |
|---|---|
| compact | bottom row, replace `execution_reality` only during `PATH_TRUTH` phase or combine into a compact `Evidence` panel |
| standard | bottom row, replace `execution_reality` with Path Truth while header keeps readiness/S3 |
| wide/fullscreen | bottom row, replace `quote_age` if quote-age data is unavailable; otherwise use an `Operator Intel` combined panel |

Compact panel content should be no more than three rows:

```text
Path tr=46 full=3 fast=43 end=46
Buckets 0-15=high 15-30=high 60+=3
Gate 1/3A 1/7B | dup=0 parse=0
```

Required display fields:

- `path_truth_trade_count`
- `path_truth_full_coverage_count`
- `path_truth_fast_close_count`
- `path_truth_bucket_0_15`
- `path_truth_bucket_15_30`
- `path_truth_bucket_60_plus`
- `path_truth_event_end_count`
- `path_truth_parse_error_count`
- `path_truth_duplicate_key_count`
- Stage A / Stage B progress fields from Stage 1

Fields missing today:

- all path-truth panel summary fields

Performance risk:

- low if values are precomputed and injected at low frequency
- high if the panel scans `runtime/quant_data/path_truth/*.jsonl` every render

Fallback behavior:

```text
Path truth: evidence unavailable
Gate UNKNOWN | dup n/a | parse n/a
```

Design note:

Stage 2 should not wire `quote_age_ms`, `candidate_id`, or `decision_id`. It only displays the known missing-field rates if a summary is available.

## Stage 3 - Session Intelligence Panel

Goal: make `02h`, `09h10h`, BTC, and NO research context visible as operator memory.

Mount point:

```text
PolymarketRealtimeDisplay._render()
```

Future panel function:

```text
_session_intelligence_panel(spec)
```

Recommended active layout:

| Mode | Proposed mount |
|---|---|
| compact | bottom row, preferably as a combined `Operator Intel` panel with Path Truth |
| standard | bottom row, replace or combine with `candidate_obs` only if candidate row remains available elsewhere |
| wide/fullscreen | bottom row or optional full Research Cockpit view |

Compact panel content:

```text
UTC 02h | HOSTILE_SESSION_CANDIDATE | conf LOW
BTC 0/10 HOSTILE | NO 2/13 SESSION_DEP
09h10h EDGE watch | no enforcement
```

Required display fields:

- `current_utc_session_bucket`
- `session_research_label`
- `btc_research_label`
- `no_research_label`
- `research_confidence_label`
- `research_sample_hint`
- optional `session_edge_watch`
- optional `hostile_session_warning`

Fields missing today:

- all operator-ready session research labels
- no in-memory provider currently normalizes research docs into console labels

Performance risk:

- low if labels are static/precomputed for the run
- medium if labels are refreshed from a compact summary file at a low cadence
- high if labels are derived from raw historical JSONL inside runtime UI updates

Fallback behavior:

```text
Session intel unavailable | no enforcement
```

Safety label:

Every session intelligence panel should include or imply:

```text
research only / no enforcement
```

## Full Research Cockpit Mount

The existing `_quant_research_panel()` should not be mounted as Stage 1.

Recommended later mount:

| Mode | Recommendation |
|---|---|
| compact | do not mount full cockpit |
| standard | do not mount full cockpit by default |
| wide | optional alternate bottom panel only after Stage 1-3 fields exist |
| fullscreen | acceptable as an advanced panel if it does not hide safety/risk surfaces |

Why not first:

- current cockpit content is older than Path Truth phase
- it can crowd compact/standard layouts
- most current path-truth/session fields are missing from `_research_obs`
- old S3/OOS fields may distract from current evidence-farming gates

## Compact Mode Feasibility

Compact mode is feasible for Stage 1 and partially feasible for Stage 2/3.

Feasible:

- header research strip
- one compact Path Truth or Operator Intel panel
- one-line candidate research context

Not feasible:

- full Research Cockpit
- full 02h / 09h10h / BTC / NO matrix
- path truth date tables
- detailed quote-age distributions by asset/outcome

Recommended compact hierarchy:

```text
Header:
  MODE | RUN | PHASE | GATE | SESSION

Top:
  Portfolio | Risk

Center:
  Market Scan

Bottom:
  Recent Decisions | Operator Intel | Candidate Diagnostics
```

`Operator Intel` can combine Stage 2 and Stage 3 in three rows:

```text
Sess 02h HOSTILE | BTC HOSTILE | NO SESSION_DEP
Path tr=46 full=3 fast=43 | gate 1/3A
Research only | no enforcement
```

## Performance Risks

| Risk | Severity | Mitigation |
|---|---|---|
| JSONL reads inside `_render()` | High | never do this; inject summaries |
| large docs/report parsing during UI refresh | High | precompute outside render path |
| too many panels in compact mode | Medium | use header strip and one Operator Intel panel |
| stale research labels | Medium | include `updated_at` or data age in state later |
| old cockpit content confusing current phase | Medium | Stage 1-3 path-truth labels before full mount |
| missing fields causing render errors | Low if using existing patterns | keep `n/a`, `--`, `_safe_text`, `_clip` style |

The current display refreshes through Rich `Live` at `low`, `medium`, or `high` FPS. Any file read or expensive aggregation inside render would be multiplied by refresh rate and can degrade the operator console.

## Fallback Behavior

All future panels should fail soft:

| Missing data | UI fallback |
|---|---|
| no research context | `research n/a` |
| no gate state | `GATE UNKNOWN` |
| no path truth summary | `Path truth unavailable` |
| no session label | `SESSION UNKNOWN` |
| no BTC / NO label | `BTC n/a`, `NO n/a` |
| no sample confidence | `conf n/a` |
| parse/duplicate counts missing | `parse n/a`, `dup n/a` |

Fallback must not:

- block trading
- change a decision
- change risk state
- alter execution
- imply live readiness
- promote S3

## Proposed Field Contract

Future display-only state can be carried in `_research_obs` or a new `_operator_research` dict.

Recommended names:

```text
research_phase
research_updated_at
path_truth_gate
stage_a_completed_dates
stage_a_target_dates
stage_b_completed_dates
stage_b_target_dates
path_truth_trade_count
path_truth_full_coverage_count
path_truth_fast_close_count
path_truth_bucket_0_15
path_truth_bucket_15_30
path_truth_bucket_60_plus
path_truth_event_end_count
path_truth_parse_error_count
path_truth_duplicate_key_count
current_utc_session_bucket
session_research_label
btc_research_label
no_research_label
research_confidence_label
research_sample_hint
research_enforcement_enabled
```

`research_enforcement_enabled` should always display as false/off for this phase.

## Stage Recommendation

### Stage 1

Implement header research strip only.

Best mount:

```text
_header(spec)
```

Status: safest first step.

### Stage 2

Implement Path Truth compact panel or combined Operator Intel panel.

Best mount:

```text
_render() bottom row
```

Status: useful during evidence farming, but requires a precomputed path-truth summary provider.

### Stage 3

Implement Session Intelligence panel.

Best mount:

```text
_render() bottom row, combined with Path Truth in compact mode
```

Status: high operator value, but labels must be explicitly research-only and sample-size aware.

## Three Future Options

### Option 1 - Safe EV Preservation

Mount only the Stage 1 header research strip.

Likely outcome: immediate phase/gate visibility with minimal layout and performance risk.

Hidden risk: path-truth detail remains outside the operator console.

Recommended action: choose this first when implementation is later scoped.

### Option 2 - Aggressive Information Discovery

Mount Stage 1 plus a compact `Operator Intel` panel that combines Path Truth and Session Intelligence.

Likely outcome: best evidence-farming console value.

Hidden risk: compact mode can become dense, and stale labels could mislead unless timestamped.

Recommended action: do this after Stage 1 if a precomputed summary path exists.

### Option 3 - Structural / Root-Cause Path

Create a formal research-summary provider that feeds UI state at low frequency, then mount full Research Cockpit in wide/fullscreen only.

Likely outcome: clean architecture for long-term research console evolution.

Hidden risk: larger scope and more moving parts before the operator gets a visible improvement.

Recommended action: reserve this for after Stage 1-3 prove useful.

## Final Design Verdict

Do not mount the full existing Research Cockpit immediately.

The safe mounting sequence is:

1. Header research strip only.
2. Path Truth compact panel.
3. Session Intelligence panel.

The active layout function for Stage 2 and Stage 3 is `_render()`. Stage 1 belongs in `_header()`.

All data should be injected as precomputed display summaries through a fail-soft display update path. No panel should read JSONL, reports, docs, or logs during render.

## Tests Required Before Future Implementation

No tests were run for this design-only task.

Future implementation should add or update focused terminal display tests for:

- header strip renders with missing data
- header strip clips long labels
- compact mode still fits
- Path Truth panel renders missing data without exceptions
- Path Truth panel renders counts and gate progress
- Session Intelligence panel renders research-only labels
- full Research Cockpit remains unmounted unless explicitly enabled

## Final Status

Files created:

- `docs/research/research_cockpit_mounting_spec.md`

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No
