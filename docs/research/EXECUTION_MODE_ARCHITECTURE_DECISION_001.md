# EXECUTION_MODE_ARCHITECTURE_DECISION_001

Date: 2026-06-20

Mode: READ ONLY / DESIGN ONLY

Runtime behavior changed: No

Strategy/risk/execution changed: No

Commit status: Not committed

## Objective

Design the safest architecture for transitioning from current `SIGNAL_MODE` research to future `EXECUTION_MODE` paper validation without contaminating the existing dust-sized signal evidence.

This decision uses the frozen conclusions from the execution reality audit set:

- 708 / 708 matched historical paper trades fail executable reality thresholds when judged by actual paper order size.
- The first failure point is position sizing, not liquidity.
- Liquidity is not the primary blocker for small fixed-share tests.
- `5 shares` is the best initial execution-size candidate.
- A `$20` bankroll fails 5-share replay.
- Option D behavior changes materially under larger size.
- Prior execution gap verdict: separate Execution Mode paper runtime recommended.

## Section 1 - Current Architecture Analysis

### Signal Generation

Current signal generation produces candidate decisions, market context, lifecycle labels, confidence / EV inputs, and trade intent evidence. This layer remains valuable because it describes when the system would want exposure.

Classification: reusable, but only as signal evidence.

### Paper Execution

Current paper execution simulates fills at dust-sized position sizes. Historical evidence shows median notional near `$0.05`, median shares near `0.095`, and all matched historical trades below `$1`, `5 shares`, and `10 shares`.

Classification: execution-sensitive. It must not be treated as executable Polymarket evidence.

### Risk Modes

Risk modes provide important state context: `NORMAL`, `DEFENSIVE`, `MICRO_RECOVERY`, and `LOCKDOWN`. They are useful for explaining candidate admission and balance-state dependence.

Classification: partially reusable. Risk-mode labels are valid context, but risk behavior must be revalidated when position size increases.

### Option D

Option D is valid as historical signal-mode stop behavior, but prior equal-share replay showed that dust-sized conclusions do not transfer cleanly. It was count-protective in dust evidence, but larger fixed-share replay changed the economics materially.

Classification: execution-sensitive. Option D must be isolated from execution-mode conclusions until replayed and validated at execution size.

### Delta Shadow

Delta Shadow remains useful as passive research / suppression evidence. It should not become an execution approval or rejection path inside a new execution runtime without a separate validation step.

Classification: reusable as observability, execution-sensitive if promoted.

### Trade Journal

The current trade journal is the authoritative record for signal-mode trade opens/closes, timestamps, entry/exit prices, lifecycle, and PnL. It is not an executable PnL ledger.

Classification: reusable for signal history and replay keys; must remain isolated from execution-mode accounting.

### Component Classification

| Component | Reusable | Execution-Sensitive | Must Remain Isolated | Decision |
|---|---:|---:|---:|---|
| Signal generation | Yes | Partial | No | Reuse as input signal source only |
| Market / lifecycle labels | Yes | Partial | No | Reuse as context |
| Current paper fills | Partial | Yes | Yes | Keep as `SIGNAL_MODE` only |
| Current trade journal | Yes | Yes | Yes | Preserve as signal ledger |
| Risk modes | Partial | Yes | Yes | Revalidate under execution size |
| Option D | Partial | Yes | Yes | Revalidate under execution mode |
| Delta Shadow | Partial | Yes | Yes | Keep passive until separately approved |
| PnL / equity curves | Partial | Yes | Yes | Split signal and execution ledgers |
| Live execution path | No | Yes | Yes | Out of scope |

## Section 2 - Architecture Options

### Option A - Single Runtime With Execution Overlays

Description: keep the current runtime and add execution-reality overlays to the same paper path.

| Dimension | Assessment |
|---|---|
| Implementation complexity | Low to medium |
| Research contamination risk | High |
| Operational risk | Medium |
| Replay compatibility | Mixed |
| Observability impact | Good field coverage, but ledger separation is fragile |
| Future live readiness | Weak, because signal and executable accounting remain intertwined |

This option is useful for passive shadow labels, but not sufficient for execution-mode validation. It risks mixing dust fills, scaled estimates, execution-size assumptions, and strategy conclusions in the same runtime history.

### Option B - Separate Execution Paper Runtime

Description: preserve the current signal runtime and add a separate paper execution profile/runtime that consumes the same signal stream or equivalent decision source, but maintains independent execution sizing, bankroll, inventory, risk accounting, journals, and PnL.

| Dimension | Assessment |
|---|---|
| Implementation complexity | Medium |
| Research contamination risk | Low |
| Operational risk | Medium |
| Replay compatibility | High |
| Observability impact | Strong, because signal and execution ledgers can be compared directly |
| Future live readiness | Strongest incremental path |

This option provides the cleanest bridge from signal evidence to executable evidence without rewriting the trading engine prematurely.

### Option C - Separate Execution Engine

Description: build a distinct execution engine architecture for multi-order, multi-price, inventory-aware trading.

| Dimension | Assessment |
|---|---|
| Implementation complexity | High |
| Research contamination risk | Low |
| Operational risk | High |
| Replay compatibility | Requires new harness / validation layer |
| Observability impact | Potentially strong, but expensive |
| Future live readiness | Long-term path, not the next safe step |

This may be the eventual architecture, but current evidence does not justify skipping the execution paper validation layer.

## Section 3 - Execution Paper Design

Preferred architecture: Option B, a separate Execution Mode paper runtime.

### Execution-Size Tracks

The execution runtime should keep fixed execution-size tracks separate from the current dust-sized paper sizing:

| Track | Purpose | Initial Use |
|---|---|---|
| `1_share` | Lowest executable unit sanity check | Diagnostic only |
| `2_shares` | Intermediate sensitivity check | Diagnostic only |
| `5_shares` | Primary execution-size candidate | Main validation track |
| `10_shares` | Stress / scale sensitivity | Diagnostic only |

The initial validation track should be `5_shares`, because prior audits found it to be the best balance between practical execution size, liquidity feasibility, and bankroll stress. `$20` is not adequate for this track.

### Bankroll Model

Execution Mode needs its own bankroll state:

- `execution_starting_bankroll`
- `execution_equity`
- `execution_realized_pnl`
- `execution_unrealized_pnl`
- `execution_drawdown`
- `execution_risk_mode`
- `execution_position_limit_used`

Signal Mode bankroll and paper PnL must remain separate:

- `signal_equity`
- `signal_pnl`
- `signal_drawdown`

Prior capital replay implies:

- `$20` remains signal-only.
- `$100` is the minimum plausible research tier for 5-share validation.
- `$250+` is cleaner for repeated execution-mode validation.

These are design conclusions only, not config changes.

### Inventory Model

Execution Mode should start with a conservative inventory model:

- Fixed-size entries only.
- No averaging down.
- No martingale.
- No reload logic.
- No multi-price ladder until a later validated phase.
- Explicit max concurrent positions.
- Explicit max market exposure.
- Explicit max total exposure.
- Forced isolation from Signal Mode inventory state.

Historical inventory replay showed low concurrency, but larger size increases loss-cluster and drawdown sensitivity. The execution runtime should therefore treat even low-concurrency sequences as new risk evidence.

### Execution Journal

Execution Mode requires a dedicated journal, separate from current signal trade journals.

Minimum fields:

- `event_type`
- `timestamp_utc`
- `run_id`
- `execution_run_id`
- `source_signal_id`
- `condition_id`
- `market_slug`
- `asset`
- `side`
- `lifecycle_phase`
- `execution_track`
- `execution_entry_price`
- `execution_exit_price`
- `execution_shares`
- `execution_notional`
- `execution_pnl`
- `execution_equity_before`
- `execution_equity_after`
- `execution_drawdown_after`
- `signal_entry_price`
- `signal_exit_price`
- `signal_pnl`
- `execution_reject_reason`
- `execution_fill_feasibility`

### PnL Ledger Separation

Execution Mode must maintain separate accounting:

| Signal Ledger | Execution Ledger |
|---|---|
| `signal_pnl` | `executable_pnl` |
| `signal_equity` | `execution_equity` |
| `signal_drawdown` | `execution_drawdown` |
| signal paper fill size | fixed execution share size |
| current dust fills | executable-size simulated fills |

No report should combine signal PnL and executable PnL into one PF, WR, equity curve, or promotion verdict.

## Section 4 - Data Governance

### Valid From Historical SIGNAL_MODE

The following evidence remains valid:

- Candidate timestamps.
- Asset / side / lifecycle labels.
- Entry and exit signal prices.
- Signal-mode TP / SL behavior.
- Trade identity keys.
- Market and session context.
- Path truth where available.
- Liquidity/depth observations as point-in-time context.
- Signal PnL as `signal_pnl` only.

### Must Be Revalidated Under EXECUTION_MODE

The following must be revalidated:

- Executable PnL.
- Executable PF / WR.
- Execution drawdown.
- Loss clusters at fixed share size.
- Option D value at fixed share size.
- Risk-mode transitions under larger drawdowns.
- Position limits.
- Bankroll adequacy.
- Fill feasibility at actual target size.
- Partial-fill and slippage assumptions.
- Any live-readiness claim.

### Evidence Classification

| Evidence Type | Classification | Reason |
|---|---|---|
| Signal timing / lifecycle | Reusable evidence | Independent of size |
| Current signal PnL | Reusable evidence | Signal-mode only |
| Current executable PnL claims | Invalid evidence | Current fills are dust-sized |
| Orderbook top depth | Partial evidence | Useful but not full fill simulation |
| Option D dust result | Partial evidence | Size-sensitive |
| Delta Shadow result | Partial evidence | Still passive and signal-contextual |
| Capital replay scaling | Partial evidence | Informative, not substitute for execution paper |
| `$20` execution viability | Invalid for 5-share execution | 5-share replay fails `$20` |
| Live readiness | Invalid evidence | Live fill/cancel/reconcile still not proven |

## Section 5 - Promotion Roadmap

### Phase 1 - Execution Shadow

Purpose: label current signal-mode paper trades with executable-reality fields without changing size or execution behavior.

Entry criteria:

- Shadow schema frozen.
- No sizing changes.
- No risk changes.
- No order changes.
- No live behavior.

Exit criteria:

- Shadow records are complete enough for daily reporting.
- Dust-zone, `1_share`, `2_shares`, `5_shares`, and `10_shares` feasibility can be measured.
- Field missingness is reported.
- No runtime side effects are observed.

### Phase 2 - Execution Paper Runtime

Purpose: run a separate paper execution profile with fixed execution-size accounting.

Entry criteria:

- Phase 1 shadow evidence is stable.
- Operator explicitly approves implementation.
- Separate execution ledger and journal are defined.
- Starting bankroll tier is explicitly declared.
- Current Signal Mode research remains untouched.

Exit criteria:

- Execution Mode produces independent paper trade records.
- `signal_pnl` and `executable_pnl` remain separate.
- `signal_equity` and `execution_equity` remain separate.
- Option D and risk-mode behavior are separately measurable at execution size.
- No Signal Mode journal contamination occurs.

### Phase 3 - Execution Validation

Purpose: determine whether fixed-size execution evidence survives realistic paper constraints.

Entry criteria:

- Execution Mode has stable journaling.
- Fixed-size track is pre-declared.
- Bankroll assumptions are frozen before evaluation.
- Rejection and fill-feasibility rules are logged.

Exit criteria:

- Execution PF, WR, drawdown, loss streaks, recovery duration, and liquidity rejects are evaluated from the execution ledger only.
- Option D is evaluated under execution-size economics.
- Risk-mode effects are reported separately from signal-mode effects.
- Evidence is classified as PASS / CAUTION / FAIL under a pre-registered validation protocol.

### Phase 4 - Live Readiness

Purpose: decide whether execution-mode paper evidence justifies a future live-readiness process.

Entry criteria:

- Execution Mode validation is complete.
- Live allowance, order placement, cancel, fill, and reconciliation are proven in a separate readiness track.
- No active research question blocks execution promotion.
- Operator explicitly authorizes live-readiness work.

Exit criteria:

- Live-readiness checklist passes.
- Capital limits are defined.
- Kill switches and reconciliation are proven.
- Any live pilot remains separately authorized and bounded.

Phase 4 does not authorize live trading by itself.

## Final Verdict

Decision: B - Build separate execution paper runtime.

Confidence: MEDIUM_HIGH.

Rationale:

- Current Signal Mode should remain intact because it is still useful for candidate discovery and signal behavior.
- A single-runtime overlay is suitable for shadow observability, but not for clean execution validation.
- A full separate execution engine is premature before fixed-size paper execution proves the signal survives real size, bankroll, drawdown, and stop behavior.
- The safest next architecture is a separate Execution Mode paper runtime with independent ledgers, independent journals, fixed execution-size tracks, and strict separation from existing Signal Mode research.

This design does not change runtime behavior, strategy, sizing, risk logic, Option D, Delta Shadow, or live trading.
