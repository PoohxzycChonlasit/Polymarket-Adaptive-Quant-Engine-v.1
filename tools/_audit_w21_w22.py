"""W21 vs W22 TREND_DOWN causality analysis — READ ONLY, no runtime wiring."""
import sys, csv, math, datetime
sys.stdout.reconfigure(encoding='utf-8')
from collections import Counter

rows = []
with open('runtime/research_exports/completed_trades_v1_2.csv', newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        rows.append(r)

def flt(v, default=None):
    try:
        return float(v)
    except:
        return default

def eth_yes_fc_os_td(r):
    if r['asset'] != 'ETH': return False
    if r['side'] != 'YES': return False
    if r['canonical_entry_lifecycle_phase'] != 'OPENING_SCAN': return False
    hs = flt(r['hold_seconds'])
    if hs is None or hs <= 15: return False
    if r['regime'] != 'TREND_DOWN': return False
    return True

def week_of(r):
    d = r['entry_ts'][:10]
    if '2026-05-18' <= d <= '2026-05-24': return 'W21'
    if '2026-05-25' <= d <= '2026-05-31': return 'W22'
    return 'Other'

def is_win(r): return flt(r['pnl_usdc'], 0) > 0

def med(vals):
    s = sorted(v for v in vals if v is not None)
    if not s: return None
    n = len(s)
    return s[n//2] if n % 2 else (s[n//2-1] + s[n//2]) / 2

def avg(vals):
    v = [x for x in vals if x is not None]
    return sum(v) / len(v) if v else None

def exit_delta(r):
    return flt(r['exit_price'], 0) - flt(r['entry_price'], 0)

td = [r for r in rows if eth_yes_fc_os_td(r)]
w21 = [r for r in td if week_of(r) == 'W21']
w22 = [r for r in td if week_of(r) == 'W22']

print(f'n: W21={len(w21)}  W22={len(w22)}')

# 1. ENTRY PRICE
ep21 = [flt(r['entry_price']) for r in w21]
ep22 = [flt(r['entry_price']) for r in w22]
print('\n1. ENTRY PRICE')
print(f'   W21: avg={avg(ep21):.3f}  med={med(ep21):.3f}  min={min(ep21):.2f}  max={max(ep21):.2f}')
print(f'   W22: avg={avg(ep22):.3f}  med={med(ep22):.3f}  min={min(ep22):.2f}  max={max(ep22):.2f}')
print(f'   W21 wins avg={avg([flt(r["entry_price"]) for r in w21 if is_win(r)]):.3f}  losses avg={avg([flt(r["entry_price"]) for r in w21 if not is_win(r)]):.3f}')
print(f'   W22 wins avg={avg([flt(r["entry_price"]) for r in w22 if is_win(r)]):.3f}  losses avg={avg([flt(r["entry_price"]) for r in w22 if not is_win(r)]):.3f}')

# 2. EXIT-ENTRY DELTA
d21 = [exit_delta(r) for r in w21]
d22 = [exit_delta(r) for r in w22]
print('\n2. EXIT-ENTRY DELTA')
print(f'   W21: avg={avg(d21):+.4f}  wins avg={avg([exit_delta(r) for r in w21 if is_win(r)]):+.4f}  losses avg={avg([exit_delta(r) for r in w21 if not is_win(r)]):+.4f}')
print(f'   W22: avg={avg(d22):+.4f}  wins avg={avg([exit_delta(r) for r in w22 if is_win(r)]):+.4f}  losses avg={avg([exit_delta(r) for r in w22 if not is_win(r)]):+.4f}')
print('   W21 individual deltas (sorted):', sorted([round(exit_delta(r),3) for r in w21]))
print('   W22 individual deltas (sorted):', sorted([round(exit_delta(r),3) for r in w22]))

# 3. SPREAD
sp21 = [flt(r['spread']) for r in w21]
sp22 = [flt(r['spread']) for r in w22]
print('\n3. SPREAD')
print(f'   W21: avg={avg(sp21):.4f}  0.02-spread count={sum(1 for s in sp21 if s > 0.015)}/{len(sp21)}')
print(f'   W22: avg={avg(sp22):.4f}  0.02-spread count={sum(1 for s in sp22 if s > 0.015)}/{len(sp22)}')

# 4. DISTANCE FROM PTB
ptb21 = [flt(r['distance_from_ptb']) for r in w21 if flt(r['distance_from_ptb']) is not None]
ptb22 = [flt(r['distance_from_ptb']) for r in w22 if flt(r['distance_from_ptb']) is not None]
print('\n4. DISTANCE FROM PTB')
if ptb21:
    print(f'   W21: n={len(ptb21)}  avg={avg(ptb21):.4f}  med={med(ptb21):.4f}')
else:
    print('   W21: no data')
if ptb22:
    print(f'   W22: n={len(ptb22)}  avg={avg(ptb22):.4f}  med={med(ptb22):.4f}')
else:
    print('   W22: no data')

# 5. EV and TRUE PROBABILITY
ev21 = [flt(r['expected_value']) for r in w21]
ev22 = [flt(r['expected_value']) for r in w22]
tp21 = [flt(r['true_probability']) for r in w21]
tp22 = [flt(r['true_probability']) for r in w22]
print('\n5. EXPECTED VALUE')
print(f'   W21: avg={avg(ev21):.4f}  med={med(ev21):.4f}  min={min(ev21):.4f}  max={max(ev21):.4f}')
print(f'   W22: avg={avg(ev22):.4f}  med={med(ev22):.4f}  min={min(ev22):.4f}  max={max(ev22):.4f}')
print(f'   W21 wins EV avg={avg([flt(r["expected_value"]) for r in w21 if is_win(r)]):.4f}  losses EV avg={avg([flt(r["expected_value"]) for r in w21 if not is_win(r)]):.4f}')
print(f'   W22 wins EV avg={avg([flt(r["expected_value"]) for r in w22 if is_win(r)]):.4f}  losses EV avg={avg([flt(r["expected_value"]) for r in w22 if not is_win(r)]):.4f}')
print('\n   TRUE PROBABILITY (model)')
print(f'   W21: avg={avg(tp21):.4f}  med={med(tp21):.4f}')
print(f'   W22: avg={avg(tp22):.4f}  med={med(tp22):.4f}')

# 6. CONFIDENCE
conf21 = [flt(r['confidence']) for r in w21]
conf22 = [flt(r['confidence']) for r in w22]
print('\n6. CONFIDENCE')
print(f'   W21: avg={avg(conf21):.4f}  all zero={all(c==0 for c in conf21 if c is not None)}')
print(f'   W22: avg={avg(conf22):.4f}  all zero={all(c==0 for c in conf22 if c is not None)}')

# 7. EV QUARTILE
print('\n7. EV QUARTILE')
print(f'   W21: {dict(Counter(r["ev_quartile"] for r in w21))}')
print(f'   W22: {dict(Counter(r["ev_quartile"] for r in w22))}')
print(f'   W21 wins: {dict(Counter(r["ev_quartile"] for r in w21 if is_win(r)))}')
print(f'   W21 losses: {dict(Counter(r["ev_quartile"] for r in w21 if not is_win(r)))}')
print(f'   W22 wins: {dict(Counter(r["ev_quartile"] for r in w22 if is_win(r)))}')
print(f'   W22 losses: {dict(Counter(r["ev_quartile"] for r in w22 if not is_win(r)))}')

# 8. TP/SL
print('\n8. TP/SL DISTRIBUTION')
tp21_n = sum(1 for r in w21 if r["tp_hit"]=="True")
sl21_n = sum(1 for r in w21 if r["sl_hit"]=="True")
tp22_n = sum(1 for r in w22 if r["tp_hit"]=="True")
sl22_n = sum(1 for r in w22 if r["sl_hit"]=="True")
print(f'   W21: TP={tp21_n}  SL={sl21_n}  TP-rate={tp21_n/len(w21)*100:.0f}%')
print(f'   W22: TP={tp22_n}  SL={sl22_n}  TP-rate={tp22_n/len(w22)*100:.0f}%')
print('   W21 SL loss magnitudes:', sorted([abs(flt(r["pnl_usdc"],0)) for r in w21 if not is_win(r)]))
print('   W22 SL loss magnitudes:', sorted([abs(flt(r["pnl_usdc"],0)) for r in w22 if not is_win(r)]))

# 9. HOLD TIME
hs21 = [flt(r['hold_seconds']) for r in w21]
hs22 = [flt(r['hold_seconds']) for r in w22]
print('\n9. HOLD TIME (seconds)')
print(f'   W21: avg={avg(hs21):.1f}  med={med(hs21):.0f}  range=[{min(hs21):.0f},{max(hs21):.0f}]')
print(f'   W22: avg={avg(hs22):.1f}  med={med(hs22):.0f}  range=[{min(hs22):.0f},{max(hs22):.0f}]')
print(f'   W21 wins hold avg={avg([flt(r["hold_seconds"]) for r in w21 if is_win(r)]):.1f}  losses hold avg={avg([flt(r["hold_seconds"]) for r in w21 if not is_win(r)]):.1f}')
print(f'   W22 wins hold avg={avg([flt(r["hold_seconds"]) for r in w22 if is_win(r)]):.1f}  losses hold avg={avg([flt(r["hold_seconds"]) for r in w22 if not is_win(r)]):.1f}')

# 10. SESSION
print('\n10. SESSION (UTC hour)')
sess21 = Counter(int(r['session_hour_utc']) for r in w21)
sess22 = Counter(int(r['session_hour_utc']) for r in w22)
print(f'   W21: {dict(sorted(sess21.items()))}')
print(f'   W22: {dict(sorted(sess22.items()))}')

# 11. QUOTE AGE
qa21 = [flt(r['quote_age_at_submit_ms']) for r in w21 if flt(r['quote_age_at_submit_ms']) is not None]
qa22 = [flt(r['quote_age_at_submit_ms']) for r in w22 if flt(r['quote_age_at_submit_ms']) is not None]
print('\n11. QUOTE AGE AT SUBMIT (ms)')
if qa21:
    print(f'   W21: n={len(qa21)}  avg={avg(qa21):.0f}ms  med={med(qa21):.0f}ms  range=[{min(qa21):.0f},{max(qa21):.0f}]')
else:
    print('   W21: n=0 (logging not active pre-May 23)')
print(f'   W22: n={len(qa22)}  avg={avg(qa22):.0f}ms  med={med(qa22):.0f}ms  range=[{min(qa22):.0f},{max(qa22):.0f}]')

# 12. NOTIONAL
nt21 = [flt(r['notional_entry']) for r in w21]
nt22 = [flt(r['notional_entry']) for r in w22]
print('\n12. NOTIONAL ENTRY ($)')
print(f'   W21: avg=${avg(nt21):.4f}  range=[${min(nt21):.4f},${max(nt21):.4f}]')
print(f'   W22: avg=${avg(nt22):.4f}  range=[${min(nt22):.4f},${max(nt22):.4f}]')

# 13. MARKET AGE (epoch_start_ts)
print('\n13. EPOCH START (market cycle start)')
for r in sorted(td, key=lambda x: x['entry_ts']):
    e = flt(r['epoch_start_ts'])
    ets = r['entry_ts'][:19]
    w = week_of(r)
    result = 'W' if is_win(r) else 'L'
    if e:
        epoch_dt = datetime.datetime.utcfromtimestamp(e).strftime('%Y-%m-%dT%H:%M')
        entry_dt = datetime.datetime.strptime(ets, '%Y-%m-%dT%H:%M:%S')
        epoch_start_dt = datetime.datetime.utcfromtimestamp(e)
        age_minutes = (entry_dt - epoch_start_dt).total_seconds() / 60
        pnl = flt(r['pnl_usdc'], 0)
        print(f'   [{w}][{result}] {ets}  epoch={epoch_dt}  age_at_entry={age_minutes:.0f}min  pnl={pnl:+.5f}')

# 14. PRICE MOVE SIZE ANALYSIS
print('\n14. WIN SIZE vs LOSS SIZE')
wins21 = [flt(r['pnl_usdc'],0) for r in w21 if is_win(r)]
losses21 = [abs(flt(r['pnl_usdc'],0)) for r in w21 if not is_win(r)]
wins22 = [flt(r['pnl_usdc'],0) for r in w22 if is_win(r)]
losses22 = [abs(flt(r['pnl_usdc'],0)) for r in w22 if not is_win(r)]
print(f'   W21 avg win={avg(wins21):+.5f}  avg loss={avg(losses21):.5f}  ratio={avg(wins21)/avg(losses21):.2f}x')
print(f'   W22 avg win={avg(wins22):+.5f}  avg loss={avg(losses22):.5f}  ratio={avg(wins22)/avg(losses22):.2f}x')
print(f'   W21 wins: {[round(v,5) for v in sorted(wins21)]}')
print(f'   W22 wins: {[round(v,5) for v in sorted(wins22)]}')
print(f'   W21 losses: {[round(v,5) for v in sorted(losses21)]}')
print(f'   W22 losses: {[round(v,5) for v in sorted(losses22)]}')
