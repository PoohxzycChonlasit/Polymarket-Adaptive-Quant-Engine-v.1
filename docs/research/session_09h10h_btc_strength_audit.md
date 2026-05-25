# 09h10h BTC Strength Audit

Date: 2026-05-25

Scope: read-only audit of whether BTC strength inside the `09h10h` session bucket is real or an artifact.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Role Routing

Primary role: `10_BACKTEST_REPLAY_AGENT.md`

Supporting roles:

- `16_PAPER_EVALUATION_AGENT.md`
- `11_OBSERVABILITY_INCIDENT_AGENT.md`
- `07_TEST_CI_AGENT.md`

Why selected: this is an offline session/lifecycle outcome audit using trade-journal evidence, with observability and evidence-sufficiency checks. It does not authorize runtime, strategy, risk, stoploss, field-wiring, or live changes.

## Sources Inspected

- `runtime/research_state/latest_research_state.md`
- `MASTER_AGENT_ROUTER.md`
- `docs/research/session_09h10h_failure_escape_audit.md`
- `docs/research/session_pressure_comparison_audit.md`
- `docs/research/session_regime_09h10h_persistence.md`
- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`

Files intentionally ignored:

- `polymarket/trader.py`
- `polymarket/order_manager.py`
- `utils/risk_manager.py`
- wallet/live config
- runtime/replay execution paths

## Method

Target population:

- BTC trades inside `09h10h`, where `09h10h` means UTC hours `09` and `10`.
- Window aligned to the prior `09h10h` failure-escape audit: `2026-05-21` through `2026-05-23`.

Pairing method:

- `trade_open` rows paired to `trade_close` rows by run, asset, and selected side order.
- Lifecycle stage comes from paired `trade_open.lifecycle_phase`.
- Outcome comes from close reason:
  - `take_profit_target_reached` -> `TP`
  - `stop_loss` / `stop_loss_hit` -> `SL`
- Hold uses `trade_close.hold_seconds`.

Path truth coverage:

- Current `path_truth` files cover `2026-05-24` and `2026-05-25`.
- The BTC `09h10h` rows in this audit are from `2026-05-21` and `2026-05-23`.
- Therefore path-truth checkpoint coverage for this BTC `09h10h` sample is `0 / 4`.

## Summary

| Metric | Value |
| --- | ---: |
| BTC 09h10h trades | 4 |
| TP | 3 |
| SL | 1 |
| Win rate | 75.0% |
| Median hold | 20s |
| Fast close <60s | 4 / 4 |
| 09h trades | 3 |
| 10h trades | 1 |
| YES split | 2 TP / 0 SL |
| NO split | 1 TP / 1 SL |
| OPENING split | 2 TP / 1 SL |
| ACTIVE split | 1 TP / 0 SL |
| Path truth coverage | 0 / 4 |

BTC does improve sharply inside `09h10h` relative to the global failure-triangle sample, where BTC was `0 TP / 8 SL`. However, the improvement is tiny and date-concentrated: every BTC win is from `2026-05-23`.

## Required Matrix

| Bucket | Trades | TP | SL | Win Rate | Median Hold | Fast Close | Hold Buckets | Price Bucket | Path Truth Coverage | Session Survival |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| 09h + BTC + YES + OPENING | 1 | 1 | 0 | 100.0% | 10s | 100.0% | 0-15s: 1 | 0.60+: 1 | 0 / 1 | survived on 2026-05-23 only |
| 09h + BTC + YES + ACTIVE | 1 | 1 | 0 | 100.0% | 49s | 100.0% | 45-60s: 1 | 0.50-0.59: 1 | 0 / 1 | survived on 2026-05-23 only |
| 09h + BTC + NO + OPENING | 1 | 0 | 1 | 0.0% | 11s | 100.0% | 0-15s: 1 | 0.50-0.59: 1 | 0 / 1 | failed on 2026-05-21 |
| 09h + BTC + NO + ACTIVE | 0 | 0 | 0 | N/A | N/A | N/A | none | none | 0 / 0 | no evidence |
| 10h + BTC + YES + OPENING | 0 | 0 | 0 | N/A | N/A | N/A | none | none | 0 / 0 | no evidence |
| 10h + BTC + YES + ACTIVE | 0 | 0 | 0 | N/A | N/A | N/A | none | none | 0 / 0 | no evidence |
| 10h + BTC + NO + OPENING | 1 | 1 | 0 | 100.0% | 29s | 100.0% | 15-30s: 1 | 0.50-0.59: 1 | 0 / 1 | survived on 2026-05-23 only |
| 10h + BTC + NO + ACTIVE | 0 | 0 | 0 | N/A | N/A | N/A | none | none | 0 / 0 | no evidence |

## Row Evidence

| Date | Hour | Run | Position | Side | Stage | Entry | Exit | Outcome | Hold | Bucket |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | ---: | --- |
| 2026-05-21 | 09 | `20260521T044143Z_13704_948b4757` | `d421999d` | NO | OPENING | 0.56 | 0.51 | SL | 11s | 0-15s |
| 2026-05-23 | 09 | `20260523T015426Z_16036_ac5d7312` | `d3d18e70` | YES | OPENING | 0.64 | 0.73 | TP | 10s | 0-15s |
| 2026-05-23 | 09 | `20260523T015426Z_16036_ac5d7312` | `03007b4c` | YES | ACTIVE | 0.54 | 0.67 | TP | 49s | 45-60s |
| 2026-05-23 | 10 | `20260523T015426Z_16036_ac5d7312` | `201e3ad4` | NO | OPENING | 0.52 | 0.60 | TP | 29s | 15-30s |

## Questions

### Is BTC strong inside 09h10h?

Verdict: BTC_RECOVERY, not BTC_EDGE.

BTC is `3 TP / 1 SL` inside this `09h10h` sample, which is a sharp recovery versus the global BTC failure sample. The evidence is too small and too concentrated to call a durable BTC edge.

### Is strength only YES?

Verdict: No, but YES is cleaner.

YES is `2 TP / 0 SL`. NO is `1 TP / 1 SL`. The 10h BTC NO OPENING trade survived, so the BTC recovery is not only YES. But the only BTC loss is also NO, so NO is not clean.

### Is strength only OPENING?

Verdict: No, but ACTIVE is one trade.

OPENING is `2 TP / 1 SL`. ACTIVE is `1 TP / 0 SL`. The BTC ACTIVE winner is useful because it directly pushes against the global ACTIVE failure pattern, but one row is not enough to call ACTIVE BTC strength.

### Is strength only one date?

Verdict: Yes, currently.

All three BTC wins occurred on `2026-05-23`. The only non-2026-05-23 BTC row was a 09h BTC NO OPENING SL on `2026-05-21`. There was no BTC `09h10h` evidence on `2026-05-22` in this matched sample.

## Classification

Primary classification: INSUFFICIENT_SAMPLE.

Candidate labels:

- BTC_RECOVERY
- ONE_DATE_ARTIFACT

Rejected labels:

- BTC_EDGE: too strong; only four trades and all wins are from one date.
- BTC_ONLY_YES: rejected; BTC NO has one TP and one SL.
- BTC_ONLY_OPENING: rejected; BTC YES ACTIVE has one TP.

## Interpretation

The BTC `09h10h` result is best treated as a recovery pocket, not a proven edge.

The useful signal is that BTC does not behave like the global BTC failure sample inside this session window. The dangerous signal is that every positive BTC row comes from a single session cluster on `2026-05-23`, and none of these rows has path-truth checkpoint coverage.

## Three Future Options

OPTION 1 - SAFE EV PRESERVATION:

Keep `09h10h BTC` as a research tag only. No strategy, risk, stoploss, field-wiring, or runtime change.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:

Continue paper evidence collection and rerun this audit after at least 8 BTC trades inside `09h10h`, with at least two completed dates containing BTC `09h10h` wins.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:

Once future path-truth files include `09h10h` BTC trades, compare BTC `09h10h` path checkpoints against global BTC failure rows to test whether the recovery is quote-age, lifecycle, side, price, or session-specific.

Recommended option: OPTION 2.

## Final Status

Files created:

- `docs/research/session_09h10h_btc_strength_audit.md`

Tests run: none. This was a read-only evidence and documentation audit.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No
