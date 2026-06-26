# POSITION_SIZING_HOTFIX_EVIDENCE_SUMMARY_001
> Task: POSITION_SIZING_HOTFIX_RUNTIME_VALIDATION_001  
> Date: 2026-06-25  
> Scope: Evidence summary across all three validation layers  
> Overall Verdict: **HOTFIX_PARTIAL** (code correct, runtime sizing layer not yet exercised)

---

## Layer 1 — Unit Tests

| Suite | File | Pass | Fail | Notes |
|-------|------|------|------|-------|
| Execution Risk Controls | `tests/test_execution_risk_controls.py` | **44** | 0 | Covers floor enforcement, EV guard, stop-loss, side guard |

**Test output**:
```
44 passed, 5 warnings, 3 subtests passed in 17.55s
```

Tests covering the hotfix directly:
- `test_micro_survival_floor_enforced` — verifies `min(max(risk_cap, floor), balance)` path
- `test_micro_survival_zero_size_rejected` — verifies zero-size probe fires when floor can't be met
- `test_side_win_rate_present_in_probe_event` — verifies `side_win_rate` field present in JSONL

---

## Layer 2 — Direct Code Verification

### `utils/risk_manager.py` — `build_micro_survival_risk_plan`

**Bug**: `min(risk_cap, min_pos, balance)` — floor acted as upper bound  
**Fix**: `min(max(risk_cap, min_pos), balance)` — floor acts as lower bound

**Proof test**:

```python
account_balance = 20.0
risk_fraction   = 0.0025      # micro_survival_risk_fraction
min_pos         = 0.10        # micro_survival_min_position_size

risk_cap = 20.0 * 0.0025 = 0.05          # below floor

# BEFORE FIX:
result = min(0.05, 0.10, 20.0) = 0.05    # ❌ floor broken
# AFTER FIX:
result = min(max(0.05, 0.10), 20.0) = 0.10  # ✅ floor enforced
```

**Python runtime result**:
```
MEF floor:              0.1
risk_cap_usd:           0.05
micro_position_size:    0.1      FLOOR_ENFORCED: True
OLD result (broken):    0.05     FLOOR_BROKEN: True
```

### `polymarket/trader.py` — `_micro_position_size` (line 629)

Identical fix applied. Confirmed via code inspection.

### `polymarket/trader.py` — `side_win_rate` telemetry

| Location | Line | Content |
|----------|------|---------|
| Computation | 9850 | `_side_win_rate = probability.p_yes if model_side == "YES" else probability.p_no` |
| Call site | 9858 | `side_win_rate=_side_win_rate,` |
| Signature | 12578 | `side_win_rate: float = 0.0,` |
| JSONL write | 12636 | `"side_win_rate": round(float(side_win_rate or 0.0), 6),` |

### `config/settings.py` — Floor Value

```python
micro_survival_min_position_size: float = 0.10  # Polymarket CLOB hard minimum is $0.10
```

---

## Layer 3 — Runtime Paper Session

**Session ID**: `20260625T052627Z_48728_55bb248a`  
**Duration**: ~2m40s | **Cycles**: 3 | **Mode**: PAPER ONLY

### Startup Evidence

```
[PAPER MODE] Forced paper trading enabled. No real orders will be placed.
[USDC BALANCE] balance=$20.0990 source=clob_collateral execution=PAPER_ONLY no_live_orders=true
[BANKROLL_RANK_LOCK] active=T0_MICRO_SEED raw=T0_MICRO_SEED family=MICRO profile=seed_protection
```

### Per-Cycle Risk Panel (Cycle 2 and 3)

```
Tier T0_MICRO_SEED | Family MICRO
Bankroll MICRO_SURVIVAL | Raw T0_MICRO_SEED
Exposure 0.0% | DD 0.0%
Mode NORMAL | RiskOff False
```

### Decision Layer

| Cycle | BTC Decision | ETH Decision | DATA State |
|-------|-------------|--------------|------------|
| 1 | UNKN REJE | — | DATA DEGRADED (warmup) |
| 2 | UNKN REJE | No entry | DATA OK |
| 3 | UNKN REJE | No entry | DATA OK |

**Root cause for no entries**: Candidates blocked before reaching sizing layer:
- `time_unsafe` (8 events) — epoch near cutoff
- `stale_data` / `orderbook_unavailable` (10 events) — CLOB refresh failures
- `delta_extreme` (5 events) — signal delta too extreme
- `frequency_cooldown` (4 events) — rate limit

### Sizing Layer Exercise

| Metric | Value |
|--------|-------|
| Candidates reaching sizing gate | 0 |
| `zero_size` rejections | 0 |
| `zero_size_probe` JSONL events | 0 |
| `risk_plan_zero` events | 0 |
| Paper orders created | 0 |
| Paper fills | 0 |

> **Interpretation**: The hotfix code path (floor rescue) was **not exercised at runtime** because no candidates reached the sizing layer in the 3-cycle session. The code is provably correct (Layer 2), but runtime sizing evidence is pending a longer or better-timed session.

---

## Pre-Hotfix Runtime Artifact (Baseline Comparison)

From risk_log `2026-06-25.jsonl`, run `32fea5ff` (June 23 session, writing until 02:39 UTC):

```
bankroll_mode:        MICRO_SURVIVAL
micro_survival_active: True
micro_position_size:  0.050345   ← PRE-HOTFIX, floor broken
cash:                 20.138
risk_mode:            MICRO_RECOVERY
```

**This is the exact bug**: `risk_cap = 20.14 × 0.0025 = 0.050` was passed directly as size, bypassing the $0.10 floor.

After hotfix, the same scenario would produce `micro_position_size = 0.10`.

---

## Verify Mode Evidence

```
auth=OK  latency=79ms  endpoint=OK  api_key=OK  api_secret=OK
cash=20.0990  equity=20.0990  sizing_bankroll=20.0990  status=MATCH
positions=0  reconciliation=SAFE  classification=FLAT
BTC  orderbook=OK  bid=0.4200  ask=0.4300  spread=0.0100
ETH  orderbook=OK  bid=0.2900  ask=0.3000  spread=0.0100
BTC  p_yes=0.4850  decision=SKIP  reason=confidence_too_low
ETH  p_yes=0.4368  decision=SKIP  reason=confidence_too_low
[VERIFY FAILED]  missing_allowance  ← live-only blocker, paper unaffected
```

---

## Offline Analyzer Evidence

| Analyzer | Key Metric | Value | Verdict |
|----------|-----------|-------|---------|
| `quant_data_quality.py` | `bad_json` | 0 | ✅ Clean JSONL |
| `quant_data_quality.py` | `invalid_numeric` | 30 | ⚠️ Pre-existing |
| `no_entry_analyzer.py` | `zero_size` | **0** | ✅ No floor-caused rejections |
| `no_entry_analyzer.py` | `confidence_too_low` | 0 | ✅ |
| `session_runtime_evaluator.py` | `risk_plan_zero` | **0** | ✅ No zero-plan events |
| `session_runtime_evaluator.py` | `SESSION_STATUS` | FAIL | ⚠️ Pre-existing latency/cutoff |

---

## Evidence Matrix

| Evidence Type | Source | Supports Hotfix? |
|--------------|--------|-----------------|
| Math fix correct | Direct Python test | ✅ Yes |
| Floor enforced (`risk_cap=0.05 → 0.10`) | Direct test | ✅ Yes |
| High-signal not penalized (`risk_cap=0.40 → 0.40`) | Direct test | ✅ Yes |
| 44/44 tests pass | pytest suite | ✅ Yes |
| `side_win_rate` wired | Code inspection | ✅ Yes |
| Paper safety preserved | Startup banner + JSONL | ✅ Yes |
| MICRO_SURVIVAL mode active | Risk log + Terminal panel | ✅ Yes |
| Pre-hotfix bug confirmed | `risk_log` run `32fea5ff` | ✅ (baseline confirmed bug) |
| Runtime floor rescue fired | JSONL evidence | ⚠️ Not yet — gate blocked |
| `zero_size_probe` event with `side_win_rate` | JSONL evidence | ⚠️ Not yet — no probe fired |

---

*Evidence summary for POSITION_SIZING_HOTFIX_RUNTIME_VALIDATION_001*
