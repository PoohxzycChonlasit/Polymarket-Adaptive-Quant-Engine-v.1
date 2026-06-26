# RESEARCH_CANONICALIZATION_AUDIT_001

## 1. Executive Summary

This audit establishes a **Research Canonicalization Map** for all major research audits completed on the repository. It reviews active and historical research conclusions to distinguish between trusted quantitative findings, disproven hypotheses, and unresolved anomalies, mapping their authority limits.

- **Main Finding**: The apparent high-expectancy profitability of low-price contracts (<$0.05 ask) has been classified as **EDGE_WEAK** due to non-executable fills and settlement proxy assumptions. However, sub-5c contracts *do* remain executable under strict orderbook spreads and L1-L3 depth gates.
- **Authority Status**: Replay-key join continuity is validated for post-wiring rows, but fill truth remains an active blocker for Growth Mode.

---

## 2. Review of Completed Audits

| Audit ID | Purpose | Classification | Key Finding / Verdict |
|---|---|---|---|
| **RISK_PLAN_ZERO_FORENSIC_AUDIT_001** | Analyze zero-position sizing triggers in the real-time loop. | **CANONICAL** | Confirmed that `confidence_too_low` is the dominant block, with 88.4% of skips caused by confidence failing the sizing threshold. |
| **REPLAY_METHODOLOGY_VALIDATION_AUDIT_001** | Validate mathematical correctness of share and win PnL formulas. | **CANONICAL** | Proven that the replay PnL engine matches standard exchange settlement specifications. Replay joins are verified. |
| **LOW_PRICE_EDGE_VALIDATION_001** | Evaluate whether the <$0.10 ask edge is real or a replay artifact. | **CANONICAL** | **EDGE_WEAK**. 85.1% of apparent backtest PnL came from the <$0.05 bucket, which has massive execution reality gaps. |
| **SUB_5C_EXECUTION_REALITY_AUDIT** | Evaluate fill realism for ask prices <$0.05. | **CANONICAL** | **EDGE_REAL (with conditions)**. 100% of analyzed sub-5c instances were executable by spread (<=2c) and ask depth (>=10.81 USDC). |
| **CLOB_EMPTY_RESPONSE_FORENSIC_AUDIT** | Forensic audit of empty orderbook states in CLOB. | **PARTIAL** | Identified that `empty_book` is emitted during feed warmup or websocket rotation, but actual market depth coverage gaps remain. |
| **DELTA_EXTREME_GATE_FORENSIC_AUDIT** | Analyze rejections from the Delta Extreme risk gate. | **HISTORICAL** | Revalidated that Delta Extreme filters out tail-risk regime transitions, acting as a crucial capital protection layer. |
| **SELECTION_BIAS_AUDIT** | Evaluates backtest selection anomalies. | **HISTORICAL** | Confirmed that selection bias inflated early backtest expectations. Replays must use deduplicated epoch keys. |
| **EVIDENCE_QUALITY_AUDIT** | Check JSONL schema integrity. | **PARTIAL** | Found minor schema drifts in older logs. Newer runs conform to the `QuantEventLogger` JSONL specification. |

---

## 3. Findings Trust Status

### A. Conclusions Still Trusted
1. **Deduplication Key Rules**: Every backtest and replay run *must* deduplicate using `(market_id, epoch_start, side)` to prevent duplication bias. This is the cornerstone of replay validation.
2. **Confidence Skippage**: Sizer blockages are driven by the probability model's output falling below the confidence floor, not by data dropouts.
3. **Delta Extreme Guard**: The Delta Extreme gate blocks HFT scale-ups but protects capital during rapid price trend sweeps.

### B. Conclusions Disproven
1. **Naïve Low-Price Expectancy**: The early thesis that trading <$0.10 contracts yields a high profit factor was disproven. Without L1-L3 liquidity gates, a high percentage of these trades represent non-executable fills.
2. **Infinite Averaging Down / Martingale**: Replays proved that averaging down under high-drawdown regimes results in catastrophic capital depletion. Bounded inventory caps must be enforced.

### C. Conclusions Remaining Unresolved (Open Questions)
1. **Settlement Proxy Reliance**: The system currently infers outcomes via path-truth price snapshots. Resolving official token settlement contracts on-chain remains an active development gap.
2. **ws_cache Warmup Delays**: The exact duration required for websocket warmup at startup (to prevent empty book rejects) is not fully parameterized.

---

## 4. Research Authority Map

To guide future AI sessions, we define the promotion authority for each completed audit domain:

```text
[Raw JSONL logs] 
       │ (Quality Verified by EVIDENCE_QUALITY_AUDIT)
       ▼
[Offline Replays] 
       │ (Formulas validated by REPLAY_METHODOLOGY_VALIDATION)
       ▼
[Sub-5c Executability] 
       │ (Gated by SUB_5C_EXECUTION_REALITY_AUDIT)
       ▼
[Sizer Policy Decisions] ──> (Requires shadow-sizer run under decision registries)
```

- **Replay Validation**: Highly trusted for validation testing, but must not overwrite real-time `trader.py` sizing rules automatically.
- **Audit Findings**: Serve as *evidence* only.
- **Live Trading**: Remains blocked until order execution, fill reconciliation, and websocket warmup logic are proven in active live loops.

---

## 5. Single Recommended Next Step

Promote [SUB_5C_EXECUTION_REALITY_AUDIT](file:///C:/Users/poh_2/.gemini/antigravity/brain/a7e352d6-0771-400b-bc56-e929bb6e63b7/SUB_5C_EXECUTION_REALITY_AUDIT.md) to **Canonical** status in `docs/research/GOVERNANCE_NAVIGATION_HUB.md` as the official authority on sub-5c contract executability.
