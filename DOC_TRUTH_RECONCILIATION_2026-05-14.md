# Documentation Truth Reconciliation - 2026-05-14

> Purpose: Identify and resolve documentation inconsistencies across PolyTrade Bot project docs before starting any new feature phase.
> Scope: Documentation only. No runtime, strategy, risk, or execution behavior changes.
> Status: Review document. Apply diffs manually after operator verification.
> Author: Strategic review pass per `AGENTS.md` Documentation Sync Rule.

---

## Summary

Six documentation inconsistencies were identified across the project's canonical documentation set. None of them block runtime safety, but all of them cause AI assistants (Codex, Claude, ChatGPT) to receive conflicting context, which compounds drift over time.

This document:

1. Lists each inconsistency with evidence.
2. Recommends a resolution direction.
3. Proposes the minimum diff for each affected file.
4. Provides a verification checklist after applying diffs.

The recommended resolution path for every issue is **align documentation to verified code reality**, not the other way around. If filesystem verification is not possible during this pass, mark the field as `pending_filesystem_verification` and resolve in a follow-up commit.

---

## INC-001 - `polymarket/expected_value.py` referenced inconsistently

### Evidence

- `CLAUDE.md` line 51 lists `polymarket/expected_value.py` under "Signals & alpha".
- `FILE_INDEX.md` Polymarket Core section does NOT list `polymarket/expected_value.py`.
- `AGENTS.md` Active Files section does NOT list `polymarket/expected_value.py`.

### Risk

- AI assistants reading `FILE_INDEX.md` or `AGENTS.md` will not know the file exists.
- AI assistants reading `CLAUDE.md` will assume the file is canonical.
- EV-related work could fragment between `polymarket/signal.py`, `polymarket/probability_model.py`, and `polymarket/expected_value.py` because no single doc owns the boundary.

### Resolution

Operator must verify in filesystem first:

```bash
ls -la polymarket/expected_value.py
```

Then choose one of three outcomes:

1. File exists and is canonical -> add it to `FILE_INDEX.md` and `AGENTS.md` Active Files.
2. File exists but is experimental -> add it to `FILE_INDEX.md` under "Secondary Or Experimental Areas" and remove from `CLAUDE.md` "Signals & alpha" group.
3. File does not exist -> remove from `CLAUDE.md`.

### Proposed diff if outcome is option 1 (file is canonical)

In `FILE_INDEX.md` under `## Polymarket Core`, add after the `probability_model.py` row:

```markdown
| `polymarket/expected_value.py` | Expected value calculation from probability, price, and cost inputs. |
```

In `AGENTS.md` under `## Active Files`, add after the `probability_model` row (note: probability_model is also missing from `AGENTS.md` -- see INC-005):

```markdown
| `polymarket/expected_value.py`     | EV calculation from probability/price/cost.                 |
```

### Owner

Anyone with filesystem access. Estimated effort: 5 minutes.

---

## INC-002 - `polymarket/position_manager.py` referenced inconsistently

### Evidence

- `CLAUDE.md` line 55 lists `polymarket/position_manager.py` under "Reconciliation".
- `FILE_INDEX.md` does NOT list `polymarket/position_manager.py` anywhere.
- `AGENTS.md` Active Files does NOT list `polymarket/position_manager.py`.
- `CURRENT_PROJECT_STATUS.md` "Important project areas" section does NOT list it.

### Risk

- Reconciliation work has ambiguous ownership. Is `utils/position_tracker.py` canonical or is `polymarket/position_manager.py` canonical?
- Position reconciliation is a live-readiness blocker (LIVE-002). Ambiguity here is high-impact when live validation begins.

### Resolution

Verify filesystem first:

```bash
ls -la polymarket/position_manager.py
```

Then:

1. If file exists -> document its relationship to `utils/position_tracker.py` explicitly. They should not duplicate responsibility.
2. If file does not exist -> remove from `CLAUDE.md`.

If both exist, the canonical division must be one of:

- `utils/position_tracker.py` owns in-memory position state and drawdown math.
- `polymarket/position_manager.py` owns reconciliation against CLOB live order/fill state.

Document this division in `docs/PROJECT_STRUCTURE.md` once verified.

### Proposed diff if outcome confirms both files exist

In `FILE_INDEX.md` under `## Polymarket Core`, add a new row:

```markdown
| `polymarket/position_manager.py` | Reconciliation against live CLOB order/fill state. Distinct from `utils/position_tracker.py` which owns in-memory state. |
```

In `AGENTS.md` Active Files, add:

```markdown
| `polymarket/position_manager.py`   | Live order/fill reconciliation; distinct from in-memory tracker. |
```

### Owner

Whoever owns LIVE-002 unblock work. Estimated effort: 15 minutes including filesystem inspection.

---

## INC-003 - Telegram alert helper list disagrees between docs

### Evidence

- `KNOWN_ISSUES.md` OBS-003 lists: `notify_startup`, `notify_entry`, `notify_exit`, `notify_risk`, `notify_critical`, `notify_summary`, `notify_incident`.
- `CURRENT_PROJECT_STATUS.md` line 79 lists: `notify_entry`, `notify_exit`, `notify_risk`, `notify_critical`, `notify_summary`, `notify_incident` (no `notify_startup`).

### Risk

- Telegram observability work could miss `notify_startup` routing if the assistant reads `CURRENT_PROJECT_STATUS.md` only.
- Conversely, if `notify_startup` was never actually implemented, `KNOWN_ISSUES.md` is overstating implementation status.

### Resolution

Verify in code:

```bash
grep -n "^def notify_" utils/telegram_alerts.py
```

Then align the doc that is wrong. Whichever list matches the code is the source of truth.

### Proposed diff (assuming KNOWN_ISSUES is correct)

In `CURRENT_PROJECT_STATUS.md` line 79, replace:

```text
- Clear trader Telegram sends were routed through centralized `notify_entry`, `notify_exit`, `notify_risk`, `notify_critical`, `notify_summary`, and `notify_incident` helpers where safe.
```

with:

```text
- Clear trader Telegram sends were routed through centralized `notify_startup`, `notify_entry`, `notify_exit`, `notify_risk`, `notify_critical`, `notify_summary`, and `notify_incident` helpers where safe.
```

### Owner

Anyone with code-grep access. Estimated effort: 5 minutes.

---

## INC-004 - `research/daily/YYYY-MM-DD.md` workflow is undefined

### Evidence

- `CURRENT_PROJECT_STATUS.md` line 536 instructs: "Read the latest real daily note in `research/daily/YYYY-MM-DD.md`."
- No other doc in the project references this folder, format, or workflow.
- `DOCUMENTATION_MAP.md`, `FILE_INDEX.md`, `AGENTS.md`, `CODEX_START_HERE.md`, and `PROJECT_RULES.md` do not mention it.
- `FILE_INDEX.md` "Generated Or Evidence Folders" section does not list `research/`.

### Risk

- Codex/Claude will try to read a folder that may not exist and fail silently.
- If the folder does exist but is undocumented, valuable daily research evidence is invisible to AI assistants.
- This is the only "single source of truth for current state" pointer that breaks the documented startup flow.

### Resolution

Verify filesystem first:

```bash
ls -la research/daily/ 2>/dev/null && echo "EXISTS" || echo "MISSING"
```

Three outcomes:

1. Folder exists and is in active use -> document it in `FILE_INDEX.md`, `DOCUMENTATION_MAP.md`, and `CODEX_START_HERE.md`. Add a daily note template.
2. Folder exists but is stale -> archive to `archive/legacy/research/` and remove the line from `CURRENT_PROJECT_STATUS.md`.
3. Folder does not exist -> remove the line from `CURRENT_PROJECT_STATUS.md` and replace with `runtime/research_state/latest_research_state.md` (which IS referenced in `CLAUDE.md` line 62).

### Proposed diff if outcome is option 3 (most likely)

In `CURRENT_PROJECT_STATUS.md` line 536, replace:

```text
2. Read the latest real daily note in `research/daily/YYYY-MM-DD.md`.
```

with:

```text
2. Read the latest research state snapshot in `runtime/research_state/latest_research_state.md`.
```

This aligns with the workflow in `CLAUDE.md` line 62.

### Owner

Project maintainer. Estimated effort: 10 minutes including filesystem check.

---

## INC-005 - `AGENTS.md` Active Files list is incomplete vs FILE_INDEX

### Evidence

`AGENTS.md` Active Files table is missing these files that `FILE_INDEX.md` documents as canonical:

- `polymarket/regime_diagnostics.py`
- `polymarket/probability_model.py`
- `polymarket/position_sizing.py`
- `utils/scan_log_loader.py`
- `utils/config_validator.py`
- `tools/no_entry_analyzer.py`
- `tools/session_runtime_evaluator.py`

### Risk

- Codex sessions that auto-load `AGENTS.md` (per its "auto-loaded" status) will not know about regime/probability/position-sizing/config-validation modules.
- This is the highest-impact inconsistency because `AGENTS.md` is the auto-loaded context for Codex.

### Resolution

Add the missing rows to `AGENTS.md` Active Files. Do not remove anything.

### Proposed diff

In `AGENTS.md` `## Active Files` table, add the following rows (insert in logical grouping):

After `polymarket/signal.py`:

```markdown
| `polymarket/regime_diagnostics.py` | Passive regime/probability diagnostics; not trade approval.  |
| `polymarket/probability_model.py`  | Probability model input/output path.                         |
```

After `polymarket/bankroll_tiers.py`:

```markdown
| `polymarket/position_sizing.py`    | Rank-aware position sizing calculation.                      |
```

After `utils/quant_event_logger.py`:

```markdown
| `utils/scan_log_loader.py`         | Shared reader for old and per-run realtime scan CSV files.   |
| `utils/config_validator.py`        | Startup config validation and secret-safe config summary.    |
```

After `tools/replay_analyzer.py`:

```markdown
| `tools/no_entry_analyzer.py`       | Offline no-entry paper session diagnostics.                  |
| `tools/session_runtime_evaluator.py` | Offline paper session health/bottleneck evaluator.         |
```

### Owner

Anyone with doc access. Estimated effort: 10 minutes.

---

## INC-006 - "Documentation Sync Rule" lacks concrete definition

### Evidence

- `AGENTS.md` line 25 says: "Before implementing any new feature phase, perform a documentation synchronization pass when docs are stale or when the user requests it."
- No doc defines what "documentation synchronization pass" means concretely. No checklist, no script, no verification gate.
- This rule was invoked successfully in 2026-05-08 (per `CURRENT_PROJECT_STATUS.md` line 118) but the procedure used was not captured.

### Risk

- Each AI assistant interprets "doc sync" differently. Some do nothing. Some over-rewrite. None reliably produces the same result.
- The current reconciliation pass (this document) is itself an example of the gap: there is no canonical procedure for what to check.

### Resolution

Add a concrete "Documentation Sync Checklist" to `AGENTS.md` or as a new file `docs/DOC_SYNC_PROCEDURE.md`.

### Proposed new file: `docs/DOC_SYNC_PROCEDURE.md`

```markdown
# Documentation Sync Procedure

> Purpose: Concrete steps for the Documentation Sync Rule referenced in `AGENTS.md`.
> Trigger: Before any new feature phase, or when operator requests it, or when doc drift is suspected.

## Checklist

1. Verify file references in canonical docs match filesystem.
   - `AGENTS.md` Active Files table
   - `FILE_INDEX.md` all sections
   - `CLAUDE.md` Key module groups
   - `CURRENT_PROJECT_STATUS.md` Important project areas

2. Verify cross-doc consistency for these items:
   - Telegram helper function list
   - Phase 1-4 roadmap wording
   - Live blocker list (LIVE-001, LIVE-002)
   - Implemented vs Partially implemented vs Planned labels
   - Lifecycle inventory vocabulary

3. Verify command examples are current:
   - Safe paper command
   - Explicit paper command
   - Verify command
   - Live command (must still be documented as blocked)
   - Test commands

4. Verify status timestamps:
   - `> Last synced:` lines must be within 30 days
   - `> Updated:` lines must be within 30 days

5. Open ticket in `KNOWN_ISSUES.md` for each inconsistency found. Do not silently fix.

6. Apply diffs only after operator review.

7. Run targeted tests if any doc-aligned change touches code:
   - `pytest -q tests/test_paper_mode.py`
   - `pytest -q tests/test_logging_resilience.py`
   - `pytest -q tests/test_execution_risk_controls.py`

## What this procedure does NOT do

- Does not change strategy, risk, execution, wallet, or live flag behavior.
- Does not delete files or move them to archive.
- Does not rewrite role docs in `docs/quant_agent_setup_md/roles/`.
- Does not promote planned features to implemented status.
```

### Proposed diff to `AGENTS.md`

In `AGENTS.md` line 25, append after the existing line:

```text
The concrete procedure for this sync is defined in `docs/DOC_SYNC_PROCEDURE.md`.
```

### Owner

Project maintainer. Estimated effort: 30 minutes to write the new file.

---

## Verification Checklist After Applying Diffs

Run this checklist after the diffs above are applied:

```bash
# 1. Confirm referenced files exist
ls -la polymarket/expected_value.py polymarket/position_manager.py 2>&1 | head

# 2. Confirm Telegram helpers match
grep -n "^def notify_" utils/telegram_alerts.py

# 3. Confirm research_state vs research/daily resolution
ls -la runtime/research_state/latest_research_state.md 2>&1 | head
ls -la research/daily/ 2>&1 | head

# 4. Confirm no test regression from doc-aligned changes (no code should change in this pass)
python -m pytest tests/test_paper_mode.py tests/test_logging_resilience.py -q

# 5. Re-grep for inconsistencies after fix
grep -l "expected_value" *.md docs/*.md 2>/dev/null
grep -l "position_manager" *.md docs/*.md 2>/dev/null
grep -l "research/daily" *.md docs/*.md 2>/dev/null
```

Expected after fix:

- All three `grep -l` searches should return a consistent set of files (no orphan references).
- No test regression.
- `git diff --stat` should show only `.md` file changes plus possibly one new `docs/DOC_SYNC_PROCEDURE.md`.

---

## Out Of Scope For This Pass

The following gaps were noted during reconciliation but are not part of doc-only fixing. They are tracked separately in `KNOWN_ISSUES_NEW_TICKETS_2026-05-14.md`:

- Decision JSONL schema is not versioned (SCHEMA-001)
- Log budget enforcement is missing (BUDGET-001)
- Allowance status is not exposed in runtime observability (OBS-005)
- No `tools/doc_truth_check.py` exists to automate future doc drift detection (TD-004)
- Lifecycle Latency Observatory v1 has no aggregator report tool (LIFECYCLE-001)
- JSONL events lack sampling policy (SAMPLING-001)

These are referenced here so the reader knows the full set of findings. They require code work, which this pass intentionally avoids.

---

## Boundaries Of This Document

This document does not:

- Authorize changes to strategy, risk, sizing, execution, wallet, or live flags.
- Authorize archiving any file.
- Authorize promotion of any planned feature to implemented status.
- Authorize disabling any test.
- Authorize loosening any safety rule in `PROJECT_RULES.md` or `AGENTS.md`.

This document only proposes documentation diffs. Operator review is required before any diff is applied.
