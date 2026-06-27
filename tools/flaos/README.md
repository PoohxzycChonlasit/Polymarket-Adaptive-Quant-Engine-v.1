# FLAOS Bootstrap Context Resolver

**Read-only offline tooling for the Full Loop Automation OS.**

---

## Usage

```bash
python tools/flaos/bootstrap.py           # compact JSON to stdout
python tools/flaos/bootstrap.py --pretty  # pretty-printed JSON
```

## What it does

1. Loads 6 operational JSON files from `docs/operations/`
2. Determines the next task from Active Workflow State
3. Selects the matching Agent Pipeline and Tool Pipeline
4. Selects skills (auto-prepends `quant_safety_review` for GATE/Class 6-8 tasks)
5. Merges required tools, memory reads, and stop conditions
6. Prints a compact `ExecutionSnapshot` JSON to stdout

## What it does NOT do

- No file writes
- No state or queue mutation
- No git commits
- No paper mode execution
- No trading runtime dependency (zero imports from `polymarket/`)

## Output fields

| Field | Description |
|-------|-------------|
| `task_id` | Next task from active workflow state |
| `workflow_tier` | FAST, LOOP, STANDARD, or GATE |
| `agent_pipeline_id` | Matched pipeline from AGENT_PIPELINE_001.json |
| `role_sequence` | Ordered agent roles for this pipeline |
| `tool_pipeline_id` | Matched pipeline from TOOL_PIPELINES_001.json |
| `skills` | Selected skill IDs (quant_safety_review prepended if applicable) |
| `required_tools` | Merged tool list from skills + tool pipeline |
| `required_memory_reads` | Memory types to load before execution |
| `required_evidence` | Minimum evidence grade (D/C/B/A) |
| `max_repairs` | Max repair attempts from tool pipeline |
| `full_accept_allowed` | False if any skill blocks auto-accept |
| `stop_conditions` | Merged stop conditions from all sources |
| `commit_policy` | Commit type constraint |
| `allowed_scope` | Files/dirs the task may modify |

## Required files

All under `docs/operations/`:

- `ACTIVE_WORKFLOW_STATE_001.json`
- `TASK_QUEUE_001.json`
- `AGENT_PIPELINE_001.json`
- `TOOL_PIPELINES_001.json`
- `skills/SKILL_REGISTRY_001.json`
- `loop_memory/LOOP_MEMORY_20260627_001.json`

## Dependencies

Python 3.10+ standard library only. No pip install required.
