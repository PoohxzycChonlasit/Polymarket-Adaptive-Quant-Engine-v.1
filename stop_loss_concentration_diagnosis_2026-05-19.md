# Stop-Loss Concentration Diagnosis - 2026-05-19

Scope: read-only diagnosis of latest overnight paper positions.

Run checked: `20260518T133028Z_1724_5d277d50`

Evidence source: `runtime/quant_data/*/2026-05-18.jsonl`

Runtime behavior changed: No

Live behavior changed: No

## Root Cause

The stop-loss concentration is primarily an early mark-to-market stop problem, not a replay-pairing problem and not an epoch-boundary forced-close problem.

All 4 positions had healthy open-close continuity, but each was stopped within 3 to 12 seconds of entry. The exits happened with 228 to 290 seconds still remaining in the 5-minute market, so they were not final-derisk or epoch-boundary closes.

The strongest causal pattern is:

1. Entries were taken very early in the market window.
2. The stored position stop-loss threshold was tight for a volatile binary token path.
3. Three of four positions were ETH and had `THIN` entry depth.
4. Exit price came from the held token mark/exit path, while close events serialized `market_readiness_state=unavailable` and `lifecycle_phase=UNKNOWN`.
5. Nearby market snapshots still showed ready orderbooks, so the close telemetry is partially blind even though the paper close event itself is real.

This means the losses are structurally suspicious as a runtime/replay maturity signal: the paper engine is generating real paired stop-loss events, but the close context is not rich enough to prove whether every stop was a true executable market loss versus thin-book/mark-price/serialization artifact.

## Position Evidence

| Position | Asset | Side | Confidence | True probability for side | EV after spread | Entry | Exit | Hold | Close timing | Entry depth | Spread | Reason |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| `8dc24043` | ETH | YES | 0.5492 | 0.6516 | 0.1216 | 0.53 | 0.45 | 4s | 282s remaining | THIN | 0.01 | stop_loss |
| `c87ea3d7` | ETH | YES | 0.5459 | 0.6485 | 0.1385 | 0.51 | 0.40 | 4s | 272s remaining | THIN | 0.02 | stop_loss |
| `848a2379` | ETH | NO | 0.7059 | 0.6328 | 0.1828 | 0.45 | 0.40 | 3s | 290s remaining | THIN | 0.01 | stop_loss |
| `1694939f` | BTC | YES | 0.7588 | 0.6706 | 0.0906 | 0.58 | 0.56 | 12s | 228s remaining | ACCEPTABLE | 0.01 | stop_loss_hit |

Asset split: ETH 3, BTC 1.

Side split: YES 3, NO 1.

Close timing: all closes occurred early, between 10 and 72 seconds after epoch open.

MICRO/DEFENSIVE state:

- Entry execution events that carried risk state showed `risk_mode=MICRO_RECOVERY`.
- Session-level risk evidence also showed MICRO_SURVIVAL activity and DEFENSIVE activity, but these 4 entry/exit records were not DEFENSIVE exits.
- The positions were micro-sized, roughly `$0.0316` to `$0.0537` notional.

## Stop Trigger Mechanics

The runtime has two relevant stop concepts:

- `PolymarketOrderManager` is initialized with `settings.default_stop_loss_pct`, which is `0.04`, and builds `stop_loss_price = entry_price * (1 - stop_loss_pct)`.
- `check_stop_loss()` also has an `execution_stop_loss_pct` setting of `0.08`, but the `stop_loss_hit` path in open-position management compares current held-token mark price against the stored `pos.stop_loss`.

The observed exits are consistent with a tight stored stop threshold being hit by early token-price movement. Three ETH exits were far beyond a 4% or 8% adverse move. The BTC exit was small in rounded terms, but close price `0.56` from entry `0.58` is near the 4% stored stop area once unrounded bid movement is considered.

## Close Context Quality

Close event payloads reported:

| Field | Close Event Pattern |
|---|---|
| `market_readiness_state` | `unavailable` |
| `orderbook_state_classification` | `unavailable` |
| `lifecycle_phase` | `UNKNOWN` |
| `pre_model_gate_group` | `ORDERBOOK_GATE` |

Nearby decision/snapshot evidence did not agree with that unavailable state. For the same markets around close, decisions and snapshots showed ready orderbooks:

| Position | Nearby snapshot at/near close | Close fill |
|---|---|---:|
| ETH YES `8dc24043` | YES bid/ask around 0.52/0.53 | 0.45 |
| ETH YES `c87ea3d7` | YES bid/ask around 0.49/0.51 | 0.40 |
| ETH NO `848a2379` | NO bid/ask around 0.44/0.45 | 0.40 |
| BTC YES `1694939f` | YES bid/ask around 0.57/0.58 | 0.56 |

Interpretation: the BTC close is plausible as normal adverse movement. The ETH closes, especially the two YES exits, need caution because close fills are materially worse than the nearest passive snapshots. That points to either fast book movement between snapshots, held-token mark-price differences, or close-event serialization not carrying the exact executable orderbook state.

## A-G Determination

### A. True Market Losses?

Partially yes, but not fully proven for all four.

The paper ledger records real paper exits below entry and negative PnL. The BTC loss is plausible from nearby snapshots. The ETH losses are less clean because nearby snapshots remained much closer to entry than the recorded exit prices.

Conclusion: paper losses are real in the journal; market-truth strength is mixed.

### B. Epoch-Boundary Forced Closes?

No.

All closes occurred with 228 to 290 seconds remaining. This was early-window stop behavior, not final derisk, emergency flatten, settlement, or epoch rollover.

### C. Liquidity Exit Artifact?

Probable contributor for ETH.

Three ETH entries had `liquidity_depth_state=THIN`. The close events did not serialize ready orderbook context, and ETH close prices were worse than nearby snapshots. That is enough to classify liquidity/mark-price artifact risk as material.

### D. Stop-Loss Too Close?

Likely yes.

The stored position stop path appears tighter than the 5-minute binary token noise profile, especially in MICRO-sized entries. Holding periods of 3, 4, 4, and 12 seconds are too short to demonstrate stabilized inventory behavior.

### E. Thin-Book Effect?

Yes for ETH, weaker for BTC.

ETH was 3/4 of the sample and all ETH entries were `THIN`. BTC had `ACCEPTABLE` depth and the smallest loss.

### F. NO-Side Bias?

No evidence.

Only 1 of 4 positions was NO. The stop-loss cluster hit 3 YES positions and 1 NO position. This is not a NO-side concentration.

### G. Replay Artifact?

Not a pairing artifact. Possibly a close-context artifact.

Open-close matching, replay keys, inventory context, candidate ids, and lifecycle ids were healthy. The artifact risk is narrower: close events serialize `unavailable`/`UNKNOWN` market context and do not prove exact executable book state at the stop trigger.

## Structural Or Expected?

Classification: structurally suspicious, but expected under the current tiny-sample and tight-stop regime.

This is not random enough yet to call normal outcome variance. A 4-position sample is too small, but 4/4 stop-loss exits within seconds suggests a structural interaction:

- early-window entries,
- tight stop thresholds,
- thin ETH books,
- micro-sized paper entries,
- and incomplete close-context observability.

The losses are expected if the system sells as soon as held-token best bid dips through a tight stop. They are not yet acceptable evidence of healthy S3 outcome diversity.

## Is Outcome Diversity Beginning?

No.

Outcome diversity has not started yet. Evidence diversity improved because the runtime produced paired opens and closes, but outcome diversity is still absent:

- take_profit count: 0
- survived count: 0
- unresolved count: 0
- stop_loss count: 4
- hold time range: 3 to 12 seconds

The system has moved from no-entry/no-pairing immaturity into paired-loss immaturity.

## S3 Implication

S3 implication: CAUTION, not promotion.

Positive for S3:

- Healthy replay continuity.
- Real paper positions exist.
- Open-close pairing is complete.
- Entry-side, asset, probability, EV, and risk context are visible in execution events.

Blocking for S3:

- 100% stop-loss concentration.
- No take-profit or stabilized-position examples.
- Close events lack trustworthy market availability/lifecycle context.
- ETH stop-loss prices may reflect thin-book or mark-price artifacts.
- Direct MFE/MAE truth is still missing, so the path between entry and stop is under-explained.

S3 should require at least some non-stop-loss closes and direct MFE/MAE or equivalent path evidence before treating this as mature inventory replay data.

## Exactly Three Future Options

### OPTION 1 - SAFE EV PRESERVATION

Thesis: keep runtime unchanged and collect more paper evidence under the current guards.

Quant logic: this tests whether 4/4 stop losses are a small-sample cluster or persistent stop-threshold behavior. Risk remains bounded and no live behavior changes.

Likely outcome: another session will quickly show whether stops continue firing within seconds.

Hidden risk: repeated stop-outs can look like useful replay data while actually proving the entry/exit loop has poor holding power.

Recommended action: run another paper session and compare stop-loss share, hold seconds, and ETH thin-book concentration.

### OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY

Thesis: run offline-only stop-path replay around these four positions.

Quant logic: reconstruct held-token best bid/ask path from snapshots and execution events, then compare stop trigger price to nearest passive market snapshots. This targets the artifact-vs-market-loss question without changing runtime.

Likely outcome: ETH exits will either validate as real fast book drops or expose a mark-price/serialization gap.

Hidden risk: without direct MFE/MAE fields, replay may still depend on proxy snapshot cadence.

Recommended action: produce a run-scoped stop-path table with entry bid/ask, close bid/ask, minimum held-token bid, and snapshot freshness.

### OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

Thesis: treat stop-loss concentration as a lifecycle design bottleneck, not an isolated exit event.

Quant logic: a future inventory system cannot reload/unload intelligently if starter entries are stopped before stabilization. The key variables are first model output, entry timing, depth class, stored stop price, mark-price source, and hold duration.

Likely outcome: the next bottleneck will be stop calibration and close-context observability rather than replay identity.

Hidden risk: promoting S3 on identity continuity alone would overstate maturity and understate adverse-selection risk.

Recommended action: make the next S3 gate require direct MFE/MAE coverage and at least one non-stop-loss close class before any inventory replay promotion.

## Final Answer

Root cause: early mark-to-market stop triggering under tight stored stop thresholds, amplified by thin ETH books and incomplete close-context serialization.

Losses structural or expected: expected under the current stop mechanics, but structurally suspicious as a maturity signal.

Outcome diversity beginning: No. Position lifecycle diversity improved; outcome diversity did not.

S3 implication: improved continuity, but S3 remains CAUTION and not ready for promotion.

Runtime behavior changed: No

Live behavior changed: No
