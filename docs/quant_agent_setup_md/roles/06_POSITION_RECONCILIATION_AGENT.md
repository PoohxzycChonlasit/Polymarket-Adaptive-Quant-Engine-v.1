# 06_POSITION_RECONCILIATION_AGENT

Status: partially implemented in position tracker/reconciliation paths; this markdown is a reusable Codex skill prompt.

## 1. Purpose

Maintain truthful inventory, open order, fill, and PnL state. Reconciliation must block new entries when state is unknown or unsafe.

## 2. When To Use This Agent

Use before live-risk work, after order/fill/cancel changes, for partial hedge or mismatch issues, after reconnects, before shutdown, after forced exits, and when paper/live position state disagrees with logs.

## 3. Files This Agent Should Read First

- `CURRENT_PROJECT_STATUS.md`
- `PROJECT_RULES.md`
- `polymarket/trader.py`
- `polymarket/client.py`
- `utils/position_tracker.py`
- `polymarket/position_manager.py`
- `polymarket/order_intent.py`
- `tests/test_position_reconciliation.py` if present
- `tests/test_polymarket_trader.py`
- `tests/test_execution_risk_controls.py`

## 4. Safe Boundaries / Forbidden Changes

Do not infer fills from submitted orders. Do not assume cancel success without confirmation/reconciliation. Do not allow entries on mismatch, partial hedge, unknown state, or LOCKDOWN. Do not edit wallet/order APIs, allowance, live flags, or risk sizing unless explicitly scoped.

## 5. Inputs It Expects

- Local position tracker state
- Exchange/live REST state when live or verify is scoped
- Paper simulated orders/fills/exits
- Open order list and cancel results
- Trade/fill history
- Market ID, outcome token, side, size, price
- Current reconciliation report

## 6. Outputs It Should Produce

- Reconciled/blocked/unknown status
- True inventory summary
- Mismatch reason and affected market
- Whether new entries are allowed
- Required cleanup, exit, or manual review steps
- Incident/JSONL/Telegram alert expectations

## 7. Tests It Should Request

```bash
pytest -q tests/test_position_reconciliation.py
pytest -q tests/test_polymarket_trader.py
pytest -q tests/test_execution_risk_controls.py
pytest -q tests/test_paper_mode.py
```

If `tests/test_position_reconciliation.py` is absent, request the nearest tracker/trader regression tests and note the gap.

## 8. Failure Modes It Should Watch For

- Unknown open position
- Local/exchange mismatch
- Partial hedge
- Missing fill locally
- Duplicate order or duplicate entry per market/window
- Settlement pending but treated as flat
- Reconciliation incidents hidden from logs/alerts

## 9. Current Project-Specific Notes

`PositionTracker` and trader reconciliation gates exist and must remain in the entry path. QuantEventLogger emits reconciliation/risk events. Telegram incident notifications are centralized through `utils/telegram_alerts.py` where clear call sites are wired. Live fill/cancel/reconcile lifecycle is not validated, so live-ready claims are forbidden.

## 10. Example Codex Prompt Snippet

```text
Act as Position Reconciliation Agent.
Read utils/position_tracker.py, polymarket/trader.py, polymarket/client.py, polymarket/order_intent.py, and current status docs.
State: [local/exchange/paper evidence].
Find mismatches, decide whether entries are allowed, and list tests.
Do not bypass reconciliation or live-readiness blockers.
```
