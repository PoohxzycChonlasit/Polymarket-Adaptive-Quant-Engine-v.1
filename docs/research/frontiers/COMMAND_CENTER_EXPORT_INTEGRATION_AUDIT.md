# Command Center Export Integration Audit

**Generated:** 2026-06-07
**Status:** READ-ONLY analysis — no code changes, no commits, no runtime changes.

**Symptom:** `ETH_YES_FC_OS_COMMAND_CENTER.md` reports `UNKNOWN` for all regime sequence and regime
mix values, despite `canonical_regime_enriched_trades_v1.csv` showing 100% regime join rate and 0%
UNKNOWN.

---

## 1. Which Source Did the Command Center Actually Use?

**Answer: the trade journal JSONL, not any CSV.**

### Source-selection logic (lines 829–846, `eth_yes_fc_os_command_center.py`)

```python
# argparse defaults:
parser.add_argument("--trade-journal-dir", type=Path, default=DEFAULT_TRADE_JOURNAL_DIR)
# DEFAULT_TRADE_JOURNAL_DIR = Path("runtime/quant_data/trade_journal")

parser.add_argument("--csv-only", action="store_true")

# wiring into compute_metrics:
trade_journal_dir=None if args.csv_only else args.trade_journal_dir
```

```python
# compute_metrics (lines 533–538):
if trade_journal_dir is not None and trade_journal_dir.exists():
    raw_rows = _trade_journal_rows(trade_journal_dir)     # ← taken
    source_label = f"trade_journal:{trade_journal_dir.as_posix()}"
else:
    raw_rows = _read_csv_rows(csv_path)
    source_label = f"csv:{csv_path.as_posix()}"
```

**Consequence:** `--trade-journal-dir` defaults to `runtime/quant_data/trade_journal`, which exists.
Unless `--csv-only` is explicitly passed, the trade journal **always wins**. Both `completed_trades_v1_2.csv`
and `canonical_regime_enriched_trades_v1.csv` are bypassed entirely when the trade journal directory
is present.

The latest run confirmed this: the generated report header reads:
> `Source evidence: trade_journal:runtime/quant_data/trade_journal`

---

## 2. Was the Export CSV Loaded?

**No. Neither CSV was loaded.**

`canonical_regime_enriched_trades_v1.csv` was not loaded because:
- It was not passed via `--csv-path`
- The `--canonical-regime-export` flag used in the daily ops task does not exist on the script
- Even if passed as `--csv-path`, the trade journal would still take priority without `--csv-only`

`completed_trades_v1_2.csv` (the default `--csv-path`) was also not loaded for row data — only for
the staleness timestamp check (line 572–575), which is always performed against the CSV path regardless
of which source provides rows.

---

## 3. Which Field Does the Command Center Read for Regime?

**`row.get("regime")`** — a single field name, in two distinct contexts.

### Row-construction path (trade journal, lines 234–251)

When rows come from the trade journal, regime is populated during row construction:

```python
"regime": _event_text(close, "regime", "market_regime") or
          _event_text(open_event, "regime", "market_regime") or
          "UNKNOWN"
```

`_event_text` searches `payload` then the event root for each name. The trade journal
`trade_open` and `trade_close` events contain neither `regime` nor `market_regime` in their
payloads — confirmed by scanning all payload keys across the first 200 events of
`runtime/quant_data/trade_journal/2026-06-07.jsonl`:

```
# Payload keys present in trade journal events (relevant subset):
market_id, market_key, market_price, market_readiness_state, market_slug,
lifecycle_phase, hold_seconds, pnl_usdc, trade_result, outcome, asset, side
# ← "regime" and "market_regime" are ABSENT
```

Both lookups return `""`, so the fallback `"UNKNOWN"` is set for every trade-journal-sourced row.

### Metrics-computation path (lines 555–556)

```python
regime_counts = Counter(
    str(row.get("regime") or "UNKNOWN").strip().upper() or "UNKNOWN"
    for row in rows
)
last_5_regimes = [
    str(row.get("regime") or "UNKNOWN").strip().upper() or "UNKNOWN"
    for row in rows[-5:]
]
```

### nc_PF series path (line 372)

```python
non_compression = [
    row for row in window
    if str(row.get("regime") or "UNKNOWN").strip().upper() != "COMPRESSION"
]
```

All three paths read `row.get("regime")`. With all rows constructed from the trade journal carrying
`"regime": "UNKNOWN"`, all 62 rows satisfy `!= "COMPRESSION"` — so nc_PF is computed on **all 62
rows**, not only non-COMPRESSION rows.

---

## 4. Schema Mismatch Between the Two CSVs

Three data sources, three different representations of the same concept:

| Source | Field name | Values present | Compatible with command center? |
|---|---|---|---|
| `completed_trades_v1_2.csv` | **`regime`** | `COMPRESSION`, `TREND_DOWN`, `SIDEWAY`, `TREND_UP` | ✓ YES — exact field name match |
| `canonical_regime_enriched_trades_v1.csv` | **`market_regime`** | Same regime values, 100% populated | ✗ NO — wrong field name; `row.get("regime")` returns `None` |
| Trade journal JSONL | *(absent)* | — | ✗ NO — field does not exist in events |
| Decision log JSONL | `payload.market_regime` | Correct values | ✓ Partial — used for COMPRESSION-share panel only, not per-trade regime |

**The canonical regime export uses `market_regime` (not `regime`).** Even if it were passed as
`--csv-path --csv-only`, `row.get("regime")` returns `None` for every row → same UNKNOWN outcome.

**`completed_trades_v1_2.csv` uses `regime` — the correct name.** Qualifying rows
(ETH YES OPENING_SCAN hold>15s, n=60 after dedupe) have a fully populated `regime` column:

```
COMPRESSION : 21  (35.0%)
TREND_DOWN  : 18  (30.0%)
SIDEWAY     : 14  (23.3%)
TREND_UP    :  7  (11.7%)
```

No UNKNOWN values in the CSV's qualifying rows.

**`canonical_regime_enriched_trades_v1.csv` regime distribution (validated source, n=61 after dedupe):**

```
COMPRESSION : 21  (34.4%)
TREND_DOWN  : 18  (29.5%)
SIDEWAY     : 15  (24.6%)
TREND_UP    :  7  (11.5%)
```

The two sources agree on COMPRESSION, TREND_DOWN, and TREND_UP exactly. SIDEWAY differs by 1
row — the canonical export captures 1 additional qualifying SIDEWAY trade dated 2026-06-06T05:20:24
that is not in the stale CSV (CSV is >59h stale relative to the audit run).

**Row-level join between sources: 0 common keys.** Despite sharing the same `condition_id` and
`paper_trade_replay_key` values, the composite key
(`condition_id + epoch_start_ts + asset + side + candidate_id`) fails to match because:
- `epoch_start_ts` is formatted as an integer string in the export (`'1779078900'`) but as a float
  string in the CSV (`'1779078900.0'`)
- `candidate_id` is populated in the export (`'candidate_d65f3cb121e9'`) but empty in the CSV

These are the same underlying trades — confirmed by matching `condition_id`, `paper_trade_replay_key`,
and `entry_ts`. The join failure is a schema artifact from the two different generation paths.

---

## 5. Silent UNKNOWN Fallback — Confirmed and Quantified

### Mechanism

The fallback is structural and silent. No warning, no error, no log message is emitted when
`_event_text(close, "regime", "market_regime")` returns `""`. The `or "UNKNOWN"` default at line 250
absorbs the miss invisibly.

### nc_PF definitional violation

nc_PF (non-COMPRESSION Profit Factor) is defined as PF computed only on non-COMPRESSION qualifying
trades. With all regimes UNKNOWN, every row passes the `!= "COMPRESSION"` check — the COMPRESSION
exclusion is completely inoperative.

**Quantified impact (computed from `canonical_regime_enriched_trades_v1.csv` `market_regime` column —
the validated regime source — n=61, rolling window=20):**

| n | Canonical nc_PF (COMPRESSION excluded) | nc rows in window | UNKNOWN nc_PF (all rows) | All rows in window |
|---:|---:|---:|---:|---:|
| 50 | 0.731 | 13 | 1.497 | 20 |
| 51 | 0.943 | 13 | 1.775 | 20 |
| 52 | 1.085 | 14 | 2.099 | 20 |
| 53 | 1.213 | 15 | 1.795 | 20 |
| 54 | 1.360 | 16 | 1.838 | 20 |
| 55 | 1.700 | 16 | 2.217 | 20 |
| 56 | 1.700 | 16 | 1.967 | 20 |
| 57 | 1.700 | 16 | 1.797 | 20 |
| 58 | 1.864 | 15 | 2.079 | 20 |
| 59 | 2.518 | 14 | 2.405 | 20 |
| 60 | 2.518 | 14 | 2.424 | 20 |
| 61 | **2.707** | 14 | **2.552** | 20 |

_Previous session computed nc_PF = 2.662 from the CSV's `regime` column at n=60 (post-dedup).
The canonical export value (2.707) supersedes that figure — same underlying trades, validated join,
1 additional SIDEWAY qualifying trade. The difference (0.061) is within the single-trade noise band._

**Direction of distortion is not consistent.** When COMPRESSION trades in the window were high-PF,
the UNKNOWN fallback inflates nc_PF (n=52–55, distortion up to +1.01 at n=52). When COMPRESSION
trades were low-PF, it deflates nc_PF (n=56–57, n=59–60). The distortion can exceed ±0.5 PF units.

**Latest command center report nc_PF = 2.159** (n=62, trade journal source). This differs from
the canonical-validated value (2.707) because it includes 1 additional trade not yet in either CSV
and uses the UNKNOWN fallback throughout — the nc_PF exclusion logic is completely inoperative.

### Consecutive-below-1.0 counter

Both correct and UNKNOWN-fallback series show 0 consecutive below 1.0 at n=61. The tripwire status
(`CLEAR`) is correct in the latest report. However, the series history leading to this point is
unreliable — a COMPRESSION-heavy window could have briefly dipped below 1.0 in the correct series
while remaining above 1.0 under the UNKNOWN fallback (or vice versa).

---

## 6. Root Cause Summary

**Five separate failure modes, all simultaneously active:**

| # | Failure | Effect |
|---|---|---|
| RC-1 | Trade journal is the default and preferred source; CSV is only used when trade journal directory is absent OR `--csv-only` is passed | Row data comes from trade journal, which has no regime field |
| RC-2 | Trade journal `trade_open`/`trade_close` events do not emit `regime` or `market_regime` in their payload | Every row constructed from the trade journal gets `regime = "UNKNOWN"` |
| RC-3 | The UNKNOWN fallback in `_trade_journal_rows` (line 250) is silent — no warning emitted | The problem is invisible in normal output |
| RC-4 | `canonical_regime_enriched_trades_v1.csv` uses column name `market_regime`; the command center reads `row.get("regime")` | Even if the export CSV were passed as `--csv-path --csv-only`, regime would still be UNKNOWN |
| RC-5 | The `--canonical-regime-export` flag does not exist on `eth_yes_fc_os_command_center.py` | The intended integration is not wired; passing it causes an error |

---

## 7. Correct Command to Get Regime-Aware Output (Current Capability)

The only data source that has both (a) regime data and (b) the field named `regime` is
`completed_trades_v1_2.csv`. The correct command to activate it is:

```bash
py -3.11 tools/eth_yes_fc_os_command_center.py \
  --csv-path runtime/research_exports/completed_trades_v1_2.csv \
  --csv-only \
  --decision-log-dir runtime/quant_data/decision_log \
  --jsonl-integrity-status NOMINAL
```

**Caveats with this approach:**
- Produces n=60 after dedup (CSV is currently 59+ hours stale; 1 qualifying trade from 2026-06-06
  is absent — captured in the canonical export but not in the CSV)
- The `regime` column in `completed_trades_v1_2.csv` agrees with the canonical export on 3 of 4
  regime classes (COMPRESSION:21 ✓, TREND_DOWN:18 ✓, TREND_UP:7 ✓) but SIDEWAY differs by 1 row
  (CSV=14, export=15); nc_PF at n=60 from CSV is 2.646 vs 2.707 from the validated export — within
  the single-trade noise band but not identical
- BTC rows for K3 are also read from this CSV — regime data applies for ETH only; BTC K3 metric
  is unaffected by regime

**What the canonical regime export provides that the CSV does not:**
- `trend_regime`, `volatility_regime`, `regime_reason`, `regime_source`, `regime_join_confidence`,
  `regime_decision_ts` — richer join metadata
- But the field name `market_regime` prevents the current command center from reading it

---

## 8. Integration Gap Classification

| Gap | Category | Impact |
|---|---|---|
| `market_regime` vs `regime` column name mismatch | Schema gap — canonical regime export | Command center cannot use export CSV for regime metrics |
| Trade journal events missing regime field | Data gap — trade journal events | All trade-journal-sourced runs produce UNKNOWN regime |
| No `--canonical-regime-export` flag | Interface gap — command center CLI | Cannot pass the export CSV as intended by the ops task |
| Silent UNKNOWN fallback with no warning | Observability gap — command center | Regime failure is invisible; no error or warning in output |
| nc_PF distortion direction is non-deterministic | Measurement gap | nc_PF can be inflated or deflated depending on window composition |

---

## 9. What Correct Regime Data Shows

For reference, using the canonical regime export (`market_regime`, validated source, n=61) as the
authoritative standard:

| Metric | UNKNOWN (current, n=62 TJ) | Canonical (market_regime, n=61) |
|---|---|---|
| Regime sequence (last 5) | UNKNOWN×5 | Requires fresh run with `--csv-only` |
| Regime mix | UNKNOWN:62 | COMPRESSION:21, TREND_DOWN:18, SIDEWAY:15, TREND_UP:7 |
| nc_PF at n=61 | 2.552 (all rows, canonical n) | **2.707** (14 non-COMPRESSION rows) |
| nc_PF at n=53 | 1.795 (inflated by +0.582 vs correct) | **1.213** (correct) |
| nc_PF at n=52 | 2.099 (inflated by +1.014 vs correct) | **1.085** (correct) |
| nc_PF from CSV --csv-only (n=60) | — | **2.646** (close; 1-row SIDEWAY delta) |
| Consecutive below 1.0 | 0 | 0 |
| Tripwire | CLEAR | CLEAR |

The tripwire verdict is unchanged under all three calculations (UNKNOWN / canonical / CSV).
The nc_PF magnitude is distorted but not catastrophically at current n; however, distortion
reached +1.01 at n=52 when COMPRESSION-heavy windows had high-PF outcomes included.

---

## 10. Governor Read

The UNKNOWN regime bug does not invalidate WR, PF, p-value, velocity, or kill-criterion status —
those metrics do not depend on the `regime` field. The affected metrics are:

- **nc_PF:** definitionally violated; computed on all rows, not non-COMPRESSION only
- **Regime sequence (last 5):** meaningless (UNKNOWN×5)
- **Regime mix:** meaningless (UNKNOWN:62)

The campaign's P-gate verdicts and K-criterion statuses are unaffected by this bug.

To fix regime metrics without code changes: run with `--csv-path completed_trades_v1_2.csv --csv-only`
and ensure the CSV is refreshed first by regenerating `completed_trades_v1_2.csv` (not the
canonical regime export, which targets a different file).

---

*This report is offline research evidence only. It must not be wired into runtime decisions.*
