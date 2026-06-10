# Evidence Velocity Dashboard v1

## N70 Milestone Update - 2026-06-10

| Metric | Value |
|---|---:|
| Current canonical n | 70 |
| Remaining to n=100 | 30 |
| New opportunities today | 3 |
| Rolling 7-day rate | 1.43/day |
| Rolling 14-day rate | 1.57/day |
| Next formal trigger | n=80 |

| Regime | Count | Share |
|---|---:|---:|
| COMPRESSION | 21 | 30.0% |
| TREND_DOWN | 19 | 27.1% |
| SIDEWAY | 18 | 25.7% |
| TREND_UP | 12 | 17.1% |

N70 is complete. N71 begins the forward validation block.

This milestone update supersedes the pre-N70 current-state fields retained
below for historical context.

generated_at: 2026-06-06
scope: ETH YES FC OS evidence velocity
mode: docs-only research monitor
runtime_changed: No
strategy_changed: No
risk_changed: No
execution_changed: No

---

## Current State

Watchlist: ETH YES FIRST_CYCLE OPENING_SCAN hold > 15s
Status: VERIFICATION_IN_PROGRESS
Target: n = 100 canonical opportunities

| Metric | Value |
|---|---:|
| Current canonical n | 61 |
| Target n | 100 |
| Remaining to target | 39 |
| Progress | 61.0% |
| New opportunities today | 1 |
| New opportunities this ISO week | 1 |
| Latest qualifying opportunity | 2026-06-06 ETH YES TP, hold 23s, SIDEWAY, +$0.01160556 |

Progress bar:

```text
n=61/100  [########################------------]  61.0%
remaining [---------------39---------------]
```

Interpretation: evidence accumulation has resumed, but only by one canonical
opportunity after the post-May-31 stall. This is enough to move the monitor from
zero-growth to slow-growth, but not enough to trigger a watchlist snapshot.

---

## Growth Metrics

| Window | Canonical opportunities | Rate |
|---|---:|---:|
| Today, 2026-06-06 UTC | 1 | 1.00/day |
| ISO W23, Jun 1-6 | 1 | 1.00/week to date |
| Rolling 7 days | 3 | 0.43/day |
| Rolling 14 days | 29 | 2.07/day |

Daily canonical growth:

```text
Date        New  Cum  Chart
2026-05-18   1    1  #
2026-05-19   4    5  #####
2026-05-20   7   12  ############
2026-05-21  10   22  ######################
2026-05-22   8   30  ##############################
2026-05-23   2   32  ################################
2026-05-24   7   39  #######################################
2026-05-25   6   45  #############################################
2026-05-26   3   48  ################################################
2026-05-27   0   48  ################################################
2026-05-28   4   52  ####################################################
2026-05-29   3   55  #######################################################
2026-05-30   3   58  ##########################################################
2026-05-31   2   60  ############################################################
2026-06-01   0   60  ############################################################
2026-06-02   0   60  ############################################################
2026-06-03   0   60  ############################################################
2026-06-04   0   60  ############################################################
2026-06-05   0   60  ############################################################
2026-06-06   1   61  #############################################################
```

The growth chart shows the May 18-31 accumulation burst, the Jun 1-5 stall, and
the Jun 6 restart.

---

## ETA Table

| Scenario | Rate source | Rate | ETA to n=100 | Calendar estimate |
|---|---|---:|---:|---|
| Current slow-growth | Rolling 7 days | 0.43/day | 91 days | 2026-09-05 |
| Recent blended | Rolling 14 days | 2.07/day | 19 days | 2026-06-25 |
| Historical active window | May 18-31 active accumulation | 4.29/day | 9 days | 2026-06-15 |

ETA risk: the rolling 7-day estimate is dominated by the post-collapse stall.
The rolling 14-day estimate still includes the late-May accumulation burst and
may be optimistic if COMPRESSION remains absent. The safest operational reading
is that evidence is accumulating again, but velocity is not yet stable.

---

## Regime Composition

Canonical opportunity composition through n=61:

| Regime | Count | Share |
|---|---:|---:|
| COMPRESSION | 21 | 34.4% |
| TREND_DOWN | 18 | 29.5% |
| SIDEWAY | 15 | 24.6% |
| TREND_UP | 7 | 11.5% |

Regime notes:

- COMPRESSION remains the largest single contributor historically, but no new
  COMPRESSION opportunity was observed in the latest qualifying row.
- The Jun 6 qualifying opportunity was SIDEWAY, which keeps the watchlist alive
  outside COMPRESSION but does not prove SIDEWAY is independently promotable.
- TREND_DOWN remains an important secondary context to monitor, especially
  because recent non-COMPRESSION accumulation depends on it.
- TREND_UP remains the weakest historical sub-regime and should be monitored for
  drag if it becomes a larger share of future evidence.

---

## Watchlist Status

| Gate | Current | Target | Status |
|---|---:|---:|---|
| Canonical n | 61 | 100 | Not met |
| Remaining evidence | 39 | 0 | Accumulating |
| Snapshot trigger | 61 | 70 | Not due |
| Calendar week coverage | 3 observed weeks | 3+ | Met by W23 resumption |
| COMPRESSION recovery | 0% recent decision share | sustained recovery | Not met |

Current status: ACCUMULATING_SLOWLY.

Next dashboard update trigger:

- n >= 70, or
- 3+ new canonical opportunities in W23/W24, or
- COMPRESSION share recovers above the predefined monitoring threshold.

---

## Governor Verdict

Evidence accumulation has resumed, and canonical ETH YES FC OS should now be
tracked as n=61. However, the current velocity is weak: one new opportunity
after a multi-day stall does not restore the original May accumulation rate.

Do not promote the watchlist. Do not create runtime filters. Continue collecting
with special attention to whether future growth comes from SIDEWAY/TREND_DOWN or
whether COMPRESSION returns as the historical velocity engine.
