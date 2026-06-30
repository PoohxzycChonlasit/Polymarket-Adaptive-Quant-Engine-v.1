"""
Shadow Strategy Evaluation Framework — schema-only offline contracts.

Offline use only. This module must NEVER import from polymarket.trader,
polymarket.client, config.settings, or any module that reaches live state.

All TypedDicts are schema definitions for JSON-serializable replay evaluation
rows. No runtime enforcement occurs — validation is the responsibility of
adapters and plugins, guided by the helper functions below.

Schema version: shadow_replay_row.v0_1
"""
from __future__ import annotations

from enum import Enum
from typing import Any, NotRequired, TypedDict

# ── Schema version constants ──────────────────────────────────────────────────

REPLAY_ROW_SCHEMA_VERSION: str = "shadow_replay_row.v0_1"
STRATEGY_DECISION_SCHEMA_VERSION: str = "strategy_decision.v0_1"

# ── Path-truth field guard ────────────────────────────────────────────────────
# All names in this set are scoring-only metadata. No strategy plugin may use
# them for entry/exit logic without proving causal timestamp-safety and
# declaring an explicit exception in its StrategyPluginMetadata.

PATH_TRUTH_SCORING_ONLY_FIELDS: frozenset[str] = frozenset({
    "mfe",
    "mae",
    "max_price",
    "min_price",
    "tp_touched",
    "sl_touched",
    "settlement_outcome",
    "settlement_price",
    "resolution_confidence",
    "path_sample_count",
})

# ── Required ReplayRow container keys ─────────────────────────────────────────
# Any key absent from a row dict signals DATA_BLOCKED for that row.

REQUIRED_REPLAY_ROW_CONTAINER_KEYS: frozenset[str] = frozenset({
    "schema_version",
    "row_id",
    "identity",
    "market",
    "model",
    "runtime_decision",
    "lifecycle_truth",
    "path_truth",
    "quality",
    "provenance",
})

# ── Required StrategySummary metric keys ──────────────────────────────────────
# Plugins must populate all of these in StrategySummary.metrics.

STRATEGY_SUMMARY_REQUIRED_METRIC_KEYS: frozenset[str] = frozenset({
    "win_rate",
    "total_pnl",
    "profit_factor",
    "expectancy",
    "max_drawdown_pct",
    "capital_utilization",
    "exposure_peak",
    "avg_hold_seconds",
    "mfe",
    "mae",
})


# ── Enums ─────────────────────────────────────────────────────────────────────

class StrategyAction(str, Enum):
    """
    Allowed plugin output actions.

    ENTRY is a hypothetical offline-only action. It does NOT grant runtime
    permission and must never be wired into live or paper execution paths
    without a separately approved implementation phase.
    """
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    HOLD = "HOLD"
    SKIP = "SKIP"


class EvidenceGrade(str, Enum):
    """
    Evidence quality grades for individual fields and rows.

    A — Runtime-observed: present in JSONL evidence from actual paper/live runs.
    B — Code-verified: confirmed by reading source code, not just docs.
    C — Test-verified: confirmed by test fixtures only; no runtime evidence.
    D — Documentation-aligned: referenced in docs; partial or historical data.
    E — Inferred only: estimated or extrapolated; never sufficient alone for READY.
    """
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class Recommendation(str, Enum):
    """
    EvidenceDecision promotion recommendations.

    TRUTH_BLOCKED  — Settlement/path truth absent or an active question
                     prevents promoting this finding.
    DATA_BLOCKED   — Required structural fields or plugin inputs are missing.
    RISK_BLOCKED   — Replay implies drawdown, exposure, or concentration
                     violations under current risk configuration.
    NOT_READY      — Mechanics work but sample size, evidence grade, or truth
                     coverage is insufficient for promotion.
    READY          — Evidence grade, sample size, truth coverage, and risk
                     boundaries all pass for this plugin.
    """
    TRUTH_BLOCKED = "TRUTH_BLOCKED"
    DATA_BLOCKED = "DATA_BLOCKED"
    RISK_BLOCKED = "RISK_BLOCKED"
    NOT_READY = "NOT_READY"
    READY = "READY"


class PluginFamily(str, Enum):
    """Strategy plugin classification families."""
    BASELINE = "baseline"
    GATE_RELAXATION = "gate_relaxation"
    SEMANTIC = "semantic"
    INVENTORY = "inventory"
    ALPHA = "alpha"


# ── ReplayRow nested containers ───────────────────────────────────────────────

class ReplayIdentity(TypedDict, total=True):
    """Stable row identity and provenance anchors."""
    # Required
    run_id: str
    timestamp_utc: str
    source_stream: str
    source_event_type: str
    row_id: str
    # Optional (strongly recommended)
    trade_id: NotRequired[str | None]
    position_id: NotRequired[str | None]
    paper_trade_replay_key: NotRequired[str | None]
    market_slug: NotRequired[str | None]
    condition_id: NotRequired[str | None]
    token_id: NotRequired[str | None]
    asset: NotRequired[str | None]
    outcome: NotRequired[str | None]
    side: NotRequired[str | None]
    epoch_start_ts: NotRequired[str | None]
    # Provenance
    source_file: NotRequired[str | None]
    source_line: NotRequired[int | None]
    source_event_ids: NotRequired[list[str]]
    adapter_name: NotRequired[str | None]
    adapter_version: NotRequired[str | None]


class ReplayMarketState(TypedDict, total=True):
    """Market orderbook and availability snapshot at the decision moment."""
    # Required
    market_state: str
    orderbook_state: str
    seconds_remaining: int | float
    # Optional
    best_bid: NotRequired[float | None]
    best_ask: NotRequired[float | None]
    spread: NotRequired[float | None]
    mid_price: NotRequired[float | None]
    liquidity_notional: NotRequired[float | None]
    depth_score: NotRequired[float | None]
    quote_age_ms: NotRequired[float | None]
    market_regime: NotRequired[str | None]
    availability_state: NotRequired[str | None]
    availability_source: NotRequired[str | None]
    clob_error: NotRequired[str | None]


class ReplayModelState(TypedDict, total=True):
    """
    Model probability and confidence state at the decision moment.

    IMPORTANT: top_level_confidence and selected_side_probability are
    intentionally kept separate. The risk-plan-zero audit (2026-06-25)
    confirmed they measure different things and must not be collapsed into
    a single field or aliased in any plugin.
    """
    # Required
    model_attempted: bool
    selected_side: str
    selected_side_probability: float
    top_level_confidence: float
    # Optional
    true_probability: NotRequired[float | None]
    model_p_yes: NotRequired[float | None]
    model_p_no: NotRequired[float | None]
    fair_value: NotRequired[float | None]
    ev: NotRequired[float | None]
    ev_after_spread: NotRequired[float | None]
    decision_score: NotRequired[float | None]
    probability_edge: NotRequired[float | None]
    confidence_reason: NotRequired[str | None]
    evidence_grade: NotRequired[str | None]
    reason_codes: NotRequired[list[str]]
    blockers: NotRequired[list[str]]


class ReplayRuntimeDecision(TypedDict, total=True):
    """What the current runtime decided and why — captured from JSONL events."""
    # Required
    baseline_action: str
    primary_skip_reason: str
    all_skip_reasons: list[str]
    risk_mode: str
    risk_plan_state: str
    # Optional
    planned_notional: NotRequired[float | None]
    planned_shares: NotRequired[float | None]
    risk_plan_zero_reason: NotRequired[str | None]
    bankroll: NotRequired[float | None]
    equity: NotRequired[float | None]
    bankroll_rank: NotRequired[str | None]
    bankroll_tier_id: NotRequired[str | None]
    risk_budget: NotRequired[float | None]
    current_exposure: NotRequired[float | None]
    target_exposure: NotRequired[float | None]
    size_sharp: NotRequired[float | None]
    size_sharp_bucket: NotRequired[str | None]
    lifecycle_phase: NotRequired[str | None]
    inventory_state: NotRequired[str | None]


class ReplayLifecycleTruth(TypedDict, total=True):
    """Ground truth about the trade lifecycle derived from JSONL evidence."""
    # Required
    trade_open_observed: bool
    trade_close_observed: bool
    fill_observed: bool
    lifecycle_status: str
    # Optional
    entry_timestamp: NotRequired[str | None]
    entry_price: NotRequired[float | None]
    entry_size: NotRequired[float | None]
    entry_notional: NotRequired[float | None]
    exit_timestamp: NotRequired[str | None]
    exit_price: NotRequired[float | None]
    exit_reason: NotRequired[str | None]
    hold_seconds: NotRequired[int | float | None]
    realized_pnl: NotRequired[float | None]
    paper_virtual_cash: NotRequired[float | None]
    current_exposure_after: NotRequired[float | None]


class ReplayPathTruth(TypedDict, total=True):
    """
    Post-trade price path metadata — SCORING ONLY.

    Fields in PATH_TRUTH_SCORING_ONLY_FIELDS must never be used by a plugin
    to make entry or exit decisions. They are retroactive price data not
    available at decision time. A plugin may only use them for evaluation
    scoring, and must set uses_path_truth_for_scoring_only=True in its
    StrategyPluginMetadata.
    """
    # Required
    path_available: bool
    truth_source: str
    # Optional (all scoring-only — see PATH_TRUTH_SCORING_ONLY_FIELDS)
    mfe: NotRequired[float | None]
    mae: NotRequired[float | None]
    max_price: NotRequired[float | None]
    min_price: NotRequired[float | None]
    tp_touched: NotRequired[bool | None]
    sl_touched: NotRequired[bool | None]
    settlement_outcome: NotRequired[str | None]
    settlement_price: NotRequired[float | None]
    resolution_confidence: NotRequired[float | None]
    path_sample_count: NotRequired[int | None]


class ReplayQuality(TypedDict, total=True):
    """Row data quality metadata and blocker inventory."""
    # Required
    data_quality_grade: str
    join_confidence: float
    missing_fields: list[str]
    missing_critical_fields: list[str]
    missing_high_fields: list[str]
    missing_medium_fields: list[str]
    missing_low_fields: list[str]
    missing_info_fields: list[str]
    evidence_grade: str
    quality_notes: list[str]
    # Optional
    source_streams: NotRequired[list[str]]
    field_availability: NotRequired[dict[str, bool]]
    truth_blockers: NotRequired[list[str]]
    risk_blockers: NotRequired[list[str]]
    data_blockers: NotRequired[list[str]]
    active_question_blockers: NotRequired[list[str]]


class ReplayRow(TypedDict, total=True):
    """
    One immutable offline evaluation row.

    Represents a normalized decision snapshot that may correspond to a runtime
    decision, candidate entry, paper fill, closed trade, lifecycle path record,
    or enriched canonical event.

    All containers are required. Missing containers → DATA_BLOCKED.
    Missing subfields are evaluated by ReplayQuality and each plugin's
    required_replay_fields list.

    The provenance dict stores adapter-specific lineage metadata.
    """
    schema_version: str
    row_id: str
    identity: ReplayIdentity
    market: ReplayMarketState
    model: ReplayModelState
    runtime_decision: ReplayRuntimeDecision
    lifecycle_truth: ReplayLifecycleTruth
    path_truth: ReplayPathTruth
    quality: ReplayQuality
    provenance: dict[str, Any]


# ── Strategy framework contracts ──────────────────────────────────────────────

class StrategyPluginMetadata(TypedDict, total=True):
    """
    Plugin declaration. All required fields must be set before any replay run.

    runtime_imports_allowed MUST be False for all framework plugins.
    A plugin that imports polymarket.trader, polymarket.client, or
    config.settings is not a shadow strategy plugin — it is a runtime module
    and must not be evaluated here.
    """
    # Required
    plugin_id: str
    plugin_version: str
    family: str
    display_name: str
    description: str
    required_replay_fields: list[str]
    optional_replay_fields: list[str]
    decision_actions: list[str]
    uses_path_truth_for_scoring_only: bool
    runtime_imports_allowed: bool  # Must always be False
    # Optional
    blocked_by_active_questions: NotRequired[list[str]]
    risk_assumption_profile: NotRequired[str | None]
    capital_model_assumption: NotRequired[str | None]
    fee_model_assumption: NotRequired[str | None]
    slippage_model_assumption: NotRequired[str | None]
    supported_assets: NotRequired[list[str]]
    supported_market_types: NotRequired[list[str]]


class StrategyDecision(TypedDict, total=True):
    """
    Plugin output for one ReplayRow.

    ENTRY is a hypothetical offline action only. It does NOT represent runtime
    authorization. A plugin that emits ENTRY must not be wired into paper or
    live execution without a separately approved implementation phase.

    Valid action values: StrategyAction enum members.
    """
    schema_version: str
    plugin_id: str
    row_id: str
    action: str
    confidence: float
    reason: str
    reject_reasons: list[str]
    metrics: dict[str, Any]
    provenance: dict[str, Any]
    # Optional
    side: NotRequired[str | None]
    target_price: NotRequired[float | None]
    target_notional: NotRequired[float | None]
    target_shares: NotRequired[float | None]
    max_exposure: NotRequired[float | None]
    risk_budget_used: NotRequired[float | None]
    decision_score: NotRequired[float | None]
    shadow_policy_id: NotRequired[str | None]
    notes: NotRequired[str | None]


class StrategyRunContext(TypedDict, total=True):
    """
    Evaluation run configuration.

    All assumptions (bankroll model, fee model, slippage model) must be
    recorded for replay reproducibility. Omitting them makes comparison
    across runs undefined.
    """
    dataset_id: str
    dataset_version: str
    plugin_id: str
    run_started_at_utc: str
    row_count: int
    evaluation_mode: str
    baseline_name: str
    # Optional
    run_ids: NotRequired[list[str]]
    date_range: NotRequired[dict[str, str]]
    asset_filter: NotRequired[list[str]]
    market_filter: NotRequired[list[str]]
    quality_filter: NotRequired[dict[str, Any]]
    bankroll_model: NotRequired[str | None]
    fee_model: NotRequired[str | None]
    slippage_model: NotRequired[str | None]
    active_questions: NotRequired[list[str]]
    excluded_rows: NotRequired[list[str]]
    exclusion_reasons: NotRequired[dict[str, str]]


class StrategySummary(TypedDict, total=True):
    """
    Aggregated plugin results over a ReplayRow dataset.

    metrics must contain all keys in STRATEGY_SUMMARY_REQUIRED_METRIC_KEYS.
    Absent metric keys → evaluation is incomplete; do not issue READY.
    """
    plugin_id: str
    dataset_id: str
    evaluated_rows: int
    entry_count: int
    exit_count: int
    hold_count: int
    skip_count: int
    blocked_count: int
    decision_distribution: dict[str, int]
    metrics: dict[str, Any]
    quality_summary: dict[str, Any]


class EvidenceDecision(TypedDict, total=True):
    """
    Final framework recommendation for a plugin over a dataset.

    recommendation — one of Recommendation enum values.
    evidence_grade  — aggregate grade for the dataset (EvidenceGrade values).
    blockers        — human-readable blocker descriptions.
    required_next_evidence — ordered list of evidence items needed to improve.
    """
    recommendation: str
    evidence_grade: str
    confidence: float
    blockers: list[str]
    required_next_evidence: list[str]
    # Optional
    plugin_id: NotRequired[str]
    dataset_id: NotRequired[str]
    notes: NotRequired[str | None]
    metrics_summary: NotRequired[dict[str, Any]]


# ── Helper functions ──────────────────────────────────────────────────────────

def validate_required_replay_row_containers(row: dict[str, Any]) -> list[str]:
    """
    Return a sorted list of missing required ReplayRow container keys.

    An empty result means all required containers are present.
    A non-empty result signals DATA_BLOCKED for that row; plugins should
    decline to evaluate it and record the missing keys in their provenance.
    """
    return sorted(k for k in REQUIRED_REPLAY_ROW_CONTAINER_KEYS if k not in row)


def make_minimal_replay_row(
    row_id: str,
    run_id: str,
    timestamp_utc: str,
) -> ReplayRow:
    """
    Build a minimal but structurally valid ReplayRow for fixtures and tests.

    All required subfields are populated with zero/empty sentinel values.
    Optional subfields are omitted. Do not use the result for real evaluation
    without populating the actual market, model, and lifecycle fields.
    """
    identity: ReplayIdentity = {
        "run_id": run_id,
        "timestamp_utc": timestamp_utc,
        "source_stream": "",
        "source_event_type": "",
        "row_id": row_id,
    }
    market: ReplayMarketState = {
        "market_state": "",
        "orderbook_state": "",
        "seconds_remaining": 0,
    }
    model: ReplayModelState = {
        "model_attempted": False,
        "selected_side": "",
        "selected_side_probability": 0.0,
        "top_level_confidence": 0.0,
    }
    runtime_decision: ReplayRuntimeDecision = {
        "baseline_action": StrategyAction.SKIP.value,
        "primary_skip_reason": "",
        "all_skip_reasons": [],
        "risk_mode": "",
        "risk_plan_state": "",
    }
    lifecycle_truth: ReplayLifecycleTruth = {
        "trade_open_observed": False,
        "trade_close_observed": False,
        "fill_observed": False,
        "lifecycle_status": "",
    }
    path_truth: ReplayPathTruth = {
        "path_available": False,
        "truth_source": "",
    }
    quality: ReplayQuality = {
        "data_quality_grade": EvidenceGrade.E.value,
        "join_confidence": 0.0,
        "missing_fields": [],
        "missing_critical_fields": [],
        "missing_high_fields": [],
        "missing_medium_fields": [],
        "missing_low_fields": [],
        "missing_info_fields": [],
        "evidence_grade": EvidenceGrade.E.value,
        "quality_notes": [],
    }
    return {
        "schema_version": REPLAY_ROW_SCHEMA_VERSION,
        "row_id": row_id,
        "identity": identity,
        "market": market,
        "model": model,
        "runtime_decision": runtime_decision,
        "lifecycle_truth": lifecycle_truth,
        "path_truth": path_truth,
        "quality": quality,
        "provenance": {},
    }


def make_minimal_strategy_decision(
    plugin_id: str,
    row_id: str,
    action: StrategyAction | str = StrategyAction.SKIP,
) -> StrategyDecision:
    """
    Build a minimal but valid StrategyDecision for fixtures and tests.

    When action is a StrategyAction enum member its string value is used.
    ENTRY is a hypothetical offline action and implies no runtime permission.
    """
    action_value = action.value if isinstance(action, StrategyAction) else str(action)
    return {
        "schema_version": STRATEGY_DECISION_SCHEMA_VERSION,
        "plugin_id": plugin_id,
        "row_id": row_id,
        "action": action_value,
        "confidence": 0.0,
        "reason": "",
        "reject_reasons": [],
        "metrics": {},
        "provenance": {},
    }
