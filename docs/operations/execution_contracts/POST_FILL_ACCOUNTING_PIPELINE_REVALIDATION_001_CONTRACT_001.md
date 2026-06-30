# POST_FILL_ACCOUNTING_PIPELINE_REVALIDATION_001 Execution Contract

**Schema:** `execution_contract_v2.1`
**Created:** `2026-06-30T16:14:34+07:00`
**HEAD before execution:** `2e12e590`
**Task class:** `5 VALIDATION / POST-FILL ACCOUNTING REVALIDATION`
**Workflow tier:** `STANDARD`
**Evidence target:** Grade A runtime evidence plus Grade C targeted tests

## Scope

Revalidate paper post-fill accounting after the `bankroll_family` bug repair and paper state reset. This task may compile files, run focused tests, launch a bounded paper runtime, inspect generated runtime evidence, and write the validation report plus ops state.

## Allowed Actions

- Run `py_compile` on task-specified runtime modules.
- Run focused pytest suites under `tests/observability` and `tests/polymarket`.
- Launch paper runtime only with:
  - `.\.venv\Scripts\python.exe main.py --mode paper --interval 60 --ui compact`
  - maximum 30 minutes
  - stop early after first paper fill if full accounting evidence is captured
- Inspect generated current-run logs, JSONL, bot status, and position tracker state.
- Create `docs/reports/POST_FILL_ACCOUNTING_PIPELINE_REVALIDATION_001.md`.
- Update:
  - `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
  - `docs/operations/TASK_QUEUE_001.json`
  - active loop memory file from workflow state

## Forbidden Scope

- No runtime behavior changes.
- No source code edits to `polymarket/`, `utils/`, `config/`, `main.py`, or tests.
- No strategy threshold, signal, sizing, risk-threshold, execution, live-execution, wallet/live-balance, `config/settings.py`, or `.env` changes.
- No runtime data deletion.
- No live mode command.
- No wallet, allowance, signing, live order, cancel, redeem, or live position actions.

## Safety Memory Spot Check

- `QS-001` present in safety memory schema: yes
- `QS-005` present in safety memory schema: yes
- `QS-010` present in safety memory schema: yes

## Evidence Plan

| Evidence | Command / Source | Expected Result |
|---|---|---|
| Clean preflight | `git status --short`, process/owner checks | clean tree, no active runtime |
| Compile | task-specified `py_compile` command | exit 0 |
| Focused tests | task-specified pytest command | exit 0 or documented pre-existing failures |
| Runtime | bounded paper command | paper mode only, no live markers |
| Accounting | current-run JSONL/state/log scan | fill/trade_open/cash/exposure/risk evidence captured |
| Final validation | JSON tool + `git diff --check` | pass |

## Stop Conditions

- Dirty core/source files before runtime launch.
- Active runtime process or active runtime owner file.
- Any command would start live mode.
- Any evidence of live order submission, wallet mutation, allowance, signing, cancel, redeem, or live position action.
- A new clear blocking bug appears: document evidence and stop without changing runtime code.
- Runtime exceeds 30 minutes without enough evidence.

## Commit Policy

Single TYPE C validation commit:

```text
docs: revalidate post fill accounting pipeline
```

Expected committed files are report, execution contract, workflow state, task queue, and loop memory only.

## Verification Checklist

- [ ] `git status --short` clean before paper run
- [ ] No active Python runtime process
- [ ] No active runtime owner file
- [ ] `py_compile` passes
- [ ] focused pytest command passes or failures are documented
- [ ] paper runtime bounded and paper-only
- [ ] run ID captured
- [ ] fill count captured
- [ ] trade_open count captured
- [ ] position_id status captured
- [ ] paper cash/exposure/open-position-value captured
- [ ] risk mode captured
- [ ] live markers captured
- [ ] JSON ops validation passes
- [ ] `git diff --check` passes
