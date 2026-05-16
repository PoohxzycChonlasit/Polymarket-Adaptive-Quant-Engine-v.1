# Replay Policy Naming Drift

> Scope: research/validation metadata only.
> This document does not change runtime behavior, strategy, risk, or execution.

---

## What Happened

The validation runner extracted `policy_B.realized_proxy_pnl` from `lifecycle_profit_management_replay` reports. This produced:

```
policy_b_rank: 5   (last)
policy_b_pnl:  $62.25
```

despite the fixed SR<60 derisk policy actually ranking **#1 at $67.67**.

The root cause: `lifecycle_profit_management_replay` uses its own internal letter assignments, where the SR<60 derisk is labeled `policy_D`, not `policy_B`. The literal `policy_B` key in that tool maps to a completely different strategy ("reduce-50% at 2x entry price").

---

## The Drift Table

| Concept | Research alias | lifecycle_profit_mgmt key | Other tool keys |
|---|---|---|---|
| Fixed SR<60 derisk | **Policy B** | **policy_D** ← drift | policy_B (consistent) |
| Hold to settlement | Policy A | policy_A | policy_A (consistent) |
| Reduce 50% at 2x | *(no alias)* | policy_B ← misleading | *(not used elsewhere)* |

---

## Why Replay Tools May Have Local Naming Autonomy

Each offline replay tool is self-contained by design (no shared runtime imports, no cross-tool code sharing). This allows tools to be developed, tested, and audited independently without coupling to a shared naming contract.

The tradeoff: when a validation runner aggregates results across tools using literal field keys (`policy_B`), naming mismatches propagate silently into aggregate metrics.

This is not a bug in any individual tool — each tool's local labeling is internally consistent. The drift only becomes visible when an aggregation layer assumes a shared naming convention that does not exist.

---

## Why Canonical Identity Matters

**Without canonical identity:**
- `policy_b_rank_1_count: 0` across sessions → appears to confirm "Policy B never wins"
- In reality, the SR<60 derisk policy ranked #1 at $67.67 — the research conclusion is correct, but the metric is wrong
- Future AI agents reading the manifest may conclude SR<60 derisk is a weak policy

**With canonical identity:**
- `canonical_sr60_rank_1_count: 1` correctly reflects that SR<60 derisk ranked #1
- Metrics are grounded in semantic meaning, not tool-local letter assignments
- The research vocabulary ("Policy B = SR<60 derisk") remains consistent with the validation evidence

---

## Solution: Canonical Policy Registry

`research/replay_policy_registry.json` defines a `canonical_policy_id` → `tool_key` mapping for each replay tool. The validation runner loads this registry and resolves canonical metrics alongside the literal `policy_B` fields (which are preserved for backward compatibility).

**New canonical fields added to validation manifests:**

| Field | Meaning |
|---|---|
| `canonical_sr60_derisk_rank` | Rank of the SR<60 derisk policy in lifecycle_pm (reads policy_D) |
| `canonical_sr60_derisk_pnl` | PnL of the SR<60 derisk policy |
| `canonical_policy_id` | `"fixed_sr60_derisk"` |
| `canonical_naming_drift_resolved` | `true` when drift was detected and corrected |
| `canonical_sr60_rank_1_count` | Aggregate: sessions where SR<60 derisk ranked #1 |
| `canonical_sr60_rank_values` | Aggregate: per-session SR<60 rank list |

**Backward compatible:** Old `policy_b_rank`, `policy_b_pnl`, `policy_b_rank_1_count` fields remain unchanged.

---

## What Changes Nothing

- No runtime files modified
- No strategy, risk, sizing, or execution behavior changed
- No JSONL evidence modified
- No trading constraints relaxed
- The registry is read-only metadata consumed by the offline validation runner

---

## Registry Location

`research/replay_policy_registry.json`

This is the single source of truth for policy semantic mappings. Update it when new replay tools are added or existing tools change their policy letter assignments.
