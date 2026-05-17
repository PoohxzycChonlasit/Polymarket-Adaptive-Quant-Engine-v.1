# Docs Reorganization Dependency Audit — Migration Plan v1

> **Date:** 2026-05-17
> **Scope:** Audit + Phase 1 executed (session analysis files moved).
> **Primary role:** 24_DOCUMENTATION_SYSTEM_AGENT (supporting: 08_RESEARCH_QUANT_AGENT, 07_TEST_CI_AGENT, 11_OBSERVABILITY_INCIDENT_AGENT)
> **Runtime behavior changed:** No
> **Live behavior changed:** No
>
> **Phase 1 status: COMPLETE (2026-05-17)**
> Moved to `docs/research/sessions/2026-05-17/`:
> - `late_window_cutoff_diagnosis_2026-05-17.md` ✓
> - `research_cockpit_live_validation.md` ✓
> - `research_cockpit_runtime_observation_2026-05-17.md` ✓
> Zero references updated (all 3 files had 0 cross-references at move time).
> Phase 2 (startup prompts → docs/project/) and Phase 3 (quant_core docs) pending operator approval.

---

## 1. Inventory — All Root-Level .md Files (24 files)

| File | Size | Reference Count | Category |
|---|---|---|---|
| AGENTS.md | 18.4 KB | 86 (all .md) | keep_at_root |
| BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md | 1.6 KB | 12 (all .md) | quant_core |
| CHATGPT_PROJECT_START_PROMPT.md | 1.5 KB | 6 (all .md) | project |
| CLAUDE.md | 4.7 KB | 23 (all .md) | keep_at_root |
| CODEX_START_HERE.md | 7.0 KB | 35 (34 .md, 1 .json) | keep_at_root |
| CODEX_START_PROMPT.md | 1.9 KB | 6 (all .md) | project |
| CURRENT_PROJECT_STATUS.md | 41.3 KB | 62 (all .md) | keep_at_root |
| DOCUMENTATION_MAP.md | 5.8 KB | 23 (all .md) | keep_at_root |
| DOC_TRUTH_RECONCILIATION_2026-05-14.md | 14.8 KB | 4 (all .md) | issues/archive |
| FILE_INDEX.md | 17.4 KB | 47 (all .md) | keep_at_root |
| INVENTORY_REPLAY_RESEARCH_PLAN.md | 1.7 KB | 14 (all .md) | quant_core |
| KNOWN_ISSUES.md | 0.3 KB | 47 (all .md) | keep_at_root (stub) |
| KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md | 15.5 KB | 1 (.md) | issues/archive |
| MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md | 1.4 KB | 13 (all .md) | quant_core |
| MASTER_AGENT_ROUTER.md | 10.4 KB | 56 (all .md) | keep_at_root |
| PROJECT_RULES.md | 5.2 KB | 49 (all .md) | keep_at_root |
| PROJECT_STRUCTURE.md | 0.6 KB | 39 (all .md) | keep_at_root (stub) |
| QUANT_FUTURE_DECISION_ENGINE.md | 4.9 KB | 32 (all .md) | keep_at_root |
| QUANT_LIFECYCLE_INVENTORY_ENGINE.md | 15.6 KB | 9 (all .md) | quant_core |
| QUANT_REGIME_PROBABILITY_ENGINE.md | 2.1 KB | 15 (all .md) | quant_core |
| README.md | 26.1 KB | 314 (self + web) | keep_at_root |
| VULTR_PAPER_RUN.md | 1.6 KB | 4 (all .md) | project |
| late_window_cutoff_diagnosis_2026-05-17.md | 12.3 KB | **0** | research/sessions |
| research_cockpit_live_validation.md | 13.2 KB | **0** | research/sessions |
| research_cockpit_runtime_observation_2026-05-17.md | 11.7 KB | **0** | research/sessions |

**Totals:** 24 root-level .md files · ~220 KB total

**Reference type breakdown:** All cross-references are `.md → .md` links inside other documentation files. Zero Python `open()` / `Path()` calls load any root .md file. Zero shell scripts reference root .md files. Zero CI workflows exist.

---

## 2. Dependency Detection Results

### 2a. Python Code References

No Python code in `polymarket/`, `utils/`, `tools/`, `tests/`, `main.py`, or `daily_report.py` loads or reads any root-level .md file by path. All Python `.md` references are to **generated output files** (replay reports, session summaries, runner manifests) written to `runtime/` or `tools/` output paths — none point to the documentation root files.

**Python risk: NONE for any root .md move.**

### 2b. Prompt / Bootstrap Loader References

The multi-agent bootstrap system (Codex, Claude, ChatGPT, Hermes) relies on a hardcoded **read-first sequence** embedded in multiple .md files:

```
Read first:
1. CODEX_START_HERE.md
2. PROJECT_RULES.md
3. AGENTS.md
4. MASTER_AGENT_ROUTER.md
5. CURRENT_PROJECT_STATUS.md
6. PROJECT_STRUCTURE.md
7. KNOWN_ISSUES.md
8. FILE_INDEX.md
9. QUANT_FUTURE_DECISION_ENGINE.md
```

This sequence appears verbatim in: `AGENTS.md`, `CODEX_START_HERE.md`, `DOCUMENTATION_MAP.md`, `FILE_INDEX.md`, `CHATGPT_PROJECT_START_PROMPT.md`, `CODEX_START_PROMPT.md`, and all 23+ role docs under `docs/quant_agent_setup_md/roles/`. These paths are interpreted as **repo-root-relative** by all agents. Moving any file in this read-first sequence would silently break agent bootstrapping unless every occurrence is updated.

**Bootstrap risk: CRITICAL for the 9 read-first files. MEDIUM for others.**

### 2c. Platform/Tool Auto-Loaders

| File | Auto-Loader | Behavior if Moved |
|---|---|---|
| `CLAUDE.md` | Claude Code reads from repo root automatically | **Silently stops loading** — no error, but project instructions lost |
| `AGENTS.md` | Codex/GitHub Copilot auto-loads from root | **Silently stops loading** — agent context lost |
| `README.md` | GitHub renders root README.md by default | Repo landing page goes blank |

**These three files are HARD BLOCKED from moving by platform convention.**

### 2d. Obsidian References

Obsidian vault (`F:\Projects\PPPPP_pro_trade\Quant Lifecycle Research\obsidian_quant_research_os`) has **0 references** to any root-level .md file. Obsidian links use wiki-link syntax pointing to vault-internal files only. No Obsidian risk.

### 2e. Shell / CI References

No `.sh` scripts (outside `web-dashboard/node_modules`) reference root .md files. No `.github/` CI workflows exist. **No CI risk.**

### 2f. Existing `docs/` Structure

The `docs/` directory already contains:

```
docs/
├── AGENT_WORKFLOW.md
├── BANKROLL_TIER_SYSTEM.md
├── DOC_SYNC_PROCEDURE.md
├── EVENT_DRIVEN_EXECUTABLE_LIQUIDITY_ADMISSION_PLAN.md
├── KNOWN_ISSUES.md               ← canonical; root KNOWN_ISSUES.md is a stub pointing here
├── OBSERVABILITY_PLAN.md
├── PAPER_TRADING_RUNBOOK.md
├── PROJECT_CLEANUP_REPORT.md
├── PROJECT_STRUCTURE.md          ← canonical; root PROJECT_STRUCTURE.md is a stub pointing here
└── quant_agent_setup_md/
    ├── roles/ (23 role docs)
    ├── playbooks/ (3 docs)
    └── templates/ (1 doc)
```

The stub pattern (`PROJECT_STRUCTURE.md` and `KNOWN_ISSUES.md` at root forwarding to `docs/`) is **already proven working** and is the recommended model for any future migrations.

---

## 3. File Classification and Migration Determination

### KEEP_AT_ROOT — Hard blocked or critical path

| File | Reason | Verdict |
|---|---|---|
| `CLAUDE.md` | Claude Code auto-loader — platform requirement | **KEEP_AT_ROOT** |
| `AGENTS.md` | Codex auto-loader — platform requirement | **KEEP_AT_ROOT** |
| `README.md` | GitHub renders root README — web convention | **KEEP_AT_ROOT** |
| `CODEX_START_HERE.md` | Read-first #1, 34 .md cross-refs, bootstrap entry | **KEEP_AT_ROOT** |
| `PROJECT_RULES.md` | Read-first sequence, 49 .md cross-refs | **KEEP_AT_ROOT** |
| `MASTER_AGENT_ROUTER.md` | Read-first sequence, 56 .md cross-refs | **KEEP_AT_ROOT** |
| `CURRENT_PROJECT_STATUS.md` | Read-first sequence, 62 .md cross-refs, largest file | **KEEP_AT_ROOT** |
| `FILE_INDEX.md` | Read-first sequence, 47 .md cross-refs | **KEEP_AT_ROOT** |
| `DOCUMENTATION_MAP.md` | Navigation hub, 23 .md cross-refs | **KEEP_AT_ROOT** |
| `QUANT_FUTURE_DECISION_ENGINE.md` | Read-first sequence, 32 .md cross-refs | **KEEP_AT_ROOT** |
| `PROJECT_STRUCTURE.md` | Root stub → docs/; already the correct pattern | **KEEP_AT_ROOT** (stub) |
| `KNOWN_ISSUES.md` | Root stub → docs/; already the correct pattern | **KEEP_AT_ROOT** (stub) |

**Total: 12 files must stay at root. These define the agent bootstrap surface.**

### SAFE_TO_MOVE — quant_core/

These files are research/design specifications referenced 9-15× in .md files. They are referenced inside longer "also read" lists, not in the mandatory read-first sequence. Moves are safe with a root redirect stub.

| File | Target Path | Stub Needed |
|---|---|---|
| `QUANT_LIFECYCLE_INVENTORY_ENGINE.md` | `docs/quant_core/QUANT_LIFECYCLE_INVENTORY_ENGINE.md` | Yes |
| `QUANT_REGIME_PROBABILITY_ENGINE.md` | `docs/quant_core/QUANT_REGIME_PROBABILITY_ENGINE.md` | Yes |
| `BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md` | `docs/quant_core/BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md` | Yes |
| `INVENTORY_REPLAY_RESEARCH_PLAN.md` | `docs/quant_core/INVENTORY_REPLAY_RESEARCH_PLAN.md` | Yes |
| `MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md` | `docs/quant_core/MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md` | Yes |

**5 files. Risk: LOW. Stub pattern already proven.**

### SAFE_TO_MOVE — project/

Startup prompts and deployment notes referenced only 4-6× as "use this when" resources, not in the mandatory bootstrap sequence.

| File | Target Path | Stub Needed |
|---|---|---|
| `CHATGPT_PROJECT_START_PROMPT.md` | `docs/project/CHATGPT_PROJECT_START_PROMPT.md` | Recommended |
| `CODEX_START_PROMPT.md` | `docs/project/CODEX_START_PROMPT.md` | Recommended |
| `VULTR_PAPER_RUN.md` | `docs/project/VULTR_PAPER_RUN.md` | Optional |

**3 files. Risk: LOW.**

### SAFE_TO_MOVE — research/sessions/ (0 references)

These three files were generated during the current session as operational analysis artifacts. They have zero cross-references anywhere in the repo. They belong in `research/` alongside the existing `research/session_memory_template.md` and `research/daily/` structure.

| File | Target Path | Stub Needed |
|---|---|---|
| `late_window_cutoff_diagnosis_2026-05-17.md` | `research/sessions/2026-05-17/late_window_cutoff_diagnosis.md` | No |
| `research_cockpit_live_validation.md` | `research/sessions/2026-05-17/research_cockpit_live_validation.md` | No |
| `research_cockpit_runtime_observation_2026-05-17.md` | `research/sessions/2026-05-17/research_cockpit_runtime_observation.md` | No |

**3 files. Risk: NONE. Zero dependencies.**

### ARCHIVE — dated audit artifacts

These two files are historical working documents from 2026-05-14 that were never merged into canonical docs. Their content should be absorbed into `docs/KNOWN_ISSUES.md` and `docs/PROJECT_CLEANUP_REPORT.md` respectively, then the originals archived.

| File | Target Path | Action |
|---|---|---|
| `DOC_TRUTH_RECONCILIATION_2026-05-14.md` | `archive/legacy/docs/2026-05-14-doc-truth-recon.md` | Archive (content absorbed or superseded) |
| `KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md` | `archive/legacy/docs/2026-05-14-known-issues-tickets.md` | Archive (merge ticket content into docs/KNOWN_ISSUES.md first) |

**2 files. Risk: LOW if content verified first.**

---

## 4. Recommended `docs/` Target Tree

```
docs/
├── project/
│   ├── CHATGPT_PROJECT_START_PROMPT.md   ← moved from root
│   ├── CODEX_START_PROMPT.md             ← moved from root
│   └── VULTR_PAPER_RUN.md                ← moved from root
├── quant_core/
│   ├── QUANT_LIFECYCLE_INVENTORY_ENGINE.md    ← moved from root
│   ├── QUANT_REGIME_PROBABILITY_ENGINE.md     ← moved from root
│   ├── BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md ← moved from root
│   ├── INVENTORY_REPLAY_RESEARCH_PLAN.md      ← moved from root
│   └── MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md ← moved from root
├── agent_system/                          ← future: move role docs here if desired
│   └── (quant_agent_setup_md/ stays as-is for now)
├── issues/                                ← new subfolder
│   └── (absorb KNOWN_ISSUES_NEW_TICKETS content)
├── AGENT_WORKFLOW.md                      ← already here
├── BANKROLL_TIER_SYSTEM.md                ← already here
├── DOC_SYNC_PROCEDURE.md                  ← already here
├── EVENT_DRIVEN_EXECUTABLE_LIQUIDITY_ADMISSION_PLAN.md ← already here
├── KNOWN_ISSUES.md                        ← already here (canonical)
├── OBSERVABILITY_PLAN.md                  ← already here
├── PAPER_TRADING_RUNBOOK.md               ← already here
├── PROJECT_CLEANUP_REPORT.md              ← already here
├── PROJECT_STRUCTURE.md                   ← already here (canonical)
└── quant_agent_setup_md/                  ← stays as-is
    ├── roles/                             ← all 23 role docs stay here
    ├── playbooks/
    └── templates/

research/
├── sessions/
│   └── 2026-05-17/
│       ├── late_window_cutoff_diagnosis.md         ← moved from root
│       ├── research_cockpit_live_validation.md      ← moved from root
│       └── research_cockpit_runtime_observation.md  ← moved from root
├── session_memory_template.md             ← already here
├── replay_policy_registry.json            ← already here
├── REPLAY_POLICY_NAMING_DRIFT.md          ← already here
└── daily/                                 ← already here

archive/legacy/docs/
└── 2026-05-14-doc-truth-recon.md          ← archived from root
└── 2026-05-14-known-issues-tickets.md     ← archived from root
```

---

## 5. Redirect Stub Strategy

The existing stub pattern (`PROJECT_STRUCTURE.md` and `KNOWN_ISSUES.md` at root) is the proven model. For any file moved from root to `docs/`, leave a 3-line redirect stub at the root path:

```markdown
# [File Title]

This document has moved to `docs/quant_core/[FILENAME].md`.
Read that file for current content.

This root-level stub exists so agents following the read-first order do not get a 404.
```

**Stub files needed:** 5 quant_core files, 2-3 project files (8 total)

No stub needed for the 3 research session files (0 references, no agent reads them by name in any prompt).

No stub needed for the 2 archived files (historical, not in any read sequence).

---

## 6. Migration Phases (Recommended Order)

### Phase 0 — Before any moves: Verify stubs work
1. Confirm `PROJECT_STRUCTURE.md` stub is correctly read by agents (already working)
2. Confirm `KNOWN_ISSUES.md` stub is correctly read by agents (already working)
3. Update `DOCUMENTATION_MAP.md` and `FILE_INDEX.md` to show new target paths alongside root stubs

### Phase 1 — Zero-reference files (no risk, no stubs needed) ✅ COMPLETE 2026-05-17
**Batch 1A: Session analysis files → docs/research/sessions/2026-05-17/**
- ✅ Moved: `late_window_cutoff_diagnosis_2026-05-17.md`
- ✅ Moved: `research_cockpit_live_validation.md`
- ✅ Moved: `research_cockpit_runtime_observation_2026-05-17.md`

**Batch 1B: Dated audit archives → archive/legacy/docs/**
- Merge ticket content from `KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md` into `docs/KNOWN_ISSUES.md` (operator review required)
- Archive: `DOC_TRUTH_RECONCILIATION_2026-05-14.md`
- Archive: `KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md`

### Phase 2 — Low-reference files (stubs recommended)
**Batch 2A: Startup prompts → docs/project/**
- Move: `CHATGPT_PROJECT_START_PROMPT.md`
- Move: `CODEX_START_PROMPT.md`
- Move: `VULTR_PAPER_RUN.md`
- Create stubs at root for each (or update `DOCUMENTATION_MAP.md` to reflect new paths)

### Phase 3 — Quant-core design docs (stubs required)
**Batch 3A: Research/design plans → docs/quant_core/**
- Move: `BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md`
- Move: `INVENTORY_REPLAY_RESEARCH_PLAN.md`
- Move: `MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md`
- Move: `QUANT_REGIME_PROBABILITY_ENGINE.md`

**Batch 3B: Future system spec (highest reference count in this group)**
- Move: `QUANT_LIFECYCLE_INVENTORY_ENGINE.md`
- Create stub at root

For each: create root redirect stub, then update `CODEX_START_HERE.md` "also read" list and `DOCUMENTATION_MAP.md` to point to `docs/quant_core/`.

### Phase 4 — Navigation entrypoint upgrade (optional)
- Promote `DOCUMENTATION_MAP.md` as the canonical navigation entrypoint
- Add `docs/quant_core/` section to `FILE_INDEX.md`
- Update all role docs' "also read" links to new `docs/quant_core/` paths

---

## 7. DOCUMENTATION_MAP.md and FILE_INDEX.md — Should They Be Canonical?

**Recommendation: Yes, with distinct roles.**

| File | Recommended Role |
|---|---|
| `DOCUMENTATION_MAP.md` | **Human/AI navigation hub.** Canonical map of where everything lives. Already contains the read-first order and links to all categories. Promote as the single place to update when files move. |
| `FILE_INDEX.md` | **Operational quick-lookup.** Canonical table of runtime files, test files, roles, and tool files. Keep runtime-code focused. Add a `docs/` section when quant_core files move. |

Both files should remain at root. They are already in the mandatory read-first sequence. Neither should move.

---

## 8. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Agents break if bootstrap files move | CRITICAL | Never move the 9 read-first files or 3 platform auto-loaders |
| Root stubs become stale | MEDIUM | Update DOCUMENTATION_MAP.md alongside every move |
| `CODEX_START_HERE.md` "also read" list outdated | MEDIUM | Update list in Phase 3 when quant_core files move |
| Merge loss for dated ticket files | MEDIUM | Review and merge KNOWN_ISSUES_NEW_TICKETS before archiving |
| Session files referenced in a future user prompt | LOW | They are in VALIDATION_LOG.md and memory, not in code |
| docs/quant_core/ creates a new "also read" burden | LOW | Limit to 5 files; DOCUMENTATION_MAP.md absorbs the update |

---

## 9. Rollback Plan

All Phase 1 moves (session analysis files, dated audit archives) are trivially reversible: `git mv` the files back to root. The 3 session analysis files have zero references — rollback is a single move with no link repairs.

All Phase 2–3 moves require:
1. Moving the file back to root: `git mv docs/quant_core/FILE.md FILE.md`
2. Deleting the root stub
3. Reverting any `DOCUMENTATION_MAP.md` / `CODEX_START_HERE.md` link changes

All changes are Markdown-only — no Python code, no test fixtures, no CI pipelines to revert. Full rollback is always one `git revert` away.

---

## 10. Files Recommended NOT to Move (Ever)

| File | Reason |
|---|---|
| `AGENTS.md` | GitHub Copilot / Codex platform auto-loader — root only |
| `CLAUDE.md` | Claude Code auto-loader — root only |
| `README.md` | GitHub root convention — root only |
| `CODEX_START_HERE.md` | Read-first #1 — 34 .md refs in prompt sequences |
| `PROJECT_RULES.md` | Core rules — 49 .md refs |
| `MASTER_AGENT_ROUTER.md` | Agent routing — 56 .md refs |
| `CURRENT_PROJECT_STATUS.md` | Project truth — 62 .md refs |
| `FILE_INDEX.md` | Quick map — 47 .md refs |
| `DOCUMENTATION_MAP.md` | Navigation hub — 23 .md refs |
| `QUANT_FUTURE_DECISION_ENGINE.md` | Read-first sequence — 32 .md refs |
| `PROJECT_STRUCTURE.md` | Root stub — part of established pattern |
| `KNOWN_ISSUES.md` | Root stub — part of established pattern |

---

## 11. Summary

| Category | Count | Verdict |
|---|---|---|
| KEEP_AT_ROOT (hard blocked) | 12 | Never move |
| SAFE_TO_MOVE — research/sessions/ | 3 | Move immediately, Phase 1, no stubs |
| SAFE_TO_MOVE — archive | 2 | Archive after content review, Phase 1 |
| SAFE_TO_MOVE — docs/project/ | 3 | Move with stubs, Phase 2 |
| SAFE_TO_MOVE — docs/quant_core/ | 5 | Move with stubs, Phase 3 |
| **Total root files** | **25** | — |

**Recommended first move batch (Phase 1A — zero risk, operator can approve immediately):**
- `late_window_cutoff_diagnosis_2026-05-17.md` → `research/sessions/2026-05-17/`
- `research_cockpit_live_validation.md` → `research/sessions/2026-05-17/`
- `research_cockpit_runtime_observation_2026-05-17.md` → `research/sessions/2026-05-17/`

These three files have zero cross-references, zero prompt dependencies, and zero platform loader impact. They are the cleanest possible starting point for any migration.

---

*Audit only. No files moved. No runtime logic changed. No tests run.*
*Runtime behavior changed: No. Live behavior changed: No.*
