# LOW_PRICE_TRUTH_RESOLUTION_DISCOVERY_001

## 1. Truth Source Map & Settlement Lineage

The settlement validation in `SUB_5C_EXECUTION_REALITY_AUDIT` was performed using three distinct source directories within `runtime/quant_data/`:

1. **trade_journal** (`runtime/quant_data/trade_journal/*.jsonl`)
   - **Fields Extracted**: `resolution`, `outcome`, or `settled_outcome`
   - **Truth Type**: `OFFICIAL` (Actual final settled outcomes from Polymarket CLOB/Gamma)
   - **Role**: Primary truth source.

2. **path_truth** (`runtime/quant_data/path_truth/*.jsonl`)
   - **Fields Extracted**: `resolution`, `outcome`, or `winner`
   - **Truth Type**: `DERIVED` (Oracle price feed and settlement verification paths)
   - **Role**: Secondary truth source.

3. **market_snapshots** (`runtime/quant_data/market_snapshots/*.jsonl`)
   - **Fields Extracted**: `epoch_start_ts`, `market_id`, `seconds_remaining`, and `yes_bid`
   - **Truth Type**: `PROXY` (Transient bid prices observed prior to market expiry)
   - **Role**: Tertiary proxy source.

---

## 2. Coverage & Official vs. Proxy Breakdown

Across the 7-day audit window (2026-06-12 → 2026-06-18) for the **99 unique sub-5c opportunities** (ask < $0.05) identified in the decision logs:

| Source | Count | Coverage | Truth Type |
|---|---|---|---|
| **trade_journal** | 0 | **0.00%** | OFFICIAL |
| **path_truth** | 0 | **0.00%** | DERIVED |
| **market_snapshots** (resolved) | 98 | **98.99%** | PROXY |
| **Ambiguous / Unresolved** | 1 | **1.01%** | UNKNOWN |

### Key Finding
**There is 0.00% official or derived truth coverage for sub-5c contracts.** Every single resolved trade (98/99) in the audit relied exclusively on the snapshot proxy `yes_bid` price.

---

## 3. Win Rate Anomaly Analysis

The audit reported the following win rates by ask price sub-tier:
- **2c–3c Ask**: **57.58% WR** (19 wins out of 33)
- **3c–4c Ask**: **42.42% WR** (14 wins out of 33)
- **4c–5c Ask**: **31.25% WR** (10 wins out of 32)

### Source of the Win Rates
These win rates came 100% from **snapshot inference** (not official settlements). 

### Code Path Tracing
The win rates were generated in `scratch/sub5c_execution_reality_audit.py` via the following logic path:
1. **Discover Opportunity**: Filter `decision_log` for `event_type == 'decision'` and `raw_skip_reason == 'risk_plan_zero'`.
2. **Side and Ask Selection**: Extract the ask price based on the trade side (`yes_ask` for YES, `no_ask` for NO).
3. **Outcome Inference**: Look up the nearest snapshot in `market_snapshots` before expiry (within a 180s window).
   - If `yes_bid` >= 0.65, resolve as `YES`.
   - If `yes_bid` <= 0.35, resolve as `NO`.
4. **Win Determination**: Compute `is_win = (e['side'] == resolution)`.
5. **Rate Calculation**: Divide wins by total resolved opportunities in each ask price bucket.

---

## 4. Confidence Assessment & Proxy Bias

The win rates of **57.58%** for 2c-priced contracts and **42.42%** for 3c-priced contracts are statistically anomalous and highly indicative of **Snapshot Proxy Bias**:

1. **Mid-Epoch Fluctuations**: The snapshot proxy reads `yes_bid` up to 180 seconds before expiry (with an average remaining duration of 161.7 seconds). In a 5-minute (300s) binary prediction market, a snapshot taken with 2 to 3 minutes remaining represents a mid-epoch transient state.
2. **Mean-Reverting Noise**: The price of low-probability options often fluctuates wildly due to spread updates and temporary oracle moves. A contract priced at 2c (representing a 2% implied probability of winning) can easily experience a brief bid fluctuation above 35c or 65c mid-epoch, only to expire worthless (0c) at the end of the 5 minutes.
3. **Outcome Misclassification**: Because the proxy classifies any snapshot `yes_bid >= 0.65` as a `YES` outcome, transient mid-epoch price spikes are recorded as wins, causing a massive simulation/replay bias.

---

## 5. Final Verdict

### Verdict: `REPLAY_ARTIFACT`

### Rationale
- **No Official Validation**: Zero outcomes are backed by real on-chain settlements or trade journals.
- **Proxy Failure**: The settlement proxy uses transient mid-epoch snapshots (averaging 161 seconds before expiry) as final outcomes, which captures transient noise and spread fluctuations rather than final settlement.
- **Mathematical Impossibility**: A true win rate of 57.58% on 2c contracts (a 29x outperformance of implied market probabilities) without live-risk fill or on-chain settlement evidence is mathematically and operationally a simulation artifact.

---

## 6. Recommendations

1. **Lock Sizer Changes**: Keep the sizer block on sub-5c contracts active.
2. **Develop On-Chain Resolution Tracking**: Future audits must join market keys against verified settlement contracts on-chain to obtain official final outcomes before modifying sizer thresholds.
3. **Reject Snapshot-Only Replays**: Never utilize snapshot-proxy resolutions to justify strategy or sizer updates.
