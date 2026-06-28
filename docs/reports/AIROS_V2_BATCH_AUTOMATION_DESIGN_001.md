# AIROS_V2_BATCH_AUTOMATION_DESIGN_001

## 1. Why v2 Batch Automation is Needed

Manual file-by-file dependency graphing and batch creation in AIROS v1 is time-consuming and prone to errors. To complete large-scale repository reorganizations efficiently, we need a programmatic scanning, scoring, clustering, and compilation engine.

---

## 2. What Automation Adds over v1

* **AST Parsing Scanner:** Replaces manual text search with Abstract Syntax Tree import analysis.
* **Connected Component Clustering:** Automatically clusters files to minimize cross-batch dependency violations.
* **Command Compilation:** Translates clusters directly into git moves, rewrite rules, and compile/test verification pipelines.
* **Context Caching:** Minimizes workspace scans, saving token context and increasing execution speed.

---

## 3. Files Created

* `docs/architecture/AI_REPOSITORY_OPERATING_SYSTEM_V2_BATCH_AUTOMATION_001.md` — Core V2 architecture.
* `docs/operations/AIROS_V2_REGISTRY_ARTIFACTS_001.md` — Index and registry specifications.
* `docs/operations/AIROS_V2_BATCH_GENERATOR_SPEC_001.md` — Clustering algorithm and batching rules.
* `docs/operations/AIROS_V2_MIGRATION_COMPILER_SPEC_001.md` — Command and rollback compilation rules.

---

## 4. Safety Boundaries

* **Core Runtime Lock:** Any batch containing core files (`polymarket/`, `config/`, `.env`) is blocked.
* **Risk/Sizing Core Lock:** Modules linked to trade risk paths are locked and marked `DO_NOT_MOVE`.
* **Max Size Limits:** Maximum 12 files or 1,500 lines changed per batch.

---

## 5. Expected Speedup

By automating the scanning, planning, command compilation, and contract creation, the time to prepare a batch is reduced from **20-30 minutes to under 1 minute**, enabling rapid execution cycles.

---

## 6. Next Implementation Task

The next task is **`AIROS_V2_SCANNER_INDEXER_IMPLEMENTATION_001`** (Class 7 Feature), which will implement the Phase 1 AST scanner and dependency graph builder.
