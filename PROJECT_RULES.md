# PolyTrade Crypto Scalper — Project Rules

> **Version:** 2.0 | **Revised:** 2026-04-19
> Rules are living guidelines — update when the project evolves, but never lower safety standards without documented justification.

---

## 1. Project Identity

- **Project name:** `PolyTrade Crypto Scalper`
- **Python version:** `3.11+`
- **Primary domains:**
  - `Polymarket Bot` — binary prediction markets via `py-clob-client` on Polygon L2
  - `Pure Quant Engine` — Sub-second mathematical signal processing (Z-Score, ATR, Momentum)
  - `Smart Stop Loss` — Dynamic recovery system (v3.6)

---

## 2. Architecture Rules

- Keep shared logic inside `config/` and `utils/`.
- `main.py` is the only top-level CLI entrypoint — all modes go through it.
- **Strict Rule:** No AI/LLM API calls in the real-time execution loop.
- All code must be deterministic and unit-testable.

---

## 3. Coding Standards

- Use `snake_case` for files, functions, variables, and module names.
- Add type hints to every function signature and return value — no exceptions.
- Prefer small, focused modules over large files; keep files under 300 lines where possible.
- Write docstrings on all public classes and non-trivial functions.
- Keep business logic deterministic and unit-testable — no hidden side effects.
- Avoid global mutable state; pass dependencies explicitly.
- All secrets via `.env` and `SecretStr` — never hardcoded.
- Maintain a `.env.example` with all required keys and empty/placeholder values.

---

## 4. Strategy Development & Validation Cycle

This is the mandatory improvement loop. Every strategy change must go through it in order.

```
[Code Change] → [Backtest] → [Metric Gate] → [Paper/Dry-Run] → [Live Staging] → [Live Full]
                    ↑                                                      |
                    └──────────── [Iterate if failing] ←──────────────────┘
```

### 4.1 Backtest Requirements

- Run backtest on **minimum 6 months** of historical data before any deployment.
- Recommended range: 1 year (e.g. `--timerange 20240101-20250101`).
- Backtest must produce artifacts in `backtest_results/`:
  - `backtest_summary.json` — win rate, profit factor, Sharpe ratio
  - `equity_curve.csv` — drawdown visualization
  - `trades.csv` — individual trade log

**Minimum Passing Criteria (all must be met):**

| Metric | Minimum | Target |
|--------|---------|--------|
| Sharpe Ratio | > 0.8 | > 1.5 |
| Max Drawdown | < 20% | < 10% |
| Win Rate | > 45% | > 55% |
| Profit Factor | > 1.2 | > 1.8 |
| Total Trades | > 50 | > 200 |

- If any metric fails, **iterate the strategy and re-backtest** — do not move forward.
- Run hyperopt after a passing backtest to find optimal parameters.

### 4.2 Paper Trading / Dry-Run Validation

- After a passing backtest, run in **paper/dry-run mode for minimum 48 hours** before live.
- `PAPER_TRADING=true` and `CRYPTO_DRY_RUN=true` are defaults — explicit action required to disable.
- Monitor `scan_log.csv` for quality of signals during paper run.
- Dry-run P&L must directionally align with backtest expectations before going live.

### 4.3 Live Trading Gates

Live trading is only permitted when ALL of the following are confirmed:

- [ ] Backtest passes all minimum criteria above
- [ ] 48+ hours dry-run/paper with no critical errors
- [ ] No open bug in risk management or order execution logic
- [ ] Human review for any first live order

**Live staging (first 2 weeks):**
- Max position size: **0.5% per trade** (half the normal 1% limit)
- Manual review required before any order > $50
- Monitor daily; review weekly

---

## 5. Risk Management Rules

These are hard limits — enforced in code, never overridden at runtime.

| Parameter | Value | Location |
|-----------|-------|----------|
| Max risk per trade | 0.5% - 2.5% (Tiered) | `settings.py` |
| Max daily drawdown | 10% | `settings.py` |
| Kelly fraction cap | 25% | `risk_manager.py` |
| Smart Stop-Loss | 70% - 90% (Dynamic) | `trader.py` |

- Every trade **must have a stop-loss** — trades without one are automatically rejected.
- Reject trades where spread > 2% of mid price (liquidity too low).
- If data is stale (> 5 minutes old), **skip trading** — do not estimate.
- If daily drawdown limit is hit, **halt all trading for the day** — no exceptions.
- If agent outputs conflict, prefer `hold` or `skip` over forcing a trade.

---

## 6. AI Guidelines (Offline Only)

### 6.1 Role of AI
- **Strict Rule:** AI (LLMs, API calls to Claude/OpenAI) is **strictly forbidden** in the real-time execution loop (`signal.py`, `trader.py`).
- The system operates on a **Pure Quant Engine** (math/statistics).
- AI is only permitted for **Offline Analysis**, running asynchronously to read logs and suggest optimizations.

### 6.2 Offline AI Analyst Protocol
- The AI Analyst reads `scan_log.csv` and `backtest_summary.json`.
- The AI Analyst outputs Markdown reports and Telegram alerts with actionable tweaks for `config/settings.py`.
- Humans must review and manually apply the AI's suggested parameter changes. The AI should not autonomously rewrite `settings.py`.

---

## 7. Continuous Improvement Rules

### 7.1 Performance Monitoring

- Review `scan_log.csv` daily — check edge distribution, signal frequency, confidence trend.
- Run `daily_report.py` every trading day and save the output.
- If win rate drops below 45% over any 20-trade window → **pause and re-backtest**.
- If Sharpe drops below 0.5 over any 30-day window → **enter paper trading mode** until fixed.

### 7.2 Strategy Iteration

- Improve strategy parameters via **hyperopt** — do not manually tune without data evidence.
- Keep hyperopt results with their corresponding backtest in `backtest_results/` with timestamps.
- After any strategy change: full backtest required before re-deploying to paper or live.
- Do not optimize for a single metric — optimize for the composite score:
  ```
  Score = Sharpe × (1 - max_drawdown) × profit_factor
  ```

### 7.3 Agent Improvement

- When an agent consistently produces low-confidence or wrong decisions:
  1. Review the last 20 agent outputs in logs
  2. Identify the failure pattern
  3. Update the prompt with a specific corrective rule
  4. Test on 10+ historical scenarios
  5. Deploy and monitor for 24 hours

---

## 8. Logging & Error Handling

- Every module uses structured logging via `utils/logger.py` — no `print()` in production code.
- Every external API call must have: retry logic (tenacity), timeout, and graceful failure.
- Never swallow exceptions silently — log with full context or re-raise.
- Log all: order decisions, rejections, risk failures, agent outputs, scan results.
- Console logs: human-readable via Rich. File logs: structured JSON.
- Log rotation: keep last 30 days, then archive.

---

## 9. Operational Rules

### 9.1 During Normal Operation

- Bot runs in paper/dry-run by default — requires explicit env change for live.
- If data quality is poor (Quality Flag: `stale` or `incomplete`), skip trading.
- If uncertainty is high (confidence < 0.6), reduce size to 50% or skip.
- WebSocket listener must parse and route market events — do not run with logging-only mode in production.

### 9.2 Emergency Stop Conditions

Immediately halt all trading and alert operator if:

- Daily drawdown exceeds 3%
- Three consecutive unexpected rejections from Polymarket API
- Claude API returns errors on > 50% of calls in a 10-minute window
- Any uncaught exception in `risk_execution_agent.py` or `order_manager.py`

### 9.3 Deployment Checklist

Before any deployment (paper or live):

- [ ] `.env.example` is up to date with all required keys
- [ ] All unit tests pass (`pytest tests/`)
- [ ] No critical violations in code (no hardcoded secrets, no bare `except:`)
- [ ] Backtest artifacts present for active strategy
- [ ] Logging configured and output confirmed

---

## 10. Testing Rules

- Unit tests required for: all agents, risk_manager, position_tracker, order_manager.
- Tests use mocks for external APIs — never call real APIs in unit tests.
- Integration tests (real API, test credentials) required before live deployment.
- Minimum coverage target: 80% on `utils/`, `ai_agents/`, `polymarket/`.
- After any bug fix: add a regression test before closing the issue.

---

## 11. Violation Handling

If a rule must be temporarily bypassed:

1. Document the bypass with reason and expected duration in `CURRENT_PROJECT_STATUS.md`.
2. Create a task to resolve it.
3. Never bypass risk management rules (Section 5) — those are absolute.
4. Never bypass stop-loss, max drawdown, or Kelly cap rules under any circumstance.
