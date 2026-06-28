"""
24/7 Opportunity Capture Audit
Analyzes decision logs for the last 6-12 hours to diagnose trade starvation.
READ ONLY — no runtime changes.
"""
import json, sys, os
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8')

LOG_DIR   = 'runtime/quant_data/decision_log'
DATES     = ['2026-06-06', '2026-06-05']
HOURS_BACK = 12   # analyze last 12 hours from latest timestamp seen

def ts_to_dt(ts):
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except:
        return None

# ── Pass 1: find latest timestamp in today's file ──────────────────────────
latest_ts = None
path_today = os.path.join(LOG_DIR, '2026-06-06.jsonl')
with open(path_today, encoding='utf-8', errors='replace') as f:
    for line in f:
        try:
            r = json.loads(line)
            ts = ts_to_dt(r.get('timestamp_utc', ''))
            if ts and (latest_ts is None or ts > latest_ts):
                latest_ts = ts
        except:
            pass

if latest_ts is None:
    print('ERROR: could not find timestamps in log.')
    sys.exit(1)

from datetime import timedelta
cutoff_12h = latest_ts - timedelta(hours=12)
cutoff_6h  = latest_ts - timedelta(hours=6)

print(f'Latest log timestamp : {latest_ts.strftime("%Y-%m-%d %H:%M UTC")}')
print(f'12-hour window start : {cutoff_12h.strftime("%Y-%m-%d %H:%M UTC")}')
print(f'6-hour window start  : {cutoff_6h.strftime("%Y-%m-%d %H:%M UTC")}')
print()

# ── Pass 2: full analysis ──────────────────────────────────────────────────
records_12h = []
records_6h  = []

for date in DATES:
    path = os.path.join(LOG_DIR, f'{date}.jsonl')
    if not os.path.exists(path):
        continue
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            try:
                r = json.loads(line)
            except:
                continue
            if r.get('event_type') != 'decision':
                continue
            ts = ts_to_dt(r.get('timestamp_utc', ''))
            if ts is None:
                continue
            if ts < cutoff_12h:
                continue
            p = r.get('payload', r)
            rec = {
                'ts':             ts,
                'asset':          p.get('asset', 'UNK'),
                'side':           p.get('side', p.get('selected_side', 'UNK')),
                'regime':         p.get('market_regime', 'UNK'),
                'lifecycle':      p.get('lifecycle_phase', p.get('canonical_entry_lifecycle_phase', 'UNK')),
                'block_reason':   p.get('candidate_block_reason', '') or '',
                'block_stage':    p.get('candidate_block_stage', '') or '',
                'probe_state':    p.get('admission_probe_state', '') or '',
                'skip_reason':    p.get('skip_reason', '') or '',
                'bankroll_mode':  p.get('bankroll_mode', '') or '',
                'confidence':     p.get('confidence', None),
                'ev_after_spread':p.get('ev_after_spread', None),
                'spread':         p.get('spread', None),
                'spread_limit':   p.get('spread_limit', None),
                'risk_plan_zero': p.get('risk_plan_zero_reason', '') or '',
                'order_size':     p.get('calculated_order_size', 0) or 0,
                'execution_intent': p.get('execution_intent', '') or '',
                'direction':      p.get('direction', '') or '',
                'seconds_since_open': p.get('seconds_since_open', None),
                'lifecycle_entered': p.get('lifecycle_phase_entered_at', '') or '',
                'delta_extreme':  p.get('delta_extreme', None),
                'max_trades_hit': p.get('max_daily_trades_hit', None),
                'cooldown_active':p.get('cooldown_active', None),
                'best_seen_state':p.get('best_seen_state', '') or '',
                'admission_probe_reason': p.get('admission_probe_reason', '') or '',
            }
            records_12h.append(rec)
            if ts >= cutoff_6h:
                records_6h.append(rec)

print(f'Decision records in 12h window: {len(records_12h):,}')
print(f'Decision records in 6h window : {len(records_6h):,}')
print()

def analyze(records, window_label):
    n = len(records)
    if n == 0:
        print(f'No records in {window_label}')
        return

    print(f'{"="*70}')
    print(f'WINDOW: {window_label}  (n={n:,} decision events)')
    print(f'{"="*70}')

    # ── 1. Asset / regime breakdown ────────────────────────────────────────
    asset_cnt  = Counter(r['asset']   for r in records)
    regime_cnt = Counter(r['regime']  for r in records)
    print('\n--- Asset distribution ---')
    for k, v in asset_cnt.most_common():
        print(f'  {k:<12} {v:>7,}  ({v/n*100:.1f}%)')

    print('\n--- Regime distribution ---')
    for k, v in regime_cnt.most_common():
        print(f'  {k:<20} {v:>7,}  ({v/n*100:.1f}%)')

    # ── 2. Probe state / execution outcome ────────────────────────────────
    probe_cnt = Counter(r['probe_state'] for r in records)
    print('\n--- Admission probe state (what decision was reached) ---')
    for k, v in probe_cnt.most_common():
        print(f'  {k:<40} {v:>7,}  ({v/n*100:.1f}%)')

    executable = sum(1 for r in records if r['probe_state'] == 'EXECUTABLE_EVALUATED'
                     and r['order_size'] > 0)
    skipped    = sum(1 for r in records if r['block_reason'] or r['skip_reason'])
    print(f'\n  → Candidates with actual order size > 0 : {executable:,}')
    print(f'  → Candidates with any block/skip reason : {skipped:,}')

    # ── 3. Block reasons ──────────────────────────────────────────────────
    block_cnt = Counter(r['block_reason'] for r in records if r['block_reason'])
    print(f'\n--- Candidate block reasons (total blocked: {sum(block_cnt.values()):,}) ---')
    for k, v in block_cnt.most_common(20):
        print(f'  {k:<45} {v:>7,}')

    # ── 4. Skip reasons ───────────────────────────────────────────────────
    skip_cnt = Counter(r['skip_reason'] for r in records if r['skip_reason'])
    if skip_cnt:
        print(f'\n--- Skip reasons (total: {sum(skip_cnt.values()):,}) ---')
        for k, v in skip_cnt.most_common(20):
            print(f'  {k:<45} {v:>7,}')

    # ── 5. Risk-plan-zero reasons ─────────────────────────────────────────
    rpz_cnt = Counter(r['risk_plan_zero'] for r in records if r['risk_plan_zero'])
    if rpz_cnt:
        print(f'\n--- Risk plan zero reasons (total: {sum(rpz_cnt.values()):,}) ---')
        for k, v in rpz_cnt.most_common(15):
            print(f'  {k:<45} {v:>7,}')

    # ── 6. Bankroll mode ──────────────────────────────────────────────────
    bm_cnt = Counter(r['bankroll_mode'] for r in records if r['bankroll_mode'])
    print(f'\n--- Bankroll mode ---')
    for k, v in bm_cnt.most_common():
        print(f'  {k:<35} {v:>7,}  ({v/n*100:.1f}%)')

    # ── 7. Key specific blocker counts ────────────────────────────────────
    def cnt_block(keyword):
        return sum(1 for r in records if keyword.lower() in (
            r['block_reason']+r['skip_reason']+r['risk_plan_zero']+r['probe_state']
        ).lower())

    micro_blocked   = sum(1 for r in records if 'micro' in (r['bankroll_mode']+r['block_reason']).lower()
                          and (r['block_reason'] or r['order_size'] == 0))
    delta_blocked   = sum(1 for r in records if 'delta' in r['block_reason'].lower())
    conf_blocked    = sum(1 for r in records if 'confidence' in (r['block_reason']+r['skip_reason']).lower())
    time_blocked    = sum(1 for r in records if 'time' in (r['block_reason']+r['skip_reason']).lower()
                          and 'unsafe' in (r['block_reason']+r['skip_reason']).lower())
    budget_blocked  = sum(1 for r in records if any(x in (r['block_reason']+r['skip_reason']+r['risk_plan_zero']).lower()
                          for x in ('max_trade', 'budget', 'cooldown', 'risk_budget', 'daily_limit')))
    spread_blocked  = sum(1 for r in records if 'spread' in r['block_reason'].lower())
    rpz_blocked     = sum(1 for r in records if r['risk_plan_zero'])

    print(f'\n--- Specific blocker counts ---')
    print(f'  MICRO_RECOVERY / MICRO mode constraint  : {micro_blocked:>7,}')
    print(f'  delta_extreme                           : {delta_blocked:>7,}')
    print(f'  confidence threshold                    : {conf_blocked:>7,}')
    print(f'  time_unsafe                             : {time_blocked:>7,}')
    print(f'  max_trades / cooldown / risk_budget     : {budget_blocked:>7,}')
    print(f'  spread too wide                         : {spread_blocked:>7,}')
    print(f'  risk_plan_zero (any reason)             : {rpz_blocked:>7,}')

    # ── 8. OPENING_SCAN coverage ──────────────────────────────────────────
    os_ready = [r for r in records if 'OPENING' in r['lifecycle'].upper()]
    os_blocked_late = [r for r in os_ready
                       if r['seconds_since_open'] is not None
                       and isinstance(r['seconds_since_open'], (int, float))
                       and r['seconds_since_open'] > 35]
    print(f'\n--- OPENING_SCAN coverage ---')
    print(f'  Total OPENING_SCAN events               : {len(os_ready):>7,}')
    print(f'  Evaluated AFTER 35s cutoff (late eval)  : {len(os_blocked_late):>7,}')
    if os_ready:
        print(f'  Late eval rate                          : {len(os_blocked_late)/len(os_ready)*100:>6.1f}%')

    # ── 9. High-quality missed — candidates with good signal but still blocked
    high_q = []
    for r in records:
        if not r['block_reason'] and not r['skip_reason']:
            continue
        conf = r['confidence']
        ev   = r['ev_after_spread']
        if conf is None or ev is None:
            continue
        try:
            if float(conf) >= 0.65 and float(ev) > 0:
                high_q.append(r)
        except:
            pass
    print(f'\n--- High-quality candidates blocked (conf>=0.65, EV>0) ---')
    print(f'  Count                                   : {len(high_q):>7,}')
    if high_q:
        hq_block = Counter(r['block_reason'] or r['skip_reason'] or r['risk_plan_zero'] for r in high_q)
        for k, v in hq_block.most_common(10):
            print(f'  {k:<45} {v:>7,}')

    # ── 10. Lifecycle phase of all records ────────────────────────────────
    lc_cnt = Counter(r['lifecycle'] for r in records)
    print(f'\n--- Lifecycle phase distribution ---')
    for k, v in lc_cnt.most_common(10):
        print(f'  {k:<40} {v:>7,}  ({v/n*100:.1f}%)')

    # ── 11. Execution direction / intent ─────────────────────────────────
    ei_cnt = Counter(r['execution_intent'] for r in records if r['execution_intent'])
    if ei_cnt:
        print(f'\n--- Execution intent ---')
        for k, v in ei_cnt.most_common(10):
            print(f'  {k:<40} {v:>7,}')

    # ── 12. Confidence distribution for BLOCKED candidates ───────────────
    conf_vals = []
    for r in records:
        if r['block_reason'] or r['skip_reason']:
            try:
                c = float(r['confidence'])
                conf_vals.append(c)
            except:
                pass
    if conf_vals:
        conf_vals.sort()
        n_c = len(conf_vals)
        p50 = conf_vals[n_c//2]
        p75 = conf_vals[int(n_c*0.75)]
        p90 = conf_vals[int(n_c*0.90)]
        low = sum(1 for c in conf_vals if c < 0.60)
        mid = sum(1 for c in conf_vals if 0.60 <= c < 0.70)
        hi  = sum(1 for c in conf_vals if c >= 0.70)
        print(f'\n--- Confidence of BLOCKED candidates ---')
        print(f'  n with confidence value             : {n_c:>7,}')
        print(f'  p50={p50:.3f}  p75={p75:.3f}  p90={p90:.3f}')
        print(f'  < 0.60 (low)                        : {low:>7,}  ({low/n_c*100:.0f}%)')
        print(f'  0.60–0.70 (mid)                     : {mid:>7,}  ({mid/n_c*100:.0f}%)')
        print(f'  >= 0.70 (high)                      : {hi:>7,}  ({hi/n_c*100:.0f}%)')

    # ── 13. Hourly activity breakdown ─────────────────────────────────────
    hour_cnt = Counter(r['ts'].hour for r in records)
    hour_exe = Counter(r['ts'].hour for r in records if r['order_size'] > 0)
    print(f'\n--- Hourly decision event count (UTC) ---')
    for h in sorted(hour_cnt.keys()):
        bar = '#' * min(40, hour_cnt[h]//200)
        exe = hour_exe.get(h, 0)
        print(f'  {h:02d}h  {hour_cnt[h]:>6,} decisions  {exe:>4} executable  {bar}')

    print()

# Run for both windows
analyze(records_12h, 'Last 12 hours')
print()
analyze(records_6h,  'Last 6 hours')
