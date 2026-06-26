# POST PATCH TRADE COUNT AUDIT

This report provides the progress audit of paper trading sessions executed since the deployment of **PATCH_STOP_002** (commit `885a795`).

---

## 1. Patch & Deployment Info

- **PATCH_STOP_002 Commit Hash**: `885a795bd6b38c2e646279f2257270e5b7fb5f7b` (short: `885a795`)
- **Deployment Timestamp**: `2026-06-16 14:34:29 +0700` (UTC: `2026-06-16T07:34:29Z`)
- **First run_id after deployment**: `20260616T074336Z_32028_b627bd33`

---

## 2. Post-Patch Runs Detected
The following 3 runs have been executed since the patch was deployed:
1. `20260616T074336Z_32028_b627bd33`
2. `20260616T093209Z_24696_60b2c27c`
3. `20260616T100229Z_26460_cd8e7f25`

---

## 3. Trade Metrics Breakdown

- **Total Closed Trades**: **9**
- **YES Contracts**: **5**
- **NO Contracts**: **4**
- **Take Profit Exits**: **6**
- **Stop Loss Exits**: **3**
- **Stop Loss Shadow Events**: **73**

---

## 4. Individual Trade Log

| # | Run ID | Asset | Side | Entry | Exit | PnL | Reason |
| :-: | :--- | :-: | :-: | :-: | :-: | :--- | :--- |
| 1 | `20260616T074336Z_32028_b627bd33` | ETH | YES | `0.47` | `0.30` | `-0.018175` | `stop_loss` |
| 2 | `20260616T074336Z_32028_b627bd33` | ETH | YES | `0.50` | `0.40` | `-0.010040` | `stop_loss` |
| 3 | `20260616T093209Z_24696_60b2c27c` | BTC | NO | `0.47` | `0.53` | `+0.020685` | `take_profit_target_reached` |
| 4 | `20260616T093209Z_24696_60b2c27c` | ETH | NO | `0.51` | `0.58` | `+0.006904` | `take_profit_target_reached` |
| 5 | `20260616T093209Z_24696_60b2c27c` | ETH | YES | `0.56` | `0.65` | `+0.008086` | `take_profit_target_reached` |
| 6 | `20260616T100229Z_26460_cd8e7f25` | ETH | NO | `0.52` | `0.66` | `+0.015283` | `take_profit_target_reached` |
| 7 | `20260616T100229Z_26460_cd8e7f25` | ETH | YES | `0.54` | `0.62` | `+0.007450` | `take_profit_target_reached` |
| 8 | `20260616T100229Z_26460_cd8e7f25` | ETH | NO | `0.56` | `0.68` | `+0.010779` | `take_profit_target_reached` |
| 9 | `20260616T100229Z_26460_cd8e7f25` | BTC | YES | `0.49` | `0.39` | `-0.010272` | `stop_loss_hit` |

---

## 5. Audit Results Summary

- **Current Closed Trades (X)**: **9**
- **Remaining to Target (Y)**: **21**

### Verdict: **CONTINUE_COLLECTION**
