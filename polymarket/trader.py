from __future__ import annotations

import logging
import time
import json
import hashlib
from collections import Counter, deque
from dataclasses import dataclass, asdict, field
from datetime import UTC, datetime
from pathlib import Path

from config.settings import Settings, get_settings
from polymarket.arbitrage import ArbitrageOpportunity, ArbitrageScanner
from polymarket.arbitrage_executor import ArbitrageExecutor
from polymarket.client import BUY, SELL, BalanceSnapshot, ClobOrderbookError, OrderReceipt, PolymarketClient
from polymarket.delta_engine import DeltaRegime, MicroDeltaInput, estimate_micro_delta
from polymarket.expected_value import ExpectedValueTier
from polymarket.gamma_fetcher import GammaFetcher, GammaMarket, ActiveFiveMinMarket
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
from polymarket.regime_diagnostics import classify_market_regime, classify_market_regime_from_payload
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
from utils.risk_manager import (
    FLOOR_BALANCE,
    MICRO_SURVIVAL_MODE,
    RiskManager,
    RiskPlan,
    bankroll_mode_for,
    build_micro_survival_risk_plan,
)
from utils.quant_event_logger import QuantEventLogger
from utils.telegram_alerts import TelegramAlertLayer, emit_startup_config_telemetry
from utils.no_entry_diagnostics import classify_time_bucket, normalize_skip_reason
import polymarket.shadow_telemetry as shadow_telemetry


LOGGER = logging.getLogger(__name__)


CLOB_ORDERBOOK_ERROR_CATEGORIES = {
    "clob_http_error",
    "clob_timeout",
    "clob_rate_limited",
    "clob_parse_error",
    "clob_empty_response",
    "clob_token_not_found",
    "clob_client_not_connected",
    "clob_auth_or_client_issue",
}
REGIME_PAYLOAD_FIELD_NAMES = (
    "market_regime",
    "volatility_regime",
    "volatility_score",
    "trend_regime",
    "trend_strength",
    "bullish_probability",
    "bearish_probability",
    "reversal_risk",
    "compression_score",
    "signal_trend_strength",
    "signal_volatility_score",
    "indicator_evidence",
    "regime_reason",
)
EMPTY_BOOK_RECOVERY_RESEARCH_FIELD_NAMES = (
    "empty_book_recovery_research_mode",
    "liquidity_recovery_grace_entered",
    "liquidity_recovery_grace_success",
    "liquidity_recovery_grace_failed",
    "recovery_wait_seconds",
    "recovered_before_cutoff",
    "candidate_survived_recovery",
    "recovery_exit_reason",
    "recovery_branch_candidate_seen",
    "recovery_branch_preempted_by_cutoff",
    "recovery_branch_skipped_reason",
    "recovery_branch_mode_disabled",
    "recovery_branch_enter_condition_failed",
)


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
    orderbook_readiness_reason: str = ""
    orderbook_unavailable_reason: str = ""
    orderbook_error: str = ""
    clob_error_category: str = ""
    clob_error_class: str = ""
    clob_exception_type: str = ""
    clob_status_code: int | None = None
    clob_parse_failure: bool = False
    clob_api_failure: bool = False
    clob_error_rate: float = 0.0
    clob_backoff_active: bool = False
    clob_circuit_open: bool = False
    clob_cooldown_seconds_remaining: float = 0.0
    clob_recovery_count: int = 0
    market_data_degraded: bool = False
    retry_count: int = 0
    empty_book_recovery_attempted: bool = False
    empty_book_recovery_success: bool = False
    empty_book_recovery_failed: bool = False
    empty_book_recovery_retry_count: int = 0
    liquidity_state: str = "HEALTHY"


@dataclass(slots=True)
class AdaptiveEntryCutoffDecision:
    allowed: bool
    policy: str
    effective_cutoff_seconds: int
    reason: str
    late_entry_hard_block: bool = False
    micro_timing_allowed: bool = False
    micro_timing_denied_reason: str = ""
    effective_micro_cutoff_seconds: int = 0
    micro_cutoff_policy: str = "standard"
    micro_timing_branch_entered: bool = False
    micro_timing_branch_skipped_reason: str = ""
    micro_timing_candidate: bool = False


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
    funnel_candidates: int = 0
    funnel_orderbook_ready: int = 0
    funnel_confidence_pass: int = 0
    funnel_ev_pass: int = 0
    funnel_delta_pass: int = 0
    funnel_risk_size_pass: int = 0
    funnel_trade_open: int = 0

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
    bankroll_tier_id: str = ""
    bankroll_tier_name: str = ""
    bankroll_family: str = ""
    bankroll_risk_profile: str = ""
    bankroll_tier_locked: bool = False
    bankroll_hysteresis_active: bool = False

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
        if not self.bankroll_tier_id:
            config = get_tier_config(self.current_bankroll_tier)
            self.bankroll_tier_id = config.tier_id
            self.bankroll_tier_name = config.tier_name
            self.bankroll_family = config.family
            self.bankroll_risk_profile = config.risk_profile


def evaluate_delta_extreme_shadow_candidate(
    *,
    price: float,
    spread: float,
    quote_age_ms: int,
    oracle_age_ms: int,
    ask_size: float,
    seconds_remaining: float,
) -> dict[str, object]:
    """Pure helper evaluating shadow executability gates and sizing tracks.
    Returns a dictionary of overlay parameters and gate flags.
    """
    import math

    price_ok = (price > 0.0 and price < 1.0)
    spread_ok = (spread <= 0.06)
    quote_fresh = (quote_age_ms <= 1000)
    oracle_fresh = (oracle_age_ms <= 5000)

    # Standard: max($1.00 entry cost, 5 shares)
    std_shares = max(5.0, math.ceil(1.00 / max(price, 1e-9)))
    # Micro: max($0.05 entry cost, 5 shares)
    micro_shares = max(5.0, math.ceil(0.05 / max(price, 1e-9)))

    depth_ok = (ask_size >= std_shares)
    cutoff_ok = (seconds_remaining > 90)
    sizer_feasible = price_ok and (price * std_shares <= 1000.0)

    executable_pass = bool(
        price_ok
        and spread_ok
        and quote_fresh
        and oracle_fresh
        and depth_ok
        and cutoff_ok
        and sizer_feasible
    )

    reject_reason = None
    if not executable_pass:
        if not price_ok:
            reject_reason = "price_unavailable"
        elif not spread_ok:
            reject_reason = "spread_too_wide"
        elif not quote_fresh:
            reject_reason = "quote_stale"
        elif not oracle_fresh:
            reject_reason = "oracle_stale"
        elif not cutoff_ok:
            reject_reason = "time_unsafe"
        elif not depth_ok:
            reject_reason = "liquidity_too_small"
        else:
            reject_reason = "sizer_infeasible"

    return {
        "executable_pass": executable_pass,
        "executable_reject_reason": reject_reason,
        "standard_shares": float(std_shares) if executable_pass else 0.0,
        "standard_size_usd": float(std_shares * price) if executable_pass else 0.0,
        "micro_shares": float(micro_shares) if executable_pass else 0.0,
        "micro_size_usd": float(micro_shares * price) if executable_pass else 0.0,
    }


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
        # v3.1: Panic sell cooldown (epoch_ts → skip next round)
        self._panic_sold_epochs: dict[str, int] = {}
        # v3.1: Partial TP tracking (position_id → already took partial)
        self._partial_tp_taken: set[str] = set()
        # v3.5: Stop-loss shadow confirmation counters (position_id → ticks)
        self._consecutive_raw_breach_seconds: dict[str, int] = {}
        self._consecutive_mid_breach_seconds: dict[str, int] = {}
        # PATCH_STOP_002 / PAPER_STOP_FAILSAFE: consecutive OB unavailable streak (position_id → ticks)
        self._consecutive_ob_unavailable_seconds: dict[str, int] = {}
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
        self._last_risk_mode_decision = None
        self._last_funnel_stage = "candidates"
        self.runtime_owner = None
        initial_bankroll = float(self.settings.account_balance)
        self.bankroll_state = BankrollState(
            starting_bankroll=initial_bankroll,
            current_cash_balance=initial_bankroll,
        )
        self._bankroll_rank_lock = BankrollRankLock(
            initial_tier=initial_bankroll,
            buffer_pct=float(
                getattr(
                    self.settings,
                    "bankroll_tier_hysteresis_pct",
                    getattr(self.settings, "bankroll_rank_hysteresis_pct", 0.05),
                )
                or 0.05
            ),
        )
        self._last_bankroll_rank_lock_log = ""
        self.last_quant_details: dict[str, dict[str, object]] = {}
        self._last_orderbook_age_ms: dict[str, int] = {}
        self._last_orderbook_refresh_at_utc: dict[str, str] = {}
        self._last_orderbook_refresh_monotonic: dict[str, float] = {}
        self._last_orderbook_refresh_source: dict[str, str] = {}
        self._last_orderbook_refresh_trigger: dict[str, str] = {}
        self._last_orderbook_refresh_token_pair_key: dict[str, str] = {}
        self._last_successful_yes_no_book_at_utc: dict[str, str] = {}
        self._last_successful_yes_no_book_monotonic: dict[str, float] = {}
        self._last_successful_yes_no_book_token_pair_key: dict[str, str] = {}
        self._last_quote_lineage_context: dict[str, dict] = {}
        self._last_decision_cycle_monotonic: dict[str, float] = {}
        self._market_evaluation_started_monotonic: dict[str, float] = {}
        self._market_evaluation_started_at_utc: dict[str, str] = {}
        self._current_cycle_market_sequence_index: dict[str, int] = {}
        self._current_cycle_market_sequence_count: dict[str, int] = {}
        self._orderbook_warmup_pending_counts: Counter[str] = Counter()
        self._preloaded_token_ids: dict[tuple[str, int], tuple[str, str]] = {}
        self._preloaded_token_meta: dict[tuple[str, int], dict[str, object]] = {}
        self._warmed_orderbook_epochs: set[tuple[str, int]] = set()

        # Preload Next Market v1
        self._preloaded_next_markets: dict[str, ActiveFiveMinMarket] = {}
        self._preload_attempted: bool = False
        self._preload_success: bool = False
        self._preload_started_ts: int = 0
        self._preload_success_ts: int = 0
        self._preload_failed_reason: str | None = None
        self._preload_ticker: str = ""
        self._preload_market_slug: str = ""
        self._preload_condition_id: str = ""
        self._preload_yes_token_id_present: bool = False
        self._preload_no_token_id_present: bool = False
        self._preload_orderbook_warmed: bool = False
        self._preload_orderbook_state: str = "UNKNOWN"
        self._preload_seconds_before_epoch: int = 0
        self._preload_latency_ms: int = 0
        self._preload_cache_hit: bool = False
        self._preload_cache_age_seconds: int = 0
        self._preload_next_epoch_start: int = 0
        self._preload_next_epoch_remaining_seconds: int = 0
        self._preload_lead_seconds: int = 0
        self._preload_book_ready_ts: int = 0
        self._market_first_seen_seconds_remaining: dict[tuple[str, int], int] = {}
        self._market_first_evaluable_seconds_remaining: dict[tuple[str, int], int] = {}
        self._market_readiness_timestamps: dict[tuple[str, int], dict[str, object]] = {}
        self._last_empty_book_recovery_detail: dict[str, dict[str, object]] = {}
        self._market_readiness_metrics = {
            "token_preload_hits": 0,
            "token_preload_misses": 0,
            "token_preload_warmups": 0,
            "token_preload_failures": 0,
            "empty_book_recovery_attempted": 0,
            "empty_book_recovery_success": 0,
            "empty_book_recovery_failed": 0,
            "empty_book_recovery_retries": 0,
        }
        self._recent_display_trades: deque[dict[str, object]] = deque(maxlen=12)
        self._cycle_count = 0
        self._session_start_monotonic: float = time.monotonic()
        self._loop_exception_count: int = 0
        self._cockpit_probe_counts: dict[str, int] = {"zero_size": 0, "cycle_selection": 0}
        self._cycle_started_monotonic = 0.0
        self._cycle_started_at_utc = ""
        self._current_cycle_market_count = 0
        self._previous_cycle_started_monotonic = 0.0
        self._effective_outer_loop_interval_seconds: float | None = None
        self._configured_decision_loop_interval_seconds: float | None = None
        self._intended_decision_loop_target_seconds = 1.0
        self._snapshot_sampling_interval_seconds = 5.0
        self._market_discovery_interval_seconds = 15.0
        self._outer_loop_poll_interval_seconds = 0.25
        self._last_scan_cycle_duration_ms = 0
        self._last_structured_logs: dict[str, str] = {}
        self._observability_health_display_state: dict[str, object] = self._default_observability_health_display_state()
        self.quant_events = self._init_quant_event_logger()
        self.telegram_alerts = self._init_telegram_alert_layer()
        self._last_system_health_event_ts = 0.0
        self._last_risk_state_event_ts = 0.0
        self._shutdown_complete = False
        self._path_truth_checkpoint_schedule_s = (15, 30, 45, 60)
        self._path_truth_checkpoint_tolerance_s = {15: 2, 30: 2, 45: 3, 60: 3}
        self._path_truth_max_writes_per_trade = 5
        self._path_truth_emitted_checkpoints_by_trade: dict[str, set[str]] = {}

        # PATCH_SIGNAL_001 Shadow Mode Counters
        self._baseline_accepted = 0
        self._shadow_would_reject = 0
        self._ev_cap_shadow_rejects = 0
        self._yes_floor_shadow_rejects = 0

    def _call_shutdown_hook(self, hook, *, join_timeout: float | None = None) -> None:
        if not callable(hook):
            return
        if join_timeout is None:
            hook()
            return
        try:
            hook(join_timeout=join_timeout)
        except TypeError:
            hook()

    def close(self, *, join_timeout: float | None = None) -> None:
        """Release trader-owned background resources without changing trading state."""
        if self._shutdown_complete:
            return
        self._shutdown_complete = True
        try:
            self._emit_path_truth_shutdown_events()
        except Exception:
            pass
        try:
            close_ptb = getattr(self.ptb_tracker, "close", None)
            self._call_shutdown_hook(close_ptb, join_timeout=join_timeout)
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
                self._call_shutdown_hook(stop_feed, join_timeout=join_timeout)
            except Exception as exc:
                LOGGER.debug("[SHUTDOWN] %s close failed: %s", module_name, exc)
        try:
            self._maybe_emit_system_health(force=True, reason="shutdown")
        except Exception:
            pass

    def shutdown(self, *, join_timeout: float | None = None) -> None:
        self.close(join_timeout=join_timeout)

    def stop(self, *, join_timeout: float | None = None) -> None:
        self.close(join_timeout=join_timeout)

    def _runtime_mode(self) -> str:
        return "paper" if self.settings.paper_trading else "live"

    def _micro_survival_threshold(self) -> float:
        return max(float(getattr(self.settings, "micro_survival_bankroll_threshold", 100.0) or 100.0), 0.0)

    def _micro_survival_min_position_size(self) -> float:
        return max(float(getattr(self.settings, "micro_survival_min_position_size", 0.05) or 0.05), 0.0)

    def _micro_survival_risk_fraction(self) -> float:
        return max(float(getattr(self.settings, "micro_survival_risk_fraction", 0.0025) or 0.0025), 0.0)

    def _bankroll_mode(self, bankroll: float | None = None) -> str:
        balance = self.bankroll_state.current_bankroll_for_sizing if bankroll is None else float(bankroll)
        return bankroll_mode_for(
            account_balance=balance,
            threshold=self._micro_survival_threshold(),
            paper_trading=bool(self.settings.paper_trading),
        )

    def _micro_survival_active(self, bankroll: float | None = None) -> bool:
        return self._bankroll_mode(bankroll) == MICRO_SURVIVAL_MODE

    def _micro_position_size(self, bankroll: float | None = None) -> float:
        balance = self.bankroll_state.current_bankroll_for_sizing if bankroll is None else float(bankroll)
        if not self._micro_survival_active(balance):
            return 0.0
        effective_fraction = min(
            self._micro_survival_risk_fraction(),
            float(getattr(self.settings, "max_risk_per_trade", 0.0) or 0.0),
            float(getattr(self.settings, "max_single_trade_risk", 0.03) or 0.03),
        )
        risk_cap = max(balance * max(effective_fraction, 0.0), 0.0)
        return round(min(max(self._micro_survival_min_position_size(), risk_cap), risk_cap, balance), 6)

    def _bankroll_mode_detail(self, bankroll: float | None = None) -> dict[str, object]:
        balance = self.bankroll_state.current_bankroll_for_sizing if bankroll is None else float(bankroll)
        mode = self._bankroll_mode(balance)
        active = mode == MICRO_SURVIVAL_MODE
        return {
            "bankroll_mode": mode,
            "micro_survival_active": active,
            "micro_position_size": self._micro_position_size(balance) if active else 0.0,
        }

    def _bankroll_tier_detail(self, tier_value: str | None = None) -> dict[str, object]:
        config = get_tier_config(tier_value or self.bankroll_state.current_bankroll_tier)
        return {
            "bankroll_tier_id": config.tier_id,
            "bankroll_tier_name": config.tier_name,
            "bankroll_family": config.family,
            "bankroll_risk_profile": config.risk_profile,
            "bankroll_tier_locked": bool(self.bankroll_state.bankroll_tier_locked),
            "bankroll_hysteresis_active": bool(self.bankroll_state.bankroll_hysteresis_active),
        }

    def _entry_min_position_size_usd(self, *, bankroll: float, entry_price: float) -> float:
        if self._micro_survival_active(bankroll):
            return self._micro_survival_min_position_size()
        return max(float(self.settings.min_shares_per_order) * entry_price, 1.0)

    def _micro_survival_allows_fractional_shares(self, *, bankroll: float) -> bool:
        return bool(self.settings.paper_trading) and self._micro_survival_active(bankroll)

    def _maybe_apply_micro_survival_plan(
        self,
        risk_plan: RiskPlan,
        *,
        current_balance: float,
        entry_price: float,
    ) -> RiskPlan:
        if not self._micro_survival_active(current_balance):
            return risk_plan
        if float(getattr(risk_plan, "position_size", 0.0) or 0.0) > 0.0:
            return risk_plan

        diagnostics = getattr(risk_plan, "diagnostics", {}) if risk_plan is not None else {}
        diagnostics = diagnostics if isinstance(diagnostics, dict) else {}
        blocked = {str(reason) for reason in diagnostics.get("blocked_reasons", []) or []}
        if blocked != {"below_min_position_size"}:
            return risk_plan

        merged_diagnostics = dict(diagnostics)
        merged_diagnostics["rescued_from_risk_plan_zero"] = True
        merged_diagnostics["original_position_size"] = float(getattr(risk_plan, "position_size", 0.0) or 0.0)
        merged_diagnostics["original_notional_size"] = float(getattr(risk_plan, "notional_size", 0.0) or 0.0)
        return build_micro_survival_risk_plan(
            account_balance=current_balance,
            entry_price=entry_price,
            stop_loss_pct=float(self._setting("execution_stop_loss_pct", self.settings.default_stop_loss_pct)),
            risk_fraction=self._micro_survival_risk_fraction(),
            min_position_size_usd=self._micro_survival_min_position_size(),
            max_risk_per_trade=float(getattr(self.settings, "max_risk_per_trade", 0.0) or 0.0),
            take_profit_pct=float(self._setting("execution_take_profit_pct", 0.10)),
            diagnostics=merged_diagnostics,
        )

    def _init_quant_event_logger(self) -> QuantEventLogger | None:
        try:
            return QuantEventLogger(mode=self._runtime_mode(), source_module="polymarket.trader")
        except Exception as exc:
            LOGGER.warning("[OBSERVABILITY] QuantEventLogger disabled at startup: %s", exc)
            return None

    def _init_telegram_alert_layer(self) -> TelegramAlertLayer | None:
        try:
            run_id = str(getattr(self.quant_events, "run_id", "") or "") or None
            layer = TelegramAlertLayer(
                telemetry_emit=self._emit_telegram_route_telemetry,
                run_id=run_id,
            )
            emit_startup_config_telemetry(
                self.settings,
                telemetry_emit=self._emit_telegram_route_telemetry,
                run_id=run_id,
            )
            return layer
        except Exception as exc:
            LOGGER.warning("[OBSERVABILITY] Telegram alert layer disabled at startup: %s", exc)
            return None

    def _default_observability_health_display_state(self) -> dict[str, object]:
        return {
            "jsonl_status": "UNKNOWN",
            "jsonl_ok": False,
            "latest_producer": "--",
            "latest_schema_version": "--",
            "trace_enrichment_status": "UNKNOWN",
            "condition_enrichment_status": "UNKNOWN",
            "trace_id_enrichment_ok": False,
            "condition_id_enrichment_ok": False,
            "candidate_trace_id_present": False,
            "condition_id_present": False,
            "token_id_present": False,
            "side_present": False,
            "event_identity_readiness": "UNKNOWN",
            "candidate_chain_trace_confidence": "UNKNOWN",
            "identity_readiness": "UNKNOWN",
            "model_attempted": "UNKNOWN",
            "probability_visible": "UNKNOWN",
            "fair_value_visible": "UNKNOWN",
            "ev_visible": "UNKNOWN",
            "dominant_model_gap": "UNKNOWN",
            "dominant_model_gap_reason": "UNKNOWN",
            "blocked_before_risk_count": 0,
            "dominant_pre_risk_cause": "UNKNOWN",
            "dominant_pre_risk_block_reason": "UNKNOWN",
            "risk_reachability_status": "UNKNOWN",
            "risk_serialization_status": "UNKNOWN",
            "risk_serialization_visibility": "UNKNOWN",
        }

    def dashboard_observability_health_state(self) -> dict[str, object]:
        """Return display-only observability health state for terminal UI surfaces."""
        return dict(getattr(self, "_observability_health_display_state", self._default_observability_health_display_state()))

    def _event_producer_label(self, event_method: str) -> str:
        return {
            "log_market_snapshot": "market_snapshots",
            "log_decision": "decision_log",
            "log_execution": "execution_log",
            "log_risk_event": "risk_log",
            "log_trade_open": "trade_journal",
            "log_trade_close": "trade_journal",
            "log_trade_path_checkpoint": "path_truth",
            "log_orderbook_lineage_probe": "orderbook_lineage",
            "log_system_health": "system_health",
        }.get(event_method, "unknown")

    def _display_field_present(self, payload: dict[str, object], *fields: str) -> bool:
        for field in fields:
            value = payload.get(field)
            if value is not None and str(value).strip() not in {"", "--", "None", "UNKNOWN"}:
                return True
        return False

    def _display_visibility_status(self, payload: dict[str, object], *fields: str) -> str:
        for field in fields:
            if field not in payload:
                continue
            value = payload.get(field)
            if isinstance(value, bool):
                return "YES" if value else "NO"
            if isinstance(value, (int, float)):
                return "YES" if float(value) != 0.0 else "NO"
            return "YES" if self._display_field_present(payload, field) else "NO"
        return "UNKNOWN"

    def _display_identity_readiness(self, payload: dict[str, object]) -> str:
        explicit = str(payload.get("identity_readiness") or payload.get("candidate_trace_confidence") or "").upper()
        if explicit in {"DIRECT", "STRONG", "WEAK", "PROXY", "UNKNOWN"}:
            return explicit
        has_trace = self._display_field_present(payload, "candidate_trace_id")
        has_parent = self._display_field_present(payload, "parent_candidate_trace_id")
        has_market = self._display_field_present(payload, "market_key", "market_slug", "condition_id", "market_id", "source_market_id")
        has_token = self._display_field_present(payload, "token_id")
        has_side = self._display_field_present(payload, "side", "outcome", "best_side")
        has_phase = self._display_field_present(payload, "lifecycle_phase")
        if has_trace and has_parent and has_market and has_token and has_side and has_phase:
            return "DIRECT"
        if has_market and has_token and has_side and has_phase:
            return "STRONG"
        if sum((has_market, has_token, has_side, has_phase)) >= 3:
            return "WEAK"
        if any((has_trace, has_market, has_token, has_side, has_phase)):
            return "PROXY"
        return "UNKNOWN"

    def _display_dominant_model_gap(self, payload: dict[str, object]) -> str:
        for field in (
            "dominant_model_gap",
            "dominant_model_gap_reason",
            "dominant_model_state_gap",
            "model_state_gap",
            "ev_after_spread_null_reason",
            "true_probability_null_reason",
            "fair_value_null_reason",
            "market_price_null_reason",
        ):
            value = str(payload.get(field) or "").strip()
            if value and value not in {"--", "UNKNOWN"}:
                return value
        if self._display_visibility_status(payload, "ev_after_spread", "ev") == "YES":
            return "--"
        return "UNKNOWN"

    def _observability_health_from_payload(
        self,
        event_method: str,
        payload: dict[str, object],
        *,
        jsonl_ok: bool,
    ) -> dict[str, object]:
        schema_version = str(getattr(getattr(self, "quant_events", None), "schema_version", "") or "--")
        producer = self._event_producer_label(event_method)
        has_trace = self._display_field_present(payload, "candidate_trace_id")
        has_condition = self._display_field_present(payload, "condition_id")
        has_token = self._display_field_present(payload, "token_id")
        has_side = self._display_field_present(payload, "side", "outcome", "best_side")
        has_probability = self._display_visibility_status(payload, "true_probability", "p_yes", "model_p_yes")
        has_fair_value = self._display_visibility_status(payload, "fair_value")
        has_ev = self._display_visibility_status(payload, "ev_after_spread", "ev")
        model_attempted = self._display_visibility_status(
            payload,
            "model_attempted",
            "ev_visibility_attempted",
            "probability_model_stage",
            "ev_calculation_stage",
        )
        trace_status = (
            "TRACE+COND"
            if has_trace and has_condition
            else "TRACE_ONLY"
            if has_trace
            else "COND_ONLY"
            if has_condition
            else "UNKNOWN"
        )
        boundary = str(payload.get("decision_to_risk_boundary") or "").upper()
        blocked_before_risk = int(
            bool(payload.get("candidate_blocked_before_risk_visibility"))
            or boundary == "BLOCKED_BEFORE_RISK"
        )
        risk_reachability = str(payload.get("risk_reachability_status") or boundary or "UNKNOWN")
        risk_serialization = str(
            payload.get("risk_serialization_status")
            or payload.get("risk_serialization_visibility")
            or "UNKNOWN"
        )
        pre_risk_cause = str(
            payload.get("dominant_pre_risk_cause")
            or payload.get("dominant_pre_risk_block_reason")
            or payload.get("pre_risk_block_reason")
            or payload.get("normalized_skip_reason")
            or payload.get("skip_reason")
            or "UNKNOWN"
        )
        model_gap = self._display_dominant_model_gap(payload)
        event_identity = self._display_identity_readiness(payload)
        chain_confidence = str(
            payload.get("candidate_chain_trace_confidence")
            or payload.get("candidate_trace_confidence")
            or "UNKNOWN"
        ).upper()
        if chain_confidence not in {"DIRECT", "STRONG", "WEAK", "PROXY", "UNKNOWN"}:
            chain_confidence = "UNKNOWN"
        return {
            "jsonl_status": "OK" if jsonl_ok else "WARN",
            "jsonl_ok": bool(jsonl_ok),
            "latest_producer": producer,
            "latest_schema_version": schema_version,
            "trace_enrichment_status": trace_status,
            "condition_enrichment_status": "OK" if has_condition else "UNKNOWN",
            "trace_id_enrichment_ok": has_trace,
            "condition_id_enrichment_ok": has_condition,
            "candidate_trace_id_present": has_trace,
            "condition_id_present": has_condition,
            "token_id_present": has_token,
            "side_present": has_side,
            "event_identity_readiness": event_identity,
            "candidate_chain_trace_confidence": chain_confidence,
            "identity_readiness": event_identity,
            "model_attempted": model_attempted,
            "probability_visible": has_probability,
            "fair_value_visible": has_fair_value,
            "ev_visible": has_ev,
            "dominant_model_gap": model_gap,
            "dominant_model_gap_reason": model_gap,
            "blocked_before_risk_count": blocked_before_risk,
            "dominant_pre_risk_cause": pre_risk_cause,
            "dominant_pre_risk_block_reason": pre_risk_cause,
            "risk_reachability_status": risk_reachability,
            "risk_serialization_status": risk_serialization,
            "risk_serialization_visibility": risk_serialization,
        }

    def _evaluate_passive_shadow_telemetry(
        self,
        *,
        ticker: str,
        candidate: Any,
        probability: Any,
        model_side: str,
        model_ev: float,
        regime_detail: dict[str, Any],
        ptb_info: Any,
        meta: dict[str, Any],
        yes_token_id: str,
        no_token_id: str,
        ob_spread: float,
        ob_liquidity_usd: float,
        trades_last_hour: int,
        daily_drawdown_pct: float,
        risk_off: bool,
    ) -> None:
        try:
            if not self.quant_events or not getattr(self.quant_events, "enabled", True):
                return

            run_id = self.quant_events.run_id
            signal_id = getattr(candidate, "candidate_trace_id", "")
            candidate_instance_id = getattr(candidate, "candidate_id", "")

            selected_token_id = yes_token_id if model_side == "YES" else no_token_id
            paper_trade_replay_key = f"{meta.get('condition_id', '')}|{getattr(ptb_info, 'epoch_start_ts', 0)}|{ticker}|{model_side}|{selected_token_id}"

            # Reconstruct record for the filters
            volatility_regime = regime_detail.get("volatility_regime")
            record = {
                "asset": ticker,
                "edge": model_ev,
                "volatility_regime": volatility_regime,
            }

            # Passively calculate proposed size in USD
            proposed_size_usd = 0.0
            try:
                current_balance = float(self.bankroll_state.current_cash_balance)
                entry_price = float(candidate.yes_ask if model_side == "YES" else candidate.no_ask)
                min_position_size_usd = self._entry_min_position_size_usd(
                    bankroll=current_balance,
                    entry_price=entry_price,
                )
                order_request = OrderRequest(
                    market_id=getattr(candidate, "market_id", ""),
                    side=model_side,
                    entry_price=entry_price,
                    win_rate=probability.p_yes if model_side == "YES" else probability.p_no,
                    reward_risk_ratio=2.0,
                    edge=model_ev,
                    price_to_beat=ptb_info.price_to_beat,
                    spread=ob_spread,
                    liquidity_usd=ob_liquidity_usd,
                    delta=getattr(candidate, "delta_score", 0.0),
                    delta_multiplier=getattr(candidate, "delta_multiplier", 1.0),
                    time_remaining_seconds=ptb_info.seconds_remaining,
                    trades_last_hour=trades_last_hour,
                    drawdown_pct=daily_drawdown_pct,
                    min_position_size_usd=min_position_size_usd,
                    daily_loss_limit_reached=risk_off,
                    hard_drawdown_reached=daily_drawdown_pct >= 0.15
                )
                self.order_manager.account_balance = current_balance
                risk_plan = self.order_manager.build_order_plan(order_request)
                risk_plan = self._maybe_apply_micro_survival_plan(
                    risk_plan,
                    current_balance=current_balance,
                    entry_price=entry_price,
                )
                proposed_size_usd = float(risk_plan.notional_size)
            except Exception:
                proposed_size_usd = 0.0

            active_filters = getattr(self.settings, "shadow_filters_active", [])
            for filter_name in active_filters:
                try:
                    eval_result = shadow_telemetry.evaluate_shadow_filter(record, filter_name)

                    payload = {
                        "run_id": run_id,
                        "signal_id": signal_id,
                        "candidate_instance_id": candidate_instance_id,
                        "paper_trade_replay_key": paper_trade_replay_key,
                        "asset": ticker,
                        "market_slug": meta.get("slug", ""),
                        "side": model_side,
                        "outcome": model_side,
                        "edge": float(model_ev),
                        "ev": float(model_ev),
                        "probability": float(getattr(probability, "p_yes" if model_side == "YES" else "p_no", 0.0)),
                        "volatility_regime": volatility_regime,
                        "trend_regime": regime_detail.get("trend_regime"),
                        "entry_price": float(candidate.yes_ask if model_side == "YES" else candidate.no_ask),
                        "proposed_size_usd": proposed_size_usd,
                        "filter_name": eval_result["filter_name"],
                        "filter_version": eval_result["filter_version"],
                        "filter_params": eval_result["filter_params"],
                        "shadow_pass": eval_result["shadow_pass"],
                        "shadow_reason": eval_result["shadow_reason"],
                        "would_trade": eval_result["would_trade"],
                        "schema_version": "1.0",

                        # Companion identity mapping fields for QuantEventLogger
                        "market_key": getattr(candidate, "market_id", ""),
                        "condition_id": meta.get("condition_id", ""),
                        "token_id": selected_token_id,
                        "epoch_start_ts": getattr(ptb_info, "epoch_start_ts", 0),
                    }
                    self.quant_events.log_signal_filter_shadow_phase_b(payload)
                except Exception as inner_e:
                    LOGGER.error("[SHADOW] Error evaluating shadow filter %s: %s", filter_name, inner_e)
        except Exception as e:
            LOGGER.error("[SHADOW] Fail-soft caught telemetry exception: %s", e, exc_info=True)

    def _display_payload_with_candidate_trace_identity(self, payload: dict[str, object]) -> dict[str, object]:
        display_payload = dict(payload)
        timestamp = self._utc_timestamp()
        logger = getattr(self, "quant_events", None)
        enrich = getattr(logger, "_with_candidate_trace_identity", None)
        if callable(enrich):
            try:
                return dict(enrich(display_payload, timestamp))
            except Exception:
                pass
        try:
            for key, value in QuantEventLogger._normalized_identity_companion_fields(display_payload).items():
                if value and not display_payload.get(key):
                    display_payload[key] = value
            for key, value in QuantEventLogger._candidate_trace_identity_fields(display_payload, timestamp).items():
                if value and not display_payload.get(key):
                    display_payload[key] = value
        except Exception:
            pass
        return display_payload

    def _execution_parent_detail(self, payload: dict[str, object]) -> tuple[str, dict[str, object]]:
        details = getattr(self, "last_quant_details", {})
        if not isinstance(details, dict):
            return "", {}

        source_market = str(payload.get("source_market_id") or payload.get("market_id") or "")
        ticker = str(payload.get("ticker") or payload.get("asset") or "").upper()
        if not ticker and source_market.startswith("pm-5m-"):
            ticker = self._ticker_from_market_id(source_market)
        if ticker and isinstance(details.get(ticker), dict):
            return ticker, details[ticker]

        refs = {
            str(value).strip()
            for value in (
                payload.get("source_market_id"),
                payload.get("market_id"),
                payload.get("condition_id"),
                payload.get("market_slug"),
            )
            if str(value or "").strip()
        }
        token_id = str(payload.get("token_id") or "").strip()
        outcome = str(payload.get("outcome") or "").upper()
        for candidate_ticker, detail in details.items():
            if not isinstance(detail, dict):
                continue
            detail_refs = {
                str(value).strip()
                for value in (
                    detail.get("market_id"),
                    detail.get("best_market"),
                    detail.get("source_market_id"),
                    detail.get("condition_id"),
                    detail.get("market_slug"),
                )
                if str(value or "").strip()
            }
            detail_tokens = {
                str(value).strip()
                for value in (
                    detail.get("token_id"),
                    detail.get("yes_token_id"),
                    detail.get("no_token_id"),
                )
                if str(value or "").strip()
            }
            detail_side = str(detail.get("side") or detail.get("best_side") or detail.get("outcome") or "").upper()
            if refs and detail_refs and refs.intersection(detail_refs):
                return str(candidate_ticker).upper(), detail
            if token_id and token_id in detail_tokens and (not outcome or not detail_side or outcome == detail_side):
                return str(candidate_ticker).upper(), detail
        return ticker, {}

    def _execution_payload_with_parent_context(self, payload: dict[str, object]) -> dict[str, object]:
        enriched = dict(payload)
        ticker, parent = self._execution_parent_detail(enriched)
        copied = False

        def put_if_missing(key: str, value: object) -> None:
            nonlocal copied
            if enriched.get(key) not in {None, ""}:
                return
            if value in {None, ""}:
                return
            enriched[key] = value
            copied = True

        def source_available(key: str) -> bool:
            return enriched.get(key) not in {None, ""}

        def put_model_field(key: str, value: object, source: str) -> None:
            put_if_missing(key, value)
            if enriched.get(key) not in {None, ""}:
                enriched.setdefault(f"{key}_source", source)

        parent_fields = (
            "candidate_id",
            "signal_id",
            "candidate_trace_id",
            "parent_candidate_trace_id",
            "trace_link_reason",
            "market_slug",
            "condition_id",
            "lifecycle_phase",
            "market_epoch_start",
            "market_epoch_end",
            "seconds_remaining",
            "market_price",
            "fair_value",
            "true_probability",
            "ev_after_spread",
            "model_probability_yes",
            "model_probability_no",
            "fair_value_yes",
            "fair_value_no",
            "model_p_yes",
            "model_p_no",
            "p_yes",
            "p_no",
            "probability_model_stage",
            "ev_calculation_stage",
            "model_attempted",
            "probability_model_called",
            "probability_model_output_visible",
            "model_output_missing_reason",
            "model_output_source",
            "model_handoff_stage",
            "probability_model_gate_reason",
            "model_not_run_reason",
            "ev_missing_reason",
        )
        for key in parent_fields:
            put_if_missing(key, parent.get(key))

        if ticker:
            put_if_missing("ticker", ticker)
            put_if_missing("asset", ticker)

        source_market = str(enriched.get("source_market_id") or enriched.get("market_id") or parent.get("market_id") or parent.get("best_market") or "")
        if source_market:
            put_if_missing("market_id", source_market)
        outcome = str(enriched.get("outcome") or parent.get("side") or parent.get("best_side") or parent.get("outcome") or "").upper()
        token_id = str(enriched.get("token_id") or parent.get("token_id") or "").strip()
        yes_token_id = str(enriched.get("yes_token_id") or parent.get("yes_token_id") or "").strip()
        no_token_id = str(enriched.get("no_token_id") or parent.get("no_token_id") or "").strip()
        if outcome not in {"YES", "NO"} and token_id:
            if yes_token_id and token_id == yes_token_id:
                outcome = "YES"
            elif no_token_id and token_id == no_token_id:
                outcome = "NO"
        if outcome in {"YES", "NO"}:
            put_if_missing("outcome", outcome)
            if enriched.get("side") in {None, "", "BUY", "SELL"}:
                enriched["side"] = outcome
                copied = True
        epoch_start = self._diagnostic_int(enriched.get("market_epoch_start") or parent.get("market_epoch_start") or parent.get("epoch_start") or parent.get("epoch_start_ts")) or 0
        if not enriched.get("decision_id") and source_market and ticker:
            enriched["decision_id"] = self._phase2_candidate_hash(
                "decision",
                source_market,
                ticker,
                outcome or "UNKNOWN",
                epoch_start,
            )
            copied = True

        if outcome == "YES":
            put_model_field("true_probability", parent.get("model_probability_yes", parent.get("p_yes", parent.get("model_p_yes"))), "parent_yes_probability_alias")
            put_model_field("fair_value", parent.get("fair_value_yes", parent.get("p_yes", parent.get("model_p_yes"))), "parent_yes_fair_value_alias")
        elif outcome == "NO":
            put_model_field("true_probability", parent.get("model_probability_no", parent.get("p_no", parent.get("model_p_no"))), "parent_no_probability_alias")
            put_model_field("fair_value", parent.get("fair_value_no", parent.get("p_no", parent.get("model_p_no"))), "parent_no_fair_value_alias")
        if source_available("ev_after_spread"):
            enriched.setdefault("ev_after_spread_source", "parent_decision_context")

        if enriched.get("true_probability") not in {None, ""}:
            enriched.setdefault("true_probability_available", True)
        if enriched.get("fair_value") not in {None, ""}:
            enriched.setdefault("fair_value_available", True)
        if enriched.get("ev_after_spread") not in {None, ""}:
            enriched.setdefault("ev_after_spread_available", True)

        if enriched.get("risk_state") in {None, ""}:
            if bool(enriched.get("risk_approved")):
                enriched["risk_state"] = "approved"
            elif enriched.get("risk_plan_present") is not None:
                enriched["risk_state"] = "blocked"
        put_if_missing("risk_mode", self._risk_mode_state.current_mode.value)

        required = ("decision_id", "true_probability", "fair_value", "lifecycle_phase", "market_slug", "risk_state")
        missing = [field for field in required if enriched.get(field) in {None, ""}]
        if missing:
            enriched["execution_context_missing_fields"] = missing
            for field in missing:
                enriched.setdefault(f"{field}_missing_reason", "not_available_at_execution")
        for field in ("true_probability", "fair_value", "ev_after_spread", "side"):
            if enriched.get(field) in {None, ""}:
                enriched.setdefault(f"{field}_propagation_status", "missing_after_parent_context")
            else:
                enriched.setdefault(f"{field}_propagation_status", "propagated")
        enriched["execution_context_source"] = "parent_decision_context" if copied else "execution_payload_only"
        return enriched

    def _emit_quant_event(self, event_method: str, payload: dict[str, object] | None = None) -> bool:
        logger = getattr(self, "quant_events", None)
        if logger is None:
            state = self._default_observability_health_display_state()
            state["jsonl_status"] = "UNKNOWN"
            self._observability_health_display_state = state
            return False
        try:
            logger.mode = self._runtime_mode()
            method = getattr(logger, event_method)
            producer_label = self._event_producer_label(event_method)
            raw_payload = dict(payload or {})
            raw_payload.setdefault("producer_event_type", producer_label)
            raw_payload.setdefault("producer", producer_label)
            if event_method == "log_execution":
                raw_payload = self._execution_payload_with_parent_context(raw_payload)
            if event_method in {"log_market_snapshot", "log_decision", "log_execution", "log_trade_open", "log_trade_close"}:
                enriched_payload = self._phase2_complete_lifecycle_observability(raw_payload)
            else:
                enriched_payload = raw_payload

            if event_method == "log_decision":
                # Promote 33 display-only keys from payload["display"] to payload root if missing
                display_dict = enriched_payload.get("display")
                if isinstance(display_dict, dict):
                    display_only_keys = [
                        "adaptive_cutoff_denied_reason", "ask_price", "best_market", "best_side",
                        "book_to_tradable_seconds", "clob_consecutive_failures", "clob_last_error_category",
                        "clob_last_error_class", "delta_multiplier", "delta_regime", "depth_ready",
                        "discovery_to_book_seconds", "distance_from_ptb_pct", "epoch_end_ts", "epoch_start_ts",
                        "final_size", "frequency_multiplier", "last_successful_orderbook_age_ms",
                        "liquidity_ready", "min_ev", "mode", "model_p_no", "model_p_yes",
                        "no_orderbook_age_ms", "p_no", "p_yes", "price_change_pct", "price_velocity",
                        "realized_volatility", "risk_plan_zero_diagnostics", "score",
                        "total_discovery_to_tradable_seconds", "yes_orderbook_age_ms"
                    ]
                    for key in display_only_keys:
                        if key in display_dict and key not in enriched_payload:
                            enriched_payload[key] = display_dict[key]

            display_payload = self._display_payload_with_candidate_trace_identity(enriched_payload)
            emitted = bool(method(display_payload))
            self._observability_health_display_state = self._observability_health_from_payload(
                event_method,
                display_payload,
                jsonl_ok=emitted,
            )
            return emitted
        except Exception as exc:
            LOGGER.warning("[OBSERVABILITY] quant event failed | method=%s error=%s", event_method, exc)
            state = self._default_observability_health_display_state()
            state["jsonl_status"] = "WARN"
            state["jsonl_ok"] = False
            state["latest_producer"] = self._event_producer_label(event_method)
            state["latest_schema_version"] = str(getattr(logger, "schema_version", "") or "--")
            self._observability_health_display_state = state
            return False

    def _utc_timestamp(self) -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    def _phase1_execution_latency_truth_level(self) -> str:
        return "paper_simulated" if self.settings.paper_trading else "unknown"

    def _phase3_paper_proxy_ms(self, ts_start: str, ts_end: str) -> "float | None":
        try:
            def _parse(s: str) -> datetime:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            return round((_parse(ts_end) - _parse(ts_start)).total_seconds() * 1000, 3)
        except Exception:
            return None

    def _phase4_build_quote_lineage(self, market_id: str, ticker_key: str) -> dict:
        try:
            import hashlib as _hashlib
            tk = str(ticker_key or "").upper()
            token_pair_key = str(getattr(self, "_last_successful_yes_no_book_token_pair_key", {}).get(tk) or "")
            quote_capture_ts = str(getattr(self, "_last_successful_yes_no_book_at_utc", {}).get(tk) or "")
            quote_source = str(getattr(self, "_last_orderbook_refresh_source", {}).get(tk) or "unknown")
            if token_pair_key and quote_capture_ts and market_id:
                ts_second = quote_capture_ts.split(".")[0].rstrip("Z") + "Z"
                h = _hashlib.sha1(f"{market_id}|{token_pair_key}|{ts_second}".encode()).hexdigest()[:12]
                quote_lineage_id: "str | None" = f"ql_{h}"
                quote_snapshot_id: "str | None" = f"qs_{h}"
            else:
                quote_lineage_id = None
                quote_snapshot_id = None
            ctx: dict = {
                "quote_lineage_id": quote_lineage_id,
                "quote_capture_ts": quote_capture_ts or None,
                "quote_snapshot_id": quote_snapshot_id,
                "quote_source": quote_source,
            }
            if not hasattr(self, "_last_quote_lineage_context"):
                self._last_quote_lineage_context = {}
            self._last_quote_lineage_context[tk] = ctx
            return ctx
        except Exception:
            return {}

    def _phase4_quote_lineage_carry(self, ticker_key: str) -> dict:
        try:
            ctx = getattr(self, "_last_quote_lineage_context", {}).get(str(ticker_key or "").upper(), {})
            return dict(ctx) if ctx else {}
        except Exception:
            return {}

    def _begin_cycle_timing(self) -> None:
        now_mono = time.monotonic()
        previous_started = float(getattr(self, "_previous_cycle_started_monotonic", 0.0) or 0.0)
        self._effective_outer_loop_interval_seconds = (
            round(max(0.0, now_mono - previous_started), 3)
            if previous_started > 0
            else None
        )
        self._previous_cycle_started_monotonic = now_mono
        self._cycle_started_monotonic = now_mono
        self._cycle_started_at_utc = self._utc_timestamp()
        self._current_cycle_market_count = 0
        self._market_evaluation_started_monotonic.clear()
        self._market_evaluation_started_at_utc.clear()
        self._current_cycle_market_sequence_index.clear()
        self._current_cycle_market_sequence_count.clear()
        self._last_scan_cycle_duration_ms = 0

    def _cycle_elapsed_ms(self) -> int:
        started = float(getattr(self, "_cycle_started_monotonic", 0.0) or 0.0)
        if started <= 0:
            return 0
        return int(max(0.0, time.monotonic() - started) * 1000)

    def set_runtime_cadence_observability(
        self,
        *,
        configured_decision_interval_seconds: float | int | None = None,
        decision_loop_target_seconds: float | int = 1.0,
        snapshot_sampling_interval_seconds: float | int = 5.0,
        market_discovery_interval_seconds: float | int = 15.0,
        outer_loop_poll_interval_seconds: float | int = 0.25,
    ) -> None:
        """Store runtime cadence configuration for emitted diagnostics only."""
        try:
            self._configured_decision_loop_interval_seconds = (
                float(configured_decision_interval_seconds)
                if configured_decision_interval_seconds is not None
                else None
            )
        except (TypeError, ValueError):
            self._configured_decision_loop_interval_seconds = None
        self._intended_decision_loop_target_seconds = float(decision_loop_target_seconds)
        self._snapshot_sampling_interval_seconds = float(snapshot_sampling_interval_seconds)
        self._market_discovery_interval_seconds = float(market_discovery_interval_seconds)
        self._outer_loop_poll_interval_seconds = float(outer_loop_poll_interval_seconds)

    def _mark_market_evaluation_started(
        self,
        ticker: str,
        *,
        sequence_index: int = 0,
        sequence_count: int = 0,
    ) -> None:
        """Record per-market scheduler timing for observability only."""
        ticker_key = ticker.upper()
        self._market_evaluation_started_monotonic[ticker_key] = time.monotonic()
        self._market_evaluation_started_at_utc[ticker_key] = self._utc_timestamp()
        if sequence_index > 0:
            self._current_cycle_market_sequence_index[ticker_key] = int(sequence_index)
        if sequence_count > 0:
            self._current_cycle_market_sequence_count[ticker_key] = int(sequence_count)

    def _scheduler_cadence_observability_detail(self, ticker: str) -> dict[str, object]:
        """Expose cycle/market hot-path timing without changing cadence or gates."""
        ticker_key = ticker.upper()
        now_mono = time.monotonic()
        cycle_started = float(getattr(self, "_cycle_started_monotonic", 0.0) or 0.0)
        market_started = getattr(self, "_market_evaluation_started_monotonic", {}).get(ticker_key)
        last_success_mono = getattr(self, "_last_successful_yes_no_book_monotonic", {}).get(ticker_key)
        recovery_detail = getattr(self, "_last_empty_book_recovery_detail", {}).get(ticker_key, {})
        try:
            recovery_seconds = float(recovery_detail.get("recovery_wait_seconds", 0.0) or 0.0)
        except (TypeError, ValueError):
            recovery_seconds = 0.0
        detail: dict[str, object] = {
            "scheduler_cadence_source": "run_single_cycle_market_loop",
            "hot_path_timing_source": "runtime_market_evaluation",
            "configured_decision_loop_interval_seconds": getattr(self, "_configured_decision_loop_interval_seconds", None),
            "intended_decision_loop_target_seconds": getattr(self, "_intended_decision_loop_target_seconds", 1.0),
            "effective_outer_loop_interval_seconds": getattr(self, "_effective_outer_loop_interval_seconds", None),
            "snapshot_sampling_interval_seconds": getattr(self, "_snapshot_sampling_interval_seconds", 5.0),
            "market_discovery_interval_seconds": getattr(self, "_market_discovery_interval_seconds", 15.0),
            "outer_loop_poll_interval_seconds": getattr(self, "_outer_loop_poll_interval_seconds", 0.25),
            "market_evaluation_asset": ticker_key,
            "market_evaluation_started_at": getattr(self, "_market_evaluation_started_at_utc", {}).get(ticker_key, ""),
            "market_sequence_index": getattr(self, "_current_cycle_market_sequence_index", {}).get(ticker_key, 0),
            "market_sequence_count": getattr(self, "_current_cycle_market_sequence_count", {}).get(
                ticker_key,
                int(getattr(self, "_current_cycle_market_count", 0) or 0),
            ),
            "cycle_elapsed_ms_at_market_evaluation": self._cycle_elapsed_ms(),
            "empty_book_recovery_duration_ms": int(max(0.0, recovery_seconds) * 1000),
        }
        if market_started is not None:
            detail["market_evaluation_duration_ms"] = int(max(0.0, now_mono - market_started) * 1000)
            if cycle_started > 0:
                detail["market_evaluation_started_ms_since_cycle"] = int(
                    max(0.0, market_started - cycle_started) * 1000
                )
        if last_success_mono is not None:
            candidate_queue_age_ms = int(max(0.0, now_mono - last_success_mono) * 1000)
            detail.update({
                "candidate_created_at": getattr(self, "_last_successful_yes_no_book_at_utc", {}).get(ticker_key, ""),
                "candidate_enqueue_at": getattr(self, "_last_successful_yes_no_book_at_utc", {}).get(ticker_key, ""),
                "candidate_dequeue_at": self._utc_timestamp(),
                "candidate_queue_age_ms": candidate_queue_age_ms,
                "hot_path_admission_wait_ms": candidate_queue_age_ms,
                "candidate_queue_age_source": "last_successful_yes_no_book_to_decision",
            })
        detail.update({
            "candidate_queue_ownership": "implicit_orderbook_refresh_cache",
            "candidate_revisit_scheduling_source": "scheduled_run_single_cycle",
            "hot_path_admission_trigger": "scheduled_decision_cycle",
            "event_vs_polling_classification": "polling_revisit_driven",
            "executable_liquidity_event_role": "passive_telemetry_only",
            "executable_liquidity_triggered_hot_path": False,
            "market_snapshot_decision_pipeline_linkage": "disconnected_passive_snapshot_to_scheduled_decision",
            "candidate_handoff_boundary": (
                f"{getattr(self, '_last_orderbook_refresh_source', {}).get(ticker_key, 'unknown')}->scheduled_run_single_cycle"
            ),
        })
        return detail

    @staticmethod
    def _orderbook_token_pair_key(
        *,
        condition_id: object = "",
        yes_token_id: object = "",
        no_token_id: object = "",
        market_slug: object = "",
    ) -> str:
        yes = str(yes_token_id or "").strip()
        no = str(no_token_id or "").strip()
        if not yes and not no:
            return ""
        condition = str(condition_id or market_slug or "").strip()
        return f"{condition}|YES:{yes}|NO:{no}"

    def _mark_orderbook_refresh(
        self,
        ticker: str,
        *,
        source: str,
        trigger: str,
        executable_yes_no_book: bool = False,
        condition_id: object = "",
        yes_token_id: object = "",
        no_token_id: object = "",
        market_slug: object = "",
    ) -> None:
        """Track orderbook refresh cadence for observability without changing fetch behavior."""
        ticker_key = ticker.upper()
        now_mono = time.monotonic()
        now_utc = self._utc_timestamp()
        token_pair_key = self._orderbook_token_pair_key(
            condition_id=condition_id,
            yes_token_id=yes_token_id,
            no_token_id=no_token_id,
            market_slug=market_slug,
        )
        self._last_orderbook_refresh_monotonic[ticker_key] = now_mono
        self._last_orderbook_refresh_at_utc[ticker_key] = now_utc
        self._last_orderbook_refresh_source[ticker_key] = source
        self._last_orderbook_refresh_trigger[ticker_key] = trigger
        self._last_orderbook_refresh_token_pair_key[ticker_key] = token_pair_key
        if executable_yes_no_book:
            self._last_successful_yes_no_book_monotonic[ticker_key] = now_mono
            self._last_successful_yes_no_book_at_utc[ticker_key] = now_utc
            self._last_successful_yes_no_book_token_pair_key[ticker_key] = token_pair_key

    def _orderbook_refresh_observability_detail(
        self,
        ticker: str,
        *,
        current_executable_yes_no_book: bool = False,
        record_decision_cycle: bool = False,
        current_fetch_succeeded: bool | None = None,
        condition_id: object = "",
        yes_token_id: object = "",
        no_token_id: object = "",
        market_slug: object = "",
    ) -> dict[str, object]:
        ticker_key = ticker.upper()
        now_mono = time.monotonic()
        last_refresh_mono = getattr(self, "_last_orderbook_refresh_monotonic", {}).get(ticker_key)
        last_success_mono = getattr(self, "_last_successful_yes_no_book_monotonic", {}).get(ticker_key)
        previous_decision_mono = getattr(self, "_last_decision_cycle_monotonic", {}).get(ticker_key)
        decision_interval = None
        if record_decision_cycle:
            if previous_decision_mono is not None:
                decision_interval = round(max(0.0, now_mono - previous_decision_mono), 3)
            if not hasattr(self, "_last_decision_cycle_monotonic"):
                self._last_decision_cycle_monotonic = {}
            self._last_decision_cycle_monotonic[ticker_key] = now_mono
        refresh_age_ms = (
            int(max(0.0, now_mono - last_refresh_mono) * 1000)
            if last_refresh_mono is not None
            else None
        )
        executable_age_ms = (
            int(max(0.0, now_mono - last_success_mono) * 1000)
            if last_success_mono is not None
            else None
        )
        decision_token_pair_key = self._orderbook_token_pair_key(
            condition_id=condition_id,
            yes_token_id=yes_token_id,
            no_token_id=no_token_id,
            market_slug=market_slug,
        )
        last_refresh_pair = getattr(self, "_last_orderbook_refresh_token_pair_key", {}).get(ticker_key, "")
        last_success_pair = getattr(self, "_last_successful_yes_no_book_token_pair_key", {}).get(ticker_key, "")
        lineage_match = bool(decision_token_pair_key and last_success_pair and decision_token_pair_key == last_success_pair)
        if current_fetch_succeeded is True and current_executable_yes_no_book:
            fetch_status = "fresh_fetch_executable"
            stale_source = "CURRENT_DECISION_FETCH_EXECUTABLE"
        elif current_fetch_succeeded is True:
            fetch_status = "fresh_fetch_non_executable"
            stale_source = (
                "CURRENT_FETCH_NON_EXECUTABLE_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR"
                if lineage_match
                else "CURRENT_FETCH_NON_EXECUTABLE_PRIOR_EXECUTABLE_DIFFERENT_OR_UNKNOWN_PAIR"
                if last_success_mono is not None
                else "CURRENT_FETCH_NON_EXECUTABLE_NO_PRIOR_EXECUTABLE"
            )
        elif current_fetch_succeeded is False:
            fetch_status = "fresh_fetch_failed"
            stale_source = (
                "CURRENT_FETCH_FAILED_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR"
                if lineage_match
                else "CURRENT_FETCH_FAILED_PRIOR_EXECUTABLE_DIFFERENT_OR_UNKNOWN_PAIR"
                if last_success_mono is not None
                else "CURRENT_FETCH_FAILED_NO_PRIOR_EXECUTABLE"
            )
        else:
            fetch_status = "fresh_fetch_not_attempted_or_unobserved"
            stale_source = (
                "NO_CURRENT_FETCH_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR"
                if lineage_match
                else "NO_CURRENT_FETCH_PRIOR_EXECUTABLE_DIFFERENT_OR_UNKNOWN_PAIR"
                if last_success_mono is not None
                else "NO_CURRENT_FETCH_NO_PRIOR_EXECUTABLE"
            )
        return {
            "decision_cycle_started_at": str(getattr(self, "_cycle_started_at_utc", "") or ""),
            "last_orderbook_refresh_at": getattr(self, "_last_orderbook_refresh_at_utc", {}).get(ticker_key, ""),
            "orderbook_snapshot_age_ms_at_decision": refresh_age_ms,
            "last_successful_yes_no_book_at": getattr(self, "_last_successful_yes_no_book_at_utc", {}).get(ticker_key, ""),
            "orderbook_refresh_source": getattr(self, "_last_orderbook_refresh_source", {}).get(ticker_key, ""),
            "orderbook_refresh_trigger": getattr(self, "_last_orderbook_refresh_trigger", {}).get(ticker_key, ""),
            "decision_token_pair_key": decision_token_pair_key,
            "last_orderbook_refresh_token_pair_key": last_refresh_pair,
            "last_successful_yes_no_book_token_pair_key": last_success_pair,
            "orderbook_lineage_match": lineage_match,
            "orderbook_current_fetch_status": fetch_status,
            "orderbook_stale_reuse_source": stale_source,
            "decision_cycle_interval_seconds": decision_interval,
            "actual_market_revisit_frequency_seconds": decision_interval,
            "orderbook_reuse_detected": bool(
                last_success_mono is not None and not current_executable_yes_no_book
            ),
            "executable_book_last_seen_age_ms": executable_age_ms,
        }

    @staticmethod
    def _orderbook_lineage_compact_text(value: object, *, limit: int = 160) -> str:
        text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
        if len(text) > limit:
            return text[: max(0, limit - 3)] + "..."
        return text

    @staticmethod
    def _orderbook_lineage_raw_count(ob: object, key: str) -> int | None:
        raw = getattr(ob, "raw_response", None)
        if not isinstance(raw, dict):
            return None
        value = raw.get(key)
        if isinstance(value, list):
            return len(value)
        return None

    def _orderbook_lineage_side_status(
        self,
        *,
        ob: object,
        bid: object,
        ask: object,
        current_fetch_status: str,
        orderbook_error: str = "",
    ) -> str:
        error = str(orderbook_error or "").lower()
        if ob is None:
            if current_fetch_status == "fresh_fetch_failed":
                return "fetch_failed"
            if current_fetch_status == "fresh_fetch_not_attempted":
                return "not_attempted"
            return "unknown"
        if "stale_orderbook" in error or "stale_book" in error:
            return "stale"
        if "invalid_orderbook" in error:
            return "invalid"
        bid_value = self._diagnostic_float(bid)
        ask_value = self._diagnostic_float(ask)
        if bid_value > 0 and ask_value > 0:
            return "executable"
        if bid_value <= 0 and ask_value <= 0:
            return "both_sides_empty"
        if bid_value <= 0:
            return "one_sided_empty_bids"
        return "one_sided_empty_asks"

    @staticmethod
    def _orderbook_lineage_current_fetch_status(
        orderbook_refresh_detail: dict[str, object],
        orderbook_fetch_succeeded: bool | None,
        current_executable_yes_no_book: bool,
    ) -> str:
        raw = str(orderbook_refresh_detail.get("orderbook_current_fetch_status") or "").strip()
        if raw == "fresh_fetch_not_attempted_or_unobserved":
            return "fresh_fetch_not_attempted"
        if raw:
            return raw
        if orderbook_fetch_succeeded is True and current_executable_yes_no_book:
            return "fresh_fetch_executable"
        if orderbook_fetch_succeeded is True:
            return "fresh_fetch_non_executable"
        if orderbook_fetch_succeeded is False:
            return "fresh_fetch_failed"
        if orderbook_fetch_succeeded is None:
            return "unknown"
        return "unknown"

    def _build_orderbook_lineage_probe_payload(
        self,
        *,
        ticker: str,
        market_id: object = "",
        market_slug: object = "",
        condition_id: object = "",
        yes_token_id: object = "",
        no_token_id: object = "",
        yes_ob: object = None,
        no_ob: object = None,
        yes_bid: object = 0.0,
        yes_ask: object = 0.0,
        yes_bid_size: object = 0.0,
        yes_ask_size: object = 0.0,
        no_bid: object = 0.0,
        no_ask: object = 0.0,
        no_bid_size: object = 0.0,
        no_ask_size: object = 0.0,
        yes_orderbook_age_ms: object = None,
        no_orderbook_age_ms: object = None,
        orderbook_fetch_succeeded: bool | None = None,
        current_executable_yes_no_book: bool = False,
        orderbook_refresh_detail: dict[str, object] | None = None,
        orderbook_readiness_reason: object = "",
        orderbook_error: object = "",
        clob_error_detail: dict[str, object] | None = None,
        empty_book_recovery_detail: dict[str, object] | None = None,
        token_mapping_warning: object = "",
        lifecycle_phase: object = "",
        seconds_remaining: object = None,
        fetch_attempt_ts: object = "",
        fetch_complete_ts: object = "",
        fetch_duration_ms: object = None,
        terminal_blocker_reason: object = "",
        terminal_blocker_stage: object = "",
        contextual_blockers: list[str] | None = None,
    ) -> dict[str, object]:
        detail = dict(orderbook_refresh_detail or {})
        clob_detail = dict(clob_error_detail or {})
        recovery_detail = dict(empty_book_recovery_detail or {})
        ticker_key = str(ticker or "").upper()
        event_ts = self._utc_timestamp()
        current_fetch_status = self._orderbook_lineage_current_fetch_status(
            detail,
            orderbook_fetch_succeeded,
            current_executable_yes_no_book,
        )
        token_pair_key = str(
            detail.get("decision_token_pair_key")
            or self._orderbook_token_pair_key(
                condition_id=condition_id,
                yes_token_id=yes_token_id,
                no_token_id=no_token_id,
                market_slug=market_slug,
            )
        )
        run_id = str(getattr(getattr(self, "quant_events", None), "run_id", "") or "")
        lineage_raw = "|".join(
            str(part or "")
            for part in (
                run_id,
                ticker_key,
                token_pair_key,
                fetch_attempt_ts,
                current_fetch_status,
            )
        )
        lineage_id = "oblp_" + hashlib.sha1(lineage_raw.encode("utf-8")).hexdigest()[:12]

        yes_age = self._diagnostic_int(yes_orderbook_age_ms)
        no_age = self._diagnostic_int(no_orderbook_age_ms)
        current_ages = [age for age in (yes_age, no_age) if age is not None and age > 0]
        cached_age = self._diagnostic_int(detail.get("executable_book_last_seen_age_ms"))
        quote_age_ms = max(current_ages) if current_ages and current_fetch_status == "fresh_fetch_executable" else cached_age
        if quote_age_ms is None:
            quote_age_source = "not_available"
        elif current_ages and current_fetch_status == "fresh_fetch_executable":
            quote_age_source = "current_fetch_raw_timestamp"
        else:
            quote_age_source = "last_successful_yes_no_book_cache"

        cached_available = bool(detail.get("last_successful_yes_no_book_at") or cached_age is not None)
        cache_match_raw = detail.get("orderbook_lineage_match")
        cache_token_pair_match = bool(cache_match_raw) if cache_match_raw is not None else None
        book_used_source = "unknown"
        cached_used = False
        if current_fetch_status == "fresh_fetch_executable" and current_executable_yes_no_book:
            book_used_source = "current_fetch"
        elif current_fetch_status in {"fresh_fetch_failed", "fresh_fetch_non_executable", "fresh_fetch_not_attempted"}:
            book_used_source = "none"

        contextual = list(contextual_blockers or [])
        readiness = str(orderbook_readiness_reason or "").strip()
        if readiness and readiness not in contextual:
            contextual.append(readiness)
        token_warning = str(token_mapping_warning or "").strip()
        if token_warning and "token_mapping_warning" not in contextual:
            contextual.append("token_mapping_warning")

        error_text = self._orderbook_lineage_compact_text(orderbook_error)
        error_type = str(
            clob_detail.get("clob_error_category")
            or clob_detail.get("clob_exception_type")
            or ("orderbook_error" if error_text else "")
        )
        terminal = str(terminal_blocker_reason or "").strip()
        terminal_stage_raw = str(terminal_blocker_stage or "").strip()
        terminal_gate_stage = "unknown"
        if terminal:
            terminal_gate_stage = "market_data" if terminal_stage_raw.startswith("market_data") else terminal_stage_raw or "unknown"
        elif current_fetch_status != "unknown":
            terminal_gate_stage = "none"

        yes_fetch_status = self._orderbook_lineage_side_status(
            ob=yes_ob,
            bid=yes_bid,
            ask=yes_ask,
            current_fetch_status=current_fetch_status,
            orderbook_error=error_text,
        )
        no_fetch_status = self._orderbook_lineage_side_status(
            ob=no_ob,
            bid=no_bid,
            ask=no_ask,
            current_fetch_status=current_fetch_status,
            orderbook_error=error_text,
        )

        def normalization_status_for(side_status: str) -> str:
            return {
                "executable": "accepted_executable",
                "one_sided_empty_bids": "rejected_empty_bids",
                "one_sided_empty_asks": "rejected_empty_asks",
                "both_sides_empty": "rejected_empty_both",
                "stale": "rejected_stale",
                "invalid": "rejected_invalid_price",
                "not_attempted": "not_attempted",
            }.get(side_status, "unknown")

        serialized_yes_no_bid_ask_present = bool(current_executable_yes_no_book)
        serialized_book_source = (
            "current_fetch"
            if book_used_source == "current_fetch"
            else "not_serialized"
            if book_used_source == "none"
            else "unknown"
        )
        book_used_for_decision = (
            "current_fetch"
            if book_used_source == "current_fetch"
            else "unavailable"
            if book_used_source == "none"
            else "unknown"
        )
        book_used_token_pair_match = (
            bool(token_pair_key)
            if book_used_source == "current_fetch"
            else cache_token_pair_match
            if book_used_source == "none"
            else None
        )
        contextual_lower = {str(value or "").lower() for value in contextual}
        terminal_lower = terminal.lower()
        if "empty_book" in terminal_lower or "empty_orderbook" in terminal_lower:
            empty_book_role = "terminal"
        elif any("empty_book" in value or "empty_orderbook" in value for value in contextual_lower):
            empty_book_role = "contextual"
        elif current_fetch_status == "unknown" and not readiness:
            empty_book_role = "unknown"
        else:
            empty_book_role = "absent"

        return {
            "probe_id": "ORDERBOOK_LINEAGE_PROBE_V1",
            "schema_version": "orderbook_lineage_probe_v1",
            "event_type": "orderbook_lineage_probe",
            "event_ts": event_ts,
            "producer": "trader.orderbook_lineage_probe",
            "probe_scope": "decision_cycle_fetch",
            "latency_truth_level": "proxy",
            "timestamp_source": "runtime_utc_clock",
            "probe_authority_level": "evidence_only",
            "policy_authority": "none",
            "runtime_decision_authority": False,
            "execution_authority": False,
            "risk_authority": False,
            "asset": ticker_key,
            "ticker": ticker_key,
            "market_id": str(market_id or ""),
            "market_slug": str(market_slug or ""),
            "condition_id": str(condition_id or ""),
            "yes_token_id": str(yes_token_id or ""),
            "no_token_id": str(no_token_id or ""),
            "token_id": str(yes_token_id or ""),
            "outcome": "YES/NO",
            "orderbook_token_pair_key": token_pair_key,
            "orderbook_lineage_id": lineage_id,
            "fetch_attempt_ts": str(fetch_attempt_ts or ""),
            "fetch_complete_ts": str(fetch_complete_ts or ""),
            "fetch_duration_ms": self._diagnostic_float(fetch_duration_ms, default=0.0) if fetch_duration_ms is not None else None,
            "current_fetch_status": current_fetch_status,
            "current_fetch_succeeded": orderbook_fetch_succeeded,
            "current_fetch_error_type": error_type,
            "current_fetch_error_message": error_text,
            "yes_fetch_status": yes_fetch_status,
            "no_fetch_status": no_fetch_status,
            "yes_bids_count": self._orderbook_lineage_raw_count(yes_ob, "top_bids"),
            "yes_asks_count": self._orderbook_lineage_raw_count(yes_ob, "top_asks"),
            "no_bids_count": self._orderbook_lineage_raw_count(no_ob, "top_bids"),
            "no_asks_count": self._orderbook_lineage_raw_count(no_ob, "top_asks"),
            "yes_best_bid": self._diagnostic_float(yes_bid),
            "yes_best_ask": self._diagnostic_float(yes_ask),
            "yes_best_bid_size": self._diagnostic_float(yes_bid_size),
            "yes_best_ask_size": self._diagnostic_float(yes_ask_size),
            "no_best_bid": self._diagnostic_float(no_bid),
            "no_best_ask": self._diagnostic_float(no_ask),
            "no_best_bid_size": self._diagnostic_float(no_bid_size),
            "no_best_ask_size": self._diagnostic_float(no_ask_size),
            "yes_raw_age_ms": yes_age,
            "no_raw_age_ms": no_age,
            "last_successful_yes_no_book_at": str(detail.get("last_successful_yes_no_book_at") or ""),
            "last_successful_yes_no_book_age_ms": cached_age,
            "last_successful_yes_no_book_token_pair_key": str(detail.get("last_successful_yes_no_book_token_pair_key") or ""),
            "cache_token_pair_match": cache_token_pair_match,
            "cached_executable_book_available": cached_available,
            "cached_book_used_for_decision": cached_used,
            "cache_reuse_reason": str(detail.get("orderbook_stale_reuse_source") or ""),
            "book_used_for_decision_source": book_used_source,
            "book_used_for_decision_token_pair_key": token_pair_key if book_used_source == "current_fetch" else "",
            "book_used_for_decision": book_used_for_decision,
            "book_used_token_pair_match": book_used_token_pair_match,
            "normalization_status": "accepted" if current_executable_yes_no_book else "not_executable",
            "yes_normalization_status": normalization_status_for(yes_fetch_status),
            "no_normalization_status": normalization_status_for(no_fetch_status),
            "serialized_truth_source": (
                "current_fetch_yes_no_top_of_book"
                if current_executable_yes_no_book
                else "unavailable_or_non_executable"
            ),
            "serialized_book_source": serialized_book_source,
            "serialized_yes_no_bid_ask_present": serialized_yes_no_bid_ask_present,
            "serialized_depth_present": bool(serialized_yes_no_bid_ask_present),
            "serialized_spread_present": bool(serialized_yes_no_bid_ask_present),
            "orderbook_readiness_reason": readiness,
            "orderbook_unavailable_reason": readiness,
            "liquidity_state": str(recovery_detail.get("liquidity_state") or ""),
            "terminal_blocker": terminal,
            "terminal_blocker_stage": terminal_stage_raw,
            "terminal_skip_reason": terminal or None,
            "terminal_gate_stage": terminal_gate_stage,
            "contextual_blockers": contextual,
            "empty_book_role": empty_book_role,
            "quote_age_ms": quote_age_ms,
            "quote_age_source": quote_age_source,
            "quote_age_truth_level": "current_fetch" if quote_age_source == "current_fetch_raw_timestamp" else "proxy" if quote_age_ms is not None else "unknown",
            "lifecycle_phase": str(lifecycle_phase or ""),
            "seconds_remaining": self._diagnostic_int(seconds_remaining),
            "lineage_confidence": "DIRECT" if token_pair_key else "UNKNOWN",
            "source_module": "polymarket.trader",
        }

    def _emit_orderbook_lineage_probe(self, **kwargs: object) -> bool:
        try:
            payload = self._build_orderbook_lineage_probe_payload(**kwargs)
            return bool(self._emit_quant_event("log_orderbook_lineage_probe", payload))
        except Exception as exc:
            LOGGER.debug("[OBSERVABILITY] orderbook lineage probe failed: %s", exc)
            return False

    def _finish_cycle_timing(self, *, reason: str, force: bool = False) -> None:
        self._last_scan_cycle_duration_ms = self._cycle_elapsed_ms()
        self._maybe_emit_system_health(force=force, reason=reason)

    def _emit_telegram_route_telemetry(self, event: dict[str, object]) -> None:
        try:
            self._emit_quant_event("log_system_health", dict(event))
        except Exception:
            LOGGER.debug("[OBSERVABILITY] telegram route telemetry emit failed", exc_info=True)

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
        # Keep next-window tokens ready before the active epoch opens. This is
        # discovery-only and does not alter entry cutoffs or strategy gates.
        return 300

    @staticmethod
    def _meta_int(meta: dict[str, object], key: str, default: int = 0) -> int:
        try:
            return int(float(meta.get(key, default) or default))
        except (TypeError, ValueError):
            return default

    def _phase2_safe_setting(self, key: str, default: object) -> object:
        try:
            return self._setting(key, default)
        except Exception:
            return default

    def _phase2_lifecycle_phase(self, seconds_remaining: object = None) -> str:
        seconds = self._diagnostic_int(seconds_remaining)
        if seconds is None or seconds <= 0:
            return "CLOSED_OR_UNSAFE"
        seconds_since_open = max(0, min(300, 300 - seconds))
        if seconds_since_open < 35:
            return "OPENING_SCAN"
        if seconds_since_open < 240:
            return "ACTIVE_INVENTORY_TRADING"
        if seconds_since_open < 270:
            return "PROFIT_MANAGEMENT"
        if seconds_since_open <= 300:
            return "FINAL_DERISK"
        return "CLOSED_OR_UNSAFE"

    @staticmethod
    def _phase2_candidate_hash(prefix: str, *parts: object) -> str:
        raw = "|".join(str(part or "") for part in parts)
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
        return f"{prefix}_{digest}"

    def _phase2_readiness_store(self) -> dict[tuple[str, int], dict[str, object]]:
        store = getattr(self, "_market_readiness_timestamps", None)
        if not isinstance(store, dict):
            store = {}
            self._market_readiness_timestamps = store
        return store

    def _phase2_readiness_timestamps(self, ticker: str, epoch_start: int) -> dict[str, object]:
        fields: dict[str, object] = {
            "token_ready_at": "",
            "token_ready_seconds_remaining": 0,
            "orderbook_ready_at": "",
            "orderbook_ready_seconds_remaining": 0,
            "liquidity_ready_at": "",
            "liquidity_ready_seconds_remaining": 0,
            "spread_ready_at": "",
            "spread_ready_seconds_remaining": 0,
            "first_tradable_at": "",
            "first_tradable_seconds_remaining": 0,
            "first_evaluable_at": "",
            "first_evaluable_ready_seconds_remaining": 0,
            # Market Readiness Timing Layer v1
            "first_discovered_ts": "",
            "first_discovered_seconds_remaining": 0,
            "first_token_ready_ts": "",
            "first_token_ready_seconds_remaining": 0,
            "first_orderbook_seen_ts": "",
            "first_orderbook_seen_seconds_remaining": 0,
            "first_nonzero_bidask_ts": "",
            "first_nonzero_bidask_seconds_remaining": 0,
            "first_spread_normalized_ts": "",
            "first_spread_normalized_seconds_remaining": 0,
            "first_tradable_ts": "",
            "first_tradable_seconds_remaining": 0,
            "readiness_confidence": 0.0,
            "executable_book_state": "UNKNOWN",
            "executable_book_state_best_seen": "UNKNOWN",
            "executable_spread_state": "UNKNOWN",
            # Liquidity Depth Observability v1
            "best_bid_size": 0.0,
            "best_ask_size": 0.0,
            "top_bid_depth": 0.0,
            "top_ask_depth": 0.0,
            "total_bid_depth_l1_l3": 0.0,
            "total_ask_depth_l1_l3": 0.0,
            "min_fillable_size_usd": 0.0,
            "liquidity_depth_state": "UNKNOWN",
            "liquidity_depth_confidence": 0.0,
            "time_to_min_depth_seconds": 0,
            "first_min_depth_ts": "",
            "first_min_depth_seconds_remaining": 0,
            "depth_oscillation_count": 0,
            "spread_oscillation_count": 0,
            "tradable_but_thin_count": 0,
        }
        if epoch_start <= 0:
            return fields
        stored = self._phase2_readiness_store().get((ticker.upper(), int(epoch_start)), {})
        for key in fields:
            if key in stored:
                fields[key] = stored[key]
        return fields

    def _compute_lifecycle_latency_ms(self, bucket: dict[str, object]) -> dict[str, object]:
        """
        Computes wall-clock ms durations between lifecycle milestone timestamps.
        Lifecycle Latency Observatory v1 — observability only, fail-soft.
        All fields default to 0 on any error or missing data.
        """
        _STAGES = (
            "DISCOVERY", "TOKEN_READY", "ORDERBOOK", "SPREAD_NORMALIZATION",
            "DECISION", "CUTOFF",
        )
        _ZERO: dict[str, object] = {
            "discovery_to_token_ready_ms": 0,
            "token_ready_to_book_ms": 0,
            "book_to_nonzero_ms": 0,
            "nonzero_to_normalized_ms": 0,
            "normalized_to_executable_ms": 0,
            "executable_to_decision_ms": 0,
            "total_discovery_to_decision_ms": 0,
            "dominant_latency_stage": "",
            "lifecycle_latency_classification": "",
        }
        try:
            from datetime import datetime as _dt

            def _parse(ts: object) -> _dt | None:
                s = str(ts or "").strip()
                if not s:
                    return None
                try:
                    return _dt.fromisoformat(s.replace("Z", "+00:00"))
                except Exception:
                    return None

            def _ms(a: _dt | None, b: _dt | None) -> int:
                if a is None or b is None or b <= a:
                    return 0
                return max(0, int((b - a).total_seconds() * 1000))

            t_disc = _parse(bucket.get("first_discovered_ts"))
            t_tok = _parse(bucket.get("first_token_ready_ts"))
            t_book = _parse(bucket.get("first_orderbook_seen_ts"))
            t_nonzero = _parse(bucket.get("first_nonzero_bidask_ts"))
            t_norm = _parse(bucket.get("first_spread_normalized_ts"))
            t_exec = _parse(bucket.get("first_tradable_ts"))
            t_dec = _parse(bucket.get("decision_complete_ts"))

            d_disc_tok = _ms(t_disc, t_tok)
            d_tok_book = _ms(t_tok, t_book)
            d_book_nonzero = _ms(t_book, t_nonzero)
            d_nonzero_norm = _ms(t_nonzero, t_norm)
            d_norm_exec = _ms(t_norm, t_exec)
            d_exec_dec = _ms(t_exec, t_dec)
            d_total = _ms(t_disc, t_dec)

            stage_durations = {
                "DISCOVERY": d_disc_tok,
                "TOKEN_READY": d_tok_book,
                "ORDERBOOK": d_book_nonzero,
                "SPREAD_NORMALIZATION": d_nonzero_norm,
                "DECISION": d_norm_exec,
                "CUTOFF": d_exec_dec,
            }
            dominant = max(stage_durations, key=lambda k: stage_durations[k]) if any(stage_durations.values()) else ""

            total = d_total or sum(stage_durations.values())
            if total >= 15000:
                classification = "CRITICAL"
            elif total >= 5000:
                classification = "SLOW"
            elif total >= 2000:
                classification = "NORMAL"
            elif total > 0:
                classification = "FAST"
            else:
                classification = ""

            return {
                "discovery_to_token_ready_ms": d_disc_tok,
                "token_ready_to_book_ms": d_tok_book,
                "book_to_nonzero_ms": d_book_nonzero,
                "nonzero_to_normalized_ms": d_nonzero_norm,
                "normalized_to_executable_ms": d_norm_exec,
                "executable_to_decision_ms": d_exec_dec,
                "total_discovery_to_decision_ms": d_total,
                "dominant_latency_stage": dominant,
                "lifecycle_latency_classification": classification,
            }
        except Exception:
            return dict(_ZERO)

    def _phase2_mark_readiness(
        self,
        *,
        ticker: str,
        epoch_start: int,
        epoch_end: int = 0,
        token_ready: bool = False,
        orderbook_ready: bool = False,
        nonzero_bidask: bool = False,
        liquidity_ready: bool = False,
        spread_ready: bool = False,
        first_evaluable_ready: bool = False,
        first_tradable_ready: bool = False,
        seconds_remaining: int | None = None,
        yes_ob: OrderbookSnapshot | None = None,
        no_ob: OrderbookSnapshot | None = None,
    ) -> dict[str, object]:
        ticker = ticker.upper()
        epoch_start = int(epoch_start or 0)
        if epoch_start <= 0:
            return self._phase2_readiness_timestamps(ticker, epoch_start)

        store = self._phase2_readiness_store()
        bucket = store.setdefault((ticker, epoch_start), {})
        now = self._utc_timestamp()
        seconds_value = self._diagnostic_int(seconds_remaining)

        # Clamp seconds_remaining to [0, epoch_length] to prevent impossible values
        # (e.g. preload detecting next epoch before it starts yields >300 raw values)
        _epoch_end_int = int(epoch_end or 0)
        _epoch_length = (
            max(300, _epoch_end_int - epoch_start)
            if _epoch_end_int > epoch_start
            else max(300, int(bucket.get("_epoch_length", 300)))
        )
        bucket["_epoch_length"] = _epoch_length
        if seconds_value is not None:
            seconds_value = max(0, min(seconds_value, _epoch_length))

        # Original fields (backwards compatibility)
        readiness_map = [
            (token_ready, "token_ready_at", "token_ready_seconds_remaining"),
            (orderbook_ready, "orderbook_ready_at", "orderbook_ready_seconds_remaining"),
            (liquidity_ready, "liquidity_ready_at", "liquidity_ready_seconds_remaining"),
            (spread_ready, "spread_ready_at", "spread_ready_seconds_remaining"),
            (first_evaluable_ready, "first_evaluable_at", "first_evaluable_ready_seconds_remaining"),
            (first_tradable_ready, "first_tradable_at", "first_tradable_seconds_remaining"),
        ]

        # New v1 fields
        readiness_map.extend([
            (True, "first_discovered_ts", "first_discovered_seconds_remaining"),
            (token_ready, "first_token_ready_ts", "first_token_ready_seconds_remaining"),
            (orderbook_ready, "first_orderbook_seen_ts", "first_orderbook_seen_seconds_remaining"),
            (nonzero_bidask, "first_nonzero_bidask_ts", "first_nonzero_bidask_seconds_remaining"),
            (spread_ready, "first_spread_normalized_ts", "first_spread_normalized_seconds_remaining"),
            (first_tradable_ready, "first_tradable_ts", "first_tradable_seconds_remaining"),
        ])

        # Lifecycle Early Snapshot Emission v1 — snapshot which milestone ts-fields are already written
        _EARLY_MILESTONE_MAP = [
            ("market_discovered",        "first_discovered_ts"),
            ("token_ready",              "first_token_ready_ts"),
            ("first_orderbook_seen",     "first_orderbook_seen_ts"),
            ("first_nonzero_book",       "first_nonzero_bidask_ts"),
            ("first_normalized_book",    "first_spread_normalized_ts"),
            ("first_executable_book",    "first_tradable_ts"),
            ("first_decision_evaluable", "first_evaluable_at"),
        ]
        _pre_milestone_written = frozenset(k for _, k in _EARLY_MILESTONE_MAP if bucket.get(k))

        for ready, key, seconds_key in readiness_map:
            if ready and not bucket.get(key):
                bucket[key] = now
            if ready and seconds_value is not None and not bucket.get(seconds_key):
                bucket[seconds_key] = seconds_value

        # Timing Metrics Calculation
        first_seen_rem = self._diagnostic_int(bucket.get("first_discovered_seconds_remaining")) or 0
        first_ob_rem = self._diagnostic_int(bucket.get("first_orderbook_seen_seconds_remaining")) or 0
        first_trad_rem = self._diagnostic_int(bucket.get("first_tradable_seconds_remaining")) or 0

        bucket["discovery_to_book_seconds"] = max(0, first_seen_rem - first_ob_rem) if first_ob_rem > 0 else 0
        bucket["book_to_tradable_seconds"] = max(0, first_ob_rem - first_trad_rem) if (first_ob_rem > 0 and first_trad_rem > 0) else 0
        bucket["total_discovery_to_tradable_seconds"] = max(0, first_seen_rem - first_trad_rem) if (first_seen_rem > 0 and first_trad_rem > 0) else 0

        # State transitions
        current_state = "DISCOVERED"
        if token_ready:
            current_state = "TOKEN_READY"
        if orderbook_ready:
            current_state = "BOOK_SEEN"
        if nonzero_bidask:
            current_state = "NONZERO_BOOK"
        if spread_ready:
            current_state = "SPREAD_NORMALIZED"
        if first_tradable_ready:
            current_state = "TRADABLE"

        # Fix C — Phase 2 Write-Path Monotonicity Guard.
        # Prevents Phase 1 TOKEN_READY downgrade of a previously SPREAD_NORMALIZED/TRADABLE
        # state when an early exit path (hard_block, FINAL_DERISK) skips Phase 2 correction.
        _STATE_LEVEL: dict[str, int] = {
            "DISCOVERED": 0, "TOKEN_READY": 1, "BOOK_SEEN": 2,
            "NONZERO_BOOK": 3, "SPREAD_NORMALIZED": 4, "TRADABLE": 5,
        }
        _prev_state = str(bucket.get("executable_book_state") or "DISCOVERED")
        if _STATE_LEVEL.get(current_state, 0) >= _STATE_LEVEL.get(_prev_state, 0):
            bucket["executable_book_state"] = current_state
        # Dual-State: best-seen advances monotonically (Fix B, observability only).
        _prev_best = str(bucket.get("executable_book_state_best_seen") or "DISCOVERED")
        if _STATE_LEVEL.get(current_state, 0) >= _STATE_LEVEL.get(_prev_best, 0):
            bucket["executable_book_state_best_seen"] = current_state
        bucket["executable_spread_state"] = "NORMALIZED" if spread_ready else "WIDE" if orderbook_ready else "UNKNOWN"

        # Spread oscillation tracking
        prev_spread_normalized = bucket.get("_prev_spread_normalized")
        if prev_spread_normalized is not None and prev_spread_normalized != spread_ready:
            bucket["spread_oscillation_count"] = int(bucket.get("spread_oscillation_count", 0)) + 1
        bucket["_prev_spread_normalized"] = spread_ready

        # Liquidity Depth Observability v1
        def _get_depth(ob: OrderbookSnapshot | None) -> tuple[float, float, float, float]:
            if ob is None or ob.raw_response is None:
                return 0.0, 0.0, 0.0, 0.0
            top_bids = ob.raw_response.get("top_bids", [])
            top_asks = ob.raw_response.get("top_asks", [])
            b_size = top_bids[0].get("size", 0.0) if top_bids else 0.0
            a_size = top_asks[0].get("size", 0.0) if top_asks else 0.0
            t_bid = sum(float(level.get("size", 0.0)) for level in top_bids)
            t_ask = sum(float(level.get("size", 0.0)) for level in top_asks)
            return b_size, a_size, t_bid, t_ask

        # Only update depth fields when a real orderbook is provided.
        # Without this guard, calls from _decision_diagnostics_payload (no yes_ob/no_ob)
        # would overwrite depth to 0.0, erasing the real values written by the main cycle.
        if yes_ob is not None or no_ob is not None:
            b_size, a_size, t_bid, t_ask = _get_depth(yes_ob)
            if no_ob:
                nb_size, na_size, nt_bid, nt_ask = _get_depth(no_ob)
                b_size, a_size = min(b_size, nb_size), min(a_size, na_size)
                t_bid, t_ask = min(t_bid, nt_bid), min(t_ask, nt_ask)

            bucket["best_bid_size"] = float(b_size)
            bucket["best_ask_size"] = float(a_size)
            bucket["top_bid_depth"] = float(b_size)
            bucket["top_ask_depth"] = float(a_size)
            bucket["total_bid_depth_l1_l3"] = float(t_bid)
            bucket["total_ask_depth_l1_l3"] = float(t_ask)

            min_depth_shares = min(t_bid, t_ask)
            min_fillable_usd = min_depth_shares * 0.5  # conservative estimate
            bucket["min_fillable_size_usd"] = float(min_fillable_usd)

            depth_state = "UNKNOWN"
            depth_conf = 0.0
            if min_fillable_usd <= 0:
                depth_state = "EMPTY"
            elif min_fillable_usd < 100.0:
                depth_state = "THIN"
                depth_conf = 0.2
            elif min_fillable_usd < 500.0:
                depth_state = "ACCEPTABLE"
                depth_conf = 0.6
            else:
                depth_state = "STRONG"
                depth_conf = 1.0

            prev_depth_state = bucket.get("liquidity_depth_state", "UNKNOWN")
            if prev_depth_state != "UNKNOWN" and prev_depth_state != depth_state:
                bucket["depth_oscillation_count"] = int(bucket.get("depth_oscillation_count", 0)) + 1
                if depth_state == "THIN" and prev_depth_state in {"ACCEPTABLE", "STRONG"}:
                    depth_state = "UNSTABLE"

            bucket["liquidity_depth_state"] = depth_state
            bucket["liquidity_depth_confidence"] = depth_conf

            if current_state == "TRADABLE" and depth_state in {"THIN", "EMPTY"}:
                bucket["tradable_but_thin_count"] = int(bucket.get("tradable_but_thin_count", 0)) + 1

            min_depth_threshold = float(self._phase2_safe_setting("liquidity_min_depth_usd_threshold", 250.0))
            if min_fillable_usd >= min_depth_threshold and not bucket.get("first_min_depth_ts"):
                bucket["first_min_depth_ts"] = now
                bucket["first_min_depth_seconds_remaining"] = seconds_value or 0
                bucket["time_to_min_depth_seconds"] = max(0, first_seen_rem - bucket["first_min_depth_seconds_remaining"])
        else:
            # No orderbook provided — preserve existing depth state from bucket.
            depth_state = str(bucket.get("liquidity_depth_state", "UNKNOWN"))
            depth_conf = float(bucket.get("liquidity_depth_confidence", 0.0))

        # Confidence heuristic (extended)
        confidence = 0.0
        if token_ready: confidence += 0.2
        if orderbook_ready: confidence += 0.2
        if nonzero_bidask: confidence += 0.2
        if spread_ready: confidence += 0.2
        if liquidity_ready and depth_state not in {"EMPTY", "THIN", "UNKNOWN"}: confidence += 0.2
        bucket["readiness_confidence"] = round(confidence, 2)

        # Lifecycle Early Snapshot Emission v1 — emit once per newly-reached milestone (fail-soft)
        try:
            for _milestone_name, _ts_key in _EARLY_MILESTONE_MAP:
                if bucket.get(_ts_key) and _ts_key not in _pre_milestone_written:
                    self._emit_lifecycle_milestone_event(
                        ticker=ticker,
                        epoch_start=epoch_start,
                        milestone=_milestone_name,
                        bucket=bucket,
                        seconds_remaining=seconds_value,
                    )
        except Exception:
            pass

        return self._phase2_readiness_timestamps(ticker, epoch_start)

    def _emit_lifecycle_milestone_event(
        self,
        ticker: str,
        epoch_start: int,
        milestone: str,
        bucket: dict[str, object],
        seconds_remaining: int | None,
    ) -> None:
        """
        Emit a compact observability event when a lifecycle milestone is first reached.
        Lifecycle Early Snapshot Emission v1 — observability-only, fail-soft.
        Fires at most once per (ticker, epoch, milestone). Does not affect strategy, risk, or execution.
        """
        try:
            if not getattr(self.settings, "hybrid_phase_v1_enabled", False):
                return
            _latency = self._compute_lifecycle_latency_ms(bucket)
            _epoch_length = int(bucket.get("_epoch_length", 300))
            _sec_rem = seconds_remaining if seconds_remaining is not None else 0
            _seconds_since_open = max(0, _epoch_length - _sec_rem)
            payload: dict[str, object] = {
                "event_subtype": "lifecycle_milestone",
                "ticker": ticker.upper(),
                "market_epoch_start": epoch_start,
                "lifecycle_phase": milestone,
                "seconds_since_market_open": _seconds_since_open,
                "seconds_remaining": _sec_rem,
                "readiness_state": str(bucket.get("executable_book_state", "UNKNOWN")),
                "dominant_latency_stage_so_far": _latency.get("dominant_latency_stage", ""),
                "lifecycle_latency_classification_so_far": _latency.get("lifecycle_latency_classification", ""),
                "readiness_confidence": float(bucket.get("readiness_confidence", 0.0)),
                "first_discovered_ts": str(bucket.get("first_discovered_ts", "") or ""),
                "milestone_ts": self._utc_timestamp(),
            }
            self._emit_quant_event("log_research_snapshot", payload)
        except Exception:
            pass

    def _phase2_exposure_timeline(
        self,
        market_id: str,
        *,
        risk_plan: RiskPlan | None = None,
        exposure_after: float | None = None,
    ) -> dict[str, float]:
        try:
            current_market_exposure = sum(
                float(getattr(pos, "notional_size", 0.0) or 0.0)
                for pos in self._open_positions_for_market(market_id)
            )
        except Exception:
            current_market_exposure = 0.0
        state = getattr(self, "bankroll_state", None)
        current_balance = float(getattr(state, "current_bankroll_for_sizing", 0.0) or 0.0)
        open_exposure = float(getattr(state, "open_position_market_value", current_market_exposure) or 0.0)
        try:
            tier_config = get_tier_config(getattr(state, "current_bankroll_tier", "T0_MICRO_SEED"))
            configured_cap = float(self._phase2_safe_setting("max_risk_per_market", tier_config.max_market_exposure_pct))
            max_risk_per_market = min(configured_cap, float(tier_config.max_market_exposure_pct))
        except Exception:
            max_risk_per_market = 0.0
        market_budget = max(current_balance * max(max_risk_per_market, 0.0), 0.0)
        if exposure_after is None:
            exposure_after = current_market_exposure
            if risk_plan is not None:
                exposure_after += float(getattr(risk_plan, "notional_size", 0.0) or 0.0)
        return {
            "exposure_before": float(current_market_exposure),
            "exposure_after": float(max(exposure_after, 0.0)),
            "risk_budget_used": float(current_market_exposure),
            "remaining_risk_budget": float(max(market_budget - current_market_exposure, 0.0)),
            "current_exposure": float(open_exposure),
            "target_exposure": float(max(exposure_after, 0.0)),
        }

    @staticmethod
    def _phase2_value_available(value: object) -> bool:
        return value is not None and value != ""

    def _phase2_ev_null_reason(
        self,
        *,
        field_name: str,
        skip_reason: object = "",
        orderbook_readiness_reason: object = "",
        liquidity_state: object = "",
        spread_normalized: object = None,
        probability_available: bool = False,
        market_price_available: bool = False,
        ev_available: bool = False,
    ) -> str:
        reason = str(skip_reason or "").lower()
        orderbook_reason = str(orderbook_readiness_reason or "").lower()
        liquidity = str(liquidity_state or "").upper()
        if "empty_book" in orderbook_reason or "empty_book" in reason:
            return "empty_book"
        if orderbook_reason or "orderbook" in reason or "warmup" in reason:
            return "no_orderbook"
        if "time_unsafe" in reason or "cutoff" in reason:
            return "time_unsafe"
        if liquidity and liquidity not in {"HEALTHY", "UNKNOWN"}:
            return "liquidity_not_ready"
        if spread_normalized is False or "spread" in reason:
            return "spread_not_ready"
        if "risk" in reason or "balance" in reason or "drawdown" in reason or "lockdown" in reason:
            return "risk_blocked_after_ev" if ev_available or probability_available else "candidate_blocked_before_ev"
        if field_name == "market_price":
            return "no_market_price"
        if field_name == "ev_after_spread":
            if not probability_available:
                return "no_probability_model_output"
            if not market_price_available:
                return "no_market_price"
            return "candidate_blocked_before_ev"
        if field_name in {"fair_value", "true_probability"}:
            return "no_probability_model_output"
        return "candidate_blocked_before_ev"

    def _phase2_pre_model_gate_detail(
        self,
        *,
        skip_reason: object = "",
        orderbook_readiness_reason: object = "",
        liquidity_state: object = "",
        spread_normalized: object = None,
        readiness_state: object = "",
        lifecycle_phase: object = "",
        probability_available: bool = False,
    ) -> dict[str, object]:
        if probability_available:
            return {
                "pre_model_gate_name": "MODEL_OUTPUT_AVAILABLE",
                "pre_model_gate_group": "MODEL_READY",
                "pre_model_gate_reason": "model_output_visible",
                "pre_model_gate_source": "probability_output",
                "pre_model_gate_blocks_probability_model": False,
                "probability_model_call_path": "probability_model_output_serialized",
            }

        reason_text = str(skip_reason or "").strip()
        orderbook_text = str(orderbook_readiness_reason or "").strip()
        readiness_text = str(readiness_state or "").strip()
        liquidity_text = str(liquidity_state or "").strip()
        lifecycle_text = str(lifecycle_phase or "").strip().upper()
        combined = " ".join(
            part.lower()
            for part in (reason_text, orderbook_text, readiness_text, liquidity_text, lifecycle_text)
            if part
        )

        gate_name = "MODEL_GATE_UNKNOWN"
        gate_group = "MODEL_GATE_UNKNOWN"
        source = "unclassified"
        if any(token in combined for token in ("hard_close", "time_unsafe", "cutoff", "entry timing", "late_hard_close_zone")):
            gate_name = "TIME_CUTOFF_GATE"
            gate_group = "TIME_CUTOFF_GATE"
            source = "time_or_cutoff"
        elif lifecycle_text in {"FINAL_DERISK", "CLOSED_OR_UNSAFE"}:
            gate_name = "LIFECYCLE_PHASE_GATE"
            gate_group = "LIFECYCLE_PHASE_GATE"
            source = "lifecycle_phase"
        elif any(token in combined for token in ("stale_feed", "feed", "oracle", "data_stale")):
            gate_name = "DATA_FRESHNESS_GATE"
            gate_group = "DATA_FRESHNESS_GATE"
            source = "market_data_freshness"
        elif any(token in combined for token in ("token_mapping", "missing_token", "token_not_ready", "api_missing_fields", "missing token")):
            gate_name = "TOKEN_MAPPING_GATE"
            gate_group = "ORDERBOOK_GATE"
            source = "token_mapping"
        elif any(token in combined for token in ("orderbook", "empty_book", "warmup", "clob_", "bid/ask", "no_orderbook", "unavailable")):
            gate_name = "ORDERBOOK_COMPLETENESS_GATE"
            gate_group = "ORDERBOOK_GATE"
            source = "orderbook_readiness"
        elif spread_normalized is False or "spread" in combined:
            gate_name = "SPREAD_GATE"
            gate_group = "SPREAD_GATE"
            source = "spread_readiness"
        elif liquidity_text.upper() not in {"", "HEALTHY", "READY", "UNKNOWN"} or "liquidity" in combined or "min shares" in combined:
            gate_name = "LIQUIDITY_GATE"
            gate_group = "LIQUIDITY_GATE"
            source = "liquidity_readiness"
        elif any(token in combined for token in ("max entries", "max 1", "frequency", "cooldown")):
            gate_name = "ENTRY_FREQUENCY_GATE"
            gate_group = "ENTRY_FREQUENCY_GATE"
            source = "entry_frequency"
        elif any(token in combined for token in ("max active", "max position", "position limit")):
            gate_name = "ENTRY_CAPACITY_GATE"
            gate_group = "ENTRY_CAPACITY_GATE"
            source = "entry_capacity"
        elif any(token in combined for token in ("panic sell", "panic_sold")):
            gate_name = "PANIC_COOLDOWN_GATE"
            gate_group = "RUNTIME_SAFETY_GATE"
            source = "panic_cooldown"
        elif "risk_plan_zero" in combined or "zero position" in combined:
            gate_name = "MODEL_GATE_UNKNOWN"
            gate_group = "MODEL_GATE_UNKNOWN"
            source = "post_model_risk_plan_or_unknown"
        elif any(token in combined for token in ("risk", "floor", "balance", "drawdown", "lockdown", "reconciliation")):
            gate_name = "RISK_SAFETY_GATE"
            gate_group = "RUNTIME_SAFETY_GATE"
            source = "runtime_safety"

        reason = orderbook_text or reason_text or readiness_text or liquidity_text or "model_gate_unknown"
        return {
            "pre_model_gate_name": gate_name,
            "pre_model_gate_group": gate_group,
            "pre_model_gate_reason": reason,
            "pre_model_gate_source": source,
            "pre_model_gate_blocks_probability_model": gate_name != "MODEL_GATE_UNKNOWN",
            "probability_model_call_path": (
                "blocked_before_probability_model"
                if gate_name != "MODEL_GATE_UNKNOWN"
                else "probability_model_call_path_unknown"
            ),
        }

    def _phase2_ev_null_reason_detail(
        self,
        *,
        fair_value: object,
        market_price: object,
        true_probability: object,
        ev_after_spread: object,
        skip_reason: object = "",
        orderbook_readiness_reason: object = "",
        liquidity_state: object = "",
        spread_normalized: object = None,
    ) -> dict[str, object]:
        fair_value_available = self._phase2_value_available(fair_value)
        market_price_available = self._phase2_value_available(market_price)
        true_probability_available = self._phase2_value_available(true_probability)
        ev_after_spread_available = self._phase2_value_available(ev_after_spread)
        probability_available = fair_value_available or true_probability_available

        skip_text = str(skip_reason or "").lower()
        orderbook_text = str(orderbook_readiness_reason or "").lower()
        pre_model_block = (
            "time_unsafe" in skip_text
            or "cutoff" in skip_text
            or "orderbook" in skip_text
            or "warmup" in skip_text
            or "empty_book" in skip_text
            or bool(orderbook_text)
        )
        if probability_available:
            probability_model_stage = "probability_model_output"
        elif pre_model_block:
            probability_model_stage = "pre_model_skip"
        else:
            probability_model_stage = "no_probability_model_output"

        if ev_after_spread_available:
            ev_calculation_stage = "ev_calculated"
        elif probability_model_stage == "pre_model_skip":
            ev_calculation_stage = "pre_model_skip"
        elif probability_available and not market_price_available:
            ev_calculation_stage = "no_market_price"
        else:
            ev_calculation_stage = "candidate_blocked_before_ev"

        gate_reason = ""
        if probability_available:
            gate_reason = "model_output_visible"
        elif pre_model_block:
            gate_reason = str(orderbook_readiness_reason or skip_reason or "pre_model_gate").strip()
        else:
            gate_reason = "model_output_not_visible"

        gate_detail = self._phase2_pre_model_gate_detail(
            skip_reason=skip_reason,
            orderbook_readiness_reason=orderbook_readiness_reason,
            liquidity_state=liquidity_state,
            spread_normalized=spread_normalized,
            probability_available=probability_available,
        )
        known_pre_model_gate = str(gate_detail.get("pre_model_gate_name") or "") not in {
            "",
            "MODEL_GATE_UNKNOWN",
            "MODEL_OUTPUT_AVAILABLE",
        }
        if not probability_available and known_pre_model_gate:
            probability_model_stage = "pre_model_skip"
            if not ev_after_spread_available:
                ev_calculation_stage = "pre_model_skip"
            gate_reason = str(gate_detail.get("pre_model_gate_reason") or gate_reason)
        detail: dict[str, object] = {
            "fair_value_available": fair_value_available,
            "fair_value_null_reason": "",
            "market_price_available": market_price_available,
            "market_price_null_reason": "",
            "true_probability_available": true_probability_available,
            "true_probability_null_reason": "",
            "ev_after_spread_available": ev_after_spread_available,
            "ev_after_spread_null_reason": "",
            "probability_model_stage": probability_model_stage,
            "ev_calculation_stage": ev_calculation_stage,
            "model_attempted": bool(probability_available),
            "probability_model_gate_reason": gate_reason,
            "model_not_run_reason": "" if probability_available else gate_reason,
            "probability_model_called": bool(probability_available),
            "probability_model_output_visible": bool(probability_available),
            "model_output_missing_reason": "" if probability_available else gate_reason,
            "model_output_source": "canonical_probability_fields" if probability_available else "",
            "model_handoff_stage": (
                "MODEL_OUTPUT_SERIALIZED"
                if probability_available
                else "PRE_MODEL_GATE" if pre_model_block or known_pre_model_gate else "MODEL_OUTPUT_NOT_VISIBLE"
            ),
            **gate_detail,
        }
        for field_name, value, available in (
            ("fair_value", fair_value, fair_value_available),
            ("market_price", market_price, market_price_available),
            ("true_probability", true_probability, true_probability_available),
            ("ev_after_spread", ev_after_spread, ev_after_spread_available),
        ):
            if available:
                continue
            detail[f"{field_name}_null_reason"] = self._phase2_ev_null_reason(
                field_name=field_name,
                skip_reason=skip_reason,
                orderbook_readiness_reason=orderbook_readiness_reason,
                liquidity_state=liquidity_state,
                spread_normalized=spread_normalized,
                probability_available=probability_available,
                market_price_available=market_price_available,
                ev_available=ev_after_spread_available,
            )
        return detail

    @staticmethod
    def _phase2_iso_from_epoch(epoch_start: int, offset_seconds: int) -> str:
        if epoch_start <= 0:
            return ""
        try:
            return datetime.fromtimestamp(epoch_start + offset_seconds, UTC).isoformat().replace("+00:00", "Z")
        except (OSError, OverflowError, ValueError):
            return ""

    @staticmethod
    def _phase2_phase_offsets(lifecycle_phase: str) -> tuple[int, int | None]:
        phase = str(lifecycle_phase or "").upper()
        if phase == "OPENING_SCAN":
            return 0, 35
        if phase == "ACTIVE_INVENTORY_TRADING":
            return 35, 240
        if phase == "PROFIT_MANAGEMENT":
            return 240, 270
        if phase == "FINAL_DERISK":
            return 270, 300
        if phase == "CLOSED_OR_UNSAFE":
            return 300, None
        return 0, None

    def _phase2_orderbook_state_classification(self, payload: dict[str, object]) -> str:
        authoritative_available, _source = self._phase2_authoritative_orderbook_availability(payload)
        reason = str(
            payload.get("orderbook_readiness_reason")
            or payload.get("orderbook_unavailable_reason")
            or payload.get("orderbook_error")
            or ""
        ).lower()
        liquidity = str(payload.get("liquidity_state") or "").upper()
        if "token_mapping" in reason or "token" in reason:
            return "token_mapping_unavailable"
        if "empty_book" in reason or "empty_orderbook" in reason or liquidity == "EMPTY":
            return "empty_book"
        if "warmup" in reason:
            return "warmup_pending"
        if "stale" in reason:
            return "stale_orderbook"
        if reason and authoritative_available and any(
            token in reason
            for token in ("orderbook", "unavailable", "bid/ask", "no_orderbook")
        ):
            return "ready"
        if reason:
            return "orderbook_unavailable"

        yes_bid = self._diagnostic_float(payload.get("yes_bid"))
        yes_ask = self._diagnostic_float(payload.get("yes_ask"))
        no_bid = self._diagnostic_float(payload.get("no_bid"))
        no_ask = self._diagnostic_float(payload.get("no_ask"))
        bid = self._diagnostic_float(payload.get("best_bid") or payload.get("bid"))
        ask = self._diagnostic_float(payload.get("best_ask") or payload.get("ask"))
        if (yes_bid > 0 and yes_ask > 0 and no_bid > 0 and no_ask > 0) or (bid > 0 and ask > 0):
            return "ready"
        if any(value is not None for value in (payload.get("yes_bid"), payload.get("yes_ask"), payload.get("no_bid"), payload.get("no_ask"))):
            return "empty_book"
        if authoritative_available:
            return "ready"
        return "unavailable"

    @staticmethod
    def _phase2_book_state_level(state: object) -> int:
        levels = {
            "DISCOVERED": 0,
            "UNKNOWN": 0,
            "TOKEN_READY": 1,
            "BOOK_SEEN": 2,
            "NONZERO_BOOK": 3,
            "SPREAD_NORMALIZED": 4,
            "EXECUTABLE": 5,
            "TRADABLE": 5,
        }
        return levels.get(str(state or "").upper().strip(), -1)

    def _phase2_authoritative_orderbook_availability(
        self,
        payload: dict[str, object],
    ) -> tuple[bool, str]:
        """Return whether decision diagnostics have non-serialized book authority."""
        yes_bid = self._diagnostic_float(payload.get("yes_bid"))
        yes_ask = self._diagnostic_float(payload.get("yes_ask"))
        no_bid = self._diagnostic_float(payload.get("no_bid"))
        no_ask = self._diagnostic_float(payload.get("no_ask"))
        bid = self._diagnostic_float(payload.get("best_bid") or payload.get("bid"))
        ask = self._diagnostic_float(payload.get("best_ask") or payload.get("ask"))
        if yes_bid > 0 and yes_ask > 0 and no_bid > 0 and no_ask > 0:
            return True, "serialized_yes_no_bid_ask"
        if bid > 0 and ask > 0:
            return True, "serialized_best_bid_ask"

        current_fetch_status = str(payload.get("orderbook_current_fetch_status") or "").strip()
        if current_fetch_status == "fresh_fetch_executable":
            return True, "current_fetch_status_fresh_fetch_executable"

        for key, label in (
            ("executable_book_state", "readiness_bucket_current"),
            ("executable_book_state_best_seen", "readiness_bucket_best_seen"),
        ):
            level = self._phase2_book_state_level(payload.get(key))
            if level >= 5:
                return True, f"{label}_tradable"
            if level >= 4:
                return True, f"{label}_spread_normalized"
            if level >= 3:
                return True, f"{label}_nonzero_book"

        for key, label in (
            ("first_tradable_ts", "readiness_first_tradable_ts"),
            ("first_spread_normalized_ts", "readiness_first_spread_normalized_ts"),
            ("first_nonzero_bidask_ts", "readiness_first_nonzero_bidask_ts"),
        ):
            if str(payload.get(key) or "").strip():
                return True, label

        if (
            bool(payload.get("orderbook_lineage_match"))
            and str(payload.get("last_successful_yes_no_book_token_pair_key") or "").strip()
            and str(payload.get("decision_token_pair_key") or "").strip()
        ):
            return True, "prior_successful_same_token_pair"
        return False, ""

    def _phase2_market_readiness_state(self, payload: dict[str, object], orderbook_state: str) -> str:
        reason = str(payload.get("active_window_alignment_reason") or "").lower()
        if reason in {"before_active_window", "late_hard_close_zone"}:
            return reason
        seconds = self._diagnostic_int(payload.get("seconds_remaining") or payload.get("seconds_until_close"))
        try:
            hard_block = self._entry_hard_block_seconds()
        except Exception:
            hard_block = 0
        if seconds is not None and seconds <= hard_block:
            return "time_unsafe"

        token_ready = bool(payload.get("token_id") or payload.get("yes_token_id") or payload.get("no_token_id") or payload.get("token_ready_at"))
        if not token_ready:
            return "token_not_ready"
        if orderbook_state != "ready":
            return orderbook_state

        liquidity = str(payload.get("liquidity_state") or "").upper()
        if liquidity and liquidity not in {"HEALTHY", "READY", "UNKNOWN"}:
            return "liquidity_not_ready"
        spread_ready = payload.get("spread_normalized")
        if spread_ready is False:
            return "spread_not_ready"
        return "ready"

    def _phase2_model_activation_detail(
        self,
        payload: dict[str, object],
        *,
        lifecycle_phase: str,
        orderbook_state: str,
        readiness_state: str,
        model_output_ready: bool | None,
    ) -> dict[str, object]:
        producer = str(payload.get("producer_event_type") or payload.get("producer") or "").strip()
        probability_stage = str(payload.get("probability_model_stage") or "").lower()
        gate_reason = str(
            payload.get("probability_model_gate_reason")
            or payload.get("model_not_run_reason")
            or payload.get("active_window_alignment_reason")
            or payload.get("adaptive_cutoff_reason")
            or payload.get("orderbook_readiness_reason")
            or readiness_state
            or ""
        )
        orderbook_available_for_decision = bool(payload.get("orderbook_available_for_decision"))
        orderbook_reason_text = str(
            payload.get("orderbook_readiness_reason")
            or payload.get("orderbook_unavailable_reason")
            or ""
        ).lower()
        generic_orderbook_unavailable = (
            orderbook_available_for_decision
            and any(token in orderbook_reason_text for token in ("orderbook", "unavailable", "bid/ask", "no_orderbook"))
            and not any(token in orderbook_reason_text for token in ("token", "empty", "warmup", "stale"))
        )
        effective_orderbook_reason = "" if generic_orderbook_unavailable else (
            payload.get("orderbook_readiness_reason") or payload.get("orderbook_unavailable_reason") or ""
        )
        if generic_orderbook_unavailable and any(
            token in gate_reason.lower() for token in ("orderbook", "unavailable", "bid/ask", "no_orderbook")
        ):
            gate_reason = str(payload.get("adaptive_cutoff_reason") or readiness_state or "model_output_not_visible")
        seconds_remaining = self._diagnostic_int(payload.get("seconds_remaining") or payload.get("seconds_until_close"))
        try:
            hard_block_seconds = self._entry_hard_block_seconds()
        except Exception:
            hard_block_seconds = 0
        effective_cutoff = self._diagnostic_int(payload.get("effective_cutoff_seconds") or payload.get("entry_cutoff_seconds"))
        pre_model_gate = self._phase2_pre_model_gate_detail(
            skip_reason=gate_reason,
            orderbook_readiness_reason=effective_orderbook_reason,
            liquidity_state=payload.get("liquidity_state") or "",
            spread_normalized=payload.get("spread_normalized"),
            readiness_state=readiness_state,
            lifecycle_phase=lifecycle_phase,
            probability_available=model_output_ready is True,
        )
        existing_gate_name = str(payload.get("pre_model_gate_name") or "").strip()
        if existing_gate_name and existing_gate_name != "MODEL_GATE_UNKNOWN":
            pre_model_gate["pre_model_gate_name"] = existing_gate_name
            pre_model_gate["pre_model_gate_group"] = str(
                payload.get("pre_model_gate_group") or pre_model_gate["pre_model_gate_group"]
            )
            pre_model_gate["pre_model_gate_reason"] = str(
                payload.get("pre_model_gate_reason") or gate_reason or pre_model_gate["pre_model_gate_reason"]
            )
            pre_model_gate["pre_model_gate_source"] = str(
                payload.get("pre_model_gate_source") or pre_model_gate["pre_model_gate_source"]
            )
            pre_model_gate["pre_model_gate_blocks_probability_model"] = bool(
                payload.get("pre_model_gate_blocks_probability_model", True)
            )
            pre_model_gate["probability_model_call_path"] = str(
                payload.get("probability_model_call_path") or pre_model_gate["probability_model_call_path"]
            )
        explicit_gate_group = str(pre_model_gate.get("pre_model_gate_group") or "")
        explicit_gate_name = str(pre_model_gate.get("pre_model_gate_name") or "")

        if model_output_ready is True:
            state = "MODEL_OUTPUT_VISIBLE"
            group = "MODEL_READY"
            reason = "model_output_visible"
            eligible = True
        elif producer == "market_snapshots":
            state = "PRE_MODEL_OBSERVATION"
            group = "PRODUCER_NOT_RESPONSIBLE"
            reason = gate_reason or "market_snapshot_pre_model_observation"
            pre_model_gate["pre_model_gate_name"] = "PRODUCER_PRE_MODEL_OBSERVATION"
            pre_model_gate["pre_model_gate_group"] = "PRODUCER_NOT_RESPONSIBLE"
            pre_model_gate["pre_model_gate_reason"] = reason
            pre_model_gate["pre_model_gate_source"] = "producer_role"
            pre_model_gate["pre_model_gate_blocks_probability_model"] = False
            pre_model_gate["probability_model_call_path"] = "producer_not_responsible_pre_model_observation"
            eligible = False
        elif explicit_gate_group and explicit_gate_group not in {"MODEL_GATE_UNKNOWN", "MODEL_READY"}:
            state = "BLOCKED_BEFORE_MODEL"
            group = explicit_gate_group
            reason = str(
                payload.get("adaptive_cutoff_reason")
                if explicit_gate_group == "TIME_CUTOFF_GATE" and payload.get("adaptive_cutoff_reason")
                else pre_model_gate.get("pre_model_gate_reason") or explicit_gate_name or gate_reason
            )
            eligible = False
        elif readiness_state == "time_unsafe" or "cutoff" in gate_reason.lower() or "hard_close" in gate_reason.lower():
            state = "BLOCKED_BEFORE_MODEL"
            group = "TIME_CUTOFF_GATE"
            reason = (
                str(payload.get("adaptive_cutoff_reason") or "").strip()
                if gate_reason.lower() in {"", "time_unsafe", "pre_model_gate"}
                else gate_reason
            ) or readiness_state
            eligible = False
        elif readiness_state in {"token_not_ready", "orderbook_unavailable", "empty_book", "warmup_pending", "stale_orderbook"} or orderbook_state != "ready":
            state = "BLOCKED_BEFORE_MODEL"
            group = "ORDERBOOK_GATE"
            reason = gate_reason or readiness_state or orderbook_state
            eligible = False
        elif readiness_state == "liquidity_not_ready":
            state = "BLOCKED_BEFORE_MODEL"
            group = "LIQUIDITY_GATE"
            reason = gate_reason or readiness_state
            eligible = False
        elif readiness_state == "spread_not_ready":
            state = "BLOCKED_BEFORE_MODEL"
            group = "SPREAD_GATE"
            reason = gate_reason or readiness_state
            eligible = False
        elif str(lifecycle_phase).upper() in {"FINAL_DERISK", "CLOSED_OR_UNSAFE"}:
            state = "BLOCKED_BEFORE_MODEL"
            group = "LIFECYCLE_PHASE_GATE"
            reason = gate_reason or lifecycle_phase
            eligible = False
        elif probability_stage == "pre_model_skip":
            state = "BLOCKED_BEFORE_MODEL"
            group = "MODEL_GATE_UNKNOWN"
            reason = gate_reason or "pre_model_skip"
            eligible = False
        elif probability_stage == "no_probability_model_output":
            state = "MODEL_OUTPUT_NOT_VISIBLE"
            group = "MODEL_GATE_UNKNOWN"
            reason = gate_reason or "model_output_not_visible"
            eligible = False
        else:
            state = "MODEL_ELIGIBILITY_UNKNOWN"
            group = "MODEL_GATE_UNKNOWN"
            reason = gate_reason or "model_gate_unknown"
            eligible = False

        lifecycle_second = self._phase2_elapsed_second(seconds_remaining)
        return {
            "model_activation_state": state,
            "model_activation_block_group": group,
            "model_activation_block_reason": reason,
            "model_attempt_eligible": bool(eligible),
            "model_activation_seconds_remaining": seconds_remaining,
            "model_activation_effective_cutoff_seconds": effective_cutoff,
            "model_activation_hard_block_seconds": hard_block_seconds,
            "model_activation_lifecycle_phase": lifecycle_phase,
            "model_activation_orderbook_state": orderbook_state,
            "model_activation_market_readiness_state": readiness_state,
            "first_model_eligible_second": lifecycle_second if eligible else None,
            "seconds_remaining_when_eligible": seconds_remaining if eligible else None,
            "first_probability_output_second": lifecycle_second if model_output_ready is True else None,
            "seconds_remaining_when_model_output_visible": seconds_remaining if model_output_ready is True else None,
            "model_eligible_at_or_inside_cutoff": bool(
                eligible
                and seconds_remaining is not None
                and effective_cutoff is not None
                and seconds_remaining <= effective_cutoff
            ),
            **pre_model_gate,
        }

    def _phase2_candidate_block_detail(self, payload: dict[str, object]) -> tuple[str, str, str]:
        reason = str(
            payload.get("normalized_skip_reason")
            or payload.get("skip_reason")
            or payload.get("raw_skip_reason")
            or payload.get("orderbook_readiness_reason")
            or payload.get("orderbook_unavailable_reason")
            or payload.get("ev_after_spread_null_reason")
            or payload.get("fair_value_null_reason")
            or ""
        ).strip()
        skipped = bool(payload.get("skipped")) or str(payload.get("decision") or "").lower() in {"skip", "skipped"}
        ev_available = bool(payload.get("ev_after_spread_available")) or self._phase2_value_available(payload.get("ev_after_spread"))
        model_output_ready = bool(payload.get("true_probability_available")) or bool(payload.get("fair_value_available"))
        probability_stage = str(payload.get("probability_model_stage") or "").lower()
        ev_stage = str(payload.get("ev_calculation_stage") or "").lower()

        if not reason and not skipped:
            return "not_blocked", "not_blocked", "candidate_active_or_approved"
        if not reason:
            reason = "unavailable"

        if "pre_model_skip" in probability_stage or "candidate_blocked_before_ev" in ev_stage:
            stage = "pre_ev"
        elif "risk_blocked_after_ev" in ev_stage or (skipped and (ev_available or model_output_ready)):
            stage = "post_ev"
        elif skipped:
            stage = "pre_ev"
        else:
            stage = "unavailable"

        reason_lower = reason.lower()
        if any(token in reason_lower for token in ("time_unsafe", "cutoff", "hard_close", "too_late")):
            expiry = "time_unsafe"
        elif any(token in reason_lower for token in ("orderbook", "empty_book", "warmup", "liquidity", "spread", "token")):
            expiry = "market_not_ready"
        elif "risk" in reason_lower or "balance" in reason_lower or "drawdown" in reason_lower or "lockdown" in reason_lower:
            expiry = "risk_block"
        elif reason == "unavailable":
            expiry = "unavailable"
        else:
            expiry = "blocked"
        return reason, stage, expiry

    def _phase2_candidate_survival_ms(self, payload: dict[str, object]) -> int | None:
        first_seen = self._diagnostic_int(payload.get("first_seen_seconds_remaining"))
        remaining = self._diagnostic_int(payload.get("seconds_remaining") or payload.get("seconds_until_close"))
        if first_seen is None or remaining is None:
            return None
        return int(max(0, first_seen - remaining) * 1000)

    def _phase2_elapsed_second(self, seconds_remaining: object) -> int | None:
        remaining = self._diagnostic_int(seconds_remaining)
        if remaining is None:
            return None
        return int(max(0, min(300, 300 - remaining)))

    def _phase2_complete_lifecycle_observability(self, payload: dict[str, object]) -> dict[str, object]:
        detail = dict(payload)
        seconds_remaining = detail.get("seconds_remaining", detail.get("seconds_until_close"))
        lifecycle_phase = str(detail.get("lifecycle_phase") or "").strip()
        if not lifecycle_phase:
            lifecycle_phase = (
                self._phase2_lifecycle_phase(seconds_remaining)
                if self._diagnostic_int(seconds_remaining) is not None
                else "UNKNOWN"
            )
            detail["lifecycle_phase"] = lifecycle_phase

        market_ref = str(detail.get("market_id") or detail.get("source_market_id") or "")
        ticker = str(detail.get("ticker") or detail.get("asset") or self._ticker_from_market_id(market_ref) or "UNKNOWN").upper()
        if not detail.get("condition_id"):
            meta_cache = getattr(self, "_market_token_meta", {})
            if not isinstance(meta_cache, dict):
                meta_cache = {}
            meta = meta_cache.get(ticker, {})
            condition_id = str(meta.get("condition_id", "") or "")
            if not condition_id:
                market_refs = {
                    str(value).strip()
                    for value in (detail.get("market_id"), detail.get("source_market_id"))
                    if str(value or "").strip()
                }
                token_id = str(detail.get("token_id") or "").strip()
                matching_condition_ids: list[str] = []
                for candidate_meta in meta_cache.values():
                    if not isinstance(candidate_meta, dict):
                        continue
                    candidate_condition_id = str(candidate_meta.get("condition_id", "") or "").strip()
                    if not candidate_condition_id:
                        continue
                    meta_market_id = str(candidate_meta.get("market_id", "") or "").strip()
                    meta_yes_token_id = str(candidate_meta.get("yes_token_id", "") or "").strip()
                    meta_no_token_id = str(candidate_meta.get("no_token_id", "") or "").strip()
                    market_match = bool(meta_market_id and meta_market_id in market_refs)
                    token_match = bool(token_id and token_id in {meta_yes_token_id, meta_no_token_id})
                    if market_match or token_match:
                        matching_condition_ids.append(candidate_condition_id)
                if len(matching_condition_ids) == 1:
                    condition_id = matching_condition_ids[0]
            if condition_id:
                detail["condition_id"] = condition_id
        market_id = str(detail.get("market_id") or detail.get("condition_id") or detail.get("source_market_id") or f"pm-5m-{ticker.lower()}")
        side = str(detail.get("side") or detail.get("best_side") or detail.get("outcome") or detail.get("decision") or "UNKNOWN").upper()
        epoch_start = self._diagnostic_int(detail.get("market_epoch_start") or detail.get("epoch_start") or detail.get("epoch_start_ts")) or 0
        if not detail.get("candidate_id"):
            detail["candidate_id"] = self._phase2_candidate_hash("candidate", market_id, ticker, side, epoch_start)
        if not detail.get("signal_id"):
            detail["signal_id"] = self._phase2_candidate_hash("signal", market_id, ticker, side, epoch_start)

        start_offset, end_offset = self._phase2_phase_offsets(lifecycle_phase)
        entered_at = self._phase2_iso_from_epoch(epoch_start, start_offset)
        exited_at = self._phase2_iso_from_epoch(epoch_start, end_offset) if end_offset is not None else ""
        detail.setdefault("lifecycle_phase_entered_at", entered_at or None)
        detail.setdefault("lifecycle_phase_exited_at", exited_at or None)
        if not detail.get("lifecycle_phase_transition_reason"):
            detail["lifecycle_phase_transition_reason"] = "epoch_window_direct" if entered_at else "seconds_remaining_direct"

        orderbook_state = self._phase2_orderbook_state_classification(detail)
        detail.setdefault("orderbook_state_classification", orderbook_state)
        readiness_state = self._phase2_market_readiness_state(detail, orderbook_state)
        detail.setdefault("market_readiness_state", readiness_state)
        if not detail.get("readiness_transition_reason"):
            detail["readiness_transition_reason"] = str(
                detail.get("active_window_alignment_reason")
                or detail.get("orderbook_readiness_reason")
                or readiness_state
                or "unavailable"
            )

        block_reason, block_stage, expiry_reason = self._phase2_candidate_block_detail(detail)
        detail.setdefault("candidate_block_reason", block_reason)
        detail.setdefault("candidate_block_stage", block_stage)
        detail.setdefault("candidate_expiry_reason", expiry_reason)
        detail.setdefault("candidate_survival_ms", self._phase2_candidate_survival_ms(detail))

        model_output_ready = None
        probability_stage = str(detail.get("probability_model_stage") or "").lower()
        if probability_stage in {"probability_model_output", "completed"}:
            model_output_ready = True
        elif probability_stage in {"pre_model_skip", "no_probability_model_output"}:
            model_output_ready = False
        elif bool(detail.get("fair_value_available")) or bool(detail.get("true_probability_available")):
            model_output_ready = True
        detail.setdefault("model_output_ready", model_output_ready)

        ev_candidate_ready = None
        ev_stage = str(detail.get("ev_calculation_stage") or "").lower()
        if ev_stage == "ev_calculated" or bool(detail.get("ev_after_spread_available")):
            ev_candidate_ready = True
        elif any(detail.get(field) for field in ("fair_value_null_reason", "market_price_null_reason", "true_probability_null_reason", "ev_after_spread_null_reason")):
            ev_candidate_ready = False
        detail.setdefault("ev_candidate_ready", ev_candidate_ready)
        activation_detail = self._phase2_model_activation_detail(
            detail,
            lifecycle_phase=lifecycle_phase,
            orderbook_state=orderbook_state,
            readiness_state=readiness_state,
            model_output_ready=model_output_ready,
        )
        for key, value in activation_detail.items():
            detail[key] = value
        detail.setdefault("probability_model_called", bool(model_output_ready))
        detail.setdefault("probability_model_output_visible", bool(model_output_ready))
        if not detail.get("model_handoff_stage"):
            detail["model_handoff_stage"] = (
                "MODEL_OUTPUT_SERIALIZED"
                if model_output_ready is True
                else "PRE_MODEL_GATE"
                if detail.get("model_activation_state") == "BLOCKED_BEFORE_MODEL"
                else "MODEL_OUTPUT_NOT_VISIBLE"
            )
        detail.setdefault(
            "model_output_missing_reason",
            "" if model_output_ready is True else str(detail.get("model_activation_block_reason") or "model_output_not_visible"),
        )
        first_seen_remaining = self._diagnostic_int(detail.get("first_seen_seconds_remaining"))
        first_orderbook_remaining = self._diagnostic_int(detail.get("orderbook_ready_seconds_remaining"))
        first_tradable_remaining = self._diagnostic_int(detail.get("first_tradable_seconds_remaining"))
        current_remaining = self._diagnostic_int(detail.get("seconds_remaining") or detail.get("seconds_until_close"))
        if first_seen_remaining is not None:
            detail.setdefault("first_seen_second", self._phase2_elapsed_second(first_seen_remaining))
        if first_orderbook_remaining:
            detail.setdefault("first_orderbook_ready_second", self._phase2_elapsed_second(first_orderbook_remaining))
        if first_tradable_remaining:
            detail.setdefault("first_candidate_ready_second", self._phase2_elapsed_second(first_tradable_remaining))
        if first_seen_remaining is not None and current_remaining is not None:
            duration = int(max(0, first_seen_remaining - current_remaining))
            detail.setdefault("candidate_lifecycle_duration_seconds", duration)
            detail.setdefault("candidate_lifecycle_duration", duration)

        # Preload Next Market v1
        detail["preload_attempted"] = getattr(self, "_preload_attempted", False)
        detail["preload_success"] = getattr(self, "_preload_success", False)
        detail["preload_failure_reason"] = getattr(self, "_preload_failed_reason", None)
        detail["preload_ticker"] = getattr(self, "_preload_ticker", "")
        detail["preload_market_slug"] = getattr(self, "_preload_market_slug", "")
        detail["preload_condition_id"] = getattr(self, "_preload_condition_id", "")
        detail["preload_yes_token_id_present"] = getattr(self, "_preload_yes_token_id_present", False)
        detail["preload_no_token_id_present"] = getattr(self, "_preload_no_token_id_present", False)
        detail["preload_orderbook_warmed"] = getattr(self, "_preload_orderbook_warmed", False)
        detail["preload_orderbook_state"] = getattr(self, "_preload_orderbook_state", "UNKNOWN")
        detail["preload_seconds_before_epoch"] = getattr(self, "_preload_seconds_before_epoch", 0)
        detail["preload_latency_ms"] = getattr(self, "_preload_latency_ms", 0)
        detail["preload_cache_hit"] = getattr(self, "_preload_cache_hit", False)
        detail["preload_cache_age_seconds"] = getattr(self, "_preload_cache_age_seconds", 0)
        detail["preload_next_epoch_start"] = getattr(self, "_preload_next_epoch_start", 0)
        detail["preload_next_epoch_remaining_seconds"] = getattr(self, "_preload_next_epoch_remaining_seconds", 0)

        return detail

    def _phase2_observability_payload(
        self,
        *,
        ticker: str,
        market_id: str = "",
        side: str = "",
        epoch_start: object = None,
        seconds_remaining: object = None,
        market_price: object = None,
        fair_value: object = None,
        true_probability: object = None,
        ev_after_spread: object = None,
        skip_reason: object = "",
        orderbook_readiness_reason: object = "",
        liquidity_state: object = "",
        spread_normalized: object = None,
        risk_plan: RiskPlan | None = None,
    ) -> dict[str, object]:
        epoch_start_int = self._diagnostic_int(epoch_start) or 0
        market_id = market_id or f"pm-5m-{ticker.lower()}"
        side = str(side or "UNKNOWN").upper()
        ticker_key = str(ticker or "").upper()
        cached_token_ids = getattr(self, "_real_token_ids", {}).get(ticker_key) or ()
        cached_meta = getattr(self, "_market_token_meta", {}).get(ticker_key, {})
        cached_yes_token_id = str(
            (cached_token_ids[0] if len(cached_token_ids) > 0 else "")
            or cached_meta.get("yes_token_id", "")
            or ""
        )
        cached_no_token_id = str(
            (cached_token_ids[1] if len(cached_token_ids) > 1 else "")
            or cached_meta.get("no_token_id", "")
            or ""
        )
        cached_side_token_id = ""
        if side == "YES":
            cached_side_token_id = cached_yes_token_id
        elif side == "NO":
            cached_side_token_id = cached_no_token_id
        cached_condition_id = str(cached_meta.get("condition_id", "") or "")
        cached_market_slug = str(cached_meta.get("slug", "") or cached_meta.get("market_slug", "") or "")
        token_handoff_source = "cached_market_token_meta" if cached_yes_token_id and cached_no_token_id else "not_available"
        lifecycle_phase = self._phase2_lifecycle_phase(seconds_remaining)
        candidate_id = self._phase2_candidate_hash("candidate", market_id, ticker_key, side, epoch_start_int)
        signal_id = self._phase2_candidate_hash("signal", market_id, ticker_key, side, epoch_start_int)
        market_key = (ticker_key, epoch_start_int)
        first_seen_remaining = getattr(self, "_market_first_seen_seconds_remaining", {}).get(market_key)
        if first_seen_remaining is None:
            first_seen_remaining = self._diagnostic_int(seconds_remaining)
        readiness_timestamps = self._phase2_readiness_timestamps(ticker, epoch_start_int)
        first_orderbook_remaining = self._diagnostic_int(readiness_timestamps.get("orderbook_ready_seconds_remaining"))
        first_tradable_remaining = self._diagnostic_int(readiness_timestamps.get("first_tradable_seconds_remaining"))
        price = self._diagnostic_float(market_price, default=0.0)
        exposure = self._phase2_exposure_timeline(market_id, risk_plan=risk_plan)
        starter_candidate = exposure["exposure_before"] <= 0.0 and lifecycle_phase in {
            "OPENING_SCAN",
            "ACTIVE_INVENTORY_TRADING",
        }
        final_derisk_candidate = exposure["exposure_before"] > 0.0 and lifecycle_phase == "FINAL_DERISK"
        payload: dict[str, object] = {
            "lifecycle_phase": lifecycle_phase,
            "candidate_id": candidate_id,
            "signal_id": signal_id,
            "token_id": cached_side_token_id,
            "yes_token_id": cached_yes_token_id,
            "no_token_id": cached_no_token_id,
            "condition_id": cached_condition_id,
            "market_slug": cached_market_slug,
            "cached_token_pair_available": bool(cached_yes_token_id and cached_no_token_id),
            "yes_no_token_pair_present": bool(cached_yes_token_id and cached_no_token_id),
            "decision_token_handoff_source": token_handoff_source,
            **readiness_timestamps,
            "first_seen_seconds_remaining": first_seen_remaining or 0,
            "first_seen_second": self._phase2_elapsed_second(first_seen_remaining),
            "first_orderbook_ready_second": (
                self._phase2_elapsed_second(first_orderbook_remaining) if first_orderbook_remaining else None
            ),
            "first_candidate_ready_second": (
                self._phase2_elapsed_second(first_tradable_remaining) if first_tradable_remaining else None
            ),
            "fair_value": fair_value,
            "market_price": market_price,
            "true_probability": true_probability,
            "ev_after_spread": ev_after_spread,
            **self._phase2_ev_null_reason_detail(
                fair_value=fair_value,
                market_price=market_price,
                true_probability=true_probability,
                ev_after_spread=ev_after_spread,
                skip_reason=skip_reason,
                orderbook_readiness_reason=orderbook_readiness_reason,
                liquidity_state=liquidity_state,
                spread_normalized=spread_normalized,
            ),
            "mfe_candidate_price": price if price > 0.0 else None,
            "mae_candidate_price": price if price > 0.0 else None,
            "candidate_peak_favorable": 0.0,
            "candidate_peak_adverse": 0.0,
            "starter_candidate": bool(starter_candidate),
            "reload_candidate": False,
            "unload_candidate": False,
            "final_derisk_candidate": bool(final_derisk_candidate),
            "inventory_action": (
                "FINAL_DERISK_CANDIDATE"
                if final_derisk_candidate
                else "STARTER_CANDIDATE" if starter_candidate else ""
            ),
            **exposure,
        }
        orderbook_state = self._phase2_orderbook_state_classification(payload)
        payload.setdefault("orderbook_state_classification", orderbook_state)
        readiness_state = self._phase2_market_readiness_state(payload, orderbook_state)
        payload.setdefault("market_readiness_state", readiness_state)
        model_output_ready = (
            self._phase2_value_available(fair_value)
            or self._phase2_value_available(true_probability)
        )
        payload.update(
            self._phase2_model_activation_detail(
                payload,
                lifecycle_phase=lifecycle_phase,
                orderbook_state=orderbook_state,
                readiness_state=readiness_state,
                model_output_ready=model_output_ready,
            )
        )
        return payload

    def _active_window_alignment_detail(
        self,
        *,
        ticker: str,
        epoch_start: int,
        epoch_end: int,
        seconds_remaining: int | None,
        token_ids: tuple[str, str] | None = None,
        orderbook_ready: bool | None = None,
        nonzero_bidask: bool = False,
        liquidity_state: str | None = None,
        spread: float | None = None,
        spread_limit: float | None = None,
        yes_ob: OrderbookSnapshot | None = None,
        no_ob: OrderbookSnapshot | None = None,
    ) -> dict[str, object]:
        ticker = ticker.upper()
        now_ts = int(time.time())
        if epoch_start <= 0 and epoch_end > 0:
            epoch_start = epoch_end - 300
        if epoch_end <= 0 and epoch_start > 0:
            epoch_end = epoch_start + 300
        seconds_until_close = (
            max(0, int(seconds_remaining))
            if seconds_remaining is not None
            else max(0, epoch_end - now_ts) if epoch_end else 0
        )
        seconds_since_open = max(0, min(300, now_ts - epoch_start)) if epoch_start else 0
        key = (ticker, epoch_start)
        first_seen = self._market_first_seen_seconds_remaining.setdefault(key, seconds_until_close)

        has_tokens = bool(token_ids and token_ids[0] and token_ids[1])
        hard_block = self._entry_hard_block_seconds()
        if not epoch_start or now_ts < epoch_start:
            reason = "before_active_window"
        elif seconds_until_close <= hard_block:
            reason = "late_hard_close_zone"
        elif not has_tokens:
            reason = "missing_token_id"
        elif orderbook_ready is False:
            reason = "orderbook_not_ready"
        elif seconds_since_open <= 60:
            reason = "early_window_ready"
        else:
            reason = "active_window_ready"

        first_evaluable = self._market_first_evaluable_seconds_remaining.get(key)
        if first_evaluable is None and has_tokens and seconds_until_close > hard_block and orderbook_ready is not False:
            first_evaluable = seconds_until_close
            self._market_first_evaluable_seconds_remaining[key] = first_evaluable
        liquidity_observed = liquidity_state is not None
        liquidity_ready = str(liquidity_state or "").upper() == "HEALTHY"
        if spread_limit is None:
            spread_limit = float(self._phase2_safe_setting("adaptive_entry_max_spread", 0.06))
        spread_ready = spread is not None and float(spread or 0.0) <= float(spread_limit)
        tradable_ready = bool(
            has_tokens
            and orderbook_ready is True
            and liquidity_ready
            and spread_ready
            and seconds_until_close > hard_block
        )
        readiness_timestamps = self._phase2_mark_readiness(
            ticker=ticker,
            epoch_start=epoch_start,
            epoch_end=epoch_end,
            token_ready=has_tokens,
            orderbook_ready=orderbook_ready is True,
            nonzero_bidask=nonzero_bidask,
            liquidity_ready=liquidity_ready,
            spread_ready=spread_ready,
            first_evaluable_ready=first_evaluable is not None,
            first_tradable_ready=tradable_ready,
            seconds_remaining=seconds_until_close,
            yes_ob=yes_ob,
            no_ob=no_ob,
        )
        first_tradable = self._diagnostic_int(readiness_timestamps.get("first_tradable_seconds_remaining")) or 0
        first_orderbook_ready = self._diagnostic_int(readiness_timestamps.get("orderbook_ready_seconds_remaining")) or 0
        candidate_lifecycle_duration_seconds = max(0, int(first_seen) - int(seconds_until_close))

        # Timing Metrics Calculation
        first_seen_rem = self._diagnostic_int(readiness_timestamps.get("first_discovered_seconds_remaining")) or 0
        first_ob_rem = self._diagnostic_int(readiness_timestamps.get("first_orderbook_seen_seconds_remaining")) or 0
        first_trad_rem = self._diagnostic_int(readiness_timestamps.get("first_tradable_seconds_remaining")) or 0

        discovery_to_book = max(0, first_seen_rem - first_ob_rem) if first_ob_rem > 0 else 0
        book_to_tradable = max(0, first_ob_rem - first_trad_rem) if (first_ob_rem > 0 and first_trad_rem > 0) else 0
        total_discovery_to_tradable = max(0, first_seen_rem - first_trad_rem) if (first_seen_rem > 0 and first_trad_rem > 0) else 0

        return {
            "market_epoch_start": epoch_start,
            "market_epoch_end": epoch_end,
            "epoch_start_ts": epoch_start,
            "epoch_end_ts": epoch_end,
            "lifecycle_phase": self._phase2_lifecycle_phase(seconds_until_close),
            "seconds_since_open": seconds_since_open,
            "seconds_until_close": seconds_until_close,
            "first_seen_seconds_remaining": first_seen,
            "first_evaluable_seconds_remaining": first_evaluable or 0,
            "first_tradable_seconds_remaining": first_tradable,
            "first_seen_second": self._phase2_elapsed_second(first_seen),
            "first_orderbook_ready_second": self._phase2_elapsed_second(first_orderbook_ready) if first_orderbook_ready else None,
            "first_candidate_ready_second": self._phase2_elapsed_second(first_tradable) if first_tradable else None,
            "candidate_lifecycle_duration_seconds": candidate_lifecycle_duration_seconds,
            "candidate_lifecycle_duration": candidate_lifecycle_duration_seconds,
            "first_tradable_at_utc": readiness_timestamps.get("first_tradable_at", ""),
            "discovery_to_book_seconds": discovery_to_book,
            "book_to_tradable_seconds": book_to_tradable,
            "total_discovery_to_tradable_seconds": total_discovery_to_tradable,
            **readiness_timestamps,
            "liquidity_ready": bool(liquidity_ready) if liquidity_observed else None,
            "depth_ready": bool(liquidity_ready) if liquidity_observed else None,
            "spread_normalized": bool(spread_ready) if spread is not None else None,
            "spread_limit": float(spread_limit),
            "spread_gap_to_limit": (
                round(float(spread or 0.0) - float(spread_limit), 6)
                if spread is not None
                else None
            ),
            "active_window_alignment_reason": reason,
        }

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
        self._market_first_seen_seconds_remaining.setdefault(key, int(meta["seconds_remaining"]))
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
        clob_error_detail: dict[str, object] = {}
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
            clob_error_detail = self._clob_orderbook_error_detail(
                exc,
                token_id=token_ids[0] if token_ids else "",
                market_slug=str(meta.get("slug", "") or ""),
                asset=ticker,
            )
            self._market_readiness_metrics["token_preload_failures"] += 1
            LOGGER.info(
                "[MARKET_WARMUP] ticker=%s market_slug=%s epoch=%s status=degraded reason=%s category=%s exception_type=%s error=%s",
                ticker,
                meta.get("slug", ""),
                epoch_start,
                reason,
                clob_error_detail.get("clob_error_category", ""),
                clob_error_detail.get("clob_exception_type", ""),
                exc,
            )
        finally:
            self._mark_orderbook_refresh(
                ticker,
                source="market_warmup",
                trigger=reason,
                executable_yes_no_book=bool(ok),
                condition_id=meta.get("condition_id", ""),
                yes_token_id=token_ids[0] if token_ids else "",
                no_token_id=token_ids[1] if token_ids else "",
                market_slug=meta.get("slug", ""),
            )
            self._warmed_orderbook_epochs.add((ticker, epoch_start))
            duration_ms = int(max(0.0, time.monotonic() - started) * 1000)
            alignment_detail = self._active_window_alignment_detail(
                ticker=ticker,
                epoch_start=epoch_start,
                epoch_end=self._meta_int(meta, "epoch_end_ts", epoch_start + 300),
                seconds_remaining=self._meta_int(meta, "seconds_remaining"),
                token_ids=token_ids,
                orderbook_ready=ok,
                nonzero_bidask=bool(ok),
                yes_ob=yes_ob,
                no_ob=no_ob,
            )
            self._emit_quant_event(
                "log_system_health",
                {
                    "event": "market_readiness_warmup",
                    "ticker": ticker,
                    "market_slug": str(meta.get("slug", "")),
                    "condition_id": str(meta.get("condition_id", "")),
                    "epoch_start_ts": epoch_start,
                    "seconds_remaining": self._meta_int(meta, "seconds_remaining"),
                    **alignment_detail,
                    "orderbook_readiness_ms": duration_ms,
                    "warmup_ok": ok,
                    "reason": reason,
                    "error": error,
                    **clob_error_detail,
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
            **self._bankroll_tier_detail(),
            "bankroll_mode": str(diagnostics.get("bankroll_mode", self._bankroll_mode())),
            "micro_survival_active": bool(diagnostics.get("micro_survival_active", self._micro_survival_active())),
            "micro_position_size": float(diagnostics.get("micro_position_size", self._micro_position_size()) or 0.0),
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
        edge = display.get("edge", display.get("ev"))
        decision_timestamp = self._utc_timestamp()
        market_close_timestamp = str(
            display.get("market_close_timestamp")
            or display.get("market_end_time")
            or ""
        )
        orderbook_age_ms = self._diagnostic_int(display.get("orderbook_age_ms")) or 0
        oracle_age_ms = self._diagnostic_int(display.get("oracle_age_ms")) or 0
        market_feed_age_ms = self._diagnostic_int(display.get("market_feed_age_ms")) or 0
        regime_detail = classify_market_regime_from_payload(display).to_payload()
        cutoff_block_seconds_remaining = (
            self._diagnostic_int(seconds_remaining)
            if normalized_reason == "time_unsafe" or "cutoff" in raw_reason.lower()
            else None
        )
        candidate_side = str(display.get("side") or display.get("best_side") or display.get("outcome") or outcome.decision)
        fair_value = display.get("fair_value")
        true_probability = display.get("true_probability")
        if fair_value is None or true_probability is None:
            side_upper = candidate_side.upper()
            if side_upper == "YES":
                fair_value = display.get("p_yes", display.get("model_p_yes")) if fair_value is None else fair_value
                true_probability = fair_value if true_probability is None else true_probability
            elif side_upper == "NO":
                fair_value = display.get("p_no", display.get("model_p_no")) if fair_value is None else fair_value
                true_probability = fair_value if true_probability is None else true_probability
        ev_after_spread_value = display.get("ev_after_spread")
        if ev_after_spread_value is None:
            ev_after_spread_value = display.get("ev")
        if ev_after_spread_value is None:
            ev_after_spread_value = edge
        phase2_detail = self._phase2_observability_payload(
            ticker=ticker or self._ticker_from_market_id(outcome.market_id),
            market_id=outcome.market_id,
            side=candidate_side,
            epoch_start=display.get("market_epoch_start", display.get("epoch_start", display.get("epoch_start_ts"))),
            seconds_remaining=seconds_remaining,
            market_price=display.get("market_price", display.get("ask_price", display.get("entry_price"))),
            fair_value=fair_value,
            true_probability=true_probability,
            ev_after_spread=ev_after_spread_value,
            skip_reason=normalized_reason or raw_reason,
            orderbook_readiness_reason=display.get("orderbook_readiness_reason", display.get("orderbook_unavailable_reason", "")),
            liquidity_state=display.get("liquidity_state", ""),
            spread_normalized=display.get("spread_normalized"),
            risk_plan=outcome.risk_plan,
        )
        decision_id = self._phase2_candidate_hash(
            "decision",
            outcome.market_id,
            (ticker or self._ticker_from_market_id(outcome.market_id) or "UNKNOWN").upper(),
            str(candidate_side or "UNKNOWN").upper(),
            self._diagnostic_int(display.get("market_epoch_start", display.get("epoch_start", display.get("epoch_start_ts")))) or 0,
        )
        for field_name in (
            "lifecycle_phase",
            "candidate_id",
            "signal_id",
            "token_ready_at",
            "token_ready_seconds_remaining",
            "orderbook_ready_at",
            "orderbook_ready_seconds_remaining",
            "liquidity_ready_at",
            "liquidity_ready_seconds_remaining",
            "spread_ready_at",
            "spread_ready_seconds_remaining",
            "first_tradable_at",
            "first_tradable_seconds_remaining",
            "first_evaluable_at",
            "first_evaluable_ready_seconds_remaining",
            "first_seen_second",
            "first_orderbook_ready_second",
            "first_candidate_ready_second",
            "candidate_lifecycle_duration_seconds",
            "candidate_lifecycle_duration",
            "fair_value",
            "fair_value_available",
            "fair_value_null_reason",
            "market_price",
            "market_price_available",
            "market_price_null_reason",
            "true_probability",
            "true_probability_available",
            "true_probability_null_reason",
            "ev_after_spread",
            "ev_after_spread_available",
            "ev_after_spread_null_reason",
            "model_probability_yes",
            "model_probability_no",
            "fair_value_yes",
            "fair_value_no",
            "model_attempted",
            "probability_model_called",
            "probability_model_output_visible",
            "model_output_missing_reason",
            "model_output_source",
            "model_handoff_stage",
            "pre_model_gate_name",
            "pre_model_gate_group",
            "pre_model_gate_reason",
            "pre_model_gate_source",
            "pre_model_gate_blocks_probability_model",
            "probability_model_call_path",
            "model_not_run_reason",
            "probability_model_gate_reason",
            "probability_model_stage",
            "ev_calculation_stage",
            "mfe_candidate_price",
            "mae_candidate_price",
            "candidate_peak_favorable",
            "candidate_peak_adverse",
            "starter_candidate",
            "reload_candidate",
            "unload_candidate",
            "final_derisk_candidate",
            "inventory_action",
            "exposure_before",
            "exposure_after",
            "risk_budget_used",
            "remaining_risk_budget",
            "current_exposure",
            "target_exposure",
            "model_activation_state",
            "model_activation_block_group",
            "model_activation_block_reason",
            "model_attempt_eligible",
            "model_activation_effective_cutoff_seconds",
            "model_activation_hard_block_seconds",
            "model_activation_lifecycle_phase",
            "model_activation_orderbook_state",
            "model_activation_market_readiness_state",
            "token_id",
            "yes_token_id",
            "no_token_id",
            "condition_id",
            "market_slug",
            "cached_token_pair_available",
            "yes_no_token_pair_present",
            "decision_token_handoff_source",
            "yes_bid",
            "yes_ask",
            "no_bid",
            "no_ask",
            "yes_bid_size",
            "yes_ask_size",
            "no_bid_size",
            "no_ask_size",
            "yes_mid",
            "no_mid",
            "spread",
            "spread_normalized",
            "spread_limit",
            "spread_gap_to_limit",
            "orderbook_bid",
            "orderbook_ask",
            "orderbook_bid_size",
            "orderbook_ask_size",
            "first_model_eligible_second",
            "seconds_remaining_when_eligible",
            "first_probability_output_second",
            "seconds_remaining_when_model_output_visible",
            "model_eligible_at_or_inside_cutoff",
            "decision_cycle_started_at",
            "last_orderbook_refresh_at",
            "orderbook_snapshot_age_ms_at_decision",
            "last_successful_yes_no_book_at",
            "orderbook_refresh_source",
            "orderbook_refresh_trigger",
            "decision_cycle_interval_seconds",
            "actual_market_revisit_frequency_seconds",
            "orderbook_reuse_detected",
            "executable_book_last_seen_age_ms",
            "decision_token_pair_key",
            "last_orderbook_refresh_token_pair_key",
            "last_successful_yes_no_book_token_pair_key",
            "orderbook_lineage_match",
            "orderbook_current_fetch_status",
            "orderbook_stale_reuse_source",
            "scheduler_cadence_source",
            "hot_path_timing_source",
            "configured_decision_loop_interval_seconds",
            "intended_decision_loop_target_seconds",
            "effective_outer_loop_interval_seconds",
            "snapshot_sampling_interval_seconds",
            "market_discovery_interval_seconds",
            "outer_loop_poll_interval_seconds",
            "market_evaluation_asset",
            "market_evaluation_started_at",
            "market_evaluation_started_ms_since_cycle",
            "market_evaluation_duration_ms",
            "market_sequence_index",
            "market_sequence_count",
            "cycle_elapsed_ms_at_market_evaluation",
            "candidate_created_at",
            "candidate_enqueue_at",
            "candidate_dequeue_at",
            "candidate_queue_age_ms",
            "hot_path_admission_wait_ms",
            "candidate_queue_age_source",
            "candidate_queue_ownership",
            "candidate_revisit_scheduling_source",
            "hot_path_admission_trigger",
            "event_vs_polling_classification",
            "executable_liquidity_event_role",
            "executable_liquidity_triggered_hot_path",
            "market_snapshot_decision_pipeline_linkage",
            "candidate_handoff_boundary",
            "empty_book_recovery_duration_ms",
            # Observability v1: probability model inputs
            "probability_model_reason",
            "prob_model_momentum_input",
            "prob_model_liquidity_usd",
            # Observability v2: signal and regime inputs (additive, read-only)
            "price_change_pct",
            "realized_volatility",
            "price_velocity",
            "distance_from_ptb_pct",
            # Two-tier signal attribution (Patch 6B)
            "signal_name",
            "signal_reason",
            "strategy_signal_name",
            "strategy_signal_reason",
        ):
            value = display.get(field_name)
            if value is not None and value != "":
                phase2_detail[field_name] = value
        payload: dict[str, object] = {
            "decision_id": decision_id,
            "raw_skip_reason": raw_reason,
            "normalized_skip_reason": normalized_reason,
            "asset": ticker or self._ticker_from_market_id(outcome.market_id),
            "side": str(candidate_side or "UNKNOWN").upper(),
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
            "micro_timing_allowed": bool(display.get("micro_timing_allowed", False)),
            "micro_timing_denied_reason": str(display.get("micro_timing_denied_reason", "") or ""),
            "effective_micro_cutoff_seconds": self._diagnostic_int(display.get("effective_micro_cutoff_seconds")) or 0,
            "micro_cutoff_policy": str(display.get("micro_cutoff_policy", "") or "standard"),
            "micro_timing_branch_entered": bool(display.get("micro_timing_branch_entered", False)),
            "micro_timing_branch_skipped_reason": str(display.get("micro_timing_branch_skipped_reason", "") or ""),
            "micro_timing_candidate": bool(display.get("micro_timing_candidate", False)),
            "cutoff_block_seconds_remaining": cutoff_block_seconds_remaining,
            "time_bucket": time_bucket,
            "epoch_start": self._diagnostic_int(display.get("epoch_start", display.get("epoch_start_ts"))),
            "market_epoch_start": self._diagnostic_int(display.get("market_epoch_start", display.get("epoch_start_ts"))),
            "market_epoch_end": self._diagnostic_int(display.get("market_epoch_end", display.get("epoch_end_ts"))),
            "seconds_since_open": self._diagnostic_int(display.get("seconds_since_open")),
            "seconds_until_close": self._diagnostic_int(display.get("seconds_until_close", seconds_remaining)),
            "first_seen_seconds_remaining": self._diagnostic_int(display.get("first_seen_seconds_remaining")),
            "first_evaluable_seconds_remaining": self._diagnostic_int(display.get("first_evaluable_seconds_remaining")),
            "first_tradable_seconds_remaining": self._diagnostic_int(display.get("first_tradable_seconds_remaining")),
            "first_seen_second": self._diagnostic_int(display.get("first_seen_second", phase2_detail.get("first_seen_second"))),
            "first_orderbook_ready_second": self._diagnostic_int(display.get("first_orderbook_ready_second", phase2_detail.get("first_orderbook_ready_second"))),
            "first_candidate_ready_second": self._diagnostic_int(display.get("first_candidate_ready_second", phase2_detail.get("first_candidate_ready_second"))),
            "candidate_lifecycle_duration_seconds": self._diagnostic_int(display.get("candidate_lifecycle_duration_seconds", phase2_detail.get("candidate_lifecycle_duration_seconds"))),
            "candidate_lifecycle_duration": self._diagnostic_int(display.get("candidate_lifecycle_duration", phase2_detail.get("candidate_lifecycle_duration"))),
            "first_tradable_at_utc": str(display.get("first_tradable_at_utc", phase2_detail.get("first_tradable_at", "")) or ""),
            **phase2_detail,
            "active_window_alignment_reason": str(display.get("active_window_alignment_reason", "") or ""),
            "market_start_time": str(display.get("market_start_time", "") or ""),
            "market_end_time": str(display.get("market_end_time", "") or ""),
            "market_close_timestamp": market_close_timestamp,
            "token_id": str(display.get("token_id") or phase2_detail.get("token_id") or ""),
            "yes_token_id": str(display.get("yes_token_id") or phase2_detail.get("yes_token_id") or ""),
            "no_token_id": str(display.get("no_token_id") or phase2_detail.get("no_token_id") or ""),
            "condition_id": str(display.get("condition_id") or phase2_detail.get("condition_id") or ""),
            "outcome": str(display.get("outcome", "") or ""),
            "source_module": str(display.get("source_module", "polymarket.trader") or "polymarket.trader"),
            "orderbook_age_ms": orderbook_age_ms,
            "orderbook_age": round(orderbook_age_ms / 1000.0, 3),
            "orderbook_age_seconds": round(orderbook_age_ms / 1000.0, 3),
            "orderbook_readiness_reason": str(display.get("orderbook_readiness_reason", "") or ""),
            "orderbook_unavailable_reason": str(display.get("orderbook_unavailable_reason", "") or ""),
            "orderbook_error": str(display.get("orderbook_error", "") or ""),
            "clob_error_category": str(display.get("clob_error_category", "") or ""),
            "clob_error_class": str(display.get("clob_error_class", "") or ""),
            "clob_exception_type": str(display.get("clob_exception_type", "") or ""),
            "clob_status_code": self._diagnostic_int(display.get("clob_status_code")),
            "clob_token_id_present": bool(display.get("clob_token_id_present", False)),
            "clob_parse_failure": bool(display.get("clob_parse_failure", False)),
            "clob_api_failure": bool(display.get("clob_api_failure", False)),
            "clob_error_rate": self._diagnostic_float(display.get("clob_error_rate")),
            "clob_backoff_active": bool(display.get("clob_backoff_active", False)),
            "clob_circuit_open": bool(display.get("clob_circuit_open", False)),
            "clob_cooldown_seconds_remaining": self._diagnostic_float(display.get("clob_cooldown_seconds_remaining")),
            "clob_recovery_count": self._diagnostic_int(display.get("clob_recovery_count")),
            "market_data_degraded": bool(display.get("market_data_degraded", False)),
            "retry_count": self._diagnostic_int(display.get("retry_count")),
            "empty_book_recovery_attempted": bool(display.get("empty_book_recovery_attempted", False)),
            "empty_book_recovery_success": bool(display.get("empty_book_recovery_success", False)),
            "empty_book_recovery_failed": bool(display.get("empty_book_recovery_failed", False)),
            "empty_book_recovery_retry_count": self._diagnostic_int(display.get("empty_book_recovery_retry_count")) or 0,
            "liquidity_state": str(display.get("liquidity_state", "") or "HEALTHY"),
            **{
                field_name: display.get(field_name, self._empty_book_recovery_detail().get(field_name))
                for field_name in EMPTY_BOOK_RECOVERY_RESEARCH_FIELD_NAMES
            },
            "oracle_age_ms": oracle_age_ms,
            "oracle_age": round(oracle_age_ms / 1000.0, 3),
            "oracle_age_seconds": round(oracle_age_ms / 1000.0, 3),
            "market_feed_age_ms": market_feed_age_ms,
            "market_feed_age_seconds": round(market_feed_age_ms / 1000.0, 3),
            "volatility_regime": str(display.get("volatility_regime", regime_detail["volatility_regime"]) or "UNKNOWN"),
            "volatility_score": self._diagnostic_float(display.get("volatility_score", regime_detail["volatility_score"])),
            "trend_regime": str(display.get("trend_regime", regime_detail["trend_regime"]) or "UNKNOWN"),
            "trend_strength": self._diagnostic_float(display.get("trend_strength", regime_detail["trend_strength"])),
            "market_regime": str(display.get("market_regime", "") or regime_detail.get("market_regime", "UNKNOWN") or "UNKNOWN"),
            "bullish_probability": self._diagnostic_float(display.get("bullish_probability", display.get("p_yes", 0.5))),
            "bearish_probability": self._diagnostic_float(display.get("bearish_probability", display.get("p_no", 0.5))),
            "reversal_risk": self._diagnostic_float(display.get("reversal_risk", 0.0)),
            "compression_score": self._diagnostic_float(display.get("compression_score", 0.0)),
            "signal_trend_strength": self._diagnostic_float(display.get("signal_trend_strength", display.get("trend_strength", 0.0))),
            "signal_volatility_score": self._diagnostic_float(display.get("signal_volatility_score", display.get("volatility_score", 0.0))),
            "indicator_evidence": str(display.get("indicator_evidence", "") or ""),
            "regime_reason": str(display.get("regime_reason", regime_detail["regime_reason"]) or ""),
            "token_mapping_warning": str(display.get("token_mapping_warning", "") or ""),
            "paper_virtual_cash": float(self.bankroll_state.current_cash_balance if self.settings.paper_trading else 0.0),
            "paper_available_balance": float(self._paper_available_balance() if self.settings.paper_trading else 0.0),
            "paper_open_position_value": float(self.bankroll_state.open_position_market_value if self.settings.paper_trading else 0.0),
            **self._bankroll_tier_detail(),
            **self._bankroll_mode_detail(),
            "live_wallet_reference_balance": (
                float(self._wallet_reference_balance)
                if self._wallet_reference_balance is not None and self._paper_wallet_reference_visible()
                else None
            ),
            "risk_per_trade": float(getattr(outcome.risk_plan, "risk_amount", 0.0) or 0.0),
            "calculated_order_size": float(getattr(outcome.risk_plan, "position_size", 0.0) or 0.0),
            "risk_plan_zero_reason": "",
        }
        for key, value in self._scheduler_cadence_observability_detail(
            str(ticker or self._ticker_from_market_id(outcome.market_id) or "")
        ).items():
            if payload.get(key) in (None, ""):
                payload[key] = value
        if not bool(payload.get("ev_after_spread_available")) and not self._phase2_value_available(payload.get("ev_after_spread")):
            ev_stage = str(payload.get("ev_calculation_stage") or "").lower()
            probability_stage = str(payload.get("probability_model_stage") or "").lower()
            if probability_stage == "pre_model_skip":
                payload["ev_missing_reason"] = "model_not_run"
            elif ev_stage in {"candidate_blocked_before_ev", "pre_model_skip"}:
                payload["ev_missing_reason"] = "not_computed_at_producer"
            else:
                payload["ev_missing_reason"] = str(payload.get("ev_after_spread_null_reason") or "field_not_available")
        if bool(payload.get("model_attempted")):
            payload["model_not_run_reason"] = ""
            payload["probability_model_gate_reason"] = str(
                payload.get("probability_model_gate_reason") or "model_output_visible"
            )
        yes_token_present = bool(str(payload.get("yes_token_id") or "").strip())
        no_token_present = bool(str(payload.get("no_token_id") or "").strip())
        payload["yes_no_token_pair_present"] = bool(yes_token_present and no_token_present)
        if payload["yes_no_token_pair_present"] and str(payload.get("decision_token_handoff_source") or "not_available") == "not_available":
            payload["decision_token_handoff_source"] = "decision_payload_or_cache"
        yes_bid_present = self._phase2_value_available(payload.get("yes_bid"))
        yes_ask_present = self._phase2_value_available(payload.get("yes_ask"))
        no_bid_present = self._phase2_value_available(payload.get("no_bid"))
        no_ask_present = self._phase2_value_available(payload.get("no_ask"))
        serialized_executable_book = bool(
            yes_bid_present and yes_ask_present and no_bid_present and no_ask_present
        )
        payload["decision_orderbook_bid_fields_present"] = bool(yes_bid_present and no_bid_present)
        payload["decision_orderbook_ask_fields_present"] = bool(yes_ask_present and no_ask_present)
        if serialized_executable_book:
            payload["decision_orderbook_completeness_source"] = "serialized_yes_no_bid_ask"
        elif yes_ask_present or no_ask_present or yes_bid_present or no_bid_present:
            payload["decision_orderbook_completeness_source"] = "partial_serialized_yes_no_book"
        else:
            payload["decision_orderbook_completeness_source"] = "not_serialized_or_unavailable"
        current_fetch_status = str(
            display.get("orderbook_current_fetch_status")
            or phase2_detail.get("orderbook_current_fetch_status")
            or ""
        )
        if current_fetch_status in {"fresh_fetch_executable", "fresh_fetch_non_executable"}:
            current_fetch_succeeded = True
        elif current_fetch_status == "fresh_fetch_failed":
            current_fetch_succeeded = False
        else:
            current_fetch_succeeded = None
        current_fetch_executable = bool(
            serialized_executable_book or current_fetch_status == "fresh_fetch_executable"
        )
        payload.update(
            self._orderbook_refresh_observability_detail(
                str(ticker or self._ticker_from_market_id(outcome.market_id) or ""),
                current_executable_yes_no_book=current_fetch_executable,
                current_fetch_succeeded=current_fetch_succeeded,
                condition_id=display.get("condition_id") or phase2_detail.get("condition_id", ""),
                yes_token_id=display.get("yes_token_id") or phase2_detail.get("yes_token_id", ""),
                no_token_id=display.get("no_token_id") or phase2_detail.get("no_token_id", ""),
                market_slug=display.get("market_slug") or phase2_detail.get("market_slug", ""),
                record_decision_cycle=True,
            )
        )
        authoritative_book_available, authoritative_book_source = self._phase2_authoritative_orderbook_availability(payload)
        payload["orderbook_available_for_decision"] = bool(authoritative_book_available)
        payload["orderbook_availability_source"] = authoritative_book_source or "none"
        if (
            authoritative_book_available
            and payload["decision_orderbook_completeness_source"] == "not_serialized_or_unavailable"
        ):
            payload["decision_orderbook_completeness_source"] = "authoritative_readiness_without_serialized_book"
        orderbook_state = self._phase2_orderbook_state_classification(payload)
        readiness_state = self._phase2_market_readiness_state(payload, orderbook_state)
        payload["orderbook_state_classification"] = orderbook_state
        payload["market_readiness_state"] = readiness_state
        skip_text = " ".join(
            str(part or "").lower()
            for part in (
                normalized_reason,
                raw_reason,
                payload.get("adaptive_cutoff_reason"),
                payload.get("active_window_alignment_reason"),
            )
            if part
        )
        if authoritative_book_available and any(
            token in skip_text for token in ("time_unsafe", "cutoff", "hard_close", "too_late")
        ):
            payload["orderbook_availability_classification"] = "orderbook_available_but_skipped_by_cutoff"
        elif authoritative_book_available and outcome.skipped:
            payload["orderbook_availability_classification"] = "orderbook_available_but_skipped"
        elif authoritative_book_available:
            payload["orderbook_availability_classification"] = "orderbook_available"
        elif orderbook_state in {"unavailable", "orderbook_unavailable"}:
            payload["orderbook_availability_classification"] = "true_orderbook_unavailable"
        else:
            payload["orderbook_availability_classification"] = "orderbook_not_authoritatively_available"
        model_output_ready = (
            bool(payload.get("model_attempted"))
            or bool(payload.get("fair_value_available"))
            or bool(payload.get("true_probability_available"))
            or self._phase2_value_available(payload.get("fair_value"))
            or self._phase2_value_available(payload.get("true_probability"))
        )
        payload.update(
            self._phase2_model_activation_detail(
                payload,
                lifecycle_phase=str(payload.get("lifecycle_phase") or "UNKNOWN"),
                orderbook_state=orderbook_state,
                readiness_state=readiness_state,
                model_output_ready=model_output_ready,
            )
        )
        if model_output_ready:
            payload["probability_model_called"] = bool(payload.get("probability_model_called")) or True
            payload["probability_model_output_visible"] = True
            payload["model_handoff_stage"] = "MODEL_OUTPUT_SERIALIZED"
            payload["model_output_missing_reason"] = ""
            payload.setdefault("model_output_source", "decision_payload")
        else:
            payload["probability_model_called"] = bool(payload.get("probability_model_called"))
            payload["probability_model_output_visible"] = False
            payload["model_handoff_stage"] = str(
                payload.get("model_handoff_stage")
                or ("PRE_MODEL_GATE" if payload.get("model_activation_state") == "BLOCKED_BEFORE_MODEL" else "MODEL_OUTPUT_NOT_VISIBLE")
            )
            payload["model_output_missing_reason"] = str(
                payload.get("model_activation_block_reason")
                or payload.get("model_output_missing_reason")
                or payload.get("probability_model_gate_reason")
                or "model_output_not_visible"
            )
            payload.setdefault("model_output_source", "")
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
        # No-Entry Root Cause Classifier v1 — additive observability fields, fail-soft
        try:
            from utils.no_entry_root_cause_classifier import classify_no_entry_root_cause as _classify_root_cause
            _root_cause = _classify_root_cause(payload)
            for _k, _v in _root_cause.items():
                if _k not in payload or payload[_k] in (None, ""):
                    payload[_k] = _v
        except Exception:
            pass
        # Market Readiness Admission Probe v1 — additive observability fields, fail-soft
        try:
            from utils.admission_probe_classifier import classify_admission_probe as _classify_probe
            _probe = _classify_probe(payload)
            for _k, _v in _probe.items():
                if _k not in payload or payload[_k] in (None, ""):
                    payload[_k] = _v
        except Exception:
            pass
        # Executable State Persistence Probe v1 — additive observability fields, fail-soft
        try:
            from utils.executable_state_persistence_classifier import (
                classify_executable_state_persistence as _classify_persistence,
            )
            _persistence = _classify_persistence(payload)
            for _k, _v in _persistence.items():
                if _k not in payload or payload[_k] in (None, ""):
                    payload[_k] = _v
        except Exception:
            pass
        return payload

    def _risk_boundary_payload_from_decision(
        self,
        decision_payload: dict[str, object],
        *,
        decision_type: str,
        outcome: TradeOutcome,
    ) -> dict[str, object] | None:
        if not outcome.skipped and decision_type != "risk_rejected":
            return None

        normalized_reason = str(decision_payload.get("normalized_skip_reason") or "").lower()
        raw_reason = str(decision_payload.get("raw_skip_reason") or outcome.skip_reason or "")
        risk_zero_reason = str(decision_payload.get("risk_plan_zero_reason") or "")
        risk_plan = outcome.risk_plan
        risk_plan_present = risk_plan is not None
        risk_plan_size = float(getattr(risk_plan, "position_size", 0.0) or 0.0)

        if decision_type == "risk_rejected" or normalized_reason == "risk_plan_zero" or risk_zero_reason:
            risk_decision = "blocked"
            risk_block_reason = risk_zero_reason or normalized_reason or raw_reason or "risk_rejected"
        elif risk_plan_present and risk_plan_size > 0.0:
            risk_decision = "approved"
            risk_block_reason = ""
        else:
            risk_decision = "not_reached"
            risk_block_reason = "blocked_before_risk_evaluation"

        wanted_fields = (
            "decision_id",
            "candidate_id",
            "signal_id",
            "candidate_trace_id",
            "parent_candidate_trace_id",
            "trace_link_reason",
            "market_id",
            "market_key",
            "market_slug",
            "condition_id",
            "token_id",
            "yes_token_id",
            "no_token_id",
            "side",
            "outcome",
            "asset",
            "ticker",
            "lifecycle_phase",
            "seconds_remaining",
            "market_epoch_start",
            "first_seen_second",
            "first_orderbook_ready_second",
            "first_candidate_ready_second",
            "first_model_eligible_second",
            "first_probability_output_second",
            "seconds_remaining_when_eligible",
            "seconds_remaining_when_model_output_visible",
            "candidate_lifecycle_duration_seconds",
            "fair_value",
            "fair_value_available",
            "fair_value_null_reason",
            "market_price",
            "market_price_available",
            "market_price_null_reason",
            "true_probability",
            "true_probability_available",
            "true_probability_null_reason",
            "ev",
            "ev_after_spread",
            "ev_after_spread_available",
            "ev_after_spread_null_reason",
            "ev_missing_reason",
            "probability_model_called",
            "probability_model_output_visible",
            "model_output_missing_reason",
            "model_output_source",
            "model_handoff_stage",
            "pre_model_gate_name",
            "pre_model_gate_group",
            "pre_model_gate_reason",
            "pre_model_gate_source",
            "pre_model_gate_blocks_probability_model",
            "probability_model_call_path",
            "probability_model_stage",
            "ev_calculation_stage",
            "candidate_block_stage",
            "candidate_block_reason",
            "orderbook_state_classification",
            "market_readiness_state",
            "liquidity_state",
            "risk_budget_used",
            "remaining_risk_budget",
            "model_activation_state",
            "model_activation_block_group",
            "model_activation_block_reason",
            "model_attempt_eligible",
            "model_activation_effective_cutoff_seconds",
            "model_activation_hard_block_seconds",
            "model_activation_lifecycle_phase",
            "model_activation_orderbook_state",
            "model_activation_market_readiness_state",
            "decision_cycle_started_at",
            "last_orderbook_refresh_at",
            "orderbook_snapshot_age_ms_at_decision",
            "last_successful_yes_no_book_at",
            "orderbook_refresh_source",
            "orderbook_refresh_trigger",
            "decision_cycle_interval_seconds",
            "orderbook_reuse_detected",
            "executable_book_last_seen_age_ms",
            "decision_token_pair_key",
            "last_orderbook_refresh_token_pair_key",
            "last_successful_yes_no_book_token_pair_key",
            "orderbook_lineage_match",
            "orderbook_current_fetch_status",
            "orderbook_stale_reuse_source",
        )
        payload = {
            field: decision_payload.get(field)
            for field in wanted_fields
            if decision_payload.get(field) not in {None, ""}
        }
        payload.update({
            "event": "decision_risk_boundary",
            "mode": self._runtime_mode(),
            "risk_decision": risk_decision,
            "risk_state": risk_decision,
            "risk_block_reason": risk_block_reason,
            "candidate_block_stage": payload.get("candidate_block_stage") or (
                "risk_boundary" if risk_decision != "not_reached" else "pre_risk"
            ),
            "candidate_block_reason": payload.get("candidate_block_reason") or risk_block_reason,
            "risk_mode": self._risk_mode_state.current_mode.value,
            "available_risk_budget": decision_payload.get("remaining_risk_budget"),
            "risk_plan_present": risk_plan_present,
            "risk_approved": bool(risk_decision == "approved"),
            "risk_serialization_source": "decision_boundary_observability",
            "does_not_change_risk_decision": True,
            "run_id": str(getattr(getattr(self, "quant_events", None), "run_id", "") or ""),
        })
        # ENTRY_MODEL_TRUTH_ENVELOPE_V1 — carry from decision payload, observability-only
        if decision_payload.get("entry_model_truth_envelope_v1"):
            payload["entry_model_truth_envelope_v1"] = decision_payload["entry_model_truth_envelope_v1"]
        return self._display_payload_with_candidate_trace_identity(payload)

    def _regime_pass_through_fields(self, source: dict[str, object] | None) -> dict[str, object]:
        if not isinstance(source, dict):
            return {}
        fields: dict[str, object] = {}
        for key in REGIME_PAYLOAD_FIELD_NAMES:
            value = source.get(key)
            if value is None or str(value).strip() == "":
                continue
            fields[key] = value
        return fields

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
        decision_diagnostics = self._decision_diagnostics_payload(
            outcome,
            ticker=ticker or self._ticker_from_market_id(outcome.market_id),
        )
        decision_payload = {
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
            **decision_diagnostics,
            **self._regime_pass_through_fields(outcome.display),
        }
        phase1_decision_ts = str(decision_payload.get("decision_timestamp") or self._utc_timestamp())
        phase1_signal_ts = str((outcome.display or {}).get("signal_generated_ts") or phase1_decision_ts)
        decision_payload.setdefault("signal_generated_ts", phase1_signal_ts)
        decision_payload.setdefault("decision_complete_ts", phase1_decision_ts)
        decision_payload.setdefault("timestamp_source", "decision_emit")
        decision_payload.setdefault("latency_truth_level", "proxy")
        # Phase 4: quote lineage
        _p4_ticker = str(ticker or self._ticker_from_market_id(outcome.market_id) or "").upper()
        _p4_ql = self._phase4_build_quote_lineage(str(outcome.market_id or ""), _p4_ticker)
        decision_payload.setdefault("quote_lineage_id", _p4_ql.get("quote_lineage_id"))
        decision_payload.setdefault("quote_capture_ts", _p4_ql.get("quote_capture_ts"))
        decision_payload.setdefault("quote_snapshot_id", _p4_ql.get("quote_snapshot_id"))
        decision_payload.setdefault("quote_source", _p4_ql.get("quote_source", "unknown"))
        # ENTRY_MODEL_TRUTH_ENVELOPE_V1 — observability-only, additive
        decision_payload.update(
            self._build_entry_model_truth_envelope(
                true_probability=decision_payload.get("true_probability"),
                fair_value=decision_payload.get("fair_value"),
                ev_after_spread=decision_payload.get("ev_after_spread"),
                confidence=decision_payload.get("confidence"),
                model_probability_yes=decision_payload.get("model_probability_yes"),
                model_probability_no=decision_payload.get("model_probability_no"),
                selected_side=decision_payload.get("side") or decision_payload.get("outcome"),
                model_handoff_stage=decision_payload.get("model_handoff_stage"),
                probability_model_stage=decision_payload.get("probability_model_stage"),
                model_output_ready=decision_payload.get("probability_model_output_visible") or decision_payload.get("model_output_ready"),
                model_attempted=decision_payload.get("probability_model_called") or decision_payload.get("model_attempted"),
                model_not_run_reason=decision_payload.get("model_not_run_reason"),
                ev_missing_reason=decision_payload.get("ev_after_spread_null_reason") or decision_payload.get("ev_missing_reason"),
                computed_by="decision_log",
                serialization_source="phase2_observability_payload",
            )
        )
        risk_boundary_payload = self._risk_boundary_payload_from_decision(
            decision_payload,
            decision_type=decision_type,
            outcome=outcome,
        )
        if risk_boundary_payload is not None:
            self._emit_quant_event("log_risk_event", risk_boundary_payload)
        self._emit_quant_event("log_decision", decision_payload)
        # Hybrid v1: emit research snapshot after decision (observability-only, fail-soft)
        if getattr(self.settings, "hybrid_phase_v1_enabled", False):
            try:
                self._emit_hybrid_v1_snapshot(
                    ticker=ticker or self._ticker_from_market_id(outcome.market_id),
                    outcome=outcome,
                    timing_payload=decision_diagnostics,
                )
            except Exception:
                pass

    def _emit_hybrid_v1_snapshot(self, ticker: str, outcome: TradeOutcome, timing_payload: dict[str, object]) -> None:
        """
        Emits a hybrid observability snapshot combining research and live metrics.
        Includes Preload Next Market v1 observability fields.
        Offline-only research evidence — does not affect strategy, risk, or execution.
        """
        _next_market = self._preloaded_next_markets.get(ticker)
        # Base on timing_payload (decision_diagnostics) so readiness/timing fields are present,
        # then override with hybrid-specific snapshot keys.
        snapshot_payload = {
            **timing_payload,
            "ticker": ticker,
            "market_id": outcome.market_id,
            "actual_decision": outcome.decision,
            "actual_skip_reason": outcome.skip_reason or "",
            "preload_started_ts": self._preload_started_ts,
            "preload_success_ts": self._preload_success_ts,
            "preload_failed_reason": self._preload_failed_reason,
            "preload_lead_seconds": self._preload_lead_seconds,
            "preload_book_ready_ts": self._preload_book_ready_ts,
            "preloaded_market_id": _next_market.market_id if _next_market else None,
            "preloaded_condition_id": _next_market.condition_id if _next_market else None,
            "preloaded_epoch_start_ts": _next_market.epoch_start_ts if _next_market else None,
            "shadow_inventory": {
                "theoretical_decision": "HOLD" if outcome.skipped else "WOULD_OPEN",
                "scope": "shadow_research_v1",
                "offline_only": True,
            },
        }
        # Orderbook Snapshot Truth Probe v1: raw display-path values at snapshot time.
        # These let us compare research_log depth against the live display/orderbook path
        # to determine whether EMPTY depth is a real market condition or a data-path lag.
        _display = outcome.display or {}
        snapshot_payload["snapshot_bid"] = float(_display.get("yes_bid", 0.0) or 0.0)
        snapshot_payload["snapshot_ask"] = float(_display.get("yes_ask", 0.0) or 0.0)
        snapshot_payload["snapshot_spread"] = float(_display.get("spread", 0.0) or 0.0)
        snapshot_payload["snapshot_best_bid_size"] = float(_display.get("yes_bid_size", 0.0) or 0.0)
        snapshot_payload["snapshot_best_ask_size"] = float(_display.get("yes_ask_size", 0.0) or 0.0)
        snapshot_payload["snapshot_orderbook_source"] = str(_display.get("orderbook_refresh_source", "") or "")
        snapshot_payload["snapshot_orderbook_age_ms"] = int(_display.get("orderbook_age_ms", 0) or 0)
        snapshot_payload["snapshot_orderbook_empty_reason"] = str(_display.get("orderbook_readiness_reason", "") or "")
        # Lifecycle Latency Observatory v1: record decision_complete_ts in bucket then compute ms durations.
        # Fail-soft — any error silently skips latency fields.
        try:
            _resolved_ticker = ticker or self._ticker_from_market_id(outcome.market_id)
            _epoch = int(
                (outcome.display or {}).get(
                    "market_epoch_start",
                    (outcome.display or {}).get("epoch_start", (outcome.display or {}).get("epoch_start_ts", 0)),
                ) or 0
            )
            if _epoch > 0:
                _bucket = self._phase2_readiness_store().setdefault(
                    (_resolved_ticker.upper(), _epoch), {}
                )
                if not _bucket.get("decision_complete_ts"):
                    _bucket["decision_complete_ts"] = self._utc_timestamp()
                _latency = self._compute_lifecycle_latency_ms(_bucket)
                snapshot_payload.update(_latency)
        except Exception:
            pass
        self._emit_quant_event("log_research_snapshot", snapshot_payload)

    @staticmethod
    def _build_paper_trade_replay_key(
        *,
        condition_id: object,
        epoch_start_ts: object,
        ticker: object,
        outcome: object,
        token_id: object,
    ) -> str:
        try:
            epoch = int(epoch_start_ts or 0)
        except (TypeError, ValueError):
            epoch = 0
        condition_text = str(condition_id or "")
        outcome_text = str(outcome or "")
        token_text = str(token_id or "")
        ticker_text = str(ticker or "")
        if condition_text and epoch and outcome_text and token_text:
            return f"{condition_text}|{epoch}|{ticker_text}|{outcome_text}|{token_text}"
        return ""

    def _build_entry_model_truth_envelope(
        self,
        *,
        true_probability: object = None,
        fair_value: object = None,
        ev_after_spread: object = None,
        confidence: object = None,
        model_probability_yes: object = None,
        model_probability_no: object = None,
        selected_side: object = None,
        model_handoff_stage: object = None,
        probability_model_stage: object = None,
        model_output_ready: object = None,
        model_attempted: object = None,
        model_not_run_reason: object = None,
        ev_missing_reason: object = None,
        computed_by: str = "unknown",
        serialization_source: str = "unknown",
    ) -> dict[str, object]:
        # ENTRY_MODEL_TRUTH_ENVELOPE_V1 — observability-only, additive, fail-soft
        try:
            def _sf(v: object) -> "float | None":
                if v is None or v == "":
                    return None
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return None

            p_true = _sf(true_probability)
            fv = _sf(fair_value)
            ev = _sf(ev_after_spread)
            conf = _sf(confidence)
            p_yes = _sf(model_probability_yes)
            p_no = _sf(model_probability_no)
            side_str = str(selected_side).upper() if selected_side else ""

            if p_true is not None and ev is not None:
                truth_status = "full"
            elif p_true is not None:
                truth_status = "probability_only"
            elif ev is not None:
                truth_status = "ev_only"
            else:
                truth_status = "absent"

            _model_output_ready: bool = (
                bool(model_output_ready)
                if model_output_ready is not None
                else (p_true is not None or fv is not None)
            )
            _model_attempted: bool = (
                bool(model_attempted)
                if model_attempted is not None
                else (p_true is not None or ev is not None)
            )
            _ev_missing_reason = (
                str(ev_missing_reason)
                if ev_missing_reason
                else ("" if ev is not None else "ev_not_available")
            )
            return {
                "entry_model_truth_envelope_v1": {
                    "schema_version": "1.0",
                    "truth_status": truth_status,
                    "truth_source": str(serialization_source),
                    "producer_stage": str(computed_by),
                    "model_output_ready": _model_output_ready,
                    "model_attempted": _model_attempted,
                    "model_not_run_reason": str(model_not_run_reason) if model_not_run_reason else "",
                    "probability_model_stage": str(probability_model_stage) if probability_model_stage else "",
                    "model_handoff_stage": str(model_handoff_stage) if model_handoff_stage else "",
                    "model_probability_yes": p_yes,
                    "model_probability_no": p_no,
                    "selected_side": side_str,
                    "true_probability": p_true,
                    "fair_value": fv,
                    "ev_after_spread": ev,
                    "expected_value": ev,
                    "confidence": conf,
                    "ev_missing_reason": _ev_missing_reason,
                    "lineage_reference_only": True,
                    "computed_at": self._utc_timestamp(),
                    "computed_by": str(computed_by),
                    "serialization_source": str(serialization_source),
                }
            }
        except Exception:
            return {}

    def _carry_entry_model_truth_from_metadata(
        self,
        metadata: dict,
    ) -> dict[str, object]:
        # ENTRY_MODEL_TRUTH_ENVELOPE_V1 — observability-only, carry from position metadata, fail-soft
        try:
            envelope = metadata.get("entry_model_truth_envelope_v1")
            if not isinstance(envelope, dict):
                return {"entry_model_truth_carry_status": "absent_in_metadata"}
            carried = dict(envelope)
            carried["carried_from"] = "position_metadata"
            return {"entry_model_truth_envelope_v1": carried}
        except Exception:
            return {}

    def _build_trade_position_metadata(
        self,
        *,
        strategy: object,
        signal_strategy: object,
        token_id: object,
        outcome: object,
        entry_ev: object,
        confidence: object,
        delta_regime: object,
        condition_id: object,
        epoch_start_ts: object,
        market_slug: object,
        lifecycle_phase: object,
        ticker: object,
        true_probability: object = None,
        fair_value: object = None,
        signal_name: object = None,
        signal_reason: object = None,
        strategy_signal_name: object = None,
        strategy_signal_reason: object = None,
    ) -> dict[str, object]:
        paper_trade_replay_key = self._build_paper_trade_replay_key(
            condition_id=condition_id,
            epoch_start_ts=epoch_start_ts,
            ticker=ticker,
            outcome=outcome,
            token_id=token_id,
        )
        # ENTRY_MODEL_TRUTH_ENVELOPE_V1 — observability-only, additive
        _envelope = self._build_entry_model_truth_envelope(
            true_probability=true_probability,
            fair_value=fair_value,
            ev_after_spread=entry_ev,
            confidence=confidence,
            selected_side=outcome,
            computed_by="position_metadata",
            serialization_source="build_trade_position_metadata",
        ).get("entry_model_truth_envelope_v1")
        ticker_key = str(ticker or "").upper()
        quant_details = getattr(self, "last_quant_details", {}).get(ticker_key, {})
        entry_attribution = {
            "candidate_id": quant_details.get("candidate_id"),
            "candidate_trace_id": quant_details.get("candidate_trace_id"),
            "candidate_instance_id": quant_details.get("candidate_instance_id"),
            "candidate_instance_trace_id": quant_details.get("candidate_instance_trace_id"),
            "candidate_instance_created_at": quant_details.get("candidate_instance_created_at"),
            "candidate_instance_identity_schema_version": quant_details.get("candidate_instance_identity_schema_version"),
            "candidate_instance_identity_source": quant_details.get("candidate_instance_identity_source"),
            "legacy_candidate_identity_source": quant_details.get("legacy_candidate_identity_source"),
            "signal_name": quant_details.get("signal_name") or signal_name,
            "signal_reason": quant_details.get("signal_reason") or signal_reason,
            "paper_trade_replay_key": paper_trade_replay_key or None,
            "entry_ev": float(entry_ev) if entry_ev is not None else (float(quant_details.get("entry_ev")) if quant_details.get("entry_ev") is not None else None),
            "entry_probability": float(true_probability) if true_probability is not None else (float(quant_details.get("true_probability")) if quant_details.get("true_probability") is not None else None),
            "selected_side": str(outcome or ""),
        }
        return {
            "strategy": strategy,
            "signal_strategy": signal_strategy,
            "token_id": token_id,
            "outcome": outcome,
            "entry_ev": entry_ev,
            "confidence": confidence,
            "delta_regime": delta_regime,
            "condition_id": condition_id,
            "epoch_start_ts": epoch_start_ts,
            "market_slug": market_slug,
            "lifecycle_phase": lifecycle_phase,
            "paper_trade_replay_key": paper_trade_replay_key or None,
            "entry_model_truth_envelope_v1": _envelope,
            "signal_name": signal_name,
            "signal_reason": signal_reason,
            "strategy_signal_name": strategy_signal_name,
            "strategy_signal_reason": strategy_signal_reason,
            "entry_attribution": entry_attribution,
        }

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
        seconds_remaining: int | None = None,
        epoch_start: int | None = None,
        condition_id: str = "",
        true_probability: float | None = None,
        fair_value: float | None = None,
        ev_after_spread: float | None = None,
        confidence: float | None = None,
        position_id: str | None = None,
        entry_attribution: dict[str, object] | None = None,
    ) -> None:
        model_context = {}
        last_quant_details = getattr(self, "last_quant_details", {})
        if isinstance(last_quant_details, dict):
            candidate_context = last_quant_details.get(str(ticker or "").upper(), {})
            if isinstance(candidate_context, dict):
                model_context = candidate_context
        if entry_attribution is None and isinstance(model_context, dict):
            entry_attribution = model_context.get("entry_attribution")

        def first_available(*values: object) -> object:
            for value in values:
                if self._phase2_value_available(value):
                    return value
            return None

        outcome_upper = str(outcome or "").upper()
        model_p_yes = first_available(
            model_context.get("model_probability_yes"),
            model_context.get("p_yes"),
            model_context.get("model_p_yes"),
            model_context.get("fair_value_yes"),
        )
        model_p_no = first_available(
            model_context.get("model_probability_no"),
            model_context.get("p_no"),
            model_context.get("model_p_no"),
            model_context.get("fair_value_no"),
        )
        selected_probability = first_available(true_probability, model_context.get("true_probability"))
        if selected_probability is None:
            if outcome_upper == "YES":
                selected_probability = model_p_yes
            elif outcome_upper == "NO":
                selected_probability = model_p_no
        selected_fair_value = first_available(fair_value, model_context.get("fair_value"))
        if selected_fair_value is None:
            if outcome_upper == "YES":
                selected_fair_value = first_available(model_context.get("fair_value_yes"), model_p_yes)
            elif outcome_upper == "NO":
                selected_fair_value = first_available(model_context.get("fair_value_no"), model_p_no)
        if selected_fair_value is None:
            selected_fair_value = selected_probability
        selected_ev = first_available(
            ev_after_spread,
            model_context.get("ev_after_spread"),
            model_context.get("expected_value"),
            model_context.get("ev"),
            model_context.get("edge"),
        )
        selected_confidence = first_available(confidence, model_context.get("confidence"))
        model_output_visible = any(
            self._phase2_value_available(value)
            for value in (selected_probability, selected_fair_value, model_p_yes, model_p_no)
        )
        phase2_detail = self._phase2_observability_payload(
            ticker=ticker,
            market_id=market_id,
            side=outcome,
            epoch_start=epoch_start,
            seconds_remaining=seconds_remaining,
            market_price=entry_price,
            fair_value=selected_fair_value,
            true_probability=selected_probability,
            ev_after_spread=selected_ev,
            skip_reason="",
            risk_plan=None,
        )
        if model_output_visible:
            phase2_detail.update({
                "model_output_ready": True,
                "model_attempted": True,
                "probability_model_called": True,
                "probability_model_output_visible": True,
                "probability_model_stage": "probability_model_output",
                "probability_model_gate_reason": "model_output_visible",
                "model_not_run_reason": "",
                "model_output_missing_reason": "",
                "model_handoff_stage": "MODEL_OUTPUT_SERIALIZED",
            })
        if self._phase2_value_available(model_p_yes):
            phase2_detail.update({
                "p_yes": model_p_yes,
                "model_p_yes": model_p_yes,
                "model_probability_yes": model_p_yes,
                "fair_value_yes": first_available(model_context.get("fair_value_yes"), model_p_yes),
            })
        if self._phase2_value_available(model_p_no):
            phase2_detail.update({
                "p_no": model_p_no,
                "model_p_no": model_p_no,
                "model_probability_no": model_p_no,
                "fair_value_no": first_available(model_context.get("fair_value_no"), model_p_no),
            })
        exposure_after = float(phase2_detail.get("exposure_after", 0.0) or 0.0)
        exposure_before = max(exposure_after - float(risk_plan.notional_size), 0.0)
        phase2_detail.update({
            "exposure_before": exposure_before,
            "risk_budget_used": exposure_before,
        })
        epoch_start_ts = int(epoch_start or 0)
        paper_trade_replay_key = self._build_paper_trade_replay_key(
            condition_id=condition_id,
            epoch_start_ts=epoch_start_ts,
            ticker=ticker,
            outcome=outcome,
            token_id=token_id,
        )
        open_payload = {
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
                "condition_id": condition_id or "",
                "epoch_start_ts": epoch_start_ts,
                "asset": ticker,
                "paper_trade_replay_key": paper_trade_replay_key,
                "candidate_peak_favorable": None,
                "candidate_peak_adverse": None,
                "signal_name": model_context.get("signal_name"),
                "signal_reason": model_context.get("signal_reason"),
                "strategy_signal_name": model_context.get("strategy_signal_name"),
                "strategy_signal_reason": model_context.get("strategy_signal_reason"),
                "position_id": position_id,
                "entry_attribution": entry_attribution,
                "entry_attribution_status": "success" if isinstance(entry_attribution, dict) else "missing",
                **phase2_detail,
                "true_probability": selected_probability,
                "fair_value": selected_fair_value,
                "ev_after_spread": selected_ev,
                "expected_value": selected_ev,
                "ev": selected_ev,
                "confidence": selected_confidence,
                # ENTRY_MODEL_TRUTH_ENVELOPE_V1 — observability-only, additive
                **self._build_entry_model_truth_envelope(
                    true_probability=selected_probability,
                    fair_value=selected_fair_value,
                    ev_after_spread=selected_ev,
                    confidence=selected_confidence,
                    model_probability_yes=model_p_yes,
                    model_probability_no=model_p_no,
                    selected_side=outcome,
                    model_handoff_stage=phase2_detail.get("model_handoff_stage"),
                    probability_model_stage=phase2_detail.get("probability_model_stage"),
                    model_output_ready=model_output_visible,
                    model_attempted=phase2_detail.get("probability_model_called") or phase2_detail.get("model_attempted"),
                    model_not_run_reason=phase2_detail.get("model_not_run_reason"),
                    ev_missing_reason=phase2_detail.get("ev_after_spread_null_reason") or phase2_detail.get("ev_missing_reason"),
                    computed_by="trade_open_context",
                    serialization_source="last_quant_details",
                ),
        }
        if isinstance(entry_attribution, dict):
            for field in ("candidate_id", "candidate_instance_id", "paper_trade_replay_key", "signal_name", "signal_reason"):
                if field in entry_attribution:
                    open_payload[field] = entry_attribution[field]
        self._emit_quant_event("log_trade_open", open_payload)

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
        exit_ts = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        ticker = self._ticker_from_market_id(getattr(position, "symbol", ""))
        token_id = self._position_token_id(position)
        outcome = self._position_outcome(position)
        metadata = getattr(position, "metadata", None) or {}
        condition_id = str(metadata.get("condition_id", "") or "")
        epoch_start_ts = int(metadata.get("epoch_start_ts", 0) or 0)
        hold_seconds: int | None = None
        entry_time_raw = getattr(position, "entry_time", None)
        if entry_time_raw:
            try:
                entry_dt = datetime.fromisoformat(str(entry_time_raw).replace("Z", "+00:00"))
                exit_dt = datetime.fromisoformat(exit_ts.replace("Z", "+00:00"))
                hold_seconds = int((exit_dt - entry_dt).total_seconds())
            except Exception:
                pass
        paper_trade_replay_key = self._build_paper_trade_replay_key(
            condition_id=condition_id,
            epoch_start_ts=epoch_start_ts,
            ticker=ticker,
            outcome=outcome,
            token_id=token_id,
        )
        # Outcome truth fields (observability only, additive)
        try:
            _reason_lower = str(reason or "").lower()
            if _reason_lower.startswith("take_profit"):
                _trade_result: str | None = "TP"
            elif _reason_lower.startswith("stop_loss"):
                _trade_result = "SL"
            elif float(pnl) > 0:
                _trade_result = "WIN"
            elif float(pnl) < 0:
                _trade_result = "LOSS"
            else:
                _trade_result = "UNKNOWN"
        except Exception:
            _trade_result = None
        try:
            _entry_price: float | None = float(getattr(position, "entry_price", None) or 0.0) or None
        except Exception:
            _entry_price = None
        close_payload = {
            "position_id": getattr(position, "position_id", ""),
            "market_id": getattr(position, "symbol", ""),
            "ticker": ticker,
            "token_id": token_id,
            "outcome": outcome,
            "reason": reason,
            "exit_price": float(exit_price),
            "exit_timestamp": exit_ts,
            "hold_seconds": hold_seconds,
            "size": float(size),
            "pnl": float(pnl),
            "pnl_usdc": float(pnl),
            "trade_result": _trade_result,
            "entry_price": _entry_price,
            "partial": bool(partial),
            "receipt": asdict(receipt) if receipt else {},
            "mode": self._runtime_mode(),
            "condition_id": condition_id,
            "epoch_start_ts": epoch_start_ts,
            "asset": ticker,
            "paper_trade_replay_key": paper_trade_replay_key,
            "candidate_peak_favorable": None,
            "candidate_peak_adverse": None,
            "signal_name": metadata.get("signal_name"),
            "signal_reason": metadata.get("signal_reason"),
            "strategy_signal_name": metadata.get("strategy_signal_name"),
            "strategy_signal_reason": metadata.get("strategy_signal_reason"),
            # ENTRY_MODEL_TRUTH_ENVELOPE_V1 — carry from position metadata, observability-only
            **self._carry_entry_model_truth_from_metadata(metadata),
        }
        attribution = metadata.get("entry_attribution")
        if isinstance(attribution, dict):
            close_payload["entry_attribution"] = attribution
            close_payload["entry_attribution_status"] = "success"
            for field in ("candidate_id", "candidate_instance_id", "paper_trade_replay_key", "signal_name", "signal_reason"):
                if field in attribution:
                    close_payload[field] = attribution[field]
        else:
            close_payload["entry_attribution_status"] = "missing_legacy"

        self._emit_quant_event("log_trade_close", close_payload)

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
                **self._bankroll_tier_detail(),
                **self._bankroll_mode_detail(),
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
                **self._bankroll_tier_detail(),
                **self._bankroll_mode_detail(),
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
        epoch_start_int = self._diagnostic_int(epoch_start) or 0
        epoch_end_int = int(getattr(ptb_info, "epoch_end_ts", 0) or 0)
        if epoch_end_int <= 0 and epoch_start_int > 0:
            epoch_end_int = epoch_start_int + 300
        ticker = self._ticker_from_market_id(getattr(market, "market_id", ""))
        token_ids = self._real_token_ids.get(ticker)
        alignment_detail = self._active_window_alignment_detail(
            ticker=ticker,
            epoch_start=epoch_start_int,
            epoch_end=epoch_end_int,
            seconds_remaining=self._diagnostic_int(raw_seconds),
            token_ids=token_ids,
        )
        return {
            "seconds_remaining": self._diagnostic_int(raw_seconds),
            "entry_cutoff_seconds": self._diagnostic_int(raw_cutoff),
            "time_bucket": classify_time_bucket(raw_seconds, raw_cutoff),
            "epoch_start": epoch_start_int,
            "market_start_time": market_start_time,
            "market_end_time": market_end_time,
            "market_close_timestamp": market_end_time,
            **alignment_detail,
        }

    def _entry_hard_block_seconds(self) -> int:
        hard_block = max(
            int(self._setting("adaptive_entry_hard_block_seconds", 45)),
            int(self._setting("entry_min_seconds_remaining", 30)),
            int(self._setting("exit_agent_entry_cutoff_seconds", 45)),
            int(self._setting("exit_agent_cancel_entries_seconds", 35)),
            int(self._setting("exit_agent_force_exit_seconds", 25)),
        )
        if not self._paper_enabled():
            hard_block = max(hard_block, int(self._setting("execution_force_exit_seconds", 60)))
        return hard_block

    def _micro_adaptive_timing_active(self) -> bool:
        if not bool(getattr(self.settings, "paper_trading", True)):
            return False
        if not bool(self._setting("micro_adaptive_timing_enabled", True)):
            return False
        try:
            return get_tier_config(self.bankroll_state.current_bankroll_tier).family == "MICRO"
        except Exception:
            return False

    def _micro_adaptive_timing_skipped_reason(self) -> str:
        if not bool(getattr(self.settings, "paper_trading", True)):
            return "live_mode"
        if not bool(self._setting("micro_adaptive_timing_enabled", True)):
            return "disabled"
        try:
            tier_config = get_tier_config(self.bankroll_state.current_bankroll_tier)
        except Exception:
            return "tier_unknown"
        if tier_config.family != "MICRO":
            return "non_micro_tier"
        return ""

    def _micro_hard_close_floor_seconds(self) -> int:
        configured = int(self._setting("micro_hard_close_floor_seconds", 35))
        return max(
            configured,
            int(self._setting("entry_min_seconds_remaining", 30)),
            int(self._setting("exit_agent_force_exit_seconds", 25)),
            int(self._setting("exit_agent_residual_sweep_seconds", 15)),
            int(self._setting("exit_agent_emergency_flatten_seconds", 10)),
        )

    def _micro_adaptive_cutoff_seconds(self) -> int:
        return max(
            self._micro_hard_close_floor_seconds(),
            int(self._setting("micro_adaptive_window_min_seconds", 35)),
        )

    def _adaptive_entry_cutoff_seconds(self) -> int:
        return max(
            self._entry_hard_block_seconds(),
            int(self._setting("adaptive_entry_cutoff_seconds", 45)),
        )

    def _cutoff_decision_detail(self, decision: AdaptiveEntryCutoffDecision) -> dict[str, object]:
        return {
            "effective_cutoff_seconds": int(decision.effective_cutoff_seconds),
            "cutoff_policy": decision.policy,
            "adaptive_cutoff_allowed": bool(decision.allowed and decision.policy == "adaptive"),
            "adaptive_cutoff_reason": decision.reason,
            "adaptive_cutoff_denied_reason": decision.reason if decision.policy == "adaptive" and not decision.allowed else "",
            "late_entry_hard_block": bool(decision.late_entry_hard_block),
            "micro_timing_allowed": bool(decision.micro_timing_allowed),
            "micro_timing_denied_reason": decision.micro_timing_denied_reason,
            "effective_micro_cutoff_seconds": int(decision.effective_micro_cutoff_seconds),
            "micro_cutoff_policy": decision.micro_cutoff_policy,
            "micro_timing_branch_entered": bool(decision.micro_timing_branch_entered),
            "micro_timing_branch_skipped_reason": decision.micro_timing_branch_skipped_reason,
            "micro_timing_candidate": bool(decision.micro_timing_candidate),
        }

    def _entry_cutoff_skip_reason(self, seconds_remaining: int, decision: AdaptiveEntryCutoffDecision) -> str:
        if decision.late_entry_hard_block:
            label = "hard block"
        elif decision.policy == "micro_adaptive":
            label = "micro adaptive denied"
        else:
            label = "adaptive denied"
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
        liquidity_state: str = "HEALTHY",
    ) -> AdaptiveEntryCutoffDecision:
        micro_timing_active = self._micro_adaptive_timing_active()
        micro_cutoff = self._micro_adaptive_cutoff_seconds() if micro_timing_active else 0
        policy = "micro_adaptive" if micro_timing_active else "adaptive"
        micro_timing_candidate = bool(micro_timing_active and seconds_remaining <= static_cutoff_seconds)
        micro_branch_skipped_reason = "" if micro_timing_active else self._micro_adaptive_timing_skipped_reason()
        hard_block = self._micro_hard_close_floor_seconds() if micro_timing_active else self._entry_hard_block_seconds()
        if seconds_remaining <= hard_block:
            return AdaptiveEntryCutoffDecision(
                allowed=False,
                policy=policy if bool(self._setting("adaptive_entry_cutoff_enabled", True)) else "static",
                effective_cutoff_seconds=hard_block,
                reason="hard_close_zone",
                late_entry_hard_block=True,
                micro_timing_denied_reason="hard_close_zone" if micro_timing_active else "",
                effective_micro_cutoff_seconds=micro_cutoff,
                micro_cutoff_policy=policy if micro_timing_active else "standard",
                micro_timing_branch_entered=micro_timing_candidate,
                micro_timing_branch_skipped_reason=micro_branch_skipped_reason,
                micro_timing_candidate=micro_timing_candidate,
            )

        if seconds_remaining > static_cutoff_seconds:
            return AdaptiveEntryCutoffDecision(
                allowed=True,
                policy="static",
                effective_cutoff_seconds=static_cutoff_seconds,
                reason="static_safe",
                micro_timing_allowed=micro_timing_active,
                effective_micro_cutoff_seconds=micro_cutoff,
                micro_cutoff_policy="static" if micro_timing_active else "standard",
                micro_timing_branch_entered=False,
                micro_timing_branch_skipped_reason=micro_branch_skipped_reason,
                micro_timing_candidate=False,
            )

        if not bool(self._setting("adaptive_entry_cutoff_enabled", True)):
            return AdaptiveEntryCutoffDecision(
                allowed=False,
                policy="static",
                effective_cutoff_seconds=static_cutoff_seconds,
                reason="static_cutoff",
                micro_timing_denied_reason="static_cutoff" if micro_timing_active else "",
                effective_micro_cutoff_seconds=micro_cutoff,
                micro_cutoff_policy="static" if micro_timing_active else "standard",
                micro_timing_branch_entered=micro_timing_candidate,
                micro_timing_branch_skipped_reason=micro_branch_skipped_reason,
                micro_timing_candidate=micro_timing_candidate,
            )

        effective_cutoff = micro_cutoff if micro_timing_active else self._adaptive_entry_cutoff_seconds()
        if seconds_remaining <= effective_cutoff:
            reason = "micro_adaptive_window_floor" if micro_timing_active else "adaptive_cutoff_floor"
            return AdaptiveEntryCutoffDecision(
                allowed=False,
                policy=policy,
                effective_cutoff_seconds=effective_cutoff,
                reason=reason,
                micro_timing_denied_reason=reason if micro_timing_active else "",
                effective_micro_cutoff_seconds=micro_cutoff,
                micro_cutoff_policy=policy if micro_timing_active else "standard",
                micro_timing_branch_entered=micro_timing_candidate,
                micro_timing_branch_skipped_reason=micro_branch_skipped_reason,
                micro_timing_candidate=micro_timing_candidate,
            )

        if self._risk_mode_state.current_mode == RiskMode.LOCKDOWN:
            return AdaptiveEntryCutoffDecision(False, policy, effective_cutoff, "lockdown", micro_timing_denied_reason="lockdown" if micro_timing_active else "", effective_micro_cutoff_seconds=micro_cutoff, micro_cutoff_policy=policy if micro_timing_active else "standard", micro_timing_branch_entered=micro_timing_candidate, micro_timing_branch_skipped_reason=micro_branch_skipped_reason, micro_timing_candidate=micro_timing_candidate)

        if not self._reconciliation_safe_for_entry():
            return AdaptiveEntryCutoffDecision(False, policy, effective_cutoff, "reconciliation_block", micro_timing_denied_reason="reconciliation_block" if micro_timing_active else "", effective_micro_cutoff_seconds=micro_cutoff, micro_cutoff_policy=policy if micro_timing_active else "standard", micro_timing_branch_entered=micro_timing_candidate, micro_timing_branch_skipped_reason=micro_branch_skipped_reason, micro_timing_candidate=micro_timing_candidate)

        if micro_timing_active and str(liquidity_state or "").upper() not in {"", "HEALTHY"}:
            return AdaptiveEntryCutoffDecision(False, policy, effective_cutoff, "liquidity_not_healthy", micro_timing_denied_reason="liquidity_not_healthy", effective_micro_cutoff_seconds=micro_cutoff, micro_cutoff_policy=policy, micro_timing_branch_entered=micro_timing_candidate, micro_timing_candidate=micro_timing_candidate)

        max_orderbook_age_ms = int(self._setting("adaptive_entry_max_orderbook_age_ms", 1000))
        if orderbook_age_ms is None:
            return AdaptiveEntryCutoffDecision(False, policy, effective_cutoff, "orderbook_age_unknown", micro_timing_denied_reason="orderbook_age_unknown" if micro_timing_active else "", effective_micro_cutoff_seconds=micro_cutoff, micro_cutoff_policy=policy if micro_timing_active else "standard", micro_timing_branch_entered=micro_timing_candidate, micro_timing_branch_skipped_reason=micro_branch_skipped_reason, micro_timing_candidate=micro_timing_candidate)
        if orderbook_age_ms > max_orderbook_age_ms:
            return AdaptiveEntryCutoffDecision(False, policy, effective_cutoff, "orderbook_stale", micro_timing_denied_reason="orderbook_stale" if micro_timing_active else "", effective_micro_cutoff_seconds=micro_cutoff, micro_cutoff_policy=policy if micro_timing_active else "standard", micro_timing_branch_entered=micro_timing_candidate, micro_timing_branch_skipped_reason=micro_branch_skipped_reason, micro_timing_candidate=micro_timing_candidate)

        max_oracle_age_ms = int(self._setting("adaptive_entry_max_oracle_age_ms", 5000))
        if oracle_age_ms is None:
            return AdaptiveEntryCutoffDecision(False, policy, effective_cutoff, "oracle_age_unknown", micro_timing_denied_reason="oracle_age_unknown" if micro_timing_active else "", effective_micro_cutoff_seconds=micro_cutoff, micro_cutoff_policy=policy if micro_timing_active else "standard", micro_timing_branch_entered=micro_timing_candidate, micro_timing_branch_skipped_reason=micro_branch_skipped_reason, micro_timing_candidate=micro_timing_candidate)
        if oracle_age_ms > max_oracle_age_ms:
            return AdaptiveEntryCutoffDecision(False, policy, effective_cutoff, "oracle_stale", micro_timing_denied_reason="oracle_stale" if micro_timing_active else "", effective_micro_cutoff_seconds=micro_cutoff, micro_cutoff_policy=policy if micro_timing_active else "standard", micro_timing_branch_entered=micro_timing_candidate, micro_timing_branch_skipped_reason=micro_branch_skipped_reason, micro_timing_candidate=micro_timing_candidate)

        max_decision_latency_ms = int(self._setting("adaptive_entry_max_decision_latency_ms", 2000))
        if decision_latency_ms is not None and decision_latency_ms > max_decision_latency_ms:
            return AdaptiveEntryCutoffDecision(False, policy, effective_cutoff, "decision_latency_high", micro_timing_denied_reason="decision_latency_high" if micro_timing_active else "", effective_micro_cutoff_seconds=micro_cutoff, micro_cutoff_policy=policy if micro_timing_active else "standard", micro_timing_branch_entered=micro_timing_candidate, micro_timing_branch_skipped_reason=micro_branch_skipped_reason, micro_timing_candidate=micro_timing_candidate)

        max_cycle_duration_ms = int(self._setting("adaptive_entry_max_cycle_duration_ms", 2500))
        if scan_cycle_duration_ms is not None and scan_cycle_duration_ms > max_cycle_duration_ms:
            return AdaptiveEntryCutoffDecision(False, policy, effective_cutoff, "cycle_latency_high", micro_timing_denied_reason="cycle_latency_high" if micro_timing_active else "", effective_micro_cutoff_seconds=micro_cutoff, micro_cutoff_policy=policy if micro_timing_active else "standard", micro_timing_branch_entered=micro_timing_candidate, micro_timing_branch_skipped_reason=micro_branch_skipped_reason, micro_timing_candidate=micro_timing_candidate)

        max_spread = float(self._setting("adaptive_entry_max_spread", 0.06))
        if spread > max_spread:
            return AdaptiveEntryCutoffDecision(False, policy, effective_cutoff, "spread_too_wide", micro_timing_denied_reason="spread_too_wide" if micro_timing_active else "", effective_micro_cutoff_seconds=micro_cutoff, micro_cutoff_policy=policy if micro_timing_active else "standard", micro_timing_branch_entered=micro_timing_candidate, micro_timing_branch_skipped_reason=micro_branch_skipped_reason, micro_timing_candidate=micro_timing_candidate)

        return AdaptiveEntryCutoffDecision(
            allowed=True,
            policy=policy,
            effective_cutoff_seconds=effective_cutoff,
            reason="micro_healthy_late_entry" if micro_timing_active else "healthy_late_entry",
            micro_timing_allowed=micro_timing_active,
            effective_micro_cutoff_seconds=micro_cutoff,
            micro_cutoff_policy=policy if micro_timing_active else "standard",
            micro_timing_branch_entered=micro_timing_candidate,
            micro_timing_branch_skipped_reason=micro_branch_skipped_reason,
            micro_timing_candidate=micro_timing_candidate,
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

    def _record_quant_detail(self, ticker_symbol: str = "", **values: object) -> dict[str, object]:
        ticker = str(ticker_symbol or values.get("ticker") or values.get("asset") or "UNKNOWN").upper()
        detail = self.last_quant_details.get(ticker, {"ticker": ticker})
        scheduler_detail = self._scheduler_cadence_observability_detail(ticker)
        market_id = str(
            values.get("market_id")
            or values.get("best_market")
            or detail.get("market_id")
            or f"pm-5m-{ticker.lower()}"
        )
        side = str(values.get("side") or values.get("best_side") or values.get("outcome") or detail.get("side") or "")
        market_price = values.get("market_price", values.get("ask_price", values.get("entry_price")))
        current_model_output_visible = any(
            self._phase2_value_available(values.get(key))
            for key in (
                "p_yes",
                "p_no",
                "model_p_yes",
                "model_p_no",
                "model_probability_yes",
                "model_probability_no",
                "true_probability",
                "fair_value",
            )
        )
        current_model_called = bool(values.get("probability_model_called")) or current_model_output_visible
        model_p_yes = values.get("model_probability_yes", values.get("p_yes", values.get("model_p_yes", detail.get("model_probability_yes", detail.get("p_yes")))))
        model_p_no = values.get("model_probability_no", values.get("p_no", values.get("model_p_no", detail.get("model_probability_no", detail.get("p_no")))))
        fair_value = values.get("fair_value")
        true_probability = values.get("true_probability")
        if fair_value is None or true_probability is None:
            side_upper = side.upper()
            if side_upper == "YES":
                fair_value = model_p_yes if fair_value is None else fair_value
                true_probability = fair_value if true_probability is None else true_probability
            elif side_upper == "NO":
                fair_value = model_p_no if fair_value is None else fair_value
                true_probability = fair_value if true_probability is None else true_probability
        ev_after_spread = values.get("ev_after_spread", values.get("ev", values.get("edge")))
        detail.update(
            self._phase2_observability_payload(
                ticker=ticker,
                market_id=market_id,
                side=side,
                epoch_start=values.get("market_epoch_start", values.get("epoch_start", values.get("epoch_start_ts"))),
                seconds_remaining=values.get("seconds_remaining", values.get("seconds_until_close")),
                market_price=market_price,
                fair_value=fair_value,
                true_probability=true_probability,
                ev_after_spread=ev_after_spread,
                skip_reason=values.get("normalized_skip_reason", values.get("raw_skip_reason", values.get("skip_reason", ""))),
                orderbook_readiness_reason=values.get("orderbook_readiness_reason", values.get("orderbook_unavailable_reason", "")),
                liquidity_state=values.get("liquidity_state", ""),
                spread_normalized=values.get("spread_normalized"),
            )
        )
        detail.update(scheduler_detail)
        detail.update(values)
        if "p_yes" in values:
            detail["model_p_yes"] = values["p_yes"]
        if "p_no" in values:
            detail["model_p_no"] = values["p_no"]
        model_output_visible = self._phase2_value_available(model_p_yes) or self._phase2_value_available(model_p_no)
        detail["probability_model_called"] = bool(detail.get("probability_model_called")) or current_model_called
        detail["probability_model_output_visible"] = bool(model_output_visible)
        if model_output_visible:
            if self._phase2_value_available(model_p_yes):
                detail["model_probability_yes"] = model_p_yes
                detail["fair_value_yes"] = model_p_yes
            if self._phase2_value_available(model_p_no):
                detail["model_probability_no"] = model_p_no
                detail["fair_value_no"] = model_p_no
            detail["model_attempted"] = True
            detail["probability_model_stage"] = "probability_model_output"
            detail["probability_model_gate_reason"] = "model_output_visible"
            detail["model_not_run_reason"] = ""
            detail["true_probability_available"] = True
            detail["fair_value_available"] = True
            detail["true_probability_null_reason"] = ""
            detail["fair_value_null_reason"] = ""
            detail["model_handoff_stage"] = "MODEL_OUTPUT_SERIALIZED"
            detail["model_output_missing_reason"] = ""
            detail["model_output_source"] = (
                "current_probability_model_result"
                if current_model_output_visible
                else "cached_quant_detail"
            )
        else:
            detail.setdefault("model_handoff_stage", "MODEL_OUTPUT_NOT_VISIBLE")
            detail.setdefault(
                "model_output_missing_reason",
                str(detail.get("probability_model_gate_reason") or detail.get("model_not_run_reason") or "model_output_not_visible"),
            )
            detail.setdefault("model_output_source", "")
        detail["ticker"] = ticker
        if not detail.get("candidate_trace_id"):
            companion = QuantEventLogger._candidate_trace_identity_fields(detail, self._utc_timestamp())
            if companion.get("candidate_trace_id"):
                detail["candidate_trace_id"] = companion["candidate_trace_id"]
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

    def _evaluate_and_log_delta_extreme_shadow(
        self,
        *,
        market: GammaMarket,
        ticker: str,
        ptb_info: Any,
        model_side: str,
        confidence: float,
        model_ev: float,
        delta: Any,
        ob_spread: float,
        ob_liquidity_usd: float,
        yes_token_id: str,
        no_token_id: str,
        yes_bid: float,
        yes_ask: float,
        yes_bid_size: float,
        yes_ask_size: float,
        no_bid: float,
        no_ask: float,
        no_bid_size: float,
        no_ask_size: float,
        yes_orderbook_age_ms: int,
        no_orderbook_age_ms: int,
        feed_age: float | None,
        current_balance: float,
        timing_detail: dict,
    ) -> None:
        """Passive shadow evaluation and event logging."""
        side = model_side if model_side in ("YES", "NO") else "YES"
        token_id = yes_token_id if side == "YES" else no_token_id
        price = yes_ask if side == "YES" else no_ask
        ask_size = yes_ask_size if side == "YES" else no_ask_size
        raw_bid = yes_bid if side == "YES" else no_bid
        raw_ask = yes_ask if side == "YES" else no_ask

        quote_age_ms = max(yes_orderbook_age_ms, no_orderbook_age_ms)
        oracle_age_ms = int(max(0.0, feed_age or 0.0) * 1000)
        seconds_remaining = float(getattr(ptb_info, "seconds_remaining", 0.0) or 0.0)

        eval_result = evaluate_delta_extreme_shadow_candidate(
            price=price,
            spread=ob_spread,
            quote_age_ms=quote_age_ms,
            oracle_age_ms=oracle_age_ms,
            ask_size=ask_size,
            seconds_remaining=seconds_remaining,
        )

        payload = {
            "market": market.market_id,
            "side": side,
            "token_id": token_id,
            "price": float(price),
            "raw_bid": float(raw_bid),
            "raw_ask": float(raw_ask),
            "spread": float(ob_spread),
            "bid_size": float(yes_bid_size if side == "YES" else no_bid_size),
            "ask_size": float(ask_size),
            "quote_age_ms": int(quote_age_ms),
            "oracle_age_ms": int(oracle_age_ms),
            "confidence": float(confidence),
            "ev": float(model_ev),
            "delta_value": float(getattr(delta, "delta_score", 0.0) or 0.0),
            "delta_reason": str(getattr(delta, "reason", "Mechanism_B") or "Mechanism_B"),
            "executable_pass": eval_result["executable_pass"],
            "executable_reject_reason": eval_result["executable_reject_reason"],
            "shadow_size_usd": eval_result["standard_size_usd"],
            "shadow_shares": eval_result["standard_shares"],
            "shadow_entry_price": float(price),
            "eventual_outcome": "PENDING",
            "shadow_pnl": 0.0,
            "settlement_source": "pending_expiry",
            "epoch_start_ts": int(getattr(ptb_info, "epoch_start_ts", 0) or 0),
            "seconds_remaining": seconds_remaining,
            "micro_shadow_size_usd": eval_result["micro_size_usd"],
            "micro_shadow_shares": eval_result["micro_shares"],
        }

        if hasattr(self, "quant_logger") and self.quant_logger:
            self.quant_logger.log_delta_shadow(payload)

    def _display_skip_reason(self, reason: str) -> str:
        clean = (reason or "").lower()
        if "stale" in clean:
            return "stale_data"
        if clean in {
            "missing_token_id",
            "empty_book",
            "clob_error",
            "warmup_pending",
            "token_mapping_mismatch",
            *CLOB_ORDERBOOK_ERROR_CATEGORIES,
        }:
            return clean
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
        self._last_risk_mode_decision = decision
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
        active_config = get_tier_config(result.active_tier)
        self.bankroll_state.bankroll_tier_id = active_config.tier_id
        self.bankroll_state.bankroll_tier_name = active_config.tier_name
        self.bankroll_state.bankroll_family = active_config.family
        self.bankroll_state.bankroll_risk_profile = active_config.risk_profile
        self.bankroll_state.bankroll_tier_locked = result.tier_locked
        self.bankroll_state.bankroll_hysteresis_active = result.hysteresis_active

        log_body = (
            f"active={result.active_tier.value} raw={result.raw_tier.value} "
            f"family={active_config.family} profile={active_config.risk_profile} "
            f"balance=${result.balance:.2f} reason={result.reason} "
            f"locked={str(result.tier_locked).lower()} hysteresis={str(result.hysteresis_active).lower()}"
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
        mode_detail = self._bankroll_mode_detail(bankroll)
        tier_detail = self._bankroll_tier_detail()
        body += (
            f" bankroll_mode={mode_detail['bankroll_mode']} "
            f"micro_survival_active={str(mode_detail['micro_survival_active']).lower()} "
            f"micro_position_size={float(mode_detail['micro_position_size']):.4f} "
            f"tier_id={tier_detail['bankroll_tier_id']} "
            f"family={tier_detail['bankroll_family']} "
            f"profile={tier_detail['bankroll_risk_profile']} "
            f"tier_locked={str(tier_detail['bankroll_tier_locked']).lower()} "
            f"hysteresis={str(tier_detail['bankroll_hysteresis_active']).lower()}"
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
        self._maybe_send_telegram_summary()

    def _maybe_send_telegram_summary(self) -> None:
        try:
            run_id = str(getattr(self.quant_events, "run_id", "") or "") or "n/a"
            uptime_s = int(time.monotonic() - self._session_start_monotonic)
            uptime_h, rem = divmod(uptime_s, 3600)
            uptime_m = rem // 60
            uptime_str = f"{uptime_h}h{uptime_m:02d}m"
            regime = "n/a"
            for asset in ("ETH", "BTC"):
                detail = (getattr(self, "last_quant_details", {}) or {}).get(asset) or {}
                r = str(detail.get("market_regime") or "").strip()
                if r and r.upper() not in ("", "UNKNOWN", "--"):
                    regime = r
                    break
            cycle_mono = float(getattr(self, "_cycle_started_monotonic", 0.0) or 0.0)
            heartbeat_age_s = int(time.monotonic() - cycle_mono) if cycle_mono > 0 else 0
            heartbeat_age = f"{heartbeat_age_s}s" if heartbeat_age_s > 0 else "<1s"
            self._notify_telegram(
                "notify_summary",
                "",
                dedup_key="runtime_status",
                run_id=run_id,
                uptime=uptime_str,
                cycles=self._cycle_count,
                trade_opens=self.paper_stats.trades_simulated,
                trade_closes=self.paper_stats.paper_exits,
                exceptions=self._loop_exception_count,
                mode=self._runtime_mode().upper(),
                risk_mode=str(self._risk_mode_state.current_mode.value),
                heartbeat_age=heartbeat_age,
                regime=regime,
            )
        except Exception:
            pass

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
        bankroll_mode_detail = self._bankroll_mode_detail()
        bankroll_tier_detail = self._bankroll_tier_detail()
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
            **bankroll_tier_detail,
            **bankroll_mode_detail,
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
        observability_health = self.dashboard_observability_health_state()
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
            **self._bankroll_tier_detail(state.current_bankroll_tier),
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
            **self._bankroll_mode_detail(state.current_bankroll_for_sizing),
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
            "observability_health": observability_health,
        }

    def _compile_dashboard_v2a_stats(self) -> dict[str, object]:
        import os
        import json
        from datetime import datetime, UTC

        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        journal_path = f"runtime/quant_data/trade_journal/{today_str}.jsonl"
        shadow_path = f"runtime/quant_data/stop_loss_shadow/{today_str}.jsonl"
        patch_time = datetime.fromisoformat("2026-06-16T07:34:29+00:00")

        closes = []
        if os.path.exists(journal_path):
            try:
                file_size = os.path.getsize(journal_path)
                with open(journal_path, "r", encoding="utf-8") as f:
                    if file_size > 10 * 1024 * 1024:
                        f.seek(file_size - 10 * 1024 * 1024)
                        f.readline()
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            evt = json.loads(line)
                            if evt.get("mode") != "paper":
                                continue
                            if evt.get("event_type") != "trade_close":
                                continue
                            ts_str = evt.get("timestamp_utc")
                            if not ts_str:
                                continue
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            if ts >= patch_time:
                                closes.append(evt)
                        except Exception:
                            pass
            except Exception:
                pass

        yes_trades = 0
        no_trades = 0
        tp_exits = 0
        sl_exits = 0
        total_pnl = 0.0
        wins = 0

        for c in closes:
            payload = c.get("payload") or {}
            side = str(payload.get("side") or "").upper()
            if side == "YES":
                yes_trades += 1
            elif side == "NO":
                no_trades += 1

            reason = payload.get("reason") or ""
            reason_lower = str(reason).lower()
            if reason == "take_profit_target_reached":
                tp_exits += 1
            elif "stop" in reason_lower:
                sl_exits += 1

            pnl = payload.get("pnl") or payload.get("pnl_usdc") or 0.0
            try:
                pnl_val = float(pnl)
            except (TypeError, ValueError):
                pnl_val = 0.0
            total_pnl += pnl_val
            if pnl_val > 0:
                wins += 1

        total_closed = len(closes)
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0.0

        shadow_events_count = 0
        raw_stop_signals = 0
        mid_3_stop_signals = 0
        suppressed_raw_stops = 0
        actual_paper_stops = 0

        if os.path.exists(shadow_path):
            try:
                file_size = os.path.getsize(shadow_path)
                with open(shadow_path, "r", encoding="utf-8") as f:
                    if file_size > 5 * 1024 * 1024:
                        f.seek(file_size - 5 * 1024 * 1024)
                        f.readline()
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            evt = json.loads(line)
                            ts_str = evt.get("timestamp_utc") or evt.get("timestamp")
                            if not ts_str:
                                continue
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            if ts < patch_time:
                                continue

                            shadow_events_count += 1
                            payload = evt.get("payload") or {}
                            if payload.get("actual_raw_bid_stop"):
                                raw_stop_signals += 1
                            if payload.get("shadow_mid_3sample_stop"):
                                mid_3_stop_signals += 1
                            if payload.get("paper_stop_suppressed"):
                                suppressed_raw_stops += 1
                            if payload.get("actual_stop_triggered") or payload.get("paper_mid_confirmed_stop"):
                                actual_paper_stops += 1
                        except Exception:
                            pass
            except Exception:
                pass

        return {
            "post_patch_trades_count": total_closed,
            "yes_trades_count": yes_trades,
            "no_trades_count": no_trades,
            "tp_exits_count": tp_exits,
            "sl_exits_count": sl_exits,
            "win_rate": win_rate,
            "pnl": total_pnl,
            "shadow_events": shadow_events_count,
            "raw_stop_signals": raw_stop_signals,
            "mid_3_stop_signals": mid_3_stop_signals,
            "suppressed_raw_stops": suppressed_raw_stops,
            "actual_paper_stops": actual_paper_stops,
            # PATCH_SIGNAL_001 Shadow Filter counters
            "shadow_baseline_accepted": self._baseline_accepted,
            "shadow_would_reject": self._shadow_would_reject,
            "ev_cap_shadow_rejects": self._ev_cap_shadow_rejects,
            "yes_floor_shadow_rejects": self._yes_floor_shadow_rejects,
        }

    def dashboard_v2a_stats(self) -> dict[str, object]:
        try:
            stats = self._compile_dashboard_v2a_stats()
            stats.update(self.dashboard_probe_counts())
            return stats
        except Exception:
            return self.dashboard_probe_counts()

    def dashboard_probe_counts(self) -> dict[str, int]:
        """Return in-memory session probe counters for Research Cockpit display.

        Keys match update_research_obs() parameter names so callers can
        unpack directly: display.update_research_obs(**trader.dashboard_probe_counts())
        Read-only copy. Fail-soft: returns zeros if dict is absent.
        """
        counts = getattr(self, "_cockpit_probe_counts", {})
        return {
            "zero_size_probe_count": int(counts.get("zero_size", 0)),
            "cycle_selection_probe_count": int(counts.get("cycle_selection", 0)),
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

    def log_paper_session_summary(self, *, include_runtime_evaluation: bool = True) -> None:
        if not self._paper_enabled():
            return
        self.log_quant_summary(force=True)
        if include_runtime_evaluation:
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

    def _path_truth_metadata(self, pos) -> dict[str, object]:
        metadata = getattr(pos, "metadata", None)
        if isinstance(metadata, dict):
            return metadata
        metadata = {}
        try:
            pos.metadata = metadata
        except Exception:
            pass
        return metadata

    def _path_truth_emitted_checkpoints(self, pos) -> set[str]:
        trade_id = str(getattr(pos, "position_id", "") or "")
        if not trade_id:
            return set()
        emitted = getattr(self, "_path_truth_emitted_checkpoints_by_trade", {}).get(trade_id, set())
        return {str(value) for value in emitted}

    def _remember_path_truth_checkpoint(self, pos, checkpoint_key: str) -> None:
        trade_id = str(getattr(pos, "position_id", "") or "")
        if not trade_id:
            return
        emitted_by_trade = getattr(self, "_path_truth_emitted_checkpoints_by_trade", None)
        if not isinstance(emitted_by_trade, dict):
            emitted_by_trade = {}
            self._path_truth_emitted_checkpoints_by_trade = emitted_by_trade
        emitted = {str(value) for value in emitted_by_trade.get(trade_id, set())}
        emitted.add(str(checkpoint_key))
        emitted_by_trade[trade_id] = emitted

    @staticmethod
    def _path_truth_parse_ts(raw: object) -> datetime | None:
        text = str(raw or "").strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except Exception:
            return None

    def _path_truth_elapsed_seconds(self, pos, now: datetime | None = None) -> int | None:
        entry_dt = self._path_truth_parse_ts(getattr(pos, "entry_time", ""))
        if entry_dt is None:
            return None
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        current = current.astimezone(UTC)
        return max(0, int((current - entry_dt).total_seconds()))

    def _path_truth_session_hour_utc(self, pos, now: datetime | None = None) -> int | None:
        entry_dt = self._path_truth_parse_ts(getattr(pos, "entry_time", ""))
        if entry_dt is not None:
            return int(entry_dt.hour)
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        return int(current.astimezone(UTC).hour)

    def _path_truth_lifecycle_phase(self, pos, now: datetime | None = None) -> str | None:
        metadata = self._path_truth_metadata(pos)
        explicit = str(metadata.get("lifecycle_phase") or "").strip()
        if explicit:
            return explicit
        epoch_start = self._diagnostic_int(metadata.get("epoch_start_ts"))
        if epoch_start is None or epoch_start <= 0:
            return None
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        seconds_remaining = int(epoch_start + 300 - current.astimezone(UTC).timestamp())
        return self._phase2_lifecycle_phase(seconds_remaining)

    def _path_truth_market_state(self, pos) -> dict[str, object]:
        token_id = self._position_token_id(pos)
        ticker = self._ticker_from_market_id(getattr(pos, "symbol", ""))
        state: dict[str, object] = {
            "current_mark_price": None,
            "bid": None,
            "ask": None,
            "spread": None,
            "quote_age_ms": None,
            "liquidity_state": None,
        }
        try:
            ob = self.client.get_orderbook(token_id)
            bid = float(getattr(ob, "best_bid", 0.0) or 0.0)
            ask = float(getattr(ob, "best_ask", 0.0) or 0.0)
            if bid > 0:
                state["current_mark_price"] = bid
                state["bid"] = bid
            if ask > 0:
                state["ask"] = ask
            if bid > 0 and ask > 0:
                state["spread"] = round(ask - bid, 6)
            quote_age = self._orderbook_age_ms(ob)
            if quote_age:
                state["quote_age_ms"] = int(quote_age)
        except Exception as exc:
            LOGGER.debug(
                "[PATH_TRUTH] orderbook checkpoint unavailable | position=%s token=%s error=%s",
                getattr(pos, "position_id", ""),
                token_id,
                exc,
            )
        try:
            metadata = self._path_truth_metadata(pos)
            readiness = self._phase2_readiness_timestamps(ticker, int(metadata.get("epoch_start_ts", 0) or 0))
            liquidity = str(
                metadata.get("liquidity_state")
                or readiness.get("liquidity_depth_state")
                or ""
            ).strip()
            if liquidity:
                state["liquidity_state"] = liquidity
        except Exception:
            pass
        return state

    def _emit_path_truth_checkpoint(
        self,
        pos,
        *,
        checkpoint_elapsed_s: int | str,
        checkpoint_reason: str,
        now: datetime | None = None,
        market_state: dict[str, object] | None = None,
    ) -> bool:
        if not bool(getattr(self.settings, "paper_trading", False)):
            return False
        checkpoint_key = str(checkpoint_elapsed_s)
        emitted = self._path_truth_emitted_checkpoints(pos)
        if checkpoint_key in emitted:
            return False
        if len(emitted) >= int(getattr(self, "_path_truth_max_writes_per_trade", 5)):
            return False

        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        current = current.astimezone(UTC)
        metadata = self._path_truth_metadata(pos)
        state = market_state if market_state is not None else self._path_truth_market_state(pos)

        def _optional_float(value: object) -> float | None:
            try:
                if value is None or value == "":
                    return None
                return float(value)
            except Exception:
                return None

        entry_price = _optional_float(getattr(pos, "entry_price", None))
        mark_price = _optional_float(state.get("current_mark_price") if isinstance(state, dict) else None)
        size = _optional_float(getattr(pos, "size", None))
        unrealized_pnl = None
        favorable = None
        adverse = None
        if entry_price is not None and mark_price is not None:
            favorable = bool(mark_price > entry_price)
            adverse = bool(mark_price < entry_price)
            if size is not None:
                unrealized_pnl = round((mark_price - entry_price) * size, 6)

        payload = {
            "event_type": "trade_path_checkpoint",
            "ts": current.isoformat().replace("+00:00", "Z"),
            "run_id": str(getattr(getattr(self, "quant_events", None), "run_id", "") or ""),
            "trade_id": str(getattr(pos, "position_id", "") or ""),
            "paper_trade_replay_key": metadata.get("paper_trade_replay_key") or None,
            "candidate_id": metadata.get("candidate_id") or None,
            "decision_id": metadata.get("decision_id") or None,
            "asset": self._ticker_from_market_id(getattr(pos, "symbol", "")),
            "side": self._position_outcome(pos),
            "market_slug": metadata.get("market_slug") or None,
            "condition_id": metadata.get("condition_id") or None,
            "lifecycle_phase": self._path_truth_lifecycle_phase(pos, current),
            "session_hour_utc": self._path_truth_session_hour_utc(pos, current),
            "checkpoint_elapsed_s": checkpoint_elapsed_s,
            "entry_price": entry_price,
            "current_mark_price": mark_price,
            "bid": _optional_float(state.get("bid") if isinstance(state, dict) else None),
            "ask": _optional_float(state.get("ask") if isinstance(state, dict) else None),
            "spread": _optional_float(state.get("spread") if isinstance(state, dict) else None),
            "quote_age_ms": self._diagnostic_int(state.get("quote_age_ms") if isinstance(state, dict) else None),
            "liquidity_state": (
                state.get("liquidity_state") if isinstance(state, dict) and state.get("liquidity_state") else None
            ),
            "unrealized_pnl": unrealized_pnl,
            "adverse_from_entry": adverse,
            "favorable_from_entry": favorable,
            "checkpoint_reason": checkpoint_reason,
            # ENTRY_MODEL_TRUTH_ENVELOPE_V1 — carry from position metadata, observability-only
            **self._carry_entry_model_truth_from_metadata(metadata),
        }

        emitted_ok = self._emit_quant_event("log_trade_path_checkpoint", payload)
        if emitted_ok:
            self._remember_path_truth_checkpoint(pos, checkpoint_key)
        return emitted_ok

    def _maybe_emit_path_truth_checkpoints(self, positions: list | None = None, *, now: datetime | None = None) -> None:
        if not bool(getattr(self.settings, "paper_trading", False)):
            return
        current = now or datetime.now(UTC)
        open_positions = positions if positions is not None else self.tracker.open_positions()
        for pos in list(open_positions or []):
            if getattr(pos, "status", "open") != "open":
                continue
            elapsed = self._path_truth_elapsed_seconds(pos, current)
            if elapsed is None:
                continue
            for checkpoint_s in getattr(self, "_path_truth_checkpoint_schedule_s", (15, 30, 45, 60)):
                checkpoint = int(checkpoint_s)
                tolerance = int(getattr(self, "_path_truth_checkpoint_tolerance_s", {}).get(checkpoint, 2))
                if checkpoint <= elapsed <= checkpoint + tolerance:
                    self._emit_path_truth_checkpoint(
                        pos,
                        checkpoint_elapsed_s=checkpoint,
                        checkpoint_reason="scheduled" if elapsed == checkpoint else "late",
                        now=current,
                    )

    def _emit_path_truth_shutdown_events(self) -> None:
        if not bool(getattr(self.settings, "paper_trading", False)):
            return
        for pos in list(self.tracker.open_positions() or []):
            self._emit_path_truth_checkpoint(
                pos,
                checkpoint_elapsed_s="event_end",
                checkpoint_reason="event_end",
                now=datetime.now(UTC),
                market_state={},
            )

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
        elif tier_config.family == "MICRO":
            LOGGER.info(
                "MICRO BANKROLL PROTECTION ACTIVE -- using rank sizing | "
                "balance=$%.2f active_tier=%s raw_tier=%s family=%s profile=%s risk_range=%.2f%%-%.2f%% max_trades_hour=%d",
                balance, tier_config.description, raw_tier, tier_config.family, tier_config.risk_profile,
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
        markets.sort(
            key=lambda market: (
                1 if self._real_token_ids.get(self._ticker_from_market_id(market.market_id)) else 0,
                self._meta_int(
                    self._market_token_meta.get(self._ticker_from_market_id(market.market_id), {}),
                    "seconds_remaining",
                    0,
                ),
            ),
            reverse=True,
        )
        token_ids_found = sum(1 for t in crypto_tickers if t in self._real_token_ids)
        LOGGER.info(
            "Selected %s Polymarket 5M Crypto markets | Real token IDs cached: %d/%d",
            len(markets), token_ids_found, len(crypto_tickers),
        )
        return markets[:top_n]

    def _preload_observability_payload(self) -> dict[str, object]:
        return {
            "event": "preload_next_market_v1",
            "preload_attempted": self._preload_attempted,
            "preload_success": self._preload_success,
            "preload_failure_reason": self._preload_failed_reason,
            "preload_ticker": self._preload_ticker,
            "preload_market_slug": self._preload_market_slug,
            "preload_condition_id": self._preload_condition_id,
            "preload_yes_token_id_present": self._preload_yes_token_id_present,
            "preload_no_token_id_present": self._preload_no_token_id_present,
            "preload_orderbook_warmed": self._preload_orderbook_warmed,
            "preload_orderbook_state": self._preload_orderbook_state,
            "preload_seconds_before_epoch": self._preload_seconds_before_epoch,
            "preload_latency_ms": self._preload_latency_ms,
            "preload_cache_hit": self._preload_cache_hit,
            "preload_cache_age_seconds": self._preload_cache_age_seconds,
            "preload_next_epoch_start": self._preload_next_epoch_start,
            "preload_next_epoch_remaining_seconds": self._preload_next_epoch_remaining_seconds,
            "mode": self._runtime_mode(),
        }

    def _preload_next_market(self, asset: str):
        """
        Attempts to preload the next 5-minute market for a given asset.
        Records observability metrics for preload success/failure.
        """
        self._preload_attempted = True
        self._preload_success = False
        self._preload_started_ts = int(time.time())
        self._preload_failed_reason = None
        self._preload_ticker = asset.split('/')[0].upper() # e.g. BTC from BTC/ETH
        ticker = self._preload_ticker

        start_mono = time.monotonic()

        try:
            # check if we already have a successful preload for the *upcoming* epoch
            now_ts = int(time.time())
            # For 5-min markets, the next epoch starts at the next multiple of 300
            next_expected_epoch = ((now_ts // 300) + 1) * 300

            self._preload_next_epoch_start = next_expected_epoch
            self._preload_next_epoch_remaining_seconds = next_expected_epoch - now_ts

            if ticker in self._preloaded_next_markets and self._preloaded_next_markets[ticker].epoch_start_ts == next_expected_epoch:
                self._preload_cache_hit = True
                self._preload_cache_age_seconds = now_ts - self._preload_success_ts
                self._preload_success = True
                # we already have it
                return

            self._preload_cache_hit = False
            self._preload_cache_age_seconds = 0

            # Actually fetch
            next_market = self.gamma.get_next_5min_market(ticker)

            latency_ms = int((time.monotonic() - start_mono) * 1000)
            self._preload_latency_ms = latency_ms

            if next_market:
                self._preloaded_next_markets[ticker] = next_market
                self._preload_success_ts = int(time.time())
                self._preload_success = True
                self._preload_market_slug = next_market.slug
                self._preload_condition_id = next_market.condition_id
                self._preload_yes_token_id_present = bool(next_market.yes_token_id)
                self._preload_no_token_id_present = bool(next_market.no_token_id)
                self._preload_seconds_before_epoch = next_market.epoch_start_ts - self._preload_success_ts
                self._preload_lead_seconds = self._preload_seconds_before_epoch # alias

                # Optionally warm orderbook
                if next_market.yes_token_id and next_market.no_token_id:
                    try:
                        # Compact orderbook fetch (v1 just warms it)
                        self.client.get_orderbook(next_market.yes_token_id)
                        self.client.get_orderbook(next_market.no_token_id)
                        self._preload_orderbook_warmed = True
                        self._preload_orderbook_state = "WARMED"
                        self._preload_book_ready_ts = int(time.time())
                    except Exception as ob_exc:
                        self._preload_orderbook_warmed = False
                        self._preload_orderbook_state = f"ERROR: {ob_exc}"

                self._emit_quant_event(
                    "log_system_health",
                    self._preload_observability_payload()
                )
                LOGGER.info(
                    "[PRELOAD] Successfully preloaded next market %s for asset %s with %d seconds lead.",
                    next_market.market_id,
                    asset,
                    self._preload_seconds_before_epoch,
                )
            else:
                self._preload_failed_reason = "no_next_market_found"
                self._emit_quant_event(
                    "log_system_health",
                    self._preload_observability_payload()
                )
                LOGGER.warning("[PRELOAD] No next market found for asset %s.", asset)

        except Exception as e:
            self._preload_failed_reason = f"exception: {e}"
            self._preload_latency_ms = int((time.monotonic() - start_mono) * 1000)
            self._emit_quant_event(
                "log_system_health",
                self._preload_observability_payload()
            )
            LOGGER.error("[PRELOAD] Error preloading next market for asset %s: %s", asset, e)

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
                active_markets = getattr(
                    self.gamma,
                    "get_current_and_next_5min_markets",
                    lambda _ticker: [self.gamma.get_current_5min_market(_ticker)],
                )(ticker)
                active_markets = [market for market in active_markets or [] if market is not None]
                active = active_markets[0] if active_markets else None
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
                        next_market = active_markets[1] if len(active_markets) > 1 else getattr(self.gamma, "get_next_5min_market", lambda _ticker: None)(ticker)
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

    @staticmethod
    def _is_empty_orderbook_error(error: object) -> bool:
        message = str(error).lower()
        return (
            "empty_orderbook" in message
            or "empty_book" in message
            or "invalid_orderbook" in message
            or "clob_empty_response" in message
        )

    def _is_liquidity_recovery_error(self, error: object, *, research_mode: bool = False) -> bool:
        if self._is_empty_orderbook_error(error):
            return True
        if not research_mode:
            return False
        return self._infer_clob_orderbook_error_category(error) in {"clob_timeout"}

    @staticmethod
    def _empty_book_recovery_detail(*, liquidity_state: str = "HEALTHY") -> dict[str, object]:
        return {
            "empty_book_recovery_attempted": False,
            "empty_book_recovery_success": False,
            "empty_book_recovery_failed": False,
            "empty_book_recovery_retry_count": 0,
            "liquidity_state": liquidity_state,
            "empty_book_recovery_research_mode": False,
            "liquidity_recovery_grace_entered": False,
            "liquidity_recovery_grace_success": False,
            "liquidity_recovery_grace_failed": False,
            "recovery_wait_seconds": 0.0,
            "recovered_before_cutoff": False,
            "candidate_survived_recovery": False,
            "recovery_exit_reason": "",
            "recovery_branch_candidate_seen": False,
            "recovery_branch_preempted_by_cutoff": False,
            "recovery_branch_skipped_reason": "",
            "recovery_branch_mode_disabled": False,
            "recovery_branch_enter_condition_failed": False,
        }

    def _fetch_orderbook_pair_once(self, yes_token_id: str, no_token_id: str):
        yes_ob = self.client.get_orderbook(yes_token_id)
        no_ob = self.client.get_orderbook(no_token_id) if no_token_id else None
        return yes_ob, no_ob

    def _empty_book_recovery_research_enabled(self) -> bool:
        return bool(
            self._paper_enabled()
            and self._setting("empty_book_recovery_research_mode", False)
        )

    def _recovery_exit_reason_for_block(
        self,
        *,
        exc: object,
        yes_token_id: str,
        no_token_id: str,
        seconds_remaining: int | None,
    ) -> str:
        if not self._paper_enabled():
            return "live_mode_disabled"
        if not bool(self._setting("orderbook_empty_recovery_enabled", True)):
            return "recovery_disabled"
        if not yes_token_id or not no_token_id:
            return "missing_token_id"
        if not self._is_liquidity_recovery_error(exc, research_mode=self._empty_book_recovery_research_enabled()):
            return "non_empty_book_error"
        if seconds_remaining is None:
            return "missing_seconds_remaining"
        if int(seconds_remaining) <= self._entry_hard_block_seconds():
            return "hard_close_zone"
        return "unknown_recovery_block"

    def _recovery_candidate_survival_detail(
        self,
        *,
        yes_ob,
        no_ob,
        seconds_remaining: int | None,
    ) -> tuple[bool, str]:
        if seconds_remaining is None or int(seconds_remaining) <= self._entry_hard_block_seconds():
            return False, "hard_close_zone"
        yes_spread = float(getattr(yes_ob, "spread", 0.0) or 0.0)
        no_spread = float(getattr(no_ob, "spread", 0.0) or 0.0)
        spread = max(yes_spread, no_spread)
        max_spread = float(self._setting("adaptive_entry_max_spread", 0.06))
        if spread > max_spread:
            return False, "spread_too_wide_after_recovery"
        max_age_ms = int(self._setting("adaptive_entry_max_orderbook_age_ms", 1000))
        orderbook_age_ms = max(self._orderbook_age_ms(yes_ob), self._orderbook_age_ms(no_ob))
        if orderbook_age_ms > max_age_ms:
            return False, "orderbook_stale_after_recovery"
        return True, "recovered"

    def _fetch_orderbook_pair_with_empty_recovery(
        self,
        *,
        ticker: str,
        yes_token_id: str,
        no_token_id: str,
        seconds_remaining: int | None,
        market_slug: str = "",
    ):
        detail = self._empty_book_recovery_detail()
        research_mode = self._empty_book_recovery_research_enabled()
        detail["empty_book_recovery_research_mode"] = research_mode
        self._last_empty_book_recovery_detail[ticker.upper()] = detail
        try:
            return (*self._fetch_orderbook_pair_once(yes_token_id, no_token_id), detail)
        except Exception as exc:
            branch_skipped_reason = self._recovery_exit_reason_for_block(
                exc=exc,
                yes_token_id=yes_token_id,
                no_token_id=no_token_id,
                seconds_remaining=seconds_remaining,
            )
            detail.update({
                "recovery_branch_candidate_seen": True,
                "recovery_branch_mode_disabled": not research_mode,
                "recovery_branch_preempted_by_cutoff": branch_skipped_reason == "hard_close_zone",
            })
            if not (
                self._paper_enabled()
                and bool(self._setting("orderbook_empty_recovery_enabled", True))
                and yes_token_id
                and no_token_id
                and self._is_liquidity_recovery_error(exc, research_mode=research_mode)
                and seconds_remaining is not None
                and int(seconds_remaining) > self._entry_hard_block_seconds()
            ):
                detail.update({
                    "liquidity_recovery_grace_failed": research_mode,
                    "recovery_exit_reason": branch_skipped_reason if research_mode else "",
                    "recovery_branch_skipped_reason": branch_skipped_reason,
                    "recovery_branch_enter_condition_failed": True,
                })
                raise

            retries = max(0, min(3, int(self._setting("orderbook_empty_recovery_retries", 2))))
            delay_ms = max(0, int(self._setting("orderbook_empty_recovery_delay_ms", 75)))
            max_total_ms = max(1, int(self._setting("orderbook_empty_recovery_max_total_ms", 300)))
            if retries <= 0:
                detail.update({
                    "liquidity_recovery_grace_failed": research_mode,
                    "recovery_exit_reason": "bounded_retries_disabled" if research_mode else "",
                    "recovery_branch_skipped_reason": "bounded_retries_disabled",
                    "recovery_branch_enter_condition_failed": True,
                })
                raise

            detail.update({
                "empty_book_recovery_attempted": True,
                "liquidity_recovery_grace_entered": research_mode,
                "recovery_exit_reason": "retrying_empty_book" if research_mode else "",
                "liquidity_state": "RECOVERING",
            })
            self._market_readiness_metrics["empty_book_recovery_attempted"] += 1
            started = time.monotonic()
            last_exc: Exception = exc
            grace_expired = False

            for retry_index in range(1, retries + 1):
                elapsed_ms = int((time.monotonic() - started) * 1000)
                if elapsed_ms >= max_total_ms:
                    grace_expired = True
                    break
                if delay_ms > 0:
                    remaining_ms = max(0, max_total_ms - elapsed_ms)
                    time.sleep(min(delay_ms, remaining_ms) / 1000.0)
                detail["empty_book_recovery_retry_count"] = retry_index
                self._market_readiness_metrics["empty_book_recovery_retries"] += 1
                try:
                    yes_ob, no_ob = self._fetch_orderbook_pair_once(yes_token_id, no_token_id)
                    detail.update({
                        "empty_book_recovery_success": True,
                        "liquidity_state": "HEALTHY",
                    })
                    if research_mode:
                        survived, exit_reason = self._recovery_candidate_survival_detail(
                            yes_ob=yes_ob,
                            no_ob=no_ob,
                            seconds_remaining=seconds_remaining,
                        )
                        detail.update({
                            "liquidity_recovery_grace_success": True,
                            "recovery_wait_seconds": round(time.monotonic() - started, 3),
                            "recovered_before_cutoff": bool(
                                seconds_remaining is not None
                                and int(seconds_remaining) > self._entry_hard_block_seconds()
                            ),
                            "candidate_survived_recovery": survived,
                            "recovery_exit_reason": exit_reason,
                        })
                    self._market_readiness_metrics["empty_book_recovery_success"] += 1
                    LOGGER.info(
                        "[ORDERBOOK_RECOVERY] ticker=%s market_slug=%s recovered=true retries=%d",
                        ticker,
                        market_slug,
                        retry_index,
                    )
                    return yes_ob, no_ob, detail
                except Exception as retry_exc:
                    last_exc = retry_exc
                    if not self._is_liquidity_recovery_error(retry_exc, research_mode=research_mode):
                        raise

            detail.update({
                "empty_book_recovery_failed": True,
                "liquidity_recovery_grace_failed": research_mode,
                "recovery_wait_seconds": round(time.monotonic() - started, 3) if research_mode else 0.0,
                "recovery_exit_reason": "grace_window_expired" if research_mode and grace_expired else "empty_book_retries_exhausted" if research_mode else "",
                "recovery_branch_skipped_reason": "grace_window_expired" if grace_expired else "empty_book_retries_exhausted",
                "liquidity_state": "EMPTY",
            })
            self._market_readiness_metrics["empty_book_recovery_failed"] += 1
            LOGGER.info(
                "[ORDERBOOK_RECOVERY] ticker=%s market_slug=%s recovered=false retries=%s error=%s",
                ticker,
                market_slug,
                detail["empty_book_recovery_retry_count"],
                last_exc,
            )
            raise last_exc

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

    def _classify_orderbook_readiness_reason(
        self,
        ticker: str,
        *,
        token_ids: tuple[str, str] | None,
        token_mapping_warning: str = "",
        orderbook_error: str = "",
        clob_error_category: str = "",
        yes_ask: float = 0.0,
        no_ask: float = 0.0,
    ) -> str:
        warning = (token_mapping_warning or "").lower()
        if not token_ids or len(token_ids) < 2 or not token_ids[0] or not token_ids[1] or "missing_yes_no_token_ids" in warning:
            return "missing_token_id"
        if warning:
            return "token_mapping_mismatch"

        error = (orderbook_error or "").lower()
        category = (clob_error_category or self._infer_clob_orderbook_error_category(orderbook_error)).lower()
        if category in CLOB_ORDERBOOK_ERROR_CATEGORIES:
            return category
        if "stale_orderbook" in error:
            return "stale_book"
        if error:
            if "empty_orderbook" not in error and "invalid_orderbook" not in error:
                return category or "clob_http_error"
            last_success_ms = int(self._last_orderbook_age_ms.get(ticker.upper(), 0) or 0)
            if last_success_ms <= 0:
                self._orderbook_warmup_pending_counts[ticker.upper()] += 1
                threshold = int(self._setting("orderbook_warmup_pending_threshold", 3))
                if self._orderbook_warmup_pending_counts[ticker.upper()] <= threshold:
                    return "warmup_pending"
            return "empty_book"

        if yes_ask <= 0 or no_ask <= 0:
            last_success_ms = int(self._last_orderbook_age_ms.get(ticker.upper(), 0) or 0)
            if last_success_ms <= 0:
                self._orderbook_warmup_pending_counts[ticker.upper()] += 1
                threshold = int(self._setting("orderbook_warmup_pending_threshold", 3))
                if self._orderbook_warmup_pending_counts[ticker.upper()] <= threshold:
                    return "warmup_pending"
            return "empty_book"

        self._orderbook_warmup_pending_counts[ticker.upper()] = 0
        return ""

    def _infer_clob_orderbook_error_category(self, error: object) -> str:
        if isinstance(error, ClobOrderbookError):
            return error.category
        text = str(error or "").lower()
        if not text:
            return ""
        if "empty_orderbook" in text or "invalid_orderbook" in text or "stale_orderbook" in text:
            return ""
        if "timeout" in text or "timed out" in text:
            return "clob_timeout"
        if "429" in text or "rate limit" in text or "too many requests" in text:
            return "clob_rate_limited"
        if "401" in text or "403" in text or "unauthorized" in text or "forbidden" in text:
            return "clob_auth_or_client_issue"
        if "400" in text or "404" in text or "not found" in text or "unknown token" in text or "invalid token" in text:
            return "clob_token_not_found"
        if "not connected" in text or "not installed" in text or "client_not_connected" in text:
            return "clob_client_not_connected"
        if "parse_orderbook_failed" in text or "malformed" in text:
            return "clob_parse_error"
        if "empty_orderbook_response" in text:
            return "clob_empty_response"
        if "http" in text or "api" in text or "status" in text:
            return "clob_http_error"
        return ""

    def _clob_orderbook_error_detail(
        self,
        exc: Exception | str,
        *,
        token_id: str = "",
        market_slug: str = "",
        asset: str = "",
    ) -> dict[str, object]:
        category = self._infer_clob_orderbook_error_category(exc)
        status_code = getattr(exc, "status_code", None)
        if status_code is None:
            response = getattr(exc, "response", None)
            status_code = getattr(response, "status_code", None) if response is not None else None
        if status_code is None and isinstance(exc, ClobOrderbookError):
            status_code = exc.status_code
        try:
            status_code_int = int(status_code) if status_code is not None else None
        except (TypeError, ValueError):
            status_code_int = None
        retry_count = int(
            getattr(
                exc,
                "retry_count",
                self._setting("clob_orderbook_retry_count", self._setting("api_retry_attempts", 1)),
            )
            or 0
        )
        health_detail: dict[str, object] = {}
        get_health = getattr(self.client, "get_orderbook_health", None)
        if callable(get_health) and token_id:
            try:
                health_detail = dict(get_health(token_id))
            except Exception:
                health_detail = {}
        cooldown_remaining = float(
            getattr(exc, "cooldown_seconds_remaining", health_detail.get("clob_cooldown_seconds_remaining", 0.0))
            or 0.0
        )
        circuit_open = bool(getattr(exc, "circuit_open", health_detail.get("clob_circuit_open", False)))
        backoff_active = bool(getattr(exc, "backoff_active", health_detail.get("clob_backoff_active", False)))
        error_rate = float(getattr(exc, "error_rate", health_detail.get("clob_error_rate", 0.0)) or 0.0)
        recovery_count = int(getattr(exc, "recovery_count", health_detail.get("clob_recovery_count", 0)) or 0)
        detail = {
            "clob_error_category": category,
            "clob_error_class": str(getattr(exc, "error_class", "") or health_detail.get("clob_last_error_class", "")),
            "clob_exception_type": getattr(exc, "exception_type", exc.__class__.__name__),
            "clob_status_code": status_code_int,
            "clob_token_id_present": bool(token_id),
            "market_slug": market_slug,
            "asset": asset.upper(),
            "retry_count": retry_count,
            "clob_error_rate": round(error_rate, 4),
            "clob_backoff_active": backoff_active,
            "clob_circuit_open": circuit_open,
            "clob_cooldown_seconds_remaining": round(cooldown_remaining, 3),
            "clob_recovery_count": recovery_count,
            "market_data_degraded": bool(category or backoff_active or circuit_open),
            "clob_parse_failure": bool(getattr(exc, "parse_failure", False)) or category in {"clob_parse_error", "clob_empty_response"},
            "clob_api_failure": bool(getattr(exc, "api_failure", False)) or category in CLOB_ORDERBOOK_ERROR_CATEGORIES,
        }
        for key, value in health_detail.items():
            detail.setdefault(key, value)
        return detail

    def _clob_orderbook_health_detail(
        self,
        token_id: str,
        *,
        market_slug: str = "",
        asset: str = "",
    ) -> dict[str, object]:
        get_health = getattr(self.client, "get_orderbook_health", None)
        if not callable(get_health) or not token_id:
            return {}
        try:
            health = dict(get_health(token_id))
        except Exception:
            return {}
        health.update(
            {
                "market_slug": market_slug,
                "asset": asset.upper(),
                "market_data_degraded": bool(
                    health.get("clob_backoff_active")
                    or health.get("clob_circuit_open")
                    or float(health.get("clob_error_rate", 0.0) or 0.0) >= 0.5
                ),
            }
        )
        return health

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
        if missing_token_ids:
            metrics.skip_reason = "missing_token_id"
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
            recovery_detail = self._empty_book_recovery_detail()
            if token_ids:
                yes_ob, no_ob, recovery_detail = self._fetch_orderbook_pair_with_empty_recovery(
                    ticker=ticker,
                    yes_token_id=token_ids[0],
                    no_token_id=token_ids[1],
                    seconds_remaining=300,
                    market_slug=str(meta.get("slug", "") or ""),
                )
            else:
                yes_ob = no_ob = None
            metrics.empty_book_recovery_attempted = bool(recovery_detail.get("empty_book_recovery_attempted", False))
            metrics.empty_book_recovery_success = bool(recovery_detail.get("empty_book_recovery_success", False))
            metrics.empty_book_recovery_failed = bool(recovery_detail.get("empty_book_recovery_failed", False))
            metrics.empty_book_recovery_retry_count = int(recovery_detail.get("empty_book_recovery_retry_count", 0) or 0)
            metrics.liquidity_state = str(recovery_detail.get("liquidity_state", "HEALTHY") or "HEALTHY")
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
            health_detail = self._clob_orderbook_health_detail(
                token_id,
                market_slug=str(meta.get("slug", "") or ""),
                asset=ticker,
            )
            for key, value in health_detail.items():
                if hasattr(metrics, key):
                    setattr(metrics, key, value)
            readiness_reason = self._classify_orderbook_readiness_reason(
                ticker,
                token_ids=token_ids,
                token_mapping_warning=metrics.token_mapping_warning,
                yes_ask=metrics.yes_ask,
                no_ask=metrics.no_ask,
            )
            metrics.orderbook_readiness_reason = readiness_reason
            metrics.orderbook_unavailable_reason = readiness_reason
            if not metrics.has_orderbook:
                metrics.skip_reason = metrics.skip_reason or readiness_reason or "empty_book"
            if metrics.token_mapping_warning:
                metrics.skip_reason = metrics.skip_reason or readiness_reason or "token_mapping_mismatch"
            if confidence > 0 and metrics.ask > 0:
                metrics.edge_pct = confidence - metrics.ask
                metrics.snipe_score = self._snipe_score(metrics.ask, confidence)
            self._mark_orderbook_refresh(
                ticker,
                source="display_snapshot_sampling",
                trigger="terminal_orderbook_panel",
                executable_yes_no_book=bool(metrics.has_orderbook),
                condition_id=metrics.condition_id,
                yes_token_id=metrics.yes_token_id,
                no_token_id=metrics.no_token_id,
                market_slug=metrics.market_slug,
            )
        except Exception as exc:
            error_detail = self._clob_orderbook_error_detail(
                exc,
                token_id=token_id,
                market_slug=str(meta.get("slug", "") or ""),
                asset=ticker,
            )
            readiness_reason = self._classify_orderbook_readiness_reason(
                ticker,
                token_ids=token_ids,
                token_mapping_warning=metrics.token_mapping_warning,
                orderbook_error=str(exc),
                clob_error_category=str(error_detail.get("clob_error_category", "") or ""),
            )
            metrics.skip_reason = metrics.skip_reason or readiness_reason or "clob_error"
            metrics.orderbook_readiness_reason = readiness_reason
            metrics.orderbook_unavailable_reason = readiness_reason
            metrics.orderbook_error = str(exc)
            metrics.clob_error_category = str(error_detail.get("clob_error_category", "") or "")
            metrics.clob_error_class = str(error_detail.get("clob_error_class", "") or "")
            metrics.clob_exception_type = str(error_detail.get("clob_exception_type", "") or "")
            metrics.clob_status_code = error_detail.get("clob_status_code") if isinstance(error_detail.get("clob_status_code"), int) else None
            metrics.clob_parse_failure = bool(error_detail.get("clob_parse_failure", False))
            metrics.clob_api_failure = bool(error_detail.get("clob_api_failure", False))
            metrics.clob_error_rate = float(error_detail.get("clob_error_rate", 0.0) or 0.0)
            metrics.clob_backoff_active = bool(error_detail.get("clob_backoff_active", False))
            metrics.clob_circuit_open = bool(error_detail.get("clob_circuit_open", False))
            metrics.clob_cooldown_seconds_remaining = float(error_detail.get("clob_cooldown_seconds_remaining", 0.0) or 0.0)
            metrics.clob_recovery_count = int(error_detail.get("clob_recovery_count", 0) or 0)
            metrics.market_data_degraded = bool(error_detail.get("market_data_degraded", False))
            metrics.retry_count = int(error_detail.get("retry_count", 0) or 0)
            self._mark_orderbook_refresh(
                ticker,
                source="display_snapshot_sampling",
                trigger="terminal_orderbook_panel_failed",
                executable_yes_no_book=False,
                condition_id=metrics.condition_id,
                yes_token_id=metrics.yes_token_id,
                no_token_id=metrics.no_token_id,
                market_slug=metrics.market_slug,
            )
            recovery_detail = self._last_empty_book_recovery_detail.get(ticker, {})
            metrics.empty_book_recovery_attempted = bool(recovery_detail.get("empty_book_recovery_attempted", False))
            metrics.empty_book_recovery_success = bool(recovery_detail.get("empty_book_recovery_success", False))
            metrics.empty_book_recovery_failed = bool(recovery_detail.get("empty_book_recovery_failed", False))
            metrics.empty_book_recovery_retry_count = int(recovery_detail.get("empty_book_recovery_retry_count", 0) or 0)
            metrics.liquidity_state = str(recovery_detail.get("liquidity_state", "EMPTY") or "EMPTY")
            LOGGER.warning(
                "[ORDERBOOK_FLOW] ticker=%s outcome=%s token=%s market_slug=%s category=%s exception_type=%s status_code=%s last_successful_orderbook_age_ms=%s retry_count=%s failed=%s",
                ticker,
                outcome,
                token_id,
                meta.get("slug", ""),
                error_detail.get("clob_error_category", ""),
                error_detail.get("clob_exception_type", ""),
                error_detail.get("clob_status_code", ""),
                self._last_orderbook_age_ms.get(ticker, 0),
                error_detail.get("retry_count", 0),
                exc,
            )
            metrics.has_orderbook = False
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
        # Check and alert on TRUE EMPTY state
        is_true_empty = not metrics.has_orderbook
        self._check_and_alert_true_empty(ticker, token_id, is_true_empty)
        return metrics

    def _check_and_alert_true_empty(self, ticker: str, token_id: str, is_true_empty: bool) -> None:
        now = time.time()
        if not hasattr(self, "_true_empty_start_times"):
            self._true_empty_start_times = {}
        if not hasattr(self, "_last_true_empty_alert_times"):
            self._last_true_empty_alert_times = {}

        if is_true_empty:
            if ticker not in self._true_empty_start_times:
                self._true_empty_start_times[ticker] = now
            else:
                elapsed = now - self._true_empty_start_times[ticker]
                if elapsed >= 600:  # 10 minutes threshold
                    last_alert = self._last_true_empty_alert_times.get(ticker, 0.0)
                    # Alert every 10 minutes while TRUE_EMPTY persists
                    if now - last_alert >= 600:
                        self._last_true_empty_alert_times[ticker] = now
                        mins = int(elapsed // 60)
                        message = (
                            f"ORDERBOOK TRUE EMPTY > 10m\n"
                            f"Asset: {ticker.upper()}\n"
                            f"Token: {token_id}\n"
                            f"Cached Book: NO\n"
                            f"Duration: {mins}m"
                        )
                        self._notify_telegram("critical", message, dedup_key=f"true_empty_{ticker}")
        else:
            self._true_empty_start_times.pop(ticker, None)
            self._last_true_empty_alert_times.pop(ticker, None)

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
        micro_timing_candidate = (
            self._micro_adaptive_timing_active()
            and seconds_to_close <= hard_block_seconds
            and seconds_to_close > self._micro_hard_close_floor_seconds()
        )
        if seconds_to_close <= hard_block_seconds and not micro_timing_candidate:
            hard_block_decision = self._evaluate_entry_cutoff(
                seconds_remaining=seconds_to_close,
                static_cutoff_seconds=entry_cutoff,
                orderbook_age_ms=None,
                oracle_age_ms=None,
                decision_latency_ms=None,
                scan_cycle_duration_ms=None,
                spread=0.0,
                liquidity_state="HEALTHY",
            )
            timing_detail.update(self._cutoff_decision_detail(hard_block_decision))
            skip_reason = self._entry_cutoff_skip_reason(seconds_to_close, hard_block_decision)
        elif len(self._open_positions_for_market(market.market_id)) >= int(self._setting("max_active_positions_per_market", 1)):
            skip_reason = "Max active positions per market reached"
        elif self._entry_count_for_market(market.market_id, ptb_info.epoch_start_ts) >= int(self._setting("max_entries_per_market", 1)):
            skip_reason = "Max entries per market reached"
            self._emit_entry_budget_probe_event(
                subtype="gate_fired", site="pre_model",
                ticker=ticker, market_id=market.market_id,
                epoch_start_ts=ptb_info.epoch_start_ts,
                seconds_remaining=float(seconds_to_close),
                lifecycle_phase=str(timing_detail.get("lifecycle_phase", "")),
                trades_before=self._entry_count_for_market(market.market_id, ptb_info.epoch_start_ts),
                max_limit=int(self._setting("max_entries_per_market", 1)),
                model_gate_reached=False,
            )
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
        yes_ob = no_ob = None
        ob_spread = 0.0
        ob_liquidity_usd = float(market.liquidity or 0.0)
        orderbook_error = ""
        token_ids = self._real_token_ids.get(ticker)
        yes_token_id = token_ids[0] if token_ids else market.market_id
        no_token_id = token_ids[1] if token_ids else ""
        meta = self._market_token_meta.get(ticker, {})
        yes_orderbook_age_ms = 0
        no_orderbook_age_ms = 0
        orderbook_fetch_succeeded = False
        clob_error_detail: dict[str, object] = {}
        empty_book_recovery_detail = self._empty_book_recovery_detail()
        token_mapping_warning = self._token_mapping_warning(ticker, token_ids, meta)
        if token_mapping_warning:
            orderbook_readiness_reason = self._classify_orderbook_readiness_reason(
                ticker,
                token_ids=token_ids,
                token_mapping_warning=token_mapping_warning,
            )
            skip_reason = orderbook_readiness_reason or f"token_mapping_warning:{token_mapping_warning}"
            regime_detail = classify_market_regime(
                price_change_pct=getattr(ptb_info, "price_diff_pct", None),
                distance_from_ptb_pct=getattr(ptb_info, "price_diff_pct", None),
                seconds_remaining=seconds_to_close,
                orderbook_spread=ob_spread,
                orderbook_age_ms=self._last_orderbook_age_ms.get(ticker, 0),
                liquidity_state=str(empty_book_recovery_detail.get("liquidity_state", "UNKNOWN") or "UNKNOWN"),
                cutoff_reason=orderbook_readiness_reason,
            ).to_payload()
            detail = {
                **timing_detail,
                **self._orderbook_refresh_observability_detail(
                    ticker,
                    current_executable_yes_no_book=False,
                    current_fetch_succeeded=None,
                    condition_id=meta.get("condition_id", ""),
                    yes_token_id=yes_token_id,
                    no_token_id=no_token_id,
                    market_slug=meta.get("slug", ""),
                    record_decision_cycle=False,
                ),
                "token_id": yes_token_id,
                "yes_token_id": yes_token_id,
                "no_token_id": no_token_id,
                "market_slug": meta.get("slug", ""),
                "condition_id": meta.get("condition_id", ""),
                "outcome": "YES/NO",
                "source_module": "polymarket.trader",
                "token_mapping_warning": token_mapping_warning,
                "orderbook_readiness_reason": orderbook_readiness_reason,
                "orderbook_unavailable_reason": orderbook_readiness_reason,
                "orderbook_error": skip_reason,
                **self._phase2_ev_null_reason_detail(
                    fair_value=None,
                    market_price=None,
                    true_probability=None,
                    ev_after_spread=None,
                    skip_reason=skip_reason,
                    orderbook_readiness_reason=orderbook_readiness_reason,
                    liquidity_state=str(empty_book_recovery_detail.get("liquidity_state", "UNKNOWN") or "UNKNOWN"),
                    spread_normalized=timing_detail.get("spread_normalized"),
                ),
                "last_successful_orderbook_age_ms": self._last_orderbook_age_ms.get(ticker, 0),
                "retry_count": int(self._setting("api_retry_attempts", 1)),
                **regime_detail,
                **self._regime_pass_through_fields(regime_detail),
            }
            self._emit_orderbook_lineage_probe(
                ticker=ticker,
                market_id=market.market_id,
                market_slug=meta.get("slug", ""),
                condition_id=meta.get("condition_id", ""),
                yes_token_id=yes_token_id,
                no_token_id=no_token_id,
                orderbook_fetch_succeeded=None,
                current_executable_yes_no_book=False,
                orderbook_refresh_detail=detail,
                orderbook_readiness_reason=orderbook_readiness_reason,
                orderbook_error=skip_reason,
                empty_book_recovery_detail=empty_book_recovery_detail,
                token_mapping_warning=token_mapping_warning,
                lifecycle_phase=timing_detail.get("lifecycle_phase", ""),
                seconds_remaining=seconds_to_close,
                terminal_blocker_reason=skip_reason,
                terminal_blocker_stage="market_data_token_mapping",
            )
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

        orderbook_fetch_attempt_ts = self._utc_timestamp()
        orderbook_fetch_attempt_mono = time.monotonic()
        orderbook_fetch_complete_ts = ""
        orderbook_fetch_duration_ms = None
        try:
            LOGGER.info(
                "[ORDERBOOK_FLOW] ticker=%s market_slug=%s condition_id=%s yes_token_id=%s no_token_id=%s",
                ticker,
                meta.get("slug", ""),
                meta.get("condition_id", ""),
                yes_token_id,
                no_token_id,
            )

            yes_ob, no_ob, empty_book_recovery_detail = self._fetch_orderbook_pair_with_empty_recovery(
                ticker=ticker,
                yes_token_id=yes_token_id,
                no_token_id=no_token_id,
                seconds_remaining=seconds_to_close,
                market_slug=str(meta.get("slug", "") or ""),
            )
            orderbook_fetch_succeeded = True
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

            if no_token_id and no_ob is not None:
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
            self._mark_orderbook_refresh(
                ticker,
                source="decision_cycle_fetch",
                trigger="candidate_evaluation",
                executable_yes_no_book=bool(yes_bid > 0 and yes_ask > 0 and no_bid > 0 and no_ask > 0),
                condition_id=meta.get("condition_id", ""),
                yes_token_id=yes_token_id,
                no_token_id=no_token_id,
                market_slug=meta.get("slug", ""),
            )
        except Exception as exc:
            orderbook_error = str(exc)
            empty_book_recovery_detail = self._last_empty_book_recovery_detail.get(
                ticker,
                empty_book_recovery_detail,
            )
            self._mark_orderbook_refresh(
                ticker,
                source="decision_cycle_fetch",
                trigger="candidate_evaluation_failed",
                executable_yes_no_book=False,
                condition_id=meta.get("condition_id", ""),
                yes_token_id=yes_token_id,
                no_token_id=no_token_id,
                market_slug=meta.get("slug", ""),
            )
            clob_error_detail = self._clob_orderbook_error_detail(
                exc,
                token_id=yes_token_id,
                market_slug=str(meta.get("slug", "") or ""),
                asset=ticker,
            )
            LOGGER.warning(
                "[OB] Unavailable for %s token_id=%s market_slug=%s outcome=YES/NO category=%s exception_type=%s status_code=%s last_successful_orderbook_age_ms=%s retry_count=%s error=%s",
                market.market_id,
                yes_token_id,
                meta.get("slug", ""),
                clob_error_detail.get("clob_error_category", ""),
                clob_error_detail.get("clob_exception_type", ""),
                clob_error_detail.get("clob_status_code", ""),
                self._last_orderbook_age_ms.get(ticker, 0),
                clob_error_detail.get("retry_count", 0),
                exc,
            )
        orderbook_fetch_complete_ts = self._utc_timestamp()
        orderbook_fetch_duration_ms = round(max(0.0, time.monotonic() - orderbook_fetch_attempt_mono) * 1000.0, 3)

        orderbook_readiness_reason = self._classify_orderbook_readiness_reason(
            ticker,
            token_ids=token_ids,
            token_mapping_warning=token_mapping_warning,
            orderbook_error=orderbook_error,
            clob_error_category=str(clob_error_detail.get("clob_error_category", "") or ""),
            yes_ask=yes_ask,
            no_ask=no_ask,
        )
        clob_health_detail = clob_error_detail or self._clob_orderbook_health_detail(
            yes_token_id,
            market_slug=str(meta.get("slug", "") or ""),
            asset=ticker,
        )
        current_executable_yes_no_book = bool(yes_bid > 0 and yes_ask > 0 and no_bid > 0 and no_ask > 0)
        orderbook_refresh_detail = self._orderbook_refresh_observability_detail(
            ticker,
            current_executable_yes_no_book=current_executable_yes_no_book,
            current_fetch_succeeded=orderbook_fetch_succeeded,
            condition_id=meta.get("condition_id", ""),
            yes_token_id=yes_token_id,
            no_token_id=no_token_id,
            market_slug=meta.get("slug", ""),
            record_decision_cycle=False,
        )
        orderbook_terminal_blocker = (
            orderbook_readiness_reason or "orderbook_unavailable"
            if yes_ask <= 0 or no_ask <= 0 or token_mapping_warning
            else ""
        )
        self._emit_orderbook_lineage_probe(
            ticker=ticker,
            market_id=market.market_id,
            market_slug=meta.get("slug", ""),
            condition_id=meta.get("condition_id", ""),
            yes_token_id=yes_token_id,
            no_token_id=no_token_id,
            yes_ob=yes_ob,
            no_ob=no_ob,
            yes_bid=yes_bid,
            yes_ask=yes_ask,
            yes_bid_size=yes_bid_size,
            yes_ask_size=yes_ask_size,
            no_bid=no_bid,
            no_ask=no_ask,
            no_bid_size=no_bid_size,
            no_ask_size=no_ask_size,
            yes_orderbook_age_ms=yes_orderbook_age_ms,
            no_orderbook_age_ms=no_orderbook_age_ms,
            orderbook_fetch_succeeded=orderbook_fetch_succeeded,
            current_executable_yes_no_book=current_executable_yes_no_book,
            orderbook_refresh_detail=orderbook_refresh_detail,
            orderbook_readiness_reason=orderbook_readiness_reason,
            orderbook_error=orderbook_error,
            clob_error_detail=clob_error_detail,
            empty_book_recovery_detail=empty_book_recovery_detail,
            token_mapping_warning=token_mapping_warning,
            lifecycle_phase=timing_detail.get("lifecycle_phase", ""),
            seconds_remaining=seconds_to_close,
            fetch_attempt_ts=orderbook_fetch_attempt_ts,
            fetch_complete_ts=orderbook_fetch_complete_ts,
            fetch_duration_ms=orderbook_fetch_duration_ms,
            terminal_blocker_reason=orderbook_terminal_blocker,
            terminal_blocker_stage="market_data_orderbook" if orderbook_terminal_blocker else "",
        )
        timing_detail.update(
            self._active_window_alignment_detail(
                ticker=ticker,
                epoch_start=int(getattr(ptb_info, "epoch_start_ts", 0) or timing_detail.get("market_epoch_start", 0) or 0),
                epoch_end=int(getattr(ptb_info, "epoch_end_ts", 0) or timing_detail.get("market_epoch_end", 0) or 0),
                seconds_remaining=seconds_to_close,
                token_ids=token_ids,
                orderbook_ready=not bool(orderbook_readiness_reason),
                nonzero_bidask=current_executable_yes_no_book,
                liquidity_state=str(empty_book_recovery_detail.get("liquidity_state", "HEALTHY") or "HEALTHY"),
                spread=ob_spread,
                spread_limit=float(self._phase2_safe_setting("adaptive_entry_max_spread", 0.06)),
                yes_ob=yes_ob,
                no_ob=no_ob,
            )
        )
        snapshot_regime_detail = classify_market_regime(
            price_change_pct=getattr(ptb_info, "price_diff_pct", None),
            distance_from_ptb_pct=getattr(ptb_info, "price_diff_pct", None),
            seconds_remaining=seconds_to_close,
            orderbook_spread=ob_spread,
            orderbook_age_ms=max(yes_orderbook_age_ms, no_orderbook_age_ms),
            decision_latency_ms=self._cycle_elapsed_ms(),
            liquidity_state=str(empty_book_recovery_detail.get("liquidity_state", "HEALTHY") or "HEALTHY"),
            cutoff_reason=orderbook_readiness_reason,
        ).to_payload()
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
                **timing_detail,
                **orderbook_refresh_detail,
                **empty_book_recovery_detail,
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
                "orderbook_readiness_reason": orderbook_readiness_reason,
                "orderbook_unavailable_reason": orderbook_readiness_reason,
                **self._phase2_ev_null_reason_detail(
                    fair_value=None,
                    market_price=None,
                    true_probability=None,
                    ev_after_spread=None,
                    skip_reason=orderbook_readiness_reason,
                    orderbook_readiness_reason=orderbook_readiness_reason,
                    liquidity_state=str(empty_book_recovery_detail.get("liquidity_state", "HEALTHY") or "HEALTHY"),
                    spread_normalized=timing_detail.get("spread_normalized"),
                ),
                **clob_health_detail,
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
                **snapshot_regime_detail,
                **self._regime_pass_through_fields(snapshot_regime_detail),
            },
        )

        if yes_ask <= 0 or no_ask <= 0 or token_mapping_warning:
            skip_reason = orderbook_readiness_reason or "orderbook_unavailable"
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
                    **orderbook_refresh_detail,
                    "orderbook_error": orderbook_error,
                    "orderbook_readiness_reason": orderbook_readiness_reason,
                    "orderbook_unavailable_reason": orderbook_readiness_reason,
                    **empty_book_recovery_detail,
                    **clob_health_detail,
                    "last_successful_orderbook_age_ms": self._last_orderbook_age_ms.get(ticker, 0),
                    "retry_count": int(self._setting("api_retry_attempts", 1)),
                    "token_mapping_warning": token_mapping_warning,
                    **snapshot_regime_detail,
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
            liquidity_state=str(empty_book_recovery_detail.get("liquidity_state", "HEALTHY") or "HEALTHY"),
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
                    **orderbook_refresh_detail,
                    "oracle_age_ms": int(max(0.0, feed_age or 0.0) * 1000),
                    "spread": float(ob_spread),
                    **empty_book_recovery_detail,
                    "last_successful_orderbook_age_ms": self._last_orderbook_age_ms.get(ticker, 0),
                    "token_mapping_warning": token_mapping_warning,
                    **snapshot_regime_detail,
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
        distance_from_ptb_pct = (window_delta / max(float(ptb_info.price_to_beat), 1e-9)) * 100.0
        regime_detail = classify_market_regime(
            price_change_pct=signal.momentum_pct,
            realized_volatility=recent_volatility,
            price_velocity=price_velocity,
            distance_from_ptb_pct=distance_from_ptb_pct,
            seconds_remaining=ptb_info.seconds_remaining,
            orderbook_spread=ob_spread,
            orderbook_age_ms=max(yes_orderbook_age_ms, no_orderbook_age_ms),
            decision_latency_ms=decision_latency_ms,
            liquidity_state=str(empty_book_recovery_detail.get("liquidity_state", "HEALTHY") or "HEALTHY"),
            cutoff_reason=str(cutoff_detail.get("adaptive_cutoff_reason", "") or ""),
        ).to_payload()

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
            "yes_bid_size": float(yes_bid_size),
            "yes_ask_size": float(yes_ask_size),
            "no_bid": float(no_bid),
            "no_ask": float(no_ask),
            "no_bid_size": float(no_bid_size),
            "no_ask_size": float(no_ask_size),
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
            "price_change_pct": float(signal.momentum_pct),
            "realized_volatility": float(recent_volatility),
            "price_velocity": float(price_velocity),
            "distance_from_ptb_pct": float(distance_from_ptb_pct),
            **regime_detail,
            "market_regime": str(getattr(signal, "market_regime", "") or regime_detail.get("market_regime", "UNKNOWN")),
            "bullish_probability": float(getattr(signal, "bullish_probability", probability.p_yes) or probability.p_yes),
            "bearish_probability": float(getattr(signal, "bearish_probability", probability.p_no) or probability.p_no),
            "reversal_risk": float(getattr(signal, "reversal_risk", 0.0) or 0.0),
            "compression_score": float(getattr(signal, "compression_score", 0.0) or 0.0),
            "signal_trend_strength": float(getattr(signal, "trend_strength", regime_detail.get("trend_strength", 0.0)) or 0.0),
            "signal_volatility_score": float(getattr(signal, "volatility_score", regime_detail.get("volatility_score", 0.0)) or 0.0),
            "indicator_evidence": str(getattr(signal, "indicator_evidence", "") or ""),
            "signal_name": signal.signal_name,
            "signal_reason": signal.signal_reason,
            "candidate_instance_id": candidate.candidate_id,
            "candidate_instance_trace_id": candidate.candidate_trace_id,
            "candidate_instance_created_at": candidate.candidate_created_at,
            "candidate_instance_identity_schema_version": candidate.candidate_identity_schema_version,
            "candidate_instance_identity_source": "opportunity_candidate",
            "legacy_candidate_identity_source": "phase2_market_side_epoch_hash",
            # Observability v1: probability model inputs (additive, read-only, no model change)
            "probability_model_reason": str(probability.model_reason),
            "prob_model_momentum_input": float(momentum_decimal),
            "prob_model_liquidity_usd": float(ob_liquidity_usd),
            **orderbook_refresh_detail,
        }
        is_model_trade = model_side in ("YES", "NO") and ev_result is not None and ev_result.approved
        clob_detail["strategy_signal_name"] = signal.signal_name
        clob_detail["strategy_signal_reason"] = signal.signal_reason
        if is_model_trade:
            clob_detail["signal_name"] = "PROBABILITY_EV_EDGE"
            clob_detail["signal_reason"] = f"{model_side.lower()}_ev_above_threshold"

            # Passive Phase B Shadow Telemetry
            if getattr(self.settings, "shadow_telemetry_enabled", False):
                self._evaluate_passive_shadow_telemetry(
                    ticker=ticker,
                    candidate=candidate,
                    probability=probability,
                    model_side=model_side,
                    model_ev=model_ev,
                    regime_detail=regime_detail,
                    ptb_info=ptb_info,
                    meta=meta,
                    yes_token_id=yes_token_id,
                    no_token_id=no_token_id,
                    ob_spread=ob_spread,
                    ob_liquidity_usd=ob_liquidity_usd,
                    trades_last_hour=trades_last_hour,
                    daily_drawdown_pct=daily_drawdown_pct,
                    risk_off=risk_off,
                )

            # Evaluate shadow filters in paper mode only
            if self._runtime_mode() == "paper":
                self._baseline_accepted += 1
                shadow_filter_reasons = []
                ev_cap_shadow_reject = False
                yes_floor_shadow_reject = False

                if model_ev >= 0.15:
                    ev_cap_shadow_reject = True
                    shadow_filter_reasons.append("ev_cap_toxicity")
                    self._ev_cap_shadow_rejects += 1

                entry_prob = probability.p_yes if model_side == "YES" else probability.p_no
                if model_side == "YES" and entry_prob < 0.60:
                    yes_floor_shadow_reject = True
                    shadow_filter_reasons.append("yes_probability_floor")
                    self._yes_floor_shadow_rejects += 1

                shadow_would_reject = ev_cap_shadow_reject or yes_floor_shadow_reject
                if shadow_would_reject:
                    self._shadow_would_reject += 1

                if self.quant_events:
                    import uuid
                    shadow_decision_id = f"sd_{uuid.uuid4().hex[:16]}"
                    candidate_trace_id = candidate.candidate_trace_id
                    run_fragment = self.quant_events.run_id[:8] if self.quant_events.run_id else "norund"
                    replay_chain_id = f"rc_{run_fragment}_{candidate_trace_id[3:]}" if candidate_trace_id else "rc_missing"

                    selected_token_id = yes_token_id if model_side == "YES" else no_token_id
                    paper_trade_replay_key = f"{meta.get('condition_id', '')}|{ptb_info.epoch_start_ts}|{ticker}|{model_side}|{selected_token_id}"
                    timestamp_utc = self.quant_events._timestamp()

                    shadow_payload = {
                        "filter_version": "signal_filter_v1_shadow",
                        "run_id": self.quant_events.run_id,
                        "candidate_trace_id": candidate_trace_id,
                        "candidate_instance_id": candidate.candidate_id,
                        "shadow_decision_id": shadow_decision_id,
                        "market": market.market_id,
                        "ticker": ticker,
                        "selected_side": model_side,
                        "signal_reason": f"{model_side.lower()}_ev_above_threshold",
                        "entry_ev": float(model_ev),
                        "entry_probability": float(entry_prob),
                        "ev_cap_threshold": 0.15,
                        "yes_prob_floor": 0.60,
                        "baseline_approved": True,
                        "shadow_would_reject": shadow_would_reject,
                        "shadow_filter_reasons": shadow_filter_reasons,
                        "shadow_outcome": None,
                        "shadow_outcome_pnl": None,
                        "replay_chain_id": replay_chain_id,
                        "paper_trade_replay_key": paper_trade_replay_key,
                        "position_id": None,
                        "timestamp_utc": timestamp_utc,

                        # companion mapping fields for logger digest
                        "market_key": market.market_id,
                        "condition_id": meta.get("condition_id", ""),
                        "token_id": selected_token_id,
                        "epoch_start_ts": ptb_info.epoch_start_ts,
                        "side": model_side,
                    }
                    self.quant_events.log_signal_filter_shadow(shadow_payload)

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
            self._emit_entry_budget_probe_event(
                subtype="gate_fired", site="post_model",
                ticker=ticker, market_id=market.market_id,
                epoch_start_ts=ptb_info.epoch_start_ts,
                seconds_remaining=float(seconds_to_close),
                lifecycle_phase=str(timing_detail.get("lifecycle_phase", "")),
                trades_before=self._entry_count_for_market(market.market_id, ptb_info.epoch_start_ts),
                max_limit=int(self._setting("max_entries_per_market", 1)),
                model_gate_reached=True,
                ev_computed=True,
            )
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
            if skip_reason == "delta_extreme" and getattr(self.settings, "delta_shadow_enabled", False):
                try:
                    self._evaluate_and_log_delta_extreme_shadow(
                        market=market,
                        ticker=ticker,
                        ptb_info=ptb_info,
                        model_side=model_side,
                        confidence=confidence,
                        model_ev=model_ev,
                        delta=delta,
                        ob_spread=ob_spread,
                        ob_liquidity_usd=ob_liquidity_usd,
                        yes_token_id=yes_token_id,
                        no_token_id=no_token_id,
                        yes_bid=yes_bid,
                        yes_ask=yes_ask,
                        yes_bid_size=yes_bid_size,
                        yes_ask_size=yes_ask_size,
                        no_bid=no_bid,
                        no_ask=no_ask,
                        no_bid_size=no_bid_size,
                        no_ask_size=no_ask_size,
                        yes_orderbook_age_ms=yes_orderbook_age_ms,
                        no_orderbook_age_ms=no_orderbook_age_ms,
                        feed_age=feed_age,
                        current_balance=current_balance,
                        timing_detail=timing_detail,
                    )
                except Exception as exc:
                    LOGGER.exception("Error in delta shadow overlay: %s", exc)

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
        min_position_size_usd = self._entry_min_position_size_usd(
            bankroll=current_balance,
            entry_price=entry_price,
        )
        order_request = OrderRequest(market_id=market.market_id, side=model_side, entry_price=entry_price, win_rate=probability.p_yes if model_side == "YES" else probability.p_no, reward_risk_ratio=2.0, edge=model_ev, price_to_beat=ptb_info.price_to_beat, spread=ob_spread, liquidity_usd=ob_liquidity_usd, delta=delta.delta_score, delta_multiplier=delta.delta_multiplier, time_remaining_seconds=ptb_info.seconds_remaining, trades_last_hour=trades_last_hour, drawdown_pct=daily_drawdown_pct, min_position_size_usd=min_position_size_usd, daily_loss_limit_reached=risk_off, hard_drawdown_reached=daily_drawdown_pct >= 0.15)
        risk_plan = self.order_manager.build_order_plan(order_request)
        risk_plan = self._maybe_apply_micro_survival_plan(
            risk_plan,
            current_balance=current_balance,
            entry_price=entry_price,
        )
        if risk_plan.position_size > 0 and size_multiplier < 1.0:
            risk_plan.risk_amount = round(risk_plan.risk_amount * size_multiplier, 6)
            risk_plan.position_size = round(risk_plan.position_size * size_multiplier, 6)
            risk_plan.notional_size = round(risk_plan.notional_size * size_multiplier, 6)
        if risk_plan.position_size > 0:
            self._apply_risk_mode_to_plan(risk_plan, risk_mode_decision)

        if risk_plan.position_size <= 0:
            self._emit_zero_size_probe_event(
                ticker=ticker,
                market_id=market.market_id,
                risk_plan=risk_plan,
                ptb_info=ptb_info,
                timing_detail=timing_detail,
                confidence=confidence,
                ev=model_ev,
                entry_price=entry_price,
            )
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

        if (
            risk_plan.position_size < self.settings.min_shares_per_order
            and not self._micro_survival_allows_fractional_shares(bankroll=current_balance)
        ):
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

        # ENTRY_MODEL_TRUTH_ENVELOPE_V1 — compute _true_prob before position open so it can be stored in metadata
        _true_prob = probability.p_yes if model_side == "YES" else probability.p_no if model_side == "NO" else None
        if receipt is not None:
            opened_pos = self.tracker.open_position(
                symbol=market.market_id,
                source="polymarket",
                side="BUY",
                entry_price=entry_price,
                size=risk_plan.position_size,
                stop_loss=risk_plan.stop_loss_price,
                take_profit=entry_price * (1 + float(self._setting("execution_take_profit_pct", 0.10))),
                order_id=receipt.order_id,
                metadata=self._build_trade_position_metadata(
                    strategy=quant_decision,
                    signal_strategy=signal.strategy,
                    token_id=clob_token_id,
                    outcome=model_side,
                    entry_ev=model_ev,
                    confidence=confidence,
                    delta_regime=delta.delta_regime.value,
                    condition_id=meta.get("condition_id", ""),
                    epoch_start_ts=int(ptb_info.epoch_start_ts or 0),
                    market_slug=meta.get("market_slug", ""),
                    lifecycle_phase=timing_detail.get("lifecycle_phase", ""),
                    ticker=ticker,
                    true_probability=_true_prob,
                    fair_value=_true_prob,
                    signal_name=clob_detail.get("signal_name"),
                    signal_reason=clob_detail.get("signal_reason"),
                    strategy_signal_name=clob_detail.get("strategy_signal_name"),
                    strategy_signal_reason=clob_detail.get("strategy_signal_reason"),
                ),
            )
            self._placed_epochs[ticker] = ptb_info.epoch_start_ts
            self._record_market_entry(market.market_id, ptb_info.epoch_start_ts)
            self._emit_entry_budget_probe_event(
                subtype="slot_consumed", site="quant_fill",
                ticker=ticker, market_id=market.market_id,
                epoch_start_ts=ptb_info.epoch_start_ts,
                seconds_remaining=float(ptb_info.seconds_remaining),
                lifecycle_phase=str(timing_detail.get("lifecycle_phase", "")),
                trades_before=self._entry_count_for_market(market.market_id, ptb_info.epoch_start_ts) - 1,
                max_limit=int(self._setting("max_entries_per_market", 1)),
                model_gate_reached=True,
                ev_computed=True,
                size_plan_value=float(getattr(risk_plan, "position_size", 0.0) or 0.0),
                real_order_attempted=True,
                paper_fill_occurred=bool(self.settings.paper_trading),
                consumed_reason="paper_fill" if self.settings.paper_trading else "live_fill",
            )
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
                seconds_remaining=int(ptb_info.seconds_remaining),
                epoch_start=int(getattr(ptb_info, "epoch_start_ts", 0) or 0),
                condition_id=meta.get("condition_id", ""),
                true_probability=_true_prob,
                ev_after_spread=float(model_ev) if model_ev is not None else None,
                confidence=float(confidence) if confidence is not None else None,
                position_id=opened_pos.position_id,
                entry_attribution=opened_pos.metadata.get("entry_attribution"),
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
            self._emit_entry_budget_probe_event(
                subtype="gate_fired", site="pre_order",
                ticker=ticker, market_id=market.market_id,
                epoch_start_ts=ptb_info.epoch_start_ts,
                seconds_remaining=float(ptb_info.seconds_remaining),
                lifecycle_phase=str(timing_detail.get("lifecycle_phase", "")),
                trades_before=market_entry_count,
                max_limit=max_entries_per_market,
                model_gate_reached=True,
                ev_computed=True,
                size_plan_value=float(getattr(risk_plan, "position_size", 0.0) or 0.0),
            )
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
            self._emit_entry_budget_probe_event(
                subtype="slot_consumed", site="legacy_fill",
                ticker=ticker, market_id=market.market_id,
                epoch_start_ts=ptb_info.epoch_start_ts,
                seconds_remaining=float(ptb_info.seconds_remaining),
                lifecycle_phase=str(timing_detail.get("lifecycle_phase", "")),
                trades_before=self._entry_count_for_market(market.market_id, ptb_info.epoch_start_ts) - 1,
                max_limit=int(self._setting("max_entries_per_market", 1)),
                model_gate_reached=False,
                ev_computed=False,
                size_plan_value=float(getattr(risk_plan, "position_size", 0.0) or 0.0),
                real_order_attempted=True,
                paper_fill_occurred=bool(self.settings.paper_trading),
                consumed_reason="paper_fill" if self.settings.paper_trading else "live_fill",
            )
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
                if self.settings.paper_trading:
                    self._emit_path_truth_checkpoint(
                        pos,
                        checkpoint_elapsed_s="event_end",
                        checkpoint_reason="event_end",
                        now=datetime.now(UTC),
                        market_state={"current_mark_price": price},
                    )
                closed = self.tracker.close_position(pos.position_id, price, reason=reason)
                self._consecutive_raw_breach_seconds.pop(pos.position_id, None)
                self._consecutive_mid_breach_seconds.pop(pos.position_id, None)
                self._consecutive_ob_unavailable_seconds.pop(pos.position_id, None)
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

        self._maybe_emit_path_truth_checkpoints(open_pos)

        stop_loss_pct = float(self._setting("execution_stop_loss_pct", 0.08))
        for pos in open_pos:
            mark_price = self._position_mark_price(pos)
            unrealized_pct = self._unrealized_pct(pos, mark_price)
            ticker = pos.symbol.replace("pm-5m-", "").upper()

            # -------------------------------------------------------------
            # STOP-LOSS SHADOW POLICY EVALUATION (PATCH_STOP_001)
            # -------------------------------------------------------------
            ob = None
            orderbook_available = True
            token_id = self._position_token_id(pos)

            try:
                ob = self.client.get_orderbook(token_id)
            except Exception as exc:
                LOGGER.warning("[STOP_LOSS_SHADOW] failed to fetch orderbook for symbol=%s token_id=%s: %s", pos.symbol, token_id, exc)
                orderbook_available = False

            # Initialize all values
            raw_bid = 0.0
            raw_ask = 0.0
            bid_size = 0.0
            ask_size = 0.0
            midpoint = 0.0
            depth_ok = False

            unrealized_raw_bid_pct = 0.0
            unrealized_mid_pct = 0.0
            unrealized_mid_depth_pct = 0.0

            actual_raw_bid_stop = False
            shadow_mid_stop = False
            shadow_mid_depth_stop = False
            shadow_raw_2sample_stop = False
            shadow_raw_3sample_stop = False
            shadow_mid_3sample_stop = False

            pos_id = pos.position_id

            if orderbook_available and ob is not None:
                raw_bid = float(ob.best_bid)
                raw_ask = float(ob.best_ask)
                bid_size = float(ob.bid_size)
                ask_size = float(ob.ask_size)

                if raw_bid > 0 and raw_ask > 0:
                    midpoint = (raw_bid + raw_ask) / 2.0
                else:
                    midpoint = raw_bid if raw_bid > 0 else float(pos.entry_price)

                # Check depth
                depth_ok = (bid_size >= 10.0 and ask_size >= 10.0)

                # Calculations
                entry_price_val = float(pos.entry_price)
                if entry_price_val > 0:
                    if raw_bid > 0:
                        unrealized_raw_bid_pct = (raw_bid - entry_price_val) / entry_price_val
                    else:
                        unrealized_raw_bid_pct = 0.0

                    if midpoint > 0:
                        unrealized_mid_pct = (midpoint - entry_price_val) / entry_price_val
                    else:
                        unrealized_mid_pct = 0.0

                    if depth_ok:
                        unrealized_mid_depth_pct = unrealized_mid_pct
                    else:
                        unrealized_mid_depth_pct = 0.0

                # Threshold check
                actual_raw_bid_stop = (unrealized_raw_bid_pct <= -stop_loss_pct)
                shadow_mid_stop = (unrealized_mid_pct <= -stop_loss_pct)
                shadow_mid_depth_stop = (unrealized_mid_depth_pct <= -stop_loss_pct)

                # Raw bid counters
                if actual_raw_bid_stop:
                    self._consecutive_raw_breach_seconds[pos_id] = self._consecutive_raw_breach_seconds.get(pos_id, 0) + 1
                else:
                    self._consecutive_raw_breach_seconds[pos_id] = 0

                # Mid price counters
                if shadow_mid_stop:
                    self._consecutive_mid_breach_seconds[pos_id] = self._consecutive_mid_breach_seconds.get(pos_id, 0) + 1
                else:
                    self._consecutive_mid_breach_seconds[pos_id] = 0

                consecutive_raw_count = self._consecutive_raw_breach_seconds[pos_id]
                consecutive_mid_count = self._consecutive_mid_breach_seconds[pos_id]

                # Decisions
                shadow_raw_2sample_stop = (consecutive_raw_count >= 2)
                shadow_raw_3sample_stop = (consecutive_raw_count >= 3)
                shadow_mid_3sample_stop = (consecutive_mid_count >= 3)
                # PATCH_STOP_002 / PAPER_STOP_FAILSAFE: reset OB unavailable counter on success
                self._consecutive_ob_unavailable_seconds[pos_id] = 0
            else:
                # If orderbook unavailable, reset breach counters for safety
                self._consecutive_raw_breach_seconds[pos_id] = 0
                self._consecutive_mid_breach_seconds[pos_id] = 0
                consecutive_raw_count = 0
                consecutive_mid_count = 0
                # PATCH_STOP_002 / PAPER_STOP_FAILSAFE: track consecutive OB failures
                self._consecutive_ob_unavailable_seconds[pos_id] = (
                    self._consecutive_ob_unavailable_seconds.get(pos_id, 0) + 1
                )

            ob_unavailable_consecutive = self._consecutive_ob_unavailable_seconds.get(pos_id, 0)
            ob_freeze_active = ob_unavailable_consecutive > 0

            # ------------------------------------------------------------------
            # PATCH_STOP_002: Paper/Live Stop Trigger Decision
            # Paper mode: requires mid-price + 3-sample confirmation to trigger.
            # Live mode: unchanged — single-tick raw-bid trigger.
            # ------------------------------------------------------------------
            _raw_bid_would_stop = (unrealized_pct <= -stop_loss_pct)
            if _raw_bid_would_stop:
                if self.settings.paper_trading:
                    _should_stop = shadow_mid_3sample_stop
                    _close_reason = "stop_loss"
                    _suppressed = not shadow_mid_3sample_stop
                    if not shadow_mid_stop:
                        _suppression_reason = "mid_not_breached"
                    elif consecutive_mid_count < 3:
                        _suppression_reason = "confirmation_count_below_3"
                    else:
                        _suppression_reason = ""
                else:
                    # Live mode: unchanged — raw-bid single-sample trigger
                    _should_stop = True
                    _close_reason = "stop_loss"
                    _suppressed = False
                    _suppression_reason = ""
            else:
                _should_stop = False
                _close_reason = ""
                _suppressed = False
                _suppression_reason = ""

            # Log shadow stop event (to stop_loss_shadow folder)
            if self.quant_events is not None:
                ts_utc = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                run_id_val = getattr(self.quant_events, "run_id", None)
                payload = {
                    "position_id": pos.position_id,
                    "market": pos.symbol,
                    "ticker": ticker,
                    "side": self._position_outcome(pos),
                    "entry_price": float(pos.entry_price),
                    "raw_bid": raw_bid,
                    "raw_ask": raw_ask,
                    "midpoint": midpoint,
                    "bid_size": bid_size,
                    "ask_size": ask_size,
                    "depth_ok": depth_ok,
                    "unrealized_raw_bid_pct": unrealized_raw_bid_pct,
                    "unrealized_mid_pct": unrealized_mid_pct,
                    "unrealized_mid_depth_pct": unrealized_mid_depth_pct,
                    "stop_threshold_pct": stop_loss_pct,
                    "consecutive_raw_breach_count": consecutive_raw_count,
                    "consecutive_mid_breach_count": consecutive_mid_count,
                    "orderbook_available": orderbook_available,
                    "actual_raw_bid_stop": actual_raw_bid_stop,
                    "shadow_mid_stop": shadow_mid_stop,
                    "shadow_mid_depth_stop": shadow_mid_depth_stop,
                    "shadow_raw_2sample_stop": shadow_raw_2sample_stop,
                    "shadow_raw_3sample_stop": shadow_raw_3sample_stop,
                    "shadow_mid_3sample_stop": shadow_mid_3sample_stop,
                    # PATCH_STOP_002: paper-gated stop telemetry
                    "paper_stop_policy_active": bool(getattr(self.settings, "paper_trading", False)),
                    "paper_mid_confirmed_stop": bool(_should_stop and getattr(self.settings, "paper_trading", False)),
                    "paper_stop_suppressed": bool(_suppressed),
                    "paper_stop_suppression_reason": _suppression_reason,
                    "actual_stop_triggered": bool(_should_stop),
                    # PAPER_STOP_FAILSAFE: OB unavailable tracking
                    "orderbook_unavailable_consecutive_count": ob_unavailable_consecutive,
                    "ob_unavailable_consecutive_count": ob_unavailable_consecutive,
                    "ob_freeze_active": ob_freeze_active,
                    "ob_freeze_hold_reason": "orderbook_unavailable" if ob_freeze_active else "",
                    "timestamp_utc": ts_utc,
                    "run_id": run_id_val,
                }
                self.quant_events.log_stop_loss_shadow(payload)

            if _should_stop:
                if self.settings.paper_trading:
                    LOGGER.warning(
                        "[STOP_LOSS_PAPER] market=%s position=%s ticker=%s "
                        "raw_bid_pct=%.2f%% mid_pct=%.2f%% mid_count=%d/3 <= -%.2f%% exit_price=%.4f",
                        pos.symbol, pos.position_id, ticker,
                        unrealized_raw_bid_pct * 100, unrealized_mid_pct * 100,
                        consecutive_mid_count, stop_loss_pct * 100, mark_price,
                    )
                else:
                    LOGGER.warning(
                        "[STOP_LOSS] market=%s position=%s ticker=%s unrealized=%.2f%% <= -%.2f%% exit_price=%.4f",
                        pos.symbol, pos.position_id, ticker, unrealized_pct * 100,
                        stop_loss_pct * 100, mark_price,
                    )
                self._close_position_with_retry(pos, reason=_close_reason, exit_price=mark_price)
            elif _raw_bid_would_stop and _suppressed:
                LOGGER.debug(
                    "[STOP_LOSS_PAPER_HOLD] suppressed: position=%s raw_bid_pct=%.2f%% mid_pct=%.2f%% "
                    "mid_count=%d/3 reason=%s",
                    pos.position_id, unrealized_raw_bid_pct * 100, unrealized_mid_pct * 100,
                    consecutive_mid_count, _suppression_reason,
                )
            else:
                LOGGER.debug(
                    "[STOP_LOSS] hold | market=%s position=%s unrealized=%.2f%% limit=-%.2f%%",
                    pos.symbol, pos.position_id, unrealized_pct * 100, stop_loss_pct * 100,
                )

            # PAPER_STOP_FAILSAFE: critical alert after 5 consecutive OB unavailable cycles
            if ob_unavailable_consecutive >= 5:
                LOGGER.critical(
                    "[STOP_LOSS_OB_FREEZE] CRITICAL: position=%s market=%s ticker=%s "
                    "has had no orderbook data for %d consecutive seconds. "
                    "Paper stop evaluation frozen. Manual review recommended.",
                    pos.position_id, pos.symbol, ticker, ob_unavailable_consecutive,
                )
                if ob_unavailable_consecutive == 5:
                    self._emit_quant_event(
                        "log_system_health",
                        {
                            "event": "stop_loss_orderbook_unavailable_critical",
                            "severity": "critical",
                            "position_id": pos.position_id,
                            "market": pos.symbol,
                            "ticker": ticker,
                            "token_id": token_id,
                            "mode": self._runtime_mode(),
                            "paper_trading": bool(self.settings.paper_trading),
                            "orderbook_unavailable_consecutive_count": ob_unavailable_consecutive,
                            "action_taken": "none",
                            "emergency_close_triggered": False,
                            "last_valid_mid_cache_used": False,
                        },
                    )

            # --- OPTION D SHADOW TELEMETRY HOOK (PATCH_001) ---
            if getattr(self.settings, "option_d_shadow_enabled", False):
                try:
                    # Update metadata with actual stop info for evaluation
                    pos_metadata = getattr(pos, "metadata", None)
                    if not isinstance(pos_metadata, dict):
                        pos_metadata = {}
                        try:
                            pos.metadata = pos_metadata
                        except Exception:
                            pass
                    if isinstance(pos_metadata, dict):
                        pos_metadata["actual_stop_triggered"] = bool(_should_stop)
                        pos_metadata["actual_exit_reason"] = _close_reason if _should_stop else ""

                    shadow_payload = evaluate_option_d_shadow(
                        pos,
                        ob,
                        datetime.now(UTC),
                        self.settings
                    )
                    if self.quant_events is not None:
                        self.quant_events.log_stop_loss_shadow(shadow_payload)
                except Exception as exc:
                    LOGGER.error("[STOP_LOSS_SHADOW] Option D Shadow evaluator error for symbol=%s: %s", pos.symbol, exc)
                    try:
                        self._emit_quant_event(
                            "log_system_health",
                            {
                                "event": "option_d_shadow_evaluator_error",
                                "severity": "error",
                                "position_id": pos.position_id,
                                "market": pos.symbol,
                                "error": str(exc),
                                "mode": self._runtime_mode(),
                            }
                        )
                    except Exception:
                        pass
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

        self._maybe_emit_path_truth_checkpoints(open_pos)

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
                    "risk_state": "missing_intent",
                    "risk_mode": self._risk_mode_state.current_mode.value,
                    "execution_context_source": "order_intent_validation",
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
            order_intent_ts = self._utc_timestamp()
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
                    "risk_state": "approved",
                    "risk_mode": self._risk_mode_state.current_mode.value,
                    "risk_plan_present": risk_plan is not None,
                    "risk_approved": bool(risk_plan and risk_plan.position_size > 0 and risk_plan.notional_size > 0),
                    "execution_context_source": "order_intent_validation",
                    "mode": self._runtime_mode(),
                    "order_intent_ts": order_intent_ts,
                    "timestamp_source": "order_intent_approved",
                    "latency_truth_level": self._phase1_execution_latency_truth_level(),
                    **{k: v for k, v in self._phase4_quote_lineage_carry(
                        self._ticker_from_market_id(source_market_id)
                    ).items() if k in ("quote_lineage_id", "quote_capture_ts")},
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
                "risk_state": "blocked",
                "risk_mode": self._risk_mode_state.current_mode.value,
                "risk_plan_present": risk_plan is not None,
                "risk_approved": False,
                "execution_context_source": "order_intent_validation",
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
        risk_approved = bool(risk_plan and risk_plan.position_size > 0 and risk_plan.notional_size > 0)
        execution_risk_context = {
            "risk_state": "approved" if risk_approved else "blocked",
            "risk_mode": self._risk_mode_state.current_mode.value,
            "risk_plan_present": risk_plan is not None,
            "risk_approved": risk_approved,
        }

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

        order_submit_ts = self._utc_timestamp()
        _p4_submit_ticker = self._ticker_from_market_id(source_market_id)
        _p4_submit_ql = self._phase4_quote_lineage_carry(_p4_submit_ticker)
        if not _p4_submit_ql.get("quote_lineage_id"):
            _p4_submit_ql = self._phase4_build_quote_lineage(source_market_id, _p4_submit_ticker)
        _p5_quote_age_at_submit_ms = (
            self._phase3_paper_proxy_ms(str(_p4_submit_ql.get("quote_capture_ts") or ""), order_submit_ts)
            if self.settings.paper_trading else None
        )
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
                **execution_risk_context,
                "mode": self._runtime_mode(),
                "order_submit_ts": order_submit_ts,
                "timestamp_source": "order_submit_attempt",
                "latency_truth_level": self._phase1_execution_latency_truth_level(),
                "quote_lineage_id": _p4_submit_ql.get("quote_lineage_id"),
                "quote_capture_ts": _p4_submit_ql.get("quote_capture_ts"),
                "quote_source": _p4_submit_ql.get("quote_source", "unknown"),
                "quote_age_at_submit_ms": _p5_quote_age_at_submit_ms,
            },
        )

        if self.settings.paper_trading:
            self.paper_stats.paper_orders_created += 1
            LOGGER.info(
                "[PAPER ORDER] side=%s type=LIMIT market=%s tier=%s price=%.4f size=%.6f live_orders=OFF",
                side, market_id, tier_label, live_limit_price, size,
            )
            order_ack_ts = self._utc_timestamp()
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
            fill_ts = self._utc_timestamp()
            submit_to_ack_ms = self._phase3_paper_proxy_ms(order_submit_ts, order_ack_ts)
            submit_to_fill_ms = self._phase3_paper_proxy_ms(order_submit_ts, fill_ts)
            _p5_quote_age_at_fill_ms = self._phase3_paper_proxy_ms(
                str(_p4_submit_ql.get("quote_capture_ts") or ""), fill_ts
            )
            try:
                _p6_quote_stale_ms = (
                    float(max(_p5_quote_age_at_submit_ms, _p5_quote_age_at_fill_ms))
                    if _p5_quote_age_at_submit_ms is not None and _p5_quote_age_at_fill_ms is not None
                    else None
                )
            except Exception:
                _p6_quote_stale_ms = None
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
                    **execution_risk_context,
                    "mode": self._runtime_mode(),
                    "order_ack_ts": order_ack_ts,
                    "fill_ts": fill_ts,
                    "ack_source": "paper_simulated",
                    "fill_source": "paper_simulated",
                    "timestamp_source": "paper_fill_emit",
                    "latency_truth_level": "paper_simulated",
                    "submit_to_ack_ms": submit_to_ack_ms,
                    "submit_to_fill_ms": submit_to_fill_ms,
                    "derived_metric_source": "paper_proxy",
                    "quote_lineage_id": _p4_submit_ql.get("quote_lineage_id"),
                    "quote_capture_ts": _p4_submit_ql.get("quote_capture_ts"),
                    "quote_source": _p4_submit_ql.get("quote_source", "unknown"),
                    "quote_age_at_submit_ms": _p5_quote_age_at_submit_ms,
                    "quote_age_at_fill_ms": _p5_quote_age_at_fill_ms,
                    "quote_stale_ms": _p6_quote_stale_ms,
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
                    **execution_risk_context,
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
                    **execution_risk_context,
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
                new_balance = self._risk_mgr.balance + total_redeemed
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
                    bankroll=self._risk_mgr.balance,
                    paper=self.settings.paper_trading,
                ),
                dedup_key=f"settlement:{pos.position_id}",
                market=symbol,
                reason="settlement",
            )

    # ------------------------------------------------------------------
    # Entry Budget Consumption Probe v1 — observability only, fail-soft
    # ------------------------------------------------------------------

    def _emit_entry_budget_probe_event(
        self,
        *,
        subtype: str,
        site: str,
        ticker: str,
        market_id: str,
        epoch_start_ts: int,
        seconds_remaining: float,
        lifecycle_phase: str,
        trades_before: int,
        max_limit: int,
        model_gate_reached: bool = False,
        ev_computed: bool = False,
        size_plan_value: float = 0.0,
        real_order_attempted: bool = False,
        paper_fill_occurred: bool = False,
        consumed_reason: str = "",
    ) -> None:
        """Emit one system_health event capturing entry-budget slot state.

        Additive-only. Fail-soft. No strategy/risk/execution side effects.
        subtype='gate_fired'   — max_entries guard returned skip (slot already consumed).
        subtype='slot_consumed' — _record_market_entry just called after real fill.
        """
        try:
            trades_after = trades_before + (1 if subtype == "slot_consumed" else 0)
            no_order = subtype == "slot_consumed" and not real_order_attempted
            no_fill  = subtype == "slot_consumed" and not paper_fill_occurred
            payload: dict[str, object] = {
                "event": "entry_budget_probe_v1",
                "event_subtype": subtype,
                "site": site,
                "ticker": ticker,
                "market_id": market_id,
                "epoch_start_ts": int(epoch_start_ts),
                "seconds_remaining": round(float(seconds_remaining), 1),
                "lifecycle_phase": str(lifecycle_phase),
                "trades_for_market_before": int(trades_before),
                "trades_for_market_after": int(trades_after),
                "max_entries_limit": int(max_limit),
                # gate_fired
                "slot_already_consumed": subtype == "gate_fired",
                # slot_consumed
                "model_gate_reached": bool(model_gate_reached),
                "ev_computed": bool(ev_computed),
                "size_plan_value": round(float(size_plan_value), 6),
                "real_order_attempted": bool(real_order_attempted),
                "paper_fill_occurred": bool(paper_fill_occurred),
                "entry_budget_consumed": subtype == "slot_consumed",
                "entry_budget_consumed_reason": str(consumed_reason or subtype),
                "entry_budget_consumed_without_order": bool(no_order),
                "entry_budget_consumed_without_fill": bool(no_fill),
                "entry_budget_consumed_after_zero_size": size_plan_value == 0.0 and subtype == "slot_consumed",
                "entry_budget_consumed_after_opening_scan": "OPENING_SCAN" in str(lifecycle_phase).upper() and subtype == "slot_consumed",
                "entry_budget_consumed_after_cutoff": "cutoff" in str(consumed_reason).lower() and subtype == "slot_consumed",
                "entry_budget_consumed_after_model_eval": bool(model_gate_reached) and subtype == "slot_consumed",
                "entry_budget_consumed_after_real_submit": bool(real_order_attempted) and subtype == "slot_consumed",
                "entry_budget_consumed_after_fill": bool(paper_fill_occurred) and subtype == "slot_consumed",
                "mode": self._runtime_mode(),
            }
            self._emit_quant_event("log_system_health", payload)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Zero-Size Risk Floor Probe v1 — observability only, fail-soft
    # ------------------------------------------------------------------

    def _zero_size_primary_constraint(self, diagnostics: dict, risk_plan) -> str:
        """Classify the dominant zero-size constraint from diagnostics. Pure read."""
        blocked = set(diagnostics.get("blocked_reasons") or [])
        reason  = str(diagnostics.get("reason_from_order_manager") or "").lower()
        balance = float(getattr(risk_plan, "account_balance", 0.0) or 0.0)
        if balance < FLOOR_BALANCE or "balance_below_floor" in reason or "floor" in reason:
            return "bankroll_too_small"
        if "time_remaining_le_90s" in blocked:
            return "time_remaining_too_short"
        if "confidence_too_low" in blocked:
            return "confidence_too_low"
        if "ev_not_positive" in blocked:
            return "ev_not_positive"
        if "spread_too_wide" in blocked:
            return "spread_too_wide"
        if "liquidity_too_low" in blocked:
            return "liquidity_too_low"
        if "daily_loss_limit_reached" in blocked or "hard_drawdown_reached" in blocked:
            return "drawdown_limit"
        if "lockdown" in reason or "risk_mode" in reason:
            return "risk_mode_blocked"
        if "below_min_position_size" in blocked:
            return "below_min_order"
        if "max_trades_per_hour_reached" in blocked:
            return "frequency_limit"
        return "unknown"

    def _emit_zero_size_probe_event(
        self,
        *,
        ticker: str,
        market_id: str,
        risk_plan,
        ptb_info,
        timing_detail: dict,
        confidence: float,
        ev: float,
        entry_price: float,
    ) -> None:
        """Emit one system_health event for every zero-size risk plan outcome.

        Additive-only. Fail-soft. No strategy/risk/execution side effects.
        Reads only existing state; never mutates anything.
        """
        try:
            diagnostics = getattr(risk_plan, "diagnostics", {}) if risk_plan is not None else {}
            diagnostics = diagnostics if isinstance(diagnostics, dict) else {}

            bankroll = float(getattr(risk_plan, "account_balance",
                                     self.bankroll_state.current_bankroll_for_sizing) or 0.0)
            base_risk_pct = float(diagnostics.get("base_risk_pct") or 0.0)
            available_risk = round(bankroll * base_risk_pct, 6)
            blocked = list(diagnostics.get("blocked_reasons") or [])
            tier_detail = self._bankroll_tier_detail()

            def _mf(key: str) -> float:
                try: return round(float(diagnostics.get(key) or 0.0), 6)
                except (TypeError, ValueError): return 0.0

            constraint = self._zero_size_primary_constraint(diagnostics, risk_plan)
            zero_reason = self._risk_plan_zero_reason(risk_plan)
            sr = float(getattr(ptb_info, "seconds_remaining", 0) or 0)
            lifecycle_phase = str(timing_detail.get("lifecycle_phase") or "")
            ev_f = float(ev or 0.0)

            # --- Semantic C shadow (observability only -- not used in sizing) ---
            _SC_GOOD_EV    = 0.08
            _SC_CONF_FLOOR = 0.54
            _SC_CONF_SPAN  = 0.21
            _sc_ev_q  = max(0.5, min(1.0, ev_f / max(_SC_GOOD_EV, 1e-9)))
            _sc_input = float(confidence or 0.0) * _sc_ev_q
            _sc_mult  = max(0.0, min(1.0, 0.25 + 0.75 * (_sc_input - _SC_CONF_FLOOR) / _SC_CONF_SPAN))
            _sc_size  = available_risk * _sc_mult

            payload: dict[str, object] = {
                "event": "zero_size_probe_v1",
                "ticker": str(ticker),
                "market_id": str(market_id),
                "epoch_start_ts": int(getattr(ptb_info, "epoch_start_ts", 0) or 0),
                "seconds_remaining": round(sr, 1),
                "lifecycle_phase": lifecycle_phase,
                # bankroll state
                "bankroll": round(bankroll, 4),
                "bankroll_floor_usd": float(FLOOR_BALANCE),
                "base_risk_pct": round(base_risk_pct, 6),
                "available_risk_budget_usd": available_risk,
                "tier_id": str(tier_detail.get("bankroll_tier_id") or diagnostics.get("tier") or ""),
                "tier_family": str(tier_detail.get("bankroll_family") or ""),
                "risk_mode": self._risk_mode_state.current_mode.value,
                "micro_survival_active": bool(self._micro_survival_active(bankroll)),
                "micro_position_size": round(float(self._micro_position_size(bankroll)), 6),
                # model output
                "confidence": round(float(confidence or 0.0), 6),
                "ev": round(ev_f, 6),
                "ev_positive": ev_f > 0.0,
                "confidence_passed": float(confidence or 0.0) >= 0.54,
                "entry_price": round(float(entry_price or 0.0), 6),
                # sizing pipeline
                "raw_size_usd": available_risk,
                "final_size_usd": _mf("final_notional_size"),
                "min_order_usd": _mf("min_position_size_usd"),
                "blocked_reasons": blocked,
                # multipliers
                "confidence_multiplier": _mf("confidence_multiplier"),
                "ev_multiplier": _mf("ev_multiplier"),
                "drawdown_multiplier": _mf("drawdown_multiplier"),
                "liquidity_multiplier": _mf("liquidity_multiplier"),
                "spread_multiplier": _mf("spread_multiplier"),
                "time_to_settlement_multiplier": _mf("time_to_settlement_multiplier"),
                "delta_multiplier": _mf("delta_multiplier"),
                "frequency_multiplier": _mf("frequency_multiplier"),
                # classification
                "zero_size_reason": zero_reason,
                "zero_size_primary_constraint": constraint,
                "mode": self._runtime_mode(),
                # Semantic C shadow -- observability only, never feeds active sizing
                "semantic_c_ev_quality_shadow":          round(_sc_ev_q, 6),
                "semantic_c_input_shadow":               round(_sc_input, 6),
                "semantic_c_multiplier_shadow":          round(_sc_mult, 6),
                "semantic_c_size_usd_shadow":            round(_sc_size, 6),
                "semantic_c_would_pass_confidence_gate": _sc_input >= _SC_CONF_FLOOR,
                "semantic_c_would_produce_nonzero_size": _sc_size > 0.0,
                "semantic_c_size_pct_bankroll":          round(_sc_size / max(bankroll, 1e-9) * 100, 4),
                "semantic_c_shadow_reason":              "confidence_score_x_ev_quality_not_in_active_sizing",
            }
            self._emit_quant_event("log_system_health", payload)
            self._cockpit_probe_counts["zero_size"] = self._cockpit_probe_counts.get("zero_size", 0) + 1
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Silent-Zone Selection Probe v1 — observability only, fail-soft
    # ------------------------------------------------------------------

    def _emit_cycle_selection_probe_event(
        self,
        *,
        early_return_reason: str | None,
        selected_markets: list | None = None,
    ) -> None:
        """Emit one system_health event per cycle for silent-zone selection analysis.

        Additive-only. Fail-soft. No strategy/risk/execution side effects.
        Reads only existing trader state; never writes or mutates state.
        """
        try:
            now_ts = int(time.time())
            epoch_ts = self._current_five_min_epoch(now_ts)
            seconds_since_epoch_open = float(now_ts - epoch_ts)

            def _mf(meta: dict, key: str, default: float = 0.0) -> float:
                try:
                    return float(meta.get(key) or default)
                except (TypeError, ValueError):
                    return default

            def _ms(meta: dict, key: str, default: str = "") -> str:
                return str(meta.get(key) or default)

            btc_meta = self._market_token_meta.get("BTC", {})
            eth_meta = self._market_token_meta.get("ETH", {})

            btc_epoch_start = _mf(btc_meta, "epoch_start_ts")
            eth_epoch_start = _mf(eth_meta, "epoch_start_ts")
            btc_epoch_end   = _mf(btc_meta, "epoch_end_ts")
            eth_epoch_end   = _mf(eth_meta, "epoch_end_ts")

            btc_token_ids = self._real_token_ids.get("BTC")
            eth_token_ids = self._real_token_ids.get("ETH")

            selected_tickers: list[str] = []
            if selected_markets:
                for m in selected_markets:
                    try:
                        selected_tickers.append(
                            self._ticker_from_market_id(m.market_id).upper()
                        )
                    except Exception:
                        pass

            selection_empty_reason: str | None = None
            if not early_return_reason and not selected_markets:
                selection_empty_reason = "no_markets_returned"

            payload: dict[str, object] = {
                "event": "cycle_selection_probe_v1",
                "cycle_count": int(getattr(self, "_cycle_count", 0)),
                "timestamp_utc": self._utc_timestamp(),
                "epoch_ts": epoch_ts,
                "seconds_since_epoch_open": round(seconds_since_epoch_open, 1),
                "early_return_reason": early_return_reason,
                "candidate_pool_size": 2,
                "selected_market_count": len(selected_markets) if selected_markets else 0,
                "selection_order": selected_tickers,
                "selection_empty_reason": selection_empty_reason,
                # BTC state
                "btc_token_ids_present": bool(btc_token_ids),
                "btc_epoch_age_seconds": (
                    round(float(now_ts - btc_epoch_start), 1)
                    if btc_epoch_start > 0 else None
                ),
                "btc_seconds_remaining": (
                    max(0, int(btc_epoch_end - now_ts))
                    if btc_epoch_end > 0 else None
                ),
                "btc_lifecycle_phase": _ms(btc_meta, "lifecycle_phase", "UNKNOWN"),
                "btc_executable_state": _ms(btc_meta, "executable_book_state", "UNKNOWN"),
                # ETH state
                "eth_token_ids_present": bool(eth_token_ids),
                "eth_epoch_age_seconds": (
                    round(float(now_ts - eth_epoch_start), 1)
                    if eth_epoch_start > 0 else None
                ),
                "eth_seconds_remaining": (
                    max(0, int(eth_epoch_end - now_ts))
                    if eth_epoch_end > 0 else None
                ),
                "eth_lifecycle_phase": _ms(eth_meta, "lifecycle_phase", "UNKNOWN"),
                "eth_executable_state": _ms(eth_meta, "executable_book_state", "UNKNOWN"),
                # Preload state (per-ticker via _preloaded_next_markets dict)
                "preload_btc_present": bool(self._preloaded_next_markets.get("BTC")),
                "preload_eth_present": bool(self._preloaded_next_markets.get("ETH")),
                "mode": self._runtime_mode(),
            }
            self._emit_quant_event("log_system_health", payload)
            self._cockpit_probe_counts["cycle_selection"] = self._cockpit_probe_counts.get("cycle_selection", 0) + 1
        except Exception:
            pass

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
            self._emit_cycle_selection_probe_event(early_return_reason="reconciliation_block")
            self._finish_cycle_timing(reason="cycle_end_reconciliation_block", force=True)
            return []
        self._cancel_stale_entry_orders_if_needed()
        self._check_stalled_positions()
        self._manage_open_positions_for_cycle()
        self._update_bankroll_state(fetch_live_cash=not self.settings.paper_trading)

        # Preload Next Market v1: Minimal observability-only preload
        for preload_asset in ["BTC", "ETH"]:
            try:
                self._preload_next_market(preload_asset)
            except Exception as e:
                LOGGER.debug("[PRELOAD] Unexpected error for %s in cycle: %s", preload_asset, e)

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
                        self._emit_cycle_selection_probe_event(early_return_reason="balance_guard")
                        self._finish_cycle_timing(reason="cycle_end_balance_guard", force=True)
                        return []
                except Exception:
                    LOGGER.warning("[CYCLE SKIP] BALANCE_GUARD: insufficient funds -- waiting for deposit/claim")
                    self._maybe_log_cycle_summary()
                    self._emit_cycle_selection_probe_event(early_return_reason="balance_guard")
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
                    LOGGER.warning("[CYCLE SKIP] BALANCE_GUARD: insufficient funds ($%.2f) -- waiting for deposit/claim", live_balance)
                    self._maybe_log_cycle_summary()
                    self._emit_cycle_selection_probe_event(early_return_reason="balance_guard")
                    self._finish_cycle_timing(reason="cycle_end_balance_guard", force=True)
                    return []
            except Exception:
                LOGGER.warning("[CYCLE SKIP] BALANCE_GUARD: insufficient funds -- waiting for deposit/claim")
                self._maybe_log_cycle_summary()
                self._emit_cycle_selection_probe_event(early_return_reason="balance_guard")
                self._finish_cycle_timing(reason="cycle_end_balance_guard", force=True)
                return []

        ok, pause_reason = self._risk_mgr.can_trade()
        if not ok:
            LOGGER.warning("[CYCLE SKIP] %s", pause_reason)
            self._emit_risk_event(
                "cycle_risk_pause",
                {
                    "reason": pause_reason,
                    "balance": float(self._risk_mgr.balance),
                },
            )
            from utils.telegram_reporter import (
                build_loss_cluster_alert, build_daily_drawdown_alert,
            )
            from utils.risk_manager import LOSS_CLUSTER_PAUSE_SECONDS, HARD_DAILY_DRAWDOWN

            balance = self._risk_mgr.balance
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
            self._emit_cycle_selection_probe_event(early_return_reason="risk_pause")
            self._finish_cycle_timing(reason="cycle_end_risk_pause", force=True)
            return []

        markets = self._select_markets(top_n=top_n)

        if not markets:
            self._maybe_log_cycle_summary()
            LOGGER.warning("No markets available -- cycle skipped.")
            self._maybe_emit_system_health(force=True, reason="no_markets")
            self._emit_cycle_selection_probe_event(early_return_reason="no_markets")
            self._finish_cycle_timing(reason="cycle_end_no_markets", force=True)
            return []

        self._current_cycle_market_count = len(markets)
        self._emit_cycle_selection_probe_event(early_return_reason=None, selected_markets=markets)
        outcomes: list[TradeOutcome] = []
        for sequence_index, market in enumerate(markets, start=1):
            try:
                self._mark_market_evaluation_started(
                    self._ticker_from_market_id(market.market_id),
                    sequence_index=sequence_index,
                    sequence_count=len(markets),
                )
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
            except Exception as exc:
                self._loop_exception_count += 1
                ticker = self._ticker_from_market_id(market.market_id)
                context = {}
                try:
                    context = dict(getattr(self, "last_quant_details", {}).get(ticker, {}) or {})
                except Exception:
                    context = {}
                LOGGER.exception("Unexpected error analyzing market_id=%s", market.market_id)
                self._emit_quant_event(
                    "log_execution",
                    {
                        "event": "market_analysis_exception",
                        "market_id": market.market_id,
                        "ticker": ticker,
                        "asset": ticker,
                        "mode": self._runtime_mode(),
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                        "lifecycle_phase": context.get("lifecycle_phase", ""),
                        "orderbook_state_classification": context.get("orderbook_state_classification", ""),
                        "market_readiness_state": context.get("market_readiness_state", ""),
                        "orderbook_unavailable_reason": context.get("orderbook_unavailable_reason", ""),
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
                **self._bankroll_tier_detail(),
                **self._bankroll_mode_detail(),
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


def evaluate_option_d_shadow(
    position,
    orderbook,
    now_ts: datetime,
    config
) -> dict:
    # Safely parse entry time
    entry_ts_raw = getattr(position, "entry_time", None)
    entry_dt = None
    if entry_ts_raw:
        try:
            ts_str = str(entry_ts_raw)
            if ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"
            entry_dt = datetime.fromisoformat(ts_str)
            if entry_dt.tzinfo is None:
                entry_dt = entry_dt.replace(tzinfo=UTC)
        except Exception:
            entry_dt = None
    if entry_dt is None:
        entry_dt = now_ts

    # Ensure now_ts has tzinfo
    if now_ts.tzinfo is None:
        now_ts = now_ts.replace(tzinfo=UTC)

    hold_seconds = max(0.0, (now_ts - entry_dt).total_seconds())

    # Settings
    delay_seconds = float(getattr(config, "sl_activation_delay_seconds", 30.0))
    stop_loss_pct = float(getattr(config, "execution_stop_loss_pct", 0.08))
    emergency_pct = float(getattr(config, "sl_emergency_stop_pct", 0.30))

    # Helper for orderbook values
    def get_val(obj, key, default=0.0):
        try:
            val = getattr(obj, key, None)
            if val is None and isinstance(obj, dict):
                val = obj.get(key)
            if val is None:
                return default
            return float(val)
        except Exception:
            return default

    raw_bid = get_val(orderbook, "best_bid", 0.0)
    raw_ask = get_val(orderbook, "best_ask", 0.0)
    bid_size = get_val(orderbook, "bid_size", 0.0)
    ask_size = get_val(orderbook, "ask_size", 0.0)

    entry_price = float(getattr(position, "entry_price", 0.0) or 0.0)

    # Mid-price and spread
    if raw_bid > 0.0 and raw_ask > 0.0:
        mid_price = (raw_bid + raw_ask) / 2.0
    elif raw_bid > 0.0:
        mid_price = raw_bid
    else:
        mid_price = entry_price

    spread = max(0.0, raw_ask - raw_bid)

    delay_active = hold_seconds < delay_seconds
    delay_remaining = max(0.0, delay_seconds - hold_seconds)
    depth_gate_pass = (bid_size >= 10.0 and ask_size >= 10.0)

    unrealized_mid_pct = 0.0
    if entry_price > 0.0:
        unrealized_mid_pct = (mid_price - entry_price) / entry_price

    mid_breached = unrealized_mid_pct <= -stop_loss_pct

    # Counter tracking in metadata
    metadata = getattr(position, "metadata", None)
    if not isinstance(metadata, dict):
        metadata = {}
        try:
            position.metadata = metadata
        except Exception:
            pass

    if delay_active:
        three_sample_count = 0
        three_sample_pass = False
        if isinstance(metadata, dict):
            metadata["option_d_consecutive_breaches"] = 0
    else:
        prev_count = metadata.get("option_d_consecutive_breaches", 0) if isinstance(metadata, dict) else 0
        if mid_breached and depth_gate_pass:
            three_sample_count = prev_count + 1
        else:
            three_sample_count = 0
        if isinstance(metadata, dict):
            metadata["option_d_consecutive_breaches"] = three_sample_count
        three_sample_pass = three_sample_count >= 3

    emergency_stop_trigger = unrealized_mid_pct <= -emergency_pct
    option_d_would_stop = emergency_stop_trigger or (three_sample_pass and not delay_active)
    option_d_would_hold = not option_d_would_stop

    # Side determination
    outcome = str(metadata.get("outcome", "")).upper()
    if outcome in {"YES", "NO"}:
        side = outcome
    else:
        side = "YES" if getattr(position, "side", "") == "BUY" else "NO"

    actual_stop_triggered = False
    actual_exit_reason = ""
    if isinstance(metadata, dict):
        actual_stop_triggered = bool(metadata.get("actual_stop_triggered", False))
        actual_exit_reason = str(metadata.get("actual_exit_reason", ""))

    return {
        "event_type": "stop_loss_shadow",
        "timestamp_utc": now_ts.isoformat().replace("+00:00", "Z"),
        "position_id": getattr(position, "position_id", ""),
        "symbol": getattr(position, "symbol", ""),
        "side": side,
        "entry_ts": str(getattr(position, "entry_time", "")),
        "hold_seconds": hold_seconds,
        "entry_price": entry_price,
        "raw_bid": raw_bid,
        "raw_ask": raw_ask,
        "mid_price": mid_price,
        "spread": spread,
        "bid_size": bid_size,
        "ask_size": ask_size,
        "delay_active": delay_active,
        "delay_remaining": delay_remaining,
        "depth_gate_pass": depth_gate_pass,
        "three_sample_count": three_sample_count,
        "three_sample_pass": three_sample_pass,
        "emergency_stop_trigger": emergency_stop_trigger,
        "option_d_would_stop": option_d_would_stop,
        "option_d_would_hold": option_d_would_hold,
        "actual_stop_triggered": actual_stop_triggered,
        "actual_exit_reason": actual_exit_reason,
    }
