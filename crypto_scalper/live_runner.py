from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings
from crypto_scalper.config import write_freqtrade_config
from utils.logger import get_logger, setup_logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PolyTrade Bot crypto scalper in dry-run or live mode.")
    parser.add_argument(
        "--mode",
        choices=["dry-run", "live"],
        default="dry-run",
        help="Execution mode for Freqtrade.",
    )
    parser.add_argument(
        "--strategy",
        default="My5mScalper",
        help="Strategy class name to run.",
    )
    parser.add_argument(
        "--config-output",
        default="runtime/freqtrade_runner_config.json",
        help="Path to the generated Freqtrade config file.",
    )
    return parser


def build_trade_command(config_path: Path, strategy: str) -> list[str]:
    return [
        "freqtrade",
        "trade",
        "--config",
        str(config_path),
        "--strategy",
        strategy,
    ]


def run_command(command: Sequence[str]) -> int:
    logger = get_logger(__name__)
    logger.info("Running command: %s", " ".join(command))
    completed = subprocess.run(command, check=False)
    logger.info("Command exited with code %s", completed.returncode)
    return completed.returncode


def main() -> int:
    args = build_parser().parse_args()
    settings = get_settings()
    setup_logger(settings.log_level, settings.log_dir)

    dry_run = args.mode == "dry-run"
    logger = get_logger(__name__)
    logger.info("Starting crypto scalper runner | mode=%s | exchange=%s", args.mode, settings.crypto_exchange)

    config_path = write_freqtrade_config(
        path=Path(args.config_output),
        settings=settings,
        dry_run=dry_run,
    )
    command = build_trade_command(config_path=config_path, strategy=args.strategy)
    return run_command(command)


if __name__ == "__main__":
    raise SystemExit(main())
