# REPOSITORY_PHASE1C_TOOLS_CANONICAL_REPLAY_MOVE_PLAN_001

## Final Verdict

FINAL_VERDICT: DESIGN_COMPLETE_MOVE_NOT_STARTED

## Candidate Analysis

Below is the analysis of all candidate files in the canonical and replay-related groups:

### 1. tools/canonical_regime_export.py
- **Current path**: `tools/canonical_regime_export.py`
- **Proposed path**: `tools/canonical/canonical_regime_export.py`
- **Imports from tests**: `tests/test_canonical_regime_export.py`
- **Imports from tools**: None (mirrored logic references only in `_drift_audit.py` comments)
- **Docs command examples**: Found in `docs/research/CANONICAL_REGIME_EXPORT_SPEC.md` and runbooks
- **Ops references**: None
- **Active workflow references**: None
- **CLI usage**: Offline regime metrics export
- **Risk level**: LOW_PATH_RISK
- **Decision**: **Include in Phase 1C batch** (has no cross-tool imports)

### 2. tools/runtime_event_replay.py
- **Current path**: `tools/runtime_event_replay.py`
- **Proposed path**: `tools/replay/runtime_event_replay.py`
- **Imports from tests**: `tests/test_runtime_event_stream.py`
- **Imports from tools**: None
- **Docs command examples**: `docs/reports/RUNTIME_EVENT_STREAM_IMPLEMENTATION_REPORT_001.md`
- **Ops references**: None
- **Active workflow references**: None
- **CLI usage**: Replay runtime event log streams
- **Risk level**: LOW_PATH_RISK
- **Decision**: **Include in Phase 1C batch** (has no cross-tool imports)

### 3. tools/canonical_trade_context_builder.py
- **Current path**: `tools/canonical_trade_context_builder.py`
- **Proposed path**: `tools/canonical/canonical_trade_context_builder.py`
- **Imports from tests**: `tests/test_canonical_trade_context_builder.py`
- **Imports from tools**: None
- **Docs command examples**: High references in architecture and specs
- **Ops references**: None
- **Active workflow references**: None
- **CLI usage**: Canonical context loader
- **Risk level**: MEDIUM_IMPORT_RISK
- **Decision**: **Defer** (heavily referenced by QIE Offline Builder and other documentation; defer to ensure isolation)

### 4. tools/canonical_trade_table_v1.py
- **Current path**: `tools/canonical_trade_table_v1.py`
- **Proposed path**: `tools/canonical/canonical_trade_table_v1.py`
- **Imports from tests**: `tests/test_canonical_trade_table_v1.py`
- **Imports from tools**: None
- **Docs command examples**: References in schema slimming audits
- **Ops references**: None
- **Active workflow references**: None
- **CLI usage**: Trade table builder
- **Risk level**: MEDIUM_IMPORT_RISK
- **Decision**: **Defer** (keep at root alongside context builder for cohesion)

### 5. tools/replay_analyzer.py
- **Current path**: `tools/replay_analyzer.py`
- **Proposed path**: `tools/replay/replay_analyzer.py`
- **Imports from tests**: `tests/test_replay_analyzer.py`
- **Imports from tools**: Imported by 9 other tools (including `candidate_continuity.py`, `ev_field_coverage.py`, `no_entry_analyzer.py`)
- **Docs command examples**: Widely referenced
- **Ops references**: None
- **Active workflow references**: None
- **CLI usage**: Replay log parsing and analyzer
- **Risk level**: MEDIUM_IMPORT_RISK
- **Decision**: **Defer** (heavily imported by other tools; moving this now has high blast radius)

### 6. tools/commitment_regime_replay.py
- **Current path**: `tools/commitment_regime_replay.py`
- **Proposed path**: `tools/replay/commitment_regime_replay.py`
- **Imports from tests**: `tests/test_commitment_regime_replay.py`, `tests/test_multi_session_runner.py`
- **Imports from tools**: Referenced in `tools/multi_session_runner.py` REPLAY_STEPS list
- **Docs command examples**: Research session logs
- **Ops references**: None
- **Active workflow references**: None
- **CLI usage**: Replay tool
- **Risk level**: MEDIUM_IMPORT_RISK
- **Decision**: **Defer** (dynamically imported and run by `multi_session_runner.py`; defer to avoid multi-file changes)

### 7. tools/convergence_regime_classification_replay.py
- **Current path**: `tools/convergence_regime_classification_replay.py`
- **Proposed path**: `tools/replay/convergence_regime_classification_replay.py`
- **Imports from tests**: `tests/test_convergence_regime_classification_replay.py`
- **Imports from tools**: Referenced in `tools/multi_session_runner.py` REPLAY_STEPS list
- **Docs command examples**: Replay classification
- **Ops references**: None
- **Active workflow references**: None
- **CLI usage**: Replay tool
- **Risk level**: MEDIUM_IMPORT_RISK
- **Decision**: **Defer** (referenced in `multi_session_runner.py` steps)

### 8. tools/exit_convergence_intelligence_replay.py
- **Current path**: `tools/exit_convergence_intelligence_replay.py`
- **Proposed path**: `tools/replay/exit_convergence_intelligence_replay.py`
- **Imports from tests**: `tests/test_exit_convergence_intelligence_replay.py`
- **Imports from tools**: Referenced in `tools/multi_session_runner.py` REPLAY_STEPS list
- **Docs command examples**: Exit intelligence
- **Ops references**: None
- **Active workflow references**: None
- **CLI usage**: Replay tool
- **Risk level**: MEDIUM_IMPORT_RISK
- **Decision**: **Defer** (referenced in `multi_session_runner.py` steps)

### 9. tools/lifecycle_profit_management_replay.py
- **Current path**: `tools/lifecycle_profit_management_replay.py`
- **Proposed path**: `tools/replay/lifecycle_profit_management_replay.py`
- **Imports from tests**: `tests/test_lifecycle_profit_management_replay.py`
- **Imports from tools**: Referenced in `tools/multi_session_runner.py` REPLAY_STEPS list
- **Docs command examples**: PM replay
- **Ops references**: None
- **Active workflow references**: None
- **CLI usage**: Replay tool
- **Risk level**: MEDIUM_IMPORT_RISK
- **Decision**: **Defer** (referenced in `multi_session_runner.py` steps)

### 10. tools/stabilization_survival_replay.py
- **Current path**: `tools/stabilization_survival_replay.py`
- **Proposed path**: `tools/replay/stabilization_survival_replay.py`
- **Imports from tests**: `tests/test_stabilization_survival_replay.py`
- **Imports from tools**: Referenced in `tools/multi_session_runner.py` REPLAY_STEPS list
- **Docs command examples**: Survival metrics
- **Ops references**: None
- **Active workflow references**: None
- **CLI usage**: Replay tool
- **Risk level**: MEDIUM_IMPORT_RISK
- **Decision**: **Defer** (referenced in `multi_session_runner.py` steps)

### 11. tools/lifecycle_truth_backfill.py & tools/lifecycle_truth_tables.py
- **Current paths**: `tools/lifecycle_truth_backfill.py` & `tools/lifecycle_truth_tables.py`
- **Proposed paths**: `tools/replay/lifecycle_truth_backfill.py` & `tools/replay/lifecycle_truth_tables.py`
- **Imports from tests**: `tests/test_lifecycle_truth_backfill.py` & `tests/test_lifecycle_truth_tables.py`
- **Imports from tools**: Heavily cross-imported by `candidate_continuity.py`, `candidate_path_observability.py`, etc.
- **Risk level**: MEDIUM_IMPORT_RISK
- **Decision**: **Defer** (keep with `replay_analyzer.py` to minimize cross-tool dependency breakage)

---

## Selected Phase 1C Batch

**Selected Batch**: `tools/canonical_regime_export.py` & `tools/runtime_event_replay.py`

This batch is the safest possible Phase 1C configuration because:
- They are not part of `REPLAY_STEPS` in `multi_session_runner.py`.
- They have zero cross-imports from other tools.
- They are isolated utilities with direct test files.

## Move List

| Current path | Proposed path | Category | Risk | Test refs | Docs refs | Ops refs | Import refs |
|---|---|---|---|---|---|---|---|
| `tools/canonical_regime_export.py` | `tools/outcome_truth/` | canonical | LOW_PATH_RISK | 1 test file | specs, runbooks | None | test imports only |
| `tools/runtime_event_replay.py` | `tools/replay/runtime_event_replay.py` | replay | LOW_PATH_RISK | 1 test file | reports | None | test imports only |

---

## Reference Update Plan

### Tests To Update

| Test file | Current reference | New reference |
|---|---|---|
| `tests/test_canonical_regime_export.py` | `import tools.canonical_regime_export as cre` | `import tools.canonical.canonical_regime_export as cre` |
| `tests/test_runtime_event_stream.py` | `from tools.runtime_event_replay import ...` | `from tools.replay.runtime_event_replay import ...` |

### Docs To Treat As Historical

The following historical docs will not be updated:
- `docs/architecture/QUANT_ARCHITECTURE_MASTER_PLAN_001.md`
- `docs/reports/RUNTIME_EVENT_STREAM_IMPLEMENTATION_REPORT_001.md`
- `docs/reports/REPOSITORY_PHASE1_TOOLS_AUDIT_REORGANIZATION_001.md`

---

## Validation Plan

Run after the move:

1. Search for old paths:
```powershell
rg "tools/canonical_regime_export.py|tools\.canonical_regime_export" . -g "!*.md" -g "!*.json"
rg "tools/runtime_event_replay.py|tools\.runtime_event_replay" . -g "!*.md" -g "!*.json"
```

2. Compile moved files only:
```powershell
.venv\Scripts\python.exe -m py_compile tools\canonical\canonical_regime_export.py
.venv\Scripts\python.exe -m py_compile tools\replay\runtime_event_replay.py
```

3. Run targeted pytest only:
```powershell
.venv\Scripts\python.exe -m pytest tests\test_canonical_regime_export.py tests\test_runtime_event_stream.py -q
```

---

## Rollback Plan

If validation fails, execute:

```powershell
git mv tools/canonical/canonical_regime_export.py tools/canonical_regime_export.py
git mv tools/replay/runtime_event_replay.py tools/runtime_event_replay.py
```

Revert updates in:
- `tests/test_canonical_regime_export.py`
- `tests/test_runtime_event_stream.py`

Then verify compile and pytest pass at original locations.
