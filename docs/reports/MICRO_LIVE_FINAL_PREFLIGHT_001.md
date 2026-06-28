# Micro-Live Final Preflight Validation Report

> **DOCUMENT_TYPE: report**
> **DESTINATION:   docs/reports/MICRO_LIVE_FINAL_PREFLIGHT_001.md**
> **REASON:        Final preflight validation audit report detailing the GO/NO-GO verdict and environmental findings.**
>
> **TASK_CLASS: 0 HEALTH_CHECK**
> **Status: PREFLIGHT_COMPLETED**
> **Runtime Impact: NONE**

---

## 1. Executive Summary & Verdict

### Final Verdict
`NO_GO`

* **Reason**: The verify mode preflight check failed with **`[VERIFY FAILED] missing_allowance`**. The proxy wallet contains **20.0990 USDC** (satisfying the balance requirement), but has **0.0000 USDC allowance** approved for the Polymarket CLOB exchange. Live order placement will be blocked by the client preflight gate.
* **Action Required**: The operator must manually approve the USDC allowance for the CLOB contract on Polymarket before the validation run.

---

## 2. Preflight Status Check

| Category | Status | Details / Observed Telemetry |
|---|---|---|
| **Repository State** | **PASS** | Commit `ed14faa` is HEAD. Working tree is clean on all runtime Python and configuration files. |
| **Credentials & Auth** | **PASS** | CLOB API credentials are valid. API connectivity latency is **171ms**. |
| **USDC Balance** | **PASS** | Cash balance is **20.0990 USDC** (satisfies floor requirement). |
| **USDC Allowance** | **FAIL** | Current allowance is **0.0000 USDC** (insufficient for live betting). |
| **Kill Switch File** | **PASS** | `runtime/KILL_SWITCH` is currently **absent**. |
| **Telegram Setup** | **PASS** | Bot token and Chat ID are configured in `.env`. |
| **Stale Position State** | **PASS** | `runtime/position_tracker_state.json` is **absent** (no stale open positions). |

---

## 3. Micro-Live Cap Profile Validation

The current `.env` does not contain overrides for micro-live limits, meaning the system falls back to default settings which are **larger** than the target safety profile. 

**Recommended Action**: Add the following overrides to `.env` immediately before launching:
```ini
# Safe Micro-Live Gating Caps
LIVE_MAX_ORDER_USD=1.00
LIVE_MAX_DAILY_LOSS_USD=2.00
LIVE_MAX_OPEN_EXPOSURE_USD=2.00
MAX_OPEN_POSITIONS=1
BANKROLL_FLOOR=8.00
```

---

## 4. Manual Allowance Approval Procedure

To transition from `NO_GO` to `GO`:
1. Open a browser and navigate to the Polymarket UI: [Polymarket Settings](https://polymarket.com/settings).
2. Connect the wallet holding key `96aa77...9402`.
3. Under **Deposit/Approve**, sign the transaction to approve USDC spending for the CLOB Exchange contract.
4. Once confirmed on-chain, rerun:
   ```powershell
   .venv\Scripts\python.exe main.py --mode verify
   ```
5. Confirm that the status reports `allowance=OK` and verify mode returns exit code `0`.

---

## 5. Command Plan

* **Step 1: Verify State** (Preflight check):
  ```powershell
  .venv\Scripts\python.exe main.py --mode verify
  ```
* **Step 2: Supervised Launch** (Run for 5 cycles with 60s intervals then stop):
  ```powershell
  .venv\Scripts\python.exe main.py --mode live --interval 60 --run-cycle-count 5
  ```
* **Step 3: Emergency Halt** (Drop file to trigger immediate lockdown):
  ```powershell
  echo "STOP" > runtime/KILL_SWITCH
  ```
* **Step 4: Post-Trade Audit** (Verify event telemetry):
  ```powershell
  .venv\Scripts\python.exe tools/replay_analyzer.py
  ```
