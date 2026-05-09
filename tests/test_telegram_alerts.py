from __future__ import annotations

from utils.telegram_alerts import TelegramAlertLayer


class FakeNotifier:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.messages: list[str] = []

    def send_message(self, message: str) -> None:
        if self.fail:
            raise RuntimeError("telegram down")
        self.messages.append(message)


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
