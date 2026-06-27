# TOOL_PIPELINE_ENGINE_001

**Date:** 2026-06-27  
**Document type:** Architecture design  
**Destination:** `docs/architecture/`  
**Status:** DESIGN — Phase 2 implementation target

---

## 1. Purpose

The Tool Pipeline Engine (TPE) is the execution layer of FLAOS. It chains registered verification tools in the correct order for each workflow tier, accumulates evidence grades, and surfaces the first failure for repair.

---

## 2. Tool Registry

Tools are registered with a machine-readable schema. The registry lives at `docs/operations/TOOL_REGISTRY_001.json` (to be created in Phase 2).

### Core Tools

| tool_id | command | grade | stop_on_fail | timeout_s |
|---------|---------|-------|-------------|-----------|
| `git_status_clean` | `git status --short | grep -v "^??" | wc -l` = 0 | B | true | 5 |
| `py_compile` | `python -m py_compile {files}` | B | true | 10 |
| `import_ok` | `python -c "from polymarket.trader import PolymarketTrader; print('OK')"` | B | true | 15 |
| `pytest_targeted` | `pytest {test_files} -q` | C | true | 120 |
| `pytest_full` | `pytest tests/ -q` | C | false | 300 |
| `forbidden_grep` | `git diff -- {files} \| grep "{patterns}"` = empty | B | true | 5 |
| `scope_check` | `git diff --cached --name-only \| grep -v "{allowed}"` = empty | B | true | 5 |
| `paper_run` | `timeout 420 python main.py --mode paper ...` | A | false | 480 |
| `jsonl_field_check` | Python: verify fields in event stream | A | false | 10 |
| `line_count_check` | `wc -l {file}` < {limit} | B | false | 5 |
| `disk_usage_check` | `du -sh runtime/event_stream/` < 4GB | B | false | 5 |

---

## 3. Tool Pipeline by Tier

```
TIER FAST (Class 0/3 with prior PASS):
  git_status_clean → scope_check → [commit]

TIER LOOP (Class 3/4/9):
  git_status_clean → py_compile → import_ok → scope_check → forbidden_grep → [commit]

TIER LOOP+ (Class 6-low):
  git_status_clean → py_compile → import_ok → pytest_targeted → scope_check → forbidden_grep → [commit]

TIER STANDARD (Class 6-high, 1):
  git_status_clean → py_compile → import_ok → pytest_targeted → scope_check → forbidden_grep → line_count_check → [commit]

TIER GATE (Class 7):
  git_status_clean → py_compile → import_ok → pytest_targeted → scope_check → forbidden_grep → paper_run → jsonl_field_check → [commit]

TIER GATE-LIVE (Class 8):
  MANUAL — no automated pipeline
```

---

## 4. Evidence Accumulation

The TPE accumulates evidence grade as tools run:

```
start:        grade = D
after git_status_clean: grade = D (no upgrade yet)
after py_compile:      grade = B
after import_ok:       grade = B (already B)
after pytest_targeted: grade = C
after paper_run:       grade = A
after jsonl_field_check: grade = A (stays)
```

The pipeline continues until the tier's minimum grade is reached AND all stop_on_fail tools pass.

---

## 5. Failure Routing

When a tool fails:

```
tool fails
  → is this tool stop_on_fail = true?
      YES → current_repair_count++
             if < max_repairs → REPAIR state
             else → STOP_AND_ESCALATE
      NO  → log warning, continue pipeline, grade capped at current level
```

---

## 6. Tool Composition

Tools can be composed into pipelines without code changes. The pipeline for each tier is declared in `docs/operations/TOOL_PIPELINES_001.json` (Phase 2). Adding a new tier or variant only requires editing the JSON, not the tool implementations.

---

## 6b. Operational Files (created 2026-06-27)

The Tool Registry and Pipeline specs are now live in `docs/operations/`:

- **`TOOL_REGISTRY_001.json`** — 32 registered tools across 7 categories with grade, risk, scope, and stop conditions
- **`TOOL_PIPELINES_001.json`** — 6 pipelines (DOCS_LOOP, HEALTH_CHECK_LOOP, LOW_RISK_REFACTOR_LOOP, RUNTIME_VALIDATION_LOOP, GATE_WORKFLOW, HIGH_RISK_STOP_WORKFLOW)

This completes v1 (spec) and v2 (JSON schema) migration phases simultaneously.

---

## 7. Migration Plan

| Phase | Implementation |
|-------|---------------|
| v0 (now) | AI runs tools manually, records results in report |
| v1 | Markdown checklist: AI checks off each tool as it runs |
| v2 | JSON pipeline: AI reads pipeline spec, runs tools in order, records evidence |
| v3 | Shell script: `run_pipeline.sh LOOP+` executes the full tool chain |
| v4 | Python: `from tools.tpe import ToolPipeline; ToolPipeline("LOOP+").run()` |

---

## 8. Agent Pipeline Integration

The Agent Pipeline (AP) and Tool Pipeline (TPE) are parallel concerns:
- AP selects WHO does the work (which agent roles, context budget)
- TPE verifies WHAT was done (tool chain, evidence grade)

They both report to the LRE. The LRE's EXECUTE state calls AP; the VERIFY state calls TPE.
