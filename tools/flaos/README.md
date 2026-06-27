# FLAOS Bootstrap Context Resolver

**Read-only offline tooling for the Full Loop Automation OS.**

---

## Usage

```bash
python tools/flaos/bootstrap.py           # compact JSON to stdout (default)
python tools/flaos/bootstrap.py --pretty  # pretty-printed JSON
python tools/flaos/bootstrap.py --diagnose # health checks and exit status
```

## What it does

1. Loads 7 operational JSON files from `docs/operations/`
2. Validates JSON structure, required schemas, and configuration integrity
3. Determines the next task from Active Workflow State
4. Selects the matching Agent Pipeline and Tool Pipeline
5. Selects skills (auto-prepends `quant_safety_review` for GATE/Class 2, 6, 7, 8 tasks)
6. Merges required tools, memory reads, and stop conditions
7. Prints a compact `ExecutionSnapshot` JSON to stdout

## Diagnose Mode

The `--diagnose` flag performs standard health checks across all operational files without outputting the full `ExecutionSnapshot`. It reports `HEALTHY` or `DEGRADED` (e.g. if the loop memory file is missing or invalid but the next task is a read-only task).

## Fail-Safe Stops

If any critical constraint is violated (e.g., missing required files, malformed JSON, state mismatch, or missing loop memory for write-active tasks), the resolver immediately prints a `STOP_AND_ESCALATE` JSON template and exits with exit code `1` (fail-safe).

```json
{
  "status": "STOP_AND_ESCALATE",
  "error_type": "...",
  "message": "...",
  "missing_or_invalid_file": "...",
  "safe_to_continue": false,
  "allowed_repair_scope": [ ... ],
  "recommended_repair_task": "FLAOS_BOOTSTRAP_REPAIR_001",
  "forbidden_actions": [ ... ]
}
```

## What it does NOT do

- No file writes (completely read-only)
- No state or queue mutation
- No git commits
- No paper mode execution
- No trading runtime dependency (zero imports from `polymarket/`)

## Output fields

| Field | Description |
|-------|-------------|
| `task_id` | Next task from active workflow state |
| `task_class` | Integer task class (0-9) |
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
| `final_output_format` | Format of output files |
| `last_loop_id` | Previous loop ID from loop memory |
| `last_loop_result` | Previous loop result |
| `current_phase` | Active workflow phase string |
| `source_files_loaded` | Paths of all files loaded by resolver |

## Required files

All under `docs/operations/`:

- `ACTIVE_WORKFLOW_STATE_001.json`
- `TASK_QUEUE_001.json`
- `AGENT_PIPELINE_001.json`
- `TOOL_PIPELINES_001.json`
- `TOOL_REGISTRY_001.json`
- `skills/SKILL_REGISTRY_001.json`
- `loop_memory/LOOP_MEMORY_20260627_001.json` (semi-critical)

## Dependencies

Python 3.10+ standard library only. No pip install required.

---

# FLAOS Runtime Session Manager

**Tooling script to coordinate and safe-guard paper runtime sessions.**

## Usage

```bash
python tools/flaos/runtime_session.py --help
```

### Subcommands

#### 1. create
Creates a session metadata JSON but does NOT launch runtime. Rejects live mode.
```bash
python tools/flaos/runtime_session.py create --task-id <task_id> --mode paper
```

#### 2. status
Queries the status of a specific session, confirming elapsed time and process health.
```bash
python tools/flaos/runtime_session.py status --session-id <session_id>
```

#### 3. detect
Returns a JSON-formatted list of active processes running `main.py --mode paper`.
```bash
python tools/flaos/runtime_session.py detect
```

#### 4. guard
Fails (returns exit code `1`) if an active paper runtime is already running.
```bash
python tools/flaos/runtime_session.py guard
```

#### 5. cleanup
Updates status of a session to `COMPLETED`, `TERMINATED`, or `UNKNOWN`. Pass `--terminate` to forcefully kill process trees.
```bash
python tools/flaos/runtime_session.py cleanup --session-id <session_id> [--terminate]
```

#### 6. launch
Asynchronously spawns a paper mode run with unique log filenames, after confirming the guard check passes.
```bash
python tools/flaos/runtime_session.py launch --task-id <task_id> --mode paper
```

## Session Directories
- **Log Files:** `runtime/validation/session_<session_id>_stdout.log` and `session_<session_id>_stderr.log`
- **Metadata Files:** `runtime/sessions/session_<session_id>.json`

