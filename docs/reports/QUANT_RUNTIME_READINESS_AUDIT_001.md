# QUANT RUNTIME READINESS AUDIT 001

**Date:** 2026-06-27 · **Scope:** Full repository code scan · **Source of truth:** Implementation, not documentation

---

## 1. RUNTIME CAPABILITY INVENTORY

| Subsystem | File | Status | Notes |
|-----------|------|--------|-------|
| **Market Feed** | `polymarket/market_feed.py`, `polymarket/gamma_fetcher.py` | ✅ PRESENT | Binance feed + Gamma market discovery operational |
| **Orderbook (WebSocket)** | `polymarket/client.py` | ✅ PRESENT | CLOB WebSocket + REST fallback working |
| **Oracle Price Feed** | `polymarket/oracle_price_feed.py` | ✅ PRESENT | PTB virtual price tracking |
| **Signal** | `polymarket/signal.py` | ✅ PRESENT | Reversion + sniper + trend signals, regime logic |
| **Probability Model** | `polymarket/probability_model.py` | ✅ PRESENT | Binary probability estimate from signal+imbalance |
| **Expected Value** | `polymarket/expected_value.py` | ✅ PRESENT | EV calculation, dynamic min_ev, best trade selector |
| **Decision Engine** | `polymarket/trader.py` (cycle loop) | ✅ PRESENT | Full go/no-go decision pipeline |
| **Inventory Engine** | `polymarket/position_manager.py` | ✅ PRESENT | State classification, stale cancel, EV exit |
| **Risk Engine** | `utils/risk_manager.py`, `polymarket/risk_modes.py` | ✅ PRESENT | NORMAL/DEFENSIVE/MICRO/LOCKDOWN, Kelly, daily stop |
| **Bankroll Tiers** | `polymarket/bankroll_tiers.py` | ✅ PRESENT | 5 tiers, hysteresis, rank lock |
| **Position Sizing** | `polymarket/position_sizing.py` | ✅ PRESENT | Rank-aware sizing, multipliers |
| **Position Management** | `polymarket/position_manager.py`, `utils/position_tracker.py` | ✅ PRESENT | Fill tracking, reconciliation |
| **Paper Execution** | `polymarket/virtual_ptb.py`, trader cycle | ✅ PRESENT | Fully operational — paper orders, fills, exits |
| **Order Intent Guard** | `polymarket/order_intent.py` | ✅ PRESENT | ENTRY/EXIT validation, type-safety |
| **Order Manager** | `polymarket/order_manager.py` | ✅ PRESENT | RiskPlan builder |
| **Live Order Placement** | `polymarket/client.py` (`post_order`) | ⚠️ PARTIAL | Code exists; **allowance approval not validated** |
| **Wallet Integration** | `polymarket/client.py` | ⚠️ PARTIAL | Balance reads work; allowance approval gate OPEN |
| **Fill Tracking (live)** | `polymarket/client.py`, `polymarket/position_manager.py` | ⚠️ PARTIAL | Fill read logic present; **live order reconciliation not battle-tested** |
| **Cancel Logic** | `polymarket/client.py` (`cancel_order`) | ✅ PRESENT | Cancel implemented |
| **Backtest** | `polymarket/backtester_5m.py` | ✅ PRESENT | 5M candle backtest with signal replay |
| **Offline Replay** | `tools/replay_analyzer.py` | ✅ PRESENT | JSONL-based decision replay |
| **Dashboard Runtime** | `tools/dashboard_state_aggregator.py` + React | ⚠️ PARTIAL | Aggregator reads JSONL; **frontend polls static JSON file** (not live WebSocket) |
| **Telegram Runtime** | `utils/telegram_alerts.py` | ✅ PRESENT | Startup, entry, exit, risk, critical, summary alerts |
| **Research Logs / JSONL** | `utils/quant_event_logger.py` | ✅ PRESENT | 242 MB today, 24,896 events (2026-06-27) |
| **Runtime Validation** | Paper mode + JSONL | ✅ PRESENT | 7-cycle paper runs with full telemetry |
| **Bootstrap (FLAOS)** | `tools/flaos/bootstrap.py` | ✅ PRESENT | Health check, memory OS, safety memory |
| **Health Engine** | `tools/flaos/log_governance.py`, bootstrap | ✅ PRESENT | Disk monitoring, bootstrap diagnose |
| **Memory OS V2** | `tools/flaos/memory_os.py`, `memory_migrate.py` | ✅ PRESENT | JSONL typed records, MEMORY_INDEX, SAFETY_MEMORY |
| **Knowledge Graph** | `tools/flaos/knowledge_graph.py` | ✅ PRESENT | blast_radius, safety_check, evidence queries |

---

## 2. RUNTIME FLOW AUDIT

```
Market Data (Binance + Gamma)
  ✅ market_feed.py → Binance BTC/ETH price feed
  ✅ gamma_fetcher.py → market discovery, epoch timing
  ✅ oracle_price_feed.py → virtual PTB
         ↓
Orderbook
  ✅ client.py → CLOB WebSocket (primary) + REST fallback
  ✅ _mark_orderbook_refresh → timing telemetry in TraderObservabilityHelper
         ↓
Signal
  ✅ signal.py → reversion/sniper/trend, regime diagnostics
  ✅ regime_diagnostics.py → volatility/compression/trend
         ↓
Probability
  ✅ probability_model.py → estimate_probability()
         ↓
Expected Value
  ✅ expected_value.py → calculate_ev(), evaluate_entry()
         ↓
Decision (go/no-go)
  ✅ trader.py cycle loop → admission probes, gates, candidate lifecycle
         ↓
Sizing
  ✅ position_sizing.py → rank-aware size
  ✅ bankroll_tiers.py → tier + hysteresis
  ✅ risk_manager.py → Kelly, daily stop, exposure limits
         ↓
Risk Gate
  ✅ order_manager.py → RiskPlan
  ✅ order_intent.py → ENTRY/EXIT validation
         ↓
Execution
  ✅ PAPER: virtual_ptb.py → simulated fills, JSONL logged
  ⚠️ LIVE: client.py post_order() → code exists, NOT tested end-to-end
  ⚠️ LIVE: allowance approval missing (preflight fails)
         ↓
Position Reconciliation
  ✅ position_manager.py → state classification
  ✅ position_tracker.py → exposure tracking
  ⚠️ LIVE: live fill reconciliation not battle-tested
         ↓
Replay / Research
  ✅ JSONL event stream → full decision telemetry
  ✅ replay_analyzer.py → offline replay
  ✅ backtester_5m.py → candle backtest
         ↓
Dashboard
  ⚠️ Polling: reads static runtime/dashboard_state.json every 15s
  ⚠️ NOT live push — stale up to 15s
         ↓
Telegram
  ✅ startup, entry, exit, risk, critical, summary
  ❌ MISSING: execution confirmation (did order fill?)
  ❌ MISSING: live order status (pending/filled/cancelled)
         ↓
Research
  ✅ JSONL, offline tools, quant_event_logger
```

**KEY DISCONNECTS:**
1. **Live execution path** — `post_order` exists but allowance approval is unvalidated. The `verify` mode explicitly shows `VERIFY FAILED` on allowance check.
2. **Dashboard** — passive polling, no live WebSocket push from runtime.
3. **Telegram** — no order status notifications (fill confirmation, cancel ack).
4. **Fill reconciliation** — paper fills are simulated; live fills depend on CLOB event stream which has never run end-to-end.

---

## 3. HISTORICAL DATA INVENTORY

| File | Size | Events | Coverage |
|------|------|--------|---------|
| `runtime_events_2026-06-25_001.jsonl` | 8 MB | ~8,400 | 1 day |
| `runtime_events_2026-06-26_001.jsonl` | 135 MB | ~47,000 | 1 day (heavy session) |
| `runtime_events_2026-06-27_001.jsonl` | 99 MB | ~24,896 | 1 day (ongoing) |

**Total: 242 MB, ~80,000+ events across 3 days**

**Event type breakdown (2026-06-27):**
- `runtime_heartbeat_v1`: 10,440 — timing baseline
- `runtime_warning_v1`: 5,754 — skip/block reasons
- `analytics_loaded_v1`: 3,064 — regime state
- `risk_mode_changed_v1`: 2,460 — risk transitions
- `go_no_go_decision_v1`: 1,436 — ✅ full decision telemetry
- `candidate_rejected_v1`: 675 — skip analysis
- `orderbook_state_changed_v1`: 323 — orderbook events
- `market_snapshot_v1`: 323 — market state
- `paper_order_submitted_v1`: 192 — paper trades
- `position_closed_v1`: 44 — exits

**Decision payload includes:** EV, probability, bankroll tier, signal, regime, sizing, risk mode, candidate ID, trace IDs, timing fields, JSONL fields.

**Backtest sufficiency:**
- ✅ EV, probability, signal present in every decision
- ✅ Entry/exit prices present
- ✅ Candidate survival ms, order timing
- ⚠️ Only 3 days of data — insufficient for Sharpe/Kelly/drawdown analysis
- ❌ No live fills — only paper simulated fills
- ❌ Historical candle data for backtester requires separate download

---

## 4. DASHBOARD AUDIT

| Component | Status |
|-----------|--------|
| Overview page | ✅ Renders from dashboard_state.json |
| Market snapshot | ✅ Present |
| Decision log | ✅ Present |
| Risk state | ✅ Present |
| Bankroll tier | ✅ Present |
| Open positions | ✅ Present |
| Closed trades | ✅ Present |
| JSONL event counts | ✅ Present |
| Signal/regime detail | ⚠️ Partial — some fields missing |
| Live order status | ❌ NOT PRESENT |
| Fill confirmation | ❌ NOT PRESENT |
| WebSocket push | ❌ HTTP polling only (15s stale) |
| Research page | ✅ Present (read-only replay) |
| Alerts page | ⚠️ Partial |

**Priority additions:** Live order status pane, fill tracker, allowance/balance live display.

---

## 5. TELEGRAM AUDIT

| Notification | Status |
|-------------|--------|
| Startup | ✅ |
| Entry signal | ✅ |
| Exit signal | ✅ |
| Risk mode change | ✅ |
| Critical error | ✅ |
| Daily summary | ✅ |
| **Order placed (live)** | ❌ MISSING |
| **Order filled** | ❌ MISSING |
| **Order cancelled** | ❌ MISSING |
| **Allowance low** | ❌ MISSING |
| **Fill reconciliation mismatch** | ❌ MISSING |
| Bankroll tier change | ✅ Partial |
| Position P&L | ⚠️ Partial |

---

## 6. BANKROLL READINESS

| Component | Status |
|-----------|--------|
| Tier system (5 tiers) | ✅ IMPLEMENTED |
| Hysteresis + rank lock | ✅ IMPLEMENTED |
| Daily stop loss | ✅ IMPLEMENTED |
| Capital floor | ✅ IMPLEMENTED |
| Reserve | ✅ IMPLEMENTED (implicit in tier floors) |
| Growth mode | ✅ IMPLEMENTED (bankroll_growth_mode setting) |
| Kelly fraction | ✅ IMPLEMENTED (`kelly_for_binary()`) |
| Dynamic stop loss pct | ✅ IMPLEMENTED |
| Exposure limits | ✅ IMPLEMENTED (`max_exposure_pct`) |
| Recovery logic (MICRO_RECOVERY) | ✅ IMPLEMENTED |
| **Live balance read** | ⚠️ PARTIAL — reads work; not reliably updating during live trading |
| **Bankroll update on fill** | ❌ NOT TESTED (paper only) |

---

## 7. ADAPTIVE POSITION SIZING READINESS

| Component | Status |
|-----------|--------|
| Fixed sizing floor/cap | ✅ |
| Rank-aware sizing | ✅ |
| Confidence multiplier | ✅ |
| Bankroll tier multiplier | ✅ |
| Liquidity check (best_bid_size) | ✅ |
| Market quality (spread) | ✅ |
| Inventory awareness | ⚠️ Partial — exposure limit enforced, no per-market inventory cap |
| Sharpe-aware sizing | ❌ NOT IMPLEMENTED — no Sharpe computed at runtime |
| Volatility-adjusted sizing | ⚠️ Partial — regime affects multiplier indirectly |
| Kelly-based sizing | ✅ Available but not primary path |

**Remaining work:** Sharpe-aware multiplier (needs historical data → Phase 1), per-market inventory cap (needs bounded inventory engine → Phase 2).

---

## 8. BACKTEST READINESS

**What exists:**
- `polymarket/backtester_5m.py` — 5M candle signal replay (797 lines)
- `tools/replay_analyzer.py` — JSONL decision replay
- 3 days of rich JSONL event data (80K+ events)

**What's missing for serious backtesting:**
- ❌ Historical price data (candles) — requires download pipeline
- ❌ Historical Polymarket orderbook data — not available in JSONL
- ❌ Slippage model — paper execution assumes best bid fill
- ❌ Multi-day Sharpe computation — need 30+ days
- ❌ Kelly calibration — need win-rate from actual trades

**Effort estimate:** 2–3 weeks to build candle download pipeline + Sharpe/Kelly backtester.

---

## 9. LIVE TRADING READINESS CHECKLIST

| Item | Status | Blocker? |
|------|--------|---------|
| ✅ Paper mode separation | PASS | No |
| ✅ Order intent validation | PASS | No |
| ✅ Risk gates (all modes) | PASS | No |
| ✅ Order size limits | PASS | No |
| ✅ Daily stop loss | PASS | No |
| ✅ No-martingale enforcement | PASS | No |
| ✅ Exit signals | PASS | No |
| ✅ Cancel logic | PASS | No |
| ⚠️ Wallet balance read | PARTIAL | P0 |
| **❌ USDC allowance approval** | **MISSING** | **P0 HARD BLOCKER** |
| **❌ Live order fill confirmation** | **MISSING** | **P0 HARD BLOCKER** |
| **❌ Live fill→position reconciliation** | **MISSING** | **P0 HARD BLOCKER** |
| ❌ Order retry on failure | MISSING | P1 |
| ❌ Partial fill handling | MISSING | P1 |
| ❌ Kill switch (emergency stop) | PARTIAL (LOCKDOWN mode) | P1 |
| ❌ Telegram: live order notifications | MISSING | P1 |
| ❌ Live allowance top-up alert | MISSING | P1 |
| ❌ Duplicate order guard | PARTIAL | P2 |
| ❌ Nonce management (live signing) | NOT TESTED | P0 |
| ❌ Health monitor (disk/JSONL/session) | PARTIAL | P2 |

**HARD BLOCKERS TO LIVE TRADING (3):**
1. **USDC allowance approval** — `_preflight_balance_allowance` fails; CLOB requires approved allowance before any order
2. **Live fill confirmation** — no feedback loop from CLOB after `post_order`; position state not updated
3. **Live reconciliation** — position_tracker relies on paper-simulated fills; live fills are a different path

---

## 10. PRIORITIZED IMPLEMENTATION ROADMAP

### P0 — Critical Blockers (cannot trade live without these)

| # | Task | Effort |
|---|------|--------|
| P0.1 | **USDC Allowance approval** — implement `approve_allowance()` and `verify_allowance()` in client.py; add to live readiness preflight | 2 days |
| P0.2 | **Live order fill loop** — poll CLOB fill status after `post_order`; update position_tracker with actual fill price/size | 3 days |
| P0.3 | **Live fill → position reconciliation** — wire live fills into existing position_tracker; handle partial fills | 2 days |
| P0.4 | **Nonce/signing validation** — end-to-end live order signing test in paper-CLOB mode (testnet if available) | 2 days |

### P1 — Adaptive Quant Intelligence

| # | Task | Effort |
|---|------|--------|
| P1.1 | **Real win-rate tracking** — accumulate win/loss/EV from closed JSONL events; compute rolling Sharpe | 3 days |
| P1.2 | **Sharpe-aware position multiplier** — scale bet size down when Sharpe < threshold | 2 days |
| P1.3 | **Order retry + partial fill handler** — retry cancelled orders up to 2x; handle partial fills gracefully | 2 days |
| P1.4 | **Telegram live order notifications** — send on order placed, filled, cancelled, partially filled | 1 day |
| P1.5 | **Kill switch** — hard LOCKDOWN trigger from Telegram command or balance drop | 1 day |

### P2 — Bankroll

| # | Task | Effort |
|---|------|--------|
| P2.1 | **Live bankroll update** — update bankroll from actual USDC balance after each fill | 1 day |
| P2.2 | **Daily loss accounting** — compute actual daily P&L from live fills (not paper simulation) | 1 day |
| P2.3 | **Allowance top-up alert** — notify Telegram when USDC allowance < min_bet × 3 | 1 day |

### P3 — Adaptive Position Sizing

| # | Task | Effort |
|---|------|--------|
| P3.1 | **Per-market inventory cap** — limit exposure per market (e.g. max 30% of bankroll in one market) | 2 days |
| P3.2 | **Kelly calibration from history** — compute Kelly from rolling win-rate in JSONL | 2 days |
| P3.3 | **Volatility-adjusted size** — reduce size in high-volatility regimes | 1 day |

### P4 — Backtest

| # | Task | Effort |
|---|------|--------|
| P4.1 | **Candle data download pipeline** — 30+ days of BTC/ETH 5M candles from Binance | 2 days |
| P4.2 | **Multi-day Sharpe/drawdown backtester** — extend backtester_5m.py with Sharpe, max drawdown, Kelly | 3 days |
| P4.3 | **JSONL replay validation** — replay 3 days of JSONL decisions against actual market outcomes | 2 days |

### P5 — Paper Validation

| # | Task | Effort |
|---|------|--------|
| P5.1 | **Extended paper run** — 7-day paper run with full monitoring | Ongoing |
| P5.2 | **Dashboard live update** — replace 15s polling with SSE/WebSocket push | 2 days |
| P5.3 | **Win rate tracker page** — dashboard tab showing rolling win rate, Sharpe, EV distribution | 2 days |

### P6 — Small Live

| # | Task | Effort |
|---|------|--------|
| P6.1 | **Small live allocation** — $5–10 live after P0 complete, single market, daily cap $1 | When P0–P1 done |
| P6.2 | **Live reconciliation monitor** — compare live fills to expected fills; alert on mismatch | 2 days |

---

## SUMMARY: WHERE THE PROJECT STANDS

**The system is a production-grade paper trader with 90% of the live trading machinery implemented.**

The decision engine, signal pipeline, risk management, bankroll tiers, position sizing, and observability are all operational. The gap is narrow but critical: 3 hard blockers prevent live execution.

**What works today:**
- Full paper trading cycle with JSONL telemetry
- Adaptive risk (4 modes), bankroll tiers, Kelly sizing
- Decision + signal + EV pipeline fully connected
- Dashboard, Telegram, replay, backtest framework

**What blocks live trading:**
1. USDC allowance approval (P0.1) — 2 days
2. Live fill confirmation loop (P0.2) — 3 days
3. Live position reconciliation (P0.3) — 2 days

**Total to first live trade: ~10–14 days of focused implementation on P0–P1.**

**Recommendation: Freeze FLAOS/documentation work. All effort → P0 implementation.**
