# Observability Probe Governance Specification

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Mode: docs-only governance specification. No implementation, runtime mutation, replay execution, strategy change, risk change, execution change, threshold tuning, live change, or library install.

## Executive Rule

Observability probes may witness runtime truth. They do not get a vote.

```text
Runtime emits compact source evidence.
Probes explain evidence lineage.
Offline systems analyze probe evidence.
Governance controls promotion.
Trading logic ignores probe fields unless a separate scoped policy phase explicitly promotes and tests them.
```

This specification governs all future probe designs, including:

- orderbook lineage,
- execution lineage,
- quote lineage,
- liquidity lineage,
- replay lineage,
- latency lineage,
- path/candidate lineage,
- blocker taxonomy lineage.

## Role Routing

Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`

Supporting roles:

- `01_PROJECT_MANAGER_AGENT.md`
- `07_TEST_CI_AGENT.md`

Why selected: this is an observability governance artifact with phase/promotion boundaries and future validation requirements.

Files inspected:

- `runtime/research_state/latest_research_state.md`
- `MASTER_AGENT_ROUTER.md`
- `docs/quant_agent_setup_md/roles/11_OBSERVABILITY_INCIDENT_AGENT.md`
- `docs/quant_agent_setup_md/roles/01_PROJECT_MANAGER_AGENT.md`
- `docs/quant_agent_setup_md/roles/07_TEST_CI_AGENT.md`
- `docs/research/runtime_health/orderbook_lineage_probe_v1_design.md`
- `docs/research/runtime_health/empty_book_reality_investigation.md`
- `docs/research/INFRASTRUCTURE_GOVERNANCE_MAP.md`
- `docs/research/performance/evidence_manifest_index_design.md`
- `docs/research/performance/runtime_evidence_archive_boundary_design.md`

Files intentionally ignored: strategy modules, risk policy modules, order placement code, wallet/live config, replay runners, and raw runtime scans.

## 1. What Qualifies As A Safe Probe

A safe probe is an additive, fail-soft, compact evidence emitter that clarifies runtime state without changing runtime behavior.

Required properties:

| Property | Requirement |
|---|---|
| Additive | Adds fields or events without removing or rewriting existing payloads. |
| Passive | Does not branch trading, risk, execution, retry, sizing, or threshold logic. |
| Compact | Emits bounded scalar fields, small enums, IDs, timestamps, counts, and top-level summaries. |
| Fail-soft | Missing fields become null/unknown; probe failure does not break runtime. |
| Source-labeled | Every derived or proxy value carries source/provenance labels. |
| Authority-labeled | Probe payload says whether it has runtime, policy, execution, or risk authority. |
| Backward compatible | Old rows remain valid; historical JSONL is not rewritten. |
| Reviewable | Has a schema, purpose, non-goals, tests, and retention plan before implementation. |

Safe probe definition:

```text
SAFE_PROBE = additive + passive + compact + fail_soft + source_labeled + no_policy_authority
```

## 2. Runtime-Safe Observability Boundaries

Allowed in runtime:

- Emit one compact event per scoped runtime moment.
- Add compact lineage fields to existing events.
- Use existing runtime timestamps and IDs.
- Emit nulls and `unknown` when data is unavailable.
- Truncate error messages.
- Use bounded enums instead of free-form classifications.
- Emit event-level authority labels.

Not allowed in runtime:

- Historical scans.
- Cross-run joins.
- Manifest generation.
- Parquet, DuckDB, Polars, PyArrow, compression, or archive work.
- Full raw orderbook dumps.
- Replay-derived enrichment.
- Telegram messages from high-frequency probe rows.
- Policy decisions based on probe fields.

Runtime-safe probe shape:

```text
one source moment
one event
bounded fields
no heavy join
no behavior mutation
```

## 3. Allowed Probe Categories

| Category | Runtime safe? | Purpose | Example |
|---|---|---|---|
| Runtime-safe lineage probe | Yes, if compact | Explain current runtime state lineage. | `ORDERBOOK_LINEAGE_PROBE_V1`. |
| Runtime-safe health probe | Yes, if low frequency | Detect write, exception, route, process, or telemetry health. | Telegram route telemetry. |
| Runtime-safe timestamp probe | Yes, if additive | Preserve event timestamps for later latency metrics. | `order_submit_ts`, `decision_complete_ts`. |
| Replay-only probe | No runtime emission | Explain replay assumptions or joins. | Replay continuity probe. |
| Offline-only probe | No runtime emission | Scan completed evidence and summarize distributions. | Quote-age distribution audit. |
| Governance-sensitive probe | Requires review | Could later affect policy, operator confidence, or readiness gates. | Executable truth blocker probe. |
| Forbidden probe | Never allowed | Mutates trading, risk, execution, live, wallet, or thresholds under observability cover. | Probe that disables a gate. |

## 4. Forbidden Probe Behavior

Forbidden behavior includes:

- Changing strategy decisions.
- Changing risk sizing, risk mode, bankroll tier, exposure caps, or LOCKDOWN behavior.
- Changing order placement, cancel, fill, retry, or reconciliation behavior.
- Changing live config, wallet, allowance, or signing behavior.
- Changing scanner timing, orderbook retry behavior, or cutoff thresholds.
- Branching runtime logic on a probe field.
- Treating paper simulated values as live observed values.
- Emitting raw credentials, private keys, auth headers, wallet secrets, or full signed payloads.
- Emitting unbounded arrays or full raw exchange responses in hot loops.
- Writing probe output into runtime config or policy files.
- Rewriting historical JSONL.
- Promoting S3, Growth Mode, executable PnL, or live readiness.

Bright-line rule:

```text
If a probe changes what the bot would do, it is no longer a probe.
```

## 5. Probe Authority Levels

Every probe schema must declare authority.

| Authority level | Meaning | Runtime consumers allowed? |
|---|---|---|
| `evidence_only` | Raw or near-raw event evidence. | No policy consumers. |
| `diagnostic_only` | Derived label for human/offline diagnosis. | No policy consumers. |
| `offline_research_only` | Computed outside runtime from raw/probe evidence. | No runtime consumers. |
| `operator_review_required` | May influence future work only after review. | No automatic consumers. |
| `policy_candidate` | Proposed future runtime input, not active. | No, until separately implemented/tested. |
| `runtime_policy` | Approved runtime input. | Only after explicit implementation scope and tests. |
| `forbidden` | Must not exist or be consumed. | Never. |

Default authority:

```text
probe_authority_level: evidence_only
policy_authority: none
runtime_decision_authority: false
execution_authority: false
risk_authority: false
```

Any deviation requires operator review.

## 6. Policy-Consumer Restrictions

Probe fields must not be consumed by:

- strategy approval,
- EV threshold logic,
- risk sizing,
- stop loss,
- order placement,
- cancel behavior,
- reconciliation,
- live gating,
- mode switching,
- bankroll tier promotion,
- S3/Growth readiness.

Allowed consumers:

- offline audits,
- data quality checks,
- runtime health reports,
- operator dashboards,
- research docs,
- Hermes cognition,
- future manifests/indexes,
- future Telegram digests after aggregation and cooldown.

Policy promotion rule:

```text
Probe -> offline audit -> review doc -> implementation plan -> tests -> paper validation -> separate promotion decision
```

No direct `Probe -> Runtime Policy` path exists.

## 7. Runtime Performance Constraints

Runtime-safe probes must obey these constraints:

| Constraint | Requirement |
|---|---|
| CPU | Constant-time per event; no historical aggregation. |
| IO | Append-only JSONL through existing logger path or equivalent scoped event writer. |
| Memory | Bounded, current-window-only state. |
| Payload size | Compact scalar/enums only; no raw arrays. |
| Frequency | Bounded by source event frequency or sampled. |
| Error handling | Probe failure swallowed/logged at debug/system-health level, not raised into trading path. |
| Dependencies | No new runtime library without explicit review. |
| Backpressure | Probe logging must not stall decision/execution loops. |

Danger signs:

- probe requires scanning prior rows;
- probe builds rolling cross-run stats in runtime;
- probe adds network calls;
- probe logs full raw exchange payloads;
- probe emits repeated Telegram alerts;
- probe failure can abort a decision cycle.

## 8. JSONL Payload Constraints

Required JSONL contract:

- JSON object per line.
- Stable `event_type`.
- Stable `schema_version`.
- UTC timestamps.
- `run_id` when available.
- Source/provenance fields for proxy or derived values.
- Authority fields.
- Null/unknown for missing values.
- Bounded enum values for classifications.
- Truncated sanitized errors.
- Backward compatible additive fields only.

Recommended common envelope:

| Field | Required | Notes |
|---|---|---|
| `event_type` | yes | Stable probe event name. |
| `schema_version` | yes | Probe-specific version. |
| `event_ts` | yes | UTC emission timestamp. |
| `run_id` | yes, if available | Do not fabricate. |
| `mode` | yes | `paper`, `live`, `verify`, or `unknown`. |
| `producer` | yes | Runtime component emitting probe. |
| `probe_name` | yes | Human-readable probe name. |
| `probe_authority_level` | yes | Default `evidence_only`. |
| `policy_authority` | yes | Default `none`. |
| `runtime_decision_authority` | yes | Default false. |
| `execution_authority` | yes | Default false. |
| `risk_authority` | yes | Default false. |
| `timestamp_source` | yes | Runtime clock, exchange raw timestamp, proxy, unknown. |
| `truth_level` | yes | `live_observed`, `paper_simulated`, `proxy`, `unknown`. |
| `lineage_id` | recommended | Probe-specific lineage id when possible. |
| `missing_fields` | optional | Compact list of important missing fields. |
| `caveats` | optional | Compact list, not prose paragraphs. |

Forbidden payload content:

- private keys,
- API secrets,
- auth headers,
- wallet signing payloads,
- full raw books,
- full stack traces per cycle,
- unbounded metadata,
- raw HTML/API bodies,
- personally identifying local paths beyond repo-relative paths unless required for evidence.

## 9. Fail-Soft Requirements

All probes must fail soft.

Required behavior:

- Missing source data -> null or `unknown`.
- Parse/serialization issue -> compact probe error, no runtime exception propagation.
- Unknown truth source -> `truth_level=unknown`, not `live_observed`.
- Paper simulated truth -> `truth_level=paper_simulated`.
- Derived approximation -> `truth_level=proxy`.
- Live exchange observation -> `truth_level=live_observed` only when genuinely observed.
- Probe writer failure -> runtime continues.
- Probe schema change -> additive version bump.

Fail-soft anti-patterns:

- defaulting missing data to positive readiness,
- defaulting unknown live truth to live observed,
- replacing missing fields with zero when zero has trading meaning,
- hiding missing fields from downstream audits,
- swallowing all unknown runtime exceptions globally under a probe label.

## 10. Probe Lineage Standards

Every probe must define its lineage spine.

Recommended identity hierarchy:

1. `(run_id, paper_trade_replay_key)` for trade/path/outcome lineage.
2. `(run_id, decision_id)` for decision lineage.
3. `(run_id, candidate_id)` for candidate lineage.
4. `(run_id, event_type, lineage_id)` for probe event lineage.
5. `(run_id, token_pair_key, event_ts bucket)` only as proxy.

Minimum lineage fields:

- `run_id`,
- `event_ts`,
- `producer`,
- `schema_version`,
- probe-specific `lineage_id`,
- source identity fields when already available,
- `lineage_confidence`: `DIRECT`, `STRONG`, `WEAK`, `PROXY`, `BLOCKED`, or `UNKNOWN`.

Lineage rules:

- Never join by raw `candidate_id` alone.
- Never fabricate `paper_trade_replay_key`.
- Distinguish direct keys from proxy keys.
- Preserve source path/date/run in offline manifests.
- Include `lineage_drop_reason` when a join cannot be direct.
- Keep old/null rows valid as legacy truth.

## 11. Probe Retention And Archive Standards

Probe data is raw evidence if emitted by runtime.

Retention class:

| Probe type | Hot retention | Warm retention | Cold/archive rule |
|---|---|---|---|
| Runtime-safe lineage probe | Current date + latest completed date | Open blocker/gate dates | Archive after manifest and operator review. |
| Runtime health probe | Current active incident + latest completed date | Incident review period | Archive after incident summary. |
| Replay-only probe | Not hot runtime evidence | Active replay research | Archive with replay report lineage. |
| Offline-only probe | Not runtime evidence | Active research period | Archive with docs/research lineage. |
| Governance-sensitive probe | Active until review resolved | Warm while blocker open | Archive only after governance summary. |

Archive requirements:

- raw JSONL remains canonical;
- no rewrite before archive;
- manifest must preserve path, hash, line count, parse errors, run IDs, event types, field coverage, and research refs;
- compressed evidence must be restorable;
- destructive deletion always requires separate explicit operator approval.

## 12. Probe Review And Promotion Process

Every future probe should pass this process:

1. Design doc:
   - purpose,
   - scope,
   - non-goals,
   - event schema,
   - authority level,
   - runtime performance risk,
   - fail-soft behavior,
   - retention plan,
   - tests.

2. Operator review:
   - required for runtime-emitted probes,
   - required for governance-sensitive probes,
   - required for any probe touching live-observed labels,
   - required for any new runtime dependency.

3. Implementation scope:
   - observability-only,
   - additive,
   - no policy consumers,
   - no strategy/risk/execution changes.

4. Tests:
   - payload shape,
   - missing field fail-soft,
   - authority labels,
   - no raw payload leakage,
   - backward compatibility,
   - source/provenance labels.

5. Paper validation:
   - short paper validation only if runtime probe implemented,
   - verify event emission,
   - verify no runtime exceptions,
   - verify no behavior change.

6. Offline consumption:
   - only after event coverage exists,
   - report missing fields and lineage confidence,
   - no executable/live claims from probe alone.

7. Promotion:
   - probe remains evidence-only unless a separate future task promotes a derived field.

Promotion gates:

```text
DESIGNED -> REVIEWED -> IMPLEMENTED_AS_OBSERVABILITY -> PAPER_VALIDATED -> OFFLINE_ANALYZED -> POLICY_CANDIDATE
```

There is no automatic promotion from `POLICY_CANDIDATE` to `runtime_policy`.

## 13. Probe Classification

### Runtime-Safe Probes

Runtime-safe probes are compact, source-local, additive, and fail-soft.

Examples:

- current orderbook lineage event,
- execution timestamp emission,
- compact quote-age source label,
- write/Telegram health event,
- path-truth checkpoint identity field.

Rules:

- allowed only if no policy consumers exist;
- must have tests before implementation;
- must be disabled by failure, not by blocking runtime.

### Replay-Only Probes

Replay-only probes run outside runtime and inspect replay assumptions.

Examples:

- replay continuity probe,
- ghost-fill replay detector,
- replay open/close match probe.

Rules:

- must not write runtime JSONL;
- must not run automatically in runtime;
- must label replay assumptions.

### Offline-Only Probes

Offline-only probes scan completed evidence.

Examples:

- quote-age distribution audit,
- session-edge control audit,
- executable truth ledger audit,
- blocker distribution audit.

Rules:

- no runtime mutation;
- no active file rewrite;
- start from manifests/indexes where available;
- no strategy/risk/execution authority.

### Governance-Sensitive Probes

Governance-sensitive probes can influence readiness perception and therefore require extra caution.

Examples:

- executable PnL blocker probe,
- live-observed fill truth probe,
- cancel/partial fill truth probe,
- Growth readiness gate probe.

Rules:

- operator review required;
- authority labels required;
- raw evidence and derived interpretations must be separated;
- no readiness promotion from probe evidence alone.

### Forbidden Probes

Forbidden probes mutate behavior, hide risk, or fabricate authority.

Examples:

- probe that bypasses `delta_extreme`,
- probe that changes cutoff behavior,
- probe that retries orderbook fetch differently under observability scope,
- probe that sizes orders from offline evidence,
- probe that treats paper fills as live fills,
- probe that claims executable PnL without fill/cancel/partial-fill truth.

## 14. When A Probe Becomes Dangerous

A probe becomes dangerous when any of these are true:

- It changes runtime branching.
- It adds network calls in the decision path.
- It emits unbounded data.
- It can block decision/execution loops.
- It hides missing fields.
- It labels proxy as live observed.
- It drives a dashboard or Telegram alert that pressures operators into premature promotion.
- It becomes a policy input without a separate implementation phase.
- It changes fetch/retry/order/cancel/risk behavior under an observability label.
- It increases evidence volume enough to threaten runtime health.

Danger classification:

```text
SAFE: passive, compact, no consumers
REVIEW_REQUIRED: high volume, live-observed, readiness-impacting, or governance-sensitive
DANGEROUS: runtime branching, policy input, mutable behavior, or unbounded emission
FORBIDDEN: wallet/live/risk/execution mutation under probe scope
```

## 15. When Operator Review Is Required

Operator review is required for:

- any runtime-emitted new probe,
- any new JSONL source folder,
- any probe in live mode,
- any probe that emits live-observed truth labels,
- any governance-sensitive probe,
- any probe that may increase evidence volume materially,
- any probe with Telegram/dashboard surfacing,
- any probe requiring new dependencies,
- any probe considered for policy-candidate status,
- any archive/compression/deletion action affecting probe output.

Operator review is not required for:

- docs-only probe design,
- read-only offline audit using existing evidence,
- typo fixes in probe docs,
- non-runtime cognition notes that do not claim new truth.

## 16. Cognition Interaction

Hermes/cognition may ingest probes as:

- `SIGNAL_EVIDENCE`,
- `PATH_EVIDENCE`,
- `BLOCKER_EVIDENCE`,
- `UNLOCK_PROGRESS`,
- `OBSERVABILITY_COVERAGE`,
- `GOVERNANCE_CAVEAT`.

Hermes/cognition must not ingest probes as:

- executable PnL,
- live profitability,
- Growth readiness,
- risk approval,
- strategy approval,
- live readiness.

Cognition rules:

- Always preserve truth level: paper, live, proxy, unknown.
- Preserve lineage confidence.
- Separate blocker evidence from unlock evidence.
- Link probe-derived claims to raw source path/run/date.
- Surface contradictions as review items, not conclusions.
- Never let cognition notes mutate runtime state.

## 17. Safe Future Agent Consumption

Future agents should consume probes in this order:

1. Read `docs/research/INDEX.md` and relevant governance specs.
2. Identify the probe schema and authority level.
3. Check whether probe output is runtime, replay-only, or offline-only.
4. Use manifests/indexes where available before scanning raw JSONL.
5. Join only with approved lineage keys.
6. Separate raw fields from derived fields.
7. Separate terminal blockers from contextual blockers.
8. Preserve null/unknown as uncertainty.
9. Report missing fields and lineage confidence.
10. Never recommend strategy/risk/execution/live changes from probe evidence alone.

Agent anti-patterns:

- treating high counts as readiness,
- collapsing proxy and direct joins,
- ignoring authority labels,
- scanning all evidence when a manifest exists,
- calling a docs-only probe "implemented",
- promoting S3/Growth from observability coverage.

## 18. Standard Probe Design Template

Every future probe design should include:

```text
1. Purpose
2. Non-goals
3. Runtime safety boundary
4. Probe category
5. Authority level
6. JSONL event schema
7. Required fields
8. Optional fields
9. Source/provenance labels
10. Lineage keys
11. Fail-soft rules
12. Performance constraints
13. Retention/archive rules
14. Offline consumption rules
15. Tests required before implementation
16. What not to do
```

## 19. Future Options

OPTION 1 - SAFE EV PRESERVATION:

Keep this spec as a review gate only. Require future probes to cite it before implementation. Lowest risk, slower standardization.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:

Use this spec to greenlight narrowly scoped runtime-safe probes like `ORDERBOOK_LINEAGE_PROBE_V1`, with targeted tests and short paper validation. Higher information gain, still no policy consumers.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:

Build a formal probe registry, schema manifest, and probe coverage dashboard later. Strong governance, but should remain offline/index-layer work and not enter the runtime loop.

Recommended path: OPTION 1 now, OPTION 2 only for explicitly scoped future probe implementations, and OPTION 3 after manifest/index infrastructure exists.

## 20. What Not To Do

Do not:

- implement probes in this task,
- run paper,
- run replay,
- modify runtime code,
- change strategy/risk/execution/live behavior,
- tune thresholds,
- install libraries,
- promote S3 or Growth Mode,
- treat this governance spec as permission to implement any probe.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Threshold tuning: No

Replay execution: No

Library installs: No

Tests run: none; docs-only governance specification.
