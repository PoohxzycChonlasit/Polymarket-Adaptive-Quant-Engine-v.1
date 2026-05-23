# Minimum Executable Reality Audit

Date: 2026-05-23

Scope: read-only audit of whether current paper order sizes are realistically executable on Polymarket.

Runtime behavior changed: No
Live behavior changed: No

## Verdict

Current `$0.05` paper orders are not meaningful live-execution evidence.

The latest clean paper run traded around `$0.0503` notional and `0.091-0.099` shares. That is below even the repo's local `min_shares_per_order=1` setting, and far below the conservative executable scenario requested for this audit: `mos=5 shares`.

Treat current T0/T1 paper trades as signal, lifecycle, quote-age, and outcome-truth evidence only. Do not treat their PnL as executable-PnL evidence.

## Sources

- `docs/research/paper_sizing_audit.md`
- `docs/research/capital_ladder_audit.md`
- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`
- `config/settings.py`
- `polymarket/position_sizing.py`
- `polymarket/trader.py`

## Metadata Check

Local runtime evidence and repo metadata did not expose a current Polymarket `min_order_size`, `minimum_order_size`, or `mos` field.

Observed local guards:

| Source | Field | Value / Behavior |
|---|---|---|
| `config/settings.py` | `min_shares_per_order` | `1` share |
| older decision JSONL | `min_position_size_usd` | `$1.00` guard on rejected rows |
| latest paper trade rows | actual filled shares | about `0.09-0.10` shares |

Because current market metadata is unavailable locally, this audit uses the conservative assumption requested by the task:

```text
assumed executable minimum = 5 shares
```

## Latest Paper Evidence

Latest run:

```text
run_id = 20260523T160429Z_24512_1677a602
trade_open = 4
trade_close = 4
paper_fill = 8
```

Open-trade sizing:

| Metric | Value |
|---|---:|
| notional min | `$0.050252` |
| notional mean | `$0.050340` |
| notional max | `$0.050562` |
| shares min | `0.091367` |
| shares mean | `0.095978` |
| shares max | `0.098592` |
| entry price range | `0.51-0.55` |

Paper fill sizing:

| Metric | Value |
|---|---:|
| fill notional min | `$0.038374` |
| fill notional mean | `$0.049077` |
| fill notional max | `$0.058146` |
| fill shares min | `0.091367` |
| fill shares mean | `0.095978` |
| fill shares max | `0.098592` |
| quote_stale_ms min | `10235.869` |
| quote_stale_ms mean | `15960.614` |
| quote_stale_ms max | `32598.740` |

Latest open rows:

| UTC | Asset | Side | Entry | Shares | Notional | Top Ask Depth | Top Bid Depth | `min_fillable_size_usd` |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 16:05:11 | ETH | NO | `0.53` | `0.095400` | `$0.050562` | `11.80` | `11.80` | `$35.900` |
| 16:10:37 | ETH | YES | `0.51` | `0.098553` | `$0.050262` | `54.80` | `56.80` | `$91.800` |
| 16:15:11 | ETH | NO | `0.51` | `0.098592` | `$0.050282` | `3.00` | `3.00` | `$35.000` |
| 16:20:25 | BTC | YES | `0.55` | `0.091367` | `$0.050252` | `165.23` | `184.11` | `$335.455` |

Interpretation:

- The simulated fills are tiny fractional-share fills.
- They do not test order placement, exchange minimums, queue priority, maker/taker fill mechanics, partial fill handling, or live rejection behavior.
- The orderbook can have ample depth, but current simulated order size is too small to be a realistic executable child order.

## Conservative Minimum Notional

Assuming `mos=5 shares`:

| Contract Price | Minimum Shares | Minimum Executable Notional |
|---:|---:|---:|
| `0.20` | `5` | `$1.00` |
| `0.50` | `5` | `$2.50` |
| `0.80` | `5` | `$4.00` |

Current paper size comparison:

| Current Paper Size | At Price `0.20` | At Price `0.50` | At Price `0.80` |
|---:|---:|---:|---:|
| `$0.05` | `0.25` shares | `0.10` shares | `0.0625` shares |

Current paper orders are `20x-80x` too small by notional under the `5 share` assumption, depending on contract price.

## Capital Ladder Executability

Representative clean order sizes are from `docs/research/capital_ladder_audit.md` plus a local check for `$25`.

Classification rules:

- `SIMULATION_ONLY`: below the assumed 5-share minimum even at `0.20`.
- `LOW_REALISM`: can clear 5 shares only at cheap prices, but not at common `0.50` or expensive `0.80` prices.
- `PRACTICAL`: clears 5 shares at common `0.50` prices, but has limited margin at high prices.
- `SAFE_EXECUTION`: clears 5 shares across `0.20`, `0.50`, and `0.80` with comfortable margin.

| Balance | Tier | Family | Expected Order Size | Shares at `0.20` | Shares at `0.50` | Shares at `0.80` | Classification |
|---:|---|---|---:|---:|---:|---:|---|
| `$20` | `T0_MICRO_SEED` | MICRO | `$0.6256` | `3.13` | `1.25` | `0.78` | `SIMULATION_ONLY` |
| `$25` | `T1_MICRO_BUILD` | MICRO | `$1.3800` | `6.90` | `2.76` | `1.73` | `LOW_REALISM` |
| `$50` | `T2_MICRO_SURVIVAL` | MICRO | `$2.3000` | `11.50` | `4.60` | `2.88` | `LOW_REALISM` |
| `$100` | `T3_BASE_BUILD` | BASE | `$3.6800` | `18.40` | `7.36` | `4.60` | `PRACTICAL` |
| `$250` | `T4_BASE_STABLE` | BASE | `$8.0500` | `40.25` | `16.10` | `10.06` | `SAFE_EXECUTION` |
| `$500` | `T5_SMALL_GROWTH` | GROWTH | `$13.8000` | `69.00` | `27.60` | `17.25` | `SAFE_EXECUTION` |
| `$1000` | `T6_GROWTH_1` | GROWTH | `$23.0000` | `115.00` | `46.00` | `28.75` | `SAFE_EXECUTION` |

Important caveat:

The `$20` clean ladder example is `$0.6256`, but current live paper evidence is closer to `$0.05` because MICRO survival and signal multipliers compress actual orders. Therefore current T0 live paper behavior is even less executable than the clean ladder table suggests.

## Bucket Classification

| Bucket | Balance / Behavior | Executability | Notes |
|---|---|---|---|
| Current paper `$0.05` / `0.09` shares | latest T0 evidence | `SIMULATION_ONLY` | Below 1 share and far below assumed 5 shares. |
| T0 clean ladder | `$0-$24.99` | `SIMULATION_ONLY` | Still below assumed 5 shares at common prices. |
| T1 | `$25-$49.99` | `LOW_REALISM` | May work only when contract price is low; not robust. |
| T2 | `$50-$99.99` | `LOW_REALISM` | Near common-price threshold but still below 5 shares at `0.50`. |
| T3 | `$100-$249.99` | `PRACTICAL` | Clears common-price minimum; high-price orders may still be marginal. |
| T4+ | `$250+` | `SAFE_EXECUTION` | Clears assumed 5-share minimum across representative prices. |

## Fill Realism

Current paper fills are useful for:

- signal lifecycle timing,
- quote lineage and quote staleness coverage,
- outcome truth attachment,
- TP/SL classification,
- session/regime evidence,
- paper-only PnL direction as a diagnostic.

Current paper fills are not sufficient for:

- live minimum-order acceptance,
- real queue fill probability,
- partial-fill risk,
- live taker slippage,
- maker/taker adverse selection,
- executable-PnL claims.

## Spread And Slippage Impact

At tiny paper size, spread and slippage are under-tested because the simulator can fill fractional dust instantly.

Under an executable minimum, the same strategy would need to absorb:

- minimum order notional of about `$1-$4` under the `5 share` assumption,
- potential one-cent spread cost of about `$0.05` for a 5-share order,
- larger relative slippage if top-of-book depth is thin or quote age is stale,
- partial-fill or no-fill risk near market close.

For a `$0.05` paper order, a one-cent/share spread across `0.095` shares is less than `$0.001`. For a 5-share order, the same one-cent/share spread is `$0.05`, which is roughly the entire latest paper order notional. This is why current dust PnL should not be promoted to executable PnL.

## Partial-Fill Risk

The latest open rows show top-of-book depth ranging from `3.00` to `184.11` shares, depending on market and side.

Under `mos=5 shares`:

- the ETH 16:15 row with top depth `3.00` shares would be partial-fill or non-executable at the top level if 5 shares had to clear immediately at that price;
- the ETH 16:05 row with top depth `11.80` shares could clear a 5-share order at top level, but with limited margin;
- the BTC 16:20 row had ample top depth, but current simulated size was still only `0.091367` shares.

So executable sizing is not only about bankroll. It also needs per-trade checks against live minimum order rules, top-of-book depth, spread, quote freshness, and allowed partial-fill behavior.

## Answers

1. Is current `$0.05` / `0.09`-share paper size meaningful for live execution?

No. It is meaningful as paper signal and lifecycle evidence, but not as live-executable evidence. It is below even a 1-share local guard and far below the conservative `5 share` assumption.

2. At what bankroll does the current ladder become practically executable?

Using clean representative sizing, the ladder becomes `PRACTICAL` at about `$100` bankroll (`T3_BASE_BUILD`). It becomes `SAFE_EXECUTION` at about `$250` bankroll (`T4_BASE_STABLE`). Current realized T0 behavior around `$20` remains `SIMULATION_ONLY`.

3. Should paper sizing enforce an executable-minimum overlay in research mode later?

Yes. Future research mode should add an offline or paper-only executable-minimum overlay so that PnL can be separated into:

- `signal_pnl_simulated_dust`
- `executable_pnl_candidate`
- `blocked_below_exchange_minimum`

This should be research/observability only unless a later implementation task explicitly scopes runtime sizing policy.

4. Should current T0/T1 paper trades be excluded from executable-PnL claims?

Yes. Current T0/T1 trades should be excluded from executable-PnL claims. They can remain in signal-quality, lifecycle, quote-staleness, and outcome-truth studies, but should be labeled `SIMULATION_ONLY` or `LOW_REALISM` for executable edge.

## Future Options

OPTION 1 - SAFE EV PRESERVATION:

Keep current runtime unchanged and label dust trades as non-executable in research docs and monitors.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:

Add a future offline analyzer that reclassifies historical paper fills against assumed or discovered minimum order rules without changing runtime behavior.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:

Later, when explicitly scoped, add a paper research overlay that records `executable_minimum_met`, `minimum_executable_notional`, `expected_live_shares`, and `below_minimum_reason` alongside paper fills.

Recommended path: OPTION 1 now, OPTION 2 next. Do not change runtime sizing until the minimum-order contract is verified from authoritative market metadata.

## Final Classification

Current state: `SIMULATION_ONLY` for latest `$0.05` paper orders.

Practical ladder threshold: about `$100`.

Safe execution threshold: about `$250`.

Tests: not run; docs-only read-only audit.
