# Evidence Velocity Root Cause Audit

**Status:** `RESEARCH_AUDIT`
**Generated:** 2026-06-07
**Cell:** ETH × YES × FIRST\_CYCLE × OPENING\_SCAN × hold > 15s
**Scope:** Docs only. No runtime changes. No strategy changes. No risk changes. No execution changes.
**Sources:** `runtime/research_exports/completed_trades_v1_2.csv` (n=440), `runtime/quant_data/decision_log/2026-06-0*.jsonl` (event counts only), `docs/research/evidence_velocity_dashboard.md`, `docs/research/frontiers/COMPRESSION_MARKET_ARCHETYPE.md`, `docs/research/campaigns/ETH_YES_FC_OS_DRIFT_AUDIT.md`, `docs/research/watchlists/ETH_YES_FC_OS.md`

> READ ONLY. No section authorizes a runtime change, strategy change, risk change,
> execution change, filter, or promotion decision.

---

## §0. Question Under Test

Why did canonical ETH YES FC OS growth slow from **4.29/day** (May 18–31,
n=60 in 14 days) to **0.14/day** (Jun 1–7, n=1 in 7 days)?

This audit quantifies the slowdown through a four-level execution funnel,
decomposes the loss into its causal factors, computes a counterfactual n,
and renders a verdict. The analysis does not rely on the campaign dashboard's
existing hypothesis — it derives the conclusion from first-principles funnel data.

---

## §1. Period Comparison

| Dimension | P1: May 18–31 | P2: Jun 1–7 |
|---|---|---|
| Calendar days | 14 | 7 |
| Active trading days (any execution in CSV) | 14 | 3 of 6¹ |
| Total canonical FC OS qualifying trades | 60 | 1² |
| Canonical rate | **4.29/day** | **0.14/day** |
| Ratio P2/P1 | — | **3.3% of P1 rate** |
| COMPRESSION share (decision cycles) | **43.1%** | **2.5%** |
| TREND\_DOWN share (decision cycles) | 14.7% | 36.5% |
| SIDEWAY share (decision cycles) | 21.4% | 27.2% |
| TREND\_UP share (decision cycles) | 12.4% | 18.8% |
| Total decision log events | ~344 K (est)³ | 55,419⁴ |

¹ Jun 1, 3, 6 have zero executed trades in the CSV export. Jun 6 had at least
1 executed trade (the canonical n=61 qualifying opportunity) but is not yet
reflected in the CSV export cutoff. Jun 3 had 136 decision cycles (~9 minutes
of coverage). Jun 7 is a partial day (incomplete at time of audit).

² n=61 − n=60 = 1 new qualifying trade (2026-06-06, SIDEWAY TP, hold=23s).

³ May 23–31 decision log data: 221,390 events (confirmed). May 18–22 estimated
at ~24,599/day × 5 days ≈ 123,000. Total P1 estimate: ~344,000 events.

⁴ Sum of daily decision log event counts: Jun 1=16,154 + Jun 2=13,572 +
Jun 3=136 + Jun 4=5,362 + Jun 5=9,659 + Jun 6=10,536 = 55,419. Jun 7 excluded
(partial day, ongoing). Note: Jun 6 has 10,536 events confirming bot was running,
even though the CSV export does not yet include Jun 6 executions.

---

## §2. Execution Funnel

Four levels measure where the velocity drop concentrates. Each level is
computed per calendar day to normalise for the different period lengths.

### Method note

`canonical_entry_lifecycle_phase` = `OPENING_SCAN` is used as the entry-phase
filter (not `lifecycle_phase`, which is dominated by exit-phase labels). The
FIRST\_CYCLE filter (`time_bucket == 'early_window'`) is an engine-internal
label not exported to the CSV; it accounts for a ≤2% difference between
ETH YES OS hold>15 and canonical FC OS in P1 (61 CSV rows vs 60 canonical).
Decision cycle counts are estimated from decision log event counts; the
rate of ~24,599 events/day comes from the COMPRESSION\_MARKET\_ARCHETYPE.md
source audit (221,390 events / 9 days, May 23–31).

### Funnel table (per calendar day)

| Level | What is measured | P1 rate | P2 rate | Ratio |
|---|---|---:|---:|---:|
| **L1** | Decision cycles (estimated) | ~24,599/day | ~9,236/day¹ | **37.5%** |
| **L2** | All-asset executed trades | **30.4/day** | **2.3/day** | **8%** |
| **L3** | ETH YES OS entries (entry-phase) | **7.64/day** | **0.58/day**² | **8%** |
| **L4** | ETH YES OS hold>15s | **4.36/day** | **0.17/day**³ | **4%** |
| **L5** | Canonical FC OS (FIRST\_CYCLE applied) | **4.29/day** | **0.14/day** | **3%** |

¹ 55,419 decision events / 6 calendar days (Jun 1–6).

² 3 trades from CSV (Jun 2, Jun 5 ×2) + 1 from research docs (Jun 6) = 4
ETH YES OS entries / 7 cal-days = 0.57/day. Using 0.58 rounded.

³ 1 qualifying trade (Jun 6) / 7 calendar days = 0.143/day.

### Multiplicative decomposition (qualifying/day = cycles/day × yield/cycle)

| Factor | P1 | P2 | Ratio | Interpretation |
|---|---:|---:|---:|---|
| Decision cycles/day | ~24,599 | ~9,236 | **37.5%** | Uptime shortfall: 62.5% reduction |
| Qualifying trades per 100k cycles | **17.42** | **1.80** | **10.4%** | Per-cycle yield collapse: 89.6% reduction |
| Combined | 4.29/day | 0.14/day | 3.3% | Matches actual |

**The per-cycle yield collapse (89.6%) is ~1.4× larger than the uptime reduction
(62.5%).** In a multiplicative model, per-cycle yield is the dominant factor.
Both channels are real; neither alone accounts for the full velocity loss.

The non-COMPRESSION yield also collapsed: P1 non-COMP yield = 19.9 per 100k
non-COMP cycles; P2 non-COMP yield = 1.85 per 100k (9.3% of P1). The per-cycle
yield collapse extends across all regime types, not only the COMPRESSION-absent
channel. COMPRESSION is the most salient single structural loss (highest PF,
35% of historical trades, 66% of PnL), but the per-cycle yield collapse is
broader — these constant gates (delta\_extreme, confidence/EV, hold attrition)
now have fewer COMPRESSION cycles to filter; without them, more non-COMP cycles
face the gates and fail. See §3 for the empirical decomposition.

**Governing limitation on all decompositions:** P2 produced n=1 qualifying trade.
Decomposing a single observation into percentage shares is inherently imprecise.
All fraction estimates in §3 and §5 carry wide uncertainty intervals.

### Where the funnel break concentrates

| Funnel step | P1 pass rate | P2 pass rate | Change | Interpretation |
|---|---:|---:|---:|---|
| L1 to L2 (execution rate per cycle) | 0.124% | 0.025% | −80% | Per-cycle yield collapsed — market conditions |
| L2 to L3 (ETH YES OS share of executions) | 25.1% | 25.0% | flat | No YES/NO/asset selection shift |
| L3 to L4 (hold>15 survival rate) | 57.0% | 25.0% | −56% | Attrition worsened — n=4, treat with caution |
| L4 to L5 (FIRST\_CYCLE filter) | 98.4% | ~100% | flat | Minimal; CSV/canonical reconciliation |

**Key finding:** The L1→L2 collapse is the primary funnel break. The YES/ETH/OS
selection share is stable, ruling out selection drift. Hold attrition worsened
but rests on n=4.

---

## §3. Velocity Decomposition

The velocity loss is attributable to four separable causal channels. The
regime-level channels (A–C below) are not independently additive — they reflect
one regime-mix shift viewed from three angles. They are presented as a single
regime table, then separated into their velocity contributions.

### 3a. Regime mix shift (single unified view)

| Regime | P1 share | P2 share | Shift | FC OS yield¹ | P1 FC OS |
|---|---:|---:|---:|---:|---:|
| COMPRESSION | **43.1%** | **2.5%** | **−40.6 pp** | 3.372 PF | 21 trades (35%) |
| TREND\_DOWN | 14.7% | 36.5% | +21.8 pp | 2.300 PF | 19 trades (31%) |
| SIDEWAY | 21.4% | 27.2% | +5.8 pp | 1.123 PF | 14 trades (23%) |
| TREND\_UP | 12.4% | 18.8% | +6.4 pp | 0.661 PF | 7 trades (11%) |
| UNKNOWN/EXTREME\_VOL | 8.4% | 13.0% | +4.6 pp | — | 0 trades |

¹ FC OS yield = profit factor within the ETH YES FC OS canonical set.
Not a direct measure of qualifying-trade frequency, but indicates edge quality.

**Regime mix verdict:** COMPRESSION's 40.6 pp collapse is the dominant structural
change. The replacement regimes (TREND\_DOWN, SIDEWAY, TREND\_UP) have lower FC OS
yield and produce qualifying opportunities at a different, lower rate.

### 3b. Channel-by-channel decomposition

**Channel A: COMPRESSION absence (Market Structure)**

Historical contribution: COMPRESSION produced 21/60 = **35% of qualifying trades**
at 1.50/day. Its near-complete disappearance (43.1% → 2.5%) eliminated this
channel entirely.

Quantified impact: At P2 actual bot coverage (37.5% of P1 rate), COMPRESSION should
have contributed 1.50/day × 6 days × 37.5% = **3.4 additional qualifying trades**.
Actual: 0. Loss from COMPRESSION absence alone: **~3.4 trades**. This is the
isolated COMPRESSION-only counterfactual contribution (see §4).

**Channel B: Bot uptime shortfall (Runtime)**

Decision cycle coverage in P2: 55,419 events across 6 calendar days vs
P1 equivalent of ~147,600 events (6 × 24,599). Coverage ratio: **37.5%**.

Jun 3 had 136 decision cycles (~9 minutes of bot operation vs a full day).
Jun 4–6 averaged 8,685 cycles/day (35% of P1 average).

**Jun 1 empirical check (16,154 cycles, 0 executions):** A sample of 162 events
drawn evenly across the Jun 1 decision log reveals the breakdown. All sampled
events were blocked at `admission_block_stage: RISK_GATE`. The candidate-level
block reasons were:

| Block reason | Share | Nature |
|---|---:|---|
| delta\_extreme | 57.4% | Market structure (volatility gate) |
| confidence\_too\_low | 24.7% | Market/EV (EV/probability signal) |
| time\_unsafe | 13.6% | Market state |
| clob\_empty\_response | 4.3% | Runtime (orderbook data) |

Jun 1 block reasons are predominantly market-condition driven (82% are regime
or EV conditions; 18% are runtime/data issues).

**P1 baseline check (new):** Evenly-sampled decision log events from May 25
(peak COMPRESSION period, n=200 of 21,347) show `delta_extreme` at **55.5%** of
blocked candidates and `bankroll_mode: MICRO_SURVIVAL` on **100%** of events.
May 28 (late P1, n=200 of 21,347) shows `delta_extreme` at **51.5%** and
`MICRO_SURVIVAL` at **100%**. A full-day scan of May 25 (all 37,820 decision
log events) confirms MICRO_SURVIVAL throughout the entire day.

**Cross-source conflict on bankroll\_mode:** The CSV records P1 executed trades
as NORMAL=353, DEFENSIVE=55, MICRO_RECOVERY=32, MICRO_SURVIVAL=0. The decision
log for May 25 (a peak-COMPRESSION P1 execution day) shows MICRO_SURVIVAL on
100% of 37,820 events — and zero executed cycles anywhere in the log file.
This means the decision log **structurally does not record executions**: its
`bankroll_mode` field is incapable of reporting the mode at execution time.
Cross-source inference between the log's mode labels and the CSV's executed-trade
modes is therefore unreliable, and MICRO_SURVIVAL's causal role is
**unresolved — a live candidate, not ruled out.** See §5c.

**Delta\_extreme finding stands (within-source):** The blocked-event
delta\_extreme rate (51–56% in P1 blocked cycles) is a within-source comparison
to Jun 1's 57.4%. It supports the conclusion that delta\_extreme is a relatively
constant gate, not a uniquely Jun 1 phenomenon. The known delta between periods
is COMPRESSION collapse (43.1% → 14.8% on Jun 1 itself).

Jun 1 regime sample across the full day: TREND\_DOWN 35.8%, SIDEWAY 28.4%,
COMPRESSION 14.8%, UNKNOWN 10.5%, TREND\_UP 10.5%. COMPRESSION had already
begun its decline from 43.1% to this 14.8% intermediate state before the
documented 12:00 UTC collapse threshold.

**Channel C: Hold attrition increase (Mixed — market structure + execution)**

P1 hold attrition within ETH YES OS: **43%** (61 of 107 entries survived hold>15).
P2 hold attrition within ETH YES OS: **75%** (1 of 4 entries survived hold>15).

P2 ETH YES OS entries observed:
| Date | Regime | hold\_seconds | Exit | Qualifying |
|---|---|---|---|---|
| 2026-06-02 | SIDEWAY | 6s | SL | No |
| 2026-06-05 | TREND\_DOWN | 11s | TP | No |
| 2026-06-05 | TREND\_DOWN | 15s | SL | No |
| 2026-06-06 | SIDEWAY | 23s | TP | **Yes** |

The fast-close pattern in TREND\_DOWN is directionally consistent with YES
positions facing a headwind in a downtrend (rapid SL hits or TP at compressed
targets). However, n=4 is too small to confirm a structural attrition shift.
The observed worsening (43% → 75%) should be treated as a candidate driver
to monitor as more P2 data accumulates, not as a confirmed rate change.

**Channel D: YES/NO selection ratio (No evidence of a shift; n=7 in P2)**

P1: YES = 41.6% of ETH OPENING\_SCAN entries (107 YES, 150 NO).
P2: YES = 42.9% of ETH OPENING\_SCAN entries (3 YES from CSV + est. Jun 6 / 7 total).
The YES selection share is directionally unchanged in the limited P2 sample.
The TREND\_DOWN-dominated P2 environment did not visibly bias the bot away from
YES entries. However, n=7 total ETH OS trades in P2 is too small to distinguish
a structural shift from noise. Downgrade to: no evidence of YES→NO shift in the
available data. YES positions that DO execute in P2 exit faster (Channel C), but
the selection rate appears stable.

**Channel E: Duplicate/canonical exclusion (Not a driver)**

P1: 62 raw execution rows → 60 canonical = 3.2% duplicate attrition.
This rate is a constant filter applied equally across all periods. It did not
change and does not explain any portion of the velocity shift.

---

## §4. Counterfactual

**Question:** What would canonical n be today under alternative historical
conditions? P2 window = Jun 1–6 (6 calendar days); baseline = n=60.

**Assumptions (stated explicitly):**
- P1 COMPRESSION qualifying rate = 21 trades / 14 days = 1.50/day
- P1 non-COMP qualifying rate = 39 trades / 14 days = 2.79/day
- P2 actual bot uptime = 37.5% of P1 equivalent (55,419 / 147,600 cycles)
- P2 actual COMP yield = 0 (confirmed: no COMP qualifying trades in P2)
- P2 actual non-COMP yield = 1 (the Jun 6 SIDEWAY TP)

| Scenario | What is restored | COMP | Non-COMP | P2 gain | n today |
|---|---|---:|---:|---:|---:|
| **Actual** | — | 0 | 1 | 1 | **61** |
| COMP-only, actual uptime | COMP frequency at 43.1% | +3.4 | 1 (actual) | ~4.4 | **~64–65** |
| COMP + non-COMP yield, actual uptime | Both yields at P1 rate | +3.4 | +6.3 | ~9.7 | **~70** |
| COMP + non-COMP yield, full uptime | Full P1 conditions | +9.0 | +16.7 | ~25.7 | **~86** |

**COMP-only counterfactual (cleanest isolated estimate):** Restoring only
COMPRESSION frequency to its historical 43.1% — holding non-COMP yield at the
actual observed P2 rate and actual bot coverage — yields **n ≈ 64–65**. This is
a narrow gain (3–4 trades over 6 days), highlighting that COMPRESSION alone
barely moves the needle when non-COMP yield has also collapsed.

**The non-COMP yield gap is the load-bearing finding:** Expected non-COMP
qualifying trades at P1 yield and actual uptime = 6.3. Actual = 1. This 6× gap
in non-COMPRESSION delivery is not explained by uptime (uptime is already held
constant). It implies hold attrition, delta\_extreme blocking, and/or EV gating
are suppressing non-COMP yield to 15.9% of its P1 level — consistent
with the 9.3% per-100k-cycle non-COMP yield ratio measured in §2.

**Theoretical ceiling (full P1 conditions):** n ≈ 86, within striking distance
of the n=100 promotion target. This scenario requires both COMPRESSION to recover
and bot uptime to return to P1 levels (~24,599 cycles/day sustained).

**Caveat:** All counterfactual rows assume P1 yield rates apply unchanged to P2.
The delta\_extreme and hold-attrition conditions that are suppressing P2 yield
might persist even if COMPRESSION returns, making these counterfactuals upper-bound
estimates.

---

## §5. Verdict

**D: Mixed**

The velocity collapse from 4.29/day to 0.14/day has two confirmed causal
channels and one candidate. The dominance ranking depends on the decomposition
method; both framings support A (market structure) as the larger factor, but the
difference is not large enough to rank with high confidence, and n=1 in P2 places
a hard ceiling on precision.

### 5a. Causal factor status table

| Factor | Verdict | Evidence |
|---|---|---|
| COMPRESSION collapse (A — Market Structure) | **Confirmed** | 43.1% to 2.5% (17x reduction); eliminated 35% of P1 qualifying-trade channel |
| Delta\_extreme + EV/confidence gates (A — constant filters) | **Confirmed (constant gates)** | Block-reason mix flat P1→P2: delta\_extreme 51–57%, confidence ~25%; not new Jun phenomena — COMPRESSION absence removes the cycles that cleared them in P1 |
| Hold attrition increase (A/Mixed) | **Candidate — n=4** | 43% to 75% attrition in P2; directionally consistent with volatility headwind |
| Bot uptime shortfall (C — Runtime) | **Confirmed** | 37.5% of P1 cycle rate; Jun 3 offline (136 cycles); Jun 4–6 partial |
| YES→NO selection shift (B — Canonical rules) | **No evidence of shift (n=7)** | YES share 41.6% to 42.9%; sample too small to confirm or rule out |
| FIRST\_CYCLE or hold>15 filter change (B) | **Ruled out** | Filter definitions unchanged |
| Duplicate attrition (B) | **Ruled out** | Constant 3.2% filter across both periods |

### 5b. Multiplicative ranking (per-cycle yield vs uptime)

| Factor | Magnitude | Type |
|---|---:|---|
| Per-cycle yield collapse | 89.6% reduction (17.42 to 1.80 per 100k cycles) | A — Market structure |
| Decision cycle shortfall | 62.5% reduction (24,599 to 9,236/day) | C — Runtime |

In the multiplicative model (qualifying/day = cycles/day × yield/cycle), the
per-cycle yield collapse is the larger factor. The same conclusion holds in the
non-COMPRESSION sub-channel: non-COMP yield fell 90.7% (19.9 to 1.85 per
100k), almost identically to the overall collapse, confirming that the yield
collapse extends across all regimes, not only the COMPRESSION-absent channel.

The per-cycle yield collapse is driven by A (market structure):
- COMPRESSION absence removes the highest-yield channel (PF=3.372, 35% of P1 trades)
  — this is the driver; the gates below are the constant mechanisms now applied to
  a lower-quality residual cycle set
- delta\_extreme blocks ~51–57% of candidates (constant rate across P1 and P2 blocked events)
- confidence/EV gates block an additional ~25% (similarly constant P1→P2)
- Hold attrition reduces qualify-through rate even for the few that pass

### 5c. Jun 1 zero-execution: consistent with COMPRESSION collapse (A+C confounded)

Jun 1 had 16,154 decision cycles (66% of P1 daily rate) and zero executed trades.
Empirical block-reason analysis (162 sampled events, evenly distributed) shows
82% of blocks were market-condition driven (delta\_extreme + confidence + time\_unsafe)
and 18% were runtime/data issues (clob).

**Confound acknowledged:** P1 decision log sampling (May 25 full day: 37,820
events; May 28: 200-event sample) shows 100% MICRO\_SURVIVAL and delta\_extreme
rates of 51–56% in blocked events. Jun 1 also shows 100% MICRO\_SURVIVAL and
57.4% delta\_extreme. However, the CSV records P1 executions as NORMAL/DEFENSIVE/
MICRO_RECOVERY with zero MICRO_SURVIVAL — indicating the two sources label
`bankroll_mode` differently. Cross-source inference on whether P1 executed
"despite MICRO_SURVIVAL" cannot be made; mode role is unresolved.

**Delta\_extreme** is more cleanly interpreted: within the blocked-event pool,
the rate was already 51–56% in P1, making Jun 1's 57.4% not a new deterioration
but a constant market filter. Delta\_extreme is not the discriminating change.

The known structural change is **COMPRESSION collapse**: 43.1% → 14.8% on Jun 1
itself. The most parsimonious reading of Jun 1's zero-execution is the removal of
the COMPRESSION-enabled window that allowed setups to clear all gates in P1.
MICRO\_SURVIVAL mode may or may not have co-contributed — that question is open
(see Channel B on the cross-source conflict; the decision log cannot speak to
execution-time bankroll mode).

The A+C factors are co-linear on Jun 1 and cannot be cleanly separated by
this observation alone.

**The bot running is a necessary condition, not a sufficient one.**
Uptime shortfall (C) explains the cycle deficit on other days, but Jun 1 shows
the bot can run 16,000+ cycles and still produce zero executions when market
conditions are unfavorable — consistent with A (market structure) being the
binding constraint in the per-cycle yield channel.

### 5d. What cannot be precisely ranked (n=1 caveat)

P2 produced one qualifying trade. Stating that A accounts for "35%" and C
accounts for "40%" of the velocity loss implies precision that a single-trade
outcome cannot support. The correct representation is:

- **A (market structure) caused a collapse in per-cycle qualifying yield across
  all regime types**, driven by COMPRESSION disappearance, delta\_extreme
  filtering, and EV/confidence gating — both constant gates now applied to a
  lower-quality residual set absent COMPRESSION cycles. This is the larger factor in the multiplicative
  decomposition and is supported by Jun 1 empirical data.
- **C (runtime) reduced the cycle budget by ~62.5%**, independently suppressing
  the number of opportunities the bot was available to observe. Jun 3 was
  effectively offline.
- These two factors compound multiplicatively. Neither is negligible. The
  per-cycle yield collapse is the primary engine of the velocity loss; the
  uptime shortfall amplifies it.

### 5e. Non-COMPRESSION channel status

TREND\_DOWN (PF=2.300) remains the only viable non-COMPRESSION accumulation vehicle.
SIDEWAY (PF=1.123) is marginal. TREND\_UP (PF=0.661) is loss-making.
The post-COMPRESSION decision-cycle mix has more TREND\_DOWN (14.7% to 36.5%)
but the qualifying yield from non-COMP in P2 fell to 9.3% of its P1 level,
consistent with delta\_extreme and hold-attrition suppressing execution even in
favorable non-COMP regimes.

---

## §6. Monitoring Implications

> No runtime changes. No strategy changes. No risk changes. No execution changes.

| Signal | Watch condition | Source |
|---|---|---|
| COMPRESSION recovery | Daily decision log COMPRESSION share > 5% sustained | Decision log analysis |
| P2 nc\_PF | Rolling non-COMP PF as TREND\_DOWN trades accumulate | Manual update when n≥70 |
| Hold attrition | ETH YES OS attrition rate over next 10–15 entries; alert if >60% sustained | Trade journal |
| Bot uptime | Decision cycle count per day vs 24,599/day baseline; alert if <10,000 for 2+ consecutive days | Decision log |

**n=70 trigger:** Currently requires 9 more qualifying trades. At actual P2 velocity
(0.14/day), ETA = 64 days (Sep 9). At COMPRESSION-absent but full-uptime rate
(P1 non-COMP only: 2.79/day), ETA = 3.2 days. The ETA is effectively gated on
either COMPRESSION returning or sustained TREND\_DOWN win runs at full bot coverage.

---

## §7. Data Quality Notes

**CSV export cutoff:** The `completed_trades_v1_2.csv` file does not include the
2026-06-06 canonical qualifying trade (confirmed in `evidence_velocity_dashboard.md`
and `ETH_YES_FC_OS_DRIFT_AUDIT.md`). All P2 CSV-derived counts should be read
as "CSV-available trades" not "all executed trades."

**FIRST\_CYCLE not in CSV:** The `time_bucket == 'early_window'` field used to
define FIRST\_CYCLE is not exported to the CSV. The L4→L5 gap (CSV: 61 hold>15
entries vs canonical n=60) is the FIRST\_CYCLE filter's effect. This filter is
effectively constant and not driving any period-to-period change.

**P2 attrition is n=4:** The 75% hold attrition figure for P2 (vs 43% in P1)
is based on 4 ETH YES OS entries in P2. It carries very wide confidence intervals
and should not be treated as a confirmed rate change until at least 20–30 P2
observations accumulate.

**Jun 1 zero executions:** Jun 1 had 16,154 decision cycles but 0 executed trades
in the CSV. This is consistent with the COMPRESSION collapse occurring at 12:00 UTC
and the Episode #5 restart at 15:20 UTC. The entire day's cycle budget was spent
either in the pre-collapse COMPRESSION window (which would not produce OPENING\_SCAN
entries if the collapse had already begun) or in the first-cycle initialization
of Ep5. This is an A+C interaction, not a pure C artifact.

---

*No code changes. No runtime changes. No strategy changes. No commits.*
*Audit produced: 2026-06-07*
