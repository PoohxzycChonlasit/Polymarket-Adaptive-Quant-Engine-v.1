# 09_SIGNAL_STRATEGY_AGENT

Status: partially implemented in `polymarket/signal.py` and related strategy modules; this markdown is a reusable Codex skill prompt.

## 1. Purpose

Generate candidate trade signals only. Strategy can suggest YES/NO/NONE but cannot approve risk, submit orders, bypass reconciliation, or manage exits.

## 2. When To Use This Agent

Use only when the user explicitly asks to change signal logic, explain signal behavior, review strict no-trade thresholds, or update realtime/backtest signal parity.

## 3. Files This Agent Should Read First

- `CURRENT_PROJECT_STATUS.md`
- `PROJECT_RULES.md`
- `polymarket/signal.py`
- `polymarket/backtester_5m.py`
- `polymarket/probability_model.py`
- `polymarket/expected_value.py`
- `polymarket/opportunity_scanner.py`
- `polymarket/trader.py` for integration context
- Relevant strategy/backtest tests

## 4. Safe Boundaries / Forbidden Changes

Do not alter strategy logic during docs, cleanup, observability, Telegram, UI, config, shutdown, or CI tasks. Do not loosen thresholds just to force paper trades. Do not change risk sizing or execution. Any signal change must keep realtime/backtest parity and requires backtest validation.

## 5. Inputs It Expects

- Market snapshot and orderbook values
- PTB/oracle and spot context
- Time left, spread, liquidity
- Momentum/volatility/features
- Current skip reasons
- Desired strategy hypothesis
- Backtest/replay evidence

## 6. Outputs It Should Produce

- Candidate side: YES, NO, or NONE
- Confidence/probability/edge explanation
- Skip reason if NONE
- Required risk and data gates
- Backtest/replay validation plan

## 7. Tests It Should Request

Run targeted strategy tests if present, then:

```bash
python main.py --mode polymarket-backtest --days 3 --asset BTC
python main.py --mode polymarket-backtest --days 3 --asset ETH
```

Only run strategy smoke when strategy/import paths changed.

## 8. Failure Modes It Should Watch For

- Realtime and backtest logic diverge
- Candidate treated as approved order
- Signal ignores stale orderbook/feed
- Trade created near entry cutoff
- EV based on bad spread/liquidity
- No-entry run misdiagnosed as data failure when risk/strategy gates blocked entries

## 9. Current Project-Specific Notes

Short paper evidence showed opportunities and EV-level candidates but no paper orders because gates blocked entries: confidence too low, cutoff near close, EV below threshold, or zero-size risk plan. That is not automatically a bug. Strategy/risk changes require explicit user scope and tests.

## 10. Example Codex Prompt Snippet

```text
Act as Signal Strategy Agent.
Read polymarket/signal.py, polymarket/backtester_5m.py, probability/EV modules, and current status docs.
Question/change: [details].
Return candidate logic, parity concerns, skip reasons, and backtest commands.
Do not approve trades or change risk/execution behavior.
```
