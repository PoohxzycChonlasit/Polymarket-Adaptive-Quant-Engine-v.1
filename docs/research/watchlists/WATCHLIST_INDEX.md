# Research Watchlist Index

type: index
created: 2026-05-30
last_updated: 2026-05-31
code_changed: No
strategy_changed: No
runtime_changed: No

---

## Active Watchlists

| Watchlist | Priority | Status | Current n | Required n | Last Snapshot |
|---|---|---|---|---|---|
| MICRO_RECOVERY_SELECTION | P0 | VERIFIED (mechanism) / OBSERVED (outcomes) | 40 conf≥0.75 | 100 | 2026-05-30 |
| MICRO_RECOVERY_LOCKOUT | P0 | VERIFIED (exit mechanism) / OBSERVED (duration) | 5 episodes | 10 episodes | 2026-05-31 |
| ETH_NO_COMPRESSION | P0 | OBSERVED | 52 | 350 | 2026-05-30 |
| BTC_COMPRESSION_OPENING_SCAN | P0 | OBSERVED | 59 | 150 | 2026-05-30 |
| ACTIVE_INVENTORY_EV_INVERSION | P1 | OBSERVED | 384 AI trades | 500 | 2026-05-30 |
| ORDERBOOK_STATE_HEALTH | P1 | OBSERVED | 402 | 600 | 2026-05-30 |

---

## Priority Definitions

- **P0** — Structural failure mode with confirmed mechanism. Directly affects entry quality or risk escalation. Monitor every session.
- **P1** — Confirmed directional pattern, insufficient n for VERIFIED. Monitor weekly or on new session batches.
- **P2** — Weak signal or early hypothesis. Monitor monthly.

---

## Governance Rules

1. **Do not promote any cell to VERIFIED** without n ≥ 50 per cell AND independent run replication across ≥ 3 sessions from different calendar periods AND calendar breadth of ≥ 7 unique calendar dates in the evidence set.
2. **Do not downgrade to NOT_SUPPORTED** until p > 0.30 (lower tail) on new n ≥ 50 data.
3. **All findings are evidence only.** No strategy, risk, EV, confidence, or execution changes from watchlist data alone.
4. **Snapshot append rule:** Add a new snapshot when ≥ 10 new trades arrive in any tracked cell, OR when 7 calendar days have elapsed — whichever comes first.
5. **Snapshots are append-only.** Never overwrite a previous snapshot entry.
6. **Each snapshot must record:** n, W, win rate, calibration gap, sessions count, and the analysis run date.

---

## Review Triggers

| Trigger | Action |
|---|---|
| ≥ 10 new trades in any tracked cell | Append snapshot to that cell's watchlist file |
| 7 calendar days elapsed | Append snapshot to all active files |
| Any cell reaches promotion n threshold | Flag in this index, request dedicated audit session |
| Any cell win rate moves > 5pp from last snapshot | Flag as movement alert in snapshot header |
| P0 cell crosses p < 0.05 (correct tail) | Immediate audit, governance decision required |
| MICRO_RECOVERY_LOCKOUT episode ends (win or restart) | Append episode snapshot immediately |
| MICRO_RECOVERY_LOCKOUT episode duration exceeds 24h | Append interim snapshot noting duration milestone |

---

## Classification Definitions

| Status | Criteria |
|---|---|
| VERIFIED | n ≥ 50 per cell, p < 0.05 correct tail, ≥ 3 independent session replications |
| OBSERVED | Directional pattern confirmed, n insufficient for statistical significance |
| WEAK_SIGNAL | Pattern present but inconsistent across sessions or n < 20 |
| NOT_SUPPORTED | Data contradicts hypothesis with p > 0.30 on n ≥ 50 |
| DORMANT | Insufficient new data to update; paused pending more trades |

---

## Audit Session Evidence Basis

All Snapshot 1 data captured during research session covering:
- May 18–30, 2026 (12 calendar days, 56 independent sessions)
- 406 total real paper trades (post-filter)
- Decision log: ~14,636 indexed candidates
- Observability patches: Tier 1 (prob_model_reason, momentum_input, liq_usd) + Tier 2 (price_change_pct, realized_volatility, price_velocity, distance_from_ptb_pct)
