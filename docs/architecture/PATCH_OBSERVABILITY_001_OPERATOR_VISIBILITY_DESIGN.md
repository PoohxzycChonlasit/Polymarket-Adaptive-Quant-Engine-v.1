# DESIGN SPECIFICATION — PATCH_OBSERVABILITY_001_OPERATOR_VISIBILITY

This document outlines the design for the re-scoped, operator-focused visibility patch.

---

## A. Entry Funnel Panel

### Objective
Track and display candidate progression through the decision pipeline to show counts, conversion rates, and the top blocker/bottleneck in real time.

### Sourcing
Add the following fields to `PaperSessionStats` in [polymarket/trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py):
- `funnel_candidates: int = 0`
- `funnel_orderbook_ready: int = 0`
- `funnel_confidence_pass: int = 0`
- `funnel_ev_pass: int = 0`
- `funnel_delta_pass: int = 0`
- `funnel_risk_size_pass: int = 0`
- `funnel_trade_open: int = 0`

These counters are incremented sequentially at the end of each candidate's evaluation in `_analyze_market_quant()`.

### Layout
In [utils/display.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/display.py), implement `_entry_funnel_panel(self, spec: DashboardLayout) -> Panel` displaying:
```text
ENTRY FUNNEL

Candidates:      {candidates}
Orderbook Pass:  {ob_ready} ({ob_ready_pct}%)
Confidence Pass: {confidence} ({confidence_pct}%)
EV Pass:         {ev} ({ev_pct}%)
Delta Pass:      {delta} ({delta_pct}%)
Risk Size Pass:  {risk} ({risk_pct}%)
Trade Open:      {open} ({open_pct}%)

Top Bottleneck:
{top_bottleneck} ({top_bottleneck_count})
```
Where `top_bottleneck` and `top_blocker_count` are resolved from the most common element in the `skipped_reasons` Counter.

---

## B. Risk Mode Explanation

### Objective
Provide human-readable reasons and exit release conditions for each active risk mode.

### Schema
When displaying the risk mode, the UI reads the state parameters and prints:
- `NORMAL`:
  - **Reason**: Baseline trading conditions.
  - **Exit Condition**: None.
- `DEFENSIVE`:
  - **Reason**: 2 consecutive losses OR daily drawdown $\ge 2\%$.
  - **Exit Condition**: 1 win to reset streak OR daily drawdown $< 2\%$.
- `MICRO_RECOVERY`:
  - **Reason**: 3 consecutive losses OR daily drawdown $\ge 4\%$.
  - **Exit Condition**: 1 win to reset streak OR daily drawdown $< 4\%$.
- `LOCKDOWN`:
  - **Reason**: Hard daily drawdown $\ge 15\%$ OR duplicate order detection.
  - **Exit Condition**: Requires manual supervisor recovery.

---

## C. Telegram Heartbeat V3

### Objective
Redesign the hourly Telegram heartbeat summary to deliver high-priority operational metrics (liveness, trading activity, top blocker, and risk mode) in a structured format.

### Layout
```text
🟢 ALIVE | {mode}

Run: {run_id}
Uptime: {uptime}

Cycles: {cycles}
Candidates: {candidates}
Trades: {trades}

Top Blocker:
{top_blocker}

Risk Mode:
{risk_mode}

PnL:
{pnl} USDC
WR: {win_rate}%
```
- `{mode}`: `PAPER` or `LIVE`
- `{run_id}`: Truncated to 8 characters.
- `{uptime}`: Formatted as `HH:MM:SS`.
- `{cycles}`: Count of main loop cycles.
- `{candidates}`: `funnel_candidates`.
- `{trades}`: `funnel_trade_open`.
- `{top_blocker}`: The most frequent skip reason and its percentage of candidates.
- `{risk_mode}`: Current risk mode name and reason.
- `{pnl}`: Session realized PnL.
- `{win_rate}`: Session win rate percentage.
