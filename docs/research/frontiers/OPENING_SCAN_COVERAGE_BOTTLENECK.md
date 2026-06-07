# OPENING_SCAN Coverage Bottleneck - Research Note

**Status:** `FRONTIER_HYPOTHESIS`
**Date:** 2026-06-06
**Scope:** Docs only. Observability plan only. No runtime, strategy, risk, or execution changes.
**Primary population:** Current run `20260606T041414Z_23488_8bde4b5d`

---

## 1. Problem Definition

OPENING_SCAN is intended to evaluate early 5-minute market opportunities while the market is still inside the first-cycle window. Recent latency and coverage audits show that many candidates become tradable during OPENING_SCAN but do not receive their first directional decision until after OPENING_SCAN has expired.

This creates a research intake bottleneck: the system may be observing valid early-window markets but failing to convert them into canonical watchlist evidence because first decision timing moves them into ACTIVE_INVENTORY_TRADING or later lifecycle phases.

This note defines an observability-only plan for continuously measuring that coverage loss.

---

## 2. Evidence Summary

Recent current-run audits found:

| Metric | Value |
|---|---:|
| OPENING_SCAN-ready candidates | 543 |
| OPENING_SCAN-covered candidates | 280 |
| OPENING_SCAN coverage rate | 51.6% |
| Missed after OPENING_SCAN | 266 |
| Medium-quality missed candidates | 156 |
| High-quality missed candidates | 0 |
| ETH YES misses | 44 |
| ETH YES medium-quality misses | 41 |
| ETH YES coverage | 44% |

Observed OPENING_SCAN window:
- Start: market epoch open / `lifecycle_phase_entered_at`
- End: `lifecycle_phase_exited_at`
- Observed duration: 35 seconds
- Observed cutoff field: `effective_micro_cutoff_seconds = 35`

Key interpretation:
- Market readiness is usually not the blocker. Most miss candidates were discovered, token-ready, orderbook-ready, and tradable during the opening window.
- The bottleneck is first-decision coverage. Many candidates are first evaluated after the lifecycle has moved out of OPENING_SCAN.
- ETH YES is materially affected, which matters because ETH YES FC OS is the active verification watchlist.

---

## 3. Research Intake Loss, Not Proven PnL Loss

This bottleneck should be treated as research intake loss, not proven PnL loss.

Reasons:
- A missed candidate being tradable during OPENING_SCAN does not prove it would have passed all entry, risk, liquidity, and execution gates at the earlier timestamp.
- The miss population contains meaningful signal evidence, but also many post-opening blockers such as `delta_extreme`, confidence thresholds, `clob_empty_response`, risk-plan-zero outcomes, max-trades-per-hour limits, and cutoff blocks.
- The opportunity loss estimate found 156 medium-quality missed candidates, but zero high-quality missed candidates under the conservative classification.
- The audits did not replay alternate scheduling or prove a fill, exit, or outcome path for missed candidates.
- No strategy, risk, execution, filter, or promotion claim is authorized from this evidence alone.

Correct label: `RESEARCH_INTAKE_LOSS_CONFIRMED`.

Incorrect labels:
- `PROVEN_PNL_LOSS`
- `RUNTIME_EDGE_CONFIRMED`
- `FILTER_READY`
- `PROMOTION_READY`

---

## 4. Metrics To Track

The daily coverage monitor should track these fields per run and per UTC date.

| Metric | Definition |
|---|---|
| `opening_ready_count` | Unique candidates with first tradable timestamp inside OPENING_SCAN. |
| `opening_covered_count` | Opening-ready candidates whose first decision occurs inside OPENING_SCAN. |
| `opening_coverage_rate` | `opening_covered_count / opening_ready_count`. |
| `active_only_count` | Opening-ready candidates whose first decision occurs after OPENING_SCAN. |
| `ready_before_15s_decision_after_opening_count` | Candidates tradable by <=15s from market open but first decision after OPENING_SCAN. |
| `ETH_YES_miss_count` | ETH YES candidates tradable during OPENING_SCAN but first decision after OPENING_SCAN. |
| `medium_quality_miss_count` | Missed candidates with good spread, liquidity, quote freshness, model visibility, and positive EV, but with at least one unresolved blocker. |
| `high_quality_miss_count` | Missed candidates that appear to pass spread, liquidity, quote freshness, model visibility, EV, confidence, delta, and risk-plan checks. |

Recommended supporting dimensions:
- asset: BTC / ETH
- side: YES / NO / SKIP / YES_NO passive
- lifecycle phase at first decision
- market regime
- compression score bucket
- skip reason
- candidate block stage
- decision cycle timestamp
- seconds since open at first tradable
- seconds since open at first decision
- readiness-to-decision delay

---

## 5. Required Future Telemetry Fields

Most required fields already exist, but they should be stabilized into an explicit coverage contract.

Minimum required fields:
- `run_id`
- `candidate_id`
- `decision_id`
- `condition_id`
- `epoch_start_ts`
- `asset`
- `side` or intended selected side
- `market_slug`
- `lifecycle_phase`
- `lifecycle_phase_entered_at`
- `lifecycle_phase_exited_at`
- `first_discovered_ts`
- `first_token_ready_ts`
- `orderbook_ready_at`
- `first_tradable_ts`
- `decision_timestamp`
- `seconds_since_open`
- `candidate_block_reason`
- `skip_reason`
- `spread`
- `spread_limit`
- `spread_normalized`
- `liquidity_state`
- `orderbook_snapshot_age_ms_at_decision`
- `quote_lineage_id`
- `quote_capture_ts`
- `market_regime`
- `compression_score`
- `ev_after_spread`
- `confidence`
- `risk_plan_present`
- `risk_plan_zero_reason`

Useful future telemetry additions:
- `opening_scan_candidate_seen`
- `opening_scan_decision_emitted`
- `opening_scan_miss_reason`
- `opening_scan_candidate_rank`
- `opening_scan_candidates_available_in_cycle`
- `opening_scan_candidates_evaluated_in_cycle`
- `opening_scan_queue_depth`
- `opening_scan_scheduler_delay_ms`
- `first_directional_decision_ts`
- `first_directional_decision_lifecycle_phase`
- `counterfactual_opening_ready_quality_bucket`

These additions should remain passive telemetry only.

---

## 6. Suggested Daily Dashboard Fields

Daily dashboard:

| Field | Purpose |
|---|---|
| Date | UTC trading date. |
| Run IDs | Runtime runs contributing data. |
| Opening ready | Count of candidates tradable inside OPENING_SCAN. |
| Opening covered | Count receiving first decision inside OPENING_SCAN. |
| Coverage rate | Core daily bottleneck metric. |
| Active-only misses | Count of opening-ready candidates first decided after OPENING_SCAN. |
| Ready <=15s, decided after opening | Measures fast-readiness loss. |
| ETH YES misses | Direct watchlist intake loss metric. |
| Medium-quality misses | Research-priority miss count. |
| High-quality misses | Potential escalation signal, should remain zero or be manually reviewed. |
| Median readiness-to-decision delay | Timing severity. |
| p90 readiness-to-decision delay | Tail severity. |
| Top miss skip reasons | Explains whether misses are scheduling, data, risk, or signal related. |
| Miss regime mix | COMPRESSION / TREND_DOWN / SIDEWAY / TREND_UP. |
| Miss asset-side mix | BTC/ETH x YES/NO. |
| Canonical watchlist additions | Whether coverage changes correlate with evidence growth. |

Suggested status labels:
- `COVERAGE_HEALTHY`: coverage >= 80% and high-quality misses = 0
- `COVERAGE_WATCH`: coverage 60-80% or ETH YES misses elevated
- `COVERAGE_BOTTLENECK`: coverage < 60% or medium-quality misses elevated
- `COVERAGE_REGRESSED`: coverage falling day over day with rising ETH YES misses

---

## 7. Guardrails

This frontier does not authorize runtime behavior changes.

Hard guardrails:
- No strategy changes.
- No execution changes.
- No risk changes.
- No sizing changes.
- No filter activation.
- No Telegram spam.
- No live behavior changes.
- No promotion claims.
- No profitability claims.
- No automatic scheduling optimization.
- No change to OPENING_SCAN, ACTIVE_INVENTORY_TRADING, or lifecycle policy.

Allowed future work:
- Docs-only research notes.
- Offline analyzer improvements.
- Passive JSONL telemetry.
- Daily dashboard reporting.
- Paper-only replay design.
- Scheduling simulation design.

---

## 8. Future Research Path

Recommended path:

1. Observability first

   Stabilize the daily coverage metrics and add passive fields only if existing fields cannot reconstruct coverage reliably.

2. Paper replay second

   Replay the missed population without changing runtime behavior. Estimate whether earlier OPENING_SCAN decisions would have changed eligibility, risk acceptance, fills, exits, or outcomes.

3. Scheduling simulation third

   Simulate alternate opening-cycle scheduling against recorded candidates. Compare coverage gain, duplicate risk, queue pressure, decision latency, and blocker composition.

4. Runtime optimization only after proof

   Runtime scheduling changes should require evidence that:
   - coverage improves materially,
   - canonical watchlist evidence growth improves,
   - blocker mix does not simply move failed candidates earlier,
   - no risk, execution, or stale-data safeguards are weakened,
   - targeted tests prove fail-soft behavior and no live behavior change unless explicitly approved.

---

## Governor Verdict

`OPENING_SCAN_COVERAGE_BOTTLENECK_CONFIRMED`

The current evidence supports a continuous observability monitor and offline replay/simulation research. It does not support strategy, risk, execution, filter, or promotion changes.
