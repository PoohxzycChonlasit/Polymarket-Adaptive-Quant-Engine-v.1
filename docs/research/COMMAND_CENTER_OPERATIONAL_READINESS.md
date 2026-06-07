# Command Center Operational Readiness Audit

Date: 2026-06-07

Scope: READ ONLY / reporting-tool readiness audit

Tool audited:

- `tools/eth_yes_fc_os_command_center.py`

Generated report target:

- `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md`

Verdict: `PARTIALLY_OPERATIONAL_WITH_DATA_SOURCE_GAPS`

## Executive Summary

The command center can run as an offline daily reporting tool without manual document edits. A temp-output validation run completed successfully and reproduced canonical `n=61` from raw trade-journal evidence.

However, it is not fully operational against the approved command-center intent because:

1. It does not automatically read `execution_log`.
2. Decision-log discovery only happens when `--decision-log-dir` is supplied.
3. Raw trade-journal mode reproduces canonical n correctly but lacks regime enrichment, so regime sequence and nc_PF are degraded unless a fresh enriched CSV is used.
4. There is no scheduler or daily automation wrapper; the operator still has to run the command.

## Validation Run

Command used for audit without modifying the repo report:

```powershell
py -3.11 tools/eth_yes_fc_os_command_center.py `
  --decision-log-dir runtime/quant_data/decision_log `
  --jsonl-integrity-status BLOCKED `
  --output-path $env:TEMP\ETH_YES_FC_OS_COMMAND_CENTER_audit.md
```

Result:

| Metric | Value |
|---|---:|
| Exit status | Success |
| Canonical n | 61 |
| Raw filtered rows | 62 |
| Duplicate rows removed | 1 |
| WR | 57.4% |
| PF | 2.031 |
| p-value | 0.153 |
| n required for p < 0.05 | 117 |
| 7d velocity | 0.43/day |
| 14d velocity | 2.07/day |
| Latest decision date | 2026-06-07 |
| Latest decision count | 9158 |

## 1. Can It Run Daily Without Manual Edits?

Status: `YES_WITH_OPERATOR_COMMAND`

The tool can generate a command-center markdown report without editing source code or hand-editing markdown content.

Daily command:

```powershell
py -3.11 tools/eth_yes_fc_os_command_center.py --decision-log-dir runtime/quant_data/decision_log --jsonl-integrity-status BLOCKED
```

What works:

- writes the report automatically
- reproduces canonical n from raw trade journals
- updates WR, PF, p-value, progress rail, velocity, and kill monitor fields
- uses default `runtime/quant_data/trade_journal`
- uses default report path
- uses default `BLOCKED` JSONL integrity label

What is not automated:

- no scheduler exists
- no daily runbook wrapper exists
- decision-log path must be supplied unless the operator accepts manual placeholders
- no automatic commit or archive behavior exists

## 2. Source Discovery

### Trade Journal

Status: `YES`

The tool defaults to:

```text
runtime/quant_data/trade_journal
```

It discovers all `*.jsonl` files under that directory and reconstructs trade open/close rows. This is the current canonical-n path and reproduced:

```text
62 raw filtered rows -> 1 duplicate removed -> canonical n=61
```

### Decision Logs

Status: `PARTIAL`

The tool can discover decision logs, but only when invoked with:

```text
--decision-log-dir runtime/quant_data/decision_log
```

It then scans the latest dated file by default:

```text
--decision-log-days 1
```

Reason: decision logs are very large. Current observed decision-log folder size is multi-GB, and scanning many days can time out interactively.

Latest observed files:

| Date | Size |
|---|---:|
| 2026-06-05 | 311,536,011 bytes |
| 2026-06-06 | 339,676,696 bytes |
| 2026-06-07 | 294,030,247 bytes |

Current behavior:

- latest decision date is detected
- ETH COMPRESSION share for latest scanned file is computed
- BTC modal regime for latest scanned file is computed
- latest decision count is computed

Limitation:

- `COMPRESSION absence days` may remain `[MANUAL REQUIRED]` when the scan window does not include a day with COMPRESSION share > 5%.
- A larger scan can be requested with `--decision-log-days N`, but that can be slow.

### Execution Logs

Status: `NO`

The tool does not currently accept or scan:

```text
runtime/quant_data/execution_log
```

Latest execution-log files exist:

| Date | Size |
|---|---:|
| 2026-06-05 | 313,575 bytes |
| 2026-06-06 | 278,698 bytes |
| 2026-06-07 | 1,323,299 bytes |

Impact:

- execution-log freshness is not displayed
- execution-log continuity is not validated
- execution-derived fields are not used for command-center metrics
- the requirement "automatically discover latest execution logs" is not met

## 3. Metric Update Readiness

| Metric | Updates without source-code changes? | Current source | Readiness |
|---|---|---|---|
| Canonical n | Yes | raw trade_journal | READY |
| WR | Yes | raw trade_journal | READY |
| PF | Yes | raw trade_journal | READY |
| p-value | Yes | computed from n and wins | READY |
| Velocity | Yes | raw trade_journal entry timestamps | READY |
| nc_PF | Mechanically yes | raw trade_journal regime field | DEGRADED |
| Regime sequence | Mechanically yes | raw trade_journal regime field | DEGRADED |
| COMPRESSION share | Yes if `--decision-log-dir` supplied | decision_log | PARTIAL |
| BTC regime | Yes if `--decision-log-dir` supplied | decision_log | PARTIAL |
| Execution continuity | No | not read | MISSING |

## nc_PF Caveat

The tool currently computes nc_PF from the rows used for canonical counting.

In raw trade-journal mode, canonical n is correct, but the reconstructed rows do not carry reliable regime labels. The generated audit report showed:

```text
Last-5 regime sequence: UNKNOWN -> UNKNOWN -> UNKNOWN -> UNKNOWN -> UNKNOWN
Regime mix: UNKNOWN:61
```

Therefore:

- canonical n is operationally correct
- WR and PF are operationally correct
- velocity is operationally correct
- nc_PF is not yet fully research-grade in raw trade-journal mode

For research-grade nc_PF, the tool needs one of:

1. a fresh enriched canonical CSV that includes n=61 and regime labels, or
2. an internal join to decision/execution evidence that carries regime context.

No source-code change was made during this audit.

## 4. Manual Steps Remaining

Required manual/operator steps:

| Step | Reason |
|---|---|
| Run the command daily | No scheduler exists |
| Supply `--decision-log-dir runtime/quant_data/decision_log` | Default is CSV/trade-journal only for decision metrics |
| Review `[MANUAL REQUIRED]` fields | Compression absence can require larger scan window |
| Decide whether to scan more decision-log days | More days improve context but can be slow |
| Interpret JSONL writer integrity flag | Static `BLOCKED` / `NOMINAL` state is not data-derived |
| Verify regime/nc_PF quality | Raw trade-journal mode lacks regime enrichment |

No manual markdown editing is required for the generated report itself.

## Operational Readiness Classification

| Capability | Classification |
|---|---|
| Daily report generation | OPERATIONAL |
| Canonical n reproduction | OPERATIONAL |
| WR/PF update | OPERATIONAL |
| Velocity update | OPERATIONAL |
| Latest trade-journal discovery | OPERATIONAL |
| Latest decision-log discovery | PARTIAL |
| Latest execution-log discovery | MISSING |
| nc_PF research-grade accuracy | PARTIAL |
| Full no-manual-argument operation | PARTIAL |

## Recommended Operating Command

Use this until the remaining gaps are explicitly addressed:

```powershell
py -3.11 tools/eth_yes_fc_os_command_center.py --decision-log-dir runtime/quant_data/decision_log --jsonl-integrity-status BLOCKED
```

Optional slower context scan:

```powershell
py -3.11 tools/eth_yes_fc_os_command_center.py --decision-log-dir runtime/quant_data/decision_log --decision-log-days 3 --jsonl-integrity-status BLOCKED
```

Avoid `--decision-log-days 0` during normal daily operation unless the operator intentionally wants a full multi-GB scan.

## Governor Verdict

`PARTIALLY_OPERATIONAL_WITH_DATA_SOURCE_GAPS`

The command center is ready for daily observational use for:

- canonical n
- WR
- PF
- velocity
- promotion gate display
- kill monitor display

It is not yet fully ready for autonomous operational governance because:

- execution logs are not discovered
- decision logs require an operator-supplied path
- nc_PF/regime panels are degraded in raw trade-journal mode
- no scheduler exists

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No
