from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re

try:  # pragma: no cover - direct script execution path
    from tools.replay_analyzer import (
        DEFAULT_QUANT_DATA_DIR,
        DEFAULT_REPORT_DIR,
        build_time_filter,
        load_replay_events,
    )
except ModuleNotFoundError:  # pragma: no cover - `python tools/...` path
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from tools.replay_analyzer import (
        DEFAULT_QUANT_DATA_DIR,
        DEFAULT_REPORT_DIR,
        build_time_filter,
        load_replay_events,
    )


ACTIVE_MODEL_PHASES = {"ACTIVE_INVENTORY_TRADING", "PROFIT_MANAGEMENT"}
TERMINAL_OR_OBSERVE_ONLY_PHASES = {"OPENING_SCAN", "FINAL_DERISK", "CLOSED_OR_UNSAFE", "UNKNOWN"}
DEFAULT_MAX_BOOK_AGE_MS = 3_000.0
DEFAULT_MAX_SIDE_SPREAD = 0.10
MODEL_REQUIRED_FIELD_GROUPS = {
    "underlying_price": (
        "current_price",
        "underlying_price",
        "oracle_price",
        "index_price",
        "spot_price",
        "asset_price",
        "mark_price",
        "last_price",
        "binance_price",
        "reference_price",
    ),
    "target_price": (
        "price_to_beat",
        "target_price",
        "ptb_price",
        "strike",
        "strike_price",
        "event_boundary_price",
        "boundary_price",
        "price_target",
        "market_strike",
    ),
    "seconds_remaining": ("seconds_remaining", "seconds_until_close", "time_remaining"),
    "market_price": ("market_price", "yes_ask", "no_ask", "ask_price"),
    "spread": ("spread", "spread_normalized", "yes_spread", "no_spread"),
    "liquidity": ("liquidity", "liquidity_usd", "liquidity_state", "depth_ready"),
    "token_pair_identity": ("condition_id", "yes_token_id", "no_token_id"),
}
PRICE_SOURCE_ALIASES = {
    "underlying_price": (
        "underlying_price",
        "current_price",
        "btc_price",
        "eth_price",
        "index_price",
        "oracle_price",
        "price",
        "underlying",
        "spot_price",
        "asset_price",
        "mark_price",
        "last_price",
        "binance_price",
        "reference_price",
    ),
    "target_price": (
        "target_price",
        "price_to_beat",
        "strike",
        "threshold",
        "event_target",
        "ptb",
        "ptb_price",
        "strike_price",
        "event_boundary_price",
        "boundary_price",
        "price_target",
        "market_strike",
    ),
}
DIRECT_PRICE_FIELDS = {
    "underlying_price": "underlying_price",
    "target_price": "target_price",
}
TITLE_OR_SLUG_FIELDS = (
    "market_slug",
    "slug",
    "market_title",
    "title",
    "question",
    "name",
    "event_title",
    "description",
)
RISK_OBSERVABILITY_FIELDS = (
    "risk_state",
    "risk_decision",
    "risk_mode",
    "risk_block_reason",
    "available_risk_budget",
    "remaining_risk_budget",
    "risk_budget_used",
    "current_exposure",
    "target_exposure",
    "reconciliation_state",
)
PACKET_SCHEMA_FIELDS: tuple[dict[str, Any], ...] = (
    {
        "field": "run_id",
        "requirement": "required",
        "purpose": "replay isolation",
        "producer_source": "quant event envelope",
        "aliases": ("run_id",),
        "future_patch_target": "keep replay loader preserving run_id",
    },
    {
        "field": "packet_schema_version",
        "requirement": "required_observability",
        "purpose": "packet schema versioning for offline replay compatibility",
        "producer_source": "admission packet observability enrichment",
        "aliases": ("packet_schema_version",),
        "future_patch_target": "emit event_driven_admission_packet_v1 on enriched executable-liquidity packets",
    },
    {
        "field": "event_ts",
        "requirement": "required",
        "purpose": "event freshness and lifecycle timing",
        "producer_source": "orderbook event envelope",
        "aliases": ("timestamp_utc", "event_ts", "book_event_ts"),
        "future_patch_target": "preserve event timestamp on admission packets",
    },
    {
        "field": "condition_id",
        "requirement": "required",
        "purpose": "market identity",
        "producer_source": "Gamma market discovery / market metadata",
        "aliases": ("condition_id", "conditionId", "market_condition_id", "clob_condition_id"),
        "future_patch_target": "carry cached condition_id into executable-liquidity packet",
    },
    {
        "field": "market_slug",
        "requirement": "required",
        "purpose": "human-readable market identity and same-market joins",
        "producer_source": "Gamma market discovery / market metadata",
        "aliases": ("market_slug", "slug", "marketSlug", "market_id", "source_market_id", "market_key"),
        "future_patch_target": "carry market_slug or stable market_key into executable-liquidity packet",
    },
    {
        "field": "yes_token_id",
        "requirement": "required",
        "purpose": "YES book identity",
        "producer_source": "Gamma token discovery / cached token metadata",
        "aliases": ("yes_token_id", "yesTokenId"),
        "future_patch_target": "carry YES token id from cached market token metadata",
    },
    {
        "field": "no_token_id",
        "requirement": "required",
        "purpose": "NO book identity",
        "producer_source": "Gamma token discovery / cached token metadata",
        "aliases": ("no_token_id", "noTokenId"),
        "future_patch_target": "carry NO token id from cached market token metadata",
    },
    {
        "field": "underlying_price",
        "requirement": "required",
        "purpose": "probability model input",
        "producer_source": "BTC/ETH price feed or oracle/PTB context",
        "coverage_group": "underlying_price",
        "aliases": MODEL_REQUIRED_FIELD_GROUPS["underlying_price"],
        "future_patch_target": "join or serialize current underlying price on executable-liquidity packet",
    },
    {
        "field": "target_price",
        "requirement": "required",
        "purpose": "probability model boundary input",
        "producer_source": "market metadata / Gamma market boundary / PTB tracker",
        "coverage_group": "target_price",
        "aliases": MODEL_REQUIRED_FIELD_GROUPS["target_price"],
        "future_patch_target": "join or serialize price_to_beat/strike boundary on executable-liquidity packet",
    },
    {
        "field": "seconds_remaining",
        "requirement": "required",
        "purpose": "probability model and lifecycle gate timing",
        "producer_source": "lifecycle engine / market clock",
        "coverage_group": "seconds_remaining",
        "aliases": MODEL_REQUIRED_FIELD_GROUPS["seconds_remaining"],
        "future_patch_target": "preserve market-clock seconds remaining at book-event time",
    },
    {
        "field": "lifecycle_phase",
        "requirement": "required",
        "purpose": "admission window and cutoff safety",
        "producer_source": "lifecycle engine",
        "aliases": ("lifecycle_phase", "model_activation_lifecycle_phase"),
        "future_patch_target": "preserve lifecycle_phase at executable-liquidity event time",
    },
    {
        "field": "yes_no_bid_ask",
        "requirement": "required",
        "purpose": "orderbook completeness and market price input",
        "producer_source": "orderbook event",
        "aliases": ("yes_bid", "yes_ask", "no_bid", "no_ask", "yes_best_bid", "yes_best_ask", "no_best_bid", "no_best_ask"),
        "future_patch_target": "keep compact top-of-book YES/NO fields only",
    },
    {
        "field": "book_freshness",
        "requirement": "required",
        "purpose": "stale-book protection",
        "producer_source": "orderbook event / cache freshness",
        "aliases": ("orderbook_age_ms", "yes_orderbook_age_ms", "no_orderbook_age_ms", "book_event_age_ms"),
        "future_patch_target": "preserve executable book age at packet creation",
    },
    {
        "field": "spread",
        "requirement": "required",
        "purpose": "EV after spread and executable edge protection",
        "producer_source": "derived from orderbook event",
        "coverage_group": "spread",
        "aliases": MODEL_REQUIRED_FIELD_GROUPS["spread"],
        "future_patch_target": "derive from compact YES/NO top-of-book or serialize normalized spread",
    },
    {
        "field": "liquidity",
        "requirement": "required",
        "purpose": "liquidity gate and EV feasibility context",
        "producer_source": "orderbook event / liquidity classifier",
        "coverage_group": "liquidity",
        "aliases": MODEL_REQUIRED_FIELD_GROUPS["liquidity"],
        "future_patch_target": "serialize compact liquidity/depth state on packet",
    },
    {
        "field": "risk_context",
        "requirement": "optional_for_model_required_for_risk_observability",
        "purpose": "risk gate observability, not trade approval",
        "producer_source": "risk state snapshot",
        "aliases": RISK_OBSERVABILITY_FIELDS,
        "future_patch_target": "join latest risk-state snapshot offline or emit compact risk context later",
    },
    {
        "field": "side",
        "requirement": "optional_until_side_selection",
        "purpose": "side-specific fair value and EV attribution",
        "producer_source": "model side selection / candidate context",
        "aliases": ("side", "asset_side", "outcome", "best_side", "token_side"),
        "future_patch_target": "carry selected side once model/fair-value path chooses YES or NO",
    },
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _payload(event: dict[str, Any]) -> dict[str, Any]:
    raw_payload = event.get("payload")
    if isinstance(raw_payload, dict):
        payload = dict(raw_payload)
        for key in ("run_id", "timestamp_utc", "event_type", "mode", "_category"):
            if key in event and key not in payload:
                payload[key] = event[key]
        return payload
    return dict(event)


def _producer(event: dict[str, Any]) -> str:
    return str(event.get("_category") or event.get("event_category") or event.get("producer") or "unknown")


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        normalized = value.strip()
        return bool(normalized) and normalized.upper() not in {"UNKNOWN", "--", "NONE", "NULL"}
    if isinstance(value, (list, tuple, dict, set)):
        return bool(value)
    return True


def _bool_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "ok", "ready", "visible", "called"}
    return False


def _float_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _positive_float(value: Any) -> float | None:
    number = _float_or_none(value)
    if number is None or number <= 0:
        return None
    return number


def _top(counter: Counter[str], limit: int = 8) -> dict[str, int]:
    return {key: count for key, count in counter.most_common(limit)}


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _market_key(payload: dict[str, Any]) -> str:
    for key in ("condition_id", "market_slug", "market_id", "source_market_id", "market_key"):
        value = payload.get(key)
        if _present(value):
            return f"{key}:{str(value).strip()}"
    yes_token = payload.get("yes_token_id")
    no_token = payload.get("no_token_id")
    if _present(yes_token) and _present(no_token):
        return f"token_pair:{yes_token}|{no_token}"
    return ""


def _run_key(payload: dict[str, Any]) -> str:
    return str(payload.get("run_id") or "").strip()


def _source_event_allowed(event: dict[str, Any], payload: dict[str, Any]) -> bool:
    producer = _producer(event)
    if producer == "market_snapshots":
        return True
    return str(payload.get("executable_liquidity_event_role") or "").strip() == "passive_telemetry_only"


def _is_executable_book_event(payload: dict[str, Any]) -> bool:
    yes_bid = _positive_float(payload.get("yes_bid") or payload.get("yes_best_bid"))
    yes_ask = _positive_float(payload.get("yes_ask") or payload.get("yes_best_ask"))
    no_bid = _positive_float(payload.get("no_bid") or payload.get("no_best_bid"))
    no_ask = _positive_float(payload.get("no_ask") or payload.get("no_best_ask"))
    return yes_bid is not None and yes_ask is not None and no_bid is not None and no_ask is not None


def _token_pair_lineage_ok(payload: dict[str, Any]) -> bool:
    if payload.get("orderbook_lineage_match") is False or payload.get("token_pair_lineage_match") is False:
        return False
    has_pair = _present(payload.get("yes_token_id")) and _present(payload.get("no_token_id"))
    has_market_key = any(
        _present(payload.get(key))
        for key in ("condition_id", "market_slug", "market_id", "source_market_id", "market_key")
    )
    return bool(has_pair and has_market_key)


def _lifecycle_phase(payload: dict[str, Any]) -> str:
    raw_phase = payload.get("lifecycle_phase") or payload.get("model_activation_lifecycle_phase")
    if _present(raw_phase):
        return str(raw_phase).strip().upper()
    seconds_remaining = _float_or_none(payload.get("seconds_remaining") or payload.get("seconds_until_close"))
    if seconds_remaining is None:
        return "UNKNOWN"
    elapsed = max(0.0, 300.0 - seconds_remaining)
    if elapsed < 35:
        return "OPENING_SCAN"
    if elapsed < 240:
        return "ACTIVE_INVENTORY_TRADING"
    if elapsed < 270:
        return "PROFIT_MANAGEMENT"
    if elapsed < 300:
        return "FINAL_DERISK"
    return "CLOSED_OR_UNSAFE"


def _book_age_ms(payload: dict[str, Any]) -> float | None:
    ages = [
        _float_or_none(payload.get("yes_orderbook_age_ms")),
        _float_or_none(payload.get("no_orderbook_age_ms")),
        _float_or_none(payload.get("orderbook_age_ms")),
        _float_or_none(payload.get("book_event_age_ms")),
        _float_or_none(payload.get("executable_book_last_seen_age_ms")),
    ]
    present_ages = [age for age in ages if age is not None]
    if not present_ages:
        return None
    return max(present_ages)


def _freshness_ok(payload: dict[str, Any], max_age_ms: float) -> tuple[bool, str]:
    age = _book_age_ms(payload)
    if age is None:
        return False, "freshness_missing"
    if age > max_age_ms:
        return False, "stale_executable_book"
    return True, "fresh"


def _spread_ok(payload: dict[str, Any], max_side_spread: float) -> tuple[bool, str]:
    spreads: list[float] = []
    yes_bid = _positive_float(payload.get("yes_bid") or payload.get("yes_best_bid"))
    yes_ask = _positive_float(payload.get("yes_ask") or payload.get("yes_best_ask"))
    no_bid = _positive_float(payload.get("no_bid") or payload.get("no_best_bid"))
    no_ask = _positive_float(payload.get("no_ask") or payload.get("no_best_ask"))
    if yes_bid is not None and yes_ask is not None:
        spreads.append(max(0.0, yes_ask - yes_bid))
    if no_bid is not None and no_ask is not None:
        spreads.append(max(0.0, no_ask - no_bid))
    explicit_spread = _float_or_none(payload.get("spread") or payload.get("spread_normalized"))
    if explicit_spread is not None:
        spreads.append(abs(explicit_spread))
    if not spreads:
        return False, "spread_missing_or_invalid"
    if max(spreads) > max_side_spread:
        return False, "spread_too_wide"
    return True, "spread_ok"


def _risk_gate_observable(payload: dict[str, Any]) -> bool:
    return any(_present(payload.get(key)) for key in RISK_OBSERVABILITY_FIELDS)


def _field_group_alias_hits(payload: dict[str, Any], group: str) -> list[str]:
    keys = MODEL_REQUIRED_FIELD_GROUPS[group]
    if group == "token_pair_identity":
        required = ("condition_id", "yes_token_id", "no_token_id")
        if all(_present(payload.get(key)) for key in required):
            return list(required)
        return [key for key in required if _present(payload.get(key))]
    if group == "spread":
        hits = [key for key in keys if _present(payload.get(key))]
        yes_bid = _positive_float(payload.get("yes_bid") or payload.get("yes_best_bid"))
        yes_ask = _positive_float(payload.get("yes_ask") or payload.get("yes_best_ask"))
        no_bid = _positive_float(payload.get("no_bid") or payload.get("no_best_bid"))
        no_ask = _positive_float(payload.get("no_ask") or payload.get("no_best_ask"))
        if yes_bid is not None and yes_ask is not None:
            hits.append("derived_yes_bid_ask_spread")
        if no_bid is not None and no_ask is not None:
            hits.append("derived_no_bid_ask_spread")
        return hits
    return [key for key in keys if _present(payload.get(key))]


def _price_source_alias_hits(payload: dict[str, Any], group: str) -> list[str]:
    return [key for key in PRICE_SOURCE_ALIASES[group] if _present(payload.get(key))]


def _title_or_slug_values(payload: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in TITLE_OR_SLUG_FIELDS:
        value = payload.get(key)
        if _present(value):
            values.append(str(value))
    return values


def _target_hint_from_title_or_slug(payload: dict[str, Any]) -> tuple[bool, bool]:
    values = _title_or_slug_values(payload)
    if not values:
        return False, False
    has_numeric = any(re.search(r"\b\d{4,}(?:\.\d+)?\b", value.replace(",", "")) for value in values)
    has_boundary_keyword = any(
        re.search(r"\b(strike|target|threshold|price to beat|above|below|over|under)\b", value, flags=re.IGNORECASE)
        for value in values
    )
    return has_numeric, bool(has_numeric and has_boundary_keyword)


def _field_group_available(payload: dict[str, Any], group: str) -> bool:
    if group == "token_pair_identity":
        return all(_present(payload.get(key)) for key in ("condition_id", "yes_token_id", "no_token_id"))
    return bool(_field_group_alias_hits(payload, group))


def _missing_model_required_groups(payload: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for group in MODEL_REQUIRED_FIELD_GROUPS:
        if not _field_group_available(payload, group):
            missing.append(group)
    return missing


def _available_field_groups(payload: dict[str, Any]) -> list[str]:
    return [group for group in MODEL_REQUIRED_FIELD_GROUPS if _field_group_available(payload, group)]


def _missing_reason_for_group(
    *,
    group: str,
    market_key: str,
    market_group_sources: dict[str, dict[str, Counter[str]]],
    global_group_seen: Counter[str],
) -> str:
    if market_key and market_key in market_group_sources and market_group_sources[market_key].get(group):
        producer = market_group_sources[market_key][group].most_common(1)[0][0]
        return f"joinable_same_market_{producer}"
    if global_group_seen.get(group, 0) > 0:
        return "available_elsewhere_not_joinable_same_market"
    return "not_emitted_in_loaded_replay"


def _packet_field_alias_hits(payload: dict[str, Any], schema_field: dict[str, Any]) -> list[str]:
    coverage_group = schema_field.get("coverage_group")
    if coverage_group:
        return _field_group_alias_hits(payload, str(coverage_group))
    field = str(schema_field["field"])
    if field == "risk_context":
        return [key for key in RISK_OBSERVABILITY_FIELDS if _present(payload.get(key))]
    if field == "yes_no_bid_ask":
        required = ("yes_bid", "yes_ask", "no_bid", "no_ask")
        if all(_positive_float(payload.get(key)) is not None for key in required):
            return list(required)
        compact_aliases = (
            ("yes_best_bid", "yes_best_ask", "no_best_bid", "no_best_ask"),
        )
        for aliases in compact_aliases:
            if all(_positive_float(payload.get(key)) is not None for key in aliases):
                return list(aliases)
        return [key for key in schema_field["aliases"] if _present(payload.get(key))]
    return [key for key in schema_field["aliases"] if _present(payload.get(key))]


def _packet_field_available(payload: dict[str, Any], schema_field: dict[str, Any]) -> bool:
    field = str(schema_field["field"])
    if field == "yes_no_bid_ask":
        return _is_executable_book_event(payload)
    return bool(_packet_field_alias_hits(payload, schema_field))


def _packet_missing_reason(
    *,
    schema_field: dict[str, Any],
    payload: dict[str, Any],
    market_group_sources: dict[str, dict[str, Counter[str]]],
    global_group_seen: Counter[str],
) -> str:
    field = str(schema_field["field"])
    coverage_group = schema_field.get("coverage_group")
    if coverage_group:
        return _missing_reason_for_group(
            group=str(coverage_group),
            market_key=_market_key(payload),
            market_group_sources=market_group_sources,
            global_group_seen=global_group_seen,
        )
    if field == "risk_context":
        return "risk_context_not_serialized_on_executable_book_events"
    return "not_emitted_on_executable_book_event"


def _build_packet_schema_gap(
    *,
    packet_event_count: int,
    packet_field_available: Counter[str],
    packet_field_missing: Counter[str],
    packet_alias_hits: dict[str, Counter[str]],
    packet_missing_reasons: dict[str, Counter[str]],
) -> dict[str, Any]:
    fields: list[dict[str, Any]] = []
    missing_required_fields: list[str] = []
    required_fields: list[str] = []
    optional_fields: list[str] = []
    field_source_map: dict[str, str] = {}
    for schema_field in PACKET_SCHEMA_FIELDS:
        field = str(schema_field["field"])
        requirement = str(schema_field["requirement"])
        if requirement == "required":
            required_fields.append(field)
            if packet_field_missing.get(field, 0) > 0:
                missing_required_fields.append(field)
        else:
            optional_fields.append(field)
        field_source_map[field] = str(schema_field["producer_source"])
        fields.append(
            {
                "field": field,
                "requirement": requirement,
                "purpose": schema_field["purpose"],
                "producer_source": schema_field["producer_source"],
                "aliases_audited": list(schema_field["aliases"]),
                "current_coverage_count": packet_field_available.get(field, 0),
                "current_missing_count": packet_field_missing.get(field, 0),
                "current_coverage_rate": _rate(packet_field_available.get(field, 0), packet_event_count),
                "alias_hits": dict(packet_alias_hits[field]),
                "missing_reason_counts": dict(packet_missing_reasons[field]),
                "future_patch_target": schema_field["future_patch_target"],
            }
        )
    if missing_required_fields:
        conclusion = "packet_schema_incomplete_for_offline_probability_fair_value_ev_simulation"
    else:
        conclusion = "packet_schema_has_required_inputs_for_offline_model_probe_simulation"
    return {
        "packet_schema_version": "event_driven_admission_packet_schema_v1",
        "coverage_denominator": "model_eligibility_would_be_reached_count",
        "packet_event_count": packet_event_count,
        "required_fields": required_fields,
        "optional_fields": optional_fields,
        "missing_required_fields": missing_required_fields,
        "field_source_map": field_source_map,
        "fields": fields,
        "audit_conclusion": conclusion,
        "recommended_next_patch_target": _recommended_packet_patch(missing_required_fields),
    }


def _recommended_packet_patch(missing_required_fields: list[str]) -> str:
    if "underlying_price" in missing_required_fields or "target_price" in missing_required_fields:
        return "Add offline packet source mapping for underlying_price and target_price before EV simulation."
    if missing_required_fields:
        return f"Add offline packet source mapping for {missing_required_fields[0]}."
    return "Required packet fields are covered; next audit optional risk_context and side continuity."


def _build_price_source_mapping(
    *,
    packet_event_count: int,
    price_loaded_alias_counts: dict[str, Counter[str]],
    price_loaded_alias_by_producer: dict[str, dict[str, Counter[str]]],
    price_packet_alias_counts: dict[str, Counter[str]],
    price_joinability_counts: dict[str, Counter[str]],
    price_join_sources: dict[str, Counter[str]],
    slug_title_present_count: int,
    slug_title_numeric_candidate_count: int,
    slug_title_reliable_target_candidate_count: int,
) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for group in ("underlying_price", "target_price"):
        fields[group] = {
            "aliases_audited": list(PRICE_SOURCE_ALIASES[group]),
            "direct_field": DIRECT_PRICE_FIELDS[group],
            "loaded_event_alias_counts": dict(price_loaded_alias_counts[group]),
            "loaded_event_alias_by_producer": {
                alias: dict(counter) for alias, counter in price_loaded_alias_by_producer[group].items()
            },
            "model_eligible_packet_alias_counts": dict(price_packet_alias_counts[group]),
            "joinability_classification_counts": dict(price_joinability_counts[group]),
            "joinability_rates": {
                key: _rate(count, packet_event_count) for key, count in price_joinability_counts[group].items()
            },
            "same_market_join_sources": dict(price_join_sources[group]),
            "recommended_runtime_observability_field": (
                "underlying_price or current_price from BTC/ETH price feed"
                if group == "underlying_price"
                else "target_price or price_to_beat from market metadata/PTB tracker"
            ),
        }
    offline_join_possible = any(
        price_joinability_counts[group].get("joinable_from_metadata", 0) > 0 for group in ("underlying_price", "target_price")
    )
    return {
        "schema_version": "price_source_mapping_v1",
        "coverage_denominator": "model_eligibility_would_be_reached_count",
        "model_eligible_packet_count": packet_event_count,
        "fields": fields,
        "target_slug_title_inference": {
            "title_or_slug_present_count": slug_title_present_count,
            "numeric_candidate_count": slug_title_numeric_candidate_count,
            "reliable_target_candidate_count": slug_title_reliable_target_candidate_count,
            "classification": (
                "explicit_boundary_candidate_present"
                if slug_title_reliable_target_candidate_count
                else "slug_or_title_not_reliable_for_target_price"
            ),
            "note": "Slug/title numeric text is not promoted to target_price unless a boundary keyword is visible.",
        },
        "offline_join_possible": offline_join_possible,
        "next_patch_recommendation": _recommended_price_source_patch(price_joinability_counts),
    }


def _recommended_price_source_patch(price_joinability_counts: dict[str, Counter[str]]) -> str:
    missing = [
        group
        for group in ("underlying_price", "target_price")
        if price_joinability_counts[group].get("not_available_in_replay", 0) > 0
        and price_joinability_counts[group].get("joinable_from_metadata", 0) == 0
    ]
    if "underlying_price" in missing and "target_price" in missing:
        return "Emit or offline-join underlying_price/current_price and target_price/price_to_beat into admission packet evidence."
    if "underlying_price" in missing:
        return "Emit or offline-join underlying_price/current_price from the BTC/ETH price feed into packet evidence."
    if "target_price" in missing:
        return "Emit or offline-join target_price/price_to_beat from Gamma/PTB metadata into packet evidence."
    return "Use available same-market price sources for offline reconstruction before adding runtime fields."


def _packet_price_fields_present(payload: dict[str, Any]) -> bool:
    return _field_group_available(payload, "underlying_price") and _field_group_available(payload, "target_price")


def _packet_bool_state(payload: dict[str, Any], key: str, *, legacy_label: str) -> str:
    if key not in payload:
        return legacy_label
    return f"{key}_{'true' if _bool_true(payload.get(key)) else 'false'}"


def _price_enrichment_source(payload: dict[str, Any]) -> str:
    source = str(payload.get("price_enrichment_source") or "").strip()
    if source:
        return source
    underlying_source = str(payload.get("underlying_price_source") or "").strip()
    target_source = str(payload.get("target_source") or payload.get("event_boundary_source") or "").strip()
    if underlying_source and target_source:
        return f"{underlying_source}+{target_source}"
    if underlying_source:
        return underlying_source
    if target_source:
        return target_source
    return "legacy_no_enrichment_source"


def _price_enrichment_drop_reason(payload: dict[str, Any]) -> str:
    if _packet_price_fields_present(payload):
        return "price_fields_present"
    reason = str(payload.get("enrichment_drop_reason") or "").strip()
    if reason:
        return reason
    if "packet_schema_version" not in payload and "price_enrichment_stage" not in payload:
        return "legacy_no_packet_price_diagnostics"
    if _bool_true(payload.get("ptb_context_available")):
        return "ptb_context_available_but_price_fields_missing"
    return "price_fields_missing_without_drop_reason"


def _producer_price_diag_key(producer: str, payload: dict[str, Any]) -> str:
    if _packet_price_fields_present(payload):
        return f"{producer}:price_fields_present"
    return f"{producer}:{_price_enrichment_drop_reason(payload)}"


def _build_packet_price_enrichment_diagnostics(
    *,
    executable_event_count: int,
    model_eligibility_would_be_reached_count: int,
    executable_price_fields_present_count: int,
    eligible_price_fields_present_count: int,
    packets_with_ptb_context: int,
    packets_without_ptb_context: int,
    packets_before_ptb_ready: int,
    packets_after_ptb_ready: int,
    packets_missing_propagation: int,
    packets_missing_source_fields: int,
    packets_missing_due_to_skip_path: int,
    packets_missing_due_to_snapshot_only_path: int,
    enrichment_source_counts: Counter[str],
    enrichment_drop_reason_counts: Counter[str],
    ptb_context_availability_counts: Counter[str],
    oracle_context_availability_counts: Counter[str],
    target_context_availability_counts: Counter[str],
    packet_schema_price_field_counts: Counter[str],
    producer_price_enrichment_counts: Counter[str],
) -> dict[str, Any]:
    missing_only_reasons = Counter(
        {
            reason: count
            for reason, count in enrichment_drop_reason_counts.items()
            if reason != "price_fields_present"
        }
    )
    dominant_reason = missing_only_reasons.most_common(1)[0][0] if missing_only_reasons else "NONE"
    return {
        "schema_version": "packet_price_enrichment_diagnostics_v1",
        "coverage_denominator": "model_eligibility_would_be_reached_count",
        "executable_liquidity_event_count": executable_event_count,
        "model_eligible_packet_count": model_eligibility_would_be_reached_count,
        "executable_packets_with_price_fields": executable_price_fields_present_count,
        "model_eligible_packets_with_price_fields": eligible_price_fields_present_count,
        "model_eligible_packets_without_price_fields": max(
            model_eligibility_would_be_reached_count - eligible_price_fields_present_count,
            0,
        ),
        "packets_with_ptb_context": packets_with_ptb_context,
        "packets_without_ptb_context": packets_without_ptb_context,
        "packets_before_ptb_ready": packets_before_ptb_ready,
        "packets_after_ptb_ready": packets_after_ptb_ready,
        "packets_missing_propagation": packets_missing_propagation,
        "packets_missing_source_fields": packets_missing_source_fields,
        "packets_missing_due_to_skip_path": packets_missing_due_to_skip_path,
        "packets_missing_due_to_snapshot_only_path": packets_missing_due_to_snapshot_only_path,
        "enrichment_source_counts": dict(enrichment_source_counts),
        "enrichment_drop_reason_counts": dict(enrichment_drop_reason_counts),
        "missing_only_enrichment_drop_reason_counts": dict(missing_only_reasons),
        "ptb_context_availability_counts": dict(ptb_context_availability_counts),
        "oracle_context_availability_counts": dict(oracle_context_availability_counts),
        "target_context_availability_counts": dict(target_context_availability_counts),
        "packet_schema_price_field_counts": dict(packet_schema_price_field_counts),
        "producer_price_enrichment_counts": dict(producer_price_enrichment_counts),
        "dominant_propagation_drop_reason": dominant_reason,
        "interpretation": _packet_price_enrichment_interpretation(dominant_reason),
    }


def _packet_price_enrichment_interpretation(dominant_reason: str) -> str:
    if dominant_reason == "NONE":
        return "No packet price enrichment drops detected for model-eligible packets."
    if dominant_reason == "legacy_no_packet_price_diagnostics":
        return "Most missing packet price fields come from replay events emitted before price-enrichment diagnostics existed."
    if dominant_reason == "ptb_context_available_but_price_fields_missing":
        return "PTB context was observable but price fields were not propagated into the executable packet."
    if dominant_reason in {"oracle_and_target_missing", "oracle_price_missing", "target_price_missing", "ptb_context_missing"}:
        return "The packet producer lacked usable price-source fields at packet creation time."
    return "Packet price enrichment loss is mixed or unresolved; inspect producer_price_enrichment_counts."


def _build_ev_input_coverage(
    *,
    executable_event_count: int,
    model_eligibility_would_be_reached_count: int,
    executable_group_available: Counter[str],
    executable_group_missing: Counter[str],
    eligible_group_available: Counter[str],
    eligible_group_missing: Counter[str],
    executable_alias_hits: dict[str, Counter[str]],
    eligible_alias_hits: dict[str, Counter[str]],
    eligible_missing_reason_counts: dict[str, Counter[str]],
    same_market_join_sources_by_group: dict[str, Counter[str]],
    risk_observable_count: int,
) -> dict[str, Any]:
    field_group_coverage: dict[str, dict[str, Any]] = {}
    minimum_additional_fields: list[str] = []
    for group, aliases in MODEL_REQUIRED_FIELD_GROUPS.items():
        eligible_missing = eligible_group_missing.get(group, 0)
        joinable_count = sum(same_market_join_sources_by_group[group].values())
        if eligible_missing > 0 and joinable_count == 0:
            minimum_additional_fields.append(group)
        field_group_coverage[group] = {
            "aliases_audited": list(aliases),
            "executable_available_count": executable_group_available.get(group, 0),
            "executable_missing_count": executable_group_missing.get(group, 0),
            "executable_coverage_rate": _rate(executable_group_available.get(group, 0), executable_event_count),
            "model_eligible_available_count": eligible_group_available.get(group, 0),
            "model_eligible_missing_count": eligible_missing,
            "model_eligible_coverage_rate": _rate(
                eligible_group_available.get(group, 0),
                model_eligibility_would_be_reached_count,
            ),
            "executable_alias_hits": dict(executable_alias_hits[group]),
            "model_eligible_alias_hits": dict(eligible_alias_hits[group]),
            "model_eligible_missing_reason_counts": dict(eligible_missing_reason_counts[group]),
            "same_market_join_sources_for_missing": dict(same_market_join_sources_by_group[group]),
        }
    risk_rate = _rate(risk_observable_count, model_eligibility_would_be_reached_count)
    if risk_observable_count:
        risk_conclusion = "risk_fields_available_on_some_simulated_model_eligible_events"
    else:
        risk_conclusion = "risk_fields_not_serialized_on_executable_book_events"
    return {
        "model_eligible_event_count": model_eligibility_would_be_reached_count,
        "field_group_coverage": field_group_coverage,
        "underlying_price_available_count": eligible_group_available.get("underlying_price", 0),
        "target_price_available_count": eligible_group_available.get("target_price", 0),
        "underlying_price_missing_count": eligible_group_missing.get("underlying_price", 0),
        "target_price_missing_count": eligible_group_missing.get("target_price", 0),
        "minimum_additional_offline_fields_needed": sorted(minimum_additional_fields),
        "risk_gate_offline_estimation": {
            "risk_gate_observable_count": risk_observable_count,
            "risk_gate_observable_rate": risk_rate,
            "can_estimate_without_runtime_risk_decision_changes": risk_observable_count > 0,
            "reason": risk_conclusion,
            "fields_audited": list(RISK_OBSERVABILITY_FIELDS),
        },
        "recommended_next_patch_target": _recommended_ev_input_patch(field_group_coverage, minimum_additional_fields),
    }


def _recommended_ev_input_patch(field_group_coverage: dict[str, dict[str, Any]], minimum_additional_fields: list[str]) -> str:
    if "underlying_price" in minimum_additional_fields or "target_price" in minimum_additional_fields:
        missing = ", ".join(field for field in ("underlying_price", "target_price") if field in minimum_additional_fields)
        return f"Add offline source/join evidence for {missing} before simulating probability or EV output."
    for group, coverage in field_group_coverage.items():
        if coverage["model_eligible_missing_count"] and coverage["same_market_join_sources_for_missing"]:
            return f"Join {group} from same-market replay sources before adding runtime fields."
    if minimum_additional_fields:
        return f"Add offline source/join evidence for {minimum_additional_fields[0]}."
    return "EV input coverage is sufficient for the simulated model-eligibility stage; next audit risk observability."


def build_event_driven_admission_simulation_report(
    *,
    date: str,
    base_dir: str | Path = DEFAULT_QUANT_DATA_DIR,
    since: str | None = None,
    until: str | None = None,
    run_id: str | None = None,
    max_book_age_ms: float = DEFAULT_MAX_BOOK_AGE_MS,
    max_side_spread: float = DEFAULT_MAX_SIDE_SPREAD,
) -> dict[str, Any]:
    time_filter = build_time_filter(date_from=date, date_to=date, since=since, until=until, run_id=run_id)
    events, bad_json_lines = load_replay_events(
        base_dir=base_dir,
        date_from=date,
        date_to=date,
        since_utc=time_filter.get("since_utc"),
        until_utc=time_filter.get("until_utc"),
        run_id=run_id,
    )

    source_event_counts_by_producer: Counter[str] = Counter()
    lifecycle_split: Counter[str] = Counter()
    fail_counts_by_gate: Counter[str] = Counter()
    fail_reasons: Counter[str] = Counter()
    phase_fail_counts: Counter[str] = Counter()
    model_required_missing: Counter[str] = Counter()
    global_group_seen: Counter[str] = Counter()
    market_group_sources: dict[str, dict[str, Counter[str]]] = {}
    executable_group_available: Counter[str] = Counter()
    executable_group_missing: Counter[str] = Counter()
    eligible_group_available: Counter[str] = Counter()
    eligible_group_missing: Counter[str] = Counter()
    executable_alias_hits: dict[str, Counter[str]] = {group: Counter() for group in MODEL_REQUIRED_FIELD_GROUPS}
    eligible_alias_hits: dict[str, Counter[str]] = {group: Counter() for group in MODEL_REQUIRED_FIELD_GROUPS}
    eligible_missing_reason_counts: dict[str, Counter[str]] = {group: Counter() for group in MODEL_REQUIRED_FIELD_GROUPS}
    same_market_join_sources_by_group: dict[str, Counter[str]] = {group: Counter() for group in MODEL_REQUIRED_FIELD_GROUPS}
    packet_field_available: Counter[str] = Counter()
    packet_field_missing: Counter[str] = Counter()
    packet_alias_hits: dict[str, Counter[str]] = {str(field["field"]): Counter() for field in PACKET_SCHEMA_FIELDS}
    packet_missing_reasons: dict[str, Counter[str]] = {str(field["field"]): Counter() for field in PACKET_SCHEMA_FIELDS}
    price_loaded_alias_counts: dict[str, Counter[str]] = {group: Counter() for group in PRICE_SOURCE_ALIASES}
    price_loaded_alias_by_producer: dict[str, dict[str, Counter[str]]] = {
        group: {alias: Counter() for alias in aliases} for group, aliases in PRICE_SOURCE_ALIASES.items()
    }
    price_sources_by_market: dict[str, dict[str, Counter[str]]] = {}
    price_packet_alias_counts: dict[str, Counter[str]] = {group: Counter() for group in PRICE_SOURCE_ALIASES}
    price_joinability_counts: dict[str, Counter[str]] = {group: Counter() for group in PRICE_SOURCE_ALIASES}
    price_join_sources: dict[str, Counter[str]] = {group: Counter() for group in PRICE_SOURCE_ALIASES}
    slug_title_present_count = 0
    slug_title_numeric_candidate_count = 0
    slug_title_reliable_target_candidate_count = 0
    executable_price_fields_present_count = 0
    eligible_price_fields_present_count = 0
    packets_with_ptb_context = 0
    packets_without_ptb_context = 0
    packets_before_ptb_ready = 0
    packets_after_ptb_ready = 0
    packets_missing_propagation = 0
    packets_missing_source_fields = 0
    packets_missing_due_to_skip_path = 0
    packets_missing_due_to_snapshot_only_path = 0
    enrichment_source_counts: Counter[str] = Counter()
    enrichment_drop_reason_counts: Counter[str] = Counter()
    ptb_context_availability_counts: Counter[str] = Counter()
    oracle_context_availability_counts: Counter[str] = Counter()
    target_context_availability_counts: Counter[str] = Counter()
    packet_schema_price_field_counts: Counter[str] = Counter()
    producer_price_enrichment_counts: Counter[str] = Counter()
    risk_observable_count = 0
    executable_event_count = 0
    same_token_pair_count = 0
    model_eligibility_would_be_reached_count = 0
    observed_probability_model_called_count = 0

    for event in events:
        payload = _payload(event)
        producer = _producer(event)
        market_key = _market_key(payload)
        for group in _available_field_groups(payload):
            global_group_seen[group] += 1
            if market_key:
                market_group_sources.setdefault(market_key, {}).setdefault(group, Counter())[producer] += 1
        for group in PRICE_SOURCE_ALIASES:
            hits = _price_source_alias_hits(payload, group)
            if not hits:
                continue
            price_loaded_alias_counts[group].update(hits)
            for alias in hits:
                price_loaded_alias_by_producer[group][alias][producer] += 1
            if market_key:
                for alias in hits:
                    price_sources_by_market.setdefault(market_key, {}).setdefault(group, Counter())[f"{producer}:{alias}"] += 1

    for event in events:
        payload = _payload(event)
        if _bool_true(payload.get("probability_model_called")):
            observed_probability_model_called_count += 1
        if not _source_event_allowed(event, payload):
            continue
        source_event_counts_by_producer[_producer(event)] += 1
        if not _is_executable_book_event(payload):
            continue

        executable_event_count += 1
        if _packet_price_fields_present(payload):
            executable_price_fields_present_count += 1
        phase = _lifecycle_phase(payload)
        lifecycle_split[phase] += 1
        for group in MODEL_REQUIRED_FIELD_GROUPS:
            hits = _field_group_alias_hits(payload, group)
            if _field_group_available(payload, group):
                executable_group_available[group] += 1
                executable_alias_hits[group].update(hits)
            else:
                executable_group_missing[group] += 1

        if not _token_pair_lineage_ok(payload):
            fail_counts_by_gate["token_pair_lineage_ok"] += 1
            fail_reasons["missing_or_mismatched_token_pair_lineage"] += 1
            phase_fail_counts[f"{phase}:token_pair_lineage_ok"] += 1
            continue
        same_token_pair_count += 1

        if phase not in ACTIVE_MODEL_PHASES:
            fail_counts_by_gate["lifecycle_window_ok"] += 1
            fail_reasons[f"phase_{phase.lower()}"] += 1
            phase_fail_counts[f"{phase}:lifecycle_window_ok"] += 1
            continue

        fresh, freshness_reason = _freshness_ok(payload, max_book_age_ms)
        if not fresh:
            fail_counts_by_gate["freshness_ok"] += 1
            fail_reasons[freshness_reason] += 1
            phase_fail_counts[f"{phase}:freshness_ok"] += 1
            continue

        spread, spread_reason = _spread_ok(payload, max_side_spread)
        if not spread:
            fail_counts_by_gate["spread_ok"] += 1
            fail_reasons[spread_reason] += 1
            phase_fail_counts[f"{phase}:spread_ok"] += 1
            continue

        model_eligibility_would_be_reached_count += 1
        producer = _producer(event)
        has_price_fields = _packet_price_fields_present(payload)
        if has_price_fields:
            eligible_price_fields_present_count += 1
        if _bool_true(payload.get("ptb_context_available")):
            packets_with_ptb_context += 1
            packets_after_ptb_ready += 1
        else:
            packets_without_ptb_context += 1
            if "ptb_context_available" in payload:
                packets_before_ptb_ready += 1
        if not has_price_fields and _bool_true(payload.get("ptb_context_available")):
            packets_missing_propagation += 1
        if not has_price_fields and not _bool_true(payload.get("ptb_context_available")):
            packets_missing_source_fields += 1
        if not has_price_fields and _bool_true(payload.get("skipped")):
            packets_missing_due_to_skip_path += 1
        if not has_price_fields and producer == "market_snapshots":
            packets_missing_due_to_snapshot_only_path += 1
        enrichment_source_counts[_price_enrichment_source(payload)] += 1
        enrichment_drop_reason_counts[_price_enrichment_drop_reason(payload)] += 1
        ptb_context_availability_counts[_packet_bool_state(payload, "ptb_context_available", legacy_label="legacy_no_ptb_context_field")] += 1
        oracle_context_availability_counts[_packet_bool_state(payload, "oracle_price_available", legacy_label="legacy_no_oracle_price_field")] += 1
        target_context_availability_counts[_packet_bool_state(payload, "target_price_available", legacy_label="legacy_no_target_price_field")] += 1
        packet_schema_price_field_counts[
            _packet_bool_state(payload, "packet_schema_price_fields_present", legacy_label="legacy_no_packet_schema_price_field")
        ] += 1
        producer_price_enrichment_counts[_producer_price_diag_key(producer, payload)] += 1
        has_slug_title = bool(_title_or_slug_values(payload))
        has_numeric_target, has_reliable_target = _target_hint_from_title_or_slug(payload)
        if has_slug_title:
            slug_title_present_count += 1
        if has_numeric_target:
            slug_title_numeric_candidate_count += 1
        if has_reliable_target:
            slug_title_reliable_target_candidate_count += 1
        if _risk_gate_observable(payload):
            risk_observable_count += 1
        for missing_group in _missing_model_required_groups(payload):
            model_required_missing[missing_group] += 1
        for group in MODEL_REQUIRED_FIELD_GROUPS:
            hits = _field_group_alias_hits(payload, group)
            if _field_group_available(payload, group):
                eligible_group_available[group] += 1
                eligible_alias_hits[group].update(hits)
            else:
                eligible_group_missing[group] += 1
                reason = _missing_reason_for_group(
                    group=group,
                    market_key=_market_key(payload),
                    market_group_sources=market_group_sources,
                    global_group_seen=global_group_seen,
                )
                eligible_missing_reason_counts[group][reason] += 1
                if reason.startswith("joinable_same_market_"):
                    same_market_join_sources_by_group[group][reason.removeprefix("joinable_same_market_")] += 1
        for schema_field in PACKET_SCHEMA_FIELDS:
            field_name = str(schema_field["field"])
            hits = _packet_field_alias_hits(payload, schema_field)
            if _packet_field_available(payload, schema_field):
                packet_field_available[field_name] += 1
                packet_alias_hits[field_name].update(hits)
            else:
                packet_field_missing[field_name] += 1
                packet_missing_reasons[field_name][
                    _packet_missing_reason(
                        schema_field=schema_field,
                        payload=payload,
                        market_group_sources=market_group_sources,
                        global_group_seen=global_group_seen,
                    )
                ] += 1
        for group in PRICE_SOURCE_ALIASES:
            hits = _price_source_alias_hits(payload, group)
            price_packet_alias_counts[group].update(hits)
            direct = DIRECT_PRICE_FIELDS[group]
            if _present(payload.get(direct)):
                price_joinability_counts[group]["directly_present"] += 1
            elif hits:
                price_joinability_counts[group]["alias_present"] += 1
            else:
                market_key = _market_key(payload)
                same_market_sources = price_sources_by_market.get(market_key, {}).get(group) if market_key else None
                if same_market_sources:
                    price_joinability_counts[group]["joinable_from_metadata"] += 1
                    price_join_sources[group].update(same_market_sources)
                else:
                    price_joinability_counts[group]["not_available_in_replay"] += 1

    estimated_uplift = max(0, model_eligibility_would_be_reached_count - observed_probability_model_called_count)
    dominant_gate = fail_counts_by_gate.most_common(1)[0][0] if fail_counts_by_gate else "NONE"
    dominant_reason = fail_reasons.most_common(1)[0][0] if fail_reasons else "NONE"
    active_profit_final_split = {
        "ACTIVE_INVENTORY_TRADING": lifecycle_split.get("ACTIVE_INVENTORY_TRADING", 0),
        "PROFIT_MANAGEMENT": lifecycle_split.get("PROFIT_MANAGEMENT", 0),
        "FINAL_DERISK": lifecycle_split.get("FINAL_DERISK", 0),
    }
    ev_input_coverage = _build_ev_input_coverage(
        executable_event_count=executable_event_count,
        model_eligibility_would_be_reached_count=model_eligibility_would_be_reached_count,
        executable_group_available=executable_group_available,
        executable_group_missing=executable_group_missing,
        eligible_group_available=eligible_group_available,
        eligible_group_missing=eligible_group_missing,
        executable_alias_hits=executable_alias_hits,
        eligible_alias_hits=eligible_alias_hits,
        eligible_missing_reason_counts=eligible_missing_reason_counts,
        same_market_join_sources_by_group=same_market_join_sources_by_group,
        risk_observable_count=risk_observable_count,
    )
    packet_schema_gap = _build_packet_schema_gap(
        packet_event_count=model_eligibility_would_be_reached_count,
        packet_field_available=packet_field_available,
        packet_field_missing=packet_field_missing,
        packet_alias_hits=packet_alias_hits,
        packet_missing_reasons=packet_missing_reasons,
    )
    price_source_mapping = _build_price_source_mapping(
        packet_event_count=model_eligibility_would_be_reached_count,
        price_loaded_alias_counts=price_loaded_alias_counts,
        price_loaded_alias_by_producer=price_loaded_alias_by_producer,
        price_packet_alias_counts=price_packet_alias_counts,
        price_joinability_counts=price_joinability_counts,
        price_join_sources=price_join_sources,
        slug_title_present_count=slug_title_present_count,
        slug_title_numeric_candidate_count=slug_title_numeric_candidate_count,
        slug_title_reliable_target_candidate_count=slug_title_reliable_target_candidate_count,
    )
    packet_price_enrichment_diagnostics = _build_packet_price_enrichment_diagnostics(
        executable_event_count=executable_event_count,
        model_eligibility_would_be_reached_count=model_eligibility_would_be_reached_count,
        executable_price_fields_present_count=executable_price_fields_present_count,
        eligible_price_fields_present_count=eligible_price_fields_present_count,
        packets_with_ptb_context=packets_with_ptb_context,
        packets_without_ptb_context=packets_without_ptb_context,
        packets_before_ptb_ready=packets_before_ptb_ready,
        packets_after_ptb_ready=packets_after_ptb_ready,
        packets_missing_propagation=packets_missing_propagation,
        packets_missing_source_fields=packets_missing_source_fields,
        packets_missing_due_to_skip_path=packets_missing_due_to_skip_path,
        packets_missing_due_to_snapshot_only_path=packets_missing_due_to_snapshot_only_path,
        enrichment_source_counts=enrichment_source_counts,
        enrichment_drop_reason_counts=enrichment_drop_reason_counts,
        ptb_context_availability_counts=ptb_context_availability_counts,
        oracle_context_availability_counts=oracle_context_availability_counts,
        target_context_availability_counts=target_context_availability_counts,
        packet_schema_price_field_counts=packet_schema_price_field_counts,
        producer_price_enrichment_counts=producer_price_enrichment_counts,
    )

    return {
        "schema_version": "event_driven_admission_simulation_v5",
        "scope": "offline_replay_simulation_only",
        "generated_at_utc": _utc_now(),
        "date": date,
        "time_filter": {
            "since": since,
            "until": until,
            "run_id": run_id,
        },
        "guardrails": {
            "offline_only": True,
            "runtime_behavior_changed": False,
            "strategy_changed": False,
            "risk_changed": False,
            "execution_changed": False,
            "live_behavior_changed": False,
            "simulation_wired_to_trading": False,
        },
        "source_events_loaded": len(events),
        "bad_json_lines": bad_json_lines,
        "source_event_counts_by_producer": dict(source_event_counts_by_producer),
        "simulation_funnel": {
            "executable_liquidity_event_count": executable_event_count,
            "same_token_pair_count": same_token_pair_count,
            "token_pair_lineage_ok_count": same_token_pair_count,
            "model_eligibility_would_be_reached_count": model_eligibility_would_be_reached_count,
            "risk_gate_observable_count": risk_observable_count,
            "EV_fields_required_event_count": model_eligibility_would_be_reached_count,
        },
        "fail_counts_by_gate": dict(fail_counts_by_gate),
        "fail_reasons": _top(fail_reasons),
        "active_profit_final_derisk_phase_split": active_profit_final_split,
        "lifecycle_phase_split": dict(lifecycle_split),
        "phase_gate_fail_counts": _top(phase_fail_counts, limit=12),
        "estimated_probability_model_called_uplift": estimated_uplift,
        "observed_probability_model_called_count": observed_probability_model_called_count,
        "model_ev_required_field_missing_counts": dict(model_required_missing),
        "required_missing_fields": sorted(model_required_missing),
        "ev_input_coverage": ev_input_coverage,
        "packet_schema_gap": packet_schema_gap,
        "price_source_mapping": price_source_mapping,
        "packet_price_enrichment_diagnostics": packet_price_enrichment_diagnostics,
        "dominant_blocker": {
            "gate": dominant_gate,
            "reason": dominant_reason,
        },
        "recommended_next_patch": _recommended_next_patch(
            executable_event_count=executable_event_count,
            model_eligibility_would_be_reached_count=model_eligibility_would_be_reached_count,
            fail_counts_by_gate=fail_counts_by_gate,
            missing_fields=model_required_missing,
        ),
        "paper_promotion_gates": [
            "Run the simulator across multiple fresh paper sessions before any runtime admission patch.",
            "Only promote to paper runtime design if simulated model eligibility is consistently non-zero.",
            "Prove risk gates remain observable before allowing an event-driven paper hot path.",
            "Keep live mode out of scope until paper-only event admission has replay evidence and targeted tests.",
        ],
    }


def _recommended_next_patch(
    *,
    executable_event_count: int,
    model_eligibility_would_be_reached_count: int,
    fail_counts_by_gate: Counter[str],
    missing_fields: Counter[str],
) -> str:
    if executable_event_count == 0:
        return "Collect fresh market_snapshot JSONL with YES/NO bid/ask fields before simulating admission."
    if model_eligibility_would_be_reached_count > 0 and missing_fields:
        top_missing = missing_fields.most_common(1)[0][0]
        return f"Add offline/reporting support for missing EV input group: {top_missing}."
    if model_eligibility_would_be_reached_count > 0:
        return "Design the smallest paper-only event admission probe; do not change gates or live behavior."
    if fail_counts_by_gate:
        top_gate = fail_counts_by_gate.most_common(1)[0][0]
        return f"Investigate simulated admission blocker {top_gate} before any runtime design."
    return "No actionable admission pattern found in this replay slice."


def write_event_driven_admission_simulation_report(report: dict[str, Any], report_dir: str | Path = DEFAULT_REPORT_DIR) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"event_driven_admission_simulation_{report['date']}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline event-driven executable-liquidity admission simulation.")
    parser.add_argument("--date", required=True, help="Replay date in YYYY-MM-DD format.")
    parser.add_argument("--since", help="Optional HH:MM UTC lower bound.")
    parser.add_argument("--until", help="Optional HH:MM UTC upper bound.")
    parser.add_argument("--run-id", help="Optional replay run_id filter.")
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--max-book-age-ms", type=float, default=DEFAULT_MAX_BOOK_AGE_MS)
    parser.add_argument("--max-side-spread", type=float, default=DEFAULT_MAX_SIDE_SPREAD)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = build_event_driven_admission_simulation_report(
        date=args.date,
        base_dir=args.base_dir,
        since=args.since,
        until=args.until,
        run_id=args.run_id,
        max_book_age_ms=args.max_book_age_ms,
        max_side_spread=args.max_side_spread,
    )
    if args.write_report:
        path = write_event_driven_admission_simulation_report(report, report_dir=args.report_dir)
        print(path)
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
