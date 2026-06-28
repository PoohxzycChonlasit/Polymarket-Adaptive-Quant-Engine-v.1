# REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001_CONTRACT_001

## Contract Metadata

- contract_id: CONTRACT-20260628-REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001
- created_at: 2026-06-28
- bootstrap_sha: c5fc3aa
- bootstrap_status: HEALTHY
- safety_memory_status: LOADED
- safety_memory_count: 10

## Task Identity

- task_id: REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001
- task_class: 6
- workflow_tier: LOOP
- objective: Move one no-import-risk offline probe from `tools/` to `tools/probes/`.

## Allowed Files

- `tools/silent_zone_selection_probe.py`
- `tools/probes/silent_zone_selection_probe.py`
- `docs/reports/REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001.md`
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json`
- `docs/operations/graph_queries/QUERY-20260628-REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001.md`
- `docs/operations/execution_contracts/REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001_CONTRACT_001.md`

## Forbidden Scope

- `polymarket/`
- `utils/`
- `config/`
- `tests/` unless reference validation proves required
- other `tools/` files
- `runtime/`
- dashboard, Telegram, `.env`, strategy, sizing, risk, execution, order submission, live/paper behavior

## Knowledge Graph Evidence

- graph_query_results_file: `docs/operations/graph_queries/QUERY-20260628-REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001.md`
- safety_findings: []
- safety_stop_triggered: false
- blast_radius_score: LOW
- graph_confidence: 0.4
- graph_timestamp: 2026-06-27
- stop_condition_triggered: none
- degraded_reason: target and baseline commit are not represented in seeded graph; fallback evidence used.

## Verification Plan

- `rg "tools/silent_zone_selection_probe.py|tools.silent_zone_selection_probe|silent_zone_selection_probe" .`
- `.venv\Scripts\python.exe -m py_compile tools\probes\silent_zone_selection_probe.py`
- `git diff --name-status`
- `git status --short`
- JSON validation for modified ops files

## Explicit Non-Actions

- Do not run pytest.
- Do not run builders.
- Do not run backtests.
- Do not launch paper or live runtime.

## Commit Policy

- Commit message: `refactor: move no-risk probe tool into probes folder`
