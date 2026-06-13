# ETH YES First Cycle Opening Scan 15s

Status: PARKED

Primary edge class: C Behavioral

Cause-of-death category: SIGNAL_ABSENT_WITH_NON_STATIONARY_ADMISSION

## Candidate Definition

```text
asset = ETH
side = YES
lifecycle = FIRST_CYCLE / OPENING_SCAN
historical canonical hold condition = hold_seconds > 15
```

The candidate was evaluated as a historical behavioral candidate. Its prior
conclusions are preserved and must not be reinterpreted through narrower
sessions, regimes, price buckets, or other post-hoc slices.

## Fingerprint

```yaml
candidate_name: ETH_YES_FIRST_CYCLE_OPENING_SCAN_15S
edge_class: C Behavioral
hypothesis: ETH YES opportunities admitted during FIRST_CYCLE OPENING_SCAN and held beyond 15 seconds contain repeatable signal value
asset: ETH
side: YES
lifecycle: FIRST_CYCLE / OPENING_SCAN
horizon: hold_seconds > 15 historical canonical condition; executable signal audit at +15s
decision_bearing_unit: first generated ETH YES OPENING_SCAN candidate per run_id and candidate_id, clustered by condition_id and epoch_start
data_boundary: historical evidence available through 2026-06-13
duplicate_policy: canonical logical opportunity key condition_id|epoch_start_ts|asset|side|candidate_id; generated-population audits report market/epoch effective sample size
null_suite_mapping: Random Entry Null; Shuffled Signal Null; Market Conditioned Null where required
replay_oos_boundary: no valid confirmatory forward boundary remains because admission was classified non-stationary
version: 1.0
frozen_at: 2026-06-13
fingerprint_hash: PENDING_FREEZE_HASH
```

## Evidence Summary

### Executable Markout@15s

Generated-population executable markout used:

```text
entry = candidate-generation-time YES ask
exit = first available YES bid at or after +15s within the documented tolerance
```

Observed evidence:

- generated candidates: 1,539;
- executable markout coverage: 1,525 / 1,539;
- effective covered market/epoch clusters: 1,280;
- raw mean markout per share: `-0.01283`;
- cluster-adjusted mean markout per share: `-0.01332`;
- cluster-adjusted profit factor: `0.707`;
- cluster-bootstrap 95% mean-markout interval:
  `[-0.01896, -0.00751]`.

The executable markout result was negative. Earlier approved-candidate-only and
path-source views were underpowered or source-limited; the combined executable
quote reconstruction improved coverage but did not restore signal.

### PF Null And Selection-Survivorship Findings

The no-signal PF null preserved actual historical admission counts by
market/epoch, risk mode, and time block.

Observed evidence:

- admitted candidates with executable markout: 139 / 141;
- actual admitted executable PF: `0.170`;
- null median PF: `0.183`;
- null 5th-95th percentile: `[0.169, 0.184]`;
- actual PF percentile: `49.24%`.

Historical admission did not outperform random generated-candidate selection
under the preserved admission structure. Historical PF therefore does not
establish candidate signal and is vulnerable to selection and survivorship
interpretation.

### Terminal Calibration Findings

Terminal-calibration analysis used the generated candidate population without
admission or canonical filtering.

Observed evidence:

- resolved candidates: 690 / 1,539;
- effective resolved market/epoch clusters: 584;
- Brier(model): `0.25726`;
- Brier(market mid): `0.22660`;
- Brier Skill: `-13.53%`;
- clustered-bootstrap Brier Skill 95% interval:
  `[-19.15%, -7.98%]`;
- log-loss improvement versus market: `-10.77%`;
- ROC AUC: `0.5895`;
- ECE: `15.98%`.

Weak discrimination did not overcome material underperformance versus market
consensus. Final terminal classification: `TERMINAL_SIGNAL_ABSENT`.

### Admission Non-Stationarity

Approval rates declined materially:

| Evidence block | Approved / generated |
|---|---:|
| N1-N25 | 22.581% |
| N26-N50 | 8.549% |
| N51-N73 | 6.897% |
| Post-N73 | 4.255% |

MICRO_RECOVERY system-health observation share increased:

| Evidence block | MICRO_RECOVERY share |
|---|---:|
| N1-N25 | 39.64% |
| N26-N50 | 59.48% |
| N51-N73 | 72.87% |
| Post-N73 | 94.31% |

Admission classification: `NON_STATIONARY`.

N100 interpretation was downgraded to
`NON_STATIONARY_FORWARD_DIAGNOSTIC`. It cannot be treated as confirmatory
forward validation.

### Approved-Candidate Observability Failure

Approved-candidate evidence alone did not provide a reliable independent signal
claim:

- early snapshot-only executable reconstruction covered only `29 / 141`
  approved candidates;
- combining decision-log and market-snapshot quotes increased coverage to
  `139 / 141`;
- the higher-coverage result still placed actual admitted PF inside the
  no-signal null distribution;
- approval was strongly conditioned by a changing balance and risk-mode state.

Approved-candidate outcomes therefore cannot substitute for generated-population
signal evidence.

## Final Governance Verdict

```text
PARKED
SIGNAL_ABSENT
NON_STATIONARY_FORWARD_DIAGNOSTIC
```

The candidate is not verified, cannot authorize capital allocation, and cannot
authorize runtime, strategy, threshold, risk, sizing, or execution changes.

## Reopen Criteria

Reopening requires all of the following:

1. A materially new, pre-specified hypothesis rather than a post-hoc slice of
   this candidate.
2. A new immutable candidate fingerprint and version.
3. A new replay out-of-sample boundary frozen before results are observed.
4. A stationary admission regime or a generated-population design independent
   of balance and risk-mode selection.
5. Required Null Suite 001 tests, including random-entry and shuffled-signal
   nulls.
6. Evidence that independently contradicts both the negative executable
   markout and terminal-signal findings.

Meeting reopen criteria creates a new candidate. It does not revive or alter
this candidate's parked record.

## Lessons Learned

- Signal must be demonstrated on generated candidates before execution outcomes
  are interpreted.
- Executable ask-to-bid markout is decision-bearing; mid-price movement is only
  diagnostic.
- Historical PF can appear attractive without outperforming a preserved
  no-signal selection process.
- Admission gates and balance state can make a forward sample non-stationary.
- Raw rows are not independent opportunities; effective market/epoch sample
  size must be reported.
- Weak discrimination does not establish terminal skill when calibration and
  scoring performance are worse than market consensus.
- Parked candidates must not metastasize into post-hoc sub-slices.
