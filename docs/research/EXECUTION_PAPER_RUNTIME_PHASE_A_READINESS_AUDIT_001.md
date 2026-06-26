# EXECUTION_PAPER_RUNTIME_PHASE_A_READINESS_AUDIT_001

Date: 2026-06-20

Mode: READ ONLY / NO CODE / NO IMPLEMENTATION

Runtime behavior changed: No

Strategy/risk/execution changed: No

Commit status: Not committed

## Objective

Verify that Execution Paper Runtime Phase A can be implemented safely without touching Signal Runtime behavior.

Input design:

- `docs/research/EXECUTION_PAPER_RUNTIME_PHASE_A_IMPLEMENTATION_PLANNING_001.md`
- Phase A verdict: `READY_TO_PLAN_CODE_IMPLEMENTATION`

This audit inspected repo structure, `runtime/quant_data` layout, journal writer patterns, event logger patterns, CLI entrypoint patterns, and test structure. It did not modify runtime, code, strategy, risk, sizing, config, or live behavior.

## Current Repo Structure

Top-level implementation-relevant directories:

| Path | Current Role |
|---|---|
| `polymarket/` | active Polymarket runtime and trading coordinator code |
| `utils/` | shared runtime utilities, logging, ownership, risk, Telegram, config helpers |
| `tools/` | offline analyzers, report builders, scanners, runners |
| `tests/` | pytest suite with tool-specific and runtime-specific tests |
| `runtime/quant_data/` | append-only quant evidence data |
| `docs/research/` | research, design, and governance docs |

Current `runtime/quant_data` categories:

| Category |
|---|
| `decision_log` |
| `execution_log` |
| `market_snapshots` |
| `orderbook_lineage` |
| `path_truth` |
| `research_log` |
| `risk_log` |
| `signal_filter_shadow` |
| `stop_loss_shadow` |
| `system_health` |
| `trade_journal` |

No existing `runtime/quant_data/execution_paper/` category was found.

## 1. Where Should Phase A Code Live?

### Option A - `polymarket/execution_paper/`

Assessment: not recommended for Phase A.

Reason:

- `polymarket/` is active runtime/trading code.
- Placing Phase A there increases risk of accidental imports from `trader.py`, order management, sizing, risk, or live client code.
- It would make a docs/planning skeleton look like runtime trading capability too early.

### Option B - `runtime/execution_paper/`

Assessment: not recommended.

Reason:

- `runtime/` is data/output/state space, not source code.
- Source code under `runtime/` would blur artifact ownership and make cleanup/retention riskier.

### Option C - `tools/execution_paper/`

Assessment: recommended in spirit, with repo-pattern adjustment.

Reason:

- Existing offline implementation work lives in `tools/`.
- Existing paired tests follow `tools/<tool>.py` plus `tests/test_<tool>.py`.
- `tools/` already contains bounded scanners, offline runners, manifest generators, replay tools, and evidence compilers.
- No `tools/__init__.py` package exists, so the repo currently favors flat tool modules over nested tool packages.

Exact Phase A recommendation:

```text
tools/execution_paper_runtime.py
tests/test_execution_paper_runtime.py
```

If Phase B or later grows beyond one module, then split into a package-like directory later:

```text
tools/execution_paper/
```

but Phase A should start flat to match existing repo style.

### Option D - `utils/execution_paper/`

Assessment: not recommended for Phase A.

Reason:

- `utils/` is shared runtime utility space.
- Adding execution-paper utilities there would make later accidental imports from Signal Runtime more likely.
- Phase A should prove isolation before any shared utility is introduced.

### Directory Verdict

```text
Recommended code location: tools/execution_paper_runtime.py
Recommended tests: tests/test_execution_paper_runtime.py
```

## 2. Existing Utilities That Can Be Reused

### JSONL Writer

Reusable pattern:

- `utils/quant_event_logger.py`
- `tools/outcome_truth_streaming_scan.py`
- `tools/official_resolution_full_history_runner.py`

Recommendation:

Use a dedicated Phase A append-only writer based on the patterns in existing tools. Do not extend `QuantEventLogger` in Phase A.

Reason:

- Extending `QuantEventLogger._CATEGORY_BY_METHOD` would modify shared runtime logging behavior.
- A dedicated writer under `tools/execution_paper_runtime.py` keeps execution-paper outputs isolated.

### Event Logger

Reusable as reference only:

- `QuantEventLogger` event envelope:
  - `timestamp_utc`
  - `event_type`
  - `mode`
  - `run_id`
  - `source_module`
  - `schema_version`
  - `payload`

Do not modify:

```text
utils/quant_event_logger.py
```

in Phase A.

### Timestamp Helpers

Reusable pattern:

- `utc_now()` helpers in `tools/outcome_truth_streaming_scan.py`
- `utc_now()` helpers in `tools/official_resolution_full_history_runner.py`
- `datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")`

Recommendation:

Implement a local `utc_now()` inside the Phase A tool rather than import runtime modules.

### Run ID Helpers

Reusable pattern:

- `QuantEventLogger` run id format:

```text
YYYYMMDDTHHMMSSZ_<pid>_<8-hex>
```

Recommendation:

Use a local execution run id:

```text
execution_<YYYYMMDDTHHMMSSZ>_<pid>_<8-hex>
```

Do not import `main.py` or instantiate `PolymarketTrader` for run id creation.

### Path Utilities

Reusable pattern:

- `DEFAULT_QUANT_DATA_DIR = Path("runtime/quant_data")`
- output path validation from `tools/outcome_truth_streaming_scan.py`
- output lock pattern from `tools/official_resolution_full_history_runner.py`

Recommendation:

Phase A should validate:

- source paths are under `runtime/quant_data`;
- output paths are under `runtime/quant_data/execution_paper`;
- checkpoint/report outputs are never inside source category directories.

### Test Fixtures

Reusable test patterns:

- `tmp_path` synthetic JSONL writers from many tests.
- no-runtime-import guard from `tests/test_official_resolution_full_history_runner.py`.
- streaming/no-whole-file-loading checks from `tests/test_outcome_truth_streaming_scan.py`.
- checkpoint/resume tests from outcome-truth scanner and full-history runner.

Recommended fixture style:

```text
synthetic trade_journal rows
synthetic execution_paper journals
tmp_path output root
no runtime module import assertion
```

## 3. Files Phase A Would Likely Add

Proposed source file:

```text
tools/execution_paper_runtime.py
```

Proposed test file:

```text
tests/test_execution_paper_runtime.py
```

Expected generated artifacts during tests or manual dry runs:

```text
runtime/quant_data/execution_paper/checkpoints/YYYY-MM-DD/<execution_run_id>.json
runtime/quant_data/execution_paper/journals/trade/YYYY-MM-DD.jsonl
runtime/quant_data/execution_paper/journals/position/YYYY-MM-DD.jsonl
runtime/quant_data/execution_paper/journals/equity/YYYY-MM-DD.jsonl
runtime/quant_data/execution_paper/journals/reject/YYYY-MM-DD.jsonl
runtime/quant_data/execution_paper/reconciliations/YYYY-MM-DD/<execution_run_id>_reconciliation.json
runtime/quant_data/execution_paper/reports/YYYY-MM-DD/<execution_run_id>_validation.json
runtime/quant_data/execution_paper/state/<execution_run_id>_open_positions.json
```

Generated runtime artifacts should not be committed unless a later task explicitly requests fixture artifacts. Tests should write to `tmp_path`.

## 4. Files That Must Not Be Modified

Hard no-touch files for Phase A:

| File | Reason |
|---|---|
| `polymarket/trader.py` | active Signal Runtime coordinator |
| `polymarket/order_manager.py` | order/risk plan construction |
| `utils/risk_manager.py` | canonical risk policy |
| `polymarket/position_sizing.py` | sizing logic |
| `config/settings.py` | runtime config behavior |
| `.env` | secrets/live-risk config |
| `main.py` | runtime dispatcher; avoid until Phase A proves standalone safety |
| `utils/quant_event_logger.py` | shared runtime JSONL categories |
| `utils/runtime_ownership.py` | active paper runtime ownership guard |
| `utils/telegram_alerts.py` | alert routes/cooldowns |
| `utils/telegram_reporter.py` | Telegram reporting behavior |

Phase A should also avoid modifying:

- `polymarket/client.py`
- `polymarket/position_manager.py`
- `polymarket/risk_modes.py`
- `polymarket/expected_value.py`
- `polymarket/probability_model.py`
- any live wallet / allowance code

## 5. CLI Strategy

Options:

| Option | Assessment |
|---|---|
| A. separate script | Safe if placed under `tools/` |
| B. `main.py` subcommand | Not recommended for Phase A |
| C. pytest-only skeleton | Useful but insufficient for operator dry-run later |
| D. offline tool first | Recommended |

Recommended CLI strategy:

```text
D. offline tool first, implemented as a separate script under tools/
```

Concrete Phase A approach:

```text
tools/execution_paper_runtime.py
```

with a CLI that can run bounded skeleton/dry-run workflows without touching `main.py`.

Recommended future command shape:

```text
py -3.11 tools/execution_paper_runtime.py ^
  --source-dir runtime/quant_data ^
  --output-dir runtime/quant_data/execution_paper ^
  --track 5_share ^
  --starting-bankroll 250 ^
  --max-events 1000 ^
  --dry-run
```

Phase A should not add:

```text
main.py --mode execution-paper
```

until the tool passes isolation, checkpoint, journal, and reconciliation tests.

## 6. Test Plan

Minimum Phase A tests:

### Schema Validation

Required tests:

- valid `execution_paper_open` passes;
- valid `execution_paper_close` passes;
- valid `execution_paper_reject` passes;
- valid `execution_paper_equity_snapshot` passes;
- valid `execution_paper_position_snapshot` passes;
- missing required field fails closed;
- unknown optional field does not fail.

### Append-Only Writer

Required tests:

- creates expected directory under output root;
- appends one JSONL row per event;
- does not overwrite existing rows;
- fails if output path is outside allowed execution-paper root;
- atomic checkpoint/report writes leave no temp file.

### Checkpoint Write / Read

Required tests:

- checkpoint contains `last_processed_trade`;
- checkpoint contains `last_processed_timestamp`;
- checkpoint contains source file/line/hash;
- resume starts after the checkpointed event;
- source mutation or hash mismatch fails closed.

### Duplicate Prevention

Required tests:

- identical duplicate source event is skipped;
- conflicting duplicate source event fails closed;
- duplicate open for active source replay key is rejected;
- duplicate close for same execution position fails reconciliation.

### Reconciliation Failure

Required tests:

- orphan close fails;
- orphan open fails;
- duplicate close fails;
- equity mismatch fails;
- journal replay reproduces ledger in passing case.

### No Signal Runtime Mutation

Required tests:

- source tool imports do not include `polymarket.trader`;
- source tool imports do not include `polymarket.order_manager`;
- source tool imports do not include `utils.risk_manager`;
- source tool imports do not include `polymarket.position_sizing`;
- synthetic run writes only under execution-paper output root;
- Signal Runtime source fixture files remain byte-identical.

Recommended test command:

```text
py -3.11 -m pytest tests/test_execution_paper_runtime.py -q
```

## 7. Risk Review

### Contamination Risks

| Step | Risk | Severity | Control |
|---|---|---:|---|
| placing code under `polymarket/` | accidental runtime import / authority confusion | High | use `tools/` |
| modifying `main.py` | makes Phase A look like supported runtime mode | High | use separate script only |
| extending `QuantEventLogger` | changes shared runtime logger categories | Medium/High | dedicated writer |
| importing risk/sizing modules | may couple execution validation to Signal Runtime state | High | static no-import test |
| writing under existing `trade_journal` | contaminates Signal Mode evidence | High | dedicated execution-paper root |
| using runtime ownership guard | could interfere with paper runtime owner file | High | separate output lock only |
| auto-repairing reconciliation | could hide evidence corruption | Medium/High | fail closed, no repair |
| reading huge JSONL into memory | repeats prior memory incident class | Medium | stream line-by-line |
| using Signal Runtime risk mode as authority | imports non-stationary balance state | High | record as context only |
| enabling Option D active exits | imports unvalidated stop behavior | High | shadow only |

### Safe Implementation Principles

- Phase A is an offline tool/skeleton, not a trading runtime.
- Source journals are read-only.
- Execution output is isolated.
- No live client, wallet, or order path exists.
- Checkpoint and reconciliation fail closed.
- Signal Runtime remains unaware of Execution Runtime output.

## Final Recommendation

Verdict:

```text
APPROVE_PHASE_A_CODE_IMPLEMENTATION
```

Approval scope:

```text
tools/execution_paper_runtime.py
tests/test_execution_paper_runtime.py
```

Required constraints for implementation:

- no modifications to `main.py`;
- no modifications to `polymarket/`;
- no modifications to `utils/risk_manager.py`;
- no modifications to `polymarket/position_sizing.py`;
- no modifications to `utils/quant_event_logger.py`;
- no modifications to `.env` or config;
- no Signal Runtime restart;
- no live behavior;
- generated artifacts excluded unless explicitly requested.

Reason:

The repo already has strong patterns for offline tools, atomic checkpointing, append-only JSONL evidence, bounded source scanning, no-runtime-import tests, and replay verification. Phase A can be implemented safely as an isolated `tools/` module with paired tests, provided it does not touch active runtime packages or shared runtime logging categories.

