# CLOB_COMPLIANT_EXTENDED_PAPER_EVIDENCE_RUN_001

**Status**: COMPLETE — INSUFFICIENT_EXECUTABLE_THROUGHPUT_SHORT_RUN  
**Operator Note**: Phase B shortened from 2 hours to 30–60 minutes by operator instruction.

---

## 1. Git Preflight

| Check | Value | Status |
|-------|-------|--------|
| Branch | `main` | ✅ |
| Synced with `origin/main` | Yes | ✅ |
| Latest commit pre-run | `813066d4` | ✅ |
| `next_task` | `null` | ✅ |
| Known untracked files | Untouched | ✅ |

---

## 2. Bug Fix Discovered and Resolved

During Phase A startup, an `AttributeError` was raised:

```
AttributeError: 'NoneType' object has no attribute 'account_balance'
  File "polymarket/trader.py", line 532
    deprecated_valid_for_live_20_bankroll_claim=(valid_for_live if settings.account_balance == 20.0 else False),
```

**Root cause**: The previous session's label normalization task (`LIVE_REFERENCE_BANKROLL_LABEL_NORMALIZATION_001`) introduced a bare `settings` reference instead of `self.settings` inside `BankrollState.__init__`. The module-level `settings` binding is `None` at that call site.

**Fix**: Changed `settings.account_balance` → `self.settings.account_balance` on line 532 of `polymarket/trader.py`.

**Committed**: `653df0b1` — `fix: use self.settings instead of bare settings in BankrollState init`

---

## 3. Phase A — Sanity Gate

| Field | Value | Status |
|-------|-------|--------|
| run_id | `20260701T075106Z_54212_3734c20c` | — |
| Duration | 7.28 minutes | — |
| mode | `paper` | ✅ |
| capital_basis | `PAPER_RESEARCH_BANKROLL` | ✅ |
| paper_research_bankroll_usd | `200.0` | ✅ |
| live_reference_bankroll_usd | `10.0` (dynamic) | ✅ |
| valid_for_live_reference_bankroll_claim | `false` | ✅ |
| valid_for_strategy_edge_research | `true` | ✅ |
| capital_reference_warning | Present (live ref ≠ 20) | ✅ |
| deprecated_valid_for_live_20_bankroll_claim | `false` | ✅ |
| No live orders | 0 order_intents, 0 orders_sent | ✅ |

**PHASE A RESULT: PASS**

---

## 4. Phase B — Extended Paper Evidence

**Operator instruction**: Shortened to 30–60 minutes. Server restart at ~08:22 UTC terminated the session at 22.31 minutes.

| Field | Value |
|-------|-------|
| run_id | `20260701T075916Z_45556_5818ec95` |
| Start | `2026-07-01T07:59:16Z` |
| End | `2026-07-01T08:21:35Z` |
| Actual Duration | **22.31 minutes** |
| Phase B shortened by operator | Yes |
| Session terminated by | Server restart (graceful — no data corruption) |

---

## 5. Trade Funnel Summary (Phase B)

| Metric | Value |
|--------|-------|
| Decisions | 46 |
| Active markets seen | 14 |
| Tradable markets | 8 |
| Candidates | 24 |
| EV pass count | 0 |
| Risk approved count | 0 |
| Order intents | 0 |
| Orders sent | 0 |
| Fills | 0 |
| Paper opens | 0 |
| Paper closes | 0 |
| TP count | 0 |
| SL count | 0 |
| Net PnL | $0.00 |
| Paper executable candidate count | 0 |
| Paper dust rejected count | 0 |
| Min-order rejected count | 0 |
| Paper opened after CLOB constraints | 0 |

---

## 6. Blocker Summary

| Blocker | Count |
|---------|-------|
| `book_warming` | **46 / 46** (100%) |
| All others | 0 |

**book_warming** is the single dominant blocker across the entire session. No candidate reached EV evaluation.

---

## 7. Did book_warming Clear?

**No.** Over 30 total minutes of combined observation (Phase A + Phase B), `book_warming` blocked every single decision. The warming timeout did not expire within the observation window. This is consistent with the prior smoke run.

---

## 8. Evidence Validity

| Label | Value |
|-------|-------|
| `VALID_FOR_BLOCKER_DIAGNOSIS` | ✅ Yes — 46 `book_warming` blocks clearly observed |
| `PARTIAL_FOR_MARKET_REALISM` | ⚠️ Yes — data feeds active but sizing/fees not validated |
| `INVALID_FOR_PROFIT_CLAIM` | ❌ Confirmed — no executable paper trades occurred |
| `VALID_FOR_STRATEGY_EDGE_RESEARCH` | `true` in telemetry |
| `valid_for_live_reference_bankroll_claim` | `false` — correct |

**PnL Meaningfulness**: Not meaningful. Zero executable trades occurred. No PnL accounting applies.

---

## 9. CLOB Constraint Status

CLOB minimum-order enforcement (15 shares) and tick-size validation (0.01) are structurally active. No candidates reached the CLOB gate because `book_warming` blocked them all upstream. The constraint layer was not bypassed — it simply had no candidates to evaluate.

---

## 10. Canonical Builder Output

Both run summaries generated successfully:
- `docs/reports/run_evidence/20260701T075106Z_54212_3734c20c_canonical_evidence_summary.json` (Phase A)
- `docs/reports/run_evidence/20260701T075916Z_45556_5818ec95_canonical_evidence_summary.json` (Phase B)

Schema: `trade_funnel_summary_v1` — all required capital-basis, bankroll, and evidence-validity fields present and correctly typed.

---

## 11. No-Behavior-Change Proofs

- **No live behavior change**: `mode = paper`, `STATUS NO LIVE ORDERS` confirmed in TUI output throughout both runs.
- **No strategy/EV tuning**: Entry gates, EV thresholds, and risk parameters were not modified.
- **No config/.env changes**: `.env` and `config/settings.py` are unchanged.
- **No CLOB constraint bypass**: `clob_constraints.py` not modified.
- **No paper_research_bankroll change**: Remains `$200.0`.

---

## 12. Remaining Uncertainty

1. **book_warming duration**: The warming timeout has not been observed to clear in any session today. The warmup window may be longer than 30 minutes under current market conditions or configuration. The exact warmup timer value should be verified in `config/settings.py` or the market feed warmup logic.
2. **Executable throughput**: Whether the strategy produces executable (≥15 share) candidates at all under current EV/confidence thresholds remains unobserved. A longer overnight run or explicit warmup-bypass diagnostic is needed to determine this.
3. **No paper fills**: Cannot assess whether CLOB constraints would accept or reject actual candidate sizes without candidates passing warmup first.

---

## 13. Tech Lead Review Candidates

1. **Investigate book_warming duration**: Determine the configured warmup window. If it exceeds 30–45 minutes, short paper runs will never yield executable evidence. Consider a diagnostic run with explicit warmup state logging.
2. **Overnight paper evidence run**: Authorize a longer (3–6 hour) paper session to observe post-warmup candidate throughput, EV pass rates, and CLOB constraint exercise.
3. **Warmup gate diagnostic**: Consider adding a telemetry event when `book_warming` expires so canonical builder can count `warmup_cleared_count` and `first_post_warmup_decision_ts`.
