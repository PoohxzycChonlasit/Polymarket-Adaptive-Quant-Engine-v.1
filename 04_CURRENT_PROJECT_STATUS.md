# 04 Current Project Status

## Status Date

2026-07-01

## Current Mission

The repository is being reset around the Profit Engine mission:

Paper profit first. Micro live only after evidence.

## Current Truth

- Paper runtime has recently proven startup, fill path, trade open, trade close, PnL accounting, cash return, exposure clearing, and bot status freshness in bounded validations.
- A 60-minute paper baseline produced two complete stop-loss cycles and negative session PnL.
- A later 60-minute TP-evidence run produced zero entries, so no take-profit sample was observed.
- Entry blocker analysis showed the strongest design question is `risk_plan_zero` side-confidence semantics.
- Entry throughput and market-realism audit now confirms current evidence is valid for blocker diagnosis and paper accounting, but not valid for a profit claim or live sizing realism.
- Canonical evidence and market-time truth review now defines the per-run funnel, alias map, evidence-validity classes, and dashboard availability needed before more replay/tuning work.
- Shadow strategy framework work exists, but the mission reset freezes further framework expansion unless it directly supports profit evidence.

## Current Blockers

| Blocker | Status | Why It Matters |
|---|---|---|
| Positive expectancy | Not proven | No profitability claim is allowed. |
| Entry throughput | Insufficient in some runs | Zero-entry sessions cannot produce TP/PnL evidence. |
| Take-profit exits | Not observed in latest TP evidence run | Cannot design winning-position ladder from absent winning samples. |
| Market-realistic sizing | Needs explicit validation | Paper fractional sizing may not match live CLOB mechanics. |
| Time truth | Needs strict governance | Profit evidence is invalid if timing is ambiguous. |
| Market/live sizing realism | Not proven | Current paper opens can use `$0.10` fractional shares; live CLOB fractional/minimum-order behavior is unresolved. |
| Canonical evidence summary | Needed | Future replay and dashboard work should consume one per-run evidence summary instead of re-deriving aliases ad hoc. |
| Live execution | Not validated | Micro live remains blocked. |

## Active Safety Position

- Runtime behavior unchanged by governance reset.
- Strategy/risk/sizing/execution thresholds unchanged.
- Live behavior unchanged.
- Paper remains the default validation path.

## Current Next Priority

Build an offline canonical run evidence summary helper before further shadow replay or threshold discussion.
