from __future__ import annotations

from datetime import datetime, timezone

import pytest

import tools.canonical.canonical_trade_table_v1 as ctt
from tools.canonical.canonical_trade_table_v1 import build_canonical_trade_table, enrich_canonical_rows_v1_1


RUN_ID = "run-canonical-test"
KEY = "condition-1|1770000000|BTC|YES|token-yes"


def _event(event_type: str, timestamp: str, payload: dict, *, run_id: str = RUN_ID) -> dict:
    return {
        "timestamp_utc": timestamp,
        "event_type": event_type,
        "mode": "paper",
        "run_id": run_id,
        "source_module": "test",
        "schema_version": "1.0",
        "payload": payload,
    }


def _open(**overrides) -> dict:
    payload = {
        "paper_trade_replay_key": KEY,
        "ticker": "BTC",
        "asset": "BTC",
        "outcome": "YES",
        "side": "BUY",
        "entry_price": 0.50,
        "size": 2.0,
        "confidence": 0.75,
    }
    payload.update(overrides)
    return _event("trade_open", "2026-06-01T00:00:00Z", payload)


def _close(**overrides) -> dict:
    payload = {
        "paper_trade_replay_key": KEY,
        "ticker": "BTC",
        "asset": "BTC",
        "outcome": "YES",
        "side": "YES",
        "entry_price": 0.50,
        "exit_price": 0.60,
        "size": 2.0,
        "pnl_usdc": 0.20,
        "exit_reason": "TP",
        "trade_result": "TP",
    }
    payload.update(overrides)
    return _event("trade_close", "2026-06-01T00:00:20Z", payload)


def _decision(**overrides) -> dict:
    payload = {
        "paper_trade_replay_key": KEY,
        "asset": "BTC",
        "side": "YES",
        "lifecycle_phase": "OPENING_SCAN",
        "market_regime": "TREND_UP",
        "expected_value": 0.08,
        "true_probability": 0.64,
        "fair_value": 0.64,
        "confidence": 0.75,
    }
    payload.update(overrides)
    return _event("decision", "2026-06-01T00:00:00Z", payload)


def _execution(**overrides) -> dict:
    payload = {
        "paper_trade_replay_key": KEY,
        "event": "paper_fill",
        "quote_age_at_submit_ms": 250,
        "quote_age_at_fill_ms": 275,
        "liquidity_state": "ACCEPTABLE",
    }
    payload.update(overrides)
    return _event("execution", "2026-06-01T00:00:01Z", payload)


def _path(checkpoint: int | str, price: float) -> dict:
    return _event(
        "trade_path_checkpoint",
        "2026-06-01T00:00:15Z",
        {
            "paper_trade_replay_key": KEY,
            "checkpoint_elapsed_s": checkpoint,
            "current_mark_price": price,
        },
    )


def test_pairs_trade_open_and_close_into_one_completed_trade() -> None:
    result = build_canonical_trade_table(
        trade_events=[_open(), _close()],
        decision_events=[_decision()],
        execution_events=[_execution()],
        path_truth_events=[_path(15, 0.55), _path("event_end", 0.60)],
    )

    assert result.summary["completed_trade_count"] == 1
    row = result.rows[0]
    assert row["canonical_trade_id"].startswith("ct_")
    assert row["paper_trade_replay_key"] == KEY
    assert row["asset"] == "BTC"
    assert row["side"] == "YES"
    assert row["pnl_usdc"] == pytest.approx(0.20)
    assert row["row_completeness"] == "FULL"
    assert row["join_confidence"] == "DIRECT"
    assert row["decision_joined"] is True
    assert row["execution_joined"] is True
    assert row["path_truth_joined"] is True


def test_duplicate_key_quarantines_completed_row() -> None:
    result = build_canonical_trade_table(
        trade_events=[_open(), _open(entry_price=0.51), _close()],
        decision_events=[_decision()],
        execution_events=[_execution()],
        path_truth_events=[],
    )

    row = result.rows[0]
    assert result.summary["duplicate_key_count"] == 1
    assert row["quarantine_flag"] is True
    assert "duplicate_open" in row["quarantine_reason"]
    assert row["row_completeness"] == "UNTRUSTWORTHY"


def test_pnl_recomputation_mismatch_quarantines_row() -> None:
    result = build_canonical_trade_table(
        trade_events=[_open(), _close(pnl_usdc=0.99)],
        decision_events=[_decision()],
        execution_events=[_execution()],
        path_truth_events=[],
    )

    row = result.rows[0]
    assert row["pnl_recomputed"] == pytest.approx(0.20)
    assert row["quarantine_flag"] is True
    assert "pnl_mismatch" in row["quarantine_reason"]


def test_missing_decision_join_keeps_row_partial_not_fabricated() -> None:
    result = build_canonical_trade_table(
        trade_events=[_open(), _close()],
        decision_events=[],
        execution_events=[_execution()],
        path_truth_events=[],
    )

    row = result.rows[0]
    assert row["decision_joined"] is False
    assert row["row_completeness"] == "PARTIAL"
    assert row["expected_value"] is None
    assert result.summary["decision_join_rate"] == pytest.approx(0.0)


def test_missing_path_truth_join_has_no_mfe_mae() -> None:
    result = build_canonical_trade_table(
        trade_events=[_open(), _close()],
        decision_events=[_decision()],
        execution_events=[_execution()],
        path_truth_events=[],
    )

    row = result.rows[0]
    assert row["path_truth_joined"] is False
    assert row["mfe_price"] is None
    assert row["mae_price"] is None
    assert result.summary["path_truth_join_rate"] == pytest.approx(0.0)


def test_executable_pnl_is_never_fabricated() -> None:
    result = build_canonical_trade_table(
        trade_events=[_open(size=3.0), _close(size=3.0, pnl_usdc=0.30)],
        decision_events=[_decision()],
        execution_events=[_execution()],
        path_truth_events=[_path(15, 0.58)],
    )

    row = result.rows[0]
    assert row["signal_pnl"] == pytest.approx(0.30)
    assert row["executable_pnl"] is None
    assert row["executable_pnl_status"].startswith("BLOCKED")
    assert result.summary["executable_pnl_approved_count"] == 0


def test_row_completeness_reconstructed_when_outcome_is_derived() -> None:
    result = build_canonical_trade_table(
        trade_events=[_open(), _close(exit_reason=None, trade_result=None)],
        decision_events=[_decision()],
        execution_events=[_execution()],
        path_truth_events=[],
    )

    row = result.rows[0]
    assert row["outcome_win_loss"] == "WIN"
    assert row["row_completeness"] == "RECONSTRUCTED"
    assert "outcome_reconstructed" in row["quarantine_reason"]


def test_timestamp_validation_requires_entry_before_exit() -> None:
    result = build_canonical_trade_table(
        trade_events=[
            _open(),
            _event("trade_close", "2026-05-31T23:59:59Z", _close()["payload"]),
        ],
        decision_events=[_decision()],
        execution_events=[_execution()],
        path_truth_events=[],
    )

    row = result.rows[0]
    assert row["quarantine_flag"] is True
    assert "entry_exit_order_invalid" in row["quarantine_reason"]


def _canonical_row(**overrides) -> dict:
    row = {
        "canonical_trade_id": "ct-existing",
        "run_id": RUN_ID,
        "paper_trade_replay_key": KEY,
        "asset": "BTC",
        "side": "YES",
        "entry_ts": "2026-06-01T00:00:00Z",
        "exit_ts": "2026-06-01T00:00:20Z",
        "hold_seconds": 20.0,
        "lifecycle_phase": "FINAL_DERISK",
        "regime": "COMPRESSION",
        "pnl_usdc": 0.20,
        "signal_pnl": 0.20,
        "executable_pnl": None,
        "executable_pnl_status": "BLOCKED_NO_TRUE_EXECUTABLE_DATA",
        "row_completeness": "FULL",
    }
    row.update(overrides)
    return row


def test_v1_1_enriches_entry_risk_mode_from_order_submit() -> None:
    rows = [_canonical_row()]
    execution_events = [
        _event(
            "execution",
            "2026-06-01T00:00:02Z",
            {
                "paper_trade_replay_key": KEY,
                "event": "order_submit_attempt",
                "risk_mode": "DEFENSIVE",
                "bankroll_mode": "MICRO_SURVIVAL",
                "bankroll_tier_id": "T0_MICRO_SEED",
                "bankroll_family": "MICRO",
                "bankroll_risk_profile": "seed_protection",
                "micro_survival_active": True,
                "available_risk_budget": 1.20,
                "current_exposure": 0.05,
                "order_submit_ts": "2026-06-01T00:00:02Z",
                "limit_price": 0.52,
                "size": 0.10,
                "quote_age_at_submit_ms": 125,
                "risk_plan_present": True,
            },
        )
    ]

    enriched, summary = enrich_canonical_rows_v1_1(rows, execution_events=execution_events, risk_events=[])

    assert len(enriched) == 1
    row = enriched[0]
    assert row["risk_mode_entry"] == "DEFENSIVE"
    assert row["bankroll_mode_entry"] == "MICRO_SURVIVAL"
    assert row["bankroll_tier_entry"] == "T0_MICRO_SEED"
    assert row["bankroll_family_entry"] == "MICRO"
    assert row["risk_profile_entry"] == "seed_protection"
    assert row["micro_survival_active_entry"] is True
    assert row["available_risk_budget_entry"] == 1.20
    assert row["current_exposure_entry"] == 0.05
    assert row["entry_risk_join_confidence"] == "DIRECT"
    assert row["entry_risk_join_source"] == "execution_log.order_submit_attempt"
    assert summary["rows_with_risk_mode_entry"] == 1


def test_v1_1_uses_trade_open_for_bankroll_fields_when_submit_lacks_them() -> None:
    enriched, summary = enrich_canonical_rows_v1_1(
        [_canonical_row()],
        execution_events=[
            _event(
                "execution",
                "2026-06-01T00:00:02Z",
                {
                    "paper_trade_replay_key": KEY,
                    "event": "order_submit_attempt",
                    "risk_mode": "NORMAL",
                },
            )
        ],
        risk_events=[],
        trade_events=[
            _event(
                "trade_open",
                "2026-06-01T00:00:00Z",
                {
                    "paper_trade_replay_key": KEY,
                    "bankroll_mode": "MICRO_SURVIVAL",
                    "bankroll_tier_id": "T0_MICRO_SEED",
                    "bankroll_family": "MICRO",
                    "bankroll_risk_profile": "seed_protection",
                    "micro_survival_active": True,
                    "available_risk_budget": 1.2,
                    "current_exposure": 0.05,
                },
            )
        ],
    )

    row = enriched[0]
    assert row["risk_mode_entry"] == "NORMAL"
    assert row["bankroll_mode_entry"] == "MICRO_SURVIVAL"
    assert row["bankroll_tier_entry"] == "T0_MICRO_SEED"
    assert row["bankroll_family_entry"] == "MICRO"
    assert row["risk_profile_entry"] == "seed_protection"
    assert row["micro_survival_active_entry"] is True
    assert row["available_risk_budget_entry"] == 1.2
    assert row["current_exposure_entry"] == 0.05
    assert summary["rows_with_bankroll_mode_entry"] == 1


def test_v1_1_handles_missing_risk_lineage_fail_soft() -> None:
    enriched, summary = enrich_canonical_rows_v1_1([_canonical_row()], execution_events=[], risk_events=[])

    row = enriched[0]
    assert row["risk_mode_entry"] == "unknown"
    assert row["bankroll_mode_entry"] == "unknown"
    assert row["entry_risk_join_confidence"] == "MISSING"
    assert row["entry_risk_join_source"] == "missing"
    assert row["execution_join_confidence"] == "MISSING"
    assert summary["missing_risk_lineage_count"] == 1
    assert summary["missing_execution_lineage_count"] == 1


def test_v1_1_enriches_submit_execution_fields() -> None:
    enriched, _summary = enrich_canonical_rows_v1_1(
        [_canonical_row()],
        execution_events=[
            _event(
                "execution",
                "2026-06-01T00:00:02Z",
                {
                    "paper_trade_replay_key": KEY,
                    "event": "order_submit_attempt",
                    "order_submit_ts": "2026-06-01T00:00:02.123Z",
                    "price": 0.51,
                    "size": 0.11,
                    "quote_age_at_submit_ms": 333,
                },
            )
        ],
        risk_events=[],
    )

    row = enriched[0]
    assert row["entry_submit_event_type"] == "order_submit_attempt"
    assert row["entry_submit_ts"] == "2026-06-01T00:00:02.123Z"
    assert row["entry_submit_price"] == 0.51
    assert row["entry_submit_size"] == 0.11
    assert row["entry_quote_age_ms"] == 333
    assert row["execution_join_confidence"] == "DIRECT"


def test_v1_1_does_not_mutate_input_rows_or_fabricate_executable_pnl() -> None:
    original = _canonical_row()
    snapshot = dict(original)

    enriched, summary = enrich_canonical_rows_v1_1([original], execution_events=[], risk_events=[])

    assert original == snapshot
    assert enriched[0]["executable_pnl"] is None
    assert enriched[0]["executable_pnl_status"].startswith("BLOCKED")
    assert summary["total_rows"] == 1
    assert len(enriched) == 1


def test_v1_2_trade_open_lifecycle_wins_over_late_decision_lifecycle() -> None:
    assert hasattr(ctt, "enrich_canonical_rows_v1_2")
    row = _canonical_row(
        entry_ts="2026-06-01T00:00:00Z",
        exit_ts="2026-06-01T00:00:20Z",
        lifecycle_phase="FINAL_DERISK",
    )

    enriched, summary = ctt.enrich_canonical_rows_v1_2(
        [row],
        trade_events=[
            _open(lifecycle_phase="OPENING_SCAN"),
            _close(lifecycle_phase="ACTIVE_INVENTORY_TRADING"),
        ],
        execution_events=[
            _execution(event="paper_fill", lifecycle_phase="ACTIVE_INVENTORY_TRADING")
        ],
        decision_events=[
            _event(
                "decision",
                "2026-06-01T00:04:50Z",
                {
                    "paper_trade_replay_key": KEY,
                    "lifecycle_phase": "FINAL_DERISK",
                },
            ),
        ],
    )

    result = enriched[0]
    assert result["trade_open_lifecycle_phase"] == "OPENING_SCAN"
    assert result["execution_fill_lifecycle_phase"] == "ACTIVE_INVENTORY_TRADING"
    assert result["decision_join_lifecycle_phase"] == "FINAL_DERISK"
    assert result["canonical_entry_lifecycle_phase"] == "OPENING_SCAN"
    assert result["canonical_entry_lifecycle_source"] == "trade_journal.trade_open"
    assert result["lifecycle_truth_status"] == "LATE_DECISION_JOIN"
    assert result["lifecycle_conflict_flag"] is True
    assert "trade_open_vs_decision_lifecycle" in result["lifecycle_conflict_reason"]
    assert result["decision_join_ts_delta_from_open_s"] == pytest.approx(290.0)
    assert result["decision_join_ts_delta_from_close_s"] == pytest.approx(270.0)
    assert summary["total_rows"] == 1
    assert summary["rows_with_trade_open_lifecycle_phase"] == 1
    assert summary["rows_with_execution_fill_lifecycle_phase"] == 1
    assert summary["rows_with_decision_join_lifecycle_phase"] == 1
    assert summary["lifecycle_conflict_count"] == 1


def test_v1_2_detects_decision_join_after_trade_close() -> None:
    assert hasattr(ctt, "enrich_canonical_rows_v1_2")
    enriched, summary = ctt.enrich_canonical_rows_v1_2(
        [_canonical_row(entry_ts="2026-06-01T00:00:00Z", exit_ts="2026-06-01T00:00:20Z")],
        trade_events=[_open(lifecycle_phase="OPENING_SCAN"), _close()],
        execution_events=[],
        decision_events=[
            _event(
                "decision",
                "2026-06-01T00:04:50Z",
                {
                    "paper_trade_replay_key": KEY,
                    "lifecycle_phase": "FINAL_DERISK",
                },
            )
        ],
    )

    row = enriched[0]
    assert row["decision_join_ts"] == "2026-06-01T00:04:50Z"
    assert row["decision_join_ts_delta_from_open_s"] == pytest.approx(290.0)
    assert row["decision_join_ts_delta_from_close_s"] == pytest.approx(270.0)
    assert row["lifecycle_truth_status"] == "LATE_DECISION_JOIN"
    assert row["lifecycle_conflict_flag"] is True
    assert "late_decision_join" in row["lifecycle_conflict_reason"]
    assert summary["late_decision_join_count"] == 1


def test_v1_2_uses_execution_fill_when_trade_open_lifecycle_is_missing() -> None:
    assert hasattr(ctt, "enrich_canonical_rows_v1_2")
    enriched, _summary = ctt.enrich_canonical_rows_v1_2(
        [_canonical_row(lifecycle_phase="FINAL_DERISK")],
        trade_events=[_open()],
        execution_events=[
            _execution(event="paper_fill", lifecycle_phase="ACTIVE_INVENTORY_TRADING")
        ],
        decision_events=[_decision(lifecycle_phase="FINAL_DERISK")],
    )

    row = enriched[0]
    assert row["trade_open_lifecycle_phase"] is None
    assert row["canonical_entry_lifecycle_phase"] == "ACTIVE_INVENTORY_TRADING"
    assert row["canonical_entry_lifecycle_source"] == "execution_log.paper_fill"


def test_v1_2_preserves_completed_trade_count_and_does_not_fabricate_executable_pnl() -> None:
    assert hasattr(ctt, "enrich_canonical_rows_v1_2")
    original = _canonical_row(executable_pnl=None, executable_pnl_status="BLOCKED_NO_TRUE_EXECUTABLE_DATA")
    snapshot = dict(original)

    enriched, summary = ctt.enrich_canonical_rows_v1_2(
        [original],
        trade_events=[_open(lifecycle_phase="OPENING_SCAN"), _close()],
        execution_events=[],
        decision_events=[],
    )

    assert original == snapshot
    assert len(enriched) == 1
    assert summary["total_rows"] == 1
    assert enriched[0]["executable_pnl"] is None
    assert enriched[0]["executable_pnl_status"].startswith("BLOCKED")
