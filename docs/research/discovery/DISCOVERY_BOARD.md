# Discovery Board

Status: PHASE 0 FROZEN

| Candidate | Class | Status | Verdict |
|---|---|---|---|
| ETH YES OPENING_SCAN 15s | C Behavioral | PARKED | SIGNAL_ABSENT |
| NULL_SUITE | Reference Control | QUEUED | - |
| CALIBRATION_BUCKET_DRIFT | C Behavioral | QUEUED | - |
| SPOT_LEADLAG | A Lead-Lag | QUEUED | - |
| ORACLE_SETTLEMENT_PRINT | B Settlement | QUEUED | - |
| CONVERGENCE_DECAY | F Time Decay | QUEUED | - |
| MAKER_SPREAD_CAPTURE | D Microstructure | QUEUED | - |

## Board Rules

- Board presence is not approval to audit or implement.
- Every candidate requires a frozen definition and decision-bearing unit before
  analysis.
- Every candidate requires an immutable fingerprint before audit.
- Every candidate must map to Null Suite 001.
- PARKED candidates require graveyard records and cannot be silently resliced.
- New results do not change runtime, strategy, thresholds, risk, or execution.

`Reference Control` is not part of the frozen A-G candidate taxonomy and does
not count as a tested candidate family or variant.

The board must track tested-family and tested-variant counts when candidates
move from QUEUED to AUDITING.
