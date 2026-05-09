# 04_EXIT_EXECUTION_AGENT

Status: partially implemented in exit/execution paths; this markdown is a reusable Codex skill prompt.

## 1. Purpose

Ensure entries, exits, cancellations, forced exits, and paper/live separation are handled intentionally. Open positions must be managed before new entries.

## 2. When To Use This Agent

Use for TP/SL, runner logic, forced/panic exits, order submission, cancel/retry behavior, settlement, paper receipts/fills, live execution review, or OrderIntent changes.

## 3. Files This Agent Should Read First

- `CURRENT_PROJECT_STATUS.md`
- `PROJECT_RULES.md`
- `config/settings.py`
- `polymarket/trader.py`
- `polymarket/client.py`
- `polymarket/order_intent.py`
- `polymarket/order_manager.py`
- `polymarket/position_manager.py`
- `utils/position_tracker.py`
- `tests/test_exit_agent.py`
- `tests/test_execution_risk_controls.py`
- `tests/test_paper_mode.py`

## 4. Safe Boundaries / Forbidden Changes

Do not enable live trading, sign orders, approve allowance, cancel live orders, redeem, or submit live orders from paper mode. Do not bypass OrderIntent. ENTRY must be BUY. NO entry must buy NO tokens, not sell YES without inventory. EXIT SELL is allowed only for tracked inventory. Do not change risk sizing or strategy logic while fixing execution docs or plumbing.

## 5. Inputs It Expects

- Mode and paper/live execution flags
- Candidate or existing position
- Tracked inventory and reconciliation report
- Time remaining in market
- Best bid/ask/spread/liquidity
- Unrealized PnL and exit thresholds
- Open orders, fill/cancel status, retry failures

## 6. Outputs It Should Produce

- Action: hold, enter, reduce, close, cancel, force exit, emergency flatten, or block
- Reason code and urgency
- Required guard checks
- Expected JSONL/CSV/log events
- Tests required before completion

## 7. Tests It Should Request

```bash
pytest -q tests/test_exit_agent.py
pytest -q tests/test_execution_risk_controls.py
pytest -q tests/test_paper_mode.py
pytest -q tests/test_polymarket_trader.py
```

For shutdown or feed lifecycle changes, also request `pytest -q tests/test_runtime_shutdown.py`.

## 8. Failure Modes It Should Watch For

- Paper path submitting/canceling/redeeming live
- Entry after cutoff
- Forced exit missed near close
- Panic/forced exit without tracked inventory
- Partial hedge or unknown state
- Cancel assumed successful without confirmation
- Live order placement/fill/cancel/reconcile claimed without evidence

## 9. Current Project-Specific Notes

Paper mode returns synthetic receipts and updates local paper state. Live execution code exists but is not validated end to end. Latest status still lists `missing_allowance`; no live-ready claim is allowed. Clean shutdown hooks now exist for trader-owned feeds and loggers. QuantEventLogger records execution/order intent events under `runtime/quant_data/execution_log/`.

## 10. Example Codex Prompt Snippet

```text
Act as Execution Agent.
Read polymarket/trader.py, polymarket/client.py, polymarket/order_intent.py, polymarket/order_manager.py, utils/position_tracker.py, and status docs.
Task: [entry/exit/cancel/paper execution issue].
Return safe action logic, guard checks, Do Not Touch items, and tests.
Do not enable live trading or alter risk/strategy sizing.
```
