# SHADOW_TELEMETRY_PHASE_B_IMPLEMENTATION_PLAN_001

* **Date:** 2026-06-21
* **Target Workspace:** `c:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
* **Status:** **`READY_FOR_SAFE_IMPLEMENTATION`**
* **Primary Role:** `02_CODE_ARCHITECT_AGENT` (Systems Architecture & Modularity)
* **Supporting Roles:** `07_TEST_CI_AGENT` (Testing Validation & Safety Gates)

---

## 1. Files to Modify & Create

To implement passive shadow telemetry with minimal surface area risk, we will touch only the following files:

### Modify:
1. **`config/settings.py`**: Add feature flag settings (`shadow_telemetry_enabled`, `shadow_filters_active`).
2. **`polymarket/trader.py`**: Wire the telemetry call inside the opportunity loop.
3. **`tests/test_shadow_filters.py`**: Expand the unit test suite to cover all new filters, flag states, and fail-soft paths.

### Create [NEW]:
1. **`polymarket/shadow_telemetry.py`**: A pure, lightweight helper module containing the core filter evaluations, parameter versioning, and default fail-safe configurations.

---

## 2. Feature Flag Definition

We will add a Pydantic field in `config/settings.py`:

```python
shadow_telemetry_enabled: bool = False
shadow_filters_active: list[str] = [
    "block_btc_shadow",
    "block_normal_vol_shadow",
    "combined_broad_shadow",
    "combined_conservative_shadow"
]
```

This flag defaults to `False` (`SHADOW_TELEMETRY_ENABLED=false` in `.env`) ensuring complete safety at rollout.

---

## 3. Event Logger Integration

We will reuse the existing `QuantEventLogger.log_signal_filter_shadow(shadow_payload)` method in `utils/quant_event_logger.py`. The logger is already integrated into the `PolymarketTrader` runtime context as `self.quant_events`, writing JSONL events under the `signal_filter_shadow` category. No new logging infrastructure or directories are required.

---

## 4. Runtime Hook Location

The telemetry hook will be placed in `polymarket/trader.py` inside `_process_ticker_opportunity` (around line 9444) immediately after the baseline model trade is approved (`is_model_trade` check) and before order processing is executed:

```python
is_model_trade = model_side in ("YES", "NO") and ev_result is not None and ev_result.approved
if is_model_trade:
    # --- PASSIVE SHADOW TELEMETRY EVALUATION ---
    if getattr(self.settings, "shadow_telemetry_enabled", False):
        self._evaluate_passive_shadow_telemetry(
            ticker=ticker,
            candidate=candidate,
            probability=probability,
            model_side=model_side,
            model_ev=model_ev,
            regime_detail=regime_detail,
            ptb_info=ptb_info,
            meta=meta,
            yes_token_id=yes_token_id,
            no_token_id=no_token_id
        )
```

---

## 5. Filter Implementation Strategy

**Recommendation**: We will place the filter logic in a new pure helper module `polymarket/shadow_telemetry.py`.
- **Rationale**: Isolating the logic inside `polymarket/shadow_telemetry.py` ensures that both runtime (`polymarket/trader.py`) and offline tests can import it safely without creating import cycles or requiring runtime modules to import from `tools/` (which are ignored in VPS deployments).
- The module will export `evaluate_shadow_filters(record: dict, active_filters: list[str]) -> list[dict]` returning a payload list of evaluations.

---

## 6. Payload Schema Specification

Each logged event payload under the `payload` key in the JSONL record will match the following exact fields:

```json
{
  "timestamp_utc": "2026-06-21T09:39:18.123456Z",
  "run_id": "20260621T093918Z_12345_abcde123",
  "signal_id": "cnd_014bf326_abcd",
  "candidate_instance_id": "cnd_014bf326_abcd",
  "paper_trade_replay_key": "pm-5m-btc-strike|1782012900|BTC|YES|0xabc...",
  "asset": "BTC",
  "market_slug": "btc-updown-5m",
  "side": "YES",
  "outcome": "YES",
  "edge": 0.045,
  "ev": 0.045,
  "probability": 0.545,
  "volatility_regime": "NORMAL_VOL",
  "trend_regime": "UP_TREND",
  "entry_price": 0.51,
  "proposed_size_usd": 10.0,
  "filter_name": "block_btc_shadow",
  "filter_version": "1.0.0",
  "filter_params": {
    "target_asset": "BTC"
  },
  "shadow_pass": false,
  "shadow_reason": "REJECT_BTC_ASSET",
  "would_trade": false,
  "schema_version": "1.0"
}
```

---

## 7. Fail-Soft Failure Behavior

To guarantee execution safety, the telemetry wrapper inside `polymarket/trader.py` will be protected by a fail-soft boundary:

```python
def _evaluate_passive_shadow_telemetry(self, ...):
    try:
        # evaluate and log shadow filters ...
    except Exception as e:
        LOGGER.error("[SHADOW] Fail-soft caught telemetry exception: %s", e, exc_info=True)
        # Bypasses error silently without raising, blocking trade, or modifying inventory state
```

---

## 8. Test Specifications

We will define target test coverage in `tests/test_shadow_filters.py`:
1. `test_feature_flag_default_off`: Verifies that telemetry does not execute or emit logs when settings `shadow_telemetry_enabled` is False.
2. `test_feature_flag_logs_when_on`: Verifies that logs are written correctly when the flag is enabled.
3. `test_fail_soft_resilience`: Mocks an exception during filter evaluation and asserts that order routing is completed successfully without interruption.
4. `test_no_order_or_sizing_mutation`: Asserts that the final trade order details (size, price, token side) remain identical whether shadow filters pass or fail.
5. `test_filter_parity`: Validates filter parity against the offline `tools/shadow_filter_evaluator.py` using synthetic test records.
6. `test_schema_completeness`: Asserts all required payload fields and schema versions are present in the emitted log events.

---

## 9. Verification & Validation Plan

Prior to committing, the following compilation and test verification pipeline must pass:
```bash
# Compilation check
py -3.11 -m py_compile config/settings.py polymarket/trader.py polymarket/shadow_telemetry.py

# Execute targeted tests
py -3.11 -m pytest tests/test_shadow_filters.py -q

# Code hygiene checks
git diff --check
```

---

## 10. Rollout Plan

- **Phase B0 (Implementation)**: Implement the telemetry code and tests. Roll out with the feature flag `shadow_telemetry_enabled` hardcoded to `False` by default.
- **Phase B1 (Silent Mode)**: Run on the VPS environment in paper trading mode with `SHADOW_TELEMETRY_ENABLED=false` to confirm zero baseline degradation or memory leaks.
- **Phase B2 (Active Telemetry)**: Manually enable the flag on paper runtime via `.env` (`SHADOW_TELEMETRY_ENABLED=true`). Observe and verify log generation quality for a 24-hour cycle.

---

## 11. Final Verdict

### Final Verdict: **`READY_FOR_SAFE_IMPLEMENTATION`**
