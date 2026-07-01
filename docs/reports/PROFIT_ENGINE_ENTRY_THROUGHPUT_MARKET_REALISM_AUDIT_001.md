# PROFIT_ENGINE_ENTRY_THROUGHPUT_MARKET_REALISM_AUDIT_001

## Final Verdict

ENTRY_THROUGHPUT_TOO_LOW_AND_MARKET_REALISM_PARTIAL_NO_TUNING_JUSTIFIED.

The current paper system is stable enough to produce accounting evidence, but not yet market-realistic enough to support a profitability claim. The best recent 60-minute baseline produced 2 entries from 120 decisions (1.7% entry rate, about 2 entries/hour), both ETH YES positions that stopped out within 27-29 seconds for total session PnL of -$0.042647. The later 60-minute take-profit evidence run produced 0 entries from 120 decisions, so it did not test take-profit reachability.

The zero-entry run was not caused by one obviously wrong gate. Offline counterfactual replay found 5 one-gate-relaxed core candidates and 0 strong clean candidates after caveats. The cleanest design bottleneck is `risk_plan_zero`, where selected-side probability is used as active sizing confidence and blocks cheap high-EV rows. That is a semantic mismatch, but still protective under current low-price truth governance.

No runtime, strategy, sizing, risk, execution, config, `.env`, paper, or live behavior changed.

## Source Evidence

| Source | Evidence Grade | Use |
|---|---|---|
| `docs/reports/PAPER_RUNTIME_LONG_VALIDATION_BASELINE_001.md` | A | 60-minute paper baseline, entries, closes, PnL, accounting, live markers. |
| `docs/reports/TAKE_PROFIT_EXIT_EVIDENCE_001.md` | A | 60-minute zero-entry TP evidence run. |
| `docs/reports/PAPER_ENTRY_SAMPLE_QUALITY_FOR_TP_EVIDENCE_001.md` | B | Blocker breakdown and near-miss analysis. |
| `docs/reports/ENTRY_GATE_COUNTERFACTUAL_REPLAY_001.md` | B | Offline one-gate-relaxed candidate counts. |
| `docs/reports/RISK_PLAN_ZERO_SIDE_CONFIDENCE_SEMANTICS_AUDIT_001.md` | B | Side-confidence versus top-level confidence lineage. |
| `runtime/quant_data/*/2026-06-30.jsonl` run-scoped rows | A | Confirmed decision, trade, execution, risk, market snapshot counts. |
| `polymarket/position_sizing.py`, `polymarket/order_manager.py`, `polymarket/trader.py`, `config/settings.py` | B | Sizing and market-realism source inspection. |

## Role Routing

| Role | Selection |
|---|---|
| Primary | `14_NO_ENTRY_DIAGNOSTICS_AGENT` |
| Supporting | `16_PAPER_EVALUATION_AGENT`, `21_EXECUTION_MICROSTRUCTURE_AGENT`, `11_OBSERVABILITY_INCIDENT_AGENT` |
| Reason | The audit is about no-entry/low-throughput causes, paper evidence sufficiency, executable market quality, and observability validity. |
| Files intentionally not changed | Runtime Python, strategy/risk/sizing/execution modules, `config/settings.py`, `.env`, runtime state. |

## Entry Throughput Summary

| Metric | Baseline run `20260630T104339Z_52084_999c4023` | TP evidence run `20260630T135455Z_6592_5fac8cf4` | Verdict |
|---|---:|---:|---|
| Duration | 60.6 min | 60 min | Comparable 1-hour samples |
| Decisions | 120 | 120 | Adequate for gate counting, not expectancy |
| Assets scanned | BTC 60 / ETH 60 | BTC 60 / ETH 60 | Both target assets covered |
| Trade opens | 2 | 0 | Too low for TP/profit inference |
| Trade closes | 2 | 0 | Close path proven only in baseline |
| Entry rate/hour | about 2.0 | 0.0 | Insufficient |
| Close rate/hour | about 2.0 | 0.0 | Insufficient |
| Net PnL | -$0.042647 | $0.00 realized | No positive expectancy evidence |
| Live markers | 0 | 0 | Paper/live safety preserved |

Unknown or incomplete: active market count and tradable market count are partially observable through market snapshots, but there is no single canonical funnel row with all counts in one place.

## Gate Blocker Analysis

### Baseline Run

| Blocker | Count | Classification | Interpretation |
|---|---:|---|---|
| `delta_extreme` | 45 | LIKELY_PROTECTIVE | Avoids chasing extended 5-minute moves; needs shadow path truth before relaxing. |
| `risk_mode_defensive:confidence_below_defensive` | 16 | HARD_PROTECTIVE | Activated after two stop-losses; capital protection worked. |
| time/cutoff variants | 17+ | HARD_PROTECTIVE | Late or hard-close-zone entries are not valid profit samples. |
| `confidence_too_low` | 7 | LIKELY_PROTECTIVE | Weak signal rows. |
| `clob_empty_response` | 7 | HARD_PROTECTIVE | No executable book. |
| `ev_below_threshold` | 3 | HARD_PROTECTIVE | Zero/subthreshold EV. |
| `risk_plan_zero` | 3 | POSSIBLY_OVER_CONSERVATIVE | Same semantic family as later run; needs shadow outcome evidence, not tuning. |

### TP Evidence Run

| Blocker | Count | Share | Classification | Interpretation |
|---|---:|---:|---|---|
| `delta_extreme` | 44 | 36.7% | POSSIBLY_OVER_CONSERVATIVE | Largest gate; only 2 one-gate-relaxed core candidates, both with THIN liquidity. |
| `confidence_too_low` | 21 | 17.5% | LIKELY_PROTECTIVE | Counterfactual produced 0 viable rows because EV was zero/subthreshold. |
| `risk_plan_zero` | 17 | 14.2% | POSSIBLY_OVER_CONSERVATIVE | Cleanest semantic bottleneck; 2 core candidates, 0 strong clean after caveats. |
| `time_unsafe` | 17 | 14.2% | HARD_PROTECTIVE | Late-window / final-zone protection. |
| `clob_empty_response` | 13 | 10.8% | HARD_PROTECTIVE | Non-executable or unavailable books. |
| `ev_below_threshold` | 8 | 6.7% | HARD_PROTECTIVE | Relaxing EV would admit zero-EV rows. |

No gate currently has enough evidence for threshold relaxation.

## Market-Time Truth Verdict

Verdict: PARTIAL_VALIDITY.

Current logs contain useful lifecycle timing fields such as `timestamp_utc`, `epoch_start_ts`, `epoch_end_ts`, `seconds_remaining`, `candidate_seen_ts`, `candidate_survival_ms`, `decision_cycle_started_at`, `book_to_tradable_seconds`, `last_orderbook_refresh_at`, `last_successful_yes_no_book_at`, and `quote_age_ms` in some streams.

However, run-scoped JSONL rows generally do not emit the exact new standard field names from `11_LOGGING_AND_MARKET_TIME_TRUTH.md`, including `market_window_start_utc`, `market_window_end_utc`, `chainlink_reference_ts_utc`, `source_orderbook_ts_utc`, `local_receive_ts_utc`, `decision_ts_utc`, `order_submit_ts_utc`, `order_ack_ts_utc`, `fill_ts_utc`, `close_ts_utc`, `settlement_ts_utc`, `data_age_ms`, `decision_latency_ms`, `submit_latency_ms`, `fill_latency_ms`, and `clock_drift_status`.

Impact: the evidence is valid for directional bottleneck diagnosis and paper accounting checks, but only partial for profit analysis that depends on precise market-time alignment and latency.

## Market Realism Verdict

| Dimension | Status | Evidence / Gap |
|---|---|---|
| Market slug/window rollover | PARTIALLY_MODELED | MAE exact-slug repair exists; logs include slug/epoch fields, but prior false-negative/stale token issues show this remains a critical watch item. |
| Up/Down token IDs | MODELED | Token IDs appear in decision/trade/execution context. |
| Price-to-beat/opening reference | PARTIALLY_MODELED | PTB and epoch fields exist; exact Chainlink/reference timestamp standard is incomplete. |
| Final reference/settlement truth | PARTIALLY_MODELED | Close/PnL path works; full settlement truth is not consistently joined to near-miss rows. |
| Tick size | UNKNOWN | Not proven in current paper evidence. |
| Minimum order size | PARTIALLY_MODELED | `$0.10` micro notional is configured, but whole-share/fractional CLOB reality remains unresolved. |
| Fractional share reality | NOT_PROVEN | Paper opens used fractional shares such as 0.196078 and 0.208333. Live CLOB acceptance is not proven. |
| Fees | PARTIALLY_MODELED | Backtester has fee assumptions; active runtime paper PnL evidence does not prove live fee realism. |
| Spread | MODELED | Spread and spread gates are logged/used. |
| Slippage | PARTIALLY_MODELED | Exit slippage guard exists; paper entry fills still simulate at available prices without live fill proof. |
| Taker delay | UNKNOWN | Not established in current evidence. |
| Orderbook freshness | PARTIALLY_MODELED | Freshness fields exist under current names; new standard names incomplete. |
| Liquidity/depth | MODELED | Depth/readiness fields and liquidity multipliers exist. |
| Partial fills | NOT_PROVEN | Paper validation has no partial-fill evidence. |
| Live-vs-paper execution | NOT_PROVEN | Live placement/fill/cancel/reconcile cycle remains unvalidated. |

## Position Sizing Reality Verdict

Verdict: PARTIAL_REALISM_FOR_PAPER_ACCOUNTING_ONLY.

Current active sizing is bankroll-rank based, not fixed 2% sizing. `PolymarketOrderManager` passes `OrderRequest` into `calculate_position_size`, which applies bankroll tier, confidence, EV, drawdown, liquidity, spread, time-to-settlement, delta, and frequency multipliers.

In micro-survival paper mode, the runtime permits fractional shares and uses a micro notional floor. Current settings show `micro_survival_min_position_size = 0.10`, `micro_survival_risk_fraction = 0.0025`, and `min_shares_per_order = 1`. The baseline paper opens were `$0.10` notional at entry prices `0.51` and `0.48`, creating fractional shares `0.196078` and `0.208333`.

This is useful for testing state accounting, trade journals, PnL math, and exposure cleanup. It is not enough to trust live PnL until fractional-share acceptance, minimum order behavior, fee/slippage treatment, and partial-fill behavior are proven.

## EV / Cost Model Gaps

| Component | Availability | Notes |
|---|---|---|
| `q` / estimated fair probability | AVAILABLE | Probability fields and fair-value fields exist in decision/trade rows. |
| `p` / market price | AVAILABLE | Ask/entry/market price fields exist. |
| EV per share | AVAILABLE | `ev`, `expected_value`, and `ev_after_spread` are present in key rows. |
| EV per order | PARTIAL | Can be derived where size is nonzero; not canonical across skips. |
| Spread | AVAILABLE | Used in gates and logs. |
| Liquidity/depth | AVAILABLE | Depth and liquidity states exist. |
| Fee | PARTIAL | Config/backtester assumptions exist; active runtime paper PnL does not prove fee realism. |
| Slippage | PARTIAL | Exit slippage guard exists; entry slippage/live fill quality not proven. |
| Latency penalty | PARTIAL | Some latency/lifecycle proxies exist; exact standard fields incomplete. |
| Uncertainty buffer | PARTIAL | Confidence/evidence fields exist; no canonical cost buffer row. |
| Expected drawdown/risk budget | PARTIAL | Risk mode and drawdown rows exist; profit-engine risk budget needs a canonical dashboard view. |

## Trade Outcome Quality

Recent real paper lifecycle evidence is thin:

| Position | Asset/Side | Entry | Exit | Hold | Exit reason | PnL | Quality |
|---|---|---:|---:|---:|---|---:|---|
| `3fdd7312` | ETH YES | 0.51 | 0.42 | 27s | `stop_loss` | -$0.017647 | Accounting valid; market timing truth partial. |
| `78725623` | ETH YES | 0.48 | 0.36 | 29s | `stop_loss` | -$0.025000 | Accounting valid; market timing truth partial. |

Take-profit count in the latest TP evidence run: 0. Stop-loss count in the latest TP evidence run: 0, because no entries opened. MFE/MAE exists only partially through path truth checkpoints and is not yet joined into a canonical profit evaluation table for near-misses.

## Dashboard Data Availability

| Dashboard Section | Status | Rationale |
|---|---|---|
| Profit Engine Header | PARTIAL | Mode, PnL, positions, risk mode exist; current bottleneck needs canonical summary. |
| Trade Funnel | PARTIAL | Decisions/fills/closes exist; candidates/EV pass/risk approved/order intents need one canonical funnel row. |
| Gate Blocker Board | AVAILABLE | Blocker counts and near-misses are available from decision logs/reports. |
| Quant Metrics Board | PARTIAL | Win rate/PnL/hold time available for tiny samples; expectancy/PF/MFE/MAE not trustworthy yet. |
| Market/Sizing Reality Board | PARTIAL | Spread/liquidity/sizing mode available; tick/min-order/fractional/fees/slippage/live mismatch not fully proven. |
| Time Truth Board | PARTIAL | Current timing proxies exist; standard field names and latency fields incomplete. |
| Operator Action Panel | AVAILABLE | Current action can be produced from reports: do not tune; run shadow outcome replay/time-truth hardening. |

## Evidence Validity

| Evidence Use | Validity |
|---|---|
| Runtime stability / paper safety | VALID |
| Paper accounting open-close-cash-exposure | VALID |
| Entry blocker diagnosis | VALID_WITH_SAMPLE_LIMITS |
| Profitability / expectancy | INVALID_FOR_PROFIT_CLAIM |
| Take-profit reachability | UNKNOWN |
| Live execution realism | INVALID |
| Market-time precise profit attribution | PARTIAL_VALIDITY |
| Sizing realism for live | PARTIAL / NOT_PROVEN |

## Blockers To Fix First

1. Market-time truth standardization: emit or map exact canonical timing fields for decision, orderbook, submit, fill, close, and settlement.
2. Shadow outcome evidence for `risk_plan_zero` and `delta_extreme` near-misses: join post-decision MFE/MAE, TP-hit, SL-hit, and settlement truth without changing runtime.
3. CLOB fractional-share/minimum-order validation: prove whether `$0.10` fractional-share paper fills can exist in real CLOB mechanics.
4. Canonical trade funnel snapshot: one compact per-run summary for decisions -> candidates -> EV pass -> risk approved -> order intents -> fills -> closes.
5. Cost realism: explicitly account for fees, slippage, taker delay, and latency penalty before using paper PnL as profit evidence.

## Do Not Change Yet

- Do not relax `delta_extreme`.
- Do not lower confidence floors.
- Do not change risk-plan confidence semantics.
- Do not increase sizing.
- Do not enable ladders or ADD logic.
- Do not infer take-profit viability from zero-entry runs.
- Do not use current paper PnL as live-profit evidence.

## Future Options

| Option | Path | Trade-off |
|---|---|---|
| OPTION 1 - SAFE EV PRESERVATION | Keep runtime unchanged and harden dashboard/time-truth summaries first. | Lowest risk, improves evidence quality before any policy work. |
| OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY | Offline shadow outcome replay for `risk_plan_zero` and `delta_extreme` near-misses. | Best information gain without changing entries. |
| OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH | Design a canonical market-realism contract covering tick/min-order/fractional/fees/slippage/latency/partial fills. | Slower, but prevents paper/live mismatch from contaminating future research. |

Recommended path: OPTION 2 next, with Option 1 time-truth/dashboard standardization running before any runtime tuning.

## Next Runtime Task

`RISK_PLAN_ZERO_SEMANTIC_C_SHADOW_REPLAY_001`

Scope:

- Offline replay only.
- Use existing `zero_size_probe_v1` and decision-log near-miss rows.
- Join MFE/MAE, TP-hit, SL-hit, settlement/path truth where available.
- Compare active zero-size decisions against shadow nonzero-size candidates.
- No runtime, strategy, sizing, risk, execution, config, `.env`, paper, or live behavior changes.

## Safety Verdict

SAFE_READ_ONLY_AUDIT. This task inspected docs, historical JSONL, and source files for evidence. It created documentation and operations metadata only. It did not modify runtime behavior.

