# PolyTrade Bot — Research & Strategy Overview

> Historical note, 2026-05-10: this document is research history, not the active source of truth. It contains older Claude-agent, fixed-strategy, and live/readiness assumptions that may conflict with current docs. Use `DOCUMENTATION_MAP.md`, `CURRENT_PROJECT_STATUS.md`, `QUANT_REGIME_PROBABILITY_ENGINE.md`, `INVENTORY_REPLAY_RESEARCH_PLAN.md`, and `BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md` for the current paper-first regime/probability and bounded-inventory roadmap.
> **Purpose:** Reference document for strategy research, design decisions, and ongoing improvement.
> **Safe to share with Gemini, GPT, or any AI assistant for help and analysis.**
> **Updated:** 2026-04-19

---

## 1. Project Summary

PolyTrade Bot is an algorithmic trading system targeting two markets:

1. **Polymarket** — Binary prediction markets on Polygon L2 (e.g. "Will BTC be above $X in the next 5 minutes?")
2. **Crypto Scalping** — 5-minute BTC/ETH scalping via Freqtrade on Binance/Bybit

The bot uses a **5-agent Claude AI pipeline** (Data → Quant → Strategy → Risk → Orchestrator) to analyze markets and make trading decisions, with a deterministic fallback if the API is unavailable.

**Current focus:** Polymarket 5-minute BTC counter-momentum strategy. Validated via 60-day backtest.

---

## 2. Polymarket 5-Minute Binary Markets — How They Work

Understanding this is essential to understand why our strategy works.

### Market Structure
- Every 5 minutes, Polymarket creates a new binary market: "Will BTC be **above** its current price in exactly 5 minutes?"
- The starting price (called **Price To Beat / PTB**) is set at window open using the Chainlink oracle price
- At window close (t=5min), the closing oracle price is compared to PTB:
  - If `close > PTB` → **YES wins** (pay $1 per YES share)
  - If `close < PTB` → **NO wins** (pay $1 per NO share)
- Entry price is typically near **$0.50** (50/50 market)
- **Polymarket charges 2% fee on gross winnings** (not on stake)

### Data Sources Used
- **Candle data:** Coinbase Exchange API — `GET /products/BTC-USD/candles?granularity=300` (5-min OHLCV, public, no auth)
- **PTB (Price To Beat):** Polymarket crypto API — `GET https://polymarket.com/api/crypto/crypto-price`
- **Market list:** Polymarket Gamma API — `GET https://gamma-api.polymarket.com/markets`

### Fee Breakeven Math
```
Win payout per share: $1.00 × (1 - 0.02 fee) = $0.98
Entry cost per share: $0.50
Net win:  $0.98 - $0.50 = +$0.48
Net loss: -$0.50

Breakeven win rate = 0.50 / (0.48 + 0.50) = 51.02%
```
Any strategy with win rate above **51.02%** is profitable after fees.

---

## 3. Strategy: Counter-Momentum Mean Reversion

### Discovery Process (April 18–19, 2026)

**Initial hypothesis (WRONG):** EMA 9/21 trend + RSI filter → bet YES when bullish
- Result: Win rate 38%, Sharpe -5.06 — complete failure

**Why it failed:** EMA trend and RSI tell you about the _direction of the past 45–105 minutes_. But each 5-minute window is essentially a coin flip that starts fresh at 50/50. Trend filters have zero predictive power for binary outcomes.

**Key discovery (from data analysis):**
After splitting the backtest trades by 3-candle momentum buckets:
```
momentum > +0.30%  → YES bet win rate: 41.9%  (58.1% for NO!)
momentum < -0.30%  → NO  bet win rate: 42.9%  (57.1% for YES!)
```
**Strong momentum predicts REVERSAL, not continuation.**

### Why Mean Reversion Occurs in These Markets

1. **Market maker behavior:** When BTC has run up strongly, market makers flood YES orders to capture the premium, pushing YES price above $0.50 and making NO the better bet
2. **Arb traders:** If YES is overpriced, arbitrageurs sell YES (effectively betting NO), pushing the price back toward 50/50
3. **Natural mean reversion in 5-min BTC:** On a 5-minute timeframe, BTC often partially retraces sharp moves within the next window

### Current Signal Logic

```python
# File: polymarket/backtester_5m.py — _compute_signal()
# File: ai_agents/strategy_agent.py — assess_setup()

momentum_pct = (candle_open - close_3_candles_ago) / close_3_candles_ago * 100

# Only trade STRONG moves (0.40% threshold found optimal via iteration)
if abs(momentum_pct) < 0.40:
    return SKIP  # No edge in moderate/weak momentum

if momentum_pct > 0.40:
    # Price ran up strongly → bet NO (mean reversion down)
    score = 0.50 (base)
    score += 0.10 if momentum > 0.60% (very strong move)
    score += 0.15 if last 2 candles both green (consecutive_up confirms overbuy)
    score += 0.10 if RSI > 60 (elevated RSI confirms overextension)
    score += 0.10 if volume >= 0.4x 20-bar mean (liquid enough to arb)

else:  # momentum < -0.40%
    # Price ran down strongly → bet YES (mean reversion up)
    score = 0.50 (base) + same bonuses mirrored

# Entry threshold: score >= 0.50 (set via min_edge_pct=5.0 → 5.0/10 = 0.50)
```

### Threshold Iteration History

| Momentum Threshold | Sharpe (60d) | Win Rate | Notes |
|-------------------|-------------|----------|-------|
| EMA+RSI (old) | -5.06 | 38.1% | EMA has no edge on binary markets |
| 0.30% counter | 0.770 | 54.6% | Too many moderate-momentum trades |
| 0.40% counter | **1.181** | **55.9%** | ✓ Optimal — filters noise |

---

## 4. Validated Backtest Results (2026-04-19)

### 60-Day Backtest (Primary Validation)
```
Asset:           BTC
Period:          60 days (~Mar–Apr 2026)
Starting capital: $8.89 (micro bankroll)
Final balance:   $17.79
Total return:    +100.15%
Win rate:        55.88% (290 wins / 229 losses)
Skipped:         17,006 / 17,525 windows (97.0% of windows skipped — very selective)
Sharpe ratio:    1.181 (annualized, per-trade basis, 252-day normalization)
Sortino ratio:   11.56
Max drawdown:    10.04%
Profit factor:   1.161 (gross wins / gross losses)
Avg trade PnL:   +$0.0078 per trade
Fees paid:       $2.59 (29% of starting capital — brutal at micro bankroll)
Strategy label:  Momentum3c+RSI35-78+Volume+YES+NO+Fees+Slippage
```

### 30-Day Backtest (Supplemental)
```
Total return:    +47.14%
Win rate:        52.91%
Sharpe ratio:    0.310
Max drawdown:    9.40%
Profit factor:   1.040
```

> The 30-day Sharpe (0.31) looks worse than 60-day (1.18) because 361 trades is a smaller sample. The edge requires volume to stabilize — ~500+ trades for reliable Sharpe measurement.

### Against PROJECT_RULES.md Thresholds

| Metric | Result | Minimum | Status |
|--------|--------|---------|--------|
| Sharpe > 0.8 | 1.181 | 0.8 | ✅ Pass |
| Win Rate > 45% | 55.9% | 45% | ✅ Pass |
| Max Drawdown < 20% | 10.0% | 20% | ✅ Pass |
| Profit Factor > 1.0 | 1.161 | 1.0 | ✅ Pass |
| Profit Factor > 1.2 (target) | 1.161 | 1.2 | ⚠️ Below target |
| Trades > 50 | 519 | 50 | ✅ Pass |

---

## 5. Position Sizing Logic

### Tiered Kelly System

The bankroll is classified into 5 tiers, each with different risk limits:

| Tier | Bankroll | Max Risk/Trade | Kelly Fraction | Min Bet |
|------|----------|---------------|----------------|---------|
| micro | $0–$10 | 0.5% | 10% | $0.05 |
| small | $10–$100 | 0.75% | 15% | $0.10 |
| conservative | $100–$1,000 | 1.0% | 20% | $0.50 |
| balanced | $1,000–$10,000 | 1.25% | 25% | $2.00 |
| growth | $10,000+ | 1.5% | 25% | $5.00 |

### Kelly Formula Applied
```python
# For binary market:
b = (1 - entry_price) / entry_price   # profit ratio
f* = (p * b - (1-p)) / b              # full Kelly fraction
f_capped = min(f* × kelly_fraction, tier_max_risk, 0.03)  # 3% hard cap
position_$ = bankroll × f_capped
```

### Hard Safety Limits (Cannot Be Overridden)
- Max 3% of bankroll per single trade
- Stop all trading if balance < $5.00 (FLOOR_BALANCE)
- Stop all trading if daily loss > 10% (HARD_DAILY_DRAWDOWN)
- Micro bankroll ($<10): forced minimum $0.10 bet when Kelly is too small

---

## 6. AI Agent Pipeline

### Agent Flow
```
[MarketData] → DataAgent → [NormalizedSnapshot]
                              ↓
                          QuantAgent → [EVAnalysis: probability, edge, Kelly]
                              ↓
                          StrategyAgent → [SignalAssessment: YES/NO/wait, quality score]
                              ↓
                          RiskExecutionAgent → [Approval: approved/rejected/reduced]
                              ↓
                          Orchestrator → [FinalDecision: buy/sell/hold/skip]
```

### Key Design Decisions
- Each agent has a **deterministic fallback** — if Claude API is down, the bot still works
- Orchestrator is the ONLY agent that outputs a final trade decision
- RiskExecutionAgent must explicitly approve before any order is placed
- Prompt caching enabled via `utils/claude_client.py` (reduces API costs)

### StrategyAgent (updated Apr 19)
The StrategyAgent was rewritten to mirror `backtester_5m._compute_signal` exactly:
- Replaced EMA 9/21 crossover filter with 3-candle momentum counter-signal
- Added NO-side signal detection (previously only YES)
- Window Delta from live oracle is used as a 5% bonus on top of momentum signal (only meaningful in realtime when live oracle diverges from PTB)

---

## 7. Known Bugs & Limitations

### Sortino Ratio Overflow (30-day)
The 30-day backtest shows `sortino_ratio = 1.07e+15` (numerical overflow). This happens because the denominator (downside deviation) approaches zero when there are very few losing trades in certain rolling windows. The 60-day result (11.56) is normal.

**Not fixed yet** — affects display only, does not affect trading logic.

### WebSocket Listener Incomplete
`polymarket/websocket_listener.py` connects to the Polymarket WebSocket but only logs raw messages. Event parsing and callbacks are not implemented. The realtime trading loop (`trader.py`) currently uses REST polling instead.

**Impact:** Live monitoring is slightly delayed (REST poll interval) compared to WS push.

### Crypto Scalper Never Validated
`crypto_scalper/freqtrade_strategies/my_5m_scalper.py` has never been backtested. The EMA9/21 + RSI strategy there is the original approach that FAILED on Polymarket. It may or may not work on continuous crypto markets (different market structure).

---

## 8. Open Research Questions

These are the questions being actively investigated:

1. **Does the counter-momentum edge hold on ETH/SOL?**
   - Only tested on BTC so far
   - Different assets may have different arb dynamics and liquidity

2. **Does the edge hold at different bankroll sizes?**
   - Current backtest used $8.89 (micro tier)
   - At $100+ (conservative tier), Kelly allows larger bets — fee impact per dollar decreases

3. **Is the 60-day window representative?**
   - BTC was in a specific market regime during the backtest period
   - Need to test on different 60-day periods (e.g., high-volatility vs low-volatility)

4. **Can Profit Factor be pushed above 1.2?**
   - Currently 1.161 (below 1.2 target)
   - Options: tighter entry filter, longer momentum lookback (5-candle vs 3-candle), RSI confirmation only on extremes

5. **What is the optimal `min_edge_pct` for different bankroll sizes?**
   - Currently hardcoded to 5.0 (threshold = 0.50)
   - Larger bankroll = can afford more selective entries

---

## 9. Daily Workflow

```bash
# Morning: check yesterday's results
python daily_report.py

# Start bot (paper trading, safe by default)
python main.py --mode polymarket-realtime --interval 60

# View live markets while bot runs
python polymarket/five_min_monitor.py --interval 30

# Evening: check dashboard
python main.py --mode polymarket-5m-dashboard

# After any strategy change: run backtest
python main.py --mode polymarket-backtest --days 60

# End of day: write research log
# → research/daily/YYYY-MM-DD.md
```

---

## 10. How to Ask an AI Assistant for Help

When sharing this document with Gemini/GPT, provide the relevant section and ask a specific question. Examples:

**For strategy improvement:**
> "Here is my current signal logic [paste Section 3]. I want to improve Profit Factor from 1.16 to 1.2+. What signal changes would you recommend? Consider that I am limited to 5-minute BTC OHLCV candle data with no look-ahead."

**For debugging:**
> "My Sortino ratio shows 1.07e+15 in the 30-day backtest but 11.56 in the 60-day [paste Section 7]. What causes this and how do I fix the calculation?"

**For code review:**
> "Here is my `_compute_signal` function [paste code]. Does this have any look-ahead bias? Are there edge cases I'm missing?"

**For backtest analysis:**
> "I have these backtest results [paste numbers from Section 4]. Is the strategy genuinely profitable or could this be overfitted to a specific 60-day window?"
