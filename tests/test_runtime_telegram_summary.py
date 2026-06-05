"""Tests for the periodic runtime Telegram summary activation."""
from __future__ import annotations

import pytest

from utils.telegram_alerts import TelegramAlertLayer


class FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send_message(self, message: str, **_metadata) -> None:
        self.messages.append(message)


def _make_layer(now_val: float = 0.0) -> tuple[TelegramAlertLayer, FakeNotifier]:
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=300, now=lambda: now_val)
    return layer, notifier


def test_runtime_heartbeat_renders_status_header() -> None:
    layer, notifier = _make_layer()
    result = layer.notify_summary(
        "",
        dedup_key="runtime_status",
        run_id="abc123",
        uptime="0h01m",
        cycles=5,
        trade_opens=2,
        trade_closes=1,
        exceptions=0,
        mode="PAPER",
        risk_mode="NORMAL",
        heartbeat_age="3s",
        regime="COMPRESSION",
    )
    assert result.sent
    msg = notifier.messages[0]
    assert "STATUS | P3" in msg
    assert "Runtime heartbeat" in msg
    assert "━━━━━━━━━━━━━━" in msg


def test_runtime_heartbeat_includes_required_fields() -> None:
    layer, notifier = _make_layer()
    layer.notify_summary(
        "",
        dedup_key="runtime_status",
        run_id="run-xyz-001",
        uptime="1h30m",
        cycles=42,
        trade_opens=7,
        trade_closes=5,
        exceptions=2,
        mode="PAPER",
        risk_mode="MICRO_RECOVERY",
        heartbeat_age="12s",
        regime="SIDEWAY",
    )
    msg = notifier.messages[0]
    assert "Up: 1h30m" in msg
    assert "Cycles: 42" in msg
    assert "Opens: 7" in msg
    assert "Closes: 5" in msg
    assert "Exc: 2" in msg
    assert "Risk: MICRO_RECOVERY" in msg
    assert "Regime: SIDEWAY" in msg
    assert "Heartbeat: 12s" in msg
    assert "Periodic runtime status" in msg
    assert "No action required" in msg


def test_runtime_heartbeat_excludes_forbidden_fields() -> None:
    layer, notifier = _make_layer()
    layer.notify_summary(
        "",
        dedup_key="runtime_status",
        uptime="0h05m",
        cycles=10,
        trade_opens=0,
        trade_closes=0,
        exceptions=0,
        mode="PAPER",
        risk_mode="NORMAL",
        heartbeat_age="5s",
        regime="n/a",
    )
    msg = notifier.messages[0]
    for forbidden in ("EV", "probability", "confidence", "Signal PnL", "TP/SL", "position", "wallet"):
        assert forbidden.lower() not in msg.lower(), f"Forbidden field present: {forbidden!r}"


def test_runtime_heartbeat_run_id_truncated_at_14_chars() -> None:
    layer, notifier = _make_layer()
    long_run_id = "abcdefghijklmnopqrstuvwxyz"
    layer.notify_summary(
        "",
        dedup_key="runtime_status",
        run_id=long_run_id,
        uptime="0h01m",
        cycles=1,
        trade_opens=0,
        trade_closes=0,
        exceptions=0,
        mode="PAPER",
        risk_mode="NORMAL",
        heartbeat_age="1s",
        regime="n/a",
    )
    msg = notifier.messages[0]
    # The Run: display line must show truncated (14-char) run_id.
    # _ref_line may still show the full id at the bottom — that's OK.
    run_line = next(line for line in msg.splitlines() if line.startswith("Run:"))
    assert long_run_id[:14] in run_line
    assert long_run_id[14:] not in run_line


def test_cooldown_limits_runtime_summary_to_one_per_interval() -> None:
    now = [0.0]
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=3600, now=lambda: now[0])

    def _send_summary() -> None:
        layer.notify_summary(
            "",
            dedup_key="runtime_status",
            uptime="0h01m",
            cycles=1,
            trade_opens=0,
            trade_closes=0,
            exceptions=0,
            mode="PAPER",
            risk_mode="NORMAL",
            heartbeat_age="1s",
            regime="n/a",
        )

    _send_summary()
    assert len(notifier.messages) == 1

    # Many rapid-fire calls within the cooldown window must not send again.
    for _ in range(10):
        now[0] += 60
        _send_summary()

    assert len(notifier.messages) == 1, "Cooldown should suppress all subsequent sends within the interval"

    # After cooldown expires, the next call sends.
    now[0] += 3601
    _send_summary()
    assert len(notifier.messages) == 2


def test_legacy_daily_digest_unaffected_when_uptime_absent() -> None:
    layer, notifier = _make_layer()
    layer.notify_summary(
        "",
        dedup_key="auto_redeem_cycle",
        trades=5,
        tp=3,
        sl=2,
        signal_pnl="+$0.012",
        mode="paper",
    )
    msg = notifier.messages[0]
    assert "DAILY DIGEST | P3" in msg
    assert "Evidence summary" in msg
    assert "TP/SL" in msg
    assert "STATUS | P3" not in msg


def test_auto_redeem_and_runtime_cooldowns_are_independent() -> None:
    now = [0.0]
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=3600, now=lambda: now[0])

    layer.notify_summary("", dedup_key="runtime_status", uptime="0h01m", cycles=1,
                         trade_opens=0, trade_closes=0, exceptions=0, mode="PAPER",
                         risk_mode="NORMAL", heartbeat_age="1s", regime="n/a")

    # auto_redeem key is a different cooldown bucket — must send independently
    layer.notify_summary("Auto-Redeem claimed $1.00", dedup_key="auto_redeem_cycle", mode="paper")

    # Both sends must go through — independent cooldown buckets.
    assert len(notifier.messages) == 2
    assert "STATUS | P3" in notifier.messages[0]
    # auto_redeem_cycle has no `uptime` — renders DAILY DIGEST template.
    assert "DAILY DIGEST | P3" in notifier.messages[1]
