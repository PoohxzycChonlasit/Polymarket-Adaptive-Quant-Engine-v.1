# AI Repository Kernel Schema v1

## Purpose

This document defines the v1 schema contracts for AIROS registry files. These files are design targets only until a later implementation task creates them.

All registry files should be JSON, deterministic, UTF-8 without BOM, and generated from repository sources rather than hand-maintained when implementation begins.

## Common Envelope

Every registry should use this envelope:

```json
{
  "$schema": "airos_registry_v1",
  "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "repo_root": "C:/quant/Polymarket-Adaptive-Quant-Engine-v.1",
  "source_commit": "<git_sha>",
  "source_files": [],
  "records": []
}
```

## repository_index.json

Purpose: compact file inventory.

```json
{
  "$schema": "repository_index_v1",
  "records": [
    {
      "path": "tools/replay/runtime_event_replay.py",
      "kind": "python|markdown|json|directory",
      "owner_area": "tools.replay",
      "status": "active|historical|generated|experimental|unknown",
      "canonical_role": "offline replay utility",
      "do_not_touch_level": "normal|guarded|runtime_sensitive|live_sensitive",
      "primary_tests": ["tests/test_runtime_event_stream.py"],
      "active_docs": ["FILE_INDEX.md"],
      "historical_docs": ["docs/reports/..."],
      "last_seen_commit": "<git_sha>"
    }
  ]
}
```

## dependency_graph.json

Purpose: typed dependency and reference graph.

```json
{
  "$schema": "dependency_graph_v1",
  "nodes": [
    {
      "id": "file:tools/replay/runtime_event_replay.py",
      "path": "tools/replay/runtime_event_replay.py",
      "node_type": "file",
      "owner_area": "tools.replay"
    }
  ],
  "edges": [
    {
      "source": "file:tests/test_runtime_event_stream.py",
      "target": "file:tools/replay/runtime_event_replay.py",
      "edge_type": "imports|tested_by|mentions|cli_invokes|moved_to|owned_by_task",
      "evidence": "from tools.replay.runtime_event_replay import ...",
      "risk": "none|low|medium|high"
    }
  ]
}
```

## tool_registry.json

Purpose: AI-facing `tools/` map.

```json
{
  "$schema": "tool_registry_v1",
  "records": [
    {
      "tool_id": "runtime_event_replay",
      "current_path": "tools/replay/runtime_event_replay.py",
      "target_path": "tools/replay/runtime_event_replay.py",
      "category": "replay",
      "cli_entrypoint": true,
      "module_path": "tools.replay.runtime_event_replay",
      "import_risk": "NO_IMPORT_RISK|LOW_PATH_RISK|MEDIUM_IMPORT_RISK|HIGH_RUNTIME_RISK",
      "direct_tests": ["tests/test_runtime_event_stream.py"],
      "docs_references": [],
      "ops_references": [],
      "migration_phase": "phase_1c",
      "move_status": "not_started|planned|moved|deferred",
      "validation_commands": []
    }
  ]
}
```

## test_registry.json

Purpose: targeted validation map.

```json
{
  "$schema": "test_registry_v1",
  "records": [
    {
      "test_path": "tests/test_runtime_event_stream.py",
      "covers": ["tools/replay/runtime_event_replay.py"],
      "command": ".venv\\Scripts\\python.exe -m pytest tests\\test_runtime_event_stream.py -q",
      "resource_class": "light|medium|heavy",
      "full_pytest_required": false,
      "known_preexisting_failures": [],
      "last_verified_commit": "<git_sha>"
    }
  ]
}
```

## command_registry.json

Purpose: approved command catalog.

```json
{
  "$schema": "command_registry_v1",
  "records": [
    {
      "command_id": "json_tool_active_workflow",
      "command": ".venv\\Scripts\\python.exe -m json.tool docs\\operations\\ACTIVE_WORKFLOW_STATE_001.json",
      "resource_class": "light|medium|heavy|live_risk",
      "allowed_task_classes": [2, 3, 4, 5, 6],
      "approval_required": false,
      "forbidden_contexts": [],
      "expected_output": "exit 0"
    }
  ]
}
```

## agent_capability_registry.json

Purpose: role capability and boundary map.

```json
{
  "$schema": "agent_capability_registry_v1",
  "records": [
    {
      "role_id": "24",
      "role_name": "REPOSITORY_LIBRARIAN_AGENT",
      "allowed_task_classes": [2, 3, 6],
      "default_read_set": ["FILE_INDEX.md", "DOCUMENTATION_MAP.md"],
      "forbidden_scopes": ["polymarket/", "utils/", "config/", ".env"],
      "validation_duties": ["docs routing", "root cleanliness", "reference consistency"],
      "escalation_triggers": ["root markdown drift", "unknown dirty tree"]
    }
  ]
}
```

## task_template_registry.json

Purpose: machine-readable task template list.

```json
{
  "$schema": "task_template_registry_v1",
  "records": [
    {
      "template_id": "atomic_repository_move",
      "task_class": 6,
      "default_allowed_scope": ["source path", "target path", "targeted tests", "docs/reports/", "docs/operations/"],
      "required_preflight": ["git status --short", "git branch -vv"],
      "required_validation": ["rg old refs", "py_compile", "targeted pytest", "json.tool ops", "git diff --check"],
      "forbidden_actions": ["full pytest", "builders", "backtests", "runtime"]
    }
  ]
}
```

## ai_context_cache.json

Purpose: compact current AI startup packet.

```json
{
  "$schema": "ai_context_cache_v1",
  "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "source_commit": "<git_sha>",
  "current_task": "TASK_ID",
  "next_task": "TASK_ID",
  "active_loop_memory_file": "docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json",
  "active_question_status": "OPEN|CLOSED|N/A",
  "repo_phase": "tools_phase_1f",
  "do_not_touch": ["polymarket/", "utils/", "config/", ".env"],
  "recent_commits": []
}
```

## repo_health.json

Purpose: fast answer to "can the next task start?"

```json
{
  "$schema": "repo_health_v1",
  "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "source_commit": "<git_sha>",
  "worktree_status": "clean|dirty",
  "dirty_tree_classification": "CLEAN|DIRTY_PREVIOUS_TASK_OUTPUTS|DIRTY_OPERATOR_WORK|DIRTY_UNKNOWN",
  "branch_status": "up_to_date|ahead|behind|diverged",
  "active_loop_memory_file": "docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json",
  "active_loop_memory_valid": true,
  "ops_json_valid": true,
  "boundary_state": "COMMITTED|CLEAN_NO_CHANGES|BLOCKED_NEEDS_OPERATOR_DECISION",
  "next_task_can_start": true,
  "required_commit_task": null
}
```
