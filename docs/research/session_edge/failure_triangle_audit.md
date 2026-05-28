# BTC / NO / ACTIVE Failure Triangle Audit

Date: 2026-05-25

Scope: read-only path truth and trade journal audit. No code, runtime, strategy, risk, stoploss, live, or field-wiring changes.

## Role Routing

Primary role: `10_BACKTEST_REPLAY_AGENT.md`

Supporting roles:

- `16_PAPER_EVALUATION_AGENT.md`
- `11_OBSERVABILITY_INCIDENT_AGENT.md`
- `07_TEST_CI_AGENT.md`

Reason: the task is an offline path-truth/backtest-style segmentation audit with paper evidence interpretation, observability coverage checks, and docs-only verification.

## Sources Inspected

- `runtime/quant_data/path_truth/*.jsonl`
- `runtime/quant_data/trade_journal/*.jsonl`
- `docs/quant_agent_setup_md/roles/10_BACKTEST_REPLAY_AGENT.md`
- `docs/quant_agent_setup_md/roles/16_PAPER_EVALUATION_AGENT.md`
- `docs/quant_agent_setup_md/roles/11_OBSERVABILITY_INCIDENT_AGENT.md`
- `docs/quant_agent_setup_md/roles/07_TEST_CI_AGENT.md`

Join method:

- Path truth rows were joined to trade journal close evidence by `run_id` and `trade_id` / `position_id`.
- Hold duration used `trade_journal.hold_seconds` where available.
- Stage normalized from lifecycle values:
  - `OPENING_SCAN` -> `OPENING`
  - `ACTIVE_INVENTORY_TRADING` -> `ACTIVE`
- Price bucket derived from `entry_price`.

## Overall Evidence

Total paired trades: 25

Outcome:

- TP: 7
- SL: 18
- Win rate: 28.0%

Fast close:

- `<60s`: 22 / 25 = 88.0%
- Full path truth coverage: 3 / 25
- Fast-close partial path truth: 22 / 25

## Failure Triangle Matrix

| Bucket | Trades | TP | SL | Win Rate | Median Hold | Fast Close | Hold Buckets | Sessions | Price Buckets | Path Truth Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| BTC + YES + OPENING | 1 | 0 | 1 | 0.0% | 16s | 100.0% | 15-30s: 1 | 1 session | 0.60+: 1 | fast before second checkpoint: 1 |
| BTC + YES + ACTIVE | 4 | 0 | 4 | 0.0% | 9s | 100.0% | 0-15s: 4 | 2 sessions | 0.50-0.59: 3, 0.40-0.49: 1 | fast before first checkpoint: 4 |
| BTC + NO + OPENING | 2 | 0 | 2 | 0.0% | 49.5s | 50.0% | 60s+: 1, 15-30s: 1 | 2 sessions | 0.50-0.59: 2 | full: 1, fast before second checkpoint: 1 |
| BTC + NO + ACTIVE | 1 | 0 | 1 | 0.0% | 8s | 100.0% | 0-15s: 1 | 1 session | 0.40-0.49: 1 | fast before first checkpoint: 1 |
| ETH + YES + OPENING | 10 | 5 | 5 | 50.0% | 23.5s | 80.0% | 60s+: 2, 0-15s: 3, 15-30s: 4, 30-45s: 1 | 4 sessions | 0.50-0.59: 9, 0.40-0.49: 1 | full: 2, fast partial: 8 |
| ETH + YES + ACTIVE | 1 | 1 | 0 | 100.0% | 11s | 100.0% | 0-15s: 1 | 1 session | 0.60+: 1 | fast before first checkpoint: 1 |
| ETH + NO + OPENING | 5 | 0 | 5 | 0.0% | 22s | 100.0% | 0-15s: 2, 15-30s: 2, 45-60s: 1 | 4 sessions | 0.50-0.59: 4, 0.60+: 1 | fast before first: 3, second: 1, 60s: 1 |
| ETH + NO + ACTIVE | 1 | 1 | 0 | 100.0% | 23s | 100.0% | 15-30s: 1 | 1 session | 0.50-0.59: 1 | fast before second checkpoint: 1 |

## Single-Factor Diagnostics

### Asset

| Asset | Trades | TP | SL | Win Rate | Median Hold | Fast Close | Hold Buckets |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BTC | 8 | 0 | 8 | 0.0% | 12s | 87.5% | 0-15s: 5, 15-30s: 2, 60s+: 1 |
| ETH | 17 | 7 | 10 | 41.2% | 23s | 88.2% | 0-15s: 6, 15-30s: 7, 30-45s: 1, 45-60s: 1, 60s+: 2 |

BTC is the cleanest weak candidate in this sample: 0 TP / 8 SL across both sides and both lifecycle stages. Sample size is still small, so this is a candidate finding, not a final strategy conclusion.

### Side

| Side | Trades | TP | SL | Win Rate | Median Hold | Fast Close | Hold Buckets |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| YES | 16 | 6 | 10 | 37.5% | 14s | 87.5% | 0-15s: 8, 15-30s: 5, 30-45s: 1, 60s+: 2 |
| NO | 9 | 1 | 8 | 11.1% | 23s | 88.9% | 0-15s: 3, 15-30s: 4, 45-60s: 1, 60s+: 1 |

NO is also a weak candidate. The weakness is not only BTC-driven: ETH + NO + OPENING was 0 TP / 5 SL.

### Lifecycle Stage

| Stage | Trades | TP | SL | Win Rate | Median Hold | Fast Close | Hold Buckets |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| OPENING | 18 | 5 | 13 | 27.8% | 23.5s | 83.3% | 0-15s: 5, 15-30s: 8, 30-45s: 1, 45-60s: 1, 60s+: 3 |
| ACTIVE | 7 | 2 | 5 | 28.6% | 11s | 100.0% | 0-15s: 6, 15-30s: 1 |

ACTIVE is not clearly weaker on win rate than OPENING in this sample. The stronger ACTIVE signal is speed: all ACTIVE trades closed before 30s and 6 / 7 closed within 15s. The observed ACTIVE damage is concentrated in BTC, especially BTC + YES + ACTIVE.

## Price Bucket Diagnostics

| Entry Price Bucket | Trades | TP | SL | Win Rate | Median Hold | Fast Close | Dominant Matrix Cells |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0.40-0.49 | 3 | 0 | 3 | 0.0% | 12s | 100.0% | BTC + YES + ACTIVE, BTC + NO + ACTIVE, ETH + YES + OPENING |
| 0.50-0.59 | 19 | 6 | 13 | 31.6% | 23s | 84.2% | ETH + YES + OPENING, ETH + NO + OPENING, BTC + YES + ACTIVE |
| 0.60+ | 3 | 1 | 2 | 33.3% | 11s | 100.0% | ETH + YES + ACTIVE, BTC + YES + OPENING, ETH + NO + OPENING |

There is no enough evidence yet that a single entry-price bucket explains the failure triangle. The 0.40-0.49 bucket was 0 / 3, but it is too small and partly overlaps with BTC + ACTIVE.

## Answers

### Is BTC Weakness Real?

Verdict: BTC_HOSTILE_CANDIDATE, with insufficient sample warning.

BTC produced 0 TP / 8 SL across all matrix cells. The weakness appears in both YES and NO, and in both OPENING and ACTIVE. This argues against BTC weakness being only a side or lifecycle artifact. The sample is too small for enforcement or strategy change.

### Is NO Weakness Real?

Verdict: NO_SIDE_WEAKNESS_CANDIDATE, with insufficient sample warning.

NO produced 1 TP / 8 SL overall. The most important supporting cell is ETH + NO + OPENING at 0 TP / 5 SL, which shows NO weakness is not only a BTC problem. The lone ETH + NO + ACTIVE winner prevents a clean universal NO failure claim.

### Is ACTIVE Weakness Real?

Verdict: interaction-dependent, not a standalone ACTIVE weakness.

ACTIVE was 2 TP / 5 SL, similar to OPENING by win rate, but every ACTIVE trade was a fast close and 6 / 7 closed in 0-15s. ETH + ACTIVE was 2 / 2 TP, while BTC + ACTIVE was 0 / 5 TP. This points toward ACTIVE as a fast-close/late-entry risk amplifier, especially for BTC, rather than a standalone failure mode.

### Is This Interaction-Only?

Verdict: No.

Interaction matters, but the evidence is not interaction-only. BTC is weak as a single factor, NO is weak as a single factor, and ACTIVE mainly sharpens the fast-close pattern. The two most suspicious interaction cells are:

- BTC + YES + ACTIVE: 0 TP / 4 SL, all 0-15s.
- ETH + NO + OPENING: 0 TP / 5 SL, all fast-close partial coverage.

## Classification

Primary classification: INSUFFICIENT_SAMPLE.

Candidate flags:

- BTC_HOSTILE_CANDIDATE
- NO_SIDE_WEAKNESS_CANDIDATE
- ACTIVE_LATE_ENTRY_CANDIDATE: weak / interaction-dependent only

Rejected as primary:

- INTERACTION_ONLY

Reason: BTC and NO both show standalone weakness, while ACTIVE is mostly an acceleration and interaction signal rather than a standalone win-rate failure.

## Next Action

No field wiring, strategy, risk, stoploss, or runtime change is justified from this sample.

Recommended next research action:

Continue path-truth collection until the Stage A early research gate has enough completed dates, then repeat this matrix with:

- at least 30-45 paired trades,
- at least 10 BTC trades,
- at least 10 NO trades,
- at least 10 ACTIVE trades,
- stable coverage across more than one completed date.

## Status

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Tests run: none. This was a read-only evidence and documentation audit.
