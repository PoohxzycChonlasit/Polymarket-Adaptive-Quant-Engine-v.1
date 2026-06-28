from datetime import UTC, datetime

from polymarket.trader import PolymarketTrader


class _FakeQuantLogger:
    def __init__(self) -> None:
        self.mode = ""
        self.payloads: list[dict[str, object]] = []

    def log_market_snapshot(self, payload: dict[str, object]) -> bool:
        self.payloads.append(payload)
        return True


def _bare_trader() -> PolymarketTrader:
    trader = PolymarketTrader.__new__(PolymarketTrader)
    trader._entry_hard_block_seconds = lambda: 10
    trader._runtime_mode = lambda: "paper"
    return trader


def test_phase2_completion_enriches_market_snapshot_without_decision_changes() -> None:
    trader = _bare_trader()
    epoch_start = int(datetime(2026, 5, 11, 12, 0, tzinfo=UTC).timestamp())

    payload = trader._phase2_complete_lifecycle_observability(
        {
            "ticker": "BTC",
            "market_id": "pm-5m-btc",
            "outcome": "YES",
            "market_epoch_start": epoch_start,
            "seconds_remaining": 240,
            "first_seen_seconds_remaining": 260,
            "token_id": "yes-token",
            "yes_token_id": "yes-token",
            "no_token_id": "no-token",
            "yes_bid": 0.45,
            "yes_ask": 0.47,
            "no_bid": 0.53,
            "no_ask": 0.55,
            "liquidity_state": "HEALTHY",
            "spread_normalized": True,
            "fair_value_available": False,
            "fair_value_null_reason": "no_probability_model_output",
            "true_probability_available": False,
            "true_probability_null_reason": "pre_model_skip",
            "ev_after_spread_available": False,
            "ev_after_spread_null_reason": "candidate_blocked_before_ev",
            "probability_model_stage": "pre_model_skip",
            "ev_calculation_stage": "pre_model_skip",
        }
    )

    assert payload["lifecycle_phase"] == "ACTIVE_INVENTORY_TRADING"
    assert payload["lifecycle_phase_transition_reason"] == "epoch_window_direct"
    assert payload["lifecycle_phase_entered_at"] == "2026-05-11T12:00:35Z"
    assert payload["lifecycle_phase_exited_at"] == "2026-05-11T12:04:00Z"
    assert str(payload["candidate_id"]).startswith("candidate_")
    assert str(payload["signal_id"]).startswith("signal_")
    assert payload["orderbook_state_classification"] == "ready"
    assert payload["market_readiness_state"] == "ready"
    assert payload["candidate_block_stage"] == "pre_ev"
    assert payload["candidate_survival_ms"] == 20000
    assert payload["model_output_ready"] is False
    assert payload["ev_candidate_ready"] is False


def test_phase2_completion_marks_post_ev_blocks_directly() -> None:
    trader = _bare_trader()

    payload = trader._phase2_complete_lifecycle_observability(
        {
            "ticker": "ETH",
            "market_id": "pm-5m-eth",
            "decision": "skip",
            "skipped": True,
            "normalized_skip_reason": "risk_plan_zero",
            "seconds_remaining": 180,
            "fair_value_available": True,
            "true_probability_available": True,
            "ev_after_spread_available": True,
            "probability_model_stage": "probability_model_output",
            "ev_calculation_stage": "risk_blocked_after_ev",
        }
    )

    assert payload["candidate_block_reason"] == "risk_plan_zero"
    assert payload["candidate_block_stage"] == "post_ev"
    assert payload["candidate_expiry_reason"] == "risk_block"
    assert payload["model_output_ready"] is True
    assert payload["ev_candidate_ready"] is True


def test_emit_quant_event_enriches_market_snapshot_payload() -> None:
    trader = _bare_trader()
    fake_logger = _FakeQuantLogger()
    trader.quant_events = fake_logger

    assert trader._emit_quant_event(
        "log_market_snapshot",
        {
            "ticker": "BTC",
            "market_id": "pm-5m-btc",
            "seconds_remaining": 12,
            "token_id": "yes-token",
            "orderbook_readiness_reason": "warmup_pending",
        },
    )

    emitted = fake_logger.payloads[0]
    assert emitted["lifecycle_phase"] == "FINAL_DERISK"
    assert emitted["market_readiness_state"] == "warmup_pending"
    assert emitted["orderbook_state_classification"] == "warmup_pending"
    assert emitted["readiness_transition_reason"] == "warmup_pending"
