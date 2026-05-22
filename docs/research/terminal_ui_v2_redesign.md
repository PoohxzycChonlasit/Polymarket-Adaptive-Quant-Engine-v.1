# Terminal UI V2 Redesign Audit

Document type: read-only terminal UI design audit.

Date: 2026-05-22

Scope: design only.

Runtime behavior changed: No.

Live behavior changed: No.

Code changed: No.

Paper launch: No.

Replay run: No.

S3 promotion: No.

Persistent tests changed: No.

---

## Role Routing

Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`

Supporting role: `07_TEST_CI_AGENT.md`

Why selected: the terminal redesign is operator-facing runtime observability. Test guidance is needed for a future implementation, but this task is docs-only.

Files allowed to inspect:

- `CODEX_START_HERE.md`
- `PROJECT_RULES.md`
- `AGENTS.md`
- `MASTER_AGENT_ROUTER.md`
- `CURRENT_PROJECT_STATUS.md`
- `PROJECT_STRUCTURE.md`
- `KNOWN_ISSUES.md`
- `FILE_INDEX.md`
- `QUANT_FUTURE_DECISION_ENGINE.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/KNOWN_ISSUES.md`
- `runtime/research_state/latest_research_state.md`
- `docs/quant_agent_setup_md/roles/11_OBSERVABILITY_INCIDENT_AGENT.md`
- `docs/quant_agent_setup_md/roles/07_TEST_CI_AGENT.md`
- `utils/display.py`
- `main.py`
- `tests/test_terminal_dashboard_display.py`
- `docs/research/execution_reality_daily_monitor.md`
- `docs/research/sessions/2026-05-22/phase5_evidence_monitor.md`
- `docs/research/research_cockpit_ui_redesign_v1.md`

Files intentionally ignored:

- Strategy modules.
- Risk sizing implementation.
- Execution/order placement implementation.
- Wallet/live config and `.env`.
- Raw JSONL/log folders.
- Replay tools and generated reports.
- Web dashboard code.

---

## Source Evidence Summary

Current terminal UI implementation:

- `utils/display.py` owns `PolymarketRealtimeDisplay`.
- It uses Rich `Live`, `Layout`, and `Panel`.
- It supports `--ui auto|compact|standard|wide|fullscreen`.
- It supports `--fps low|medium|high`.
- It falls back to compact mode when terminal size is below minimum.
- Current panels include System Status, Portfolio, Risk, Market Scan or BTC/ETH Market cards, Recent Decisions / Timing, Decision Diagnostics, Research Cockpit, Execution, and Rolling Logs.
- Current footer shows compact health fields such as data status, mode, risk, tier, blocker, latency, and JSONL.

Current runtime UI update path:

- `main.py` creates `PolymarketRealtimeDisplay(...)` in `run_polymarket_realtime`.
- `main.py` passes `ui_mode` and `fps_mode` from CLI flags.
- Every 1 second, the loop updates countdown, portfolio, session summary, recent trades, oracle/PTB state, market display metrics, WebSocket status, and batch market updates.
- Every configured decision interval, the loop runs `trader.run_single_cycle(...)`, refreshes portfolio/session state, calls `update_research_obs(...)`, updates market cards, adds display trades when orders are placed, writes scan records, and updates cycle results.

Execution reality monitor evidence:

- Current clean outcome-truth aggregation is 9 confirmed paired trades.
- Asset split is BTC 1 and ETH 8.
- TP/WIN count is 3 and SL/LOSS count is 6.
- Mean PnL is -0.005455.
- Mean submit quote age is 18.987s.
- Mean fill quote age is 18.990s.
- Quote-age bucket counts are 0-5s: 2, 5-15s: 9, 15-30s: 3, 30-60s: 3, 60s+: 1.
- Phase 6 readiness is 65.0%.
- Phase 6 remains blocked because paired trades, BTC trades, and TP outcomes are below gates.
- `market_analysis_exception` must remain an alert-class field.

---

## Root Problem

The existing terminal UI is useful but hard to read in the Execution Reality era. It shows many raw diagnostic signals at once, while the operator's first questions are now narrower:

- Is this run paper or live?
- Which run is this?
- Is evidence readiness improving?
- Which Phase 6 gates are blocking?
- Are BTC and ETH both represented?
- Are TP/SL and WIN/LOSS directly confirmed?
- Are quotes stale at submit or fill?
- Is the current market runtime safe, active, or degraded?
- Which alert requires attention right now?

The current UI mixes runtime market state, research probes, lifecycle diagnostics, execution events, and logs across panels. The result is information-rich but not decision-shaped. The redesign should keep the same Rich terminal surface, but reorganize it around operator triage and execution reality.

---

## Current Terminal Pain Points

1. Readiness is not first-class.

   The current header and footer show data health, mode, risk, blocker, latency, and JSONL. They do not make Phase readiness, readiness percent, S3 status, and blocking gates impossible to miss.

2. Execution reality is split across panels.

   Recent trades appear in Execution, decision state appears in Recent Decisions / Timing, quote age is not first-class, and paired trade evidence is not summarized as an operator count.

3. Research Cockpit is dense.

   The current Research Cockpit panel compresses regime, lifecycle, S3, economics, health, anomalies, and runtime into one block. That is good for development, but too noisy for live paper monitoring.

4. Quote freshness is not shaped around submit/fill truth.

   The Execution Reality era needs `quote_age_at_submit_ms`, `quote_age_at_fill_ms`, and bucket distribution to be visible without reading JSONL or Markdown reports.

5. Alerts are implicit.

   Low BTC diversity, stalled TP outcomes, Phase 6 blocked/near-ready, `market_analysis_exception`, orderbook unavailable, and stale quote warnings should be promoted into a compact alert strip.

6. Missing fields can look like zeros.

   Some numeric defaults in display state are `0.0`, which is safe for rendering but risky for interpretation. The redesigned UI must label unsupported or absent evidence as `n/a`, `missing`, or `unsupported`, not as zero progress.

7. Windows terminal readability needs ASCII-first shapes.

   The UI should rely on text labels, ASCII bars, and simple arrows (`^`, `v`, `->`) rather than glyphs that may render poorly in Windows terminal fonts.

8. Current market cards are too verbose for first-screen triage.

   BTC/ETH cards show many fields: oracle, PTB, YES/NO bid/ask, source, token, model probabilities, regime, EV, timing, cutoff, micro, liquidity, lifecycle, depth, readiness, preload, replay IDs, and latency. The redesign should preserve drilldown but make first-screen market runtime simpler.

---

## Design Goal

Create an in-terminal Execution Reality dashboard that answers the operator's status questions in one compact screen:

```text
Can I trust the evidence?
Is Phase 6 blocked or near-ready?
What changed since the prior update?
Are quote ages fresh, aging, or stale?
Is BTC/ETH market runtime healthy?
Are there active alerts?
```

This is a display-layer redesign only. It must not:

- Read from the web dashboard.
- Run replay.
- Launch paper.
- Promote S3.
- Change strategy, risk, execution, wallet, paper/live behavior, or live config.
- Treat offline analyzer output as runtime authority.

---

## Traffic Light Semantics

Use both color and label so screenshots remain readable without color.

| Light | Label | Meaning |
|---|---|---|
| GREEN | OK / MET / READY | Direct evidence exists and the target is satisfied. |
| YELLOW | WATCH / PARTIAL / ACCUM | Evidence exists but is below threshold, thin, stale, or inconclusive. |
| RED | BLOCK / FAIL / UNSAFE | Missing required direct evidence, invalid source, market unsafe, or live-risk ambiguity. |
| GRAY | N/A / MISSING | Field is unsupported, absent, or not applicable. |
| BLUE | INFO | Context only, not a gate. |

Operator rule: never show a green gate without its interpretation. Example: `60s+ 1/1 GREEN coverage` can coexist with `stale relation YELLOW inconclusive`.

---

## Simple Bars

Use fixed-width ASCII bars.

```text
bar_width = 20
filled = floor(min(current / target, 1.0) * bar_width)
bar = "[" + "#" * filled + "-" * (bar_width - filled) + "]"
```

Examples:

```text
Paired  9/20 [#########-----------] 45% WATCH
BTC     1/5  [####----------------] 20% WATCH
TP      3/5  [############--------] 60% WATCH
SL      6/5  [####################] 100% MET capped
60s+    1/1  [####################] 100% MET coverage
```

Fallback behavior:

- If target is missing: show `[n/a]`.
- If current is missing: show `n/a`, not `0`.
- If value is stale: show the last value with `STALE`.
- If value is unsupported: show `unsupported`.

---

## Trend Arrows

Use ASCII arrows:

| Arrow | Label | Meaning |
|---|---|---|
| `^` | UP | Current value increased since previous update. |
| `v` | DOWN | Current value decreased since previous update. |
| `->` | FLAT | Current value unchanged. |
| `?` | UNKNOWN | Previous value unavailable or field missing. |

Trend arrows show monitor-to-monitor movement only. They must not imply statistical significance.

Examples:

```text
Paired     8 -> 9    ^ +1
BTC        0 -> 1    ^ +1
TP         3 -> 3    -> stalled
Readiness 60 -> 65   ^ +5.0 pp
```

---

## Proposed Layout

Recommended first implementation target: replace the current first-screen emphasis with this layout in wide/fullscreen mode, then derive compact/standard variants.

```text
+----------------------------------------------------------------------------------------------+
| PolyTrade Execution Reality | PAPER | run 20260522T130017Z_21712_035b3af7 | git dirty        |
| Ready 65.0% WATCH | Phase6 BLOCKED | S3 READY | DATA OK | JSONL OK | NO LIVE ORDERS        |
+----------------------------------------------------------------------------------------------+
| Execution Reality                 | Quote Age                         | Trend              |
| Paired 9/20 [#########-----------] | submit mean 18.987s WATCH         | Paired 8->9 ^ +1   |
| BTC    1/5  [####----------------] | fill   mean 18.990s WATCH         | BTC    0->1 ^ +1   |
| ETH    8/5  [####################] | 0-5s   2 [##------------------]    | TP     3->3 -> 0   |
| TP     3/5  [############--------] | 5-15s  9 [##########----------]    | Ready 60->65 ^ +5  |
| SL     6/5  [####################] | 15-30s 3 [###-----------------]    |                    |
| WIN 3 LOSS 6 | 60s+ 1 MET coverage | 30-60s 3 [###-----------------]   |                    |
| Gates: paired,BTC,TP              | 60s+   1 [#-------------------]    | delta since prev   |
+----------------------------------------------------------------------------------------------+
| Alerts                                      | Market Runtime                                      |
| [YELLOW] BTC diversity low 1/5              | BTC conf 0.00 | ob OK | phase ACTIVE | pos 0        |
| [YELLOW] TP stalled 3/5                     | ETH conf 0.00 | ob OK | phase ACTIVE | pos 0        |
| [YELLOW] Phase6 blocked: paired,BTC,TP      | PnL -0.0055 | exposure 0.0% | risk NORMAL       |
| [GREEN] market_analysis_exception 0         | lifecycle OPENING_SCAN/ACTIVE/PROFIT/FINAL/UNSAFE  |
+----------------------------------------------------------------------------------------------+
| Footer: MODE PAPER | DATA OK | RISK NORMAL | ORDERBOOK OK | QUOTE WATCH | BLOCKER paired/BTC/TP |
+----------------------------------------------------------------------------------------------+
```

Compact mode should stack sections:

```text
HEADER
EXECUTION REALITY
ALERTS
MARKET RUNTIME
FOOTER
```

Standard mode should use two columns:

```text
HEADER
left: Execution Reality + Trend
right: Quote Age + Alerts
Market Runtime
FOOTER
```

Wide/fullscreen mode should use three columns:

```text
HEADER
Execution Reality | Quote Age | Trend
Alerts            | Market Runtime | Recent Execution
FOOTER
```

---

## Section Design

### 1. Header

Purpose: make mode, identity, readiness, phase, and safety status visible before any details.

Required fields:

- Mode.
- Run ID.
- Git status if available.
- Readiness percent.
- Phase status.
- S3 status.
- Data/orderbook/JSONL summary.
- Paper/live safety marker.

Example:

```text
PolyTrade Execution Reality | PAPER | run 20260522T130017Z_21712_035b3af7 | git dirty
Ready 65.0% WATCH | Phase6 BLOCKED | S3 READY | DATA OK | JSONL OK | NO LIVE ORDERS
```

Git status rule:

- `clean`: show `git clean`.
- dirty worktree: show `git dirty`.
- git unavailable: show `git n/a`.
- command failure: show `git unknown`.

Do not block terminal rendering on git status. Cache it and refresh slowly if implemented later.

Fallbacks:

| Field | Fallback |
|---|---|
| mode | infer from `paper_trading`; else `UNKNOWN` |
| run_id | `run n/a` |
| git status | `git n/a` |
| readiness percent | `Ready n/a` |
| phase status | `Phase n/a` |
| S3 status | `S3 n/a` |
| data status | existing `_data_status_tag()` |
| safety marker | `NO LIVE ORDERS` in paper; `LIVE MODE` in live |

### 2. Execution Reality

Purpose: show outcome-truth gate progress and blocker state.

Required fields:

- Paired trades.
- BTC / ETH.
- TP / SL.
- WIN / LOSS.
- 60s+ count.
- Readiness gates.

Example:

```text
Execution Reality
Paired 9/20 [#########-----------] 45% WATCH
BTC    1/5  [####----------------] 20% WATCH
ETH    8/5  [####################] 100% MET capped
TP     3/5  [############--------] 60% WATCH
SL     6/5  [####################] 100% MET capped
WIN 3 | LOSS 6 | mean PnL -0.005455 WATCH
60s+ quote-age fills 1/1 MET coverage; relation WATCH inconclusive
Blocking gates: paired, BTC, TP
```

Fallbacks:

- Missing paired count: `Paired n/a [n/a] MISSING`.
- Missing asset split: `BTC n/a | ETH n/a`.
- Missing `trade_result`: show `TP/SL unsupported`, do not infer.
- Missing `pnl_usdc`: show `WIN/LOSS unsupported`, do not infer.
- Missing readiness target: show count only.

### 3. Quote Age

Purpose: show quote freshness at submit/fill and bucket distribution.

Required fields:

- `quote_age_at_submit_ms`.
- `quote_age_at_fill_ms`.
- Buckets:
  - 0-5s
  - 5-15s
  - 15-30s
  - 30-60s
  - 60s+

Example:

```text
Quote Age
submit mean 18.987s WATCH
fill   mean 18.990s WATCH
0-5s    2 [##------------------] 11.1%
5-15s   9 [##########----------] 50.0%
15-30s  3 [###-----------------] 16.7%
30-60s  3 [###-----------------] 16.7%
60s+    1 [#-------------------] 5.6% coverage MET, relation WATCH
```

Bucket interpretation:

- GREEN only after a bucket has enough paired closes and a stable relationship.
- YELLOW for thin or contradictory samples.
- RED only if stale buckets repeatedly concentrate losses after a defined minimum.
- GRAY when bucket has no paired closes.

Fallbacks:

- Missing submit age: `submit age n/a`.
- Missing fill age: `fill age n/a`.
- Missing bucket counts: `bucket distribution n/a`.
- If submit/fill ages are present but bucket outcomes are missing, show quote-age coverage but hide outcome interpretation.

### 4. Trend

Purpose: show deltas since the previous terminal refresh or monitor baseline.

Required fields:

- Paired trend.
- BTC trend.
- TP trend.
- Readiness trend.
- Delta since previous update.

Example:

```text
Trend
Paired     8 -> 9    ^ +1
BTC        0 -> 1    ^ +1
TP         3 -> 3    -> stalled
Readiness 60.0 -> 65.0 ^ +5.0 pp
```

Fallbacks:

- Missing prior point: `? first point`.
- Missing current point: `n/a`.
- Non-numeric field: do not render a trend arrow.

### 5. Alerts

Purpose: promote operator action items above passive diagnostics.

Required alerts:

- BTC diversity low.
- TP stalled.
- Phase6 blocked/near-ready.
- `market_analysis_exception`.
- Orderbook unavailable.
- Stale quote warning.

Example:

```text
Alerts
[YELLOW] BTC diversity low: 1/5
[YELLOW] TP stalled: 3/5, delta 0
[YELLOW] Phase6 blocked: paired,BTC,TP
[GREEN] market_analysis_exception: 0
[GREEN] orderbook available: BTC,ETH
[YELLOW] stale quote relation inconclusive: 60s+ sample 1
```

Severity rules:

| Alert | GREEN | YELLOW | RED |
|---|---|---|---|
| BTC diversity low | BTC >= target | 0 < BTC < target | BTC missing or 0 after enough paired trades |
| TP stalled | TP >= target | TP below target or flat | TP field missing in outcome era |
| Phase6 status | all gates met | blocked by evidence gaps | invalid/era-mixed source |
| market_analysis_exception | count 0 | count > 0 but non-fatal | repeated/current-cycle exception |
| orderbook unavailable | BTC/ETH OK | one asset degraded | both unavailable/stale |
| stale quote warning | no stale risk or enough stable evidence | thin/inconclusive stale sample | repeated stale losses after threshold |

Fallbacks:

- Missing alert source: show `[GRAY] alert source n/a`.
- Never suppress a red alert because another section is green.

### 6. Market Runtime

Purpose: keep live market state readable without turning the terminal into a debug dump.

Required fields:

- BTC confidence.
- ETH confidence.
- Orderbook availability.
- Current lifecycle phase.
- PnL.
- Active positions.

Example:

```text
Market Runtime
BTC conf 0.61 | orderbook OK | phase ACTIVE | quote age 0.8s | blocker none
ETH conf 0.58 | orderbook OK | phase ACTIVE | quote age 1.1s | blocker spread_too_wide
PnL realized -0.0055 | unrealized 0.0000 | exposure 0.0% | active positions 0
Risk NORMAL | source paper_virtual | NO LIVE ORDERS
```

Fallbacks:

- Missing confidence: `conf n/a`.
- Missing orderbook: `orderbook UNKNOWN`.
- Missing lifecycle phase: `phase UNKNOWN`.
- Missing PnL: `PnL n/a`.
- Missing positions: `positions n/a`.

---

## Field Mapping

### Current Runtime Sources

| UI field | Current source path | Notes |
|---|---|---|
| mode | `PolymarketRealtimeDisplay.paper_trading` | Already available. |
| run_id | `update_run_id(...)` / `_run_id` | Method exists; runtime wiring should confirm it is called. |
| git status | new display-only cached helper | Do not run every refresh. |
| data status | `_data_status_tag()` | Existing helper. |
| orderbook status | `_orderbook_status()` | Existing helper. |
| JSONL status | `_footer_jsonl_compact_tag()` / `_observability_health` | Existing helper/state. |
| S3 status | `_research_obs.s3_status` or `_research_obs.s3_probe_ready` | Existing Research Cockpit uses `s3_probe_ready`. |
| BTC/ETH confidence | `_markets[ticker].confidence` | Populated from metrics/outcomes. |
| orderbook age | `_markets[ticker].orderbook_age_ms` | Existing market cards. |
| lifecycle phase | `_markets[ticker].lifecycle_phase` or cycle result | Existing field in defaults. |
| PnL | `_session_summary`, `_portfolio` | Need consistent preference order. |
| active positions | `_portfolio.open_count` / `_recent_trades` | Prefer portfolio open count. |

### Execution Reality Sources

These fields may not yet be part of the live display state. Future implementation should introduce a display-only summary object, not parse large logs inside `utils/display.py`.

Recommended new in-memory state:

```python
_execution_reality: dict[str, object] = {
    "readiness_pct": None,
    "phase_status": "",
    "paired_trades": None,
    "paired_target": 20,
    "btc_trades": None,
    "btc_target": 5,
    "eth_trades": None,
    "eth_target": 5,
    "tp_count": None,
    "tp_target": 5,
    "sl_count": None,
    "sl_target": 5,
    "win_count": None,
    "loss_count": None,
    "mean_pnl_usdc": None,
    "quote_age_submit_mean_ms": None,
    "quote_age_fill_mean_ms": None,
    "quote_age_buckets": {},
    "sixty_plus_count": None,
    "market_analysis_exception_count": None,
    "previous": {},
    "updated_at": "",
}
```

This object should be populated by an explicit update method in a future implementation, for example:

```python
display.update_execution_reality(**summary)
```

Do not make terminal rendering scan JSONL, reports, or Markdown files directly.

### Monitor Field Mapping

| Terminal field | Monitor field / current value |
|---|---|
| readiness percent | Phase 6 readiness: 65.0% |
| phase status | `ACCUMULATING` / `COLLECT_MORE_EVIDENCE` / blocked gates |
| paired trades | 9/20 |
| BTC trades | 1/5 |
| ETH trades | 8/5 |
| TP / WIN | 3/5 |
| SL / LOSS | 6/5 |
| WIN / LOSS split | 3 / 6 |
| mean PnL | -0.005455 |
| mean submit quote age | 18.987s |
| mean fill quote age | 18.990s |
| 0-5s bucket | 2 |
| 5-15s bucket | 9 |
| 15-30s bucket | 3 |
| 30-60s bucket | 3 |
| 60s+ bucket | 1 |
| paired trend | 8 -> 9, `^ +1` |
| BTC trend | 0 -> 1, `^ +1` |
| TP trend | 3 -> 3, `-> 0` |
| readiness trend | 60.0 -> 65.0, `^ +5.0 pp` |

---

## Fallback Behavior

The redesigned terminal must degrade safely when fields are missing.

Rules:

1. Missing means unknown, not zero.
2. Unsupported means unsupported, not failed.
3. Stale means stale, not current.
4. Offline/research summaries must be visibly labeled if shown.
5. Readiness must not be green unless all required direct fields are present.
6. Header must still render if every new Execution Reality field is absent.
7. Terminal rendering must not throw when values are `None`, strings, malformed numbers, or empty mappings.

Fallback labels:

| Condition | Display |
|---|---|
| Missing numeric field | `n/a` |
| Missing string field | `--` |
| Missing gate target | `target n/a` |
| Missing current and target | `[n/a]` |
| Field not implemented | `unsupported` |
| Report freshness unknown | `freshness n/a` |
| Previous trend unavailable | `? first point` |
| Git unavailable | `git n/a` |

Example missing-state screen:

```text
PolyTrade Execution Reality | PAPER | run n/a | git n/a
Ready n/a | Phase n/a | S3 n/a | DATA DEGRADED | JSONL OK | NO LIVE ORDERS

Execution Reality
Paired n/a [n/a] MISSING
BTC n/a | ETH n/a | TP/SL unsupported | WIN/LOSS unsupported
Blocking gates: evidence unavailable

Quote Age
submit age n/a | fill age n/a | buckets n/a

Alerts
[GRAY] execution reality summary not populated
```

---

## What Not To Show In Terminal

Keep the terminal compact and operational. Do not show:

- Raw JSONL payloads.
- Full orderbooks.
- Private keys, wallet secrets, API keys, or full wallet identifiers.
- Full `condition_id`, token IDs, or market slugs unless in explicit debug/fullscreen detail.
- Long Markdown monitor tables.
- Web dashboard links as required dependencies.
- Full replay report contents.
- Strategy internals that imply trade approval.
- Raw exception tracebacks in the main panel; show alert summary and route traceback to logs.
- Any text implying Phase 6 promotion when gates remain below target.
- Any text implying live readiness while allowance/execution/reconciliation remain unvalidated.
- Any stale-quote threshold recommendation derived from the current thin sample.

---

## Implementation Phases

### Phase A - Display Contract Only

Add a display-only execution reality state object and `update_execution_reality(...)`.

No JSONL reads, no report parsing, no strategy changes, no risk changes, no live changes.

Deliverables:

- State defaults.
- Safe numeric/string formatting helpers.
- Bar helper.
- Trend helper.
- Traffic-light helper.
- Unit tests for missing values.

### Phase B - Header And Footer

Add readiness, phase, S3, run_id, and optional cached git status to the header/footer.

Deliverables:

- Header renders with and without new fields.
- Git status is optional and fail-soft.
- Paper mode still shows `NO LIVE ORDERS`.
- Live mode remains explicit and visually red.

### Phase C - Execution Reality And Quote Age Panels

Add the two core panels.

Deliverables:

- Gate bars.
- TP/SL and WIN/LOSS summary.
- Quote-age mean submit/fill fields.
- Bucket distribution.
- 60s+ coverage versus interpretation split.

### Phase D - Trend And Alerts Panels

Add trend arrows and alert generation from display state.

Deliverables:

- Paired/BTC/TP/readiness deltas.
- BTC diversity alert.
- TP stalled alert.
- Phase6 blocked/near-ready alert.
- `market_analysis_exception` alert.
- Orderbook unavailable alert.
- Stale quote warning.

### Phase E - Market Runtime Simplification

Condense the first-screen BTC/ETH runtime rows while preserving detailed market cards in wide/fullscreen drilldown.

Deliverables:

- BTC/ETH confidence.
- Orderbook status.
- Lifecycle phase.
- Quote age/orderbook age.
- PnL and active positions.
- Current blocker.

### Phase F - Runtime Wiring

Wire the state only after the display contract is tested. Prefer a summary already computed by trader/session observability code. Do not make `utils/display.py` read disk.

Deliverables:

- `main.py` calls the new update method only if summary data exists.
- Missing summary keeps the UI stable.
- No paper/live behavior changes.

---

## Tests Needed Before Implementation

Docs-only audit requires no runtime tests now. Future implementation should add or update focused tests.

Required display tests:

- Header renders mode, run_id, readiness percent, phase status, S3 status, and safety marker.
- Header falls back when run_id/git/readiness/S3 fields are absent.
- Execution Reality panel renders gate bars for paired, BTC, ETH, TP, SL, and 60s+.
- Execution Reality panel preserves missing fields as `n/a`, not zero.
- Quote Age panel renders submit/fill mean ages and all five buckets.
- Quote Age panel separates 60s+ coverage met from stale relationship interpretation.
- Trend panel renders `^`, `v`, `->`, and `?`.
- Alerts panel emits BTC diversity low, TP stalled, Phase6 blocked, `market_analysis_exception`, orderbook unavailable, and stale quote warning.
- Market Runtime panel renders BTC/ETH confidence, orderbook availability, lifecycle phase, PnL, and active positions.
- Compact, standard, wide, and fullscreen layouts render without overflow.
- Long alert strings are clipped.
- None/malformed values do not raise.

Required safety tests:

- Paper mode still shows `NO LIVE ORDERS`.
- Live mode still shows explicit live warning styling.
- No new display method calls live APIs.
- No display method reads JSONL/report files.
- Existing `tests/test_terminal_dashboard_display.py` tests continue to pass.

Suggested command for future implementation:

```bash
python -m pytest -q tests/test_terminal_dashboard_display.py
```

Broader tests only if future code touches `main.py` wiring:

```bash
python -m pytest -q tests/test_terminal_dashboard_display.py tests/test_paper_mode.py tests/test_logging_resilience.py
```

Do not run paper, replay, or live verify for the implementation unless a future task explicitly scopes it.

---

## Example Terminal Output

### Current Evidence Example

```text
+------------------------------------------------------------------------------------------------+
| PolyTrade Execution Reality | PAPER | run 20260522T130017Z_21712_035b3af7 | git dirty          |
| Ready 65.0% WATCH | Phase6 BLOCKED | S3 READY | DATA OK | JSONL OK | NO LIVE ORDERS          |
+------------------------------------------------------------------------------------------------+
| Execution Reality                  | Quote Age                         | Trend                |
| Paired 9/20 [#########-----------] | submit mean 18.987s WATCH         | Paired 8->9 ^ +1     |
| BTC    1/5  [####----------------] | fill   mean 18.990s WATCH         | BTC    0->1 ^ +1     |
| ETH    8/5  [####################] | 0-5s    2 [##------------------]   | TP     3->3 -> 0     |
| TP     3/5  [############--------] | 5-15s   9 [##########----------]   | Ready 60->65 ^ +5pp  |
| SL     6/5  [####################] | 15-30s  3 [###-----------------]   |                      |
| WIN 3 LOSS 6 mean PnL -0.005455    | 30-60s  3 [###-----------------]   | delta since previous |
| 60s+ 1/1 MET coverage, WATCH rel   | 60s+    1 [#-------------------]   |                      |
+------------------------------------------------------------------------------------------------+
| Alerts                                     | Market Runtime                                      |
| [YELLOW] BTC diversity low: 1/5            | BTC conf n/a | ob OK | phase UNKNOWN | pos 0       |
| [YELLOW] TP stalled: 3/5, delta 0          | ETH conf n/a | ob OK | phase UNKNOWN | pos 0       |
| [YELLOW] Phase6 blocked: paired,BTC,TP     | PnL -0.0055 | exposure n/a | risk NORMAL          |
| [GREEN] market_analysis_exception: 0       | source paper_virtual | NO LIVE ORDERS                  |
| [YELLOW] stale quote relation inconclusive |                                                     |
+------------------------------------------------------------------------------------------------+
| MODE PAPER | DATA OK | RISK NORMAL | ORDERBOOK OK | QUOTE WATCH | BLOCKER paired/BTC/TP    |
+------------------------------------------------------------------------------------------------+
```

### Missing Fields Example

```text
+------------------------------------------------------------------------------------------------+
| PolyTrade Execution Reality | PAPER | run n/a | git n/a                                      |
| Ready n/a | Phase n/a | S3 n/a | DATA DEGRADED | JSONL OK | NO LIVE ORDERS               |
+------------------------------------------------------------------------------------------------+
| Execution Reality                  | Quote Age                         | Trend                |
| Paired n/a [n/a] MISSING           | submit age n/a                    | Paired ? first point |
| BTC n/a | ETH n/a                  | fill age n/a                      | BTC    ? first point |
| TP/SL unsupported                  | buckets n/a                       | TP     ? first point |
| WIN/LOSS unsupported               |                                  | Ready  ? first point |
| Blocking gates: evidence missing   |                                  |                      |
+------------------------------------------------------------------------------------------------+
| Alerts                                     | Market Runtime                                      |
| [GRAY] execution reality not populated     | BTC conf n/a | ob UNKNOWN | phase UNKNOWN | pos n/a |
| [GRAY] quote age not populated             | ETH conf n/a | ob UNKNOWN | phase UNKNOWN | pos n/a |
| [GRAY] trend baseline unavailable          | PnL n/a | exposure n/a | risk n/a                    |
+------------------------------------------------------------------------------------------------+
```

### Near-Ready Example

```text
+------------------------------------------------------------------------------------------------+
| PolyTrade Execution Reality | PAPER | run 20260522T235959Z_11111_abcd | git clean          |
| Ready 95.0% WATCH | Phase6 NEAR_READY | S3 READY | DATA OK | JSONL OK | NO LIVE ORDERS        |
+------------------------------------------------------------------------------------------------+
| Execution Reality                  | Quote Age                         | Trend                |
| Paired 20/20 [####################]| submit mean 12.200s OK            | Paired 19->20 ^ +1   |
| BTC    5/5  [####################] | fill   mean 12.300s OK            | BTC    4->5 ^ +1     |
| ETH   15/5  [####################] | 0-5s    6 [######--------------]   | TP     4->4 -> 0     |
| TP     4/5  [################----] | 5-15s  11 [###########---------]   | Ready 90->95 ^ +5pp  |
| SL     8/5  [####################] | 15-30s  4 [####----------------]   |                      |
| WIN 4 LOSS 8 mean PnL n/a          | 30-60s  1 [#-------------------]   | Still blocked by TP  |
| 60s+ 1/1 MET coverage              | 60s+    1 [#-------------------]   |                      |
+------------------------------------------------------------------------------------------------+
| Alerts                                     | Market Runtime                                      |
| [YELLOW] TP below gate: 4/5                | BTC conf 0.62 | ob OK | phase ACTIVE | pos 0       |
| [YELLOW] Phase6 near-ready, not promoted   | ETH conf 0.58 | ob OK | phase ACTIVE | pos 0       |
| [GREEN] BTC diversity met: 5/5             | PnL n/a | exposure 0.0% | risk NORMAL            |
+------------------------------------------------------------------------------------------------+
```

---

## Exactly Three Future Options

## OPTION 1 - SAFE EV PRESERVATION

Thesis: implement the redesign as a display-only state contract and static Rich panels.

Quant logic:

- EV impact: none; display only.
- Risk impact: lowest, because no strategy/risk/execution behavior changes.
- Liquidity impact: none; orderbook state remains read-only display input.
- Fill probability: unchanged.
- Drawdown behavior: unchanged.

Likely outcome: operators can identify Phase 6 blockers, stale quote evidence, and runtime market health faster without changing trading behavior.

Hidden risk: if runtime does not supply an execution reality summary, the UI may show too many `n/a` fields until a later wiring pass.

Recommended action: use this as the next implementation phase.

## OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY

Thesis: wire richer runtime execution reality summaries immediately, including quote-age buckets and outcome truth.

Quant logic:

- Expected data gain: high if summaries are available in memory.
- Expected regime discovery: medium because BTC/ETH split becomes visible.
- Expected volatility interaction: medium if quote age and lifecycle phase are shown together.
- Expected runtime learning: high, but only if fields are trustworthy.

Likely outcome: the terminal becomes more informative sooner, but implementation risk rises if it reaches into reports or JSONL.

Hidden risk: disk reads or report parsing in display code could make the terminal slow, stale, or coupled to offline artifacts.

Recommended action: only choose this after a tested summary producer exists.

## OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

Thesis: create a normalized operator status model before changing terminal rendering.

Quant logic:

- System-level bottleneck: execution reality evidence currently lives in monitors, JSONL summaries, and runtime state rather than one canonical display contract.
- Architecture weakness: display code may become bloated if every new field is added directly to panels.
- Timing distortion: terminal refresh cadence must not be confused with evidence monitor cadence.
- Inventory behavior: future lifecycle and inventory fields need a stable status envelope.
- Execution microstructure: quote age, orderbook age, and liquidity should share freshness semantics.
- Regime mismatch: BTC/ETH sample diversity must remain a gate, not a hidden table.

Likely outcome: cleaner long-term architecture, but slower immediate readability relief.

Hidden risk: building a status model first could become a larger architecture task and delay the urgent terminal readability improvement.

Recommended action: reserve this for a later architecture pass if display-only state starts spreading across modules.

---

## Recommendation

Recommended implementation phase:

```text
OPTION 1 - SAFE EV PRESERVATION
```

Build this as an in-place Terminal UI V2 evolution:

1. Add a display-only execution reality state contract.
2. Add header readiness and safety fields.
3. Add Execution Reality, Quote Age, Trend, Alerts, and Market Runtime sections.
4. Keep all fields fail-soft.
5. Do not read logs, JSONL, reports, or web dashboard data from terminal rendering.
6. Preserve paper/live separation and all existing risk/execution behavior.

Current Phase 6 status remains:

```text
COLLECT_MORE_EVIDENCE
```

Blocked gates:

```text
paired trades, BTC trades, TP outcomes
```

Runtime behavior changed: No.

Live behavior changed: No.
