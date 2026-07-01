# RISK_STATE_PREFLIGHT_BEFORE_NEXT_PAPER_EVIDENCE_RUN_001

## 1. Executive Summary
Recent CLOB-compliant paper evidence runs were 100% blocked by `risk_mode_lockdown:hard_drawdown`. This audit reveals that the `hard_drawdown` condition is an **artificial state bug** introduced during the Paper Research Bankroll separation, not a real trading drawdown or stale state file issue. 

The paper trader correctly initializes `starting_bankroll` and `peak_bankroll` to $200.0 (`PAPER_RESEARCH_BANKROLL_USD`). However, the periodic live wallet reference check overwrites `current_cash_balance` with the actual live wallet balance (e.g., $10.0 or $20.09). This causes the bot to immediately perceive an instantaneous 90-95% drawdown, locking down all trades.

## 2. Root Cause Analysis (Grade B - Source Verified)

In `polymarket/trader.py`, `PolymarketTrader.__init__` correctly isolates the starting paper bankroll:
```python
if self.settings.paper_trading:
    from polymarket.execution.paper_accounting import PAPER_RESEARCH_BANKROLL_USD
    initial_bankroll = PAPER_RESEARCH_BANKROLL_USD  # 200.0
    ...
```

However, during runtime, `_refresh_wallet_reference_balance` fetches the real live wallet balance (e.g. $10.0 or $20.09) and calls `_set_wallet_reference_snapshot`. This chains to `_apply_paper_reference_balance`, which executes:
```python
# polymarket/trader.py:4181
state.current_cash_balance = max(0.0, reference_balance + state.realized_pnl - invested_cost)
```
Where `reference_balance` is the $10.0 (or $20.09) live wallet balance! 

The next time equity is calculated:
```python
# polymarket/trader.py:4342
cash = max(float(state.current_cash_balance), 0.0) # $10.0
equity = max(cash + open_value, 0.0)               # ~$10.0
...
# polymarket/trader.py:4353
state.daily_drawdown_pct = max(0.0, (state.peak_bankroll - equity) / state.peak_bankroll) 
# (200.0 - 10.0) / 200.0 = 95.0%
```

Because `daily_drawdown_pct >= 0.15` (15%), `hard_drawdown_reached` evaluates to `True`, passing `hard_drawdown` to `evaluate_risk_mode()`, triggering `risk_mode_lockdown:hard_drawdown` for all subsequent cycles.

## 3. Evidence of State Variables (Grade A - Runtime Inferred)
- **bot_status.json** (last paper run): `account_balance: 20.09901`
- **risk_log**: `live_reference_bankroll_usd: 10.0`
- **risk_log**: `paper_research_bankroll_usd: 200.0`
- **Decision Engine Blocker**: `risk_mode_lockdown:hard_drawdown`

## 4. Pre-conditions for Next Paper Run
Before authorizing the next extended paper evidence run (`CLOB_COMPLIANT_EXTENDED_PAPER_EVIDENCE_RUN_001`), a Class 6 (Refactor) or Class 7 (Feature) task must correct the wallet reference balance logic in paper mode:
1. `_apply_paper_reference_balance` must NOT overwrite `current_cash_balance` when a separated `PAPER_RESEARCH_BANKROLL_USD` is active.
2. The live reference bankroll must only be stored for metadata/reporting (e.g. `live_reference_bankroll_usd` field), not mathematically applied to the `BankrollState`'s core accounting (which causes the 95% drawdown).

## 5. Conclusion
The paper risk state is artificially broken due to live-wallet leakage into paper cash balances. The system is structurally sound otherwise.

---

## TASK_OUTPUT_CONTRACT

### Task Identity
- Task name: RISK_STATE_PREFLIGHT_BEFORE_NEXT_PAPER_EVIDENCE_RUN_001
- Task class: 2
- Agent roles used: PRIMARY=14_NO_ENTRY_DIAGNOSTICS_AGENT SUPPORTING=03_RISK_MANAGER_AGENT

### Files Changed
- NONE

### Files Read (Not Changed)
- `polymarket/trader.py` — Source logic for bankroll state, wallet refresh, and equity/drawdown calculation.
- `polymarket/risk_modes.py` — `evaluate_risk_mode` definition.
- `runtime/quant_data/risk_log/2026-07-01.jsonl` — Validated risk logging blocker state.
- `runtime/bot_status.json` — Evaluated persisted balance variables.

### Tests Run
- Command: N/A
- Result: NOT_REQUIRED
- Pre-existing failures: NONE

### Evidence
- [Grade B] `polymarket/trader.py` line 4181 `_apply_paper_reference_balance` incorrectly applies the real wallet reference balance to `state.current_cash_balance` during paper runs, breaking the $200.0 research bankroll state.
- [Grade A] `runtime/bot_status.json` confirms `account_balance` was set to the wallet reference balance (~20.099).
- [Grade B] `polymarket/trader.py` line 4353 evaluates `daily_drawdown_pct` using `(peak_bankroll - equity) / peak_bankroll` which yields ~95% in this corrupted state.

### No-Hardcode Audit
- HARDCODE_AUDIT_STATUS: N/A_DOCS_ONLY
- NEW_CONSTANTS_ADDED: NONE
- CONSTANT_PROVENANCE: NONE
- CONFIG_VALUES_USED: NONE
- MAGIC_VALUES_FOUND: NONE
- MAGIC_VALUES_JUSTIFIED: NONE
- MAGIC_VALUES_REJECTED: NONE
- NO_HARDCODE_PROOF: N/A

### Remaining Uncertainty
- None. The root cause for `risk_mode_lockdown:hard_drawdown` is definitively isolated.

### Commits Made
- NONE

### Active Question Status
- CLOSED: Risk-off/hard_drawdown root cause identified.

### Batch 2 Authorization
- NOT AUTHORIZED

### Tech Lead Review Candidates
- PAPER_ACCOUNTING_LOGIC_FIX_001 (Class 6/7)
- EXTENDED_PAPER_EVIDENCE_RUN_001 (Class 3)

### Blockers
- The `current_cash_balance` overwrite bug in `_apply_paper_reference_balance` blocks any meaningful paper strategy evaluation.

### Recommended Review Topics
- Authorize fixing `_apply_paper_reference_balance` logic so the live wallet balance does not corrupt the $200 paper bankroll cache.
