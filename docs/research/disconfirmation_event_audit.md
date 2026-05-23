# Disconfirmation Event Audit

Generated: 2026-05-23  
Scope: read-only evidence audit for the first ACTIVE TP and first >30s TP events.  
Sources:

- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`
- `runtime/quant_data/decision_log/2026-05-23.jsonl`

No code, replay, runtime, policy, strategy, risk, execution, live, or S3 changes were made.

## Method

- TP / SL and PnL are from `trade_journal` `trade_close`.
- Lifecycle, elapsed second, quote source, quote age, `quote_stale_ms`, EV, confidence, and entry context are joined from ENTRY `paper_fill` / `trade_open` using `paper_trade_replay_key`.
- First event ordering uses `timestamp_utc` on the close event.

## First ACTIVE TP

| Field | Value |
|---|---|
| Run ID | `20260523T015426Z_16036_ac5d7312` |
| Timestamp UTC | `2026-05-23T09:17:06.393106Z` |
| Hour | `09h` |
| Asset | `ETH` |
| YES / NO | `YES` |
| Lifecycle | `ACTIVE_INVENTORY_TRADING` |
| Elapsed | `52s` |
| Quote source | `decision_cycle_fetch` |
| quote_age_at_submit_ms | `10700.571` |
| quote_age_at_fill_ms | `10701.571` |
| quote_stale_ms | `10701.571` |
| EV | `0.1292856058507258` |
| Confidence | `0.5572498861432621` |
| Entry price | `0.53` |
| Exit price | `0.87` |
| PnL | `+0.0321929 USDC` |
| Result | `TP` |
| Close reason | `take_profit_target_reached` |
| Candidate ID | `candidate_fa687411bee0` |
| Signal ID | `signal_fa687411bee0` |
| Decision ID | `decision_fa687411bee0` |

## First >30s TP

The first >30s TP is the same trade as the first ACTIVE TP.

| Field | Value |
|---|---|
| Run ID | `20260523T015426Z_16036_ac5d7312` |
| Timestamp UTC | `2026-05-23T09:17:06.393106Z` |
| Hour | `09h` |
| Asset | `ETH` |
| YES / NO | `YES` |
| Lifecycle | `ACTIVE_INVENTORY_TRADING` |
| Elapsed | `52s` |
| Quote source | `decision_cycle_fetch` |
| quote_age_at_submit_ms | `10700.571` |
| quote_age_at_fill_ms | `10701.571` |
| quote_stale_ms | `10701.571` |
| EV | `0.1292856058507258` |
| Confidence | `0.5572498861432621` |
| Entry price | `0.53` |
| Exit price | `0.87` |
| PnL | `+0.0321929 USDC` |
| Result | `TP` |
| Close reason | `take_profit_target_reached` |

## Related Disconfirmation Events

| Timestamp UTC | Asset | Side | Lifecycle | Elapsed | quote_stale_ms | Entry | Exit | PnL | Result |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| `2026-05-23T09:17:06.393106Z` | ETH | YES | ACTIVE_INVENTORY_TRADING | 52s | 10701.571 | 0.53 | 0.87 | +0.0321929 | TP |
| `2026-05-23T09:22:03.679302Z` | BTC | YES | ACTIVE_INVENTORY_TRADING | 74s | 11365.973 | 0.47 | 0.59 | +0.0121052 | TP |

The second row matters because it prevents an ETH-only explanation.

## Questions

### 1. Same trade or different?

Same trade for the first ACTIVE TP and first >30s TP.

- Shared replay key.
- Same timestamp: `2026-05-23T09:17:06.393106Z`.
- Same asset/side: ETH YES.
- Same lifecycle and elapsed: ACTIVE, 52s.

### 2. Single hour anomaly?

Likely yes for the current file set.

- All ACTIVE TP and >30s TP evidence appears in 09h UTC.
- 01h had an ACTIVE trade, but it was SL.
- 02h had multiple ACTIVE trades, all SL.
- 03h had a >30s OPENING_SCAN trade, also SL.

Current evidence supports a 09h regime cluster, not a day-wide ACTIVE edge.

### 3. 09h-only effect?

Yes in the current data.

| Hour | Trades | TP | SL | ACTIVE TP | >30s TP |
|---:|---:|---:|---:|---:|---:|
| 01h | 2 | 1 | 1 | 0 | 0 |
| 02h | 8 | 0 | 8 | 0 | 0 |
| 03h | 1 | 0 | 1 | 0 | 0 |
| 09h | 4 | 4 | 0 | 2 | 2 |

### 4. ETH-only?

No.

- First disconfirmation event: ETH YES, ACTIVE, 52s, TP.
- Second disconfirmation event: BTC YES, ACTIVE, 74s, TP.

The first event is ETH, but the broader disconfirmation is cross-asset within 09h.

### 5. Does event weaken or break opening edge?

It weakens the opening-only thesis, but does not fully break the idea that OPENING can be useful.

Evidence:

- OPENING TP did appear at 01h and 09h.
- OPENING also failed during the 02h-03h loss cluster.
- ACTIVE failed in 01h-02h, then succeeded twice in 09h.
- >30s timing failed earlier, then succeeded twice in 09h.

Interpretation: opening edge is not universal. ACTIVE and >30s entries can be profitable in the right regime, so a hard "opening only" or "no >30s" conclusion is overfit.

## Recomputed Classification

Classification: `EDGE_WEAKENING`

Rationale:

- Not `EDGE_INTACT`: the first ACTIVE/>30s TP directly disproves "all edge is OPENING_SCAN" and "all >30s entries fail."
- Not `EDGE_BROKEN`: the disconfirmation is concentrated in one observed hour and OPENING still produced TP outcomes.
- `EDGE_WEAKENING`: the edge appears conditional on market/hour regime, not structurally exclusive to opening.

## Final Verdict

The first ACTIVE TP and first >30s TP are the same ETH YES event at 09:17:06 UTC. The event weakens the opening-edge thesis because it proves ACTIVE/>30s can win, but it does not break the thesis outright because the evidence is still concentrated in 09h and sample size is small.

Runtime behavior changed: No  
Live behavior changed: No  
Tests: not run, docs-only  
Persistent tests unchanged
