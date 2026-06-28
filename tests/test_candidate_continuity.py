import json
from pathlib import Path

from tools.unknown.candidate_continuity import (
    build_candidate_continuity_report,
    main,
    write_candidate_continuity_report,
)


DATE = "2026-05-08"


def _write_jsonl(base_dir: Path, category: str, events: list[dict]) -> None:
    path = base_dir / category / f"{DATE}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n",
        encoding="utf-8",
    )


def _event(
    timestamp: str,
    payload: dict,
    *,
    run_id: str = "run-target",
    event_type: str = "candidate_decision",
    asset: str = "BTC",
) -> dict:
    return {
        "timestamp_utc": timestamp,
        "event_type": event_type,
        "mode": "paper",
        "asset": asset,
        "run_id": run_id,
        "source_module": "synthetic_test",
        "schema_version": "1.0",
        "payload": payload,
    }


def test_candidate_continuity_chains_status_and_schema(tmp_path):
    base_dir = tmp_path / "quant_data"
    _write_jsonl(
        base_dir,
        "market_snapshots",
        [
            _event(
                "2026-05-08T12:00:00Z",
                {
                    "candidate_id": "candidate-a",
                    "signal_id": "signal-a",
                    "market_id": "btc-market",
                    "lifecycle_phase": "OPENING_SCAN",
                    "market_readiness_state": "warming",
                    "token_ready_at": "2026-05-08T12:00:00Z",
                },
                event_type="market_snapshot",
            ),
            _event(
                "2026-05-08T12:00:05Z",
                {
                    "candidate_id": "candidate-b",
                    "signal_id": "signal-b",
                    "market_id": "eth-market",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "market_readiness_state": "ready",
                    "orderbook_state_classification": "ready",
                },
                event_type="market_snapshot",
                asset="ETH",
            ),
        ],
    )
    _write_jsonl(
        base_dir,
        "decision_log",
        [
            _event(
                "2026-05-08T12:00:20Z",
                {
                    "decision": "skip",
                    "candidate_id": "candidate-a",
                    "signal_id": "signal-a",
                    "market_id": "btc-market",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "fair_value": 0.62,
                    "market_price": 0.58,
                    "true_probability": 0.62,
                    "ev_after_spread": 0.03,
                    "candidate_block_stage": "post_ev",
                    "candidate_block_reason": "risk_plan_zero",
                    "candidate_survival_ms": 20000,
                    "candidate_expiry_reason": "risk_block",
                    "market_readiness_state": "ready",
                },
            ),
            _event(
                "2026-05-08T12:00:25Z",
                {
                    "decision": "skip",
                    "market_id": "proxy-market",
                    "seconds_remaining": 220,
                    "normalized_skip_reason": "orderbook_unavailable",
                    "orderbook_unavailable_reason": "empty_book",
                },
            ),
            _event(
                "2026-05-08T12:00:30Z",
                {
                    "decision": "skip",
                    "candidate_id": "candidate-other-run",
                    "lifecycle_phase": "OPENING_SCAN",
                },
                run_id="run-other",
            ),
        ],
    )

    report = build_candidate_continuity_report(
        base_dir=base_dir,
        date=DATE,
        run_id="run-target",
    )

    assert report["scope"] == "offline_research_replay_only"
    assert report["schema_version"] == "candidate_continuity_v1"
    assert report["does_not_claim_profitability"] is True
    assert report["does_not_authorize_runtime_decisions"] is True
    assert report["does_not_infer_inventory_truth"] is True
    assert report["events_loaded"] == 4
    assert report["candidate_events"] == 4
    assert report["summary"]["candidate_continuity_chains"] == 3
    assert report["summary"]["continuity_status_counts"]["TERMINATED"] == 1
    assert report["summary"]["continuity_status_counts"]["DISAPPEARED"] == 1
    assert report["summary"]["continuity_status_counts"]["ORPHAN_OR_PROXY"] == 1
    assert report["summary"]["candidate_last_seen_phase_counts"]["ACTIVE_INVENTORY_TRADING"] >= 2
    assert report["summary"]["pre_ev_vs_post_ev_survival"]["post_ev_chain_count"] >= 1
    assert report["research_questions"]["replay_truth_impact"]["guardrail"] == "evidence only; no runtime execution decision authority"

    chains = {chain["candidate_id"] or chain["identity_inference"]: chain for chain in report["chains"]}
    candidate_a = chains["candidate-a"]
    assert candidate_a["continuity_chain_id"].startswith("cc-")
    assert candidate_a["continuity_status"] == "TERMINATED"
    assert candidate_a["candidate_terminal_state"] == "EXPIRED"
    assert candidate_a["continuity_break_reason"] == "expired"
    assert candidate_a["candidate_last_seen_phase"] == "ACTIVE_INVENTORY_TRADING"
    assert candidate_a["candidate_survival_ms"] == 20000
    assert candidate_a["candidate_survival_inference"] == "direct_observed"
    assert candidate_a["continuity_confidence"] == "HIGH_DIRECT"
    assert candidate_a["lifecycle_transition_sequence"] == [
        {"from": "OPENING_SCAN", "to": "ACTIVE_INVENTORY_TRADING"}
    ]
    assert "continuity_break_reason" in candidate_a
    assert "continuity_confidence" in candidate_a


def test_candidate_continuity_detects_phase_regression_break(tmp_path):
    base_dir = tmp_path / "quant_data"
    _write_jsonl(
        base_dir,
        "market_snapshots",
        [
            _event(
                "2026-05-08T12:00:00Z",
                {
                    "candidate_id": "candidate-regression",
                    "lifecycle_phase": "PROFIT_MANAGEMENT",
                    "market_readiness_state": "ready",
                },
                event_type="market_snapshot",
            ),
            _event(
                "2026-05-08T12:00:10Z",
                {
                    "candidate_id": "candidate-regression",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "market_readiness_state": "ready",
                },
                event_type="market_snapshot",
            ),
        ],
    )

    report = build_candidate_continuity_report(base_dir=base_dir, date=DATE, run_id="run-target")
    chain = report["chains"][0]

    assert chain["continuity_status"] == "CONTINUITY_BREAK"
    assert chain["continuity_break_reason"] == "lifecycle_phase_regression"
    assert chain["lifecycle_degradation"]["phase_regression_observed"] is True
    assert report["summary"]["continuity_break_reason_counts"]["lifecycle_phase_regression"] == 1


def test_write_candidate_continuity_report_includes_sanitized_run_id(tmp_path):
    report = {
        "date_from": DATE,
        "date_to": DATE,
        "run_id": "run/id:target",
        "time_filter": {"since": "12:00", "until": "12:05", "applied": True},
        "summary": {},
        "chains": [],
    }

    path = write_candidate_continuity_report(report, report_dir=tmp_path / "reports")

    assert path.name == "candidate_continuity_2026-05-08_1200_to_1205_run_run_id_target.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["run_id"] == "run/id:target"


def test_candidate_continuity_cli_writes_report(tmp_path, monkeypatch, capsys):
    base_dir = tmp_path / "quant_data"
    report_dir = tmp_path / "reports"
    _write_jsonl(
        base_dir,
        "decision_log",
        [
            _event(
                "2026-05-08T12:00:01Z",
                {
                    "decision": "skip",
                    "candidate_id": "candidate-cli",
                    "signal_id": "signal-cli",
                    "lifecycle_phase": "OPENING_SCAN",
                    "candidate_block_stage": "pre_ev",
                    "candidate_block_reason": "no_probability_model_output",
                },
            )
        ],
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate_continuity",
            "--date",
            DATE,
            "--run-id",
            "run-target",
            "--base-dir",
            str(base_dir),
            "--report-dir",
            str(report_dir),
        ],
    )

    assert main() == 0
    output = capsys.readouterr().out
    assert "Candidate Continuity Diagnostics" in output
    assert (report_dir / "candidate_continuity_2026-05-08_run_run-target.json").exists()
