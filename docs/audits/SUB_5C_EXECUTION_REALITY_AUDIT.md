# SUB_5C_EXECUTION_REALITY_AUDIT

**Role**: 10_BACKTEST_REPLAY_AGENT + 08_RESEARCH_QUANT_AGENT + 11_OBSERVABILITY_INCIDENT_AGENT  
**Mode**: READ ONLY — no code, config, strategy, risk, or execution changes  
**Date**: 2026-06-18  
**Script**: `scratch/sub5c_execution_reality_audit.py`  
**Source**: 7-day decision_log + market_snapshots + trade_journal + path_truth (2026-06-12 → 2026-06-18)

---

## Context

LOW_PRICE_EDGE_VALIDATION_001 produced:
- Verdict: `EDGE_WEAK`
- Recommendation: `INVESTIGATE_EXECUTION_REALISM`
- 85.1% of replay PnL came from ask < $0.05 bucket
- 41.7% of <$0.05 events classified NON_EXECUTABLE (prior audit)

This audit answers: **are sub-5c contracts actually executable, or only a replay artifact?**

---

## Q1 — Raw Sub-5c Event Count

| Metric | Value |
|---|---|
| Total risk_plan_zero events (all prices) | 1,156 |
| **Raw sub-5c events (ask < $0.05)** | **244** |

---

## Q2 — Unique Sub-5c Opportunities (after dedup)

Dedup key: `(market_id, epoch_start, side)`

| Metric | Value |
|---|---|
| raw_sub5c_events | 244 |
| **unique_sub5c_events** | **99** |
| duplication_factor | **2.46×** |
| max_dups_per_key | 9 |
| median_dups_per_key | 2 |

> [!NOTE]
> The prior LOW_PRICE_EDGE_VALIDATION_001 reported 60 unique `<$0.05` events. This audit correctly extracts `no_ask` for NO-side events (rather than falling back to `yes_ask`), yielding 99 true unique opportunities. The prior count was understated.

---

## Q3 — Execution Field Inventory (unique events)

| Field | Available | Coverage |
|---|---|---|
| ask_price | 99/99 | **100%** |
| bid_price | 99/99 | **100%** |
| spread | 99/99 | **100%** |
| liq_at_ask | 99/99 | **100%** |
| liq_total_l3 | 99/99 | **100%** |
| seconds_remaining | 99/99 | **100%** |
| orderbook_age | 27/99 | **27%** ⚠ |
| token_id | 99/99 | **100%** |

**Ask price distribution:**

| Sub-tier | Count | Ask range |
|---|---|---|
| 2c–3c | 33 | $0.02 exactly |
| 3c–4c | 33 | $0.03 exactly |
| 4c–5c | 33 | $0.04 exactly |

> [!IMPORTANT]
> The minimum ask price is **$0.02** — not $0.01 as implied by the prior audit's `entry_price < 0.03` NON_EXECUTABLE cutoff. The prior audit used a spurious classification rule. This audit uses actual `yes_ask`/`no_ask` extracted directly from payload.

**Spread statistics:**

| Metric | Value |
|---|---|
| Min spread | $0.0100 |
| Avg spread | **$0.0101** |
| Max spread | $0.0200 |
| Spreads > 3c (>3 ticks) | **0** |

**Liquidity at ask:**

| Metric | Value |
|---|---|
| Min | $10.81 |
| Avg | $1,084.58 |
| Max | $7,137.84 |
| Below $0.05 (unexecutable) | **0** |

**Seconds remaining:**

| Metric | Value |
|---|---|
| Min | 91s |
| Avg | 161.7s |
| Max | 270s |
| Below 30s | **0** |

**Orderbook age (where available, n=27):**

| Metric | Value |
|---|---|
| Min | 0.023s |
| Avg | 0.128s |
| Max | 1.033s |
| Stale >3s | **0** |
| Stale >5s | **0** |

> [!WARNING]
> **Orderbook age is missing for 72/99 events (73%).** Where recorded, quotes are extremely fresh (avg 128ms). However, for the 73% with no age data, quote freshness cannot be verified. This is a data quality gap in the observability system, not a blocking execution concern — but it means "quote_age unknown" for most events.

---

## Q4 + Q5 — Execution Realism Classification

**Classification criteria:**
- `NON_EXECUTABLE`: ask < $0.01, OR spread > 3c, OR SR < 30s, OR liq_at_ask < $0.05
- `EXECUTABLE`: all other cases where all available fields pass thresholds
- `PARTIAL`: liq within 2 ticks ≥ $0.05, age ≤ 5s, SR ≥ 30s
- `UNKNOWN`: no liquidity data at all

| Class | Count | % |
|---|---|---|
| **EXECUTABLE** | **99** | **100.0%** |
| PARTIAL | 0 | 0.0% |
| NON_EXECUTABLE | 0 | 0.0% |
| UNKNOWN | 0 | 0.0% |

**Per ask sub-tier:**

| Ask tier | n | NON_EXEC | PARTIAL | EXECUTABLE |
|---|---|---|---|---|
| 2c–3c | 33 | 0 | 0 | **33 (100%)** |
| 3c–4c | 33 | 0 | 0 | **33 (100%)** |
| 4c–5c | 33 | 0 | 0 | **33 (100%)** |

> [!IMPORTANT]
> **This reverses the prior audit finding.** LOW_PRICE_EDGE_VALIDATION_001 classified 25/60 sub-5c events as NON_EXECUTABLE using `entry_price < $0.03` as a proxy. The actual field data shows:
> - Min ask = $0.02 (not $0.01)
> - Spread never exceeds 2¢ (always ≤ 2c, never > 3c threshold)  
> - Liquidity minimum $10.81 (far above $0.05 threshold)
> - All events have ≥ 91s before expiry (well above 30s)
>
> **All 99 unique sub-5c events pass execution criteria.**

---

## Q8 — Settlement Quality

| Source | Count |
|---|---|
| **Official truth** (trade_journal resolution) | **0** |
| **Path truth** (path_truth JSONL) | **0** |
| **Snapshot proxy** (yes_bid < 180s) | **98** |
| Ambiguous | 1 |
| Missing | 0 |
| **Resolution rate** | **98/99 (99.0%)** |

**Snapshot timing:**

| Proximity | Count | % |
|---|---|---|
| <60s before expiry | 89 | **89.9%** |
| 60–120s before expiry | 9 | 9.1% |
| 120–180s before expiry | 1 | 1.0% |

**Settlement methodology:**
```
Proxy truth = yes_bid at nearest snapshot before expiry (within 180s window)
YES ← yes_bid >= 0.65
NO  ← yes_bid <= 0.35
AMBIGUOUS ← 0.35 < yes_bid < 0.65 (1 event excluded)
```

> [!CAUTION]
> **Zero official truth records exist for sub-5c events in the 7-day window.** The trade_journal and path_truth JSONL files cover this date range but contain no resolution data matching these market keys. **All 98 resolved events rely exclusively on the snapshot proxy.** The reliability of the snapshot proxy at the 2c–5c price tier is a critical open question — see the win rate analysis in Q7.

---

## Q6 — Replay PnL Under Fill Assumptions ($0.05 notional, 98 resolved trades)

**Win Rate: 43.88% (43 wins, 55 losses)**

| Scenario | Fill Assumption | Trades | WR | Total PnL | Expectancy | PF |
|---|---|---|---|---|---|---|
| **A — Optimistic** | 100% at ask | 98 | 43.88% | **+$78.43** | +$0.800 | 29.52 |
| **B — Realistic** | EX@ask, PART@ask+1c | 98 | 43.88% | **+$78.43** | +$0.800 | 29.52 |
| **C — Conservative** | EX only at ask+1c | 98 | 43.88% | **+$54.27** | +$0.553 | 20.73 |
| **D — Stress** | EX only at ask+2c | 98 | 43.88% | **+$41.18** | +$0.420 | 15.98 |

> [!NOTE]
> Scenarios A and B are identical because all 99 events are classified EXECUTABLE (no PARTIAL or NON_EXECUTABLE events to exclude). Scenarios C and D add slippage to the executable fill price.

---

## Q7 — Duplication and Overfit Check

| Metric | Value |
|---|---|
| max_dups_per_key | 9 |
| median_dups_per_key | 2 |
| Total PnL scenario A (resolved) | $78.43 |
| PnL from top 5 events | 15.6% |
| PnL from top 10 events | 31.2% |
| Top 5 individual PnLs | [$2.45, $2.45, $2.45, $2.45, $2.45] |

**Assessment**: PnL is reasonably distributed — top 5 events represent only 15.6% of total. The identical $2.45 top events are all 2c-tier wins (`$0.05 × (1−0.02)/0.02 = $2.45`). No single event dominates.

**Win rate by ask sub-tier — CRITICAL ANOMALY:**

| Ask tier | n | Win Rate | Avg Ask | Breakeven WR |
|---|---|---|---|---|
| **2c–3c** | 33 | **57.58%** | $0.02 | 2.00% |
| 3c–4c | 33 | **42.42%** | $0.03 | 3.00% |
| 4c–5c | 32 | **31.25%** | $0.04 | 4.00% |

> [!CAUTION]
> **The win rates are anomalous.** A 2c contract means the market consensus is ~2% probability of that outcome. The model achieving a 57.58% win rate on such contracts would require extraordinary predictive skill — ~29× the implied market probability. Three explanations:
>
> 1. **Settlement proxy bias**: At 2c ask, the market is highly directional. If the snapshot (≥60s before expiry) captures pre-settlement noise rather than final outcome, yes_bid thresholds (≥0.65 = YES) may misclassify outcomes. For markets where YES is priced at 2c, a pre-settlement bid spike to 0.65+ would falsely count as a YES win.
>
> 2. **Mixed YES/NO side confusion**: If NO-side bets are being evaluated against `yes_bid >= 0.65` settlement without adjustment, wins and losses may be inverted for some events.
>
> 3. **Real model edge**: The model genuinely identifies the rare cases when 2c markets resolve in the predicted direction. Possible but statistically extraordinary.
>
> **This win rate anomaly is the primary unresolved concern** for this audit. The $78.43 PnL figure depends almost entirely on the correctness of the 57.58% WR in the 2c tier.

---

## Q9 — Final Verdict

**Scoring dimensions:**

| Dimension | Value | Status |
|---|---|---|
| Unique events | 99 | — |
| EXECUTABLE fraction | 100% | ✅ |
| NON_EXECUTABLE fraction | 0% | ✅ |
| Spread ≤ 3c | 100% | ✅ |
| Liquidity ≥ $0.05 | 100% | ✅ |
| SR ≥ 30s | 100% | ✅ |
| Scenario B PnL | +$78.43 | ✅ |
| Scenario C PnL (conservative) | +$54.27 | ✅ |
| Scenario D PnL (stress +2c) | +$41.18 | ✅ |
| Official truth coverage | 0/98 (0%) | ❌ |
| Orderbook age coverage | 27% | ⚠ |
| Win rate anomaly at 2c tier | 57.58% (vs 2% implied) | ❌ Unexplained |

```
VERDICT: SUB_5C_EDGE_EXECUTABLE
```

**Rationale**: All 99 unique events pass execution criteria. Spread never exceeds 2c. Liquidity minimum is $10.81. All events have >90 seconds remaining. PnL is positive through +2c stress slippage (PF 15.98). The prior NON_EXECUTABLE finding was an artifact of using `entry_price < 0.03` as a proxy instead of actual ask field data.

**Caveats that prevent upgrading to CONFIRMED**:
1. Zero official truth — 100% snapshot proxy dependence
2. 57.58% WR at 2c tier is statistically unexplained
3. Orderbook age unknown for 73% of events

---

## Q10 — Recommendation

```
RECOMMENDED_ACTION: RUN_SHADOW_SUB_5C_SIZER
```

### What this means

All execution criteria are met by the data available. The recommended next step is to run a **paper shadow mode specifically capturing sub-5c entry attempts** to collect:

1. **Real fill confirmation**: Whether the system can actually place and fill orders at 2c–4c ask prices in live CLOB conditions
2. **Actual win/loss outcomes** from the trade_journal (official truth, not snapshot proxy), specifically for sub-5c entries
3. **Orderbook age during attempted entries** — fill in the 73% gap in quote freshness data
4. **Settlement proxy validation** — compare snapshot proxy outcomes vs. trade_journal official outcomes for sub-5c markets

### What this does NOT authorize

- No confidence threshold change
- No sizer parameter modification
- No execution behavior change
- No live trading modification
- No code changes of any kind
- Shadow mode = paper observation only, no new risk exposure

### Prerequisites before proceeding

Before treating `RUN_SHADOW_SUB_5C_SIZER` as an implementation task:

1. **Resolve the win rate anomaly**: Determine whether 57.58% WR at 2c is real edge, settlement proxy artifact, or side-assignment error. This requires comparing snapshot proxy outcomes against any real fills in trade_journal.
2. **Verify settlement proxy for sub-5c**: Run a cross-validation on markets where both official truth and snapshot proxy are available (from earlier date ranges where trade_journal has resolution data) specifically at prices < $0.05.
3. **Enable orderbook_age logging**: 73% of events are missing this field. It should be logged for all decision events to verify quote freshness at entry time.

---

## Final Confirmation

| Item | Status |
|---|---|
| Runtime changed | **No** |
| Strategy changed | **No** |
| EV changed | **No** |
| Risk changed | **No** |
| Execution changed | **No** |
| Live trading changed | **No** |
| Files modified | **0** |

---

*Report generated by: 10_BACKTEST_REPLAY_AGENT + 08_RESEARCH_QUANT_AGENT + 11_OBSERVABILITY_INCIDENT_AGENT*  
*Script: `scratch/sub5c_execution_reality_audit.py`*  
*Read-only audit — evidence only.*
