"""ETH YES FC OS Regime Transition / Drift Audit.

Source: canonical_regime_enriched_trades_v1.csv (market_regime column).
Legacy fallback: completed_trades_v1_2.csv (regime column).

Row qualification contract (mirrors canonical_regime_export._cell_qualifies):
  1. asset = ETH
  2. side = YES
  3. OPENING_SCAN in canonical_entry_lifecycle_phase
  4. hold_seconds > 15
  5. canonical_retained_flag = true  (dedup guard; absent/None defaults to true)
  6. trade_result in {TP, SL} OR pnl_usdc not empty  (outcome quality gate)

Offline/reporting only — no runtime imports, no strategy/risk/execution changes.
Run: py -3.11 tools/_drift_audit.py
"""
from __future__ import annotations

import csv
import sys
import warnings
from datetime import date as _date
from typing import Optional


_CANONICAL_PATH = 'runtime/research_exports/canonical_regime_enriched_trades_v1.csv'


# ---------------------------------------------------------------------------
# Pure helpers — side-effect-free, importable for tests
# ---------------------------------------------------------------------------

def _validate_regime_column(fieldnames) -> None:
    """Raise SystemExit if neither market_regime nor regime column is present.

    Fail-loud guard: prevents silent UNKNOWN fallback from producing a
    confidently-wrong drift document when run against the wrong source.
    """
    names = set(fieldnames) if fieldnames else set()
    if 'market_regime' not in names and 'regime' not in names:
        sys.exit(
            'ERROR: Source CSV has neither market_regime nor regime column.\n'
            'Required: canonical_regime_enriched_trades_v1.csv (market_regime) '
            'or completed_trades_v1_2.csv (regime).'
        )


def _regime(r: dict) -> str:
    """Resolve regime: market_regime (canonical) → regime (legacy CSV) → UNKNOWN."""
    return (r.get('market_regime') or r.get('regime') or 'UNKNOWN').strip().upper()


def _flt(v) -> Optional[float]:
    """Parse float, return None on failure."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _row_qualifies(r: dict) -> bool:
    """Full ETH YES FC OS row qualification predicate.

    Mirrors canonical_regime_export._cell_qualifies() so the drift audit
    counts exactly the same rows the canonical export does.

    Filters:
      1. asset = ETH
      2. side = YES
      3. OPENING_SCAN in canonical_entry_lifecycle_phase
      4. hold_seconds > 15
      5. canonical_retained_flag = true  -- dedup guard.
         Absent or None value defaults to 'true' (legacy-CSV compatible:
         rows from a CSV without this column are included, not dropped).
      6. trade_result in {TP, SL}  OR  pnl_usdc not empty  -- outcome gate.
         Excludes open/unresolved rows that the export also excludes.
    """
    # 1. asset
    if r.get('asset', '') != 'ETH':
        return False
    # 2. side
    if r.get('side', '') != 'YES':
        return False
    # 3. lifecycle phase  — (... or '') handles None values from test dicts safely
    if 'OPENING_SCAN' not in (r.get('canonical_entry_lifecycle_phase') or ''):
        return False
    # 4. hold
    hs = _flt(r.get('hold_seconds', ''))
    if hs is None or hs <= 15:
        return False
    # 5. dedup guard — (... or 'true') so absent/None column defaults to include
    if (r.get('canonical_retained_flag') or 'true').lower() != 'true':
        return False
    # 6. outcome quality gate
    trade_result = r.get('trade_result', '')
    pnl_raw = r.get('pnl_usdc', '')
    if trade_result not in {'TP', 'SL'} and pnl_raw in {None, ''}:
        return False
    return True


def _iso_week(entry_ts: str, exit_ts: str = '') -> str:
    """Derive bare ISO week label (e.g. 'W21') from an ISO timestamp or date string.

    Tries entry_ts first, then exit_ts, then returns 'WUNK' as a safe sentinel.
    Accepts full ISO timestamps ('2026-05-22T10:00:00Z') or date strings ('2026-05-22').
    """
    for ts in (entry_ts, exit_ts):
        try:
            d_obj = _date.fromisoformat(ts[:10])
            _, iso_week, _ = d_obj.isocalendar()
            return f'W{iso_week:02d}'
        except (ValueError, AttributeError, TypeError):
            continue
    return 'WUNK'


def _nc_pf(window: list[dict]) -> Optional[float]:
    """nc_PF: PF computed on non-COMPRESSION trades in window only.

    Returns None when the non-COMPRESSION subset has no wins or no losses.
    """
    nc = [t for t in window if t['regime'] != 'COMPRESSION']
    wins   = [t['pnl'] for t in nc if t['pnl'] > 0]
    losses = [t['pnl'] for t in nc if t['pnl'] < 0]
    if not wins or not losses:
        return None
    return sum(wins) / abs(sum(losses))


def _phase_buckets(n: int) -> list[tuple[str, int, int]]:
    """Equal-thirds phase segmentation covering all n trades with no index gaps."""
    third = n // 3
    return [
        (f'Early #1-{third}',             1,           third),
        (f'Mid   #{third+1}-{2*third}',   third + 1,   2 * third),
        (f'Late  #{2*third+1}-{n}',       2*third + 1, n),
    ]


# ---------------------------------------------------------------------------
# Rolling metric helpers
# ---------------------------------------------------------------------------

def _rolling_pf(trades: list[dict], i: int, w: int = 20) -> Optional[float]:
    window = trades[max(0, i - w + 1):i + 1]
    wins   = [t['pnl'] for t in window if t['pnl'] > 0]
    losses = [t['pnl'] for t in window if t['pnl'] < 0]
    if not losses or not wins:
        return None
    return sum(wins) / abs(sum(losses))


def _rolling_wr(trades: list[dict], i: int, w: int = 20) -> Optional[float]:
    window = trades[max(0, i - w + 1):i + 1]
    if not window:
        return None
    return sum(t['win'] for t in window) / len(window)


def _rolling_comp_pf(trades: list[dict], i: int, w: int = 20) -> Optional[float]:
    """Rolling nc_PF: delegates to _nc_pf for testability."""
    return _nc_pf(trades[max(0, i - w + 1):i + 1])


def _rolling_comp_share(trades: list[dict], i: int, w: int = 20) -> Optional[float]:
    window = trades[max(0, i - w + 1):i + 1]
    if not window:
        return None
    return sum(1 for t in window if t['regime'] == 'COMPRESSION') / len(window)


# ---------------------------------------------------------------------------
# Main execution block — all I/O, side effects, and printing live here
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import argparse
    sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--path',
        default=_CANONICAL_PATH,
        help='Canonical regime export CSV path (default: %(default)s)',
    )
    args = parser.parse_args()
    path = args.path

    rows: list[dict] = []
    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        _validate_regime_column(reader.fieldnames or [])
        for r in reader:
            if _row_qualifies(r):
                rows.append(r)

    rows.sort(key=lambda r: (r.get('entry_ts', ''), r.get('epoch_start_ts', '')))

    trades: list[dict] = []
    for i, r in enumerate(rows):
        pnl = _flt(r.get('pnl_usdc')) or _flt(r.get('pnl_recomputed')) or 0.0
        reg = _regime(r)
        result = r.get('trade_result', '') or r.get('outcome_win_loss', '')
        win = 1 if ('WIN' in result.upper() or 'TP' in result.upper()) else 0
        if result == '' and pnl > 0:
            win = 1
        if result == '' and pnl < 0:
            win = 0
        trades.append({
            'idx':    i + 1,
            'regime': reg,
            'pnl':    pnl,
            'win':    win,
            'date':   r.get('entry_ts', '')[:10],
        })

    # Warn (not exit) if UNKNOWN regimes remain after column-presence check passed
    unknown_count = sum(1 for t in trades if t['regime'] == 'UNKNOWN')
    if unknown_count:
        warnings.warn(
            f'{unknown_count}/{len(trades)} trades resolved to UNKNOWN regime — '
            'nc_PF exclusion may be incomplete.',
            stacklevel=1,
        )

    metrics: list[dict] = []
    for i in range(len(trades)):
        metrics.append({
            'idx':    trades[i]['idx'],
            'date':   trades[i]['date'],
            'regime': trades[i]['regime'],
            'pnl':    trades[i]['pnl'],
            'win':    trades[i]['win'],
            'rwr':    _rolling_wr(trades, i),
            'rpf':    _rolling_pf(trades, i),
            'ncpf':   _rolling_comp_pf(trades, i),
            'csh':    _rolling_comp_share(trades, i),
        })

    # ---- full-window metrics (idx >= 20) ----
    full      = [m for m in metrics if m['idx'] >= 20]
    wr_vals   = [m['rwr']  for m in full if m['rwr']  is not None]
    pf_vals   = [m['rpf']  for m in full if m['rpf']  is not None]
    ncpf_vals = [m['ncpf'] for m in full if m['ncpf'] is not None]
    csh_vals  = [m['csh']  for m in full if m['csh']  is not None]

    print('=== ROLLING EXTREMES (full 20-wide windows, idx>=20) ===')
    print(f'Rolling WR :  min={min(wr_vals)*100:.1f}%  max={max(wr_vals)*100:.1f}%  final={wr_vals[-1]*100:.1f}%')
    print(f'Rolling PF :  min={min(pf_vals):.3f}   max={max(pf_vals):.3f}   final={pf_vals[-1]:.3f}')
    print(f'nc PF      :  min={min(ncpf_vals):.3f}   max={max(ncpf_vals):.3f}   final={ncpf_vals[-1]:.3f}')
    print(f'COMP share :  min={min(csh_vals)*100:.1f}%  max={max(csh_vals)*100:.1f}%  final={csh_vals[-1]*100:.1f}%')

    min_wr_m = min(full, key=lambda m: m['rwr']  if m['rwr']  else 1.0)
    min_pf_m = min(full, key=lambda m: m['rpf']  if m['rpf']  else 99.0)
    min_nc_m = min(full, key=lambda m: m['ncpf'] if m['ncpf'] else 99.0)
    print(f'\nWR trough:  #{min_wr_m["idx"]} {min_wr_m["date"]} = {min_wr_m["rwr"]*100:.1f}%')
    print(f'PF trough:  #{min_pf_m["idx"]} {min_pf_m["date"]} = {min_pf_m["rpf"]:.3f}')
    print(f'nc_PF low:  #{min_nc_m["idx"]} {min_nc_m["date"]} = {min_nc_m["ncpf"]:.3f}')

    print('\n=== PERIODS WHEN ROLLING WR < 52% ===')
    for m in metrics:
        if m['rwr'] is not None and m['rwr'] < 0.52:
            print(f'  #{m["idx"]:>2} {m["date"]}  {m["regime"]:<12} WR={m["rwr"]*100:.1f}%')

    print('\n=== PERIODS WHEN ROLLING PF < 1.5 ===')
    for m in metrics:
        if m['rpf'] is not None and m['rpf'] < 1.5:
            print(f'  #{m["idx"]:>2} {m["date"]}  {m["regime"]:<12} PF={m["rpf"]:.3f}')

    print('\n=== PERIODS WHEN nc_PF < 1.0 ===')
    for m in metrics:
        if m['ncpf'] is not None and m['ncpf'] < 1.0:
            print(f'  #{m["idx"]:>2} {m["date"]}  {m["regime"]:<12} nc_PF={m["ncpf"]:.3f}')

    print('\n=== CONSECUTIVE REGIME RUNS ===')
    runs: list[dict] = []
    cur_reg = None
    cur_run: list[dict] = []
    cur_wins = 0
    cur_pnl  = 0.0
    for t in trades:
        if t['regime'] != cur_reg:
            if cur_reg is not None:
                runs.append({
                    'regime':     cur_reg,
                    'start':      cur_run[0]['idx'],
                    'end':        cur_run[-1]['idx'],
                    'n':          len(cur_run),
                    'wins':       cur_wins,
                    'pnl':        cur_pnl,
                    'start_date': cur_run[0]['date'],
                })
            cur_reg  = t['regime']
            cur_run  = [t]
            cur_wins = t['win']
            cur_pnl  = t['pnl']
        else:
            cur_run.append(t)
            cur_wins += t['win']
            cur_pnl  += t['pnl']
    if cur_run:
        runs.append({
            'regime':     cur_reg,
            'start':      cur_run[0]['idx'],
            'end':        cur_run[-1]['idx'],
            'n':          len(cur_run),
            'wins':       cur_wins,
            'pnl':        cur_pnl,
            'start_date': cur_run[0]['date'],
        })

    print(f'{"Run":<4} {"Regime":<12} {"Idx range":<12} {"Date":<12} {"n":>3} {"W/L":<7} {"PnL":>10}')
    for run_i, run in enumerate(runs):
        wl = f'{run["wins"]}W/{run["n"] - run["wins"]}L'
        print(f'  {run_i+1:<3} {run["regime"]:<12} #{run["start"]}-#{run["end"]:<4} '
              f'{run["start_date"]:<12} {run["n"]:>3} {wl:<7} {run["pnl"]:+.5f}')

    print('\n=== CALENDAR WEEK BREAKDOWN ===')
    weeks: dict = {}
    for t in trades:
        w = _iso_week(t['date'])
        if w not in weeks:
            weeks[w] = {'trades': [], 'wins': 0, 'pnl': 0.0, 'regimes': {}}
        weeks[w]['trades'].append(t)
        weeks[w]['wins'] += t['win']
        weeks[w]['pnl']  += t['pnl']
        weeks[w]['regimes'][t['regime']] = weeks[w]['regimes'].get(t['regime'], 0) + 1

    for w, wd in sorted(weeks.items()):
        n_w  = len(wd['trades'])
        wr   = wd['wins'] / n_w * 100
        gw   = sum(t['pnl'] for t in wd['trades'] if t['pnl'] > 0)
        gl   = sum(t['pnl'] for t in wd['trades'] if t['pnl'] < 0)
        pf   = gw / abs(gl) if gl else 999.0
        regs = ', '.join(f'{k}:{v}' for k, v in sorted(wd['regimes'].items(), key=lambda x: -x[1]))
        print(f'  {w}: n={n_w:>2}  WR={wr:.1f}%  PF={pf:.3f}  net={wd["pnl"]:+.5f}  [{regs}]')

    print('\n=== FULL CELL STATS ===')
    all_w = [t['pnl'] for t in trades if t['pnl'] > 0]
    all_l = [t['pnl'] for t in trades if t['pnl'] < 0]
    print(f'n={len(trades)}  WR={sum(t["win"] for t in trades)/len(trades)*100:.1f}%  '
          f'PF={sum(all_w)/abs(sum(all_l)):.3f}  net={sum(t["pnl"] for t in trades):+.5f}')

    print('\n=== REGIME STATS ===')
    for reg in ['COMPRESSION', 'TREND_DOWN', 'SIDEWAY', 'TREND_UP']:
        rt = [t for t in trades if t['regime'] == reg]
        if not rt:
            continue
        rw  = [t['pnl'] for t in rt if t['pnl'] > 0]
        rl  = [t['pnl'] for t in rt if t['pnl'] < 0]
        wr  = sum(t['win'] for t in rt) / len(rt) * 100
        pf  = sum(rw) / abs(sum(rl)) if rl and rw else None
        net = sum(t['pnl'] for t in rt)
        pf_s = f'{pf:.3f}' if pf else 'N/A (no losses)'
        print(f'  {reg:<12}  n={len(rt):>2}  WR={wr:.1f}%  PF={pf_s}  net={net:+.5f}')

    # Phase segmentation: equal thirds, n-derived, covers all trades
    print('\n=== PHASE SEGMENTATION (early/mid/late) ===')
    for label, lo, hi in _phase_buckets(len(trades)):
        seg = [t for t in trades if lo <= t['idx'] <= hi]
        if not seg:
            print(f'  {label}: n=0  (no trades in range)')
            continue
        sw   = [t['pnl'] for t in seg if t['pnl'] > 0]
        sl   = [t['pnl'] for t in seg if t['pnl'] < 0]
        wr   = sum(t['win'] for t in seg) / len(seg) * 100
        pf   = sum(sw) / abs(sum(sl)) if sl and sw else None
        pf_s = f'{pf:.3f}' if pf else 'N/A'
        reg_c: dict = {}
        for t in seg:
            reg_c[t['regime']] = reg_c.get(t['regime'], 0) + 1
        reg_s = ' '.join(f'{k[:4]}:{v}' for k, v in sorted(reg_c.items(), key=lambda x: -x[1]))
        print(f'  {label}: n={len(seg)}  WR={wr:.1f}%  PF={pf_s}  [{reg_s}]')
