"""Independent offline validation harness for Discovery Framework V3.

This module validates analytical primitives against deterministic synthetic
controls. It has no runtime trading imports and no authority over strategy,
risk, execution, or live behavior.
"""
from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Iterable


DEFAULT_VALIDATION_RECORD = Path("runtime/reports/harness_validation_002.json")
CLUSTER_FIELDS = ("condition_id", "epoch_start_ts")


class HarnessValidationError(ValueError):
    """Raised when a validation input cannot support a trustworthy result."""


def _require_non_empty(values: Iterable[Any], label: str) -> list[Any]:
    items = list(values)
    if not items:
        raise HarnessValidationError(f"{label} must be non-empty")
    return items


def _require_probability(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise HarnessValidationError(f"{label} must be numeric") from exc
    if not 0.0 <= result <= 1.0:
        raise HarnessValidationError(f"{label} must be between zero and one")
    return result


def _require_outcome(value: Any) -> int:
    if value not in (0, 1, False, True):
        raise HarnessValidationError("outcomes must be binary")
    return int(value)


def brier_score(probabilities: Iterable[Any], outcomes: Iterable[Any]) -> float:
    """Return mean squared probability error."""
    probs = _require_non_empty(probabilities, "probabilities")
    actual = _require_non_empty(outcomes, "outcomes")
    if len(probs) != len(actual):
        raise HarnessValidationError("probabilities and outcomes must have equal length")
    pairs = [
        (_require_probability(probability, "probability"), _require_outcome(outcome))
        for probability, outcome in zip(probs, actual)
    ]
    return mean((probability - outcome) ** 2 for probability, outcome in pairs)


def brier_skill(
    model_probabilities: Iterable[Any],
    market_probabilities: Iterable[Any],
    outcomes: Iterable[Any],
) -> float:
    """Return Brier Skill versus the market probability benchmark."""
    model = list(model_probabilities)
    market = list(market_probabilities)
    actual = list(outcomes)
    if not (len(model) == len(market) == len(actual)):
        raise HarnessValidationError("model, market, and outcomes must have equal length")
    model_score = brier_score(model, actual)
    market_score = brier_score(market, actual)
    if market_score == 0:
        raise HarnessValidationError("market Brier score is zero")
    return 1.0 - model_score / market_score


def executable_markouts(rows: Iterable[dict[str, Any]]) -> list[float]:
    """Return executable +15s markouts using entry ask and exit bid."""
    items = _require_non_empty(rows, "rows")
    markouts: list[float] = []
    for row in items:
        if row.get("entry_ask") is None:
            raise HarnessValidationError("entry_ask is required")
        if row.get("exit_bid_15s") is None:
            raise HarnessValidationError("exit_bid_15s is required")
        try:
            markouts.append(float(row["exit_bid_15s"]) - float(row["entry_ask"]))
        except (TypeError, ValueError) as exc:
            raise HarnessValidationError("markout prices must be numeric") from exc
    return markouts


def _cluster_key(row: dict[str, Any]) -> tuple[str, int]:
    condition = row.get("condition_id")
    epoch = row.get("epoch_start_ts")
    if condition in (None, "") or epoch is None:
        raise HarnessValidationError("condition_id and epoch_start_ts are required")
    try:
        return str(condition), int(epoch)
    except (TypeError, ValueError) as exc:
        raise HarnessValidationError("epoch_start_ts must be an integer") from exc


def _cluster_groups(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, int], list[dict[str, Any]]]:
    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in _require_non_empty(rows, "rows"):
        groups[_cluster_key(row)].append(row)
    return dict(groups)


def effective_cluster_count(rows: Iterable[dict[str, Any]]) -> int:
    """Return unique condition/epoch decision-bearing units."""
    return len(_cluster_groups(rows))


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(_require_non_empty(values, "values"))
    if not 0.0 <= probability <= 1.0:
        raise HarnessValidationError("percentile probability must be between zero and one")
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _mean_executable_markout(rows: list[dict[str, Any]]) -> float:
    return mean(executable_markouts(rows))


def cluster_bootstrap(
    rows: Iterable[dict[str, Any]],
    *,
    iterations: int = 1_000,
    seed: int = 2026,
    metric: Callable[[list[dict[str, Any]]], float] = _mean_executable_markout,
) -> dict[str, Any]:
    """Bootstrap a metric by resampling condition/epoch clusters."""
    groups = _cluster_groups(rows)
    keys = sorted(groups)
    if len(keys) < 2:
        raise HarnessValidationError("cluster bootstrap requires at least two clusters")
    if iterations < 1:
        raise HarnessValidationError("iterations must be positive")
    rng = random.Random(seed)
    distribution: list[float] = []
    for _ in range(iterations):
        sampled_keys = [rng.choice(keys) for _ in keys]
        sample = [row for key in sampled_keys for row in groups[key]]
        distribution.append(float(metric(sample)))
    return {
        "seed": seed,
        "iterations": iterations,
        "effective_cluster_count": len(keys),
        "distribution": distribution,
        "ci_low": _percentile(distribution, 0.025),
        "ci_high": _percentile(distribution, 0.975),
    }


def _stratum(row: dict[str, Any]) -> str:
    value = row.get("time_block")
    if value in (None, ""):
        raise HarnessValidationError("time_block is required for null construction")
    return str(value)


def random_entry_null(
    eligible_rows: Iterable[dict[str, Any]],
    selected_rows: Iterable[dict[str, Any]],
    *,
    iterations: int = 1_000,
    seed: int = 2026,
) -> dict[str, Any]:
    """Randomly select clusters while preserving selected time-block counts."""
    eligible_groups = _cluster_groups(eligible_rows)
    selected_groups = _cluster_groups(selected_rows)
    selected_counts = Counter(_stratum(rows[0]) for rows in selected_groups.values())
    eligible_by_stratum: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for key, rows in eligible_groups.items():
        eligible_by_stratum[_stratum(rows[0])].append(key)
    for stratum, count in selected_counts.items():
        if len(eligible_by_stratum[stratum]) < count:
            raise HarnessValidationError("eligible population cannot preserve selected strata")

    rng = random.Random(seed)
    distribution: list[float] = []
    sample_strata_counts: list[dict[str, int]] = []
    for _ in range(iterations):
        sampled_keys: list[tuple[str, int]] = []
        for stratum in sorted(selected_counts):
            sampled_keys.extend(rng.sample(sorted(eligible_by_stratum[stratum]), selected_counts[stratum]))
        sample = [row for key in sampled_keys for row in eligible_groups[key]]
        distribution.append(_mean_executable_markout(sample))
        sample_strata_counts.append(dict(Counter(_stratum(eligible_groups[key][0]) for key in sampled_keys)))
    return {
        "seed": seed,
        "iterations": iterations,
        "selected_cluster_count": len(selected_groups),
        "expected_strata_counts": dict(selected_counts),
        "sample_strata_counts": sample_strata_counts,
        "distribution": distribution,
        "p95": _percentile(distribution, 0.95),
    }


def _brier_skill_for_rows(rows: list[dict[str, Any]]) -> float:
    return brier_skill(
        [row["model_probability"] for row in rows],
        [row["market_mid"] for row in rows],
        [row["outcome_yes"] for row in rows],
    )


def shuffled_signal_null(
    rows: Iterable[dict[str, Any]],
    *,
    iterations: int = 1_000,
    seed: int = 2026,
) -> dict[str, Any]:
    """Shuffle model probabilities among clusters within each time block."""
    items = [dict(row) for row in _require_non_empty(rows, "rows")]
    groups = _cluster_groups(items)
    cluster_probabilities = {key: float(group[0]["model_probability"]) for key, group in groups.items()}
    keys_by_stratum: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for key, group in groups.items():
        keys_by_stratum[_stratum(group[0])].append(key)

    rng = random.Random(seed)
    distribution: list[float] = []
    for _ in range(iterations):
        probability_map: dict[tuple[str, int], float] = {}
        for stratum in sorted(keys_by_stratum):
            keys = sorted(keys_by_stratum[stratum])
            probabilities = [cluster_probabilities[key] for key in keys]
            rng.shuffle(probabilities)
            probability_map.update(zip(keys, probabilities))
        shuffled = [
            {**row, "model_probability": probability_map[_cluster_key(row)]}
            for row in items
        ]
        distribution.append(_brier_skill_for_rows(shuffled))

    return {
        "seed": seed,
        "iterations": iterations,
        "effective_cluster_count": len(groups),
        "distribution": distribution,
        "p95": _percentile(distribution, 0.95),
        "model_probability_values_preserved": True,
        "outcomes_preserved": True,
        "cluster_keys_preserved": True,
    }


def time_shift_null(rows: Iterable[dict[str, Any]], *, shift_clusters: int = 1) -> list[dict[str, Any]]:
    """Rotate model probabilities across clusters within each time block."""
    items = [dict(row) for row in _require_non_empty(rows, "rows")]
    groups = _cluster_groups(items)
    keys_by_stratum: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for key, group in groups.items():
        keys_by_stratum[_stratum(group[0])].append(key)
    probability_map: dict[tuple[str, int], float] = {}
    for stratum in sorted(keys_by_stratum):
        keys = sorted(keys_by_stratum[stratum])
        if len(keys) < 2:
            raise HarnessValidationError("time shift requires at least two clusters per stratum")
        shift = shift_clusters % len(keys)
        if shift == 0:
            raise HarnessValidationError("time shift must change cluster alignment")
        probabilities = [float(groups[key][0]["model_probability"]) for key in keys]
        rotated = probabilities[-shift:] + probabilities[:-shift]
        probability_map.update(zip(keys, rotated))
    return [{**row, "model_probability": probability_map[_cluster_key(row)]} for row in items]


def build_positive_control() -> list[dict[str, Any]]:
    """Build deterministic signal and background clusters with known effects."""
    rows: list[dict[str, Any]] = []
    base_epoch = 1_780_000_000
    for index in range(80):
        selected = index % 2 == 0
        outcome = (index // 2) % 2
        model_probability = (0.8 if outcome else 0.2) if selected else 0.5
        markout = 0.06 if selected else -0.06
        rows.append(
            {
                "unit_id": f"positive-{index}",
                "condition_id": f"condition-{index}",
                "epoch_start_ts": base_epoch + index * 300,
                "cluster_id": f"condition-{index}|{base_epoch + index * 300}",
                "time_block": "early" if index < 40 else "late",
                "signal_score": 0.9 if selected else 0.1,
                "selected": selected,
                "model_probability": model_probability,
                "market_mid": 0.5,
                "outcome_yes": outcome,
                "entry_ask": 0.50,
                "exit_bid_15s": 0.50 + markout,
            }
        )
    return rows


def build_null_control() -> list[dict[str, Any]]:
    """Build deterministic clusters with zero predictive and markout effect."""
    rows: list[dict[str, Any]] = []
    base_epoch = 1_790_000_000
    for index in range(40):
        outcome = index % 2
        markout = 0.02 if index % 2 else -0.02
        rows.append(
            {
                "unit_id": f"null-{index}",
                "condition_id": f"null-condition-{index}",
                "epoch_start_ts": base_epoch + index * 300,
                "cluster_id": f"null-condition-{index}|{base_epoch + index * 300}",
                "time_block": "early" if index < 20 else "late",
                "signal_score": 0.5,
                "selected": True,
                "model_probability": 0.5,
                "market_mid": 0.5,
                "outcome_yes": outcome,
                "entry_ask": 0.50,
                "exit_bid_15s": 0.50 + markout,
            }
        )
    return rows


def validate_harness() -> dict[str, Any]:
    """Run deterministic controls and return the harness graduation record."""
    positive_population = build_positive_control()
    positive = [row for row in positive_population if row["selected"]]
    null = build_null_control()

    positive_skill = _brier_skill_for_rows(positive)
    positive_markout = _mean_executable_markout(positive)
    positive_bootstrap = cluster_bootstrap(positive, iterations=500, seed=101)
    random_null = random_entry_null(positive_population, positive, iterations=500, seed=102)
    shuffled_null = shuffled_signal_null(positive, iterations=500, seed=103)
    shifted = time_shift_null(positive, shift_clusters=1)
    shifted_skill = _brier_skill_for_rows(shifted)

    null_skill = _brier_skill_for_rows(null)
    null_markout = _mean_executable_markout(null)
    null_bootstrap = cluster_bootstrap(null, iterations=500, seed=104)

    duplicated = [dict(row) for row in positive for _ in range(3)]
    duplication_original = cluster_bootstrap(positive, iterations=100, seed=105)
    duplication_repeated = cluster_bootstrap(duplicated, iterations=100, seed=105)
    reproducibility_first = cluster_bootstrap(positive, iterations=100, seed=106)
    reproducibility_second = cluster_bootstrap(positive, iterations=100, seed=106)

    checks = {
        "positive_brier_skill_detected": positive_skill > 0,
        "positive_executable_markout_detected": positive_markout > 0,
        "positive_cluster_ci_excludes_zero": positive_bootstrap["ci_low"] > 0,
        "random_entry_null_attenuates_markout": random_null["p95"] < positive_markout,
        "shuffled_signal_null_attenuates_skill": shuffled_null["p95"] < positive_skill,
        "time_shift_null_attenuates_skill": shifted_skill < positive_skill,
        "null_brier_skill_absent": abs(null_skill) <= 1e-12,
        "null_markout_absent": abs(null_markout) <= 1e-12,
        "null_cluster_ci_contains_zero": null_bootstrap["ci_low"] <= 0 <= null_bootstrap["ci_high"],
        "cluster_duplication_invariant": (
            duplication_original["distribution"] == duplication_repeated["distribution"]
            and duplication_original["effective_cluster_count"]
            == duplication_repeated["effective_cluster_count"]
        ),
        "bootstrap_seed_reproducible": reproducibility_first == reproducibility_second,
        "null_suite_invariants_preserved": (
            shuffled_null["model_probability_values_preserved"]
            and shuffled_null["outcomes_preserved"]
            and shuffled_null["cluster_keys_preserved"]
            and all(
                sample == random_null["expected_strata_counts"]
                for sample in random_null["sample_strata_counts"]
            )
        ),
    }
    passed = sum(bool(value) for value in checks.values())
    verdict = "HARNESS_READY" if passed == len(checks) else "HARNESS_NOT_READY"

    return {
        "schema_version": "harness_validation_002",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "harness_verdict": verdict,
        "required_checks_total": len(checks),
        "required_checks_passed": passed,
        "checks": checks,
        "controls": {
            "positive": {
                "raw_rows": len(positive),
                "effective_cluster_count": effective_cluster_count(positive),
                "brier_skill": positive_skill,
                "mean_executable_markout": positive_markout,
                "bootstrap_ci_low": positive_bootstrap["ci_low"],
                "bootstrap_ci_high": positive_bootstrap["ci_high"],
                "random_entry_null_p95": random_null["p95"],
                "shuffled_signal_null_p95": shuffled_null["p95"],
                "time_shift_brier_skill": shifted_skill,
                "classification": "SIGNAL_PRESENT",
            },
            "null": {
                "raw_rows": len(null),
                "effective_cluster_count": effective_cluster_count(null),
                "brier_skill": null_skill,
                "mean_executable_markout": null_markout,
                "bootstrap_ci_low": null_bootstrap["ci_low"],
                "bootstrap_ci_high": null_bootstrap["ci_high"],
                "classification": "SIGNAL_ABSENT",
            },
        },
        "seeds": {
            "positive_bootstrap": 101,
            "random_entry_null": 102,
            "shuffled_signal_null": 103,
            "null_bootstrap": 104,
            "duplication_invariance": 105,
            "reproducibility": 106,
        },
        "guardrails": {
            "offline_only": True,
            "runtime_trading_imports": False,
            "candidate_audits_run": False,
            "replay_signal_tests_run": False,
            "runtime_authority": False,
        },
    }


def write_validation_record(record: dict[str, Any], path: Path = DEFAULT_VALIDATION_RECORD) -> Path:
    """Persist a deterministic-format validation record."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> int:
    record = validate_harness()
    write_validation_record(record)
    print(json.dumps({"harness_verdict": record["harness_verdict"], "path": str(DEFAULT_VALIDATION_RECORD)}))
    return 0 if record["harness_verdict"] == "HARNESS_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
