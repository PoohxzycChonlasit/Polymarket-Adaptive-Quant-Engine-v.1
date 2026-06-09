# Legacy Reference Retirement Plan

Date: 2026-06-09

Mode: read-only audit. No code, runtime, strategy, execution, risk-control, staging, commit, or push action was taken.

Target reference:

```text
completed_trades_v1_2.csv
```

## Verdict

**CAUTION**

N70 accumulation can continue because the current command-center report and drift audit can run from `canonical_regime_enriched_trades_v1.csv`. However, active tooling and tests still contain hardcoded legacy completed-trades references. The canonical export already replaces the legacy CSV for ETH YES FC OS N70 governance, but the old references remain as defaults, fallback compatibility, historical generators, test fixtures, and archived provenance.

## Classification Summary

| Classification | Counted Files | Risk |
| --- | ---: | --- |
| ACTIVE_DEPENDENCY | 3 | Medium |
| LEGACY_FALLBACK | 1 | Low |
| HISTORICAL_DOCUMENTATION | 12 | Low |
| SCRATCH_TOOL | 2 | Low |

## Active Dependency Plan

| File | Lines | Why It Still Exists | Canonical Replacement | Migration Complexity | Risk |
| --- | --- | --- | --- | --- | --- |
| `tools/eth_yes_fc_os_command_center.py` | 14 | `DEFAULT_CSV_PATH` still points at `runtime/research_exports/completed_trades_v1_2.csv` for the CSV fallback path and `--csv-path` default. The tool now prefers `DEFAULT_CANONICAL_EXPORT_PATH` unless `--csv-only` is used or canonical validation fails. | `runtime/research_exports/canonical_regime_enriched_trades_v1.csv` already replaces it for current command-center generation. | Low to medium: change fallback default and CLI help, then update tests that assume the legacy filename. | Medium: accidental `--csv-only` or invalid canonical export could silently fall back to stale legacy data. |
| `tools/canonical_trade_table_v1.py` | 22 | This offline historical export generator still defines `CSV_V1_2_NAME` and can produce the completed-trades v1.2 artifact. | Partial: canonical regime export replaces it for ETH YES FC OS governance, but not necessarily for all historical completed-trade table use cases. | Medium: either retain as archived generator, rename as legacy-only, or prove no current docs/tools depend on regenerated v1.2 outputs. | Medium: not part of daily N70 path, but it can regenerate a stale-looking artifact and confuse operators. |
| `tests/test_eth_yes_fc_os_command_center.py` | 65, 104, 175, 208, 244, 279, 297 | Tests create temp files named `completed_trades_v1_2.csv` to exercise legacy CSV, fallback, and stale-CSV behavior. | Canonical export fixtures can replace most happy-path tests; one explicit legacy fallback test can remain if fallback support is intentionally preserved. | Low: rename fixtures and expectations after command-center default is migrated. | Low to medium: tests currently preserve legacy behavior, making accidental retirement harder. |

## Legacy Fallback

| File | Lines | Classification | Notes |
| --- | --- | --- | --- |
| `tools/_drift_audit.py` | 4, 44 | LEGACY_FALLBACK | Default path is canonical export. The legacy reference exists in docstring/error text because the parser still accepts old CSV shape with `regime` instead of `market_regime`. Risk is low when the daily command passes `--path runtime/research_exports/canonical_regime_enriched_trades_v1.csv`. |

Retirement option: keep one explicit fallback note only if legacy CSV compatibility is still required; otherwise remove the fallback language and require `market_regime`.

## Scratch Tools

| File | Lines | Classification | Notes |
| --- | --- | --- | --- |
| `tools/_audit_w21_w22.py` | 7 | SCRATCH_TOOL | Untracked scratch audit tool. Do not stage. Safe to delete only under a dedicated cleanup task. |
| `tools/_delta_audit.py` | 13 | SCRATCH_TOOL | Untracked scratch audit tool. Do not stage. Safe to delete only under a dedicated cleanup task. |

## Historical Documentation Inventory

These are static research/provenance references. They should not block N70 accumulation unless an operator intends to re-run the old instructions.

| File | Lines | Classification | Notes |
| --- | --- | --- | --- |
| `docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md` | 6, 589 | HISTORICAL_DOCUMENTATION | Active-looking campaign doc still names old source provenance. Should be refreshed to canonical export wording during the next scoped docs refresh. |
| `docs/research/CANONICAL_REGIME_EXPORT_SPEC.md` | 47 | HISTORICAL_DOCUMENTATION | Explicitly labels old CSV as prior compact export/reference only. |
| `docs/research/CANONICAL_N61_REPRODUCIBILITY_AUDIT.md` | 19, 151 | HISTORICAL_DOCUMENTATION | Reproducibility provenance for older N61 state. |
| `docs/research/frontiers/SHARE_SIZE_REALITY_REPORT.md` | 5 | HISTORICAL_DOCUMENTATION | Historical all-trades sizing report source. |
| `docs/research/frontiers/N70_READINESS_STATUS.md` | 11, 130, 131, 132, 133, 139 | HISTORICAL_DOCUMENTATION | Current status doc records the caution; not a dependency itself. |
| `docs/research/frontiers/LEGACY_CSV_DEPENDENCY_AUDIT.md` | 15, 23, 73, 102, 112, 145, 175, 187, 224, 225, 238, 241, 273, 310, 327 | HISTORICAL_DOCUMENTATION | Prior dependency audit and provenance. It is allowed to preserve the old reference as audit history. |
| `docs/research/frontiers/EVIDENCE_VELOCITY_ROOT_CAUSE_AUDIT.md` | 7, 427 | HISTORICAL_DOCUMENTATION | Historical root-cause audit source and cutoff note. |
| `docs/research/frontiers/ETH_YES_FC_OS_COMMAND_CENTER_IMPLEMENTATION_PLAN.md` | 39, 50, 77, 90, 180, 296, 337, 347, 357, 443, 450 | HISTORICAL_DOCUMENTATION | Older implementation plan predates canonical regime export integration. Superseded by current tooling and N70 docs. |
| `docs/research/frontiers/DRIFT_AUDIT_MIGRATION_PLAN.md` | 6, 70, 73, 86 | HISTORICAL_DOCUMENTATION | Migration plan explicitly about moving away from old CSV. |
| `docs/research/frontiers/DELTA_EXTREME_PROTECTION_AUDIT.md` | 8 | HISTORICAL_DOCUMENTATION | Historical source provenance. |
| `docs/research/frontiers/COMMAND_CENTER_EXPORT_INTEGRATION_AUDIT.md` | 40, 58, 126, 134, 241, 245, 254, 313, 314 | HISTORICAL_DOCUMENTATION | Prior integration audit; some recommendations are now superseded by canonical export default behavior. |
| `docs/research/REGIME_ENRICHMENT_SOURCE_AUDIT.md` | 56, 157, 159, 270 | HISTORICAL_DOCUMENTATION | Historical source comparison. The current canonical regime export spec supersedes it for N70 operations. |

## Migration Sequence

Recommended future scoped cleanup, if approved:

1. Change `tools/eth_yes_fc_os_command_center.py` fallback default from `completed_trades_v1_2.csv` to canonical export or remove the CSV fallback from routine CLI defaults.
2. Update `tests/test_eth_yes_fc_os_command_center.py` fixtures so canonical export is the happy-path fixture and legacy CSV is only one explicit fallback test.
3. Decide whether `tools/canonical_trade_table_v1.py` remains maintained generator or becomes archived legacy tooling.
4. Refresh `docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md` provenance to canonical export language.
5. Leave historical docs unchanged unless they are converted from provenance to active instructions.

## N70 Impact

| Question | Answer |
| --- | --- |
| Does this block N70 accumulation? | No |
| Does this block a clean READY verdict? | Yes, if strict "no active hardcoded legacy references" is required |
| Does canonical export replace the old CSV for ETH YES FC OS N70 governance? | Yes |
| Is any runtime path affected? | No |
| Is any strategy/risk/execution path affected? | No |

## Final Classification

Current state: **CAUTION**.

Reason: canonical export is operational and preferred, but active tooling still preserves legacy CSV default/fallback behavior.
