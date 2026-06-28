from __future__ import annotations

import logging
import time
from typing import Any

LOGGER = logging.getLogger(__name__)


class TraderLifecycleHelper:
    """Helper containing extracted startup and shutdown lifecycle logic for PolymarketTrader."""

    def init_quant_event_logger(self, trader: Any) -> Any:
        try:
            from utils.quant_event_logger import QuantEventLogger
            ql = QuantEventLogger(mode=trader._runtime_mode(), source_module="polymarket.trader")
            try:
                from utils.runtime_event_stream import RuntimeEventStream
                ql.event_stream = RuntimeEventStream(
                    session_id=ql.run_id,
                    mode=trader._runtime_mode(),
                )
            except Exception as exc:
                LOGGER.warning("[OBSERVABILITY] RuntimeEventStream disabled: %s", exc)
            return ql
        except Exception as exc:
            LOGGER.warning("[OBSERVABILITY] QuantEventLogger disabled at startup: %s", exc)
            return None

    def init_telegram_alert_layer(self, trader: Any) -> Any:
        try:
            from utils.telegram_alerts import TelegramAlertLayer, emit_startup_config_telemetry
            run_id = str(getattr(trader.quant_events, "run_id", "") or "") or None
            layer = TelegramAlertLayer(
                telemetry_emit=trader._emit_telegram_route_telemetry,
                run_id=run_id,
            )
            emit_startup_config_telemetry(
                trader.settings,
                telemetry_emit=trader._emit_telegram_route_telemetry,
                run_id=run_id,
            )
            return layer
        except Exception as exc:
            LOGGER.warning("[OBSERVABILITY] Telegram alert layer disabled at startup: %s", exc)
            return None

    def ensure_connected(self, trader: Any) -> None:
        if trader._connected:
            return

        LOGGER.info(
            "Connecting to Polymarket CLOB client (paper_trading=%s) to fetch balance...",
            trader.settings.paper_trading,
        )
        if trader.settings.paper_trading:
            if trader.paper_stats.trades_simulated == 0 and abs(trader.bankroll_state.realized_pnl) < 0.0001:
                trader._paper_virtual_reference_balance = float(trader.settings.account_balance)
            if trader._paper_wallet_reference_enabled():
                LOGGER.info(
                    "[PAPER] Wallet reference startup sync active -- reading real wallet/CLOB balance once "
                    "to initialize paper virtual cash. Execution remains PAPER ONLY; NO LIVE ORDERS."
                )
                trader._refresh_wallet_reference_balance(force=True)
            else:
                LOGGER.info("[PAPER] Local simulation mode active -- skipping CLOB connect and live balance fetch.")
                trader._apply_balance(float(trader.settings.account_balance), refresh_wallet_reference=False)
                trader._paper_virtual_cash_initial = float(trader.bankroll_state.current_bankroll_for_sizing)
                trader._balance_source = "paper_virtual"
            if not trader._balance_wallet_address:
                trader._balance_wallet_address = trader._wallet_address_for_logs()
            LOGGER.info(
                "[WALLET CONNECTED] mode=paper connected=%s wallet_address=%s balance_source=%s execution=PAPER_ONLY",
                "reference_only" if trader._balance_source == "wallet_reference_paper" else "false",
                trader._balance_wallet_address or "not_configured",
                trader._balance_source,
            )
            LOGGER.info(
                "[USDC BALANCE] mode=paper source=%s balance=$%.4f wallet_bankroll=%s paper_cash=$%.4f "
                "paper_sizing_balance=$%.4f execution=PAPER_ONLY no_live_orders=true",
                trader._balance_source,
                trader.bankroll_state.current_cash_balance,
                (
                    f"${trader._wallet_reference_balance:.4f}"
                    if trader._wallet_reference_balance is not None
                    else "unavailable"
                ),
                trader.bankroll_state.current_cash_balance,
                trader.bankroll_state.current_bankroll_for_sizing,
            )
            LOGGER.info(
                "[PAPER BALANCE STARTUP] mode=paper paper_starting_balance_source=%s "
                "paper_wallet_sync_on_start=%s paper_wallet_sync_mode=%s "
                "live_wallet_reference_balance=%s paper_virtual_cash_initial=$%.4f fallback_used=%s",
                trader._paper_starting_balance_source_setting(),
                str(trader._paper_wallet_sync_on_start()).lower(),
                trader._paper_wallet_sync_mode(),
                (
                    f"${trader._wallet_reference_balance:.4f}"
                    if trader._wallet_reference_balance is not None
                    else "unavailable"
                ),
                trader._paper_virtual_cash_initial,
                str(trader._paper_startup_fallback_used).lower(),
            )
            trader._connected = True
            trader._maybe_emit_system_health(force=True, reason="startup_connected")
            return

        try:
            trader.client.connect()
            snapshot = trader._fetch_live_balance_snapshot()
            real_balance = snapshot.balance
            trader._record_balance_snapshot(snapshot)

            trader._apply_balance(real_balance, reset_starting_balance=True)
            LOGGER.info(
                "[WALLET CONNECTED] mode=live connected=true wallet_address=%s balance_source=%s",
                trader._balance_wallet_address,
                trader._balance_source,
            )
            LOGGER.info("Bankroll fetched: $%.4f", real_balance)
            if real_balance == 0:
                LOGGER.warning("Wallet Balance is $0.00. Orders will be skipped.")
            trader._log_wallet_startup_verification()
            trader._connected = True
            trader._maybe_emit_system_health(force=True, reason="startup_connected")
        except Exception:
            LOGGER.exception("Failed to connect to Polymarket CLOB. Using Default Bankroll.")
            trader._connected = False
            trader._maybe_emit_system_health(force=True, reason="startup_connect_failed")

    def call_shutdown_hook(self, trader: Any, hook: Any, *, join_timeout: float | None = None) -> None:
        if not callable(hook):
            return
        if join_timeout is None:
            hook()
            return
        try:
            hook(join_timeout=join_timeout)
        except TypeError:
            hook()

    def close(self, trader: Any, *, join_timeout: float | None = None) -> None:
        """Release trader-owned background resources without changing trading state."""
        if trader._shutdown_complete:
            return
        trader._shutdown_complete = True
        try:
            trader._emit_path_truth_shutdown_events()
        except Exception:
            pass
        try:
            close_ptb = getattr(trader.ptb_tracker, "close", None)
            trader._call_shutdown_hook(close_ptb, join_timeout=join_timeout)
        except Exception as exc:
            LOGGER.debug("[SHUTDOWN] PTB/oracle feed close failed: %s", exc)
        for module_name, attr_name in (
            ("polymarket.market_feed", "_feed"),
            ("polymarket.models.quant_indicators", "_quant_feed"),
        ):
            try:
                module = __import__(module_name, fromlist=[attr_name])
                feed = getattr(module, attr_name, None)
                stop_feed = getattr(feed, "stop", None)
                trader._call_shutdown_hook(stop_feed, join_timeout=join_timeout)
            except Exception as exc:
                LOGGER.debug("[SHUTDOWN] %s close failed: %s", module_name, exc)
        try:
            trader._maybe_emit_system_health(force=True, reason="shutdown")
        except Exception:
            pass
