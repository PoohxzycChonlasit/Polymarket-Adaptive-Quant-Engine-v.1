import json
import tempfile
from pathlib import Path
from tools.quant_intelligence_engine import (
    EvidenceCollector,
    EvidenceCompiler,
    EvidenceStore,
    ExperimentRegistry,
    FeatureRegistry,
    MetricRegistry,
    RecommendationStore,
    EvidenceUnit
)


def test_empty_logs():
    """Verify collector and compiler behave properly with no logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        collector = EvidenceCollector(base_path)
        
        # Collect from non-existent directories
        events = collector.collect_events("trade_journal", ["2026-06-27"])
        assert events == []

        compiler = EvidenceCompiler()
        units = compiler.compile([], [], [], [], [])
        assert units == []


def test_corrupted_rows():
    """Verify collector handles corrupted/invalid JSON rows cleanly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        journal_dir = base_path / "trade_journal"
        journal_dir.mkdir(parents=True, exist_ok=True)
        
        # Write valid + invalid rows
        log_file = journal_dir / "2026-06-27.jsonl"
        with open(log_file, "w") as f:
            f.write('{"event_type": "trade_open", "run_id": "r1", "trade_id": "t1"}\n')
            f.write('{"event_type": "trade_open", "run_id": "r2", corrupted_json_here}\n')
            f.write('{"event_type": "trade_close", "run_id": "r1", "trade_id": "t1"}\n')

        collector = EvidenceCollector(base_path)
        events = collector.collect_events("trade_journal", ["2026-06-27"])
        # Should skip the corrupted row, returning 2 valid events
        assert len(events) == 2
        assert events[0]["trade_id"] == "t1"
        assert events[1]["trade_id"] == "t1"


def test_duplicated_events():
    """Verify event deduplication works correctly."""
    collector = EvidenceCollector(Path("."))
    
    events = [
        {"event_id": "id1", "run_id": "r1", "payload": {"val": 1}},
        {"event_id": "id1", "run_id": "r1", "payload": {"val": 1}}, # explicit duplicate
        {"run_id": "r2", "payload": {"val": 2}}, # dynamic ID generation duplicate below
        {"run_id": "r2", "payload": {"val": 2}},
    ]
    
    deduped = collector.deduplicate_events(events)
    assert len(deduped) == 2
    assert deduped[0]["run_id"] == "r1"
    assert deduped[1]["run_id"] == "r2"


def test_legacy_rows_and_mixed_schemas():
    """Verify legacy logs with missing size_sharp fields get safe fallbacks."""
    opens = [
        # Normal modern row
        {"event_type": "trade_open", "run_id": "run1", "payload": {"trade_id": "t1", "condition_id": "c1", "ticker": "BTC"}},
        # Legacy row missing fields
        {"event_type": "trade_open", "run_id": "run2", "payload": {"trade_id": "t2"}},
    ]
    
    closes = [
        {"event_type": "trade_close", "run_id": "run1", "payload": {"trade_id": "t1", "pnl": 0.50}},
        {"event_type": "trade_close", "run_id": "run2", "payload": {"trade_id": "t2", "pnl": -0.20}},
    ]

    decisions = [
        {"run_id": "run1", "payload": {"size_sharp": 3.2, "bankroll_tier_id": "T0"}},
        # Legacy decision without size_sharp or bankroll_tier_id (lacks predictors)
        {"run_id": "run2", "payload": {}},
    ]

    compiler = EvidenceCompiler()
    units = compiler.compile(opens, closes, decisions, [], [])
    
    assert len(units) == 2
    
    # Modern row compilation checks
    assert units[0].trade_id == "t1"
    assert units[0].predictors["size_sharp"] == 3.2
    assert units[0].predictors["size_sharp_bucket"] == "ELITE"
    assert units[0].predictors["capital_state"] == "T0"
    assert units[0].outcome["win_status"] == "WIN"

    # Legacy row checks
    assert units[1].trade_id == "t2"
    assert units[1].predictors["size_sharp"] is None
    assert units[1].predictors["size_sharp_bucket"] == "UNKNOWN"
    assert units[1].predictors["capital_state"] == "UNKNOWN"
    assert units[1].outcome["win_status"] == "LOSS"


def test_incremental_rebuild_and_checkpoint():
    """Verify checkpoint state is updated and skips unchanged logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        journal_dir = base_path / "trade_journal"
        journal_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = journal_dir / "2026-06-27.jsonl"
        with open(log_file, "w") as f:
            f.write('{"event_type": "trade_open", "run_id": "r1", "trade_id": "t1"}\n')

        checkpoint = {"processed_files": {}}
        collector = EvidenceCollector(base_path)
        
        # Pass 1: Reads file
        events1 = collector.collect_events("trade_journal", ["2026-06-27"], checkpoint)
        assert len(events1) == 1
        assert "trade_journal/2026-06-27" in checkpoint["processed_files"]

        # Pass 2: Skips file (unchanged)
        events2 = collector.collect_events("trade_journal", ["2026-06-27"], checkpoint)
        assert len(events2) == 0


def test_replay_determinism():
    """Verify compiling same inputs produces identical evidence IDs."""
    opens = [{"event_type": "trade_open", "run_id": "r1", "payload": {"trade_id": "t1"}}]
    closes = [{"event_type": "trade_close", "run_id": "r1", "payload": {"trade_id": "t1", "pnl": 0.50}}]
    
    compiler = EvidenceCompiler()
    units1 = compiler.compile(opens, closes, [], [], [])
    units2 = compiler.compile(opens, closes, [], [], [])
    
    assert len(units1) == 1
    assert len(units2) == 1
    assert units1[0].evidence_id == units2[0].evidence_id


def test_metric_and_experiment_registries():
    """Verify statistical metrics calculation and counterfactual simulation."""
    units = [
        EvidenceUnit("ev1", "t1", "m1", "BTC", "CRYPTO", "2026-06-27T00:00:00Z", {"size_sharp": 3.5, "capital_state": "T0"}, {}, {"resolved_side": "YES", "fill_price": 0.5, "exit_price": 0.6, "realized_pnl": 0.1, "win_status": "WIN"}),
        EvidenceUnit("ev2", "t2", "m2", "BTC", "CRYPTO", "2026-06-27T00:01:00Z", {"size_sharp": 1.5, "capital_state": "T1"}, {}, {"resolved_side": "YES", "fill_price": 0.5, "exit_price": 0.4, "realized_pnl": -0.1, "win_status": "LOSS"}),
    ]

    metrics = MetricRegistry()
    assert metrics.calculate_win_rate(units) == 0.50
    assert metrics.calculate_expectancy(units) == 0.00
    assert metrics.calculate_max_drawdown(units) == 0.1  # t1 goes +0.1, t2 goes -0.1 (dd=0.1)
    assert metrics.calculate_profit_factor(units) == 1.0

    registry = ExperimentRegistry()
    # Filter for size_sharp >= 2.0 (filters out t2, leaves only profitable t1)
    record = registry.run_experiment("hyp_size_sharp_cutoff", units, {"min_size_sharp": 2.0})
    assert record["accepted"] is True
    assert record["results"]["expectancy_delta"] == 0.1  # expectancy goes from 0.0 to 0.1
