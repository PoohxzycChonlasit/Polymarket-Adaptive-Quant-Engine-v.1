# AI Agent Security Checklist

This checklist applies to Codex, Claude, Gemini, ChatGPT, and any other AI-assisted workflow for this repository.

## Absolute Warnings

- Never edit `.env` unless explicitly scoped.
- Never expose secrets.
- Never paste private keys, wallet credentials, API keys, bot tokens, or chat IDs into docs, logs, prompts, or reports.
- Never enable live trading from docs-only tasks.
- Never bypass allowance checks.
- Never bypass OrderIntent validation.
- Never bypass reconciliation.
- Never bypass stale data protection.
- Never bypass risk gates, forced exits, or panic exits.
- Never enable MCP/hook auto-run without dedicated review.
- Never wire offline analyzers into runtime decisions.
- Never claim live-ready without orderbook, wallet, allowance, order placement, fill, cancel, and reconciliation evidence.

## Safe Defaults

| Area | Safe Default |
|------|--------------|
| Runtime mode | Paper mode. |
| Live trading | Blocked unless explicitly scoped and readiness passes. |
| Offline analyzers | Evidence only. |
| Skills | Guidance only. |
| Prompts | Human-invoked only. |
| Hooks | Disabled. |
| MCP | Not enabled by this harness. |
| Secrets | Never printed or copied. |

## Before Any Live-Risk Work

Confirm:

1. The user explicitly asked for live-risk review or live operation.
2. `.env` inspection is explicitly allowed.
3. Secrets will be redacted.
4. Paper/live separation tests are identified.
5. Readiness evidence exists for orderbook, wallet, allowance, order placement, fill, cancel, and reconciliation.
6. Live mode remains blocked if any readiness evidence is incomplete.

## Before Any Docs-Only Work

Confirm:

1. No Python runtime files are needed.
2. No strategy, risk, wallet, execution, or config files are touched.
3. No tests are deleted.
4. No auto-running hook or MCP config is added.
5. Final report states runtime behavior changed: No.
6. Final report states live behavior changed: No.
