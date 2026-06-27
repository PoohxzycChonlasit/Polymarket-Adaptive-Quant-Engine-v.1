# REPOSITORY_GRAPH_ENGINE_001

**Date:** 2026-06-27 · **Destination:** `docs/architecture/` · **Status:** DESIGN v1

---

## 1. Objective

The Repository Graph Engine (RGE) models the repository as a directed graph of entities and relationships. It enables the Planning Engine to perform **impact analysis** — given a proposed change to a file or method, what else is affected? — replacing fragile grep-based call-site searches with structured dependency traversal.

---

## 2. Why File Index Is Not Enough

| Capability | File Index | Repository Graph |
|-----------|-----------|----------------|
| Lists files | ✓ | ✓ |
| Shows imports between files | ✗ | ✓ |
| Shows which tests cover a method | ✗ | ✓ |
| Shows call sites for a method | ✗ | ✓ |
| Identifies blast radius of a change | ✗ | ✓ |
| Detects permanent coupling (e.g. _phase4_) | ✗ | ✓ |
| Identifies orphaned methods | ✗ | ✓ |
| Tracks documentation coverage | ✗ | ✓ |

---

## 3. Graph Nodes

| Node type | Examples | Properties |
|-----------|---------|-----------|
| `file` | `polymarket/trader.py` | path, language, line_count, last_modified |
| `module` | `polymarket.trader` | fully_qualified_name, is_package |
| `class` | `PolymarketTrader` | file, line_start, method_count |
| `function` | `_mark_orderbook_refresh` | class, file, line, is_static, is_property, is_permanent |
| `test` | `test_paper_mode.py::test_cycle` | file, covers_methods, is_known_failure |
| `script` | `tools/replay_analyzer.py` | file, offline_only |
| `tool` | `py_compile_runtime` | tool_id from registry, grade, risk |
| `config` | `config/settings.py` | file, has_live_flags |
| `runtime_artifact` | `runtime/event_stream/*.jsonl` | type, retention_days |
| `report` | `docs/reports/BATCH_3C_*.md` | type, commit_sha |

---

## 4. Graph Edges

| Edge type | From | To | Properties |
|-----------|------|----|-----------|
| `imports` | module → module | `import_type: direct|star|conditional` |
| `calls` | function → function | `call_type: direct|indirect`, `line_numbers: [int]` |
| `tests` | test → function | `test_type: unit|integration`, `is_known_failure: bool` |
| `writes` | function → runtime_artifact | `write_type: append|overwrite` |
| `reads` | function → runtime_artifact | `read_type: stream|batch` |
| `owns` | class → function | `ownership: defined_in_class` |
| `documents` | report → function | `doc_type: design|audit|commit_report` |
| `validates` | tool → function | `validation_type: compile|test|runtime` |
| `is_permanent` | function → (special node) | `reason: execution_path|risk_coupled|blast_radius` |
| `moved_from` | function → file | `batch: "Batch 3B-1"`, `commit: "a491820"` |
| `proxied_by` | function → function | `proxy_type: method_proxy|property_shim` |

---

## 5. Graph Schema

```json
{
  "$schema": "repository_graph_v1",
  "generated_at": "ISO timestamp",
  "nodes": [
    {
      "node_id": "fn:polymarket.trader.PolymarketTrader._mark_orderbook_refresh",
      "node_type": "function",
      "name": "_mark_orderbook_refresh",
      "class": "PolymarketTrader",
      "file": "polymarket/trader.py",
      "is_permanent": false,
      "is_proxy": true,
      "proxy_target": "fn:polymarket.orchestration.trader_observability.TraderObservabilityHelper._mark_orderbook_refresh",
      "batch_extracted": "Batch 3B-1",
      "extraction_commit": "a491820"
    }
  ],
  "edges": [
    {
      "from": "fn:polymarket.trader.PolymarketTrader._mark_orderbook_refresh",
      "to": "fn:polymarket.orchestration.trader_observability.TraderObservabilityHelper._mark_orderbook_refresh",
      "edge_type": "proxied_by",
      "batch": "Batch 3B-1"
    }
  ]
}
```

---

## 6. Graph Generation Strategy

| Phase | Method | Trigger |
|-------|--------|---------|
| v1 | Manual: AI writes key nodes/edges based on gate check analysis | Per gate check |
| v2 | Semi-auto: Python script uses `ast` to parse trader.py and extract function nodes | After 30+ loop entries |
| v3 | Full AST: Parse all Python files in polymarket/ to build complete import + call graph | Phase 3 FLAOS |
| v4 | Incremental: Update graph on each commit using `git diff --name-only` | Phase 4 FLAOS |
| v5 | Validated: Cross-reference graph with test coverage to detect uncovered paths | Phase 5 FLAOS |

---

## 7. Graph Query Examples

| Query | Answer |
|-------|--------|
| "What tests cover `_phase2_candidate_hash`?" | Returns test nodes with `tests` edge to this function |
| "What methods in trader.py call `_phase2_value_available`?" | Returns function nodes with `calls` edge + line numbers |
| "What is the blast radius of moving `_scheduler_cadence_observability_detail`?" | Returns all functions with `calls` edge to it, their tests, and any permanent coupling |
| "Which methods are permanently forbidden from extraction?" | Returns all function nodes where `is_permanent = true` |
| "What was extracted in Batch 3B-2?" | Returns all function nodes where `batch_extracted = "Batch 3B-2"` |
| "What is the proxy chain for `_mark_orderbook_refresh`?" | Returns node → proxied_by chain to final implementation |

---

## 8. Impact Analysis Use Cases

### Gate Check Impact Analysis
Before Batch 3D gate check:
```
Query: get all functions in _phase2_complete_lifecycle_observability call tree
→ identify all functions it calls
→ for each: check is_permanent, check tests coverage
→ produce blast radius score
```

### Refactor Batch Validation
After implementing a batch:
```
Query: get all proxied_by edges created in this commit
→ verify each proxy target exists in helper
→ verify no calls from forbidden nodes (execution path)
```

### Drift Detection
On session start:
```
Query: compare expected graph nodes from last gate check against current grep results
→ if node moved unexpectedly → flag drift
```

---

## 9. Integration with Repository Intelligence Engine

The RIE reads the graph to produce the `RepositorySnapshot.trader_py_lines` and to detect if `is_permanent` methods are in scope. The graph is a first-class input to the `repository_snapshot_generator` tool (Phase 4).

---

## 10. Integration with Planning Engine

The Planning Engine queries the graph during `PLAN()`:
- `get_blast_radius(method_name)` → contributes to `complexity_score`
- `get_permanent_methods(scope)` → contributes to `risk_score` and `full_accept_override`
- `get_proxy_chain(method_name)` → informs call site count for complexity

---

## 11. Quant Safety Graph Constraints

The following graph constraints are hardcoded and override any query result:

| Constraint | Rule |
|-----------|------|
| Permanent methods | `is_permanent = true` nodes must NEVER appear as targets of `moved_from` edges |
| Execution path | Any method with `calls` edge to live order methods is execution-coupled |
| Risk coupling | Any method reading bankroll_tier or risk_mode nodes is risk-coupled |
| Data deletion guard | No graph edge may model deletion of `runtime_artifact` nodes |

These constraints are seeded from Quant Safety Memory (QS-001 through QS-010).

---

## 12. Migration Roadmap

| Phase | What ships | Trigger |
|-------|-----------|---------|
| v1 | This spec + manual seed entries for known permanent methods | NOW |
| v2 | `docs/operations/REPO_GRAPH_SEED_001.json`: hand-written nodes for Batch 3 extraction history | After Batch 3D gate |
| v3 | Python AST parser in tools/: generates nodes from trader.py | Phase 3 FLAOS |
| v4 | Full incremental graph with edge updates per commit | Phase 4 FLAOS |
| v5 | Graph-backed impact analysis integrated into Planning Engine | Phase 5 FLAOS |
