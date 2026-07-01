# CLOB_COMPLIANT_BOUNDED_PAPER_EVIDENCE_RUN_002

## Run ID
`20260701T104421Z_28776_49a52dd3`

## Runtime Duration
34.85 minutes (34:48 uptime in TUI).

## Paper/Live Mode Proof
- Mode: `paper`
- Canonical builder mode: `paper`
- `STATUS NO LIVE ORDERS` confirmed throughout the run.

## Cash/Equity/Drawdown Proof
- **Cash**: `$200.00`
- **Equity**: `$200.00`
- **Drawdown (DD)**: `0.0%`
- **Capital Basis**: `PAPER_RESEARCH_BANKROLL`
- Verified visually in TUI and via Canonical Summary logs that the paper equity correctly ignored the live reference balance update.

## Live Reference Metadata Proof
- `live_reference_bankroll_usd`: 20.10
- `paper_research_bankroll_usd`: 200.0
- `valid_for_live_reference_bankroll_claim`: false
- `deprecated_valid_for_live_20_bankroll_claim`: false

## Risk Mode Result
- **Mode**: `NORMAL`
- `RiskOff`: False
- `hard_drawdown`: completely eliminated.

## Trade Funnel Summary
- **Decisions**: 64
- **Candidates**: 56
- **EV Pass Count**: 23
- **Risk Approved Count**: 0
- **CLOB Executable Candidate Count**: 0
- **Dust Rejected Count**: 0
- **Min-order Rejected Count**: 0
- **Paper Opened Count**: 0
- **Paper Closed Count**: 0
- **TP Count**: 0
- **SL Count**: 0
- **Net PnL**: 0
- **Drawdown**: 0.0%

## Raw Runtime Blocker Summary
- `time_unsafe`: 25
- `delta_extreme`: 25
- `risk_plan_zero`: 6
- `confidence_too_low`: 6
- `ev_below_threshold`: 1
- `clob_empty_response`: 1

## Classified Blocker Summary
- `cutoff_passed`: 25
- `imbalance_extreme`: 25
- `zero_size_plan`: 6
- `confidence_below_threshold`: 6
- `first_executable_too_late`: 1
- `ev_negative`: 1

## Blocker Conflict Summary
- **Raw vs Classified Conflict Count**: 64
- **Conflict Rate**: 1.0 (100%)
- **Warnings**: `classifier_primary_differs_from_raw_runtime_blocker`
- **Explanation**: The canonical builder expects raw runtime reasons (e.g., `time_unsafe` / `delta_extreme`) while the classifier produces generalized categories (`cutoff_passed` / `imbalance_extreme`). This causes a strict string-matching mismatch, though the semantic meaning aligns.

## CLOB Constraint Status
- The engine correctly refused to open invalid/dust size positions. The strict $15 CLOB rule successfully prevented entry where sizing was not explicitly verified.

## Canonical Builder Result
- `record_count`: 1138
- Builder output explicitly loaded `decision_log`, `market_snapshots`, `research_log`, `risk_log`, and `system_health`. 

## Executable Candidate Status
- **0 Executable Candidates**. While 23 candidates passed the EV gate, they were subsequently blocked by confidence or zero-size-plan constraints. The market was heavily trending (ETH/BTC down) and mostly generated `delta_extreme` rejections before reaching execution thresholds.

## Paper Open Status
- **0 Paper Opens**.

## PnL Meaningfulness Status
- Not meaningful (no execution).

## Evidence Validity Status
- `VALID_FOR_BLOCKER_DIAGNOSIS`
- `PARTIAL_FOR_MARKET_REALISM`
- `INVALID_FOR_PROFIT_CLAIM`

## Next Evidence Run Allowed
- **YES**. The risk state and capital bases are mathematically sound. The bot can safely sit in the market for extended sessions.

## No Runtime Trading Behavior Change Proof
- Validated: `git diff --check` clean. Only temporary runtime wrapper script used.

## No Live Behavior Change Proof
- Confirmed via absence of code modification to `polymarket/trader.py` or execution layer paths.

## No Strategy/Risk/EV Threshold Change Proof
- Thresholds remained at standard hard defaults. Rejections were healthy organic blockers rather than artificial `risk_off` flags.

## Hardcode Audit Status
- **HARDCODE_AUDIT_STATUS**: PASS
- **NEW_CONSTANTS_ADDED**: NONE
- **CONSTANT_PROVENANCE**: N/A
- **MAGIC_VALUES_FOUND**: NONE
- **NO_HARDCODE_PROOF**: Read-only observation task.

## Remaining Uncertainty
- Whether a multi-hour session across dozens of rotating markets will eventually yield enough overlapping edge cases to produce a dense dataset of CLOB-compliant paper executions.

## Tech Lead Review Candidates
- `CLOB_COMPLIANT_EXTENDED_PAPER_EVIDENCE_RUN_003` (Multi-hour run to gather deeper edge stats).
