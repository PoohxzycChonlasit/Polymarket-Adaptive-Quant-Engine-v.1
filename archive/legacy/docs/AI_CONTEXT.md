# PolyTrade Bot — AI Context File
> Copy-paste ไฟล์นี้ทั้งหมดเพื่อให้ AI อื่น (ChatGPT, Gemini, Claude ฯลฯ) เข้าใจ project ได้ทันที
> อัปเดตล่าสุด: 2026-04-25

---

## สิ่งที่กำลังสร้าง

Bot เทรด **Polymarket 5-minute BTC/ETH/SOL Up/Down binary markets** บน Polygon L2
Strategy: **counter-momentum mean reversion** — เมื่อราคาวิ่งแรงใน 3 candles → bet ว่าจะ revert กลับ

ผ่านการ validate แล้ว: BTC 60d Sharpe 1.18 | WR 55.9% | MaxDD 10% | Breakeven WR = 51.02%

---

## Data Pipeline (ปัจจุบัน)

```
Binance WebSocket → BinanceFeed (polymarket/market_feed.py)
    ↓ closed 5-min klines (<1ms latency)
compute_realtime_signal(asset, imbalance)  (polymarket/signal.py)
    ↑ Polymarket CLOB orderbook → imbalance = (bid_vol - ask_vol) / total_vol
    ↓ side=YES|NO|SKIP, score=0.50–0.95
PolymarketTrader._analyze_market()  (polymarket/trader.py)
    ↓ microstructure WinProb formula (ไม่มี AI dependency)
RiskManager Kelly sizing → paper/live order
```

**Claude AI pipeline ถูกลบออก 25 Apr** — ทำให้เกิด 0 trades / 574 scans (latency + rate limits)

---

## Signal Rules (ห้ามแก้โดยไม่ผ่าน 60d backtest)

```python
momentum_pct = (candle_open - close_3_candles_ago) / close_3_candles_ago * 100

# Bounds: 0.40–1.00% (tested optimal)
if  0.40 <= momentum_pct < 1.00:   → BET NO   (mean revert down)
if -1.00 <  momentum_pct <= -0.40: → BET YES  (mean revert up)
else:                               → SKIP

# Score bonuses (threshold เข้า trade = 0.50):
  +0.50 base
  +0.10 if |mom| > 0.60%
  +0.15 if last 2 candles consecutive same direction
  +0.10 if RSI confirms (35–78 band)
  +0.10 if volume >= 0.4× 20-bar mean
  +0.05 if CLOB orderbook imbalance > 10% aligns (ใหม่ Apr 25)
```

---

## ไฟล์สำคัญ

| ไฟล์ | หน้าที่ |
|------|---------|
| `polymarket/backtester_5m.py` | `_compute_signal()` = source of truth ของ strategy |
| `polymarket/market_feed.py` | Binance WS singleton — `get_feed()` (ใหม่ Apr 25) |
| `polymarket/signal.py` | `compute_realtime_signal(asset, imbalance)` |
| `polymarket/trader.py` | Full trade cycle (ไม่มี AI) |
| `utils/risk_manager.py` | Kelly + tiers + FLOOR=$5 |
| `config/settings.py` | Settings ทั้งหมด (pydantic v2) |

---

## Bankroll Tiers (อัปเดต Apr 25 — aggressive scaling)

| Tier | Balance | Max Risk/Trade |
|------|---------|---------------|
| micro | $0–$10 | 0.5% |
| small | $10–$100 | 1.0% |
| conservative | $100–$1K | 1.5% |
| balanced | $1K–$10K | 2.0% |
| growth | $10K+ | 2.5% |

Hard caps: `FLOOR=$5` | `HARD_CAP_SINGLE=3%` | `DAILY_DD=10%`

Optional flags: `--score-scale` (bet size ×2 เมื่อ score สูง) | `--momentum-price` (entry price discount เหมือน trader มือโปร)

---

## Phases

| Phase | Status | รายละเอียด |
|-------|--------|-----------|
| 1 — Fast data + no AI | ✅ Done Apr 25 | Binance WS, ลบ Claude, orderbook imbalance |
| 2 — ML model | ❌ ต้องทำต่อ | XGBoost 11 features, SQLite data, Pyth oracle |
| 3 — Risk upgrade | ❌ ทีหลัง | Exit strategy 5 rules, dynamic Kelly, safety systems |
| 4 — Go-live | ❌ Blocked | ต้องมี MATIC + 30 paper trades ก่อน |

---

## Blockers สำหรับ Live Trading

1. **MATIC = 0** → wallet `0x645a661bcf56c28297538848b6c519e378e833e2` ต้องการ ~0.5 MATIC
2. **USDC ยังไม่ deposit** ไป Polymarket CLOB
3. **30+ paper trades** ยังไม่ผ่าน validation

---

## คำสั่ง Backtest

```bash
python main.py --mode polymarket-backtest --days 60 --asset BTC
python main.py --mode polymarket-backtest --days 3   # smoke test
python main.py --mode polymarket-backtest --days 60 --asset BTC,ETH --balance 50 --score-scale --momentum-price
```
