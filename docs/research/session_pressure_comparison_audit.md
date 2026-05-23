# Session Pressure Comparison Audit

Date: 2026-05-24

Scope: read-only comparison of active session hypotheses across the latest three complete trading dates before 2026-05-24.

Runtime behavior changed: No
Live behavior changed: No

## Verdict

This is a signal-pressure comparison, not executable edge.

Across 2026-05-21 through 2026-05-23:

| Session Bucket | Current Label | Pressure Verdict |
|---|---|---|
| `02h` | `HOSTILE_SESSION_CANDIDATE` | strongest negative pressure; keep separate and exclude from positive edge claims |
| `09h10h` | `SESSION_EDGE_CANDIDATE` | best positive signal bucket, but date-concentrated and still has fast SL pressure |
| `16h` | `PRACTICAL_SURVIVABLE candidate` | downgraded to `WATCH / MIXED`; recent evidence is not clean enough for practical survivability |
| `01h` | `A_TIER candidate` | thin, balanced, mild positive signal PnL; not enough evidence for tier confidence |

Executable reality result:

```text
all compared buckets = DUST_ZONE / SIMULATION_ONLY
executable_pnl = N/A
```

## Sources

- `docs/research/session_02h_multiday_validation.md`
- `docs/research/session_02h_fast_sl_audit.md`
- `docs/research/fast_stop_loss_audit.md`
- `docs/research/session_regime_09h10h_persistence.md`
- `docs/research/session_survival_ranking.md`
- `docs/research/hourly_market_personality_map.md`
- `docs/research/session_personality_stability.md`
- `runtime/quant_data/trade_journal/2026-05-21.jsonl`
- `runtime/quant_data/trade_journal/2026-05-22.jsonl`
- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-21.jsonl`
- `runtime/quant_data/execution_log/2026-05-22.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`

## Method

Reviewed dates:

```text
2026-05-21
2026-05-22
2026-05-23
```

Session buckets:

- `02h`: hour `02`
- `09h10h`: hours `09` and `10`
- `16h`: hour `16`
- `01h`: hour `01`

Outcome handling:

- `trade_result` used when present.
- Older rows without `trade_result` use stop/take-profit reason or PnL-sign proxy.
- Confirmed and proxy rows are counted separately.

Executable overlay:

- `minimum practical shares = 5`
- rows below the minimum are `DUST_ZONE` / `SIMULATION_ONLY`
- executable PnL only counts trades that clear the practical minimum

## Pressure Table

| Session | Trades | TP | SL | TP Rate | Fast SL <=15s | Fast SL % | Median Hold | Signal PnL | Dust Ratio | Executable Trades | Executable PnL | Truth Mix |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `02h` | `12` | `0` | `12` | `0.0%` | `8` | `66.7%` | `6.5s` | `-$0.09499953` | `100%` | `0` | `N/A` | `8 confirmed / 4 proxy` |
| `09h10h` | `16` | `8` | `8` | `50.0%` | `7` | `87.5%` | `11.0s` | `+$0.02647529` | `100%` | `0` | `N/A` | `12 confirmed / 4 proxy` |
| `16h` | `9` | `4` | `5` | `44.4%` | `3` | `60.0%` | `22.0s` | `-$0.02217450` | `100%` | `0` | `N/A` | `9 confirmed / 0 proxy` |
| `01h` | `2` | `1` | `1` | `50.0%` | `0` | `0.0%` | `20.0s` | `+$0.00224975` | `100%` | `0` | `N/A` | `2 confirmed / 0 proxy` |
| all-session baseline | `118` | `43` | `75` | `36.4%` | `49` | `65.3%` | `13.0s` | `-$0.09749249` | `100%` | `0` | `N/A` | `51 confirmed / 67 proxy` |

Interpretation:

- `02h` is the cleanest negative bucket: no TP, deepest signal loss, shortest median hold.
- `09h10h` is the best positive bucket by signal PnL and TP count, but not clean: SL count equals TP count in the three-date window.
- `16h` does not currently justify "practical survivable" on recent evidence alone because it is negative and below 50% TP.
- `01h` is too thin to trust: only two confirmed trades.

## Lifecycle Split

| Session | OPENING TP/SL | ACTIVE TP/SL | Read |
|---|---|---|---|
| `02h` | `0 TP / 8 SL` | `0 TP / 4 SL` | both lifecycle phases fail |
| `09h10h` | `5 TP / 6 SL` | `3 TP / 2 SL` | ACTIVE is the cleaner split; OPENING mixed |
| `16h` | `3 TP / 2 SL` | `1 TP / 3 SL` | OPENING survives better than ACTIVE |
| `01h` | `1 TP / 0 SL` | `0 TP / 1 SL` | opening-only hint, sample too small |

Lifecycle interpretation:

`02h` is not merely an ACTIVE problem. OPENING fails hardest there. `09h10h` is the only bucket where ACTIVE is net positive in this comparison.

## Asset Split

| Session | BTC TP/SL | ETH TP/SL | Read |
|---|---|---|---|
| `02h` | `0 TP / 3 SL` | `0 TP / 9 SL` | ETH-heavy, but BTC also fails |
| `09h10h` | `3 TP / 1 SL` | `5 TP / 7 SL` | BTC is cleaner; ETH mixed |
| `16h` | `0 TP / 2 SL` | `4 TP / 3 SL` | ETH carries the bucket; BTC fails |
| `01h` | `0 / 0` | `1 TP / 1 SL` | ETH-only and tiny |

Asset interpretation:

The best cross-asset read is `09h10h`, because BTC contributes positively there. `16h` is not cross-asset survivable in this window because BTC is `0/2`.

## Side Split

| Session | YES TP/SL | NO TP/SL | Read |
|---|---|---|---|
| `02h` | `0 TP / 8 SL` | `0 TP / 4 SL` | both fail; YES worse by count |
| `09h10h` | `4 TP / 3 SL` | `4 TP / 5 SL` | YES slightly cleaner, both mixed |
| `16h` | `2 TP / 1 SL` | `2 TP / 4 SL` | NO side is weak |
| `01h` | `0 TP / 1 SL` | `1 TP / 0 SL` | split one each |

Side interpretation:

There is no universal YES/NO rule. The only strong side warning is `02h YES`, which is `0 TP / 8 SL`.

## Quote Staleness

| Session | Quote Stale Coverage | Mean `quote_stale_ms` | Median `quote_stale_ms` | Read |
|---|---:|---:|---:|---|
| `02h` | `8/12` | `6875ms` | `7591ms` | not stale-driven in confirmed rows |
| `09h10h` | `8/16` | `11115ms` | `11867ms` | moderate quote age |
| `16h` | `6/9` | `13367ms` | `13239ms` | oldest among compared buckets |
| `01h` | `2/2` | `13315ms` | `13315ms` | covered but tiny sample |
| baseline | `34/118` | `10218ms` | `10646ms` | comparison baseline |

Quote interpretation:

`02h` is not the stalest bucket. The hostile read is driven by outcome and hold-time pressure, not visible quote staleness. `16h` and `01h` have older quote ages in this comparison, but too little executable evidence to draw policy conclusions.

## Date Trend

| Session | 2026-05-21 | 2026-05-22 | 2026-05-23 |
|---|---|---|---|
| `02h` | `0 TP / 2 SL`, `-$0.020505` | `0 TP / 2 SL`, `-$0.009337` | `0 TP / 8 SL`, `-$0.065157` |
| `09h10h` | `0 TP / 2 SL`, `-$0.011260` | `2 TP / 4 SL`, `-$0.025318` | `6 TP / 2 SL`, `+$0.063053` |
| `16h` | no trades | `2 TP / 1 SL`, `+$0.002704` | `2 TP / 4 SL`, `-$0.024879` |
| `01h` | no trades | no trades | `1 TP / 1 SL`, `+$0.002250` |

Date interpretation:

`02h` is consistently adverse. `09h10h` is the only session with a strong upside day, but it is date-concentrated on 2026-05-23. `16h` weakened on 2026-05-23. `01h` has too little evidence.

## Ranking

| Rank | Session | Current Research Read |
|---:|---|---|
| 1 | `09h10h` | best signal-edge candidate, but needs more dates and executable-size evidence |
| 2 | `01h` | mild positive but too thin; keep as watch/A-tier candidate only if using legacy context |
| 3 | `16h` | mixed; downgrade from practical survivable to watch until it repeats positively |
| 4 | `02h` | hostile candidate and negative-control session |

## Key Findings

1. `02h` is the clearest pressure bucket.

It has `0 TP / 12 SL`, median hold `6.5s`, and near-total signal loss contribution.

2. `09h10h` remains the best positive candidate.

It is the only bucket with meaningful positive signal PnL and net-positive ACTIVE behavior, but its edge is concentrated on 2026-05-23.

3. `16h` is not yet practical survivable.

It has confirmed evidence but recent pressure is mixed: `4 TP / 5 SL`, negative signal PnL, and `0 TP / 2 SL` on BTC.

4. `01h` is too thin.

It has only `2` confirmed trades in the window. Treat as watch, not a strong tier.

5. Executable reality dominates all interpretation.

Every compared trade is dust-zone / simulation-only under the `5 share` practical minimum overlay. No session has executable PnL.

## Final Classification

```text
02h: HOSTILE_SESSION_CANDIDATE
09h10h: SESSION_EDGE_CANDIDATE
16h: WATCH / MIXED_SURVIVAL_CANDIDATE
01h: WATCH / THIN_A_TIER_CANDIDATE
EXECUTABLE_EDGE: NONE
```

## Recommendation

Use the sessions as research buckets only:

- keep `02h` separate as a negative control;
- prioritize `09h10h` for more evidence;
- do not promote `16h` or `01h` without more confirmed trades;
- keep executable reality labels attached to every session table;
- do not make runtime, risk, threshold, or live changes from this audit.

Tests: not run; docs-only read-only audit.
