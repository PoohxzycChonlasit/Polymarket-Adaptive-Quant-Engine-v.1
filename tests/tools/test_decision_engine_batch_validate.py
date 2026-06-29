import ast
import json
from pathlib import Path

from tools.decision.decision_engine_batch_validate import (
    build_markdown_report,
    load_jsonl_rows,
    summarize_decision_diagnostics,
    validate_jsonl_files,
)


def _row(**overrides):
    row = {
        "trade_id": "trade-pass",
        "intended_price": 0.45,
        "true_probability": 0.62,
        "probability": 0.62,
        "ev_after_spread": 0.14,
        "quote_age_ms": 120,
        "slippage": 0.0,
        "data_quality_grade": "A",
        "join_confidence": "HIGH",
        "source_streams": ["trade_journal", "decision_log", "execution_log"],
        "missing_fields": [],
    }
    row.update(overrides)
    return row


def _write_jsonl(path: Path, rows: list[dict], include_broken_line: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
        if include_broken_line:
            handle.write("{broken json\n")


def test_load_jsonl_rows_skips_malformed_lines_and_counts_parse_errors(tmp_path: Path):
    path = tmp_path / "canonical.jsonl"
    _write_jsonl(path, [_row(trade_id="ok")], include_broken_line=True)

    loaded = load_jsonl_rows([path])

    assert loaded["rows"] == [_row(trade_id="ok")]
    assert loaded["total_lines"] == 2
    assert loaded["parse_errors"] == 1
    assert loaded["files_read"] == [str(path)]


def test_summarize_decision_diagnostics_counts_states_and_quality():
    rows = [
        _row(trade_id="pass"),
        _row(trade_id="missing-price", intended_price=None),
        _row(trade_id="weak-evidence", data_quality_grade="D", join_confidence="LOW"),
    ]

    summary = summarize_decision_diagnostics(rows, source_files=["fixture.jsonl"], parse_errors=0, total_lines=3)

    assert summary["total_rows"] == 3
    assert summary["decision_state_counts"] == {
        "PASS_CONTEXT": 1,
        "REJECT_MISSING_CONTEXT": 1,
        "REJECT_LOW_EVIDENCE": 1,
    }
    assert summary["confidence_counts"] == {"HIGH": 1, "LOW": 2}
    assert summary["missing_field_counts"]["intended_price"] == 1
    assert summary["reject_reason_counts"] == {
        "missing_required_context": 1,
        "low_evidence_quality": 1,
    }
    assert summary["evidence_quality_summary"]["status_counts"] == {"PASS": 2, "FAIL": 1}
    assert summary["evidence_quality_summary"]["data_quality_grade_counts"] == {"A": 2, "D": 1}
    assert summary["examples"]["PASS_CONTEXT"][0]["trade_id"] == "pass"
    assert summary["examples"]["REJECT_MISSING_CONTEXT"][0]["trade_id"] == "missing-price"
    assert summary["examples"]["REJECT_LOW_EVIDENCE"][0]["trade_id"] == "weak-evidence"


def test_validate_jsonl_files_returns_serializable_summary(tmp_path: Path):
    path = tmp_path / "canonical.jsonl"
    _write_jsonl(path, [_row(trade_id="pass"), _row(trade_id="missing-ev", ev_after_spread=None)])

    summary = validate_jsonl_files([path])

    assert summary["total_rows"] == 2
    assert summary["decision_state_counts"]["PASS_CONTEXT"] == 1
    assert summary["decision_state_counts"]["REJECT_MISSING_CONTEXT"] == 1
    assert json.loads(json.dumps(summary, sort_keys=True))["total_rows"] == 2


def test_build_markdown_report_includes_required_sections(tmp_path: Path):
    path = tmp_path / "canonical.jsonl"
    _write_jsonl(path, [_row(trade_id="pass"), _row(trade_id="missing-ev", ev_after_spread=None)])
    summary = validate_jsonl_files([path])

    markdown = build_markdown_report(summary)

    assert "# DECISION_ENGINE_PROTOTYPE_BATCH_VALIDATION_001" in markdown
    assert "## Total Rows Evaluated" in markdown
    assert "## Decision State Counts" in markdown
    assert "## Missing Field Counts" in markdown
    assert "## Examples" in markdown
    assert "## Limitations" in markdown


def test_batch_validator_has_no_runtime_imports():
    source_path = Path("tools/decision/decision_engine_batch_validate.py")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = set()
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
            imported_modules.add(node.module)

    forbidden_roots = {"polymarket", "config", "utils"}
    assert imported_roots.isdisjoint(forbidden_roots)
    assert "tools.decision.decision_engine_prototype" in imported_modules
