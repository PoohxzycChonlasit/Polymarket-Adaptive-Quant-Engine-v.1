# SCHEMA SLIMMING IMPLEMENTATION PLAN (SCHEMA_SLIMMING_IMPLEMENTATION_PLAN_001)

This implementation plan outlines the steps, testing matrix, and rollout procedures to safely remove redundant payload display data in `decision_log` and `research_log` files without breaking downstream analysis tools.

---

## 1. Display-Only Key Promotion Plan

To safely deprecate `payload.display`, the 33 keys present only inside `display` must first be promoted to the root of the `payload` dictionary. 

### Key Classifications & Promotion Mapping

| Rank | Display-Only Key | downstream Target | Root Payload Field | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `clob_consecutive_failures` | `replay_analyzer` | `payload["clob_consecutive_failures"]` | **Required** |
| 2 | `clob_last_error_category` | `replay_analyzer` | `payload["clob_last_error_category"]` | **Required** |
| 3 | `clob_last_error_class` | `replay_analyzer` | `payload["clob_last_error_class"]` | **Required** |
| 4 | `liquidity_ready` | `replay_analyzer` | `payload["liquidity_ready"]` | **Required** |
| 5 | `model_p_yes` | `replay/no_entry` | `payload["model_p_yes"]` | **Required** |
| 6 | `model_p_no` | `replay/no_entry` | `payload["model_p_no"]` | **Required** |
| 7 | `yes_orderbook_age_ms` | `replay_analyzer` | `payload["yes_orderbook_age_ms"]` | **Required** |
| 8 | `no_orderbook_age_ms` | `replay_analyzer` | `payload["no_orderbook_age_ms"]` | **Required** |
| 9 | `price_velocity` | `replay_analyzer` | `payload["price_velocity"]` | **Required** |
| 10 | `distance_from_ptb_pct` | `replay_analyzer` | `payload["distance_from_ptb_pct"]` | **Required** |
| 11 | `total_discovery_to_tradable_seconds`| `replay_analyzer` | `payload["total_discovery_to_tradable_seconds"]` | **Required** |
| 12 | `adaptive_cutoff_denied_reason`| `no_entry` | `payload["adaptive_cutoff_denied_reason"]` | **Required** |
| 13 | `score` | `replay_analyzer` | `payload["score"]` | **Required** |
| 14 | `delta_multiplier` | `replay_analyzer` | `payload["delta_multiplier"]` | **Required** |
| 15 | `ask_price` | General debug | `payload["ask_price"]` | Optional |
| 16 | `best_market` | General debug | `payload["best_market"]` | Optional |
| 17 | `best_side` | General debug | `payload["best_side"]` | Optional |
| 18 | `book_to_tradable_seconds` | General debug | `payload["book_to_tradable_seconds"]` | Optional |
| 19 | `depth_ready` | General debug | `payload["depth_ready"]` | Optional |
| 20 | `discovery_to_book_seconds` | General debug | `payload["discovery_to_book_seconds"]` | Optional |
| 21 | `epoch_end_ts` | General debug | `payload["epoch_end_ts"]` | Optional |
| 22 | `epoch_start_ts` | General debug | `payload["epoch_start_ts"]` | Optional |
| 23 | `final_size` | General debug | `payload["final_size"]` | Optional |
| 24 | `frequency_multiplier` | General debug | `payload["frequency_multiplier"]` | Optional |
| 25 | `last_successful_orderbook_age_ms`| General debug | `payload["last_successful_orderbook_age_ms"]` | Optional |
| 26 | `min_ev` | General debug | `payload["min_ev"]` | Optional |
| 27 | `mode` | General debug | `payload["mode"]` | Optional |
| 28 | `p_no` | General debug | `payload["p_no"]` | Optional |
| 29 | `p_yes` | General debug | `payload["p_yes"]` | Optional |
| 30 | `price_change_pct` | General debug | `payload["price_change_pct"]` | Optional |
| 31 | `realized_volatility` | General debug | `payload["realized_volatility"]` | Optional |
| 32 | `risk_plan_zero_diagnostics`| General debug | `payload["risk_plan_zero_diagnostics"]` | Optional |
| 33 | `delta_regime` | General debug | `payload["delta_regime"]` | Optional |

---

## 2. Backward Compatibility Strategy

To ensure zero downtime or analytical errors:
1. **Fallback Helpers remain Intact:** The helper functions (`_get_nested`, `_nested`) in `replay_analyzer.py` and `no_entry_analyzer.py` will continue checking root payload keys first before looking inside `display`.
2. **Old Log Parsing:** Old logs containing `payload.display` will parse correctly because fallback properties are successfully resolved when root keys are absent.
3. **New Log Parsing:** New logs without `display` will parse correctly because the keys are populated directly at the root.

---

## 3. Feature Flag Design

We will introduce a new configuration parameter in `config/settings.py` via Pydantic:

```python
# config/settings.py
class Settings(BaseSettings):
    # ...
    SLIM_DECISION_LOGGING: bool = False  # Defaults to false (safe baseline)
```

- **Runtime Logic:**
  ```python
  # polymarket/trader.py
  if settings.SLIM_DECISION_LOGGING:
      payload.pop("display", None)
  ```

---

## 4. Test Matrix & Validation Plan

Prior to merging the schema slimming patch, the following tests must pass under `tests/`:

1. **Unit Tests:**
   - Verify that all 33 promoted fields are present at the root payload level.
   - Verify that enabling `SLIM_DECISION_LOGGING` removes `display` but leaves root fields intact.
2. **Downstream Integration Tests:**
   - Execute `replay_analyzer.py` against a slim log file; assert that no `NoneType` errors occur.
   - Execute `no_entry_analyzer.py` against a slim log file; verify that cutoff metrics are extracted.
   - Parse mixed/concatenated logs containing both old records (with `display`) and new records (without `display`) through the analyzer pipeline; assert matching row counts.

---

## 5. Phased Rollout Stages

```text
Stage 0: Audit Completed -> Stage 1: Promote 33 Keys -> Stage 2: Feature Flag Patch -> Stage 3: Bounded Paper Run -> Stage 4: Parity Check -> Stage 5: Default Enabled
```

- **Stage 0 (Current):** Audit completed; keys mapped.
- **Stage 1 (Promotion):** Promote the 33 keys to the payload root inside `polymarket/trader.py` while keeping the `display` sub-dictionary (ensures absolute safety).
- **Stage 2 (Flag Integration):** Add `SLIM_DECISION_LOGGING` to config defaults.
- **Stage 3 (Validation Run):** Enable `SLIM_DECISION_LOGGING=true` during a 24-hour paper session.
- **Stage 4 (Parity Scan):** Run the `replay_analyzer` and `no_entry_analyzer` against the logs from Stage 3; verify that calculations match Stage 1 metrics exactly.
- **Stage 5 (Default Activation):** Change config default to `SLIM_DECISION_LOGGING = true`.

---

## 6. Estimated Footprint Savings

Based on our active decision logs:

- **Daily Reduction:** Reclaims **`470.8 MB/day`** (assuming ~1.08 GB generated daily, reduced by 44%).
- **Monthly (30 Days) Reduction:** Reclaims **`14.12 GB/month`**.
- **Yearly Reduction:** Reclaims **`171.8 GB/year`**.

---

## 7. Rollback Plan

If downstream issues are detected in Stage 3 or 4:
1. Set `SLIM_DECISION_LOGGING=false` in the `.env` file.
2. Restart the paper/live engine process.
3. The engine immediately resumes writing `payload.display`, restoring the baseline state. Downstream tools continue fallback parsing without data loss.

---

## 8. Final Verdict

The staged plan provides a safe, fully compatible path to roll out log slimming without disrupting historical audit tools.

> [!IMPORTANT]
> **VERDICT: READY_FOR_SCHEMA_SLIMMING_SAFE_PATCH**
