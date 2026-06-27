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
        self.heartbeat_retry_cooldown_seconds = 60
        self._now = now or time.monotonic
        self._last_sent: dict[str, float] = {}
        self._heartbeat_retry_until: dict[str, float] = {}
        self._telemetry_emit = telemetry_emit
        self.run_id = run_id
        # Guarantees one startup heartbeat per instance before the hourly cooldown activates.
        self._startup_heartbeat_sent: bool = False

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
        # Startup heartbeat bypass: the very first runtime_status summary per instance
        # is sent unconditionally, bypassing the hourly cooldown gate. This guarantees
        # at least one heartbeat per runtime run regardless of session duration.
        # All subsequent runtime_status calls and all non-runtime_status summaries
        # continue to use the normal cooldown path unchanged.
        if context.get("dedup_key") == "runtime_status":
            self._emit_heartbeat_event("heartbeat_generated", cooldown_key=key)
        if context.get("dedup_key") == "runtime_status" and not self._startup_heartbeat_sent:
            self._startup_heartbeat_sent = True
            formatted = self._format_message("SUMMARY", message, context)
            result = self._send("summary", formatted, context, cooldown_key=key)
            if result.sent:
                self._record_summary_send_queued(key)
            else:
                self._record_runtime_status_failure(key, reason=result.reason or "send_failed")
            return result
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

    # ── Live order observability helpers (P0.4) ────────────────────────────
    # These are fail-soft and deduped. Telegram failure never blocks runtime.

    def notify_allowance_missing(self, message: str = "", **context: Any) -> AlertResult:
        """USDC allowance is zero or missing — must approve before live trading."""
        key = self._dedup_key("allowance_missing", message, context)
        formatted = self._format_message("ALLOWANCE_MISSING", message or "USDC allowance missing. Approve before live trading.", context)
        return self._send_with_cooldown("critical", key, formatted, context, self.cooldown_seconds)

    def notify_signing_not_ready(self, message: str = "", **context: Any) -> AlertResult:
        """Live signing capability check failed — key/builder not loaded."""
        key = self._dedup_key("signing_not_ready", message, context)
        formatted = self._format_message("SIGNING_NOT_READY", message or "Live signing not ready. Check private key configuration.", context)
        return self._send_with_cooldown("critical", key, formatted, context, self.cooldown_seconds)

    def notify_order_submitted(self, message: str = "", **context: Any) -> AlertResult:
        """Live order submitted to CLOB — not yet confirmed fill."""
        key = self._dedup_key("order_submitted", message, context)
        formatted = self._format_message("ORDER_SUBMITTED", message, context)
        return self._send_with_cooldown("entry", key, formatted, context, self.cooldown_seconds)

    def notify_order_filled(self, message: str = "", **context: Any) -> AlertResult:
        """Live order confirmed filled."""
        key = self._dedup_key("order_filled", message, context)
        formatted = self._format_message("ORDER_FILLED", message, context)
        return self._send_with_cooldown("entry", key, formatted, context, self.cooldown_seconds)

    def notify_order_cancelled(self, message: str = "", **context: Any) -> AlertResult:
        """Live order cancelled or rejected (non-timeout terminal states)."""
        key = self._dedup_key("order_cancelled", message, context)
        formatted = self._format_message("ORDER_CANCELLED", message, context)
        return self._send_with_cooldown("risk", key, formatted, context, self.cooldown_seconds)

    def notify_order_timeout_cancelled(self, message: str = "", **context: Any) -> AlertResult:
        """Live order cancelled because it timed out waiting for a fill."""
        key = self._dedup_key("order_timeout_cancelled", message, context)
        formatted = self._format_message("ORDER_TIMEOUT_CANCELLED", message, context)
        return self._send_with_cooldown("risk", key, formatted, context, self.cooldown_seconds)

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
            if self._is_runtime_status_summary(route, key):
                self._emit_heartbeat_event(
                    "heartbeat_suppressed",
                    cooldown_key=key,
                    suppression_reason="cooldown",
                    cooldown_seconds=int(cooldown_seconds),
                    seconds_remaining=seconds_remaining,
                )
            return AlertResult(sent=False, suppressed=True, reason="cooldown")

        retry_until = self._heartbeat_retry_until.get(key)
        if self._is_runtime_status_summary(route, key) and retry_until is not None and now < retry_until:
            seconds_remaining = max(0, int(retry_until - now))
            self._emit_telemetry(
                "telegram_suppressed_cooldown",
                route=route,
                source_event_id=source_event_id,
                cooldown_key=key,
                suppression_reason="heartbeat_retry_backoff",
                cooldown_seconds=int(self.heartbeat_retry_cooldown_seconds),
                seconds_remaining=seconds_remaining,
            )
            self._emit_heartbeat_event(
                "heartbeat_suppressed",
                cooldown_key=key,
                suppression_reason="heartbeat_retry_backoff",
                retry_cooldown_seconds=int(self.heartbeat_retry_cooldown_seconds),
                seconds_remaining=seconds_remaining,
            )
            return AlertResult(sent=False, suppressed=True, reason="heartbeat_retry_backoff")

        result = self._send(route, message, context, cooldown_key=key, emit_attempt=False)
        if result.sent:
            if self._is_runtime_status_summary(route, key):
                self._record_summary_send_queued(key)
            else:
                self._last_sent[key] = now
        elif self._is_runtime_status_summary(route, key):
            self._record_runtime_status_failure(key, reason=result.reason or "send_failed")
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
        event: dict[str, Any] | None = None
        if isinstance(event_type, dict):
            event = dict(event_type)
        else:
            event = _telegram_telemetry_event(event_type, run_id=self.run_id, **fields)
        self._handle_runtime_status_delivery_event(event)
        if emit is None:
            return
        try:
            emit(event)
        except Exception:
            LOGGER.debug("telegram telemetry emit failed", exc_info=True)

    @staticmethod
    def _is_runtime_status_summary(route: str, key: str | None) -> bool:
        return route == "summary" and key == "summary:runtime_status"

    def _notifier_uses_async_delivery_telemetry(self) -> bool:
        notifier = self.notifier or _get_project_notifier()
        return bool(getattr(notifier, "supports_async_telegram_telemetry", False))

    def _record_summary_send_queued(self, key: str) -> None:
        if key in self._last_sent and key not in self._heartbeat_retry_until:
            return
        if self._notifier_uses_async_delivery_telemetry():
            self._heartbeat_retry_until[key] = self._now() + self.heartbeat_retry_cooldown_seconds
            return
        now = self._now()
        self._last_sent[key] = now
        self._heartbeat_retry_until.pop(key, None)
        self._emit_heartbeat_event(
            "heartbeat_delivered",
            cooldown_key=key,
            cooldown_seconds=int(self.summary_interval_seconds),
        )

    def _record_runtime_status_failure(self, key: str, *, reason: str) -> None:
        self._last_sent.pop(key, None)
        self._heartbeat_retry_until[key] = self._now() + self.heartbeat_retry_cooldown_seconds
        self._emit_heartbeat_event(
            "heartbeat_send_failed",
            cooldown_key=key,
            reason=reason,
        )
        self._emit_heartbeat_event(
            "heartbeat_retry_scheduled",
            cooldown_key=key,
            retry_cooldown_seconds=int(self.heartbeat_retry_cooldown_seconds),
        )

    def _handle_runtime_status_delivery_event(self, event: dict[str, Any]) -> None:
        route = str(event.get("route") or "")
        key = str(event.get("cooldown_key") or "")
        if not self._is_runtime_status_summary(route, key):
            return
        event_type = str(event.get("event_type") or "")
        if event_type == "telegram_send_success":
            self._last_sent[key] = self._now()
            self._heartbeat_retry_until.pop(key, None)
            self._emit_heartbeat_event(
                "heartbeat_delivered",
                cooldown_key=key,
                cooldown_seconds=int(self.summary_interval_seconds),
            )
        elif event_type == "telegram_send_failure":
            self._record_runtime_status_failure(key, reason=str(event.get("exception_class") or "send_failed"))

    def _emit_heartbeat_event(self, event_type: str, **fields: Any) -> None:
        emit = self._telemetry_emit
        if emit is None:
            return
        try:
            emit(_telegram_telemetry_event(event_type, run_id=self.run_id, route="summary", **fields))
        except Exception:
            LOGGER.debug("heartbeat telemetry emit failed", exc_info=True)

    @staticmethod
    def _format_message(kind: str, message: str, context: dict[str, Any]) -> str:
        ctx = dict(context)
        if message:
            # Check if message is already in compact pipe-separated format
            lines = message.splitlines()
            first_line = lines[0].strip() if lines else ""
            if " | " in first_line:
                return message

            parsed = _parse_verbose_message(message)
            ctx.update(parsed)

            if "legacy_message" not in ctx:
                summary = _safe_message_summary(message)
                ctx["legacy_message"] = summary
                ctx.setdefault("reason", summary)
                ctx.setdefault("headline", summary)
                ctx.setdefault("impact", summary)

            if "event_type_detected" in ctx:
                kind = ctx["event_type_detected"]
        return _operator_console_message(kind, ctx)

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


def _map_display_shortcut(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    norm = s.lower().replace(" ", "_")
    shortcuts = {
        "probability_ev_edge": "EV_EDGE",
        "no_signal": "NO_SIG",
        "yes_ev_above_threshold": "YES_EV",
        "no_ev_above_threshold": "NO_EV",
        "no_strategy_met_threshold": "NO_STRAT_MET",
        "stop_loss": "SL",
        "take_profit": "TP",
        "forced_exit": "FORCED",
        "final_derisk": "DERISK",
        "binary_settlement": "SETTLED",
    }
    if norm in shortcuts:
        return shortcuts[norm]
    return s


def _parse_verbose_message(message: str) -> dict[str, Any]:
    parsed = {}
    if not message:
        return parsed

    import re
    clean_msg = re.sub(r"<[^>]+>", "", message)
    lines = [line.strip() for line in clean_msg.splitlines() if line.strip()]

    first_few = " ".join(lines[:2]).upper()
    if "STARTUP" in first_few or "STARTED" in first_few:
        parsed["event_type_detected"] = "STARTUP"
    elif "ENTRY OPENED" in first_few or "OPEN" in first_few:
        parsed["event_type_detected"] = "ENTRY"
    elif "CLOSED" in first_few or "CLOSE" in first_few or "SETTLED" in first_few:
        parsed["event_type_detected"] = "EXIT"
    elif "RISK" in first_few or "PAUSE" in first_few or "SUSPENDED" in first_few:
        parsed["event_type_detected"] = "RISK"
    elif "INCIDENT" in first_few or "ERROR" in first_few or "CRITICAL" in first_few:
        parsed["event_type_detected"] = "INCIDENT"
    elif "STATUS" in first_few or "HEARTBEAT" in first_few:
        parsed["event_type_detected"] = "SUMMARY"
    elif "DAILY" in first_few or "DIGEST" in first_few:
        parsed["event_type_detected"] = "SUMMARY"

    for line in lines:
        line_clean = re.sub(r"^[•\-\*└\s\t\W]+", "", line).strip()
        parts = []
        if ":" in line_clean:
            parts = line_clean.split(":", 1)
        else:
            split_spaces = re.split(r"\s{2,}", line_clean, maxsplit=1)
            if len(split_spaces) == 2:
                parts = split_spaces

        if len(parts) == 2:
            k = parts[0].strip().lower().replace("&amp;", "").replace("p&l", "pnl")
            v = parts[1].strip()

            if k in ("mode", "execution"):
                parsed["mode"] = v
            elif k in ("status", "state"):
                parsed["status"] = v
            elif k in ("scan loop", "interval"):
                parsed["interval"] = v
            elif k in ("bankroll", "capital", "wallet bankroll", "paper cash"):
                parsed["bankroll"] = v
            elif k in ("asset", "market", "ticker"):
                parsed["market"] = v
            elif k in ("side", "signal", "direction", "outcome"):
                parsed["side"] = v
            elif k in ("entry price", "entry", "price"):
                if "->" in v:
                    entry_exit = v.split("->")
                    parsed["entry_price"] = entry_exit[0].strip()
                    parsed["exit_price"] = entry_exit[1].strip()
                else:
                    parsed["entry_price"] = v
            elif k == "exit price":
                parsed["exit_price"] = v
            elif k in ("size", "shares", "cost", "position_size"):
                parsed["size"] = v
            elif k in ("pnl", "signal pnl"):
                parsed["pnl"] = v
            elif k == "reason":
                parsed["reason"] = v
            elif k in ("hold", "hold time", "hold seconds", "countdown"):
                parsed["hold_seconds"] = v
            elif k in ("run", "run id", "ref", "order id"):
                parsed["run_id"] = v
            elif k == "cycles":
                parsed["cycles"] = v
            elif k == "opens":
                parsed["trade_opens"] = v
            elif k == "closes":
                parsed["trade_closes"] = v
            elif k == "exc":
                parsed["exceptions"] = v
            elif k == "risk":
                parsed["risk_mode"] = v
            elif k == "regime":
                parsed["regime"] = v
            elif k == "heartbeat":
                parsed["heartbeat_age"] = v
            elif k == "impact":
                parsed["impact"] = v
            elif k == "subsystem":
                parsed["subsystem"] = v
            elif k == "action":
                parsed["action"] = v
            elif k == "streak":
                parsed["streak"] = v
            elif k == "pause":
                parsed["pause"] = v
            elif k == "drawdown":
                parsed["drawdown"] = v

    return parsed


def _get_val(context: dict[str, Any], keys: list[str] | str, default: str = "") -> str:
    if isinstance(keys, str):
        keys = [keys]
    for key in keys:
        val = context.get(key)
        if val is not None:
            s = str(val).strip()
            import re
            s = re.sub(r"<[^>]+>", "", s)
            if s and s.lower() not in ("n/a", "none", "unknown"):
                return _map_display_shortcut(s)
    return default


def _short_run_id(context: dict[str, Any]) -> str:
    run_id = _get_val(context, ["run_id", "trade_id", "order_id", "position_id", "source_event_id"])
    if run_id:
        if "/" in run_id:
            run_id = run_id.split("/")[-1]
        if len(run_id) > 8:
            return run_id[:8]
        return run_id
    return ""


def _is_pnl_positive(pnl_str: str) -> bool:
    if not pnl_str:
        return False
    if pnl_str.startswith("+"):
        return True
    if pnl_str.startswith("-"):
        return False
    try:
        import re
        nums = re.findall(r"[-+]?\d*\.\d+|\d+", pnl_str)
        if nums:
            return float(nums[0]) >= 0
    except Exception:
        pass
    return False


def _format_hold_time(hold_val: Any) -> str:
    if hold_val is None:
        return ""
    s = str(hold_val).strip()
    if not s or s.lower() in ("n/a", "none", "unknown"):
        return ""
    s_clean = s.rstrip("s")
    try:
        sec = int(float(s_clean))
        if sec < 60:
            return f"{sec}s"
        m = sec // 60
        sec_rem = sec % 60
        if sec_rem == 0:
            return f"{m}m"
        return f"{m}m{sec_rem}s"
    except Exception:
        return s


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
    if kind in {"SUMMARY", "SUMMARY_STATUS", "SUMMARY_DIGEST"}:
        return _operator_summary_message(context)
    return _operator_incident_message(kind, context)


def _operator_startup_message(context: dict[str, Any]) -> str:
    mode = _mode_label(context)
    run_id = _short_run_id(context)
    interval = _get_val(context, ["interval", "scan_interval"], "n/a")
    
    wallet = _get_val(context, ["wallet", "balance_source"], "paper")
    if wallet.startswith("0x") and len(wallet) > 10:
        wallet = f"{wallet[:6]}...{wallet[-4:]}"
    elif "paper" in wallet.lower():
        wallet = "paper"
        
    live_status = "ON" if mode == "LIVE" else "OFF"
    
    line1 = f"🚀 START | {mode}"
    if run_id:
        line1 += f" | Run:{run_id}"
    if interval != "n/a":
        line1 += f" | Interval:{interval}s"
        
    line2 = f"Wallet:{wallet} | Live:{live_status}"
    return f"{line1}\n{line2}"


def _operator_entry_message(context: dict[str, Any]) -> str:
    market = _get_val(context, ["market", "asset", "ticker"], "SYSTEM")
    side = _get_val(context, ["side", "outcome"])
    entry_price = _get_val(context, ["entry_price", "price"])
    size = _get_val(context, ["size", "shares", "position_size"])
    
    signal = _get_val(context, ["signal", "event_type"])
    strategy = _get_val(context, ["strategy"])
    ev = _get_val(context, ["ev", "ev_after_spread"])
    prob = _get_val(context, ["prob", "score", "confidence", "true_probability"])
    run_id = _short_run_id(context)
    
    if "YES" in side.upper():
        side = "YES"
    elif "NO" in side.upper():
        side = "NO"
        
    line1 = f"🟢 OPEN | {market} {side}".strip()
    if entry_price:
        line1 += f" | Entry:{entry_price}"
    if size:
        line1 += f" | Size:{size}"
        
    line2_parts = []
    if signal:
        line2_parts.append(f"Sig:{signal}")
    if strategy:
        line2_parts.append(f"Strat:{strategy}")
    if ev:
        line2_parts.append(f"EV:{ev}")
    if prob:
        line2_parts.append(f"P:{prob}")
    legacy = _get_val(context, ["legacy_message"])
    if legacy and legacy not in ("Research signal only.", "Live order path event.", "operator event", "exit", "startup"):
        line2_parts.append(f"Msg:{legacy}")
    if run_id:
        line2_parts.append(f"Run:{run_id}")
        
    line2 = " | ".join(line2_parts)
    return f"{line1}\n{line2}"


def _operator_exit_message(context: dict[str, Any]) -> str:
    market = _get_val(context, ["market", "asset", "ticker"], "SYSTEM")
    side = _get_val(context, ["side", "outcome"])
    pnl = _get_val(context, ["pnl", "pnl_usdc"])
    reason = _get_val(context, ["reason", "exit_reason"])
    
    hold = _get_val(context, ["hold_seconds", "hold"])
    hold_formatted = _format_hold_time(hold)
    
    entry_price = _get_val(context, ["entry_price"])
    exit_price = _get_val(context, ["exit_price", "price"])
    run_id = _short_run_id(context)
    
    if "YES" in side.upper():
        side = "YES"
    elif "NO" in side.upper():
        side = "NO"
        
    icon = "🟢" if _is_pnl_positive(pnl) else "🔴"
    
    line1 = f"{icon} CLOSE | {market} {side}"
    if pnl:
        line1 += f" | PnL:{pnl}"
    if reason:
        line1 += f" | {reason}"
        
    line2_parts = []
    if hold_formatted:
        line2_parts.append(f"Hold:{hold_formatted}")
    if entry_price:
        line2_parts.append(f"Entry:{entry_price}")
    if exit_price:
        line2_parts.append(f"Exit:{exit_price}")
    legacy = _get_val(context, ["legacy_message"])
    if legacy and legacy not in ("Research signal only.", "Live order path event.", "operator event", "exit", "startup"):
        line2_parts.append(f"Msg:{legacy}")
    if run_id:
        line2_parts.append(f"Run:{run_id}")
        
    line2 = " | ".join(line2_parts)
    return f"{line1}\n{line2}"


def _operator_risk_message(context: dict[str, Any]) -> str:
    reason = _get_val(context, ["reason", "event_type"])
    run_id = _short_run_id(context)
    state = _get_val(context, ["risk_state", "state"], "PAUSED")
    impact = _get_val(context, ["impact"])
    
    line1 = f"🚨 RISK | {reason}"
    if run_id:
        line1 += f" | Run:{run_id}"
        
    line2 = f"State:{state}"
    if impact:
        line2 += f" | Impact:{impact}"
    return f"{line1}\n{line2}"


def _operator_incident_message(kind: str, context: dict[str, Any]) -> str:
    run_id = _short_run_id(context)
    headline = _get_val(context, ["headline", "reason", "event_type"])
    subsystem = _get_val(context, ["subsystem", "module", "component"])
    impact = _get_val(context, ["impact"])
    cycle = _get_val(context, ["cycles", "cycle"])
    
    is_attr_fail = "attr" in headline.lower() or "attribution" in headline.lower() or "missing" in headline.lower()
    
    if is_attr_fail:
        failed_field = _get_val(context, ["failed_field", "field"], "candidate_trace_id")
        market = _get_val(context, ["market", "asset"])
        side = _get_val(context, ["side", "outcome"])
        
        line1 = f"🚨 ATTR_FAIL | {failed_field} missing"
        if run_id:
            line1 += f" | Run:{run_id}"
            
        line2 = f"Trade:{market} {side} | Action:stop/audit"
        return f"{line1}\n{line2}"
    else:
        error_type = subsystem or headline or "runtime_exception"
        action_hint = _get_val(context, ["action", "action_hint", "impact"], "check logs")
        
        line1 = f"🚨 ERROR | {error_type}"
        if run_id:
            line1 += f" | Run:{run_id}"
            
        line2 = ""
        if cycle:
            line2 += f"Cycle:{cycle} | "
        line2 += f"Action:{action_hint}"
        return f"{line1}\n{line2}"


def _operator_summary_message(context: dict[str, Any]) -> str:
    uptime = _get_val(context, ["uptime"])
    mode = _mode_label(context)
    run_id = _short_run_id(context)
    
    if uptime:
        cycles = _get_val(context, ["cycles"])
        open_count = _get_val(context, ["trade_opens", "opens", "open"], "0")
        closed_count = _get_val(context, ["trade_closes", "closes", "closed"], "0")
        pnl = _get_val(context, ["pnl", "pnl_usdc", "signal_pnl"], "+0.0000")
        
        line1 = f"🟢 ALIVE | {mode} | Up:{uptime}"
        if run_id:
            line1 += f" | Run:{run_id}"
            
        line2 = f"Cycle:{cycles} | Open:{open_count} | Closed:{closed_count} | PnL:{pnl}"
        return f"{line1}\n{line2}"
    else:
        trades = _get_val(context, ["trades", "trade_count"])
        wins = _get_val(context, ["wins", "w", "tp"])
        losses = _get_val(context, ["losses", "l", "sl"])
        
        win_rate = _get_val(context, ["win_rate", "wr"])
        if not win_rate and wins and losses:
            try:
                w_val = int(wins)
                l_val = int(losses)
                total = w_val + l_val
                if total > 0:
                    win_rate = f"{(w_val / total) * 100:.1f}"
            except Exception:
                pass
        if not win_rate:
            win_rate = "0.0"
            
        pnl = _get_val(context, ["pnl", "signal_pnl"])
        edge_pnl = _get_val(context, ["edge_pnl", "ev_edge_pnl", "ev_edge", "ev_pnl"], "0.0000")
        quarantine_count = _get_val(context, ["quarantine_count", "quar"], "0")
        
        line1 = f"📊 DAY | Trades:{trades} | W:{wins} L:{losses} | WR:{win_rate}%"
        line2 = f"PnL:{pnl} | EV_EDGE:{edge_pnl} | Quar:{quarantine_count}"
        return f"{line1}\n{line2}"


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


def notify_allowance_missing(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_allowance_missing(message, **context)


def notify_signing_not_ready(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_signing_not_ready(message, **context)


def notify_order_submitted(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_order_submitted(message, **context)


def notify_order_filled(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_order_filled(message, **context)


def notify_order_cancelled(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_order_cancelled(message, **context)


def notify_order_timeout_cancelled(message: str = "", **context: Any) -> AlertResult:
    return get_telegram_alert_layer().notify_order_timeout_cancelled(message, **context)
