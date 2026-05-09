from __future__ import annotations

import logging
import time
import json
from collections import Counter, deque
from dataclasses import dataclass, asdict, field
from datetime import UTC, datetime
from pathlib import Path

from config.settings import Settings, get_settings
from polymarket.arbitrage import ArbitrageOpportunity, ArbitrageScanner
from polymarket.arbitrage_executor import ArbitrageExecutor
from polymarket.client import BUY, SELL, BalanceSnapshot, OrderReceipt, PolymarketClient
from polymarket.delta_engine import DeltaRegime, MicroDeltaInput, estimate_micro_delta
from polymarket.expected_value import ExpectedValueTier
from polymarket.gamma_fetcher import GammaFetcher, GammaMarket
from polymarket.lucky_shot import LuckyShotInput, evaluate_lucky_shot
from polymarket.order_manager import OrderRequest, PolymarketOrderManager
from polymarket.order_intent import OrderIntent, OrderIntentType, validate_order_intent
from polymarket.opportunity_scanner import (
    OpportunityCandidate,
    OpportunityDecision,
    OpportunityScanContext,
    scan_opportunities,
)
from polymarket.position_manager import PositionManagerInput, PositionState, manage_position
from polymarket.probability_model import ProbabilityModelInput, estimate_probability
from polymarket.signal import BACKTEST_WIN_RATE, SignalResult, compute_realtime_signal
from polymarket.trade_frequency import frequency_multiplier_for_tier
from polymarket.trend_runner import TrendRunnerInput, evaluate_trend_entry
from polymarket.virtual_ptb import VirtualPriceToBeatTracker
from polymarket.quant_indicators import get_quant_feed
from polymarket.bankroll_tiers import (
    BankrollRankLock,
    BankrollRankLockResult,
    calculate_base_risk_pct,
    get_bankroll_tier,
    get_tier_config,
)
from polymarket.risk_modes import (
    RiskMode,
    RiskModeDecision,
    RiskModeState,
    trade_quality_allowed,
)
from utils.position_tracker import InventoryClassification, PositionTracker, ReconciliationReport
from utils.risk_manager import FLOOR_BALANCE, RiskManager, RiskPlan
from utils.quant_event_logger import QuantEventLogger
from utils.telegram_alerts import TelegramAlertLayer
from utils.no_entry_diagnostics import classify_time_bucket, normalize_skip_reason


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TradeOutcome:
    market_id: str
    question: str
    decision: str
    confidence: float
    risk_plan: RiskPlan | None
    receipt: OrderReceipt | None
    skipped: bool
    skip_reason: str
    display: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class MarketDisplayMetrics:
    ticker: str
    outcome: str
    token_id: str
    yes_token_id: str = ""
    no_token_id: str = ""
    condition_id: str = ""
    market_slug: str = ""
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    yes_bid: float = 0.0
    yes_ask: float = 0.0
    no_bid: float = 0.0
    no_ask: float = 0.0
    yes_mid: float = 0.0
    no_mid: float = 0.0
    orderbook_age_ms: int = 0
    yes_orderbook_age_ms: int = 0
    no_orderbook_age_ms: int = 0
    clob_source: str = "CLOB orderbook"
    token_mapping_warning: str = ""
    snipe_score: float = 0.0
    edge_pct: float = 0.0
    has_orderbook: bool = False
    p_yes: float = 0.0
    p_no: float = 0.0
    ev: float = 0.0
    min_ev: float = 0.0
    delta_regime: str = "--"
    delta_multiplier: float = 0.0
    skip_reason: str = ""
    score: float = 0.0
    frequency_multiplier: float = 0.0
    final_size: float = 0.0
    ask_price: float = 0.0


@dataclass(slots=True)
class AdaptiveEntryCutoffDecision:
    allowed: bool
    policy: str
    effective_cutoff_seconds: int
    reason: str
    late_entry_hard_block: bool = False


@dataclass(slots=True)
class PaperSessionStats:
    cycles_scanned: int = 0
    markets_scanned: int = 0
    opportunities_found: int = 0
    trades_simulated: int = 0
    paper_orders_created: int = 0
    paper_fills: int = 0
    paper_exits: int = 0
    wins: int = 0
    losses: int = 0
    ev_sum: float = 0.0
    ev_count: int = 0
    confidence_sum: float = 0.0
    confidence_count: int = 0
    position_size_sum: float = 0.0
    simulated_pnl: float = 0.0
    max_drawdown: float = 0.0
    skipped_reasons: Counter[str] = field(default_factory=Counter)
    cancel_reasons: Counter[str] = field(default_factory=Counter)
    state_transitions: Counter[str] = field(default_factory=Counter)
    risk_mode_transitions: Counter[str] = field(default_factory=Counter)
    critical_warnings: list[str] = field(default_factory=list)
    trade_timestamps: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        pass

    @property
    def win_rate(self) -> float:
        closed = self.wins + self.losses
        return self.wins / closed if closed else 0.0

    @property
    def average_ev(self) -> float:
        return self.ev_sum / self.ev_count if self.ev_count else 0.0

    @property
    def average_confidence(self) -> float:
        return self.confidence_sum / self.confidence_count if self.confidence_count else 0.0

    @property
    def average_position_size(self) -> float:
        return self.position_size_sum / self.trades_simulated if self.trades_simulated else 0.0


@dataclass(slots=True)
class BankrollState:
    starting_bankroll: float
    current_cash_balance: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    open_position_market_value: float = 0.0
    equity: float = 0.0
    current_bankroll_for_sizing: float = 0.0
    daily_start_bankroll: float = 0.0
    current_bankroll: float = 0.0
    peak_bankroll: float = 0.0
    daily_pnl: float = 0.0
    daily_drawdown_pct: float = 0.0
    total_drawdown_pct: float = 0.0
    current_bankroll_tier: str = ""
    raw_bankroll_tier: str = ""

    def __post_init__(self) -> None:
        if self.equity <= 0:
            self.equity = self.current_cash_balance
        if self.current_bankroll_for_sizing <= 0:
            self.current_bankroll_for_sizing = self.equity
        if self.daily_start_bankroll <= 0:
            self.daily_start_bankroll = self.starting_bankroll
        if self.current_bankroll <= 0:
            self.current_bankroll = self.equity
        if self.peak_bankroll <= 0:
            self.peak_bankroll = self.equity
        if not self.current_bankroll_tier:
            self.current_bankroll_tier = get_bankroll_tier(self.equity).value
        if not self.raw_bankroll_tier:
            self.raw_bankroll_tier = get_bankroll_tier(self.equity).value


class PolymarketTrader:
    """Coordinate one full Polymarket trading cycle.

    Workflow per cycle:
    1. Fetch top active markets from Gamma.
    2. For each market, run the five-agent AI pipeline.
    3. If the pipeline approves, build a risk plan and place an order.
       In paper-trading mode the order is logged but never submitted.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        tracker: PositionTracker | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = PolymarketClient()
        self.gamma = GammaFetcher()
        self.order_manager = PolymarketOrderManager(
            account_balance=self.settings.account_balance,
            max_risk_per_trade=self.settings.max_risk_per_trade,
            stop_loss_pct=self.settings.default_stop_loss_pct,
            kelly_fraction_cap=self.settings.kelly_fraction_cap,
        )
        self.tracker = tracker or PositionTracker(settings=self.settings)
        self.ptb_tracker = VirtualPriceToBeatTracker()
        self._connected = False
        # Tracking to ensure exactly 1 bet per asset per 5-min window
        self._placed_epochs: dict[str, int] = {}
        self._market_entry_counts: dict[tuple[str, int], int] = {}
        # Last cycle signal per ticker â€” read by main.py for CSV logging
        self.last_signals: dict[str, SignalResult] = {}
        # Loss cluster pause tracker
        self._risk_mgr = RiskManager(initial_balance=self.settings.account_balance or 8.89)
        # Real CLOB token IDs per ticker: ticker â†’ (yes_token_id, no_token_id)
        # Refreshed each cycle in _select_markets(); empty = use synthetic fallback
        self._real_token_ids: dict[str, tuple[str, str]] = {}
        self._market_token_meta: dict[str, dict[str, str]] = {}
        self._arb_scanner = ArbitrageScanner(
            self.client,
            min_net_edge=self.settings.arb_min_net_edge,
            min_profit_usdc=self.settings.arb_min_profit_usdc,
            fee_buffer=self.settings.arb_fee_buffer,
            slippage_buffer=self.settings.arb_slippage_buffer,
            fail_risk_buffer=self.settings.arb_fail_risk_buffer,
            max_leg_spread=self.settings.arb_max_leg_spread,
        )
        self._arb_executor = ArbitrageExecutor(self.client, settings=self.settings, tracker=self.tracker)
        # v3.1: Balance guard pause flag
        self._paused_insufficient_funds = False
        self._last_verified_balance: float = 0.0
        # v3.1: Panic sell cooldown (epoch_ts â†’ skip next round)
        self._panic_sold_epochs: dict[str, int] = {}
        # v3.1: Partial TP tracking (position_id â†’ already took partial)
        self._partial_tp_taken: set[str] = set()
        self._last_reconciliation: ReconciliationReport | None = None
        self._balance_source: str = "paper_virtual" if self.settings.paper_trading else "unverified"
        self._balance_wallet_address: str = self.settings.polymarket_proxy_wallet or self.settings.polymarket_funder
        self._last_balance_snapshot: BalanceSnapshot | None = None
        self._paper_virtual_reference_balance = float(self.settings.account_balance)
        self._wallet_reference_balance: float | None = None
        self._wallet_reference_source: str = ""
        self._wallet_reference_error: str = ""
        self._last_wallet_reference_refresh_ts = 0.0
        self._paper_wallet_reference_initialized = False
        self._paper_startup_fallback_used = False
        self._paper_virtual_cash_initial = float(self.settings.account_balance)
        self.paper_stats = PaperSessionStats()
        self._risk_mode_state = RiskModeState()
        self._last_risk_mode_log = ""
        initial_bankroll = float(self.settings.account_balance)
        self.bankroll_state = BankrollState(
            starting_bankroll=initial_bankroll,
            current_cash_balance=initial_bankroll,
        )
        self._bankroll_rank_lock = BankrollRankLock(
            initial_tier=initial_bankroll,
            buffer_pct=float(getattr(self.settings, "bankroll_rank_hysteresis_pct", 0.05) or 0.05),
        )
        self._last_bankroll_rank_lock_log = ""
        self.last_quant_details: dict[str, dict[str, object]] = {}
        self._last_orderbook_age_ms: dict[str, int] = {}
        self._preloaded_token_ids: dict[tuple[str, int], tuple[str, str]] = {}
        self._preloaded_token_meta: dict[tuple[str, int], dict[str, object]] = {}
        self._warmed_orderbook_epochs: set[tuple[str, int]] = set()
        self._market_readiness_metrics = {
            "token_preload_hits": 0,
            "token_preload_misses": 0,
            "token_preload_warmups": 0,
            "token_preload_failures": 0,
        }
        self._recent_display_trades: deque[dict[str, object]] = deque(maxlen=12)
        self._cycle_count = 0
        self._cycle_started_monotonic = 0.0
        self._cycle_started_at_utc = ""
        self._last_scan_cycle_duration_ms = 0
        self._last_structured_logs: dict[str, str] = {}
        self.quant_events = self._init_quant_event_logger()
        self.telegram_alerts = self._init_telegram_alert_layer()
        self._last_system_health_event_ts = 0.0
        self._last_risk_state_event_ts = 0.0
        self._shutdown_complete = False

    def close(self) -> None:
        """Release trader-owned background resources without changing trading state."""
        if self._shutdown_complete:
            return
        self._shutdown_complete = True
        try:
            close_ptb = getattr(self.ptb_tracker, "close", None)
            if callable(close_ptb):
                close_ptb()
        except Exception as exc:
            LOGGER.debug("[SHUTDOWN] PTB/oracle feed close failed: %s", exc)
        for module_name, attr_name in (
            ("polymarket.market_feed", "_feed"),
            ("polymarket.quant_indicators", "_quant_feed"),
        ):
            try:
                module = __import__(module_name, fromlist=[attr_name])
                feed = getattr(module, attr_name, None)
                stop_feed = getattr(feed, "stop", None)
                if callable(stop_feed):
                    stop_feed()
            except Exception as exc:
                LOGGER.debug("[SHUTDOWN] %s close failed: %s", module_name, exc)
        try:
            self._maybe_emit_system_health(force=True, reason="shutdown")
        except Exception:
            pass

    def shutdown(self) -> None:
        self.close()

    def stop(self) -> None:
        self.close()

    def _runtime_mode(self) -> str:
        return "paper" if self.settings.paper_trading else "live"

    def _init_quant_event_logger(self) -> QuantEventLogger | None:
        try:
            return QuantEventLogger(mode=self._runtime_mode(), source_module="polymarket.trader")
        except Exception as exc:
            LOGGER.warning("[OBSERVABILITY] QuantEventLogger disabled at startup: %s", exc)
            return None

    def _init_telegram_alert_layer(self) -> TelegramAlertLayer | None:
        try:
            return TelegramAlertLayer()
        except Exception as exc:
            LOGGER.warning("[OBSERVABILITY] Telegram alert layer disabled at startup: %s", exc)
            return None

    def _emit_quant_event(self, event_method: str, payload: dict[str, object] | None = None) -> bool:
        logger = getattr(self, "quant_events", None)
        if logger is None:
            return False
        try:
            logger.mode = self._runtime_mode()
            method = getattr(logger, event_method)
            return bool(method(payload or {}))
        except Exception as exc:
            LOGGER.warning("[OBSERVABILITY] quant event failed | method=%s error=%s", event_method, exc)
            return False

    def _utc_timestamp(self) -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    def _begin_cycle_timing(self) -> None:
        self._cycle_started_monotonic = time.monotonic()
        self._cycle_started_at_utc = self._utc_timestamp()
        self._last_scan_cycle_duration_ms = 0

    def _cycle_elapsed_ms(self) -> int:
        started = float(getattr(self, "_cycle_started_monotonic", 0.0) or 0.0)
        if started <= 0:
            return 0
        return int(max(0.0, time.monotonic() - started) * 1000)

    def _finish_cycle_timing(self, *, reason: str, force: bool = False) -> None:
        self._last_scan_cycle_duration_ms = self._cycle_elapsed_ms()
        self._maybe_emit_system_health(force=force, reason=reason)

    def _notify_telegram(self, alert_method: str, message: str = "", **context: object):
        alerts = getattr(self, "telegram_alerts", None)
        if alerts is None:
            return None
        try:
            method = getattr(alerts, alert_method)
            result = method(message, **context)
            if getattr(result, "reason", "") == "send_failed":
                self._emit_quant_event(
                    "log_system_health",
                    {
                        "event": "telegram_degraded",
                        "alert_method": alert_method,
                        "reason": result.reason,
                        "mode": self._runtime_mode(),
                    },
                )
            return result
        except Exception as exc:
            LOGGER.warning("[OBSERVABILITY] telegram alert failed | method=%s error=%s", alert_method, exc)
            self._emit_quant_event(
                "log_system_health",
                {
                    "event": "telegram_degraded",
                    "alert_method": alert_method,
                    "reason": "exception",
                    "error": str(exc),
                    "mode": self._runtime_mode(),
                },
            )
            return None

    def _risk_plan_payload(self, risk_plan: RiskPlan | None) -> dict[str, object]:
        if risk_plan is None:
            return {}
        try:
            return asdict(risk_plan)
        except Exception:
            return {
                "position_size": float(getattr(risk_plan, "position_size", 0.0) or 0.0),
                "notional_size": float(getattr(risk_plan, "notional_size", 0.0) or 0.0),
                "risk_amount": float(getattr(risk_plan, "risk_amount", 0.0) or 0.0),
            }

    def _market_slug_for_ticker(self, ticker: str, fallback: str = "") -> str:
        meta = self._market_token_meta.get((ticker or "").upper(), {})
        return str(meta.get("slug", "") or fallback or "")

    @staticmethod
    def _current_five_min_epoch(now_ts: int | None = None) -> int:
        now_ts = int(time.time()) if now_ts is None else int(now_ts)
        return now_ts - (now_ts % 300)

    def _market_preload_lead_seconds(self) -> int:
        return max(
            int(self._setting("execution_entry_cutoff_seconds", 90)),
            int(self._setting("exit_agent_entry_cutoff_seconds", 45)),
        ) + 60

    @staticmethod
    def _meta_int(meta: dict[str, object], key: str, default: int = 0) -> int:
        try:
            return int(float(meta.get(key, default) or default))
        except (TypeError, ValueError):
            return default

    def _cached_active_market_valid(self, ticker: str, now_ts: int) -> bool:
        token_ids = self._real_token_ids.get(ticker)
        meta = self._market_token_meta.get(ticker, {})
        if not token_ids:
            return False
        epoch_start = self._meta_int(meta, "epoch_start_ts")
        epoch_end = self._meta_int(meta, "epoch_end_ts", epoch_start + 300 if epoch_start else 0)
        return bool(epoch_start and epoch_start <= now_ts < epoch_end)

    def _cache_market_tokens(self, ticker: str, market, *, source: str) -> dict[str, object] | None:
        yes_token = str(getattr(market, "yes_token_id", "") or "")
        no_token = str(getattr(market, "no_token_id", "") or "")
        if not yes_token or not no_token:
            return None

        now_ts = int(time.time())
        epoch_start = int(getattr(market, "epoch_start_ts", 0) or self._current_five_min_epoch(now_ts))
        epoch_end = int(getattr(market, "epoch_end_ts", 0) or epoch_start + 300)
        meta: dict[str, object] = {
            "slug": str(getattr(market, "slug", "")),
            "condition_id": str(getattr(market, "condition_id", "")),
            "yes_token_id": yes_token,
            "no_token_id": no_token,
            "market_id": str(getattr(market, "market_id", "")),
            "epoch_start_ts": epoch_start,
            "epoch_end_ts": epoch_end,
            "seconds_remaining": max(0, epoch_end - now_ts),
            "source": source,
            "discovered_at_ts": now_ts,
        }
        key = (ticker, epoch_start)
        self._preloaded_token_ids[key] = (yes_token, no_token)
        self._preloaded_token_meta[key] = meta
        return meta

    def _promote_preloaded_market(self, ticker: str, epoch_start: int, *, source: str) -> bool:
        key = (ticker, epoch_start)
        token_ids = self._preloaded_token_ids.get(key)
        meta = self._preloaded_token_meta.get(key)
        if not token_ids or not meta:
            return False
        self._real_token_ids[ticker] = token_ids
        self._market_token_meta[ticker] = dict(meta)
        self._market_token_meta[ticker]["source"] = source
        if source.startswith("preloaded"):
            self._market_readiness_metrics["token_preload_hits"] += 1
        self._warm_orderbooks_for_ticker(ticker, token_ids, self._market_token_meta[ticker], reason=source)
        return True

    def _warm_orderbooks_for_ticker(
        self,
        ticker: str,
        token_ids: tuple[str, str],
        meta: dict[str, object],
        *,
        reason: str,
    ) -> None:
        epoch_start = self._meta_int(meta, "epoch_start_ts")
        if not epoch_start or (ticker, epoch_start) in self._warmed_orderbook_epochs:
            return
        if not bool(getattr(self, "_connected", False)):
            return

        started = time.monotonic()
        ok = False
        error = ""
        try:
            yes_ob = self.client.get_orderbook(token_ids[0])
            no_ob = self.client.get_orderbook(token_ids[1])
            yes_age_ms = self._orderbook_age_ms(yes_ob)
            no_age_ms = self._orderbook_age_ms(no_ob)
            if yes_age_ms or no_age_ms:
                self._last_orderbook_age_ms[ticker] = max(yes_age_ms, no_age_ms)
            ok = True
            self._market_readiness_metrics["token_preload_warmups"] += 1
        except Exception as exc:
            error = str(exc)
            self._market_readiness_metrics["token_preload_failures"] += 1
            LOGGER.info(
                "[MARKET_WARMUP] ticker=%s market_slug=%s epoch=%s status=degraded reason=%s error=%s",
                ticker,
                meta.get("slug", ""),
                epoch_start,
                reason,
                exc,
            )
        finally:
            self._warmed_orderbook_epochs.add((ticker, epoch_start))
            duration_ms = int(max(0.0, time.monotonic() - started) * 1000)
            self._emit_quant_event(
                "log_system_health",
                {
                    "event": "market_readiness_warmup",
                    "ticker": ticker,
                    "market_slug": str(meta.get("slug", "")),
                    "condition_id": str(meta.get("condition_id", "")),
                    "epoch_start_ts": epoch_start,
                    "seconds_remaining": self._meta_int(meta, "seconds_remaining"),
                    "orderbook_readiness_ms": duration_ms,
                    "warmup_ok": ok,
                    "reason": reason,
                    "error": error,
                    "metrics": dict(self._market_readiness_metrics),
                    "mode": self._runtime_mode(),
                },
            )

    @staticmethod
    def _diagnostic_float(value: object, default: float = 0.0) -> float:
        if isinstance(value, bool) or value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _diagnostic_int(value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def _risk_plan_zero_diagnostics(
        self,
        risk_plan: RiskPlan | None,
        *,
        confidence: float,
        edge: object,
    ) -> dict[str, object]:
        diagnostics = getattr(risk_plan, "diagnostics", {}) if risk_plan is not None else {}
        diagnostics = diagnostics if isinstance(diagnostics, dict) else {}
        reason = self._risk_plan_zero_reason(risk_plan, fallback_reason=str(diagnostics.get("reason_from_order_manager", "") or ""))
        return {
            "bankroll": float(getattr(risk_plan, "account_balance", diagnostics.get("bankroll", 0.0)) or 0.0),
            "tier": str(diagnostics.get("tier", "")),
            "risk_mode": self._risk_mode_state.current_mode.value,
            "confidence": float(confidence or 0.0),
            "edge": self._diagnostic_float(edge),
            "entry_price": float(getattr(risk_plan, "entry_price", diagnostics.get("entry_price", 0.0)) or 0.0),
            "final_position_size": float(getattr(risk_plan, "position_size", diagnostics.get("final_position_size", 0.0)) or 0.0),
            "final_notional_size": float(getattr(risk_plan, "notional_size", diagnostics.get("final_notional_size", 0.0)) or 0.0),
            "min_position_size_usd": float(diagnostics.get("min_position_size_usd", 0.0) or 0.0),
            "reason_from_order_manager": str(diagnostics.get("reason_from_order_manager", "") or ""),
            "risk_plan_zero_reason": reason,
        }

    def _paper_available_balance(self) -> float:
        if not self.settings.paper_trading:
            return float(self.bankroll_state.current_cash_balance)
        return max(float(self.bankroll_state.current_cash_balance), 0.0)

    def _risk_plan_zero_reason(self, risk_plan: RiskPlan | None, *, fallback_reason: str = "") -> str:
        diagnostics = getattr(risk_plan, "diagnostics", {}) if risk_plan is not None else {}
        diagnostics = diagnostics if isinstance(diagnostics, dict) else {}
        text = " ".join(
            [
                fallback_reason,
                str(diagnostics.get("reason_from_order_manager", "") or ""),
                " ".join(str(item) for item in diagnostics.get("blocked_reasons", []) or []),
            ]
        ).lower()
        balance = float(getattr(risk_plan, "account_balance", self.bankroll_state.current_bankroll_for_sizing) or 0.0)
        if "balance_guard" in text or "insufficient" in text:
            return "insufficient_paper_balance"
        if balance < FLOOR_BALANCE or "floor" in text or "balance_below_floor" in text:
            return "bankroll_floor"
        if (
            self._risk_mode_state.current_mode == RiskMode.LOCKDOWN
            or "drawdown" in text
            or "daily_loss" in text
            or "hard_drawdown" in text
            or "lockdown" in text
        ):
            return "risk_mode_blocked"
        if "below_min_position_size" in text or "min shares" in text or "min_order" in text:
            return "min_order_size_not_met"
        if "max risk per market" in text or "position tracker" in text or "max active" in text or "max_position" in text:
            return "max_position_limit"
        return "unknown"

    def _decision_diagnostics_payload(
        self,
        outcome: TradeOutcome,
        *,
        ticker: str,
    ) -> dict[str, object]:
        display = outcome.display or {}
        raw_reason = str(display.get("raw_skip_reason", "") or outcome.skip_reason or "")
        normalized_reason = str(display.get("normalized_skip_reason", "") or normalize_skip_reason(raw_reason))
        seconds_remaining = display.get("seconds_remaining", display.get("time_remaining_seconds"))
        entry_cutoff_seconds = display.get(
            "entry_cutoff_seconds",
            int(self._setting("execution_entry_cutoff_seconds", 90)),
        )
        time_bucket = str(display.get("time_bucket", "") or classify_time_bucket(seconds_remaining, entry_cutoff_seconds))
        edge = display.get("edge", display.get("ev", 0.0))
        decision_timestamp = self._utc_timestamp()
        market_close_timestamp = str(
            display.get("market_close_timestamp")
            or display.get("market_end_time")
            or ""
        )
        orderbook_age_ms = self._diagnostic_int(display.get("orderbook_age_ms")) or 0
        oracle_age_ms = self._diagnostic_int(display.get("oracle_age_ms")) or 0
        market_feed_age_ms = self._diagnostic_int(display.get("market_feed_age_ms")) or 0
        cutoff_block_seconds_remaining = (
            self._diagnostic_int(seconds_remaining)
            if normalized_reason == "time_unsafe" or "cutoff" in raw_reason.lower()
            else None
        )
        payload: dict[str, object] = {
            "raw_skip_reason": raw_reason,
            "normalized_skip_reason": normalized_reason,
            "asset": ticker or self._ticker_from_market_id(outcome.market_id),
            "market_slug": str(display.get("market_slug", "") or self._market_slug_for_ticker(ticker, outcome.market_id)),
            "edge": self._diagnostic_float(edge),
            "ev": self._diagnostic_float(display.get("ev", edge or 0.0)),
            "decision_timestamp": decision_timestamp,
            "decision_latency_ms": self._cycle_elapsed_ms(),
            "scan_cycle_duration_ms": self._cycle_elapsed_ms(),
            "seconds_remaining": self._diagnostic_int(seconds_remaining),
            "entry_cutoff_seconds": self._diagnostic_int(entry_cutoff_seconds),
            "effective_cutoff_seconds": self._diagnostic_int(display.get("effective_cutoff_seconds", entry_cutoff_seconds)),
            "cutoff_policy": str(display.get("cutoff_policy", "static") or "static"),
            "adaptive_cutoff_allowed": bool(display.get("adaptive_cutoff_allowed", False)),
            "adaptive_cutoff_reason": str(display.get("adaptive_cutoff_reason", "") or ""),
            "late_entry_hard_block": bool(display.get("late_entry_hard_block", False)),
            "cutoff_block_seconds_remaining": cutoff_block_seconds_remaining,
            "time_bucket": time_bucket,
            "epoch_start": self._diagnostic_int(display.get("epoch_start", display.get("epoch_start_ts"))),
            "market_start_time": str(display.get("market_start_time", "") or ""),
            "market_end_time": str(display.get("market_end_time", "") or ""),
            "market_close_timestamp": market_close_timestamp,
            "token_id": str(display.get("token_id", "") or ""),
            "yes_token_id": str(display.get("yes_token_id", "") or ""),
            "no_token_id": str(display.get("no_token_id", "") or ""),
            "condition_id": str(display.get("condition_id", "") or ""),
            "outcome": str(display.get("outcome", "") or ""),
            "source_module": str(display.get("source_module", "polymarket.trader") or "polymarket.trader"),
            "orderbook_age_ms": orderbook_age_ms,
            "orderbook_age": round(orderbook_age_ms / 1000.0, 3),
            "orderbook_age_seconds": round(orderbook_age_ms / 1000.0, 3),
            "oracle_age_ms": oracle_age_ms,
            "oracle_age": round(oracle_age_ms / 1000.0, 3),
            "oracle_age_seconds": round(oracle_age_ms / 1000.0, 3),
            "market_feed_age_ms": market_feed_age_ms,
            "market_feed_age_seconds": round(market_feed_age_ms / 1000.0, 3),
            "token_mapping_warning": str(display.get("token_mapping_warning", "") or ""),
            "paper_virtual_cash": float(self.bankroll_state.current_cash_balance if self.settings.paper_trading else 0.0),
            "paper_available_balance": float(self._paper_available_balance() if self.settings.paper_trading else 0.0),
            "paper_open_position_value": float(self.bankroll_state.open_position_market_value if self.settings.paper_trading else 0.0),
            "live_wallet_reference_balance": (
                float(self._wallet_reference_balance)
                if self._wallet_reference_balance is not None and self._paper_wallet_reference_visible()
                else None
            ),
            "risk_per_trade": float(getattr(outcome.risk_plan, "risk_amount", 0.0) or 0.0),
            "calculated_order_size": float(getattr(outcome.risk_plan, "position_size", 0.0) or 0.0),
            "risk_plan_zero_reason": "",
        }
        is_zero_plan = (
            outcome.skipped
            and normalized_reason == "risk_plan_zero"
            and outcome.risk_plan is not None
            and float(getattr(outcome.risk_plan, "position_size", 0.0) or 0.0) <= 0.0
        )
        if is_zero_plan:
            payload["risk_plan_zero_reason"] = self._risk_plan_zero_reason(outcome.risk_plan, fallback_reason=raw_reason)
            payload["risk_plan_zero_diagnostics"] = self._risk_plan_zero_diagnostics(
                outcome.risk_plan,
                confidence=outcome.confidence,
                edge=edge,
            )
        elif outcome.skipped and outcome.risk_plan is not None:
            classified = self._risk_plan_zero_reason(outcome.risk_plan, fallback_reason=raw_reason)
            if classified != "unknown":
                payload["risk_plan_zero_reason"] = classified
        return payload

    def _emit_decision_event(
        self,
        outcome: TradeOutcome,
        *,
        ticker: str = "",
        stage: str = "market_analysis",
    ) -> None:
        reason = outcome.skip_reason or ""
        reason_lower = reason.lower()
        if not outcome.skipped:
            decision_type = "approved"
        elif any(flag in reason_lower for flag in ("risk", "floor", "balance", "drawdown", "reconciliation", "lockdown")):
            decision_type = "risk_rejected"
        elif any(flag in reason_lower for flag in ("order_intent", "blocked", "duplicate")):
            decision_type = "rejected"
        else:
            decision_type = "skipped"
        self._emit_quant_event(
            "log_decision",
            {
                "stage": stage,
                "decision_type": decision_type,
                "market_id": outcome.market_id,
                "ticker": ticker or self._ticker_from_market_id(outcome.market_id),
                "decision": outcome.decision,
                "confidence": float(outcome.confidence or 0.0),
                "skipped": bool(outcome.skipped),
                "skip_reason": reason,
                "has_receipt": outcome.receipt is not None,
                "receipt_status": getattr(outcome.receipt, "status", "") if outcome.receipt else "",
                "risk_plan": self._risk_plan_payload(outcome.risk_plan),
                "display": outcome.display,
                **self._decision_diagnostics_payload(outcome, ticker=ticker or self._ticker_from_market_id(outcome.market_id)),
            },
        )

    def _emit_trade_opened_event(
        self,
        *,
        market_id: str,
        ticker: str,
        token_id: str,
        outcome: str,
        receipt: OrderReceipt,
        risk_plan: RiskPlan,
        entry_price: float,
        strategy: str,
    ) -> None:
        self._emit_quant_event(
            "log_trade_open",
            {
                "market_id": market_id,
                "ticker": ticker,
                "token_id": token_id,
                "outcome": outcome,
                "side": BUY,
                "entry_price": float(entry_price),
                "size": float(risk_plan.position_size),
                "notional_size": float(risk_plan.notional_size),
                "receipt": asdict(receipt),
                "strategy": strategy,
                "mode": self._runtime_mode(),
            },
        )

    def _emit_trade_closed_event(
        self,
        *,
        position,
        reason: str,
        exit_price: float,
        size: float,
        pnl: float,
        receipt: OrderReceipt | None,
        partial: bool = False,
    ) -> None:
        self._emit_quant_event(
            "log_trade_close",
            {
                "position_id": getattr(position, "position_id", ""),
                "market_id": getattr(position, "symbol", ""),
                "ticker": self._ticker_from_market_id(getattr(position, "symbol", "")),
                "token_id": self._position_token_id(position),
                "outcome": self._position_outcome(position),
                "reason": reason,
                "exit_price": float(exit_price),
                "size": float(size),
                "pnl": float(pnl),
                "partial": bool(partial),
                "receipt": asdict(receipt) if receipt else {},
                "mode": self._runtime_mode(),
            },
        )

    def _emit_risk_event(self, event: str, payload: dict[str, object] | None = None) -> None:
        data = {"event": event, "mode": self._runtime_mode()}
        if payload:
            data.update(payload)
        self._emit_quant_event("log_risk_event", data)

    def _maybe_emit_risk_state_event(self, *, force: bool = False, reason: str = "periodic") -> None:
        now = time.time()
        if not force and now - self._last_risk_state_event_ts < 60.0:
            return
        self._last_risk_state_event_ts = now
        state = self.bankroll_state
        summary = self.tracker.summary()
        self._emit_risk_event(
            "risk_state",
            {
                "reason": reason,
                "cash": float(state.current_cash_balance),
                "equity": float(state.equity),
                "balance_source": self._balance_source,
                "paper_balance_source": self._paper_balance_source_setting(),
                "wallet_reference_balance": (
                    float(self._wallet_reference_balance)
                    if self._wallet_reference_balance is not None and self._paper_wallet_reference_visible()
                    else None
                ),
                "wallet_reference_source": self._wallet_reference_source,
                "wallet_reference_error": self._wallet_reference_error,
                "execution": "PAPER ONLY" if self.settings.paper_trading else "LIVE",
                "no_live_orders": bool(self.settings.paper_trading),
                "daily_drawdown_pct": float(state.daily_drawdown_pct),
                "total_drawdown_pct": float(state.total_drawdown_pct),
                "risk_off": self._risk_off(state.daily_drawdown_pct),
                "risk_mode": self._risk_mode_state.current_mode.value,
                "total_exposure": float(getattr(summary, "total_exposure", 0.0) or 0.0),
                "open_positions": int(getattr(summary, "open_count", 0) or 0),
            },
        )

    def _maybe_emit_system_health(self, *, force: bool = False, reason: str = "periodic") -> None:
        now = time.time()
        if not force and now - self._last_system_health_event_ts < 60.0:
            return
        self._last_system_health_event_ts = now
        reconciliation = self._last_reconciliation
        disabled_quant_writers = []
        if getattr(self, "quant_events", None) is not None:
            disabled_quant_writers = sorted(getattr(self.quant_events, "disabled_categories", set()))
        self._emit_quant_event(
            "log_system_health",
            {
                "reason": reason,
                "cycle": int(self._cycle_count),
                "cycle_started_at_utc": str(getattr(self, "_cycle_started_at_utc", "") or ""),
                "scan_cycle_duration_ms": int(
                    self._last_scan_cycle_duration_ms
                    if self._last_scan_cycle_duration_ms
                    else self._cycle_elapsed_ms()
                ),
                "mode": self._runtime_mode(),
                "connected": bool(self._connected),
                "paper_trading": bool(self.settings.paper_trading),
                "balance_source": self._balance_source,
                "risk_mode": self._risk_mode_state.current_mode.value,
                "open_positions": len(self.tracker.open_positions()),
                "reconciliation_class": getattr(getattr(reconciliation, "classification", None), "value", ""),
                "reconciliation_blocks_trading": bool(getattr(reconciliation, "block_new_trading", False)),
                "quant_disabled_writers": disabled_quant_writers,
            },
        )

    def _setting(self, name: str, default: float | int | bool) -> float | int | bool:
        return getattr(self.settings, name, default)

    def _feed_age_seconds(self, ptb_info) -> float | None:
        feed_age = getattr(ptb_info, "feed_age_seconds", None)
        if feed_age is not None:
            try:
                return max(0.0, float(feed_age))
            except (TypeError, ValueError):
                return None

        last_updated = getattr(ptb_info, "last_updated", None)
        if not last_updated:
            return None
        try:
            return max(0.0, time.time() - float(last_updated))
        except (TypeError, ValueError):
            return None

    def _seconds_to_close(self, ptb_info) -> int | None:
        raw = getattr(ptb_info, "seconds_remaining", None)
        try:
            seconds = int(raw)
        except (TypeError, ValueError):
            return None
        return seconds if seconds >= 0 else None

    def _market_timing_detail(
        self,
        market: GammaMarket,
        ptb_info,
        *,
        seconds_remaining: object = None,
        entry_cutoff_seconds: object = None,
    ) -> dict[str, object]:
        raw_seconds = seconds_remaining
        if raw_seconds is None:
            raw_seconds = getattr(ptb_info, "seconds_remaining", None)
        raw_cutoff = entry_cutoff_seconds
        if raw_cutoff is None:
            raw_cutoff = int(self._setting("execution_entry_cutoff_seconds", 90))
        epoch_start = getattr(ptb_info, "epoch_start_ts", None)
        market_start_time = str(getattr(ptb_info, "market_start_time", "") or "")
        if epoch_start is not None and not market_start_time:
            try:
                market_start_time = datetime.fromtimestamp(int(epoch_start), tz=UTC).isoformat()
            except (TypeError, ValueError, OSError):
                market_start_time = ""
        market_end_time = str(
            getattr(ptb_info, "market_end_time", "")
            or getattr(ptb_info, "end_date_iso", "")
            or getattr(market, "end_date_iso", "")
            or ""
        )
        if not market_end_time and epoch_start is not None:
            try:
                market_end_time = datetime.fromtimestamp(int(epoch_start) + 300, tz=UTC).isoformat()
            except (TypeError, ValueError, OSError):
                market_end_time = ""
        return {
            "seconds_remaining": self._diagnostic_int(raw_seconds),
            "entry_cutoff_seconds": self._diagnostic_int(raw_cutoff),
            "time_bucket": classify_time_bucket(raw_seconds, raw_cutoff),
            "epoch_start": self._diagnostic_int(epoch_start),
            "market_start_time": market_start_time,
            "market_end_time": market_end_time,
            "market_close_timestamp": market_end_time,
        }

    def _entry_hard_block_seconds(self) -> int:
        return max(
            int(self._setting("adaptive_entry_hard_block_seconds", 60)),
            int(self._setting("entry_min_seconds_remaining", 30)),
            int(self._setting("execution_force_exit_seconds", 60)),
            int(self._setting("exit_agent_cancel_entries_seconds", 35)),
            int(self._setting("exit_agent_force_exit_seconds", 25)),
        )

    def _adaptive_entry_cutoff_seconds(self) -> int:
        return max(
            self._entry_hard_block_seconds(),
            int(self._setting("adaptive_entry_cutoff_seconds", 60)),
        )

    def _cutoff_decision_detail(self, decision: AdaptiveEntryCutoffDecision) -> dict[str, object]:
        return {
            "effective_cutoff_seconds": int(decision.effective_cutoff_seconds),
            "cutoff_policy": decision.policy,
            "adaptive_cutoff_allowed": bool(decision.allowed and decision.policy == "adaptive"),
            "adaptive_cutoff_reason": decision.reason,
            "late_entry_hard_block": bool(decision.late_entry_hard_block),
        }

    def _entry_cutoff_skip_reason(self, seconds_remaining: int, decision: AdaptiveEntryCutoffDecision) -> str:
        label = "hard block" if decision.late_entry_hard_block else "adaptive denied"
        return (
            f"Entry cutoff: {seconds_remaining}s <= {decision.effective_cutoff_seconds}s "
            f"({label}: {decision.reason})"
        )

    def _evaluate_entry_cutoff(
        self,
        *,
        seconds_remaining: int,
        static_cutoff_seconds: int,
        orderbook_age_ms: int | None,
        oracle_age_ms: int | None,
        decision_latency_ms: int | None,
        scan_cycle_duration_ms: int | None,
        spread: float,
    ) -> AdaptiveEntryCutoffDecision:
        hard_block = self._entry_hard_block_seconds()
        if seconds_remaining <= hard_block:
            return AdaptiveEntryCutoffDecision(
                allowed=False,
                policy="adaptive" if bool(self._setting("adaptive_entry_cutoff_enabled", True)) else "static",
                effective_cutoff_seconds=hard_block,
                reason="hard_close_zone",
                late_entry_hard_block=True,
            )

        if seconds_remaining > static_cutoff_seconds:
            return AdaptiveEntryCutoffDecision(
                allowed=True,
                policy="static",
                effective_cutoff_seconds=static_cutoff_seconds,
                reason="static_safe",
            )

        if not bool(self._setting("adaptive_entry_cutoff_enabled", True)):
            return AdaptiveEntryCutoffDecision(
                allowed=False,
                policy="static",
                effective_cutoff_seconds=static_cutoff_seconds,
                reason="static_cutoff",
            )

        effective_cutoff = self._adaptive_entry_cutoff_seconds()
        if seconds_remaining <= effective_cutoff:
            return AdaptiveEntryCutoffDecision(
                allowed=False,
                policy="adaptive",
                effective_cutoff_seconds=effective_cutoff,
                reason="adaptive_cutoff_floor",
            )

        if self._risk_mode_state.current_mode == RiskMode.LOCKDOWN:
            return AdaptiveEntryCutoffDecision(False, "adaptive", effective_cutoff, "lockdown")

        if not self._reconciliation_safe_for_entry():
            return AdaptiveEntryCutoffDecision(False, "adaptive", effective_cutoff, "reconciliation_block")

        max_orderbook_age_ms = int(self._setting("adaptive_entry_max_orderbook_age_ms", 1000))
        if orderbook_age_ms is None:
            return AdaptiveEntryCutoffDecision(False, "adaptive", effective_cutoff, "orderbook_age_unknown")
        if orderbook_age_ms > max_orderbook_age_ms:
            return AdaptiveEntryCutoffDecision(False, "adaptive", effective_cutoff, "orderbook_stale")

        max_oracle_age_ms = int(self._setting("adaptive_entry_max_oracle_age_ms", 5000))
        if oracle_age_ms is None:
            return AdaptiveEntryCutoffDecision(False, "adaptive", effective_cutoff, "oracle_age_unknown")
        if oracle_age_ms > max_oracle_age_ms:
            return AdaptiveEntryCutoffDecision(False, "adaptive", effective_cutoff, "oracle_stale")

        max_decision_latency_ms = int(self._setting("adaptive_entry_max_decision_latency_ms", 2000))
        if decision_latency_ms is not None and decision_latency_ms > max_decision_latency_ms:
            return AdaptiveEntryCutoffDecision(False, "adaptive", effective_cutoff, "decision_latency_high")

        max_cycle_duration_ms = int(self._setting("adaptive_entry_max_cycle_duration_ms", 2500))
        if scan_cycle_duration_ms is not None and scan_cycle_duration_ms > max_cycle_duration_ms:
            return AdaptiveEntryCutoffDecision(False, "adaptive", effective_cutoff, "cycle_latency_high")

        max_spread = float(self._setting("adaptive_entry_max_spread", 0.06))
        if spread > max_spread:
            return AdaptiveEntryCutoffDecision(False, "adaptive", effective_cutoff, "spread_too_wide")

        return AdaptiveEntryCutoffDecision(
            allowed=True,
            policy="adaptive",
            effective_cutoff_seconds=effective_cutoff,
            reason="healthy_late_entry",
        )

    def _exit_agent_entry_cutoff_seconds(self) -> int:
        return max(
            int(self._setting("execution_entry_cutoff_seconds", 90)),
            int(self._setting("exit_agent_entry_cutoff_seconds", 45)),
        )

    def _exit_agent_force_exit_seconds(self) -> int:
        return max(
            int(self._setting("execution_force_exit_seconds", 60)),
            int(self._setting("exit_agent_force_exit_seconds", 25)),
        )

    def _exit_agent_action(self, seconds_to_close: int) -> tuple[str, str] | None:
        if seconds_to_close <= int(self._setting("exit_agent_emergency_flatten_seconds", 10)):
            return "emergency_flatten", "emergency_flatten"
        if seconds_to_close <= int(self._setting("exit_agent_residual_sweep_seconds", 15)):
            return "residual_sweep", "residual_sweep"
        if seconds_to_close <= self._exit_agent_force_exit_seconds():
            return "force_exit", "forced_exit"
        return None

    def _order_matches_market(self, order: dict, market_id: str, token_ids: tuple[str, str] | None = None) -> bool:
        identifiers = {market_id}
        if token_ids:
            identifiers.update(str(token_id) for token_id in token_ids if token_id)
        fields = (
            "market_id",
            "market",
            "condition_id",
            "conditionId",
            "token_id",
            "tokenId",
            "asset_id",
            "assetId",
        )
        values = {str(order.get(field, "")) for field in fields if order.get(field)}
        return not values or bool(identifiers & values)

    def _cancel_entry_orders_for_market(self, market_id: str, ticker: str, seconds_to_close: int, reason: str) -> None:
        if self.settings.paper_trading:
            return
        try:
            open_orders = self.client.get_open_orders()
        except Exception as exc:
            LOGGER.warning(
                "[EXIT] market=%s action=cancel_scan_failed seconds_to_close=%s reason=%s",
                market_id,
                seconds_to_close,
                exc,
            )
            return

        token_ids = self._real_token_ids.get(ticker)
        for order in open_orders:
            side = str(order.get("side", "")).upper()
            order_id = str(order.get("order_id") or order.get("id") or "")
            if side != BUY or not order_id or not self._order_matches_market(order, market_id, token_ids):
                continue
            if self.client.cancel_order(order_id):
                self._paper_record_cancel(reason)
                self._log_order_section(
                    order_type="CANCEL",
                    size=0.0,
                    price=0.0,
                    status="CANCELED",
                    cancel_reason=reason,
                )
                LOGGER.info(
                    "[EXIT] market=%s action=cancel_entry_order seconds_to_close=%s reason=%s order_id=%s",
                    market_id,
                    seconds_to_close,
                    reason,
                    order_id,
                )
                self._emit_quant_event(
                    "log_execution",
                    {
                        "event": "cancel_order",
                        "status": "canceled",
                        "market_id": market_id,
                        "ticker": ticker,
                        "order_id": order_id,
                        "seconds_to_close": int(seconds_to_close),
                        "reason": reason,
                    },
                )
            else:
                self._paper_record_cancel("cancel_failed")
                self._log_order_section(
                    order_type="CANCEL",
                    size=0.0,
                    price=0.0,
                    status="FAILED",
                    cancel_reason="cancel_failed",
                )
                LOGGER.warning(
                    "[EXIT] market=%s action=cancel_failed seconds_to_close=%s reason=%s order_id=%s",
                    market_id,
                    seconds_to_close,
                    reason,
                    order_id,
                )
                self._emit_quant_event(
                    "log_execution",
                    {
                        "event": "cancel_order",
                        "status": "failed",
                        "market_id": market_id,
                        "ticker": ticker,
                        "order_id": order_id,
                        "seconds_to_close": int(seconds_to_close),
                        "reason": reason,
                    },
                )

    def _paper_enabled(self) -> bool:
        return bool(getattr(self.settings, "paper_trading", False))

    def _paper_record_skip(self, reason: str) -> None:
        if not self._paper_enabled():
            return
        clean_reason = reason or "unknown"
        self.paper_stats.skipped_reasons[clean_reason] += 1
        if any(flag in clean_reason.lower() for flag in ("floor", "drawdown", "reconciliation", "risk", "unknown")):
            self.paper_stats.critical_warnings.append(clean_reason)

    def _paper_record_model(self, confidence: float, ev: float, *, opportunity_found: bool) -> None:
        if not self._paper_enabled():
            return
        self.paper_stats.confidence_sum += max(float(confidence), 0.0)
        self.paper_stats.confidence_count += 1
        self.paper_stats.ev_sum += float(ev)
        self.paper_stats.ev_count += 1
        if opportunity_found:
            self.paper_stats.opportunities_found += 1

    def _paper_record_trade(self, notional_size: float) -> None:
        if not self._paper_enabled():
            return
        self.paper_stats.trades_simulated += 1
        self.paper_stats.position_size_sum += max(float(notional_size), 0.0)
        self.paper_stats.trade_timestamps.append(time.time())
        self._paper_apply_entry_cash(notional_size)

    def _paper_record_close(self, pnl: float) -> None:
        if not self._paper_enabled():
            return
        pnl = float(pnl)
        self.paper_stats.simulated_pnl += pnl
        self.paper_stats.paper_exits += 1
        if pnl >= 0:
            self.paper_stats.wins += 1
        else:
            self.paper_stats.losses += 1

    def _paper_record_cancel(self, reason: str) -> None:
        if self._paper_enabled():
            self.paper_stats.cancel_reasons[reason or "unknown"] += 1

    def _paper_record_position_state(self, state: str, action: str) -> None:
        if self._paper_enabled():
            self.paper_stats.state_transitions[f"{state}->{action}"] += 1

    def _ticker_from_market_id(self, market_id: str) -> str:
        return market_id.replace("pm-5m-", "").upper()

    def _record_quant_detail(self, ticker: str, **values: object) -> dict[str, object]:
        ticker = ticker.upper()
        detail = self.last_quant_details.get(ticker, {"ticker": ticker})
        detail.update(values)
        if "p_yes" in values:
            detail["model_p_yes"] = values["p_yes"]
        if "p_no" in values:
            detail["model_p_no"] = values["p_no"]
        detail["ticker"] = ticker
        self.last_quant_details[ticker] = detail
        LOGGER.debug(
            "[DASHBOARD_QUANT] ticker=%s model_p_yes=%s model_p_no=%s ev=%s min_ev=%s delta=%s x%s decision=%s reason=%s",
            ticker,
            detail.get("p_yes", "--"),
            detail.get("p_no", "--"),
            detail.get("ev", "--"),
            detail.get("min_ev", "--"),
            detail.get("delta_regime", "--"),
            detail.get("delta_multiplier", "--"),
            detail.get("decision", "--"),
            detail.get("skip_reason", ""),
        )
        return detail

    def _display_skip_reason(self, reason: str) -> str:
        clean = (reason or "").lower()
        if "stale" in clean:
            return "stale_data"
        if "token" in clean or "missing" in clean or "parse" in clean or "api" in clean:
            return "api_missing_fields"
        if "orderbook" in clean or "bid/ask" in clean:
            return "no_orderbook"
        if "ev" in clean or "threshold" in clean or "scanner" in clean:
            return "ev_below_threshold"
        if "confidence" in clean:
            return "confidence_too_low"
        if "delta" in clean:
            return "delta_extreme"
        if "cutoff" in clean or "tim" in clean or "<=" in clean:
            return "time_unsafe"
        if "spread" in clean:
            return "spread_too_wide"
        if "liquidity" in clean:
            return "liquidity_too_low"
        if "cooldown" in clean or "frequency" in clean or "max 1" in clean:
            return "frequency_cooldown"
        if "drawdown" in clean or "risk" in clean or "floor" in clean or "balance" in clean:
            return "risk_off"
        return reason or "--"

    def _record_display_trade(
        self,
        *,
        market: str,
        side: str,
        entry_price: float,
        size: float,
        reason: str,
        mode: str,
        exit_price: float | None = None,
        realized_pnl: float = 0.0,
        status: str = "paper",
    ) -> None:
        self._recent_display_trades.appendleft({
            "time": datetime.now(tz=UTC).strftime("%H:%M:%S"),
            "market": market,
            "side": side,
            "entry_price": float(entry_price),
            "exit_price": float(exit_price) if exit_price is not None else None,
            "size": float(size),
            "realized_pnl": float(realized_pnl),
            "reason": reason,
            "mode": mode,
            "status": status,
        })

    def get_recent_display_trades(self) -> list[dict[str, object]]:
        return list(self._recent_display_trades)

    def _trades_last_hour(self) -> int:
        now = time.time()
        recent_paper_trades = [
            ts for ts in self.paper_stats.trade_timestamps
            if now - ts <= 3600
        ]
        return max(len(recent_paper_trades), len(self.tracker.open_positions()))

    def _log_section(self, section: str, body: str, *, force: bool = False) -> None:
        if not force and self._last_structured_logs.get(section) == body:
            return
        self._last_structured_logs[section] = body
        LOGGER.info("[%s] %s", section, body)

    def _momentum_label(self, momentum: float) -> str:
        if momentum > 0.0005:
            return "UP"
        if momentum < -0.0005:
            return "DOWN"
        return "FLAT"

    def _volatility_label(self, volatility: float) -> str:
        if volatility >= 0.006:
            return "HIGH"
        if volatility >= 0.002:
            return "MEDIUM"
        return "LOW"

    def _liquidity_label(self, liquidity: float) -> str:
        if liquidity >= 100.0:
            return "GOOD"
        if liquidity >= 25.0:
            return "OK"
        return "WEAK"

    def _edge_label(self, ev: float, min_ev: float) -> str:
        if ev >= min_ev + 0.02:
            return "GOOD"
        if ev >= min_ev:
            return "OK"
        return "BAD"

    def _risk_off(self, daily_drawdown_pct: float) -> bool:
        return daily_drawdown_pct >= float(self._setting("max_daily_drawdown", 0.10))

    def _consecutive_losses(self) -> int:
        tier_mgr = getattr(self._risk_mgr, "_tier_mgr", None)
        return max(int(getattr(tier_mgr, "_consecutive_losses", 0) or 0), 0)

    def _trigger_lockdown(self, reason: str) -> RiskModeDecision:
        self._risk_mode_state.trigger_lockdown(reason)
        return self._update_risk_mode(force_log=True)

    def _update_risk_mode(self, *, force_log: bool = False) -> RiskModeDecision:
        drawdown = float(getattr(self.bankroll_state, "daily_drawdown_pct", 0.0) or 0.0)
        decision = self._risk_mode_state.update(
            consecutive_losses=self._consecutive_losses(),
            drawdown_pct=drawdown,
            hard_drawdown_reached=self._risk_off(drawdown),
        )
        body = (
            f"mode={decision.mode.value} previous={decision.previous_mode.value} "
            f"reason={decision.reason} consecutive_losses={decision.consecutive_losses} "
            f"drawdown={decision.drawdown_pct * 100:.2f}% "
            f"size_multiplier={decision.size_multiplier:.2f} "
            f"allow_new_entries={decision.allow_new_entries}"
        )
        if decision.lockdown_reasons:
            body += f" lockdown_reasons={','.join(decision.lockdown_reasons)}"
        if force_log or decision.changed or body != self._last_risk_mode_log:
            LOGGER.info("[RISK_MODE] %s", body)
            if self._paper_enabled() and decision.changed:
                self.paper_stats.risk_mode_transitions[
                    f"{decision.previous_mode.value}->{decision.mode.value}"
                ] += 1
            self._last_risk_mode_log = body
            self._emit_risk_event(
                "risk_mode",
                {
                    "mode": decision.mode.value,
                    "previous_mode": decision.previous_mode.value,
                    "reason": decision.reason,
                    "consecutive_losses": int(decision.consecutive_losses),
                    "drawdown_pct": float(decision.drawdown_pct),
                    "size_multiplier": float(decision.size_multiplier),
                    "allow_new_entries": bool(decision.allow_new_entries),
                    "lockdown_reasons": list(decision.lockdown_reasons),
                },
            )
        return decision

    def _apply_risk_mode_to_plan(self, risk_plan: RiskPlan, decision: RiskModeDecision) -> None:
        multiplier = max(0.0, min(float(decision.size_multiplier), 1.0))
        if multiplier >= 1.0:
            return
        risk_plan.risk_amount = round(risk_plan.risk_amount * multiplier, 6)
        risk_plan.position_size = round(risk_plan.position_size * multiplier, 6)
        risk_plan.notional_size = round(risk_plan.notional_size * multiplier, 6)
        risk_plan.capped_fraction = (
            risk_plan.notional_size / risk_plan.account_balance
            if risk_plan.account_balance > 0
            else 0.0
        )

    def _sync_sizing_bankroll(self, bankroll: float) -> None:
        bankroll = max(float(bankroll), 0.0)
        self.settings.account_balance = bankroll
        self.tracker.account_balance = bankroll
        self.order_manager.account_balance = bankroll
        self._risk_mgr.set_balance(bankroll)

    def _coerce_cash_balance(self, raw_balance) -> float:
        if not isinstance(raw_balance, (int, float, str)):
            raise TypeError(f"unsupported balance type: {type(raw_balance).__name__}")
        return float(raw_balance)

    def _wallet_address_for_logs(self) -> str:
        return (
            getattr(self.settings, "polymarket_proxy_wallet", "")
            or getattr(self.settings, "polymarket_funder", "")
            or ""
        )

    def _fetch_live_balance_snapshot(self) -> BalanceSnapshot:
        try:
            snapshot = self.client.get_usdc_balance_snapshot()
            live_balance = self._coerce_cash_balance(snapshot.balance)
            return BalanceSnapshot(
                balance=live_balance,
                source=str(snapshot.source or "live_wallet"),
                wallet_address=str(snapshot.wallet_address or self._wallet_address_for_logs()),
                clob_balance=float(getattr(snapshot, "clob_balance", 0.0) or 0.0),
                onchain_balance=float(getattr(snapshot, "onchain_balance", 0.0) or 0.0),
                proxy_wallet=str(getattr(snapshot, "proxy_wallet", "") or self.settings.polymarket_proxy_wallet),
                funder_wallet=str(getattr(snapshot, "funder_wallet", "") or self.settings.polymarket_funder),
            )
        except Exception:
            live_balance = self._coerce_cash_balance(self.client.get_usdc_balance())
            return BalanceSnapshot(
                balance=live_balance,
                source="live_wallet",
                wallet_address=self._wallet_address_for_logs(),
                clob_balance=live_balance,
                onchain_balance=0.0,
                proxy_wallet=getattr(self.settings, "polymarket_proxy_wallet", ""),
                funder_wallet=getattr(self.settings, "polymarket_funder", ""),
            )

    def _record_balance_snapshot(self, snapshot: BalanceSnapshot) -> None:
        self._last_balance_snapshot = snapshot
        self._balance_source = snapshot.source
        self._balance_wallet_address = snapshot.wallet_address

    def _paper_balance_source_setting(self) -> str:
        source = str(getattr(self.settings, "paper_balance_source", "virtual") or "virtual").strip().lower()
        return source if source in {"virtual", "wallet_reference"} else "virtual"

    def _paper_starting_balance_source_setting(self) -> str:
        source = str(getattr(self.settings, "paper_starting_balance_source", "") or "").strip().lower()
        aliases = {
            "virtual": "config",
            "paper_virtual": "config",
            "wallet_reference": "live_wallet_reference",
        }
        if not source:
            source = "live_wallet_reference" if self._paper_balance_source_setting() == "wallet_reference" else "config"
        source = aliases.get(source, source)
        return source if source in {"config", "live_wallet_reference"} else "config"

    def _paper_wallet_sync_on_start(self) -> bool:
        return bool(getattr(self.settings, "paper_wallet_sync_on_start", True))

    def _paper_wallet_sync_mode(self) -> str:
        mode = str(getattr(self.settings, "paper_wallet_sync_mode", "initialize_only") or "initialize_only").strip().lower()
        return "initialize_only" if mode != "initialize_only" else mode

    def _paper_min_balance_fallback(self) -> float:
        try:
            return max(float(getattr(self.settings, "paper_min_balance_fallback", 0.0) or 0.0), 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _paper_wallet_reference_enabled(self) -> bool:
        return bool(
            self.settings.paper_trading
            and self._paper_starting_balance_source_setting() == "live_wallet_reference"
            and self._paper_wallet_sync_on_start()
            and self._paper_wallet_sync_mode() == "initialize_only"
        )

    def _paper_wallet_reference_refresh_seconds(self) -> float:
        try:
            return max(30.0, float(getattr(self.settings, "wallet_reference_refresh_seconds", 300) or 300))
        except (TypeError, ValueError):
            return 300.0

    def _paper_wallet_reference_visible(self) -> bool:
        return bool(getattr(self.settings, "show_wallet_reference_balance", True))

    def _paper_open_position_entry_cost(self) -> float:
        total = 0.0
        for pos in self.tracker.open_positions():
            try:
                total += float(pos.entry_price) * float(pos.size)
            except Exception:
                continue
        return max(total, 0.0)

    def _apply_paper_reference_balance(self, reference_balance: float, *, reset_starting_balance: bool = False) -> None:
        reference_balance = max(float(reference_balance), 0.0)
        self._paper_virtual_cash_initial = reference_balance
        state = self.bankroll_state
        if reset_starting_balance:
            state.starting_bankroll = reference_balance
            state.daily_start_bankroll = reference_balance
            state.peak_bankroll = max(state.peak_bankroll, reference_balance)
            self._bankroll_rank_lock.reset(reference_balance)
        invested_cost = self._paper_open_position_entry_cost()
        state.current_cash_balance = max(0.0, reference_balance + state.realized_pnl - invested_cost)
        self._update_bankroll_state(refresh_wallet_reference=False)

    def _set_wallet_reference_snapshot(self, snapshot: BalanceSnapshot, *, reset_starting_balance: bool = False) -> None:
        wallet_balance = self._coerce_cash_balance(snapshot.balance)
        self._last_balance_snapshot = snapshot
        self._wallet_reference_balance = wallet_balance
        self._wallet_reference_source = str(snapshot.source or "wallet_reference")
        self._wallet_reference_error = ""
        self._balance_source = "wallet_reference_paper"
        self._balance_wallet_address = str(snapshot.wallet_address or self._wallet_address_for_logs())
        self._last_wallet_reference_refresh_ts = time.time()
        self._apply_paper_reference_balance(wallet_balance, reset_starting_balance=reset_starting_balance)

    def _activate_paper_virtual_fallback(self, reason: str) -> None:
        self._wallet_reference_error = str(reason)
        self._wallet_reference_balance = None
        self._wallet_reference_source = ""
        self._balance_source = "paper_virtual"
        self._balance_wallet_address = self._wallet_address_for_logs()
        self._last_wallet_reference_refresh_ts = time.time()
        self._paper_startup_fallback_used = True
        self._paper_wallet_reference_initialized = True
        fallback_balance = max(self._paper_virtual_reference_balance, self._paper_min_balance_fallback())
        LOGGER.warning(
            "[PAPER WALLET REFERENCE] Wallet bankroll unavailable, fallback to paper_virtual | reason=%s",
            reason,
        )
        self._apply_balance(
            fallback_balance,
            reset_starting_balance=True,
            refresh_wallet_reference=False,
        )

    def _refresh_wallet_reference_balance(self, *, force: bool = False) -> bool:
        if not self._paper_wallet_reference_enabled():
            return False
        if self._paper_wallet_sync_mode() == "initialize_only" and self._paper_wallet_reference_initialized and not force:
            return False
        if self._paper_wallet_sync_mode() == "initialize_only" and not force:
            return False
        now = time.time()
        if not force and now - self._last_wallet_reference_refresh_ts < self._paper_wallet_reference_refresh_seconds():
            return False
        try:
            if force:
                try:
                    self.client.connect()
                except Exception as exc:
                    LOGGER.warning(
                        "[PAPER WALLET REFERENCE] CLOB read-only connect failed, trying balance snapshot fallback: %s",
                        exc,
                    )
            snapshot = self._fetch_live_balance_snapshot()
            if not str(snapshot.wallet_address or self._wallet_address_for_logs()).strip():
                raise RuntimeError("wallet address not configured")
            self._set_wallet_reference_snapshot(snapshot, reset_starting_balance=force)
            self._paper_wallet_reference_initialized = True
            self._paper_startup_fallback_used = False
            LOGGER.info(
                "[PAPER WALLET REFERENCE] REAL WALLET BALANCE (REFERENCE ONLY) source=%s wallet=%s "
                "wallet_bankroll=$%.4f paper_virtual_cash_initial=$%.4f execution=PAPER ONLY NO LIVE ORDERS sync_mode=%s",
                self._wallet_reference_source,
                self._balance_wallet_address or "not_configured",
                self._wallet_reference_balance or 0.0,
                self._paper_virtual_cash_initial,
                self._paper_wallet_sync_mode(),
            )
            return True
        except Exception as exc:
            self._activate_paper_virtual_fallback(str(exc))
            return False

    def _ensure_bankroll_state_matches_settings(self) -> None:
        if not self.settings.paper_trading:
            return
        if self._paper_wallet_reference_enabled():
            return
        configured = float(self.settings.account_balance)
        state = self.bankroll_state
        if (
            self.paper_stats.trades_simulated == 0
            and abs(state.realized_pnl) < 0.0001
            and abs(state.starting_bankroll - configured) >= 0.0001
        ):
            self.bankroll_state = BankrollState(
                starting_bankroll=configured,
                current_cash_balance=configured,
            )
            self._bankroll_rank_lock.reset(configured)

    def _update_bankroll_rank_lock(self, balance: float, *, force_log: bool = False) -> BankrollRankLockResult:
        result = self._bankroll_rank_lock.update(balance)
        self.bankroll_state.current_bankroll_tier = result.active_tier.value
        self.bankroll_state.raw_bankroll_tier = result.raw_tier.value

        log_body = (
            f"active={result.active_tier.value} raw={result.raw_tier.value} "
            f"balance=${result.balance:.2f} reason={result.reason}"
        )
        should_log = (
            force_log
            or result.changed
            or result.active_tier != result.raw_tier
            or log_body != self._last_bankroll_rank_lock_log
        )
        if should_log:
            LOGGER.info("[BANKROLL_RANK_LOCK] %s", log_body)
            self._last_bankroll_rank_lock_log = log_body
        return result

    def _update_bankroll_state(
        self,
        *,
        fetch_live_cash: bool = False,
        force_log: bool = False,
        refresh_wallet_reference: bool = True,
    ) -> BankrollState:
        self._ensure_bankroll_state_matches_settings()
        if refresh_wallet_reference:
            self._refresh_wallet_reference_balance()
        state = self.bankroll_state

        if not self.settings.paper_trading and fetch_live_cash:
            try:
                snapshot = self._fetch_live_balance_snapshot()
                live_balance = snapshot.balance
                self._record_balance_snapshot(snapshot)
                self._last_verified_balance = live_balance
                state.current_cash_balance = live_balance
            except Exception as exc:
                fallback = self._last_verified_balance or state.current_cash_balance
                LOGGER.warning(
                    "[BALANCE_REFRESH] failed: %s -- using last_known_cash=$%.4f",
                    exc,
                    fallback,
                )
                state.current_cash_balance = float(fallback)

        open_value = 0.0
        unrealized = 0.0
        for pos in self.tracker.open_positions():
            try:
                mark = self._position_mark_price(pos)
                size = float(pos.size)
                entry = float(pos.entry_price)
            except Exception:
                continue
            open_value += mark * size
            unrealized += (mark - entry) * size

        cash = max(float(state.current_cash_balance), 0.0)
        equity = max(cash + open_value, 0.0)
        if not self.settings.paper_trading:
            state.realized_pnl = equity - state.starting_bankroll - unrealized

        state.open_position_market_value = open_value
        state.unrealized_pnl = unrealized
        state.equity = equity
        state.current_bankroll_for_sizing = equity
        state.current_bankroll = equity
        state.peak_bankroll = max(state.peak_bankroll, equity)
        state.daily_pnl = equity - state.daily_start_bankroll
        state.daily_drawdown_pct = (
            max(0.0, (state.peak_bankroll - equity) / state.peak_bankroll)
            if state.peak_bankroll > 0
            else 0.0
        )
        state.total_drawdown_pct = (
            max(0.0, (state.starting_bankroll - equity) / state.starting_bankroll)
            if state.starting_bankroll > 0
            else 0.0
        )
        self._update_bankroll_rank_lock(equity, force_log=force_log)
        self._update_risk_mode(force_log=force_log)
        self._sync_sizing_bankroll(state.current_bankroll_for_sizing)
        if force_log:
            self._log_portfolio_source("PORTFOLIO_SYNC")
        return state

    def _paper_apply_entry_cash(self, notional_size: float) -> None:
        if not self._paper_enabled():
            return
        self.bankroll_state.current_cash_balance = max(
            0.0,
            self.bankroll_state.current_cash_balance - max(float(notional_size), 0.0),
        )
        self._update_bankroll_state()

    def _paper_apply_exit_cash(self, proceeds: float, pnl: float) -> None:
        if not self._paper_enabled():
            return
        self._ensure_bankroll_state_matches_settings()
        cash_delta = max(float(proceeds), 0.0) if self.paper_stats.trades_simulated > 0 else float(pnl)
        self.bankroll_state.current_cash_balance += cash_delta
        self.bankroll_state.realized_pnl += float(pnl)
        self._update_bankroll_state()

    def _log_risk_section(
        self,
        *,
        bankroll: float,
        tier: str,
        base_risk_pct: float,
        frequency_multiplier: float,
        final_size: float,
        daily_drawdown_pct: float,
        risk_off: bool,
        skip_reason: str = "",
        force: bool = False,
    ) -> None:
        if not bool(self._setting("verbose_risk_logs", True)):
            return
        state = self.bankroll_state
        body = (
            f"start={state.starting_bankroll:.2f} cash={state.current_cash_balance:.2f} "
            f"open_value={state.open_position_market_value:.2f} "
            f"realized={state.realized_pnl:+.2f} unrealized={state.unrealized_pnl:+.2f} "
            f"equity={state.equity:.2f} sizing_bankroll={state.current_bankroll_for_sizing:.2f} "
            f"tier={tier} base_risk={base_risk_pct * 100:.2f}% "
            f"freq_mult={frequency_multiplier:.2f} final_size={final_size:.4f} "
            f"daily_dd={daily_drawdown_pct * 100:.2f}% risk_off={risk_off}"
        )
        risk_mode = self._risk_mode_state.current_mode
        body += f" risk_mode={risk_mode.value}"
        if risk_mode != RiskMode.NORMAL:
            body += f" risk_mode_mult={self._update_risk_mode().size_multiplier:.2f}"
        if skip_reason:
            body += f" skip_reason={skip_reason}"
        self._log_section("RISK", body, force=force)

    def _log_order_section(
        self,
        *,
        order_type: str,
        size: float,
        price: float,
        status: str,
        retries: int = 0,
        cancel_reason: str = "",
    ) -> None:
        if not bool(self._setting("verbose_risk_logs", True)):
            return
        body = (
            f"type={order_type} size={size:.4f} price={price:.4f} "
            f"status={status} retries={retries}"
        )
        if cancel_reason:
            body += f" cancel_reason={cancel_reason}"
        self._log_section("ORDER", body, force=True)

    def _summary_body(self) -> str:
        self._update_bankroll_state()
        summary = self.paper_session_summary()
        skipped = sum(summary["skipped_trade_reasons"].values())
        canceled = sum(summary["order_cancel_reasons"].values())
        unrealized_pnl = 0.0
        for pos in self.tracker.open_positions():
            try:
                mark = self._position_mark_price(pos)
                unrealized_pnl += (mark - float(pos.entry_price)) * float(pos.size)
            except Exception:
                continue
        return (
            f"cycles={summary['cycles_scanned']} markets={summary['total_markets_scanned']} "
            f"opportunities={summary['total_opportunities_found']} skipped={skipped} "
            f"orders={summary['paper_orders_created']} fills={summary['paper_fills']} "
            f"exits={summary['paper_exits']} entered={summary['total_trades_simulated']} canceled={canceled} "
            f"win_rate={float(summary['win_rate']) * 100:.1f}% "
            f"avg_ev={float(summary['average_ev']):.4f} "
            f"avg_conf={float(summary['average_confidence']):.2f} "
            f"avg_position_size={float(summary['average_position_size']):.4f} "
            f"pnl={float(summary['simulated_pnl']):+.4f} "
            f"unrealized={unrealized_pnl:+.4f} "
            f"max_dd={float(summary['max_drawdown']) * 100:.2f}% "
            f"risk_mode={summary['risk_mode']} "
            f"top_skips={summary['top_skip_reasons']} critical={len(summary['critical_warnings'])}"
        )

    def log_quant_summary(self, *, force: bool = False) -> None:
        self._log_section("SUMMARY", self._summary_body(), force=force)

    def _maybe_log_cycle_summary(self) -> None:
        interval = int(self._setting("summary_interval_cycles", 5))
        if interval > 0 and self._cycle_count % interval == 0:
            self.log_quant_summary(force=True)

    def _paper_update_drawdown(self) -> None:
        if not self._paper_enabled():
            return
        try:
            self.paper_stats.max_drawdown = max(self.paper_stats.max_drawdown, self.bankroll_state.daily_drawdown_pct)
        except Exception:
            pass

    def paper_session_summary(self) -> dict[str, object]:
        stats = self.paper_stats
        self._update_bankroll_state()
        now = time.time()
        recent_trades = [ts for ts in stats.trade_timestamps if now - ts <= 3600]
        top_skip_reasons = sorted(
            stats.skipped_reasons.items(),
            key=lambda item: (-item[1], item[0]),
        )[:5]
        risk_mode_decision = self._update_risk_mode()
        return {
            "cycles_scanned": stats.cycles_scanned,
            "total_markets_scanned": stats.markets_scanned,
            "total_opportunities_found": stats.opportunities_found,
            "total_trades_simulated": stats.trades_simulated,
            "paper_orders_created": stats.paper_orders_created,
            "paper_fills": stats.paper_fills,
            "paper_exits": stats.paper_exits,
            "win_rate": stats.win_rate,
            "average_ev": stats.average_ev,
            "average_confidence": stats.average_confidence,
            "average_position_size": stats.average_position_size,
            "simulated_pnl": stats.simulated_pnl,
            "simulated_bankroll": self.bankroll_state.current_bankroll_for_sizing,
            "max_drawdown": stats.max_drawdown,
            "trade_frequency_last_hour": len(recent_trades),
            "skipped_trade_reasons": dict(stats.skipped_reasons),
            "top_skip_reasons": top_skip_reasons,
            "order_cancel_reasons": dict(stats.cancel_reasons),
            "position_state_transitions": dict(stats.state_transitions),
            "risk_mode": risk_mode_decision.mode.value,
            "risk_mode_reason": risk_mode_decision.reason,
            "risk_mode_size_multiplier": risk_mode_decision.size_multiplier,
            "risk_mode_allow_new_entries": risk_mode_decision.allow_new_entries,
            "risk_mode_transitions": dict(stats.risk_mode_transitions),
            "risk_mode_lockdown_reasons": list(risk_mode_decision.lockdown_reasons),
            "critical_warnings": list(stats.critical_warnings),
        }

    def dashboard_portfolio_state(self) -> dict[str, object]:
        state = self._update_bankroll_state(fetch_live_cash=not self.settings.paper_trading and self._connected)
        summary = self.tracker.summary()
        total_exposure = float(getattr(summary, "total_exposure", 0.0) or 0.0)
        total_exposure_pct = (
            total_exposure / state.current_bankroll_for_sizing
            if state.current_bankroll_for_sizing > 0
            else 0.0
        )
        return {
            "starting_bankroll": state.starting_bankroll,
            "cash": state.current_cash_balance,
            "open_value": state.open_position_market_value,
            "realized_pnl": state.realized_pnl,
            "unrealized_pnl": state.unrealized_pnl,
            "equity": state.equity,
            "sizing_bankroll": state.current_bankroll_for_sizing,
            "bankroll_tier": state.current_bankroll_tier,
            "active_bankroll_tier": state.current_bankroll_tier,
            "raw_bankroll_tier": state.raw_bankroll_tier,
            "daily_drawdown": state.daily_drawdown_pct,
            "risk_off": self._risk_off(state.daily_drawdown_pct),
            "risk_mode": self._risk_mode_state.current_mode.value,
            "account_balance": state.current_bankroll_for_sizing,
            "daily_realized_pnl": state.realized_pnl,
            "daily_drawdown_pct": state.daily_drawdown_pct,
            "total_exposure": total_exposure,
            "total_exposure_pct": total_exposure_pct,
            "open_count": getattr(summary, "open_count", 0),
            "max_open_positions": getattr(summary, "max_open_positions", 0),
            "positions": getattr(summary, "positions", []),
            "balance_source": self._balance_source,
            "wallet_address": self._balance_wallet_address,
            "paper_balance_source": self._paper_balance_source_setting(),
            "execution_mode": "PAPER ONLY" if self.settings.paper_trading else "LIVE",
            "live_orders_enabled": not self.settings.paper_trading,
            "no_live_orders": bool(self.settings.paper_trading),
            "paper_cash": state.current_cash_balance,
            "paper_sizing_balance": state.current_bankroll_for_sizing,
            "wallet_reference_balance": (
                float(self._wallet_reference_balance)
                if self._wallet_reference_balance is not None and self._paper_wallet_reference_visible()
                else None
            ),
            "wallet_reference_available": self._wallet_reference_balance is not None,
            "wallet_reference_source": self._wallet_reference_source,
            "wallet_reference_error": self._wallet_reference_error,
            "wallet_reference_label": (
                "REAL WALLET BALANCE (REFERENCE ONLY)"
                if self._balance_source == "wallet_reference_paper"
                else ""
            ),
        }

    def dashboard_session_summary(self) -> dict[str, object]:
        summary = self.paper_session_summary()
        return {
            "scanned": summary["total_markets_scanned"],
            "opportunities": summary["total_opportunities_found"],
            "entered": summary["total_trades_simulated"],
            "skipped": sum(summary["skipped_trade_reasons"].values()),
            "canceled": sum(summary["order_cancel_reasons"].values()),
            "win_rate": summary["win_rate"],
            "realized_pnl": self.bankroll_state.realized_pnl,
            "unrealized_pnl": self.bankroll_state.unrealized_pnl,
            "max_drawdown": summary["max_drawdown"],
            "risk_mode": summary["risk_mode"],
            "risk_mode_size_multiplier": summary["risk_mode_size_multiplier"],
            "critical_count": len(summary["critical_warnings"]),
        }

    def log_paper_session_summary(self) -> None:
        if not self._paper_enabled():
            return
        self.log_quant_summary(force=True)
        self._log_session_runtime_evaluation()

    def _log_session_runtime_evaluation(self) -> None:
        try:
            from tools.session_runtime_evaluator import evaluate_session_runtime, format_terminal_summary

            evaluation = evaluate_session_runtime(
                session_summary=self.paper_session_summary(),
                date=datetime.now(UTC).strftime("%Y-%m-%d"),
                quant_data_dir=str(self._setting("quant_data_dir", "runtime/quant_data")),
                load_offline_reports=True,
            )
            for line in format_terminal_summary(evaluation):
                LOGGER.info("[SESSION_EVAL] %s", line)
            self._emit_quant_event(
                "log_system_health",
                {
                    "event": "session_runtime_evaluation",
                    "session_status": evaluation.session_status,
                    "primary_bottleneck": evaluation.primary_bottleneck,
                    "secondary_bottleneck": evaluation.secondary_bottleneck,
                    "bottleneck_scores": evaluation.bottleneck_scores,
                    "health_summary": evaluation.health_summary,
                    "timing_quality": evaluation.timing_quality,
                    "cutoff_behavior": evaluation.cutoff_behavior,
                    "risk_blocks": evaluation.risk_blocks,
                    "execution_summary": evaluation.execution_summary,
                    "orderbook_readiness": evaluation.orderbook_readiness,
                    "mode": self._runtime_mode(),
                },
            )
        except Exception as exc:
            LOGGER.warning("[SESSION_EVAL] automatic evaluation failed: %s", exc)

    def _skip_outcome(
        self,
        market: GammaMarket,
        decision: str,
        confidence: float,
        reason: str,
        risk_plan: RiskPlan | None = None,
        *,
        edge: float | None = None,
        ev: float | None = None,
        seconds_remaining: int | None = None,
        entry_cutoff_seconds: int | None = None,
        extra_detail: dict[str, object] | None = None,
    ) -> TradeOutcome:
        ticker = self._ticker_from_market_id(market.market_id)
        raw_reason = reason
        normalized_reason = normalize_skip_reason(raw_reason)
        detail_values: dict[str, object] = dict(extra_detail or {})
        if entry_cutoff_seconds is None:
            entry_cutoff_seconds = detail_values.get(
                "entry_cutoff_seconds",
                int(self._setting("execution_entry_cutoff_seconds", 90)),
            )
        if seconds_remaining is None:
            seconds_remaining = detail_values.get("seconds_remaining")
        detail_values.update({
            "market_id": market.market_id,
            "market_slug": self._market_slug_for_ticker(ticker, market.market_id),
            "decision": "SKIP",
            "skip_reason": self._display_skip_reason(reason),
            "raw_skip_reason": raw_reason,
            "normalized_skip_reason": normalized_reason,
            "confidence": confidence,
            "final_size": 0.0,
            "seconds_remaining": seconds_remaining,
            "entry_cutoff_seconds": entry_cutoff_seconds,
            "time_bucket": classify_time_bucket(seconds_remaining, entry_cutoff_seconds),
        })
        if edge is not None:
            detail_values["edge"] = float(edge)
        if ev is not None:
            detail_values["ev"] = float(ev)
        detail = self._record_quant_detail(
            ticker,
            **detail_values,
        )
        LOGGER.info(
            "[ENTRY_SKIP] market=%s decision=%s confidence=%.3f reason=%s",
            market.market_id, decision, confidence, reason,
        )
        self._paper_record_skip(reason)
        outcome = TradeOutcome(
            market_id=market.market_id,
            question=market.question,
            decision=decision,
            confidence=confidence,
            risk_plan=risk_plan,
            receipt=None,
            skipped=True,
            skip_reason=reason,
            display=detail,
        )
        self._emit_decision_event(outcome, ticker=ticker)
        return outcome

    def _open_positions_for_market(self, market_id: str) -> list:
        return [pos for pos in self.tracker.open_positions() if pos.symbol == market_id]

    def _entry_count_for_market(self, market_id: str, epoch_start_ts: int) -> int:
        return self._market_entry_counts.get((market_id, epoch_start_ts), 0)

    def _record_market_entry(self, market_id: str, epoch_start_ts: int) -> None:
        key = (market_id, epoch_start_ts)
        self._market_entry_counts[key] = self._market_entry_counts.get(key, 0) + 1

    def _position_token_id(self, pos) -> str:
        metadata = getattr(pos, "metadata", None) or {}
        token_id = metadata.get("token_id")
        return str(token_id or pos.symbol)

    def _position_outcome(self, pos) -> str:
        metadata = getattr(pos, "metadata", None) or {}
        outcome = str(metadata.get("outcome", "")).upper()
        if outcome in {"YES", "NO"}:
            return outcome
        return "YES" if getattr(pos, "side", "") == "BUY" else "NO"

    def _position_mark_price(self, pos) -> float:
        token_id = self._position_token_id(pos)
        try:
            ob = self.client.get_orderbook(token_id)
            if ob.best_bid > 0:
                return ob.best_bid
        except Exception as exc:
            LOGGER.warning("[MARK_PRICE] failed | position=%s token=%s error=%s", pos.position_id, token_id, exc)
        return max(0.01, min(0.99, float(pos.entry_price)))

    def _unrealized_pct(self, pos, mark_price: float) -> float:
        return (mark_price - float(pos.entry_price)) / max(float(pos.entry_price), 1e-8)

    def reconcile_live_positions(self) -> ReconciliationReport:
        if self.settings.paper_trading:
            report = self.tracker.reconcile_inventory(
                polymarket_positions=[],
                open_orders=[],
                recently_filled_orders=[],
            )
            self._last_reconciliation = report
            return report

        polymarket_positions = self.client.get_positions()
        open_orders = self.client.get_open_orders()
        recent_orders: list[dict] = []
        for pos in self.tracker.open_positions():
            if pos.order_id:
                receipt = self.client.get_order_status(pos.order_id)
                recent_orders.append({
                    "order_id": receipt.order_id,
                    "status": receipt.status,
                    "outcome": (pos.metadata or {}).get("outcome", ""),
                    "filled_size": receipt.filled_size,
                })
        report = self.tracker.reconcile_inventory(
            polymarket_positions=polymarket_positions,
            open_orders=open_orders,
            recently_filled_orders=recent_orders,
        )
        self._last_reconciliation = report
        return report

    def _block_on_reconciliation_if_needed(self, report: ReconciliationReport) -> bool:
        if not report.block_new_trading:
            return False

        self._trigger_lockdown("reconciliation_mismatch")
        LOGGER.critical(
            "[TRADING_BLOCKED_RECONCILIATION] class=%s reason=%s",
            report.classification.value,
            report.reason,
        )
        self._emit_risk_event(
            "reconciliation_mismatch",
            {
                "classification": report.classification.value,
                "reason": report.reason,
                "local_yes": float(report.local_yes),
                "local_no": float(report.local_no),
                "clob_yes": float(report.clob_yes),
                "clob_no": float(report.clob_no),
            },
        )
        self._notify_telegram(
            "notify_incident",
            (
                "*TRADING BLOCKED: POSITION RECONCILIATION*\n"
                f"Class: {report.classification.value}\n"
                f"Reason: {report.reason}\n"
                f"Local YES/NO: {report.local_yes:.4f}/{report.local_no:.4f}\n"
                f"CLOB YES/NO: {report.clob_yes:.4f}/{report.clob_no:.4f}"
            ),
            dedup_key=f"reconciliation:{report.classification.value}:{report.reason}",
            reason=report.reason,
        )

        if report.classification == InventoryClassification.PARTIALLY_HEDGED_ARB:
            LOGGER.critical(
                "[PARTIAL_ARB_REQUIRES_UNWIND] yes=%.6f no=%.6f reason=%s",
                max(report.local_yes, report.clob_yes),
                max(report.local_no, report.clob_no),
                "manual_intervention_required_without_liquidity_snapshot",
            )
        return True

    def _reconcile_after_order_attempt(self) -> None:
        try:
            report = self.reconcile_live_positions()
            self._block_on_reconciliation_if_needed(report)
        except Exception as exc:
            LOGGER.critical("[RECONCILE_AFTER_ORDER_FAILED] %s", exc, exc_info=True)
            self._trigger_lockdown("reconciliation_failed")

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        if self._connected:
            return

        LOGGER.info(
            "Connecting to Polymarket CLOB client (paper_trading=%s) to fetch balance...",
            self.settings.paper_trading,
        )
        if self.settings.paper_trading:
            if self.paper_stats.trades_simulated == 0 and abs(self.bankroll_state.realized_pnl) < 0.0001:
                self._paper_virtual_reference_balance = float(self.settings.account_balance)
            if self._paper_wallet_reference_enabled():
                LOGGER.info(
                    "[PAPER] Wallet reference startup sync active -- reading real wallet/CLOB balance once "
                    "to initialize paper virtual cash. Execution remains PAPER ONLY; NO LIVE ORDERS."
                )
                self._refresh_wallet_reference_balance(force=True)
            else:
                LOGGER.info("[PAPER] Local simulation mode active -- skipping CLOB connect and live balance fetch.")
                self._apply_balance(float(self.settings.account_balance), refresh_wallet_reference=False)
                self._paper_virtual_cash_initial = float(self.bankroll_state.current_bankroll_for_sizing)
                self._balance_source = "paper_virtual"
            if not self._balance_wallet_address:
                self._balance_wallet_address = self._wallet_address_for_logs()
            LOGGER.info(
                "[WALLET CONNECTED] mode=paper connected=%s wallet_address=%s balance_source=%s execution=PAPER_ONLY",
                "reference_only" if self._balance_source == "wallet_reference_paper" else "false",
                self._balance_wallet_address or "not_configured",
                self._balance_source,
            )
            LOGGER.info(
                "[USDC BALANCE] mode=paper source=%s balance=$%.4f wallet_bankroll=%s paper_cash=$%.4f "
                "paper_sizing_balance=$%.4f execution=PAPER_ONLY no_live_orders=true",
                self._balance_source,
                self.bankroll_state.current_cash_balance,
                (
                    f"${self._wallet_reference_balance:.4f}"
                    if self._wallet_reference_balance is not None
                    else "unavailable"
                ),
                self.bankroll_state.current_cash_balance,
                self.bankroll_state.current_bankroll_for_sizing,
            )
            LOGGER.info(
                "[PAPER BALANCE STARTUP] mode=paper paper_starting_balance_source=%s "
                "paper_wallet_sync_on_start=%s paper_wallet_sync_mode=%s "
                "live_wallet_reference_balance=%s paper_virtual_cash_initial=$%.4f fallback_used=%s",
                self._paper_starting_balance_source_setting(),
                str(self._paper_wallet_sync_on_start()).lower(),
                self._paper_wallet_sync_mode(),
                (
                    f"${self._wallet_reference_balance:.4f}"
                    if self._wallet_reference_balance is not None
                    else "unavailable"
                ),
                self._paper_virtual_cash_initial,
                str(self._paper_startup_fallback_used).lower(),
            )
            self._connected = True
            self._maybe_emit_system_health(force=True, reason="startup_connected")
            return

        try:
            self.client.connect()
            snapshot = self._fetch_live_balance_snapshot()
            real_balance = snapshot.balance
            self._record_balance_snapshot(snapshot)

            self._apply_balance(real_balance, reset_starting_balance=True)
            LOGGER.info(
                "[WALLET CONNECTED] mode=live connected=true wallet_address=%s balance_source=%s",
                self._balance_wallet_address,
                self._balance_source,
            )
            LOGGER.info("Bankroll fetched: $%.4f", real_balance)
            if real_balance == 0:
                LOGGER.warning("Wallet Balance is $0.00. Orders will be skipped.")
            self._log_wallet_startup_verification()
            self._connected = True
            self._maybe_emit_system_health(force=True, reason="startup_connected")
        except Exception:
            LOGGER.exception("Failed to connect to Polymarket CLOB. Using Default Bankroll.")
            self._connected = False
            self._maybe_emit_system_health(force=True, reason="startup_connect_failed")

    def _apply_balance(
        self,
        balance: float,
        *,
        reset_starting_balance: bool = False,
        refresh_wallet_reference: bool = False,
    ) -> None:
        """Propagate a fresh cash/equity balance to bankroll state and sub-components."""
        balance = float(balance)
        if reset_starting_balance:
            self.bankroll_state.starting_bankroll = balance
            self.bankroll_state.daily_start_bankroll = balance
            self.bankroll_state.peak_bankroll = balance
        self.bankroll_state.current_cash_balance = balance
        self._update_bankroll_state(refresh_wallet_reference=refresh_wallet_reference)
        balance = self.bankroll_state.current_bankroll_for_sizing

        tier_config = get_tier_config(self.bankroll_state.current_bankroll_tier)
        tier = tier_config.tier
        raw_tier = self.bankroll_state.raw_bankroll_tier

        if balance < FLOOR_BALANCE:
            msg = f"[FLOOR BREACH] Balance ${balance:.2f} < floor ${FLOOR_BALANCE:.2f} -- ALL TRADING SUSPENDED"
            LOGGER.warning(msg)
            self._emit_risk_event(
                "floor_breach",
                {
                    "balance": float(balance),
                    "floor": float(FLOOR_BALANCE),
                    "balance_source": self._balance_source,
                },
            )
            from utils.telegram_reporter import build_floor_breach_alert

            self._notify_telegram(
                "notify_risk",
                build_floor_breach_alert(balance, FLOOR_BALANCE),
                dedup_key="floor_breach",
                reason="floor_breach",
            )
        elif tier.value in {"SEED_TEST", "MICRO", "MICRO_PLUS"}:
            LOGGER.info(
                "MICRO BANKROLL PROTECTION ACTIVE -- using rank sizing | "
                "balance=$%.2f active_tier=%s raw_tier=%s risk_range=%.2f%%-%.2f%% max_trades_hour=%d",
                balance, tier_config.description, raw_tier,
                tier_config.min_risk_pct * 100, tier_config.max_risk_pct * 100,
                tier_config.max_trades_per_hour,
            )
        else:
            LOGGER.info(
                "Bankroll tier: %s | raw_tier=%s risk_range=%.2f%%-%.2f%% max_trades_hour=%d",
                tier_config.description,
                raw_tier,
                tier_config.min_risk_pct * 100, tier_config.max_risk_pct * 100,
                tier_config.max_trades_per_hour,
            )

    def refresh_live_balance(self) -> float:
        """Fetch live wallet/CLOB balance and sync every trading component."""
        if self.settings.paper_trading:
            return self._update_bankroll_state().current_bankroll_for_sizing
        if not self._connected:
            self._ensure_connected()
            return self.bankroll_state.current_bankroll_for_sizing

        previous_cash = self.bankroll_state.current_cash_balance
        state = self._update_bankroll_state(fetch_live_cash=True)
        if abs(state.current_cash_balance - previous_cash) >= 0.0001:
            LOGGER.info(
                "[BALANCE_REFRESH] Cash changed $%.4f -> $%.4f",
                previous_cash,
                state.current_cash_balance,
            )
        self._log_portfolio_source("PORTFOLIO_SYNC")
        return state.current_bankroll_for_sizing

    def _log_portfolio_source(self, tag: str = "PORTFOLIO_SYNC") -> None:
        state = self.bankroll_state
        summary = self.tracker.summary()
        positions_count = int(getattr(summary, "open_count", 0) or 0)
        exposure = float(getattr(summary, "total_exposure", 0.0) or 0.0)
        exposure_pct = exposure / state.current_bankroll_for_sizing if state.current_bankroll_for_sizing > 0 else 0.0
        LOGGER.info(
            "[%s] wallet_address=%s balance_source=%s start=$%.4f cash=$%.4f equity=$%.4f "
            "exposure=$%.4f exposure_pct=%.2f%% positions_count=%d",
            tag,
            self._balance_wallet_address or "not_configured",
            self._balance_source,
            state.starting_bankroll,
            state.current_cash_balance,
            state.equity,
            exposure,
            exposure_pct * 100,
            positions_count,
        )

    def _collateral_allowance_snapshot(self) -> tuple[str, float, float]:
        try:
            allowance = self.client.get_balance_allowance(side=BUY)
            allowance_balance = float(allowance.get("balance", 0.0) or 0.0)
            allowance_amount = float(allowance.get("allowance", 0.0) or 0.0)
        except Exception as exc:
            LOGGER.warning("[ALLOWANCE_CHECK] failed: %s", exc)
            return "FAIL", 0.0, 0.0

        status = "OK" if allowance_amount > 0 or allowance_balance <= 0 else "MISSING"
        return status, allowance_balance, allowance_amount

    def _log_wallet_startup_verification(self) -> None:
        state = self._update_bankroll_state()
        summary = self.tracker.summary()
        positions_count = int(getattr(summary, "open_count", 0) or 0)
        exposure = float(getattr(summary, "total_exposure", 0.0) or 0.0)
        allowance_status, allowance_balance, allowance_amount = self._collateral_allowance_snapshot()
        ready = (
            self._connected
            and state.current_cash_balance >= self.settings.bankroll_floor
            and allowance_status == "OK"
        )
        LOGGER.info(
            "[LIVE MODE READY] ready=%s wallet_connected=true wallet_address=%s balance_source=%s "
            "cash=$%.4f equity=$%.4f exposure=$%.4f positions_count=%d floor=$%.4f "
            "allowance=%s allowance_balance=$%.4f allowance_amount=$%.4f",
            ready,
            self._balance_wallet_address or "not_configured",
            self._balance_source,
            state.current_cash_balance,
            state.equity,
            exposure,
            positions_count,
            self.settings.bankroll_floor,
            allowance_status,
            allowance_balance,
            allowance_amount,
        )

    # ------------------------------------------------------------------
    # Market selection
    # ------------------------------------------------------------------

    def _select_markets(self, top_n: int = 7) -> list[GammaMarket]:
        """Return active Polymarket Crypto 5M markets (Coinbase price feed).

        Also refreshes self._real_token_ids so live orders use correct CLOB token IDs.
        """
        # Keep the live universe small to control VPS bandwidth and log volume.
        crypto_tickers = {
            "BTC":  "BTC/USD",
            "ETH":  "ETH/USD",
        }
        self._refresh_token_ids(crypto_tickers.keys())

        markets = [
            GammaMarket(
                market_id=f"pm-5m-{ticker.lower()}",
                question=f"Will {ticker} Up or Down - 5 min? | coinbase:{symbol}",
                volume=500_000.0,
                liquidity=250_000.0,
                end_date_iso="",
            )
            for ticker, symbol in crypto_tickers.items()
        ]
        token_ids_found = sum(1 for t in crypto_tickers if t in self._real_token_ids)
        LOGGER.info(
            "Selected %s Polymarket 5M Crypto markets | Real token IDs cached: %d/%d",
            len(markets), token_ids_found, len(crypto_tickers),
        )
        return markets[:top_n]

    def _refresh_token_ids(self, tickers: object) -> None:
        refresh_started = time.monotonic()
        now_ts = int(time.time())
        current_epoch = self._current_five_min_epoch(now_ts)
        preload_lead = self._market_preload_lead_seconds()
        refreshed = 0
        cache_hits = 0
        cache_misses = 0
        preloaded = 0
        for raw_ticker in tickers:
            ticker = str(raw_ticker).upper()
            try:
                if self._promote_preloaded_market(ticker, current_epoch, source="preloaded_current"):
                    cache_hits += 1
                    refreshed += 1
                    continue

                if self._cached_active_market_valid(ticker, now_ts):
                    meta = self._market_token_meta.get(ticker, {})
                    epoch_end = self._meta_int(meta, "epoch_end_ts")
                    next_epoch = current_epoch + 300
                    next_cached = (ticker, next_epoch) in self._preloaded_token_ids
                    seconds_remaining = max(0, epoch_end - now_ts) if epoch_end else 0
                    if seconds_remaining > preload_lead or next_cached:
                        cache_hits += 1
                        continue

                self._market_readiness_metrics["token_preload_misses"] += 1
                cache_misses += 1
                active = self.gamma.get_current_5min_market(ticker)
                if active and active.yes_token_id and active.no_token_id:
                    meta = self._cache_market_tokens(ticker, active, source="current")
                    epoch_start = self._meta_int(meta or {}, "epoch_start_ts", current_epoch)
                    is_active_now = epoch_start <= now_ts < self._meta_int(meta or {}, "epoch_end_ts", epoch_start + 300)
                    if is_active_now:
                        self._promote_preloaded_market(ticker, epoch_start, source="current")
                        refreshed += 1
                        LOGGER.info(
                            "[TOKEN_FLOW] ticker=%s market_slug=%s condition_id=%s yes_token_id=%s no_token_id=%s source=current seconds_remaining=%s",
                            ticker,
                            str((meta or {}).get("slug", "")),
                            str((meta or {}).get("condition_id", "")),
                            active.yes_token_id,
                            active.no_token_id,
                            (meta or {}).get("seconds_remaining", 0),
                        )
                    else:
                        preloaded += 1
                    if self._meta_int(meta or {}, "seconds_remaining", 999) <= preload_lead:
                        next_market = getattr(self.gamma, "get_next_5min_market", lambda _ticker: None)(ticker)
                        if next_market and getattr(next_market, "yes_token_id", "") and getattr(next_market, "no_token_id", ""):
                            next_meta = self._cache_market_tokens(ticker, next_market, source="next_preload")
                            if next_meta:
                                preloaded += 1
                    continue

                exact = self.gamma.get_exact_5min_ptb(ticker)
                if exact and exact.yes_token_id and exact.no_token_id:
                    meta = self._cache_market_tokens(ticker, exact, source="exact")
                    epoch_start = self._meta_int(meta or {}, "epoch_start_ts", current_epoch)
                    if epoch_start <= now_ts < self._meta_int(meta or {}, "epoch_end_ts", epoch_start + 300):
                        self._promote_preloaded_market(ticker, epoch_start, source="exact")
                        refreshed += 1
                        LOGGER.info(
                            "[TOKEN_FLOW] ticker=%s market_slug=%s condition_id=%s yes_token_id=%s no_token_id=%s source=exact",
                            ticker,
                            str((meta or {}).get("slug", "")),
                            str((meta or {}).get("condition_id", "")),
                            exact.yes_token_id,
                            exact.no_token_id,
                        )
                    else:
                        preloaded += 1
            except Exception as exc:
                LOGGER.warning("[TokenID] Failed to fetch token IDs for %s: %s", ticker, exc)
        duration_ms = int(max(0.0, time.monotonic() - refresh_started) * 1000)
        if bool(getattr(self, "_connected", False)) and (refreshed or preloaded):
            self._emit_quant_event(
                "log_system_health",
                {
                    "event": "market_discovery_refresh",
                    "tickers": [str(t).upper() for t in tickers],
                    "market_discovery_duration_ms": duration_ms,
                    "token_preload_hit_rate": cache_hits / max(cache_hits + cache_misses, 1),
                    "refreshed_markets": refreshed,
                    "preloaded_markets": preloaded,
                    "metrics": dict(self._market_readiness_metrics),
                    "mode": self._runtime_mode(),
                },
            )

    def _snipe_score(self, best_ask: float, model_implied_prob: float) -> float:
        """Relative edge of model vs best ask. Positive = contract is underpriced."""
        if best_ask <= 0:
            return 0.0
        return (model_implied_prob - best_ask) / best_ask

    @staticmethod
    def _orderbook_age_ms(snapshot) -> int:
        try:
            return int(max(0.0, float(getattr(snapshot, "age_seconds", 0.0) or 0.0)) * 1000)
        except (TypeError, ValueError):
            return 0

    def _token_mapping_warning(
        self,
        ticker: str,
        token_ids: tuple[str, str] | None,
        meta: dict[str, str] | None = None,
        *,
        yes_ob=None,
        no_ob=None,
    ) -> str:
        meta = meta or {}
        warnings: list[str] = []
        if not token_ids or len(token_ids) < 2 or not token_ids[0] or not token_ids[1]:
            warnings.append("missing_yes_no_token_ids")
        elif token_ids[0] == token_ids[1]:
            warnings.append("yes_no_token_ids_identical")

        expected_yes = token_ids[0] if token_ids else ""
        expected_no = token_ids[1] if token_ids and len(token_ids) > 1 else ""
        actual_yes = str(getattr(yes_ob, "token_id", "") or "")
        actual_no = str(getattr(no_ob, "token_id", "") or "")
        if expected_yes and actual_yes and actual_yes != expected_yes:
            warnings.append("yes_token_id_mismatch")
        if expected_no and actual_no and actual_no != expected_no:
            warnings.append("no_token_id_mismatch")

        meta_condition = str(meta.get("condition_id", "") or "")
        yes_condition = str(getattr(yes_ob, "condition_id", "") or "")
        no_condition = str(getattr(no_ob, "condition_id", "") or "")
        if yes_condition and no_condition and yes_condition != no_condition:
            warnings.append("yes_no_condition_id_mismatch")
        if meta_condition:
            if yes_condition and yes_condition != meta_condition:
                warnings.append("yes_condition_id_mismatch")
            if no_condition and no_condition != meta_condition:
                warnings.append("no_condition_id_mismatch")

        warning = ",".join(dict.fromkeys(warnings))
        if warning:
            LOGGER.warning(
                "[TOKEN_MAPPING_WARNING] ticker=%s market_slug=%s condition_id=%s yes_token_id=%s no_token_id=%s reason=%s",
                ticker,
                meta.get("slug", ""),
                meta_condition,
                expected_yes,
                expected_no,
                warning,
            )
        return warning

    def get_market_display_metrics(
        self,
        ticker: str,
        outcome: str = "YES",
        confidence: float = 0.0,
    ) -> MarketDisplayMetrics:
        """Return live CLOB orderbook metrics for the outcome shown in the terminal."""
        ticker = ticker.upper()
        outcome = "NO" if outcome.upper() == "NO" else "YES"
        token_ids = self._real_token_ids.get(ticker)
        if not token_ids:
            self._refresh_token_ids((ticker,))
            token_ids = self._real_token_ids.get(ticker)

        missing_token_ids = not token_ids
        token_id = (
            f"pm-5m-{ticker.lower()}"
            if missing_token_ids
            else token_ids[0] if outcome == "YES" else token_ids[1]
        )
        meta = self._market_token_meta.get(ticker, {})
        metrics = MarketDisplayMetrics(
            ticker=ticker,
            outcome=outcome,
            token_id=token_id,
            yes_token_id=token_ids[0] if token_ids else "",
            no_token_id=token_ids[1] if token_ids else "",
            condition_id=str(meta.get("condition_id", "")),
            market_slug=str(meta.get("slug", "")),
            skip_reason="api_missing_fields" if missing_token_ids else "",
        )
        metrics.token_mapping_warning = self._token_mapping_warning(ticker, token_ids, meta)
        try:
            LOGGER.info(
                "[ORDERBOOK_FLOW] ticker=%s outcome=%s market_slug=%s condition_id=%s yes_token_id=%s no_token_id=%s requested_token_id=%s",
                ticker,
                outcome,
                meta.get("slug", ""),
                meta.get("condition_id", ""),
                meta.get("yes_token_id", token_ids[0] if token_ids else ""),
                meta.get("no_token_id", token_ids[1] if token_ids else ""),
                token_id,
            )
            yes_ob = self.client.get_orderbook(token_ids[0]) if token_ids else None
            no_ob = self.client.get_orderbook(token_ids[1]) if token_ids else None
            metrics.token_mapping_warning = self._token_mapping_warning(
                ticker,
                token_ids,
                meta,
                yes_ob=yes_ob,
                no_ob=no_ob,
            )
            metrics.yes_bid = float(getattr(yes_ob, "best_bid", 0.0) or 0.0)
            metrics.yes_ask = float(getattr(yes_ob, "best_ask", 0.0) or 0.0)
            metrics.no_bid = float(getattr(no_ob, "best_bid", 0.0) or 0.0)
            metrics.no_ask = float(getattr(no_ob, "best_ask", 0.0) or 0.0)
            metrics.yes_mid = (metrics.yes_bid + metrics.yes_ask) / 2.0 if metrics.yes_bid > 0 and metrics.yes_ask > 0 else 0.0
            metrics.no_mid = (metrics.no_bid + metrics.no_ask) / 2.0 if metrics.no_bid > 0 and metrics.no_ask > 0 else 0.0
            metrics.yes_orderbook_age_ms = self._orderbook_age_ms(yes_ob)
            metrics.no_orderbook_age_ms = self._orderbook_age_ms(no_ob)
            metrics.orderbook_age_ms = max(metrics.yes_orderbook_age_ms, metrics.no_orderbook_age_ms)
            if metrics.orderbook_age_ms:
                self._last_orderbook_age_ms[ticker] = metrics.orderbook_age_ms
            metrics.bid = metrics.no_bid if outcome == "NO" else metrics.yes_bid
            metrics.ask = metrics.no_ask if outcome == "NO" else metrics.yes_ask
            metrics.spread = max(
                metrics.yes_ask - metrics.yes_bid if metrics.yes_bid > 0 and metrics.yes_ask > 0 else 0.0,
                metrics.no_ask - metrics.no_bid if metrics.no_bid > 0 and metrics.no_ask > 0 else 0.0,
            )
            metrics.has_orderbook = metrics.yes_bid > 0 and metrics.yes_ask > 0 and metrics.no_bid > 0 and metrics.no_ask > 0
            if not metrics.has_orderbook:
                metrics.skip_reason = metrics.skip_reason or "no_orderbook"
            if metrics.token_mapping_warning:
                metrics.skip_reason = metrics.skip_reason or "token_mapping_warning"
            if confidence > 0 and metrics.ask > 0:
                metrics.edge_pct = confidence - metrics.ask
                metrics.snipe_score = self._snipe_score(metrics.ask, confidence)
        except Exception as exc:
            metrics.skip_reason = metrics.skip_reason or ("stale_orderbook" if "stale_orderbook" in str(exc) else "no_orderbook")
            LOGGER.warning(
                "[ORDERBOOK_FLOW] ticker=%s outcome=%s token=%s market_slug=%s last_successful_orderbook_age_ms=%s retry_count=%s failed=%s",
                ticker,
                outcome,
                token_id,
                meta.get("slug", ""),
                self._last_orderbook_age_ms.get(ticker, 0),
                int(self._setting("api_retry_attempts", 1)),
                exc,
            )
        detail = self.last_quant_details.get(ticker, {})
        for key in ("p_yes", "p_no", "ev", "min_ev", "delta_regime", "delta_multiplier", "score", "frequency_multiplier", "final_size", "ask_price"):
            if key in detail:
                setattr(metrics, key, detail[key])
        if detail.get("skip_reason"):
            metrics.skip_reason = str(detail["skip_reason"])
        elif not detail and not metrics.skip_reason:
            metrics.skip_reason = "model_not_run"
        LOGGER.debug(
            "[DASHBOARD_OB] ticker=%s token=%s yes_bid=%.4f yes_ask=%.4f no_bid=%.4f no_ask=%.4f spread=%.4f model_p_yes=%s ev=%s delta=%s age_ms=%s reason=%s",
            ticker,
            token_id,
            metrics.yes_bid,
            metrics.yes_ask,
            metrics.no_bid,
            metrics.no_ask,
            metrics.spread,
            metrics.p_yes,
            metrics.ev,
            metrics.delta_regime,
            metrics.orderbook_age_ms,
            metrics.skip_reason,
        )
        return metrics

    def verify_account_readiness(self) -> dict[str, object]:
        """Run read-only connectivity, wallet, balance, market, and model checks."""
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen

        warnings: list[str] = []
        fatal: list[str] = []

        def add_warning(code: str, *, required: bool = False) -> None:
            if code not in warnings:
                warnings.append(code)
            if required and code not in fatal:
                fatal.append(code)

        def secret_value(value: object) -> str:
            if value is None:
                return ""
            if hasattr(value, "get_secret_value"):
                try:
                    return str(value.get_secret_value())
                except Exception:
                    return ""
            return str(value)

        def raw_float(payload: dict, *keys: str) -> float:
            for key in keys:
                value = payload.get(key)
                if value is not None:
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        return 0.0
            return 0.0

        report: dict[str, object] = {
            "api": {},
            "wallet": {},
            "balance": {},
            "positions": {},
            "markets": [],
            "model": [],
            "warnings": warnings,
            "fatal": fatal,
        }

        api_secret = secret_value(self.settings.polymarket_api_secret)
        private_key = secret_value(self.settings.polymarket_private_key)
        wallet_address = self.settings.polymarket_proxy_wallet or self.settings.polymarket_funder

        if not self.settings.polymarket_api_key:
            add_warning("missing_api_key")
        if not api_secret:
            add_warning("missing_api_secret")

        endpoint_ok = False
        latency_ms: int | str = "--"
        started = time.monotonic()
        try:
            req = Request(self.settings.polymarket_host, method="GET")
            with urlopen(req, timeout=5):
                pass
            endpoint_ok = True
        except HTTPError as exc:
            endpoint_ok = exc.code < 500
        except Exception:
            endpoint_ok = False
        finally:
            latency_ms = int((time.monotonic() - started) * 1000)
        if not endpoint_ok:
            add_warning("auth_failed", required=True)

        websocket_status = "SKIPPED"
        ws_url = getattr(self.settings, "polymarket_ws_url", "")
        if ws_url:
            try:
                import websocket  # type: ignore

                ws = websocket.create_connection(ws_url, timeout=3)
                ws.close()
                websocket_status = "OK"
            except ImportError:
                websocket_status = "SKIPPED"
            except Exception:
                websocket_status = "FAIL"
                add_warning("websocket_disconnected")

        signer_status = "MISSING"
        if private_key:
            signer_status = "OK"
            try:
                from eth_account import Account  # type: ignore

                Account.from_key(private_key)
            except ImportError:
                signer_status = "OK"
            except Exception:
                signer_status = "FAIL"
                add_warning("auth_failed", required=True)
        else:
            add_warning("auth_failed", required=True)

        auth_status = "FAIL"
        try:
            self.client.connect()
            self._connected = True
            auth_status = "OK"
        except Exception:
            self._connected = False
            add_warning("auth_failed", required=True)

        allowance_status = "UNKNOWN"
        allowance_balance = 0.0
        allowance_amount = 0.0
        if self._connected:
            try:
                allowance = self.client.get_balance_allowance(side=BUY)
                allowance_balance = float(allowance.get("balance", 0.0) or 0.0)
                allowance_amount = float(allowance.get("allowance", 0.0) or 0.0)
                allowance_status = "OK" if allowance_amount > 0 or allowance_balance <= 0 else "MISSING"
                if allowance_status == "MISSING":
                    add_warning("missing_allowance", required=True)
            except Exception:
                allowance_status = "FAIL"
                add_warning("missing_allowance", required=True)

        report["api"] = {
            "api_key": "OK" if self.settings.polymarket_api_key else "MISSING",
            "api_secret": "OK" if api_secret else "MISSING",
            "auth": auth_status,
            "endpoint": "OK" if endpoint_ok else "FAIL",
            "latency_ms": latency_ms,
            "websocket": websocket_status,
        }
        report["wallet"] = {
            "address": wallet_address or "--",
            "chain": f"Polygon:{self.settings.polymarket_chain_id}",
            "signer": signer_status,
            "allowance": allowance_status,
            "allowance_balance": allowance_balance,
            "allowance_amount": allowance_amount,
        }

        fetched_cash = 0.0
        balance_source = "unverified"
        previous_sizing = self.bankroll_state.current_bankroll_for_sizing
        if self._connected:
            try:
                snapshot = self._fetch_live_balance_snapshot()
                fetched_cash = snapshot.balance
                balance_source = snapshot.source
                self._record_balance_snapshot(snapshot)
                if fetched_cash <= 0:
                    add_warning("no_balance", required=True)
            except Exception:
                add_warning("no_balance", required=True)
        else:
            add_warning("no_balance", required=True)

        open_positions: list[dict] = []
        open_orders: list[dict] = []
        if self._connected:
            try:
                open_positions = self.client.get_positions()
            except Exception:
                open_positions = []
                add_warning("api_missing_fields")
            try:
                open_orders = self.client.get_open_orders()
            except Exception:
                open_orders = []
                add_warning("api_missing_fields")

        open_value = 0.0
        for pos in open_positions:
            size = raw_float(pos, "size", "balance", "shares")
            value = raw_float(pos, "value", "currentValue", "market_value", "cashPnl")
            price = raw_float(pos, "curPrice", "current_price", "price", "avgPrice")
            open_value += value if value > 0 else size * price

        if fetched_cash > 0:
            self.bankroll_state.current_cash_balance = fetched_cash
            self._update_bankroll_state(fetch_live_cash=False)
            self._sync_sizing_bankroll(self.bankroll_state.current_bankroll_for_sizing)

        equity = fetched_cash + open_value
        sizing = self.bankroll_state.current_bankroll_for_sizing
        mismatch_threshold = max(0.50, max(equity, sizing, 1.0) * 0.02)
        balance_status = "MATCH"
        if fetched_cash > 0 and abs(equity - sizing) > mismatch_threshold:
            balance_status = "MISMATCH"
            add_warning("equity_mismatch")

        report["balance"] = {
            "cash": fetched_cash,
            "open_value": open_value,
            "equity": equity,
            "internal_bankroll": previous_sizing,
            "sizing_bankroll": sizing,
            "source": balance_source,
            "wallet_address": self._balance_wallet_address,
            "status": balance_status,
        }

        try:
            reconciliation = self.tracker.reconcile_inventory(
                polymarket_positions=open_positions,
                open_orders=open_orders,
                recently_filled_orders=[],
            )
            reconciliation_state = "BLOCKED" if reconciliation.block_new_trading else "SAFE"
            if reconciliation.block_new_trading:
                add_warning("reconciliation_mismatch", required=True)
        except Exception as exc:
            reconciliation = None
            reconciliation_state = "UNKNOWN"
            add_warning("reconciliation_mismatch", required=True)
            LOGGER.warning("[VERIFY POSITIONS] reconciliation failed: %s", exc)

        report["positions"] = {
            "count": len(open_positions),
            "open_orders": len(open_orders),
            "reconciliation": reconciliation_state,
            "classification": reconciliation.classification.value if reconciliation else "UNKNOWN",
            "reason": reconciliation.reason if reconciliation else "reconciliation_failed",
        }
        LOGGER.info(
            "[WALLET CONNECTED] mode=verify connected=%s wallet_address=%s balance_source=%s",
            self._connected,
            self._balance_wallet_address or wallet_address or "not_configured",
            balance_source,
        )
        LOGGER.info(
            "[LIVE MODE READY] ready=%s wallet_connected=%s wallet_address=%s balance_source=%s "
            "cash=$%.4f equity=$%.4f exposure=$%.4f positions_count=%d floor=$%.4f",
            self._connected and fetched_cash >= self.settings.bankroll_floor and not fatal,
            self._connected,
            self._balance_wallet_address or wallet_address or "not_configured",
            balance_source,
            fetched_cash,
            equity,
            open_value,
            len(open_positions),
            self.settings.bankroll_floor,
        )

        selected_markets: list[GammaMarket] = []
        try:
            selected_markets = self._select_markets(top_n=2)
        except Exception:
            add_warning("api_missing_fields", required=True)

        if not selected_markets:
            add_warning("api_missing_fields", required=True)

        market_reports: list[dict[str, object]] = []
        model_reports: list[dict[str, object]] = []
        for market in selected_markets:
            ticker = self._ticker_from_market_id(market.market_id)
            token_ids = self._real_token_ids.get(ticker)
            yes_ob = no_ob = None
            try:
                if token_ids:
                    yes_ob = self.client.get_orderbook(token_ids[0])
                    no_ob = self.client.get_orderbook(token_ids[1])
                else:
                    add_warning("api_missing_fields")
            except Exception:
                add_warning("api_missing_fields", required=True)

            best_bid = yes_ob.best_bid if yes_ob else 0.0
            best_ask = yes_ob.best_ask if yes_ob else 0.0
            spread = yes_ob.spread if yes_ob else 0.0
            orderbook_ok = best_bid > 0 and best_ask > 0
            if not orderbook_ok:
                add_warning("stale_orderbook", required=True)

            market_reports.append({
                "ticker": ticker,
                "orderbook": "OK" if orderbook_ok else "FAIL",
                "bid": best_bid,
                "ask": best_ask,
                "spread": spread,
                "implied_probability": best_ask,
            })

            if not orderbook_ok or not no_ob:
                model_reports.append({
                    "ticker": ticker,
                    "p_yes": 0.0,
                    "ev": 0.0,
                    "delta": "--",
                    "decision": "SKIP",
                    "reason": "api_missing_fields",
                })
                continue

            try:
                ptb_info = self.ptb_tracker.get_market_ptb(ticker)
                yes_bid_size = float(yes_ob.bid_size or 0.0)
                yes_ask_size = float(yes_ob.ask_size or 0.0)
                total_size = yes_bid_size + yes_ask_size
                imbalance = (yes_bid_size - yes_ask_size) / total_size if total_size > 0 else 0.0
                signal = compute_realtime_signal(ticker, imbalance=imbalance)
                window_delta = float(ptb_info.current_price) - float(ptb_info.price_to_beat)
                momentum_decimal = float(signal.momentum_pct) / 100.0
                price_velocity = momentum_decimal / 5.0
                recent_volatility = max(abs(momentum_decimal), abs(float(ptb_info.price_diff_pct)) / 100.0) * max(signal.vol_ratio, 0.5)
                yes_mid = (yes_ob.best_bid + yes_ob.best_ask) / 2.0 if yes_ob.best_bid > 0 and yes_ob.best_ask > 0 else yes_ob.best_ask
                ob_spread = max(float(yes_ob.spread or 0.0), float(no_ob.spread or 0.0))
                ob_liquidity_usd = total_size * yes_mid

                probability = estimate_probability(ProbabilityModelInput(
                    underlying_price=ptb_info.current_price,
                    target_price=ptb_info.price_to_beat,
                    distance_to_target=window_delta,
                    time_remaining_seconds=ptb_info.seconds_remaining,
                    recent_price_velocity=price_velocity,
                    short_term_momentum=momentum_decimal,
                    volatility=recent_volatility,
                    orderbook_bid=yes_ob.best_bid,
                    orderbook_ask=yes_ob.best_ask,
                    spread=ob_spread,
                    liquidity=ob_liquidity_usd,
                    polymarket_implied_probability=yes_mid,
                ))
                delta = estimate_micro_delta(MicroDeltaInput(
                    underlying_price=ptb_info.current_price,
                    target_price=ptb_info.price_to_beat,
                    distance_to_target=window_delta,
                    time_remaining_seconds=ptb_info.seconds_remaining,
                    recent_volatility=recent_volatility,
                    recent_price_velocity=price_velocity,
                    spread=ob_spread,
                    liquidity=ob_liquidity_usd,
                ))
                tier = self._update_bankroll_rank_lock(max(sizing, fetched_cash, 0.01)).active_tier
                candidate = OpportunityCandidate(
                    market_id=market.market_id,
                    asset=ticker,
                    p_yes=probability.p_yes,
                    p_no=probability.p_no,
                    yes_ask=yes_ob.best_ask,
                    no_ask=no_ob.best_ask,
                    confidence_score=probability.confidence_score,
                    delta_score=delta.delta_score,
                    delta_regime=delta.delta_regime,
                    delta_multiplier=delta.delta_multiplier,
                    spread=ob_spread,
                    liquidity=ob_liquidity_usd,
                    time_remaining_seconds=ptb_info.seconds_remaining,
                    price_velocity=price_velocity,
                    distance_to_strike=abs(window_delta) / max(float(ptb_info.price_to_beat), 1e-9),
                    orderbook_bid_size=yes_bid_size,
                    orderbook_ask_size=yes_ask_size,
                    drawdown_pct=self.bankroll_state.daily_drawdown_pct,
                    trades_for_market=0,
                )
                scan = scan_opportunities(
                    [candidate],
                    OpportunityScanContext(
                        ev_tier=ExpectedValueTier(name=tier.value, min_ev=0.02),
                        bankroll_tier=tier,
                        trades_last_hour=0,
                        risk_off=False,
                        reconciliation_safe=reconciliation_state == "SAFE",
                        max_trades_per_market=int(self._setting("max_entries_per_market", 1)),
                    ),
                )
                scored = scan.best_trade or (scan.watchlist[0] if scan.watchlist else scan.skipped[0] if scan.skipped else None)
                ev_result = scored.ev_result if scored else None
                side = ev_result.side if ev_result else "SKIP"
                ev = ev_result.ev_yes if side == "YES" and ev_result else ev_result.ev_no if side == "NO" and ev_result else 0.0
                model_reports.append({
                    "ticker": ticker,
                    "p_yes": probability.p_yes,
                    "p_no": probability.p_no,
                    "ev": ev,
                    "delta": delta.delta_regime.value,
                    "decision": scan.decision.value,
                    "reason": scored.skip_reason if scored and scored.skip_reason else probability.model_reason,
                })
            except Exception as exc:
                add_warning("api_missing_fields")
                model_reports.append({
                    "ticker": ticker,
                    "p_yes": 0.0,
                    "ev": 0.0,
                    "delta": "--",
                    "decision": "SKIP",
                    "reason": f"model_error:{exc}",
                })

        report["markets"] = market_reports
        report["model"] = model_reports
        return report

    def get_arbitrage_opportunity(self, ticker: str) -> ArbitrageOpportunity:
        ticker = ticker.upper()
        token_ids = self._real_token_ids.get(ticker)
        if not token_ids:
            self._refresh_token_ids((ticker,))
            token_ids = self._real_token_ids.get(ticker)
        if not token_ids:
            return ArbitrageOpportunity(ticker=ticker, reason="missing_token_ids")

        try:
            opp = self._arb_scanner.scan(ticker, token_ids[0], token_ids[1], market_id=f"pm-5m-{ticker.lower()}")
            if self.settings.arb_auto_execute and not self.settings.paper_trading:
                seconds_remaining = self.ptb_tracker.get_state(ticker).seconds_remaining
                self._arb_executor.cancel_stale_orders_if_needed(seconds_remaining)
            if self.settings.arb_auto_execute and not self.settings.paper_trading and opp.executable:
                seconds_remaining = self.ptb_tracker.get_state(ticker).seconds_remaining
                result = self._arb_executor.execute_buy_both(
                    opp,
                    bankroll=float(self.settings.account_balance),
                    seconds_remaining=seconds_remaining,
                )
                LOGGER.info(
                    "[ARB_EXEC_RESULT] ticker=%s success=%s reason=%s yes=%.6f no=%.6f",
                    ticker, result.success, result.reason, result.yes_filled, result.no_filled,
                )
            return opp
        except Exception as exc:
            LOGGER.warning("[ARB] %s scan failed: %s", ticker, exc)
            return ArbitrageOpportunity(ticker=ticker, reason=f"scan_failed: {exc}")

    # ------------------------------------------------------------------
    # Per-market analysis â†’ order decision
    # ------------------------------------------------------------------

    def _analyze_market_quant(self, market: GammaMarket, ticker: str, ptb_info) -> TradeOutcome:
        if self._paper_enabled():
            self.paper_stats.markets_scanned += 1

        bankroll_state = self._update_bankroll_state(fetch_live_cash=not self.settings.paper_trading)
        current_balance = bankroll_state.current_bankroll_for_sizing
        tier_config = get_tier_config(bankroll_state.current_bankroll_tier)
        tier = tier_config.tier
        portfolio = self.tracker.summary()
        daily_drawdown_pct = bankroll_state.daily_drawdown_pct
        risk_off = self._risk_off(daily_drawdown_pct)
        risk_mode_decision = self._update_risk_mode()
        trades_last_hour = self._trades_last_hour()
        seconds_to_close = self._seconds_to_close(ptb_info)
        entry_cutoff = self._exit_agent_entry_cutoff_seconds()
        timing_detail = self._market_timing_detail(
            market,
            ptb_info,
            seconds_remaining=seconds_to_close,
            entry_cutoff_seconds=entry_cutoff,
        )

        if not risk_mode_decision.allow_new_entries:
            skip_reason = f"risk_mode_lockdown:{risk_mode_decision.reason}"
            self._log_risk_section(
                bankroll=current_balance,
                tier=tier.value,
                base_risk_pct=calculate_base_risk_pct(current_balance),
                frequency_multiplier=frequency_multiplier_for_tier(tier_config, trades_last_hour),
                final_size=0.0,
                daily_drawdown_pct=daily_drawdown_pct,
                risk_off=risk_off,
                skip_reason=skip_reason,
            )
            return self._skip_outcome(
                market,
                "skip",
                0.0,
                skip_reason,
                seconds_remaining=seconds_to_close,
                entry_cutoff_seconds=entry_cutoff,
                extra_detail=timing_detail,
            )

        if seconds_to_close is None:
            LOGGER.info(
                "[EXIT] market=%s action=skip_entry seconds_to_close=-1 reason=missing_close_time",
                market.market_id,
            )
            self._log_risk_section(
                bankroll=current_balance,
                tier=tier.value,
                base_risk_pct=calculate_base_risk_pct(current_balance),
                frequency_multiplier=frequency_multiplier_for_tier(tier_config, trades_last_hour),
                final_size=0.0,
                daily_drawdown_pct=daily_drawdown_pct,
                risk_off=risk_off,
                skip_reason="missing_close_time",
            )
            return self._skip_outcome(
                market,
                "skip",
                0.0,
                "missing_close_time",
                entry_cutoff_seconds=entry_cutoff,
                extra_detail=timing_detail,
            )

        self._exit_agent_tick(market.market_id, ticker, seconds_to_close)

        skip_reason = ""
        hard_block_seconds = self._entry_hard_block_seconds()
        if seconds_to_close <= hard_block_seconds:
            hard_block_decision = AdaptiveEntryCutoffDecision(
                allowed=False,
                policy="adaptive" if bool(self._setting("adaptive_entry_cutoff_enabled", True)) else "static",
                effective_cutoff_seconds=hard_block_seconds,
                reason="hard_close_zone",
                late_entry_hard_block=True,
            )
            timing_detail.update(self._cutoff_decision_detail(hard_block_decision))
            skip_reason = self._entry_cutoff_skip_reason(seconds_to_close, hard_block_decision)
        elif len(self._open_positions_for_market(market.market_id)) >= int(self._setting("max_active_positions_per_market", 1)):
            skip_reason = "Max active positions per market reached"
        elif self._entry_count_for_market(market.market_id, ptb_info.epoch_start_ts) >= int(self._setting("max_entries_per_market", 1)):
            skip_reason = "Max entries per market reached"
        elif self._placed_epochs.get(ticker) == ptb_info.epoch_start_ts:
            self._trigger_lockdown("duplicate_order")
            skip_reason = f"Max 1 trade per window (already placed for epoch {ptb_info.epoch_start_ts})"
        elif self._panic_sold_epochs.get(ticker) == ptb_info.epoch_start_ts:
            skip_reason = f"Panic sell cooldown (epoch {ptb_info.epoch_start_ts})"
        elif current_balance < FLOOR_BALANCE:
            skip_reason = f"Floor breach: balance ${current_balance:.2f} < floor ${FLOOR_BALANCE:.2f}"

        if skip_reason:
            quant_detail = self._record_quant_detail(
                ticker,
                decision="SKIP",
                skip_reason=self._display_skip_reason(skip_reason),
                raw_skip_reason=skip_reason,
                final_size=0.0,
            )
            self._log_risk_section(
                bankroll=current_balance,
                tier=tier.value,
                base_risk_pct=calculate_base_risk_pct(current_balance),
                frequency_multiplier=frequency_multiplier_for_tier(tier_config, trades_last_hour),
                final_size=0.0,
                daily_drawdown_pct=daily_drawdown_pct,
                risk_off=risk_off,
                skip_reason=skip_reason,
            )
            return self._skip_outcome(
                market,
                "skip",
                0.0,
                skip_reason,
                seconds_remaining=seconds_to_close,
                entry_cutoff_seconds=entry_cutoff,
                extra_detail=timing_detail,
            )

        feed_age = self._feed_age_seconds(ptb_info)
        feed_age_log = -1.0 if feed_age is None else feed_age
        feed_threshold = float(self._setting("max_feed_age_seconds", 10.0))
        has_feed_timestamp = getattr(ptb_info, "last_updated", None) is not None or getattr(ptb_info, "feed_age_seconds", None) is not None
        try:
            has_valid_prices = float(ptb_info.current_price) > 0 and float(ptb_info.price_to_beat) > 0
        except (TypeError, ValueError):
            has_valid_prices = False
        if not has_feed_timestamp or feed_age is None or feed_age > feed_threshold or not has_valid_prices:
            LOGGER.info(
                "[RISK] market=%s skip_reason=stale_feed feed_age_seconds=%.3f threshold=%.3f",
                market.market_id,
                feed_age_log,
                feed_threshold,
            )
            self._log_risk_section(
                bankroll=current_balance,
                tier=tier.value,
                base_risk_pct=calculate_base_risk_pct(current_balance),
                frequency_multiplier=frequency_multiplier_for_tier(tier_config, trades_last_hour),
                final_size=0.0,
                daily_drawdown_pct=daily_drawdown_pct,
                risk_off=risk_off,
                skip_reason="stale_feed",
            )
            return self._skip_outcome(
                market,
                "skip",
                0.0,
                "stale_feed",
                seconds_remaining=seconds_to_close,
                entry_cutoff_seconds=entry_cutoff,
                extra_detail=timing_detail,
            )

        yes_bid = yes_ask = no_bid = no_ask = 0.0
        yes_bid_size = yes_ask_size = no_bid_size = no_ask_size = 0.0
        ob_spread = 0.0
        ob_liquidity_usd = float(market.liquidity or 0.0)
        orderbook_error = ""
        token_ids = self._real_token_ids.get(ticker)
        yes_token_id = token_ids[0] if token_ids else market.market_id
        no_token_id = token_ids[1] if token_ids else ""
        meta = self._market_token_meta.get(ticker, {})
        yes_orderbook_age_ms = 0
        no_orderbook_age_ms = 0
        token_mapping_warning = self._token_mapping_warning(ticker, token_ids, meta)
        if token_mapping_warning:
            skip_reason = f"token_mapping_warning:{token_mapping_warning}"
            detail = {
                **timing_detail,
                "token_id": yes_token_id,
                "yes_token_id": yes_token_id,
                "no_token_id": no_token_id,
                "market_slug": meta.get("slug", ""),
                "condition_id": meta.get("condition_id", ""),
                "outcome": "YES/NO",
                "source_module": "polymarket.trader",
                "token_mapping_warning": token_mapping_warning,
                "orderbook_error": skip_reason,
                "last_successful_orderbook_age_ms": self._last_orderbook_age_ms.get(ticker, 0),
                "retry_count": int(self._setting("api_retry_attempts", 1)),
            }
            self._emit_quant_event(
                "log_market_snapshot",
                {
                    "ticker": ticker,
                    "market_id": market.market_id,
                    **detail,
                },
            )
            self._log_risk_section(
                bankroll=current_balance,
                tier=tier.value,
                base_risk_pct=calculate_base_risk_pct(current_balance),
                frequency_multiplier=frequency_multiplier_for_tier(tier_config, trades_last_hour, liquidity=ob_liquidity_usd),
                final_size=0.0,
                daily_drawdown_pct=daily_drawdown_pct,
                risk_off=risk_off,
                skip_reason=skip_reason,
            )
            return self._skip_outcome(
                market,
                "skip",
                0.0,
                skip_reason,
                seconds_remaining=seconds_to_close,
                entry_cutoff_seconds=entry_cutoff,
                extra_detail=detail,
            )

        try:
            LOGGER.info(
                "[ORDERBOOK_FLOW] ticker=%s market_slug=%s condition_id=%s yes_token_id=%s no_token_id=%s",
                ticker,
                meta.get("slug", ""),
                meta.get("condition_id", ""),
                yes_token_id,
                no_token_id,
            )

            yes_ob = self.client.get_orderbook(yes_token_id)
            yes_bid, yes_ask = yes_ob.best_bid, yes_ob.best_ask
            yes_bid_size, yes_ask_size = yes_ob.bid_size, yes_ob.ask_size
            yes_orderbook_age_ms = self._orderbook_age_ms(yes_ob)
            LOGGER.info(
                "[ORDERBOOK_BEST] ticker=%s outcome=YES condition_id=%s token=%s bid=%.4f ask=%.4f spread=%.6f age=%.3fs",
                ticker,
                yes_ob.condition_id,
                yes_ob.token_id,
                yes_bid,
                yes_ask,
                yes_ob.spread,
                yes_ob.age_seconds,
            )

            if no_token_id:
                no_ob = self.client.get_orderbook(no_token_id)
                no_bid, no_ask = no_ob.best_bid, no_ob.best_ask
                no_bid_size, no_ask_size = no_ob.bid_size, no_ob.ask_size
                no_orderbook_age_ms = self._orderbook_age_ms(no_ob)
                token_mapping_warning = self._token_mapping_warning(ticker, token_ids, meta, yes_ob=yes_ob, no_ob=no_ob)
                LOGGER.info(
                    "[ORDERBOOK_BEST] ticker=%s outcome=NO condition_id=%s token=%s bid=%.4f ask=%.4f spread=%.6f age=%.3fs",
                    ticker,
                    no_ob.condition_id,
                    no_ob.token_id,
                    no_bid,
                    no_ask,
                    no_ob.spread,
                    no_ob.age_seconds,
                )
            elif yes_bid > 0 and yes_ask > 0:
                no_bid = max(0.01, 1.0 - yes_ask)
                no_ask = min(0.99, 1.0 - yes_bid)
                no_bid_size, no_ask_size = yes_ask_size, yes_bid_size

            if yes_bid > 0 and yes_ask > 0:
                ob_spread = yes_ask - yes_bid
            if no_bid > 0 and no_ask > 0:
                ob_spread = max(ob_spread, no_ask - no_bid)

            total_size = yes_bid_size + yes_ask_size + no_bid_size + no_ask_size
            prices = [p for p in (yes_bid, yes_ask, no_bid, no_ask) if p > 0]
            avg_price = sum(prices) / max(len(prices), 1)
            if total_size > 0:
                ob_liquidity_usd = total_size * avg_price
            if yes_orderbook_age_ms or no_orderbook_age_ms:
                self._last_orderbook_age_ms[ticker] = max(yes_orderbook_age_ms, no_orderbook_age_ms)
        except Exception as exc:
            orderbook_error = str(exc)
            LOGGER.warning(
                "[OB] Unavailable for %s token_id=%s market_slug=%s outcome=YES/NO last_successful_orderbook_age_ms=%s retry_count=%s error=%s",
                market.market_id,
                yes_token_id,
                meta.get("slug", ""),
                self._last_orderbook_age_ms.get(ticker, 0),
                int(self._setting("api_retry_attempts", 1)),
                exc,
            )

        self._emit_quant_event(
            "log_market_snapshot",
            {
                "ticker": ticker,
                "market_id": market.market_id,
                "market_slug": meta.get("slug", ""),
                "condition_id": meta.get("condition_id", ""),
                "yes_token_id": yes_token_id,
                "no_token_id": no_token_id,
                "token_id": yes_token_id,
                "outcome": "YES/NO",
                "source_module": "polymarket.trader",
                "yes_bid": float(yes_bid),
                "yes_ask": float(yes_ask),
                "yes_bid_size": float(yes_bid_size),
                "yes_ask_size": float(yes_ask_size),
                "yes_mid": (float(yes_bid) + float(yes_ask)) / 2.0 if yes_bid > 0 and yes_ask > 0 else 0.0,
                "no_bid": float(no_bid),
                "no_ask": float(no_ask),
                "no_bid_size": float(no_bid_size),
                "no_ask_size": float(no_ask_size),
                "no_mid": (float(no_bid) + float(no_ask)) / 2.0 if no_bid > 0 and no_ask > 0 else 0.0,
                "spread": float(ob_spread),
                "liquidity_usd": float(ob_liquidity_usd),
                "orderbook_error": orderbook_error,
                "orderbook_age_ms": max(yes_orderbook_age_ms, no_orderbook_age_ms),
                "orderbook_age": round(max(yes_orderbook_age_ms, no_orderbook_age_ms) / 1000.0, 3),
                "orderbook_age_seconds": round(max(yes_orderbook_age_ms, no_orderbook_age_ms) / 1000.0, 3),
                "yes_orderbook_age_ms": yes_orderbook_age_ms,
                "no_orderbook_age_ms": no_orderbook_age_ms,
                "oracle_age_ms": int(max(0.0, feed_age or 0.0) * 1000),
                "oracle_age": round(max(0.0, feed_age or 0.0), 3),
                "oracle_age_seconds": round(max(0.0, feed_age or 0.0), 3),
                "market_feed_age_ms": int(max(0.0, feed_age or 0.0) * 1000),
                "market_feed_age_seconds": round(max(0.0, feed_age or 0.0), 3),
                "last_successful_orderbook_age_ms": self._last_orderbook_age_ms.get(ticker, 0),
                "retry_count": int(self._setting("api_retry_attempts", 1)),
                "token_mapping_warning": token_mapping_warning,
                "seconds_remaining": int(getattr(ptb_info, "seconds_remaining", 0) or 0),
                "market_close_timestamp": timing_detail.get("market_close_timestamp", ""),
            },
        )

        if yes_ask <= 0 or no_ask <= 0 or token_mapping_warning:
            skip_reason = "stale_orderbook" if "stale_orderbook" in orderbook_error else "orderbook_unavailable"
            if token_mapping_warning:
                skip_reason = f"token_mapping_warning:{token_mapping_warning}"
            self._log_risk_section(
                bankroll=current_balance,
                tier=tier.value,
                base_risk_pct=calculate_base_risk_pct(current_balance),
                frequency_multiplier=frequency_multiplier_for_tier(tier_config, trades_last_hour, liquidity=ob_liquidity_usd),
                final_size=0.0,
                daily_drawdown_pct=daily_drawdown_pct,
                risk_off=risk_off,
                skip_reason=skip_reason,
            )
            return self._skip_outcome(
                market,
                "skip",
                0.0,
                skip_reason,
                seconds_remaining=seconds_to_close,
                entry_cutoff_seconds=entry_cutoff,
                extra_detail={
                    **timing_detail,
                    "token_id": yes_token_id,
                    "yes_token_id": yes_token_id,
                    "no_token_id": no_token_id,
                    "market_slug": meta.get("slug", ""),
                    "condition_id": meta.get("condition_id", ""),
                    "outcome": "YES/NO",
                    "source_module": "polymarket.trader",
                    "orderbook_error": orderbook_error,
                    "last_successful_orderbook_age_ms": self._last_orderbook_age_ms.get(ticker, 0),
                    "retry_count": int(self._setting("api_retry_attempts", 1)),
                    "token_mapping_warning": token_mapping_warning,
                },
            )

        decision_latency_ms = self._cycle_elapsed_ms()
        scan_cycle_duration_ms = self._last_scan_cycle_duration_ms or decision_latency_ms
        cutoff_decision = self._evaluate_entry_cutoff(
            seconds_remaining=seconds_to_close,
            static_cutoff_seconds=entry_cutoff,
            orderbook_age_ms=max(yes_orderbook_age_ms, no_orderbook_age_ms),
            oracle_age_ms=int(max(0.0, feed_age or 0.0) * 1000),
            decision_latency_ms=decision_latency_ms,
            scan_cycle_duration_ms=scan_cycle_duration_ms,
            spread=ob_spread,
        )
        cutoff_detail = self._cutoff_decision_detail(cutoff_decision)
        timing_detail.update(
            {
                **cutoff_detail,
                "decision_latency_ms": decision_latency_ms,
                "scan_cycle_duration_ms": scan_cycle_duration_ms,
            }
        )
        if not cutoff_decision.allowed:
            skip_reason = self._entry_cutoff_skip_reason(seconds_to_close, cutoff_decision)
            self._log_risk_section(
                bankroll=current_balance,
                tier=tier.value,
                base_risk_pct=calculate_base_risk_pct(current_balance),
                frequency_multiplier=frequency_multiplier_for_tier(tier_config, trades_last_hour, liquidity=ob_liquidity_usd),
                final_size=0.0,
                daily_drawdown_pct=daily_drawdown_pct,
                risk_off=risk_off,
                skip_reason=skip_reason,
            )
            return self._skip_outcome(
                market,
                "skip",
                0.0,
                skip_reason,
                seconds_remaining=seconds_to_close,
                entry_cutoff_seconds=entry_cutoff,
                extra_detail={
                    **timing_detail,
                    "token_id": yes_token_id,
                    "yes_token_id": yes_token_id,
                    "no_token_id": no_token_id,
                    "market_slug": meta.get("slug", ""),
                    "condition_id": meta.get("condition_id", ""),
                    "outcome": "YES/NO",
                    "source_module": "polymarket.trader",
                    "orderbook_age_ms": max(yes_orderbook_age_ms, no_orderbook_age_ms),
                    "oracle_age_ms": int(max(0.0, feed_age or 0.0) * 1000),
                    "spread": float(ob_spread),
                    "last_successful_orderbook_age_ms": self._last_orderbook_age_ms.get(ticker, 0),
                    "token_mapping_warning": token_mapping_warning,
                },
            )

        imbalance_total = yes_bid_size + yes_ask_size
        imbalance = (yes_bid_size - yes_ask_size) / imbalance_total if imbalance_total > 0 else 0.0
        signal: SignalResult = compute_realtime_signal(ticker, imbalance=imbalance)
        self.last_signals[ticker] = signal

        window_delta = float(ptb_info.current_price) - float(ptb_info.price_to_beat)
        momentum_decimal = float(signal.momentum_pct) / 100.0
        price_velocity = momentum_decimal / 5.0
        recent_volatility = max(abs(momentum_decimal), abs(float(ptb_info.price_diff_pct)) / 100.0) * max(signal.vol_ratio, 0.5)
        yes_mid = (yes_bid + yes_ask) / 2.0 if yes_bid > 0 and yes_ask > 0 else yes_ask

        probability = estimate_probability(ProbabilityModelInput(
            underlying_price=ptb_info.current_price,
            target_price=ptb_info.price_to_beat,
            distance_to_target=window_delta,
            time_remaining_seconds=ptb_info.seconds_remaining,
            recent_price_velocity=price_velocity,
            short_term_momentum=momentum_decimal,
            volatility=recent_volatility,
            orderbook_bid=yes_bid,
            orderbook_ask=yes_ask,
            spread=ob_spread,
            liquidity=ob_liquidity_usd,
            polymarket_implied_probability=yes_mid,
        ))
        confidence = probability.confidence_score

        delta = estimate_micro_delta(MicroDeltaInput(
            underlying_price=ptb_info.current_price,
            target_price=ptb_info.price_to_beat,
            distance_to_target=window_delta,
            time_remaining_seconds=ptb_info.seconds_remaining,
            recent_volatility=recent_volatility,
            recent_price_velocity=price_velocity,
            spread=ob_spread,
            liquidity=ob_liquidity_usd,
        ))

        ev_tier = ExpectedValueTier(name=tier.value, min_ev=0.02)
        candidate = OpportunityCandidate(
            market_id=market.market_id,
            asset=ticker,
            p_yes=probability.p_yes,
            p_no=probability.p_no,
            yes_ask=yes_ask,
            no_ask=no_ask,
            confidence_score=confidence,
            delta_score=delta.delta_score,
            delta_regime=delta.delta_regime,
            delta_multiplier=delta.delta_multiplier,
            spread=ob_spread,
            liquidity=ob_liquidity_usd,
            time_remaining_seconds=ptb_info.seconds_remaining,
            price_velocity=price_velocity,
            distance_to_strike=abs(window_delta) / max(float(ptb_info.price_to_beat), 1e-9),
            orderbook_bid_size=yes_bid_size,
            orderbook_ask_size=yes_ask_size,
            drawdown_pct=daily_drawdown_pct,
            trades_for_market=self._entry_count_for_market(market.market_id, ptb_info.epoch_start_ts),
        )
        scan = scan_opportunities(
            [candidate],
            OpportunityScanContext(
                ev_tier=ev_tier,
                bankroll_tier=tier,
                trades_last_hour=trades_last_hour,
                risk_off=risk_off,
                reconciliation_safe=not (self._last_reconciliation and self._last_reconciliation.block_new_trading),
                max_trades_per_market=int(self._setting("max_entries_per_market", 1)),
            ),
        )
        scored = scan.best_trade or (scan.watchlist[0] if scan.watchlist else scan.skipped[0] if scan.skipped else None)
        ev_result = scored.ev_result if scored else None
        model_side = ev_result.side if ev_result else "SKIP"
        entry_price = yes_ask if model_side == "YES" else no_ask if model_side == "NO" else yes_ask
        model_ev = ev_result.ev_yes if model_side == "YES" and ev_result else ev_result.ev_no if model_side == "NO" and ev_result else 0.0
        self._paper_record_model(confidence, model_ev, opportunity_found=scan.best_trade is not None)
        frequency_multiplier = frequency_multiplier_for_tier(tier_config, trades_last_hour, liquidity=ob_liquidity_usd)
        min_ev_required = ev_result.min_ev if ev_result else ev_tier.min_ev
        clob_detail = {
            "yes_bid": float(yes_bid),
            "yes_ask": float(yes_ask),
            "no_bid": float(no_bid),
            "no_ask": float(no_ask),
            "yes_mid": (float(yes_bid) + float(yes_ask)) / 2.0 if yes_bid > 0 and yes_ask > 0 else 0.0,
            "no_mid": (float(no_bid) + float(no_ask)) / 2.0 if no_bid > 0 and no_ask > 0 else 0.0,
            "spread": float(ob_spread),
            "token_id": yes_token_id if model_side != "NO" else no_token_id,
            "yes_token_id": yes_token_id,
            "no_token_id": no_token_id,
            "market_slug": meta.get("slug", ""),
            "condition_id": meta.get("condition_id", ""),
            "outcome": model_side,
            "source_module": "polymarket.trader",
            "orderbook_age_ms": max(yes_orderbook_age_ms, no_orderbook_age_ms),
            "orderbook_age": round(max(yes_orderbook_age_ms, no_orderbook_age_ms) / 1000.0, 3),
            "orderbook_age_seconds": round(max(yes_orderbook_age_ms, no_orderbook_age_ms) / 1000.0, 3),
            "yes_orderbook_age_ms": yes_orderbook_age_ms,
            "no_orderbook_age_ms": no_orderbook_age_ms,
            "oracle_age_ms": int(max(0.0, feed_age or 0.0) * 1000),
            "oracle_age": round(max(0.0, feed_age or 0.0), 3),
            "oracle_age_seconds": round(max(0.0, feed_age or 0.0), 3),
            "market_feed_age_ms": int(max(0.0, feed_age or 0.0) * 1000),
            "market_feed_age_seconds": round(max(0.0, feed_age or 0.0), 3),
            "token_mapping_warning": token_mapping_warning,
        }
        quant_detail = self._record_quant_detail(
            ticker,
            market_id=market.market_id,
            best_market=market.market_id,
            best_side=model_side,
            side=model_side,
            score=scan.best_trade.score if scan.best_trade else scored.score if scored else 0.0,
            p_yes=probability.p_yes,
            p_no=probability.p_no,
            ask_price=entry_price,
            ev=model_ev,
            min_ev=min_ev_required,
            confidence=confidence,
            delta_regime=delta.delta_regime.value,
            delta_multiplier=delta.delta_multiplier,
            final_size=0.0,
            frequency_multiplier=frequency_multiplier,
            decision=scan.decision.value,
            skip_reason=self._display_skip_reason(scored.skip_reason if scored and scored.skip_reason else ""),
            raw_skip_reason=scored.skip_reason if scored and scored.skip_reason else "",
            **timing_detail,
            **clob_detail,
        )

        if bool(self._setting("verbose_scan_logs", True)):
            self._log_section(
                "SCAN",
                (
                    f"markets=1 best={scan.best_trade.candidate.market_id if scan.best_trade else ''} "
                    f"score={scan.best_trade.score if scan.best_trade else 0.0:.4f} "
                    f"watchlist={len(scan.watchlist)} trades_last_hour={trades_last_hour} "
                    f"active_positions={len(self.tracker.open_positions())} decision={scan.decision.value}"
                ),
            )
        if bool(self._setting("verbose_model_logs", True)):
            self._log_section(
                "MODEL",
                (
                    f"p_yes={probability.p_yes:.4f} p_no={probability.p_no:.4f} "
                    f"confidence={confidence:.4f} momentum={self._momentum_label(momentum_decimal)} "
                    f"volatility={self._volatility_label(recent_volatility)} reason={probability.model_reason}"
                ),
            )
            self._log_section(
                "EV",
                (
                    f"side={model_side} ask={entry_price:.4f} ev={model_ev:.4f} "
                    f"min_ev={min_ev_required:.4f} edge={self._edge_label(model_ev, min_ev_required)} "
                    f"decision={'ENTER' if ev_result and ev_result.approved else 'SKIP'}"
                ),
            )
            self._log_section(
                "DELTA",
                (
                    f"score={delta.delta_score:.4f} regime={delta.delta_regime.value} "
                    f"multiplier={delta.delta_multiplier:.2f} distance={window_delta:.6f} "
                    f"time_left={int(ptb_info.seconds_remaining)}s spread={ob_spread:.4f} "
                    f"liquidity={self._liquidity_label(ob_liquidity_usd)}(${ob_liquidity_usd:.2f})"
                ),
            )

        quality_ok, quality_reason = trade_quality_allowed(
            self._risk_mode_state.current_mode,
            confidence=confidence,
        )
        skip_reason = ""
        if len(self._open_positions_for_market(market.market_id)) >= int(self._setting("max_active_positions_per_market", 1)):
            skip_reason = "Max active positions per market reached"
        elif self._entry_count_for_market(market.market_id, ptb_info.epoch_start_ts) >= int(self._setting("max_entries_per_market", 1)):
            skip_reason = "Max entries per market reached"
        elif self._placed_epochs.get(ticker) == ptb_info.epoch_start_ts:
            self._trigger_lockdown("duplicate_order")
            skip_reason = f"Max 1 trade per window (already placed for epoch {ptb_info.epoch_start_ts})"
        elif self._panic_sold_epochs.get(ticker) == ptb_info.epoch_start_ts:
            skip_reason = f"Panic sell cooldown (epoch {ptb_info.epoch_start_ts})"
        elif current_balance < FLOOR_BALANCE:
            skip_reason = f"Floor breach: balance ${current_balance:.2f} < floor ${FLOOR_BALANCE:.2f}"
        elif ob_spread > 0.10:
            skip_reason = f"ob_spread={ob_spread:.3f}>0.10"
        elif probability.skipped:
            skip_reason = f"probability_model: {probability.skip_reason}"
        elif delta.delta_regime == DeltaRegime.EXTREME or delta.delta_multiplier <= 0:
            skip_reason = "delta_extreme"
        elif not quality_ok:
            skip_reason = f"risk_mode_{self._risk_mode_state.current_mode.value.lower()}:{quality_reason}"
        elif not ev_result or not ev_result.approved or scan.decision != OpportunityDecision.BEST_TRADE:
            skip_reason = scored.skip_reason if scored and scored.skip_reason else "scanner_no_best_trade"

        if skip_reason:
            self._log_risk_section(
                bankroll=current_balance,
                tier=tier.value,
                base_risk_pct=calculate_base_risk_pct(current_balance),
                frequency_multiplier=frequency_multiplier,
                final_size=0.0,
                daily_drawdown_pct=daily_drawdown_pct,
                risk_off=risk_off,
                skip_reason=skip_reason,
            )
            outcome = self._skip_outcome(
                market,
                "skip",
                confidence,
                skip_reason,
                edge=model_ev,
                ev=model_ev,
                seconds_remaining=int(ptb_info.seconds_remaining),
                entry_cutoff_seconds=entry_cutoff,
                extra_detail=quant_detail,
            )
            return outcome

        trend = evaluate_trend_entry(TrendRunnerInput(side=model_side, momentum=momentum_decimal, price_velocity=price_velocity, ev=model_ev, confidence_score=confidence, tier=tier, spread=ob_spread, liquidity=ob_liquidity_usd, delta_regime=delta.delta_regime))
        lucky = evaluate_lucky_shot(LuckyShotInput(bankroll=current_balance, tier=tier, ev=model_ev, confidence_score=confidence, hard_stop_loss_pct=float(self._setting("execution_stop_loss_pct", 0.08)), daily_drawdown_pct=daily_drawdown_pct, consecutive_losses=getattr(self._risk_mgr._tier_mgr, "_consecutive_losses", 0)))
        quant_decision = "TREND_RUNNER" if trend.approved else "NORMAL_SCALP"
        size_multiplier = trend.trend_size_multiplier if trend.approved else 1.0
        if signal.strategy == "sniper" and lucky.approved and not trend.approved:
            quant_decision = "LUCKY_SHOT"
            size_multiplier = min(size_multiplier, lucky.risk_pct / max(tier_config.max_risk_pct, 1e-9))

        self.order_manager.account_balance = current_balance
        min_position_size_usd = max(float(self.settings.min_shares_per_order) * entry_price, 1.0)
        order_request = OrderRequest(market_id=market.market_id, side=model_side, entry_price=entry_price, win_rate=probability.p_yes if model_side == "YES" else probability.p_no, reward_risk_ratio=2.0, edge=model_ev, price_to_beat=ptb_info.price_to_beat, spread=ob_spread, liquidity_usd=ob_liquidity_usd, delta=delta.delta_score, delta_multiplier=delta.delta_multiplier, time_remaining_seconds=ptb_info.seconds_remaining, trades_last_hour=trades_last_hour, drawdown_pct=daily_drawdown_pct, min_position_size_usd=min_position_size_usd, daily_loss_limit_reached=risk_off, hard_drawdown_reached=daily_drawdown_pct >= 0.15)
        risk_plan = self.order_manager.build_order_plan(order_request)
        if risk_plan.position_size > 0 and size_multiplier < 1.0:
            risk_plan.risk_amount = round(risk_plan.risk_amount * size_multiplier, 6)
            risk_plan.position_size = round(risk_plan.position_size * size_multiplier, 6)
            risk_plan.notional_size = round(risk_plan.notional_size * size_multiplier, 6)
        if risk_plan.position_size > 0:
            self._apply_risk_mode_to_plan(risk_plan, risk_mode_decision)

        if risk_plan.position_size <= 0:
            quant_detail = self._record_quant_detail(
                ticker,
                decision="SKIP",
                skip_reason="ev_below_threshold",
                raw_skip_reason="risk_plan_zero",
                normalized_skip_reason="risk_plan_zero",
                edge=model_ev,
                ev=model_ev,
                seconds_remaining=int(ptb_info.seconds_remaining),
                entry_cutoff_seconds=entry_cutoff,
                time_bucket=classify_time_bucket(ptb_info.seconds_remaining, entry_cutoff),
                final_size=0.0,
                **{key: value for key, value in timing_detail.items() if key not in {"seconds_remaining", "entry_cutoff_seconds", "time_bucket"}},
                risk_plan_zero_diagnostics=self._risk_plan_zero_diagnostics(
                    risk_plan,
                    confidence=confidence,
                    edge=model_ev,
                ),
                **clob_detail,
            )
            self._log_risk_section(
                bankroll=current_balance,
                tier=tier.value,
                base_risk_pct=calculate_base_risk_pct(current_balance),
                frequency_multiplier=frequency_multiplier,
                final_size=0.0,
                daily_drawdown_pct=daily_drawdown_pct,
                risk_off=risk_off,
                skip_reason="risk_plan_zero",
            )
            self._paper_record_skip("Risk plan returned zero position size -- skipping.")
            outcome = TradeOutcome(market.market_id, market.question, "skip", confidence, risk_plan, None, True, "Risk plan returned zero position size -- skipping.", quant_detail)
            self._emit_decision_event(outcome, ticker=ticker)
            return outcome

        configured_market_cap = float(self._setting("max_risk_per_market", tier_config.max_market_exposure_pct))
        max_risk_per_market = min(configured_market_cap, tier_config.max_market_exposure_pct)
        current_market_exposure = sum(pos.notional_size for pos in self._open_positions_for_market(market.market_id))
        max_market_exposure = current_balance * max_risk_per_market
        remaining_market_capacity = max_market_exposure - current_market_exposure
        if remaining_market_capacity <= 0:
            skip_msg = f"Max risk per market exceeded: ${current_market_exposure + risk_plan.notional_size:.4f} > ${max_market_exposure:.4f} ({max_risk_per_market:.0%} bankroll)"
            quant_detail = self._record_quant_detail(
                ticker,
                decision="SKIP",
                skip_reason="risk_off",
                raw_skip_reason=skip_msg,
                final_size=0.0,
                **timing_detail,
                **clob_detail,
            )
            self._log_risk_section(
                bankroll=current_balance,
                tier=tier.value,
                base_risk_pct=calculate_base_risk_pct(current_balance),
                frequency_multiplier=frequency_multiplier,
                final_size=0.0,
                daily_drawdown_pct=daily_drawdown_pct,
                risk_off=risk_off,
                skip_reason=skip_msg,
            )
            self._paper_record_skip("Max risk per market exceeded")
            outcome = self._skip_outcome(
                market,
                "buy" if model_side == "YES" else "sell",
                confidence,
                skip_msg,
                risk_plan=risk_plan,
                extra_detail=timing_detail,
            )
            outcome.display.update(quant_detail)
            return outcome
        if risk_plan.notional_size > remaining_market_capacity:
            capped_notional = round(max(remaining_market_capacity, 0.0), 6)
            risk_plan.risk_amount = capped_notional
            risk_plan.notional_size = capped_notional
            risk_plan.position_size = round(capped_notional / max(entry_price, 1e-9), 6)
            risk_plan.capped_fraction = capped_notional / current_balance if current_balance > 0 else 0.0

        can_open, gate_reason = self.tracker.can_open(risk_plan.notional_size)
        if not can_open:
            skip_msg = f"Position tracker blocked: {gate_reason}"
            quant_detail = self._record_quant_detail(
                ticker,
                decision="SKIP",
                skip_reason="risk_off",
                raw_skip_reason=skip_msg,
                final_size=0.0,
                **timing_detail,
                **clob_detail,
            )
            self._log_risk_section(
                bankroll=current_balance,
                tier=tier.value,
                base_risk_pct=calculate_base_risk_pct(current_balance),
                frequency_multiplier=frequency_multiplier,
                final_size=0.0,
                daily_drawdown_pct=daily_drawdown_pct,
                risk_off=risk_off,
                skip_reason=skip_msg,
            )
            self._paper_record_skip(skip_msg)
            outcome = TradeOutcome(market.market_id, market.question, "skip", confidence, risk_plan, None, True, skip_msg, quant_detail)
            self._emit_decision_event(outcome, ticker=ticker)
            return outcome

        if risk_plan.position_size < self.settings.min_shares_per_order:
            skip_msg = f"Min shares: {risk_plan.position_size:.1f} < {self.settings.min_shares_per_order}"
            quant_detail = self._record_quant_detail(
                ticker,
                decision="SKIP",
                skip_reason="liquidity_too_low",
                raw_skip_reason=skip_msg,
                final_size=0.0,
                **timing_detail,
                **clob_detail,
            )
            self._log_risk_section(
                bankroll=current_balance,
                tier=tier.value,
                base_risk_pct=calculate_base_risk_pct(current_balance),
                frequency_multiplier=frequency_multiplier,
                final_size=0.0,
                daily_drawdown_pct=daily_drawdown_pct,
                risk_off=risk_off,
                skip_reason=skip_msg,
            )
            self._paper_record_skip(skip_msg)
            outcome = TradeOutcome(market.market_id, market.question, "skip", confidence, risk_plan, None, True, skip_msg, quant_detail)
            self._emit_decision_event(outcome, ticker=ticker)
            return outcome

        LOGGER.info("[DECISION] %s %s | mode=%s score=%.2f mom=%.3f%% delta_score=%.2f entry=%.4f shares=%.1f cost=$%.4f reason=quant_stack", ticker, model_side, quant_decision, signal.score, signal.momentum_pct, delta.delta_score, entry_price, risk_plan.position_size, risk_plan.notional_size)
        self._log_risk_section(
            bankroll=current_balance,
            tier=tier.value,
            base_risk_pct=calculate_base_risk_pct(current_balance),
            frequency_multiplier=frequency_multiplier,
            final_size=risk_plan.notional_size,
            daily_drawdown_pct=daily_drawdown_pct,
            risk_off=risk_off,
            force=True,
        )

        clob_token_id = market.market_id
        tids = self._real_token_ids.get(ticker)
        if tids:
            clob_token_id = tids[0] if model_side == "YES" else tids[1]
            LOGGER.info("[OrderToken] %s outcome=%s token_id=%s...", ticker, model_side, clob_token_id[:16])
        elif not self.settings.paper_trading:
            LOGGER.warning("[LiveOrder] %s - no real token_id cached, using synthetic (will fail)", ticker)

        if not self._verify_balance_for_order(risk_plan.notional_size, ticker):
            quant_detail = self._record_quant_detail(
                ticker,
                decision="SKIP",
                skip_reason="risk_off",
                raw_skip_reason="BALANCE_GUARD: insufficient funds for order",
                final_size=0.0,
                **timing_detail,
                **clob_detail,
            )
            self._log_risk_section(
                bankroll=current_balance,
                tier=tier.value,
                base_risk_pct=calculate_base_risk_pct(current_balance),
                frequency_multiplier=frequency_multiplier,
                final_size=0.0,
                daily_drawdown_pct=daily_drawdown_pct,
                risk_off=risk_off,
                skip_reason="BALANCE_GUARD: insufficient funds for order",
            )
            self._paper_record_skip("BALANCE_GUARD: insufficient funds for order")
            outcome = TradeOutcome(market.market_id, market.question, "skip", confidence, risk_plan, None, True, "BALANCE_GUARD: insufficient funds for order", quant_detail)
            self._emit_decision_event(outcome, ticker=ticker)
            return outcome

        receipt = self._submit_order(
            market_id=clob_token_id,
            side=BUY,
            price=entry_price,
            size=risk_plan.position_size,
            tier_label=tier.value,
            intent_type=OrderIntentType.ENTRY,
            risk_plan=risk_plan,
            source_market_id=market.market_id,
            outcome=model_side,
        )

        if receipt is not None:
            opened_pos = self.tracker.open_position(symbol=market.market_id, source="polymarket", side="BUY", entry_price=entry_price, size=risk_plan.position_size, stop_loss=risk_plan.stop_loss_price, take_profit=entry_price * (1 + float(self._setting("execution_take_profit_pct", 0.10))), order_id=receipt.order_id, metadata={"strategy": quant_decision, "signal_strategy": signal.strategy, "token_id": clob_token_id, "outcome": model_side, "entry_ev": model_ev, "confidence": confidence, "delta_regime": delta.delta_regime.value})
            self._placed_epochs[ticker] = ptb_info.epoch_start_ts
            self._record_market_entry(market.market_id, ptb_info.epoch_start_ts)
            self._paper_record_trade(risk_plan.notional_size)
            self._paper_record_position_state("FLAT", "PAPER_ENTRY_FILLED")
            quant_detail = self._record_quant_detail(
                ticker,
                decision="ENTER",
                mode=quant_decision,
                skip_reason="",
                raw_skip_reason="",
                final_size=risk_plan.notional_size,
                **timing_detail,
                **clob_detail,
            )
            self._record_display_trade(
                market=ticker,
                side=model_side,
                entry_price=entry_price,
                size=risk_plan.notional_size,
                reason="entry",
                mode=quant_decision,
                status=receipt.status,
            )
            self._emit_trade_opened_event(
                market_id=market.market_id,
                ticker=ticker,
                token_id=clob_token_id,
                outcome=model_side,
                receipt=receipt,
                risk_plan=risk_plan,
                entry_price=entry_price,
                strategy=quant_decision,
            )
            self._notify_telegram(
                "notify_entry",
                "",
                market=ticker,
                side=model_side,
                price=f"{entry_price:.4f}",
                size=f"{risk_plan.position_size:.6f}",
                status=receipt.status,
                dedup_key=f"entry:{receipt.order_id}",
            )
            LOGGER.info("[ENTRY] market=%s token=%s outcome=%s action=BUY entry=%.4f size=%.6f cost=%.4f", market.market_id, clob_token_id, model_side, entry_price, risk_plan.position_size, risk_plan.notional_size)

        outcome = TradeOutcome(market_id=market.market_id, question=market.question, decision="buy" if model_side == "YES" else "sell", confidence=confidence, risk_plan=risk_plan, receipt=receipt, skipped=False, skip_reason="", display=quant_detail)
        self._emit_decision_event(outcome, ticker=ticker)
        return outcome

    def _analyze_market(self, market: GammaMarket) -> TradeOutcome:
        ticker   = market.market_id.replace("pm-5m-", "").upper()
        ptb_info = self.ptb_tracker.get_market_ptb(ticker)
        return self._analyze_market_quant(market, ticker, ptb_info)

        direction = "ABOVE" if ptb_info.is_above_ptb else "BELOW"
        LOGGER.info(
            "Polymarket Price To Beat: $%.4f | Oracle Price: $%.4f (%s %.4f%%) | "
            "Market Window: %ds remaining | market_id=%s",
            ptb_info.price_to_beat,
            ptb_info.current_price,
            direction,
            abs(ptb_info.price_diff_pct),
            ptb_info.seconds_remaining,
            market.market_id,
        )

        current_balance = self.settings.account_balance
        tier = get_bankroll_tier(current_balance)

        # â”€â”€ 1. Orderbook snapshot (entry price + imbalance for signal) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        entry_price = 0.50
        imbalance   = 0.0
        ob_spread   = 0.0
        ob_liquidity_usd = 1_000.0
        try:
            token_ids = self._real_token_ids.get(ticker)
            ob_token_id = token_ids[0] if token_ids else market.market_id
            ob = self.client.get_orderbook(ob_token_id)
            if ob.best_bid > 0 and ob.best_ask > 0:
                total_size = ob.bid_size + ob.ask_size
                if total_size > 0:
                    imbalance = (ob.bid_size - ob.ask_size) / total_size
                    ob_liquidity_usd = total_size * ((ob.best_bid + ob.best_ask) / 2.0)
                ob_spread = ob.best_ask + (1.0 - ob.best_bid) - 1.0  # YES_ask + NO_ask - 1
                snipe = self._snipe_score(ob.best_ask, BACKTEST_WIN_RATE)
                if snipe >= self.settings.snipe_min_edge:
                    entry_price = round(ob.best_ask + 0.01, 4)
                else:
                    entry_price = (ob.best_bid + ob.best_ask) / 2.0
        except Exception:
            LOGGER.warning("[OB] Unavailable for %s â€” using default entry_price=0.50", market.market_id)

        # â”€â”€ 2. Counter-momentum signal (validated strategy) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        signal: SignalResult = compute_realtime_signal(ticker, imbalance=imbalance)
        self.last_signals[ticker] = signal
        window_delta = ptb_info.current_price - ptb_info.price_to_beat

        LOGGER.info(
            "[Signal] %s side=%s score=%.2f strategy=%s mom=%.3f%% rsi=%.1f vol=%.2f imb=%.3f | WinDelta=$%.4f",
            ticker, signal.side, signal.score, signal.strategy.upper(), signal.momentum_pct,
            signal.rsi, signal.vol_ratio, imbalance, window_delta,
        )

        quant_data = get_quant_feed().get_quant_data(ticker)
        LOGGER.info(
            "[Quant] %s OI=%.2f L/S=%.2f (L:%.1f%% S:%.1f%%)",
            ticker, quant_data.get("open_interest", 0.0),
            quant_data.get("long_short_ratio", 0.0),
            quant_data.get("ls_long_pct", 0.0) * 100,
            quant_data.get("ls_short_pct", 0.0) * 100
        )

        decision = "buy" if signal.side == "YES" else "sell" if signal.side == "NO" else "skip"

        # â”€â”€ 3. Win probability / Confidence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        momentum_norm = min(abs(signal.momentum_pct) / self.settings.strategy_mom_upper, 1.0)
        price_anchor  = max(0.0, 1.0 - abs(entry_price - 0.50) / 0.50)
        micro_prob = 0.50 + (
            0.45 * abs(imbalance) + 0.30 * momentum_norm + 0.25 * price_anchor
        ) * 0.35
        confidence = max(BACKTEST_WIN_RATE, min(micro_prob, 0.75))
        quant_edge = confidence - 0.50

        # ======================================================================
        # 4. SKIP GUARDS (Dashboard will show signal/conf even if skipped)
        # ======================================================================

        entry_cutoff = int(self._setting("execution_entry_cutoff_seconds", 90))
        if ptb_info.seconds_remaining < entry_cutoff:
            return self._skip_outcome(
                market,
                "skip",
                confidence,
                f"Entry cutoff: {ptb_info.seconds_remaining}s < {entry_cutoff}s",
            )

        max_active_per_market = int(self._setting("max_active_positions_per_market", 1))
        active_for_market = self._open_positions_for_market(market.market_id)
        if len(active_for_market) >= max_active_per_market:
            return self._skip_outcome(
                market,
                "skip",
                confidence,
                f"Max active positions per market reached ({len(active_for_market)}/{max_active_per_market})",
            )

        max_entries_per_market = int(self._setting("max_entries_per_market", 1))
        market_entry_count = self._entry_count_for_market(market.market_id, ptb_info.epoch_start_ts)
        if market_entry_count >= max_entries_per_market:
            return self._skip_outcome(
                market,
                "skip",
                confidence,
                f"Max entries per market reached ({market_entry_count}/{max_entries_per_market}) for epoch {ptb_info.epoch_start_ts}",
            )

        # Single Bet Per Window Guard
        if self._placed_epochs.get(ticker) == ptb_info.epoch_start_ts:
            self._trigger_lockdown("duplicate_order")
            LOGGER.info("[SKIP] %s already placed a bet for epoch %s", ticker, ptb_info.epoch_start_ts)
            return TradeOutcome(
                market_id=market.market_id, question=market.question, decision="skip",
                confidence=confidence, risk_plan=None, receipt=None, skipped=True,
                skip_reason=f"Max 1 trade per window (already placed for epoch {ptb_info.epoch_start_ts})"
            )

        # v3.2: Entry Timing Gate
        legacy_min_seconds = int(self._setting("entry_min_seconds_remaining", 30))
        if ptb_info.seconds_remaining < legacy_min_seconds:
            LOGGER.info(
                "[ENTRY_TIMING] %s SKIP â€” only %ds remaining < %ds minimum",
                ticker, ptb_info.seconds_remaining, legacy_min_seconds,
            )
            return TradeOutcome(
                market_id=market.market_id, question=market.question, decision="skip",
                confidence=confidence, risk_plan=None, receipt=None, skipped=True,
                skip_reason=f"Entry timing: {ptb_info.seconds_remaining}s < {legacy_min_seconds}s min",
            )

        # v3.2: Panic Sell Cooldown
        if self._panic_sold_epochs.get(ticker) == ptb_info.epoch_start_ts:
            LOGGER.info("[PANIC_COOLDOWN] %s SKIP â€” panic sold in this epoch", ticker)
            return TradeOutcome(
                market_id=market.market_id, question=market.question, decision="skip",
                confidence=confidence, risk_plan=None, receipt=None, skipped=True,
                skip_reason=f"Panic sell cooldown (epoch {ptb_info.epoch_start_ts})",
            )

        # Floor guard
        if current_balance < FLOOR_BALANCE:
            LOGGER.warning(
                "[FLOOR BREACH] Skipping market %s â€” balance $%.2f < floor $%.2f",
                market.market_id, current_balance, FLOOR_BALANCE,
            )
            return TradeOutcome(
                market_id=market.market_id, question=market.question,
                decision="skip", confidence=confidence,
                risk_plan=None, receipt=None, skipped=True,
                skip_reason=f"Floor breach: balance ${current_balance:.2f} < floor ${FLOOR_BALANCE:.2f}",
            )

        # Wide Spread Guard
        if ob_spread > 0.10:
            LOGGER.info("[OB] %s spread=%.3f > 10c â€” skip (wide market)", ticker, ob_spread)
            return TradeOutcome(
                market_id=market.market_id, question=market.question,
                decision="skip", confidence=confidence,
                risk_plan=None, receipt=None, skipped=True,
                skip_reason=f"ob_spread={ob_spread:.3f}>0.10",
            )

        if signal.side == "SKIP":
            return TradeOutcome(
                market_id=market.market_id, question=market.question,
                decision="skip", confidence=confidence,
                risk_plan=None, receipt=None, skipped=True,
                skip_reason=f"no_signal: {signal.skip_reason}",
            )

        # â”€â”€ v3.4: Sniper Strategy Max Price Guard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if signal.strategy == "sniper" and entry_price > self.settings.sniper_max_entry_price:
            return TradeOutcome(
                market_id=market.market_id, question=market.question,
                decision="skip", confidence=confidence,
                risk_plan=None, receipt=None, skipped=True,
                skip_reason=f"Sniper max entry price exceeded: {entry_price:.4f} > {self.settings.sniper_max_entry_price}",
            )

        # â”€â”€ Win probability via microstructure formula â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # WinProb = 0.50 + (0.45Ã—imbalance + 0.30Ã—momentum_norm + 0.25Ã—price_anchor) Ã— 0.35
        momentum_norm = min(abs(signal.momentum_pct) / self.settings.strategy_mom_upper, 1.0)
        price_anchor  = max(0.0, 1.0 - abs(entry_price - 0.50) / 0.50)
        micro_prob = 0.50 + (
            0.45 * abs(imbalance) + 0.30 * momentum_norm + 0.25 * price_anchor
        ) * 0.35
        confidence = max(BACKTEST_WIN_RATE, min(micro_prob, 0.75))
        quant_edge = confidence - 0.50

        portfolio = self.tracker.summary()
        request = OrderRequest(
            market_id=market.market_id,
            side=signal.side,
            entry_price=entry_price,
            win_rate=confidence,
            reward_risk_ratio=2.0,
            edge=confidence - entry_price,
            price_to_beat=ptb_info.price_to_beat,
            spread=ob_spread,
            liquidity_usd=ob_liquidity_usd,
            delta=abs(window_delta),
            time_remaining_seconds=ptb_info.seconds_remaining,
            trades_last_hour=len(self.tracker.open_positions()),
            drawdown_pct=portfolio.daily_drawdown_pct,
            min_position_size_usd=max(float(self.settings.min_shares_per_order) * entry_price, 1.0),
            daily_loss_limit_reached=portfolio.daily_drawdown_pct >= self.settings.max_daily_drawdown,
            hard_drawdown_reached=portfolio.daily_drawdown_pct >= 0.15,
        )
        risk_plan = self.order_manager.build_order_plan(request)

        if risk_plan.position_size <= 0:
            return TradeOutcome(
                market_id=market.market_id,
                question=market.question,
                decision=decision,
                confidence=confidence,
                risk_plan=risk_plan,
                receipt=None,
                skipped=True,
                skip_reason="Risk plan returned zero position size â€” skipping.",
            )

        tier_config = get_tier_config(tier)
        configured_market_cap = float(self._setting("max_risk_per_market", tier_config.max_market_exposure_pct))
        max_risk_per_market = min(configured_market_cap, tier_config.max_market_exposure_pct)
        current_market_exposure = sum(pos.notional_size for pos in self._open_positions_for_market(market.market_id))
        max_market_exposure = current_balance * max_risk_per_market
        if current_market_exposure + risk_plan.notional_size > max_market_exposure:
            return self._skip_outcome(
                market,
                decision,
                confidence,
                (
                    "Max risk per market exceeded: "
                    f"${current_market_exposure + risk_plan.notional_size:.4f} > "
                    f"${max_market_exposure:.4f} ({max_risk_per_market:.0%} bankroll)"
                ),
                risk_plan=risk_plan,
            )

        # Portfolio-level gate: check tracker limits before placing order
        can_open, gate_reason = self.tracker.can_open(risk_plan.notional_size)
        if not can_open:
            return TradeOutcome(
                market_id=market.market_id,
                question=market.question,
                decision=decision,
                confidence=confidence,
                risk_plan=risk_plan,
                receipt=None,
                skipped=True,
                skip_reason=f"Position tracker blocked: {gate_reason}",
            )

        # v3.2: Minimum Shares Guard â€” Polymarket requires â‰¥5 shares to sell
        if risk_plan.position_size < self.settings.min_shares_per_order:
            LOGGER.info(
                "[MIN_SHARES] %s SKIP â€” size=%.1f < min=%d shares",
                ticker, risk_plan.position_size, self.settings.min_shares_per_order,
            )
            return TradeOutcome(
                market_id=market.market_id, question=market.question,
                decision=decision, confidence=confidence,
                risk_plan=risk_plan, receipt=None, skipped=True,
                skip_reason=f"Min shares: {risk_plan.position_size:.1f} < {self.settings.min_shares_per_order}",
            )

        # v3.2: Enhanced Decision Summary Log
        LOGGER.info(
            "[DECISION] %s %s | score=%.2f mom=%.3f%% delta=$%.2f entry=%.4f "
            "shares=%.1f cost=$%.4f tp=%.1f%%/%.1f%% | reason=counter_momentum",
            ticker, signal.side, signal.score, signal.momentum_pct,
            window_delta, entry_price,
            risk_plan.position_size, risk_plan.notional_size,
            self.settings.tp_partial_pct * 100, self.settings.tp_full_pct * 100,
        )

        # Resolve real CLOB token ID for live orders (YES/NO token changes every 5 min)
        clob_token_id = market.market_id  # synthetic fallback (safe for paper)
        if not self.settings.paper_trading:
            tids = self._real_token_ids.get(ticker)
            if tids:
                clob_token_id = tids[0] if decision == "buy" else tids[1]
                LOGGER.info("[LiveOrder] %s using real token_id=%s...", ticker, clob_token_id[:16])
            else:
                LOGGER.warning("[LiveOrder] %s â€” no real token_id cached, using synthetic (will fail)", ticker)

        # v3.1: Balance Guard â€” verify funds before every order
        tids = self._real_token_ids.get(ticker)
        if tids:
            clob_token_id = tids[0] if signal.side == "YES" else tids[1]
            LOGGER.info("[OrderToken] %s outcome=%s token_id=%s...", ticker, signal.side, clob_token_id[:16])

        if not self._verify_balance_for_order(risk_plan.notional_size, ticker):
            return TradeOutcome(
                market_id=market.market_id, question=market.question,
                decision=decision, confidence=confidence,
                risk_plan=risk_plan, receipt=None, skipped=True,
                skip_reason="BALANCE_GUARD: insufficient funds for order",
            )

        receipt = self._submit_order(
            market_id=clob_token_id,
            side=BUY,
            price=entry_price,
            size=risk_plan.position_size,
            tier_label=tier.value,
            intent_type=OrderIntentType.ENTRY,
            risk_plan=risk_plan,
            source_market_id=market.market_id,
            outcome=signal.side,
        )

        # Register in tracker if order was placed
        if receipt is not None:
            self.tracker.open_position(
                symbol=market.market_id,
                source="polymarket",
                side=decision.upper(),
                entry_price=entry_price,
                size=risk_plan.position_size,
                stop_loss=risk_plan.stop_loss_price,
                take_profit=entry_price * (1 + float(self._setting("execution_take_profit_pct", 0.10))),
                order_id=receipt.order_id,
                metadata={"strategy": signal.strategy, "token_id": clob_token_id, "outcome": signal.side},
            )
            self._placed_epochs[ticker] = ptb_info.epoch_start_ts
            self._record_market_entry(market.market_id, ptb_info.epoch_start_ts)
            LOGGER.info(
                "[ENTRY] market=%s token=%s outcome=%s action=BUY entry=%.4f size=%.6f cost=%.4f",
                market.market_id, clob_token_id, signal.side, entry_price,
                risk_plan.position_size, risk_plan.notional_size,
            )

            bet_size    = risk_plan.notional_size
            edge_pct    = quant_edge * 100
            ptb_display = f"${ptb_info.price_to_beat:,.2f}" if ptb_info.price_to_beat > 0 else "N/A"
            LOGGER.info(
                "=== 5-MIN CYCLE COMPLETE === Bankroll: $%.2f | Tier: %s | "
                "Bet: $%.2f | Side: %s | Score: %.2f | Mom: %.3f%% | Edge: %.1f%% | PTB: %s",
                current_balance, tier.value.title(), bet_size, signal.side,
                signal.score, signal.momentum_pct, edge_pct, ptb_display,
            )

            from utils.telegram_reporter import build_trade_alert

            self._notify_telegram(
                "notify_entry",
                build_trade_alert(
                    asset=ticker,
                    signal=signal.side,
                    momentum_pct=signal.momentum_pct,
                    score=signal.score,
                    position_size=bet_size,
                    bankroll=current_balance,
                    entry_price=entry_price,
                    ptb_display=ptb_display,
                    paper=self.settings.paper_trading,
                ),
                dedup_key=f"entry:{receipt.order_id}",
                market=ticker,
            )

        return TradeOutcome(
            market_id=market.market_id,
            question=market.question,
            decision=decision,
            confidence=confidence,
            risk_plan=risk_plan,
            receipt=receipt,
            skipped=False,
            skip_reason="",
        )

    # ------------------------------------------------------------------
    # v3.1: Pre-Trade Balance Guard
    # ------------------------------------------------------------------

    def _verify_balance_for_order(self, cost_needed: float, ticker: str) -> bool:
        """Check that we have sufficient funds before placing an order.
        Polymarket has auto-claim â€” balance can change mid-cycle.
        Returns True if balance is sufficient.
        """
        if self.settings.paper_trading:
            available = self._paper_available_balance()
            if available < float(cost_needed):
                LOGGER.warning(
                    "[PAPER BALANCE_GUARD] %s BLOCKED -- paper_available_balance $%.2f < cost $%.2f",
                    ticker,
                    available,
                    cost_needed,
                )
                self._emit_risk_event(
                    "paper_balance_guard",
                    {
                        "ticker": ticker,
                        "balance": float(available),
                        "required": float(cost_needed),
                        "balance_source": self._balance_source,
                        "risk_plan_zero_reason": "insufficient_paper_balance",
                    },
                )
                return False
            LOGGER.info(
                "[PAPER BALANCE_GUARD] %s OK -- paper_available_balance $%.2f >= cost $%.2f",
                ticker,
                available,
                cost_needed,
            )
            return True

        try:
            live_balance = self._coerce_cash_balance(self.client.get_usdc_balance())
            self._last_verified_balance = live_balance
            self.bankroll_state.current_cash_balance = live_balance
            self._update_bankroll_state()
        except Exception as e:
            LOGGER.warning("[BALANCE_GUARD] Failed to fetch live balance: %s â€” using cached", e)
            live_balance = self._last_verified_balance or self.bankroll_state.current_cash_balance

        if live_balance < cost_needed:
            self._paused_insufficient_funds = True
            LOGGER.warning(
                "[BALANCE_GUARD] %s BLOCKED â€” balance $%.2f < cost $%.2f | AUTO PAUSE",
                ticker, live_balance, cost_needed,
            )
            self._emit_risk_event(
                "balance_guard",
                {
                    "ticker": ticker,
                    "balance": float(live_balance),
                    "required": float(cost_needed),
                    "balance_source": self._balance_source,
                },
            )
            self._notify_telegram(
                "notify_risk",
                (
                    f"BALANCE GUARD\n"
                    f"Blocked order for {ticker}\n"
                    f"Balance: ${live_balance:.2f}\n"
                    f"Required: ${cost_needed:.2f}\n"
                    f"Bot PAUSED until balance is sufficient"
                ),
                dedup_key=f"balance_guard:{ticker}",
                market=ticker,
                reason="balance_guard",
            )
            return False

        self._paused_insufficient_funds = False
        LOGGER.info("[BALANCE_GUARD] %s OK â€” balance $%.2f >= cost $%.2f", ticker, live_balance, cost_needed)
        return True

    def _close_position_with_retry(
        self,
        pos,
        reason: str,
        exit_price: float | None = None,
    ) -> bool:
        token_id = self._position_token_id(pos)
        price = exit_price if exit_price is not None else self._position_mark_price(pos)
        price = max(0.01, min(0.99, float(price)))
        attempts = int(self._setting("close_order_retry_attempts", 3))
        delay = float(self._setting("close_order_retry_delay_seconds", 0.5))

        for attempt in range(1, attempts + 1):
            receipt = self._submit_order(
                market_id=token_id,
                side=SELL,
                price=price,
                size=pos.size,
                intent_type=OrderIntentType.EXIT,
                source_market_id=pos.symbol,
                outcome=self._position_outcome(pos),
                position_id=pos.position_id,
            )
            if receipt is not None:
                closed = self.tracker.close_position(pos.position_id, price, reason=reason)
                pnl = (price - pos.entry_price) * pos.size
                self._risk_mgr.record_result(won=pnl >= 0, pnl=abs(pnl))
                if self.settings.paper_trading:
                    self._paper_record_close(pnl)
                    self._paper_apply_exit_cash(price * pos.size, pnl)
                    self._paper_record_position_state("OPEN", f"EXIT:{reason}")
                    self._paper_update_drawdown()
                    LOGGER.info(
                        "[PAPER EXIT] position=%s market=%s token=%s reason=%s exit_price=%.4f size=%.6f proceeds=%.4f",
                        pos.position_id,
                        pos.symbol,
                        token_id,
                        reason,
                        price,
                        pos.size,
                        price * pos.size,
                    )
                    LOGGER.info(
                        "[PAPER PNL] position=%s market=%s realized_pnl=%+.4f cash=$%.4f equity=$%.4f",
                        pos.position_id,
                        pos.symbol,
                        pnl,
                        self.bankroll_state.current_cash_balance,
                        self.bankroll_state.equity,
                    )
                LOGGER.warning(
                    "[%s] closed | position=%s market=%s token=%s price=%.4f size=%.6f attempt=%d/%d pnl=%.4f",
                    reason.upper(), pos.position_id, pos.symbol, token_id, price, pos.size,
                    attempt, attempts, pnl,
                )
                metadata = getattr(pos, "metadata", None) or {}
                self._record_display_trade(
                    market=self._ticker_from_market_id(pos.symbol),
                    side=str(metadata.get("outcome") or self._position_outcome(pos)),
                    entry_price=pos.entry_price,
                    exit_price=price,
                    size=pos.notional_size,
                    realized_pnl=pnl,
                    reason=reason,
                    mode=str(metadata.get("strategy", "--")),
                    status=receipt.status,
                )
                self._emit_trade_closed_event(
                    position=pos,
                    reason=reason,
                    exit_price=price,
                    size=pos.size,
                    pnl=pnl,
                    receipt=receipt,
                    partial=False,
                )
                self._notify_telegram(
                    "notify_exit",
                    "",
                    market=self._ticker_from_market_id(pos.symbol),
                    reason=reason,
                    pnl=f"{pnl:+.4f}",
                    status=receipt.status,
                    dedup_key=f"exit:{receipt.order_id}:{reason}",
                )
                self._partial_tp_taken.discard(pos.position_id)
                return True

            LOGGER.error(
                "[FAILED_ORDER] close failed | reason=%s position=%s market=%s token=%s attempt=%d/%d price=%.4f size=%.6f",
                reason, pos.position_id, pos.symbol, token_id, attempt, attempts, price, pos.size,
            )
            self._emit_quant_event(
                "log_execution",
                {
                    "event": "exit_submit_failed",
                    "reason": reason,
                    "position_id": pos.position_id,
                    "market_id": pos.symbol,
                    "token_id": token_id,
                    "attempt": attempt,
                    "attempts": attempts,
                    "price": float(price),
                    "size": float(pos.size),
                },
            )
            if attempt < attempts:
                time.sleep(delay)

        LOGGER.critical(
            "[CRITICAL_CLOSE_FAILED] position still open after %d attempts | reason=%s position=%s market=%s token=%s",
            attempts, reason, pos.position_id, pos.symbol, token_id,
        )
        self._emit_risk_event(
            "exit_failure",
            {
                "reason": reason,
                "position_id": pos.position_id,
                "market_id": pos.symbol,
                "token_id": token_id,
                "attempts": attempts,
            },
        )
        self._notify_telegram(
            "notify_critical",
            (
                "CRITICAL CLOSE FAILED\n"
                f"Market: {pos.symbol}\n"
                f"Position: {pos.position_id}\n"
                f"Reason: {reason}\n"
                f"Attempts: {attempts}"
            ),
            dedup_key=f"exit_failure:{pos.position_id}:{reason}",
            reason="exit_failure",
        )
        self._trigger_lockdown("exit_failure")
        return False

    def _reduce_position_with_retry(
        self,
        pos,
        reason: str,
        exit_price: float,
        size: float,
    ) -> bool:
        current_size = max(float(getattr(pos, "size", 0.0)), 0.0)
        sell_size = min(max(float(size), 0.0), current_size)
        if sell_size <= 0:
            return False
        if sell_size >= current_size - 1e-9:
            return self._close_position_with_retry(pos, reason=reason, exit_price=exit_price)

        token_id = self._position_token_id(pos)
        price = max(0.01, min(0.99, float(exit_price)))
        attempts = int(self._setting("close_order_retry_attempts", 3))
        delay = float(self._setting("close_order_retry_delay_seconds", 0.5))

        for attempt in range(1, attempts + 1):
            receipt = self._submit_order(
                market_id=token_id,
                side=SELL,
                price=price,
                size=sell_size,
                intent_type=OrderIntentType.EXIT,
                source_market_id=pos.symbol,
                outcome=self._position_outcome(pos),
                position_id=pos.position_id,
            )
            if receipt is not None:
                pnl = (price - float(pos.entry_price)) * sell_size
                pos.size = max(0.0, current_size - sell_size)
                pos.notional_size = float(pos.entry_price) * pos.size
                pos.realized_pnl = round(float(getattr(pos, "realized_pnl", 0.0)) + pnl, 6)
                self._risk_mgr.record_result(won=pnl >= 0, pnl=abs(pnl))
                if self.settings.paper_trading:
                    self._paper_record_close(pnl)
                    self._paper_apply_exit_cash(price * sell_size, pnl)
                    self._paper_record_position_state("OPEN", f"REDUCE:{reason}")
                    self._paper_update_drawdown()
                    LOGGER.info(
                        "[PAPER EXIT] position=%s market=%s token=%s reason=%s exit_price=%.4f size=%.6f proceeds=%.4f remaining=%.6f",
                        pos.position_id,
                        pos.symbol,
                        token_id,
                        reason,
                        price,
                        sell_size,
                        price * sell_size,
                        pos.size,
                    )
                    LOGGER.info(
                        "[PAPER PNL] position=%s market=%s realized_pnl=%+.4f cash=$%.4f equity=$%.4f",
                        pos.position_id,
                        pos.symbol,
                        pnl,
                        self.bankroll_state.current_cash_balance,
                        self.bankroll_state.equity,
                    )
                LOGGER.warning(
                    "[%s] reduced | position=%s market=%s token=%s price=%.4f size=%.6f remaining=%.6f attempt=%d/%d pnl=%.4f",
                    reason.upper(),
                    pos.position_id,
                    pos.symbol,
                    token_id,
                    price,
                    sell_size,
                    pos.size,
                    attempt,
                    attempts,
                    pnl,
                )
                metadata = getattr(pos, "metadata", None) or {}
                self._record_display_trade(
                    market=self._ticker_from_market_id(pos.symbol),
                    side=str(metadata.get("outcome") or self._position_outcome(pos)),
                    entry_price=pos.entry_price,
                    exit_price=price,
                    size=sell_size * float(pos.entry_price),
                    realized_pnl=pnl,
                    reason=reason,
                    mode=str(metadata.get("strategy", "--")),
                    status=receipt.status,
                )
                self._emit_trade_closed_event(
                    position=pos,
                    reason=reason,
                    exit_price=price,
                    size=sell_size,
                    pnl=pnl,
                    receipt=receipt,
                    partial=True,
                )
                self._notify_telegram(
                    "notify_exit",
                    "",
                    market=self._ticker_from_market_id(pos.symbol),
                    reason=reason,
                    pnl=f"{pnl:+.4f}",
                    status=receipt.status,
                    dedup_key=f"partial_exit:{receipt.order_id}:{reason}",
                )
                return True

            LOGGER.error(
                "[FAILED_ORDER] reduce failed | reason=%s position=%s market=%s token=%s attempt=%d/%d price=%.4f size=%.6f",
                reason,
                pos.position_id,
                pos.symbol,
                token_id,
                attempt,
                attempts,
                price,
                sell_size,
            )
            self._emit_quant_event(
                "log_execution",
                {
                    "event": "reduce_submit_failed",
                    "reason": reason,
                    "position_id": pos.position_id,
                    "market_id": pos.symbol,
                    "token_id": token_id,
                    "attempt": attempt,
                    "attempts": attempts,
                    "price": float(price),
                    "size": float(sell_size),
                },
            )
            if attempt < attempts:
                time.sleep(delay)

        LOGGER.critical(
            "[CRITICAL_REDUCE_FAILED] position still unchanged after %d attempts | reason=%s position=%s market=%s token=%s",
            attempts,
            reason,
            pos.position_id,
            pos.symbol,
            token_id,
        )
        self._emit_risk_event(
            "exit_failure",
            {
                "reason": reason,
                "position_id": pos.position_id,
                "market_id": pos.symbol,
                "token_id": token_id,
                "attempts": attempts,
                "partial": True,
            },
        )
        self._notify_telegram(
            "notify_critical",
            (
                "CRITICAL REDUCE FAILED\n"
                f"Market: {pos.symbol}\n"
                f"Position: {pos.position_id}\n"
                f"Reason: {reason}\n"
                f"Attempts: {attempts}"
            ),
            dedup_key=f"reduce_failure:{pos.position_id}:{reason}",
            reason="exit_failure",
        )
        self._trigger_lockdown("exit_failure")
        return False

    def _force_exit_position(self, pos, seconds_to_close: int, action: str, reason: str) -> bool:
        exit_price = self._position_mark_price(pos)
        LOGGER.warning(
            "[EXIT] market=%s action=%s seconds_to_close=%s reason=%s",
            pos.symbol,
            action,
            seconds_to_close,
            reason,
        )
        return self._close_position_with_retry(pos, reason=reason, exit_price=exit_price)

    def _exit_agent_check_position(self, pos, seconds_to_close: int) -> bool:
        action = self._exit_agent_action(seconds_to_close)
        if action is None:
            return False
        action_name, reason = action
        return self._force_exit_position(pos, seconds_to_close, action_name, reason)

    def _exit_agent_tick(self, market_id: str, ticker: str, seconds_to_close: int) -> None:
        if seconds_to_close <= int(self._setting("exit_agent_cancel_entries_seconds", 35)):
            self._cancel_entry_orders_for_market(
                market_id,
                ticker,
                seconds_to_close,
                "pre_close_cancel_entry",
            )
        for pos in list(self._open_positions_for_market(market_id)):
            self._exit_agent_check_position(pos, seconds_to_close)

    def enforce_pre_close_exits(self, countdown: int) -> None:
        force_exit_seconds = self._exit_agent_force_exit_seconds()
        if countdown > force_exit_seconds:
            return

        open_pos = self.tracker.open_positions()
        if not open_pos:
            return

        for pos in list(open_pos):
            self._exit_agent_check_position(pos, countdown)

    # ------------------------------------------------------------------
    # v3.1: Dynamic Panic Sell
    # ------------------------------------------------------------------

    def panic_sell_check(self, countdown: int) -> None:
        """Called every second from main.py realtime loop.

        Trigger window: countdown <= 20s AND position is LOSING.

        v3.3 Slippage Guard:
          Before executing a market sell we measure the cost of hitting the bid:
            slippage = fair_value - best_bid   (fair_value = mid of bid+ask)
          If slippage > panic_sell_max_slippage â†’ skip the sell and hold to settlement.
          Rationale: thin Polymarket orderbooks can have 10â€“20c spreads near expiry.
          Selling into that spread guarantees a worse outcome than letting the binary expire.
        """
        if countdown > 20:
            return

        open_pos = self.tracker.open_positions()
        if not open_pos:
            return

        delta_threshold = self.settings.panic_sell_delta_threshold
        max_slippage    = self.settings.panic_sell_max_slippage

        for pos in open_pos:
            ticker = pos.symbol.replace("pm-5m-", "").upper()
            try:
                state = self.ptb_tracker.get_state(ticker)
            except Exception:
                continue

            is_winning = (
                (pos.side == "BUY" and state.is_above_ptb) or
                (pos.side == "SELL" and not state.is_above_ptb)
            )

            if is_winning:
                LOGGER.debug("[PANIC_SELL] %s winning â€” hold for settlement", ticker)
                continue

            window_delta = abs(state.current_price - state.price_to_beat)
            delta_weak   = window_delta < delta_threshold

            if not (delta_weak or countdown <= 10):
                continue

            # â”€â”€ Slippage Guard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # Fetch the orderbook to measure the real cost of an immediate sell.
            exit_price = 0.01
            fair_value = 0.01
            ob_ok      = False
            try:
                ob = self.client.get_orderbook(self._position_token_id(pos))
                if ob.best_bid > 0 and ob.best_ask > 0:
                    exit_price = ob.best_bid
                    fair_value = (ob.best_bid + ob.best_ask) / 2.0
                    ob_ok      = True
                elif ob.best_bid > 0:
                    exit_price = ob.best_bid
                    fair_value = ob.best_bid
                    ob_ok      = True
            except Exception as exc:
                LOGGER.debug("[PANIC_SELL] %s orderbook unavailable: %s", ticker, exc)

            slippage = fair_value - exit_price  # cost of selling at bid vs mid

            if ob_ok and slippage > max_slippage:
                # Spread is too wide â€” selling now is worse than a losing settlement.
                # Hold to expiry and accept the binary outcome.
                LOGGER.warning(
                    "[PANIC_SELL] %s HOLD for settlement â€” slippage=%.3f > tolerance=%.3f "
                    "(bid=%.4f fair=%.4f countdown=%ds delta=$%.2f)",
                    ticker, slippage, max_slippage, exit_price, fair_value, countdown, window_delta,
                )
                self._emit_risk_event(
                    "panic_sell_blocked",
                    {
                        "ticker": ticker,
                        "countdown": int(countdown),
                        "slippage": float(slippage),
                        "max_slippage": float(max_slippage),
                    },
                )
                self._notify_telegram(
                    "notify_risk",
                    (
                        f"PANIC SELL BLOCKED - slippage too high\n"
                        f"Asset: {ticker} | Countdown: {countdown}s\n"
                        f"Slippage: {slippage:.3f} > max {max_slippage:.3f}\n"
                        f"Holding to settlement (binary outcome)"
                    ),
                    dedup_key=f"panic_block:{ticker}",
                    market=ticker,
                    reason="panic_sell_blocked",
                )
                continue  # do NOT sell â€” hold to expiry

            # Slippage is acceptable â€” proceed with exit
            LOGGER.warning(
                "[PANIC_SELL] %s %s EXITING | countdown=%ds delta=$%.2f "
                "bid=%.4f fair=%.4f slippage=%.3f",
                pos.side, ticker, countdown, window_delta, exit_price, fair_value, slippage,
            )

            self._close_position_with_retry(pos, reason="panic_sell", exit_price=exit_price)

            epoch_ts = int(time.time())
            epoch_ts = epoch_ts - (epoch_ts % 300)
            self._panic_sold_epochs[ticker] = epoch_ts

            self._notify_telegram(
                "notify_exit",
                (
                    f"PANIC SELL\n"
                    f"Asset: {ticker} ({pos.side})\n"
                    f"Countdown: {countdown}s | Delta: ${window_delta:.2f}\n"
                    f"Exit: {exit_price:.4f} | Slippage: {slippage:.4f} (OK)\n"
                    f"Auto-pause: next round skipped"
                ),
                dedup_key=f"panic_sell:{ticker}:{epoch_ts}",
                market=ticker,
                reason="panic_sell",
            )

    # ------------------------------------------------------------------
    # v3.5: Dynamic Tiered & Quant-Adjusted Stop Loss
    # ------------------------------------------------------------------

    def check_stop_loss(self, countdown: int) -> None:
        """Called every second from main.py realtime loop.
        Checks open positions for SL conditions:
        - Base SL is set by Bankroll Tier (e.g. 70% to 90% unrealized loss).
        - If the live Quant L/S Ratio strongly contradicts the position, SL tightens by 10%.
        - Exits the position to prevent a 100% loss (salvage capital).
        """
        open_pos = self.tracker.open_positions()
        if not open_pos:
            return

        stop_loss_pct = float(self._setting("execution_stop_loss_pct", 0.08))
        for pos in open_pos:
            mark_price = self._position_mark_price(pos)
            unrealized_pct = self._unrealized_pct(pos, mark_price)
            ticker = pos.symbol.replace("pm-5m-", "").upper()
            if unrealized_pct <= -stop_loss_pct:
                LOGGER.warning(
                    "[STOP_LOSS] market=%s position=%s ticker=%s unrealized=%.2f%% <= -%.2f%% exit_price=%.4f",
                    pos.symbol, pos.position_id, ticker, unrealized_pct * 100,
                    stop_loss_pct * 100, mark_price,
                )
                self._close_position_with_retry(pos, reason="stop_loss", exit_price=mark_price)
            else:
                LOGGER.debug(
                    "[STOP_LOSS] hold | market=%s position=%s unrealized=%.2f%% limit=-%.2f%%",
                    pos.symbol, pos.position_id, unrealized_pct * 100, stop_loss_pct * 100,
                )
        return

        current_balance = self.settings.account_balance
        tier = get_bankroll_tier(current_balance)
        base_sl_pct = float(self._setting("execution_stop_loss_pct", 0.08))

        for pos in open_pos:
            ticker = pos.symbol.replace("pm-5m-", "").upper()
            if getattr(pos, "status", "open") != "open":
                continue
            if self._exit_agent_check_position(pos, countdown):
                continue
            metadata = getattr(pos, "metadata", None)
            if not isinstance(metadata, dict):
                metadata = {}
                pos.metadata = metadata
            original_size = float(metadata.get("tp_original_size") or 0.0)
            if original_size <= 0:
                original_size = float(pos.size) * (2.0 if pos.position_id in self._partial_tp_taken else 1.0)
                metadata["tp_original_size"] = original_size
            try:
                state = self.ptb_tracker.get_state(ticker)
            except Exception:
                state = None

            # Calculate unrealized loss
            is_winning = (
                (pos.side == "BUY" and state.is_above_ptb) or
                (pos.side == "SELL" and not state.is_above_ptb)
            )
            if is_winning:
                continue

            # Quant-adjusted SL
            active_sl_pct = base_sl_pct
            try:
                quant_data = get_quant_feed().get_quant_data(ticker)
                ls_ratio = quant_data.get("long_short_ratio", 1.0)
                if ls_ratio > 0.0:
                    if pos.side == "BUY" and ls_ratio < 0.85:
                        active_sl_pct -= 0.10
                        LOGGER.debug("[STOP_LOSS] %s Quant adjustment (LS=%.2f < 0.85). SL tightened to %.0f%%", ticker, ls_ratio, active_sl_pct * 100)
                    elif pos.side == "SELL" and ls_ratio > 1.15:
                        active_sl_pct -= 0.10
                        LOGGER.debug("[STOP_LOSS] %s Quant adjustment (LS=%.2f > 1.15). SL tightened to %.0f%%", ticker, ls_ratio, active_sl_pct * 100)
            except Exception as e:
                LOGGER.debug("[STOP_LOSS] Failed to get Quant feed for %s: %s", ticker, e)

            # Measure current liquidation price against orderbook
            try:
                ob = self.client.get_orderbook(pos.symbol)
                current_price = ob.best_bid if ob.best_bid > 0 else pos.entry_price
            except Exception:
                current_price = pos.entry_price

            if current_price <= 0.01:
                continue

            unrealized_loss_pct = (pos.entry_price - current_price) / max(pos.entry_price, 1e-8)

            if unrealized_loss_pct >= active_sl_pct:
                fair_value = (ob.best_bid + ob.best_ask) / 2.0 if (ob.best_bid > 0 and ob.best_ask > 0) else current_price
                slippage = fair_value - current_price
                max_slippage = self.settings.panic_sell_max_slippage

                if slippage > max_slippage:
                    LOGGER.debug(
                        "[STOP_LOSS] %s BLOCKED â€” slippage %.3f > %.3f (bid=%.4f, fair=%.4f)",
                        ticker, slippage, max_slippage, current_price, fair_value
                    )
                    continue

                LOGGER.warning(
                    "[STOP_LOSS] %s %s STOPPED OUT | loss=%.1f%% >= %.1f%% | exit=%.4f (entry=%.4f) | Tier=%s",
                    pos.side, ticker, unrealized_loss_pct * 100, active_sl_pct * 100, current_price, pos.entry_price, tier.value
                )

                receipt = self._submit_order(
                    market_id=self._position_token_id(pos),
                    side=SELL,
                    price=current_price,
                    size=pos.size,
                    intent_type=OrderIntentType.EXIT,
                    source_market_id=pos.symbol,
                    outcome=self._position_outcome(pos),
                    position_id=pos.position_id,
                )
                if receipt is None:
                    continue
                pnl = pos.size * (current_price - pos.entry_price)
                self.tracker.close_position(pos.position_id, current_price, reason="stop_loss")
                self._risk_mgr.record_result(won=False, pnl=abs(pnl))
                if self.settings.paper_trading:
                    self._paper_record_close(pnl)
                    self._paper_apply_exit_cash(current_price * pos.size, pnl)
                    self._paper_update_drawdown()

                self._notify_telegram(
                    "notify_exit",
                    (
                        f"STOP LOSS HIT\n"
                        f"Asset: {ticker} ({pos.side})\n"
                        f"Loss: {unrealized_loss_pct*100:.1f}% (Limit: {active_sl_pct*100:.0f}%)\n"
                        f"Exit: {current_price:.4f} (Entry: {pos.entry_price:.4f})\n"
                        f"P&L: -${abs(pnl):.4f}"
                    ),
                    dedup_key=f"stop_loss:{pos.position_id}",
                    market=ticker,
                    reason="stop_loss",
                )

    # ------------------------------------------------------------------
    # v3.1: Take Profit + Let Profit Run
    # ------------------------------------------------------------------

    def check_take_profit(self, countdown: int) -> None:
        """Called every second from main.py realtime loop.
        Checks open positions for TP conditions:
        - Partial TP (50% of position) at tp_partial_pct (default 5%)
        - Full TP at tp_full_pct (default 10%)
        - Let Profit Run: if profit > partial but delta strong + time > 60s, hold
        """
        open_pos = self.tracker.open_positions()
        if not open_pos:
            return

        tp_partial = self.settings.tp_partial_pct
        tp_full = self.settings.tp_full_pct

        for pos in open_pos:
            ticker = pos.symbol.replace("pm-5m-", "").upper()
            if getattr(pos, "status", "open") != "open":
                continue
            if self._exit_agent_check_position(pos, countdown):
                continue
            metadata = getattr(pos, "metadata", None)
            if not isinstance(metadata, dict):
                metadata = {}
                pos.metadata = metadata
            original_size = float(metadata.get("tp_original_size") or 0.0)
            if original_size <= 0:
                original_size = float(pos.size) * (2.0 if pos.position_id in self._partial_tp_taken else 1.0)
                metadata["tp_original_size"] = original_size
            try:
                state = self.ptb_tracker.get_state(ticker)
            except Exception:
                state = None

            # v3.2: Dynamic TP Adjust â€” boost TP when entry price was better than expected
            pos_tp_partial = tp_partial
            pos_tp_full = tp_full
            if self.settings.dynamic_tp_enabled and pos.entry_price < 0.50:
                # Price advantage: how much cheaper than fair value (0.50) we bought
                price_advantage = (0.50 - pos.entry_price) / 0.50
                boost = price_advantage * self.settings.dynamic_tp_boost_factor
                pos_tp_partial = tp_partial * (1.0 + boost)
                pos_tp_full = tp_full * (1.0 + boost)
                LOGGER.debug(
                    "[DYNAMIC_TP] %s entry=%.4f advantage=%.1f%% â†’ partial=%.1f%% full=%.1f%%",
                    ticker, pos.entry_price, price_advantage * 100,
                    pos_tp_partial * 100, pos_tp_full * 100,
                )

            # Calculate unrealized profit percentage
            current_price = self._position_mark_price(pos)
            unrealized_pct = (current_price - pos.entry_price) / max(pos.entry_price, 1e-8)
            is_winning = unrealized_pct > 0
            if not is_winning:
                continue

            window_delta = 0.0
            if state is not None:
                try:
                    window_delta = abs(float(state.current_price) - float(state.price_to_beat))
                except Exception:
                    window_delta = 0.0

            # v3.4: Sniper Strategy bias -> no partial TP, always let profit run
            if pos.metadata and pos.metadata.get("strategy") == "sniper":
                pos_tp_full = max(pos_tp_full, 0.85) # Aim for 85 cents
                pos_tp_partial = 1.0 # Disable partial TP

            # â”€â”€ Synthetic Auto-Redeem (Early Exit) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # Prevent capital from being locked in winning shares by selling at the Bid
            # just before market resolves, immediately freeing up bankroll.
            if countdown <= 30 and is_winning and current_price >= 0.90:
                LOGGER.info(
                    "[AUTO_REDEEM] %s Synthetic Redeem â€” countdown=%ds | forcing sell at %.4f to recycle capital",
                    ticker, countdown, current_price
                )
                self._close_position_with_retry(pos, reason="auto_redeem", exit_price=current_price)

                self._notify_telegram(
                    "notify_exit",
                    (
                        f"AUTO-REDEEM (EARLY EXIT)\n"
                        f"Asset: {ticker}\n"
                        f"Action: Claimed at {current_price:.4f} (Recycled)"
                    ),
                    dedup_key=f"auto_redeem_exit:{pos.position_id}",
                    market=ticker,
                    reason="auto_redeem",
                )
                continue

            # â”€â”€ Full TP â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            tp1_taken = bool(metadata.get("tp1_taken")) or pos.position_id in self._partial_tp_taken
            tp2_taken = bool(metadata.get("tp2_taken"))
            min_order_size = float(self._setting("min_shares_per_order", 1))
            risk_mode_decision = self._update_risk_mode()

            let_runner = (
                bool(self._setting("let_profit_run", True))
                and risk_mode_decision.mode not in {RiskMode.MICRO_RECOVERY, RiskMode.LOCKDOWN}
                and countdown > int(self._setting("let_profit_run_min_seconds", 60))
                and window_delta > 10.0
            )
            if unrealized_pct >= pos_tp_full and tp1_taken and not tp2_taken and let_runner:
                runner_fraction = max(0.0, min(float(self._setting("tp_runner_fraction", 0.25)), 0.50))
                runner_size = min(float(pos.size), max(original_size * runner_fraction, min_order_size))
                sell_size = max(0.0, float(pos.size) - runner_size)
                if sell_size >= min_order_size:
                    LOGGER.info(
                        "[LET_PROFIT_RUN] %s TP2 runner | unrealized=%.1f%% delta=$%.2f time=%ds selling=%.6f runner=%.6f",
                        ticker, unrealized_pct * 100, window_delta, countdown, sell_size, runner_size,
                    )
                    if self._reduce_position_with_retry(pos, reason="take_profit_runner", exit_price=current_price, size=sell_size):
                        metadata["tp2_taken"] = True
                        metadata["runner_active"] = True
                else:
                    metadata["tp2_taken"] = True
                    metadata["runner_active"] = True
                    LOGGER.info(
                        "[LET_PROFIT_RUN] %s runner already small | size=%.6f runner_target=%.6f",
                        ticker, float(pos.size), runner_size,
                    )
                continue

            if unrealized_pct >= pos_tp_full and tp1_taken and not tp2_taken:
                LOGGER.info(
                    "[TAKE_PROFIT] %s FULL TP â€” unrealized=%.1f%% >= %.1f%% | selling 100%%",
                    ticker, unrealized_pct * 100, pos_tp_full * 100,
                )
                self._close_position_with_retry(pos, reason="take_profit_full", exit_price=current_price)

                self._notify_telegram(
                    "notify_exit",
                    (
                        f"TAKE PROFIT (FULL)\n"
                        f"Asset: {ticker}\n"
                        f"Profit: {unrealized_pct*100:.1f}%"
                    ),
                    dedup_key=f"tp_full:{pos.position_id}",
                    market=ticker,
                    reason="take_profit_full",
                )
                continue

            # â”€â”€ Partial TP (sell 50%) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if unrealized_pct >= pos_tp_partial and not tp1_taken:
                half_size = min(float(pos.size), max(0.0, original_size * 0.50))
                if half_size < min_order_size:
                    continue  # Too small to split

                LOGGER.info(
                    "[TAKE_PROFIT] %s PARTIAL TP â€” unrealized=%.1f%% >= %.1f%% | selling 50%%",
                    ticker, unrealized_pct * 100, pos_tp_partial * 100,
                )
                if self._reduce_position_with_retry(pos, reason="take_profit_partial", exit_price=current_price, size=half_size):
                    metadata["tp1_taken"] = True
                    self._partial_tp_taken.add(pos.position_id)
                else:
                    continue

                self._notify_telegram(
                    "notify_exit",
                    (
                        f"TAKE PROFIT (PARTIAL 50%)\n"
                        f"Asset: {ticker}\n"
                        f"Profit: {unrealized_pct*100:.1f}%\n"
                        f"Sold: {half_size:.2f} shares (holding rest)"
                    ),
                    dedup_key=f"tp_partial:{pos.position_id}",
                    market=ticker,
                    reason="take_profit_partial",
                )

                if unrealized_pct >= pos_tp_full and not bool(metadata.get("tp2_taken")):
                    let_runner_after_partial = (
                        bool(self._setting("let_profit_run", True))
                        and countdown > int(self._setting("let_profit_run_min_seconds", 60))
                        and window_delta > 10.0
                    )
                    if let_runner_after_partial:
                        runner_fraction = max(0.0, min(float(self._setting("tp_runner_fraction", 0.25)), 0.50))
                        runner_size = min(float(pos.size), max(original_size * runner_fraction, min_order_size))
                        sell_size = max(0.0, float(pos.size) - runner_size)
                        if sell_size >= min_order_size:
                            if self._reduce_position_with_retry(pos, reason="take_profit_runner", exit_price=current_price, size=sell_size):
                                metadata["tp2_taken"] = True
                                metadata["runner_active"] = True
                        else:
                            metadata["tp2_taken"] = True
                            metadata["runner_active"] = True
                    else:
                        self._close_position_with_retry(pos, reason="take_profit_full", exit_price=current_price)

    # ------------------------------------------------------------------
    # Order submission
    # ------------------------------------------------------------------

    def _compute_limit_price(
        self,
        tier_label: str,
        ob_best_bid: float,
        ob_best_ask: float,
        side: str,
    ) -> float:
        """Compute a tier-appropriate limit price for ENTRY orders.

        Strategy:
          micro ($0-$10)        â€” BUY at best_ask - 0.002  (tight, every cent matters)
          small ($10-$100)      â€” BUY at best_ask - 0.001  (standard, quick fill OK)
          conservative ($100+)  â€” BUY at best_ask - 0.003  (patient, better fill)
          balanced ($1K+)       â€” BUY at best_bid + 0.005  (passive, wait for sellers)
          growth ($10K+)        â€” BUY at best_bid + 0.003  (large, avoid market impact)

        For SELL orders, logic is mirrored (try to get above best_bid).
        Falls back to mid-price if orderbook is empty.
        """
        mid = (ob_best_bid + ob_best_ask) / 2.0 if (ob_best_bid > 0 and ob_best_ask > 0) else 0.0
        if mid <= 0:
            return 0.0  # No orderbook â€” caller will use signal price as fallback

        # Tier-based offset config: {label: (buy_offset_from_ask, sell_offset_from_bid)}
        _TIER_OFFSETS: dict[str, tuple[float, float]] = {
            "micro":        (-0.002, +0.002),  # BUY 0.2Â¢ below ask | SELL 0.2Â¢ above bid
            "small":        (-0.001, +0.001),  # BUY 0.1Â¢ below ask | SELL 0.1Â¢ above bid
            "conservative": (-0.003, +0.003),  # BUY 0.3Â¢ below ask | SELL 0.3Â¢ above bid
            "balanced":     (-0.005, +0.005),  # BUY 0.5Â¢ below ask | SELL 0.5Â¢ above bid
            "growth":       (-0.003, +0.003),  # BUY passive        | SELL passive
        }
        buy_off, sell_off = _TIER_OFFSETS.get(tier_label, (-0.001, +0.001))

        if side == "BUY":
            raw = ob_best_ask + buy_off  # negative offset = undercut ask
        else:
            raw = ob_best_bid + sell_off  # positive offset = above bid

        # Clamp to valid binary range (0.01 â€“ 0.99)
        price = round(max(0.01, min(0.99, raw)), 4)
        LOGGER.info(
            "[LIMIT_PRICE] tier=%s side=%s bid=%.4f ask=%.4f -> limit=%.4f",
            tier_label, side, ob_best_bid, ob_best_ask, price,
        )
        return price

    def _reconciliation_safe_for_entry(self) -> bool:
        return not (self._last_reconciliation and self._last_reconciliation.block_new_trading)

    def _tracked_exit_inventory_size(self, position_id: str, token_id: str) -> float:
        if not position_id:
            return 0.0
        for pos in self.tracker.open_positions():
            if getattr(pos, "position_id", "") != position_id:
                continue
            if self._position_token_id(pos) != token_id:
                return 0.0
            return max(float(getattr(pos, "size", 0.0) or 0.0), 0.0)
        return 0.0

    def _validate_submit_order_intent(
        self,
        *,
        market_id: str,
        side: str,
        price: float,
        size: float,
        intent_type: OrderIntentType | str | None,
        risk_plan: RiskPlan | None = None,
        source_market_id: str = "",
        outcome: str = "",
        position_id: str = "",
    ) -> bool:
        if intent_type is None:
            LOGGER.error(
                "[ORDER_INTENT_BLOCKED] token=%s side=%s size=%.6f reason=missing_order_intent",
                market_id,
                side,
                size,
            )
            self._emit_quant_event(
                "log_execution",
                {
                    "event": "order_intent_reject",
                    "reason": "missing_order_intent",
                    "token_id": market_id,
                    "side": side,
                    "price": float(price),
                    "size": float(size),
                    "source_market_id": source_market_id,
                    "outcome": outcome,
                    "position_id": position_id,
                },
            )
            return False

        intent_kind = intent_type if isinstance(intent_type, OrderIntentType) else OrderIntentType(str(intent_type).upper())
        tracked_inventory = (
            self._tracked_exit_inventory_size(position_id, market_id)
            if intent_kind == OrderIntentType.EXIT
            else 0.0
        )
        decision = validate_order_intent(OrderIntent(
            intent_type=intent_kind,
            token_id=market_id,
            side=side,
            price=price,
            size=size,
            market_id=source_market_id,
            outcome=outcome,
            position_id=position_id,
            risk_plan_present=risk_plan is not None,
            risk_approved=bool(risk_plan and risk_plan.position_size > 0 and risk_plan.notional_size > 0),
            reconciliation_safe=self._reconciliation_safe_for_entry(),
            lockdown_active=self._risk_mode_state.current_mode == RiskMode.LOCKDOWN,
            tracked_inventory_size=tracked_inventory,
        ))
        if decision.approved:
            LOGGER.info(
                "[ORDER_INTENT] approved intent=%s token=%s side=%s outcome=%s position=%s size=%.6f reason=%s",
                intent_kind.value,
                market_id,
                side,
                outcome or "--",
                position_id or "--",
                size,
                decision.reason,
            )
            self._emit_quant_event(
                "log_execution",
                {
                    "event": "order_intent_approved",
                    "intent": intent_kind.value,
                    "token_id": market_id,
                    "side": side,
                    "price": float(price),
                    "size": float(size),
                    "source_market_id": source_market_id,
                    "outcome": outcome,
                    "position_id": position_id,
                    "reason": decision.reason,
                    "tracked_inventory_size": float(tracked_inventory),
                    "mode": self._runtime_mode(),
                },
            )
            return True

        LOGGER.error(
            "[ORDER_INTENT_BLOCKED] intent=%s token=%s side=%s outcome=%s position=%s size=%.6f reason=%s",
            intent_kind.value,
            market_id,
            side,
            outcome or "--",
            position_id or "--",
            size,
            decision.reason,
        )
        self._emit_quant_event(
            "log_execution",
            {
                "event": "order_intent_reject",
                "intent": intent_kind.value,
                "token_id": market_id,
                "side": side,
                "price": float(price),
                "size": float(size),
                "source_market_id": source_market_id,
                "outcome": outcome,
                "position_id": position_id,
                "reason": decision.reason,
                "tracked_inventory_size": float(tracked_inventory),
                "mode": self._runtime_mode(),
            },
        )
        self._paper_record_skip(f"order_intent:{decision.reason}")
        return False

    def _submit_order(
        self,
        market_id: str,
        side: str,
        price: float,
        size: float,
        tier_label: str = "micro",
        *,
        intent_type: OrderIntentType | str | None = None,
        risk_plan: RiskPlan | None = None,
        source_market_id: str = "",
        outcome: str = "",
        position_id: str = "",
    ) -> OrderReceipt | None:
        """Submit a limit order with tier-appropriate price offset.

        For paper trading: logs intent and returns a synthetic receipt.
        For live trading: fetches live orderbook and applies tier offset to get best fill.
        """
        if not self._validate_submit_order_intent(
            market_id=market_id,
            side=side,
            price=price,
            size=size,
            intent_type=intent_type,
            risk_plan=risk_plan,
            source_market_id=source_market_id,
            outcome=outcome,
            position_id=position_id,
        ):
            return None

        intent_name = (
            intent_type.value
            if isinstance(intent_type, OrderIntentType)
            else str(intent_type or "")
        )

        # â”€â”€ Tier-based live limit price calculation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        live_limit_price = price  # default: use signal price
        if not self.settings.paper_trading:
            try:
                ob = self.client.get_orderbook(market_id)
                if ob.best_bid > 0 or ob.best_ask > 0:
                    computed = self._compute_limit_price(
                        tier_label=tier_label,
                        ob_best_bid=ob.best_bid,
                        ob_best_ask=ob.best_ask,
                        side=side,
                    )
                    if computed > 0:
                        live_limit_price = computed
            except Exception as e:
                LOGGER.warning("[LIMIT_PRICE] Orderbook unavailable (%s) â€” using signal price %.4f", e, price)

        self._emit_quant_event(
            "log_execution",
            {
                "event": "order_submit_attempt",
                "intent": intent_name,
                "token_id": market_id,
                "source_market_id": source_market_id,
                "outcome": outcome,
                "position_id": position_id,
                "side": side,
                "signal_price": float(price),
                "limit_price": float(live_limit_price),
                "size": float(size),
                "paper": bool(self.settings.paper_trading),
                "mode": self._runtime_mode(),
            },
        )

        if self.settings.paper_trading:
            self.paper_stats.paper_orders_created += 1
            LOGGER.info(
                "[PAPER ORDER] side=%s type=LIMIT market=%s tier=%s price=%.4f size=%.6f live_orders=OFF",
                side, market_id, tier_label, live_limit_price, size,
            )
            receipt = OrderReceipt(
                order_id="paper-" + market_id[:8],
                status="paper",
                token_id=market_id,
                price=live_limit_price,
                size=size,
                side=side,
                filled_size=size,
                remaining_size=0.0,
                created_at=datetime.now().isoformat(),
                order_type="GTC",
            )
            LOGGER.info(
                "[PAPER FILL] order_id=%s token=%s side=%s price=%.4f size=%.6f filled=%.6f remaining=%.6f",
                receipt.order_id,
                receipt.token_id,
                receipt.side,
                receipt.price,
                receipt.size,
                receipt.filled_size,
                receipt.remaining_size,
            )
            self.paper_stats.paper_fills += 1
            self._emit_quant_event(
                "log_execution",
                {
                    "event": "paper_fill",
                    "intent": intent_name,
                    "token_id": market_id,
                    "source_market_id": source_market_id,
                    "outcome": outcome,
                    "position_id": position_id,
                    "receipt": asdict(receipt),
                    "mode": self._runtime_mode(),
                },
            )
            self._log_order_section(
                order_type="LIMIT_BUY" if side == BUY else "LIMIT_SELL",
                size=size,
                price=live_limit_price,
                status="PAPER",
            )
            return receipt

        clob_side = BUY if side == "BUY" else SELL
        try:
            receipt = self.client.place_limit_order(
                token_id=market_id,
                price=live_limit_price,
                size=size,
                side=clob_side,
            )
            self._log_order_section(
                order_type="LIMIT_BUY" if side == BUY else "LIMIT_SELL",
                size=size,
                price=live_limit_price,
                status=str(receipt.status or "SUBMITTED").upper(),
            )
            self._emit_quant_event(
                "log_execution",
                {
                    "event": "live_order_submitted",
                    "intent": intent_name,
                    "token_id": market_id,
                    "source_market_id": source_market_id,
                    "outcome": outcome,
                    "position_id": position_id,
                    "receipt": asdict(receipt),
                    "mode": self._runtime_mode(),
                },
            )
            self._reconcile_after_order_attempt()
            return receipt
        except Exception:
            self._log_order_section(
                order_type="LIMIT_BUY" if side == BUY else "LIMIT_SELL",
                size=size,
                price=live_limit_price,
                status="FAILED",
            )
            LOGGER.exception(
                "[FAILED_ORDER] Order submission failed | market=%s side=%s price=%.4f size=%.6f",
                market_id, side, live_limit_price, size,
            )
            self._emit_quant_event(
                "log_execution",
                {
                    "event": "order_submit_failed",
                    "intent": intent_name,
                    "token_id": market_id,
                    "source_market_id": source_market_id,
                    "outcome": outcome,
                    "position_id": position_id,
                    "side": side,
                    "limit_price": float(live_limit_price),
                    "size": float(size),
                    "mode": self._runtime_mode(),
                },
            )
            self._trigger_lockdown("api_order_failure")
            self._reconcile_after_order_attempt()
            return None

    # ------------------------------------------------------------------
    # Auto-Redeem (claim settled winnings before each cycle)
    # ------------------------------------------------------------------

    def auto_redeem_cycle(self) -> float:
        """Check for any settled positions with unclaimed USDC and redeem them.

        Called at the start of every run_single_cycle() to ensure the bankroll
        always reflects the true available balance including pending winnings.

        Returns:
            total_redeemed (float): Total USDC claimed in this cycle.
        """
        if self.settings.paper_trading:
            # Paper mode: simulate a check without calling real API
            LOGGER.info("[AUTO_REDEEM] Paper mode â€” skipping real redeem check.")
            return 0.0

        total_redeemed = 0.0
        try:
            redeemable = self.client.get_redeemable_positions()
            if not redeemable:
                LOGGER.debug("[AUTO_REDEEM] No redeemable positions found.")
                return 0.0

            LOGGER.info("[AUTO_REDEEM] Found %d positions to redeem.", len(redeemable))

            for pos in redeemable:
                token_id = pos.get("token_id", "")
                size     = pos.get("size", 0.0)
                outcome  = pos.get("outcome", "?")

                if not token_id or size <= 0:
                    continue

                amount = self.client.redeem_position(token_id=token_id, size=size)
                if amount > 0:
                    total_redeemed += amount
                    LOGGER.info(
                        "[AUTO_REDEEM] Redeemed $%.4f | token=%s outcome=%s",
                        amount, token_id[:16], outcome,
                    )

            if total_redeemed > 0:
                # Update internal balance tracker with redeemed funds
                new_balance = self._risk_mgr._balance + total_redeemed
                self._apply_balance(new_balance)

                LOGGER.info(
                    "[AUTO_REDEEM] Total redeemed: $%.4f | New balance: $%.4f",
                    total_redeemed, new_balance,
                )

                self._notify_telegram(
                    "notify_summary",
                    (
                        f"Auto-Redeem\n"
                        f"Claimed ${total_redeemed:.4f} from {len(redeemable)} settled position(s)\n"
                        f"New Bankroll: ${new_balance:.4f}"
                    ),
                    dedup_key="auto_redeem_cycle",
                    reason="auto_redeem",
                )

        except Exception as e:
            LOGGER.warning("[AUTO_REDEEM] Cycle failed: %s", e)

        return total_redeemed

    def _check_stalled_positions(self) -> None:
        """Force-exit BUY positions that are underwater and have stalled beyond the threshold."""
        open_pos = self.tracker.open_positions()
        if not open_pos:
            return
        current_prices: dict[str, float] = {}
        for pos in open_pos:
            if pos.symbol not in current_prices:
                try:
                    ob = self.client.get_orderbook(pos.symbol)
                    if ob.best_bid > 0:
                        current_prices[pos.symbol] = ob.best_bid
                except Exception as exc:
                    LOGGER.debug("[Stall] Orderbook fetch failed for %s: %s", pos.symbol, exc)
        stalled = self.tracker.get_stalled_positions(
            stall_seconds=self.settings.stall_exit_seconds,
            current_prices=current_prices,
        )
        for pos in stalled:
            exit_price = current_prices.get(pos.symbol, pos.entry_price)
            LOGGER.warning(
                "Stall exit | id=%s symbol=%s entry=%.4f bid=%.4f",
                pos.position_id, pos.symbol, pos.entry_price, exit_price,
            )
            receipt = self._submit_order(
                market_id=self._position_token_id(pos),
                side=SELL,
                price=exit_price,
                size=pos.size,
                intent_type=OrderIntentType.EXIT,
                source_market_id=pos.symbol,
                outcome=self._position_outcome(pos),
                position_id=pos.position_id,
            )
            if receipt is not None:
                self.tracker.close_position(pos.position_id, exit_price, reason="stall_exit")
                pnl = (exit_price - pos.entry_price) * pos.size
                self._risk_mgr.record_result(won=pnl >= 0, pnl=abs(pnl))
                if self.settings.paper_trading:
                    self._paper_record_close(pnl)
                    self._paper_apply_exit_cash(exit_price * pos.size, pnl)
                    self._paper_update_drawdown()

    def _manage_open_positions_for_cycle(self) -> None:
        for pos in self.tracker.open_positions():
            ticker = pos.symbol.replace("pm-5m-", "").upper()
            metadata = getattr(pos, "metadata", None) or {}
            outcome = self._position_outcome(pos)
            try:
                ptb_state = self.ptb_tracker.get_market_ptb(ticker)
                time_remaining = self._seconds_to_close(ptb_state)
            except Exception:
                time_remaining = None

            if time_remaining is None:
                LOGGER.warning(
                    "[EXIT] market=%s action=hold seconds_to_close=-1 reason=missing_close_time",
                    pos.symbol,
                )
                continue

            if self._exit_agent_check_position(pos, time_remaining):
                continue

            current_price = self._position_mark_price(pos)
            unrealized_pct = self._unrealized_pct(pos, current_price)
            state = PositionState.OPEN_YES if outcome == "YES" else PositionState.OPEN_NO
            decision = manage_position(PositionManagerInput(
                state=state,
                current_ev=float(metadata.get("entry_ev", 0.02)),
                confidence_score=float(metadata.get("confidence", 0.70)),
                time_remaining_seconds=time_remaining,
                held_outcome=outcome,
                held_token_id=self._position_token_id(pos),
                stop_loss_hit=current_price <= float(pos.stop_loss),
                take_profit_hit=current_price >= float(pos.take_profit),
                reconciliation_safe=not (self._last_reconciliation and self._last_reconciliation.block_new_trading),
            ))
            if bool(self._setting("verbose_risk_logs", True)):
                self._log_section(
                    "POSITION",
                    (
                        f"state={decision.state.value} side={outcome} entry={float(pos.entry_price):.4f} "
                        f"current={current_price:.4f} pnl={unrealized_pct * 100:+.2f}% "
                        f"tp={float(pos.take_profit):.4f} sl={float(pos.stop_loss):.4f} "
                        f"action={decision.action.value}"
                    ),
                )
            else:
                LOGGER.info(
                    "[POSITION] state=%s side=%s entry=%.4f current_price=%.4f unrealized_pnl=%.4f action=%s",
                    decision.state.value,
                    outcome,
                    pos.entry_price,
                    current_price,
                    unrealized_pct,
                    decision.action.value,
                )
            self._paper_record_position_state(decision.state.value, decision.action.value)
            if decision.action.value == "SELL_HELD_TOKEN":
                self._close_position_with_retry(pos, reason=decision.reason, exit_price=current_price)

    def _cancel_stale_entry_orders_if_needed(self, max_age_seconds: float = 20.0) -> None:
        if self.settings.paper_trading:
            return
        try:
            open_orders = self.client.get_open_orders()
        except Exception as exc:
            LOGGER.warning("[POSITION] state=PENDING_ENTRY side=UNKNOWN entry=0 current_price=0 unrealized_pnl=0 action=cancel_scan_failed reason=%s", exc)
            return

        now = time.time()
        for order in open_orders:
            side = str(order.get("side", "")).upper()
            order_id = str(order.get("order_id") or order.get("id") or "")
            created_at = order.get("created_at") or order.get("createdAt") or order.get("timestamp") or now
            try:
                created_ts = float(created_at)
            except (TypeError, ValueError):
                created_ts = now
            if side == BUY and order_id and now - created_ts >= max_age_seconds:
                try:
                    self.client.cancel_order(order_id)
                    self._paper_record_cancel("stale_entry_order")
                    self._log_order_section(
                        order_type="CANCEL",
                        size=0.0,
                        price=0.0,
                        status="CANCELED",
                        cancel_reason="stale_entry_order",
                    )
                    LOGGER.info("[POSITION] state=PENDING_ENTRY side=BUY entry=0 current_price=0 unrealized_pnl=0 action=CANCEL_ENTRY reason=stale_entry_order order_id=%s", order_id)
                    self._emit_quant_event(
                        "log_execution",
                        {
                            "event": "cancel_order",
                            "status": "canceled",
                            "order_id": order_id,
                            "reason": "stale_entry_order",
                        },
                    )
                except Exception as exc:
                    self._paper_record_cancel("cancel_failed")
                    self._log_order_section(
                        order_type="CANCEL",
                        size=0.0,
                        price=0.0,
                        status="FAILED",
                        cancel_reason="cancel_failed",
                    )
                    LOGGER.warning("[POSITION] state=PENDING_ENTRY side=BUY entry=0 current_price=0 unrealized_pnl=0 action=cancel_failed order_id=%s reason=%s", order_id, exc)
                    self._emit_quant_event(
                        "log_execution",
                        {
                            "event": "cancel_order",
                            "status": "failed",
                            "order_id": order_id,
                            "reason": "cancel_failed",
                            "error": str(exc),
                        },
                    )

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def settle_and_record(self, symbol: str, is_above_ptb: bool) -> None:
        """Settle expired binary positions and record win/loss for loss cluster tracking."""
        open_before = {
            p.position_id: p
            for p in self.tracker.open_positions()
            if p.symbol == symbol
        }
        self.tracker.settle_expired_binaries(symbol, is_above_ptb)
        for pos in open_before.values():
            outcome = self._position_outcome(pos)
            won = (outcome == "YES" and is_above_ptb) or (outcome == "NO" and not is_above_ptb)
            pnl = pos.size * (1.0 - pos.entry_price) if won else pos.size * pos.entry_price
            signed_pnl = pnl if won else -pnl
            self._risk_mgr.record_result(won=won, pnl=pnl)
            if self.settings.paper_trading:
                self._paper_record_close(signed_pnl)
                self._paper_apply_exit_cash(pos.size if won else 0.0, signed_pnl)
                self._paper_record_position_state("OPEN", "SETTLED_WIN" if won else "SETTLED_LOSS")
                self._paper_update_drawdown()
                LOGGER.info(
                    "[PAPER EXIT] position=%s market=%s reason=settlement outcome=%s won=%s",
                    pos.position_id,
                    symbol,
                    outcome,
                    won,
                )
                LOGGER.info(
                    "[PAPER PNL] position=%s market=%s realized_pnl=%+.4f cash=$%.4f equity=$%.4f",
                    pos.position_id,
                    symbol,
                    signed_pnl,
                    self.bankroll_state.current_cash_balance,
                    self.bankroll_state.equity,
                )
            LOGGER.info(
                "[SETTLEMENT] %s %s | won=%s pnl=%.4f | is_above_ptb=%s",
                outcome, symbol, won, signed_pnl, is_above_ptb,
            )
            self._emit_trade_closed_event(
                position=pos,
                reason="settlement",
                exit_price=1.0 if won else 0.0,
                size=pos.size,
                pnl=signed_pnl,
                receipt=None,
                partial=False,
            )
            
            from utils.telegram_reporter import build_settlement_alert

            self._notify_telegram(
                "notify_exit",
                build_settlement_alert(
                    asset=symbol,
                    won=won,
                    pnl=pnl,
                    bankroll=self._risk_mgr._balance,
                    paper=self.settings.paper_trading,
                ),
                dedup_key=f"settlement:{pos.position_id}",
                market=symbol,
                reason="settlement",
            )

    def run_single_cycle(self, top_n: int = 3) -> list[TradeOutcome]:
        """Run one complete analysis-and-execution cycle.

        Returns one TradeOutcome per selected market.
        """
        self._cycle_count += 1
        self._begin_cycle_timing()
        if self._paper_enabled():
            self.paper_stats.cycles_scanned += 1
        # â”€â”€ Auto-Redeem: claim any settled winnings before trading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.auto_redeem_cycle()

        self._ensure_connected()
        report = self.reconcile_live_positions()
        self._update_bankroll_state(fetch_live_cash=not self.settings.paper_trading)
        self._maybe_emit_risk_state_event(reason="cycle_start")
        self._maybe_emit_system_health(reason="cycle_start")
        if self._block_on_reconciliation_if_needed(report):
            self._maybe_emit_system_health(force=True, reason="reconciliation_block")
            self._maybe_log_cycle_summary()
            self._finish_cycle_timing(reason="cycle_end_reconciliation_block", force=True)
            return []
        self._cancel_stale_entry_orders_if_needed()
        self._check_stalled_positions()
        self._manage_open_positions_for_cycle()
        self._update_bankroll_state(fetch_live_cash=not self.settings.paper_trading)

        # v3.1/3.2: Balance guard â€” auto pause and resume
        if self._paused_insufficient_funds:
            if self.settings.paper_trading:
                self._paused_insufficient_funds = False
                LOGGER.info("[PAPER_MODE] Cleared live balance pause flag in paper mode.")
            else:
                # Check if funds have been deposited/claimed to auto-resume
                try:
                    live_balance = self.client.get_usdc_balance()
                    if live_balance >= self.settings.bankroll_floor:
                        self._paused_insufficient_funds = False
                        LOGGER.info("[AUTO_RESUME] Balance recovered to $%.2f. Resuming trading.", live_balance)
                    else:
                        LOGGER.warning("[CYCLE SKIP] BALANCE_GUARD: insufficient funds ($%.2f) -- waiting for deposit/claim", live_balance)
                        self._maybe_log_cycle_summary()
                        self._finish_cycle_timing(reason="cycle_end_balance_guard", force=True)
                        return []
                except Exception:
                    LOGGER.warning("[CYCLE SKIP] BALANCE_GUARD: insufficient funds -- waiting for deposit/claim")
                    self._maybe_log_cycle_summary()
                    self._finish_cycle_timing(reason="cycle_end_balance_guard", force=True)
                    return []
        if self._paused_insufficient_funds and not self.settings.paper_trading:
            # Check if funds have been deposited/claimed to auto-resume
            try:
                live_balance = self.client.get_usdc_balance()
                if live_balance >= self.settings.bankroll_floor:
                    self._paused_insufficient_funds = False
                    LOGGER.info("[AUTO_RESUME] Balance recovered to $%.2f. Resuming trading.", live_balance)
                else:
                    LOGGER.warning("[CYCLE SKIP] BALANCE_GUARD: insufficient funds ($%.2f) â€” waiting for deposit/claim", live_balance)
                    self._maybe_log_cycle_summary()
                    self._finish_cycle_timing(reason="cycle_end_balance_guard", force=True)
                    return []
            except Exception:
                LOGGER.warning("[CYCLE SKIP] BALANCE_GUARD: insufficient funds â€” waiting for deposit/claim")
                self._maybe_log_cycle_summary()
                self._finish_cycle_timing(reason="cycle_end_balance_guard", force=True)
                return []

        ok, pause_reason = self._risk_mgr.can_trade()
        if not ok:
            LOGGER.warning("[CYCLE SKIP] %s", pause_reason)
            self._emit_risk_event(
                "cycle_risk_pause",
                {
                    "reason": pause_reason,
                    "balance": float(getattr(self._risk_mgr, "_balance", 0.0) or 0.0),
                },
            )
            from utils.telegram_reporter import (
                build_loss_cluster_alert, build_daily_drawdown_alert,
            )
            from utils.risk_manager import LOSS_CLUSTER_PAUSE_SECONDS, HARD_DAILY_DRAWDOWN

            balance = self._risk_mgr._balance
            if "LOSS CLUSTER" in pause_reason or "consecutive" in pause_reason.lower():
                self._notify_telegram(
                    "notify_risk",
                    build_loss_cluster_alert(
                        streak=3,
                        pause_minutes=LOSS_CLUSTER_PAUSE_SECONDS // 60,
                        bankroll=balance,
                    ),
                    dedup_key="loss_cluster",
                    reason="loss_cluster",
                )
            elif "DRAWDOWN" in pause_reason:
                import re as _re
                m = _re.search(r"([\d.]+)%", pause_reason)
                dd = float(m.group(1)) if m else HARD_DAILY_DRAWDOWN * 100
                self._notify_telegram(
                    "notify_risk",
                    build_daily_drawdown_alert(
                        dd_pct=dd,
                        limit_pct=HARD_DAILY_DRAWDOWN * 100,
                        bankroll=balance,
                    ),
                    dedup_key="daily_drawdown",
                    reason="daily_drawdown",
            )
            self._maybe_emit_system_health(force=True, reason="cycle_risk_pause")
            self._maybe_log_cycle_summary()
            self._finish_cycle_timing(reason="cycle_end_risk_pause", force=True)
            return []

        markets = self._select_markets(top_n=top_n)

        if not markets:
            self._maybe_log_cycle_summary()
            LOGGER.warning("No markets available â€” cycle skipped.")
            self._maybe_emit_system_health(force=True, reason="no_markets")
            self._finish_cycle_timing(reason="cycle_end_no_markets", force=True)
            return []

        outcomes: list[TradeOutcome] = []
        for market in markets:
            try:
                outcome = self._analyze_market(market)
                outcomes.append(outcome)
                if outcome.skipped:
                    LOGGER.info(
                        "Market skipped | id=%s reason=%s",
                        market.market_id,
                        outcome.skip_reason,
                    )
                else:
                    LOGGER.info(
                        "Trade outcome | id=%s decision=%s confidence=%.2f order=%s",
                        market.market_id,
                        outcome.decision,
                        outcome.confidence,
                        outcome.receipt.order_id if outcome.receipt else "none",
                    )
            except Exception:
                LOGGER.exception("Unexpected error analyzing market_id=%s", market.market_id)
                self._emit_quant_event(
                    "log_execution",
                    {
                        "event": "market_analysis_exception",
                        "market_id": market.market_id,
                        "mode": self._runtime_mode(),
                    },
                )

        self.update_dashboard_status(0)
        self._finish_cycle_timing(reason="cycle_end")
        self._maybe_log_cycle_summary()
        return outcomes

    def update_dashboard_status(self, countdown: int) -> None:
        """Write current bot state to runtime/bot_status.json for the API to consume."""
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "account_balance": float(self.settings.account_balance),
                "balance_source": self._balance_source,
                "paper_balance_source": self._paper_balance_source_setting(),
                "execution_mode": "PAPER ONLY" if self.settings.paper_trading else "LIVE",
                "wallet_reference_balance": self._wallet_reference_balance,
                "wallet_reference_error": self._wallet_reference_error,
                "open_positions": [asdict(p) for p in self.tracker.open_positions()],
                "is_paper_trading": self.settings.paper_trading,
                "current_countdown": countdown,
                "last_signals": {k: asdict(v) for k, v in self.last_signals.items()},
                "last_update": datetime.now().strftime("%H:%M:%S")
            }
            status_path = Path("runtime/bot_status.json")
            with open(status_path, "w") as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            LOGGER.debug("[DASHBOARD] Failed to update status: %s", e)
