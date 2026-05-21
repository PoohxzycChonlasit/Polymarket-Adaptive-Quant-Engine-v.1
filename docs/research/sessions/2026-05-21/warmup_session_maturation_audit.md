# Warmup / Session Maturation Audit v1

Date: 2026-05-21

## Scope and Guardrails

Runtime behavior changed: No
Live behavior changed: No
Replay tools run: No
Paper runtime run: No
Strategy/risk/test changes: No
S3 promoted: No

This is a read-only research audit. The only permitted write is this Markdown report and its identical research-vault copy.

## Source Files Inspected

- `docs/research/sessions/2026-05-21/overnight_evidence_merge_2026-05-21.md`
- `docs/research/sessions/2026-05-21/outcome_diversity_re_evaluation.md`
- `runtime_clean_validation_2026-05-19.md`
- `runtime/research_state/latest_research_state.md`
- `runtime/quant_data/trade_journal/2026-05-20.jsonl`
- `runtime/quant_data/trade_journal/2026-05-21.jsonl`
- `runtime/quant_data/decision_log/2026-05-20.jsonl`
- `runtime/quant_data/decision_log/2026-05-21.jsonl`

Forbidden runtime files were not inspected or modified: `polymarket/trader.py`, `polymarket/order_manager.py`, `utils/risk_manager.py`, and `tests/`.

## Methodology

Direct JSONL inspection was used; replay tools were not executed.

Trade pair metrics used `trade_journal` events paired by `payload.paper_trade_replay_key`, with opens from `event_type=trade_open` and closes from `event_type=trade_close`. Trade index was computed within each `run_id` by ascending open `timestamp_utc`.

Primary fields used:

- Identity and pairing: `run_id`, `timestamp_utc`, `event_type`, `payload.paper_trade_replay_key`
- Outcome and performance: `payload.reason`, `payload.pnl`, `payload.hold_seconds`
- Trade context: `payload.asset`, `payload.ticker`, `payload.confidence`, `payload.liquidity_depth_state`, `payload.lifecycle_phase`
- Liquidity and timing: `payload.best_bid_size`, `payload.best_ask_size`, `payload.min_fillable_size_usd`, `payload.tradable_but_thin_count`, `payload.first_tradable_seconds_remaining`, `payload.orderbook_ready_seconds_remaining`, `payload.preload_orderbook_warmed`
- Model visibility: `payload.model_output_ready`, `payload.model_not_run_reason`, `payload.probability_model_output_visible`
- Decision diagnostics: `payload.candidate_block_reason`, `payload.normalized_skip_reason`, `payload.delta_regime`, `payload.liquidity_depth_state`, `payload.lifecycle_phase`

Missing-field caveats:

- Direct trade journals now contain 42 paired trades across 2026-05-20 and 2026-05-21, while earlier summary docs reported 40. The audit uses direct JSONL as the newer source and treats the prose reports as context.
- `run_id` timestamps place all observed trades more than 60 minutes after run start, so the requested 0-10, 10-30, and 30-60 minute runtime-start bins are empty under direct `run_id` timing. A first-observed-open proxy is included only as supplementary context.
- Entry opens have `model_not_run_reason=model_output_not_visible` on all 42 trades, while decision-log events mostly show serialized model output. This means decision-layer model visibility exists, but executed trade-open payloads still do not prove model output at entry.
- Close events still do not provide usable MFE/MAE path truth; `candidate_peak_adverse` and `candidate_peak_favorable` are unavailable on closes.

## A. Trade Index Effect

| Trade index in run | Trades | TP | SL | WR | PnL | Avg hold seconds | BTC / ETH | Liquidity class |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 7 | 3 | 4 | 42.9% | +0.0027 | 11.6 | 0 / 7 | ACCEPTABLE 1, THIN 6 |
| 2-4 | 14 | 5 | 9 | 35.7% | +0.0356 | 23.8 | 5 / 9 | ACCEPTABLE 3, THIN 7, UNSTABLE 4 |
| 5-8 | 12 | 7 | 5 | 58.3% | +0.0629 | 25.7 | 2 / 10 | ACCEPTABLE 2, THIN 10 |
| 9+ | 9 | 4 | 5 | 44.4% | -0.0147 | 15.7 | 1 / 8 | ACCEPTABLE 1, THIN 8 |

Interpretation: A simple "first trade always bad" claim is not supported by the direct 42-trade set, because trade 1 is near breakeven and 42.9% WR. The strongest pocket is trades 5-8. Trade 9+ weakens again, so maturation is nonlinear rather than steadily improving.

## B. Time Since Run Start

Using `run_id` timestamp as the run-start source:

| Time since run start | Trades | TP | SL | WR | PnL | Avg confidence | BTC / ETH | Depth class |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 0-10 min | 0 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| 10-30 min | 0 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| 30-60 min | 0 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| 60+ min | 42 | 19 | 23 | 45.2% | +0.0864 | 0.570 | 8 / 34 | ACCEPTABLE 7, THIN 31, UNSTABLE 4 |

Supplementary first-observed-open proxy, not true runtime start:

| Proxy age since first observed open in run | Trades | TP | SL | WR | PnL | Avg confidence | BTC / ETH | Depth class |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 0-10 min | 13 | 5 | 8 | 38.5% | +0.0366 | 0.563 | 2 / 11 | ACCEPTABLE 2, THIN 9, UNSTABLE 2 |
| 10-30 min | 5 | 3 | 2 | 60.0% | +0.0154 | 0.546 | 1 / 4 | THIN 3, UNSTABLE 2 |
| 30-60 min | 1 | 0 | 1 | 0.0% | -0.0059 | 0.545 | 0 / 1 | THIN 1 |
| 60+ min | 23 | 11 | 12 | 47.8% | +0.0404 | 0.580 | 5 / 18 | ACCEPTABLE 5, THIN 18 |

Interpretation: True runtime-start bins cannot prove startup warmup because early bins have no direct trades. The proxy bins show weak evidence that the first 10 minutes after the first observed open are worse than 10-30 minutes, but sample size is small and confounded by run interruption, asset mix, and THIN depth.

## C. Frequency Maturation

Decision-log inspection across 5,717 decision events:

| Frequency signal | Count | Evidence-bounded interpretation |
|---|---:|---|
| `frequency_cooldown` | 820 | Frequency gating is active and commonly blocks re-entry after fills or recent opportunities. |
| `max_trades_per_hour_reached` | 52 | Hourly cap appears in the latest/highest-activity run only, so it is a late-session saturation signal rather than startup warmup. |
| `max_active_positions_per_market_reached` | 46 | Active-position cap exists in decisions, but this audit did not inspect execution internals. |
| Trade entries per run | 1 to 14 | Longer runs produce more diverse outcomes; runs with 1-4 trades remain mostly SL-heavy. |
| Entry timing evolution | partial | Entries are generally early in the 5-minute market window by `first_tradable_seconds_remaining`, but run-start timing is not observable in early bins. |

Run-level frequency context:

| Run | Trades | TP | SL | PnL | Frequency cooldown decisions | Max trades/hour decisions |
|---|---:|---:|---:|---:|---:|---:|
| `25443b98` | 2 | 0 | 2 | -0.0091 | 22 | 0 |
| `dc23e716` | 8 | 3 | 5 | -0.0006 | 142 | 0 |
| `d6c09eac` | 14 | 9 | 5 | +0.0551 | 302 | 0 |
| `1b6a20bd` | 2 | 0 | 2 | -0.0205 | 33 | 0 |
| `4b9e665c` | 1 | 0 | 1 | -0.0019 | 18 | 0 |
| `45581845` | 4 | 1 | 3 | -0.0032 | 67 | 0 |
| `13704` | 11 | 6 | 5 | +0.0666 | 236 | 52 |

Interpretation: Frequency maturation is plausible. The best PnL runs are the longer runs, and frequency gates are active enough to shape entry cadence. However, the 9+ trade bucket turns negative in direct JSONL, so "more trades always improves quality" is not supported.

## D. Market Maturation

Decision-log and trade-open context:

| Market maturation signal | Direct evidence | Interpretation |
|---|---:|---|
| `delta_extreme` decision blocks | 2,087 skip reasons; 3,584 decisions with `delta_regime=EXTREME` | Extreme delta is a dominant market-state filter. This points to timing/regime selectivity more than pure startup artifact. |
| THIN trade opens | 31 / 42 | Entry liquidity remains structurally THIN, especially ETH. This is not resolved by longer sessions. |
| UNSTABLE trade opens | 4 / 42 | Smaller but present entry-quality risk. |
| ACCEPTABLE trade opens | 7 / 42 | Mostly BTC; BTC has higher confidence/depth but is minority. |
| Model output on trade opens | 0 / 42 visible; all `model_output_not_visible` | Executed entry payloads still lack confirmed model output visibility. |
| Decision model output | 5,709 / 5,717 decisions visible | Decision-layer model visibility exists, but the entry journal does not preserve it. |
| Lifecycle on opens | OPENING_SCAN 39, ACTIVE_INVENTORY_TRADING 3 | Most entries occur in OPENING_SCAN; the few ACTIVE_INVENTORY_TRADING opens are all SL in direct data. |
| Preload warmed on opens | 33 true, 9 false | Preload helps but does not eliminate THIN-book or model-output caveats. |

Depth outcome table:

| Depth class | Trades | TP | SL | WR | PnL | Avg hold | Avg confidence | BTC / ETH |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ACCEPTABLE | 7 | 3 | 4 | 42.9% | +0.0235 | 16.7 | 0.628 | 6 / 1 |
| THIN | 31 | 14 | 17 | 45.2% | +0.0558 | 22.6 | 0.555 | 0 / 31 |
| UNSTABLE | 4 | 2 | 2 | 50.0% | +0.0071 | 11.5 | 0.588 | 2 / 2 |

Interpretation: Liquidity class alone does not explain outcome direction because THIN trades are still net positive, but THIN dominance remains the largest execution-quality uncertainty. Without MFE/MAE close-path truth, stop losses in thin books cannot be cleanly separated from mark-price artifacts.

## Root-Cause Ranking

| Rank | Candidate cause | Confidence | Evidence |
|---:|---|---|---|
| 1 | C. Frequency maturation | Medium | Longer runs improve versus 1-4 trade runs, frequency cooldown appears 820 times, and best PnL runs have 11-14 trades. Nonlinear 9+ weakness limits confidence. |
| 2 | D. Timing effect | Medium | `delta_extreme` and `time_unsafe` dominate decision skips, and most opens are early-window OPENING_SCAN. True runtime-start early bins are unavailable. |
| 3 | E. Liquidity warmup | Low-Medium | THIN entries dominate 31/42, but THIN trades are net positive and not uniquely worse. Liquidity is a quality risk, not proven root cause. |
| 4 | B. Sample randomness | Low-Medium | 42 trades is still small, and several buckets have tiny samples. The recurring short-run weakness argues against pure randomness. |
| 5 | A. Startup artifact | Low | True run-start bins 0-60 minutes contain no observed trades, so startup artifact is not directly proven. |
| 6 | F. Strategy weakness | Low-Medium | Net PnL is positive, TP exits exist, and pairing is clean. But no expiry closes, no MFE/MAE path, and model-output gaps prevent a strong strategy-quality claim. |

Overall root-cause call: mixed frequency maturation plus timing/regime filtering, with liquidity/model observability as unresolved evidence-quality constraints. It is not safe to reduce this to a pure startup artifact.

## Recommendation-Only S3 Evaluation Gates

No enforcement is recommended in this audit. These are evaluation gates only:

| Gate | Recommendation | Why |
|---|---|---|
| Minimum runtime | Require enough runtime to observe trades beyond the first observed-open period and beyond run interruption effects. A practical review threshold is at least 60 minutes of clean evidence or a documented reason when all direct trades occur later. | Current run-start bins cannot test startup maturation because all observed trades are 60+ minutes by `run_id`. |
| Minimum closes | Require more than the current short-run samples before S3 reconsideration. At minimum, avoid S3 decisions from runs with fewer than 8-10 closes; prefer a larger multi-run close set. | Runs with 1-4 closes remain SL-heavy and unstable. |
| Stable liquidity | Require a stable-liquidity slice where THIN/UNSTABLE is not dominant, or explicitly segment S3 by depth class. | 31/42 direct entries are THIN, so the current sample is not a clean liquidity-quality proof. |
| Model output visible | Require model output visible and preserved on entry/open payloads for a full evaluation cycle. | Decision logs mostly show model output, but trade opens still show `model_output_not_visible` on all 42 entries. |
| Outcome diversity | Continue requiring expiry or held-to-resolution evidence before promotion. | Direct evidence still has no expiry path and max holds remain short versus the 300-second market. |
| MFE/MAE path | Require close-path MFE/MAE or equivalent path truth before interpreting stop losses as genuine adverse movement. | Close events lack usable path truth, especially important for THIN ETH books. |

## Final Verdict

A session maturation effect probably exists, but it is partial and uncertain.

Evidence supports the idea that very short/interrupted runs are fragile and that mid-run trade buckets can improve. The best evidence is the 5-8 trade bucket and the stronger longer-run PnL. Evidence does not support a clean startup-warmup explanation, because true run-start early bins are empty and all observed trades are 60+ minutes after `run_id` start.

The most defensible conclusion is: maturation is mixed frequency/timing selection, not simple startup warmup. S3 remains CAUTION and should not be promoted until runtime duration, close count, stable liquidity, visible model output at entry, expiry coverage, and MFE/MAE path evidence improve.

