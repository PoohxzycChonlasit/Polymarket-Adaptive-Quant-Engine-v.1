"""Tests for the periodic runtime Telegram summary activation."""
from __future__ import annotations

import pytest

from utils.telegram_alerts import TelegramAlertLayer


class FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send_message(self, message: str, **_metadata) -> None:
        self.messages.append(message)


class AsyncFailureNotifier:
    supports_async_telegram_telemetry = True

    def __init__(self) -> None:
        self.messages: list[str] = []

    def send_message(self, message: str, **metadata) -> None:
        self.messages.append(message)
        metadata["telemetry_emit"](
            {
                "timestamp": "2026-06-17T00:00:00Z",
                "event_type": "telegram_send_failure",
                "route": metadata["route"],
                "run_id": metadata["run_id"],
                "source_event_id": metadata["source_event_id"],
                "cooldown_key": metadata["cooldown_key"],
                "exception_class": "ConnectionError",
                "failure_stage": "http_post",
            }
        )


class AsyncSuccessNotifier:
    supports_async_telegram_telemetry = True

    def __init__(self) -> None:
        self.messages: list[str] = []

    def send_message(self, message: str, **metadata) -> None:
        self.messages.append(message)
        metadata["telemetry_emit"](
            {
                "timestamp": "2026-06-17T00:00:00Z",
                "event_type": "telegram_send_success",
                "route": metadata["route"],
                "run_id": metadata["run_id"],
                "source_event_id": metadata["source_event_id"],
                "cooldown_key": metadata["cooldown_key"],
                "http_status": 200,
                "telegram_ok": True,
            }
        )


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
    assert "ALIVE" in msg
    assert "PAPER" in msg
    assert " | " in msg


def test_runtime_status_delivery_failure_uses_short_retry_not_hourly_cooldown() -> None:
    now = [0.0]
    events: list[dict[str, object]] = []
    notifier = AsyncFailureNotifier()
    layer = TelegramAlertLayer(
        notifier,
        cooldown_seconds=300,
        summary_interval_minutes=60,
        now=lambda: now[0],
        telemetry_emit=events.append,
        run_id="run-heartbeat-retry",
    )

    first = layer.notify_summary("", **_runtime_status_kwargs())
    assert first.sent
    assert len(notifier.messages) == 1

    now[0] += 30
    suppressed = layer.notify_summary("", **_runtime_status_kwargs())
    assert suppressed.suppressed
    assert suppressed.reason == "heartbeat_retry_backoff"
    assert len(notifier.messages) == 1

    now[0] += 31
    retry = layer.notify_summary("", **_runtime_status_kwargs())
    assert retry.sent
    assert len(notifier.messages) == 2

    event_types = [event["event_type"] for event in events]
    assert "heartbeat_generated" in event_types
    assert "heartbeat_send_failed" in event_types
    assert "heartbeat_retry_scheduled" in event_types
    assert "heartbeat_suppressed" in event_types
    retry_event = next(event for event in events if event["event_type"] == "heartbeat_retry_scheduled")
    assert retry_event["retry_cooldown_seconds"] == 60


def test_runtime_status_delivery_success_sets_hourly_cooldown() -> None:
    now = [0.0]
    events: list[dict[str, object]] = []
    notifier = AsyncSuccessNotifier()
    layer = TelegramAlertLayer(
        notifier,
        cooldown_seconds=300,
        summary_interval_minutes=60,
        now=lambda: now[0],
        telemetry_emit=events.append,
        run_id="run-heartbeat-success",
    )

    first = layer.notify_summary("", **_runtime_status_kwargs())
    assert first.sent
    assert len(notifier.messages) == 1

    now[0] += 120
    suppressed = layer.notify_summary("", **_runtime_status_kwargs())
    assert suppressed.suppressed
    assert suppressed.reason == "cooldown"
    assert len(notifier.messages) == 1

    assert any(event["event_type"] == "heartbeat_delivered" for event in events)


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
    assert "Up:0h01m" not in msg  # verify correct uptime is used
    assert "Up:1h30m" in msg
    assert "Cycle:42" in msg
    assert "Open:7" in msg
    assert "Closed:5" in msg


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


def test_runtime_heartbeat_run_id_truncated_at_8_chars() -> None:
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
    run_line = next(line for line in msg.splitlines() if "Run:" in line)
    assert long_run_id[:8] in run_line
    assert long_run_id[8:] not in run_line


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
    assert "DAY" in msg
    assert "Trades:5" in msg
    assert "W:3 L:2" in msg
    assert "PnL" in msg


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
    assert "ALIVE" in notifier.messages[0]
    assert "DAY" in notifier.messages[1]


# ---------------------------------------------------------------------------
# PATCH_TG_HEARTBEAT_V2 — startup bypass tests
# ---------------------------------------------------------------------------

def _runtime_status_kwargs() -> dict:
    return dict(
        dedup_key="runtime_status",
        run_id="test-run-hb",
        uptime="0h00m",
        cycles=1,
        trade_opens=0,
        trade_closes=0,
        exceptions=0,
        mode="PAPER",
        risk_mode="NORMAL",
        heartbeat_age="1s",
        regime="n/a",
    )


def test_startup_heartbeat_bypasses_cooldown_on_first_call() -> None:
    """First notify_summary(dedup_key='runtime_status') must send even if cooldown
    is artificially pre-seeded, guaranteeing one heartbeat per run."""
    now = [0.0]
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=3600, now=lambda: now[0])
    # Pre-seed last_sent to simulate "cooldown already active" (e.g. from a prior send
    # that populated _last_sent 10 seconds ago in the same instance).
    layer._last_sent["summary:runtime_status"] = now[0] - 10.0

    result = layer.notify_summary("", **_runtime_status_kwargs())

    assert result.sent, "Startup heartbeat must bypass the cooldown on first call"
    assert len(notifier.messages) == 1
    assert layer._startup_heartbeat_sent is True
    assert "ALIVE" in notifier.messages[0]


def test_second_runtime_status_is_cooldown_gated_after_startup_heartbeat() -> None:
    """After the startup bypass fires once, all subsequent runtime_status calls
    must use the normal hourly cooldown — no second immediate send."""
    now = [0.0]
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=3600, now=lambda: now[0])

    def _send() -> None:
        layer.notify_summary("", **_runtime_status_kwargs())

    _send()  # first call — startup bypass fires
    assert len(notifier.messages) == 1, "Startup send must succeed"

    # Many calls within the cooldown window must all be suppressed
    for _ in range(20):
        now[0] += 60
        _send()
    assert len(notifier.messages) == 1, "All calls within cooldown must be suppressed"


def test_runtime_status_sends_after_cooldown_expires() -> None:
    """After startup bypass + cooldown expiry, the hourly heartbeat fires normally."""
    now = [0.0]
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=3600, now=lambda: now[0])

    def _send() -> None:
        layer.notify_summary("", **_runtime_status_kwargs())

    _send()  # startup bypass
    assert len(notifier.messages) == 1

    now[0] += 3601  # advance past the 1-hour cooldown
    _send()  # hourly heartbeat
    assert len(notifier.messages) == 2, "Hourly heartbeat must fire after cooldown expires"


def test_non_runtime_summary_unchanged_by_startup_bypass() -> None:
    """Non-runtime_status summaries (e.g. auto_redeem_cycle) must not be affected
    by the startup bypass flag at all — they still use the standard cooldown."""
    now = [0.0]
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=3600, now=lambda: now[0])

    # Non-runtime_status summary — no bypass should apply
    r1 = layer.notify_summary("Auto-Redeem claimed $1.00", dedup_key="auto_redeem_cycle", mode="paper")
    assert r1.sent

    # Second call for the same non-runtime key must be cooldown-gated
    r2 = layer.notify_summary("Auto-Redeem claimed $1.00", dedup_key="auto_redeem_cycle", mode="paper")
    assert r2.suppressed, "Non-runtime summary must remain cooldown-gated"
    assert len(notifier.messages) == 1

    # Startup bypass flag must remain False — non-runtime call must not prime it
    assert layer._startup_heartbeat_sent is False


def test_startup_heartbeat_message_is_compact() -> None:
    """The startup heartbeat message must be compact (≤ 2 non-empty lines)."""
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=3600, now=lambda: 0.0)

    layer.notify_summary("", **_runtime_status_kwargs())

    msg = notifier.messages[0]
    non_empty_lines = [ln for ln in msg.splitlines() if ln.strip()]
    assert len(non_empty_lines) <= 2, (
        f"Heartbeat message must be ≤ 2 lines, got {len(non_empty_lines)}: {msg!r}"
    )
