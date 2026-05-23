# Fast Stop-Loss Audit

Date: 2026-05-23

Scope: read-only audit of latest paper trades and recent matched trades.

Runtime behavior changed: No
Live behavior changed: No

## Verdict

Stop-loss exits are systematically fast in the latest 2026-05-23 matched evidence.

Same-day matched trades:

| Result | Count | Min Hold | Mean Hold | Median Hold | Max Hold |
|---|---:|---:|---:|---:|---:|
| TP | `11` | `10s` | `26.09s` | `16s` | `73s` |
| SL | `23` | `4s` | `14.74s` | `11s` | `60s` |

SLs are faster than TPs, but the evidence points more toward stop-threshold / rapid adverse price movement than quote staleness. Exit quote age is lower for SL than TP on average.

Current fast-SL evidence should be treated as signal evidence only, not executable evidence, because current paper sizes remain dust-zone / simulation-only.

## Sources

- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`
- `docs/research/executable_reality_monitor.md`
- `docs/research/minimum_executable_reality_audit.md`

## Latest Run Snapshot

Latest run:

```text
run_id = 20260523T164003Z_21336_726ed17b
```

Latest matched trades:

| UTC | Asset | Side | Result | Reason | Lifecycle | Entry | Exit | Hold | Quote Stale | Entry Quote Age | Exit Quote Age | PnL |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 16:55:40 | ETH | NO | SL | `stop_loss` | ACTIVE_INVENTORY_TRADING | `0.47` | `0.39` | `22s` | `13348.619ms` | `10461.105ms` | `13348.619ms` | `-$0.008553` |
| 16:56:04 | BTC | NO | SL | `stop_loss_hit` | ACTIVE_INVENTORY_TRADING | `0.62` | `0.59` | `11s` | `11996.171ms` | `11023.676ms` | `11996.171ms` | `-$0.006225` |

Latest-run interpretation:

- `2/2` latest matched trades were SL.
- Both were `ACTIVE_INVENTORY_TRADING`.
- Both were fast: one `5-15s`, one `15-30s`.
- Quote staleness was moderate, around `12-13s`, not `60s+`.

## Recent Matched Trade Set

Same-day matched trade count:

```text
matched trades = 34
TP = 11
SL = 23
```

SL hold-time buckets:

| Bucket | SL Count |
|---|---:|
| `0-5s` | `5` |
| `5-15s` | `10` |
| `15-30s` | `6` |
| `30s+` | `2` |

TP hold-time buckets:

| Bucket | TP Count |
|---|---:|
| `0-5s` | `0` |
| `5-15s` | `5` |
| `15-30s` | `3` |
| `30s+` | `3` |

Fast-SL concentration:

```text
SL <= 15s = 15/23 = 65.2%
SL <= 30s = 21/23 = 91.3%
TP <= 15s = 5/11 = 45.5%
TP <= 30s = 8/11 = 72.7%
```

## Price Move

| Result | Mean Move | Median Move | Min Move | Max Move | Mean Move % | Median Move % |
|---|---:|---:|---:|---:|---:|---:|
| SL | `-0.0800` | `-0.0700` | `-0.1700` | `-0.0300` | `-15.37%` | `-14.00%` |
| TP | `+0.1073` | `+0.0800` | `+0.0600` | `+0.3400` | `+19.69%` | `+15.38%` |

Interpretation:

SL exits are not just a timestamp artifact. They coincide with quick adverse moves from entry to exit. The median SL price move is about `-0.07` contract price, while median TP move is about `+0.08`.

## Quote Staleness

Quote-age comparison:

| Result | Quote Field | Count | Mean | Median | Min | Max |
|---|---|---:|---:|---:|---:|---:|
| TP | exit `quote_stale_ms` | `11` | `13089.471ms` | `12486.660ms` | `10355.553ms` | `17853.982ms` |
| SL | exit `quote_stale_ms` | `23` | `8845.150ms` | `7691.451ms` | `4221.603ms` | `14339.662ms` |
| TP | entry `quote_stale_ms` | `11` | `16261.826ms` | `10701.571ms` | n/a | n/a |
| SL | entry `quote_stale_ms` | `23` | `17346.924ms` | `10652.799ms` | n/a | n/a |

SL quote-staleness buckets:

| Bucket | SL Count |
|---|---:|
| `0-5s` | `4` |
| `5-15s` | `19` |
| `15-30s` | `0` |
| `30-60s` | `0` |
| `60s+` | `0` |

Interpretation:

Fast SLs are not clearly linked to stale quotes. Exit quote age is lower for SL than TP, and no SL in this sample used `15s+` exit quote age. Entry quote age is similar between TP and SL.

## Lifecycle Split

| Lifecycle | TP | SL | SL Rate |
|---|---:|---:|---:|
| OPENING_SCAN | `6` | `13` | `68.4%` |
| ACTIVE_INVENTORY_TRADING | `5` | `10` | `66.7%` |

Interpretation:

Fast SLs are not uniquely ACTIVE-driven. Both OPENING and ACTIVE have similar SL rates in this sample. The latest run was ACTIVE-only, but the broader matched set shows SL behavior across both lifecycle phases.

## Session Concentration

SL by hour:

| Hour UTC | SL Count |
|---|---:|
| `01h` | `1` |
| `02h` | `8` |
| `03h` | `1` |
| `10h` | `2` |
| `11h` | `4` |
| `12h` | `2` |
| `14h` | `1` |
| `16h` | `4` |

TP by hour:

| Hour UTC | TP Count |
|---|---:|
| `01h` | `1` |
| `09h` | `4` |
| `10h` | `2` |
| `11h` | `1` |
| `12h` | `1` |
| `16h` | `2` |

Fast SL by hour and bucket:

| Hour UTC | `0-5s` | `5-15s` | `15-30s` | `30s+` |
|---|---:|---:|---:|---:|
| `01h` | `0` | `0` | `1` | `0` |
| `02h` | `3` | `3` | `2` | `0` |
| `03h` | `1` | `0` | `0` | `0` |
| `10h` | `1` | `1` | `0` | `0` |
| `11h` | `0` | `2` | `1` | `1` |
| `12h` | `0` | `1` | `1` | `0` |
| `14h` | `0` | `1` | `0` | `0` |
| `16h` | `0` | `2` | `1` | `1` |

Interpretation:

Fast SLs are most concentrated in `02h UTC`, with `6/8` of that hour's SLs closing inside `15s`. `11h` and `16h` also have clusters, but 02h is the clearest fast-loss pocket.

## Asset And Side

SL by asset:

| Asset | SL Count |
|---|---:|
| ETH | `19` |
| BTC | `4` |

TP by asset:

| Asset | TP Count |
|---|---:|
| ETH | `8` |
| BTC | `3` |

SL by side:

| Side | SL Count |
|---|---:|
| YES | `10` |
| NO | `13` |

TP by side:

| Side | TP Count |
|---|---:|
| YES | `6` |
| NO | `5` |

Interpretation:

ETH has more SLs because it has more trades in this sample. There is no clean YES/NO directional smoking gun: SLs are split across both sides.

## Exit Reasons

SL reason counts:

| Reason | Count |
|---|---:|
| `stop_loss` | `17` |
| `stop_loss_hit` | `6` |

All SLs are stop-loss exits. There is no evidence here of alternate close reasons being mislabeled as SL.

## Answers

1. Are SL exits systematically too fast?

Yes. Same-day SL median hold is `11s`, and `65.2%` of SLs close within `15s`. TPs are also often fast, but they last longer on average and have no `0-5s` closes in this sample.

2. Are fast SLs concentrated in specific sessions?

Yes. `02h UTC` is the strongest fast-SL cluster, with `8` SLs and `6` closing within `15s`. `11h` and `16h` also show clusters, but they are less clean.

3. Are fast SLs linked to stale quotes?

Not strongly. SL exit quote age is lower than TP exit quote age on average: about `8.85s` for SL versus `13.09s` for TP. No SL in this matched set has `15s+` exit quote age.

4. Are fast SLs linked to ACTIVE vs OPENING?

Not uniquely. OPENING has `13` SL / `6` TP; ACTIVE has `10` SL / `5` TP. SL rate is similar across both lifecycle phases.

5. Are fast SLs caused by stop threshold or entry timing?

The evidence points to stop threshold triggered by rapid adverse price movement after entry. Median SL move is about `-0.07` contract price, or `-14%`. Entry timing/session likely contributes, especially in `02h`, but quote staleness is not the primary visible cause.

6. Should current fast-SL evidence be treated as signal evidence only or executable evidence?

Signal evidence only. Current paper sizing remains dust-zone / simulation-only, so fast-SL observations are useful for signal timing, threshold behavior, and session diagnostics, but not executable PnL or live fill realism.

## Current Classification

```text
FAST_SL_PRESENT
SESSION_CLUSTER_02H
QUOTE_STALENESS_NOT_PRIMARY
ACTIVE_ONLY_CAUSE_NOT_PROVEN
THRESHOLD_OR_ENTRY_TIMING_LIKELY
EXECUTABLE_EVIDENCE: NO
```

## Recommended Next Research Step

Compare `02h` entries against `09h/10h` entries using:

- entry price distance to midpoint,
- spread at entry,
- first 15-second MFE/MAE,
- lifecycle phase,
- quote age,
- executable reality class.

This should remain research-only unless a future task explicitly scopes threshold, timing, or risk-policy changes.

Tests: not run; docs-only read-only audit.
