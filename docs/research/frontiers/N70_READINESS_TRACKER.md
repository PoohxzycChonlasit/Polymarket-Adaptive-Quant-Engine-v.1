# N70 Readiness Tracker

Date: 2026-06-10

Mode: evidence accumulation only. No strategy, risk, execution, sizing, or live change is authorized by this tracker.

## N70 Milestone Update

The real N70 event was reached and frozen on 2026-06-10.

| Field | Value |
| --- | ---: |
| Current canonical n | 70 |
| Remaining to n=70 | 0 |
| Remaining to n=100 | 30 |
| Raw filtered rows | 71 |
| Duplicate rows removed | 1 |
| WR | 57.1% |
| PF | 2.006 |
| nc_PF | 3.865 |
| N62-N70 block | 5W / 4L, WR 55.6%, PF 1.803, +$0.018609 |
| N70 trigger | ACTIVE AND COMPLETED |
| Next formal trigger | n=80 |

```text
Rows 1-70   = discovery / retrospective selected-slice evidence
Rows 71-100 = forward validation block
```

Governor verdict: `CONTINUE_ACCUMULATION`.

This milestone update supersedes the pre-N70 current-state fields retained
below for historical context.

## Current State

Source stack:

- `runtime/research_exports/canonical_regime_enriched_trades_v1.csv`
- `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json`
- `tools/_drift_audit.py --path runtime/research_exports/canonical_regime_enriched_trades_v1.csv`
- `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md`
- `docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md`

| Field | Value | Notes |
| --- | ---: | --- |
| Current canonical n | 70 | Latest export validation: 71 raw filtered rows, 1 duplicate removed |
| Remaining to n=70 | 0 | N70 package completed |
| Wins / Losses | 40 / 30 | Outcome truth from canonical regime export |
| WR | 57.1% | Above 52% watch threshold |
| PF | 2.006 | Above 1.5 watch threshold |
| nc_PF | 3.865 | Final rolling non-COMPRESSION PF from drift audit |
| p-value | 0.141 | One-sided binomial, p=0.5 baseline |
| 7d velocity | 1.43/day | 10 qualifying trades in latest 7 calendar days |
| 14d velocity | 1.57/day | 22 qualifying trades in latest 14 calendar days |
| ETA to n=70, 7d rate | 0 days | N70 reached |
| ETA to n=70, 14d rate | 0 days | N70 reached |
| Latest qualifying trade | 2026-06-10 | SIDEWAY TP |
| Days since last qualifying trade | 0 | Measured to 2026-06-10 |

## Regime Mix

| Regime | n | Share | WR | PF | Net PnL |
| --- | ---: | ---: | ---: | ---: | ---: |
| COMPRESSION | 21 | 30.0% | 61.9% | 3.372 | +$0.13007 |
| TREND_DOWN | 19 | 27.1% | 57.9% | 2.209 | +$0.06422 |
| SIDEWAY | 18 | 25.7% | 55.6% | 1.150 | +$0.01013 |
| TREND_UP | 12 | 17.1% | 50.0% | 1.292 | +$0.01135 |

COMPRESSION share in the canonical sequence is 30.0%, but W23/W24 contribution remains zero. The current campaign is therefore still dependent on non-COMPRESSION continuation until COMPRESSION returns.

## TREND_DOWN Hold > 15 Status

TREND_DOWN is viable historically but not stable enough for promotion logic:

- Canonical TREND_DOWN: n=19, WR 57.9%, PF 2.209.
- W23 TREND_DOWN fast-resolution audit: short holds in W23 are explained by a small effective episode count, not by a confirmed strategy failure.
- Governance status: monitoring hypothesis only. No runtime filter, threshold, or policy change.

## Kill Criteria Status

| Criterion | Status | Evidence |
| --- | --- | --- |
| WR below promotion floor | Clear | Full-cell WR 57.1% |
| PF below 1.5 at sufficient n | Clear | Full-cell PF 2.006 |
| nc_PF deterioration | Clear | Final nc_PF 3.865; historical trough was 0.596 |
| COMPRESSION disappearance | Watch | W23/W24 COMPRESSION share remains 0% |
| TREND_UP expansion | Watch | TREND_UP n=12; sample-doubling tripwire at n>=14 |
| Evidence velocity collapse | Clear | 7d velocity 1.43/day |

No kill criterion is active. Watch criteria remain active for COMPRESSION absence and TREND_UP sample expansion.

## N70 Trigger Rule

Trigger the N70 execution package only when:

1. Canonical n >= 70 from the canonical regime export.
2. Export validation status is PASS.
3. Duplicate removal count is reconciled.
4. Regime join rate is >= 95%.
5. `UNKNOWN` regime rate is reviewed and explained.
6. Drift audit runs successfully against the same export.
7. No runtime, strategy, risk, execution, or config mutation is bundled with the review.

Current trigger: **COMPLETED**.

Governor verdict: **CONTINUE_ACCUMULATION**. N70 is complete; the next formal
snapshot is n=80 and N71 begins the forward validation block.
