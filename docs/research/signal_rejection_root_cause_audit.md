# Signal Rejection Root Cause Audit

Date: 2026-05-27 20:53 Asia/Bangkok

Run under audit: `20260527T110608Z_26764_9d379e2c`

Mode: read-only audit. No code changes, runtime mutation, restart, replay, strategy, risk, execution, wallet, or live changes.

## Executive Verdict

```text
ROOT_CAUSE_CLASSIFICATION: SIGNAL_REJECTED_BY_SAFETY_AND_EXECUTABILITY_GATES
NO_SIGNAL: false
NO_TRADE_BEHAVIOR: correct under current guards, but over-filtering candidate remains open
DOMINANT_BLOCKER: delta_extreme
SECONDARY_BLOCKERS: empty_book_context, time_unsafe, risk_plan_zero
RISK_PLAN_ZERO_CAUSE: likely micro sizing/capital ladder/minimum-size interaction, not proven dust
EMPTY_BOOK_CAUSE: mixed real liquidity + fetch/reuse/serialization ambiguity
```

The prior no-trade audit snapshot had `116` EV-ready candidates. The latest decision-log snapshot grew while the paper run continued:

| Metric | Prior audit | Latest snapshot |
|---|---:|---:|
| decision rows | 1096 | 1230 |
| unique candidates | 156 | 178 |
| EV-ready candidates | 116 | 133 |
| trade_open | 0 | 0 |
| trade_close | 0 | 0 |
| execution_log rows | 0 | 0 |
| path_truth rows | 0 | 0 |

The answer is unchanged: opportunities existed, model/EV evidence existed, but no candidate survived the combined safety and executability filters into order submission.

## Role Routing

Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`

Supporting roles: none

Why selected: this is a run-scoped observability, JSONL, and evidence-quality diagnosis.

Files inspected:

- `docs/research/no_trade_open_runtime_audit.md`
- `runtime/quant_data/decision_log/2026-05-27.jsonl`
- `runtime/quant_data/trade_journal/2026-05-27.jsonl`
- `runtime/quant_data/execution_log/2026-05-27.jsonl`
- `runtime/quant_data/path_truth/2026-05-27.jsonl`
- `runtime/research_state/latest_research_state.md`
- `MASTER_AGENT_ROUTER.md`
- `docs/quant_agent_setup_md/roles/11_OBSERVABILITY_INCIDENT_AGENT.md`

Files intentionally ignored: strategy code, risk code, order execution code, replay tools, wallet/live config, and unrelated reports.

## Method

Rows were grouped by `candidate_id`. A candidate was counted as EV-ready if any row had `ev_candidate_ready=true` or `ev_after_spread_available=true`.

Blockers were counted as candidate-level `ever-hit` flags:

| Blocker | Detection |
|---|---|
| `delta_extreme` | `normalized_skip_reason=delta_extreme`, `skip_reason_primary=imbalance_extreme`, or raw `delta_extreme` |
| `time_unsafe` | `normalized_skip_reason=time_unsafe`, `skip_reason_primary=cutoff_passed`, `Entry cutoff...`, or `late_entry_hard_block=true` |
| `empty_book` | `empty_book`, `orderbook_unavailable`, `stale_data`, `book_warming`, `thin_liquidity`, empty-book readiness, or failed fresh fetch |
| `risk_plan_zero` | `normalized_skip_reason=risk_plan_zero`, `skip_reason_primary=zero_size_plan`, `decision_type=risk_rejected`, or raw `risk_plan_zero` |

Canonical `price_bucket` fields were not present. The audit therefore reports price as unavailable where no `market_price` existed, and uses a clearly labeled `proxy_market_price_*` bucket only where `market_price` was available.

## Blocker Summary

Denominators:

| Population | Count |
|---|---:|
| all candidates | 178 |
| EV-ready candidates | 133 |

| Blocker | Row count | All candidates | % all candidates | EV-ready candidates | % EV-ready |
|---|---:|---:|---:|---:|---:|
| `delta_extreme` | 783 | 130 | 73.0% | 130 | 97.7% |
| `empty_book` | 1107 | 161 | 90.4% | 118 | 88.7% |
| `time_unsafe` | 236 | 74 | 41.6% | 64 | 48.1% |
| `risk_plan_zero` | 41 | 23 | 12.9% | 23 | 17.3% |

Interpretation: `delta_extreme` is the decisive EV-ready blocker because it touched nearly every EV-ready candidate. `empty_book` is broader contextual degradation and often co-occurs with other final blockers. `time_unsafe` mostly appears at the hard-close boundary. `risk_plan_zero` is smaller but important because it includes otherwise positive-EV, confidence-visible candidates.

## Delta Extreme

EV-ready candidates affected: `130 / 133 = 97.7%`

Asset split:

| Asset | EV-ready candidates |
|---|---:|
| BTC | 65 |
| ETH | 65 |

Side split:

| Side | EV-ready candidates |
|---|---:|
| SKIP / unresolved side | 59 |
| YES | 44 |
| NO | 27 |

Lifecycle split:

| Lifecycle phase | EV-ready candidates |
|---|---:|
| ACTIVE_INVENTORY_TRADING | 86 |
| PROFIT_MANAGEMENT | 44 |

Session-hour split:

| Session UTC | EV-ready candidates |
|---|---:|
| 11h | 41 |
| 12h | 45 |
| 13h | 44 |

Proxy price bucket:

| Proxy bucket | EV-ready candidates |
|---|---:|
| `proxy_market_price_0.00_0.20` | 75 |
| `proxy_market_price_0.20_0.40` | 20 |
| `proxy_market_price_0.40_0.60` | 12 |
| `proxy_market_price_0.60_0.80` | 7 |
| `proxy_market_price_0.80_1.00` | 16 |

Interpretation:

`delta_extreme` is protecting the bot from extreme imbalance/movement states, and it is balanced across BTC/ETH. However, touching `97.7%` of EV-ready candidates means it effectively suppressed almost all apparent opportunity in this run. With no trade outcomes, this cannot be called wrong, but it is a strong over-filtering candidate for offline counterfactual review.

## Time Unsafe

EV-ready candidates affected: `64 / 133 = 48.1%`

Asset split:

| Asset | EV-ready candidates |
|---|---:|
| BTC | 32 |
| ETH | 32 |

Side split:

| Side | EV-ready candidates |
|---|---:|
| YES | 29 |
| NO | 12 |
| SKIP / unresolved side | 21 |
| YES/NO unresolved | 2 |

Lifecycle split:

| Lifecycle phase | EV-ready candidates |
|---|---:|
| FINAL_DERISK | 63 |
| ACTIVE_INVENTORY_TRADING | 1 |

Session-hour split:

| Session UTC | EV-ready candidates |
|---|---:|
| 11h | 19 |
| 12h | 24 |
| 13h | 21 |

Time remaining distribution:

| Bucket | EV-ready candidates |
|---|---:|
| 0-15s | 61 |
| 16-30s | 2 |
| 31-35s | 0 |
| 36s+ | 1 |

Price bucket: unavailable for these rows because canonical price bucket fields were absent and `market_price` was generally null after the time block.

Interpretation:

This mostly looks like correct hard-close safety behavior. `63 / 64` affected EV-ready candidates were in `FINAL_DERISK`, and `61 / 64` had only `0-15s` remaining. The one `36s+` case is a small lifecycle/timestamp consistency flag, not enough to conclude the cutoff is too strict.

## Empty Book

EV-ready candidates affected: `118 / 133 = 88.7%`

Asset split:

| Asset | EV-ready candidates |
|---|---:|
| BTC | 59 |
| ETH | 59 |

Side split:

| Side | EV-ready candidates |
|---|---:|
| SKIP / unresolved side | 49 |
| YES | 43 |
| NO | 24 |
| YES/NO unresolved | 2 |

Lifecycle split:

| Lifecycle phase | EV-ready candidates |
|---|---:|
| FINAL_DERISK | 56 |
| ACTIVE_INVENTORY_TRADING | 55 |
| PROFIT_MANAGEMENT | 7 |

Session-hour split:

| Session UTC | EV-ready candidates |
|---|---:|
| 11h | 29 |
| 12h | 45 |
| 13h | 44 |

Price / availability:

| Bucket | EV-ready candidates |
|---|---:|
| unavailable | 57 |
| `proxy_market_price_0.00_0.20` | 27 |
| `proxy_market_price_0.20_0.40` | 14 |
| `proxy_market_price_0.40_0.60` | 8 |
| `proxy_market_price_0.60_0.80` | 3 |
| `proxy_market_price_0.80_1.00` | 9 |

Fetch-state details for affected EV-ready candidates:

| Field | Distribution |
|---|---|
| last normalized blocker row | `delta_extreme=61`, `time_unsafe=56`, `stale_data=1` |
| `orderbook_readiness_reason` | `empty_book=118` |
| `orderbook_current_fetch_status` | `fresh_fetch_executable=90`, `fresh_fetch_failed=28` |
| `orderbook_unavailable_reason` | `empty_book=118` |
| `liquidity_state` | `HEALTHY=92`, `EMPTY=26` |
| `executable_spread_state` | `NORMALIZED=60`, `UNKNOWN=57`, `WIDE=1` |

Interpretation:

This is not cleanly classifiable as only real liquidity disappearance. The evidence is mixed:

- `orderbook_readiness_reason=empty_book` is widespread.
- But `90 / 118` affected EV-ready candidates show `fresh_fetch_executable`.
- `92 / 118` show `liquidity_state=HEALTHY`.
- `60 / 118` still show `executable_spread_state=NORMALIZED`.

Best classification:

```text
EMPTY_BOOK_CONTEXTUAL / OBSERVABILITY_AMBIGUOUS
```

It may represent side-specific book evaporation, stale/fallback book reuse, or serialization ambiguity around current fetch versus cached executable state. It should not be treated as pure market liquidity truth until the orderbook lineage fields are clearer.

## Risk Plan Zero

EV-ready candidates affected: `23 / 133 = 17.3%`

Asset split:

| Asset | EV-ready candidates |
|---|---:|
| BTC | 21 |
| ETH | 2 |

Side split:

| Side | EV-ready candidates |
|---|---:|
| YES | 15 |
| NO | 8 |

Lifecycle split:

| Lifecycle phase | EV-ready candidates |
|---|---:|
| ACTIVE_INVENTORY_TRADING | 22 |
| OPENING_SCAN | 1 |

Session-hour split:

| Session UTC | EV-ready candidates |
|---|---:|
| 11h | 6 |
| 12h | 9 |
| 13h | 8 |

Price bucket: unavailable for risk-plan-zero rows.

Representative evidence:

| Field | Observed pattern |
|---|---|
| `calculated_order_size` | `0.0` |
| `risk_per_trade` | `0.0` |
| `micro_position_size` | `0.050248` |
| `bankroll_tier_id` | `T0_MICRO_SEED` |
| `bankroll_mode` | `MICRO_SURVIVAL` |
| `risk_plan_zero_reason` | `unknown` |
| `min_fillable_size_usd` | ranged from about `40` to `1115` in inspected rows |
| EV/confidence | positive EV and visible confidence in representative rows |

Interpretation:

`risk_plan_zero` is likely caused by a sizing/minimum-executable/capital-ladder interaction in micro bankroll mode. It is concentrated in BTC, mostly YES, and almost entirely ACTIVE.

However, the current evidence does not prove a single root cause because `risk_plan_zero_reason=unknown`. It may be dust, minimum fillable size, capital ladder, zero risk budget, or a combination. Label it:

```text
RISK_BLOCKED_ZERO_SIZE_PLAN
CAUSE: LIKELY_MICRO_SIZING_OR_MINIMUM_SIZE
CONFIDENCE: PARTIAL
```

Do not call this executable dust truth yet.

## Co-Occurrence

EV-ready co-occurrence:

| Blocker pair | EV-ready candidates | % EV-ready |
|---|---:|---:|
| `delta_extreme + empty_book` | 118 | 88.7% |
| `delta_extreme + time_unsafe` | 64 | 48.1% |
| `time_unsafe + empty_book` | 58 | 43.6% |
| `delta_extreme + risk_plan_zero` | 21 | 15.8% |
| `empty_book + risk_plan_zero` | 20 | 15.0% |
| `time_unsafe + risk_plan_zero` | 15 | 11.3% |

EV-ready blocker-set distribution:

| Blocker set | EV-ready candidates |
|---|---:|
| `delta_extreme + empty_book` | 54 |
| `delta_extreme + empty_book + time_unsafe` | 44 |
| `delta_extreme + empty_book + risk_plan_zero + time_unsafe` | 14 |
| `delta_extreme` only | 6 |
| `delta_extreme + empty_book + risk_plan_zero` | 6 |
| `delta_extreme + time_unsafe` | 5 |
| `risk_plan_zero` only | 2 |
| `delta_extreme + risk_plan_zero + time_unsafe` | 1 |
| none of these four | 1 |

Interpretation:

The blockers are highly entangled. The dominant practical path is:

```text
EV-ready candidate
-> delta_extreme and/or empty_book context
-> later time_unsafe near close
-> no order submission
```

`risk_plan_zero` is a smaller but cleaner separate blocker because it can stop positive-EV candidates during ACTIVE before final derisk.

## Answers

### 1. Is no-trade behavior correct safety?

Mostly yes under current guardrails.

The runtime avoided trading during extreme imbalance, empty/stale book contexts, late hard-close windows, and zero-size risk plans. There were no execution rows, so no unsafe order slipped through.

But research verdict is not “all good.” The no-trade outcome is also a candidate over-filtering signal because `delta_extreme` touched `97.7%` of EV-ready candidates.

### 2. Is risk_plan_zero caused by sizing/dust/capital ladder?

Likely sizing/capital-ladder/minimum-size interaction, but not proven.

Evidence points to micro bankroll mode:

- `bankroll_tier_id=T0_MICRO_SEED`
- `bankroll_mode=MICRO_SURVIVAL`
- `micro_position_size=0.050248`
- `calculated_order_size=0.0`
- `risk_per_trade=0.0`
- positive EV/confidence present

The blocker is not diagnosable to a single cause because `risk_plan_zero_reason=unknown` and canonical dust/executable minimum fields are not present in the decision row.

### 3. Is empty_book from real liquidity or stale market parsing?

Mixed / ambiguous.

Some evidence supports real side-specific liquidity disappearance, but many affected candidates simultaneously show `liquidity_state=HEALTHY`, `fresh_fetch_executable`, or `executable_spread_state=NORMALIZED`. That means the current fields are blending current fetch failure, cached book state, and executable-state memory.

Verdict:

```text
EMPTY_BOOK_IS_REAL_ENOUGH_TO_SKIP
BUT_NOT_CLEAN_ENOUGH_TO_CLASSIFY_AS PURE_LIQUIDITY_TRUTH
```

### 4. Is time_unsafe too strict near lifecycle boundary?

Not obviously.

`61 / 64` affected EV-ready candidates had `0-15s` remaining, and `63 / 64` were in `FINAL_DERISK`. That is exactly where hard-close protection should dominate.

The one `36s+` case should be treated as a small observability/lifecycle-boundary anomaly, not proof that the cutoff is too strict.

### 5. Is delta_extreme protecting us or blocking all opportunity?

Both.

It is protecting the bot by rejecting extreme imbalance states, but in this run it also blocked almost all EV-ready opportunities:

```text
130 / 133 EV-ready candidates = 97.7%
```

Without counterfactual outcomes, do not weaken it. But it deserves offline review because the run shows `delta_extreme` as the dominant reason EV-ready candidates never became trades.

## Research Classification

```text
NO_TRADE_REASON: SIGNAL_REJECTED
PRIMARY_ROOT: DELTA_EXTREME_DOMINANT
SECONDARY_ROOTS: EMPTY_BOOK_CONTEXTUAL, TIME_UNSAFE_FINAL_DERISK, RISK_PLAN_ZERO_MICRO_SIZING_CANDIDATE
COOLDOWN_ROOT: NOT_SUPPORTED
NO_SIGNAL_ROOT: REJECTED
OVER_FILTERING_RISK: PLAUSIBLE_NOT_PROVEN
```

## Next Safe Step

Three options:

1. `SAFE_EV_PRESERVATION`: keep collecting paper evidence until a natural trade open validates replay-key wiring.
2. `AGGRESSIVE_INFORMATION_DISCOVERY`: run a read-only cross-run `delta_extreme` blocker audit to see whether it systematically suppresses EV-ready candidates or only this run.
3. `STRUCTURAL_ROOT_CAUSE`: design observability-only fields for `risk_plan_zero_reason`, canonical `price_bucket`, and orderbook lineage separation.

Recommended: option 2 first. It is read-only and directly tests whether the dominant blocker is a one-run artifact or a persistent no-trade regime.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Replay run: No

Runtime restart: No

Code changes: No

Tests run: none; docs-only/read-only JSONL audit.
