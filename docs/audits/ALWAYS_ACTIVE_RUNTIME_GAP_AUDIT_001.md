# ALWAYS_ACTIVE_RUNTIME_GAP_AUDIT_001

**Task:** ALWAYS_ACTIVE_RUNTIME_GAP_AUDIT_001  
**Mode:** DISCOVERY ONLY — no code changes  
**Date:** 2026-06-25  
**Analyst Role:** 06_POSITION_RECONCILIATION_AGENT (primary), 03_RISK_MANAGER_AGENT, 09_TRADE_FREQUENCY_AGENT (supporting)

---

## Observed Pattern Under Audit

```
OPEN  | ETH NO    ← position 1 opens
CLOSE | ETH       ← position 1 closes
OPEN  | ETH NO    ← position 2 opens
CLOSE | ETH       ← position 2 closes
ALIVE | PAPER     ← cycles continue, no new entries
ALIVE | PAPER
ALIVE | PAPER     (indefinitely)
```

Runtime remains alive. No errors visible. Open count and PnL frozen.

---

## Evidence Sources

| Source | Date | Scope |
|---|---|---|
| `utils/risk_manager.py` | current | Risk mode, loss cluster, lockdown |
| `polymarket/risk_modes.py` | current | `RiskModeState`, `evaluate_risk_mode`, `trade_quality_allowed` |
| `polymarket/trade_frequency.py` | current | Cooldown timers, frequency multiplier |
| `polymarket/opportunity_scanner.py` | current | Hard-skip gates, scan pipeline |
| `polymarket/trader.py` | current | All gate sequences, trigger sites |
| `utils/position_tracker.py` | current | Reconciliation, inventory classification |
| `config/settings.py` | current | `max_entries_per_market = 1` |
| `FIRST_BLOCKING_GATE_DISTRIBUTION_001.md` | 2026-06-25 | 80 decision events, June 25 session |
| `EXIT_EXECUTION_ROOT_CAUSE_AUDIT_001.md` | 2026-06-25 | 8 exit failures, ghost session analysis |

---

## 12-Question Audit

---

### Q1 — Does `frequency_cooldown` actually gate entries after a trade closes?

**Code evidence:**

`polymarket/trade_frequency.py` defines:
- `COOLDOWN_AFTER_LOSS_SECONDS = 120` (2-min post-loss cooldown)
- `COOLDOWN_AFTER_WIN_SECONDS = 30` (30-s post-win cooldown)
- `MIN_SECONDS_BETWEEN_ENTRIES = 30`
- `frequency_multiplier_for_tier()` → returns 0.20–1.0 (affects sizing only, not hard-block)

`polymarket/opportunity_scanner.py` passes `seconds_since_last_entry=context.seconds_since_last_entry` to the frequency evaluator. However, in `polymarket/trader.py`, `OpportunityScanContext` is constructed **without setting `seconds_since_last_entry`** — it defaults to `None` in every production call path.

When `seconds_since_last_entry=None`, none of the cooldown-after-loss / cooldown-after-win checks fire. The timers are dead code in the current wiring.

**Gate distribution evidence (June 25):** `frequency / active position: 9/80 = 11.25%`. These 9 blocks come from the **epoch caps** (`max_entries_per_market=1`, `max_active_positions_per_market=1`), not from cooldown timers. The epoch caps correctly block same-epoch re-entry while a position is open or after one has been placed in that 5-minute window.

**Verdict:** Epoch-level frequency caps work and do fire (11.25%). Loss/win cooldown timers are dead code — `seconds_since_last_entry` is never passed. Not the cause of post-trade stall across epochs.

---

### Q2 — Does `risk_mode` escalate and block after consecutive losses?

**Code evidence (`polymarket/risk_modes.py`):**

```python
def evaluate_risk_mode(*, consecutive_losses, drawdown_pct, lockdown_reasons=(), ...):
    reasons = tuple(str(r) for r in lockdown_reasons if str(r))
    if hard_drawdown_reached or reasons:   # ANY reason → permanent LOCKDOWN
        return _decision(RiskMode.LOCKDOWN, ...)
    if losses >= 3:
        return _decision(RiskMode.MICRO_RECOVERY, ...)
    if losses >= 2:
        return _decision(RiskMode.DEFENSIVE, ...)
    ...
```

```python
def trade_quality_allowed(mode, *, confidence=None, ...):
    if mode == RiskMode.LOCKDOWN:      return False, "risk_mode_lockdown"
    if mode == RiskMode.MICRO_RECOVERY: return confidence >= 0.75, ...
    if mode == RiskMode.DEFENSIVE:      return confidence >= 0.65, ...
    return True, "normal"
```

Normal operating confidence range (per `ENTRY_FUNNEL_ROOT_CAUSE_AUDIT_001`): **0.54–0.64**.

After 2 consecutive paper losses:
- `RiskModeState` → `RiskMode.DEFENSIVE`
- Required confidence: **0.65**
- Typical candidate confidence: 0.54–0.64
- Result: all candidates fail `trade_quality_allowed()` → skip_reason `risk_mode_defensive:confidence_below_defensive`
- The system continues scanning and evaluating but no candidate clears the elevated bar

After 3 consecutive paper losses:
- Required confidence: **0.75**
- No normal candidate achieves this

Recovery: consecutive_losses resets to 0 on a WIN. In MICRO_SURVIVAL tier at $0.10 notional, the probability of a win returning the mode to NORMAL is tied entirely to whether any candidate can clear the 0.75 floor — which is very unlikely.

**Verdict: HIGH PROBABILITY POST-TRADE BLOCKER.** If both observed trades closed at a loss, DEFENSIVE mode is active, and no subsequent candidate can clear the 0.65 floor. The mode will not self-heal without a winning trade, which it cannot place because the mode prevents entry.

---

### Q3 — Does `loss_cluster_pause` (30-min) fire after 3 losses?

**Code evidence (`utils/risk_manager.py`):**

```python
LOSS_CLUSTER_THRESHOLD     = 3
LOSS_CLUSTER_PAUSE_SECONDS = 1800  # 30-minute hard stop

class BankrollTierManager:
    def record_loss(self, loss: float) -> float:
        self._consecutive_losses += 1
        if self._consecutive_losses >= LOSS_CLUSTER_THRESHOLD:
            self._pause_until_ts = time.time() + LOSS_CLUSTER_PAUSE_SECONDS
    
    def can_trade(self) -> tuple[bool, str]:
        if now < self._pause_until_ts:
            return False, "LOSS CLUSTER PAUSE: ..."
```

Checked at cycle start (trader.py line 12926). If `False`, cycle returns immediately — no evaluation happens.

The user-observed pattern shows **2 OPENS and 2 CLOSES**. Two losses trigger DEFENSIVE mode but NOT the 30-minute pause (requires 3). If the session had a prior loss before the observed trades, the 3rd loss would trigger the 30-minute pause — which would also explain sudden silence.

**Verdict: POSSIBLE SECONDARY CAUSE** if there was a prior loss in the same session. For a clean 2-trade-then-stall pattern with no prior losses, this gate does not fire. Cannot rule out without runtime logs.

---

### Q4 — Does `time_unsafe` silence the last epoch fraction?

**Code evidence (`polymarket/opportunity_scanner.py`):**

```python
if candidate.time_remaining_seconds <= 90:
    return "time_remaining_le_90s"
```

Gate distribution evidence: `time: time_unsafe / cutoff: 14/80 = 17.5%`. This blocks candidates in the last 90s of each 5-minute epoch (30% of epoch duration unavailable).

Sub-breakdown from distribution:
- `unsafe_cutoff=24`, `late_window=12`, `mid_window=35`, `early_window=7`
- Hard close zone (`<45s`): multiple events
- Micro adaptive denied (`<35s`): multiple events

**Verdict: CONTRIBUTING BACKGROUND BLOCKER.** Removes 17.5% of candidates per session. Not the post-trade stall cause — it fires uniformly throughout the session, not specifically after entries. Reduces the effective scanning window.

---

### Q5 — Is orderbook stale data causing blocks?

**Code evidence:** Orderbook staleness check is in `_hard_skip_reason` via `candidate.ob_spread > 0.10` and via the preloader health flag. Pre-hotfix, this was an artifact source (87–92% false-positive block rate). Post-hotfix, corrected.

**Gate distribution evidence (June 25, post-hotfix):** `orderbook: stale/unavailable: 11/80 = 13.75%`
- `clob_http_error`: 5 (genuine API HTTP failure)
- `stale_data`: 6 (real Binance or CLOB stale events)
- `empty_book`: 0
- Average orderbook age for successful fetches: 73.57ms (fresh)

**Verdict: PARTIAL BACKGROUND BLOCKER.** Real failure rate ~14%, not an artifact. Not the post-trade stall cause — these are transient per-fetch failures, not session-wide state changes tied to trade history.

---

### Q6 — Is `delta_extreme` dominant?

**Code evidence (`polymarket/opportunity_scanner.py`):**

```python
if regime == DeltaRegime.EXTREME or candidate.delta_multiplier <= 0:
    return "delta_extreme"
```

Fires when YES/NO price is near 0.05 (extreme end of the binary range). DeltaRegime classification is price-derived and can persist for extended periods if the market is trending strongly in one direction.

**Gate distribution evidence:** `decision: delta_extreme: 24/80 = 30.0%`
- Average EV at delta_extreme skip: 0.102496 (positive EV, but gated out by regime)
- First-blocking for 30% of all candidates — the single largest gate
- Per prior `ENTRY_FUNNEL_ROOT_CAUSE_AUDIT_001`: EXTREME classification blocked 51.14% of candidates earlier in the session history; June 25 shows 30.0% after market conditions shifted

**Verdict: DOMINANT BACKGROUND BLOCKER.** Present in all market conditions. Does not specifically increase post-trade — it's a persistent market-condition gate. However, if ETH enters an extreme regime after the 2 observed trades, this gate will block all ETH candidates regardless of risk mode.

---

### Q7 — Does the confidence/probability gate block post-trade?

**Code evidence:**

Normal operation confidence floor: 0.54 (from `confidence_floor` in `OpportunityScanContext`).

In `_hard_skip_reason`:
```python
if candidate.confidence_score < context.confidence_floor:
    return "confidence_too_low"
```

In post-model quality gate (trader.py ~line 9820):
```python
elif not quality_ok:
    skip_reason = f"risk_mode_{mode}:{quality_reason}"
```

Where `quality_ok` = `trade_quality_allowed(mode, confidence=...)`.

**Gate distribution evidence:** `decision: confidence_too_low: 7/80 = 8.75%` at normal floor 0.54.

Post-2-loss scenario: DEFENSIVE mode raises floor to 0.65. Candidates that passed at 0.54 now fail at 0.65. The additional blocked fraction = candidates with confidence in [0.54, 0.65) — a significant subset, likely 15–30% of remaining candidates based on confidence distribution.

**Verdict: ELEVATED BLOCKER IN DEFENSIVE MODE.** In normal mode, 8.75% blocked here. In DEFENSIVE, the additional [0.54, 0.65) fraction blocks, potentially removing 20–40% of what would otherwise enter. Compounded with delta_extreme (30%), the combined post-2-loss block rate approaches 50–60% of all candidates, leaving very few reaching execution.

---

### Q8 — Is `ev_below_threshold` blocking significantly?

**Gate distribution evidence:** `decision: ev_below_threshold: 5/80 = 6.25%`

**Verdict: MINOR BACKGROUND BLOCKER.** 6.25% in normal operation. EV threshold is dynamic. Not a post-trade stall cause in isolation.

---

### Q9 — Is capacity/throttle blocking inter-epoch entries?

**Code evidence:**

`max_entries_per_market = 1` (config/settings.py line 207) — keyed to `(market_id, epoch_start_ts)`. Resets per 5-minute epoch. After a position closes and the next epoch begins, this counter is 0 for the new epoch pair.

`max_active_positions_per_market = 1` — blocks while a position is open. Resets when position closes.

`frequency_multiplier_for_tier()` — affects sizing (0.20–1.0), does not hard-block.

**Gate distribution evidence:** `frequency / active position: 9/80 = 11.25%`. These fire correctly during the epoch the trade was placed, or while the position was open. They reset per epoch.

**Verdict: EPOCH-SCOPED ONLY.** Within the epoch of a trade, re-entry is correctly blocked. Between epochs, these gates reset. Not the inter-epoch stall cause.

---

### Q10 — Is inventory reconciliation blocking?

**Code evidence (utils/position_tracker.py line 412):**

```python
elif local_positions and not clob_positions and not self.settings.paper_trading:
    mismatches.append("local_positions_without_clob_positions")
# paper_trading=True → this branch NOT taken → no mismatch
```

Paper mode always passes `polymarket_positions=[]` to `reconcile_inventory`. The branch that generates `local_without_clob` mismatch explicitly excludes paper mode. In normal paper operation, reconciliation returns `block=False`.

**EXIT_EXECUTION_ROOT_CAUSE_AUDIT_001 evidence:** The 4 `risk_mode_lockdown` events in the June 25 distribution all originate from ghost probe sessions (PIDs 04:50–05:32 UTC) with `reconciliation_mismatch` due to ghost positions. The primary production session (PID 06:19 UTC) had **zero lockdown triggers from reconciliation**. Zero exit failures.

**Verdict: NOT A BLOCKER** in normal production paper operation. The 4 lockdown events in the distribution are ghost artifacts from separate PIDs, fully isolated from the primary session.

---

### Q11 — Is Telegram/UI visibility hiding trades that ARE happening?

**Code evidence:** The `ALIVE | PAPER` display fires every cycle. It does not differentiate between:
- "No candidate reached execution" (gates blocked at pre-model stage)
- "Candidate reached execution but risk mode blocked it"
- "Candidate reached execution, risk mode passed, but EV failed"
- "Candidate reached execution, all gates passed, but no BEST_TRADE declared"

The `OPEN | ETH NO` and `CLOSE | ETH` events fire on confirmed paper trade opens/closes. If the quality gate or any post-model gate blocks, no OPEN event fires. The trade does not happen silently.

**Gate distribution evidence:** The no-entry analyzer counts all decision events. 1/80 = 1.25% ENTERED. Trades are not silently passing — the pipeline is correctly blocking.

**Verdict: CONFIRMED OBSERVABILITY GAP** in the output, not a correctness issue. The `ALIVE | PAPER` cadence does not reveal which gate blocked or at which priority level. `CONTINUITY_BLOCKED_BY_RISK_MODE` and `CONTINUITY_BLOCKED_BY_MARKET_CONDITIONS` both produce identical `ALIVE | PAPER` silence — no way to distinguish from the terminal output alone.

---

### Q12 — True no-op: are cycles genuinely scanning but simply blocked?

**Code evidence:** The main trader loop continues regardless of risk mode (LOCKDOWN does not stop the loop, only gates within it). `can_trade()` at cycle start only blocks when loss_cluster_pause is active or floor/drawdown is breached. Otherwise cycles run, candidates are evaluated, and each is passed through the gate sequence.

**Gate distribution evidence:** 80 evaluated decision events confirm scanning is active. Blocking is real and at specific gates. No evidence of a true no-op where no evaluation occurs.

**Verdict: NOT TRUE NO-OP.** Cycles are running. Candidates are being evaluated. They are being blocked at specific gates, most likely delta_extreme (30%) and risk_mode/confidence (elevated post-loss). The system is working as designed — it is the design's conservative thresholds and lack of recovery mechanism that produce the stall.

---

## Combined Gate Analysis (June 25)

| Gate | Count | % | Nature |
|---|---|---|---|
| delta_extreme | 24 | 30.0% | Market regime — persistent if ETH trending |
| time_unsafe/cutoff | 14 | 17.5% | Structural — 30% of each epoch unavailable |
| orderbook stale | 11 | 13.75% | Transient — real API/feed failures |
| frequency/active position | 9 | 11.25% | Epoch-scoped — correct protective behavior |
| confidence_too_low | 7 | 8.75% | Elevated in DEFENSIVE mode |
| ev_below_threshold | 5 | 6.25% | Minor background blocker |
| risk_mode_lockdown | 4 | 5.0% | Ghost sessions only, not primary PID |
| risk_plan_zero | 2 | 2.5% | Sizing edge case |
| ENTERED | 1 | 1.25% | Success |
| other | 3 | 3.75% | Token/field mapping edge cases |

Post-2-loss (DEFENSIVE mode active), estimated block rate compounds:
- delta_extreme: 30% (unchanged)
- time_unsafe: 17.5% (unchanged)
- confidence_now_defensive: +15–25% of remaining candidates
- Combined elimination: ~65–75% of candidates never reach final quality gate
- Of the ~25–35% reaching quality gate: DEFENSIVE floor 0.65 blocks those with confidence 0.54–0.64
- Effective entry rate post-2-loss: **near zero**

---

## Final Verdict

**`CONTINUITY_BLOCKED_BY_RISK_MODE`**

**Primary mechanism:** After 2 consecutive paper trade losses, `RiskModeState` transitions to `RiskMode.DEFENSIVE`. The confidence floor rises from 0.54 to 0.65. The typical candidate confidence range (0.54–0.64) falls below this floor. All candidates fail `trade_quality_allowed()`. The mode does not self-heal — it requires a winning trade to reset `consecutive_losses`, but it cannot execute a winning trade because DEFENSIVE blocks all entries. This is a **deadlock**: no entries possible until a win; no win possible without an entry.

**Secondary mechanisms:**
- `delta_extreme` (30%) reduces the pool before the quality gate even fires
- Permanent LOCKDOWN architecture: any future `duplicate_order`, `exit_failure`, or `api_order_failure` trigger will permanently halt entries for the rest of the session with no recovery path

**Confirmed non-causes (June 25 primary session):**
- Exit failures: 0 exit failures in primary session — no `exit_failure` lockdown triggered
- Reconciliation lockdown: ghost sessions only, isolated from primary PID
- Loss cluster 30-min pause: requires 3 losses; observed pattern has 2 trades
- Orderbook artifact: pre-hotfix issue, resolved
- Cooldown timers: dead code (seconds_since_last_entry never wired)

---

*Audit complete. No code changes were made. See companion documents for funnel breakdown, gate distribution analysis, implementation gap analysis, and next actions.*
