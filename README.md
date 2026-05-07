# PolyTrade Crypto Scalper

> **v4.0 — HFT Tiered Signal System**  
> Algorithmic trading bot for **Polymarket 5-minute BTC binary prediction markets** on Polygon L2.  
> Designed for high-frequency micro-grinding with Window-Delta primary signal + Counter-momentum entry timing.

---

## Current Operating Docs

Use these files as the current map before changing or running the bot:

- `AGENTS.md` - safety rules and active files for AI agents.
- `docs/quant_agent_setup_md/` - quant-agent operating system.
- `docs/PROJECT_STRUCTURE.md` - current data flow, risk flow, execution flow, and logging flow.
- `docs/PROJECT_CLEANUP_REPORT.md` - cleanup findings, archived files, and manual review items.
- `CURRENT_PROJECT_STATUS.md` - latest project status.

Canonical Polymarket runtime path:

```bash
python main.py --mode polymarket-realtime --interval 60
```

Verify `.env` before running this command. The command can become live-risk if `PAPER_TRADING=false` or `DRY_RUN=false`.

---

## How It Works

Polymarket sells binary contracts: **YES** ($1 if BTC closes above a price target) and **NO** ($1 if below).  
Each contract expires every **5 minutes**. The bot predicts which side wins using live Binance data.

```
BTC spot > PTB (Price To Beat) → YES wins → YES holders get $1/share
BTC spot ≤ PTB               → NO wins  → NO holders get $1/share
```

The edge comes from detecting when market prices (YES/NO) are mispriced relative to our probability model.

---

## Signal Pipeline

```
Binance WebSocket         Gamma API
(BTC spot + 1m/5m candles)   (YES/NO price)
        │                       │
        └──────────┬────────────┘
                   ▼
         compute_tiered_signal()
              │
              ├── window_delta = (spot - PTB) / PTB × 100   ← primary driver
              ├── 3-candle momentum (1m bars)                ← entry timing
              ├── RSI-14                                     ← overbought/oversold filter
              └── p_model → EV → Edge
                   │
                   ▼
         ┌─────────────────┐
         │  Tier Selection │
         │  STRONG / MEDIUM / WEAK
         └────────┬────────┘
                  │
         Dominant-side lock
         (one direction per window)
                  │
                  ▼
         Binary Settlement
         (spot vs PTB at window close)
```

---

## Tiered Signal System

The bot finds **3 levels of edge** per cycle — more opportunities without more risk:

| Tier | Min EV | Min Edge | Bet Size | Max/Window |
|------|--------|----------|----------|-----------|
| **STRONG** | 2.5% | 4.0% | $1.50 | 3 positions |
| **MEDIUM** | 0.8% | 1.5% | $0.75 | 2 positions |
| **WEAK** | 0.2% | 0.5% | $0.30 | 2 positions |

**Max window exposure:** `3×$1.50 + 2×$0.75 + 2×$0.30 = $6.60 = 6.6%` (hard cap 10%)

**Dominant-side lock:** Once the first position is entered in a window (e.g. YES), all subsequent entries in that window must also be YES — preventing self-hedging.

---

## Risk Management

| Rule | Value |
|------|-------|
| Floor balance (hard stop) | $5.00 |
| Max window exposure | 10% of bankroll |
| Daily drawdown limit | 8% |
| Circuit breaker | 5-min pause if near floor |

**4-Tier Bankroll (hft/risk_manager.py):**

| Tier | Balance | Kelly Fraction | Max Bet |
|------|---------|---------------|---------|
| micro | < $100 | 25% | $2 |
| small | $100–$999 | 20% | $5 |
| growth | $1K–$10K | 15% | $15 |
| institutional | $10K+ | 10% | $50 |

---

## Project Structure

```
polytrade-crypto-scalper/
│
├── hft_paper_run.py              ★ Main HFT paper trade loop
│
├── hft/                          HFT engine modules
│   ├── risk_manager.py           4-tier Kelly bankroll + circuit breaker
│   ├── strategy_engine.py        Strategy A (Deep Value) / B (MTF Momentum) / C (Hold)
│   ├── execution_router.py       Limit → FOK smart routing (maker-first for Tier 3/4)
│   ├── signal_engine.py          Signal computation
│   ├── config.py                 HFT constants
│   └── utils.py                  sigmoid, Kelly, EV helpers
│
├── polymarket/
│   ├── market_feed.py            Binance WebSocket feed (BTC spot + 1m/5m candles)
│   ├── gamma_fetcher.py          Gamma API wrapper (YES/NO prices)
│   ├── signal.py                 Quant signal (main bot)
│   ├── trader.py                 Live/paper trading loop
│   ├── client.py                 py-clob-client wrapper (L2 auth + orders)
│   └── backtester_5m.py          5-minute backtest engine
│
├── config/
│   └── settings.py               pydantic v2 settings (all env vars)
│
├── utils/
│   ├── risk_manager.py           Kelly + tiered sizing + $5 floor
│   └── telegram_reporter.py      Trade, settlement & daily alerts
│
├── web-dashboard/                Next.js dashboard (Port 3000)
│
├── runtime/
│   ├── hft_trades.csv            Trade log — every closed position
│   └── bot_status.json           Current bot state
│
└── research/
    └── daily/YYYY-MM-DD.md       Daily work logs
```

---

## Quick Start

**Requirements:** Python 3.11+

```bash
# 1. Clone and create virtual environment
git clone <repo>
cd polytrade-crypto-scalper-main
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
copy .env.example .env       # Windows
# cp .env.example .env       # Mac/Linux
# Edit .env and fill in your keys
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PAPER_TRADING` | Simulate orders — never touch real money | `true` |
| `POLYMARKET_PRIVATE_KEY` | Polygon wallet private key | required |
| `POLYMARKET_FUNDER` | Funding wallet address | required |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` | `INFO` |

> **Safety:** `PAPER_TRADING=true` by default. You must explicitly set `false` to trade real money.

---

## Running the Bot

### Paper Trade (HFT — recommended first)

```bash
python hft_paper_run.py
```

Runs a live paper trade loop against real Polymarket + Binance data.  
Logs every closed trade to `runtime/hft_trades.csv`.

### Main Bot Loop

```bash
python main.py --mode polymarket-realtime --interval 60
```

### Backtesting

```bash
# 60-day backtest
python main.py --mode polymarket-backtest --days 60 --asset BTC

# Quick 3-day smoke test
python main.py --mode polymarket-backtest --days 3
```

### Market Monitor

```bash
python polymarket/five_min_monitor.py --interval 30
```

---

## Strategy Details

### Primary Signal — Window Delta

```
window_delta = (BTC_spot - PTB) / PTB × 100

sigma = 2.0 + 3.0 × window_progress    # steeper near window end
p_yes = sigmoid(window_delta × sigma)   # P(BTC ends above PTB)
```

### Adjustments

| Adjustment | Condition | Effect |
|-----------|-----------|--------|
| Counter-momentum | momentum same direction as delta | −0.02 (fade the crowd) |
| Counter-momentum | momentum opposite to delta | +0.015 (bounce expected) |
| RSI overbought | RSI > 72 | −0.04 |
| RSI oversold | RSI < 28 | +0.04 |
| Late window boost | < 60s left + clear delta | ±0.03 |

### Advanced Strategies (hft/ modules)

| Strategy | Condition | Action |
|----------|-----------|--------|
| **A — Deep Value** | ask < $0.32 AND EV > 12% | Maker limit order |
| **B — MTF Momentum** | 5m HTF bias + 1m spike detected | Counter-trend entry |
| **C — Hold Decision** | p_win > 92% | Hold to window end |
| **C — Emergency Exit** | p_win drops from ≥ 92% to < 80% | Exit immediately |

---

## Live Trading Checklist

Do not go live until all items are confirmed:

- [ ] Run paper trade for **48+ hours** — check `runtime/hft_trades.csv`
- [ ] Win Rate > 51% and Max Drawdown < 20%
- [ ] Add **MATIC ≥ 0.5** to wallet for gas fees
- [ ] Set `PAPER_TRADING=false` in `.env`
- [ ] Wallet: `0x645a661bcf56c28297538848b6c519e378e833e2`

---

## Current Status (as of 2026-04-27)

| Item | Status |
|------|--------|
| Binance WebSocket feed | ✅ Live |
| Polymarket market data | ✅ Live (Gamma API) |
| Paper trading | ✅ Ready to run |
| Telegram alerts | ✅ Active |
| Web dashboard | ✅ Port 3000 |
| Live trading | ❌ Blocked — MATIC = 0 |

---

## Tech Stack

| Component | Library |
|-----------|---------|
| Prediction Markets | `py-clob-client` |
| HTTP | `httpx` + `tenacity` |
| Data | `pandas`, `numpy` |
| Settings | `pydantic-settings` v2 |
| Dashboard | `Next.js` (web-dashboard/) |
| Alerts | Telegram Bot API |

---

## Important Notes

- **PTB proxy:** Gamma API does not return the true Coinbase oracle PTB. The bot uses BTC spot at window open as a proxy — slightly less accurate but functional.
- **Intra-window TP/SL:** Polymarket prices don't move within a window, so Take-Profit and Stop-Loss only trigger at binary settlement (window end).
- **Liquidity:** BTC/ETH markets on Polymarket have wide spreads (0.01 bid / 0.99 ask). The `execution_router` handles this with Limit → FOK fallback logic.

---

*Last updated: 2026-04-27 | Version: v4.0*
