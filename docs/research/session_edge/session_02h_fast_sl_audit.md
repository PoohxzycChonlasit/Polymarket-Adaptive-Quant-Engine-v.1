# 02h Fast Stop-Loss + Executable Reality Audit

Date: 2026-05-24

Scope: read-only research audit of 02h UTC fast stop-loss pressure and executable-reality classification.

Runtime behavior changed: No
Live behavior changed: No

## Verdict

Classification:

```text
02h UTC = HOSTILE_SESSION_CANDIDATE
```

This is not a confirmed structural runtime rule. It is a research label only.

Why:

- 02h has `0 TP / 8 SL` in the latest matched 2026-05-23 evidence.
- `6/8` SLs close within `15s`.
- `8/8` SLs close within `30s`.
- median hold time is only `6.5s`.
- all 02h trades are dust-zone / simulation-only, so this is signal evidence, not executable evidence.

The strongest interpretation is:

```text
02h is more than NORMAL_SESSION noise, but not yet proven structurally hostile.
Track as HOSTILE_SESSION_CANDIDATE, exclude from positive session-edge evidence, and do not change runtime thresholds or policy.
```

## Sources

- `docs/research/fast_stop_loss_audit.md`
- `docs/research/executable_truth/paper_sizing_audit.md`
- `docs/research/executable_truth/capital_ladder_audit.md`
- `docs/research/executable_truth/minimum_executable_reality_audit.md`
- `docs/research/executable_truth/executable_reality_overlay_design.md`
- `docs/research/executable_truth/executable_reality_monitor.md`
- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`
- `runtime/quant_data/decision_log/2026-05-23.jsonl`

## Evidence Set

Latest matched evidence used:

```text
date = 2026-05-23
matched trades = 34
02h matched trades = 8
```

All matched rows are paper evidence. Some 02h rows repeat the same market timestamp across separate paper runs, so the sample should be interpreted as repeated paper-session evidence, not independent live execution.

## 02h Summary

| Metric | Value |
|---|---:|
| TP | `0` |
| SL | `8` |
| TP rate | `0.0%` |
| SL rate | `100.0%` |
| SL <= 15s | `6/8` |
| SL <= 30s | `8/8` |
| min hold | `4s` |
| median hold | `6.5s` |
| mean hold | `8.75s` |
| max hold | `19s` |
| signal PnL | `-$0.06515721` |
| executable PnL | `N/A` |
| dust-zone trades | `8/8` |
| executable trades | `0/8` |

## Evidence Table

| UTC | Run ID | Asset | Side | Lifecycle | Entry | Exit | Move | Hold | Result | Quote Stale | EV | Confidence | Notional | Executable Class |
|---|---|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| 02:10:08 | `20260523T014953Z_24280_63ef0520` | ETH | NO | OPENING_SCAN | `0.50` | `0.46` | `-0.04` | `6s` | SL | `7590.804ms` | `0.1443` | `0.5415` | `$0.050248` | `SIMULATION_ONLY` |
| 02:10:08 | `20260523T020201Z_1500_a1f33f5a` | ETH | NO | OPENING_SCAN | `0.50` | `0.46` | `-0.04` | `7s` | SL | `7590.804ms` | `0.1443` | `0.5415` | `$0.050248` | `SIMULATION_ONLY` |
| 02:10:48 | `20260523T015426Z_16036_ac5d7312` | ETH | YES | ACTIVE_INVENTORY_TRADING | `0.58` | `0.42` | `-0.16` | `4s` | SL | `4452.233ms` | `0.0884` | `0.5668` | `$0.055554` | `SIMULATION_ONLY` |
| 02:20:50 | `20260523T015426Z_16036_ac5d7312` | ETH | YES | ACTIVE_INVENTORY_TRADING | `0.52` | `0.43` | `-0.09` | `19s` | SL | `7691.451ms` | `0.1368` | `0.5546` | `$0.050241` | `SIMULATION_ONLY` |
| 02:20:50 | `20260523T014953Z_24280_63ef0520` | ETH | YES | ACTIVE_INVENTORY_TRADING | `0.52` | `0.41` | `-0.11` | `5s` | SL | `7691.451ms` | `0.1368` | `0.5546` | `$0.050241` | `SIMULATION_ONLY` |
| 02:20:50 | `20260523T020201Z_1500_a1f33f5a` | ETH | YES | ACTIVE_INVENTORY_TRADING | `0.52` | `0.41` | `-0.11` | `18s` | SL | `7691.451ms` | `0.1368` | `0.5546` | `$0.050241` | `SIMULATION_ONLY` |
| 02:30:30 | `20260523T020201Z_1500_a1f33f5a` | BTC | YES | OPENING_SCAN | `0.51` | `0.45` | `-0.06` | `4s` | SL | `4877.433ms` | `0.1410` | `0.7314` | `$0.048271` | `SIMULATION_ONLY` |
| 02:40:08 | `20260523T015426Z_16036_ac5d7312` | ETH | NO | OPENING_SCAN | `0.50` | `0.44` | `-0.06` | `7s` | SL | `7416.797ms` | `0.1445` | `0.7223` | `$0.025093` | `SIMULATION_ONLY` |

## Hold-Time Buckets

| Bucket | 02h SL Count |
|---|---:|
| `0-5s` | `3` |
| `5-15s` | `3` |
| `15-30s` | `2` |
| `30s+` | `0` |

Interpretation:

02h pressure is fast. Every 02h SL closed before `30s`; most closed before `15s`.

## Lifecycle Split

| Lifecycle | TP | SL |
|---|---:|---:|
| OPENING_SCAN | `0` | `4` |
| ACTIVE_INVENTORY_TRADING | `0` | `4` |

Interpretation:

Fast SL pressure is not ACTIVE-specific. It appears in both OPENING_SCAN and ACTIVE_INVENTORY_TRADING.

## Asset And Side Split

| Asset | TP | SL |
|---|---:|---:|
| ETH | `0` | `7` |
| BTC | `0` | `1` |

| Side | TP | SL |
|---|---:|---:|
| YES | `0` | `5` |
| NO | `0` | `3` |

Interpretation:

02h is mostly ETH in the observed sample, but the one BTC trade also failed fast. Side is not cleanly isolated: YES has more SLs, but NO also fails.

## Quote Staleness

02h quote staleness:

| Field | Count | Min | Mean | Median | Max |
|---|---:|---:|---:|---:|---:|
| exit `quote_stale_ms` | `8` | `4452.233ms` | `6875.303ms` | `7590.804ms` | `7691.451ms` |
| entry `quote_stale_ms` | `8` | `10016.489ms` | `23146.514ms` | `10214.309ms` | `59356.153ms` |

Exit quote buckets:

| Bucket | Count |
|---|---:|
| `0-5s` | `2` |
| `5-15s` | `6` |
| `15-30s` | `0` |
| `30-60s` | `0` |
| `60s+` | `0` |

Interpretation:

02h fast SLs are not primarily quote-staleness driven. Exit quotes are mostly `5-15s` old, with no `15s+` exit quote ages. One entry quote was very stale at about `59s`, but the cluster persists across rows with around `10s` entry quote age.

## Entry, Exit, EV, Confidence

02h aggregate:

| Metric | Min | Mean | Median | Max |
|---|---:|---:|---:|---:|
| entry price | `0.50` | `0.51875` | `0.515` | `0.58` |
| exit price | `0.41` | `0.435` | `0.435` | `0.46` |
| price move | `-0.16` | `-0.08375` | `-0.075` | `-0.04` |
| EV | `0.0884` | `0.1341` | `0.1389` | `0.1445` |
| confidence | `0.5415` | `0.5959` | `0.5546` | `0.7314` |

Interpretation:

The model was not only entering low-EV rows. EV and confidence were often acceptable, including a BTC trade with confidence `0.7314`, but the exits reversed quickly. This points toward session/microstructure/entry-timing pressure rather than a simple low-confidence-only issue.

## 02h Decision Blockers

Filtered 02h decision log rows:

```text
decision rows = 1524
approved-like rows = 9
```

Top normalized blockers:

| Blocker | Count |
|---|---:|
| `delta_extreme` | `770` |
| `confidence_too_low` | `362` |
| `time_unsafe` | `194` |
| `frequency_cooldown` | `146` |
| `risk_plan_zero` | `19` |
| `empty_book` | `18` |
| `ev_below_threshold` | `9` |
| `max_active_positions_per_market_reached` | `3` |
| `max_trades_per_hour_reached` | `2` |
| `stale_data` | `1` |

Lifecycle distribution in 02h decisions:

| Lifecycle | Count |
|---|---:|
| OPENING_SCAN | `181` |
| ACTIVE_INVENTORY_TRADING | `1033` |
| PROFIT_MANAGEMENT | `156` |
| FINAL_DERISK | `154` |

Interpretation:

The broader 02h decision surface is hostile-looking: many rows are filtered by extreme delta, low confidence, unsafe timing, and cooldowns. This supports `HOSTILE_SESSION_CANDIDATE`, but does not authorize threshold/risk changes.

## Executable Reality

All 02h matched trades are:

```text
DUST_ZONE
SIMULATION_ONLY
```

Reasons:

- shares are around `0.05-0.10`, far below the conservative `5 share` practical minimum;
- notional is around `$0.025-$0.056`, far below the representative `$2.50` executable notional at `0.50`;
- executable trade count is `0`.

Executable reality changes the interpretation:

- it strengthens the caution against executable-PnL claims;
- it weakens any argument for immediate runtime policy;
- it does not erase the signal-level warning that 02h behaves badly.

## Required Answers

1. Is 02h structurally hostile or only noisy?

Not proven structurally hostile, but more than ordinary noise in this sample. The right label is `HOSTILE_SESSION_CANDIDATE`, not confirmed hostile regime.

2. Is fast SL pressure ACTIVE-specific?

No. 02h has `4` OPENING_SCAN SLs and `4` ACTIVE_INVENTORY_TRADING SLs.

3. Is it asset/side-specific?

Partially asset-skewed toward ETH: `7/8` SLs are ETH. But BTC also produced a fast SL, and both YES and NO fail, so the pattern is not cleanly asset- or side-specific.

4. Is it quote-staleness driven?

No clear evidence. Exit quote ages are `4.45s-7.69s`; no 02h SL has `15s+` exit quote age. Entry quote age has one stale outlier, but the broader pattern remains with around `10s` entry quote age.

5. Should 02h be excluded from session-edge evidence?

Yes for positive session-edge claims. 02h should be excluded from bullish session-edge evidence and tracked separately as a negative/hostile candidate bucket.

6. Should 02h be tracked as HOSTILE_SESSION_CANDIDATE or WATCH only?

Track as `HOSTILE_SESSION_CANDIDATE`. Keep the label research-only. Do not convert it into a runtime block, threshold change, or risk change without more evidence.

7. Does executable reality change the interpretation?

Yes. It downgrades all 02h PnL to signal-only / simulation-only evidence. The session warning remains useful, but no executable-PnL or live-readiness claim should be made from these trades.

## Final Classification

```text
SESSION_CLASSIFICATION: HOSTILE_SESSION_CANDIDATE
STRUCTURAL_CONFIDENCE: LOW_TO_MEDIUM
EVIDENCE_TYPE: SIGNAL_MODE_ONLY
EXECUTABLE_MODE: NO_EVIDENCE
DUST_ZONE: 8/8
POLICY_ACTION: NONE
```

## Monitoring Recommendation

Keep 02h in a separate watch bucket:

- count TP/SL by date;
- require cross-date recurrence before policy;
- compare 02h against 09h/10h;
- track fast SL under `15s` and under `30s`;
- keep executable reality labels in the table;
- do not mix 02h losses into positive session-edge claims without separate attribution.

Tests: not run; docs-only read-only audit.
