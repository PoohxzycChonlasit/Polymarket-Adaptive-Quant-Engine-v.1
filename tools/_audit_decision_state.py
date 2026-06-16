"""Extract BTC/ETH state from decision_log near each TREND_DOWN trade entry time."""
import sys, json, csv, os
sys.stdout.reconfigure(encoding='utf-8')

# Trade entries we need context for: (date, entry_ts_prefix, week, result)
trades = [
    ('2026-05-19', '2026-05-19T09:50', 'W21', 'WIN'),
    ('2026-05-19', '2026-05-19T11:40', 'W21', 'LOSS'),
    ('2026-05-19', '2026-05-19T14:35', 'W21', 'WIN'),
    ('2026-05-21', '2026-05-21T02:55', 'W21', 'LOSS'),
    ('2026-05-21', '2026-05-21T05:50', 'W21', 'WIN'),
    ('2026-05-21', '2026-05-21T06:10', 'W21', 'WIN'),
    ('2026-05-21', '2026-05-21T06:15', 'W21', 'LOSS'),
    ('2026-05-21', '2026-05-21T07:20', 'W21', 'LOSS'),
    ('2026-05-21', '2026-05-21T13:50', 'W21', 'WIN'),
    ('2026-05-23', '2026-05-23T02:20', 'W21', 'LOSS'),
    ('2026-05-24', '2026-05-24T05:40', 'W21', 'LOSS'),
    ('2026-05-26', '2026-05-26T02:40', 'W22', 'WIN'),
    ('2026-05-26', '2026-05-26T02:45', 'W22', 'LOSS'),
    ('2026-05-26', '2026-05-26T12:10', 'W22', 'WIN'),
    ('2026-05-28', '2026-05-28T11:10', 'W22', 'LOSS'),
    ('2026-05-28', '2026-05-28T11:25', 'W22', 'WIN'),
    ('2026-05-29', '2026-05-29T18:50', 'W22', 'WIN'),
    ('2026-05-29', '2026-05-29T23:20', 'W22', 'WIN'),
]

log_dir = 'runtime/quant_data/decision_log'

def parse_record(line):
    try:
        return json.loads(line)
    except:
        return None

# For each trade, find the closest ETH decision_log record by timestamp
results = []

by_date = {}
for date, ts_prefix, week, result in trades:
    by_date.setdefault(date, []).append((ts_prefix, week, result))

for date, trade_list in sorted(by_date.items()):
    path = f'{log_dir}/{date}.jsonl'
    if not os.path.exists(path):
        for ts_prefix, week, result in trade_list:
            results.append((ts_prefix, week, result, None))
        continue

    # Read full file and collect ETH records near trade times
    eth_records = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            r = parse_record(line.strip())
            if not r:
                continue
            ts = r.get('timestamp_utc', '')
            asset = r.get('payload', {}).get('asset', '') or r.get('asset', '')
            payload = r.get('payload', r)

            # Try different payload structures
            regime = payload.get('market_regime', '')
            cs = payload.get('compression_score')
            vs = payload.get('volatility_score')
            ts_val = payload.get('trend_strength') or payload.get('trend_score')

            if not regime and 'market_regime' in r:
                regime = r['market_regime']
            if cs is None and 'compression_score' in r:
                cs = r['compression_score']
            if vs is None and 'volatility_score' in r:
                vs = r['volatility_score']

            # Only ETH records with regime info
            if asset == 'ETH' and regime:
                eth_records.append({
                    'ts': ts[:16],
                    'regime': regime,
                    'cs': cs,
                    'vs': vs,
                    'ts_val': ts_val,
                })

    for ts_prefix, week, result in trade_list:
        # Find closest record to trade entry time
        target = ts_prefix[:16]
        closest = None
        min_diff = float('inf')
        for rec in eth_records:
            rec_ts = rec['ts'][:16]
            # Simple string comparison for same-day timestamps
            if rec_ts[:10] == target[:10]:
                diff = abs(int(rec_ts[11:13])*60 + int(rec_ts[14:16]) -
                           int(target[11:13])*60 - int(target[14:16]))
                if diff < min_diff:
                    min_diff = diff
                    closest = rec
        results.append((ts_prefix, week, result, closest, min_diff if closest else None))

print(f'{"trade_ts":<18} {"wk":<4} {"R":<5} {"regime":<16} {"cs":>5} {"vs":>5} {"ts":>5} {"delta_min":>10}')
print('-'*75)
for item in results:
    ts, week, result, rec, diff = item if len(item)==5 else (*item, None)
    if rec:
        cs_str = f'{rec["cs"]:.3f}' if rec['cs'] is not None else '  N/A'
        vs_str = f'{rec["vs"]:.3f}' if rec['vs'] is not None else '  N/A'
        ts_str = f'{rec["ts_val"]:.3f}' if rec['ts_val'] is not None else '  N/A'
        print(f'{ts:<18} {week:<4} {result:<5} {rec["regime"]:<16} {cs_str:>5} {vs_str:>5} {ts_str:>5} {diff:>8}min')
    else:
        print(f'{ts:<18} {week:<4} {result:<5} {"NO DATA":<16}')
