# Single Run Path Truth Audit

Date: 2026-05-25 21:15 Asia/Bangkok

Scope: read-only audit of a single clean run after stale process cleanup.

Target run only: `20260525T065423Z_53560_1b672958`

## Sources

- `runtime/quant_data/path_truth/2026-05-25.jsonl`
- `runtime/quant_data/trade_journal/2026-05-25.jsonl`
- `logs/polytrade_bot_20260525_135420_53560.log`
- `docs/research/path_truth/path_truth_multiday_coverage_monitor.md`

The 2026-05-25 path-truth file contains multiple run IDs. This audit ignores all non-target run IDs.

## Path Truth Summary

| Metric | Value |
|---|---:|
| Path truth lines | 6 |
| Trades represented | 5 |
| Parse errors | 0 |
| Duplicate checkpoint keys | 0 |
| Full coverage trades | 0 |
| Fast-close partial trades | 5 |
| Scheduled 15s checkpoints | 1 |
| Scheduled 30s checkpoints | 0 |
| Scheduled 45s checkpoints | 0 |
| Scheduled 60s checkpoints | 0 |
| `event_end` checkpoints | 5 |

Coverage classification:

- `FAST_CLOSE_BEFORE_FIRST_CHECKPOINT`: 4 trades
- `FAST_CLOSE_BEFORE_SECOND_CHECKPOINT`: 1 trade
- `FULL_COVERAGE`: 0 trades

Path truth writer health is clean for this run: no parse errors, no duplicate keys, and every trade has an `event_end` path truth event. The missing full coverage is explained by fast closes, not by writer failure.

## Outcome Summary

| Metric | Value |
|---|---:|
| Trades | 5 |
| TP | 2 |
| SL | 3 |
| Win rate | 40.0% |
| Median hold | 10s |
| Fast close `<60s` | 5 / 5 |
| 0-15s holds | 3 |
| 15-30s holds | 2 |
| BTC trades | 1 |
| ETH trades | 4 |
| YES trades | 2 |
| NO trades | 3 |
| OPENING trades | 4 |
| ACTIVE trades | 1 |

## Trade Rows

| Position | Hour | Asset | Side | Phase | Entry | Exit | Hold | Outcome | Reason |
|---|---:|---|---|---|---:|---:|---:|---|---|
| `5a3ae6a8` | 06 | ETH | NO | OPENING | 0.50 | 0.57 | 19s | TP | `take_profit_target_reached` |
| `a4061a7f` | 07 | ETH | YES | OPENING | 0.49 | 0.54 | 25s | TP | `take_profit_target_reached` |
| `9ac0205e` | 07 | ETH | NO | ACTIVE | 0.61 | 0.56 | 9s | SL | `stop_loss_triggered` |
| `1ad27444` | 07 | ETH | NO | OPENING | 0.52 | 0.44 | 8s | SL | `stop_loss_triggered` |
| `6b6e28e1` | 08 | BTC | YES | OPENING | 0.59 | 0.57 | 10s | SL | `stop_loss_triggered` |

## BTC / NO Weakness

BTC remains weak in this slice, but the sample is only one trade:

- BTC: 0 TP / 1 SL
- BTC + NO: 0 trades
- BTC + YES + OPENING: 0 TP / 1 SL

NO side remains weak/mixed in this slice:

- NO: 1 TP / 2 SL
- ETH + NO: 1 TP / 2 SL
- NO + ACTIVE: 0 TP / 1 SL
- NO + OPENING: 1 TP / 1 SL

Verdict: the target run is directionally consistent with prior BTC/NO caution, but too small to strengthen either label beyond candidate status.

## 09h10h Evidence

There were no 09h or 10h trades in the target run.

Verdict: no new evidence for or against the 09h10h partial-survival hypothesis.

## Field Gaps

Within the target run path-truth slice:

| Field | Present | Missing | Missing % |
|---|---:|---:|---:|
| `quote_age_ms` | 0 | 6 | 100% |
| `candidate_id` | 0 | 6 | 100% |
| `decision_id` | 0 | 6 | 100% |

No regression conclusion should be drawn from this single slice; the known field gaps remain open and should not be wired until the gate allows it.

## Telegram / Runtime Errors

Precise log searches for Telegram failures, send failures, tracebacks, fatal errors, and true error-level log records found no Telegram errors for the target process log.

Broad log searches still show orderbook recovery and `[OB] Unavailable` warnings, but those are not Telegram failures and were not fatal in this audit slice.

## Verdict

This is a clean single-run evidence slice:

- Path truth emitted cleanly.
- No parse errors.
- No duplicate checkpoint keys.
- `event_end` exists for all 5 trades.
- The run produced 2 TP and 3 SL.
- Fast close remains dominant at 5 / 5 trades.
- No 09h10h evidence was added.
- BTC and NO weakness remain candidates, not resolved conclusions.

Coverage gate remains `INSUFFICIENT_DATES`.

Runtime behavior changed: No.

Live behavior changed: No.

Strategy/risk/execution changed: No.

Tests run: none; this was a read-only evidence and documentation audit.
