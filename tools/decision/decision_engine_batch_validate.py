"""Offline batch validation for canonical trade context decision diagnostics."""

from __future__ import annotations

import argparse
import glob
import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from tools.decision.decision_engine_prototype import (
    PASS_CONTEXT,
    REJECT_BAD_EV,
    REJECT_BAD_PROBABILITY,
    REJECT_LOW_EVIDENCE,
    REJECT_MISSING_CONTEXT,
    REVIEW_REQUIRED,
    validate_trade_context,
)


SCHEMA_VERSION = "decision_engine_batch_validation.v1"

DECISION_STATES = (
    PASS_CONTEXT,
    REJECT_MISSING_CONTEXT,
    REJECT_BAD_PROBABILITY,
    REJECT_BAD_EV,
    REJECT_LOW_EVIDENCE,
    REVIEW_REQUIRED,
)

REJECT_STATES = (
    REJECT_MISSING_CONTEXT,
    REJECT_BAD_PROBABILITY,
    REJECT_BAD_EV,
    REJECT_LOW_EVIDENCE,
)


def load_jsonl_rows(paths: Sequence[str | Path]) -> dict[str, Any]:
    """Load JSONL rows from paths, skipping malformed lines with a count."""

    rows: list[dict[str, Any]] = []
    files_read: list[str] = []
    missing_files: list[str] = []
    total_lines = 0
    parse_errors = 0

    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file():
            missing_files.append(str(path))
            continue

        files_read.append(str(path))
        with path.open(encoding="utf-8") as handle:
            for raw_line in handle:
                total_lines += 1
                text = raw_line.strip()
                if not text:
                    continue
                try:
                    row = json.loads(text)
                except json.JSONDecodeError:
                    parse_errors += 1
                    continue
                if isinstance(row, dict):
                    rows.append(row)

    return {
        "rows": rows,
        "files_read": files_read,
        "missing_files": missing_files,
        "total_lines": total_lines,
        "parse_errors": parse_errors,
    }


def validate_jsonl_files(paths: Sequence[str | Path], max_examples: int = 3) -> dict[str, Any]:
    """Load canonical JSONL files and summarize prototype diagnostics."""

    loaded = load_jsonl_rows(paths)
    return summarize_decision_diagnostics(
        loaded["rows"],
        source_files=loaded["files_read"],
        parse_errors=loaded["parse_errors"],
        total_lines=loaded["total_lines"],
        missing_files=loaded["missing_files"],
        max_examples=max_examples,
    )


def summarize_decision_diagnostics(
    rows: Iterable[Mapping[str, Any]],
    *,
    source_files: Sequence[str],
    parse_errors: int,
    total_lines: int,
    missing_files: Sequence[str] | None = None,
    max_examples: int = 3,
) -> dict[str, Any]:
    """Aggregate decision diagnostics for canonical context rows."""

    decision_state_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    missing_field_counts: Counter[str] = Counter()
    reject_reason_counts: Counter[str] = Counter()
    note_counts: Counter[str] = Counter()
    evidence_status_counts: Counter[str] = Counter()
    evidence_grade_counts: Counter[str] = Counter()
    join_confidence_counts: Counter[str] = Counter()
    probability_status_counts: Counter[str] = Counter()
    ev_status_counts: Counter[str] = Counter()
    liquidity_status_counts: Counter[str] = Counter()
    availability_status_counts: Counter[str] = Counter()
    examples: dict[str, list[dict[str, Any]]] = {state: [] for state in DECISION_STATES}

    total_rows = 0
    for row in rows:
        total_rows += 1
        diagnostic = validate_trade_context(row)
        decision_state = str(diagnostic["decision_state"])
        decision_state_counts[decision_state] += 1
        confidence_counts[str(diagnostic["confidence"])] += 1
        missing_field_counts.update(str(field) for field in diagnostic["missing_fields"])
        reject_reason_counts.update(str(reason) for reason in diagnostic["reject_reasons"])
        note_counts.update(str(note) for note in diagnostic["notes"])

        evidence_quality = diagnostic["evidence_quality"]
        evidence_status_counts[str(evidence_quality["status"])] += 1
        evidence_grade_counts[str(evidence_quality["data_quality_grade"])] += 1
        join_confidence_counts[str(evidence_quality["join_confidence"])] += 1

        probability_status_counts[str(diagnostic["probability_quality"]["status"])] += 1
        ev_status_counts[str(diagnostic["ev_quality"]["status"])] += 1
        liquidity_status_counts[str(diagnostic["liquidity_quality"]["status"])] += 1
        availability_status_counts[str(diagnostic["availability_quality"]["status"])] += 1

        if len(examples.setdefault(decision_state, [])) < max_examples:
            examples[decision_state].append(_compact_example(row, diagnostic))

    return {
        "schema_version": SCHEMA_VERSION,
        "total_rows": total_rows,
        "total_lines": total_lines,
        "parse_errors": parse_errors,
        "source_files": list(source_files),
        "missing_files": list(missing_files or []),
        "decision_state_counts": _counter_dict(decision_state_counts),
        "confidence_counts": _counter_dict(confidence_counts),
        "missing_field_counts": _counter_dict(missing_field_counts),
        "reject_reason_counts": _counter_dict(reject_reason_counts),
        "note_counts": _counter_dict(note_counts),
        "evidence_quality_summary": {
            "status_counts": _counter_dict(evidence_status_counts),
            "data_quality_grade_counts": _counter_dict(evidence_grade_counts),
            "join_confidence_counts": _counter_dict(join_confidence_counts),
        },
        "probability_quality_counts": _counter_dict(probability_status_counts),
        "ev_quality_counts": _counter_dict(ev_status_counts),
        "liquidity_quality_counts": _counter_dict(liquidity_status_counts),
        "availability_quality_counts": _counter_dict(availability_status_counts),
        "examples": examples,
    }


def build_markdown_report(summary: Mapping[str, Any]) -> str:
    """Render a concise markdown report from a batch validation summary."""

    lines = [
        "# DECISION_ENGINE_PROTOTYPE_BATCH_VALIDATION_001",
        "",
        "## Verdict",
        "",
        "OFFLINE_VALIDATION_COMPLETE. The prototype was evaluated as a diagnostic layer only; no runtime trading behavior was changed.",
        "",
        "## Inputs",
        "",
        f"- Schema version: `{summary.get('schema_version')}`",
        f"- Source files: {len(summary.get('source_files', []))}",
        f"- Total lines read: {summary.get('total_lines', 0)}",
        f"- Parse errors skipped: {summary.get('parse_errors', 0)}",
    ]
    for source_file in summary.get("source_files", []):
        lines.append(f"- `{source_file}`")

    lines.extend(
        [
            "",
            "## Total Rows Evaluated",
            "",
            str(summary.get("total_rows", 0)),
            "",
            "## Decision State Counts",
            "",
            _markdown_table(summary.get("decision_state_counts", {}), "decision_state", "count"),
            "",
            "## Confidence Distribution",
            "",
            _markdown_table(summary.get("confidence_counts", {}), "confidence", "count"),
            "",
            "## Missing Field Counts",
            "",
            _markdown_table(summary.get("missing_field_counts", {}), "missing_field", "count", limit=25),
            "",
            "## Reject Reason Counts",
            "",
            _markdown_table(summary.get("reject_reason_counts", {}), "reject_reason", "count"),
            "",
            "## Evidence Quality Summary",
            "",
            "### Evidence Status",
            "",
            _markdown_table(summary.get("evidence_quality_summary", {}).get("status_counts", {}), "status", "count"),
            "",
            "### Data Quality Grades",
            "",
            _markdown_table(summary.get("evidence_quality_summary", {}).get("data_quality_grade_counts", {}), "grade", "count"),
            "",
            "### Join Confidence",
            "",
            _markdown_table(summary.get("evidence_quality_summary", {}).get("join_confidence_counts", {}), "join_confidence", "count"),
            "",
            "## Quality Subsystems",
            "",
            "### Probability Quality",
            "",
            _markdown_table(summary.get("probability_quality_counts", {}), "status", "count"),
            "",
            "### EV Quality",
            "",
            _markdown_table(summary.get("ev_quality_counts", {}), "status", "count"),
            "",
            "### Liquidity Quality",
            "",
            _markdown_table(summary.get("liquidity_quality_counts", {}), "status", "count"),
            "",
            "### Availability Quality",
            "",
            _markdown_table(summary.get("availability_quality_counts", {}), "status", "count"),
            "",
            "## Examples",
            "",
        ]
    )

    examples = summary.get("examples", {})
    for state in DECISION_STATES:
        lines.append(f"### {state}")
        lines.append("")
        state_examples = examples.get(state) or []
        if not state_examples:
            lines.append("Not observed in this batch.")
            lines.append("")
            continue
        for example in state_examples:
            lines.append(f"- `{json.dumps(example, sort_keys=True)}`")
        lines.append("")

    lines.extend(
        [
            "## Limitations",
            "",
            "- This is an offline diagnostic distribution, not a trading policy or runtime approval layer.",
            "- `PASS_CONTEXT` means the row has sufficient context for the prototype's conservative validation checks only.",
            "- Missing-field counts include canonical row metadata and prototype-required context fields.",
            "- Observed distributions depend on available canonical JSONL outputs and may change as context quality improves.",
            "- No strategy thresholds, risk sizing, execution, wallet, live/paper runtime, `.env`, or config behavior was changed.",
            "",
            "## Next Task",
            "",
            "`DECISION_ENGINE_PROTOTYPE_EDGE_CASE_FIXTURE_AUDIT_001` - add targeted fixture validation for decision states not observed in real canonical rows, if any remain unobserved.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate canonical context rows with the offline decision prototype.")
    parser.add_argument("paths", nargs="*", help="JSONL files or glob patterns. Defaults to runtime/reports/canonical_trade_context_*.jsonl")
    parser.add_argument("--output", type=Path, help="Optional markdown report output path.")
    parser.add_argument("--json-output", type=Path, help="Optional JSON summary output path.")
    args = parser.parse_args(argv)

    paths = _expand_paths(args.paths or ["runtime/reports/canonical_trade_context_*.jsonl"])
    summary = validate_jsonl_files(paths)
    report = build_markdown_report(summary)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return 0


def _expand_paths(patterns: Sequence[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            paths.extend(Path(match) for match in matches)
        else:
            paths.append(Path(pattern))
    return sorted(paths)


def _compact_example(row: Mapping[str, Any], diagnostic: Mapping[str, Any]) -> dict[str, Any]:
    evidence_quality = diagnostic["evidence_quality"]
    return {
        "trade_id": row.get("trade_id"),
        "position_id": row.get("position_id"),
        "ticker": row.get("ticker") or row.get("asset_id"),
        "outcome": row.get("outcome"),
        "event_classification": row.get("event_classification"),
        "decision_state": diagnostic["decision_state"],
        "confidence": diagnostic["confidence"],
        "missing_fields": list(diagnostic["missing_fields"])[:10],
        "reject_reasons": list(diagnostic["reject_reasons"]),
        "data_quality_grade": evidence_quality["data_quality_grade"],
        "join_confidence": evidence_quality["join_confidence"],
    }


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter, key=lambda item: (-counter[item], item))}


def _markdown_table(values: Mapping[str, int], key_header: str, value_header: str, limit: int | None = None) -> str:
    if not values:
        return "No rows."

    items = list(values.items())
    if limit is not None:
        items = items[:limit]
    lines = [f"| {key_header} | {value_header} |", "|---|---:|"]
    lines.extend(f"| `{key}` | {value} |" for key, value in items)
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
