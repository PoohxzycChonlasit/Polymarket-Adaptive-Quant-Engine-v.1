"""Tests for polymarket/observability/trader_path_truth.py.

Verifies pure helper output, edge cases, and golden equivalence between the
PolymarketTrader wrappers and the extracted helper functions.
"""
from __future__ import annotations

from datetime import UTC, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from polymarket.observability.trader_path_truth import (
    path_truth_elapsed_seconds,
    path_truth_lifecycle_phase,
    path_truth_session_hour_utc,
)
from polymarket.trader import PolymarketTrader


def _pos(entry_time: object = None) -> object:
    return SimpleNamespace(entry_time=entry_time)


def _now(hour: int = 12, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2026, 6, 1, hour, minute, second, tzinfo=UTC)


def _trader_stub(lifecycle_phase: str = "", epoch_start_ts: object = None) -> MagicMock:
    """Return a minimal trader stub with _path_truth_metadata returning controlled data."""
    trader = MagicMock(spec=PolymarketTrader)
    trader._path_truth_metadata.return_value = {
        "lifecycle_phase": lifecycle_phase,
        "epoch_start_ts": epoch_start_ts,
    }
    return trader


# ---------------------------------------------------------------------------
# path_truth_elapsed_seconds
# ---------------------------------------------------------------------------


def test_elapsed_seconds_valid_entry_time() -> None:
    pos = _pos("2026-06-01T12:00:00+00:00")
    now = _now(12, 1, 30)  # 90 seconds later
    assert path_truth_elapsed_seconds(pos, now) == 90


def test_elapsed_seconds_zero_when_now_equals_entry() -> None:
    pos = _pos("2026-06-01T12:00:00+00:00")
    now = _now(12, 0, 0)
    assert path_truth_elapsed_seconds(pos, now) == 0


def test_elapsed_seconds_clamps_to_zero_for_future_entry() -> None:
    pos = _pos("2026-06-01T13:00:00+00:00")
    now = _now(12, 0, 0)  # now is before entry
    assert path_truth_elapsed_seconds(pos, now) == 0


def test_elapsed_seconds_none_on_invalid_entry_time() -> None:
    assert path_truth_elapsed_seconds(_pos(None), _now()) is None
    assert path_truth_elapsed_seconds(_pos(""), _now()) is None
    assert path_truth_elapsed_seconds(_pos("not-a-date"), _now()) is None


def test_elapsed_seconds_no_entry_time_attr() -> None:
    pos = SimpleNamespace()  # no entry_time attribute
    assert path_truth_elapsed_seconds(pos, _now()) is None


def test_elapsed_seconds_naive_now_treated_as_utc() -> None:
    pos = _pos("2026-06-01T12:00:00+00:00")
    now_naive = datetime(2026, 6, 1, 12, 1, 0)  # no tzinfo
    result = path_truth_elapsed_seconds(pos, now_naive)
    assert result == 60


# ---------------------------------------------------------------------------
# path_truth_session_hour_utc
# ---------------------------------------------------------------------------


def test_session_hour_utc_from_entry_time() -> None:
    pos = _pos("2026-06-01T15:30:00+00:00")
    result = path_truth_session_hour_utc(pos, _now(20, 0, 0))
    assert result == 15  # uses entry_time hour, not now


def test_session_hour_utc_fallback_to_now() -> None:
    pos = _pos(None)
    result = path_truth_session_hour_utc(pos, _now(9, 0, 0))
    assert result == 9


def test_session_hour_utc_fallback_invalid_entry_time() -> None:
    pos = _pos("bad-ts")
    result = path_truth_session_hour_utc(pos, _now(7, 30, 0))
    assert result == 7


def test_session_hour_utc_naive_now_treated_as_utc() -> None:
    pos = _pos(None)
    now_naive = datetime(2026, 6, 1, 14, 0, 0)
    result = path_truth_session_hour_utc(pos, now_naive)
    assert result == 14


def test_session_hour_utc_boundary_midnight() -> None:
    pos = _pos("2026-06-01T00:00:00+00:00")
    result = path_truth_session_hour_utc(pos, _now())
    assert result == 0


def test_session_hour_utc_boundary_23() -> None:
    pos = _pos(None)
    result = path_truth_session_hour_utc(pos, _now(23, 59, 59))
    assert result == 23


# ---------------------------------------------------------------------------
# path_truth_lifecycle_phase
# ---------------------------------------------------------------------------


def test_lifecycle_phase_explicit_in_metadata() -> None:
    trader = _trader_stub(lifecycle_phase="OPENING_SCAN")
    result = path_truth_lifecycle_phase(trader, _pos(), _now())
    assert result == "OPENING_SCAN"


def test_lifecycle_phase_explicit_takes_precedence_over_epoch() -> None:
    trader = _trader_stub(lifecycle_phase="FINAL_DERISK", epoch_start_ts=1000)
    result = path_truth_lifecycle_phase(trader, _pos(), _now())
    assert result == "FINAL_DERISK"


def test_lifecycle_phase_none_on_missing_epoch() -> None:
    trader = _trader_stub(lifecycle_phase="", epoch_start_ts=None)
    result = path_truth_lifecycle_phase(trader, _pos(), _now())
    assert result is None


def test_lifecycle_phase_none_on_zero_epoch() -> None:
    trader = _trader_stub(lifecycle_phase="", epoch_start_ts=0)
    result = path_truth_lifecycle_phase(trader, _pos(), _now())
    assert result is None


def test_lifecycle_phase_computed_opening_scan() -> None:
    now = datetime(2026, 6, 1, 12, 0, 20, tzinfo=UTC)
    epoch_start = int(now.timestamp()) - 10  # 10s into 300s epoch → 290s remaining
    trader = _trader_stub(lifecycle_phase="", epoch_start_ts=epoch_start)
    result = path_truth_lifecycle_phase(trader, _pos(), now)
    assert result == "OPENING_SCAN"


def test_lifecycle_phase_computed_active_inventory() -> None:
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    epoch_start = int(now.timestamp()) - 100  # 100s in → 200s remaining
    trader = _trader_stub(lifecycle_phase="", epoch_start_ts=epoch_start)
    result = path_truth_lifecycle_phase(trader, _pos(), now)
    assert result == "ACTIVE_INVENTORY_TRADING"


def test_lifecycle_phase_computed_profit_management() -> None:
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    epoch_start = int(now.timestamp()) - 250  # 250s in → 50s remaining
    trader = _trader_stub(lifecycle_phase="", epoch_start_ts=epoch_start)
    result = path_truth_lifecycle_phase(trader, _pos(), now)
    assert result == "PROFIT_MANAGEMENT"


def test_lifecycle_phase_computed_final_derisk() -> None:
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    epoch_start = int(now.timestamp()) - 280  # 280s in → 20s remaining
    trader = _trader_stub(lifecycle_phase="", epoch_start_ts=epoch_start)
    result = path_truth_lifecycle_phase(trader, _pos(), now)
    assert result == "FINAL_DERISK"


def test_lifecycle_phase_closed_when_past_epoch() -> None:
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    epoch_start = int(now.timestamp()) - 400  # 400s in → -100s remaining → closed
    trader = _trader_stub(lifecycle_phase="", epoch_start_ts=epoch_start)
    result = path_truth_lifecycle_phase(trader, _pos(), now)
    assert result == "CLOSED_OR_UNSAFE"


# ---------------------------------------------------------------------------
# Golden equivalence: wrapper == extracted function
# ---------------------------------------------------------------------------


def _trader_instance() -> PolymarketTrader:
    return PolymarketTrader.__new__(PolymarketTrader)


def test_golden_elapsed_seconds_valid() -> None:
    pos = _pos("2026-06-01T10:00:00+00:00")
    now = _now(10, 5, 0)
    trader = _trader_instance()
    assert trader._path_truth_elapsed_seconds(pos, now) == path_truth_elapsed_seconds(pos, now)


def test_golden_elapsed_seconds_invalid() -> None:
    for entry in (None, "", "bad"):
        pos = _pos(entry)
        now = _now()
        trader = _trader_instance()
        assert trader._path_truth_elapsed_seconds(pos, now) == path_truth_elapsed_seconds(pos, now)


def test_golden_session_hour_utc() -> None:
    for entry in ("2026-06-01T08:30:00+00:00", None, "invalid"):
        pos = _pos(entry)
        now = _now(16, 0, 0)
        trader = _trader_instance()
        assert trader._path_truth_session_hour_utc(pos, now) == path_truth_session_hour_utc(pos, now)


def test_golden_lifecycle_phase_explicit() -> None:
    trader_real = _trader_instance()

    class _FakePos:
        metadata: dict = {"lifecycle_phase": "FINAL_DERISK", "epoch_start_ts": None}

    trader_real._path_truth_metadata = lambda pos: pos.metadata
    pos = _FakePos()
    now = _now()
    wrapper = trader_real._path_truth_lifecycle_phase(pos, now)
    extracted = path_truth_lifecycle_phase(trader_real, pos, now)
    assert wrapper == extracted == "FINAL_DERISK"


def test_golden_lifecycle_phase_computed() -> None:
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    # 20s into 300s epoch → seconds_remaining=280 → seconds_since_open=20 → OPENING_SCAN
    epoch_start = int(now.timestamp()) - 20

    trader_real = _trader_instance()

    class _FakePos:
        metadata: dict = {"lifecycle_phase": "", "epoch_start_ts": epoch_start}

    trader_real._path_truth_metadata = lambda pos: pos.metadata
    pos = _FakePos()
    wrapper = trader_real._path_truth_lifecycle_phase(pos, now)
    extracted = path_truth_lifecycle_phase(trader_real, pos, now)
    assert wrapper == extracted
    assert wrapper == "OPENING_SCAN"
