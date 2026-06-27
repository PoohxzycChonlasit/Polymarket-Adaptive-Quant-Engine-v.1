# Trade Context Lineage Audit Report

> **DOCUMENT_TYPE: report**
> **DESTINATION:   docs/reports/TRADE_CONTEXT_LINEAGE_AUDIT_001.md**
> **REASON:        Report on the audit of trade context lineage fields from decision to backtesting.**
>
> **TASK_CLASS: 1 — RESEARCH**
> **Date: 2026-06-28 | Evidence Grade: B (source-code verified) + A (runtime observed)**

---

## 1. Summary

We audited the lineage of trade context fields from candidate evaluation to database logs. The audit revealed a critical flaw: `PositionTracker` is volatile and starts fresh on every script restart because its state persistence is never called in production. When the bot restarts, it rebuilds open positions from CLOB balance feeds, losing all original entry metadata. This explains why 108/112 closes on 2026-06-27 had LOW join confidence and lacked sizing context.

---

## 2. Key Findings

### Critical Flaw: Position Tracker Volatility (Grade B)
- `PositionTracker` contains `save_state` and `load_state` but they are never called in production.
- Process restarts wipe all open position metadata (EV, probability, sizer tier, risk mode).
- Settled or closed trades after a restart are logged as "missing_legacy" attribution.

### Match Analysis (Grade A)
- Date-scoping is the secondary cause for LOW joins on date-specific runs.
- Running the builder over a 2-day range (`--start-date 2026-06-26 --end-date 2026-06-27`) successfully matched 100% (14/14) of the open events within that range. The remaining unmatched closes represent legacy positions from prior days or mock runs.

---

## 3. Recommended Next Task

**`TELEMETRY_BACKFILL_FOR_QUANT_TRUTH_001`** (Class 5 — OBSERVABILITY)

Implement the carry-forward metadata logic in `trader.py` and enable `PositionTracker` state persistence. This secures the context lineage and allows all future trades to carry full metadata at exit time.
