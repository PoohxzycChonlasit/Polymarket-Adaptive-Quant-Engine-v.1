# 02h Multi-Day Hostile Session Validation

Date: 2026-05-24

Scope: read-only validation of 02h UTC across the latest three complete trading dates before 2026-05-24.

Runtime behavior changed: No
Live behavior changed: No

## Verdict

Classification:

```text
02h UTC = HOSTILE_SESSION_CANDIDATE
```

02h is adverse across all three reviewed dates, but it does not yet meet the stricter `HOSTILE_SESSION` threshold because the fast-SL cluster is clear on only two of the three dates.

Threshold check:

| Required for HOSTILE_SESSION | Current Evidence | Pass |
|---|---|---|
| `>=3` dates adverse | 2026-05-21, 2026-05-22, 2026-05-23 all adverse | Yes |
| fast SL cluster persists | strong on 2026-05-22 and 2026-05-23; weak on 2026-05-21 | Partial |
| TP materially below baseline | 02h `0/12 TP` vs baseline `43/118 TP` | Yes |

Final read:

```text
02h is not normal.
02h should remain excluded from positive session-edge claims.
02h is not yet proven enough for runtime policy.
```

## Sources

- `docs/research/session_edge/session_02h_fast_sl_audit.md`
- `docs/research/fast_stop_loss_audit.md`
- `docs/research/session_edge/session_survival_ranking.md`
- `docs/research/session_edge/hourly_market_personality_map.md`
- `docs/research/session_edge/session_personality_stability.md`
- `runtime/quant_data/trade_journal/2026-05-21.jsonl`
- `runtime/quant_data/trade_journal/2026-05-22.jsonl`
- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-21.jsonl`
- `runtime/quant_data/execution_log/2026-05-22.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`
- `runtime/quant_data/decision_log/2026-05-21.jsonl`
- `runtime/quant_data/decision_log/2026-05-22.jsonl`
- `runtime/quant_data/decision_log/2026-05-23.jsonl`

## Method Notes

Dates reviewed:

```text
2026-05-21
2026-05-22
2026-05-23
```

Outcome truth handling:

- `trade_result` is used when present.
- For older rows without `trade_result`, stop-loss/take-profit `reason` and PnL sign are treated as proxy evidence.
- Proxy rows are counted separately and should not be promoted as strongly as confirmed Phase 6 outcome truth.

Executable reality handling:

- conservative practical minimum: `5 shares`;
- rows below that are `DUST_ZONE` / `SIMULATION_ONLY`;
- executable PnL is counted only when the practical minimum is met.

## Date Table: 02h UTC

| Date | TP | SL | Truth Quality | Fast SL <=15s | Fast SL <=30s | Median Hold | OPENING | ACTIVE | BTC | ETH | YES | NO | Quote Stale | Dust Ratio | Signal PnL | Executable PnL | Classification |
|---|---:|---:|---|---:|---:|---:|---|---|---|---|---|---|---:|---:|---:|---:|---|
| 2026-05-21 | `0` | `2` | proxy | `0/2` | `1/2` | `63.5s` | `0 TP / 2 SL` | `0 / 0` | `0 / 0` | `0 TP / 2 SL` | `0 TP / 1 SL` | `0 TP / 1 SL` | n/a | `100%` | `-$0.020505` | `N/A` | `WATCH_SESSION` |
| 2026-05-22 | `0` | `2` | proxy | `2/2` | `2/2` | `5.5s` | `0 TP / 2 SL` | `0 / 0` | `0 TP / 2 SL` | `0 / 0` | `0 TP / 2 SL` | `0 / 0` | n/a | `100%` | `-$0.009337` | `N/A` | `HOSTILE_SESSION_CANDIDATE` |
| 2026-05-23 | `0` | `8` | confirmed | `6/8` | `8/8` | `6.5s` | `0 TP / 4 SL` | `0 TP / 4 SL` | `0 TP / 1 SL` | `0 TP / 7 SL` | `0 TP / 5 SL` | `0 TP / 3 SL` | `6875ms mean` | `100%` | `-$0.065157` | `N/A` | `HOSTILE_SESSION_CANDIDATE` |

Combined 02h:

| Metric | Value |
|---|---:|
| trades | `12` |
| TP | `0` |
| SL | `12` |
| confirmed TP | `0` |
| confirmed SL | `8` |
| proxy rows | `4` |
| fast SL <=15s | `8/12` |
| fast SL <=30s | `11/12` |
| median hold | `6.5s` |
| signal PnL | `-$0.09499953` |
| executable PnL | `N/A` |
| dust ratio | `100%` |

## 02h vs All-Session Baseline

Same three-date baseline:

| Scope | Trades | TP | SL | TP Rate | Signal PnL | Fast SL <=15s | Fast SL <=30s | Median Hold | Dust Ratio | Executable Trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 02h only | `12` | `0` | `12` | `0.0%` | `-$0.095000` | `8` | `11` | `6.5s` | `100%` | `0` |
| all sessions | `118` | `43` | `75` | `36.4%` | `-$0.097492` | `49` | `67` | `13.0s` | `100%` | `0` |

Interpretation:

- 02h contributes almost the entire three-date net signal loss despite only `12/118` trades.
- 02h TP rate is materially worse than the all-session baseline.
- 02h median hold is half the all-session median hold.
- executable reality is zero everywhere in this range, but 02h is still a negative signal bucket.

## Lifecycle Read

Combined 02h lifecycle:

| Lifecycle | TP | SL |
|---|---:|---:|
| OPENING_SCAN | `0` | `8` |
| ACTIVE_INVENTORY_TRADING | `0` | `4` |

Does OPENING survive?

No. Across the three-date 02h sample, OPENING_SCAN is `0 TP / 8 SL`. ACTIVE is also bad, but only appears in the 2026-05-23 confirmed cluster.

Is hostility ACTIVE-specific?

No. The adverse result exists in OPENING on all three dates. ACTIVE adds more 2026-05-23 failures, but it is not the root of the full 02h pattern.

## Asset And Side Read

Combined 02h:

| Asset | TP | SL |
|---|---:|---:|
| ETH | `0` | `9` |
| BTC | `0` | `3` |

| Side | TP | SL |
|---|---:|---:|
| YES | `0` | `8` |
| NO | `0` | `4` |

Is it ETH-specific?

Mostly ETH-skewed, but not ETH-only. BTC is also `0 TP / 3 SL`, including the 2026-05-22 fast BTC YES losses and one 2026-05-23 confirmed BTC YES loss.

Is it side-specific?

No clean side-only answer. YES is worse by count, but NO also loses. The safer interpretation is session-level pressure, with ETH and YES skew.

## Quote Staleness Read

02h quote coverage exists only for 2026-05-23 in this three-date set.

2026-05-23 02h:

| Field | Count | Min | Mean | Median | Max |
|---|---:|---:|---:|---:|---:|
| `quote_stale_ms` | `8` | `4452ms` | `6875ms` | `7591ms` | `7691ms` |
| `quote_age_at_submit_ms` | `8` | `4451ms` | `6874ms` | `7589ms` | `7689ms` |
| `quote_age_at_fill_ms` | `8` | `4452ms` | `6875ms` | `7591ms` | `7691ms` |

Is it quote-staleness driven?

Not from visible evidence. The confirmed 2026-05-23 cluster has moderate exit quote ages and no `15s+` exit quote staleness. Older 2026-05-21 and 2026-05-22 rows lack quote-stale coverage, so the conclusion is:

```text
quote staleness not proven as cause
```

## Decision Blockers Around 02h

| Date | 02h Decision Rows | Approved-Like | Top Blockers |
|---|---:|---:|---|
| 2026-05-21 | `117` | `2` | `time_unsafe`, `frequency_cooldown`, `max_active_positions_per_market_reached`, `risk_plan_zero` |
| 2026-05-22 | `842` | `2` | `delta_extreme`, `confidence_too_low`, `time_unsafe`, `empty_book`, `stale_data`, `spread_too_wide` |
| 2026-05-23 | `1524` | `9` | `delta_extreme`, `confidence_too_low`, `time_unsafe`, `frequency_cooldown`, `risk_plan_zero`, `empty_book` |

Interpretation:

The 02h decision surface is also adverse-looking: many rows are filtered by extreme delta, low confidence, timing, cooldown, and orderbook gates. This supports the hostile-session candidate label, but it remains observational.

## Stability Assessment

Does 02h remain adverse across dates?

Yes. It is adverse on all three reviewed dates:

```text
2026-05-21: 0 TP / 2 SL
2026-05-22: 0 TP / 2 SL
2026-05-23: 0 TP / 8 SL
```

Is hostility stable?

Adverse direction is stable. Fast-SL intensity is not fully stable:

- 2026-05-21: adverse but not a clear fast-SL cluster.
- 2026-05-22: adverse and fast.
- 2026-05-23: adverse and fast, with confirmed outcome truth.

Therefore the current classification is `HOSTILE_SESSION_CANDIDATE`, not confirmed `HOSTILE_SESSION`.

## Required Answers

1. Does 02h remain adverse across dates?

Yes. It is `0 TP / 12 SL` across the latest three complete dates, with `8` confirmed SLs on 2026-05-23 and `4` proxy SLs on 2026-05-21/22.

2. Is hostility stable?

Directionally yes; fast-SL intensity only partially. It needs at least one more date with confirmed fast-SL behavior before promoting to `HOSTILE_SESSION`.

3. Is it ETH-specific?

No. ETH is the majority at `9/12` SLs, but BTC is also `0 TP / 3 SL`.

4. Is it ACTIVE-specific?

No. OPENING_SCAN is `0 TP / 8 SL`. ACTIVE is `0 TP / 4 SL`, all from 2026-05-23.

5. Does OPENING survive?

No. 02h OPENING does not survive in this range.

6. Does executable reality change interpretation?

Yes. It downgrades all PnL to signal-only. Every 02h trade is dust-zone / simulation-only, and executable PnL is `N/A`. The session warning remains valid for signal research, but it cannot be used as executable or live evidence.

## Final Classification

```text
NORMAL_SESSION: No
WATCH_SESSION: Too weak; adverse evidence is stronger than watch-only
HOSTILE_SESSION_CANDIDATE: Yes
HOSTILE_SESSION: Not yet
```

Reason:

02h meets adverse-date and below-baseline criteria, but fast-SL cluster persistence is only partial across the three dates and older two dates rely on proxy truth.

## Monitoring Recommendation

Keep 02h as a hostile candidate bucket:

- exclude 02h from positive session-edge claims;
- keep 02h in signal research as a negative-control session;
- require another confirmed outcome-truth date before any `HOSTILE_SESSION` promotion;
- continue separating confirmed truth from proxy rows;
- keep executable reality labels attached to every 02h row.

No runtime policy, stop-loss, threshold, risk, live, or strategy action is recommended from this audit alone.

Tests: not run; docs-only read-only audit.
