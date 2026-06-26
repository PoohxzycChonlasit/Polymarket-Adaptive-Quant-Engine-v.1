# ACTIVE QUESTION: LOW_PRICE_TRUTH_RESOLUTION_001

## Metadata
- **Current Active Question**: `LOW_PRICE_TRUTH_RESOLUTION_001`
- **Question Type**: RESEARCH
- **Question Owner**: Research Governance Layer
- **Opened By**: Governance Bootstrap Phase 1
- **Status**: ACTIVE
- **Next Gate**: Staging execution ledger check on historical files.

## Objective
Verify whether simulated settlement outputs for ask prices < $0.05 are backed by official on-chain Polymarket outcomes, or are purely dependent on provisional snapshot price proxies.

## Blocking
- Strategy changes
- Sizer changes
- Execution changes
- Threshold changes
- Inventory changes

## Allowed Work
- Audits examining token ID settlement contracts on-chain.
- Replays validating path truth versus final resolutions for post-wiring rows.

## Forbidden Work
- New parameter sweeps or sizer modifications.
- Repetitive reviews of low-price PnL expectancy without direct settlement data joins.
- Code modifications, parameter tuning, or live sizer changes.

## Closure States
An active question can only transition to closed if the operator approves one of the following verdicts:
- `EDGE_REAL`: Quantitative evidence confirms the edge is executable and profitable.
- `REPLAY_ARTIFACT`: Evidence proves the findings are a simulation/replay bias.
- `DATA_INSUFFICIENT`: Missing or corrupt logs make verification impossible.
