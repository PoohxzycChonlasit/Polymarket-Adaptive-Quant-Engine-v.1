# Growth-Mode Sizing and Risk Redesign Feasibility Audit

Date: 2026-05-24

Scope: READ ONLY / DESIGN ONLY. No code changes. No runtime changes. No threshold changes. No live.

Prior art:
- `docs/research/executable_truth/paper_sizing_audit.md`
- `docs/research/executable_truth/capital_ladder_audit.md`
- `docs/research/executable_truth/minimum_executable_reality_audit.md`
- `polymarket/bankroll_tiers.py`
- `polymarket/position_sizing.py`
- `polymarket/risk_modes.py`
- `utils/risk_manager.py`

---

## 1. Executive Summary

At `$20` bankroll the system is in `T0_MICRO_SEED` / MICRO / seed_protection. Actual realized paper
orders run at approximately `$0.05` notional and `0.09-0.10` shares. This is `SIMULATION_ONLY` under
the conservative `mos=5` share assumption used across recent audits.

**Nothing in this audit changes sizing, risk, stop-loss, strategy, or live state.**

The audit answers whether a growth-mode path is feasible, what the thresholds should be, and what
must happen before any parameter is touched.

---

## 2. Current Sizing Ladder Limitations

### 2.1 Tier at $20

| Field | Value |
|---|---|
| Tier | `T0_MICRO_SEED` |
| Family | `MICRO` |
| Profile | `seed_protection` |
| Base risk range | `5.0% → 3.0%` (tapering from lower to upper bound) |
| At $20: base risk | ~`3.40%` |
| Base risk budget | `$20 × 3.40% = $0.68` |
| Realized paper order | ~`$0.05` (MICRO survival minimum at `0.25%` of bankroll) |

The gap between the base risk budget (`$0.68`) and the realized paper order (`$0.05`) is caused by two
compounding constraints:

1. **MICRO survival mode** (active below `$100`): caps the position at the survival minimum (`$0.05`
   at `0.25%` of bankroll), regardless of what the sizing multipliers return.
2. **Sizing multipliers** (confidence, EV, spread, liquidity, delta, frequency, time): collectively
   reduced the base budget to around `7.4%` of the base budget in latest observed evidence. Under
   normal market conditions with weaker signals, the multiplier product can be well below `0.10`.

These two factors mean the system is doing what it was designed to do: protect a `$20` seed from
meaningful capital loss. The limitation is not a bug — it is the correct safety behavior for this
bankroll tier.

### 2.2 Structural Floor Problem

The underlying problem is that Polymarket binary markets have a realistic minimum executable order
size. Under the `mos=5 shares` assumption used across these audits, the minimum executable notional
at a common `0.50` entry price is `$2.50`.

At `$20` bankroll with `0.25%` micro-survival risk, the system targets `$0.05` per trade — which is
`50x` below `$2.50`. Even the clean ladder estimate of `$0.63` (at ideal signal quality) is `4x`
below `$2.50`.

This is not a parameter problem. It is a **bankroll problem**. No parameter change makes `$20` into
a realistically executable bankroll under the `mos=5` assumption.

---

## 3. Minimum Executable Size Overlay (mos=5 Reference)

Using `mos=5 shares` as the conservative assumption (consistent with prior audits):

| Entry Price | Min Shares | Min Executable Notional |
|---:|---:|---:|
| `0.20` | `5` | `$1.00` |
| `0.50` | `5` | `$2.50` |
| `0.80` | `5` | `$4.00` |

The `0.50` price is the most common entry range for BTC/ETH 5-minute markets near expiry.
The `$2.50` figure is therefore the working minimum for this analysis.

---

## 4. Bankroll Threshold Analysis

### 4.1 Full Table

| Balance | Tier | Family | Clean Order Size | Shares@0.50 | Shares@0.20 | Shares@0.80 | Executability |
|---:|---|---|---:|---:|---:|---:|---|
| `$20` | T0_MICRO_SEED | MICRO | `$0.63` clean / `$0.05` realized | `0.10` / `1.25` | `0.25` / `3.13` | `0.06` / `0.78` | `SIMULATION_ONLY` |
| `$25` | T1_MICRO_BUILD | MICRO | `$1.38` | `2.76` | `6.90` | `1.73` | `LOW_REALISM` |
| `$50` | T2_MICRO_SURVIVAL | MICRO | `$2.30` | `4.60` | `11.50` | `2.88` | `LOW_REALISM` |
| `$100` | T3_BASE_BUILD | BASE | `$3.68` | `7.36` | `18.40` | `4.60` | `PRACTICAL` |
| `$250` | T4_BASE_STABLE | BASE | `$8.05` | `16.10` | `40.25` | `10.06` | `SAFE_EXECUTION` |
| `$500` | T5_SMALL_GROWTH | GROWTH | `$13.80` | `27.60` | `69.00` | `17.25` | `SAFE_EXECUTION` |
| `$1000` | T6_GROWTH_1 | GROWTH | `$23.00` | `46.00` | `115.00` | `28.75` | `SAFE_EXECUTION` |

Note: "Clean order size" uses ideal signal inputs (confidence 0.75, EV 0.08, good liquidity, no
drawdown). Realized paper orders in the current T0 environment are significantly smaller due to
MICRO survival mode and weaker-than-ideal signal multipliers. The `$0.05` realized figure is
the current paper truth; the `$0.63` clean figure is the theoretical ceiling.

### 4.2 Tier Boundaries

- `$25.00`: exits `T0_MICRO_SEED`, enters `T1_MICRO_BUILD`. Still MICRO family, still MICRO survival.
- `$100.00`: exits MICRO family, enters `T3_BASE_BUILD` (BASE). MICRO survival mode deactivates.
  This is the first tier where paper MICRO survival constraints are lifted.
- `$250.00`: enters `T4_BASE_STABLE`. `SAFE_EXECUTION` classification starts here.

### 4.3 Key Threshold Interpretation

| Threshold | Meaning |
|---|---|
| `$20` (current) | Seed validation only. Signal and lifecycle evidence. PnL is not executable. |
| `$25` | Exits seed protection. Still MICRO, still sub-executable at common prices. |
| `$50` | MICRO survival still active. Near-executable only at cheap prices. |
| `$100` | First BASE tier. MICRO survival off. `PRACTICAL` executability. Minimum for GROWTH_MODE. |
| `$250` | `SAFE_EXECUTION`. Full mos=5 coverage at all common prices. Minimum for EXECUTABLE_MODE. |

---

## 5. Required Order Notional to Clear mos=5 Shares

At `mos=5 shares` and common entry price `0.50`:

```
required_notional = 5 shares × $0.50 = $2.50
```

For the current `$0.05` paper order to meet this:

```
required_bankroll_fraction = $2.50 / bankroll
```

At `$20` bankroll this fraction is `12.5%`. The system's hard single-trade cap is `3%`. Even with
the hard cap removed (which must never happen), placing a `$2.50` order on a `$20` bankroll is
`12.5% risk/trade` — catastrophic by Kelly and all tier risk rules.

This confirms: **`$20` cannot support `mos=5` minimum orders.** The bankroll must grow to at least
`$100` before executable minimums are achievable with conservative risk fractions (3-4% per trade
= `$3.00-$4.00` at `$100`).

---

## 6. Drawdown Risk at $2.5–$5 Minimum Orders on $20 Bankroll

Forcing executable minimum orders (`$2.50-$5.00`) on a `$20` bankroll produces the following
drawdown risk profile:

### 6.1 $2.50 Minimum Orders on $20

| Scenario | Per-trade risk | After 1 loss | After 2 losses | After 4 losses |
|---|---:|---:|---:|---:|
| `$2.50` order, price `0.50` | `12.5%` of bankroll | `$17.50` | `$15.00` | `$10.00` |
| Daily drawdown limit (10%) | triggers at `$2.00` loss | Already breached on first loss | — | — |

A single `$2.50` loss on a `$20` bankroll is `12.5%`, which immediately exceeds the `10%` hard
daily drawdown limit. The risk manager would block further trading after the first loss.

Even without hitting the daily drawdown limit, 4 consecutive losses eliminates half the bankroll.
8 losses eliminate the bankroll entirely, with no meaningful compounding to recover.

### 6.2 $5.00 Minimum Orders on $20

| Scenario | Per-trade risk | After 1 loss | After 2 losses |
|---|---:|---:|---:|
| `$5.00` order | `25%` of bankroll | `$15.00` | `$10.00` |
| Floor breach | `$5.00` floor | 3 losses reach floor | — |

Two `$5.00` losses on a `$20` bankroll leave `$10.00`, hitting the `$5.00` floor at 3 losses.
The floor guard would halt trading entirely.

### 6.3 Conclusion on Forced Minimum Orders

Forcing `$2.50-$5.00` minimum orders on a `$20` bankroll is not aggressive growth — it is
**capital destruction**. The system's risk rules exist precisely to prevent this.

- The per-trade risk exceeds the hard daily drawdown limit on the first loss.
- Floor breach occurs within 3-4 losses.
- No stop-loss or strategy change makes this safer; the bankroll itself is too small.

**Do not force executable minimums on a $20 bankroll. Do not change sizing thresholds to do so.**

---

## 7. Is $20 Too Small for Live Executable Trading?

**Yes, definitively.**

Three separate reasons:

1. **Exchange minimum**: Under `mos=5`, the minimum executable order at `0.50` is `$2.50`. The
   system currently produces `$0.05` orders, which would be rejected by the exchange.

2. **Risk arithmetic**: A `$2.50` order on a `$20` bankroll is `12.5%` risk/trade — more than
   4× the hard single-trade cap (`3%`) and exceeding the daily drawdown limit on the first loss.

3. **Compounding impossibility**: Even at 60% win rate, the expected gain per trade at `$0.05`
   notional and typical binary margins is under `$0.01`. Growing from `$20` to `$100` at this
   rate without luck or capital injection is a multi-year proposition.

The `$20` bankroll is correctly classified as **paper validation capital only**. Its purpose is
signal quality evidence, lifecycle evidence, quote staleness evidence, and outcome truth
validation — not executable PnL growth.

---

## 8. Should Strategy Remain SIGNAL_MODE Until $100?

**Yes.**

The rationale is layered:

### 8.1 Evidence Validity

Trades below `mos=5` produce valid signal evidence:
- Signal confidence and EV field coverage
- Lifecycle timing (OPENING_SCAN → ACTIVE → close)
- Quote lineage and quote staleness
- Outcome truth and TP/SL classification
- Regime and session personality

These are meaningful for strategy research regardless of notional size.

### 8.2 Evidence Invalidity

Trades below `mos=5` do NOT produce valid:
- Executable PnL evidence
- Fill realism (spread and slippage at real size)
- Partial fill risk
- Queue position and maker/taker adverse selection
- Stop-loss and take-profit mechanics at realistic notional

### 8.3 The $100 Threshold

At `$100` (`T3_BASE_BUILD`):
- MICRO survival mode deactivates
- Orders reach `$3.68` clean (7+ shares at `0.50`)
- `PRACTICAL` classification
- Stop-loss and TP mechanics have real notional meaning
- Signal evidence transitions from signal-only to executable-candidate evidence

Until the bankroll or live capital reaches `$100`, the strategy should remain in SIGNAL_MODE.
No parameter changes should be made based on sub-`$100` evidence.

---

## 9. Proposed Paper Mode Additions (Design Only)

These are design proposals for future implementation. **No implementation is authorized by this
audit.**

### 9.1 Proposed Fields

| Field | Purpose | When Active |
|---|---|---|
| `signal_pnl` | PnL computed as if signal fired — regardless of notional | Always |
| `executable_pnl` | PnL only when `notional >= executable_minimum_usd` | When mos filter met |
| `executable_min_reject` | Flag for trades rejected by executable minimum check | When notional < mos |
| `dust_trade_flag` | True when `shares < mos` | Always |
| `executable_size_overlay` | Simulated `notional` at mos=5 shares for comparison | Research mode |
| `executable_minimum_usd` | Applied minimum for this trade (from mos × entry_price) | Always |
| `executable_minimum_met` | Boolean: notional >= executable_minimum_usd | Always |
| `minimum_executable_notional` | The threshold value used for this trade | Always |

### 9.2 Rationale

With these fields, the offline replay system can separate:
- **signal_pnl** (current paper PnL): valid for signal direction research.
- **executable_pnl** (future, post-$100 paper): valid for live-readiness claims.
- **dust_trade_flag**: allows filtering signal evidence from executable evidence.
- **executable_size_overlay**: projects what a real-size trade would have cost and earned.

This separation prevents promoting dust PnL to executable claims without conflating the two.

### 9.3 Implementation Sequencing

Do not implement these fields until:
1. The executable minimum is confirmed from authoritative Polymarket market metadata (not assumed).
2. A separate scoped implementation phase is approved.
3. The SIGNAL_MODE to GROWTH_MODE transition criteria below are understood and agreed upon.

---

## 10. Stop-Loss Analysis: Dust Artifact vs Real Signal

### 10.1 Current Stop-Loss Configuration

From `polymarket/bankroll_tiers.py` (read-only):

| Tier | stop_loss_pct |
|---|---:|
| T0_MICRO_SEED | `0.90` |
| T1_MICRO_BUILD | `0.88` |
| T2_MICRO_SURVIVAL | `0.85` |
| T3_BASE_BUILD | `0.80` |
| T4_BASE_STABLE | `0.78` |
| T5_SMALL_GROWTH | `0.76` |
| T6_GROWTH_1 | `0.75` |

In `build_risk_plan`: `stop_loss_price = entry_price × (1 - stop_loss_pct)`.

At T0 (`stop_loss_pct=0.90`) and entry `0.50`:
```
stop_loss_price = 0.50 × (1 - 0.90) = 0.50 × 0.10 = 0.05
```

This places the stop at a market probability of `0.05` — meaning the position must fall nearly to
zero before the stop triggers. This appears very wide. However, the dynamic_stop_loss_pct function
also exists (min 1%, max 4% of position) and may be the active control path depending on which
code branch is reached.

### 10.2 Observed Paper SL Rate

From `docs/research/executable_truth/paper_sizing_audit.md`, latest 2026-05-23 trade journal:
- `TP: 10` (34%)
- `SL: 19` (66%)

A 66% stop-loss rate on paper trades raises a question: is this a strategy accuracy problem or a
dust-mode artifact?

### 10.3 Dust Artifacts That Inflate SL Rate

At `$0.05` notional and `0.095` shares, the following dust effects distort the observed SL rate:

**Spread dominance**: A one-cent spread across `0.095` shares costs `~$0.001`. The TP target is
roughly `3-6%` of entry, or `$0.001-$0.003` for a `$0.05` position. Spread noise alone can erase
the TP or push price below SL before the market moves directionally.

**Quote staleness noise**: Latest evidence shows `quote_stale_ms` ranging from `10,235ms` to
`32,599ms`. A stale quote can see price bounce by several percent on refresh, triggering SL
on noise rather than directional move.

**Simulation fill artifacts**: Paper fills are simulated at the current quote. At tiny size, the
simulator can fill instantly at mid-market with no slippage. In live execution, the same trade
would face adverse selection and bid/ask spread on a real order book. The observed SL behavior
in paper mode may not reflect live SL mechanics at real size.

**Binary market price behavior**: BTC/ETH 5-minute binary markets near expiry can swing rapidly
between 10% and 90% as news and price action develop. A `$0.05` paper position's SL at market
probability `0.05` may trigger on normal within-window volatility even when the directional signal
is eventually correct.

### 10.4 Is the Stop-Loss Too Tight?

No — and also yes, depending on the frame:

- **In dust mode**: Stop-loss at 90% loss of entry (probability drops to 10% of entry) is not
  "tight" in the traditional sense — it is actually very wide, allowing the position to decay
  nearly to zero before stopping out. The high SL rate in paper is more likely caused by TP
  targets being too small relative to spread and quote noise at tiny notional, not by stops
  being triggered aggressively.

- **In executable mode**: The stop-loss configuration matters at real size. With `$3.68` per
  trade at `$100`, a 90% loss of the entry value before stopping out means absorbing a `$1.84`
  loss (50% of notional at `0.50` entry) before the stop fires. That is a significant per-trade
  loss for a conservative system. Whether this is appropriate depends on market microstructure
  evidence that does not yet exist.

### 10.5 Conclusion on Stop-Loss

**Do not change stop-loss configuration based on dust-mode evidence.**

The observed 66% SL rate in paper is almost certainly a dust-mode artifact driven by spread noise,
quote staleness, and TP targets too small relative to simulation noise — not a real signal about
live SL behavior.

Tuning stop-loss based on this evidence would be optimizing against noise and could dangerously
widen or tighten stops before the system has real executable evidence to support the direction.

**The stop-loss should only be reviewed after executable overlay replay is built and run against
$100+ equivalent paper data.**

---

## 11. Is Changing Stop-Loss Before Executable Replay Dangerous?

**Yes.**

The specific dangers:

1. **Optimizing against simulation artifacts**: Dust-mode PnL statistics are noise, not signal.
   Any stop-loss change motivated by current paper evidence is tuning to noise.

2. **Cascade through tier configs**: Stop-loss values in `bankroll_tiers.py` cascade through
   `build_risk_plan`, `build_micro_survival_risk_plan`, and Kelly position sizing. A change
   in one tier can affect notional risk in ways not apparent from a single-trade view.

3. **Live-mode risk if stop is widened**: Widening the stop before live readiness is proven
   increases potential loss per live trade without evidence that the wider stop improves
   outcome. This is extra dangerous given the allowance/execution path is still unvalidated.

4. **Live-mode risk if stop is tightened**: Tightening the stop on dust evidence may cause
   premature exits in live mode where spread and latency are real, increasing costs.

5. **Paper SL/TP calibration would break**: Current paper evidence is being used to study
   lifecycle, timing, and regime patterns. Changing the SL invalidates the comparison baseline
   for all current and accumulated paper data.

**Decision: freeze stop-loss configuration until executable overlay replay provides real evidence.**

---

## 12. Mode Definitions

### 12.1 SIGNAL_MODE

**Definition**: The system is in SIGNAL_MODE when bankroll < `$100` (MICRO family, any tier 0-2).

**Purpose**: Accumulate signal quality, lifecycle, quote lineage, outcome truth, and regime
evidence. Not executable PnL accumulation.

**Rules**:
- All paper trades labeled `signal_only` or `dust_trade=true`.
- PnL tracked as `signal_pnl` only — not `executable_pnl`.
- No live execution at any sub-`$100` bankroll.
- No stop-loss changes.
- No risk fraction changes.
- No min_position_size_usd changes.
- MICRO survival mode remains active.
- Evidence used for signal calibration and research only.
- SL/TP ratios are diagnostic only; do not tune thresholds based on these ratios.

**Exit condition**: Bankroll >= `$100` AND live execution path validated AND executable overlay
built and run.

### 12.2 GROWTH_MODE

**Definition**: Bankroll `$100-$249` (T3_BASE_BUILD, BASE family). MICRO survival deactivated.

**Purpose**: Transition from signal-only evidence to executable-candidate evidence. First tier
where sizing is `PRACTICAL` and PnL begins to have real meaning.

**Rules**:
- Paper continues; live only when all readiness gates pass (allowance, execution, fill, reconcile).
- Trades tracked with both `signal_pnl` and `executable_pnl` (since `mos=5` is now achievable).
- `dust_trade_flag = false` for most trades at `0.50` entry (orders ~`$3.68`, ~7.4 shares).
- Risk fraction unchanged from tier config (3-4% base risk).
- Stop-loss unchanged from tier config.
- Strategy unchanged.
- Do NOT increase risk fraction beyond tier config to "grow faster."
- `executable_size_overlay` research tracking begins.
- Begin monitoring whether signals survive at executable size (spread, slippage).
- Target accumulation toward `$250` threshold before full executable claims.

**Exit condition**: Bankroll >= `$250`.

**What GROWTH_MODE is NOT**: It is not permission to increase position size, override risk, or
claim live profitability. It means executable-quality sizing begins, but evidence must still
accumulate before live risk is authorized.

### 12.3 EXECUTABLE_MODE

**Definition**: Bankroll >= `$250` (T4_BASE_STABLE and above, SAFE_EXECUTION classification).

**Purpose**: Orders clear `mos=5` at all common price levels with margin. Full signal-to-execution
pipeline can be validated.

**Rules**:
- All readiness gates must be proven before live: orderbook, allowance, order placement, fill,
  cancel, reconciliation.
- Risk per trade remains at tier config (2.5-3.5% for T4, tapering down as bankroll grows).
- Stop-loss reviewed and calibrated only after executable overlay replay provides real evidence.
- Conservative trade frequency (T4: 6-8 trades/hour max).
- Max market exposure (T4: 7% of bankroll).
- `executable_pnl` is the primary PnL signal; `signal_pnl` remains for research comparison.
- No martingale, no averaging down, no `arb_auto_execute`.

---

## 13. Capital Thresholds Summary

| Threshold | Mode | Tier | Key Behavior Change |
|---:|---|---|---|
| `$0-$24.99` | SIGNAL_MODE | T0 MICRO SEED | Seed protection active. `$0.05` realized orders. |
| `$25-$49.99` | SIGNAL_MODE | T1 MICRO BUILD | Exits seed protection. MICRO survival still active. |
| `$50-$99.99` | SIGNAL_MODE | T2 MICRO SURVIVAL | MICRO survival still active. Near-executable only at cheap prices. |
| `$100.00` | GROWTH_MODE entry | T3 BASE BUILD | MICRO survival off. PRACTICAL executability. First real PnL threshold. |
| `$250.00` | EXECUTABLE_MODE entry | T4 BASE STABLE | SAFE_EXECUTION. All prices clear mos=5 with margin. |
| `$500.00` | EXECUTABLE_MODE stable | T5 SMALL GROWTH | Comfortable margin. Trade frequency can increase safely. |
| `$1000.00` | EXECUTABLE_MODE growth | T6 GROWTH 1 | Growth tier. Risk fraction tapers further. |

---

## 14. What to Change Later (Sequenced)

These changes are proposed for future phases only. **None are authorized now.**

### Phase A — Add Executable Overlay (offline, paper-only, no runtime change)
1. Build offline analyzer that applies `mos=5` filter to historical JSONL.
2. Compute `executable_pnl` vs `signal_pnl` separation for all existing paper trades.
3. Label all T0/T1/T2 trades as `SIMULATION_ONLY` or `LOW_REALISM` in offline reports.
4. No runtime sizing change in this phase.

### Phase B — Add Paper Mode Overlay Fields (paper runtime, no live, no strategy change)
1. Add `dust_trade_flag`, `executable_minimum_met`, `executable_minimum_usd`, `executable_pnl`
   fields to paper JSONL events (trade_journal and execution_log producers).
2. Use authoritative `min_order_size` from Polymarket market metadata, not assumed mos=5.
3. No live execution change. No strategy change. No stop-loss change.
4. Requires separate scoped implementation phase with tests.

### Phase C — GROWTH_MODE Live Execution Preparation (at $100+)
1. Resolve live allowance (current blocker).
2. Validate order placement, fill, cancel, reconcile in a tiny controlled live test.
3. Confirm live orderbook path for fresh BTC/ETH markets.
4. Confirm paper/live separation remains intact.
5. Only then consider live trading at T3_BASE_BUILD sizing.

### Phase D — Stop-Loss Review (after Phase A and Phase C evidence exists)
1. Run executable overlay replay against T3+ paper data.
2. Compare SL/TP ratios in executable vs dust-mode paper.
3. Measure spread and slippage impact at real order sizes.
4. Only if evidence supports adjustment: propose a calibrated stop-loss change with a written
   rationale document and test coverage before applying.

### Phase E — EXECUTABLE_MODE Live (at $250+, all prior phases done)
1. All Phase C readiness gates confirmed.
2. Phase D stop-loss review complete.
3. Live capital >= `$250` confirmed.
4. Operate at T4_BASE_STABLE tier parameters.

---

## 15. What NOT to Change Now

| Item | Why Not |
|---|---|
| Stop-loss percentages | Dust-mode SL rate is noise; evidence base is invalid. |
| MICRO survival minimum (`$0.05`) | Correct protective behavior for `$20` seed. |
| Base risk fractions (tier config) | Calibrated by tier; not evidence-backed for change. |
| Min position size guard | Changing it now forces larger orders before bankroll supports it. |
| MICRO survival threshold (`$100`) | Correct family boundary; no evidence to move it. |
| Strategy logic | Paper evidence is `SIMULATION_ONLY`; no strategy signal is confirmed executable. |
| Paper/live separation | Must never be weakened under any circumstance. |
| `arb_auto_execute` default | Must remain `false`. |
| Live execution path | Blocked; allowance not validated. |
| Kelly fractions in tier config | Calibrated conservatively; no evidence to loosen. |
| Hard drawdown limit (10%) | Hard safety limit; must not be relaxed. |
| Floor balance ($5.00) | Hard safety limit; must not be relaxed. |

---

## 16. Answers to Specific Questions

### Q1: Can $20 realistically grow in live Polymarket with this sizing?

**No.**

- `$0.05` orders are below any realistic Polymarket minimum (conservative `mos=5` assumption gives
  `$2.50` minimum at `0.50` entry).
- Live orders would be rejected at the exchange before fill.
- Even if wins accumulate, the compounding rate at `$0.005` per winning trade is too slow to
  reach a meaningful threshold without capital injection.
- The `$20` bankroll is paper validation capital. It is correctly in SIGNAL_MODE.

### Q2: What minimum bankroll makes sense for GROWTH_MODE?

**$100.**

- This is the first tier where MICRO survival mode deactivates.
- Orders reach `PRACTICAL` executability (`mos=5` clearance at `0.50` prices).
- PnL begins to have executable meaning (not just signal meaning).
- Risk per trade (3-4%) × `$100` = `$3-$4` notional, which clears `6-8 shares` at `0.50`.
- The system does not need to be "made ready" at `$100` — it is already designed for this
  tier. GROWTH_MODE at `$100` is using the tier ladder as intended.

Full EXECUTABLE_MODE (SAFE_EXECUTION across all prices) requires `$250`.

### Q3: Should sizing be changed now or only after executable overlay replay?

**Only after executable overlay replay.**

Changing sizing now (before Phase A offline overlay exists) would:
1. Alter the signal evidence baseline being collected.
2. Have no executable benefit at `$20` bankroll.
3. Risk capital without evidence of strategy edge at real size.

The correct sequence is: build executable overlay → run against existing data → get evidence →
then decide if sizing calibration is needed.

### Q4: Should stop-loss / risk / strategy be changed now?

**No.**

- Stop-loss: dust-mode artifact, not valid signal. Do not touch.
- Risk fractions: conservatively set for each tier. No evidence basis for change.
- Strategy: SIMULATION_ONLY evidence does not validate strategy changes.

All three should remain frozen until Phase A (offline executable overlay) and Phase C (live
readiness) are complete.

### Q5: What is the safest redesign path?

The safest path, in sequence:

```
1. Keep current state unchanged (SIGNAL_MODE, paper only, $20 seed)
   └── Collect signal, lifecycle, regime, quote, outcome evidence
   └── Do not interpret dust PnL as executable PnL

2. Build offline executable overlay (Phase A - read-only tools only)
   └── Classify all existing paper trades by mos=5 filter
   └── Separate signal_pnl from executable_pnl in reports
   └── No runtime change

3. Add paper mode overlay fields (Phase B - scoped implementation)
   └── dust_trade_flag, executable_minimum_met, executable_pnl in JSONL
   └── Uses real market metadata, not assumed mos
   └── No strategy, stop-loss, or live change

4. Resolve live readiness blockers (Phase C - parallel with Phase B)
   └── Allowance → order placement → fill → cancel → reconcile
   └── Tiny controlled live validation only with explicit user approval
   └── No capital at risk until each step is confirmed

5. At bankroll >= $100: Graduate to GROWTH_MODE
   └── Tier config already handles this automatically (T3_BASE_BUILD)
   └── MICRO survival deactivates
   └── Monitor executable_pnl vs signal_pnl divergence

6. Stop-loss review after Phase A + Phase C evidence exists (Phase D)
   └── Do not adjust until executable replay shows real SL/TP ratios
   └── Write a separate calibration document before any change

7. At bankroll >= $250 + all gates confirmed: EXECUTABLE_MODE
   └── T4_BASE_STABLE sizing
   └── Live trading with full risk management active
```

---

## 17. Final Classification Table

| Question | Answer |
|---|---|
| Is `$20` bankroll live-executable? | **No.** SIMULATION_ONLY. |
| Is `$20` paper PnL meaningful for strategy? | **Signal direction only.** Not executable PnL. |
| Should sizing be changed now? | **No.** Wait for executable overlay. |
| Should stop-loss be changed now? | **No.** Dust-mode evidence is invalid for SL tuning. |
| Is 66% SL rate a strategy problem? | **Likely not.** Most likely a dust-mode artifact. |
| GROWTH_MODE minimum bankroll? | **$100** (T3_BASE_BUILD, PRACTICAL executability). |
| EXECUTABLE_MODE minimum bankroll? | **$250** (T4_BASE_STABLE, SAFE_EXECUTION). |
| Is $2.5-$5 order on $20 safe? | **No.** Exceeds hard daily drawdown limit on first loss. |
| Should strategy remain SIGNAL_MODE? | **Yes, until $100 and live readiness confirmed.** |
| Should paper mode add overlay fields? | **Yes, in a future scoped implementation phase.** |

---

## 18. Audit Integrity Notes

- No code was modified.
- No runtime parameters were changed.
- No live execution was enabled or modified.
- No thresholds were altered.
- All numbers are derived from existing code (`bankroll_tiers.py`, `position_sizing.py`,
  `risk_manager.py`) and existing audit documents.
- The `mos=5` assumption is conservative and consistent with prior audits. Actual Polymarket
  minimum order size must be confirmed from market metadata before any implementation.
- This document is evidence and design only. It does not authorize any implementation.

---

*Tests: not run. Read-only audit.*
