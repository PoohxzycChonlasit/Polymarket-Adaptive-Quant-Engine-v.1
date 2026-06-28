#!/usr/bin/env python3
"""
canonical_trade_context_builder.py
==================================
Offline Canonical Trade Context v1 compiler.
Aggregates and compiles historical JSONL log streams (trade_journal, decision_log,
execution_log, risk_log, path_truth) into Completed Trades v1 datasets
conforming to the Canonical Trade Context v1 schema.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

LOGGER = logging.getLogger(__name__)

DEFAULT_QUANT_DATA_DIR = Path("runtime/quant_data")
DEFAULT_REPORT_DIR = Path("runtime/reports")

# The 5 log streams we parse
CATEGORIES = (
    "trade_journal",
    "decision_log",
    "execution_log",
    "risk_log",
    "path_truth",
)

def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)

def _to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None

def _first_text(payloads: list[dict[str, Any]], *keys: str) -> str | None:
    for p in payloads:
        if not isinstance(p, dict):
            continue
        for key in keys:
            val = p.get(key)
            if val is not None and str(val).strip() not in ("", "null", "None"):
                return str(val).strip()
    return None

def _first_float(payloads: list[dict[str, Any]], *keys: str) -> float | None:
    for p in payloads:
        if not isinstance(p, dict):
            continue
        for key in keys:
            val = _to_float(p.get(key))
            if val is not None:
                return val
    return None

def _parse_date(value: str) -> date_type:
    return datetime.strptime(value, "%Y-%m-%d").date()

def iter_dates(date_from: str, date_to: str) -> list[str]:
    dates: list[str] = []
    current = _parse_date(date_from)
    end = _parse_date(date_to)
    while current <= end:
        dates.append(current.isoformat())
        current += timedelta(days=1)
    return dates

def get_event_payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, dict) else event

def extract_field(events: list[dict[str, Any]], *keys: str) -> Any:
    """Extract first non-null field value checking payloads, envelopes, and root."""
    for event in events:
        if not isinstance(event, dict):
            continue
        payload = event.get("payload") or {}
        envelope = payload.get("entry_model_truth_envelope_v1") or {}
        diagnostics = payload.get("risk_plan_zero_diagnostics") or {}
        receipt = payload.get("receipt") or {}
        
        for key in keys:
            # Check nested keys separated by dot
            if "." in key:
                parts = key.split(".")
                curr: Any = payload
                for part in parts:
                    if isinstance(curr, dict) and part in curr:
                        curr = curr[part]
                    else:
                        curr = None
                        break
                if curr is not None and str(curr).strip() not in ("", "null", "None"):
                    return curr
            
            # Check payload root
            val = payload.get(key)
            if val is not None and str(val).strip() not in ("", "null", "None"):
                return val
                
            # Check event root
            val = event.get(key)
            if val is not None and str(val).strip() not in ("", "null", "None"):
                return val
                
            # Check inner envelopes
            val = envelope.get(key)
            if val is not None and str(val).strip() not in ("", "null", "None"):
                return val
                
            val = diagnostics.get(key)
            if val is not None and str(val).strip() not in ("", "null", "None"):
                return val
                
            val = receipt.get(key)
            if val is not None and str(val).strip() not in ("", "null", "None"):
                return val
    return None

def _run_id(event: dict[str, Any]) -> str:
    return str(event.get("run_id") or get_event_payload(event).get("run_id") or "").strip()

def _paper_key(event: dict[str, Any]) -> str:
    payload = get_event_payload(event)
    return str(payload.get("paper_trade_replay_key") or event.get("paper_trade_replay_key") or "").strip()

def _position_id(event: dict[str, Any]) -> str:
    payload = get_event_payload(event)
    return str(payload.get("position_id") or event.get("position_id") or "").strip()

def _event_type(event: dict[str, Any]) -> str:
    return str(event.get("event_type") or get_event_payload(event).get("event_type") or "").strip()

def _ts_text(event: dict[str, Any]) -> str:
    return str(event.get("timestamp_utc") or get_event_payload(event).get("timestamp_utc") or "")

def load_jsonl_file(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.is_file():
        return events
    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                text = raw_line.strip()
                if not text:
                    continue
                try:
                    event = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict):
                    event["_source_file"] = f"{path.parent.name}/{path.name}:{line_number}"
                    event["_category"] = path.parent.name
                    events.append(event)
    except OSError:
        pass
    return events


# ── Round-number PnL values typical of test/settlement events ─────────────
_ROUND_PNL_VALUES = {1.0, -1.0, 2.0, -2.0, 0.5, -0.5, 0.25, -0.25, 0.1, -0.1}

_TEST_EXIT_REASONS = frozenset({"test", "test_close", "debug", "synthetic"})
_SETTLEMENT_EXIT_REASONS = frozenset({"settlement", "binary_settlement", "resolved", "resolution"})
_FORCED_EXIT_REASONS = frozenset({"emergency_flatten", "forced_exit", "residual_sweep", "session_end"})


def _classify_event(
    row: dict[str, Any],
    open_event: dict[str, Any] | None,
    close_event: dict[str, Any] | None,
) -> str:
    """Classify a canonical row into one of five event types.

    Classification order (first match wins):
    1. test_event        — exit_reason is a test marker or PnL is a round test value
    2. settlement_event  — exit_reason indicates binary market settlement
    3. forced_exit_legacy — forced closure without entry metadata
    4. signal_driven_trade — has replay_key, ev, and decision context (usable for backtest)
    5. unknown_legacy    — everything else (unclassifiable grade D)
    """
    exit_reason = str(row.get("exit_reason") or "").lower()
    pnl = row.get("realized_pnl")
    has_rkey = bool(row.get("replay_key"))
    has_ev = row.get("ev") is not None
    has_open = open_event is not None
    has_close = close_event is not None

    if exit_reason in _TEST_EXIT_REASONS:
        return "test_event"

    # Round PnL values with no signal context strongly suggest test/synthetic events
    if pnl is not None and not has_ev and not has_rkey:
        try:
            if abs(round(float(pnl), 2)) in _ROUND_PNL_VALUES:
                return "test_event"
        except (TypeError, ValueError):
            pass

    if exit_reason in _SETTLEMENT_EXIT_REASONS:
        return "settlement_event"

    if exit_reason in _FORCED_EXIT_REASONS and not has_rkey:
        return "forced_exit_legacy"

    if has_rkey and has_ev and has_open and has_close:
        return "signal_driven_trade"

    if has_rkey and has_open and has_close:
        return "signal_driven_trade_partial"

    return "unknown_legacy"


def _diagnose_grade_d(
    row: dict[str, Any],
    open_event: dict[str, Any] | None,
    close_event: dict[str, Any] | None,
) -> str:
    """Return a short diagnostic code explaining why a grade D row is unmatched."""
    has_rkey = bool(row.get("replay_key"))
    has_pid = bool(row.get("position_id"))
    exit_reason = str(row.get("exit_reason") or "").lower()
    classification = row.get("event_classification", "")

    if classification == "test_event":
        return "test_event_no_signal_context"
    if classification == "settlement_event":
        return "settlement_event_no_open_matched"
    if classification == "forced_exit_legacy":
        return "forced_exit_no_replay_key"

    if not has_rkey and open_event is None:
        return "close_only_no_replay_key_legacy_schema"
    if not has_rkey and close_event is not None:
        return "close_missing_replay_key_cross_session"
    if has_rkey and open_event is None:
        return "close_has_replay_key_open_not_in_date_window"
    if has_pid and not has_rkey:
        return "position_id_only_run_id_mismatch"

    return "unmatched_unknown"


class CanonicalContextBuilder:
    def __init__(self, base_dir: Path, dates: list[str], *, skip_risk_log: bool = True):
        self.base_dir = base_dir
        self.dates = dates
        self.skip_risk_log = skip_risk_log
        
        # Loaded events
        self.opens: list[dict[str, Any]] = []
        self.closes: list[dict[str, Any]] = []
        self.decisions: list[dict[str, Any]] = []
        self.executions: list[dict[str, Any]] = []
        self.risks: list[dict[str, Any]] = []
        self.path_truths: list[dict[str, Any]] = []
        
        # Indexes for matching
        self.opens_by_replay_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        self.opens_by_pos_id: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        
        self.closes_by_replay_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        self.closes_by_pos_id: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        
        self.decisions_by_replay_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        self.decisions_by_pos_id: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        
        self.executions_by_replay_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        self.executions_by_pos_id: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        
        self.risks_by_run_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
        
        self.path_by_replay_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        self.path_by_pos_id: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    def load_all(self):
        for date_str in self.dates:
            for cat in CATEGORIES:
                path = self.base_dir / cat / f"{date_str}.jsonl"
                events = load_jsonl_file(path)
                if cat == "trade_journal":
                    for event in events:
                        etype = _event_type(event)
                        if etype == "trade_open":
                            self.opens.append(event)
                        elif etype == "trade_close":
                            self.closes.append(event)
                elif cat == "decision_log":
                    self.decisions.extend(events)
                elif cat == "execution_log":
                    self.executions.extend(events)
                elif cat == "risk_log":
                    if not self.skip_risk_log:
                        self.risks.extend(events)
                elif cat == "path_truth":
                    self.path_truths.extend(events)
                    
        # Build lookup indexes
        for op in self.opens:
            run_id = _run_id(op)
            rkey = _paper_key(op)
            pid = _position_id(op)
            if run_id and rkey:
                self.opens_by_replay_key[(run_id, rkey)].append(op)
            if run_id and pid:
                self.opens_by_pos_id[(run_id, pid)].append(op)
                
        for cl in self.closes:
            run_id = _run_id(cl)
            rkey = _paper_key(cl)
            pid = _position_id(cl)
            if run_id and rkey:
                self.closes_by_replay_key[(run_id, rkey)].append(cl)
            if run_id and pid:
                self.closes_by_pos_id[(run_id, pid)].append(cl)
                
        for dec in self.decisions:
            run_id = _run_id(dec)
            rkey = _paper_key(dec)
            pid = _position_id(dec)
            if run_id and rkey:
                self.decisions_by_replay_key[(run_id, rkey)].append(dec)
            if run_id and pid:
                self.decisions_by_pos_id[(run_id, pid)].append(dec)
                
        for ex in self.executions:
            run_id = _run_id(ex)
            rkey = _paper_key(ex)
            pid = _position_id(ex)
            if run_id and rkey:
                self.executions_by_replay_key[(run_id, rkey)].append(ex)
            if run_id and pid:
                self.executions_by_pos_id[(run_id, pid)].append(ex)
                
        for rk in self.risks:
            run_id = _run_id(rk)
            if run_id:
                self.risks_by_run_id[run_id].append(rk)
                
        for pt in self.path_truths:
            run_id = _run_id(pt)
            rkey = _paper_key(pt)
            pid = _position_id(pt)
            if run_id and rkey:
                self.path_by_replay_key[(run_id, rkey)].append(pt)
            if run_id and pid:
                self.path_by_pos_id[(run_id, pid)].append(pt)

    def compile(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        matched_opens: set[str] = set()
        matched_closes: set[str] = set()
        
        # Senders index tracking for unique mapping
        open_processed: set[str] = set()
        close_processed: set[str] = set()
        
        # 1. Process all Opens
        for op in self.opens:
            op_src = op.get("_source_file", "")
            if op_src in open_processed:
                continue
            open_processed.add(op_src)
            
            run_id = _run_id(op)
            rkey = _paper_key(op)
            pid = _position_id(op)
            
            # Find matching close
            cl_match: dict[str, Any] | None = None
            join_conf = "LOW"
            
            # Try primary key (run_id + replay_key)
            if run_id and rkey:
                potential_closes = self.closes_by_replay_key.get((run_id, rkey), [])
                unmatched = [c for c in potential_closes if c.get("_source_file") not in close_processed]
                if unmatched:
                    # Sort by timestamp to get closest exit
                    unmatched_sorted = sorted(unmatched, key=lambda x: _ts_text(x))
                    cl_match = unmatched_sorted[0]
                    join_conf = "HIGH"
            
            # Try fallback key (run_id + position_id)
            if not cl_match and run_id and pid:
                potential_closes = self.closes_by_pos_id.get((run_id, pid), [])
                unmatched = [c for c in potential_closes if c.get("_source_file") not in close_processed]
                if unmatched:
                    unmatched_sorted = sorted(unmatched, key=lambda x: _ts_text(x))
                    cl_match = unmatched_sorted[0]
                    join_conf = "MEDIUM"
                    
            if cl_match:
                close_processed.add(cl_match.get("_source_file", ""))
                matched_opens.add(op_src)
                matched_closes.add(cl_match.get("_source_file", ""))
                
            # Gather other stream elements
            dec_match = self._find_associated_event(run_id, rkey, pid, self.decisions_by_replay_key, self.decisions_by_pos_id)
            ex_match = self._find_associated_event(run_id, rkey, pid, self.executions_by_replay_key, self.executions_by_pos_id)
            pts = self._find_associated_path_events(run_id, rkey, pid)
            
            row = self._build_canonical_row(
                open_event=op,
                close_event=cl_match,
                decision_event=dec_match,
                execution_event=ex_match,
                path_events=pts,
                join_confidence=join_conf if cl_match else "LOW",
            )
            rows.append(row)
            
        # 2. Process Unmatched Closes
        for cl in self.closes:
            cl_src = cl.get("_source_file", "")
            if cl_src in close_processed:
                continue
            close_processed.add(cl_src)
            
            run_id = _run_id(cl)
            rkey = _paper_key(cl)
            pid = _position_id(cl)
            
            dec_match = self._find_associated_event(run_id, rkey, pid, self.decisions_by_replay_key, self.decisions_by_pos_id)
            ex_match = self._find_associated_event(run_id, rkey, pid, self.executions_by_replay_key, self.executions_by_pos_id)
            pts = self._find_associated_path_events(run_id, rkey, pid)
            
            row = self._build_canonical_row(
                open_event=None,
                close_event=cl,
                decision_event=dec_match,
                execution_event=ex_match,
                path_events=pts,
                join_confidence="LOW",
            )
            rows.append(row)

        summary = self._compute_summary_stats(rows, matched_opens, matched_closes)
        return rows, summary

    def _find_associated_event(
        self,
        run_id: str,
        rkey: str,
        pid: str,
        idx_rkey: dict[tuple[str, str], list[dict[str, Any]]],
        idx_pid: dict[tuple[str, str], list[dict[str, Any]]],
    ) -> dict[str, Any] | None:
        if run_id and rkey:
            events = idx_rkey.get((run_id, rkey))
            if events:
                return sorted(events, key=lambda x: _ts_text(x))[-1]
        if run_id and pid:
            events = idx_pid.get((run_id, pid))
            if events:
                return sorted(events, key=lambda x: _ts_text(x))[-1]
        return None

    def _find_associated_path_events(self, run_id: str, rkey: str, pid: str) -> list[dict[str, Any]]:
        pts: list[dict[str, Any]] = []
        seen = set()
        if run_id and rkey:
            for p in self.path_by_replay_key.get((run_id, rkey), []):
                src = p.get("_source_file")
                if src not in seen:
                    pts.append(p)
                    seen.add(src)
        if run_id and pid:
            for p in self.path_by_pos_id.get((run_id, pid), []):
                src = p.get("_source_file")
                if src not in seen:
                    pts.append(p)
                    seen.add(src)
        return sorted(pts, key=lambda x: _ts_text(x))

    def _build_canonical_row(
        self,
        open_event: dict[str, Any] | None,
        close_event: dict[str, Any] | None,
        decision_event: dict[str, Any] | None,
        execution_event: dict[str, Any] | None,
        path_events: list[dict[str, Any]],
        join_confidence: str,
    ) -> dict[str, Any]:
        events = [item for item in (open_event, close_event, decision_event, execution_event) if item is not None]
        payloads = [get_event_payload(item) for item in events]
        
        run_id = _run_id(open_event or close_event or {})
        rkey = _paper_key(open_event or close_event or {})
        pid = _position_id(open_event or close_event or {})
        
        # Derive trade_id
        key_str = rkey or pid or str(uuid_hash_key(open_event or close_event or {}))
        digest = hashlib.sha1(f"{run_id}|{key_str}".encode("utf-8")).hexdigest()
        trade_id = f"ct_{digest[:20]}"
        
        # Basic fields
        ticker = extract_field(events, "ticker", "asset")
        asset_id = "BTC" if (ticker and "BTC" in str(ticker).upper()) else ("ETH" if (ticker and "ETH" in str(ticker).upper()) else "UNKNOWN")
        outcome = extract_field(events, "outcome", "side")
        side = extract_field(events, "side")
        
        # Settle YES/NO outcome format
        if outcome and str(outcome).upper() in ("YES", "BUY_YES", "YES_TOKEN"):
            outcome = "YES"
        elif outcome and str(outcome).upper() in ("NO", "BUY_NO", "NO_TOKEN"):
            outcome = "NO"
            
        if side and str(side).upper() in ("BUY", "LONG"):
            side = "BUY"
        elif side and str(side).upper() in ("SELL", "SHORT"):
            side = "SELL"
            
        # Entry Decision Context
        prob = extract_field(events, "true_probability")
        if prob is None:
            outcome_upper = str(outcome or "").upper()
            if outcome_upper == "YES":
                prob = extract_field(events, "model_p_yes", "model_probability_yes", "p_yes")
            elif outcome_upper == "NO":
                prob = extract_field(events, "model_p_no", "model_probability_no", "p_no")
        prob = _to_float(prob)
        
        ev = _to_float(extract_field(events, "ev", "expected_value"))
        ev_after_spread = _to_float(extract_field(events, "ev_after_spread"))
        
        reason_codes = []
        for r_key in ("signal_reason", "strategy_signal_reason", "reason"):
            val = extract_field(events, r_key)
            if val and str(val) not in reason_codes:
                reason_codes.append(str(val))
                
        # Execution Context
        intended_price = _to_float(extract_field(events, "entry_price", "price"))
        intended_size = _to_float(extract_field(events, "size", "shares"))
        intended_notional = _to_float(extract_field(events, "notional_size"))
        if intended_notional is None and intended_price is not None and intended_size is not None:
            intended_notional = intended_price * intended_size
            
        fill_price = _to_float(extract_field(events, "fill_price", "price"))
        filled_size = _to_float(extract_field(events, "filled_size"))
        if filled_size is None and fill_price is not None:
            # Fallback to total size if fill size not explicitly reported but filled
            filled_size = intended_size
            
        slippage = None
        if fill_price is not None and intended_price is not None:
            slippage = fill_price - intended_price
            
        # Capital/Risk
        bankroll = _to_float(extract_field(events, "bankroll", "paper_available_balance"))
        equity = _to_float(extract_field(events, "paper_virtual_cash"))
        
        # Exit Outcome
        exit_price = _to_float(extract_field(events, "exit_price"))
        realized_pnl = _to_float(extract_field(events, "pnl", "pnl_usdc"))
        
        hold_seconds = _to_float(extract_field(events, "hold_seconds", "holding_seconds"))
        if hold_seconds is None and open_event and close_event:
            o_ts = _parse_ts(_ts_text(open_event))
            c_ts = _parse_ts(_ts_text(close_event))
            if o_ts and c_ts:
                hold_seconds = (c_ts - o_ts).total_seconds()
                
        pnl_pct = None
        if realized_pnl is not None and intended_notional and intended_notional > 0:
            pnl_pct = realized_pnl / intended_notional
            
        trade_result = extract_field(events, "trade_result")
        if not trade_result and realized_pnl is not None:
            trade_result = "WIN" if realized_pnl > 0 else ("LOSS" if realized_pnl < 0 else "FLAT")
            
        # Replay/Backtest
        source_streams = sorted(list({ev.get("_category") for ev in events if ev.get("_category")}))
        source_event_ids = {ev.get("_category"): ev.get("_source_file") for ev in events if ev.get("_category")}
        
        row = {
            # Identity
            "trade_id": trade_id,
            "position_id": pid or None,
            "market_id": extract_field(events, "market_id", "symbol"),
            "asset_id": asset_id,
            "ticker": ticker,
            "market_slug": extract_field(events, "market_slug", "preload_market_slug"),
            "outcome": outcome,
            "side": side or "BUY",
            "source_event_ids": source_event_ids,
            "replay_key": rkey or None,
            
            # Entry Decision Context
            "signal_name": extract_field(events, "signal_name"),
            "probability": prob,
            "fair_value": _to_float(extract_field(events, "fair_value")),
            "ev": ev,
            "ev_after_spread": ev_after_spread,
            "decision_score": _to_float(extract_field(events, "score")),
            "reason_codes": reason_codes,
            "blockers": extract_field(events, "blockers") or [],
            "market_state": extract_field(events, "market_state") or "UNKNOWN",
            "lifecycle_phase": extract_field(events, "lifecycle_phase") or "UNKNOWN",
            "seconds_remaining": _to_float(extract_field(events, "seconds_remaining", "seconds_until_close")),
            "quote_age_ms": _to_float(extract_field(events, "quote_age_ms", "orderbook_age_ms")),
            
            # Execution Context
            "intended_price": intended_price,
            "intended_size": intended_size,
            "intended_notional": intended_notional,
            "order_type": extract_field(events, "order_type") or "GTC",
            "order_id": extract_field(events, "order_id"),
            "submitted_at": extract_field(events, "created_at", "submitted_at") or (open_event.get("timestamp_utc") if open_event else None),
            "fill_status": extract_field(events, "status") or ("filled" if close_event else "unfilled"),
            "filled_size": filled_size,
            "fill_price": fill_price,
            "slippage": slippage,
            "timeout_status": extract_field(events, "timeout_status") or False,
            
            # Capital / Risk Context
            "bankroll": bankroll,
            "equity": equity,
            "realized_pnl_before": _to_float(extract_field(events, "realized_pnl_before")),
            "unrealized_pnl_before": _to_float(extract_field(events, "unrealized_pnl_before")),
            "bankroll_tier_id": extract_field(events, "bankroll_tier_id", "tier"),
            "bankroll_rank": extract_field(events, "bankroll_rank"),  # tier-string e.g. "T0_MICRO_SEED"
            "risk_mode": extract_field(events, "risk_mode") or "NORMAL",
            "risk_budget": _to_float(extract_field(events, "risk_budget", "remaining_risk_budget")),
            "max_order_usd": _to_float(extract_field(events, "max_order_usd", "live_max_order_usd")),
            "max_daily_loss_usd": _to_float(extract_field(events, "max_daily_loss_usd", "live_max_daily_loss_usd")),
            "max_open_exposure_usd": _to_float(extract_field(events, "max_open_exposure_usd", "live_max_open_exposure_usd")),
            "current_exposure": _to_float(extract_field(events, "current_exposure")),
            "target_exposure": _to_float(extract_field(events, "target_exposure")),
            "capital_score": _to_float(extract_field(events, "capital_score")),
            "capital_state": extract_field(events, "capital_state") or "HEALTHY",
            "promotion_candidate": extract_field(events, "promotion_candidate") or False,
            "demotion_candidate": extract_field(events, "demotion_candidate") or False,
            "expected_risk_profile": extract_field(events, "expected_risk_profile") or "MODERATE",
            "size_sharp_at_entry": _to_float(extract_field(events, "size_sharp_at_entry", "size_sharp")),
            "size_sharp_bucket": extract_field(events, "size_sharp_bucket") or "UNKNOWN",
            "size_sharp_deployment_state": extract_field(events, "size_sharp_deployment_state", "deployment_state") or "UNKNOWN",
            "size_sharp_limiting_factor": extract_field(events, "size_sharp_limiting_factor", "limiting_factor") or "UNKNOWN",
            "size_sharp_confidence_grade": extract_field(events, "size_sharp_confidence_grade", "confidence_grade") or "UNKNOWN",
            "size_sharp_component_scores": extract_field(events, "size_sharp_component_scores", "component_scores") or {},
            "size_sharp_penalties": extract_field(events, "size_sharp_penalties", "penalties") or {},
            "size_sharp_boosts": extract_field(events, "size_sharp_boosts", "boosts") or {},
            "size_sharp_hard_caps": extract_field(events, "size_sharp_hard_caps", "hard_caps") or [],
            "size_sharp_missing_inputs": extract_field(events, "size_sharp_missing_inputs", "missing_inputs") or [],
            "size_sharp_schema_version": extract_field(events, "size_sharp_schema_version") or "missing_legacy_metadata",

            # Shadow Policy — offline candidate validation telemetry (observability-only)
            "shadow_policy_decision": extract_field(events, "shadow_policy_decision"),
            "shadow_policy_reasons": extract_field(events, "shadow_policy_reasons") or [],
            "shadow_policy_observed_ev": _to_float(extract_field(events, "shadow_policy_observed_ev")),
            "shadow_policy_observed_probability": _to_float(extract_field(events, "shadow_policy_observed_probability")),
            "shadow_policy_observed_risk_mode": extract_field(events, "shadow_policy_observed_risk_mode"),
            "shadow_policy_id": extract_field(events, "shadow_policy_id"),
            "shadow_policy_confidence": extract_field(events, "shadow_policy_confidence"),

            # Inventory Context
            "inventory_state": extract_field(events, "inventory_state") or "FLAT",
            "open_position_count": _to_float(extract_field(events, "open_position_count")),
            "market_exposure_before": _to_float(extract_field(events, "market_exposure_before")),
            "market_exposure_after": _to_float(extract_field(events, "market_exposure_after")),
            "position_lifecycle_state": extract_field(events, "position_lifecycle_state", "lifecycle_action") or "UNKNOWN",
            
            # Exit / Outcome Context
            "exit_reason": extract_field(events, "exit_reason", "reason"),
            "exit_price": exit_price,
            "exit_timestamp": extract_field(events, "exit_timestamp") or (close_event.get("timestamp_utc") if close_event else None),
            "hold_seconds": hold_seconds,
            "realized_pnl": realized_pnl,
            "expected_pnl_at_entry": _to_float(extract_field(events, "expected_pnl_at_entry")),
            "pnl_pct": pnl_pct,
            "trade_result": trade_result,
            "resolved_outcome": extract_field(events, "resolved_outcome", "outcome"),
            
            # Replay / Backtest Context
            "replay_version": "1.0",
            "source_streams": source_streams,
            "join_confidence": join_confidence,
            "counterfactual_available": extract_field(events, "counterfactual_available") or False,
        }
        
        # Determine missing fields and data quality grade
        missing = [k for k, v in row.items() if v is None or (isinstance(v, list) and not v) or (isinstance(v, dict) and not v)]
        row["missing_fields"] = missing
        
        # Calculate grade
        # A: matched open+close, no critical fields missing
        # B: matched open+close, some minor missing
        # C: matched open+close, major missing
        # D: unmatched open/close
        # F: corrupt
        if not open_event or not close_event:
            grade = "D"
        else:
            critical_missing = [f for f in ("entry_price", "exit_price", "realized_pnl", "intended_size", "ticker") if f in missing]
            if critical_missing:
                grade = "C"
            elif any(f in missing for f in ("true_probability", "fair_value", "ev", "bankroll_tier_id", "risk_mode")):
                grade = "B"
            else:
                grade = "A"
        row["data_quality_grade"] = grade

        # Event classification — what kind of trade is this?
        row["event_classification"] = _classify_event(row, open_event, close_event)

        # Grade D diagnosis — why was this row unmatched?
        if grade == "D":
            row["grade_d_diagnosis"] = _diagnose_grade_d(row, open_event, close_event)
        else:
            row["grade_d_diagnosis"] = None

        # Embed MFE/MAE if path truth checkpoints exist
        if path_events:
            row.update(self._compute_path_excursions(path_events, intended_price or fill_price or 0.50, filled_size or intended_size or 0.0))
            
        return row

    def _compute_path_excursions(self, path_events: list[dict[str, Any]], entry_price: float, size: float) -> dict[str, Any]:
        prices: list[float] = []
        for p in path_events:
            payload = get_event_payload(p)
            price = _to_float(payload.get("current_mark_price") or payload.get("mark_price") or payload.get("price"))
            if price is not None:
                prices.append(price)
        if not prices:
            return {}
        max_price = max(prices)
        min_price = min(prices)
        return {
            "mfe_price": max_price,
            "mae_price": min_price,
            "mfe_usdc": (max_price - entry_price) * size,
            "mae_usdc": (min_price - entry_price) * size,
        }

    def _compute_summary_stats(self, rows: list[dict[str, Any]], matched_opens: set[str], matched_closes: set[str]) -> dict[str, Any]:
        grades = Counter(r["data_quality_grade"] for r in rows)
        join_confs = Counter(r["join_confidence"] for r in rows)
        
        # Calculate missing field rates
        field_null_counts = Counter()
        for r in rows:
            for field in r["missing_fields"]:
                field_null_counts[field] += 1
                
        total_rows = len(rows)
        missing_rates = {k: round(v / total_rows, 4) for k, v in field_null_counts.items()} if total_rows else {}
        
        # PnL stats
        pnls = [r["realized_pnl"] for r in rows if r["realized_pnl"] is not None]
        total_pnl = sum(pnls) if pnls else 0.0
        avg_pnl = total_pnl / len(pnls) if pnls else 0.0
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        win_rate = len(wins) / len(pnls) if pnls else 0.0
        
        return {
            "input_counts": {
                "trade_open": len(self.opens),
                "trade_close": len(self.closes),
                "decision": len(self.decisions),
                "execution": len(self.executions),
                "risk": len(self.risks),
                "path_truth": len(self.path_truths),
            },
            "matched_trades": len(matched_opens),
            "unmatched_opens": len(self.opens) - len(matched_opens),
            "unmatched_closes": len(self.closes) - len(matched_closes),
            "missing_field_rates": missing_rates,
            "data_quality_grade_distribution": dict(grades),
            "join_confidence_distribution": dict(join_confs),
            "event_classification_distribution": dict(Counter(r.get("event_classification", "unknown") for r in rows)),
            "grade_d_diagnosis_distribution": dict(Counter(
                r.get("grade_d_diagnosis", "n/a") for r in rows if r.get("data_quality_grade") == "D"
            )),
            "field_availability": {
                "has_ev": sum(1 for r in rows if r.get("ev") is not None),
                "has_size_sharp_at_entry": sum(1 for r in rows if r.get("size_sharp_at_entry") is not None),
                "has_bankroll_rank": sum(1 for r in rows if r.get("bankroll_rank") is not None),
                "has_replay_key": sum(1 for r in rows if r.get("replay_key")),
                "has_bankroll": sum(1 for r in rows if r.get("bankroll") is not None),
                "has_seconds_remaining": sum(1 for r in rows if r.get("seconds_remaining") is not None),
                "signal_driven_trades": sum(1 for r in rows if r.get("event_classification") in
                    ("signal_driven_trade", "signal_driven_trade_partial")),
                "test_events_excluded": sum(1 for r in rows if r.get("event_classification") == "test_event"),
                "total_rows": total_rows,
            },
            "pnl_summary": {
                "total_trades": len(pnls),
                "win_rate": round(win_rate, 4),
                "total_realized_pnl": round(total_pnl, 4),
                "avg_realized_pnl": round(avg_pnl, 4),
                "gross_profit": round(sum(wins), 4) if wins else 0.0,
                "gross_loss": round(sum(losses), 4) if losses else 0.0,
                "win_count": len(wins),
                "loss_count": len(losses),
            },
            "signal_driven_pnl_summary": self._compute_signal_pnl(rows),
        }

    def _compute_signal_pnl(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """PnL stats for signal_driven_trade rows only (excludes test/settlement)."""
        signal_rows = [r for r in rows if r.get("event_classification") in
                       ("signal_driven_trade", "signal_driven_trade_partial")]
        pnls = [r["realized_pnl"] for r in signal_rows if r.get("realized_pnl") is not None]
        if not pnls:
            return {"total_trades": 0, "win_rate": 0.0, "total_realized_pnl": 0.0}
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        return {
            "total_trades": len(pnls),
            "win_rate": round(len(wins) / len(pnls), 4),
            "total_realized_pnl": round(sum(pnls), 4),
            "avg_realized_pnl": round(sum(pnls) / len(pnls), 4),
            "gross_profit": round(sum(wins), 4) if wins else 0.0,
            "gross_loss": round(sum(losses), 4) if losses else 0.0,
            "win_count": len(wins),
            "loss_count": len(losses),
            "high_conf_only": {
                "total": sum(1 for r in signal_rows if r.get("join_confidence") == "HIGH"),
                "win_rate": round(
                    sum(1 for r in signal_rows if r.get("join_confidence") == "HIGH" and (r.get("realized_pnl") or 0) > 0) /
                    max(1, sum(1 for r in signal_rows if r.get("join_confidence") == "HIGH")), 4
                ),
            },
        }


def uuid_hash_key(event: dict[str, Any]) -> str:
    # Fallback to hash of event dict representation if replay key is missing
    return hashlib.sha1(str(sorted(event.items())).encode("utf-8")).hexdigest()

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Canonical Trade Context v1 Offline Compiler.")
    parser.add_argument("--base-dir", default=str(DEFAULT_QUANT_DATA_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--date", help="Process specific date YYYY-MM-DD")
    parser.add_argument("--start-date", help="Range start date YYYY-MM-DD")
    parser.add_argument("--end-date", help="Range end date YYYY-MM-DD")
    parser.add_argument("--pretty", action="store_true", help="Format JSON output with indents")
    parser.add_argument(
        "--skip-risk-log",
        action="store_true",
        default=True,
        help="Skip loading risk_log (default: True — risk data is indexed but never used in matching)",
    )
    parser.add_argument(
        "--include-risk-log",
        action="store_true",
        help="Force-load risk_log despite large file size (overrides --skip-risk-log)",
    )
    args = parser.parse_args(argv)
    
    base_dir = Path(args.base_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Resolve dates
    dates: list[str] = []
    if args.date:
        dates = [args.date]
    elif args.start_date and args.end_date:
        dates = iter_dates(args.start_date, args.end_date)
    else:
        # Default to all date files found in trade_journal directory
        trade_journal_dir = base_dir / "trade_journal"
        if trade_journal_dir.is_dir():
            dates = sorted([p.stem for p in trade_journal_dir.glob("*.jsonl")])
        else:
            print("Error: No trade_journal directory found at", trade_journal_dir, file=sys.stderr)
            return 1
            
    if not dates:
        print("Error: No dates to process.", file=sys.stderr)
        return 1
        
    skip_risk = not getattr(args, "include_risk_log", False)
    print(f"Processing {len(dates)} dates: {dates[0]} to {dates[-1]}")
    if skip_risk:
        print("Note: risk_log skipped (--include-risk-log to force). risk_by_run_id is unused in matching.")
    builder = CanonicalContextBuilder(base_dir, dates, skip_risk_log=skip_risk)
    builder.load_all()
    rows, summary = builder.compile()
    
    # File suffix timestamp (end-date or date or local YYYYMMDD)
    suffix_date = (args.end_date or args.date or dates[-1]).replace("-", "")
    
    # Write output
    jsonl_output = output_dir / f"canonical_trade_context_{suffix_date}.jsonl"
    summary_output = output_dir / f"canonical_trade_context_summary_{suffix_date}.json"
    
    with jsonl_output.open("w", encoding="utf-8") as handle:
        for r in rows:
            handle.write(json.dumps(r) + "\n")
            
    with summary_output.open("w", encoding="utf-8") as handle:
        indent = 2 if args.pretty else None
        json.dump(summary, handle, indent=indent)
        
    print(f"Successfully processed {len(rows)} compiled trades.")
    print(f"Wrote compiled rows to: {jsonl_output}")
    print(f"Wrote execution summary to: {summary_output}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
