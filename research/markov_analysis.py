"""
markov_analysis.py
==================
Phase 1: Build Markov transition matrix from 90-day BTC candle data.

Momentum states (same formula as backtester_5m._compute_signal):
  momentum_pct = (candle_open - close_3_candles_ago) / close_3_candles_ago * 100

7 states:
  S0: mom > +1.00%        extreme up
  S1: +0.60% to +1.00%   strong up
  S2: +0.40% to +0.60%   moderate up  (current threshold boundary)
  S3: -0.40% to +0.40%   neutral      (currently skipped)
  S4: -0.60% to -0.40%   moderate down
  S5: -1.00% to -0.60%   strong down
  S6: < -1.00%            extreme down

Entry condition (from article):
  gap     = p_hat - market_price  >= 0.05
  persist = P[j_star][j_star]     >= 0.87
  Both must be true to enter.

Run:
  python research/markov_analysis.py
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx
import numpy as np
import pandas as pd

# ── State config ───────────────────────────────────────────────────────────────
STATE_LABELS = [
    "Extreme UP  > +1.00%",
    "Strong  UP  +0.60–1.00%",
    "Moderate UP +0.40–0.60%",
    "Neutral     -0.40–+0.40%",
    "Moderate DN -0.60–-0.40%",
    "Strong  DN  -1.00–-0.60%",
    "Extreme DN  < -1.00%",
]
N = 7
NO_STATES  = {0, 1, 2}   # up momentum → bet NO (mean reversion down)
YES_STATES = {4, 5, 6}   # down momentum → bet YES (mean reversion up)

BREAKEVEN  = 0.5102       # 51.02% breakeven at 2% Polymarket fee
MARKET_MID = 0.50         # Polymarket YES/NO entry price


# ── State classifier ───────────────────────────────────────────────────────────

def classify(mom: float) -> int:
    if   mom >  1.00: return 0
    elif mom >  0.60: return 1
    elif mom >  0.40: return 2
    elif mom >= -0.40: return 3
    elif mom >= -0.60: return 4
    elif mom >= -1.00: return 5
    else:              return 6


# ── Coinbase candle fetch (same as backtester_5m) ─────────────────────────────

def fetch_candles(days: int = 90) -> pd.DataFrame:
    url      = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    end_ts   = int(time.time())
    start_ts = end_ts - days * 86_400
    rows: list = []
    chunk_end = end_ts
    client = httpx.Client(
        timeout=httpx.Timeout(15.0),
        headers={"User-Agent": "PolyTradeBot-MarkovAnalysis/1.0"},
    )
    print(f"Fetching {days}d BTC-USD candles from Coinbase...")
    while chunk_end > start_ts:
        chunk_start = max(start_ts, chunk_end - 300 * 300)
        try:
            resp = client.get(url, params={
                "granularity": 300,
                "start": datetime.fromtimestamp(chunk_start, tz=timezone.utc).isoformat(),
                "end":   datetime.fromtimestamp(chunk_end,   tz=timezone.utc).isoformat(),
            })
            resp.raise_for_status()
            chunk = resp.json()
            if chunk:
                rows.extend(chunk)
        except Exception as e:
            print(f"  chunk error: {e}")
        chunk_end = chunk_start
        time.sleep(0.2)

    df = pd.DataFrame(rows, columns=["time", "low", "high", "open", "close", "volume"])
    df["time"] = df["time"].astype(int)
    df = (df.sort_values("time")
            .drop_duplicates("time")
            .reset_index(drop=True))
    df = df[(df["time"] >= start_ts) & (df["time"] <= end_ts)].reset_index(drop=True)
    print(f"  {len(df)} candles fetched\n")
    return df


# ── Momentum + state series ────────────────────────────────────────────────────

def build_states(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    price_now  = df["open"]
    price_3ago = df["close"].shift(3)
    mom    = (price_now - price_3ago) / price_3ago.replace(0, np.nan) * 100
    states = mom.dropna().apply(classify)
    return mom.dropna(), states


# ── Transition matrix ─────────────────────────────────────────────────────────

def build_matrix(states: pd.Series) -> np.ndarray:
    P = np.zeros((N, N))
    arr = states.values
    for i in range(len(arr) - 1):
        P[arr[i]][arr[i + 1]] += 1
    row_sums = P.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    return P / row_sums


# ── Win rates per state ────────────────────────────────────────────────────────

def compute_win_rates(df: pd.DataFrame, states: pd.Series) -> list[dict]:
    df = df.loc[states.index].reset_index(drop=True)
    states = states.reset_index(drop=True)

    # next candle: 1 = price up (YES wins), 0 = price down (NO wins)
    next_up = (df["close"].shift(-1) > df["open"].shift(-1)).astype(float)
    next_up.iloc[-1] = np.nan  # last candle has no next

    results = []
    for s in range(N):
        mask = (states == s) & next_up.notna()
        n    = mask.sum()
        if n == 0:
            results.append({"n": 0, "win_rate": np.nan, "bet": "SKIP"})
            continue
        outcomes = next_up[mask]
        if s in NO_STATES:
            wr = (outcomes == 0).sum() / n
            results.append({"n": int(n), "win_rate": float(wr), "bet": "NO"})
        elif s in YES_STATES:
            wr = (outcomes == 1).sum() / n
            results.append({"n": int(n), "win_rate": float(wr), "bet": "YES"})
        else:
            results.append({"n": int(n), "win_rate": np.nan, "bet": "SKIP"})
    return results


# ── Markov entry filter ────────────────────────────────────────────────────────

def entry_signal(P: np.ndarray, state: int,
                 tau: float = 0.87, eps: float = 0.05) -> dict:
    j_star  = int(np.argmax(P[state]))
    p_hat   = float(P[state][j_star])
    persist = float(P[j_star][j_star])
    gap     = p_hat - MARKET_MID
    return {
        "j_star":  j_star,
        "p_hat":   p_hat,
        "persist": persist,
        "gap":     gap,
        "enter":   gap >= eps and persist >= tau,
    }


# ── p_hat for counter-momentum (more meaningful for binary market) ─────────────

def counter_momentum_prob(P: np.ndarray, state: int) -> float:
    """Probability that price moves OPPOSITE to current momentum (our actual bet edge)."""
    if state in NO_STATES:
        # bet NO: win when price goes to neutral or down states next
        return float(P[state, 3:].sum())   # S3 + S4 + S5 + S6
    if state in YES_STATES:
        # bet YES: win when price goes to neutral or up states next
        return float(P[state, :4].sum())   # S0 + S1 + S2 + S3
    return np.nan


# ── Report ─────────────────────────────────────────────────────────────────────

def print_report(P: np.ndarray, win_rates: list[dict], states: pd.Series) -> None:
    SEP  = "=" * 88
    SEP2 = "-" * 88

    # ── State distribution ────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  STATE DISTRIBUTION  (90d BTC 5-min candles)")
    print(SEP2)
    for i, label in enumerate(STATE_LABELS):
        n   = (states == i).sum()
        pct = n / len(states) * 100
        bar = "█" * int(pct / 1.5)
        print(f"  S{i}  {label:<28}  {n:5d}  ({pct:5.1f}%)  {bar}")

    # ── Transition matrix ─────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  TRANSITION MATRIX  P[from → to]")
    print(SEP2)
    print(f"  {'':4}", end="")
    for j in range(N):
        print(f"    S{j}  ", end="")
    print(f"   {'DIAG':>6}   {'≥0.87':>5}")
    print(f"  {SEP2}")
    for i in range(N):
        print(f"  S{i}  ", end="")
        for j in range(N):
            v   = P[i][j]
            hl  = f"\033[92m{v:.3f}\033[0m" if (i == j and v >= 0.87) else \
                  f"\033[93m{v:.3f}\033[0m" if (i == j) else f"{v:.3f}"
            print(f"  {hl}  ", end="")
        diag = P[i][i]
        flag = "  ✅" if diag >= 0.87 else ""
        print(f"  {diag:6.3f}  {flag}")

    # ── Win rate + entry signals ──────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  WIN RATE PER STATE  +  MARKOV ENTRY  (tau=0.87, eps=0.05)")
    print(SEP2)
    print(f"  {'S':<2}  {'Label':<28}  {'Bet':>4}  {'N':>5}  "
          f"{'WinRate':>7}  {'p_hat(CM)':>9}  {'Gap':>6}  {'Persist':>7}  {'Signal':>8}")
    print(f"  {SEP2}")

    for i in range(N):
        wr   = win_rates[i]
        e    = entry_signal(P, i)
        cm   = counter_momentum_prob(P, i)
        gap  = (cm - MARKET_MID) if not np.isnan(cm) else np.nan

        wr_s  = f"{wr['win_rate']:.1%}" if not np.isnan(wr["win_rate"]) else "  —   "
        cm_s  = f"{cm:.3f}"             if not np.isnan(cm)             else "  —   "
        gap_s = f"{gap:+.3f}"           if not np.isnan(gap)            else "  —   "
        sig   = "✅ ENTER" if (not np.isnan(gap) and gap >= 0.05
                               and e["persist"] >= 0.87) else "— skip"
        pers  = f"{e['persist']:.3f}"

        print(f"  S{i}  {STATE_LABELS[i]:<28}  {wr['bet']:>4}  {wr['n']:>5}  "
              f"{wr_s:>7}  {cm_s:>9}  {gap_s:>6}  {pers:>7}  {sig:>8}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  SUMMARY  —  Current threshold vs Markov filter")
    print(SEP2)

    # Current: trade states 0,1,2,4,5,6 (any momentum > 0.40%)
    current_states = [i for i in range(N) if i != 3]
    current_n  = sum(win_rates[i]["n"] for i in current_states)
    current_wrs = [win_rates[i]["win_rate"] for i in current_states
                   if not np.isnan(win_rates[i]["win_rate"])]
    current_wr = np.mean(current_wrs) if current_wrs else np.nan

    # Markov: trade only where counter-momentum gap >= 0.05 AND persist >= 0.87
    markov_states = []
    for i in range(N):
        if i == 3:
            continue
        cm  = counter_momentum_prob(P, i)
        e   = entry_signal(P, i)
        if not np.isnan(cm) and (cm - MARKET_MID) >= 0.05 and e["persist"] >= 0.87:
            markov_states.append(i)

    markov_n  = sum(win_rates[i]["n"] for i in markov_states) if markov_states else 0
    markov_wrs = [win_rates[i]["win_rate"] for i in markov_states
                  if not np.isnan(win_rates[i]["win_rate"])]
    markov_wr = np.mean(markov_wrs) if markov_wrs else np.nan

    print(f"\n  Current (momentum threshold 0.40%)")
    print(f"    States traded  : {current_states}")
    print(f"    Total samples  : {current_n:,}")
    print(f"    Avg win rate   : {current_wr:.2%}  (breakeven: {BREAKEVEN:.2%})")
    print(f"    Edge per trade : {current_wr - BREAKEVEN:+.2%}")

    print(f"\n  Markov filter (counter-momentum gap≥0.05 AND persist≥0.87)")
    if markov_states:
        print(f"    States traded  : {markov_states}")
        print(f"    Total samples  : {markov_n:,}")
        print(f"    Avg win rate   : {markov_wr:.2%}  (breakeven: {BREAKEVEN:.2%})")
        print(f"    Edge per trade : {markov_wr - BREAKEVEN:+.2%}")
        trade_reduction = (1 - markov_n / max(current_n, 1)) * 100
        print(f"    Trade reduction: {trade_reduction:.0f}% fewer trades vs current")
    else:
        print(f"    No states trigger at tau=0.87, eps=0.05")
        print(f"    Relaxing parameters:")
        for tau, eps in [(0.80, 0.04), (0.75, 0.03), (0.70, 0.02)]:
            relaxed = []
            for i in range(N):
                if i == 3: continue
                cm = counter_momentum_prob(P, i)
                e  = entry_signal(P, i, tau=tau, eps=eps)
                if not np.isnan(cm) and (cm - MARKET_MID) >= eps and e["persist"] >= tau:
                    relaxed.append(i)
            if relaxed:
                r_wrs = [win_rates[i]["win_rate"] for i in relaxed
                          if not np.isnan(win_rates[i]["win_rate"])]
                r_wr  = np.mean(r_wrs) if r_wrs else np.nan
                print(f"      tau={tau}, eps={eps}: states {relaxed}  "
                      f"avg_wr={r_wr:.2%}  n={sum(win_rates[i]['n'] for i in relaxed):,}")

    print(f"\n{SEP}")
    print("  INTERPRETATION")
    print(SEP2)
    print("""
  The transition matrix shows HOW OFTEN each momentum state transitions to another.
  High diagonal = state tends to PERSIST (momentum continues).
  Low diagonal  = state tends to REVERT  (mean reversion likely).

  For counter-momentum trading:
    LOW diagonal in up-momentum states (S0/S1/S2) = price reverts → NO bets work
    LOW diagonal in down-momentum states (S4/S5/S6) = price reverts → YES bets work

  The Markov filter adds a second condition:
    The NEXT state must also be PERSISTENT (persist ≥ 0.87).
    This ensures we don't enter into chaotic/unpredictable transitions.

  Phase 2: If Markov filter improves win rate vs baseline → replace _compute_signal().
""")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    df            = fetch_candles(days=90)
    mom, states   = build_states(df)
    P             = build_matrix(states)
    win_rates     = compute_win_rates(df.loc[mom.index], states)
    print_report(P, win_rates, states)


if __name__ == "__main__":
    main()
