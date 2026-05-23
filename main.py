from __future__ import annotations

import argparse
import inspect
import importlib.util
import json
import logging
import os
import re
import subprocess
import threading
from dataclasses import asdict
from pathlib import Path


from config.settings import get_settings
from crypto_scalper.live_runner import main as run_scalper
from utils.config_validator import (
    apply_validation_to_settings,
    build_paper_balance_debug_summary,
    build_startup_summary,
    validate_env,
)
from utils.logger import get_telegram_notifier, quiet_http_client_loggers_for_shutdown, setup_logger
from polymarket.signal import BACKTEST_WIN_RATE


LOGGER = logging.getLogger(__name__)


def _call_with_optional_ui(func, interval: int, ui_mode: str, fps_mode: str) -> int:
    """Call realtime runners with UI args while keeping old test monkeypatches valid."""
    params = inspect.signature(func).parameters
    if "ui_mode" in params or "fps_mode" in params:
        return func(interval, ui_mode=ui_mode, fps_mode=fps_mode)
    return func(interval)


DEPENDENCY_SPECS: tuple[dict[str, object], ...] = (
    {
        "label": "py-clob-client",
        "modules": ("py_clob_client_v2", "py_clob_client"),
        "install": "pip install py-clob-client",
        "features": ("orderbook", "bid/ask", "spread", "live order execution"),
    },
    {
        "label": "web3",
        "modules": ("web3",),
        "install": "pip install web3",
        "features": ("wallet balance", "USDC balance", "allowance", "Polygon RPC"),
    },
    {
        "label": "eth-account",
        "modules": ("eth_account",),
        "install": "pip install eth-account",
        "features": ("private key validation", "wallet address derivation", "CLOB signing"),
    },
)


def _dependency_available(module_names: tuple[str, ...]) -> bool:
    return any(importlib.util.find_spec(module_name) is not None for module_name in module_names)


def _build_dependency_report() -> list[dict[str, object]]:
    report: list[dict[str, object]] = []
    for spec in DEPENDENCY_SPECS:
        modules = tuple(str(item) for item in spec["modules"])
        report.append({
            "label": str(spec["label"]),
            "status": "OK" if _dependency_available(modules) else "MISSING",
            "install": str(spec["install"]),
            "features": tuple(str(item) for item in spec["features"]),
        })
    return report


def _missing_dependencies(report: list[dict[str, object]]) -> list[dict[str, object]]:
    return [item for item in report if item.get("status") != "OK"]


def _log_dependency_report(report: list[dict[str, object]]) -> None:
    LOGGER.info(
        "[DEPENDENCIES]\n%s",
        "\n".join(f"{item['label']}={item['status']}" for item in report),
    )
    for item in _missing_dependencies(report):
        LOGGER.warning(
            "[MISSING DEPENDENCY]\n%s not installed\nRequired for:\n- %s\n\nInstall:\n%s",
            item["label"],
            "\n- ".join(str(feature) for feature in item["features"]),
            item["install"],
        )


def _validate_dependencies_for_mode(mode: str) -> bool:
    report = _build_dependency_report()
    _log_dependency_report(report)
    missing = _missing_dependencies(report)
    if not missing:
        return True

    labels = ", ".join(str(item["label"]) for item in missing)
    if mode == "paper":
        LOGGER.warning("[DEPENDENCIES] paper mode continuing with reduced functionality: %s", labels)
        return True

    LOGGER.critical("[DEPENDENCIES] %s mode blocked until missing dependencies are installed: %s", mode, labels)
    return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PolyTrade Crypto Scalper.")
    parser.add_argument(
        "--mode",
        choices=["paper", "live", "polymarket", "scalper", "dashboard", "realtime", "polymarket-backtest", "polymarket-5m-dashboard", "polymarket-realtime", "polymarket-paper", "verify", "hft"],
        default="paper",
        help="Which subsystem to run. Default is safe paper mode; live runtime requires --mode live.",
    )

    parser.add_argument(
        "--scalper-mode",
        choices=["dry-run", "live"],
        default="dry-run",
        help="Runner mode when using --mode scalper.",
    )
    parser.add_argument(
        "--symbol",
        default="BTC/USDT",
        help="Trading pair for realtime mode, e.g. BTC/USDT or BTC/USD.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Scan interval in seconds for polymarket-realtime/polymarket-paper (default: 60).",
    )
    parser.add_argument(
        "--ui",
        choices=["auto", "compact", "standard", "wide", "fullscreen"],
        default="auto",
        help="Terminal dashboard layout mode for paper/live realtime modes (default: auto).",
    )
    parser.add_argument(
        "--fps",
        choices=["low", "medium", "high"],
        default="medium",
        help="Terminal dashboard refresh rate for paper/live realtime modes (default: medium).",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=60,
        help="Number of days of history for polymarket-backtest (default: 60).",
    )
    parser.add_argument(
        "--asset",
        default="BTC",
        help="Asset symbol for polymarket-backtest, e.g. BTC, ETH (default: BTC).",
    )
    parser.add_argument(
        "--min-edge",
        type=float,
        default=3.0,
        metavar="PCT",
        dest="min_edge",
        help="Minimum edge %% to enter a trade in backtest (default: 3.0). "
             "3.0=aggressive, 5.0=moderate, 8.0=conservative.",
    )
    parser.add_argument(
        "--balance",
        type=float,
        default=8.89,
        metavar="USD",
        help="Starting balance in USD for polymarket-backtest (default: 8.89).",
    )
    parser.add_argument(
        "--score-scale",
        action="store_true",
        default=False,
        dest="score_scale",
        help="Score-proportional bet sizing: score=0.95→2x, score=0.85→1.5x, score=0.50→1x.",
    )
    parser.add_argument(
        "--momentum-price",
        action="store_true",
        default=False,
        dest="momentum_price",
        help="Momentum-adjusted entry price: simulate buying counter-side at real discount "
             "when momentum is strong (e.g. BTC +0.60pct -> NO priced at ~0.44 not 0.50).",
    )
    return parser


def run_polymarket_mode() -> int:
    settings = get_settings()
    dep_mode = "paper" if settings.paper_trading else "live"
    if not _validate_dependencies_for_mode(dep_mode):
        return 1

    from polymarket.trader import PolymarketTrader

    trader = PolymarketTrader()
    LOGGER.info("Starting PolyTrade Crypto Scalper trading cycle (paper_trading=%s).", trader.settings.paper_trading)
    outcomes = trader.run_single_cycle(top_n=7)

    for outcome in outcomes:
        if outcome.skipped:
            LOGGER.info("[SKIP] %s — %s", outcome.market_id, outcome.skip_reason)
        else:
            order_id = outcome.receipt.order_id if outcome.receipt else "none"
            LOGGER.info(
                "[TRADE] %s | decision=%s confidence=%.2f order=%s",
                outcome.market_id,
                outcome.decision,
                outcome.confidence,
                order_id,
            )

    print(json.dumps(
        [
            {
                "market_id": o.market_id,
                "question": o.question,
                "decision": o.decision,
                "confidence": o.confidence,
                "skipped": o.skipped,
                "skip_reason": o.skip_reason,
                "order_id": o.receipt.order_id if o.receipt else None,
                "order_status": o.receipt.status if o.receipt else None,
            }
            for o in outcomes
        ],
        indent=2,
    ))
    return 0


def run_polymarket_backtest(
    days: int = 60, asset: str = "BTC", min_edge: float = 3.0,
    balance: float = 8.89, score_scale: bool = False, momentum_price: bool = False,
) -> int:
    from polymarket.backtester_5m import main_runner
    assets = [a.strip().upper() for a in asset.split(",")]
    if len(assets) == 1:
        LOGGER.info(
            "Starting polymarket-backtest | asset=%s days=%d balance=$%.2f "
            "min_edge=%.1f%% score_scale=%s momentum_price=%s",
            assets[0], days, balance, min_edge, score_scale, momentum_price,
        )
        return main_runner(days=days, asset=assets[0], initial_balance=balance,
                           min_edge_pct=min_edge, score_scale=score_scale,
                           momentum_price=momentum_price)

    # Multi-asset: split capital evenly, run each asset separately
    LOGGER.info(
        "Starting multi-asset backtest | assets=%s days=%d balance=$%.2f "
        "min_edge=%.1f%% score_scale=%s momentum_price=%s",
        assets, days, balance, min_edge, score_scale, momentum_price,
    )
    per_asset_balance = balance / len(assets)
    for a in assets:
        LOGGER.info("  Running %s (balance=$%.2f) ...", a, per_asset_balance)
        main_runner(days=days, asset=a, initial_balance=per_asset_balance,
                    min_edge_pct=min_edge, score_scale=score_scale,
                    momentum_price=momentum_price)

    LOGGER.info("Multi-asset backtest complete. Check backtest_results/polymarket_5m/ for per-asset results.")
    return 0


def _log_paper_mode_banner(settings=None) -> None:
    legacy_source = str(getattr(settings, "paper_balance_source", "virtual") or "virtual").strip().lower()
    starting_source = str(getattr(settings, "paper_starting_balance_source", "") or "").strip().lower()
    if not starting_source:
        starting_source = "live_wallet_reference" if legacy_source == "wallet_reference" else "config"
    if starting_source == "wallet_reference":
        starting_source = "live_wallet_reference"
    sync_on_start = bool(getattr(settings, "paper_wallet_sync_on_start", True))
    sync_mode = str(getattr(settings, "paper_wallet_sync_mode", "initialize_only") or "initialize_only")
    if starting_source == "live_wallet_reference" and sync_on_start:
        sizing_source = "paper_virtual (initialized once from live wallet reference)"
    else:
        sizing_source = "paper_virtual (isolated virtual cash)"
    LOGGER.warning(
        "\n================="
        "\nPAPER MODE"
        "\nReal Market Data: ON"
        "\nLive Orders: OFF"
        "\nSimulated Execution: ON"
        "\nWallet Risk: NONE"
        "\nExecution: PAPER ONLY"
        "\nPaper Starting Balance Source: %s"
        "\nPaper Wallet Sync On Start: %s"
        "\nPaper Wallet Sync Mode: %s"
        "\nSizing Source: %s"
        "\n=================",
        starting_source,
        str(sync_on_start).lower(),
        sync_mode,
        sizing_source,
    )


def _shutdown_realtime_resources(
    *,
    trader,
    rl_logger,
    console_handlers: list[logging.Handler],
    root_log: logging.Logger,
    shutdown_requested: bool,
    cycle_num: int,
    stop_scheduler=None,
) -> None:
    """Quiet and stop realtime-owned resources before console output is restored."""
    quiet_http_client_loggers_for_shutdown()
    try:
        trader.shutdown()
    except Exception as exc:
        LOGGER.debug("[SHUTDOWN] trader shutdown failed: %s", exc)
    try:
        trader.log_paper_session_summary()
    finally:
        try:
            rl_logger.force_save_summary()
        except Exception as exc:
            LOGGER.debug("[SHUTDOWN] realtime logger close failed: %s", exc)
        try:
            if stop_scheduler is None:
                from daily_report import stop_scheduler as stop_scheduler_func
            else:
                stop_scheduler_func = stop_scheduler
            stop_scheduler_func(join_timeout=1.0)
        except Exception as exc:
            LOGGER.debug("[SHUTDOWN] daily report scheduler stop failed: %s", exc)
        for handler in console_handlers:
            root_log.addHandler(handler)

    if shutdown_requested:
        LOGGER.info("[SHUTDOWN] Ctrl+C received; runtime stopped cleanly after %s cycles.", cycle_num)
    else:
        LOGGER.info("polymarket-realtime stopped after %s cycles.", cycle_num)


def run_polymarket_realtime(
    interval: int,
    force_paper: bool = True,
    ui_mode: str = "auto",
    fps_mode: str = "medium",
) -> int:
    import signal
    import time
    from datetime import datetime, timezone
    from logging.handlers import RotatingFileHandler

    settings = get_settings()
    if force_paper:
        settings.paper_trading = True
        settings.dry_run = True
        LOGGER.warning("[PAPER_MODE] Forced paper trading enabled. No real orders will be placed.")
    if settings.paper_trading:
        _log_paper_mode_banner(settings)
    dep_mode = "paper" if settings.paper_trading else "live"
    if not _validate_dependencies_for_mode(dep_mode):
        return 1

    from polymarket.trader import PolymarketTrader
    from polymarket.realtime_logger import RealtimeLogger, ScanRecord
    from utils.display import PolymarketRealtimeDisplay

    trader   = PolymarketTrader()
    cadence_config = getattr(trader, "set_runtime_cadence_observability", None)
    if callable(cadence_config):
        cadence_config(
            configured_decision_interval_seconds=interval,
            decision_loop_target_seconds=1.0,
            snapshot_sampling_interval_seconds=5.0,
            market_discovery_interval_seconds=15.0,
            outer_loop_poll_interval_seconds=0.25,
        )

    # Pre-fetch balance so the display and logger start with correct data
    LOGGER.info("Fetching initial bankroll...")
    trader._ensure_connected()
    
    if not trader._connected:
        LOGGER.error("CRITICAL: Failed to connect to Polymarket! Please check your POLYMARKET_PRIVATE_KEY and POLYMARKET_FUNDER in .env.")
        LOGGER.error("Setting display balance to $0.00 to indicate connection failure.")
        trader._apply_balance(0.0)
    
    rl_logger = RealtimeLogger(initial_balance=settings.account_balance)
    display  = PolymarketRealtimeDisplay(
        paper_trading  = settings.paper_trading,
        interval       = interval,
        snipe_min_edge = settings.snipe_min_edge,
        ui_mode        = ui_mode,
        fps_mode       = fps_mode,
    )

    stop       = threading.Event()
    cycle_num  = 0
    shutdown_requested = False

    def _handle_sigint(*_args: object) -> None:
        nonlocal shutdown_requested
        shutdown_requested = True
        stop.set()

    signal.signal(signal.SIGINT, _handle_sigint)

    # Identify console handlers (everything that is NOT a file handler).
    # We remove them before entering the Live screen so their output does not
    # bleed into the Rich display, then restore them on exit.
    root_log = logging.getLogger()
    _console_handlers = [
        h for h in root_log.handlers
        if not isinstance(h, (logging.FileHandler, RotatingFileHandler))
    ]

    LOGGER.info(
        "polymarket-realtime started | interval=%ds paper=%s snipe_edge=%.0f%%",
        interval, settings.paper_trading, settings.snipe_min_edge * 100,
    )
    tg = get_telegram_notifier()
    if tg:
        mode = "PAPER" if settings.paper_trading else "LIVE"
        status = "CONNECTED" if trader._connected else "CONNECTION_FAILED"
        from utils.telegram_reporter import build_startup_alert
        wallet = settings.polymarket_proxy_wallet or settings.polymarket_funder
        portfolio = trader.dashboard_portfolio_state()
        tg.send_message(build_startup_alert(
            mode=mode,
            status=status,
            interval=interval,
            bankroll=float(portfolio.get("sizing_bankroll", settings.account_balance)),
            paper=settings.paper_trading,
            wallet=wallet,
            balance_source=str(portfolio.get("balance_source", "paper_virtual")),
            wallet_balance=portfolio.get("wallet_reference_balance"),
            paper_cash=float(portfolio.get("paper_cash", portfolio.get("cash", settings.account_balance))),
            execution_mode=str(portfolio.get("execution_mode", "PAPER ONLY" if settings.paper_trading else "LIVE")),
            wallet_reference_error=str(portfolio.get("wallet_reference_error", "") or ""),
            gas_note="Required for LIVE orders on Polygon",
            snipe_min_edge=settings.snipe_min_edge,
            floor=settings.bankroll_floor,
            daily_dd_limit=settings.max_daily_drawdown,
            max_open_positions=settings.max_open_positions,
        ))

    try:
        from daily_report import run_scheduler
        run_scheduler()
    except Exception as e:
        LOGGER.warning("Could not start daily report scheduler: %s", e)

    for h in _console_handlers:
        root_log.removeHandler(h)

    with display:
        last_cycle = time.monotonic() - interval  # fire immediately on first loop

        last_tick = 0.0
        last_orderbook_tick = 0.0
        last_balance_tick = 0.0

        while not stop.is_set():
            now_mono = time.monotonic()
            elapsed  = now_mono - last_cycle
            next_in  = max(0, int(interval - elapsed))
            display.update_countdown(next_in)

            # ── REALTIME LOOP (every 1s) ── Oracle prices + countdown refresh ──
            if now_mono - last_tick >= 1.0:
                last_tick = now_mono

                if now_mono - last_balance_tick >= 30.0:
                    last_balance_tick = now_mono
                    try:
                        trader.refresh_live_balance()
                    except Exception as exc:
                        LOGGER.warning("[BALANCE_REFRESH] Failed: %s", exc)
                    display.update_portfolio(trader.dashboard_portfolio_state())
                    display.update_session_summary(trader.dashboard_session_summary())
                    display.update_recent_trades(trader.get_recent_display_trades())

                # Compute 5-minute window clock once (same for all assets)
                now_ts   = int(time.time())
                epoch    = now_ts - (now_ts % 300)
                countdown = max(0, epoch + 300 - now_ts)
                win_start = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%H:%M")
                win_end   = datetime.fromtimestamp(epoch + 300, tz=timezone.utc).strftime("%H:%M")
                window_ts = f"{win_start}-{win_end}"

                ticker_updates: dict[str, dict] = {}
                for ticker in display._TICKERS:
                    state  = trader.ptb_tracker.get_state(ticker)
                    symbol = f"pm-5m-{ticker.lower()}"

                    trader.tracker.update_polymarket_unrealized(symbol, state.is_above_ptb)
                    trader.enforce_pre_close_exits(countdown)
                    if countdown <= 5:
                        trader.settle_and_record(symbol, state.is_above_ptb)

                    ticker_updates[ticker] = {
                        "ref_price":     state.price_to_beat,
                        "current_price": state.current_price,
                        "is_above":      state.is_above_ptb,
                        "price_diff":    state.price_diff_pct,
                        "countdown":     countdown,
                        "window_ts":     window_ts,
                    }
                    quant_detail = trader.last_quant_details.get(ticker, {})
                    if quant_detail:
                        ticker_updates[ticker].update({
                            "p_yes":       quant_detail.get("p_yes", 0.0),
                            "p_no":        quant_detail.get("p_no", 0.0),
                            "ev":          quant_detail.get("ev", 0.0),
                            "min_ev":      quant_detail.get("min_ev", 0.0),
                            "delta_regime": quant_detail.get("delta_regime", "--"),
                            "delta_multiplier": quant_detail.get("delta_multiplier", 0.0),
                            "skip_reason": quant_detail.get("skip_reason", ""),
                            "score":       quant_detail.get("score", 0.0),
                            "ask_price":   quant_detail.get("ask_price", 0.0),
                            "final_size":  quant_detail.get("final_size", 0.0),
                            "frequency_multiplier": quant_detail.get("frequency_multiplier", 0.0),
                            "decision":    quant_detail.get("decision", "SKIP"),
                        })
                    else:
                        ticker_updates[ticker].update({
                            "skip_reason": "model_not_run",
                            "decision": "SKIP",
                        })

                if now_mono - last_orderbook_tick >= 5.0:
                    last_orderbook_tick = now_mono
                    for ticker in display._TICKERS:
                        sig = trader.last_signals.get(ticker)
                        outcome = sig.side if sig and sig.side in ("YES", "NO") else "YES"
                        confidence = sig.score if sig and sig.score > 0 else BACKTEST_WIN_RATE
                        metrics = trader.get_market_display_metrics(
                            ticker=ticker,
                            outcome=outcome,
                            confidence=confidence,
                        )
                        ticker_updates.setdefault(ticker, {}).update({
                            "bid":         metrics.bid,
                            "ask":         metrics.ask,
                            "spread":      metrics.spread,
                            "snipe_score": metrics.snipe_score,
                            "edge_pct":    metrics.edge_pct,
                            "p_yes":       metrics.p_yes,
                            "p_no":        metrics.p_no,
                            "model_p_yes": metrics.p_yes,
                            "model_p_no":  metrics.p_no,
                            "yes_bid":     metrics.yes_bid,
                            "yes_ask":     metrics.yes_ask,
                            "no_bid":      metrics.no_bid,
                            "no_ask":      metrics.no_ask,
                            "yes_mid":     metrics.yes_mid,
                            "no_mid":      metrics.no_mid,
                            "clob_source": metrics.clob_source,
                            "orderbook_age_ms": metrics.orderbook_age_ms,
                            "yes_orderbook_age_ms": metrics.yes_orderbook_age_ms,
                            "no_orderbook_age_ms": metrics.no_orderbook_age_ms,
                            "token_id":    metrics.token_id,
                            "yes_token_id": metrics.yes_token_id,
                            "no_token_id": metrics.no_token_id,
                            "condition_id": metrics.condition_id,
                            "market_slug": metrics.market_slug,
                            "outcome":     metrics.outcome,
                            "token_mapping_warning": metrics.token_mapping_warning,
                            "ev":          metrics.ev,
                            "min_ev":      metrics.min_ev,
                            "delta_regime": metrics.delta_regime,
                            "delta_multiplier": metrics.delta_multiplier,
                            "skip_reason": metrics.skip_reason,
                            "score":       metrics.score,
                            "ask_price":   metrics.ask_price,
                            "final_size":  metrics.final_size,
                            "frequency_multiplier": metrics.frequency_multiplier,
                            # Research Cockpit wiring v1 — display-only, no trading effect
                            "liquidity_state":        metrics.liquidity_state,
                            "market_regime":          sig.market_regime if sig else "UNKNOWN",
                            "signal_volatility_score": sig.volatility_score if sig else 0.0,
                        })
                        LOGGER.debug(
                            "[DASHBOARD_PAYLOAD] ticker=%s yes_bid=%.4f yes_ask=%.4f no_bid=%.4f no_ask=%.4f spread=%.4f model_p_yes=%s model_p_no=%s ev=%s min_ev=%s delta=%s x%s age_ms=%s reason=%s",
                            ticker,
                            metrics.yes_bid,
                            metrics.yes_ask,
                            metrics.no_bid,
                            metrics.no_ask,
                            metrics.spread,
                            metrics.p_yes,
                            metrics.p_no,
                            metrics.ev,
                            metrics.min_ev,
                            metrics.delta_regime,
                            metrics.delta_multiplier,
                            metrics.orderbook_age_ms,
                            metrics.skip_reason,
                        )
                        if settings.arb_display_enabled:
                            arb = trader.get_arbitrage_opportunity(ticker)
                            arb_data = asdict(arb)
                            arb_data.pop("ticker", None)
                            display.update_arbitrage(ticker, **arb_data)

                display.update_realtime_batch(ticker_updates)

                # v3.1: Panic Sell check (every second when countdown <= 20s)
                trader.panic_sell_check(countdown)

                # v3.1: Take Profit check (every second — catch profits early)
                trader.check_take_profit(countdown)

                # v3.5: Stop Loss check (every second)
                trader.check_stop_loss(countdown)

                # Push WebSocket sync status
                ws_status = trader.ptb_tracker._feed.get_ws_sync_status()
                display.update_ws_status(ws_status)

                # Log a compact oracle line for active markets only (file log only — console removed).
                active_bits = []
                for ticker in display._TICKERS:
                    item = ticker_updates.get(ticker, {})
                    edge = display._markets[ticker].get("edge_pct") or 0.0
                    active_bits.append(
                        f"{ticker} PTB=${float(item.get('ref_price', 0.0)):,.2f} "
                        f"Oracle=${float(item.get('current_price', 0.0)):,.2f} "
                        f"Edge={float(edge) * 100:.2f}%"
                    )
                LOGGER.info("[REALTIME 1s] %s | Countdown: %ds", " | ".join(active_bits), countdown)

            if elapsed >= interval:
                last_cycle = time.monotonic()
                cycle_num += 1

                LOGGER.info("[PM-REALTIME] Cycle #%s starting", cycle_num)

                # ── Run full AI + execution cycle ──────────────────────────
                try:
                    outcomes = trader.run_single_cycle(top_n=7)
                except Exception:
                    LOGGER.exception("Cycle #%s raised an exception — skipping.", cycle_num)
                    outcomes = []

                # ── Refresh portfolio after cycle ──────────────────────────
                display.update_portfolio(trader.dashboard_portfolio_state())
                display.update_session_summary(trader.dashboard_session_summary())
                # Research Cockpit v1: probe counts (in-memory only, no disk read)
                display.update_research_obs(**trader.dashboard_probe_counts())

                # ── Update per-market state and build cycle result list ────
                cycle_results: list[dict] = []

                for outcome in outcomes:
                    ticker = outcome.market_id.replace("pm-5m-", "").upper()

                    decision  = "rejected" if outcome.skipped else "approved"
                    notional  = outcome.risk_plan.notional_size if outcome.risk_plan else 0.0
                    signal    = "long" if outcome.decision == "buy" else "flat" if outcome.skipped else "wait"

                    # Only call AI and Risk for open slots, but update display with latest fetched ptb
                    ptb_info = trader.ptb_tracker.get_market_ptb(ticker)

                    sig = trader.last_signals.get(ticker)
                    display_outcome = "NO" if outcome.decision == "sell" else "YES"
                    if outcome.skipped and sig and sig.side in ("YES", "NO"):
                        display_outcome = sig.side
                    display_confidence = (
                        outcome.confidence
                        if outcome.confidence > 0
                        else sig.score if sig and sig.score > 0
                        else BACKTEST_WIN_RATE
                    )
                    metrics = trader.get_market_display_metrics(
                        ticker=ticker,
                        outcome=display_outcome,
                        confidence=display_confidence,
                    )

                    display.update_market(
                        ticker,
                        ref_price     = ptb_info.price_to_beat,
                        current_price = ptb_info.current_price,
                        is_above      = ptb_info.is_above_ptb,
                        price_diff    = ptb_info.price_diff_pct,
                        bid           = metrics.bid,
                        ask           = metrics.ask,
                        spread        = metrics.spread,
                        snipe_score   = metrics.snipe_score,
                        edge_pct      = metrics.edge_pct,
                        p_yes         = metrics.p_yes,
                        p_no          = metrics.p_no,
                        model_p_yes   = metrics.p_yes,
                        model_p_no    = metrics.p_no,
                        yes_bid       = metrics.yes_bid,
                        yes_ask       = metrics.yes_ask,
                        no_bid        = metrics.no_bid,
                        no_ask        = metrics.no_ask,
                        yes_mid       = metrics.yes_mid,
                        no_mid        = metrics.no_mid,
                        clob_source   = metrics.clob_source,
                        orderbook_age_ms = metrics.orderbook_age_ms,
                        yes_orderbook_age_ms = metrics.yes_orderbook_age_ms,
                        no_orderbook_age_ms = metrics.no_orderbook_age_ms,
                        token_id      = metrics.token_id,
                        yes_token_id  = metrics.yes_token_id,
                        no_token_id   = metrics.no_token_id,
                        condition_id  = metrics.condition_id,
                        market_slug   = metrics.market_slug,
                        outcome       = metrics.outcome,
                        token_mapping_warning = metrics.token_mapping_warning,
                        ev            = metrics.ev,
                        min_ev        = metrics.min_ev,
                        delta_regime  = metrics.delta_regime,
                        delta_multiplier = metrics.delta_multiplier,
                        skip_reason   = metrics.skip_reason or outcome.display.get("skip_reason", ""),
                        score         = metrics.score,
                        ask_price     = metrics.ask_price,
                        final_size    = metrics.final_size,
                        frequency_multiplier = metrics.frequency_multiplier,
                        signal        = signal,
                        confidence    = outcome.confidence,
                        decision      = outcome.display.get("decision", "SKIP" if outcome.skipped else "ENTER"),
                        size          = notional,
                        # Research Cockpit wiring v1 — display-only, no trading effect
                        liquidity_state        = metrics.liquidity_state,
                        market_regime          = sig.market_regime if sig else "UNKNOWN",
                        signal_volatility_score = sig.volatility_score if sig else 0.0,
                    )

                    # Record trade in display if order was placed
                    if not outcome.skipped and outcome.receipt and outcome.risk_plan:
                        rp = outcome.risk_plan
                        display.add_trade(
                            ticker   = ticker,
                            side     = str(outcome.display.get("side", outcome.decision.upper())),
                            price    = rp.entry_price,
                            size     = rp.notional_size,
                            notional = rp.notional_size,
                            status   = outcome.receipt.status,
                            reason   = "entry",
                            mode     = str(outcome.display.get("mode", "--")),
                        )

                    cycle_results.append({
                        "ticker":      ticker,
                        "decision":    decision,
                        "confidence":  outcome.confidence,
                        "skipped":     outcome.skipped,
                        "snipe_score": metrics.snipe_score,
                        "skip_reason": outcome.display.get("skip_reason", outcome.skip_reason),
                        "ev":          outcome.display.get("ev", metrics.ev),
                        "min_ev":      outcome.display.get("min_ev", metrics.min_ev),
                    })

                    # ── Write scan record to CSV log ──────────────────────────
                    now_utc    = datetime.now(timezone.utc)
                    sig        = trader.last_signals.get(ticker)
                    rl_logger.log_scan(ScanRecord(
                        timestamp_utc  = now_utc.isoformat(),
                        date_th        = now_utc.strftime("%d/%m/%Y"),
                        time_th        = now_utc.strftime("%H:%M:%S"),
                        asset          = ticker,
                        feed           = "polymarket-5m",
                        decision       = decision,
                        confidence     = outcome.confidence,
                        edge           = sig.score if sig else 0.0,
                        momentum_pct   = sig.momentum_pct if sig else 0.0,
                        score          = sig.score if sig else 0.0,
                        signal         = sig.side if sig else "SKIP",
                        position_size  = notional,
                        order_id       = outcome.receipt.order_id if outcome.receipt else "",
                        order_status   = outcome.receipt.status if outcome.receipt else "skipped",
                        skip_reason    = outcome.skip_reason or "",
                        daily_pnl_pct  = (
                            (settings.account_balance - rl_logger.start_of_day_balance)
                            / max(rl_logger.start_of_day_balance, 0.01)
                        ),
                        bankroll       = settings.account_balance,
                        raw_skip_reason = str(outcome.display.get("raw_skip_reason", outcome.skip_reason or "")),
                        normalized_skip_reason = str(outcome.display.get("normalized_skip_reason", "")),
                        seconds_remaining = int(outcome.display.get("seconds_remaining", ptb_info.seconds_remaining) or 0),
                        entry_cutoff_seconds = int(outcome.display.get("entry_cutoff_seconds", settings.execution_entry_cutoff_seconds) or 0),
                        time_bucket = str(outcome.display.get("time_bucket", "")),
                        epoch_start = str(outcome.display.get("epoch_start", getattr(ptb_info, "epoch_start_ts", "")) or ""),
                        market_start_time = str(outcome.display.get("market_start_time", "")),
                        market_end_time = str(outcome.display.get("market_end_time", "")),
                        token_id = str(outcome.display.get("token_id", "")),
                        outcome = str(outcome.display.get("outcome", "")),
                        source_module = str(outcome.display.get("source_module", "polymarket.trader")),
                        market_slug = str(outcome.display.get("market_slug", "")),
                        condition_id = str(outcome.display.get("condition_id", "")),
                        orderbook_age_ms = int(outcome.display.get("orderbook_age_ms", 0) or 0),
                        oracle_age_ms = int(outcome.display.get("oracle_age_ms", 0) or 0),
                        market_feed_age_ms = int(outcome.display.get("market_feed_age_ms", 0) or 0),
                        token_mapping_warning = str(outcome.display.get("token_mapping_warning", "")),
                    ))

                display.update_cycle(cycle_results, cycle_num)
                display.update_recent_trades(trader.get_recent_display_trades())
                display.update_session_summary(trader.dashboard_session_summary())



            time.sleep(0.25)

    _shutdown_realtime_resources(
        trader=trader,
        rl_logger=rl_logger,
        console_handlers=_console_handlers,
        root_log=root_log,
        shutdown_requested=shutdown_requested,
        cycle_num=cycle_num,
    )
    return 0


def run_polymarket_paper(interval: int = 15, ui_mode: str = "auto", fps_mode: str = "medium") -> int:
    params = inspect.signature(run_polymarket_realtime).parameters
    if "ui_mode" in params or "fps_mode" in params:
        return run_polymarket_realtime(interval=interval, force_paper=True, ui_mode=ui_mode, fps_mode=fps_mode)
    return run_polymarket_realtime(interval=interval, force_paper=True)


def run_polymarket_live(interval: int = 60, ui_mode: str = "auto", fps_mode: str = "medium") -> int:
    LOGGER.warning("[LIVE_MODE] Explicit --mode live selected. Running live readiness preflight before realtime loop.")
    preflight_code = run_verify_mode()
    if preflight_code != 0:
        LOGGER.error("[LIVE_MODE_BLOCKED] Readiness preflight failed. Live realtime loop was not started.")
        return preflight_code
    settings = get_settings()
    settings.paper_trading = False
    settings.dry_run = False
    return run_polymarket_realtime(interval=interval, force_paper=False, ui_mode=ui_mode, fps_mode=fps_mode)


SENSITIVE_ENV_NAMES = {
    "POLYMARKET_API_KEY",
    "POLYMARKET_API_SECRET",
    "POLYMARKET_API_PASSPHRASE",
    "POLYMARKET_PRIVATE_KEY",
    "PRIVATE_KEY",
    "SIGNER_PRIVATE_KEY",
    "TELEGRAM_BOT_TOKEN",
}


def _mask_secret(value: object, *, prefix: int = 6, suffix: int = 4) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        return "missing"
    if len(text) <= prefix + suffix:
        return f"{text[:2]}...{text[-2:]}" if len(text) > 4 else "<masked>"
    return f"{text[:prefix]}...{text[-suffix:]}"


def _load_dotenv_explicit(env_path: Path | None = None) -> dict[str, str]:
    env_path = env_path or Path(".env")
    loaded: dict[str, str] = {}
    try:
        from dotenv import dotenv_values, load_dotenv

        load_dotenv(dotenv_path=env_path, override=False)
        loaded = {str(k): str(v) for k, v in dotenv_values(env_path).items() if k and v is not None}
    except Exception:
        if env_path.exists():
            for raw in env_path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                loaded[key] = value
                os.environ.setdefault(key, value)
    return loaded


def _env_value(names: tuple[str, ...], loaded_env: dict[str, str]) -> tuple[str, str]:
    for name in names:
        value = os.environ.get(name)
        if value is None:
            value = loaded_env.get(name)
        if value is not None and str(value).strip():
            return name, str(value).strip()
    return names[0], ""


def _valid_evm_address(value: str) -> bool:
    return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", value or ""))


def _valid_private_key(value: str) -> bool:
    clean = (value or "").strip()
    if clean.startswith("0x"):
        clean = clean[2:]
    return bool(re.fullmatch(r"[a-fA-F0-9]{64}", clean))


def _derive_private_key_address(private_key: str) -> tuple[str, str]:
    if not private_key:
        return "", "MISSING"
    if not _valid_private_key(private_key):
        return "", "MALFORMED"
    try:
        from eth_account import Account  # type: ignore

        return str(Account.from_key(private_key).address), "OK"
    except ImportError:
        return "", "SKIPPED"
    except Exception:
        return "", "MALFORMED"


def _build_env_verification(loaded_env: dict[str, str]) -> dict[str, object]:
    checks: list[dict[str, str]] = []
    warnings: list[str] = []
    critical: list[str] = []

    def add_warning(code: str, *, critical_error: bool = False) -> None:
        if code not in warnings:
            warnings.append(code)
        if critical_error and code not in critical:
            critical.append(code)

    def check(
        label: str,
        aliases: tuple[str, ...],
        *,
        sensitive: bool = False,
        validator=None,
        required: bool = True,
    ) -> tuple[str, str, str]:
        source, value = _env_value(aliases, loaded_env)
        if not value:
            status = "missing" if required else "disabled"
            if required:
                add_warning("missing_env", critical_error=True)
            rendered = "missing"
        elif validator and not validator(value):
            status = "malformed"
            rendered = _mask_secret(value) if sensitive else value
            add_warning("malformed_env", critical_error=True)
        else:
            status = "loaded"
            rendered = _mask_secret(value) if sensitive or label in SENSITIVE_ENV_NAMES else value
        checks.append({"label": label, "source": source, "status": status, "value": rendered})
        return source, value, status

    check("POLYMARKET_API_KEY", ("POLYMARKET_API_KEY",), sensitive=True)
    check("POLYMARKET_API_SECRET", ("POLYMARKET_API_SECRET",), sensitive=True)
    check("POLYMARKET_API_PASSPHRASE", ("POLYMARKET_API_PASSPHRASE",), sensitive=True)
    _, private_key, private_status = check(
        "PRIVATE_KEY",
        ("PRIVATE_KEY", "POLYMARKET_PRIVATE_KEY", "SIGNER_PRIVATE_KEY"),
        sensitive=True,
        validator=_valid_private_key,
    )
    wallet_source, wallet_address, wallet_status = check(
        "WALLET_ADDRESS",
        ("WALLET_ADDRESS", "POLYMARKET_PROXY_WALLET", "POLYMARKET_FUNDER"),
        sensitive=True,
        validator=_valid_evm_address,
    )
    rpc_source, rpc_url, rpc_status = check("RPC_URL", ("RPC_URL", "ALCHEMY_URL", "POLYGON_RPC_URL"), sensitive=True)

    def valid_chain_id(value: str) -> bool:
        try:
            return int(value) > 0
        except (TypeError, ValueError):
            return False

    _, chain_id, chain_status = check("CHAIN_ID", ("CHAIN_ID", "POLYMARKET_CHAIN_ID"), validator=valid_chain_id)

    telegram_enabled = (os.environ.get("TELEGRAM_ENABLED") or loaded_env.get("TELEGRAM_ENABLED") or "").lower() in {"1", "true", "yes", "on"}
    token_name, telegram_token = _env_value(("TELEGRAM_BOT_TOKEN",), loaded_env)
    chat_name, telegram_chat = _env_value(("TELEGRAM_CHAT_ID",), loaded_env)
    if telegram_enabled or telegram_token or telegram_chat:
        check("TELEGRAM_BOT_TOKEN", (token_name,), sensitive=True)
        check("TELEGRAM_CHAT_ID", (chat_name,), sensitive=True)
        if not telegram_token or not telegram_chat:
            add_warning("missing_env")

    derived_address, derived_status = _derive_private_key_address(private_key)
    explicit_wallet = _env_value(("WALLET_ADDRESS",), loaded_env)[1]
    wallet_match = "UNKNOWN"
    if derived_status == "OK" and explicit_wallet:
        wallet_match = str(derived_address.lower() == explicit_wallet.lower()).upper()
        if wallet_match != "TRUE":
            add_warning("wallet_mismatch", critical_error=True)
    elif derived_status in {"MALFORMED", "MISSING"}:
        add_warning("malformed_env" if private_status == "malformed" else "missing_env", critical_error=True)

    chain_match = "UNKNOWN"
    if chain_status == "loaded":
        chain_match = str(int(chain_id) == 137).upper()
        if chain_match != "TRUE":
            add_warning("chain_mismatch", critical_error=True)

    if rpc_status == "loaded":
        try:
            from web3 import Web3  # type: ignore

            w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 5}))
            rpc_chain_id = int(w3.eth.chain_id)
            rpc_status = "OK"
            if rpc_chain_id != 137:
                add_warning("chain_mismatch", critical_error=True)
        except ImportError:
            rpc_status = "SKIPPED"
        except Exception:
            rpc_status = "FAIL"
            add_warning("rpc_unreachable", critical_error=True)

    return {
        "checks": checks,
        "warnings": warnings,
        "critical": critical,
        "wallet": {
            "configured": wallet_address,
            "configured_source": wallet_source,
            "derived": derived_address,
            "derived_status": derived_status,
            "match": wallet_match,
            "network": "Polygon",
            "chain_id": chain_id if chain_id else "--",
            "chain_match": chain_match,
            "rpc_source": rpc_source,
            "rpc_status": rpc_status,
            "wallet_status": wallet_status,
        },
    }


def run_verify_mode() -> int:
    loaded_env = _load_dotenv_explicit()
    get_settings.cache_clear()
    env_report = _build_env_verification(loaded_env)
    for item in env_report["checks"]:
        LOGGER.info(
            "[ENV]\n%s=%s %s%s",
            item["label"],
            item["status"],
            item["value"],
            "" if item["source"] == item["label"] else f" source={item['source']}",
        )

    if not _validate_dependencies_for_mode("verify"):
        return 1

    from polymarket.trader import PolymarketTrader

    trader = PolymarketTrader()
    report = trader.verify_account_readiness()

    api = report["api"]
    LOGGER.info(
        "[VERIFY API]\nauth=%s latency=%sms endpoint=%s websocket=%s api_key=%s api_secret=%s",
        api.get("auth", "FAIL"),
        api.get("latency_ms", "--"),
        api.get("endpoint", "FAIL"),
        api.get("websocket", "SKIPPED"),
        api.get("api_key", "MISSING"),
        api.get("api_secret", "MISSING"),
    )

    wallet = report["wallet"]
    verify_wallet = env_report["wallet"]
    LOGGER.info(
        "[VERIFY WALLET]\nconfigured=%s derived=%s match=%s network=%s chain_id=%s rpc=%s signer=%s allowance=%s",
        _mask_secret(verify_wallet.get("configured", "")),
        _mask_secret(verify_wallet.get("derived", "")) if verify_wallet.get("derived") else verify_wallet.get("derived_status", "--"),
        verify_wallet.get("match", "UNKNOWN"),
        verify_wallet.get("network", "--"),
        verify_wallet.get("chain_id", "--"),
        verify_wallet.get("rpc_status", "--"),
        wallet.get("signer", "FAIL"),
        wallet.get("allowance", "UNKNOWN"),
    )

    balance = report["balance"]
    LOGGER.info(
        "[VERIFY BALANCE]\ncash=%.4f open_value=%.4f equity=%.4f sizing_bankroll=%.4f source=%s wallet=%s status=%s",
        float(balance.get("cash", 0.0) or 0.0),
        float(balance.get("open_value", 0.0) or 0.0),
        float(balance.get("equity", 0.0) or 0.0),
        float(balance.get("sizing_bankroll", 0.0) or 0.0),
        balance.get("source", "UNKNOWN"),
        _mask_secret(balance.get("wallet_address", "")),
        balance.get("status", "UNKNOWN"),
    )

    positions = report["positions"]
    LOGGER.info(
        "[VERIFY POSITIONS]\npositions=%s reconciliation=%s classification=%s reason=%s",
        positions.get("count", 0),
        positions.get("reconciliation", "UNKNOWN"),
        positions.get("classification", "--"),
        positions.get("reason", ""),
    )

    for item in report["markets"]:
        LOGGER.info(
            "[VERIFY MARKETS]\n%s orderbook=%s bid=%.4f ask=%.4f spread=%.4f implied=%.4f",
            item.get("ticker", "--"),
            item.get("orderbook", "FAIL"),
            float(item.get("bid", 0.0) or 0.0),
            float(item.get("ask", 0.0) or 0.0),
            float(item.get("spread", 0.0) or 0.0),
            float(item.get("implied_probability", 0.0) or 0.0),
        )

    for item in report["model"]:
        LOGGER.info(
            "[VERIFY MODEL]\n%s p_yes=%.4f ev=%.4f delta=%s decision=%s reason=%s",
            item.get("ticker", "--"),
            float(item.get("p_yes", 0.0) or 0.0),
            float(item.get("ev", 0.0) or 0.0),
            item.get("delta", "--"),
            item.get("decision", "--"),
            item.get("reason", ""),
        )

    warnings = list(env_report.get("warnings", [])) + list(report.get("warnings", []))
    fatal = list(env_report.get("critical", [])) + list(report.get("fatal", []))
    if warnings:
        LOGGER.warning("[VERIFY WARNINGS] %s", ", ".join(str(w) for w in warnings))
    if fatal:
        LOGGER.error("[VERIFY FAILED] %s", ", ".join(str(w) for w in fatal))
        return 1
    LOGGER.info("[VERIFY OK] Read-only connectivity and account checks passed.")
    return 0


def run_polymarket_5m_dashboard() -> int:
    dashboard_path = Path(__file__).resolve().parent / "dashboard" / "polymarket_5m_dashboard.py"
    command = ["streamlit", "run", str(dashboard_path)]
    LOGGER.info("Starting polymarket 5m dashboard with command: %s", " ".join(command))
    completed = subprocess.run(command, check=False)
    return completed.returncode


def run_scalper_mode(scalper_mode: str) -> int:
    import sys

    LOGGER.info("Scalper mode selected with submode=%s", scalper_mode)
    sys.argv = ["live_runner.py", "--mode", scalper_mode]
    return run_scalper()



def run_realtime_mode(symbol: str) -> int:
    import signal
    import time

    from crypto_scalper.realtime_feed import CryptoRealtimeFeed
    from utils.display import RealtimeTickerDisplay
    from utils.position_tracker import PositionTracker

    settings = get_settings()
    feed = CryptoRealtimeFeed(symbol=symbol, settings=settings)
    tracker = PositionTracker(settings=settings)
    stop = threading.Event()

    def _handle_sigint(*_args: object) -> None:
        stop.set()

    signal.signal(signal.SIGINT, _handle_sigint)

    display = RealtimeTickerDisplay(
        symbol=symbol,
        exchange=settings.crypto_exchange,
        paper_trading=settings.paper_trading,
    )

    def _on_tick(tick: object) -> None:
        display.update_tick(tick)
        triggered = tracker.update_price(symbol, getattr(tick, "last_price", 0.0))
        if triggered:
            LOGGER.warning("Auto-closed %s positions (SL/TP hit)", len(triggered))
        display.update_portfolio(tracker.summary())

    feed.subscribe(_on_tick)
    feed.start()

    LOGGER.info(
        "Realtime feed started | symbol=%s exchange=%s",
        symbol,
        settings.crypto_exchange,
    )

    with display:
        while not stop.is_set():
            time.sleep(0.25)

    feed.stop()
    return 0


def run_dashboard_mode() -> int:
    dashboard_path = Path(__file__).resolve().parent / "dashboard" / "app.py"
    command = ["streamlit", "run", str(dashboard_path)]
    LOGGER.info("Starting dashboard with command: %s", " ".join(command))
    completed = subprocess.run(command, check=False)
    return completed.returncode


def main() -> int:
    args = build_parser().parse_args()
    validation = validate_env(cli_mode=args.mode)
    settings = get_settings()
    apply_validation_to_settings(settings, validation)
    setup_logger(settings.log_level, settings.log_dir)
    if validation.errors:
        for error in validation.errors:
            LOGGER.critical("[CONFIG_INVALID] %s", error)
        return 1
    LOGGER.info("[STARTUP CONFIG]\n%s", build_startup_summary(settings, validation, mode=args.mode))
    LOGGER.info("%s", build_paper_balance_debug_summary(
        result=validation,
        mode=args.mode,
    ))
    for warning in validation.warnings:
        LOGGER.warning("[CONFIG_WARNING] %s", warning)

    if args.mode == "polymarket":
        return run_polymarket_mode()
    if args.mode in {"paper", "polymarket-paper", "polymarket-realtime"}:
        return _call_with_optional_ui(run_polymarket_paper, args.interval, args.ui, args.fps)
    if args.mode == "live":
        return _call_with_optional_ui(run_polymarket_live, args.interval, args.ui, args.fps)
    if args.mode == "verify":
        return run_verify_mode()
    if args.mode == "polymarket-backtest":
        return run_polymarket_backtest(days=args.days, asset=args.asset, min_edge=args.min_edge,
                                       balance=args.balance, score_scale=args.score_scale,
                                       momentum_price=args.momentum_price)
    if args.mode == "polymarket-5m-dashboard":
        return run_polymarket_5m_dashboard()
    if args.mode == "scalper":
        return run_scalper_mode(args.scalper_mode)
    if args.mode == "dashboard":
        return run_dashboard_mode()
    if args.mode == "realtime":
        return run_realtime_mode(args.symbol)
    if args.mode == "hft":
        from hft.main import run_hft
        import asyncio
        paper = settings.paper_trading
        asyncio.run(run_hft(bankroll=args.balance, paper=paper))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
