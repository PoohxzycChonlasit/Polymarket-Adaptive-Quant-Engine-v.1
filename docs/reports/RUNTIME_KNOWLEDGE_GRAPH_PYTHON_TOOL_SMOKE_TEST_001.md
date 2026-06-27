# RUNTIME_KNOWLEDGE_GRAPH_PYTHON_TOOL_SMOKE_TEST_001

Mode: LOOP_RUNTIME_ENGINE_V1

Task class: 0 HEALTH_CHECK / TOOL_SMOKE_TEST

Workflow tier: LOOP

## Bootstrap Results

| Check | Expected | Observed | Result |
| --- | --- | --- | --- |
| `bootstrap.py --diagnose` status | `HEALTHY` | `HEALTHY` | PASS |
| `bootstrap.py --pretty` task | `RUNTIME_KNOWLEDGE_GRAPH_PYTHON_TOOL_SMOKE_TEST_001` | `RUNTIME_KNOWLEDGE_GRAPH_PYTHON_TOOL_SMOKE_TEST_001` | PASS |
| workflow tier | `LOOP` | `LOOP` | PASS |
| `memory_os_v2_enabled` | `true` | `true` | PASS |
| `safety_memory_loaded` | `true` | `true` | PASS |

## Command Result Table

| Command | Return code | JSON parse | Schema | Key validation | Result |
| --- | ---: | --- | --- | --- | --- |
| `knowledge_graph.py graph-health` | 0 | PASS | `$schema=rkg_health_v1` | `status=DEGRADED` | PASS with known limitation |
| `knowledge_graph.py safety-check _last_quote_lineage_context` | 0 | PASS | `$schema=rkg_query_output_v1` | `STOP_REQUIRED`, includes `QS-003` | PASS |
| `knowledge_graph.py why-deferred BATCH_3D_GATE_CHECK_001` | 0 | PASS | `$schema=rkg_query_output_v1` | Missing `PAUSE_BATCH_3D_DEFER`; `deferred_methods=[]` | FAIL |
| `knowledge_graph.py evidence-for-commit 3c5b781` | 0 | PASS | `$schema=rkg_query_output_v1` | Includes Batch 3C evidence and `POST_BATCH_3C` runtime validation | PASS |
| `knowledge_graph.py blast-radius TraderObservabilityHelper` | 0 | PASS | `$schema=rkg_query_output_v1` | Includes `TraderObservabilityHelper` target, affected runtime evidence nodes | PASS |

Raw command outputs and validation booleans were saved to:

```text
docs/operations/graph_queries/RKG_PYTHON_TOOL_SMOKE_TEST_OUTPUTS_001.json
```

## Expected vs Observed

| Requirement | Expected | Observed | Result |
| --- | --- | --- | --- |
| All command outputs parse as JSON | Yes | Yes | PASS |
| Query schemas | `rkg_query_output_v1` | 4 query outputs use `$schema=rkg_query_output_v1`; `graph-health` uses `$schema=rkg_health_v1` | PASS for query outputs |
| Safety check target status | `STOP_REQUIRED` | `STOP_REQUIRED` | PASS |
| Safety check includes `QS-003` | Yes | Yes | PASS |
| `why-deferred` includes `PAUSE_BATCH_3D_DEFER` | Yes | No | FAIL |
| `why-deferred` returns deferred methods for required unprefixed command | Expected from manual template | `[]` | FAIL |
| `evidence-for-commit` includes Batch 3C evidence | Yes | Yes | PASS |
| `blast-radius` includes `TraderObservabilityHelper` affected/runtime evidence | Yes | Yes | PASS |
| Graph health DEGRADED understood as known seed limitation | Yes | DEGRADED due graph-health integrity limitations | PASS with caveat |

## Schema Validation

The Python tool emits the schema field as `$schema`, not `schema`.

Observed schemas:

| Output | `$schema` |
| --- | --- |
| `graph-health` | `rkg_health_v1` |
| `safety-check` | `rkg_query_output_v1` |
| `why-deferred` | `rkg_query_output_v1` |
| `evidence-for-commit` | `rkg_query_output_v1` |
| `blast-radius` | `rkg_query_output_v1` |

The four query outputs satisfy the expected `rkg_query_output_v1` schema. `graph-health` has a separate health schema.

## Graph Health Note

`graph-health` returned `DEGRADED`.

This is consistent with the known seed limitation from unresolved/orphaned placeholder edges:

- `orphaned_edges = 4`
- `graph_health_checks.all_edge_nodes_resolve = false`
- `graph_health_checks.qs_001_to_010_all_present = true`

This health degradation did not block the query smoke test by itself.

## Manual Template Comparison

The manual query template smoke test expected:

- `why_deferred("BATCH_3D_GATE_CHECK_001")`
- `PAUSE_BATCH_3D_DEFER`
- two deferred methods
- affected audit/task lineage

The Python tool required command returned:

```json
{
  "target": "BATCH_3D_GATE_CHECK_001",
  "affected_nodes": ["audit:BATCH_3D_GATE_CHECK_001"],
  "deferred_methods": []
}
```

Supplemental read-only diagnostic:

```text
.venv\Scripts\python.exe tools/flaos/knowledge_graph.py why-deferred task:BATCH_3D_GATE_CHECK_001
```

This prefixed task target returned the two deferred methods, but still did not include `PAUSE_BATCH_3D_DEFER` evidence in the required output shape. The required unprefixed command remains the decision-bearing smoke-test result.

## Execution Contract Readiness

Execution Contract ready: NO

Reason:

- 3 of 4 decision-bearing queries passed.
- `why-deferred BATCH_3D_GATE_CHECK_001` did not match the manual template expectation.
- State/queue/memory PASS updates were not applied because the task explicitly conditions them on 4 passing queries.

## State / Queue / Memory

No state update was performed.

Reason:

The pass condition was not met:

```text
queries_passed = 3
required = 4
```

Therefore these were intentionally left unchanged:

- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- `docs/operations/loop_memory/LOOP_MEMORY_20260627_001.json`

## Next Recommendation

Recommended next task:

```text
RUNTIME_KNOWLEDGE_GRAPH_WHY_DEFERRED_QUERY_PARITY_FIX_001
```

Purpose:

- Make the Python `why-deferred BATCH_3D_GATE_CHECK_001` command match the manual query template smoke-test expectation.
- Preserve exact unprefixed command behavior required by the execution contract.
- Include `PAUSE_BATCH_3D_DEFER` and deferred method lineage in the standard `rkg_query_output_v1` output.

## Final Verdict

RUNTIME_KNOWLEDGE_GRAPH_PYTHON_TOOL_SMOKE_TEST_FAIL
