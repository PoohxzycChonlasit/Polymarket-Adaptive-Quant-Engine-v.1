"""
Delta Extreme Causal Verification
READ ONLY — no runtime changes.

Three targeted checks:
  A. Cross-tab clob_circuit_open × executable_book_state for delta_extreme blocks
  B. orderbook_snapshot_age_ms_at_decision: executed vs delta_extreme blocked
  C. Sub-trigger breakdown: time_remaining ≤90s (hard block) vs formula EXTREME
"""
import json, os
from collections import Counter, defaultdict

import sys
sys.stdout.reconfigure(encoding='utf-8')

LOG_DIR = 'runtime/quant_data/decision_log'
DATES   = ['2026-06-06', '2026-06-05', '2026-06-04', '2026-06-03',
           '2026-06-02', '2026-06-01', '2026-05-31', '2026-05-30']

delta_blocked  = []  # clob_circuit_open field not null + candidate_block_reason=delta_extreme
executed       = []  # order_size > 0

def safe_float(v):
    try: return float(v)
    except: return None

for date in DATES:
    path = os.path.join(LOG_DIR, f'{date}.jsonl')
    if not os.path.exists(path):
        continue
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            try: r = json.loads(line)
            except: continue
            if r.get('event_type') != 'decision':
                continue
            p = r.get('payload', r)
            block = str(p.get('candidate_block_reason', '') or '')
            size  = safe_float(p.get('calculated_order_size', 0) or 0)

            if block == 'delta_extreme':
                delta_blocked.append(p)
            if size is not None and size > 0:
                executed.append(p)

print(f'Delta-extreme blocked records : {len(delta_blocked):,}')
print(f'Executed records (order_size>0): {len(executed):,}')
print()

# ── A. Cross-tab clob_circuit_open × executable_book_state ──────────────────
print('='*65)
print('A. Cross-tab clob_circuit_open × executable_book_state')
print('   (for delta_extreme blocked records)')
print('='*65)
cross = Counter()
for p in delta_blocked:
    circuit = bool(p.get('clob_circuit_open', False))
    book    = str(p.get('executable_book_state', 'UNKNOWN') or 'UNKNOWN')
    cross[(circuit, book)] += 1

print(f'\n  {"clob_circuit_open":<20}  {"executable_book_state":<20}  {"count":>8}  {"pct":>6}')
print(f'  {"-"*20}  {"-"*20}  {"-"*8}  {"-"*6}')
n = len(delta_blocked)
for (circ, book), cnt in sorted(cross.items(), key=lambda x: -x[1]):
    print(f'  {str(circ):<20}  {book:<20}  {cnt:>8,}  {cnt/n*100:>5.1f}%')

# How many CLOB-open blocks have TRADABLE cached book?
circuit_tradable = sum(1 for p in delta_blocked
                       if bool(p.get('clob_circuit_open', False))
                       and 'TRADABLE' in str(p.get('executable_book_state', '') or ''))
circuit_total    = sum(1 for p in delta_blocked if bool(p.get('clob_circuit_open', False)))
if circuit_total:
    print(f'\n  Of {circuit_total:,} circuit-open delta_extreme blocks:')
    print(f'    With TRADABLE cached book: {circuit_tradable:,} ({circuit_tradable/circuit_total*100:.1f}%)')
    print(f'    Without TRADABLE           : {circuit_total-circuit_tradable:,} ({(circuit_total-circuit_tradable)/circuit_total*100:.1f}%)')

# What fraction of all delta_extreme blocks have both circuit open AND tradable book?
both = sum(1 for p in delta_blocked
           if bool(p.get('clob_circuit_open', False))
           and 'TRADABLE' in str(p.get('executable_book_state', '') or ''))
print(f'\n  Delta-extreme blocks with circuit_open=True AND TRADABLE: {both:,} ({both/n*100:.1f}%)')

# ── B. orderbook_snapshot_age_ms_at_decision comparison ─────────────────────
print()
print('='*65)
print('B. orderbook_snapshot_age_ms_at_decision')
print('   Executed vs delta_extreme blocked')
print('='*65)

def pct(vals, p):
    if not vals: return float('nan')
    vals = sorted(vals)
    idx = int(len(vals) * p / 100)
    return vals[min(idx, len(vals)-1)]

age_field = 'orderbook_snapshot_age_ms_at_decision'
age_executed = [v for p in executed
                if (v := safe_float(p.get(age_field))) is not None]
age_blocked  = [v for p in delta_blocked
                if (v := safe_float(p.get(age_field))) is not None]

alt_fields = ['orderbook_age_ms', 'yes_orderbook_age_ms']

for label, ages, pool in [('Executed', age_executed, executed),
                           ('Delta-blocked', age_blocked, delta_blocked)]:
    print(f'\n  {label} (n={len(pool):,}):')
    if ages:
        print(f'    {age_field}: n={len(ages):,}')
        print(f'      p25={pct(ages,25):.0f}ms  p50={pct(ages,50):.0f}ms  p75={pct(ages,75):.0f}ms  p90={pct(ages,90):.0f}ms')
        stale_1s = sum(1 for v in ages if v > 1000)
        stale_5s = sum(1 for v in ages if v > 5000)
        print(f'      >1s (stale): {stale_1s} ({stale_1s/len(ages)*100:.1f}%)')
        print(f'      >5s (very stale): {stale_5s} ({stale_5s/len(ages)*100:.1f}%)')
    else:
        print(f'    {age_field}: NOT FOUND in logs')
        # Try alternatives
        for af in alt_fields:
            alt_ages = [v for p in pool if (v := safe_float(p.get(af))) is not None]
            if alt_ages:
                print(f'    {af}: n={len(alt_ages):,}  p50={pct(alt_ages,50):.0f}ms  p90={pct(alt_ages,90):.0f}ms')
                break

# ── C. Sub-trigger breakdown ─────────────────────────────────────────────────
print()
print('='*65)
print('C. Sub-trigger breakdown for delta_extreme blocks')
print('   time_remaining ≤90s = hard block (delta_score forced to 10.0)')
print('   time_remaining >90s = formula EXTREME (delta_score >4.0)')
print('='*65)

hard_block  = []
formula_ext = []
no_seconds  = []

for p in delta_blocked:
    secs = safe_float(p.get('seconds_remaining') or p.get('time_remaining_seconds'))
    if secs is None:
        no_seconds.append(p)
    elif secs <= 90:
        hard_block.append(p)
    else:
        formula_ext.append(p)

nb = len(delta_blocked)
print(f'\n  Hard block (≤90s)  : {len(hard_block):>7,}  ({len(hard_block)/nb*100:.1f}%)')
print(f'  Formula EXTREME(>90s): {len(formula_ext):>7,}  ({len(formula_ext)/nb*100:.1f}%)')
print(f'  Unknown seconds    : {len(no_seconds):>7,}  ({len(no_seconds)/nb*100:.1f}%)')

# For formula EXTREME: what is the regime breakdown?
if formula_ext:
    regime_cnt = Counter(p.get('market_regime', 'UNK') for p in formula_ext)
    circ_cnt   = Counter(bool(p.get('clob_circuit_open', False)) for p in formula_ext)
    print(f'\n  Formula EXTREME regime breakdown:')
    for k, v in regime_cnt.most_common():
        print(f'    {k:<25} {v:>6,}  ({v/len(formula_ext)*100:.1f}%)')
    print(f'\n  Formula EXTREME: clob_circuit_open distribution:')
    for k, v in sorted(circ_cnt.items()):
        print(f'    circuit_open={k}  {v:>6,}  ({v/len(formula_ext)*100:.1f}%)')

# For hard block: same circuit distribution
if hard_block:
    circ_hb = Counter(bool(p.get('clob_circuit_open', False)) for p in hard_block)
    print(f'\n  Hard block: clob_circuit_open distribution:')
    for k, v in sorted(circ_hb.items()):
        print(f'    circuit_open={k}  {v:>6,}  ({v/len(hard_block)*100:.1f}%)')

# ── D. EV comparison by sub-trigger ─────────────────────────────────────────
print()
print('='*65)
print('D. EV distribution by sub-trigger')
print('='*65)

def ev_stats(pool, label):
    evs = [v for p in pool if (v := safe_float(p.get('ev_after_spread'))) is not None and v > -1]
    if not evs:
        print(f'  {label}: no EV data')
        return
    print(f'  {label} (n={len(evs):,}): p25={pct(evs,25):.4f}  p50={pct(evs,50):.4f}  p75={pct(evs,75):.4f}  p90={pct(evs,90):.4f}')
    pos = sum(1 for v in evs if v > 0)
    print(f'    EV>0: {pos} ({pos/len(evs)*100:.1f}%)')

ev_stats(executed,   'Executed')
ev_stats(hard_block, 'Hard block (≤90s)')
ev_stats(formula_ext,'Formula EXTREME (>90s)')
