# TRADE_CLOSE_AND_PNL_ACCOUNTING_VALIDATION_001 Execution Contract

**Schema:** `execution_contract_v2.1`
**Created:** `2026-06-30T16:38:02+07:00`
**HEAD before execution:** `eded02a0`
**Task class:** `5 VALIDATION / PAPER CLOSE AND PNL ACCOUNTING`
**Workflow tier:** `STANDARD`
**Evidence target:** Grade A runtime evidence plus Grade C targeted tests

## Scope

Validate the paper close / exit / PnL accounting path for existing target paper position `bd919e7a`. This task may compile files, run focused tests, launch a bounded paper runtime, inspect generated runtime evidence, and write the validation report plus ops state.

## Allowed Actions

- Run `py_compile` on task-specified runtime modules.
- Run focused pytest suites under `tests/observability` and `tests/polymarket`.
- Launch paper runtime only with:
  - `.\.venv\Scripts\python.exe main.py --mode paper --interval 60 --ui compact`
  - maximum 30 minutes
  - stop early after target position `bd919e7a` closes and close/PnL evidence is captured
- Inspect generated current-run logs, JSONL, bot status, and position tracker state.
- Create `docs/reports/TRADE_CLOSE_AND_PNL_ACCOUNTING_VALIDATION_001.md`.
- Update:
  - `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
  - `docs/operations/TASK_QUEUE_001.json`
  - active loop memory file from workflow state

## Forbidden Scope

- No runtime behavior changes.
- No source code edits to `polymarket/`, `utils/`, `config/`, `main.py`, or tests.
- No strategy threshold, signal, sizing, risk-threshold, execution, live-execution, wallet/live-balance, `config/settings.py`, or `.env` changes.
- No runtime data deletion or manual runtime-state reset.
- No manual close helper unless it is already part of the paper runtime and explicitly safe; this task will not use one.
- No live mode command.
- No wallet, allowance, signing, live order, cancel, redeem, or live position actions.

## Target Position

| Field | Value |
|---|---|
| Position ID | `bd919e7a` |
| Symbol | `pm-5m-eth` |
| Outcome | `NO` |
| Side | `BUY` |
| Entry price | `0.50` |
| Size | `0.2` |
| Notional | `$0.10` |
| Order ID | `paper-82073141` |
| Status before validation | `open` |

## Evidence Plan

| Evidence | Command / Source | Expected Result |
|---|---|---|
| Clean preflight | `git status --short`, process/owner checks | clean tree before contract; no active runtime |
| Compile | task-specified `py_compile` command | exit 0 |
| Focused tests | task-specified pytest command | exit 0 or documented pre-existing failures |
| Runtime | bounded paper command | paper mode only, no live markers |
| Close accounting | current-run JSONL/state/log scan | `trade_close`, realized PnL, cash/exposure state captured |
| Final validation | JSON tool + `git diff --check` | pass |

## Stop Conditions

- Dirty source/core files before runtime launch.
- Active runtime process or active runtime owner file.
- Any command would start live mode.
- Any evidence of live order submission, wallet mutation, allowance, signing, cancel, redeem, or live position action.
- A new clear blocking bug appears: document evidence and stop without changing runtime code.
- Runtime exceeds 30 minutes without target close evidence.

## Commit Policy

Single TYPE C validation commit:

```text
docs: validate paper trade close pnl accounting
```

Expected committed files are report, execution contract, workflow state, task queue, and loop memory only.

## Verification Checklist

- [ ] `git status --short` clean before contract creation
- [ ] No active Python runtime process
- [ ] No active runtime owner file
- [ ] Target position `bd919e7a` visible before runtime
- [ ] `py_compile` passes
- [ ] focused pytest command passes or failures are documented
- [ ] paper runtime bounded and paper-only
- [ ] run ID captured
- [ ] target close status captured
- [ ] trade_close count captured
- [ ] realized PnL captured
- [ ] paper cash/exposure/open-position-value captured
- [ ] risk mode/outcome update captured
- [ ] live markers captured
- [ ] JSON ops validation passes
- [ ] `git diff --check` passes
