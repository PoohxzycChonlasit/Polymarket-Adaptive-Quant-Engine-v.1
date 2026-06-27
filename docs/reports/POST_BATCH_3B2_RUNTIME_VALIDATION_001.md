# POST_BATCH_3B2_RUNTIME_VALIDATION_001

**Date:** 2026-06-27  
**Task Class:** 0 (HEALTH_CHECK)  
**Document type:** Runtime validation report  
**Destination:** `docs/reports/`  
**Commit validated:** `381cbc4` — refactor: extract scheduler cadence observability

---

## 1. Pre-Run Verification

| Check | Result |
|-------|--------|
| HEAD | `381cbc4` ✓ |
| Working tree | clean (1 untracked commit report — harmless) ✓ |
| `py_compile polymarket/trader.py polymarket/orchestration/trader_observability.py` | COMPILE_OK ✓ |
| `from polymarket.trader import PolymarketTrader` | IMPORT_OK ✓ |

---

## 2. Commands Run

```bash
python main.py --mode paper --interval 60 --ui auto --fps medium
```

Background process PID 24980, started 20:16:12 UTC. `timeout 420` wrapper.

---

## 3. Runtime Observations

| Metric | Value |
|--------|-------|
| PID | 24980 |
| Start time | 20:16:12 UTC |
| Final cycle | **Cycle #7** @ 20:22:19 UTC |
| UPTIME at end | **6:54** |
| Exit code | **0** (clean) |
| STATUS | `NO LIVE ORDERS` ✓ |
| JSONL status | `JSONL OK` ✓ |
| AttributeError | **0** ✓ |
| Traceback | **0** ✓ |

Paper trade lifecycle confirmed: `position_opened_v1: 1`, `position_closed_v1: 1` — full paper execution path operational.

---

## 4. Telemetry / JSONL Verification

**Session events (PID 24980): 310 total**

| Event type | Count |
|-----------|-------|
| `runtime_heartbeat_v1` | 83 |
| `runtime_warning_v1` | 72 |
| `candidate_rejected_v1` | 30 |
| `analytics_loaded_v1` | 42 |
| `go_no_go_decision_v1` | 14 |
| `paper_order_submitted_v1` | 6 |
| `exit_signal_v1` | 12 |
| `position_opened_v1` | 1 |
| `position_reconciled_v1` | 1 |
| `position_closed_v1` | 1 |

### Cadence Fields — Batch 3B-2 Targets

| Field | Events | Sample value |
|-------|--------|-------------|
| `market_evaluation_duration_ms` | **28** ✓ | `2187` ms |
| `market_sequence_index` | **28** ✓ | `1` |
| `market_evaluation_started_at` | **28** ✓ | `2026-06-26T20:16:16.792309` |
| `decision_cycle_interval_seconds` | **51** ✓ | populated |

All cadence fields from the moved methods (`_scheduler_cadence_observability_detail`) are present and correctly shaped.

### Out-of-Scope Field Checks (confirmed not moved)

| Field | Events | Expected |
|-------|--------|---------|
| Quote lineage fields | 0 | 0 ✓ (permanent on trader) |
| `_last_quote_lineage_context` refs | 0 | 0 ✓ |

---

## 5. Paper Safety Confirmation

| Safety check | Evidence |
|-------------|---------|
| No live orders | [A] `STATUS NO LIVE ORDERS` in TUI throughout ✓ |
| No wallet collateral | [A] Paper mode — no CLOB write APIs ✓ |
| Paper execution working | [A] `paper_order_submitted_v1: 6` + `position_opened_v1: 1` + `position_closed_v1: 1` ✓ |

---

## 6. Shutdown Behavior

SIGTERM at 420s limit (timeout wrapper). Process exited cleanly with code 0. Consistent with all prior paper validation runs.

---

## 7. Comparison with Pre-Commit Validation

| Metric | Implementation paper run (pre-commit) | Post-commit (this run) |
|--------|--------------------------------------|----------------------|
| Cycles | 6 | **7** |
| Exit code | 0 | 0 |
| `market_evaluation_duration_ms` events | 24 | **28** |
| `decision_cycle_interval_seconds` events | 44 | **51** |
| AttributeError | 0 | 0 |
| Paper trade lifecycle | position open+close | position open+close |

Field counts vary with run-to-run market window timing — both runs show healthy emission.

---

## Final Verdict

```
POST_BATCH_3B2_RUNTIME_VALIDATED
```

**Summary:** Batch 3B-2 commit `381cbc4` validates cleanly post-commit. 7 paper cycles, exit 0, 0 errors. All cadence telemetry fields (`market_evaluation_duration_ms`, `market_sequence_index`, `market_evaluation_started_at`, `decision_cycle_interval_seconds`) present and correctly shaped in 28–51 JSONL events. Paper trade lifecycle (open + close) completed. `STATUS NO LIVE ORDERS` confirmed throughout. No regression from pre-commit validation runs. Batch 3C has not started.
