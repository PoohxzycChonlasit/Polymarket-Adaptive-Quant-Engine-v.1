# BANKROLL_TIER_RUNTIME_MAP_001
**Mode: DISCOVERY ONLY**  
**OS Version: Windows**  

---

This report presents the runtime mapping, boundaries, promotion/demotion gates, and risk bounds for the bankroll tier framework.

---

## 1. Tier Selection and Bounds

Tiers are statefully managed by the `BankrollRankLock` manager. The system contains 13 tiers defined in [bankroll_tiers.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/bankroll_tiers.py#L147):

| Tier Enum | Lower Bound | Upper Bound | Family | Base Risk Bounds | Max Exposure | Kelly Fraction | Stop Loss | Description |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **T0_MICRO_SEED** | $0.0 | $25.0 | MICRO | 3.0% – 5.0% | 10.0% | 0.10 | 90% | Paper validation tier for tiny seed bankrolls. |
| **T1_MICRO_BUILD** | $25.0 | $50.0 | MICRO | 4.0% – 6.0% | 10.0% | 0.12 | 88% | Micro bankroll building tier with tight limits. |
| **T2_MICRO_SURVIVAL** | $50.0 | $100.0 | MICRO | 4.0% – 5.0% | 9.0% | 0.15 | 85% | Upper micro tier; paper micro-survival active. |
| **T3_BASE_BUILD** | $100.0 | $250.0 | BASE | 3.0% – 4.0% | 8.0% | 0.20 | 80% | First standard tier; no micro-survival behavior. |
| **T4_BASE_STABLE** | $250.0 | $500.0 | BASE | 2.5% – 3.5% | 7.0% | 0.20 | 78% | Stable base tier with lower risk than build tiers. |
| **T5_SMALL_GROWTH** | $500.0 | $1,000.0 | GROWTH | 2.0% – 3.0% | 6.0% | 0.22 | 76% | Sizing capped by rank and market exposure. |
| **T6_GROWTH_1** | $1,000.0 | $2,500.0 | GROWTH | 1.5% – 2.5% | 5.0% | 0.25 | 75% | Reduced risk fraction as capital increases. |
| **T7_GROWTH_2** | $2,500.0 | $5,000.0 | GROWTH | 1.0% – 2.0% | 4.0% | 0.25 | 74% | Mid-growth tier focused on reducing variance. |
| **T8_GROWTH_3** | $5,000.0 | $10,000.0 | GROWTH | 0.75% – 1.5% | 3.5% | 0.25 | 72% | Late-growth tier with lower exposure. |
| **T9_CAPITAL_1** | $10,000.0 | $25,000.0 | CAPITAL | 0.5% – 1.25% | 3.0% | 0.22 | 70% | Capital tier prioritizing preservation. |
| **T10_CAPITAL_2** | $25,000.0 | $50,000.0 | CAPITAL | 0.4% – 1.0% | 2.5% | 0.20 | 70% | Capital tier with tighter max market exposure. |
| **T11_CAPITAL_3** | $50,000.0 | $100,000.0 | CAPITAL | 0.25% – 0.75% | 2.0% | 0.18 | 70% | Large capital tier with conservative risk. |
| **T12_CAPITAL_PRESERVE**| $100,000.0 | $\infty$ | CAPITAL | 0.1% – 0.5% | 1.5% | 0.15 | 70% | Preservation tier; risk tapers toward minimum. |

---

## 2. Dynamic Promotion & Demotion Rules

### Promotion Rule
* A promotion is evaluated statefully when `current_balance >= upper_bound` of the current active tier.
* The tier is instantly upgraded to the new corresponding tier.

### Demotion Rule
* A demotion is evaluated statefully when `current_balance < lower_bound * (1.0 - buffer_pct)`.
* This prevents demoting on minor balance fluctuations.

### Hysteresis
* Configured by `bankroll_tier_hysteresis_pct` in settings (default = `0.05` or 5%).
* For example, when promoting from **T0_MICRO_SEED** to **T1_MICRO_BUILD** at `$25.0`, the system will remain in T1 unless the balance drops below `$25.0 * (1.0 - 0.05) = $23.75`.

### Recovery Logic
* Evaluated by `evaluate_risk_mode` in [risk_modes.py:L55](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/risk_modes.py#L55).
* If consecutive losses >= 3 or drawdown >= 4%, size multiplier is set to **0.25** (`MICRO_RECOVERY` mode).
* Normal mode is restored when consecutive losses are reset (upon a win) and drawdown decreases.

### Floor Balance
* Hardcoded as `FLOOR_BALANCE = 5.00` in [risk_manager.py:L42](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/risk_manager.py#L42) and settings.
* If the balance drops below **$5.00 USDC**, all trading is immediately blocked.

### Maximum Exposure
* **Single Market Cap**: Defined per tier under `max_market_exposure_pct` (ranging from 10% for T0 to 1.5% for T12).
* **Total Session Cap**: Settings enforce `max_total_exposure = 0.30` (30% of total bankroll across all active positions).
