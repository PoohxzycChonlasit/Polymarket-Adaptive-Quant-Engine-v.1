from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AlertResult:
    sent: bool
    suppressed: bool = False
    reason: str = ""


class TelegramAlertLayer:
    """Cooldown and fail-soft wrapper around the project Telegram notifier."""

    def __init__(
        self,
        notifier: Any | None = None,
        *,
        cooldown_seconds: int | None = None,
        summary_interval_minutes: int | None = None,
        now: Callable[[], float] | None = None,
    ) -> None:
        if cooldown_seconds is None or summary_interval_minutes is None:
            try:
                from config.settings import get_settings

                settings = get_settings()
                if cooldown_seconds is None:
                    cooldown_seconds = int(getattr(settings, "telegram_alert_cooldown_seconds", 300))
                if summary_interval_minutes is None:
                    summary_interval_minutes = int(getattr(settings, "telegram_summary_interval_minutes", 60))
            except Exception:
                cooldown_seconds = 300 if cooldown_seconds is None else cooldown_seconds
                summary_interval_minutes = 60 if summary_interval_minutes is None else summary_interval_minutes

        self.notifier = notifier
        self.cooldown_seconds = int(cooldown_seconds)
        self.summary_interval_seconds = int(summary_interval_minutes) * 60
        self._now = now or time.monotonic
        self._last_sent: dict[str, float] = {}

    def notify_startup(self, message: str = "", **context: Any) -> AlertResult:
        return self._send(self._format_message("STARTUP", message, context))

    def notify_entry(self, message: str = "", **context: Any) -> AlertResult:
        return self._send(self._format_message("ENTRY", message, context))

    def notify_exit(self, message: str = "", **context: Any) -> AlertResult:
        return self._send(self._format_message("EXIT", message, context))

    def notify_risk(self, message: str = "", **context: Any) -> AlertResult:
        key = self._dedup_key("risk", message, context)
        return self._send_with_cooldown(key, self._format_message("RISK", message, context), self.cooldown_seconds)

    def notify_critical(self, message: str = "", **context: Any) -> AlertResult:
        key = self._dedup_key("critical", message, context)
        return self._send_with_cooldown(key, self._format_message("CRITICAL", message, context), self.cooldown_seconds)

    def notify_summary(self, message: str = "", **context: Any) -> AlertResult:
        key = self._dedup_key("summary", message, context)
        return self._send_with_cooldown(
            key,
            self._format_message("SUMMARY", message, context),
            self.summary_interval_seconds,
        )

    def notify_incident(self, message: str = "", **context: Any) -> AlertResult:
        key = self._dedup_key("incident", message, context)
        return self._send_with_cooldown(key, self._format_message("INCIDENT", message, context), self.cooldown_seconds)

    def _send_with_cooldown(self, key: str, message: str, cooldown_seconds: int) -> AlertResult:
        now = self._now()
        last_sent = self._last_sent.get(key)
        if last_sent is not None and now - last_sent < cooldown_seconds:
            return AlertResult(sent=False, suppressed=True, reason="cooldown")

        result = self._send(message)
        if result.sent:
            self._last_sent[key] = now
        return result

    def _send(self, message: str) -> AlertResult:
        notifier = self.notifier or _get_project_notifier()
        if notifier is None:
            return AlertResult(sent=False, reason="notifier_unavailable")
        try:
            notifier.send_message(message)
            return AlertResult(sent=True)
        except Exception as exc:
            LOGGER.warning("telegram alert send failed: %s", exc)
            return AlertResult(sent=False, reason="send_failed")

    @staticmethod
    def _format_message(kind: str, message: str, context: dict[str, Any]) -> str:
        if message:
            return message
        parts = [f"[{kind}]"]
        for key in sorted(context):
            if key == "dedup_key":
                continue
            parts.append(f"{key}={context[key]}")
        return " ".join(parts)

    @staticmethod
    def _dedup_key(category: str, message: str, context: dict[str, Any]) -> str:
        explicit = context.get("dedup_key")
        if explicit:
            return f"{category}:{explicit}"
        market = context.get("market") or context.get("asset")
        reason = context.get("reason") or context.get("event_type")
        if market or reason:
            return f"{category}:{market}:{reason}"
        return f"{category}:{message}"


_DEFAULT_ALERT_LAYER: TelegramAlertLayer | None = None


def _get_project_notifier() -> Any | None:
    try:
        from utils.logger import get_telegram_notifier

        return get_telegram_notifier()
    except Exception:
        return None


def get_telegram_alert_layer() -> TelegramAlertLayer:
    global _DEFAULT_ALERT_LAYER
    if _DEFAULT_ALERT_LAYER is None:
        _DEFAULT_ALERT_LAYER = TelegramAlertLayer()
    return _DEFAULT_ALERT_LAYER


def notify_startup(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_startup(message, **context)


def notify_entry(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_entry(message, **context)


def notify_exit(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_exit(message, **context)


def notify_risk(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_risk(message, **context)


def notify_critical(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_critical(message, **context)


def notify_summary(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_summary(message, **context)


def notify_incident(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_incident(message, **context)
