# POLYMARKET_EXECUTABLE_SIZING_REALITY_AUDIT_001

**Task class:** 2 DESIGN / EXECUTION REALITY AUDIT
**Date:** 2026-06-30
**Final verdict:** DESIGN_COMPLETE

## Scope

Design-only audit of executable sizing reality for Polymarket BTC/ETH 5M paper/live
readiness. Produces a bankroll-tiered sizing ladder design, dust zone definition,
liquidity-aware sizing rules, and no-fixed-cooldown throttle policy. No runtime
code was modified.

Do NOT modify: strategy thresholds, execution behavior, risk logic, sizing, wallet/balance,
live execution, order submission, `config/settings.py`, `.env`.

---

## 1. Current Sizing Assumptions

### 1.1 Bankroll Tier (T0_MICRO_SEED, $0–$25)

Current balance: $20.10

| Parameter | Value | Source |
|---|---|---|
| Tier | T0_MICRO_SEED | `polymarket/bankroll_tiers.py:148` |
| max_risk_pct | 5% | bankroll_tiers.py |
| kelly_fraction | 10% | bankroll_tiers.py |
| min_position_size_hint | $0.01 | bankroll_tiers.py |
| max_market_exposure_pct | 10% = $2.01 | bankroll_tiers.py |
| max_trades_per_hour | 4 | bankroll_tiers.py |
| stop_loss_pct | 90% | bankroll_tiers.py |

### 1.2 Kelly Chain at $20 Bankroll

```
full_kelly         = edge / (1 - entry_price)
fractional_kelly   = full_kelly × 0.10
applied_risk_pct   = min(fractional_kelly, 0.05, 0.03)
position_dollars   = $20.10 × applied_risk_pct  ← target profit if WIN
shares             = position_dollars / (1 - entry_price)
cost_to_enter      = shares × entry_price        ← actual $ spent
```

At a typical entry_price=0.55, edge=0.10:
- full_kelly = 0.10 / 0.45 = 0.222
- fractional_kelly = 0.222 × 0.10 = 0.022 (2.2%)
- applied_risk_pct = min(0.022, 0.05, 0.03) = **0.022 (2.2%)**
- position_dollars = $20.10 × 0.022 = **$0.44**
- shares = $0.44 / 0.45 = **~1 share**
- cost_to_enter = 1 × 0.55 = **$0.55**

At edge=0.05 (typical paper observation):
- full_kelly = 0.111
- fractional_kelly = 0.011 (1.1%)
- position_dollars = $0.22
- Dynamic minimum shares override kicks in: **1 share**
- cost_to_enter = 1 × 0.55 = **$0.55**

### 1.3 Position Sizing Multiplier Chain

`polymarket/position_sizing.py` applies 8 multipliers to `bankroll × base_risk_pct`:

| Multiplier | Range | Blocked when |
|---|---|---|
| confidence_multiplier | 0.0–1.0 | confidence < 0.54 (full block) |
| ev_multiplier | 0.20–1.0 | ev ≤ 0 (full block) |
| drawdown_multiplier | 0.10–1.0 | drawdown ≥ 8% (full block) |
| liquidity_multiplier | 0.25–1.0 | liquidity < $10 (full block) |
| spread_multiplier | 0.20–1.0 | spread > 10% (full block) |
| time_to_settlement_multiplier | 0.0–1.0 | time_remaining ≤ 90s (full block) |
| delta_multiplier | 0.0–1.0 | |
| frequency_multiplier | 0.20–1.0 | max_trades_per_hour reached |

At T0_MICRO_SEED with max 4 trades/hr and base_risk=5% of $20.10:
- base notional = $20.10 × 5% = $1.005 (before multipliers)
- Typical multiplier product at moderate edge: ~0.10–0.30
- **Realistic base order size: $0.10–$0.30** per trade before min-share override

### 1.4 Risk Mode Size Multipliers

`polymarket/risk_modes.py`:

| Mode | Size Multiplier | Triggered by |
|---|---|---|
| NORMAL | 1.0× | Default |
| DEFENSIVE | 0.5× | 2+ losses or 2%+ drawdown |
| MICRO_RECOVERY | 0.25× | 3+ losses or 4%+ drawdown |
| LOCKDOWN | 0.0× | Hard drawdown or explicit trigger |

### 1.5 Loss Cluster Pause (Current Design)

`utils/risk_manager.py:44`:
```python
LOSS_CLUSTER_THRESHOLD     = 3      # Consecutive losses before pause
LOSS_CLUSTER_PAUSE_SECONDS = 1800   # 30-minute pause after loss cluster
```

This is a **fixed 30-minute sleep** — incompatible with always-active scanning. The engine
goes blind to new epoch opportunities rather than adapting sizing.

### 1.6 Paper/Execution Guards (Current)

| Setting | Value | Source |
|---|---|---|
| Polymarket CLOB hard minimum | $0.10 | `config/settings.py:226` (comment) |
| min_shares_per_order | 1 | `config/settings.py:233` |
| max_active_positions_per_market | 1 | `config/settings.py:222` |
| max_entries_per_market | 1 | `config/settings.py:223` |
| max_risk_per_market | 6% | `config/settings.py:224` |
| bankroll_floor | $5.00 | `config/settings.py:285` |
| max_single_trade_risk | 3% | `config/settings.py:286` |
| cooldown_after_loss | 120s | `polymarket/trade_frequency.py:9` |
| cooldown_after_win | 30s | `polymarket/trade_frequency.py:10` |
| min_seconds_between_entries | 30s | `polymarket/trade_frequency.py:11` |

---

## 2. Executable Reality Constraints

### 2.1 Polymarket CLOB Minimum Order

**Hard floor: $0.10 notional per order.** This is the documented Polymarket CLOB minimum.
Any sizing result below $0.10 must be rejected as a dust order.

### 2.2 Minimum Shares

At a price of $0.55 (typical BTC/ETH 5M YES side mid-window):
- 1 share × $0.55 = $0.55 cost → **above CLOB minimum** ✓
- At $0.10 price (deep NO side): 1 share × $0.10 = $0.10 → exactly at minimum

Price precision on Polymarket: 2 decimal places (cent-level). Share sizes are whole numbers
in the CLOB protocol (no fractional share fills guaranteed).

### 2.3 Available Book Depth

From validation run snapshots (2026-06-30, epoch 1782793800, ETH market):

| Metric | Observed value |
|---|---|
| best_bid (YES) | $0.81 |
| best_ask (YES) | $0.82 |
| best_bid_size (YES) | 34.93 shares |
| best_ask_size (YES) | 124.83 shares |
| total_bid_depth_l1_l3 | $272.02 |
| total_ask_depth_l1_l3 | $272.02 |
| spread | $0.01 (1.2%) |
| min_fillable_size_usd | $136.01 |

At $0.10–$2 order sizes, the L1 depth ($35–$125) is more than sufficient to fill. No
significant slippage expected for orders under $5.

### 2.4 Spread Reality

Observed spreads in validation run:
- ETH mid-window: **$0.01 (1.2%)** — within `max_spread=6%` gate
- BTC: spread data intermittent due to 3x CLOB empty response events

Spread widens near epoch end (final 60s). A `spread_too_wide` block fires if spread > 10%.
For sizing, the spread multiplier degrades linearly: at 6% spread → 0.20× multiplier.

### 2.5 Stale Quote Risk

- Orderbook cache TTL: fresh per decision cycle (every ~50–60s in paper run)
- CLOB empty response events: 3 observed in 8-minute run (all BTC, all after 04:29 UTC)
- Risk: entering on stale quote where spread has widened post-cache. Mitigated by
  `orderbook_snapshot_age_ms_at_decision` < 1000ms in observed snapshots.

### 2.6 Partial Fill Risk

Polymarket binary markets use a CLOB with resting orders. Partial fills can occur when the
requested size exceeds resting liquidity at the best price. At $0.10–$2 order sizes and
L1 depth of $35+, partial fill risk is low mid-epoch. Near epoch close (< 30s remaining),
resting liquidity often disappears.

### 2.7 Liquidity by Time Remaining

From observed lifecycle data:

| Phase | Time remaining | Book state |
|---|---|---|
| Opening (0–30s after open) | 285–300s | NONZERO_BOOK (thin) |
| Active window (30–240s) | 60–270s | TRADABLE (healthy depth) |
| Late window (240–280s) | 20–60s | TRADABLE but thinning |
| Close (280–300s) | 0–20s | Stale/empty, cutoff active |

Entry cutoff: **90 seconds remaining** (hard block in `position_sizing.py:184`).

### 2.8 Price Precision and Dust Zone

**Dust zone definition:** Any order where `cost_to_enter < $0.10`. At T0_MICRO_SEED
with $20.10 balance:

| Edge | Applied risk% | Cost-to-enter | Dust? |
|---|---|---|---|
| 0.03 | 0.3% → $0.06 → 1 share | $0.55 (min-share override) | No |
| 0.10 | 2.2% → $0.44 → 1 share | $0.55 | No |
| 0.15 | 3.0% (hard cap) → $0.60 → 1 share | $0.55 | No |

With dynamic min-share override (1–5 shares), all T0 orders land at $0.10–$4.00. The dust
zone is **primarily a concern for fractional-share results before the min-share override**.
After override, all orders clear the $0.10 CLOB minimum.

**At T0_MICRO_SEED, every valid order is $0.55–$2.75 (1–5 shares at $0.55 entry).**

---

## 3. Bankroll Tier Reference Table

| Tier ID | Name | Range | max_risk% | kelly_frac | min_hint | max_mkt% | max_trades/hr | Practical order range |
|---|---|---|---|---|---|---|---|---|
| T0_MICRO_SEED | Micro Seed | $0–$25 | 5% | 10% | $0.01 | 10% | 4 | $0.10–$1.25 |
| T1_MICRO_BUILD | Micro Build | $25–$50 | 6% | 12% | $0.02 | 10% | 5 | $0.25–$3.00 |
| T2_MICRO_SURVIVAL | Micro Survival | $50–$100 | 5% | 15% | $0.05 | 9% | 6 | $0.50–$5.00 |
| T3_BASE_BUILD | Base Build | $100–$250 | 4% | 20% | $0.50 | 8% | 8 | $1.00–$10.00 |
| T4_BASE_STABLE | Base Stable | $250–$500 | 3.5% | 20% | $0.75 | 7% | 8 | $2.00–$17.50 |
| T5_SMALL_GROWTH | Small Growth | $500–$1K | 3% | 22% | $1.00 | 6% | 10 | $5.00–$30.00 |

_T0 current (balance $20.10). T3 is the first "standard" tier; paper pilot target before live._

**Practical order range** is `bankroll × (min_risk_pct × multiplier_floor)` to
`bankroll × max_risk_pct`.

---

## 4. Many-Small-Orders Sizing Ladder

### 4.1 Ladder Design Principles

- **Always active scanning.** No fixed sleep between epochs. MAE confirms ACTIVE before
  evaluating. Engine scans every ~50s.
- **Many small orders, not large single entries.** Each order is sized to be ≤3% bankroll.
  At T0, this is ≤$0.60 per order per trade. Accumulate edge over many small fills.
- **One position per market at T0–T2.** Upgrade to multi-leg only at T3+ with evidence.
- **Probe → Base → Add cadence.** Each layer is gated by book state and risk mode.

### 4.2 Order Types

| Order type | Purpose | Size rule |
|---|---|---|
| **Probe** | Validate fill path works; build fill evidence | CLOB minimum = $0.10 |
| **Base** | Primary entry sized by Kelly and multipliers | $0.10–bankroll×3% |
| **Add** | Add to winning position with fresh edge confirmation | ≤50% of base size |

### 4.3 Tier Ladder by Bankroll

#### T0_MICRO_SEED ($0–$25, current balance $20.10)

| Layer | Size | Constraint |
|---|---|---|
| Probe | $0.10 | CLOB minimum; evidence-only until 3 paper fills confirm path |
| Base | $0.10–$0.60 | Kelly chain output; min 1 share |
| Add | $0.10 | Add only if: position is winning, ≥60s remaining, spread < 4%, RiskMode=NORMAL |
| Max adds | 1 | Total position: probe + base + 1 add = $0.20–$1.30 |
| Per-market cap | $2.00 | 10% of bankroll (T0 max_market_exposure_pct) |
| Portfolio cap | $4.00 | ≤20% total (2 markets × 10%) |
| Stop adding | time ≤ 90s, RiskMode ≠ NORMAL, spread > 4%, daily loss ≥ 5% |

**Minimum viable bankroll for T0 ladder:** $5.00 (floor) — but in practice $10+ required
for 1 full base order + margin. Below $10, only probe-mode is safe.

#### T1_MICRO_BUILD ($25–$50)

| Layer | Size |
|---|---|
| Probe | $0.25 |
| Base | $0.25–$1.50 |
| Add | $0.25 |
| Max adds | 2 |
| Per-market cap | $5.00 (10%) |

#### T2_MICRO_SURVIVAL ($50–$100)

| Layer | Size |
|---|---|
| Probe | $0.50 |
| Base | $0.50–$2.50 |
| Add | $0.25–$0.50 |
| Max adds | 2 |
| Per-market cap | $9.00 (9%) |

#### T3_BASE_BUILD ($100–$250) — first "real money" tier

| Layer | Size |
|---|---|
| Probe | $1.00 |
| Base | $1.00–$10.00 |
| Add | $0.50–$2.00 |
| Max adds | 3 |
| Per-market cap | $20.00 (8%) |
| Portfolio cap | 4 markets possible |

### 4.4 Ladder Gate Rules

```
BEFORE PROBE:
  - RiskMode == NORMAL
  - book_state == TRADABLE
  - spread <= max_spread
  - time_remaining > 120s
  - No open position in this market
  - Paper: ≥0 paper fills logged (fill path unverified → first probe only)

BEFORE BASE (after probe fills):
  - Same as probe, plus:
  - confidence >= 0.54
  - ev > 0
  - size output >= $0.10 (CLOB minimum)

BEFORE ADD:
  - Existing position is profitable (current price > cost_basis)
  - time_remaining > 90s
  - RiskMode == NORMAL (no adds in DEFENSIVE/MICRO_RECOVERY)
  - spread <= 4%
  - Total position exposure < per-market cap
  - Daily loss < 5%
```

---

## 5. Dust Zone

| Scenario | Cost-to-enter | Classification | Action |
|---|---|---|---|
| Kelly output < $0.10 BEFORE min-share override | < $0.10 | **DUST** | Reject |
| Kelly output produces 0 shares | $0.00 | **DUST** | Reject |
| Kelly output ≥ 1 share × entry_price ≥ $0.10 | ≥ $0.10 | VALID | Submit |
| Residual position after partial exit < 1 share | < entry_price | **DUST** | Skip exit, sweep at epoch close |

**Dust rejection is already enforced** by `order_intent.py:validate_order_intent`:
`if float(intent.size) <= 0` → rejected. The CLOB minimum $0.10 must be added as an
explicit pre-submission check before `validate_order_intent` is called in a future
implementation phase.

---

## 6. Liquidity-Aware Sizing Rules

### 6.1 Spread-Based Size Scaling

The existing spread_multiplier (`position_sizing.py:139`) degrades linearly:
```
spread_multiplier = clamp(1.0 - 0.80 × (spread / max_spread), 0.20, 1.0)
```
At spread=1% (observed): multiplier ≈ 0.87
At spread=4%: multiplier ≈ 0.68
At spread=6%: multiplier ≈ 0.52

This is **adequate for T0–T2**. For a many-small-orders engine:
- spread > 4%: no adds, base only
- spread > 6%: base only if confidence ≥ 0.65
- spread > 10%: full block (existing gate)

### 6.2 Time-to-Settlement Scaling

The existing time_to_settlement_multiplier (`position_sizing.py:141–146`):
```
time_window = max(good_time_remaining_seconds - 90, 1) = 150
multiplier = clamp(0.35 + 0.65 × ((seconds_remaining - 90) / 150), 0.0, 1.0)
```
At 300s remaining: 1.0
At 180s remaining: 0.70
At 120s remaining: 0.35
At ≤90s remaining: hard block

**For adds:** tighter cutoff. No adds when time_remaining < 120s (not just 90s).

### 6.3 Depth-Based Sizing Cap

At T0, max order $0.60. L1 depth typically $35+. No depth cap needed at T0.
At T3+, cap single order at `min(sizing_output, L1_depth_$ × 0.10)` to avoid moving
the market. This is a future implementation guideline only.

### 6.4 Liquidity Score Integration

`prob_model_liquidity_usd` observed in paper run: $158.85 (ETH epoch 1782793800).
At T0, this is more than adequate. The liquidity_multiplier gate ($10 minimum) is the
relevant existing control.

---

## 7. No Fixed Cooldown Policy

### 7.1 Problem with Current 30-Minute Pause

`risk_manager.py:44` hardcodes a 30-minute blind pause after 3 consecutive losses:
```python
LOSS_CLUSTER_PAUSE_SECONDS = 1800
```
This forces the engine to miss 3–6 full 5-minute BTC/ETH epochs. With MAE now seeing
markets and rollovers correctly, a blind 30-minute pause is incompatible with the
always-active scanning goal.

### 7.2 Replacement: Opportunity Throttle Framework

The throttle framework below does NOT change runtime code in this task. It is the design
target for a future implementation phase.

**Throttle tiers** (replace 30-minute pause):

| Trigger | Response | Duration |
|---|---|---|
| 0 losses | NORMAL mode | — |
| 1 loss | NORMAL mode, size−10% for next 2 entries | 2 entries only |
| 2 consecutive losses | DEFENSIVE mode (0.5× size) | Until 1 win or 30 min elapsed |
| 3 consecutive losses | MICRO_RECOVERY mode (0.25×), base-only, no adds | Until 1 win or 60 min elapsed |
| 4 consecutive losses | Entry ban for 1 epoch (5 min), then MICRO_RECOVERY | 5 min absolute minimum |
| Daily drawdown 4–10% | MICRO_RECOVERY | Remainder of trading day |
| Daily drawdown ≥ 10% | LOCKDOWN | Full day stop |

**Key difference from current design:**
- After 3 losses the engine does NOT sleep 30 minutes. It enters MICRO_RECOVERY (0.25× size)
  and continues scanning.
- Re-entry is allowed in any epoch if RiskMode allows AND evidence is sufficient.
- Adds are always banned in DEFENSIVE/MICRO_RECOVERY.
- Lockdown is reserved for daily drawdown only, not loss streaks.

### 7.3 Degraded Market Throttle

| Condition | Throttle |
|---|---|
| book_state == TRUE_EMPTY | Skip this cycle; no order |
| MAE state == BETWEEN_EPOCHS | Skip until ACTIVE |
| MAE state == MARKET_NOT_SCHEDULED | Skip until next MAE check (30s) |
| spread > max_spread | Size via spread_multiplier (existing) |
| CLOB error rate > 3 in 60s | circuit breaker active; skip entries |

### 7.4 Loss Response by Size Reduction (Not Sleep)

```
loss_event → immediately reduce SIZE, not pause TIME
```

Sequence after any loss:
1. Record loss → update consecutive_losses, drawdown_pct
2. Evaluate risk mode → may downgrade to DEFENSIVE/MICRO_RECOVERY
3. Next decision cycle: sizing uses current risk_mode size_multiplier
4. If risk_mode allows entry AND evidence passes all gates → trade (at reduced size)
5. Win → reset consecutive_losses; risk_mode allowed to upgrade on next cycle

Edge re-entry is **explicitly allowed** when evidence returns. The engine must not be
arbitrarily quiet just because time has passed — it should be quiet because the edge is
absent and resume when the edge appears.

---

## 8. Replay and Backtest Requirements

Before any live pilot:

| Requirement | Status |
|---|---|
| Paper fill path exercised (≥1 paper fill logged) | **NOT MET** — all current paper cycles SKIP/NO |
| Paper win/loss PnL accounting loop verified | **NOT MET** |
| ≥20 paper fills across ≥3 epochs | NOT MET |
| Replay analysis: MFE/MAE distribution | NOT MET (Phase 2) |
| Backtest on canonical context with PASS_CONTEXT rows | Partially met (41 rows, not statistically significant) |
| Evidence grade: ≥B on decision engine review | NOT MET (need signal-driven fills) |

The primary paper-to-live blocker is that the engine has not yet executed a single paper
fill. All decisions are currently blocked at the microstructure gate
(`skip_reason_primary=imbalance_extreme` or `delta_extreme`). The signal and sizing logic
exist but have not been exercised on the actual fill path.

---

## 9. Live Pilot Blockers

| Blocker | Severity | Notes |
|---|---|---|
| Zero paper fills in execution history | **CRITICAL** | Fill path, accounting, position tracking unverified |
| $0.10 CLOB minimum vs $20.10 bankroll | HIGH | Only 1 share per trade, very limited accumulation |
| Loss cluster 30-minute sleep conflicts with active scanning | HIGH | Design fix required before live |
| max_active_positions_per_market=1 prevents adding | MEDIUM | Must be raised to ≥3 for ladder strategy |
| max_entries_per_market=1 prevents re-entry after fill | MEDIUM | Must be raised to allow probe → base → add |
| BTC CLOB intermittent empty (3× in 8-minute run) | MEDIUM | May cause missed entries; monitor fill rate |
| imbalance_extreme skip pattern (7/15 decisions) | MEDIUM | Signal gate working but may be too aggressive |
| No paper PnL compounding proof | MEDIUM | $20.10 has not changed; accounting loop untested |
| Microstructure skip rate 7/15 = 47% | LOW | Acceptable — shows risk gate working |
| Polymarket USDC allowance status (prior: false-positive) | LOW | Verify allowance before live; prior preflight was GO_WITH_WARNING |

### 9.1 Sizing Reality at Live T0 Bankroll

At $20 balance, live orders would be:
- 1 share × $0.55 = **$0.55 per trade**
- Max 4 trades/hr × $0.55 = **$2.20/hr maximum deployment**
- Max per-market exposure = $2.00 (10% of $20)
- Max portfolio exposure = $4.00 (20%)

This is deliberately small. The purpose at T0 is to prove the execution loop, not to
generate meaningful PnL. Live T0 is a process validation, not a capital-growth exercise.

---

## 10. Path to T3 (First Standard Tier)

| Milestone | Bankroll | Priority |
|---|---|---|
| Paper fill path working | $20 | NOW |
| 20 paper fills across ≥5 epochs | $20 | NOW |
| Positive paper PnL on ≥10 trades | $20 | NOW |
| Decision engine PASS_CONTEXT on ≥50 real trades | $20–$25 | Phase 2 |
| Live T0 micro pilot ($0.55/trade) | $20+ | After 20 paper fills |
| Grow to $25 (T1) | $25 | After 5 live fills |
| Grow to $50 (T2) | $50 | After 20 live fills |
| Grow to $100 (T3) | $100 | After statistical evidence |

---

## 11. Summary Table

### Current Sizing Assumptions

| Item | Value |
|---|---|
| Bankroll | $20.10 (T0_MICRO_SEED) |
| Max risk per trade | 3% = $0.60 |
| Effective risk at T0 | ~2.2% on edge=0.10 = ~$0.44 |
| Practical order size | $0.55 (1 share × entry_price) |
| Max trades/hr | 4 |
| Loss cluster pause | 30 min (change in future phase) |
| Max positions per market | 1 (change in future phase) |

### Executable Constraints

| Constraint | Value |
|---|---|
| CLOB minimum order | $0.10 |
| Min shares | 1 (whole shares) |
| Typical spread (mid-epoch) | 1–4% |
| L1 depth (ETH, observed) | $35–$125/side |
| Entry cutoff | 90s remaining (hard block) |
| Add cutoff | 120s remaining (design) |

### Order Ladder (T0_MICRO_SEED, $20.10)

| Order type | Size | Gate |
|---|---|---|
| Probe | $0.10 | CLOB minimum; RiskMode=NORMAL; TRADABLE book |
| Base | $0.10–$0.60 | All multipliers pass; min 1 share |
| Add | $0.10 | Position winning; ≥120s; NORMAL; spread<4%; within cap |
| Max adds | 1 | |
| Per-market cap | $2.00 | 10% of bankroll |
| Portfolio cap | $4.00 | 20% of bankroll |

### No Fixed Cooldown

Replacing 30-minute blind sleep with tiered opportunity throttle: loss → size down, not
pause. Re-entry allowed in next epoch if risk mode and evidence permit.

---

## Files Reviewed

| File | Purpose |
|---|---|
| `utils/risk_manager.py` | Kelly sizing, loss cluster pause, floor |
| `polymarket/position_sizing.py` | Multiplier chain, blocked reasons |
| `polymarket/bankroll_tiers.py` | 13 tiers, risk profiles, exposure caps |
| `polymarket/risk_modes.py` | NORMAL/DEFENSIVE/MICRO_RECOVERY/LOCKDOWN |
| `polymarket/trade_frequency.py` | Cooldowns, max trades, min seconds between |
| `polymarket/order_manager.py` | Build order plan, zero plan |
| `polymarket/order_intent.py` | Validation gates before submission |
| `polymarket/virtual_ptb.py` | Oracle feed wrapper |
| `config/settings.py` | CLOB minimum, max positions, floor, hard cap |
| `docs/reports/MARKET_AVAILABILITY_ENGINE_POST_REPAIR_PAPER_VALIDATION_001.md` | MAE evidence |
| `docs/reports/MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001.md` | Repair context |

## Safety Classification

SAFE_DESIGN_AUDIT. No runtime code, sizing, risk, execution, wallet, configuration, or
strategy thresholds were modified.
