# STOP_LOSS_SHADOW_COMPARATOR_PLAN_001

## 1. Role Routing Block

- **Primary Role**: `10_BACKTEST_REPLAY_AGENT.md` (owns offline replay, candidate lifecycle, and offline evaluator validation).
- **Supporting Roles**:
  - `11_OBSERVABILITY_INCIDENT_AGENT.md` (owns event schemas, logs, and telemetry).
  - `22_INVENTORY_ANALYTICS_AGENT.md` (owns offline inventory replay metrics).
- **Why Selected**: Designing an offline comparator tool to process event logs and reconstruct counterfactual trade histories is a core backtest/replay analytics concern.
- **Files Inspected**:
  - `tools/paper_evaluation_report.py`
  - `tools/replay_analyzer.py`
  - `utils/quant_event_logger.py`
- **Files Intentionally Ignored**: Sizing models, entry filters, and live wallet configurations.

---

## 2. Tool Purpose

The offline comparator tool, `tools/stop_loss_shadow_comparator.py`, is designed to analyze paper trading sessions. It compares the actual raw-bid stop behavior against five alternative shadow policies to measure:
*   How often raw best bids cause premature or false stop-outs.
*   The trade-saving rate and false stop-out reduction of each shadow policy.
*   The estimated counterfactual PnL gains (or losses) from adopting each alternative policy.
*   Whether shadow policies are overly passive (failing to stop real losses).

---

## 3. Schema & Join Rules

### Input Schema
1.  **Shadow Logs (`stop_loss_shadow/*.jsonl`)**:
    - `position_id` (str)
    - `raw_bid`, `raw_ask`, `midpoint`, `bid_size`, `ask_size` (floats)
    - `unrealized_raw_bid_pct`, `unrealized_mid_pct`, `unrealized_mid_depth_pct` (floats)
    - `consecutive_raw_breach_count`, `consecutive_mid_breach_count` (ints)
    - `actual_raw_bid_stop`, `shadow_mid_stop`, `shadow_mid_depth_stop`, `shadow_raw_2sample_stop`, `shadow_raw_3sample_stop`, `shadow_mid_3sample_stop` (booleans)
2.  **Trade Journal (`trade_journal/*.jsonl`)**:
    - `event_type`: `"trade_open"` (gives `entry_price`, `side`, `ticker`)
    - `event_type`: `"trade_close"` (gives `exit_price`, `reason`, `pnl`, `exit_timestamp`)

### Join Rules
1.  Join shadow tick records with trade journal entries using **`position_id`** as the primary hash key.
2.  Optionally verify **`run_id`** and **`paper_trade_replay_key`** to validate data consistency.
3.  Sort shadow ticks chronologically to trace the state progression of each position.

---

## 4. Metrics Computed

For each policy, the tool will calculate:
*   `event_count`: Total tick checks.
*   `unique_positions`: Distinct positions evaluated.
*   `trigger_count`: Total times the stop condition was met.
*   `actual_stop_overlap`: Number of positions stopped by both this policy and the actual stop.
*   `saved_actual_stops`: Positions stopped by actual raw-bid but *not* by this policy.
*   `false_stop_reduction_rate`: `saved_actual_stops / total_actual_stops`.
*   `positions_recovered_after_actual_stop`: Saved positions that expired in favor of the trade (outcome = 1.0).
*   `positions_not_recovered_after_actual_stop`: Saved positions that expired out-of-the-money (outcome = 0.0).
*   `estimated_counterfactual_pnl`: Realized PnL plus the theoretical change (saved trades resolving at expiry price, or true stops exiting at the policy's trigger price).
*   `positions_with_missing_followup`: Saved trades with no closed record or resolution price due to premature session shutdowns.

---

## 5. Output Schemas

1.  **Terminal Console Output (Default)**: Prints a clean ASCII-formatted table of metrics.
2.  **JSON Output (`runtime/reports/stop_loss_shadow_comparator_v1.json`)**:
    ```json
    {
      "date_range": "2026-06-16_to_2026-06-16",
      "generated_at_utc": "2026-06-16T03:22:10Z",
      "policies": {
        "shadow_mid_stop": {
          "trigger_count": 0,
          "saved_actual_stops": 1,
          "false_stop_reduction_rate": 1.0,
          "estimated_counterfactual_pnl_diff": 0.035
        }
      }
    }
    ```
3.  **Markdown Report (`runtime/reports/stop_loss_shadow_comparator_v1.md`)**: Contains descriptive summaries and Markdown tables.
4.  **CSV Export (`runtime/research_exports/stop_loss_shadow_events_v1.csv`)**: Contains joined row-by-row trade records with actual vs. shadow PnLs.

No files are written unless the corresponding CLI flags are enabled.

---

## 6. CLI Design

```bash
# Analyze a single day
python tools/stop_loss_shadow_comparator.py --date YYYY-MM-DD

# Analyze a range of dates
python tools/stop_loss_shadow_comparator.py --from YYYY-MM-DD --to YYYY-MM-DD

# Write reports
python tools/stop_loss_shadow_comparator.py --date 2026-06-16 --write-json --write-md --write-csv
```

---

## 7. Test Plan

Unit tests in `tests/test_stop_loss_shadow_comparator.py` will prove:
1.  **Parsing Safety**: Gracefully reads malformed JSONL files or empty directories.
2.  **Hash Joining**: Accurately matches shadow ticks to trade journal items by `position_id`.
3.  **Logical Flags**: Correctly classifies saved trades when `actual_raw_bid_stop = true` but `shadow_mid_stop = false`.
4.  **Math Correctness**: Checks calculations for `false_stop_reduction_rate` and `estimated_counterfactual_pnl`.
5.  **Missing Close Handling**: Identifies and flags positions that lack a corresponding trade close.
6.  **Flag Isolation**: Asserts that no file writes occur if write flags are omitted.
7.  **No Trading Imports**: Verifies that the tool imports no trader/client modules, ensuring it operates purely offline.

---

## 8. Risks & Mitigations

-   **Memory Overhead**: Reading long files of raw tick data could saturate memory.
    *   *Mitigation*: Stream events line-by-line using generators, filtering out non-essential keys early in the pipeline.
-   **Incomplete Trade Resolution**: Trades saved in shadow mode may lack resolution outcomes if the bot was stopped before expiry.
    *   *Mitigation*: Exclude positions flagged with `positions_with_missing_followup` from counterfactual PnL metrics to avoid skewing stats.

---

## 9. Recommended Design Options

Under Exit Agent guidelines, we present exactly three future options:

### Option 1 — SAFE EV PRESERVATION (Implement the comparator tool) (Recommended)
- **Description**: Implement `tools/stop_loss_shadow_comparator.py` as designed. This is offline, safe, and allows processing paper session logs to produce policy validation reports.
- **Risk**: Extremely low. Offline only.

### Option 2 — AGGRESSIVE INFORMATION DISCOVERY (Backtest simulator integration)
- **Description**: Build the policies into `polymarket/backtester_5m.py` directly to simulate shadow stop performance on historical datasets.
- **Risk**: Low, but requires major modifications to the backtesting engine.

### Option 3 — STRUCTURAL / ROOT-CAUSE PATH (Telegram Alert daily digest integration)
- **Description**: Instead of a separate tool, integrate shadow calculations directly into `daily_report.py` and the daily Telegram summary.
- **Risk**: Low, but complicates Telegram alert formatting.

---

## 10. Final Recommendation

**IMPLEMENT_COMPARATOR_TOOL**

*Rationale*: We have validated that the shadow logging is operational. Having an offline diagnostic tool is the standard, safest, and most thorough method to validate counterfactual pricing models using the collected evidence.

---

## 11. Final Confirmation

Runtime changed: No
Strategy changed: No
EV changed: No
Risk changed: No
Execution changed: No
Live trading changed: No
Files modified: 0
