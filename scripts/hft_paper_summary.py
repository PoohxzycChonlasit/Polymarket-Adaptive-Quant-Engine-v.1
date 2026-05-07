from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_TRADES_CSV = Path("runtime/hft_trades.csv")


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _pct(numerator: float, denominator: float) -> float:
    return numerator / denominator * 100.0 if denominator else 0.0


def load_trades(path: Path = DEFAULT_TRADES_CSV) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_summary(path: Path = DEFAULT_TRADES_CSV) -> dict[str, Any]:
    rows = load_trades(path)
    trades = len(rows)
    wins = sum(1 for row in rows if row.get("outcome") == "win")
    losses = sum(1 for row in rows if row.get("outcome") == "loss")
    pnl_values = [_as_float(row.get("pnl_usd")) for row in rows]
    total_pnl = sum(pnl_values)
    avg_pnl = total_pnl / trades if trades else 0.0

    bankroll_series = [_as_float(row.get("bankroll_after"), math.nan) for row in rows]
    bankroll_series = [v for v in bankroll_series if not math.isnan(v)]
    final_bankroll = bankroll_series[-1] if bankroll_series else 0.0

    peak = bankroll_series[0] if bankroll_series else 0.0
    max_drawdown = 0.0
    for value in bankroll_series:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - value) / peak * 100.0)

    by_tier: dict[str, dict[str, Any]] = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl_usd": 0.0})
    by_side: dict[str, dict[str, Any]] = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl_usd": 0.0})
    for row in rows:
        pnl = _as_float(row.get("pnl_usd"))
        won = row.get("outcome") == "win"
        tier = row.get("bet_tier") or "UNKNOWN"
        side = row.get("side") or "UNKNOWN"
        for bucket, key in ((by_tier, tier), (by_side, side)):
            bucket[key]["trades"] += 1
            bucket[key]["wins"] += int(won)
            bucket[key]["pnl_usd"] += pnl

    def finalize_bucket(bucket: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {
            key: {
                "trades": value["trades"],
                "wins": value["wins"],
                "win_rate_pct": round(_pct(value["wins"], value["trades"]), 2),
                "pnl_usd": round(value["pnl_usd"], 4),
            }
            for key, value in sorted(bucket.items())
        }

    first_ts = rows[0].get("timestamp", "") if rows else ""
    last_ts = rows[-1].get("timestamp", "") if rows else ""

    return {
        "source": str(path),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "first_trade_at": first_ts,
        "last_trade_at": last_ts,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(_pct(wins, trades), 2),
        "total_pnl_usd": round(total_pnl, 4),
        "avg_pnl_usd": round(avg_pnl, 4),
        "final_bankroll": round(final_bankroll, 4),
        "max_drawdown_pct": round(max_drawdown, 2),
        "by_tier": finalize_bucket(by_tier),
        "by_side": finalize_bucket(by_side),
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# HFT Paper Trade Summary",
        "",
        f"- Source: `{summary['source']}`",
        f"- Generated: `{summary['generated_at']}`",
        f"- First trade: `{summary['first_trade_at'] or 'N/A'}`",
        f"- Last trade: `{summary['last_trade_at'] or 'N/A'}`",
        "",
        "## Overall",
        "",
        f"- Trades: {summary['trades']}",
        f"- Wins/Losses: {summary['wins']} / {summary['losses']}",
        f"- Win rate: {summary['win_rate_pct']:.2f}%",
        f"- Total PnL: ${summary['total_pnl_usd']:+.4f}",
        f"- Avg PnL/trade: ${summary['avg_pnl_usd']:+.4f}",
        f"- Final bankroll: ${summary['final_bankroll']:.4f}",
        f"- Max drawdown: {summary['max_drawdown_pct']:.2f}%",
        "",
        "## By Tier",
        "",
        "| Tier | Trades | Wins | Win Rate | PnL |",
        "|------|--------|------|----------|-----|",
    ]
    for tier, data in summary["by_tier"].items():
        lines.append(
            f"| {tier} | {data['trades']} | {data['wins']} | "
            f"{data['win_rate_pct']:.2f}% | ${data['pnl_usd']:+.4f} |"
        )
    lines.extend([
        "",
        "## By Side",
        "",
        "| Side | Trades | Wins | Win Rate | PnL |",
        "|------|--------|------|----------|-----|",
    ])
    for side, data in summary["by_side"].items():
        lines.append(
            f"| {side} | {data['trades']} | {data['wins']} | "
            f"{data['win_rate_pct']:.2f}% | ${data['pnl_usd']:+.4f} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_summary(path: Path = DEFAULT_TRADES_CSV, output_dir: Path = Path("runtime")) -> dict[str, Any]:
    summary = build_summary(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"hft_summary_{stamp}.json"
    md_path = output_dir / f"hft_summary_{stamp}.md"
    latest_md = output_dir / "hft_summary_latest.md"

    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    markdown = render_markdown(summary)
    md_path.write_text(markdown, encoding="utf-8")
    latest_md.write_text(markdown, encoding="utf-8")

    summary["json_path"] = str(json_path)
    summary["markdown_path"] = str(md_path)
    summary["latest_markdown_path"] = str(latest_md)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize HFT paper trade CSV results.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_TRADES_CSV)
    parser.add_argument("--output-dir", type=Path, default=Path("runtime"))
    args = parser.parse_args()

    summary = write_summary(args.csv, args.output_dir)
    print(render_markdown(summary))
    print(f"JSON: {summary['json_path']}")
    print(f"Markdown: {summary['markdown_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
