# BANKROLL_RANK_ENGINE_001
> **TASK_CLASS: 7 — FEATURE**
> **PRIMARY: 03_RISK_MANAGER_AGENT | SUPPORTING: 11_OBSERVABILITY_INCIDENT_AGENT, 07_TEST_CI_AGENT**
> **Date: 2026-06-28 | Evidence Grade: A (runtime observed) + B (source-code verified) + C (test verified)**

---

## 1. Runtime Implementation

We have implemented the stateful `BankrollRankEngine` inside [`polymarket/bankroll_rank_engine.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/bankroll_rank_engine.py) and integrated it into [`polymarket/trader.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py).

### Core Quality Metrics
- **Streaks**: Computes consecutive wins/losses by reading closed positions sorted by exit time from `PositionTracker`.
- **Volatility**: Tracks an equity history buffer (up to 50 points) and calculates standard deviation to capture curve variance.
- **Recovery Factor**: Compares realized PnL against dollar-based maximum drawdown.
- **Hysteresis State transitions**: Smoothly transitions between `HEALTHY`, `DEGRADED`, and `CRITICAL` capital states using an exponential moving average (EMA, $\alpha=0.15$) and hysteresis buffers.
- **Risk Profiling**: Dynamically maps to `expected_risk_profile` (`AGGRESSIVE`, `MODERATE`, `CONSERVATIVE`) to inform future sizing logic.

---

## 2. Telemetry Fields

A new JSONL telemetry event `log_bankroll_rank_evaluation` is emitted on every portfolio balance synchronization:
```json
{
  "timestamp": "2026-06-28T00:00:00Z",
  "equity": 500.00,
  "capital_score": 0.8500,
  "capital_state": "HEALTHY",
  "promotion_candidate": false,
  "demotion_candidate": false,
  "expected_risk_profile": "AGGRESSIVE",
  "consecutive_wins": 2,
  "consecutive_losses": 0,
  "recovery_factor": 10.0,
  "volatility": 0.0
}
```

These fields are also packed into position metadata on open and carried flat into the `log_trade_close` event stream:
- `capital_score`
- `capital_state`
- `promotion_candidate`
- `demotion_candidate`
- `expected_risk_profile`

---

## 3. Replay Support

[`tools/canonical_trade_context_builder.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/canonical_trade_context_builder.py) has been upgraded to extract these 5 capital evaluation fields from the event streams. This ensures they are fully populated in the compiled Completed Trades v1 datasets, allowing offline backtests and replays to leverage actual historical capital quality state.

---

## 4. Tests

Added [`tests/test_bankroll_rank_engine.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tests/test_bankroll_rank_engine.py) to cover:
- Streak calculation (wins vs. losses).
- Volatility tracking over varying equity paths.
- Capital score computation under drawdown and streak penalties.
- Hysteresis boundary crossings and state transitions (`HEALTHY` $\leftrightarrow$ `DEGRADED` $\leftrightarrow$ `CRITICAL`).
- Integration inside `PolymarketTrader._update_bankroll_state` and event emission (PASS).

---

## TASK_OUTPUT_CONTRACT

### Task Identity
- Task name: BANKROLL_RANK_ENGINE_001
- Task class: 7 (FEATURE)
- Agent roles used: PRIMARY=03_RISK_MANAGER_AGENT SUPPORTING=11_OBSERVABILITY_INCIDENT_AGENT, 07_TEST_CI_AGENT

### Files Changed
- `polymarket/bankroll_rank_engine.py` — [NEW] rank engine implementation
- `polymarket/trader.py` — integrated evaluation, metadata packing, and event logging
- `tools/canonical_trade_context_builder.py` — added fields extraction support
- `tests/test_bankroll_rank_engine.py` — [NEW] unit test suite
- `docs/reports/BANKROLL_RANK_ENGINE_001.md` — [NEW] validation report
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json` — updated
- `docs/operations/TASK_QUEUE_001.json` — updated
- `docs/operations/loop_memory/LOOP_MEMORY_20260627_001.json` — updated

### Files Read (Not Changed)
- `polymarket/bankroll_tiers.py` — read tier and config details

### Tests Run
- Command: `.venv\Scripts\pytest tests/test_bankroll_rank_engine.py`
- Result: PASS 3/3

### Evidence
- [Grade C] pytest successfully executes and verifies engine transition boundaries.
- [Grade A] Event logs capture `log_bankroll_rank_evaluation` and compile cleanly with canonical builder.

### Remaining Uncertainty
- None.

### Commits Made
- NONE

### Active Question Status
- CLOSED: Bankroll Rank Engine implemented.

### Batch 2 Authorization
- NOT AUTHORIZED

### Recommended Next Task
- SIZE_SHARP_ENGINE_DESIGN_001 (Class 2 — DESIGN)
