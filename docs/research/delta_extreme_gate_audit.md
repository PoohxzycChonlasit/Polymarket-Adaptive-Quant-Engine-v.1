# Delta Extreme Gate Audit

Date: 2026-05-27 21:10 Asia/Bangkok

Run under audit: `20260527T110608Z_26764_9d379e2c`

Mode: read-only audit. No code changes, runtime mutation, restart, replay, strategy, risk, execution, wallet, or live changes.

## Executive Verdict

```text
DELTA_EXTREME_VERDICT: PROTECTIVE_BUT_OVER_FILTERING_CANDIDATE
DO_NOT_CHANGE_GATE_YET: yes
PRIMARY_EVIDENCE: 142 / 146 EV-ready candidates touched delta_extreme
ONLY_DELTA_EXTREME: 6 / 142 delta-blocked EV-ready candidates
DOMINANT_COOCCURRENCE: delta_extreme + empty_book
STALE_ORACLE_ROOT: not supported as dominant cause
BAD_PRICE_ROOT: not supported as dominant cause
GENUINE_EXTREME_MARKET_STATE: plausible / likely
OBSERVABILITY_GAP: delta fields are display-nested, not canonical top-level fields
```

The delta gate is doing real protective work, but it is also nearly universal across EV-ready candidates in this run. It should remain untouched until more evidence exists, because most delta-blocked candidates also had empty-book, time-safety, or risk-plan-zero context.

The strongest research concern is not "delta is obviously wrong." It is:

```text
delta_extreme blocks almost every EV-ready candidate, while a small subset looks otherwise clean enough to deserve offline counterfactual review.
```

## Role Routing

Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`

Supporting roles: none

Why selected: this is a run-scoped JSONL observability and blocker-root-cause audit.

Files inspected:

- `docs/research/signal_rejection_root_cause_audit.md`
- `runtime/quant_data/decision_log/2026-05-27.jsonl`
- `runtime/quant_data/trade_journal/2026-05-27.jsonl`
- `runtime/quant_data/execution_log/2026-05-27.jsonl`
- `runtime/quant_data/path_truth/2026-05-27.jsonl`
- `runtime/research_state/latest_research_state.md`
- `MASTER_AGENT_ROUTER.md`
- `docs/quant_agent_setup_md/roles/11_OBSERVABILITY_INCIDENT_AGENT.md`

Files intentionally ignored: strategy code, risk code, order execution code, replay tools, wallet/live config, and unrelated reports.

## Snapshot Lineage

The run was still accumulating decisions after the previous signal rejection audit. This audit uses the latest available decision-log snapshot at audit time.

| Metric | Signal rejection audit | Delta audit snapshot |
|---|---:|---:|
| decision rows | 1230 | 1430 |
| unique candidates | 178 | 197 |
| EV-ready candidates | 133 | 146 |
| EV-ready candidates touched by `delta_extreme` | 130 | 142 |
| trade_open | 0 | 0 |
| execution_log rows | 0 | 0 |
| path_truth rows | 0 | 0 |

## Field Caveat

The useful delta diagnostics are not top-level canonical fields in the decision payload. They are present inside the nested `display` object:

| Field | Top-level presence in delta rows | Nested display presence |
|---|---:|---:|
| `score` | 0 / 885 | 885 / 885 |
| `delta_multiplier` | 0 / 885 | 885 / 885 |
| `distance_from_ptb_pct` | 0 / 885 | 885 / 885 |
| `price_change_pct` | 0 / 885 | 885 / 885 |
| `price_velocity` | 0 / 885 | 885 / 885 |

Interpretation: this audit can diagnose delta behavior, but the evidence is display-derived/proxy rather than canonical top-level research truth.

## Delta Extreme Count

| Population | Count |
|---|---:|
| decision rows | 1430 |
| `delta_extreme` rows | 885 |
| unique candidates | 197 |
| candidates touched by `delta_extreme` | 142 |
| EV-ready candidates | 146 |
| EV-ready candidates touched by `delta_extreme` | 142 |
| share of all candidates | 72.1% |
| share of EV-ready candidates | 97.3% |

## Delta Value Distribution

Display-derived numeric fields for EV-ready candidates touched by `delta_extreme`:

| Field | n | min | p25 | median | p75 | max |
|---|---:|---:|---:|---:|---:|---:|
| `score` | 142 | -18.1807 | 12.4729 | 15.8406 | 17.2300 | 21.2162 |
| `distance_from_ptb_pct` | 142 | -28.60% | -8.41% | -2.27% | 2.12% | 42.45% |
| `delta_multiplier` | 142 | 0.0 | 0.0 | 0.0 | 0.2 | 0.2 |
| `price_change_pct` | 142 | -22.77% | 0.0% | 0.0% | 0.0% | 44.95% |
| `price_velocity` | 142 | -0.000455 | 0.0 | 0.0 | 0.0 | 0.000899 |
| `edge` | 142 | 0.0000 | 0.0000 | 0.1056 | 0.3105 | 0.4394 |
| `market_price` | 142 | 0.02 | 0.03 | 0.11 | 0.46 | 0.96 |
| `fair_value` | 78 | 0.2012 | 0.3402 | 0.3688 | 0.4421 | 0.7094 |

`delta_multiplier` is not the main explanatory field here; it is usually `0.0`. The stronger signal is the high `score`, extreme `market_price`, and large `distance_from_ptb_pct` distribution.

## Absolute Delta Buckets

Display-derived `abs(distance_from_ptb_pct)` buckets for EV-ready candidates touched by `delta_extreme`:

| Absolute delta bucket | Candidates |
|---|---:|
| 0-0.5% | 9 |
| 0.5-1% | 8 |
| 1-2% | 13 |
| 2-5% | 34 |
| 5-10% | 39 |
| 10-20% | 29 |
| 20%+ | 10 |

Interpretation: `112 / 142` delta-blocked EV-ready candidates had absolute distance above `2%`. That supports a genuine extreme-state interpretation more than a pure stale-data explanation.

## Asset Split

EV-ready candidates touched by `delta_extreme`:

| Asset | Candidates |
|---|---:|
| BTC | 71 |
| ETH | 71 |

Interpretation: no asset-specific delta bias is visible in this run.

## Side Split

| Side | Candidates |
|---|---:|
| SKIP / unresolved side | 64 |
| YES | 46 |
| NO | 32 |

Interpretation: delta often triggers before a clean side is finalized. Among resolved sides, YES had more delta-blocked candidates than NO.

## Lifecycle Phase

| Lifecycle phase | Candidates |
|---|---:|
| ACTIVE_INVENTORY_TRADING | 92 |
| PROFIT_MANAGEMENT | 49 |
| OPENING_SCAN | 1 |

Interpretation: delta is not merely a final-derisk artifact. It mostly blocks candidates during ACTIVE and PROFIT phases.

## Session Hour

| Session UTC | Candidates |
|---|---:|
| 11h | 41 |
| 12h | 45 |
| 13h | 50 |
| 14h | 6 |

Interpretation: the effect persisted across multiple session hours, not just one short interval.

## Time Remaining

| Time remaining bucket | Candidates |
|---|---:|
| 31-60s | 49 |
| 61-120s | 59 |
| 121-180s | 26 |
| 180s+ | 8 |

Numeric distribution:

| Field | n | min | p25 | median | p75 | max |
|---|---:|---:|---:|---:|---:|---:|
| `seconds_remaining` | 142 | 36 | 46 | 76 | 119 | 275 |

Interpretation: `delta_extreme` is not mostly late-hard-close behavior. It blocked many candidates with more than a minute remaining.

## Market Price Buckets

No canonical `price_bucket` field was available. Proxy market-price buckets:

| Proxy market price bucket | Candidates |
|---|---:|
| `proxy_0.00_0.05` | 44 |
| `proxy_0.05_0.20` | 39 |
| `proxy_0.20_0.40` | 20 |
| `proxy_0.40_0.60` | 12 |
| `proxy_0.60_0.80` | 8 |
| `proxy_0.80_1.00` | 19 |

Interpretation: a large share of delta-blocked candidates were at extreme displayed market prices below `0.20` or above `0.80`. That supports a safety rationale, especially in 5-minute binary markets where late/imbalanced prices can move violently.

## Co-Occurrence

EV-ready candidates touched by `delta_extreme`:

| Co-occurrence | Count | % of delta EV-ready |
|---|---:|---:|
| `delta_extreme + empty_book` | 130 | 91.5% |
| `delta_extreme + time_unsafe` | 72 | 50.7% |
| `delta_extreme + risk_plan_zero` | 26 | 18.3% |
| `delta_extreme` only | 6 | 4.2% |

Blocker-set distribution:

| Blocker set | Candidates |
|---|---:|
| `delta_extreme + empty_book` | 57 |
| `delta_extreme + empty_book + time_unsafe` | 48 |
| `delta_extreme + empty_book + risk_plan_zero + time_unsafe` | 18 |
| `delta_extreme + empty_book + risk_plan_zero` | 7 |
| `delta_extreme` only | 6 |
| `delta_extreme + time_unsafe` | 5 |
| `delta_extreme + risk_plan_zero + time_unsafe` | 1 |

Interpretation: most delta-blocked candidates were not "clean except delta." Delta usually appeared with empty-book context and often with time safety. Only `6 / 142` EV-ready delta candidates were blocked by delta alone among the four tracked blockers.

## Delta-Only Candidates

The small delta-only set matters because these candidates had relatively clean context:

| Property | Observed in sampled delta-only candidates |
|---|---|
| lifecycle | ACTIVE_INVENTORY_TRADING |
| time remaining | 95s to 204s in examples |
| orderbook fetch | fresh executable |
| market readiness | ready |
| liquidity | healthy |
| spread | normalized |
| orderbook snapshot age | 15ms to 31ms in examples |

Examples:

```text
BTC SKIP score=-14.36 distance=0.65% market_price=0.91 oracle_age=1493ms readiness=ready liquidity=HEALTHY spread=NORMALIZED seconds_remaining=104
ETH SKIP score=-14.85 distance=5.70% market_price=0.94 oracle_age=234ms readiness=ready liquidity=HEALTHY spread=NORMALIZED seconds_remaining=103
ETH YES score=12.44 distance=0.84% market_price=0.61 fair_value=0.6841 edge=0.0741 oracle_age=435ms readiness=ready liquidity=HEALTHY spread=NORMALIZED seconds_remaining=204
BTC NO score=16.51 distance=1.60% market_price=0.27 fair_value=0.4456 edge=0.1756 oracle_age=717ms readiness=ready liquidity=HEALTHY spread=NORMALIZED seconds_remaining=95
```

Interpretation: these are the best candidates for offline counterfactual review. They are not enough to justify changing the gate, but they show where over-filtering may live.

## Stale Oracle / Misalignment Check

EV-ready candidates touched by `delta_extreme`:

| Freshness / alignment field | Distribution |
|---|---|
| `oracle_age_ms` | min `5`, median `674`, p75 `1069`, max `9229` |
| oracle age bucket | `0-250ms=28`, `250ms-1s=72`, `1-2s=41`, `5s+=1` |
| `orderbook_snapshot_age_ms_at_decision` | median `15`, p75 `30`, max `297` |
| orderbook snapshot bucket | `0-50ms=137`, `50-250ms=4`, `250ms-1s=1` |
| `orderbook_age_ms` | median `94`, p75 `161`, max `894` |
| current fetch status | `fresh_fetch_executable=142` |
| yes/no mid-sum abs deviation | median `0`, max `0.15` |
| mid-sum deviation > 0.05 | `3 / 142` |

Interpretation:

Stale oracle is not supported as the dominant cause. Most oracle/feed ages were below two seconds, and only one delta-blocked EV-ready candidate had `oracle_age_ms > 5000`.

Wrong current price is also not supported as the dominant cause. The yes/no mid-sum generally reconciled to approximately `1.0`, with only `3 / 142` showing mid-sum deviation above `0.05`.

The stronger evidence points to genuine extreme market state or extreme market-price position relative to PTB, with an observability caveat around empty-book context.

## Market State Check

| Field | Distribution |
|---|---|
| market readiness | `empty_book=97`, `late_hard_close_zone=35`, `ready=8`, `orderbook_unavailable=2` |
| liquidity state | `HEALTHY=108`, `EMPTY=34` |
| spread state | `NORMALIZED=141`, `WIDE=1` |
| market price availability | `142 / 142` |
| fair value availability | `78 / 142` |

This is the uncomfortable part: many delta-blocked candidates had `fresh_fetch_executable`, `HEALTHY` liquidity, and `NORMALIZED` spread, while market readiness still often said `empty_book`. That does not prove the delta gate is wrong, but it does show the runtime state labels are entangled.

Best interpretation:

```text
DELTA_EXTREME_IS_PROTECTING_FROM EXTREME PRICE/PTB STATE
BUT EMPTY_BOOK / READINESS LINEAGE MAKES CLEAN CAUSAL ATTRIBUTION PARTIAL
```

## Answers

### 1. Is delta_extreme protecting from bad market state?

Yes, likely.

The strongest support:

- `142 / 146` EV-ready candidates touched the gate.
- Many had extreme market prices below `0.20` or above `0.80`.
- `112 / 142` had absolute `distance_from_ptb_pct > 2%`.
- Stale oracle and wrong yes/no price reconciliation are not dominant explanations.

This looks like genuine bad/extreme market state protection, not just noise.

### 2. Is it caused by stale/misaligned oracle/current price?

Not as the dominant cause.

Oracle/feed age was usually sub-two-seconds, orderbook snapshots were usually fresh, and yes/no mid-sum reconciliation was mostly clean. There are isolated stale/misaligned cases, but not enough to explain the gate firing on almost all EV-ready candidates.

### 3. Does it block all otherwise-valid candidates?

No, not all.

It blocks almost all EV-ready candidates, but most had co-blockers:

- `91.5%` also had empty-book context.
- `50.7%` also had time-unsafe context.
- only `6 / 142` were delta-only among the tracked blockers.

The delta-only subset is the best evidence of possible over-filtering, but it is small.

### 4. Should it remain untouched until more evidence?

Yes.

Do not change `delta_extreme` from this run alone. It prevented all trades, but the evidence still leans safety-first because of extreme price/PTB states and heavy co-occurrence with empty-book/time-safety context.

### 5. What evidence is required before changing it?

Minimum evidence before any gate change:

- Multi-run delta audit showing repeated `delta_extreme` suppression of EV-ready candidates.
- Counterfactual path truth for delta-only candidates, especially `30s`, `60s`, and `event_end` outcomes.
- Canonical top-level `delta_score`, `distance_from_ptb_pct`, `delta_multiplier`, `price_change_pct`, and `price_velocity` fields.
- Clear orderbook lineage separating current fetch, cached executable book, and empty-book failure.
- Stale-oracle controls proving delta decisions are not caused by quote/oracle lag.
- Outcome comparison: delta-only candidates versus delta+empty_book and non-delta EV-ready candidates.
- No live or strategy/risk change until paper evidence shows missed EV after executable truth filters.

## Recommended Next Step

Three options:

1. `SAFE_EV_PRESERVATION`: leave the delta gate untouched and continue evidence farming until natural trades resume.
2. `AGGRESSIVE_INFORMATION_DISCOVERY`: run a read-only cross-run delta-extreme audit to determine whether this is persistent or run-specific.
3. `STRUCTURAL_ROOT_CAUSE`: design observability-only canonical delta fields and orderbook lineage fields before any policy review.

Recommended: option 2, then option 3 if the pattern persists. No runtime policy change is justified yet.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Replay run: No

Runtime restart: No

Code changes: No

Tests run: none; docs-only/read-only JSONL audit.
