# DECISION_ENGINE_PROTOTYPE_BATCH_VALIDATION_001

## Verdict

OFFLINE_VALIDATION_COMPLETE. The prototype was evaluated as a diagnostic layer only; no runtime trading behavior was changed.

## Inputs

- Schema version: `decision_engine_batch_validation.v1`
- Source files: 4
- Total lines read: 1794
- Parse errors skipped: 0
- `runtime\reports\canonical_trade_context_20260523.jsonl`
- `runtime\reports\canonical_trade_context_20260531.jsonl`
- `runtime\reports\canonical_trade_context_20260614.jsonl`
- `runtime\reports\canonical_trade_context_20260627.jsonl`

## Total Rows Evaluated

1794

## Decision State Counts

| decision_state | count |
|---|---:|
| `REJECT_MISSING_CONTEXT` | 907 |
| `REVIEW_REQUIRED` | 886 |
| `REJECT_LOW_EVIDENCE` | 1 |

## Confidence Distribution

| confidence | count |
|---|---:|
| `LOW` | 908 |
| `MEDIUM` | 886 |

## Missing Field Counts

| missing_field | count |
|---|---:|
| `bankroll_rank` | 1794 |
| `blockers` | 1794 |
| `capital_score` | 1794 |
| `expected_pnl_at_entry` | 1794 |
| `market_exposure_after` | 1794 |
| `market_exposure_before` | 1794 |
| `max_daily_loss_usd` | 1794 |
| `max_open_exposure_usd` | 1794 |
| `max_order_usd` | 1794 |
| `open_position_count` | 1794 |
| `realized_pnl_before` | 1794 |
| `size_sharp_at_entry` | 1794 |
| `size_sharp_boosts` | 1794 |
| `size_sharp_component_scores` | 1794 |
| `size_sharp_hard_caps` | 1794 |
| `size_sharp_missing_inputs` | 1794 |
| `size_sharp_penalties` | 1794 |
| `unrealized_pnl_before` | 1794 |
| `decision_score` | 1753 |
| `signal_name` | 1601 |
| `bankroll` | 908 |
| `bankroll_tier_id` | 908 |
| `equity` | 908 |
| `quote_age_ms` | 908 |
| `ev` | 907 |

## Reject Reason Counts

| reject_reason | count |
|---|---:|
| `missing_required_context` | 907 |
| `low_evidence_quality` | 1 |

## Evidence Quality Summary

### Evidence Status

| status | count |
|---|---:|
| `FAIL` | 908 |
| `PASS` | 885 |
| `REVIEW` | 1 |

### Data Quality Grades

| grade | count |
|---|---:|
| `D` | 908 |
| `A` | 885 |
| `B` | 1 |

### Join Confidence

| join_confidence | count |
|---|---:|
| `LOW` | 908 |
| `HIGH` | 886 |

## Quality Subsystems

### Probability Quality

| status | count |
|---|---:|
| `MISSING` | 905 |
| `PASS` | 889 |

### EV Quality

| status | count |
|---|---:|
| `MISSING` | 907 |
| `PASS` | 887 |

### Liquidity Quality

| status | count |
|---|---:|
| `PASS` | 1794 |

### Availability Quality

| status | count |
|---|---:|
| `FAIL` | 907 |
| `REVIEW` | 887 |

## Examples

### PASS_CONTEXT

Not observed in this batch.

### REJECT_MISSING_CONTEXT

- `{"confidence": "LOW", "data_quality_grade": "D", "decision_state": "REJECT_MISSING_CONTEXT", "event_classification": "unknown_legacy", "join_confidence": "LOW", "missing_fields": ["true_probability", "ev_after_spread", "position_id", "replay_key", "signal_name", "probability", "fair_value", "ev", "decision_score", "reason_codes"], "outcome": "NO", "position_id": null, "reject_reasons": ["missing_required_context"], "ticker": "ETH", "trade_id": "ct_8771257d3a797099be0f"}`
- `{"confidence": "LOW", "data_quality_grade": "D", "decision_state": "REJECT_MISSING_CONTEXT", "event_classification": "unknown_legacy", "join_confidence": "LOW", "missing_fields": ["true_probability", "ev_after_spread", "position_id", "replay_key", "signal_name", "probability", "fair_value", "ev", "decision_score", "reason_codes"], "outcome": "NO", "position_id": null, "reject_reasons": ["missing_required_context"], "ticker": "ETH", "trade_id": "ct_6c129f1f92381dff7426"}`
- `{"confidence": "LOW", "data_quality_grade": "D", "decision_state": "REJECT_MISSING_CONTEXT", "event_classification": "unknown_legacy", "join_confidence": "LOW", "missing_fields": ["ev_after_spread", "replay_key", "signal_name", "ev", "decision_score", "blockers", "quote_age_ms", "bankroll", "equity", "realized_pnl_before"], "outcome": "NO", "position_id": "ce17ff61", "reject_reasons": ["missing_required_context"], "ticker": "ETH", "trade_id": "ct_46fedb17f48f8cd45108"}`

### REJECT_BAD_PROBABILITY

Not observed in this batch.

### REJECT_BAD_EV

Not observed in this batch.

### REJECT_LOW_EVIDENCE

- `{"confidence": "LOW", "data_quality_grade": "D", "decision_state": "REJECT_LOW_EVIDENCE", "event_classification": "unknown_legacy", "join_confidence": "LOW", "missing_fields": ["position_id", "signal_name", "decision_score", "reason_codes", "blockers", "realized_pnl_before", "unrealized_pnl_before", "bankroll_rank", "max_order_usd", "max_daily_loss_usd"], "outcome": "NO", "position_id": null, "reject_reasons": ["low_evidence_quality"], "ticker": "ETH", "trade_id": "ct_eb492f8d852f71693d57"}`

### REVIEW_REQUIRED

- `{"confidence": "MEDIUM", "data_quality_grade": "A", "decision_state": "REVIEW_REQUIRED", "event_classification": "signal_driven_trade", "join_confidence": "HIGH", "missing_fields": ["position_id", "signal_name", "decision_score", "blockers", "realized_pnl_before", "unrealized_pnl_before", "bankroll_rank", "max_order_usd", "max_daily_loss_usd", "max_open_exposure_usd"], "outcome": "YES", "position_id": null, "reject_reasons": [], "ticker": "BTC", "trade_id": "ct_7226e683d8c723122738"}`
- `{"confidence": "MEDIUM", "data_quality_grade": "A", "decision_state": "REVIEW_REQUIRED", "event_classification": "signal_driven_trade", "join_confidence": "HIGH", "missing_fields": ["position_id", "signal_name", "decision_score", "blockers", "realized_pnl_before", "unrealized_pnl_before", "bankroll_rank", "max_order_usd", "max_daily_loss_usd", "max_open_exposure_usd"], "outcome": "YES", "position_id": null, "reject_reasons": [], "ticker": "BTC", "trade_id": "ct_ddbb30bd886d32a4eebe"}`
- `{"confidence": "MEDIUM", "data_quality_grade": "A", "decision_state": "REVIEW_REQUIRED", "event_classification": "signal_driven_trade", "join_confidence": "HIGH", "missing_fields": ["position_id", "signal_name", "decision_score", "blockers", "realized_pnl_before", "unrealized_pnl_before", "bankroll_rank", "max_order_usd", "max_daily_loss_usd", "max_open_exposure_usd"], "outcome": "NO", "position_id": null, "reject_reasons": [], "ticker": "BTC", "trade_id": "ct_8731211ff45ec4c12b02"}`

## Limitations

- This is an offline diagnostic distribution, not a trading policy or runtime approval layer.
- `PASS_CONTEXT` means the row has sufficient context for the prototype's conservative validation checks only.
- Missing-field counts include canonical row metadata and prototype-required context fields.
- Observed distributions depend on available canonical JSONL outputs and may change as context quality improves.
- No strategy thresholds, risk sizing, execution, wallet, live/paper runtime, `.env`, or config behavior was changed.

## Next Task

`DECISION_ENGINE_PROTOTYPE_EDGE_CASE_FIXTURE_AUDIT_001` - add targeted fixture validation for decision states not observed in real canonical rows, if any remain unobserved.
