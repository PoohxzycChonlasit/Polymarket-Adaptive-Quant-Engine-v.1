# Hourly Market Personality Map

Generated: 2026-05-23  
Scope: read-only hour-by-hour audit across all historical JSONL dates.  
Hours are UTC.

No code, replay, runtime, policy, strategy, risk, execution, live, or S3 changes were made.

## Sources

- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/execution_log/*.jsonl`
- `runtime/quant_data/decision_log/*.jsonl`

Dates present: `2026-05-08`, `2026-05-09`, `2026-05-10`, `2026-05-11`, `2026-05-12`, `2026-05-13`, `2026-05-14`, `2026-05-15`, `2026-05-17`, `2026-05-18`, `2026-05-19`, `2026-05-20`, `2026-05-21`, `2026-05-22`, `2026-05-23`.

## Method And Caveats

- TP / SL columns are confirmed only from `trade_result`.
- Proxy W/L uses PnL sign for older rows where `trade_result` is missing.
- OPENING and ACTIVE rates use confirmed TP where present, otherwise PnL-sign proxy. Treat them as directional personality rates, not strict TP truth.
- Quote stale coverage exists only where Phase 6 fields were emitted.
- Older 02h and BTC-heavy rows have different schema and PnL scale, so Phase 6 profiles are called out separately where they contradict legacy aggregates.

## Hourly Personality Table

| Hour | Trades | TP | SL | Proxy W/L | BTC | ETH | OPENING Rate | ACTIVE Rate | Mean PnL | Mean quote_stale_ms | Top Skip Reasons | Personality |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 00h | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | n/a | `delta_extreme`, `confidence_too_low`, `time_unsafe` | LOW_SIGNAL |
| 01h | 7 | 1 | 1 | 6/1 | 5 | 2 | 100.0% | 0.0% | +0.714607 | 29010.5 | `delta_extreme`, `confidence_too_low`, `time_unsafe` | OPENING_DISLOCATION |
| 02h | 75 | 0 | 8 | 53/22 | 62 | 13 | 10.0% | 0.0% | +0.374056 | 23146.5 | `delta_extreme`, `time_unsafe`, `confidence_too_low` | CHOP |
| 03h | 17 | 0 | 1 | 11/6 | 8 | 9 | 40.0% | 0.0% | +0.410302 | 10251.7 | `delta_extreme`, `time_unsafe`, `confidence_too_low` | TREND |
| 04h | 102 | 0 | 0 | 84/18 | 91 | 11 | 50.0% | 0.0% | +0.389820 | n/a | `delta_extreme`, `confidence_too_low`, `time_unsafe` | BTC_ACTIVE |
| 05h | 18 | 0 | 0 | 7/11 | 8 | 10 | 31.2% | n/a | +0.112503 | n/a | `delta_extreme`, `confidence_too_low`, `time_unsafe` | CHOP |
| 06h | 56 | 0 | 0 | 47/9 | 45 | 11 | 60.0% | 66.7% | +0.327362 | n/a | `delta_extreme`, `confidence_too_low`, `time_unsafe` | BTC_ACTIVE |
| 07h | 13 | 0 | 0 | 5/8 | 5 | 8 | 0.0% | n/a | +0.379924 | n/a | `delta_extreme`, `confidence_too_low`, `time_unsafe` | CHOP |
| 08h | 12 | 0 | 0 | 8/4 | 3 | 9 | 66.7% | 50.0% | +0.005983 | n/a | `delta_extreme`, `confidence_too_low`, `time_unsafe` | ETH_ACTIVE |
| 09h | 34 | 5 | 1 | 24/10 | 18 | 16 | 56.2% | 66.7% | +0.292287 | 9974.1 | `delta_extreme`, `confidence_too_low`, `time_unsafe` | TREND |
| 10h | 18 | 1 | 1 | 11/7 | 11 | 7 | 40.0% | 25.0% | +0.271755 | n/a | `delta_extreme`, `confidence_too_low`, `time_unsafe` | TREND |
| 11h | 80 | 0 | 0 | 66/14 | 73 | 7 | 71.4% | 0.0% | +0.387141 | n/a | `delta_extreme`, `time_unsafe`, `confidence_too_low` | BTC_ACTIVE |
| 12h | 63 | 0 | 1 | 50/13 | 59 | 4 | 62.5% | 0.0% | +0.468222 | n/a | `delta_extreme`, `time_unsafe`, `confidence_too_low` | BTC_ACTIVE |
| 13h | 76 | 1 | 2 | 62/14 | 66 | 10 | 62.5% | 50.0% | +0.437316 | n/a | `delta_extreme`, `time_unsafe`, `confidence_too_low` | BTC_ACTIVE |
| 14h | 12 | 0 | 0 | 7/5 | 5 | 7 | 57.1% | 0.0% | +0.248573 | n/a | `delta_extreme`, `time_unsafe`, `confidence_too_low` | OPENING_DISLOCATION |
| 15h | 26 | 0 | 2 | 17/9 | 21 | 5 | 25.0% | 0.0% | +0.374203 | n/a | `delta_extreme`, `time_unsafe`, `stale_data` | BTC_ACTIVE |
| 16h | 28 | 2 | 1 | 22/6 | 22 | 6 | 83.3% | 0.0% | +0.440293 | n/a | `delta_extreme`, `time_unsafe`, `confidence_too_low` | BTC_ACTIVE |
| 17h | 12 | 1 | 2 | 9/3 | 9 | 3 | 33.3% | 0.0% | +0.666008 | n/a | `delta_extreme`, `time_unsafe`, `confidence_too_low` | BTC_ACTIVE |
| 18h | 21 | 0 | 0 | 17/4 | 21 | 0 | n/a | n/a | +0.513333 | n/a | `delta_extreme`, `confidence_too_low`, `time_unsafe` | BTC_ACTIVE |
| 19h | 3 | 0 | 1 | 2/1 | 3 | 0 | n/a | 0.0% | +0.665322 | n/a | `delta_extreme`, `confidence_too_low`, `time_unsafe` | TREND |
| 20h | 30 | 0 | 0 | 24/6 | 30 | 0 | n/a | n/a | +0.489000 | n/a | `delta_extreme`, `confidence_too_low`, `time_unsafe` | BTC_ACTIVE |
| 21h | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | n/a | `delta_extreme`, `confidence_too_low`, `time_unsafe` | LOW_SIGNAL |
| 22h | 1 | 0 | 0 | 0/1 | 1 | 0 | 0.0% | n/a | -0.002402 | n/a | `delta_extreme`, `confidence_too_low`, `time_unsafe` | LOW_SIGNAL |
| 23h | 0 | 0 | 0 | 0/0 | 0 | 0 | n/a | n/a | n/a | n/a | `delta_extreme`, `confidence_too_low`, `time_unsafe` | LOW_SIGNAL |

## Best Hours

Best confirmed / Phase 6-aware hours:

- 09h: confirmed 5 TP / 1 SL, 24 proxy wins / 10 proxy losses, ACTIVE success present, mean Phase 6 quote stale 9.974s.
- 16h: confirmed 2 TP / 1 SL, strong legacy proxy profile, BTC_ACTIVE.
- 17h: confirmed 1 TP / 2 SL but high legacy mean PnL; use caution because confirmed evidence is mixed.
- 01h: confirmed 1 TP / 1 SL, strong OPENING profile but ACTIVE failed.

Best legacy/proxy hours by mean PnL:

- 01h, 17h, 19h, 18h, 20h.

These are not all equally trustworthy because older rows have weaker outcome truth.

## Worst Hours

Worst Phase 6 / confirmed hours:

- 02h: confirmed 0 TP / 8 SL, OPENING 0/4 and ACTIVE 0/4 in the 2026-05-23 loss cluster.
- 05h and 07h: legacy proxy losses outnumber wins.
- 22h: one proxy loss and no confirmed TP.

Worst personality buckets:

- CHOP: 02h, 05h, 07h.
- LOW_SIGNAL: 00h, 21h, 22h, 23h.

## Hour Clusters

| Cluster | Hours | Personality |
|---|---|---|
| Opening dislocation candidates | 01h, 14h | Opening rate positive; ACTIVE weak or absent. |
| Trend / continuation candidates | 03h, 09h, 10h, 19h | Positive proxy profile; 09h has confirmed ACTIVE TP. |
| BTC-active legacy block | 04h, 06h, 11h, 12h, 13h, 15h, 16h, 17h, 18h, 20h | BTC dominates historical rows; some hours need Phase 6 confirmation. |
| ETH-active pocket | 08h | ETH dominates row count and OPENING rate is positive. |
| Chop / adverse pockets | 02h, 05h, 07h | Weak or negative OPENING/ACTIVE behavior; 02h is confirmed bad in Phase 6. |
| Low-signal / no-trade pockets | 00h, 21h, 22h, 23h | Decision activity but little/no trade outcome evidence. |

## 02h Profile

Personality: `CHOP` in Phase 6, despite all-history `BTC_ACTIVE` legacy row count.

Evidence:

- All-history: 75 trades, BTC 62, ETH 13.
- Confirmed outcome truth: 0 TP / 8 SL.
- Phase 6 2026-05-23: 8 trades, 8 SL, OPENING 0/4 and ACTIVE 0/4.
- Mean quote stale where available: 23.147s.
- Top skip reasons: `delta_extreme`, `time_unsafe`, `confidence_too_low`.

Interpretation: older 02h BTC activity makes the hour look active, but current outcome-truth evidence marks it as adverse/choppy. Treat 02h as a risk hour until fresh evidence clears it.

## 09h Profile

Personality: `TREND`.

Evidence:

- All-history: 34 trades, 18 BTC, 16 ETH.
- Confirmed outcome truth: 5 TP / 1 SL.
- Proxy W/L: 24 / 10.
- OPENING rate: 56.2%.
- ACTIVE rate: 66.7%.
- Mean quote stale where available: 9.974s.
- Top skip reasons: `delta_extreme`, `confidence_too_low`, `time_unsafe`.

Interpretation: 09h is the strongest session-edge candidate because it is cross-asset, has confirmed TP evidence, and is the only hour with meaningful confirmed ACTIVE TP in the current Phase 6 set.

## Candidate Session Edges

1. 09h TREND / continuation candidate.
   - Best confirmed balance.
   - ACTIVE TP appears.
   - Cross-asset BTC and ETH participation.

2. 01h OPENING_DISLOCATION candidate.
   - Opening worked, ACTIVE failed.
   - Needs more confirmed samples.

3. 14h OPENING_DISLOCATION candidate.
   - Positive opening proxy rate.
   - No confirmed TP/SL yet.

4. 16h BTC_ACTIVE candidate.
   - Strong historical proxy and some confirmed TP.
   - Needs fresh quote-stale and outcome-truth confirmation.

## Final Interpretation

The hourly personality map does not support a universal opening-only rule. It supports a conditional framework:

- 09h is a `TREND` session-edge candidate.
- 01h and 14h are `OPENING_DISLOCATION` candidates.
- 02h is Phase 6 `CHOP` and should remain suspect.
- Many BTC-active hours are legacy-heavy and need modern Phase 6 confirmation before being trusted.

Recommended next evidence step: continue Phase 6 collection and maintain separate hourly counters for confirmed TP/SL, OPENING/ACTIVE, BTC/ETH, and quote staleness.

Runtime behavior changed: No  
Live behavior changed: No  
Tests: not run, docs-only  
Persistent tests unchanged
