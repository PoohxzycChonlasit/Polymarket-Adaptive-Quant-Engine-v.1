from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
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
        telemetry_emit: Callable[[dict[str, Any]], Any] | None = None,
        run_id: str | None = None,
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
        self._telemetry_emit = telemetry_emit
        self.run_id = run_id

    def notify_startup(self, message: str = "", **context: Any) -> AlertResult:
        return self._send("startup", self._format_message("STARTUP", message, context), context)

    def notify_entry(self, message: str = "", **context: Any) -> AlertResult:
        return self._send("entry", self._format_message("ENTRY", message, context), context)

    def notify_exit(self, message: str = "", **context: Any) -> AlertResult:
        return self._send("exit", self._format_message("EXIT", message, context), context)

    def notify_risk(self, message: str = "", **context: Any) -> AlertResult:
        key = self._dedup_key("risk", message, context)
        return self._send_with_cooldown("risk", key, self._format_message("RISK", message, context), context, self.cooldown_seconds)

    def notify_critical(self, message: str = "", **context: Any) -> AlertResult:
        key = self._dedup_key("critical", message, context)
        return self._send_with_cooldown("critical", key, self._format_message("CRITICAL", message, context), context, self.cooldown_seconds)

    def notify_summary(self, message: str = "", **context: Any) -> AlertResult:
        key = self._dedup_key("summary", message, context)
        return self._send_with_cooldown(
            "summary",
            key,
            self._format_message("SUMMARY", message, context),
            context,
            self.summary_interval_seconds,
        )

    def notify_incident(self, message: str = "", **context: Any) -> AlertResult:
        key = self._dedup_key("incident", message, context)
        return self._send_with_cooldown("incident", key, self._format_message("INCIDENT", message, context), context, self.cooldown_seconds)

    def _send_with_cooldown(
        self,
        route: str,
        key: str,
        message: str,
        context: dict[str, Any],
        cooldown_seconds: int,
    ) -> AlertResult:
        now = self._now()
        source_event_id = _safe_optional_text(context.get("source_event_id"))
        self._emit_telemetry(
            "telegram_route_attempt",
            route=route,
            source_event_id=source_event_id,
            cooldown_key=key,
        )
        last_sent = self._last_sent.get(key)
        if last_sent is not None and now - last_sent < cooldown_seconds:
            seconds_remaining = max(0, int(cooldown_seconds - (now - last_sent)))
            self._emit_telemetry(
                "telegram_suppressed_cooldown",
                route=route,
                source_event_id=source_event_id,
                cooldown_key=key,
                suppression_reason="cooldown",
                cooldown_seconds=int(cooldown_seconds),
                seconds_remaining=seconds_remaining,
            )
            return AlertResult(sent=False, suppressed=True, reason="cooldown")

        result = self._send(route, message, context, cooldown_key=key, emit_attempt=False)
        if result.sent:
            self._last_sent[key] = now
        return result

    def _send(
        self,
        route: str,
        message: str,
        context: dict[str, Any],
        *,
        cooldown_key: str | None = None,
        emit_attempt: bool = True,
    ) -> AlertResult:
        source_event_id = _safe_optional_text(context.get("source_event_id"))
        if emit_attempt:
            self._emit_telemetry(
                "telegram_route_attempt",
                route=route,
                source_event_id=source_event_id,
                cooldown_key=cooldown_key,
            )
        notifier = self.notifier or _get_project_notifier()
        if notifier is None:
            self._emit_telemetry(
                "telegram_send_failure",
                route=route,
                source_event_id=source_event_id,
                cooldown_key=cooldown_key,
                exception_class="NotifierUnavailable",
                failure_stage="submit",
            )
            return AlertResult(sent=False, reason="notifier_unavailable")
        try:
            try:
                notifier.send_message(
                    message,
                    route=route,
                    source_event_id=source_event_id,
                    cooldown_key=cooldown_key,
                    run_id=self.run_id,
                    telemetry_emit=self._emit_telemetry,
                )
            except TypeError:
                notifier.send_message(message)
            if not getattr(notifier, "supports_async_telegram_telemetry", False):
                self._emit_telemetry(
                    "telegram_send_success",
                    route=route,
                    source_event_id=source_event_id,
                    cooldown_key=cooldown_key,
                )
            return AlertResult(sent=True)
        except Exception as exc:
            LOGGER.warning("telegram alert send failed: %s", exc)
            self._emit_telemetry(
                "telegram_send_failure",
                route=route,
                source_event_id=source_event_id,
                cooldown_key=cooldown_key,
                exception_class=exc.__class__.__name__,
                failure_stage="submit",
            )
            return AlertResult(sent=False, reason="send_failed")

    def _emit_telemetry(self, event_type: str | dict[str, Any], **fields: Any) -> None:
        emit = self._telemetry_emit
        if emit is None:
            return
        try:
            if isinstance(event_type, dict):
                emit(event_type)
            else:
                emit(_telegram_telemetry_event(event_type, run_id=self.run_id, **fields))
        except Exception:
            LOGGER.debug("telegram telemetry emit failed", exc_info=True)

    @staticmethod
    def _format_message(kind: str, message: str, context: dict[str, Any]) -> str:
        if message:
            context = dict(context)
            summary = _safe_message_summary(message)
            context.setdefault("legacy_message", summary)
            context.setdefault("reason", summary)
            context.setdefault("headline", summary)
            context.setdefault("impact", summary)
        return _operator_console_message(kind, context)

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


def _safe_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_text(value: Any, default: str = "n/a") -> str:
    text = _safe_optional_text(value)
    if text is None:
        return default
    return text.replace("<", "").replace(">", "")


def _safe_message_summary(value: Any, limit: int = 160) -> str:
    text = _safe_text(value, "")
    for token in ("secret", "token", "chat_id", "private_key", "authorization"):
        text = text.replace(token, "[redacted]").replace(token.upper(), "[redacted]")
    text = " ".join(text.split())
    if len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text or "operator event"


def _mode_label(context: dict[str, Any]) -> str:
    raw = str(context.get("mode") or context.get("execution_mode") or "").strip().upper()
    paper_hint = context.get("paper")
    if raw in {"LIVE", "REAL"} or paper_hint is False:
        return "LIVE"
    return "PAPER"


def _paper_signal_label(context: dict[str, Any]) -> str:
    mode = _mode_label(context)
    if mode == "LIVE":
        return "LIVE"
    state = str(context.get("state") or context.get("evidence") or context.get("evidence_label") or "SIGNAL").upper()
    if "EXECUTABLE" in state and not bool(context.get("dust_zone")):
        return "PAPER / EXECUTABLE_CANDIDATE"
    return "PAPER / SIGNAL"


def _market_label(context: dict[str, Any]) -> str:
    return _safe_text(context.get("market") or context.get("asset") or context.get("ticker"), "SYSTEM")


def _yes_no(value: Any) -> str:
    if isinstance(value, str):
        return "Yes" if value.strip().lower() in {"1", "true", "yes", "y", "on"} else "No"
    return "Yes" if bool(value) else "No"


def _compact_lifecycle(value: Any) -> str:
    raw = _safe_text(value, "")
    return raw.replace("_SCAN", "").replace("_INVENTORY_TRADING", "").replace("_OR_UNSAFE", "")


def _evidence_lines(context: dict[str, Any]) -> list[str]:
    executable = context.get("executable")
    dust_zone = context.get("dust_zone")
    lines = ["Evidence:"]
    if dust_zone is not None:
        lines.append("Dust Zone" if bool(dust_zone) else "Not Dust Zone")
    elif _mode_label(context) == "PAPER":
        lines.append("SIGNAL_MODE")
    if executable is not None:
        lines.append(f"Executable: {_yes_no(executable)}")
    elif _mode_label(context) == "PAPER":
        lines.append("Executable: Unknown")
    return lines


def _ref_line(context: dict[str, Any]) -> str:
    ref = (
        context.get("trade_id")
        or context.get("order_id")
        or context.get("position_id")
        or context.get("source_event_id")
        or context.get("run_id")
    )
    return f"Ref: {_safe_text(ref)}"


def _operator_console_message(kind: str, context: dict[str, Any]) -> str:
    kind = kind.upper()
    if kind == "STARTUP":
        return _operator_startup_message(context)
    if kind == "ENTRY":
        return _operator_entry_message(context)
    if kind == "EXIT":
        return _operator_exit_message(context)
    if kind == "RISK":
        return _operator_risk_message(context)
    if kind in {"CRITICAL", "INCIDENT"}:
        return _operator_incident_message(kind, context)
    if kind == "SUMMARY":
        return _operator_summary_message(context)
    return _operator_incident_message(kind, context)


def _operator_startup_message(context: dict[str, Any]) -> str:
    mode = _mode_label(context)
    status = _safe_text(context.get("status"), "started")
    interval = _safe_text(context.get("interval") or context.get("scan_interval"), "n/a")
    meaning = "Paper evidence collection active." if mode == "PAPER" else "Live mode requested; monitor readiness closely."
    return "\n".join(
        [
            "🚀 STARTUP | P2",
            "Operator console online",
            "━━━━━━━━━━━━━━",
            f"Mode: {mode}",
            f"Status: {status}",
            f"Scan Loop: {interval}s",
            f"Evidence: {'SIGNAL_MODE' if mode == 'PAPER' else 'LIVE'}",
            "",
            "Meaning:",
            meaning,
            _ref_line(context),
        ]
    )


def _operator_entry_message(context: dict[str, Any]) -> str:
    return "\n".join(
        [
            "🟢 ENTRY OPENED",
            "━━━━━━━━━━━━━━",
            f"Mode: {_paper_signal_label(context)}",
            f"Market: {_market_label(context)}",
            f"Side: {_safe_text(context.get('side') or context.get('outcome'))}",
            f"Entry: {_safe_text(context.get('entry_price') or context.get('price'))}",
            f"Size: {_safe_text(context.get('size') or context.get('shares') or context.get('position_size'))}",
            "",
            "Context:",
            f"Session: {_safe_text(context.get('session') or context.get('session_hour') or context.get('session_hour_utc'))}",
            f"Lifecycle: {_compact_lifecycle(context.get('lifecycle_phase')) or 'n/a'}",
            f"Price Bucket: {_safe_text(context.get('price_bucket'))}",
            "",
            *_evidence_lines(context),
            "",
            "Meaning:",
            _safe_text(context.get("legacy_message"), "Research signal only." if _mode_label(context) == "PAPER" else "Live order path event."),
            _ref_line(context),
        ]
    )


def _operator_exit_message(context: dict[str, Any]) -> str:
    reason = _safe_text(context.get("reason") or context.get("exit_reason"), "exit")
    lower_reason = reason.lower()
    pnl = _safe_text(context.get("pnl") or context.get("pnl_usdc"), "n/a")
    is_tp = "take_profit" in lower_reason or lower_reason in {"tp", "profit"}
    is_sl = "stop_loss" in lower_reason or lower_reason in {"sl", "loss"}
    title = "✅ TAKE PROFIT CLOSED" if is_tp else "🔴 STOP LOSS CLOSED" if is_sl else "🟠 EXIT CLOSED"
    pnl_label = "Signal PnL" if _mode_label(context) == "PAPER" else "PnL"
    hold = _safe_text(context.get("hold_seconds") or context.get("hold"), "n/a")
    return "\n".join(
        [
            title,
            "━━━━━━━━━━━━━━",
            f"Mode: {_paper_signal_label(context)}",
            f"Market: {_market_label(context)}",
            f"Side: {_safe_text(context.get('side') or context.get('outcome'))}",
            f"Price: {_safe_text(context.get('entry_price'))} -> {_safe_text(context.get('exit_price') or context.get('price'))}",
            f"Hold: {hold}s" if hold != "n/a" else "Hold: n/a",
            f"{pnl_label}: {pnl}",
            f"Reason: {reason}",
            "",
            *_evidence_lines(context),
            "",
            "Meaning:",
            _safe_text(context.get("legacy_message"), "Research signal only." if _mode_label(context) == "PAPER" else "Live exit path event."),
            _ref_line(context),
        ]
    )


def _operator_risk_message(context: dict[str, Any]) -> str:
    return "\n".join(
        [
            "🟡 RISK / PAUSE | P1",
            "Trading attention required",
            "━━━━━━━━━━━━━━",
            f"Mode: {_mode_label(context)}",
            f"Market: {_market_label(context)}",
            f"Reason: {_safe_text(context.get('reason') or context.get('event_type'))}",
            f"State: {_safe_text(context.get('risk_state') or context.get('state'), 'PAUSED')}",
            "",
            "Meaning: Trading attention required.",
            _ref_line(context),
        ]
    )


def _operator_incident_message(kind: str, context: dict[str, Any]) -> str:
    priority = "P0" if kind == "CRITICAL" else "P1"
    return "\n".join(
        [
            f"🚨 INCIDENT | {priority}",
            _safe_text(context.get("headline") or context.get("reason") or context.get("event_type"), "Operator incident"),
            "━━━━━━━━━━━━━━",
            f"Mode: {_mode_label(context)}",
            f"Subsystem: {_safe_text(context.get('subsystem') or context.get('module') or context.get('component'))}",
            f"Market: {_market_label(context)}",
            f"Impact: {_safe_text(context.get('impact'), 'review needed')}",
            "Trading: unaffected unless stated",
            "",
            "Meaning: Inspect logs or dashboard before taking action.",
            _ref_line(context),
        ]
    )


def _operator_summary_message(context: dict[str, Any]) -> str:
    return "\n".join(
        [
            "📊 DAILY DIGEST | P3",
            "Evidence summary",
            "━━━━━━━━━━━━━━",
            f"Mode: {_mode_label(context)}",
            f"Trades: {_safe_text(context.get('trades') or context.get('trade_count'))}",
            f"TP/SL: {_safe_text(context.get('tp'))}/{_safe_text(context.get('sl'))}",
            f"Signal PnL: {_safe_text(context.get('signal_pnl') or context.get('pnl'))}",
            f"Executable: {_safe_text(context.get('executable_trade_count') or context.get('executable'))}",
            "",
            "Meaning: Daily research snapshot.",
            _ref_line(context),
        ]
    )


def _telegram_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _telegram_telemetry_event(event_type: str, *, run_id: str | None = None, **fields: Any) -> dict[str, Any]:
    event: dict[str, Any] = {
        "timestamp": _telegram_timestamp(),
        "event_type": event_type,
        "route": _safe_optional_text(fields.pop("route", None)) or "unknown",
        "run_id": run_id,
        "source_event_id": _safe_optional_text(fields.pop("source_event_id", None)),
    }
    for key, value in fields.items():
        if value is not None:
            event[key] = value
    return event


def _telegram_enabled_value(settings: Any) -> bool:
    return str(getattr(settings, "telegram_enabled", "true") or "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "enabled",
    }


def _secret_present(value: Any) -> bool:
    try:
        if hasattr(value, "get_secret_value"):
            value = value.get_secret_value()
    except Exception:
        return False
    return bool(str(value or "").strip())


def emit_startup_config_telemetry(
    settings: Any,
    *,
    telemetry_emit: Callable[[dict[str, Any]], Any] | None,
    run_id: str | None = None,
) -> None:
    if telemetry_emit is None:
        return
    try:
        enabled = _telegram_enabled_value(settings)
        has_token = _secret_present(getattr(settings, "telegram_bot_token", ""))
        has_chat_id = _secret_present(getattr(settings, "telegram_chat_id", ""))
        if not enabled:
            telemetry_emit(
                _telegram_telemetry_event(
                    "telegram_disabled",
                    run_id=run_id,
                    route="startup",
                    source_event_id=None,
                    suppression_reason="disabled",
                )
            )
        elif not has_token or not has_chat_id:
            telemetry_emit(
                _telegram_telemetry_event(
                    "telegram_missing_config",
                    run_id=run_id,
                    route="startup",
                    source_event_id=None,
                    suppression_reason="missing_config",
                    has_token=has_token,
                    has_chat_id=has_chat_id,
                )
            )
    except Exception:
        LOGGER.debug("telegram startup config telemetry failed", exc_info=True)


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
