# Quant Lifecycle Inventory Engine

> Status: official future system specification.
> Scope: docs-only architecture target. This document does not implement runtime behavior, enable inventory trading, authorize live trading, or change current paper/live execution.

## 1. System Purpose

The project is migrating from single-entry scalping toward Quant Lifecycle Inventory Trading.

The old philosophy was mostly:

```text
wait for one clean signal
-> ENTER or SKIP
-> exit as one position
```

That model is too narrow for Polymarket BTC/ETH 5-minute markets. These markets compress opportunity into a short window where scanner delay, token readiness, orderbook warmup, spread normalization, liquidity timing, and cutoff pressure can consume the useful part of the trade before a perfect sniper entry appears.

The new philosophy is lifecycle participation:

```text
understand the market window early
-> estimate probability, fair value, EV, regime, liquidity, and risk budget
-> choose bounded target exposure
-> manage inventory through open, reduce, hold, stop loss, final derisk, or runner decisions
```

The system must remain paper-first, risk-first, and evidence-first. This specification defines the future target. It does not change the current runtime.

## 2. Market Window Lifecycle

The official 5-minute lifecycle phases are:

| Phase | Window | Purpose | Restrictions |
|-------|--------|---------|--------------|
| `OPENING_SCAN` | 0-35 seconds | Preload market, resolve token IDs, warm orderbook, establish first tradable second, measure early spread/liquidity. | No forced inventory behavior. No live-risk change. Do not trade on stale, missing, or unreconciled data. |
| `ACTIVE_INVENTORY_TRADING` | 35-240 seconds | Future bounded starter entry, limited reload, hold, or reduce decisions when EV, probability, liquidity, and risk budget agree. | No unlimited reloads. No martingale. No risk or OrderIntent bypass. |
| `PROFIT_MANAGEMENT` | 240-270 seconds | Harvest gains, reduce exposure as edge decays, protect realized PnL, and prepare for final derisk. | No new oversized exposure. No turning winners into uncontrolled losses. |
| `FINAL_DERISK` | 270-300 seconds | Cancel unnecessary orders, reduce most exposure, stop unsafe inventory, and allow only capped runner logic if all safety gates pass. | No new entries. Forced exit and panic exit override runner logic. |
| `CLOSED_OR_UNSAFE` | Any unsafe or closed state | Stop trading when market closed, orderbook stale, reconciliation blocked, risk budget exhausted, or LOCKDOWN active. | No entries, reloads, or runner continuation. |

Lifecycle timing is measured from market open. Implementation tasks may adapt exact clock source later, but must preserve these conceptual responsibilities.

## 3. Quant Decision Model

The future system no longer thinks only `ENTER / SKIP`.

It decides:

- target exposure
- current inventory state
- current exposure versus target exposure
- risk budget usage
- whether the next action should be `OPEN`, `REDUCE`, `HOLD`, `BLOCK`, `STOP_LOSS`, `FINAL_DERISK`, or `RUNNER_ALLOWED`

Required concepts:

- probability
- fair value
- edge
- EV
- spread quality
- liquidity
- volatility
- regime
- time remaining
- current exposure
- target exposure
- bankroll tier
- realtime risk budget

An action is valid only if quant edge, executable microstructure, time window, risk budget, and position/reconciliation state agree. A high-probability estimate is not a trade approval by itself.

## 4. Scanner Lifecycle Philosophy

The scanner must evolve from:

```text
discover market after open
-> wait for tokens
-> wait for orderbook
-> evaluate late
-> cutoff blocked
```

toward:

```text
preload next market
-> cache token IDs
-> warm orderbook immediately
-> mark first tradable second
-> evaluate from early window
-> participate earlier when safe
```

Key scanner lifecycle delays:

- market discovery delay
- token ID delay
- orderbook warmup delay
- spread normalization delay
- liquidity readiness delay
- candidate timing decay

Scanner lifecycle evidence must explain whether no-entry behavior is caused by late discovery, missing tokens, empty/stale books, spread/liquidity readiness, candidate timing, risk, or execution safety.

## 5. Entry Philosophy

Future inventory starts with a starter entry only.

Starter entry is allowed only when:

- EV is positive after executable spread assumptions
- probability edge is sufficient
- spread is acceptable
- liquidity is ready
- orderbook is fresh
- time remaining is sufficient
- risk budget is available
- reconciliation is healthy
- OrderIntent validation is valid
- regime/probability context supports exposure

Explicitly forbidden:

- random entries
- revenge entries
- loss-chasing
- emotional sizing
- entries designed only to force activity
- entries that bypass cutoff, spread, stale-book, risk, reconciliation, or OrderIntent gates

The first entry should be small enough that the system can still stop out, unload, or derisk without threatening bankroll survival.

## 6. Profit Unload Philosophy

Profit should be harvested gradually.

Required future behavior:

- unload 25-40% at the first profit objective
- unload 30-50% at the second profit objective
- reduce exposure when edge decays
- protect realized profit
- avoid turning winners into uncontrolled losses

Inventory recycling means realized profit can reduce the risk burden of remaining exposure. Realized PnL and unrealized PnL must be tracked separately. Exposure reduction is a decision based on fair value, EV decay, spread/liquidity, time remaining, and risk budget, not a cosmetic exit.

## 7. Stop Loss Philosophy

Stop loss is required.

Future stop-loss logic must include:

- position loss threshold
- probability flip exit
- liquidity deterioration exit
- stale orderbook exit
- risk-mode `LOCKDOWN` exit
- forced exit override
- panic exit override

Core rule:

```text
cut losses early, preserve bankroll survival
```

The system must never hold a deteriorating position because it hopes for a late rescue. If edge, liquidity, data freshness, or risk budget fails, the correct action is reduce, stop loss, final derisk, or block.

## 8. Final Derisk Philosophy

In the last 30 seconds:

- no new entries
- cancel unnecessary orders
- reduce 80-95% of exposure
- allow an optional tiny lucky runner only if all safety gates pass

Runner logic is allowed only if:

- the position is profitable or risk-contained
- runner size is capped
- orderbook is not stale
- reconciliation is healthy
- risk mode is not `LOCKDOWN`
- forced exit and panic exit are not active

Forced exit overrides runner logic.

The purpose of a tiny runner is asymmetric upside preservation after downside has been contained. It is not an excuse to leave uncontrolled exposure into expiry.

## 9. Bounded Reload / Unload Philosophy

Reload is allowed only if:

- EV remains positive
- probability still supports exposure
- liquidity remains acceptable
- spread remains executable
- risk budget remains available
- drawdown remains acceptable
- market lifecycle phase still allows reload
- reconciliation and OrderIntent gates pass

Explicitly forbidden:

- martingale
- unlimited averaging down
- increasing size only because of losses
- infinite reload chains
- reloads after risk budget is exhausted
- reloads that create unplanned final-derisk pressure

Quant inventory scaling is bounded exposure adjustment around probability, fair value, liquidity, and risk budget. Gambling behavior increases size because the previous action lost. This system must always be the former and never the latter.

## 10. Dynamic Quant Risk Budget Engine

The future system replaces rigid fixed order-count thinking such as `0/3`.

Risk budget must be dynamic and based on:

- realtime bankroll
- current equity
- open exposure
- realized PnL
- unrealized PnL
- drawdown
- volatility
- liquidity
- edge quality
- bankroll tier
- current risk mode

Conceptual sizing:

```text
allowed_market_risk_usd =
    bankroll * tier_risk_percent * risk_mode_multiplier

order_size_usd =
    allowed_market_risk_usd
    * edge_multiplier
    * liquidity_multiplier
    * volatility_multiplier
    * drawdown_multiplier
    * time_multiplier
```

The system may allow additional small orders only if risk budget remains safe. More orders are not automatically more risk if exposure is reduced elsewhere, profit has been realized, or target exposure remains capped. Fewer orders are not automatically safe if one order is oversized.

Risk budget, not order count, is the future source of truth.

## 11. Realtime Bankroll State

All future trading decisions must reference realtime bankroll state.

Tracked values:

- `starting_bankroll`
- `current_cash`
- `current_equity`
- `open_exposure`
- `realized_pnl`
- `unrealized_pnl`
- `available_risk_budget`
- `market_risk_used`
- `session_risk_used`
- `drawdown_percent`
- `tier_id`
- `risk_mode`
- `target_exposure`
- `current_exposure`

The action decision must be explainable as:

```text
given bankroll state + position state + lifecycle phase + edge + liquidity + regime,
why is the correct action OPEN, REDUCE, HOLD, BLOCK, STOP_LOSS, FINAL_DERISK, or RUNNER_ALLOWED?
```

## 12. Tier-Based Bankroll System

Tier behavior must make larger bankrolls more disciplined, not more reckless.

| Tier | Bankroll Range | Risk Per Market | Max Total Exposure | Starter Sizing | Reload Permissions | Unload Behavior | Runner Allowance | Drawdown Response | Survival Priority |
|------|----------------|-----------------|--------------------|----------------|--------------------|-----------------|------------------|-------------------|------------------|
| `T0_MICRO_SEED` | tiny seed / below stable base bankroll | Minimal; survival-only | Very low | Smallest practical paper size | Rare or disabled until evidence proves feasibility | Fast unload and strict stop | Usually disabled or dust-only after profit | Rapid defensive mode / LOCKDOWN | Highest |
| `T1_SMALL` | small bankroll | Low | Low | Small starter only | Limited reload only with strong EV and liquidity | Early partial unload | Tiny capped runner only after realized profit | Reduce risk quickly | Very high |
| `T2_BASE` | base operating bankroll | Conservative normal | Moderate | Starter sized by tier risk budget | Bounded reload if EV and budget remain strong | Standard 25-40% then 30-50% unload path | Allowed if capped and risk-contained | Defensive sizing after drawdown | High |
| `T3_GROWTH` | growth bankroll | Lower percent risk than smaller tiers | Controlled moderate/high | More scalable but still capped | Bounded reload with stronger evidence requirements | More systematic profit recycling | Allowed only after profit lock | Tier demotion or risk-mode reduction | High |
| `T4_CAPITAL` | larger capital | Lowest relative risk | Strict portfolio cap | Conservative institutional-style starter | Reload only with high-quality liquidity and low drawdown | Aggressive profit protection and exposure discipline | Small relative runner only | Fast exposure reduction under stress | Highest |

Each tier must define:

- bankroll range
- risk per market
- max total exposure
- starter sizing behavior
- reload permissions
- unload behavior
- runner allowance
- drawdown response
- survival priority

Capital growth should reduce reckless risk expansion. Higher tiers should have better discipline, tighter drawdown response, and lower relative risk per decision.

## 13. Bankruptcy Protection

Required hard guards:

- `bankroll_floor`
- `max_market_loss`
- `max_session_loss`
- `max_daily_loss`
- `max_drawdown_lock`
- forced exit
- panic exit
- `LOCKDOWN` mode
- exposure caps

The system must prioritize long-term survival over short-term gain.

No edge estimate, regime label, replay result, or inventory theory may override bankruptcy protection.

## 14. Observability Requirements

Required runtime visibility for future implementation:

- bankroll
- exposure
- target exposure
- edge
- EV
- fair value
- regime
- spread
- liquidity
- risk budget
- reload decisions
- unload decisions
- derisk state
- runner state
- stop-loss reason
- lifecycle phase

Every inventory/risk decision must be explainable after replay. The operator should be able to answer:

- What was the lifecycle phase?
- What was the estimated edge?
- What did fair value imply?
- What was executable spread/liquidity?
- What was the risk budget before and after the action?
- Why did the system open, reload, unload, hold, stop out, derisk, block, or allow a runner?

Observability must remain compact. Do not log full orderbooks continuously or create unbounded runtime logs.

## 15. Safety Boundaries

This specification explicitly preserves:

- paper mode default
- no live readiness claim
- no live deployment authorization
- no martingale
- no unlimited averaging down
- no all-in behavior
- no risk bypass
- no OrderIntent bypass
- no reconciliation bypass
- no stale-orderbook usage
- forced exit and panic exit priority
- wallet and allowance safety
- paper/live separation
- offline analyzer separation from runtime decisions

## 16. Implementation Roadmap

Future implementation phases:

| Phase | Name | Scope | Live Readiness |
|-------|------|-------|----------------|
| Phase A | Spec only | This document and routing references. | None implied. |
| Phase B | Lifecycle phase classifier | Classify market window phase in diagnostics/paper observability. | None implied. |
| Phase C | Paper-only starter entry | Evaluate starter-entry behavior in paper mode only. | None implied. |
| Phase D | Profit unload + stop loss | Add paper-safe unload and stop-loss behavior with tests. | None implied. |
| Phase E | Dynamic quant risk budget | Replace rigid order-count thinking with budget-aware paper decisions. | None implied. |
| Phase F | Bounded reload/unload | Add strictly capped paper reload/unload behavior. | None implied. |
| Phase G | Final derisk + lucky runner | Add final derisk and capped runner behavior under safety gates. | None implied. |
| Phase H | Tier-based inventory scaling | Scale behavior by bankroll tier and risk mode in paper first. | None implied. |
| Phase I | Paper evidence review | Decide whether evidence supports further runtime hardening. | None implied. |

No phase implies live readiness. Live readiness remains separately blocked until live allowance, order placement, fill, cancel, and reconciliation are proven.

## 17. Promotion Gates

The system may progress only if:

- tests pass
- paper evidence exists
- evaluator confirms useful data
- risk remains controlled
- no live path changed
- operator explicitly approves the next phase
- paper/live separation is preserved
- OrderIntent and reconciliation remain enforced
- stale-book, forced-exit, and panic-exit protections remain active

Promotion must be explicit. A good replay table is not permission to change runtime behavior.

## 18. Future File Ownership

Likely future files, depending on scoped implementation phase:

- `config/settings.py`
- `polymarket/trader.py`
- `polymarket/order_manager.py`
- `polymarket/order_intent.py`
- `utils/risk_manager.py`
- `utils/position_tracker.py`
- `utils/display.py`
- `tools/session_runtime_evaluator.py`
- `tests/test_paper_mode.py`
- `tests/test_execution_risk_controls.py`

No runtime edits are authorized by this document.

## 19. What This Spec Does Not Authorize

This document does not authorize:

- runtime changes
- live trading
- live wallet usage
- allowance changes
- risk bypass
- execution bypass
- scanner rewrite
- strategy threshold changes
- risk sizing code changes
- paper/live behavior changes
- inventory trading activation
- multi-entry runtime behavior
- reload/unload runtime logic
- runner runtime logic
- offline analyzer output feeding automatic runtime decisions

Any future implementation must be a separate scoped task with read-first docs, responsible agents, relevant files, minimal diffs, focused tests, and explicit operator approval.
