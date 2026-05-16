# Skill: Live Risk Security Check

## Purpose

Run a preflight safety checklist before any live-risk, wallet, allowance, private key, `.env`, or live execution work.

Default verdict is keep live blocked until complete readiness evidence exists.

## Required Checks

| Area | Required Review |
|------|-----------------|
| `.env` | Inspect only when explicitly scoped. Never print secrets. |
| `LIVE_TRADING_ENABLED` | Must not be enabled by docs-only or unrelated tasks. |
| `PAPER_TRADING` | Paper mode must remain default unless live is explicitly scoped. |
| `DRY_RUN` | Do not disable dry-run protections without explicit live-risk approval. |
| Wallet | Confirm wallet source and balance source labels without exposing addresses unnecessarily. |
| Allowance | Keep live blocked when allowance is missing or unknown. |
| Order placement | Require evidence of safe order placement before live-ready claims. |
| Fill/cancel/reconcile | Require fill, cancel, and reconciliation evidence before live-ready claims. |
| Private keys | Never expose, paste, log, or transform private keys. |
| MCP/hooks | Do not enable MCP servers or auto-running hooks without dedicated review. |

## Live Readiness Evidence Required

Do not claim live-ready unless all are proven:

- orderbook visible with BID, ASK, SPREAD
- wallet/collateral source verified
- allowance ready
- order placement validated
- fill observed
- cancel path validated
- reconciliation validated
- stale data protections active
- OrderIntent active
- risk manager active
- paper/live separation tested

## Hard Warnings

- Never edit `.env` unless explicitly scoped.
- Never expose secrets.
- Never enable live trading from docs-only tasks.
- Never bypass allowance checks.
- Never bypass OrderIntent.
- Never bypass reconciliation.
- Never bypass stale data protection.
- Never enable MCP/hook auto-run without review.
- Never wire offline analyzers into runtime decisions.

## Output Shape

Report:

1. scope and files inspected
2. current live-risk state
3. missing readiness evidence
4. blocked/unblocked verdict
5. secrets handling statement
6. next safe step
