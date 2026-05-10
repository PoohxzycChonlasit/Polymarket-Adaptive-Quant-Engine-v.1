from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from polymarket.client import OrderReceipt, OrderbookSnapshot
from polymarket.gamma_fetcher import GammaMarket
from polymarket.bankroll_tiers import BankrollTier
from polymarket.order_manager import OrderRequest, PolymarketOrderManager
from polymarket.order_intent import OrderIntentType
from polymarket.risk_modes import RiskMode
from polymarket.signal import SignalResult
from polymarket.trader import AdaptiveEntryCutoffDecision, BankrollState, PolymarketTrader
from utils.risk_manager import RiskPlan
from utils.position_tracker import PositionTracker


def _settings(**overrides):
    values = {
        "paper_trading": True,
        "account_balance": 100.0,
        "max_risk_per_trade": 0.01,
        "default_stop_loss_pct": 0.02,
        "default_take_profit_pct": 0.15,
        "kelly_fraction_cap": 0.25,
        "bankroll_floor": 5.0,
        "max_open_positions": 10,
        "max_total_exposure": 1.0,
        "max_daily_drawdown": 0.10,
        "execution_entry_cutoff_seconds": 90,
        "execution_force_exit_seconds": 60,
        "execution_take_profit_pct": 0.10,
        "execution_stop_loss_pct": 0.08,
        "max_active_positions_per_market": 1,
        "max_entries_per_market": 1,
        "max_risk_per_market": 0.20,
        "micro_survival_bankroll_threshold": 100.0,
        "micro_survival_min_position_size": 0.05,
        "micro_survival_risk_fraction": 0.0025,
        "close_order_retry_attempts": 3,
        "close_order_retry_delay_seconds": 0.0,
        "entry_min_seconds_remaining": 30,
        "min_shares_per_order": 1,
        "strategy_mom_upper": 1.0,
        "snipe_min_edge": 0.30,
        "sniper_max_entry_price": 0.45,
        "tp_partial_pct": 0.05,
        "tp_full_pct": 0.10,
        "dynamic_tp_enabled": False,
        "dynamic_tp_boost_factor": 0.5,
        "let_profit_run": False,
        "let_profit_run_min_seconds": 60,
        "panic_sell_max_slippage": 0.08,
        "panic_sell_delta_threshold": 5.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _trader(settings=None) -> PolymarketTrader:
    trader = PolymarketTrader()
    trader.settings = settings or _settings()
    trader.tracker = PositionTracker(settings=trader.settings)
    trader.order_manager = PolymarketOrderManager(
        account_balance=trader.settings.account_balance,
        max_risk_per_trade=trader.settings.max_risk_per_trade,
        stop_loss_pct=trader.settings.default_stop_loss_pct,
        kelly_fraction_cap=trader.settings.kelly_fraction_cap,
    )
    trader.client = MagicMock()
    trader.bankroll_state = BankrollState(
        starting_bankroll=float(trader.settings.account_balance),
        current_cash_balance=float(trader.settings.account_balance),
    )
    trader._update_bankroll_state()
    return trader


def _open_position(trader: PolymarketTrader, token_id: str = "yes-token"):
    return trader.tracker.open_position(
        symbol="pm-5m-btc",
        source="polymarket",
        side="BUY",
        entry_price=0.50,
        size=10.0,
        stop_loss=0.46,
        take_profit=0.55,
        order_id="entry-1",
        metadata={"token_id": token_id, "outcome": "YES"},
    )


def _market() -> GammaMarket:
    return GammaMarket(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        volume=1000.0,
        liquidity=1000.0,
        end_date_iso="",
    )


def _close_receipt(token_id: str = "yes-token", price: float = 0.60, size: float = 10.0) -> OrderReceipt:
    return OrderReceipt(
        order_id="close-1",
        status="paper",
        token_id=token_id,
        side="SELL",
        price=price,
        size=size,
        filled_size=size,
        remaining_size=0.0,
    )


def _risk_plan(size: float = 10.0, price: float = 0.50) -> RiskPlan:
    return RiskPlan(
        account_balance=100.0,
        entry_price=price,
        stop_loss_price=0.46,
        take_profit_price=0.55,
        partial_tp_price=0.53,
        risk_amount=size * price,
        kelly_fraction=0.0,
        capped_fraction=0.05,
        position_size=size,
        notional_size=size * price,
        stop_loss_pct=0.08,
    )


def _zero_min_size_plan(balance: float = 20.0, price: float = 0.50) -> RiskPlan:
    return RiskPlan(
        account_balance=balance,
        entry_price=price,
        stop_loss_price=price,
        take_profit_price=price,
        partial_tp_price=price,
        risk_amount=0.0,
        kelly_fraction=0.0,
        capped_fraction=0.0,
        position_size=0.0,
        notional_size=0.0,
        stop_loss_pct=0.08,
        diagnostics={
            "reason_from_order_manager": "below_min_position_size",
            "blocked_reasons": ["below_min_position_size"],
            "min_position_size_usd": 1.0,
        },
    )


class ExecutionRiskControlTests(unittest.TestCase):
    def test_forced_exit_closes_position_at_sixty_seconds(self) -> None:
        trader = _trader()
        _open_position(trader)
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.54, 0.56, 0.02, 10, 10)

        trader.enforce_pre_close_exits(countdown=60)

        self.assertEqual(trader.tracker.open_positions(), [])
        closed = trader.tracker.closed_positions()
        self.assertEqual(len(closed), 1)
        self.assertEqual(closed[0].exit_reason, "forced_exit")
        self.assertAlmostEqual(closed[0].exit_price, 0.54)

    def test_close_order_retries_three_times_before_success(self) -> None:
        trader = _trader()
        pos = _open_position(trader)
        receipt = OrderReceipt(
            order_id="close-1",
            status="paper",
            token_id="yes-token",
            side="SELL",
            price=0.54,
            size=10.0,
            filled_size=10.0,
            remaining_size=0.0,
        )
        trader._submit_order = MagicMock(side_effect=[None, None, receipt])

        ok = trader._close_position_with_retry(pos, reason="forced_exit", exit_price=0.54)

        self.assertTrue(ok)
        self.assertEqual(trader._submit_order.call_count, 3)
        self.assertEqual(trader.tracker.open_positions(), [])

    def test_take_profit_closes_at_ten_percent_unrealized_pnl(self) -> None:
        trader = _trader()
        _open_position(trader)
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.55, 0.57, 0.02, 10, 10)

        trader.check_take_profit(countdown=180)

        self.assertEqual(trader.tracker.open_positions(), [])
        self.assertEqual(trader.tracker.closed_positions()[0].exit_reason, "take_profit_full")

    def test_stop_loss_closes_at_minus_eight_percent_unrealized_pnl(self) -> None:
        trader = _trader()
        _open_position(trader)
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.459, 0.47, 0.011, 10, 10)

        trader.check_stop_loss(countdown=180)

        self.assertEqual(trader.tracker.open_positions(), [])
        self.assertEqual(trader.tracker.closed_positions()[0].exit_reason, "stop_loss")

    def test_entry_skips_when_time_to_close_inside_hard_close_zone(self) -> None:
        trader = _trader()
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_market_ptb.return_value = SimpleNamespace(
            is_above_ptb=True,
            price_to_beat=100.0,
            current_price=101.0,
            price_diff_pct=0.01,
            seconds_remaining=40,
            epoch_start_ts=123,
        )
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.49, 0.50, 0.01, 10, 10)
        signal = SignalResult(
            asset="BTC",
            side="YES",
            score=0.70,
            momentum_pct=0.4,
            rsi=50.0,
            vol_ratio=1.0,
            skip_reason="",
            strategy="reversion",
        )
        quant = SimpleNamespace(get_quant_data=lambda _ticker: {})

        with patch("polymarket.trader.compute_realtime_signal", return_value=signal), \
             patch("polymarket.trader.get_quant_feed", return_value=quant):
            outcome = trader._analyze_market(_market())

        self.assertTrue(outcome.skipped)
        self.assertIn("Entry cutoff", outcome.skip_reason)
        self.assertEqual(trader.tracker.open_positions(), [])

    def test_adaptive_cutoff_denied_when_data_stale(self) -> None:
        trader = _trader(_settings(adaptive_entry_max_oracle_age_ms=1000))

        decision = trader._evaluate_entry_cutoff(
            seconds_remaining=75,
            static_cutoff_seconds=90,
            orderbook_age_ms=10,
            oracle_age_ms=1500,
            decision_latency_ms=100,
            scan_cycle_duration_ms=100,
            spread=0.01,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.policy, "adaptive")
        self.assertEqual(decision.reason, "oracle_stale")

    def test_adaptive_cutoff_denied_when_latency_high(self) -> None:
        trader = _trader(_settings(adaptive_entry_max_decision_latency_ms=500))

        decision = trader._evaluate_entry_cutoff(
            seconds_remaining=75,
            static_cutoff_seconds=90,
            orderbook_age_ms=10,
            oracle_age_ms=100,
            decision_latency_ms=750,
            scan_cycle_duration_ms=100,
            spread=0.01,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "decision_latency_high")

    def test_adaptive_cutoff_denied_near_hard_close_zone(self) -> None:
        trader = _trader()

        decision = trader._evaluate_entry_cutoff(
            seconds_remaining=40,
            static_cutoff_seconds=90,
            orderbook_age_ms=10,
            oracle_age_ms=100,
            decision_latency_ms=100,
            scan_cycle_duration_ms=100,
            spread=0.01,
        )

        self.assertFalse(decision.allowed)
        self.assertTrue(decision.late_entry_hard_block)
        self.assertEqual(decision.reason, "hard_close_zone")

    def test_live_adaptive_cutoff_keeps_force_exit_hard_block(self) -> None:
        trader = _trader(_settings(paper_trading=False))

        decision = trader._evaluate_entry_cutoff(
            seconds_remaining=55,
            static_cutoff_seconds=90,
            orderbook_age_ms=10,
            oracle_age_ms=100,
            decision_latency_ms=100,
            scan_cycle_duration_ms=100,
            spread=0.01,
        )

        self.assertFalse(decision.allowed)
        self.assertTrue(decision.late_entry_hard_block)
        self.assertEqual(decision.effective_cutoff_seconds, 60)
        self.assertEqual(decision.reason, "hard_close_zone")

    def test_adaptive_cutoff_allowed_when_market_data_and_latency_are_healthy(self) -> None:
        trader = _trader()

        decision = trader._evaluate_entry_cutoff(
            seconds_remaining=75,
            static_cutoff_seconds=90,
            orderbook_age_ms=10,
            oracle_age_ms=100,
            decision_latency_ms=100,
            scan_cycle_duration_ms=100,
            spread=0.01,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.policy, "adaptive")
        self.assertEqual(decision.effective_cutoff_seconds, 45)
        self.assertEqual(decision.reason, "healthy_late_entry")

    def test_micro_adaptive_timing_allows_paper_micro_tier_above_micro_floor(self) -> None:
        trader = _trader(_settings(account_balance=20.0))

        decision = trader._evaluate_entry_cutoff(
            seconds_remaining=40,
            static_cutoff_seconds=90,
            orderbook_age_ms=10,
            oracle_age_ms=100,
            decision_latency_ms=10,
            scan_cycle_duration_ms=20,
            spread=0.01,
            liquidity_state="HEALTHY",
        )
        detail = trader._cutoff_decision_detail(decision)

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.policy, "micro_adaptive")
        self.assertEqual(decision.effective_cutoff_seconds, 35)
        self.assertEqual(decision.reason, "micro_healthy_late_entry")
        self.assertTrue(decision.micro_timing_branch_entered)
        self.assertTrue(decision.micro_timing_candidate)
        self.assertEqual(decision.micro_timing_branch_skipped_reason, "")
        self.assertTrue(detail["micro_timing_allowed"])
        self.assertTrue(detail["micro_timing_branch_entered"])
        self.assertTrue(detail["micro_timing_candidate"])
        self.assertEqual(detail["effective_micro_cutoff_seconds"], 35)
        self.assertEqual(detail["micro_cutoff_policy"], "micro_adaptive")

    def test_micro_adaptive_timing_branch_activates_for_micro_tiers(self) -> None:
        for balance, expected_tier in (
            (20.0, BankrollTier.T0_MICRO_SEED),
            (40.0, BankrollTier.T1_MICRO_BUILD),
            (75.0, BankrollTier.T2_MICRO_SURVIVAL),
        ):
            with self.subTest(balance=balance, expected_tier=expected_tier):
                trader = _trader(_settings(account_balance=balance))

                decision = trader._evaluate_entry_cutoff(
                    seconds_remaining=40,
                    static_cutoff_seconds=90,
                    orderbook_age_ms=10,
                    oracle_age_ms=100,
                    decision_latency_ms=10,
                    scan_cycle_duration_ms=20,
                    spread=0.01,
                    liquidity_state="HEALTHY",
                )

                self.assertEqual(trader.bankroll_state.current_bankroll_tier, expected_tier)
                self.assertEqual(trader.bankroll_state.bankroll_family, "MICRO")
                self.assertTrue(decision.micro_timing_branch_entered)
                self.assertTrue(decision.micro_timing_candidate)
                self.assertEqual(decision.micro_timing_branch_skipped_reason, "")
                self.assertTrue(decision.allowed)

    def test_micro_adaptive_timing_denies_below_micro_hard_floor(self) -> None:
        trader = _trader(_settings(account_balance=20.0))

        decision = trader._evaluate_entry_cutoff(
            seconds_remaining=34,
            static_cutoff_seconds=90,
            orderbook_age_ms=10,
            oracle_age_ms=100,
            decision_latency_ms=10,
            scan_cycle_duration_ms=20,
            spread=0.01,
            liquidity_state="HEALTHY",
        )

        self.assertFalse(decision.allowed)
        self.assertTrue(decision.late_entry_hard_block)
        self.assertEqual(decision.policy, "micro_adaptive")
        self.assertEqual(decision.reason, "hard_close_zone")
        self.assertEqual(decision.micro_timing_denied_reason, "hard_close_zone")
        self.assertTrue(decision.micro_timing_branch_entered)
        self.assertTrue(decision.micro_timing_candidate)

    def test_micro_adaptive_timing_does_not_apply_to_standard_tier(self) -> None:
        trader = _trader(_settings(account_balance=100.0))

        decision = trader._evaluate_entry_cutoff(
            seconds_remaining=40,
            static_cutoff_seconds=90,
            orderbook_age_ms=10,
            oracle_age_ms=100,
            decision_latency_ms=10,
            scan_cycle_duration_ms=20,
            spread=0.01,
            liquidity_state="HEALTHY",
        )

        self.assertFalse(decision.allowed)
        self.assertTrue(decision.late_entry_hard_block)
        self.assertEqual(decision.effective_cutoff_seconds, 45)
        self.assertEqual(decision.micro_cutoff_policy, "standard")
        self.assertFalse(decision.micro_timing_branch_entered)
        self.assertFalse(decision.micro_timing_candidate)
        self.assertEqual(decision.micro_timing_branch_skipped_reason, "non_micro_tier")

    def test_micro_adaptive_timing_does_not_apply_to_live_mode(self) -> None:
        trader = _trader(_settings(paper_trading=False, account_balance=20.0))

        decision = trader._evaluate_entry_cutoff(
            seconds_remaining=55,
            static_cutoff_seconds=90,
            orderbook_age_ms=10,
            oracle_age_ms=100,
            decision_latency_ms=10,
            scan_cycle_duration_ms=20,
            spread=0.01,
            liquidity_state="HEALTHY",
        )

        self.assertFalse(decision.allowed)
        self.assertTrue(decision.late_entry_hard_block)
        self.assertEqual(decision.effective_cutoff_seconds, 60)
        self.assertEqual(decision.micro_cutoff_policy, "standard")
        self.assertFalse(decision.micro_timing_branch_entered)
        self.assertFalse(decision.micro_timing_candidate)
        self.assertEqual(decision.micro_timing_branch_skipped_reason, "live_mode")

    def test_micro_adaptive_timing_denies_when_liquidity_not_healthy(self) -> None:
        trader = _trader(_settings(account_balance=20.0))

        decision = trader._evaluate_entry_cutoff(
            seconds_remaining=40,
            static_cutoff_seconds=90,
            orderbook_age_ms=10,
            oracle_age_ms=100,
            decision_latency_ms=10,
            scan_cycle_duration_ms=20,
            spread=0.01,
            liquidity_state="EMPTY",
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.policy, "micro_adaptive")
        self.assertEqual(decision.reason, "liquidity_not_healthy")
        self.assertEqual(decision.micro_timing_denied_reason, "liquidity_not_healthy")
        self.assertTrue(decision.micro_timing_branch_entered)
        self.assertTrue(decision.micro_timing_candidate)

    def test_micro_timing_candidate_reaches_evaluator_before_generic_hard_close_reject(self) -> None:
        trader = _trader(_settings(account_balance=20.0))
        trader._real_token_ids["BTC"] = ("yes-token", "no-token")
        trader._market_token_meta["BTC"] = {
            "slug": "btc-up-down-5m",
            "condition_id": "condition-1",
            "epoch_start_ts": 123,
            "epoch_end_ts": 423,
        }
        trader.client.get_orderbook.side_effect = [
            OrderbookSnapshot("yes-token", 0.49, 0.50, 0.01, 10, 10, "condition-1", age_seconds=0.01),
            OrderbookSnapshot("no-token", 0.49, 0.50, 0.01, 10, 10, "condition-1", age_seconds=0.01),
        ]
        trader._evaluate_entry_cutoff = MagicMock(
            return_value=AdaptiveEntryCutoffDecision(
                allowed=False,
                policy="micro_adaptive",
                effective_cutoff_seconds=35,
                reason="test_micro_gate",
                micro_timing_denied_reason="test_micro_gate",
                effective_micro_cutoff_seconds=35,
                micro_cutoff_policy="micro_adaptive",
                micro_timing_branch_entered=True,
                micro_timing_candidate=True,
            )
        )
        ptb_info = SimpleNamespace(
            is_above_ptb=True,
            price_to_beat=100.0,
            current_price=101.0,
            price_diff_pct=0.01,
            seconds_remaining=40,
            epoch_start_ts=123,
            epoch_end_ts=423,
            feed_age_seconds=0.1,
        )

        outcome = trader._analyze_market_quant(_market(), "BTC", ptb_info)

        self.assertTrue(outcome.skipped)
        self.assertIn("test_micro_gate", outcome.skip_reason)
        trader._evaluate_entry_cutoff.assert_called_once()
        self.assertEqual(trader.client.get_orderbook.call_count, 2)

    def test_adaptive_cutoff_denied_when_spread_too_wide(self) -> None:
        trader = _trader(_settings(adaptive_entry_max_spread=0.06))

        decision = trader._evaluate_entry_cutoff(
            seconds_remaining=75,
            static_cutoff_seconds=90,
            orderbook_age_ms=10,
            oracle_age_ms=100,
            decision_latency_ms=100,
            scan_cycle_duration_ms=100,
            spread=0.08,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.policy, "adaptive")
        self.assertEqual(decision.reason, "spread_too_wide")

    def test_adaptive_cutoff_detail_reports_denied_reason(self) -> None:
        trader = _trader(_settings(adaptive_entry_max_oracle_age_ms=1000))

        decision = trader._evaluate_entry_cutoff(
            seconds_remaining=75,
            static_cutoff_seconds=90,
            orderbook_age_ms=10,
            oracle_age_ms=1500,
            decision_latency_ms=100,
            scan_cycle_duration_ms=100,
            spread=0.01,
        )
        detail = trader._cutoff_decision_detail(decision)

        self.assertEqual(detail["adaptive_cutoff_reason"], "oracle_stale")
        self.assertEqual(detail["adaptive_cutoff_denied_reason"], "oracle_stale")

    def test_adaptive_cutoff_does_not_bypass_order_intent_guard(self) -> None:
        trader = _trader()
        trader.quant_events = None
        decision = trader._evaluate_entry_cutoff(
            seconds_remaining=75,
            static_cutoff_seconds=90,
            orderbook_age_ms=10,
            oracle_age_ms=100,
            decision_latency_ms=100,
            scan_cycle_duration_ms=100,
            spread=0.01,
        )

        receipt = trader._submit_order(
            market_id="yes-token",
            side="BUY",
            price=0.50,
            size=2.0,
            intent_type=OrderIntentType.ENTRY,
            risk_plan=None,
            source_market_id="pm-5m-btc",
            outcome="YES",
        )

        self.assertTrue(decision.allowed)
        self.assertIsNone(receipt)
        self.assertEqual(trader.paper_stats.paper_orders_created, 0)

    def test_entry_skips_when_market_already_has_active_position(self) -> None:
        trader = _trader()
        _open_position(trader)
        trader.ptb_tracker = MagicMock()
        trader.ptb_tracker.get_market_ptb.return_value = SimpleNamespace(
            is_above_ptb=True,
            price_to_beat=100.0,
            current_price=101.0,
            price_diff_pct=0.01,
            seconds_remaining=200,
            epoch_start_ts=123,
        )
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.49, 0.50, 0.01, 10, 10)
        signal = SignalResult(
            asset="BTC",
            side="YES",
            score=0.70,
            momentum_pct=0.4,
            rsi=50.0,
            vol_ratio=1.0,
            skip_reason="",
            strategy="reversion",
        )
        quant = SimpleNamespace(get_quant_data=lambda _ticker: {})

        with patch("polymarket.trader.compute_realtime_signal", return_value=signal), \
             patch("polymarket.trader.get_quant_feed", return_value=quant):
            outcome = trader._analyze_market(_market())

        self.assertTrue(outcome.skipped)
        self.assertIn("Max active positions per market", outcome.skip_reason)
        self.assertEqual(len(trader.tracker.open_positions()), 1)

    def test_bankroll_increases_after_profitable_paper_exit(self) -> None:
        trader = _trader(_settings(account_balance=20.0))
        pos = _open_position(trader)
        trader._paper_record_trade(pos.entry_price * pos.size)
        trader._submit_order = MagicMock(return_value=_close_receipt(price=0.60, size=pos.size))

        self.assertTrue(trader._close_position_with_retry(pos, reason="test", exit_price=0.60))

        self.assertAlmostEqual(trader.bankroll_state.current_cash_balance, 21.0)
        self.assertAlmostEqual(trader.bankroll_state.realized_pnl, 1.0)
        self.assertAlmostEqual(trader.bankroll_state.current_bankroll_for_sizing, 21.0)
        self.assertAlmostEqual(trader.order_manager.account_balance, 21.0)

    def test_bankroll_decreases_after_losing_paper_exit(self) -> None:
        trader = _trader(_settings(account_balance=20.0))
        pos = _open_position(trader)
        trader._paper_record_trade(pos.entry_price * pos.size)
        trader._submit_order = MagicMock(return_value=_close_receipt(price=0.40, size=pos.size))

        self.assertTrue(trader._close_position_with_retry(pos, reason="test", exit_price=0.40))

        self.assertAlmostEqual(trader.bankroll_state.current_cash_balance, 19.0)
        self.assertAlmostEqual(trader.bankroll_state.realized_pnl, -1.0)
        self.assertAlmostEqual(trader.bankroll_state.current_bankroll_for_sizing, 19.0)

    def test_unrealized_pnl_updates_equity_while_position_is_open(self) -> None:
        trader = _trader(_settings(account_balance=20.0))
        pos = _open_position(trader)
        trader._paper_record_trade(pos.entry_price * pos.size)
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.60, 0.62, 0.02, 10, 10)

        trader._update_bankroll_state()

        self.assertAlmostEqual(trader.bankroll_state.current_cash_balance, 15.0)
        self.assertAlmostEqual(trader.bankroll_state.open_position_market_value, 6.0)
        self.assertAlmostEqual(trader.bankroll_state.unrealized_pnl, 1.0)
        self.assertAlmostEqual(trader.bankroll_state.equity, 21.0)

    def test_position_sizing_uses_updated_equity(self) -> None:
        trader = _trader(_settings(account_balance=20.0))
        pos = _open_position(trader)
        trader._paper_record_trade(pos.entry_price * pos.size)
        trader._submit_order = MagicMock(return_value=_close_receipt(price=0.60, size=pos.size))

        trader._close_position_with_retry(pos, reason="test", exit_price=0.60)

        plan = trader.order_manager.build_order_plan(
            OrderRequest(
                market_id="pm-5m-eth",
                side="YES",
                entry_price=0.50,
                win_rate=0.75,
                reward_risk_ratio=2.0,
                edge=0.08,
                spread=0.0,
                liquidity_usd=1_000.0,
                delta_multiplier=1.0,
                time_remaining_seconds=300,
                min_position_size_usd=0.001,
            )
        )
        self.assertAlmostEqual(plan.account_balance, 21.0)

    def test_micro_survival_mode_activates_for_sub_100_paper_bankroll(self) -> None:
        trader = _trader(_settings(account_balance=20.0))

        portfolio = trader.dashboard_portfolio_state()

        self.assertEqual(portfolio["bankroll_mode"], "MICRO_SURVIVAL")
        self.assertTrue(portfolio["micro_survival_active"])
        self.assertAlmostEqual(portfolio["micro_position_size"], 0.05)
        self.assertEqual(portfolio["bankroll_tier_id"], BankrollTier.T0_MICRO_SEED.value)
        self.assertEqual(portfolio["bankroll_tier_name"], "Micro Seed")
        self.assertEqual(portfolio["bankroll_family"], "MICRO")
        self.assertEqual(portfolio["bankroll_risk_profile"], "seed_protection")

    def test_standard_mode_remains_for_100_or_more_bankroll(self) -> None:
        trader = _trader(_settings(account_balance=100.0))

        portfolio = trader.dashboard_portfolio_state()

        self.assertEqual(portfolio["bankroll_mode"], "STANDARD")
        self.assertFalse(portfolio["micro_survival_active"])
        self.assertEqual(portfolio["bankroll_tier_id"], BankrollTier.T3_BASE_BUILD.value)
        self.assertEqual(portfolio["bankroll_family"], "BASE")
        self.assertAlmostEqual(
            trader._entry_min_position_size_usd(bankroll=100.0, entry_price=0.50),
            1.0,
        )

    def test_micro_survival_rescues_min_size_zero_plan(self) -> None:
        trader = _trader(_settings(account_balance=20.0))

        plan = trader._maybe_apply_micro_survival_plan(
            _zero_min_size_plan(),
            current_balance=20.0,
            entry_price=0.50,
        )

        self.assertGreater(plan.position_size, 0.0)
        self.assertAlmostEqual(plan.notional_size, 0.05)
        self.assertAlmostEqual(plan.stop_loss_price, 0.46)
        self.assertEqual(plan.diagnostics["bankroll_mode"], "MICRO_SURVIVAL")
        self.assertTrue(plan.diagnostics["micro_survival_active"])
        self.assertTrue(plan.diagnostics["rescued_from_risk_plan_zero"])

    def test_micro_survival_does_not_rescue_live_mode(self) -> None:
        trader = _trader(_settings(paper_trading=False, account_balance=20.0))
        original_plan = _zero_min_size_plan()

        plan = trader._maybe_apply_micro_survival_plan(
            original_plan,
            current_balance=20.0,
            entry_price=0.50,
        )

        self.assertIs(plan, original_plan)
        self.assertEqual(trader.dashboard_portfolio_state()["bankroll_mode"], "STANDARD")

    def test_micro_survival_does_not_bypass_order_intent_guard(self) -> None:
        trader = _trader(_settings(account_balance=20.0))
        plan = trader._maybe_apply_micro_survival_plan(
            _zero_min_size_plan(),
            current_balance=20.0,
            entry_price=0.50,
        )

        receipt = trader._submit_order(
            "no-token",
            side="SELL",
            price=0.50,
            size=plan.position_size,
            intent_type=OrderIntentType.ENTRY,
            risk_plan=plan,
            source_market_id="pm-5m-btc",
            outcome="NO",
        )

        self.assertIsNone(receipt)
        trader.client.place_limit_order.assert_not_called()

    def test_bankroll_tier_lock_upgrades_at_boundary_and_keeps_metadata_visible(self) -> None:
        trader = _trader(_settings(account_balance=24.0))
        pos = _open_position(trader)
        trader._paper_record_trade(pos.entry_price * pos.size)
        trader._submit_order = MagicMock(return_value=_close_receipt(price=0.70, size=pos.size))

        trader._close_position_with_retry(pos, reason="test", exit_price=0.70)

        self.assertEqual(trader.bankroll_state.raw_bankroll_tier, BankrollTier.T1_MICRO_BUILD.value)
        self.assertEqual(trader.bankroll_state.current_bankroll_tier, BankrollTier.T1_MICRO_BUILD.value)
        self.assertEqual(trader.bankroll_state.bankroll_tier_id, BankrollTier.T1_MICRO_BUILD.value)
        self.assertEqual(trader.bankroll_state.bankroll_family, "MICRO")
        self.assertFalse(trader.bankroll_state.bankroll_hysteresis_active)

        trader.bankroll_state.current_cash_balance = 26.26
        trader._update_bankroll_state()

        self.assertEqual(trader.bankroll_state.current_bankroll_tier, BankrollTier.T1_MICRO_BUILD.value)

    def test_bankroll_tier_lock_holds_standard_tier_inside_downgrade_buffer(self) -> None:
        trader = _trader(_settings(account_balance=100.0))

        trader.bankroll_state.current_cash_balance = 99.0
        trader._update_bankroll_state()

        self.assertEqual(trader.bankroll_state.raw_bankroll_tier, BankrollTier.T2_MICRO_SURVIVAL.value)
        self.assertEqual(trader.bankroll_state.current_bankroll_tier, BankrollTier.T3_BASE_BUILD.value)
        self.assertTrue(trader.bankroll_state.bankroll_tier_locked)
        self.assertTrue(trader.bankroll_state.bankroll_hysteresis_active)

    def test_daily_drawdown_updates_from_realtime_equity(self) -> None:
        trader = _trader(_settings(account_balance=20.0))
        pos = _open_position(trader)
        trader._paper_record_trade(pos.entry_price * pos.size)
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.40, 0.42, 0.02, 10, 10)

        trader._update_bankroll_state()

        self.assertAlmostEqual(trader.bankroll_state.equity, 19.0)
        self.assertAlmostEqual(trader.bankroll_state.daily_drawdown_pct, 0.05)

    def test_open_position_value_is_not_double_counted(self) -> None:
        trader = _trader(_settings(account_balance=20.0))
        pos = _open_position(trader)
        trader._paper_record_trade(pos.entry_price * pos.size)
        trader.client.get_orderbook.return_value = OrderbookSnapshot("yes-token", 0.50, 0.52, 0.02, 10, 10)

        trader._update_bankroll_state()

        self.assertAlmostEqual(trader.bankroll_state.current_cash_balance, 15.0)
        self.assertAlmostEqual(trader.bankroll_state.open_position_market_value, 5.0)
        self.assertAlmostEqual(trader.bankroll_state.equity, 20.0)

    def test_live_balance_fetch_failure_uses_last_known_bankroll(self) -> None:
        trader = _trader(_settings(paper_trading=False, account_balance=20.0))
        trader.client.get_usdc_balance.side_effect = RuntimeError("balance unavailable")

        state = trader._update_bankroll_state(fetch_live_cash=True)

        self.assertAlmostEqual(state.current_cash_balance, 20.0)
        self.assertAlmostEqual(state.current_bankroll_for_sizing, 20.0)
        self.assertAlmostEqual(trader.order_manager.account_balance, 20.0)

    def test_defensive_mode_scales_existing_risk_plan_down(self) -> None:
        trader = _trader()
        trader._risk_mgr.record_result(won=False, pnl=1.0)
        trader._risk_mgr.record_result(won=False, pnl=1.0)
        decision = trader._update_risk_mode()
        plan = RiskPlan(
            account_balance=100.0,
            entry_price=0.50,
            stop_loss_price=0.46,
            take_profit_price=0.55,
            partial_tp_price=0.53,
            risk_amount=10.0,
            kelly_fraction=0.0,
            capped_fraction=0.10,
            position_size=20.0,
            notional_size=10.0,
            stop_loss_pct=0.08,
        )

        trader._apply_risk_mode_to_plan(plan, decision)

        self.assertEqual(decision.mode, RiskMode.DEFENSIVE)
        self.assertAlmostEqual(plan.risk_amount, 5.0)
        self.assertAlmostEqual(plan.position_size, 10.0)
        self.assertAlmostEqual(plan.notional_size, 5.0)
        self.assertLessEqual(plan.capped_fraction, 0.10)

    def test_micro_recovery_mode_scales_existing_risk_plan_down(self) -> None:
        trader = _trader()
        trader.bankroll_state.peak_bankroll = 100.0
        trader.bankroll_state.current_cash_balance = 96.0
        trader._update_bankroll_state()
        decision = trader._update_risk_mode()
        plan = RiskPlan(
            account_balance=100.0,
            entry_price=0.50,
            stop_loss_price=0.46,
            take_profit_price=0.55,
            partial_tp_price=0.53,
            risk_amount=10.0,
            kelly_fraction=0.0,
            capped_fraction=0.10,
            position_size=20.0,
            notional_size=10.0,
            stop_loss_pct=0.08,
        )

        trader._apply_risk_mode_to_plan(plan, decision)

        self.assertEqual(decision.mode, RiskMode.MICRO_RECOVERY)
        self.assertAlmostEqual(plan.risk_amount, 2.5)
        self.assertAlmostEqual(plan.position_size, 5.0)
        self.assertAlmostEqual(plan.notional_size, 2.5)

    def test_lockdown_mode_blocks_new_entry_approval(self) -> None:
        trader = _trader()
        trader._trigger_lockdown("reconciliation_mismatch")
        ptb_info = SimpleNamespace(
            is_above_ptb=True,
            price_to_beat=100.0,
            current_price=101.0,
            price_diff_pct=0.01,
            seconds_remaining=200,
            epoch_start_ts=123,
            last_updated=0.0,
        )
        trader._submit_order = MagicMock()

        outcome = trader._analyze_market_quant(_market(), "BTC", ptb_info)

        self.assertTrue(outcome.skipped)
        self.assertIn("risk_mode_lockdown", outcome.skip_reason)
        trader._submit_order.assert_not_called()
        self.assertEqual(trader.paper_session_summary()["risk_mode"], RiskMode.LOCKDOWN.value)

    def test_duplicate_entry_same_market_epoch_enters_lockdown_before_order(self) -> None:
        trader = _trader()
        trader._placed_epochs["BTC"] = 123
        trader._submit_order = MagicMock()
        ptb_info = SimpleNamespace(
            is_above_ptb=True,
            price_to_beat=100.0,
            current_price=101.0,
            price_diff_pct=0.01,
            seconds_remaining=200,
            epoch_start_ts=123,
            last_updated=0.0,
        )

        outcome = trader._analyze_market_quant(_market(), "BTC", ptb_info)

        self.assertTrue(outcome.skipped)
        self.assertIn("Max 1 trade per window", outcome.skip_reason)
        self.assertEqual(trader._risk_mode_state.current_mode, RiskMode.LOCKDOWN)
        trader._submit_order.assert_not_called()

    def test_order_intent_blocks_sell_without_tracked_inventory_in_paper(self) -> None:
        trader = _trader()

        receipt = trader._submit_order(
            "yes-token",
            side="SELL",
            price=0.50,
            size=1.0,
            intent_type=OrderIntentType.EXIT,
            position_id="missing",
        )

        self.assertIsNone(receipt)
        trader.client.place_limit_order.assert_not_called()

    def test_no_entry_routes_as_buy_on_no_token_in_paper(self) -> None:
        trader = _trader()

        receipt = trader._submit_order(
            "no-token",
            side="BUY",
            price=0.50,
            size=2.0,
            intent_type=OrderIntentType.ENTRY,
            risk_plan=_risk_plan(size=2.0),
            source_market_id="pm-5m-btc",
            outcome="NO",
        )

        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.side, "BUY")
        self.assertEqual(receipt.token_id, "no-token")
        trader.client.place_limit_order.assert_not_called()

    def test_entry_sell_for_no_outcome_is_blocked_in_paper(self) -> None:
        trader = _trader()

        receipt = trader._submit_order(
            "no-token",
            side="SELL",
            price=0.50,
            size=2.0,
            intent_type=OrderIntentType.ENTRY,
            risk_plan=_risk_plan(size=2.0),
            source_market_id="pm-5m-btc",
            outcome="NO",
        )

        self.assertIsNone(receipt)
        trader.client.place_limit_order.assert_not_called()

    def test_exit_sell_allowed_only_for_tracked_inventory_in_paper(self) -> None:
        trader = _trader()
        pos = _open_position(trader, token_id="yes-token")

        receipt = trader._submit_order(
            "yes-token",
            side="SELL",
            price=0.55,
            size=pos.size,
            intent_type=OrderIntentType.EXIT,
            source_market_id=pos.symbol,
            outcome="YES",
            position_id=pos.position_id,
        )

        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.side, "SELL")
        self.assertEqual(receipt.token_id, "yes-token")

    def test_lockdown_blocks_entry_but_allows_tracked_exit_in_paper(self) -> None:
        trader = _trader()
        pos = _open_position(trader, token_id="yes-token")
        trader._trigger_lockdown("api_order_failure")

        entry_receipt = trader._submit_order(
            "yes-token",
            side="BUY",
            price=0.50,
            size=2.0,
            intent_type=OrderIntentType.ENTRY,
            risk_plan=_risk_plan(size=2.0),
            source_market_id="pm-5m-btc",
            outcome="YES",
        )
        exit_receipt = trader._submit_order(
            "yes-token",
            side="SELL",
            price=0.55,
            size=pos.size,
            intent_type=OrderIntentType.EXIT,
            source_market_id=pos.symbol,
            outcome="YES",
            position_id=pos.position_id,
        )

        self.assertIsNone(entry_receipt)
        self.assertIsNotNone(exit_receipt)


if __name__ == "__main__":
    unittest.main()
