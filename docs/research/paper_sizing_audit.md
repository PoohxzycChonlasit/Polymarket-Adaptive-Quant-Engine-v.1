# Paper Sizing Audit

Date: 2026-05-23

Scope: read-only audit of latest paper trade sizing path.

Runtime behavior changed: No
Live behavior changed: No

## Verdict

Latest paper sizing is using MICRO seed protection behavior as intended.

The latest matched paper trade was a very small ETH NO position:

- run_id: `20260523T160429Z_24512_1677a602`
- candidate_id: `candidate_4f9e1d34c744`
- trade: ETH NO
- lifecycle at entry: `OPENING_SCAN`
- entry timestamp: `2026-05-23T16:05:11.639040Z`
- close timestamp: `2026-05-23T16:05:41.542457Z`
- result: `TP`
- pnl_usdc: `+0.005724`

The sizing path stayed paper-only and tiny: planned notional was about five cents, and actual filled notional matched it.

## Evidence Sources

- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`
- `runtime/quant_data/decision_log/2026-05-23.jsonl`
- `runtime/quant_data/risk_log/2026-05-23.jsonl`
- `runtime/quant_data/system_health/2026-05-23.jsonl`
- `logs/polytrade_bot_20260523_230428_24512.log`
- `polymarket/bankroll_tiers.py`
- `polymarket/position_sizing.py`
- `polymarket/order_manager.py`
- `polymarket/trader.py`
- `utils/risk_manager.py`
- `config/settings.py`

## Latest Trade Sizing

| Field | Value |
|---|---:|
| raw bankroll / paper sizing balance | about `$20.10` |
| exact post-close paper cash/equity | `$20.1047` |
| tier | `T0_MICRO_SEED` |
| tier family | `MICRO` |
| risk profile | `seed_protection` |
| bankroll mode | `MICRO_SURVIVAL` |
| risk mode | `NORMAL` |
| base risk pct | `3.39%` |
| final risk pct | `0.25%` |
| raw base risk budget | about `$0.6818` |
| planned notional | `$0.050562` |
| entry price | `0.53` |
| planned/actual shares | `0.095400` |
| actual filled notional | `$0.050562` |
| blockers | none for executed ETH trade |

Execution evidence:

- `[BANKROLL_RANK] APPROVED tier=T0_MICRO_SEED bankroll=$20.10 base_risk=3.39% final=$0.05 risk=0.25% reasons=none`
- `[DECISION] ETH NO ... entry=0.5300 shares=0.1 cost=$0.0506`
- `[PAPER BALANCE_GUARD] ETH OK -- paper_available_balance $20.10 >= cost $0.05`
- `[PAPER ORDER] ... price=0.5300 size=0.095400 live_orders=OFF`
- trade journal `notional_size=0.050562`, `size=0.0954`

## Sizing Path

1. Paper sizing balance

The paper path used paper cash/equity, not live funds. The latest run logged paper available balance around `$20.10`; after the winning close it logged cash/equity `$20.1047`.

2. Tier assignment

`bankroll=$20.10` maps to `T0_MICRO_SEED` because `polymarket/bankroll_tiers.py` defines that tier for `$0.00` to `$25.00`.

3. Family selection

`T0_MICRO_SEED` belongs to family `MICRO` with profile `seed_protection`.

4. Risk multiplier

The base risk budget was about `$0.6818`:

```text
$20.10 bankroll * 3.39% base risk ~= $0.6818
```

The approved final notional was about `$0.0506`, so the effective aggregate sizing multiplier was roughly:

```text
$0.0506 / $0.6818 ~= 0.074
```

This means the final position was about `7.4%` of the base risk budget, or `0.25%` of bankroll.

5. Seed protection effect

Seed protection kept the position near the MICRO survival minimum instead of allowing a standard larger bankroll-rank size. The system remained in:

- `bankroll_mode=MICRO_SURVIVAL`
- `micro_survival_active=true`
- `micro_position_size~=0.0502`
- `tier_id=T0_MICRO_SEED`
- `family=MICRO`
- `profile=seed_protection`

6. Final order size path

```text
paper sizing balance ~= $20.10
-> T0_MICRO_SEED
-> MICRO / seed_protection
-> base risk budget ~= $0.6818
-> aggregate sizing/risk reduction
-> planned notional ~= $0.0506
-> entry price 0.53
-> shares = 0.050562 / 0.53 = 0.095400
-> paper fill size = 0.095400
```

## Latest Trade Table

| Timestamp UTC | Asset | Side | Entry | Exit | Planned Notional | Actual Size | Result | PnL |
|---|---|---|---:|---:|---:|---:|---|---:|
| 2026-05-23T16:05:11Z | ETH | NO | 0.53 | 0.59 | `$0.050562` | `0.095400` | TP | `+0.005724` |

## Recent Paper Trade Context

Latest 2026-05-23 trade journal state:

- trade_open count: `29`
- trade_close count: `29`
- assets: ETH `24`, BTC `5`
- results: TP `10`, SL `19`
- observed notional range: `$0.014279` to `$0.072503`
- mean opened notional: `$0.049616`

Recent trade sizes are consistently tiny, usually around `$0.05`, which matches MICRO survival / seed protection sizing rather than standard larger-risk sizing.

## Blockers Observed After Latest Trade

After the latest ETH TP, the same market was blocked by lifecycle/session controls:

- `Max entries per market reached`
- `Max active positions per market reached` while the position was open

BTC candidates in the same run were blocked by sizing/confidence:

| Time UTC | Asset | Reason | Evidence |
|---|---|---|---|
| 2026-05-23T16:05:12Z | BTC | `confidence_too_low` | `[BANKROLL_RANK] BLOCKED ... reasons=confidence_too_low` |
| 2026-05-23T16:06:14Z | BTC | `confidence_too_low` | zero-size probe: `final_size_usd=0.0`, `blocked_reasons=["confidence_too_low"]` |
| 2026-05-23T16:06:59Z | BTC | `confidence_too_low` | zero-size probe: `final_size_usd=0.0`, `blocked_reasons=["confidence_too_low"]` |

Representative zero-size probe:

- bankroll: `$20.0981`
- tier_id: `T0_MICRO_SEED`
- tier_family: `MICRO`
- base_risk_pct: `0.033922`
- raw_size_usd: `$0.681757`
- final_size_usd: `$0.000000`
- micro_survival_active: `true`
- micro_position_size: `$0.050245`
- blocked_reasons: `["confidence_too_low"]`

## Observability Notes

Approved order JSONL confirms planned notional and actual fill size, but it does not currently include the full per-multiplier sizing breakdown for approved trades.

Zero-size probes include detailed multiplier fields:

- confidence multiplier
- EV multiplier
- drawdown multiplier
- liquidity multiplier
- spread multiplier
- time-to-settlement multiplier
- delta multiplier
- frequency multiplier

For approved trades, the strongest sizing evidence is split across:

- order-manager log for tier/base risk/final risk
- decision/trade JSONL for target exposure, notional, and fill
- risk/system-health JSONL for current MICRO survival state

## Final Answer

1. Paper sizing balance:

The latest paper trade used paper balance around `$20.10`, not live capital.

2. Tier assignment:

`$20.10` maps to `T0_MICRO_SEED`.

3. Family selection:

`T0_MICRO_SEED` maps to family `MICRO`.

4. Risk multiplier:

Base risk was `3.39%`, but final notional was only `0.25%` of bankroll. Effective aggregate reduction was about `0.074x` of the base risk budget.

5. Seed protection effect:

Seed protection kept the trade around `$0.05` notional and blocked low-confidence BTC candidates.

6. Final order size path:

The executed ETH trade planned `$0.050562`, bought `0.095400` shares at `0.53`, and closed at `0.59` for `+0.005724` USDC.

Tests: not run; read-only audit.

