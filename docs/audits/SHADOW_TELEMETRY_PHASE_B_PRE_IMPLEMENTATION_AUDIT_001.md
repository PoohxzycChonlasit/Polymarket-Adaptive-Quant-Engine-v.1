# SHADOW_TELEMETRY_PHASE_B_PRE_IMPLEMENTATION_AUDIT_001

* **Date:** 2026-06-21
* **Target Workspace:** `c:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
* **Status:** **`AUDIT COMPLETE / IMPLEMENTATION GATE PASS`**
* **Primary Role:** `08_RESEARCH_QUANT_AGENT` (Quant Research & Design Audit)
* **Supporting Roles:** `10_BACKTEST_REPLAY_AGENT` (Backtest Replay & Lifecycle Analytics)

---

## 1. Signal Identity & Lifecycle Join Stability

To accurately measure the performance of passive shadow filters, we must trace each opportunity from the initial decision scan (`signal_filter_shadow`) through the entry fill (`log_trade_open`) to the final exit fill (`log_trade_close`).

### Join Feasibility Analysis:
- **`run_id`**: Identifies a specific paper runtime session. Stable across all logs in a single runtime instance.
- **`signal_id`**: Maps to `candidate_trace_id` (a hash generated based on candidate features). This is highly stable, but can collision-risk if multiple scans of the same market ticker occur within the same epoch.
- **`candidate_id` / `candidate_instance_id`**: A unique UUID generated per candidate instance in the scan. Extremely stable and guarantees zero collisions.

### Canonical Join Key Recommendation:
We recommend the compound key **`(run_id, candidate_instance_id)`** as the primary canonical join key.
- **Why**: It uniquely identifies a single scan instance across the entire lifecycle, eliminating collision risks in cases where multiple signal updates are processed for a single strike epoch.
- **Fallback Verification Key**: We recommend logging **`paper_trade_replay_key`** (`condition_id` | `epoch_start_ts` | `ticker` | `side` | `token_id`) as a secondary validator key to ensure join robustness in offline replays.

---

## 2. Shadow PnL Attribution Schema Audit

The baseline schema defined in `SHADOW_TELEMETRY_PHASE_B_DESIGN_001.md` is logged at the **moment of entry scan**, before the trade outcomes (fills, exit prices, and PnL) are realized. 

### Attribution Gaps & Solutions:
To accurately calculate would-be performance metrics without complex, stateful log joins, we recommend:
1. **Carrying Attributions to Trade Closes**: Modify the position metadata model so that when a trade close event (`log_trade_close`) is emitted, the shadow pass/fail flags and the active filter versions are copied directly from the entry candidate into the close record.
2. **Additional Fields for Sizing Replay**: Reconstructing dollar-weighted PnL requires tracking the proposed trade size and side at entry.

### Recommended Schema Extensions:
We recommend adding the following fields to the `signal_filter_shadow` log payload:
- **`side`** (`"YES"` or `"NO"`): Crucial for direction attribution.
- **`entry_price`** (float): The strike/token price at scan time.
- **`proposed_size_usd`** (float): The calculated target size before any baseline execution filters.

### Performance Formulation:
- **`would_trade_count`**: Count of closed positions where `shadow_pass == True`.
- **`would_block_count`**: Count of closed positions where `shadow_pass == False`.
- **`shadow_net_pnl`**: Sum of realized PnL from closed positions where `shadow_pass == True`.
- **`rejected_net_pnl`**: Sum of realized PnL from closed positions where `shadow_pass == False` (representing saved losses or missed gains).

---

## 3. Filter Versioning & Parameters Evolution Schema

To allow filters to evolve (e.g. changing thresholds or rules) without corrupting historical datasets, we design a clean versioning contract.

### Filter Versioning Contract:
- **`filter_name`**: The canonical filter name (e.g. `block_edge_lt_005_shadow`).
- **`filter_version`**: A SemVer version string (e.g., `1.0.0`) mapped to the code release.
- **`filter_params`**: A key-value dictionary containing the actual thresholds used during evaluation, providing self-documenting telemetry.

### Example Versioned Payload:
```json
{
  "filter_name": "combined_conservative_shadow",
  "filter_version": "1.0.0",
  "filter_params": {
    "asset_whitelist": ["ETH"],
    "min_edge": 0.05,
    "max_edge": 0.15
  }
}
```

If the minimum edge threshold is shifted in a future release to `0.06`, the `filter_version` must be incremented to `1.1.0`.

---

## 4. Safety & Operational Recommendation

- **VCS & Runtime Integrity**: **`CONFIRMED`** (No codebase files were modified or staged during this pre-implementation audit. The audit remains strictly offline).
- **Implementation Readiness**: **`APPROVED`**. The design is stable, and the canonical join keys and schema extensions resolve all downstream telemetry aggregation requirements.
