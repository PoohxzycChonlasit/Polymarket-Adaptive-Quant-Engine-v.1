# Telegram Operator Console Design

Date: 2026-05-24

Scope: docs-only UX design for Telegram operator-facing alerts.

Runtime behavior changed: No

Live behavior changed: No

## Goal

Move Telegram alerts away from raw log copy and toward an operator console style:

- short;
- structured;
- human-scannable on mobile;
- clear about paper vs live;
- clear about signal-only vs executable evidence;
- quiet by default for routine telemetry.

Telegram should answer:

```text
What happened?
Does the operator need to act?
How serious is it?
What mode/evidence class is this?
Where can deeper evidence be found?
```

Telegram should not become a mirror of runtime logs, JSONL, terminal UI, or research dashboards.

## Global Format

Recommended structure:

```text
<emoji> <CATEGORY> | <PRIORITY>
<one-line headline>

Mode: PAPER / LIVE
Asset: BTC / ETH / BOTH / SYSTEM
State: SIGNAL_MODE / DUST_ZONE / EXECUTABLE / UNKNOWN
Action: entered / exited / paused / blocked / observed / needs review

<key fields, 3-6 lines max>

Ref: run_id / trade_id / source_event_id
```

Rules:

- Put the most important operator fact first.
- Use stable category names.
- Use compact labels, not paragraphs.
- Use UTC timestamps only when timing matters.
- Use `PAPER` or `LIVE` near the top.
- Use `SIGNAL_MODE`, `DUST_ZONE`, or `EXECUTABLE` when paper evidence is involved.
- Prefer one alert per meaningful state transition.
- Keep raw diagnostics in JSONL, not Telegram.

## Priority Scale

| Priority | Meaning | Telegram Behavior |
|---|---|---|
| `P0` | Immediate operator risk or runtime failure | send immediately, no broad cooldown except exact duplicate |
| `P1` | Trade lifecycle event or risk pause | send immediately, route-specific cooldown only |
| `P2` | Session intelligence / evidence state changed | digest or bounded cooldown |
| `P3` | Informational / routine health | daily digest only |

## Evidence Labels

| Label | Meaning | Telegram Use |
|---|---|---|
| `SIGNAL_MODE` | Paper signal evidence only; not executable PnL | show on entries/exits/digests |
| `DUST_ZONE` | Order size below practical executable threshold | show when PnL might look misleading |
| `EXECUTABLE_CANDIDATE` | Size/price may be practically executable | show when available, not live-ready claim |
| `EXECUTABLE_CONFIRMED` | Future label only after executable overlay is validated | do not use until proven |
| `SIMULATION_ONLY` | Paper trade cannot support live execution claim | show in digest/research alerts |
| `UNKNOWN_EXECUTABILITY` | Missing size/price/MOS fields | use when evidence incomplete |

## Paper vs Live Differences

| Field | Paper Alert | Live Alert |
|---|---|---|
| Mode label | `Mode: PAPER` | `Mode: LIVE` |
| Execution wording | `simulated fill`, `paper exit` | `live order`, `live fill`, `live exit` |
| PnL wording | `signal PnL` unless executable | `realized/unrealized PnL` |
| Risk tone | evidence-first | operational-risk-first |
| Alert threshold | lower for evidence milestones | higher for noise, immediate for risk |
| Required ref | `run_id`, `trade_id` | `run_id`, `order_id`, `position_id` |

Paper alerts must not imply live readiness or executable profitability.

Live alerts must not hide operational uncertainty.

## Category 1: ENTRY

Purpose: operator sees a new position or simulated position was opened.

Priority:

| Mode | Priority |
|---|---|
| Paper | `P1` |
| Live | `P0/P1` depending on size/risk |

Emoji:

```text
🟢
```

Cooldown:

- no cooldown for actual entry events;
- deduplicate exact `trade_id` / `order_id`;
- no repeated alert for the same fill.

Field order:

1. category + priority;
2. headline: `Entry opened`;
3. mode;
4. asset / side;
5. lifecycle phase;
6. entry price / size / notional;
7. evidence label;
8. quote age / stale metric if available;
9. run/trade reference.

Short form:

```text
🟢 ENTRY | P1
Entry opened

Mode: PAPER
Asset: ETH YES
Phase: OPENING_SCAN
Entry: 0.6200 | Size: 0.09 sh | Notional: $0.05
Evidence: SIGNAL_MODE / DUST_ZONE
Quote stale: 4.2s
Ref: run=... trade=...
```

Verbose form:

- include EV/confidence only if available and safe;
- include `SIMULATION_ONLY` warning for dust trades;
- include orderbook state only if degraded.

Do not include:

- full market slug unless needed;
- raw orderbook;
- all candidate diagnostics;
- repeated "strategy says" prose.

## Category 2: EXIT

Purpose: operator sees TP/SL/forced/settlement close.

Priority:

| Exit Type | Priority |
|---|---|
| TP paper | `P1` |
| SL paper | `P1` |
| forced exit | `P0/P1` |
| live exit failure | `P0` |

Emoji:

```text
✅ TP
🔴 SL
🟠 FORCED
```

Cooldown:

- no cooldown for unique trade exits;
- exact duplicate suppression by `trade_id + exit_reason`;
- aggregate repeated partial exits in a digest if future runner logic creates many fragments.

Field order:

1. category + result;
2. mode;
3. asset / side;
4. result: TP / SL / WIN / LOSS / FORCED;
5. entry -> exit;
6. hold time;
7. PnL label and value;
8. evidence label;
9. quote/path state if available;
10. ref.

Short form:

```text
🔴 EXIT | P1
Stop loss closed

Mode: PAPER
Asset: BTC NO
Result: SL
Price: 0.6100 -> 0.5600
Hold: 12s
Signal PnL: -$0.0045
Evidence: SIGNAL_MODE / DUST_ZONE
Ref: run=... trade=...
```

Verbose form:

- add `quote_stale_ms`;
- add `lifecycle_phase`;
- add `session_hour_utc`;
- add `trade_path_checkpoint` coverage once available.

Do not include:

- every price poll before exit;
- stack traces;
- raw JSON receipt.

## Category 3: RISK / PAUSE

Purpose: operator sees that trading was paused, blocked, limited, or entered a safety state.

Priority:

| Event | Priority |
|---|---|
| LOCKDOWN / live risk block | `P0` |
| paper risk pause | `P1` |
| balance guard | `P1` |
| repeated no-entry reason | `P2` |

Emoji:

```text
🛑 P0
🟡 P1/P2
```

Cooldown:

- 5 minutes for repeated same reason;
- immediate if state escalates;
- send recovery alert when risk state clears.

Field order:

1. risk state;
2. mode;
3. reason;
4. affected asset/session;
5. current gate;
6. operator action if any;
7. ref.

Short form:

```text
🟡 RISK / PAUSE | P1
Trading paused by risk gate

Mode: PAPER
Reason: balance_guard
Asset: BTC
State: ACCUMULATING_EVIDENCE
Action: no operator action
Ref: run=...
```

Do not include:

- repeated per-cycle skip logs;
- all blocked candidates;
- internal risk object dumps.

## Category 4: SESSION INTELLIGENCE

Purpose: operator sees meaningful evidence changes, not every research observation.

Priority:

| Event | Priority |
|---|---|
| session classification change | `P2` |
| hostile session candidate active | `P2` |
| readiness gate crossed | `P2` |
| routine accumulation | `P3/digest` |

Emoji:

```text
🧭
```

Cooldown:

- default 30-60 minutes;
- immediate only when crossing a named research gate;
- otherwise daily digest.

Field order:

1. session label;
2. mode/evidence class;
3. sample count;
4. TP/SL or outcome direction;
5. confidence / caveat;
6. recommended handling;
7. ref doc/run.

Short form:

```text
🧭 SESSION INTELLIGENCE | P2
09h10h edge candidate updated

Mode: PAPER
Evidence: SIGNAL_MODE / DUST_ZONE
Sample: 27 trades
Result: 15 TP / 12 SL
Read: promising, not executable
Ref: session_09h10h_structural_edge
```

Do not include:

- hourly tables;
- full research conclusions;
- raw JSONL counts unless a gate changed.

## Category 5: DAILY DIGEST

Purpose: one compact end-of-day operational + research summary.

Priority:

```text
P3
```

Emoji:

```text
📊
```

Cooldown:

- once daily;
- optional manual resend;
- no repeated hourly digest unless operator asks.

Field order:

1. date / mode;
2. run count / health;
3. trades;
4. TP/SL/WIN/LOSS;
5. signal PnL / executable PnL;
6. evidence labels;
7. best/worst sessions;
8. incidents;
9. next action.

Short form:

```text
📊 DAILY DIGEST | P3
Paper evidence summary

Date: 2026-05-24 UTC
Trades: 18 | TP/SL: 9/9
Signal PnL: +$0.0412
Executable PnL: n/a
Evidence: SIGNAL_MODE / DUST_ZONE
Best: 09h10h, 16h
Watch: 02h HOSTILE_SESSION_CANDIDATE
Incidents: 0
Next: collect more executable evidence
```

Do not include:

- every trade;
- raw path checkpoints;
- per-cycle skip reasons unless top-level blocker.

## Category 6: PATH TRUTH

Purpose: operator sees whether path-truth observability is healthy enough for replay research.

Priority:

| Event | Priority |
|---|---|
| path truth enabled/first checkpoint | `P3/digest` |
| checkpoint writer failure | `P1` |
| coverage gate crossed | `P2` |
| missing checkpoint spike | `P2` |

Emoji:

```text
🧵
```

Cooldown:

- do not alert for every checkpoint;
- summarize checkpoint coverage every 30-60 minutes or daily;
- immediate only for writer failure or coverage collapse.

Field order:

1. path truth status;
2. mode;
3. checkpoint coverage;
4. events written;
5. missing/partial count;
6. replay readiness impact;
7. ref.

Short form:

```text
🧵 PATH TRUTH | P2
Checkpoint coverage updated

Mode: PAPER
Trades tracked: 12
Checkpoints: 42/60
Coverage: PARTIAL
Replay impact: not ready for treatment test
Ref: path_truth/YYYY-MM-DD.jsonl
```

Do not include:

- individual `trade_path_checkpoint` rows;
- bid/ask updates per checkpoint;
- raw path state.

## Category 7: INCIDENT

Purpose: operator sees runtime problems requiring attention.

Priority:

| Incident | Priority |
|---|---|
| runtime crash | `P0` |
| JSONL write failure | `P1` |
| market_analysis_exception | `P1` |
| orderbook unavailable persistent | `P1/P2` |
| Telegram send failure | `P2` unless repeated/critical |

Emoji:

```text
🚨 P0/P1
⚠️ P2
```

Cooldown:

- exact duplicate cooldown: 5 minutes;
- escalation if count increases or new asset affected;
- recovery alert when healthy again.

Field order:

1. incident headline;
2. priority;
3. mode;
4. affected subsystem;
5. asset if applicable;
6. count / first seen / last seen;
7. impact;
8. operator action;
9. ref.

Short form:

```text
🚨 INCIDENT | P1
JSONL writer degraded

Mode: PAPER
Subsystem: path_truth
Impact: checkpoint evidence partial
Trading: unaffected
Action: inspect disk/permissions
Ref: run=...
```

Do not include:

- exception body if it may contain secrets;
- full traceback unless P0 and explicitly sanitized;
- repeated HTTP INFO noise.

## Short vs Verbose Rules

Short alert:

- default for Telegram;
- 8-12 lines max;
- no raw JSON;
- one conclusion line.

Verbose alert:

- only for manual operator request, daily digest, or P0/P1 incidents;
- can include more fields but still no raw orderbooks, secrets, or stack spam;
- should point to docs/JSONL rather than paste them.

Recommended default:

```text
short for ENTRY, EXIT, RISK, PATH_TRUTH
short+summary for SESSION_INTELLIGENCE
structured digest for DAILY_DIGEST
short+action for INCIDENT
```

## Cooldown Matrix

| Category | Default Cooldown | Duplicate Rule |
|---|---:|---|
| ENTRY | none | suppress same `trade_id/order_id` |
| EXIT | none | suppress same `trade_id + reason` |
| RISK / PAUSE | 300s | send escalation/recovery |
| SESSION INTELLIGENCE | 1800-3600s | send only gate changes |
| DAILY DIGEST | 24h | manual resend allowed |
| PATH TRUTH | 1800-3600s | immediate on writer failure |
| INCIDENT | 300s | immediate escalation |

## What The Operator Should See

The operator should see:

- entries and exits;
- risk state changes;
- pauses and recoveries;
- meaningful session intelligence updates;
- once-daily evidence digest;
- path-truth coverage health, not every checkpoint;
- incidents with clear action and impact;
- paper/live mode at the top;
- executable reality labels when PnL is shown.

## What Should Not Spam

Do not send Telegram alerts for:

- every skipped candidate;
- every market snapshot;
- every path checkpoint;
- every orderbook refresh;
- every quote-age update;
- every repeated low-confidence decision;
- every per-cycle status line;
- raw JSONL payloads;
- raw orderbooks;
- full exception tracebacks by default;
- Telegram route telemetry itself except persistent failure.

These belong in JSONL, terminal UI, research docs, or daily digest.

## Safety Rules

Telegram UX must remain:

- fail-soft;
- no secrets;
- no message body leakage in telemetry;
- no trading-loop blocking;
- no strategy changes;
- no risk changes;
- no execution changes;
- no live behavior changes.

## Final Recommendation

Use Telegram as a compact operator console, not a log stream.

Recommended first future implementation boundary:

```text
TELEGRAM_COPY_ONLY
```

Do not combine copy redesign with:

```text
RISK_POLICY_CHANGE
STRATEGY_CHANGE
EXECUTION_CHANGE
LIVE_CHANGE
PATH_TRUTH_REPLAY_POLICY
```

Tests: not run; docs-only design.

