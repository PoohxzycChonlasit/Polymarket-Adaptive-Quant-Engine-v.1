from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings
from crypto_scalper.config import write_freqtrade_config
from utils.logger import get_logger, setup_logger


@dataclass(slots=True)
class DashboardExportPaths:
    summary_path: Path
    equity_curve_path: Path
    trades_path: Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Freqtrade backtesting or hyperopt for PolyTrade Bot.")
    parser.add_argument(
        "--mode",
        choices=["backtest", "hyperopt"],
        default="backtest",
        help="Execution mode.",
    )
    parser.add_argument(
        "--timerange",
        default="20250101-",
        help="Freqtrade timerange value, for example 20250101-20250301.",
    )
    parser.add_argument(
        "--strategy",
        default="My5mScalper",
        help="Strategy class name to run.",
    )
    parser.add_argument(
        "--spaces",
        default="buy sell roi stoploss trailing",
        help="Hyperopt spaces to use when --mode hyperopt.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=100,
        help="Hyperopt epochs to run when --mode hyperopt.",
    )
    parser.add_argument(
        "--config-output",
        default="crypto_scalper/backtest_results/freqtrade_backtest_config.json",
        help="Path to the generated Freqtrade config file.",
    )
    parser.add_argument(
        "--dashboard-output",
        default="runtime",
        help="Directory used by the dashboard for normalized artifacts.",
    )
    parser.add_argument(
        "--summary-json",
        default="",
        help="Optional path to a backtest summary JSON file to normalize into dashboard format.",
    )
    parser.add_argument(
        "--equity-csv",
        default="",
        help="Optional path to an equity curve CSV file to normalize into dashboard format.",
    )
    parser.add_argument(
        "--trades-csv",
        default="",
        help="Optional path to a trades CSV file to normalize into dashboard format.",
    )
    parser.add_argument(
        "--sample-dashboard-data",
        action="store_true",
        help="Write sample dashboard artifacts without running Freqtrade.",
    )
    return parser


def build_backtest_command(config_path: Path, strategy: str, timerange: str) -> list[str]:
    return [
        "freqtrade",
        "backtesting",
        "--config",
        str(config_path),
        "--strategy",
        strategy,
        "--timeframe",
        "5m",
        "--timerange",
        timerange,
    ]


def build_hyperopt_command(
    config_path: Path,
    strategy: str,
    timerange: str,
    spaces: str,
    epochs: int,
) -> list[str]:
    return [
        "freqtrade",
        "hyperopt",
        "--config",
        str(config_path),
        "--strategy",
        strategy,
        "--timeframe",
        "5m",
        "--timerange",
        timerange,
        "--spaces",
        spaces,
        "--epochs",
        str(epochs),
    ]


def run_command(command: Sequence[str]) -> int:
    logger = get_logger(__name__)
    logger.info("Running command: %s", " ".join(command))
    completed = subprocess.run(command, check=False)
    logger.info("Command exited with code %s", completed.returncode)
    return completed.returncode


def build_dashboard_paths(output_dir: Path) -> DashboardExportPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    return DashboardExportPaths(
        summary_path=output_dir / "backtest_summary.json",
        equity_curve_path=output_dir / "equity_curve.csv",
        trades_path=output_dir / "trades.csv",
    )


def export_sample_dashboard_artifacts(output_dir: Path) -> None:
    logger = get_logger(__name__)
    paths = build_dashboard_paths(output_dir)

    summary = {
        "starting_balance": 10_000,
        "ending_balance": 10_720,
        "total_trades": 24,
        "win_rate": 62.5,
        "profit_factor": 1.84,
        "max_drawdown_pct": 4.2,
        "total_profit_pct": 7.2,
    }
    equity_curve = pd.DataFrame(
        [
            {"timestamp": "2026-01-01 00:00:00", "equity": 10_000, "drawdown_pct": 0.0},
            {"timestamp": "2026-01-07 00:00:00", "equity": 10_260, "drawdown_pct": -0.9},
            {"timestamp": "2026-01-14 00:00:00", "equity": 10_420, "drawdown_pct": -0.5},
            {"timestamp": "2026-01-21 00:00:00", "equity": 10_180, "drawdown_pct": -2.8},
            {"timestamp": "2026-01-28 00:00:00", "equity": 10_720, "drawdown_pct": -0.2},
        ]
    )
    trades = pd.DataFrame(
        [
            {"pair": "BTC/USDT", "side": "long", "profit_pct": 1.8, "duration_min": 35, "result": "win"},
            {"pair": "ETH/USDT", "side": "long", "profit_pct": -1.2, "duration_min": 22, "result": "loss"},
            {"pair": "SOL/USDT", "side": "long", "profit_pct": 2.4, "duration_min": 41, "result": "win"},
            {"pair": "BTC/USDT", "side": "long", "profit_pct": 1.1, "duration_min": 28, "result": "win"},
        ]
    )

    paths.summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    equity_curve.to_csv(paths.equity_curve_path, index=False)
    trades.to_csv(paths.trades_path, index=False)
    logger.info("Sample dashboard artifacts exported to %s", output_dir.as_posix())


def normalize_dashboard_artifacts(
    output_dir: Path,
    summary_json: str,
    equity_csv: str,
    trades_csv: str,
) -> None:
    logger = get_logger(__name__)
    paths = build_dashboard_paths(output_dir)

    if summary_json:
        summary_source = Path(summary_json)
        summary_payload = json.loads(summary_source.read_text(encoding="utf-8"))
        if isinstance(summary_payload, dict):
            numeric_summary: dict[str, float | int] = {}
            for key, value in summary_payload.items():
                if isinstance(value, (int, float)):
                    numeric_summary[str(key)] = value
            paths.summary_path.write_text(json.dumps(numeric_summary, indent=2), encoding="utf-8")
            logger.info("Normalized summary JSON into %s", paths.summary_path.as_posix())

    if equity_csv:
        equity_frame = pd.read_csv(Path(equity_csv))
        equity_frame.to_csv(paths.equity_curve_path, index=False)
        logger.info("Normalized equity CSV into %s", paths.equity_curve_path.as_posix())

    if trades_csv:
        trades_frame = pd.read_csv(Path(trades_csv))
        trades_frame.to_csv(paths.trades_path, index=False)
        logger.info("Normalized trades CSV into %s", paths.trades_path.as_posix())


def main() -> int:
    args = build_parser().parse_args()
    settings = get_settings()
    setup_logger(settings.log_level, settings.log_dir)
    dashboard_output = Path(args.dashboard_output)

    if args.sample_dashboard_data:
        export_sample_dashboard_artifacts(dashboard_output)
        return 0

    config_path = write_freqtrade_config(
        path=Path(args.config_output),
        settings=settings,
        dry_run=True,
    )

    if args.mode == "hyperopt":
        command = build_hyperopt_command(
            config_path=config_path,
            strategy=args.strategy,
            timerange=args.timerange,
            spaces=args.spaces,
            epochs=args.epochs,
        )
    else:
        command = build_backtest_command(
            config_path=config_path,
            strategy=args.strategy,
            timerange=args.timerange,
        )

    exit_code = run_command(command)
    normalize_dashboard_artifacts(
        output_dir=dashboard_output,
        summary_json=args.summary_json,
        equity_csv=args.equity_csv,
        trades_csv=args.trades_csv,
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
