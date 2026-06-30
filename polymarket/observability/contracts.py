"""Schema contracts for trade-event payload builders.

TypedDict definitions documenting the stable payload shapes produced by:
  - trader_reconciliation_carry.py
  - trader_trade_event_payload.py

All TypedDicts use total=False because several builders use **spread operators
(phase2_detail, size_sharp_payload, entry_model_truth_envelope) that can add
keys beyond those explicitly listed here. The declared fields are the stable
contract; spread-contributed keys are additive and must not remove declared keys.

Usage:
  from polymarket.observability.contracts import TradeOpenedPayload
  def build_trade_opened_payload(...) -> TradeOpenedPayload: ...
"""

from __future__ import annotations

from typing import TypedDict


class EntryModelTruthEnvelope(TypedDict, total=False):
    """Inner envelope dict returned by build_entry_model_truth_envelope.
    When carried via carry_entry_model_truth_from_metadata, also contains carried_from.
    """
    schema_version: str
    truth_status: str              # "full" | "probability_only" | "ev_only" | "absent"
    truth_source: str
    carried_from: str              # "position_metadata" when produced by carry helper
    producer_stage: str
    model_output_ready: bool
    model_attempted: bool
    model_not_run_reason: str
    probability_model_stage: str
    model_handoff_stage: str
    model_probability_yes: float | None
    model_probability_no: float | None
    selected_side: str
    true_probability: float | None
    fair_value: float | None
    ev_after_spread: float | None
    expected_value: float | None
    confidence: float | None
    ev_missing_reason: str
    lineage_reference_only: bool
    computed_at: str
    computed_by: str
    serialization_source: str


class EntryModelTruthEnvelopeWrapper(TypedDict, total=False):
    """Outer wrapper returned by build_entry_model_truth_envelope (or {} on failure)."""
    entry_model_truth_envelope_v1: EntryModelTruthEnvelope


class SizeSharpMetadata(TypedDict, total=False):
    """Output of size_sharp_metadata(). Two possible shapes:
    - result is None: {"size_sharp_close_carry_status": "missing_not_scored"}
    - result provided:  full 11-field dict plus no status key
    total=False covers both shapes.
    """
    size_sharp_at_entry: float | None
    size_sharp_bucket: str | None
    size_sharp_deployment_state: str | None
    size_sharp_limiting_factor: str | None
    size_sharp_confidence_grade: str | None
    size_sharp_component_scores: dict[str, object]
    size_sharp_penalties: dict[str, object]
    size_sharp_boosts: dict[str, object]
    size_sharp_hard_caps: list[object]
    size_sharp_missing_inputs: list[object]
    size_sharp_schema_version: str
    size_sharp_close_carry_status: str  # "missing_not_scored" when result is None


class SizeSharpCloseCarry(TypedDict, total=False):
    """Output of size_sharp_close_carry(). Always has size_sharp_close_carry_status."""
    size_sharp_at_entry: float | None
    size_sharp_bucket: str | None
    size_sharp_deployment_state: str | None
    size_sharp_limiting_factor: str | None
    size_sharp_confidence_grade: str | None
    size_sharp_component_scores: dict[str, object]
    size_sharp_penalties: dict[str, object]
    size_sharp_boosts: dict[str, object]
    size_sharp_hard_caps: list[object]
    size_sharp_missing_inputs: list[object]
    size_sharp_schema_version: str
    size_sharp_close_carry_status: str  # "carried" or "missing_legacy_metadata"


class CarryMetadata(TypedDict, total=False):
    """Output of carry_entry_model_truth_from_metadata(). Two possible shapes:
    - envelope absent: {"entry_model_truth_carry_status": "absent_in_metadata"}
    - envelope present: {"entry_model_truth_envelope_v1": {...}}
    total=False covers both shapes.
    """
    entry_model_truth_envelope_v1: EntryModelTruthEnvelope
    entry_model_truth_carry_status: str  # "absent_in_metadata" when envelope is missing


class TradeOpenContext(TypedDict, total=False):
    """Output of collect_trade_open_context()."""
    model_context: dict[str, object]
    entry_attribution: dict[str, object] | None
    model_p_yes: float | None
    model_p_no: float | None
    selected_probability: float | None
    selected_fair_value: float | None
    selected_ev: float | None
    selected_confidence: float | None
    model_output_visible: bool
    phase2_detail: dict[str, object]
    epoch_start_ts: int
    paper_trade_replay_key: str
    runtime_mode: str
    size_sharp_payload: SizeSharpMetadata
    bankroll_rank: object
    bankroll_family: object
    capital_score: object
    entry_model_truth_envelope: dict[str, object]


class TradePositionMetadata(TypedDict, total=False):
    """Output of build_trade_position_metadata()."""
    strategy: object
    signal_strategy: object
    token_id: object
    outcome: object
    entry_ev: object
    confidence: object
    delta_regime: object
    condition_id: object
    epoch_start_ts: object
    market_slug: object
    lifecycle_phase: object
    paper_trade_replay_key: str | None
    entry_model_truth_envelope_v1: EntryModelTruthEnvelope | None
    signal_name: object
    signal_reason: object
    strategy_signal_name: object
    strategy_signal_reason: object
    entry_attribution: dict[str, object]
    bankroll_tier_id: object
    bankroll_family: object
    risk_mode: object
    risk_budget: object
    current_exposure: object
    target_exposure: object
    notional_size: object
    seconds_remaining: object
    true_probability: object
    fair_value: object
    capital_score: object
    capital_state: object
    promotion_candidate: object
    demotion_candidate: object
    expected_risk_profile: object
    bankroll_rank: object
    shadow_policy_decision: object
    shadow_policy_reasons: object
    shadow_policy_observed_ev: object
    shadow_policy_observed_probability: object
    shadow_policy_observed_risk_mode: object
    shadow_policy_id: object
    shadow_policy_confidence: object
    # size_sharp fields spread from size_sharp_metadata()
    size_sharp_at_entry: float | None
    size_sharp_bucket: str | None
    size_sharp_deployment_state: str | None
    size_sharp_limiting_factor: str | None
    size_sharp_confidence_grade: str | None
    size_sharp_component_scores: dict[str, object]
    size_sharp_penalties: dict[str, object]
    size_sharp_boosts: dict[str, object]
    size_sharp_hard_caps: list[object]
    size_sharp_missing_inputs: list[object]
    size_sharp_schema_version: str
    size_sharp_close_carry_status: str


class TradeOpenedPayload(TypedDict, total=False):
    """Output of build_trade_opened_payload().

    Additional keys may be present from **phase2_detail, **size_sharp_payload,
    and **entry_model_truth_envelope spreads. The declared fields here are the
    stable contract — they must always be present in a valid payload.
    """
    market_id: str
    ticker: str
    token_id: str
    outcome: str
    side: object
    entry_price: float
    size: float
    notional_size: float
    receipt: dict[str, object]
    strategy: str
    mode: str | None
    condition_id: str
    epoch_start_ts: object
    asset: str
    paper_trade_replay_key: str | None
    candidate_peak_favorable: None
    candidate_peak_adverse: None
    signal_name: str | None
    signal_reason: str | None
    strategy_signal_name: str | None
    strategy_signal_reason: str | None
    position_id: str | None
    entry_attribution: dict[str, object] | None
    entry_attribution_status: str
    true_probability: float | None
    fair_value: float | None
    ev_after_spread: float | None
    expected_value: float | None
    ev: float | None
    confidence: float | None
    bankroll_rank: object
    bankroll_family: object
    capital_score: object
    shadow_policy_decision: object
    shadow_policy_reasons: object
    shadow_policy_observed_ev: object
    shadow_policy_observed_probability: object
    shadow_policy_observed_risk_mode: object
    shadow_policy_id: object
    shadow_policy_confidence: object
    # conditionally present when entry_attribution is a dict
    candidate_id: str | None
    candidate_instance_id: str | None


class TradeClosedPayload(TypedDict, total=False):
    """Output of build_trade_closed_payload().

    Additional keys may be present from **size_sharp_carry and
    **entry_model_truth_carry spreads.
    """
    position_id: str
    market_id: str
    ticker: str
    token_id: str
    outcome: str
    reason: str
    exit_reason: str
    paper_virtual_cash: float | None
    exit_price: float
    exit_timestamp: str
    hold_seconds: int | None
    size: float
    pnl: float
    pnl_usdc: float
    trade_result: str | None
    entry_price: float | None
    partial: bool
    receipt: dict[str, object]
    mode: str
    condition_id: str
    epoch_start_ts: int
    asset: str
    paper_trade_replay_key: str
    candidate_peak_favorable: None
    candidate_peak_adverse: None
    true_probability: float | None
    fair_value: float | None
    ev: float | None
    ev_after_spread: float | None
    confidence: float | None
    signal_name: str | None
    signal_reason: str | None
    strategy_signal_name: str | None
    strategy_signal_reason: str | None
    lifecycle_phase: object
    seconds_remaining: object
    bankroll_tier_id: object
    bankroll_family: object
    risk_mode: object
    risk_budget: object
    current_exposure: object
    target_exposure: object
    notional_size: object
    capital_score: object
    capital_state: object
    promotion_candidate: object
    demotion_candidate: object
    expected_risk_profile: object
    bankroll_rank: object
    shadow_policy_decision: object
    shadow_policy_observed_ev: object
    shadow_policy_observed_probability: object
    shadow_policy_observed_risk_mode: object
    shadow_policy_id: object
    entry_attribution: dict[str, object]
    entry_attribution_status: str
    # conditionally present when entry_attribution is a dict
    candidate_id: str
    candidate_instance_id: str
