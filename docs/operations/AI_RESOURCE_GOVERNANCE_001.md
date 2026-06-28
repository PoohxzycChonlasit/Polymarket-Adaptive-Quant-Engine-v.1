# AI_RESOURCE_GOVERNANCE_001

**Status:** ACTIVE  
**Date:** 2026-06-28  
**Purpose:** Prevent resource overload and parallel heavy process conflicts during AI-assisted development sessions.

---

## Why This Exists

On 2026-06-28, multiple heavy background processes were launched in parallel (canonical builder × 3, full risk-log load, backtest grid). The machine required a restart. This doc governs how AI agents manage compute resources.

---

## Hard Rules

### 1. Maximum Concurrent Heavy Processes: 1

Only ONE of the following may run at a time:
- Canonical context builder (any date range)
- BacktestEngineV2 scenario grid (100+ configs)
- pytest suite (full repo)
- Full historical data load

**If a heavy process is running: STOP before launching another.**

### 2. Maximum Concurrent Background Processes: 1

Only ONE `run_in_background=true` task is permitted per turn. Wait for its notification before launching the next.

**If notified of a background completion: process it before starting a new background task.**

### 3. No Parallel pytest + Builder + Backtest

Never launch in the same turn:
- pytest AND builder
- builder AND backtest grid
- backtest grid AND full data load

Run these sequentially with verification between each.

### 4. No Full-Repo pytest Without Explicit Approval

Targeted test runs only unless the operator explicitly says "run all tests":

```bash
# GOOD — targeted
.venv/Scripts/pytest.exe tests/test_canonical_trade_context_builder.py -q

# REQUIRES EXPLICIT APPROVAL
.venv/Scripts/pytest.exe tests/ -q
```

### 5. No Full Historical Builder Without Explicit Approval

Full-range builder (all 47 dates) requires operator approval. Default to date-range batches of ≤14 days.

```bash
# GOOD — targeted batch
.venv/Scripts/python.exe tools/canonical_trade_context_builder.py --start-date 2026-06-15 --end-date 2026-06-27

# REQUIRES EXPLICIT APPROVAL
.venv/Scripts/python.exe tools/canonical_trade_context_builder.py  # no args = all 47 dates
```

### 6. Always Run Heavy Tasks Sequentially

For tasks A, B, C that are each heavy:
- Run A → wait for completion → verify → run B → wait → verify → run C

Never chain heavy tasks without completion verification between them.

### 7. Always Announce Resource Estimate Before a Heavy Task

Before launching any builder, backtest grid, or full test run, state:
- Estimated duration
- Estimated memory/CPU
- What will be blocked while it runs

Example: *"Running June 15-27 builder. Est. 15-30s. No other heavy tasks until complete."*

### 8. Risk-Log Skip is Default

The canonical context builder must always use `--skip-risk-log` (which is now the default). Loading risk_log adds 2.6 GB of data that is indexed but never consumed. Never use `--include-risk-log` without explicit operator instruction.

### 9. Prefer Targeted pytest First

Order of preference:
1. Single test file
2. Keyword filter (`-k "test_name"`)
3. Single module subset
4. Full repo (requires explicit approval)

### 10. Use Temp Output Dirs for Intermediate Builder Runs

When running the builder for analysis (not writing a final canonical artifact), use a scratch output dir to avoid overwriting production outputs:

```bash
mkdir -p runtime/reports/scratch
.venv/Scripts/python.exe tools/canonical_trade_context_builder.py --start-date ... --output-dir runtime/reports/scratch
```

Only write to `runtime/reports/` for final artifact production.

### 11. Preserve Runtime Evidence

Never delete, overwrite, or rotate files in `runtime/reports/`, `runtime/quant_data/`, or `runtime/research_exports/` without explicit operator approval.

---

## Checklist Before Any Heavy Task

```
[ ] No other background process is currently running
[ ] git status is clean (or operator has approved dirty state)
[ ] GitHub is current (git branch -vv shows no "ahead N")
[ ] Resource estimate stated
[ ] Output directory confirmed (scratch vs production)
[ ] Sequential order confirmed if this is one of multiple tasks
```

---

## Resource Classification

| Task | Classification | Max parallel | Approval required |
|---|---|---|---|
| Single pytest file | Light | 2 | No |
| Full repo pytest | Heavy | 1 | Yes |
| Builder ≤14 days | Medium | 1 | No |
| Builder all dates | Heavy | 1 | Yes |
| Backtest grid 100+ | Heavy | 1 | No |
| Backtest grid 1000+ | Heavy | 1 | Yes |
| git push | Light | 1 | No |
| Full data analysis | Heavy | 1 | No |
