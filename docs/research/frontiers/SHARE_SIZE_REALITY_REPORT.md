# Share Size And Executable Reality Audit

**Generated:** 2026-06-07
**Data sources:**
- `runtime/research_exports/completed_trades_v1_2.csv` — 440 completed paper trades
- `runtime/quant_data/decision_log/2026-06-05.jsonl` — 9,659 decision events
- `polymarket/trader.py` — gate and override logic (lines 565–604, 9291–9305)
- `tools/canonical_trade_table_v1.py` — PnL field assignments (lines 389–392, 1058)

**Constraints:** Read-only analysis. No code changes. No strategy changes. No risk changes. No live trading.
No commits. Offline evidence only — must not wire into runtime decisions.

---

## Scope

Determines whether paper trades generated under $20 MICRO_SURVIVAL mode are realistically executable on
Polymarket, and clarifies the meaning of signal, paper, and executable trade types at this scale.

---

## 1. Current Share Sizing

**Paper wallet balance:** ~$20.06 (confirmed from `paper_virtual_cash` field in 2026-06-05.jsonl)
**Bankroll tier:** T0_MICRO_SEED ($0–$25)
**Mode:** MICRO_SURVIVAL (active when bankroll < $100)
**MICRO_SURVIVAL risk fraction:** 0.0025 (0.25%)
**micro_position_size in production:** ~$0.0502 per trade (= $20.06 × 0.0025)

**Distribution across all 440 paper trades:**

| Metric | Value |
|---|---|
| Mean shares | 0.0976 |
| Median shares | 0.0952 |
| Min shares | 0.0203 |
| Max shares | 0.2867 |
| Mean notional_entry | $0.0508 |
| Median notional_entry | $0.0503 |
| Min notional | $0.0126 |
| Max notional | $0.1453 |
| Mean entry_price | $0.5282 |

**Sizing mechanism — micro override:**
In MICRO_SURVIVAL mode, the standard multiplier stack executes first. Because
`min_position_size_usd = max(1 × entry_price, $1.00) = $1.00` in standard mode, and `bankroll × base_risk_pct`
($20 × 3–5% = $0.60–$1.00) is at or below that floor, any multiplier product < 1.0 triggers a
`"below_min_position_size"` block. `_maybe_apply_micro_survival_plan()` (trader.py lines 573–604) then
overrides with a flat $0.0502, discarding the multiplier result entirely. The override saves the original
blocked value in `diagnostics["original_position_size"] = 0`.

The `minimum_usd` parameter (`$0.05`) has no mathematical effect: `min(max(A, B), A) = A` identically, so
`notional_size = balance × risk_fraction` exactly. Shares = notional / entry_price ≈ $0.0502 / $0.5282
≈ **0.095 shares per trade** (average).

---

## 2. Dust Zone Classification

Two distinct and independent senses of "dust":

### Size-Dust — shares < 1.0 MOS

`MOS_ASSUMPTION_SHARES = 1.0` is the repository's research assumption for Polymarket's minimum executable
order size (`mos_source="research_assumption"` in `canonical_trade_table_v1.py`). This is a Polymarket
research convention, not a verified platform API minimum; it is the correct reference for this audit.

| Metric | Count | % |
|---|---|---|
| dust_zone = True (shares < 1.0) | 440 | **100%** |
| executable_minimum_met = False (shares < 1.0) | 440 | **100%** |
| executable_candidate = False | 440 | **100%** |
| executable_pnl_status = BLOCKED_NO_TRUE_EXECUTABLE_DATA | 440 | **100%** |

### PnL-Dust — |paper_pnl| < $0.01

| Metric | Count | % |
|---|---|---|
| Trades with |paper_pnl| < $0.01 | 312 | **70.9%** |
| Mean paper_pnl | −$0.000604 | (−0.06¢ per trade) |

At 0.097 shares and a typical ~$0.03 price move, expected PnL ≈ $0.003 — below the 1¢ threshold.
The 70.9% PnL-dust figure is a consequence of both tiny notional and realistic price-move magnitudes.

**These two measures are independent.** Size-dust captures whether shares are executable; PnL-dust
captures whether dollar outcomes are distinguishable from rounding noise.

---

## 3. Signal / Paper / Executable — Three-Way Distinction

### Signal Trade

The model fires: direction (YES/NO), confidence score, EV, regime context. Signal quality is measured by
win rate (WR) and profit factor (PF) — both are **scale-independent** rate metrics. They are unaffected by
position size.

For ETH YES FC OS (n=31 as of 2026-06-07): WR ≈ 58.1%, PF ≈ 2.055. These values would be identical
whether each position was $0.05 or $500.

### Paper Trade (current $20 micro-survival mode)

A fractional position (~$0.0502, ~0.097 shares) is simulated. Fractional shares are permitted **only**
because both conditions on trader.py line 570–571 hold:

```python
def _micro_survival_allows_fractional_shares(self, *, bankroll: float) -> bool:
    return bool(self.settings.paper_trading) and self._micro_survival_active(bankroll)
```

`paper_trading=True` AND `micro_survival_active` (bankroll < $100). This is a simulation permission gate,
not a real execution path. If either condition fails, the gate closes.

**Signal PnL = Paper PnL — by design in the code.**
In `canonical_trade_table_v1.py` (lines 389–390):

```python
"signal_pnl": pnl,
"paper_pnl": pnl,
```

Both fields are assigned the same computed value `pnl` in the same expression. `signal_pnl` does not
represent a separate signal-quality calculation — it is the same price-move × fractional-shares figure as
`paper_pnl`. At this scale, both fields are informational proxies for the price signal, not separate
measurements. The identity is structural, not incidental.

### Executable Live Trade

Requires:
1. ≥ 1 full share (MOS_ASSUMPTION_SHARES = 1.0)
2. Bankroll ≥ $100 (exits MICRO_SURVIVAL; standard gate re-activates)
3. Standard sizing produces ≥ `min_position_size_usd = max(1 × entry_price, $1.00) = $1.00`
4. `PAPER_TRADING=false` + passing the readiness preflight
5. Real CLOB execution: taker fee ~2%, slippage, fill risk, liquidity — **not modeled in paper**

`executable_pnl` is intentionally `None` for all 440 trades. Documented explicitly in
`canonical_trade_table_v1.py` line 1058:
> _"`executable_pnl` is intentionally null and blocked for every row."_

No executable truth data exists in this dataset.

---

## 4. Executable vs Non-Executable Paper Trades

All 440 trades are non-executable by every measure:

| Classification | Count | % of 440 |
|---|---|---|
| size-dust (shares < 1.0) | 440 | 100% |
| executable_minimum_met = False | 440 | 100% |
| executable_candidate = False | 440 | 100% |
| executable_pnl blocked | 440 | 100% |

**The sub-1-share SKIP gate (trader.py lines 9291–9295):**

```python
if (
    risk_plan.position_size < self.settings.min_shares_per_order
    and not self._micro_survival_allows_fractional_shares(bankroll=current_balance)
):
    skip_msg = f"Min shares: {risk_plan.position_size:.1f} < {self.settings.min_shares_per_order}"
    # → SKIP, reason: "liquidity_too_low"
```

This gate is bypassed in paper+MICRO_SURVIVAL mode. If the gate were active — i.e., if the bot moved to
live mode at the same $20 bankroll, or if the mode were standard paper at $100+ — all 440 of these
signals would be **SKIPPED**, not shrunk.

**Risk mode distribution (present but sizing-inert in micro mode):**

| Risk Mode | Count | % | Position Size Effect |
|---|---|---|---|
| NORMAL (1.0×) | 353 | 80.2% | Applied to multiplier stack; discarded by micro override |
| DEFENSIVE (0.5×) | 55 | 12.5% | Applied to multiplier stack; discarded by micro override |
| MICRO_RECOVERY (0.25×) | 32 | 7.3% | Applied to multiplier stack; discarded by micro override |

Risk modes affect the multiplier stack that runs first. Since the micro override fires when that stack
produces zero, risk mode multipliers are presently inert for sizing purposes in MICRO_SURVIVAL mode.

---

## 5. Bankroll Required for Meaningful Shares

### Structural constraint — MICRO_SURVIVAL is capped below 1 share at any bankroll (definitive)

From `risk_manager.py` lines 541–548, the formula reduces exactly to `notional = balance × risk_fraction`
(the `min_position_size_usd` parameter is mathematically inert: `min(max(A, B), A) = A` identically).
Maximum shares possible within MICRO_SURVIVAL (at bankroll just below $100):

```
max_notional = ($100 − ε) × 0.0025 = ~$0.25
max_shares   = $0.25 / ~$0.53 ≈ 0.47 shares
```

**MICRO_SURVIVAL cannot produce ≥ 1 share regardless of balance.** The 0.25% risk fraction is
structurally insufficient at any bankroll within the mode's range. This is not a gap to be closed by
increasing the bankroll within micro mode — it requires exiting the mode entirely.

### The discontinuity at $100

At bankroll ≥ $100, `micro_survival_active = False`:
- `_micro_survival_allows_fractional_shares()` → `False`
- The sub-1-share SKIP gate re-activates **even in paper mode**
- Signals below 1 share are **SKIPPED**, not filled with dust
- Standard sizing takes over; the multiplier stack now determines notional

### Necessary conditions in standard mode

In standard mode, two separate gates can block a trade:
- **1-share SKIP gate:** `position_size < min_shares_per_order` (trader.py 9291-9295). Necessary condition
  to clear: `notional ≥ entry_price × 1 share ≈ $0.53`. This is the fundamental ≥1-share requirement.
- **Notional floor gate:** `min_position_size_usd = max(1 × entry_price, $1.00) = $1.00`. If enforced in
  standard mode, it raises the requirement. Which gate binds depends on the `effective_min_size` calculation
  in the standard sizing path — **not verified empirically in this dataset.**

**Necessary Π bounds (for ≥1 share; entry_price ≈ $0.53):**

```
bankroll × base_risk_pct × Π ≥ entry_price
Π ≥ entry_price / (bankroll × base_risk_pct)
```

| Bankroll | Tier | Base Risk | Pre-Multiplier | Min Π for ≥1 share | If $1.00 floor also applies |
|---|---|---|---|---|---|
| $100 | T3_BASE_BUILD | 4.0% | $4.00 | **≥ 13%** | ≥ 25% |
| $150 | T3_BASE_BUILD | ~3.7% | $5.55 | **≥ 10%** | ≥ 18% |
| $250 | T3_BASE_BUILD | 3.0% | $7.50 | **≥ 7%** | ≥ 13% |
| $500 | T4_BASE_STABLE | 2.5% | $12.50 | **≥ 4%** | ≥ 8% |

_Left column: strict necessary condition (≥1 share). Right column: if $1.00 notional floor also binds
(higher bar; verify which gate is active in standard mode before relying on either threshold)._

**Critical caveat:** This dataset contains **zero standard-mode trades**. All 440 are MICRO_SURVIVAL paper
mode. The 0.097-share average provides no information about what the standard multiplier stack would
produce — the multiplier result was discarded by the micro override every time
(`diagnostics["original_position_size"] = 0`). Projections above $100 are bounds only, not empirical
estimates.

**What can be stated without speculation:**
- $20 paper run: structurally below MOS on every trade — signal capture only
- $100 is the mode-switch threshold; it is a necessary but not sufficient condition for executability
- $250–$500 offers more margin (Π threshold drops to 8–13%), making executability more likely for most
  non-blocked signals — but remains empirically unverified without a standard-mode paper run
- Executability should be verified with a purpose-built standard-mode paper session at the target bankroll
  before any live consideration

---

## 6. Is $20 Mode Signal-Only?

**Yes — structurally, by code, not just convention.** Three independent reasons:

**Reason 1 — Fractional share gate is paper+MICRO_SURVIVAL only.**
In live mode at any bankroll, `paper_trading=False` → `_micro_survival_allows_fractional_shares()=False`
→ all 440 signals would have been **SKIPPED**. The fills exist only because paper mode unlocked the gate.

**Reason 2 — Micro override bypasses the multiplier stack.**
Position sizing is set to a flat $0.0502 regardless of signal confidence, EV, spread, or liquidity.
The sizing system is not exercised in a way that reflects live behavior. Paper PnL at this scale is
proportional to the underlying price signal scaled by an average factor (~0.097×; range 0.020–0.287) — it is not a function
of risk-adjusted position sizing.

**Reason 3 — executable_pnl is explicitly blocked by design.**
The canonical table codifies the absence of executable truth: `executable_pnl = None` for every row,
hardcoded. No inference from paper_pnl to live dollar returns is warranted.

**Terminology note:** "SIGNAL_MODE" is not a named mode or code toggle in this codebase. The actual
configuration is `paper_trading=True` + MICRO_SURVIVAL active (bankroll < $100). The intent of the
question — "should $20 mode remain research/signal-only with no live execution?" — is unambiguously
answered: **yes**. The paper dollar amounts are a windowed view of signal quality at a fixed scale
factor, not a projection of live returns.

---

## 7. Governor Verdict

**Verdict: $20 paper run is SIGNAL CAPTURE mode — research only. Live execution is structurally blocked.**

| Criterion | Status |
|---|---|
| All 440 trades are size-dust (shares < 1.0 MOS) | ✓ CONFIRMED |
| 100% of paper trades below MOS_ASSUMPTION = 1 share | ✓ CONFIRMED |
| Fractional shares via paper+MICRO_SURVIVAL gate only | ✓ CONFIRMED |
| Sub-1-share signals would be SKIPPED in live mode | ✓ CONFIRMED |
| executable_pnl intentionally blocked for all 440 trades | ✓ CONFIRMED |
| Signal quality (WR, PF) is valid and scale-independent | ✓ CONFIRMED |
| signal_pnl = paper_pnl (co-assigned same value, lines 389–390) | ✓ CONFIRMED |
| $20 bankroll: structurally insufficient for executable live trades | ✓ CONFIRMED |
| MICRO_SURVIVAL max shares ≈ 0.47 (never reaches 1.0) | ✓ CONFIRMED |
| Mode discontinuity at $100: gate re-activates, even in paper | ✓ CONFIRMED |
| Standard-mode multiplier behavior at $100+: empirically unknown | ✓ CONFIRMED |
| $20 paper run must not inform live execution sizing decisions | ✓ CONFIRMED |

**Bottom line:** The $20 paper run is correctly generating signal quality evidence — WR, PF, regime
context, evidence velocity. It is not generating executable trade data and cannot: the micro survival gate
is paper-only by design, the position size is a fixed override unrelated to signal quality, and all dollar
PnL is a scale-proportional proxy for the underlying price signal.

Paper PnL should not be used to estimate live dollar returns. WR and PF are the relevant metrics for the
ongoing verification campaign.

**Executability requires:** (a) exiting MICRO_SURVIVAL (≥ $100 bankroll), (b) a standard-mode paper run
at target bankroll to verify multiplier behavior empirically, and (c) the full live readiness preflight —
in that sequence, before any live consideration. No shortcuts from current data.

---

*This report is offline research evidence only. It must not be wired into runtime decisions.*
