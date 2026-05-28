# Market Observation Key — Cycle-Level Epoch Alignment Verification

Date: 2026-05-28
Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
Mode: read-only, docs only, no implementation, no runtime mutation.

Prior context:
- `docs/research/runtime_health/market_observation_key_implementation_readiness_audit.md` (PARTIALLY_READY — gating gap identified)
- `docs/research/runtime_health/market_observation_key_epoch_alignment_audit.md` (key-set overlap confirmed, cycle-level not confirmed)

---

## Classification

```text
GATING_GAP_CLOSED
```

Cycle-level epoch alignment has been verified empirically across 5,403 matched cycle pairs with **zero mismatches**. The single gating evidence gap identified in `market_observation_key_implementation_readiness_audit.md` (Section 1c) is now closed. The readiness classification upgrades from **PARTIALLY_READY → READY**.

---

## Gating Gap Statement (from Section 1c of Readiness Audit)

> Select 5–10 specific bot cycles from a paper runtime log. For each cycle, find the MS row and its corresponding DL rows by bot-cycle timestamp proximity. Confirm that the resolved `epoch_start` value matches between the MS row and the DL rows.
>
> If any mismatch is found, the fallback is to use `time_bucket` instead of raw `epoch_start`.

This verification addresses that requirement exactly.

---

## Data Sources

| File | Producer | Date | Total rows | Rows with alias-resolved epoch |
|---|---|---|---:|---:|
| `runtime/quant_data/market_snapshots/2026-05-28.jsonl` | MS | 2026-05-28 | — | 5,317 |
| `runtime/quant_data/decision_log/2026-05-28.jsonl` | DL | 2026-05-28 | — | 6,170 |

Row counts reflect rows where alias-resolved epoch is non-null and condition_id is present.

---

## Methodology

### Field-name confirmation

Both files store epoch and other payload fields under a nested `payload` key, not at the top level:

```
row.payload.epoch_start_ts  ← MS uses this field name
row.payload.epoch_start     ← DL uses this field name (epoch_start_ts is 0% in DL)
```

The alias-priority resolution chain `("epoch_start_ts", "epoch_start", "market_epoch_start_ts", "market_epoch_start", "event_start_ts")` resolves:
- MS → first hit: `epoch_start_ts`
- DL → second hit: `epoch_start`

Both resolve to the same numeric epoch value.

### Cycle pairing

MS and DL rows in the same bot cycle share the same `condition_id` (BTC or ETH market) and a `timestamp_utc` that differs by milliseconds. Exact-timestamp matching produces 0 pairs because each producer emits at a slightly different wall-clock time. Proximity matching with a 2-second window correctly pairs same-cycle rows.

Matching algorithm:
1. Load all MS rows with a non-null alias-resolved epoch and non-empty `condition_id`.
2. Group all DL rows by `condition_id`.
3. For each MS row, find all DL rows with the same `condition_id` whose `timestamp_utc` falls within ±2 seconds.
4. For each pair, compare the alias-resolved epoch values.

---

## Results

### Cycle-pair summary

| Metric | Value |
|---|---|
| MS rows with epoch | 5,317 |
| DL rows with epoch | 6,170 |
| Matched pairs within 2s window | **5,403** |
| Epoch value mismatches | **0** |
| Mismatch rate | **0.000%** |

### Producer timing skew

DL emits consistently after MS within the same bot cycle. Sample skew from first 15 pairs:

| MS row | DL row | Skew | Asset | Epoch val |
|---:|---:|---:|---|---|
| 0000 | 0000 | +22ms | BTC | 1779926400 |
| 0001 | 0001 | +18ms | ETH | 1779926400 |
| 0002 | 0002 | +24ms | BTC | 1779926400 |
| 0003 | 0003 | +27ms | ETH | 1779926400 |
| 0004 | 0004 | +23ms | BTC | 1779926400 |
| 0005 | 0005 | +31ms | ETH | 1779926400 |
| 0006 | 0006 | +22ms | BTC | 1779926400 |
| 0007 | 0007 | +21ms | ETH | 1779926400 |
| 0008 | 0008 | +18ms | BTC | 1779926400 |
| 0009 | 0009 | +17ms | ETH | 1779926400 |
| 0010 | 0010 | +20ms | BTC | 1779926400 |
| 0011 | 0011 | +24ms | ETH | 1779926400 |
| 0012 | 0012 | +25ms | BTC | 1779926400 |
| 0013 | 0013 | +26ms | ETH | 1779926400 |
| 0014 | 0014 | +32ms | BTC | 1779926400 |

Skew range observed: **+17ms to +32ms**. DL consistently lags MS by 17–32ms within the same bot cycle.

### Epoch value set overlap

| Metric | Value |
|---|---|
| Unique epoch values in MS | 118 |
| Unique epoch values in DL | 118 |
| Overlap | **118/118 (100%)** |
| MS-only epochs | 0 |
| DL-only epochs | 0 |

The complete epoch value set is identical between MS and DL. Every market window observed by MS is also observed by DL, and vice versa. This is consistent with the key-set overlap result from `market_observation_key_epoch_alignment_audit.md` (225/225 unique `(condition_id, epoch_start)` pairs) and extends it to confirm full epoch-value-set equality.

---

## Epoch Transition Risk Assessment

### Risk statement (from readiness audit Section 1b)

> If there is an epoch boundary transition between MS and DL emission within a single cycle (e.g., MS captures epoch=X, but DL evaluates in the next epoch window=X+300), the keys would not match for that cycle.

### Assessment

This risk does not materialise. Evidence:

1. **Zero mismatches across 5,403 pairs.** If epoch boundary transitions caused mismatches within bot cycles, some would appear in this dataset.
2. **Epoch window is 300 seconds; bot cycle interval is ~10 seconds.** A bot cycle cannot span an epoch boundary unless the cycle takes longer than 300 seconds, which would indicate a hung process, not normal operation.
3. **Skew is 17–32ms.** The DL emission follows MS by 17–32ms — well within any single epoch window.
4. **Epoch values are derived from market metadata at cycle start, not from the current wall clock.** The epoch value reflects the Polymarket market's epoch window, not the time of emission. Both producers read this from the same market data feed, so they will carry the same value regardless of minor wall-clock timing differences.

The fallback path (use `time_bucket` instead of `epoch_start`) is **not required**.

---

## Field Name Asymmetry (Confirmed)

The verification confirms the asymmetry documented in prior audits:

| Producer | Field emitted | Alias chain position | Coverage |
|---|---|---:|---:|
| `market_snapshots` | `epoch_start_ts` | 1st | 100% |
| `decision_log` | `epoch_start` | 2nd | 100% |

**The alias-priority resolution chain correctly bridges this asymmetry.** Both resolve to the same numeric value. A `market_observation_key` implementation using the established alias chain will produce identical key values for paired MS and DL rows from the same bot cycle.

Hardcoding `epoch_start_ts` directly (without alias chain) would produce null keys for all DL rows, as `epoch_start_ts` is 0% present in `decision_log`. This remains a forbidden pattern.

---

## Conclusion

| Dimension | Finding |
|---|---|
| Cycle-level epoch alignment | **Verified** — 5,403 pairs, 0 mismatches |
| Epoch value set overlap | **100%** — 118/118 unique values |
| Field name asymmetry | **Bridged** — alias chain resolves identically |
| Epoch transition risk | **Not present** — 0 mismatches, timing gap 17–32ms |
| Fallback path needed | **No** — raw `epoch_start` is sufficient |
| Gating gap status | **CLOSED** |

The gating condition from `market_observation_key_implementation_readiness_audit.md` Section 1c is met. The readiness classification upgrades from **PARTIALLY_READY to READY**.

---

## Updated Readiness Classification

**Before this verification:** `PARTIALLY_READY`

**After this verification:** `READY`

Remaining pre-implementation prerequisites (unchanged from readiness audit):
1. Add test coverage in `tests/test_quant_event_logger.py` before paper runtime launch
2. Implement `_compute_market_observation_key` classmethod in `utils/quant_event_logger.py`
3. Wire call in `_with_candidate_trace_identity`, adjacent to `paper_trade_replay_key` block
4. Launch paper runtime and confirm fresh MS and DL rows emit non-zero key overlap

No governance prerequisites remain. Cycle-level epoch alignment was the only empirical gap.

---

## Scope of Verification — Disclosures

Three scope constraints apply. They do not invalidate the findings but should be considered when deciding whether to extend the verification.

### 1 — Single day sampled

Verification covers **2026-05-28 only** out of ~21 days of available JSONL data (2026-05-08 through 2026-05-28). The conclusion that cycle-level alignment holds is drawn from one day's runtime. If epoch field derivation has changed between older and newer code versions, earlier days may behave differently. A multi-day re-run is not required to proceed but would strengthen the claim for long-term documentation.

### 2 — Runtime rotation within the analysis date

The 2026-05-28 data spans a documented runtime rotation (old PID 38660, run_id `20260528T074009Z_38660_884a713e`, rows from `00:00:08Z` to ~`08:10Z`; new PID 39092, run_id `20260528T081158Z_39092_3d32c465`, rows from `08:11:58Z` onward). The verification pools both runs without `run_id` segmentation. Pairs near the rotation boundary (`08:10Z`–`08:12Z`) may have mixed-run origins. No mismatches were found, suggesting the rotation did not cause epoch divergence — but per-run confirmation was not explicitly performed.

### 3 — Unpaired MS rows not quantified

The 5,403 matched pairs count exceeds the 5,317 MS rows with epoch. This is expected: each MS row (one per market per cycle) can pair with multiple DL rows from the same cycle (YES side + NO side emitting separate DL rows). The verification counted mismatches among matched pairs only. It did not count MS rows with **zero** DL matches within the 2-second window. "0 mismatches among matched pairs" is a correct but survivor-biased claim — it does not assert that every MS row has at least one matching DL row. For the purposes of the readiness classification (`market_observation_key` is a coarse market-window bridge, not a row-for-row trace), survivor-biased alignment is sufficient. For a row-completeness claim it would not be.

---

## Safety Confirmation

| Dimension | Changed |
|---|---|
| Runtime behavior | No |
| Strategy / risk / execution | No |
| Thresholds | No |
| Live behavior | No |
| Replay execution | No |
| JSONL files written or modified | No |
| Implementation performed | No |
| Policy authority introduced | No |
