# POST_MAINTENANCE_STRATEGY_REVIEW_001

**Date:** 2026-06-27 · **Tier:** GATE Class 2 · **Repairs:** 0

---

## 1. Context After Phase A Maintenance

**Phase A complete:** `logs/` 1.6 GB → 219 MB (1,411.7 MB reclaimed, 856 files deleted, 0 failures). JSONL, trading runtime, test suite all intact. Bootstrap HEALTHY.

**Loop memory state:** 33 entries in `LOOP_MEMORY_20260627_001.json` (930 lines, single daily JSON array).

**Task queue:** 24 entries, 303 lines, growing.

**Active question:** `LOW_PRICE_TRUTH_RESOLUTION_001` OPEN — blocks strategy/sizer/execution changes; does NOT block tooling, docs, structural refactors.

---

## 2. Option Analysis

### A. Resume Batch 3D — `_phase2_complete_lifecycle_observability` + `_phase2_observability_payload`

**Gate verdict (BATCH_3D_GATE_CHECK_001):** `PAUSE_BATCH_3D_DEFER`

| Method | Safe extraction score | Coupling |
|--------|----------------------|---------|
| `_phase2_complete_lifecycle_observability` | **5/10** | MEDIUM — reads many trader state fields, calls `_diagnostic_int/_float` (permanent) |
| `_phase2_observability_payload` | **3/10** | HIGH — assembles full observability payload, 200+ lines, maximum state reads |

The gate explicitly recommended keeping these as "controller-level orchestration logic" in trader.py. This recommendation stands — the maintenance sprint did not change the risk profile.

**Smaller Batch 3D-A alternative:** Some phase2 utility methods (`_phase2_lifecycle_phase`, `_phase2_book_state_level`, `_phase2_safe_setting`) have safer extraction profiles (~7/10). These could be a scaled-down Batch 3D-A. But the primary payoff (200–400 lines from trader.py) requires the large methods — and those are still deferred.

**Verdict:** Not the primary next task. Batch 3D in full scope remains deferred per gate.

---

### B. Memory OS V2 Design — `MEMORY_OS_V2_DESIGN_001`

**Problem statement:**

| Current | Problem | Threshold |
|---------|---------|-----------|
| 33 loop memory entries in one daily JSON | Single array, no index, no query support | Manageable now; will be ~1,000 entries in 6 months |
| Memory files: one `.json` per day | No typed separation (decision / failure / repair / quant_safety) | AI must read all entries to find relevant context |
| ACME design (`AI_COGNITION_MEMORY_ENGINE_001.md`) is v1 spec only | Not operational — just a schema document | Need JSONL records + index file |
| Loop memory entries average 30–40 lines each | 33 entries × 35 lines = 1,155 lines to scan per session | Session startup cost grows linearly |

**What Memory OS V2 would deliver:**
1. JSONL-based memory records (one record per line, grep-able, appendable)
2. Per-category files: `decision_memory.jsonl`, `failure_memory.jsonl`, `quant_safety_memory.jsonl`, etc.
3. Index file: `MEMORY_INDEX.json` — compact, keyed by task_id and loop_id — loaded in ~50 tokens
4. Session startup reads index only, loads specific records on demand
5. Quant safety memory: permanent, never compacted, grep-first

**Why now:**
- This is pure docs/tooling work (no trading code changes, not blocked by active question)
- Memory infrastructure directly improves AI session quality — each session has better context in fewer tokens
- Prevents the "read 33 entries to find 3 relevant ones" problem from getting worse
- The Planning Engine design depends on memory being queryable

**Risk:** NONE for trading code. Docs/JSON work only.

**Evidence Grade required:** D (docs/schema design) or B (if tools/flaos tool created).

---

### C. Execution Engine Design — `EXECUTION_ENGINE_DESIGN_001`

**Problem:** `LOW_PRICE_TRUTH_RESOLUTION_001` is OPEN and blocks execution path analysis. Even designing execution changes requires resolving the active question first — the question affects how execution decisions should be made.

**Verdict:** DEFERRED until active question resolved.

---

### D. Repository Graph Runtime — `REPOSITORY_GRAPH_RUNTIME_001`

**Problem:** The graph design (`REPOSITORY_GRAPH_ENGINE_001.md`) exists but has no operational implementation. Building the graph requires storing graph facts somewhere — which requires Memory OS V2 first (quant_safety entries in the graph need the quant_safety memory layer).

**Verdict:** SECONDARY after Memory OS V2. The seed graph (`REPO_GRAPH_SEED_001.json`) can be created as part of Memory OS V2 work.

---

### E. Pause for Quant Truth

`LOW_PRICE_TRUTH_RESOLUTION_001` does NOT block Memory OS V2, FLAOS tooling, structural refactors (non-execution). No reason to pause.

**Verdict:** Do not pause.

---

## 3. Recommendation

**Primary: `MEMORY_OS_V2_DESIGN_001`** — GATE tier Class 2

Design v2 Memory OS with:
- JSONL-based typed record files per memory category
- `MEMORY_INDEX.json` for O(1) session startup lookup
- Migration path from daily JSON array to JSONL records
- Tool: `tools/flaos/memory_os.py` — read/write/query memory records
- Quant safety memory: pre-seeded with QS-001 through QS-010 as JSONL records

This is the highest-value next step: pure docs/tooling, no risk, directly improves every future AI session, unblocked by active question.

**Secondary: `BATCH_3D_MINI_GATE_001`** — Investigate whether the 6 smaller phase2 utility methods (`_phase2_lifecycle_phase`, `_phase2_book_state_level`, `_phase2_safe_setting`, `_phase2_candidate_survival_ms`, `_phase2_iso_from_epoch` already moved, `_phase2_phase_offsets` already moved) could form a safe Batch 3D-A with extraction scores ≥ 7/10. Much lower risk than the deferred payload assembly methods.

---

## 4. Implementation Sequence

```
1. MEMORY_OS_V2_DESIGN_001       GATE  Class 2  → Architecture + schema design
2. MEMORY_OS_V2_IMPLEMENTATION   LOOP  Class 4  → tools/flaos/memory_os.py + JSONL records
3. MEMORY_MIGRATION_001          LOOP  Class 3  → Migrate loop_memory JSON → JSONL
4. BATCH_3D_MINI_GATE_001        GATE  Class 2  → Smaller phase2 utility scope (optional, parallel)
5. EXECUTION_ENGINE_DESIGN_001   GATE  Class 2  → After active question resolved
```

---

## 5. Final Verdict

```
RECOMMENDATION: MEMORY_OS_V2_DESIGN_001
SECONDARY:      BATCH_3D_MINI_GATE_001 (parallel-eligible)
DEFERRED:       Full Batch 3D (payload assembly methods — gate said DEFER)
DEFERRED:       Execution Engine Design (blocked by active question)
```
