from __future__ import annotations

from types import SimpleNamespace

from polymarket.trader import BankrollState, PolymarketTrader, TradeOutcome
from polymarket.observability.trader_decision_diagnostics import build_decision_diagnostics_payload


EPOCH = 1_700_000_000


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        paper_trading=True,
        dry_run=True,
        account_balance=100.0,
        max_risk_per_trade=0.01,
        default_stop_loss_pct=0.02,
        kelly_fraction_cap=0.25,
        bankroll_floor=5.0,
        max_open_positions=10,
        max_total_exposure=1.0,
        max_daily_drawdown=0.10,
        close_order_retry_attempts=1,
        close_order_retry_delay_seconds=0.0,
        polymarket_proxy_wallet="0xProxy",
        polymarket_funder="0xFunder",
        paper_balance_source="virtual",
        paper_starting_balance_source="config",
        paper_wallet_sync_on_start=True,
        paper_wallet_sync_mode="initialize_only",
        paper_min_balance_fallback=0.0,
        wallet_reference_refresh_seconds=300,
        show_wallet_reference_balance=True,
        micro_survival_bankroll_threshold=100.0,
        micro_survival_min_position_size=0.05,
        micro_survival_risk_fraction=0.0025,
        hybrid_phase_v1_enabled=False,
        adaptive_entry_max_spread=0.06,
        execution_entry_cutoff_seconds=90,
        execution_entry_hard_block_seconds=35,
        min_shares_per_order=5.0,
    )


def _trader() -> PolymarketTrader:
    trader = PolymarketTrader()
    trader.settings = _settings()
    trader.bankroll_state = BankrollState(
        starting_bankroll=100.0,
        current_cash_balance=100.0,
    )
    trader._connected = True
    trader._utc_timestamp = lambda: "2026-06-29T00:00:00Z"
    trader._cycle_elapsed_ms = lambda: 123
    trader._scheduler_cadence_observability_detail = lambda _ticker: {
        "scheduler_cadence_source": "fixed_test",
        "decision_cycle_interval_seconds": 7.5,
        "actual_market_revisit_frequency_seconds": 7.5,
    }
    trader._orderbook_refresh_observability_detail = lambda _ticker, **_kwargs: {
        "decision_cycle_started_at": "2026-06-29T00:00:00Z",
        "orderbook_current_fetch_status": "fresh_fetch_executable",
        "orderbook_stale_reuse_source": "CURRENT_DECISION_FETCH_EXECUTABLE",
        "decision_cycle_interval_seconds": 7.5,
        "actual_market_revisit_frequency_seconds": 7.5,
        "orderbook_reuse_detected": False,
    }
    return trader


def _outcome(display: dict[str, object], *, skip_reason: str = "orderbook_unavailable") -> TradeOutcome:
    return TradeOutcome(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        decision="skip",
        confidence=0.42,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason=skip_reason,
        display=display,
    )


def test_decision_diagnostics_builder_matches_wrapper_for_rich_payload() -> None:
    trader = _trader()
    outcome = _outcome(
        {
            "market_epoch_start": EPOCH,
            "epoch_start": EPOCH,
            "market_epoch_end": EPOCH + 300,
            "seconds_remaining": 180,
            "entry_cutoff_seconds": 90,
            "effective_cutoff_seconds": 90,
            "token_id": "yes-token",
            "yes_token_id": "yes-token",
            "no_token_id": "no-token",
            "condition_id": "condition-btc",
            "market_slug": "btc-updown-5m",
            "outcome": "YES",
            "side": "YES",
            "fair_value": 0.61,
            "true_probability": 0.61,
            "market_price": 0.58,
            "ev_after_spread": 0.03,
            "yes_bid": 0.57,
            "yes_ask": 0.58,
            "no_bid": 0.41,
            "no_ask": 0.42,
            "orderbook_current_fetch_status": "fresh_fetch_executable",
        }
    )

    assert trader._decision_diagnostics_payload(outcome, ticker="BTC") == build_decision_diagnostics_payload(
        trader,
        outcome,
        ticker="BTC",
    )


def test_decision_diagnostics_builder_matches_wrapper_for_missing_fields() -> None:
    trader = _trader()
    outcome = _outcome(
        {
            "seconds_remaining": None,
            "raw_skip_reason": "missing orderbook",
            "normalized_skip_reason": "orderbook_unavailable",
        }
    )

    assert trader._decision_diagnostics_payload(outcome, ticker="BTC") == build_decision_diagnostics_payload(
        trader,
        outcome,
        ticker="BTC",
    )
