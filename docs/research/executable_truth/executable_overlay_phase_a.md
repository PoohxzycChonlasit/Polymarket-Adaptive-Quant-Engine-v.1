# Executable Overlay Phase A Design

Date: 2026-05-24

Scope: DOCS ONLY. Design of the offline executable replay layer. No code. No runtime changes. No live.

Prior art:
- `docs/research/growth_mode_feasibility_audit.md`
- `docs/research/executable_truth/minimum_executable_reality_audit.md`
- `docs/research/executable_truth/capital_ladder_audit.md`
- `docs/research/fast_stop_loss_audit.md`
- `docs/research/executable_truth/paper_sizing_audit.md`

Evidence base:
- `runtime/quant_data/trade_journal/2026-05-22.jsonl`
- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- 54 reliable `trade_close` records with confirmed schema (entry_price, size, pnl, trade_result)

---

## 1. Purpose

The executable overlay is an **offline research layer** that separates the current paper evidence
into three distinct quality tiers: signal edge, tradable edge, and executable edge.

Without this separation, dust-zone paper PnL appears alongside executable-quality evidence as if
they carry equal weight. They do not. Current `$0.05` paper trades cannot be placed on Polymarket.
Their PnL is not executable PnL. The overlay makes this distinction explicit in every report.

This document defines the terms, the filter logic, and the simulation rules. Implementation
is a separate future task and requires explicit scope approval before any code is written.

---

## 2. Term Definitions

### 2.1 SIGNAL_PNL

The PnL produced by the current paper simulator regardless of order size. This is the value already
tracked in `trade_journal` as `pnl_usdc`.

`SIGNAL_PNL` is:
- Valid for direction research (was the model right about the move direction?).
- Valid for lifecycle timing (how long did the trade live before TP or SL?).
- Valid for regime and session pattern research.
- **Not valid** for executable PnL claims.
- **Not valid** for live fill realism, spread impact, partial fill risk, or capital growth claims.

All current paper trades produce `SIGNAL_PNL` only. No current paper trade produces
`EXECUTABLE_PNL`.

### 2.2 EXECUTABLE_PNL

The PnL from a paper trade that meets all executable minimum criteria. A trade produces
`EXECUTABLE_PNL` only when **all** of the following are true:

1. `shares >= mos` (meets the assumed exchange minimum share count).
2. `notional >= mos × entry_price` (notional clears the minimum at the entry price).
3. `notional <= bankroll × hard_cap` (does not violate the hard single-trade cap).
4. The trade's quote age was within the acceptable freshness window at entry.
5. The top-of-book depth at entry was sufficient to fill at the target size (depth coverage check).

Only trades passing all five gates contribute to `EXECUTABLE_PNL` in reports.

`EXECUTABLE_PNL` is **prospective**: it does not exist in current paper data. It will exist once
the bankroll reaches `$100+` and trades begin to clear executable minimums under the T3_BASE_BUILD
tier without MICRO survival compression.

### 2.3 DUST_ZONE

A trade is in the DUST_ZONE when `shares < mos`. The entire current paper evidence corpus is
DUST_ZONE. The classification is applied per-trade and is binary.

DUST_ZONE trades contribute to `SIGNAL_PNL` but are excluded from `EXECUTABLE_PNL`.
They are not discarded — they are labeled and their signal direction is still studied.

DUST_ZONE is not a judgment about signal quality. A DUST_ZONE trade can have a correct directional
signal and useful lifecycle evidence. It simply cannot be placed on the exchange at current size.

Sub-classification within DUST_ZONE:

| Sub-class | Condition | Notes |
|---|---|---|
| `MICRO_DUST` | `shares < 0.10` | Current paper evidence falls here entirely |
| `SUB_MOS` | `0.10 <= shares < mos` | Larger than current but still below exchange minimum |
| `NEAR_MOS` | `mos × 0.5 <= shares < mos` | Close to threshold — reached at T1/T2 bankroll |

### 2.4 EXECUTABLE_MIN_REJECT

A trade tagged `EXECUTABLE_MIN_REJECT` when it would have been blocked by the executable minimum
check in a live or size-validated paper environment.

`EXECUTABLE_MIN_REJECT` is triggered when:
- `shares < mos`, OR
- `notional < mos × entry_price`, OR
- `notional < minimum_order_size_usd` (if confirmed from authoritative market metadata)

All 54 current reliable paper trades are `EXECUTABLE_MIN_REJECT`. This confirms that the entire
current evidence corpus is SIMULATION_ONLY.

`EXECUTABLE_MIN_REJECT` is an **offline label only**. It does not block any current paper trades
at runtime. It is applied retroactively in the overlay analyzer to existing JSONL records.

### 2.5 EXECUTABLE_SIZE_OVERLAY

A synthetic per-trade simulation that projects what the PnL would have been if the same trade
direction had been executed at exactly `mos` shares.

```
overlay_notional    = mos × entry_price
overlay_scale       = mos / actual_shares
overlay_pnl         = actual_pnl × overlay_scale
overlay_capital_pct = overlay_notional / bankroll
```

The `EXECUTABLE_SIZE_OVERLAY` is:
- A **research tool** only.
- Not a sizing recommendation.
- Not permission to increase live or paper order sizes.
- Not a claim about what would have happened in live execution (spread, slippage, queue, partial fill
  are not modeled by a simple linear scale).

It answers the question: *given the same trade direction and exit trigger, what would the P&L have
been at executable size?* This isolates the signal direction from the notional question.

---

## 3. Current Evidence Simulation

This section applies the overlay definitions to the 54 reliable recent paper trades
(2026-05-22 and 2026-05-23) using real JSONL data.

### 3.1 Raw Trade Statistics (Current Paper Reality)

| Metric | Value |
|---|---:|
| Trade close records (reliable schema) | 54 |
| Mean shares per trade | 0.0994 |
| Median shares per trade | 0.0966 |
| Min shares | 0.0223 |
| Max shares | 0.2075 |
| Mean notional (shares × entry_price) | `$0.0525` |
| Max notional | `$0.1287` |
| Min notional | `$0.0143` |
| Mean entry price | 0.5306 |
| Win rate (TP) | 31.5% (17/54) |
| Loss rate (SL) | 68.5% (37/54) |
| Total SIGNAL_PNL | `$-0.1769` |
| Mean TP PnL | `+$0.0088` |
| Mean SL PnL | `-$0.0088` |
| Mean TP contract price move | `+0.0988` |
| Mean SL contract price move | `-0.0862` |
| Mean hold time | 19.2 s |
| Median hold time | 11.5 s |

### 3.2 DUST_ZONE Classification of All Current Trades

Under `mos=5`:

| Filter | Survive | Rejected | Pass Rate |
|---|---:|---:|---:|
| `shares >= 1` | 0 | 54 | 0% |
| `shares >= 3` | 0 | 54 | 0% |
| `shares >= 5 (mos)` | 0 | 54 | 0% |
| `shares >= 10` | 0 | 54 | 0% |
| `notional >= $0.50` | 0 | 54 | 0% |
| `notional >= $1.00` | 0 | 54 | 0% |
| `notional >= $2.50` | 0 | 54 | 0% |
| `notional >= $5.00` | 0 | 54 | 0% |

**All 54 current paper trades are DUST_ZONE / EXECUTABLE_MIN_REJECT at every tested threshold.**

The current paper corpus produces zero `EXECUTABLE_PNL` records. The `SIGNAL_PNL` total of
`-$0.1769` is the only PnL evidence that exists, and it is signal-only.

### 3.3 Entry Price Distribution

| Entry Price Band | Trade Count | mos=5 Notional at Mean Price | Pass mos=5? |
|---|---:|---:|---|
| 0.30–0.39 | 1 | `$1.60` | NO |
| 0.40–0.49 | 6 | `$2.33` | NO |
| 0.50–0.59 | 42 | `$2.68` | NO |
| 0.60–0.69 | 5 | `$3.06` | NO |

No entry price band produces trades that survive any threshold, because the problem is shares
(0.09–0.21), not entry price. Even at the cheapest observed entry (`0.32`), 5 shares would cost
`$1.60` — which is `31x` the mean observed notional of `$0.052`.

### 3.4 EXECUTABLE_MIN_REJECT Count

```
EXECUTABLE_MIN_REJECT count:  54 / 54  (100%)
EXECUTABLE_PNL count:          0 / 54  (0%)
DUST_ZONE (MICRO_DUST):       54 / 54  (100%)
```

All current evidence is `MICRO_DUST`. Maximum observed shares (`0.2075`) is still `24x` below the
`mos=5` threshold.

---

## 4. Signal Edge vs Tradable Edge vs Executable Edge

These are the three edge tiers produced by the overlay analysis. Each answers a different question.

### 4.1 Signal Edge

**Question**: Does the model produce correct directional signals?

**Filter**: All closed paper trades regardless of size.

**Current measurement** (54 recent trades):

| Metric | Value |
|---|---|
| Win rate | 31.5% |
| Total SIGNAL_PNL | `-$0.177` |
| Mean TP move | `+0.099` contract price |
| Mean SL move | `-0.086` contract price |
| Edge classification | NEGATIVE at current win rate |

**Interpretation**: The model is signaling direction. The win rate of 31.5% is below 50%. A neutral
random entry at common binary market prices would expect ~50% TP given symmetric exit mechanics.
The observed 31.5% win rate with fast SL holds (median 11.5s) suggests one or more of:

1. The SL threshold is too tight relative to within-window volatility at these prices.
2. The signal is entering during adverse momentum windows (especially `02h UTC`).
3. The dust-mode simulator exits faster than a live order would (no slippage, no queue delay).
4. The 54-trade sample is too small to confirm statistical edge in either direction.

**What signal edge cannot tell us**: Whether the direction signal survives at executable size
with real spread, queue position, and quote staleness at entry.

### 4.2 Tradable Edge

**Question**: Does the strategy produce positive edge at the minimum tradable size (sub-mos
but above dust threshold)?

**Filter**: Trades where `notional >= $1.00` (approximately T1 at `$25` bankroll, `$1.38`
clean order at `0.50` entry, `2.76` shares). This filter is **hypothetical** — zero current
trades survive it.

**Simulated T1 overlay** (`$25` bankroll, `$1.38` order, scale = 26.3x actual):

| Metric | Simulated Value |
|---|---|
| Scale factor | 26.3× actual PnL |
| Simulated net PnL (54 trades) | `-$4.65` |
| Mean TP per trade | `+$0.232` |
| Mean SL per trade | `-$0.232` |
| Tradable edge | NEGATIVE at 31.5% win rate |

**Interpretation**: At T1 size the signal is still not profitable at current win rates. The
symmetric TP/SL amounts (`+$0.232` / `-$0.232`) indicate the strategy is currently making
symmetric bets with a negative win rate. For tradable edge to be positive, win rate must exceed
50% OR the mean TP must significantly exceed the mean SL (positive reward-to-risk ratio).

Neither condition is met in the current evidence. However, the sample (54 trades) is not
large enough for statistical confidence. Tradable edge remains `UNCONFIRMED`.

### 4.3 Executable Edge

**Question**: Does the strategy produce positive edge at `mos=5` executable minimum?

**Filter**: Trades where `shares >= 5`. Zero current trades survive.

**Simulated mos=5 overlay** (scale = 50.3× actual):

| Metric | Simulated Value |
|---|---|
| Scale factor | 50.3× actual PnL |
| Simulated net PnL (54 trades) | `-$8.90` |
| Mean TP per trade | `+$0.444` |
| Mean SL per trade | `-$0.445` |
| Executable edge | NEGATIVE (simulated) |
| Trades cleared at mos=5 | 0 / 54 |

**Critical finding**: At mos=5 scale on a `$20` bankroll, the 54-trade simulation produces `-$8.90`
in simulated losses — **nearly 50% of the entire bankroll eliminated in 54 trades**. The daily
drawdown limit (`10%` = `$2.00`) is breached after approximately 7 trades in sequential simulation.

**Required bankroll to support mos=5 within the 3% hard cap per trade**:

| Entry Price | mos=5 Notional | Min Bankroll (3% cap) |
|---:|---:|---:|
| `0.32` | `$1.60` | `$53` |
| `0.50` | `$2.50` | `$83` |
| `0.64` | `$3.20` | `$107` |

The system reaches safe territory for mos=5 around `$83-$107` bankroll, which corresponds to
`T2_MICRO_SURVIVAL` to `T3_BASE_BUILD` transition. This aligns with the `$100` GROWTH_MODE
threshold from `docs/research/growth_mode_feasibility_audit.md`.

**Edge summary table**:

| Edge Tier | Filter | Current Trades Passing | Simulated PnL | Win Rate | Status |
|---|---|---:|---:|---:|---|
| Signal Edge | All 54 trades | 54 / 54 | `-$0.177` | 31.5% | NEGATIVE |
| Tradable Edge | notional >= `$1.00` | 0 / 54 | `-$4.65` (sim) | 31.5% | UNCONFIRMED |
| Executable Edge | shares >= `mos=5` | 0 / 54 | `-$8.90` (sim) | 31.5% | UNCONFIRMED |

All three edge tiers are currently negative or unconfirmed. The negative signal edge is not
proof that the strategy has no edge — it means 54 trades at dust size with a current 31.5% win
rate do not demonstrate a confirmed edge. Larger sample at executable size is required.

---

## 5. Phase A Architecture Design

### 5.1 Scope

Phase A is an **offline-only, no-runtime, no-live** analyzer that reads existing JSONL trade records
and produces a structured overlay report. It is equivalent in architecture to `tools/replay_analyzer.py`
and `tools/quant_data_quality.py` — offline tools only.

Phase A produces no changes to:
- `polymarket/trader.py`
- `polymarket/position_sizing.py`
- `polymarket/bankroll_tiers.py`
- `utils/risk_manager.py`
- Any config or settings file
- Any paper or live execution path

### 5.2 Input Sources

| Input | Source | Notes |
|---|---|---|
| Trade records | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | `event_type=trade_close` |
| Execution records | `runtime/quant_data/execution_log/YYYY-MM-DD.jsonl` | Fill confirmation, quote age |
| Risk records | `runtime/quant_data/risk_log/YYYY-MM-DD.jsonl` | Sizing context |
| Market snapshots | `runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl` | Depth, spread at entry |

### 5.3 Configuration Parameters

All parameters are design-time constants for the overlay. They do not affect runtime:

| Parameter | Design Value | Source |
|---|---|---|
| `mos` (minimum order shares) | `5` (conservative assumption) | This audit; must be confirmed from real metadata |
| `hard_cap_pct` | `0.03` (3%) | `utils/risk_manager.py` `HARD_CAP_SINGLE_TRADE` |
| `daily_dd_limit_pct` | `0.10` (10%) | `utils/risk_manager.py` `HARD_DAILY_DRAWDOWN` |
| `floor_balance_usd` | `5.00` | `utils/risk_manager.py` `FLOOR_BALANCE` |
| `quote_freshness_limit_ms` | `30_000` (30s) | Consistent with existing stale-data guards |
| `depth_coverage_multiplier` | `1.5×` | Conservative: top depth must be ≥ 1.5× order size |

### 5.4 Per-Trade Classification Logic

For each `trade_close` record, the overlay applies the following sequential gates:

```
Gate 0: Schema check
  - Has entry_price, size, pnl, trade_result? → PASS / SCHEMA_INVALID

Gate 1: DUST_ZONE check
  - shares < mos? → DUST_ZONE_REJECT
    sub-classify: MICRO_DUST / SUB_MOS / NEAR_MOS

Gate 2: Notional check
  - notional < mos × entry_price? → NOTIONAL_REJECT
  (If Gate 1 passed, this should also pass — belt-and-suspenders)

Gate 3: Hard cap check
  - notional / bankroll > hard_cap_pct? → CAPITAL_REJECT
  (Only relevant at bankrolls where mos=5 notional approaches the cap)

Gate 4: Quote freshness check (if execution_log joinable)
  - entry quote_stale_ms > quote_freshness_limit_ms? → QUOTE_STALE_REJECT

Gate 5: Depth coverage check (if market_snapshot joinable)
  - top_depth_shares < mos × depth_coverage_multiplier? → DEPTH_REJECT

→ If all gates pass: EXECUTABLE_PNL_APPROVED
→ Otherwise: EXECUTABLE_MIN_REJECT (with gate label)
```

### 5.5 Overlay Fields per Trade

The overlay produces one record per closed trade with these fields:

| Field | Type | Description |
|---|---|---|
| `candidate_id` | str | Join key from trade_journal |
| `date` | str | YYYY-MM-DD |
| `asset` | str | BTC / ETH |
| `side` | str | YES / NO |
| `entry_price` | float | Market entry price |
| `actual_shares` | float | Shares in current paper trade |
| `actual_notional` | float | `actual_shares × entry_price` |
| `actual_pnl` | float | Raw paper PnL (`pnl_usdc`) |
| `trade_result` | str | TP / SL |
| `hold_seconds` | float | Duration of trade |
| `dust_zone` | bool | `actual_shares < mos` |
| `dust_zone_sub_class` | str | MICRO_DUST / SUB_MOS / NEAR_MOS |
| `executable_min_reject` | bool | True if any gate failed |
| `executable_reject_gate` | str | Which gate caused reject |
| `executable_reject_reason` | str | Human-readable reason |
| `mos_shares` | float | Assumed mos value used |
| `mos_notional` | float | `mos × entry_price` |
| `overlay_scale` | float | `mos / actual_shares` |
| `overlay_pnl` | float | `actual_pnl × overlay_scale` (SIMULATION only) |
| `overlay_capital_pct` | float | `mos_notional / bankroll` |
| `overlay_exceeds_hard_cap` | bool | `mos_notional / bankroll > hard_cap_pct` |
| `signal_pnl` | float | Same as `actual_pnl` (always populated) |
| `executable_pnl` | float | Same as `actual_pnl` only if EXECUTABLE_PNL_APPROVED |
| `pnl_classification` | str | SIGNAL_ONLY / EXECUTABLE_APPROVED |
| `quote_stale_ms_at_entry` | float | From execution_log join (null if not joinable) |
| `quote_freshness_ok` | bool / null | Pass/fail for Gate 4 |
| `top_depth_at_entry` | float / null | From market_snapshot join (null if not joinable) |
| `depth_coverage_ok` | bool / null | Pass/fail for Gate 5 |

### 5.6 Aggregate Report Structure

The overlay analyzer produces one JSON report file per date or date range, mirroring the
existing report convention in `runtime/reports/`.

**Report file naming**:
```
runtime/reports/executable_overlay_YYYY-MM-DD.json
runtime/reports/executable_overlay_YYYY-MM-DD_to_YYYY-MM-DD.json
```

**Report sections**:

```
{
  "generated_at": "...",
  "scope": "offline executable overlay v1",
  "date_range": "...",
  "mos": 5,
  "hard_cap_pct": 0.03,
  "daily_dd_limit_pct": 0.10,

  "trade_summary": {
    "total_trades": N,
    "dust_zone_count": N,
    "dust_zone_pct": N,
    "executable_approved_count": N,
    "executable_approved_pct": N,
    "executable_min_reject_count": N
  },

  "dust_zone_breakdown": {
    "MICRO_DUST": N,
    "SUB_MOS": N,
    "NEAR_MOS": N
  },

  "reject_gate_counts": {
    "DUST_ZONE_REJECT": N,
    "NOTIONAL_REJECT": N,
    "CAPITAL_REJECT": N,
    "QUOTE_STALE_REJECT": N,
    "DEPTH_REJECT": N,
    "SCHEMA_INVALID": N
  },

  "signal_edge": {
    "trades": N,
    "win_rate": F,
    "total_pnl": F,
    "mean_tp_pnl": F,
    "mean_sl_pnl": F,
    "mean_tp_hold_s": F,
    "mean_sl_hold_s": F,
    "edge_classification": "NEGATIVE|NEUTRAL|POSITIVE|INSUFFICIENT_SAMPLE"
  },

  "tradable_edge": {
    "threshold_notional_usd": F,
    "trades_above_threshold": N,
    "simulated_scale": F,
    "simulated_net_pnl": F,
    "edge_classification": "NEGATIVE|NEUTRAL|POSITIVE|INSUFFICIENT_SAMPLE|NO_REAL_TRADES"
  },

  "executable_edge": {
    "mos": N,
    "trades_above_mos": N,
    "total_executable_pnl": F,
    "simulated_overlay_pnl": F,
    "overlay_capital_pct_mean": F,
    "overlay_capital_pct_max": F,
    "edge_classification": "NEGATIVE|NEUTRAL|POSITIVE|INSUFFICIENT_SAMPLE|NO_REAL_TRADES"
  },

  "bankroll_impact_simulation": {
    "starting_bankroll": F,
    "sequential_sim_final_bankroll": F,
    "floor_breach_at_trade": N_or_null,
    "daily_dd_breach_at_trade": N_or_null,
    "survival_rate": F
  },

  "per_trade_records": [ ... ]
}
```

### 5.7 Command Interface (Design)

Proposed CLI (not implemented):

```bash
# Single date overlay
python tools/executable_overlay.py --date 2026-05-23

# Date range
python tools/executable_overlay.py --from 2026-05-22 --to 2026-05-23

# With custom mos (if real mos becomes known)
python tools/executable_overlay.py --date 2026-05-23 --mos 3

# Write report
python tools/executable_overlay.py --date 2026-05-23 --write-report

# Run-scoped (to isolate a single paper run)
python tools/executable_overlay.py --date 2026-05-23 --run-id 20260523T160429Z_24512_1677a602
```

This interface is consistent with `tools/replay_analyzer.py` and `tools/quant_data_quality.py`.
It is a design proposal only. Actual CLI arguments are subject to implementation decisions.

---

## 6. Simulating Current $20 Evidence Under mos=5

This section applies the Phase A design to the 54 current reliable paper trades as a manual
simulation. This is the pre-implementation result — what the overlay tool would produce.

### 6.1 Overall Classification

```
Total trades:                    54
DUST_ZONE (MICRO_DUST):          54  (100%)
EXECUTABLE_MIN_REJECT:           54  (100%)
EXECUTABLE_PNL_APPROVED:          0  (0%)
```

**No current paper trade survives the mos=5 filter at any entry price.**

### 6.2 Bankroll Drawdown Simulation (Sequential mos=5 Overlay)

Starting bankroll: `$20.00`. Daily drawdown limit: `$2.00` (10%). Floor: `$5.00`.
Scale: 50.3× actual PnL (mos=5 / mean actual shares).

| Trade # | Result | Simulated PnL | Bankroll | Daily Loss | Status |
|---:|---|---:|---:|---:|---|
| 1 | SL | `-$0.85` | `$19.15` | `$0.85` | OK |
| 2 | TP | `+$0.30` | `$19.45` | `$0.85` | OK |
| 3 | SL | `-$0.25` | `$19.20` | `$1.10` | OK |
| 4 | TP | `+$0.30` | `$19.50` | `$1.10` | OK |
| 5 | SL | `-$0.55` | `$18.95` | `$1.65` | OK |
| 6 | SL | `-$0.35` | `$18.60` | `$2.00` | WARNING |
| **7** | **SL** | **`-$0.40`** | **`$18.20`** | **`$2.40`** | **DAILY_DD_BREACH** |

**Daily drawdown limit breached at trade 7.** The risk manager would halt trading for the
rest of the session. This happens before any meaningful sample of executable trades accumulates.

If run to completion without the daily DD halt (full 54 trades):
```
Simulated net PnL at mos=5: -$8.90
Final bankroll: $11.10 (starting from $20.00)
Capital loss: -44.5% in 54 trades
```

This confirms: **`$20` is not a viable bankroll for live mos=5 execution with the current strategy
win rate and exit mechanics.**

### 6.3 Which Trades Survive Executable Overlay?

Under strict `mos=5`:

```
Survivors: 0 of 54 (0%)
All 54 trades: EXECUTABLE_MIN_REJECT via DUST_ZONE_REJECT
```

Under relaxed mos=1:

```
Survivors: 0 of 54 (0%)
Maximum observed shares: 0.2075 — still below 1 share
```

Under notional >= $0.50:

```
Survivors: 0 of 54 (0%)
Maximum observed notional: $0.1287 — still below $0.50
```

**The current evidence has no executable survivors at any realistic threshold.** The overlay
finds the same result regardless of how generously the mos threshold is set.

### 6.4 What Needs to Change Before Survivors Exist

The overlay will begin finding EXECUTABLE_PNL_APPROVED trades only when:

| Condition | Required Change |
|---|---|
| Shares per trade >= 5 | Bankroll grows to ~$100+ AND MICRO survival deactivates |
| Notional per trade >= $2.50 | Same — bankroll grows AND tier config allows larger sizing |
| Daily DD limit not breached at trade 7 | Bankroll large enough that $2.50 losses are < 10% of daily |

None of these conditions are met at `$20`. No parameter change to the current sizing logic
produces executable trades at `$20` without violating the hard cap or daily drawdown rules.

---

## 7. Signal Edge Interpretation and Cautions

### 7.1 What the 31.5% Win Rate Means

A 31.5% win rate across 54 trades does not confirm the strategy has negative edge. It means:

- The current 54-trade sample has produced 17 TP and 37 SL.
- At `p=0.50` and `n=54`, a 31.5% result is not statistically unusual (it is within 2σ of
  50% for a small sample — binomial std dev ≈ 6.8% at n=54).
- The mean TP PnL (`+$0.0088`) and mean SL PnL (`-$0.0088`) are nearly symmetric, meaning the
  strategy is not achieving a significantly positive reward-to-risk ratio.
- Fast SL exits (median 11.5s) suggest the SL trigger is firing on within-window volatility
  rather than sustained adverse moves in many cases.

**The signal edge is currently neither confirmed positive nor confirmed negative.** The sample
is too small and the sizing too small to draw reliable statistical conclusions.

### 7.2 What the Overlay Cannot Prove

The `EXECUTABLE_SIZE_OVERLAY` linear-scale simulation (`overlay_pnl = actual_pnl × 50.3x`) is
an arithmetic projection, not an execution simulation. It does not model:

- Real spread costs at mos=5 size (spread at `$2.50` order is not the same as at `$0.05`)
- Queue position and fill probability at different order sizes
- Partial fill risk when top-of-book depth < mos
- Market impact of larger orders near expiry
- Adverse selection at the ask vs bid for real taker orders
- Time-in-force behavior and fill latency

The overlay projection is therefore a **lower bound on real-world drag** at executable size.
Actual executable PnL is likely worse than the linear projection due to these friction costs.

### 7.3 Minimum Sample for Reliable Edge Measurement

Before any signal edge claim is made, the following minimums are needed:

| Evidence Quality | Minimum Trades | Condition |
|---|---:|---|
| Preliminary signal direction | 100 | At dust size, any bankroll |
| Tentative signal edge claim | 200 | At dust size, all sessions represented |
| Tradable edge claim | 100 | At notional >= $1.00 (T1+ bankroll) |
| Executable edge claim | 100 | At mos=5 or higher (T3+ bankroll) |
| Reliable edge claim | 500 | At executable size across multiple market regimes |

Current status: 54 trades at dust size. Preliminary signal direction analysis is possible.
No edge claim is supported at any tier.

---

## 8. Phase A Implementation Requirements (Future)

This section defines what must be true before Phase A implementation begins. These are
prerequisites, not instructions to implement now.

### 8.1 Pre-implementation Checklist

| Requirement | Status |
|---|---|
| Design document approved (this doc) | Pending approval |
| `mos` value confirmed from Polymarket market metadata | NOT DONE — currently assumed 5 |
| Existing JSONL schema stability confirmed | Partially done (schema varies by date) |
| `candidate_id` join key present in all target records | Partially done (present in May 22-23) |
| Offline tool does not modify any runtime file | Required constraint |
| Tests cover empty input, schema mismatch, zero trades | Required |
| Report output goes to `runtime/reports/` only | Required |
| Tool is explicitly read-only with respect to JSONL inputs | Required |

### 8.2 Schema Compatibility Note

Historical JSONL records before 2026-05-22 use a different `size` field schema (apparent integer
vs fractional share units). Phase A implementation must handle schema versioning explicitly. The
recommended approach:

- Filter: only process records where `entry_price > 0 AND 0 < size < 2`.
- Warn and skip records where size appears to be a legacy integer schema.
- Report the count of skipped/schema-incompatible records separately.

### 8.3 mos Confirmation Requirement

The `mos=5` assumption is conservative and consistent across audits, but it is not confirmed from
authoritative Polymarket exchange documentation or market metadata.

Before Phase A produces reports that influence trading decisions:
1. Confirm actual minimum order size from Polymarket CLOB documentation or real API response.
2. Update `mos` parameter in the tool config when confirmed.
3. Re-run overlay reports with confirmed mos and note the change in report metadata.

Until then, all overlay reports must include a prominent caveat:
```
WARNING: mos=5 is an assumed minimum, not confirmed from exchange metadata.
Executable edge classifications are conservative estimates only.
```

### 8.4 What Phase A Does Not Do

Phase A explicitly does NOT:
- Change any runtime sizing parameter.
- Block any current paper trade.
- Modify any JSONL record.
- Feed results into runtime decisions.
- Constitute permission to change stop-loss, risk fractions, or strategy.
- Constitute permission to begin live trading.

Phase A is evidence accumulation only. Any decision to change sizing, risk, or live behavior
requires a separate explicitly scoped task with written rationale and test coverage.

---

## 9. What Comes After Phase A

Phase A is the first of a multi-phase executable evidence path. The downstream phases are:

| Phase | Description | Prerequisite |
|---|---|---|
| Phase A | Offline overlay — classify existing evidence | This document approved |
| Phase B | Paper JSONL overlay fields — add executable fields at runtime | Phase A complete + mos confirmed |
| Phase C | Live readiness — allowance, order, fill, reconcile validation | Independent |
| Phase D | Stop-loss calibration review | Phase A + Phase C evidence |
| Phase E | EXECUTABLE_MODE live at `$250+` | All prior phases |

Phase A output informs Phase B field design. Phase A does not authorize Phase D or Phase E.

---

## 10. Summary

### 10.1 Core Findings

| Finding | Evidence |
|---|---|
| 100% of current trades are DUST_ZONE | 54/54 shares below 0.21, mos=5 requires 5.0 |
| 100% are EXECUTABLE_MIN_REJECT | 0 trades clear any realistic notional threshold |
| SIGNAL_PNL exists | `-$0.177` across 54 trades — valid for direction research |
| EXECUTABLE_PNL = $0 | No current trade produces executable PnL |
| mos=5 simulation is destructive at $20 | Daily DD breach at trade 7; -44.5% bankroll in 54 trades |
| Signal edge is currently negative | 31.5% win rate; symmetric TP/SL PnL |
| Signal edge conclusion | Sample too small for reliable claim in either direction |
| GROWTH_MODE bankroll minimum | `$100` (T3_BASE_BUILD, MICRO survival off, PRACTICAL) |
| EXECUTABLE_MODE bankroll minimum | `$250` (T4_BASE_STABLE, SAFE_EXECUTION) |

### 10.2 Three-Edge Summary

| Edge | Current Measurement | Interpretation |
|---|---|---|
| **Signal Edge** | 31.5% win rate, `-$0.177` total, 54 trades | NEGATIVE / INSUFFICIENT_SAMPLE |
| **Tradable Edge** | 0 real trades; simulated `-$4.65` at T1 scale | UNCONFIRMED / NO_REAL_TRADES |
| **Executable Edge** | 0 real trades; simulated `-$8.90` at mos=5 | UNCONFIRMED / NO_REAL_TRADES |

### 10.3 What Must NOT Change Based on This Analysis

- Stop-loss thresholds — dust-mode artifact, not executable evidence.
- Risk fractions — insufficient evidence at any executable tier.
- MICRO survival minimum — correct protection for `$20` bankroll.
- Strategy logic — no executable evidence to validate strategy changes.
- Live execution — allowance and execution path still unvalidated.

### 10.4 What Phase A Enables

Once implemented:
- Clear separation of SIGNAL_PNL from EXECUTABLE_PNL in all research reports.
- Automatic DUST_ZONE and EXECUTABLE_MIN_REJECT labeling for every paper trade.
- EXECUTABLE_SIZE_OVERLAY projection for research-only use.
- Foundation for Phase B paper JSONL overlay fields.
- Quantified answer to "which trades survive executable overlay" updated automatically
  as more paper sessions run.

---

*Tests: not run. Docs-only design.*
