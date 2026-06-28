# EXECUTION CONTRACT — PROXY_WALLET_ALLOWANCE_SEMANTICS_FIX_001

## 1. Target System / Subsystem
- Target system: `polymarket/client.py` and `polymarket/trader.py` (preflight and verification logic).

## 2. Rationale & Change Summary
- Fix verify/preflight allowance semantics to correctly distinguish standard EOA accounts from Proxy Wallet (Signature Type 2) accounts.
- EOA accounts require standard ERC20 USDC allowance.
- Proxy wallets (Signature Type 2) with sufficient deposited CLOB collateral should pass without failing on standard allowance.

## 3. Forbidden Scope & Side Effects Check
- Do NOT start live trading.
- Do NOT place any real orders.
- Do NOT touch sizing or risk models.
- Verified no side effects on strategy scoring or trading loop.

## 4. Specific File Permissions Allowed
- `polymarket/client.py` (read/write)
- `polymarket/trader.py` (read/write)
- `tests/` (read/write)
- `docs/` (read/write)

## 5. Specific File Permissions Blocked
- All other files.

## 6. Sizer & Risk Plan Variables Blocked
- `_risk_plan_zero_diagnostics`
- `_diagnostic_float`
- `_diagnostic_int`
- `_submit_order` execution code

## 7. Configuration Safety Matrix
- Live trading flags remain disabled (`PAPER_TRADING=true`, `LIVE_TRADING_ENABLED=false`).
- Sizing bankroll floor and exposure bounds are untouched.

## 8. Rollback Plan
- Restore files using git:
  ```bash
  git checkout -- polymarket/client.py polymarket/trader.py
  ```

## 9. Verification & Evidence Plan
- Run unit tests to prove correctness of the fix.
- Run verify mode on the actual account to observe `VERIFY PASS` or `GO_WITH_WARNING_PROXY`.

## 10. Task ID & Classification
- Task ID: `PROXY_WALLET_ALLOWANCE_SEMANTICS_FIX_001`
- Class: 7 (FEATURE)
- Tier: STANDARD

## 11. Knowledge Graph Evidence Block
```yaml
knowledge_graph_evidence:
  safety_check_query_id: QUERY-20260628-PROXY-ALLOWANCE-SAFETY
  safety_findings:
    - QS-007: blocks live trading automation; mitigated because changes are limited to preflight checks and verify mode.
  safety_stop_triggered: false
  blast_radius_score: HIGH
  blast_radius_query_id: QUERY-20260628-PROXY-ALLOWANCE-BLAST
  evidence_for_commit_grade: B
  evidence_query_id: N/A
  deferred_history: N/A
  why_deferred_query_id: N/A
  graph_confidence: 0.90
  graph_timestamp: 2026-06-27
  graph_query_ids:
    - QUERY-20260628-PROXY-ALLOWANCE-SAFETY
    - QUERY-20260628-PROXY-ALLOWANCE-BLAST
  stop_condition_triggered: NONE
```

## 12. Human Authorization Check
- Approved by user prompt triggering the task.

## 13. Execution Steps
1. Modify `polymarket/client.py` to support proxy allowance logic in `_preflight_balance_allowance` and `get_balance_allowance`.
2. Modify `polymarket/trader.py` to distinguish wallet types and balance sources in `verify_account_readiness`.
3. Add unit tests for the new semantics.
4. Run `pytest` to verify the tests pass.
5. Run verify mode and verify no exit code 1.
