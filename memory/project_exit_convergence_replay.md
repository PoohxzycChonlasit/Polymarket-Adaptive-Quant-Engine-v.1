---
name: project-exit-convergence-replay
description: Exit Convergence Intelligence Replay v1 — offline replay tool added for studying YES book convergence toward settlement
metadata:
  type: project
---

Exit Convergence Intelligence Replay v1 added as offline-only research tool.

**Why:** Lifecycle Profit Management Replay showed Policy D (fixed SR<60 derisk) was best (proxy PnL $67.67, uplift +$5.22). Policy E (decay heuristics) had 21 false triggers. Task: test whether YES book convergence signals can improve on static SR<60.

**Files created:**
- `tools/exit_convergence_intelligence_replay.py`
- `tests/test_exit_convergence_intelligence_replay.py`

**Policies:**
- A: baseline hold-to-settlement
- B: fixed_derisk_sr60 (mirrors Lifecycle PM Policy D)
- C: dynamic_convergence_exit_95 (proxy proximity — RESEARCH: uses settlement proxy = future knowledge)
- D: dynamic_convergence_exit_volatility (vol collapse, backward-looking only)
- E: hybrid_convergence_derisk (SR guard + convergence confirmation)

**New metrics beyond prior replay tools:**
- `convergence_false_positive_cost_usd`: sum of max(0, premature_regret) for false convergence exits
- `late_uncertainty_expansion_count`: count of epochs where late-window vol > early-window vol

**Key constraints:** `_CONV_PROXY_BAND = 0.05` (absolute, not relative), `_CONV_PERSIST_N = 3`, Policy D needs 4 constant snapshots to reach streak=3 (first snap gives vol=inf). All convergence exits are full closes (reduce_fraction=1.0).

**Commit:** 7a69afb — 86 tests, all passing.

**How to apply:** This is Phase 2 replay research only. Output is evidence only. Do not wire into runtime without a separately scoped Phase 3 implementation.
