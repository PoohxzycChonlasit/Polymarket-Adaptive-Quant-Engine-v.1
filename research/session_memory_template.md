# Session Memory Template

Use this template after meaningful Codex, Claude, Gemini, or ChatGPT work so future sessions can resume without rereading excessive context.

## Date

YYYY-MM-DD

## Run ID

`run_id` or `none`

## Branch / Commit

- Branch:
- Commit:
- Working tree notes:

## What Changed Today

- 

## Files Modified

| File | Why |
|------|-----|
| | |

## Tests Run

| Command | Result |
|---------|--------|
| | |

## Runtime Evidence

- Mode:
- Command:
- Start/end time:
- Notes:

## Replay Evidence

- Report path:
- Continuity:
- Bad JSON impact:
- Event coverage:

## Trade Count / Fills / Exits / PnL

| Metric | Value |
|--------|-------|
| Trades | |
| Paper orders | |
| Paper fills | |
| Paper exits | |
| Gross PnL | |
| Max drawdown | |

## Primary Bottleneck

- 

## Secondary Bottleneck

- 

## Trust Verdict

PASS / CAUTION / FAIL:

Reason:

## Caveats

- 

## Next 3 Options

Use `QUANT_FUTURE_DECISION_ENGINE.md`.

### OPTION 1 - SAFE EV PRESERVATION

#### Thesis


#### Quant Logic

- EV impact:
- Risk impact:
- Liquidity impact:
- Fill probability:
- Drawdown behavior:

#### Likely Outcome


#### Hidden Risk


#### Recommended Action


### OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY

#### Thesis


#### Quant Logic

- Expected data gain:
- Expected regime discovery:
- Expected volatility interaction:
- Expected runtime learning:

#### Likely Outcome


#### Hidden Risk


#### Recommended Action


### OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

#### Thesis


#### Quant Logic

- System-level bottleneck:
- Architecture weakness:
- Timing distortion:
- Inventory behavior:
- Execution microstructure:
- Regime mismatch:

#### Likely Outcome


#### Hidden Risk


#### Recommended Action


## Safe Next Prompt For Codex

```text
Read CODEX_START_HERE.md, PROJECT_RULES.md, AGENTS.md, MASTER_AGENT_ROUTER.md, CURRENT_PROJECT_STATUS.md, PROJECT_STRUCTURE.md, KNOWN_ISSUES.md, FILE_INDEX.md, DOCUMENTATION_MAP.md, and QUANT_FUTURE_DECISION_ENGINE.md.

Use MASTER_AGENT_ROUTER.md to select one primary role and up to three supporting roles.

Task:
[paste the next scoped task]

Do not touch strategy, risk sizing, wallet/live config, execution, orderbook behavior, reconciliation, paper/live separation, or runtime behavior unless explicitly scoped.

Run targeted checks only.
Report files changed and tests/checks run.
```

## Safe Next Prompt For ChatGPT

```text
Review this project state and evidence:
[paste compact summary]

Keep offline evidence separate from runtime execution.
Do not claim profitability or live readiness.
Generate exactly 3 future options using QUANT_FUTURE_DECISION_ENGINE.md format.
Recommend the safest next Codex task.
```
