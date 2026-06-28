# QUERY-20260628-REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001

## Metadata

- Query timestamp: 2026-06-28T19:34:17+07:00
- Task: REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001
- Task class: 6 REFACTOR / ATOMIC TOOLS MIGRATION
- Graph files read:
  - docs/operations/knowledge_graph/REPO_GRAPH_NODES_001.jsonl
  - docs/operations/knowledge_graph/REPO_GRAPH_EDGES_001.jsonl
  - docs/operations/knowledge_graph/GRAPH_INDEX_001.json

## Query Results

| Query | Target | Status | Result |
|---|---|---|---|
| safety_check | REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001 | DEGRADED | TARGET_NOT_IN_GRAPH |
| blast_radius | REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001 | DEGRADED | TARGET_NOT_IN_GRAPH |
| evidence_for_commit | 288f8a3 | DEGRADED | COMMIT_NOT_IN_GRAPH |

## Fallback Evidence

The graph snapshot does not contain this repository organization task or the current AIROS design commit. Fallback source inspection was therefore required and completed before file moves.

### Import / Path Checks

Fallback command:

```powershell
rg -n "tools\.semantic_c_bounded_reload_replay|tools\.semantic_c_shadow_observability_report|tools\.cross_run_ev_blindness|tools\.shadow_filter_evaluator|from tools import shadow_filter_evaluator" -g "*.py"
```

Findings before move:

- `tests/test_cross_run_ev_blindness.py` imports `tools.cross_run_ev_blindness`.
- `tests/test_semantic_c_bounded_reload_replay.py` imports and dynamically imports `tools.semantic_c_bounded_reload_replay`.
- `tests/test_semantic_c_shadow_observability_report.py` imports and dynamically imports `tools.semantic_c_shadow_observability_report`.
- `tests/test_shadow_filter_evaluator.py` imports `tools.shadow_filter_evaluator`.
- `tests/test_joined_records_builder.py` imports `shadow_filter_evaluator` from `tools`.
- The moved module docstrings contain CLI examples using old module paths.

Fallback command:

```powershell
rg -n "semantic_c_bounded_reload_replay|semantic_c_shadow_observability_report|cross_run_ev_blindness|shadow_filter_evaluator" tools\multi_session_runner.py
```

Finding: no `multi_session_runner.py` REPLAY_STEPS references for the approved Phase 1F LOW_PATH_RISK quartet.

## Safety Findings

- No QS safety rule hit was present in the graph result.
- No runtime trading files are in the approved diff scope.
- No `polymarket/`, strategy, sizing, risk, execution, dashboard, Telegram, `.env`, builders, backtests, paper, or live runtime scope is authorized.

## Execution Contract Attachment

```json
{
  "graph_query_id": "QUERY-20260628-REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001",
  "graph_confidence": 0.0,
  "safety_findings_count": 0,
  "safety_findings": [],
  "affected_nodes_count": 0,
  "affected_edges_count": 0,
  "blast_radius_score": "LOW",
  "recommended_workflow_tier": "LOOP",
  "fallback_required": true,
  "status": "DEGRADED"
}
```

## Final Result

```json
{
  "$schema": "rkg_query_output_v1",
  "query_id": "QUERY-20260628-REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001",
  "query_type": "safety_check+blast_radius+evidence_for_commit",
  "target": "REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001",
  "status": "DEGRADED",
  "safety_findings": [],
  "affected_nodes": [],
  "affected_edges": [],
  "evidence": [
    {
      "type": "fallback_rg",
      "grade": "B",
      "description": "Targeted import/path checks found only planned test imports and docstring CLI examples; no multi_session_runner REPLAY_STEPS coupling."
    }
  ],
  "recommended_workflow_tier": "LOOP",
  "stop_conditions": [],
  "confidence": 0.0,
  "evidence_grade": "B",
  "execution_contract_attachment": {
    "graph_query_id": "QUERY-20260628-REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001",
    "graph_confidence": 0.0,
    "safety_findings_count": 0,
    "safety_findings": [],
    "affected_nodes_count": 0,
    "affected_edges_count": 0,
    "blast_radius_score": "LOW",
    "recommended_workflow_tier": "LOOP",
    "fallback_required": true,
    "status": "DEGRADED"
  }
}
```
