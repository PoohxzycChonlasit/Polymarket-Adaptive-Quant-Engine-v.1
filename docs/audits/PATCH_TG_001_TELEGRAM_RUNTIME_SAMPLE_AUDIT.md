# PATCH_TG_001_TELEGRAM_RUNTIME_SAMPLE_AUDIT

This audit reviews real, rendered Telegram operator notification samples generated after the integration of the compact display patch `PATCH_TG_001_TELEGRAM_COMPACT_FORMATTING`.

---

## 1. Rendered Sample Messages

### A. Runtime Startup
```text
🚀 START | PAPER | Run:run-f465 | Interval:10s
Wallet:paper | Live:OFF
```

### B. Trade Open
```text
🟢 OPEN | ETH NO | Entry:0.600 | Size:0.0836
Sig:EV_EDGE | Strat:sniper | EV:0.126 | P:0.656 | Run:run-f465
```

### C. Trade Close (Loss / Stop Loss)
```text
🔴 CLOSE | ETH NO | PnL:-0.0042 | SL
Hold:2m10s | Entry:0.600 | Exit:0.650 | Run:run-f465
```

### D. Trade Close (Profit / Take Profit)
```text
🟢 CLOSE | BTC YES | PnL:+0.0081 | TP
Hold:1m42s | Entry:0.420 | Exit:0.510 | Run:run-f465
```

### E. Risk Alert
```text
🚨 RISK | cooldown | Run:run-f465
State:PAUSED | Impact:drawdown threshold hit
```

### F. Critical Subsystem Error
```text
🚨 ERROR | runtime_exception | Run:run-f465
Cycle:4821 | Action:check logs
```

### G. Pipeline Attribution Failure
```text
🚨 ATTR_FAIL | candidate_trace_id missing | Run:run-f465
Trade:ETH NO | Action:stop/audit
```

### H. Runtime Heartbeat (Status)
```text
🟢 ALIVE | PAPER | Up:8h24m | Run:run-f465
Cycle:4821 | Open:2 | Closed:31 | PnL:+0.0240
```

### I. Daily Summary Digest
```text
📊 DAY | Trades:30 | W:11 L:19 | WR:36.7%
PnL:-0.0189 | EV_EDGE:+0.0179 | Quar:17
```

---

## 2. Template Evaluation Checklist

| Template | Rendered Lines | Key Data Present | Removals OK | Mappings Mapped | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Startup** | 2 | Mode, Run ID, Interval, Wallet, Live status | Yes | Mapped correctly | **PASS** |
| **Trade Open** | 2 | Market, Side, Price, Size, Sig, Strat, EV, P, Run ID | Yes | `PROBABILITY_EV_EDGE` → `EV_EDGE` | **PASS** |
| **Trade Close (SL)** | 2 | Market, Side, PnL, Reason, Hold (m/s), Entry/Exit, Run ID | Yes | `stop_loss` → `SL` | **PASS** |
| **Trade Close (TP)** | 2 | Market, Side, PnL, Reason, Hold (m/s), Entry/Exit, Run ID | Yes | `take_profit` → `TP` | **PASS** |
| **Risk Alert** | 2 | Reason, Run ID, State, Impact | Yes | Mapped correctly | **PASS** |
| **Subsystem Error** | 2 | Error Type, Run ID, Cycle, Action Hint | Yes | Mapped correctly | **PASS** |
| **Pipeline Attr Fail** | 2 | Failed Field, Run ID, Trade details, Action Hint | Yes | Mapped correctly | **PASS** |
| **Heartbeat (Status)** | 2 | Mode, Uptime, Run ID, Cycle, Open/Closed count, PnL | Yes | Mapped correctly | **PASS** |
| **Daily Digest** | 2 | Trade count, Wins/Losses, Win Rate, PnL, Edge PnL, Quar count | Yes | Mapped correctly | **PASS** |

*Note: All boilerplate metadata (`Meaning`, `Evidence`, `Ref`, `Session:n/a`, `Lifecycle:n/a`, `Price Bucket:n/a`, etc.) has been completely removed.*

---

## 3. Verdict

### **`TELEGRAM_COMPACT_UI_PASS`**

All message layouts generated strictly fit within the **2-line maximum budget**, apply display overrides, omit empty/n/a values, and dramatically improve mobile screen utilization for the operator.
