from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from polymarket.bankroll_tiers import BankrollTier
from polymarket.delta_engine import DeltaRegime
from polymarket.expected_value import ExpectedValueInput, ExpectedValueResult, ExpectedValueTier, evaluate_entry
from polymarket.trade_frequency import TradeFrequencyInput, evaluate_trade_frequency


CANDIDATE_IDENTITY_SCHEMA_VERSION = "1.0"


def _new_candidate_id() -> str:
    return f"candidate_{uuid4().hex}"


def _candidate_trace_id(schema_version: str, candidate_id: str) -> str:
    digest = hashlib.sha256(f"{schema_version}|{candidate_id}".encode("utf-8")).hexdigest()[:16]
    return f"ct_{digest}"


def _candidate_created_at() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _initialize_candidate_identity(value: object) -> None:
    schema_version = str(
        getattr(value, "candidate_identity_schema_version", "") or CANDIDATE_IDENTITY_SCHEMA_VERSION
    )
    candidate_id = str(getattr(value, "candidate_id", "") or _new_candidate_id())
    candidate_trace_id = str(
        getattr(value, "candidate_trace_id", "") or _candidate_trace_id(schema_version, candidate_id)
    )
    candidate_created_at = str(getattr(value, "candidate_created_at", "") or _candidate_created_at())
    object.__setattr__(value, "candidate_identity_schema_version", schema_version)
    object.__setattr__(value, "candidate_id", candidate_id)
    object.__setattr__(value, "candidate_trace_id", candidate_trace_id)
    object.__setattr__(value, "candidate_created_at", candidate_created_at)


class OpportunityDecision(str, Enum):
    BEST_TRADE = "BEST_TRADE"
    WATCHLIST = "WATCHLIST"
    SKIP = "SKIP"


@dataclass(frozen=True, slots=True)
class OpportunityInput:
    market_id: str
    asset: str
    p_yes: float
    p_no: float
    yes_ask: float
    no_ask: float
    confidence_score: float
    delta_score: float
    delta_regime: DeltaRegime | str
    delta_multiplier: float = 1.0
    spread: float = 0.0
    liquidity: float = 1_000.0
    time_remaining_seconds: int = 300
    price_velocity: float = 0.0
    distance_to_strike: float = 0.0
    orderbook_bid_size: float = 0.0
    orderbook_ask_size: float = 0.0
    drawdown_pct: float = 0.0
    trades_for_market: int = 0
    min_ev: float = 0.02
    min_confidence: float = 0.54
    risk_off: bool = False
    candidate_id: str = field(default="", compare=False, kw_only=True)
    candidate_trace_id: str = field(default="", compare=False, kw_only=True)
    candidate_created_at: str = field(default="", compare=False, kw_only=True)
    candidate_identity_schema_version: str = field(
        default=CANDIDATE_IDENTITY_SCHEMA_VERSION,
        compare=False,
        kw_only=True,
    )

    def __post_init__(self) -> None:
        _initialize_candidate_identity(self)


@dataclass(frozen=True, slots=True)
class OpportunityResult:
    market_id: str
    decision: OpportunityDecision
    side: str
    score: float
    ev: float
    probability_edge: float
    skip_reason: str = ""


@dataclass(frozen=True, slots=True)
class OpportunityCandidate:
    market_id: str
    asset: str
    p_yes: float
    p_no: float
    yes_ask: float
    no_ask: float
    confidence_score: float
    delta_score: float
    delta_regime: DeltaRegime | str
    spread: float
    liquidity: float
    time_remaining_seconds: int
    price_velocity: float
    distance_to_strike: float
    orderbook_bid_size: float
    orderbook_ask_size: float
    drawdown_pct: float = 0.0
    trades_for_market: int = 0
    delta_multiplier: float = 1.0
    candidate_id: str = field(default="", compare=False, kw_only=True)
    candidate_trace_id: str = field(default="", compare=False, kw_only=True)
    candidate_created_at: str = field(default="", compare=False, kw_only=True)
    candidate_identity_schema_version: str = field(
        default=CANDIDATE_IDENTITY_SCHEMA_VERSION,
        compare=False,
        kw_only=True,
    )

    def __post_init__(self) -> None:
        _initialize_candidate_identity(self)


@dataclass(frozen=True, slots=True)
class OpportunityScanContext:
    ev_tier: ExpectedValueTier = field(default_factory=ExpectedValueTier)
    bankroll_tier: BankrollTier | str = BankrollTier.MICRO
    trades_last_hour: int = 0
    seconds_since_last_entry: float | None = None
    last_trade_result: str = ""
    risk_off: bool = False
    reconciliation_safe: bool = True
    max_trades_per_market: int = 1
    confidence_floor: float = 0.54
    max_spread: float = 0.10
    min_liquidity: float = 10.0


@dataclass(frozen=True, slots=True)
class ScoredOpportunity:
    candidate: OpportunityCandidate
    decision: OpportunityDecision
    side: str
    score: float
    ev: float
    probability_edge: float
    ev_result: ExpectedValueResult
    skip_reason: str = ""


@dataclass(frozen=True, slots=True)
class OpportunityScanResult:
    decision: OpportunityDecision
    best_trade: ScoredOpportunity | None
    watchlist: tuple[ScoredOpportunity, ...]
    skipped: tuple[ScoredOpportunity, ...]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _as_regime(value: DeltaRegime | str) -> DeltaRegime:
    if isinstance(value, DeltaRegime):
        return value
    return DeltaRegime[str(value).upper()]


def _orderbook_imbalance(candidate: OpportunityCandidate) -> float:
    total = candidate.orderbook_bid_size + candidate.orderbook_ask_size
    if total <= 0:
        return 0.0
    return (candidate.orderbook_bid_size - candidate.orderbook_ask_size) / total


def _probability_edge(candidate: OpportunityCandidate, side: str) -> float:
    if side == "NO":
        return candidate.p_no - candidate.no_ask
    return candidate.p_yes - candidate.yes_ask


def _score(candidate: OpportunityCandidate, ev: float, probability_edge: float) -> float:
    liquidity_score = _clamp(candidate.liquidity / 1_000.0, 0.0, 2.0)
    confidence_score = _clamp((candidate.confidence_score - 0.50) * 10.0, 0.0, 3.0)
    momentum_score = _clamp(abs(candidate.price_velocity) / 0.004, 0.0, 2.0)
    momentum_score += _clamp(abs(_orderbook_imbalance(candidate)), 0.0, 1.0)

    spread_penalty = _clamp(candidate.spread / 0.02, 0.0, 6.0)
    delta_penalty = {
        DeltaRegime.LOW: 0.0,
        DeltaRegime.NORMAL: 0.8,
        DeltaRegime.HIGH: 2.0,
        DeltaRegime.EXTREME: 5.0,
    }[_as_regime(candidate.delta_regime)]
    drawdown_penalty = _clamp(candidate.drawdown_pct / 0.02, 0.0, 5.0)
    time_penalty = 0.0
    if candidate.time_remaining_seconds < 150:
        time_penalty = _clamp((150 - candidate.time_remaining_seconds) / 30.0, 0.0, 4.0)

    distance_bonus = _clamp(0.004 / max(abs(candidate.distance_to_strike), 0.0005), 0.0, 1.5)

    return (
        _clamp(ev * 100.0, -5.0, 10.0)
        + _clamp(probability_edge * 100.0, -5.0, 10.0)
        + confidence_score
        + liquidity_score
        + momentum_score
        + distance_bonus
        - spread_penalty
        - delta_penalty
        - drawdown_penalty
        - time_penalty
    )


def _hard_skip_reason(candidate: OpportunityCandidate, context: OpportunityScanContext) -> str:
    regime = _as_regime(candidate.delta_regime)
    if context.risk_off:
        return "risk_off"
    if not context.reconciliation_safe:
        return "reconciliation_unsafe"
    if candidate.trades_for_market >= context.max_trades_per_market:
        return "max_trades_per_market_reached"
    if candidate.confidence_score < context.confidence_floor:
        return "confidence_too_low"
    if regime == DeltaRegime.EXTREME or candidate.delta_multiplier <= 0:
        return "delta_extreme"
    if candidate.spread > context.max_spread:
        return "spread_too_wide"
    if candidate.liquidity < context.min_liquidity:
        return "liquidity_too_low"
    if candidate.time_remaining_seconds <= 90:
        return "time_remaining_le_90s"
    return ""


def _candidate_from_input(opportunity: OpportunityInput) -> OpportunityCandidate:
    return OpportunityCandidate(
        market_id=opportunity.market_id,
        asset=opportunity.asset,
        p_yes=opportunity.p_yes,
        p_no=opportunity.p_no,
        yes_ask=opportunity.yes_ask,
        no_ask=opportunity.no_ask,
        confidence_score=opportunity.confidence_score,
        delta_score=opportunity.delta_score,
        delta_regime=opportunity.delta_regime,
        delta_multiplier=opportunity.delta_multiplier,
        spread=opportunity.spread,
        liquidity=opportunity.liquidity,
        time_remaining_seconds=opportunity.time_remaining_seconds,
        price_velocity=opportunity.price_velocity,
        distance_to_strike=opportunity.distance_to_strike,
        orderbook_bid_size=opportunity.orderbook_bid_size,
        orderbook_ask_size=opportunity.orderbook_ask_size,
        drawdown_pct=opportunity.drawdown_pct,
        trades_for_market=opportunity.trades_for_market,
        candidate_id=opportunity.candidate_id,
        candidate_trace_id=opportunity.candidate_trace_id,
        candidate_created_at=opportunity.candidate_created_at,
        candidate_identity_schema_version=opportunity.candidate_identity_schema_version,
    )


def scan_opportunity(
    opportunity: OpportunityInput,
    context: OpportunityScanContext | None = None,
) -> OpportunityResult:
    context = context or OpportunityScanContext(
        ev_tier=ExpectedValueTier(min_ev=opportunity.min_ev),
        confidence_floor=opportunity.min_confidence,
        risk_off=opportunity.risk_off,
    )
    candidate = _candidate_from_input(opportunity)
    if opportunity.risk_off:
        context = OpportunityScanContext(
            ev_tier=context.ev_tier,
            bankroll_tier=context.bankroll_tier,
            trades_last_hour=context.trades_last_hour,
            seconds_since_last_entry=context.seconds_since_last_entry,
            last_trade_result=context.last_trade_result,
            risk_off=True,
            reconciliation_safe=context.reconciliation_safe,
            max_trades_per_market=context.max_trades_per_market,
            confidence_floor=context.confidence_floor,
            max_spread=context.max_spread,
            min_liquidity=context.min_liquidity,
        )
    ev_result = evaluate_entry(
        ExpectedValueInput(
            p_yes=candidate.p_yes,
            p_no=candidate.p_no,
            yes_ask=candidate.yes_ask,
            no_ask=candidate.no_ask,
            confidence_score=candidate.confidence_score,
            spread=candidate.spread,
            liquidity=candidate.liquidity,
            delta=candidate.delta_score,
            tier=context.ev_tier,
            confidence_floor=context.confidence_floor,
        )
    )
    side = ev_result.side if ev_result.side in {"YES", "NO"} else "SKIP"
    ev = ev_result.ev_no if side == "NO" else ev_result.ev_yes
    probability_edge = _probability_edge(candidate, side if side != "SKIP" else "YES")
    score = _score(candidate, ev, probability_edge)

    hard_skip = _hard_skip_reason(candidate, context)
    if hard_skip:
        return OpportunityResult(candidate.market_id, OpportunityDecision.SKIP, "SKIP", score, ev, probability_edge, hard_skip)
    if not ev_result.approved:
        return OpportunityResult(candidate.market_id, OpportunityDecision.SKIP, "SKIP", score, ev, probability_edge, ev_result.skip_reason)
    return OpportunityResult(candidate.market_id, OpportunityDecision.BEST_TRADE, side, score, ev, probability_edge)


def rank_opportunities(
    opportunities: list[OpportunityInput] | tuple[OpportunityInput, ...],
    context: OpportunityScanContext | None = None,
) -> tuple[OpportunityResult, ...]:
    return tuple(sorted(
        (scan_opportunity(opportunity, context) for opportunity in opportunities),
        key=lambda result: result.score,
        reverse=True,
    ))


def scan_opportunities(
    candidates: list[OpportunityCandidate] | tuple[OpportunityCandidate, ...],
    context: OpportunityScanContext | None = None,
) -> OpportunityScanResult:
    context = context or OpportunityScanContext()

    watchlist: list[ScoredOpportunity] = []
    skipped: list[ScoredOpportunity] = []
    best: ScoredOpportunity | None = None

    frequency = evaluate_trade_frequency(
        TradeFrequencyInput(
            tier=context.bankroll_tier,
            trades_last_hour=context.trades_last_hour,
            seconds_since_last_entry=context.seconds_since_last_entry,
            last_trade_result=context.last_trade_result,
            risk_off=context.risk_off,
            reconciliation_safe=context.reconciliation_safe,
            max_trades_per_market=context.max_trades_per_market,
        )
    )

    for candidate in candidates:
        ev_result = evaluate_entry(
            ExpectedValueInput(
                p_yes=candidate.p_yes,
                p_no=candidate.p_no,
                yes_ask=candidate.yes_ask,
                no_ask=candidate.no_ask,
                confidence_score=candidate.confidence_score,
                spread=candidate.spread,
                liquidity=candidate.liquidity,
                delta=candidate.delta_score,
                tier=context.ev_tier,
                confidence_floor=context.confidence_floor,
            )
        )
        side = ev_result.side if ev_result.side in {"YES", "NO"} else "SKIP"
        ev = ev_result.ev_no if side == "NO" else ev_result.ev_yes
        probability_edge = _probability_edge(candidate, side if side != "SKIP" else "YES")
        score = _score(candidate, ev, probability_edge)

        hard_skip = _hard_skip_reason(candidate, context)
        if hard_skip or not ev_result.approved:
            reason = hard_skip or ev_result.skip_reason
            skipped.append(
                ScoredOpportunity(candidate, OpportunityDecision.SKIP, "SKIP", score, ev, probability_edge, ev_result, reason)
            )
            continue

        market_frequency = evaluate_trade_frequency(
            TradeFrequencyInput(
                tier=context.bankroll_tier,
                trades_last_hour=context.trades_last_hour,
                trades_for_market=candidate.trades_for_market,
                seconds_since_last_entry=context.seconds_since_last_entry,
                last_trade_result=context.last_trade_result,
                risk_off=context.risk_off,
                reconciliation_safe=context.reconciliation_safe,
                max_trades_per_market=context.max_trades_per_market,
                liquidity=candidate.liquidity,
            )
        )
        frequency_blocked = tuple(dict.fromkeys(frequency.blocked_reasons + market_frequency.blocked_reasons))

        if not frequency_blocked:
            scored = ScoredOpportunity(
                candidate,
                OpportunityDecision.BEST_TRADE,
                side,
                score,
                ev,
                probability_edge,
                ev_result,
            )
            if best is None or scored.score > best.score:
                best = scored
            continue

        reason = ",".join(frequency_blocked) or "watch_only"
        skipped.append(
            ScoredOpportunity(
                candidate,
                OpportunityDecision.SKIP,
                side,
                score,
                ev,
                probability_edge,
                ev_result,
                reason,
            )
        )

    watchlist.sort(key=lambda item: item.score, reverse=True)
    skipped.sort(key=lambda item: item.score, reverse=True)

    if best is not None:
        return OpportunityScanResult(OpportunityDecision.BEST_TRADE, best, tuple(watchlist), tuple(skipped))
    if watchlist:
        return OpportunityScanResult(OpportunityDecision.WATCHLIST, None, tuple(watchlist), tuple(skipped))
    return OpportunityScanResult(OpportunityDecision.SKIP, None, (), tuple(skipped))
