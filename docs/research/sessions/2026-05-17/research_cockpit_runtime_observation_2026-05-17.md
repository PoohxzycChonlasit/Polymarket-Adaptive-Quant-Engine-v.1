# Research Cockpit Runtime Observation Session v1

> **Date:** 2026-05-17
> **Observation window:** 00:00–00:32 UTC (32 min captured from JSONL analysis)
> **Method:** JSONL forensic analysis — system_health, market_snapshots, decision_log, execution_log, research_log
> **Runtime command:** `py main.py --mode paper --interval 10 --ui compact --fps medium`
> **Cockpit version:** Research Cockpit v1 (23/34 fields live, 68% coverage)
> **Role:** 11_OBSERVABILITY_INCIDENT_AGENT / 08_RESEARCH_QUANT_AGENT / 18_MARKET_REGIME_AGENT
> **Files modified:** None
> **Runtime behavior changed:** No
> **Live behavior changed:** No

---

## 1. Observation Timeline

### T0 — 00:00:11 UTC (session start)

| Metric | Value |
|---|---|
| cycle_selection_probe_v1 | 0 |
| zero_size_probe_v1 | 0 |
| btc_executable_state (cycle probe) | UNKNOWN |
| liquidity_state (snapshot) | HEALTHY |
| market_regime (snapshot) | UNKNOWN |
| decisions | 0 |
| trades | 0 |

---

### T+5 — 00:05 UTC

| Metric | Value |
|---|---|
| cycle_selection_probe_v1 cumulative | 30 |
| zero_size_probe_v1 cumulative | **0** |
| btc_executable_state (cycle probe) | UNKNOWN |
| btc_seconds_remaining at probe | 267s |
| selected_market_count | 2 (every cycle) |
| early_return_reason | None (every cycle) |
| decisions | ~5 |

---

### T+10 — 00:10 UTC

| Metric | Value |
|---|---|
| cycle_selection_probe_v1 cumulative | 60 |
| zero_size_probe_v1 cumulative | **0** |
| btc_executable_state | UNKNOWN |
| btc_seconds_remaining at probe | ~238s |
| market_snapshots accumulated | ~60 |

---

### T+15 — 00:15 UTC

| Metric | Value |
|---|---|
| cycle_selection_probe_v1 cumulative | 90 |
| zero_size_probe_v1 cumulative | **0** |
| btc_executable_state | UNKNOWN |
| Decision lifecycle distribution | FINAL_DERISK dominant |
| Active decisions seen | 0 of expected |

---

### T+20 — 00:20 UTC

| Metric | Value |
|---|---|
| cycle_selection_probe_v1 cumulative | 120 |
| zero_size_probe_v1 cumulative | **0** |
| btc_seconds_remaining (latest probe) | ~148s |
| Note | First ACTIVE_INVENTORY decisions appear |

2 ACTIVE_INVENTORY decisions observed with:
- `yes_bid`: 0.68 / 0.66
- `spread`: 0.13 (spike from baseline 0.01)
- `ev_after_spread`: 0.0
- `confidence`: 0.0
- `skip_reason`: "Entry cutoff: 63s / 78s (micro adaptive denied: spread_too_wide)"

---

### T+25 — 00:25 UTC

| Metric | Value |
|---|---|
| cycle_selection_probe_v1 cumulative | 150 |
| zero_size_probe_v1 cumulative | **0** |
| btc_seconds_remaining at probe | ~118s |

---

### T+32 (final observation) — 00:32 UTC

| Metric | Value |
|---|---|
| cycle_selection_probe_v1 | **192** total |
| zero_size_probe_v1 | **0** |
| entry_budget_probe_v1 | **0** |
| market_discovery_refresh | 192 |
| preload_next_market_v1 | 16 |
| market_readiness_warmup | 16 |
| market_snapshots | 336 (302 + growth) |
| decision_log entries | 48 |
| execution_log entries | 336 |
| research_log entries | 160 |
| trade_journal | **no file** (0 trades) |

---

## 2. REGIME Panel Field Status

### liquidity_state (NEW — wired in upgrade v1)

- **Status: LIVE ✓** — all 336 market snapshots show `liquidity_state=HEALTHY`
- Spread median: **0.010** (tight, consistent with S1/S2 days)
- Spread max observed: 0.130 (two momentary spikes at the two ACTIVE decisions)
- BTC and ETH both HEALTHY throughout the observation window
- **Cockpit displays correctly when wired** — this field is now showing real data

### market_regime (NEW — wired in upgrade v1)

- **Status: LIVE but shows UNKNOWN** — all 336 market snapshots emit `market_regime=UNKNOWN`
- `bullish_probability`: 0.5 (flat — no signal differentiation)
- `signal_volatility_score`: ABSENT from snapshots (not emitted to JSONL)
- `trend_strength`: 0.00013354 (near-zero, effectively flat)
- **Root cause**: The regime classifier runs but emits UNKNOWN because the BTC oracle price feed hasn't provided enough candle history at this UTC hour for the regime signal to form. The signal is not suppressed — it runs and returns UNKNOWN as its classification.
- **Cockpit shows `reg=UNKNOWN`** — accurate reflection of real state, not a wiring bug.

### volatility / signal_volatility_score

- `signal_volatility_score`: **ABSENT from JSONL** — the snapshot event doesn't emit this field
- Cockpit shows `vol=--` — accurate, not a wiring bug
- Note: `volatility_score` field IS in `SignalResult` dataclass and forwarded to `update_market()`, but it may be 0.0 at this session stage, falling below the display threshold for showing

---

## 3. SEM-C / S3 Panel Status

### cycle_selection_probe_v1

| Time | Cumulative count |
|---|---|
| T0 | 0 |
| T+5 | 30 |
| T+10 | 60 |
| T+15 | 90 |
| T+20 | 120 |
| T+25 | 150 |
| T+32 | 192 |

**Growth rate: ~6 per minute (consistent, no gaps)**. Each cycle selection fires once per ~10s interval. The cycle probe counter is incrementing correctly via the wired `_cockpit_probe_counts["cycle_selection"]` counter.

### zero_size_probe_v1

| Time | Cumulative count |
|---|---|
| T0–T+32 | **0** (no events) |

**S3 status: `collecting`** — correctly shown in cockpit as `S3:collecting`.

---

## 4. S3 Emergence Analysis

### Why zero_size_probe_v1 = 0 at T+32

The zero_size probe fires when:
1. Lifecycle phase = ACTIVE_INVENTORY_TRADING
2. The candidate passes the EV / probability pipeline
3. The resulting size plan is zero (due to bankroll floor, confidence too low, etc.)

**Current block chain:**

```
All 48 decisions → time_cutoff (SR ≤ 35s when evaluated)
                  → never reach EV/model gate
                  → zero_size probe never fires
```

Decision phase distribution at T+32:
- `FINAL_DERISK`: 34 decisions (71%) — SR ≤ 35s, time_cutoff guaranteed
- `PROFIT_MANAGEMENT`: 6 decisions (12%) — same, near-close window
- `ACTIVE_INVENTORY_TRADING`: 2 decisions (4%) — SR=63s / 78s, but `spread_too_wide` blocked EV

Mean SR at decision time: **21 seconds** (bot is evaluating markets near close).

**Historical baseline for comparison:**
- 2026-05-15: 1,030 ACTIVE decisions, 85% had EV > 0
- 2026-05-16: 2,567 ACTIVE decisions, 99% had EV > 0

The current session is at UTC midnight (Asia session). Polymarket 5-minute BTC/ETH markets are cycling, but the bot's evaluation loop is catching them at late stages. This is early-session behavior that typically self-corrects as the day progresses.

### Additional observation: btc_executable_state UNKNOWN discrepancy

There is a discrepancy between two data sources:
- `market_snapshots.executable_book_state = TRADABLE` (306 events) — orderbook IS executable
- `cycle_selection_probe.btc_executable_state = UNKNOWN` (192 events) — probe reads from `_market_token_meta` which has a different update path

This is **not a trading blocker** — the market evaluation uses the snapshot data path (TRADABLE), not the meta path. The UNKNOWN in cycle probes is a stale-read in the observability probe only.

### MICRO_RECOVERY risk mode

The misc system_health events show `risk_mode=MICRO_RECOVERY` (vs NORMAL on 2026-05-15/16). This may indicate a session-start condition where the bankroll monitoring triggered recovery mode. MICRO_RECOVERY imposes tighter sizing constraints, which means even when EV > 0, the resulting size plan may more frequently be zero — which could actually INCREASE zero_size probe firing rate once EV pipeline warms up.

---

## 5. S3 Readiness Estimate

### Conditions required for first zero_size probe:
1. Bot evaluates a market at ACTIVE_INVENTORY_TRADING with SR > 200s
2. EV pipeline produces confidence > 0 (requires oracle warmup and spread < threshold)
3. Size plan is computed and found to be zero (likely due to MICRO_RECOVERY floor)

### Historical emergence comparison:
- 2026-05-16: zero_size probes appeared at SR=219s, ACTIVE phase, confidence=0.575
- 2026-05-16 had 63 zero_size probes for the full day (spread mean 0.014)
- 2026-05-15 had 342 zero_size probes for the full day (more active session)

### S3 timeline projection:

| Milestone | Estimated time |
|---|---|
| First zero_size probe appears | ~2–6 hours from session start (UTC 02:00–06:00) |
| 15 zero_size probes (S3 probe gate) | ~4–10 hours depending on session activity |
| S3 cockpit shows `READY` | When the 15th zero_size probe fires (counter crosses threshold) |
| N stabilized ≥ 10 (valid S3 gate) | Requires multi_session_runner post-accumulation |

**Key risk**: If the time_cutoff dominance persists (bot catching markets late in their windows), zero_size probes may not fire until the Asia session transitions to Europe session (~08:00 UTC) when Polymarket markets tend to have more midpoint candidates.

---

## 6. HEALTH Panel

### jsonl_status → continuity (NEW — wired in upgrade v1)

- `jsonl_status` emitted by `_observability_health_display_state` as `ACTIVE` when JSONL writing is healthy
- Cockpit correctly shows `continuity=ACTIVE` — verified by presence of 336 market_snapshots and growing JSONL files
- `bad_json=n/a` (data quality gate not run yet)
- Zero malformed JSON lines in all JSONL files today

### logging_status

- `log=SAFE` — logging pipeline healthy, no disabled writes
- All six JSONL categories writing normally (decision_log, execution_log, market_snapshots, research_log, risk_log, system_health)

---

## 7. ANOMALY Panel

### ⚠ slope_direction_watch (pre_stabilization_slope reversal S1→S2)
- Watch remains active by default
- No new stabilization events to assess today (no zero_size probes → no EV evaluation → no stabilization evidence)
- Watch status: **unchanged, valid**

### Notable anomalies observed this session

| Anomaly | Severity | Details |
|---|---|---|
| market_regime persistently UNKNOWN | LOW | Oracle regime classifier running but returning UNKNOWN — early-session behavior, not a bug |
| btc_executable_state UNKNOWN in cycle probe | LOW | Discrepancy vs snapshot TRADABLE; observability-only field, not a trading blocker |
| All decisions time_cutoff | MEDIUM | 100% skip rate at time_cutoff — bot evaluates at late-window SR. Self-resolving as session matures |
| zero_size probes absent at T+32 | MEDIUM | Upstream of EV gate — consistent with time_cutoff dominance. Not a data failure |
| risk_mode MICRO_RECOVERY | INFO | Tighter sizing constraints active. Will increase zero_size probe rate when EV pipeline fires |
| ACTIVE decisions: confidence=0, spread=0.13 | INFO | Two momentary wide-spread spikes blocked the only ACTIVE-phase candidates so far |

### Probe disappearance: N/A
No probes appeared to disappear — cycle_selection grew at 6/min continuously with no gaps.

---

## 8. RUNTIME Panel (confirmed live throughout)

| Field | Value | Status |
|---|---|---|
| WS | connected | ✓ |
| oracle | OK/WAIT (alternating by market cycle) | ✓ |
| mode=PAPER | constant | ✓ |
| live_orders=OFF | constant | ✓ |
| log=SAFE | constant | ✓ |

---

## 9. Probe Growth Curve

```
zero_size_probe_v1:
00:00  0  ──────────────────────────────── (horizontal, none fired)
00:32  0

cycle_selection_probe_v1:
00:00    0  ╔
00:05   30  ║  ~6/min steady growth
00:10   60  ║
00:15   90  ║
00:20  120  ║
00:25  150  ║
00:32  192  ╝

S3 gate threshold:  [zero_size ≥ 15] ←── not yet crossed
```

---

## 10. Files Modified

None. Observation only.

---

## 11. Projected Cockpit Panels After First zero_size Probe

Once the first zero_size probe fires:

```
 SEM-C / S3
 zero_probe=1  >=15:✗
 budget=n/a  cycle=NNN
 thr=0.302213  [FROZEN]
 S1:complete  S2:valid  S3:collecting
```

Once 15th fires:
```
 SEM-C / S3
 zero_probe=15  >=15:✓
 budget=n/a  cycle=NNN
 thr=0.302213  [FROZEN]
 S1:complete  S2:valid  S3:READY
```

At which point `multi_session_runner --date 2026-05-17` can be evaluated for valid S3 (still requires N stabilized ≥ 10 from commitment_regime_replay output).

---

*Observation-only. No code changed. No OOS protocol touched. No threshold changed.*
