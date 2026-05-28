# No Trade Open Runtime Audit

Date: 2026-05-27 20:36 Asia/Bangkok

Run under audit: `20260527T110608Z_26764_9d379e2c`

Mode: read-only audit. No code changes, runtime mutation, restart, replay, strategy, risk, execution, wallet, or live changes.

## Executive Verdict

```text
NO_TRADE_OPEN_CLASSIFICATION: SIGNAL_REJECTED
PRIMARY_BLOCKERS: delta_extreme, time_unsafe, empty_book
SECONDARY_BLOCKER: risk_plan_zero
COOLDOWN: not observed
NO_SIGNAL: false
```

The run did not fail because there were no candidates or no model/EV visibility. It produced `1096` decision rows across `156` unique candidates, with `152` candidates ever reaching model-ready state and `116` candidates ever reaching EV-candidate-ready state.

Despite that, every decision row was a skip/reject:

- `trade_open`: `0`
- `trade_close`: `0`
- `execution_log`: `0`
- `path_truth`: `0`

The dominant explanation is that opportunities existed but were rejected before order execution. Most rejection pressure came from `delta_extreme`, late cutoff / hard-close timing, and empty-book/orderbook availability. A smaller but important bucket reached positive EV and then received `risk_plan_zero`.

## Role Routing

Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`

Supporting roles: none

Why selected: this is a run-scoped observability and JSONL evidence diagnosis.

Files inspected:

- `runtime/quant_data/decision_log/2026-05-27.jsonl`
- `runtime/quant_data/trade_journal/2026-05-27.jsonl`
- `runtime/quant_data/execution_log/2026-05-27.jsonl`
- `runtime/quant_data/path_truth/2026-05-27.jsonl`
- `runtime/research_state/latest_research_state.md`
- `MASTER_AGENT_ROUTER.md`
- `docs/quant_agent_setup_md/roles/11_OBSERVABILITY_INCIDENT_AGENT.md`

Files intentionally ignored: strategy modules, risk modules, order/execution modules, replay tools, wallet/live config, and unrelated reports.

## Run Coverage

| Metric | Count |
|---|---:|
| decision rows | 1096 |
| decision parse errors | 0 |
| unique candidates | 156 |
| unique paper replay keys in decision rows | 130 |
| first decision timestamp | `2026-05-27T11:08:33.098485Z` |
| last decision timestamp in audit snapshot | `2026-05-27T13:34:51.982561Z` |
| trade_journal rows | 0 |
| trade_open | 0 |
| trade_close | 0 |
| execution_log rows | 0 |
| path_truth rows | 0 |

## Decision Outcome

Row-level decision outcomes:

| Field | Count |
|---|---:|
| `decision=skip` | 1096 |
| `decision_type=skipped` | 1061 |
| `decision_type=risk_rejected` | 35 |

No submit/fill/position event was emitted. Since no position opened, path truth had no position to checkpoint.

## Candidate Count And Signal Availability

| Signal visibility metric | Count |
|---|---:|
| unique candidates | 156 |
| candidates ever model-ready | 152 |
| candidates ever EV-candidate-ready | 116 |
| row-level `model_output_ready=true` | 1089 |
| row-level `ev_after_spread_available=true` | 765 |
| row-level `ev_candidate_ready=true` | 765 |

Interpretation: this is not `NO_SIGNAL`. The model and EV path were visible for most of the run. The blocker is downstream rejection.

## Row-Level Reject Reasons

`skip_reason_primary` distribution:

| Reason | Rows |
|---|---:|
| `imbalance_extreme` | 711 |
| `cutoff_passed` | 201 |
| `book_warming` | 122 |
| `zero_size_plan` | 35 |
| `confidence_below_threshold` | 16 |
| `unclassified` | 7 |
| `ev_negative` | 3 |
| `thin_liquidity` | 1 |

`normalized_skip_reason` distribution:

| Reason | Rows |
|---|---:|
| `delta_extreme` | 711 |
| `time_unsafe` | 201 |
| `empty_book` | 119 |
| `risk_plan_zero` | 35 |
| `confidence_too_low` | 16 |
| `stale_data` | 10 |
| `ev_below_threshold` | 3 |
| `orderbook_unavailable` | 1 |

## Candidate-Level Final State

Final observed reason per candidate:

| Final normalized reason | Candidates |
|---|---:|
| `time_unsafe` | 65 |
| `delta_extreme` | 58 |
| `empty_book` | 29 |
| `stale_data` | 3 |
| `orderbook_unavailable` | 1 |

Candidate-level ever-hit categories:

| Category | Candidates |
|---|---:|
| ever `model_output_ready` | 152 |
| ever `ev_candidate_ready` | 116 |
| ever `delta_extreme` | 116 |
| ever `time_unsafe` | 65 |
| ever empty/unavailable/stale orderbook | 38 |
| ever `risk_plan_zero` / `risk_rejected` | 19 |
| ever `confidence_too_low` | 9 |
| ever `ev_below_threshold` | 3 |

## Blocker Classification

| Classification | Verdict | Evidence |
|---|---|---|
| `NO_SIGNAL` | No | `152 / 156` candidates reached model-ready; `116 / 156` reached EV-candidate-ready. |
| `SIGNAL_REJECTED` | Primary | All `1096` decision rows were skip/reject; no execution rows. |
| `RISK_BLOCKED` | Secondary | `35` rows were `decision_type=risk_rejected` / `risk_plan_zero`; `19` candidates ever hit this state. |
| `EXECUTABLE_BLOCKED` | Secondary | `119` rows `empty_book`, `10` rows `stale_data`, `1` row `orderbook_unavailable`, plus `1` `thin_liquidity` primary reason. |
| `COOLDOWN` | No | `clob_backoff_active=false`, `clob_circuit_open=false`, and `clob_cooldown_seconds_remaining=0.0` for all `1096` rows. |

## Risk Blocks

The explicit risk-reject bucket is small but real:

| Metric | Count |
|---|---:|
| `decision_type=risk_rejected` | 35 rows |
| `normalized_skip_reason=risk_plan_zero` | 35 rows |
| candidates ever risk-plan-zero | 19 |

Representative rows had positive EV and confidence but zero calculated size:

```text
BTC NO conf=0.5697 ev_after=0.2345 calculated_order_size=0.0 micro_position_size=0.050248 min_fillable_size_usd=48.035 risk_plan_zero=unknown
BTC YES conf=0.7108 ev_after=0.3137 calculated_order_size=0.0 micro_position_size=0.050248 min_fillable_size_usd=433.10 risk_plan_zero=unknown
```

Interpretation: these are best labeled `RISK_BLOCKED / ZERO_SIZE_PLAN`, not proven dust-zone executable truth. The field `risk_plan_zero_reason` is `unknown`, so the audit should not claim a precise size-policy root cause without a separate risk observability audit.

## Executable / Liquidity Blocks

Orderbook and executable-state blockers were frequent:

| Field | Dominant values |
|---|---|
| `orderbook_readiness_reason` | `empty_book=980`, blank `116` |
| `liquidity_state` | `HEALTHY=799`, `EMPTY=297` |
| `liquidity_depth_state` | `ACCEPTABLE=420`, `THIN=369`, `STRONG=181`, `UNSTABLE=111`, `UNKNOWN=15` |
| `executable_book_state` | `TRADABLE=1079`, `SPREAD_NORMALIZED=15`, `NONZERO_BOOK=2` |
| `executable_spread_state` | `NORMALIZED=899`, `UNKNOWN=196`, `WIDE=1` |

Important caveat: `orderbook_readiness_reason=empty_book` appears much more often than the final normalized skip reason. It is a persistent degraded context, but the actual final skip is often `delta_extreme` or `time_unsafe`. Therefore the clean classification is:

```text
EXECUTABLE_BLOCKED: secondary / contextual
```

## Cooldowns

Cooldown was not the cause:

| Field | Observed |
|---|---|
| `clob_backoff_active` | `False` for 1096 rows |
| `clob_circuit_open` | `False` for 1096 rows |
| `clob_cooldown_seconds_remaining` | `0.0` for 1096 rows |

## Lifecycle And Market Context

Row-level lifecycle distribution:

| Lifecycle phase | Rows |
|---|---:|
| `ACTIVE_INVENTORY_TRADING` | 778 |
| `FINAL_DERISK` | 162 |
| `PROFIT_MANAGEMENT` | 156 |

Candidate final lifecycle distribution:

| Lifecycle phase | Candidates |
|---|---:|
| `FINAL_DERISK` | 58 |
| `ACTIVE_INVENTORY_TRADING` | 57 |
| `PROFIT_MANAGEMENT` | 41 |

Asset distribution was balanced:

| Asset | Rows | Final candidates |
|---|---:|---:|
| BTC | 548 | 80 |
| ETH | 548 | 76 |

## Answer To Core Question

Was there no opportunity?

```text
No.
```

There were many candidate evaluations, visible model outputs, and EV-ready rows. Some rows even reached positive-EV-looking states before being rejected.

Were opportunities rejected?

```text
Yes.
```

The run is best classified as:

```text
SIGNAL_REJECTED
```

With sublabels:

```text
DELTA_EXTREME_DOMINANT
TIME_UNSAFE_SECONDARY
EMPTY_BOOK_CONTEXTUAL
RISK_PLAN_ZERO_SECONDARY
NO_COOLDOWN_BLOCK
```

## Next Safe Step

Three options:

1. `SAFE_EV_PRESERVATION`: keep farming evidence and wait for a natural post-patch trade open; no changes.
2. `AGGRESSIVE_INFORMATION_DISCOVERY`: run a read-only zero-trade blocker trend audit across recent clean runs to see whether `delta_extreme` and `risk_plan_zero` are persistent or run-specific.
3. `STRUCTURAL_ROOT_CAUSE`: design a future observability-only risk-plan-zero reason field so `risk_plan_zero=unknown` becomes diagnosable without changing risk behavior.

Recommended: option 2 first, because this run has enough decisions to compare blocker distribution without touching runtime behavior.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Replay run: No

Runtime restart: No

Code changes: No

Tests run: none; docs-only/read-only JSONL audit.
