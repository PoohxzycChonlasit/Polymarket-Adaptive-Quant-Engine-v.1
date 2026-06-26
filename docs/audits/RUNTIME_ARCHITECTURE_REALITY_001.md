# RUNTIME_ARCHITECTURE_REALITY_001

**Task:** FULL_PROJECT_REALITY_AUDIT_001  
**Mode:** DISCOVERY ONLY — no code changes  
**Date:** 2026-06-26  
**Evidence basis:** Source code only. All claims marked NOT VERIFIED RUNTIME where runtime execution was not observed.

---

## Audit Method

Evidence drawn exclusively from source code. Entry points traced by reading function signatures and call sites in `main.py` and `polymarket/trader.py`. No runtime execution observed — any claim about runtime behavior is inferred from source and marked accordingly.

---

## 1. Entry Points

### 1.1 Primary Entry Point

**File:** `main.py` (63,323 bytes)  
**Function:** `main()` — registered via `if __name__ == "__main__": sys.exit(main())`  
**CLI parsing:** `build_parser()` — argparse-based, returns `args`

### 1.2 Mode Dispatch Table (verified from source)

| args.mode | Handler function | Lazy import? |
|---|---|---|
| `polymarket` | `run_polymarket_mode()` | No |
| `paper`, `polymarket-paper`, `polymarket-realtime` | `run_polymarket_paper()` | No |
| `live` | `run_polymarket_live()` | No |
| `verify` | `run_verify_mode()` | No |
| `polymarket-backtest` | `run_polymarket_backtest()` | No |
| `polymarket-5m-dashboard` | `run_polymarket_5m_dashboard()` | No |
| `scalper` | `run_scalper_mode(args.scalper_mode)` | No — uses module-level `from crypto_scalper.live_runner import main as run_scalper` (line 17) |
| `dashboard` | `run_dashboard_mode()` | No |
| `realtime` | `run_realtime_mode(args.symbol)` | No |
| `hft` | calls `run_hft(bankroll, paper)` | YES — `from hft.main import run_hft` is inside the `if args.mode == "hft"` block (line 1410) |

### 1.3 Startup Sequence (all modes)

```
main()
  1. args = build_parser().parse_args()
  2. validation = validate_env(cli_mode=args.mode)  # utils/config_validator.py
  3. settings = get_settings()                        # config/settings.py (lru_cache)
  4. apply_validation_to_settings(settings, validation)
  5. setup_logger(settings.log_level, settings.log_dir)  # utils/logger.py
  6. → route to mode handler
```

---

## 2. Paper / Realtime Mode Trace (Primary Path)

### 2.1 `run_polymarket_paper()` → `run_polymarket_realtime()`

From source, `run_polymarket_paper()` calls `_call_with_optional_ui(run_polymarket_paper, ...)` from the dispatcher, suggesting the UI wrapper is the outer layer.

The paper mode function:
1. Calls `_acquire_paper_runtime_owner()` — writes a lock file to `runtime/` to prevent concurrent paper sessions
2. Instantiates `PolymarketTrader(settings=settings)` — `polymarket/trader.py:373`
3. Starts the trader's main loop (method name not confirmed from source read — NOT VERIFIED RUNTIME)
4. On shutdown: calls `_shutdown_realtime_resources(trader)` and `trader.close()`

### 2.2 `PolymarketTrader.__init__()` (verified from `trader.py:363-541`)

Initializes the following subsystems in order:

| Component | Class/Source |
|---|---|
| Settings | `get_settings()` → `config/settings.py` |
| CLOB client | `PolymarketClient()` → `polymarket/client.py` |
| Gamma fetcher | `GammaFetcher()` → `polymarket/gamma_fetcher.py` |
| Order manager | `PolymarketOrderManager(account_balance, max_risk_per_trade, stop_loss_pct, kelly_fraction_cap)` → `polymarket/order_manager.py` |
| Position tracker | `PositionTracker(settings)` → `utils/position_tracker.py` |
| Virtual PTB tracker | `VirtualPriceToBeatTracker()` → `polymarket/virtual_ptb.py` |
| Risk manager | `RiskManager(initial_balance)` → `utils/risk_manager.py` |
| Arbitrage scanner | `ArbitrageScanner(client, ...)` → `polymarket/arbitrage.py` |
| Arbitrage executor | `ArbitrageExecutor(client, settings, tracker)` → `polymarket/arbitrage_executor.py` |
| Paper stats | `PaperSessionStats()` — local dataclass |
| Risk mode state | `RiskModeState()` → `polymarket/risk_modes.py` |
| Bankroll state | `BankrollState(starting_bankroll, current_cash_balance)` — local dataclass |
| Bankroll rank lock | `BankrollRankLock(initial_tier, buffer_pct)` → `polymarket/bankroll_tiers.py` |
| Quant event logger | `self._init_quant_event_logger()` → `utils/quant_event_logger.py` |
| Telegram alerts | `self._init_telegram_alert_layer()` → `utils/telegram_alerts.py` |
| Market readiness metrics | Dict tracking 8 counters (empty_book_recovery, preload, etc.) |
| Path truth schedule | `(15, 30, 45, 60)` — seconds at which path-truth checkpoints are emitted per trade |

---

## 3. Per-Cycle Decision Pipeline (Inferred from Module Structure)

The following sequence is inferred from module imports, function signatures, and docstrings. Call ordering within `PolymarketTrader` methods is NOT VERIFIED RUNTIME without reading all ~13,000 lines of trader.py.

```
[CYCLE START]
  ┌─ Market Selection
  │   GammaFetcher.get_active_markets()  → polymarket/gamma_fetcher.py
  │   (WebSocket fallback to REST for orderbooks)
  │
  ├─ Per-Market Evaluation
  │   ┌─ Signal Computation
  │   │   compute_realtime_signal(asset, imbalance)  → polymarket/signal.py
  │   │   ├─ get_feed(asset)                         → polymarket/market_feed.py
  │   │   ├─ get_quant_feed(asset)                   → polymarket/quant_indicators.py
  │   │   ├─ classify_candle_regime(df)              → polymarket/regime_diagnostics.py
  │   │   └─ returns SignalResult (side, score, rsi, vol_ratio, ...)
  │   │
  │   ├─ Probability Model
  │   │   evaluate_probability_model(ProbabilityModelInput)  → polymarket/probability_model.py
  │   │   └─ returns ProbabilityModelResult (p_yes, p_no, confidence_score)
  │   │
  │   ├─ Expected Value
  │   │   evaluate_ev(ExpectedValueInput)            → polymarket/expected_value.py
  │   │   └─ returns ExpectedValueResult (approved, side, ev_yes, ev_no)
  │   │
  │   ├─ Risk Mode Check
  │   │   RiskModeState.update(consecutive_losses, drawdown_pct)  → polymarket/risk_modes.py
  │   │   └─ returns RiskModeDecision (mode, size_multiplier, allow_new_entries)
  │   │
  │   ├─ Bankroll Tier Update
  │   │   BankrollRankLock.update(balance)           → polymarket/bankroll_tiers.py
  │   │   └─ returns BankrollRankLockResult (active_tier, raw_tier, hysteresis_active)
  │   │
  │   ├─ Position Sizing
  │   │   calculate_position_size(PositionSizingInput)  → polymarket/position_sizing.py
  │   │   ├─ _build_multipliers(sizing_input, config)
  │   │   └─ returns PositionSizingResult (approved, final_size_usd, shares, tier, blocked_reasons)
  │   │
  │   ├─ Order Plan
  │   │   PolymarketOrderManager.build_order_plan(OrderRequest)  → polymarket/order_manager.py
  │   │   └─ returns RiskPlan (position_size, notional_size, kelly_fraction, ...)
  │   │
  │   ├─ Order Intent Validation
  │   │   validate_order_intent(OrderIntent)          → polymarket/order_intent.py
  │   │   └─ returns OrderIntentDecision (approved, reason)
  │   │
  │   ├─ Paper Execution (paper mode only — NOT VERIFIED RUNTIME)
  │   │   Virtual position recorded in PositionTracker
  │   │   No wallet/CLOB call made
  │   │
  │   └─ Event Logging
  │       QuantEventLogger.decision(...)              → utils/quant_event_logger.py
  │       QuantEventLogger.execution(...)
  │       QuantEventLogger.trade_open(...)
  │       RuntimeEventStream.emit(...)               → utils/runtime_event_stream.py
  │       RealtimeLogger.log_scan(ScanRecord)        → polymarket/realtime_logger.py
  │
  └─ UI Render
      display() or equivalent                        → utils/display.py
```

---

## 4. Live Mode Differences

`run_polymarket_live()` — all steps identical to paper mode EXCEPT:

1. Requires `settings.live_trading_enabled == "true"` (config gate)
2. Requires passing readiness preflight check (exact checks NOT VERIFIED RUNTIME)
3. At execution step: places real CLOB order via `PolymarketClient` instead of simulating
4. `OrderIntent.reconciliation_safe` must be True (reconciliation gate)
5. `order_intent.lockdown_active` must be False

**Live mode protection layers (verified from source):**
- `settings.live_trading_enabled` — config gate (default: `"false"`)
- `RiskModeState.current_mode != LOCKDOWN` — mode gate
- `validate_order_intent()` — structural validation
- `OrderIntent.risk_plan_present` and `OrderIntent.risk_approved` — risk plan gate
- `OrderIntent.reconciliation_safe` — reconciliation gate

---

## 5. Shutdown Sequence

`trader.close()` is called on all exit paths (verified from `trader.py:560`):
- Closes background writer threads (RuntimeEventStream)
- Flushes pending JSONL events
- Releases runtime ownership lock
- Emits final session health event

`_shutdown_realtime_resources(trader)` is called from `main.py` before close.

---

## 6. Secondary Mode Traces

### 6.1 `scalper` mode → `crypto_scalper/`

```
run_scalper_mode(scalper_mode) 
  → run_scalper(...)  # imported as: from crypto_scalper.live_runner import main as run_scalper
```
Import occurs at module level (main.py line 17). Runs an independent scalper engine.

### 6.2 `hft` mode → `hft/`

```
run_polymarket_mode() for args.mode == "hft":
  from hft.main import run_hft   # lazy import — line 1410
  asyncio.run(run_hft(bankroll=args.balance, paper=paper))
```
Import is lazy (inside the if-block). HFT engine runs its own async event loop.

### 6.3 `verify` mode → `run_verify_mode()`

Validates `.env` settings without starting any trading loop:
- Checks API keys, wallet address format
- Calls `_build_env_verification()` for structured output
- Does not instantiate `PolymarketTrader`

### 6.4 Dashboard modes

`polymarket-5m-dashboard` → `run_polymarket_5m_dashboard()` → imports and starts Streamlit dashboard  
`dashboard` → `run_dashboard_mode()` → starts Flask API or Streamlit offline dashboard

---

## 7. WebSocket Architecture (Verified from Settings + Module Presence)

`settings.polymarket_ws_url` = `"wss://ws-subscriptions-clob.polymarket.com/ws/"` (config/settings.py:120)

`polymarket/market_feed.py` — WebSocket market state cache (the primary market state source per architecture rules)
`polymarket/oracle_price_feed.py` — Binance price feed (also WebSocket or REST — NOT VERIFIED from module read)

**Architecture rule (from CLAUDE.md, verified as stated):** WebSocket cache is primary; REST is fallback only; never poll REST orderbooks every second.

**NOT VERIFIED RUNTIME:** Whether the WS connection is actually established per cycle, or whether REST fallback is triggered in current paper sessions.

---

## 8. Verified Facts Summary

| Fact | Source | Verified? |
|---|---|---|
| main.py is entry point | main.py:1 | YES |
| 10+ mode handlers | main.py dispatcher | YES |
| hft import is lazy | main.py:1410 | YES |
| crypto_scalper import is module-level | main.py:17 | YES |
| PolymarketTrader is central class | trader.py:363 | YES |
| 634KB trader.py | file size | YES |
| RiskModeState initialized in __init__ | trader.py:436 | YES |
| BankrollRankLock initialized in __init__ | trader.py:446 | YES |
| QuantEventLogger initialized in __init__ | trader.py:533 | YES |
| 4 risk modes: NORMAL/DEFENSIVE/MICRO_RECOVERY/LOCKDOWN | risk_modes.py:7 | YES |
| Size multipliers: 1.0 / 0.5 / 0.25 / 0.0 | risk_modes.py:135–142 | YES |
| Confidence floors: 0.54/0.65/0.75 | risk_modes.py:105,111; position_sizing.py:32 | YES |
| 13 bankroll tiers T0–T12 | bankroll_tiers.py:8 | YES |
| paper_trading default=True | settings.py:77 | YES |
| live_trading_enabled default="false" | settings.py:87 | YES |
| Per-cycle pipeline order | INFERRED from module structure | NOT VERIFIED RUNTIME |
| Exact trader run-loop method name | NOT read | NOT VERIFIED |
| WS connection lifecycle | NOT read | NOT VERIFIED |
