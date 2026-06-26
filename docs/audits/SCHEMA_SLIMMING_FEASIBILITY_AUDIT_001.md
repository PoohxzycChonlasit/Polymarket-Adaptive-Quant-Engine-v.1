# SCHEMA SLIMMING FEASIBILITY AUDIT (SCHEMA_SLIMMING_FEASIBILITY_AUDIT_001)

This audit determines the safety, downstream impact, and implementation requirements of pruning redundant log fields inside `decision_log` and `research_log`.

---

## 1. Downstream Dependency Scan & Code Usages

We scanned the codebase recursively to locate references to the nested `display` field in downstream systems (including replay analyzers, dashboards, pipelines, and reviews).

### Key Discovery: Fallback Mechanics
Downstream analysis tools use helper functions like `_get_nested` or `_nested` to parse values. These helpers check the root `payload` first, falling back to `display.<key>` second:
- **`tools/no_entry_analyzer.py`:**
  - `_first_present(payload.get("entry_cutoff_seconds"), _nested(payload, "display.entry_cutoff_seconds"))`
  - `_nested(payload, "display.time_bucket")`
- **`tools/replay_analyzer.py`:**
  - `_get_nested(payload, "clob_error_category", "display.clob_error_category")`
  - `_get_nested(payload, "seconds_remaining", "display.seconds_remaining")`
- **`tools/session_runtime_evaluator.py`:**
  - Validates presence of `volatility_regime` and `trend_regime` at payload root or `payload.display`.

### The 33 Display-Only Keys
While **281 keys** overlap exactly between payload root and `display`, **33 keys** exist *only* inside `display`. If `payload.display` is removed without changes, the downstream system will fail to extract these fields, returning `None`.

**Critical fields that must be promoted to the root of `payload` before removing `display`:**
- Model probabilities: `model_p_yes`, `model_p_no`, `p_yes`, `model_p_yes`
- Performance scores: `score`, `delta_multiplier`
- Price metrics: `price_velocity`, `distance_from_ptb_pct`
- CLOB diagnostic stats: `clob_consecutive_failures`, `yes_orderbook_age_ms`

---

## 2. Decision Log Breakdown

Storage footprint breakdown per record (average size: `29.86 KB`):

| Component / Layer | Average Size (KB) | Size Share (%) | Action |
| :--- | :---: | :---: | :--- |
| **Metadata Headers** | 0.20 KB | 0.7% | **KEEP** (Required for routing/indexing). |
| **`payload` Root Keys** | 16.34 KB | 54.7% | **SLIM** (Retain machine features; promote 33 keys). |
| **`payload.display`** | 13.32 KB | 44.6% | **REMOVE** (Redundant console rendering variables). |

- **Rebuild Feasibility:** Yes, `display` can be rebuilt dynamically from root payload fields at render-time (in console printers or dashboard servers) instead of being serialized to disk.

---

## 3. Research Log: Snapshot vs Delta Protocol

To eliminate repeated full-state dumps (~150+ fields, up to 17 KB) on every cycle transition, we design the following protocol:

```text
Discovery Event (FULL)
  └── payload: { all 150+ variables }

Model Call Event (DELTA)
  └── payload: { event_subtype: delta_update, changed_fields: { probability: 0.65 } }

Risk Checked Event (DELTA)
  └── payload: { event_subtype: delta_update, changed_fields: { risk_budget_used: 0.12 } }
```

### Protocol Schema
1. **FULL_SNAPSHOT (`event_subtype: full_snapshot`):** Emitted once per cycle at discovery. Logs all initialization fields.
2. **DELTA_UPDATE (`event_subtype: delta_update`):** Emitted on milestones. Logs only changed fields under `changed_fields`.

### Minimal Research Fields to Preserve
- `ticker`, `condition_id`, `yes_bid`, `yes_ask`, `true_probability`, `regime_reason`, `score`.

---

## 4. Projected Storage Savings

Accumulated storage reductions under schema slimming:

| Interval | Current Growth (GB) | Slimmed Growth (GB) | Space Reclaimed (GB) | Savings (%) |
| :--- | :---: | :---: | :---: | :---: |
| **30 Days** | 25.43 GB | **3.81 GB** | **21.62 GB** | **85.0%** |
| **90 Days** | 76.29 GB | **11.44 GB** | **64.85 GB** | **85.0%** |
| **1 Year** | 309.40 GB | **46.41 GB** | **262.99 GB** | **85.0%** |

---

## 5. Migration Risk Assessment

- **Risk Level:** **`MEDIUM`**
- **Justification:**
  - Although the logging change is straightforward, the 33 display-only keys represent a silent-failure risk if deleted.
  - Downstream analyzers will compile without errors but yield wrong calculations (e.g. `price_velocity` or `model_p_yes` returning `None` instead of throwing exceptions).
- **Mitigation Path:** The implementation must run in tandem with unit tests verifying that all `display` keys accessed by `replay_analyzer` exist at the payload root.

---

## 6. Final Verdict

Schema slimming is safe and highly recommended, provided the 33 display-only keys are promoted first.

> [!IMPORTANT]
> **VERDICT: SAFE_FOR_SCHEMA_SLIMMING**
