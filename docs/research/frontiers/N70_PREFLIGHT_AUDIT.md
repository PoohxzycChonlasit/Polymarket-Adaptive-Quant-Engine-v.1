# N70 Preflight Audit

Date: 2026-06-08

Goal: define every dependency required when ETH YES FC OS reaches canonical n=70. This is a preflight only; it does not execute the full N70 package.

## Required Commands

Run from repository root:

```powershell
py -3.11 tools/canonical_regime_export.py
py -3.11 tools/eth_yes_fc_os_command_center.py
py -3.11 tools/_drift_audit.py --path runtime/research_exports/canonical_regime_enriched_trades_v1.csv
py -3.11 -m pytest -q tests/test_drift_audit.py tests/test_canonical_regime_export.py tests/test_eth_yes_fc_os_command_center.py
py -3.11 -m py_compile tools/_drift_audit.py tools/canonical_regime_export.py tools/eth_yes_fc_os_command_center.py
git diff --check
git status --short
```

Do not run replay, paper launch, live mode, S3 promotion, or runtime mutation as part of N70 preflight.

## Required Source Files

| Source | Required For | Freshness Rule |
| --- | --- | --- |
| `runtime/quant_data/trade_journal/*.jsonl` | Canonical trade truth | Latest complete files must be readable |
| `runtime/quant_data/decision_log/*.jsonl` | Regime enrichment truth | Latest decision timestamp should not lag latest trade close |
| `runtime/research_exports/canonical_regime_enriched_trades_v1.csv` | N70 analysis input | Must be regenerated at review time |
| `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json` | Export validation | `validation.status=PASS` |
| `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md` | Campaign dashboard | Should match export n |
| `docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md` | Drift context | Should be regenerated or reviewed against latest export |
| `docs/research/N70_EXECUTION_PACKAGE.md` | N70 review workflow | Must remain the governing checklist |

## Expected Outputs

| Output | Expected Condition |
| --- | --- |
| Canonical export CSV | n >= 70, duplicate count reconciled |
| Export metadata JSON | PASS, freshness FRESH or explained |
| Export summary MD | Human-readable validation summary |
| Command center markdown | Current n, WR, PF, nc_PF, velocity, kill criteria |
| Drift audit stdout or archived doc | Rolling WR/PF/nc_PF, regime runs, phase segmentation |
| Governor review notes | PASS / CAUTION / FAIL classification |

## Stale Or Missing Input Checks

- If trade journal latest close is newer than decision log latest scan, flag stale regime enrichment.
- If `UNKNOWN` regime count is non-zero, classify whether each row is join failure, pre-patch evidence, or malformed input.
- If canonical n differs between command center and export metadata, stop and reconcile before N70 review.
- If generated exports are present under `runtime/research_exports/`, keep them uncommitted unless explicitly approved.
- If scratch tools under `tools/_audit*.py`, `tools/_delta*.py`, or `tools/_opp_capture_audit.py` appear, exclude them from commits.

## Blockers

| Blocker | Action |
| --- | --- |
| Canonical n < 70 | Continue evidence accumulation |
| Export validation FAIL | Fix offline export tooling only after explicit implementation scope |
| Regime join rate < 95% | Run regime enrichment reconciliation audit |
| Duplicate count unexplained | Run canonical count reconciliation |
| Drift audit cannot run | Treat N70 review as blocked |
| Runtime/code/config changes mixed into docs commit | Stop and split scope |

## Estimated Runtime

| Step | Estimate |
| --- | ---: |
| Canonical export generation | < 1 minute |
| Command center generation | < 1 minute |
| Drift audit | < 1 minute |
| Targeted tests | 1-3 minutes |
| Manual governor review | 15-30 minutes |

## Test Requirements

Mandatory at N70:

- `tests/test_drift_audit.py`
- `tests/test_canonical_regime_export.py`
- `tests/test_eth_yes_fc_os_command_center.py`
- Python compile for the three offline tools.

Optional if tooling changes before N70:

- Additional fixture tests for duplicate tie-breaks.
- Additional fixture tests for blank `trade_result` with valid `outcome_win_loss`.
- Markdown link/reference check for N70 docs.

## Governor Checklist

At n=70, compare against the current n=62 baseline:

| Metric | Baseline |
| --- | ---: |
| WR | 56.5% |
| PF | 1.980 |
| nc_PF | 2.367 |
| p-value | 0.187 |
| COMPRESSION share | 33.9% historical, 0% W23 |
| TREND_DOWN share | 29.0% |
| SIDEWAY share | 25.8% |
| TREND_UP share | 11.3% |
| 7d velocity | 0.29/day |
| 14d velocity | 1.21/day |

Required questions:

1. Did WR remain above the watch floor?
2. Did PF remain above 1.5?
3. Did nc_PF remain above 1.0 and preferably above 1.5?
4. Did new opportunities come from TREND_DOWN/SIDEWAY or COMPRESSION recovery?
5. Did TREND_UP drag expand?
6. Did W23/W24 velocity recover without changing runtime policy?
7. Are any kill criteria newly active?

Governor verdict: **PREFLIGHT_READY, N70_TRIGGER_INACTIVE**.
