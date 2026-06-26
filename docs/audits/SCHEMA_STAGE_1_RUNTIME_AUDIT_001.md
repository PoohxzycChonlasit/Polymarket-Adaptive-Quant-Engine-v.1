# SCHEMA_STAGE_1_RUNTIME_AUDIT_001

**Verdict: PASS**

## 1. Objective and Scope
The goal of this audit (`SCHEMA_STAGE_1_RUNTIME_AUDIT_001`) is to validate the Stage 1 key promotion patch in live emitted runtime logs. This stage copies 33 display-only fields from the nested `payload.display` block directly into the root level of the decision log payload.

We audited:
- `runtime/quant_data/decision_log/`
- `runtime/quant_data/research_log/`

## 2. Sample Details
We sampled the 100 most recent records emitted to `runtime/quant_data/decision_log/2026-06-22.jsonl` following the Stage 1 patch commit.

- **Sample Size:** 100 records
- **Total Keys Monitored:** 33 keys
- **Total Checked Key Instances:** 3,026 key-level instances (where key existed inside `payload.display`)

## 3. Metrics Summary
We evaluated the occurrence and consistency of all 33 promoted keys at the payload root:

| Metric | Count | Rate (%) |
|--------|-------|----------|
| **Promotion Success Rate** | 3,026 / 3,026 | 100.00% |
| **Missing Key Rate** | 0 / 3,026 | 0.00% |
| **Mismatch Rate** | 0 / 3,026 | 0.00% |

- **Verification checks:**
  - `payload.display` exists in all sampled lines: **YES**
  - All promoted keys exist at payload root when present in `display`: **YES**
  - Root value is exactly equal to display value: **YES**

The 33 promoted keys checked are:
1. `adaptive_cutoff_denied_reason`
2. `ask_price`
3. `best_market`
4. `best_side`
5. `book_to_tradable_seconds`
6. `clob_consecutive_failures`
7. `clob_last_error_category`
8. `clob_last_error_class`
9. `delta_multiplier`
10. `delta_regime`
11. `depth_ready`
12. `discovery_to_book_seconds`
13. `distance_from_ptb_pct`
14. `epoch_end_ts`
15. `epoch_start_ts`
16. `final_size`
17. `frequency_multiplier`
18. `last_successful_orderbook_age_ms`
19. `liquidity_ready`
20. `min_ev`
21. `mode`
22. `model_p_no`
23. `model_p_yes`
24. `no_orderbook_age_ms`
25. `p_no`
26. `p_yes`
27. `price_change_pct`
28. `price_velocity`
29. `realized_volatility`
30. `risk_plan_zero_diagnostics`
31. `score`
32. `total_discovery_to_tradable_seconds`
33. `yes_orderbook_age_ms`

## 4. Downstream Systems Verification
We executed the three main downstream analyzers against the post-patch log files to verify compatibility and correct parsing:

1. **`replay_analyzer.py`**:
   - Status: **PASSED**
   - Details: Correctly processed 3,184 events (including the post-patch records) without syntax/logic errors or unhandled exceptions. Emitted 0 bad_json records.
2. **`no_entry_analyzer.py`**:
   - Status: **PASSED**
   - Details: Evaluated 442 decision events with 0 bad_json entries. Correctly categorized skip reasons, delta indicators, and orderbook readiness messages.
3. **`phase_b_weekly_review_engine.py`**:
   - Status: **PASSED**
   - Details: Parsed logs and compiled weekly reviews. Outputted reports to `scratch/phase_b_weekly_review/` successfully.

## 5. Storage Savings Estimation
We measured the JSON string footprint reduction on the 100 sampled lines if we delete the nested `payload.display` dictionary (preserving the root payload):

- **Original Sample Size:** 3,338,391 bytes (3.18 MB)
- **Slimmed Sample Size:** 1,974,490 bytes (1.88 MB)
- **Estimated Size Reduction:** **40.86%**

Once Stage 2 removes `display`, the decision log footprint is expected to shrink by **~41%**, resulting in significant disk savings without loss of machine-readable fields.
