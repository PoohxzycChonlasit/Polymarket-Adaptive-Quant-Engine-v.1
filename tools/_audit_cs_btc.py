"""Extract BTC state and analyze cs-outcome relationship for TREND_DOWN trades."""
import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')

log_dir = 'runtime/quant_data/decision_log'

# Trade list with known ETH cs values from previous run
trades_data = [
    ('2026-05-19', '2026-05-19T09:50', 'W21', 'WIN',  0.218),
    ('2026-05-19', '2026-05-19T11:40', 'W21', 'LOSS', 0.627),
    ('2026-05-19', '2026-05-19T14:35', 'W21', 'WIN',  0.000),
    ('2026-05-21', '2026-05-21T02:55', 'W21', 'LOSS', 0.571),
    ('2026-05-21', '2026-05-21T05:50', 'W21', 'WIN',  0.584),
    ('2026-05-21', '2026-05-21T06:10', 'W21', 'WIN',  0.585),
    ('2026-05-21', '2026-05-21T06:15', 'W21', 'LOSS', 0.577),
    ('2026-05-21', '2026-05-21T07:20', 'W21', 'LOSS', 0.511),
    ('2026-05-21', '2026-05-21T13:50', 'W21', 'WIN',  0.187),
    ('2026-05-23', '2026-05-23T02:20', 'W21', 'LOSS', 0.559),
    ('2026-05-24', '2026-05-24T05:40', 'W21', 'LOSS', 0.760),
    ('2026-05-26', '2026-05-26T02:40', 'W22', 'WIN',  0.471),
    ('2026-05-26', '2026-05-26T02:45', 'W22', 'LOSS', 0.530),
    ('2026-05-26', '2026-05-26T12:10', 'W22', 'WIN',  0.448),
    ('2026-05-28', '2026-05-28T11:10', 'W22', 'LOSS', 0.608),
    ('2026-05-28', '2026-05-28T11:25', 'W22', 'WIN',  0.551),
    ('2026-05-28', '2026-05-28T11:25', 'W22', 'WIN',  0.551),  # duplicate ts, same record
    ('2026-05-29', '2026-05-29T18:50', 'W22', 'WIN',  0.375),
    ('2026-05-29', '2026-05-29T23:20', 'W22', 'WIN',  0.550),
]

# === CS vs OUTCOME ANALYSIS ===
print('=== COMPRESSION_SCORE vs OUTCOME (ETH TREND_DOWN) ===')
cs_outcome = [(cs, r) for _, _, _, r, cs in trades_data]
cs_outcome.sort()

print(f'{"cs":>6}  {"result":<5}  {"week":<4}')
for cs, result in cs_outcome:
    week = [w for _, _, w, r, c in trades_data if c==cs and r==result][0]
    print(f'{cs:6.3f}  {result:<5}  {week:<4}')

print()
print('cs < 0.50:')
low = [(cs,r) for cs,r in cs_outcome if cs < 0.50]
low_wins = sum(1 for cs,r in low if r=='WIN')
print(f'  n={len(low)}  WR={low_wins/len(low)*100:.0f}%  ({low_wins}W/{len(low)-low_wins}L)')

print('cs 0.50-0.60:')
mid = [(cs,r) for cs,r in cs_outcome if 0.50 <= cs < 0.60]
mid_wins = sum(1 for cs,r in mid if r=='WIN')
print(f'  n={len(mid)}  WR={mid_wins/len(mid)*100:.0f}%  ({mid_wins}W/{len(mid)-mid_wins}L)')

print('cs >= 0.60:')
high = [(cs,r) for cs,r in cs_outcome if cs >= 0.60]
high_wins = sum(1 for cs,r in high if r=='WIN')
print(f'  n={len(high)}  WR={high_wins/len(high)*100:.0f}%  ({high_wins}W/{len(high)-high_wins}L)')

print()
print('=== W21 vs W22 CS DISTRIBUTION ===')
w21_cs = [cs for _, _, w, _, cs in trades_data if w=='W21']
w22_cs = [cs for _, _, w, _, cs in trades_data if w=='W22']
print(f'W21 avg cs={sum(w21_cs)/len(w21_cs):.3f}  n_high(>=0.60)={sum(1 for c in w21_cs if c>=0.60)}  n_low(<0.50)={sum(1 for c in w21_cs if c<0.50)}')
print(f'W22 avg cs={sum(w22_cs)/len(w22_cs):.3f}  n_high(>=0.60)={sum(1 for c in w22_cs if c>=0.60)}  n_low(<0.50)={sum(1 for c in w22_cs if c<0.50)}')

# === BTC STATE AT TRADE TIME ===
print()
print('=== BTC STATE AT TRADE TIME ===')

def parse_record(line):
    try: return json.loads(line)
    except: return None

by_date = {}
for date, ts_prefix, week, result, eth_cs in trades_data:
    by_date.setdefault(date, []).append((ts_prefix, week, result, eth_cs))

print(f'{"trade_ts":<18} {"wk":<4} {"R":<5} {"ETH_cs":>7} {"BTC_regime":<16} {"BTC_cs":>7} {"BTC_vs":>7}')
print('-' * 75)

for date in sorted(by_date):
    path = f'{log_dir}/{date}.jsonl'
    if not os.path.exists(path):
        continue

    btc_records = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            r = parse_record(line.strip())
            if not r: continue
            ts = r.get('timestamp_utc', '')
            payload = r.get('payload', r)
            asset = payload.get('asset', '') or r.get('asset', '')
            regime = payload.get('market_regime', '') or r.get('market_regime', '')
            cs = payload.get('compression_score')
            vs = payload.get('volatility_score')
            if cs is None: cs = r.get('compression_score')
            if vs is None: vs = r.get('volatility_score')
            if asset == 'BTC' and regime:
                btc_records.append({'ts': ts[:16], 'regime': regime, 'cs': cs, 'vs': vs})

    for ts_prefix, week, result, eth_cs in by_date[date]:
        target = ts_prefix[:16]
        closest = None
        min_diff = float('inf')
        for rec in btc_records:
            rec_ts = rec['ts'][:16]
            if rec_ts[:10] == target[:10]:
                diff = abs(int(rec_ts[11:13])*60 + int(rec_ts[14:16]) -
                           int(target[11:13])*60 - int(target[14:16]))
                if diff < min_diff:
                    min_diff = diff
                    closest = rec

        if closest:
            cs_str = f'{closest["cs"]:.3f}' if closest["cs"] is not None else '   N/A'
            vs_str = f'{closest["vs"]:.3f}' if closest["vs"] is not None else '   N/A'
            print(f'{ts_prefix:<18} {week:<4} {result:<5} {eth_cs:7.3f} {closest["regime"]:<16} {cs_str:>7} {vs_str:>7}')
        else:
            print(f'{ts_prefix:<18} {week:<4} {result:<5} {eth_cs:7.3f} {"NO BTC DATA":<16}')
