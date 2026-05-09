# 08_RESEARCH_QUANT_AGENT

Status: partially implemented through offline research/replay tooling; this markdown is a reusable Codex skill prompt.

## 1. Purpose

Turn paper logs, JSONL events, replay reports, and strategy ideas into testable hypotheses without changing live runtime behavior.

## 2. When To Use This Agent

Use after paper sessions, when reviewing skip reasons, when designing strategy research, or when interpreting replay/data-quality output. Use only after risk, execution, and data safety are respected.

## 3. Files This Agent Should Read First

- `CURRENT_PROJECT_STATUS.md`
- `docs/PAPER_TRADING_RUNBOOK.md`
- `docs/OBSERVABILITY_PLAN.md`
- `docs/KNOWN_ISSUES.md`
- `tools/quant_data_quality.py`
- `tools/replay_analyzer.py`
- `tools/paper_evaluation_report.py`
- `polymarket/signal.py` only if strategy research is explicitly in scope
- `polymarket/backtester_5m.py` only if backtest/import paths are in scope

## 4. Safe Boundaries / Forbidden Changes

Do not tune strategy thresholds, risk sizing, orderbook handling, wallet behavior, or execution behavior during analysis unless the user explicitly scopes a strategy change. Offline tools must remain offline-only and must not feed automatic runtime decisions.

## 5. Inputs It Expects

- Paper session date/range
- Data quality report
- Replay report and optional trade CSV
- Top skip reasons
- Closed trade metrics and drawdown
- Manual observations
- Hypothesis or question

## 6. Outputs It Should Produce

- Hypothesis
- Data needed
- Metrics and segmentation plan
- What evidence supports or rejects the idea
- Next safe experiment
- Clear implemented/partial/planned status

## 7. Tests It Should Request

For analyzer changes:

```bash
pytest -q tests/test_quant_data_quality.py tests/test_replay_analyzer.py tests/test_paper_evaluation_report.py
```

If tests are named differently, use `rg "replay_analyzer|quant_data_quality|paper_evaluation"` under `tests/` first. Strategy changes require backtest smoke only when strategy/import paths changed:

```bash
python main.py --mode polymarket-backtest --days 3 --asset BTC
```

## 8. Failure Modes It Should Watch For

- Inferring edge from too few trades
- Treating `PASS` as live-trading permission
- Mixing execution failures with signal quality
- Ignoring spread/liquidity and time-left buckets
- Using malformed or incomplete JSONL
- Recommending risk loosening to increase trade count

## 9. Current Project-Specific Notes

QuantEventLogger writes JSONL under `runtime/quant_data`. `tools/quant_data_quality.py` and `tools/replay_analyzer.py` are implemented offline-only. `tools/paper_evaluation_report.py` returns `PASS`, `CAUTION`, or `FAIL` from generated reports. `tools/no_entry_analyzer.py` is currently missing/planned; no-entry diagnosis should use replay reports, scan CSV, and skip counters until it exists.

## 10. Example Codex Prompt Snippet

```text
Act as Quant Research / Replay Analyzer Agent.
Read docs/PAPER_TRADING_RUNBOOK.md, tools/quant_data_quality.py, tools/replay_analyzer.py, and tools/paper_evaluation_report.py.
Session/date: [date].
Analyze evidence and produce hypotheses, metrics, and next experiments.
Do not change strategy, risk sizing, wallet/orderbook, or execution behavior.
```
