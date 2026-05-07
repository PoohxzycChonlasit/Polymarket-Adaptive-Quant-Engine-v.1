"""
ai_analyst.py — Offline AI Quant Analyst
=========================================
Reads today's scan log & backtest summary, then uses Claude AI to generate
actionable parameter tuning suggestions. Sends results to Telegram + saves
as a markdown report in research/daily/.

Usage:
    python scripts/ai_analyst.py          # Analyse today's log
    python scripts/ai_analyst.py --date 2026-04-25   # Specific date
    python scripts/ai_analyst.py --mock   # Dry-run (no Claude API call)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings

# ── Constants ────────────────────────────────────────────────────────────────
TZ_TH          = ZoneInfo("Asia/Bangkok")
LOG_BASE       = Path("runtime/realtime_logs")
BACKTEST_BASE  = Path("backtest_results/polymarket_5m")
RESEARCH_DIR   = Path("research/daily")

ANALYST_SYSTEM_PROMPT = """You are the Offline AI Quant Analyst for PolyTrade Crypto Scalper.

Your role is to analyze the daily execution logs and backtest results of a deterministic, 
high-frequency quant trading bot operating on Polymarket 5-minute binary markets.

Core Responsibilities:
1. Identify performance patterns (e.g., Which asset performs best? Which strategy fails most?).
2. Analyze the P&L, Win Rate, and trade frequency of the day.
3. Suggest CONCRETE adjustments to Quant Engine parameters in `config/settings.py`
   (e.g., `sniper_zscore_threshold`, `trend_adx_threshold`, `atr_multiplier`, `strategy_score_threshold`).

Rules:
- NEVER suggest adding AI back into the real-time execution loop.
- Focus on math, statistics, and parameter tuning only.
- Be concise but specific. Propose actionable parameter changes with exact values.
- Highlight anomalies (e.g., thin liquidity sessions, unusually large loss streaks).

Output Format (STRICT - Markdown):
# 🧠 Daily AI Analyst Insights — {date}

## 📊 Performance Overview
<2-3 sentence summary of the day>

## ✅ Strengths
- <bullet point>

## ⚠️ Weaknesses
- <bullet point>

## 🛠️ Recommended Parameter Tweaks
| Parameter | Current | Suggested | Reasoning |
|-----------|---------|-----------|-----------|
| `param_name` | value | value | reason |

## 🔮 Tomorrow's Outlook
<Short market regime prediction and what strategy should dominate>"""


# ── Data loaders ─────────────────────────────────────────────────────────────

def _load_scan_log(date_str: str) -> list[dict]:
    path = LOG_BASE / date_str / "scan_log.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_latest_backtest() -> dict:
    path = BACKTEST_BASE / "latest_metrics.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _summarize_scan_log(rows: list[dict]) -> dict:
    """Turn raw scan log rows into a compact stats dict for the AI."""
    if not rows:
        return {"error": "No scan log data found for this date."}

    trades      = [r for r in rows if r.get("order_status") == "paper"]
    skips       = [r for r in rows if r.get("signal") == "SKIP"]
    yes_trades  = [r for r in trades if r.get("signal") == "YES"]
    no_trades   = [r for r in trades if r.get("signal") == "NO"]

    # Asset breakdown
    asset_counts: dict[str, int] = {}
    for r in trades:
        a = r.get("asset", "?")
        asset_counts[a] = asset_counts.get(a, 0) + 1

    # Strategy breakdown
    strategy_counts: dict[str, int] = {}
    for r in trades:
        s = r.get("strategy", "unknown")
        strategy_counts[s] = strategy_counts.get(s, 0) + 1

    # Score distribution
    scores = []
    for r in trades:
        try:
            scores.append(float(r.get("score", 0)))
        except ValueError:
            pass
    avg_score = sum(scores) / len(scores) if scores else 0.0
    min_score = min(scores) if scores else 0.0
    max_score = max(scores) if scores else 0.0

    # Bankroll info
    bankroll_start = 0.0
    bankroll_end   = 0.0
    try:
        bankroll_start = float(rows[0].get("bankroll", 0))
        bankroll_end   = float(rows[-1].get("bankroll", 0))
    except (ValueError, TypeError):
        pass

    pnl_usd = bankroll_end - bankroll_start

    return {
        "date":               rows[0].get("timestamp_utc", "?")[:10] if rows else "?",
        "total_scans":        len(rows),
        "total_trades":       len(trades),
        "total_skips":        len(skips),
        "yes_trades":         len(yes_trades),
        "no_trades":          len(no_trades),
        "asset_breakdown":    asset_counts,
        "strategy_breakdown": strategy_counts,
        "avg_signal_score":   round(avg_score, 3),
        "min_signal_score":   round(min_score, 3),
        "max_signal_score":   round(max_score, 3),
        "bankroll_start":     round(bankroll_start, 4),
        "bankroll_end":       round(bankroll_end, 4),
        "pnl_usd":            round(pnl_usd, 4),
        "skip_rate_pct":      round(len(skips) / max(len(rows), 1) * 100, 1),
    }


# ── Claude AI caller ─────────────────────────────────────────────────────────

def _call_claude(scan_summary: dict, backtest_metrics: dict, settings_snapshot: dict, date_str: str) -> str:
    """Call Claude API and return the analyst markdown report."""
    try:
        import anthropic
    except ImportError:
        return "❌ `anthropic` package not installed. Run: `pip install anthropic`"

    s = get_settings()
    api_key = s.claude_api_key.get_secret_value() if hasattr(s, "claude_api_key") else ""
    if not api_key:
        return "❌ CLAUDE_API_KEY not set in .env file."

    client = anthropic.Anthropic(api_key=api_key)

    user_message = f"""
Analyse today's PolyTrade Bot execution for **{date_str}**.

## Today's Scan Log Summary
```json
{json.dumps(scan_summary, indent=2)}
```

## Latest Backtest Metrics (Validated Strategy)
```json
{json.dumps(backtest_metrics, indent=2)}
```

## Current Active Settings (Key Parameters)
```json
{json.dumps(settings_snapshot, indent=2)}
```

Please provide your analysis following the output format exactly.
"""
    try:
        resp = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            system=ANALYST_SYSTEM_PROMPT.replace("{date}", date_str),
            messages=[{"role": "user", "content": user_message}],
        )
        return resp.content[0].text
    except Exception as e:
        return f"❌ Claude API error: {e}"


def _mock_report(date_str: str, scan_summary: dict) -> str:
    """Return a realistic mock report for dry-run testing."""
    n_trades = scan_summary.get("total_trades", 0)
    pnl      = scan_summary.get("pnl_usd", 0.0)
    return f"""# 🧠 Daily AI Analyst Insights — {date_str}

## 📊 Performance Overview
The bot executed {n_trades} paper trades today with a net P&L of **${pnl:+.4f}**.
This is a MOCK report generated without a Claude API call (`--mock` flag was used).

## ✅ Strengths
- Sniper strategy is detecting Z-Score extremes effectively.
- Low skip rate suggests good market activity.

## ⚠️ Weaknesses
- Trade frequency may be insufficient for the $50 bankroll to compound.
- ADX threshold of 20.0 may be admitting weak trend signals.

## 🛠️ Recommended Parameter Tweaks
| Parameter | Current | Suggested | Reasoning |
|-----------|---------|-----------|-----------|
| `trend_adx_threshold` | 20.0 | 22.0 | Slightly tighter to filter weak trends |
| `sniper_zscore_threshold` | 2.0 | 1.9 | Catch slightly less extreme but still valid entries |

## 🔮 Tomorrow's Outlook
Monitor Reversion strategy performance. If MACD histograms are aligning with BB touches, Reversion + Sniper combo should dominate.
"""


# ── Telegram sender ───────────────────────────────────────────────────────────

def _send_telegram(text: str) -> bool:
    """Send the AI analyst report via Telegram (chunked if >4096 chars)."""
    import httpx
    s        = get_settings()
    bot_tok  = s.telegram_bot_token.get_secret_value() if hasattr(s, "telegram_bot_token") else ""
    chat_id  = str(s.telegram_chat_id) if hasattr(s, "telegram_chat_id") else ""

    if not bot_tok or not chat_id:
        print("[Telegram] No bot token or chat_id — skipping notification.")
        return False

    url      = f"https://api.telegram.org/bot{bot_tok}/sendMessage"
    max_len  = 4000
    chunks   = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    ok       = True

    for chunk in chunks:
        try:
            r = httpx.post(url, json={"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"}, timeout=15)
            r.raise_for_status()
        except Exception as e:
            print(f"[Telegram] Send failed: {e}")
            ok = False

    return ok


# ── Report saver ──────────────────────────────────────────────────────────────

def _save_report(date_str: str, report_md: str) -> Path:
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out = RESEARCH_DIR / f"{date_str}_ai_analysis.md"
    out.write_text(report_md, encoding="utf-8")
    return out


# ── Settings snapshot ─────────────────────────────────────────────────────────

def _get_settings_snapshot() -> dict:
    """Capture key quant parameters from current settings for AI context."""
    s = get_settings()
    return {
        "strategy_score_threshold":  s.strategy_score_threshold,
        "sniper_zscore_threshold":   s.sniper_zscore_threshold,
        "sniper_max_entry_price":    s.sniper_max_entry_price,
        "trend_adx_threshold":       s.trend_adx_threshold,
        "trend_ema_fast":            s.trend_ema_fast,
        "trend_ema_slow":            s.trend_ema_slow,
        "atr_multiplier":            s.atr_multiplier,
        "atr_mom_lower_floor":       s.atr_mom_lower_floor,
        "atr_mom_upper_cap":         s.atr_mom_upper_cap,
        "htf_ema_period":            s.htf_ema_period,
        "htf_ema_penalty":           s.htf_ema_penalty,
        "bankroll_floor":            s.bankroll_floor,
        "active_strategy":           s.active_strategy,
    }


# ── CLI Entrypoint ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="PolyTrade Offline AI Quant Analyst")
    parser.add_argument("--date",  default=None,  help="Date to analyse (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--mock",  action="store_true", help="Dry-run: skip Claude API, print mock report.")
    parser.add_argument("--no-telegram", action="store_true", help="Skip Telegram notification.")
    args = parser.parse_args()

    date_str = args.date or datetime.now(TZ_TH).strftime("%Y-%m-%d")
    print(f"[AI Analyst] Analysing date: {date_str} {'(MOCK)' if args.mock else ''}")

    # 1. Load data
    scan_rows       = _load_scan_log(date_str)
    scan_summary    = _summarize_scan_log(scan_rows)
    backtest_data   = _load_latest_backtest()
    settings_snap   = _get_settings_snapshot()

    print(f"[AI Analyst] Scan rows loaded: {len(scan_rows)} | Trades: {scan_summary.get('total_trades', 0)}")

    # 2. Generate report
    if args.mock:
        report = _mock_report(date_str, scan_summary)
    else:
        print("[AI Analyst] Calling Claude API...")
        report = _call_claude(scan_summary, backtest_data, settings_snap, date_str)

    # 3. Save to research/daily/
    out_path = _save_report(date_str, report)
    print(f"[AI Analyst] Report saved -> {out_path}")

    # 4. Send to Telegram
    if not args.no_telegram:
        ok = _send_telegram(report)
        print(f"[AI Analyst] Telegram: {'OK - sent' if ok else 'WARN - failed'}")

    # 5. Print to console (force UTF-8 for Windows terminals that default to cp874)
    import io
    out = "\n" + "=" * 60 + "\n" + report + "\n" + "=" * 60 + "\n"
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
