# Repository Cleanup and Organization Audit

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Mode: read-only audit. No files deleted, moved, renamed, or changed outside this report.

## Executive Verdict

```text
CLEANUP_STATUS: NEEDED_BEFORE_PERFORMANCE_STACK
PRIMARY_CLUTTER: runtime evidence volume, logs volume, flat docs/research growth
RUNTIME_DATA_STATUS: ARCHIVE_CANDIDATE, not delete
TEST_STATUS: KEEP / reorganize only with dedicated test-layout task
DOCS_STATUS: organize research notes by session/domain, no exact duplicate markdown hashes found
APPROVAL_REQUIRED: yes for any delete, archive, move, or cache removal
```

The repo is functionally organized enough to continue work, but it is carrying heavy evidence and research accumulation. The biggest pressure is disk volume, not source-code clutter:

- `runtime/`: about `11,604.66 MB`
- `runtime/quant_data/`: about `10,547.59 MB`
- `logs/`: about `971.89 MB`
- `docs/research/`: `124` markdown files, with `91` directly in the root of `docs/research`

Before a performance stack setup, the safest cleanup path is to archive old runtime/log evidence by date and normalize research docs into session/domain folders. Do not delete anything without operator approval.

## Role Routing

Primary role: `01_PROJECT_MANAGER_AGENT.md`

Supporting role: `02_CODE_ARCHITECT_AGENT.md`

Why selected: this is cleanup sequencing, phase boundary control, and repository organization, not runtime implementation.

Files inspected:

- `CODEX_START_HERE.md`
- `PROJECT_RULES.md`
- `MASTER_AGENT_ROUTER.md`
- `CURRENT_PROJECT_STATUS.md`
- `DOCUMENTATION_MAP.md`
- `docs/PROJECT_CLEANUP_REPORT.md`
- repo metadata via `git status`, top-level file listing, size summaries, and docs/test inventories

Files intentionally ignored:

- strategy/risk/execution implementation internals
- wallet/live config contents
- raw JSONL/log content beyond metadata, counts, sizes, and names

## Repo Tree Summary

Top-level structure observed:

| Area | Status | Notes |
|---|---|---|
| `polymarket/` | KEEP | canonical runtime coordinator/client/market modules |
| `utils/` | KEEP | display, logging, risk, position, Telegram, quant logging helpers |
| `tools/` | KEEP | offline analyzers and report tooling |
| `tests/` | KEEP | large but active flat test suite |
| `docs/` | KEEP | canonical docs and research docs |
| `docs/research/` | MOVE_CANDIDATE for organization | root is crowded with daily/session/domain notes |
| `runtime/` | ARCHIVE_CANDIDATE by date/run | generated evidence; huge |
| `logs/` | ARCHIVE_CANDIDATE by date/run | generated logs; already gitignored |
| `research_cockpit/` | KEEP, with generated subfolders reviewed | frontend/app surface; `node_modules` and `dist` are generated |
| `archive/` | KEEP | existing legacy docs archive |
| `.codex/`, `.claude/` | KEEP / DO_NOT_TOUCH unless tool config cleanup is scoped | local AI-tool config |
| `.env` | DO_NOT_TOUCH | secret/live-risk file |

Approximate directory sizes:

| Path | Files | Size |
|---|---:|---:|
| `runtime/` | 452 | `11,604.66 MB` |
| `runtime/quant_data/` | 131 | `10,547.59 MB` |
| `logs/` | 608 | `971.89 MB` |
| `research_cockpit/` | 2878 | `70.67 MB` |
| `tests/` | 212 | `7.69 MB` |
| `docs/` | 185 | `1.62 MB` |
| `docs/research/` | 124 | `1.31 MB` |
| `archive/` | 10 | `0.03 MB` |

## Git / Untracked State

Current tracked/untracked working-tree findings:

| Path | Status | Classification | Recommendation |
|---|---|---|---|
| `docs/research/delta_extreme_gate_audit.md` | staged/add shown by git status | KEEP | recent requested audit; commit with related docs when ready |
| `docs/research/morning_replay_key_runtime_audit.md` | staged/add shown by git status | KEEP | recent requested audit |
| `docs/research/no_trade_open_runtime_audit.md` | staged/add shown by git status | KEEP | recent requested audit |
| `docs/research/runtime_replay_key_blocker_audit.md` | staged/add shown by git status | KEEP / REVIEW | untracked/staged research doc not part of this task; review before commit |
| `docs/research/signal_rejection_root_cause_audit.md` | staged/add shown by git status | KEEP | recent requested audit |
| `docs/research/path_truth/path_truth_replay_key_live_validation.md` | modified | KEEP | ongoing validation note |

Ignored local/generated areas:

| Path | Status | Classification | Recommendation |
|---|---|---|---|
| `.env` | ignored | DO_NOT_TOUCH | never archive/delete casually |
| `.pytest_cache/` | ignored | DELETE_CANDIDATE_REQUIRES_APPROVAL | safe regenerate, but ask first |
| `__pycache__/`, package `__pycache__/` folders | ignored | DELETE_CANDIDATE_REQUIRES_APPROVAL | safe regenerate, but ask first |
| `runtime/` | ignored | ARCHIVE_CANDIDATE | archive by date/run, do not delete |
| `logs/` | ignored | ARCHIVE_CANDIDATE | archive/compress by date, do not delete |
| `research_cockpit/node_modules/` | ignored | DELETE_CANDIDATE_REQUIRES_APPROVAL | generated dependency folder; remove only if reinstall path is confirmed |
| `research_cockpit/dist/` | ignored | ARCHIVE_CANDIDATE or DELETE_CANDIDATE_REQUIRES_APPROVAL | generated build output; remove only if reproducible |
| `.claude/` | ignored | KEEP / DO_NOT_TOUCH | tool-local config |

## Top Clutter Areas

### 1. Runtime Quant Data

Classification: `ARCHIVE_CANDIDATE`

Size breakdown:

| Path | Files | Size |
|---|---:|---:|
| `runtime/quant_data/decision_log` | 19 | `4713.02 MB` |
| `runtime/quant_data/research_log` | 14 | `2609.95 MB` |
| `runtime/quant_data/market_snapshots` | 19 | `1761.51 MB` |
| `runtime/quant_data/risk_log` | 19 | `913.15 MB` |
| `runtime/quant_data/system_health` | 19 | `298.71 MB` |
| `runtime/quant_data/execution_log` | 19 | `246.40 MB` |
| `runtime/quant_data/trade_journal` | 18 | `4.64 MB` |
| `runtime/quant_data/path_truth` | 4 | `0.21 MB` |

Largest examples:

| File family | Example size |
|---|---:|
| `decision_log/2026-05-25.jsonl` | about `1084.84 MB` |
| `decision_log/2026-05-22.jsonl` | about `814.18 MB` |
| `research_log/2026-05-25.jsonl` | about `600.52 MB` |
| `market_snapshots/2026-05-25.jsonl` | about `345.46 MB` |

Recommendation: archive old completed dates into compressed evidence bundles, with a manifest per date. Keep latest active date and any milestone validation runs readily available.

### 2. Runtime Root Output Files

Classification: `ARCHIVE_CANDIDATE`

Large root runtime files:

| File | Size | Recommendation |
|---|---:|---|
| `runtime/paper_harvest_20260523_085423.out.log` | `464.88 MB` | archive/compress after confirming linked summary exists |
| `runtime/paper_harvest_stdout.txt` | `458.01 MB` | archive/compress after confirming linked summary exists |
| `runtime/validation_extended_run.log` | `23.09 MB` | archive with 2026-05-14 validation evidence |
| `runtime/validation_run_output.log` | `11.00 MB` | archive with 2026-05-14 validation evidence |
| `runtime/liquidity_truth_validation.log` | `9.19 MB` | archive with liquidity validation evidence |

These are high-value evidence artifacts, not deletion targets.

### 3. Logs

Classification: `ARCHIVE_CANDIDATE`

`logs/` contains `608` files totaling about `971.89 MB`. Many files are rotated `polytrade_bot_*.log` or `*.log.N` files around `1.9 MB`.

Recommendation: compress/archive logs by date, keeping the latest active run logs and the last few incident/milestone logs in place.

### 4. Docs / Research Structure

Classification: `MOVE_CANDIDATE`

Findings:

- `docs/research/` has `124` markdown files.
- `91` markdown files are directly under `docs/research/`.
- Session folders exist for `2026-05-17`, `2026-05-18`, `2026-05-21`, and `2026-05-22`.
- Most 2026-05-23 to 2026-05-28 research notes are flat in `docs/research/` instead of under `docs/research/sessions/YYYY-MM-DD/`.
- Exact duplicate markdown hashes under `docs/research/`: none found.

Move candidates:

| Pattern | Classification | Recommendation |
|---|---|---|
| `docs/research/*_audit.md` daily/session-specific notes | MOVE_CANDIDATE | move to `docs/research/sessions/YYYY-MM-DD/` by date when doing docs cleanup |
| `docs/research/*_validation.md` run-specific notes | MOVE_CANDIDATE | move to session folder or `docs/research/validation/` |
| `docs/research/*_monitor.md` active rolling monitors | KEEP | keep flat if they are current rolling state, or move to `docs/research/monitors/` |
| `docs/research/research_cockpit_*` | MOVE_CANDIDATE | group under `docs/research/cockpit/` |
| `docs/research/executable_*` | MOVE_CANDIDATE | group under `docs/research/executable_truth/` |
| `docs/research/path_truth_*` | MOVE_CANDIDATE | group under `docs/research/path_truth/` |
| `docs/research/session_*` | MOVE_CANDIDATE | group under `docs/research/session_edges/` |

Do not move now; many docs may be referenced by exact path in recent tasks.

### 5. Root-Level Markdown Research Notes

Classification: `MOVE_CANDIDATE`

Root-level operational docs should stay in root. Root-level dated research notes should be moved in a dedicated docs-cleanup task.

| File | Classification | Recommendation |
|---|---|---|
| `research_cockpit_v2_gap_audit.md` | MOVE_CANDIDATE | move to `docs/research/cockpit/` or `docs/research/` |
| `runtime_clean_validation_2026-05-19.md` | MOVE_CANDIDATE | move to `docs/research/sessions/2026-05-19/` |
| `overnight_maturity_check_2026-05-19.md` | MOVE_CANDIDATE | move to `docs/research/sessions/2026-05-19/` |
| `stop_loss_concentration_diagnosis_2026-05-19.md` | MOVE_CANDIDATE | move to `docs/research/sessions/2026-05-19/` |
| `repo_canonical_check_2026-05-19.md` | MOVE_CANDIDATE | move to `docs/research/sessions/2026-05-19/` or `docs/research/repo_health/` |
| `DOC_TRUTH_RECONCILIATION_2026-05-14.md` | MOVE_CANDIDATE | move to `docs/research/docs_audits/` |
| `KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md` | MOVE_CANDIDATE | merge/archive after confirming `KNOWN_ISSUES.md` and `docs/KNOWN_ISSUES.md` cover it |
| `CLAUDE.md` | KEEP / REVIEW | tool-facing root doc may be intentional despite earlier cleanup history |

### 6. Generated Caches

Classification: `DELETE_CANDIDATE_REQUIRES_APPROVAL`

Observed generated cache folders:

- `.pytest_cache/`
- root `__pycache__/`
- `config/__pycache__/`
- `crypto_scalper/__pycache__/`
- `dashboard/__pycache__/`
- `polymarket/__pycache__/`
- `tests/__pycache__/`
- `tools/__pycache__/`
- `utils/__pycache__/`

These can be regenerated. They should not be archived for research value, but deletion still requires approval because this audit is read-only.

### 7. `docs.zip`

Classification: `ARCHIVE_CANDIDATE`

`docs.zip` exists at repo root. It appears to duplicate documentation packaging and is not listed in the active docs map.

Recommendation: verify creation purpose. If stale, move to `archive/legacy/docs/` or delete only with explicit operator approval.

### 8. Test File Organization

Classification: `KEEP`, future `MOVE_CANDIDATE`

Findings:

- `tests/` is flat and large.
- Test names span runtime, observability, replay, lifecycle, semantic shadow, UI, Telegram, config, and execution controls.
- This is navigable with `rg`, but not ergonomic for performance-stack work.

Recommendation: do not reorganize tests before performance stack setup unless there is a dedicated test-layout task. If reorganized later, use a staged plan:

1. `tests/unit/`
2. `tests/integration/`
3. `tests/research/`
4. `tests/runtime_safety/`
5. update pytest paths/import assumptions

Never delete tests.

## Naming Consistency Findings

| Finding | Classification | Recommendation |
|---|---|---|
| Mixed dates: `2026-05-19`, `2026_05_23`, and no date | RENAME_CANDIDATE | choose one convention for new docs, preferably ISO `YYYY-MM-DD` |
| Mixed report nouns: audit, monitor, validation, design, spec, review | KEEP | useful distinction, but define folder taxonomy |
| Root research docs mixed with canonical root docs | MOVE_CANDIDATE | keep root for operating docs only |
| `docs/research/sessions/` exists but recent sessions are flat | MOVE_CANDIDATE | restore session-folder habit for dated work |
| Generated runtime files use date-based names | KEEP | useful for evidence lineage |

## Cleanup Priority

| Priority | Area | Classification | Why |
|---:|---|---|---|
| 1 | `runtime/quant_data` old dates | ARCHIVE_CANDIDATE | 10.5 GB; largest performance/setup pressure |
| 2 | `runtime/*.log`, harvest stdout files | ARCHIVE_CANDIDATE | nearly 1 GB in two harvest files alone |
| 3 | `logs/` old rotated logs | ARCHIVE_CANDIDATE | about 972 MB; low operational value after summaries exist |
| 4 | `docs/research` flat root | MOVE_CANDIDATE | high cognitive clutter; low disk cost |
| 5 | root dated research markdown | MOVE_CANDIDATE | root-level confusion |
| 6 | caches and pyc | DELETE_CANDIDATE_REQUIRES_APPROVAL | safe space cleanup, low strategic value |
| 7 | `research_cockpit/node_modules`, `dist` | DELETE_CANDIDATE_REQUIRES_APPROVAL | generated dependencies/build output; verify reproducibility first |

## Safe Cleanup Plan

No action was taken in this audit. Proposed future plan:

1. Freeze current working tree and commit/park pending research docs.
2. Create an archive manifest format for runtime/log evidence.
3. Archive completed runtime dates older than the current active date into compressed date bundles.
4. Keep current active date, latest validation run, and milestone evidence in place.
5. Compress old `logs/` by date while preserving active/latest run logs.
6. Move root-level dated research docs into session folders.
7. Split `docs/research` into domain folders only after confirming no external process expects exact paths.
8. Remove generated caches only after operator approval.
9. Leave `.env`, config, runtime code, tests, and live-related files untouched.

Suggested future archive layout:

```text
archive/evidence/YYYY-MM-DD/
  quant_data_manifest.md
  runtime_logs_manifest.md
  selected_reports/
  compressed_raw/
```

## Files Requiring Operator Approval

Any operation on these requires explicit approval:

| Path | Why |
|---|---|
| `.env` | secrets/live-risk |
| `runtime/` | evidence may be needed for replay/research lineage |
| `logs/` | incident and runtime diagnostics |
| `runtime/quant_data/` | canonical raw evidence |
| `tests/` | persistent tests must not be deleted |
| `research_cockpit/node_modules/` | generated but may be needed for offline frontend work |
| `research_cockpit/dist/` | generated but may be useful for deployment/reference |
| root dated research markdown | may be referenced by exact path in recent prompts |
| `docs/research/*` | recent docs may be referenced by exact path |

## What Not To Touch

Classification: `DO_NOT_TOUCH`

- `.env`
- wallet/API credential helpers
- `config/`
- `polymarket/`
- `utils/risk_manager.py`
- `polymarket/order_manager.py`
- `polymarket/client.py`
- `utils/position_tracker.py`
- `tests/` contents without a dedicated test migration plan
- current active runtime files
- recent path-truth/replay-key validation docs until the validation sequence is complete
- archive contents unless a dedicated archive-index task is opened

## Classification Summary

| Classification | Items |
|---|---|
| KEEP | source modules, canonical docs, tests, current research monitors, active validation docs |
| ARCHIVE_CANDIDATE | old runtime JSONL, old logs, harvest stdout/log files, root `docs.zip` |
| MOVE_CANDIDATE | root dated research docs, flat `docs/research` session/domain docs |
| RENAME_CANDIDATE | inconsistent date naming and future docs with mixed separators |
| DELETE_CANDIDATE_REQUIRES_APPROVAL | Python caches, pytest cache, generated `node_modules`/`dist` if reproducible |
| DO_NOT_TOUCH | `.env`, config, live/wallet paths, runtime code, tests, active evidence |

## Final Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Files deleted: No

Files moved: No

Code changed: No

Tests run: none; docs-only repository audit.
