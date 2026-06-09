# N70 Readiness Status

Date: 2026-06-09

Mode: read-only readiness audit. No runtime, strategy, risk, execution, config, or live behavior changes were made.

## Verdict

**CAUTION**

N70 accumulation mode is operationally usable, but not perfectly clean. The canonical export, command center, drift audit, and N70 tracker are healthy enough for continued accumulation. The caution is dependency hygiene: active tooling still contains a legacy `completed_trades_v1_2.csv` fallback/default path, and one active drift document still carries old completed-trades provenance.

This is not a runtime blocker. It is a governance hygiene item to clear before treating the N70 package as fully dependency-clean.

## Status Summary

| Component | Status | Evidence |
| --- | --- | --- |
| Canonical export | HEALTHY | Metadata validation `PASS`; canonical n=62; raw filtered rows=63; duplicate rows removed=1 |
| Export freshness | HEALTHY | Metadata status `FRESH`; source lag 0.0s |
| Regime join | HEALTHY | Regime join rate 100%; unknown regime rate 0.0% |
| Command center | HEALTHY_WITH_NOTES | Generated from `canonical_regime_enriched_trades_v1.csv`; n=62; WR=56.5%; PF=1.980 |
| Drift audit | HEALTHY | Runs successfully against canonical export; final rolling WR=60.0%, PF=2.159, nc_PF=2.367 |
| N70 tracker | HEALTHY | Tracks n=62, remaining=8, trigger inactive |
| Stale dependencies | CAUTION | Legacy completed-trades references remain in active tooling/docs |
| N70 trigger | INACTIVE | canonical n < 70 |

## Canonical Export Check

Source: `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json`

| Field | Value |
| --- | ---: |
| Export generated | 2026-06-08T12:26:57Z |
| Validation status | PASS |
| Canonical n | 62 |
| Raw filtered rows | 63 |
| Duplicate rows removed | 1 |
| Regime join rate | 1.0 |
| Unknown regime count | 0 |
| Unknown regime rate | 0.0 |
| Freshness status | FRESH |
| Source lag seconds | 0.0 |

Assessment: **HEALTHY**.

## Command Center Check

Source: `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md`

| Field | Value |
| --- | ---: |
| Generated | 2026-06-08T12:27:36Z |
| Source evidence | `canonical_export:runtime/research_exports/canonical_regime_enriched_trades_v1.csv` |
| Canonical n | 62 |
| Remaining to N70 | 8 |
| WR | 56.5% |
| PF | 1.980 |
| p-value | 0.187 |
| nc_PF | 2.367 |
| nc_PF tripwire | CLEAR |
| Export validation | VALID |
| Source freshness | FRESH/RECENT |
| Unknown regime rate | 0.0% |

Notes:

- Command center is reading the canonical regime export in the current generated report.
- The report still contains manual-required market-structure fields.
- The report labels JSONL writer as `BLOCKED`; this appears to be an integrity-status input label, not evidence that the canonical export failed.

Assessment: **HEALTHY_WITH_NOTES**.

## Drift Audit Check

Command:

```powershell
py -3.11 tools/_drift_audit.py --path runtime/research_exports/canonical_regime_enriched_trades_v1.csv
```

Result: command completed successfully.

Key outputs:

| Metric | Value |
| --- | ---: |
| Full cell n | 62 |
| Full WR | 56.5% |
| Full PF | 1.980 |
| Rolling WR final | 60.0% |
| Rolling PF final | 2.159 |
| nc_PF final | 2.367 |
| nc_PF consecutive below 1.0 | 0 |
| COMPRESSION final rolling share | 25.0% |
| W23 contribution | n=2, WR=50.0%, PF=2.357 |

Assessment: **HEALTHY**.

## N70 Tracker Check

Source: `docs/research/frontiers/N70_READINESS_TRACKER.md`

| Field | Value |
| --- | ---: |
| Current canonical n | 62 |
| Remaining to n=70 | 8 |
| WR | 56.5% |
| PF | 1.980 |
| nc_PF | 2.367 |
| p-value | 0.187 |
| N70 trigger | INACTIVE |

Assessment: **HEALTHY**.

## Stale Dependency Check

Search scope:

```text
tools
docs/research
excluding scratch tools: tools/_audit*.py, tools/_delta*.py, tools/_opp_capture_audit.py
```

Findings:

| Location | Finding | Status |
| --- | --- | --- |
| `tools/eth_yes_fc_os_command_center.py` | `DEFAULT_CSV_PATH = runtime/research_exports/completed_trades_v1_2.csv` | CAUTION |
| `tools/_drift_audit.py` | Legacy fallback text supports `completed_trades_v1_2.csv` when `regime` column is present | CAUTION |
| `tools/canonical_trade_table_v1.py` | Generates `completed_trades_v1_2.csv` artifacts | ACCEPTABLE HISTORICAL GENERATOR |
| `docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md` | Provenance still names `completed_trades_v1_2.csv` | CAUTION |
| Historical research docs | Multiple completed-trades references | ACCEPTABLE IF STATIC PROVENANCE |

Interpretation:

- The current command-center output is sourced from `canonical_regime_enriched_trades_v1.csv`, so the active report is healthy.
- The code still exposes the old completed-trades CSV as a default/fallback path. That violates a strict reading of "no hardcoded completed_trades_v1_2.csv dependencies remain in active tooling."
- Historical docs can retain provenance references, but active daily workflow docs should prefer canonical regime export naming.

Assessment: **CAUTION**.

## Readiness Gates

| Gate | Status |
| --- | --- |
| Canonical export PASS | PASS |
| Export fresh | PASS |
| Regime join >=95% | PASS |
| Unknown regime reviewed | PASS |
| Command center generated from canonical export | PASS |
| Drift audit runs against canonical export | PASS |
| N70 tracker current with n=62 | PASS |
| No active legacy hardcoded dependency | CAUTION |
| N70 trigger active | NO |

## Recommended Action

Continue accumulation mode.

Before declaring full READY, clear or explicitly accept the legacy completed-trades fallback/default in active tooling and refresh the active drift-audit provenance doc to canonical export language.

No strategy, risk, execution, runtime, or live change is required.
