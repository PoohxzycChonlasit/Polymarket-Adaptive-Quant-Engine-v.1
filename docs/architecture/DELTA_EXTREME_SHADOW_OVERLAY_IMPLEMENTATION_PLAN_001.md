# DELTA_EXTREME_SHADOW_OVERLAY_IMPLEMENTATION_PLAN_001

* **Date:** 2026-06-20
* **Target Workspace:** `c:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
* **Status:** **`IMPLEMENTATION PLANNING COMPLETE`**
* **Primary Role:** `02_CODE_ARCHITECT_AGENT` (Systems modulations & logging interfaces)
* **Supporting Roles:** `03_RISK_MANAGER_AGENT` (Safety boundaries), `07_TEST_CI_AGENT` (Test specifications)

---

## 1. File Impact Map

The implementation requires modifications to three existing files and the creation of one new test module:

| File | Modification Details | Risk Level | Runtime Behavior Change |
| :--- | :--- | :---: | :---: |
| **`utils/quant_event_logger.py`** | Register `delta_shadow` event category and log directory mapping; add `log_delta_shadow()` method. | **Low** | None (purely additive observability method). |
| **`polymarket/trader.py`** | Insert shadow overlay evaluator hook inside `_analyze_market_quant()` where `skip_reason == "delta_extreme"`. Add private helper `_evaluate_and_log_delta_extreme_shadow()`. | **Medium** | None (active trading and order routing flows remain unchanged). |
| **`config/settings.py`** | Add `delta_shadow_enabled: bool = False` configuration parameter to control overlay lifecycle. | **Low** | None. |
| **`tests/test_delta_shadow.py`** | **[NEW]** Targeted unit tests verifying gates, sizing, logging, and crash-resilience. | **Low** | None. |

---

## 2. Hook Location Design

The hook will be placed inside `polymarket/trader.py` within `_analyze_market_quant()`, specifically in the block handling `skip_reason` outcomes (around line 9461):

```python
        # Existing skip logic in trader.py:
        if skip_reason:
            # New Shadow Hook Block:
            if skip_reason == "delta_extreme" and self.settings.delta_shadow_enabled:
                try:
                    self._evaluate_and_log_delta_extreme_shadow(
                        market=market,
                        ticker=ticker,
                        ptb_info=ptb_info,
                        model_side=model_side,
                        confidence=confidence,
                        model_ev=model_ev,
                        delta=delta,
                        ob_spread=ob_spread,
                        ob_liquidity_usd=ob_liquidity_usd,
                        yes_token_id=yes_token_id,
                        no_token_id=no_token_id,
                        yes_bid=yes_bid,
                        yes_ask=yes_ask,
                        yes_bid_size=yes_bid_size,
                        yes_ask_size=yes_ask_size,
                        no_bid=no_bid,
                        no_ask=no_ask,
                        no_bid_size=no_bid_size,
                        no_ask_size=no_ask_size,
                        yes_orderbook_age_ms=yes_orderbook_age_ms,
                        no_orderbook_age_ms=no_orderbook_age_ms,
                        feed_age=feed_age,
                        current_balance=current_balance,
                        timing_detail=timing_detail,
                    )
                except Exception as exc:
                    LOGGER.exception("[SHADOW] Failed to process delta shadow: %s", exc)

            # Continued existing skip logging & return:
            self._log_risk_section(
                bankroll=current_balance,
                ...
            )
            return outcome
```

This ensures that the shadow evaluation is triggered **only** when `delta_extreme` has bypassed order execution, and runs within a hard `try/except` block to prevent loop disruption.

---

## 3. Logger Design

* **Log Directory:** `runtime/quant_data/delta_shadow/`
* **JSONL File Name:** `YYYY-MM-DD.jsonl` (standard daily log file).
* **Quant Event Category:** `delta_shadow` mapped via `QuantEventLogger._CATEGORY_BY_METHOD`.
* **Fail-Soft Behavior:** Inherits the parent `QuantEventLogger` write safety mechanics. If a write fails (e.g. disk full or `PermissionError`), logging for the category is silently disabled in memory for the run rather than raising an unhandled exception in `trader.py`.
* **Log Space Footprint:** At an average of 5,000 skipped events per day at 1.5 KB per JSON line, maximum log usage is bounded to **~7.5 MB per day**.

---

## 4. Evaluator Design

We define a pure helper method `_evaluate_and_log_delta_extreme_shadow` inside `polymarket/trader.py` (which delegates calculation details to `evaluate_delta_extreme_shadow_candidate`):

```python
def evaluate_delta_extreme_shadow_candidate(
    *,
    price: float,
    spread: float,
    quote_age_ms: int,
    oracle_age_ms: int,
    ask_size: float,
    seconds_remaining: float,
) -> tuple[bool, str | None, float, float]:
    """Pure helper evaluating shadow executability gates and sizing tracks."""
    # 1. Price Gate
    if price <= 0.0 or price >= 1.0:
        return False, "price_unavailable", 0.0, 0.0
    
    # 2. Spread Gate
    if spread > 0.06:
        return False, "spread_too_wide", 0.0, 0.0
        
    # 3. Freshness Gates
    if quote_age_ms > 1000:
        return False, "quote_stale", 0.0, 0.0
    if oracle_age_ms > 5000:
        return False, "oracle_stale", 0.0, 0.0
        
    # 4. Sizing Calculations (Standard & Micro)
    # Standard: max($1.00 entry cost, 5 shares)
    std_shares = max(5.0, ceil(1.00 / price))
    # Micro: max($0.05 entry cost, 5 shares)
    micro_shares = max(5.0, ceil(0.05 / price))
    
    # 5. Depth Gate
    if ask_size < std_shares:
         return False, "liquidity_too_small", 0.0, 0.0
         
    # 6. Cutoff Gate
    if seconds_remaining <= 90:
         return False, "time_unsafe", 0.0, 0.0
         
    return True, None, std_shares, micro_shares
```

---

## 5. Settlement Design

To verify outcomes without blocking active threads:
1. Every logged candidate contains the target `market`, `token_id`, and `epoch_start_ts`.
2. Settlement logic runs completely decoupled from the live trading loop. A background task or post-processing log compiler matches logged candidates to corresponding entries in `runtime/quant_data/path_truth/` using the composite key:
   $$\text{Match Key} = \text{market} \mathbin{\Vert} \text{epoch\_start\_ts}$$
3. Outcomes are resolved to a final win/loss state, and cumulative standard/micro PnL metrics are populated in the analysis database.

---

## 6. Required Unit Tests

We will add a suite of test cases to `tests/test_delta_shadow.py` using mock configurations:

1. **`test_delta_candidate_logged_on_skip`**: Mock a `delta_extreme` state and verify that a payload of category `delta_shadow` is logged.
2. **`test_no_log_on_non_delta_skip`**: Mock a `confidence_too_low` state and verify no `delta_shadow` event is written.
3. **`test_executable_gate_pass_fail`**: Test combinations of stale books (>1000ms), wide spreads (>0.06), and thin asks to verify the correct pass/fail categorization.
4. **`test_stale_quote_rejection`**: Assert that candidates with orderbooks older than 1s are rejected with `quote_stale`.
5. **`test_logger_failure_does_not_crash_loop`**: Mock a file write permission failure and assert that the main trader loop continues normal processing.
6. **`test_active_decision_remains_skip`**: Assert that in all evaluated cases, the trader method returns a skip outcome and does not touch active wallet inventory.

---

## 7. Rollback Plan

If the shadow overlay causes memory growth, file system locking, or thread delays, it can be immediately disabled using two redundant paths:

1. **Config Toggle (Zero-Code):** Set `PAPER_TRADING_DELTA_SHADOW_ENABLED=false` (or `delta_shadow_enabled=false` in `.env`). This skips evaluation logic entirely and resolves the hook immediately.
2. **Git Revert:** Revert the commits modifying `polymarket/trader.py` and `utils/quant_event_logger.py` to restore the original clean codebase state.

---

## 8. Safety Checklist

* **Can this place orders?** **NO.** The code path is restricted to passive variables and does not call any contract or API placement methods.
* **Can this change sizer?** **NO.** The sizing outputs are logged as attributes of the shadow payload and never mutate the active `OrderRequest` size.
* **Can this bypass delta_extreme?** **NO.** The active `skip_reason` remains `"delta_extreme"`, and the loops returns a skip outcome exactly as before.
* **Can this change stop-loss?** **NO.** It does not share code or data with Option D or live stop-loss controls.
* **Can this affect Option D?** **NO.** Option D tracking is isolated to `stop_loss_shadow` logs and runs independently.
* **Is it enabled by default?** **NO.** It is disabled by default via config settings and requires explicit operator activation.

---

## 9. Final Verdict

### **`APPROVE_PHASE_A_IMPLEMENTATION`**

The implementation plan is structurally isolated, guarantees zero mutation of active trading execution, implements standard fail-soft behavior, and specifies targeted unit tests for verification.

---

*Report prepared by Antigravity (Crypto Trading Bot Engineer Agent).*
