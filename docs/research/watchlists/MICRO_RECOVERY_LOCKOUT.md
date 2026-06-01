# MICRO_RECOVERY_LOCKOUT Watchlist

type: living evidence tracker
priority: P0
status: VERIFIED (exit mechanism) / OBSERVED (duration patterns)
current_n: 5 episodes (5 completed, 0 ongoing)
last_snapshot: 2026-06-01
last_evidence_run: 2026-06-01
created: 2026-05-31
code_changed: No
strategy_changed: No
runtime_changed: No

---

## Purpose

Track long-duration MICRO_RECOVERY lockout episodes. A lockout episode begins
when `consecutive_losses ≥ 3` triggers MICRO_RECOVERY and ends when either
a win resets `_consecutive_losses = 0` or the process restarts.

The exit mechanism is architecturally **VERIFIED** by code trace. There is no
time-based exit, no daily reset, and no decay function on the consecutive-loss
counter (`utils/risk_manager.py`, `BankrollManager._consecutive_losses`).

```python
# Only two exit paths exist:
# Path A — in-session win:
def record_win(self, profit: float) -> float:
    self._consecutive_losses = 0  # ← sole in-session reset
    ...

# Path B — process restart:
def __init__(self, ...):
    self._consecutive_losses = 0  # ← resets on every new process
```

Duration patterns — how long episodes last and whether they self-terminate via
wins — are **OBSERVED** across scan log evidence (5 episodes, May 2026).

---

## Tracked Metrics (per episode)

| Metric | Definition |
|---|---|
| `episode_start` | UTC timestamp when consecutive_losses first reached 3 |
| `episode_end` | UTC timestamp when MR exited (win or restart); blank if ongoing |
| `duration_hours` | Wall-clock hours from start to end |
| `exit_reason` | `win` / `restart` / `unknown` / `ongoing` |
| `consecutive_loss_count` | Number of consecutive losses at peak (≥ 3 by definition) |
| `cycles_in_recovery` | Total scan cycles during which MR was the active skip reason |
| `candidates_conf_ge_075` | Candidates that reached conf≥0.75 during the episode |
| `trades_executed` | Trades that executed (conf≥0.75 cleared, not blocked downstream) |
| `wins_inside_episode` | Wins that occurred but did NOT clear MR (re-triggered by new losses) |
| `re_trigger_count` | Times the 30-min pause re-fired within the same episode |
| `notes` | Session IDs, anomalies, CLOB state |

---

## Promotion Criteria (OBSERVED → VERIFIED for duration patterns)

- n ≥ 10 completed episodes
- Exit-reason distribution stable across ≥ 5 calendar periods
- Average duration confirmed > 12 hours (current observed mean: ~26 hours for
  completed episodes)
- Self-termination via win confirmed as the dominant exit path OR restart
  confirmed as dominant path — both require n ≥ 5 per category

## Downgrade Criteria (OBSERVED → NOT_SUPPORTED for duration patterns)

- Average episode duration < 4 hours over n ≥ 5 new episodes
- Win-exit rate > 80% on n ≥ 5 new episodes (would suggest the loop
  is not a structural trap)

---

## Snapshot 1 — 2026-05-31

analysis_run: 2026-05-31
source: Scan log analysis, 201 scan_log_*.csv files, May 21–31 2026
sessions_with_mr: 40 / 201 (19.9%)
episodes_found: 5 (4 completed + 1 ongoing)
evidence_method: timestamp-based window detection on normalized_skip_reason

```
Episodes observed:   5 / 10   [################--------------------]  50.0%
Completed episodes:  4 / 10   [############------------------------]  40.0%
Win exits:           4 / 4    [########################################] 100% of completed
Restart exits:       0 / 4
```

### Episode Log

| # | Start (UTC) | End (UTC) | Duration | Exit | Peak losses | Trades exec | Wins inside | Re-triggers |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-05-22T00:00 | 2026-05-22T12:34 | ~12.5h | win | ≥3 | 1 | 0 | ≥3 |
| 2 | 2026-05-23T00:00 | 2026-05-24T04:32 | ~28.5h | win | ≥3 | 5 | unknown | ≥5 |
| 3 | 2026-05-25T02:32 | 2026-05-25T11:26 | ~8.9h | unknown (session end) | ≥3 | 0 | 0 | unknown |
| **4 (current)** | **2026-05-29T02:30** | **ongoing** | **53+ h** | **ongoing** | **5** | **0 today** | **5+ (May 30)** | **≥7** |

**Note on Episode 3:** The scan log shows MICRO_RECOVERY active at session end
on May 25. Exit classification is 'unknown' — the session terminated without
a confirmed win. Likely a restart-triggered reset.

**Note on Episode 4 (current):**
- Started ~2026-05-29T02:30 UTC (after the previous win_ended_mr at 02:26)
- May 30: 5 wins occurred inside MR but new losses re-triggered each time
- May 31: 0 trades executed as of 07:24 UTC (6 conf≥0.75 candidates all
  blocked by delta_extreme or risk_plan_zero)
- PID 17916 running continuously — no process restart, no counter reset
- This is the longest observed episode (previous longest: ~28.5h in Episode 2)

### Core Metrics

| Metric | Value |
|---|---|
| Total completed episodes | 4 |
| Episodes with win exit | 4 (100% of completed) |
| Episodes with restart exit | 0 |
| Episodes with unknown exit | 0 |
| Mean completed duration | ~17.5 hours |
| Max completed duration | ~28.5 hours (Episode 2) |
| Current episode duration | 53+ hours (ongoing) |
| Current is longest observed | Yes |
| Re-trigger rate | Every episode had ≥3 pause re-fires |
| Exit-then-retrigger | All 4 exits were followed by re-triggering within the same day |

### Exit Pattern Analysis

All 4 confirmed exits were via win. However:
- **Win does not permanently exit MICRO_RECOVERY.** In all 4 cases, new losses
  accumulated within the same day and MICRO_RECOVERY re-triggered.
- The win clears the counter, but BTC COMPRESSION at conf≥0.75 (the only cell
  MICRO_RECOVERY allows) has a 22.2% win rate. On average, 4 losses follow
  each win in the high-conf zone before another win can clear MR again.
- This makes MICRO_RECOVERY a recurring state rather than a rare exception.

### CLOB Interaction

CLOB degradation (high `clob_empty_response` rate) reduces conf≥0.75
candidate generation, extending lockout duration:
- May 30: 95% orderbook_unavailable → very few candidates reached conf≥0.75
- May 31: 2.7% clob_empty_response → 6 conf≥0.75 candidates in 7.4h,
  but all blocked by delta_extreme (timing gate) or risk_plan_zero

CLOB health and lockout duration are correlated: worse CLOB = fewer chances
for a conf≥0.75 win = longer lockout.

### 30-Min Pause Interaction

The 30-minute LOSS_CLUSTER_PAUSE fires when consecutive_losses ≥ 3. After
expiry, the system can attempt to trade but remains in MICRO_RECOVERY mode.
The pause re-fires on every subsequent loss. In Episode 4:
- Pause fired at ~18:41 UTC May 30 (loss #5)
- Pause expired at ~19:11 UTC May 30
- No executable conf≥0.75 candidate found before pause re-fired
- System has been looping: pause → expire → no conf≥0.75 → wait → repeat

---

---

## Snapshot 2 — 2026-06-01 (Episode #5 complete)

analysis_run: 2026-06-01
source: Scan log + decision log, May 31 – June 1 2026
episodes_since_snapshot_1: 1 new (Episode #5 completed)

```
Episodes observed:   5 / 10   [####################--------------------]  50.0%
Completed episodes:  5 / 10   [####################--------------------]  50.0%
Win exits:           4 / 5    [################################--------]  80.0% of completed
Restart exits:       1 / 5    [########--------------------------------]  20.0% ← first confirmed
Ongoing:             0        (process terminated June 1)
```

### Updated Episode Log

| # | Start (UTC) | End (UTC) | Duration | Exit | Trades exec | Wins inside | Re-triggers |
|---|---|---|---|---|---|---|---|
| 1 | 2026-05-22T00:00 | 2026-05-22T12:34 | ~12.5h | win | 1 | 0 | ≥3 |
| 2 | 2026-05-23T00:00 | 2026-05-24T04:32 | ~28.5h | win | 5 | unknown | ≥5 |
| 3 | 2026-05-25T02:32 | 2026-05-25T11:26 | ~8.9h | unknown (restart est.) | 0 | 0 | unknown |
| 4 | 2026-05-29T02:30 | ~2026-05-31T16:30 | ~82h (incl. win cycles) | win (final cycle cleared MR) | ~5 | 5+ (May 30) | ≥7 |
| **5** | **2026-05-31T16:35** | **2026-06-01T15:20** | **22h 44m** | **restart (process termination)** | **0** | **0** | **5+** |

### Episode #5 Detail

```
duration:                22h 44m (22.74h)
exit:                    restart — process terminated 2026-06-01T15:20 UTC
                         (no June 2 logs exist; log boundary confirmed)
executions:              0 — longest zero-execution run in episode history
scan_cycles:             14,898
conf_ge_075_candidates:  149 (all blocked — 0 executed)
  delta_extreme:         92  (61.7%)
  risk_plan_zero/ep002:  57  (38.3%)
ep002_candidates:        18 (May 31: 12 / June 1: 6)
clob_error_rate_at_end:  13.16%
last_decision:           2026-06-01T15:20:12 UTC
                         confidence_too_low (conf=0.44, BTC OPENING_SCAN, secs=289)

Blocker uniformity: skip distribution was STABLE across all 22h 44m
  delta_extreme=59.3%  confidence_too_low=23.1%  time_unsafe=12.0%
  clob_empty_response=5.1%  risk_plan_zero=0.4%
  No hour showed a materially different pattern — structurally frozen throughout.

Record broken: previous zero-execution reference = 20.3h
  Episode #5 crossed 20.3h at 2026-06-01T12:53 UTC (margin: +2h 26m)
```

### Updated Core Metrics

| Metric | Snapshot 1 (2026-05-31) | Snapshot 2 (2026-06-01) |
|---|---|---|
| Total completed episodes | 4 | **5** |
| Win exits | 4 (100% of completed) | **4 (80%)** |
| Restart exits | 0 | **1 (20%) — first confirmed** |
| Unknown exits | 1 (Episode #3) | 1 (Episode #3) |
| Mean duration (Episodes #1–3, #5) | ~16.6h | **~18.2h** |
| Longest zero-execution run | — | **Episode #5: 22h 44m** |
| Longest total MR period (incl. win cycles) | Episode #4: 53+ h | Episode #4: ~82h est. |
| Re-trigger count | Every episode ≥3 | Every episode ≥3 |

### Exit Path Confirmation

Episode #5 is the **first confirmed restart-exit** in the monitored episode set.
V6 (VERIFIED) architecturally documents both exit paths:

- **Path A (win):** `record_win()` → `_consecutive_losses = 0` — confirmed by Episodes #1, #2, #4
- **Path B (restart):** `__init__()` → `_consecutive_losses = 0` — confirmed by Episode #5

Directional observation (n=5, insufficient for statistical inference): zero-execution
episodes (#3, #5) appear more likely to exit via restart than win. Episodes with active
executions (#1, #2, #4) exited via win. The structural blocker chain prevents qualifying
wins from occurring in zero-execution episodes — so restart becomes the only exit path.
This is OBSERVED behavior, not yet VERIFIED at sufficient n.

---

*See also: [WATCHLIST_INDEX.md](WATCHLIST_INDEX.md) | [WATCHLIST_REVIEW_WORKFLOW.md](WATCHLIST_REVIEW_WORKFLOW.md) | [RESEARCH_FRONTIER_DASHBOARD.md](../RESEARCH_FRONTIER_DASHBOARD.md)*
