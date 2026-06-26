# TRADE FORENSIC AUDIT 001

This report presents the trade forensic analysis for the paper session run ID **`20260616T093209Z_24696_60b2c27c`** using records from `trade_journal/2026-06-16.jsonl`.

---

## 1. Trade Metrics Summary

| Metric | Value |
| :--- | :--- |
| **Number of Entries** | 3 |
| **Number of Exits** | 3 |
| **Realized PnL** | **+0.035676 USDC** |
| **Win Rate** | **100.00%** |
| **Average Hold Time** | **15.00 seconds** |
| **Stop Losses Triggered** | **0** |

---

## 2. Individual Trade Details

### Trade 1: Bitcoin (BTC) — Short (NO)
- **Asset / Side**: BTC / NO (Predicting price will not exceed strike/revert)
- **Entry Price / Exit Price**: `0.47` / `0.53`
- **Realized PnL**: `+0.020685 USDC`
- **Hold Time**: 20.0 seconds
- **Exit Reason**: `take_profit_target_reached`
- **Signal Name**: `PROBABILITY_EV_EDGE`
- **Entry EV**: `0.168398`
- **Entry Probability**: `0.638398`

### Trade 2: Ethereum (ETH) — Short (NO)
- **Asset / Side**: ETH / NO
- **Entry Price / Exit Price**: `0.51` / `0.58`
- **Realized PnL**: `+0.006904 USDC`
- **Hold Time**: 13.0 seconds
- **Exit Reason**: `take_profit_target_reached`
- **Signal Name**: `PROBABILITY_EV_EDGE`
- **Entry EV**: `0.142374`
- **Entry Probability**: `0.652374`

### Trade 3: Ethereum (ETH) — Long (YES)
- **Asset / Side**: ETH / YES
- **Entry Price / Exit Price**: `0.56` / `0.65`
- **Realized PnL**: `+0.008086 USDC`
- **Hold Time**: 12.0 seconds
- **Exit Reason**: `take_profit_target_reached`
- **Signal Name**: `PROBABILITY_EV_EDGE`
- **Entry EV**: `0.097982`
- **Entry Probability**: `0.657982`

---

## 3. Forensic Conclusion

- **Stop Loss Failsafes**: No stop losses were triggered. All 3 positions hit their profit targets swiftly (within 12 to 20 seconds).
- **Execution Strategy**: The strategy successfully sniped undervalued contracts based on the `PROBABILITY_EV_EDGE` signal model.
- **Data Quality**: Trade entries and exits were recorded cleanly with matching schema fields.
