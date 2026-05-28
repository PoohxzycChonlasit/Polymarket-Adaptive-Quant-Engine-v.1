# Quant Research Governance Navigation Hub

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Mode: docs-only navigation hub. No implementation, runtime mutation, replay execution, strategy change, risk change, execution change, threshold tuning, live change, or library install.

## Start Here

This is the top-level governance map for operators and future agents.

Current posture:

```text
Runtime mode: PAPER / SIGNAL_MODE
Research phase: PATH_TRUTH / EVIDENCE_FARMING
Executable truth: NOT_REACHED
Growth mode: BLOCKED
Live readiness: NOT_READY
```

Core rule:

```text
Runtime truth is emitted by runtime.
Research interpretation explains runtime truth.
Governance controls promotion.
Docs do not change runtime behavior.
Observability probes do not get a vote.
```

## 1. Canonical Reading Order

New operators should start here:

1. [GOVERNANCE_NAVIGATION_HUB.md](GOVERNANCE_NAVIGATION_HUB.md)
2. [INDEX.md](INDEX.md)
3. [INFRASTRUCTURE_GOVERNANCE_MAP.md](INFRASTRUCTURE_GOVERNANCE_MAP.md)
4. [runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md](runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md)
5. [runtime_health/OBSERVABILITY_PROBE_REGISTRY_DESIGN.md](runtime_health/OBSERVABILITY_PROBE_REGISTRY_DESIGN.md)
6. [performance/evidence_manifest_index_design.md](performance/evidence_manifest_index_design.md)
7. [performance/research_evidence_discovery_layer_design.md](performance/research_evidence_discovery_layer_design.md)
8. [performance/runtime_evidence_archive_boundary_design.md](performance/runtime_evidence_archive_boundary_design.md)
9. [path_truth/path_truth_multiday_coverage_monitor.md](path_truth/path_truth_multiday_coverage_monitor.md)
10. [executable_truth/executable_truth_frontier_map.md](executable_truth/executable_truth_frontier_map.md)
11. [runtime_health/signal_rejection_root_cause_audit.md](runtime_health/signal_rejection_root_cause_audit.md)
12. [runtime_health/empty_book_reality_investigation.md](runtime_health/empty_book_reality_investigation.md)

New agents should also read:

- `runtime/research_state/latest_research_state.md`
- `MASTER_AGENT_ROUTER.md`
- exactly one selected primary role doc under `docs/quant_agent_setup_md/roles/`
- zero to three supporting role docs only when the task crosses boundaries

## 2. Runtime Truth Hierarchy

Truth ladder:

```text
Signal Truth
-> Path Truth
-> Executable Truth
-> Growth Readiness
-> Live Readiness
```

Meaning:

| Layer | Current status | What it can support | What it cannot support |
|---|---|---|---|
| Signal Truth | `ACTIVE` | Model/EV/rejection/signal evidence. | Executable PnL or live readiness. |
| Path Truth | `ACTIVE` | Path checkpoints and direct replay-key continuity for post-wiring rows. | Fill, cancel, partial-fill, or executable truth. |
| Executable Truth | `NOT_REACHED` | Blocker maps and future ledger design. | Executable PnL approval. |
| Growth Readiness | `BLOCKED` | No current promotion. | Runtime scale-up. |
| Live Readiness | `NOT_READY` | No current promotion. | Live trading claims. |

Never skip a layer.

## 3. Probe Authority Hierarchy

Probe authority levels:

```text
evidence_only
diagnostic_only
offline_research_only
operator_review_required
policy_candidate
runtime_policy
forbidden
```

Default for new probes:

```text
probe_authority_level: evidence_only
policy_authority: none
runtime_decision_authority: false
execution_authority: false
risk_authority: false
```

Policy rule:

```text
Probe -> offline audit -> review doc -> implementation plan -> tests -> paper validation -> separate promotion decision
```

There is no direct `Probe -> Runtime Policy` path.

## 4. Evidence Authority Hierarchy

Evidence authority should be read in this order:

1. Runtime-emitted raw JSONL for the specific source/date/run.
2. Trade/path direct join keys, especially `(run_id, paper_trade_replay_key)`.
3. Validated source-specific audits.
4. Manifest/index summaries when they exist.
5. Research docs and cognition notes.
6. Operator interpretation.

Authority warnings:

- Raw paper evidence is not executable evidence.
- Signal PnL is not executable PnL.
- Path truth continuity is not fill truth.
- Offline replay is not runtime execution.
- Cognition metadata is not raw evidence.
- Archive custody is not truth promotion.

## 5. Governance Review Flow

Standard flow:

```text
Docs/design
-> operator review
-> scoped implementation task
-> targeted tests
-> paper validation if runtime-emitted
-> offline audit
-> governance review
-> possible policy-candidate review
```

Review required for:

- runtime code changes,
- new runtime-emitted probes,
- new JSONL source folders,
- live-observed labels,
- governance-sensitive probes,
- new runtime dependencies,
- archive/compression/deletion actions,
- any policy-candidate transition,
- any strategy/risk/execution/live change.

Docs-only design does not require runtime tests.

## 6. Probe Lifecycle Flow

Probe lifecycle:

```text
DESIGNED
-> REVIEWED
-> IMPLEMENTED_OBSERVABILITY_ONLY
-> PAPER_VALIDATED
-> OFFLINE_ANALYZED
-> POLICY_CANDIDATE
```

Other terminal/side states:

```text
REJECTED
DEPRECATED
ARCHIVED
```

Blocked transitions:

- `DESIGNED -> IMPLEMENTED_OBSERVABILITY_ONLY` without review.
- `DESIGNED -> POLICY_CANDIDATE`.
- `PAPER_VALIDATED -> runtime_policy`.
- `OFFLINE_ANALYZED -> runtime_policy`.
- `POLICY_CANDIDATE -> runtime_policy` without a separate implementation task.

Primary probe docs:

- [runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md](runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md)
- [runtime_health/OBSERVABILITY_PROBE_REGISTRY_DESIGN.md](runtime_health/OBSERVABILITY_PROBE_REGISTRY_DESIGN.md)
- [runtime_health/orderbook_lineage_probe_v1_design.md](runtime_health/orderbook_lineage_probe_v1_design.md)

## 7. Archive And Discovery Flow

Archive/discovery flow:

```text
Raw JSONL
-> file/run/schema manifests
-> domain indexes
-> discovery layer
-> research docs / cognition
-> archive review
-> cold archive
-> restored evidence when needed
```

Rules:

- Runtime must not build manifests or indexes.
- Runtime must not compress or archive evidence.
- Agents should search indexes/manifests first when available.
- Raw JSONL remains canonical.
- Archive is not delete.
- Destructive deletion always needs separate explicit operator approval.

Canonical docs:

- [performance/evidence_manifest_index_design.md](performance/evidence_manifest_index_design.md)
- [performance/research_evidence_discovery_layer_design.md](performance/research_evidence_discovery_layer_design.md)
- [performance/runtime_evidence_archive_boundary_design.md](performance/runtime_evidence_archive_boundary_design.md)
- [INFRASTRUCTURE_GOVERNANCE_MAP.md](INFRASTRUCTURE_GOVERNANCE_MAP.md)

## 8. Current Active Blockers

| Blocker | Status | Read first | Do not infer |
|---|---|---|---|
| `RUNTIME_TRUTH_UNKNOWN` | `BLOCKED` | [executable_truth/runtime_executable_truth_source_audit.md](executable_truth/runtime_executable_truth_source_audit.md) | executable PnL |
| `MOS_UNKNOWN` | `BLOCKED` | [executable_truth/minimum_executable_reality_audit.md](executable_truth/minimum_executable_reality_audit.md) | executable minimum authority |
| `EXECUTABLE_PNL_BLOCKED` | `BLOCKED` | [executable_truth/offline_executable_truth_ledger_audit.md](executable_truth/offline_executable_truth_ledger_audit.md), [executable_truth/executable_truth_frontier_map.md](executable_truth/executable_truth_frontier_map.md) | Growth readiness |
| `empty_book ambiguity` | `REVIEW_ONLY` | [runtime_health/empty_book_reality_investigation.md](runtime_health/empty_book_reality_investigation.md) | strategy/risk change |
| `delta_extreme near-universal in key no-trade run` | `REVIEW_ONLY` | [runtime_health/delta_extreme_gate_audit.md](runtime_health/delta_extreme_gate_audit.md) | gate tuning |
| `fill/cancel/partial-fill truth missing` | `BLOCKED` | [executable_truth/executable_truth_frontier_map.md](executable_truth/executable_truth_frontier_map.md) | executable evidence |

## 9. Current Designed-Only Systems

Designed-only means a spec exists. It does not mean runtime support exists.

| System | Status | Doc |
|---|---|---|
| Infrastructure governance map | `DESIGN / GOVERNANCE` | [INFRASTRUCTURE_GOVERNANCE_MAP.md](INFRASTRUCTURE_GOVERNANCE_MAP.md) |
| Evidence manifest/index layer | `DESIGN_ONLY` | [performance/evidence_manifest_index_design.md](performance/evidence_manifest_index_design.md) |
| Research discovery layer | `DESIGN_ONLY` | [performance/research_evidence_discovery_layer_design.md](performance/research_evidence_discovery_layer_design.md) |
| Runtime evidence archive boundary | `DESIGN_ONLY` | [performance/runtime_evidence_archive_boundary_design.md](performance/runtime_evidence_archive_boundary_design.md) |
| Observability probe governance | `DESIGN / GOVERNANCE` | [runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md](runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md) |
| Observability probe registry | `DESIGN_ONLY` | [runtime_health/OBSERVABILITY_PROBE_REGISTRY_DESIGN.md](runtime_health/OBSERVABILITY_PROBE_REGISTRY_DESIGN.md) |
| Orderbook lineage probe | `DESIGNED` | [runtime_health/orderbook_lineage_probe_v1_design.md](runtime_health/orderbook_lineage_probe_v1_design.md) |
| Research Cockpit v2 | `BLUEPRINT / ROADMAP` | [performance/research_cockpit_v2_architecture.md](performance/research_cockpit_v2_architecture.md), [performance/research_cockpit_v2_roadmap.md](performance/research_cockpit_v2_roadmap.md) |

## 10. Current Implemented Systems

Implemented or previously validated systems, as represented by current docs and project instructions:

| System | Status | Notes |
|---|---|---|
| Paper runtime mode | `IMPLEMENTED` | Paper is default; live remains not ready. |
| QuantEventLogger JSONL evidence | `IMPLEMENTED` | Runtime emits structured JSONL under `runtime/quant_data`. |
| Trade journal / decision / execution / health logs | `IMPLEMENTED` | Raw evidence sources exist. |
| Path Truth checkpoint layer | `IMPLEMENTED` | Active path-truth evidence exists. |
| Path Truth replay-key direct join for post-wiring rows | `VALIDATED` | `PATH_JOIN_0_77` resolved for post-wiring rows. |
| Header research strip | `IMPLEMENTED_UI_OBSERVABILITY` | UI-only; no policy authority. |
| Telegram telemetry/route evidence | `IMPLEMENTED_OBSERVABILITY` | Use only with cooldown/aggregation governance. |
| Offline audits and research docs | `ACTIVE` | Evidence interpretation only. |

Do not treat implemented observability as implemented policy.

## 11. Current Offline-Only Systems

Offline-only means no runtime policy authority.

| System | Status | Notes |
|---|---|---|
| Session-edge audits | `RESEARCH_ONLY` | No session filter approved. |
| Executable truth ledger audit | `AUDIT / SPEC_ONLY` | No executable PnL approval. |
| Executable truth frontier map | `ROADMAP` | Blocks remain active. |
| Runtime cleanup/action plans | `DOCS_ONLY` | No file moves/deletes unless separately scoped. |
| Performance stack roadmap | `DOCS_ONLY` | No library installs. |
| Manifest/index/archive/discovery designs | `DOCS_ONLY` | No indexing/archive execution. |
| Probe registry design | `DOCS_ONLY` | No registry implementation. |

## 12. Current Forbidden Areas

Forbidden without explicit future scope:

- strategy threshold changes,
- risk sizing changes,
- order placement changes,
- cancel/fill/reconciliation changes,
- wallet, allowance, signing, or live config changes,
- live enablement,
- replay execution when task says read-only,
- threshold tuning from observability docs,
- deleting or rewriting runtime evidence,
- raw JSONL historical rewrite,
- treating probe fields as policy inputs,
- claiming executable PnL from paper/signal/path truth.

Hard warning:

```text
No docs-only task authorizes runtime behavior change.
```

## 13. Current Future Roadmap Layers

Roadmap sequence:

1. Keep paper evidence farming clean.
2. Preserve Path Truth direct join quality.
3. Resolve runtime truth and `empty_book` lineage ambiguity.
4. Design and review observability probes before implementation.
5. Build manifest/index layer offline.
6. Build discovery layer for agents/operators.
7. Establish archive custody without deleting source truth.
8. Continue executable truth blocker observatory.
9. Add fill/cancel/partial-fill truth before executable PnL.
10. Review Growth readiness only after executable truth exists.

Near-term designed-only candidates:

- `ORDERBOOK_LINEAGE_PROBE_V1`
- future `EXECUTION_LINEAGE_PROBE_V1`
- future `QUOTE_LINEAGE_PROBE_V1`
- future `LIQUIDITY_LINEAGE_PROBE_V1`
- future `REPLAY_LINEAGE_PROBE_V1`
- future `LATENCY_LINEAGE_PROBE_V1`

## 14. Dangerous Misconception Warnings

Do not conclude:

- "Path join is fixed, therefore executable truth is fixed."
- "Signal PnL is positive, therefore executable PnL exists."
- "Paper fills are live fills."
- "A designed probe is implemented."
- "A validated probe has policy authority."
- "A dashboard panel means runtime logic changed."
- "A governance doc is permission to implement."
- "Archive means delete."
- "Cognition notes are raw evidence."
- "High evidence volume means readiness."
- "`empty_book` always means true empty current market."
- "`delta_extreme` is wrong because it blocked many candidates."

Safer framing:

```text
What is the source?
What is the truth level?
What is the lineage confidence?
What is the authority level?
What remains blocked?
```

## 15. New Agent Onboarding Flow

Use this flow:

1. Read this hub.
2. Read [INDEX.md](INDEX.md).
3. Read `runtime/research_state/latest_research_state.md`.
4. Read `MASTER_AGENT_ROUTER.md`.
5. Select exactly one primary role.
6. Read only selected role docs.
7. Identify whether the task is docs-only, read-only audit, implementation, validation, or runtime operation.
8. Confirm forbidden areas.
9. Read the relevant domain folder:
   - `runtime_health/`
   - `path_truth/`
   - `executable_truth/`
   - `session_edge/`
   - `performance/`
10. Use manifests/indexes when available.
11. Only inspect raw JSONL when specifically needed.
12. Report runtime/live/strategy/risk/execution change status explicitly.

## 16. Where Operators Start

For daily status:

1. [INDEX.md](INDEX.md)
2. [path_truth/path_truth_multiday_coverage_monitor.md](path_truth/path_truth_multiday_coverage_monitor.md)
3. latest `runtime_health/new_day_*` or `runtime_health/morning_*` audit
4. [runtime_health/signal_rejection_root_cause_audit.md](runtime_health/signal_rejection_root_cause_audit.md) if no-trade/rejection dominates
5. [executable_truth/executable_truth_frontier_map.md](executable_truth/executable_truth_frontier_map.md) before any executable claims

For probe work:

1. [runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md](runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md)
2. [runtime_health/OBSERVABILITY_PROBE_REGISTRY_DESIGN.md](runtime_health/OBSERVABILITY_PROBE_REGISTRY_DESIGN.md)
3. specific probe design doc
4. future scoped implementation task only after review

For cleanup/archive:

1. [repository_cleanup_action_plan.md](repository_cleanup_action_plan.md)
2. [performance/runtime_evidence_archive_boundary_design.md](performance/runtime_evidence_archive_boundary_design.md)
3. manifest/index docs
4. explicit operator approval before moves/deletes/compression

## 17. How To Avoid False Readiness

Before saying "ready", verify:

| Claim | Required proof |
|---|---|
| Signal ready | Signal evidence, model visibility, decision lineage. |
| Path ready | Direct joins and checkpoint coverage. |
| Executable ready | MOS, fill, cancel, partial-fill, liquidity, non-dust evidence. |
| Growth ready | Executable truth plus risk/drawdown review. |
| Live ready | Live order placement, fill, cancel, reconcile, wallet/config safety. |

If any required proof is absent, use:

```text
BLOCKED
PARTIAL
REVIEW_ONLY
DESIGNED_ONLY
NOT_READY
```

## 18. How To Avoid Policy Creep

Policy creep happens when evidence starts steering runtime without a scoped implementation task.

Prevention rules:

- Keep docs and runtime separate.
- Keep probes evidence-only by default.
- Require authority labels.
- Require explicit implementation scope.
- Require targeted tests.
- Require paper validation for runtime-emitted probes.
- Require separate promotion decisions.
- Never change strategy/risk/execution from an audit-only task.

## 19. Runtime Truth vs Research Interpretation

Runtime truth:

- emitted by runtime,
- source/date/run scoped,
- append-only,
- parseable,
- traceable to JSONL/log rows.

Research interpretation:

- human/agent analysis,
- may be partial or contradictory,
- may use proxy joins,
- must preserve caveats,
- has no runtime authority.

Use this distinction:

```text
Runtime says what happened.
Research says what it might mean.
Governance says what may happen next.
```

## 20. Quick Links

Governance:

- [INDEX.md](INDEX.md)
- [INFRASTRUCTURE_GOVERNANCE_MAP.md](INFRASTRUCTURE_GOVERNANCE_MAP.md)
- [runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md](runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md)
- [runtime_health/OBSERVABILITY_PROBE_REGISTRY_DESIGN.md](runtime_health/OBSERVABILITY_PROBE_REGISTRY_DESIGN.md)

Runtime health investigations:

- [runtime_health/no_trade_open_runtime_audit.md](runtime_health/no_trade_open_runtime_audit.md)
- [runtime_health/signal_rejection_root_cause_audit.md](runtime_health/signal_rejection_root_cause_audit.md)
- [runtime_health/delta_extreme_gate_audit.md](runtime_health/delta_extreme_gate_audit.md)
- [runtime_health/empty_book_reality_investigation.md](runtime_health/empty_book_reality_investigation.md)

Probe docs:

- [runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md](runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md)
- [runtime_health/OBSERVABILITY_PROBE_REGISTRY_DESIGN.md](runtime_health/OBSERVABILITY_PROBE_REGISTRY_DESIGN.md)
- [runtime_health/orderbook_lineage_probe_v1_design.md](runtime_health/orderbook_lineage_probe_v1_design.md)

Infrastructure:

- [performance/quant_performance_stack_roadmap.md](performance/quant_performance_stack_roadmap.md)
- [performance/evidence_manifest_index_design.md](performance/evidence_manifest_index_design.md)
- [performance/research_evidence_discovery_layer_design.md](performance/research_evidence_discovery_layer_design.md)
- [performance/runtime_evidence_archive_boundary_design.md](performance/runtime_evidence_archive_boundary_design.md)

Domain truth:

- [path_truth/path_truth_multiday_coverage_monitor.md](path_truth/path_truth_multiday_coverage_monitor.md)
- [path_truth/path_join_root_cause_map.md](path_truth/path_join_root_cause_map.md)
- [executable_truth/runtime_executable_truth_source_audit.md](executable_truth/runtime_executable_truth_source_audit.md)
- [executable_truth/offline_executable_truth_ledger_audit.md](executable_truth/offline_executable_truth_ledger_audit.md)
- [executable_truth/executable_truth_frontier_map.md](executable_truth/executable_truth_frontier_map.md)
- [session_edge/session_edge_missing_split_refresh.md](session_edge/session_edge_missing_split_refresh.md)

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Replay execution: No

Threshold tuning: No

Library installs: No

Tests run: none; docs-only navigation hub.
