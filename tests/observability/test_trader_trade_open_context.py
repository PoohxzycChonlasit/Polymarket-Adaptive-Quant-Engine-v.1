"""Trade-open context collector tests."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from types import SimpleNamespace

from polymarket.observability.trader_trade_event_payload import collect_trade_open_context
from polymarket.observability.trader_trade_event_payload import build_trade_opened_payload
from polymarket.trader import BUY, PolymarketTrader


@dataclass
class DummyReceipt:
    order_id: str
    filled_size: float
    average_price: float


def _available(value: object) -> bool:
    return value is not None and value != ""


def _first_available(*values: object) -> object:
    for value in values:
        if _available(value):
            return value
    return None


class DummyOpenContextTrader:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(paper_trading=True)
        self.last_quant_details = {
            "BTC": {
                "model_probability_yes": 0.63,
                "model_probability_no": 0.37,
                "fair_value_yes": 0.64,
                "fair_value_no": 0.36,
                "expected_value": 0.041,
                "confidence": 0.82,
                "signal_name": "breakout_entry",
                "signal_reason": "ev_after_spread_positive",
                "strategy_signal_name": "phase3_strategy",
                "strategy_signal_reason": "spread_ok",
                "entry_attribution": {
                    "candidate_id": "cand-123",
                    "candidate_instance_id": "inst-456",
                    "paper_trade_replay_key": "attribution-replay-key",
                    "signal_name": "attr_signal",
                    "signal_reason": "attr_reason",
                },
                "shadow_policy_decision": "WOULD_ENTER",
                "shadow_policy_reasons": ["ev_positive"],
                "shadow_policy_observed_ev": 0.041,
                "shadow_policy_observed_probability": 0.63,
                "shadow_policy_observed_risk_mode": "NORMAL",
                "shadow_policy_id": "shadow-v1",
                "shadow_policy_confidence": 0.79,
                "size_sharp_result": {
                    "size_sharp": 0.91,
                    "size_sharp_bucket": "sharp",
                    "deployment_state": "observe",
                    "limiting_factor": "none",
                    "confidence_grade": "A",
                    "component_scores": {"edge": 0.9},
                    "penalties": {},
                    "boosts": {"liquidity": 0.1},
                    "hard_caps": [],
                    "missing_inputs": [],
                    "schema_version": "size_sharp_v1",
                },
            }
        }
        self._last_bankroll_rank = "tier_1"
        self._last_bankroll_family = "core"
        self._last_capital_score = 0.77

    def _phase2_observability_payload(self, **kwargs: object) -> dict[str, object]:
        return {
            "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
            "seconds_remaining": kwargs.get("seconds_remaining"),
            "fair_value": kwargs.get("fair_value"),
            "true_probability": kwargs.get("true_probability"),
            "ev_after_spread": kwargs.get("ev_after_spread"),
            "exposure_after": 18.0,
            "probability_model_called": False,
            "model_attempted": False,
            "model_handoff_stage": "MODEL_NOT_SERIALIZED",
            "probability_model_stage": "not_called",
            "ev_after_spread_null_reason": "",
        }

    def _build_paper_trade_replay_key(self, **kwargs: object) -> str:
        return PolymarketTrader._build_paper_trade_replay_key(**kwargs)

    def _runtime_mode(self) -> str:
        return "paper"

    def _size_sharp_metadata(self, result: object) -> dict[str, object]:
        return PolymarketTrader._size_sharp_metadata(result)

    def _utc_timestamp(self) -> str:
        return "2026-06-29T09:00:00Z"

    def _build_entry_model_truth_envelope(self, **kwargs: object) -> dict[str, object]:
        return PolymarketTrader._build_entry_model_truth_envelope(self, **kwargs)

    def _emit_quant_event(self, event_name: str, payload: dict[str, object]) -> None:
        raise AssertionError(f"collector must not emit {event_name}: {payload!r}")


def _legacy_trade_open_context(
    trader: DummyOpenContextTrader,
    *,
    market_id: str,
    ticker: str,
    token_id: str,
    outcome: str,
    risk_plan: SimpleNamespace,
    entry_price: float,
    seconds_remaining: int | None,
    epoch_start: int | None,
    condition_id: str,
    true_probability: float | None,
    fair_value: float | None,
    ev_after_spread: float | None,
    confidence: float | None,
    entry_attribution: dict[str, object] | None,
) -> dict[str, object]:
    model_context = {}
    last_quant_details = getattr(trader, "last_quant_details", {})
    if isinstance(last_quant_details, dict):
        candidate_context = last_quant_details.get(str(ticker or "").upper(), {})
        if isinstance(candidate_context, dict):
            model_context = candidate_context
    if entry_attribution is None and isinstance(model_context, dict):
        entry_attribution = model_context.get("entry_attribution")

    outcome_upper = str(outcome or "").upper()
    model_p_yes = _first_available(
        model_context.get("model_probability_yes"),
        model_context.get("p_yes"),
        model_context.get("model_p_yes"),
        model_context.get("fair_value_yes"),
    )
    model_p_no = _first_available(
        model_context.get("model_probability_no"),
        model_context.get("p_no"),
        model_context.get("model_p_no"),
        model_context.get("fair_value_no"),
    )
    selected_probability = _first_available(true_probability, model_context.get("true_probability"))
    if selected_probability is None:
        if outcome_upper == "YES":
            selected_probability = model_p_yes
        elif outcome_upper == "NO":
            selected_probability = model_p_no
    selected_fair_value = _first_available(fair_value, model_context.get("fair_value"))
    if selected_fair_value is None:
        if outcome_upper == "YES":
            selected_fair_value = _first_available(model_context.get("fair_value_yes"), model_p_yes)
        elif outcome_upper == "NO":
            selected_fair_value = _first_available(model_context.get("fair_value_no"), model_p_no)
    if selected_fair_value is None:
        selected_fair_value = selected_probability
    selected_ev = _first_available(
        ev_after_spread,
        model_context.get("ev_after_spread"),
        model_context.get("expected_value"),
        model_context.get("ev"),
        model_context.get("edge"),
    )
    selected_confidence = _first_available(confidence, model_context.get("confidence"))
    model_output_visible = any(
        _available(value)
        for value in (selected_probability, selected_fair_value, model_p_yes, model_p_no)
    )
    phase2_detail = trader._phase2_observability_payload(
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
    if _available(model_p_yes):
        phase2_detail.update({
            "p_yes": model_p_yes,
            "model_p_yes": model_p_yes,
            "model_probability_yes": model_p_yes,
            "fair_value_yes": _first_available(model_context.get("fair_value_yes"), model_p_yes),
        })
    if _available(model_p_no):
        phase2_detail.update({
            "p_no": model_p_no,
            "model_p_no": model_p_no,
            "model_probability_no": model_p_no,
            "fair_value_no": _first_available(model_context.get("fair_value_no"), model_p_no),
        })
    exposure_after = float(phase2_detail.get("exposure_after", 0.0) or 0.0)
    exposure_before = max(exposure_after - float(risk_plan.notional_size), 0.0)
    phase2_detail.update({
        "exposure_before": exposure_before,
        "risk_budget_used": exposure_before,
    })
    epoch_start_ts = int(epoch_start or 0)
    paper_trade_replay_key = trader._build_paper_trade_replay_key(
        condition_id=condition_id,
        epoch_start_ts=epoch_start_ts,
        ticker=ticker,
        outcome=outcome,
        token_id=token_id,
    )
    return {
        "model_context": model_context,
        "entry_attribution": entry_attribution,
        "model_p_yes": model_p_yes,
        "model_p_no": model_p_no,
        "selected_probability": selected_probability,
        "selected_fair_value": selected_fair_value,
        "selected_ev": selected_ev,
        "selected_confidence": selected_confidence,
        "model_output_visible": model_output_visible,
        "phase2_detail": phase2_detail,
        "epoch_start_ts": epoch_start_ts,
        "paper_trade_replay_key": paper_trade_replay_key,
        "runtime_mode": trader._runtime_mode(),
        "size_sharp_payload": trader._size_sharp_metadata(model_context.get("size_sharp_result")),
        "bankroll_rank": trader._last_bankroll_rank,
        "bankroll_family": trader._last_bankroll_family,
        "capital_score": trader._last_capital_score,
        "entry_model_truth_envelope": trader._build_entry_model_truth_envelope(
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


def _legacy_trade_open_payload(
    trader: DummyOpenContextTrader,
    *,
    market_id: str,
    ticker: str,
    token_id: str,
    outcome: str,
    receipt: DummyReceipt,
    risk_plan: SimpleNamespace,
    entry_price: float,
    strategy: str,
    seconds_remaining: int | None,
    epoch_start: int | None,
    condition_id: str,
    true_probability: float | None,
    fair_value: float | None,
    ev_after_spread: float | None,
    confidence: float | None,
    position_id: str | None,
    entry_attribution: dict[str, object] | None,
) -> dict[str, object]:
    context = _legacy_trade_open_context(
        trader,
        market_id=market_id,
        ticker=ticker,
        token_id=token_id,
        outcome=outcome,
        risk_plan=risk_plan,
        entry_price=entry_price,
        seconds_remaining=seconds_remaining,
        epoch_start=epoch_start,
        condition_id=condition_id,
        true_probability=true_probability,
        fair_value=fair_value,
        ev_after_spread=ev_after_spread,
        confidence=confidence,
        entry_attribution=entry_attribution,
    )
    model_context = context["model_context"]
    entry_attribution = context["entry_attribution"]
    phase2_detail = context["phase2_detail"]
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
        "mode": context["runtime_mode"],
        "condition_id": condition_id or "",
        "epoch_start_ts": context["epoch_start_ts"],
        "asset": ticker,
        "paper_trade_replay_key": context["paper_trade_replay_key"],
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
        "true_probability": context["selected_probability"],
        "fair_value": context["selected_fair_value"],
        "ev_after_spread": context["selected_ev"],
        "expected_value": context["selected_ev"],
        "ev": context["selected_ev"],
        "confidence": context["selected_confidence"],
        **context["size_sharp_payload"],
        "bankroll_rank": context["bankroll_rank"],
        "bankroll_family": context["bankroll_family"],
        "capital_score": context["capital_score"],
        "shadow_policy_decision": model_context.get("shadow_policy_decision"),
        "shadow_policy_reasons": model_context.get("shadow_policy_reasons"),
        "shadow_policy_observed_ev": model_context.get("shadow_policy_observed_ev"),
        "shadow_policy_observed_probability": model_context.get("shadow_policy_observed_probability"),
        "shadow_policy_observed_risk_mode": model_context.get("shadow_policy_observed_risk_mode"),
        "shadow_policy_id": model_context.get("shadow_policy_id"),
        "shadow_policy_confidence": model_context.get("shadow_policy_confidence"),
        **context["entry_model_truth_envelope"],
    }
    if isinstance(entry_attribution, dict):
        for field in ("candidate_id", "candidate_instance_id", "paper_trade_replay_key", "signal_name", "signal_reason"):
            if field in entry_attribution:
                open_payload[field] = entry_attribution[field]
    return open_payload


def _open_args() -> dict[str, object]:
    return {
        "market_id": "pm-5m-btc",
        "ticker": "BTC",
        "token_id": "tok-yes",
        "outcome": "YES",
        "risk_plan": SimpleNamespace(position_size=20.0, notional_size=10.0),
        "entry_price": 0.5,
        "seconds_remaining": 188,
        "epoch_start": 1780000000,
        "condition_id": "cond-abc",
        "true_probability": None,
        "fair_value": None,
        "ev_after_spread": None,
        "confidence": None,
        "entry_attribution": None,
    }


def test_collect_trade_open_context_matches_legacy_context() -> None:
    trader = DummyOpenContextTrader()
    args = _open_args()

    assert collect_trade_open_context(trader=trader, **args) == _legacy_trade_open_context(trader, **args)


def test_collect_trade_open_context_does_not_emit_or_mutate_trader_state() -> None:
    trader = DummyOpenContextTrader()
    before = deepcopy(trader.__dict__)

    context = collect_trade_open_context(trader=trader, **_open_args())

    assert context["runtime_mode"] == "paper"
    assert trader.__dict__ == before


def test_collect_trade_open_context_handles_missing_model_context() -> None:
    trader = DummyOpenContextTrader()
    trader.last_quant_details = {}
    args = _open_args()
    args.update({
        "ticker": "ETH",
        "outcome": "NO",
        "true_probability": 0.44,
        "fair_value": None,
        "ev_after_spread": -0.01,
        "confidence": 0.51,
    })

    context = collect_trade_open_context(trader=trader, **args)

    assert context["model_context"] == {}
    assert context["entry_attribution"] is None
    assert context["selected_probability"] == 0.44
    assert context["selected_fair_value"] == 0.44
    assert context["selected_ev"] == -0.01
    assert context["selected_confidence"] == 0.51
    assert context["phase2_detail"]["exposure_before"] == 8.0
    assert context["size_sharp_payload"] == {"size_sharp_close_carry_status": "missing_not_scored"}


def test_emit_trade_opened_event_payload_matches_legacy_controlled_case() -> None:
    trader = DummyOpenContextTrader()
    emitted: list[tuple[str, dict[str, object]]] = []
    trader._emit_quant_event = lambda event_name, payload: emitted.append((event_name, payload))  # type: ignore[method-assign]
    receipt = DummyReceipt(order_id="order-1", filled_size=20.0, average_price=0.5)
    args = _open_args()
    expected = _legacy_trade_open_payload(
        trader,
        receipt=receipt,
        strategy="phase3_entry",
        position_id="pos-1",
        **args,
    )

    PolymarketTrader._emit_trade_opened_event(
        trader,  # type: ignore[arg-type]
        receipt=receipt,  # type: ignore[arg-type]
        strategy="phase3_entry",
        position_id="pos-1",
        **args,
    )

    assert emitted == [("log_trade_open", expected)]


def test_build_trade_opened_payload_matches_legacy_payload_and_has_no_side_effects() -> None:
    trader = DummyOpenContextTrader()
    receipt = DummyReceipt(order_id="order-1", filled_size=20.0, average_price=0.5)
    args = _open_args()
    context = collect_trade_open_context(trader=trader, **args)
    before_context = deepcopy(context)
    expected = _legacy_trade_open_payload(
        trader,
        receipt=receipt,
        strategy="phase3_entry",
        position_id="pos-1",
        **args,
    )

    payload = build_trade_opened_payload(
        market_id=args["market_id"],
        ticker=args["ticker"],
        token_id=args["token_id"],
        outcome=args["outcome"],
        side=BUY,
        entry_price=args["entry_price"],
        position_size=args["risk_plan"].position_size,
        notional_size=args["risk_plan"].notional_size,
        receipt_payload=asdict(receipt),
        strategy="phase3_entry",
        condition_id=args["condition_id"],
        position_id="pos-1",
        trade_open_context=context,
    )

    assert payload == expected
    assert context == before_context


def test_build_trade_opened_payload_preserves_missing_context_behavior() -> None:
    trader = DummyOpenContextTrader()
    trader.last_quant_details = {}
    receipt = DummyReceipt(order_id="order-2", filled_size=12.0, average_price=0.44)
    args = _open_args()
    args.update({
        "ticker": "ETH",
        "token_id": "tok-no",
        "outcome": "NO",
        "true_probability": 0.44,
        "ev_after_spread": None,
        "confidence": None,
    })
    context = collect_trade_open_context(trader=trader, **args)
    expected = _legacy_trade_open_payload(
        trader,
        receipt=receipt,
        strategy="phase3_entry",
        position_id=None,
        **args,
    )

    payload = build_trade_opened_payload(
        market_id=args["market_id"],
        ticker=args["ticker"],
        token_id=args["token_id"],
        outcome=args["outcome"],
        side=BUY,
        entry_price=args["entry_price"],
        position_size=args["risk_plan"].position_size,
        notional_size=args["risk_plan"].notional_size,
        receipt_payload=asdict(receipt),
        strategy="phase3_entry",
        condition_id=args["condition_id"],
        position_id=None,
        trade_open_context=context,
    )

    assert payload == expected
    assert payload["entry_attribution_status"] == "missing"
    assert payload["signal_name"] is None
