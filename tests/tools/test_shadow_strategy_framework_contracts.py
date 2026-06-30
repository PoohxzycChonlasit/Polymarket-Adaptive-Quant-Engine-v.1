"""
Tests for tools/shadow_strategy_framework/contracts.py

Validates the offline schema-only contracts for the Shadow Strategy Evaluation
Framework. These tests must never import runtime modules and must be safe to
run without a Polymarket connection, wallet, or live config.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.shadow_strategy_framework.contracts import (
    REPLAY_ROW_SCHEMA_VERSION,
    REQUIRED_REPLAY_ROW_CONTAINER_KEYS,
    STRATEGY_DECISION_SCHEMA_VERSION,
    STRATEGY_SUMMARY_REQUIRED_METRIC_KEYS,
    PATH_TRUTH_SCORING_ONLY_FIELDS,
    EvidenceDecision,
    EvidenceGrade,
    PluginFamily,
    ReplayQuality,
    ReplayRow,
    Recommendation,
    StrategyAction,
    StrategyDecision,
    StrategyPluginMetadata,
    make_minimal_replay_row,
    make_minimal_strategy_decision,
    validate_required_replay_row_containers,
)

# Project root for subprocess tests (2 levels above tests/tools/)
_PROJECT_ROOT = Path(__file__).parents[2]


# ── Test 1: module import cleanliness ─────────────────────────────────────────

def test_contracts_module_imports_cleanly() -> None:
    """contracts.py imports without error and exposes all public names."""
    assert REPLAY_ROW_SCHEMA_VERSION == "shadow_replay_row.v0_1"
    assert STRATEGY_DECISION_SCHEMA_VERSION == "strategy_decision.v0_1"
    assert isinstance(REQUIRED_REPLAY_ROW_CONTAINER_KEYS, frozenset)
    assert isinstance(PATH_TRUTH_SCORING_ONLY_FIELDS, frozenset)
    assert isinstance(STRATEGY_SUMMARY_REQUIRED_METRIC_KEYS, frozenset)


# ── Test 2: minimal ReplayRow JSON round-trip ─────────────────────────────────

def test_minimal_replay_row_serializes_to_json() -> None:
    """make_minimal_replay_row() output survives a JSON round-trip unchanged."""
    row = make_minimal_replay_row(
        row_id="test-row-001",
        run_id="test-run-001",
        timestamp_utc="2026-07-01T00:00:00Z",
    )
    serialized = json.dumps(row)
    restored = json.loads(serialized)

    assert restored["schema_version"] == REPLAY_ROW_SCHEMA_VERSION
    assert restored["row_id"] == "test-row-001"
    assert restored["identity"]["run_id"] == "test-run-001"
    assert restored["identity"]["timestamp_utc"] == "2026-07-01T00:00:00Z"
    assert restored["model"]["model_attempted"] is False
    assert restored["model"]["selected_side_probability"] == 0.0
    assert restored["model"]["top_level_confidence"] == 0.0
    assert restored["path_truth"]["path_available"] is False
    assert restored["runtime_decision"]["baseline_action"] == "SKIP"
    assert restored["quality"]["evidence_grade"] == "E"
    assert isinstance(restored["provenance"], dict)


# ── Test 3: validate_required_replay_row_containers — missing container ────────

def test_validate_missing_container_detection() -> None:
    """Removing a required container from a row dict is detected and reported."""
    row = make_minimal_replay_row(
        row_id="test-row-002",
        run_id="run-002",
        timestamp_utc="2026-07-01T00:01:00Z",
    )
    # Remove a required container
    row_dict = dict(row)
    del row_dict["model"]

    missing = validate_required_replay_row_containers(row_dict)
    assert "model" in missing
    assert len(missing) == 1


# ── Test 4: validate_required_replay_row_containers — all present ─────────────

def test_validate_all_containers_present_returns_empty() -> None:
    """A fully populated minimal row has no missing required containers."""
    row = make_minimal_replay_row(
        row_id="test-row-003",
        run_id="run-003",
        timestamp_utc="2026-07-01T00:02:00Z",
    )
    missing = validate_required_replay_row_containers(row)
    assert missing == []


# ── Test 5: StrategyDecision JSON round-trip ──────────────────────────────────

def test_strategy_decision_serializes_to_json() -> None:
    """make_minimal_strategy_decision() output survives a JSON round-trip."""
    for action in StrategyAction:
        decision = make_minimal_strategy_decision(
            plugin_id="test-plugin",
            row_id="test-row-004",
            action=action,
        )
        serialized = json.dumps(decision)
        restored = json.loads(serialized)

        assert restored["schema_version"] == STRATEGY_DECISION_SCHEMA_VERSION
        assert restored["plugin_id"] == "test-plugin"
        assert restored["row_id"] == "test-row-004"
        assert restored["action"] == action.value
        assert isinstance(restored["metrics"], dict)
        assert isinstance(restored["reject_reasons"], list)


# ── Test 6: path-truth fields are scoring-only ────────────────────────────────

def test_path_truth_fields_are_scoring_only() -> None:
    """PATH_TRUTH_SCORING_ONLY_FIELDS contains the expected post-trade fields."""
    expected_scoring_fields = {"mfe", "mae", "tp_touched", "sl_touched",
                               "settlement_outcome", "settlement_price"}
    for field in expected_scoring_fields:
        assert field in PATH_TRUTH_SCORING_ONLY_FIELDS, (
            f"Expected scoring-only field '{field}' missing from "
            f"PATH_TRUTH_SCORING_ONLY_FIELDS"
        )

    # Decision-time fields must NOT appear in the scoring-only set
    decision_time_fields = {"path_available", "truth_source"}
    for field in decision_time_fields:
        assert field not in PATH_TRUTH_SCORING_ONLY_FIELDS, (
            f"Decision-time field '{field}' must not be in PATH_TRUTH_SCORING_ONLY_FIELDS"
        )

    # top_level_confidence and selected_side_probability are model fields —
    # not in path_truth and not in PATH_TRUTH_SCORING_ONLY_FIELDS
    assert "top_level_confidence" not in PATH_TRUTH_SCORING_ONLY_FIELDS
    assert "selected_side_probability" not in PATH_TRUTH_SCORING_ONLY_FIELDS


# ── Test 7: EvidenceGrade enum completeness ───────────────────────────────────

def test_evidence_grade_enum_values() -> None:
    """EvidenceGrade has all five grades A–E and they are distinct str values."""
    grades = {g.value for g in EvidenceGrade}
    assert grades == {"A", "B", "C", "D", "E"}

    # Each grade is a str (needed for JSON serialization without custom encoder)
    for grade in EvidenceGrade:
        assert isinstance(grade.value, str)
        assert json.dumps(grade.value) == f'"{grade.value}"'


# ── Test 8: StrategyAction enum completeness ──────────────────────────────────

def test_strategy_action_enum_values() -> None:
    """StrategyAction has exactly ENTRY, EXIT, HOLD, SKIP and all values are str."""
    actions = {a.value for a in StrategyAction}
    assert actions == {"ENTRY", "EXIT", "HOLD", "SKIP"}

    # ENTRY is an offline-only hypothetical — string value must serialize cleanly
    assert StrategyAction.ENTRY.value == "ENTRY"
    assert json.dumps({"action": StrategyAction.ENTRY.value}) == '{"action": "ENTRY"}'


# ── Test 9: StrategyPluginMetadata runtime_imports_allowed enforcement ─────────

def test_strategy_plugin_metadata_runtime_imports_allowed_false() -> None:
    """
    runtime_imports_allowed is a required field in StrategyPluginMetadata.
    The schema contract requires it to be set to False for all framework plugins.
    """
    meta: StrategyPluginMetadata = {
        "plugin_id": "baseline-skip-all-v0",
        "plugin_version": "0.1.0",
        "family": PluginFamily.BASELINE.value,
        "display_name": "Baseline Skip-All",
        "description": "Reference plugin that always emits SKIP.",
        "required_replay_fields": ["model.model_attempted", "runtime_decision.baseline_action"],
        "optional_replay_fields": [],
        "decision_actions": [StrategyAction.SKIP.value],
        "uses_path_truth_for_scoring_only": True,
        "runtime_imports_allowed": False,
    }

    assert meta["runtime_imports_allowed"] is False, (
        "runtime_imports_allowed must be False; True would allow the plugin "
        "to import live runtime modules."
    )
    assert meta["uses_path_truth_for_scoring_only"] is True
    assert meta["family"] == "baseline"

    # Verify the Recommendation and EvidenceDecision round-trip correctly
    decision: EvidenceDecision = {
        "recommendation": Recommendation.NOT_READY.value,
        "evidence_grade": EvidenceGrade.C.value,
        "confidence": 0.4,
        "blockers": ["insufficient sample size"],
        "required_next_evidence": ["min 100 paper fills with exit truth"],
        "plugin_id": meta["plugin_id"],
    }
    serialized = json.dumps(decision)
    restored = json.loads(serialized)
    assert restored["recommendation"] == "NOT_READY"
    assert restored["evidence_grade"] == "C"


# ── Test 10: subprocess import-safety — no runtime modules imported ────────────

def test_runtime_import_safety_subprocess() -> None:
    """
    Importing contracts.py in a subprocess must not pull in polymarket.trader,
    polymarket.client, or config.settings. Uses a subprocess so pytest's own
    imports in the parent process don't contaminate sys.modules.
    """
    check_code = (
        "import tools.shadow_strategy_framework.contracts; "
        "import sys; "
        "assert 'polymarket.trader' not in sys.modules, "
        "    'polymarket.trader was imported by contracts.py'; "
        "assert 'polymarket.client' not in sys.modules, "
        "    'polymarket.client was imported by contracts.py'; "
        "assert 'config.settings' not in sys.modules, "
        "    'config.settings was imported by contracts.py'"
    )
    result = subprocess.run(
        [sys.executable, "-c", check_code],
        capture_output=True,
        cwd=str(_PROJECT_ROOT),
        env={
            **__import__("os").environ,
            "PYTHONPATH": str(_PROJECT_ROOT),
        },
    )
    assert result.returncode == 0, (
        f"Runtime import detected in contracts.py:\n"
        f"stdout: {result.stdout.decode()}\n"
        f"stderr: {result.stderr.decode()}"
    )
