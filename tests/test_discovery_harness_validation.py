from __future__ import annotations

import ast
import json
from collections import Counter
from pathlib import Path

import pytest

from tools.discovery_harness_validation import (
    DEFAULT_VALIDATION_RECORD,
    HarnessValidationError,
    brier_score,
    brier_skill,
    build_null_control,
    build_positive_control,
    cluster_bootstrap,
    effective_cluster_count,
    executable_markouts,
    random_entry_null,
    shuffled_signal_null,
    time_shift_null,
    validate_harness,
    write_validation_record,
)


def test_brier_score_and_skill_are_analytically_correct() -> None:
    assert brier_score([0.8, 0.2], [1, 0]) == pytest.approx(0.04)
    assert brier_skill([0.8, 0.2], [0.5, 0.5], [1, 0]) == pytest.approx(0.84)


def test_executable_markout_is_ask_to_bid() -> None:
    rows = [
        {"entry_ask": 0.51, "exit_bid_15s": 0.56},
        {"entry_ask": 0.48, "exit_bid_15s": 0.46},
    ]
    assert executable_markouts(rows) == pytest.approx([0.05, -0.02])


def test_positive_control_is_detected() -> None:
    record = validate_harness()
    positive = record["controls"]["positive"]

    assert positive["brier_skill"] > 0
    assert positive["mean_executable_markout"] > 0
    assert positive["bootstrap_ci_low"] > 0
    assert positive["shuffled_signal_null_p95"] < positive["brier_skill"]
    assert positive["random_entry_null_p95"] < positive["mean_executable_markout"]


def test_null_control_is_rejected() -> None:
    record = validate_harness()
    null = record["controls"]["null"]

    assert null["classification"] == "SIGNAL_ABSENT"
    assert null["bootstrap_ci_low"] <= 0 <= null["bootstrap_ci_high"]
    assert abs(null["brier_skill"]) <= 1e-12
    assert abs(null["mean_executable_markout"]) <= 1e-12


def test_cluster_duplication_does_not_change_bootstrap_distribution() -> None:
    selected = [row for row in build_positive_control() if row["selected"]]
    duplicated = [dict(row) for row in selected for _ in range(3)]

    original = cluster_bootstrap(selected, iterations=250, seed=17)
    repeated = cluster_bootstrap(duplicated, iterations=250, seed=17)

    assert original["distribution"] == pytest.approx(repeated["distribution"])
    assert original["effective_cluster_count"] == repeated["effective_cluster_count"]


def test_effective_cluster_count_uses_condition_and_epoch() -> None:
    rows = build_positive_control()
    duplicated = [dict(row) for row in rows for _ in range(4)]

    assert effective_cluster_count(rows) == 80
    assert effective_cluster_count(duplicated) == 80


def test_bootstrap_is_seed_reproducible() -> None:
    selected = [row for row in build_positive_control() if row["selected"]]

    first = cluster_bootstrap(selected, iterations=200, seed=991)
    second = cluster_bootstrap(selected, iterations=200, seed=991)

    assert first == second


def test_random_entry_null_preserves_sample_count_and_time_blocks() -> None:
    rows = build_positive_control()
    selected = [row for row in rows if row["selected"]]
    expected = Counter(row["time_block"] for row in selected)

    result = random_entry_null(rows, selected, iterations=40, seed=22)

    assert result["selected_cluster_count"] == len(selected)
    assert result["expected_strata_counts"] == dict(expected)
    assert all(sample == dict(expected) for sample in result["sample_strata_counts"])


def test_shuffled_signal_null_preserves_values_outcomes_and_clusters() -> None:
    selected = [row for row in build_positive_control() if row["selected"]]
    result = shuffled_signal_null(selected, iterations=20, seed=44)

    assert result["effective_cluster_count"] == effective_cluster_count(selected)
    assert result["model_probability_values_preserved"] is True
    assert result["outcomes_preserved"] is True
    assert result["cluster_keys_preserved"] is True


def test_time_shift_null_preserves_identity_and_rotates_probabilities() -> None:
    selected = [row for row in build_positive_control() if row["selected"]]
    shifted = time_shift_null(selected, shift_clusters=1)

    original_keys = [(row["condition_id"], row["epoch_start_ts"]) for row in selected]
    shifted_keys = [(row["condition_id"], row["epoch_start_ts"]) for row in shifted]
    assert shifted_keys == original_keys
    assert sorted(row["model_probability"] for row in shifted) == sorted(
        row["model_probability"] for row in selected
    )
    assert any(
        before["model_probability"] != after["model_probability"]
        for before, after in zip(selected, shifted)
    )


@pytest.mark.parametrize(
    ("call", "match"),
    [
        (lambda: brier_score([], []), "non-empty"),
        (lambda: brier_score([0.5], [2]), "binary"),
        (lambda: brier_skill([0.5], [1.0], [1]), "zero"),
        (lambda: executable_markouts([{"entry_ask": 0.5}]), "exit_bid_15s"),
        (
            lambda: cluster_bootstrap(
                [
                    {
                        "condition_id": "only",
                        "epoch_start_ts": 1,
                        "entry_ask": 0.5,
                        "exit_bid_15s": 0.6,
                    }
                ]
            ),
            "two clusters",
        ),
    ],
)
def test_missing_or_invalid_inputs_fail_closed(call, match: str) -> None:
    with pytest.raises(HarnessValidationError, match=match):
        call()


def test_module_has_no_runtime_trading_imports() -> None:
    module_path = Path("tools/discovery_harness_validation.py")
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    forbidden = ("polymarket", "main", "config", "utils.risk_manager")
    assert not [name for name in imported if name.startswith(forbidden)]


def test_validation_record_reports_harness_ready() -> None:
    record = validate_harness()
    path = write_validation_record(record, DEFAULT_VALIDATION_RECORD)
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert persisted["harness_verdict"] == "HARNESS_READY"
    assert persisted["required_checks_passed"] == persisted["required_checks_total"]
    assert persisted["guardrails"]["offline_only"] is True
    assert path == DEFAULT_VALIDATION_RECORD
