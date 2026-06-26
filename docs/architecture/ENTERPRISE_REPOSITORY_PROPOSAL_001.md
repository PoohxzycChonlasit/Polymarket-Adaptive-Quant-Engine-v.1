# ENTERPRISE_REPOSITORY_PROPOSAL_001

**Task:** REPOSITORY_ORGANIZATION_AUDIT_001  
**Mode:** DISCOVERY ONLY — this is a PROPOSAL, not an implementation  
**Date:** 2026-06-26

---

## Design Principles

1. **Root is sacred.** Root contains only: entry points, configuration, AI startup context, and repo metadata.
2. **Every file has one home.** No duplicates. No stub files pointing to the "real" copy.
3. **Documentation has hierarchy.** Active design docs, historical audit reports, and AI working notes are visually distinguishable by their folder path.
4. **Generated files never coexist with source.** Runtime data, logs, and compiled artifacts have their own top-level folders.
5. **Orphaned projects are isolated or removed.** If it's not part of PolyTrade, it gets extracted or archived.
6. **AI readability is a first-class concern.** An AI loading this repo for the first time should find essential context in < 5 files in root.

---

## Proposed Layout

```
PolyTrade/
├── .claude/                    # Claude Code AI tooling
│   ├── memory/                 # Session memory (moved from memory/)
│   └── MEMORY.md
│
├── .codex/                     # Codex / ChatGPT AI tooling (unchanged)
│   ├── prompts/
│   ├── security/
│   └── skills/
│
├── .github/                    # GitHub Actions CI/CD (future)
│   └── workflows/
│
├── config/                     # Runtime configuration
│   ├── settings.py             # Pydantic BaseSettings (unchanged)
│   └── __init__.py
│
├── dashboard/                  # React + Python dashboard (active)
│   ├── src/                    # React source
│   ├── dist/                   # Built assets
│   ├── dashboard_api.py        # Moved from api/
│   ├── app.py
│   ├── data_loader.py
│   ├── live_dashboard.py
│   ├── offline_quant_report_dashboard.py
│   └── package.json
│
├── docs/                       # ALL documentation
│   ├── ai_context/             # NEW: AI startup prompts for non-Claude tools
│   │   ├── CHATGPT_PROJECT_START_PROMPT.md
│   │   └── CODEX_START_PROMPT.md
│   │
│   ├── architecture/           # Permanent design decisions (V1 docs)
│   │   ├── ALWAYS_ACTIVE_ENGINE_V1_DESIGN_001.md
│   │   ├── BANKROLL_ENGINE_V1_DESIGN_001.md
│   │   ├── DECISION_FRAMEWORK_V1_DESIGN_001.md
│   │   ├── EVENT_CATALOG_V1.md
│   │   ├── POSITION_SIZING_ENGINE_V1_DESIGN_001.md
│   │   ├── RUNTIME_STATE_MACHINE_V1.md
│   │   └── ... (all _V1_ and _DESIGN_ docs)
│   │
│   ├── audits/                 # Quality and compliance audits
│   │   ├── GOVERNANCE_V1_CLOSURE_AUDIT_001.md
│   │   ├── QUANT_CORE_ARCHITECTURE_CONSISTENCY_AUDIT_001.md
│   │   ├── SCHEMA_SLIMMING_FEASIBILITY_AUDIT_001.md
│   │   ├── SELECTION_BIAS_AUDIT.md
│   │   └── ...
│   │
│   ├── design/                 # Implementation plans and feature specs
│   │   ├── COLD_JSONL_COMPRESSION_REAL_IMPLEMENTATION_PLAN_001.md
│   │   ├── DASHBOARD_STATE_DESIGN_001.md
│   │   ├── DELTA_EXTREME_SHADOW_OVERLAY_SPEC_001.md
│   │   ├── EXECUTION_SHADOW_FILTER_SPEC_001.md
│   │   ├── OPTION_D_SHADOW_IMPLEMENTATION_PLAN_001.md
│   │   └── ...
│   │
│   ├── operations/             # Runbooks and operational procedures
│   │   ├── PAPER_TRADING_RUNBOOK.md
│   │   ├── DOC_SYNC_PROCEDURE.md
│   │   ├── VULTR_PAPER_RUN.md
│   │   └── INCIDENT_RESPONSE.md
│   │
│   ├── quant_agent_setup_md/   # Agent role documentation (unchanged)
│   │   ├── 00_MASTER_CONTEXT.md
│   │   ├── 01_QUANT_OPERATING_SYSTEM.md
│   │   ├── 02_AGENT_INDEX.md
│   │   └── ... (01_–23_ agent role files)
│   │
│   ├── reports/                # Patch history, commit reports, impl reports
│   │   ├── 2026-04/            # Optionally organized by month
│   │   ├── 2026-05/
│   │   ├── 2026-06/
│   │   └── ... (all *_COMMIT_REPORT*.md, *_IMPLEMENTATION_REPORT*.md)
│   │
│   └── research/               # Research findings organized by domain
│       ├── campaigns/          # (existing)
│       ├── candidate_graveyard/# (existing)
│       ├── discovery/          # (existing)
│       ├── executable_truth/   # (existing)
│       ├── frontiers/          # (existing)
│       ├── path_truth/         # (existing)
│       ├── performance/        # (existing)
│       ├── risk_modes/         # NEW: risk mode research (MICRO_RECOVERY, DEFENSIVE, etc.)
│       ├── runtime_health/     # (existing)
│       ├── session_edge/       # (existing)
│       ├── sessions/           # (existing)
│       └── watchlists/         # (existing)
│
├── experiments/                # NEW: isolated experiments (not in production)
│   ├── hft/                    # Moved from root hft/
│   └── crypto_scalper/         # Moved from root crypto_scalper/
│
├── archive/                    # Superseded/historical docs (existing, unchanged)
│   └── ...
│
├── polymarket/                 # Core trading engine (active, unchanged)
│   ├── trader.py
│   ├── signal.py
│   ├── probability_model.py
│   ├── expected_value.py
│   ├── position_sizing.py
│   ├── risk_modes.py
│   ├── order_manager.py
│   ├── order_intent.py
│   └── ... (all core engine files)
│
├── utils/                      # Shared Python utilities (active, unchanged)
│   ├── risk_manager.py
│   ├── display.py
│   ├── logger.py
│   ├── quant_event_logger.py
│   └── ...
│
├── research/                   # Live research: session notes + experiment code
│   ├── sessions/               # Date-organized session notes
│   │   ├── 2026-04-18.md
│   │   ├── 2026-04-19.md
│   │   └── ...
│   ├── experiments/            # Research Python scripts
│   │   ├── markov_analysis.py
│   │   └── markov_backtest.py
│   └── README.md
│
├── runtime/                    # Runtime-generated data (existing structure, unchanged)
│   ├── quant_data/
│   ├── realtime_logs/
│   ├── reports/
│   ├── research_exports/
│   ├── research_state/
│   └── ...
│
├── scripts/                    # Operational scripts
│   ├── ai_analyst.py           # (existing)
│   ├── check_balance.py        # Moved from root
│   ├── daily_report.py         # Moved from root
│   ├── generate_bypass.py      # Moved from root (after review)
│   ├── hft_paper_summary.py    # (existing)
│   ├── register_api_keys.py    # Moved from root
│   └── vultr_deploy_paper.py   # (existing)
│
├── tests/                      # Test suite (active, unchanged)
│   ├── test_*.py               # (139 test files)
│   ├── __init__.py
│   └── conftest.py (if exists)
│
├── tools/                      # Offline analysis tools (active, unchanged)
│   ├── replay_analyzer.py
│   ├── quant_data_quality.py
│   ├── session_runtime_evaluator.py
│   └── ... (all analysis tools)
│
│   # NOTE: __pycache__/ removed from all source dirs via .gitignore fix
│
├── .env                        # Runtime secrets (never committed)
├── .env.example                # Template
├── .gitignore                  # Updated with __pycache__, *.pyc, .venv*
├── AGENTS.md                   # AI startup: agent registry
├── CLAUDE.md                   # AI startup: Claude Code contract
├── CODEX_START_HERE.md         # AI startup: read-first sequence
├── CURRENT_PROJECT_STATUS.md   # AI startup: live status
├── FILE_INDEX.md               # Navigation index
├── DOCUMENTATION_MAP.md        # Documentation map
├── MASTER_AGENT_ROUTER.md      # AI startup: task routing
├── PROJECT_RULES.md            # AI startup: constraints
├── README.md                   # Public repository entry point
├── main.py                     # Entry point
├── pytest.ini                  # Test configuration
└── requirements.txt            # Python dependencies
```

---

## Key Improvements Over Current State

### Root Directory: 408 files → ~18 files

| Current Root | Proposed Root |
|---|---|
| 395 markdown files | 10 markdown files (AI startup only) |
| 5 Python scripts mixed with docs | main.py only (others → scripts/) |
| No clear separation | Clear: entry points + AI context + metadata |

### Documentation: Flat dump → Hierarchy

| Current | Proposed |
|---|---|
| 395 + 510 files, partially organized | All in docs/ with 8 semantic subfolders |
| Audit, design, report mixed together | architecture/, design/, reports/, research/ separated |
| 149 docs/research/ files at root | Classified into 12 research subfolders |

### Orphaned Projects: Colocated → Isolated

| Current | Proposed |
|---|---|
| hft/ in root of PolyTrade repo | experiments/hft/ |
| crypto_scalper/ in root | experiments/crypto_scalper/ |
| research_cockpit/ in root | Deleted (abandoned prototype) |
| web-dashboard/ in root | Deleted (abandoned prototype) |

### Compiled Artifacts: Tracked → Excluded

| Current | Proposed |
|---|---|
| 210+ .pyc files in tools/ | .gitignore: **/__pycache__/, **/*.pyc |
| 542 .pyc files in tests/ | Removed from git tracking |
| .pyc in crypto_scalper/ | Removed with folder |

---

## New Folders Required

| New Folder | Reason | Files |
|---|---|---|
| `docs/design/` | Implementation plans (distinct from architecture) | ~20 files from root |
| `docs/ai_context/` | Non-Claude AI startup prompts | 2 files from root |
| `docs/research/risk_modes/` | Concentrated MICRO_RECOVERY/DEFENSIVE research | ~10 files |
| `experiments/` | Isolated legacy/experimental projects | hft/, crypto_scalper/ |

---

## Root File Count Before vs After

| Category | Current | Proposed |
|---|---|---|
| Markdown files | 395 | 10 |
| Python entry points | 1 (main.py) | 1 (main.py) |
| Python utility scripts | 4 | 0 (→ scripts/) |
| Config / metadata | 6 | 6 (unchanged) |
| Security (.env) | 3 | 2 (.env + .env.example; delete .env.backup.local) |
| **Total root files** | **408** | **~19** |

---

## What Does NOT Change

- All Python source files in `polymarket/`, `utils/`, `config/`, `tools/`, `tests/` — unchanged
- All runtime paths and JSONL log paths — unchanged
- `dashboard/src/` React source structure — unchanged
- `.claude/` and `.codex/` directories — unchanged (memory/ moves into .claude/)
- `runtime/` directory structure — unchanged
- All test file names and pytest.ini config — unchanged
- `CLAUDE.md` content and position (root) — unchanged
- `AGENTS.md` position (root) — unchanged

---

## Migration Complexity Estimate

| Phase | Scope | Effort | Risk |
|---|---|---|---|
| Fix .gitignore and remove .pyc | Global | Low | Zero |
| Delete venv backups | Root | Low | Zero |
| Move root scripts → scripts/ | 4 files | Low | Low |
| Move root markdown → docs/ | 376 files | Medium | Low |
| Delete stub duplicates | 3 files | Low | Low |
| Move api/ → dashboard/ | 1 file | Low | Low (1 import check) |
| Move memory/ → .claude/ | 2 files | Low | Low |
| Archive research_cockpit/ web-dashboard/ | 2 folders | Medium | Low |
| Move hft/ crypto_scalper/ → experiments/ | 2 folders | Medium | Low |
| Update FILE_INDEX.md + DOCUMENTATION_MAP.md | 2 files | Medium | Low |
| Update MASTER_AGENT_ROUTER.md references | 1 file | Low | Low |
