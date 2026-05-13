import json
from pathlib import Path

from tools.candidate_path_observability import (
    build_candidate_path_observability_report,
    main,
    write_candidate_path_observability_report,
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
    event_type: str = "market_snapshot",
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


def test_candidate_path_observability_reconstructs_mfe_mae_path(tmp_path):
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
                    "market_readiness_state": "ready",
                    "fair_value": 0.60,
                    "market_price": 0.56,
                    "ev_after_spread": 0.02,
                    "yes_bid": 0.55,
                    "yes_ask": 0.57,
                    "no_bid": 0.43,
                    "no_ask": 0.45,
                },
            ),
            _event(
                "2026-05-08T12:00:10Z",
                {
                    "candidate_id": "candidate-a",
                    "signal_id": "signal-a",
                    "market_id": "btc-market",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "market_readiness_state": "ready",
                    "fair_value": 0.63,
                    "market_price": 0.56,
                    "ev_after_spread": 0.06,
                    "yes_bid": 0.56,
                    "yes_ask": 0.58,
                },
            ),
            _event(
                "2026-05-08T12:00:20Z",
                {
                    "candidate_id": "candidate-a",
                    "signal_id": "signal-a",
                    "market_id": "btc-market",
                    "lifecycle_phase": "ACTIVE_INVENTORY_TRADING",
                    "market_readiness_state": "ready",
                    "fair_value": 0.57,
                    "market_price": 0.58,
                    "ev_after_spread": -0.01,
                    "candidate_block_stage": "post_ev",
                    "candidate_block_reason": "risk_plan_zero",
                    "candidate_survival_ms": 20000,
                    "candidate_expiry_reason": "risk_block",
                },
            ),
        ],
    )

    report = build_candidate_path_observability_report(
        base_dir=base_dir,
        date=DATE,
        run_id="run-target",
    )

    assert report["scope"] == "offline_research_replay_only"
    assert report["schema_version"] == "candidate_path_observability_v1"
    assert report["does_not_claim_profitability"] is True
    assert report["does_not_authorize_runtime_decisions"] is True
    assert report["does_not_infer_execution"] is True
    assert report["does_not_infer_inventory_truth"] is True
    assert report["continuity_chains_loaded"] == 1
    assert report["summary"]["candidate_paths"] == 1
    assert report["summary"]["path_confidence_counts"]["HIGH_DIRECT"] == 1
    assert report["summary"]["edge_expansion_chain_count"] == 1
    assert report["summary"]["edge_decay_chain_count"] == 1

    path = report["candidate_paths"][0]
    assert path["path_confidence"] == "HIGH_DIRECT"
    assert path["path_observability_quality"] == "OBSERVABLE_EV_PATH"
    assert path["peak_favorable_move"] == 0.04
    assert path["peak_adverse_move"] == -0.03
    assert path["peak_ev_after_birth"] == 0.06
    assert path["worst_ev_after_birth"] == -0.01
    assert path["candidate_terminal_path_state"] == "TERMINAL_EDGE_DECAYED"
    assert len(path["mfe_candidate_path"]) == 3
    assert len(path["mae_candidate_path"]) == 3
    assert path["mfe_candidate_path"][1]["ev_delta_from_birth"] == 0.04
    assert path["mae_candidate_path"][2]["ev_delta_from_birth"] == -0.03


def test_candidate_path_observability_labels_weak_proxy_paths(tmp_path):
    base_dir = tmp_path / "quant_data"
    _write_jsonl(
        base_dir,
        "decision_log",
        [
            _event(
                "2026-05-08T12:00:00Z",
                {
                    "decision": "skip",
                    "market_id": "proxy-market",
                    "seconds_remaining": 220,
                    "normalized_skip_reason": "orderbook_unavailable",
                },
                event_type="candidate_decision",
            ),
        ],
    )
    _write_jsonl(
        base_dir,
        "market_snapshots",
        [
            _event(
                "2026-05-08T12:00:01Z",
                {
                    "market_id": "proxy-market",
                    "seconds_remaining": 219,
                    "fair_value": 0.61,
                    "market_price": 0.59,
                },
            ),
        ],
    )

    report = build_candidate_path_observability_report(base_dir=base_dir, date=DATE, run_id="run-target")
    path = report["candidate_paths"][0]

    assert path["path_confidence"] in {"LOW_PROXY", "LOW_EVIDENCE", "INSUFFICIENT"}
    assert path["low_confidence_label"] == "LOW_CONFIDENCE_PATH_CONTINUITY"
    assert path["path_observability_quality"] in {"PRICE_ONLY_PROXY_PATH", "SPARSE_SINGLE_POINT_PATH", "INSUFFICIENT_PATH_FIELDS"}
    assert report["research_questions"]["continuity_path_confidence"]["guardrail"] == "evidence only; no fake fills, inferred execution, or inventory truth"


def test_write_candidate_path_observability_report_includes_sanitized_run_id(tmp_path):
    report = {
        "date_from": DATE,
        "date_to": DATE,
        "run_id": "run/id:target",
        "time_filter": {"since": "12:00", "until": "12:05", "applied": True},
        "summary": {},
        "candidate_paths": [],
    }

    path = write_candidate_path_observability_report(report, report_dir=tmp_path / "reports")

    assert path.name == "candidate_path_observability_2026-05-08_1200_to_1205_run_run_id_target.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["run_id"] == "run/id:target"


def test_candidate_path_observability_cli_writes_report(tmp_path, monkeypatch, capsys):
    base_dir = tmp_path / "quant_data"
    report_dir = tmp_path / "reports"
    _write_jsonl(
        base_dir,
        "market_snapshots",
        [
            _event(
                "2026-05-08T12:00:01Z",
                {
                    "candidate_id": "candidate-cli",
                    "signal_id": "signal-cli",
                    "market_id": "btc-market",
                    "lifecycle_phase": "OPENING_SCAN",
                    "fair_value": 0.61,
                    "market_price": 0.58,
                    "candidate_block_stage": "pre_ev",
                    "candidate_block_reason": "no_probability_model_output",
                },
            )
        ],
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate_path_observability",
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
    assert "Candidate Path Observability" in output
    assert (report_dir / "candidate_path_observability_2026-05-08_run_run-target.json").exists()
