# Overnight Maturity Check - 2026-05-19

Scope: read-only audit of latest paper session evidence after orderbook fix and identity continuity instrumentation.

Run checked: `20260518T133028Z_1724_5d277d50`

UTC period: `2026-05-18T13:30:30.210496Z` to `2026-05-18T23:16:48.020400Z`

Evidence source: `runtime/quant_data/*/2026-05-18.jsonl`

Runtime behavior changed: No

Live behavior changed: No

## Summary Verdict

Overnight evidence accumulation improved materially for S3-style replay readiness on identity continuity and paired trade evidence, but it is not mature enough for S3 promotion. The session now has real paper position lifecycle evidence: 4 opened, 4 closed, 0 unresolved, and 100% open-to-close replay key matching. However, all closed positions failed by stop loss, take-profit evidence is absent, canonical MFE/MAE fields are still mostly placeholders, and the sample is too small to support bounded inventory or live-risk conclusions.

S3 maturity status: CAUTION - improved toward S3, not S3-ready.

Next bottleneck: outcome-quality plus replay-depth maturity. The new identity continuity is good enough to pair trades, but the next proof needs more positions, non-stop-loss exits, and MFE/MAE truth fields that can explain whether exits failed because of adverse selection, timing, stop settings, or market regime.

## 1. Position Maturity

Total positions: 4

Positions opened: 4

Positions closed: 4

Open positions: 0

ETH vs BTC split:

| Asset | Opens | Closes |
|---|---:|---:|
| ETH | 3 | 3 |
| BTC | 1 | 1 |

Exit outcomes:

| Metric | Count |
|---|---:|
| stop_loss | 4 |
| take_profit | 0 |
| survived | 0 |
| stabilized estimate | 0 |
| failed | 4 |
| unresolved | 0 |

Close reason distribution:

| Reason | Count |
|---|---:|
| stop_loss | 3 |
| stop_loss_hit | 1 |

PnL from closed paper positions: `-0.02556092`

Hold time range: 3 to 12 seconds.

Interpretation: position lifecycle collection is now alive, but position maturity is weak. These were short-lived stop-loss exits, not stable inventory examples.

## 2. Paired Evidence Quality

| Metric | Value |
|---|---:|
| trade_open count | 4 |
| trade_close count | 4 |
| paper_trade_replay_key coverage | 8/8 |
| open-close matched pairs | 4 |
| open-close matching rate | 100% |
| missing replay keys | 0 |
| unmatched open keys | 0 |
| unmatched close keys | 0 |

Pair continuity:

| Continuity Check | Rate |
|---|---:|
| inventory_context_id open-close match | 100% |
| candidate_id open-close match | 100% |
| parent_candidate_trace_id open-close match | 100% |
| lifecycle_instance_id open-close match | 100% |

Candidate trace coverage by producer:

| Producer | candidate_trace_id coverage | inventory_context_id coverage |
|---|---:|---:|
| trade_journal | 8/8 | 8/8 |
| decision_log | 851/851 | 851/851 |
| risk_log | 847/1747 | 847/1747 |
| execution_log | 4945/4945 | 4945/4945 |
| market_snapshots | 4729/4729 | 4729/4729 |

Lineage confidence distribution:

| Confidence | Count |
|---|---:|
| DIRECT | 6459 |
| WEAK | 4921 |
| UNKNOWN | 900 |

Interpretation: paired trade evidence is the strongest improvement. Replay key, inventory context, candidate id, parent trace, and lifecycle id all matched for the 4 open-close pairs. Risk-log coverage is still partial because 900 risk events are generic cycle/risk-state events without candidate identity.

## 3. Runtime Health

Event volume for run:

| Producer | Events |
|---|---:|
| system_health | 6934 |
| execution_log | 4945 |
| market_snapshots | 4729 |
| research_log | 2363 |
| risk_log | 1747 |
| decision_log | 851 |
| trade_journal | 8 |

Orderbook decision evidence:

| Metric | Value |
|---|---:|
| orderbook_available_for_decision=true | 851 |
| orderbook_state_classification=ready | 851 |
| confidence > 0 count | 123 |

orderbook_availability_classification:

| Class | Count |
|---|---:|
| orderbook_available_but_skipped_by_cutoff | 686 |
| orderbook_available_but_skipped | 165 |

MODEL_GATE distribution:

| Gate | Count |
|---|---:|
| MODEL_READY | 851 |

RISK_GATE distribution:

| Risk state | Count |
|---|---:|
| missing | 900 |
| not_reached | 728 |
| blocked | 119 |

Risk mode and survival activity:

| Metric | Count |
|---|---:|
| MICRO_SURVIVAL activity | 1391 |
| MICRO_RECOVERY activity | 572 |
| DEFENSIVE activity | 690 |

Interpretation: orderbook availability improved enough that decision records consistently saw ready orderbooks. The active bottleneck shifted away from missing orderbook data and toward timing, risk boundary, and outcome quality. MODEL_READY is visible, but many decisions still do not reach actionable risk approval.

## 4. Market Split

BTC:

| Metric | Value |
|---|---:|
| attempts | 408 |
| entries | 1 |
| blocks | 408 |
| confidence range | 0.00 to 0.88 |

BTC top block reasons:

| Reason | Count |
|---|---:|
| time_unsafe | 339 |
| risk_plan_zero | 69 |

ETH:

| Metric | Value |
|---|---:|
| attempts | 443 |
| entries | 3 |
| blocks | 443 |
| confidence range | 0.00 to 0.88 |

ETH top block reasons:

| Reason | Count |
|---|---:|
| time_unsafe | 345 |
| risk_plan_zero | 50 |
| frequency_cooldown | 45 |
| stale_data | 3 |

Interpretation: ETH produced more paper entries than BTC, but both assets remain dominated by late-window cutoff and zero-size/risk blocking. Confidence is present, but actionable conversion remains low.

## 5. MFE/MAE Placeholder Coverage

Requested fields:

| Field | Coverage Count |
|---|---:|
| mfe_price | 0 |
| mae_price | 0 |
| peak_favorable_seen | 0 |
| peak_adverse_seen | 0 |

Related candidate placeholder fields:

| Field | Coverage Count |
|---|---:|
| mfe_candidate_price | 4 |
| mae_candidate_price | 4 |
| candidate_peak_favorable | 855 |
| candidate_peak_adverse | 855 |

Interpretation: MFE/MAE is not replay-ready under the canonical requested field names. Candidate-level placeholders exist, but the direct `mfe_price`, `mae_price`, `peak_favorable_seen`, and `peak_adverse_seen` fields have zero coverage in this scoped run.

## 6. S3 Determination

Did overnight evidence accumulation improve enough toward S3?

Answer: Yes toward S3, but no for S3 maturity.

Improved:

- Real paper position lifecycle evidence exists.
- Open-close pairing is complete for the session.
- `paper_trade_replay_key` coverage is complete for trade journal events.
- Inventory context continuity is complete across matched trade pairs.
- Candidate trace continuity is complete for decision, execution, market snapshot, and trade journal producers.
- Orderbook availability is no longer the dominant blocker in scoped decision evidence.

Not mature enough:

- Only 4 total positions.
- All 4 closed by stop loss.
- No take-profit or survived-position sample.
- Canonical MFE/MAE fields have zero direct coverage.
- Risk boundary still has partial candidate identity coverage and many `not_reached` or generic risk events.
- Timing cutoff remains the dominant decision bottleneck.

Replay readiness: PARTIAL. Good for pairing and lifecycle reconstruction of paper opens/closes; not enough for robust S3 inventory replay or promotion claims.

## 7. Exactly Three Future Options

### OPTION 1 - SAFE EV PRESERVATION

Thesis: keep runtime unchanged and collect another paper session with the same safeguards to test whether the stop-loss cluster is a sample artifact or persistent exit-quality problem.

Quant logic: protects bankroll and preserves the current risk/cutoff system while gathering more paired open-close examples. Fill probability is no longer the primary unknown; outcome distribution is.

Likely outcome: more cleanly paired trades, with the next key signal being whether any position survives beyond the 3 to 12 second stop-loss window.

Hidden risk: if stop-loss exits dominate again, the system may be collecting excellent identity evidence for a structurally poor entry/exit loop.

Recommended action: run another paper collection window and compare stop-loss share, hold seconds, and MFE/MAE coverage.

### OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY

Thesis: run offline-only replay diagnostics on this run to isolate whether stop-loss failures were caused by spread, late entry, adverse movement, or entry-side mismatch.

Quant logic: higher information gain without runtime changes. The target is not profitability; it is explaining why 100% of realized positions failed despite ready orderbooks and complete pairing.

Likely outcome: evidence will separate microstructure failure from timing failure, especially for ETH where entries were more frequent.

Hidden risk: replay without canonical MFE/MAE fields may over-rely on proxy fields and understate path risk.

Recommended action: generate run-scoped replay/no-entry reports for `20260518T133028Z_1724_5d277d50` and explicitly label proxy-vs-direct evidence.

### OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

Thesis: assume the visible stop-loss cluster is a symptom of deeper lifecycle mismatch: decisions often become model-ready too late, risk is not reached often enough, and open positions close before stabilization evidence can accumulate.

Quant logic: the structural bottleneck may be candidate timing, inventory handoff, or exit pressure rather than orderbook availability. This matters before any bounded inventory research because reload/unload logic cannot be trusted if starter entries fail immediately.

Likely outcome: the next scaling blocker will be position lifecycle quality, not identity continuity.

Hidden risk: S3 promotion based only on clean replay keys would overstate maturity and ignore that all realized lifecycle outcomes failed.

Recommended action: make the next bottleneck review focus on first tradable second, first model output second, risk reached/not reached, hold_seconds, and stop-loss path evidence.

## Final Status

Total positions: 4

Paired evidence status: strong for trade journal pairing, partial across all producers.

Replay readiness: partial, improved, not sufficient for S3 promotion.

S3 maturity status: CAUTION - not ready.

Next bottleneck: explain and reduce the 100% stop-loss cluster while adding direct MFE/MAE coverage.

Runtime behavior changed: No

Live behavior changed: No
