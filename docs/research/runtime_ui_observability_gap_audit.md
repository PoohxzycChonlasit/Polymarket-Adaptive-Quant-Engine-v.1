# Runtime UI Observability Gap Audit

Date: 2026-05-25

Scope: research-only audit of the runtime operator console against current path-truth and session-intelligence research.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Role Routing

- Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`
- Supporting roles: `08_RESEARCH_QUANT_AGENT.md`, `16_PAPER_EVALUATION_AGENT.md`
- Why selected: the task audits operator-visible observability against research evidence and paper-evidence gates.
- Files inspected: `utils/display.py`, `main.py`, `docs/OBSERVABILITY_PLAN.md`, `docs/research/path_truth_multiday_coverage_monitor.md`, `docs/research/single_run_path_truth_audit.md`, `docs/research/path_truth_gate_revision.md`, selected research summaries under `docs/research/`.
- Files intentionally ignored: strategy modules, risk modules, order placement modules, wallet/live config, replay execution, paper runtime launch.

## Current UI

The current `PolymarketRealtimeDisplay` is a responsive Rich terminal console with `auto`, `compact`, `standard`, `wide`, and `fullscreen` modes.

Active layout panels:

| Surface | Current visibility |
|---|---|
| Header | mode, run id, data status, git tag, readiness, Phase6 label, S3 label, JSONL status |
| System Status | WebSocket, oracle, orderbook, mode, latency, logging, run id |
| Portfolio | cash, equity, source, bankroll tier, risk mode, guard, exposure, drawdown, positions, paper/live safety |
| Risk | runtime risk state and risk-off status |
| Market Scan / Market Cards | BTC/ETH price, PTB, bid/ask, spread, model probabilities, EV, confidence, decision, blocker, liquidity, lifecycle phase, timing milestones, executable book/spread, depth, fill size, readiness |
| Recent Decisions / Timing | latest ticker decisions, phase, blocker, EV, confidence, remaining time |
| Decision Diagnostics | candidate state, lifecycle phase, main blocker, cutoff, age, token/orderbook/liquidity, EV/probability visibility; trace details only in fullscreen |
| Execution Reality | paired trades, BTC/ETH counts, TP/SL counts, 60s+ count, win/loss, blocking gates |
| Quote Age | mean submit/fill age and buckets, but only in wide/fullscreen and only when populated |
| Rolling Logs | wide/fullscreen only |

There is also a `Research Cockpit` renderer with sections for regime, lifecycle, S3, economic/classification evidence, health, anomalies, and runtime. However, it is not mounted in the active `_render()` layout. In practice, the research cockpit surface is dormant unless directly rendered by tests or a future layout path.

## Missing Observability

### Session Intelligence

Research-visible but operator-invisible:

| Research state | Current operator visibility | Gap |
|---|---|---|
| `02h` = `HOSTILE_SESSION_CANDIDATE`, currently cited as 0 TP / 12 SL | Not shown as a session warning | Operator cannot see that current UTC hour may be historically hostile |
| `09h10h` = `SESSION_EDGE_CANDIDATE` | Not shown as an edge watch | Operator cannot see when the run is inside the priority harvest window |
| BTC global weakness, path-truth 0 TP / 10 SL | BTC market card shows live market state only | Operator sees BTC price/liquidity but not BTC research caution |
| NO weakness, recent 26 TP / 59 SL and path-truth 2 TP / 13 SL | Side is visible in market/candidate fields only | Operator sees NO side but not the current NO weakness label |
| Confidence of research labels | Not shown | Operator cannot distinguish strong evidence from tiny-sample candidate labels |

Current UI answers "what is happening now?" but not "is this current context a known hostile or edge candidate?"

### Path Truth

Research-visible but operator-invisible:

| Research state | Current operator visibility | Gap |
|---|---|---|
| Path truth checkpoints: +15, +30, +45, +60, `event_end` | Not displayed as path-truth coverage | Operator cannot see whether path truth is growing cleanly |
| Fast close is real and dominant, around 88% in current research context | Execution Reality has a 60s+ gate only | Operator cannot see 0-15s and 15-30s dominance |
| Full coverage vs fast-close partial | Not shown | Operator cannot distinguish writer failure from legitimate fast close |
| Gate progress: Stage A 3 dates, Stage B 7 dates | Header does not show path-truth gates | Operator cannot see why field wiring remains blocked |
| Field gaps: `quote_age_ms`, `candidate_id`, `decision_id` | Not shown in runtime console | Operator cannot tell which research joins remain blind |

The current console has execution-evidence counters, but it does not have a true Path Truth panel.

### Execution Reality

Current visibility is partial:

- Visible: paired trade count, BTC/ETH counts, TP/SL counts, 60s+ count, win/loss, blocking gates.
- Partly visible elsewhere: quote age buckets in wide/fullscreen, orderbook age in market cards, executable book/spread state, depth and fill-dollar proxy.
- Missing or not explicit: signal trades, dust trades, executable trades, execution mode, MOS, edge state, submit/fill realism labels, paper-vs-live truth labels, and whether a trade was signal-grade or only evidence-grade.

The panel title says "Execution Reality", but the current content is closer to an evidence-readiness gate. It does not yet explain executable EV truth.

### Header

Already visible:

- run id
- mode
- data status
- readiness
- Phase6
- S3
- JSONL status

Missing:

- current research phase: `PATH_TRUTH / EVIDENCE_FARMING`
- path truth gate label: `INSUFFICIENT_DATES`, `EARLY_RESEARCH_GATE`, or `IMPLEMENTATION_GATE`
- completed-date progress: `1/3` and `1/7`
- active UTC session bucket, for example `02h`, `09h10h`, or `other`

The header is the best place for non-negotiable research context because it remains visible in compact mode.

### Candidate Diagnostics

Already visible:

- why blocked, via main blocker labels
- lifecycle phase
- EV/probability visibility
- orderbook/liquidity readiness
- cutoff and age

Missing:

- BTC state: `BTC_HOSTILE_CANDIDATE`, `BTC_RECOVERY`, or `INSUFFICIENT_SAMPLE`
- NO state: `NO_SESSION_DEPENDENT`, `02h_NO_HOSTILE`, or `INSUFFICIENT_SAMPLE`
- session state: `02h_HOSTILE`, `09h10h_EDGE_CANDIDATE`, or `NEUTRAL`
- EV state as a compact operator label, not only a numeric EV
- confidence state tied to research sample size and date coverage

This is the most important local gap: the operator sees why the current candidate was blocked, but not whether the candidate sits inside a known research-risk triangle.

## Proposed Operator Console Panels

### 1. Header Research Strip

Priority: P0

Compact content:

```text
PHASE PATH_TRUTH | GATE 1/3A 1/7B INSUFF | UTC 02h HOSTILE | RUN <id>
```

Operator value:

- keeps research phase visible at all times
- prevents accidental interpretation of path-truth data as implementation-ready
- makes hostile/edge session context visible before reading any panel

### 2. Session Intelligence Panel

Priority: P0

Fields:

| Field | Example |
|---|---|
| current UTC bucket | `02h`, `09h10h`, `other` |
| session label | `HOSTILE_SESSION_CANDIDATE`, `SESSION_EDGE_CANDIDATE`, `NEUTRAL_OR_UNKNOWN` |
| BTC label | `BTC_HOSTILE_CANDIDATE`, `BTC_09H10H_RECOVERY_CANDIDATE`, `INSUFFICIENT_SAMPLE` |
| NO label | `NO_SESSION_DEPENDENT`, `02h_NO_HOSTILE`, `INSUFFICIENT_SAMPLE` |
| confidence | `LOW`, `MEDIUM`, `HIGH` based on dates/trades |
| sample hint | `02h 0/12`, `BTC 0/10`, `NO path 2/13` |

Operator value:

- turns research memory into situational awareness
- reduces blind operation during known hostile windows
- keeps labels research-only instead of turning them into automatic gates

### 3. Path Truth Panel

Priority: P0

Fields:

| Field | Why |
|---|---|
| path truth trades | shows evidence growth |
| full coverage | confirms long-enough path checkpoint coverage |
| fast close | explains partial coverage |
| 0-15s, 15-30s, 60s+ buckets | makes fast-close distribution visible |
| `event_end` count | confirms terminal path record is present |
| parse errors / duplicates | writer health |
| Stage A / Stage B progress | prevents premature field wiring |

Compact example:

```text
Path 46tr | full 3 | fast 43 | 0-15 high | gate 1/3A 1/7B
```

Operator value:

- distinguishes data-quality failure from real fast-close behavior
- makes evidence-farming progress visible without opening docs
- aligns operator expectations with the gate policy

### 4. Execution Reality Panel v2

Priority: P1

Fields:

| Field | Source category | Notes |
|---|---|---|
| signal trades | future aggregate | trades from strategy signal path |
| dust trades | future aggregate | tiny/not-actionable evidence rows |
| executable trades | future aggregate | trades satisfying executable-size/liquidity criteria |
| mode | existing runtime mode | paper/live/paper-simulated label |
| MOS | future margin-of-safety field | display-only until scoped |
| edge state | existing/future EV fields | `POSITIVE`, `THIN`, `NEGATIVE`, `UNKNOWN` |
| quote age buckets | quote age panel | should be visible in standard/compact summary too |

Operator value:

- separates "a trade happened" from "a trade was executable-quality evidence"
- protects against overclaiming EV from paper fills
- prepares console language for later latency/fill-truth work

### 5. Candidate Diagnostics v2

Priority: P1

Add one compact research-context row:

```text
Ctx BTC=HOSTILE? NO=WEAK? SESSION=02h_HOSTILE EV=POS CONF=LOW
```

Fields:

- blocker
- BTC state
- NO state
- session state
- EV state
- confidence/sample state

Operator value:

- explains not just why this candidate is blocked, but why the current candidate context is risky or interesting
- reduces context switching from console to research docs

### 6. Research Cockpit Mount

Priority: P2

The existing `_quant_research_panel()` can become useful if mounted selectively, but its current content is older than the path-truth phase. It should not be the first panel promoted as-is.

Recommended use:

- mount only in `wide` or `fullscreen`
- repurpose or supplement it with session intelligence and path-truth fields
- keep it read-only and fed by precomputed in-memory summaries, not disk scans from the render loop

Operator value:

- gives advanced operators a richer research view without crowding compact mode
- avoids rebuilding UI primitives that already exist

## Proposed Layout

### Compact Mode

Goal: preserve current fit while adding research awareness.

Proposed shape:

```text
Header:
  MODE | RUN | PHASE PATH_TRUTH | GATE 1/3A 1/7B | SESSION label

Top:
  Portfolio | Risk

Center:
  Market Scan

Bottom:
  Session Intel | Path Truth | Candidate Diagnostics
```

Feasibility: high, if each bottom panel is limited to 3 compact rows. Existing compact mode already supports three bottom panels, so this is a content swap or consolidation problem rather than a layout invention.

### Standard Mode

Proposed shape:

```text
Top:
  System | Portfolio | Risk

Center:
  BTC Market | ETH Market

Bottom:
  Session Intel | Path Truth | Execution Reality v2
```

Candidate diagnostics can remain visible by folding its most important context row into the market cards or rotating with Execution Reality.

### Wide / Fullscreen

Proposed shape:

```text
Top:
  System | Portfolio | Risk

Center:
  BTC Market | ETH Market | Recent Decisions

Bottom:
  Session Intel | Path Truth | Execution Reality v2 | Logs/Quote Age

Optional:
  Research Cockpit mounted as a full-width lower/alternate view
```

Feasibility: medium. Wide/fullscreen already have Quote Age and Rolling Logs, but a fourth research panel increases crowding. Best path is either a mode toggle later or a compact "Operator Intel" panel that combines Session Intelligence + Path Truth.

### Mobile Fit Later

No implementation now.

Mobile should be a future single-column stack:

1. Header strip
2. Session/Gate chip row
3. BTC/ETH cards
4. Path Truth card
5. Candidate Diagnostics card
6. Execution Reality card

Do not start mobile work until the terminal compact information hierarchy is frozen.

## Priority Tiers

### P0 - Operator Must See

- header phase and gate: `PATH_TRUTH`, `1/3`, `1/7`, verdict
- current UTC session label: `02h_HOSTILE`, `09h10h_EDGE`, or `NEUTRAL`
- BTC and NO research caution labels with sample confidence
- path truth trades, full coverage, fast close, and gate progress

Reason: these are the fastest ways to prevent research-blind operation.

### P1 - High Value During Evidence Farming

- fast-close buckets: 0-15s, 15-30s, 60s+
- `event_end` count
- parse errors and duplicate keys
- signal/dust/executable trade split
- edge state and MOS label
- candidate diagnostics research-context row

Reason: these help interpret whether evidence quality is improving without implying runtime enforcement.

### P2 - Advanced Research Console

- mounted Research Cockpit panel
- 02h vs 09h10h mini matrix
- BTC/NO/session/lifecycle interaction cells
- quote-age distribution by TP/SL and asset
- research frontier/unknown labels

Reason: useful, but it can crowd the console and should be secondary to P0 visibility.

### P3 - Later UX

- mobile layout
- panel toggles
- historical trend sparkline
- deep drilldown views
- offline dashboard integration

Reason: valuable after field definitions and compact terminal hierarchy stabilize.

## Compact Mode Feasibility

Compact mode can support the audit goal if the UI uses labels instead of tables:

```text
Sess 02h HOSTILE | BTC 0/10 | NO 2/13 | conf LOW
Path tr=46 full=3 fast=43 | 0-15 HIGH | gate 1/3A
Cand BTC=warn NO=warn Sess=hostile EV=pos c=.62
```

Do not attempt to show full matrices in compact mode. The operator needs alerting context, not a research table.

## Operator Value

The current UI is operationally useful for live market state. The missing layer is research memory:

- "Is this hour known hostile?"
- "Is this side weak right now?"
- "Is BTC weakness active or partially escaping?"
- "Are path truth rows complete enough to trust?"
- "Are fast closes normal behavior or missing data?"
- "Why is field wiring still blocked?"

Adding those labels would reduce operator cognitive load and make the console reflect the actual research phase.

## Three Future Options

### Option 1 - Safe EV Preservation

Keep the console mostly unchanged and add only header/gate/session labels plus a compact Path Truth summary.

Likely outcome: fastest operator value with the least layout risk.

Hidden risk: too little detail may still force operators back into docs.

Recommended action: use this as the first implementation blueprint later, once a UI task is explicitly opened.

### Option 2 - Aggressive Information Discovery

Add a dedicated Operator Intel panel that combines Session Intelligence, Path Truth, and Candidate Context in compact/standard/wide modes.

Likely outcome: best learning loop during evidence farming.

Hidden risk: panel overcrowding, especially in compact terminals.

Recommended action: prototype only after P0 labels are agreed, and keep it display-only.

### Option 3 - Structural / Root-Cause Path

Design a formal research-state provider that precomputes console-ready labels from JSONL/docs outside the render loop.

Likely outcome: cleaner long-term architecture for operator intelligence.

Hidden risk: provider freshness, stale research labels, and accidental policy coupling if boundaries are not explicit.

Recommended action: plan this separately if the console becomes the main research command center.

## Recommended Next Step

Do not implement yet.

For a future scoped UI task, start with P0 only:

1. Header research strip.
2. Session Intelligence compact labels.
3. Path Truth compact panel.
4. Candidate Diagnostics context row.

Keep all fields observability-only, additive, fail-soft, and clearly labeled as research evidence. Do not wire any label into strategy, risk, execution, stops, sizing, or live behavior.

## Final Status

Files created:

- `docs/research/runtime_ui_observability_gap_audit.md`

Files modified:

- none beyond this documentation artifact

Tests run: none; read-only research/design audit.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No
