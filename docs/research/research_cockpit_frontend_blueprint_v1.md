# Research Cockpit v2 Frontend Blueprint

Document type: frontend architecture blueprint.

Date: 2026-05-22

Scope: design only.

Runtime behavior changed: No.

Live behavior changed: No.

Code changed: No.

Paper launch: No.

Replay run: No.

S3 promotion: No.

---

## Source Documents Inspected

- `docs/research/research_cockpit_ui_redesign_v1.md`
- `docs/research/execution_reality_daily_monitor.md`
- `docs/research/sessions/2026-05-22/phase5_evidence_monitor.md`
- `docs/research/research_cockpit_v2_architecture.md`

---

## Goal

Convert the current Markdown execution monitors into a local dashboard architecture that is easier to read, while preserving the Research Cockpit v2 guardrail:

```text
finalized artifacts in, no runtime actions out
```

The dashboard should expose current Phase 5 / Phase 6 evidence as cards, tables, traffic lights, trend arrows, readiness state, and alerts. It must not call live APIs, submit orders, cancel orders, alter risk state, launch paper, run replay, or promote S3.

---

## Current Evidence Snapshot

| Metric | Current |
|---|---:|
| Paired trades | 9 |
| BTC | 1 |
| ETH | 8 |
| TP / WIN | 3 |
| SL / LOSS | 6 |
| Mean `pnl_usdc` | -0.005455 |
| Mean `quote_age_at_submit_ms` | 18.987s |
| Mean `quote_age_at_fill_ms` | 18.990s |
| Quote lineage IDs | 18 |
| 60s+ quote-age fills | 1 |
| Phase 6 readiness | 65.0% |
| Recommendation | `COLLECT_MORE_EVIDENCE` |

Blocking gates:

- paired trades: 9/20
- BTC: 1/5
- TP: 3/5

---

## MVP Architecture

```text
docs/research/*.md
docs/research/sessions/**/*.md
runtime/reports/*.json or future normalized report
        |
        v
read-only local artifact loader
        |
        v
Research Cockpit frontend pages
        |
        v
cards, tables, traffic lights, trend arrows, alerts
```

MVP input can start from a checked-in static JSON fixture or manually normalized artifact derived from the current monitors. The dashboard should not parse raw JSONL directly in the browser for MVP. Raw JSONL remains a source tier, but a normalizer should convert it into a stable dashboard contract before UI rendering.

---

## Frontend Stack Recommendation

| Stack | Fit | Pros | Cons | Recommendation |
|---|---|---|---|---|
| Static HTML + CSS + small JS | Good for one-off artifact viewer | Minimal tooling, easy local open, low risk | Harder to scale page routing, reusable cards, state, and future filters | Not recommended as canonical MVP |
| React SPA with Vite | Best MVP fit | Lightweight, local-first, component reuse, easy static build, no server requirement after build | Needs one frontend package boundary | Recommended MVP |
| Next.js | Good for larger product dashboard | Strong routing and data conventions | More server/app complexity than needed for read-only local artifacts | Defer |
| Existing artifact viewer / Markdown-only | Safe but insufficient | No code needed, preserves docs | Does not solve monitor readability enough | Use only as fallback |

Recommended MVP path:

```text
React SPA with Vite, rendered from static normalized JSON artifacts.
```

Why this path:

- It is lighter than Next.js.
- It can run locally and export static assets.
- It fits the existing `web-dashboard` direction from the architecture doc.
- It supports reusable gate cards, traffic lights, trend arrows, drawers, and tables.
- It keeps data loading read-only and artifact-driven.

Non-MVP stack decisions:

- Do not add backend APIs.
- Do not connect to live runtime internals.
- Do not parse private config.
- Do not read wallet, CLOB, or exchange state.
- Do not make the cockpit a runtime control plane.

---

## Shared UI Primitives

Every page should use the same primitives so evidence status is consistent.

### Status Badge

| Status | Color | Meaning |
|---|---|---|
| `AVAILABLE` | green | Direct field or validated offline derivation exists. |
| `PARTIAL` | yellow | Evidence exists but is below gate or incomplete. |
| `MISSING` | red | Required field or source is absent. |
| `UNSUPPORTED` | gray | Current artifacts do not produce this field. |
| `STALE` | yellow | Source exists but is outside selected window. |
| `GAP` | red/yellow | Known evidence gap from monitor or compact state. |
| `INFO` | blue | Non-gating context. |

### Traffic Light

| Light | UI label | Use |
|---|---|---|
| GREEN | met | Gate passed with direct evidence. |
| YELLOW | accumulating | Gate has evidence but remains below target or is inconclusive. |
| RED | blocked | Missing, invalid, mixed-era, or unsafe evidence. |
| GRAY | unsupported | Not emitted by current artifact contract. |
| BLUE | info | Context only. |

### Trend Arrow

| Arrow label | Meaning |
|---|---|
| UP | current value improved against prior monitor baseline. |
| DOWN | current value regressed. |
| FLAT | current value unchanged. |
| NA | no prior point or unsupported field. |

Trend arrows describe monitor-to-monitor movement only. They do not imply statistical significance.

### Gate Card Contract

| Field | Required |
|---|---|
| `title` | yes |
| `value` | yes |
| `target` | when gated |
| `unit` | when needed |
| `status` | yes |
| `traffic_light` | yes |
| `trend_arrow` | when prior baseline exists |
| `source_doc` | yes |
| `jsonl_source` | yes if direct JSONL source exists |
| `evidence_ref` | yes |
| `notes` | yes for partial or blocked states |

---

## Page: Overview

Purpose: show Phase 6 readiness, blocking gates, and the most important deltas immediately.

Cards:

| Card | Current value | Traffic light | Trend arrow | Data source | JSONL source |
|---|---:|---|---|---|---|
| Phase 6 readiness | 65.0% | YELLOW | UP | `execution_reality_daily_monitor.md` | derived from execution/trade artifacts |
| Recommendation | `COLLECT_MORE_EVIDENCE` | YELLOW | NA | both monitors | n/a |
| Paired trades | 9/20 | YELLOW | UP | `phase5_evidence_monitor.md` | `trade_journal`, `execution_log` |
| BTC coverage | 1/5 | YELLOW | UP | `phase5_evidence_monitor.md` | `trade_journal` |
| ETH coverage | 8/5 | GREEN | NA | `phase5_evidence_monitor.md` | `trade_journal` |
| TP coverage | 3/5 | YELLOW | FLAT | `phase5_evidence_monitor.md` | `trade_journal` |
| SL coverage | 6/5 | GREEN | NA | `phase5_evidence_monitor.md` | `trade_journal` |
| 60s+ quote evidence | 1/1 | GREEN for coverage, YELLOW for interpretation | NA | `phase5_evidence_monitor.md` | `execution_log`, `trade_journal` |

Tables:

- compact blocking gate table
- current evidence snapshot
- last monitor delta summary

Future widgets:

- source freshness strip
- run selector by date and run id
- asset filter chips
- "what blocks Phase 6" callout

---

## Page: Execution Reality

Purpose: prove that timestamp, fill, submit, and quote lineage evidence exists before interpreting outcomes.

Cards:

| Card | Current value | Traffic light | Trend arrow | Data source | JSONL source |
|---|---:|---|---|---|---|
| Clean outcome-truth runs | 2 | BLUE | NA | both monitors | `execution_log`, `trade_journal` |
| Paper fills with quote age | 18/18 | GREEN | NA | `phase5_evidence_monitor.md` | `execution_log` |
| Submit attempts with quote age | 18/18 | GREEN | NA | `phase5_evidence_monitor.md` | `execution_log` |
| Quote lineage IDs | 18 | GREEN | NA | both monitors | `execution_log` |
| Paired trades | 9/20 | YELLOW | UP | both monitors | `trade_journal`, `execution_log` |
| Outcome-truth closes | 9/9 | GREEN | NA | `phase5_evidence_monitor.md` | `trade_journal` |

Tables:

- instrumentation-era run ledger
- field integrity table
- paired trade detail table

Traffic-light rules:

- GREEN when direct field coverage is complete for included clean runs.
- YELLOW when evidence is valid but below readiness gate.
- RED when required fields are missing or eras are mixed.
- BLUE for non-gating run metadata.

Future widgets:

- execution lifecycle timeline: signal, decision, intent, submit, ack, fill, close
- p50 / p95 / max latency cards when available
- quote lineage drilldown drawer
- clean-run eligibility checklist

---

## Page: Quote Age

Purpose: show quote freshness, stale bucket evidence, and quote-age vs outcome relationship.

Cards:

| Card | Current value | Traffic light | Trend arrow | Data source | JSONL source |
|---|---:|---|---|---|---|
| Mean submit quote age | 18.987s | BLUE | NA | `phase5_evidence_monitor.md` | `execution_log` |
| Mean fill quote age | 18.990s | BLUE | NA | `phase5_evidence_monitor.md` | `execution_log` |
| 60s+ fills | 1 | GREEN for coverage | NA | both monitors | `execution_log` |
| Stale relationship | inconclusive | YELLOW | NA | `phase5_evidence_monitor.md` | `execution_log`, `trade_journal` |
| 5-15s mean PnL | -0.006089 | YELLOW | NA | `phase5_evidence_monitor.md` | `trade_journal` |
| 30-60s mean PnL | -0.010346 | YELLOW | NA | `phase5_evidence_monitor.md` | `trade_journal` |
| 60s+ mean PnL | +0.012388 | YELLOW | NA | `phase5_evidence_monitor.md` | `trade_journal` |

Tables:

- quote-age distribution
- mean PnL by entry quote-age bucket
- quote-age vs outcome matrix
- entry age vs exit age detail

Traffic-light rules:

- GRAY for buckets with no paired closes.
- YELLOW for small samples or contradictory stale behavior.
- RED only after repeated stale losses meet minimum evidence.
- GREEN only when a bucket has enough sample size and stable interpretation.

Future widgets:

- bucket histogram
- quote-age vs PnL scatter plot
- entry quote age vs exit quote age linked chart
- stale quote contradiction badge

---

## Page: Outcome Truth

Purpose: make ground-truth outcomes obvious and separate them from inferred TP/SL labels.

Cards:

| Card | Current value | Traffic light | Trend arrow | Data source | JSONL source |
|---|---:|---|---|---|---|
| TP / WIN | 3/5 | YELLOW | FLAT | `phase5_evidence_monitor.md` | `trade_journal` |
| SL / LOSS | 6/5 | GREEN | NA | `phase5_evidence_monitor.md` | `trade_journal` |
| WIN / LOSS split | 3 / 6 | YELLOW | NA | `phase5_evidence_monitor.md` | `trade_journal` |
| Mean PnL | -0.005455 | YELLOW | NA | both monitors | `trade_journal` |
| Result/PnL agreement | 9/9 | GREEN | NA | `phase5_evidence_monitor.md` | `trade_journal` |
| BTC mean PnL | -0.020121 | YELLOW | NA | `phase5_evidence_monitor.md` | `trade_journal` |
| ETH mean PnL | -0.003622 | YELLOW | NA | `phase5_evidence_monitor.md` | `trade_journal` |

Tables:

- asset segmentation table
- confirmed paired trade detail
- outcome summary table
- deprecated inferred outcome drawer if old labels exist

Traffic-light rules:

- GREEN for complete direct field agreement.
- YELLOW for below-gate outcome counts, asset concentration, or small negative PnL sample.
- RED for missing `trade_result`, missing `pnl_usdc`, or sign/result disagreement.

Future widgets:

- TP/SL stacked bar by asset
- PnL distribution by bucket and asset
- side split: YES vs NO
- result/PnL consistency validator

---

## Page: Trend

Purpose: show daily deltas and whether the evidence base is accumulating.

Cards:

| Card | Current value | Traffic light | Trend arrow | Data source | JSONL source |
|---|---:|---|---|---|---|
| Paired delta | +1 | YELLOW | UP | both monitors | derived |
| BTC delta | +1 | YELLOW | UP | both monitors | derived |
| TP delta | 0 | YELLOW | FLAT | both monitors | derived |
| Readiness delta | +5.0 pp | YELLOW | UP | both monitors | derived |
| Trend status | `ACCUMULATING` | YELLOW | UP | `execution_reality_daily_monitor.md` | n/a |

Tables:

- rolling trend table
- daily execution reality table
- prior baseline vs current table

Traffic-light rules:

- GREEN only when all required gates are met.
- YELLOW for accumulating but incomplete evidence.
- RED for regression, invalid source, or evidence contradiction.

Future widgets:

- sparkline by gate
- daily accumulation chart
- asset coverage trend
- TP/SL balance trend

---

## Page: Readiness

Purpose: make Phase 6 readiness and promotion blockers impossible to miss.

Cards:

| Card | Current value | Traffic light | Trend arrow | Data source | JSONL source |
|---|---:|---|---|---|---|
| Phase 6 readiness | 65.0% | YELLOW | UP | both monitors | derived |
| Paired gate | 9/20 | YELLOW | UP | both monitors | `trade_journal` |
| BTC gate | 1/5 | YELLOW | UP | `phase5_evidence_monitor.md` | `trade_journal` |
| TP gate | 3/5 | YELLOW | FLAT | `phase5_evidence_monitor.md` | `trade_journal` |
| SL gate | 6/5 | GREEN | NA | `phase5_evidence_monitor.md` | `trade_journal` |
| 60s+ gate | 1/1 | GREEN coverage, YELLOW interpretation | NA | `phase5_evidence_monitor.md` | `execution_log`, `trade_journal` |
| Recommendation | `COLLECT_MORE_EVIDENCE` | YELLOW | NA | both monitors | n/a |

Tables:

- gate progress table
- blocking gate reasons
- readiness formula and capped gate components
- ETA by gate

Traffic-light rules:

- `READY_FOR_PHASE6` only when paired, BTC, TP, SL, and stale evidence are all green and stale interpretation is not contradictory.
- `COLLECT_MORE_EVIDENCE` if any required gate is yellow or red.
- `ACCUMULATING` is a status label, not a promotion recommendation.

Future widgets:

- radial readiness meter
- gate progress bars
- blocking-gate priority list
- readiness audit trail by monitor update

---

## Page: Alerts

Purpose: centralize operator attention and prevent important warnings from being buried in tables.

Cards:

| Card | Current value | Traffic light | Trend arrow | Data source | JSONL source |
|---|---|---|---|---|---|
| Active alerts | 6 | YELLOW | NA | `research_cockpit_ui_redesign_v1.md` | derived |
| Blocking gates | paired, BTC, TP | YELLOW | NA | both monitors | derived |
| Stale relationship | inconclusive | YELLOW | NA | `phase5_evidence_monitor.md` | `execution_log`, `trade_journal` |
| Source health | outcome truth present | GREEN | NA | `phase5_evidence_monitor.md` | `trade_journal` |

Tables:

- active alert list
- alert severity taxonomy
- resolved/met gate list
- source health checklist

Traffic-light rules:

- RED for missing direct fields, era mixing, invalid source, or live-risk ambiguity.
- YELLOW for below-gate evidence, sample concentration, contradiction, or stalled trend.
- BLUE for context-only facts.
- GREEN for resolved alerts and met gates.

Future widgets:

- alert drawer visible on every page
- severity filter
- alert-to-evidence link
- stale contradiction watchlist

---

## Data Contract Recommendation

The frontend should not depend directly on Markdown table parsing long term. It should consume a small normalized local artifact.

MVP contract shape:

```json
{
  "schema_version": "research_cockpit_frontend_v1",
  "generated_at": "2026-05-22",
  "mode": "paper",
  "source_docs": [],
  "runtime_behavior_changed": false,
  "live_behavior_changed": false,
  "recommendation": "COLLECT_MORE_EVIDENCE",
  "readiness": {
    "percent": 65.0,
    "status": "ACCUMULATING",
    "blocking_gates": ["paired", "BTC", "TP"]
  },
  "pages": {
    "overview": { "cards": [], "tables": [], "alerts": [] },
    "execution_reality": { "cards": [], "tables": [] },
    "quote_age": { "cards": [], "tables": [] },
    "outcome_truth": { "cards": [], "tables": [] },
    "trend": { "cards": [], "tables": [] },
    "readiness": { "cards": [], "tables": [] },
    "alerts": { "cards": [], "tables": [] }
  }
}
```

Each card:

```json
{
  "id": "paired_trades",
  "title": "Paired trades",
  "value": 9,
  "target": 20,
  "unit": "trades",
  "status": "PARTIAL",
  "traffic_light": "YELLOW",
  "trend_arrow": "UP",
  "source_doc": "docs/research/sessions/2026-05-22/phase5_evidence_monitor.md",
  "jsonl_source": ["runtime/quant_data/trade_journal/*.jsonl"],
  "evidence_ref": "Current Coverage",
  "notes": "Below Phase 6 paired gate."
}
```

---

## JSONL Source Map

| Evidence area | Primary JSONL source | Secondary JSONL source |
|---|---|---|
| execution timestamps | `runtime/quant_data/execution_log/*.jsonl` | `runtime/quant_data/decision_log/*.jsonl` |
| quote age | `runtime/quant_data/execution_log/*.jsonl` | `runtime/quant_data/market_snapshots/*.jsonl` |
| quote lineage | `runtime/quant_data/execution_log/*.jsonl` | `runtime/quant_data/market_snapshots/*.jsonl` |
| paired trade outcome | `runtime/quant_data/trade_journal/*.jsonl` | `runtime/quant_data/execution_log/*.jsonl` |
| PnL | `runtime/quant_data/trade_journal/*.jsonl` | none |
| asset split | `runtime/quant_data/trade_journal/*.jsonl` | `runtime/quant_data/execution_log/*.jsonl` |
| trend / delta | normalized monitor artifact | source monitor docs |
| alerts | normalized monitor artifact | source monitor docs |

For MVP, JSONL sources should be shown as provenance labels, not parsed by the frontend.

---

## Exactly Three MVP Paths

## OPTION 1 - SAFE EV PRESERVATION

Build a React + Vite static local dashboard that consumes a checked-in normalized JSON artifact created from the current monitors.

Pros:

- Best balance of readability and safety.
- Reusable cards and pages without server complexity.
- Easy to keep read-only.
- Fits future `web-dashboard` direction.

Cons:

- Requires a small normalized artifact before rendering.

Recommendation: choose this path.

## OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY

Build a richer React dashboard with interactive filtering, bucket charts, asset drilldowns, and alert drawers immediately.

Pros:

- Higher operator insight.
- Better exploration for quote-age and outcome truth.

Cons:

- More UI surface before the data contract is stable.
- Higher risk of one-off parsing or accidental interpretation drift.

Use after Option 1 proves useful.

## OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

Create the full Research Cockpit v2 report normalizer and schema before any frontend page exists.

Pros:

- Cleanest long-term architecture.
- Avoids Markdown parsing and duplicated calculations.

Cons:

- Delays the readability fix.
- Larger scope than the current monitor UX problem.

Use when multiple monitor families are ready to consolidate.

---

## Recommended MVP Path

```text
React SPA with Vite + static normalized JSON artifact
```

MVP pages:

1. Overview
2. Execution Reality
3. Quote Age
4. Outcome Truth
5. Trend
6. Readiness
7. Alerts

MVP components:

- status badge
- traffic light
- trend arrow
- gate card
- metric card
- evidence table
- progress bar
- alert row
- source label

MVP data behavior:

- load local normalized JSON
- render missing fields as `MISSING`, `UNSUPPORTED`, or `GAP`
- never convert missing to zero
- never call runtime APIs
- never write runtime files
- never promote readiness automatically

---

## Non-Goals

- No code implementation in this task.
- No dashboard scaffold in this task.
- No runtime behavior changes.
- No live behavior changes.
- No paper launch.
- No replay.
- No S3 promotion.
- No wallet, order, strategy, risk, or execution changes.
- No direct browser parsing of raw JSONL for MVP.
- No automatic Phase 6 promotion.

---

## Acceptance Criteria For Future Implementation

1. The dashboard opens locally and displays all seven MVP pages.
2. Every page shows cards, tables, traffic lights, trend arrows where applicable, data source, JSONL source, and future widget placeholders.
3. Phase 6 readiness is visible on Overview and Readiness.
4. Blocking gates are visible without opening a detail table.
5. Alerts are visible from every page.
6. Missing or unsupported evidence is explicitly labeled.
7. No runtime APIs, live APIs, wallet APIs, paper launch, replay launch, or S3 promotion path exists in the frontend.
8. The frontend can be statically built for offline review.
