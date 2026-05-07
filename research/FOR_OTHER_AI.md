# PolyTrade Bot — Context for External AI Assistants
# (Gemini, ChatGPT, Grok, etc.)
#
# วิธีใช้: Copy section ที่ต้องการ + paste ลงใน AI ตัวอื่น
# ไม่ต้อง paste ทั้งหมด — เลือกเฉพาะ section ที่เกี่ยวกับงานที่จะถาม
# Updated: 2026-04-19

---

## [SECTION A] — Project Summary (paste นี้เสมอ — เป็น base context)

```
โปรเจคชื่อ PolyTrade Bot — Python algorithmic trading bot ที่ trade บน Polymarket
(binary prediction markets บน Polygon L2) และ crypto scalping ผ่าน Freqtrade

Stack: Python 3.11, Anthropic SDK, py-clob-client, pydantic-settings v2, httpx, pandas/numpy

Strategy ที่ validated แล้ว: Counter-momentum mean reversion บน Polymarket 5-min BTC markets
- ทุก 5 นาที Polymarket สร้าง market ใหม่: "Will BTC be above its current price in 5 min?"
- ถ้า BTC วิ่งขึ้นแรง (>0.40% ใน 3 candles) → bet NO (mean reversion down)
- ถ้า BTC วิ่งลงแรง (>0.40% ใน 3 candles) → bet YES (mean reversion up)
- Polymarket fee: 2% of gross winnings → breakeven win rate = 51.02%

60-day backtest results (BTC, Apr 2026):
- Return: +100.15% | Win Rate: 55.88% | Sharpe: 1.181 | Max Drawdown: 10.04%
- Profit Factor: 1.161 | Trades: 519 | Fees paid: $2.59 on $8.89 start

Signal logic (file: polymarket/backtester_5m.py → _compute_signal()):
  momentum_pct = (candle_open - close_3_candles_ago) / close_3_candles_ago * 100
  if momentum_pct > +0.40% → NO score = 0.50 base
    +0.10 if momentum > 0.60% (very strong)
    +0.15 if last 2 candles both bullish (consecutive_up)
    +0.10 if RSI > 60 (overbought)
    +0.10 if volume >= 0.4x 20-bar mean
  if momentum_pct < -0.40% → YES score = 0.50 base (mirror)
  if |momentum_pct| < 0.40% → SKIP (no edge)
  Entry threshold: score >= 0.50
```

---

## [SECTION B] — Strategy Code (paste เมื่อถามเรื่อง signal logic)

```python
# File: polymarket/backtester_5m.py
_MOM_THRESHOLD = 0.40   # % threshold (tested: 0.30→Sharpe 0.77, 0.40→Sharpe 1.18)
_MOM_STRONG    = 0.60   # bonus for very strong momentum
_RSI_OB        = 60     # RSI overbought threshold
_RSI_OS        = 40     # RSI oversold threshold
_VOL_FACTOR    = 0.4    # min volume as fraction of 20-bar mean

def _compute_signal(self, candles: pd.DataFrame, idx: int) -> tuple[str, float]:
    price_now  = candles.iloc[idx]["open"]
    price_3ago = candles.iloc[idx - 3]["close"]
    momentum_pct = (price_now - price_3ago) / max(price_3ago, 1.0) * 100.0
    abs_mom = abs(momentum_pct)

    rsi_val = _compute_rsi(candles["close"].iloc[: idx + 1])
    rsi_ok  = rsi_val is not None
    vol_ok  = (
        candles.iloc[idx]["volume"] >= _VOL_FACTOR * candles["volume"].iloc[max(0, idx - 20): idx].mean()
        if idx >= 5 else False
    )
    c1_bull = candles.iloc[idx - 1]["close"] > candles.iloc[idx - 1]["open"]
    c2_bull = candles.iloc[idx - 2]["close"] > candles.iloc[idx - 2]["open"]
    c1_bear = not c1_bull
    c2_bear = candles.iloc[idx - 2]["close"] < candles.iloc[idx - 2]["open"]
    consecutive_up   = c1_bull and c2_bull
    consecutive_down = c1_bear and c2_bear

    yes_score = no_score = 0.0

    if abs_mom < _MOM_THRESHOLD:
        pass  # no edge
    elif momentum_pct > _MOM_THRESHOLD:
        no_score += 0.50
        if abs_mom   > _MOM_STRONG:     no_score += 0.10
        if consecutive_up:              no_score += 0.15
        if rsi_ok and rsi_val > _RSI_OB: no_score += 0.10
        if vol_ok:                      no_score += 0.10
    else:
        yes_score += 0.50
        if abs_mom   > _MOM_STRONG:      yes_score += 0.10
        if consecutive_down:             yes_score += 0.15
        if rsi_ok and rsi_val < _RSI_OS: yes_score += 0.10
        if vol_ok:                       yes_score += 0.10

    if yes_score >= 0.50 and yes_score >= no_score:
        return "YES", yes_score
    if no_score >= 0.50 and no_score > yes_score:
        return "NO", no_score
    return "SKIP", 0.0
```

---

## [SECTION C] — Backtest Results Detail (paste เมื่อถามเรื่อง performance / optimization)

```
60-day backtest (primary, BTC, Mar–Apr 2026):
  initial_balance:   $8.89
  final_balance:     $17.79
  total_return_pct:  100.15%
  n_trades:          519  (290 wins / 229 losses)
  n_skipped:         17,006 / 17,525 windows (97% skipped — very selective)
  win_rate:          55.88%
  sharpe_ratio:      1.181  (annualized, 252-day normalization)
  sortino_ratio:     11.56
  max_drawdown_pct:  10.04%
  profit_factor:     1.161  (target is 1.2 — slightly below)
  avg_trade_pnl:     +$0.0078
  total_fees_paid:   $2.59

30-day backtest (supplemental):
  total_return_pct:  47.14%
  n_trades:          361
  win_rate:          52.91%
  sharpe_ratio:      0.310  (lower because smaller sample)
  max_drawdown_pct:  9.40%
  profit_factor:     1.040

Fee math:
  Entry price: $0.50/share
  Win payout:  $0.98/share (after 2% fee)
  Net win:     +$0.48  |  Net loss: -$0.50
  Breakeven win rate = 0.50 / (0.48 + 0.50) = 51.02%
  Current win rate 55.88% >> 51.02% ✓
```

---

## [SECTION D] — Risk & Position Sizing (paste เมื่อถามเรื่อง money management)

```python
# File: utils/risk_manager.py
# Kelly formula for binary markets:
#   b = (1 - entry_price) / entry_price   # profit ratio
#   f* = (p*b - (1-p)) / b                # full Kelly
#   f_capped = min(f* × kelly_fraction, tier_max_risk, 0.03)

FLOOR_BALANCE         = 5.00   # hard stop — cease all trading below this
HARD_CAP_SINGLE_TRADE = 0.03   # never risk > 3% of bankroll per trade
HARD_DAILY_DRAWDOWN   = 0.10   # stop day if daily loss > 10%

Bankroll tiers:
  micro        $0–$10      max_risk=0.5%   kelly=10%   min_bet=$0.05
  small        $10–$100    max_risk=0.75%  kelly=15%   min_bet=$0.10
  conservative $100–$1K    max_risk=1.0%   kelly=20%   min_bet=$0.50
  balanced     $1K–$10K    max_risk=1.25%  kelly=25%   min_bet=$2.00
  growth       $10K+       max_risk=1.5%   kelly=25%   min_bet=$5.00

Current wallet: $8.82 USDC → micro tier
```

---

## [SECTION E] — File Structure (paste เมื่อถามเรื่อง codebase / architecture)

```
polymarket/
  backtester_5m.py         ★ Strategy source of truth — _compute_signal()
  trader.py                Live/paper trading loop
  client.py                Wallet auth + USDC balance (CLOB API + on-chain Web3)
  gamma_fetcher.py         Polymarket Gamma API — fetches active markets
  order_manager.py         Kelly-based risk plan before order submission
  oracle_price_feed.py     Coinbase 5-min candle feed (thread-safe)
  price_to_beat_fetcher.py PTB per window from Polymarket crypto API
  realtime_logger.py       CSV/JSON logging per scan cycle

ai_agents/
  orchestrator.py          Coordinates 5 agents → final buy/sell/hold
  data_agent.py            Market data normalization
  quant_agent.py           EV, edge, Kelly calculation
  strategy_agent.py        Mirrors _compute_signal() exactly
  risk_execution_agent.py  Final gatekeeper — approves/rejects

utils/
  risk_manager.py          Tiered Kelly + hard caps
  claude_client.py         Anthropic SDK + prompt caching + retry

config/settings.py         pydantic v2 BaseSettings — all env vars
```

---

## [SECTION F] — Open Questions / Research Areas

```
1. Profit Factor ยังต่ำกว่า target (1.161 vs target 1.2)
   → ลอง: tighter entry (0.45% threshold), 5-candle lookback, RSI extremes only (>65/<35)

2. ยังไม่ได้ test ETH/SOL — counter-momentum อาจทำงานต่างกัน

3. 60-day window อาจ period-specific (Mar–Apr 2026 bull market)
   → ต้องรัน 90-day และ different time periods

4. WebSocket listener ยังไม่ complete — ใช้ REST polling แทน
   → file: polymarket/websocket_listener.py

5. Crypto scalper (freqtrade) ยังไม่เคย backtest เลย
   → file: crypto_scalper/freqtrade_strategies/my_5m_scalper.py
```

---

## วิธีใช้ไฟล์นี้กับ AI ตัวอื่น

### ถามเรื่อง strategy improvement:
> paste [SECTION A] + [SECTION B] + [SECTION C] แล้วถาม:
> "ฉันอยากเพิ่ม Profit Factor จาก 1.161 ให้ถึง 1.2+ มีข้อมูลแค่ 5-min BTC OHLCV
>  ควรแก้ signal ยังไง ห้ามใช้ lookahead bias"

### ถาม code review:
> paste [SECTION A] + [SECTION B] แล้วถาม:
> "ช่วย review _compute_signal() ว่ามี lookahead bias ไหม และ edge case ที่อาจพลาด"

### ถาม risk management:
> paste [SECTION A] + [SECTION D] แล้วถาม:
> "bankroll $8.82 ควรปรับ Kelly parameters ยังไงให้ risk-adjusted return ดีที่สุด"

### ถาม architecture:
> paste [SECTION A] + [SECTION E] แล้วถาม:
> "ช่วย review architecture ว่ามีจุดไหน single point of failure ไหม"
