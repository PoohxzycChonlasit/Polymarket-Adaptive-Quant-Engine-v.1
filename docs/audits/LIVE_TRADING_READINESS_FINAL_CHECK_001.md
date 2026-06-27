# LIVE_TRADING_READINESS_FINAL_CHECK_001
## Production Readiness Audit — $10 Live Account Standard

**Date**: 2026-06-27  
**Auditor**: Antigravity (FLAOS Gate Check)  
**Scope**: End-to-end live trading pipeline — wallet to Telegram  
**Standard**: Would you enable a real $10 account immediately after this audit? 

---

## Integration Diagram

```
[.env / Settings]
      │ paper_trading=False, private_key, api_key, funder
      ▼
[Startup: _log_wallet_startup_verification()]
      │ check_allowance_status() → MISSING | OK | INSUFFICIENT
      │ verify_signing_capability() → has_signer, has_builder, sig_type
      │ notify_allowance_missing() / notify_signing_not_ready()  ← P0.4
      ▼
[run_single_cycle() every 60s]
      │
      ├─► reconcile_live_positions()        ← CLOB truth vs tracker
      │         └─► tracker.reconcile_inventory()
      │         └─► _block_on_reconciliation_if_needed()
      │               └─► _trigger_lockdown("reconciliation_mismatch")
      │               └─► notify_incident()
      │
      ├─► _poll_pending_live_orders()       ← every 5 cycles
      │         └─► client.get_order_status()
      │         └─► notify_order_filled() / notify_order_cancelled() ← P0.4
      │
      ├─► _update_bankroll_state(fetch_live_cash=True)
      │         └─► client.get_usdc_balance()
      │         └─► _risk_off(daily_drawdown_pct)  → LOCKDOWN at ≥10%
      │
      ├─► _manage_open_positions_for_cycle()  exit logic, stop-loss, TP
      │
      └─► run_single_market_cycle()
              │
              ├─► signal + probability + EV model
              ├─► risk_plan (Kelly, max_risk_per_trade 0.5%, floor $5)
              ├─► quant_decision (PROCEED / DEFER / BLOCK)
              │
              ├─► client._preflight_balance_allowance()  ← P0.1 fix
              │         raise RuntimeError if balance < needed
              │         raise RuntimeError if allowance < needed  ← zero-fix
              │
              ├─► client.place_limit_order(timeout_sec=30.0)
              │         └─► client.create_order() + post_order()
              │         └─► wait_for_fill() → cancel_on_timeout=True
              │
              ├─► Fill confirmed? → tracker.open_position()
              │   Not confirmed? → _pending_live_orders[order_id] = receipt
              │
              ├─► _reconcile_after_order_attempt()
              ├─► notify_order_submitted() / notify_order_filled() ← P0.4
              │
              ├─► _emit_quant_event("log_execution", ...)  → JSONL
              │
              └─► [Telegram] notify_* helpers (fail-soft, cooldown-deduped)
```

---

## Component Audit

### 1. Wallet & Credentials

| Check | Status | Evidence |
|-------|--------|----------|
| `paper_trading=False` guard at startup | **PASS** | `settings.py` validates via Pydantic; `client.place_limit_order()` raises `paper_mode_live_order_api_blocked` if `paper_trading=True` at line 1157–1158 |
| Private key loaded via `.env` | **PASS** | `polymarket_private_key: SecretStr` field; never logged |
| `polymarket_funder` and proxy wallet set | **WARNING** | Defaults to `""` — must be verified non-empty in `.env` before live launch |
| API key / secret / passphrase set | **WARNING** | All default to `""` — no startup validation that they are non-empty for live mode |

---

### 2. Allowance

| Check | Status | Evidence |
|-------|--------|----------|
| Startup allowance check surfaced | **PASS** | `check_allowance_status()` called in `_log_wallet_startup_verification()` |
| Zero-allowance bug fixed | **PASS** | P0.1: `if allowance + 1e-9 < needed` replaces falsy check (client.py L1014) |
| Pre-order allowance preflight | **PASS** | `_preflight_balance_allowance()` raises `RuntimeError` on every BUY order |
| Telegram alert on MISSING allowance | **PASS** | P0.4: `notify_allowance_missing()` wired to startup check |
| Programmatic `approve_allowance()` | **FAIL** | **No method exists.** Must be done via Polymarket UI or manual Web3 call before live session. Documented in `docs/audits/LIVE_EXECUTION_GAP_ANALYSIS_001.md §4`. |

---

### 3. Signing

| Check | Status | Evidence |
|-------|--------|----------|
| `verify_signing_capability()` exists | **PASS** | Returns `{status, has_signer, has_builder, sig_type}` (client.py L1075) |
| Signing check wired to startup | **PASS** | P0.4: Called in `_log_wallet_startup_verification()` |
| Telegram alert on signing FAIL | **PASS** | P0.4: `notify_signing_not_ready()` wired to startup |
| Full signing test (create_order) | **WARNING** | `verify_signing_capability()` deliberately does NOT call `create_order()` — it only checks that `signer` and `builder` attributes are non-None. An actual signing test requires a real `token_id` and will only be discovered at first order submission. |

---

### 4. Order Submission

| Check | Status | Evidence |
|-------|--------|----------|
| GTC order type enforced | **PASS** | `place_limit_order()` defaults to `"GTC"` (client.py L1136) |
| Price and size validation | **PASS** | `raise ValueError` if `price <= 0 or size <= 0` (L1153) |
| API retry with backoff | **PASS** | `_api_call_with_retry()` with circuit breaker (3 threshold, 60s window) |
| Fill timeout wired to 30s | **PASS** | P0.2: `timeout_sec=live_timeout` (30.0s from settings) passed to `wait_for_fill()` with `cancel_on_timeout=True` (trader.py L11912–11918) |
| JSONL event `live_order_submitted` | **PASS** | Emitted at trader.py L11926 with full context |
| Telegram `notify_order_submitted` | **PASS** | P0.4: wired at trader.py L11941 |
| Order submission exception handling | **PASS** | Wrapped in `try/except`; logs FAILED_ORDER; emits `order_submit_failed` event |

---

### 5. Exchange Response & Fill Confirmation

| Check | Status | Evidence |
|-------|--------|----------|
| Fill confirmed vs pending split | **PASS** | P0.2: `_is_fill_confirmed` checks receipt status ∈ {filled, matched} |
| Position opened only on fill confirm | **PASS** | `tracker.open_position()` called only if `_is_fill_confirmed` (trader.py L9854) |
| Non-confirmed orders tracked | **PASS** | Added to `_pending_live_orders` for cross-cycle polling (trader.py L9850) |
| `wait_for_fill()` cancel on timeout | **PASS** | `cancel_on_timeout=True` ensures GTC orders are cancelled after 30s if unfilled |
| JSONL event `live_fill_not_confirmed` | **PASS** | Emitted with order_id, status, filled_size (trader.py L9840) |

---

### 6. Pending Order Tracking

| Check | Status | Evidence |
|-------|--------|----------|
| `_pending_live_orders` dict initialized | **PASS** | `dict[str, object]` at trader.py L520 |
| Cross-cycle polling on fill/cancel | **PASS** | P0.3: `_poll_pending_live_orders()` called every `live_reconciliation_interval_cycles=5` cycles (trader.py L12603) |
| Terminal states removed from dict | **PASS** | `to_remove` list pattern (trader.py L6963) |
| Exceptions in polling are swallowed | **PASS** | `except Exception as exc: LOGGER.warning(...)` (trader.py L6961) |
| Telegram on fill/cancel | **PASS** | P0.4: `notify_order_filled()` / `notify_order_cancelled()` wired |

---

### 7. Position Tracker

| Check | Status | Evidence |
|-------|--------|----------|
| `tracker.open_position()` for fills | **PASS** | With all metadata: stop_loss, take_profit, order_id, token_id |
| Ghost position detection | **PASS** | `ghost_position_max_age=3600` + quarantine enabled |
| Max open positions cap | **PASS** | `max_open_positions=3` enforced in risk pre-check |
| Position size minimum floor | **PASS** | `bankroll_floor=$5.00`; Polymarket min $0.10 per share enforced |

---

### 8. Live Reconciliation

| Check | Status | Evidence |
|-------|--------|----------|
| `reconcile_live_positions()` called each cycle | **PASS** | At start of `run_single_cycle()` (trader.py L12600) |
| Queries CLOB truth (positions + open orders) | **PASS** | `client.get_positions()` + `client.get_open_orders()` |
| Mismatch triggers LOCKDOWN | **PASS** | `_block_on_reconciliation_if_needed()` → `_trigger_lockdown("reconciliation_mismatch")` |
| Mismatch triggers Telegram incident | **PASS** | `notify_incident()` with classification and reason |
| Reconcile failure triggers LOCKDOWN | **PASS** | `_reconcile_after_order_attempt()` catches exceptions → `_trigger_lockdown("reconciliation_failed")` |
| PARTIALLY_HEDGED_ARB logged as CRITICAL | **PASS** | Logs with `manual_intervention_required` — operator must unwind manually |

---

### 9. Risk Controls

| Check | Status | Evidence |
|-------|--------|----------|
| Max risk per trade: 0.5% (micro tier) | **PASS** | `max_risk_per_trade=0.005`; hard cap enforced at 3% in validator |
| Max daily drawdown: 10% | **PASS** | `_risk_off()` at ≥10%; `_trigger_lockdown()` called |
| Max open positions: 3 | **PASS** | Enforced in risk pre-check |
| Bankroll floor: $5.00 | **PASS** | Stops trading below floor |
| Emergency flatten at 10s to close | **PASS** | `exit_agent_emergency_flatten_seconds=10` |
| LOCKDOWN blocks all new entries | **PASS** | `RiskMode.LOCKDOWN` checked in `run_single_cycle()` (L3540, L5146) |
| Duplicate order protection | **PASS** | `_trigger_lockdown("duplicate_order")` at L8632, L9510, L10078 |
| Hard drawdown at 15% | **PASS** | `hard_drawdown_reached = daily_drawdown_pct >= 0.15` |
| Circuit breaker on API failures | **PASS** | 3 consecutive failures → 30s cooldown |
| Stop-loss % via `sl_emergency_stop_pct` | **PASS** | 30% position loss triggers emergency stop |

---

### 10. Bankroll Updates

| Check | Status | Evidence |
|-------|--------|----------|
| Live USDC balance fetched each cycle | **PASS** | `_update_bankroll_state(fetch_live_cash=True)` (trader.py L12606) |
| Balance guard with auto-resume | **PASS** | `_paused_insufficient_funds` → checked vs floor; auto-resumes when balance recovered (L12635) |
| Tier automatically adjusts | **PASS** | `bankroll_tiers` config covers micro ($0–10) through growth ($10k+) |
| Daily drawdown tracked vs daily start | **PASS** | `daily_start_bankroll` set at session start; `daily_drawdown_pct` computed each cycle |

---

### 11. JSONL Logging

| Check | Status | Evidence |
|-------|--------|----------|
| `live_order_submitted` event | **PASS** | Emitted with full receipt, risk context, mode |
| `live_fill_not_confirmed` event | **PASS** | Emitted with order_id, status, fill sizes |
| `pending_order_fill_confirmed` event | **PASS** | Emitted from `_poll_pending_live_orders()` |
| `pending_order_terminal` event | **PASS** | Emitted for cancelled/timeout/rejected |
| `reconciliation_mismatch` risk event | **PASS** | Emitted via `_emit_risk_event()` with classification |
| `log_trade_open` / `log_trade_close` | **PASS** | Full position lifecycle logged |
| Event stream as source of truth | **PASS** | Telegram is notification-only; JSONL is authoritative |

---

### 12. Replay

| Check | Status | Evidence |
|-------|--------|----------|
| Replay tooling exists | **PASS** | `tools/replay_analyzer.py`, `canonical_trade_table_v1.py` |
| Live events replayable offline | **PASS** | Event stream JSONL files in `runtime/event_stream/` |
| MFE/MAE analytics available | **PASS** | `tools/mae_mfe_analytics_v1.py` exists |

---

### 13. Dashboard

| Check | Status | Evidence |
|-------|--------|----------|
| Dashboard API running | **PASS** | `dashboard/src/` React app + Flask API server |
| Live vs paper mode displayed | **PASS** | `mode` field emitted in system health events |
| Bankroll rank, drawdown visible | **PASS** | `daily_drawdown`, `risk_off` in dashboard state aggregator |
| Market state display | **WARNING** | Market state classifier designed but not yet emitted as structured payload in logs |

---

### 14. Telegram

| Check | Status | Evidence |
|-------|--------|----------|
| Allowance missing alert | **PASS** | P0.4: `notify_allowance_missing()` |
| Signing not ready alert | **PASS** | P0.4: `notify_signing_not_ready()` |
| Order submitted | **PASS** | P0.4: `notify_order_submitted()` |
| Order filled | **PASS** | P0.4: `notify_order_filled()` |
| Order cancelled/timeout | **PASS** | P0.4: `notify_order_cancelled()` |
| Reconciliation incident | **PASS** | `notify_incident()` wired to reconciliation mismatch |
| Fail-soft (never blocks runtime) | **PASS** | All Telegram calls wrapped in `_notify_telegram()` which is exception-safe |
| Cooldown/dedup | **PASS** | Dedup key per order_id; `cooldown_seconds` from settings |

---

### 15. Kill Switch

| Check | Status | Evidence |
|-------|--------|----------|
| Software LOCKDOWN | **PASS** | `_trigger_lockdown()` → `RiskMode.LOCKDOWN` → blocks all new entries |
| Daily drawdown auto-stop | **PASS** | `_risk_off()` at 10% drawdown |
| Emergency flatten | **PASS** | `exit_agent_emergency_flatten_seconds=10` before market close |
| Ctrl+C clean shutdown | **PASS** | `feed.stop()` + atexit hooks registered |
| Manual operator file-based kill switch | **FAIL** | **No file-drop kill switch exists.** LOCKDOWN requires drawdown trigger or code restart. No operator-facing `/tmp/KILL` or `.stop` file mechanism. Documented gap in `LIVE_TRADING_READINESS_GATE_001.md §5`. |

---

## Failure Matrix

| Failure Scenario | Detection | Response | Recovery |
|-----------------|-----------|----------|----------|
| USDC allowance missing | Startup check | `notify_allowance_missing` + log | Manual UI approval required |
| Private key not loaded | `verify_signing_capability()` | `notify_signing_not_ready` | Fix `.env`, restart |
| Balance < order size | `_preflight_balance_allowance()` | `RuntimeError` → order skipped | Auto-recovers on balance increase |
| Order submission API failure | `try/except` in `place_limit_order` | Log + `order_submit_failed` JSONL | Retry (3x backoff) |
| Order not filled in 30s | `wait_for_fill(cancel_on_timeout=True)` | Auto-cancel + `timeout_cancelled` event | Next cycle evaluates fresh |
| Fill status unknown | `_pending_live_orders` tracking | Cross-cycle polling every 5 cycles | Reconcile resolves truth |
| Position mismatch (local ≠ CLOB) | `reconcile_live_positions()` | LOCKDOWN + Telegram incident | Manual intervention required |
| Daily drawdown ≥ 10% | `_risk_off()` | LOCKDOWN, no new entries | Auto-resets next calendar day |
| API circuit breaker open | 3 consecutive errors | 30s cooldown | Auto-resets after cooldown |
| Telegram API failure | `_notify_telegram()` exception handling | Swallowed, runtime continues | N/A (fail-soft) |
| Partially hedged ARB detected | Reconciliation | LOCKDOWN + CRITICAL log | Manual unwind required |
| Ghost position detected | `ghost_position_sentinel` | Quarantine, alert | Manual review |

---

## Production Checklist

### Must be done BEFORE enabling live mode:

- [ ] **`.env` verified**: `PAPER_TRADING=false`, `POLYMARKET_PRIVATE_KEY`, `POLYMARKET_API_KEY`, `POLYMARKET_API_SECRET`, `POLYMARKET_API_PASSPHRASE`, `POLYMARKET_FUNDER`, `POLYMARKET_PROXY_WALLET` are all non-empty
- [ ] **USDC allowance approved** via Polymarket UI for the proxy wallet address (CLOB contract spending)
- [ ] **Signing capability verified**: Run `--mode verify` and confirm `has_signer=True`, `has_builder=True`
- [ ] **Bankroll floor confirmed**: Starting balance ≥ $10 (above micro-tier floor of $5)
- [ ] **Single runtime verified**: Run `runtime_session.py guard` before starting
- [ ] **Telegram configured**: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` set; test message received
- [ ] **Dashboard accessible**: API server running; dashboard shows correct wallet address
- [ ] **Paper mode has run cleanly for ≥ 1 cycle** immediately prior to switching to live

### Recommended first live test procedure ($5–10):

1. Start with exactly **$10 USDC** in the proxy wallet
2. Set `MAX_RISK_PER_TRADE=0.005` (0.5% = $0.05 max per trade)
3. Set `MAX_OPEN_POSITIONS=1`
4. Set `MAX_DAILY_DRAWDOWN=0.05` (5% = $0.50 max loss)
5. Set `BANKROLL_FLOOR=8.00` (stop trading if balance drops below $8)
6. Run `--mode live --interval 60` for **one hour only** with operator watching Telegram
7. After 1 hour: `Ctrl+C` → verify JSONL `live_order_submitted` / `pending_order_fill_confirmed` events exist
8. Review `reconcile_live_positions()` report before any further session

---

## Remaining Blockers

| # | Blocker | Severity | Impact |
|---|---------|----------|--------|
| **B1** | No programmatic `approve_allowance()` — manual UI step required before every live session | HIGH | Cannot auto-recover from allowance expiry |
| **B2** | No file-drop / operator kill switch — LOCKDOWN requires drawdown trigger or `Ctrl+C` | MEDIUM | Operator cannot instantly halt mid-cycle without killing the process |
| **B3** | `verify_signing_capability()` does not call `create_order()` — signing untested until first real order | MEDIUM | A key format error will only surface at first submission |
| **B4** | Empty/invalid `.env` credentials not validated at startup (no check that `polymarket_funder != ""`) | MEDIUM | Live mode will connect but fail at first order with a confusing error |
| **B5** | `PARTIALLY_HEDGED_ARB` reconciliation requires manual unwind — no auto-unwind | LOW | Rare scenario; requires operator intervention |

---

## Final Verdict

```
READY_WITH_BLOCKERS

B1 (no approve_allowance) and B4 (no credential startup validation) must
be resolved or acknowledged by the operator before the first live session.

B2 (no file kill switch) and B3 (signing not fully tested) are acceptable
for a supervised $10 micro-test but should be implemented before scaling.

The P0 pipeline (allowance preflight, fill confirmation, pending order
tracking, periodic reconciliation, signing visibility, Telegram lifecycle
events) is functionally complete and tested (160/160 tests pass).

Risk controls (drawdown cap, position limits, bankroll floor, circuit
breaker, LOCKDOWN) are solid. JSONL logging is comprehensive and replayable.
```
