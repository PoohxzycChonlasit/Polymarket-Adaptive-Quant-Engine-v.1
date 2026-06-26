# IMPLEMENTATION PLAN — PATCH_OBSERVABILITY_001_OPERATOR_VISIBILITY

This document outlines the implementation plan and explicit answers to governance and safety questions for the operator visibility patch.

---

## Explicit Answers to Governance Questions

1. **Exact files required**:
   - [polymarket/trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py) (pipeline metrics, risk state mapping)
   - [utils/display.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/display.py) (dashboard panels rendering)
   - [utils/telegram_alerts.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/telegram_alerts.py) (ALIVE alert template formatting)
   - [main.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/main.py) (heartbeat tracking data flow)

2. **Exact telemetry required**:
   - Candidates, Orderbook Pass, Confidence Pass, EV Pass, Delta Pass, Risk Size Pass, and Trade Open progression checks.
   - Session-level skipped reasons counter for resolving the Top Blocker.

3. **Whether any new counters are needed**:
   - Yes, the 7 funnel counters listed in the design.

4. **Whether PaperSessionStats must change**:
   - Yes, add the 7 fields as `int` properties initialized to `0`.

5. **Expected dashboard layout changes**:
   - Replace the `_candidate_observability_panel` with the new `_entry_funnel_panel` in the bottom row across standard, compact, and wide layouts.

6. **Expected Telegram format changes**:
   - Restructure `_operator_summary_message(context)` to construct the sectioned heartbeat when `uptime` is provided.

7. **Required tests**:
   - `tests/test_terminal_dashboard_display.py` (funnel rendering and risk explanations)
   - `tests/test_runtime_telegram_summary.py` (ALIVE heartbeat template assertions)

8. **Rollback plan**:
   - `git checkout -- polymarket/trader.py utils/display.py utils/telegram_alerts.py main.py`

9. **Safety analysis**:
   - High safety. Telemetry variables are added in-memory and rendered passively. No changes to execution routes, ordering APIs, or risk limits.

10. **Estimated implementation complexity**:
    - Low. Passively increments counters and reformats output string templates.

---

## Proposed Changes

### Component: Metrics and Telemetry Sourcing
#### [MODIFY] [trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py)
- Update `PaperSessionStats` with the 7 funnel counters.
- Increment counters at the end of `_analyze_market_quant()`.
- Add `consecutive_losses` to `dashboard_portfolio_state()` and `dashboard_session_summary()`.
- Expose the top skipped reason as `top_blocker` in `dashboard_v2a_stats()`.

### Component: Terminal Dashboard Rendering
#### [MODIFY] [display.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/display.py)
- Implement `_entry_funnel_panel(self, spec: DashboardLayout) -> Panel`.
- Update `_risk_panel` with human-readable mode reasons and exits.
- Modify `_render()` to split the layout and insert the new panels.

### Component: Telegram Heartbeats
#### [MODIFY] [telegram_alerts.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/telegram_alerts.py)
- Update `_operator_summary_message(context)` to build the redesigned ALIVE message layout.

---

## Verification Plan

### Automated Tests
```bash
python -m pytest tests/test_terminal_dashboard_display.py -q
python -m pytest tests/test_runtime_telegram_summary.py -q
```

### Manual Verification
1. Run the bot in paper mode:
   ```bash
   python main.py
   ```
2. Verify the console dashboard displays the new panels.
3. Check the Telegram alerts to verify the formatting of the summary.

---

## Final Verdict

**APPROVE_OPERATOR_VISIBILITY_PATCH**
