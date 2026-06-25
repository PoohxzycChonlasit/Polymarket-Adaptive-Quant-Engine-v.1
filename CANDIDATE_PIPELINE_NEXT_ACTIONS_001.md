# CANDIDATE_PIPELINE_NEXT_ACTIONS_001
**Mode: VALIDATION / DISCOVERY ONLY**
**Date: 2026-06-25**
**Applies to: post-HOTFIX_PARTIAL pipeline state**

---

## Current Pipeline Status

**VERDICT: PIPELINE_REACHES_SIZING**

The candidate pipeline now delivers candidates through the sizing gate and into paper execution. The position sizing hotfix was exercised by the runtime and produced a confirmed paper order at exactly the $0.10 minimum floor.

---

## What Changed (Do Not Touch)

- `utils/risk_manager.py`: `build_micro_survival_risk_plan()` minimum floor logic (hotfix, uncommitted)
- `polymarket/trader.py`: `_micro_survival_max_position_size()` minimum floor logic (hotfix, uncommitted)
- `polymarket/trader.py`: `_emit_zero_size_probe_event()` now receives `side_win_rate` for richer observability

Do not revert these changes. Do not modify sizing, probability, EV, or strategy logic.

---

## Three-Option Rule (Next Actions)

### OPTION 1 — SAFE EV PRESERVATION (Recommended)
Commit the hotfix. Monitor the paper pipeline over 3–5 sessions to accumulate enough candidates reaching sizing to validate the micro survival floor behavior statistically. Continue Phase 1 paper evidence collection.

**Steps**:
1. Commit the working-tree hotfix (`utils/risk_manager.py` + `polymarket/trader.py`)
2. Run 3–5 60-minute paper sessions using `python main.py --mode paper --interval 60`
3. After each session run: `python tools/no_entry_analyzer.py --date YYYY-MM-DD --run-id RUN_ID --write-report`
4. Compare `risk_plan_zero` count and `entered_count` across sessions
5. Investigate and resolve `exit_submit_failed: 8` (exit submission failures)
6. Investigate `risk_mode_lockdown:reconciliation_mismatch` from ghost early sessions
7. Do NOT modify delta_extreme threshold, confidence floors, EV threshold, or risk sizing

**EV preservation**: all conservative gates remain. The only change is enforcing the minimum floor already present in the code.

### OPTION 2 — AGGRESSIVE INFORMATION DISCOVERY
Extend paper sessions to multiple hours and instrument the `_emit_zero_size_probe_event` with the new `side_win_rate` field to study the 2 remaining `risk_plan_zero` events — specifically which confidence/EV combinations fail even the micro survival path.

**Steps**:
1. Run a 2–4 hour paper session (leaving terminal running, not via Bash tool)
2. Use the new `side_win_rate` observability field to classify the 2 remaining sizing failures
3. Check whether they share a pattern (e.g., confidence < 0.50, EV < 0.02)
4. Do NOT use this evidence to loosen the micro survival rescue condition without explicit scope

**Risk**: this may show micro survival is already well-tuned. Low behavioral risk.

### OPTION 3 — STRUCTURAL / ROOT-CAUSE PATH
Investigate the `exit_submit_failed: 8` issue and the `reconciliation_mismatch` ghost state. These suggest the position lifecycle after entry (exits, reconciliation) has gaps that could affect future multi-entry or Phase 2 inventory replay work.

**Steps**:
1. Inspect execution_log for `exit_submit_failed` events — identify which position, asset, epoch, and reason
2. Inspect `risk_mode_lockdown:reconciliation_mismatch` events from the 04:50 UTC session — confirm they are from a ghost lifecycle state, not a runtime bug in the 06:19 session
3. If exit failures are structural, open a scoped task for exit path hardening
4. If reconciliation_mismatch is from probe session restart artifact, document and close

---

## Recommended Action

**OPTION 1** — commit the hotfix and monitor.

**Do immediately (minimal)**:
1. Commit the two hotfix changes to git with a clear message referencing HOTFIX_PARTIAL and this report
2. Update CURRENT_PROJECT_STATUS.md to reflect PIPELINE_REACHES_SIZING status
3. Investigate `exit_submit_failed: 8` in a targeted read-only pass before the next session

**Do in next scoped tasks (sequenced)**:
1. **Sizing Floor Verification Task**: accumulate evidence from 3–5 sessions; confirm `notional_size >= 0.10` is consistent
2. **Exit Path Audit Task**: root-cause `exit_submit_failed` — separate from sizing validation
3. **Reconciliation Mismatch Task**: clarify ghost session state; confirm it does not affect clean restarts
4. **Phase 2 Readiness Task**: once entry funnel is consistently validated, begin paper-only replay analysis

---

## Remaining Risks

| Risk                              | Severity | Notes                                                        |
|-----------------------------------|----------|--------------------------------------------------------------|
| exit_submit_failed: 8             | MEDIUM   | Exit orders failing at submission; needs root cause          |
| reconciliation_mismatch (4 events)| LOW      | From ghost early session; not from the primary validated run |
| delta_extreme blocks 30%          | LOW-MEDIUM | Known; protective; no action without backtest evidence     |
| 2 remaining risk_plan_zero events | LOW      | Correct behavior — ultra-low confidence/EV candidates        |
| Single paper trade (N=1)          | MEDIUM   | Need more sessions to confirm consistency; not a regression  |

---

## Files Not to Touch

- Strategy modules: `polymarket/signal.py`, `polymarket/probability_model.py`, `polymarket/expected_value.py`
- Risk thresholds: confidence floors, EV threshold, delta extreme threshold
- Sizing cap logic beyond the hotfix already applied
- Live mode flags, wallet/signing code
- Paper/live separation

---

## Completion Gate

This validation task is complete when:
- [x] Verify mode confirms BTC/ETH orderbook OK
- [x] Paper session produces at least 1 candidate reaching sizing
- [x] Paper order created at notional >= $0.10
- [x] Funnel evidence documented
- [x] First-blocking gate distribution produced
- [ ] Hotfix committed to git (NEXT ACTION — not part of VALIDATION scope)
- [ ] Exit path failures investigated (NEXT TASK)
