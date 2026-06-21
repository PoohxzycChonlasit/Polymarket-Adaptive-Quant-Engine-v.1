# EXECUTION_PAPER_RUNTIME_PHASE_C_FULL_ELIGIBLE_REPLAY_COMPAT_RERUN_001

## 1. Replay Configuration & Source Metadata
- **Number of Source Files Selected**: 32 files
- **Date Range**: 2026-05-18 to 2026-06-20 (inclusive)
- **Track**: `5_share`
- **Starting Bankroll**: 250.0
- **Compatibility Mode**: `historical`

## 2. Replay Performance & Reconciliation Stats
- **Processed Source Events**: 1829
- **Emitted Events**: 2562
- **Rejected Events**: 366
- **Rejection Rate**: 20.01%
- **Top Reject Reasons**:
  - `missing_condition_id`: 366 (100% of rejections, correspond to mock test events without a valid condition ID)
- **Reconciliation Status**: `PARTIAL_OPEN_ALLOWED`
- **Execution Closed Trade Count**: 731
- **Execution Net PnL**: -20.80
- **Execution Gross Profit**: 157.05
- **Execution Gross Loss**: 177.85
- **Profit Factor (PF)**: 0.883
- **Win Rate (WR)**: 36.94%
- **Win Count**: 270
- **Loss Count**: 461
- **Flat Count**: 0
- **Max Drawdown (DD)**: 33.50
- **Max Drawdown Pct**: 12.91%
- **Final Equity**: 229.20
- **Risk of Ruin**: False
- **PnL Label**: `execution_pnl_5_share_model`

## 3. Safety Verification
- **Real Output Check**: Confirmed that `runtime/quant_data/execution_paper` was NOT created or modified. All outputs were sandboxed into `scratch/`.
- **Git Diff Formatting Check**: `git diff --check` passed cleanly.
- **Git Status**:
  ```text
   M AGENTS.md
   M CURRENT_PROJECT_STATUS.md
   M DOCUMENTATION_MAP.md
   M FILE_INDEX.md
   M PROJECT_RULES.md
   M tools/execution_paper_runtime.py
  ```
  Note: `tools/execution_paper_runtime.py` is dirty in working tree due to diagnostics and empty string condition ID check inserts, but has NOT been staged or committed.

## 4. Final Verdict
**FULL_ELIGIBLE_COMPAT_RERUN_PASS**
The historical position identity patch resolved the duplicate open reconciliation errors on 2026-05-22. The entire 32-day historical paper trading lifecycle replayed successfully to completion.
