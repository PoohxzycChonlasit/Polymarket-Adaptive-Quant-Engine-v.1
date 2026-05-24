from __future__ import annotations

from types import SimpleNamespace

from utils.telegram_alerts import TelegramAlertLayer
from utils.telegram_reporter import build_error_alert, build_startup_alert, build_trade_alert, build_exit_alert


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

    assert len(notifier.messages) == 3
    assert all("━━━━━━━━━━━━━━" in message for message in notifier.messages)
    assert "ENTRY OPENED" in notifier.messages[0]
    assert "entry one" in notifier.messages[0]
    assert "EXIT CLOSED" in notifier.messages[2]
    assert "exit one" in notifier.messages[2]


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
    assert len(notifier.messages) == 2
    assert all("RISK / PAUSE" in message for message in notifier.messages)
    assert all("Reason: drawdown" in message for message in notifier.messages)


def test_critical_alerts_deduplicate_repeated_message_but_send_new_issue() -> None:
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=300, now=lambda: 100.0)

    assert layer.notify_critical("api failure").sent
    assert layer.notify_critical("api failure").suppressed
    assert layer.notify_critical("reconcile mismatch").sent

    assert len(notifier.messages) == 2
    assert "INCIDENT | P0" in notifier.messages[0]
    assert "api failure" in notifier.messages[0]
    assert "reconcile mismatch" in notifier.messages[1]


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


def test_entry_blank_message_uses_operator_console_template() -> None:
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=300, now=lambda: 100.0)

    assert layer.notify_entry(
        "",
        mode="paper",
        market="ETH 5M",
        side="NO",
        price="0.530",
        size="0.096",
        session="09h10h",
        lifecycle_phase="OPENING_SCAN",
        price_bucket="0.50-0.70",
        executable=False,
        dust_zone=True,
    ).sent

    message = notifier.messages[0]
    assert "ENTRY OPENED" in message
    assert "Mode: PAPER / SIGNAL" in message
    assert "Market: ETH 5M" in message
    assert "Side: NO" in message
    assert "Entry: 0.530" in message
    assert "Size: 0.096" in message
    assert "Session: 09h10h" in message
    assert "Lifecycle: OPENING" in message
    assert "Dust Zone" in message
    assert "Executable: No" in message
    assert "Research signal only." in message
    assert "dedup_key" not in message


def test_exit_blank_message_uses_tp_or_sl_operator_template() -> None:
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=300, now=lambda: 100.0)

    assert layer.notify_exit(
        "",
        mode="paper",
        market="BTC 5M",
        side="YES",
        reason="stop_loss",
        entry_price="0.610",
        exit_price="0.560",
        pnl="-0.0045",
        hold_seconds=12,
        dust_zone=True,
    ).sent

    message = notifier.messages[0]
    assert "STOP LOSS CLOSED" in message
    assert "Mode: PAPER / SIGNAL" in message
    assert "Market: BTC 5M" in message
    assert "Side: YES" in message
    assert "Price: 0.610 -> 0.560" in message
    assert "Signal PnL: -0.0045" in message
    assert "Reason: stop_loss" in message
    assert "Dust Zone" in message


def test_risk_and_incident_blank_messages_use_operator_console_templates() -> None:
    now = [100.0]
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=300, now=lambda: now[0])

    assert layer.notify_risk("", mode="paper", market="BTC", reason="cooldown", risk_state="PAUSED").sent
    now[0] += 301
    assert layer.notify_incident(
        "",
        mode="paper",
        subsystem="telegram",
        reason="send_failure",
        impact="operator visibility degraded",
    ).sent

    risk_message, incident_message = notifier.messages
    assert "RISK / PAUSE" in risk_message
    assert "Mode: PAPER" in risk_message
    assert "Reason: cooldown" in risk_message
    assert "Meaning: Trading attention required." in risk_message
    assert "INCIDENT" in incident_message
    assert "Subsystem: telegram" in incident_message
    assert "Impact: operator visibility degraded" in incident_message
    assert "Trading: unaffected unless stated" in incident_message


def test_reporter_startup_trade_exit_and_error_use_operator_console_copy() -> None:
    startup = build_startup_alert(
        mode="PAPER",
        status="CONNECTED",
        interval=60,
        bankroll=250.0,
        paper=True,
        wallet="0x1234567890abcdef",
        balance_source="wallet_reference_paper",
        wallet_balance=250.0,
        paper_cash=250.0,
        execution_mode="PAPER ONLY",
    )
    entry = build_trade_alert(
        asset="ETH 5M",
        signal="NO",
        momentum_pct=0.1,
        score=0.7,
        position_size=0.05,
        bankroll=250.0,
        entry_price=0.53,
        paper=True,
        shares=0.096,
    )
    exit_msg = build_exit_alert(
        title="Stop Loss",
        asset="BTC 5M",
        side="YES",
        entry_price=0.61,
        exit_price=0.56,
        pnl=-0.0045,
        bankroll=249.99,
        reason="stop_loss",
        paper=True,
        shares=0.096,
        countdown=120,
    )
    error = build_error_alert("polymarket.trader", "secret <payload> " + "x" * 500, "ERROR")

    assert "STARTUP" in startup
    assert "Mode: PAPER" in startup
    assert "wallet_reference_paper" in startup
    assert "$250.0000 USDC" in startup
    assert "NO LIVE ORDERS" in startup
    assert "0x1234567890abcdef" not in startup
    assert "ENTRY OPENED" in entry
    assert "Mode: PAPER / SIGNAL" in entry
    assert "Evidence:" in entry
    assert "Dust Zone" in entry
    assert "STOP LOSS CLOSED" in exit_msg
    assert "Signal PnL: -$0.0045" in exit_msg
    assert "INCIDENT" in error
    assert "secret" not in error.lower()
    assert "<payload>" not in error
