# N70 Readiness Tracker

Date: 2026-06-08

Mode: evidence accumulation only. No strategy, risk, execution, sizing, or live change is authorized by this tracker.

## Current State

Source stack:

- `runtime/research_exports/canonical_regime_enriched_trades_v1.csv`
- `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json`
- `tools/_drift_audit.py --path runtime/research_exports/canonical_regime_enriched_trades_v1.csv`
- `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md`
- `docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md`

| Field | Value | Notes |
| --- | ---: | --- |
| Current canonical n | 62 | Latest export validation: 63 raw filtered rows, 1 duplicate removed |
| Remaining to n=70 | 8 | N70 package remains inactive |
| Wins / Losses | 35 / 27 | Outcome truth includes one retained loss row with blank `trade_result` but `outcome_win_loss=LOSS` |
| WR | 56.5% | Above 52% watch threshold |
| PF | 1.980 | Above 1.5 watch threshold |
| nc_PF | 2.367 | Final rolling non-COMPRESSION PF from drift audit |
| p-value | 0.187 | One-sided binomial, p=0.5 baseline |
| 7d velocity | 0.29/day | 2 qualifying trades in latest 7 calendar days |
| 14d velocity | 1.21/day | 17 qualifying trades in latest 14 calendar days |
| ETA to n=70, 7d rate | ~28 days | Conservative current-velocity estimate |
| ETA to n=70, 14d rate | ~7 days | Recent-window estimate |
| Latest qualifying trade | 2026-06-07 | SIDEWAY SL, hold 24s |
| Days since last qualifying trade | 1 | Measured to 2026-06-08 |

## Regime Mix

| Regime | n | Share | WR | PF | Net PnL |
| --- | ---: | ---: | ---: | ---: | ---: |
| COMPRESSION | 21 | 33.9% | 61.9% | 3.372 | +$0.13007 |
| TREND_DOWN | 18 | 29.0% | 55.6% | 2.111 | +$0.05903 |
| SIDEWAY | 16 | 25.8% | 56.2% | 1.228 | +$0.01328 |
| TREND_UP | 7 | 11.3% | 42.9% | 0.661 | -$0.01014 |

COMPRESSION share in the canonical sequence is 33.9%, but W23 contribution is zero. The current campaign is therefore still dependent on non-COMPRESSION continuation until COMPRESSION returns.

## TREND_DOWN Hold > 15 Status

TREND_DOWN is viable historically but not stable enough for promotion logic:

- Canonical TREND_DOWN: n=18, WR 55.6%, PF 2.111.
- W23 TREND_DOWN fast-resolution audit: short holds in W23 are explained by a small effective episode count, not by a confirmed strategy failure.
- Governance status: monitoring hypothesis only. No runtime filter, threshold, or policy change.

## Kill Criteria Status

| Criterion | Status | Evidence |
| --- | --- | --- |
| WR below promotion floor | Clear | Full-cell WR 56.5% |
| PF below 1.5 at sufficient n | Clear | Full-cell PF 1.980 |
| nc_PF deterioration | Watch | Final nc_PF 2.367, but historical trough was 0.596 |
| COMPRESSION disappearance | Watch | W23 COMPRESSION share remains 0% |
| TREND_UP drag | Watch | TREND_UP PF 0.661 |
| Evidence velocity collapse | Watch | 7d velocity 0.29/day |

No kill criterion is active. Watch criteria remain active for COMPRESSION absence, low velocity, and non-COMPRESSION stability.

## N70 Trigger Rule

Trigger the N70 execution package only when:

1. Canonical n >= 70 from the canonical regime export.
2. Export validation status is PASS.
3. Duplicate removal count is reconciled.
4. Regime join rate is >= 95%.
5. `UNKNOWN` regime rate is reviewed and explained.
6. Drift audit runs successfully against the same export.
7. No runtime, strategy, risk, execution, or config mutation is bundled with the review.

Current trigger: **INACTIVE**.

Governor verdict: **RETURN_TO_EVIDENCE_ACCUMULATION_MODE**. N70 is close but not active.
