# QUERY-20260628-REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001

## Metadata

- Query timestamp: 2026-06-28T20:05:56+07:00
- Task: REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001
- Task class: 6 REFACTOR / ATOMIC TOOLS MIGRATION
- Graph files read:
  - docs/operations/knowledge_graph/REPO_GRAPH_NODES_001.jsonl
  - docs/operations/knowledge_graph/REPO_GRAPH_EDGES_001.jsonl
  - docs/operations/knowledge_graph/GRAPH_INDEX_001.json

## Query Results

| Query | Target | Status | Result |
|---|---|---|---|
| safety_check | REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001 | DEGRADED | TARGET_NOT_IN_GRAPH |
| blast_radius | REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001 | DEGRADED | TARGET_NOT_IN_GRAPH |
| evidence_for_commit | 1241d15 | DEGRADED | COMMIT_NOT_IN_GRAPH |

## Fallback Evidence

The graph snapshot does not include this newly authorized repository organization task or the latest Phase 1F commit. Fallback source inspection was required and completed before file moves.

### Remaining Candidate Inventory

Root-level shadow/cross-run candidates after Phase 1F:

- `tools/semantic_c_shadow_fill_replay.py`
- `tools/semantic_c_shadow_pnl_truth.py`
- `tools/semantic_c_inventory_continuity_replay.py`
- `tools/cross_run_lifecycle_truth.py`

Already moved and not candidates:

- `tools/shadow/semantic_c_bounded_reload_replay.py`
- `tools/shadow/semantic_c_shadow_observability_report.py`
- `tools/shadow/cross_run_ev_blindness.py`
- `tools/shadow/shadow_filter_evaluator.py`

### Dependency Findings

Fallback command:

```powershell
rg -n "tools\.semantic_c_shadow_fill_replay|tools\.semantic_c_shadow_pnl_truth|tools\.semantic_c_inventory_continuity_replay|tools\.cross_run_lifecycle_truth|from tools import cross_run_lifecycle_truth|import tools\.cross_run_lifecycle_truth" -g "*.py"
```

Findings:

- The three `semantic_c_*` replay-step tools are referenced by their targeted tests and `tools/multi_session_runner.py` module strings.
- `tools/cross_run_lifecycle_truth.py` is imported by `tools/lifecycle_truth_backfill.py` and `tests/test_cross_run_lifecycle_truth.py`.
- No `polymarket/` runtime Python import was found for the semantic replay-step tools.

Fallback command:

```powershell
rg -n "semantic_c_shadow_fill_replay|semantic_c_shadow_pnl_truth|semantic_c_inventory_continuity_replay|cross_run_lifecycle_truth" tools\multi_session_runner.py tests tools -g "*.py"
```

Findings:

- `tools/multi_session_runner.py` has REPLAY_STEPS module strings for the three semantic replay-step tools, so it must be updated atomically with the move.
- `cross_run_lifecycle_truth.py` has cross-tool coupling through `tools/lifecycle_truth_backfill.py`; it is deferred from this atomic batch.

## Selected Move Set

Move:

- `tools/semantic_c_shadow_fill_replay.py` -> `tools/shadow/semantic_c_shadow_fill_replay.py`
- `tools/semantic_c_shadow_pnl_truth.py` -> `tools/shadow/semantic_c_shadow_pnl_truth.py`
- `tools/semantic_c_inventory_continuity_replay.py` -> `tools/shadow/semantic_c_inventory_continuity_replay.py`

Update:

- `tools/multi_session_runner.py`
- `tests/test_semantic_c_shadow_fill_replay.py`
- `tests/test_semantic_c_shadow_pnl_truth.py`
- `tests/test_semantic_c_inventory_continuity_replay.py`
- `tests/test_multi_session_runner.py`

Defer:

- `tools/cross_run_lifecycle_truth.py` because it is imported by another root tool and should be moved with `tools/lifecycle_truth_backfill.py` in a separately planned batch.

## Safety Findings

- No QS safety rule hit was present in the graph result.
- No runtime trading files are in the approved diff scope.
- No `polymarket/`, strategy, sizing, risk, execution, dashboard, Telegram, `.env`, builders, backtests, paper, or live runtime scope is authorized.

## Execution Contract Attachment

```json
{
  "graph_query_id": "QUERY-20260628-REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001",
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
  "query_id": "QUERY-20260628-REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001",
  "query_type": "safety_check+blast_radius+evidence_for_commit",
  "target": "REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001",
  "status": "DEGRADED",
  "safety_findings": [],
  "affected_nodes": [],
  "affected_edges": [],
  "evidence": [
    {
      "type": "fallback_rg",
      "grade": "B",
      "description": "Targeted import/path checks identified a safe semantic replay-step move set and deferred cross_run_lifecycle_truth due cross-tool import coupling."
    }
  ],
  "recommended_workflow_tier": "LOOP",
  "stop_conditions": [],
  "confidence": 0.0,
  "evidence_grade": "B",
  "execution_contract_attachment": {
    "graph_query_id": "QUERY-20260628-REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001",
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
