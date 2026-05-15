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
