# Research Cockpit UI Redesign Audit v1

Document type: UI wireframe and monitor readability audit.

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

- `docs/research/execution_reality_daily_monitor.md`
- `docs/research/sessions/2026-05-22/phase5_evidence_monitor.md`
- `docs/research/research_cockpit_v2_architecture.md`

---

## Root Problem

The current Markdown monitors are correct but difficult to operate from. The reader must scan long tables, repeated gate language, and prose notes to answer a few high-priority questions:

- Is Phase 6 ready?
- Which gate is blocking?
- Did evidence improve today?
- Are quote-age outcomes safe, stale, or contradictory?
- Are BTC and ETH covered enough to trust the sample?
- Which alerts require operator attention?

The cockpit should convert the same evidence into an operator-readable status surface. It must not add runtime behavior, infer missing data as zero, or hide uncertainty.

---

## Design Principles

1. One screen answers readiness.
2. Traffic lights show gate state before tables.
3. Cards show value, target, trend, source, and status.
4. Missing, partial, stale, and unsupported evidence must be visible.
5. Tables remain available as drilldown, not the first view.
6. The cockpit reads finalized artifacts only.
7. Phase 6 recommendation is advisory research status, not runtime authority.

---

## Traffic Light Semantics

| Light | Label | Meaning | Example |
|---|---|---|---|
| GREEN | Ready / met | Gate target met with direct evidence. | SL 6/5, ETH 8/5, 60s+ 1/1 |
| YELLOW | Accumulating / partial | Evidence exists but gate target is not met. | paired 9/20, TP 3/5 |
| RED | Blocked / missing | Evidence is absent, invalid, stale, or unsafe for a claim. | BTC 0/5 before first BTC sample |
| GRAY | Unsupported | Current artifacts do not produce the field. | Future MFE/MAE path cards until direct path evidence exists |
| BLUE | Informational | Non-gating context or neutral status. | source freshness, run count |

Use both color and text labels so screenshots remain interpretable without color.

---

## Global Shell Wireframe

```text
Research Cockpit v2: Execution Reality

[Run scope: 2026-05-22] [Mode: PAPER] [Source: finalized artifacts] [No runtime actions]

┌──────────────────────────────────────────────────────────────────────────────┐
│ Phase 6 Readiness                                                           │
│ STATUS: ACCUMULATING / COLLECT_MORE_EVIDENCE                                │
│ Readiness: 65.0%        Paired: 9/20        BTC: 1/5        TP: 3/5          │
│ Blocking gates: paired, BTC, TP                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│ Overview    │ Execution   │ Quote Age   │ Outcome     │ Trend       │
│ selected    │ Reality     │             │ Truth       │             │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘

Main canvas:
  left rail: section navigation and alert count
  center: selected section cards and chart/table preview
  right rail: readiness gates, ETA, source health
```

Desktop should use a dense operations layout. Mobile should stack the readiness panel first, then the selected section, then alerts.

---

## Overview

Purpose: answer "what changed and what blocks Phase 6?" in under 10 seconds.

```text
┌──────────────────────── Overview ────────────────────────┐
│ Traffic Lights                                             │
│ [YELLOW] Paired 9/20   [YELLOW] BTC 1/5   [GREEN] ETH 8/5 │
│ [YELLOW] TP 3/5        [GREEN] SL 6/5    [GREEN] 60s+ 1/1 │
│                                                           │
│ Today                                                     │
│ Paired +1   BTC +1   TP 0   Readiness +5.0 pp             │
│                                                           │
│ Recommendation                                            │
│ COLLECT_MORE_EVIDENCE                                     │
└───────────────────────────────────────────────────────────┘
```

Overview cards:

| Card | Value | Light | Trend | Source |
|---|---:|---|---|---|
| Phase 6 readiness | 65.0% | YELLOW | UP | daily monitor |
| Paired trades | 9/20 | YELLOW | UP | phase5 monitor |
| BTC coverage | 1/5 | YELLOW | UP | phase5 monitor |
| ETH coverage | 8/5 | GREEN | FLAT/covered | phase5 monitor |
| TP outcomes | 3/5 | YELLOW | FLAT | phase5 monitor |
| SL outcomes | 6/5 | GREEN | covered | phase5 monitor |
| Stale evidence | 1/1 | GREEN for coverage, YELLOW for interpretation | FLAT | quote-age monitor |

The stale evidence card needs two states: evidence coverage is met, but interpretation remains yellow because the single 60s+ trade was a TP and does not prove stale quotes lose more.

---

## Execution Reality

Purpose: show whether the execution timestamp and quote lineage evidence is complete enough to trust the outcome sample.

```text
┌──────────── Execution Reality ────────────┐
│ Fills with quote age      18/18  GREEN    │
│ Submit attempts with age  18/18  GREEN    │
│ Quote lineage IDs         18     GREEN    │
│ Paired trades             9/20   YELLOW   │
│ Outcome-truth runs        2      BLUE     │
└───────────────────────────────────────────┘
```

Gate cards:

| Card | Primary value | Secondary value | Light | Drilldown |
|---|---:|---:|---|---|
| Paired trades | 9 | target 20 | YELLOW | paired trade detail |
| Fills | 18 | quote-age coverage 18/18 | GREEN | fill event coverage |
| Submit attempts | 18 | submit-age coverage 18/18 | GREEN | submit event coverage |
| Quote lineage | 18 | distinct IDs | GREEN | lineage table |
| Outcome-truth runs | 2 | clean runs | BLUE | run ledger |

Operator rule: show counts first, then expose the run ledger under a drawer. The long run table should not be the first thing the user sees.

---

## Quote Age

Purpose: make the stale-quote relationship visually obvious without overclaiming from one 60s+ trade.

```text
┌──────────────────────── Quote Age ────────────────────────┐
│ Mean submit age: 18.987s     Mean fill age: 18.990s        │
│                                                           │
│ Buckets                                                   │
│ 0-5s    2 fills   no paired closes                        │
│ 5-15s   9 fills   5 trades   mean pnl -0.006089           │
│ 15-30s  3 fills   no paired closes                        │
│ 30-60s  3 fills   3 trades   mean pnl -0.010346           │
│ 60s+    1 fill    1 trade    mean pnl +0.012388           │
│                                                           │
│ Stale relationship: INCONCLUSIVE                          │
└───────────────────────────────────────────────────────────┘
```

Recommended visualization:

```text
Bucket      Outcome Mix          Mean PnL        State
0-5s        no closes            n/a             GRAY
5-15s       TP 1 / SL 4          -0.006089       YELLOW
15-30s      no closes            n/a             GRAY
30-60s      TP 1 / SL 2          -0.010346       YELLOW
60s+        TP 1 / SL 0          +0.012388       YELLOW
```

Traffic-light rule:

- GREEN only when bucket has enough samples and relationship is stable.
- YELLOW when samples exist but are too thin or contradictory.
- RED when stale bucket shows repeated loss concentration after minimum sample.
- GRAY when no paired closes exist.

---

## Outcome Truth

Purpose: separate confirmed `trade_result` and `pnl_usdc` from any inferred outcome label.

```text
┌──────────────────── Outcome Truth ────────────────────┐
│ TP / WIN       3     YELLOW     target 5               │
│ SL / LOSS      6     GREEN      target 5               │
│ Mean PnL       -0.005455        YELLOW                 │
│ Sign agreement 9/9   GREEN                              │
│ Asset split    BTC 1 / ETH 8    YELLOW                 │
└────────────────────────────────────────────────────────┘
```

Outcome cards:

| Card | Display | Light | Reason |
|---|---|---|---|
| TP/WIN | 3/5 | YELLOW | below gate |
| SL/LOSS | 6/5 | GREEN | gate met |
| WIN/LOSS split | 3 / 6 | YELLOW | SL-heavy sample |
| Mean PnL | -0.005455 | YELLOW | negative but small sample |
| Result/PnL agreement | 9/9 | GREEN | direct fields agree |
| BTC vs ETH | BTC 1, ETH 8 | YELLOW | BTC below gate |

The cockpit should label `trade_result` and `pnl_usdc` as ground truth fields and move inferred labels into a hidden or deprecated drawer.

---

## Trend

Purpose: show movement since the prior accepted monitor baseline.

Use arrows plus labels:

| Metric | Previous | Current | Arrow | Label |
|---|---:|---:|---|---|
| Paired trades | 8 | 9 | UP | improving |
| BTC trades | 0 | 1 | UP | improving |
| TP outcomes | 3 | 3 | FLAT | stalled |
| Readiness | 60.0% | 65.0% | UP | improving |

Wireframe:

```text
┌──────────────────────── Trend ────────────────────────┐
│ Paired       8 -> 9      UP      +1                    │
│ BTC          0 -> 1      UP      +1                    │
│ TP           3 -> 3      FLAT    needs +2              │
│ Readiness    60 -> 65    UP      +5.0 pp               │
└────────────────────────────────────────────────────────┘
```

Trend arrows must never imply statistical significance. They only describe monitor-to-monitor movement.

---

## Readiness

Purpose: make promotion status impossible to misread.

```text
┌──────────────────── Phase 6 Readiness ────────────────────┐
│ Recommendation: COLLECT_MORE_EVIDENCE                      │
│ Readiness: 65.0%                                           │
│ Blocking gates: paired, BTC, TP                            │
│                                                            │
│ paired  9/20  [#########-----------] YELLOW                │
│ BTC     1/5   [####----------------] YELLOW                │
│ TP      3/5   [############--------] YELLOW                │
│ SL      6/5   [####################] GREEN capped          │
│ 60s+    1/1   [####################] GREEN coverage only   │
└────────────────────────────────────────────────────────────┘
```

Gate card structure:

| Field | Required |
|---|---|
| Gate name | Required |
| Current / target | Required |
| Percent capped | Required |
| Traffic light | Required |
| Trend arrow | Required |
| Blocking reason | Required when yellow or red |
| Evidence source | Required |
| Last updated | Required |

Readiness rule:

- `READY_FOR_PHASE6` only if all required gates are green and stale-quote interpretation is not contradictory.
- `COLLECT_MORE_EVIDENCE` if any required gate is yellow or red.
- `ACCUMULATING` is a monitor state, not a promotion recommendation.

---

## ETA

Purpose: show how much evidence remains without pretending the accumulation rate is stable.

```text
┌──────────────────────── ETA ────────────────────────┐
│ paired >=20    needs 11     current speed +1/delta   │
│ BTC >=5        needs 4      current speed +1/delta   │
│ TP >=5         needs 2      stalled; not estimable   │
│ Phase 6        blocked      waits on paired/BTC/TP   │
└──────────────────────────────────────────────────────┘
```

ETA states:

| State | Meaning |
|---|---|
| ESTIMABLE | Recent delta is positive and target gap is finite. |
| STALLED | Recent delta is zero for a required gate. |
| BLOCKED | Gate has missing direct field or invalid source. |
| MET | Gate already satisfied. |

Do not express ETA as calendar days unless monitor cadence is explicit. Use "monitor deltas" until daily run cadence is stable.

---

## Alerts

Purpose: separate operator attention from passive context.

Alert drawer:

```text
┌──────────────────────── Alerts ──────────────────────┐
│ YELLOW  paired sample below gate      9/20            │
│ YELLOW  BTC sample below gate         1/5             │
│ YELLOW  TP sample below gate          3/5             │
│ YELLOW  stale quote relationship inconclusive         │
│ BLUE    ETH and SL gates already capped               │
└───────────────────────────────────────────────────────┘
```

Alert severity:

| Severity | Use |
|---|---|
| RED | Missing direct field, invalid source, era mixing, or live-risk ambiguity. |
| YELLOW | Gate below threshold, sample concentration, contradictory relationship, stalled trend. |
| BLUE | Informational source or context update. |
| GREEN | Resolved alert or met gate. |

Initial alert set from current monitors:

| Severity | Alert | Evidence |
|---|---|---|
| YELLOW | Paired count below Phase 6 gate | 9/20 |
| YELLOW | BTC count below Phase 6 gate | 1/5 |
| YELLOW | TP count below Phase 6 gate | 3/5 |
| YELLOW | Stale quote relationship inconclusive | 60s+ bucket has one TP |
| YELLOW | Outcome sample is ETH-heavy and SL-heavy | BTC 1, ETH 8, TP 3, SL 6 |
| BLUE | Outcome truth fields are present | `trade_result`, `pnl_usdc`, `entry_price` |

---

## Navigation Model

```text
Overview
Execution Reality
Quote Age
Outcome Truth
Trend
Readiness
ETA
Alerts
```

Recommended default route: Overview.

Persistent right rail:

- Phase 6 recommendation.
- Readiness percent.
- Blocking gates.
- Source freshness.
- "No runtime actions" marker.

---

## Data Mapping

| UI area | Source field / section | Current value |
|---|---|---|
| Paired trades | confirmed paired trades | 9 |
| BTC | BTC confirmed paired trades | 1 |
| ETH | ETH confirmed paired trades | 8 |
| TP | `trade_result=TP` / `pnl_usdc > 0` | 3 |
| SL | `trade_result=SL` / `pnl_usdc < 0` | 6 |
| WIN/LOSS | `pnl_usdc` sign | 3 / 6 |
| Mean PnL | mean `pnl_usdc` | -0.005455 |
| Submit quote age | mean `quote_age_at_submit_ms` | 18.987s |
| Fill quote age | mean `quote_age_at_fill_ms` | 18.990s |
| Quote lineage | distinct `quote_lineage_id` | 18 |
| Stale bucket | 60s+ fills | 1 |
| Readiness | capped gate average | 65.0% |
| Recommendation | monitor recommendation | COLLECT_MORE_EVIDENCE |

---

## Exactly Three UI Paths

## OPTION 1 - SAFE EV PRESERVATION

Build the cockpit as a static artifact-driven dashboard view that mirrors the markdown monitors. This is the safest path because it improves readability without changing evidence production, runtime policy, paper behavior, or live behavior.

Recommended for the next implementation phase.

## OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY

Add richer interactive drilldowns for quote-age buckets, BTC/ETH segmentation, and paired trade details. This improves research velocity but requires a stronger normalized report contract to avoid one-off parsing logic.

Use after the static card model is accepted.

## OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

Create the full Research Cockpit v2 normalized report before building any UI. This gives the cleanest long-term architecture but delays the immediate readability fix.

Use if the main risk is inconsistent source documents rather than cockpit readability.

---

## Recommendation

```text
OPTION 1 - SAFE EV PRESERVATION
```

Create a static, artifact-driven Research Cockpit UI view with:

- Overview traffic lights.
- Execution Reality gate cards.
- Quote Age bucket cards.
- Outcome Truth cards using `trade_result` and `pnl_usdc`.
- Trend arrows.
- Phase 6 readiness panel.
- ETA panel.
- Alerts drawer.

Current Phase 6 recommendation remains:

```text
COLLECT_MORE_EVIDENCE
```

---

## Non-Goals

- No runtime behavior changes.
- No live behavior changes.
- No paper launch.
- No replay.
- No S3 promotion.
- No wallet, order, risk, strategy, or execution changes.
- No conversion of missing fields to zero.
- No automatic Phase 6 promotion.

---

## Acceptance Criteria For Future UI Work

1. Operator can identify blocking Phase 6 gates in under 10 seconds.
2. Every card shows status, source, and evidence freshness.
3. Green gates cannot hide yellow interpretation warnings.
4. Quote-age stale evidence remains inconclusive until sample size supports a relationship.
5. BTC, ETH, TP, SL, WIN, LOSS, PnL, quote-age, delta, trend, ETA, and alerts are visible without reading long markdown tables.
6. The UI preserves the v2 architecture guardrail: finalized artifacts in, no runtime actions out.
