from __future__ import annotations

from types import SimpleNamespace

from utils.telegram_alerts import TelegramAlertLayer


class FakeNotifier:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.messages: list[str] = []

    def send_message(self, message: str, **_metadata) -> None:
        if self.fail:
            raise RuntimeError("telegram down")
        self.messages.append(message)


class _Secret:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get_secret_value(self) -> str:
        return self.value


class AsyncTelemetryNotifier:
    supports_async_telegram_telemetry = True

    def send_message(self, _message: str, **metadata) -> None:
        metadata["telemetry_emit"](
            {
                "timestamp": "2026-05-23T00:00:00Z",
                "event_type": "telegram_send_success",
                "route": metadata["route"],
                "run_id": metadata["run_id"],
                "source_event_id": metadata["source_event_id"],
            }
        )


def test_entry_and_exit_alerts_send_without_cooldown() -> None:
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=300, now=lambda: 100.0)

    assert layer.notify_entry("entry one").sent
    assert layer.notify_entry("entry one").sent
    assert layer.notify_exit("exit one").sent

    assert notifier.messages == ["entry one", "entry one", "exit one"]


def test_risk_alerts_are_cooldown_limited() -> None:
    now = [100.0]
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=300, now=lambda: now[0])

    assert layer.notify_risk("risk", market="BTC", reason="drawdown").sent
    second = layer.notify_risk("risk", market="BTC", reason="drawdown")
    assert second.suppressed
    assert second.reason == "cooldown"

    now[0] += 301.0
    assert layer.notify_risk("risk", market="BTC", reason="drawdown").sent
    assert notifier.messages == ["risk", "risk"]


def test_critical_alerts_deduplicate_repeated_message_but_send_new_issue() -> None:
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=300, now=lambda: 100.0)

    assert layer.notify_critical("api failure").sent
    assert layer.notify_critical("api failure").suppressed
    assert layer.notify_critical("reconcile mismatch").sent

    assert notifier.messages == ["api failure", "reconcile mismatch"]


def test_telegram_failures_never_raise() -> None:
    layer = TelegramAlertLayer(FakeNotifier(fail=True), cooldown_seconds=300, now=lambda: 100.0)

    result = layer.notify_incident("network down")

    assert not result.sent
    assert not result.suppressed
    assert result.reason == "send_failed"


def test_route_attempt_and_success_telemetry_omit_message_body() -> None:
    events: list[dict[str, object]] = []
    layer = TelegramAlertLayer(
        FakeNotifier(),
        cooldown_seconds=300,
        now=lambda: 100.0,
        telemetry_emit=events.append,
        run_id="run-telegram-test",
    )

    result = layer.notify_entry("secret message body", source_event_id="trade_open:abc")

    assert result.sent
    assert [event["event_type"] for event in events] == [
        "telegram_route_attempt",
        "telegram_send_success",
    ]
    assert events[0]["route"] == "entry"
    assert events[0]["run_id"] == "run-telegram-test"
    assert events[0]["source_event_id"] == "trade_open:abc"
    assert "secret message body" not in str(events)


def test_cooldown_suppression_emits_route_and_suppression_telemetry() -> None:
    now = [100.0]
    events: list[dict[str, object]] = []
    layer = TelegramAlertLayer(
        FakeNotifier(),
        cooldown_seconds=300,
        now=lambda: now[0],
        telemetry_emit=events.append,
        run_id="run-telegram-test",
    )

    assert layer.notify_risk("risk", asset="BTC", reason="drawdown").sent
    second = layer.notify_risk("risk", asset="BTC", reason="drawdown")

    assert second.suppressed
    assert [event["event_type"] for event in events] == [
        "telegram_route_attempt",
        "telegram_send_success",
        "telegram_route_attempt",
        "telegram_suppressed_cooldown",
    ]
    suppressed = events[-1]
    assert suppressed["route"] == "risk"
    assert suppressed["cooldown_key"] == "risk:BTC:drawdown"
    assert suppressed["suppression_reason"] == "cooldown"
    assert suppressed["cooldown_seconds"] == 300
    assert suppressed["seconds_remaining"] == 300


def test_unavailable_notifier_emits_failure_telemetry_without_raising() -> None:
    events: list[dict[str, object]] = []
    layer = TelegramAlertLayer(
        None,
        cooldown_seconds=300,
        now=lambda: 100.0,
        telemetry_emit=events.append,
        run_id="run-telegram-test",
    )

    result = layer.notify_exit("secret body", source_event_id="trade_close:def")

    assert not result.sent
    assert result.reason == "notifier_unavailable"
    assert [event["event_type"] for event in events] == [
        "telegram_route_attempt",
        "telegram_send_failure",
    ]
    assert events[-1]["exception_class"] == "NotifierUnavailable"
    assert events[-1]["failure_stage"] == "submit"
    assert "secret body" not in str(events)


def test_startup_config_telemetry_for_disabled_and_missing_config() -> None:
    from utils.telegram_alerts import emit_startup_config_telemetry

    events: list[dict[str, object]] = []
    disabled_settings = SimpleNamespace(
        telegram_enabled="false",
        telegram_bot_token=_Secret(""),
        telegram_chat_id=_Secret(""),
    )
    missing_settings = SimpleNamespace(
        telegram_enabled="true",
        telegram_bot_token=_Secret("token-present"),
        telegram_chat_id=_Secret(""),
    )

    emit_startup_config_telemetry(disabled_settings, telemetry_emit=events.append, run_id="run-telegram-test")
    emit_startup_config_telemetry(missing_settings, telemetry_emit=events.append, run_id="run-telegram-test")

    assert [event["event_type"] for event in events] == [
        "telegram_disabled",
        "telegram_missing_config",
    ]
    assert events[0]["suppression_reason"] == "disabled"
    assert events[1]["suppression_reason"] == "missing_config"
    assert events[1]["has_token"] is True
    assert events[1]["has_chat_id"] is False


def test_async_notifier_telemetry_callback_preserves_event_shape() -> None:
    events: list[dict[str, object]] = []
    layer = TelegramAlertLayer(
        AsyncTelemetryNotifier(),
        cooldown_seconds=300,
        now=lambda: 100.0,
        telemetry_emit=events.append,
        run_id="run-telegram-test",
    )

    result = layer.notify_exit("message", source_event_id="trade_close:xyz")

    assert result.sent
    assert [event["event_type"] for event in events] == [
        "telegram_route_attempt",
        "telegram_send_success",
    ]
    assert events[1]["route"] == "exit"
    assert events[1]["run_id"] == "run-telegram-test"
