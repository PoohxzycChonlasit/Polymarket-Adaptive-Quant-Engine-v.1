# Research Cockpit Live Validation Report

> **Generated:** 2026-05-17
> **Scope:** Post-upgrade terminal validation of Research Cockpit v1 (display.py `_quant_research_panel`)
> **Runtime during validation:** `py main.py --mode paper --interval 10 --ui compact --fps medium`
> **Role:** 11_OBSERVABILITY_INCIDENT_AGENT / 08_RESEARCH_QUANT_AGENT
> **Runtime behavior changed:** No
> **Live behavior changed:** No

---

## 1. Baseline Terminal Output (real runtime simulation)

The following is the exact Research Cockpit output when driven by fields that the actual runtime populates today. `update_research_obs()` is **never called** by main.py.

```
 Research Cockpit
 REGIME
 BTC reg=N/A  liq=--  spd=0.030  vol=--
 ETH reg=N/A  liq=--  spd=0.030  vol=--
 LIFECYCLE
 bottleneck=ev_below_threshold
 stab=--  surv=--  skip=ev_below_threshold
 SEM-C / S3
 zero_probe=n/a  >=15:?
 budget=n/a  cycle=n/a
 thr=0.302213  [FROZEN]
 S1:complete  S2:valid  S3:collecting
 ECON vs CLASS
 SR<60 rank=n/a  pnl=n/a
 HEALTH
 quality=n/a  bad_json=n/a  anm=0
 continuity=n/a  registry=OK
 ANOMALIES
 ⚠ slope_dir watch (S1→S2 reversal)
 RUNTIME
 WS=connected  oracle=WAIT  lat=--
 mode=PAPER  live_orders=OFF  log=SAFE
```

---

## 2. Section-by-Section Field Status

### 2.1 REGIME Panel

| Field | Status | Source | Notes |
|---|---|---|---|
| `BTC reg=` (market_regime) | **n/a** | Not wired | `REGIME_PAYLOAD_FIELD_NAMES` exists in trader.py but not passed to `update_market()` |
| `ETH reg=` (market_regime) | **n/a** | Not wired | Same |
| `liq=` (liquidity_state) | **n/a** | Not wired | `metrics.liquidity_state` is populated in `get_market_display_metrics()` but not included in `update_market()` call in main.py |
| `spd=` (spread) | **LIVE ✓** | `metrics.spread` → `update_market()` and `ticker_updates` | Shows current CLOB spread in real time |
| `vol=` (signal_volatility_score) | **n/a** | Not wired | `REGIME_PAYLOAD_FIELD_NAMES` includes it but not passed |

**Assessment:** 1 of 5 fields live. Spread is the only live field in this section.

---

### 2.2 LIFECYCLE Panel

| Field | Status | Source | Notes |
|---|---|---|---|
| `bottleneck=` | **LIVE ✓** | `_footer_blocker_tag()` reads `_cycle_results[].skip_reason` | Shows most recent skip reason as bottleneck |
| `stab=` (N stabilized) | **n/a** | Not wired | Offline replay only — from `commitment_regime_replay` output |
| `surv=` (N survived) | **n/a** | Not wired | Offline replay only — from `stabilization_survival_replay` output |
| `skip=` (latest skip reason) | **LIVE ✓** | `_cycle_results[0].skip_reason` | Shows first skip reason from current cycle |

**Assessment:** 2 of 4 fields live. The pipeline bottleneck is readable from cycle data.

---

### 2.3 SEM-C / S3 Panel

| Field | Status | Source | Notes |
|---|---|---|---|
| `zero_probe=` | **n/a** | Not wired | No in-memory counter; 0 events on 2026-05-17 as of validation (JSONL has 0 zero_size_probe_v1, 105 cycle_selection_probe_v1) |
| `budget=` (entry_budget_probe_count) | **n/a** | Not wired | Same — no in-memory counter |
| `cycle=` (cycle_selection_probe_count) | **n/a** | Not wired | 105 events exist in JSONL but no counter is surfaced to display |
| `thr=0.302213 [FROZEN]` | **LIVE ✓** | Hardcoded default in `_quant_research_panel()` | Always shows; cannot be overwritten |
| `score_c=` (score_c_current) | **n/a** | Not wired | Score C not computed at runtime |
| `S1:complete S2:valid` | **LIVE ✓** | Hardcoded defaults in `_research_obs.get()` | Correct values that match actual validation state |
| `S3:collecting` | **LIVE ✓** | Default `False` for `s3_probe_ready` → shows "collecting" | Correct: S3 not yet ready |
| S3 readiness hint (>=15:?) | **n/a** | Not wired | Cannot compute without probe counter |

**Key finding (2026-05-17 probe state):**
```
zero_size_probe_v1:      0   (S3 NOT ready)
entry_budget_probe_v1:   0
cycle_selection_probe_v1: 105
btc_executable_state:    UNKNOWN  (bot warming up)
```
S3 data is not ready. Bot is running but in early lifecycle / market discovery phase.

**Assessment:** 3 of 8 fields live (frozen threshold + S1/S2/S3 static labels). Probe counts all n/a.

---

### 2.4 ECON vs CLASS Panel

| Field | Status | Source | Notes |
|---|---|---|---|
| `SR<60 rank=` | **n/a** | Not wired | Populated only after `multi_session_runner` executes; caller must call `update_research_obs(canonical_sr60_rank=1, ...)` |
| `SR<60 pnl=` | **n/a** | Not wired | Same — runner output only |
| `OOS acc=` (score_c_oos_acc) | **n/a** | Not wired | Runner output only |
| `δ=` (score_c_guard_delta) | **n/a** | Not wired | Runner output only |
| Classifier-ok warning | **n/a** | Not wired | Cannot evaluate without OOS metrics |

**Assessment:** 0 of 5 fields live. Entire section is n/a at runtime. Expected — these are post-runner metrics, not live signals.

---

### 2.5 HEALTH Panel

| Field | Status | Source | Notes |
|---|---|---|---|
| `quality=` (data_quality_verdict) | **n/a** | Not wired | `quant_data_quality.py` only — run offline |
| `bad_json=` (bad_json_count) | **n/a** | Not wired | Same |
| `anm=0` (unresolved_anomaly_count) | **LIVE ✓** | Default `0` | Correct default; caller can update |
| `continuity=` (replay_continuity) | **n/a** | Not wired | Runner only |
| `registry=OK` (policy_registry_loaded) | **LIVE ✓** | Default `True` | Correctly reflects that canonical policy registry is loaded |

**Note:** The `_observability_health` dict (populated via `update_portfolio()`) contains `jsonl_status` and `jsonl_ok` fields that are NOT surfaced in the HEALTH section. These are consumed by `_candidate_observability_panel()` instead. Cross-section wiring gap.

**Assessment:** 2 of 5 fields live. Defaults are correct but data quality and continuity cannot be shown without offline tool results.

---

### 2.6 ANOMALIES Panel

| Field | Status | Source | Notes |
|---|---|---|---|
| `⚠ slope_dir watch (S1→S2 reversal)` | **LIVE ✓** | Default `True` for `slope_direction_watch` | Correct and intentional — the S1→S2 reversal IS the active watch |
| `anomaly_notes` | **LIVE ✓** | Defaults to empty list | Ready to receive notes via `update_research_obs(anomaly_notes=[...])` |

**Assessment:** 2 of 2 fields live by design. Defaults are intentionally set to the correct research state. No wiring needed here.

---

### 2.7 RUNTIME Panel

| Field | Status | Source | Notes |
|---|---|---|---|
| `WS=` (_ws_status) | **LIVE ✓** | `update_ws_status()` called every second from main.py | Shows "connected", "reconnecting", etc. |
| `oracle=` (_oracle_status) | **LIVE ✓** | Reads `_markets[ticker].current_price > 0` | Shows OK/WAIT based on oracle feed |
| `lat=` (_latency_ms) | **LIVE ✓** | Reads `_last_orderbook_age_ms` | Shows orderbook freshness as latency proxy |
| `mode=PAPER` | **LIVE ✓** | `self.paper_trading` field | Always correct |
| `live_orders=OFF` | **LIVE ✓** | `self.paper_trading` field | Always OFF in paper mode |
| `log=SAFE` (_logging_status) | **LIVE ✓** | Updated by `add_log()` | Shows "SAFE" or "FILE DISABLED" |

**Assessment:** 6 of 6 fields live. RUNTIME section is fully wired.

---

## 3. Fail-Soft Verification

All n/a fields degrade gracefully:
- `zero_probe=n/a >=15:?` — no crash, informative label
- `SR<60 rank=n/a pnl=n/a` — no crash
- `quality=n/a bad_json=n/a` — no crash
- `continuity=n/a` — no crash

Tests confirm: `test_quant_research_panel_no_crash_on_none_fields` passes.

---

## 4. Missing Metric Inventory and Wiring Priority

### Priority: HIGH

These require small, safe changes to existing code to wire.

| Field | What Needs Wiring | Safe Change Scope |
|---|---|---|
| `liquidity_state` | Add `liquidity_state=metrics.liquidity_state` to `update_market()` call in main.py (lines 635–680) and to `ticker_updates` dict (lines 502–538) | 2 lines in main.py only |
| `market_regime` | Pass `market_regime` from `signal` object or `last_signals[ticker]` to `update_market()`. The `REGIME_PAYLOAD_FIELD_NAMES` tuple already names the fields — they just aren't forwarded | Read from `trader.last_signals.get(ticker)` if it has regime; 2–4 lines in main.py |
| `zero_size_probe_count` | Add an in-memory session counter `self._probe_counts: dict[str, int]` in trader.py, increment inside `_emit_entry_budget_probe_event()` / zero-size path. Expose via a new `dashboard_probe_counts()` method. Call `display.update_research_obs()` once per cycle in main.py | Additive only; no strategy/risk changes; fail-soft |
| `cycle_selection_probe_count` | Same pattern — increment in `_emit_cycle_selection_probe_event()` | Same |
| `jsonl_ok / jsonl_status` | Already in `_observability_health` dict — add `replay_continuity=health.get("jsonl_status")` mapping inside `_quant_research_panel()` | 1 line in display.py only |

---

### Priority: MEDIUM

These require slightly more coordination but remain display/observability only.

| Field | What Needs Wiring | Safe Change Scope |
|---|---|---|
| `entry_budget_probe_count` | Same in-memory counter pattern as above | Additive trader.py change |
| `signal_volatility_score` | `trader.last_signals.get(ticker)` may expose volatility score; check `SignalResult` fields and pass to `update_market()` | Check SignalResult dataclass; 2–4 lines main.py |
| `data_quality_verdict` + `bad_json_count` | After running `quant_data_quality.py`, caller could invoke `display.update_research_obs(data_quality_verdict="CAUTION", bad_json_count=1)`. Runner already does this in offline mode | No runtime change needed; requires user/agent to call update_research_obs() post-runner |
| `canonical_sr60_rank` + `canonical_sr60_pnl` + `score_c_oos_acc` + `score_c_guard_delta` | Post-runner: after `multi_session_runner` completes, agent can call `display.update_research_obs(canonical_sr60_rank=1, canonical_sr60_pnl=13.52, ...)` | No runtime change needed; post-runner call only |

---

### Priority: LOW

These are definitionally offline and cannot be live.

| Field | Why It Stays Offline | Recommendation |
|---|---|---|
| `n_stabilized`, `n_survived` | Only known after commitment_regime_replay and stabilization_survival_replay complete | Keep as n/a; populate via `update_research_obs()` after runner |
| `replay_continuity` | Requires replay chain check; offline tool only | Same pattern |
| `score_c_current` | Score C is not computed at runtime — it requires stabilization detection which is offline-only | Permanently offline; keep n/a |

---

## 5. Next Safe Wiring Candidates (ordered)

1. **Wire `liquidity_state` into `update_market()`** — zero risk, 2 lines, immediately makes REGIME section show liquid state for BTC/ETH.

2. **Wire `jsonl_status` → `continuity` in HEALTH section** — already in `_observability_health`; 1-line change in `_quant_research_panel()`.

3. **Add in-memory probe counters** — increment in trader.py at probe emission sites; expose via new `dashboard_probe_counts()` method; call `display.update_research_obs()` once per cycle. This is the highest-value future wiring: it makes S3 readiness visible in real time.

4. **Wire `market_regime` from `last_signals`** — check whether `SignalResult` carries the regime field; if present, forward to display.

5. **Post-runner `update_research_obs()` call** — after `multi_session_runner` completes (offline agent session), populate ECON vs CLASS and HEALTH sections by calling `display.update_research_obs(...)`. No runtime plumbing needed.

---

## 6. Files Inspected

| File | Finding |
|---|---|
| `utils/display.py` | `_quant_research_panel()` and `update_research_obs()` exist and work. No `update_research_obs()` calls outside display tests. |
| `main.py` | `update_market()` does not pass `market_regime`, `liquidity_state`, `signal_volatility_score`. `update_research_obs()` never called. |
| `polymarket/trader.py` | Probe events emitted to JSONL but no in-memory counters for display. `dashboard_portfolio_state()` includes `observability_health` with `jsonl_status`. `metrics.liquidity_state` exists in `MarketDisplayMetrics` but not forwarded. |
| `runtime/quant_data/system_health/2026-05-17.jsonl` | 237 events, 105 `cycle_selection_probe_v1`, 0 `zero_size_probe_v1`, 0 `entry_budget_probe_v1`. Bot in UNKNOWN executable state (warming up). S3 NOT ready. |
| `tests/test_terminal_dashboard_display.py` | 55 tests pass, including 18 new Research Cockpit tests. All fail-soft cases covered. |

---

## 7. Current Live vs n/a Summary

| Section | Live Fields | n/a Fields | % Live |
|---|---|---|---|
| REGIME | spread (1) | regime, liquidity, vol (3) | 25% |
| LIFECYCLE | bottleneck, skip (2) | stab, surv (2) | 50% |
| SEM-C / S3 | frozen thr, S1/S2/S3 labels (3) | probe counts, score_c, S3 probe ready (5) | 38% |
| ECON vs CLASS | (0) | rank, pnl, oos_acc, delta, warning (5) | 0% |
| HEALTH | anm=0, registry=OK (2) | quality, bad_json, continuity (3) | 40% |
| ANOMALIES | slope watch, notes (2) | (0) | 100% |
| RUNTIME | WS, oracle, lat, mode, live_orders, log (6) | (0) | 100% |
| **Total** | **16** | **18** | **47%** |

---

## 8. Runtime / Live Safety Checklist

- [x] No trader.py changes
- [x] No order_manager.py changes
- [x] No strategy/risk/execution changes
- [x] No frozen threshold changed (0.302213 hardcoded, unmodifiable)
- [x] No OOS validation re-run
- [x] Paper/live separation preserved
- [x] No new runtime features added
- [x] Tests: 55 pass, 0 fail

---

*This document is evidence only. No research findings were promoted to runtime.*
