# Repo Canonical Check - 2026-05-19

## Scope

Target repo:

```text
C:\quant\Polymarket-Adaptive-Quant-Engine-v.1
```

Reference repo requested:

```text
C:\Users\POOHXYZ\Desktop\quant\Polymarket-Adaptive-Quant-Engine-v.1
```

Rules followed:

- Read-only first.
- No runtime/code modifications.
- No paper runtime started.
- No replay started.
- Only allowed readiness smoke executed: `py -c "import main; print('IMPORT_OK')"`.

## Role Routing

- Primary role: `01_PROJECT_MANAGER_AGENT.md`
- Supporting role: `07_TEST_CI_AGENT.md`
- Why selected: canonical repo coordination plus a narrow import smoke check.
- Files/areas inspected: startup docs, router/role docs, git metadata, required path existence, required symbol search, import smoke.
- Files/areas intentionally ignored: strategy/risk/execution/wallet/live config internals, raw runtime logs/JSONL, replay outputs, and generated evidence beyond path-existence checks.

## Target Repo Findings

### Git State

```text
branch: main
tracking: origin/main
status before this report: clean
HEAD: fb88fe081d61b43a57b4410d9d1c109e703e1bb0
remote: https://github.com/PoohxzycChonlasit/Polymarket-Adaptive-Quant-Engine-v.1.git
```

Recent log head:

```text
fb88fe0 feat: add overnight maturity check and stop-loss concentration diagnosis reports
4eac885 feat: add paired trade identity continuity instrumentation v1
0a81783 docs: Phase 6 - preserve runtime reports to git-tracked archive
a81a807 docs: organize session reports - Phase 2 + audit v1
69a8d5e Enhance orderbook diagnostics and error handling
```

### Required Commits

| Commit | Expected purpose | Result |
|---|---|---|
| `4eac885` | paired trade identity continuity | Present |
| `69a8d5e` | orderbook diagnostics | Present |
| `0a81783` | runtime report archive | Present |
| `a81a807` | docs organization | Present |

### Required Local State

| Path | Result |
|---|---|
| `runtime/` | Present |
| `runtime/quant_data/` | Present |
| `runtime/research_state/` | Present |
| `logs/` | Present |
| `.env` | Present |
| `.claude` | Present |
| `docs/research/sessions/` | Present |

### Required Symbols

All required symbols were found in the target repo:

- `paper_trade_replay_key`
- `orderbook_available_for_decision`
- `orderbook_availability_classification`

Key code locations include:

- `polymarket/trader.py`
- `utils/quant_event_logger.py`
- `tests/test_orderbook_handoff_diagnostics.py`
- `tests/test_paired_trade_identity_continuity.py`

### Paper Readiness Smoke

Command run:

```bash
py -c "import main; print('IMPORT_OK')"
```

Result:

```text
IMPORT_OK
```

Paper ready for an explicitly approved future paper launch: **Yes, based on import smoke only.**

This is not live-readiness evidence.

## Reference Repo Findings

The requested Desktop reference path does not resolve in this environment:

```text
C:\Users\POOHXYZ\Desktop\quant\Polymarket-Adaptive-Quant-Engine-v.1
```

`Test-Path` result for the exact reference repo path: `False`.

Because the exact reference repo is unavailable, these comparisons could not be performed:

- Reference HEAD SHA
- Reference working tree status
- Reference branch tracking
- Reference remote

Requested reference local-state path checks all resolved `False` because the base repo path itself was missing:

| Reference path | Result |
|---|---|
| repo root | Missing |
| `runtime/` | Missing / unavailable |
| `runtime/quant_data/` | Missing / unavailable |
| `runtime/research_state/` | Missing / unavailable |
| `logs/` | Missing / unavailable |
| `.env` | Missing / unavailable |
| `.claude` | Missing / unavailable |
| `docs/research/sessions/` | Missing / unavailable |

Desktop repo status versus target: **unavailable / not comparable from the requested path.**

## Canonical Decision

`C:\quant\Polymarket-Adaptive-Quant-Engine-v.1` should be treated as the recommended canonical local repo for the next task because:

- It exists.
- It is on `main`.
- It was clean before this report was created.
- It is tracking `origin/main`.
- It has the required commits.
- It has the required runtime/research/log/local assistant state paths.
- It passes the allowed import smoke.
- The requested Desktop reference repo path is missing/unavailable.

Conclusion: **C:\quant is current/canonical for the next safe workflow, subject to the operator confirming no alternate Desktop path was intended.**

## Missing Local State

Target repo missing local state from the requested checklist: **None found.**

Reference repo missing/unavailable: **the exact requested reference repo path does not exist from this environment.**

## Safe Launch Command

Do not launch yet under this task.

When the operator explicitly approves a future paper run, use:

```bash
python main.py --mode paper --interval 60
```

Safe default paper command remains:

```bash
python main.py
```

## Behavior Change Statement

- Runtime behavior changed: **No**
- Live behavior changed: **No**
- Strategy changed: **No**
- Risk changed: **No**
- Execution changed: **No**
- Wallet/live config changed: **No**
- Replay logic changed: **No**

Only this markdown report was added.

## Claude Code Prompt

```text
You are working in the canonical local repo:

C:\quant\Polymarket-Adaptive-Quant-Engine-v.1

Do not use the Desktop reference path for work right now. The requested reference path
C:\Users\POOHXYZ\Desktop\quant\Polymarket-Adaptive-Quant-Engine-v.1
did not resolve from Codex's environment, so it could not be compared.

Current canonical status:
- C:\quant exists and is the recommended canonical repo for the next task.
- Branch: main
- HEAD: fb88fe081d61b43a57b4410d9d1c109e703e1bb0
- Required commits are present:
  - 4eac885 paired trade identity continuity
  - 69a8d5e orderbook diagnostics
  - 0a81783 runtime report archive
  - a81a807 docs organization
- Required local state exists in C:\quant:
  - runtime/
  - runtime/quant_data/
  - runtime/research_state/
  - logs/
  - .env
  - .claude
  - docs/research/sessions/
- Import smoke passed:
  - py -c "import main; print('IMPORT_OK')"
  - output: IMPORT_OK

Do not run paper yet unless the operator explicitly approves it.
Do not run replay yet.
Do not start live mode.
Do not modify runtime/code for this handoff task.

What to monitor when a future paper run is explicitly approved:
- Paper banner is visible.
- Mode is paper, not live.
- Terminal/source shows paper_virtual or other explicitly paper-safe source.
- Real BTC/ETH BID, ASK, and SPREAD are visible.
- orderbook_available_for_decision is emitted.
- orderbook_availability_classification is emitted.
- paper_trade_replay_key appears on paper trade open/close events if trades occur.
- Skip reasons, cutoff behavior, risk_plan_zero, and liquidity/orderbook classifications.
- PAPER ORDER, PAPER FILL, PAPER EXIT, and PAPER PNL events if natural gates allow them.
- No live order, cancel, redeem, signing, allowance, or wallet-spending path is touched.

What not to touch:
- Do not modify strategy logic.
- Do not modify risk sizing, thresholds, bankroll tiers, risk modes, or LOCKDOWN behavior.
- Do not modify execution, order intent, reconciliation, wallet, allowance, live flags, or live config.
- Do not modify replay logic or wire replay output into runtime decisions.
- Do not loosen cutoff, EV, confidence, liquidity, stale-orderbook, or risk gates.
- Do not delete or archive runtime, logs, backtest results, config files, or research records.

Next safe task:
Prepare a paper-session monitoring checklist from the current repo state and wait for explicit operator approval before launching:

python main.py --mode paper --interval 60

If the operator wants another canonical comparison first, ask for the corrected Desktop/reference path and compare HEAD/status/local-state only. Keep it read-only.
```
