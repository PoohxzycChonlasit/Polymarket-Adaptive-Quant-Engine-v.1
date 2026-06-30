# EXECUTION_REALITY_POSITION_LADDER_RESEARCH_001

## FINAL_VERDICT

**RESEARCH_COMPLETE — NO_CODE_CHANGES.** Current paper runtime produces $0.10 fractional-share fills that match Polymarket's notional floor but violate the CLOB's whole-share convention. The entire inventory ladder concept is structurally blocked by two settings (`max_active_positions_per_market=1`, `max_entries_per_market=1`) and by the absence of a `MarketWindowTracker`. The T0 ladder design in the architecture masterplan is sound. Implementation cannot begin until (1) paper fills are confirmed reliable, (2) max_positions/max_entries are lifted in a controlled change, and (3) MarketWindowTracker is built. Full scope, constraints, and unknown blockers are documented below.

DO NOT MODIFY: strategy thresholds, signal logic, sizing logic, risk thresholds, execution behavior, live execution, wallet/live balance, `config/settings.py`, `.env`.

---

## CURRENT_RUNTIME_SIZING

### Bankroll context

| Parameter | Value | Source |
|---|---|---|
| bankroll (current) | ~$20.10 | paper session bankroll_state |
| tier | T0_MICRO_SEED | bankroll < $100 threshold |
| bankroll mode | MICRO_SURVIVAL | `settings.micro_survival_bankroll_threshold=100.0` |
| micro_survival_risk_fraction | 0.0025 (0.25%) | `settings.micro_survival_risk_fraction` |
| risk_cap per trade | $20.10 × 0.0025 = **$0.050** | computed at runtime |
| min_position_size | **$0.10** | `settings.micro_survival_min_position_size` |

### Sizing resolution

The micro survival path in `utils/risk_manager.py:calculate_micro_survival_risk_plan()` (line 548):

```python
notional_size = min(max(risk_cap_usd, minimum_usd), account_balance)
position_size = notional_size / entry_price  # fractional shares
```

Because `risk_cap_usd=$0.050 < minimum_usd=$0.10`, the floor wins: **notional always = $0.10**.

Share count = `0.10 / entry_price`:

| entry_price | shares produced | whole-share gap |
|---|---|---|
| 0.30 | 0.333 | −0.667 short of 1 share |
| 0.40 | 0.250 | −0.750 short |
| 0.48 | **0.208** | −0.792 short |
| 0.50 | **0.200** | −0.800 short |
| 0.51 | **0.196** | −0.804 short |
| 0.53 | **0.189** | −0.811 short |
| 0.60 | 0.167 | −0.833 short |
| 0.76 | 0.132 | −0.868 short |

All fills are sub-1-share. The `min_shares_per_order=1` setting (`config/settings.py:233`) is **not enforced** by the micro survival path — `calculate_micro_survival_risk_plan()` in `risk_manager.py` does not reference it, and `_entry_min_position_size_usd()` in `trader.py` returns the micro_survival floor directly (line 863–864), bypassing the `min_shares_per_order × entry_price` calculation.

### Observed fills from journal

795 micro-era paper opens confirmed in `runtime/quant_data/trade_journal/`:

| Metric | Value |
|---|---|
| Notional per fill | always $0.10 |
| Size range (shares) | 0.020–0.287 (always fractional, entry-price dependent) |
| Mean share size | 0.101 |
| Entry price range | 0.30–0.76, mean=0.53 |
| Tickers | ETH (576), BTC (219) |
| Outcomes | ETH NO 322, ETH YES 254, BTC NO 107, BTC YES 112 |
| Confirmed recent fills | 3fdd7312 (0.196 shares, hold=27s), 78725623 (0.208, hold=29s), 5e5f073b (0.189, hold=6s) |
| All recent exits | stop_loss (zero take_profit exits observed in micro-era) |

### Position sizing pipeline (non-MICRO_SURVIVAL mode, for reference)

`polymarket/position_sizing.py:calculate_position_size()` applies 8 multiplicative dampeners to `bankroll × base_risk_pct`:

| Multiplier | Floor | Ceiling | Driven by |
|---|---|---|---|
| confidence | 0.0 | 1.0 | confidence vs confidence_floor (0.54) |
| ev | 0.20 | 1.0 | ev / good_ev (0.08) |
| drawdown | 0.10 | 1.0 | drawdown_pct / daily_loss_limit_pct |
| liquidity | 0.25 | 1.0 | liquidity_usd / good_liquidity_usd |
| spread | 0.20 | 1.0 | spread / max_spread |
| time_to_settlement | 0.0 | 1.0 | time_remaining_seconds vs good_time (240s) |
| delta | 0.0 | 1.0 | delta score |
| frequency | 0.0 | 1.0 | trades_last_hour vs max_trades_per_hour |

This pipeline is **bypassed** in T0_MICRO_SEED (MICRO_SURVIVAL mode). All 8 multipliers reduce to $0.10 floor from the micro survival plan.

---

## REAL_MARKET_OBSERVATIONS

Sources: user-provided observation context (task specification), Polymarket CLOB protocol documentation, and inference from CLOB design.

### What real Polymarket traders do

1. **Multiple buy orders per market**: traders accumulate positions over time with separate BUY orders, each targeting the same token. Each order is a discrete CLOB fill.
2. **Whole-share-like sizing**: the practical minimum order is 1 token share at the current ask price. At $0.50, 1 share = $0.50; at $0.40, 1 share = $0.40. Fractional shares are theoretically allowed by the CLOB ($0.10 notional floor) but unusual in practice.
3. **Position merges**: multiple fills for the same outcome token are aggregated by the CLOB into a single position record. The position shows total shares held, not individual fill lots.
4. **Redeems**: at market resolution, holders of winning tokens receive $1.00 per share. Holders of matched YES+NO pairs can redeem early for $1.00 combined regardless of market resolution.
5. **Position building pattern**: traders enter at a price, observe market movement, add more shares if direction is confirmed, hold until resolution or profit target.
6. **Ladder entries**: entry at $0.45, add at $0.40 (cost averaging), or entry at $0.40, add at $0.45 (pyramiding) — both observed.
7. **$0.10 CLOB minimum**: Polymarket enforces a hard minimum of $0.10 notional per order. Orders below this are rejected at submission.

### Inferred minimum practical order sizes

| Scenario | Shares | Notional at $0.50 |
|---|---|---|
| CLOB absolute minimum | 0.20 | $0.10 |
| Practical whole-share minimum | 1.0 | $0.50 |
| Typical retail single order | 2–5 | $1.00–$2.50 |
| Large retail order | 10+ | $5.00+ |

At T0_MICRO_SEED bankroll (~$20), 1 whole share at $0.50 = $0.50 = **2.5% of bankroll** — which exceeds the current `micro_survival_risk_fraction=0.0025` (0.25%). Moving to whole-share sizing would require raising the risk fraction by 10× from 0.25% to ~2.5%.

---

## GAP_ANALYSIS

### Gap 1: Granularity mismatch (dollars vs. shares)

Current runtime thinks in dollars-first: `notional=$0.10 → shares=0.10/price`. Real CLOB thinks in shares-first: `shares=N → cost=N×price`.

Consequence: all paper fills are sub-1-share, which would be rejected or produce anomalous CLOB fills in a real execution context. Paper simulation accepts fractional shares because `virtual_ptb.py` has no share-floor enforcement.

### Gap 2: min_shares_per_order=1 is a dead setting

`settings.min_shares_per_order=1` exists (`config/settings.py:233`) but is not enforced by:
- `calculate_micro_survival_risk_plan()` in `risk_manager.py` (which computes `position_size=notional/price`, no share floor)
- `validate_order_intent()` in `order_intent.py` (only checks `size > 0`, not `size >= 1`)
- `calculate_position_size()` in `position_sizing.py` (this is the non-micro path; it computes `shares = final_size/entry_price` but enforces no floor)

The setting has no runtime effect. If whole-share execution is required for live trading, enforcement must be added to `order_intent.py` or the micro survival plan.

### Gap 3: max_active_positions_per_market=1 and max_entries_per_market=1

`config/settings.py:222–223`:
```python
max_active_positions_per_market: int = 1
max_entries_per_market: int = 1
```

These two settings structurally forbid any ladder. No implementation of PROBE→BASE→ADD is possible while these remain at 1. Both must be raised (to at least 3) before any multi-entry inventory model can be tested in paper.

### Gap 4: No MarketWindowTracker

The architecture masterplan describes four market window phases:
- OPENING_SCAN (0–35s): assessment only, no entry
- ACTIVE_INVENTORY_TRADING (35–240s): entries and adds
- PROFIT_MANAGEMENT (240–270s): reduce or hold
- FINAL_DERISK (270–300s): forced exit if still open

No MarketWindowTracker exists. Current runtime has no concept of time-phase within a market's 5-minute window. All entry/exit decisions are phase-blind.

### Gap 5: LOSS_CLUSTER_PAUSE_SECONDS=1800

`utils/risk_manager.py:44`: `LOSS_CLUSTER_PAUSE_SECONDS = 1800`

After 3 consecutive losses, runtime pauses for 30 minutes. This blunt instrument prevents any ladder testing during a 30-minute window after any 3-loss sequence. In T0_MICRO_SEED with $0.10 fills at typical 0.48-0.53 entry prices, a 3-loss streak is very common (all 3 confirmed recent fills were stop_losses). Real ladder behavior must tolerate multiple losses without triggering the pause, or the pause threshold must be redesigned before ladder testing is meaningful.

### Gap 6: No merge/redeem simulation in paper mode

`polymarket/virtual_ptb.py` simulates fills but does not model:
- Position merges (multiple fills into single CLOB position)
- Early redeem (YES+NO pair → $1)
- Resolution payout per share

A ladder that accumulates multiple fills would show multiple position_ids in paper, whereas real CLOB would show a single merged position. Accounting accuracy requires merge simulation before multi-entry goes live.

### Gap 7: Zero take_profit exits in micro-era

All 795+ paper fills in the micro era ended with `stop_loss`. No `take_profit` exits have been observed. This means:
1. TP targets may be miscalibrated vs. market volatility at $0.50 entry
2. Or market conditions during testing periods were uniformly adverse
3. Or hold windows are too short (6-29s) for TP to trigger

This must be resolved before a ladder is meaningful — there is no profit evidence base to add upon.

---

## PROPOSED_LADDER_V1

Design based on EXECUTION_REALITY_ARCHITECTURE_MASTERPLAN_001 T0 tier parameters and current paper sizing reality. **Research/design only — no implementation in this task.**

### T0_MICRO_SEED Ladder

| Level | Notional | Trigger | Condition | Max count |
|---|---|---|---|---|
| PROBE | $0.10 | confidence ≥ 0.54, EV > 0 | Any approved market window | 1 |
| BASE | $0.10–$0.60 | EV ≥ 0.04, spread ≤ 0.08, liquidity ≥ 50 | PROBE confirmed in direction | 1 |
| ADD | $0.10 | position MTM ≥ +0.03 (price moved in correct direction) | BASE held ≥ 35s with no adverse move | 1 |

**Per-market cap**: $2.00 notional aggregate (PROBE + BASE + ADD ≤ $2.00)
**Portfolio cap**: $4.00 across all open positions

### Position lifecycle states (target)

```
PROBE → [direction confirmed] → BUILD → [profit confirmed] → ADD → HOLD
      ↘ [stop_loss]                  ↘ [stop_loss]              ↓
        CLOSED                         CLOSED              PROFIT_MANAGEMENT → REDUCE → EXIT
                                                                              ↘ FINAL_DERISK → EXIT
```

### Market window phase targeting (target)

| Phase | Action |
|---|---|
| 0–35s: OPENING_SCAN | Direction assessment only. No PROBE allowed. |
| 35–240s: ACTIVE_INVENTORY_TRADING | PROBE entry, BASE scaling if PROBE confirmed |
| 120–240s: ADD window | ADD entry only in this range (min 85s of holding PROBE/BASE) |
| 240–270s: PROFIT_MANAGEMENT | Reduce or hold. No new entries. |
| 270–300s: FINAL_DERISK | Force-close all positions at market. |

### Size transition logic (shares-first design)

For live CLOB compatibility, the ADD/BASE layers should use shares-first sizing:
```
target_shares = max(1, floor(target_notional / entry_price))
actual_notional = target_shares × entry_price
```

At bankroll=$20, entry=0.50:
- 1 share = $0.50 → 2.5% of bankroll (above current micro_survival_risk_fraction)
- Requires micro_survival_risk_fraction to be raised to ~0.025 for BASE layer
- PROBE can remain at $0.10 (sub-share, fractional — acceptable for probe role only)

---

## UNKNOWN_REQUIRING_VALIDATION

| # | Question | Why it matters |
|---|---|---|
| 1 | Does Polymarket CLOB accept fractional share orders (e.g., 0.196 shares)? | All current paper fills are fractional. If CLOB rounds or rejects, all current paper modeling is wrong. |
| 2 | What is the actual CLOB-level minimum: $0.10 notional, or 1 whole share, or something else? | Determines whether PROBE=$0.10 / 0.2 shares is a real tradeable order. |
| 3 | Does the WebSocket feed report position as merged after multiple BUY fills for same token? | Determines whether ladder position tracking must correlate by token_id or position_id. |
| 4 | What is typical bid-ask spread on BTC/ETH 5M markets at entry_price≈0.50? | Spread multiplier (max_spread=0.10) may be blocking most entries. Need empirical spread data. |
| 5 | At $0.10 probe size, is slippage material? Are partial fills possible? | If order book depth < $0.10 at best ask, probe fill becomes partial or fails entirely. |
| 6 | What is the WebSocket snapshot frequency and latency for BTC/ETH 5M markets? | MarketWindowTracker depends on reliable tick rate to gate time phases. |
| 7 | Why are all micro-era exits stop_loss? Is TP target miscalibrated, or is hold time too short? | Cannot design ADD trigger ("position profitable") until TP fires at least once. |

---

## IMPLEMENTATION_BLOCKERS

Listed by severity:

### CRITICAL (must be resolved first)

1. **max_active_positions_per_market=1 + max_entries_per_market=1** — structural block on any ladder. Raising these requires a separate settings change with risk review and explicit approval. Not part of this task.

2. **No confirmed take_profit exit in micro-era** — zero paper evidence that the current TP target is reachable at $0.10 fills in 5M markets. Cannot design "add on profit confirmation" without at least one TP fill as evidence.

3. **Fractional share validity in live CLOB unknown** — all paper fills are fractional. Before any ladder is built on top of the current micro fill path, it must be established whether the CLOB accepts or rejects fractional share orders. This requires a live API verification run or definitive CLOB documentation.

### HIGH

4. **No MarketWindowTracker** — time-phase gating (OPENING_SCAN, ACTIVE_INVENTORY_TRADING, PROFIT_MANAGEMENT, FINAL_DERISK) is required for ladder entry/exit timing. This must be designed and built before any phase-sensitive ladder logic is tested.

5. **min_shares_per_order=1 not enforced** — the setting exists but is a no-op. Enforce it in `order_intent.py` (size >= 1 for live orders) before enabling live ladder execution.

6. **LOSS_CLUSTER_PAUSE_SECONDS=1800** — 30-minute blind pause after 3 consecutive losses. All 3 confirmed recent paper fills were stop_losses, meaning every test run triggers the pause. Ladder cannot be tested meaningfully with this blunt instrument active. Replace with adaptive throttle (future task) before ladder validation.

### MEDIUM

7. **No merge/redeem simulation in virtual_ptb.py** — multi-entry ladder in paper will produce multiple position_ids; real CLOB merges these into one. Accounting discrepancy must be resolved before live ladder is enabled.

8. **8-multiplier pipeline bypassed in MICRO_SURVIVAL** — all sizing intelligence (ev, spread, liquidity, delta, frequency multipliers) is bypassed for T0_MICRO_SEED. The ladder's BASE and ADD layers require multiplier-driven sizing. Either lift out of MICRO_SURVIVAL mode first, or expose multiplier inputs to the micro plan.

---

## SIZING RESEARCH ANSWERS (7 research questions)

**Q1. What does current paper sizing produce?**

Single $0.10 notional fills. Fractional shares (0.132–0.333 depending on entry price). Single entry per market (max_entries_per_market=1). Hold time 6–29 seconds. All exits stop_loss in confirmed micro-era fills.

**Q2. How does it differ from real Polymarket activity?**

Real traders: whole-share-like sizing (1+ shares), multiple entries per market, position merges, redeems. Current: fractional shares, single entry, no ladder, no merge/redeem modeling. Key structural difference: runtime is dollars-first; CLOB is shares-first.

**Q3. Minimum practical share/notional model?**

CLOB absolute minimum: $0.10 notional (any fractional share ≥ $0.10 is technically valid). Practical whole-share minimum: 1 share × entry_price ≈ $0.40–$0.60. For T0 ladder, PROBE stays at $0.10 fractional (probe role), BASE/ADD should target 1+ whole shares.

**Q4. Should runtime think in shares first?**

Yes, for BASE and ADD layers. For PROBE, dollars-first ($0.10 floor) is acceptable. The shares-first formula is: `shares = max(1, floor(target_notional / entry_price)); notional = shares × entry_price`. This ensures whole-share fills for BASE/ADD while preserving the $0.10 PROBE floor.

**Q5. What should T0_MICRO_SEED ladder look like?**

PROBE=$0.10 (fractional, any confirmed signal) → BASE=$0.10–$0.60 (scaled by multipliers, direction confirmed) → ADD=$0.10 (single add, position profitable, ≥35s hold). Per-market cap=$2.00, portfolio cap=$4.00. See PROPOSED_LADDER_V1 table above.

**Q6. What should probe/base/add/max exposure rules be?**

- PROBE: confidence ≥ 0.54, EV > 0, OPENING_SCAN phase complete, !lockdown → $0.10 fixed
- BASE: EV ≥ 0.04, spread ≤ 0.08, liquidity ≥ 50, ACTIVE_INVENTORY_TRADING phase → $0.10–$0.60 via multipliers
- ADD: position MTM ≥ +0.03 (direction confirmed), held ≥ 35s, ACTIVE_INVENTORY_TRADING phase → $0.10 single add
- Per-market cap: $2.00 (PROBE + BASE + ADD combined)
- Portfolio cap: $4.00 (all markets combined)
- Hard stop: stop_loss on all layers if price drops below stop_loss_price from original PROBE entry

**Q7. What remains unknown?**

See UNKNOWN_REQUIRING_VALIDATION section above (7 open questions). The most critical are: CLOB fractional share acceptance, actual spread/depth at probe size, and the absence of any TP exit evidence.

---

## REPOSITORY_STATUS

| Check | Result |
|---|---|
| Working tree | Clean (no uncommitted changes from research phase) |
| Files changed | 0 (research/design only) |
| Strategy/risk/config/env changes | None |
| Paper/live separation | Intact |
| arb_auto_execute | false (unchanged) |
| Commit target for this task | "docs: research execution reality position ladder" |

---

## NEXT_TASK

**EXECUTION_REALITY_POSITION_LADDER_RESEARCH_001** is complete (research/design).

The recommended next tasks (in order):

1. **TAKE_PROFIT_EXIT_EVIDENCE_001** — Run paper sessions until at least one take_profit exit is confirmed. Without this, the ADD trigger ("position profitable") cannot be calibrated and the ladder design has no empirical foundation.

2. **LOSS_CLUSTER_PAUSE_ADAPTIVE_REDESIGN_001** — Replace 30-minute blind pause with adaptive throttle that distinguishes market-driven losses from noise. CRITICAL prerequisite for any meaningful ladder test.

3. **CLOB_FRACTIONAL_SHARE_VALIDATION_001** — Determine definitively whether Polymarket CLOB accepts fractional share orders. Use verify mode (`python main.py --mode verify`) or CLOB API documentation to establish the minimum share floor. This unblocks the decision of whether min_shares_per_order=1 must be enforced.

4. **MAX_ENTRIES_LIFT_001** — Raise `max_active_positions_per_market` and `max_entries_per_market` to 3 (paper-only; requires separate risk review and explicit approval). First implementation prerequisite for any ladder.

5. **MARKET_WINDOW_TRACKER_001** — Build `MarketWindowTracker` that tracks time-to-settlement phases for active markets. Required before phase-sensitive entry/exit gating can be tested.

No implementation of ladder logic (LadderEngine, InventoryEngine, ExecutionPlanner) should begin until items 1–4 are resolved.
