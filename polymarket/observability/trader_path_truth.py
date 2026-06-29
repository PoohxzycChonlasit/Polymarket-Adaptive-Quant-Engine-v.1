"""Pure path-truth observability helpers extracted from PolymarketTrader.

All functions are free of self.* reads/writes. Functions that need to call
back into trader state accept ``trader: Any`` and delegate via method calls.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from polymarket.observability.trader_lifecycle_observability import (
    diagnostic_int,
    path_truth_parse_ts,
    phase2_lifecycle_phase,
)


def path_truth_elapsed_seconds(pos: Any, now: datetime | None = None) -> int | None:
    entry_dt = path_truth_parse_ts(getattr(pos, "entry_time", ""))
    if entry_dt is None:
        return None
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    current = current.astimezone(UTC)
    return max(0, int((current - entry_dt).total_seconds()))


def path_truth_session_hour_utc(pos: Any, now: datetime | None = None) -> int | None:
    entry_dt = path_truth_parse_ts(getattr(pos, "entry_time", ""))
    if entry_dt is not None:
        return int(entry_dt.hour)
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return int(current.astimezone(UTC).hour)


def path_truth_lifecycle_phase(trader: Any, pos: Any, now: datetime | None = None) -> str | None:
    metadata = trader._path_truth_metadata(pos)
    explicit = str(metadata.get("lifecycle_phase") or "").strip()
    if explicit:
        return explicit
    epoch_start = diagnostic_int(metadata.get("epoch_start_ts"))
    if epoch_start is None or epoch_start <= 0:
        return None
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    seconds_remaining = int(epoch_start + 300 - current.astimezone(UTC).timestamp())
    return phase2_lifecycle_phase(seconds_remaining)
