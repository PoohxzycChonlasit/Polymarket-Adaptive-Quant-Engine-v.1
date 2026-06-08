# JSONL Writer Truth Audit

Generated: 2026-06-08
Scope: READ ONLY — no code changes, no config changes, no commits, no runtime modifications.
Non-authorization: this document does not change strategy, risk, execution, sizing, live behavior, runtime policy, or alerts.

---

## 1. Question

The ETH YES FC OS Command Center report (rendered `2026-06-07T23:20:48Z`) shows:

```
| JSONL Writer | BLOCKED |
```

Is this a real runtime failure or a stale/artifact status?

---

## 2. Executive Summary

**BLOCKED is a dashboard artifact. The JSONL writer is NOMINAL.**

The status originates from a hardcoded default value (`"BLOCKED"`) in the `--jsonl-integrity-status` argparse parameter of `eth_yes_fc_os_command_center.py`. No probe function ever reads actual JSONL file state; no caller has ever passed a non-default value. The parameter is an operator-injection stub that has never been injected.

Meanwhile, the actual JSONL writer (`utils/quant_event_logger.py`) is fully operational: 6 of 9 categories are actively writing under run `20260607T135728Z_24128_e2091b7f`, with `system_health` and `decision_log` confirmed writing at `2026-06-08T05:21:47Z` (the moment of evidence collection).

The terminal UI (`utils/display.py`) reports "OK" for the JSONL writer via a completely separate code path that reads actual write results. The two systems do not share vocabulary, telemetry, or data flow.

---

## 3. Task Candidate Root Cause Evaluation

The task enumerates six candidate explanations. Each is evaluated against primary-source evidence.

| # | Candidate | Verdict | Evidence |
|---|---|---|---|
| 1 | **Real runtime failure** | ❌ ELIMINATED | 6/9 JSONL categories writing at age=0.0h; system_health has 8,318 events; decision_log has 3,242 events — all under the same active run_id. No write errors in trader.py vocabulary. |
| 2 | **Stale telemetry** | ❌ ELIMINATED | No telemetry is read at all. `compute_metrics()` never opens any JSONL file or reads any status from disk. There is no live source to go stale. |
| 3 | **Missing refresh** | ❌ ELIMINATED | There is no refresh mechanism to be missing. The command center never connected to a live probe; a missing refresh requires a connection that once existed. |
| 4 | **Dashboard artifact** | ✓ CONFIRMED (mechanism) | The label `BLOCKED` is rendered verbatim from a function parameter via `| JSONL Writer | {jsonl_integrity_status} |`. The parameter is never computed — it is just shown. |
| 5 | **Manual flag** | ❌ ELIMINATED | No operator has ever passed `--jsonl-integrity-status` with any value. The value has never been consciously set for any specific run. |
| 6 | **Fallback value** | ✓ ROOT CAUSE | `parser.add_argument("--jsonl-integrity-status", default="BLOCKED")` and `def generate_command_center_report(..., jsonl_integrity_status: str = "BLOCKED")` — both default to `"BLOCKED"`. This default has never been overridden. |

**Root cause chain:** The fallback value `"BLOCKED"` propagates through an unprobed parameter into a template substitution, producing a dashboard artifact that looks like a runtime status but carries no runtime information.

---

## 4. Observability Path Diagram

Two entirely separate code paths report on JSONL health. They do not share vocabulary, data, or call chains.

```
PATH A — Runtime Terminal UI (accurate)
─────────────────────────────────────────────────────────────────
polymarket/trader.py
  _emit_quant_event()
    QuantEventLogger.log(...)
      _append_jsonl() — tries write, fail-soft on PermissionError
    jsonl_ok = (write result)
    jsonl_status = "OK" if jsonl_ok else "WARN"
    payload["jsonl_status"] = jsonl_status
  _observability_health_from_payload(payload)
    returns {"jsonl_status": "OK" if jsonl_ok else "WARN"}
        ↓
utils/display.py
  _footer_jsonl_tag()
    reads _observability_health["jsonl_status"]
    returns "OK" | "WARN" | "UNKNOWN"
  _system_status()
    "OK" if _footer_jsonl_tag() == "OK" else "DEGRADED"
        ↓
Terminal: shows "OK" or "DEGRADED"
Vocabulary: {OK, WARN, UNKNOWN, DEGRADED}
Source: actual write results

PATH B — Offline Command Center (not accurate for JSONL)
─────────────────────────────────────────────────────────────────
tools/eth_yes_fc_os_command_center.py
  argparse: --jsonl-integrity-status  default="BLOCKED"
  generate_command_center_report(jsonl_integrity_status="BLOCKED")
    [no probe; compute_metrics() never touches JSONL files]
  _render_report(jsonl_integrity_status="BLOCKED")
    template: "| JSONL Writer | {jsonl_integrity_status} |"
        ↓
Report: shows "BLOCKED"
Vocabulary: {BLOCKED, NOMINAL, DEGRADED}  (caller-injected only)
Source: argparse default — no runtime data
```

The two paths never converge. Path A correctly reflects write results; Path B reflects only what a caller passes as an argument.

---

## 5. Source Trace: Where Does BLOCKED Come From?

### 5.1 Function signature default

`tools/eth_yes_fc_os_command_center.py`, `generate_command_center_report()`:

```python
def generate_command_center_report(
    ...
    jsonl_integrity_status: str = "BLOCKED",   # line 876
    ...
) -> str:
```

If no caller overrides this parameter, the function always receives `"BLOCKED"`.

### 5.2 Argparse default

`tools/eth_yes_fc_os_command_center.py`, `__main__` argument parser:

```python
parser.add_argument(                           # line 904
    "--jsonl-integrity-status",
    default="BLOCKED",
)
```

Running `python tools/eth_yes_fc_os_command_center.py` without `--jsonl-integrity-status NOMINAL` always passes `"BLOCKED"` to `generate_command_center_report()`.

### 5.3 Template rendering

`tools/eth_yes_fc_os_command_center.py`, `_render_report()`:

```python
f"| JSONL Writer | {jsonl_integrity_status} |"  # line 751
```

No transformation, no conditional logic. The string is rendered verbatim.

### 5.4 No probe in compute_metrics()

`compute_metrics()` (the function that calculates all actual campaign metrics) never:
- Opens any JSONL file
- Checks any write timestamp
- Queries `QuantEventLogger` state
- Returns or sets `jsonl_integrity_status`

The parameter flows entirely outside of `compute_metrics()`, from argparse default → function call → template — bypassing all actual evidence.

### 5.5 No caller injection

A shell grep of all Python files, shell scripts, and invocation sites finds no caller that passes `--jsonl-integrity-status` with a non-default value. The "BLOCKED" label has never been set deliberately for any run.

---

## 6. Logical Proof: BLOCKED Cannot Originate From the Runtime Writer

Even if the command center were wired to the terminal UI observability path, it could not produce "BLOCKED" — because "BLOCKED" does not exist in the runtime writer's vocabulary.

### 6.1 QuantEventLogger vocabulary

`utils/quant_event_logger.py`, `_append_jsonl()`:

- On success: increments counter, returns normally
- On `PermissionError`: disables the category for the session, returns normally
- On other exceptions: propagates (caller catches)
- Never emits: "BLOCKED", "NOMINAL", "DEGRADED", or any string status

### 6.2 Trader.py vocabulary

`polymarket/trader.py`, `_emit_quant_event()` and `_observability_health_from_payload()`:

```python
jsonl_status = "OK" if jsonl_ok else "WARN"
# _observability_health_from_payload:
{"jsonl_status": "OK" if jsonl_ok else "WARN"}
```

Possible values: `{"OK", "WARN"}`. "UNKNOWN" is produced when `self._quant_logger` is None.

### 6.3 Display.py JSONL tag vocabulary

`utils/display.py`, `_footer_jsonl_tag()` (line 3300):

```python
def _footer_jsonl_tag(self) -> str:
    status = str(self._observability_health.get("jsonl_status", "") or "").upper()
    if status in {"OK", "WARN", "UNKNOWN"}:
        return status
    value = self._observability_health.get("jsonl_ok")
    if value is not None:
        return "OK" if bool(value) else "WARN"
    return "OK" if self._logging_status == "SAFE" else "WARN"
```

The function has three branches: (1) direct `jsonl_status` string check, (2) `jsonl_ok` boolean fallback, (3) `_logging_status` fallback. All branches return one of `{"OK", "WARN", "UNKNOWN"}`. "BLOCKED" is not reachable from this function by any branch.

### 6.4 "BLOCKED" in display.py is a different concept

The string `"BLOCKED"` does appear in `utils/display.py` — but in completely unrelated contexts:

| Location | Context | What it means |
|---|---|---|
| Line 3217: `return "BLOCKED"` | `_candidate_state_label()` | A candidate order's lifecycle state (blocked by a main blocker) |
| Line 3232: `if upper == "BLOCKED":` | `_candidate_state_style()` | Styling for the above label |
| Line 3468: `if boundary == "BLOCKED_BEFORE_RISK"` | Execution pipeline render | Order stopped before risk check |
| Line 3498: `{"BLOCKED_BEFORE_RISK"}` | Same pipeline | Same context |
| Line 3560: `else "BLOCKED"` | `_execution_readiness_label()` | Readiness pct = 0; execution gate has zero progress |
| Line 3571: `else "BLOCKED"` | `_phase6_label()` | Phase 6 gate: `readiness_pct` is zero |
| Line 3585: `return "BLOCKED"` | `_phase6_label()` | Phase 6 gate: insufficient individual gate counts |
| Line 3605: `else "BLOCKED"` | `_execution_gate_line()` | Individual execution gate: `cur = 0` |

None of these are in `_footer_jsonl_tag()` or any JSONL writer status function. **"BLOCKED" as a JSONL-writer status string is unique to the command center template and its argument default.**

---

## 7. JSONL File Evidence

Observed at time of evidence collection (`~2026-06-08T05:22Z`), run `20260607T135728Z_24128_e2091b7f`:

| Category | Today's file | Last mtime | Age at observation | Size | Write pattern |
|---|---|---|---|---|---|
| `system_health` | 2026-06-08.jsonl | 2026-06-08T05:21:47Z | **0.0h** | 8.9 MB (8,318 events) | Cycle-driven |
| `decision_log` | 2026-06-08.jsonl | 2026-06-08T05:21:47Z | **0.0h** | 101.9 MB (3,242 events) | Cycle-driven |
| `market_snapshots` | 2026-06-08.jsonl | 2026-06-08T05:21:47Z | **0.0h** | 31.5 MB | Cycle-driven |
| `risk_log` | 2026-06-08.jsonl | 2026-06-08T05:21:47Z | **0.0h** | 21.0 MB | Cycle-driven |
| `orderbook_lineage` | 2026-06-08.jsonl | 2026-06-08T05:21:47Z | **0.0h** | 12.7 MB | Cycle-driven |
| `research_log` | 2026-06-08.jsonl | 2026-06-08T05:21:47Z | **0.0h** | 54.2 MB | Cycle-driven |
| `trade_journal` | 2026-06-08.jsonl | 2026-06-08T00:16:53Z | 5.1h | 14 KB (2 events) | Event-driven |
| `execution_log` | 2026-06-08.jsonl | 2026-06-08T00:16:53Z | 5.1h | 34 KB (6 events) | Event-driven |
| `path_truth` | 2026-06-08.jsonl | 2026-06-08T00:16:53Z | 5.1h | 2 KB | Event-driven |

**6 of 9 categories active at age=0.0h** under the same run_id. All 9 categories have a today-dated file.

### 7.1 Trade journal / execution log — 5.1h age explained

A reader seeing "5.1h" for `trade_journal` and `execution_log` might suspect the writer is blocked. The correct explanation is **write pattern**, not write failure.

`trade_journal` and `execution_log` are **event-driven**: they write only when a trade opens or closes. The last write at `00:16:53Z` corresponds to the one trade in the session: a BTC/YES paper SL at `00:16:48Z` (`pnl = -0.006138`). No further trades executed after `00:17Z`, so no further writes — by design.

`decision_log` and `system_health` are **cycle-driven**: they write on every bot cycle. Their `05:21:47Z` mtime (the most recent cycle before evidence collection) confirms the bot is alive and writing normally. Both categories are under the same `run_id` and the same `QuantEventLogger` instance that serves `trade_journal`.

**Discriminator:** if the writer were blocked, cycle-driven and event-driven categories would both be silent. The cycle-driven categories at 0.0h prove the writer process is fully operational. The 5.1h for event-driven categories means the market conditions produced no qualifying trade signals after 00:17Z — not a writer failure.

---

## 8. Two-Path Vocabulary Comparison

| Attribute | Terminal UI (Path A) | Offline Command Center (Path B) |
|---|---|---|
| Source | `_append_jsonl()` write result | Argparse default `"BLOCKED"` |
| Computation | Actual JSONL write success/fail | None |
| Status vocabulary | OK / WARN / UNKNOWN | BLOCKED / NOMINAL / DEGRADED |
| Can show "BLOCKED"? | **No** (not in vocabulary) | Yes (hardcoded default) |
| Reflects runtime state? | **Yes** | No |
| Populated each cycle? | Yes (per `_emit_quant_event()`) | No (set once at script invocation) |

The two systems cannot be reconciled by checking one against the other. Path B must be connected to a probe before it can carry truthful runtime information.

---

## 9. Governor Verdict

```
VERDICT: BLOCKED is a stale dashboard artifact.

Root cause: hardcoded argparse default in eth_yes_fc_os_command_center.py.
Mechanism: the default flows through an unprobed parameter into a template.
Actual JSONL writer status: NOMINAL.

No runtime action required.
No writer fix required.
No file recovery required.
```

### Interpretation note

The `"BLOCKED"` default is plausibly intentional: a fail-closed stub that displays "BLOCKED" until an operator explicitly asserts healthy. Under this reading the parameter is not a bug but an unimplemented feature — the probe was meant to be built but never was. Under either reading (intentional stub or oversight), the operational consequence is the same: the label carries zero runtime information and should not be used to infer writer health.

---

## 10. Required Fix (Informational — Code Change Not In Scope)

Two options, in increasing fidelity:

### Option A — Operator injection (minimal)

When generating the report, probe JSONL file freshness inline and pass the computed status:

```bash
python tools/eth_yes_fc_os_command_center.py --jsonl-integrity-status NOMINAL
```

This is a manual assertion and degrades to stale on the next run if forgotten.

### Option B — Implement a real probe (durable)

Add a `_probe_jsonl_health()` function to `eth_yes_fc_os_command_center.py` (offline only, no runtime imports) that:

1. Lists `runtime/quant_data/*/` date files
2. Checks mtime of the current date's files
3. Returns `"NOMINAL"` if any cycle-driven category (system_health or decision_log) has a file aged < 10 minutes; `"DEGRADED"` if aged 10–60 minutes; `"BLOCKED"` if no today-dated file exists at all

Passes computed status to `generate_command_center_report()`. This option makes the command center truthful without any runtime imports or modifications.

Both options are informational. Neither is authorized by this document. Implementation requires a separate authorized task.

---

## 11. Evidence Chain Summary

| Evidence item | Source | Conclusion |
|---|---|---|
| `jsonl_integrity_status: str = "BLOCKED"` (line 876) | `eth_yes_fc_os_command_center.py` | Hardcoded function default |
| `default="BLOCKED"` (line 904) | `eth_yes_fc_os_command_center.py` argparse | Hardcoded CLI default |
| `| JSONL Writer | {jsonl_integrity_status} |` (line 751) | `_render_report()` | Verbatim template rendering — no logic |
| `compute_metrics()` never sets `jsonl_integrity_status` | `eth_yes_fc_os_command_center.py` | Parameter is never computed |
| No caller passes `--jsonl-integrity-status` | All invocation sites | Value has never been consciously set |
| `_footer_jsonl_tag()` returns only OK/WARN/UNKNOWN | `utils/display.py` | "BLOCKED" unreachable from runtime path |
| `_emit_quant_event()` uses only OK/WARN/UNKNOWN | `polymarket/trader.py` | "BLOCKED" not in runtime writer vocabulary |
| `_append_jsonl()` is fail-soft, no status emission | `utils/quant_event_logger.py` | Writer never emits "BLOCKED" |
| 6/9 JSONL categories at age=0.0h | `runtime/quant_data/` mtime | Writer is fully operational |
| system_health: 8,318 events at 05:21:47Z | `system_health/2026-06-08.jsonl` | Active write confirmed |
| decision_log: 3,242 events at 05:21:47Z | `decision_log/2026-06-08.jsonl` | Active write confirmed |
| trade_journal 5.1h age = 1 trade event, not writer failure | `trade_journal/2026-06-08.jsonl` | Event-driven; no trades after 00:17Z |

---

*Offline/reporting only. READ ONLY scope. No runtime, strategy, risk, execution, or code changes. No commits authorized by this document.*
