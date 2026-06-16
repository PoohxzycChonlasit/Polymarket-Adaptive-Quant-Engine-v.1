"""
Delta Extreme Protection Audit
Reads 7 days of decision logs + canonical ETH YES FC OS CSV.
READ ONLY — no runtime changes.
"""
import json, csv, sys, os
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(encoding='utf-8')

LOG_DIR = 'runtime/quant_data/decision_log'
CSV_PATH = 'runtime/research_exports/completed_trades_v1_2.csv'
DATES_7D = [
    '2026-05-30','2026-05-31','2026-06-01',
    '2026-06-02','2026-06-03','2026-06-04',
    '2026-06-05','2026-06-06',
]

def flt(v):
    try: return float(v)
    except: return None

def ts_to_dt(ts):
    try: return datetime.fromisoformat(ts.replace('Z','+00:00'))
    except: return None

# ── PART 1: 7-DAY DECISION LOG ANALYSIS ──────────────────────────────────────
print('='*72)
print('PART 1 — 7-DAY DECISION LOG ANALYSIS')
print('='*72)

all_recs     = []
delta_recs   = []
exec_recs    = []
daily_total  = Counter()
daily_delta  = Counter()
daily_exec   = Counter()

for date in DATES_7D:
    path = os.path.join(LOG_DIR, f'{date}.jsonl')
    if not os.path.exists(path):
        print(f'  {date}: MISSING — skipped')
        continue
    n_total = n_delta = n_exec = 0
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            try:
                r = json.loads(line)
            except:
                continue
            if r.get('event_type') != 'decision':
                continue
            p = r.get('payload', r)
            block = p.get('candidate_block_reason','') or ''
            order_sz = flt(p.get('calculated_order_size',0)) or 0.0
            conf = flt(p.get('confidence'))
            ev   = flt(p.get('ev_after_spread')) or flt(p.get('ev'))
            regime = p.get('market_regime','UNK') or 'UNK'
            asset  = p.get('asset','UNK') or 'UNK'
            side   = p.get('side','UNK') or 'UNK'
            lc     = p.get('lifecycle_phase','UNK') or 'UNK'
            secs_rem = flt(p.get('seconds_remaining'))
            clob_open = p.get('clob_circuit_open', False)
            clob_cat  = p.get('clob_error_category','') or ''
            skip_primary = p.get('skip_reason_primary','') or ''
            price_vel = flt(p.get('price_velocity'))
            volatility = flt(p.get('realized_volatility')) or flt(p.get('volatility_score'))
            spread = flt(p.get('spread'))
            compression = flt(p.get('compression_score'))

            rec = {
                'date': date,
                'block': block,
                'order_sz': order_sz,
                'conf': conf,
                'ev': ev,
                'regime': regime,
                'asset': asset,
                'side': side,
                'lc': lc,
                'secs_rem': secs_rem,
                'clob_open': clob_open,
                'clob_cat': clob_cat,
                'skip_primary': skip_primary,
                'price_vel': price_vel,
                'volatility': volatility,
                'spread': spread,
                'compression': compression,
            }

            n_total += 1
            all_recs.append(rec)

            if block == 'delta_extreme':
                n_delta += 1
                delta_recs.append(rec)

            if order_sz > 0:
                n_exec += 1
                exec_recs.append(rec)

    daily_total[date] = n_total
    daily_delta[date] = n_delta
    daily_exec[date]  = n_exec

n_all   = len(all_recs)
n_delta = len(delta_recs)
n_exec  = len(exec_recs)

print(f'\nTotal decision records (7d): {n_all:,}')
print(f'Total delta_extreme blocks  : {n_delta:,}  ({n_delta/n_all*100:.1f}%)')
print(f'Total executed (order>0)    : {n_exec:,}  ({n_exec/n_all*100:.3f}%)')

# 1. Daily breakdown
print('\n--- Daily breakdown ---')
print(f'  {"Date":<12} {"Total":>8} {"Delta":>8} {"DeltaPct":>9} {"Exec":>6} {"ExecPct":>8}')
for d in DATES_7D:
    nt = daily_total.get(d,0)
    nd = daily_delta.get(d,0)
    ne = daily_exec.get(d,0)
    if nt == 0: continue
    print(f'  {d:<12} {nt:>8,} {nd:>8,} {nd/nt*100:>8.1f}% {ne:>6,} {ne/nt*100:>7.3f}%')

# 2. Regime breakdown of delta_extreme blocks
print('\n--- Regime breakdown of delta_extreme blocks ---')
regime_cnt = Counter(r['regime'] for r in delta_recs)
regime_all = Counter(r['regime'] for r in all_recs)
for reg, cnt in regime_cnt.most_common():
    total_reg = regime_all.get(reg, 0)
    rate = cnt/total_reg*100 if total_reg else 0
    print(f'  {reg:<15} delta_blocked={cnt:>7,}  total={total_reg:>7,}  delta_rate={rate:.1f}%')

# 3. Quality of delta_extreme blocked candidates
print('\n--- Quality of delta_extreme blocked (EV > 0, confidence thresholds) ---')
d_pos_ev   = [r for r in delta_recs if r['ev'] is not None and r['ev'] > 0]
d_c60_ev   = [r for r in d_pos_ev  if r['conf'] is not None and r['conf'] > 0.60]
d_c65_ev   = [r for r in d_pos_ev  if r['conf'] is not None and r['conf'] > 0.65]
d_c70_ev   = [r for r in d_pos_ev  if r['conf'] is not None and r['conf'] > 0.70]
print(f'  delta_extreme blocked                 : {n_delta:>7,}  (100%)')
print(f'  ... with EV > 0                       : {len(d_pos_ev):>7,}  ({len(d_pos_ev)/n_delta*100:.1f}%)')
print(f'  ... with EV > 0 AND conf > 0.60       : {len(d_c60_ev):>7,}  ({len(d_c60_ev)/n_delta*100:.1f}%)')
print(f'  ... with EV > 0 AND conf > 0.65       : {len(d_c65_ev):>7,}  ({len(d_c65_ev)/n_delta*100:.1f}%)')
print(f'  ... with EV > 0 AND conf > 0.70       : {len(d_c70_ev):>7,}  ({len(d_c70_ev)/n_delta*100:.1f}%)')

# Confidence distribution of delta_extreme blocked
conf_vals = [r['conf'] for r in delta_recs if r['conf'] is not None]
conf_vals.sort()
nc = len(conf_vals)
if nc:
    p50 = conf_vals[nc//2]
    p75 = conf_vals[int(nc*0.75)]
    p90 = conf_vals[int(nc*0.90)]
    low = sum(1 for c in conf_vals if c < 0.55)
    mid = sum(1 for c in conf_vals if 0.55 <= c < 0.65)
    hi  = sum(1 for c in conf_vals if c >= 0.65)
    print(f'\n  Confidence distribution of delta_extreme blocked:')
    print(f'    n={nc:,}  p50={p50:.3f}  p75={p75:.3f}  p90={p90:.3f}')
    print(f'    < 0.55         : {low:>7,} ({low/nc*100:.0f}%)')
    print(f'    0.55–0.65      : {mid:>7,} ({mid/nc*100:.0f}%)')
    print(f'    >= 0.65        : {hi:>7,}  ({hi/nc*100:.0f}%)')

# 4. Comparison: executed vs delta_extreme blocked
print('\n--- Executed trades vs delta_extreme blocked ---')
exec_conf = [r['conf'] for r in exec_recs if r['conf'] is not None]
exec_ev   = [r['ev']   for r in exec_recs if r['ev']   is not None]
delt_conf = [r['conf'] for r in delta_recs if r['conf'] is not None]
delt_ev   = [r['ev']   for r in delta_recs if r['ev']   is not None and r['ev'] > 0]

def stats(vals, label):
    if not vals: return
    vals = sorted(vals)
    n = len(vals)
    print(f'  {label}:  n={n:,}  median={vals[n//2]:.4f}  p75={vals[int(n*0.75)]:.4f}  max={vals[-1]:.4f}')

print('  Confidence:')
stats(exec_conf, 'Executed')
stats(delt_conf, 'Delta-blocked (all)')
print('  EV-after-spread (positive EV subset for delta-blocked):')
stats(exec_ev,  'Executed EV')
stats(delt_ev,  'Delta-blocked EV (pos)')

print('\n  Regime of executed trades:')
exec_regime = Counter(r['regime'] for r in exec_recs)
for reg, cnt in exec_regime.most_common():
    print(f'    {reg:<15} {cnt:>4}')

print('\n  Lifecycle phase of delta_extreme blocked:')
lc_cnt = Counter(r['lc'] for r in delta_recs)
for lc, cnt in lc_cnt.most_common(6):
    print(f'    {lc:<30} {cnt:>7,}  ({cnt/n_delta*100:.1f}%)')

# 5. Sub-trigger analysis: what's actually causing delta_extreme?
print('\n--- Sub-trigger analysis of delta_extreme blocks ---')
clob_circuit_count  = sum(1 for r in delta_recs if r['clob_open'])
not_clob = len(delta_recs) - clob_circuit_count
print(f'  Total delta_extreme blocks            : {n_delta:>7,}')
print(f'  ... clob_circuit_open = True          : {clob_circuit_count:>7,}  ({clob_circuit_count/n_delta*100:.1f}%)')
print(f'  ... clob_circuit_open = False (delta_engine or time gate): {not_clob:>7,}  ({not_clob/n_delta*100:.1f}%)')

skip_primary_cnt = Counter(r['skip_primary'] for r in delta_recs)
print(f'\n  skip_reason_primary breakdown:')
for k, v in skip_primary_cnt.most_common():
    print(f'    {k:<35} {v:>7,}  ({v/n_delta*100:.1f}%)')

clob_cat_cnt = Counter(r['clob_cat'] for r in delta_recs if r['clob_cat'])
print(f'\n  CLOB error category (for delta_extreme blocks):')
for k, v in clob_cat_cnt.most_common():
    print(f'    {k:<35} {v:>7,}')

# Time-remaining distribution for delta_extreme
secs_vals = [r['secs_rem'] for r in delta_recs if r['secs_rem'] is not None]
if secs_vals:
    secs_vals.sort()
    ns = len(secs_vals)
    le90  = sum(1 for s in secs_vals if s <= 90)
    le120 = sum(1 for s in secs_vals if s <= 120)
    gt200 = sum(1 for s in secs_vals if s > 200)
    print(f'\n  Seconds remaining at delta_extreme block:')
    print(f'    n={ns:,}  median={secs_vals[ns//2]:.0f}s  p10={secs_vals[ns//10]:.0f}s  p90={secs_vals[int(ns*0.9)]:.0f}s')
    print(f'    <= 90s (hard time block)  : {le90:>7,}  ({le90/ns*100:.1f}%)')
    print(f'    <= 120s (near-expiry zone): {le120:>7,}  ({le120/ns*100:.1f}%)')
    print(f'    > 200s (early window)     : {gt200:>7,}  ({gt200/ns*100:.1f}%)')

# 5. Counterfactual admission estimate
print('\n--- Counterfactual: if delta_extreme had NOT existed ---')
# Among non-delta-blocked candidates, what fraction get executed?
other_blocked = [r for r in all_recs if r['block'] and r['block'] != 'delta_extreme']
other_passed  = exec_recs  # executed = no block

# Estimate: of delta_extreme blocked with EV>0 and conf>0.60:
# What fraction of comparable (EV>0 AND conf>0.60) non-delta-blocked candidates get executed?
nondelta_evcconf = [r for r in all_recs
                    if r['block'] != 'delta_extreme'
                    and r['ev'] is not None and r['ev'] > 0
                    and r['conf'] is not None and r['conf'] > 0.60]
nondelta_exec_evcconf = [r for r in exec_recs
                         if r['ev'] is not None and r['ev'] > 0
                         and r['conf'] is not None and r['conf'] > 0.60]

exec_rate_comparable = (len(nondelta_exec_evcconf) / len(nondelta_evcconf) * 100
                        if nondelta_evcconf else 0)

# delta_extreme blocked with EV>0 and conf>0.60
delta_hq60 = len(d_c60_ev)
delta_hq65 = len(d_c65_ev)
delta_hq70 = len(d_c70_ev)

# Also: clob-circuit-caused delta_extreme (those should NOT be counted as real missed opps
# since the orderbook was unreliable)
delta_clob_circuit_hq60 = sum(1 for r in delta_recs
                               if r['clob_open'] and r['ev'] is not None and r['ev'] > 0
                               and r['conf'] is not None and r['conf'] > 0.60)
delta_engine_hq60 = delta_hq60 - delta_clob_circuit_hq60

print(f'  Non-delta-blocked candidates with EV>0 AND conf>0.60    : {len(nondelta_evcconf):>7,}')
print(f'  Of those: executed                                       : {len(nondelta_exec_evcconf):>7,}  ({exec_rate_comparable:.2f}%)')
print()
print(f'  Delta-blocked candidates with EV>0 AND conf>0.60        : {delta_hq60:>7,}')
print(f'  Delta-blocked candidates with EV>0 AND conf>0.65        : {delta_hq65:>7,}')
print(f'  Delta-blocked candidates with EV>0 AND conf>0.70        : {delta_hq70:>7,}')
print()
print(f'  Of the conf>0.60 HQ delta-blocked:')
print(f'    Caused by CLOB circuit open (orderbook unreliable)     : {delta_clob_circuit_hq60:>7,}')
print(f'    Caused by delta_engine (genuine price structure risk)  : {delta_engine_hq60:>7,}')
print()
print(f'  IF delta_extreme were removed entirely and execution rate')
print(f'  matched non-delta blocked comparables ({exec_rate_comparable:.2f}%):')
print(f'    Additional admissions from conf>0.60 HQ pool          : ~{delta_hq60 * exec_rate_comparable/100:.0f}')
print(f'    Additional admissions from conf>0.65 HQ pool          : ~{delta_hq65 * exec_rate_comparable/100:.0f}')
print(f'    Additional admissions from conf>0.70 HQ pool          : ~{delta_hq70 * exec_rate_comparable/100:.0f}')
print()
print(f'  CAUTION: This estimate is a CEILING — it assumes delta_extreme')
print(f'  candidates would face the same risk-plan, sizing, and downstream')
print(f'  gates as non-delta candidates. Many would still be rejected.')
print(f'  CLOB-circuit-open candidates should be EXCLUDED (orderbook invalid).')
print(f'  Genuine additional admissions (conf>0.60, non-CLOB): ~{delta_engine_hq60 * exec_rate_comparable/100:.0f}')

# ── PART 2: ETH YES FC OS HISTORICAL VALIDATION ──────────────────────────────
print('\n' + '='*72)
print('PART 2 — ETH YES FC OS HISTORICAL VALIDATION (n=61 canonical trades)')
print('='*72)

eth_yes_fc_os = []
with open(CSV_PATH, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        if r.get('asset','') != 'ETH': continue
        if r.get('side','') != 'YES': continue
        if 'OPENING_SCAN' not in r.get('canonical_entry_lifecycle_phase',''): continue
        hs = flt(r.get('hold_seconds',''))
        if hs is None or hs <= 15: continue
        eth_yes_fc_os.append(r)

print(f'\nETH YES FC OS canonical trades loaded: {len(eth_yes_fc_os)}')

# Proxy for delta risk: decision timing closeness to expiry
def classify_win(r):
    result = r.get('trade_result','') or r.get('outcome_win_loss','')
    pnl = flt(r.get('pnl_usdc')) or flt(r.get('pnl_recomputed')) or 0.0
    if 'WIN' in result.upper() or 'TP' in result.upper(): return 1
    if 'LOSS' in result.upper() or 'SL' in result.upper(): return 0
    if result == '' and pnl > 0: return 1
    if result == '' and pnl < 0: return 0
    return None

wins  = [r for r in eth_yes_fc_os if classify_win(r) == 1]
losses= [r for r in eth_yes_fc_os if classify_win(r) == 0]

print(f'  Wins : {len(wins)}')
print(f'  Losses: {len(losses)}')

# Spread comparison
def spread_stats(trades, label):
    spreads = [flt(r.get('spread')) for r in trades if flt(r.get('spread')) is not None]
    if not spreads: return
    spreads.sort()
    n = len(spreads)
    print(f'  {label} spread: n={n}  median={spreads[n//2]:.4f}  p75={spreads[int(n*0.75)]:.4f}  max={spreads[-1]:.4f}')

print('\n--- Spread at entry (proxy for market volatility/delta conditions) ---')
spread_stats(wins, 'Winners')
spread_stats(losses, 'Losers ')

# Confidence comparison
def conf_stats(trades, label):
    confs = [flt(r.get('confidence')) for r in trades if flt(r.get('confidence')) is not None]
    if not confs: return
    confs.sort()
    n = len(confs)
    print(f'  {label} conf : n={n}  median={confs[n//2]:.4f}  p75={confs[int(n*0.75)]:.4f}  max={confs[-1]:.4f}')

print('\n--- Confidence at entry ---')
conf_stats(wins, 'Winners')
conf_stats(losses, 'Losers ')

# Decision timing from close (proxy for time-pressure delta)
print('\n--- Decision timing from close (proxy for time pressure at entry) ---')
print('   Lower seconds-from-close = higher time pressure = higher delta risk potential')
def time_stats(trades, label):
    vals = [flt(r.get('decision_join_ts_delta_from_close_s')) for r in trades
            if flt(r.get('decision_join_ts_delta_from_close_s')) is not None]
    if not vals: return
    vals.sort()
    n = len(vals)
    lt120 = sum(1 for v in vals if v <= 120)
    lt90  = sum(1 for v in vals if v <= 90)
    print(f'  {label}: n={n}  median={vals[n//2]:.0f}s  p25={vals[n//4]:.0f}s  p10={vals[n//10]:.0f}s  '
          f'<90s={lt90}({lt90/n*100:.0f}%)  <120s={lt120}({lt120/n*100:.0f}%)')

time_stats(wins, 'Winners')
time_stats(losses, 'Losers ')

# Regime breakdown
print('\n--- Regime breakdown ---')
regime_win  = Counter(r.get('regime','UNK') for r in wins)
regime_loss = Counter(r.get('regime','UNK') for r in losses)
all_regimes = set(list(regime_win.keys()) + list(regime_loss.keys()))
print(f'  {"Regime":<14} {"Wins":>5}  {"Losses":>7}  {"WR":>6}')
for reg in sorted(all_regimes):
    w = regime_win.get(reg,0)
    l = regime_loss.get(reg,0)
    wr = w/(w+l)*100 if (w+l) else 0
    print(f'  {reg:<14} {w:>5}  {l:>7}  {wr:>5.1f}%')

# EV at entry
print('\n--- EV after spread at entry ---')
def ev_stats(trades, label):
    evs = [flt(r.get('ev_after_spread')) for r in trades if flt(r.get('ev_after_spread')) is not None]
    if not evs: return
    evs.sort()
    n = len(evs)
    pos = sum(1 for e in evs if e > 0)
    print(f'  {label} EV  : n={n}  median={evs[n//2]:.4f}  pos={pos}({pos/n*100:.0f}%)')

ev_stats(wins, 'Winners')
ev_stats(losses, 'Losers ')

# Hold time and path
print('\n--- Hold time (fast closes may indicate delta-driven reversal) ---')
def hold_stats(trades, label):
    holds = [flt(r.get('hold_seconds')) for r in trades if flt(r.get('hold_seconds')) is not None]
    if not holds: return
    holds.sort()
    n = len(holds)
    fast = sum(1 for h in holds if h <= 30)
    print(f'  {label}: n={n}  median={holds[n//2]:.0f}s  p25={holds[n//4]:.0f}s  fast(<30s)={fast}({fast/n*100:.0f}%)')

hold_stats(wins, 'Winners')
hold_stats(losses, 'Losers ')

# 6. Summary calibration table
print('\n--- Calibration summary: delta risk proxies vs outcome ---')
print(f'  Metric                      Winners ({len(wins)})    Losers ({len(losses)})    Assessment')

# Spread
ws = sorted([flt(r.get('spread')) for r in wins if flt(r.get('spread')) is not None])
ls_s = sorted([flt(r.get('spread')) for r in losses if flt(r.get('spread')) is not None])
wmed = ws[len(ws)//2] if ws else None
lmed = ls_s[len(ls_s)//2] if ls_s else None
print(f'  Spread (median)             {wmed:.4f}            {lmed:.4f}          ', end='')
if wmed and lmed:
    print('Winners LOWER' if wmed < lmed else ('Losers LOWER' if lmed < wmed else 'SIMILAR'))
else: print('N/A')

# Confidence
wc = sorted([flt(r.get('confidence')) for r in wins if flt(r.get('confidence')) is not None])
lc = sorted([flt(r.get('confidence')) for r in losses if flt(r.get('confidence')) is not None])
wcmed = wc[len(wc)//2] if wc else None
lcmed = lc[len(lc)//2] if lc else None
print(f'  Confidence (median)         {wcmed:.4f}            {lcmed:.4f}          ', end='')
if wcmed and lcmed:
    print('Winners HIGHER' if wcmed > lcmed else ('Losers HIGHER' if lcmed > wcmed else 'SIMILAR'))
else: print('N/A')

# Time from close
wt = sorted([flt(r.get('decision_join_ts_delta_from_close_s')) for r in wins if flt(r.get('decision_join_ts_delta_from_close_s')) is not None])
lt = sorted([flt(r.get('decision_join_ts_delta_from_close_s')) for r in losses if flt(r.get('decision_join_ts_delta_from_close_s')) is not None])
wtmed = wt[len(wt)//2] if wt else None
ltmed = lt[len(lt)//2] if lt else None
print(f'  Time-from-close (median)    {wtmed:.0f}s              {ltmed:.0f}s              ', end='')
if wtmed and ltmed:
    print('Winners MORE TIME' if wtmed > ltmed else ('Losers MORE TIME' if ltmed > wtmed else 'SIMILAR'))
else: print('N/A')

print()
