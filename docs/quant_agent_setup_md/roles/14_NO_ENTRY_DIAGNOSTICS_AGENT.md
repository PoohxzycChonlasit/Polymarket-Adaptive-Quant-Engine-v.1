# 14_NO_ENTRY_DIAGNOSTICS_AGENT

Status: planned as a dedicated tool; diagnostic workflow is usable through existing logs, JSONL, replay, and paper reports. `tools/no_entry_analyzer.py` is not present as of this sync.

## 1. Purpose

Explain zero-trade paper runs without weakening safety gates. Separate healthy no-entry outcomes from data, risk, or execution regressions.

## 2. When To Use This Agent

Use when paper runs produce no orders/fills/exits, when skip reasons dominate, when risk plans return zero size, or when the user asks why the bot is not trading.

## 3. Files This Agent Should Read First

- `CURRENT_PROJECT_STATUS.md`
- `docs/PAPER_TRADING_RUNBOOK.md`
- `docs/KNOWN_ISSUES.md`
- `polymarket/trader.py`
- `polymarket/realtime_logger.py`
- `utils/quant_event_logger.py`
- `tools/replay_analyzer.py`
- `tools/quant_data_quality.py`
- `tools/paper_evaluation_report.py`
- `tools/no_entry_analyzer.py` if it exists in the future

## 4. Safe Boundaries / Forbidden Changes

Do not loosen confidence, EV, cutoff, risk size, bankroll floor, exposure, drawdown, or reconciliation gates to force trades. Do not alter strategy/risk/execution during diagnostics unless the user explicitly scopes a follow-up implementation.

## 5. Inputs It Expects

- Paper run date/range
- Scan CSV path or summary
- JSONL quant data availability
- Replay/data-quality/paper evaluation reports
- Top skip reasons
- Approved/rejected decision counts
- Orderbook availability evidence
- Risk zero-size reasons

## 6. Outputs It Should Produce

- Ranked explanation for no trades
- Evidence by category: data, signal, risk, timing, execution
- Whether zero trades are expected or suspicious
- Offline commands to run
- Follow-up task recommendation

## 7. Tests It Should Request

For docs/analysis only, no runtime tests. If a future `tools/no_entry_analyzer.py` is added, request its focused tests plus:

```bash
pytest -q tests/test_quant_data_quality.py tests/test_replay_analyzer.py tests/test_paper_evaluation_report.py
```

## 8. Failure Modes It Should Watch For

- `SKIP no_orderbook` returning for valid active markets
- Many approved decisions but no paper orders
- Risk plan zero size on tiny bankroll
- Entry cutoff near market close
- Confidence or EV below threshold
- Reconciliation or LOCKDOWN blocking entries
- Malformed JSONL or missing scan logs

## 9. Current Project-Specific Notes

Latest evidence showed no paper trades in a short run because confidence, EV, entry cutoff, and zero-size risk gates blocked entries despite orderbook data being available. This is not automatically a bug. A dedicated no-entry analyzer is planned/missing; use replay reports and skip counters for now.

## 10. Example Codex Prompt Snippet

```text
Act as No-Entry Diagnostics Agent.
Read docs/PAPER_TRADING_RUNBOOK.md, tools/replay_analyzer.py, tools/quant_data_quality.py, tools/paper_evaluation_report.py, and current status docs.
Run/date evidence: [summary or paths].
Explain why no entries happened and whether it is expected, suspicious, or blocked by data quality.
Do not change strategy or risk thresholds.
```
