from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd
from pandas import DataFrame


LOGGER = logging.getLogger(__name__)

try:
    from freqtrade.strategy import IStrategy
except ImportError:  # pragma: no cover
    class IStrategy:  # type: ignore[override]
        minimal_roi: dict[str, float]
        stoploss: float
        trailing_stop: bool
        timeframe: str


class My5mScalper(IStrategy):
    timeframe: str = "5m"
    startup_candle_count: int = 50
    can_short: bool = False

    minimal_roi: dict[str, float] = {
        "0": 0.020,
        "10": 0.012,
        "20": 0.008,
        "40": 0.0,
    }
    stoploss: float = -0.02
    trailing_stop: bool = True
    trailing_stop_positive: float = 0.008
    trailing_stop_positive_offset: float = 0.015
    trailing_only_offset_is_reached: bool = True

    order_types: dict[str, str | bool] = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict[str, str]) -> DataFrame:
        pair = metadata.get("pair", "unknown")
        LOGGER.debug("Populating indicators for %s", pair)

        dataframe["ema_fast"] = dataframe["close"].ewm(span=9, adjust=False).mean()
        dataframe["ema_slow"] = dataframe["close"].ewm(span=21, adjust=False).mean()
        dataframe["volume_mean"] = dataframe["volume"].rolling(window=20).mean()

        delta = dataframe["close"].diff()
        gains = delta.clip(lower=0.0)
        losses = -delta.clip(upper=0.0)
        average_gain = gains.ewm(alpha=1 / 14, adjust=False).mean()
        average_loss = losses.ewm(alpha=1 / 14, adjust=False).mean()
        rs = average_gain / average_loss.replace(0.0, 1e-10)
        dataframe["rsi"] = 100 - (100 / (1 + rs))

        # Integrate Polymarket Mock Data
        mock_path = Path("crypto_scalper/backtest_results/polymarket_mock_data.csv")
        if mock_path.exists():
            try:
                pm_df = pd.read_csv(mock_path)
                pm_df["date"] = pd.to_datetime(pm_df["date"], utc=True)
                
                # Freqtrade provides the 'date' column. Use merge_asof for time-series alignment
                dataframe = pd.merge_asof(
                    dataframe.sort_values("date"), 
                    pm_df.sort_values("date"), 
                    on="date", 
                    direction="backward"
                )
                dataframe["polymarket_implied_probability"].fillna(0.5, inplace=True)
                LOGGER.debug("Loaded and merged Polymarket data successfully.")
            except Exception as e:
                LOGGER.warning("Could not merge Polymarket data: %s", e)
                dataframe["polymarket_implied_probability"] = 0.5
        else:
            dataframe["polymarket_implied_probability"] = 0.5

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict[str, str]) -> DataFrame:
        pair = metadata.get("pair", "unknown")
        LOGGER.debug("Populating entry trend for %s", pair)
        dataframe["enter_long"] = 0

        entry_condition = (
            (dataframe["ema_fast"] > dataframe["ema_slow"])
            & (dataframe["ema_fast"].shift(1) <= dataframe["ema_slow"].shift(1))
            & (dataframe["rsi"] > 45)
            & (dataframe["rsi"] < 70)
            & (dataframe["close"] > dataframe["ema_fast"])
            & (dataframe["volume"] > dataframe["volume_mean"])
            & (dataframe["volume"] > 0)
            & (dataframe["polymarket_implied_probability"] > 0.40) # Safety filter from Polymarket
        )

        dataframe.loc[entry_condition, "enter_long"] = 1
        dataframe.loc[entry_condition, "enter_tag"] = "rsi_ema_volume_long"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict[str, str]) -> DataFrame:
        pair = metadata.get("pair", "unknown")
        LOGGER.debug("Populating exit trend for %s", pair)
        dataframe["exit_long"] = 0

        exit_condition = (
            (dataframe["ema_fast"] < dataframe["ema_slow"])
            | (dataframe["rsi"] > 75)
            | (dataframe["close"] < dataframe["ema_slow"])
        )

        dataframe.loc[exit_condition, "exit_long"] = 1
        dataframe.loc[exit_condition, "exit_tag"] = "ema_loss_or_rsi_exhaustion"
        return dataframe
