# AIROS_V2_REGISTRY_ARTIFACTS_001

**Status:** ACTIVE  
**Date:** 2026-06-28  
**Purpose:** Registry definitions, schemas, and governance rules for AIROS v2 generated artifacts.

---

## 1. Expected Generated Artifacts

### 1.1 `docs/operations/repository/repository_index.json`
* **Schema Intent:** Flat index of all repository files with paths, sizes, line counts, hashes, and AST metadata flags (e.g., imports runtime, executes CLI).
* **Producer:** Repository Scanner & Index Generator.
* **Consumer:** Dependency Graph Builder, Blast Radius Engine.
* **Refresh Cadence:** At task startup and after every commit.
* **Validation Command:** `python -m json.tool docs/operations/repository/repository_index.json`
* **Failure Mode:** Empty or partial scans (e.g., directory permission errors). Action: Regenerate with force flag.

### 1.2 `docs/operations/repository/dependency_graph.json`
* **Schema Intent:** Directed graph mapping files to their imports (outbound) and importers (inbound).
* **Producer:** Dependency Graph Generator.
* **Consumer:** Blast Radius Engine, Batch Generator.
* **Refresh Cadence:** Automatically regenerated after index refresh.
* **Validation Command:** Verification that all internal imports resolve to files in `repository_index.json`.
* **Failure Mode:** Unresolved imports or missing local paths. Action: Mark references as unknown and flag for manual audit.

### 1.3 `docs/operations/repository/tool_registry.json`
* **Schema Intent:** Catalog of all utility, diagnostic, and research tools, categorized by domain (e.g., audit, replay, shadow).
* **Producer:** AIROS v2 Indexer.
* **Consumer:** AI Agents looking for target tools.
* **Refresh Cadence:** Weekly or post-migration.
* **Validation Command:** Check that all tool paths exist in `repository_index.json`.
* **Failure Mode:** Broken path references. Action: Run indexer to rebuild paths.

### 1.4 `docs/operations/repository/test_registry.json`
* **Schema Intent:** Mappings of tools and runtime modules to their corresponding test suites.
* **Producer:** Dependency Graph Generator (analyzing imports in test files).
* **Consumer:** Validation Planner.
* **Refresh Cadence:** Post-migration.
* **Validation Command:** Check that all test files map to a valid source tool/module.
* **Failure Mode:** Orphaned tests. Action: Flag tests for deprecation or rewrite.

### 1.5 `docs/operations/repository/command_registry.json`
* **Schema Intent:** Registry of safe CLI commands, parameters, and expected logs/outputs.
* **Producer:** AST docstring analyzer.
* **Consumer:** Execution Planner, Validation Planner.
* **Refresh Cadence:** Post-refactor.
* **Validation Command:** Match regex patterns against command strings.
* **Failure Mode:** Outdated commands. Action: Update command definitions based on code signatures.

### 1.6 `docs/operations/repository/ownership_registry.json`
* **Schema Intent:** Maps components (e.g., execution, risk, strategy) to primary AI roles and ownership classes.
* **Producer:** Code Architect Agent.
* **Consumer:** Master Agent Router.
* **Refresh Cadence:** Ad-hoc when folder boundaries change.
* **Validation Command:** Check file path patterns coverage.
* **Failure Mode:** Untracked/orphaned files. Action: Classify as `unknown_needs_review`.

### 1.7 `docs/operations/repository/batch_candidates.json`
* **Schema Intent:** Optimal batch groupings of files eligible for migration, sorted by risk category.
* **Producer:** Batch Generator.
* **Consumer:** Migration Compiler, Codebase Developer AI.
* **Refresh Cadence:** Post-commit.
* **Validation Command:** Check that no candidate overlaps with `DO_NOT_MOVE` boundaries.
* **Failure Mode:** Overlap with forbidden files. Action: Immediately purge candidate from list and alert operator.

### 1.8 `docs/operations/repository/repo_health.json`
* **Schema Intent:** Current system metrics (ahead/behind counts, dirty status, active loop memory file, active task id).
* **Producer:** Repository Health Check engine.
* **Consumer:** AI Bootstrapper.
* **Refresh Cadence:** Before any task execution.
* **Validation Command:** Verification of state pointers.
* **Failure Mode:** Divergence from git CLI output. Action: Reject task execution and trigger health checklist.
