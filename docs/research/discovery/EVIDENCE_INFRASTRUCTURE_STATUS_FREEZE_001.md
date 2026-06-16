# Evidence Infrastructure Status Freeze 001

Status: FROZEN PLANNING STATE

Scope: Discovery Framework V3 evidence infrastructure only

Authority: none over runtime, strategy, risk, execution, candidate promotion, or live trading

## Objective

Preserve the current evidence-infrastructure priority and prevent work from
expanding before the first Discovery Audit becomes possible.

Exact next milestone:

```text
OUTCOME_TRUTH_READY
```

## Candidate Blocker Map

| Candidate | Primary blocker | Current readiness | Outcome Truth dependency |
|---|---|---|---|
| `CALIBRATION_BUCKET_DRIFT` | Official terminal outcome truth | `AUDIT_NOT_READY` | Required |
| `ORACLE_SETTLEMENT_PRINT` | Official outcome truth plus raw oracle history | `QUEUED` | Required |
| `SPOT_LEADLAG` | Replay-grade raw spot and oracle history | `AUDIT_NOT_READY` | Not required for initial lead-lag audit |
| `CONVERGENCE_DECAY` | Replay-grade raw market history | `QUEUED` | Candidate-definition dependent |
| `MAKER_SPREAD_CAPTURE` | Queue position and deterministic passive-fill truth | `BLOCKED` | Not required |

## Evidence Layer Priority

| Priority | Evidence layer | Portfolio role | Current state |
|---:|---|---|---|
| 1 | Official Outcome Truth | Shortest path to the first `AUDIT_READY` candidate | `BLOCKED_BY_ARCHIVE_RPC` |
| 2 | Raw Spot / Oracle Feed Foundation | Unlocks prospective lead-lag and settlement research | `DESIGN_READY_COLLECTION_NOT_STARTED` |
| 3 | Queue / Fill Truth | Required for executable maker-spread research | `BLOCKED_MISSING_QUEUE_AND_FILL_TRUTH` |

This ordering is frozen until `OUTCOME_TRUTH_READY` is reached or the archive
RPC dependency is formally declared unavailable.

## Evidence Layer Status

### Outcome Truth

```text
Status: OUTCOME_TRUTH_NOT_READY
```

Completed:

- Discovery governance, harness, Null Suite, scanner, and loss-bound work.
- Basic Conditional Tokens Framework payout-state pilot.
- Hardened pilot acquisition and replay-verification code.
- Full-history execution sequence defined.

Blocking dependency:

```text
archive-capable Polygon historical RPC access
```

The archive RPC must support historical blocks, logs, receipts, and state calls
required to preserve ConditionResolution provenance and final payout state.

### Raw Feed Foundation

```text
Status: SPOT_LEADLAG_AUDIT_NOT_READY
```

Current evidence:

- persisted replay-grade raw spot observations: `0`
- persisted replay-grade raw oracle observations: `0`
- direct source timestamp coverage: unavailable
- deterministic historical lead-lag reconstruction: impossible

The minimum prospective architecture is defined, but no implementation or
collection is authorized by this document.

### Queue / Fill Truth

```text
Status: MAKER_SPREAD_CAPTURE_BLOCKED
```

Available evidence includes sampled top-of-book bid, ask, spread, shallow
depth, liquidity, and path checkpoints.

Missing decision-bearing evidence:

- queue position;
- queue-ahead size;
- deterministic passive-maker fill reconstruction;
- partial-fill lifecycle;
- cancel/replace lifecycle;
- fill-conditioned maker adverse-selection truth.

Quoted spread can be described, but executable maker spread capture cannot be
audited.

## Next External Dependency

The single next required external dependency is:

```text
archive-capable Polygon RPC
```

When available, the approved sequence is:

```text
archive RPC preflight
-> full-history official outcome acquisition
-> evidence packaging
-> replay verification
-> deterministic decision-to-outcome joins
-> coverage measurement
-> Outcome Truth graduation review
```

## Work That Must Not Be Built Next

Until `OUTCOME_TRUTH_READY`:

- no new governance;
- no new dashboards;
- no new candidate families;
- no strategy changes;
- no risk or execution changes;
- no live trading;
- no Raw Feed implementation ahead of the frozen priority;
- no Queue / Fill Truth implementation ahead of the frozen priority.

## Freeze Verdict

```text
CURRENT_DISCOVERY_INFRASTRUCTURE_STATE:
OUTCOME_TRUTH_BLOCKED_BY_ARCHIVE_RPC

NEXT_MILESTONE:
OUTCOME_TRUTH_READY
```

No candidate audit becomes authorized by this status freeze. The next valid
work begins only when archive-capable Polygon RPC access is available for the
already-defined Outcome Truth execution path.
