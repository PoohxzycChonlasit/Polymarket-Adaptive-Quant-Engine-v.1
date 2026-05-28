# Observability Probe Registry Design

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Mode: docs-only registry design. No implementation, runtime mutation, replay execution, strategy change, risk change, execution change, threshold tuning, live change, or library install.

## Executive Verdict

The project should maintain a centralized observability probe registry as a governance and discovery layer, not as a runtime dependency.

```text
Probe designs live in docs.
Runtime emits only approved compact evidence.
Registry tracks probe status, authority, schema, deployment, lineage, and review state.
Manifests and discovery layers reference registry metadata later.
Trading logic must not read the registry.
```

The registry should begin as a docs-only source of truth. Future manifest/index infrastructure may materialize it into JSON, CSV, DuckDB, or dashboard form, but that is explicitly out of scope here.

## Source Inputs

This design is anchored to:

- `docs/research/runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md`
- `docs/research/runtime_health/orderbook_lineage_probe_v1_design.md`
- `docs/research/runtime_health/empty_book_reality_investigation.md`
- `docs/research/INFRASTRUCTURE_GOVERNANCE_MAP.md`
- `docs/research/performance/evidence_manifest_index_design.md`
- `docs/research/performance/runtime_evidence_archive_boundary_design.md`

It does not authorize implementation of any probe.

## 1. Probe Registry Purpose

The registry answers:

1. What probes exist or are proposed?
2. Which probes are implemented?
3. Which probes are runtime-safe?
4. Which probes are offline-only or replay-only?
5. Which probes are governance-sensitive or dangerous?
6. Which schemas and evidence sources do they produce?
7. Which probes have policy authority, if any?
8. Which probes can future agents safely consume?
9. Which probes are deprecated or archived?

The registry prevents three common failure modes:

- treating a design doc as implemented runtime evidence;
- treating evidence-only fields as policy authority;
- losing probe lineage when evidence moves to manifests or archive.

## 2. Registry Structure

Recommended initial structure:

```text
docs/research/runtime_health/OBSERVABILITY_PROBE_REGISTRY.md
docs/research/runtime_health/OBSERVABILITY_PROBE_REGISTRY_DESIGN.md
docs/research/runtime_health/probes/
  ORDERBOOK_LINEAGE_PROBE_V1.md
  EXECUTION_LINEAGE_PROBE_V1.md
  QUOTE_LINEAGE_PROBE_V1.md
  LIQUIDITY_LINEAGE_PROBE_V1.md
  REPLAY_LINEAGE_PROBE_V1.md
  LATENCY_LINEAGE_PROBE_V1.md
```

Design-only note:

- This task creates only the registry design.
- The actual registry file and probe cards should be created only when explicitly scoped.

Future machine-readable mirror, optional:

```text
runtime/reports/probe_registry_manifest.json
```

That mirror would be generated offline from docs and manifests. It must not be hand-edited runtime state and must not be consumed by trading logic.

## 3. Probe Metadata Schema

Each registry row or probe card should contain:

| Field | Required | Meaning |
|---|---|---|
| `probe_id` | yes | Stable uppercase identifier. |
| `probe_name` | yes | Human-readable name. |
| `schema_version` | yes | Probe payload schema version. |
| `design_doc` | yes | Path to design/spec doc. |
| `registry_card` | optional | Path to dedicated probe card. |
| `category` | yes | Runtime-safe, replay-only, offline-only, governance-sensitive, forbidden. |
| `lifecycle_state` | yes | Current lifecycle state. |
| `review_state` | yes | Governance review status. |
| `implementation_state` | yes | Whether code exists and where. |
| `runtime_deployment_state` | yes | Whether emitted by runtime and in which mode. |
| `policy_consumer_state` | yes | Whether any runtime policy consumes the probe. |
| `authority_level` | yes | Evidence-only, diagnostic-only, policy-candidate, etc. |
| `truth_level_supported` | yes | Paper simulated, live observed, proxy, unknown. |
| `jsonl_destination` | optional | Expected output path if runtime-emitted. |
| `event_type` | optional | Probe event type. |
| `producer` | optional | Runtime/offline producer. |
| `required_fields` | yes | Required payload fields or ref. |
| `optional_fields` | optional | Optional payload fields or ref. |
| `lineage_keys` | yes | Supported join keys. |
| `lineage_confidence_support` | yes | DIRECT/STRONG/WEAK/PROXY/BLOCKED support. |
| `dependencies` | optional | Probe or source dependencies. |
| `downstream_consumers` | optional | Approved non-policy consumers. |
| `evidence_coverage_state` | yes | No evidence, partial, validated, stale, archived. |
| `archive_class` | optional | Hot/warm/cold/archived or not applicable. |
| `deprecation_state` | optional | Active, superseded, deprecated, archived. |
| `operator_notes` | optional | Short governance notes. |

## 4. Probe ID Rules

Probe IDs must be stable, uppercase, and versioned.

Format:

```text
<DOMAIN>_<PURPOSE>_PROBE_V<N>
```

Examples:

- `ORDERBOOK_LINEAGE_PROBE_V1`
- `EXECUTION_LINEAGE_PROBE_V1`
- `QUOTE_LINEAGE_PROBE_V1`
- `LIQUIDITY_LINEAGE_PROBE_V1`
- `REPLAY_LINEAGE_PROBE_V1`
- `LATENCY_LINEAGE_PROBE_V1`

Rules:

- Never reuse a probe ID for incompatible schemas.
- Increment version for schema-breaking changes.
- Additive field changes may keep the same probe ID but must update `schema_version`.
- Deprecation does not delete the ID.
- Archived probes remain discoverable.

## 5. Schema Version Tracking

Each probe must track two versions:

| Version | Meaning |
|---|---|
| `probe_id` version | Human/governance generation, for example `V1`. |
| `schema_version` | Payload contract version, for example `orderbook_lineage_probe_v1`. |

Schema changes:

| Change type | Required action |
|---|---|
| Add optional field | Update registry `schema_notes`; keep schema version if compatible. |
| Add required field | Bump schema version. |
| Rename field | Bump schema version; mark old field deprecated. |
| Change enum meaning | Bump schema version. |
| Remove field | Bump schema version and require migration note. |
| Change authority semantics | Operator review required. |

## 6. Authority Tracking

Authority must be tracked separately from implementation state.

Allowed authority levels:

- `evidence_only`
- `diagnostic_only`
- `offline_research_only`
- `operator_review_required`
- `policy_candidate`
- `runtime_policy`
- `forbidden`

Default:

```text
authority_level: evidence_only
policy_consumer_state: none
runtime_decision_authority: false
execution_authority: false
risk_authority: false
```

Registry invariant:

```text
IMPLEMENTED_OBSERVABILITY_ONLY does not imply POLICY_CANDIDATE.
PAPER_VALIDATED does not imply runtime_policy.
OFFLINE_ANALYZED does not imply executable truth.
```

## 7. Lifecycle States

Required lifecycle states:

| State | Meaning |
|---|---|
| `DESIGNED` | Design doc exists; no implementation implied. |
| `REVIEWED` | Operator/governance review completed. |
| `IMPLEMENTED_OBSERVABILITY_ONLY` | Runtime/offline implementation exists and is evidence-only. |
| `PAPER_VALIDATED` | Runtime-emitted probe validated in paper without behavior change. |
| `OFFLINE_ANALYZED` | Probe evidence has been consumed by an offline audit. |
| `POLICY_CANDIDATE` | A derived field may be considered for future policy, but is not active policy. |
| `REJECTED` | Probe design or implementation path rejected. |
| `DEPRECATED` | Probe superseded but still discoverable. |
| `ARCHIVED` | Probe no longer active; evidence preserved by archive/manifest lineage. |

Allowed transitions:

```text
DESIGNED -> REVIEWED
REVIEWED -> IMPLEMENTED_OBSERVABILITY_ONLY
IMPLEMENTED_OBSERVABILITY_ONLY -> PAPER_VALIDATED
PAPER_VALIDATED -> OFFLINE_ANALYZED
OFFLINE_ANALYZED -> POLICY_CANDIDATE
DESIGNED -> REJECTED
REVIEWED -> REJECTED
IMPLEMENTED_OBSERVABILITY_ONLY -> DEPRECATED
PAPER_VALIDATED -> DEPRECATED
OFFLINE_ANALYZED -> DEPRECATED
DEPRECATED -> ARCHIVED
REJECTED -> ARCHIVED
```

Blocked transitions:

```text
DESIGNED -> IMPLEMENTED_OBSERVABILITY_ONLY without review
DESIGNED -> POLICY_CANDIDATE
PAPER_VALIDATED -> runtime_policy
OFFLINE_ANALYZED -> runtime_policy
POLICY_CANDIDATE -> runtime_policy without separate implementation task
```

## 8. Governance Review States

Review state is separate from lifecycle state.

| Review state | Meaning |
|---|---|
| `NOT_REVIEWED` | Design exists but no operator/governance review. |
| `REVIEW_REQUESTED` | Awaiting review. |
| `APPROVED_FOR_DESIGN_ONLY` | Approved as docs/spec. |
| `APPROVED_FOR_OBSERVABILITY_IMPLEMENTATION` | May be implemented as passive evidence only. |
| `APPROVED_FOR_PAPER_VALIDATION` | May run short paper validation after implementation. |
| `APPROVED_FOR_OFFLINE_ANALYSIS` | May be consumed by offline audits. |
| `POLICY_REVIEW_REQUIRED` | Any policy use requires fresh review. |
| `REJECTED` | Must not implement or consume. |

Review rules:

- Runtime-emitted probes require review before implementation.
- Live-observed labels require review.
- Any policy-candidate transition requires review.
- Any new JSONL source folder requires review.
- Any high-volume probe requires review.

## 9. Runtime-Safe Classification

Registry field:

```text
runtime_safe_classification
```

Allowed values:

| Value | Meaning |
|---|---|
| `RUNTIME_SAFE_COMPACT` | May be emitted in runtime if reviewed and implemented passively. |
| `RUNTIME_SAFE_SAMPLED` | May be emitted only with sampling or bounded frequency. |
| `RUNTIME_HEALTH_ONLY` | Health/incident evidence only. |
| `REVIEW_REQUIRED_HIGH_VOLUME` | Potential runtime pressure; needs review. |
| `NOT_RUNTIME_SAFE` | Must remain offline/replay/docs only. |
| `FORBIDDEN_RUNTIME` | Must never enter runtime. |

Runtime-safe does not mean implemented. It means eligible for a future scoped implementation.

## 10. Offline-Only Classification

Registry field:

```text
offline_classification
```

Allowed values:

- `RUNTIME_EMITTED_SOURCE`
- `REPLAY_ONLY`
- `OFFLINE_AUDIT_ONLY`
- `MANIFEST_ONLY`
- `DISCOVERY_ONLY`
- `COGNITION_ONLY`
- `ARCHIVE_ONLY`
- `NOT_APPLICABLE`

Offline-only probes must not write runtime JSONL and must not be used as runtime policy.

## 11. Implementation State Tracking

Registry field:

```text
implementation_state
```

Allowed values:

| Value | Meaning |
|---|---|
| `NOT_IMPLEMENTED` | Design only. |
| `PARTIAL_DOCS_ONLY` | Docs exist, no runtime/offline code. |
| `OFFLINE_IMPLEMENTED` | Offline tool/report exists. |
| `RUNTIME_IMPLEMENTED_OBSERVABILITY_ONLY` | Runtime emits evidence, no policy consumer. |
| `TESTED` | Targeted tests exist and pass in last known run. |
| `PAPER_VALIDATED` | Real paper evidence shows emission without behavior change. |
| `UNKNOWN` | State not verified. |

Implementation state must cite files/tests when not `NOT_IMPLEMENTED`.

## 12. Runtime Deployment State

Registry field:

```text
runtime_deployment_state
```

Allowed values:

- `NOT_DEPLOYED`
- `PAPER_ONLY`
- `PAPER_AND_VERIFY`
- `LIVE_OBSERVABILITY_ONLY`
- `LIVE_FORBIDDEN`
- `UNKNOWN`

Default for new probes:

```text
NOT_DEPLOYED
```

Live deployment requires explicit operator review, live truth labeling, and no policy consumers.

## 13. Policy-Consumer State

Registry field:

```text
policy_consumer_state
```

Allowed values:

| Value | Meaning |
|---|---|
| `NONE` | No runtime policy consumers. Default. |
| `FORBIDDEN` | Must never be consumed by policy. |
| `OFFLINE_ONLY` | May inform docs/audits only. |
| `POLICY_CANDIDATE_REVIEW_REQUIRED` | Candidate only, not active. |
| `ACTIVE_RUNTIME_POLICY` | Only allowed after separate explicit implementation and tests. |
| `UNKNOWN` | Must be treated as unsafe until verified. |

Any value other than `NONE`, `FORBIDDEN`, or `OFFLINE_ONLY` requires operator review.

## 14. Evidence Coverage State

Registry field:

```text
evidence_coverage_state
```

Allowed values:

- `NO_EVIDENCE`
- `SCHEMA_DESIGNED_ONLY`
- `EMISSION_UNVALIDATED`
- `PARTIAL_COVERAGE`
- `PAPER_VALIDATED_COVERAGE`
- `OFFLINE_ANALYZED_COVERAGE`
- `STALE_COVERAGE`
- `ARCHIVED_COVERAGE`
- `REGRESSED_COVERAGE`
- `UNKNOWN`

Coverage must cite:

- source path,
- date/run coverage,
- parse status,
- field coverage,
- missing fields,
- lineage confidence.

## 15. Probe Dependency Tracking

Probe dependencies should be explicit so future agents know what must exist first.

Dependency fields:

| Field | Meaning |
|---|---|
| `source_dependencies` | Required runtime/offline evidence sources. |
| `field_dependencies` | Required fields. |
| `probe_dependencies` | Other probes this probe depends on. |
| `manifest_dependencies` | Manifest/index layer requirements. |
| `governance_dependencies` | Required review or gate docs. |
| `runtime_dependencies` | Runtime modules touched if implemented. |
| `test_dependencies` | Tests required before implementation. |

Example:

```text
ORDERBOOK_LINEAGE_PROBE_V1
source_dependencies: decision_log, market_snapshots, orderbook fetch path
field_dependencies: run_id, token_pair_key, side-specific fetch status
probe_dependencies: none
manifest_dependencies: future evidence_file_manifest optional
governance_dependencies: OBSERVABILITY_PROBE_GOVERNANCE_SPEC
```

## 16. Probe Lineage Relationships

The registry should model lineage between probes.

Relationship types:

| Relationship | Meaning |
|---|---|
| `supersedes` | New probe replaces older probe. |
| `depends_on` | Probe requires another probe/source. |
| `enriches` | Probe adds context to another source. |
| `validates` | Probe validates a lineage or coverage claim. |
| `contradicts` | Probe revealed conflicting evidence. |
| `feeds_manifest` | Probe evidence is indexed by manifest layer. |
| `feeds_cognition` | Probe metadata is safe for Hermes/cognition. |
| `blocked_by` | Probe cannot advance due missing evidence/review. |

Lineage relationship rules:

- Relationships must be explicit, not inferred by filename similarity.
- Deprecated probes must point to their successor.
- Contradictions must remain visible until resolved.
- Probe relationships do not grant policy authority.

## 17. Lineage Confidence Support

Registry field:

```text
lineage_confidence_support
```

Allowed values:

- `DIRECT_SUPPORTED`
- `STRONG_SUPPORTED`
- `WEAK_SUPPORTED`
- `PROXY_ONLY`
- `BLOCKED`
- `UNKNOWN`

Registry should list supported keys:

- `(run_id, paper_trade_replay_key)`
- `(run_id, decision_id)`
- `(run_id, candidate_id)`
- `(run_id, lineage_id)`
- source-specific key, such as `(run_id, orderbook_token_pair_key, event_ts bucket)`

Rules:

- `PROXY_ONLY` cannot unlock executable truth.
- `DIRECT_SUPPORTED` must cite the direct key.
- Missing lineage fields must be recorded, not hidden.

## 18. Archive And Discovery Integration

Registry metadata must connect to future manifest/discovery/archive layers.

Manifest references:

- `probe_id`
- `schema_version`
- `event_type`
- `jsonl_destination`
- `source_type`
- `source_path`
- `evidence_date`
- `run_ids`
- `line_count`
- `parse_error_count`
- `field_presence`
- `schema_fingerprint`
- `archive_class`

Discovery references:

- active probe list,
- governance-sensitive probe list,
- implemented probe list,
- rejected/deprecated probe list,
- probe-to-domain map,
- probe-to-blocker map.

Archive references:

- original JSONL path,
- archive path,
- source hash,
- line count,
- parse status,
- restore instructions,
- registry state at archive time,
- successor probe if deprecated.

Archive rule:

```text
Archive may move evidence custody.
Archive must not erase probe identity or lineage.
```

## 19. How Future Agents Discover Probes

Future agent flow:

1. Read `docs/research/INDEX.md`.
2. Read `docs/research/runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md`.
3. Read `docs/research/runtime_health/OBSERVABILITY_PROBE_REGISTRY.md` when it exists.
4. Filter by domain and lifecycle state.
5. Check authority level and policy consumer state.
6. Open the probe design or registry card.
7. Use manifests/indexes where available to find actual evidence.
8. Report coverage and lineage confidence before making claims.

Until the real registry exists, agents should use this design plus individual probe design docs.

## 20. How Governance Tracks Dangerous Probes

The registry should make dangerous probes visible with:

- `runtime_safe_classification`,
- `authority_level`,
- `policy_consumer_state`,
- `review_state`,
- `danger_flags`,
- `operator_review_required`,
- `blocked_actions`.

Recommended danger flags:

- `HIGH_VOLUME`
- `LIVE_OBSERVED`
- `POLICY_ADJACENT`
- `READINESS_IMPACTING`
- `EXECUTABLE_TRUTH_ADJACENT`
- `REQUIRES_NEW_DEPENDENCY`
- `TOUCHES_RUNTIME_HOT_PATH`
- `TELEGRAM_SURFACING`
- `DASHBOARD_SURFACING`
- `ARCHIVE_SENSITIVE`

Any probe with danger flags should default to:

```text
review_state: POLICY_REVIEW_REQUIRED
policy_consumer_state: NONE
runtime_deployment_state: NOT_DEPLOYED
```

## 21. How Cognition Consumes Probe Metadata

Hermes/cognition may consume registry metadata as:

- `OBSERVABILITY_COVERAGE`,
- `BLOCKER_EVIDENCE`,
- `UNLOCK_PROGRESS`,
- `GOVERNANCE_CAVEAT`,
- `LINEAGE_CONFIDENCE`,
- `PROBE_STATUS`.

Hermes/cognition must not translate registry metadata into:

- executable PnL,
- live profitability,
- Growth readiness,
- risk approval,
- strategy approval,
- live readiness.

Cognition ingestion should preserve:

- `probe_id`,
- lifecycle state,
- authority level,
- truth level,
- lineage confidence,
- missing fields,
- blocker/unlock caveats,
- source docs and source evidence refs.

## 22. How Manifests Reference Probes

Future evidence manifests should include probe-aware columns when applicable:

| Manifest field | Meaning |
|---|---|
| `probe_id` | Registry probe id. |
| `probe_schema_version` | Payload schema version. |
| `probe_lifecycle_state_at_manifest` | Registry lifecycle state when manifest generated. |
| `probe_authority_level` | Authority state. |
| `probe_event_type` | JSONL event type. |
| `probe_field_coverage` | Required/optional field coverage summary. |
| `probe_lineage_confidence` | Direct/proxy/blocked summary. |
| `probe_archive_class` | Hot/warm/cold/archive state. |

Manifests may reference registry metadata. Runtime must not reference manifests during trading.

## 23. Deprecation Rules

A probe may be deprecated when:

- a newer probe supersedes it,
- schema is no longer sufficient,
- evidence volume is too high,
- authority labels are unsafe,
- implementation was rejected,
- lineage is blocked permanently,
- probe is redundant with a better source.

Deprecation requirements:

- mark `lifecycle_state=DEPRECATED`;
- preserve original design doc;
- preserve evidence location and archive refs;
- identify successor probe if any;
- document whether historical rows remain valid;
- block new implementation unless explicitly revived.

Archived does not mean deleted.

## 24. Initial Registry Seed Candidates

The first registry, when created, should seed these rows:

| Probe ID | Category | Initial lifecycle | Authority | Notes |
|---|---|---|---|---|
| `ORDERBOOK_LINEAGE_PROBE_V1` | Runtime-safe lineage probe | `DESIGNED` | `evidence_only` | Designed to resolve `empty_book` ambiguity. |
| `EXECUTION_LINEAGE_PROBE_V1` | Governance-sensitive/runtime-safe candidate | `DESIGNED` or `NOT_STARTED` | `evidence_only` | Future submit/ack/fill/cancel lineage. |
| `QUOTE_LINEAGE_PROBE_V1` | Runtime-safe lineage probe | `DESIGNED` or `NOT_STARTED` | `evidence_only` | Future quote age/source lineage. |
| `LIQUIDITY_LINEAGE_PROBE_V1` | Governance-sensitive probe | `DESIGNED` or `NOT_STARTED` | `evidence_only` | Future spread/depth/liquidity truth. |
| `REPLAY_LINEAGE_PROBE_V1` | Replay-only | `DESIGNED` or `NOT_STARTED` | `offline_research_only` | Future replay assumptions and continuity. |
| `LATENCY_LINEAGE_PROBE_V1` | Runtime-safe timestamp probe | `DESIGNED` or `NOT_STARTED` | `evidence_only` | Future latency truth coverage. |

Do not mark any as implemented unless code/tests/paper validation prove it.

## 25. Registry Card Template

Each probe card should use:

```text
# <PROBE_ID>

probe_id:
probe_name:
schema_version:
category:
lifecycle_state:
review_state:
implementation_state:
runtime_deployment_state:
policy_consumer_state:
authority_level:
truth_level_supported:
runtime_safe_classification:
offline_classification:
jsonl_destination:
event_type:
producer:
design_doc:
required_fields:
optional_fields:
lineage_keys:
lineage_confidence_support:
dependencies:
downstream_consumers:
evidence_coverage_state:
archive_class:
danger_flags:
deprecation_state:
operator_notes:
```

## 26. What Not To Do

Do not:

- implement the registry in this task,
- create runtime registry consumers,
- run paper,
- run replay,
- modify runtime code,
- change strategy/risk/execution/live behavior,
- tune thresholds,
- install libraries,
- mark designed probes as implemented,
- grant policy authority to evidence-only probes,
- use registry state as trading input.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Threshold tuning: No

Replay execution: No

Library installs: No

Tests run: none; docs-only registry design.
