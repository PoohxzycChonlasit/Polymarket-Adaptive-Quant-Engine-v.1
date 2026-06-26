# Regime Analytics V1 Commit Report

**Status:** `REGIME_ANALYTICS_V1_COMMIT_PASS`  
**Run ID:** `20260623T125000Z`  
**Commit Hash:** `622fa27be98ab22568f93ae00c3ac7ed3b4c4d1c`  
**Prior Commit Hash:** `cc0e01ad7ba48c1d490edf5eea8bb4da20fb7946` (dashboard: add candidate lifecycle analytics)

## 1. Staged and Committed Files

The following approved files were staged and successfully committed to the repository:

* [tools/dashboard_state_aggregator.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/dashboard_state_aggregator.py) (extended aggregator with Regime Analytics CSV parser and session evaluations parser)
* [tests/test_dashboard_state_aggregator.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tests/test_dashboard_state_aggregator.py) (added 5 python unit tests for regime calculations, sorting, and edge cases)
* [dashboard/src/types/dashboard.ts](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/dashboard/src/types/dashboard.ts) (updated types schema)
* [dashboard/src/pages/research/ResearchPage.tsx](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/dashboard/src/pages/research/ResearchPage.tsx) (rendered Regime Analytics Bloomberg V3 panel UI widgets)
* [REGIME_ANALYTICS_V1_DESIGN_001.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/REGIME_ANALYTICS_V1_DESIGN_001.md) (design document)
* [REGIME_ANALYTICS_V1_IMPLEMENTATION_REPORT_001.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/REGIME_ANALYTICS_V1_IMPLEMENTATION_REPORT_001.md) (implementation details report)
* [REGIME_ANALYTICS_V1_PRE_COMMIT_AUDIT_001.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/REGIME_ANALYTICS_V1_PRE_COMMIT_AUDIT_001.md) (pre-commit safety checklist)

## 2. Ignored Files

All runtime files, temporary artifacts, environments, and other pages remained unstaged:
* `runtime/` and `runtime/dashboard_state.json`
* Unrelated page files and packages
* Local environment files (`.env`)

## 3. Post-Commit Validation Smoke Output

All verification checks were successfully run prior to commit creation:

### Python Unit Tests
```bash
python -m pytest tests/test_dashboard_state_aggregator.py -q
..................................                                       [100%]
34 passed in 0.58s
```

### Vitest Frontend Tests
```bash
npm run test:run
 ✓ src/utils/formatters.test.ts (5 tests) 26ms
 ✓ src/pages/overview/OverviewPage.test.tsx (1 test) 72ms
 ✓ src/app/router/AppRouter.test.tsx (6 tests) 52ms

 Test Files  3 passed (3)
      Tests  12 passed (12)
   Start at  19:58:50
   Duration  2.94s
```

### Vite Production Build
```bash
npm run build
dist/assets/index-ySsdnF5j.css   17.72 kB │ gzip:   4.36 kB
dist/assets/index-wlXTM-B2.js   770.96 kB │ gzip: 231.31 kB
✓ built in 8.12s
```

### Format / Whitespace Compliance Check
```bash
git diff --check
# No whitespace or merge conflict markers found.
```

## 4. Final Verdict

**REGIME_ANALYTICS_V1_COMMIT_PASS**
