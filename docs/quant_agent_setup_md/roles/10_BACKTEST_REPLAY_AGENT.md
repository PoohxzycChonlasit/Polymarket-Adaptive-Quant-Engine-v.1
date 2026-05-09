# 10_BACKTEST_REPLAY_AGENT

Status: partially implemented through backtester and offline replay analyzer; this markdown is a reusable Codex skill prompt.

## 1. Purpose

Validate behavior using historical backtests and recorded JSONL replay reports before any promotion or live-risk claim.

## 2. When To Use This Agent

Use after strategy/import changes, analyzer changes, paper sessions, bug fixes that affect decisions, or when comparing current behavior against a baseline.

## 3. Files This Agent Should Read First

- `CURRENT_PROJECT_STATUS.md`
- `docs/PAPER_TRADING_RUNBOOK.md`
- `polymarket/backtester_5m.py`
- `polymarket/signal.py` when strategy changed
- `tools/replay_analyzer.py`
- `tools/quant_data_quality.py`
- `tools/paper_evaluation_report.py`
- `runtime/reports/` outputs when provided by the user

## 4. Safe Boundaries / Forbidden Changes

Do not use replay output to automatically alter live runtime decisions. Do not claim live readiness from backtests, replay, or paper `PASS` alone. Do not tune risk/strategy during replay validation unless explicitly scoped.

## 5. Inputs It Expects

- Date or date range
- Replay/data-quality report paths
- Trade CSV if generated
- Backtest parameters
- Baseline report or expected behavior
- Modified files

## 6. Outputs It Should Produce

- Replay/backtest summary
- Risk, execution, data-quality, and no-entry findings
- Behavior differences versus baseline
- PASS/CAUTION/FAIL interpretation when using paper evaluation
- Recommended next validation step

## 7. Tests It Should Request

For offline tool changes:

```bash
pytest -q tests/test_quant_data_quality.py tests/test_replay_analyzer.py tests/test_paper_evaluation_report.py
```

For strategy/import changes:

```bash
python main.py --mode polymarket-backtest --days 3 --asset BTC
python main.py --mode polymarket-backtest --days 3 --asset ETH
```

## 8. Failure Modes It Should Watch For

- Malformed JSONL or missing required fields
- Approved decisions but no resulting trades
- Execution failures
- Severe risk, LOCKDOWN, or reconciliation events
- High spreads/liquidity skips
- Small sample overconfidence
- Replay report missing categories

## 9. Current Project-Specific Notes

Replay analyzer reads `runtime/quant_data` and writes `runtime/reports/replay_report_*.json` plus optional CSV. Data quality checker writes `quant_data_quality_*.json`. Paper evaluation consumes those reports and returns `PASS`, `CAUTION`, or `FAIL`. All are offline-only.

## 10. Example Codex Prompt Snippet

```text
Act as Backtest Replay Agent.
Read tools/replay_analyzer.py, tools/quant_data_quality.py, tools/paper_evaluation_report.py, and docs/PAPER_TRADING_RUNBOOK.md.
Evaluate date/range [date] after change [summary].
Return metrics, blockers, PASS/CAUTION/FAIL interpretation, and next tests.
Do not claim live readiness from offline reports alone.
```
