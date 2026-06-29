"""Compatibility shim — re-exports all public symbols from the canonical modules.

Phase 3M split:
  - Reconciliation carry helpers  → trader_reconciliation_carry.py
  - Trade event payload builders  → trader_trade_event_payload.py

This shim preserves backward compatibility for any callers that still import
from this path. No implementation logic lives here.
"""

from polymarket.observability.trader_reconciliation_carry import (
    carry_entry_model_truth_from_metadata,
    build_paper_trade_replay_key,
    size_sharp_metadata,
    size_sharp_close_carry,
    build_entry_model_truth_envelope,
    build_trade_position_metadata,
)
from polymarket.observability.trader_trade_event_payload import (
    collect_trade_open_context,
    build_trade_opened_payload,
    build_trade_closed_payload,
)

__all__ = [
    "carry_entry_model_truth_from_metadata",
    "build_paper_trade_replay_key",
    "size_sharp_metadata",
    "size_sharp_close_carry",
    "build_entry_model_truth_envelope",
    "build_trade_position_metadata",
    "collect_trade_open_context",
    "build_trade_opened_payload",
    "build_trade_closed_payload",
]
