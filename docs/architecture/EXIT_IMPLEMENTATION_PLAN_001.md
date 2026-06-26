# EXIT_IMPLEMENTATION_PLAN_001
**Mode: DISCOVERY ONLY — Implementation Plan Only, No Code Changes**
**Date: 2026-06-25**
**Derived from: EXIT_EXECUTION_ROOT_CAUSE_AUDIT_001.md + EXIT_LIFECYCLE_TRACE_001.md + EXIT_FAILURE_DISTRIBUTION_001.md**

---

## Situation

The exit pipeline is **working correctly in production**. Zero exit failures in the primary session. The 8 `exit_submit_failed` events are ghost artifacts from test/scratch activity on June 24 — they are non-recurring under normal paper operation.

**Nothing is blocking Phase 1 paper evidence collection.**

This plan is structured as a Three-Option Rule per the role doc format. All options are future work and require explicit scope approval before implementation.

---

## Three-Option Rule

### OPTION 1 — MINIMAL SENTINEL (Recommended)

**Summary**: Add a startup check that identifies and skips test-placeholder positions. No behavioral change for production positions.

**Trigger for implementation**: Recurrence of `exit_submit_failed` in any future session, OR before Phase 2 (replay analysis) begins.

**Scope**:
- `polymarket/trader.py`: In the startup state validation path, add a check for `token_id: "yes-token"` or any token_id matching known test placeholder patterns
- If found, emit a `startup_ghost_position_detected` event and remove from tracker (do not attempt exit)
- Zero change to exit logic, retry logic, or production position handling

**Effort**: ~10 lines
**Risk**: Minimal — only affects positions with explicitly-identified test token strings
**Unblocks**: Cleaner execution logs, no ghost exits in future sessions

**Steps**:
1. Identify the startup initialization path in `polymarket/trader.py` where positions are first loaded (if any) or where the first cycle begins
2. Add: `if token_id in KNOWN_TEST_PLACEHOLDERS: emit warning, skip`
3. Define `KNOWN_TEST_PLACEHOLDERS = {"yes-token", "no-token"}` as a module constant
4. Write targeted test confirming ghost positions are skipped and real positions are unaffected

---

### OPTION 2 — FULL GHOST STATE HARDENING

**Summary**: Enforce token_id format validation at the order_intent layer. Reject any exit order where `token_id` does not match the expected Polymarket token format (hex string, 66 chars).

**Trigger for implementation**: Before live mode activation (Phase 4 readiness gate).

**Scope**:
- `polymarket/order_intent.py`: Add `token_id` format validation to `validate_order_intent`
- `polymarket/trader.py`: Add lifecycle_phase guard — skip forced exits if `lifecycle_phase == "UNKNOWN"` at startup
- Add `close_order_retry_delay_seconds` minimum enforcement (warn if < 0.1s)

**Effort**: ~25 lines across 2 files
**Risk**: Low — only rejects orders that would fail anyway (invalid token_ids cannot fill on CLOB or paper)
**Unblocks**: Production hardening, cleaner live-mode safety profile

**Steps**:
1. Define Polymarket token format: 66-character hex string starting with `"0x"`
2. Add format check to `validate_order_intent` for EXIT orders: `if not re.match(r'^0x[0-9a-f]{64}$', token_id): reject("invalid_token_id_format")`
3. Add startup `lifecycle_phase` guard: `if pos.lifecycle_phase == "UNKNOWN": skip forced exit, log warning`
4. Write tests for both new validation paths

---

### OPTION 3 — STRUCTURAL: TEST ISOLATION ENFORCEMENT

**Summary**: Prevent test/scratch code from using the production runtime environment. Enforce isolation via environment flags.

**Trigger for implementation**: Before any team expansion or CI/CD integration; or if another ghost-state incident occurs.

**Scope**:
- `scratch/bounded_runtime_validation.py`: Add `ALLOW_PRODUCTION_RUNTIME=false` guard; fail loudly if production settings are passed
- `config/settings.py`: Add `runtime_mode: Literal["production", "test", "scratch"]` field; paper/live modes reject `test` or `scratch` runtime_mode
- `utils/position_tracker.py`: In `open_position`, if `runtime_mode != "production"` and `token_id` matches known test placeholders, emit a loud warning

**Effort**: ~40 lines across 3 files
**Risk**: Low for enforcement; medium for structural change (requires testing all modes)
**Unblocks**: Clean separation between test activity and production runtime; safe for multi-developer or CI use

**Steps**:
1. Add `runtime_mode` to `config/settings.py` with default `"production"`
2. Add runtime_mode check to `PolymarketTrader.__init__` — warn if mode mismatch
3. Update `scratch/bounded_runtime_validation.py` to set `runtime_mode="scratch"` and confirm it cannot interact with production tracker
4. Write integration test confirming scratch mode does not pollute production state

---

## Recommended Sequence

| Priority | Option | When | Blocking? |
|---|---|---|---|
| 0 | None — current pipeline is fine | Now | No blocker |
| 1 | OPTION 1 (minimal sentinel) | Before Phase 2 begins | No |
| 2 | OPTION 2 (token format validation) | Before live mode gate | No |
| 3 | OPTION 3 (test isolation) | Before team expansion or CI | No |

---

## Files Involved

| File | Option 1 | Option 2 | Option 3 |
|---|---|---|---|
| `polymarket/trader.py` | startup ghost check | lifecycle_phase guard | runtime_mode check |
| `polymarket/order_intent.py` | — | token_id format validation | — |
| `config/settings.py` | — | delay min enforcement | `runtime_mode` field |
| `scratch/bounded_runtime_validation.py` | — | — | isolation guard |
| `utils/position_tracker.py` | — | — | test placeholder warning |

---

## Files NOT to Touch

- `polymarket/signal.py`, `polymarket/probability_model.py`, `polymarket/expected_value.py`
- Risk thresholds (confidence floors, EV, delta_extreme)
- Sizing logic (hotfix already validated)
- `close_order_retry_attempts` (3 is correct — attempt 3 succeeds)
- Paper/live separation
- Exit retry loop structure

---

## Completion Gate for This Audit

- [x] All 8 `exit_submit_failed` root-caused to ghost sessions
- [x] Primary session confirmed zero exit failures
- [x] Exit lifecycle fully traced (PATH A and PATH B)
- [x] PnL corruption scoped to ghost PIDs only
- [x] No code changed
- [x] Four output documents created
- [ ] OPTION 1 implementation (future scope, not this task)
