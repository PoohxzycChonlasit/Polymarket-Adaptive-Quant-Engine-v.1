# Evidence Quality Audit

Date: 2026-06-09

Mode: READ ONLY. No runtime, strategy, risk, execution, sizing, config, wallet, or live behavior change is authorized by this audit.

Role: adversarial quant research governor.

Scope constraint: this audit ignores documentation quality, architecture quality, and governance quality. It evaluates only whether the current evidence proves what the project appears to believe.

## Executive Finding

The current evidence proves that the canonical ETH YES FIRST_CYCLE OPENING_SCAN hold > 15s cell has a positive historical paper sample at `canonical_n = 67`, with `WR = 56.7%`, `PF = 1.993`, `38 wins / 29 losses`, `net PnL = +$0.208317`, export validation `PASS`, regime join rate `100%`, and duplicate removal reconciled as `1`.

It does not prove that the edge is statistically significant, persistent through N100, regime-stable, selection-bias-free, executable at larger size, or ready for live trading. At the current win rate, the command center reports `n_required = 143` for `p < 0.05`, so N100 is not guaranteed to satisfy the significance gate unless the win rate improves.

Final classification: `PARTIALLY_PROVEN`.

## Source Evidence Reviewed

- `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json`
- `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md`
- `docs/research/frontiers/N70_READINESS_TRACKER.md`
- `docs/research/EXECUTIVE_N70_WAITING_STATE_REPORT.md`
- `docs/research/watchlists/ETH_YES_FC_OS.md`
- `docs/research/verification_tracker.md`
- `docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md`
- `docs/research/CANONICAL_N61_REPRODUCIBILITY_AUDIT.md`
- `docs/research/REGIME_ENRICHMENT_SOURCE_AUDIT.md`
- `runtime/research_state/latest_research_state.md`

## Classification Summary

| Claim | Classification | Evidence quality |
| --- | --- | --- |
| Canonical count is currently 67 | Proven | Export metadata says `canonical_n=67`, raw filtered rows 68, duplicate rows removed 1, validation PASS. |
| Current historical paper sample is profitable | Proven | WR 56.7%, PF 1.993, net +$0.208317 on 67 canonical outcomes. |
| Regime enrichment is complete for current export | Proven | Regime join rate 100%, unknown regime rate 0.0%. |
| The cell is a strong candidate worth continued paper accumulation | Partially Proven | PF/WR positive, robustness at n=60 supportive, but p-value and N100 gate remain open. |
| Edge is statistically significant | Unproven | p-value 0.164; current WR scenario requires n=143 for p<0.05. |
| N100 will be sufficient if reached | Unproven | N100 may still miss p<0.05 at current WR; regime composition can change before then. |
| Regime robustness is proven | Partially Proven | COMPRESSION/TREND_DOWN strong; SIDEWAY marginal; TREND_UP small and unstable. |
| Path quality is proven for the full population | Unproven | MFE/MAE path truth covers 28/60 in the older snapshot, not the full n=67 population. |
| Selection bias is ruled out | Unknown | This audit did not find a complete hypothesis ledger or abandoned-hypothesis denominator. |
| Live/executable edge is proven | Unproven | All evidence is paper/offline; live fill/cancel/reconcile remains unproven by project status. |

## What Is Actually Proven

1. The current canonical export is internally valid for the ETH YES FC OS cell:
   `canonical_n=67`, `direct_strong_rate=1.0`, `regime_join_rate=1.0`, `unknown_regime_rate=0.0`, `freshness=FRESH`.

2. The included paper outcomes are positive on headline metrics:
   `38W / 29L`, `WR=56.7%`, `PF=1.993`, `gross wins=+0.418174`, `gross losses=-0.209857`, `net=+0.208317`, median PnL positive.

3. The original n=61 count contract is reproducible from raw `trade_journal` using the runless logical opportunity key:
   `condition_id | epoch_start_ts | asset | side | candidate_id`.

4. The current regime labels are not UNKNOWN-filled placeholders. The current export joins regime at 100%.

5. The historical n=60/n=61 robustness layer is supportive but older:
   top-5 removal PF remained above 1.0, LODO minimum PF was above 1.0, and bootstrap PF > 1.0 rate was reported as 99.5%.

## What Is Believed But Not Proven

1. The project appears to treat the cell as a robust edge candidate. That is plausible, but not proven at statistical significance.

2. The project appears to treat the post-n60/n61 continuation as consistent. The n=67 metrics support this directionally, but the newest six or seven trades do not yet constitute a decisive forward-validation block.

3. The project appears to treat path evidence as confirming entry/exit quality. That is only partially supported because the MFE/MAE audit covers 28/60 matched trades and does not yet cover the full current population.

4. The project appears to treat regime behavior as monitorable. That is true for labels, but not the same as proving regime-sufficient edge. SIDEWAY is near breakeven and TREND_UP remains small and unstable.

5. The project appears to treat N100 as the next decisive milestone. N100 is useful, but at current WR it may still fail the p-value gate.

## Load-Bearing Metrics

These metrics materially support or threaten the edge claim:

| Metric | Why load-bearing |
| --- | --- |
| Canonical n | Determines whether any statistical or milestone claim is valid. |
| WR | Directly drives the p-value and promotion gate. |
| PF | Best single profitability summary; sensitive to payoff asymmetry and loss tail. |
| Gross win / gross loss | Needed to check whether PF is driven by a few large wins. |
| Ex-top-5 PF | Tests whether the edge collapses after removing outlier winners. |
| p-value / n_required | Prevents mistaking positive sample performance for significance. |
| Regime n / regime PF | Reveals whether the edge survives outside COMPRESSION/TREND_DOWN. |
| New-block WR/PF | Best guard against old evidence masking current deterioration. |
| Duplicate count and key contract | Prevents repeated runtime rows from inflating n. |
| Path truth match rate | Determines whether MFE/MAE conclusions are representative. |

## Decorative Or Secondary Metrics

These are useful context but cannot carry the edge claim alone:

| Metric | Reason |
| --- | --- |
| ETA to N70/N100 | Operational planning only; not evidence of edge. |
| Evidence velocity | Useful for accumulation planning, not proof of profitability. |
| Calendar weeks | Coverage gate, not edge proof unless paired with performance by week. |
| nc_PF current value alone | Useful warning metric, but can hide the prior 14-point negative nc_PF zone. |
| Median PnL | Supportive, but too small in dollar terms to replace PF/gross loss checks. |
| Runtime health/tool pass status | Necessary for trust in outputs, but not proof of quant edge. |
| Command-center status labels | Derived summaries; must remain subordinate to raw counts/outcomes. |

## Conclusions Depending On Strong Evidence

1. The canonical current sample is positive.
2. The current enriched export is usable for N70 tracking.
3. The edge candidate has not hit the existing kill criteria.
4. The project should continue paper evidence accumulation rather than promote, mutate runtime policy, or stop purely on current evidence.

## Conclusions Depending On Weak Evidence

1. The edge is structurally persistent.
2. The edge will remain positive in a COMPRESSION-absent environment.
3. SIDEWAY is meaningfully positive rather than noise around breakeven.
4. TREND_UP has recovered from earlier negative readings.
5. MFE/MAE path quality generalizes to all current and future qualifying trades.
6. N100 will be statistically decisive.
7. Selection bias is not materially explaining the cell.

## Evidence Gaps Before N100

1. Full forward block review from n=61 to n=70, then n=70 to n=80/n=90/n=100.
2. Updated robustness tests on the current n=67 and future n=70/n=100 populations, not only the older n=60 set.
3. Updated ex-top-1/top-3/top-5 PF after each milestone.
4. Regime-specific minimum samples, especially SIDEWAY and TREND_UP.
5. Direct path truth coverage for future trades that is materially better than 47%.
6. A written denominator of explored, abandoned, merged, or de-emphasized hypotheses to assess selection bias.
7. A clear rule for what happens if N100 has WR/PF pass but p-value remains above 0.05.
8. Evidence that current PF is not concentrated in COMPRESSION and TREND_DOWN while new evidence accumulates mostly elsewhere.
9. Explicit confirmation that new trades are not only surviving because of one or two high-PnL winners.
10. Forward validation of current export tooling at the exact N70/N100 snapshots.

## What Evidence Would Change My Mind

Toward stronger confidence:

1. N100 reaches `WR > 52%`, `PF > 1.5`, `p < 0.05`, and ex-top-5 PF remains above 1.0.
2. New-block metrics after n=61 remain positive without relying on one outlier winner.
3. SIDEWAY and TREND_UP either accumulate enough n to prove they are not dangerous, or their drag remains small while TREND_DOWN carries non-COMPRESSION edge.
4. Path truth coverage rises enough that MFE/MAE is no longer based on a minority matched sample.
5. A selection-bias audit proves the cell survived a pre-declared or at least fully inventoried hypothesis process.

Toward weaker confidence:

1. Cumulative PF falls below 1.5 before or at n=80.
2. New-block PF falls below 1.0 over any meaningful 9- to 20-trade milestone block.
3. nc_PF spends another sustained period below 1.0 during COMPRESSION absence.
4. TREND_UP reaches the monitoring threshold and remains below breakeven.
5. Ex-top-5 PF falls below 1.0 at N100.
6. N100 arrives with p-value still materially above 0.05 and no predeclared rationale for accepting that.

## Final Verdict

`PARTIALLY_PROVEN__CONTINUE_ACCUMULATION__DO_NOT_PROMOTE`

The current evidence is good enough to continue toward N70/N100 under paper-only accumulation. It is not good enough to claim the edge is statistically proven, regime-stable, selection-bias-free, or executable/live-ready.

## Exactly Three Future Options

### Option 1 - Safe EV Preservation

Thesis: Continue accumulation unchanged and treat the current cell as a candidate, not a proven edge.

Likely outcome: N70 will probably be reached soon, but N70 should only update the evidence state. It should not change runtime, strategy, execution, or risk.

Hidden risk: old positive evidence can mask new-block deterioration.

Recommended action: at N70, require cumulative metrics plus n=62-70 block WR/PF, regime mix, ex-top concentration, and p-value projection.

### Option 2 - Aggressive Information Discovery

Thesis: Use N70/N80/N90 as forward-validation checkpoints, not ceremonial milestones.

Likely outcome: the project learns whether the edge is still alive in W23/W24 conditions instead of relying on the stronger W21/W22 sequence.

Hidden risk: small new blocks can overreact to noise.

Recommended action: write each milestone as `old evidence vs new evidence`, with explicit new-block PF, regime composition, and concentration checks.

### Option 3 - Structural / Root-Cause Path

Thesis: The largest hidden evidence risk is not current PF; it is whether the surviving cell is a selected survivor from a larger hypothesis search.

Likely outcome: a selection-bias audit may downgrade confidence even if WR/PF remain positive.

Hidden risk: without a hypothesis denominator, the project may mistake the best surviving slice for a generalizable edge.

Recommended action: run `SELECTION_BIAS_AUDIT.md` before treating N100 as decisive.
