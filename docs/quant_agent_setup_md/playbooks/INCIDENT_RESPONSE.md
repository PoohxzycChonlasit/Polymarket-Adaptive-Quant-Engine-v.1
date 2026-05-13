# Incident Response Playbook

Status: active incident workflow. Incidents are evidence-first and safety-first.

## First Response

1. Freeze the scope: identify whether the issue is runtime, paper-only, docs-only, observability, replay, risk, execution, or config.
2. Preserve evidence and avoid broad scans of generated folders.
3. Identify the primary agent through `MASTER_AGENT_ROUTER.md`.
4. Determine whether trading safety could be affected.
5. If live-risk flags or position truth are uncertain, treat the state as unsafe until proven otherwise.

## Quant Incident Diagnosis

Classify the incident by likely subsystem:

- Scanner lifecycle delay.
- Token/orderbook readiness.
- Spread/liquidity microstructure.
- Regime/probability evidence quality.
- Risk budget or LOCKDOWN behavior.
- OrderIntent/reconciliation/position truth.
- Exit/forced-exit/final-derisk behavior.
- Observability/logging/Telegram signal quality.
- Config or mode safety.

## Safety Response

- Do not bypass risk, OrderIntent, reconciliation, stale-book checks, forced exits, or panic exits.
- Do not alter wallet, allowance, private keys, `.env`, or live flags unless explicitly scoped.
- Do not wire offline analyzer output into runtime decisions.
- Keep logging compact; no raw orderbook spam.

## Incident Output

- Root Problem
- Evidence
- Suspected Root Cause
- Safety Impact
- Immediate Containment
- Files To Inspect
- Tests Required
- What Not To Touch
- One exact next recommended step
