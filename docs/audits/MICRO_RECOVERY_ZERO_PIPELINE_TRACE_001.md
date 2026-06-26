# MICRO_RECOVERY_ZERO_PIPELINE_TRACE_001

**Task:** MICRO_RECOVERY_RISK_PLAN_ZERO_AUDIT_001  
**Mode:** DISCOVERY ONLY  
**Date:** 2026-06-25  
**Source:** polymarket/trader.py, polymarket/order_manager.py, polymarket/position_sizing.py, polymarket/risk_modes.py, polymarket/trade_frequency.py, utils/risk_manager.py

---

## Stage Map — BTC NO Candidate in MICRO_RECOVERY

The following traces the exact code path for a representative blocked candidate:
- Asset: BTC, Market: pm-5m-btc
- Side: NO (model predicts NO outcome is underpriced)
- Composite confidence: 0.8551
- Entry price (NO ask): 0.08
- Raw model p_no: 0.2607
- Edge: 0.1807
- Session risk mode: MICRO_RECOVERY
- Time remaining: 207 seconds
- Session: 20260625T065019Z_20608_0bee180b

---

## Stage 1 — Risk Mode Gate

**Code:** `polymarket/risk_modes.py:88–111` — `trade_quality_allowed()`

```python
trade_quality_allowed(
    mode=RiskMode.MICRO_RECOVERY,
    confidence=0.8551,  # composite confidence score
    grade=None,
)
# → MICRO_RECOVERY branch: float(0.8551) >= 0.75 → True, "confidence_ok"
# RESULT: ALLOWED
```

**Inputs:**
- `mode`: MICRO_RECOVERY (consecutive_losses=4 after T9)
- `confidence`: 0.8551 (composite confidence from model + regime + indicators)

**Output:** ALLOWED — composite confidence 0.8551 ≥ MICRO_RECOVERY floor 0.75.

---

## Stage 2 — EV Gate

**Code:** `polymarket/trader.py` (ev_below_threshold check before sizing)

```python
model_ev = 0.1807  # p_no - entry_price_no = 0.2607 - 0.08
# model_ev > 0 → passes EV gate
# RESULT: ALLOWED
```

**Output:** ALLOWED — positive expected value.

---

## Stage 3 — Order Request Construction

**Code:** `polymarket/trader.py:9904–9909`

```python
min_position_size_usd = self._entry_min_position_size_usd(
    bankroll=20.039,
    entry_price=0.08,
)
# → _micro_survival_active(20.039) = True (balance < 100)
# → returns _micro_survival_min_position_size() = 0.05  ← NOT 0.10 here
```

Wait — the diagnostic shows `min_position_size_usd=0.1`. This is the micro_survival rescue minimum, not the entry minimum. The entry minimum is 0.05 (configurable). The diagnostics field `min_position_size_usd` in `risk_plan_zero_diagnostics` reflects the rescue minimum (0.10 default).

```python
order_request = OrderRequest(
    market_id="pm-5m-btc",
    side="NO",
    entry_price=0.08,
    win_rate=probability.p_no,  # ← p_no = 0.2607 (raw model output)
    reward_risk_ratio=2.0,
    edge=0.1807,
    spread=0.010,
    liquidity_usd=1222.59,     # strong liquidity
    delta=0.8,
    delta_multiplier=0.8,
    time_remaining_seconds=207,  # fine
    trades_last_hour=0,          # fine
    drawdown_pct=0.003,          # 0.3% — fine
    min_position_size_usd=0.05,  # micro_survival entry min
    daily_loss_limit_reached=False,
    hard_drawdown_reached=False,
)
```

**Critical:** `win_rate=probability.p_no=0.2607`. This is the raw model probability for the NO outcome. It is NOT the composite confidence score (0.8551).

---

## Stage 4 — Position Sizing

**Code:** `polymarket/order_manager.py:99–117` → `polymarket/position_sizing.py:171–220`

```python
# build_order_plan() calls:
sizing = calculate_position_size(PositionSizingInput(
    bankroll=20.039,
    confidence=0.2607,          # ← win_rate = p_no, NOT composite confidence
    ev=0.1807,
    entry_price=0.08,
    drawdown_pct=0.003,
    spread=0.010,
    liquidity_usd=1222.59,
    delta=0.8,
    delta_multiplier=0.8,
    time_remaining_seconds=207,
    trades_last_hour=0,
    min_position_size_usd=0.05,
    daily_loss_limit_reached=False,
    hard_drawdown_reached=False,
    confidence_floor=0.54,       # ← DEFAULT — NOT updated for MICRO_RECOVERY mode
    max_spread=0.10,
    min_liquidity_usd=10.0,
    daily_loss_limit_pct=0.08,
    hard_drawdown_pct=0.15,
))
```

**Blocking checks in `calculate_position_size()` (polymarket/position_sizing.py:177–195):**

```
bankroll=20.039 > 0             → invalid_bankroll: NO
daily_loss_limit: 0.003 < 0.08 → daily_loss_limit_reached: NO
hard_drawdown: 0.003 < 0.15    → hard_drawdown_reached: NO
time_remaining: 207 > 90        → time_remaining_le_90s: NO
confidence: 0.2607 < 0.54      → confidence_too_low: YES ← THE BLOCK
ev: 0.1807 > 0                 → ev_not_positive: NO
spread: 0.010 < 0.10           → spread_too_wide: NO
liquidity: 1222 > 10.0         → liquidity_too_low: NO
trades_last_hour: 0 < 4         → max_trades_per_hour_reached: NO
```

**Result:** `blocked = ["confidence_too_low"]` → `_zero_result()` called  
→ `PositionSizingResult(approved=False, final_size_usd=0.0, shares=0.0, blocked_reasons=("confidence_too_low",))`

**Multipliers computed (for observability even on zero result):**
- confidence_multiplier: 0.25 + 0.75 * (0.2607 - 0.54)/0.21 = clamped to 0.0 (negative input)
- frequency_multiplier: 1.0 (trades_last_hour=0 < 25% of max)
- delta_multiplier: 0.8 (from pre-computed delta.delta_multiplier)

---

## Stage 5 — Order Manager Zero Plan

**Code:** `polymarket/order_manager.py:118–150`

```python
if not sizing.approved:  # True — sizing blocked
    return self._zero_plan(
        request,
        reason="confidence_too_low",
        diagnostics={
            "blocked_reasons": ["confidence_too_low"],
            "final_position_size": 0.0,    # shares
            "final_notional_size": 0.0,    # USD
            "tier": "T0_MICRO_SEED",
            "base_risk_pct": 0.034,
            "confidence_multiplier": 0.0,  # observed in logs
            ...
        },
    )
```

`_zero_plan()` at order_manager.py:66–74 sets:
```python
RiskPlan(
    position_size=0.0,
    notional_size=0.0,
    diagnostics={"blocked_reasons": ["confidence_too_low"], ...},
)
```

---

## Stage 6 — Micro-Survival Rescue Check

**Code:** `polymarket/trader.py:702–733` — `_maybe_apply_micro_survival_plan()`

```python
# Step 1: micro_survival_active?
self._micro_survival_active(20.039)
= bankroll_mode_for(account_balance=20.039, threshold=100.0, paper_trading=True)
= MICRO_SURVIVAL_MODE  → True  ✓ (proceed)

# Step 2: position_size > 0?
float(risk_plan.position_size) = 0.0 → NOT > 0 ✓ (proceed)

# Step 3: blocked_reasons == {"below_min_position_size"}?
blocked = {"confidence_too_low"}
blocked != {"below_min_position_size"}
→ RESCUE ABORTED — return unchanged risk_plan(position_size=0.0)
```

**If rescue had been allowed** (hypothetical):
```python
build_micro_survival_risk_plan(
    account_balance=20.039,
    entry_price=0.08,
    risk_fraction=0.0025,            # 0.25%
    min_position_size_usd=0.10,      # $0.10 minimum
    max_risk_per_trade=0.0,          # from settings (0 → effective_fraction=0)
)
# → notional_size = min(max(0.0, 0.10), 20.039) = 0.10
# → position_size = 0.10 / 0.08 = 1.25 shares
# Hypothetical result: position_size=1.25, notional=$0.10
```

But rescue is never reached. The `micro_position_size: 0.1` shown in `risk_plan_zero_diagnostics` is the hypothetical rescue output, computed for observability only.

---

## Stage 7 — Risk Mode Size Multiplier (NOT REACHED)

**Code:** `polymarket/trader.py:9920–9921`

```python
if risk_plan.position_size > 0:
    self._apply_risk_mode_to_plan(risk_plan, risk_mode_decision)
```

This only runs if position_size > 0. Since position_size=0.0 after rescue failed, this is never called. The MICRO_RECOVERY `size_multiplier=0.25` does NOT contribute to the zero size.

---

## Stage 8 — Zero Plan Label

**Code:** `polymarket/trader.py:9923–9941`

```python
if risk_plan.position_size <= 0:  # True
    # Emit zero-size probe event
    quant_detail = self._record_quant_detail(
        ...
        skip_reason="ev_below_threshold",        # (confusing label — legacy)
        raw_skip_reason="risk_plan_zero",
        normalized_skip_reason="risk_plan_zero", # ← label applied
        final_size=0.0,
        ...
    )
    outcome = TradeOutcome(..., "Risk plan returned zero position size -- skipping.")
```

The `normalized_skip_reason="risk_plan_zero"` is hardcoded. The underlying cause (`confidence_too_low` in blocked_reasons) is buried in `risk_plan_zero_diagnostics.reason_from_order_manager`.

---

## Confidence Duality — The Core Mismatch

```
COMPOSITE CONFIDENCE (0.8551)
  = f(p_no=0.26, regime_alignment, indicator_evidence, ...)
  Used by: trade_quality_allowed() at risk mode gate
  Floor applied: MICRO_RECOVERY = 0.75

RAW PROBABILITY (p_no = 0.2607)
  = probability model output for NO outcome
  Used by: calculate_position_size() as sizing "confidence"
  Floor applied: confidence_floor = 0.54 (hardcoded default, never updated)

RESULT:
  Composite 0.8551 >> 0.75 → passes risk mode gate
  Raw 0.2607 << 0.54 → blocked by sizing gate
  → Permanent deadlock for all BTC NO bets
```

---

## What Enables BTC YES Bets to Execute

For comparison — BTC YES bets that executed (T5 conf=0.7448, T7 conf=0.7348):
- Side: YES
- Entry price (YES ask): 0.49–0.51 (YES was priced ~50/50)
- Raw p_yes from model: ≈ 0.73–0.75 (model sees YES as more likely)
- Sizing confidence: p_yes ≈ 0.73 > 0.54 floor → PASSES sizing

BTC YES bets pass because the model p_yes ≈ 0.73 is itself above the sizing floor. BTC NO bets fail because the model p_no ≈ 0.26 is far below the sizing floor even when composite confidence is high.

This asymmetry means:
- BTC YES entries: feasible (p_yes typically 0.6–0.8)
- BTC NO entries: permanently blocked by sizing (p_no typically 0.2–0.35)

---

## Summary

| Stage | Check | Input | Result |
|---|---|---|---|
| Risk mode gate | composite_conf ≥ 0.75 | 0.8551 | PASS |
| EV gate | ev > 0 | 0.1807 | PASS |
| Sizing confidence | p_no ≥ 0.54 | 0.2607 | **FAIL** |
| Other sizing checks | spread, liquidity, time, freq | all fine | PASS |
| Micro-survival rescue | blocked == {"below_min_position_size"} | {"confidence_too_low"} | ABORTED |
| Risk mode multiplier | position_size > 0 required | 0.0 | NOT REACHED |
| Label | normalized | — | risk_plan_zero |
