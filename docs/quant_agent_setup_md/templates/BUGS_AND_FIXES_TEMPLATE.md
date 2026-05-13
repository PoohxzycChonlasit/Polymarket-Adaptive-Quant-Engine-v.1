# Bugs And Fixes Template

Use this template for bug reports, repair plans, and implementation summaries.

## Root Problem

What failed? Is it root cause, final symptom, mixed, or insufficient data?

## Evidence

List exact logs, JSONL fields, evaluator output, tests, screenshots, or code paths.

## Quant Interpretation

Explain the failure through timing, market data, regime, probability, fair value, EV, spread, liquidity, risk budget, inventory state, and execution feasibility.

## Safety Impact

State whether paper/live separation, risk controls, OrderIntent, reconciliation, stale-book protection, forced exits, or panic exits are affected.

## Fix Scope

Files to inspect:

- `[file]`

Files to modify:

- `[file]`

Files/directories not to touch:

- `.env`
- runtime/log/generated evidence folders
- wallet/allowance/private-key paths
- unrelated strategy/risk/execution modules

## Exactly Three Future Options

1. OPTION 1 - SAFE EV PRESERVATION
2. OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY
3. OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

Recommended option: `[option]`

## Tests Required

List focused tests only. For docs-only work, say runtime tests are not required and list markdown/reference checks.

## Completion Gate

- Changed:
- Not changed:
- Tests/checks run:
- Safety proof:
- Remaining risks:
- Next exact step:
