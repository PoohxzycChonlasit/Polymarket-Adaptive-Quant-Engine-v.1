# SHADOW_SIZING_REPLAY_AUDIT_001

**Role Routing:**
- Primary: 10_BACKTEST_REPLAY_AGENT
- Supporting: 08_RESEARCH_QUANT_AGENT
- Mode: READ ONLY — No code changes made

---

## Objective

Validate whether the 68 confidence-floor blocked candidates would have produced positive executable expectancy at $0.05 micro position size.

---

## Methodology

| Step | Action |
|------|--------|
| Population | 68 events with `raw_skip_reason = confidence_too_low` (June 17–18) |
| Side selection | Model-probability-driven: YES if `model_prob_yes > model_prob_no` |
| Entry price | `yes_ask` (YES side) or `no_ask` (NO side) |
| Position size | $0.05 USDC per candidate |
| Resolution source | `market_snapshots` `yes_bid` at minimum `seconds_remaining` |
| Resolution rule | `yes_bid ≥ 0.70` → YES resolved; `yes_bid ≤ 0.30` → NO resolved |
| PnL (win) | `$0.05 × (1.0 − entry_price) / entry_price` |
| PnL (loss) | `−$0.05` |

---

## Sample Coverage

| Category | Count | % of 68 |
|----------|-------|---------|
| Total blocked candidates | 68 | 100% |
| No snapshot (gap) | 8 | 11.8% |
| Ambiguous at expiry (yes_bid 0.30–0.70) | 13 | 19.1% |
| **Resolved with outcome** | **47** | **69.1%** |

> [!NOTE]
> 13 candidates (19%) had ambiguous yes_bid at expiry — markets still near 50/50 when last snapshot was taken. These are excluded from PnL calculation. This is a conservative exclusion (ambiguous = most likely low-EV).

---

## Aggregate Results ($0.05/trade)

| Metric | Value |
|--------|-------|
| Resolved candidates | 47 |
| Wins | 17 |
| Win rate | **36.2%** |
| **Total PnL** | **−$0.8166** |
| Capital deployed | $2.35 |
| Return on capital | **−34.7%** |
| Expectancy per trade | **−$0.0174** |
| Mean PnL per trade | −$0.0174 |
| Median PnL per trade | −$0.0500 |
| Profit Factor | **0.456** |
| Gross wins | +$0.6834 |
| Gross losses | −$1.5000 |

> [!CAUTION]
> Profit Factor = 0.456. A value below 1.0 means the strategy loses more than it gains even when it wins. This is not a rounding artifact — it reflects that the payoff at mean $0.51 entry price is insufficient to overcome the 63.8% loss rate.

---

## Tier Breakdown

| Tier | Description | N | Wins | WR | Total PnL | Exp/Trade | Verdict |
|------|-------------|---|------|-----|-----------|-----------|---------|
| A | < $0.15 (high leverage) | 0 | — | — | — | — | **NO DATA** |
| B | $0.15–$0.30 | 1 | 0 | 0.0% | −$0.05 | −$0.0500 | **NEGATIVE** |
| C | $0.30–$0.50 | 15 | 6 | 40.0% | −$0.199 | −$0.0132 | **NEGATIVE** |
| D | ≥ $0.50 (near fair value) | 31 | 11 | 35.5% | −$0.568 | −$0.0183 | **NEGATIVE** |

> [!IMPORTANT]
> **Tier A (< $0.15) had ZERO candidates in this 24h window.** The structural edge hypothesis (27% WR at 9x payoff = positive EV) cannot be confirmed or denied from this sample. The 24h blocked candidates were concentrated in the $0.50 price zone where model confidence of 0.46 is genuinely below the breakeven required (~0.51).

---

## Asset Breakdown

| Asset | N | Wins | Win Rate | Total PnL |
|-------|---|------|----------|-----------|
| BTC | 25 | 11 | **44.0%** | −$0.203 |
| ETH | 22 | 6 | **27.3%** | −$0.613 |

BTC performed materially better (44% WR vs 27% for ETH). ETH blocked candidates were significantly worse. Both are negative.

---

## Confidence Analysis

| Field | Value |
|-------|-------|
| Confidence mean (resolved sample) | 0.4623 |
| Confidence median | 0.4487 |
| Confidence floor | 0.54 |
| Gap to floor (mean) | **0.0777** |
| Breakeven win rate at mean ask ($0.51) | **~51%** |
| Actual win rate | **36.2%** |

**The confidence floor is NOT misconfigured.** The realized win rate (36.2%) is materially below the breakeven required for $0.50 YES tokens (~51%). The confidence of 0.46 correctly predicts poor directional accuracy at this price level.

---

## Comparison: Actual vs Counterfactual

| Metric | Actual Runtime | Counterfactual (Shadow) |
|--------|---------------|------------------------|
| Trades | 0 (all blocked) | 47 (hypothetical) |
| Win rate | N/A | 36.2% |
| Total PnL | $0.00 | **−$0.8166** |
| Capital at risk | $0.00 | $2.35 |
| Outcome | Correctly blocked | Would have lost money |

**The runtime correctly blocked these trades.** The confidence floor acted as a proper quality gate on this sample.

---

## Assessment of Confidence Floor Options

| Option | Assessment |
|--------|-----------|
| A: Improve expectancy | **NO** — realized negative on resolved sample |
| B: Reduce expectancy | **YES** — lowering floor would worsen returns |
| C: Only help low-price options | **UNCONFIRMED** — zero Tier A candidates in 24h window |
| D: No material difference | **NO** — material difference: −$0.82 if unblocked |

---

## Final Verdict

### `KEEP_CONFIDENCE_FLOOR`

**Primary evidence:**
- Realized PnL: **−$0.8166** on $2.35 deployed (−34.7%)
- Win rate: **36.2%** vs breakeven **~51%** at mean $0.51 entry price
- Profit Factor: **0.456** — gross losses nearly double gross wins
- All tiers negative (B, C, D)
- No Tier A (< $0.15) candidates in 24h window

**The confidence floor (0.54) is functioning correctly.** It is blocking candidates where the model's directional confidence is genuinely insufficient relative to the price they would need to pay.

---

## Secondary Recommendation

### `LOW_PRICE_ONLY_RESEARCH` (for future investigation)

The prior full-session audit found mean price $0.38 with a 27% win rate counterfactual producing +$13 USDC. The 24h window shows zero Tier A candidates. **These populations are different.**

A future read-only research task should:
1. Extract all Tier A (< $0.15) confidence_too_low blocked candidates from the **full session** (109 events)
2. Apply snapshot resolution to that specific subset only
3. If Tier A produces positive expectancy → raise as `LOW_PRICE_ONLY_RESEARCH` for a bounded experiment

**Do NOT lower the confidence floor based on the current evidence.**

---

## Analysis Limitations

| Limitation | Impact |
|------------|--------|
| 31% of candidates not resolved (8 gap + 13 ambiguous) | Moderate — excludes uncertain outcomes |
| Side selection uses model probability, not signal | Model may be wrong directionally |
| Snapshot resolution (≥0.70 / ≤0.30) is approximate | Some misclassification possible |
| Only 24h window (Jun 17–18) | May not represent full population |
| No Tier A candidates | Cannot confirm/deny structural edge |

**Evidence quality: MEDIUM** (47 resolved events, snapshot-inferred outcomes, 69% coverage)

---

## Final Confirmation

```
Runtime changed: No
Strategy changed: No
EV changed: No
Risk changed: No
Execution changed: No
Live trading changed: No
Files modified: 0
```
