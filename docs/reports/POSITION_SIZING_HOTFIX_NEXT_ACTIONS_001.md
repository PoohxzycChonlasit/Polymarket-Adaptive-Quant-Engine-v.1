# POSITION_SIZING_HOTFIX_NEXT_ACTIONS_001
> Task: POSITION_SIZING_HOTFIX_RUNTIME_VALIDATION_001  
> Date: 2026-06-25  
> Current Verdict: **HOTFIX_PARTIAL**  
> Blocking: None — hotfix is correct and safe. No action required before continuing paper sessions.

---

## What Is Complete

| Item | Status |
|------|--------|
| `micro_survival_min_position_size = 0.10` in `config/settings.py` | ✅ Done |
| Math fix in `build_micro_survival_risk_plan` (`utils/risk_manager.py`) | ✅ Done |
| Math fix in `_micro_position_size` (`polymarket/trader.py` line 629) | ✅ Done |
| `side_win_rate` telemetry in zero-size probe events (`polymarket/trader.py`) | ✅ Done |
| 44/44 regression tests passing | ✅ Done |
| Paper mode safety confirmed | ✅ Done |
| Floor enforcement proven via direct Python test | ✅ Done |
| Pre-hotfix bug baseline documented | ✅ Done |
| `POSITION_SIZING_HOTFIX_RUNTIME_VALIDATION_001.md` | ✅ Written |
| `POSITION_SIZING_HOTFIX_EVIDENCE_SUMMARY_001.md` | ✅ Written |
| `POSITION_SIZING_HOTFIX_NEXT_ACTIONS_001.md` | ✅ This document |

---

## What Is Pending (HOTFIX_PARTIAL → HOTFIX_VALIDATED)

### P1 — Runtime Sizing Layer Exercise

The hotfix code path (floor rescue of `$0.05 → $0.10`) has not fired at runtime yet because all 3-cycle paper candidates were blocked before reaching the sizing gate.

**What to watch for** in future paper sessions:
- `zero_size_probe` JSONL events with `side_win_rate` field present
- `micro_position_size >= 0.10` in risk_log entries from a session where `micro_survival_active=True`
- No `micro_position_size < 0.10` entries in any post-hotfix run

**How to confirm** (offline, after a normal paper session):
```bash
python -c "
import json, pathlib
f = pathlib.Path('runtime/quant_data/risk_log/<TODAY>.jsonl')
broken = [(j.get('run_id'), p.get('micro_position_size')) 
          for line in open(f)
          for j in [json.loads(line)]
          for p in [j.get('payload', {})]
          if p.get('micro_survival_active') and p.get('micro_position_size', 1) < 0.10]
print('Floor violations:', len(broken), broken[:5])
"
```

**Expected result**: `Floor violations: 0 []`

### P2 — Data Quality (30 invalid_numeric lines)

Pre-existing issue. Not introduced by hotfix. To investigate separately:
```bash
python tools/quant_data_quality.py --date <TODAY> --verbose
```

Identify which fields are numeric-invalid and which run_id they belong to.

---

## What Is Out of Scope For This Task

These items were explicitly excluded and must **not** be pursued under this task:

| Item | Reason |
|------|--------|
| Strategy / probability model changes | Forbidden in task scope |
| EV model changes | Forbidden in task scope |
| Risk threshold changes | Forbidden in task scope |
| Sizing tuning beyond the $0.10 floor | Out of scope |
| Dashboard or UI changes | Out of scope |
| Live trading enablement | Out of scope |
| `.env` secrets modification | Out of scope |
| Committing / pushing changes | Out of scope (not requested) |
| Backtest re-run | Out of scope |

---

## Downstream Actions Now Unblocked

Now that the floor is enforced, the following Phase 2 research activities can proceed when the operator is ready:

### 1. Inventory Replay Research (Phase 2)

With correct sizing, paper-fill replays now produce valid notional figures. The previous `$0.05` floor-broken sizes would have inflated loss calculations in reload/unload analytics.

**Relevant tool**: `tools/replay_analyzer.py`

### 2. MFE/MAE Tracking

Position MAE and MFE calculations depend on correct position size. With the floor fixed, offline MFE/MAE metrics are now valid for MICRO_SURVIVAL entries.

### 3. Opportunity Decay Research

Frequency-cooldown and cutoff blocking analysis can now be done with confidence that any entry that *would* have been placed is sized correctly.

### 4. Monitoring in Longer Paper Sessions

The next extended paper session (≥30 cycles with live candidates) should naturally exercise the sizing path if market conditions allow. Key metrics to monitor:

```
risk_log: micro_position_size >= 0.10 when micro_survival_active=True
decision_log: zero_size_probe events → verify side_win_rate field present
no_entry_analyzer: zero_size=0 should remain zero
```

---

## Upgrade Checklist (HOTFIX_PARTIAL → HOTFIX_VALIDATED)

```
[ ] Run paper session with ≥30 cycles
[ ] Confirm at least 1 candidate reaches sizing gate
[ ] Verify: no micro_position_size < 0.10 in post-hotfix risk_log
[ ] Verify: zero_size_probe event (if fired) contains side_win_rate field
[ ] Update this document and POSITION_SIZING_HOTFIX_RUNTIME_VALIDATION_001.md verdict to HOTFIX_VALIDATED
[ ] Close task POSITION_SIZING_HOTFIX_RUNTIME_VALIDATION_001
```

---

## Task Closure Statement

**Task `POSITION_SIZING_HOTFIX_RUNTIME_VALIDATION_001` is closed at the code-verification level.**

- All three output documents have been written.
- The hotfix is correct, safe, and regression-free.
- Upgrade to `HOTFIX_VALIDATED` requires only a longer paper session — no code changes required.
- No further action is needed before resuming normal paper operations.

---

*Next actions document for POSITION_SIZING_HOTFIX_RUNTIME_VALIDATION_001*
