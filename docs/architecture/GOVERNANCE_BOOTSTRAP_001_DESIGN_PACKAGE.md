# GOVERNANCE_BOOTSTRAP_001_DESIGN_PACKAGE

## 1. AUDIT_REGISTRY_SCHEMA_V1

This schema governs the tracking of all quantitative backtests, replays, and forensic reports inside `docs/research/AUDIT_REGISTRY.json`.

### Exact JSON Schema (Draft)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AuditRegistry",
  "type": "object",
  "properties": {
    "audits": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "audit_id": { "type": "string" },
          "title": { "type": "string" },
          "owner": { "type": "string" },
          "status": { 
            "type": "string", 
            "enum": ["IN_PROGRESS", "VERIFIED", "SUPERSEDED", "ABANDONED"] 
          },
          "verdict": { 
            "type": "string", 
            "enum": ["EDGE_REAL", "EDGE_WEAK", "REPLAY_ARTIFACT", "PIPELINE_INCIDENT", "DATA_QUALITY_GAP", "OPEN_QUESTION"] 
          },
          "created_date": { "type": "string", "format": "date" },
          "last_updated": { "type": "string", "format": "date" },
          "superseded_by": { "type": ["string", "null"] },
          "canonical": { "type": "boolean" },
          "next_action": { "type": "string" }
        },
        "required": ["audit_id", "title", "owner", "status", "verdict", "created_date", "last_updated", "superseded_by", "canonical", "next_action"]
      }
    }
  },
  "required": ["audits"]
}
```

### Initial Registry Entries
```json
{
  "audits": [
    {
      "audit_id": "RISK_PLAN_ZERO_FORENSIC_AUDIT_001",
      "title": "Analyze zero position-sizing skips in real-time execution loop",
      "owner": "Claude-3.5-Sonnet",
      "status": "VERIFIED",
      "verdict": "EDGE_REAL",
      "created_date": "2026-06-18",
      "last_updated": "2026-06-18",
      "superseded_by": null,
      "canonical": true,
      "next_action": "Incorporate confidence floor diagnostics into status monitoring"
    },
    {
      "audit_id": "LOW_PRICE_EDGE_VALIDATION_001",
      "title": "Verify expectation profile of contracts priced under 10 cents",
      "owner": "Claude-3.5-Sonnet",
      "status": "VERIFIED",
      "verdict": "EDGE_WEAK",
      "created_date": "2026-06-18",
      "last_updated": "2026-06-18",
      "superseded_by": null,
      "canonical": true,
      "next_action": "Design and validate shadow sizer mode for contracts under 5 cents"
    },
    {
      "audit_id": "SUB_5C_EXECUTION_REALITY_AUDIT",
      "title": "Forensic audit of executability gates for ask prices under 5 cents",
      "owner": "Claude-3.5-Sonnet",
      "status": "VERIFIED",
      "verdict": "OPEN_QUESTION",
      "created_date": "2026-06-18",
      "last_updated": "2026-06-19",
      "superseded_by": null,
      "canonical": false,
      "next_action": "Resolve official on-chain settlement keys before treating as executable"
    }
  ]
}
```

---

## 2. DECISION_REGISTRY_SCHEMA_V1

This schema tracks configuration updates and policy/parameter decisions inside `docs/research/DECISION_REGISTRY.json`.

### Exact JSON Schema (Draft)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "DecisionRegistry",
  "type": "object",
  "properties": {
    "decisions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "decision_id": { "type": "string" },
          "evidence": { "type": "string" },
          "approved_by": { "type": "string" },
          "status": { 
            "type": "string", 
            "enum": ["PROPOSED", "ACTIVE", "SUPERSEDED", "DEPRECATED"] 
          },
          "rationale": { "type": "string" },
          "superseded_by": { "type": ["string", "null"] }
        },
        "required": ["decision_id", "evidence", "approved_by", "status", "rationale", "superseded_by"]
      }
    }
  },
  "required": ["decisions"]
}
```

### Initial Registry Entries
```json
{
  "decisions": [
    {
      "decision_id": "DEC_2026_06_18_SHADOW_SIZER_DESIGN",
      "evidence": "LOW_PRICE_EDGE_VALIDATION_001",
      "approved_by": "Operator",
      "status": "ACTIVE",
      "rationale": "Approve the development of a shadow-only sizer configuration to monitor simulated executability of contracts under 5 cents ask before any live activation.",
      "superseded_by": null
    }
  ]
}
```

---

## 3. ACTIVE_QUESTION_V1

This defines the content structure for `docs/research/ACTIVE_QUESTION.md` to focus agent tasks on one topic.

```markdown
# ACTIVE QUESTION: LOW_PRICE_TRUTH_RESOLUTION_001

## Objective
Verify whether simulated settlement outputs for ask prices < $0.05 are backed by official on-chain Polymarket outcomes, or are purely dependent on provisional snapshot price proxies.

## Metadata
- **Current Active Question**: `LOW_PRICE_TRUTH_RESOLUTION_001`
- **Owner Agent**: PM / Research Quant
- **Status**: ACTIVE
- **Next Gate**: Staging execution ledger check on historical files.

## Allowed Audits
- Audits examining token ID settlement contracts on-chain.
- Replays validating path truth versus final resolutions for post-wiring rows.

## Forbidden Audits
- New parameter sweeps or sizer modifications.
- Repetitive reviews of low-price PnL expectancy without direct settlement data joins.
```

---

## 4. PROJECT_RULES_PATCH_PLAN

These are the exact locations inside `PROJECT_RULES.md` where new rules will be inserted when a future write-task is approved:

### A. Archive Exclusion Rules
- **Location**: Inside `# File Reading Rules` (lines 3-23), under the `Do NOT inspect by default:` block.
- **Insert Point**: Directly after line 14 (`- archives/`), append:
  ```text
  - docs/archive/ (Obsolete research/logs)
  ```

### B. Anti-Loop & Max Polling Limits
- **Location**: Inside `# Development Workflow` (lines 198-213), directly after line 206 (`5. Make minimal diffs`).
- **Insert Point**: Insert a new header and sub-bullets:
  ```text
  # Task Anti-Loop Rules
  - Maximum background polling attempts: 3.
  - Maximum wait time: 30 seconds.
  - If a task exceeds either threshold, abort and report partial findings immediately.
  ```

### C. Max Active Frontier Limits
- **Location**: Inside `# File Reading Rules` (lines 3-23), directly before the `Exception for research tasks:` block (line 19).
- **Insert Point**: Insert:
  ```text
  - Limit directory scans to the specific research folder relevant to the active question. Do not explore adjacent frontiers.
  ```

---

## 5. AGENTS_PATCH_PLAN

These are the exact locations inside `AGENTS.md` where new agent instructions will be inserted when a future write-task is approved:

### A. Registry Check Requirement & Duplicate Audit Prevention
- **Location**: Inside `## Role-Routed Compact Workflow v1` (lines 67-87), directly after line 72 (`2. Read MASTER_AGENT_ROUTER.md.`).
- **Insert Point**: Insert a new step:
  ```text
  3. Query docs/research/AUDIT_REGISTRY.json to verify that the target date range, market scope, or hypothesis has not already been verified. Inherit existing findings to avoid duplicate audits.
  ```

### B. Active Question Enforcement
- **Location**: Inside `## Agent Use Boundaries` (lines 155-164), directly after line 163 (`- For docs-only agent work, do not change Python runtime behavior.`).
- **Insert Point**: Insert a new bullet:
  ```text
  - Enforce active question alignment. Agents must only accept tasks matching the current question listed in `docs/research/ACTIVE_QUESTION.md`.
  ```

---

## 6. RESEARCH_AUTHORITY_MAP_V2

This map categorizes all completed audits based on their validation quality:

### A. CANONICAL (Highly Trusted / Source of Truth)
- **`REPLAY_METHODOLOGY_VALIDATION_AUDIT_001`**: Settlement share/win formulas are validated.
- **`RISK_PLAN_ZERO_FORENSIC_AUDIT_001`**: Identifies loop skippage metrics.
- **`LOW_PRICE_EDGE_VALIDATION_001`**: Proves naïve lower-price PnL expectancy has massive execution gaps.

### B. PARTIAL (Informational / Unreconciled Gaps)
- **`CLOB_EMPTY_RESPONSE_FORENSIC_AUDIT`**: Identifies websocket rotation warmup issues, but lacks full parameters.
- **`EVIDENCE_QUALITY_AUDIT`**: Shows older JSONL formatting drifts.

### C. OPEN_QUESTION (Unresolved / Under Audit)
- **`SUB_5C_EXECUTION_REALITY_AUDIT`**:
  - *Verdict*: Gated by unresolved official settlement coverage and incomplete path joins (provisional proxy dependency). **DO NOT treat as Canonical.**
  - *Current Status*: OPEN_QUESTION.

### D. SUPERSEDED (Outdated / Do NOT Use)
- **Naïve Low-Price Expectancy Replays**: Early runs displaying high expectancy without L1-L3 liquidity gates.
- **Experimental HFT specs (`VULTR_PAPER_RUN.md`)**: Replaced by 5-minute market designs.

---

## 7. Implementation Handoff Details

### Recommended Implementation Order
1. **Registry Templates**: Create empty registries `AUDIT_REGISTRY.json` and `DECISION_REGISTRY.json`.
2. **Reconciled Rules**: Apply the patches to `PROJECT_RULES.md` and `AGENTS.md`.
3. **Active Question**: Create `ACTIVE_QUESTION.md` in `docs/research/`.

### Estimated Implementation Effort
- **Total Time**: 1 Hour (docs-only updates and JSON initializations).
- **Complexity**: Low (requires zero python codebase modification).

### Risks
- Incorrect line/header formatting during patches could break markdown links.
- Forcing agents to check registries might cause script failures if the registry JSON syntax is broken.

### Single Highest-Priority Next Action

Create the empty registries `docs/research/AUDIT_REGISTRY.json` and `docs/research/DECISION_REGISTRY.json` under an operator-approved file write task.
