# BTC Window Run Plan

Document type: operational run plan — docs only.

Created: 2026-05-23

Updated: 2026-05-23

Runtime behavior changed: No.
Live behavior changed: No.
Code changed: No.
Tests: none, docs-only.

---

## Objective

Run one clean paper session timed to the BTC primary active window to accumulate BTC outcome-truth
trades and advance Phase 6 readiness gates.

---

## Run Parameters

| Parameter | Value |
|---|---|
| Mode | `python main.py` (safe paper default) |
| Start target | **04:00 UTC ± 30 min** |
| Minimum duration | **≥ 6 hours** (covers 04h–05h primary + 12h secondary window) |
| Stop condition | Manual stop after ≥ 6h or after confirming ≥ 2 BTC outcome-truth closes |
| Assets | BTC + ETH (both active; do not restrict to BTC only) |
| Outcome-truth fields | Required: `trade_result`, `pnl_usdc`, `quote_lineage_id` on all closes |
| Quote-age fields | Required: `quote_age_at_submit_ms`, `quote_age_at_fill_ms` on execution events |

---

## Gate Targets

| Gate | Pre-run | Target | Source |
|---|---:|---:|---|
| BTC outcome-truth trades | 1 | ≥ 3 | +2 from this session |
| TP outcomes (all assets) | 6 | ≥ 8 | +2 from this session |
| Paired trades (all assets) | 15 | ≥ 17 | +2 from this session |
| Readiness (old formula) | 79% | ≥ 80% | +1 BTC trade clears |

Minimum success condition:

```text
BTC outcome-truth trades >= 3  AND  readiness >= 80%
```

Readiness crosses 80% with 1 additional BTC trade (→ 83%).
BTC task gate (≥ 3) clears with 2 additional BTC trades.

---

## Expected Yield

Based on historical yield of 1.7 BTC opens per 04h-start session (10 pre-patch BTC opens across
6 sessions starting 04h–06h UTC):

| Scenario | BTC OT trades | Global BTC total | Readiness | BTC gate | Readiness gate |
|---|---:|---:|---:|---|---|
| Conservative (1 BTC) | 1 | 2 | 83% | NOT MET | **MET** |
| Expected (2 BTC) | 2 | 3 | 87% | **MET** | MET |
| Optimistic (3 BTC) | 3 | 4 | 91% | MET | MET |

ETH trades are additional: 15 current + ~3-6 ETH per session = paired 18–21, TP 7–9.

---

## Window Coverage

| UTC hour | What to expect | Action |
|---|---|---|
| 04h | BTC primary window opens. First BTC entries likely. | Monitor for BTC fills. |
| 05h | Continued BTC activity (historically 6 opens total at this hour). | Most productive BTC hour. |
| 06h–11h | Reduced BTC (2 opens historically). ETH continues. | Normal ETH accumulation. |
| 12h | BTC secondary window. Additional BTC entries possible. | Monitor for BTC fills. |
| 12h+ | Continue if ≥ 6h not yet reached or BTC target not met. | Can stop at operator discretion. |

---

## Pre-Run Checklist

Before starting:

- [ ] Confirm current date/time and that start is within 04:00–04:30 UTC.
- [ ] Confirm system is in paper mode: `python main.py` defaults to paper.
- [ ] Confirm JSONL path is writing to `runtime/quant_data/`.
- [ ] Confirm no stale processes from prior session holding file locks.
- [ ] Note run ID from startup banner (first log line after launch).

---

## During-Run Monitoring

At each check interval:

- Terminal shows `S3 CAUTION` (not READY — no promotion has occurred).
- Terminal shows `Phase6 BLOCKED` or `Phase6 ACCUMULATING` — not `PASS`.
- Paper mode banner visible: `SOURCE paper_virtual` or `NO LIVE ORDERS`.
- Rolling log panel shows `[PAPER FILL]` events for each BTC/ETH close.

Watch for BTC fills specifically in 04h–05h and 12h windows.

---

## Post-Run Analysis Steps

After stopping:

```bash
# 1. Identify the run ID from logs or startup banner
# 2. Check data quality for the run
python tools/quant_data_quality.py --date YYYY-MM-DD --run-id RUN_ID --write-report

# 3. Run offline replay analyzer
python tools/replay_analyzer.py --date YYYY-MM-DD --csv

# 4. Check no-entry reasons if BTC count is zero
python tools/no_entry_analyzer.py --date YYYY-MM-DD --run-id RUN_ID --write-report

# 5. Update monitors
# docs/research/runtime_health/execution_reality_daily_monitor.md
# docs/research/btc_evidence_watch.md
# docs/research/btc_harvest_window_monitor.md
```

---

## Post-Run Update Targets

If BTC outcome-truth trades are confirmed:

| Document | What to update |
|---|---|
| `btc_harvest_window_monitor.md` | Add to active-window ledger, update OT count and gate progress |
| `btc_evidence_watch.md` | Update BTC total, TP/SL split, quote age if available |
| `execution_reality_daily_monitor.md` | Update daily snapshot, delta, gate progress, classification |
| `btc_session_intelligence.md` | Add session to active-window session list |

---

## Success Conditions

| Condition | Met when | Impact |
|---|---|---|
| Readiness gate | BTC OT total ≥ 2 (79% → 83%) | Readiness task gate clears |
| BTC task gate | BTC OT total ≥ 3 | BTC task gate clears |
| Phase 6 review eligible | All four task gates met | Daily monitor → NEAR_READY or READY_FOR_PHASE6_REVIEW |

---

## Abort Conditions

Stop the session and investigate before updating any monitor if:

- `market_analysis_exception` > 0 appears in any cycle (run not eligible for outcome-truth counting).
- Terminal shows `model_output_ready=false` on consecutive cycles (model visibility gap).
- Logging `PermissionError` causes CSV or JSONL to stop writing (check file locks).
- BTC orderbook shows `no_orderbook` on repeated cycles (BTC market may not be active this window).

If any abort condition fires, exclude the run from the active-window ledger.

---

## Fallback Plan

If the 04h session produces 0 BTC entries (possible — delta_extreme blocks ~45% of BTC decisions):

1. Do not change strategy, risk, or thresholds.
2. Check `no_entry_analyzer` output for `delta_extreme` dominance.
3. Run a second session on the next day also starting at 04h UTC.
4. After two zero-BTC sessions: inspect whether the BTC 5-minute market was inactive or spread was too wide. Do not loosen risk gates based on one or two session nulls.

---

## Do Not

- Do not promote S3 based on this session alone.
- Do not change risk sizing, entry thresholds, or delta_extreme limits.
- Do not count pre-outcome-truth BTC closes from this or any prior session.
- Do not treat a BTC TP result as permission to increase BTC allocation — one TP is still n=1.
- Do not run `--mode live`. Paper mode only.
