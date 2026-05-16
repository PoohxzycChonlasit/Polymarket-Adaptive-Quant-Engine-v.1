from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from polymarket.trader import PolymarketTrader
import tools.session_runtime_evaluator as session_runtime_evaluator
from tools.paper_evaluation_report import DECISION_CAUTION, DECISION_FAIL, DECISION_PASS
from tools.session_runtime_evaluator import (
    build_multi_session_spread_summary,
    evaluate_session_runtime,
    format_terminal_summary,
    write_session_runtime_report,
)


DATE = "2026-05-09"


def _session_summary(**overrides) -> dict:
    summary = {
        "cycles_scanned": 50,
        "total_markets_scanned": 97,
        "total_opportunities_found": 0,
        "total_trades_simulated": 0,
        "paper_orders_created": 0,
        "paper_fills": 0,
        "paper_exits": 0,
        "simulated_pnl": 0.0,
        "max_drawdown": 0.0,
        "skipped_trade_reasons": {
            "Entry cutoff: 80s <= 90s": 44,
            "orderbook_unavailable": 42,
            "Risk plan returned zero position size -- skipping.": 11,
        },
        "top_skip_reasons": [],
        "risk_mode": "NORMAL",
        "risk_mode_allow_new_entries": True,
    }
    summary.update(overrides)
    return summary


def _replay_report(**overrides) -> dict:
    report = {
        "date_from": DATE,
        "date_to": DATE,
        "events_loaded": 120,
        "bad_json_lines": 0,
        "total_trades": 0,
        "skipped_decisions": 97,
        "top_skip_reasons": [["time_unsafe", 44], ["orderbook_unavailable", 42], ["risk_plan_zero", 11]],
        "approved_decisions": 0,
        "rejected_decisions": 97,
        "risk_reject_count": 11,
        "execution_failure_count": 0,
        "average_seconds_remaining": 187.68,
        "min_seconds_remaining": 34,
        "average_orderbook_age_ms": 4.71,
        "max_orderbook_age_ms": 25,
        "average_oracle_age_ms": 500,
        "max_oracle_age_ms": 900,
        "average_scan_cycle_duration_ms": 587.04,
        "average_decision_latency_ms": 993.22,
        "cutoff_block_count": 44,
        "adaptive_cutoff_allowed_count": 0,
        "adaptive_cutoff_denied_count": 44,
        "adaptive_cutoff_denied_reasons": [["hard_close_zone", 27], ["spread_too_wide", 17]],
    }
    report.update(overrides)
    return report


def _no_entry_report(**overrides) -> dict:
    report = {
        "total_scanned": 130,
        "total_entered": 0,
        "total_skipped": 130,
        "skip_reason_counts": {
            "time_unsafe": 70,
            "orderbook_unavailable": 40,
            "risk_plan_zero": 20,
        },
        "execution_events_loaded": 0,
        "execution_failure_count": 0,
        "order_submit_attempt_count": 0,
        "paper_fill_count": 0,
        "market_data_quality": {},
    }
    report.update(overrides)
    return report


class _FakeAnalyzerReport:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def to_dict(self) -> dict:
        return dict(self.payload)

    def __getattr__(self, name: str):
        if name == "market_data_quality":
            return self.payload.get("market_data_quality", {})
        if name == "recommendations":
            return self.payload.get("recommendations", [])
        return self.payload.get(name, 0)


def _write_execution_log(base_dir: Path, events: list[dict], *, flat_name: bool = False) -> None:
    lines = [json.dumps({"payload": event}) for event in events]
    if flat_name:
        base_dir.mkdir(parents=True)
        path = base_dir / f"execution_log_{DATE}.jsonl"
    else:
        execution_dir = base_dir / "execution_log"
        execution_dir.mkdir(parents=True)
        path = execution_dir / f"{DATE}.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_decision_log(base_dir: Path, events: list[dict]) -> None:
    decision_dir = base_dir / "decision_log"
    decision_dir.mkdir(parents=True)
    lines = [json.dumps(event) for event in events]
    (decision_dir / f"{DATE}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_market_snapshot_log(base_dir: Path, events: list[dict]) -> None:
    snapshot_dir = base_dir / "market_snapshots"
    snapshot_dir.mkdir(parents=True)
    lines = [json.dumps(event) for event in events]
    (snapshot_dir / f"{DATE}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_quant_category_log(base_dir: Path, category: str, events: list[dict]) -> None:
    category_dir = base_dir / category
    category_dir.mkdir(parents=True)
    lines = [json.dumps(event) for event in events]
    (category_dir / f"{DATE}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _decision_event(timestamp: str, skip_reason: str) -> dict:
    return {
        "timestamp_utc": timestamp,
        "event_type": "decision",
        "mode": "paper",
        "payload": {
            "decision_type": "skipped",
            "decision": "skip",
            "skipped": True,
            "skip_reason": skip_reason,
            "seconds_remaining": 180,
        },
    }


def _multi_session_payload(
    *,
    date: str,
    spread_diagnosis: str,
    candidate_diagnosis: str = "SPREAD_TOO_WIDE",
    entered: int = 0,
    recovery_rate: float = 0.0,
    normalization_seconds: float | None = None,
    avg_velocity: float = 0.0,
    closest_candidate_seconds: float | None = 120,
    closest_bucket: str = "90-120s",
    trend: str = "SIDEWAY",
    volatility: str = "NORMAL_VOL",
    bankroll_family: str = "",
    bankroll_mode: str = "",
    late_window_blocks: int = 1,
) -> dict:
    combo = f"{trend}+{volatility}"
    normalized_events = 1 if recovery_rate > 0 else 0
    return {
        "date": date,
        "health_summary": {"entered": entered},
        "candidate_gap_summary": {
            "candidate_gap_diagnosis": candidate_diagnosis,
            "closest_candidate_bucket": closest_bucket,
            "seconds_remaining_at_closest_candidate": closest_candidate_seconds,
            "closest_candidate_before_cutoff": {
                "trend_regime": trend,
                "volatility_regime": volatility,
            },
        },
        "spread_compression_summary": {
            "events_counted": 4,
            "pre_cutoff_spread_events": 4,
            "spread_compression_diagnosis": spread_diagnosis,
            "spread_recovery_rate": recovery_rate,
            "avg_spread_velocity": avg_velocity,
            "spread_normalization_seconds": normalization_seconds,
            "spread_gap_by_regime": {
                "trend_regime": {
                    trend: {
                        "events": 4,
                        "normalized_events": normalized_events,
                        "recovery_rate": recovery_rate,
                        "avg_spread": 0.12,
                        "avg_spread_gap": 0.02,
                    }
                },
                "volatility_regime": {
                    volatility: {
                        "events": 4,
                        "normalized_events": normalized_events,
                        "recovery_rate": recovery_rate,
                        "avg_spread": 0.12,
                        "avg_spread_gap": 0.02,
                    }
                },
                "combo_regime": {
                    combo: {
                        "events": 4,
                        "normalized_events": normalized_events,
                        "recovery_rate": recovery_rate,
                        "avg_spread": 0.12,
                        "avg_spread_gap": 0.02,
                    }
                },
            },
        },
        "cutoff_by_regime": {
            "late_window_opportunity": {
                "total_late_window_blocks": late_window_blocks,
                "late_window_diagnosis": "NO_LATE_WINDOW_SAMPLE" if late_window_blocks == 0 else "CUTOFF_PROTECTED_CAPITAL",
            }
        },
        "risk_blocks": {
            "bankroll_family": bankroll_family,
            "bankroll_mode": bankroll_mode,
        },
    }


def test_session_evaluator_classifies_cutoff_primary_and_market_readiness_secondary() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(),
        replay_report=_replay_report(),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_CAUTION
    assert evaluation.primary_bottleneck == "cutoff"
    assert evaluation.secondary_bottleneck == "market_readiness"
    assert evaluation.cutoff_behavior["time_unsafe_count"] == 44
    assert ["hard_close_zone", 27] in evaluation.cutoff_behavior["adaptive_cutoff_denied_reasons"]
    assert evaluation.orderbook_readiness["orderbook_unavailable_count"] == 42
    assert evaluation.risk_blocks["risk_plan_zero_count"] == 11
    assert evaluation.timing_quality["average_decision_latency_ms"] == pytest.approx(993.22)


def test_session_evaluator_groups_regimes_from_replay_payload() -> None:
    evaluation = evaluate_session_runtime(
        replay_report=_replay_report(
            volatility_regimes=[["HIGH_VOL", 3], ["NORMAL_VOL", 2]],
            trend_regimes=[["BREAKOUT", 4], ["SIDEWAY", 1]],
        ),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.regime_summary["events_counted"] == 5
    assert ["HIGH_VOL", 3] in evaluation.regime_summary["volatility_regimes"]
    assert ["BREAKOUT", 4] in evaluation.regime_summary["trend_regimes"]
    lines = format_terminal_summary(evaluation, verbose=True)
    assert any("regimes events=5" in line for line in lines)


def test_session_evaluator_groups_regimes_from_jsonl_events(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "skip_reason": "time_unsafe",
                    "volatility_regime": "LOW_VOL",
                    "trend_regime": "SIDEWAY",
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:01:00Z",
                "event_type": "decision",
                "payload": {
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "skip_reason": "orderbook_unavailable",
                    "display": {
                        "volatility_regime": "EXTREME_VOL",
                        "trend_regime": "REVERSAL_RISK",
                    },
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    assert evaluation.regime_summary["events_counted"] == 2
    assert ["LOW_VOL", 1] in evaluation.regime_summary["volatility_regimes"]
    assert ["EXTREME_VOL", 1] in evaluation.regime_summary["volatility_regimes"]
    assert ["REVERSAL_RISK", 1] in evaluation.regime_summary["trend_regimes"]


def test_session_evaluator_summarizes_regime_probability_diagnostics(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "skip_reason": "ev_below_threshold",
                    "market_regime": "TREND_UP",
                    "bullish_probability": 0.62,
                    "bearish_probability": 0.38,
                    "trend_strength": 0.72,
                    "reversal_risk": 0.15,
                    "volatility_score": 0.34,
                    "compression_score": 0.20,
                    "seconds_remaining": 160,
                    "indicator_evidence": {"ema_slope": "up", "rsi": "neutral"},
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:01:00Z",
                "event_type": "decision",
                "payload": {
                    "decision_type": "approved",
                    "decision": "buy",
                    "market_regime": "TREND_UP",
                    "bullish_probability": 0.68,
                    "bearish_probability": 0.32,
                    "trend_strength": 0.81,
                    "reversal_risk": 0.20,
                    "volatility_score": 0.41,
                    "compression_score": 0.10,
                    "seconds_remaining": 130,
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:02:00Z",
                "event_type": "decision",
                "payload": {
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "skip_reason": "spread_too_wide",
                    "market_regime": "COMPRESSION",
                    "bullish_probability": 0.52,
                    "bearish_probability": 0.48,
                    "compression_score": 0.82,
                    "seconds_remaining": 80,
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:03:00Z",
                "event_type": "decision",
                "payload": {
                    "decision_type": "risk_rejected",
                    "decision": "skip",
                    "skipped": True,
                    "skip_reason": "risk_mode_lockdown",
                    "market_regime": "EXTREME_VOL",
                    "bullish_probability": 0.20,
                    "bearish_probability": 0.80,
                    "reversal_risk": 0.76,
                    "volatility_score": 0.91,
                    "seconds_remaining": 40,
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    summary = evaluation.regime_probability_summary
    assert summary["events_counted"] == 4
    assert summary["events_with_probability_fields"] == 4
    assert ["TREND_UP", 2] in summary["market_regimes"]
    assert summary["skip_decisions_by_regime"]["TREND_UP"] == 1
    assert summary["enter_candidates_by_regime"]["TREND_UP"] == 1
    assert summary["probability_buckets"]["0.55-0.65"]["blocked_candidates"] == 1
    assert summary["skip_reasons_by_regime"]["COMPRESSION"] == [["spread_too_wide", 1]]
    assert summary["candidate_timing_by_regime"]["EXTREME_VOL"]["closest_seconds_remaining"] == pytest.approx(40)
    assert summary["compression_no_entry_correlation"]["high_compression_blocked_count"] == 1
    assert summary["reversal_defensive_skip_correlation"]["high_reversal_defensive_skip_count"] == 1
    assert summary["candidate_cutoff_timing"]["diagnosis"] == "CANDIDATES_TOO_CLOSE_TO_CUTOFF"
    assert summary["diagnostic_usefulness_for_inventory_replay"] == "READY_FOR_PHASE_2_REPLAY_RESEARCH"
    assert any("regime_probability " in line and "probability_fields=4" in line for line in format_terminal_summary(evaluation))


def test_session_evaluator_regime_probability_summary_handles_missing_phase1_fields(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "skip_reason": "orderbook_unavailable",
                    "seconds_remaining": 140,
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    summary = evaluation.regime_probability_summary
    assert summary["events_counted"] == 1
    assert summary["events_with_probability_fields"] == 0
    assert summary["market_regimes"] == [["UNKNOWN", 1]]
    assert summary["probability_buckets"]["UNKNOWN"]["blocked_candidates"] == 1
    assert summary["diagnostic_usefulness_for_inventory_replay"] == "INSUFFICIENT_DIAGNOSTIC_COVERAGE"


def test_session_evaluator_reports_inventory_replay_readiness_coverage(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "mode": "paper",
                "run_id": "run-test",
                "source_module": "test",
                "schema_version": "1.0",
                "payload": {
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "skip_reason": "spread_too_wide",
                    "seconds_remaining": 180,
                    "first_evaluable_seconds_remaining": 240,
                    "orderbook_readiness_reason": "ready",
                    "spread_gap_to_limit": 0.02,
                    "liquidity_state": "HEALTHY",
                    "edge": 0.01,
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    assert evaluation.phase2_coverage["status"] == "PARTIAL_PHASE2_COVERAGE"
    assert evaluation.inventory_replay_readiness["ready_for_runtime_inventory"] is False
    assert "mfe_mae_support" in evaluation.inventory_replay_readiness["coverage_gaps"]
    assert evaluation.phase2_coverage["requirements"]["fair_value_ev_decay"]["status"] == "proxy_inferred"
    assert evaluation.partial_lifecycle_replay["status"] == "PARTIAL_PROXY_REPLAY"
    assert evaluation.lifecycle_replay_confidence in {"LOW_PROXY", "MEDIUM_PROXY"}
    assert evaluation.missed_starter_candidates
    assert evaluation.missed_starter_candidates[0]["starter_replay_label"] == "missed_starter_proxy"
    assert any(item["section"] == "mfe_mae_support" for item in evaluation.replay_unsupported_sections)


def test_session_evaluator_default_output_is_compact_scanner_first() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(),
        replay_report=_replay_report(
            candidate_gap_summary={
                "events_counted": 2,
                "pre_cutoff_candidate_count": 1,
                "cutoff_or_late_candidate_count": 1,
                "candidate_gap_diagnosis": "SPREAD_TOO_WIDE",
                "cutoff_interpretation": "FINAL_SYMPTOM",
            },
            spread_compression_summary={
                "events_counted": 2,
                "normalized_spread_events": 1,
                "spread_state_before_cutoff": "WIDE_PRE_CUTOFF",
            },
        ),
        date=DATE,
        load_offline_reports=False,
    )

    lines = format_terminal_summary(evaluation)
    joined = "\n".join(lines)

    assert any(line.startswith("scanner_lifecycle ") for line in lines)
    assert any(line.startswith("market_readiness ") for line in lines)
    assert any(line.startswith("candidate_timing ") for line in lines)
    assert any(line.startswith("cutoff_summary ") for line in lines)
    assert "cutoff_by_regime" not in joined
    assert "late_window_opportunity" not in joined
    assert "spread_compression " not in joined
    assert "regime_replay " not in joined
    assert "regime_coverage_audit" not in joined


def test_session_evaluator_verbose_output_keeps_deep_diagnostics() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(),
        replay_report=_replay_report(
            cutoff_by_regime={"events_counted": 1},
            spread_compression_summary={"events_counted": 1},
            regime_replay_summary={"events_counted": 1},
            regime_coverage_audit={"total_events_checked": 1},
        ),
        date=DATE,
        load_offline_reports=False,
    )

    lines = format_terminal_summary(evaluation, verbose=True)
    joined = "\n".join(lines)

    assert "cutoff_by_regime" in joined
    assert "spread_compression " in joined
    assert "regime_replay " in joined
    assert "regime_coverage_audit" in joined
    assert "scanner_reset_plan=" in joined


def test_session_evaluator_classifies_lifecycle_and_cutoff_symptom() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(),
        replay_report=_replay_report(
            first_seen_seconds_remaining=240,
            first_evaluable_seconds_remaining=180,
            candidate_gap_summary={
                "events_counted": 2,
                "pre_cutoff_candidate_count": 1,
                "cutoff_or_late_candidate_count": 1,
                "avg_seconds_remaining_at_candidate": 96,
                "seconds_remaining_at_closest_candidate": 84,
                "candidate_gap_diagnosis": "SPREAD_TOO_WIDE",
                "cutoff_interpretation": "FINAL_SYMPTOM",
            },
            spread_compression_summary={
                "events_counted": 3,
                "normalized_spread_events": 0,
                "spread_state_before_cutoff": "WIDE_PRE_CUTOFF",
                "spread_compression_diagnosis": "SPREAD_NEVER_NORMALIZED",
            },
        ),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.scanner_lifecycle["dominant_lifecycle_bottleneck"] == "SPREAD_READINESS_DELAY"
    assert evaluation.cutoff_summary["cutoff_as_root_or_symptom"] == "FINAL_SYMPTOM"
    assert evaluation.cutoff_summary["cutoff_after_late_candidate"] is True
    assert evaluation.candidate_timing["closest_valid_candidate_seconds_remaining"] == 84


def test_session_evaluator_limits_top_skips_and_recommendations() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(
            skipped_trade_reasons={
                "time_unsafe": 6,
                "orderbook_unavailable": 5,
                "risk_plan_zero": 4,
                "confidence_too_low": 3,
                "ev_below_threshold": 2,
                "extra_reason": 1,
            }
        ),
        replay_report=_replay_report(
            top_skip_reasons=[
                ["time_unsafe", 6],
                ["orderbook_unavailable", 5],
                ["risk_plan_zero", 4],
                ["confidence_too_low", 3],
                ["ev_below_threshold", 2],
                ["extra_reason", 1],
            ],
            recommendations=["one", "two", "three", "four"],
        ),
        no_entry_report={
            "total_scanned": 21,
            "total_entered": 0,
            "total_skipped": 21,
            "skip_reason_counts": {
                "time_unsafe": 6,
                "orderbook_unavailable": 5,
                "risk_plan_zero": 4,
                "confidence_too_low": 3,
                "ev_below_threshold": 2,
                "extra_reason": 1,
            },
            "recommendations": ["inspect one", "inspect two", "inspect three"],
            "execution_failure_count": 0,
            "order_submit_attempt_count": 0,
            "paper_fill_count": 0,
            "market_data_quality": {},
        },
        date=DATE,
        load_offline_reports=False,
    )

    assert len(evaluation.skip_summary["top_skip_reasons"]) == 5
    assert ["extra_reason", 1] not in evaluation.skip_summary["top_skip_reasons"]
    assert len(evaluation.recommendations) <= 3


def test_session_evaluator_groups_cutoff_blocks_by_regime(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "skip_reason": "Entry cutoff: 40s <= 90s",
                    "seconds_remaining": 40,
                    "decision_latency_ms": 100,
                    "volatility_regime": "NORMAL_VOL",
                    "trend_regime": "SIDEWAY",
                    "micro_timing_denied_reason": "hard_close_zone",
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:01:00Z",
                "event_type": "decision",
                "payload": {
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "time_unsafe",
                    "seconds_remaining": 30,
                    "decision_latency_ms": 200,
                    "volatility_regime": "HIGH_VOL",
                    "trend_regime": "STRONG_UPTREND",
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:02:00Z",
                "event_type": "decision",
                "payload": {
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "skip_reason": "risk_plan_zero",
                    "seconds_remaining": 50,
                    "decision_latency_ms": 300,
                    "display": {
                        "volatility_regime": "NORMAL_VOL",
                        "trend_regime": "SIDEWAY",
                        "micro_timing_denied_reason": "spread_too_wide",
                    },
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:03:00Z",
                "event_type": "decision",
                "payload": {
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "skip_reason": "orderbook_unavailable",
                    "volatility_regime": "EXTREME_VOL",
                    "trend_regime": "BREAKOUT",
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    cutoff_by_regime = evaluation.cutoff_by_regime
    assert cutoff_by_regime["events_counted"] == 3
    assert cutoff_by_regime["volatility_regime"]["NORMAL_VOL"]["blocks"] == 2
    assert cutoff_by_regime["volatility_regime"]["NORMAL_VOL"]["avg_seconds_remaining"] == pytest.approx(45.0)
    assert cutoff_by_regime["volatility_regime"]["NORMAL_VOL"]["min_seconds_remaining"] == pytest.approx(40.0)
    assert cutoff_by_regime["volatility_regime"]["NORMAL_VOL"]["avg_decision_latency_ms"] == pytest.approx(200.0)
    assert ["hard_close_zone", 1] in cutoff_by_regime["volatility_regime"]["NORMAL_VOL"]["top_micro_deny_reasons"]
    assert ["spread_too_wide", 1] in cutoff_by_regime["trend_regime"]["SIDEWAY"]["top_micro_deny_reasons"]
    assert cutoff_by_regime["combo"]["SIDEWAY+NORMAL_VOL"]["blocks"] == 2
    assert "EXTREME_VOL" not in cutoff_by_regime["volatility_regime"]
    assert any("cutoff_by_regime events=3" in line for line in format_terminal_summary(evaluation, verbose=True))


def test_session_evaluator_groups_old_cutoff_events_as_unknown_regime(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "skip_reason": "Entry cutoff: 12s <= 90s",
                    "seconds_remaining": 12,
                    "decision_latency_ms": 80,
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    cutoff_by_regime = evaluation.cutoff_by_regime
    assert cutoff_by_regime["events_counted"] == 1
    assert cutoff_by_regime["volatility_regime"]["UNKNOWN"]["blocks"] == 1
    assert cutoff_by_regime["trend_regime"]["UNKNOWN"]["blocks"] == 1
    assert cutoff_by_regime["combo"]["UNKNOWN+UNKNOWN"]["blocks"] == 1


def test_session_evaluator_reports_late_window_opportunity_by_combo(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "skip_reason": "Entry cutoff: 30s <= 90s",
                    "seconds_remaining": 30,
                    "outcome": "YES",
                    "yes_mid": 0.50,
                    "volatility_regime": "EXTREME_VOL",
                    "trend_regime": "SIDEWAY",
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:01:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-2",
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "time_unsafe",
                    "seconds_remaining": 20,
                    "outcome": "NO",
                    "no_mid": 0.60,
                    "volatility_regime": "EXTREME_VOL",
                    "trend_regime": "SIDEWAY",
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:02:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-3",
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "time_unsafe",
                    "seconds_remaining": 50,
                    "outcome": "YES",
                    "yes_mid": 0.50,
                    "volatility_regime": "EXTREME_VOL",
                    "trend_regime": "SIDEWAY",
                },
            },
        ],
    )
    _write_market_snapshot_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:10Z",
                "event_type": "market_snapshot",
                "payload": {
                    "market_id": "market-1",
                    "seconds_remaining": 20,
                    "yes_mid": 0.56,
                    "no_mid": 0.44,
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:00:20Z",
                "event_type": "market_snapshot",
                "payload": {
                    "market_id": "market-1",
                    "seconds_remaining": 10,
                    "yes_mid": 0.72,
                    "no_mid": 0.28,
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:01:10Z",
                "event_type": "market_snapshot",
                "payload": {
                    "market_id": "market-2",
                    "seconds_remaining": 10,
                    "yes_mid": 0.51,
                    "no_mid": 0.49,
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    opportunity = evaluation.cutoff_by_regime["late_window_opportunity"]["combo"]["SIDEWAY+EXTREME_VOL"]
    late_window = evaluation.cutoff_by_regime["late_window_opportunity"]
    assert opportunity["blocks"] == 2
    assert opportunity["priced_blocks"] == 2
    assert opportunity["missing_price_data_blocks"] == 0
    assert opportunity["reached_plus_0_05"] == 1
    assert opportunity["reached_plus_0_10"] == 1
    assert opportunity["reached_plus_0_20"] == 1
    assert opportunity["adverse_instead_count"] == 1
    assert opportunity["max_favorable_move"] == pytest.approx(0.22)
    assert opportunity["max_adverse_move"] == pytest.approx(0.11)
    assert late_window["total_late_window_blocks"] == 2
    assert late_window["total_priced_blocks"] == 2
    assert late_window["total_missing_price_data_blocks"] == 0
    assert late_window["regimes_with_positive_followthrough"] == ["SIDEWAY+EXTREME_VOL"]
    assert late_window["regimes_with_adverse_followthrough"] == ["SIDEWAY+EXTREME_VOL"]
    assert late_window["strongest_missed_opportunity_regime"]["regime"] == "SIDEWAY+EXTREME_VOL"
    assert late_window["strongest_missed_opportunity_regime"]["score"] == pytest.approx(0.22)
    assert late_window["strongest_protective_cutoff_regime"]["regime"] == "SIDEWAY+EXTREME_VOL"
    assert late_window["strongest_protective_cutoff_regime"]["score"] == pytest.approx(0.11)
    assert late_window["late_window_diagnosis"] == "MIXED_REGIME_DEPENDENT"
    assert any("late_window_opportunity" in line for line in format_terminal_summary(evaluation, verbose=True))


def test_session_evaluator_classifies_late_window_missed_opportunity(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "time_unsafe",
                    "seconds_remaining": 30,
                    "outcome": "YES",
                    "yes_mid": 0.50,
                    "volatility_regime": "HIGH_VOL",
                    "trend_regime": "BREAKOUT",
                },
            },
        ],
    )
    _write_market_snapshot_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:10Z",
                "event_type": "market_snapshot",
                "payload": {
                    "market_id": "market-1",
                    "seconds_remaining": 20,
                    "yes_mid": 0.57,
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    late_window = evaluation.cutoff_by_regime["late_window_opportunity"]
    assert late_window["late_window_diagnosis"] == "CUTOFF_MISSED_OPPORTUNITY"
    assert late_window["regimes_with_positive_followthrough"] == ["BREAKOUT+HIGH_VOL"]
    assert late_window["regimes_with_adverse_followthrough"] == []
    assert late_window["strongest_missed_opportunity_regime"]["regime"] == "BREAKOUT+HIGH_VOL"
    assert late_window["strongest_protective_cutoff_regime"] is None


def test_session_evaluator_classifies_late_window_protective_cutoff(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "time_unsafe",
                    "seconds_remaining": 30,
                    "outcome": "NO",
                    "no_mid": 0.60,
                    "volatility_regime": "NORMAL_VOL",
                    "trend_regime": "SIDEWAY",
                },
            },
        ],
    )
    _write_market_snapshot_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:10Z",
                "event_type": "market_snapshot",
                "payload": {
                    "market_id": "market-1",
                    "seconds_remaining": 20,
                    "no_mid": 0.49,
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    late_window = evaluation.cutoff_by_regime["late_window_opportunity"]
    assert late_window["late_window_diagnosis"] == "CUTOFF_PROTECTED_CAPITAL"
    assert late_window["regimes_with_positive_followthrough"] == []
    assert late_window["regimes_with_adverse_followthrough"] == ["SIDEWAY+NORMAL_VOL"]
    assert late_window["strongest_missed_opportunity_regime"] is None
    assert late_window["strongest_protective_cutoff_regime"]["regime"] == "SIDEWAY+NORMAL_VOL"


def test_session_evaluator_classifies_late_window_insufficient_price_data(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "time_unsafe",
                    "seconds_remaining": 30,
                    "outcome": "YES",
                    "yes_mid": 0.50,
                    "volatility_regime": "LOW_VOL",
                    "trend_regime": "SIDEWAY",
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    late_window = evaluation.cutoff_by_regime["late_window_opportunity"]
    assert late_window["total_late_window_blocks"] == 1
    assert late_window["total_priced_blocks"] == 0
    assert late_window["total_missing_price_data_blocks"] == 1
    assert late_window["late_window_diagnosis"] == "INSUFFICIENT_PRICE_DATA"


def test_session_evaluator_classifies_no_late_window_sample(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "decision_type": "skipped",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "time_unsafe",
                    "seconds_remaining": 60,
                    "outcome": "YES",
                    "yes_mid": 0.50,
                    "volatility_regime": "LOW_VOL",
                    "trend_regime": "SIDEWAY",
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    late_window = evaluation.cutoff_by_regime["late_window_opportunity"]
    assert late_window["total_late_window_blocks"] == 0
    assert late_window["total_priced_blocks"] == 0
    assert late_window["total_missing_price_data_blocks"] == 0
    assert late_window["late_window_diagnosis"] == "NO_LATE_WINDOW_SAMPLE"


def test_session_evaluator_reports_candidate_gap_summary_before_cutoff(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "ticker": "BTC",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "ev_below_threshold",
                    "seconds_remaining": 170,
                    "entry_cutoff_seconds": 90,
                    "best_candidate_side": "YES",
                    "ev": 0.010,
                    "min_ev": 0.020,
                    "confidence": 0.70,
                    "confidence_threshold": 0.65,
                    "spread": 0.04,
                    "max_spread": 0.10,
                    "liquidity_state": "HEALTHY",
                    "volatility_regime": "HIGH_VOL",
                    "trend_regime": "BREAKOUT",
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:01:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "ticker": "BTC",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "ev_below_threshold",
                    "seconds_remaining": 130,
                    "entry_cutoff_seconds": 90,
                    "best_candidate_side": "NO",
                    "ev": 0.015,
                    "min_ev": 0.020,
                    "confidence": 0.72,
                    "confidence_threshold": 0.65,
                    "spread": 0.03,
                    "max_spread": 0.10,
                    "liquidity_state": "HEALTHY",
                    "volatility_regime": "HIGH_VOL",
                    "trend_regime": "SIDEWAY",
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:02:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-2",
                    "ticker": "ETH",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "confidence_too_low",
                    "seconds_remaining": 110,
                    "entry_cutoff_seconds": 90,
                    "best_candidate_side": "YES",
                    "ev": 0.030,
                    "min_ev": 0.020,
                    "confidence": 0.58,
                    "confidence_threshold": 0.65,
                    "spread": 0.03,
                    "max_spread": 0.10,
                    "liquidity_state": "HEALTHY",
                    "volatility_regime": "NORMAL_VOL",
                    "trend_regime": "SIDEWAY",
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:03:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-2",
                    "ticker": "ETH",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "spread_too_wide",
                    "seconds_remaining": 95,
                    "entry_cutoff_seconds": 90,
                    "best_candidate_side": "YES",
                    "ev": 0.040,
                    "min_ev": 0.020,
                    "confidence": 0.70,
                    "confidence_threshold": 0.65,
                    "spread": 0.13,
                    "max_spread": 0.10,
                    "liquidity_state": "EMPTY",
                    "volatility_regime": "EXTREME_VOL",
                    "trend_regime": "REVERSAL_RISK",
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    summary = evaluation.candidate_gap_summary
    closest = summary["closest_candidate_before_cutoff"]
    assert summary["events_counted"] == 4
    assert summary["pre_cutoff_candidate_count"] == 4
    assert summary["dominant_gap_type"] == "EV_TOO_LOW"
    assert summary["candidate_gap_diagnosis"] == "EV_TOO_LOW"
    assert summary["cutoff_interpretation"] == "FINAL_SYMPTOM"
    assert summary["closest_candidate_bucket"] == "120-180s"
    assert summary["seconds_remaining_at_closest_candidate"] == pytest.approx(130)
    assert summary["final_pre_cutoff_block_reason"] == "spread_too_wide"
    assert summary["timing_bucket_counts"]["120-180s"] == 2
    assert summary["timing_bucket_counts"]["90-120s"] == 2
    assert summary["gap_type_counts"]["EV_TOO_LOW"] == 2
    assert summary["gap_type_counts"]["CONFIDENCE_TOO_LOW"] == 1
    assert summary["gap_type_counts"]["SPREAD_TOO_WIDE"] == 1
    assert summary["gap_type_counts"]["LIQUIDITY_NOT_READY"] == 1
    assert closest["best_candidate_side"] == "NO"
    assert closest["ev_gap_to_threshold"] == pytest.approx(0.005)
    assert closest["confidence_gap_to_threshold"] == pytest.approx(-0.07)
    assert closest["spread_gap_to_limit"] == pytest.approx(-0.07)
    assert closest["liquidity_state"] == "HEALTHY"
    assert closest["volatility_regime"] == "HIGH_VOL"
    assert closest["trend_regime"] == "SIDEWAY"
    assert any("candidate_gap events=4" in line for line in format_terminal_summary(evaluation, verbose=True))


def test_session_evaluator_candidate_gap_classifies_candidate_too_late(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "time_unsafe",
                    "seconds_remaining": 40,
                    "entry_cutoff_seconds": 90,
                    "best_candidate_side": "YES",
                    "ev": 0.030,
                    "min_ev": 0.020,
                    "confidence": 0.70,
                    "confidence_threshold": 0.65,
                    "spread": 0.04,
                    "max_spread": 0.10,
                    "liquidity_state": "HEALTHY",
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    summary = evaluation.candidate_gap_summary
    assert summary["pre_cutoff_candidate_count"] == 0
    assert summary["cutoff_or_late_candidate_count"] == 1
    assert summary["dominant_gap_type"] == "CANDIDATE_TOO_LATE"
    assert summary["candidate_gap_diagnosis"] == "CANDIDATE_TOO_LATE"
    assert summary["cutoff_interpretation"] == "UNKNOWN"
    assert summary["closest_candidate_before_cutoff"] is None


def test_session_evaluator_candidate_gap_classifies_cutoff_too_strict(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "frequency_cooldown",
                    "seconds_remaining": 100,
                    "entry_cutoff_seconds": 90,
                    "best_candidate_side": "YES",
                    "ev": 0.030,
                    "min_ev": 0.020,
                    "confidence": 0.70,
                    "confidence_threshold": 0.65,
                    "spread": 0.04,
                    "max_spread": 0.10,
                    "liquidity_state": "HEALTHY",
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:01:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "time_unsafe",
                    "seconds_remaining": 40,
                    "entry_cutoff_seconds": 90,
                    "best_candidate_side": "YES",
                    "ev": 0.030,
                    "min_ev": 0.020,
                    "confidence": 0.70,
                    "confidence_threshold": 0.65,
                    "spread": 0.04,
                    "max_spread": 0.10,
                    "liquidity_state": "HEALTHY",
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    summary = evaluation.candidate_gap_summary
    assert summary["candidate_gap_diagnosis"] == "CUTOFF_TOO_STRICT"
    assert summary["cutoff_interpretation"] == "ROOT_CAUSE"
    assert summary["closest_candidate_bucket"] == "90-120s"
    assert summary["gap_type_counts"] == {}


def test_session_evaluator_candidate_gap_classifies_regime_no_edge(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "decision": "skip",
                    "skipped": True,
                    "skip_reason": "probability_model: no directional edge",
                    "seconds_remaining": 150,
                    "entry_cutoff_seconds": 90,
                    "best_candidate_side": "YES",
                    "ev": 0.020,
                    "min_ev": 0.020,
                    "confidence": 0.65,
                    "confidence_threshold": 0.65,
                    "spread": 0.04,
                    "max_spread": 0.10,
                    "liquidity_state": "HEALTHY",
                    "volatility_regime": "LOW_VOL",
                    "trend_regime": "SIDEWAY",
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    summary = evaluation.candidate_gap_summary
    assert summary["dominant_gap_type"] == "REGIME_NO_EDGE"
    assert summary["candidate_gap_diagnosis"] == "REGIME_NO_EDGE"
    assert summary["cutoff_interpretation"] == "FINAL_SYMPTOM"


def test_session_evaluator_candidate_gap_requires_candidate_data(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "decision": "skip",
                    "skipped": True,
                    "skip_reason": "Entry cutoff: 80s <= 90s",
                    "seconds_remaining": 80,
                    "entry_cutoff_seconds": 90,
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    summary = evaluation.candidate_gap_summary
    assert summary["events_counted"] == 1
    assert summary["candidate_gap_diagnosis"] == "INSUFFICIENT_CANDIDATE_DATA"
    assert summary["cutoff_interpretation"] == "UNKNOWN"


def test_session_evaluator_reports_spread_compression_recovered_before_cutoff(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "ticker": "BTC",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "spread_too_wide",
                    "seconds_remaining": 170,
                    "entry_cutoff_seconds": 90,
                    "best_candidate_side": "YES",
                    "spread": 0.16,
                    "max_spread": 0.10,
                    "liquidity_state": "HEALTHY",
                    "volatility_regime": "HIGH_VOL",
                    "trend_regime": "BREAKOUT",
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:01:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "ticker": "BTC",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "spread_too_wide",
                    "seconds_remaining": 130,
                    "entry_cutoff_seconds": 90,
                    "best_candidate_side": "YES",
                    "spread": 0.12,
                    "max_spread": 0.10,
                    "liquidity_state": "HEALTHY",
                    "volatility_regime": "HIGH_VOL",
                    "trend_regime": "BREAKOUT",
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:02:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "ticker": "BTC",
                    "decision": "skip",
                    "skipped": True,
                    "normalized_skip_reason": "frequency_cooldown",
                    "seconds_remaining": 100,
                    "entry_cutoff_seconds": 90,
                    "best_candidate_side": "YES",
                    "spread": 0.10,
                    "max_spread": 0.10,
                    "liquidity_state": "HEALTHY",
                    "volatility_regime": "HIGH_VOL",
                    "trend_regime": "BREAKOUT",
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    summary = evaluation.spread_compression_summary
    closest = summary["closest_spread_gap_before_cutoff"]
    timeline = summary["candidate_vs_spread_gap_timeline"]
    assert summary["events_counted"] == 3
    assert summary["pre_cutoff_spread_events"] == 3
    assert summary["spread_recovery_rate"] == pytest.approx(1 / 3, abs=0.0001)
    assert summary["avg_spread_velocity"] == pytest.approx(0.0005)
    assert summary["spread_normalization_seconds"] == pytest.approx(100)
    assert summary["spread_state_before_cutoff"] == "MIXED_PRE_CUTOFF"
    assert summary["spread_compression_diagnosis"] == "SPREAD_RECOVERED_BEFORE_CUTOFF"
    assert closest["seconds_remaining"] == pytest.approx(100)
    assert closest["spread_gap_to_limit"] == pytest.approx(0.0)
    assert summary["spread_gap_by_timing_bucket"]["120-180s"]["events"] == 2
    assert summary["spread_gap_by_timing_bucket"]["90-120s"]["normalized_events"] == 1
    assert summary["spread_gap_by_regime"]["volatility_regime"]["HIGH_VOL"]["events"] == 3
    assert summary["spread_gap_by_regime"]["trend_regime"]["BREAKOUT"]["recovery_rate"] == pytest.approx(1 / 3, abs=0.0001)
    assert summary["spread_gap_by_regime"]["combo_regime"]["BREAKOUT+HIGH_VOL"]["avg_spread_gap"] == pytest.approx(0.026667)
    assert summary["avg_spread_velocity_by_combo_regime"]["BREAKOUT+HIGH_VOL"] == pytest.approx(0.0005)
    assert timeline[0]["spread_gap_to_limit"] == pytest.approx(0.06)
    assert any("spread_compression events=3" in line for line in format_terminal_summary(evaluation, verbose=True))


def test_session_evaluator_classifies_spread_normalized_too_late(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "seconds_remaining": 100,
                    "entry_cutoff_seconds": 90,
                    "spread": 0.13,
                    "max_spread": 0.10,
                    "volatility_regime": "NORMAL_VOL",
                    "trend_regime": "SIDEWAY",
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:01:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "seconds_remaining": 80,
                    "entry_cutoff_seconds": 90,
                    "spread": 0.08,
                    "max_spread": 0.10,
                    "volatility_regime": "NORMAL_VOL",
                    "trend_regime": "SIDEWAY",
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    summary = evaluation.spread_compression_summary
    assert summary["spread_compression_diagnosis"] == "SPREAD_NORMALIZED_TOO_LATE"
    assert summary["spread_state_before_cutoff"] == "WIDE_PRE_CUTOFF"
    assert summary["spread_normalization_seconds"] == pytest.approx(80)


def test_session_evaluator_classifies_spread_never_normalized(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "seconds_remaining": 150,
                    "entry_cutoff_seconds": 90,
                    "spread": 0.14,
                    "max_spread": 0.10,
                    "volatility_regime": "EXTREME_VOL",
                    "trend_regime": "REVERSAL_RISK",
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:01:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "seconds_remaining": 95,
                    "entry_cutoff_seconds": 90,
                    "spread": 0.12,
                    "max_spread": 0.10,
                    "volatility_regime": "EXTREME_VOL",
                    "trend_regime": "REVERSAL_RISK",
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    summary = evaluation.spread_compression_summary
    assert summary["spread_compression_diagnosis"] == "SPREAD_NEVER_NORMALIZED"
    assert summary["spread_recovery_rate"] == 0.0
    assert summary["spread_state_before_cutoff"] == "WIDE_PRE_CUTOFF"


def test_session_evaluator_classifies_regime_dependent_spread_behavior(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "seconds_remaining": 150,
                    "entry_cutoff_seconds": 90,
                    "spread": 0.09,
                    "max_spread": 0.10,
                    "volatility_regime": "NORMAL_VOL",
                    "trend_regime": "SIDEWAY",
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:01:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-2",
                    "seconds_remaining": 150,
                    "entry_cutoff_seconds": 90,
                    "spread": 0.16,
                    "max_spread": 0.10,
                    "volatility_regime": "EXTREME_VOL",
                    "trend_regime": "BREAKOUT",
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    summary = evaluation.spread_compression_summary
    combo = summary["spread_gap_by_regime"]["combo_regime"]
    assert summary["spread_compression_diagnosis"] == "REGIME_DEPENDENT_SPREAD_BEHAVIOR"
    assert combo["SIDEWAY+NORMAL_VOL"]["recovery_rate"] == pytest.approx(1.0)
    assert combo["BREAKOUT+EXTREME_VOL"]["recovery_rate"] == pytest.approx(0.0)


def test_session_evaluator_classifies_insufficient_spread_data(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "payload": {
                    "market_id": "market-1",
                    "decision": "skip",
                    "skipped": True,
                    "seconds_remaining": 150,
                    "entry_cutoff_seconds": 90,
                    "normalized_skip_reason": "confidence_too_low",
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    summary = evaluation.spread_compression_summary
    assert summary["events_counted"] == 0
    assert summary["spread_compression_diagnosis"] == "INSUFFICIENT_SPREAD_DATA"


def test_session_evaluator_reports_regime_replay_summary(tmp_path: Path) -> None:
    events: list[dict] = []
    for index in range(6):
        events.append({
            "timestamp_utc": f"{DATE}T10:00:{index:02d}Z",
            "event_type": "decision",
            "payload": {
                "market_id": f"normal-{index}",
                "decision": "skip",
                "skipped": True,
                "normalized_skip_reason": "no_signal",
                "seconds_remaining": 180 - index,
                "entry_cutoff_seconds": 90,
                "best_candidate_side": "YES",
                "spread": 0.05,
                "max_spread": 0.10,
                "liquidity_state": "HEALTHY",
                "volatility_regime": "NORMAL_VOL",
                "trend_regime": "SIDEWAY",
            },
        })
    for index in range(6):
        events.append({
            "timestamp_utc": f"{DATE}T10:01:{index:02d}Z",
            "event_type": "decision",
            "payload": {
                "market_id": f"extreme-{index}",
                "decision": "skip",
                "skipped": True,
                "normalized_skip_reason": "spread_too_wide",
                "seconds_remaining": 120 - index,
                "entry_cutoff_seconds": 90,
                "best_candidate_side": "NO",
                "spread": 0.14,
                "max_spread": 0.10,
                "liquidity_state": "EMPTY",
                "volatility_regime": "EXTREME_VOL",
                "trend_regime": "SIDEWAY",
            },
        })
    for index in range(10):
        events.append({
            "timestamp_utc": f"{DATE}T10:02:{index:02d}Z",
            "event_type": "decision",
            "payload": {
                "market_id": f"unknown-{index}",
                "decision": "skip",
                "skipped": True,
                "normalized_skip_reason": "time_unsafe",
                "seconds_remaining": 40,
                "entry_cutoff_seconds": 90,
                "spread": 0.02,
                "max_spread": 0.10,
                "liquidity_state": "HEALTHY",
            },
        })
    _write_decision_log(tmp_path, events)

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    summary = evaluation.regime_replay_summary
    combo = summary["spread_recovery_by_regime"]["combo_regime"]
    candidate_combo = summary["candidate_gap_by_regime"]["combo_regime"]
    liquidity_combo = summary["liquidity_readiness_by_regime"]["combo_regime"]
    no_entry_combo = summary["no_entry_by_regime"]["combo_regime"]
    late_combo = summary["late_window_by_regime"]["combo_regime"]
    timing_combo = summary["closest_candidate_timing_by_regime"]["combo_regime"]

    assert summary["events_counted"] == 22
    assert summary["regime_tradeability_classification"] == "UNKNOWN_COVERAGE_GAP"
    assert combo["NORMAL_VOL+SIDEWAY"]["spread_recovery_rate"] == pytest.approx(1.0)
    assert combo["NORMAL_VOL+SIDEWAY"]["regime_tradeability_classification"] == "TRADEABLE_REGIME"
    assert combo["EXTREME_VOL+SIDEWAY"]["spread_recovery_rate"] == pytest.approx(0.0)
    assert combo["EXTREME_VOL+SIDEWAY"]["avg_spread_gap"] == pytest.approx(0.04)
    assert combo["EXTREME_VOL+SIDEWAY"]["regime_tradeability_classification"] == "AVOID_REGIME"
    assert candidate_combo["EXTREME_VOL+SIDEWAY"]["dominant_candidate_gap"] == "SPREAD_TOO_WIDE"
    assert candidate_combo["EXTREME_VOL+SIDEWAY"]["candidate_gap_counts"]["LIQUIDITY_NOT_READY"] == 6
    assert liquidity_combo["EXTREME_VOL+SIDEWAY"]["liquidity_not_ready_rate"] == pytest.approx(1.0)
    assert no_entry_combo["NORMAL_VOL+SIDEWAY"]["no_entry_events"] == 6
    assert late_combo["UNKNOWN+UNKNOWN"]["late_window_blocks"] == 10
    assert timing_combo["NORMAL_VOL+SIDEWAY"]["closest_candidate_bucket"] == "180s+"
    assert summary["unknown_regime_coverage"]["unknown_combo_share"] == pytest.approx(10 / 22, abs=0.0001)
    assert summary["unknown_regime_coverage"]["classification"] == "UNKNOWN_COVERAGE_GAP"
    assert any("regime_replay events=22" in line for line in format_terminal_summary(evaluation, verbose=True))


def test_session_evaluator_reports_regime_coverage_audit(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:00:00Z",
                "event_type": "decision",
                "source_module": "polymarket.trader",
                "payload": {
                    "market_id": "complete-decision",
                    "volatility_regime": "NORMAL_VOL",
                    "trend_regime": "SIDEWAY",
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:00:01Z",
                "event_type": "decision",
                "source_module": "polymarket.trader",
                "payload": {
                    "market_id": "missing-decision",
                    "source_module": "polymarket.trader",
                    "display": {"skip_reason": "time_unsafe"},
                },
            },
        ],
    )
    _write_market_snapshot_log(
        tmp_path,
        [
            {
                "timestamp_utc": f"{DATE}T10:01:00Z",
                "event_type": "market_snapshot",
                "source_module": "polymarket.trader",
                "payload": {
                    "market_id": "snapshot-display",
                    "display": {
                        "volatility_regime": "EXTREME_VOL",
                        "trend_regime": "BREAKOUT",
                    },
                },
            },
            {
                "timestamp_utc": f"{DATE}T10:01:01Z",
                "event_type": "market_snapshot",
                "source_module": "legacy.snapshot",
                "payload": {
                    "market_id": "snapshot-unknown",
                    "volatility_regime": "UNKNOWN",
                    "trend_regime": "UNKNOWN",
                },
            },
        ],
    )
    _write_quant_category_log(
        tmp_path,
        "execution_log",
        [
            {
                "timestamp_utc": f"{DATE}T10:02:00Z",
                "event_type": "execution",
                "source_module": "polymarket.trader",
                "payload": {"market_id": "execution-missing"},
            }
        ],
    )
    _write_quant_category_log(
        tmp_path,
        "risk_log",
        [
            {
                "timestamp_utc": f"{DATE}T10:03:00Z",
                "event_type": "risk_event",
                "source_module": "polymarket.trader",
                "payload": {"risk_mode": "NORMAL"},
            }
        ],
    )
    _write_quant_category_log(
        tmp_path,
        "system_health",
        [
            {
                "timestamp_utc": f"{DATE}T10:04:00Z",
                "event_type": "system_health",
                "source_module": "polymarket.trader",
                "payload": {"connected": True},
            }
        ],
    )
    _write_quant_category_log(
        tmp_path,
        "trade_journal",
        [
            {
                "timestamp_utc": f"{DATE}T10:05:00Z",
                "event_type": "trade_open",
                "source_module": "polymarket.trader",
                "payload": {
                    "market_id": "trade-open",
                    "volatility_regime": "HIGH_VOL",
                    "trend_regime": "SIDEWAY",
                },
            }
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        load_offline_reports=True,
    )

    audit = evaluation.regime_coverage_audit
    assert audit["total_events_seen"] == 8
    assert audit["regime_not_applicable_events"] == 2
    assert audit["regime_not_applicable_by_jsonl_category"]["system_health"] == 1
    assert audit["regime_not_applicable_by_jsonl_category"]["risk_log"] == 1
    assert audit["regime_not_applicable_reasons"]["system_health_regime_agnostic"] == 1
    assert audit["regime_not_applicable_reasons"]["portfolio_risk_event_without_market"] == 1
    assert audit["total_events_checked"] == 6
    assert audit["events_with_complete_regime"] == 3
    assert audit["events_missing_volatility_regime"] == 3
    assert audit["events_missing_trend_regime"] == 3
    assert audit["events_missing_both"] == 3
    assert audit["unknown_regime_share"] == pytest.approx(3 / 6, abs=0.0001)
    assert audit["missing_by_event_type"]["decision"]["missing_both"] == 1
    assert audit["missing_by_event_type"]["market_snapshot"]["missing_both"] == 1
    assert audit["missing_by_jsonl_category"]["execution_log"]["missing_both"] == 1
    assert audit["missing_by_source_module"]["polymarket.trader"]["missing_both"] == 2
    assert audit["available_regime_field_paths"]["payload.volatility_regime"] == 2
    assert audit["available_regime_field_paths"]["payload.display.trend_regime"] == 1
    assert audit["suspected_missing_payload_sources"][0]["missing_both_events"] >= 1
    assert any("decision_log" in item for item in audit["recommended_field_mapping_fixes"])
    assert any("system_health" in item for item in audit["recommended_field_mapping_fixes"])
    assert any("regime_coverage_audit checked=6" in line for line in format_terminal_summary(evaluation, verbose=True))


def test_multi_session_spread_summary_classifies_structural_limitation() -> None:
    summary = build_multi_session_spread_summary([
        _multi_session_payload(
            date="2026-05-07",
            spread_diagnosis="SPREAD_NEVER_NORMALIZED",
            recovery_rate=0.0,
            normalization_seconds=None,
            avg_velocity=0.0001,
            trend="SIDEWAY",
            volatility="NORMAL_VOL",
        ),
        _multi_session_payload(
            date="2026-05-08",
            spread_diagnosis="SPREAD_NORMALIZED_TOO_LATE",
            recovery_rate=0.25,
            normalization_seconds=70,
            avg_velocity=0.0002,
            trend="BREAKOUT",
            volatility="HIGH_VOL",
        ),
        _multi_session_payload(
            date="2026-05-09",
            spread_diagnosis="SPREAD_NEVER_NORMALIZED",
            recovery_rate=0.0,
            normalization_seconds=None,
            avg_velocity=0.0001,
            trend="REVERSAL_RISK",
            volatility="EXTREME_VOL",
        ),
    ])

    multi = summary["multi_session_spread_summary"]
    assert multi["sessions_counted"] == 3
    assert multi["no_entry_frequency"] == pytest.approx(1.0)
    assert multi["late_window_frequency"] == pytest.approx(1.0)
    assert multi["avg_spread_velocity"] == pytest.approx(0.000133)
    assert summary["spread_diagnosis_frequency"]["SPREAD_NEVER_NORMALIZED"] == 2
    assert summary["candidate_gap_diagnosis_frequency"]["SPREAD_TOO_WIDE"] == 3
    assert summary["structural_vs_regime_dependent_interpretation"] == "STRUCTURAL_SPREAD_LIMITATION"
    assert summary["spread_failure_clusters"][0]["sessions"] >= 1
    assert summary["repeated_no_entry_patterns"][0]["sessions"] >= 1


def test_multi_session_spread_summary_classifies_regime_dependent_limitation() -> None:
    summary = build_multi_session_spread_summary([
        _multi_session_payload(
            date="2026-05-07",
            spread_diagnosis="SPREAD_RECOVERED_BEFORE_CUTOFF",
            recovery_rate=1.0,
            normalization_seconds=160,
            avg_velocity=0.0007,
            closest_candidate_seconds=150,
            closest_bucket="120-180s",
            trend="SIDEWAY",
            volatility="NORMAL_VOL",
        ),
        _multi_session_payload(
            date="2026-05-08",
            spread_diagnosis="REGIME_DEPENDENT_SPREAD_BEHAVIOR",
            recovery_rate=0.0,
            normalization_seconds=None,
            avg_velocity=-0.0001,
            closest_candidate_seconds=80,
            closest_bucket="45-90s",
            trend="BREAKOUT",
            volatility="EXTREME_VOL",
        ),
    ])

    matrix = summary["regime_spread_matrix"]
    assert summary["structural_vs_regime_dependent_interpretation"] == "REGIME_DEPENDENT_SPREAD_LIMITATION"
    assert matrix["trend_family"]["SIDEWAY"]["recovery_rate"] == pytest.approx(0.25)
    assert matrix["trend_family"]["TREND"]["recovery_rate"] == pytest.approx(0.0)
    assert matrix["volatility_family"]["NORMAL_VOL"]["recovery_rate"] == pytest.approx(0.25)
    assert matrix["volatility_family"]["EXTREME_VOL"]["recovery_rate"] == pytest.approx(0.0)
    assert summary["spread_normalization_by_regime"]["combo_regime"]["SIDEWAY+NORMAL_VOL"]["avg_normalization_seconds"] == pytest.approx(160)
    assert summary["candidate_timing_by_regime"]["combo_regime"]["BREAKOUT+EXTREME_VOL"]["avg_closest_candidate_seconds"] == pytest.approx(80)


def test_multi_session_spread_summary_classifies_micro_bankroll_sensitivity() -> None:
    summary = build_multi_session_spread_summary([
        _multi_session_payload(
            date="2026-05-07",
            spread_diagnosis="SPREAD_NORMALIZED_TOO_LATE",
            recovery_rate=0.25,
            normalization_seconds=70,
            bankroll_family="MICRO",
            bankroll_mode="MICRO_SURVIVAL",
        ),
        _multi_session_payload(
            date="2026-05-08",
            spread_diagnosis="SPREAD_RECOVERED_BEFORE_CUTOFF",
            entered=1,
            recovery_rate=1.0,
            normalization_seconds=180,
            bankroll_family="STANDARD",
            bankroll_mode="NORMAL",
            trend="BREAKOUT",
            volatility="NORMAL_VOL",
            late_window_blocks=0,
        ),
    ])

    assert summary["structural_vs_regime_dependent_interpretation"] == "MICRO_BANKROLL_SENSITIVITY"
    assert summary["multi_session_spread_summary"]["no_entry_sessions"] == 1
    assert summary["repeated_no_entry_patterns"][0]["bankroll_mode"] == "MICRO_SURVIVAL"


def test_multi_session_spread_summary_requires_multiple_sessions() -> None:
    summary = build_multi_session_spread_summary([
        _multi_session_payload(
            date="2026-05-07",
            spread_diagnosis="SPREAD_NEVER_NORMALIZED",
        )
    ])

    assert summary["structural_vs_regime_dependent_interpretation"] == "INSUFFICIENT_MULTI_SESSION_DATA"
    assert summary["multi_session_spread_summary"]["sessions_counted"] == 1


def test_session_evaluator_reports_micro_survival_bankroll_mode() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(
            bankroll_tier_id="T0_MICRO_SEED",
            bankroll_tier_name="Micro Seed",
            bankroll_family="MICRO",
            bankroll_risk_profile="seed_protection",
            bankroll_tier_locked=False,
            bankroll_hysteresis_active=False,
            bankroll_mode="MICRO_SURVIVAL",
            micro_survival_active=True,
            micro_position_size=0.05,
        ),
        replay_report=_replay_report(),
        date=DATE,
        load_offline_reports=False,
    )

    lines = format_terminal_summary(evaluation, verbose=True)

    assert evaluation.risk_blocks["bankroll_mode"] == "MICRO_SURVIVAL"
    assert evaluation.risk_blocks["micro_survival_active"] is True
    assert evaluation.risk_blocks["micro_position_size"] == pytest.approx(0.05)
    assert evaluation.risk_blocks["bankroll_tier_id"] == "T0_MICRO_SEED"
    assert evaluation.risk_blocks["bankroll_tier_name"] == "Micro Seed"
    assert evaluation.risk_blocks["bankroll_family"] == "MICRO"
    assert evaluation.risk_blocks["bankroll_risk_profile"] == "seed_protection"
    assert any("bankroll_mode=MICRO_SURVIVAL" in line for line in lines)
    assert any("micro_survival_active=true" in line for line in lines)
    assert any("tier_id=T0_MICRO_SEED" in line for line in lines)
    assert any("family=MICRO" in line for line in lines)


def test_session_evaluator_fails_on_execution_failures() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(skipped_trade_reasons={"order_submit_failed": 1}),
        replay_report=_replay_report(
            execution_failure_count=1,
            top_skip_reasons=[["order_submit_failed", 1]],
            cutoff_block_count=0,
            adaptive_cutoff_denied_count=0,
        ),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_FAIL
    assert evaluation.primary_bottleneck == "execution_failures"
    assert "execution_failures_present" in evaluation.fail_reasons


def test_session_evaluator_keeps_no_entry_safety_rejections_as_caution() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(skipped_trade_reasons={"order_intent:risk_not_approved": 8}),
        replay_report=_replay_report(
            top_skip_reasons=[["order_intent:risk_not_approved", 8]],
            execution_failure_count=0,
            cutoff_block_count=0,
            adaptive_cutoff_denied_count=0,
        ),
        no_entry_report={
            "total_scanned": 8,
            "total_entered": 0,
            "total_skipped": 8,
            "skip_reason_counts": {"order_intent:risk_not_approved": 8},
            "execution_failure_count": 0,
            "order_submit_attempt_count": 0,
            "paper_fill_count": 0,
            "market_data_quality": {},
        },
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_CAUTION
    assert evaluation.execution_summary["execution_failure_count"] == 0
    assert "execution_failures_present" not in evaluation.fail_reasons


def test_session_evaluator_does_not_use_total_execution_events_as_failures() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(
            total_markets_scanned=130,
            skipped_trade_reasons={"time_unsafe": 70, "orderbook_unavailable": 40, "risk_plan_zero": 20},
        ),
        replay_report=_replay_report(
            skipped_decisions=130,
            top_skip_reasons=[["time_unsafe", 70], ["orderbook_unavailable", 40], ["risk_plan_zero", 20]],
            execution_failure_count=0,
            cutoff_block_count=70,
            adaptive_cutoff_denied_count=70,
        ),
        no_entry_report=_no_entry_report(execution_events_loaded=170, execution_failure_count=0),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_CAUTION
    assert evaluation.primary_bottleneck == "cutoff"
    assert evaluation.bottleneck_scores["execution_failures"] == 0
    assert evaluation.execution_summary["execution_events_loaded"] == 170
    assert evaluation.execution_summary["execution_failure_count"] == 0


def test_session_evaluator_prefers_corrected_replay_failure_count_over_no_entry_total_events_regression() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(
            total_markets_scanned=130,
            skipped_trade_reasons={"time_unsafe": 70, "orderbook_unavailable": 40, "risk_plan_zero": 20},
        ),
        replay_report=_replay_report(
            skipped_decisions=130,
            top_skip_reasons=[["time_unsafe", 70], ["orderbook_unavailable", 40], ["risk_plan_zero", 20]],
            execution_failure_count=0,
            cutoff_block_count=70,
            adaptive_cutoff_denied_count=70,
        ),
        no_entry_report=_no_entry_report(execution_events_loaded=170, execution_failure_count=170),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_CAUTION
    assert evaluation.primary_bottleneck == "cutoff"
    assert evaluation.bottleneck_scores["execution_failures"] == 0
    assert evaluation.execution_summary["execution_failure_count"] == 0


def test_session_health_uses_offline_paper_evidence_when_runtime_summary_counters_are_stale() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(
            total_markets_scanned=990,
            total_trades_simulated=15,
            paper_orders_created=0,
            paper_fills=0,
            paper_exits=0,
            simulated_pnl=0.0,
        ),
        replay_report=_replay_report(
            total_trades=15,
            gross_pnl=0.00450312,
            skipped_decisions=975,
            top_skip_reasons=[["time_unsafe", 492], ["risk_plan_zero", 178]],
            execution_failure_count=0,
            cutoff_block_count=507,
            adaptive_cutoff_denied_count=0,
        ),
        no_entry_report=_no_entry_report(
            total_scanned=990,
            total_entered=15,
            total_skipped=975,
            skip_reason_counts={"time_unsafe": 492, "risk_plan_zero": 178},
            execution_events_loaded=3260,
            execution_failure_count=0,
            order_submit_attempt_count=30,
            paper_fill_count=30,
        ),
        date=DATE,
        load_offline_reports=False,
    )

    health = evaluation.health_summary
    assert health["entered"] == 15
    assert health["paper_orders_created"] == 30
    assert health["paper_fills"] == 30
    assert health["paper_exits"] == 15
    assert health["gross_pnl"] == pytest.approx(0.00450312)
    assert health["runtime_summary_paper_orders_created"] == 0
    assert health["runtime_summary_paper_fills"] == 0
    assert health["runtime_summary_paper_exits"] == 0
    assert health["paper_orders_created_source"] == "execution_summary.order_submit_attempt_count"
    assert health["paper_fills_source"] == "execution_summary.paper_fill_count"
    assert health["paper_exits_source"] == "replay_report.trade_journal_trade_close"
    assert evaluation.execution_summary["order_submit_attempt_count"] == 30
    assert evaluation.execution_summary["paper_fill_count"] == 30


def test_session_evaluator_regression_high_execution_events_zero_failures() -> None:
    evaluation = evaluate_session_runtime(
        no_entry_report=_no_entry_report(
            execution_events_loaded=170,
            execution_failure_count=0,
            skip_reason_counts={"orderbook_unavailable": 90, "risk_plan_zero": 40},
        ),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_CAUTION
    assert evaluation.primary_bottleneck == "market_readiness"
    assert evaluation.bottleneck_scores["execution_failures"] == 0
    assert "execution_failures_present" not in evaluation.fail_reasons


def test_session_evaluator_reports_orderbook_reason_breakdown_without_counting_warmup_as_unavailable() -> None:
    evaluation = evaluate_session_runtime(
        replay_report=_replay_report(
            top_skip_reasons=[["orderbook_unavailable", 12]],
            skipped_decisions=12,
            cutoff_block_count=0,
            adaptive_cutoff_denied_count=0,
            orderbook_readiness_reasons=[
                ["warmup_pending", 7],
                ["missing_token_id", 3],
                ["stale_book", 2],
                ["clob_rate_limited", 4],
            ],
            clob_error_categories=[["clob_rate_limited", 4]],
            clob_exception_types=[["HTTPError", 4]],
            clob_error_classes=[["rate_limited", 4]],
            clob_backoff_active_count=4,
            clob_circuit_open_count=2,
            max_clob_error_rate=0.75,
            clob_recovery_count=1,
        ),
        no_entry_report=_no_entry_report(
            total_scanned=12,
            total_skipped=12,
            skip_reason_counts={"orderbook_unavailable": 12},
            market_data_quality={},
        ),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.orderbook_readiness["warmup_pending_count"] == 7
    assert evaluation.orderbook_readiness["orderbook_unavailable_count"] == 7
    assert evaluation.orderbook_readiness["stale_data_count"] == 2
    assert ["warmup_pending", 7] in evaluation.orderbook_readiness["reason_breakdown"]
    assert ["clob_rate_limited", 4] in evaluation.orderbook_readiness["reason_breakdown"]
    assert ["clob_rate_limited", 4] in evaluation.orderbook_readiness["clob_error_categories"]
    assert ["HTTPError", 4] in evaluation.orderbook_readiness["clob_exception_types"]
    assert ["rate_limited", 4] in evaluation.orderbook_readiness["clob_error_classes"]
    assert evaluation.orderbook_readiness["clob_backoff_active_count"] == 4
    assert evaluation.orderbook_readiness["clob_circuit_open_count"] == 2
    assert evaluation.orderbook_readiness["max_clob_error_rate"] == pytest.approx(0.75)
    assert evaluation.orderbook_readiness["clob_recovery_count"] == 1


def test_session_evaluator_reports_empty_book_recovery_metrics() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(),
        replay_report=_replay_report(
            empty_book_recovery_attempted_count=3,
            empty_book_recovery_success_count=2,
            empty_book_recovery_failed_count=1,
            empty_book_recovery_retry_count=4,
            liquidity_states=[["HEALTHY", 2], ["EMPTY", 1]],
        ),
        date=DATE,
        load_offline_reports=False,
    )

    lines = format_terminal_summary(evaluation, verbose=True)

    assert evaluation.orderbook_readiness["empty_book_recovery_attempted"] == 3
    assert evaluation.orderbook_readiness["empty_book_recovery_success"] == 2
    assert evaluation.orderbook_readiness["empty_book_recovery_failed"] == 1
    assert evaluation.orderbook_readiness["empty_book_recovery_retry_count"] == 4
    assert ["HEALTHY", 2] in evaluation.orderbook_readiness["liquidity_states"]
    assert any("empty_recovery_success=2" in line for line in lines)


def test_session_evaluator_reports_liquidity_recovery_grace_from_jsonl(tmp_path: Path) -> None:
    _write_decision_log(
        tmp_path,
        [
            {
                "timestamp_utc": "2026-05-09T12:00:00Z",
                "event_type": "decision",
                "payload": {
                    "decision_type": "skipped",
                    "empty_book_recovery_research_mode": True,
                    "liquidity_recovery_grace_entered": True,
                    "liquidity_recovery_grace_success": True,
                    "liquidity_recovery_grace_failed": False,
                    "recovery_wait_seconds": 0.1,
                    "recovered_before_cutoff": True,
                    "candidate_survived_recovery": True,
                    "recovery_exit_reason": "recovered",
                    "recovery_branch_candidate_seen": True,
                    "recovery_branch_mode_disabled": False,
                    "recovery_branch_preempted_by_cutoff": False,
                    "recovery_branch_enter_condition_failed": False,
                },
            },
            {
                "timestamp_utc": "2026-05-09T12:01:00Z",
                "event_type": "decision",
                "payload": {
                    "decision_type": "skipped",
                    "empty_book_recovery_research_mode": True,
                    "liquidity_recovery_grace_entered": True,
                    "liquidity_recovery_grace_success": False,
                    "liquidity_recovery_grace_failed": True,
                    "recovery_wait_seconds": 0.3,
                    "recovered_before_cutoff": False,
                    "candidate_survived_recovery": False,
                    "recovery_exit_reason": "empty_book_retries_exhausted",
                    "recovery_branch_candidate_seen": True,
                    "recovery_branch_mode_disabled": False,
                    "recovery_branch_preempted_by_cutoff": False,
                    "recovery_branch_enter_condition_failed": False,
                    "recovery_branch_skipped_reason": "empty_book_retries_exhausted",
                },
            },
            {
                "timestamp_utc": "2026-05-09T12:02:00Z",
                "event_type": "decision",
                "payload": {
                    "decision_type": "skipped",
                    "empty_book_recovery_research_mode": True,
                    "liquidity_recovery_grace_entered": False,
                    "liquidity_recovery_grace_success": False,
                    "liquidity_recovery_grace_failed": False,
                    "recovery_wait_seconds": 0.0,
                    "recovery_exit_reason": "",
                    "recovery_branch_candidate_seen": True,
                    "recovery_branch_mode_disabled": True,
                    "recovery_branch_preempted_by_cutoff": True,
                    "recovery_branch_enter_condition_failed": True,
                    "recovery_branch_skipped_reason": "hard_close_zone",
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(),
        quant_data_dir=tmp_path,
        realtime_log_dir=tmp_path / "realtime",
        date=DATE,
    )
    lines = format_terminal_summary(evaluation, verbose=True)
    orderbook = evaluation.orderbook_readiness

    assert orderbook["liquidity_recovery_research_mode_events"] == 3
    assert orderbook["recovery_branch_candidate_seen"] == 3
    assert orderbook["recovery_branch_mode_disabled"] == 1
    assert orderbook["recovery_branch_preempted_by_cutoff"] == 1
    assert orderbook["recovery_branch_enter_condition_failed"] == 1
    assert orderbook["liquidity_recovery_grace_entered"] == 2
    assert orderbook["liquidity_recovery_grace_success"] == 1
    assert orderbook["liquidity_recovery_grace_failed"] == 1
    assert orderbook["recovery_wait_seconds"] == pytest.approx(0.2)
    assert orderbook["max_recovery_wait_seconds"] == pytest.approx(0.3)
    assert orderbook["recovered_before_cutoff"] == 1
    assert orderbook["candidate_survived_recovery"] == 1
    assert orderbook["recovery_exit_reason"] == "recovered"
    assert ["empty_book_retries_exhausted", 1] in orderbook["recovery_exit_reasons"]
    assert ["hard_close_zone", 1] in orderbook["recovery_branch_skipped_reasons"]
    assert any("recovery_branch_seen=3" in line for line in lines)
    assert any("liquidity_grace_entered=2" in line for line in lines)


def test_session_evaluator_reports_micro_adaptive_timing_metrics() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(),
        replay_report=_replay_report(
            micro_timing_allowed_count=2,
            micro_timing_denied_count=1,
            micro_timing_branch_entered_count=3,
            micro_timing_candidate_count=3,
            micro_timing_denied_reasons=[["hard_close_zone", 1]],
            micro_timing_branch_skipped_reasons=[["non_micro_tier", 4], ["live_mode", 1]],
        ),
        date=DATE,
        load_offline_reports=False,
    )

    lines = format_terminal_summary(evaluation, verbose=True)

    assert evaluation.cutoff_behavior["micro_timing_allowed_count"] == 2
    assert evaluation.cutoff_behavior["micro_timing_denied_count"] == 1
    assert evaluation.cutoff_behavior["micro_timing_branch_entered_count"] == 3
    assert evaluation.cutoff_behavior["micro_timing_candidate_count"] == 3
    assert ["hard_close_zone", 1] in evaluation.cutoff_behavior["micro_timing_denied_reasons"]
    assert ["non_micro_tier", 4] in evaluation.cutoff_behavior["micro_timing_branch_skipped_reasons"]
    assert any("micro_timing_allowed=2" in line for line in lines)
    assert any("micro_branch_entered=3" in line for line in lines)
    assert any("micro_candidates=3" in line for line in lines)
    assert evaluation.execution_summary["execution_failure_count"] == 0


def test_session_evaluator_no_entry_only_legacy_total_events_regression_is_caution() -> None:
    evaluation = evaluate_session_runtime(
        no_entry_report=_no_entry_report(
            execution_events_loaded=170,
            execution_failure_count=170,
            skip_reason_counts={"time_unsafe": 80, "risk_plan_zero": 50},
        ),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_CAUTION
    assert evaluation.primary_bottleneck == "cutoff"
    assert evaluation.execution_summary["execution_failure_count"] == 0


def test_cli_recomputes_execution_failures_from_execution_jsonl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    quant_dir = tmp_path / "quant_data"
    realtime_log_dir = tmp_path / "realtime_logs"
    _write_execution_log(
        quant_dir,
        (
            [{"event": "market_analysis_exception"} for _ in range(168)]
            + [{"event": "exit_submit_failed", "reason": "forced_exit"} for _ in range(2)]
        ),
        flat_name=True,
    )
    monkeypatch.setattr(
        session_runtime_evaluator,
        "_safe_analyze_replay",
        lambda **_: (
            _FakeAnalyzerReport(
                _replay_report(
                    skipped_decisions=130,
                    top_skip_reasons=[["time_unsafe", 70], ["orderbook_unavailable", 40], ["risk_plan_zero", 20]],
                    execution_failure_count=170,
                    cutoff_block_count=70,
                    adaptive_cutoff_denied_count=70,
                )
            ),
            None,
        ),
    )
    monkeypatch.setattr(
        session_runtime_evaluator,
        "_safe_analyze_no_entries",
        lambda **_: (
            _FakeAnalyzerReport(_no_entry_report(execution_events_loaded=170, execution_failure_count=170)),
            None,
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "session_runtime_evaluator",
            "--date",
            DATE,
            "--quant-data-dir",
            str(quant_dir),
            "--realtime-log-dir",
            str(realtime_log_dir),
        ],
    )

    exit_code = session_runtime_evaluator.main()
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "SESSION_STATUS=CAUTION PRIMARY_BOTTLENECK=cutoff" in output
    assert "execution_failures=0" in output
    assert "Execution failures were present" not in output


def test_cli_recomputed_execution_failures_still_counts_real_submit_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    quant_dir = tmp_path / "quant_data"
    realtime_log_dir = tmp_path / "realtime_logs"
    _write_execution_log(
        quant_dir,
        [{"event": "order_submit_failed", "error": "submit rejected by API"}],
        flat_name=True,
    )
    monkeypatch.setattr(
        session_runtime_evaluator,
        "_safe_analyze_replay",
        lambda **_: (
            _FakeAnalyzerReport(
                _replay_report(
                    skipped_decisions=0,
                    top_skip_reasons=[],
                    execution_failure_count=0,
                    cutoff_block_count=0,
                    adaptive_cutoff_denied_count=0,
                )
            ),
            None,
        ),
    )
    monkeypatch.setattr(
        session_runtime_evaluator,
        "_safe_analyze_no_entries",
        lambda **_: (
            _FakeAnalyzerReport(
                _no_entry_report(
                    total_scanned=0,
                    total_skipped=0,
                    skip_reason_counts={},
                    execution_events_loaded=1,
                    execution_failure_count=0,
                )
            ),
            None,
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "session_runtime_evaluator",
            "--date",
            DATE,
            "--quant-data-dir",
            str(quant_dir),
            "--realtime-log-dir",
            str(realtime_log_dir),
        ],
    )

    exit_code = session_runtime_evaluator.main()
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "SESSION_STATUS=FAIL PRIMARY_BOTTLENECK=execution_failures" in output
    assert "execution_failures=1" in output


def test_time_filter_since_excludes_earlier_events(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    _write_decision_log(
        quant_dir,
        [
            _decision_event(f"{DATE}T01:00:00Z", "clob_http_error"),
            _decision_event(f"{DATE}T02:00:00Z", "time_unsafe"),
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
        since="01:30",
    )

    assert evaluation.skip_summary["skip_reason_counts"] == {"time_unsafe": 1}
    assert evaluation.time_filter["range"] == f"{DATE}T01:30:00Z..{DATE}T23:59:59Z"
    assert evaluation.reports_used["no_entry_report"] is False


def test_session_evaluator_filters_events_by_run_id_and_writes_run_scoped_report(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    target = _decision_event(f"{DATE}T01:00:00Z", "time_unsafe")
    target["run_id"] = "run/target"
    other = _decision_event(f"{DATE}T02:00:00Z", "clob_http_error")
    other["run_id"] = "run-other"
    missing = _decision_event(f"{DATE}T03:00:00Z", "risk_plan_zero")
    _write_decision_log(quant_dir, [target, other, missing])

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
        run_id="run/target",
    )
    report_path = write_session_runtime_report(evaluation, report_dir=tmp_path / "reports")

    assert evaluation.run_id == "run/target"
    assert evaluation.skip_summary["skip_reason_counts"] == {"time_unsafe": 1}
    assert evaluation.time_filter["run_id"] == "run/target"
    assert evaluation.time_filter["run_id_applied"] is True
    assert report_path == tmp_path / "reports" / f"session_runtime_evaluation_{DATE}_run_run_target.json"


def test_session_evaluator_cli_lists_run_ids(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    quant_dir = tmp_path / "quant_data"
    first = _decision_event(f"{DATE}T01:00:00Z", "time_unsafe")
    first["run_id"] = "run-a"
    second = _decision_event(f"{DATE}T02:00:00Z", "clob_http_error")
    second["run_id"] = "run-b"
    _write_decision_log(quant_dir, [first, second])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "session_runtime_evaluator",
            "--date",
            DATE,
            "--quant-data-dir",
            str(quant_dir),
            "--realtime-log-dir",
            str(tmp_path / "realtime_logs"),
            "--list-run-ids",
        ],
    )

    assert session_runtime_evaluator.main() == 0

    output = capsys.readouterr().out
    assert "Available run IDs" in output
    assert "run_id=run-a event_count=1" in output
    assert "run_id=run-b event_count=1" in output


def test_session_evaluator_extracts_bankroll_tier_visibility_from_runtime_events(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    _write_decision_log(
        quant_dir,
        [
            {
                **_decision_event(f"{DATE}T01:00:00Z", "time_unsafe"),
                "payload": {
                    **_decision_event(f"{DATE}T01:00:00Z", "time_unsafe")["payload"],
                    "bankroll_tier_id": "T0_MICRO_SEED",
                    "bankroll_tier_name": "Micro Seed",
                    "bankroll_family": "MICRO",
                    "bankroll_risk_profile": "seed_protection",
                    "bankroll_mode": "MICRO_SURVIVAL",
                    "micro_survival_active": True,
                    "micro_position_size": 0.05,
                },
            },
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
    )
    lines = format_terminal_summary(evaluation)

    assert evaluation.risk_blocks["bankroll_tier_id"] == "T0_MICRO_SEED"
    assert evaluation.risk_blocks["bankroll_tier_name"] == "Micro Seed"
    assert evaluation.risk_blocks["bankroll_family"] == "MICRO"
    assert evaluation.risk_blocks["bankroll_risk_profile"] == "seed_protection"
    assert evaluation.risk_blocks["bankroll_mode"] == "MICRO_SURVIVAL"
    assert evaluation.risk_blocks["micro_survival_active"] is True
    assert evaluation.risk_blocks["micro_position_size"] == pytest.approx(0.05)
    assert any("tier_id=T0_MICRO_SEED" in line for line in lines)
    assert any("micro_survival_active=true" in line for line in lines)


def test_time_filter_until_excludes_later_events(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    _write_decision_log(
        quant_dir,
        [
            _decision_event(f"{DATE}T01:00:00Z", "clob_http_error"),
            _decision_event(f"{DATE}T02:00:00Z", "time_unsafe"),
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
        until="01:30",
    )

    assert evaluation.skip_summary["skip_reason_counts"] == {"clob_http_error": 1}
    assert evaluation.orderbook_readiness["orderbook_unavailable_count"] == 1


def test_time_filter_since_until_together(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    _write_decision_log(
        quant_dir,
        [
            _decision_event(f"{DATE}T01:00:00Z", "clob_http_error"),
            _decision_event(f"{DATE}T02:00:00Z", "time_unsafe"),
            _decision_event(f"{DATE}T03:00:00Z", "risk_plan_zero"),
        ],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
        since="01:30",
        until="02:30",
    )

    assert evaluation.skip_summary["skip_reason_counts"] == {"time_unsafe": 1}
    assert evaluation.time_filter["semantics"] == "half_open_since_inclusive_until_exclusive"


def test_time_filter_no_matching_events_returns_caution_no_data(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant_data"
    _write_decision_log(
        quant_dir,
        [_decision_event(f"{DATE}T01:00:00Z", "clob_http_error")],
    )

    evaluation = evaluate_session_runtime(
        date=DATE,
        quant_data_dir=quant_dir,
        realtime_log_dir=tmp_path / "realtime_logs",
        since="03:00",
        until="04:00",
    )

    assert evaluation.session_status == DECISION_CAUTION
    assert evaluation.primary_bottleneck == "no_data"
    assert "no_data_for_time_filter" in evaluation.caution_reasons
    assert evaluation.health_summary["skipped"] == 0


def test_cli_main_path_uses_time_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    quant_dir = tmp_path / "quant_data"
    report_dir = tmp_path / "reports"
    _write_decision_log(
        quant_dir,
        [
            _decision_event(f"{DATE}T01:00:00Z", "clob_http_error"),
            _decision_event(f"{DATE}T02:00:00Z", "time_unsafe"),
        ],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "session_runtime_evaluator",
            "--date",
            DATE,
            "--quant-data-dir",
            str(quant_dir),
            "--realtime-log-dir",
            str(tmp_path / "realtime_logs"),
            "--report-dir",
            str(report_dir),
            "--since",
            "01:30",
            "--write-report",
        ],
    )

    exit_code = session_runtime_evaluator.main()
    output = capsys.readouterr().out
    report_path = report_dir / f"session_runtime_evaluation_{DATE}_0130_to_end.json"
    saved = json.loads(report_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert f"filter={DATE}T01:30:00Z..{DATE}T23:59:59Z" in output
    assert "top_skip_reasons=[['time_unsafe', 1]]" in output
    assert "clob_http_error" not in output
    assert saved["time_filter"]["since"] == "01:30"
    assert saved["time_filter"]["timezone"] == "UTC"


def test_session_evaluator_still_fails_for_real_submit_cancel_or_system_execution_errors() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(skipped_trade_reasons={"order_submit_failed": 1}),
        replay_report=_replay_report(
            execution_failure_count=3,
            top_skip_reasons=[["order_submit_failed", 1]],
            cutoff_block_count=0,
            adaptive_cutoff_denied_count=0,
        ),
        no_entry_report=_no_entry_report(
            total_scanned=0,
            total_skipped=0,
            skip_reason_counts={},
            execution_events_loaded=3,
            execution_failure_count=3,
        ),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_FAIL
    assert evaluation.primary_bottleneck == "execution_failures"
    assert evaluation.execution_summary["execution_failure_count"] == 3
    assert "execution_failures_present" in evaluation.fail_reasons


def test_session_evaluator_passes_healthy_session() -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(
            total_markets_scanned=20,
            total_trades_simulated=5,
            paper_orders_created=5,
            paper_fills=5,
            skipped_trade_reasons={},
        ),
        replay_report=_replay_report(
            total_trades=5,
            skipped_decisions=0,
            top_skip_reasons=[],
            cutoff_block_count=0,
            adaptive_cutoff_denied_count=0,
        ),
        date=DATE,
        load_offline_reports=False,
    )

    assert evaluation.session_status == DECISION_PASS
    assert evaluation.primary_bottleneck == "healthy_no_signal"


def test_session_evaluator_formats_and_writes_report(tmp_path: Path) -> None:
    evaluation = evaluate_session_runtime(
        session_summary=_session_summary(),
        replay_report=_replay_report(),
        date=DATE,
        load_offline_reports=False,
    )
    lines = format_terminal_summary(evaluation)
    report_path = write_session_runtime_report(evaluation, report_dir=tmp_path)

    assert any("SESSION_STATUS=CAUTION" in line for line in lines)
    assert any("PRIMARY_BOTTLENECK=cutoff" in line for line in lines)
    assert any("cutoff_summary " in line for line in lines)
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["primary_bottleneck"] == "cutoff"
    assert saved["session_status"] == DECISION_CAUTION
    assert evaluation.to_telegram_payload()["primary_bottleneck"] == "cutoff"


def test_trader_session_evaluator_hook_is_fail_soft(caplog: pytest.LogCaptureFixture) -> None:
    trader = PolymarketTrader.__new__(PolymarketTrader)
    trader.settings = SimpleNamespace(paper_trading=True, quant_data_dir="missing-quant-data")
    trader._paper_enabled = lambda: True
    trader.log_quant_summary = lambda force=False: None
    trader.paper_session_summary = lambda: _session_summary()
    emitted: list[dict] = []
    trader._emit_quant_event = lambda _method, payload: emitted.append(payload) or True
    trader._runtime_mode = lambda: "paper"

    with caplog.at_level("INFO"):
        trader.log_paper_session_summary()

    assert any("SESSION_STATUS=" in record.message for record in caplog.records)
    assert emitted and emitted[0]["event"] == "session_runtime_evaluation"
