# Skill: Semantic Shadow Sizing

## Purpose

Analyze semantic confidence, EV quality, and shadow sizing research.

Shadow fields are observability-only. They must not become runtime sizing, trading approval, or live-risk behavior unless a future task explicitly scopes and tests that promotion.

## Required Inputs

- Run-scoped replay report.
- Run-scoped session evaluator report.
- `trade_journal` paper outcomes.
- Decision/risk/execution JSONL evidence when needed.
- MFE/MAE or lifecycle replay evidence when available.
- Regime, liquidity, spread, and lifecycle timing fields.

## Required Analysis

Compare shadow ideas against observed paper evidence:

| Area | Question |
|------|----------|
| Semantic confidence | Did confidence align with realized paper outcomes? |
| EV quality | Did EV after spread predict better outcomes or safer skips? |
| Shadow size | How did proposed shadow size compare with realized PnL, drawdown, MFE/MAE, and liquidity? |
| Regime | Did volatility/trend/compression affect quality? |
| Liquidity | Did spread or book readiness explain false positives? |
| Lifecycle latency | Did late detection or cutoff decay reduce edge? |
| Risk budget | Would shadow size have stayed within tier and drawdown limits? |

## Explicit Forbids

- Do not promote `c_size_usd` into runtime sizing.
- Do not promote `c_mult` into runtime sizing.
- Do not wire shadow fields into trade approval.
- Do not change probability semantics.
- Do not change strategy thresholds.
- Do not change risk sizing.
- Do not change execution behavior.
- Do not change wallet/live config.

## Output Shape

Report:

1. selected run_id and continuity status
2. shadow field coverage
3. EV/probability visibility
4. shadow size vs realized paper outcome
5. MFE/MAE and lifecycle latency notes
6. liquidity/regime caveats
7. verdict: observability-only
8. next safest offline research step
