# Full-Day Regime Audit - 2026-05-23

Generated: 2026-05-23  
Scope: read-only evidence audit from local JSONL files.  
Source hours: UTC, using `timestamp_utc` / fill timestamps in the 2026-05-23 files.

## Source Files

- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`
- `runtime/quant_data/decision_log/2026-05-23.jsonl`

No replay, code, runtime policy, strategy, risk, execution, live, or S3 changes were made.

## Method

- Trade count means closed paper trades from `trade_journal` `trade_close`.
- BTC / ETH are closed-trade asset counts.
- TP / SL use `trade_result`.
- PnL uses `pnl_usdc`.
- Lifecycle, elapsed second, quote age, and `quote_stale_ms` are joined from ENTRY `paper_fill` records in `execution_log` by `paper_trade_replay_key`.
- OPENING TP rate uses ENTRY fill lifecycle `OPENING_SCAN` or elapsed <= 30s.
- ACTIVE TP rate uses ENTRY fill lifecycle `ACTIVE_INVENTORY_TRADING` or elapsed > 30s.
- Elapsed <=30s / >30s TP rates use `first_probability_output_second` / `first_model_eligible_second`.
- Mean quote age uses ENTRY `quote_age_at_fill_ms`, falling back to submit age if needed.
- Dominant skip reason uses hourly `candidate_block_reason` from `decision_log`, excluding no-trade outcome inference.

Coverage note: current files contain decision events for 00h-09h UTC and no source events for 10h-23h UTC at audit time.

## Daily Summary

| Metric | Value |
|---|---:|
| Closed trades | 15 |
| BTC trades | 3 |
| ETH trades | 12 |
| TP | 5 |
| SL | 10 |
| Mean PnL | -0.002534 USDC |
| ENTRY quote stale coverage | 15 / 15 |
| Paper-fill quote stale coverage | 30 / 30 |
| market_analysis_exception | 0 |

## Hourly Regime Table

Quote age and stale values are seconds.

| Hour | Trades | BTC | ETH | TP | SL | OPENING TP | ACTIVE TP | <=30s TP | >30s TP | Mean PnL | Mean Quote Age | quote_stale_ms | Dominant Skip | market_analysis_exception | Classification | Market Shape |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---|
| 00h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | delta_extreme | 0 | NO_TRICES | dead market |
| 01h | 2 | 0 | 2 | 1 | 1 | 100% | 0% | 100% | 0% | +0.001125 | 29.010 | 29.010 | delta_extreme | 0 | OPENING_EDGE | opening dislocation |
| 02h | 8 | 1 | 7 | 0 | 8 | 0% | 0% | 0% | 0% | -0.008145 | 23.147 | 23.147 | delta_extreme | 0 | ACTIVE_FAILURE | mean reversion / adverse chop |
| 03h | 1 | 0 | 1 | 0 | 1 | 0% | 0% | n/a | 0% | -0.010150 | 10.252 | 10.252 | delta_extreme | 0 | ACTIVE_FAILURE | mixed |
| 04h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | delta_extreme | 0 | NO_TRICES | dead market |
| 05h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | delta_extreme | 0 | NO_TRICES | dead market |
| 06h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | delta_extreme | 0 | NO_TRICES | dead market |
| 07h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | delta_extreme | 0 | NO_TRICES | dead market |
| 08h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | delta_extreme | 0 | NO_TRICES | dead market |
| 09h | 4 | 2 | 2 | 4 | 0 | 100% | 100% | 100% | 100% | +0.013548 | 9.974 | 9.974 | delta_extreme | 0 | OPENING_EDGE | opening dislocation / trend |
| 10h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | none | 0 | NO_TRICES | no source events yet |
| 11h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | none | 0 | NO_TRICES | no source events yet |
| 12h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | none | 0 | NO_TRICES | no source events yet |
| 13h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | none | 0 | NO_TRICES | no source events yet |
| 14h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | none | 0 | NO_TRICES | no source events yet |
| 15h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | none | 0 | NO_TRICES | no source events yet |
| 16h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | none | 0 | NO_TRICES | no source events yet |
| 17h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | none | 0 | NO_TRICES | no source events yet |
| 18h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | none | 0 | NO_TRICES | no source events yet |
| 19h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | none | 0 | NO_TRICES | no source events yet |
| 20h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | none | 0 | NO_TRICES | no source events yet |
| 21h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | none | 0 | NO_TRICES | no source events yet |
| 22h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | none | 0 | NO_TRICES | no source events yet |
| 23h | 0 | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | none | 0 | NO_TRICES | no source events yet |

## Trade-Level Evidence

| Time UTC | Asset | Result | PnL | Lifecycle | Elapsed | quote_stale_ms | Side |
|---|---|---|---:|---|---:|---:|---|
| 01:51:05 | ETH | SL | -0.003920 | ACTIVE_INVENTORY_TRADING | 40s | 10.463s | YES |
| 01:55:21 | ETH | TP | +0.006170 | OPENING_SCAN | 4s | 47.558s | NO |
| 02:10:11 | ETH | SL | -0.004927 | OPENING_SCAN | 7s | 59.356s | NO |
| 02:10:15 | ETH | SL | -0.004020 | OPENING_SCAN | 7s | 59.356s | NO |
| 02:10:52 | ETH | SL | -0.015325 | ACTIVE_INVENTORY_TRADING | 47s | 10.255s | YES |
| 02:20:54 | ETH | SL | -0.009473 | ACTIVE_INVENTORY_TRADING | 49s | 10.016s | YES |
| 02:20:55 | ETH | SL | -0.010628 | ACTIVE_INVENTORY_TRADING | 49s | 10.016s | YES |
| 02:20:59 | ETH | SL | -0.012094 | ACTIVE_INVENTORY_TRADING | 49s | 10.016s | YES |
| 02:30:35 | BTC | SL | -0.005679 | OPENING_SCAN | 30s | 10.173s | YES |
| 02:40:16 | ETH | SL | -0.003011 | OPENING_SCAN | 8s | 15.982s | NO |
| 03:35:38 | ETH | SL | -0.010150 | OPENING_SCAN | 34s | 10.252s | NO |
| 09:10:41 | BTC | TP | +0.002008 | OPENING_SCAN | 30s | 10.548s | YES |
| 09:17:06 | ETH | TP | +0.032193 | ACTIVE_INVENTORY_TRADING | 52s | 10.702s | YES |
| 09:20:31 | ETH | TP | +0.007885 | OPENING_SCAN | 20s | 7.281s | NO |
| 09:22:03 | BTC | TP | +0.012105 | ACTIVE_INVENTORY_TRADING | 74s | 11.366s | YES |

## Answers

### 1. Best trading hours today

Best observed hour: 09h UTC.

- 4 trades, 4 TP, 0 SL.
- Mean PnL: +0.013548 USDC.
- BTC and ETH both contributed.
- Both OPENING and ACTIVE entries were profitable.
- Mean `quote_stale_ms`: 9.974s, lower than 01h and 02h.

Secondary but mixed: 01h UTC.

- 2 trades, 1 TP, 1 SL.
- Mean PnL: +0.001125 USDC.
- OPENING trade won, ACTIVE trade lost.

### 2. Worst hours

Worst observed hour: 02h UTC.

- 8 trades, 0 TP, 8 SL.
- Mean PnL: -0.008145 USDC.
- Both OPENING and ACTIVE lifecycle buckets failed.
- ETH dominated the loss cluster: 7 ETH losses and 1 BTC loss.

Next worst: 03h UTC.

- 1 trade, 0 TP, 1 SL.
- Mean PnL: -0.010150 USDC.

### 3. Did OPENING edge survive all day?

No. OPENING edge was regime-dependent.

- 01h: OPENING TP rate 100% on 1 trade.
- 02h: OPENING TP rate 0% on 4 trades.
- 03h: OPENING TP rate 0% on 1 trade.
- 09h: OPENING TP rate 100% on 2 trades.

Interpretation: OPENING edge appears episodic, not stable across all observed hours.

### 4. Did >30s TP appear?

Yes.

- 09:17:06 ETH TP at elapsed 52s.
- 09:22:03 BTC TP at elapsed 74s.

This directly contradicts a simple rule that all >30s entries fail. Earlier >30s trades did fail, especially in 01h-03h, so timing appears regime-conditioned.

### 5. Did ACTIVE TP appear?

Yes.

- 09h ACTIVE TP rate was 100% on 2 trades.
- Earlier ACTIVE entries were weak: 01h ACTIVE 0/1 TP, 02h ACTIVE 0/4 TP.

Interpretation: ACTIVE is not structurally dead, but it is unstable and needs regime gating before any policy conclusion.

### 6. Which hours resemble trend / mean reversion / opening dislocation / dead market?

| Regime Shape | Hours | Evidence |
|---|---|---|
| Trend | 09h | 4/4 TP, both BTC and ETH, OPENING and ACTIVE winners |
| Mean reversion / adverse chop | 02h | 8/8 SL, repeated ETH losses, both lifecycle buckets failed |
| Opening dislocation | 01h, 09h | OPENING entries had TP outcomes; 09h also supported ACTIVE continuation |
| Dead market / no-trade | 00h, 04h-08h | decision activity present but no trades; dominant skip was `delta_extreme` |
| No source events yet | 10h-23h | no decision/trade/execution rows in current files |

## Regime Conclusions

### Market Regime

The observed day splits into three usable states:

- 01h: small opening dislocation with one successful early ETH trade, but ACTIVE failed.
- 02h-03h: adverse/choppy regime where both OPENING and ACTIVE entries lost.
- 09h: trend/continuation-friendly regime where both OPENING and ACTIVE worked.

The many no-trade hours with `delta_extreme` as dominant skip reason should not be treated as negative trade evidence; they are mostly no-admission market states.

### Lifecycle Regime

OPENING_SCAN is not universally superior. It wins in 01h and 09h, but fails in 02h-03h.

ACTIVE_INVENTORY_TRADING is worse early in the sample but recovers strongly at 09h. This makes ACTIVE a conditional regime candidate, not an always-off bucket.

### Timing Regime

There is no universal 30-second timing cliff in this data.

- <=30s: mixed across the day; strong at 09h, weak at 02h.
- >30s: poor in 01h-03h, strong at 09h.

The timing signal is likely interacting with market regime and asset state.

### Quote Staleness Regime

Quote staleness alone does not explain outcomes today.

- The oldest quote-stale trades were 02h OPENING ETH losses at 59.356s.
- The 01h OPENING TP had 47.558s staleness.
- The 09h TP cluster had lower staleness around 7.281s-11.366s.

Interpretation: very stale quotes can be dangerous, but a stale quote was not sufficient to predict loss by itself. Lower staleness aligned with the cleanest TP cluster.

## MARK / POKER Comparison

| Market State | Lifecycle State | Timing State | Recommended System |
|---|---|---|---|
| Opening dislocation | OPENING_SCAN edge visible | <=30s favored when regime is clean | MARK: scout early edge; POKER: play premium hands only, small size, no chase |
| Trend / continuation | OPENING and ACTIVE both viable | >30s can still TP | MARK: allow metric collection for ACTIVE continuation; POKER: press only with confirmed table texture |
| Adverse chop / mean reversion | OPENING and ACTIVE both failing | <=30s and >30s both weak | MARK: stand down; POKER: fold marginal setups, protect stack |
| Dead / no-admission market | No trade lifecycle | Timing signal absent | MARK: observe only; POKER: wait for playable hand |
| Stale quote / microstructure uncertainty | Lifecycle signal unreliable | Timing edge can invert | MARK: collect quote-stale evidence only; POKER: do not bluff into bad information |

## Recommendation

OPTION 1 - SAFE EV PRESERVATION: keep Phase 6 as metric-only and continue harvesting hourly evidence without policy thresholds.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY: add a paper-only daily regime dashboard that compares OPENING vs ACTIVE, <=30s vs >30s, asset, and quote staleness by hour.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH: later investigate why `delta_extreme` dominates no-trade hours and whether it reflects real no-edge conditions or a gate calibration artifact.

Recommended: OPTION 1 now, with OPTION 2 as the next docs/observability artifact. The current sample is useful but too small and regime-clustered for runtime policy.

## Final Classification

- Best hours: 09h UTC, then 01h UTC with caution.
- Worst hours: 02h UTC, then 03h UTC.
- OPENING edge survived all day: No.
- >30s TP appeared: Yes.
- ACTIVE TP appeared: Yes.
- Phase 6 policy readiness: Not ready for thresholds from this sample alone.

Runtime behavior changed: No  
Live behavior changed: No  
Tests: not run, docs-only  
Persistent tests unchanged
