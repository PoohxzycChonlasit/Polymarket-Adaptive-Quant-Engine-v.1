# Capital Ladder Audit

Date: 2026-05-23

Scope: read-only audit of bankroll tier ladder, T0_MICRO_SEED sizing, risk-mode multipliers, and representative order-size examples.

Runtime behavior changed: No
Live behavior changed: No

## Verdict

The system leaves seed protection at `$25.00` raw bankroll.

Important distinctions:

- Seed protection tier ends at `$25.00`: `T0_MICRO_SEED` is `$0.00 <= balance < $25.00`.
- MICRO family ends at `$100.00`: `T0`, `T1`, and `T2` are all `MICRO`.
- Paper `MICRO_SURVIVAL` bankroll mode remains active below `$100.00`, so a `$50` account has left seed protection but is still MICRO survival.
- BASE family starts at `$100.00`.

## Sources

- `polymarket/bankroll_tiers.py`
- `polymarket/position_sizing.py`
- `polymarket/risk_modes.py`
- `utils/risk_manager.py`
- `config/settings.py`

## Tier Ranges

| Balance Range | Tier | Family | Profile | Base Risk Range | Max Market Exposure | Min/Max Hint |
|---:|---|---|---|---:|---:|---:|
| `$0-$24.99` | `T0_MICRO_SEED` | MICRO | seed_protection | `5.0% -> 3.0%` | `10%` | `$0.01-$1.25` |
| `$25-$49.99` | `T1_MICRO_BUILD` | MICRO | micro_build | `6.0% -> 4.0%` | `10%` | `$0.02-$3.00` |
| `$50-$99.99` | `T2_MICRO_SURVIVAL` | MICRO | micro_survival | `5.0% -> 4.0%` | `9%` | `$0.05-$5.00` |
| `$100-$249.99` | `T3_BASE_BUILD` | BASE | base_build | `4.0% -> 3.0%` | `8%` | `$0.50-$10.00` |
| `$250-$499.99` | `T4_BASE_STABLE` | BASE | base_stable | `3.5% -> 2.5%` | `7%` | `$0.75-$17.50` |
| `$500-$999.99` | `T5_SMALL_GROWTH` | GROWTH | small_growth | `3.0% -> 2.0%` | `6%` | `$1.00-$30.00` |
| `$1000-$2499.99` | `T6_GROWTH_1` | GROWTH | growth_1 | `2.5% -> 1.5%` | `5%` | `$2.00-$62.50` |

## Requested Capital Ladder

Representative order examples use the current local sizing function with clean favorable inputs:

- confidence `0.75`
- EV `0.08`
- entry price `0.50`
- spread `0.01`
- good liquidity
- neutral delta multiplier `1.0`
- time remaining `300s`
- no drawdown
- no frequency pressure

Because spread multiplier is still applied, expected order size is about `92%` of base risk budget in this clean example.

| Balance | Tier | Family | Profile | Base Risk/Trade | Base Risk Budget | Expected Order Size | Order % of Balance |
|---:|---|---|---|---:|---:|---:|---:|
| `$20` | `T0_MICRO_SEED` | MICRO | seed_protection | `3.40%` | `$0.68` | `$0.6256` | `3.13%` |
| `$50` | `T2_MICRO_SURVIVAL` | MICRO | micro_survival | `5.00%` | `$2.50` | `$2.3000` | `4.60%` |
| `$100` | `T3_BASE_BUILD` | BASE | base_build | `4.00%` | `$4.00` | `$3.6800` | `3.68%` |
| `$250` | `T4_BASE_STABLE` | BASE | base_stable | `3.50%` | `$8.75` | `$8.0500` | `3.22%` |
| `$500` | `T5_SMALL_GROWTH` | GROWTH | small_growth | `3.00%` | `$15.00` | `$13.8000` | `2.76%` |
| `$1000` | `T6_GROWTH_1` | GROWTH | growth_1 | `2.50%` | `$25.00` | `$23.0000` | `2.30%` |

## T0_MICRO_SEED Path

For `$20` bankroll:

```text
balance = $20
-> tier = T0_MICRO_SEED
-> family = MICRO
-> profile = seed_protection
-> base risk ~= 3.40%
-> base risk budget ~= $0.68
-> position_sizing multipliers
-> expected clean order ~= $0.6256
```

Recent live paper evidence showed smaller realized notional, about `$0.05`, because actual market signals had weak confidence/liquidity/delta multipliers and MICRO survival minimum behavior constrained the final practical order.

## Risk Mode Percentages

| Risk Mode | Trigger | Size Multiplier | New Entries |
|---|---|---:|---|
| `NORMAL` | default | `100%` | allowed |
| `DEFENSIVE` | drawdown `>=2%` or losses `>=2` | `50%` | allowed with higher quality bar |
| `MICRO_RECOVERY` | drawdown `>=4%` or losses `>=3` | `25%` | allowed with highest quality bar |
| `LOCKDOWN` | hard drawdown or explicit lockdown reason | `0%` | blocked |

Hard daily drawdown config is `10%`; position-sizing hard drawdown guard defaults to `15%`. In practice, explicit runtime hard-drawdown/lockdown reasons can force `LOCKDOWN` before any order.

## Micro Survival Settings

From current settings:

| Setting | Value |
|---|---:|
| paper micro survival threshold | `$100.00` |
| micro survival minimum position | `$0.05` |
| micro survival risk fraction | `0.25%` |
| max risk per trade from `.env` | `1.00%` |
| hard max single trade risk | `3.00%` |

Micro survival notional is capped by the smallest compatible risk fraction. At `$20`, `0.25%` equals `$0.05`, matching the tiny recent paper order behavior.

## Transition Answers

When does the system leave seed protection?

- Raw tier leaves `T0_MICRO_SEED` at `$25.00`.
- It enters `T1_MICRO_BUILD` from `$25.00` to `$49.99`.
- It enters `T2_MICRO_SURVIVAL` from `$50.00` to `$99.99`.
- It leaves MICRO family and paper MICRO survival mode at `$100.00`.

Does the system jump directly from seed protection to standard sizing?

No. It leaves seed protection at `$25`, but remains MICRO until `$100`.

Does `$50` still behave conservatively?

Yes. `$50` is `T2_MICRO_SURVIVAL`, still MICRO family, with paper MICRO survival active below `$100`.

## Operational Interpretation

The capital ladder is conservative:

- `$20`: seed-protected validation capital.
- `$50`: still MICRO, larger but survival-oriented.
- `$100`: first BASE tier, no paper micro-survival mode.
- `$250+`: base/stable/growth progression with tapering risk percentages.
- `$1000`: growth tier but still capped at `2.5% -> 1.5%` base risk range.

Tests: not run; read-only audit.

