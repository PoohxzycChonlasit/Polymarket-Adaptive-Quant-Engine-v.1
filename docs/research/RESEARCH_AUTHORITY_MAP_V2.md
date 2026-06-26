# RESEARCH_AUTHORITY_MAP_V2

This map defines the canonical authority levels and allowed/forbidden uses for all completed repository audits.

---

## 1. CANONICAL (Source of Truth / Highly Trusted)

### A. REPLAY_METHODOLOGY_VALIDATION_001
- **Authority Level**: Full validation of share, payout, and transaction formulas.
- **Limitations**: Does not evaluate execution fills or liquidity availability.
- **Allowed Use**: Serves as the mathematical baseline for backtester and replay PnL calculations.
- **Forbidden Use**: Cannot be used to approve live trading or claim that paper-simulated fills are executable.

### B. RISK_PLAN_ZERO_FORENSIC_AUDIT_001
- **Authority Level**: Source of truth on confidence floor skippage triggers in real-time.
- **Limitations**: Does not analyze why the model confidence was low in specific market cycles.
- **Allowed Use**: Explaining zero-position blocks and skipping behavior.
- **Forbidden Use**: Cannot justify bypassing public sizer thresholds.

### C. CLOB_EMPTY_RESPONSE_FORENSIC_AUDIT
- **Authority Level**: Source of truth on websocket warmup delays and startup checks.
- **Limitations**: Does not prove feed integrity during high-volatility sessions.
- **Allowed Use**: Tuning startup orderbook initialization delays.
- **Forbidden Use**: Cannot prove live execution readiness.

---

## 2. PARTIAL (Qualified / Incomplete Scope)

### A. EXECUTABLE_REALITY_AUDIT_001
- **Authority Level**: Initial analysis of spread and ask sizes.
- **Limitations**: Small sample size (historical only).
- **Allowed Use**: Reference for basic liquidity bounds.
- **Forbidden Use**: Cannot prove executability under live slip conditions.

### B. SHADOW_SIZING_REPLAY_AUDIT_001
- **Authority Level**: Diagnostic of counterfactual sizing behavior.
- **Limitations**: Highly dependent on historical logs, lacks real-time feed tests.
- **Allowed Use**: Planning sizer simulations.
- **Forbidden Use**: Cannot alter active sizer parameters.

### C. LOW_PRICE_EDGE_VALIDATION_001
- **Authority Level**: Proves low-price expectancies have execution gaps.
- **Limitations**: Does not verify token ID settlement contract on-chain.
- **Allowed Use**: Gating naïve <10c backtest expectancies.
- **Forbidden Use**: Cannot close active question `LOW_PRICE_TRUTH_RESOLUTION_001`.

---

## 3. OPEN_QUESTION (Active Investigation)

### A. SUB_5C_EXECUTION_REALITY_AUDIT
- **Authority Level**: Evaluates sub-5c spreads and orderbook depth.
- **Limitations**: Dependent on provisional snapshot price proxies; lacks verified settlement joins.
- **Allowed Use**: Supporting documentation only.
- **Forbidden Use**: Cannot change sizer confidence limits.

---

## 4. SUPERSEDED (Obsolete / Outdated)

- **Non-deduplicated Replays**: Zero authority (invalidated by count double-counting bias).
- **Early Positive Expectancy Replays**: Zero authority (invalidated by selection bias).
- **Historical HFT specs (`VULTR_PAPER_RUN.md`)**: Zero authority (superseded by 5-minute binary prediction market design).
