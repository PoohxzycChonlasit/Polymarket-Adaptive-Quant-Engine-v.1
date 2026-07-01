# CLOB_COMPLIANT_PAPER_SIZING_RISK_DESIGN_001

## 1. Sizing Math & Constraints
The paper sizing module now respects the Polymarket live Orderbook (CLOB) constraints for Crypto 5M Up/Down markets:
- **minimum_order_size_shares** = 15
- **minimum_tick_size** = 0.01

Given a base live simulated **bankroll** of .00:
- **minimum_executable_notional** = 15 * price
- **exposure_pct** = minimum_executable_notional / bankroll

## 2. Price Bucket Risk Table
This table outlines the minimum required notional investment (and its exposure against a  bankroll) to simply open the minimum allowed 15-share position.

| Price | Min Shares | Min Notional | Exposure % of  | Max Loss (resolves 0) | Classification |
|-------|------------|--------------|-------------------|-----------------------|----------------|
| 0.10  | 15         | .50        | 7.5%              | .50                 | CLOB_EXECUTABLE_LOW_BANKROLL_RISK |
| 0.20  | 15         | .00        | 15.0%             | .00                 | CLOB_EXECUTABLE_MODERATE_BANKROLL_RISK |
| 0.30  | 15         | .50        | 22.5%             | .50                 | CLOB_EXECUTABLE_MODERATE_BANKROLL_RISK |
| 0.40  | 15         | .00        | 30.0%             | .00                 | CLOB_EXECUTABLE_HIGH_BANKROLL_RISK |
| 0.50  | 15         | .50        | 37.5%             | .50                 | CLOB_EXECUTABLE_HIGH_BANKROLL_RISK |
| 0.60  | 15         | .00        | 45.0%             | .00                 | CLOB_EXECUTABLE_EXTREME_BANKROLL_RISK |
| 0.70  | 15         | .50       | 52.5%             | .50                | CLOB_EXECUTABLE_EXTREME_BANKROLL_RISK |
| 0.80  | 15         | .00       | 60.0%             | .00                | NOT_RECOMMENDED_FOR_20_BANKROLL |
| 0.90  | 15         | .50       | 67.5%             | .50                | NOT_RECOMMENDED_FOR_20_BANKROLL |

*Note: With an extreme bankroll risk, a single loss can wipe out nearly half the capital. True quantitative sizing models typically limit single-trade risk to 1-5%.*

## 3. Risk Cap Table
If we restrict trading to specific bankroll exposure caps, we are intrinsically constrained to lower-priced markets.

| Max Exposure Cap | Allowed $ Risk | Max Allowed Price (Cap * 20 / 15) | Implications |
|------------------|----------------|-----------------------------------|--------------|
| 5%               | .00          | 0.066                             | Only deep out-of-the-money entries allowed. |
| 10%              | .00          | 0.133                             | Severely restricts entries to very low-probability longshots. |
| 15%              | .00          | 0.200                             | Restricts mostly to underdog positions. |
| 25%              | .00          | 0.333                             | Allows moderate-probability entries, excludes favorites. |
| 40%              | .00          | 0.533                             | Allows 50/50 entries but subjects the bankroll to extreme drawdown risk. |

## 4. Policy Options
- **Option A:** Keep  bankroll and reject all trades unless min-notional exposure is below a chosen cap. (Highly restrictive on entry types).
- **Option B:** Use  bankroll but allow only low-price entries where min order exposure is acceptable. (Biases the strategy strictly to low-prob).
- **Option C:** Use a larger simulated research bankroll (e.g. ) for paper evidence to validate the strategy across all price bands, while separately marking it as not representative of a  live bankroll. (Safely tests the edge without artificial constraints).
- **Option D:** Shadow-size all signals with 15-share minimum but do not open paper positions until a firm live risk policy is authorized.
- **Option E:** Micro-live later only after actual capital and max-loss rules are aligned with CLOB minimums.

## 5. Recommended Safe Implementation
**Recommendation: Option C (Bankroll scaling separation)**
We recommend implementing a distinctly larger *Paper Research Bankroll* (e.g.,  - ) exclusively for generating executable paper trade evidence. This allows us to scale trades realistically to the >=15 share minimum across all price ranges (including favorites at 0.60–0.80) while preserving safe risk percentages (1–5% of the research bankroll). 
The  live bankroll remains untouched until the strategys profitability is robustly proven on paper, at which point the live bankroll must realistically be increased to support CLOB minimums safely.

## 6. What is Forbidden
- Raising live bankroll constraints blindly without capital commitment.
- Treating sub-15-share paper executions as valid evidence of edge.
- Modifying EV, probability thresholds, or strategy entry logics to adapt to these constraints.

## 7. Why AUTHORIZE_CLOB_COMPLIANT_MICRO_SIZING_001 is Not Approved Yet
It remains unapproved because directly forcing 15 shares against a  bankroll introduces extreme ruin risk (up to 45–67% drawdown on a single loss). The sizing policy must be mathematically decoupled from the small live wallet to properly test the strategys edge in paper mode.

## 8. Remaining Uncertainty
- Will the Tech Lead approve Option C (Paper Research Bankroll) or prefer Option A (Exposure Caps on )? 
- How will the metrics builder separate paper ROI metrics on a  virtual bankroll versus a  theoretical live bankroll?

## 9. Tech Lead Review Candidates
- AUTHORIZE_PAPER_RESEARCH_BANKROLL_001 (To enact Option C)
