# REPOSITORY_PHASE1D_TOOLS_COMPLEX_CANONICAL_MOVE_PLAN_001

## Final Verdict

FINAL_VERDICT: DESIGN_COMPLETE_MOVE_NOT_STARTED

## Candidate Analysis

Below is the dependency and risk analysis for the complex tools:

### 1. tools/commitment_regime_replay.py
- **Current path**: `tools/commitment_regime_replay.py`
- **Proposed path**: `tools/replay/commitment_regime_replay.py`
- **Direct imports from tests**: `tests/test_commitment_regime_replay.py`, `tests/test_multi_session_runner.py`
- **Direct imports from tools**: None (referenced as module string in `tools/multi_session_runner.py`'s `REPLAY_STEPS`)
- **Dynamic execution references**: Executed dynamically by module string in `multi_session_runner.py`
- **Docs command examples**: Found in research session logs
- **Ops/task queue references**: None
- **Migration risk**: LOW (if updated in `multi_session_runner.py` steps)
- **Decision**: **Include in Phase 1D batch**

### 2. tools/convergence_regime_classification_replay.py
- **Current path**: `tools/convergence_regime_classification_replay.py`
- **Proposed path**: `tools/replay/convergence_regime_classification_replay.py`
- **Direct imports from tests**: `tests/test_convergence_regime_classification_replay.py`
- **Direct imports from tools**: None (referenced in `multi_session_runner.py` steps)
- **Dynamic execution references**: Executed dynamically in `multi_session_runner.py`
- **Docs command examples**: None
- **Ops/task queue references**: None
- **Migration risk**: LOW (if updated in steps)
- **Decision**: **Include in Phase 1D batch**

### 3. tools/exit_convergence_intelligence_replay.py
- **Current path**: `tools/exit_convergence_intelligence_replay.py`
- **Proposed path**: `tools/replay/exit_convergence_intelligence_replay.py`
- **Direct imports from tests**: `tests/test_exit_convergence_intelligence_replay.py`
- **Direct imports from tools**: None (referenced in `multi_session_runner.py` steps)
- **Dynamic execution references**: Executed dynamically in `multi_session_runner.py`
- **Docs command examples**: None
- **Ops/task queue references**: None
- **Migration risk**: LOW (if updated in steps)
- **Decision**: **Include in Phase 1D batch**

### 4. tools/lifecycle_profit_management_replay.py
- **Current path**: `tools/lifecycle_profit_management_replay.py`
- **Proposed path**: `tools/replay/lifecycle_profit_management_replay.py`
- **Direct imports from tests**: `tests/test_lifecycle_profit_management_replay.py`
- **Direct imports from tools**: None (referenced in `multi_session_runner.py` steps)
- **Dynamic execution references**: Executed dynamically in `multi_session_runner.py`
- **Docs command examples**: None
- **Ops/task queue references**: None
- **Migration risk**: LOW (if updated in steps)
- **Decision**: **Include in Phase 1D batch**

### 5. tools/stabilization_survival_replay.py
- **Current path**: `tools/stabilization_survival_replay.py`
- **Proposed path**: `tools/replay/stabilization_survival_replay.py`
- **Direct imports from tests**: `tests/test_stabilization_survival_replay.py`
- **Direct imports from tools**: None (referenced in `multi_session_runner.py` steps)
- **Dynamic execution references**: Executed dynamically in `multi_session_runner.py`
- **Docs command examples**: None
- **Ops/task queue references**: None
- **Migration risk**: LOW (if updated in steps)
- **Decision**: **Include in Phase 1D batch**

### 6. tools/quant_intelligence_engine.py
- **Current path**: `tools/quant_intelligence_engine.py`
- **Proposed path**: `tools/research/quant_intelligence_engine.py`
- **Direct imports from tests**: `tests/test_quant_intelligence_engine.py`
- **Direct imports from tools**: None
- **Dynamic execution references**: None
- **Docs command examples**: Found in QIE reports
- **Ops/task queue references**: Completed compiler task metadata
- **Migration risk**: LOW (isolated research tool)
- **Decision**: **Include in Phase 1D batch**

### 7. tools/replay_analyzer.py
- **Current path**: `tools/replay_analyzer.py`
- **Proposed path**: `tools/replay/replay_analyzer.py`
- **Direct imports from tests**: `tests/test_replay_analyzer.py`
- **Direct imports from tools**: Imported by 9 other tools (including continuity, coverage, and simulation tools)
- **Dynamic execution references**: None
- **Docs command examples**: High references in replay specs
- **Ops/task queue references**: None
- **Migration risk**: HIGH (due to heavy cross-tool dependencies)
- **Decision**: **Defer** (keep at root to avoid breaking dependent tools)

### 8. tools/lifecycle_truth_tables.py & tools/lifecycle_truth_backfill.py
- **Current paths**: `tools/lifecycle_truth_tables.py` & `tools/lifecycle_truth_backfill.py`
- **Proposed paths**: `tools/replay/lifecycle_truth_tables.py` & `tools/replay/lifecycle_truth_backfill.py`
- **Direct imports from tests**: `tests/test_lifecycle_truth_tables.py`, `tests/test_lifecycle_truth_backfill.py`
- **Direct imports from tools**: Cross-imported by `candidate_continuity.py`, `candidate_path_observability.py`, etc.
- **Migration risk**: MEDIUM (dependent on replay_analyzer)
- **Decision**: **Defer** (keep at root for cohesion with replay_analyzer)

### 9. tools/canonical_trade_context_builder.py & tools/canonical_trade_table_v1.py
- **Current paths**: `tools/canonical_trade_context_builder.py` & `tools/canonical_trade_table_v1.py`
- **Proposed paths**: `tools/canonical/canonical_trade_context_builder.py` & `tools/canonical/canonical_trade_table_v1.py`
- **Direct imports from tests**: `tests/test_canonical_trade_context_builder.py`, `tests/test_canonical_trade_table_v1.py`
- **Direct imports from tools**: None
- **Migration risk**: MEDIUM (high docs usage, active ops state references, CLI wrappers)
- **Decision**: **Defer** (keep at root as stable wrappers until final cleanup phase)

### 10. tools/multi_session_runner.py
- **Current path**: `tools/multi_session_runner.py`
- **Proposed path**: `tools/runtime/multi_session_runner.py`
- **Direct imports from tests**: `tests/test_multi_session_runner.py`
- **Direct imports from tools**: None
- **Migration risk**: HIGH (main offline orchestrator, high CLI usage risk)
- **Decision**: **Defer** (keep at root as stable orchestrator)

---

## Dependency Graph

```mermaid
graph TD
    MSR[tools/multi_session_runner.py]
    MSR -- dynamically executes module --> CRR[tools/commitment_regime_replay.py]
    MSR -- dynamically executes module --> ECI[tools/exit_convergence_intelligence_replay.py]
    MSR -- dynamically executes module --> CR[tools/convergence_regime_classification_replay.py]
    MSR -- dynamically executes module --> SS[tools/stabilization_survival_replay.py]
    MSR -- dynamically executes module --> LPM[tools/lifecycle_profit_management_replay.py]

    subgraph Phase 1D Moves (Selected)
        CRR
        ECI
        CR
        SS
        LPM
        QIE[tools/quant_intelligence_engine.py]
    end

    subgraph Deferred (Root Stable)
        MSR
        RA[tools/replay_analyzer.py]
        LTT[tools/lifecycle_truth_tables.py]
        LTB[tools/lifecycle_truth_backfill.py]
        CTCB[tools/canonical_trade_context_builder.py]
        CTT[tools/canonical_trade_table_v1.py]
    end

    RA --> LTT
    RA --> LTB
    LTT --> LTB
    RA --> continuity[tools/candidate_continuity.py]
    LTT --> continuity
```

---

## Selected Phase 1D Batch

**Selected Batch**: Move the 5 replay steps group + QIE tool, and update `multi_session_runner.py` steps.

This batch is highly cohesive and contains all standalone modules run as steps. Deferring the main runner and cross-tool imported utilities minimizes the blast radius.

## Move List

| Current path | Proposed path | Category | Risk |
|---|---|---|---|
| `tools/commitment_regime_replay.py` | `tools/replay/commitment_regime_replay.py` | replay | LOW (with MSR step update) |
| `tools/convergence_regime_classification_replay.py` | `tools/replay/convergence_regime_classification_replay.py` | replay | LOW (with MSR step update) |
| `tools/exit_convergence_intelligence_replay.py` | `tools/replay/exit_convergence_intelligence_replay.py` | replay | LOW (with MSR step update) |
| `tools/lifecycle_profit_management_replay.py` | `tools/replay/lifecycle_profit_management_replay.py` | replay | LOW (with MSR step update) |
| `tools/stabilization_survival_replay.py` | `tools/replay/stabilization_survival_replay.py` | replay | LOW (with MSR step update) |
| `tools/quant_intelligence_engine.py` | `tools/research/quant_intelligence_engine.py` | research | LOW (isolated tool) |

---

## Reference Update Plan

### Code File To Update
- `tools/multi_session_runner.py`: Update the module strings in `REPLAY_STEPS` from `"tools.X"` to `"tools.replay.X"`.

### Test Files To Update
- `tests/test_multi_session_runner.py`: Update module string matches in `TOOL_TO_PREFIX` and test assertions.
- `tests/test_commitment_regime_replay.py`: Update imports and `TOOL_PATH` file presence assertion to `"tools/replay/"`.
- `tests/test_convergence_regime_classification_replay.py`: Update imports.
- `tests/test_exit_convergence_intelligence_replay.py`: Update imports.
- `tests/test_lifecycle_profit_management_replay.py`: Update imports.
- `tests/test_stabilization_survival_replay.py`: Update imports.
- `tests/test_quant_intelligence_engine.py`: Update imports.

---

## Validation Plan

1. Search for old paths:
```powershell
rg "tools/commitment_regime_replay|tools\.commitment_regime_replay" . -g "!*.md" -g "!*.json"
rg "tools/convergence_regime_classification_replay|tools\.convergence_regime_classification_replay" . -g "!*.md" -g "!*.json"
rg "tools/exit_convergence_intelligence_replay|tools\.exit_convergence_intelligence_replay" . -g "!*.md" -g "!*.json"
rg "tools/lifecycle_profit_management_replay|tools\.lifecycle_profit_management_replay" . -g "!*.md" -g "!*.json"
rg "tools/stabilization_survival_replay|tools\.stabilization_survival_replay" . -g "!*.md" -g "!*.json"
rg "tools/quant_intelligence_engine|tools\.quant_intelligence_engine" . -g "!*.md" -g "!*.json"
```

2. Compile moved files only:
```powershell
.venv\Scripts\python.exe -m py_compile tools\replay\commitment_regime_replay.py tools\replay\convergence_regime_classification_replay.py tools\replay\exit_convergence_intelligence_replay.py tools\replay\lifecycle_profit_management_replay.py tools\replay\stabilization_survival_replay.py tools\research\quant_intelligence_engine.py tools\multi_session_runner.py
```

3. Run targeted pytest only (expect 394/394 passing):
```powershell
.venv\Scripts\python.exe -m pytest tests\test_commitment_regime_replay.py tests\test_convergence_regime_classification_replay.py tests\test_exit_convergence_intelligence_replay.py tests\test_lifecycle_profit_management_replay.py tests\test_stabilization_survival_replay.py tests\test_quant_intelligence_engine.py tests\test_multi_session_runner.py -q
```

---

## Rollback Plan

If validation fails:
1. `git mv` files back to `tools/` root directory.
2. Revert import updates in test files and `tools/multi_session_runner.py`.
3. Verify compilation and targeted tests pass at baseline root locations.
