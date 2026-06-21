# README_REFRESH_AUDIT_001

Mode: DOCUMENTATION REWRITE

## Sources Reviewed

- `CURRENT_PROJECT_STATUS.md`
- `FILE_INDEX.md`
- `DOCUMENTATION_MAP.md`
- `README.md`
- `docs/`
- `tools/`
- `tests/`

## Current Verified State

- Repository identity: Adaptive Polymarket Quant Research Platform for BTC/ETH 5-minute Polymarket research.
- Runtime status: paper-first and not live-trading ready.
- Safety status: live execution remains unproven; live trading must not be described as enabled.
- Evidence posture: observability-first and replay-first.
- Phase B telemetry is implemented.
- Phase B schema isolation is implemented through `runtime/quant_data/signal_filter_shadow_phase_b/`.
- Legacy shadow telemetry remains separate under `runtime/quant_data/signal_filter_shadow/`.
- Daily evidence tooling exists:
  - `tools/phase_b_daily_evidence_collector.py`
  - `tools/phase_b_daily_report.py`
  - `tools/phase_b_run_daily_pipeline.py`
- Snapshot archive tooling exists:
  - `tools/phase_b_snapshot_archiver.py`
  - `runtime/quant_data/reports/phase_b_daily_snapshots/`
- Weekly review tooling exists:
  - `tools/phase_b_weekly_review_engine.py`
  - `tests/test_phase_b_weekly_review_engine.py`
- Weekly review source-of-truth governance is implemented in tooling:
  - `source_of_truth = "snapshot_archive"`
  - `raw_telemetry_used = False`
  - output defaults to `scratch/phase_b_weekly_review/`
- Documentation reorganization is reflected in:
  - `docs/architecture/`
  - `docs/audits/`
  - `docs/reports/`
  - `docs/evidence/`
  - `docs/research/`
  - `docs/operations/`

## Outdated Statements

- The prior README still described the project mainly as a general adaptive trading system and did not fully identify the current source-of-truth governance fix.
- The prior README did not clearly document the Weekly Review Engine as implemented.
- The prior README did not make the snapshot archive the explicit weekly review source of truth.
- The prior README did not explicitly name the runtime ownership manager as a current runtime component.
- The prior README treated roadmap items too broadly and could be read as implying future phases were closer to completion than verified.

## Missing Systems

- `tools/phase_b_weekly_review_engine.py`
- Weekly review outputs:
  - `scratch/phase_b_weekly_review/phase_b_weekly_review.json`
  - `scratch/phase_b_weekly_review/phase_b_weekly_review.md`
- Snapshot archive source-of-truth rule for weekly governance.
- Runtime ownership guard:
  - `utils/runtime_ownership.py`
  - `runtime/ownership/paper_runtime_owner.json`
  - `runtime/ownership/archive/`
- Documentation reorganization warning: files in `docs/audits/`, `docs/reports/`, and `docs/evidence/` are historical records unless explicitly referenced as active.

## Obsolete Architecture Sections

- Older broad diagrams did not separate:
  - Runtime Layer
  - Research Layer
  - Evidence Layer
  - Governance Layer
- Older architecture language did not distinguish Phase B isolated telemetry from legacy shadow telemetry.
- Older architecture language did not clearly separate active runtime from offline execution-paper tooling.

## Obsolete Roadmap Sections

- Any roadmap that implies completed live execution, autonomous trading, or Phase C promotion is obsolete.
- Any roadmap that treats future strategy, sizing, risk, or execution changes as implied next steps is obsolete.
- Current roadmap should be limited to verified operational work:
  - continue Phase B accumulation,
  - run daily and weekly evidence reviews,
  - preserve snapshot source-of-truth governance,
  - conduct promotion review only after gates are satisfied.

## Obsolete Operational Instructions

- README should not tell operators to rely on legacy shadow telemetry for Phase B evidence.
- README should not present daily dashboards as trade approval.
- README should not present weekly review output as an automatic promotion mechanism.
- README should not direct operators toward live mode except to state that live trading is not enabled and not ready.

## Rewrite Requirements

The README rewrite should:

- State the current purpose as Adaptive Polymarket Quant Research Platform.
- State paper-first, observability-first, replay-first, not live-trading ready.
- Document runtime, research, evidence, and governance layers.
- Include current runtime components:
  - `main.py`
  - `polymarket/trader.py`
  - shadow telemetry
  - paper runtime
  - ownership manager
- Include Phase B evidence system:
  - `signal_filter_shadow_phase_b`
  - Daily Evidence Collector
  - Daily Report Generator
  - Snapshot Archive
  - Weekly Review Engine
- Document governance flow:
  - Telemetry -> Daily Evidence -> Daily Dashboard -> Snapshot Archive -> Weekly Review -> Promotion Review
- Reflect current documentation layout.
- Keep limitations and roadmap conservative.
