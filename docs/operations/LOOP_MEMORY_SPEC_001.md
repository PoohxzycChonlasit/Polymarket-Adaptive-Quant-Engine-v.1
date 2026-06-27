# LOOP_MEMORY_SPEC_001

**Date:** 2026-06-27  
**Document type:** Operations specification  
**Destination:** `docs/operations/`

---

## 1. Purpose

Loop Memory records are compact, machine-readable JSON files that summarize completed loops. They allow future AI sessions to quickly understand what was done without reading long reports.

A session starting fresh can `ls docs/operations/loop_memory/` and `cat` the relevant records to reconstruct the project's recent loop history in seconds.

---

## 2. File Location Policy

All loop memory records live at:

```
docs/operations/loop_memory/LOOP_MEMORY_YYYYMMDD_NNN.json
```

- `YYYYMMDD` — date the loop completed (UTC)
- `NNN` — 3-digit sequence number (001, 002, ...)
- Files are append-only; never delete or overwrite a committed record

---

## 3. JSON Schema

```json
{
  "$schema": "loop_memory_v1",
  "date": "YYYY-MM-DD",
  "loop_id": "LOOP_NAME_001",
  "task_class": 3,
  "scope": ["file1", "file2"],
  "forbidden_scope_confirmed": true,
  "result": "PASS",
  "repairs": 0,
  "evidence_grade": "B",
  "commits": ["abc1234"],
  "commit_messages": ["docs: example change"],
  "acceptance_criteria": {
    "criterion_name": true
  },
  "files_changed": 3,
  "net_lines": 50,
  "next_recommendation": "Free text describing what should happen next.",
  "notes": "Optional brief notes."
}
```

---

## 4. Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `$schema` | string | Always `"loop_memory_v1"` |
| `date` | string | ISO date (YYYY-MM-DD) |
| `loop_id` | string | Matches the loop task name |
| `task_class` | int | 0–9 per task class system |
| `result` | string | `"PASS"`, `"PARTIAL"`, or `"FAIL"` |
| `repairs` | int | Number of repair iterations (0–3) |
| `evidence_grade` | string | Highest evidence grade reached: `"A"`, `"B"`, `"C"`, `"D"` |
| `commits` | array | Short SHAs of commits produced |
| `forbidden_scope_confirmed` | bool | `true` if forbidden scope was verified untouched |

---

## 5. Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `scope` | array | Files/directories in allowed scope |
| `commit_messages` | array | Full commit messages (one per commit) |
| `acceptance_criteria` | object | Each criterion name mapped to `true`/`false` |
| `files_changed` | int | Total file count in commit(s) |
| `net_lines` | int | Net line change across all commits |
| `next_recommendation` | string | What the next AI session should do |
| `notes` | string | Any brief contextual note |

---

## 6. Evidence Grade Field

Use the highest grade achieved during the loop:

| Grade | Meaning |
|-------|---------|
| A | Runtime observed (paper run, JSONL) |
| B | Source code verified (compile, import, git diff) |
| C | Test suite verified (pytest) |
| D | Documentation only |

A docs-only loop should record `"evidence_grade": "D"`. A runtime validation loop should record `"evidence_grade": "A"`.

---

## 7. Examples

### Docs housekeeping loop (Class 3)

```json
{
  "$schema": "loop_memory_v1",
  "date": "2026-06-27",
  "loop_id": "FILE_INDEX_DOCUMENTATION_MAP_REFRESH_LOOP_001",
  "task_class": 3,
  "result": "PASS",
  "repairs": 0,
  "evidence_grade": "B",
  "commits": ["c3449d5"],
  "forbidden_scope_confirmed": true,
  "next_recommendation": "Proceed to Batch 3C gate check."
}
```

### Runtime refactor loop (Class 6)

```json
{
  "$schema": "loop_memory_v1",
  "date": "2026-06-27",
  "loop_id": "BATCH_3B2_IMPLEMENTATION_001",
  "task_class": 6,
  "result": "PASS",
  "repairs": 0,
  "evidence_grade": "A",
  "commits": ["381cbc4"],
  "acceptance_criteria": {
    "py_compile": true,
    "import_ok": true,
    "zero_new_test_failures": true,
    "paper_5_cycles_exit_0": true,
    "jsonl_cadence_fields_present": true
  },
  "forbidden_scope_confirmed": true,
  "next_recommendation": "Post-commit runtime validation, then start Batch 3C gate."
}
```
