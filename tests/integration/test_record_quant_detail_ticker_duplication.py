from __future__ import annotations

import json
from types import SimpleNamespace

from polymarket.gamma_fetcher import GammaMarket
from polymarket.trader import PolymarketTrader


class _CollectingQuantLogger:
    def __init__(self) -> None:
        self.mode = "paper"
        self.schema_version = "test"
        self.disabled_categories: set[str] = set()
        self.events: list[tuple[str, dict]] = []

    def log_decision(self, payload: dict) -> bool:
        self.events.append(("decision", payload))
        return True

    def log_risk_event(self, payload: dict) -> bool:
        self.events.append(("risk", payload))
        return True


class _FailingQuantLogger:
    mode = "paper"
    schema_version = "test"
    disabled_categories: set[str] = set()

    def log_decision(self, _payload: dict) -> bool:
        raise PermissionError("jsonl writer locked")

    def log_risk_event(self, _payload: dict) -> bool:
        raise PermissionError("jsonl writer locked")


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        paper_trading=True,
        dry_run=True,
        account_balance=100.0,
        execution_entry_cutoff_seconds=90,
        hybrid_phase_v1_enabled=False,
    )


def _trader() -> PolymarketTrader:
    trader = PolymarketTrader()
    trader.settings = _settings()
    return trader


def _market() -> GammaMarket:
    return GammaMarket(
        market_id="pm-5m-btc",
        question="Will BTC close above PTB?",
        volume=0.0,
        liquidity=0.0,
        end_date_iso="",
    )


def test_skip_outcome_accepts_existing_quant_detail_with_ticker_once() -> None:
    trader = _trader()
    collector = _CollectingQuantLogger()
    trader.quant_events = collector
    existing_detail = trader._record_quant_detail(
        "BTC",
        market_id="pm-5m-btc",
        p_yes=0.61,
        p_no=0.39,
        ev=0.04,
        custom_probe="preserve-me",
    )

    outcome = trader._skip_outcome(
        _market(),
        "skip",
        0.61,
        "scanner_no_best_trade",
        extra_detail=existing_detail,
    )

    assert outcome.display["ticker"] == "BTC"
    assert json.dumps(outcome.display).count('"ticker"') == 1
    assert outcome.display["p_yes"] == 0.61
    assert outcome.display["p_no"] == 0.39
    assert outcome.display["ev"] == 0.04
    assert outcome.display["custom_probe"] == "preserve-me"
    assert trader.last_quant_details["BTC"]["ticker"] == "BTC"
    assert json.dumps(trader.last_quant_details["BTC"]).count('"ticker"') == 1


def test_skip_outcome_preserves_fail_soft_quant_logging_with_ticker_detail() -> None:
    trader = _trader()
    trader.quant_events = _FailingQuantLogger()
    existing_detail = trader._record_quant_detail(
        "BTC",
        market_id="pm-5m-btc",
        p_yes=0.61,
        p_no=0.39,
        ev=0.04,
    )

    outcome = trader._skip_outcome(
        _market(),
        "skip",
        0.61,
        "scanner_no_best_trade",
        extra_detail=existing_detail,
    )

    assert outcome.display["ticker"] == "BTC"
    assert outcome.display["p_yes"] == 0.61
    assert trader._observability_health_display_state["jsonl_status"] == "WARN"

