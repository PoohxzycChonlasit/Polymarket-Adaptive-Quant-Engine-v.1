# Polymarket Adaptive Quant Engine

Polymarket Adaptive Quant Engine is an Adaptive Polymarket Quant Research Platform for BTC/ETH 5-minute prediction-market research.

The repository is currently:

- Paper-first
- Observability-first
- Replay-first
- Not live-trading ready

Live trading is not enabled. The current system exists to collect evidence, validate passive filters, preserve replayable research records, and support governance review before any promotion decision.

## Architecture Diagram

```text
Polymarket Data
  -> Paper Runtime
  -> Shadow Telemetry
  -> Daily Evidence
  -> Daily Dashboard
  -> Snapshot Archive
  -> Weekly Review
  -> Governance Review
```

The active runtime is paper-only. The evidence and governance layers are designed to decide what deserves review, not to deploy trades automatically.

## Project Overview

The project studies Polymarket 5-minute BTC/ETH binary markets using a paper runtime, structured telemetry, offline replay tools, and evidence governance.

Current purpose:

```text
Adaptive Polymarket Quant Research Platform
```

The system is designed to answer research and safety questions before changing strategy, sizing, risk, execution, or live trading behavior.

Current operating principle:

```text
Telemetry
  -> Evidence
  -> Replay / Review
  -> Governance
  -> Promotion decision only if gates are satisfied
```

No dashboard, report, replay, weekly review, or telemetry stream is an automatic trade approval mechanism.

## Quick Start

Clone the repository:

```bash
git clone <repository-url>
cd Polymarket-Adaptive-Quant-Engine-v.1
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the paper runtime:

```bash
python main.py --mode paper --interval 60
```

This command starts paper mode. It does not authorize live trading.

## Current Status

| Area | Current state |
| --- | --- |
| Runtime mode | PAPER MODE ONLY |
| Live trading | NOT ENABLED |
| Live readiness | NOT PROVEN |
| Paper runtime | ACTIVE |
| Phase B shadow telemetry | IMPLEMENTED |
| Phase B schema isolation | IMPLEMENTED |
| Daily evidence collection | IMPLEMENTED |
| Daily report dashboard | IMPLEMENTED |
| Snapshot archive system | IMPLEMENTED |
| Weekly review engine | IMPLEMENTED |
| Governance promotion | PENDING |
| Phase C runtime promotion | NOT STARTED |

The repository should not be described as live-ready until live order placement, fill detection, cancel behavior, allowance readiness, wallet sync, and position reconciliation are all proven with runtime evidence.

## Repository Maturity Matrix

| System | Current status | Boundary |
| --- | --- | --- |
| Paper Runtime | ACTIVE | Paper mode with simulated execution. |
| Ownership Guard | IMPLEMENTED | Blocks duplicate paper runtime and supports stale-owner recovery. |
| Phase B Telemetry | IMPLEMENTED | Passive shadow evidence only. |
| Daily Pipeline | IMPLEMENTED | Manual daily evidence/report/archive pipeline. |
| Snapshot Archive | IMPLEMENTED | Daily dashboards archived as review evidence. |
| Weekly Review | IMPLEMENTED | Snapshot archive is the review source of truth. |
| Replay Research | ACTIVE | Offline research and diagnostics only. |
| Live Execution | NOT ENABLED | Live readiness is not proven. |
| Wallet Sync | PARTIAL | Paper mode is safe; live wallet readiness remains constrained by live-readiness checks. |
| Position Reconciliation | PARTIAL | Live fill/cancel/reconcile lifecycle is not fully proven. |

## Current Architecture

```text
Runtime Layer
  -> Research Layer
  -> Evidence Layer
  -> Governance Layer
```

### Runtime Layer

The runtime layer scans markets, evaluates paper signals, simulates paper execution, and emits structured telemetry.

Key files:

| File | Role |
| --- | --- |
| `main.py` | CLI entrypoint, mode routing, paper runtime launch, runtime ownership acquisition. |
| `polymarket/trader.py` | Main paper trading coordinator, market analysis, paper execution path, telemetry hook points. |
| `utils/runtime_ownership.py` | Paper runtime ownership guard, duplicate-runtime prevention, stale-owner recovery. |
| `utils/quant_event_logger.py` | Structured JSONL event writer. |
| `polymarket/shadow_telemetry.py` | Passive Phase B shadow filter logic. |

Runtime ownership uses files under:

```text
runtime/ownership/
runtime/ownership/archive/
```

### Research Layer

The research layer contains offline analyzers, replay tools, candidate studies, and execution-reality tooling.

Examples:

| File | Role |
| --- | --- |
| `tools/replay_analyzer.py` | Offline replay summaries. |
| `tools/quant_data_quality.py` | JSONL quality and continuity checks. |
| `tools/shadow_filter_evaluator.py` | Offline shadow-filter evaluation. |
| `tools/execution_paper_runtime.py` | Isolated offline execution-paper runtime skeleton. |
| `tools/joined_records_builder.py` | Offline joined-record builder for shadow filter evaluation. |
| `tools/decision_log_slim_index.py` | Scratch-only decision-log slim index builder. |

Research tools are offline evidence tools. They do not authorize strategy, risk, sizing, execution, or live trading changes by themselves.

### Evidence Layer

The evidence layer stores runtime telemetry, daily dashboards, archived snapshots, and validation records.

Important paths:

| Path | Contents |
| --- | --- |
| `runtime/quant_data/` | Runtime JSONL telemetry and paper journals. |
| `runtime/quant_data/signal_filter_shadow_phase_b/` | Isolated Phase B telemetry category. |
| `runtime/quant_data/signal_filter_shadow/` | Legacy shadow telemetry category. |
| `runtime/quant_data/reports/phase_b_daily_snapshots/` | Immutable daily Phase B dashboard snapshots and index. |
| `scratch/phase_b_daily_reports/` | Generated daily dashboard JSON and Markdown. |
| `scratch/phase_b_weekly_review/` | Weekly review JSON and Markdown outputs. |
| `scratch/phase_b_7day_snapshot_summary.md` | Rolling snapshot summary. |

### Governance Layer

The governance layer prevents ad hoc promotion and preserves source-of-truth boundaries.

Key files:

| File | Role |
| --- | --- |
| `docs/research/ACTIVE_QUESTION.md` | Active research question gate. |
| `docs/research/AUDIT_REGISTRY.json` | Audit registry. |
| `docs/research/DECISION_REGISTRY.json` | Decision registry. |
| `docs/research/RESEARCH_AUTHORITY_MAP_V2.md` | Authority map for research evidence. |
| `tools/phase_b_weekly_review_engine.py` | Snapshot-based weekly governance review engine. |

The Weekly Review Engine uses the snapshot archive as its source of truth. It does not read raw telemetry as the weekly decision source.

## Runtime Components

| Component | Current role |
| --- | --- |
| `main.py` | Starts paper mode by default and supports explicit `--mode paper`. |
| `polymarket/trader.py` | Coordinates market scanning, signal evaluation, paper execution, and telemetry emission. |
| Paper runtime | Uses real market data with simulated execution; does not submit live orders. |
| Shadow telemetry | Emits passive filter evidence without changing runtime decisions. |
| Ownership manager | Blocks duplicate paper runtimes and recovers stale owner locks. |
| QuantEventLogger | Writes structured JSONL evidence under `runtime/quant_data/`. |

Safe explicit paper command:

```bash
python main.py --mode paper --interval 60
```

Do not use live mode for normal research operation.

## Phase B Evidence System

Phase B is the active passive evidence layer.

Implemented Phase B components:

| Component | File / path | Purpose |
| --- | --- | --- |
| Phase B shadow telemetry | `runtime/quant_data/signal_filter_shadow_phase_b/` | Isolated schema for passive filter evidence. |
| Legacy shadow telemetry | `runtime/quant_data/signal_filter_shadow/` | Older schema retained separately. |
| Daily Evidence Collector | `tools/phase_b_daily_evidence_collector.py` | Compiles daily Phase B telemetry and outcome-linked evidence. |
| Daily Report Generator | `tools/phase_b_daily_report.py` | Produces daily dashboard JSON and Markdown. |
| Manual Daily Pipeline | `tools/phase_b_run_daily_pipeline.py` | Runs daily report, archive, and summary steps. |
| Snapshot Archive | `tools/phase_b_snapshot_archiver.py` | Copies daily dashboards into immutable dated snapshot folders. |
| 7-Day Snapshot Summary | `tools/phase_b_snapshot_summary.py` | Builds rolling summary from archived snapshots. |
| Weekly Review Engine | `tools/phase_b_weekly_review_engine.py` | Performs snapshot-only weekly governance review. |

Phase B telemetry fields include:

- `filter_name`
- `filter_version`
- `filter_params`
- `shadow_pass`
- `shadow_reason`
- `would_trade`

Phase B telemetry is passive. It must not change paper entries, sizing, exits, risk modes, order routing, or live behavior.

## Governance Flow

```text
Telemetry
  -> Daily Evidence
  -> Daily Dashboard
  -> Snapshot Archive
  -> Weekly Review
  -> Promotion Review
```

Governance source-of-truth rule:

- Daily reports may read runtime telemetry.
- Archived daily snapshots preserve the evidence used for review.
- Weekly review reads the snapshot archive, not raw telemetry.
- Promotion review remains manual and evidence-gated.
- No filter promotion is automatic.

Weekly review output defaults:

```text
scratch/phase_b_weekly_review/phase_b_weekly_review.json
scratch/phase_b_weekly_review/phase_b_weekly_review.md
```

## Current Research Questions

Current research is focused on evidence accumulation and passive filter evaluation.

Active question areas:

| Question | Current purpose |
| --- | --- |
| Expectancy improvement | Determine whether passive filters improve realized paper expectancy versus baseline behavior. |
| Drawdown reduction | Determine whether filters reduce drawdown without destroying useful positive expectancy. |
| Passive filter evaluation | Compare filters such as block-style and combined shadow filters using Phase B evidence. |
| Promotion eligibility | Determine whether any filter reaches governance review quality without automatic deployment. |
| Evidence accumulation | Continue collecting enough daily and weekly evidence for stable conclusions. |

## Documentation Layout

Current documentation layout:

| Path | Role |
| --- | --- |
| `docs/` | Documentation root. |
| `docs/architecture/` | Architecture designs, schemas, and system blueprints. |
| `docs/audits/` | Point-in-time forensic and safety audits. |
| `docs/reports/` | Implementation, commit, migration, and milestone reports. |
| `docs/evidence/` | Validation evidence and real-data proof logs. |
| `docs/research/` | Research governance, candidate specs, active questions, and quant reports. |
| `docs/operations/` | Operational runbooks and deployment guidance. |

Root files are active entrypoints:

| File | Role |
| --- | --- |
| `README.md` | Current operator-facing overview. |
| `CURRENT_PROJECT_STATUS.md` | Current status and blockers. |
| `FILE_INDEX.md` | File map and active entrypoints. |
| `DOCUMENTATION_MAP.md` | Documentation routing and source-of-truth policy. |
| `PROJECT_RULES.md` | Project safety rules. |
| `AGENTS.md` | Codex/AI-agent operating boundaries. |
| `MASTER_AGENT_ROUTER.md` | Role-routing guide. |

Historical files in `docs/audits/`, `docs/reports/`, and `docs/evidence/` are preserved for auditability. They are not active operational instructions unless a current task or root status file explicitly names them.

## Documentation Navigation

Start here:

- [Current Project Status](CURRENT_PROJECT_STATUS.md)
- [File Index](FILE_INDEX.md)
- [Documentation Map](DOCUMENTATION_MAP.md)

Core documentation folders:

- [Architecture](docs/architecture/)
- [Research](docs/research/)
- [Evidence](docs/evidence/)
- [Reports](docs/reports/)
- [Audits](docs/audits/)

## Current Safe Operator Workflow

1. Start paper runtime.

   ```bash
   python main.py --mode paper --interval 60
   ```

2. Run a paper session and allow telemetry to accumulate.

3. Before shutdown, run the daily Phase B pipeline.

   ```bash
   python tools/phase_b_run_daily_pipeline.py --date YYYY-MM-DD
   ```

4. Verify daily dashboard and snapshot artifacts.

   Expected paths:

   ```text
   scratch/phase_b_daily_reports/phase_b_dashboard.json
   scratch/phase_b_daily_reports/phase_b_dashboard.md
   runtime/quant_data/reports/phase_b_daily_snapshots/YYYY-MM-DD/
   runtime/quant_data/reports/phase_b_daily_snapshots/phase_b_snapshot_index.json
   scratch/phase_b_7day_snapshot_summary.md
   ```

5. Run weekly governance review when enough snapshots exist.

   ```bash
   python tools/phase_b_weekly_review_engine.py --date YYYY-MM-DD
   ```

6. Review weekly outputs.

   ```text
   scratch/phase_b_weekly_review/phase_b_weekly_review.json
   scratch/phase_b_weekly_review/phase_b_weekly_review.md
   ```

7. Keep promotion decisions manual and evidence-gated.

Do not start live mode as part of this workflow.

## Current Known Limitations

- The project is not live-ready.
- Live order placement is not proven.
- Live fill, cancel, allowance, wallet sync, and reconciliation are not fully proven.
- Phase B evidence is still accumulating.
- Governance promotion gates are not yet satisfied.
- Weekly review output is evidence for review, not automatic deployment approval.
- Execution-paper tooling is offline and isolated from the active signal runtime.
- Legacy shadow telemetry still exists, but Phase B evidence uses the isolated `signal_filter_shadow_phase_b` category.
- Historical reports may be stale relative to root status and current tools.

## Current Roadmap

Verified current roadmap:

1. Continue paper-mode Phase B evidence accumulation.
2. Run the daily Phase B pipeline before runtime shutdown.
3. Preserve daily dashboards through the snapshot archive.
4. Run the Weekly Review Engine from archived snapshots.
5. Use governance review to decide whether any passive filter deserves promotion review.
6. Continue replay and execution-reality validation as offline research only.

No Phase C runtime promotion has started. No live trading promotion has started.

## What This Repository Is NOT

This repository is not:

- A live-trading system.
- An autonomous capital deployment system.
- A guaranteed-profitable strategy.
- A production-ready trading service.
- A signal-selling product.

It is a research and evidence platform. Treat all outputs as evidence for review, not as financial advice or automatic trading authorization.

## Safety Statement

This repository is currently PAPER MODE ONLY.

No live execution is enabled.

No autonomous capital deployment is authorized.

All promotion decisions require evidence review, governance checks, and explicit operator approval.
