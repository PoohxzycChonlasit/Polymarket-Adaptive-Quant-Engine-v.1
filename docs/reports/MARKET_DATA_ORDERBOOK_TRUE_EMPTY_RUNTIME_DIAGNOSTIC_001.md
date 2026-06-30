# MARKET_DATA_ORDERBOOK_TRUE_EMPTY_RUNTIME_DIAGNOSTIC_001

**Task class:** 5 VALIDATION / MARKET DATA RUNTIME DIAGNOSTIC
**Date:** 2026-06-30
**Final verdict:** ROOT_CAUSE_IDENTIFIED

## Scope

Diagnosed why `MAIN_PAPER_RUNTIME_SMOKE_VERIFICATION_001` reached the paper decision loop but displayed `TRUE EMPTY`, `empty_orderbook`, and `no_orderbook`.

No trading behavior, strategy thresholds, execution logic, risk logic, sizing, wallet/balance behavior, live execution, order submission, `config/settings.py`, or `.env` files were modified.

## Root Cause Classification

Primary classification: `AVAILABILITY_FALSE_NEGATIVE`.

Secondary classification: `STALE_MARKET` / `MARKET_CLOSED_OR_ROTATED`.

The CLOB orderbooks were not broadly empty. The runtime discovered and warmed nonzero BTC/ETH 5-minute books, including next-epoch books. The failure was that the Market Availability Engine reported `MARKET_NOT_SCHEDULED` from its broad Gamma `/markets?limit=50` scan and returned early before `_select_markets()` could promote/refetch the current active epoch. Meanwhile, stale old-epoch token ids continued to produce `empty_orderbook`, `clob_orderbook_cooldown_active`, and `stale_orderbook` lines after the epoch rolled.

## Markets Inspected

Smoke-run markets:

| Ticker | Slug | Condition ID | Smoke status |
|---|---|---|---|
| BTC | `btc-updown-5m-1782789000` | `0x1acbe3fd3c98a8c5e65de860ddab6316b91ac9adf83380d6ce1d77c8b7cb63a6` | Current market at startup, only 5-6s remaining |
| BTC | `btc-updown-5m-1782789300` | `0x86d9fc86c19c44542e90a0c3ebcf31fc4140581f6129ac736821dacc52ed537c` | Next epoch, warmed before open |
| BTC | `btc-updown-5m-1782789600` | `0xcf58d9b02fd56338af363c728ec8b3a4ec5e85a60f1ef59c67cd0e59c65930be` | Next cycle future epoch, warmed |
| ETH | `eth-updown-5m-1782789000` | `0xc4f2871a12a5461b78e7b51d8829eeb3805b2625a724d4b1fe54f079347e9677` | Current market at startup, only 4s remaining |
| ETH | `eth-updown-5m-1782789300` | `0x850150ddc41bda3f9637ae1167eec6e949d000e973e68129ac26142d0f0aada7` | Next epoch, warmed before open |
| ETH | `eth-updown-5m-1782789600` | `0xcd249dc15c98ef0a8b7d96dbf134ce040d101927c7fc6fbe7a65a0bf220ffe59` | Next cycle future epoch, warmed |

## Token IDs Inspected

| Market | YES token prefix | NO token prefix | Smoke evidence |
|---|---:|---:|---|
| BTC 1782789000 | `686620162851` | `502828069392` | Nonzero book first, then empty/cooldown after expiry |
| BTC 1782789300 | `872199476007` | `837167191811` | Preloaded, nonzero warmed book |
| BTC 1782789600 | `475287141329` | `497722087214` | Preloaded, nonzero warmed book |
| ETH 1782789000 | `141057668550` | `114542190507` | Empty/cooldown/stale on old current epoch |
| ETH 1782789300 | `596944305527` | `159336042147` | Preloaded, nonzero warmed book |
| ETH 1782789600 | `430977281039` | `793121689020` | Preloaded, nonzero warmed book |

## Smoke-Run Evidence

Key log and JSONL findings:

- At `10:14:55`, Gamma found `btc-updown-5m-1782789000` with 6s remaining and `btc-updown-5m-1782789300` with 306s remaining.
- BTC current token `686620162851...` had a live book: bid `0.05`, ask `0.06`, spread `0.01`.
- BTC NO token `502828069392...` had a live book: bid `0.94`, ask `0.95`, spread `0.01`.
- At `10:14:59`, BTC next epoch `1782789300` was warmed with bid/ask books on both tokens.
- At `10:15:00`, ETH next epoch `1782789300` was warmed with bid/ask books on both tokens.
- At `10:15:01`, Market Availability Engine emitted `MARKET_NOT_SCHEDULED` with `active_market_count=0`, `matching_slugs=[]`, and `next_check_seconds=300`.
- Cycle 1 and cycle 2 ended with `cycle_end_market_market_not_scheduled`.
- After epoch rollover, repeated orderbook failures referenced the old `1782789000` token ids, not the warmed `1782789300` or `1782789600` token ids.

JSONL evidence for run id `20260630T031452Z_14888_9dc7cf21`:

| Stream | Finding |
|---|---|
| `system_health` | `market_readiness_warmup` for BTC current was `NONZERO_BOOK`, 5s remaining |
| `system_health` | `preload_next_market_v1` for BTC/ETH `1782789300` was `WARMED` |
| `system_health` | `preload_next_market_v1` for BTC/ETH `1782789600` was `WARMED` |
| `research_log` | two `market_availability_check` rows reported `MARKET_NOT_SCHEDULED` |
| `system_health` | cycle-end reason was `cycle_end_market_market_not_scheduled` |

## Code Path Findings

Source-verified path:

1. `PolymarketTrader.run_single_cycle()` preloads next BTC/ETH markets via `_preload_next_market()`.
2. `_preload_next_market()` uses `GammaFetcher.get_next_5min_market()` and warms YES/NO orderbooks with `client.get_orderbook()`.
3. `run_single_cycle()` then calls `MarketAvailabilityEngine.check()` before `_select_markets()`.
4. If MAE returns anything other than `ACTIVE`, `run_single_cycle()` returns early.
5. `_select_markets()` is the method that calls `_refresh_token_ids()` and can promote/refetch active current tokens.

Therefore, a false `MARKET_NOT_SCHEDULED` from MAE prevents the normal token refresh/promotion path from running.

## Offline Direct Fetch

Safe read-only checks were run. No paper/live runtime loop, wallet mutation, signing, order submission, cancellation, redemption, config mutation, or `.env` write occurred.

### Current live market check

At diagnostic time, slug-specific Gamma and direct CLOB checks found active BTC/ETH markets and nonzero orderbooks:

| Ticker | Current slug | Gamma status | Direct CLOB book |
|---|---|---|---|
| BTC | `btc-updown-5m-1782790500` | `active=true`, `acceptingOrders=true` | YES 57 bids / 42 asks; NO 42 bids / 57 asks |
| ETH | `eth-updown-5m-1782790500` | `active=true`, `acceptingOrders=true` | YES 77 bids / 22 asks; NO 22 bids / 77 asks |
| BTC next | `btc-updown-5m-1782790800` | `active=true`, `acceptingOrders=true` | YES 50 bids / 49 asks; NO 49 bids / 50 asks |
| ETH next | `eth-updown-5m-1782790800` | `active=true`, `acceptingOrders=true` | YES 50 bids / 49 asks; NO 49 bids / 50 asks |

### Runtime GammaFetcher check

`GammaFetcher.get_current_and_next_5min_markets(..., force_refresh=True)` found:

- BTC current + next markets with token ids and nonzero time remaining.
- ETH current + next markets with token ids and nonzero time remaining.

### Market Availability Engine check

In the same diagnostic window, `MarketAvailabilityEngine(Settings()).check()` returned:

```text
state=MARKET_NOT_SCHEDULED
active_market_count=0
matching_slugs=[]
next_check_seconds=300
error=None
```

This contradicts the slug-specific GammaFetcher and direct CLOB checks.

## Why MAE False-Negatives

`MarketAvailabilityEngine._fetch_and_classify()` queries:

```text
https://gamma-api.polymarket.com/markets?limit=50&closed=False&active=True
```

The broad first page did not include BTC/ETH 5-minute `updown-5m` markets during the diagnostic, so `_classify()` saw no matching slugs and returned `MARKET_NOT_SCHEDULED`.

By contrast, `GammaFetcher.get_current_and_next_5min_markets()` queries exact event slugs such as:

```text
https://gamma-api.polymarket.com/events?slug=btc-updown-5m-{epoch}
```

That exact-slug path found active current/next markets and token ids.

## Empty Orderbook Reason

The `empty_orderbook` / cooldown lines have two different meanings:

1. For expired `1782789000` token ids, the CLOB book naturally disappears or becomes stale after market close. Direct post-run checks returned 404/no orderbook for those historical tokens.
2. For active current/next slugs, direct CLOB checks showed nonzero books. This rules out a broad parser bug or global CLOB outage.

So the smoke-run display of `TRUE EMPTY` was not evidence that BTC/ETH orderbooks were universally unavailable. It was the combined result of:

- MAE false-negative gating the active scan.
- Old-epoch token ids continuing to produce stale/empty/cooldown failures.
- The run starting in the final seconds of one 5-minute epoch, amplifying rollover noise.

## Parser / Token Mapping Assessment

| Hypothesis | Verdict | Evidence |
|---|---|---|
| `WRONG_TOKEN_ID` | Not supported | Token ids from Gamma matched CLOB book responses before expiry |
| `PARSER_BUG` | Not supported | Direct book parsing produced bid/ask counts; runtime logged `ORDERBOOK_BEST` |
| `RATE_LIMIT_OR_API_ERROR` | Not primary | No HTTP status errors in runtime orderbook failures; direct CLOB worked |
| `EXTERNAL_EMPTY_ORDERBOOK` | Partial only for expired markets | Historical/closed tokens now 404; active current tokens are nonempty |
| `STALE_MARKET` | Supported as secondary | Repeated failures reference `1782789000` after rollover |
| `AVAILABILITY_FALSE_NEGATIVE` | Supported as primary | MAE says not scheduled while slug-specific Gamma/CLOB says active |

## Future Options

1. OPTION 1 - SAFE EV PRESERVATION: keep MAE disabled or bypassed only in a controlled paper validation task after explicit approval; do not change strategy/risk/sizing.
2. OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY: run a bounded paper session with MAE diagnostics comparing broad `/markets` results versus exact-slug GammaFetcher results each cycle.
3. OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH: repair MAE to use exact slug discovery or shared GammaFetcher market discovery, then add regression tests proving active BTC/ETH 5-minute markets are not classified as `MARKET_NOT_SCHEDULED`.

Recommended option: OPTION 3.

## Safety Verdict

SAFE_DIAGNOSTIC_ONLY.

This task made no runtime behavior changes. The next implementation task should be scoped narrowly to the Market Availability Engine, tests, and docs. It must not alter thresholds, execution, risk, sizing, wallet behavior, live behavior, or order submission.

## Next Task

`MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001`

Suggested scope:

- Fix MAE discovery so exact active BTC/ETH 5-minute slugs are recognized.
- Add tests for broad `/markets` false-negative fallback or exact-slug discovery.
- Validate with a bounded paper runtime smoke.
