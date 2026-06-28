from __future__ import annotations

from types import SimpleNamespace

from polymarket.trader import BankrollState, PolymarketTrader, TradeOutcome


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
    return trader


def _seed_authoritative_book(trader: PolymarketTrader) -> None:
    trader._real_token_ids["BTC"] = ("yes-token", "no-token")
    trader._market_token_meta["BTC"] = {
        "condition_id": "condition-btc",
        "market_slug": "btc-updown-5m",
        "yes_token_id": "yes-token",
        "no_token_id": "no-token",
    }
    trader._phase2_mark_readiness(
        ticker="BTC",
        epoch_start=EPOCH,
        epoch_end=EPOCH + 300,
        token_ready=True,
        orderbook_ready=True,
        nonzero_bidask=True,
        spread_ready=True,
        liquidity_ready=True,
        first_tradable_ready=True,
        seconds_remaining=180,
    )
    trader._mark_orderbook_refresh(
        "BTC",
        source="market_snapshot",
        trigger="snapshot_sampling",
        executable_yes_no_book=True,
        condition_id="condition-btc",
        yes_token_id="yes-token",
        no_token_id="no-token",
        market_slug="btc-updown-5m",
    )


def _outcome(display: dict[str, object], *, skip_reason: str = "orderbook_unavailable") -> TradeOutcome:
    return TradeOutcome(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        decision="skip",
        confidence=0.0,
        risk_plan=None,
        receipt=None,
        skipped=True,
        skip_reason=skip_reason,
        display=display,
    )


def _base_display(**overrides: object) -> dict[str, object]:
    display: dict[str, object] = {
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
        "orderbook_current_fetch_status": "fresh_fetch_executable",
    }
    display.update(overrides)
    return display


def test_authoritative_book_without_serialized_bidask_is_not_true_unavailable() -> None:
    trader = _trader()
    _seed_authoritative_book(trader)

    payload = trader._decision_diagnostics_payload(
        _outcome(_base_display()),
        ticker="BTC",
    )

    assert "yes_bid" not in payload
    assert payload["orderbook_available_for_decision"] is True
    assert payload["orderbook_availability_source"] in {
        "current_fetch_status_fresh_fetch_executable",
        "readiness_bucket_current_tradable",
        "readiness_bucket_best_seen_tradable",
    }
    assert payload["decision_orderbook_completeness_source"] == "authoritative_readiness_without_serialized_book"
    assert payload["orderbook_current_fetch_status"] == "fresh_fetch_executable"
    assert payload["orderbook_state_classification"] == "ready"
    assert payload["orderbook_availability_classification"] != "true_orderbook_unavailable"
    assert payload["model_activation_orderbook_state"] == "ready"


def test_missing_readiness_and_book_data_stays_unavailable() -> None:
    trader = _trader()

    payload = trader._decision_diagnostics_payload(
        _outcome(
            {
                "market_epoch_start": EPOCH,
                "epoch_start": EPOCH,
                "seconds_remaining": 180,
                "entry_cutoff_seconds": 90,
                "effective_cutoff_seconds": 90,
                "normalized_skip_reason": "orderbook_unavailable",
            }
        ),
        ticker="BTC",
    )

    assert payload["orderbook_available_for_decision"] is False
    assert payload["orderbook_availability_source"] == "none"
    assert payload["decision_orderbook_completeness_source"] == "not_serialized_or_unavailable"
    assert payload["orderbook_state_classification"] == "unavailable"
    assert payload["orderbook_availability_classification"] == "true_orderbook_unavailable"


def test_cutoff_skip_with_authoritative_book_is_cutoff_book_available() -> None:
    trader = _trader()
    _seed_authoritative_book(trader)

    payload = trader._decision_diagnostics_payload(
        _outcome(
            _base_display(
                seconds_remaining=50,
                normalized_skip_reason="time_unsafe",
                raw_skip_reason="entry cutoff reached",
                adaptive_cutoff_reason="entry cutoff reached",
            ),
            skip_reason="entry cutoff reached",
        ),
        ticker="BTC",
    )

    assert payload["orderbook_available_for_decision"] is True
    assert payload["orderbook_state_classification"] == "ready"
    assert payload["orderbook_availability_classification"] == "orderbook_available_but_skipped_by_cutoff"
    assert payload["model_activation_block_group"] == "TIME_CUTOFF_GATE"
    assert payload["pre_model_gate_group"] == "TIME_CUTOFF_GATE"
    assert payload["admission_block_stage"] == "CUTOFF"
    assert payload["model_activation_block_reason"] != "orderbook_unavailable"
