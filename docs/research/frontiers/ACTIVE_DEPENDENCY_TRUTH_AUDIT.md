# Active Dependency Truth Audit

Date: 2026-06-09

Mode: read-only audit. No code, tests, runtime, strategy, execution, risk controls, staging, commit, or push action was taken.

Focus scope:

- `tools/eth_yes_fc_os_command_center.py`
- `tools/canonical_trade_table_v1.py`
- `tests/test_eth_yes_fc_os_command_center.py`

Target reference:

```text
completed_trades_v1_2.csv
```

## Verdict

**CAUTION**

No reference is runtime-required. The remaining references are research-tool fallback/default behavior, one historical research export generator output name, and test fixture filenames. Canonical regime export already replaces `completed_trades_v1_2.csv` for current ETH YES FC OS command-center/N70 governance, but not every broader completed-trade-table use case is proven replaceable.

## Reference Inventory

| # | File | Function | Line | Classification | Why It Still Exists | What Breaks If Removed | Canonical Export Provides Same Data? | Difficulty |
| ---: | --- | --- | ---: | --- | --- | --- | --- | --- |
| 1 | `tools/eth_yes_fc_os_command_center.py` | `<module>` | 14 | FALLBACK_COMPATIBILITY_ONLY | `DEFAULT_CSV_PATH` is still the default fallback CSV path and `--csv-path` default. The tool prefers `DEFAULT_CANONICAL_EXPORT_PATH` when not in `--csv-only` mode. | Removing it without replacing the default breaks function defaults, CLI parser default, `--csv-only`, and fallback behavior when canonical export is missing/invalid and trade journal is unavailable. | Yes for current ETH YES FC OS N70 governance. The canonical export is already the preferred source in normal command-center generation. | LOW |
| 2 | `tools/canonical_trade_table_v1.py` | `<module>` | 22 | ACTIVE_RESEARCH_REQUIRED | `CSV_V1_2_NAME` defines the output artifact name for the completed-trade table V1.2 lifecycle-truth export. This tool is offline research tooling, not runtime. | Removing it without replacing the artifact contract breaks V1.2 export generation and any historical/manual workflows expecting that completed-trades artifact. | Partially. Canonical regime export replaces it for ETH YES FC OS governance, but V1.2 also carries broader completed-trade-table fields and summaries not proven identical in the canonical regime export. | MEDIUM |
| 3 | `tests/test_eth_yes_fc_os_command_center.py` | `test_generates_four_panel_report_and_deduplicates_canonical_opportunities` | 65 | TEST_FIXTURE_ONLY | Temp filename exercises old-style CSV row input and canonical dedupe behavior. | Only this test fixture path/name breaks if removed without renaming; production behavior does not depend on the literal temp filename. | Yes for current command-center happy path, but this test is specifically exercising CSV input compatibility. | LOW |
| 4 | `tests/test_eth_yes_fc_os_command_center.py` | `test_csv_only_mode_marks_decision_metrics_manual` | 104 | TEST_FIXTURE_ONLY | Temp filename exercises CSV-only/manual-decision-metric behavior. | The test fixture breaks if removed without renaming; CSV-only compatibility would still need a fixture if retained. | Mostly. Canonical export covers normal governance, but not the explicit `csv_path` compatibility behavior under test. | LOW |
| 5 | `tests/test_eth_yes_fc_os_command_center.py` | `test_canonical_export_flag_accepted_and_used_when_valid` | 175 | TEST_FIXTURE_ONLY | Temp legacy CSV path exists as fallback while the valid canonical export is expected to win. | The test setup breaks if removed without replacing the fallback fixture path. The asserted canonical-export behavior does not require this exact filename. | Yes. This test proves canonical export replaces the legacy CSV when valid. | LOW |
| 6 | `tests/test_eth_yes_fc_os_command_center.py` | `test_market_regime_column_maps_into_regime_metrics` | 208 | TEST_FIXTURE_ONLY | Temp legacy CSV path exists as unused fallback while canonical export supplies `market_regime`. | The test setup breaks if removed without replacing the fallback fixture path. | Yes. The canonical export provides the regime data under test. | LOW |
| 7 | `tests/test_eth_yes_fc_os_command_center.py` | `test_unknown_regime_rate_zero_when_export_valid` | 244 | TEST_FIXTURE_ONLY | Temp legacy CSV path exists as unused fallback while canonical export validates unknown-regime handling. | The test setup breaks if removed without replacing the fallback fixture path. | Yes. The canonical export provides the regime completeness data under test. | LOW |
| 8 | `tests/test_eth_yes_fc_os_command_center.py` | `test_fallback_to_csv_when_canonical_export_missing` | 279 | TEST_FIXTURE_ONLY | Temp filename intentionally exercises fallback to CSV when canonical export is missing. | The specific fallback test breaks. If fallback behavior is retired, this test would become obsolete rather than production-critical. | No for this test's purpose. The point is canonical export missing/invalid fallback behavior. | LOW |
| 9 | `tests/test_eth_yes_fc_os_command_center.py` | `test_old_regime_csv_rejected_as_canonical_export` | 297 | TEST_FIXTURE_ONLY | Temp filename represents an old-style CSV passed as canonical export to prove it is rejected as canonical because it lacks `market_regime`. | The test setup breaks if removed without replacing the stale legacy fixture. | Yes for canonical happy path; no for proving old CSV rejection. | LOW |

## Classification Detail

### ACTIVE_RUNTIME_REQUIRED

None found.

No inspected reference is imported by the trading runtime or required for live/paper execution.

### ACTIVE_RESEARCH_REQUIRED

Only `tools/canonical_trade_table_v1.py:22`.

It is active only in the offline research-export sense. It is not required for the N70 command-center path, but it remains a named output contract for the completed-trade table V1.2 generator.

### FALLBACK_COMPATIBILITY_ONLY

Only `tools/eth_yes_fc_os_command_center.py:14`.

The command center's normal path now validates and uses `canonical_regime_enriched_trades_v1.csv`. The legacy CSV path remains as a fallback default and for `--csv-only` compatibility.

### DEAD_CODE

None proven.

The inspected references are either used by offline tooling paths or by tests. No reference in this focus scope can be labeled dead code from static inspection alone.

### TEST_FIXTURE_ONLY

All seven test references in `tests/test_eth_yes_fc_os_command_center.py`.

They use the old filename as a temporary fixture name. They do not represent runtime dependency. Several tests intentionally prove canonical export wins over or rejects the old schema.

## N70 Readiness Impact

| Question | Answer |
| --- | --- |
| Does any reference block paper/runtime operation? | No |
| Does any reference block N70 accumulation? | No |
| Does any reference prevent a perfectly clean dependency posture? | Yes |
| Does canonical export already provide the N70 governance source? | Yes |
| Is a code/test migration required for clean READY? | Yes, but outside this read-only audit |

## Final Verdict

**CAUTION**

The project is not blocked, but active research tooling still preserves legacy CSV compatibility. The cleanest truth statement is: canonical export is the current N70 governance source; `completed_trades_v1_2.csv` is no longer required for N70 governance, but it remains in fallback/export-generator/test contracts.
