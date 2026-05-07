# PolyTrade Crypto Scalper — Claude Code Instructions

> Auto-loaded every session. Keep this file accurate and up-to-date.

---

## Project Identity

Algorithmic trading bot — Polymarket 5-min BTC/ETH binary prediction markets + crypto scalping.
**Validated strategy:** Counter-momentum mean reversion. 60d backtest ETH: +320%, Sharpe 0.54, Sortino 1.51, WR 54.3%, MaxDD 20.5%.
**Current status:** Backtest passed (ETH). Paper trade 48h required → then get MATIC → then live.

Full context: `CURRENT_PROJECT_STATUS.md` | Strategy deep-dive: `research/OVERVIEW.md`

---

## Session Startup Checklist

When starting a new session, always do this first (in parallel):
1. Read `CURRENT_PROJECT_STATUS.md` — know where we left off
2. Read latest `research/daily/YYYY-MM-DD.md` — yesterday's notes
3. Run smoke test if strategy code was changed: `python main.py --mode polymarket-backtest --days 3`

---

## Key Commands

```bash
# Daily operations
python main.py --mode polymarket-realtime --interval 60   # Live/paper trading loop
python daily_report.py                                     # Today's P&L from scan logs
python polymarket/five_min_monitor.py --interval 30       # Live market monitor

# Backtesting
python main.py --mode polymarket-backtest --days 60        # Full 60-day backtest
python main.py --mode polymarket-backtest --days 3         # Quick smoke test (fast)

# Dashboard
python main.py --mode polymarket-5m-dashboard             # Streamlit backtest dashboard

# Tests
pytest tests/ -v                                           # Full test suite
python -c "from polymarket.backtester_5m import PolymarketBacktester5m; print('OK')"
```

---

## Critical Files

| File | Purpose |
|------|---------|
| `polymarket/backtester_5m.py` | Core strategy — `_compute_signal()` is the source of truth |
| `utils/risk_manager.py` | Kelly sizing + FLOOR_BALANCE=$5 hard stop |
| `polymarket/trader.py` | Live trading loop |
| `polymarket/client.py` | Wallet auth + balance fetch |
| `config/settings.py` | All env vars (pydantic v2) |
| `.env` | Private keys — NEVER commit |

---

## Strategy Rules (DO NOT CHANGE without backtest)

```
momentum_pct = (candle_open - close_3_candles_ago) / close_3_candles_ago * 100

if momentum_pct > +0.40%  → bet NO   (mean reversion down)
if momentum_pct < -0.40%  → bet YES  (mean reversion up)
if |momentum_pct| < 0.40% → SKIP

Threshold 0.40% is optimal (tested: 0.30%→Sharpe 0.77, 0.40%→Sharpe 1.18)
```

Any signal change → must run `--days 60 --asset ETH` backtest → must pass: Sortino>1.0, Sharpe>0.4, WinRate>51%, MaxDD<25%
(Binary markets have high variance → use Sortino not Sharpe as primary metric)

---

## Hard Limits (Never Override in Code)

- `FLOOR_BALANCE = $5.00` — stop all trading if balance drops below
- `HARD_CAP_SINGLE_TRADE = 3%` of bankroll per trade
- `HARD_DAILY_DRAWDOWN = 10%` — stop for the day if hit
- `PAPER_TRADING=true` in .env by default — must explicitly set false for live

---

## Wallet Info

- **Wallet:** `0x645a661bcf56c28297538848b6c519e378e833e2`
- **Balance:** ~$8.82 USDC (native, Polygon)
- **Gas:** MATIC needed before live trading (currently 0)
- **Tier:** micro ($0–$10), max risk 0.5%/trade, min bet $0.05

---

## Known Issues (Do Not Forget)

| Issue | File | Priority |
|-------|------|---------|
| MATIC = 0 — can't place orders | wallet | HIGH — add ~0.5 MATIC |
| Paper trading not run yet | — | HIGH — run 48h before live |
| WebSocket listener incomplete | `polymarket/websocket_listener.py` | MEDIUM |
| Crypto scalper never backtested | `crypto_scalper/` | MEDIUM |
| Sortino overflow in 30d backtest | `backtester_5m.py` display | LOW |

---

## Coding Rules

- No comments unless the WHY is non-obvious
- No extra abstractions beyond what the task needs
- Any change to signal logic → update BOTH `backtester_5m.py` AND `polymarket/signal.py`
- After any file deletion → update `CURRENT_PROJECT_STATUS.md` file structure section
- Daily work log → `research/daily/YYYY-MM-DD.md`

---

## Bankroll Tiers

| Tier | Balance | Max Risk/Trade | Min Bet |
|------|---------|---------------|---------|
| micro | $0–$10 | 0.5% | $0.05 |
| small | $10–$100 | 0.75% | $0.10 |
| conservative | $100–$1K | 1.0% | $0.50 |
| balanced | $1K–$10K | 1.25% | $2.00 |
| growth | $10K+ | 1.5% | $5.00 |
