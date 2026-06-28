# AI Repository Operating System v1

## Objective

AI Repository Operating System v1 (AIROS v1) is the shared navigation and governance kernel for Claude, Gemini, Codex, ChatGPT, and future AI agents working in this quant repository.

AIROS does not change runtime behavior. It gives agents a compact way to find the current task, active memory, repository maps, tool locations, tests, commands, and safety boundaries without repeatedly rediscovering the repository through broad searches.

## Non-Goals

- Do not alter trading strategy, sizing, risk, execution, dashboard, Telegram, `.env`, or paper/live behavior.
- Do not implement scripts in v1 design.
- Do not move files as part of this design.
- Do not replace `AGENTS.md`, `PROJECT_RULES.md`, or active task governance; AIROS indexes and routes them.

## Architecture Layers

| Layer | Purpose | Primary docs |
|---|---|---|
| Repository Kernel | Defines canonical registries, health state, and AI startup contract. | `docs/operations/AI_REPOSITORY_KERNEL_SCHEMA_001.md` |
| Repository Index | Compact inventory of source, docs, tools, tests, runtime evidence folders, and ownership. | Future `repository_index.json` |
| Dependency Graph | File and module relationship map for imports, command calls, docs references, and task ownership. | Future `dependency_graph.json` |
| Tool Registry | Tool path, category, CLI form, import risk, target folder, tests, and migration state. | Future `tool_registry.json` |
| Test Registry | Test files, covered modules, safe targeted commands, and no-full-pytest defaults. | Future `test_registry.json` |
| Command Registry | Approved commands, resource class, safety flags, and forbidden contexts. | Future `command_registry.json` |
| Task Template Registry | Standard task templates for repeatable AI workflows. | `docs/operations/AI_TASK_TEMPLATE_LIBRARY_001.md` |
| Agent Capability Registry | Which agent roles can read, write, validate, or stop each task class. | Future `agent_capability_registry.json` |
| Context Cache | Precomputed compact summaries for startup, current refactor phase, active blockers, and recent commits. | Future `ai_context_cache.json` |
| Health Dashboard | Current git, dirty tree, active loop memory, remote sync, resource, and safety health. | Future `repo_health.json` |

## Repository Kernel

The Repository Kernel is the authoritative AI-facing contract for repository navigation. It is not an executable runtime. In v1 it defines:

- Where each registry lives.
- Which docs are read first.
- How the active task and active loop memory are discovered.
- Which generated artifacts may be trusted as current versus historical.
- What validations must pass before implementation, commit, or push.
- Which areas are hard do-not-touch zones unless explicitly scoped.

Kernel source of truth:

- `docs/operations/AI_REPO_BOOTSTRAP_001.md`
- `docs/operations/AI_REPOSITORY_KERNEL_SCHEMA_001.md`
- `docs/operations/AI_TASK_TEMPLATE_LIBRARY_001.md`
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- the active loop memory file pointed to by `ACTIVE_WORKFLOW_STATE_001.json`

## Repository Index

The Repository Index will be a generated JSON file that compresses the navigation data currently spread across `FILE_INDEX.md`, `DOCUMENTATION_MAP.md`, `TOOLS_STRUCTURE_TARGET_001.md`, task reports, and the filesystem.

Minimum v1 fields:

- `path`
- `kind`
- `owner_area`
- `status`
- `canonical_role`
- `do_not_touch_level`
- `primary_tests`
- `active_docs`
- `historical_docs`
- `last_seen_commit`

The index must distinguish active operational docs from historical reports. Agents must not infer active runtime behavior from historical reports.

## Dependency Graph

The Dependency Graph maps how files relate. It should include:

- Python imports.
- Test imports.
- CLI command references.
- Docs references.
- Task queue references.
- Runtime ownership.
- Refactor/move history.

Graph edges should be typed, for example:

- `imports`
- `tested_by`
- `mentions_command`
- `moved_to`
- `owned_by_task`
- `forbidden_for_task_class`

The graph is used for blast-radius checks and migration planning. It does not authorize code changes by itself.

## Tool Registry

The Tool Registry is the AI-facing contract for `tools/` navigation. It should build on `TOOLS_STRUCTURE_TARGET_001.md` and track:

- current path
- target path
- category
- CLI entrypoint status
- import risk
- direct tests
- docs references
- ops references
- active migration phase
- move status
- validation command

It should support the repository reorganization phases without requiring repeated `rg` inventory scans.

## Test Registry

The Test Registry maps changed areas to safe targeted tests. It should include:

- test file
- covered modules
- command
- expected resource class
- whether full pytest is required
- whether builder/backtest is forbidden
- known pre-existing failures

Default rule: targeted tests first. Full pytest requires explicit operator approval unless a task explicitly scopes it.

## Command Registry

The Command Registry defines commands agents may run and their resource/safety class:

- `git status --short`
- `git branch -vv`
- `python -m json.tool`
- `python -m py_compile`
- targeted pytest
- builder commands
- backtest commands
- paper runtime commands
- live runtime commands

Each command should record:

- resource class: light, medium, heavy, live-risk
- approval required
- allowed task classes
- forbidden contexts
- expected output artifact

## Task Template Registry

The Task Template Registry standardizes recurring task shapes. v1 templates are defined in `docs/operations/AI_TASK_TEMPLATE_LIBRARY_001.md`:

- Atomic repository move
- Docs/governance task
- Class 6 low-risk refactor
- Design-only architecture task
- Runtime validation task
- Replay/backtest task
- Paper session report
- Commit-boundary repair
- Dirty tree classification

## Agent Capability Registry

The Agent Capability Registry maps roles to task classes, read scopes, write scopes, stop conditions, and validation expectations.

It complements `MASTER_AGENT_ROUTER.md`; it does not replace the role docs.

Minimum fields:

- role id
- role name
- allowed task classes
- default read set
- forbidden scopes
- validation duties
- escalation triggers

## Context Cache

The Context Cache stores short AI-readable summaries that are cheaper than rereading large docs:

- current task and next task
- active loop memory pointer
- current tools migration phase
- current dirty-tree boundary state
- active strategy/research blocker
- recent commits
- known no-touch zones

The cache must be regenerated from source docs and registries. If cache conflicts with `ACTIVE_WORKFLOW_STATE_001.json`, the active workflow file wins.

## Health Dashboard

The Health Dashboard is a compact repository health snapshot:

- worktree status
- branch ahead/behind
- active loop memory pointer validity
- ops JSON validity
- resource governance state
- active task boundary state
- last commit and push status
- high-risk dirty file classification

It should make "can the next task start?" answerable without broad searches.

## Loop Memory Integration

AIROS must never hardcode loop memory filenames. Agents must read:

```text
docs/operations/ACTIVE_WORKFLOW_STATE_001.json
```

and use:

```text
workflow_governance.active_loop_memory_file
```

If the pointer is missing, agents must stop with `LOOP_MEMORY_POINTER_MISSING`.

Loop memory entries should store:

- task id
- task class
- scope
- result
- evidence grade
- files changed
- tests run
- commit status
- next recommendation

## Active Workflow Integration

`ACTIVE_WORKFLOW_STATE_001.json` remains the current workflow pointer. AIROS should use it for:

- current phase
- last completed task
- next task
- active loop memory file
- working tree expectation
- active question status
- governance flags

`TASK_QUEUE_001.json` remains the task scheduling layer.

## Update Cadence

| Artifact | Cadence |
|---|---|
| `ACTIVE_WORKFLOW_STATE_001.json` | Every task that changes workflow state |
| active loop memory file | Every completed task |
| task queue | Every task completion or new queued task |
| registries | After file moves, command additions, test additions, or refactor batches |
| context cache | After registry updates or workflow state changes |
| health dashboard | Before implementation tasks and before commits |

## Safety Boundaries

AIROS must preserve existing project safety:

- Paper mode is default.
- Live trading requires explicit operator intent and readiness preflight.
- No strategy, sizing, risk, execution, order submission, dashboard, Telegram, `.env`, or runtime behavior changes from AIROS design.
- Offline tools remain offline-only unless separately scoped.
- Historical reports are evidence, not active instructions.
- Dirty previous task outputs must be committed before implementation starts.
- Full pytest, builders, backtests, paper, and live runtime commands remain controlled by task scope and resource governance.

## Phase Roadmap

### Phase 0 - Design

Create the AIROS architecture, bootstrap doc, schemas, templates, report, and references.

### Phase 1 - Static Registries

Generate initial JSON registries from existing docs and filesystem scans. No runtime coupling.

### Phase 2 - Validator

Add a read-only validator that checks registry freshness, active loop memory pointer, task queue consistency, and dirty tree classification.

### Phase 3 - Bootstrap CLI

Add a light `tools/` command that prints the AI startup packet from registries. It must remain offline-only and not import runtime trading code.

### Phase 4 - Dependency Graph Upgrade

Expand graph edges from text-search references into import-aware and docs-aware dependency maps.

### Phase 5 - Health Dashboard

Expose `repo_health.json` and optional human-readable status summaries for agents and operators.

### Phase 6 - Refactor Integration

Use AIROS registries as the planning input for continued tools reorganization and future `trader.py` decomposition.
