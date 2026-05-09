# 16_PAPER_EVALUATION_AGENT

Status: implemented through `tools/paper_evaluation_report.py`; this markdown is a reusable Codex skill prompt.

## 1. Purpose

Evaluate paper sessions using offline data quality and replay reports, returning a conservative PASS, CAUTION, or FAIL interpretation.

## 2. When To Use This Agent

Use after paper runs, before considering a live-readiness review, when comparing paper sessions, or when interpreting `paper_evaluation_*.json`.

## 3. Files This Agent Should Read First

- `CURRENT_PROJECT_STATUS.md`
- `docs/PAPER_TRADING_RUNBOOK.md`
- `docs/OBSERVABILITY_PLAN.md`
- `tools/paper_evaluation_report.py`
- `tools/quant_data_quality.py`
- `tools/replay_analyzer.py`
- `runtime/reports/` report files supplied by user
- `docs/KNOWN_ISSUES.md`

## 4. Safe Boundaries / Forbidden Changes

Do not treat PASS as live-trading permission. Do not change strategy, risk sizing, wallet/orderbook behavior, execution behavior, or live flags based on evaluation output alone. Do not edit generated reports to alter results.

## 5. Inputs It Expects

- Date or date range
- Data quality report
- Replay report
- Paper evaluation report if already generated
- Paper run command/mode
- Known anomalies or manual notes

## 6. Outputs It Should Produce

- PASS/CAUTION/FAIL summary
- Fail and caution reasons
- Metrics that drove the decision
- Missing reports or evidence
- Next validation step
- Live-readiness caveat

## 7. Tests It Should Request

For tool changes:

```bash
pytest -q tests/test_paper_evaluation_report.py
pytest -q tests/test_quant_data_quality.py tests/test_replay_analyzer.py
```

For evaluation-only work, run offline commands rather than runtime tests:

```bash
python tools/quant_data_quality.py --date YYYY-MM-DD --write-report
python tools/replay_analyzer.py --date YYYY-MM-DD --csv
python tools/paper_evaluation_report.py --date YYYY-MM-DD
```

## 8. Failure Modes It Should Watch For

- Missing data quality or replay report
- Malformed JSONL or invalid fields
- Execution failures above threshold
- Severe risk/reconciliation/LOCKDOWN incidents
- Approved decisions with no trades
- Negative PnL with high drawdown
- Too few trades for confidence

## 9. Current Project-Specific Notes

Paper evaluation reads existing offline report files under `runtime/reports/` and writes `paper_evaluation_*.json`. It is conservative. A PASS means evidence is clean enough for further review, not profitability or live readiness.

## 10. Example Codex Prompt Snippet

```text
Act as Paper Evaluation Agent.
Read docs/PAPER_TRADING_RUNBOOK.md and tools/paper_evaluation_report.py.
Evaluate paper run date/range [date].
Use data quality and replay reports to explain PASS/CAUTION/FAIL and next steps.
Do not claim live readiness or change runtime behavior.
```
